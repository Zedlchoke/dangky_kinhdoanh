# -*- coding: utf-8 -*-
"""Kiểm tra Wave 2 Agent 2C: lưới ngành ds_nganh trong 2 mẫu HỘ KINH DOANH
PLII_M02 (giấy đề nghị thay đổi nội dung ĐKKD hộ KD) và PLII_M07 (giấy chứng
nhận đăng ký hộ kinh doanh) - production.

Phạm vi TỪNG mẫu:
1. blocks app/data/blocks/<ID>.json có đúng 1 loop "ds_nganh":
   - hàng tiêu đề 4 cột khớp số ô của body/template;
   - cols zero-based {ten_nganh, ma_nganh, la_nganh_chinh};
   - cột 0 (STT) KHÔNG tag (STT tự sinh qua biến engine {_stt}).
2. form_maps.json khai báo dynamic_tables tương ứng (col/tag khớp).
3. Render template bằng tools/docx_render.write_rendered với 3 dòng mẫu
   (dòng đầu đánh dấu X ngành chính):
   - đủ 3 hàng dữ liệu nhân bản, mỗi giá trị nằm đúng ô cột;
   - STT hiển thị 1/2/3 (tự sinh);
   - đúng MỘT dấu X ở cột "Ngành, nghề kinh doanh chính";
   - không còn sót '{#ds_nganh}', '{/ds_nganh}', tag cột hay {_stt}.

Bằng chứng cột ngành chính trên template gốc (python-docx, đã ghi vào
tools/form_specs/household/*.json):
- PLII_M02: ô tiêu đề mục C.3 'Ngành, nghề kinh doanh chính9' + chú thích
  '9 Đánh dấu X để chọn một trong các ngành, nghề đã kê khai làm ngành,
  nghề kinh doanh chính.'
- PLII_M07: ô tiêu đề mục 3 'Ngành, nghề kinh doanh chính' (mẫu này không
  kèm số chú thích).

File test thuần Python (chỉ DOCX/blocks), exit code 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 -m tools.test_industry_household
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document                      # noqa: E402
from docx.oxml.ns import qn                   # noqa: E402
from docx.table import Table                  # noqa: E402
from docx.text.paragraph import Paragraph     # noqa: E402

from tools.docx_render import write_rendered  # noqa: E402

FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
OUT_DIR = ROOT / "generated_ho_so" / "_test_industry_household"

FORMS = ["PLII_M02", "PLII_M07"]
LOOP_NAME = "ds_nganh"
EXPECTED_HEADERS = ["STT", "Tên ngành", "Mã ngành",
                    "Ngành, nghề kinh doanh chính"]
EXPECTED_COLS = [(1, "ten_nganh"), (2, "ma_nganh"), (3, "la_nganh_chinh")]


def blocks_path(fid: str) -> Path:
    return ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)


def template_path(fid: str) -> Path:
    return ROOT / "app" / "templates" / ("%s.docx" % fid)


SAMPLE_ROWS = [
    {"ten_nganh": "Hoạt động lập trình máy vi tính",
     "ma_nganh": "6201", "la_nganh_chinh": "X"},
    {"ten_nganh": "Trồng lúa",
     "ma_nganh": "0111", "la_nganh_chinh": ""},
    {"ten_nganh": "Bán lẻ lương thực trong cửa hàng",
     "ma_nganh": "4711", "la_nganh_chinh": ""},
]

_results: list[tuple[bool, str]] = []


def check(name):
    """name: chuỗi tĩnh hoặc hàm nhận cùng tham số với fn -> nhãn test."""
    def deco(fn):
        def run(*args):
            label = name(*args) if callable(name) else name
            try:
                fn(*args)
                _results.append((True, label))
                print("PASS %s" % label)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (label, exc)))
                print("FAIL %s: %s" % (label, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append((False, "%s: exception %r" % (label, exc)))
                print("FAIL %s: exception %r" % (label, exc))
        return run
    return deco


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def cell_runs_text(cell: dict) -> str:
    return "".join(r.get("text", "") for r in cell["runs"])


def tc_iter(tr):
    for child in tr.iterchildren():
        if child.tag == qn("w:tc"):
            yield child


def tr_cell_texts(tbl, ri: int) -> list[str]:
    """Text từng ô của hàng ri — duyệt trực tiếp w:tc (mỗi ô đúng một lần)."""
    out = []
    for tc in tc_iter(tbl._tbl.tr_lst[ri]):
        txt = "\n".join(
            Paragraph(p_el, tbl.part.document).text
            for p_el in tc.iterchildren()
            if p_el.tag == qn("w:p")
        )
        out.append(txt.strip())
    return out


def body_tables(doc):
    """Các bảng theo thứ tự thân tài liệu (duyệt con trực tiếp body)."""
    return [Table(child, doc) for child in doc.element.body.iterchildren()
            if child.tag == qn("w:tbl")]


def find_industry_table(doc):
    """Tìm bảng có hàng tiêu đề khớp EXPECTED_HEADERS."""
    want = fold(" ".join(EXPECTED_HEADERS))
    for ti, tbl in enumerate(doc.tables):
        if len(tbl.rows) and fold(" ".join(tr_cell_texts(tbl, 0))) == want:
            return ti, tbl
    return None, None


@check(lambda fid: "blocks %s: dung 1 loop ds_nganh, 4 cot, cols zero-based, cot 0 khong tag" % fid)
def t_blocks_loop_structure(fid: str):
    data = json.loads(blocks_path(fid).read_text(encoding="utf-8"))
    loops = [b for b in data["blocks"] if b.get("t") == "loop"]
    assert len(loops) == 1, "kỳ vọng đúng 1 block loop, thấy %d" % len(loops)
    blk = loops[0]
    assert blk["loop"] == LOOP_NAME, "loop=%r != %r" % (blk["loop"], LOOP_NAME)
    assert blk["headerRows"] == [0], "headerRows=%r != [0]" % (blk["headerRows"],)

    hdr_cells = blk["rows"][blk["headerRows"][0]]["cells"]
    assert len(hdr_cells) == 4, "header có %d ô != 4" % len(hdr_cells)
    got_headers = [cell_runs_text(c).strip() for c in hdr_cells]
    assert got_headers == EXPECTED_HEADERS, \
        "header %r != %r" % (got_headers, EXPECTED_HEADERS)

    for ri, row in enumerate(blk["rows"]):
        assert len(row["cells"]) == 4, \
            "rows[%d] có %d ô != 4" % (ri, len(row["cells"]))

    got_cols = sorted((c["col"], c["tag"]) for c in blk["cols"])
    assert got_cols == EXPECTED_COLS, "cols %r != %r" % (got_cols, EXPECTED_COLS)
    assert all(c["col"] != 0 for c in blk["cols"]), \
        "cột 0 (STT tự sinh) không được có tag trong cols"

    # grid khớp template: rows + blank + 1 khuôn = tổng hàng bảng trong template
    fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))[fid]
    dt = next(t for t in fm["dynamic_tables"] if t["loop"] == LOOP_NAME)
    doc = Document(str(template_path(fid)))
    tbl = body_tables(doc)[dt["table_index"]]
    n_tr = len(tbl._tbl.tr_lst)
    total = len(blk["rows"]) + blk["blankRows"] + 1
    assert total == n_tr, \
        "rows(%d)+blank(%d)+khuôn(1)=%d != %d hàng template" % (
            len(blk["rows"]), blk["blankRows"], total, n_tr)
    assert blk["blankRows"] >= 1, "cần ít nhất 1 hàng trắng để in"


@check(lambda fid: "form_maps %s: dynamic_tables khai bao dung col/tag cho ds_nganh" % fid)
def t_form_maps_metadata(fid: str):
    fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))[fid]
    dts = [t for t in fm.get("dynamic_tables") or [] if t["loop"] == LOOP_NAME]
    assert len(dts) == 1, "kỳ vọng 1 dynamic_tables ds_nganh, thấy %d" % len(dts)
    dt = dts[0]
    got_cols = sorted((c["col"], c["tag"]) for c in dt["columns"])
    assert got_cols == EXPECTED_COLS, \
        "columns %r != %r" % (got_cols, EXPECTED_COLS)
    fld_keys = {f["key"] for f in fm.get("fields", [])}
    for _, tag in EXPECTED_COLS:
        assert ("%s.%s" % (LOOP_NAME, tag)) in fld_keys, \
            "thiếu field %s.%s trong form_maps" % (LOOP_NAME, tag)


@check(lambda fid: "render DOCX %s: 3 dong vao dung cot, STT 1/2/3, dung mot X nganh chinh, khong con token" % fid)
def t_render_three_rows(fid: str):
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ("%s_ds_nganh.docx" % fid)
    write_rendered(str(template_path(fid)),
                   {LOOP_NAME: SAMPLE_ROWS}, out_path)

    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    doc = Document(str(out_path))
    _, tbl = find_industry_table(doc)
    assert tbl is not None, "không tìm thấy bảng ngành nghề trong file render"
    texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]

    assert [t.strip() for t in texts[0]] == EXPECTED_HEADERS, \
        "header render %r != %r" % (texts[0], EXPECTED_HEADERS)

    n_data = len(SAMPLE_ROWS)
    data_texts = texts[-n_data:]
    n_x = 0
    for i, row in enumerate(data_texts):
        want = SAMPLE_ROWS[i]
        assert len(row) == 4, "hàng dữ liệu %d có %d ô != 4" % (i, len(row))
        assert row[0] == str(i + 1), \
            "STT dòng %d = %r, kỳ vọng %r" % (i, row[0], str(i + 1))
        assert row[1] == want["ten_nganh"], \
            "Tên ngành dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "Mã ngành dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "Ngành chính dòng %d = %r != %r" % (i, row[3], want["la_nganh_chinh"])
        n_x += 1 if row[3] == "X" else 0
    assert n_x == 1, "kỳ vọng đúng 1 dòng có X ngành chính, thấy %d" % n_x
    assert data_texts[0][3] == "X", "dòng đầu phải là ngành chính (X)"

    # không còn bất kỳ the loop/cột/biến engine nào sót trong XML
    for tok in ("{#%s}" % LOOP_NAME, "{/%s}" % LOOP_NAME,
                "{ten_nganh}", "{ma_nganh}", "{la_nganh_chinh}", "{_stt}"):
        assert tok not in xml, "còn sót token %r trong document.xml" % tok


def main() -> int:
    for fid in FORMS:
        t_blocks_loop_structure(fid)
        t_form_maps_metadata(fid)
        t_render_three_rows(fid)
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("test_industry_household: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
