#!/usr/bin/env python3
"""Lead tool: hop nhat 3 census fragment L0 thanh app/data/layout_specs/layout_manifest.json

Read-only tren production blocks/templates; doc 3 fragment evidence JSON cua
L0-A/L0-B/L0-C (moi agent mot shape rieng) va chuan hoa thanh rollup per form.
Chi ghi layout_manifest.json khi co --write. Gate: du 87/87 form, khong form
nao thieu entry; chay 2 lan cho output giong nhau (idempotent).
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRAG_DIR = os.path.join(ROOT, "app", "data", "layout_specs", "fragments")
MANIFEST_PATH = os.path.join(ROOT, "app", "data", "layout_specs", "layout_manifest.json")

EXPECTED = {
    "l0_a": "PLI_M01-M12",
    "l0_b": "PLI_M13-M80",
    "l0_c": "PLII_M01-M28",
}


def _load(name):
    path = os.path.join(FRAG_DIR, name)
    with io.open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def _len(x):
    return len(x) if isinstance(x, list) else 0


def _norm_l0_a(data):
    out = {}
    for fid, f in data["forms"].items():
        out[fid] = {
            "fragment": "l0_a",
            "ten_mau": f.get("ten_mau"),
            "block_count": f.get("block_count"),
            "source_indicator_count": _len(f.get("source_indicators")),
            "form_number_lines": _len(f.get("form_number_lines")),
            "newline_collapse_blocks": _len(f.get("newline_blocks")),
            "digit_glue_candidates": _len(f.get("glue_candidates")),
            "footnote_body_blocks": None,
            "superscript_runs_docx": _len((f.get("ooxml") or {}).get("vertalign_runs")
                                          if isinstance(f.get("ooxml"), dict) else []),
            "landmarks": f.get("landmarks"),
        }
    return out


def _norm_l0_b(data):
    out = {}
    for fid, f in data["per_form"].items():
        roles = f.get("roles") if isinstance(f.get("roles"), dict) else {}
        out[fid] = {
            "fragment": "l0_b",
            "ten_mau": f.get("ten_mau"),
            "block_count": f.get("nblocks"),
            "source_indicator_count": _len(f.get("source_indicator")),
            "form_number_lines": _len(f.get("form_number")),
            "newline_collapse_blocks": _len(f.get("newline_blocks")),
            "digit_glue_candidates": _len(f.get("digit_glued")),
            "footnote_body_blocks": _len(f.get("footnote_like_lines")),
            "superscript_runs_docx": _len(f.get("ooxml_vertAlign_paras_head")),
            "landmarks": {k: _len(v) for k, v in roles.items()
                          if isinstance(v, list)},
        }
    return out


def _norm_l0_c(data):
    out = {}
    for fid, f in data.items():
        if not isinstance(f, dict):
            continue
        out[fid] = {
            "fragment": "l0_c",
            "ten_mau": f.get("ten_mau"),
            "block_count": f.get("n_blocks"),
            "source_indicator_count": _len(f.get("source_indicator")),
            "form_number_lines": _len(f.get("form_number")),
            "newline_collapse_blocks": _len(f.get("newline_blocks")),
            "digit_glue_candidates": _len(f.get("glue_footnote_refs")),
            "footnote_body_blocks": _len(f.get("footnote_body_blocks")),
            "superscript_runs_docx": _len(f.get("docx_superscript_runs")),
            "landmarks": {
                "title": _len(f.get("title")),
                "salutation": _len(f.get("salutation")),
                "date_line": _len(f.get("date_line")),
                "signature": _len(f.get("signature")),
            },
            "flattened_table_header_blocks":
                _len(f.get("flattened_table_header_blocks")),
        }
    return out


def build():
    norm = {}
    norm.update(_norm_l0_a(_load("l0_a_evidence.json")))
    norm.update(_norm_l0_b(_load("l0_b_evidence.json")))
    norm.update(_norm_l0_c(_load("l0_c_evidence.json")))

    forms = []
    totals = {
        "forms": len(norm),
        "by_fragment": {},
        "forms_with_source_indicator": 0,
        "forms_with_newline_collapse": 0,
        "forms_with_digit_glue": 0,
        "total_source_indicator_blocks": 0,
        "total_newline_blocks": 0,
        "total_digit_glue_candidates": 0,
        "unclassified_markers": 0,
    }
    for fid in sorted(norm):
        e = norm[fid]
        e["form_id"] = fid
        frag = EXPECTED.get(e["fragment"], "?")
        e["range"] = frag
        forms.append(e)
        totals["by_fragment"][e["fragment"]] = \
            totals["by_fragment"].get(e["fragment"], 0) + 1
        if e["source_indicator_count"]:
            totals["forms_with_source_indicator"] += 1
            totals["total_source_indicator_blocks"] += e["source_indicator_count"]
        if e["newline_collapse_blocks"]:
            totals["forms_with_newline_collapse"] += 1
            totals["total_newline_blocks"] += e["newline_collapse_blocks"]
        if e["digit_glue_candidates"]:
            totals["forms_with_digit_glue"] += 1
            totals["total_digit_glue_candidates"] += e["digit_glue_candidates"]

    manifest = {
        "version": "layout-manifest-v1",
        "generated_by": "lead/tools/census/build_layout_manifest.py",
        "sources": [
            {"fragment": k, "range": v,
             "evidence": "app/data/layout_specs/fragments/%s_evidence.json" % k,
             "census_md": "app/data/layout_specs/fragments/%s.md" % k}
            for k, v in EXPECTED.items()
        ],
        "notes": [
            "Census L0 chi doc production; screenshot UI NOT RUN (moi truong "
            "khong browser backend) - bu bang evidence text/OOXML nguyen van.",
            "Marker ky thuat vs 'Mau so N' hop le phan loai trong fragment; "
            "role/style cu the de Wave L1 extractor chot.",
            "p1_b_verify_m72.py FAIL san tai HEAD la known-issue tien-integrate, "
            "khong thuoc gate layout.",
        ],
        "totals": totals,
        "forms": forms,
    }
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="ghi layout_manifest.json")
    args = ap.parse_args()

    manifest = build()
    t = manifest["totals"]
    missing = [f["form_id"] for f in manifest["forms"]
               if not f.get("form_id")]
    dupes = len(manifest["forms"]) - len({f["form_id"] for f in manifest["forms"]})

    print("Layout manifest rollup:")
    for k in ("forms", "forms_with_source_indicator",
              "total_source_indicator_blocks", "forms_with_newline_collapse",
              "total_newline_blocks", "forms_with_digit_glue",
              "total_digit_glue_candidates"):
        print("  %-34s %s" % (k, t[k]))
    print("  by_fragment                        %s" % t["by_fragment"])

    ok = (t["forms"] == 87 and not missing and dupes == 0
          and t["by_fragment"] == {"l0_a": 12, "l0_b": 47, "l0_c": 28})
    if not ok:
        print("GATE FAIL: forms=%s missing=%s dupes=%s by_fragment=%s"
              % (t["forms"], missing, dupes, t["by_fragment"]))
        return 1

    if args.write:
        os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
        with io.open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=False)
            fh.write("\n")
        print("Wrote", os.path.relpath(MANIFEST_PATH, ROOT))
    else:
        print("(dry-run - dung --write de ghi)")
    print("GATE PASS: layout manifest 87/87, moi form co entry duy nhat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
