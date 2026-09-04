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
    FIXTURES, M72_VARIANTS, ValueFactory, build_fixture, validate_fixture,
)

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
SIG_WRITE_PT = 40            # vùng viết tối thiểu dưới instruction (WLAY-004)
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
    """D9: grid width — cột < 1cm hoặc tổng width vượt khổ in được.
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
        narrow = [(i, w) for i, w in enumerate(cols) if w < MIN_COL_TWIPS]
        total = sum(cols)
        if narrow:
            issues.append({"table": ti, "code": "NARROW_COL",
                           "cols": narrow, "total": total})
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
        pages.append({"pno": pno, "text": text, "words": words, "pixmap": pix})
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
_SIG_INSTR_FOLD = re.compile(
    r"\((ky va ghi ro ho ten|ky ghi ro ho ten|ky va ghi ho ten|ky ten|"
    r"ky, ghi ro ho ten|ky, ho ten|ky ho ten|da ky|ky, ho ten, dong dau|"
    r"ky ten, dong dau)\b")


def _sig_lines(page) -> list[dict]:
    """Gom words thành dòng; đánh dấu title/instruction chữ ký. Title nhận
    theo 2 đường: (a) vocabulary nhãn người ký; (b) dòng CHỮ IN ngắn kề trên
    instruction (caps-ratio >= 0.6, <= 80 ký tự) — vocabulary không thể liệt
    kê hết nhãn pháp lý (M14: 'NGƯỜI ĐƯỢC TẶNG CHO/NGƯỜI THỪA KẾ/NGƯỜI MUA')."""
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
        out.append({"text": text, "fold": f, "x0": x0, "x1": x1,
                    "y0": y0, "y1": y1,
                    "title": bool(_SIG_TITLE_FOLD.match(f))
                    or (caps >= 0.6 and len(text.strip()) <= 80
                        and not _SIG_INSTR_FOLD.search(f)),
                    "instr": bool(_SIG_INSTR_FOLD.search(f))})
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
        "x0": c["instr"]["x0"]} for c in clusters],
        "fails": [], "candidates": []}

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
    # D8 vùng viết: khoảng dọc từ instr xuống dòng text kế tiếp trong cùng cột.
    # Registry khai min_write_gap_pt cho form → thiếu vùng viết là FAIL (P0,
    # WLAY-004); form chưa có registry chỉ census CANDIDATE.
    min_gap = float(((expectations.get(fid) or {}).get("signature") or {})
                    .get("min_write_gap_pt") or 0)
    for p in pages:
        lines = _sig_lines(p)
        for c in clusters:
            if c["page"] != p["pno"] + 1:
                continue
            instr = c["instr"]
            below = [l for l in lines
                     if l["y0"] > instr["y1"] + 2
                     and not (l["x1"] < instr["x0"] - 60 or
                              l["x0"] > instr["x1"] + 60)
                     and not (l["title"] or l["instr"])]
            if below:
                nearest = min(below, key=lambda l: l["y0"])
                gap = nearest["y0"] - instr["y1"]
                item = {"code": "SIG_WRITE_SPACE", "page": p["pno"] + 1,
                        "gap_pt": round(gap, 1),
                        "instr": instr["text"][:50]}
                if min_gap and gap < min_gap:
                    res["fails"].append(item)
                elif gap < SIG_WRITE_PT:
                    res["candidates"].append(item)
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


# nạp 1 lần sau khi hàm load đã định nghĩa (registry adjudicate ở C2/V4)
HANDWRITING_SLOTS = load_handwriting_slots()


# [6V-V1] D15 — chk glyph (lớp B3). Chạy trên fixture choice-variants với
# form có field type=chk. Tick hợp pháp = X trong ô vuông: glyph ☒ trong
# cùng paragraph, HOẶC X nằm trong w:tc có viền hiển thị (tcBorders/
# tblBorders val single/thick/…). "X" trần trong paragraph thường, X trong
# cell KHÔNG viền, X cạnh glyph ô trống ☐, và "X" rơi dòng riêng (PDF) đều
# là finding. Câu hướng dẫn "(đánh dấu X vào ô thích hợp)" có X giữa câu —
# loại bằng rule vị trí (X chỉ tính ở ĐẦU/CUỐI paragraph) + từ khoá hướng
# dẫn đứng kề.
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
    # PDF: "X" rơi dòng riêng (XML cùng paragraph nhưng PDF wrap tách dòng)
    for p in pages:
        for ln in p["text"].split("\n"):
            if ln.strip() == "X":
                issues.append({"page": p["pno"] + 1, "code": "X_OWN_LINE",
                               "paragraph": ""})
    return issues


# nạp 1 lần sau khi hàm load đã định nghĩa (registry adjudicate ở C2/V4)
HANDWRITING_SLOTS = load_handwriting_slots()


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

def build_all_data(maps: dict, blocks_all: dict, fixture: str) -> dict:
    """Gộp data mọi form cho một batch export (key unique per form giữ giá trị
    riêng; key chung — ngày ký, cơ quan… — nhận giá trị cuối, cùng ngữ nghĩa)."""
    merged: dict = {}
    for fid in sorted(maps):
        merged.update(build_fixture(fid, maps[fid], fixture,
                                    blocks_all.get(fid), ValueFactory()))
    return merged


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
        data = {}
        for fid in ids:
            data.update(build_fixture(fid, maps[fid], fixture,
                                      blocks_all.get(fid), ValueFactory()))
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

            # --- PDF detectors
            if pdf_path.exists():
                _doc, pages = pdf_pages(pdf_path, zoom)
                rec["page_count"] = len(pages)
                rec["detectors"]["D5_blank_sparse"] = det_blank_sparse(pages)
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
                # [6V-V1] D15 chk glyph — contract fixture choice-variants
                # (mọi nhóm loại trừ có đúng 1 lựa chọn được tick)
                rec["detectors"]["D15_chk_glyph"] = (
                    det_chk_glyph(docx_path, pages, maps[fid])
                    if fixture == "choice-variants" else [])
                # fixture exclusivity (D12)
                fdata = build_fixture(fid, maps[fid], fixture,
                                      blocks_all.get(fid), ValueFactory())
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
}


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
                # registry/contract (orientation, split, write-space theo
                # min_write_gap_pt) — toàn bộ là hard; candidates là census.
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
                        candidates.append({"detector": key, "detail": item})
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
                                                "phase5r_blank_page_allowlist.json"))
    args = ap.parse_args()

    fixtures = [f.strip() for f in args.fixtures.split(",") if f.strip()]
    for f in fixtures:
        if f not in FIXTURES:
            print("fixture không hợp lệ: %r" % f)
            return 2
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    if args.forms == "all":
        form_ids = sorted(maps)
    else:
        form_ids = [f.strip() for f in args.forms.split(",") if f.strip()]
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
                     "D12_fixture_violations")
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
