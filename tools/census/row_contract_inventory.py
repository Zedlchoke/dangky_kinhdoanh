#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""row_contract_inventory.py — Phase 4: inventory machine-readable của MỌI
repeatable table/grid contract trong app (PLAN Wave row/blank-row contract).

Đọc-only các nguồn sự thật:

  * ``app_web/ui/form-domain.js``  — GRID_META / FORM_GRID_META /
    FORM_TABLE_CONTRACTS (parser dùng chung với table_coverage_audit)
  * ``app/data/form_maps.json``    — dynamic_tables / section_specs
  * ``app/data/blocks/<fid>.json`` — block loop mang ``blankRows`` (số hàng
    trắng in sẵn theo bản giấy nguồn — "fixed legal row", KHÔNG phải blank
    row của người dùng)

Sinh ``docs/row_contract_inventory.json`` + ``.md``: mỗi contract một entry
(form_id · section_id · grid_id/loop · kind · variant/activeWhen · minRows ·
required · empty-row policy · export-row policy · DOCX loop/table · source
evidence · test coverage). Kèm mục ``policies`` (hợp đồng row/blank-row hiện
hành) và ``gaps`` (khai-báo chưa được enforce — không tự vá, chờ owner).

Gate phủ: exit != 0 khi một họ contract không scan được hoặc đếm lệch chuẩn
(GRID_META=11, FORM_TABLE_CONTRACTS=14, dynamic_tables=42, section_specs=21
tại thời điểm viết — đổi có chủ đích phải cập nhật EXPECTED_COUNTS).

Chạy:
    python3 -X utf8 -m tools.census.row_contract_inventory           # ghi docs
    python3 -X utf8 -m tools.census.row_contract_inventory --no-write
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from tools.census.table_coverage_audit import (  # noqa: E402
    find_js_block, find_block_from, iter_js_entries, strip_js,
)

FD_JS = os.path.join(REPO, "app_web", "ui", "form-domain.js")
FORM_MAPS_PATH = os.path.join(REPO, "app", "data", "form_maps.json")
BLOCKS_DIR = os.path.join(REPO, "app", "data", "blocks")
OUT_JSON = os.path.join(REPO, "docs", "row_contract_inventory.json")
OUT_MD = os.path.join(REPO, "docs", "row_contract_inventory.md")

EXPECTED_COUNTS = {
    "global_grids": 11,
    "section_contracts": 14,
    "dynamic_tables": 42,
    "section_specs": 21,
}

# Hợp đồng row/blank-row hiện hành (đúng như code thực thi tại HEAD này).
POLICIES = OrderedDict([
    ("blank_row", "Dòng MỌI ô trống (bỏ key nội bộ _*) không trở thành "
                  "business data: GridCtl.exportLoops (app.js) lọc trước, "
                  "_expand_loops (docx_render.py) guard last-mile; {_stt} "
                  "đánh lại trên dòng dữ liệu in ra."),
    ("blank_helper_ui", "UI render tối thiểu 1 dòng trống helper cho grid "
                        "cho-phép-thêm (render.js renderLoop/nested) — dòng "
                        "ảo KHÔNG nằm trong store cho tới khi người dùng gõ."),
    ("partial_row", "Dòng điền một phần được GIỮ (không âm thầm mất); "
                    "validator chặn theo contract: ROW_INCOMPLETE (thiếu cột "
                    "required), MIN_ROWS, INDUSTRY_REQUIRED, MAX_ROWS (warn)."),
    ("fixed_legal_row", "fixed-matrix in ĐỦ dòng pháp định bất kể ô nhập trống "
                        "(kể cả dòng Tổng output_only, tổng recompute strict "
                        "fail-loud). blankRows của blocks là hàng trắng IN "
                        "SẴN theo bản giấy — không bị lọc, không bị đếm là "
                        "dữ liệu."),
    ("inactive_variant", "M72: grid inactive-theo-selector (valueOf "
                         "dn.loai_hinh) -> payload rỗng cho grid đó; block "
                         "DOCX {?flag} của variant sai bị drop."),
    ("stt", "STT KHÔNG lưu: suy từ thứ tự mảng sau lọc — engine {_stt} "
            "1-based; fixed-matrix chỉ khi spec.stt.mode='generated'."),
    ("draft", "store.loops[loop] là mảng — thứ tự + _row_id bảo toàn qua "
              "draft save/load; blank row SỐNG trong draft, chỉ lọc ở "
              "export; migrateDraft v1->v2 additive."),
    ("grid_ops", "add/delete/reorder/duplicate/clear scope theo tên loop "
                 "(GridCtl); policy theo kind: fixed-matrix/output-table "
                 "F/F/F, nested-grid + editable-grid T/T/T; duplicate bỏ "
                 "duplicateKeys + _row_id; confirm xóa dòng có dữ liệu."),
])

GAPS = [
    {
        "id": "nested_grid_min_rows_declared_not_enforced",
        "detail": "spec.min_rows=1 khai tại 3 nested-grid (PLI_M02 "
                  "nddpl_uy_quyen_chu_so_huu, PLI_M12 ndd_uy_quyen_sau_thay_doi, "
                  "PLI_M15 ndd_pl_uy_quyen_chu_so_huu_moi) nhưng KHÔNG tầng "
                  "nào enforce (nested-grid.js validate không đọc; rowOpMeta "
                  "chỉ đọc max_rows). Nghĩa nghiệp vụ chưa chốt: (a) bắt buộc "
                  "≥1 dòng khi section ĐANG trống sẽ chặn export hợp lệ của "
                  "hồ sơ không ủy quyền; (b) enforce khi section có dữ liệu "
                  "thì min_rows=1 là hiển nhiên. -> BLOCKED_OWNER, xem "
                  "docs/decision_registry.md câu hỏi owner Phase 4.",
    },
]

TEST_COVERAGE = OrderedDict([
    ("blank_only_row_not_exported", [
        "app_web/test_row_contract_corpus.js R1",
        "tools/test_row_contract_export.py [RC1]",
    ]),
    ("one_row_and_order", [
        "app_web/test_row_contract_corpus.js R2",
        "tools/test_row_contract_export.py [RC2]",
    ]),
    ("partial_row_kept", [
        "app_web/test_row_contract_corpus.js R3",
        "tools/test_row_contract_export.py [RC3]",
    ]),
    ("grid_ops_isolation", [
        "app_web/test_row_contract_corpus.js R4",
        "app_web/test_grid.js B (add/delete/reorder/duplicate/clear)",
    ]),
    ("draft_roundtrip", [
        "app_web/test_row_contract_corpus.js R5/R8",
        "app_web/test_p3_draft.js D1-D30",
    ]),
    ("stt_computed", [
        "app_web/test_grid.js B (STT đánh lại theo mảng)",
        "tools/test_row_contract_export.py [RC2]/[RC4]",
    ]),
    ("m72_variant_isolation", [
        "app_web/test_row_contract_corpus.js R7/R8",
        "app_web/test_m72_activation.js",
        "tools/test_m72_conditional_export.py",
    ]),
    ("fixed_matrix_rows_and_totals", [
        "tools/test_row_contract_export.py [FM1-FM3]",
        "tools/test_export_grid_kinds.py [TS1-TS6]",
    ]),
    ("no_marker_leftover", [
        "tools/test_row_contract_export.py [RC5]",
        "tools/test_acceptance_docx.py",
    ]),
])


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def raw_entries(js_text: str, header_re: str) -> dict:
    """{key: raw_value_text} tầng đầu của object literal khai báo."""
    body = find_js_block(strip_js(js_text), header_re)
    return {k: v for k, v in iter_js_entries(body)} if body else {}


def scalar(raw: str, name: str):
    """Giá trị scalar `name:` trong raw (strip_js chuẩn hoá string sang
    nháy kép nên chấp nhận cả hai loại quote + ký tự '-' trong value)."""
    m = re.search(r"\b%s\s*:\s*('(?:[^']*)'|\"(?:[^\"]*)\"|[A-Za-z0-9_.\-]+"
                  r"|\[[^\]]*\])" % name, raw or "")
    if not m:
        return None
    v = m.group(1)
    if v.startswith("["):
        return [x for x in re.findall(r"'([^']*)'|\"([^\"]*)\"", v)
                for x in x if x]
    return v.strip("'\"")


def active_when_variant(raw: str):
    """(THUẦN) equals[...] của `activeWhen: { valueOf: {...} }` — brace cân
    bằng (regex [^}]* không nuốt được valueOf lồng)."""
    m = re.search(r"\bactiveWhen\s*:\s*", raw or "")
    if not m:
        return None
    blk = find_block_from(raw, m.end())
    if not blk:
        return None
    eq = re.search(r"equals\s*:\s*\[([^\]]*)\]", blk)
    if not eq:
        return "conditional"
    return ", ".join(x for tup in re.findall(r"'([^']*)'|\"([^\"]*)\"",
                                             eq.group(1)) for x in tup if x)


def sub_loop_raws(form_raw: str) -> dict:
    """{loop: raw_text} của khối `loops: { ... }` trong 1 entry form.

    Value của entry có thể là object literal HOẶC lời gọi mkGrid(BASE,
    {...}) — iter_js_entries chỉ xử lý được loại đầu (cắt tại dấu phẩy
    tầng-0 bên trong call) nên scanner này tự lấy balanced-parens cho call,
    rồi thay options object vào value. Lọc bỏ entry phi-grid (label/
    minRows/semanticKey/activeWhen đứng riêng...)."""
    m = re.search(r"\bloops\s*:\s*\{", form_raw or "")
    if not m:
        return {}
    sub = find_block_from(form_raw, m.end() - 1)
    if not sub:
        return {}
    entry_re = re.compile(r"\s*([A-Za-z_$][\w$]*)\s*:\s*")
    n, i = len(sub), 1
    out = {}
    while i < n - 1:
        em = entry_re.match(sub[i:])
        if not em:
            i += 1
            continue
        key = em.group(1)
        j = i + em.end()
        while j < n and sub[j] in " \t\r\n":
            j += 1
        depth, k2 = 0, j
        if sub[j] == "{":
            blk = find_block_from(sub, j)
            k2 = (j + len(blk) - 1) if blk else j
            val = blk or ""
        elif sub[j] not in ",}":
            while k2 < n:
                if sub[k2] == "(":
                    depth += 1
                elif sub[k2] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k2 += 1
            val = sub[j:k2 + 1] if depth == 0 else ""
        else:
            val = ""
            k2 = j
        if val:
            b = val.find("{")
            if "mkGrid" in val and b >= 0:
                opts = find_block_from(val, b)
                val = "mkGrid " + opts if opts else val
            if "mkGrid" in val or "tag:" in val or "columns" in val:
                out[key] = val
        i = k2 + 1
    return out


def blocks_blank_rows() -> list:
    out = []
    for fid in sorted(os.listdir(BLOCKS_DIR)):
        if not fid.endswith(".json"):
            continue
        doc = json.load(open(os.path.join(BLOCKS_DIR, fid), encoding="utf-8"))
        stack = [doc]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                if cur.get("t") == "loop" and cur.get("blankRows"):
                    out.append(OrderedDict([
                        ("form_id", fid[:-5]),
                        ("loop", cur.get("loop") or cur.get("name")),
                        ("blank_rows_printed", cur.get("blankRows")),
                        ("policy", "fixed legal blank rows in sẵn theo bản "
                                   "giấy — luôn in, không là dữ liệu"),
                    ]))
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    return out


def main(argv=None) -> int:
    js = read(FD_JS)
    fm = json.load(open(FORM_MAPS_PATH, encoding="utf-8"))

    gm_raw = raw_entries(js, r"\bvar\s+GRID_META\s*=")
    fgm_raw = raw_entries(js, r"\bvar\s+FORM_GRID_META\s*=")
    contracts_raw = raw_entries(js, r"\bvar\s+FORM_TABLE_CONTRACTS\s*=")

    # ---- global editable grids (GRID_META) ----
    global_grids = []
    for name in sorted(gm_raw):
        raw = gm_raw[name]
        global_grids.append(OrderedDict([
            ("form_id", "*"),
            ("grid_id", name),
            ("kind", "editable-grid"),
            ("variant_activeWhen", None),
            ("min_rows_filled", scalar(raw, "minRows")),
            ("required", scalar(raw, "required")),
            ("require_primary", scalar(raw, "requirePrimary")),
            ("duplicate_keys", scalar(raw, "duplicateKeys") or []),
            ("source_evidence", "app_web/ui/form-domain.js GRID_META.%s" % name),
        ]))

    # ---- form-scoped grids (FORM_GRID_META) ----
    form_grids = []
    for form in sorted(fgm_raw):
        for loop, raw in sorted(sub_loop_raws(fgm_raw[form]).items()):
            variant = active_when_variant(raw)
            if variant == "conditional":
                variant = "conditional (checkedKey/minFilledRows)"
            form_grids.append(OrderedDict([
                ("form_id", form),
                ("grid_id", loop),
                ("kind", "editable-grid"),
                ("variant_activeWhen", variant),
                ("min_rows_filled", scalar(raw, "minRows")),
                ("required", scalar(raw, "required")),
                ("source_evidence",
                 "app_web/ui/form-domain.js FORM_GRID_META.%s.loops.%s"
                 % (form, loop)),
            ]))

    # ---- section contracts (FORM_TABLE_CONTRACTS) ----
    section_contracts = []
    for form in sorted(contracts_raw):
        marks = list(re.finditer(r'sectionId\s*:\s*["\']([^"\']+)["\']',
                                 contracts_raw[form]))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else \
                len(contracts_raw[form])
            raw = contracts_raw[form][m.start():end]
            kind = scalar(raw, "kind") or "output-table"
            section_contracts.append(OrderedDict([
                ("form_id", form),
                ("section_id", m.group(1)),
                ("kind", kind),
                ("allow_add", scalar(raw, "allowAdd")),
                ("allow_delete", scalar(raw, "allowDelete")),
                ("allow_reorder", scalar(raw, "allowReorder")),
                ("stt_mode", (re.search(r"stt\s*:\s*\{\s*mode:\s*[\"']([^\"']+)[\"']",
                                        raw) or [None, None])[1]),
                ("min_rows", scalar(raw, "min_rows")),
                ("totals", len(re.findall(r"formula\s*:", raw))),
                ("cross_field_rules", len(re.findall(
                    r"type:\s*'(percentSum|sumEqualsKey)'", raw))),
                ("export_row_policy",
                 "fixed legal rows luôn in" if kind == "fixed-matrix" else
                 ("grid tĩnh luôn in dù payload rỗng" if kind == "output-table"
                  else "selector-inactive -> rỗng; blank row bị lọc")),
                ("source_evidence",
                 "app_web/ui/form-domain.js FORM_TABLE_CONTRACTS.%s.%s"
                 % (form, m.group(1))),
            ]))

    # ---- form_maps dynamic_tables + section_specs ----
    dynamic_tables, section_specs = [], []
    for fid in sorted(fm):
        for i, dt in enumerate(fm[fid].get("dynamic_tables") or []):
            dynamic_tables.append(OrderedDict([
                ("form_id", fid),
                ("id", dt.get("id")),
                ("loop", dt.get("loop")),
                ("kind", "editable-grid"),
                ("occurrence_id", dt.get("occurrence_id")),
                ("table_index", dt.get("table_index")),
                ("n_columns", len(dt.get("columns") or [])),
                ("source_evidence",
                 "app/data/form_maps.json %s.dynamic_tables[%d]" % (fid, i)),
            ]))
        for i, ss in enumerate(fm[fid].get("section_specs") or []):
            section_specs.append(OrderedDict([
                ("form_id", fid),
                ("id", ss.get("id")),
                ("loop", ss.get("loop")),
                ("kind", ss.get("kind")),
                ("semantic_key", ss.get("semantic_key")),
                ("stt_mode", (ss.get("stt") or {}).get("mode")
                 if isinstance(ss.get("stt"), dict) else None),
                ("n_fixed_rows", len(ss.get("fixed_rows") or [])
                 if isinstance(ss.get("fixed_rows"), list) else None),
                ("table_index", ss.get("table_index")),
                ("min_rows", ss.get("min_rows")),
                ("source_evidence",
                 "app/data/form_maps.json %s.section_specs[%d]" % (fid, i)),
            ]))

    counts = {
        "global_grids": len(global_grids),
        "form_grids": len(form_grids),
        "section_contracts": len(section_contracts),
        "dynamic_tables": len(dynamic_tables),
        "section_specs": len(section_specs),
        "blocks_blank_rows": len(blocks_blank_rows()),
    }
    gate_fail = [k for k, v in EXPECTED_COUNTS.items()
                 if counts.get(k) != v]

    payload = OrderedDict([
        ("meta", OrderedDict([
            ("tool", "tools/census/row_contract_inventory.py"),
            ("head", subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                capture_output=True, text=True).stdout.strip()),
            ("expected_counts", EXPECTED_COUNTS),
            ("counts", counts),
            ("gate", "FAIL: %s" % gate_fail if gate_fail else "PASS"),
        ])),
        ("policies", POLICIES),
        ("gaps", GAPS),
        ("test_coverage", TEST_COVERAGE),
        ("global_grids", global_grids),
        ("form_grids", form_grids),
        ("section_contracts", section_contracts),
        ("dynamic_tables", dynamic_tables),
        ("section_specs", section_specs),
        ("blocks_blank_rows", blocks_blank_rows()),
    ])

    lines = [
        "# Row/blank-row contract inventory (Phase 4)",
        "",
        "Sinh bởi `tools/census/row_contract_inventory.py` tại HEAD `%s`."
        % payload["meta"]["head"],
        "",
        "| họ contract | số entry |",
        "|---|---|",
    ]
    for k, v in counts.items():
        lines.append("| %s | %d |" % (k, v))
    lines += ["", "Gate phủ: **%s**" % payload["meta"]["gate"], "",
              "## Policies (hợp đồng hiện hành)", ""]
    for k, v in POLICIES.items():
        lines.append("- **%s**: %s" % (k, v))
    lines += ["", "## Gaps (chờ owner)", ""]
    for g in GAPS:
        lines.append("- **%s**: %s" % (g["id"], g["detail"]))
    lines += ["", "Chi tiết đầy đủ: `docs/row_contract_inventory.json`.", ""]

    no_write = "--no-write" in (argv if argv is not None else sys.argv[1:])
    if not no_write:
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    print("counts:", json.dumps(counts))
    print("gate:", payload["meta"]["gate"])
    return 1 if gate_fail else 0


if __name__ == "__main__":
    sys.exit(main())
