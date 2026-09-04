# -*- coding: utf-8 -*-
"""[6V-V2/C2] Bằng chứng name-slot binding (diệt B2/D14) — lane nameslot.

Export 14 form RED của D14 (baseline tools/census/6v_v1_baseline.json,
detectors.D14_name_slot) × fixture valid-full qua ĐƯỜNG PRODUCTION
(Bridge.export — docx + pdf + LibreOffice, cùng cách
tools/test_phase5r_signatures._export_subset dùng), sau đó:

  1. det_name_slot (tools/phase5_visual_gate) trên PDF page 1 của TỪNG form
     phải trả RỖNG (D14 = 0 trên subset);
  2. in dòng render chứa slot tên của TỪNG form (phải thấy giá trị tiếng
     Việt thật do fixture C4 sinh, không còn gạch/chấm/trống).

Không đụng app_web/**, detector, fixture — chỉ gọi đường export chuẩn.
Evidence (docx/pdf/png + report JSON) nằm trong generated_ho_so/ (gitignored).

Chạy:
    python -X utf8 tools/phase6v_c2_nameslot_evidence.py
Exit 0 = PASS (14/14 det_name_slot rỗng), 1 = FAIL.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_fixtures import build_fixture, ValueFactory  # noqa: E402
from tools.phase5_visual_gate import (  # noqa: E402
    det_name_slot, load_handwriting_slots, pdf_pages, run_export)

# 14 form RED của D14 trên baseline V1 (khớp census 6v_v1_baseline.json)
D14_RED_FORMS = [
    "PLII_M08", "PLII_M10", "PLII_M11", "PLII_M12", "PLII_M13", "PLII_M19",
    "PLII_M21", "PLII_M22", "PLII_M23", "PLII_M25", "PLII_M27", "PLII_M28",
    "PLI_M43", "PLI_M71",
]
# mảnh slot cần thấy giá trị, theo form (label gốc trên bản giấy)
_SLOT_PROBE = {
    "PLI_M43": "Tên doanh nghiệp/chi nhánh",
    "PLI_M71": "(Tên doanh nghiệp)",
}
OUT_ROOT = ROOT / "generated_ho_so" / "_visual_layout" / "phase6v" / "c2_nameslot"

# từ khóa: dòng page-1 có nhãn slot; in kèm phần còn lại của dòng
_SLOT_LINE = re.compile(
    r"Tên hộ kinh doanh|Tên doanh nghiệp", re.UNICODE)


def main() -> int:
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json").read_text(
        encoding="utf-8"))
    blocks_all = {}
    for fid in D14_RED_FORMS:
        p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        if p.exists():
            blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))

    print("[c2-evidence] export %d form x valid-full qua Bridge.export ..."
          % len(D14_RED_FORMS))
    errors, dirs = run_export(maps, blocks_all, "valid-full", D14_RED_FORMS,
                              OUT_ROOT)
    if errors:
        print("[c2-evidence] EXPORT LOI: %r" % (errors,))
        return 1

    registry = load_handwriting_slots()
    report = {"fixture": "valid-full", "forms": {}, "errors": []}
    n_fail = 0
    # mỗi batch "main" tạo 1 thư mục evidence chứa pdf toàn bộ form trong batch
    pdf_found = {}
    for d in dirs:
        for pdf in sorted(d.rglob("*.pdf")):
            pdf_found[pdf.stem] = pdf
    for fid in D14_RED_FORMS:
        pdf = pdf_found.get(fid)
        if pdf is None:
            # stem có thể mang tên case; quét theo hậu tố
            cands = [p for s, p in pdf_found.items()
                     if s.endswith("_%s" % fid) or s == fid]
            pdf = cands[0] if cands else None
        if pdf is None:
            print("[c2-evidence] %s: KHONG THAY PDF" % fid)
            report["errors"].append("%s: missing pdf" % fid)
            n_fail += 1
            continue
        _doc, pages = pdf_pages(pdf)
        issues = det_name_slot(pages, fid, registry)
        ok = not issues
        n_fail += 0 if ok else 1
        # dòng render chứa slot (page 1)
        slot_lines = [ln.strip() for ln in pages[0]["text"].split("\n")
                      if _SLOT_LINE.search(ln)]
        probe = _SLOT_PROBE.get(fid, "Tên hộ kinh doanh")
        slot_lines = [ln for ln in slot_lines
                      if probe in ln] or slot_lines[:2]
        report["forms"][fid] = {
            "d14_issues": issues, "ok": ok,
            "pdf": str(pdf.relative_to(OUT_ROOT)),
            "slot_lines": [ln[:120] for ln in slot_lines],
        }
        print("%-9s D14=%s  slot-render:" % (fid, "0 OK" if ok else "FAIL"))
        for ln in slot_lines[:2]:
            print("          | %s" % ln[:110])

    out_json = OUT_ROOT / "c2_nameslot_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("[c2-evidence] report: %s" % out_json)
    print("[c2-evidence] KET QUA: %d/%d form D14=0"
          % (len(D14_RED_FORMS) - n_fail, len(D14_RED_FORMS)))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
