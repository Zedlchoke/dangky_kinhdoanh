#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""row_placement_census.py — F3T Lane A (TABLE-ROW-PLACEMENT): census/inventory
động của MỌI bảng lặp mang ``blankRows`` (K) tại HEAD. READ-ONLY với
production (blocks, form_maps, templates, docx_render) — tool chỉ ĐỌC và ghi
kết quả ra ``docs/audits/``.

Nguồn sự thật được quét:

  * ``app/data/blocks/<form_id>.json`` — block ``{"t": "loop", "blankRows": K,
    "cols": [...], "headerRows": [...]}``: K = số hàng trắng in sẵn theo bản
    giấy nguồn, ``cols`` = map cột -> tag dữ liệu.
  * ``app/data/form_maps.json``        — ``dynamic_tables`` (dt_id,
    table_index, occurrence_id) + ``section_specs`` (kind, semantic_key,
    min_rows) để join theo ``loop``.
  * ``app/templates/<form_id>.docx``   — bằng chứng ``w:tbl`` thật: đếm hàng
    header, số hàng trắng THẬT trong template (w:tr không chữ không tag),
    hàng khuôn có marker ``{#loop}…{/loop}`` và vị trí hàng trắng (trước/sau
    hàng khuôn).

Trường mỗi entry (machine-readable, mảng ``loops`` trong JSON):

    form_id, loop, kind, semantic_key, blank_rows (K), n_cols, cols,
    has_marker_row, template {file, table_ordinal, rows_total, header_rows,
    blank_rows_in_template, blank_before_template_row,
    blank_after_template_row, template_marker_rows, matches_blocks_K,
    cond_region}, policy, source_evidence

Hợp đồng row-placement (F3T, do Lane C ``docx_render._expand_loops`` thực
thi): ``max(K, N)`` — N dòng dữ liệu in từ hàng đầu, K−N dòng trắng sau;
blank không STT; N ≥ K không append thêm hàng trắng.

EXCEPTION REGISTRY (bắt buộc đọc trước khi sửa)
-----------------------------------------------
``EXCEPTION_REGISTRY`` dưới đây mặc định RỖNG — mọi loop đều dùng policy
``max-fill`` (tức hợp đồng ``max(K, N)`` ở trên). Mode ngoại lệ (ví dụ
``fixed-blank-after``: bảng cần đúng K hàng trắng CỐ ĐỊNH đứng SAU dữ liệu,
ngoài hợp đồng max(K,N)) CHỈ được đăng ký khi có đủ CẢ BA:

  1. ``source_evidence``: đường dẫn tới bản giấy/ảnh scan mẫu pháp lý hiện
     hành + trích đoạn văn bản cho thấy bảng in đúng K hàng trắng cố định;
  2. tham chiếu phê duyệt của owner (file decision registry / chỉ thị);
  3. loop cụ thể (form_id + loop) — CẤM allowlist mù theo hình dạng.

Không TỰ gán exception nào khi chưa có evidence: scanner này không suy
diễn mode từ hình dạng template, nó chỉ đọc registry.

Chạy:
    python3 -X utf8 -m tools.census.row_placement_census           # ghi docs
    python3 -X utf8 -m tools.census.row_placement_census --no-write

Gate: exit != 0 khi (a) số loop/form lệch EXPECTED_COUNTS, (b) một loop nào
có ``blankRows`` nhưng không tìm thấy hàng khuôn marker trong template,
(c) số hàng trắng thật trong template lệch K của blocks, (d) một loop nào
tuyên bố mode khác ``max-fill`` mà không nằm trong registry có evidence.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import OrderedDict, Counter

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCKS_DIR = os.path.join(REPO, "app", "data", "blocks")
FORM_MAPS_PATH = os.path.join(REPO, "app", "data", "form_maps.json")
TEMPLATES_DIR = os.path.join(REPO, "app", "templates")
OUT_JSON = os.path.join(REPO, "docs", "audits", "row_placement_census.json")
OUT_MD = os.path.join(REPO, "docs", "audits", "row_placement_census.md")

# Drift gate — kiểm lại census sơ bộ của owner (2026-09-08): 47 loop / 26 form,
# 37 loop K=4, 10 loop K=5. Đổi cấu trúc có chủ đích phải cập nhật hằng số này.
EXPECTED_COUNTS = OrderedDict([
    ("loops_with_blank_rows", 47),
    ("forms_with_blank_rows", 26),
    ("loops_k4", 37),
    ("loops_k5", 10),
])

# Hợp đồng row-placement hiện hành — Lane C thực thi trong _expand_loops.
POLICY_MAX_FILL = "max-fill"

# ---------------------------------------------------------------------------
# EXCEPTION REGISTRY — RỖNG theo chỉ thị F3T Lane A (cấm allowlist mù).
#
# Cú pháp khi CÓ source-evidence + phê duyệt owner:
#
#   EXCEPTION_REGISTRY = {
#       ("PLI_MXX", "ten_loop"): {
#           "mode": "fixed-blank-after",        # tên mode ngoại lệ
#           "reason": "Mẫu pháp lý in đúng K hàng trắng cố định sau dữ liệu",
#           "source_evidence": "docs/evidence/PLI_MXX_scan.png (trích: ...)",
#           "owner_approval": "docs/decision_registry.md#<mục>",
#       },
#   }
#
# Tool sẽ gán policy theo registry; mọi loop ngoài registry là ``max-fill``.
# KHÔNG thêm entry nếu thiếu 1 trong 3 điều kiện nêu ở module docstring.
# ---------------------------------------------------------------------------
EXCEPTION_REGISTRY: dict = {}


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def walk_loops(node, out: list) -> None:
    """Thu mọi dict block ``t == 'loop'`` mang ``blankRows`` (đệ quy mọi mức)."""
    if isinstance(node, dict):
        if node.get("t") == "loop" and node.get("blankRows"):
            out.append(node)
        for v in node.values():
            walk_loops(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_loops(v, out)


def scan_blocks() -> "OrderedDict[str, list]":
    """{form_id: [loop_block, ...]} từ app/data/blocks, sắp theo form_id."""
    forms: "OrderedDict[str, list]" = OrderedDict()
    for fid in sorted(os.listdir(BLOCKS_DIR)):
        if not fid.endswith(".json"):
            continue
        doc = json.loads(read_text(os.path.join(BLOCKS_DIR, fid)))
        found: list = []
        walk_loops(doc, found)
        if found:
            forms[fid[:-5]] = found
    return forms


def join_form_maps(fm: dict, form_id: str, loop: str) -> dict:
    """Join metadata form_maps cho 1 loop: dynamic_tables (dt) + section_specs
    (ss). dt_id có thể trùng giữa 2 loop khác table_index — trả theo thứ tự."""
    f = fm.get(form_id) or {}
    dts = [dt for dt in (f.get("dynamic_tables") or []) if dt.get("loop") == loop]
    sss = [ss for ss in (f.get("section_specs") or []) if ss.get("loop") == loop]
    dt = dts[0] if dts else {}
    ss = sss[0] if sss else {}
    return {
        "dt_found": bool(dts),
        "dt_id": dt.get("id"),
        "dt_table_index": dt.get("table_index"),
        "dt_occurrence_id": dt.get("occurrence_id"),
        "dt_duplicates": max(0, len(dts) - 1),
        "ss_found": bool(sss),
        "ss_kind": ss.get("kind"),
        "ss_semantic_key": ss.get("semantic_key"),
        "ss_min_rows": ss.get("min_rows"),
        "ss_table_index": ss.get("table_index"),
    }


_TR_RE = re.compile(r"<w:tr(?: [^>]*)?>.*?</w:tr>", re.S)
_WT_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")
_TAG_RE = re.compile(r"\{[#/?]?[A-Za-z_]")
_COND_MARK_RE = re.compile(r"\{\?([A-Za-z_][\w.]*)\}|\{/([A-Za-z_][\w.]*)\}")


def row_is_blank(row_xml: str) -> bool:
    """w:tr 'trắng thật': không chữ in được và không chứa tag/marker nào."""
    if _TAG_RE.search(row_xml):
        return False
    return "".join(_WT_RE.findall(row_xml)).strip() == ""


def template_proof(form_id: str, loop: str) -> dict:
    """Bằng chứng cấu trúc trong app/templates/<form_id>.docx: bảng w:tbl chứa
    marker ``{#loop}``, số hàng header / hàng trắng thật / hàng khuôn, vị trí
    hàng trắng tương đối với hàng khuôn và vùng điều kiện bao ngoài (nếu có)."""
    path = os.path.join(TEMPLATES_DIR, form_id + ".docx")
    proof = OrderedDict([
        ("file", "templates/%s.docx" % form_id),
        ("table_ordinal", None),
        ("rows_total", None),
        ("header_rows", None),
        ("blank_rows_in_template", None),
        ("blank_before_template_row", None),
        ("blank_after_template_row", None),
        ("template_marker_rows", 0),
        ("matches_blocks_K", None),
        ("cond_region", None),
    ])
    if not os.path.exists(path):
        proof["file"] = None
        return proof
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")

    tables = list(re.finditer(r"<w:tbl[ >].*?</w:tbl>", xml, re.S))
    target = next((m for m in tables if "{#%s}" % loop in m.group(0)), None)
    if target is None:
        return proof
    proof["table_ordinal"] = tables.index(target)

    # Vùng điều kiện bao ngoài: quét marker {?flag}/{/flag} theo thứ tự văn bản
    # trước bảng, dựng stack. Marker nằm trong cùng ô bảng loop được bỏ qua
    # (chỉ tính marker TRƯỚC bảng).
    stack: list = []
    for m in _COND_MARK_RE.finditer(xml[: target.start()]):
        if m.group(1):
            stack.append(m.group(1))
        elif stack and stack[-1] == m.group(2):
            stack.pop()
    proof["cond_region"] = stack[-1] if stack else None

    rows = _TR_RE.findall(target.group(0))
    tpl_idx = [i for i, r in enumerate(rows) if "{#%s}" % loop in r]
    proof["template_marker_rows"] = len(tpl_idx)
    header = [i for i, r in enumerate(rows)
              if i not in tpl_idx and not row_is_blank(r)]
    blank_idx = [i for i, r in enumerate(rows)
                 if i not in tpl_idx and row_is_blank(r)]
    proof["rows_total"] = len(rows)
    proof["header_rows"] = len(header)
    proof["blank_rows_in_template"] = len(blank_idx)
    if tpl_idx:
        first_tpl, last_tpl = tpl_idx[0], tpl_idx[-1]
        proof["blank_before_template_row"] = sum(1 for i in blank_idx
                                                 if i < first_tpl)
        proof["blank_after_template_row"] = sum(1 for i in blank_idx
                                                if i > last_tpl)
    return proof


def census() -> tuple:
    """Chạy census. Trả (payload_dict, gate_fail_list)."""
    fm = json.loads(read_text(FORM_MAPS_PATH))
    forms = scan_blocks()

    loops_out = []
    k_hist = Counter()
    for form_id, blocks in forms.items():
        for blk in blocks:
            loop = blk.get("loop") or blk.get("name")
            k = int(blk["blankRows"])
            k_hist[k] += 1
            cols = [{"col": c.get("col"), "tag": c.get("tag")}
                    for c in (blk.get("cols") or [])]
            jm = join_form_maps(fm, form_id, loop)
            proof = template_proof(form_id, loop)

            exc = EXCEPTION_REGISTRY.get((form_id, loop))
            policy = exc["mode"] if exc else POLICY_MAX_FILL
            has_marker = bool(proof.get("template_marker_rows"))
            matches_k = (proof.get("blank_rows_in_template") == k
                         if proof.get("blank_rows_in_template") is not None
                         else None)

            loops_out.append(OrderedDict([
                ("form_id", form_id),
                ("loop", loop),
                ("kind", jm["ss_kind"] or "editable-grid"),
                ("semantic_key", jm["ss_semantic_key"]),
                ("blank_rows", k),
                ("n_cols", len(cols)),
                ("cols", cols),
                ("header_rows_blocks", len(blk.get("headerRows") or [])),
                ("has_marker_row", has_marker),
                ("template", proof),
                ("template_matches_K", matches_k),
                ("form_maps", OrderedDict([
                    ("dt_found", jm["dt_found"]),
                    ("dt_id", jm["dt_id"]),
                    ("dt_table_index", jm["dt_table_index"]),
                    ("dt_occurrence_id", jm["dt_occurrence_id"]),
                    ("dt_duplicate_loops", jm["dt_duplicates"]),
                    ("ss_found", jm["ss_found"]),
                    ("ss_min_rows", jm["ss_min_rows"]),
                ])),
                ("policy", policy),
                ("policy_source", ("exception_registry" if exc
                                   else "default max(K,N) — không có ngoại lệ "
                                        "được đăng ký")),
                ("source_evidence", OrderedDict([
                    ("blocks", "app/data/blocks/%s.json t:loop %s.blankRows"
                               % (form_id, loop)),
                    ("form_maps", "app/data/form_maps.json %s.dynamic_tables"
                                  % form_id),
                    ("template", proof.get("file")),
                ])),
            ]))

    forms_n = len(forms)
    counts = OrderedDict([
        ("loops_with_blank_rows", len(loops_out)),
        ("forms_with_blank_rows", forms_n),
        ("loops_k4", k_hist.get(4, 0)),
        ("loops_k5", k_hist.get(5, 0)),
        ("k_distribution", OrderedDict(sorted(k_hist.items()))),
        ("per_form", OrderedDict(
            (f, len(b)) for f, b in forms.items())),
    ])

    gate_fail = []
    for key, expected in EXPECTED_COUNTS.items():
        if counts.get(key) != expected:
            gate_fail.append("%s=%d (expected %d)"
                             % (key, counts.get(key, -1), expected))
    for lp in loops_out:
        if not lp["has_marker_row"]:
            gate_fail.append("NO_MARKER_ROW %s.%s (template %s)"
                             % (lp["form_id"], lp["loop"],
                                lp["template"].get("file")))
        elif lp["template_matches_K"] is not True:
            gate_fail.append("TEMPLATE_BLANK_MISMATCH %s.%s blocks_K=%d "
                             "template_blank=%s"
                             % (lp["form_id"], lp["loop"], lp["blank_rows"],
                                lp["template"].get("blank_rows_in_template")))
        if lp["policy"] != POLICY_MAX_FILL and not (
                EXCEPTION_REGISTRY.get((lp["form_id"], lp["loop"])) or {}
                ).get("source_evidence"):
            gate_fail.append("EXCEPTION_WITHOUT_EVIDENCE %s.%s mode=%s"
                             % (lp["form_id"], lp["loop"], lp["policy"]))

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    payload = OrderedDict([
        ("meta", OrderedDict([
            ("tool", "tools/census/row_placement_census.py"),
            ("lane", "F3T Lane A (TABLE-ROW-PLACEMENT) — census/inventory"),
            ("head", head),
            ("generated_at_utc",
             datetime.datetime.now(datetime.timezone.utc)
             .strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("expected_counts", EXPECTED_COUNTS),
            ("counts", counts),
            ("gate", "FAIL: %s" % "; ".join(gate_fail) if gate_fail
             else "PASS"),
        ])),
        ("row_placement_contract", OrderedDict([
            ("policy_default", POLICY_MAX_FILL),
            ("definition", "max(K, N): N dòng dữ liệu in từ hàng đầu, "
                           "K−N dòng trắng sau; blank không STT; "
                           "N >= K không append hàng trắng."),
            ("enforced_by", "tools/docx_render.py::_expand_loops (Lane C)"),
        ])),
        ("exception_registry", OrderedDict([
            ("note", "RỖNG theo chỉ thị F3T Lane A: cấm allowlist mù. Mỗi "
                     "ngoại lệ mode riêng PHẢI có source-evidence (bản giấy/"
                     "ảnh mẫu pháp lý) + phê duyệt owner; xem module docstring "
                     "của tool để biết cú pháp đăng ký."),
            ("entries", EXCEPTION_REGISTRY),
        ])),
        ("loops", loops_out),
    ])
    return payload, gate_fail


def write_md(payload: dict, path: str) -> None:
    meta = payload["meta"]
    counts = meta["counts"]
    lines = [
        "# Row-placement census (F3T Lane A) — loops có `blankRows`",
        "",
        "Sinh bởi `tools/census/row_placement_census.py` tại HEAD `%s` (%s)."
        % (meta["head"], meta["generated_at_utc"]),
        "",
        "Hợp đồng mặc định: **%s** — %s" % (
            payload["row_placement_contract"]["policy_default"],
            payload["row_placement_contract"]["definition"]),
        "",
        "| đại lượng | số |",
        "|---|---|",
    ]
    for k, v in counts.items():
        if k == "per_form":
            continue
        if isinstance(v, dict):
            v = ", ".join("%s:%s" % (ik, iv) for ik, iv in v.items())
        lines.append("| %s | %s |" % (k, v))
    lines += ["", "Gate phủ: **%s**" % meta["gate"], "",
              "## Registry ngoại lệ", "",
              payload["exception_registry"]["note"], "",
              "## Danh sách loop", "",
              "| form | loop | kind | K | cols | semantic_key | header | "
              "blank thật trong template | trắng trước/sau hàng khuôn | "
              "cond | policy |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for lp in payload["loops"]:
        t = lp["template"]
        lines.append(
            "| %s | `%s` | %s | %d | %d | %s | %s | %s | %s/%s | %s | %s |" % (
                lp["form_id"], lp["loop"], lp["kind"], lp["blank_rows"],
                lp["n_cols"], lp["semantic_key"] or "—",
                t.get("header_rows") if t.get("header_rows") is not None
                else "N/A",
                t.get("blank_rows_in_template")
                if t.get("blank_rows_in_template") is not None else "N/A",
                t.get("blank_before_template_row"),
                t.get("blank_after_template_row"),
                t.get("cond_region") or "—",
                lp["policy"]))
    lines += ["", "Chi tiết đầy đủ (machine-readable): "
              "`docs/audits/row_placement_census.json`.", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(argv=None) -> int:
    payload, gate_fail = census()
    no_write = "--no-write" in (argv if argv is not None else sys.argv[1:])
    if not no_write:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        write_md(payload, OUT_MD)
    print("counts:", json.dumps(payload["meta"]["counts"], ensure_ascii=False))
    print("gate:", payload["meta"]["gate"])
    if gate_fail:
        for g in gate_fail:
            print("  -", g)
    return 1 if gate_fail else 0


if __name__ == "__main__":
    sys.exit(main())
