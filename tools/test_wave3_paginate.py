#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_wave3_paginate.py — Wave 3 lane E (paginate): mutation/structural test
cho 4 fix phân trang render-side. Python thuần (zip/regex) — KHÔNG soffice/
export; kết quả fit trang do Lead verify bằng render (visual gate).

  E1  bảng ký ngang không tràn trang (PLI_M70): `_keep_signature_blocks`
      pass 2 — ngoài cantSplit, bảng ký còn được NÉN: trHeight atLeast
      1200→600, spacer exact trong ô 800→240 (đồng bộ mirror
      _SIG_TABLE_TEMPLATE/_SIG_CELL_TEMPLATE của tools/build_form_maps.py).
      Bảng KHÔNG phải bảng ký giữ nguyên giá trị.
  E2  cặp ký dọc nguyên khối (PLII_M17): `_ensure_signature_space` — khi
      đoạn chữ kế tiếp instruction là title cụm ký khác (đa-người-ký dọc),
      instruction + spacer vừa chèn nhận keepNext (cặp atomic); đồng thời
      `existing` đếm w:line exact (spacer có sẵn) để không double-insert.
  E3  `_collapse_blank_para_runs` (m72_dhdn): run ≥3 paragraph rỗng liên
      tiếp ĐỨNG NGAY SAU bảng (body-level) nén về 1 paragraph (giữ paragraph
      CUỐI, mang w:before=120 tách bảng khỏi mục kế); run <3 hoặc nằm giữa
      văn bản thường KHÔNG bị đụng.
  E4  `_trim_trailing_sig_gap` (PLI_M45/M53): paragraph cụm ký là con CUỐI
      body (sau chỉ còn sectPr) + para liền trước rỗng + w:before ≥120 ->
      xoá para rỗng + zero w:before của para ký. Cụm ký KHÔNG cuối body,
      para liền trước có chữ, hoặc before <120 -> KHÔNG đụng.

Chạy:  python3 -X utf8 -m tools.test_wave3_paginate
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import docx_render as dr   # noqa: E402

TEST_OUT = Path("/tmp/wave3_paginate_test")


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
                import traceback
                traceback.print_exc()
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_min_docx(path: Path, body_parts: list[str]) -> Path:
    """DOCX tối thiểu tự viết document.xml (kiểm soát từng phần tử)."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>%s'
        "<w:sectPr/></w:body></w:document>" % "".join(body_parts))
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.'
            'openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", xml)
    return path


def _docx_xml(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        return z.read("word/document.xml").decode("utf-8")


def _body_children(xml: str) -> list[str]:
    """Các con trực tiếp của w:body (chuỗi seg, theo thứ tự tài liệu)."""
    body = re.search(r"<w:body>(.*)</w:body>", xml, re.S).group(1)
    return [body[s:e] for s, e in dr._split_body_children(body)]


def _para_text(seg: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", seg)).strip()


_P_SIG1 = ('<w:p><w:r><w:t xml:space="preserve">NGƯỜI NỘP</w:t><w:br/>'
           "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p>")
_P_SIG2 = ('<w:p><w:r><w:t xml:space="preserve">NGƯỜI NHẬN</w:t><w:br/>'
           "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p>")
_P_SIG_CENTER = ('<w:p><w:pPr><w:jc w:val="center"/>'
                 '<w:spacing w:before="120"/></w:pPr><w:r><w:t xml:space='
                 '"preserve">TRƯỜNG ĐƠN VỊ</w:t><w:br/><w:t>(Ký, ghi họ tên'
                 " và đóng dấu)</w:t></w:r></w:p>")
_P_PLAIN = "<w:p><w:r><w:t>Nội dung thường</w:t></w:r></w:p>"
_P_EMPTY_120 = ('<w:p><w:pPr><w:spacing w:before="120"/></w:pPr></w:p>')
_SPACER_TPL = ('<w:p><w:pPr><w:spacing w:before="0" w:after="0" '
               'w:line="%d" w:lineRule="exact"/></w:pPr></w:p>')


def _sig_table_1200(text_a: str, text_b: str) -> str:
    """Bảng ký ngang 1x2 với trHeight 1200 atLeast + spacer exact 800 trong
    ô — hình dạng cookie-cutter của template PLI_M70 / build_form_maps."""
    def _cell(text: str) -> str:
        return ('<w:tc><w:tcPr><w:tcW w:w="4320" w:type="dxa"/></w:tcPr>'
                '<w:p><w:r><w:t xml:space="preserve">%s</w:t><w:br/>'
                "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p>"
                "<w:p><w:pPr><w:spacing w:before=\"0\" w:after=\"0\" "
                'w:line="800" w:lineRule="exact"/></w:pPr></w:p>'
                "</w:tc>" % text)
    return ('<w:tbl><w:tblPr><w:tblW w:w="8640" w:type="dxa"/></w:tblPr>'
            '<w:tblGrid><w:gridCol w:w="4320"/><w:gridCol w:w="4320"/>'
            "</w:tblGrid>"
            '<w:tr><w:trPr><w:trHeight w:val="1200" w:hRule="atLeast"/>'
            "</w:trPr>%s%s</w:tr></w:tbl>"
            % (_cell(text_a), _cell(text_b)))


class _Registry:
    """Vá registry kỳ vọng ký (dr._EXPECT_CACHE) trong phạm vi test."""

    def __init__(self, expectations: dict):
        self._old = dr._EXPECT_CACHE
        self._new = expectations

    def __enter__(self):
        dr._EXPECT_CACHE = self._new
        return self

    def __exit__(self, *exc):
        dr._EXPECT_CACHE = self._old
        return False


# ---------------------------------------------------------------------------
# E1 — bảng ký ngang: nén trHeight + spacer
# ---------------------------------------------------------------------------

@check("E1_sig_table_compacted_600_240")
def test_e1_sig_table():
    src = _write_min_docx(TEST_OUT / "e1_sig.docx",
                          [_P_PLAIN, _sig_table_1200("NGƯỜI NỘP", "NGƯỜI NHẬN"),
                           _P_PLAIN])
    xml = _docx_xml(dr.render(src, {}))
    assert '<w:trHeight w:val="600" w:hRule="atLeast"/>' in xml, \
        "trHeight bảng ký chưa hạ 1200->600: %s" % _trheights(xml)
    assert 'w:line="240" w:lineRule="exact"' in xml, "spacer chưa nén 800->240"
    assert 'w:val="1200"' not in xml, "còn trHeight 1200 sót trong bảng ký"
    assert 'w:line="800"' not in xml, "còn spacer 800 sót trong bảng ký"
    assert "<w:cantSplit/>" in xml, "hàng ký mất cantSplit"
    # idempotent: render 2 lần cùng bytes
    assert dr.render(src, {}) == dr.render(src, {}), "E1 render không ổn định"


def _trheights(xml: str) -> list[str]:
    return re.findall(r"<w:trHeight[^>]*/>", xml)


@check("E1_nonsig_table_untouched")
def test_e1_nonsig_table():
    plain_tbl = ('<w:tbl><w:tblPr><w:tblW w:w="8640" w:type="dxa"/></w:tblPr>'
                 '<w:tblGrid><w:gridCol w:w="8640"/></w:tblGrid>'
                 '<w:tr><w:trPr><w:trHeight w:val="1200" w:hRule="atLeast"/>'
                 "</w:trPr>"
                 '<w:tc><w:tcPr><w:tcW w:w="8640" w:type="dxa"/></w:tcPr>'
                 "<w:p><w:r><w:t>Nội dung thường</w:t></w:r></w:p>"
                 "</w:tc></w:tr></w:tbl>")
    src = _write_min_docx(TEST_OUT / "e1_plain.docx", [plain_tbl])
    xml = _docx_xml(dr.render(src, {}))
    assert '<w:trHeight w:val="1200" w:hRule="atLeast"/>' in xml, \
        "bảng thường bị nén nhầm: %s" % _trheights(xml)
    assert 'w:line="240" w:lineRule="exact"' not in xml


@check("E1_mirror_build_form_maps_templates")
def test_e1_mirror():
    from tools.build_form_maps import _SIG_CELL_TEMPLATE, _SIG_TABLE_TEMPLATE
    assert '<w:trHeight w:val="600" w:hRule="atLeast"/>' in _SIG_TABLE_TEMPLATE, \
        "_SIG_TABLE_TEMPLATE chưa đồng bộ 600"
    assert 'w:val="1200"' not in _SIG_TABLE_TEMPLATE
    assert 'w:line="240" w:lineRule="exact"' in _SIG_CELL_TEMPLATE, \
        "_SIG_CELL_TEMPLATE chưa đồng bộ 240"
    assert 'w:line="800"' not in _SIG_CELL_TEMPLATE
    # guard render _cell_wrap đã dùng 240 từ trước — nhất quán giá trị nén
    src = Path(dr.__file__).read_text(encoding="utf-8")
    m = re.search(r"def _cell_wrap.*?</w:tc>'", src, re.S)
    assert m and 'w:line="240"' in m.group(0), "_cell_wrap phải giữ spacer 240"


# ---------------------------------------------------------------------------
# E2 — cặp ký dọc nguyên khối + existing đếm w:line exact
# ---------------------------------------------------------------------------

_E2_REG = {
    # key = form id = STEM của file .docx test (render lấy form_id từ stem)
    "E2PAIR": {"signature": {"signers": 2, "keep_together": True,
                             "min_write_gap_pt": 72}},
    "E2EXACT": {"signature": {"signers": 2, "keep_together": True,
                              "min_write_gap_pt": 72}},
    "E2PLAIN": {"signature": {"signers": 1, "keep_together": True,
                              "min_write_gap_pt": 72}},
}


@check("E2_sig_pair_keepnext_instruction_and_spacer")
def test_e2_pair_atomic():
    # cụm mang before=120 như template thật (M17) -> (a) không chèn thêm
    # <w:p/> giữa 2 cụm; existing = before(cụm 2)=120 -> deficit = 1440+60-120
    sig1 = _P_SIG1.replace(
        "<w:p><w:r>",
        '<w:p><w:pPr><w:spacing w:before="120"/></w:pPr><w:r>', 1)
    sig2 = _P_SIG2.replace(
        "<w:p><w:r>",
        '<w:p><w:pPr><w:spacing w:before="120"/></w:pPr><w:r>', 1)
    src = _write_min_docx(TEST_OUT / "E2PAIR.docx", [sig1, sig2])
    with _Registry(_E2_REG):
        xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    sig1_out = [c for c in children if "NGƯỜI NỘP" in c]
    sig2_out = [c for c in children if "NGƯỜI NHẬN" in c]
    assert len(sig1_out) == 1 and len(sig2_out) == 1, children
    assert "<w:keepNext/>" in sig1_out[0], \
        "instruction cụm 1 thiếu keepNext (bó với cụm 2)"
    assert "<w:keepLines/>" in sig1_out[0] and "<w:keepLines/>" in sig2_out[0]
    assert "<w:keepNext/>" not in sig2_out[0], \
        "instruction cụm CUỐI không được bó với nội dung sau nó"
    # spacer deficit chèn giữa 2 cụm: existing = before(sig2)=120 -> 1380
    between = children[children.index(sig1_out[0]) + 1:
                       children.index(sig2_out[0])]
    assert len(between) == 1 and 'w:line="1380" w:lineRule="exact"' in \
        between[0], "spacer deficit giữa 2 cụm sai: %r" % between
    assert "<w:keepNext/>" in between[0], "spacer giữa cặp thiếu keepNext"


@check("E2_existing_counts_line_exact_no_double_insert")
def test_e2_existing_exact():
    # spacer exact 1380 có sẵn + before=120 của cụm 2 -> existing 1500 >= 1440
    # -> KHÔNG chèn spacer thứ hai (trước hardening: 240+120=360 -> insert).
    # [_P_TEXT8 cuối] để cụm 2 KHÔNG là con cuối body (tách khỏi điều kiện
    # E4 — pass E4 chạy trước sẽ ăn đúng para rỗng đó theo thiết kế).
    pre = _SPACER_TPL % 1380
    sig2_sp = ('<w:p><w:pPr><w:spacing w:before="120"/></w:pPr><w:r>'
               '<w:t xml:space="preserve">NGƯỜI NHẬN</w:t><w:br/>'
               "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p>")
    src = _write_min_docx(TEST_OUT / "E2EXACT.docx",
                          [_P_SIG1, pre, sig2_sp, _P_TEXT8])
    with _Registry(_E2_REG):
        xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    i1 = next(i for i, c in enumerate(children) if "NGƯỜI NỘP" in c)
    i2 = next(i for i, c in enumerate(children) if "NGƯỜI NHẬN" in c)
    between = children[i1 + 1:i2]
    assert len(between) == 1, \
        "double-insert spacer (w:line exact chưa được đếm): %r" % between
    assert 'w:line="1380" w:lineRule="exact"' in between[0], between[0]
    assert "<w:keepNext/>" in children[i1], "instruction cụm 1 thiếu keepNext"


@check("E2_next_plain_text_no_bind")
def test_e2_no_bind_plain():
    src = _write_min_docx(TEST_OUT / "E2PLAIN.docx",
                          [_P_SIG_CENTER, _P_PLAIN])
    with _Registry(_E2_REG):
        xml = _docx_xml(dr.render(src, {}))
    sig = [c for c in _body_children(xml) if "TRƯỜNG ĐƠN VỊ" in c]
    assert len(sig) == 1
    assert "<w:keepNext/>" not in sig[0], \
        "instruction kế text thường bị bó nhầm với nội dung sau"
    # spacer vùng viết vẫn chèn đúng như trước (hành vi 5R2 giữ nguyên)
    children = _body_children(xml)
    between = children[children.index(sig[0]) + 1:
                       next(i for i, c in enumerate(children)
                            if "Nội dung thường" in c)]
    assert len(between) == 1 and 'w:line="1500" w:lineRule="exact"' in \
        between[0], "spacer vùng viết trước text thường sai: %r" % between


# ---------------------------------------------------------------------------
# E3 — nén run paragraph rỗng ngay sau bảng
# ---------------------------------------------------------------------------

_PLAIN_TBL = ('<w:tbl><w:tblPr><w:tblW w:w="8640" w:type="dxa"/></w:tblPr>'
              '<w:tblGrid><w:gridCol w:w="8640"/></w:tblGrid>'
              "<w:tr><w:tc><w:tcPr><w:tcW w:w=\"8640\"/></w:tcPr>"
              "<w:p><w:r><w:t>Ô bảng</w:t></w:r></w:p></w:tc></w:tr></w:tbl>")
_P_TEXT8 = "<w:p><w:r><w:t>8. Nơi đăng ký hợp lệ của doanh nghiệp</w:t></w:r>" \
           "</w:p>"


def _empty_run(n: int, last_before: int | None = 120) -> list[str]:
    out = ["<w:p/>" for _ in range(max(0, n - 1))]
    if last_before is not None and n > 0:
        out.append('<w:p><w:pPr><w:spacing w:before="%d"/></w:pPr></w:p>'
                   % last_before)
    return out


@check("E3_run3_after_table_collapsed_to_1")
def test_e3_run3():
    src = _write_min_docx(TEST_OUT / "e3_run3.docx",
                          [_PLAIN_TBL] + _empty_run(3) + [_P_TEXT8])
    xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    i_tbl = next(i for i, c in enumerate(children) if c.startswith("<w:tbl"))
    i_text = next(i for i, c in enumerate(children) if "Nơi đăng ký" in c)
    between = children[i_tbl + 1:i_text]
    assert len(between) == 1, "run 3 rỗng chưa nén về 1: %r" % between
    assert 'w:before="120"' in between[0], \
        "paragraph giữ lại mất w:before=120 (tách bảng khỏi mục kế)"


@check("E3_run4_after_table_collapsed_to_1")
def test_e3_run4():
    src = _write_min_docx(TEST_OUT / "e3_run4.docx",
                          [_PLAIN_TBL] + _empty_run(4) + [_P_TEXT8])
    xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    i_tbl = next(i for i, c in enumerate(children) if c.startswith("<w:tbl"))
    i_text = next(i for i, c in enumerate(children) if "Nơi đăng ký" in c)
    between = children[i_tbl + 1:i_text]
    assert len(between) == 1, "run 4 rỗng chưa nén về 1: %r" % between


@check("E3_run2_after_table_untouched")
def test_e3_run2_kept():
    src = _write_min_docx(TEST_OUT / "e3_run2.docx",
                          [_PLAIN_TBL] + _empty_run(2) + [_P_TEXT8])
    xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    i_tbl = next(i for i, c in enumerate(children) if c.startswith("<w:tbl"))
    i_text = next(i for i, c in enumerate(children) if "Nơi đăng ký" in c)
    between = children[i_tbl + 1:i_text]
    assert len(between) == 2, "run 2 rỗng sau bảng bị đụng: %r" % between


@check("E3_run2_between_text_untouched")
def test_e3_between_text_kept():
    src = _write_min_docx(TEST_OUT / "e3_text.docx",
                          [_P_PLAIN, "<w:p/>", "<w:p/>", _P_TEXT8])
    xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    i_a = next(i for i, c in enumerate(children) if "Nội dung thường" in c)
    i_b = next(i for i, c in enumerate(children) if "Nơi đăng ký" in c)
    between = children[i_a + 1:i_b]
    assert len(between) == 2, \
        "run 2 rỗng GIỮA văn bản thường bị đụng: %r" % between


@check("E3_m72_no_run3_after_any_table")
def test_e3_m72_integration():
    maps_path = ROOT / "app" / "data" / "form_maps.json"
    import json
    maps = json.loads(maps_path.read_text(encoding="utf-8"))
    src = ROOT / "app" / maps["PLI_M72"]["template"]
    xml = _docx_xml(dr.render(src, {}))
    children = _body_children(xml)
    worst = 0
    for i, c in enumerate(children):
        if not c.startswith("<w:tbl"):
            continue
        n = 0
        for nxt in children[i + 1:]:
            if not nxt.startswith("<w:p") or _para_text(nxt):
                break
            n += 1
        worst = max(worst, n)
    assert worst < 3, \
        "PLI_M72 còn run %d paragraph rỗng ngay sau bảng (>=3)" % worst


# ---------------------------------------------------------------------------
# E4 — cụm ký cuối body: xoá para rỗng + zero before
# ---------------------------------------------------------------------------

_P_TAIL_TEXT = ('<w:p><w:pPr><w:spacing w:before="120"/></w:pPr><w:r>'
                "<w:t>Nơi nhận: … - Lưu: X</w:t></w:r></w:p>")


@check("E4_trailing_sig_gap_trimmed")
def test_e4_unit_trim():
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s%s%s'
           "<w:sectPr/></w:body></w:document>"
           % (_P_TAIL_TEXT, _P_EMPTY_120, _P_SIG_CENTER))
    out = dr._trim_trailing_sig_gap(xml)
    assert out != xml, "E4 không có tác dụng trên đuôi [text][empty][sig]"
    children = [c for c in _body_children(out) if not c.startswith("<w:sectPr")]
    assert len(children) == 2, "para rỗng chưa bị xoá: %d children" % \
        len(children)
    assert "TRƯỜNG ĐƠN VỊ" in children[1]
    assert 'w:before="0"' in children[1], \
        "w:before của para ký chưa được zero"
    assert 'w:before="120"' not in children[1]


@check("E4_not_last_body_untouched")
def test_e4_not_last():
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s%s%s%s'
           "<w:sectPr/></w:body></w:document>"
           % (_P_TAIL_TEXT, _P_EMPTY_120, _P_SIG_CENTER, _P_TEXT8))
    assert dr._trim_trailing_sig_gap(xml) == xml, \
        "cụm ký KHÔNG cuối body mà bị đụng"


@check("E4_prev_has_text_untouched")
def test_e4_prev_text():
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s%s'
           "<w:sectPr/></w:body></w:document>"
           % (_P_TAIL_TEXT, _P_SIG_CENTER))
    assert dr._trim_trailing_sig_gap(xml) == xml, \
        "para liền trước CÓ CHỮ mà bị đụng"


@check("E4_before_below_120_untouched")
def test_e4_before_small():
    sig0 = _P_SIG_CENTER.replace('w:before="120"', 'w:before="0"')
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s%s%s'
           "<w:sectPr/></w:body></w:document>"
           % (_P_TAIL_TEXT, _P_EMPTY_120, sig0))
    assert dr._trim_trailing_sig_gap(xml) == xml, \
        "para ký before<120 mà vẫn bị zero/xoá"


@check("E4_render_end_to_end_before_zeroed")
def test_e4_render():
    src = _write_min_docx(TEST_OUT / "e4_render.docx",
                          [_P_TAIL_TEXT, _P_EMPTY_120, _P_SIG_CENTER])
    xml = _docx_xml(dr.render(src, {}))
    sig = [c for c in _body_children(xml) if "TRƯỜNG ĐƠN VỊ" in c]
    assert len(sig) == 1
    assert 'w:before="0"' in sig[0], "render: before para ký chưa zero: %s" \
        % sig[0]
    # para rỗng before=120 gốc đã mất (mọi para rỗng còn lại không mang
    # spacing before=120 đứng giữa text và cụm ký)
    children = _body_children(xml)
    i_text = next(i for i, c in enumerate(children) if "Nơi nhận" in c)
    i_sig = children.index(sig[0])
    for c in children[i_text + 1:i_sig]:
        assert 'w:before="120"' not in c, \
            "para rỗng before=120 gốc vẫn còn: %s" % c


# ---------------------------------------------------------------------------

def main() -> int:
    test_e1_sig_table()
    test_e1_nonsig_table()
    test_e1_mirror()
    test_e2_pair_atomic()
    test_e2_existing_exact()
    test_e2_no_bind_plain()
    test_e3_run3()
    test_e3_run4()
    test_e3_run2_kept()
    test_e3_between_text_kept()
    test_e3_m72_integration()
    test_e4_unit_trim()
    test_e4_not_last()
    test_e4_prev_text()
    test_e4_before_small()
    test_e4_render()
    print("-" * 60)
    passed = sum(1 for ok, _ in _results if ok)
    failed = sum(1 for ok, _ in _results if not ok)
    print("Tổng kết: %d PASS / %d FAIL / %d test" % (
        passed, failed, len(_results)))
    for ok, name in _results:
        if not ok:
            print(" -", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
