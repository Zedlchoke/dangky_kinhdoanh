# -*- coding: utf-8 -*-
"""Customer export mode — phiếu rút gọn vs full (wave P0).

[CEX1] TNHH 1TV customer: số câu map < 50% so với full.
[CEX2] Wizard thành lập mới: không có chk_tt_chuyen_doi_tu_hkd trong map.
[CEX3] Customer export: không sheet AUTH_META.
[CEX4] Round-trip customer TNHH: wizard + core -> import OK.
[CEX5] Full export backward compat: default export_mode vẫn có AUTH (nếu store ok).

Chạy: python -X utf8 -m tools.test_excel_customer_export
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from tools.excel_case_export import (  # noqa: E402
    EXPORT_MODE_CUSTOMER, EXPORT_MODE_FULL, MAP_COLUMNS, MAP_SHEET,
    write_case_workbook,
)
from tools.excel_case_import import import_case_workbook  # noqa: E402

FIXTURE_META = {"today": "01/01/2026", "exported_at": "01/01/2026 10:00"}
CASE_TNHH = "thanh_lap_tnhh_1tv"
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


def _manifest(case_id: str) -> dict:
    return json.loads(
        (ROOT / "app" / "data" / "case_questionnaires" / ("%s.json" % case_id))
        .read_text(encoding="utf-8"))


def _map_question_ids(path: Path) -> set[str]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    qids: set[str] = set()
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        if qid:
            qids.add(str(qid))
    wb.close()
    return qids


def _export(manifest: dict, mode: str, wizard_answers=None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cex_"))
    out = tmp / ("wb_%s.xlsx" % mode)
    write_case_workbook(manifest, out, meta=FIXTURE_META,
                        export_mode=mode, wizard_answers=wizard_answers)
    return out


@check("[CEX1] TNHH 1TV customer map qids < 50% full")
def cex1():
    manifest = _manifest(CASE_TNHH)
    full = _map_question_ids(_export(manifest, EXPORT_MODE_FULL))
    cust = _map_question_ids(_export(manifest, EXPORT_MODE_CUSTOMER))
    assert len(cust) < len(full) * 0.5, (len(cust), len(full))
    assert len(cust) >= 5


@check("[CEX2] wizard=moi: không có q_i02_chk_tt_chuyen_doi_tu_hkd")
def cex2():
    manifest = _manifest(CASE_TNHH)
    out = _export(manifest, EXPORT_MODE_CUSTOMER,
                  wizard_answers={"wiz_tt_loai": "moi"})
    qids = _map_question_ids(out)
    assert "q_i02_chk_tt_chuyen_doi_tu_hkd" not in qids


@check("[CEX3] customer: không sheet AUTH_META")
def cex3():
    manifest = _manifest(CASE_TNHH)
    out = _export(manifest, EXPORT_MODE_CUSTOMER)
    wb = openpyxl.load_workbook(out, read_only=True)
    assert "AUTH_META" not in wb.sheetnames
    wb.close()


@check("[CEX4] round-trip customer TNHH wizard + core")
def cex4():
    manifest = _manifest(CASE_TNHH)
    out = _export(manifest, EXPORT_MODE_CUSTOMER)
    wb = openpyxl.load_workbook(out)
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    answers = {
        "wiz_tt_loai": "moi",
        "wiz_chu_so_huu": "ca_nhan",
        "q_i02_chu_hkd_ho_ten": "Nguyễn Văn A",
        "q_i02_dia_chi_chi_tiet": "25 Nguyễn Trãi",
        "q_i02_xa_phuong": "Phường Bến Thành",
        "q_i02_tinh_thanh": "TP. Hồ Chí Minh",
        "q_i02_dn_ten_tieng_viet": "Công ty TNHH An Phát",
        "q_i02_ho_ten_in_hoa": "Nguyễn Văn A",
        "q_i02_ds_nganh_ten_nganh": ["Bán lẻ"],
        "q_i02_ds_nganh_la_nganh_chinh": ["X"],
    }
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        if qid not in answers:
            continue
        layout = mp.cell(r, col["layout"]).value
        if layout == "mirror":
            continue
        value = answers[qid]
        cell = mp.cell(r, col["cell"]).value
        ws = wb[mp.cell(r, col["sheet"]).value]
        if isinstance(value, list):
            rows = [rr for rr in range(4, mp.max_row + 1)
                    if mp.cell(rr, col["question_id"]).value == qid
                    and mp.cell(rr, col["layout"]).value != "mirror"]
            for idx, rr in enumerate(rows):
                if idx < len(value) and value[idx] is not None:
                    c = mp.cell(rr, col["cell"]).value
                    wb[mp.cell(rr, col["sheet"]).value][c] = value[idx]
        else:
            ws[cell] = value
    filled = out.parent / "filled.xlsx"
    wb.save(filled)
    wb.close()
    res = import_case_workbook(filled, manifest,
                               imported_at="2026-09-15T00:00:00")
    assert res["ok"], res.get("errors")


@check("[CEX5] full default vẫn xuất được (không export_mode)")
def cex5():
    manifest = _manifest(CASE_TNHH)
    tmp = Path(tempfile.mkdtemp(prefix="cex5_"))
    write_case_workbook(manifest, tmp / "full.xlsx", meta=FIXTURE_META)
    qids = _map_question_ids(tmp / "full.xlsx")
    assert len(qids) > 50


def main() -> int:
    for fn in (cex1, cex2, cex3, cex4, cex5):
        fn()
    fails = [name for ok, name in _results if not ok]
    print("\n%d/%d PASS" % (len(_results) - len(fails), len(_results)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
