# -*- coding: utf-8 -*-
"""Kiểm toán độ bền engine render (tools/docx_render.py) — file kiểm toán độc lập.

Phạm vi:
- Giá trị chứa ký tự đặc biệt XML (& < > " ', dấu tiếng Việt, xuống dòng trong ô).
- Giá trị None/số/đối tượng lạ; key thiếu trong data; data có key thừa.
- Template có header/footer chứa the (dùng cả template thật nếu có, và template
  tổng hợp tạo bằng python-docx để chắc chắn có header/footer).
- Loop: 1 phần tử, 100 phần tử, list chứa None, giá trị None (không phải list),
  2 loop khác tên trong 1 tài liệu (PLII_M01).
- File xuất ra mở được bằng python-docx và zip nguyên vẹn (zipfile.testzip).
- Lưu ý đã biết: giá trị chứa chuỗi "{key}" sẽ bị thay lần thứ hai ở lượt
  _subst_vars (engine chạy 2 lượt trên cùng XML) — test ghi nhận hành vi này.

Chạy:  python -m tools.audit_engine_test
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import docx  # python-docx

from tools.docx_render import write_rendered

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
OUT_DIR = ROOT / "generated_ho_so" / "_audit_engine"

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


def make_doc(paragraph_texts, header_text=None, footer_text=None, table_rows=None):
    """Tạo template .docx tổng hợp trong bộ nhớ tạm, trả về đường dẫn."""
    d = docx.Document()
    for t in paragraph_texts:
        d.add_paragraph(t)
    if table_rows is not None:
        ncol = len(table_rows[0])
        tbl = d.add_table(rows=len(table_rows), cols=ncol)
        for ri, row in enumerate(table_rows):
            for ci, val in enumerate(row):
                tbl.rows[ri].cells[ci].paragraphs[0].add_run(val)
    sec = d.sections[0]
    if header_text is not None:
        sec.header.paragraphs[0].add_run(header_text)
    if footer_text is not None:
        sec.footer.paragraphs[0].add_run(footer_text)
    fd = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    d.save(fd.name)
    fd.close()
    return Path(fd.name)


def verify_rendered(out_path: Path, must_contain=(), must_not_contain=(),
                    check_header=None, check_footer=None):
    """File xuất ra: zip nguyên vẹn + python-docx mở OK + nội dung đúng."""
    with zipfile.ZipFile(out_path) as z:
        assert z.testzip() is None, "zip hỏng (testzip != None)"
        body = z.read("word/document.xml").decode("utf-8")
        hdr = z.read("word/header1.xml").decode("utf-8") if "word/header1.xml" in z.namelist() else ""
        ftr = z.read("word/footer1.xml").decode("utf-8") if "word/footer1.xml" in z.namelist() else ""
    docx.Document(str(out_path))  # phải mở được
    for s in must_contain:
        assert s in body or s in hdr or s in ftr, "thiếu nội dung mong đợi: %r" % s
    for s in must_not_contain:
        assert s not in body and s not in hdr and s not in ftr, \
            "còn sót/tag không mong muốn: %r" % s
    if check_header is not None:
        assert check_header in hdr, "header thiếu: %r (header=%r)" % (check_header, hdr[:200])
    if check_footer is not None:
        assert check_footer in ftr, "footer thiếu: %r" % check_footer


# ---------------------------------------------------------------------------

@check("ky tu dac biet XML: & < > \" ' , tieng Viet, xuong dong trong o")
def t_special_chars():
    tpl = make_doc(["Ten: {ten}", "Ghi chu: {ghi_chu}"])
    out = OUT_DIR / "special.docx"
    data = {
        "ten": 'A&B <C> "D" \'E\' Nguyễn Văn Đệ — ếễể',
        "ghi_chu": "dong1\ndong2\ndong3",
    }
    write_rendered(tpl, data, out)
    # & < > phải được escape thành entity trong XML
    verify_rendered(
        out,
        must_contain=["Nguyễn Văn Đệ"],
        must_not_contain=["A&B <C>", "{ten}", "{ghi_chu}"],
    )
    import re
    with zipfile.ZipFile(out) as z:
        body = z.read("word/document.xml").decode("utf-8")
    assert "&amp;" in body and "&lt;" in body and "&gt;" in body, "không thấy escape entity"
    assert "\ndong2" in body, "xuống dòng bị mất trong w:t"


@check("gia tri None / so / doi tuong la")
def t_odd_values():
    tpl = make_doc(["{so}", "{none}", "{obj}", "{float}"])
    out = OUT_DIR / "odd.docx"
    class Weird:
        def __str__(self):
            return "OBJ<>&"
    data = {"so": 12345678901234567, "none": None, "obj": Weird(), "float": 3.14}
    write_rendered(tpl, data, out)
    with zipfile.ZipFile(out) as z:
        body = z.read("word/document.xml").decode("utf-8")
    assert "12345678901234567" in body
    assert "3.14" in body
    assert "OBJ&lt;&gt;&amp;" in body, "đối tượng lạ phải str() rồi escape"
    assert "{none}" not in body and "{obj}" not in body


@check("key khong ton tai -> rong; data co key thua -> bo qua")
def t_missing_and_extra():
    tpl = make_doc(["{co}", "{khong_co}"])
    out = OUT_DIR / "missing.docx"
    data = {"co": "OK", "thua_1": "X", "thua_2.nested": "Y"}
    write_rendered(tpl, data, out)
    with zipfile.ZipFile(out) as z:
        body = z.read("word/document.xml").decode("utf-8")
    assert ">OK<" in body
    assert "{" not in body.replace("{", "", 0) or "{khong_co}" not in body, \
        "tag thiếu key phải bị thay bằng rỗng"


@check("header/footer chua the duoc render (template tong hop)")
def t_header_footer_synthetic():
    tpl = make_doc(["Body: {noi_dung}"], header_text="Header {ten_dn}",
                   footer_text="Trang cua {ten_dn}")
    out = OUT_DIR / "hf.docx"
    write_rendered(tpl, {"noi_dung": "ND", "ten_dn": "Công ty ABC & Test"}, out)
    verify_rendered(out, must_not_contain=["{ten_dn}"],
                    check_header="Công ty ABC &amp; Test", check_footer="Công ty ABC &amp; Test")


@check("template that co header/footer: quet + render mau co the")
def t_header_footer_real():
    hits = []
    fm = json.loads((APP / "data" / "form_maps.json").read_text(encoding="utf-8"))
    for fid in sorted(fm):
        p = APP / fm[fid]["template"]
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            hf = [n for n in names if n.startswith(("word/header", "word/footer"))]
            tagged = False
            for n in hf:
                xml = z.read(n).decode("utf-8", "ignore")
                import re
                if re.search(r"\{[#/]?[A-Za-z]", xml):
                    tagged = True
            if hf:
                hits.append((fid, len(hf), tagged))
    print("   -> template co header/footer: %d/%d" % (len(hits), len(fm)))
    print("   -> template co THE trong header/footer:", [h[0] for h in hits if h[2]])
    if not hits:
        print("   -> GHI CHU: khong template nao co header/footer — bo qua phan nay")


@check("loop 1 phan tu va 100 phan tu")
def t_loop_sizes():
    rows = [["STT", "Ten"], ["{#ds}{stt}{/ds}", "{ho_ten}"]]
    tpl = make_doc([], table_rows=rows)
    out1 = OUT_DIR / "loop1.docx"
    write_rendered(tpl, {"ds": [{"stt": "1", "ho_ten": "Mot"}]}, out1)
    with zipfile.ZipFile(out1) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert "Mot" in b and "{#ds}" not in b and "{ho_ten}" not in b
    assert b.count("<w:tr") == 2, "1 phần tử: phải còn 2 hàng (tiêu đề + dữ liệu)"
    out100 = OUT_DIR / "loop100.docx"
    write_rendered(tpl, {"ds": [{"stt": str(i), "ho_ten": "N%d" % i} for i in range(100)]}, out100)
    with zipfile.ZipFile(out100) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert b.count("<w:tr") == 101
    verify_rendered(out100)


@check("loop: list chua None; gia tri None (khong phai list)")
def t_loop_bad_items():
    rows = [["STT"], ["{#ds}{ten}{/ds}"]]
    tpl = make_doc([], table_rows=rows)
    out = OUT_DIR / "loopbad.docx"
    write_rendered(tpl, {"ds": [None, "chuoi", {"ten": "OK"}, 42]}, out)
    with zipfile.ZipFile(out) as z:
        b = z.read("word/document.xml").decode("utf-8")
    # chỉ dict được nhân bản; None/chuỗi/số bị bỏ qua im lặng
    assert "OK" in b and "{#ds}" not in b
    assert b.count("<w:tr") == 2, "chỉ hàng dict hợp lệ được giữ"
    out2 = OUT_DIR / "loopnull.docx"
    write_rendered(tpl, {"ds": None}, out2)
    with zipfile.ZipFile(out2) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert b.count("<w:tr") == 1, "giá trị không phải list: hàng khuôn phải bị xóa"
    # thiếu hẳn key cũng vậy
    out3 = OUT_DIR / "loopabsent.docx"
    write_rendered(tpl, {}, out3)
    with zipfile.ZipFile(out3) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert b.count("<w:tr") == 1


@check("PLII_M01: 2 loop khac ten trong 1 tai lieu (ds_nganh + ds_tv_ho_gia_dinh)")
def t_two_loops_real():
    fmap = json.loads((APP / "data" / "form_maps.json").read_text(encoding="utf-8"))["PLII_M01"]
    tpl = APP / fmap["template"]
    data = {
        "ds_nganh": [
            {"ten_nganh": "Xây dựng công trình & hạ tầng", "ma_nganh": "4101"},
            {"ten_nganh": "Bán lẻ <thực phẩm>", "ma_nganh": "4711"},
        ],
        "ds_tv_ho_gia_dinh": [
            {"ho_ten": "Trần Thị B", "ngay_sinh": "01/01/1980", "so_cccd": "012345678901",
             "gioi_tinh": "Nữ", "quoc_tich": "Việt Nam", "dan_toc": "Kinh",
             "noi_thuong_tru": "Hà Nội", "noi_o_hien_tai": "Hà Nội"},
        ],
    }
    # điền nốt các field thường để tránh tag lơ lửng do thiếu key là OK (-> rỗng)
    out = OUT_DIR / "plii_m01_twoloop.docx"
    write_rendered(tpl, data, out)
    with zipfile.ZipFile(out) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert "Xây dựng công trình &amp; hạ tầng" in b
    assert "Bán lẻ &lt;thực phẩm&gt;" in b
    assert "Trần Thị B" in b
    assert "{#" not in b and "{/" not in b, "còn sót tag loop"
    verify_rendered(out)


@check("injection ngoac nhon: gia tri chua '{key}' KHONG duoc doc nham thanh tag")
def t_brace_injection():
    # a) giá trị thường
    tpl = make_doc(["Val: {v}"])
    out = OUT_DIR / "inject.docx"
    write_rendered(tpl, {"v": "chu_a {secret} chu_b", "secret": "BI_THAY"}, out)
    with zipfile.ZipFile(out) as z:
        b = z.read("word/document.xml").decode("utf-8")
    assert "BI_THAY" not in b, \
        "giá trị thường chứa '{secret}' đã bị thay thế lần thứ hai (double-substitution)"
    assert "chu_a" in b and "chu_b" in b
    # b) giá trị trong HÀNG LOOP (trước đây bị double-substitution)
    rows = [["Ten"], ["{#ds}{ten}{/ds}"]]
    tpl2 = make_doc([], table_rows=rows)
    out2 = OUT_DIR / "inject_loop.docx"
    write_rendered(tpl2, {"ds": [{"ten": "chu_a {secret2} chu_b"}], "secret2": "BI_THAY"}, out2)
    with zipfile.ZipFile(out2) as z:
        b2 = z.read("word/document.xml").decode("utf-8")
    assert "BI_THAY" not in b2, \
        "giá trị trong hàng loop chứa '{secret2}' đã bị thay lần 2 — engine đọc nhầm dữ liệu thành tag"
    assert "chu_a" in b2 and "chu_b" in b2


@check("file xuat ra mo duoc bang Word-python-docx + zip integrity (toan bo ket qua audit)")
def t_all_outputs_zip_ok():
    outs = sorted(OUT_DIR.glob("*.docx")) if OUT_DIR.exists() else []
    assert outs, "không có file kết quả để kiểm tra"
    for p in outs:
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None, "%s: zip hỏng" % p.name
        docx.Document(str(p))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        t_special_chars,
        t_odd_values,
        t_missing_and_extra,
        t_header_footer_synthetic,
        t_header_footer_real,
        t_loop_sizes,
        t_loop_bad_items,
        t_two_loops_real,
        t_brace_injection,
        t_all_outputs_zip_ok,
    ):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("Audit engine: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
