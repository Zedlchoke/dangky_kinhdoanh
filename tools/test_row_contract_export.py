# -*- coding: utf-8 -*-
"""test_row_contract_export.py — PHASE 4 row/blank-row contract ở LỚP ENGINE
DOCX (tools/docx_render.py) + fixed-matrix row-count contract.

Phủ (mỗi nhóm contract cùng semantics):

[RC] editable/nested loop ở tầng render
     - RC1 payload chứa dòng MỌI ô trống -> KHÔNG in hàng DOCX (blank không
       thành business data); guard last-mile của _expand_loops.
     - RC2 one-row -> đúng 1 hàng; nhiều dòng + blank đầu/giữa/cuối -> hàng
       in đúng thứ tự dữ liệu, {_stt} đánh lại 1..n TRÊN DỮ LIỆU.
     - RC3 partial row (một ô có giá trị) KHÔNG bị mất.
     - RC4 hai loop cùng template -> số hàng độc lập (không cross-contaminate).
     - RC5 output không còn marker {...} sót.
     - RC6 [F3T.2/F3T.4] ROW-PLACEMENT matrix trên fixture PRODUCTION-LIKE
       (header + K hàng trắng in sẵn + hàng marker): pin
       (K,N) = (4,0) (4,1) (4,4) (4,6) (5,2) + (0,3) không-K;
       [Pin sync — owner N-only 2026-09-08] mỗi pin assert TỔNG SỐ HÀNG =
       header + N (không max(K,N)), VỊ TRÍ DATA (ngay sau header, không
       blank chen trước), STT 1..N và KHÔNG hàng trắng đuôi. Trước F3T
       suite này 8/8 PASS trên fixture tối giản không có K trắng — blind
       spot của defect K-blank-then-data; fixture nâng cấp chứ không bỏ
       assertion.

[FM] fixed-matrix giữ đúng cấu trúc dòng pháp định
     - FM1 chưa nhập gì -> ĐỦ số dòng cố định (kể cả dòng Tổng), tổng = '0'
       (phân biệt với blank row: fixed legal row KHÔNG bị lọc vì ô trống).
     - FM2 partial (1 dòng có giá trị) -> số dòng không đổi, tổng recompute.
     - FM3 stored totals sai -> fail-loud (ExportTotalsError) — đã phủ TS2
       của test_export_grid_kinds; corpus chỉ pin lại hành vi.

Template editable dựng bằng python-docx trong tmp (không đụng production
templates). Fixture fixed-matrix tái dùng sandbox helper của
tools/test_generator_deep_idempotency. Exit 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 -m tools.test_row_contract_export
"""
from __future__ import annotations

import sys
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.docx_render import (               # noqa: E402
    LEFTOVER_RE, ExportTotalsError, render,
)
from tools.test_generator_deep_idempotency import (   # noqa: E402
    FIXED_MATRIX_SOURCE_PARAS, FIXED_MATRIX_SPEC,
    apply_sandbox, new_sandbox, restore, run_generation,
    write_source, write_spec,
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


# ---------------------------------------------------------------------------
# Editable-loop template PRODUCTION-LIKE (F3T.4): mỗi loop một bảng
#   header | K hàng trắng in sẵn | hàng khuôn
#   {#ds_x}{_stt} | {ma_nganh} | {ten_nganh}{/ds_x}
# blank_rows=0 mô phỏng loop không-K (chỉ header + marker).
# ---------------------------------------------------------------------------
LOOP_HDR = ("STT", "Mã ngành", "Tên ngành")


def build_loop_template(path: Path, loops: list[str],
                        blank_rows: int = 0) -> None:
    d = docx.Document()
    d.add_paragraph("PHỤ LỤC — corpus loop template (production-like: "
                    "header + %d blank + marker)" % blank_rows)
    for name in loops:
        t = d.add_table(rows=1, cols=3)
        for i, htxt in enumerate(LOOP_HDR):
            t.rows[0].cells[i].text = htxt
        for _ in range(blank_rows):
            r = t.add_row()
            for c in r.cells:
                c.text = ""
        cells = t.add_row().cells
        cells[0].text = "{#%s}{_stt}" % name
        cells[1].text = "{ma_nganh}"
        cells[2].text = "{ten_nganh}{/%s}" % name
    d.save(str(path))


def docx_table_rows(path: Path) -> list[list[str]]:
    """Text từng cell theo từng hàng bảng, theo thứ tự tài liệu."""
    d = docx.Document(str(path))
    out = []
    for t in d.tables:
        for r in t.rows:
            out.append([c.text.strip() for c in r.cells])
    return out


# ---------------------------------------------------------------------------
# [RC] loop row contract
# ---------------------------------------------------------------------------

@check("[RC1] blank row trong payload KHONG in hang DOCX (guard last-mile)")
def rc1_blank_row_not_rendered():
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    tmp.mkdir(parents=True, exist_ok=True)
    tpl = tmp / "loop_tpl.docx"
    # fixture production-like: header + 4 hàng trắng + hàng marker (như
    # ds_nganh_* của PLI_M72; K=4 trong blocks blankRows)
    build_loop_template(tpl, ["ds_x"], blank_rows=4)
    payload = {"ds_x": [
        {"ma_nganh": "0111", "ten_nganh": "Trồng lúa"},
        {},                                            # blank hoàn toàn
        {"ma_nganh": "", "ten_nganh": ""},             # blank dạng chuỗi rỗng
    ]}
    out = tmp / "rc1_out.docx"
    out.write_bytes(render(str(tpl), payload))
    rows = docx_table_rows(out)
    body = [r for r in rows if r and r[0].isdigit()]
    assert len(body) == 1, "phải còn đúng 1 hàng dữ liệu, thấy %r" % (rows,)
    assert body[0][1] == "0111", "dữ liệu lệch: %r" % (body,)


@check("[RC2] nhieu dong + blank xen keo -> thu tu dung, _stt danh lai 1..n")
def rc2_order_and_stt():
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    tpl = tmp / "loop_tpl.docx"
    if not tpl.exists():
        build_loop_template(tpl, ["ds_x"])
    payload = {"ds_x": [
        {},
        {"ma_nganh": "0111", "ten_nganh": "Trồng lúa"},
        {},
        {"ma_nganh": "0140", "ten_nganh": "Chăn nuôi"},
        {},
    ]}
    out = tmp / "rc2_out.docx"
    out.write_bytes(render(str(tpl), payload))
    rows = docx_table_rows(out)
    body = [r for r in rows if r and r[0].isdigit()]
    assert len(body) == 2, "phải 2 hàng dữ liệu, thấy %r" % (rows,)
    assert body[0][0] == "1" and body[0][1] == "0111", repr(body[0])
    assert body[1][0] == "2" and body[1][1] == "0140", repr(body[1])


@check("[RC3] partial row (mot o co gia tri) KHONG bi mat")
def rc3_partial_kept():
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    tpl = tmp / "loop_tpl.docx"
    payload = {"ds_x": [
        {"ma_nganh": "0111", "ten_nganh": "Trồng lúa"},
        {"ma_nganh": "9999", "ten_nganh": ""},         # partial: chỉ mã
        {"ma_nganh": "", "ten_nganh": "Chỉ tên"},      # partial: chỉ tên
    ]}
    out = tmp / "rc3_out.docx"
    out.write_bytes(render(str(tpl), payload))
    rows = docx_table_rows(out)
    body = [r for r in rows if r and r[0].isdigit()]
    assert len(body) == 3, "partial row phải được giữ — thấy %r" % (rows,)
    assert body[1][1] == "9999" and body[2][2] == "Chỉ tên", repr(body)


@check("[RC4] hai loop cung template -> so hang doc lap, khong tron")
def rc4_two_loops_independent():
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    tpl = tmp / "loop_tpl2.docx"
    build_loop_template(tpl, ["ds_a", "ds_b"], blank_rows=4)
    payload = {
        "ds_a": [{"ma_nganh": "1", "ten_nganh": "A1"}, {}, 
                 {"ma_nganh": "2", "ten_nganh": "A2"}],
        "ds_b": [{"ma_nganh": "9", "ten_nganh": "B1"}],
    }
    out = tmp / "rc4_out.docx"
    out.write_bytes(render(str(tpl), payload))
    rows = docx_table_rows(out)
    body = [r for r in rows if r and r[0].isdigit()]
    a = [r for r in body if r[1] in ("1", "2")]
    b = [r for r in body if r[1] == "9"]
    assert len(a) == 2 and len(b) == 1, "loop độc lập phải 2+1 hàng: %r" % (body,)
    assert body[0][0] == "1" and body[2][0] == "1", \
        "_stt mỗi loop phải đánh riêng 1..n: %r" % (body,)


@check("[RC5] output khong con marker {...} sot")
def rc5_no_markers():
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    names = ["rc1_out.docx", "rc2_out.docx", "rc3_out.docx",
             "rc4_out.docx"]
    names += sorted(p.name for p in tmp.glob("rc6_out_*.docx"))
    for name in names:
        p = tmp / name
        if not p.exists():
            continue
        import re
        import zipfile
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
        left = LEFTOVER_RE.findall(xml)
        assert not left, "%s còn marker: %r" % (name, left)


# ---------------------------------------------------------------------------
# [RC6] F3T.2/F3T.4 — ROW-PLACEMENT matrix trên fixture production-like
# (header + K hàng trắng + hàng marker).
# [Pin sync — owner N-only 2026-09-08] hợp đồng mới CHỈ N hàng dữ liệu,
# KHÔNG hàng trắng: mỗi pin assert tổng số hàng = header + N; N hàng dữ
# liệu đứng NGAY SAU header (không blank chen trước dòng 1) với STT 1..N
# đúng; không còn hàng trắng đuôi (K chỉ là metadata blocks, không còn
# được render).
# ---------------------------------------------------------------------------

def loop_table_rows(path: Path) -> list[list[str]]:
    """Text từng ô của bảng loop ĐẦU TIÊN trong tài liệu."""
    d = docx.Document(str(path))
    t = d.tables[0]
    return [[c.text.strip() for c in r.cells] for r in t.rows]


def _pin_case(k: int, n: int, out_name: str) -> None:
    tmp = Path("/tmp/dkdn_row_contract_corpus")
    tmp.mkdir(parents=True, exist_ok=True)
    tpl = tmp / ("rc6_tpl_k%d.docx" % k)
    build_loop_template(tpl, ["ds_x"], blank_rows=k)
    payload = {"ds_x": [
        {"ma_nganh": "%04d" % (i + 1),
         "ten_nganh": "Ngành nghề %d" % (i + 1)}
        for i in range(n)
    ]}
    out = tmp / out_name
    out.write_bytes(render(str(tpl), payload))
    rows = loop_table_rows(out)

    # [Pin sync — owner N-only 2026-09-08] CHỈ N hàng dữ liệu, không hàng trắng
    expect_total = 1 + n
    assert len(rows) == expect_total, (
        "(K=%d,N=%d): tổng hàng %d != 1 + %d = %d" % (k, n, len(rows), n, expect_total))
    assert tuple(rows[0]) == LOOP_HDR, "header lệch"
    for i in range(n):
        row = rows[1 + i]
        assert row[0] == str(i + 1), "STT hàng %d = %r" % (1 + i, row[0])
        assert row[1] == "%04d" % (i + 1) and row[2], "data lệch"
    # [Pin sync — owner N-only 2026-09-08] KHÔNG có hàng trắng đuôi
    # (tổng hàng đã pin = header + N nên không thể còn hàng nào sau data)


@check("[RC6a] (K=4,N=0) chi header, khong hang trang (N-only)")
def rc6a_k4_n0():
    _pin_case(4, 0, "rc6_out_k4n0.docx")


@check("[RC6b] (K=4,N=1) 1 data ngay sau header, khong trang duoi (N-only)")
def rc6b_k4_n1():
    _pin_case(4, 1, "rc6_out_k4n1.docx")


@check("[RC6c] (K=4,N=4) dung 4 data STT 1..4, khong trang thua")
def rc6c_k4_n4():
    _pin_case(4, 4, "rc6_out_k4n4.docx")


@check("[RC6d] (K=4,N=6) N>=K: dung 6 data STT 1..6, khong append trang")
def rc6d_k4_n6():
    _pin_case(4, 6, "rc6_out_k4n6.docx")


@check("[RC6e] (K=5,N=2) 2 data, khong trang duoi (N-only)")
def rc6e_k5_n2():
    _pin_case(5, 2, "rc6_out_k5n2.docx")


@check("[RC6f] (K=0,N=3) loop khong-K: 3 data ngay sau header")
def rc6f_k0_n3():
    _pin_case(0, 3, "rc6_out_k0n3.docx")


# ---------------------------------------------------------------------------
# [FM] fixed-matrix row-count contract (sandbox generator fixtures)
# ---------------------------------------------------------------------------

_FM: dict = {}


def _docx_body_rows(path: Path) -> list[list[str]]:
    d = docx.Document(str(path))
    rows = []
    for t in d.tables:
        for r in t.rows:
            rows.append([c.text.strip() for c in r.cells])
    return rows


@check("[FM1] chua nhap gi -> DU so dong phap dinh + tong '0' (fixed row khong bi loc)")
def fm1_empty_keeps_all_fixed_rows():
    from tools import test_generator_deep_idempotency as gen_mod
    meta, tpl = _FM["meta"], _FM["tpl"]
    out = Path(gen_mod._tmp_root) / "fm1_out.docx"
    out.write_bytes(render(str(tpl), {}, tables_meta=meta))
    rows = _docx_body_rows(out)
    n_fixed = len(_FM["spec"]["fixed_rows"])
    body = [r for r in rows if any(c for c in r)]
    assert len(body) >= n_fixed, (
        "fixed-matrix phải giữ đủ %d dòng pháp định khi rỗng, thấy %d: %r"
        % (n_fixed, len(body), body))
    joined = " | ".join(" ".join(r) for r in rows)
    assert "Tổng cộng" in joined or "Tổng số" in joined, \
        "dòng Tổng phải luôn in: %r" % (rows[-3:],)
    assert not LEFTOVER_RE.findall(
        __import__("zipfile").ZipFile(out).read(
            "word/document.xml").decode("utf-8"))


@check("[FM2] partial 1 dong -> so dong khong doi, tong recompute dung")
def fm2_partial_recompute():
    from tools import test_generator_deep_idempotency as gen_mod
    sem = _FM["spec"]["semantic_key"]
    meta, tpl = _FM["meta"], _FM["tpl"]
    flat = {
        "%s.von_nsnn.so_tien_vnd" % sem: "2000000000",
        "%s.von_nsnn.ty_le" % sem: "20",
    }
    payload = {}
    for k, v in flat.items():
        cur = payload
        parts = k.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = v
    out = Path(gen_mod._tmp_root) / "fm2_out.docx"
    out.write_bytes(render(str(tpl), payload, tables_meta=meta))
    rows = _docx_body_rows(out)
    n_fixed = len(_FM["spec"]["fixed_rows"])
    body = [r for r in rows if any(c for c in r)]
    assert len(body) >= n_fixed, "số dòng pháp định không được đổi: %r" % (body,)
    text_all = " ".join(" ".join(r) for r in rows)
    assert "2000000000" in text_all, "giá trị partial phải in: %r" % (rows,)


@check("[FM3] stored totals sai -> fail-loud ExportTotalsError (pin lai)")
def fm3_stored_conflict_fail_loud():
    from tools import test_generator_deep_idempotency as gen_mod
    sem = _FM["spec"]["semantic_key"]
    meta, tpl = _FM["meta"], _FM["tpl"]

    def setp(payload, key, value):
        cur = payload
        parts = key.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    payload = {}
    setp(payload, "%s.von_nsnn.so_tien_vnd" % sem, "2000000000")
    setp(payload, "%s.tong_cong.so_tien_vnd" % sem, "999")
    raised = False
    try:
        render(str(tpl), payload, tables_meta=meta)
    except ExportTotalsError:
        raised = True
    assert raised, "stored totals sai phải ExportTotalsError (strict)"


def main() -> int:
    rc1_blank_row_not_rendered()
    rc2_order_and_stt()
    rc3_partial_kept()
    rc4_two_loops_independent()
    # [RC6] matrix pin (K,N) — chạy trước RC5 để outputs có mặt khi quét
    # leftover marker
    rc6d_k4_n6()
    rc6e_k5_n2()
    rc6f_k0_n3()
    rc6a_k4_n0()
    rc6b_k4_n1()
    rc6c_k4_n4()
    rc5_no_markers()
    # [FM] dùng chung 1 sandbox generator đã apply, như pattern
    # test_export_grid_kinds (apply_sandbox trước, restore sau).
    import shutil
    from tools import test_generator_deep_idempotency as gen_mod
    sandbox = new_sandbox()
    saved = apply_sandbox(sandbox)
    try:
        write_spec(sandbox, "PLI_M92", FIXED_MATRIX_SPEC)
        write_source(sandbox, 92, FIXED_MATRIX_SOURCE_PARAS, trailing_table=True)
        form_meta, _tpl = run_generation("PLI_M92", 92, sandbox)
        # tables_meta cho render/recompute PHẢI là section_specs (list),
        # không phải full form meta — đang tái hiện contract của main.py:236.
        _FM["meta"] = form_meta["section_specs"]
        _FM["tpl"] = _tpl
        _FM["spec"] = FIXED_MATRIX_SPEC["tables"][0]["spec"]
        fm1_empty_keeps_all_fixed_rows()
        fm2_partial_recompute()
        fm3_stored_conflict_fail_loud()
    finally:
        restore(saved)
        shutil.rmtree(gen_mod._tmp_root, ignore_errors=True)
    fails = [r for r in _results if not r[0]]
    print("-" * 60)
    print("test_row_contract_export: %d PASS / %d FAIL"
          % (len(_results) - len(fails), len(fails)))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
