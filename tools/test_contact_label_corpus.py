# -*- coding: utf-8 -*-
"""test_contact_label_corpus.py — census + sweep nhãn liên hệ toàn template.

Bối cảnh (defect EML-001/WEB-001, commit d7ec076): nhãn `Thư điện tử (nếu
có):` / `Website (nếu có):` đứng cùng paragraph với giá trị; Word được phép
ngắt dòng ngay sau dấu `:` → nhãn mồ côi cuối dòng, giá trị rơi xuống dòng
kế. Render pass `_keep_contact_label_with_value` (tools/docx_render.py) chèn
NBSP (`\\u00a0`) ngay sau `:` của mọi nhãn để nhãn + giá trị chuyển dòng
CÙNG nhau; khi chính giá trị dài hơn bề rộng dòng, Word ngắt BÊN TRONG giá
trị (URL chỉ gãy trong nó — hợp pháp).

Suite này NÂNG verify từ 1 form (PLII_M02, tools/test_email_label_wrap.py)
lên TOÀN BỘ template active:

  [CENSUS] Đếm form + occurrence của nhãn (mọi biến thể `(nếu có)`/không
           ngoặc) trên word/document.xml của template active theo
           current_law — pin số lượng DERIVED để thay đổi template phải
           cập nhật pin một cách có chủ đích.
  [SWEEP]  Với MỖI form có nhãn: export 1 fixture (payload valid-full +
           GHÉ ĐÈ giá trị email/website DÀI tại mọi key liên hệ) qua ĐÚNG
           đường production Bridge.export (LO normalize + PDF), rồi:
             a) DOCX trên đĩa: KHÔNG occurrence nhãn nào còn dấu CÁCH THƯỜNG
                sau `:` — mọi occurrence phải là `:\\u00a0`;
             b) text-layer PDF: trên MỌI dòng chứa nhãn, ngay sau `:` là
                NBSP + ký tự không khoảng trắng (giá trị BẮT ĐẦU trên cùng
                dòng với nhãn — nhãn không bao giờ mồ côi cuối dòng).

Chạy: python3 -X utf8 -m tools.test_contact_label_corpus  (từ root repo)
Evidence sweep ghi tại generated_ho_so/_visual_layout/phase10_contact/_sweep/
"""
from __future__ import annotations

import re
import shutil
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_fixtures import (                    # noqa: E402
    active_form_ids, build_fixture, ValueFactory,
)
from tools.phase5_visual_gate import MAPS_PATH          # noqa: E402

try:
    import fitz  # pymupdf
except ImportError:                                    # pragma: no cover
    fitz = None

BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
SWEEP_ROOT = (ROOT / "generated_ho_so" / "_visual_layout" /
              "phase10_contact" / "_sweep")

# Nhãn liên hệ — ĐỒNG BỘ với _CONTACT_LABEL_VALUE_RE trong tools/docx_render.py
# LƯU Ý: bản FIND (không đòi dấu cách sau ':') dùng cho ĐỌC output đã render —
# sau pass NBSP, ': ' (cách thường) đã đổi thành ':\u00a0' nên regex nguồn
# (kết thúc `\x20`) không bao giờ khớp text rendered nữa.
LABEL_FIND_RE = re.compile(r"(?:Thư điện tử|Website)\s*(?:\([^)]*\))?\s*:", re.I)
_PARA_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.S)
_WT_RE = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
_TAG_RE = re.compile(r"\{([A-Za-z0-9_.]+)\}")

# Giá trị dài dùng chung cho sweep (giống test_email_label_wrap — proven wrap)
LONG_EMAIL = "bo-phan-ho-tro-khach-hang-va-ho-so-dang-ky-kinh-doanh@example.com"
LONG_WEBSITE = ("https://cong-ty-co-ten-mien-rat-dai"
                "-cho-ho-kinh-doanh.example.vn")


def _para_texts(xml: str) -> list[str]:
    return ["".join(_WT_RE.findall(p)) for p in _PARA_RE.findall(xml)]


def census_contact_labels() -> tuple[dict[str, int], int]:
    """Census nhãn trên template active. Trả về ({form_id: số occurrence},
    tổng occurrence). Ghép text các w:t trong từng paragraph để nhãn tách
    nhiều run vẫn được đếm (cùng cách _keep_contact_label_with_value định vị).
    """
    maps = _maps()
    active, _skipped = active_form_ids(maps)
    per_form: dict[str, int] = {}
    for fid in active:
        template = ROOT / "app" / maps[fid]["template"]
        with zipfile.ZipFile(template) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        n = sum(len(list(LABEL_FIND_RE.finditer(t))) for t in _para_texts(xml))
        if n:
            per_form[fid] = n
    return per_form, sum(per_form.values())


_MAPS_CACHE: dict = {}


def _maps() -> dict:
    if not _MAPS_CACHE:
        import json
        _MAPS_CACHE.update(
            json.loads(MAPS_PATH.read_text(encoding="utf-8")))
    return _MAPS_CACHE


def _long_value_for_key(key: str) -> str | None:
    """Giá trị dài thay cho key liên hệ (key chứa 'email' -> email dài,
    'website' -> URL dài). Key khác (dien_thoai, dn.*, ve_viec…) giữ giá trị
    fixture — NBSP gắn sau nhãn không phụ thuộc loại giá trị."""
    k = key.lower()
    if "email" in k:
        return LONG_EMAIL
    if "website" in k:
        return LONG_WEBSITE
    return None


class ContactLabelCensus(unittest.TestCase):
    """[CENSUS] pin số lượng DERIVED từ template hiện hành."""

    def test_census_matches_derived_pin(self):
        # Pin DERIVED 2026-09-10 @ d7ec076: 67/86 form active có nhãn,
        # 173 occurrence. Template đổi (thêm/bớt mẫu, sửa nhãn) -> cập nhật
        # pin CÓ CHỦ ĐÍCH kèm evidence, không phải nới lỏng mù.
        per_form, total = census_contact_labels()
        self.assertEqual(len(per_form), 67,
                         "số form active có nhãn đổi: %s" % sorted(per_form))
        self.assertEqual(total, 173, "tổng occurrence đổi: %r" % per_form)
        # các form chốt defect gốc phải nằm trong census
        for fid in ("PLII_M02", "PLI_M45", "PLI_M70"):
            self.assertIn(fid, per_form)

    def test_every_label_occurrence_has_bound_value_key(self):
        # Mỗi occurrence phải có ít nhất 1 {key} theo sau trong cùng paragraph
        # (nếu không, NBSP có gắn cũng không có giá trị để giữ — occurrence
        # dạng đó cần được nhìn thấy, không lọt vòng sweep).
        maps = _maps()
        active, _ = active_form_ids(maps)
        orphans = []
        for fid in active:
            template = ROOT / "app" / maps[fid]["template"]
            with zipfile.ZipFile(template) as z:
                xml = z.read("word/document.xml").decode("utf-8")
            for text in _para_texts(xml):
                hits = list(LABEL_FIND_RE.finditer(text))
                for i, m in enumerate(hits):
                    end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
                    if not _TAG_RE.search(text[m.end():end]):
                        orphans.append((fid, text[:80]))
        self.assertEqual(orphans, [],
                         "occurrence nhãn không có key giá trị: %r" % orphans[:5])


def _geo_rows(page) -> list[str]:
    """Gom từ của 1 trang PDF theo baseline hình học (~3pt) — get_text()
    thường mode tách dòng theo SPAN chứ không theo hàng thực (tái hiện:
    PLI_M15 p2 — URL cùng hàng nhãn nhưng span riêng làm 'line' đứt giả)."""
    rows: dict[int, list] = {}
    for w in page.get_text("words"):
        rows.setdefault(int(round(w[1] / 3.0)), []).append(w)
    return [" ".join(x[4] for x in sorted(ws, key=lambda w: w[0]))
            for _, ws in sorted(rows.items())]


class ContactLabelSweep(unittest.TestCase):
    """[SWEEP] export production × form có nhãn — NBSP + PDF glue.

    PLI_M72 render theo ĐÚNG pipeline corpus: 5 batch riêng, mỗi batch gắn
    cờ biến thể (dn.loai_hinh + chk flag) như run_export của gate — nhãn của
    M72 nằm trong section có điều kiện, batch 'main' không gắn cờ render 0
    occurrence (không phải defect, là cấu trúc template).
    """

    units: list = []            # (form, tag, docx, pdf)
    rendered_counts: dict = {}  # (form, tag) -> số occurrence rendered

    @classmethod
    def setUpClass(cls):
        if cls.units:
            return
        import json
        maps = _maps()
        per_form, _total = census_contact_labels()
        forms = [f for f in sorted(per_form) if f != "PLI_M72"]
        m72 = "PLI_M72" in per_form
        all_ids = forms + (["PLI_M72"] if m72 else [])
        blocks_all = {}
        for fid in all_ids:
            p = BLOCKS_DIR / ("%s.json" % fid)
            if p.exists():
                blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))

        def merged(ids: list) -> dict:
            data: dict = {}
            for fid in ids:
                data.update(build_fixture(fid, maps[fid], "valid-full",
                                          blocks_all.get(fid), ValueFactory()))
            overridden = 0
            for key in list(data):
                long_val = _long_value_for_key(key)
                if long_val is not None:
                    data[key] = long_val
                    overridden += 1
            # batch M72 đơn form chỉ có 2 key liên hệ (email_khac/website)
            assert overridden >= 2, ("phải ghè được >=2 key liên hệ, got %d"
                                     % overridden)
            return data

        from app_web.main import Bridge
        bridge = Bridge()
        SWEEP_ROOT.parent.mkdir(parents=True, exist_ok=True)
        if SWEEP_ROOT.exists():
            shutil.rmtree(SWEEP_ROOT)

        def export_batch(tag: str, ids: list, data: dict) -> Path:
            payload = {"case_id": "p10_contact_sweep_%s" % tag,
                       "format": "both",
                       "forms": [{"id": f} for f in ids], "data": data}
            r = bridge.export(payload)
            errors = r.get("errors") or []
            assert not errors, "export lỗi (%s): %r" % (tag, errors[:5])
            src = r.get("dir")
            assert src, "export không có thư mục (%s)" % tag
            dst = SWEEP_ROOT / tag
            shutil.move(src, str(dst))  # SWEEP_ROOT đã dọn nên dst chưa tồn tại
            zsrc = Path(str(src) + ".zip")
            if zsrc.exists():
                shutil.move(str(zsrc), str(dst) + ".zip")
            return dst

        batches = [("main", forms, merged(forms))]
        if m72:
            from tools.phase5_fixtures import M72_VARIANTS
            for value, flag in M72_VARIANTS:
                data = merged(["PLI_M72"])
                data["dn.loai_hinh"] = value
                data[flag] = "X"
                batches.append(("m72_%s" % value.lower(), ["PLI_M72"], data))

        for tag, ids, data in batches:
            dst = export_batch(tag, ids, data)
            for fid in ids:
                docx = dst / ("%s.docx" % fid)
                pdf = dst / ("%s.pdf" % fid)
                assert docx.exists() and pdf.exists(), (
                    "thiếu evidence %s/%s" % (tag, fid))
                with zipfile.ZipFile(docx) as z:
                    xml = z.read("word/document.xml").decode("utf-8")
                n = sum(len(list(LABEL_FIND_RE.finditer(t)))
                        for t in _para_texts(xml))
                cls.units.append((fid, tag, docx, pdf))
                cls.rendered_counts[(fid, tag)] = n

    def test_01_all_census_forms_rendered(self):
        per_form, _ = census_contact_labels()
        for fid in sorted(per_form):
            got = [(tag, n) for (f, tag), n in self.rendered_counts.items()
                   if f == fid]
            with self.subTest(form=fid):
                self.assertTrue(got, "thiếu unit sweep cho %s" % fid)
                for tag, n in got:
                    self.assertGreaterEqual(
                        n, 1,
                        "%s/%s: form có nhãn trong template nhưng rendered 0 "
                        "occurrence" % (fid, tag))

    def test_02_docx_every_label_nbsp(self):
        # (a) mọi occurrence nhãn trong DOCX trên đĩa phải là ':\u00a0'
        for fid, tag, docx, _pdf in self.units:
            with self.subTest(form=fid, tag=tag):
                with zipfile.ZipFile(docx) as z:
                    xml = z.read("word/document.xml").decode("utf-8")
                bad = []
                total = 0
                for text in _para_texts(xml):
                    for m in LABEL_FIND_RE.finditer(text):
                        total += 1
                        nxt = text[m.end():m.end() + 1]
                        if nxt != "\u00a0":
                            bad.append(text[max(0, m.start() - 24):
                                            m.end() + 32])
                self.assertEqual(
                    bad, [],
                    "%s/%s: %d/%d occurrence nhãn KHÔNG có NBSP sau ':'"
                    % (fid, tag, len(bad), total))

    def test_03_pdf_value_starts_on_label_line(self):
        # (b) PDF hình học: sau ':' của nhãn PHẢI còn chữ của giá trị trên
        # CÙNG hàng — nhãn không bao giờ đứng cuối hàng một mình (ngắt chỉ
        # được xảy ra BÊN TRONG giá trị). Đo theo hàng hình học (words+baseline)
        # thay vì get_text() per-span (đứt giả — PLI_M15 p2).
        self.assertIsNotNone(fitz, "cần pymupdf (fitz) để đọc text-layer PDF")
        checked = 0
        nbsp_plain = 0
        for fid, tag, _docx, pdf in self.units:
            with self.subTest(form=fid, tag=tag):
                bad = []
                with fitz.open(pdf) as doc:
                    for pno, page in enumerate(doc, start=1):
                        plain = page.get_text()
                        nbsp_plain += plain.count("\u00a0")
                        for line in _geo_rows(page):
                            for m in LABEL_FIND_RE.finditer(line):
                                checked += 1
                                tail = line[m.end():].replace("\u00a0", "")
                                if not tail.strip():
                                    bad.append("p%d %r" % (pno, line[:96]))
                self.assertEqual(
                    bad, [],
                    "%s/%s: %d hàng PDF tách giá trị khỏi nhãn: %s"
                    % (fid, tag, len(bad), bad[:3]))
        print("[contact-sweep] PDF label occurrences checked: %d "
              "(NBSP glyphs in plain text-layer: %d)" % (checked, nbsp_plain))

    def test_04_rendered_census_report(self):
        # Báo cáo census rendered vs template (in ra để log suite tự chứa)
        per_form, total = census_contact_labels()
        print("[contact-sweep] template census: %d form / %d occurrence"
              % (len(per_form), total))
        for fid in sorted(per_form):
            counts = {tag: n for (f, tag), n in self.rendered_counts.items()
                      if f == fid}
            print("[contact-sweep] %-10s template=%-3d rendered=%s %s"
                  % (fid, per_form[fid], counts,
                     "OK" if any(n >= 1 for n in counts.values())
                     else "NOT-RENDERED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
