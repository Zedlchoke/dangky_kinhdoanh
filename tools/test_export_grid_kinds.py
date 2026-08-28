# -*- coding: utf-8 -*-
"""Export gate cho 3 kind mới trên template SANDBOX (Lane B2).

Kiểm chứng ở LỚP ENGINE DOCX (tools/docx_render.py):

[TS] totals recompute lúc export
     - tổng TÍNH LẠI từ các ô dữ liệu, không tin stored value;
     - stored != computed -> raise ExportTotalsError
       (code EXPORT_TOTALS_RECOMPUTE_CONFLICT);
     - strict=False chỉ ghi report, không raise;
     - ô tổng KHÔNG có dữ liệu giả khi chưa nhập gì (kết quả 0);
     - render() không mutate payload của caller.

[OT] output-table: giữ lưới dù không có input + presence có điều kiện {?cond}
     - payload rỗng -> lưới vẫn in nguyên nhãn, không tag sót;
     - cond truthy/falsy -> presence/absence đúng như PLI_M72 Option D.

[NG] nested-grid sau khi render không được lệch cột vật lý
     - số gridCol mỗi bảng giữ nguyên; tổng gridSpan từng hàng = width;
     - rowspan/colspan header bất biến trước/sau render;
     - {_stt} tự sinh 1-based; dữ liệu rơi đúng cột nguồn;
     - mỗi occurrence (bảng biến thể) nhân đúng dòng dữ liệu riêng.

[NB] Ownership guard: lớp Python này KHÔNG đặt tên trùng/chép cơ chế chốt
     export thật của runtime (`EXPORT_LOOP_CONTRACT_CONFLICT` thuộc về
     exportLoopsStrict trong app_web/ui/app.js) — không bypass.

Mọi fixture dựng bằng sandbox helper của tools/test_generator_deep_idempotency
(nguồn docx + spec JSON đều nằm trong tmp). Exit 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 tools/test_export_grid_kinds.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.docx_render import (               # noqa: E402
    ExportTotalsError, LEFTOVER_RE, render, recompute_totals,
)
from tools import test_generator_deep_idempotency as gen_mod   # noqa: E402
from tools.test_generator_deep_idempotency import (   # noqa: E402
    FIXED_MATRIX_SOURCE_PARAS, FIXED_MATRIX_SPEC, NESTED_SOURCE_PARAS,
    OUTPUT_COND_SPEC, OUTPUT_TABLE_SOURCE_PARAS, OUTPUT_TABLE_SPEC,
    apply_sandbox, new_sandbox, nested_occ_spec, physical_widths,
    restore, run_generation, write_source, write_spec,
)

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(*args):
            try:
                fn(*args)
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


def nest(flat: dict) -> dict:
    """Draft lưu key phẳng '<sem>.<row>.<tag>'; app_web/main.py đựng chúng
    thành cây trước khi render. Helper này mô phỏng đúng điều đó."""
    out: dict = {}
    for key, value in flat.items():
        cur = out
        parts = key.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return out


def xml_text(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def visible_texts(docx_path: Path) -> list[str]:
    return re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml_text(docx_path))


def leftover(docx_path: Path) -> list[str]:
    return LEFTOVER_RE.findall(xml_text(docx_path))


def row_span_sums(docx_path: Path) -> list[list[int]]:
    """Tổng gridSpan của từng hàng <w:tr> theo thứ tự xuất hiện."""
    xml = xml_text(docx_path)
    sums = []
    for tr_m in re.finditer(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", xml, re.S):
        total = 0
        for tc_m in re.finditer(r"<w:tc(?:\s[^>]*)?>.*?</w:tc>", tr_m.group(0),
                                re.S):
            gs = re.search(r"<w:gridSpan w:val=\"(\d+)\"/>", tc_m.group(0))
            total += int(gs.group(1)) if gs else 1
        sums.append(total)
    return sums


def vmerge_counts(docx_path: Path) -> tuple[int, int]:
    xml = xml_text(docx_path)
    restart = len(re.findall(r"<w:vMerge w:val=\"restart\"/>", xml))
    cont = len(re.findall(r"<w:vMerge(?: w:val=\"continue\")?/>", xml))
    return restart, cont


# ---------------------------------------------------------------------------
# Fixtures dùng chung các mệnh đề
# ---------------------------------------------------------------------------

MATRIX_META = None       # section_specs PLI_M92 (fixed-matrix)
MATRIX_TPL = None
NESTED_META = None       # section_specs PLI_M91 (nested-grid x4 occurrence)
NESTED_TPL = None
OUT_TPL = None           # PLI_M93 (output-table thường)
OUT_COND_TPL = None      # PLI_M94 (output-table + {?co_chi_tiet_cn})

SEM = "nguon_von_dieu_le_demo"


def build_fixtures(sandbox: dict) -> None:
    global MATRIX_META, MATRIX_TPL, NESTED_META, NESTED_TPL, OUT_TPL, \
        OUT_COND_TPL
    write_spec(sandbox, "PLI_M92", FIXED_MATRIX_SPEC)
    write_source(sandbox, 92, FIXED_MATRIX_SOURCE_PARAS, trailing_table=True)
    meta, tpl = run_generation("PLI_M92", 92, sandbox)
    MATRIX_META, MATRIX_TPL = meta["section_specs"], tpl

    write_spec(sandbox, "PLI_M91", nested_occ_spec())
    write_source(sandbox, 91, NESTED_SOURCE_PARAS)
    nmeta, ntpl = run_generation("PLI_M91", 91, sandbox)
    NESTED_META, NESTED_TPL = nmeta["section_specs"], ntpl

    write_spec(sandbox, "PLI_M93", OUTPUT_TABLE_SPEC)
    write_source(sandbox, 93, OUTPUT_TABLE_SOURCE_PARAS)
    OUT_TPL = run_generation("PLI_M93", 93, sandbox)[1]

    write_spec(sandbox, "PLI_M94", OUTPUT_COND_SPEC)
    write_source(sandbox, 94, OUTPUT_TABLE_SOURCE_PARAS)
    OUT_COND_TPL = run_generation("PLI_M94", 94, sandbox)[1]


TOTAL_ROWS = {
    "von_nsnn": {"so_tien_vnd": "2000000000", "ty_le": ""},
    "von_tu_nhan": {"so_tien_vnd": "3000000000", "ty_le": "30"},
    "von_nuoc_ngoai": {"so_tien_vnd": "", "ty_le": ""},
    "von_khac": {"so_tien_vnd": "", "ty_le": ""},
}
EXPECTED_TOTAL_TIEN = "5000000000"
EXPECTED_TY_LE = "50"


def matrix_payload(extra_total: dict | None = None) -> dict:
    """Draft phẳng -> dạng cây: NSNN 20% + tư nhân 30% = 50% tổng tỷ lệ,
    tiền 2 + 3 tỷ = 5 tỷ."""
    flat = {}
    for rid, cells in TOTAL_ROWS.items():
        for tag, value in cells.items():
            flat["%s.%s.%s" % (SEM, rid, tag)] = value
    # đặt sau vòng lặp để không bị giá trị rỗng mặc định ghi đè
    flat["%s.von_nsnn.ty_le" % SEM] = "20"
    if extra_total:
        flat.update(extra_total)
    return nest(flat)


def make_ts_check(name: str, fn):
    @check(name)
    def runner(sandbox):
        fn(sandbox)
    return runner


# ---------------------------------------------------------------------------
# [TS] totals recompute
# ---------------------------------------------------------------------------

@check("[TS1] tong TINH LAI tu cac o va dien vao o tong chua co du lieu")
def ts_recompute_overrides_stored(sandbox):
    # draft chỉ có ô nhập; ô tổng KHÔNG hề có giá trị lưu
    payload = matrix_payload()
    out = sandbox["templates"] / "ts1_rendered.docx"
    out.write_bytes(render(str(MATRIX_TPL), payload, tables_meta=MATRIX_META))
    texts = visible_texts(out)
    assert EXPECTED_TOTAL_TIEN in texts, \
        "mất tổng tiền tính lại %r: %s" % (EXPECTED_TOTAL_TIEN, texts[:25])
    assert EXPECTED_TY_LE in texts, \
        "mất tổng tỷ lệ tính lại %r: %s" % (EXPECTED_TY_LE, texts[:25])
    assert len(leftover(out)) == 0, "còn tag sót: %s" % leftover(out)[:6]
    # draft gốc phải nguyên vẹn (render làm việc trên bản sao sâu)
    assert payload.get(SEM, {}).get("tong_cong") is None, \
        "render không được mutate payload caller"
    assert payload[SEM]["von_tu_nhan"]["so_tien_vnd"] == "3000000000"


@check("[TS2] stored != computed -> ExportTotalsError "
       "(EXPORT_TOTALS_RECOMPUTE_CONFLICT)")
def ts_conflict_fails_loud(sandbox):
    payload = matrix_payload({"%s.tong_cong.so_tien_vnd" % SEM: "777"})
    raised = None
    try:
        render(str(MATRIX_TPL), payload, tables_meta=MATRIX_META)
    except ExportTotalsError as exc:
        raised = exc
    assert isinstance(raised, ExportTotalsError), \
        "lệch tổng phải fail loud, nhận %r" % (raised,)
    codes = {p["code"] for p in raised.problems}
    assert codes == {"EXPORT_TOTALS_RECOMPUTE_CONFLICT"}, codes
    detail = str(raised)
    # [P3.2/F-P3-SEC-LOG] detail KHÔNG được nhúng giá trị người dùng
    # (giá trị thật vẫn nằm ở problems[i]["stored"/"computed"] để debug).
    assert "tong_cong" in detail and "777" not in detail, \
        "thông báo phải nêu hàng nhưng lọc giá trị: %s" % detail


@check("[TS3] strict=False: chi ghi report, van dung so tinh lai")
def ts_non_strict_reports(sandbox):
    payload = matrix_payload({"%s.tong_cong.so_tien_vnd" % SEM: "777"})
    out = sandbox["templates"] / "ts3_rendered.docx"
    out.write_bytes(render(str(MATRIX_TPL), payload, tables_meta=MATRIX_META,
                           totals_strict=False))
    assert EXPECTED_TOTAL_TIEN in visible_texts(out), \
        "chế độ mềm vẫn phải dùng số tính lại"
    assert "777" not in visible_texts(out)


@check("[TS4] chua nhap gi: o tong la '0' (KHONG du lieu gia), grid van nguyen")
def ts_empty_inputs_zero(sandbox):
    out = sandbox["templates"] / "ts4_rendered.docx"
    out.write_bytes(render(str(MATRIX_TPL), {}, tables_meta=MATRIX_META))
    texts = visible_texts(out)
    for label in ("Loại nguồn vốn", "Vốn ngân sách nhà nước", "Vốn tư nhân",
                  "Tổng cộng"):
        assert any(label in t for t in texts), "mất nhãn %r: %s" % (
            label, texts[:20])
    zeros = [t for t in texts if t.strip() == "0"]
    assert len(zeros) >= 2, "ô tổng phải là '0', thấy %s" % texts
    assert not any("TEST" in t or "1" == t for t in texts), \
        "có dữ liệu giả trong export: %s" % texts
    assert leftover(out) == [], "còn tag sót: %s" % leftover(out)[:6]


@check("[TS5] formula khong ho tro -> FORMULA_UNSUPPORTED fail loud")
def ts_unsupported_formula(sandbox):
    bad_meta = json.loads(json.dumps(MATRIX_META))
    bad_meta[0]["totals"][0]["formula"] = "avg(so_tien_vnd)"
    raised = None
    try:
        recompute_totals({}, bad_meta)
    except ExportTotalsError as exc:
        raised = exc
    assert isinstance(raised, ExportTotalsError), \
        "formula lạ phải fail loud, nhận %r" % (raised,)
    assert raised.problems[0]["code"] == "FORMULA_UNSUPPORTED"


@check("[TS6] recompute_totals doc lap: report day du stored/computed")
def ts_report_shape(sandbox):
    payload = matrix_payload({"%s.tong_cong.ty_le" % SEM: "999"})
    report = recompute_totals(payload, MATRIX_META, strict=False)
    by_tag = {r["target"]: r for r in report}
    tien = by_tag.get("%s.tong_cong.so_tien_vnd" % SEM)
    ty_le = by_tag.get("%s.tong_cong.ty_le" % SEM)
    assert tien and tien["computed"] == EXPECTED_TOTAL_TIEN, tien
    assert tien["stored"] == "", "stored mặc định phải rỗng: %r" % tien
    assert ty_le and ty_le["computed"] == "50" and ty_le["stored"] == "999", \
        "report thiếu stored/computed của tỷ lệ: %r" % ty_le


# ---------------------------------------------------------------------------
# [OT] output-table presence + conditional presence
# ---------------------------------------------------------------------------

@check("[OT1] output-table GIU luoi khi payload rong, 0 input, 0 tag sot")
def ot_present_without_input(sandbox):
    out = sandbox["templates"] / "ot1_rendered.docx"
    out.write_bytes(render(str(OUT_TPL), {}))
    texts = "".join(visible_texts(out))
    assert "NGƯỜI NỘP (Ký và ghi họ tên)" in texts, "mất nhãn NGƯỜI NỘP"
    assert "NGƯỜI NHẬN (Ký và ghi họ tên)" in texts, "mất nhãn NGƯỜI NHẬN"
    assert "{{" not in texts, "tag sót dạng ngoặc kép"
    assert leftover(out) == [], "còn tag sót: %s" % leftover(out)[:6]


@check("[OT2] cond_flag: falsy -> mat khoi output; truthy -> giu nguyen")
def ot_conditional_presence(sandbox):
    out_off = sandbox["templates"] / "ot2_off.docx"
    out_off.write_bytes(render(str(OUT_COND_TPL),
                               {"co_chi_tiet_cn": ""}))
    texts_off = "".join(visible_texts(out_off))
    assert "NGƯỜI NỘP" not in texts_off and "NGƯỜI NHẬN" not in texts_off, \
        "flag rỗng mà lưới vẫn in"
    assert "{?co_chi_tiet_cn}" not in texts_off, "marker điều kiện lộ ra output"

    out_on = sandbox["templates"] / "ot2_on.docx"
    out_on.write_bytes(render(str(OUT_COND_TPL), {"co_chi_tiet_cn": "X"}))
    texts_on = "".join(visible_texts(out_on))
    assert "NGƯỜI NỘP" in texts_on and "NGƯỜI NHẬN" in texts_on, \
        "flag đúng nhưng mất lưới"
    assert leftover(out_on) == [] and leftover(out_off) == [], \
        "còn marker/tag sót sau render"

    # bảng nằm giữa hai marker biến mất cùng vùng -> không còn w:tbl nào
    def tbl_count(path: Path) -> int:
        return len(re.findall(r"<w:tbl[ >]", xml_text(path)))
    assert tbl_count(out_off) == 0, "vùng bỏ phải kéo cả w:tbl đi theo"
    assert tbl_count(out_on) == 1, "vùng giữ phải còn đúng 1 bảng"


# ---------------------------------------------------------------------------
# [NG] nested-grid renders without column loss
# ---------------------------------------------------------------------------

NESTED_LOOP = "ds_tv_01"
NESTED_WIDTH = 5


@check("[NG1] render giu nguyen so cot vat ly cua MOI bang nested-grid")
def ng_physical_width_kept(sandbox):
    rows = [{"ho_ten": "Thành viên A", "von_vnd": "1000", "von_ntte": "",
             "chu_ky": ""},
            {"ho_ten": "B", "von_vnd": "", "von_ntte": "500", "chu_ky": ""},
            {"ho_ten": "C", "von_vnd": "7", "von_ntte": "9", "chu_ky": "X"}]
    payload = {loop: list(rows) for loop in ("ds_tv_01", "ds_tv_02")}
    payload["ds_tv_03"] = []
    payload["ds_tv_04"] = []
    out = sandbox["templates"] / "ng1_rendered.docx"
    out.write_bytes(render(str(NESTED_TPL), payload))
    widths_out = physical_widths(out)
    widths_tpl = physical_widths(NESTED_TPL)
    assert widths_out == widths_tpl, \
        "số gridCol đổi sau render: %s vs %s" % (widths_out, widths_tpl)
    assert all(w == NESTED_WIDTH for w in widths_out), \
        "bảng bị làm phẳng mất cột: %s" % widths_out
    sig = row_span_sums(out)
    assert sig, "không đọc được hàng nào trong output"
    for s in sig:
        assert s == NESTED_WIDTH, \
            "hàng lệch tổng gridSpan (%s), kỳ vọng %d (mất cột vật lý)" % (
                s, NESTED_WIDTH)


@check("[NG2] rowspan/colspan header BAT BIEN truoc/sau render")
def ng_header_spans_invariant(sandbox):
    restart_tpl, cont_tpl = vmerge_counts(NESTED_TPL)
    rows = [{"ho_ten": "Người ủy quyền", "von_vnd": "1", "von_ntte": "",
             "chu_ky": ""}]
    payload = {"ds_tv_01": rows, "ds_tv_02": rows, "ds_tv_03": [],
               "ds_tv_04": []}
    out = sandbox["templates"] / "ng2_rendered.docx"
    out.write_bytes(render(str(NESTED_TPL), payload))
    restart_out, cont_out = vmerge_counts(out)
    assert (restart_out, cont_out) == (restart_tpl, cont_tpl), \
        "rowspan header bị thay đổi khi render: %s vs %s" % (
            (restart_out, cont_out), (restart_tpl, cont_tpl))
    assert restart_tpl >= 3, "fixture mất sẵn ô gộp dọc để đối chiếu"


@check("[NG3] _stt tu sinh 1-based va du lieu roi DUNG cot nguon")
def ng_stt_and_column_order(sandbox):
    rows = [{"ho_ten": "An", "von_vnd": "10", "von_ntte": "11", "chu_ky": ""},
            {"ho_ten": "Binh", "von_vnd": "20", "von_ntte": "21",
             "chu_ky": "X"}]
    payload = {"ds_tv_01": rows, "ds_tv_02": [], "ds_tv_03": [], "ds_tv_04": []}
    out = sandbox["templates"] / "ng3_rendered.docx"
    out.write_bytes(render(str(NESTED_TPL), payload))
    # lấy bảng đầu tiên
    tbl_m = re.search(r"<w:tbl[ >].*?</w:tbl>", xml_text(out), re.S).group(0)
    tr_ms = list(re.finditer(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", tbl_m, re.S))
    def row_cells(tr_xml: str) -> list[str]:
        vals = []
        for tc_m in re.finditer(r"<w:tc(?:\s[^>]*)?>.*?</w:tc>", tr_xml, re.S):
            txts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc_m.group(0))
            vals.append("".join(txts).strip())
        return vals
    # bảng rebuild còn các hàng TRẮNG giữ chỗ giữa header và hàng mẫu: sau
    # render hàng khuôn được nhân thành 2 dòng dữ liệu, các hàng trắng vẫn rỗng
    def meaningful(tr_m):
        return [c for c in row_cells(tr_m.group(0)) if c != ""]
    data_rows = [meaningful(tr_m) for tr_m in tr_ms[2:]]
    data_rows = [cells for cells in data_rows if cells]
    assert len(data_rows) == 2, \
        "kỳ vọng 2 dòng dữ liệu, thấy %d (%r)" % (
            len(data_rows), data_rows[:4])
    assert [r[0] for r in data_rows] == ["1", "2"], \
        "STT tự sinh sai: %s" % [r[0] for r in data_rows]
    assert [r[1] for r in data_rows] == ["An", "Binh"], data_rows
    assert [r[2] for r in data_rows] == ["10", "20"], data_rows
    assert [r[3] for r in data_rows] == ["11", "21"], data_rows
    assert leftover(out) == [], "còn tag sót: %s" % leftover(out)[:6]


@check("[NG4] moi occurrence nhan dung dong rieng (khong nhan ban lung)")
def ng_occurrence_isolation(sandbox):
    payload = {
        "ds_tv_01": [{"ho_ten": "P1", "von_vnd": "1", "von_ntte": "",
                      "chu_ky": ""}],
        "ds_tv_02": [{"ho_ten": "P2", "von_vnd": "2", "von_ntte": "",
                      "chu_ky": ""}],
        "ds_tv_03": [],
        "ds_tv_04": [],
    }
    out = sandbox["templates"] / "ng4_rendered.docx"
    out.write_bytes(render(str(NESTED_TPL), payload))
    text_all = "\n".join(visible_texts(out))
    for token in ("P1", "P2"):
        assert text_all.count(token) == 1, \
            "%s xuất hiện %d lần (phải đúng 1 bảng biến thể)" % (
                token, text_all.count(token))
    assert leftover(out) == [], "còn tag sót: %s" % leftover(out)[:6]


# ---------------------------------------------------------------------------
# [NB] ownership guard
# ---------------------------------------------------------------------------

@check("[NB1] RESERVED EXPORT_LOOP_CONTRACT_CONFLICT thuoc exportLoopsStrict (JS)")
def nb_no_bypass_of_js_guard(sandbox):
    src = (ROOT / "tools" / "docx_render.py").read_text(encoding="utf-8")
    assert "EXPORT_LOOP_CONTRACT_CONFLICT" not in src, \
        "Python layer không được chép/dùng mã chốt dành riêng cho exportLoopsStrict"
    own_code = "EXPORT_TOTALS_RECOMPUTE_CONFLICT"
    assert own_code in src, "mã lỗi riêng của lớp này phải được khai báo tường minh"
    # và phải là một lỗi độc lập (class riêng), không phải alias của CondTagError
    from tools.docx_render import CondTagError
    assert ExportTotalsError is not CondTagError
    del sandbox


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    sandbox = new_sandbox()
    saved = apply_sandbox(sandbox)
    tests = [
        lambda: build_fixtures(sandbox),
        lambda: ts_recompute_overrides_stored(sandbox),
        lambda: ts_conflict_fails_loud(sandbox),
        lambda: ts_non_strict_reports(sandbox),
        lambda: ts_empty_inputs_zero(sandbox),
        lambda: ts_unsupported_formula(sandbox),
        lambda: ts_report_shape(sandbox),
        lambda: ot_present_without_input(sandbox),
        lambda: ot_conditional_presence(sandbox),
        lambda: ng_physical_width_kept(sandbox),
        lambda: ng_header_spans_invariant(sandbox),
        lambda: ng_stt_and_column_order(sandbox),
        lambda: ng_occurrence_isolation(sandbox),
        lambda: nb_no_bypass_of_js_guard(sandbox),
    ]
    try:
        for t in tests:
            t()
    finally:
        restore(saved)
        shutil.rmtree(gen_mod._tmp_root, ignore_errors=True)
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("test_export_grid_kinds: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
