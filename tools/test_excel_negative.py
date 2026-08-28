# -*- coding: utf-8 -*-
"""Wave X4 — negative Excel: khách phá khung phiếu -> fail-loud, KHÔNG data
một phần (điều kiện "không bao giờ ghi đè draft khi fail" của PLAN X3/X4).

Mỗi case: export phiếu thật (PLI_M72) -> mutate như khách/lập trình sai ->
import_questionnaire phải trả {"ok": False, "errors": [mã lỗi đúng], "data":
None}. Mã lỗi là contract chung với bridge X5 (hiện toast người dùng).

[NG1] xóa sheet map / file không phải xlsx             -> BAD_HEADER
[NG2] sửa header map (key -> key_hong)                 -> BAD_HEADER
[NG3] metadata questionnaire_version lệch              -> BAD_VERSION
[NG4] gõ vào ô lạ trong vùng điền (C12 — cột có ô map) -> UNKNOWN_CELL
[NG5] thiếu câu bắt buộc (q_ten_tieng_viet trống)      -> MISSING_REQUIRED
[NG6] select gõ tay giá trị ngoài danh sách            -> BAD_SELECT
[NG7] ngày 32/13/2020                                  -> BAD_DATE
[NG8] tiền "năm tỷ"                                    -> BAD_NUMBER

Chạy:  python3 -X utf8 -m tools.test_excel_negative   (exit 0 = PASS)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from tools.excel_export import (  # noqa: E402
    MAP_COLUMNS, MAP_SHEET, write_questionnaire)
from tools.excel_import import import_questionnaire  # noqa: E402

QUESTIONNAIRE = json.loads(
    (ROOT / "app" / "data" / "questionnaire" / "PLI_M72.json")
    .read_text(encoding="utf-8"))

BASE_ANSWERS = {"q_loai_hinh": "DNTN", "q_ten_tieng_viet": "Công ty A",
                "q_dia_chi_tru_so": "1 Đường B, TP.HCM"}

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def export_filled(extra: dict[str, str] | None = None) -> Path:
    """Export phiếu thật + điền các ô (theo map) của `extra` và BASE_ANSWERS."""
    answers = dict(BASE_ANSWERS)
    answers.update(extra or {})
    tmp = Path(tempfile.mkdtemp(prefix="p3ng_"))
    out = write_questionnaire(QUESTIONNAIRE, tmp / "phieu.xlsx")
    wb = openpyxl.load_workbook(out)
    mp, ws = wb[MAP_SHEET], wb["Phieu"]
    col = {h: i + 1 for i, h in enumerate(MAP_COLUMNS)}
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        if qid in answers:
            when = mp.cell(r, col["when"]).value or ""
            if when in ("", "{}") or '"DNTN"' in when:
                ws[mp.cell(r, col["cell"]).value] = answers[qid]
    filled = tmp / "filled.xlsx"
    wb.save(filled)
    return filled


def codes(res: dict) -> list[str]:
    return [e.get("code") for e in res.get("errors") or []]


@check("[NG1a] xóa sheet map -> BAD_HEADER, data None")
def ng1a():
    tmp = Path(tempfile.mkdtemp(prefix="p3ng1_"))
    out = write_questionnaire(QUESTIONNAIRE, tmp / "p.xlsx")
    wb = openpyxl.load_workbook(out)
    del wb[MAP_SHEET]
    p = tmp / "no_map.xlsx"
    wb.save(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert codes(res) == ["BAD_HEADER"], res["errors"]


@check("[NG1b] file không phải xlsx -> BAD_HEADER (không crash)")
def ng1b():
    tmp = Path(tempfile.mkdtemp(prefix="p3ng1b_"))
    p = tmp / "not_excel.xlsx"
    p.write_text("đây là file text", encoding="utf-8")
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert codes(res) == ["BAD_HEADER"], res["errors"]


@check("[NG2] sửa tên cột map (key -> key_hỏng) -> BAD_HEADER")
def ng2():
    p = export_filled()
    wb = openpyxl.load_workbook(p)
    mp = wb[MAP_SHEET]
    header = [mp.cell(row=3, column=c).value for c in range(1, len(MAP_COLUMNS) + 1)]
    key_idx = header.index("key") + 1
    mp.cell(row=3, column=key_idx, value="key_hong")
    wb.save(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "BAD_HEADER" in codes(res), res["errors"]


@check("[NG3] metadata questionnaire_version=99 -> BAD_VERSION")
def ng3():
    p = export_filled()
    wb = openpyxl.load_workbook(p)
    mp = wb[MAP_SHEET]
    fixed = False
    for row in mp.iter_rows(min_row=1, max_row=2):
        for cell in row:
            if isinstance(cell.value, str) and \
                    cell.value.startswith("questionnaire_version="):
                cell.value = "questionnaire_version=99"
                fixed = True
    assert fixed, "không tìm thấy metadata questionnaire_version"
    wb.save(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert codes(res) == ["BAD_VERSION"], res["errors"]


@check("[NG4] gõ ô lạ trong vùng điền (C12) -> UNKNOWN_CELL")
def ng4():
    p = export_filled()
    wb = openpyxl.load_workbook(p)
    ws = wb["Phieu"]
    ws["C12"] = "khách gõ linh tinh"          # C12: cột C có ô map, ô này không
    wb.save(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "UNKNOWN_CELL" in codes(res), res["errors"]


@check("[NG5] thiếu câu bắt buộc -> MISSING_REQUIRED")
def ng5():
    p = export_filled({"q_ten_tieng_viet": None})
    wb = openpyxl.load_workbook(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "MISSING_REQUIRED" in codes(res), res["errors"]


@check("[NG6] select gõ tay giá trị ngoài danh sách -> BAD_SELECT")
def ng6():
    p = export_filled({"q_loai_hinh": "Công ty TNHH phương bắc"})
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "BAD_SELECT" in codes(res), res["errors"]


@check("[NG7] ngày 32/13/2020 -> BAD_DATE")
def ng7():
    p = export_filled({"q_ngay_sinh": "32/13/2020"})
    wb = openpyxl.load_workbook(p)
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "BAD_DATE" in codes(res), res["errors"]


@check("[NG8] tiền 'năm tỷ' -> BAD_NUMBER")
def ng8():
    p = export_filled({"q_von": "năm tỷ"})
    res = import_questionnaire(p, QUESTIONNAIRE)
    assert res["ok"] is False and res["data"] is None, res
    assert "BAD_NUMBER" in codes(res), res["errors"]


def main() -> int:
    for fn in (ng1a, ng1b, ng2, ng3, ng4, ng5, ng6, ng7, ng8):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_excel_negative: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
