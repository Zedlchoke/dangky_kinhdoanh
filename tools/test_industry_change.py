# -*- coding: utf-8 -*-
"""Kiểm tra Wave 2B (industry-change): 7 mẫu thay đổi PLI_M12/M17/M19/M21/M23/
M25/M72 có lưới ngành nghề tái dựng đúng và render DOCX đúng bảng/cột.

Phạm vi từng mẫu:
1. Blocks app/data/blocks/<id>.json: block loop đúng tên + cols zero-based
   theo row contract của từng loop:
   - PLI_M12: BA loop RIÊNG, KHÔNG gộp vào ds_nganh (PLAN.md Agent 2B):
     * nganh_bo_sung          = STT{_stt} | ten_nganh | ma_nganh | la_nganh_chinh
     * nganh_xoa_bo           = STT{_stt} | ten_nganh | ma_nganh | ghi_chu
       (cột 4 template là "Ghi chú" — KHÔNG có cột ngành chính)
     * nganh_sua_doi_chi_tiet = STT{_stt} | ten_nganh | ma_nganh | la_nganh_chinh
   - PLI_M17/M19/M21/M23/M25/M72: 1 loop canonical ds_nganh
     = STT{_stt} | ten_nganh | ma_nganh | la_nganh_chinh.
   - form_maps.json khai báo dynamic_tables tương ứng.
2. Render DOCX bằng tools/docx_render.write_rendered với dữ liệu mẫu dùng mã
   VSIC THẬT (app/data/nganh_vsic.json):
   - ds_nganh (mẫu có): 3 dòng chuẩn STT tự sinh 1/2/3, dòng đầu đánh X
     ngành chính;
   - riêng PLI_M12: render thêm cả BA loop bo_sung/xoa_bo/sua_doi -> assert
     mỗi giá trị nằm vào ĐÚNG bảng/ô cột tương ứng (so text từng ô), không
     sót token {#loop}/{tag}/{_stt} trong document.xml.

File test thuần Python, exit code 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 tools/test_industry_change.py
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

BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
TEMPLATES_DIR = ROOT / "app" / "templates"
OUT_DIR = ROOT / "generated_ho_so" / "_test_industry_change"

# Mã VSIC thật từ app/data/nganh_vsic.json (đối chiếu đầu file test)
VSIC_ROWS = [
    {"ma_nganh": "0111", "ten_nganh": "Trồng lúa"},
    {"ma_nganh": "4751",
     "ten_nganh": "Bán lẻ vải, len, sợi, chỉ khâu và hàng dệt khác "
                  "trong các cửa hàng chuyên doanh"},
    {"ma_nganh": "6201", "ten_nganh": "Lập trình máy vi tính"},
]

# Row contract từng mẫu: loop -> [(col, tag)], None tag = cột STT engine
CONTRACT_DS_NGANH = [(0, None), (1, "ten_nganh"), (2, "ma_nganh"),
                     (3, "la_nganh_chinh")]
# PLI_M12 mục 2 (bỏ ngành): cột 4 template là "Ghi chú", KHÔNG có ngành chính
CONTRACT_XOA_BO = [(0, None), (1, "ten_nganh"), (2, "ma_nganh"), (3, "ghi_chu")]
EXPECTED_CONTRACTS = {
    "PLI_M12": [
        ("nganh_bo_sung", CONTRACT_DS_NGANH,
         ["STT", "Tên ngành, nghề kinh doanh được bổ sung", "Mã ngành",
          "Ngành, nghề kinh doanh chính"]),
        ("nganh_xoa_bo", CONTRACT_XOA_BO,
         ["STT", "Tên ngành, nghề kinh doanh được bỏ khỏi danh sách đã đăng ký",
          "Mã ngành", "Ghi chú"]),
        ("nganh_sua_doi_chi_tiet", CONTRACT_DS_NGANH,
         ["STT", "Tên ngành, nghề kinh doanh được sửa đổi chi tiết", "Mã ngành",
          "Ngành, nghề kinh doanh chính"]),
    ],
    "PLI_M17": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
    "PLI_M19": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
    "PLI_M21": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
    "PLI_M23": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
    "PLI_M25": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
    "PLI_M72": [("ds_nganh", CONTRACT_DS_NGANH,
                 ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"])],
}

# Dữ liệu render mẫu
DS_NGANH_3ROWS = [dict(r, la_nganh_chinh="X" if i == 0 else "")
                  for i, r in enumerate(VSIC_ROWS)]

BO_SUNG_ROWS = [dict(r, la_nganh_chinh="X" if i == 0 else "")
                for i, r in enumerate(VSIC_ROWS)]
XOA_BO_ROWS = [
    {"ma_nganh": VSIC_ROWS[2]["ma_nganh"], "ten_nganh": VSIC_ROWS[2]["ten_nganh"],
     "ghi_chu": "Ngừng kinh doanh từ 01/01/2027"},
    {"ma_nganh": VSIC_ROWS[1]["ma_nganh"], "ten_nganh": VSIC_ROWS[1]["ten_nganh"],
     "ghi_chu": ""},
]
SUA_DOI_ROWS = [
    {"ma_nganh": VSIC_ROWS[1]["ma_nganh"], "ten_nganh": VSIC_ROWS[1]["ten_nganh"],
     "la_nganh_chinh": ""},
    {"ma_nganh": VSIC_ROWS[0]["ma_nganh"], "ten_nganh": VSIC_ROWS[0]["ten_nganh"],
     "la_nganh_chinh": "X"},
]

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(*args):
            try:
                fn(*args)
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
    return [Table(child, doc) for child in doc.element.body.iterchildren()
            if child.tag == qn("w:tbl")]


def find_table_by_headers(doc, headers: list[str]):
    """Tìm bảng có HÀNG TIÊU ĐỀ (bỏ qua hàng trắng/khác trước đó) khớp headers."""
    want = fold(" ".join(headers))
    for tbl in body_tables(doc):
        for ri in range(min(3, len(tbl.rows))):
            cells = tr_cell_texts(tbl, ri)
            if cells and fold(" ".join(cells)) == want:
                return tbl
    return None


def assert_loop_contract(fid: str, form_maps: dict) -> None:
    data = json.loads((BLOCKS_DIR / ("%s.json" % fid)).read_text(encoding="utf-8"))
    loops = {b["loop"]: b for b in data["blocks"] if b.get("t") == "loop"}
    contract = EXPECTED_CONTRACTS[fid]
    assert len(loops) == len(contract), \
        "%s: kỳ vọng %d block loop, thấy %d (%s)" % (
            fid, len(contract), len(loops), sorted(loops))
    fm_dts = {t["loop"]: t for t in (form_maps[fid].get("dynamic_tables") or [])}
    for name, cols_want, headers_want in contract:
        assert name in loops, "%s: thiếu block loop %r" % (fid, name)
        blk = loops[name]
        got_cols = sorted((c["col"], c["tag"]) for c in blk["cols"])
        want_cols = sorted((c, t) for c, t in cols_want if t is not None)
        assert got_cols == want_cols, \
            "%s/%s cols %r != %r" % (fid, name, got_cols, want_cols)
        assert all(c["col"] != 0 for c in blk["cols"]), \
            "%s/%s: cột 0 (STT tự sinh {_stt}) không được có tag" % (fid, name)
        hdr_cells = blk["rows"][blk["headerRows"][0]]["cells"]
        got_hdr = [cell_runs_text(c).strip() for c in hdr_cells]
        assert got_hdr == headers_want, \
            "%s/%s header %r != %r" % (fid, name, got_hdr, headers_want)
        # mọi hàng đều đủ số ô như header (grid không vỡ)
        for ri, row in enumerate(blk["rows"]):
            assert len(row["cells"]) == len(headers_want), \
                "%s/%s rows[%d] có %d ô != %d" % (
                    fid, name, ri, len(row["cells"]), len(headers_want))
        # blankRows hợp lý + bảo toàn số hàng so với template
        assert blk["blankRows"] >= 1, "%s/%s: cần >=1 hàng trắng để in" % (fid, name)
        dt = fm_dts.get(name)
        assert dt is not None, \
            "%s: dynamic_tables thiếu khai báo cho loop %r" % (fid, name)
        doc = Document(str(TEMPLATES_DIR / ("%s.docx" % fid)))
        tables = body_tables(doc)
        tbl = tables[dt["table_index"]]
        n_tr = len(tbl._tbl.tr_lst)
        total = len(blk["rows"]) + blk["blankRows"] + 1
        assert total == n_tr, \
            "%s/%s rows(%d)+blank(%d)+khuôn(1)=%d != %d hàng template" % (
                fid, name, len(blk["rows"]), blk["blankRows"], total, n_tr)
        # fields đăng ký "<loop>.<tag>" trong form_maps
        fld_keys = {f["key"] for f in form_maps[fid].get("fields", [])}
        for _, tag in cols_want:
            if tag is not None:
                assert ("%s.%s" % (name, tag)) in fld_keys, \
                    "%s: thiếu field %s.%s trong form_maps" % (fid, name, tag)


@check("blocks+form_maps: dung row contract tung loop cho ca 7 mau")
def t_all_contracts():
    form_maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    for fid in EXPECTED_CONTRACTS:
        assert fid in form_maps, "thiếu %s trong form_maps" % fid
        assert_loop_contract(fid, form_maps)


def assert_render_ds_nganh(fid: str) -> None:
    """Render 3 dòng ds_nganh (mã VSIC thật), assert STT 1/2/3 + X đúng dòng +
    từng giá trị đúng ô cột + không sót token."""
    out_path = OUT_DIR / ("%s_ds_nganh.docx" % fid)
    write_rendered(TEMPLATES_DIR / ("%s.docx" % fid),
                   {"ds_nganh": DS_NGANH_3ROWS}, out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    hdr = EXPECTED_CONTRACTS[fid][0][2]
    doc = Document(str(out_path))
    tbl = find_table_by_headers(doc, hdr)
    assert tbl is not None, "%s: không tìm thấy bảng ngành trong file render" % fid
    texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]
    data_texts = texts[-len(DS_NGANH_3ROWS):]
    for i, row in enumerate(data_texts):
        want = DS_NGANH_3ROWS[i]
        assert len(row) == 4, "%s: hàng dữ liệu %d có %d ô != 4" % (fid, i, len(row))
        assert row[0] == str(i + 1), \
            "%s: STT dòng %d = %r, kỳ vọng %r" % (fid, i, row[0], str(i + 1))
        assert row[1] == want["ten_nganh"], \
            "%s: Tên ngành dòng %d = %r != %r" % (fid, i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "%s: Mã ngành dòng %d = %r != %r" % (fid, i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "%s: Ngành chính dòng %d = %r != %r (chỉ dòng 1 có duy nhất một X)" % (
                fid, i, row[3], want["la_nganh_chinh"])
    n_x = sum(1 for r in data_texts if r[3] == "X")
    assert n_x == 1, "%s: kỳ vọng đúng 1 dòng ngành chính X, thấy %d" % (fid, n_x)

    for tok in ("{#ds_nganh}", "{/ds_nganh}", "{ten_nganh}", "{ma_nganh}",
                "{la_nganh_chinh}", "{_stt}"):
        assert tok not in xml, "%s: còn sót token %r trong document.xml" % (fid, tok)


@check("render DOCX ds_nganh 3 dong (STT 1/2/3 + dung mot dau X) cho 6 mau")
def t_render_ds_nganh_forms():
    for fid in ["PLI_M17", "PLI_M19", "PLI_M21", "PLI_M23", "PLI_M25", "PLI_M72"]:
        assert_render_ds_nganh(fid)


@check("render PLI_M12: BA loop vao DUNG ba bang/cot tuong ung, khong sot token")
def t_render_m12_three_loops():
    out_path = OUT_DIR / "PLI_M12_ba_loop.docx"
    data = {
        "nganh_bo_sung": BO_SUNG_ROWS,
        "nganh_xoa_bo": XOA_BO_ROWS,
        "nganh_sua_doi_chi_tiet": SUA_DOI_ROWS,
    }
    write_rendered(TEMPLATES_DIR / "PLI_M12.docx", data, out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    doc = Document(str(out_path))
    contract = {name: hdr for name, _cols, hdr in EXPECTED_CONTRACTS["PLI_M12"]}
    tbl_bs = find_table_by_headers(doc, contract["nganh_bo_sung"])
    tbl_xb = find_table_by_headers(doc, contract["nganh_xoa_bo"])
    tbl_sd = find_table_by_headers(doc, contract["nganh_sua_doi_chi_tiet"])
    assert tbl_bs is not None and tbl_xb is not None and tbl_sd is not None, \
        "không tìm thấy đủ 3 bảng ngành trong PLI_M12 render"
    assert tbl_bs._tbl is not tbl_xb._tbl and tbl_xb._tbl is not tbl_sd._tbl, \
        "3 bảng phải là 3 bảng vật lý khác nhau"

    def rows_of(tbl, n):
        texts = [tr_cell_texts(tbl, ri) for ri in range(len(tbl.rows))]
        data_texts = texts[-n:]
        for row in data_texts:
            assert len(row) == 4, "hàng có %d ô != 4: %r" % (len(row), row)
        return data_texts

    # mục 1 bổ sung: 3 dòng, X ở dòng 1, giá trị đúng cột ten/ma/nganh-chinh
    bs = rows_of(tbl_bs, len(BO_SUNG_ROWS))
    for i, row in enumerate(bs):
        want = BO_SUNG_ROWS[i]
        assert row[0] == str(i + 1), "bo_sung STT %d = %r" % (i, row[0])
        assert row[1] == want["ten_nganh"], \
            "bo_sung ten dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "bo_sung ma dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "bo_sung nganh chinh dòng %d = %r != %r" % (i, row[3],
                                                        want["la_nganh_chinh"])

    # mục 2 xóa bỏ: ghi_chu phải nằm ĐÚNG CỘT 4 (Ghi chú) của bảng xóa bỏ,
    # không trượt sang bảng khác; KHÔNG có cột ngành chính trên bảng này
    xb = rows_of(tbl_xb, len(XOA_BO_ROWS))
    for i, row in enumerate(xb):
        want = XOA_BO_ROWS[i]
        assert row[0] == str(i + 1), "xoa_bo STT %d = %r" % (i, row[0])
        assert row[1] == want["ten_nganh"], \
            "xoa_bo ten dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "xoa_bo ma dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["ghi_chu"], \
            "xoa_bo ghi_chu dòng %d = %r != %r (cột 4 là Ghi chú)" % (
                i, row[3], want["ghi_chu"])

    # mục 3 sửa đổi chi tiết: 2 dòng, X ở dòng 2
    sd = rows_of(tbl_sd, len(SUA_DOI_ROWS))
    for i, row in enumerate(sd):
        want = SUA_DOI_ROWS[i]
        assert row[0] == str(i + 1), "sua_doi STT %d = %r" % (i, row[0])
        assert row[1] == want["ten_nganh"], \
            "sua_doi ten dòng %d = %r != %r" % (i, row[1], want["ten_nganh"])
        assert row[2] == want["ma_nganh"], \
            "sua_doi ma dòng %d = %r != %r" % (i, row[2], want["ma_nganh"])
        assert row[3] == want["la_nganh_chinh"], \
            "sua_doi nganh chinh dòng %d = %r != %r" % (i, row[3],
                                                        want["la_nganh_chinh"])
    assert sum(1 for r in bs if r[3] == "X") == 1, \
        "bo_sung cần đúng 1 dấu X ngành chính"
    assert sum(1 for r in sd if r[3] == "X") == 1, \
        "sua_doi cần đúng 1 dấu X ngành chính"

    # giá trị ghi_chu không lọt vào bảng khác (đúng BẢNG/CỘT)
    note = XOA_BO_ROWS[0]["ghi_chu"]
    for other_name, other_tbl in (("bo_sung", tbl_bs), ("sua_doi", tbl_sd)):
        all_txt = "".join(
            t for ri in range(len(other_tbl.rows))
            for t in tr_cell_texts(other_tbl, ri))
        assert note not in all_txt, \
            "ghi_chu bị lọt vào bảng sửa đổi %s" % other_name

    # không sót token nào của cả 3 loop
    for tok in ("{#nganh_bo_sung}", "{/nganh_bo_sung}",
                "{#nganh_xoa_bo}", "{/nganh_xoa_bo}",
                "{#nganh_sua_doi_chi_tiet}", "{/nganh_sua_doi_chi_tiet}",
                "{ten_nganh}", "{ma_nganh}", "{la_nganh_chinh}", "{ghi_chu}",
                "{_stt}"):
        assert tok not in xml, "PLI_M12: còn sót token %r trong document.xml" % tok


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_all_contracts()
    t_render_ds_nganh_forms()
    t_render_m12_three_loops()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("test_industry_change: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
