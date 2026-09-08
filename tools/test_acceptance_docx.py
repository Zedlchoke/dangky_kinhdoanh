# -*- coding: utf-8 -*-
"""Acceptance AC13 (PLAN.md mục "Acceptance tests bắt buộc", mục 13): DOCX PLII_M01.

Phạm vi:
1. Render app/templates/PLII_M01.docx bằng tools/docx_render.write_rendered với
   dữ liệu ds_nganh mẫu (3 dòng: ma_nganh/ten_nganh/la_nganh_chinh).
2. Bảng ngành nghề trong file render phải:
   - giữ nguyên hàng tiêu đề (STT | Tên ngành | Mã ngành | Ngành, nghề kinh
     doanh chính);
   - nhân đúng số dòng dữ liệu ở CUỐI bảng (sau các hàng trắng để in);
   - mỗi giá trị nằm đúng ô cột (so text từng cell):
     * cột STT tự sinh 1/2/3 theo {_stt};
     * cột "Ngành, nghề kinh doanh chính" có ĐÚNG MỘT ô 'X' tại dòng ngành
       chính, các dòng còn lại rỗng;
     * mã/tên ngành đúng giá trị từng dòng;
   - KHÔNG còn sót token loop/cột ({#ds_nganh}, {/ds_nganh}, {ten_nganh},
     {ma_nganh}, {la_nganh_chinh}, {_stt}) trong word/document.xml.

File thuần Python, exit code 0 = PASS / 1 = FAIL.
Được gọi độc lập HOẶC từ app_web/test_acceptance.js (mục AC13).

Chạy:  python -X utf8 tools/test_acceptance_docx.py
"""
from __future__ import annotations

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

TEMPLATE_PATH = ROOT / "app" / "templates" / "PLII_M01.docx"
OUT_DIR = ROOT / "generated_ho_so" / "_test_acceptance_plii_m01"

LOOP_NAME = "ds_nganh"
EXPECTED_HEADERS = ["STT", "Tên ngành", "Mã ngành",
                    "Ngành, nghề kinh doanh chính"]
SAMPLE_ROWS = [
    {"ma_nganh": "0111", "ten_nganh": "Trồng lúa", "la_nganh_chinh": "X"},
    {"ma_nganh": "0112", "ten_nganh": "Trồng ngô và cây lương thực có hạt khác",
     "la_nganh_chinh": ""},
    {"ma_nganh": "6201", "ten_nganh": "Hoạt động lập trình máy vi tính",
     "la_nganh_chinh": ""},
]

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


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def tc_iter(tr):
    return [c for c in tr.iterchildren() if c.tag == qn("w:tc")]


def tr_cell_texts(tbl: Table, ri: int) -> list[str]:
    """Text từng ô của hàng ri — duyệt trực tiếp w:tc (mỗi ô đúng một lần)."""
    return ["\n".join(
        Paragraph(p_el, tbl.part.document).text
        for p_el in tc.iterchildren()
        if p_el.tag == qn("w:p")
    ).strip() for tc in tc_iter(tbl._tbl.tr_lst[ri])]


def find_industry_table(doc) -> Table | None:
    want = fold(" ".join(EXPECTED_HEADERS))
    for tbl in doc.tables:
        if len(tbl.rows) and fold(" ".join(tr_cell_texts(tbl, 0))) == want:
            return tbl
    return None


@check("PLII_M01 render DOCX: tim duoc bang ds_nganh, header giu nguyen")
def t_render_and_header():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "PLII_M01_ds_nganh.docx"
    write_rendered(TEMPLATE_PATH, {LOOP_NAME: SAMPLE_ROWS}, out_path)
    doc = Document(str(out_path))
    tbl = find_industry_table(doc)
    assert tbl is not None, \
        "không tìm thấy bảng ngành nghề (%s) trong file render" % LOOP_NAME
    got = [t.strip() for t in tr_cell_texts(tbl, 0)]
    assert got == EXPECTED_HEADERS, "header %r != %r" % (got, EXPECTED_HEADERS)


@check("PLII_M01 render DOCX: dung so dong du lieu, gia tri dung cot, dung thu tu")
def t_rows_and_columns():
    out_path = OUT_DIR / "PLII_M01_ds_nganh.docx"
    doc = Document(str(out_path))
    tbl = find_industry_table(doc)
    assert tbl is not None, "mất bảng ngành nghề"
    texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]

    n_data = len(SAMPLE_ROWS)
    # [F3T.2 max(K,N)] dữ liệu đứng NGAY SAU header; K−N hàng trắng còn lại
    # nằm SAU dữ liệu. Pin cũ "dữ liệu nằm cuối bảng" (texts[-n_data:]) là
    # vị trí khiếm khuyết K-blank-then-data — đã nâng cấp theo hợp đồng mới.
    data_texts = texts[1:1 + n_data]
    for i, row in enumerate(data_texts):
        want = SAMPLE_ROWS[i]
        assert len(row) == len(EXPECTED_HEADERS), \
            "hàng dữ liệu %d có %d ô != %d" % (
                i, len(row), len(EXPECTED_HEADERS))
        assert row[1] == want["ten_nganh"], \
            "Tên ngành dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "Mã ngành dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        # Cột STT: engine {_stt} phải sinh đúng số thứ tự 1-based từng dòng.
        assert row[0] == str(i + 1), \
            "ô STT dòng %d = %r != %r" % (i, row[0], str(i + 1))
        # Cột Ngành chính: ĐÚNG MỘT ô 'X' tại dòng ngành chính (dòng 0),
        # mọi dòng khác phải rỗng — không chấp nhận rỗng toàn cột.
        assert row[3] == want["la_nganh_chinh"], \
            "ô Ngành chính dòng %d = %r != %r" % (
                i, row[3], want["la_nganh_chinh"] or "(trống)")
    x_marks = [t[3] for t in data_texts]
    assert x_marks.count("X") == 1 and x_marks[0] == "X", \
        "cột Ngành chính phải có đúng một 'X' ở dòng ngành chính, thấy %r" % (
            x_marks,)
    # [F3T.2] hàng trắng residual (K−N) nằm SAU dữ liệu: phải trắng hoàn
    # toàn — không được mang STT/giá trị.
    for r in texts[1 + n_data:]:
        assert all(c == "" for c in r), \
            "hàng đuôi phải trắng hoàn toàn (STT trống): %r" % (r,)
    mid = texts[1 + n_data:]
    joined = "|".join("|".join(r) for r in mid)
    for want in SAMPLE_ROWS:
        assert want["ma_nganh"] not in joined, \
            "giá trị dữ liệu %r bị trượt vào hàng trắng giữa bảng" % (
                want["ma_nganh"],)


@check("PLII_M01 render DOCX: khong con sot token loop/cot trong document.xml")
def t_no_leftover_tokens():
    out_path = OUT_DIR / "PLII_M01_ds_nganh.docx"
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    for tok in ("{#%s}" % LOOP_NAME, "{/%s}" % LOOP_NAME,
                "{ten_nganh}", "{ma_nganh}", "{la_nganh_chinh}", "{_stt}"):
        assert tok not in xml, "còn sót token %r trong document.xml" % tok


def main() -> int:
    t_render_and_header()
    t_rows_and_columns()
    t_no_leftover_tokens()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("test_acceptance_docx (PLII_M01): %d PASS / %d FAIL"
          % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
