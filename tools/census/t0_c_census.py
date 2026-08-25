# -*- coding: utf-8 -*-
"""T0-C census: PLII_M01-M28 table inventory (read-only on production).

Cross-references three sources per form:
  1. app/data/blocks/PLII_*.json  (generated blocks: p/chk/table/loop)
  2. app/templates/PLII_M*.docx   (python-docx / w:tbl structure)
  3. app/data/form_maps.json      (fields + loops mapping)

Writes a machine-readable evidence dump to stdout (or --out FILE).
Production files are never modified.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCKS_DIR = os.path.join(ROOT, "app", "data", "blocks")
TEMPLATES_DIR = os.path.join(ROOT, "app", "templates")
FORM_MAPS = os.path.join(ROOT, "app", "data", "form_maps.json")

FORM_IDS = ["PLII_M%02d" % i for i in range(1, 29)]

STT_RE = re.compile(r"^\s*STT\b")
GLUED_STT_RE = re.compile(r"^STT[A-ZÀ-Ỹ]")
LIST_HINT_RE = re.compile(r"\b(Danh sách|Liệt kê|Các|Danh sách các|liệt kê)\b.{0,60}(sau|dưới đây)", re.I)
TAX_RE = re.compile(r"\b[56]\.\d+\b")
SIGNATURE_RE = re.compile(r"(Chữ ký|Ký và ghi họ tên|Ký, ghi họ tên|NGƯỜI ĐẠI DIỆN|CHỦ HỘ|ĐẠI DIỆN)", re.I)


def iter_body_items(doc):
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            yield ("p", Paragraph(child, doc))
        elif tag == "tbl":
            yield ("tbl", Table(child, doc))


def grid_span(cell):
    tc_pr = cell._tc.tcPr
    span = 1
    vmerge = None
    if tc_pr is not None:
        gs = tc_pr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}gridSpan")
        if gs is not None:
            span = int(gs.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"))
        vm = tc_pr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vMerge")
        if vm is not None:
            vmerge = vm.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") or "continue"
    return span, vmerge


def describe_table(tbl, idx):
    n_rows = len(tbl.rows)
    grid_cols = len(tbl.columns)
    header_rows = []
    merges = []
    data_rows_with_input = 0
    empty_data_rows = 0
    tags_in_table = []
    for ri, row in enumerate(tbl.rows):
        cells_txt = []
        seen = set()
        row_has_input = False
        for ci, cell in enumerate(row.cells):
            key = id(cell._tc)
            span, vmerge = grid_span(cell)
            if span > 1 or vmerge is not None:
                merges.append({"r": ri, "c": ci, "span": span, "vmerge": vmerge})
            txt = cell.text.strip().replace("\n", "\\n")
            has_tag = "{" in txt and "}" in txt
            if has_tag:
                tags_in_table.extend(re.findall(r"\{([^{}]+)\}", txt))
                row_has_input = True
            if key not in seen:
                seen.add(key)
                cells_txt.append(txt[:40])
        joined = " | ".join(cells_txt).strip()
        if ri <= 2 and joined:
            header_rows.append({"row": ri, "cells": joined})
        if ri > 0 and row_has_input:
            data_rows_with_input += 1
        if ri > 0 and not joined.replace("|", "").strip():
            empty_data_rows += 1
    return {
        "index": idx,
        "rows": n_rows,
        "grid_cols": grid_cols,
        "header_preview": header_rows[:3],
        "merges": merges[:12],
        "n_merges": len(merges),
        "data_rows_with_input_tags": data_rows_with_input,
        "empty_data_rows": empty_data_rows,
        "tags": sorted(set(tags_in_table)),
    }


def scan_docx(path):
    import docx
    doc = docx.Document(path)
    tables = []
    paragraphs = []
    last_heading = ""
    idx = -1
    for kind, obj in iter_body_items(doc):
        if kind == "p":
            txt = obj.text.strip()
            if txt:
                paragraphs.append(txt)
                if not txt.startswith(("{", "-")):
                    last_heading = txt
        else:
            idx += 1
            desc = describe_table(obj, idx)
            prev = [p for p in paragraphs[-3:]]
            desc["preceding_paragraphs"] = prev
            desc["heading"] = last_heading[:160]
            tables.append(desc)
    glued = [p for p in paragraphs if GLUED_STT_RE.match(p)]
    stt_paras = [p for p in paragraphs if STT_RE.match(p) and not GLUED_STT_RE.match(p)]
    list_hints = [p for p in paragraphs if LIST_HINT_RE.search(p)]
    tax_paras = [p for p in paragraphs if TAX_RE.search(p) and len(p) < 300]
    sig_paras = [p for p in paragraphs if SIGNATURE_RE.search(p)][:8]
    return {
        "tables": tables,
        "stt_paragraphs": stt_paras[:20],
        "glued_stt_paragraphs": glued[:20],
        "list_hint_paragraphs": list_hints[:20],
        "tax_indicator_paragraphs": tax_paras[:25],
        "signature_paragraphs": sig_paras,
        "n_paragraphs": len(paragraphs),
    }


def scan_blocks(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    counts = {"p": 0, "chk": 0, "table": 0, "loop": 0}
    loops = []
    stt_paras = []
    list_hints = []
    tax_paras = []
    inputs_total = 0
    keys = set()
    chk_keys = set()
    for b in d["blocks"]:
        t = b.get("t", "p")
        counts[t] = counts.get(t, 0) + 1
        if t == "p":
            text = "".join(r.get("text", "") for r in b.get("runs", []) if r.get("text"))
            for r in b.get("runs", []):
                inp = r.get("input")
                if inp and inp.get("key"):
                    inputs_total += 1
                    keys.add(inp["key"])
                if r.get("chk"):
                    chk_keys.add((r["chk"] or {}).get("key", ""))
            if STT_RE.match(text):
                stt_paras.append(text[:120])
            elif GLUED_STT_RE.match(text):
                stt_paras.append("[GLUED] " + text[:120])
            if LIST_HINT_RE.search(text):
                list_hints.append(text[:140])
            if TAX_RE.search(text) and len(text) < 250:
                tax_paras.append(text[:150])
        elif t == "chk":
            chk_keys.add(b.get("key", ""))
        elif t == "loop":
            cols = [{"col": c.get("col"), "tag": c.get("tag")} for c in b.get("cols", [])]
            hdr_cells = []
            for row in b.get("rows", []):
                hdr_cells.append([c["runs"][0]["text"] if c.get("runs") else "" for c in row.get("cells", [])])
            loops.append({
                "name": b.get("loop"),
                "cols": cols,
                "headerRows": b.get("headerRows"),
                "blankRows": b.get("blankRows"),
                "headers": hdr_cells,
            })
    return {
        "ten_mau": d.get("ten_mau"),
        "counts": counts,
        "loops": loops,
        "stt_paragraphs": stt_paras,
        "list_hint_paragraphs": list_hints,
        "tax_indicator_paragraphs": tax_paras,
        "n_inputs": inputs_total,
        "chk_count": len(chk_keys),
    }


def scan_form_maps(fm, form_id):
    entry = fm.get(form_id)
    if not entry:
        return None
    loop_fields = {}
    plain_fields = []
    chk_fields = []
    for f in entry.get("fields", []):
        key = f.get("key", "")
        if f.get("type") == "chk":
            chk_fields.append(key)
        elif "." in key:
            base = key.split(".")[0]
            loop_fields.setdefault(base, []).append(key.split(".", 1)[1])
        else:
            plain_fields.append(key)
    return {
        "template": entry.get("template"),
        "file": entry.get("file"),
        "n_fields": len(entry.get("fields", [])),
        "loops": {k: sorted(set(v)) for k, v in loop_fields.items()},
        "chk": sorted(set(chk_fields)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(FORM_MAPS, encoding="utf-8") as fh:
        fm = json.load(fh)
    report = {"generated_by": "t0-c-census", "forms": {}}
    for form_id in FORM_IDS:
        blocks_path = os.path.join(BLOCKS_DIR, form_id + ".json")
        tpl_path = os.path.join(TEMPLATES_DIR, form_id + ".docx")
        entry = {
            "blocks": scan_blocks(blocks_path) if os.path.exists(blocks_path) else {"missing": True},
            "docx": scan_docx(tpl_path) if os.path.exists(tpl_path) else {"missing": True},
            "form_maps": scan_form_maps(fm, form_id),
        }
        report["forms"][form_id] = entry
    out_json = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out_json)
        print("written:", args.out)
    else:
        sys.stdout.write(out_json + "\n")


if __name__ == "__main__":
    main()
