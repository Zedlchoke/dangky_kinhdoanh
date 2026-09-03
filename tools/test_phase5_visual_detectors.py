# -*- coding: utf-8 -*-
"""test_phase5_visual_detectors.py — unit tests cho bộ detector Phase 5R0.

Mỗi detector được test 2 chiều trên bằng chứng TỔNG HỢP (docx/pdf dựng riêng,
không phụ thuộc corpus): injected defect phải bị BẮT, nội dung hợp lệ phải
ĐƯỢC QUA. Đây là điều kiện để tin gate `phase5_visual_gate.py` (WLAY-012:
không được tin gate chưa qua test hai chiều).

Chạy:  python3 -X utf8 tools/test_phase5_visual_detectors.py
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_visual_gate import (          # noqa: E402
    det_blank_sparse, det_contamination, det_field_code, det_markers,
    det_source_indicator, det_signatures, det_table_grid,
)
from tools.phase5_fixtures import (             # noqa: E402
    ValueFactory, build_fixture, validate_fixture,
)

TMP = Path("/tmp/p5r_detector_tests")
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


def _write_docx(path: Path, paragraphs: list[str],
                table_cols: list[int] | None = None) -> Path:
    """Dựng DOCX tối thiểu (document.xml tự viết — kiểm soát từng w:t)."""
    body_parts = []
    for text in paragraphs:
        body_parts.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>"
            % text)
    if table_cols:
        cols = "".join('<w:gridCol w:w="%d"/>' % w for w in table_cols)
        row_cells = "".join(
            '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>'
            "<w:p><w:r><w:t>C%d</w:t></w:r></w:p></w:tc>" % (w, i)
            for i, w in enumerate(table_cols))
        body_parts.append(
            "<w:tbl><w:tblPr/><w:tblGrid>%s</w:tblGrid>%s<w:tr>%s</w:tr>"
            "</w:tbl>" % (cols, "<w:tr/>" if False else "", row_cells))
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>%s'
        '<w:sectPr/></w:body></w:document>' % "".join(body_parts))
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", xml)
    return path


def _pdf_pages(pdf_path: Path):
    """Dựng pages[] cùng shape với gate: {pno, text, words}."""
    import fitz
    doc = fitz.open(str(pdf_path))
    pages = []
    for pno in range(doc.page_count):
        page = doc[pno]
        pages.append({"pno": pno, "text": page.get_text("text"),
                      "words": page.get_text("words"), "pixmap": None})
    return pages


def _make_pdf(path: Path, page_lines: list[list[tuple[float, float, str]]]):
    """Mỗi trang = list dòng; dòng = (x, y, text). Font base-14 của fitz
    không có glyph tiếng Việt — dùng ASCII không dấu; detector đều fold dấu
    nên kết quả khớp với text có dấu trong corpus thật."""
    import fitz
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    for lines in page_lines:
        page = doc.new_page()  # A4 default 595x842pt
        for x, y, text in lines:
            page.insert_text((x, y), text, fontname="helv", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


# ---------------------------------------------------------------------------

@check("[D1] source-indicator: bắt 'PL2 - Mẫu số 9', qua 'Mẫu số 9' pháp lý")
def d1_source_indicator():
    bad = _write_docx(TMP / "d1_bad.docx",
                      ["PL2 - Mẫu số 9: Giấy chứng nhận đăng ký hộ kinh doanh",
                       "Nội dung thân bài bình thường"])
    hits = det_source_indicator(bad)
    assert len(hits) == 1, "phải bắt đúng 1 leak, thấy %r" % hits
    ok = _write_docx(TMP / "d1_ok.docx",
                     ["Mẫu số 9 (Ban hành kèm theo Thông tư...)", "Thân bài"])
    assert det_source_indicator(ok) == [], "không được nhầm form-number pháp lý"


@check("[D2] field-code literal: bắt 'PAGE \\* MERGEFORMAT'")
def d2_field_code():
    bad = _write_docx(TMP / "d2_bad.docx", [" PAGE   \\* MERGEFORMAT 2"])
    hits = det_field_code(bad)
    assert len(hits) == 1, "phải bắt field code literal, thấy %r" % hits
    ok = _write_docx(TMP / "d2_ok.docx", ["Trang 2 trên tổng số trang"])
    assert det_field_code(ok) == [], "văn thường không được báo"
    # đúng dạng dữ liệu thật từ PLII_M28
    real = _write_docx(TMP / "d2_real.docx", ["PAGE   \\* MERGEFORMAT 2"])
    assert len(det_field_code(real)) == 1


@check("[D3] marker/garbage: bắt {tag} sót + undefined/null/NaN")
def d3_markers():
    bad = _write_docx(TMP / "d3_bad.docx",
                      ["Kính gửi: {co_quan_dkkd}", "Tên: undefined"])
    hits = det_markers(bad)
    assert any("co_quan_dkkd" in h for h in hits), hits
    assert any("undefined" in h for h in hits), hits
    ok = _write_docx(TMP / "d3_ok.docx", ["Kính gửi: Sở Kế hoạch và Đầu tư"])
    assert det_markers(ok) == []


@check("[D4] contamination: form PLI chứa banner 'PHỤ LỤC II' phải bị bắt")
def d4_contamination():
    bad = _write_docx(TMP / "d4_bad.docx",
                      ["PHỤ LỤC II", "BIỂU MẪU SỬ DỤNG TRONG ĐĂNG KÝ HỘ KINH DOANH"])
    hits = det_contamination(bad, {"phu_luc": "Phụ lục I"})
    assert len(hits) == 1, "phải bắt banner khác phụ lục, thấy %r" % hits
    # form_maps ghi phu_luc là số La Mã thuần ('I') — phải nhận đúng
    hits = det_contamination(bad, {"phu_luc": "I"})
    assert len(hits) == 1, "phu_luc='I' phải được chuẩn hoá, thấy %r" % hits
    ok = _write_docx(TMP / "d4_ok.docx", ["PHỤ LỤC I", "BIỂU MẪU..."])
    assert det_contamination(ok, {"phu_luc": "I"}) == []
    # câu thân bài viện dẫn 'theo Phụ lục II' KHÔNG phải banner — không báo
    body = _write_docx(TMP / "d4_body.docx",
                       ["Hồ sơ gồm 01 tờ khai theo mẫu tại Phụ lục II"])
    assert det_contamination(body, {"phu_luc": "I"}) == []


@check("[D9] table grid: cột <1cm và tổng width vượt khổ phải bị bắt")
def d9_table_grid():
    bad = _write_docx(TMP / "d9_bad.docx", ["x"], table_cols=[400, 400, 400])
    issues = det_table_grid(bad)
    assert any(i["code"] == "NARROW_COL" for i in issues), issues
    wide = _write_docx(TMP / "d9_wide.docx", ["x"],
                       table_cols=[1200] * 15)  # 18000 > 16850
    issues = det_table_grid(wide)
    assert any(i["code"] == "WIDTH_OVERFLOW" for i in issues), issues
    ok = _write_docx(TMP / "d9_ok.docx", ["x"],
                     table_cols=[1200] * 8)   # 9600, mỗi cột 2.1cm
    assert det_table_grid(ok) == [], det_table_grid(ok)


@check("[D5] blank/sparse: trang trống phải bị báo BLANK")
def d5_blank():
    long_text = ("Trang đầu có nội dung đầy đủ vượt ngưỡng thưa hẳn — đoạn "
                 "này được viết đủ dài với nhiều từ tiếng Việt không dấu để "
                 "bộ đếm ký tự của detector không xếp vào nhóm SPARSE nữa")
    pdf = _make_pdf(TMP / "d5.pdf", [
        [(72, 100, long_text)],
        [],                                   # trang trắng hoàn toàn
    ])
    pages = _pdf_pages(pdf)
    issues = det_blank_sparse(pages)
    assert {"page": 2, "code": "BLANK", "chars": 0} in issues, issues
    # trang có nội dung không bao giờ bị xếp BLANK (SPARSE chỉ là census)
    assert not any(i["page"] == 1 and i["code"] == "BLANK" for i in issues)


@check("[D6] orientation: 2 signer cùng hàng=horizontal, xếp dọc=vertical")
def d6_orientation():
    horiz = _make_pdf(TMP / "d6_horiz.pdf", [[
        (72, 700, "NGUOI NOP"), (330, 700, "NGUOI NHAN"),
        (72, 716, "(Ky va ghi ho ten)"), (330, 716, "(Ky va ghi ho ten)"),
    ]])
    exp_h = {"fid": {"signature": {"orientation": "horizontal"}}}
    res = det_signatures(_pdf_pages(horiz), exp_h, "fid")
    assert not res["fails"], res["fails"]
    vert = _make_pdf(TMP / "d6_vert.pdf", [[
        (72, 700, "NGUOI NOP"), (72, 716, "(Ky va ghi ho ten)"),
        (72, 770, "NGUOI NHAN"), (72, 786, "(Ky va ghi ho ten)"),
    ]])
    res = det_signatures(_pdf_pages(vert), exp_h, "fid")
    assert any(f["code"] == "SIG_ORIENTATION" and
               f["measured"] == "vertical" for f in res["fails"]), res["fails"]


@check("[D7] split: instruction đầu trang không title cùng trang phải bị bắt")
def d7_split():
    pdf = _make_pdf(TMP / "d7.pdf", [
        [(72, 100, "Noi dung trang mot, khoi ky chua xuat hien o day")],
        [(72, 60, "(Ky va ghi ho ten)")],   # đầu trang 2, không title
    ])
    res = det_signatures(_pdf_pages(pdf), {}, "fid")
    assert any(f["code"] == "SIG_SPLIT" and f["page"] == 2
               for f in res["fails"]), res["fails"]


@check("[D8] writing space: gap < min_write_gap_pt registry phải FAIL")
def d8_write_space():
    pdf = _make_pdf(TMP / "d8.pdf", [[
        (72, 700, "CHU SO HUU MOI"), (72, 716, "(Ky va ghi ho ten)"),
        (72, 740, "CHU SO HUU CU"), (72, 756, "(Ky va ghi ho ten)"),
        (72, 768, "Ghi chu cua co quan dang ky kinh doanh"),  # text thường ngay dưới
    ]])
    exp = {"fid": {"signature": {"min_write_gap_pt": 40}}}
    res = det_signatures(_pdf_pages(pdf), exp, "fid")
    assert any(f["code"] == "SIG_WRITE_SPACE" for f in res["fails"]), res["fails"]
    # không registry → chỉ candidate
    res2 = det_signatures(_pdf_pages(pdf), {}, "fid")
    assert not any(f["code"] == "SIG_WRITE_SPACE" for f in res2["fails"])
    assert any(c["code"] == "SIG_WRITE_SPACE" for c in res2["candidates"])


@check("[D12] fixture: tick tràn nhóm loại-trừ phải bị validator chặn")
def d12_fixture():
    import json
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    blocks = json.loads((ROOT / "app" / "data" / "blocks" / "PLI_M01.json")
                        .read_text(encoding="utf-8"))
    bad = {"chk_bc_hang_thang": "X", "chk_bc_03_thang": "X"}
    errs = validate_fixture(maps["PLI_M01"], blocks, bad, "choice-variants")
    assert any(e.startswith("V1") for e in errs), errs
    f = ValueFactory()
    data = build_fixture("PLI_M01", maps["PLI_M01"], "choice-variants",
                         blocks, f)
    assert validate_fixture(maps["PLI_M01"], blocks, data,
                            "choice-variants") == []


@check("[Fixture] giá trị phân biệt: hai field không cùng chuỗi trong 1 form")
def fixture_distinct_values():
    import json
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    for fid in ("PLI_M01", "PLI_M70", "PLI_M12"):
        f = ValueFactory()
        data = build_fixture(fid, maps[fid], "valid-full")
        # Giá trị NGẮN (thành phần ngày "05", "2026") trùng nhau là hợp lệ;
        # glue chỉ bắt được khi giá trị dài (định danh/mô tả) phân biệt.
        vals = [v for v in data.values()
                if isinstance(v, str) and len(v) >= 8]
        assert len(vals) == len(set(vals)), \
            "%s: fixture có giá trị dài trùng lặp → mất khả năng bắt glue" % fid


@check("[Fixture] long-boundary ép pagination: M72 25 dòng ngành")
def fixture_long_boundary():
    import json
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    data = build_fixture("PLI_M72", maps["PLI_M72"], "long-boundary")
    loop = data.get("ds_nganh_dntn")
    assert isinstance(loop, list) and len(loop) >= 25, \
        "long-boundary phải ép ≥25 dòng, thấy %r" % (loop and len(loop))


def main() -> int:
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    d1_source_indicator()
    d2_field_code()
    d3_markers()
    d4_contamination()
    d9_table_grid()
    d5_blank()
    d6_orientation()
    d7_split()
    d8_write_space()
    d12_fixture()
    fixture_distinct_values()
    fixture_long_boundary()
    fails = [r for r in _results if not r[0]]
    print("-" * 60)
    print("test_phase5_visual_detectors: %d PASS / %d FAIL"
          % (len(_results) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
