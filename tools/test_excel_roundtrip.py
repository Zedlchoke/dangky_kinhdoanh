# -*- coding: utf-8 -*-
"""Wave X4 — round-trip Excel: draft-trạng-thiết → xlsx → import giữ 100% giá trị.

[RT1] Export phiếu từ questionnaire PLI_M72 thật → điền theo map (như khách)
     → import_questionnaire trả đúng từng giá trị:
     - text/tel/email giữ nguyên văn (kể cả số 0 đầu, dấu tiếng Việt);
     - money "5.000.000.000" -> 5000000000 (số; chuẩn hóa E2);
     - date "05/12/1985" -> ngay/thang/nam = "05"/"12"/"1985" (transform);
     - select so theo label -> value (dn.loai_hinh = "DNTN");
     - bảng row_group 'nganh' 2 hàng -> loop rows đúng thứ tự, 'X' nguyên.
[RT2] Đổi nhánh `when`: điền theo TNHH_2TV -> data nhảy đúng sang von_dieu_le
     + ds_nganh_tnhh_2tv + ndd.* (không trộn nhánh DNTN).
[RT3] Idempotent export: ghi ×2 cùng questionnaire/meta -> byte-identical.
[RT4] Ô điền number_format '@' — số 0 đầu CCCD không bị Excel ăn mất.
[RT5] [O4] Mã định danh dài "012345678901234567890123456789" (30 chữ số, số 0
     đầu) round-trip giữ 100% chuỗi; ô trong file là string, không scientific,
     không truncate — giữ nguyên văn cả tel "0084…".

Chạy:  python3 -X utf8 -m tools.test_excel_roundtrip   (exit 0 = PASS)
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


def fill_and_import(answers: dict[str, str], variant_value: str,
                    table_rows: dict[str, list[dict]] | None = None,
                    meta: dict | None = None,
                    return_path: bool = False,
                    questionnaire: dict | None = None):
    """Export -> điền answers theo map (chỉ nhánh khớp variant) -> import."""
    q = questionnaire or QUESTIONNAIRE
    tmp = Path(tempfile.mkdtemp(prefix="p3rt_"))
    out = write_questionnaire(q, tmp / "phieu.xlsx", meta=meta)
    wb = openpyxl.load_workbook(out)
    mp, ws = wb[MAP_SHEET], wb["Phieu"]
    col = {h: i + 1 for i, h in enumerate(MAP_COLUMNS)}
    table_cursor: dict[str, int] = {}
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        cell = mp.cell(r, col["cell"]).value
        when = mp.cell(r, col["when"]).value or ""
        # variant_value="" = cụm không có nhánh when -> điền mọi dòng map.
        when_ok = (True if variant_value == "" else
                   (when in ("", "{}") or ('"%s"' % variant_value) in when))
        if qid in answers and when_ok:
            ws[cell] = answers[qid]
        if table_rows and qid in table_rows and when_ok:
            # map X4: MỖI ô điền một dòng — điền tuần tự theo con trỏ
            idx = table_cursor.get(qid, 0)
            rows = table_rows[qid]
            if idx < len(rows):
                ws[cell] = rows[idx]
                table_cursor[qid] = idx + 1
    filled = tmp / "phieu_filled.xlsx"
    wb.save(filled)
    res = import_questionnaire(filled, q)
    if return_path:
        return res, mp, wb["Phieu"], filled
    return res


@check("[RT1] DNTN: giữ 100% giá trị — text/money/date 3 key/select/bảng ngành")
def rt1():
    res = fill_and_import(
        {"q_loai_hinh": "DNTN", "q_ten_tieng_viet": "Công ty TNHH Thử Nghiệm",
         "q_dia_chi_tru_so": "123 Nguyễn Huệ, Quận 1, TP.HCM",
         "q_von": "5.000.000.000", "q_ho_ten": "nguyễn văn a",
         "q_gioi_tinh": "Nam", "q_ngay_sinh": "05/12/1985",
         "q_quoc_tich": "Việt Nam", "q_so_cccd": "079085001234",
         "q_cccd_ngay_cap": "10/01/2015", "q_dien_thoai": "0901234567",
         "q_email": "khach@test.vn"},
        "DNTN",
        table_rows={"q_nganh_ten": ["Bán lẻ hàng điện tử"],
                    "q_nganh_ma": ["4751"],
                    "q_nganh_chinh": ["X"]},
        meta={"case_id": "RT1", "today": "28/08/2028"})
    assert res["ok"], res["errors"]
    d = res["data"]
    assert d["dn.loai_hinh"] == "DNTN", d
    assert d["dn.ten_tieng_viet"] == "Công ty TNHH Thử Nghiệm"
    assert d["dn.dia_chi_tru_so"] == "123 Nguyễn Huệ, Quận 1, TP.HCM"
    assert d["von_dau_tu_so"] == 5000000000, d["von_dau_tu_so"]
    assert (d["ngay_sinh"], d["thang_sinh"], d["nam_sinh"]) == ("05", "12", "1985")
    assert d["ho_ten_in_hoa"] == "nguyễn văn a"          # giữ nguyên văn (app in hoa)
    assert d["chu_hkd.gioi_tinh"] == "Nam"
    assert d["chu_hkd.quoc_tich"] == "Việt Nam"
    assert d["chu_hkd.so_cccd"] == "079085001234"        # số 0 đầu không mất
    assert d["ngay_cap"] == "10/01/2015"
    assert d["dien_thoai_khac"] == "0901234567"
    assert d["email_khac"] == "khach@test.vn"
    rows = d["ds_nganh_dntn"]
    assert isinstance(rows, list) and len(rows) == 1, rows
    assert rows[0] == {"ten_nganh": "Bán lẻ hàng điện tử", "ma_nganh": "4751",
                       "la_nganh_chinh": "X"}


@check("[RT2] TNHH_2TV: nhánh when nhảy đúng von_dieu_le + ds_nganh_tnhh_2tv + ndd.*")
def rt2():
    res = fill_and_import(
        {"q_loai_hinh": "TNHH_2TV", "q_ten_tieng_viet": "Công ty TNHH Hai Bà",
         "q_dia_chi_tru_so": "45 Lê Lợi, Quận 1, TP.HCM",
         "q_von": "20000000000", "q_ho_ten": "Trần Thị B",
         "q_so_cccd": "079085005678", "q_chuc_vu": "Giám đốc"},
        "TNHH_2TV",
        table_rows={"q_nganh_ten": ["Phần mềm", "Tư vấn CNTT"],
                    "q_nganh_ma": ["6201", "7020"],
                    "q_nganh_chinh": ["X", ""]})
    assert res["ok"], res["errors"]
    d = res["data"]
    assert d["von_dieu_le"] == 20000000000
    assert "von_dau_tu_so" not in d, "lẫn nhánh DNTN: %s" % d
    assert d["ndd.ho_ten"] == "Trần Thị B"
    assert d["ndd.so_cccd"] == "079085005678"
    assert d["ndd.chuc_vu"] == "Giám đốc"
    assert "ho_ten_in_hoa" not in d, "lẫn nhánh DNTN/TNHH_1TV"
    rows = d["ds_nganh_tnhh_2tv"]
    assert len(rows) == 2, rows
    assert rows[0]["ten_nganh"] == "Phần mềm" and rows[0]["la_nganh_chinh"] == "X"
    assert rows[1]["ten_nganh"] == "Tư vấn CNTT" and rows[1]["ma_nganh"] == "7020"


@check("[RT3] export ×2 same cell-content (deterministic; so NỘI DUNG ô — "
      "xlsx là zip có mtime, byte-idempotent bất khả thi như tiền lệ docx)")
def rt3():
    tmp = Path(tempfile.mkdtemp(prefix="p3rt3_"))
    a = write_questionnaire(QUESTIONNAIRE, tmp / "a.xlsx",
                            meta={"case_id": "X", "today": "01/01/2026"})
    b = write_questionnaire(QUESTIONNAIRE, tmp / "b.xlsx",
                            meta={"case_id": "X", "today": "01/01/2026"})
    wa, wbb = openpyxl.load_workbook(a), openpyxl.load_workbook(b)
    assert wa.sheetnames == wbb.sheetnames
    for name in wa.sheetnames:
        sa, sb = wa[name], wbb[name]
        assert (sa.max_row, sa.max_column) == (sb.max_row, sb.max_column), name
        for row in sa.iter_rows():
            for cell in row:
                if cell.value is not None:
                    assert sb[cell.coordinate].value == cell.value, \
                        "%s!%s: %r != %r" % (name, cell.coordinate,
                                             cell.value,
                                             sb[cell.coordinate].value)


@check("[RT4] ô điền number_format '@' — chuỗi giữ nguyên (không thành serial)")
def rt4():
    tmp = Path(tempfile.mkdtemp(prefix="p3rt4_"))
    out = write_questionnaire(QUESTIONNAIRE, tmp / "p.xlsx")
    wb = openpyxl.load_workbook(out)
    mp, ws = wb[MAP_SHEET], wb["Phieu"]
    col = {h: i + 1 for i, h in enumerate(MAP_COLUMNS)}
    checked = 0
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["question_id"]).value == "q_dia_chi_tru_so" and \
                (mp.cell(r, col["when"]).value or "") in ("", "{}"):
            addr = mp.cell(r, col["cell"]).value
            assert ws[addr].number_format == "@", ws[addr].number_format
            checked += 1
    assert checked >= 1, "không tìm thấy ô q_dia_chi_tru_so không có when"


LONG_ID = "012345678901234567890123456789"   # 30 chữ số, số 0 đầu — [O4]


@check("[RT5] O4 mã định danh dài: 30 chữ số + số 0 đầu round-trip giữ "
       "100% chuỗi (không scientific, không truncate, không mất số 0 đầu)")
def rt5():
    answers = {"q_loai_hinh": "DNTN", "q_ten_tieng_viet": "Công ty O4",
               "q_dia_chi_tru_so": "9 Đường O4, TP.HCM", "q_so_cccd": LONG_ID,
               "q_ho_ten": "Lê Văn O4", "q_dien_thoai": "0084901234567"}
    table_rows = {"q_nganh_ten": ["Bán lẻ hàng điện tử"],
                  "q_nganh_chinh": ["X"]}
    res, mp, ws, filled = fill_and_import(
        answers, "DNTN", table_rows=table_rows,
        meta={"case_id": "RT5", "today": "06/09/2026"}, return_path=True)
    assert res["ok"], res["errors"]
    d = res["data"]
    assert d["chu_hkd.so_cccd"] == LONG_ID, repr(d["chu_hkd.so_cccd"])
    assert isinstance(d["chu_hkd.so_cccd"], str), type(d["chu_hkd.so_cccd"])
    assert d["dien_thoai_khac"] == "0084901234567", d["dien_thoai_khac"]

    # File trên đĩa: ô vừa điền là string, number_format '@', không scientific.
    col = {h: i + 1 for i, h in enumerate(MAP_COLUMNS)}
    seen = 0
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["question_id"]).value == "q_so_cccd" and \
                '"DNTN"' in (mp.cell(r, col["when"]).value or ""):
            addr = mp.cell(r, col["cell"]).value
            assert ws[addr].number_format == "@", ws[addr].number_format
            v = ws[addr].value
            assert v == LONG_ID and isinstance(v, str), repr(v)
            assert "E" not in v.upper(), v     # không scientific notation
            assert not v.startswith("."), v    # không truncate đầu
            seen += 1
    assert seen >= 1, "không tìm thấy ô q_so_cccd nhánh DNTN"
    # Nạp lại file lần 2 (kiểm import idempotent trên cùng file string).
    res2 = import_questionnaire(filled, QUESTIONNAIRE)
    assert res2["ok"], res2["errors"]
    assert res2["data"]["chu_hkd.so_cccd"] == LONG_ID
    assert isinstance(res2["data"]["chu_hkd.so_cccd"], str)


Q_M01 = json.loads((ROOT / "app" / "data" / "questionnaire" / "PLII_M01.json")
                   .read_text(encoding="utf-8"))
Q_M02 = json.loads((ROOT / "app" / "data" / "questionnaire" / "PLII_M02.json")
                   .read_text(encoding="utf-8"))


@check("[RT6] O7 cụm hộ KD — PLII_M01: bảng tv_hgd 2 hàng + ngành + CCCD "
       "dài số 0 đầu + money/date chuẩn hóa đúng")
def rt6():
    res = fill_and_import(
        {"q_ho_ten": "nguyễn văn a", "q_ngay_sinh": "05/12/1985",
         "q_gioi_tinh": "Nam", "q_so_cccd": "079085001234",
         "q_ten_hkd": "Hộ kinh doanh bánh ngọt Hải Phòng",
         "q_dia_chi_chi_tiet": "25 Nguyễn Trãi", "q_xa_phuong": "P. Bến Thành",
         "q_tinh_thanh": "TP. Hồ Chí Minh", "q_von": "50.000.000",
         "q_ngay_bd": "01/10/2026", "q_so_lao_dong": "3"},
        variant_value="",  # cụm M01 không có nhánh when — điền mọi dòng map
        table_rows={"q_nganh_ten": ["Bán lẻ bánh ngọt"],
                    "q_nganh_ma": ["1071"],
                    "q_nganh_chinh": ["X"],
                    "q_tv_hgd_ho_ten": ["NGUYỄN THỊ C", "LÊ VĂN D"],
                    "q_tv_hgd_so_cccd": ["079085005678", "079085009999"]},
        meta={"case_id": "RT6", "today": "06/09/2026"},
        questionnaire=Q_M01)
    assert res["ok"], res["errors"]
    d = res["data"]
    assert d["chu_hkd.ho_ten"] == "nguyễn văn a"
    assert d["chu_hkd.so_cccd"] == "079085001234"
    assert (d["ngay_sinh"], d["thang_sinh"], d["nam_sinh"]) == ("05", "12", "1985")
    assert d["von_kinh_doanh"] == 50000000, d["von_kinh_doanh"]
    assert (d["ngay_bd"], d["thang_bd"], d["nam_bd"]) == ("01", "10", "2026")
    assert d["so_lao_dong"] == 3
    rows = d["ds_nganh"]
    assert rows == [{"ten_nganh": "Bán lẻ bánh ngọt", "ma_nganh": "1071",
                     "la_nganh_chinh": "X"}], rows
    tv = d["ds_tv_ho_gia_dinh"]
    assert isinstance(tv, list) and len(tv) == 2, tv
    assert tv[0]["ho_ten"] == "NGUYỄN THỊ C" and tv[0]["so_cccd"] == "079085005678"
    assert tv[1]["ho_ten"] == "LÊ VĂN D" and tv[1]["so_cccd"] == "079085009999"


@check("[RT7] O7 cụm thuế — PLII_M02: chỉ tiêu đăng ký thuế (5.1/5.2 giá trị "
       "mới) + bảng ngành bổ sung round-trip đúng key phẳng")
def rt7():
    res = fill_and_import(
        {"q_hkd_ten": "Hộ kinh doanh bánh ngọt Hải Phòng",
         "q_hkd_ma_so": "0312345678-001",
         "q_thue_dia_chi_tb_moi": "25 Nguyễn Trãi, P. Bến Thành, TP.HCM",
         "q_thue_so_lao_dong_moi": "4"},
        variant_value="",
        table_rows={"q_nganh_bs_ten": ["Bán nước ép trái cây"],
                    "q_nganh_bs_ma": ["1030"],
                    "q_nganh_bs_chinh": ["X"]},
        meta={"case_id": "RT7", "today": "06/09/2026"},
        questionnaire=Q_M02)
    assert res["ok"], res["errors"]
    d = res["data"]
    assert d["hkd_ten_tieng_viet_2"] == "Hộ kinh doanh bánh ngọt Hải Phòng"
    assert d["hkd_ma_so"] == "0312345678-001"       # chuỗi, giữ nguyên dấu -
    assert d["thue_chi_tieu_cu_moi.chi_tieu_5_1_dia_chi_nhan_thong_bao_thue.thong_tin_dang_ky_moi"] \
        == "25 Nguyễn Trãi, P. Bến Thành, TP.HCM"
    assert d["thue_chi_tieu_cu_moi.chi_tieu_5_2_tong_so_lao_dong.thong_tin_dang_ky_moi"] == 4
    rows = d["nganh_bo_sung"]
    assert rows == [{"ten_nganh_bo_sung": "Bán nước ép trái cây",
                     "ma_nganh": "1030", "la_nganh_chinh": "X"}], rows


def main() -> int:
    for fn in (rt1, rt2, rt3, rt4, rt5, rt6, rt7):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_excel_roundtrip: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
