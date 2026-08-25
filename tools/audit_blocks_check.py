# -*- coding: utf-8 -*-
"""KIỂM TRA ĐỘC LẬP output của tools/docx_to_blocks.py (app/data/blocks/*.json).

Viết riêng cho đợt audit — KHÔNG tái dùng các hàm tự-kiểm định của
tools/docx_to_blocks.py. Nguồn sự thật đối chiếu:
  - app/templates/<id>.docx  (template gốc gắn the {key}/{chk_x}/{#loop})
  - app/data/form_maps.json  (fields + dynamic_tables)
  - cách duyệt chuẩn theo tools/dump_structure.py (body theo thứ tự p/tbl,
    ô merge dedup theo phần tử w:tc)

6 mục kiểm tra:
  1. Đủ đuôi: 87 file tồn tại, json.load OK, id khớp tên file, text khớp template.
  2. The đầy đủ: set key trong blocks vs the trong template vs fields form_maps.
  3. Loop đúng: cols/headerRows/blankRows đối chiếu dynamic_tables.
  4. Chk hợp lệ: key có trong form_maps type=chk; nhãn suy ra từ template đúng.
  5. Schema frontend: chỉ chấp nhận trường/liểu kiểu đã định nghĩa.
  6. Render thử nghiệm: 5 mẫu render bằng tools/docx_render.py, không sót the.

Chạy:
    python -X utf8 tools/audit_blocks_check.py
Exit code 0 nếu mọi mục PASS, 1 nếu có FAIL.
Finding mức BỎ-QUA-ĐƯỢC chỉ là ghi chú tham khảo, không làm FAIL gate.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
TEMPLATES_DIR = APP_DIR / "templates"
BLOCKS_DIR = APP_DIR / "data" / "blocks"
FORM_MAPS_PATH = APP_DIR / "data" / "form_maps.json"
RENDER_OUT_DIR = ROOT / "generated_ho_so" / "_audit_blocks_render"

# ---------------------------------------------------------------------------
# Regex & hằng số (định nghĩa lại độc lập, không import từ docx_to_blocks)
# ---------------------------------------------------------------------------

# The biến thường: {key} hoặc {a.b.c}
TAG_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")
# Mọi dạng the: {key} / {#loop} / {/loop} / {_stt} (biến engine gạch dưới đầu)
ANY_TAG_RE = re.compile(r"\{[/#]?[A-Za-z_][A-Za-z0-9_.#/]*\}")
# Mọi khoảng trắng (kể cả \n, \t, NBSP) — dùng để chuẩn hóa so text
WS_RE = re.compile(r"\s+")
CHK_PREFIX = "chk"

SEV_CHAN = "CHẶN-FRONTEND"
SEV_MY = "THẤM-MỸ"
SEV_NH = "BỎ-QUA-ĐƯỢC"

FINDINGS: list[tuple[str, str, str, str]] = []  # (mục, file, mô tả, mức)


def add(section: str, fid: str, desc: str, sev: str) -> None:
    FINDINGS.append((section, fid, desc, sev))


# ---------------------------------------------------------------------------
# Đọc template theo cách duyệt chuẩn (dump_structure.py)
# ---------------------------------------------------------------------------


def iter_body(doc):
    """Duyệt body theo thứ tự: ('p', Paragraph) hoặc ('tbl', Table)."""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", Table(child, doc))


def tc_iter(tr):
    """Duyệt con TRỰC TIẾP w:tc của w:tr. Ô merge (gridSpan/vMerge) là các
    phần tử XML riêng biệt nên cách duyệt này không bao giờ gặp ô nhân bản —
    không cần dedup, và đặc biệt KHÔNG dùng id() trên proxy lxml/python-docx:
    proxy được tạo mới mỗi lần truy cập nên id() không ổn định (CPython tái
    sử dụng địa chỉ sau khi GC) dẫn tới dedup sai, bỏ nhầm ô."""
    for child in tr.iterchildren():
        if child.tag == qn("w:tc"):
            yield child


def _cell_texts(tbl: Table) -> list[str]:
    """Text từng ô của bảng, duyệt tr theo thứ tự hàng; ô merge lặp (vMerge
    continue) là phần tử XML riêng nhưng text rỗng nên không ảnh hưởng."""
    out = []
    for tr in tbl._tbl.tr_lst:
        for tc in tc_iter(tr):
            parts = []
            for p_el in tc.iterchildren():
                if child_tag(p_el) == "p":
                    parts.append(Paragraph(p_el, tbl.part.document).text)
            out.append("".join(parts))
    return out


def child_tag(el):
    return el.tag.split("}", 1)[-1]


def template_text_stripped(path: Path) -> str:
    """Toàn bộ text của template, đã bỏ mọi the; dùng cho mục 1b."""
    doc = Document(str(path))
    parts = []
    for kind, obj in iter_body(doc):
        if kind == "p":
            parts.append(ANY_TAG_RE.sub("", obj.text))
        else:
            parts.extend(ANY_TAG_RE.sub("", t) for t in _cell_texts(obj))
    return WS_RE.sub("", "".join(parts))


def template_tag_set(path: Path) -> set:
    """Tập mọi the biến thường {key} xuất hiện trong template (mục 2)."""
    doc = Document(str(path))
    tags: set = set()
    for kind, obj in iter_body(doc):
        if kind == "p":
            tags.update(TAG_RE.findall(obj.text))
        else:
            for t in _cell_texts(obj):
                tags.update(TAG_RE.findall(t))
    return tags


def template_paras(path: Path) -> list:
    """Các paragraph cấp thân tài liệu theo thứ tự; bảng được đánh dấu None
    (ngăn việc mượn nhãn chk băng qua bảng)."""
    doc = Document(str(path))
    seq = []
    for kind, obj in iter_body(doc):
        seq.append(obj if kind == "p" else None)
    return seq


# ---------------------------------------------------------------------------
# Đọc blocks JSON
# ---------------------------------------------------------------------------


def walk_run_containers(data: dict):
    """Yield mọi list runs trong blocks: p, ô của table, ô của loop rows."""
    for b in data["blocks"]:
        t = b["t"]
        if t == "p":
            yield b["runs"]
        elif t in ("table", "loop"):
            for row in b.get("rows", []):
                for cell in row["cells"]:
                    yield cell["runs"]


def json_keys(data: dict) -> set:
    """Tập key người dùng nhập: mọi input.key + key của block chk."""
    keys: set = set()
    for runs in walk_run_containers(data):
        for r in runs:
            if "input" in r:
                keys.add(r["input"]["key"])
    for b in data["blocks"]:
        if b["t"] == "chk":
            keys.add(b["key"])
    return keys


def json_text(data: dict) -> str:
    """Nối toàn bộ text hiển thị trong blocks THEO THỨ TỰ block: nhãn của
    block chk đứng đúng vị trí block của nó trong tài liệu (không dồn về cuối
    như bản cũ — điều đó làm mục so text báo lệch thứ tự giả)."""
    parts = []
    for b in data["blocks"]:
        t = b["t"]
        if t == "p":
            for r in b["runs"]:
                if "text" in r:
                    parts.append(r["text"])
        elif t == "chk":
            parts.append(b.get("label", ""))
        elif t in ("table", "loop"):
            for row in b.get("rows", []):
                for cell in row["cells"]:
                    for r in cell["runs"]:
                        if "text" in r:
                            parts.append(r["text"])
    return WS_RE.sub("", "".join(parts))


def json_chk_blocks(data: dict) -> list:
    """[(key, label)] theo thứ tự tài liệu — chỉ block chk, không gồm chk lồng."""
    return [(b["key"], b.get("label", "")) for b in data["blocks"] if b["t"] == "chk"]


def json_nested_chk_keys(data: dict) -> set:
    """Key chk lồng trong runs (paragraph dài / ô bảng)."""
    keys: set = set()
    for runs in walk_run_containers(data):
        for r in runs:
            if "input" in r and r["input"].get("chk"):
                keys.add(r["input"]["key"])
    return keys


def json_table_like_blocks(data: dict) -> list:
    """Các block t in ('table','loop') theo thứ tự — dùng để map table_index."""
    return [b for b in data["blocks"] if b["t"] in ("table", "loop")]


# ---------------------------------------------------------------------------
# MỤC 1 — Đủ đuôi + text khớp template
# ---------------------------------------------------------------------------


def audit_section1(form_maps: dict, loaded: dict) -> None:
    ids = sorted(form_maps.keys())
    # (a) mỗi mẫu có file blocks, load OK, id khớp
    for fid in ids:
        jf = BLOCKS_DIR / ("%s.json" % fid)
        if not jf.exists():
            add("1", fid, "thiếu file blocks %s" % jf.name, SEV_CHAN)
            continue
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            add("1", fid, "json.load thất bại: %r" % (exc,), SEV_CHAN)
            continue
        loaded[fid] = data
        if data.get("id") != fid:
            add(
                "1",
                fid,
                'trường "id"=%r khác tên file' % (data.get("id"),),
                SEV_CHAN,
            )
    # file thừa không ánh xạ form_maps
    for jf in sorted(BLOCKS_DIR.glob("*.json")):
        if jf.stem not in form_maps:
            add("1", jf.stem, "file blocks thừa, không có trong form_maps", SEV_NH)

    # (b) nối text blocks (bỏ input) == text template (bỏ the), bỏ hết whitespace
    for fid in sorted(loaded):
        want = template_text_stripped(TEMPLATES_DIR / ("%s.docx" % fid))
        got = json_text(loaded[fid])
        if want != got:
            # tìm vị trí lệch đầu tiên để báo cáo cụ thể
            i = 0
            while i < min(len(want), len(got)) and want[i] == got[i]:
                i += 1
            ctx_w = want[max(0, i - 40) : i + 40]
            ctx_g = got[max(0, i - 40) : i + 40]
            add(
                "1",
                fid,
                "LỆCH TEXT: template=%d ký tự vs blocks=%d ký tự; "
                "lệch đầu tiên tại offset %d; template: …%r… vs blocks: …%r…"
                % (len(want), len(got), i, ctx_w, ctx_g),
                SEV_CHAN,
            )


# ---------------------------------------------------------------------------
# MỤC 2 — The đầy đủ (fields form_maps phải xuất hiện trong blocks)
# ---------------------------------------------------------------------------


def audit_section2(form_maps: dict, loaded: dict) -> None:
    for fid in sorted(loaded):
        data = loaded[fid]
        fmap = form_maps[fid]
        fm_fields = {f["key"] for f in fmap.get("fields", [])}
        bkeys = json_keys(data)
        ttags = template_tag_set(TEMPLATES_DIR / ("%s.docx" % fid))

        missing_fm = sorted(fm_fields - bkeys)
        # các key dạng "<loop>.<tag>" trùng với cột của dynamic_tables là
        # metadata của bảng lặp — người dùng nhập qua cơ chế bảng loop
        # (render.js sinh input theo cols), không phải ô nhập bị mất.
        dt_map = {}
        for t in fmap.get("dynamic_tables") or []:
            for c in t["columns"]:
                dt_map.setdefault(t["loop"], set()).add(c["tag"])
        for k in missing_fm:
            parts = k.split(".", 1)
            if len(parts) == 2 and parts[1] in dt_map.get(parts[0], set()):
                add(
                    "2",
                    fid,
                    'field %r của form_maps không có trong blocks — nhưng đây là '
                    "metadata trùng của cột loop %s.%s (ô nhập do bảng lặp đảm nhiệm, "
                    "lưu ý: app_tk chế độ danh-sách-trường vẫn hiện ô rời cho key này)"
                    % (k, parts[0], parts[1]),
                    SEV_NH,
                )
            else:
                add(
                    "2",
                    fid,
                    'field %r của form_maps KHÔNG xuất hiện trong blocks '
                    "(frontend sẽ thiếu ô nhập)" % k,
                    SEV_CHAN,
                )

        ghost = sorted(bkeys - ttags)
        for k in ghost:
            add(
                "2",
                fid,
                "key %r có trong blocks nhưng KHÔNG có the tương ứng trong template" % k,
                SEV_CHAN,
            )

        # thông tin tham khảo: field có trong template mà blocks cũng có — OK


# ---------------------------------------------------------------------------
# MỤC 3 — Loop đúng đối chiếu dynamic_tables
# ---------------------------------------------------------------------------


def table_row_cells(path: Path, table_index: int, row_index: int) -> list[str]:
    """Text từng ô (giữ cả ô rỗng, đúng vị trí) của hàng row_index trong bảng
    thứ table_index. Duyệt con trực tiếp w:tc của w:tr qua tc_iter nên không
    bao giờ bỏ sót ô do dedup id() sai (lỗi cũ làm rơi ô cuối của header)."""
    doc = Document(str(path))
    tables = [obj for kind, obj in iter_body(doc) if kind == "tbl"]
    if table_index >= len(tables):
        return ["<không có bảng %d>" % table_index]
    tbl = tables[table_index]
    trs = tbl._tbl.tr_lst
    if row_index >= len(trs):
        return ["<không có hàng %d>" % row_index]
    out = []
    for tc in tc_iter(trs[row_index]):
        txt = " ".join(
            Paragraph(p_el, tbl.part.document).text
            for p_el in tc.iterchildren()
            if child_tag(p_el) == "p"
        ).strip()
        out.append(txt)
    return out


def table_row_text(path: Path, table_index: int, row_index: int) -> str:
    """Bản đẹp để in báo cáo: các ô nối bằng ' | ', bỏ ô rỗng. KHÔNG dùng
    cho so khớp tự động — dấu '|' là nhân tạo, template không hề có."""
    return " | ".join(t for t in table_row_cells(path, table_index, row_index) if t)


def audit_section3(form_maps: dict, loaded: dict) -> None:
    total_loop_blocks = 0
    loop_ids = set()
    for fid in sorted(loaded):
        dts = form_maps[fid].get("dynamic_tables") or []
        tbl_blocks = json_table_like_blocks(loaded[fid])
        loops_here = [b for b in loaded[fid]["blocks"] if b["t"] == "loop"]
        total_loop_blocks += len(loops_here)

        if not dts:
            if loops_here:
                add(
                    "3",
                    fid,
                    "có %d block loop nhưng form_maps không khai báo dynamic_tables"
                    % len(loops_here),
                    SEV_CHAN,
                )
            continue

        for dt in dts:
            ti = dt["table_index"]
            loop_ids.add((fid, dt["id"]))
            if ti >= len(tbl_blocks):
                add(
                    "3",
                    fid,
                    "dynamic_tables[%s] table_index=%d vượt số bảng trong blocks (%d)"
                    % (dt["id"], ti, len(tbl_blocks)),
                    SEV_CHAN,
                )
                continue
            blk = tbl_blocks[ti]
            if blk["t"] != "loop":
                add(
                    "3",
                    fid,
                    "dynamic_tables[%s] table_index=%d trỏ tới block t=%s, kỳ vọng 'loop'"
                    % (dt["id"], ti, blk["t"]),
                    SEV_CHAN,
                )
                continue

            # tên loop
            if blk.get("loop") != dt["loop"]:
                add(
                    "3",
                    fid,
                    "tên loop blocks=%r vs form_maps=%r"
                    % (blk.get("loop"), dt["loop"]),
                    SEV_CHAN,
                )

            # cột: (col, tag) phải khớp tập và không trùng
            got_cols = sorted((c["col"], c["tag"]) for c in blk.get("cols", []))
            want_cols = sorted((c["col"], c["tag"]) for c in dt["columns"])
            got_tag_list = [c["tag"] for c in blk.get("cols", [])]
            if len(set(got_tag_list)) != len(got_tag_list):
                add(
                    "3",
                    fid,
                    "cols có tag trùng nhau: %s" % got_tag_list,
                    SEV_CHAN,
                )
            if got_cols != want_cols:
                only_b = [x for x in got_cols if x not in want_cols]
                only_f = [x for x in want_cols if x not in got_cols]
                add(
                    "3",
                    fid,
                    "cols[].(col,tag) LỆCH: blocks thừa=%s thiếu=%s (blocks=%s / form_maps=%s)"
                    % (only_b, only_f, got_cols, want_cols),
                    SEV_CHAN,
                )

            # Hợp đồng render.js: headerRows là CHỈ SỐ TRONG mảng rows của
            # block loop (hàng tiêu đề được chép vào rows); các hàng trong rows
            # không nằm trong headerRows sẽ KHÔNG được web render (renderLoop
            # chỉ sinh <thead> từ headerRows + hàng dữ liệu động từ cols).
            rows_json = blk.get("rows", [])
            hdr_list = blk.get("headerRows", [])
            hr_grid = dt["header_row"]

            # text hàng tiêu đề trong template để đối chiếu + in báo cáo.
            # So khớp: NỐI text các ô (bỏ whitespace) — cùng quy tắc với
            # blocks; dấu ' | ' chỉ dùng khi in cho người đọc.
            hdr_cells = table_row_cells(
                TEMPLATES_DIR / ("%s.docx" % fid), ti, hr_grid
            )
            want_hdr_txt = WS_RE.sub("", "".join(hdr_cells))
            print(
                "    [%s/%s] hàng tiêu đề template (hàng %d): %s"
                % (fid, dt["id"], hr_grid,
                   table_row_text(
                       TEMPLATES_DIR / ("%s.docx" % fid), ti, hr_grid)[:120])
            )

            if not hdr_list:
                add("3", fid, "loop %s: headerRows rỗng" % dt["id"], SEV_CHAN)
            for ri in hdr_list:
                if not isinstance(ri, int) or ri < 0 or ri >= len(rows_json):
                    add(
                        "3",
                        fid,
                        "loop %s: headerRows=%s chứa chỉ mục ngoài phạm vi rows "
                        "(len(rows)=%d)" % (dt["id"], hdr_list, len(rows_json)),
                        SEV_CHAN,
                    )
                    continue
                got_txt = WS_RE.sub(
                    "",
                    "".join(
                        rr.get("text", "")
                        for cell in rows_json[ri]["cells"]
                        for rr in cell["runs"]
                    ),
                )
                if got_txt != want_hdr_txt:
                    add(
                        "3",
                        fid,
                        "loop %s: rows[%d] (do headerRows trỏ) KHÔNG khớp hàng tiêu "
                        "đề template: template=%r vs blocks=%r"
                        % (dt["id"], ri, want_hdr_txt[:80], got_txt[:80]),
                        SEV_CHAN,
                    )
            # hàng tĩnh nằm ngoài headerRows: render.js sẽ bỏ sót hoàn toàn
            for ri in range(len(rows_json)):
                if ri not in hdr_list:
                    txt = "".join(
                        rr.get("text", "")
                        for cell in rows_json[ri]["cells"]
                        for rr in cell["runs"]
                    ).strip()
                    if txt:
                        add(
                            "3",
                            fid,
                            "loop %s: rows[%d] là hàng có nội dung (%r…) nhưng không "
                            "được headerRows trỏ — render.js sẽ KHÔNG hiển thị hàng này"
                            % (dt["id"], ri, txt[:60]),
                            SEV_MY,
                        )

            # blankRows hợp lý
            br = blk.get("blankRows", -1)
            if not isinstance(br, int) or br < 0:
                add("3", fid, "blankRows=%r âm/không hợp lệ" % (br,), SEV_CHAN)

            # bảo toàn số hàng: static rows giữ trong rows + blank + 1 hàng khuôn
            # = tổng số hàng w:tr của bảng template
            doc = Document(str(TEMPLATES_DIR / ("%s.docx" % fid)))
            tables = [obj for kind, obj in iter_body(doc) if kind == "tbl"]
            if ti < len(tables):
                n_tr = len(tables[ti]._tbl.tr_lst)
                expect_total = len(rows_json) + br + 1
                if expect_total != n_tr:
                    add(
                        "3",
                        fid,
                        "bảng %d: rows(%d)+blank(%d)+hàng khuôn(1)=%d "
                        "≠ số hàng template=%d — có hàng bị rơi"
                        % (
                            ti,
                            len(rows_json),
                            br,
                            expect_total,
                            n_tr,
                        ),
                        SEV_CHAN,
                    )

    # Kỳ vọng 9: 8 loop cũ (PLI_M06..M11, PLII_M01×2) + ds_nganh PLI_M02
    # (PLAN PHASE 3 — bảng ngành nghề thật dựng lại trong template).
    if total_loop_blocks != 9:
        add(
            "3",
            "*",
            "tổng số block loop=%d, kỳ vọng 9 "
            "(PLI_M06..11, PLII_M01×2, PLI_M02 ds_nganh)"
            % total_loop_blocks,
            SEV_CHAN,
        )


# ---------------------------------------------------------------------------
# MỤC 4 — Chk hợp lệ: key thuộc form_maps type=chk; nhãn suy luận từ template
# ---------------------------------------------------------------------------


def _seg_labels_multi(full: str, chk_keys: list) -> list:
    """Nhãn kỳ vọng khi 1 paragraph chứa nhiều the chk: đoạn text ngay trước
    từng the (strip); đoạn rỗng thì dùng text đuôi của paragraph."""
    pos = 0
    segs = []
    for m in TAG_RE.finditer(full):
        segs.append(full[pos : m.start()].strip())
        pos = m.end()
    rest = ANY_TAG_RE.sub("", full).strip()
    out = []
    for idx, k in enumerate(chk_keys):
        lab = segs[idx] if idx < len(segs) else ""
        if not lab and idx > 0:
            lab = rest
        out.append((k, lab))
    return out


def expected_chk_list(path: Path) -> list:
    """Dựng danh sách (key, nhãn) chk-block kỳ vọng, suy ra thẳng từ template.

    Quy tắc nguồn sự thật:
      - paragraph chỉ chứa the chk (không the thường) và phần chữ ≤80 ký tự
        mới trở thành block chk; còn lại chk là input lồng trong block p.
      - 1 chk + có chữ: nhãn = phần chữ đó.
      - 1 chk không chữ ("chk đứng một mình"): mượn nhãn từ paragraph văn bản
        gần nhất phía trước (không băng qua bảng, paragraph đó không chứa the
        nào và ≤80 ký tự).
      - nhiều chk trong 1 paragraph: nhãn = đoạn chữ ngay trước từng the,
        rỗng thì lấy phần chữ đuôi paragraph.
    """
    seq = template_paras(path)
    expected: list = []
    last_text_para: str | None = None  # paragraph text thuần gần nhất (reset qua bảng)
    for obj in seq:
        if obj is None:  # bảng: ngắt khả năng mượn nhãn
            last_text_para = None
            continue
        full = obj.text
        keys = TAG_RE.findall(full)
        chk_keys = [k for k in keys if k.startswith(CHK_PREFIX)]
        other_keys = [k for k in keys if not k.startswith(CHK_PREFIX)]
        rest = ANY_TAG_RE.sub("", full).strip()
        if not chk_keys or other_keys or len(rest) > 80:
            # không phải block chk; cập nhật ứng viên mượn nhãn nếu là text thuần
            if not keys and rest:
                last_text_para = rest
            continue
        if len(chk_keys) == 1:
            if rest:
                expected.append((chk_keys[0], rest))
            else:
                label = ""
                if (
                    last_text_para is not None
                    and len(last_text_para) <= 80
                ):
                    label = last_text_para
                expected.append((chk_keys[0], label))
            # sau khi dùng làm nhãn mượn thì không tái sử dụng
            if not rest:
                last_text_para = None
        else:
            expected.extend(_seg_labels_multi(full, chk_keys))
    return expected


def audit_section4(form_maps: dict, loaded: dict) -> None:
    n_chk_blocks = 0
    n_nested = 0
    for fid in sorted(loaded):
        data = loaded[fid]
        fmap = form_maps[fid]
        chk_fields = {
            f["key"] for f in fmap.get("fields", []) if f.get("type") == "chk"
        }
        all_fields = {f["key"] for f in fmap.get("fields", [])}

        cb = json_chk_blocks(data)
        n_chk_blocks += len(cb)
        nested = json_nested_chk_keys(data)
        n_nested += len(nested)

        # (a) mọi key chk (block + lồng) phải là field type=chk trong form_maps
        for k, _lab in cb:
            if k not in all_fields:
                add("4", fid, "chk key %r không có trong form_maps.fields" % k, SEV_CHAN)
            elif k not in chk_fields:
                add(
                    "4",
                    fid,
                    "chk key %r có trong form_maps nhưng type≠chk (%r)"
                    % (k, next(f.get("type") for f in fmap["fields"] if f["key"] == k)),
                    SEV_CHAN,
                )
        for k in sorted(nested):
            if k not in chk_fields:
                add(
                    "4",
                    fid,
                    "chk lồng (trong runs) key %r không thuộc fields type=chk" % k,
                    SEV_CHAN,
                )

        # (b) đối chiếu toàn bộ danh sách (key, nhãn) với suy luận từ template
        exp = expected_chk_list(TEMPLATES_DIR / ("%s.docx" % fid))
        if exp != cb:
            exp_map = {}
            for k, l in exp:
                exp_map.setdefault(k, []).append(l)
            got_map = {}
            for k, l in cb:
                got_map.setdefault(k, []).append(l)
            for k in sorted(set(exp_map) | set(got_map)):
                le, lg = exp_map.get(k, []), got_map.get(k, [])
                if le != lg:
                    add(
                        "4",
                        fid,
                        "nhãn chk %r LỆCH: kỳ vọng từ template=%r, blocks=%r"
                        % (k, le, lg),
                        SEV_MY,
                    )
            # sai thứ tự/số lượng dù nhãn từng key giống nhau
            if [k for k, _ in exp] != [k for k, _ in cb]:
                add(
                    "4",
                    fid,
                    "thứ tự/số lượng block chk khác suy luận từ template: "
                    "template=%s blocks=%s"
                    % ([k for k, _ in exp], [k for k, _ in cb]),
                    SEV_CHAN,
                )
    print(
        "    tổng: %d block chk, %d key chk lồng trong runs" % (n_chk_blocks, n_nested)
    )


# ---------------------------------------------------------------------------
# MỤC 5 — Schema frontend
# ---------------------------------------------------------------------------

ALLOWED_TOP_KEYS = {"id", "ten_mau", "blocks"}
ALLOWED_BLOCK_KEYS = {
    "p": {"t", "align", "runs"},
    "chk": {"t", "key", "label"},
    "table": {"t", "widths", "rows"},
    "loop": {"t", "loop", "headerRows", "cols", "blankRows", "rows"},
}
ALLOWED_RUN_KEYS_TEXT = {"text", "b", "i", "u"}
ALLOWED_COL_KEYS = {"col", "tag"}
VALID_ALIGN = {"left", "center", "right"}
ALLOWED_NAMES = (
    "text/b/i/u/input/colspan/rowspan/label/key/w/loop/headerRows/cols/"
    "blankRows/rows/cells/widths/t/align/id/ten_mau"
)


def _check_runs(section, fid, where, runs, errs):
    for ri, r in enumerate(runs):
        if not isinstance(r, dict):
            errs.append("%s run#%d: không phải dict: %r" % (where, ri, r))
            continue
        bad = set(r) - ALLOWED_RUN_KEYS_TEXT - {"input"}
        if bad:
            errs.append(
                "%s run#%d có trường lạ %s (chỉ cho phép: %s)"
                % (where, ri, sorted(bad), ALLOWED_NAMES)
            )
        if "input" in r:
            inp = r["input"]
            if not isinstance(inp, dict):
                errs.append("%s run#%d input không phải dict" % (where, ri))
                continue
            if not isinstance(inp.get("key"), str) or not inp["key"].strip():
                errs.append("%s run#%d input.key rỗng/thiếu: %r" % (where, ri, inp))
            extra = set(inp) - {"key", "w", "chk"}
            if extra:
                errs.append(
                    "%s run#%d input có trường lạ %s" % (where, ri, sorted(extra))
                )
            if "w" in inp and (not isinstance(inp["w"], int) or inp["w"] <= 0):
                errs.append("%s run#%d input.w=%r không hợp lệ" % (where, ri, inp["w"]))
            if "chk" in inp and inp["chk"] is not True:
                errs.append(
                    "%s run#%d input.chk=%r chỉ được true" % (where, ri, inp["chk"])
                )
        elif "text" not in r:
            errs.append(
                "%s run#%d không phải {'text'} lẫn {'input'}: %r" % (where, ri, r)
            )


def audit_section5(loaded: dict) -> None:
    for fid in sorted(loaded):
        data = loaded[fid]
        errs: list = []
        bad_top = set(data) - ALLOWED_TOP_KEYS
        if bad_top:
            errs.append("top-level có trường lạ: %s" % sorted(bad_top))
        for bi, b in enumerate(data["blocks"]):
            t = b.get("t")
            if t not in ALLOWED_BLOCK_KEYS:
                errs.append("block#%d t lạ: %r" % (bi, t))
                continue
            bad = set(b) - ALLOWED_BLOCK_KEYS[t]
            if bad:
                errs.append(
                    "block#%d (t=%s) có trường lạ %s (chỉ cho phép: %s)"
                    % (bi, t, sorted(bad), ALLOWED_NAMES)
                )
            if t == "p":
                if b.get("align") not in VALID_ALIGN:
                    errs.append("block#%d align lạ: %r" % (bi, b.get("align")))
                _check_runs(5, fid, "p#%d" % bi, b.get("runs", []), errs)
            elif t == "table":
                for rowi, row in enumerate(b.get("rows", [])):
                    for ci, cell in enumerate(row["cells"]):
                        for span in ("colspan", "rowspan"):
                            v = cell.get(span, 1)
                            if not isinstance(v, int) or v < 1:
                                errs.append(
                                    "table block#%d r%d c%d %s=%r <1"
                                    % (bi, rowi, ci, span, v)
                                )
                        badc = set(cell) - {"runs", "colspan", "rowspan"}
                        if badc:
                            errs.append(
                                "table block#%d r%d c%d ô có trường lạ %s"
                                % (bi, rowi, ci, sorted(badc))
                            )
                        _check_runs(
                            5, fid, "table#%d r%d c%d" % (bi, rowi, ci),
                            cell.get("runs", []), errs,
                        )
            elif t == "loop":
                hr = b.get("headerRows")
                if (
                    not isinstance(hr, list)
                    or not hr
                    or not all(isinstance(x, int) and x >= 0 for x in hr)
                ):
                    errs.append("loop block#%d headerRows lạ: %r" % (bi, hr))
                for c in b.get("cols", []):
                    badc = set(c) - ALLOWED_COL_KEYS
                    if badc:
                        errs.append(
                            "loop block#%d cols có trường lạ %s" % (bi, sorted(badc))
                        )
                    if not isinstance(c.get("tag"), str) or not c["tag"]:
                        errs.append("loop block#%d cols tag rỗng: %r" % (bi, c))
                if not isinstance(b.get("blankRows"), int) or b["blankRows"] < 0:
                    errs.append(
                        "loop block#%d blankRows lạ: %r" % (bi, b.get("blankRows"))
                    )
                for rowi, row in enumerate(b.get("rows", [])):
                    for ci, cell in enumerate(row["cells"]):
                        _check_runs(
                            5, fid, "loop#%d r%d c%d" % (bi, rowi, ci),
                            cell.get("runs", []), errs,
                        )
        for e in errs[:20]:
            add("5", fid, e, SEV_CHAN)
        if len(errs) > 20:
            add("5", fid, "… và %d lỗi schema nữa" % (len(errs) - 20), SEV_CHAN)


# ---------------------------------------------------------------------------
# MỤC 6 — Render thử nghiệm bằng tools/docx_render.py
# ---------------------------------------------------------------------------

RENDER_IDS = ["PLI_M02", "PLI_M06", "PLI_M17", "PLII_M01", "PLI_M30"]


def audit_section6(form_maps: dict) -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import docx_render  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        add("6", "*", "không import được tools/docx_render.py: %r" % (exc,), SEV_CHAN)
        return

    RENDER_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for fid in RENDER_IDS:
        if fid not in form_maps:
            add("6", fid, "không có trong form_maps, bỏ qua render", SEV_CHAN)
            continue
        fmap = form_maps[fid]
        tpath = APP_DIR / fmap["template"]
        out_path = RENDER_OUT_DIR / ("%s.docx" % fid)
        try:
            data = docx_render.dummy_data_from_map(fmap)
            docx_render.write_rendered(tpath, data, out_path)
            ok, msg = docx_render.check_output(out_path)
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, "exception khi render: %r" % (exc,)
        print("    render %-10s -> %s (%s)" % (fid, "OK" if ok else "FAIL", msg))
        if not ok:
            add("6", fid, "render thử nghiệm thất bại: %s" % msg, SEV_CHAN)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    form_maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    loaded: dict = {}

    print("=" * 72)
    print("MỤC 1: ĐỦ ĐUI (87 mẫu — tồn tại / json OK / id khớp / text khớp template)")
    print("=" * 72)
    audit_section1(form_maps, loaded)
    print("    đã load %d file blocks" % len(loaded))

    print("=" * 72)
    print("MỤC 2: THE ĐẦY ĐỦ (fields form_maps ⊆ keys blocks; keys blocks ⊆ the template)")
    print("=" * 72)
    audit_section2(form_maps, loaded)

    print("=" * 72)
    print("MỤC 3: LOOP ĐÚNG (9 block loop vs dynamic_tables)")
    print("=" * 72)
    audit_section3(form_maps, loaded)

    print("=" * 72)
    print("MỤC 4: CHK HỢP LỆ (key ∈ form_maps type=chk; nhãn suy từ template)")
    print("=" * 72)
    audit_section4(form_maps, loaded)

    print("=" * 72)
    print("MỤC 5: SCHEMA FRONTEND")
    print("=" * 72)
    audit_section5(loaded)

    print("=" * 72)
    print("MỤC 6: RENDER THỬ NGHIỆM (tools/docx_render.py, dữ liệu giả)")
    print("=" * 72)
    audit_section6(form_maps)

    # ---- Tổng kết ---------------------------------------------------------
    print()
    print("#" * 72)
    print("TỔNG KẾT THEO TỪNG MỤC")
    print("#" * 72)
    overall_fail = False
    for sec, title in [
        ("1", "Đủ đuôi + text khớp"),
        ("2", "The đầy đủ"),
        ("3", "Loop đúng"),
        ("4", "Chk hợp lệ"),
        ("5", "Schema frontend"),
        ("6", "Render thử nghiệm"),
    ]:
        fs = [f for f in FINDINGS if f[0] == sec and f[3] != SEV_NH]
        notes = [f for f in FINDINGS if f[0] == sec and f[3] == SEV_NH]
        status = "PASS" if not fs else "FAIL (%d lỗi)" % len(fs)
        if notes:
            status += " (+%d ghi chú bỏ qua được)" % len(notes)
        overall_fail = overall_fail or bool(fs)
        print("MỤC %s — %-22s : %s" % (sec, title, status))

    blockers = [f for f in FINDINGS if f[3] != SEV_NH]
    notes_all = [f for f in FINDINGS if f[3] == SEV_NH]

    if blockers:
        print()
        print("DANH SÁCH LỖI CỤ THỂ (%d):" % len(blockers))
        cur = None
        for sec, fid, desc, sev in blockers:
            if sec != cur:
                cur = sec
                print("-" * 72)
            print("[%s|%s] %s\n    → mức: %s" % (sec, fid, desc, sev))
    else:
        print("\nKhông phát hiện lỗi nào.")
    if notes_all:
        print()
        print("GHI CHÚ BỎ-QUA-ĐƯỢC (%d) — không ảnh hưởng exit code:" % len(notes_all))
        for sec, fid, desc, sev in notes_all:
            print("[%s|%s] %s" % (sec, fid, desc))

    return 1 if overall_fail else 0


if __name__ == "__main__":
    sys.exit(main())
