# -*- coding: utf-8 -*-
"""N10 - INDEPENDENT AUDIT wave P1: negative test DOCX PLII_M01.

Tái dùng HELPER của tools/test_plii_m01_member_stt.py bằng import module
(KHÔNG sửa file đó). Kiểm chứng độc lập:
- render PLII_M01 với 3 thành viên hộ gia đình: STT '1','2','3' nằm ĐÚNG
  cột 0 của từng dòng dữ liệu trong bảng ds_tv_ho_gia_dinh;
- w:tbl[0] (bảng ds_nganh bên cạnh) không đổi so contract cũ: STT 1..3,
  đúng MỘT ô X ngành chính ở dòng đầu, giá trị cột khớp dữ liệu vào;
- không còn token engine nào sót trong document.xml.

Chạy: python -X utf8 -m tools.test_audit_p1_docx_negative
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document  # noqa: E402

import tools.test_plii_m01_member_stt as ref  # noqa: E402
from tools.docx_render import write_rendered  # noqa: E402

OUT_DIR = ROOT / "generated_ho_so" / "_test_audit_p1_docx_negative"

_results = []


def check(name):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append(("PASS", name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append(("FAIL", "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append(("FAIL", "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def render_out(name: str) -> tuple[Path, str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / name
    write_rendered(str(ref.TEMPLATE_PATH),
                   {ref.LOOP_MEMBER: ref.MEMBER_ROWS,
                    ref.LOOP_INDUSTRY: ref.INDUSTRY_ROWS},
                   out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return out_path, xml


@check("N10a. render PLII_M01: STT '1','2','3' dung cot 0 tung row thanh vien")
def t_member_stt_col0():
    _, xml = render_out("audit_thanh_vien.docx")
    doc = Document(str(OUT_DIR / "audit_thanh_vien.docx"))
    tbl = ref.find_table_by_headers(doc, ref.MEMBER_HEADERS)
    assert tbl is not None, "khong tim thay bang thanh vien ho gia dinh"
    texts = [ref.tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]
    n_data = len(ref.MEMBER_ROWS)
    assert len(texts) >= 1 + n_data, \
        "bang chi co %d hang, thua cho %d dong du lieu" % (len(texts), n_data)
    # [F3T.2 max(K,N)] dữ liệu ngay sau header (pin cũ texts[-n:] là vị trí
    # khiếm khuyết K-blank-then-data)
    data_rows = texts[1:1 + n_data]
    for i, row in enumerate(data_rows):
        want = ref.MEMBER_ROWS[i]
        assert len(row) == len(ref.MEMBER_HEADERS), \
            "hang %d co %d o != %d" % (i, len(row), len(ref.MEMBER_HEADERS))
        assert row[0] == str(i + 1), \
            "STT dong %d = %r, ky vọng %r (cot 0)" % (i, row[0], str(i + 1))
        for ci, tag in ref.MEMBER_COLS:
            assert row[ci] == want[tag], \
                "o cot %d (%s) dong %d = %r != %r" % (
                    ci, tag, i, row[ci], want[tag])
    ref.assert_no_leftover_tokens(
        xml,
        ["{_stt}",
         "{#%s}" % ref.LOOP_MEMBER, "{/%s}" % ref.LOOP_MEMBER]
        + ["{%s}" % t for _, t in ref.MEMBER_COLS]
        + ["{#%s}" % ref.LOOP_INDUSTRY, "{/%s}" % ref.LOOP_INDUSTRY]
        + ["{%s}" % t for _, t in ref.INDUSTRY_COLS])


@check("N10b. w:tbl[0] ds_nganh canh ben giu contract cu (STT 1..3, dung MOT X)")
def t_industry_table_contract():
    _, xml = render_out("audit_ds_nganh.docx")
    doc = Document(str(OUT_DIR / "audit_ds_nganh.docx"))
    tbl = ref.find_table_by_headers(doc, ref.INDUSTRY_HEADERS)
    assert tbl is not None, "khong tim thay bang nganh nghe"
    texts = [ref.tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]
    n_data = len(ref.INDUSTRY_ROWS)
    # [F3T.2 max(K,N)] dữ liệu ngay sau header (pin cũ texts[-n:] là vị trí
    # khiếm khuyết K-blank-then-data)
    data_rows = texts[1:1 + n_data]
    n_x = 0
    for i, row in enumerate(data_rows):
        want = ref.INDUSTRY_ROWS[i]
        assert len(row) == len(ref.INDUSTRY_HEADERS), \
            "hang nganh %d co %d o != %d" % (i, len(row), len(ref.INDUSTRY_HEADERS))
        assert row[0] == str(i + 1), \
            "STT nganh dong %d = %r != %r" % (i, row[0], str(i + 1))
        assert row[1] == want["ten_nganh"], \
            "Ten nganh dong %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "Ma nganh dong %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "Nganh chinh dong %d = %r != %r" % (i, row[3], want["la_nganh_chinh"])
        n_x += 1 if row[3] == "X" else 0
    assert n_x == 1, "ky vọng dung 1 o X nganh chinh, thay %d" % n_x
    assert data_rows[0][3] == "X", "dong dau phai la nganh chinh (X)"
    ref.assert_no_leftover_tokens(
        xml,
        ["{_stt}",
         "{#%s}" % ref.LOOP_INDUSTRY, "{/%s}" % ref.LOOP_INDUSTRY]
        + ["{%s}" % t for _, t in ref.INDUSTRY_COLS]
        + ["{#%s}" % ref.LOOP_MEMBER, "{/%s}" % ref.LOOP_MEMBER]
        + ["{%s}" % t for _, t in ref.MEMBER_COLS])


def main() -> int:
    # template chua regen thi ca hai check deu khong y nghia -> bao ro
    tokens = ref.khuon_row_tokens(ref.template_xml(), ref.LOOP_MEMBER)
    if "{_stt}" not in tokens:
        print("FAIL template PLII_M01 chua co {_stt} o hang khuon thanh vien "
              "(regression so voi a07122d)")
        return 1
    t_member_stt_col0()
    t_industry_table_contract()
    fails = [n for s, n in _results if s != "PASS"]
    print("-" * 60)
    print("test_audit_p1_docx_negative: %d PASS / %d FAIL"
          % (len(_results) - len(fails), len(fails)))
    for n in fails:
        print(" - FAIL:", n)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
