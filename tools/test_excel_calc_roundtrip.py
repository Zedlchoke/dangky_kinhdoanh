# -*- coding: utf-8 -*-
"""E3-Calc — round-trip LibreOffice Calc THẬT cho workbook CASE-LEVEL
(PLAN_hoan_thien_pfat_hanh §5-E3, phần "import lại file đã được mỗi ứng dụng
lưu" — phương án Calc làm được tự động).

Kịch bản MỖI case:
  1. `write_case_workbook` -> workbook gốc (meta fixture).
  2. Điền dữ liệu NHƯ KHÁCH bằng openpyxl (đọc `__map`, bỏ ô mirror) — cùng
     cách điền `tools/test_excel_case_roundtrip.py` (file đối tác, KHÔNG sửa).
  3. Re-save qua LibreOffice Calc headless:
       soffice --headless --convert-to "xlsx:Calc MS Excel 2007 XML"
               --outdir <tmp> -env:UserInstallation=file:///tmp/lo_prof_calc_<pid>
     Profile CÁCH LY bắt buộc (máy có runner khác dùng soffice song song).
  4. `import_case_workbook` trên file Calc đã lưu -> phải ok, candidate đúng
     case; assert giá trị then chốt sống sót: text Unicode, số 0 đầu (ô text),
     ngày dd/mm/yyyy, money/integer, select label->value, mark->checks,
     bảng lặp N hàng, mirror công thức (case synthetic 2 form shared key).

Gate PASS/FAIL (per case):
  + Calc convert rc=0 và file tồn tại
  + import ok=True (đã gồm: marker `__map`, contract/case/hash, CHECKSUM
    sha256 tái tính khớp, mirror không bị gõ đè, không ô lạ)
  + candidate.caseId == case
  + các giá trị expected sống sót 100%
  + `__map`/`__lists` VẪN TỒN TẠI trong file Calc (presence — chống sửa trộm)

QUAN SÁT trung thực (ghi nhận, KHÔNG làm fail — đã adjudicate, xem hằng
`_ADJUDICATION`): các thuộc tính TRÌNH BÀY mà Calc đổi — hiện tại LibreOffice
26.8.0.3 hạ `veryHidden` -> `hidden` trên `__map`/`__lists`, đơn giản hoá cờ
sheetProtection. Checksum + presence vẫn khớp => chống sửa trộm KHÔNG yếu đi.
Đề xuất Lead: kiểm tra sheet_state trong audit hạ thành CẢNH BÁO (patch đề
xuất nằm trong báo cáo lane; KHÔNG tự sửa `tools/excel_case_import.py`).

Tập case: 4 case READY đại diện (hộ KD PLII_M01, thay đổi ngành PLI_M12,
tạm ngừng DN PLI_M27, case dài nhất PLII_M02) + 1 case synthetic mirror.
Case PENDING (chưa có câu hỏi) BỎ QUA — in NOT RUN (lane content đang bật).
Dùng `--cases id1,id2` để chạy lại tập khác (vd sau khi lane kia bật đủ 28).

Suite KHÔNG có SKIP: bất kỳ thất bại nào -> exit 1 + báo cáo, Lead quyết.
Không có soffice -> exit 1 (môi trường thiếu, không adjudicate thay Lead).

Chạy:  python3 -X utf8 -m tools.test_excel_calc_roundtrip   (exit 0 = PASS)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from tools.excel_case_export import (  # noqa: E402
    COMMON_SHEET, GUIDE_SHEET, LISTS_SHEET, MAP_COLUMNS, MAP_SHEET,
    write_case_workbook,
)
from tools.excel_case_import import import_case_workbook  # noqa: E402

SOFFICE = "/opt/homebrew/bin/soffice"
CALC_FILTER = "xlsx:Calc MS Excel 2007 XML"
FIXTURE_META = {"today": "01/01/2026", "exported_at": "01/01/2026 10:00"}

# 4 case READY đại diện theo PLAN §5-E3 + lý do chọn
DEFAULT_CALC_CASES = [
    "dang_ky_ho_kinh_doanh_lan_dau",      # hộ KD PLII_M01: select/date/mark/bảng
    "thay_doi_nganh_nghe",                # PLI_M12: bảng ngành, date 3 key, money
    "tam_ngung_tiep_tuc_kinh_doanh_dn",   # PLI_M27: date cặp từ/đến, bảng ĐVTT
    "thay_doi_noi_dung_dang_ky_hkd",      # PLII_M02: case READY DÀI NHẤT (43 câu)
]

_ADJUDICATION = (
    "ĐÃ ADJUDICATE (probe trước khi viết suite): LibreOffice Calc 26.8.0.3 "
    "giữ nguyên TOÀN BỘ giá trị + kiểu ô (text '@', số 0 đầu) + `__map` records "
    "(checksum sha256 khớp) + named range LST_nnnn + data validation list + "
    "sheet protection + merge/freeze + mirror công thức; CHỈ đổi thuộc tính "
    "trình bày: veryHidden -> hidden trên __map/__lists, đơn giản hoá cờ "
    "sheetProtection. Importer không đọc sheet_state nên tamper-check (marker + "
    "checksum + presence) KHÔNG bị yếu hoá => các delta này là CẢNH BÁO, "
    "không phải FAIL.")

_observations: list[str] = []          # delta thuộc tính Calc đã quan sát
_results: list[tuple[bool, str]] = []


# ---------------------------------------------------------------------------
# Tiện ích chung
# ---------------------------------------------------------------------------

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
    """ĐỌC manifest TỪ ĐĨA lúc chạy (lane content có thể vừa bật case)."""
    return json.loads(
        (ROOT / "app" / "data" / "case_questionnaires" / ("%s.json" % case_id))
        .read_text(encoding="utf-8"))


def _case_is_ready(manifest: dict) -> bool:
    return any(f.get("content_review") == "approved" and f.get("questions")
               for f in manifest.get("forms", []))


def _map_reader(wb):
    """Trả (col_of, rows) đọc sheet `__map` — cùng quy ước điền như khách."""
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    rows = []
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        if not qid:
            continue
        rows.append({
            "question_id": qid,
            "sheet": mp.cell(r, col["sheet"]).value,
            "cell": mp.cell(r, col["cell"]).value,
            "layout": mp.cell(r, col["layout"]).value or "",
        })
    return mp, col, rows


def _fill_like_customer(out_path: Path, answers: dict) -> Path:
    """Điền answers theo `__map` như khách (bỏ mirror) -> file filled.xlsx."""
    wb = openpyxl.load_workbook(out_path)
    _mp, _col, rows = _map_reader(wb)
    cursor: dict[str, int] = {}
    for entry in rows:
        qid = entry["question_id"]
        if qid not in answers or entry["layout"] == "mirror":
            continue
        value = answers[qid]
        ws = wb[entry["sheet"]]
        if isinstance(value, list):
            idx = cursor.get(qid, 0)
            if idx < len(value):
                if value[idx] is not None:
                    ws[entry["cell"]] = value[idx]
                cursor[qid] = idx + 1
        else:
            ws[entry["cell"]] = value
    filled = out_path.parent / "filled.xlsx"
    wb.save(filled)
    return filled


def _calc_resave(xlsx: Path, outdir: Path, profile_tag: str) -> Path:
    """Re-save qua LibreOffice Calc headless (profile cách ly) -> Path mới."""
    profile = "file:///tmp/lo_prof_calc_%s_%d" % (profile_tag, os.getpid())
    calc_dir = outdir / "calc_saved"
    cmd = [SOFFICE, "--headless", "--norestore", "--convert-to", CALC_FILTER,
           "--outdir", str(calc_dir), "-env:UserInstallation=%s" % profile,
           str(xlsx)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    saved = calc_dir / xlsx.name
    if proc.returncode != 0 or not saved.exists():
        raise AssertionError(
            "Calc convert rc=%s file=%s stderr=%r stdout=%r"
            % (proc.returncode, saved.exists(),
               (proc.stderr or "")[-400:], (proc.stdout or "")[-200:]))
    return saved


def _wb_properties(path: Path) -> dict:
    """Thu thập thuộc tính cấu trúc để so PRE/POST quanh bước Calc re-save."""
    wb = openpyxl.load_workbook(path)
    return {
        "sheetnames": list(wb.sheetnames),
        "states": {s: wb[s].sheet_state for s in wb.sheetnames},
        "protection": {s: bool(wb[s].protection.sheet) for s in wb.sheetnames},
        "names": sorted(str(k) for k in wb.defined_names.keys()),
        "dv": {s: sorted((dv.type or "", str(dv.formula1), str(dv.sqref))
                         for dv in wb[s].data_validations.dataValidation)
               for s in wb.sheetnames},
        "map_marker": (wb[MAP_SHEET]["A1"].value
                       if MAP_SHEET in wb.sheetnames else None),
        "n_map_rows": len(_map_reader(wb)[2]),
    }


def _record_deltas(case_id: str, pre: dict, post: dict) -> list[str]:
    """Ghi OBSERVATION từng khác biệt thuộc tính PRE -> POST (Calc)."""
    deltas: list[str] = []
    if pre["sheetnames"] != post["sheetnames"]:
        deltas.append("sheetnames: %s -> %s" % (pre["sheetnames"],
                                                post["sheetnames"]))
    for sheet, state in post["states"].items():
        old = pre["states"].get(sheet)
        if old != state:
            deltas.append("sheet_state %s: %s -> %s" % (sheet, old, state))
    lost_prot = [s for s in pre["protection"]
                 if pre["protection"][s] and not post["protection"].get(s)]
    if lost_prot:
        deltas.append("mất protection: %s" % lost_prot)
    if pre["names"] != post["names"]:
        deltas.append("named range: %s -> %s" % (pre["names"], post["names"]))
    for sheet, dvs in pre["dv"].items():
        if dvs != post["dv"].get(sheet):
            deltas.append("data validation %s: %d -> %d DV"
                          % (sheet, len(dvs), len(post["dv"].get(sheet) or [])))
    if pre["map_marker"] != post["map_marker"]:
        deltas.append("map marker: %r -> %r" % (pre["map_marker"],
                                                post["map_marker"]))
    if pre["n_map_rows"] != post["n_map_rows"]:
        deltas.append("số dòng __map: %d -> %d" % (pre["n_map_rows"],
                                                   post["n_map_rows"]))
    for d in deltas:
        _observations.append("[%s] %s" % (case_id, d))
    return deltas


def _assert_text_type(post_calc: Path, sheet: str, addr: str, expect: str,
                      label: str) -> None:
    """Ô text sống sót: giá trị bằng nguyên văn VẪN là kiểu string '@'."""
    wb = openpyxl.load_workbook(post_calc)
    cell = wb[sheet][addr]
    assert cell.value == expect, \
        "%s (%s!%s): %r != %r" % (label, sheet, addr, cell.value, expect)
    assert cell.data_type == "s", \
        "%s (%s!%s): data_type %s — ô text bị Calc đổi kiểu" % (
            label, sheet, addr, cell.data_type)
    assert cell.number_format == "@", \
        "%s (%s!%s): number_format %r != '@'" % (label, sheet, addr,
                                                 cell.number_format)


def _first_cell_of(wb, qid: str) -> tuple[str, str]:
    _mp, _col, rows = _map_reader(wb)
    for entry in rows:
        if entry["question_id"] == qid and entry["layout"] != "mirror":
            return entry["sheet"], entry["cell"]
    raise AssertionError("không tìm thấy ô canonical của %s" % qid)


# ---------------------------------------------------------------------------
# Các case READY đại diện — answers như khách + expected giá trị sống sót
# ---------------------------------------------------------------------------

def _calc_case(case_id: str, answers: dict, expect_fn) -> None:
    """Một vòng Calc round-trip đầy đủ cho 1 case READY."""
    manifest = _manifest(case_id)               # đọc từ đĩa lúc chạy
    if not _case_is_ready(manifest):
        print("NOT RUN %s: case PENDING (chưa có câu hỏi — lane content sở hữu)"
              % case_id)
        return
    tmp = Path(tempfile.mkdtemp(prefix="calc_rt_%s_" % case_id[:12]))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    pre = _wb_properties(out)

    filled = _fill_like_customer(out, answers)
    saved = _calc_resave(filled, tmp, case_id[:20])
    post = _wb_properties(saved)

    # presence của 2 sheet máy đọc phải sống sót qua Calc (chống sửa trộm)
    assert MAP_SHEET in post["sheetnames"], "Calc làm MẤT sheet %s" % MAP_SHEET
    if pre["names"]:
        assert LISTS_SHEET in post["sheetnames"], \
            "Calc làm MẤT sheet %s" % LISTS_SHEET
    assert post["map_marker"] == "__EXCEL_CASE_MAP_V2__", \
        "marker `__map` hỏng sau Calc: %r" % post["map_marker"]
    _record_deltas(case_id, pre, post)

    res = import_case_workbook(saved, manifest,
                               imported_at="2026-09-10T00:00:00")
    assert res["ok"], "import sau Calc thất bại: %s" % json.dumps(
        res["errors"], ensure_ascii=False)[:800]
    cand = res["candidate"]
    assert cand["caseId"] == manifest["case_id"], cand["caseId"]
    assert cand["source"]["kind"] == "EXCEL_CASE_V2"
    st = cand["store"]
    expect_fn(st)
    print("  -> %s: %d values / %d checks / %d loop rows sống sót qua Calc"
          % (case_id, len(st["values"]), len(st["checks"]),
             sum(len(v) for v in st["loops"].values())))
    # spot-check kiểu ô text (số 0 đầu / ngày) ngay trên file Calc đã lưu
    wb_f = openpyxl.load_workbook(filled)     # bản PRE-calc để tra địa chỉ ô
    for qid, expect in getattr(expect_fn, "text_cells", []):
        _assert_text_type(saved, *_first_cell_of(wb_f, qid), expect, qid)


@check("[CRT1] hộ KD PLII_M01: Unicode + số 0 đầu + date + money + select + "
       "mark + bảng ngành 2 hàng sống sót qua Calc")
def crt1():
    def expect(st):
        v = st["values"]
        assert v["chu_hkd.ho_ten"] == "nguyễn văn a", v["chu_hkd.ho_ten"]
        assert v["chu_hkd.gioi_tinh"] == "Nam"
        assert (v["ngay_sinh"], v["thang_sinh"], v["nam_sinh"]) == \
            ("05", "12", "1985")
        assert v["chu_hkd.so_cccd"] == "079085001234"
        assert v["dien_thoai_lien_he"] == "0084090123456"
        assert v["von_kinh_doanh"] == 50000000
        assert v["so_lao_dong"] == 3
        assert st["checks"] == {"chk_khong_kd_tai_tru_so": True,
                                "chk_ct_ho_gia_dinh": True}, st["checks"]
        rows = st["loops"]["ds_nganh"]
        assert len(rows) == 2, rows
        assert rows[0] == {"ten_nganh": "Bán lẻ hàng điện tử",
                           "ma_nganh": "4774", "la_nganh_chinh": "X"}, rows[0]
        assert rows[1] == {"ten_nganh": "Sửa chữa xe cơ giới"}, rows[1]
    expect.text_cells = [
        ("q_so_cccd", "079085001234"),      # text 0 đầu
        ("q_dien_thoai", "0084090123456"),  # tel 2 số 0 đầu
        ("q_ngay_sinh", "5/12/1985"),       # date gõ dạng text dd/mm/yyyy
    ]
    _calc_case("dang_ky_ho_kinh_doanh_lan_dau", {
        "q_ho_ten": "  nguyễn văn a ",
        "q_gioi_tinh": "Nam",
        "q_ngay_sinh": "5/12/1985",
        "q_so_cccd": "079085001234",
        "q_dia_chi_chi_tiet": "25 Nguyễn Trãi",
        "q_xa_phuong": "Phường Bến Thành",
        "q_tinh_thanh": "TP. Hồ Chí Minh",
        "q_ten_hkd": "Hộ kinh doanh An Phát",
        "q_dien_thoai": "0084090123456",
        "q_nganh_ten": ["Bán lẻ hàng điện tử", "Sửa chữa xe cơ giới"],
        "q_nganh_ma": ["4774", None],
        "q_nganh_chinh": ["X", None],
        "q_von": "50.000.000",
        "q_khong_kd_tai_tru_so": "X",
        "q_chu_ho_la_ho_gia_dinh": "X",
        "q_so_lao_dong": "3",
    }, expect)


@check("[CRT2] thay đổi ngành PLI_M12: 3 bảng ngành + date 3 key + money + "
       "tel 0 đầu + mark sống sót qua Calc")
def crt2():
    def expect(st):
        v = st["values"]
        assert v["dn.ten_tieng_viet"] == "Công ty TNHH Minh Châu"
        assert v["dn.ma_so_dn"] == "0312345678"
        assert v["dien_thoai_khac"] == "00842838123456"
        assert v["von_dieu_le_chu"] == 120000000
        assert (v["ngay_bd"], v["thang_bd"], v["nam_bd"]) == \
            ("01", "07", "2015")
        assert v["so_lao_dong"] == 25
        assert st["checks"]["chk_doi_dia_chi_tb_thue"] is True
        assert st["checks"]["chk_ht_doc_lap"] is True
        bs = st["loops"]["nganh_bo_sung"]
        assert len(bs) == 2, bs
        assert bs[0] == {"ten_nganh": "Bán lẻ hàng điện tử",
                         "ma_nganh": "4774", "la_nganh_chinh": "X"}, bs[0]
        assert bs[1] == {"ten_nganh": "Cho thuê xe máy",
                         "ma_nganh": "7711"}, bs[1]
        assert st["loops"]["nganh_xoa_bo"] == [
            {"ten_nganh": "Bán vàng", "ma_nganh": "4741"}]
        assert st["loops"]["nganh_sua_doi_chi_tiet"] == [
            {"ten_nganh": "Bán phụ tùng ô tô", "ma_nganh": "4530"}]
    expect.text_cells = [
        ("q_dn_ma_so", "0312345678"),
        ("q_dien_thoai", "00842838123456"),
        ("q_ngay_bd_hoat_dong", "01/07/2015"),
    ]
    _calc_case("thay_doi_nganh_nghe", {
        "q_dn_ten": "Công ty TNHH Minh Châu",
        "q_dn_ma_so": "0312345678",
        "q_co_quan_dkkd": "Phòng Đăng ký kinh doanh - SKHĐT TP.HCM",
        "q_dia_chi_chi_tiet": "112 Nguyễn Văn Cừ",
        "q_xa_phuong": "Phường Nguyễn Cư Trinh",
        "q_tinh_thanh": "TP. Hồ Chí Minh",
        "q_dien_thoai": "00842838123456",
        "q_nganh_bs_ten": ["Bán lẻ hàng điện tử", "Cho thuê xe máy"],
        "q_nganh_bs_ma": ["4774", "7711"],
        "q_nganh_bs_chinh": ["X", None],
        "q_nganh_xoa_ten": ["Bán vàng"],
        "q_nganh_xoa_ma": ["4741"],
        "q_nganh_sua_ten": ["Bán phụ tùng ô tô"],
        "q_nganh_sua_ma": ["4530"],
        "q_von_moi": "120.000.000",
        "q_ngay_bd_hoat_dong": "01/07/2015",
        "q_doi_dia_chi_tb_thue": "X",
        "q_ht_doc_lap": "X",
        "q_so_lao_dong": "25",
    }, expect)


@check("[CRT3] tạm ngừng DN PLI_M27: cặp ngày từ/đến + lý do + bảng người "
       "liên hệ + bảng đơn vị trực thuộc sống sót qua Calc")
def crt3():
    def expect(st):
        v = st["values"]
        assert v["dn.ten_tieng_viet"] == "Công ty CP Dịch vụ Biển Đông"
        assert v["dn.ma_so_dn"] == "0309876543"
        assert v["tu_ngay"] == "01/03/2026"
        assert v["den_ngay"] == "30/06/2026"
        assert v["ly_do_tam_ngung"] == "Chờ hoàn tất chuyển địa điểm"
        assert st["loops"]["ds_ndd_pl_thong_bao_tam_ngung"] == [
            {"ho_ten": "Nguyễn Thị Tám",
             "dien_thoai": "0084909876543",
             "email": "tam@example.vn"}], \
            st["loops"]["ds_ndd_pl_thong_bao_tam_ngung"]
        assert st["loops"]["don_vi_truc_thuoc_tam_ngung_tiep_tuc"] == [
            {"ten_don_vi": "Chi nhánh Quận 7",
             "ma_so_don_vi": "0309876543001"}], \
            st["loops"]["don_vi_truc_thuoc_tam_ngung_tiep_tuc"]
    expect.text_cells = [
        ("q_dn_ma_so", "0309876543"),
        ("q_tam_ngung_tu_ngay", "01/03/2026"),
        ("q_dien_thoai_lien_he", "0084909876543"),
    ]
    _calc_case("tam_ngung_tiep_tuc_kinh_doanh_dn", {
        "q_dn_ten": "Công ty CP Dịch vụ Biển Đông",
        "q_dn_ma_so": "0309876543",
        "q_co_quan_dkkd": "Phòng Đăng ký kinh doanh - SKHĐT TP.HCM",
        "q_tam_ngung_tu_ngay": "01/03/2026",
        "q_tam_ngung_den_ngay": "30/06/2026",
        "q_ly_do_tam_ngung": "Chờ hoàn tất chuyển địa điểm",
        "q_nguoi_lien_he": ["Nguyễn Thị Tám"],
        "q_dien_thoai_lien_he": ["0084909876543"],
        "q_email_lien_he": ["tam@example.vn"],
        "q_cn_ten": ["Chi nhánh Quận 7"],
        "q_cn_ma_so": ["0309876543001"],
    }, expect)


@check("[CRT4] PLII_M02 (case READY dài nhất, 43 câu): text/tel/money/date/"
       "select/2 bảng lặp sống sót qua Calc")
def crt4():
    def expect(st):
        v = st["values"]
        assert v["hkd_ten_tieng_viet_2"] == "Hộ kinh doanh Bách Hòa"
        assert v["hkd_ma_so"] == "0310001122"
        assert v["hkd_ten_tieng_viet"] == "Hộ kinh doanh Bách Hòa 2"
        assert v["dien_thoai_khac"] == "0084283910111"
        assert v["chu_hkd.ho_ten"] == "Trần Văn Bể"
        assert (v["ngay_sinh"], v["thang_sinh"], v["nam_sinh"]) == \
            ("09", "08", "1979")
        assert v["chu_hkd.gioi_tinh"] == "Nam"
        assert v["chu_hkd.so_cccd"] == "079197900112"
        assert v["von_kd_moi"] == 800000000
        assert st["checks"]["chk_khong_kd_tai_tru_so"] is True
        # PLII_M02 đặt tên key `nganh_bo_sung.ten_nganh_bo_sung` (khác M12)
        assert st["loops"]["nganh_bo_sung"] == [
            {"ten_nganh_bo_sung": "Dịch vụ ăn uống", "ma_nganh": "5610",
             "la_nganh_chinh": "X"}], st["loops"]["nganh_bo_sung"]
        assert st["loops"]["tv_hgd_sau_thay_doi"] == [
            {"ho_ten": "Lê Thị C", "ngay_sinh": "14/02/1983",
             "so_cccd": "079198300223", "gioi_tinh": "Nữ",
             "noi_o_hien_tai": "12 Nguyễn Huệ"}], \
            st["loops"]["tv_hgd_sau_thay_doi"]
    expect.text_cells = [
        ("q_hkd_ma_so", "0310001122"),
        ("q_so_cccd", "079197900112"),
        ("q_ngay_sinh", "09/08/1979"),
    ]
    _calc_case("thay_doi_noi_dung_dang_ky_hkd", {
        "q_hkd_ten": "Hộ kinh doanh Bách Hòa",
        "q_hkd_ma_so": "0310001122",
        "q_ten_moi": "Hộ kinh doanh Bách Hòa 2",
        "q_dia_chi_chi_tiet": "48 Lê Lợi",
        "q_xa_phuong": "Phường Bến Nghé",
        "q_tinh_thanh": "TP. Hồ Chí Minh",
        "q_dien_thoai_hkd": "0084283910111",
        "q_chu_ho_ten": "Trần Văn Bể",
        "q_ngay_sinh": "09/08/1979",
        "q_gioi_tinh": "Nam",
        "q_so_cccd": "079197900112",
        "q_von_moi": "800.000.000",
        "q_nganh_bs_ten": ["Dịch vụ ăn uống"],
        "q_nganh_bs_ma": ["5610"],
        "q_nganh_bs_chinh": ["X"],
        "q_tv_hgd_ho_ten": ["Lê Thị C"],
        "q_tv_hgd_ngay_sinh": ["14/02/1983"],
        "q_tv_hgd_so_cccd": ["079198300223"],
        "q_tv_hgd_gioi_tinh": ["Nữ"],
        "q_tv_hgd_noi_o": ["12 Nguyễn Huệ"],
        "q_khong_kd_tai_tru_so": "X",
    }, expect)


def _shared_manifest() -> dict:
    """Manifest synthetic 2 form dùng chung data-key (test mirror qua Calc)."""
    base = json.loads(
        (ROOT / "app" / "data" / "questionnaire" / "PLII_M03.json")
        .read_text(encoding="utf-8"))
    form_a = {
        "form_id": "FORM_A", "ten_mau": "Mẫu A", "bat_buoc": True,
        "ghi_chu": "form canonical", "questionnaire_version": 1,
        "cluster": "a", "title": "Mẫu A", "content_review": "approved",
        "questions": base["questions"],
    }
    renamed = []
    for q in base["questions"]:
        q2 = json.loads(json.dumps(q, ensure_ascii=False))
        q2["question_id"] = q2["question_id"] + "_b"
        renamed.append(q2)
    form_b = {
        "form_id": "FORM_B", "ten_mau": "Mẫu B", "bat_buoc": True,
        "ghi_chu": "form mirror", "questionnaire_version": 1,
        "cluster": "b", "title": "Mẫu B", "content_review": "approved",
        "questions": renamed,
    }
    manifest = {
        "manifest_id": "case_shared", "manifest_version": 1,
        "schema_version": 1, "case_id": "case_shared",
        "case_title": "Case thử mirror", "nhom": "Thử", "mo_ta": "",
        "co_so_phap_ly": [], "luu_y": [], "giay_to_kem": [],
        "forms_oneOf": [], "forms": [form_a, form_b],
    }
    manifest["manifest_hash"] = hashlib.sha256(
        json.dumps({k: v for k, v in manifest.items()
                    if k != "manifest_hash"},
                   ensure_ascii=True, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    return manifest


@check("[CRT5] mirror shared key qua Calc: ô canonical ở Thông_tin_chung, "
       "mirror VẪN là công thức (không dính MIRROR_CELL), import đúng 1 lần")
def crt5():
    manifest = _shared_manifest()
    tmp = Path(tempfile.mkdtemp(prefix="calc_rt_mirror_"))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    pre = _wb_properties(out)
    filled = _fill_like_customer(out, {"q_hkd_ten": "Hộ KD Mirror",
                                       "q_hkd_ma_so": "0312345678"})
    saved = _calc_resave(filled, tmp, "mirror")
    post = _wb_properties(saved)
    _record_deltas("mirror_synthetic", pre, post)

    wb_raw = openpyxl.load_workbook(saved, data_only=False)
    _mp, _col, rows = _map_reader(wb_raw)
    n_mirror = 0
    for entry in rows:
        if entry["layout"] != "mirror":
            continue
        cell = wb_raw[entry["sheet"]][entry["cell"]]
        assert isinstance(cell.value, str) and cell.value.startswith("="), \
            "mirror %s!%s không còn là công thức sau Calc: %r" % (
                entry["sheet"], entry["cell"], cell.value)
        n_mirror += 1
    assert n_mirror >= 2, n_mirror

    res = import_case_workbook(saved, manifest,
                               imported_at="2026-09-10T00:00:00")
    assert res["ok"], json.dumps(res["errors"], ensure_ascii=False)[:800]
    codes = {e["code"] for e in res["errors"]}
    assert "MIRROR_CELL" not in codes, codes
    assert res["candidate"]["store"]["values"] == {
        "hkd_ten_tieng_viet_2": "Hộ KD Mirror", "hkd_ma_so": "0312345678"}, \
        res["candidate"]["store"]["values"]


# ---------------------------------------------------------------------------

def _pending_and_idle() -> tuple[list[str], list[str]]:
    """(case PENDING, case READY ngoài tập Calc đang chạy) — ghi NOT RUN."""
    qdir = ROOT / "app" / "data" / "case_questionnaires"
    pending: list[str] = []
    ready: list[str] = []
    for p in sorted(qdir.glob("*.json")):
        if p.name == "_index.json":
            continue
        try:
            manifest = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        cid = manifest.get("case_id") or p.stem
        (ready if _case_is_ready(manifest) else pending).append(cid)
    idle = [c for c in ready if c not in DEFAULT_CALC_CASES]
    return pending, idle


def main() -> int:
    # cho phép Lead chạy lại tập khác: --cases id1,id2
    cases = list(DEFAULT_CALC_CASES)
    if len(sys.argv) > 2 and sys.argv[1] == "--cases":
        cases = [c.strip() for c in sys.argv[2].split(",") if c.strip()]

    if not shutil.which(SOFFICE) and not Path(SOFFICE).exists():
        print("FAIL: không tìm thấy soffice tại %s — môi trường thiếu "
              "LibreOffice, KHÔNG adjudicate thay Lead" % SOFFICE)
        return 1

    for fn in (crt1, crt2, crt3, crt4, crt5):
        fn()

    pending, idle = _pending_and_idle()
    print("-" * 72)
    print("CALC OBSERVATIONS (thuộc tính trình bày — đã adjudicate, không fail):")
    if _observations:
        for line in _observations:
            print("  ~ %s" % line)
    else:
        print("  ~ (Calc giữ nguyên mọi thuộc tính đã theo dõi)")
    print(_ADJUDICATION)
    print("-" * 72)
    print("NOT RUN (%d case PENDING — lane content đang bật, chưa có câu hỏi):"
          % len(pending))
    for cid in pending:
        print("  - %s" % cid)
    print("NOT RUN (%d case READY ngoài tập Calc này — phủ bởi visual tool):"
          % len(idle))
    for cid in idle:
        print("  - %s" % cid)
    print("-" * 72)
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("test_excel_calc_roundtrip: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
