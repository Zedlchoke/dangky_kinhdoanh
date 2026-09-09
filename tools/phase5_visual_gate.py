# -*- coding: utf-8 -*-
"""phase5_visual_gate.py — Phase 5R0: gate VISUAL LAYOUT có bằng chứng.

Vòng đời một lần chạy:
  1. Build fixture semantic (phase5_fixtures) cho từng form;
  2. Export qua ĐÚNG đường production (Bridge.export → write_rendered →
     LibreOffice normalize + PDF);
  3. Với từng DOCX/PDF: hash (template/fixture/docx/pdf), detector XML+PDF,
     render PNG từng trang (pymupdf), đếm trang;
  4. Ghi evidence manifest JSON + summary per WLAY; exit 2 khi có detector
     FAIL (baseline RED kỳ vọng tại HEAD trước khi lane sửa).

Detector ↔ WLAY:
  D1 source-indicator leak      → WLAY-001
  D2 field-code literal         → WLAY-006
  D3 marker/garbage token       → marker/undefined/null/NaN
  D4 next-form contamination    → WLAY-007 (banner phụ lục khác phụ lục)
  D5 blank/sparse page          → WLAY-007 (trang trắng M72) + WLAY-009
  D6 signer orientation         → WLAY-002 (registry: phase5r_expectations.json)
  D7 signature title/split      → WLAY-003
  D8 signature writing space    → WLAY-004
  D9 table grid width/readable  → WLAY-008
  D10 fixed-matrix headers      → WLAY-005 (thiếu cột/hàng pháp định)
  D11 label/value glue          → WLAY-011
  D12 fixture exclusivity       → WLAY-010 (validate_fixture)
  D13 skeleton glue (6V-V1)     → B1 (PLAN 6V mục 1.2): ngày04tháng /
                                  "):CÔNG TY" / value dính label liên hệ
                                  ("0900Fax:", "…vnWebsite:")
  D14 name-slot binding (6V-V1) → B2: slot tên DN/hộ KD trống/gạch/chấm
                                  (chỉ fixture valid-full; form trong
                                  registry handwriting_only_slots được miễn)
  D15 chk glyph (6V-V1)         → B3: tick = "X" trần không ô vuông (chỉ
                                  fixture choice-variants; X trong cell có
                                  viền hoặc cạnh glyph ☒ là hợp pháp)
  D16 token giá trị (6V-V1)     → B4: giá trị LABEL_HOA_N fallback
                                  (NOI_O_HIEN_TAI_123) + mảnh token Word
                                  wrap (_HIEN, _TAI_1)
  D17 header-name sync (WAVE v7)→ band tên DN/HKD lệch/thiếu giá trị
  D18 row placement [F3T]       → F3T.1/F3T.2: pattern K-blank-then-data
                                  (blank chen trước/giữa data), tổng hàng
                                  != header + max(K,N), STT đứt, STT trên
                                  hàng trắng; PDF_BLANK_GAP (chỉ fixture
                                  valid-full). Registry = blocks blankRows.
  D19 header semantics [F3H]    → role-aware theo census (header_semantic_
                                  census.json): BAND_REQUIRED_MISSING,
                                  BAND_FORBIDDEN_PRESENT, BAND_LABEL_REMOVED,
                                  BAND_VALUE_OR_SLOT_MISSING, BAND_WRONG_KEY,
                                  DUPLICATE_EDITABLE, STALE_MIRROR,
                                  LEGAL_SUBTITLE_MUTATED (tools/header_
                                  semantics.py — tách khỏi D17).

Chạy:
  python3 -X utf8 tools/phase5_visual_gate.py                # full corpus × 5 fixture
  python3 -X utf8 tools/phase5_visual_gate.py --forms PLI_M70,PLI_M15
  python3 -X utf8 tools/phase5_visual_gate.py --fixtures valid-full --no-export --dir <dir>

Trạng thái verdict: PASS / FAIL / CANDIDATE (cần reviewer) / NOT RUN.
CANDIDATE không tự nâng thành PASS — reviewer phải xem PNG từng trang và
ghi reviewer_verdict trong manifest (WLAY-012: structural ≠ visual).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.layout_roles import classify_role   # noqa: E402
from tools.phase5_fixtures import (          # noqa: E402
    FIXTURES, M72_VARIANTS, ValueFactory, active_form_ids, build_fixture,
    validate_fixture,
)
from tools.row_placement import (           # noqa: E402  [F3T] D18
    det_row_placement, det_row_placement_pdf, load_loop_registry,
)
from tools import header_semantics as hs    # noqa: E402  [F3H] D19

MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
EXPECT_PATH = ROOT / "tools" / "phase5r_expectations.json"
GATE_ROOT = ROOT / "generated_ho_so" / "_visual_layout" / "phase5r_gate"
# [6V-V1/D14] registry slot tên điền tay theo bản giấy (PLAN 6V Q-V3/C2)
HANDWRITING_SLOTS_PATH = ROOT / "tools" / "phase6v_handwriting_slots.json"

# ngưỡng detector (twips = 1/1440 inch; 567 twips = 1 cm)
# [6V-V1/D9] sàn legacy làm tròn XUỐNG 566 (I4: census có bảng 566 làm
# candidate vĩnh viễn ở sàn 567); bảng >=10 cột dùng sàn riêng 900 (B5).
MIN_COL_TWIPS = 566          # cột hẹp hơn 1 cm (làm tròn xuống) → chữ vỡ
MIN_COL_WIDE_TWIPS = 900     # bảng >=10 cột: cột < 900 twips không đọc được
WIDE_TABLE_COLS = 10         # ngưỡng "bảng rộng" (audit B5: 9–15 cột)
COL_WIDTH_TOLERANCE = 60     # dung sai tổng width vs khổ giấy in
BLANK_PAGE_CHARS = 20        # < 20 ký tự không trắng = trang trắng
SPARSE_PAGE_CHARS = 120      # < 120 ký tự = trang thưa (census)
SIG_PAIR_GAP_PT = 25         # title → instruction cùng cụm (≤25pt)
# [WAVE v7] sàn vùng ký tay 72pt = 2.54cm (quyết định owner
# SIGNATURE-USABILITY-SPACE 2026-09-05; trước đây 40pt legacy floor).
SIG_WRITE_PT = 72
SIG_TOP_MARGIN_PT = 100      # instruction ở đầu trang → nghi split (WLAY-003)

FIELD_CODE_RE = re.compile(
    r"\b(?:PAGE|NUMPAGES|TOC|HYPERLINK|SEQ|STYLEREF|IF)\s*\\\*|\bMERGEFORMAT\b")
GLUE_RE = re.compile(r"[a-zà-ỹ]:[A-ZÀ-Ỹ0-9]")   # "Họ tên:NGUYỄN" (không space)
GARBAGE_RE = re.compile(r"\b(undefined|null|NaN)\b")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fold(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def load_expectations() -> dict:
    if EXPECT_PATH.exists():
        return json.loads(EXPECT_PATH.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# XML detectors
# ---------------------------------------------------------------------------

def xml_texts(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return xml, re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)


def det_source_indicator(docx_path: Path) -> list[str]:
    """D1: paragraph khớp role source-indicator còn trong DOCX."""
    _xml, texts = xml_texts(docx_path)
    hits = []
    for t in texts:
        if classify_role(_fold(t)) == "source-indicator":
            hits.append(t.strip()[:120])
    return hits


def det_field_code(docx_path: Path) -> list[str]:
    """D2: field code Word bị flatten thành text literal (raw text, không
    fold — '\\*' là ký tự literal trong w:t)."""
    _xml, texts = xml_texts(docx_path)
    return [t.strip()[:120] for t in texts if FIELD_CODE_RE.search(t)]


def det_markers(docx_path: Path) -> list[str]:
    """D3: marker {..} sót, undefined/null/NaN, engine token {_stt}."""
    _xml, texts = xml_texts(docx_path)
    joined = " ".join(texts)
    out = [m for m in re.findall(r"\{[/#?]?[A-Za-z_][A-Za-z0-9_.#/?]*\}", joined)]
    out += [m for m in GARBAGE_RE.findall(joined)]
    return out


def det_contamination(docx_path: Path, form_meta: dict) -> list[str]:
    """D4: banner phụ lục KHÁC phụ lục của form (VD: form PLI kéo
    'PHỤ LỤC II ...' của phụ lục kế — PLI_M80). form_maps ghi phu_luc là số
    La Mã thuần ('I'/'II') — chuẩn hoá cả hai phía rồi so SỐ LA MÃ đầy đủ
    (không so prefix — 'I' là prefix của 'II')."""
    _xml, texts = xml_texts(docx_path)
    own_raw = _fold(str(form_meta.get("phu_luc") or ""))
    own_m = re.match(r"^(?:phu luc )?(i{1,3}|iv|v)$", own_raw)
    if not own_m:
        return []
    own = own_m.group(1)
    bad = []
    for t in texts:
        m = re.match(r"^phu luc (i{1,3}|iv|v)\b", _fold(t))
        if m and m.group(1) != own:
            bad.append(t.strip()[:80])
    return bad


def det_table_grid(docx_path: Path) -> list[dict]:
    """D9: grid width — [6V-V1] policy 2 tầng: bảng >=10 cột bắt
    NARROW_COL_WIDE khi min col < 900 twips (không đọc được, B5); bảng
    <10 cột giữ sàn 1cm (566 twips sau làm tròn xuống I4) → NARROW_COL;
    tổng width vượt khổ in được → WIDTH_OVERFLOW.
    Bắt <w:tbl> CÓ attribute (regex '<w:tbl>' mù với '<w:tbl xmlns=...>') và
    DUYỆT CÂN BẰNG để bảng lồng không bị đếm gộp (finditer non-greedy cắt
    bảng lồng sai); chỉ tính gridCol của TẦNG NGOÀI (grid con là phần của
    bảng cha)."""
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    issues = []

    def _balanced_tbls(s: str):
        pos = 0
        while True:
            m = re.search(r"<w:tbl[ >]", s[pos:])
            if not m:
                return
            start = pos + m.start()
            depth = 1
            scan = pos + m.end()
            while depth:
                mm = re.search(r"<w:tbl[ >]|</w:tbl>", s[scan:])
                if not mm:
                    return  # hỏng cấu trúc — bỏ phần còn lại
                depth += -1 if mm.group(0).startswith("</") else 1
                scan += mm.end()
            yield start, scan
            pos = scan

    for ti, (s, e) in enumerate(_balanced_tbls(xml)):
        tbl = xml[s:e]
        cols = [int(w) for w in re.findall(
            r'<w:gridCol[^>]*w:w="(\d+)"', tbl)]
        if not cols:
            continue
        total = sum(cols)
        # [6V-V1/D9] policy 2 tầng (PLAN 6V B5 + I4):
        # - bảng >=10 cột: sàn riêng 900 twips — cột 566-899 "1cm giấy" vẫn
        #   không đọc được khi dàn 10-15 cột (vision M12 1-2mm, M09 2-3mm)
        #   → NARROW_COL_WIDE;
        # - bảng <10 cột: sàn legacy làm tròn XUỐNG 566 (I4: sàn 567 để
        #   bảng census 566 treo candidate vĩnh viễn) → NARROW_COL.
        if len(cols) >= WIDE_TABLE_COLS:
            floor = MIN_COL_WIDE_TWIPS
            code = "NARROW_COL_WIDE"
        else:
            floor = MIN_COL_TWIPS
            code = "NARROW_COL"
        narrow = [(i, w) for i, w in enumerate(cols) if w < floor]
        if narrow:
            issues.append({"table": ti, "code": code,
                           "cols": narrow, "total": total,
                           "ncols": len(cols)})
        if total > 16850:  # A4 portrait 11906 + dung sai rộng (landscape 16838)
            issues.append({"table": ti, "code": "WIDTH_OVERFLOW",
                           "total": total, "cols": len(cols)})
    return issues


# ---------------------------------------------------------------------------
# PDF detectors (pymupdf)
# ---------------------------------------------------------------------------

def pdf_pages(pdf_path: Path, zoom: float = 2.0):
    import fitz  # pymupdf
    doc = fitz.open(str(pdf_path))
    pages = []
    for pno in range(doc.page_count):
        page = doc[pno]
        text = page.get_text("text")
        words = page.get_text("words")  # (x0,y0,x1,y1,word,block,line,wordno)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pages.append({"pno": pno, "text": text, "words": words, "pixmap": pix,
                      # [WAVE v7/D8] mép dưới trang cho phép đo khoảng viết
                      # khi KHÔNG có dòng text phía dưới instruction
                      "page_bottom": float(page.rect.y1)})
    return doc, pages


def det_blank_sparse(pages) -> list[dict]:
    out = []
    for p in pages:
        chars = len(re.sub(r"\s+", "", p["text"]))
        if chars < BLANK_PAGE_CHARS:
            out.append({"page": p["pno"] + 1, "code": "BLANK", "chars": chars})
        elif chars < SPARSE_PAGE_CHARS:
            out.append({"page": p["pno"] + 1, "code": "SPARSE", "chars": chars})
    return out


_SIG_TITLE_FOLD = re.compile(
    r"^(chu ho kinh doanh|dai dien chu ho|chu doanh nghiep|nguoi dai dien "
    r"theo phap luat|dai dien theo phap luat|nguoi khai ho so|nguoi nop ho "
    r"so|nguoi uy quyen|nguoi ky|truong ban|giam doc|ke toan|ke toan truong|"
    r"ban giao dich|dai dien cong ty|chu tich|thu ky|nguoi nop|nguoi nhan|"
    r"chu so huu|chu so huu moi|chu so huu cu|dai dien cac thanh vien khong "
    r"yeu cau thanh lap|hội đồng thanh vien|hoi dong thanh vien|chu tich "
    r"hoi dong thanh vien|chu tich hoi dong thanh vien|tong giam doc|"
    r"cac thanh vien hop danh|nguoi chuyen doi|dai dien phap luat cua to "
    r"chuc|to chuc|ca nhan)\b")
# [WAVE v7] ngữ pháp D6 ĐỒNG BỘ với grammar census rộng
# (tools/test_phase5r_signatures.py): thêm biến thể "ký, ghi họ tên và đóng
# dấu" — trước đây D6 chỉ nhận 215/420 cụm output do grammar hẹp.
_SIG_INSTR_FOLD = re.compile(
    r"\((ky va ghi ro ho ten|ky ghi ro ho ten|ky va ghi ho ten|ky ten|"
    r"ky, ghi ro ho ten|ky, ho ten|ky ho ten|da ky|ky, ho ten, dong dau|"
    r"ky ten, dong dau|ky, ghi ho ten va dong dau)\b")
# [WAVE v7] chỉ thị KHÔNG ngoặc đứng dòng riêng ("Ký, ghi họ tên và đóng dấu"
# của các giấy chứng nhận; "Ký và ghi họ tên từng thành viên") — census nhận,
# D6 trước đây bỏ qua. Nhiều dòng cơ quan đã ký số "Đã ký: ..." không khớp.
_SIG_INSTR_NOPAREN_FOLD = re.compile(
    r"^(da ky|ky(,| va)? (ghi ro ho ten|ghi ho ten|ten va ghi ro ho ten)"
    r"( tung thanh vien)?( va)?( dong dau)?)[0-9]{0,2}(:.*)?$")


def _sig_is_instr(folded: str) -> bool:
    return bool(_SIG_INSTR_FOLD.search(folded)
                or _SIG_INSTR_NOPAREN_FOLD.match(folded))


def _sig_is_daky(folded: str) -> bool:
    """Cụm 'Đã ký' — đã ký số/điện tử: KHÔNG cần vùng viết tay (owner v7)."""
    return "da ky" in folded


def _sig_lines(page) -> list[dict]:
    """Gom words thành dòng; đánh dấu title/instruction chữ ký. Title nhận
    theo 2 đường: (a) vocabulary nhãn người ký; (b) dòng CHỮ IN ngắn kề trên
    instruction (caps-ratio >= 0.6, <= 80 ký tự) — vocabulary không thể liệt
    kê hết nhãn pháp lý (M14: 'NGƯỜI ĐƯỢC TẶNG CHO/NGƯỜI THỪA KẾ/NGƯỜI MUA').
    [WAVE v7] instruction nhận cả chỉ thị KHÔNG ngoặc (_sig_is_instr)."""
    lines: dict[tuple, list] = {}
    for w in page["words"]:
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for _bk, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        text = " ".join(w[4] for w in ws)
        x0 = min(w[0] for w in ws)
        x1 = max(w[2] for w in ws)
        y0 = min(w[1] for w in ws)
        y1 = max(w[3] for w in ws)
        f = _fold(text)
        caps = 0.0
        alpha = [c for c in text if c.isalpha()]
        if len(alpha) >= 4:
            caps = sum(c.isupper() for c in alpha) / len(alpha)
        instr = _sig_is_instr(f)
        out.append({"text": text, "fold": f, "x0": x0, "x1": x1,
                    "y0": y0, "y1": y1,
                    "title": bool(_SIG_TITLE_FOLD.match(f))
                    or (caps >= 0.6 and len(text.strip()) <= 80 and not instr),
                    "instr": instr,
                    "daky": _sig_is_daky(f)})
    return out


def det_signatures(pages, expectations: dict, fid: str) -> dict:
    """D6/D7/D8: đo cụm chữ ký — orientation, split trang, vùng viết."""
    clusters: list[dict] = []   # {page, title_line, instr_line}
    for p in pages:
        lines = [l for l in _sig_lines(p) if l["title"] or l["instr"]]
        used = set()
        for i, l in enumerate(lines):
            if l["instr"] and i not in used:
                title = None
                for j in range(i - 1, -1, -1):
                    cand = lines[j]
                    if cand["title"] and 0 <= l["y0"] - cand["y1"] <= SIG_PAIR_GAP_PT \
                            and not (cand["x1"] < l["x0"] - 200 or
                                     cand["x0"] > l["x1"] + 200):
                        title = cand
                        break
                    if l["y0"] - cand["y1"] > SIG_PAIR_GAP_PT * 3:
                        break
                clusters.append({"page": p["pno"] + 1, "title": title,
                                 "instr": l})
                used.add(i)
                if title:
                    used.add(lines.index(title))
    res = {"clusters": [{k: c[k] for k in ("page",)} | {
        "title": (c["title"] or {}).get("text"),
        "title_y": (c["title"] or {}).get("y0"),
        "instr": c["instr"]["text"][:60], "instr_y": c["instr"]["y0"],
        "daky": c["instr"].get("daky", False),
        "x0": c["instr"]["x0"]} for c in clusters],
        "fails": [], "candidates": []}

    # [WAVE v7] coverage == census: form có registry pin signature (signers
    # >= 1) mà output KHÔNG phát hiện cụm nào = HARD FAIL (khoảng trống không
    # còn được đo, cụm mất thật). Grammar D6 đã đồng bộ census nên điều kiện
    # này không còn có mù grammar để che.
    exp0 = (expectations.get(fid) or {}).get("signature")
    if exp0 and int(exp0.get("signers") or 0) >= 1 and not clusters:
        res["fails"].append({
            "code": "SIG_MISSING", "page": None,
            "expected_signers": exp0.get("signers")})

    # D7 split: instruction ở sát mép trên trang mà không có title cùng trang
    # (cụm không ghép được title trong trang này → title nằm trang trước)
    for c in clusters:
        if not c["title"] and c["instr"]["y0"] < SIG_TOP_MARGIN_PT \
                and c["page"] > 1:
            res["fails"].append({
                "code": "SIG_SPLIT", "page": c["page"],
                "instr": c["instr"]["text"][:60]})
    # D6 orientation theo registry
    exp = (expectations.get(fid) or {}).get("signature")
    if exp and clusters:
        titles = [(_c["title"] or {}).get("text") or _c["instr"]["text"]
                  for _c in clusters if _c["page"] == clusters[0]["page"]]
        # đo: title cùng y (±10pt) ở cùng trang = horizontal
        horiz = 0
        pairs = 0
        cs = [c for c in clusters]
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if cs[i]["page"] != cs[j]["page"]:
                    continue
                pairs += 1
                dy = abs((cs[i]["title"] or cs[i]["instr"])["y0"] -
                         (cs[j]["title"] or cs[j]["instr"])["y0"])
                if dy <= 10:
                    horiz += 1
        measured = "horizontal" if (pairs and horiz == pairs) else (
            "vertical" if clusters else "none")
        if exp.get("orientation") and measured != exp["orientation"]:
            res["fails"].append({
                "code": "SIG_ORIENTATION",
                "expected": exp["orientation"], "measured": measured,
                "clusters": len(clusters)})
    # D8 vùng viết: khoảng dọc từ instr xuống dòng text kế tiếp trong cùng cột;
    # KHÔNG có dòng dưới thì đo ĐẾN MÉP DƯỚI TRANG (census 2026-09-05 — trước
    # đây phép đo bị bỏ qua, che cụm cuối trang).
    # [6V-V4/signgap] sàn 40pt toàn corpus → [WAVE v7] owner nâng 72pt (2.54cm)
    # cho cụm CÒN PHẢI KÝ TAY; cụm "Đã ký" KHÔNG áp vùng viết tay nhưng vẫn
    # chịu keep-together (D7) và vẫn được đo để census. Registry chỉ được pin
    # CAO hơn 72 (max, không thấp hơn); gap < ngưỡng là HARD-FAIL.
    min_gap = max(SIG_WRITE_PT, float(((expectations.get(fid) or {})
                                       .get("signature") or {})
                                      .get("min_write_gap_pt") or 0))
    for p in pages:
        lines = _sig_lines(p)
        page_bottom = p.get("page_bottom")
        for c in clusters:
            if c["page"] != p["pno"] + 1:
                continue
            instr = c["instr"]
            if instr.get("daky"):
                continue   # "Đã ký" — không cần chỗ ký tay
            below = [l for l in lines
                     if l["y0"] > instr["y1"] + 2
                     and not (l["x1"] < instr["x0"] - 60 or
                              l["x0"] > instr["x1"] + 60)
                     and not (l["title"] or l["instr"])]
            if below:
                nearest = min(below, key=lambda l: l["y0"])
                gap = nearest["y0"] - instr["y1"]
            elif page_bottom:
                gap = page_bottom - instr["y1"]
            else:
                continue   # page_bottom thiếu (page fake thiếu field) — bỏ đo
            if gap < min_gap:
                res["fails"].append({
                    "code": "SIG_WRITE_SPACE", "page": p["pno"] + 1,
                    "gap_pt": round(gap, 1),
                    "daky": bool(instr.get("daky")),
                    "instr": instr["text"][:50]})
    return res


def det_glue(pages) -> list[dict]:
    """D11: label':' dính ngay giá trị (không khoảng trắng)."""
    out = []
    for p in pages:
        for m in GLUE_RE.finditer(p["text"]):
            ctx = p["text"][max(0, m.start() - 30):m.end() + 30]
            out.append({"page": p["pno"] + 1,
                        "snippet": ctx.replace("\n", " ")[:80]})
    return out


# [6V-V1] D13 — skeleton glue (lớp B1, PLAN 6V mục 1.2). Rộng hơn D11:
# D11 chỉ bắt label:value dính qua ':' (ngữ pháp [a-zà-ỹ]:[A-Z…]); D13 bắt
# thêm (a) ngày/tháng/năm dính số, (b) label đóng ngoặc dính value in hoa,
# (c) cụm liên hệ template chèn placeholder kề placeholder không separator
# (VD PLII_M13 "{dien_thoai_khac}Thư điện tử" → "0900000014Fax:").
_D13_SUBPATTERNS = (
    # (mã, regex) — case-sensitive như bản in (audit B1 ví dụ đều chữ thường)
    ("DATE_NUM", re.compile(r"(?:ngày|tháng|năm)\d|\d(?:ngày|tháng|năm)")),
    ("PAREN_VALUE", re.compile(r"\):[A-ZÀ-Ỹ]")),
    ("CONTACT_GLUE", re.compile(
        r"(?:Fax|Website|Thư điện tử|Điện thoại):[A-Za-z0-9]"
        r"|[a-z0-9.](?:Fax|Website|Thư điện tử|Điện thoại)\b")),
)


def det_skeleton_glue(docx_path: Path, pages: list) -> list[dict]:
    """D13: skeleton glue — placeholder chèn vào skeleton không space.

    Hai nguồn: PDF text (chủ yếu) + DOCX XML (bắt glue bị PDF wrap che).
    Match từ XML chỉ tính khi chuỗi khớp KHÔNG xuất hiện trong PDF text
    (tránh đếm двой một defect)."""
    pdf_full = "\n".join(p["text"] for p in pages)
    out = []
    for p in pages:
        for code, pat in _D13_SUBPATTERNS:
            for m in pat.finditer(p["text"]):
                ctx = p["text"][max(0, m.start() - 30):m.end() + 30]
                out.append({"page": p["pno"] + 1, "code": code,
                            "snippet": ctx.replace("\n", " ")[:80]})
    if docx_path is not None and docx_path.exists():
        _xml, texts = xml_texts(docx_path)
        xml_full = " ".join(texts)
        seen_xml = set()
        for code, pat in _D13_SUBPATTERNS:
            for m in pat.finditer(xml_full):
                frag = m.group(0)
                if frag in pdf_full or frag in seen_xml:
                    continue   # đã bắt ở PDF (hoặc trùng lặp trong XML)
                seen_xml.add(frag)
                ctx = xml_full[max(0, m.start() - 30):m.end() + 30]
                out.append({"page": 0, "code": code, "source": "docx",
                            "snippet": ctx.replace("\n", " ")[:80]})
    return out


# [6V-V1] D14 — name-slot binding (lớp B2). Chỉ chạy trên fixture
# valid-full: mọi form có slot tên dưới tiêu đề ("(Tên hộ kinh doanh)",
# "Tên hộ kinh doanh (ghi bằng chữ in hoa):", …) phải NHẬN giá trị
# non-empty không phải dòng gạch/chấm (-----, ……, ____). Form nằm trong
# registry handwriting_only_slots (điền tay theo bản giấy) được miễn.
_D14_INLINE = re.compile(
    r"^(?:\d+[.\s]+)?ten (?:ho kinh doanh|doanh nghiep)[^:]{0,70}:(.*)$")
_D14_PAREN = re.compile(
    r"^([^()]{0,40})\(\s*ten\s+(?:ho kinh doanh|doanh nghiep)\s*\)\s*(.*)$")
# từ nối = dấu hiệu mention trong câu, không phải slot dưới tiêu đề
_D14_NOISE = re.compile(r"\b(cua|ve|cho|voi|tren|theo|yeu cau|dien)\b")
_D14_FILLER = re.compile(r"[.\-–—…_·\s]")
_D14_NEXT_LABEL = re.compile(r"ma so|:$|ma so thue")


def load_handwriting_slots(path: Path = HANDWRITING_SLOTS_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"forms": {}}


def det_name_slot(pages: list, form: str,
                  registry: dict | None = None) -> list[dict]:
    """D14: slot tên DN/hộ KD không nhận giá trị ở valid-full.

    Phạm vi: trang 1 (vùng "dưới tiêu đề"). Hai dạng slot:
    inline  "Tên … (ghi bằng chữ in hoa):<giá trị>"
    paren   "(Tên …)" đứng dòng riêng — giá trị ở phần còn lại của dòng
            hoặc dòng kế (dòng kế là label khác → slot trống).
    Giá trị hợp lệ = có ≥2 ký tự chữ sau khi bỏ gạch/chấm/nền. Dòng
    "TÊN HỘ KINH DOANH" in hoa đơn thuần là header band (không phải slot)
    — grammar yêu cầu ':' hoặc ngoặc nên tự loại."""
    if not pages:
        return []
    reg_forms = ((registry or {}).get("forms") or {})
    lines = pages[0]["text"].split("\n")
    issues = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        f = _fold(s)
        mi = _D14_INLINE.match(f)
        mp = _D14_PAREN.match(f)
        rest = None
        kind = None
        if mi and not _D14_NOISE.search(f[:f.find(":")]):
            kind, rest = "inline", mi.group(1).strip()
        elif mp and not _D14_NOISE.search(mp.group(1)):
            suf = mp.group(2)
            cut = re.search(r"ma so|ma so thue", suf)
            kind, rest = "paren", (suf[:cut.start()] if cut else suf).strip()
        if kind is None:
            continue
        slot_label = re.sub(r":.*$", ":", s)[:60]
        if form in reg_forms:
            continue  # handwriting theo bản giấy — đã adjudicate (C2/V4)
        bound = False
        if rest and any(c.isalpha() for c in _D14_FILLER.sub("", rest)) \
                and not _D14_NEXT_LABEL.search(_fold(rest)):
            bound = True
        else:
            # giá trị có thể nằm dòng kế (title-block); dừng nếu dòng kế là
            # label khác ("Trụ sở…:") hoặc header band
            for j in range(i + 1, min(i + 5, len(lines))):
                s2 = lines[j].strip()
                if not s2 or set(s2) <= set(".-–—…_· "):
                    continue
                f2 = _fold(s2)
                if _D14_NEXT_LABEL.search(f2) or f2 == ("cong hoa xa hoi "
                                                        "chu nghia viet nam"):
                    break
                if any(c.isalpha() for c in _D14_FILLER.sub("", s2)):
                    bound = True
                break
        if not bound:
            issues.append({"page": 1, "kind": kind, "slot": slot_label,
                           "value": (rest or "")[:40]})
    return issues


# [6V-V1] D15 — chk glyph (lớp B3). Chạy trên fixture choice-variants với
# form có field type=chk. Tick hợp pháp = X trong ô vuông, ba hình thức
# (Q-V1 chốt 2026-09-04: ô vuông VẼ BẰNG VIỀN, không phụ thuộc font glyph):
#   (a) [6V-V2/C3] X trong RUN có w:bdr (character border — hình thức C3
#       render sinh ra: run viền quanh "X", tick cùng dòng nhãn);
#   (b) glyph ☒ trong cùng paragraph (lịch sử, không phụ thuộc font chủ
#       động sinh);
#   (c) X nằm trong w:tc có viền hiển thị (tcBorders/tblBorders val
#       single/thick/…).
# "X" trần trong paragraph thường, X trong cell KHÔNG viền, X cạnh glyph ô
# trống ☐, và "X" rơi dòng riêng (PDF) đều là finding. Câu hướng dẫn "(đánh
# dấu X vào ô thích hợp)" có X giữa câu — loại bằng rule vị trí (X chỉ tính
# ở ĐẦU/CUỐI paragraph) + từ khoá hướng dẫn đứng kề. Legality (a) tính theo
# RUN chứa tick, không theo paragraph — ô vuông trống (run viền quanh nbsp)
# cạnh X trần KHÔNG được che lỗi.
_D15_INSTR_PREV = re.compile(
    r"(?:danh dau|danh dau x|dau|chon|nhap|ky hieu|bao cao)\s*$")
_D15_INSTR_NEXT = re.compile(r"^(vao|o vuong|o nay|o thich hop)\b")
_D15_VISIBLE_BORDER = re.compile(
    r'<w:(?:tcBorders|tblBorders)[^>]*>.*?w:val="(?:single|thick|double|'
    r"dotted|dashed|inset|outset|wave|dotDash|dotDotDash|triple|thinThick)"
    r'.*?</w:(?:tcBorders|tblBorders)>', re.S)
_D15_TICK_START = re.compile(r"^X(?=$|\s|[,.;)])")
_D15_TICK_END = re.compile(r"(?:(?<=^)|(?<=\s)|(?<=[,.;(:]))X$")
# glue cuối dòng "Thành lập mớiX". KHÔNG có rule glued-ĐẦU: "Xã/Phường…"
# là label tiếng Việt thật (bắt giả "Xã…"), tick thực không có dạng đó
_D15_TICK_GLUED_END = re.compile(r"[A-Za-zÀ-ỹ0-9]X$")
# [6V-V2/C3] legality (a): run có w:bdr (character border) chứa tick.
# w:r không lồng nhau -> non-greedy đủ; w:bdr chỉ xuất hiện trong w:rPr của run.
_D15_RUN_RE = re.compile(r"<w:r(?:\s[^>]*)?>.*?</w:r>", re.S)
_D15_TICK_IN_TEXT = [_D15_TICK_START, _D15_TICK_END, _D15_TICK_GLUED_END]


def _d15_bordered_tick(p_xml: str) -> bool:
    """True nếu paragraph có run VIỀN (w:bdr trong rPr) mà text của đúng run
    đó chứa tick X — hình thức C3 (Q-V1): ô vuông vẽ viền quanh X."""
    for rm in _D15_RUN_RE.finditer(p_xml):
        rseg = rm.group(0)
        if "<w:bdr" not in rseg:
            continue
        rtext = "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", rseg))
        if any(pat.search(rtext) for pat in _D15_TICK_IN_TEXT):
            return True
    return False


def _d15_open_context(xml: str, pos: int, tag: str) -> tuple[int, int] | None:
    """(start, end) của tag mở chứa `pos` chưa đóng (w:tc/w:tbl), hoặc None."""
    opens: list[int] = []
    for mm in re.finditer(r"<%s[ >]|</%s>" % (tag, tag), xml[:pos]):
        if mm.group(0).startswith("</"):
            if opens:
                opens.pop()
        else:
            opens.append(mm.start())
    if not opens:
        return None
    start = opens[-1]
    end = xml.find("</%s>" % tag, pos)
    return (start, end if end != -1 else len(xml))


def det_chk_glyph(docx_path: Path, pages: list,
                  form_meta: dict) -> list[dict]:
    """D15: tick checkbox phải là X TRONG ô vuông (PLAN 6V 5.1.3)."""
    fields = form_meta.get("fields") or []
    if not any(f.get("type") == "chk" for f in fields):
        return []
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    issues = []
    for pm in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.S):
        ptxt = re.sub(r"<[^>]+>", "", pm.group(0)).strip()
        if not ptxt or "X" not in ptxt:
            continue
        ftxt = _fold(ptxt)
        words = ftxt.split()
        tick = False
        if _D15_TICK_START.search(ptxt):
            nxt = words[1] if len(words) > 1 else ""
            tick = not (nxt and _D15_INSTR_NEXT.match(nxt))
        if not tick and (_D15_TICK_END.search(ptxt)
                         or _D15_TICK_GLUED_END.search(ptxt)):
            prev = words[-2] if (len(words) > 1 and words[-1] == "x") \
                else (words[-1][:-1] if words and words[-1].endswith("x")
                      else "")
            tick = not (prev and _D15_INSTR_PREV.search(prev + " "))
        if not tick:
            continue
        if "☒" in ptxt:
            continue  # glyph tick hợp pháp
        if _d15_bordered_tick(pm.group(0)):
            continue  # [6V-V2/C3] X trong run viền w:bdr = ô vuông hợp pháp
        pstart = pm.start()
        cell = _d15_open_context(xml, pstart, "w:tc")
        code = "BARE_X_PARAGRAPH"
        if cell is not None:
            tbl = _d15_open_context(xml, cell[0] + 1, "w:tbl")
            scope = xml[(tbl[0] if tbl else cell[0]):cell[1]]
            if _D15_VISIBLE_BORDER.search(scope):
                continue  # X trong cell có viền = ô vuông hợp pháp
            code = "BARE_X_BORDERLESS_CELL"
        if "☐" in ptxt or "□" in ptxt:
            code = "X_BESIDE_EMPTY_BOX"
        issues.append({"code": code, "paragraph": ptxt[:70]})
    # PDF: "X" rơi dòng riêng (XML cùng paragraph nhưng PDF wrap tách dòng).
    # [F-V5-2] Chỉ tính khi DOCX còn ÍT NHẤT MỘT X trần bất hợp pháp ở lớp
    # XML: khi mọi X của hồ sơ đều hợp pháp (glyph ☒, run w:bdr, cell có
    # viền), một X đứng một mình trên dòng PDF là artifact wrap của ô bảng
    # có viền (tên ngành dài ép dòng — audit V5 E2E PLI_M01 p4), không phải
    # lỗi người dùng nhìn thấy. Mutation V1d giữ bất biến: X trần thật thì
    # cả BARE_X_* lẫn X_OWN_LINE vẫn bị bắt.
    if issues:
        for p in pages:
            for ln in p["text"].split("\n"):
                if ln.strip() == "X":
                    issues.append({"page": p["pno"] + 1, "code": "X_OWN_LINE",
                                   "paragraph": ""})
    return issues


# nạp 1 lần sau khi hàm load đã định nghĩa (registry adjudicate ở C2/V4)
HANDWRITING_SLOTS = load_handwriting_slots()


# [6V-V1] D16 — token kỹ thuật làm giá trị (lớp B4). Fixture fallback
# sinh giá trị LABEL_HOA_N (phase5_fixtures ValueFactory nhánh mặc định:
# nhãn fold → HOA + gạch dưới + chỉ số) — người đọc thấy "NOI_O_HIEN_TAI_
# 123" thay vì giá trị thật. Token dài trong cột hẹp (~1cm) còn bị Word
# wrap XÉ GIỮA TOKEN thành các dòng mảnh "_HIEN", "_TAI_1", "NOI_T".
# Grammar token theo audit B4: ^[A-Z][A-Z0-9_]*_[0-9]+$ (full-match một
# từ trong PDF text). Mảnh: cả dòng chỉ chứa HOA/chữ số/gạch dưới, có
# "_", KHÔNG full-match grammar token (đó mới là mảnh vỡ, không phải
# token nguyên) và không chứa chữ thường.
_D16_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]*_[0-9]+$")
_D16_PIECE = re.compile(r"^[A-Z0-9_]*_[A-Z0-9_]*$")
# [6V-V2/Lead] dòng TOÀN gạch dưới (VD "___________________" — đường điền
# in sẵn của bản giấy, PLI_M12/M15) KHÔNG phải mảnh token vỡ: mảnh thật
# luôn có ít nhất 1 ký tự chữ HOA/chữ số (VD "_TAI_1", "NOI_T", "_122").
# Loại false-positive này để D16 đạt 0 trung thực khi B4 đóng (finding khi
# Lead review C4: 16/16 hit residual trên subset đều là đường điền).
_D16_PIECE_HAS_ALNUM = re.compile(r"[A-Z0-9]")
_D16_MAX_PIECE_LEN = 24   # dài hơn = token nguyên dòng riêng, không phải mảnh


def det_token_values(pages: list) -> list[dict]:
    """D16: giá trị là token kỹ thuật (LABEL_HOA_N) hoặc mảnh token vỡ."""
    out = []
    for p in pages:
        for ln in p["text"].split("\n"):
            s = ln.strip()
            if not s:
                continue
            # (1) token nguyên: quét từng từ trong dòng
            for w in s.split():
                w2 = w.strip(",.;:()“”\"'")
                if w2 and _D16_TOKEN.fullmatch(w2):
                    out.append({"page": p["pno"] + 1, "code": "TOKEN_VALUE",
                                "value": w2[:40]})
            # (2) mảnh token: cả dòng là mảnh HOA có "_" không phải token
            if "_" in s and len(s) <= _D16_MAX_PIECE_LEN \
                    and not any(c.islower() for c in s) \
                    and not _D16_TOKEN.fullmatch(s) \
                    and _D16_PIECE.fullmatch(s) \
                    and _D16_PIECE_HAS_ALNUM.search(s):
                out.append({"page": p["pno"] + 1, "code": "TOKEN_FRAGMENT",
                            "value": s[:40]})
    return out


# [WAVE v7] D17 — HEADER-NAME-SYNC: band đầu trang phải mirror đúng giá trị
# canonical của thân. Registry tools/header_name_binding.json (nguồn chân lý
# duy nhất, census 2026-09-05). Contract fixture valid-full:
#   - ô band còn dòng kẻ '-------'            → HDR_NAME_UNBOUND (hard)
#   - band có giá trị nhưng KHÔNG khớp thân   → HDR_NAME_SYNC (hard)
#     (đếm số lần xuất hiện của giá trị band trong toàn văn: band + thân
#     phải >= 2; bind nhầm key cho giá trị khác sẽ chỉ thấy 1 lần)
# Form không nằm registry: detector bỏ qua (M33/PLII_M06 BLOCKED_OWNER).
_HEADER_NAME_BINDING_PATH = ROOT / "tools" / "header_name_binding.json"


def load_header_name_binding(path: Path = _HEADER_NAME_BINDING_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"forms": {}}


_HDR_NAME_LABEL_FOLD = re.compile(r"^ten (doanh nghiep|ho kinh doanh)$")
_HDR_NAME_DASH_FOLD = re.compile(r"^[-_.\u2013\u2014\u2026 ]{3,}$")


def _find_motto_line(lines: list) -> dict | None:
    """[Pin sync — owner band-label removal 2026-09-08] commit e148d83 xoá
    nhãn khỏi ô band nên D17 không còn dòng nhãn để neo. Neo mới: dòng
    quốc hiệu trang 1 — luôn nằm trong band chủ thể, không có ở bảng dữ
    liệu. Dòng giá trị band = các dòng trong cột trái quanh dòng quốc hiệu
    (tên dài wrap làm lệch baseline trái/phải, giá trị có thể nằm TRÊN
    dòng quốc hiệu)."""
    for ln in lines:
        if "cong hoa xa hoi chu nghia viet nam" in ln["fold"]:
            return ln
    return None


def _band_slot_lines(lines: list) -> tuple[dict | None, list]:
    """(dòng quốc hiệu, [dòng quốc hiệu] + các dòng slot band theo y)."""
    anchor = _find_motto_line(lines)
    if anchor is None:
        return None, []
    lo, hi = anchor["y0"] - 40.0, anchor["y1"] + 40.0
    slot = [ln for ln in lines
            if ln is not anchor
            and ln["x0"] <= anchor["x0"] + 20
            and lo <= ln["y0"] <= hi]
    slot.sort(key=lambda ln: ln["y0"])
    return anchor, [anchor] + slot[:4]


def _page_lines_of(page) -> list[dict]:
    lines: dict[tuple, list] = {}
    for w in page["words"]:
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for _bk, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        out.append({
            "text": " ".join(w[4] for w in ws),
            "fold": _fold(" ".join(w[4] for w in ws)),
            "x0": min(w[0] for w in ws), "x1": max(w[2] for w in ws),
            "y0": min(w[1] for w in ws), "y1": max(w[3] for w in ws),
        })
    return out


def det_header_name(pages: list, form: str, registry: dict | None = None,
                    full_text: str | None = None) -> list[dict]:
    if not pages:
        return []
    bind = ((registry or {}).get("forms") or {}).get(form)
    if not bind:
        return []
    lines = _page_lines_of(pages[0])
    # [Pin sync — owner band-label removal 2026-09-08] neo band qua dòng
    # quốc hiệu (nhãn 'TÊN …' đã bị owner xoá khỏi band — e148d83). Mất
    # quốc hiệu = mất cả band.
    anchor, below = _band_slot_lines(lines)
    if anchor is None:
        return [{"code": "HDR_NAME_LABEL_MISSING", "page": 1,
                 "expect": bind.get("label"),
                 "note": "band mất khối quốc hiệu (band không còn nhãn từ "
                         "e148d83 — neo là dòng quốc hiệu)"}]
    if not below:
        return [{"code": "HDR_NAME_SYNC", "page": 1, "value": ""}]
    # [Pin sync — owner band-label removal 2026-09-08] vùng band chỉ còn
    # dòng kẻ (slot không bind, artifact/mutation cũ) → HDR_NAME_UNBOUND.
    has_dash = any(_HDR_NAME_DASH_FOLD.match(ln["fold"]) for ln in below)
    # Tên dài wrap 2 dòng và PDF gom baseline trái+phải thành một dòng
    # (chữ quốc hiệu dính vào giá trị band) — tách quốc hiệu đã biết rồi
    # PASS nếu BẤT KỲ mảnh nào của band khớp thân (xuất hiện >= 2 lần).
    # [F3B 2026-09-07] mode=band_input (N-v1/N-v2 DECIDED A — PLI_M33,
    # PLII_M06): band là Ô NHẬP pháp định DUY NHẤT, thân mẫu KHÔNG có
    # trường tên (docs/audits/f3_hard_fail_2026-09-07.md) → mỗi mảnh giá
    # trị band (đã lọc motto + dòng kẻ) phải xuất hiện ĐÚNG 1 LẦN trong
    # toàn văn. count >= 2 = double-slot (band + thân) quay lại → FAIL;
    # count != 1 (kể cả 0 — không đối chiếu được) cũng FAIL. Mode mặc
    # định (mirror) giữ nguyên hợp đồng >=2.
    _motto_folds = ("cong hoa xa hoi chu nghia viet nam",
                    "doc lap - tu do - hanh phuc")
    hay = re.sub(r"\s+", " ", _fold(
        full_text or "\n".join(p["text"] for p in pages)))
    band_input = (bind.get("mode") or "").strip() == "band_input"
    bi_seen = saw_needle = False
    for ln in below[:3]:
        f = ln["fold"]
        if _HDR_NAME_DASH_FOLD.match(f):
            continue
        for m in _motto_folds:
            f = f.replace(m, " ")
        needle = re.sub(r"\s+", " ", f).strip(" .,-")
        if not needle or not any(c.isalpha() for c in needle):
            continue
        saw_needle = True
        n = hay.count(needle)
        if band_input:
            if n != 1:
                return [{"code": "HDR_NAME_SYNC", "page": 1,
                         "value": ln["text"][:60]}]
            bi_seen = True
        elif n >= 2:
            return []
    if not saw_needle:
        if has_dash:
            return [{"code": "HDR_NAME_UNBOUND", "page": 1,
                     "slot": bind.get("label")}]
        return [{"code": "HDR_NAME_SYNC", "page": 1, "value": ""}]
    if band_input and bi_seen:
        return []
    return [{"code": "HDR_NAME_SYNC", "page": 1,
             "value": (below[1] if len(below) > 1 else below[0])["text"][:60]}]


# [WAVE v7] registry band mirror tên chủ thể — nạp 1 lần sau khi loader đã
# định nghĩa (như HANDWRITING_SLOTS)
HEADER_NAME_BINDING = load_header_name_binding()


def det_fixed_matrix_headers(pdf_text: str, form_map: dict) -> list[str]:
    """D10: header cột của fixed-matrix phải xuất hiện trong PDF text."""
    missing = []
    hay = _fold(pdf_text)
    for spec in form_map.get("section_specs") or []:
        if spec.get("kind") != "fixed-matrix":
            continue
        for c in spec.get("columns") or []:
            label = (c.get("label") or "").strip()
            if len(label) >= 3 and _fold(label) not in hay:
                missing.append("%s.%s" % (spec.get("semantic_key"),
                                          label[:40]))
    return missing


# ---------------------------------------------------------------------------
# Gate runner
# ---------------------------------------------------------------------------

def merge_fixture_data(maps: dict, blocks_all: dict, fixture: str,
                       form_ids: list[str]) -> dict:
    """Gộp data các form cho một batch export (key unique per form giữ giá
    trị riêng; key chung — ngày ký, cơ quan… — nhận giá trị cuối, cùng ngữ
    nghĩa). [wave2-B1] tách thành hàm dùng chung để run_export và test hồi
    quy gọi ĐÚNG một logic merge; payload phẳng sau đó qua Bridge.export
    (_nest) — list dòng grid của từng form phải sống sót sau merge.

    [wave2-B6 2026-09-09] de-dup tick cụm loại-trừ sau merge: batch 86 form
    gộp flat last-write-wins, các form khác nhau pick lựa chọn KHÁC NHAU của
    CÙNG key auto (vd `chk_auto_khong` dùng chung M01–M05/M12/M15) → merged
    cùng lúc 'X' ở 2 key của một cụm → render "Có X Không X" (finding corpus
    v2 choice-variants: 7 cụm / 7 form). Duyệt từng cụm exclusive theo thứ tự
    (form, index): giữ đúng 1 key ticked (sort đầu), unset phần còn lại —
    xác suất cụm sau mất sạch tick là 0 trong corpus hiện hành vì mỗi form
    build riêng đã tick đúng 1; key dùng chung chỉ có thể NHẤT QUÁN toàn
    batch (một key một giá trị) — khác biệt giữa các form cùng key là giới
    hạn của data-model auto-key, ghi defect_registry P1."""
    from tools.phase5_fixtures import _exclusive_clusters
    merged: dict = {}
    for fid in form_ids:
        merged.update(build_fixture(fid, maps[fid], fixture,
                                    blocks_all.get(fid), ValueFactory()))
    if fixture == "choice-variants":
        for fid in sorted(form_ids):
            try:
                groups, _counts = _exclusive_clusters(maps[fid],
                                                      blocks_all.get(fid) or {})
            except Exception:
                continue
            for members in groups:
                xs = sorted(k for k in set(members) if merged.get(k) == "X")
                for k in xs[1:]:
                    merged.pop(k, None)
    return merged


def build_all_data(maps: dict, blocks_all: dict, fixture: str) -> dict:
    """Wrapper tương thích: gộp TOÀN BỘ form trong maps (đã sắp xếp)."""
    return merge_fixture_data(maps, blocks_all, fixture, sorted(maps))


def run_export(maps: dict, blocks_all: dict, fixture: str,
               form_ids: list[str], out_root: Path) -> tuple[list, list]:
    """Export qua Bridge.export rồi DỜI evidence vào out_root/<fixture>/ để
    bundle tự chứa (docx + pdf + manifest + PNG cùng một cây)."""
    import shutil
    from app_web.main import Bridge
    bridge = Bridge()
    errors = []
    dirs = []
    non72 = [f for f in form_ids if f != "PLI_M72"]
    batches = []
    if non72:
        batches.append(("main", non72, None))
    for value, flag in M72_VARIANTS:
        if "PLI_M72" in form_ids:
            batches.append(("m72_%s" % value.lower(), ["PLI_M72"],
                            (value, flag)))
    dst_root = out_root / fixture
    dst_root.mkdir(parents=True, exist_ok=True)
    for tag, ids, variant in batches:
        # [wave2-B1] merge qua hàm dùng chung merge_fixture_data (testable)
        data = merge_fixture_data(maps, blocks_all, fixture, ids)
        if variant:
            value, flag = variant
            data["dn.loai_hinh"] = value
            data[flag] = "X"
        case_id = "p5r_%s_%s" % (fixture.replace("-", "_"), tag)
        payload = {"case_id": case_id, "format": "both",
                   "forms": [{"id": f} for f in ids], "data": data}
        r = bridge.export(payload)
        errors += ["%s: %s" % (tag, e) for e in (r.get("errors") or [])]
        src = r.get("dir")
        if src:
            dst = dst_root / tag
            # dst còn lại từ lần chạy trước (run bị kill giữa chừng) sẽ biến
            # shutil.move thành move-VÀO-TRONG (nested) và analyze() đọc PHẢI
            # file stale — xoá dst trước khi move để evidence luôn là file
            # của lần chạy hiện hành.
            if dst.exists():
                shutil.rmtree(dst)
            shutil.move(src, dst)
            # kèm ZIP nếu có
            zsrc = Path(str(src) + ".zip")
            if zsrc.exists():
                shutil.move(str(zsrc), str(dst) + ".zip")
            dirs.append(dst)
        else:
            errors.append("%s: không có thư mục export" % tag)
    return errors, dirs


def analyze(maps, blocks_all, fixture: str, dirs: list[Path],
            out_root: Path, expectations: dict, zoom: float,
            render_pages: bool = True) -> list[dict]:
    records = []
    for d in dirs:
        for docx_path in sorted(d.glob("*.docx")):
            fid = docx_path.stem
            if fid not in maps:
                continue
            pdf_path = docx_path.with_suffix(".pdf")
            template = ROOT / "app" / maps[fid]["template"]
            rec = {
                "form": fid, "fixture": fixture,
                # d.name là tag batch ("main" | "m72_*") — dùng làm variant
                # thật (điều kiện startswith("p5r_") cũ không bao giờ đúng vì
                # p5r_ là case_id, không phải tên thư mục đích).
                "tag": d.name,
                "variant": "m72" if d.name.startswith("m72_") else "",
                "dir": str(d),
                "docx": str(docx_path), "pdf": str(pdf_path),
                "template": maps[fid]["template"],
                "template_hash": sha256_file(template),
                "docx_hash": sha256_file(docx_path),
                "pdf_hash": sha256_file(pdf_path) if pdf_path.exists() else "",
                "word_open_verdict": "NOT RUN",
                "reviewer_verdict": "NOT_REVIEWED",
                "detectors": {}, "pages": [], "page_count": 0,
            }

            # --- XML detectors
            rec["detectors"]["D1_source_indicator"] = det_source_indicator(docx_path)
            rec["detectors"]["D2_field_code"] = det_field_code(docx_path)
            rec["detectors"]["D3_markers"] = det_markers(docx_path)
            rec["detectors"]["D4_contamination"] = det_contamination(
                docx_path, maps[fid])
            rec["detectors"]["D9_table_grid"] = det_table_grid(docx_path)
            # [F3T] D18 row placement — structural DOCX (mọi fixture):
            # K-blank-then-data / tổng hàng max(K,N) / STT đứt / STT trên
            # hàng trắng. Registry loop đọc blocks blankRows (không hard-code
            # form); fixed-matrix/output-table không bị áp công thức max(K,N).
            rec["detectors"]["D18_row_placement"] = det_row_placement(
                docx_path, load_loop_registry(blocks_all.get(fid) or {}))

            # --- PDF detectors
            if pdf_path.exists():
                _doc, pages = pdf_pages(pdf_path, zoom)
                rec["page_count"] = len(pages)
                rec["detectors"]["D5_blank_sparse"] = det_blank_sparse(pages)
                # [F3T] D18 lớp PDF bổ trợ — chỉ fixture valid-full (N>=1;
                # N=0 là K trắng hợp pháp nên không có dòng STT để đo).
                rec["detectors"]["D18_row_placement"] = (
                    rec["detectors"].get("D18_row_placement", [])
                    + det_row_placement_pdf(pages))
                sig = det_signatures(pages, expectations, fid)
                rec["detectors"]["D6_signature"] = {
                    "fails": sig["fails"], "candidates": sig["candidates"]}
                full_text = "\n".join(p["text"] for p in pages)
                rec["detectors"]["D10_matrix_headers"] = \
                    det_fixed_matrix_headers(full_text, maps[fid])
                glues = det_glue(pages)
                rec["detectors"]["D11_glue"] = glues[:40]
                rec["detectors"]["D11_glue_count"] = len(glues)
                # [6V-V1] D13 skeleton glue (PDF + XML), rộng hơn D11
                skel = det_skeleton_glue(docx_path, pages)
                rec["detectors"]["D13_skeleton_glue"] = skel[:40]
                rec["detectors"]["D13_glue_count"] = len(skel)
                # [6V-V1] D14 name-slot binding — contract fixture
                # valid-full (đầy đủ dữ liệu mới có quyền đòi slot bound)
                rec["detectors"]["D14_name_slot"] = (
                    det_name_slot(pages, fid, HANDWRITING_SLOTS)
                    if fixture == "valid-full" else [])
                # [WAVE v7] D17 header-name sync — contract fixture
                # valid-full (giá trị canonical phải có mặt để đối chiếu)
                rec["detectors"]["D17_header_name"] = (
                    det_header_name(pages, fid, HEADER_NAME_BINDING,
                                    "\n".join(p["text"] for p in pages))
                    if fixture == "valid-full" else [])
                # fixture exclusivity (D12) — build TRƯỚC D19 (D19 lớp PDF
                # cần giá trị canonical từ fixture valid-full)
                fdata = build_fixture(fid, maps[fid], fixture,
                                      blocks_all.get(fid), ValueFactory())
                # [F3H] D19 header-subject-semantics — role-aware, TÁCH KHỎI
                # D17 (census header_semantic_census.json): structural chạy
                # mọi fixture; lớp PDF chỉ valid-full (cần giá trị canonical).
                rec["detectors"]["D19_header_semantics"] = hs.det_record(
                    fid, blocks_all.get(fid), pages=pages,
                    data=fdata,
                    full_text="\n".join(p["text"] for p in pages),
                    pdf_checks=(fixture == "valid-full"),
                    registry=HEADER_NAME_BINDING)
                # [6V-V1] D15 chk glyph — contract fixture choice-variants
                # (mọi nhóm loại trừ có đúng 1 lựa chọn được tick)
                rec["detectors"]["D15_chk_glyph"] = (
                    det_chk_glyph(docx_path, pages, maps[fid])
                    if fixture == "choice-variants" else [])
                # [6V-V1] D16 token giá trị (mọi fixture, mạnh ở
                # long-boundary nơi token dài bị Word wrap)
                toks = det_token_values(pages)
                rec["detectors"]["D16_token_values"] = toks[:60]
                rec["detectors"]["D16_token_count"] = len(toks)
                rec["detectors"]["D12_fixture_violations"] = validate_fixture(
                    maps[fid], blocks_all.get(fid) or {}, fdata, fixture)
                # render PNG
                if render_pages:
                    # [V0-I2] PNG THEO RECORD: <fixture>/<tag>/<FORM>/ với tag
                    # là tên batch ("main" | "m72_*"). Trước đây 5 biến thể M72
                    # ghi chung <fixture>/PLI_M72/ → ghi đè lẫn nhau: manifest
                    # claim 1644 trang, đĩa 1567 file, 4/5 biến thể trỏ ảnh
                    # nhầm. d.name chính là tag (dst_root/tag trong run_export).
                    pdir = out_root / fixture / d.name / fid
                    if pdir.exists():
                        shutil.rmtree(pdir)
                    pdir.mkdir(parents=True, exist_ok=True)
                    rec["png_dir"] = str(pdir)
                    for p in pages:
                        name = pdir / ("page-%02d.png" % (p["pno"] + 1))
                        p["pixmap"].save(str(name))
                        rec["pages"].append(str(name))
            else:
                rec["page_count"] = 0
                rec["detectors"]["D5_blank_sparse"] = [{"page": 0,
                                                        "code": "NO_PDF"}]
            records.append(rec)
    return records


HARD_FAIL_KEYS = {
    "D1_source_indicator": 1, "D2_field_code": 1, "D3_markers": 1,
    "D4_contamination": 1, "D12_fixture_violations": 1,
    # [WAVE v7] HEADER-NAME-SYNC là hard gate (owner: band mirror read-only,
    # một giá trị một lần nhập) — band còn dòng kẻ hoặc lệch giá trị thân
    # đều FAIL record.
    "D17_header_name": 1,
    # [F3T] ROW_PLACEMENT fail-loud (owner directive 2026-09-08): pattern
    # K-blank-then-data (K+N) trên DOCX/PDF là defect cấu trúc bảng — không
    # cho qua như candidate.
    "D18_row_placement": 1,
    # [F3H] HEADER-SUBJECT-SEMANTICS (owner directive 2026-09-08): band chủ
    # thể theo role census — thiếu/cấm/nhãn mất/slot mất/sai key/trùng
    # editable/stale mirror/subtitle pháp định bị sửa đều FAIL record.
    "D19_header_semantics": 1,
}


def _d5_sparse_allowed(entries: list[dict], rec: dict, item: dict) -> dict | None:
    """[6V-V4b việc 9] Tra sparse allowlist theo (fixture, tag, form, page).
    Khóa vắng mặt trong entry = wildcard. Trả entry adjudicate (có
    "adjudication" + "reason") hoặc None."""
    for a in entries:
        if a.get("form") not in (None, rec.get("form")):
            continue
        if a.get("fixture") not in (None, rec.get("fixture")):
            continue
        if a.get("tag") not in (None, rec.get("tag")):
            continue
        if a.get("page") not in (None, item.get("page")):
            continue
        return a
    return None


def record_verdicts(records: list[dict], allowlist: dict) -> None:
    for rec in records:
        fails = []
        candidates = []
        for key, val in rec["detectors"].items():
            if not val:
                continue
            if key in HARD_FAIL_KEYS:
                fails.append({"detector": key, "detail": val})
            elif key == "D6_signature" and isinstance(val, dict):
                # detector đã phân ranh giới: res["fails"] chỉ chứa vi phạm
                # registry/contract (orientation, split, write-space — sàn 40pt
                # TOÀN CORPUS theo quyết định owner 2026-09-05 [6V-V4/signgap],
                # registry chỉ pin cao hơn) — toàn bộ là hard; candidates là
                # census.
                fails += [{"detector": "D6_signature", "detail": f}
                          for f in val.get("fails", [])]
                candidates += [{"detector": "D6_signature", "detail": c}
                               for c in val.get("candidates", [])]
            elif key == "D5_blank_sparse":
                for item in val:
                    code = item.get("code")
                    if code == "NO_PDF":
                        fails.append({"detector": key, "detail": item})
                    elif code == "BLANK":
                        allowed = allowlist.get("blank_pages", [])
                        if not any(rec["form"] == a.get("form") and
                                   item["page"] == a.get("page")
                                   for a in allowed):
                            fails.append({"detector": key, "detail": item})
                    else:
                        # [6V-V4b việc 9] SPARSE có thể được adjudicate trước
                        # (auditor/6v-visual 2026-09-05: 72 hit = 59 (i) + 7
                        # (ii) + 6 (iii) đã fix) — hit nằm trong
                        # sparse_pages của allowlist không còn là candidate
                        # "chưa adjudicate"; verdict ghi vào record để
                        # summary minh bạch số đã adjudicate.
                        entry = _d5_sparse_allowed(
                            allowlist.get("sparse_pages", []), rec, item)
                        if entry:
                            rec.setdefault("d5_adjudicated", []).append({
                                "page": item.get("page"),
                                "chars": item.get("chars"),
                                "adjudication": entry.get("adjudication"),
                                "reason": entry.get("reason"),
                            })
                        else:
                            candidates.append({"detector": key,
                                               "detail": item})
            else:
                # D9/D10/D11 census → candidate (chốt policy ở Lane C/5R4)
                candidates.append({"detector": key, "detail": val})
        rec["gate_fails"] = fails
        rec["gate_candidates"] = candidates
        rec["gate_verdict"] = "FAIL" if fails else "PASS_CANDIDATE_REVIEW"


def assert_png_disk_matches_manifest(out_root: Path, records: list[dict],
                                     fixtures: list[str]) -> dict:
    """[V0-I2] Evidence phải khớp đĩa: Σ len(pages) trong manifest == số file
    page-*.png vật lý dưới cây từng fixture — lệch 1 file cũng FAIL.

    Sự kiện 1567/1644 (manifest claim 1644 trang, đĩa chỉ 1567 file vì 5
    biến thể M72 render ghi đè chung 1 thư mục) phải chết ngay tại gate với
    báo cáo path-mismatch chi tiết: tổng claim, tổng thật, từng thư mục lệch
    (claim bao nhiêu / đĩa bao nhiêu).
    """
    claimed = 0
    per_dir_claim: dict[str, int] = {}
    for r in records:
        pages = r.get("pages") or []
        claimed += len(pages)
        pdir = r.get("png_dir")
        if pdir:
            per_dir_claim[pdir] = per_dir_claim.get(pdir, 0) + len(pages)
    disk = 0
    per_dir_disk: dict[str, int] = {}
    for fixture in fixtures:
        froot = out_root / fixture
        if not froot.exists():
            continue
        for png in froot.rglob("page-*.png"):
            parent = str(png.parent)
            per_dir_disk[parent] = per_dir_disk.get(parent, 0) + 1
            disk += 1
    mismatches = []
    for d in sorted(set(per_dir_claim) | set(per_dir_disk)):
        c, a = per_dir_claim.get(d, 0), per_dir_disk.get(d, 0)
        if c != a:
            mismatches.append({"dir": d, "claimed": c, "disk": a})
    return {"claimed": claimed, "disk": disk, "mismatches": mismatches,
            "ok": claimed == disk and not mismatches}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=",".join(FIXTURES))
    ap.add_argument("--forms", default="all")
    ap.add_argument("--outdir", default="")
    ap.add_argument("--zoom", type=float, default=2.0)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--allowlist", default=str(ROOT / "docs" /
                                                "phase6v_d5_sparse_allowlist.json"))
    args = ap.parse_args()

    fixtures = [f.strip() for f in args.fixtures.split(",") if f.strip()]
    for f in fixtures:
        if f not in FIXTURES:
            print("fixture không hợp lệ: %r" % f)
            return 2
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    skipped: list[tuple[str, str]] = []
    if args.forms == "all":
        # [wave2-B5] inventory ĐỘNG như phase5_export_corpus: form mang marker
        # current_law_status inactive (vd PLI_M11 REMOVED_BY_CURRENT_LAW —
        # TT 121/2026 bãi bỏ Mẫu 11) phải ra KHỎI corpus; trước đây
        # sorted(maps) đưa cả form đã bãi bỏ vào render + manifest.
        form_ids, skipped = active_form_ids(maps, log=print)
    else:
        form_ids = [f.strip() for f in args.forms.split(",") if f.strip()]
    # [wave2-B5] render-unit đếm ĐỘNG (không hard-code): batch 'main' =
    # mọi form active TRỪ PLI_M72; PLI_M72 (nếu active) render 1 DOCX riêng
    # cho MỖI variant trong M72_VARIANTS.
    non72 = [f for f in form_ids if f != "PLI_M72"]
    m72_units = len(M72_VARIANTS) if "PLI_M72" in form_ids else 0
    render_units = len(non72) + m72_units
    print("[corpus-inventory] active=%d skipped=%d m72_variants=%d "
          "render_units_per_fixture=%d"
          % (len(form_ids), len(skipped), m72_units, render_units))
    blocks_all = {}
    for fid in form_ids:
        p = BLOCKS_DIR / ("%s.json" % fid)
        if p.exists():
            blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))
    allowlist = {}
    alp = Path(args.allowlist)
    if alp.exists():
        allowlist = json.loads(alp.read_text(encoding="utf-8"))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(args.outdir) if args.outdir else GATE_ROOT / ts
    out_root.mkdir(parents=True, exist_ok=True)
    expectations = load_expectations()

    all_records = []
    export_errors = []
    for fixture in fixtures:
        t0 = datetime.now()
        errors, dirs = run_export(maps, blocks_all, fixture,
                                  form_ids, out_root)
        export_errors += ["%s: %s" % (fixture, e) for e in errors]
        recs = analyze(maps, blocks_all, fixture, dirs, out_root,
                       expectations, args.zoom, not args.no_render)
        record_verdicts(recs, allowlist)
        all_records += recs
        n_fail = sum(1 for r in recs if r["gate_verdict"] == "FAIL")
        print("[%s] %d forms, %d FAIL, %.1fs"
              % (fixture, len(recs), n_fail,
                 (datetime.now() - t0).total_seconds()))

    manifest = {
        "generated": ts,
        "fixtures": fixtures,
        "forms": form_ids,
        # [wave2-B5] inventory động: số render-unit không hard-code — tổng
        # DOCX mỗi fixture = len(non72) + M72 variants (90 với corpus hiện
        # tại: 86 active, M11 bị loại, M72 ×5 variant).
        "inventory": {
            "active": len(form_ids),
            "skipped": skipped,
            "m72_variants": m72_units,
            "render_units_per_fixture": render_units,
        },
        "export_errors": export_errors,
        "records": all_records,
    }
    # [V0-I2] assert đĩa == manifest NGAY trong run render (không đợi auditor
    # đếm tay): lệch 1 file PNG cũng FAIL gate với path-mismatch chi tiết.
    png_assert = None
    if not args.no_render:
        png_assert = assert_png_disk_matches_manifest(
            out_root, all_records, fixtures)
        manifest["png_disk_assert"] = png_assert
    mpath = out_root / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    # summary per detector — đếm FAIL DO HARD RULES theo detector
    summary = {}
    detector_keys = ("D1_source_indicator", "D2_field_code", "D3_markers",
                     "D4_contamination", "D5_blank_sparse", "D6_signature",
                     "D9_table_grid", "D10_matrix_headers", "D11_glue",
                     "D12_fixture_violations",
                     # [6V-V1/Lead] detector mới — vẫn candidates (không
                     # hard) tới khi V2 xong; đếm ở đây để số hard luôn
                     # hiện diện trong summary ngay khi Lead nâng hard.
                     "D13_skeleton_glue", "D14_name_slot", "D15_chk_glyph",
                     "D16_token_values", "D17_header_name",
                     "D18_row_placement")
    for key in detector_keys:
        summary[key] = sum(
            1 for r in all_records
            if any(f["detector"] == key or f["detector"].startswith(key)
                   for f in r.get("gate_fails", [])))

    # [V0-I3] summary HAI LỚP trung thực: hard-fail và candidate là hai con
    # số khác nhau. Lớp cũ chỉ đếm hard-fail nên in "D9_table_grid: 0" trong
    # khi det_table_grid vẫn bắt NARROW_COL trên corpus (hit nằm
    # gate_candidates) — gây hiểu sai "không còn finding" (bài học G-E2).
    # Detector lấy từ chính gate_fails/gate_candidates nên detector tương lai
    # (D13+) tự xuất hiện, không phải khai báo lại.
    hard_fail_counts: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}
    candidate_ids: list[str] = []
    hard_hits = cand_hits = 0
    for r in all_records:
        for f in r.get("gate_fails", []):
            k = f["detector"]
            hard_fail_counts[k] = hard_fail_counts.get(k, 0) + 1
            hard_hits += 1
        has_cand = False
        for c in r.get("gate_candidates", []):
            k = c["detector"]
            candidate_counts[k] = candidate_counts.get(k, 0) + 1
            cand_hits += 1
            has_cand = True
        if has_cand:
            candidate_ids.append("%s/%s/%s" % (r["fixture"],
                                               r.get("tag") or "main",
                                               r["form"]))
    n_fail = sum(1 for r in all_records if r["gate_verdict"] == "FAIL")
    summary["hard_fail_counts"] = hard_fail_counts
    summary["hard_fail_hits"] = hard_hits
    summary["hard_fail_total_records"] = n_fail
    summary["candidate_counts"] = candidate_counts
    summary["candidate_hits"] = cand_hits
    summary["candidate_total_records"] = len(candidate_ids)
    summary["candidate_ids"] = candidate_ids
    summary["records"] = len(all_records)
    summary["gate_fail_records"] = n_fail
    summary["export_errors"] = len(export_errors)
    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    # Hai dòng riêng, đọc ngay được: không bao giờ chỉ in "0 hard-fail" khi
    # corpus còn candidate chưa adjudicate (G-E2).
    print("HARD-FAIL: %d" % summary["hard_fail_total_records"])
    print("CANDIDATES: %d" % summary["candidate_total_records"])
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if png_assert is not None:
        print("PNG-DISK-ASSERT: claimed=%d disk=%d ok=%s"
              % (png_assert["claimed"], png_assert["disk"], png_assert["ok"]))
        for mm in png_assert["mismatches"]:
            print("  PATH-MISMATCH %s claimed=%d disk=%d"
                  % (mm["dir"], mm["claimed"], mm["disk"]))
    print("manifest:", mpath)
    png_bad = png_assert is not None and not png_assert["ok"]
    return 2 if (n_fail or export_errors or png_bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
