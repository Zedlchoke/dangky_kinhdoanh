# -*- coding: utf-8 -*-
"""[6V-V2/B3r] Bằng chứng gộp paragraph chk-đứng-một-mình — mini-lane
6v-chkline (Q-V1 "tick cùng dòng nhãn").

Export TOÀN BỘ form có field chk (form_maps type=chk — superset chặt của 16
form residue D15 X_OWN_LINE corpus v3) × fixture choice-variants qua ĐƯỜNG
PRODUCTION (Bridge.export — docx + pdf + LibreOffice, cùng cách lane C2
tools/phase6v_c2_nameslot_evidence.py dùng), sau đó:

  1. det_chk_glyph (tools/phase5_visual_gate) trên TỪNG form phải trả RỖNG
     (D15 = 0 — hết BARE_X lẫn X_OWN_LINE: nhãn và tick cùng một dòng PDF);
  2. in dòng render nhãn+tick của 5 form tiêu biểu (M01/M05/M12/M17/PLII_M02)
     — phải thấy nhãn VÀ X trên MỘT dòng text PDF.

Chỉ gọi đường export chuẩn; không đụng app_web/**, detector, fixture.
Evidence (docx/pdf/png + report JSON) nằm trong generated_ho_so/ (gitignored).
Chạy trong EVIDENCE WORKTREE RIÊNG (không phải lane worktree):

    python -X utf8 tools/phase6v_b3r_chkline_evidence.py
Exit 0 = PASS (17/17 det_chk_glyph rỗng), 1 = FAIL.
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_visual_gate import (  # noqa: E402
    det_chk_glyph, pdf_pages, run_export)

OUT_ROOT = ROOT / "generated_ho_so" / "_visual_layout" / "phase6v" \
    / "b3r_chkline"

# 5 form tiêu biểu: (form_id, [nhãn display cần thấy cùng X trên 1 dòng]).
# Nhãn chọn đúng option fixture choice-variants tick (đối chiếu build_fixture).
_PROBE_LINES = {
    "PLI_M01": ["Thành lập mới"],
    "PLI_M05": ["Thành lập trên cơ sở hợp nhất doanh nghiệp"],
    "PLI_M12": ["- Đăng ký thay đổi trên cơ sở tách doanh nghiệp",
                "Hạch toán độc lập"],
    "PLI_M17": ["Khu công nghiệp", "Khấu trừ"],
    "PLII_M02": ["Cá nhân",
                 "Thành viên hộ gia đình uỷ quyền"],
}


def main() -> int:
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json").read_text(
        encoding="utf-8"))
    # mọi form có field chk (superset của 16 form residue corpus v3)
    form_ids = sorted(
        fid for fid, m in maps.items()
        if any(f.get("type") == "chk" for f in m.get("fields", [])))
    blocks_all = {}
    for fid in form_ids:
        p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        if p.exists():
            blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))

    print("[b3r-evidence] export %d form x choice-variants qua "
          "Bridge.export ..." % len(form_ids))
    errors, dirs = run_export(maps, blocks_all, "choice-variants",
                              form_ids, OUT_ROOT)
    if errors:
        print("[b3r-evidence] EXPORT LOI: %r" % (errors,))
        return 1

    pdf_found, docx_found = {}, {}
    for d in dirs:
        for pdf in sorted(d.rglob("*.pdf")):
            pdf_found[pdf.stem] = pdf
        for docx in sorted(d.rglob("*.docx")):
            docx_found[docx.stem] = docx

    report = {"fixture": "choice-variants", "forms": {}, "errors": []}
    n_fail = 0
    for fid in form_ids:
        pdf = pdf_found.get(fid) or next(
            (p for s, p in pdf_found.items() if s.endswith("_%s" % fid)),
            None)
        docx = docx_found.get(fid) or next(
            (p for s, p in docx_found.items() if s.endswith("_%s" % fid)),
            None)
        if pdf is None or docx is None:
            print("[b3r-evidence] %s: KHONG THAY PDF/DOCX" % fid)
            report["errors"].append("%s: missing export" % fid)
            n_fail += 1
            continue
        _doc, pages = pdf_pages(pdf)
        issues = det_chk_glyph(Path(docx), pages, maps[fid])
        ok = not issues
        n_fail += 0 if ok else 1
        report["forms"][fid] = {
            "d15_issues": issues, "ok": ok,
            "pdf": str(pdf.relative_to(OUT_ROOT)),
        }
        print("%-9s D15=%s" % (fid, "0 OK" if ok else
                               "FAIL %d hit %r" % (len(issues),
                                                   issues[:2])))

    # dòng nhãn+tick của 5 form tiêu biểu — nhãn và X phải TRÊN MỘT dòng
    print("-" * 64)
    report["probe_lines"] = {}
    for fid, probes in _PROBE_LINES.items():
        pdf = pdf_found.get(fid) or next(
            (p for s, p in pdf_found.items() if s.endswith("_%s" % fid)),
            None)
        if pdf is None:
            continue
        _doc, pages = pdf_pages(pdf)
        lines = [ln.strip() for p in pages for ln in p["text"].split("\n")]
        got = []
        for probe in probes:
            hit = [ln for ln in lines
                   if probe.lower() in ln.lower() and "X" in ln]
            got.append({"probe": probe, "lines": [ln[:110] for ln in hit[:3]],
                        "found_same_line": bool(hit)})
        report["probe_lines"][fid] = got
        for g in got:
            mark = "OK " if g["found_same_line"] else "MISS"
            print("[%s] %s %s:" % (mark, fid, g["probe"]))
            for ln in g["lines"]:
                print("        | %s" % ln)
            if not g["found_same_line"]:
                n_fail += 1

    out_json = OUT_ROOT / "b3r_chkline_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("-" * 64)
    print("[b3r-evidence] report: %s" % out_json)
    print("[b3r-evidence] KET QUA: %d/%d form D15=0 (+ 5-form probe lines)"
          % (len(form_ids) - min(n_fail, len(form_ids)), len(form_ids)))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
