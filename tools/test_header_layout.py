#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_header_layout.py — Việc 2 (lệnh owner 2026-08-28): header 2-band.

Sửa layout header các mẫu có ô TÊN DOANH NGHIỆP / TÊN HỘ KINH DOANH. Nguồn
docx scrape được xếp DỌC (mỗi dòng một paragraph căn giữa); bản Word gốc
(Phụ lục II Mẫu 2 / Phụ lục I Mẫu 13 — Thông tư 68/2025/TT-BTC) là 2 băng:

    BAND 1 | TÊN ….. + dòng kẻ | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
           |                    | Độc lập - Tự do - Hạnh phúc  (gạch chân)
    BAND 2 | Số: …              | ……, ngày … tháng … năm …

tools/build_form_maps.py tái dụng 4 paragraph đó thành w:tbl KHÔNG VIỀN 2 cột
TRƯỚC khi gắn the; các paragraph được DI CHUYỂN nguyên vẹn vào ô nên không
thế {..} nào mất.

Mệnh đề kiểm chứng (chạy HOÀN TOÀN sandbox — bfm.OUT_TPL/OUT_DATA trỏ vào
temp, KHÔNG ghi vào app/templates / app/data):

  [CENSUS]  allowlist HEADER_BAND_FORMS phải == đúng tập mẫu có ô band trong
            blocks JSON (detector gập dấu); PLI_M72 là false positive
            và PHẢI ở ngoài (lý do ghi trong source).
            [integ(F0L) 2026-09-06] PLI_M12 ra KHỎI nhóm false positive:
            premise cũ "nguồn mất ô tên + TT 121/2026 đã thay mẫu" không còn
            đúng — M12 đã migrate current-law TT 121/2026 (ảnh p50), nguồn
            mới có khối 4 paragraph header chuẩn -> +vào allowlist (22 -> 23).
  [LAYOUT]  23 mẫu: bảng header đúng 1 cái, đứng ngay sau các paragraph
            "Mẫu số …", 2 hàng x 2 cột, KHÔNG viền, chiều rộng = vùng chữ,
            alignment ô trái/phải đúng, vị trí ô đúng.
  [TEXT]    không mất chữ — ngoại lệ DUY NHẤT là dòng kẻ scraped "-----" dưới
            "Độc lập - Tự do - Hạnh phúc" (được thay bằng w:u thật).
  [MOTTO]   "Độc lập - Tự do - Hạnh phúc" được gạch chân (w:u val=single).
  [FIELDS]  tập field của CẢ 87 mẫu không đổi so với form_maps.json đang
            commit (refactor _assign_para_slots không được trôi rule nào).
  [TAGS]    mọi the {..} từng nằm trong 4 paragraph header đều còn trong bảng;
            converter blocks (docx_to_blocks) đọc được bảng mới và giữ input.
  [IDEMPOT] chạy process_form LẦN 1 và LẦN 2 từ cùng nguồn -> canonical XML
            hash + meta hash GIỐNG HỆT.
  [NEG]     nguồn lệch dạng (mất paragraph ngày ký / ô tên) -> ValueError
            (fail loud, không bao giờ bỏ im).
  [GUARD]   checksum app/templates + app/data KHÔNG đổi trong suốt test.

Chạy:  python3 -X utf8 -m tools.test_header_layout     (từ root repo/worktree)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.build_form_maps as bfm          # noqa: E402
import tools.docx_to_blocks as dxtb          # noqa: E402

BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
TEMPLATES_DIR = ROOT / "app" / "templates"

_results: list[tuple[bool, str]] = []
_tmp_root: Path | None = None


def check(name: str):
    def deco(fn):
        def run(*args, **kw):
            try:
                fn(*args, **kw)
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    return bfm.fold(re.sub(r"\s+", " ", text or "")).strip()


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------

class Sandbox:
    """Đổi bfm.OUT_TPL/OUT_DATA sang temp; giữ checksum app/ để đối chiếu."""

    def __enter__(self):
        global _tmp_root
        _tmp_root = Path(tempfile.mkdtemp(prefix="hdr2col_"))
        self.tpl = _tmp_root / "templates"
        self.data = _tmp_root / "data"
        self.tpl.mkdir()
        self.data.mkdir()
        self.saved = (bfm.OUT_TPL, bfm.OUT_DATA)
        bfm.OUT_TPL = self.tpl
        bfm.OUT_DATA = self.data
        bfm._form_spec_cache.clear()
        self.guards = {}
        for base in (TEMPLATES_DIR, ROOT / "app" / "data"):
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    self.guards[str(p)] = _sha_file(p)
        return self

    def __exit__(self, *exc):
        bfm.OUT_TPL, bfm.OUT_DATA = self.saved
        bfm._form_spec_cache.clear()
        shutil.rmtree(_tmp_root, ignore_errors=True)
        return False

    def assert_repo_untouched(self):
        drifted = []
        for base in (TEMPLATES_DIR, ROOT / "app" / "data"):
            for p in sorted(base.rglob("*")):
                if not p.is_file():
                    continue
                if _sha_file(p) != self.guards.get(str(p)):
                    drifted.append(p)
        assert not drifted, "file trong app/ bị ghi ngoài sandbox: %s" % drifted[:4]


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_xml_sha(path: Path) -> str:
    """sha256 trên word/document.xml ĐÃ chuẩn hoá (bỏ zip timestamp)."""
    with zipfile.ZipFile(str(path)) as zf:
        raw = zf.read("word/document.xml")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Đọc cấu trúc header band từ 1 template
# ---------------------------------------------------------------------------

def header_band_table(doc):
    """Bảng header 2-band = w:tbl ĐẦU TIÊN của thân, phải là lưới 2x2."""
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:tbl"):
            tbl = Table(child, doc)
            if len(tbl.rows) == 2 and len(tbl.columns) == 2:
                return tbl
            return None
    return None


def body_texts_before_table(doc):
    out = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:tbl"):
            return out
        if child.tag == qn("w:p"):
            out.append(Paragraph(child, doc).text)
    return out


def cell_para(cell):
    return cell.paragraphs[0]


def cell_text(cell):
    return "\n".join(p.text for p in cell.paragraphs)


def is_borderless(tbl):
    tblPr = tbl._tbl.tblPr
    tb = tblPr.find(qn("w:tblBorders"))
    if tb is None:
        return False
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = tb.find(qn("w:%s" % edge))
        if e is None or e.get(qn("w:val")) not in ("nil", "none"):
            return False
    for row in tbl.rows:
        for cell in row.cells:
            tcPr = cell._tc.find(qn("w:tcPr"))
            if tcPr is None:
                return False
            cb = tcPr.find(qn("w:tcBorders"))
            if cb is None:
                return False
            for edge in ("top", "left", "bottom", "right"):
                e = cb.find(qn("w:%s" % edge))
                if e is None or e.get(qn("w:val")) not in ("nil", "none"):
                    return False
    return True


def visible_text(doc):
    parts = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            parts.append(Paragraph(child, doc).text)
        elif child.tag == qn("w:tbl"):
            tbl = Table(child, doc)
            for row in tbl.rows:
                for cell in row.cells:
                    parts.append("\n".join(p.text for p in cell.paragraphs))
    return "".join(parts)


# ---------------------------------------------------------------------------
# [CENSUS]
# ---------------------------------------------------------------------------

BAND_LABEL_FOLD = ("ten doanh nghiep", "ten ho kinh doanh")


def blocks_band_label_ids():
    """Mẫu nào trong blocks JSON có bảng header band (đầu tài liệu).

    Sau khi Lead regen (merge hdr2col @ 084444d), ô "TÊN …" KHÔNG còn là
    paragraph form-subtitle đứng riêng mà nằm trong bảng header 2 band —
    extractor gắn marker `band: "header"` (docx_to_blocks.is_header_band_table).
    Pin đổi theo bằng chứng sản phẩm mới: census vẫn ÉP ĐÚNG tập mẫu
    (23 mẫu sau [integ(F0L) 2026-09-06] +PLI_M12 current-law p50),
    chỉ đổi cách nhận diện từ paragraph-sang-bảng. Trạng thái pre-regen
    (ô tên còn là paragraph) vẫn được nhận để suite đọc được ở cả 2 thời điểm.
    """
    hits = []
    for jf in sorted(BLOCKS_DIR.glob("*.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        for blk in d.get("blocks", [])[:12]:
            # trạng thái MỚI (post-regen): bảng header band có marker
            if blk.get("t") == "table" and blk.get("band") == "header":
                hits.append(jf.stem)
                break
            # trạng thái CŨ (pre-regen): ô tên là paragraph riêng
            if blk.get("t") != "p" or blk.get("role") != "form-subtitle":
                continue
            txt = "".join(r.get("text", "") for r in blk.get("runs", []))
            f = fold(txt)
            for lab in BAND_LABEL_FOLD:
                if f.startswith(lab):
                    rest = f[len(lab):].strip().strip(":").strip()
                    if rest == "" or bfm.HEADER_BAND_RULE_RE.match(rest):
                        hits.append(jf.stem)
                    break
            if jf.stem in hits:
                break
    return sorted(set(hits))


@check("[CENSUS] allowlist 23 mau == dung tap mau co o band trong blocks JSON")
def t_census():
    got = blocks_band_label_ids()
    want = sorted(bfm.HEADER_BAND_FORMS)
    assert got == want, ("census lệch:\n  blocks có mà allowlist thiếu: %s\n"
                         "  allowlist có mà blocks không có: %s"
                         % (sorted(set(got) - set(want)),
                            sorted(set(want) - set(got))))
    # [integ(F0L) 2026-09-06] 22 -> 23: +PLI_M12 (current-law TT 121/2026,
    # ảnh p50 — premise cũ "false positive, chờ nguồn mới" hết hiệu lực vì
    # nguồn migrate đã có khối header chuẩn + blocks JSON có ô band).
    assert len(want) == 23, "census kỳ vọng 23 mẫu, thấy %d" % len(want)
    pli = sorted(x for x in want if x.startswith("PLI_"))
    plii = sorted(x for x in want if x.startswith("PLII_"))
    assert pli == ["PLI_M12", "PLI_M13", "PLI_M14", "PLI_M15", "PLI_M17",
                   "PLI_M18", "PLI_M19", "PLI_M21", "PLI_M23", "PLI_M25",
                   "PLI_M26", "PLI_M27", "PLI_M28", "PLI_M29", "PLI_M30",
                   "PLI_M31", "PLI_M32", "PLI_M33"], pli
    assert plii == ["PLII_M02", "PLII_M03", "PLII_M04", "PLII_M05",
                    "PLII_M06"], plii
    # false positive PHẢI ở ngoài allowlist
    # [integ(F0L) 2026-09-06] bỏ PLI_M12 khỏi pin âm — đã +vào allowlist;
    # PLI_M72 vẫn là false positive ('(TÊN DOANH NGHIỆP TƯ NHÂN)' là subtitle
    # mục công bố, không có khối quốc hiệu).
    for fid in ("PLI_M72",):
        assert fid not in bfm.HEADER_BAND_FORMS, (
            "%s không phải ô header 2-band ('(TÊN DOANH NGHIỆP TƯ NHÂN)' là "
            "subtitle mục công bố)" % fid)


@check("[CENSUS] nguon docx 23 mau deu nhan dien duoc 4 paragraph header")
def t_census_sources():
    for fid, label in sorted(bfm.HEADER_BAND_FORMS.items()):
        src = bfm.find_source(fid)
        doc = Document(str(src))
        el = _find_label_element(doc, label)
        assert el is not None, "%s: nguồn không có ô %r" % (fid, label)


def _find_label_element(doc, label):
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        if bfm._hdr_is_label(Paragraph(child, doc).text, label):
            return child
    return None


# ---------------------------------------------------------------------------
# [LAYOUT] / [TEXT] / [MOTTO]
# ---------------------------------------------------------------------------

EXPECTED_CELL_ALIGN = {(0, 0): "left", (0, 1): "center",
                       (1, 0): "left", (1, 1): "right"}
ALIGN_ENUM = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}

# [integ(F0L) 2026-09-06] Band đứng TUYỆT ĐỐI đầu tài liệu (giấy đề nghị,
# không có dòng 'Mẫu số …' phía trước như mẫu Phụ lục). Premise cũ: toàn bộ
# allowlist là Phụ lục -> 'Mẫu số' luôn có. Hiện trạng: +PLI_M12 (TT 121/2026
# p50) phá premise đó; evidence: source PL1_Mau_12_tach_tu_file_full.docx
# paragraph 0 chính là ô 'TÊN DOANH NGHIỆP'.
TOP_BAND_FORMS = {"PLI_M12"}


def source_header_texts(fid, label):
    """Text 4 paragraph header của NGUỒN: [ô tên, quốc hiệu, Số, ngày ký]."""
    src = Document(str(bfm.find_source(fid)))
    el = _find_label_element(src, label)
    kids = list(src.element.body.iterchildren())
    idx = kids.index(el)
    return [Paragraph(k, src).text for k in kids[idx:idx + 4]]


def motto_two_lines(motto_text):
    """Khối quốc hiệu về 2 dòng: bỏ dòng kẻ scraped ở cuối."""
    lines = motto_text.split("\n")
    assert bfm.HEADER_BAND_RULE_RE.match(lines[-1].strip()), \
        "dòng cuối quốc hiệu không phải dòng kẻ: %r" % lines[-1]
    return "\n".join(lines[:-1])


@check("[LAYOUT] 23 mau: bang khong vien 2x2, alignment + vi tri o dung")
def t_layout():
    with Sandbox() as sb:
        for fid, label in sorted(bfm.HEADER_BAND_FORMS.items()):
            src_texts = source_header_texts(fid, label)
            meta, _un = bfm.process_form(bfm.find_source(fid), {}, None)
            tpl = sb.tpl / ("%s.docx" % fid)
            assert tpl.exists(), "%s: chưa ghi template" % fid
            doc = Document(str(tpl))
            tbl = header_band_table(doc)
            assert tbl is not None, "%s: không thấy bảng header 2x2 ở đầu thân" % fid
            assert len(tbl.rows) == 2 and len(tbl.columns) == 2, \
                "%s: bảng %dx%d != 2x2" % (fid, len(tbl.rows), len(tbl.columns))
            assert is_borderless(tbl), "%s: bảng header vẫn còn viền" % fid
            # căn lề từng ô
            for (ri, ci), mode in EXPECTED_CELL_ALIGN.items():
                p = cell_para(tbl.rows[ri].cells[ci])
                got = str(p.alignment).split(" ")[0] if p.alignment is not None \
                    else "LEFT"
                assert got == ALIGN_ENUM[mode], (
                    "%s: ô (%d,%d) align %s != %s" % (fid, ri, ci, got, mode))
            # nội dung từng ô = nguồn (băng 1 phải) / nguồn + the (băng 2)
            # [WAVE v7 HEADER-NAME-SYNC] form bật binding: ô (0,0) được
            # generator bind the {key} của registry.
            # [Pin sync — owner band-label removal 2026-09-08] commit e148d83:
            # _bind_header_name_slot XOÁ TOÀN BỘ run (nhãn 'TÊN …' + dòng
            # kẻ) thay bằng ĐÚNG 1 run the {key} — band in ra CHỈ hiện tên.
            # Pin mới: ô (0,0) == the {key}, KHÔNG còn nhãn/dòng kẻ.
            src00 = src_texts[0]
            _bind = bfm.header_name_binding()["forms"].get(fid)
            if _bind:
                src00 = "{%s}" % _bind["key"]
            expected = {
                (0, 0): src00,
                (0, 1): motto_two_lines(src_texts[1]),                 # bỏ dòng kẻ
                (1, 0): "Số: {so_van_ban}",
                # [6V-V2/C1] pin lại theo skeleton đã normalize glue (B1/D13):
                # space quanh {ngay_ky_vb}/{thang_ky_vb} — rule tại
                # build_form_maps.normalize_skeleton_glue
                (1, 1): ("{dia_diem_ky}, ngày {ngay_ky_vb} "
                         "tháng {thang_ky_vb} năm {nam_ky_vb}"),
            }
            for (ri, ci), want in expected.items():
                got = cell_text(tbl.rows[ri].cells[ci])
                assert got == want, (
                    "%s: ô (%d,%d) = %r != %r" % (fid, ri, ci, got, want))
            # băng 1 PHẢI cùng hàng ngang: ô trái (tên) và ô phải (quốc hiệu)
            # [Pin sync — owner band-label removal 2026-09-08] ô trái CHỈ có
            # the {key} — nhãn không được còn lại ở band.
            if _bind:
                c00 = cell_text(tbl.rows[0].cells[0])
                assert c00 == "{%s}" % _bind["key"], \
                    "%s: ô (0,0) phải CHỈ chứa the %s: %r" % (
                        fid, _bind["key"], c00)
                assert not fold(c00).startswith(
                    tuple(fold(l) for l in BAND_LABEL_FOLD)), \
                    "%s: band còn nhãn pháp lý (owner đã xoá 2026-09-08): %r" % (
                        fid, c00)
            assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in cell_text(tbl.rows[0].cells[1])
            # băng 2: Số trái, ngày tháng năm phải, cùng hàng
            assert cell_text(tbl.rows[1].cells[0]).startswith("Số:")
            assert "tháng" in cell_text(tbl.rows[1].cells[1])
            # các paragraph "Mẫu số …" vẫn nằm TRƯỚC bảng (không bị hút vào ô);
            # KHÔNG còn paragraph header dọc nào sót lại trước bảng
            # [integ(F0L) 2026-09-06] PLI_M12 là GIẤY ĐỀ NGHỊ (TT 121/2026,
            # ảnh p50) — band đứng ở ĐẦU tài liệu, KHÔNG có dòng 'Mẫu số …'
            # phía trước (đó là contract của mẫu Phụ lục). Contract riêng cho
            # nhóm này: KHÔNG text nào đứng trước band (assert thật, không
            # phải bypass).
            before = [t for t in body_texts_before_table(doc) if t.strip()]
            if fid in TOP_BAND_FORMS:
                assert before == [], \
                    "%s: band phải đứng đầu tài liệu, thấy %r" % (fid, before)
            else:
                assert any("Mẫu số" in t for t in before), \
                    "%s: mất dòng 'Mẫu số …' trước bảng: %r" % (fid, before)
            for t in before:
                assert "CỘNG HÒA" not in t and "Số:" not in t \
                    and not t.startswith(label), \
                    "%s: sót paragraph header dọc trước bảng: %r" % (fid, t)
            # chiều rộng = vùng chữ, tổng cột khớp tblW
            tblW = tbl._tbl.tblPr.find(qn("w:tblW"))
            total = int(tblW.get(qn("w:w")))
            assert total == bfm._band_usable_width_twips(doc), \
                "%s: tblW %s != vùng chữ" % (fid, total)
            cols = [int(c.width / 635) for c in tbl.columns]
            assert sum(cols) == total, "%s: tổng gridCol %s != %s" % (fid, cols, total)
            right = cols[1]
            assert right >= total * 0.5, (
                "%s: cột phải %d twips quá hẹp cho khối quốc hiệu (tblW=%d)"
                % (fid, right, total))
            # thuộc tính tạm đã được scrub trước khi lưu
            assert tbl._tbl.get(bfm.HEADER_BAND_TEMP_ATTR) is None, \
                "%s: còn sót thuộc tính tạm %s" % (fid, bfm.HEADER_BAND_TEMP_ATTR)
            assert not [u for u in _un if str(u.get("where", "")).startswith("hdr")], \
                "%s: unmatched phát sinh ở bảng header: %r" % (
                    fid, [u for u in _un if str(u.get("where", "")).startswith("hdr")][:3])
        sb.assert_repo_untouched()


@check("[TEXT] khong mat chu — ngoai le duy nhat la dong ke scraped '-----'")
def t_text_preserved():
    # chuẩn hoá: dãy dấu chấm (nguồn) và the {key} (kết quả) -> cùng 1 marker,
    # bỏ mọi khoảng trắng — so sánh CHỈ nội dung chữ, không so cách gắn the.
    def norm(s):
        s = bfm.DOT_RUN.sub("", s)
        s = re.sub(r"\{[#/?]?[A-Za-z0-9_.]+\}", "", s)
        return re.sub(r"\s+", "", fold(s))
    with Sandbox() as sb:
        for fid, label in sorted(bfm.HEADER_BAND_FORMS.items()):
            src = Document(str(bfm.find_source(fid)))
            # 4 paragraph header ở NGUỒN
            el = _find_label_element(src, label)
            kids = list(src.element.body.iterchildren())
            idx = kids.index(el)
            before = [Paragraph(k, src).text for k in kids[idx:idx + 4]]
            bfm.process_form(bfm.find_source(fid), {}, None)
            doc = Document(str(sb.tpl / ("%s.docx" % fid)))
            new_txt = visible_text(doc)
            tbl = header_band_table(doc)
            after = [cell_text(tbl.rows[ri].cells[ci])
                     for ri in (0, 1) for ci in (0, 1)]
            # dòng kẻ scraped duy nhất bị bỏ = dòng CUỐI của khối quốc hiệu
            motto_lines = before[1].split("\n")
            rule = motto_lines[-1].strip()
            assert bfm.HEADER_BAND_RULE_RE.match(rule), (
                "%s: dòng cuối quốc hiệu %r không phải dòng kẻ" % (fid, rule))
            # dòng kẻ điền tên ở ô trái phải VẪN còn
            assert any(bfm.HEADER_BAND_RULE_RE.match(ln.strip())
                       for ln in before[0].split("\n")), (
                           "%s: ô trái mất dòng kẻ điền tên" % fid)
            expect = list(before)
            expect[1] = "\n".join(motto_lines[:-1])
            # [WAVE v7 HEADER-NAME-SYNC] form nằm registry mirror: dòng kẻ
            # điền tên ô trái được generator thay bằng the {key} — norm()
            # gỡ the nên hai phía phải quy về cùng chữ. Chỉ form BẬT binding
            # mới áp (M33/PLII_M06 blocked_owner giữ nguyên dòng kẻ).
            #dash-run đầu tiên trong tài liệu CHÍNH LÀ dòng kẻ của slot tên
            # (label para đứng trước quốc hiệu/Số/ngày) — visible_text có thể
            # không giữ \n nên so bằng regex thay vì theo dòng.
            _dash_run_re = re.compile(r"[-_.\u2013\u2014\u2026]{3,}")

            def _swap_label_rule(text):
                bind = bfm.header_name_binding()["forms"].get(fid)
                if not bind:
                    return text
                return _dash_run_re.sub("{%s}" % bind["key"], text, count=1)
            # [Pin sync — owner band-label removal 2026-09-08] commit e148d83:
            # generator XOÁ toàn bộ run (nhãn 'TÊN …' + dòng kẻ) và thay bằng
            # ĐÚNG 1 run the {key} — kỳ vọng ô trái là CHỈ the {key}.
            _bind0 = bfm.header_name_binding()["forms"].get(fid)
            expect[0] = ("{%s}" % _bind0["key"]) if _bind0 \
                else _swap_label_rule(expect[0])
            # Toàn bộ chữ còn lại PHẢI GIỮ NGUYÊN (kể cả dòng kẻ điền tên ô trái)
            assert "".join(norm(t) for t in expect) == \
                "".join(norm(t) for t in after), (
                    "%s: MẤT/ĐỔI text header:\n  kỳ vọng %r\n  thực tế %r"
                    % (fid, expect, after))
            # và: cùng pipeline nhưng TẮT header band -> text phải giống hệt
            # (trừ đúng dòng kẻ scraped đã bỏ). So sánh 2 lần chạy generator
            # để phần rebuild bảng/băng khác không can thiệp vào phép so sánh.
            saved_forms = bfm.HEADER_BAND_FORMS
            try:
                bfm.HEADER_BAND_FORMS = {}
                bfm.process_form(bfm.find_source(fid), {}, None)
                plain = visible_text(Document(str(sb.tpl / ("%s.docx" % fid))))
            finally:
                bfm.HEADER_BAND_FORMS = saved_forms
            # [WAVE v7] plain (band tắt) còn dòng kẻ tên; band bật (post
            # e148d83) chỉ còn the {key}, KHÔNG nhãn — quy đồng trước khi so:
            # gỡ dòng kẻ (norm gỡ token) và gỡ nhãn 'TÊN …' khỏi plain
            # [Pin sync — owner band-label removal 2026-09-08].
            plain = _swap_label_rule(plain)
            _n_plain = norm(plain).replace(norm(rule), "", 1)
            if bfm.header_name_binding()["forms"].get(fid):
                _n_plain = _n_plain.replace(norm(label), "", 1)
            assert _n_plain == norm(new_txt), (
                "%s: text tài liệu đổi ngoài cụm header khi bật header band"
                % fid)
        sb.assert_repo_untouched()


@check("[MOTTO] 'Độc lập - Tự do - Hạnh phúc' duoc gach chan that (w:u)")
def t_motto_underline():
    with Sandbox() as sb:
        for fid in sorted(bfm.HEADER_BAND_FORMS):
            bfm.process_form(bfm.find_source(fid), {}, None)
            doc = Document(str(sb.tpl / ("%s.docx" % fid)))
            tbl = header_band_table(doc)
            found = False
            for p in tbl.rows[0].cells[1].paragraphs:
                for run in p.runs:
                    if fold(run.text) == fold("Độc lập - Tự do - Hạnh phúc"):
                        assert run.underline, (
                            "%s: run quốc hiệu dòng 2 chưa gạch chân" % fid)
                        found = True
            assert found, "%s: không tìm thấy run 'Độc lập - Tự do - Hạnh phúc'" % fid
            # dòng kẻ "-----" dưới quốc hiệu phải biến mất
            assert "-----" not in cell_text(tbl.rows[0].cells[1]), (
                "%s: còn sót dòng kẻ scraped trong ô quốc hiệu" % fid)
            # ô trái: [hdr2col base] dòng kẻ điền tên phải còn; [WAVE v7]
            # form BẬT binding mirror thì dòng kẻ được thay bằng the {key}
            # — kiểm: có dòng kẻ HOẶC the của đúng key registry.
            c0 = cell_text(tbl.rows[0].cells[0])
            bind = bfm.header_name_binding()["forms"].get(fid)
            if bind:
                assert "{%s}" % bind["key"] in c0, (
                    "%s: ô trái phải chứa the mirror %s (WAVE v7)"
                    % (fid, bind["key"]))
            else:
                assert "-----" in c0, (
                    "%s: mất dòng kẻ điền tên ở ô trái" % fid)
        sb.assert_repo_untouched()


# ---------------------------------------------------------------------------
# [FIELDS] / [TAGS]
# ---------------------------------------------------------------------------

@check("[FIELDS] tap field ca 87 mau khong doi so voi form_maps.json commit")
def t_fields_unchanged():
    committed = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    with Sandbox() as sb:
        generated = {}
        for p in bfm.iter_docx_files():
            if p.name.startswith("~$") or p.name.startswith("_"):
                continue
            # [v7-F0] Mirror ĐỦ hợp đồng nguồn canonical của generator
            # (build_form_maps.main()): (1) bỏ bản alias khi form có
            # SOURCE_OVERRIDES (vd M03/M04 tách từ bản gốc đầy đủ — bản cũ
            # 83 fields phải bị bỏ, nếu không first-wins nhặt nhầm bản thô);
            # (2) FIRST-WINS theo id ("Lane D F2") — nguồn PLI_M28 tồn tại
            # 2 bản byte-identical ở 03_ và 04_ (cùng sha256 69fd5022…);
            # last-wins của loop cũ tự tạo lệch path 03_→04_ mà full-regen
            # thật không bao giờ sinh.
            fid, _, _ = bfm.parse_form_id(p)
            if fid in bfm.SOURCE_OVERRIDES and \
                    p.relative_to(bfm.ROOT).as_posix() != \
                    bfm.SOURCE_OVERRIDES[fid]:
                continue
            meta, _un = bfm.process_form(p, bfm.load_csv_titles(), None)
            generated.setdefault(meta["id"], meta)
        assert set(generated) == set(committed), (
            "tập form lệch: %s" % sorted(set(generated) ^ set(committed))[:5])
        for fid in sorted(generated):
            a = committed[fid].get("fields")
            b = generated[fid].get("fields")
            assert a == b, ("%s: fields trôi (%d -> %d)\n  cũ: %r\n  mới: %r"
                            % (fid, len(a or []), len(b or []),
                               (a or [])[:4], (b or [])[:4]))
            for key in ("id", "phu_luc", "mau_so", "ten_mau", "file", "template"):
                assert committed[fid].get(key) == generated[fid].get(key), \
                    "%s: %s đổi" % (fid, key)
            for kind in ("dynamic_tables", "section_specs"):
                ov = committed[fid].get(kind) or []
                nv = generated[fid].get(kind) or []
                if fid in bfm.HEADER_BAND_FORMS:
                    # Hai trạng thái hợp lệ (pin sync theo bằng chứng, merge
                    # hdr2col @ 084444d):
                    #  (a) ĐỒNG NHẤT — trạng thái ổn định sau khi Lead commit
                    #      form_maps regen (sandbox rebuild == đĩa);
                    #  (b) DỊCH +1 — cửa sổ migration: đĩa còn form_maps cũ
                    #      (chưa regen/commit), sandbox build từ nguồn đã có
                    #      bảng header -> MỌI table_index +1, còn lại nguyên.
                    def _is_plus1_shape(ovv, nvv):
                        if len(ovv) != len(nvv):
                            return False
                        for o, n in zip(ovv, nvv):
                            if o.get("table_index") is None or \
                               n.get("table_index") is None or \
                               o.get("table_index") + 1 != n.get("table_index"):
                                return False
                            o2 = dict(o); n2 = dict(n)
                            o2.pop("table_index"); n2.pop("table_index")
                            if o2 != n2:
                                return False
                        return True
                    if ov == nv:
                        continue
                    assert _is_plus1_shape(ov, nv), (
                        "%s/%s: form_maps lệch sandbox — không đồng nhất và "
                        "không đúng hình +1 (migration chưa chạy hoặc metadata "
                        "trôi)" % (fid, kind))
                else:
                    assert ov == nv, ("%s/%s: KHÔNG được đổi khi mẫu không nằm "
                                      "trong allowlist" % (fid, kind))
        sb.assert_repo_untouched()


@check("[TAGS] the header khong mat + converter blocks doc duoc bang moi")
def t_tags_and_blocks():
    with Sandbox() as sb:
        for fid, label in sorted(bfm.HEADER_BAND_FORMS.items()):
            src_doc = Document(str(bfm.find_source(fid)))
            src_tags = []
            el = _find_label_element(src_doc, label)
            idx = list(src_doc.element.body.iterchildren()).index(el)
            for child in list(src_doc.element.body.iterchildren())[idx:idx + 4]:
                src_tags += dxtb.TAG_RE.findall(Paragraph(child, src_doc).text)
            # nguồn sạch (chưa gắn the) -> kỳ vọng 5 slot chuẩn của băng dưới
            assert src_tags == [], "%s: nguồn docx không được còn the %r" % (fid, src_tags)
            want = ["so_van_ban", "dia_diem_ky", "ngay_ky_vb", "thang_ky_vb",
                    "nam_ky_vb"]
            # [WAVE v7] form bật binding: ô (0,0) mang thêm the mirror
            # (quét trước các slot băng dưới trong cùng bảng).
            _bind = bfm.header_name_binding()["forms"].get(fid)
            if _bind:
                want = [_bind["key"]] + want

            meta, _un = bfm.process_form(bfm.find_source(fid), {}, None)
            tpl = sb.tpl / ("%s.docx" % fid)
            doc = Document(str(tpl))
            tbl = header_band_table(doc)
            got = []
            for ri in (0, 1):
                for ci in (0, 1):
                    for p in tbl.rows[ri].cells[ci].paragraphs:
                        got += dxtb.TAG_RE.findall(p.text)
            assert got == want, "%s: the trong bảng header %r != %r" % (fid, got, want)

            blocks = dxtb.convert_document(
                Document(str(tpl)), fid, meta.get("ten_mau", ""),
                overrides={}, footnotes={}, section_specs=None)
            # bảng header là block "table" ĐẦU TIÊN của blocks
            first_tbl = next((b for b in blocks["blocks"]
                              if b.get("t") in ("table", "loop")), None)
            assert first_tbl is not None and first_tbl.get("t") == "table", (
                "%s: block bảng header không đọc được: %r" % (fid, first_tbl))
            cell_inputs = [r["input"]["key"]
                           for row in first_tbl["rows"] for c in row["cells"]
                           for r in c.get("runs", []) if "input" in r]
            # [WAVE v7] run mirror của band (0,0) KHÔNG phải input — danh
            # sách input của converter vẫn là đúng 5 slot băng dưới.
            want_slots = ["so_van_ban", "dia_diem_ky", "ngay_ky_vb",
                          "thang_ky_vb", "nam_ky_vb"]
            # [N-v1/N-v2 2026-09-06] mode='band_input': band (0,0) LÀ ô nhập
            # duy nhất của form — input band nằm TRƯỚC 5 slot băng dưới.
            if _bind and _bind.get("mode") == "band_input":
                want_slots = [_bind["key"]] + want_slots
            assert cell_inputs == want_slots, (
                "%s: converter mất input trong bảng header: %r" % (fid, cell_inputs))
            if _bind and _bind.get("mode") != "band_input":
                mirror_runs = [
                    r["mirror"]["key"]
                    for row in first_tbl["rows"] for c in row["cells"]
                    for r in c.get("runs", []) if "mirror" in r]
                assert mirror_runs == [_bind["key"]], (
                    "%s: converter không sinh run mirror cho band: %r"
                    % (fid, mirror_runs))
            # không mất text toàn tài liệu (docx vs blocks)
            want_txt = re.sub(r"\s+", "",
                              dxtb.collect_docx_text(tpl))
            got_txt = re.sub(r"\s+", "", dxtb.collect_json_text(blocks))
            assert want_txt == got_txt, "%s: text docx vs blocks lệch" % fid
        sb.assert_repo_untouched()


# ---------------------------------------------------------------------------
# [IDEMPOT]
# ---------------------------------------------------------------------------

@check("[IDEMPOT] chay 2 lan tu cung nguon -> hash giong het")
def t_idempotent():
    probes = ["PLII_M02", "PLI_M13", "PLI_M27", "PLI_M33", "PLII_M06"]
    with Sandbox() as sb:
        run1 = {}
        for fid in probes:
            meta, _un = bfm.process_form(bfm.find_source(fid), {}, None)
            tpl = sb.tpl / ("%s.docx" % fid)
            run1[fid] = (_canonical_xml_sha(tpl),
                         json.dumps(meta, ensure_ascii=False, sort_keys=True))
        sb.tpl.mkdir(exist_ok=True)
        for name in list(sb.tpl.iterdir()):
            name.unlink()
        for fid in probes:
            meta, _un = bfm.process_form(bfm.find_source(fid), {}, None)
            tpl = sb.tpl / ("%s.docx" % fid)
            h2 = (_canonical_xml_sha(tpl),
                  json.dumps(meta, ensure_ascii=False, sort_keys=True))
            assert run1[fid] == h2, (
                "%s: lần 2 khác lần 1 (idempotency gãy)" % fid)
        sb.assert_repo_untouched()


@check("[IDEMPOT] mau NGOAI allowlist khong bi dong den")
def t_untouched_forms():
    # [integ(F0L) 2026-09-06] bỏ PLI_M12 khỏi probes — đã +vào allowlist
    # (current-law TT 121/2026 p50), nghĩa Idempotent đổi: 2 lần chạy CÙNG
    # sinh band; mức đó đã cover bởi [IDEMPOT] chính phía trên.
    probes = ["PLI_M01", "PLI_M02", "PLII_M01", "PLI_M72",
              "PLII_M07", "PLI_M43"]
    with Sandbox() as sb:
        for fid in probes:
            meta, _un = bfm.process_form(bfm.find_source(fid), {}, None)
            doc = Document(str(sb.tpl / ("%s.docx" % fid)))
            got = header_band_table(doc)
            assert got is None, ("%s: không được sinh bảng header 2-band" % fid)
            if fid in ("PLI_M72",):
                continue
            # mẫu không trong allowlist: cấu trúc body giữ nguyên (chỉ gắn the)
            texts = [Paragraph(c, doc).text
                     for c in doc.element.body.iterchildren() if c.tag == qn("w:p")]
            assert any("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in t for t in texts), \
                "%s: mất khối quốc hiệu" % fid
        sb.assert_repo_untouched()


# ---------------------------------------------------------------------------
# [NEG]
# ---------------------------------------------------------------------------

def _mutated_doc(fid, label, drop):
    """Mở nguồn, xoá 1 paragraph trong cụm 4 paragraph header -> phải raise."""
    doc = Document(str(bfm.find_source(fid)))
    el = _find_label_element(doc, label)
    kids = list(doc.element.body.iterchildren())
    idx = kids.index(el)
    if drop == "label":
        doc.element.body.remove(el)
    else:
        doc.element.body.remove(kids[idx + drop])
    return doc


@check("[NEG] nguon lech dang (thieu paragraph) -> ValueError fail loud")
def t_negative():
    fid = "PLII_M02"
    label = bfm.HEADER_BAND_FORMS[fid]
    cases = {
        "mất ô TÊN HỘ KINH DOANH": ("label", None),
        "mất khối quốc hiệu": (1, "không tìm thấy"),
        "mất dòng Số:": (2, "lệch dạng chuẩn"),
        "mất dòng ngày tháng năm": (3, "lệch dạng chuẩn"),
    }
    for name, (drop, _expect) in cases.items():
        doc = _mutated_doc(fid, label, drop)
        try:
            bfm.build_header_band_table(doc, fid)
        except ValueError as exc:
            assert "[hdr2col]" in str(exc), "%s: message sai nguồn gốc: %s" % (name, exc)
            continue
        raise AssertionError("%s: phải raise ValueError khi %s" % (fid, name))


@check("[NEG] mau khong nam allowlist -> build_header_band_table tra None")
def t_negative_not_in_allowlist():
    # [integ(F0L) 2026-09-06] bỏ PLI_M12 khỏi pin âm — đã +vào allowlist
    # (current-law TT 121/2026 p50, band fillable).
    for fid in ("PLI_M01", "PLI_M72", "PLII_M01"):
        doc = Document(str(bfm.find_source(fid)))
        assert bfm.build_header_band_table(doc, fid) is None, \
            "%s: phải là no-op" % fid


# ---------------------------------------------------------------------------

def main() -> int:
    for _name, fn in sorted(globals().items()):
        if _name.startswith("t_") and callable(fn):
            fn()
    fails = [m for ok, m in _results if not ok]
    print("-" * 72)
    print("HEADER 2-BAND: %d PASS / %d FAIL" % (
        sum(1 for ok, _ in _results if ok), len(fails)))
    for m in fails:
        print(" - FAIL %s" % m)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
