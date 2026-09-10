# -*- coding: utf-8 -*-
"""test_a8_trailing_sig_trim.py — A-8 P1.1(a): cụm ký mồ côi trang 2
PLI_M45/M53 (audit phase9_bandfix 2026-09-09, §2 A-8 + §4).

Gốc rễ (render): tail body sau _drop_trailing_empty_para là
  [para rỗng (before=120)][Nơi nhận… (before=120)][TRƯỜNG ĐƠN VỊ (before=120,
  keepLines)][sectPr] — cụm ký nguyên khối 27.2pt trong khi trang trước còn
  25pt (M45) / 6.5pt (M53) → tràn trang 2 mồ côi. E4 (_trim_trailing_sig_gap)
  no-op vì para kề trên cụm là NỘI DUNG (para rỗng nằm cách 2 bậc).

Fix render (whitespace-only, registry-gated):
  `_trim_trailing_sig_before` — CHỈ form có
  phase5r_expectations[form].signature.trailing_before_trim (PLI_M45/M53):
    1. zero w:before paragraph tiêu đề cụm ký cuối body;
    2. xoá paragraph rỗng kề TRƯỚC paragraph nội dung cuối (thu hồi ~1 dòng
       ~20pt) — đủ cho M45; M53 còn thiếu ~1-3pt (cận biên đúng audit P1.1(a)
       ghi; phần dư thuộc phương án (c) P1.2 A4 geometry — quyết owner).

Mệnh đề kiểm chứng:
  [UNIT]     synthetic XML: flag on -> zero before + xoá para rỗng; flag off
             / cụm không cuối body / trước cụm rỗng (vùng E4) / before<120 /
             không phải cụm ký -> xml byte-identical; idempotent ×2.
  [RENDER]   PLI_M45/M53 render thật: tail có before="0" + không còn para
             rỗng trước "Nơi nhận"; form đối chứng PLI_M47 (cùng shape tail,
             KHÔNG flag) nguyên vẹn (before="120", para rỗng còn).
  [PAGINATE] PLI_M45 empty-paper/valid-minimal về 1 trang (đo trên corpus
             v3 phase10_contact — pin kèm evidence render; M53 giữ 2 trang
             trạng thái đã adjudicate (i) allowlist, chờ owner P1.2).

Chạy: python3 -X utf8 -m tools.test_a8_trailing_sig_trim  (từ root repo)
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.docx_render import (                         # noqa: E402
    _trim_trailing_sig_before, check_output, write_rendered,
)
from tools.phase5_visual_gate import _fold   # noqa: E402  (fold NFD-ASCII)

MAPS = json.loads((ROOT / "app" / "data" / "form_maps.json")
                  .read_text(encoding="utf-8"))
BODY_RE = re.compile(r"(<w:body[^>]*>)(.*)(</w:body>)", re.S)

SIG_P = ('<w:p><w:pPr><w:spacing w:before="120" w:after="0"/>'
         '<w:keepLines/></w:pPr><w:r><w:t>TRƯỜNG ĐƠN VỊ</w:t></w:r>'
         '<w:r><w:t>(Ký, ghi họ tên và đóng dấu)</w:t></w:r></w:p>')
NOI_NHAN_P = ('<w:p><w:pPr><w:spacing w:before="120" w:after="0"/></w:pPr>'
              '<w:r><w:t>Nơi nhận:- Lưu:</w:t></w:r></w:p>')
EMPTY_P = ('<w:p><w:pPr><w:spacing w:before="120" w:after="0"/></w:pPr></w:p>')
SECT_PR = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
           '<w:pgMar w:bottom="1440"/></w:sectPr>')


def _doc(*children: str) -> str:
    return ('<w:document><w:body>' + "".join(children) + '</w:body>'
            '</w:document>')


def _last_spacing(xml: str) -> str | None:
    body = BODY_RE.search(xml).group(2)
    paras = re.findall(r"<w:p(?:\s[^>]*)?>.*?</w:p>", body, re.S)
    m = re.search(r'w:before="(\d+)"', paras[-1])
    return m.group(1) if m else None


def _has_empty_before_last_content(xml: str) -> bool:
    body = BODY_RE.search(xml).group(2)
    paras = re.findall(r"<w:p(?:\s[^>]*)?>.*?</w:p>", body, re.S)
    # tail mẫu sau fix: [nội dung][cụm ký] — trước đó là [rỗng][nội dung][cụm]
    for i in range(len(paras) - 2):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", paras[i]))
        if not t.strip():
            return True
    return False


class UnitTrimTrailingSigBefore(unittest.TestCase):
    DOC_TAIL = (_doc('<w:p><w:r><w:t>Mã số: 0312345678</w:t></w:r></w:p>',
                     EMPTY_P, NOI_NHAN_P, SIG_P, SECT_PR))

    def test_flagged_form_zeroes_before_and_drops_empty(self):
        got = _trim_trailing_sig_before(self.DOC_TAIL, "PLI_M45")
        self.assertEqual(_last_spacing(got), "0",
                         "cụm ký cuối phải before=0")
        # nội dung giữ nguyên + para rỗng biến mất
        self.assertIn("Mã số: 0312345678", got)
        self.assertIn("Nơi nhận:- Lưu:", got)
        self.assertNotIn(EMPTY_P, got, "para rỗng phải bị xoá")

    def test_unflagged_form_is_byte_identical(self):
        # PLI_M47 cùng shape tail nhưng KHÔNG flag -> nguyên vẹn
        got = _trim_trailing_sig_before(self.DOC_TAIL, "PLI_M47")
        self.assertEqual(got, self.DOC_TAIL)

    def test_idempotent_second_run_byte_identical(self):
        once = _trim_trailing_sig_before(self.DOC_TAIL, "PLI_M45")
        twice = _trim_trailing_sig_before(once, "PLI_M45")
        self.assertEqual(once, twice)

    def test_sig_not_last_body_child_untouched(self):
        doc = _doc(SIG_P, '<w:p><w:r><w:t>Phụ lục sau cụm ký</w:t></w:r></w:p>',
                   SECT_PR)
        self.assertEqual(_trim_trailing_sig_before(doc, "PLI_M45"), doc)

    def test_empty_para_adjacent_to_sig_is_e4_territory(self):
        # [rỗng][cụm ký]: vùng _trim_trailing_sig_gap — pass này không đụng
        doc = _doc('<w:p><w:r><w:t>Mã số: 0312345678</w:t></w:r></w:p>',
                   EMPTY_P, SIG_P, SECT_PR)
        self.assertEqual(_trim_trailing_sig_before(doc, "PLI_M45"), doc)

    def test_low_before_untouched(self):
        sig_low = SIG_P.replace('w:before="120"', 'w:before="60"')
        doc = _doc('<w:p><w:r><w:t>Mã số</w:t></w:r></w:p>',
                   EMPTY_P, NOI_NHAN_P, sig_low, SECT_PR)
        self.assertEqual(_trim_trailing_sig_before(doc, "PLI_M45"), doc)

    def test_no_sig_title_untouched(self):
        doc = _doc('<w:p><w:r><w:t>Mã số</w:t></w:r></w:p>', EMPTY_P,
                   NOI_NHAN_P,
                   '<w:p><w:r><w:t>Chú thích thường</w:t></w:r></w:p>',
                   SECT_PR)
        self.assertEqual(_trim_trailing_sig_before(doc, "PLI_M45"), doc)


class RenderTrailingTrim(unittest.TestCase):
    """[RENDER] render production thật — trim áp đúng form, không lan form khác."""

    def _render(self, fid: str) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="a8_"))
        out = tmp / ("%s.docx" % fid)
        from tools.phase5_fixtures import build_fixture, ValueFactory
        blocks = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        data = build_fixture(fid, MAPS[fid], "empty-paper",
                             json.loads(blocks.read_text(encoding="utf-8"))
                             if blocks.exists() else None,
                             ValueFactory())
        write_rendered(ROOT / "app" / MAPS[fid]["template"], data, out,
                       tables_meta=MAPS[fid].get("section_specs") or None)
        return out

    def test_m45_m53_trailing_sig_before_zeroed(self):
        for fid in ("PLI_M45", "PLI_M53"):
            with self.subTest(form=fid):
                out = self._render(fid)
                ok, msg = check_output(out)
                self.assertTrue(ok, msg)
                xml = zipfile.ZipFile(out).read(
                    "word/document.xml").decode("utf-8")
                self.assertEqual(_last_spacing(xml), "0",
                                 "%s: cụm ký cuối body phải before=0" % fid)

    def test_m45_empty_para_before_noi_nhan_dropped(self):
        out = self._render("PLI_M45")
        xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
        paras = re.findall(r"<w:p(?:\s[^>]*)?>.*?</w:p>", xml, re.S)
        tail = paras[-3:]
        texts = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
                 for p in tail]
        self.assertTrue(
            _fold(texts[-1]).startswith("truong don vi"),
            "para cuối phải là cụm ký: %r" % texts)
        self.assertTrue(
            _fold(texts[-2]).startswith("noi nhan"),
            "para kề trên cụm phải là nội dung: %r" % texts)
        # EMPTY_X đã bị xoá: para ngay trước khối [Nơi nhận][cụm ký] phải
        # CÓ nội dung (template gốc đặt para rỗng ở vị trí này)
        if len(paras) >= 4:
            t4 = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", paras[-4]))
            self.assertTrue(
                t4.strip(),
                "para kề trước khối [Nơi nhận][cụm ký] không được rỗng "
                "(para rỗng phải bị xoá); tail=%r" % texts)

    def test_control_form_m47_not_trimmed(self):
        # PLI_M47 cùng tail shape (census 37 form) nhưng không flag —
        # chống lan truyền fix sang phần còn lại của corpus
        out = self._render("PLI_M47")
        xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
        self.assertEqual(_last_spacing(xml), "120",
                         "form không flag phải giữ before=120")

    def test_registry_flags_exactly_m45_m53(self):
        reg = json.loads((ROOT / "tools" / "phase5r_expectations.json")
                         .read_text(encoding="utf-8"))
        flagged = sorted(
            fid for fid, entry in reg.items()
            if isinstance(entry, dict)
            and (entry.get("signature") or {}).get("trailing_before_trim"))
        self.assertEqual(flagged, ["PLI_M45", "PLI_M53"],
                         "flag chỉ được đăng ký cho M45/M53 (audit A-8)")


if __name__ == "__main__":
    unittest.main(verbosity=1)
