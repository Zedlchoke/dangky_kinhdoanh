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
3. P1-B (lane p1/b-pli-m72) — M72 5 occurrence theo loại hình: spec
   tools/form_specs/change/PLI_M72.json khai báo occurrences contract
   (ds_nganh_dntn/tnhh_1tv/tnhh_2tv/ctcp/dhdn, sync_group=ds_nganh_pli_m72).
   ĐÃ integrate đủ 5 lưới; từ P1.2 Option D template bọc từng biến thể bằng
   marker điều kiện {?loai_hinh_*} — dữ liệu render M72 phải bật ĐỦ 5 flag
   (M72_SECTION_FLAGS) để giữ cả 5 bảng như trước khi có vùng điều kiện.
   Isolation từng biến thể (chỉ xuất 1 loại hình) được cover riêng bởi
   tools/test_m72_conditional_export.py; verifier cấu trúc template:
   tools/census/p1_b_verify_m72.py.

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
# Loop KHÔNG thuộc nhóm ngành nhưng đã đăng ký có chủ đích bởi lane domain
# khác (R3B1 people/ownership 2026-08-27, specs core/PLI_M02.json +
# change/PLI_M12.json + suite test_r3b1_people_specs): exact-set của từng form
# vẫn bị khóa chặt ở assert_loop_contract.
EXTRA_LOOPS = {
    "PLI_M02": {"ds_nddpl_uy_quyen_chu_so_huu"},
    "PLI_M12": {"ds_ndd_uy_quyen_sau_thay_doi"},
    # [P2 pin sync 2026-09-03] P2 rebuild thêm 4 lưới thành viên/cổ đông
    # (nested-grid) vào PLI_M72: 5 lưới ngành + 4 lưới thành viên = 9 loop.
    "PLI_M72": {"ds_thanh_vien_tnhh_2tv", "ds_co_dong_sang_lap_ctcp",
                "ds_co_dong_nuoc_ngoai_ctcp", "ds_thanh_vien_hop_danh_dhdn"},
    "PLI_M15": set(),   # M15 không nằm trong EXPECTED_CONTRACTS; chỉ để tra cứu rõ ràng
}

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
    # P1-B: SAU integration M72 có đủ 5 loop occurrence theo loại hình —
    # gán sau khi M72_OCCURRENCE_LOOPS được định nghĩa (xem dưới).
    "PLI_M72": None,
}

# ---------------------------------------------------------------------------
# P1-B: contract 5 occurrence PLI_M72 (spec tools/form_specs/change/PLI_M72.json)
# ---------------------------------------------------------------------------
M72_SPEC_PATH = ROOT / "tools" / "form_specs" / "change" / "PLI_M72.json"
M72_OCCURRENCE_IDS = ["ds_nganh_dntn", "ds_nganh_tnhh_1tv", "ds_nganh_tnhh_2tv",
                      "ds_nganh_ctcp", "ds_nganh_dhdn"]
M72_SYNC_GROUP = "ds_nganh_pli_m72"
M72_MATCH_HEADING = "5. Ngành, nghề kinh doanh"
# P1.2 Option D: 5 flag điều kiện bọc 5 biến thể loại hình trên template
# (section_cond trong spec M72). Bật đủ 'X' khi render để giữ cả 5 bảng.
M72_SECTION_FLAGS = ["loai_hinh_dntn", "loai_hinh_tnhh_1tv",
                     "loai_hinh_tnhh_2tv", "loai_hinh_ctcp",
                     "loai_hinh_dhdn"]
HDR_NGANH = ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"]
M72_OCCURRENCE_LOOPS = [(oid, CONTRACT_DS_NGANH, HDR_NGANH)
                        for oid in M72_OCCURRENCE_IDS]
EXPECTED_CONTRACTS["PLI_M72"] = M72_OCCURRENCE_LOOPS

# Dữ liệu render RIÊNG BIỆT từng occurrence (số dòng + vị trí X khác nhau)
# để phát hiện dữ liệu trượt sang bảng của loại hình khác:
M72_RENDER_DATASETS = {
    # DNTN: 3 dòng, X ở dòng 1
    "ds_nganh_dntn": [dict(r, la_nganh_chinh="X" if i == 0 else "")
                      for i, r in enumerate(VSIC_ROWS)],
    # TNHH 1TV: 2 dòng, X ở dòng cuối
    "ds_nganh_tnhh_1tv": [dict(VSIC_ROWS[1], la_nganh_chinh=""),
                          dict(VSIC_ROWS[2], la_nganh_chinh="X")],
    # TNHH 2TV+: 1 dòng duy nhất, có X
    "ds_nganh_tnhh_2tv": [dict(VSIC_ROWS[2], la_nganh_chinh="X")],
    # CTCP: 2 dòng đảo thứ tự VSIC, X ở dòng 2
    "ds_nganh_ctcp": [dict(VSIC_ROWS[2], la_nganh_chinh=""),
                      dict(VSIC_ROWS[0], la_nganh_chinh="X")],
    # DHDN: 3 dòng trộn, X ở dòng giữa
    "ds_nganh_dhdn": [dict(VSIC_ROWS[1], la_nganh_chinh=""),
                      dict(VSIC_ROWS[0], la_nganh_chinh="X"),
                      dict(VSIC_ROWS[2], la_nganh_chinh="")],
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
    # [Lead sync sau regen R3B1] khóa ĐÚNG TẬP tên loop thay vì chỉ đếm:
    # lane domain khác (R3B1 people/ownership) thêm loop người đã đăng ký
    # (EXTRA_LOOPS dưới) — exact-set giữ nguyên độ cứng, không nới thành
    # "ít nhất N vòng".
    want_set = set(EXTRA_LOOPS.get(fid, set())) | {
        name for name, _cols, _hdr in contract}
    assert set(loops) == want_set, \
        "%s: tập block loop %r != kỳ vọng %r" % (
            fid, sorted(loops), sorted(want_set))
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
    # [F3T.2 max(K,N)] dữ liệu ngay sau header (pin cũ texts[-n:] là vị trí
    # khiếm khuyết K-blank-then-data)
    data_texts = texts[1:1 + len(DS_NGANH_3ROWS)]
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


@check("render DOCX ds_nganh 3 dong (STT 1/2/3 + dung mot dau X) cho 5 mau")
def t_render_ds_nganh_forms():
    # PLI_M72 khong con loop ds_nganh don nhat sau P1: render cua no duoc
    # cover SAT HON boi t_m72_five_grids_render (5 occurrence, dataset rieng,
    # kiem tra tron du lieu giua cac loai hinh).
    for fid in ["PLI_M17", "PLI_M19", "PLI_M21", "PLI_M23", "PLI_M25"]:
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
        # [F3T.2 max(K,N)] dữ liệu ngay sau header (pin cũ texts[-n:] là vị
        # trí khiếm khuyết K-blank-then-data)
        data_texts = texts[1:1 + n]
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


@check("M72 spec: khai bao dung 5 occurrence (id/nth/sync_group/end_markers)")
def t_m72_spec_occurrences():
    """Hợp đồng occurrences P1 trong spec M72 — PASS ngay trước integration."""
    spec = json.loads(M72_SPEC_PATH.read_text(encoding="utf-8-sig"))
    entries = spec.get("tables") or []
    # [P2 pin sync 2026-09-03] spec M72 giờ có 5 table entry: entry 0 là entry
    # ngành (5 occurrence), entries 1..4 là 4 entry nested-grid thành viên/
    # cổ đông do lane P2 rebuild (mỗi entry 1 occurrence, sync_group null).
    assert len(entries) == 5, \
        "M72 spec: kỳ vọng 5 table entry (1 ngành + 4 thành viên P2), thấy %d" \
        % len(entries)
    entry = entries[0]
    occs = entry.get("occurrences") or []
    assert len(occs) == 5, "M72 spec: kỳ vọng 5 occurrences, thấy %d" % len(occs)
    assert [o["occurrence_id"] for o in occs] == M72_OCCURRENCE_IDS, \
        "M72 spec: occurrence_id sai: %s" % [o.get("occurrence_id") for o in occs]
    for k, occ in enumerate(occs, 1):
        assert occ["nth"] == k, \
            "%s: nth=%r != %d (thứ tự tài liệu)" % (occ["occurrence_id"],
                                                    occ["nth"], k)
        assert occ["match_heading"] == M72_MATCH_HEADING, \
            "%s: match_heading %r != text đã verify %r" % (
                occ["occurrence_id"], occ["match_heading"], M72_MATCH_HEADING)
        assert occ["sync_group"] == M72_SYNC_GROUP, \
            "%s: sync_group %r != %r" % (occ["occurrence_id"],
                                         occ["sync_group"], M72_SYNC_GROUP)
        assert isinstance(occ.get("end_markers"), list) and occ["end_markers"], \
            "%s: thiếu end_markers" % occ["occurrence_id"]
        for pat in occ["end_markers"]:
            re.compile(pat)  # regex hợp lệ
    # [P2 pin sync 2026-09-03] pin 4 entry thành viên: nested-grid, id = tên
    # loop, đúng tập/thứ tự 4 lưới P2 theo biến thể.
    member_ids = ["ds_thanh_vien_tnhh_2tv", "ds_co_dong_sang_lap_ctcp",
                  "ds_co_dong_nuoc_ngoai_ctcp", "ds_thanh_vien_hop_danh_dhdn"]
    got_member = [e["occurrences"][0]["occurrence_id"] for e in entries[1:]]
    assert got_member == member_ids, \
        "M72 spec: entry thành viên sai %s != %s" % (got_member, member_ids)
    for e in entries[1:]:
        assert e.get("spec", {}).get("kind") == "nested-grid", \
            "M72 spec %s: kind phải nested-grid" % e["occurrences"][0]["occurrence_id"]
        assert len(e.get("occurrences") or []) == 1, \
            "M72 spec: entry thành viên kỳ vọng 1 occurrence"
        assert e["occurrences"][0]["sync_group"] is None, \
            "M72 spec: sync_group entry thành viên phải null"
    # cấu hình bảng gốc phải được giữ nguyên qua lần chuyển sang occurrences
    assert entry["spec"]["loop"] == "ds_nganh"
    assert entry["pos"] == "after" and entry["no_default_drops"] is True
    assert entry["headers"] == HDR_NGANH
    col_tags = [c[1] for c in entry["spec"]["cols"]]
    assert sorted(t for t in col_tags if t) == \
        ["la_nganh_chinh", "ma_nganh", "ten_nganh"], \
        "M72 spec: cols sai tag %r" % col_tags
    assert col_tags.count(None) == 1, \
        "M72 spec: cần đúng 1 cột không tag (STT), thấy %d" % col_tags.count(None)


def assert_m72_five_loop_contract(blocks: dict, form_maps: dict) -> None:
    """Contract SAU INTEGRATE: blocks+form_maps PLI_M72 có đủ 5 loop occurrence,
    mỗi loop 4 cột STT|ten_nganh|ma_nganh|la_nganh_chinh.
    [P2 pin sync 2026-09-03] exact-set mở rộng: +4 lưới thành viên/cổ đông
    (nested-grid P2) -> 9 loop block trên PLI_M72; contract 4 cột vẫn áp cho
    đúng 5 occurrence ngành."""
    loops = {b["loop"]: b for b in blocks["blocks"] if b.get("t") == "loop"}
    want_loops = sorted(EXTRA_LOOPS["PLI_M72"] | set(M72_OCCURRENCE_IDS))
    assert sorted(loops) == want_loops, \
        "PLI_M72: kỳ vọng đúng 9 loop (5 ngành + 4 thành viên P2) %s, " \
        "thấy %d loop %s" % (want_loops, len(loops), sorted(loops))
    fm_dts = {t["loop"]: t for t in (form_maps["PLI_M72"].get("dynamic_tables")
                                     or [])}
    doc = Document(str(TEMPLATES_DIR / "PLI_M72.docx"))
    tables = body_tables(doc)
    seen_indexes = set()
    for name, cols_want, headers_want in M72_OCCURRENCE_LOOPS:
        blk = loops[name]
        got_cols = sorted((c["col"], c["tag"]) for c in blk["cols"])
        want_cols = sorted((c, t) for c, t in cols_want if t is not None)
        assert got_cols == want_cols, \
            "PLI_M72/%s cols %r != %r" % (name, got_cols, want_cols)
        assert all(c["col"] != 0 for c in blk["cols"]), \
            "PLI_M72/%s: cột 0 (STT {_stt}) không được gắn tag" % name
        hdr_cells = blk["rows"][blk["headerRows"][0]]["cells"]
        got_hdr = [cell_runs_text(c).strip() for c in hdr_cells]
        assert got_hdr == headers_want, \
            "PLI_M72/%s header %r != %r" % (name, got_hdr, headers_want)
        for ri, row in enumerate(blk["rows"]):
            assert len(row["cells"]) == 4, \
                "PLI_M72/%s rows[%d] có %d ô != 4" % (name, ri, len(row["cells"]))
        assert blk["blankRows"] >= 1, \
            "PLI_M72/%s: cần >=1 hàng trắng để in" % name
        dt = fm_dts.get(name)
        assert dt is not None, \
            "PLI_M72: dynamic_tables thiếu khai báo cho loop %r" % name
        ti = dt["table_index"]
        assert ti not in seen_indexes, \
            "PLI_M72/%s: table_index %d bị trùng giữa các occurrence" % (name, ti)
        seen_indexes.add(ti)
        tbl = tables[ti]
        total = len(blk["rows"]) + blk["blankRows"] + 1
        assert total == len(tbl._tbl.tr_lst), \
            "PLI_M72/%s rows(%d)+blank(%d)+khuôn(1)=%d != %d hàng template" % (
                name, len(blk["rows"]), blk["blankRows"], total,
                len(tbl._tbl.tr_lst))
        fld_keys = {f["key"] for f in form_maps["PLI_M72"].get("fields", [])}
        for _, tag in cols_want:
            if tag is not None:
                assert ("%s.%s" % (name, tag)) in fld_keys, \
                    "PLI_M72: thiếu field %s.%s trong form_maps" % (name, tag)


@check("M72 blocks+form_maps: 5 loop occurrence, moi loop 4 cot")
def t_m72_five_grids_contract():
    form_maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    assert "PLI_M72" in form_maps, "thiếu PLI_M72 trong form_maps"
    data = json.loads((BLOCKS_DIR / "PLI_M72.json").read_text(encoding="utf-8"))
    assert_m72_five_loop_contract(data, form_maps)


def industry_tables_in(doc):
    """Các bảng ngành (đúng hàng tiêu đề STT|Tên ngành|Mã ngành|Ngành chính),
    theo thứ tự xuất hiện trong body."""
    want = fold(" ".join(HDR_NGANH))
    out = []
    for tbl in body_tables(doc):
        for ri in range(min(3, len(tbl.rows))):
            cells = tr_cell_texts(tbl, ri)
            if cells and fold(" ".join(cells)) == want:
                out.append(tbl)
                break
    return out


@check("M72 render DOCX: dung 5 bang nganh theo loai hinh, STT 1..n, "
       "moi bang dung mot X")
def t_m72_five_grids_render():
    out_path = OUT_DIR / "PLI_M72_nam_loai_hinh.docx"
    # P1.2 Option D: bật đủ 5 flag loai_hinh_* để giữ cả 5 bảng (như cũ);
    # assertion số bảng/STT/X KHÔNG đổi.
    data = dict(M72_RENDER_DATASETS)
    data.update({flag: "X" for flag in M72_SECTION_FLAGS})
    write_rendered(TEMPLATES_DIR / "PLI_M72.docx", data, out_path)
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    doc = Document(str(out_path))
    tables = industry_tables_in(doc)
    assert len(tables) == 5, \
        "PLI_M72 render: kỳ vọng 5 bảng ngành (DNTN/TNHH1TV/TNHH2TV/CTCP/DHDN), " \
        "thấy %d — generator chưa dựng đủ 5 vùng loại hình" % len(tables)

    for k, (name, _cols, _hdr) in enumerate(M72_OCCURRENCE_LOOPS):
        dataset = M72_RENDER_DATASETS[name]
        texts = [tr_cell_texts(tables[k], ri)
                 for ri in range(len(tables[k].rows))]
        # [F3T.2 max(K,N)] dữ liệu ngay sau header (pin cũ texts[-n:] là vị
        # trí khiếm khuyết K-blank-then-data)
        data_texts = texts[1:1 + len(dataset)]
        assert len(data_texts) == len(dataset), \
            "PLI_M72/%s: bảng %d chỉ đọc được %d hàng dữ liệu != %d" % (
                name, k, len(data_texts), len(dataset))
        for i, row in enumerate(data_texts):
            want = dataset[i]
            assert len(row) == 4, \
                "PLI_M72/%s: hàng %d có %d ô != 4" % (name, i, len(row))
            assert row[0] == str(i + 1), \
                "PLI_M72/%s: STT dòng %d = %r, kỳ vọng %d" % (
                    name, i, row[0], i + 1)
            assert row[1] == want["ten_nganh"], \
                "PLI_M72/%s: Tên ngành dòng %d = %r != %r" % (
                    name, i, row[1], want["ten_nganh"])
            assert row[2] == want["ma_nganh"], \
                "PLI_M72/%s: Mã ngành dòng %d = %r != %r" % (
                    name, i, row[2], want["ma_nganh"])
            assert row[3] == want["la_nganh_chinh"], \
                "PLI_M72/%s: Ngành chính dòng %d = %r != %r" % (
                    name, i, row[3], want["la_nganh_chinh"])
        n_x = sum(1 for r in data_texts if r[3] == "X")
        assert n_x == 1, \
            "PLI_M72/%s: kỳ vọng đúng 1 X ngành chính, thấy %d" % (name, n_x)

    for tok in ["{#%s}" % n for n in M72_OCCURRENCE_IDS] + \
               ["{/%s}" % n for n in M72_OCCURRENCE_IDS] + \
               ["{ten_nganh}", "{ma_nganh}", "{la_nganh_chinh}", "{_stt}"]:
        assert tok not in xml, \
            "PLI_M72: còn sót token %r trong document.xml sau render" % tok


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_all_contracts()
    t_render_ds_nganh_forms()
    t_render_m12_three_loops()
    t_m72_spec_occurrences()
    t_m72_five_grids_contract()
    t_m72_five_grids_render()
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
