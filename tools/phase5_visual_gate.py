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

# ngưỡng detector (twips = 1/1440 inch; 567 twips = 1 cm)
MIN_COL_TWIPS = 567          # cột hẹp hơn 1 cm → chữ vỡ (WLAY-008)
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
                "variant": "m72" if d.name.startswith("p5r_") and "m72" in d.name else "",
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
                # fixture exclusivity (D12)
                fdata = build_fixture(fid, maps[fid], fixture,
                                      blocks_all.get(fid), ValueFactory())
                rec["detectors"]["D12_fixture_violations"] = validate_fixture(
                    maps[fid], blocks_all.get(fid) or {}, fdata, fixture)
                # render PNG
                if render_pages:
                    pdir = out_root / fixture / fid
                    pdir.mkdir(parents=True, exist_ok=True)
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
    n_fail = sum(1 for r in all_records if r["gate_verdict"] == "FAIL")
    summary["records"] = len(all_records)
    summary["gate_fail_records"] = n_fail
    summary["export_errors"] = len(export_errors)
    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("manifest:", mpath)
    return 2 if (n_fail or export_errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
