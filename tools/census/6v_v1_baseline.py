# -*- coding: utf-8 -*-
"""6v_v1_baseline.py — 6V-V1: chốt baseline ĐỎ của D9(mới)/D13/D14/D15/D16
trên corpus kiểm chứng sẵn có (KHÔNG export lại, KHÔNG soffice).

Corpus: generated_ho_so/_visual_layout/phase6v/v0_corpuscheck/
  (455 record = 91 record/fixture × 5 fixture; 87 form, PLI_M72 có 6 tag:
  main + 5 biến thể; mỗi record có .docx + .pdf — manifest.json dẫn đường).

Đầu ra JSON (mặc định tools/census/6v_v1_baseline.json):
  {
    "corpus": {...}, "records_total": 455,
    "detectors": {
      "D13_skeleton_glue": {"records": N, "hits": M, "forms": [...],
                            "per_fixture": {...}, "per_form": {...},
                            "audit_expectation": "~303 hit / ~55 form"},
      ... D14/D15/D16/D9_table_grid ...
    }
  }

Chạy:  python3 -X utf8 -m tools.census.6v_v1_baseline [--corpus DIR]
       [--out FILE] [--max-details N]
Exit 0 luôn (script đo lường, không phán verdict — verdict thuộc
test_phase6v_detectors pin số).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

import tools.phase5_visual_gate as gate  # noqa: E402

MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
DEFAULT_CORPUS = (ROOT / "generated_ho_so" / "_visual_layout" / "phase6v"
                  / "v0_corpuscheck")
# worktree không mang theo generated_ho_so (gitignore) — rơi về checkout
# chính nằm cạnh cây worktrees
MAIN_CHECKOUT_CORPUS = (ROOT.parent.parent / "dangky_kinhdoanh"
                        / "generated_ho_so" / "_visual_layout" / "phase6v"
                        / "v0_corpuscheck")

AUDIT_EXPECT = {
    "D13_skeleton_glue": "~303 hit / ~55 form (B1) — mọi fixture",
    "D14_name_slot": "~37/72 form có slot (B2); 48/87 bind đúng",
    "D15_chk_glyph": "mọi form có field type=chk (B3)",
    "D16_token_values": "~938 hit / ~73 form (B4) — mạnh ở long-boundary",
    "D9_table_grid": "~60 bảng / ~10 form (B5) — PLII_M01/02, "
                     "PLI_M02/06/07/09/10/12/15/72",
}


def resolve_corpus(cli: str | None) -> Path:
    if cli:
        return Path(cli)
    if (DEFAULT_CORPUS / "manifest.json").exists():
        return DEFAULT_CORPUS
    if (MAIN_CHECKOUT_CORPUS / "manifest.json").exists():
        return MAIN_CHECKOUT_CORPUS
    raise SystemExit("không tìm thấy corpus v0_corpuscheck (thử --corpus)")


def pdf_pages_text(pdf_path: Path) -> list[dict]:
    doc = pymupdf.open(str(pdf_path))
    return [{"pno": p.number, "text": p.get_text("text")} for p in doc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="")
    ap.add_argument("--out", default=str(
        ROOT / "tools" / "census" / "6v_v1_baseline.json"))
    ap.add_argument("--max-details", type=int, default=5,
                    help="số sample hit lưu tối đa per form trong JSON")
    args = ap.parse_args()

    corpus = resolve_corpus(args.corpus or None)
    manifest = json.loads((corpus / "manifest.json").read_text("utf-8"))
    records = manifest["records"]
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    registry = gate.load_handwriting_slots()

    agg: dict[str, dict] = {}
    for det in AUDIT_EXPECT:
        agg[det] = {
            "records": 0, "hits": 0, "forms": set(),
            "per_fixture": collections.defaultdict(lambda: [0, 0]),
            "per_form": collections.defaultdict(
                lambda: {"records": 0, "hits": 0, "codes": {},
                         "samples": []}),
        }

    def tally(det: str, rec: dict, issues: list, codes_of=None):
        if not issues:
            return
        a = agg[det]
        a["records"] += 1
        a["hits"] += len(issues)
        a["forms"].add(rec["form"])
        fx = a["per_fixture"][rec["fixture"]]
        fx[0] += 1
        fx[1] += len(issues)
        pf = a["per_form"][rec["form"]]
        pf["records"] += 1
        pf["hits"] += len(issues)
        for it in issues:
            code = (codes_of(it) if codes_of else (it or {}).get("code"))
            pf["codes"][code] = pf["codes"].get(code, 0) + 1
        pf["samples"] = [
            (codes_of(x) if codes_of else (x or {}).get("code"))
            + ": " + json.dumps(x, ensure_ascii=False)[:90]
            for x in issues[:args.max_details]]

    t0 = datetime.now()
    for i, rec in enumerate(records):
        # manifest ghi đường dẫn relative với REPO ROOT
        docx = Path(rec["docx"])
        pdf = Path(rec["pdf"])
        if not docx.is_absolute():
            docx = ROOT / docx
            pdf = ROOT / pdf
        pages = pdf_pages_text(pdf)
        fid = rec["form"]

        skel = gate.det_skeleton_glue(docx, pages)
        tally("D13_skeleton_glue", rec, skel,
              codes_of=lambda x: x["code"])

        if rec["fixture"] == "valid-full":
            nslot = gate.det_name_slot(pages, fid, registry)
            tally("D14_name_slot", rec, nslot, codes_of=lambda x: x["kind"])

        if rec["fixture"] == "choice-variants":
            chk = gate.det_chk_glyph(docx, pages, maps[fid])
            tally("D15_chk_glyph", rec, chk, codes_of=lambda x: x["code"])

        toks = gate.det_token_values(pages)
        tally("D16_token_values", rec, toks, codes_of=lambda x: x["code"])

        grid = gate.det_table_grid(docx)
        tally("D9_table_grid", rec, grid, codes_of=lambda x: x["code"])
        if (i + 1) % 100 == 0:
            print("  … %d/%d record (%.0fs)" % (
                i + 1, len(records), (datetime.now() - t0).total_seconds()),
                file=sys.stderr)

    out = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "corpus": {
            "path": str(corpus),
            "records": len(records),
            "note": "v0_corpuscheck render post-V0 @313b0af; template "
                    "giống hệt audit-HEAD 294604c (git diff rỗng với "
                    "app/templates) — mọi lệch số audit là khác biệt "
                    "grammar/đơn vị đếm, bảng per_form để đối chiếu",
        },
        "detectors": {},
    }
    for det, a in agg.items():
        out["detectors"][det] = {
            "records": a["records"], "hits": a["hits"],
            "forms": sorted(a["forms"]),
            "audit_expectation": AUDIT_EXPECT[det],
            "per_fixture": {k: {"records": v[0], "hits": v[1]}
                            for k, v in sorted(a["per_fixture"].items())},
            "per_form": {k: v for k, v in sorted(a["per_form"].items())},
        }
    out["d14_forms_with_slot"] = sorted({
        r["form"] for r in records if r["fixture"] == "valid-full"
        and _has_slot(ROOT / r["pdf"])})

    outp = Path(args.out)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print("%-22s %8s %8s %6s" % ("detector", "records", "hits", "forms"))
    for det, d in out["detectors"].items():
        print("%-22s %8d %8d %6d   %s" % (
            det, d["records"], d["hits"], len(d["forms"]),
            d["audit_expectation"]))
    print("D14 forms có slot (valid-full):", len(out["d14_forms_with_slot"]))
    print("JSON:", outp)
    return 0


def _has_slot(pdf_path: Path) -> bool:
    """Có ít nhất 1 slot tên khớp grammar D14 ở trang 1 (đếm forms có slot)."""
    pages = pdf_pages_text(pdf_path)
    if not pages:
        return False
    for raw in pages[0]["text"].split("\n"):
        f = gate._fold(raw.strip())
        if not f:
            continue
        mi = gate._D14_INLINE.match(f)
        mp = gate._D14_PAREN.match(f)
        if (mi and not gate._D14_NOISE.search(f[:f.find(":")])) or \
                (mp and not gate._D14_NOISE.search(mp.group(1))):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
