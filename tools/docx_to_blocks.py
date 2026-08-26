# -*- coding: utf-8 -*-
"""Chuyển mỗi template app/templates/PLI_Mxx.docx thành app/data/blocks/<id>.json.

Template đã gắn the dạng {key} (key chấm được: dn.ten_tieng_viet), {chk_xxx},
và bảng loop có hàng khuôn chứa {#ten} ở ô đầu và {/ten} ở ô cuối cùng hàng,
các ô giữa là {tag_cot}. Biến đặc biệt {_stt} trong hàng khuôn là STT tự sinh
(1-based theo thứ tự dòng dữ liệu, engine render thay khi nhân bản hàng),
không được tính là cột dữ liệu trong cols.

Schema JSON đầu ra (blocks-v3 — mọi trường mới đều OPTIONAL, chỉ emit khi khác
default; block cũ thiếu role/format/vertAlign vẫn hợp lệ hoàn toàn):
{
  "id": "PLI_M02",
  "ten_mau": "...",            # lấy từ app/data/form_maps.json
  "blocks": [...],
  "v": 3                       # schema version (L1): 1 block mới có thể có
                               # "role"/"format"/"footnotes", run mới có thể có
                               # "vertAlign"/"role":"footnote-ref"
}
Block "p":
{"t":"p", "align":"left|center|right",
 "role": "...",               # optional, tools/layout_roles.py; thiếu = "body"
 "format": {...},             # optional, chỉ khi khác default:
                              # leftIndentPt/rightIndentPt/firstLineIndentPt/
                              # spaceBeforePt/spaceAfterPt (EMU→pt, làm tròn 1),
                              # lineSpacing (bội, vd 1.15) | lineSpacingPt
                              # (exact/at-least), keepWithNext=true
 "footnotes": {"7": "chú thích…"},  # optional, id→text từ word/footnotes.xml
 "runs":[
    {"text":"..."},                          # \n từ <w:br/>/<w:cr/>, \t từ
                                             # <w:tab/> được giữ nguyên ký tự
    {"text":"1","vertAlign":"superscript"},  # hoặc "subscript"
    {"role":"footnote-ref","footnoteId":7},  # <w:footnoteReference w:id="7"/>
    {"input":{"key":"dn.ten_tieng_viet","w":40}},
    {"input":{"key":"chk_x","chk":true}}     # chk lồng trong paragraph dài
 ]}
{"t":"chk", "label":"...", "key":"chk_x"},   # paragraph chỉ gồm chk + nhãn ngắn
{"t":"table", "widths":null, "rows":[
    {"cells":[{"runs":[...], "colspan":1, "rowspan":1}]}
]},
{"t":"loop", "loop":"ds_thanh_vien", "headerRows":[0],
 "cols":[{"col":1,"tag":"ho_ten"}], "blankRows":4, "rows":[...]}

Chạy:
    python -X utf8 tools/docx_to_blocks.py              # chuyển cả 87 file + tự kiểm định
    python -X utf8 tools/docx_to_blocks.py --one PLI_M02  # chuyển 1 file
"""
from __future__ import annotations

import io
import json
import os
import random
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Length
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import layout_roles

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "app" / "templates"
FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
OUT_DIR = ROOT / "app" / "data" / "blocks"

# Tag biến: {key} hoặc {a.b.c}; không khớp {#loop}/{/loop}
TAG_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")
LOOP_OPEN_RE = re.compile(r"\{#([A-Za-z0-9_]+)\}")
# Marker vùng điều kiện P1.2 M72 Option D: {?flag} mở / {/flag} đóng.
# Paragraph CHỈ chứa marker không sinh block; mọi block nằm trong vùng
# được gắn "cond": [flag, ...] (renderer UI lọc theo flag, engine DOCX
# tự loại vùng theo cùng flag - xem tools/docx_render.py).
COND_OPEN_FULL_RE = re.compile(r"^\{\?([A-Za-z0-9_]+)\}$")
COND_CLOSE_FULL_RE = re.compile(r"^\{/([A-Za-z0-9_]+)\}$")
CHK_PREFIX = "chk"


def iter_blocks(doc):
    """Duyệt body theo thứ tự: ('p', Paragraph) hoặc ('tbl', Table)."""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", Table(child, doc))


# ---------------------------------------------------------------------------
# Paragraph -> runs
# ---------------------------------------------------------------------------

def _para_full_text(p: Paragraph) -> str:
    return "".join(r.text for r in p.runs)


def _run_flags(run):
    return bool(run.bold), bool(run.italic), bool(run.underline)


def _run_vert_align(run):
    """'superscript'|'subscript' từ w:rPr/w:vertAlign, None nếu không có."""
    rPr = run._element.rPr
    if rPr is None:
        return None
    va = rPr.find(qn("w:vertAlign"))
    if va is None:
        return None
    val = va.get(qn("w:val"))
    return val if val in ("superscript", "subscript") else None


# python-docx 1.2.0 (docx/oxml/text/run.py CT_R.text) map các con của w:r
# thành ký tự: w:t -> text; w:br, w:cr -> "\n"; w:tab -> "\t";
# w:noBreakHyphen -> "-"; w:ptab -> "\t". _char_stream dựng lại ĐÚNG chuỗi đó
# kèm metadata từng ký tự và vị trí footnoteReference.
_CHAR_STREAM_TAGS = {
    qn("w:t"),
    qn("w:br"),
    qn("w:cr"),
    qn("w:tab"),
    qn("w:noBreakHyphen"),
    qn("w:ptab"),
}


def _char_stream(p: Paragraph):
    """Dựng dòng ký tự của paragraph với metadata mỗi ký tự.

    Trả về (chars, footnote_refs):
      chars: list[(ch, meta)], meta = (b, i, u, vertAlign)
      footnote_refs: list[(pos, id)] — pos là vị trí chèn trong stream
    """
    chars: list[tuple] = []
    fn_refs: list[tuple] = []
    for r in p.runs:
        b, i_, u = _run_flags(r)
        meta = (b, i_, u, _run_vert_align(r))
        for child in r._element:
            tag = child.tag
            if tag not in _CHAR_STREAM_TAGS:
                if tag == qn("w:footnoteReference"):
                    try:
                        fid = int(child.get(qn("w:id")))
                    except (TypeError, ValueError):
                        continue  # fail-soft: thiếu id thì bỏ qua ref này
                    fn_refs.append((len(chars), fid))
                continue  # rPr & con khác không sinh text (như Run.text)
            if tag == qn("w:t"):
                txt = child.text or ""
                for ch in txt:
                    chars.append((ch, meta))
            elif tag == qn("w:br") or tag == qn("w:cr"):
                chars.append(("\n", meta))
            elif tag == qn("w:noBreakHyphen"):
                chars.append(("-", meta))
            else:  # w:tab / w:ptab
                chars.append(("\t", meta))
    return chars, fn_refs


def build_runs(p: Paragraph) -> list[dict]:
    """Tách paragraph thành runs: gộp text liền nhau cùng metadata (b/i/u +
    vertAlign), tách run tại mỗi the; the chk -> input.chk=true, the thường ->
    input.key + w. <w:footnoteReference> -> run {"role":"footnote-ref",
    "footnoteId":N} giữ đúng vị trí tương đối.

    Chuỗi text đầu ra khớp chính xác "".join(r.text ...) của python-docx
    (hard break \n và tab \t được bảo toàn, KHÔNG collapse).
    """
    chars, fn_refs = _char_stream(p)
    full = "".join(c for c, _meta in chars)
    n = len(chars)
    out: list[dict] = []

    def emit_text(s: int, e: int) -> None:
        while s < e:
            j = s + 1
            while j < e and chars[j][1] == chars[s][1]:
                j += 1
            b, i_, u, va = chars[s][1]
            run = {"text": full[s:j]}
            if b:
                run["b"] = True
            if i_:
                run["i"] = True
            if u:
                run["u"] = True
            if va:
                run["vertAlign"] = va
            out.append(run)
            s = j

    tags = list(TAG_RE.finditer(full))
    fns = sorted(fn_refs)
    ti = fi = 0
    cur = 0
    prev_tag_end = 0
    while True:
        nxt_tag = tags[ti].start() if ti < len(tags) else None
        nxt_fn = fns[fi][0] if fi < len(fns) else None
        if nxt_tag is None and nxt_fn is None:
            emit_text(cur, n)
            break
        # footnote-ref đứng trước tag/text tại cùng vị trí (zero-width)
        if nxt_fn is not None and (nxt_tag is None or nxt_fn <= nxt_tag):
            emit_text(cur, nxt_fn)
            out.append({"role": "footnote-ref", "footnoteId": fns[fi][1]})
            fi += 1
            cur = nxt_fn
            continue
        m = tags[ti]
        emit_text(cur, m.start())
        key = m.group(1)
        # nhãn trước the = khoảng cách từ the trước đến the này (giữ nguyên
        # công thức cũ để output w không đổi với template hiện có)
        label_len = m.start() - prev_tag_end
        w = min(60, max(12, label_len // 2 + 8))
        if key.startswith(CHK_PREFIX):
            out.append({"input": {"key": key, "chk": True}})
        else:
            out.append({"input": {"key": key, "w": w}})
        cur = prev_tag_end = m.end()
        ti += 1
    return out


def para_text_no_tags(p: Paragraph) -> str:
    return TAG_RE.sub("", _para_full_text(p))


def _align_of(p: Paragraph) -> str:
    a = p.alignment
    if a == WD_ALIGN_PARAGRAPH.CENTER:
        return "center"
    if a == WD_ALIGN_PARAGRAPH.RIGHT:
        return "right"
    return "left"


_EMU_PER_PT = 12700


def _len_pt(length) -> float | None:
    """EMU (docx.shared.Length) -> pt làm tròn 1 số thập phân."""
    if length is None:
        return None
    return round(int(length) / _EMU_PER_PT, 1)


def _para_format_dict(p: Paragraph) -> dict | None:
    """Paragraph format khác default mới emit (schema blocks-v3)."""
    pf = p.paragraph_format
    fmt: dict = {}
    for key, val in (
        ("leftIndentPt", pf.left_indent),
        ("rightIndentPt", pf.right_indent),
        ("firstLineIndentPt", pf.first_line_indent),
        ("spaceBeforePt", pf.space_before),
        ("spaceAfterPt", pf.space_after),
    ):
        pt = _len_pt(val)
        if pt:  # None hoặc 0 = mặc định -> bỏ
            fmt[key] = pt
    ls = pf.line_spacing
    if ls is not None:
        if isinstance(ls, Length):  # exact/at-least (twips) -> pt
            pt = _len_pt(ls)
            if pt:
                fmt["lineSpacingPt"] = pt
        elif abs(float(ls) - 1.0) > 1e-9:  # bội dòng, vd 1.15
            fmt["lineSpacing"] = round(float(ls), 2)
    if pf.keep_with_next:
        fmt["keepWithNext"] = True
    return fmt or None


# ---------------------------------------------------------------------------
# Override role tường minh (tools/layout_role_overrides.json)
# ---------------------------------------------------------------------------

OVERRIDES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "layout_role_overrides.json"
)


def load_role_overrides(path=None) -> dict:
    """Đọc override JSON; file rỗng {} = dùng rule thuần.

    Shape hỗ trợ (tất cả optional):
      {"by_index": {FORM_ID: {"<block_index_cấp_thân>": role}},
       "by_folded_prefix": [{"prefix": "...", "role": "...",
                             "forms": ["PLI_M01"]}]}   # bỏ "forms" = mọi form
    """
    p = path or OVERRIDES_PATH
    try:
        with io.open(p, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}  # fail-soft: override hỏng/thiếu không được phá converter


def apply_role_override(overrides, fid, body_para_index, text_folded, role):
    """Áp override tường minh (ưu tiên index theo form, rồi prefix gập dấu)."""
    form_map = (overrides.get("by_index") or {}).get(fid or "", {})
    hit = form_map.get(str(body_para_index)) if form_map else None
    if isinstance(hit, str) and hit in layout_roles.ROLES:
        return hit
    for entry in overrides.get("by_folded_prefix") or []:
        if not isinstance(entry, dict):
            continue
        forms = entry.get("forms")
        if forms and fid not in forms:
            continue
        prefix = entry.get("prefix")
        if isinstance(prefix, str) and text_folded.startswith(prefix):
            r = entry.get("role")
            if isinstance(r, str) and r in layout_roles.ROLES:
                return r
    return role


# ---------------------------------------------------------------------------
# Body paragraph -> block (p hoặc chk)
# ---------------------------------------------------------------------------

def para_block(p: Paragraph, prev_block_ref: dict, ctx: dict | None = None) -> list[dict]:
    """Trả về list block cho 1 paragraph ở thân tài liệu.
    prev_block_ref: {'block': dict|None} để lấy nhãn cho chk đứng một mình.
    ctx (optional): {'form_id', 'body_para_index', 'footnotes', 'overrides'}
    — dùng để gắn role/format/footnotes cho block "p" (schema blocks-v3)."""
    runs = build_runs(p)
    keys = [r["input"]["key"] for r in runs if "input" in r]
    rest = para_text_no_tags(p).strip()

    if not rest and not keys:
        return []  # paragraph rỗng, bỏ

    def is_chk(k: str) -> bool:
        return k.startswith(CHK_PREFIX)

    # Paragraph chỉ gồm the chk + nhãn ngắn (hoặc chk đứng một mình) -> block chk
    if keys and all(is_chk(k) for k in keys) and len(rest) <= 80:
        blocks = []
        if not rest and keys:
            # chk đứng một mình: mượn nhãn từ paragraph văn bản ngắn ngay trước
            pb = prev_block_ref.get("block")
            if (
                pb is not None
                and pb.get("t") == "p"
                and not prev_block_ref.get("consumed")
                and len("".join(r.get("text", "") for r in pb.get("runs", [])).strip()) <= 80
            ):
                label = "".join(
                    r.get("text", "") for r in pb["runs"] if "text" in r
                ).strip()
                blocks.append({"t": "chk", "label": label, "key": keys[0]})
                prev_block_ref["consumed"] = True
                # xoá block p đã bị hút vào nhãn khỏi danh sách đã emit
                emitted = prev_block_ref.get("emitted")
                if emitted is not None and pb in emitted:
                    emitted.remove(pb)
                keys = keys[1:]
                if not keys:
                    return blocks
        # nhiều chk kèm nhãn ngắn trong cùng paragraph
        if len(keys) == 1:
            blocks.append({"t": "chk", "label": rest, "key": keys[0]})
        else:
            # chia nhãn theo đoạn text quanh từng the
            full = _para_full_text(p)
            pos = 0
            segs_before = []
            for m in TAG_RE.finditer(full):
                segs_before.append(full[pos:m.start()].strip())
                pos = m.end()
            for idx, k in enumerate(keys):
                label = segs_before[idx] if idx < len(segs_before) else ""
                if not label and idx > 0:
                    label = rest
                blocks.append({"t": "chk", "label": label, "key": k})
        return blocks

    blk = {"t": "p", "align": _align_of(p), "runs": runs}
    _attach_layout_metadata(blk, p, runs, ctx)
    return [blk]


def _attach_layout_metadata(blk: dict, p: Paragraph, runs: list, ctx: dict | None):
    """Gắn role/format/footnotes (blocks-v3) — chỉ khi khác default."""
    ctx = ctx or {}
    fmt = _para_format_dict(p)
    if fmt:
        blk["format"] = fmt

    raw_full = "".join(r.get("text", "") for r in runs if "text" in r)
    folded = layout_roles.fold(raw_full)
    role = layout_roles.classify_role(folded, fmt, runs)
    role = apply_role_override(
        ctx.get("overrides") or {}, ctx.get("form_id"),
        ctx.get("body_para_index"), folded, role,
    )
    # blocks-v3: MỌI block "p" đều có role tường minh (kể cả "body") để L2
    # không phải regex lại văn bản; block cũ thiếu role vẫn hợp lệ (= body).
    blk["role"] = role

    fn_texts = ctx.get("footnotes")
    if fn_texts:
        ids = sorted(
            {
                r["footnoteId"]
                for r in runs
                if r.get("role") == "footnote-ref" and "footnoteId" in r
            }
        )
        present = {str(i): fn_texts[i] for i in ids if i in fn_texts}
        if present:  # id không tìm thấy text vẫn giữ ở run (fail-soft)
            blk["footnotes"] = present


# ---------------------------------------------------------------------------
# Table -> block table / loop
# ---------------------------------------------------------------------------

def _cell_paragraphs(tc_elem, doc):
    """Các Paragraph trực tiếp của một ô (w:tc)."""
    return [
        Paragraph(child, doc)
        for child in tc_elem.iterchildren()
        if child.tag == qn("w:p")
    ]


def parse_table(tbl: Table):
    """Phân rã bảng thành rows/cells với dedup ô merge, colspan/rowspan.

    Trả về list hàng; mỗi hàng là list ô:
    {"_tc": element, "col": c0, "colspan": n, "rowspan": n, "runs": [...]}
    """
    rows_out = []
    active = {}  # cột -> record ô đang mở dọc (cho rowspan)
    for tr in tbl._tbl.tr_lst:
        row_cells = []
        col = 0
        # Duyệt con trực tiếp w:tc của w:tr (tc_iter): mỗi ô xuất hiện đúng
        # một lần, không cần dedup — và tránh id() trên proxy lxml/python-docx
        # (proxy tạo mới mỗi lần truy cập nên id() không ổn định).
        for tc in tc_iter(tr):
            tc_pr = tc.find(qn("w:tcPr"))
            span = 1
            vmerge_val = None
            if tc_pr is not None:
                gs = tc_pr.find(qn("w:gridSpan"))
                if gs is not None:
                    span = int(gs.get(qn("w:val")))
                vm = tc_pr.find(qn("w:vMerge"))
                if vm is not None:
                    vmerge_val = vm.get(qn("w:val")) or "continue"
            if vmerge_val == "continue":
                rec = None
                for c in range(col, col + span):
                    if c in active:
                        rec = active[c]
                        break
                if rec is not None:
                    rec["rowspan"] += 1
                for c in range(col, col + span):
                    active[c] = rec
                col += span
                continue
            paras = _cell_paragraphs(tc, tbl.part.document)
            runs = []
            for pp in paras:
                runs.extend(build_runs(pp))
            rec = {
                "_tc": tc,
                "col": col,
                "colspan": span,
                "rowspan": 1,
                "runs": runs,
            }
            row_cells.append(rec)
            for c in range(col, col + span):
                active[c] = rec
            col += span
        rows_out.append(row_cells)
    return rows_out


def tc_iter(tr):
    for child in tr.iterchildren():
        if child.tag == qn("w:tc"):
            yield child


def cell_record_to_json(rec: dict) -> dict:
    return {
        "runs": rec["runs"],
        "colspan": rec["colspan"],
        "rowspan": rec["rowspan"],
    }


def cell_full_text(rec: dict) -> str:
    """Text đầy đủ của ô, the thường/chk được dựng lại dạng {key}."""
    parts = []
    for r in rec["runs"]:
        if "text" in r:
            parts.append(r["text"])
        elif "input" in r:
            parts.append("{%s}" % r["input"]["key"])
    return "".join(parts)


def row_visible_text(row_cells: list[dict]) -> str:
    txts = []
    for rec in row_cells:
        txts.append(cell_full_text(rec))
    return ANY_TAG_RE.sub("", "".join(txts)).strip()


def table_block(tbl: Table) -> dict:
    grid = parse_table(tbl)

    # phát hiện hàng khuôn loop: một hàng chứa cả {#ten} và {/ten}
    loop_name = None
    template_idx = None
    for ri, row_cells in enumerate(grid):
        texts = "".join(cell_full_text(rec) for rec in row_cells)
        opens = LOOP_OPEN_RE.findall(texts)
        for name in opens:
            if "{/%s}" % name in texts:
                loop_name, template_idx = name, ri
                break
        if loop_name:
            break

    if loop_name is None:
        return {
            "t": "table",
            "widths": None,
            "rows": [
                {"cells": [cell_record_to_json(rec) for rec in row]}
                for row in grid
            ],
        }

    # bảng loop: headerRows = hàng tiêu đề (không trắng) trước hàng khuôn,
    # blankRows = số hàng trắng giữa header và khuôn (bỏ khỏi rows),
    # hàng khuôn bỏ khỏi rows.
    blank_idx = set()
    last_header = -1
    for ri in range(template_idx):
        if row_visible_text(grid[ri]):
            last_header = ri
        else:
            blank_idx.add(ri)
    header_rows = [ri for ri in range(template_idx) if ri not in blank_idx]

    cols = []
    for rec in grid[template_idx]:
        cell_text = cell_full_text(rec)
        for tag in TAG_RE.findall(cell_text):
            if tag == "_stt":
                # biến engine: STT tự sinh 1-based khi render, không phải
                # cột dữ liệu người dùng -> không vào cols/fields
                continue
            cols.append({"col": rec["col"], "tag": tag})

    rows_json = [
        {"cells": [cell_record_to_json(rec) for rec in row]}
        for ri, row in enumerate(grid)
        if ri != template_idx and ri not in blank_idx
    ]

    return {
        "t": "loop",
        "loop": loop_name,
        "headerRows": header_rows,
        "cols": cols,
        "blankRows": len(blank_idx & set(range(last_header + 1, template_idx))),
        "rows": rows_json,
    }


# ---------------------------------------------------------------------------
# Chuyển 1 file
# ---------------------------------------------------------------------------

def load_footnotes(doc) -> dict:
    """Đọc text chú thích từ word/footnotes.xml (python-docx 1.2.0 không có
    API — truy cập part qua package). Trả về {id: text}; bỏ id <= 0
    (separator/continuation). Fail-soft: thiếu part -> {}."""
    out: dict = {}
    try:
        parts = list(doc.part.package.iter_parts())
    except Exception:  # noqa: BLE001
        return out
    for part in parts:
        name = str(part.partname)
        if not name.endswith("/footnotes.xml") and name != "/word/footnotes.xml":
            continue
        try:
            from lxml import etree

            root = etree.fromstring(part.blob)
            for el in root.iter(qn("w:footnote")):
                raw = el.get(qn("w:id"))
                try:
                    fid = int(raw)
                except (TypeError, ValueError):
                    continue
                if fid < 1:
                    continue
                txt = "".join(t.text or "" for t in el.iter(qn("w:t")))
                txt = txt.strip()
                if txt:
                    out.setdefault(fid, txt)
        except Exception:  # noqa: BLE001
            continue  # part hỏng -> coi như không có footnote text
    return out


def convert_document(
    doc, fid: str, ten_mau: str, overrides: dict | None = None,
    footnotes: dict | None = None,
) -> dict:
    """Chuyển một Document đã mở thành block JSON (không IO file).

    Tách riêng để test dựng fixture DOCX trong temp và gọi trực tiếp.
    """
    blocks: list[dict] = []
    prev_ref = {"block": None, "consumed": False, "emitted": blocks}
    cond_stack: list[str] = []  # flag đang mở theo thứ tự (lồng nhau = AND)
    ctx = {
        "form_id": fid,
        "footnotes": footnotes if footnotes is not None else {},
        "overrides": overrides or {},
        "body_para_index": -1,
    }

    def _attach_cond(b: dict) -> dict:
        if cond_stack:
            b["cond"] = list(cond_stack)
        return b

    for kind, obj in iter_blocks(doc):
        if kind == "p":
            ctx["body_para_index"] += 1
            full = _para_full_text(obj).strip()
            mo = COND_OPEN_FULL_RE.match(full)
            mc = COND_CLOSE_FULL_RE.match(full)
            if mo:
                cond_stack.append(mo.group(1))
                continue
            if mc:
                name = mc.group(1)
                if not cond_stack or cond_stack[-1] != name:
                    raise ValueError(
                        "%s: marker {/%s} sai cặp (đang mở: %s)"
                        % (fid, name, cond_stack))
                cond_stack.pop()
                continue
            new_blocks = para_block(obj, prev_ref, ctx)
            blocks.extend(_attach_cond(b) for b in new_blocks)
            prev_ref["block"] = new_blocks[-1] if new_blocks else prev_ref["block"]
            if not new_blocks:
                # paragraph rỗng: không reset trạng thái consumed
                pass
            else:
                prev_ref["consumed"] = False
        else:
            blk = table_block(obj)
            _attach_cond(blk)
            blocks.append(blk)
            prev_ref["block"] = None
            prev_ref["consumed"] = False

    if cond_stack:
        raise ValueError(
            "%s: marker {?%s} không được đóng trong template" % (fid, cond_stack[-1]))

    return {"id": fid, "ten_mau": ten_mau, "blocks": blocks, "v": SCHEMA_VERSION}


SCHEMA_VERSION = 3


def convert(fid: str, form_maps: dict, overrides: dict | None = None) -> dict:
    path = TEMPLATES_DIR / ("%s.docx" % fid)
    doc = Document(str(path))
    ten_mau = form_maps.get(fid, {}).get("ten_mau", "")
    return convert_document(
        doc, fid, ten_mau,
        overrides=overrides if overrides is not None else load_role_overrides(),
        footnotes=load_footnotes(doc),
    )


# ---------------------------------------------------------------------------
# Tự kiểm định
# ---------------------------------------------------------------------------

def collect_docx_tags(path: Path) -> int:
    """Đếm tổng số the {…} (không tính {#..}/{/..}) từ python-docx trực tiếp.

    The {_stt} bị loại vì đây là biến engine (STT tự sinh khi render) không
    xuất hiện dưới dạng input trong blocks — giữ đối xứng với collect_json_tags.
    Duyệt con trực tiếp w:tc của w:tr thay vì row.cells + dedup id(): proxy
    python-docx tạo mới mỗi lần nên id() không ổn định, có thể bỏ nhầm ô."""
    doc = Document(str(path))
    n = 0
    for kind, obj in iter_blocks(doc):
        if kind == "p":
            n += len(TAG_RE.findall(_para_full_text(obj)))
        else:
            for tr in obj._tbl.tr_lst:
                for tc in tc_iter(tr):
                    for pp in _cell_paragraphs(tc, obj.part.document):
                        n += sum(1 for t in TAG_RE.findall(pp.text)
                                 if t != "_stt")
    return n


def collect_json_tags(data: dict) -> int:
    n = 0
    for b in data["blocks"]:
        if b["t"] in ("p", "table"):
            rows = b.get("rows") if b["t"] == "table" else None
            if rows is not None:
                for row in rows:
                    for cell in row["cells"]:
                        n += sum(1 for r in cell["runs"] if "input" in r)
            else:
                n += sum(1 for r in b["runs"] if "input" in r)
        elif b["t"] == "chk":
            n += 1
        elif b["t"] == "loop":
            n += len(b["cols"])
            for row in b.get("rows", []):
                for cell in row["cells"]:
                    n += sum(1 for r in cell["runs"] if "input" in r)
    return n


ANY_TAG_RE = re.compile(r"\{[/#?]?[A-Za-z_][A-Za-z0-9_.#/?]*\}")


def collect_docx_text(path: Path) -> str:
    """Toàn bộ text của file, đã bỏ mọi the {…}/{#…}/{/…}.
    Duyệt con trực tiếp w:tc (không dùng row.cells + id() — xem
    collect_docx_tags)."""
    doc = Document(str(path))
    parts = []
    for kind, obj in iter_blocks(doc):
        if kind == "p":
            parts.append(ANY_TAG_RE.sub("", obj.text))
        else:
            for tr in obj._tbl.tr_lst:
                for tc in tc_iter(tr):
                    txt = "\n".join(
                        pp.text for pp in _cell_paragraphs(tc, obj.part.document)
                    )
                    parts.append(ANY_TAG_RE.sub("", txt))
    return "".join(parts)


_WS_RE = re.compile(r"\s+")


def collect_json_text(data: dict) -> str:
    parts = []

    def runs_text(runs):
        for r in runs:
            if "text" in r:
                parts.append(r["text"])

    for b in data["blocks"]:
        if b["t"] == "p":
            runs_text(b["runs"])
        elif b["t"] == "chk":
            parts.append(b.get("label", ""))
        elif b["t"] == "table":
            for row in b["rows"]:
                for cell in row["cells"]:
                    runs_text(cell["runs"])
        elif b["t"] == "loop":
            for row in b.get("rows", []):
                for cell in row["cells"]:
                    runs_text(cell["runs"])
    return "".join(parts)


def summarize_tree(data: dict) -> str:
    lines = []
    for i, b in enumerate(data["blocks"]):
        if b["t"] == "p":
            txt = "".join(r.get("text", "") for r in b["runs"])
            ntag = sum(1 for r in b["runs"] if "input" in r)
            head = _WS_RE.sub(" ", txt).strip()[:60]
            lines.append("[%d] p(%s) tags=%d %r" % (i, b["align"], ntag, head))
        elif b["t"] == "chk":
            lines.append("[%d] chk %s label=%r" % (i, b["key"], b["label"][:40]))
        elif b["t"] == "table":
            nr = len(b["rows"])
            nc = len(b["rows"][0]["cells"]) if b["rows"] else 0
            first = ""
            if b["rows"] and b["rows"][0]["cells"]:
                first = _WS_RE.sub(
                    " ",
                    "".join(
                        r.get("text", "") for r in b["rows"][0]["cells"][0]["runs"]
                    ),
                ).strip()[:30]
            lines.append("[%d] table rows=%d cells(r0)=%d %r" % (i, nr, nc, first))
        elif b["t"] == "loop":
            lines.append(
                "[%d] loop %s headerRows=%s blankRows=%d cols=%s rows=%d"
                % (
                    i,
                    b["loop"],
                    b["headerRows"],
                    b["blankRows"],
                    [(c["col"], c["tag"]) for c in b["cols"]],
                    len(b.get("rows", [])),
                )
            )
    return "\n".join(lines)


def self_check(ids: list[str], form_maps: dict, tree_ids: list[str]) -> int:
    errors = []
    # (a) đủ file, json.load OK
    json_files = sorted(OUT_DIR.glob("*.json"))
    loaded = {}
    for jf in json_files:
        try:
            loaded[jf.stem] = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append("(a) %s json hỏng: %r" % (jf.name, exc))
    missing = [i for i in ids if i not in loaded]
    if missing:
        errors.append("(a) thiếu %d file: %s" % (len(missing), missing[:5]))

    # (b) 10 mẫu ngẫu nhiên: tổng số the khớp python-docx
    rng = random.Random(20260824)
    sample = rng.sample(sorted(loaded.keys()), min(10, len(loaded)))
    for fid in sample:
        want = collect_docx_tags(TEMPLATES_DIR / ("%s.docx" % fid))
        got = collect_json_tags(loaded[fid])
        status = "OK" if want == got else "LỆCH"
        print("  (b) %-10s the docx=%-4d json=%-4d %s" % (fid, want, got, status))
        if want != got:
            errors.append("(b) %s: docx=%d json=%d" % (fid, want, got))

    # (c) cây block 3 mẫu đối chiếu mắt
    for fid in tree_ids:
        print("----- cây block %s -----" % fid)
        print(summarize_tree(loaded[fid]))

    # (d) không mất text
    rng2 = random.Random(42)
    sample2 = rng2.sample(sorted(loaded.keys()), min(20, len(loaded)))
    for fid in sample2:
        want = _WS_RE.sub("", collect_docx_text(TEMPLATES_DIR / ("%s.docx" % fid)))
        got = _WS_RE.sub("", collect_json_text(loaded[fid]))
        if want != got:
            errors.append(
                "(d) %s mất text: docx=%d ký tự vs json=%d ký tự"
                % (fid, len(want), len(got))
            )
            print("  (d) %-10s MẤT TEXT (%d vs %d)" % (fid, len(want), len(got)))
        else:
            print("  (d) %-10s text khớp (%d ký tự)" % (fid, len(want)))

    print("-" * 60)
    if errors:
        print("TỰ KIỂM ĐỊNH THẤT BẠI:")
        for e in errors:
            print(" -", e)
        return 1
    print("TỰ KIỂM ĐỊNH: %d file JSON đều hợp lệ." % len(json_files))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    form_maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if "--one" in args:
        fid = args[args.index("--one") + 1]
        data = convert(fid, form_maps)
        out = OUT_DIR / ("%s.json" % fid)
        out.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print("Đã ghi", out)
        return 0

    ids = sorted(form_maps.keys())
    for fid in ids:
        data = convert(fid, form_maps)
        out = OUT_DIR / ("%s.json" % fid)
        out.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    print("Đã chuyển %d template -> %s" % (len(ids), OUT_DIR))

    stats = {}
    total_blocks = 0
    for jf in sorted(OUT_DIR.glob("*.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        cnt = {}
        for b in d["blocks"]:
            cnt[b["t"]] = cnt.get(b["t"], 0) + 1
        stats[jf.stem] = cnt
        total_blocks += len(d["blocks"])
    kinds = ("p", "chk", "table", "loop")
    print("%-10s %6s %5s %7s %6s %7s" % (("file",) + kinds + ("tổng",)))
    for fid in sorted(stats):
        c = stats[fid]
        print(
            "%-10s %6d %5d %7d %6d %7d"
            % ((fid,) + tuple(c.get(k, 0) for k in kinds) + (sum(c.values()),))
        )
    print("Tổng số block mọi mẫu:", total_blocks)

    return self_check(ids, form_maps, ["PLI_M02", "PLI_M06", "PLII_M01"])


if __name__ == "__main__":
    sys.exit(main())
