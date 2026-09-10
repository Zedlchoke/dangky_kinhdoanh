# -*- coding: utf-8 -*-
"""E3 — round-trip workbook CASE-LEVEL: export -> điền như khách -> import
candidate draft v2 nguyên tử giữ 100% giá trị
(PLAN_hoan_thien_pfat_hanh §5-E3, phần round-trip).

[RTC1] PLII_M01 (case hộ kinh doanh): text/tel/email giữ nguyên văn kể cả số
       0 đầu; date tách 3 key theo transform; money bỏ dấu chấm nghìn;
       select label -> value; mark scalar `chk_*` -> store.checks (bool);
       bảng lặp nganh N hàng giữ thứ tự, `la_nganh_chinh` giữ 'X'.
[RTC2] Bảng lặp 0/1/N hàng: bảng bỏ trống -> không có loop; 1 hàng; N hàng.
[RTC3] Candidate hình dạng draft v2: v/caseId/checkedForms/activeDocId/store
       {values, checks, loops} — khớp contract `FD.migrateDraft`/UI.
[RTC4] Shared key mirror (manifest synthetic 2 form dùng chung data-key):
       canonical ở `Thông_tin_chung` hỏi MỘT lần; form kia là mirror
       read-only tham chiếu; import chỉ lấy canonical (cấm last-write-wins).
[RTC5] Optional form (bat_buoc=false) vẫn có sheet + vào checkedForms.
[RTC6] Export deterministic: ghi ×2 cùng meta -> nội dung mọi ô/sheet giống
       nhau (xlsx là zip có mtime nên so NỘI DUNG, không so byte).
[RTC7] Cả 9 case READY: export -> import phiếu TRẮNG chỉ ra lỗi
       MISSING_REQUIRED (không lỗi khung) — layout mọi case hợp lệ.
[RTC8] Unicode + số 0 đầu: "0084…", tên tiếng Việt có dấu giữ 100%.
[RTC9] Escape export: label bắt đầu "=" được lưu dạng Text (data_type 's'),
       mở lại là chuỗi, KHÔNG thành công thức.
[RTC10] Style contract: ô điền number_format="@" + locked=False; ô khác
       locked=True; __map/__lists veryHidden.

Chạy:  python3 -X utf8 -m tools.test_excel_case_roundtrip   (exit 0 = PASS)
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
    COMMON_SHEET, DOCS_SHEET, GUIDE_SHEET, LISTS_SHEET, MAP_COLUMNS,
    MAP_SHEET, workbook_stem, write_case_workbook,
)
from tools.excel_case_import import import_case_workbook  # noqa: E402

# Wave E4: MỌI case đều READY (28/28) — RTC7/RTC11 chạy trên list này
ALL_CASES = sorted(p.stem for p in
                   (ROOT / "app" / "data" / "case_questionnaires")
                   .glob("*.json") if p.stem != "_index")

FIXTURE_META = {"today": "01/01/2026", "exported_at": "01/01/2026 10:00"}

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


def fill_and_import(manifest: dict, answers: dict,
                    tmp_prefix: str = "rt_case_"):
    """Export workbook -> điền answers theo __map (như khách) -> import.

    answers: {question_id: giá-trị | [giá_trị_từng_hàng_bảng]}. Trả kết quả
    import_case_workbook.
    """
    tmp = Path(tempfile.mkdtemp(prefix=tmp_prefix))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    wb = openpyxl.load_workbook(out)
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1
           for i in range(len(MAP_COLUMNS))}
    cursor: dict[str, int] = {}
    for r in range(4, mp.max_row + 1):
        qid = mp.cell(r, col["question_id"]).value
        if qid not in answers:
            continue
        layout = mp.cell(r, col["layout"]).value
        if layout == "mirror":
            continue  # mirror tự phản chiếu — không điền
        value = answers[qid]
        cell = mp.cell(r, col["cell"]).value
        ws = wb[mp.cell(r, col["sheet"]).value]
        if isinstance(value, list):
            idx = cursor.get(qid, 0)
            if idx < len(value):
                ws[cell] = value[idx]
                cursor[qid] = idx + 1
        else:
            ws[cell] = value
    filled = tmp / "filled.xlsx"
    wb.save(filled)
    return import_case_workbook(filled, manifest,
                                imported_at="2026-09-10T00:00:00")


@check("[RTC1] hộ KD: scalar/mark->checks/select/date 3 key/money/bảng ngành")
def rtc1():
    manifest = _manifest("dang_ky_ho_kinh_doanh_lan_dau")
    res = fill_and_import(manifest, {
        "q_ho_ten": "  nguyễn văn a ",           # trim -> giữ nguyên văn
        "q_gioi_tinh": "Nam",                    # label -> value
        "q_ngay_sinh": "5/12/1985",              # 1 chữ số -> "05"/"12"
        "q_so_cccd": "079085001234",             # số 0 đầu giữ 100%
        "q_dia_chi_chi_tiet": "25 Nguyễn Trãi",
        "q_xa_phuong": "Phường Bến Thành",
        "q_tinh_thanh": "TP. Hồ Chí Minh",
        "q_ten_hkd": "Hộ kinh doanh An Phát",
        "q_dien_thoai": "0084090123456",         # tel 2 số 0 đầu
        "q_nganh_ten": ["Bán lẻ hàng điện tử", "Sửa chữa xe cơ giới"],
        "q_nganh_ma": ["4774", None],
        "q_nganh_chinh": ["X", None],
        "q_von": "50.000.000",
        "q_khong_kd_tai_tru_so": "X",
        "q_chu_ho_la_ho_gia_dinh": "X",
        "q_so_lao_dong": "3",
    })
    assert res["ok"], res["errors"]
    st = res["candidate"]["store"]
    assert st["values"]["chu_hkd.ho_ten"] == "nguyễn văn a"
    assert st["values"]["chu_hkd.gioi_tinh"] == "Nam"
    assert (st["values"]["ngay_sinh"], st["values"]["thang_sinh"],
            st["values"]["nam_sinh"]) == ("05", "12", "1985")
    assert st["values"]["chu_hkd.so_cccd"] == "079085001234"
    assert st["values"]["dien_thoai_lien_he"] == "0084090123456"
    assert st["values"]["von_kinh_doanh"] == 50000000
    assert st["values"]["so_lao_dong"] == 3
    assert st["checks"] == {"chk_khong_kd_tai_tru_so": True,
                            "chk_ct_ho_gia_dinh": True}, st["checks"]
    rows = st["loops"]["ds_nganh"]
    assert len(rows) == 2, rows
    assert rows[0] == {"ten_nganh": "Bán lẻ hàng điện tử",
                       "ma_nganh": "4774", "la_nganh_chinh": "X"}, rows[0]
    assert rows[1] == {"ten_nganh": "Sửa chữa xe cơ giới"}, rows[1]


@check("[RTC2] bảng lặp 0/1/N hàng — bảng trống không sinh loop")
def rtc2():
    manifest = _manifest("dang_ky_ho_kinh_doanh_lan_dau")
    # nganh là bảng BẮT BUỘC ≥1 hàng (D7.3-A) — dùng tv_hgd (tùy chọn) cho
    # case 0 hàng; nganh dùng cho 1/N hàng.
    common = {
        "q_ho_ten": "nguyễn văn a", "q_so_cccd": "079085001234",
        "q_dia_chi_chi_tiet": "25 Nguyễn Trãi",
        "q_xa_phuong": "Phường Bến Thành",
        "q_tinh_thanh": "TP. Hồ Chí Minh", "q_ten_hkd": "Hộ KD B",
        "q_nganh_ten": ["Bán vàng"], "q_nganh_chinh": ["X"],
    }
    zero = fill_and_import(manifest, dict(common), tmp_prefix="rt0_")
    assert zero["ok"], zero["errors"]
    loops = zero["candidate"]["store"]["loops"]
    assert "ds_tv_ho_gia_dinh" not in loops, loops

    one = fill_and_import(manifest, {
        **common, "q_tv_hgd_ho_ten": ["Trần B"],
    }, tmp_prefix="rt1_")
    assert one["ok"], one["errors"]
    rows = one["candidate"]["store"]["loops"]["ds_tv_ho_gia_dinh"]
    assert rows == [{"ho_ten": "Trần B"}], rows

    many = fill_and_import(manifest, {
        **common, "q_nganh_ten": ["A", "B", "C"],
    }, tmp_prefix="rt3_")
    assert many["ok"], many["errors"]
    rows = many["candidate"]["store"]["loops"]["ds_nganh"]
    assert [r["ten_nganh"] for r in rows] == ["A", "B", "C"], rows


@check("[RTC3] candidate hình dạng draft v2 (migrateDraft/UI đọc được)")
def rtc3():
    manifest = _manifest("tam_ngung_tiep_tuc_kinh_doanh_hkd")  # PLII_M03
    res = fill_and_import(manifest, {
        "q_hkd_ten": "Hộ KD C", "q_hkd_ma_so": "0312345678",
    })
    assert res["ok"], res["errors"]
    c = res["candidate"]
    assert c["v"] == 2
    assert c["caseId"] == manifest["case_id"]
    assert c["checkedForms"] == ["PLII_M03"]
    assert c["activeDocId"] == "PLII_M03"
    assert c["autoSum"] is False
    assert set(c["store"].keys()) == {"values", "checks", "loops"}
    assert set(c["source"].keys()) >= {"kind", "manifest_hash",
                                       "file_sha256"}
    assert c["source"]["kind"] == "EXCEL_CASE_V2"
    assert res["audit"]["file_sha256"] == c["source"]["file_sha256"]


def _shared_manifest() -> dict:
    """Manifest synthetic 2 form dùng chung data-key (test mirror)."""
    base = json.loads(
        (ROOT / "app" / "data" / "questionnaire" / "PLII_M03.json")
        .read_text(encoding="utf-8"))
    form_a = {
        "form_id": "FORM_A", "ten_mau": "Mẫu A", "bat_buoc": True,
        "ghi_chu": "form canonical", "questionnaire_version": 1,
        "cluster": "a", "title": "Mẫu A",
        "content_review": "approved",
        "questions": base["questions"],
    }
    renamed = []
    for q in base["questions"]:
        q2 = json.loads(json.dumps(q, ensure_ascii=False))
        q2["question_id"] = q2["question_id"] + "_b"
        renamed.append(q2)
    form_b = {
        "form_id": "FORM_B", "ten_mau": "Mẫu B", "bat_buoc": False,
        "ghi_chu": "form mirror", "questionnaire_version": 1,
        "cluster": "b", "title": "Mẫu B",
        "content_review": "approved",
        "questions": renamed,
    }
    # Wave E4: form tùy chọn ngoài oneOf mang câu mark `optionalForm.*`
    # (builder nhúng) — đánh X mới đưa form vào checkedForms.
    form_b["questions"].append({
        "question_id": "q_opt_FORM_B",
        "group": "Các mẫu tùy chọn trong hồ sơ",
        "text": "Bạn có làm mẫu «Mẫu B» không? (đánh X nếu CÓ làm mẫu này)",
        "type": "mark",
        "options": [{"value": "X", "label": "Có"}],
        "version": 1,
        "data_key": "optionalForm.FORM_B",
    })
    manifest = {
        "manifest_id": "case_shared", "manifest_version": 1,
        "schema_version": 1, "case_id": "case_shared",
        "case_title": "Case thử mirror", "nhom": "Thử", "mo_ta": "",
        "co_so_phap_ly": [], "luu_y": [], "giay_to_kem": [],
        "forms_oneOf": [], "forms": [form_a, form_b],
    }
    manifest["manifest_hash"] = __import__("hashlib").sha256(
        json.dumps({k: v for k, v in manifest.items()
                    if k != "manifest_hash"},
                   ensure_ascii=True, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    return manifest


@check("[RTC4] shared key: canonical hỏi 1 lần ở Thông_tin_chung, mirror đọc theo")
def rtc4():
    manifest = _shared_manifest()
    tmp = Path(tempfile.mkdtemp(prefix="rt_mirror_"))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    wb = openpyxl.load_workbook(out)
    # canonical nằm ở COMMON; hai form sheet là mirror tham chiếu
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    layouts = {}
    for r in range(4, mp.max_row + 1):
        key = (mp.cell(r, col["sheet"]).value,
               mp.cell(r, col["question_id"]).value)
        layouts[key] = mp.cell(r, col["layout"]).value
    assert layouts.get((COMMON_SHEET, "q_hkd_ma_so")) == "single"
    assert layouts.get(("01_Mẫu A", "q_hkd_ma_so")) == "mirror"
    assert layouts.get(("02_Mẫu B", "q_hkd_ma_so_b")) == "mirror"
    # ô mirror chứa công thức tham chiếu + khóa
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["layout"]).value != "mirror":
            continue
        ws = wb[mp.cell(r, col["sheet"]).value]
        cell = ws[mp.cell(r, col["cell"]).value]
        assert isinstance(cell.value, str) and cell.value.startswith("="), \
            cell.value
        assert cell.protection.locked, cell.coordinate
    # điền canonical -> import lấy giá trị ĐÚNG MỘT LẦN cho từng key
    wb2 = openpyxl.load_workbook(out)
    mp2 = wb2[MAP_SHEET]
    for r in range(4, mp2.max_row + 1):
        if mp2.cell(r, col["question_id"]).value in ("q_hkd_ten",
                                                     "q_hkd_ma_so") and \
                mp2.cell(r, col["layout"]).value == "single":
            wb2[mp2.cell(r, col["sheet"]).value][
                mp2.cell(r, col["cell"]).value] = \
                "Hộ KD Mirror" if mp2.cell(r, col["question_id"]).value == \
                "q_hkd_ten" else "0312345678"
    filled = tmp / "filled.xlsx"
    wb2.save(filled)
    res = import_case_workbook(filled, manifest)
    assert res["ok"], res["errors"]
    assert res["candidate"]["store"]["values"]["hkd_ma_so"] == "0312345678"


@check("[RTC5] optional form: sheet vẫn có; checkedForms theo câu opt-in E4")
def rtc5():
    manifest = _shared_manifest()
    manifest["forms"][1]["bat_buoc"] = False
    manifest["manifest_hash"] = __import__("hashlib").sha256(
        json.dumps({k: v for k, v in manifest.items()
                    if k != "manifest_hash"},
                   ensure_ascii=True, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    # Không đánh X "Có làm mẫu này không?" -> form tùy chọn KHÔNG vào
    # checkedForms (design E4); ô của nó trống -> không lỗi, import ok.
    res = fill_and_import(manifest, {"q_hkd_ten": "Hộ KD D",
                                     "q_hkd_ma_so": "0312345679"})
    assert res["ok"], res["errors"]
    c = res["candidate"]
    assert c["checkedForms"] == ["FORM_A"], c["checkedForms"]
    assert c["activeDocId"] == "FORM_A"
    assert c["store"]["values"]["hkd_ma_so"] == "0312345679"
    # Đánh X -> form tùy chọn vào checkedForms; activeDocId vẫn form bắt buộc
    res2 = fill_and_import(manifest, {"q_hkd_ten": "Hộ KD D",
                                      "q_hkd_ma_so": "0312345679",
                                      "q_opt_FORM_B": "X"})
    assert res2["ok"], res2["errors"]
    c2 = res2["candidate"]
    assert c2["checkedForms"] == ["FORM_A", "FORM_B"], c2["checkedForms"]
    assert c2["activeDocId"] == "FORM_A"     # bat_buoc ưu tiên làm active
    assert res2["audit"]["forms"] == ["FORM_A", "FORM_B"]


@check("[RTC6] export ×2 same cell-content (so nội dung — zip có mtime)")
def rtc6():
    manifest = _manifest("cham_dut_hoat_dong_hkd")
    tmp = Path(tempfile.mkdtemp(prefix="rt_det_"))
    a = write_case_workbook(manifest, tmp / "a.xlsx", meta=FIXTURE_META)
    b = write_case_workbook(manifest, tmp / "b.xlsx", meta=FIXTURE_META)
    wa, wb2 = openpyxl.load_workbook(a), openpyxl.load_workbook(b)
    assert wa.sheetnames == wb2.sheetnames
    for name in wa.sheetnames:
        sa, sb = wa[name], wb2[name]
        assert (sa.max_row, sa.max_column) == (sb.max_row, sb.max_column), name
        for row in sa.iter_rows():
            for cell in row:
                if cell.value is not None:
                    assert sb[cell.coordinate].value == cell.value, \
                        "%s!%s" % (name, cell.coordinate)


@check("[RTC7] cả 28 case READY: import phiếu TRẮNG chỉ ra MISSING_REQUIRED")
def rtc7():
    assert len(ALL_CASES) == 28, ALL_CASES
    for case_id in ALL_CASES:
        manifest = _manifest(case_id)
        tmp = Path(tempfile.mkdtemp(prefix="rt_all_"))
        out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
        res = import_case_workbook(out, manifest)
        assert res["ok"] is False and res["candidate"] is None, case_id
        codes = {e["code"] for e in res["errors"]}
        assert codes <= {"MISSING_REQUIRED"}, \
            "%s: lỗi khung %s" % (case_id, codes)
        assert codes, "%s: phiếu bắt buộc trống phải có lỗi" % case_id


@check("[RTC8] Unicode + số 0 đầu giữ 100% qua round-trip")
def rtc8():
    manifest = _manifest("dang_ky_ho_kinh_doanh_lan_dau")
    weird_name = "Ông Ba Ø–€ „nháy” \t胸口 007"
    res = fill_and_import(manifest, {
        "q_ho_ten": weird_name,
        "q_so_cccd": "007908500123",
        "q_dia_chi_chi_tiet": "Số 0 Đường 00",
        "q_xa_phuong": "Xã 0 Phường 00",
        "q_tinh_thanh": "Tỉnh 00",
        "q_ten_hkd": "Hộ KD 00 Việt Nam ß",
        "q_nganh_ten": ["Bán hàng 00"],
    })
    assert res["ok"], res["errors"]
    st = res["candidate"]["store"]["values"]
    assert st["chu_hkd.ho_ten"] == weird_name, st["chu_hkd.ho_ten"]
    assert st["chu_hkd.so_cccd"] == "007908500123"


@check("[RTC9] escape export: label đầu '=' lưu dạng Text, không thành công thức")
def rtc9():
    manifest = _manifest("cham_dut_hoat_dong_hkd")
    manifest = json.loads(json.dumps(manifest, ensure_ascii=False))
    manifest["forms"][0]["questions"][0]["text"] = "=1+1 Hộ kinh doanh tên?"
    tmp = Path(tempfile.mkdtemp(prefix="rt_esc_"))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    wb = openpyxl.load_workbook(out, data_only=True)
    ws = wb[[s for s in wb.sheetnames if s.startswith("01_")][0]]
    hits = [c for row in ws.iter_rows(max_col=1) for c in row
            if isinstance(c.value, str) and c.value.startswith("=1+1")]
    assert len(hits) == 1, hits
    assert hits[0].data_type == "s", hits[0].data_type


@check("[RTC10] style: ô điền '@' + unlocked, sheet khác locked, __map/__lists veryHidden")
def rtc10():
    manifest = _manifest("dang_ky_ho_kinh_doanh_lan_dau")
    tmp = Path(tempfile.mkdtemp(prefix="rt_style_"))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    wb = openpyxl.load_workbook(out)
    assert wb[MAP_SHEET].sheet_state == "veryHidden"
    assert wb[LISTS_SHEET].sheet_state == "veryHidden"
    assert wb[GUIDE_SHEET].protection.sheet
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    checked_fill = 0
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["layout"]).value != "single":
            continue
        ws = wb[mp.cell(r, col["sheet"]).value]
        cell = ws[mp.cell(r, col["cell"]).value]
        assert cell.number_format == "@", cell.coordinate
        assert cell.protection.locked == \
            bool(mp.cell(r, col["autofill"]).value), cell.coordinate
        assert cell.fill.fgColor.rgb in ("00FFF2CC", "00D9D9D9"), cell.coordinate
        checked_fill += 1
        if checked_fill >= 5:
            break
    assert checked_fill >= 5
    # tên file contract: DKKD_<caseId>_<hash8>
    stem = workbook_stem(manifest)
    assert stem == "DKKD_%s_%s" % (manifest["case_id"],
                                   manifest["manifest_hash"][:8]), stem


def _checked_forms_of(manifest: dict, wb=None) -> set:
    """Bộ form filler coi là ĐƯỢC CHỌN (E4): chọn option ĐẦU của từng nhóm
    oneOf; tick mọi câu optionalForm (form tùy chọn ngoài oneOf); form
    bat_buoc luôn được chọn."""
    checked: set = set()
    for group in manifest.get("forms_oneOf") or []:
        ids = group.get("ids") or []
        if ids:
            checked.add(ids[0])
    for form in manifest["forms"]:
        fid = form["form_id"]
        if form.get("bat_buoc", True):
            checked.add(fid)
    for form in manifest["forms"]:
        fid = form["form_id"]
        if any(str(q.get("data_key", "")).startswith("optionalForm.")
               for q in form["questions"]):
            checked.add(fid)
    return checked


def fill_all_like_client(manifest: dict, tmp_prefix: str = "rt28_") -> dict:
    """E4 — filler tự động data-type-aware từ __map cho CẢ case:
    điền mọi ô của các form được chọn (text riêng từng ô; date/money/integer/
    select/mark theo type; mark luôn 'X' để mọi `when` kích hoạt). Ô của form
    KHÔNG được chọn và ô mirror không đụng tới. Trả kết quả import."""
    tmp = Path(tempfile.mkdtemp(prefix=tmp_prefix))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    wb = openpyxl.load_workbook(out)
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    questions = {q["question_id"]: q for f in manifest["forms"]
                 for q in f["questions"]}
    checked = _checked_forms_of(manifest)
    seq_by_qid: dict[str, int] = {}
    for r in range(4, mp.max_row + 1):
        layout = mp.cell(r, col["layout"]).value
        if layout == "mirror":
            continue
        form_id = mp.cell(r, col["form_id"]).value
        if form_id not in checked:
            continue
        qid = mp.cell(r, col["question_id"]).value
        q = questions[qid]
        sheet = mp.cell(r, col["sheet"]).value
        cell = mp.cell(r, col["cell"]).value
        seq = seq_by_qid.get(qid, 0)
        t = q["type"]
        if t == "select":
            value = q["options"][0]["label"]
        elif t == "mark":
            value = "X"
        elif t == "date":
            value = "01/02/2026"
        elif t == "money":
            value = "1.000"
        elif t == "integer":
            value = "5"
        else:
            value = "Giá trị %d" % seq          # từng hàng bảng KHÁC nhau
        wb[sheet][cell] = value
        seq_by_qid[qid] = seq + 1
    filled = tmp / "filled.xlsx"
    wb.save(filled)
    return import_case_workbook(filled, manifest,
                                imported_at="2026-09-10T00:00:00")


@check("[RTC11] round-trip ĐỦ 28 case: filler type-aware -> import ok")
def rtc11():
    assert len(ALL_CASES) == 28, ALL_CASES
    for case_id in ALL_CASES:
        manifest = _manifest(case_id)
        res = fill_all_like_client(manifest, tmp_prefix="rt28_%s_" % case_id)
        assert res["ok"], "%s: %s" % (
            case_id, [(e["code"], e.get("cell"), e["message"])
                      for e in res["errors"][:5]])
        st = res["candidate"]["store"]
        assert st["values"] or st["checks"] or st["loops"], case_id
        assert not any(str(k).startswith(("oneOf.", "optionalForm."))
                       for k in list(st["values"]) + list(st["checks"])), \
            "%s: pseudo-key rò rỉ vào store" % case_id


@check("[RTC12] case dài nhất mỗi cụm: điền có chọn lọc + assert giá trị cụ thể")
def rtc12():
    # case dài nhất (nhiều map row) của từng nhóm — điền CHỈ các câu bắt buộc
    by_group: dict[str, list] = {}
    for case_id in ALL_CASES:
        m = _manifest(case_id)
        by_group.setdefault(m.get("nhom") or "", []).append(m)
    for nhom, manifests in by_group.items():

        def n_rows(m):
            return len(m["forms"]) + sum(len(f["questions"])
                                         for f in m["forms"])
        longest = max(manifests, key=n_rows)
        checked = _checked_forms_of(longest)
        tmp = Path(tempfile.mkdtemp(prefix="rt12_"))
        out = write_case_workbook(longest, tmp / "wb.xlsx",
                                  meta=FIXTURE_META)
        wb = openpyxl.load_workbook(out)
        mp = wb[MAP_SHEET]
        col = {mp.cell(3, i + 1).value: i + 1
               for i in range(len(MAP_COLUMNS))}
        questions = {q["question_id"]: q for f in longest["forms"]
                     for q in f["questions"]}
        cursor: dict[str, int] = {}
        for r in range(4, mp.max_row + 1):
            if mp.cell(r, col["layout"]).value == "mirror":
                continue
            if mp.cell(r, col["form_id"]).value not in checked:
                continue
            qid = mp.cell(r, col["question_id"]).value
            q = questions[qid]
            sheet = mp.cell(r, col["sheet"]).value
            cell = mp.cell(r, col["cell"]).value
            layout = mp.cell(r, col["layout"]).value
            if layout == "table":
                if not q.get("required"):
                    continue      # phiếu tối thiểu: chỉ hàng đầu bảng cần
                idx = cursor.get(qid, 0)
                if idx == 0:      # chỉ hàng đầu của bảng bắt buộc
                    t = q["type"]
                    wb[sheet][cell] = \
                        q["options"][0]["label"] if t == "select" else \
                        "X" if t == "mark" else "Bán lẻ hàng điện tử"
                    cursor[qid] = 1
                continue
            if not q.get("required") and q.get("type") not in ("select",) \
                    and not str(q.get("data_key", "")).startswith(
                        ("oneOf.", "optionalForm.")):
                continue          # phiếu tối thiểu: bắt buộc + selector
            t = q["type"]
            value = q["options"][0]["label"] if t == "select" else \
                "X" if t == "mark" else "01/02/2026" if t == "date" else \
                "1.000" if t == "money" else "5" if t == "integer" else \
                "Dữ liệu %s" % qid
            wb[sheet][cell] = value
        res = import_case_workbook(_save(tmp, wb), longest)
        assert res["ok"], "%s/%s: %s" % (
            nhom, longest["case_id"], [(e["code"], e.get("cell"))
                                       for e in res["errors"][:5]])
        st = res["candidate"]["store"]
        # giá trị cụ thể: có store thực và đúng hình dạng
        assert st["values"] or st["checks"], longest["case_id"]
        if "dn.ten_tieng_viet" in st["values"]:
            assert st["values"]["dn.ten_tieng_viet"].startswith("Dữ liệu q_")
        if "ds_nganh" in st["loops"]:
            row0 = st["loops"]["ds_nganh"][0]
            assert row0.get("ten_nganh") == "Bán lẻ hàng điện tử", row0


def _save(tmp: Path, wb) -> Path:
    filled = tmp / "filled.xlsx"
    wb.save(filled)
    return filled


@check("[RTC13] sheet Giấy_tờ_cần_gửi: checklist thật + cơ sở pháp lý + nguồn")
def rtc13():
    for case_id in ("thanh_lap_tnhh_1tv",        # có giay_to_kem
                    "lap_dia_diem_kinh_doanh",   # giay_to_kem rỗng
                    ):
        manifest = _manifest(case_id)
        tmp = Path(tempfile.mkdtemp(prefix="rt13_"))
        out = write_case_workbook(manifest, tmp / "wb.xlsx",
                                  meta=FIXTURE_META)
        wb = openpyxl.load_workbook(out, data_only=True)
        ws = wb[DOCS_SHEET]
        texts = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    texts.append(str(cell.value))
        joined = "\n".join(texts)
        assert "CHỜ DUYỆT" not in joined and "chưa duyệt" not in joined, \
            "%s: còn watermark" % case_id
        assert "GIẤY TỜ CẦN CHUẨN BỊ NỘP KÈM" in joined
        assert "Nguồn: Nghị định 168/2025/NĐ-CP, TT 121/2026/TT-BTC" in joined
        for ref in manifest.get("co_so_phap_ly") or []:
            assert str(ref) in joined, "%s: thiếu cơ sở pháp lý %r" % (
                case_id, ref)
        for item in manifest.get("giay_to_kem") or []:
            assert str(item) in joined, "%s: thiếu giấy tờ %r" % (case_id,
                                                                  item)
        if not manifest.get("giay_to_kem"):
            assert "không khai danh mục giấy tờ" in joined
        else:
            # ô tick là ô vàng mở khóa đầu mỗi dòng checklist
            unlocked = [c for r in ws.iter_rows(min_col=1, max_col=1)
                        for c in r
                        if c.protection is not None
                        and c.protection.locked is False]
            assert len(unlocked) >= len(manifest["giay_to_kem"]), case_id


def main() -> int:
    for fn in (rtc1, rtc2, rtc3, rtc4, rtc5, rtc6, rtc7, rtc8, rtc9, rtc10,
               rtc11, rtc12, rtc13):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_excel_case_roundtrip: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
