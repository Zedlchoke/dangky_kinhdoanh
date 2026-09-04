# -*- coding: utf-8 -*-
"""[6V-V4/signgap] Bằng chứng vùng viết chữ ký 40pt toàn corpus — lane signgap.

Owner đồng ý nâng sàn vùng viết 40pt từ riêng PLI_M15 (phiên quyết "chỗ ký"
2026-09-05) cho TOÀN BỘ cụm ký. Script này chứng minh trên 12 form đại diện
có cụm ký × fixture valid-full + long-boundary, export qua ĐƯỜNG PRODUCTION
(Bridge.export — docx + pdf + LibreOffice, cùng đường
tools/test_phase5r_signatures._export_subset):

  1. MỌI cụm ký đo được gap dọc dưới instruction >= 40pt — thuật toán đo
     NHÂN BẢN 1:1 vòng lặp write-gap của detector D6
     (tools/phase5_visual_gate.det_signatures) trên cùng _sig_lines;
  2. detector D6 chạy thật trên từng PDF: KHÔNG item SIG_WRITE_SPACE còn lại
     ở fails lẫn candidates (sau khi lane nâng hard);
  3. D5: trang BLANK = 0 (SPARSE chỉ ghi nhận, so sánh thủ công before/after
     trong báo cáo lane — tăng SPARSE bất thường = red flag pagination);
  4. orphan-signature-page (WLAY-009, logic test B5): trang thưa chứa
     instruction ký KHÔNG có title cùng trang = FAIL — gap mới KHÔNG được
     đẩy cụm ký sang trang riêng tạo orphan;
  5. page_count từng form×fixture được ghi lại để đối chiếu before/after.

Chạy (trong worktree evidence, trạng thái tương ứng before/after):
    python -X utf8 tools/phase6v_signgap_evidence.py --label before
    python -X utf8 tools/phase6v_signgap_evidence.py --label after
Exit 0 = PASS (mọi gap >= 40, D6 sạch, D5 BLANK=0, không orphan); 1 = FAIL.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_visual_gate import (  # noqa: E402
    SIG_WRITE_PT, _sig_lines, det_blank_sparse, det_signatures, load_expectations,
    pdf_pages, run_export)

# 12 form đại diện có cụm ký (Lead yêu cầu tối thiểu: M15, M70, PLII_M02,
# PLII_M25, M09, M12): phủ horizontal (M70), 2-signer vertical có pin (M15),
# 2-signer BLOCKED_OWNER (M14, PLII_M17), cụm đơn dọc (PLII_M01, PLII_M27),
# publication (M43, M71), long-boundary nhạy orphan (M09, PLII_M25), bảng
# thuế (PLII_M02), thay đổi thông tin (M12).
SIGGAP_FORMS = [
    "PLI_M09", "PLI_M12", "PLI_M14", "PLI_M15", "PLI_M43", "PLI_M70",
    "PLI_M71", "PLII_M01", "PLII_M02", "PLII_M17", "PLII_M25", "PLII_M27",
]
SIGGAP_FIXTURES = ("valid-full", "long-boundary")

OUT_ROOT = ROOT / "generated_ho_so" / "_visual_layout" / "phase6v" / "signgap"


def _cluster_gaps(pages) -> tuple[list[float], list[float], list[dict]]:
    """Nhân bản 1:1 vòng lặp write-gap của D6 (det_signatures): với mỗi cụm
    (instruction), tìm dòng chữ kế tiếp trong cùng cột, gap = y0 - instr.y1.
    Cụm KHÔNG có dòng dưới (cuối ô bảng / cuối nội dung): gap thay thế =
    phần giấy còn lại dưới instruction (page_h - instr.y1) — nếu cả đó mà
    < 40pt thì không còn chỗ ký. Trả (gaps, bottom_gaps_cua_cum_khong_co_duoi,
    danh sách orphan-sparse-item)."""
    gaps: list[float] = []
    no_below: list[float] = []
    orphans: list[dict] = []
    for p in pages:
        lines = _sig_lines(p)
        page_h = p["pixmap"].height / 2.0 if p.get("pixmap") is not None \
            else None
        # orphan check theo test B5: trang thưa chứa instr không title
        chars = len(re.sub(r"\s+", "", p["text"]))
        if chars < 120:
            has_instr = any(l["instr"] for l in lines)
            has_title = any(l["title"] for l in lines)
            if has_instr and not has_title:
                orphans.append({"page": p["pno"] + 1, "chars": chars})
        for instr in (l for l in lines if l["instr"]):
            below = [l for l in lines
                     if l["y0"] > instr["y1"] + 2
                     and not (l["x1"] < instr["x0"] - 60 or
                              l["x0"] > instr["x1"] + 60)
                     and not (l["title"] or l["instr"])]
            if not below:
                # pixmap zoom 2.0 -> height/2 = pt; pdf_pages luôn render
                no_below.append(round((page_h or 0) - instr["y1"], 1))
                continue
            nearest = min(below, key=lambda l: l["y0"])
            gaps.append(nearest["y0"] - instr["y1"])
    return gaps, no_below, orphans


def _xml_spacers_800(docx_path: Path) -> int:
    """Đếm paragraph đệm vùng viết exact-height >= 800 twips (40pt) trong
    document.xml của file render — bằng chứng bổ sung cho cụm mà D6 không đo
    được bằng PDF (cụm cuối ô bảng / cụm cuối tài liệu, không có dòng chữ
    dưới để đo). Cùng dấu vân tay XML mà test B4 (test_phase5r_signatures)
    dùng cho M15."""
    import zipfile
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return sum(1 for v in re.findall(r'w:line="(\d+)" w:lineRule="exact"', xml)
               if int(v) >= 800)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="after",
                    choices=["before", "after"])
    ap.add_argument("--outdir", default="")
    args = ap.parse_args()

    out_root = Path(args.outdir) if args.outdir else OUT_ROOT
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json").read_text(
        encoding="utf-8"))
    blocks_all = {}
    for fid in SIGGAP_FORMS:
        p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        if p.exists():
            blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))
    expectations = load_expectations()

    report = {"label": args.label, "min_required_pt": SIG_WRITE_PT,
              "forms": {}, "errors": []}
    n_bad = 0
    for fixture in SIGGAP_FIXTURES:
        errors, dirs = run_export(maps, blocks_all, fixture, SIGGAP_FORMS,
                                  out_root)
        if errors:
            print("[signgap] EXPORT LOI %s: %r" % (fixture, errors))
            report["errors"] += ["%s: %s" % (fixture, e) for e in errors]
            return 1
        pdf_found = {}
        for d in dirs:
            for pdf in sorted(d.glob("*.pdf")):
                pdf_found[pdf.stem] = pdf
        for fid in SIGGAP_FORMS:
            pdf = pdf_found.get(fid)
            if pdf is None:
                cands = [p for s, p in pdf_found.items()
                         if s.endswith("_%s" % fid) or s == fid]
                pdf = cands[0] if cands else None
            if pdf is None:
                print("[signgap] %s/%s: KHONG THAY PDF" % (fid, fixture))
                report["errors"].append("%s/%s: missing pdf" % (fid, fixture))
                n_bad += 1
                continue
            _doc, pages = pdf_pages(pdf)
            gaps, no_below, orphans = _cluster_gaps(pages)
            d5 = det_blank_sparse(pages)
            det = det_signatures(pages, expectations, fid)
            write_fails = [f for f in det["fails"]
                           if f.get("code") == "SIG_WRITE_SPACE"]
            write_cands = [c for c in det["candidates"]
                           if c.get("code") == "SIG_WRITE_SPACE"]
            other_fails = [f for f in det["fails"]
                           if f.get("code") != "SIG_WRITE_SPACE"]
            min_gap = min(gaps) if gaps else None
            spacers = _xml_spacers_800(pdf.with_suffix(".docx"))
            # Phân loại trung thực:
            #  - D6-MEASURED: có gap đo được -> mọi gap phải >= 40;
            #  - D6-UNMEASURABLE: cụm không có dòng chữ dưới trong cùng cột
            #    (cuối ô bảng / cuối nội dung) — D6 không đo được bằng PDF.
            #    Đạt nếu MỘI cụm trong nhóm này có (i) spacer XML >= 800 twips
            #    trong container (ô ký bảng 1x2, như test B4) HOẶC (ii) phần
            #    giấy còn lại dưới instruction >= 40pt (cụm cuối nội dung —
            #    vùng viết là phần giấy trống tới hết trang);
            #  - N/A-D6: PDF không có instruction nào trong ngữ pháp D6 — lỗ
            #    hổng vocabulary có sẵn của gate (biến thể "(Ký, ghi họ tên và
            #    đóng dấu)" — test_phase5r_signatures docstring B1 đã ghi nhận
            #    census phải mở rộng vì "gate chưa bắt"), NGOÀI PHẠM VI lane
            #    này (chỉ được sửa D6 phần write-gap).
            if gaps:
                status = "D6-MEASURED"
            elif no_below:
                status = "D6-UNMEASURABLE"
            else:
                status = "N/A-D6"
            unmeas_ok = (
                spacers >= len(no_below)
                or (min(no_below) >= SIG_WRITE_PT if no_below else True))
            ok = (not orphans
                  and not [d for d in d5 if d["code"] == "BLANK"]
                  and not write_fails and not write_cands
                  and (status == "N/A-D6"
                       or (min_gap is None or min_gap >= SIG_WRITE_PT))
                  and (status != "D6-UNMEASURABLE" or unmeas_ok))
            if not ok:
                n_bad += 1
            report["forms"]["%s/%s" % (fid, fixture)] = {
                "ok": ok, "status": status,
                "clusters": len(gaps) + len(no_below),
                "clusters_measured": len(gaps),
                "clusters_no_below": len(no_below),
                "no_below_bottom_gaps_pt": no_below,
                "gaps_pt": [round(g, 1) for g in gaps],
                "min_gap_pt": None if min_gap is None else round(min_gap, 1),
                "xml_spacers_800": spacers,
                "page_count": len(pages),
                "d5_blank": [d for d in d5 if d["code"] == "BLANK"],
                "d5_sparse": [d for d in d5 if d["code"] == "SPARSE"],
                "orphans": orphans,
                "det_write_fails": len(write_fails),
                "det_write_candidates": len(write_cands),
                "det_other_fails": other_fails,
                "pdf": str(pdf.relative_to(out_root)),
            }
            print("%-9s %-13s [%s] clusters=%2d (khoang-cuoi=%d, "
                  "bottom_min=%s) min_gap=%s spacer800=%d pages=%d "
                  "D5blank=%d orphan=%d D6write(f/c)=%d/%d %s"
                  % (fid, fixture, status, len(gaps) + len(no_below),
                     len(no_below),
                     "%.0fpt" % min(no_below) if no_below else "n/a",
                     "n/a" if min_gap is None else "%.1f" % min_gap,
                     spacers, len(pages),
                     len([d for d in d5 if d["code"] == "BLANK"]),
                     len(orphans), len(write_fails), len(write_cands),
                     "OK" if ok else "FAIL"))
            for f in other_fails:
                print("          D6-other: %r" % (f,))

    out_json = out_root / ("signgap_report_%s.json" % args.label)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("[signgap] report: %s" % out_json)
    print("[signgap] KET QUA (%s): %d form-fixture KHONG dat chuan"
          % (args.label, n_bad))
    return 0 if n_bad == 0 and not report["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
