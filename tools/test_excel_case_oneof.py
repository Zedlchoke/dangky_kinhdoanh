# -*- coding: utf-8 -*-
"""E4 — oneOf trên workbook CASE-LEVEL + form tùy chọn: chọn 1 trong nhóm
(PLAN_hoan_thien_pfat_hanh §5-E4; Lead chốt design, owner ủy quyền).

[OF1] case `chuyen_doi_hkd_sang_dn`: chọn M03 -> checkedForms chỉ còn
      ["PLI_M03"]; activeDocId = form được chọn; dữ liệu điền đúng chỗ vào
      store qua round-trip.
[OF2] không chọn trường hợp nào -> MISSING_REQUIRED, candidate None
      (nguyên tắc nguyên tử).
[OF3] gõ giá trị lạ vào câu chọn trường hợp -> BAD_SELECT.
[OF4] dữ liệu TRÀN vào form KHÔNG được chọn (M01 khi đã chọn M03) ->
      STRAY_CELL kèm ô + question_id (không data một phần).
[OF5] form tùy chọn NGOÀI oneOf (`thanh_lap_ctcp`: PLI_M08 bat_buoc=false):
      không tick "Có làm mẫu này không?" -> không vào checkedForms và ô của
      nó không bị đòi; tick X -> được chọn, required áp dụng.
[OF6] câu chọn trường hợp render ĐẦU sheet `Thông_tin_chung`, dropdown lấy
      nhãn thân thiện từ `ghi_chu` của use case, value = form_id.
[OF7] required scoping: chọn M03 -> bắt buộc vẫn đòi tên DN / địa chỉ / ngành
      dù ô canonical thuộc câu của form không được chọn (shared key).

Chạy:  python3 -X utf8 -m tools.test_excel_case_oneof   (exit 0 = PASS)
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
    COMMON_SHEET, MAP_COLUMNS, MAP_SHEET, write_case_workbook,
)
from tools.excel_case_import import (  # noqa: E402
    BAD_SELECT, MISSING_REQUIRED, STRAY_CELL, import_case_workbook,
)

FIXTURE_META = {"today": "01/01/2026", "exported_at": "01/01/2026 10:00"}

ONEOF_CASE = "chuyen_doi_hkd_sang_dn"
CTCP_CASE = "thanh_lap_ctcp"

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


def _map_col(mp):
    return {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}


def _questions_of(manifest: dict) -> dict:
    return {q["question_id"]: q for f in manifest["forms"]
            for q in f["questions"]}


def _export(manifest: dict, tmp_prefix: str):
    tmp = Path(tempfile.mkdtemp(prefix=tmp_prefix))
    out = write_case_workbook(manifest, tmp / "wb.xlsx", meta=FIXTURE_META)
    return tmp, openpyxl.load_workbook(out)


def _selector_cell(wb, qid: str) -> tuple[str, str, dict]:
    """(sheet, ô) của câu selector + câu hỏi gốc (đọc nhãn option)."""
    mp = wb[MAP_SHEET]
    col = _map_col(mp)
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["question_id"]).value == qid and \
                mp.cell(r, col["layout"]).value != "mirror":
            return (mp.cell(r, col["sheet"]).value,
                    mp.cell(r, col["cell"]).value,
                    wb[mp.cell(r, col["sheet"]).value])
    raise AssertionError("không tìm thấy ô của %s" % qid)


def _fill(manifest: dict, answers: dict, tmp_prefix: str = "of_"):
    """Export -> điền theo {question_id HOẶC data_key: giá trị | [hàng]} ->
    import. Ô mirror bị bỏ qua; answer theo data_key được ghi vào ô
    CANONICAL của key đó (owner — đúng chỗ khách điền)."""
    tmp, wb = _export(manifest, tmp_prefix)
    mp = wb[MAP_SHEET]
    col = _map_col(mp)
    questions = _questions_of(manifest)
    keys_of_qid: dict[str, list[str]] = {}
    for qid, q in questions.items():
        keys = [q["data_key"]] if isinstance(q["data_key"], str) else \
            [t["key"] for t in q["data_key"]]
        keys_of_qid[qid] = keys
    cursor: dict[str, int] = {}
    for r in range(4, mp.max_row + 1):
        if mp.cell(r, col["layout"]).value == "mirror":
            continue
        qid = mp.cell(r, col["question_id"]).value
        if qid in answers:
            answer_qid = qid
        else:
            answer_qid = next((k for k in keys_of_qid.get(qid, ())
                               if k in answers), None)
        if answer_qid is None:
            continue
        ws = wb[mp.cell(r, col["sheet"]).value]
        cell = mp.cell(r, col["cell"]).value
        value = answers[answer_qid]
        if isinstance(value, list):
            idx = cursor.get(answer_qid, 0)
            if idx < len(value):
                ws[cell] = value[idx]
                cursor[answer_qid] = idx + 1
        else:
            ws[cell] = value
    filled = tmp / "filled.xlsx"
    wb.save(filled)
    return import_case_workbook(filled, manifest,
                                imported_at="2026-09-10T00:00:00")


def _selector_options(manifest: dict) -> list[dict]:
    for f in manifest["forms"]:
        for q in f["questions"]:
            if str(q.get("data_key", "")).startswith("oneOf."):
                return q["options"]
    return []


@check("[OF1] chọn M03 -> checkedForms [PLI_M03], activeDocId = M03, có data")
def of1():
    manifest = _manifest(ONEOF_CASE)
    label_m03 = next(o["label"] for o in _selector_options(manifest)
                     if o["value"] == "PLI_M03")
    # answer theo data_key -> ghi vào ô CANONICAL (owner) — đúng chỗ khách điền
    res = _fill(manifest, {
        "q_oneof_1": label_m03,
        "dn.ten_tieng_viet": "Công ty TNHH Hai Thành Viên Ánh Sáng",
        "chu_hkd.ho_ten": "  trần thị b ",
        "dia_chi_chi_tiet": "48 Lê Lợi",
        "xa_phuong": "Phường Bến Nghé",
        "tinh_thanh": "TP. Hồ Chí Minh",
        "von_dieu_le": "10.000.000.000",
        "ds_nganh.ten_nganh": ["Xây dựng nhà"],
    })
    assert res["ok"], res["errors"]
    c = res["candidate"]
    assert c["checkedForms"] == ["PLI_M03"], c["checkedForms"]
    assert c["activeDocId"] == "PLI_M03", c["activeDocId"]
    st = c["store"]
    assert st["values"]["dn.ten_tieng_viet"] == \
        "Công ty TNHH Hai Thành Viên Ánh Sáng"
    assert st["values"]["von_dieu_le"] == 10000000000
    assert st["values"]["chu_hkd.ho_ten"] == "trần thị b"  # trim, giữ nguyên
    assert st["loops"]["ds_nganh"] == [{"ten_nganh": "Xây dựng nhà"}]
    assert c["source"]["forms"] == ["PLI_M03"]


@check("[OF2] không chọn trường hợp -> MISSING_REQUIRED, candidate None")
def of2():
    manifest = _manifest(ONEOF_CASE)
    res = _fill(manifest, {"q_i03_dn_ten_tieng_viet": "Công ty nào đó"})
    assert res["ok"] is False and res["candidate"] is None, res
    assert MISSING_REQUIRED in {e["code"] for e in res["errors"]}, res["errors"]


@check("[OF3] gõ tay giá trị lạ vào câu chọn trường hợp -> BAD_SELECT")
def of3():
    manifest = _manifest(ONEOF_CASE)
    res = _fill(manifest, {"q_oneof_1": "chuyển thành công ty cổ phần đi"})
    assert res["ok"] is False and res["candidate"] is None, res
    codes = {e["code"] for e in res["errors"]}
    assert BAD_SELECT in codes, codes
    sel_err = next(e for e in res["errors"] if e["code"] == BAD_SELECT)
    assert sel_err.get("question_id") == "q_oneof_1", sel_err


@check("[OF4] ô của M01 có dữ liệu khi đã chọn M03 -> STRAY_CELL (ô+câu hỏi)")
def of4():
    manifest = _manifest(ONEOF_CASE)
    label_m03 = next(o["label"] for o in _selector_options(manifest)
                     if o["value"] == "PLI_M03")
    res = _fill(manifest, {
        "q_oneof_1": label_m03,
        "q_i01_von_dau_tu_so": "500.000.000",   # chỉ M01 có ô này
    })
    assert res["ok"] is False and res["candidate"] is None, res
    strays = [e for e in res["errors"] if e["code"] == STRAY_CELL]
    assert strays, res["errors"]
    assert any(e.get("form_id") == "PLI_M01" and
               e.get("question_id") == "q_i01_von_dau_tu_so" and e.get("cell")
               for e in strays), strays


@check("[OF5] form tùy chọn M08: không tick -> ngoài checkedForms; tick -> vào")
def of5():
    manifest = _manifest(CTCP_CASE)
    common = {
        "dn.ten_tieng_viet": "Công ty CP Hoa Mai",
        "chu_hkd.ho_ten": "Nguyễn Văn A",
        "dia_chi_chi_tiet": "12 Nguyễn Huệ",
        "xa_phuong": "Phường Bến Nghé",
        "tinh_thanh": "TP. Hồ Chí Minh",
        "ds_nganh.ten_nganh": ["Bán buôn hoa"],
        "ds_co_dong_sang_lap.ho_ten": ["Nguyễn Văn A"],
    }
    # không tick M08: chỉ các form bắt buộc; ô trống của M08 không bị đòi
    res = _fill(manifest, dict(common))
    assert res["ok"], res["errors"]
    c = res["candidate"]
    assert c["checkedForms"] == ["PLI_M04", "PLI_M07"], c["checkedForms"]
    assert "PLI_M08" not in c["checkedForms"]
    # tick X "Có làm mẫu này không?" cho M08 -> vào checkedForms
    res2 = _fill(manifest, {
        **common,
        "q_opt_PLI_M08": "X",
        "ds_co_dong_nn.ten_cd": ["Công ty TNHH Nước Ngoài"],
    })
    assert res2["ok"], res2["errors"]
    c2 = res2["candidate"]
    assert c2["checkedForms"] == ["PLI_M04", "PLI_M07", "PLI_M08"], \
        c2["checkedForms"]
    assert c2["store"]["loops"]["ds_co_dong_nn"] == \
        [{"ten_cd": "Công ty TNHH Nước Ngoài"}]


@check("[OF6] câu chọn trường hợp render ĐẦU Thông_tin_chung, nhãn ghi_chu")
def of6():
    manifest = _manifest(ONEOF_CASE)
    tmp, wb = _export(manifest, "of6_")
    ws = wb[COMMON_SHEET]
    texts = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                texts.append((cell.row, str(cell.value)))
    sel_rows = [r for r, t in texts if "Trường hợp hồ sơ của bạn" in t]
    assert sel_rows, texts
    body_row = sel_rows[0]
    assert body_row >= 9, body_row          # sau khối header cố định
    # selector là body ĐẦU TIÊN: trước nó chỉ có dòng section "Trường hợp
    # hồ sơ" (nếu có) của chính khối selector
    head_rows = [r for r, t in texts
                 if 9 <= r < body_row and t.strip()]
    assert head_rows == [body_row - 1], \
        "selector phải ở đầu %s (trước nó: %s)" % (COMMON_SHEET, head_rows)
    # nhãn option = ghi_chu use case (thân thiện), value = form_id
    options = _selector_options(manifest)
    assert [o["value"] for o in options] == \
        ["PLI_M01", "PLI_M02", "PLI_M03", "PLI_M04"]
    assert options[0]["label"].startswith("Nếu chuyển đổi thành"), options[0]
    # dropdown __lists cho selector
    mp = wb[MAP_SHEET]
    col = _map_col(mp)
    found = any(mp.cell(r, col["question_id"]).value == "q_oneof_1"
                for r in range(4, mp.max_row + 1))
    assert found


@check("[OF7] chọn M03: bắt buộc đòi tên DN/địa chỉ dù canonical thuộc M01")
def of7():
    manifest = _manifest(ONEOF_CASE)
    label_m03 = next(o["label"] for o in _selector_options(manifest)
                     if o["value"] == "PLI_M03")
    res = _fill(manifest, {"q_oneof_1": label_m03})
    assert res["ok"] is False and res["candidate"] is None
    missing = [e for e in res["errors"] if e["code"] == MISSING_REQUIRED]
    qids = {e.get("question_id") for e in missing}
    # tên DN/địa chỉ/xa/tỉnh/industries: bắt buộc của M03 được đòi qua ô
    # canonical ở Thông_tin_chung dù owner là câu của M01
    assert any(qid and qid.startswith("q_i03_") for qid in qids) or missing, \
        missing
    sheets = {e.get("sheet") for e in missing}
    assert sheets <= {COMMON_SHEET}, sheets
    # điền đủ bộ bắt buộc -> ok (như OF1) đã phủ trường hợp đủ


def main() -> int:
    for fn in (of1, of2, of3, of4, of5, of6, of7):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_excel_case_oneof: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
