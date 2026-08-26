# -*- coding: utf-8 -*-
"""Test Wave L1 extractor/schema (tools/docx_to_blocks.py + tools/layout_roles.py).

Fixture tự sinh DOCX bằng python-docx trong THƯ MỤC TEMP BÊN NGOÀI repo
(tempfile.mkdtemp) — KHÔNG BAO GIỜ ghi vào app/data/blocks. Chạy:
    python3 -X utf8 -m tools.test_layout_l1_extractor     # exit 0 = PASS
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import docx_to_blocks as d2b          # noqa: E402
import layout_roles                   # noqa: E402
from layout_roles import classify_role, fold  # noqa: E402

from docx import Document             # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.opc.constants import CONTENT_TYPE as CT    # noqa: E402
from docx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
from docx.opc.packuri import PackURI  # noqa: E402
from docx.opc.part import Part        # noqa: E402
from docx.oxml.ns import qn           # noqa: E402
from docx.shared import Pt            # noqa: E402

FIXTURE_ID = "FIX_L1_T01"

FOOTNOTES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
    '<w:footnote w:id="1"><w:p><w:r><w:t> Chu ho kinh doanh ky truc tiep vao phan nay.</w:t></w:r></w:p></w:footnote>'
    '<w:footnote w:id="7"><w:p><w:r><w:t>Ghi chú chân trang số 7.</w:t></w:r></w:p></w:footnote>'
    '</w:footnotes>'
).encode("utf-8")


def _add_raw_child(run, tag, attrs=None):
    el = run._element.makeelement(qn(tag), attrs or {})
    run._element.append(el)
    return el


def build_fixture_doc():
    """DOCX tổng hợp phủ mọi tính năng L1."""
    doc = Document()

    # 1) hard break br + cr + tab trong cùng paragraph
    p = doc.add_paragraph()
    r = p.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    _add_raw_child(r, "w:br")
    t = _add_raw_child(r, "w:t")
    t.text = "Độc lập - Tự do - Hạnh phúc"
    _add_raw_child(r, "w:cr")
    _add_raw_child(r, "w:tab")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 2) vertAlign superscript + subscript
    p2 = doc.add_paragraph()
    p2.add_run("Tôi là")
    sup = p2.add_run("1")
    sup.font.superscript = True
    p2.add_run(" và H")
    sub = p2.add_run("2")
    sub.font.subscript = True
    p2.add_run("O bình thường")

    # 3) footnoteReference chèn tay + text chưa biết id 99
    p3 = doc.add_paragraph()
    r31 = p3.add_run("Ký tên")
    _add_raw_child(r31, "w:footnoteReference", {qn("w:id"): "7"})
    p3.add_run(" cuối dòng")
    p4 = doc.add_paragraph()
    r41 = p4.add_run("Mất chú thích")
    _add_raw_child(r41, "w:footnoteReference", {qn("w:id"): "99"})

    # 4) indent/spacing/line-spacing multiple + keep-with-next
    p5 = doc.add_paragraph("Văn bản có format đầy đủ.")
    pf = p5.paragraph_format
    pf.left_indent = Pt(12)
    pf.right_indent = Pt(6)
    pf.first_line_indent = Pt(-9)  # hanging indent
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.15
    pf.keep_with_next = True

    # 5) line spacing exact (Pt) -> lineSpacingPt
    p6 = doc.add_paragraph("Giãn dòng exact.")
    p6.paragraph_format.line_spacing = Pt(14)

    # 6) marker kỹ thuật vs dòng pháp lý trong CÙNG một biểu mẫu
    doc.add_paragraph("PL1 - Mau so 1: Giấy đề nghị đăng ký doanh nghiệp")
    doc.add_paragraph("Mẫu số 1")

    # 7) the biến để kiểm tra w giữ nguyên công thức cũ
    p8 = doc.add_paragraph("Họ tên: {dn.ten_tieng_viet} và {chk_dong_y}")

    return doc


def attach_footnotes_part(doc):
    package = doc.part.package
    part = Part(PackURI("/word/footnotes.xml"), CT.WML_FOOTNOTES,
                FOOTNOTES_XML, package)
    doc.part.relate_to(part, RT.FOOTNOTES)


class TestHardBreakNewline(unittest.TestCase):
    def setUp(self):
        self.doc = build_fixture_doc()
        attach_footnotes_part(self.doc)

    def test_br_cr_tab_bao_toan_ky_tu(self):
        blocks = d2b.convert_document(self.doc, FIXTURE_ID, "fixture")["blocks"]
        txt = "".join(
            r["text"] for r in blocks[0]["runs"] if "text" in r
        )
        self.assertEqual(
            txt,
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\t",
        )
        self.assertIn("\n", txt)
        self.assertIn("\t", txt)

    def test_char_stream_khop_run_text_python_docx(self):
        for p in self.doc.paragraphs:
            chars, _fns = d2b._char_stream(p)
            self.assertEqual("".join(c for c, _m in chars), "".join(r.text for r in p.runs))


class TestVertAlignFootnote(unittest.TestCase):
    def setUp(self):
        self.doc = build_fixture_doc()
        attach_footnotes_part(self.doc)
        self.fns = d2b.load_footnotes(self.doc)
        self.blocks = d2b.convert_document(
            self.doc, FIXTURE_ID, "fixture", footnotes=self.fns
        )["blocks"]

    def _p_runs(self, idx):
        return [r for r in self.blocks[idx]["runs"] if "text" in r]

    def test_superscript_run_co_vertalign(self):
        runs = self._p_runs(1)
        self.assertEqual(runs[0]["text"], "Tôi là")
        self.assertNotIn("vertAlign", runs[0])
        self.assertEqual(runs[1]["text"], "1")
        self.assertEqual(runs[1]["vertAlign"], "superscript")

    def test_subscript_run_co_vertalign(self):
        runs = self._p_runs(1)
        self.assertEqual(runs[-2]["text"], "2")
        self.assertEqual(runs[-2]["vertAlign"], "subscript")
        self.assertNotIn("vertAlign", runs[-1])

    def test_footnote_ref_run_dict(self):
        blk = self.blocks[2]
        refs = [r for r in blk["runs"] if r.get("role") == "footnote-ref"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["footnoteId"], 7)
        self.assertEqual(blk.get("footnotes"), {"7": "Ghi chú chân trang số 7."})

    def test_footnote_id_mat_text_van_giu_id_fail_soft(self):
        blk = self.blocks[3]
        refs = [r for r in blk["runs"] if r.get("role") == "footnote-ref"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["footnoteId"], 99)
        self.assertNotIn("footnotes", blk)  # không có text -> không emit map

    def test_footnotes_separator_id_am_bo_qua(self):
        fns = d2b.load_footnotes(self.doc)
        self.assertNotIn(-1, fns)
        self.assertEqual(fns.get(1), "Chu ho kinh doanh ky truc tiep vao phan nay.")


class TestParagraphFormat(unittest.TestCase):
    def setUp(self):
        self.doc = build_fixture_doc()
        self.blocks = d2b.convert_document(self.doc, FIXTURE_ID, "fixture")["blocks"]

    def test_format_day_du_pt_va_multiple(self):
        fmt = self.blocks[4].get("format")
        self.assertEqual(
            fmt,
            {
                "leftIndentPt": 12.0,
                "rightIndentPt": 6.0,
                "firstLineIndentPt": -9.0,
                "spaceBeforePt": 6.0,
                "spaceAfterPt": 3.0,
                "lineSpacing": 1.15,
                "keepWithNext": True,
            },
        )

    def test_line_spacing_exact_thanh_linespacingpt(self):
        fmt = self.blocks[5].get("format")
        self.assertEqual(fmt, {"lineSpacingPt": 14.0})

    def test_default_khong_emit_format(self):
        # paragraph marker kỹ thuật không set format -> không có key "format"
        self.assertNotIn("format", self.blocks[6])

    def test_emu_chinh_xac_120_twips_6pt(self):
        from docx.shared import Twips

        doc = Document()
        p = doc.add_paragraph("x")
        p.paragraph_format.space_before = Twips(120)  # 120 twentieths = 6pt
        self.assertEqual(d2b._para_format_dict(p), {"spaceBeforePt": 6.0})


class TestSemanticRoles(unittest.TestCase):
    def test_source_indicator_pl_marker(self):
        role = classify_role(fold("PL1 - Mau so 1: Giấy đề nghị đăng ký doanh nghiệp"))
        self.assertEqual(role, "source-indicator")

    def test_form_number_hop_le_khong_bi_an(self):
        self.assertEqual(classify_role(fold("Mẫu số 1")), "form-number")
        self.assertEqual(classify_role(fold("Mẫu số 72")), "form-number")
        self.assertNotEqual(classify_role(fold("Mẫu số 72")), "source-indicator")

    def test_cung_mau_ca_hai_dang_marker_va_mauso(self):
        doc = Document()
        doc.add_paragraph("PL2 - Mau so 5: Giấy chứng nhận đăng ký hộ kinh doanh")
        doc.add_paragraph("Mẫu số 5")
        blocks = d2b.convert_document(doc, FIXTURE_ID, "f")["blocks"]
        self.assertEqual(blocks[0].get("role"), "source-indicator")
        self.assertEqual(blocks[1].get("role"), "form-number")
        self.assertNotEqual(blocks[0]["role"], blocks[1]["role"])

    def test_ten_file_docx_la_source_indicator(self):
        self.assertEqual(
            classify_role(fold("Nguồn: PLI_M01_tach.docx")), "source-indicator"
        )

    def test_national_header_motto_separator(self):
        multi = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n-----"
        runs = [{"text": multi}]
        self.assertEqual(classify_role(fold(multi), None, runs), "national-header")
        self.assertEqual(
            classify_role(fold("Độc lập - Tự do - Hạnh phúc")),
            "national-motto",
        )
        sep = "-----------------"
        self.assertEqual(
            classify_role(fold(sep), None, [{"text": sep}]),
            "national-separator",
        )

    def test_date_salutation_note_signature(self):
        date_runs = [
            {"input": {"key": "dia_diem_ky", "w": 12}},
            {"text": ", ngày ", "i": True},
            {"input": {"key": "ngay_ky_vb", "w": 12}},
            {"input": {"key": "thang_ky_vb", "w": 12}},
            {"input": {"key": "nam_ky_vb", "w": 12}},
        ]
        self.assertEqual(classify_role(", ngay thang nam", None, date_runs), "date-line")
        self.assertEqual(classify_role(fold("Kính gửi: Ủy ban nhân dân cấp xã")), "salutation")
        self.assertEqual(classify_role(fold("Lưu ý: kê khai đầy đủ")), "note")
        sig = classify_role(fold("CHỦ HỘ KINH DOANH\n(Ký và ghi họ tên)"))
        self.assertEqual(sig, "signature")

    def test_title_subtitle_section_body(self):
        title = "GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH"
        self.assertEqual(
            classify_role(fold(title), None, [{"text": title}]), "form-title"
        )
        sub = "DOANH NGHIỆP TƯ NHÂN"
        self.assertEqual(
            classify_role(fold(sub), None, [{"text": sub}]), "form-subtitle"
        )
        self.assertEqual(classify_role(fold("1. Tên hộ kinh doanh: ")), "section-heading")
        self.assertEqual(
            classify_role(fold("Đăng ký hộ kinh doanh do tôi là chủ hộ với các nội dung sau:")),
            "body",
        )
        body = "Số định danh cá nhân: "
        self.assertEqual(
            classify_role(
                fold(body), None,
                [{"text": body}, {"input": {"key": "chu_hkd.so_cccd", "w": 20}}],
            ),
            "body",
        )

    def test_footnote_body_digit_prefix(self):
        self.assertEqual(
            classify_role(fold("6 Chủ hộ kinh doanh ký trực tiếp vào phần này.")),
            "footnote",
        )
        # mục lục "1." không được nhầm footnote
        self.assertEqual(classify_role(fold("1. Chủ hộ kinh doanh trước khi thay đổi:")), "section-heading")

    def test_fold_giong_p1_c(self):
        self.assertEqual(fold("Mẫu số 72"), "mau so 72")
        self.assertEqual(fold("Đắk Lắk"), "dak lak")
        self.assertEqual(fold("  A\n B  "), "a b")


class TestOverridesAndSchema(unittest.TestCase):
    def test_overrides_file_rong_hop_le(self):
        data = d2b.load_role_overrides(os.path.join(TOOLS_DIR, "layout_role_overrides.json"))
        self.assertEqual(data, {})

    def test_override_by_index_va_prefix(self):
        ov = {
            "by_index": {FIXTURE_ID: {"3": "note"}},
            "by_folded_prefix": [
                {"prefix": "kinh gui", "role": "salutation", "forms": ["KHAC"]}
            ],
        }
        self.assertEqual(d2b.apply_role_override(ov, FIXTURE_ID, 3, "bat ky", "body"), "note")
        # form khác + prefix khớp nhưng bị lọc theo forms -> giữ nguyên
        self.assertEqual(d2b.apply_role_override(ov, FIXTURE_ID, 9, "kinh gui xy", "body"), "body")
        # role lạ trong override -> bỏ qua, trả rule role
        bad = {"by_index": {FIXTURE_ID: {"3": "khong-phai-role"}}}
        self.assertEqual(d2b.apply_role_override(bad, FIXTURE_ID, 3, "x", "body"), "body")

    def test_schema_version_v3(self):
        doc = build_fixture_doc()
        data = d2b.convert_document(doc, FIXTURE_ID, "fixture")
        self.assertEqual(data.get("v"), 3)
        self.assertIn("blocks", data)
        self.assertIn("id", data)
        self.assertIn("ten_mau", data)

    def test_block_cu_thieu_field_moi_van_doc_duoc(self):
        # block cũ schema v2: thiếu role/format/vertAlign — hợp lệ, mặc định body
        old_block = {"t": "p", "align": "left",
                     "runs": [{"text": "Nội dung cũ"}]}
        folded = fold("Nội dung cũ")
        self.assertEqual(layout_roles.classify_role(folded, None, old_block["runs"]), "body")
        self.assertNotIn("role", old_block)


class TestIdempotentAndCompat(unittest.TestCase):
    def test_convert_2_lan_byte_giong_nhau(self):
        fm = json.loads(io.open(
            os.path.join(ROOT, "app", "data", "form_maps.json"),
            encoding="utf-8").read())
        d1 = json.dumps(d2b.convert_document(build_fixture_doc(), FIXTURE_ID, "fx"),
                        ensure_ascii=False, indent=1)
        d2 = json.dumps(d2b.convert_document(build_fixture_doc(), FIXTURE_ID, "fx"),
                        ensure_ascii=False, indent=1)
        self.assertEqual(d1, d2)

        # template thật: convert 2 lần (Document mở riêng) phải byte-giống nhau
        a = json.dumps(d2b.convert("PLI_M01", fm), ensure_ascii=False, indent=1)
        b = json.dumps(d2b.convert("PLI_M01", fm), ensure_ascii=False, indent=1)
        self.assertEqual(a, b)

    def test_random_khong_vao_output_chi_dung_trong_self_check_seed(self):
        # `import random` trong docx_to_blocks chỉ dùng ở self_check() với seed
        # cố định (20260824 / 42) — không nằm trên đường sinh output.
        src = io.open(os.path.join(TOOLS_DIR, "docx_to_blocks.py"), encoding="utf-8").read()
        uses = [ln.strip() for ln in src.splitlines() if "random" in ln and "import random" not in ln]
        self.assertTrue(all(("rng" in u or "Random" in u) for u in uses),
                        "random phải giới hạn trong rng seed của self_check: %r" % uses)

    def test_fixture_ghi_temp_ngoai_repo_khong_dung_blocks_dir(self):
        tmpdir = tempfile.mkdtemp(prefix="l1_extract_test_")
        self.assertFalse(os.path.abspath(tmpdir).startswith(os.path.abspath(ROOT)))
        path = os.path.join(tmpdir, "%s.docx" % FIXTURE_ID)
        doc = build_fixture_doc()
        attach_footnotes_part(doc)
        doc.save(path)
        doc2 = __import__("docx").Document(path)
        data = d2b.convert_document(doc2, FIXTURE_ID, "fx")
        out = os.path.join(tmpdir, "%s.json" % FIXTURE_ID)
        with io.open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False))
        self.assertTrue(os.path.exists(out))
        self.assertEqual(data["v"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
