# -*- coding: utf-8 -*-
"""v7_signature_census.py — [WAVE v7] Bằng chứng SIGNATURE-USABILITY-SPACE
trên corpus visual dạng phase7v (baseline phase7v/final: 455 record). Số
record LUÔN đếm từ đĩa (rglob *.pdf) — không pin; kỳ vọng signature đọc từ
registry template-derived tools/phase5r_expectations.json (B1 của
test_phase5r_signatures ép registry == census template).

Ba số phải KHỚP NHAU:
  1. census   — cụm ký tìm bằng NGỮ PHÁP CENSUS RỘNG (test_phase5r_signatures)
  2. detector — cụm ký D6 nhận (det_signatures trên cùng PDF)
  3. space    — 100% cụm CÒN KÝ TAY có gap >= 72pt; "Đã ký" chỉ cần được đo

Expected signature nhưng zero detected = FAIL. Exit 0 = PASS.

Chạy:
  python3 -X utf8 -m tools.census.v7_signature_census \
    --corpus generated_ho_so/_visual_layout/phase7v/final
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import fitz  # noqa: E402

from tools.phase5_visual_gate import (          # noqa: E402
    _fold, _sig_is_instr, _sig_is_daky, det_signatures,
    load_expectations, _sig_lines, _page_lines_of)

# ngữ pháp census RỘNG (mirror tools/test_phase5r_signatures.py)
_SIG_INSTR_FOLD_RE = re.compile(
    r"\((ky va ghi ro ho ten|ky ghi ro ho ten|ky va ghi ho ten|ky ten|"
    r"ky, ghi ro ho ten|ky, ho ten|ky ho ten|da ky|ky, ho ten, dong dau|"
    r"ky ten, dong dau|ky, ghi ho ten va dong dau)\b")
_SIG_INSTR_NOPAREN_RE = re.compile(
    r"^ky(,| va)? (ghi ho ten|ghi ro ho ten)( tung thanh vien)?"
    r"( va)?( dong dau)?[0-9]{0,2}$")


def _census_instr_lines(pdf_path: Path) -> int:
    doc = fitz.open(str(pdf_path))
    n = 0
    for page in doc:
        lines = _page_lines_of({"words": page.get_text("words")})
        for ln in lines:
            f = ln["fold"]
            if _SIG_INSTR_FOLD_RE.search(f) or _SIG_INSTR_NOPAREN_RE.match(f):
                n += 1
    doc.close()
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="generated_ho_so/_visual_layout/"
                                        "phase7v/final")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    expectations = load_expectations()
    records = []
    for pdf_path in sorted(corpus.rglob("*.pdf")):
        fixture = pdf_path.relative_to(corpus).parts[0]
        tag = pdf_path.relative_to(corpus).parts[1]
        records.append((fixture, tag, pdf_path.stem, pdf_path))

    total_census = total_det = total_manual = 0
    manual_gaps = []
    daky = 0
    missing = []
    coverage_mismatch = []
    for fixture, tag, fid, pdf_path in records:
        census_n = _census_instr_lines(pdf_path)
        doc = fitz.open(str(pdf_path))
        pages = []
        for pno in range(doc.page_count):
            page = doc[pno]
            pages.append({"pno": pno, "words": page.get_text("words"),
                          "text": page.get_text("text"),
                          "page_bottom": float(page.rect.y1)})
        res = det_signatures(pages, expectations, fid)
        doc.close()
        det_n = len(res["clusters"])
        total_census += census_n
        total_det += det_n
        exp = (expectations.get(fid) or {}).get("signature") or {}
        if int(exp.get("signers") or 0) >= 1 and det_n == 0:
            missing.append("%s/%s/%s" % (fixture, tag, fid))
        if census_n != det_n:
            coverage_mismatch.append("%s/%s/%s census=%d det=%d" % (
                fixture, tag, fid, census_n, det_n))
        # gap stats từ fails/cụm: đo lại gap từng cụm manual
        doc = fitz.open(str(pdf_path))
        for pno in range(doc.page_count):
            page = doc[pno]
            plines = _page_lines_of({"words": page.get_text("words")})
            # dùng cùng bộ line objects của D8 qua _sig_lines
            sig_lines = _sig_lines({"words": page.get_text("words")})
            for l in sig_lines:
                if not l["instr"]:
                    continue
                if l["daky"]:
                    continue
                below = [x for x in sig_lines
                         if x["y0"] > l["y1"] + 2
                         and not (x["x1"] < l["x0"] - 60 or
                                  x["x0"] > l["x1"] + 60)
                         and not (x["title"] or x["instr"])]
                if below:
                    manual_gaps.append(
                        min(x["y0"] for x in below) - l["y1"])
                else:
                    manual_gaps.append(float(page.rect.y1) - l["y1"])
        doc.close()
        # đếm manual/daky từ detector clusters cho báo cáo
    # gap floor check
    below72 = [g for g in manual_gaps if g < 72.0 - 0.5]
    report = {
        "corpus": str(corpus),
        "records": len(records),
        "census_clusters": total_census,
        "detector_clusters": total_det,
        "coverage_equal": total_census == total_det
                          and not coverage_mismatch,
        "coverage_mismatch_sample": coverage_mismatch[:20],
        "expected_but_zero_detected": missing,
        "manual_clusters": len(manual_gaps),
        "manual_gap_min_pt": round(min(manual_gaps), 1) if manual_gaps else None,
        "manual_gap_median_pt": (round(sorted(manual_gaps)[len(manual_gaps) // 2], 1)
                                 if manual_gaps else None),
        "manual_gap_below_72": len(below72),
    }
    out = corpus / "v7_signature_census.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    ok = (report["coverage_equal"] and not missing
          and not below72 and total_det > 0)
    print("VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
