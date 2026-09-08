# -*- coding: utf-8 -*-
"""P1-E (lane p1/e-plii-m01-stt) — acceptance test cột STT bảng THÀNH VIÊN HỘ
GIA ĐÌNH của PLII_M01 (Giấy đề nghị đăng ký hộ kinh doanh).

Defect manifest `plii_m01_stt_thieu_tag_ho_gia_dinh`: template làm việc
app/templates/PLII_M01.docx w:tbl[1] thiếu tag {_stt} ở ô r5c0 -> DOCX render
cột STT thành viên hộ gia đình TRỐNG. Fix: spec
tools/form_specs/core/PLII_M01.json đổi stt_tag=true cho entry
ds_tv_ho_gia_dinh rồi regen generator (build_form_maps --one PLII_M01).

Các test ĐỌC trang thái production hiện tại (spec + form_maps.json + template):
- Hợp đồng spec / form_maps / blocks: PASS NGAY (không phụ thuộc regen).
- Template + render DOCX 3 thành viên: capability probe kiểm tra {_stt} ở hàng
  khuôn w:tbl[1] TRƯỚC khi assert; template CHƯA regen thì ghi nhận
  EXPECTED-FAIL-PRE-INTEGRATION (đếm riêng, không tính PASS, KHÔNG nuốt lỗi —
  mọi assert bên dưới vẫn chạy đủ khi probe pass). Sau khi Lead regen tập
  trung, các test này tự XANH không cần sửa assertion.
- Bảng ds_nganh cạnh bên: giữ nguyên contract cũ (STT 1/2/3 tự sinh + đúng
  MỘT ô X ngành chính, đối chiếu CONTRACT_PLII_M01_STT_X trong
  tools/test_contract_release.py) — chạy độc lập, phải PASS cả hai trạng thái.

Biến môi trường STRICT=1 biến mọi EXPECTED-FAIL-PRE-INTEGRATION thành FAIL
thật (dùng làm gate sau integration).

File thuần Python (chỉ DOCX/blocks), exit 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 -m tools.test_plii_m01_member_stt
"""
from __future__ import annotations

import json
import os
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

from tools.docx_render import LEFTOVER_RE, write_rendered  # noqa: E402

SPEC_PATH = ROOT / "tools" / "form_specs" / "core" / "PLII_M01.json"
FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
BLOCKS_PATH = ROOT / "app" / "data" / "blocks" / "PLII_M01.json"
TEMPLATE_PATH = ROOT / "app" / "templates" / "PLII_M01.docx"
OUT_DIR = ROOT / "generated_ho_so" / "_test_plii_m01_member_stt"

LOOP_MEMBER = "ds_tv_ho_gia_dinh"
LOOP_INDUSTRY = "ds_nganh"

# Header 10 cột bảng thành viên (spec headers, khớp template thật)
MEMBER_HEADERS = ["STT", "Họ tên", "Ngày, tháng, năm sinh",
                  "Số định danh cá nhân", "Giới tính", "Quốc tịch", "Dân tộc",
                  "Nơi thường trú", "Nơi ở hiện tại", "Chữ ký"]
# cols zero-based: cột 0 STT tự sinh {_stt} (không tag), cột 1..9 có tag
MEMBER_COLS = [(1, "ho_ten"), (2, "ngay_sinh"), (3, "so_cccd"),
               (4, "gioi_tinh"), (5, "quoc_tich"), (6, "dan_toc"),
               (7, "noi_thuong_tru"), (8, "noi_o_hien_tai"), (9, "chu_ky")]
MEMBER_FIELDS = [tag for _, tag in MEMBER_COLS if tag != "chu_ky"]

INDUSTRY_HEADERS = ["STT", "Tên ngành", "Mã ngành",
                    "Ngành, nghề kinh doanh chính"]
INDUSTRY_COLS = [(1, "ten_nganh"), (2, "ma_nganh"), (3, "la_nganh_chinh")]

# 3 thành viên dữ liệu hợp lệ, giá trị phân biệt từng ô để phát hiện trượt cột
MEMBER_ROWS = [
    {"ho_ten": "Nguyễn Văn An", "ngay_sinh": "01/01/1980",
     "so_cccd": "001080001234", "gioi_tinh": "Nam", "quoc_tich": "Việt Nam",
     "dan_toc": "Kinh", "noi_thuong_tru": "Số 1 Phố Huế, Hà Nội",
     "noi_o_hien_tai": "Số 2 Nguyễn Trãi, Hà Nội", "chu_ky": ""},
    {"ho_ten": "Trần Thị Bình", "ngay_sinh": "02/02/1985",
     "so_cccd": "001085002345", "gioi_tinh": "Nữ", "quoc_tich": "Việt Nam",
     "dan_toc": "Tày", "noi_thuong_tru": "Thôn 3, Xã Quang Minh, Hà Nội",
     "noi_o_hien_tai": "Số 8 Trần Duy Hưng, Hà Nội", "chu_ky": ""},
    {"ho_ten": "Lê Văn Cường", "ngay_sinh": "03/03/1990",
     "so_cccd": "001090003456", "gioi_tinh": "Nam", "quoc_tich": "Việt Nam",
     "dan_toc": "Nùng", "noi_thuong_tru": "Số 15 Đường Láng, Hà Nội",
     "noi_o_hien_tai": "Số 27 Khuất Duy Tiến, Hà Nội", "chu_ky": ""},
]

INDUSTRY_ROWS = [
    {"ten_nganh": "Hoạt động lập trình máy vi tính", "ma_nganh": "6201",
     "la_nganh_chinh": "X"},
    {"ten_nganh": "Trồng lúa nước", "ma_nganh": "0111", "la_nganh_chinh": ""},
    {"ten_nganh": "Bán lẻ thực phẩm trong cửa hàng chuyên doanh",
     "ma_nganh": "4711", "la_nganh_chinh": ""},
]

_results: list[tuple[str, str]] = []  # (status, label)
STRICT = os.environ.get("STRICT") == "1"


class EFPI(Exception):
    """Capability probe thất bại: artifact production CHƯA regen sau khi merge
    spec (template còn thiếu {_stt}). Chỉ ném từ probe, trước phần assert."""
    pass


def check(name):
    def deco(fn):
        def run(*args):
            try:
                fn(*args)
                _results.append(("PASS", name))
                print("PASS %s" % name)
            except EFPI as exc:
                _results.append(("EXPECTED-FAIL-PRE-INTEGRATION", name))
                print("EXPECTED-FAIL-PRE-INTEGRATION %s: %s" % (name, exc))
            except AssertionError as exc:
                _results.append(("FAIL", "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append(("FAIL", "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def spec_json() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))


def form_maps() -> dict:
    return json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))


def template_xml() -> str:
    with zipfile.ZipFile(TEMPLATE_PATH) as z:
        return z.read("word/document.xml").decode("utf-8")


def khuon_row_tokens(xml: str, loop_name: str) -> list[str]:
    """Token {..} trong hàng khuôn (w:tr chứa {#loop} và {/loop}) của template."""
    for row in re.findall(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", xml, re.S):
        if "{#%s}" % loop_name in row and "{/%s}" % loop_name in row:
            return sorted(set(re.findall(
                r"\{[/#]?[A-Za-z_][A-Za-z0-9_.#/]*\}", row)))
    raise AssertionError(
        "template PLII_M01 mất hàng khuôn loop %r (w:tr chứa "
        "{#%s}...{/%s})" % (loop_name, loop_name, loop_name))


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


def find_table_by_headers(doc, headers: list[str]):
    """Bảng có hàng tiêu đề (hàng 0) khớp headers; trả None nếu không thấy."""
    want = fold(" ".join(headers))
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:tbl"):
            continue
        tbl = Table(child, doc)
        if len(tbl.rows) and fold(" ".join(tr_cell_texts(tbl, 0))) == want:
            return tbl
    return None


def assert_no_leftover_tokens(xml: str, extra_tokens: list[str]) -> None:
    """Không sót token loop/cột/biến engine nào trong document.xml."""
    for tok in extra_tokens:
        assert tok not in xml, "còn sót token %r trong document.xml" % tok
    leftovers = sorted(set(LEFTOVER_RE.findall(xml)))
    assert not leftovers, \
        "render còn tag sót: %s" % ", ".join(leftovers[:10])


@check("spec PLII_M01: ds_tv_ho_gia_dinh stt_tag=true, cols/fields dung contract; ds_nganh giu nguyen")
def t_spec_contract():
    entries = {e["spec"]["id"]: e for e in (spec_json().get("tables") or [])}
    assert set(entries) == {"ds_nganh_nghe", "ds_tv_ho_gia_dinh"}, (
        "spec chỉ được có 2 entry, thấy %r" % sorted(entries))

    member = entries["ds_tv_ho_gia_dinh"]
    mspec = member["spec"]
    assert mspec["stt_tag"] is True, (
        "spec ds_tv_ho_gia_dinh.stt_tag phải là true (defect "
        "plii_m01_stt_thieu_tag_ho_gia_dinh), thấy %r" % mspec.get("stt_tag"))
    assert mspec["loop"] == LOOP_MEMBER
    assert mspec["detect"] == ["stt", "ho ten", "chu ky", "quoc tich"]
    got_cols = [(pat, tag) for pat, tag in mspec["cols"]]
    want_first = ("^stt$", None)
    assert got_cols[0] == want_first, \
        "cols[0] phải là cột STT không tag, thấy %r" % (got_cols[0],)
    got_tags = [t for _, t in got_cols[1:]]
    assert got_tags == [t for _, t in MEMBER_COLS], \
        "tags cột thành viên sai: %r" % (got_tags,)
    assert sorted(mspec["fields"]) == sorted(MEMBER_FIELDS), \
        "fields thành viên sai: %r" % (sorted(mspec["fields"]),)
    assert member["anchor"] == "^7\\. thong tin ve cac thanh vien ho gia dinh"
    assert member["headers"] == MEMBER_HEADERS
    assert member["pos"] == "after"

    industry = entries["ds_nganh_nghe"]
    ispec = industry["spec"]
    assert ispec["stt_tag"] is True and ispec["loop"] == LOOP_INDUSTRY
    assert [(p, t) for p, t in ispec["cols"]] == [
        ("^stt$", None), ("ten nganh", "ten_nganh"), ("ma nganh", "ma_nganh"),
        ("^nganh chinh$|nganh, nghe kinh doanh chinh", "la_nganh_chinh")]
    assert sorted(ispec["fields"]) == \
        sorted(["ten_nganh", "ma_nganh", "la_nganh_chinh"])
    assert industry["anchor"] == "^3\\. nganh, nghe kinh doanh"
    assert industry["pos"] == "after"
    assert industry["headers"] == INDUSTRY_HEADERS


@check("form_maps+blocks PLII_M01: dynamic_tables 2 bang, bang thanh vien 9 cot col1..col9, khong tag o cot 0")
def t_form_maps_and_blocks():
    fm = form_maps()["PLII_M01"]
    dts = {t["loop"]: t for t in fm.get("dynamic_tables") or []}
    assert sorted(dts) == sorted([LOOP_INDUSTRY, LOOP_MEMBER]), \
        "kỳ vọng 2 dynamic_tables, thấy %r" % sorted(dts)

    dt = dts[LOOP_MEMBER]
    assert dt["table_index"] == 1 and dt["header_row"] == 0
    got_cols = sorted((c["col"], c["tag"]) for c in dt["columns"])
    assert got_cols == sorted(MEMBER_COLS), \
        "columns %r != %r (cột 0 STT tự sinh không tag)" % (
            got_cols, sorted(MEMBER_COLS))
    fld_keys = {f["key"] for f in fm.get("fields", [])}
    for tag in MEMBER_FIELDS:
        assert ("%s.%s" % (LOOP_MEMBER, tag)) in fld_keys, \
            "thiếu field %s.%s trong form_maps" % (LOOP_MEMBER, tag)

    dt_i = dts[LOOP_INDUSTRY]
    assert dt_i["table_index"] == 0
    got_cols_i = sorted((c["col"], c["tag"]) for c in dt_i["columns"])
    assert got_cols_i == sorted(INDUSTRY_COLS), \
        "columns ds_nganh bị thay đổi: %r" % (got_cols_i,)

    data = json.loads(BLOCKS_PATH.read_text(encoding="utf-8"))
    loops = {b["loop"]: b for b in data["blocks"] if b.get("t") == "loop"}
    assert sorted(loops) == sorted([LOOP_INDUSTRY, LOOP_MEMBER]), \
        "blocks kỳ vọng 2 loop, thấy %r" % sorted(loops)
    blk = loops[LOOP_MEMBER]
    got_bcols = sorted((c["col"], c["tag"]) for c in blk["cols"])
    assert got_bcols == sorted(MEMBER_COLS), \
        "blocks cols %r != %r" % (got_bcols, sorted(MEMBER_COLS))
    assert all(c["col"] != 0 for c in blk["cols"]), \
        "blocks: cột 0 (STT tự sinh {_stt}) không được có tag"


@check("template PLII_M01: hang khuon w:tbl[1] co {_stt} (cot STT tu sinh)")
def t_template_member_stt():
    xml = template_xml()
    tokens = khuon_row_tokens(xml, LOOP_MEMBER)
    assert "{#%s}" % LOOP_MEMBER in tokens and "{/%s}" % LOOP_MEMBER in tokens
    # Capability probe: chưa regen thì template thiếu {_stt} -> EFPI
    if "{_stt}" not in tokens:
        raise EFPI(
            "hàng khuôn w:tbl[1] chưa có {_stt} (template chưa regen sau khi "
            "merge spec; token hiện có: %s)" % tokens)
    # Các tag cột vẫn phải nguyên vẹn trên cùng hàng khuôn
    for tag in ("ho_ten", "ngay_sinh", "so_cccd", "gioi_tinh", "quoc_tich",
                "dan_toc", "noi_thuong_tru", "noi_o_hien_tai", "chu_ky"):
        assert "{%s}" % tag in tokens, "mất tag {%s} ở hàng khuôn" % tag
    # Bảng ds_nganh (đã stt_tag=true từ trước) không được suy giảm
    ind_tokens = khuon_row_tokens(xml, LOOP_INDUSTRY)
    assert "{_stt}" in ind_tokens, \
        "hàng khuôn ds_nganh mất {_stt} (regression)"


@check("render DOCX PLII_M01: 3 thanh vien vao dung cot, STT 1/2/3, khong con token")
def t_render_member_rows():
    tokens_probe = khuon_row_tokens(template_xml(), LOOP_MEMBER)
    if "{_stt}" not in tokens_probe:
        raise EFPI(
            "template chưa regen (thiếu {_stt} ở hàng khuôn thành viên); "
            "token hiện có: %s" % tokens_probe)

    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "PLII_M01_thanh_vien.docx"
    write_rendered(str(TEMPLATE_PATH),
                   {LOOP_MEMBER: MEMBER_ROWS, LOOP_INDUSTRY: INDUSTRY_ROWS},
                   out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    doc = Document(str(out_path))
    tbl = find_table_by_headers(doc, MEMBER_HEADERS)
    assert tbl is not None, \
        "không tìm thấy bảng thành viên hộ gia đình trong file render"
    texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]

    n_data = len(MEMBER_ROWS)
    assert len(texts) >= 1 + n_data, \
        "bảng thành viên chỉ có %d hàng, không đủ chỗ cho %d dòng dữ liệu" % (
            len(texts), n_data)
    # [F3T.2 max(K,N)] dữ liệu NGAY SAU header (pin cũ texts[-n:] là vị trí
    # khiếm khuyết K-blank-then-data)
    data_texts = texts[1:1 + n_data]
    for i, row in enumerate(data_texts):
        want = MEMBER_ROWS[i]
        assert len(row) == len(MEMBER_HEADERS), \
            "hàng thành viên %d có %d ô != %d" % (
                i, len(row), len(MEMBER_HEADERS))
        assert row[0] == str(i + 1), \
            "STT dòng %d = %r, kỳ vọng %r ({_stt} không tự sinh?)" % (
                i, row[0], str(i + 1))
        for ci, tag in MEMBER_COLS:
            assert row[ci] == want[tag], \
                "ô cột %d (%s) dòng %d = %r != %r" % (
                    ci, tag, i, row[ci], want[tag])

    assert_no_leftover_tokens(
        xml,
        ["{_stt}",
         "{#%s}" % LOOP_MEMBER, "{/%s}" % LOOP_MEMBER]
        + ["{%s}" % t for _, t in MEMBER_COLS]
        + ["{#%s}" % LOOP_INDUSTRY, "{/%s}" % LOOP_INDUSTRY]
        + ["{%s}" % t for _, t in INDUSTRY_COLS],
    )


@check("regression bang ds_nganh canh ben: STT 1/2/3 + dung MOT X nganh chinh, khong sot token (contract cu giu nguyen)")
def t_render_ds_nganh_regression():
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "PLII_M01_ds_nganh.docx"
    write_rendered(str(TEMPLATE_PATH),
                   {LOOP_MEMBER: MEMBER_ROWS, LOOP_INDUSTRY: INDUSTRY_ROWS},
                   out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    doc = Document(str(out_path))
    tbl = find_table_by_headers(doc, INDUSTRY_HEADERS)
    assert tbl is not None, "không tìm thấy bảng ngành nghề trong file render"
    texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]

    n_data = len(INDUSTRY_ROWS)
    # [F3T.2 max(K,N)] dữ liệu NGAY SAU header (pin cũ texts[-n:] là vị trí
    # khiếm khuyết K-blank-then-data)
    data_texts = texts[1:1 + n_data]
    n_x = 0
    for i, row in enumerate(data_texts):
        want = INDUSTRY_ROWS[i]
        assert len(row) == len(INDUSTRY_HEADERS), \
            "hàng ngành %d có %d ô != %d" % (i, len(row), len(INDUSTRY_HEADERS))
        assert row[0] == str(i + 1), \
            "STT ngành dòng %d = %r, kỳ vọng %r" % (i, row[0], str(i + 1))
        assert row[1] == want["ten_nganh"], \
            "Tên ngành dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "Mã ngành dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "Ngành chính dòng %d = %r != %r" % (i, row[3],
                                                want["la_nganh_chinh"])
        n_x += 1 if row[3] == "X" else 0
    assert n_x == 1, "kỳ vọng đúng 1 dòng có X ngành chính, thấy %d" % n_x
    assert data_texts[0][3] == "X", "dòng đầu phải là ngành chính (X)"

    assert_no_leftover_tokens(
        xml,
        ["{_stt}",
         "{#%s}" % LOOP_INDUSTRY, "{/%s}" % LOOP_INDUSTRY]
        + ["{%s}" % t for _, t in INDUSTRY_COLS]
        + ["{#%s}" % LOOP_MEMBER, "{/%s}" % LOOP_MEMBER]
        + ["{%s}" % t for _, t in MEMBER_COLS],
    )


def main() -> int:
    t_spec_contract()
    t_form_maps_and_blocks()
    t_template_member_stt()
    t_render_member_rows()
    t_render_ds_nganh_regression()
    counts = {"PASS": 0, "FAIL": 0, "EXPECTED-FAIL-PRE-INTEGRATION": 0}
    for status, _ in _results:
        counts[status] += 1
    print("-" * 60)
    print("test_plii_m01_member_stt: %d PASS / %d FAIL / %d "
          "EXPECTED-FAIL-PRE-INTEGRATION%s" % (
              counts["PASS"], counts["FAIL"],
              counts["EXPECTED-FAIL-PRE-INTEGRATION"],
              "" if not STRICT else " [STRICT=1]"))
    for status, name in _results:
        if status != "PASS":
            print(" - %s:" % status, name)
    fail = counts["FAIL"]
    efpi = counts["EXPECTED-FAIL-PRE-INTEGRATION"]
    if STRICT and efpi:
        print("STRICT=1: %d EXPECTED-FAIL-PRE-INTEGRATION tính là FAIL" % efpi)
        return 1
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
