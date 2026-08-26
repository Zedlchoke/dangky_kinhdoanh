# -*- coding: utf-8 -*-
"""Census T0-B (CHỈ ĐỌC) cho PLI_M13..M80.

Với từng mẫu trong phạm vi, đối chiếu 3 nguồn:
  1. app/data/blocks/<id>.json     - block 'p'/'chk'/'table'/'loop'
  2. DOCX nguồn gốc (thư mục số ở root, cùng luật chọn file với
     build_form_maps.find_source: thư mục 02->06, file đầu tiên thắng)
  3. app/data/form_maps.json       - entry fields/dynamic_tables

Script không ghi/sửa bất kỳ file production nào. Kết quả ghi ra --out
(mặc định ngoài repo) để agent phân loại viết fragment t0_b.json.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
SOURCE_FOLDERS = [
    "01_dang_ky_thanh_lap_doanh_nghiep",
    "02_thay_doi_thong_tin_doanh_nghiep",
    "03_chi_nhanh_van_phong_dai_dien_dia_diem",
    "04_tam_ngung_cham_dut_giai_the",
    "05_cong_bo_cung_cap_thong_tin",
    "06_ho_kinh_doanh_va_chuyen_doi",
]
RANGE = (13, 80)

SIGNATURE_MARKERS = [
    "chu ky", "nguoi dai dien", "truong don vi", "(ky", "ky ten",
    "ky, ghi ho ten", "nguoi uy quyen", "chu ho", "dai dien hop phap",
]
DECISION_MARKERS = ["quyet dinh"]


def fold(text):
    norm = unicodedata.normalize("NFD", text or "")
    no_mark = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", no_mark.replace("đ", "d").replace("Đ", "D")).strip().lower()


def parse_form_id(path):
    m = re.match(r"(?:DN_)?PL(\d)_Mau_(\d+)", path.stem)
    if not m:
        return None, None
    pl = "I" if m.group(1) == "1" else "II"
    return f"PL{pl}_M{int(m.group(2)):02d}", int(m.group(2))


def iter_source_docx():
    for folder in SOURCE_FOLDERS:
        d = ROOT / folder
        if d.is_dir():
            yield from sorted(p for p in d.rglob("*.docx")
                              if not p.name.startswith("~$") and not p.name.startswith("_"))


def find_sources(form_id):
    """Trả về (canonical_path, [mọi path trùng]). File đầu tiên thắng như find_source."""
    hits = []
    for path in iter_source_docx():
        fid, _ = parse_form_id(path)
        if fid == form_id:
            hits.append(path)
    return (hits[0] if hits else None), hits[1:]


def table_inventory(tbl):
    rows_xml = tbl.findall(qn("w:tr"))
    n_rows = len(rows_xml)
    grid_cols = len(tbl.findall(qn("w:tblGrid") + "/" + qn("w:gridCol")))
    header_rows = []
    merges = 0
    for ri, tr in enumerate(rows_xml[:3]):
        cells = []
        for tc in tr.findall(qn("w:tc")):
            span = tc.find(qn("w:tcPr") + "/" + qn("w:gridSpan"))
            vmerge = tc.find(qn("w:tcPr") + "/" + qn("w:vMerge"))
            if span is not None or vmerge is not None:
                merges += 1
            txt = " ".join(t.text or "" for t in tc.iter(qn("w:t")))
            cells.append(re.sub(r"\s+", " ", txt).strip())
        header_rows.append(cells)
    return {
        "rows": n_rows,
        "cols": grid_cols,
        "merges": merges,
        "row0": header_rows[0] if header_rows else [],
        "row1": header_rows[1] if len(header_rows) > 1 else None,
        "row2": header_rows[2] if len(header_rows) > 2 else None,
    }


def analyze_docx(path):
    doc = Document(str(path))
    body_children = list(doc.element.body.iterchildren())
    tables = []
    para_markers = []
    sig_hits = set()
    decision_hits = []
    last_context = ""

    para_idx = 0
    for child in body_children:
        if child.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            p = Paragraph(child, doc)
            txt = re.sub(r"\s+", " ", p.text).strip()
            fd = fold(txt)
            if txt:
                last_context = txt
                if re.match(r"^stt$", fd):
                    para_markers.append({"i": para_idx, "kind": "stt_alone", "text": txt[:120]})
                elif re.match(r"^stt(?=[^\s\d.)])", fd):
                    para_markers.append({"i": para_idx, "kind": "stt_joined", "text": txt[:160]})
                elif re.match(r"^(danh sach|liet ke)\b", fd) or re.match(r"^cac\b.{0,60}\bsau\b", fd):
                    para_markers.append({"i": para_idx, "kind": "list_intro", "text": txt[:160]})
                elif re.match(r"^6\.\d+", fd):
                    para_markers.append({"i": para_idx, "kind": "tax_indicator", "text": txt[:120]})
                elif any(m in fd for m in DECISION_MARKERS) and len(txt) < 90:
                    decision_hits.append(txt[:90])
                if any(m in fd for m in SIGNATURE_MARKERS):
                    sig_hits.add(txt[:80])
            para_idx += 1
        elif child.tag == qn("w:tbl"):
            inv = table_inventory(child)
            inv["context"] = last_context[:140]
            tables.append(inv)

    # bảng lồng nhau (hiếm) qua doc.tables nếu thiếu so với body-level
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "tables": tables,
        "para_markers": para_markers,
        "signature_lines": sorted(sig_hits)[:12],
        "decision_headings": decision_hits[:6],
    }


def analyze_blocks(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    stats = {"p": 0, "chk": 0, "table": 0, "loop": 0}
    loops = []
    input_keys = []

    def collect_runs(runs):
        for r in runs or []:
            inp = r.get("input")
            if isinstance(inp, dict) and inp.get("key"):
                input_keys.append(inp["key"])

    def walk(blocks):
        for b in blocks:
            t = b.get("t")
            if t in stats:
                stats[t] += 1
            if t == "p":
                collect_runs(b.get("runs"))
            elif t == "table":
                for row in b.get("rows", []):
                    for c in row.get("cells", []):
                        collect_runs(c.get("runs"))
            elif t == "loop":
                loops.append({
                    "loop": b.get("loop"),
                    "header": [" ".join(filter(None, [
                        "".join(rr.get("text", "") for rr in cell.get("runs", []))
                        for cell in row.get("cells", [])
                    ])) for row in b.get("rows", [])],
                    "col_tags": [c.get("tag") for c in b.get("cols", [])],
                    "blankRows": b.get("blankRows"),
                })

    walk(data.get("blocks", []))
    return {
        "stats": stats,
        "loops": loops,
        "input_key_count": len(input_keys),
        "distinct_input_keys": len(set(input_keys)),
    }, data.get("ten_mau", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    maps = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    report = {"generated_by": "t0-b-census", "range": "PLI_M13-M80", "forms": []}

    block_files = sorted(
        BLOCKS_DIR.glob("PLI_M*.json"),
        key=lambda p: int(re.search(r"M(\d+)$", p.stem).group(1)))
    in_range = []
    for bf in block_files:
        num = int(re.search(r"M(\d+)$", bf.stem).group(1))
        fid = bf.stem
        if RANGE[0] <= num <= RANGE[-1]:
            in_range.append(fid)
            blk, ten_mau = analyze_blocks(bf)
            canonical, dupes = find_sources(fid)
            src = analyze_docx(canonical) if canonical else None
            fm = maps.get(fid)
            entry = {
                "form_id": fid,
                "ten_mau": ten_mau,
                "blocks": blk,
                "template_tables": None,
                "source": src,
                "duplicate_sources": [p.relative_to(ROOT).as_posix() for p in dupes],
                "form_maps": None if not fm else {
                    "fields": len(fm.get("fields", [])),
                    "dynamic_tables": fm.get("dynamic_tables"),
                },
            }
            tpl = ROOT / "app" / "templates" / f"{fid}.docx"
            if tpl.exists():
                entry["template_tables"] = len(Document(str(tpl)).tables)
            report["forms"].append(entry)

    missing_blocks = []
    have = set(in_range)
    for path in iter_source_docx():
        fid, mau = parse_form_id(path)
        if fid and mau and RANGE[0] <= mau <= RANGE[-1] \
                and fid.startswith("PLI_M") and fid not in have:
            missing_blocks.append({"form_id": fid, "path": path.relative_to(ROOT).as_posix()})
    report["forms_without_blocks_in_range"] = missing_blocks
    report["counts"] = {
        "forms_with_blocks": len(report["forms"]),
        "source_files_scanned": sum(1 for _ in iter_source_docx()),
    }

    out = Path(args.out) if args.out else Path(__file__).with_name("t0_b_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[t0-b] forms={len(report['forms'])} "
          f"sources={report['counts']['source_files_scanned']} "
          f"report={out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
