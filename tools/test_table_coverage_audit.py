#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest cho tools/census/table_coverage_audit.py (targeted, python3 thuần).

KHÔNG đọc fixture production: mọi hàm được test là hàm thuần nhận dict/list.
Chạy:  python3 -X utf8 tools/test_table_coverage_audit.py
Exit 0 = toàn PASS; exit 1 = có FAIL.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.census.table_coverage_audit import (  # noqa: E402
    FINAL_BLOCKED,
    FINAL_IMPLEMENTED,
    FINAL_MISSING,
    FINAL_NO_TABLE,
    FINAL_OUTPUT_ONLY,
    FINAL_PARTIAL,
    FINAL_REMOVED,
    bridge_loop_names,
    check_section_count,
    derive_final_status,
    iter_js_entries,
    legal_blocker_flags,
    match_blocks,
    resolve_override_keys,
    strip_js,
    find_js_block,
)

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS  " if cond else "FAIL  ") + name +
          (("  | " + detail) if (detail and not cond) else ""))


def full_stages():
    return {"spec": True, "template": True, "form_maps": True,
            "blocks": True, "blocks_loop": True, "runtime": True,
            "draft": True, "validation": True}


def stage_arg(overrides=None):
    st = full_stages()
    st.update(overrides or {})
    return st


# ------------------------------------------------------------- IMPLEMENTED
def test_implemented():
    st, missing, _ = derive_final_status(
        kind="editable-grid", manifest_status="missing_grid",
        override_status=None, stages=stage_arg(),
        required_cols=["stt", "ten_nganh"], evidenced_tags=["stt",
                                                            "ten_nganh"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("IMPLEMENTED_VERIFIED + (manifest stale missing_grid vẫn nâng vì "
          "đủ pipeline)", st == FINAL_IMPLEMENTED and missing == [],
          "got %s / %s" % (st, missing))

    st2, missing2, _ = derive_final_status(
        kind="editable-grid", manifest_status="already_complete",
        override_status="already_complete", stages=stage_arg(),
        required_cols=["a"], evidenced_tags=["a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("IMPLEMENTED_VERIFIED + (case chuẩn đủ stage)",
          st2 == FINAL_IMPLEMENTED and missing2 == [])

    # ÂM: thiếu 1 stage (validation) -> KHÔNG được IMPLEMENTED_VERIFIED
    st3, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="already_complete",
        override_status=None, stages=stage_arg({"validation": False}),
        required_cols=["a"], evidenced_tags=["a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: thiếu validation -> MISSING_IMPLEMENTATION (không nâng)",
          st3 == FINAL_MISSING, "got %s" % st3)

    st4, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="already_complete",
        override_status=None, stages=stage_arg({"draft": False}),
        required_cols=["a"], evidenced_tags=["a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: thiếu draft -> MISSING_IMPLEMENTATION", st4 == FINAL_MISSING,
          "got %s" % st4)


# ----------------------------------------------------------------- PARTIAL
def test_partial():
    st, _, detail = derive_final_status(
        kind="fixed-matrix", manifest_status="partial_columns",
        override_status=None, stages=stage_arg(),
        required_cols=["stt", "a", "b", "c"], evidenced_tags=["stt", "a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("PARTIAL_COLUMNS + (đủ pipeline nhưng thiếu cột b,c)",
          st == FINAL_PARTIAL and "b" in " ".join(detail)
          and "c" in " ".join(detail),
          "got %s / %s" % (st, detail))

    # ÂM: đủ cột -> không được PARTIAL (phải IMPLEMENTED)
    st2, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="partial_columns",
        override_status=None, stages=stage_arg(),
        required_cols=["a"], evidenced_tags=["x_a", "a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: đủ cột -> không PARTIAL_COLUMNS", st2 == FINAL_IMPLEMENTED,
          "got %s" % st2)

    # tags chưa biết (None) -> không kết luận PARTIAL
    st3, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="partial_columns",
        override_status=None, stages=stage_arg({"validation": False}),
        required_cols=["a", "b"], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: evidenced_tags=None -> không dám PARTIAL, rơi MISSING",
          st3 == FINAL_MISSING, "got %s" % st3)


# ----------------------------------------------------------------- MISSING
def test_missing():
    st, missing, _ = derive_final_status(
        kind="editable-grid", manifest_status="missing_grid",
        override_status=None, stages=stage_arg({"blocks": False,
                                                "blocks_loop": False,
                                                "runtime": False,
                                                "draft": False,
                                                "validation": False}),
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("MISSING_IMPLEMENTATION + (spec+form_maps khai nhưng thiếu "
          "blocks/runtime/draft/validation)",
          st == FINAL_MISSING and set(missing) == {"blocks", "runtime",
                                                   "draft", "validation"},
          "got %s / %s" % (st, missing))

    # ÂM: không được MISSING khi đủ pipeline
    st2, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="missing_grid",
        override_status=None, stages=stage_arg(),
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: đủ pipeline -> không MISSING", st2 == FINAL_IMPLEMENTED,
          "got %s" % st2)


# ----------------------------------------------------------------- BLOCKED
def test_blocked():
    st, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="missing_grid",
        override_status=None, stages=stage_arg({"spec": False,
                                                "form_maps": False,
                                                "blocks": False,
                                                "blocks_loop": False,
                                                "runtime": False,
                                                "draft": False,
                                                "validation": False}),
        required_cols=[], evidenced_tags=None,
        legal_blocker=True, override_blocked=False, removed_by_law=False)
    check("BLOCKED_OWNER + (không implementation + blocker tường minh)",
          st == FINAL_BLOCKED, "got %s" % st)

    st2, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="missing_grid",
        override_status=None, stages=stage_arg({"spec": False,
                                                "form_maps": False,
                                                "blocks": False,
                                                "blocks_loop": False,
                                                "runtime": False,
                                                "draft": False,
                                                "validation": False}),
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=True, removed_by_law=False)
    check("BLOCKED_OWNER + (override ghi blocked)", st2 == FINAL_BLOCKED,
          "got %s" % st2)

    # ÂM: blocker NHƯNG có bằng chứng vật lý nhóm chk trong blocks -> không
    # được BLOCKED (có implementation một phần -> MISSING bảo thủ)
    st5, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="already_complete",
        override_status=None, stages=stage_arg({"spec": False,
                                                "form_maps": False,
                                                "runtime": False,
                                                "draft": False,
                                                "validation": False,
                                                "blocks_loop": False,
                                                "blocks_chk": True}),
        required_cols=["khu_a"], evidenced_tags=["khu_a"],
        legal_blocker=True, override_blocked=False, removed_by_law=False)
    check("âm: chỉ có chk blocks + blocker -> MISSING (không BLOCKED vì "
          "vẫn có implementation vật lý)", st5 == FINAL_MISSING,
          "got %s" % st5)

    # ÂM: có bằng chứng bảng thì KHÔNG được BLOCKED (chuyển MISSING bảo thủ)
    st3, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="missing_grid",
        override_status=None, stages=stage_arg({"draft": False,
                                                "validation": False}),
        required_cols=[], evidenced_tags=None,
        legal_blocker=True, override_blocked=False, removed_by_law=False)
    check("âm: có bảng + blocker -> MISSING (không BLOCKED)",
          st3 == FINAL_MISSING, "got %s" % st3)

    # ÂM: blocker nhưng không hề blocked và đủ pipeline -> IMPLEMENTED
    st4, _, _ = derive_final_status(
        kind="fixed-matrix", manifest_status="already_complete",
        override_status=None, stages=stage_arg(),
        required_cols=["a"], evidenced_tags=["a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: đủ pipeline -> không BLOCKED", st4 == FINAL_IMPLEMENTED,
          "got %s" % st4)


# ---------------------------------------------------------------- NO_TABLE
def test_no_table():
    empty = {k: False for k in full_stages()}
    st, _, _ = derive_final_status(
        kind="prose-block", manifest_status="no_table",
        override_status=None, stages=empty,
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("NO_TABLE + (manifest no_table, không tầng nào thấy bảng)",
          st == FINAL_NO_TABLE, "got %s" % st)

    # ÂM: manifest no_table NHƯNG blocks có loop -> không NO_TABLE (bảo thủ
    # rơi MISSING + để gate báo xung đột)
    conflicting = dict(empty)
    conflicting["blocks"] = True
    conflicting["blocks_loop"] = True
    st2, _, _ = derive_final_status(
        kind="prose-block", manifest_status="no_table",
        override_status=None, stages=conflicting,
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: no_table nhưng có loop block -> KHÔNG NO_TABLE",
          st2 == FINAL_MISSING, "got %s" % st2)


# ------------------------------------------------------------- OUTPUT_ONLY
def test_output_only():
    st, _, _ = derive_final_status(
        kind="output-table", manifest_status="output_only",
        override_status=None, stages=stage_arg(),
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("OUTPUT_ONLY + (kind output-table)", st == FINAL_OUTPUT_ONLY,
          "got %s" % st)

    st2, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="output_only",
        override_status=None, stages={k: False for k in full_stages()},
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("OUTPUT_ONLY + (manifest output_only thắng cả khi không evidence)",
          st2 == FINAL_OUTPUT_ONLY, "got %s" % st2)

    # ÂM: kind thường -> không OUTPUT_ONLY
    st3, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="already_complete",
        override_status=None, stages=stage_arg(),
        required_cols=["a"], evidenced_tags=["a"],
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: editable-grid -> không OUTPUT_ONLY",
          st3 == FINAL_IMPLEMENTED, "got %s" % st3)


# ---------------------------------------------------------------- REMOVED
def test_removed():
    st, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="missing_grid",
        override_status=None, stages={k: False for k in full_stages()},
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=True)
    check("REMOVED_BY_CURRENT_LAW + (manifest ghi rõ đã bỏ, có bằng chứng)",
          st == FINAL_REMOVED, "got %s" % st)

    # ÂM: KHÔNG có bằng chứng thì cấm dùng giá trị này
    st2, _, _ = derive_final_status(
        kind="editable-grid", manifest_status="missing_grid",
        override_status=None, stages={k: False for k in full_stages()},
        required_cols=[], evidenced_tags=None,
        legal_blocker=False, override_blocked=False, removed_by_law=False)
    check("âm: removed_by_law=False -> không REMOVED_BY_CURRENT_LAW",
          st2 == FINAL_MISSING, "got %s" % st2)


# ------------------------------------------------------------------- gates
def test_override_gate():
    manifest_index = {("PLI_M02", "ds_nganh_tnmv"), ("PLI_M06",
                                                     "ds_thanh_vien_tnhh")}
    overrides_ok = {("PLI_M02", "ds_nganh_tnmv"): {"status":
                                                   "already_complete"},
                    ("PLI_M06", "ds_thanh_vien_tnhh"): {
                        "status": "already_complete"}}
    check("override resolve: key đúng -> 0 drift",
          resolve_override_keys(overrides_ok, manifest_index) == [])

    overrides_bad = {("PLI_M02", "ds_nganh_sai_section"): {
        "status": "already_complete"}}
    drift = resolve_override_keys(overrides_bad, manifest_index)
    check("override resolve: sai section_id -> FAIL (1 drift)",
          len(drift) == 1 and drift[0]["gate"] == "override_resolve",
          "got %s" % drift)

    overrides_orphan = {("FORM_KHONG_TON_TAI", "section_bom"): {
        "status": "already_complete"}}
    drift2 = resolve_override_keys(overrides_orphan, manifest_index)
    check("override resolve: form mồ côi -> FAIL",
          len(drift2) == 1 and "KHÔNG resolve" in drift2[0]["detail"],
          "got %s" % drift2)


def test_count_gate():
    check("section count: 111 -> PASS", check_section_count(111) == [])
    drift = check_section_count(110)
    check("section count: 110 -> FAIL", len(drift) == 1 and
          drift[0]["gate"] == "section_count", "got %s" % drift)


# ------------------------------------------------------- JS parser helpers
def test_js_parser():
    src = ("var GRID_META = { /* brace { in comment */\n"
           "  'PLI_M72': { loops: { ds_nganh: { tag: 'ma_nganh' },"
           " other: 1, flag: true } },\n"
           "  ds_plain: { tag: 'x', note: \"brace } inside\" }, // } trail\n"
           "};")
    stripped = strip_js(src)
    body = find_js_block(stripped, r"\bvar\s+GRID_META\s*=")
    check("find_js_block: cân bằng ngoặc bỏ qua comment/string",
          body is not None and body.count("{") == body.count("}"),
          "body=%r" % (body,))
    entries = dict(iter_js_entries(body))
    check("iter_js_entries: key quoted 'PLI_M72' vẫn còn sau strip",
          "PLI_M72" in entries, "keys=%s" % list(entries))
    check("iter_js_entries: key không quoted vẫn đọc được",
          "ds_plain" in entries, "keys=%s" % list(entries))
    inner = dict(iter_js_entries(entries["PLI_M72"]))
    check("iter_js_entries: wrapper loops tồn tại", "loops" in inner,
          "inner=%s" % list(inner))
    loops_block = dict(iter_js_entries(inner["loops"]))
    check("iter_js_entries: object + primitive entry cùng tầng đọc đủ "
          "(ds_nganh/other/flag)",
          set(loops_block) == {"ds_nganh", "other", "flag"},
          "loops_block=%s" % list(loops_block))

    check("strip_js: bỏ // comment", "//" not in strip_js("a // x\nb"))
    check("strip_js: brace trong string không đếm",
          strip_js("{'a': 'x{y}z'}").count("{") == 1)


def test_js_block_not_found():
    check("find_js_block: không có -> None",
          find_js_block("var X = 5;", r"\bvar\s+GRID_META\s*=") is None)


# ------------------------------------------------- bridge / legal / chk
def test_bridge_loop_names():
    inv = {"nganh_xoa_bo", "ds_nganh"}
    ov = {"evidence": "P1 integrate: loop rieng nganh_xoa_bo; suite 13 PASS."}
    got = bridge_loop_names(ov, inv, {"a6_2_nganh_bo", "nganh_bo"})
    check("bridge: tên loop trong override evidence + có thật trong "
          "inventory -> bridge", got == ["nganh_xoa_bo"], "got %s" % got)

    check("bridge âm: không override -> rỗng",
          bridge_loop_names(None, inv, set()) == [])
    check("bridge âm: tên trong evidence KHÔNG có trong inventory -> không "
          "bridge (chống bịa)",
          bridge_loop_names({"evidence": "loop rieng nganh_tuong_tuong"},
                            inv, set()) == [])
    check("bridge âm: base_names (section_id/semantic khớp trực tiếp) bị "
          "loại khỏi kết quả",
          bridge_loop_names({"evidence": "dung ds_nganh"},
                            inv, {"ds_nganh"}) == [])


def test_legal_blocker_flags():
    blocked, src, n0 = legal_blocker_flags("cần owner chốt blocker pháp lý",
                                           [])
    check("legal blocker + (notes ghi blocker) -> True",
          blocked and "notes" in (src or "") and n0 == 0,
          "got %s / %s" % (blocked, src))

    blocked2, src2, n1 = legal_blocker_flags(
        "notes bình thường", ["Câu hỏi pháp lý 1?", "Câu hỏi 2?"])
    check("legal blocker + (form có legal_questions) -> True",
          blocked2 and "legal_questions" in (src2 or "") and n1 == 2,
          "got %s / %s" % (blocked2, src2))

    blocked3, src3, _ = legal_blocker_flags("", [])
    check("legal blocker âm: không notes blocker, không legal_questions",
          blocked3 is False and src3 is None, "got %s / %s" % (blocked3, src3))


def test_match_blocks_chk_prefix():
    blocks_doc = {"blocks": [
        {"t": "p", "runs": [{"text": "Doanh nghiệp nằm trong"}]},
        {"t": "chk", "key": "chk_khu_cong_nghiep"},
        {"t": "chk", "key": "chk_khu_che_xuat"},
    ]}
    section = {"notes": "đã map đủ các chk_khu_*", "source_evidence": {}}
    bm = match_blocks(blocks_doc, set(), section, "")
    check("chk prefix: token 'chk_khu_' khớp các key chk_khu_* -> chk_ok",
          bm["chk_ok"] is True and bm["chk_missing"] == [],
          "got %s / %s" % (bm["chk_ok"], bm["chk_missing"]))

    section_bad = {"notes": "nhóm chk_khue_ (sai tên)", "source_evidence": {}}
    bm2 = match_blocks(blocks_doc, set(), section_bad, "")
    check("chk prefix âm: token không khớp key nào -> chk_ok False + liệt "
          "kê thiếu", bm2["chk_ok"] is False and bm2["chk_missing"] ==
          ["chk_khue_"], "got %s / %s" % (bm2["chk_ok"], bm2["chk_missing"]))

    bm3 = match_blocks(blocks_doc, set(), {"notes": None,
                                           "source_evidence": {}}, "")
    check("chk: notes không nêu token -> chk_ok None (không kết luận)",
          bm3["chk_ok"] is None)


def main():
    print("== selftest tools/test_table_coverage_audit.py ==")
    test_implemented()
    test_partial()
    test_missing()
    test_blocked()
    test_no_table()
    test_output_only()
    test_removed()
    test_override_gate()
    test_count_gate()
    test_js_parser()
    test_js_block_not_found()
    test_bridge_loop_names()
    test_legal_blocker_flags()
    test_match_blocks_chk_prefix()
    fails = [r for r in RESULTS if not r[1]]
    print("\nTOTAL: %d | PASS: %d | FAIL: %d"
          % (len(RESULTS), len(RESULTS) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
