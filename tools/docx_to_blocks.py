# -*- coding: utf-8 -*-
"""Chuyển mỗi template app/templates/PLI_Mxx.docx thành app/data/blocks/<id>.json.

Template đã gắn the dạng {key} (key chấm được: dn.ten_tieng_viet), {chk_xxx},
và bảng loop có hàng khuôn chứa {#ten} ở ô đầu và {/ten} ở ô cuối cùng hàng,
các ô giữa là {tag_cot}. Biến đặc biệt {_stt} trong hàng khuôn là STT tự sinh
(1-based theo thứ tự dòng dữ liệu, engine render thay khi nhân bản hàng),
không được tính là cột dữ liệu trong cols.

Schema JSON đầu ra:
{
  "id": "PLI_M02",
  "ten_mau": "...",            # lấy từ app/data/form_maps.json
  "blocks": [
    {"t":"p", "align":"left|center|right", "runs":[
        {"text":"..."},
        {"input":{"key":"dn.ten_tieng_viet","w":40}},
        {"input":{"key":"chk_x","chk":true}}     # chk lồng trong paragraph dài
    ]},
    {"t":"chk", "label":"...", "key":"chk_x"},   # paragraph chỉ gồm chk + nhãn ngắn
    {"t":"table", "widths":null, "rows":[
        {"cells":[{"runs":[...], "colspan":1, "rowspan":1}]}
    ]},
    {"t":"loop", "loop":"ds_thanh_vien", "headerRows":[0],
     "cols":[{"col":1,"tag":"ho_ten"}], "blankRows":4, "rows":[...]}
  ]
}

Chạy:
    python -X utf8 tools/docx_to_blocks.py              # chuyển cả 87 file + tự kiểm định
    python -X utf8 tools/docx_to_blocks.py --one PLI_M02  # chuyển 1 file
"""
from __future__ import annotations

import io
import json
import random
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

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


def build_runs(p: Paragraph) -> list[dict]:
    """Tách paragraph thành runs: gộp text liền nhau không chứa the,
    tách run tại mỗi the; the chk -> input.chk=true, the thường -> input.key + w."""
    runs = p.runs
    full = "".join(r.text for r in runs)
    # offset bắt đầu của từng run trong full
    bounds = []
    off = 0
    for r in runs:
        bounds.append(off)
        off += len(r.text)

    def flags_at(pos: int):
        for i in range(len(bounds) - 1, -1, -1):
            if bounds[i] <= pos:
                return _run_flags(runs[i])
        return (False, False, False)

    out: list[dict] = []
    plain_buf: list[str] = []  # các đoạn text thường liền nhau

    def flush_plain():
        if plain_buf:
            b, i, u = flags_at(plain_start[0])
            run = {"text": "".join(plain_buf)}
            if b:
                run["b"] = True
            if i:
                run["i"] = True
            if u:
                run["u"] = True
            out.append(run)
            plain_buf.clear()

    plain_start = [0]
    prev_end = 0
    for m in TAG_RE.finditer(full):
        seg = full[prev_end:m.start()]
        if seg:
            plain_start[0] = prev_end
            plain_buf.append(seg)
        flush_plain()
        key = m.group(1)
        # nhãn trước the = đoạn text từ sau the trước đến the này
        label_len = m.start() - prev_end
        w = min(60, max(12, label_len // 2 + 8))
        if key.startswith(CHK_PREFIX):
            out.append({"input": {"key": key, "chk": True}})
        else:
            out.append({"input": {"key": key, "w": w}})
        prev_end = m.end()
    seg = full[prev_end:]
    if seg:
        plain_start[0] = prev_end
        plain_buf.append(seg)
    flush_plain()
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


# ---------------------------------------------------------------------------
# Body paragraph -> block (p hoặc chk)
# ---------------------------------------------------------------------------

def para_block(p: Paragraph, prev_block_ref: dict) -> list[dict]:
    """Trả về list block cho 1 paragraph ở thân tài liệu.
    prev_block_ref: {'block': dict|None} để lấy nhãn cho chk đứng một mình."""
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

    return [{"t": "p", "align": _align_of(p), "runs": runs}]


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

def convert(fid: str, form_maps: dict) -> dict:
    path = TEMPLATES_DIR / ("%s.docx" % fid)
    doc = Document(str(path))
    ten_mau = form_maps.get(fid, {}).get("ten_mau", "")

    blocks: list[dict] = []
    prev_ref = {"block": None, "consumed": False, "emitted": blocks}
    cond_stack: list[str] = []  # flag đang mở theo thứ tự (lồng nhau = AND)

    def _attach_cond(b: dict) -> dict:
        if cond_stack:
            b["cond"] = list(cond_stack)
        return b

    for kind, obj in iter_blocks(doc):
        if kind == "p":
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
            new_blocks = para_block(obj, prev_ref)
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

    return {"id": fid, "ten_mau": ten_mau, "blocks": blocks}


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
