# -*- coding: utf-8 -*-
"""test_phase6v_detectors.py — 6V-V1 (agent/6v-detectors): pin baseline ĐỎ
của D13/D14/D15/D16 + D9 nâng cấp trên corpus v0_corpuscheck, kèm negative
mutations (docx/pdf tự dựng nhỏ) cho từng detector.

==== Phương pháp ====

V1a (pin baseline — chống "chọn số đẹp"):
  Chạy 5 detector trên TOÀN BỘ corpus sẵn có
  generated_ho_so/_visual_layout/phase6v/v0_corpuscheck (455 record, đọc
  docx/pdf có sẵn — không export, không soffice) và so với số PIN dưới đây,
  số lấy từ tools/census/6v_v1_baseline.json @ branch 6v-detectors (corpus
  render post-V0 @313b0af; template giống hệt audit-HEAD 294604c). Corpus
  không có trên máy (gitignore, chưa export) → check SKIP, KHÔNG đếm vào
  PASS/FAIL — chạy tools.census.6v_v1_baseline để tái lập.

  Đối chiếu audit 2026-09-04 (PLAN 6V mục 1.2):
  - D9  60 bảng / 10 form — khớp ĐÚNG B5.
  - D15 17/17 form có chk — khớp B3 "mọi form có chk".
  - D13 77 form vs ~55: 55 form date-glue khớp đúng audit; +22 form do
    grammar rộng hơn (contact "0900Fax:"/"…vnWebsite:", "):CÔNG TY").
  - D16 82 form vs ~73: +9 form do grammar mảnh-wrap (NOI_T, G_TRU)
    ngoài ví dụ audit (_HIEN, _TAI_1).
  - D14 14 form vs ~37: corpus giống hệt audit-HEAD nhưng grammar audit
    rộng hơn (đếm cả slot nhận token kỹ thuật, slot phụ tiếng nước
    ngoài/viết tắt, slot ngoài trang 1) — bảng per_form trong
    tools/census/6v_v1_baseline.json.

V1b–V1f (negative mutations): mỗi detector có cặp positive/negative tự
dựng (docx zip tối thiểu + pdf pymupdf) — bug phải bắt, bản đúng phải bỏ.

V3 (F3T 2026-09-08): D18_row_placement — structural DOCX (BLANK_BEFORE_DATA
/ STT_ON_BLANK / STT_BREAK / ROW_COUNT_MISMATCH theo registry blocks
blankRows) + PDF_BLANK_GAP (chỉ đo khi có chuỗi STT). Mutation ĐỎ từng case
F3T.4: K-blank-then-data (K+N), blank giữa hai dòng data, STT trên hàng
trắng, STT đảo, lệch tổng hàng; hard-gate contract (gate_fails, FAIL).

Chạy:  python3 -X utf8 -m tools.test_phase6v_detectors
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

import tools.phase5_visual_gate as gate  # noqa: E402

CORPUS = ROOT / "generated_ho_so" / "_visual_layout" / "phase6v" \
    / "v0_corpuscheck"
MAIN_CHECKOUT = ROOT.parent.parent / "dangky_kinhdoanh"
TMP = Path("/tmp/6v_v1_detectors_test")

# ==== SỐ PIN (baseline @ 6v-detectors, corpus 455 record) ====
PIN = {
    "D13_skeleton_glue": {"records": 323, "hits": 1104, "forms": 77},
    "D14_name_slot": {"records": 14, "hits": 14, "forms": 14,
                      "forms_with_slot": 65},
    "D15_chk_glyph": {"records": 17, "hits": 191, "forms": 17,
                      "codes": {"BARE_X_PARAGRAPH": 130,
                                "X_OWN_LINE": 61}},
    # [6V-V2/Lead] grammar v2: bỏ FP dòng TOÀN gạch dưới (đường điền in sẵn
    # của bản giấy — finding review C4: 16/16 residual subset là lớp này).
    # Số cũ grammar v1: 355/8846 (TOKEN_FRAGMENT 5981) — giảm 13 rec/95 hit.
    "D16_token_values": {"records": 342, "hits": 8751, "forms": 82,
                         "codes": {"TOKEN_VALUE": 2865,
                                   "TOKEN_FRAGMENT": 5886}},
    "D9_table_grid": {"records": 50, "hits": 60, "forms": 10,
                      "codes": {"NARROW_COL_WIDE": 60}},
}

_RESULTS: list[tuple[str, bool, str]] = []
_SKIPPED: list[str] = []


def check(name):
    def deco(fn):
        def wrapped():
            try:
                fn()
            except AssertionError as exc:
                _RESULTS.append((name, False, str(exc)))
            except Exception as exc:  # noqa: BLE001
                _RESULTS.append((name, False, "%r" % (exc,)))
            else:
                _RESULTS.append((name, True, ""))
        wrapped.__name__ = fn.__name__
        return wrapped
    return deco


# ---------------------------------------------------------------------------
# Helpers — docx/pdf tự dựng cho mutations
# ---------------------------------------------------------------------------

def _min_docx(path: Path, body: str) -> Path:
    """DOCX tối thiểu: chỉ word/document.xml (detector chỉ regex XML)."""
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s'
           "<w:sectPr/></w:body></w:document>" % body)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", xml)
    return path


def _p(text: str) -> str:
    return "<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % text


def _pdf_pages(path: Path, lines: list[str]) -> list[dict]:
    """PDF 1 trang chứa `lines`; trả pages như gate dùng (pno + text)."""
    doc = pymupdf.open()
    page = doc.new_page()
    for i, ln in enumerate(lines):
        page.insert_text((50, 80 + 20 * i), ln)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    d2 = pymupdf.open(str(path))
    return [{"pno": p.number, "text": p.get_text("text")} for p in d2]


def _tbl(widths: list[int], borders: bool = False) -> str:
    grid = "".join('<w:gridCol w:w="%d"/>' % w for w in widths)
    b = ('<w:tblBorders><w:top w:val="single" w:sz="4"/>'
         "</w:tblBorders>") if borders else ""
    row = "<w:tr>%s</w:tr>" % "".join(
        "<w:tc><w:tcPr><w:tcW w:w=\"%d\" w:type=\"dxa\"/>%s</w:tcPr>"
        "<w:p><w:r><w:t>X</w:t></w:r></w:p></w:tc>" % (
            w, '<w:tcBorders><w:top w:val="single" w:sz="4"/>'
            "</w:tcBorders>" if borders else "")
        for w in widths)
    return "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>%s" \
        "</w:tblPr><w:tblGrid>%s</w:tblGrid>%s</w:tbl>" % (b, grid, row)


# ---------------------------------------------------------------------------
# V1a — pin baseline trên corpus
# ---------------------------------------------------------------------------

@check("V1a_pin_baseline_do_corpus")
def test_v1a_pin():
    corpus = CORPUS if (CORPUS / "manifest.json").exists() else None
    if corpus is None and (MAIN_CHECKOUT / CORPUS.relative_to(ROOT)
                           / "manifest.json").exists():
        corpus = MAIN_CHECKOUT / CORPUS.relative_to(ROOT)
    if corpus is None:
        _SKIPPED.append("V1a_pin_baseline_do_corpus (không có corpus "
                        "v0_corpuscheck — chạy export corpus hoặc "
                        "tools.census.6v_v1_baseline để tái lập)")
        return
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    records = json.loads((corpus / "manifest.json").read_text("utf-8"))[
        "records"]
    assert len(records) == 455, "corpus phải 455 record, có %d" % len(records)
    registry = gate.load_handwriting_slots()
    got = {k: {"records": 0, "hits": 0, "forms": set(), "codes": {}}
           for k in PIN}
    slot_forms = set()
    for rec in records:
        root = ROOT if (ROOT / rec["docx"]).exists() else MAIN_CHECKOUT
        docx, pdf = root / rec["docx"], root / rec["pdf"]
        d = pymupdf.open(str(pdf))
        pages = [{"pno": p.number, "text": p.get_text("text")} for p in d]

        for det, issues in (
                ("D13_skeleton_glue", gate.det_skeleton_glue(docx, pages)),
                ("D16_token_values", gate.det_token_values(pages)),
                ("D9_table_grid", gate.det_table_grid(docx))):
            if issues:
                got[det]["records"] += 1
                got[det]["hits"] += len(issues)
                got[det]["forms"].add(rec["form"])
                for it in issues:
                    c = it.get("code", "?")
                    got[det]["codes"][c] = got[det]["codes"].get(c, 0) + 1
        if rec["fixture"] == "valid-full":
            ns = gate.det_name_slot(pages, rec["form"], registry)
            if _has_slot(pages):
                slot_forms.add(rec["form"])
            if ns:
                got["D14_name_slot"]["records"] += 1
                got["D14_name_slot"]["hits"] += len(ns)
                got["D14_name_slot"]["forms"].add(rec["form"])
        if rec["fixture"] == "choice-variants":
            cg = gate.det_chk_glyph(docx, pages, maps[rec["form"]])
            if cg:
                got["D15_chk_glyph"]["records"] += 1
                got["D15_chk_glyph"]["hits"] += len(cg)
                got["D15_chk_glyph"]["forms"].add(rec["form"])
                for it in cg:
                    c = it["code"]
                    got["D15_chk_glyph"]["codes"][c] = \
                        got["D15_chk_glyph"]["codes"].get(c, 0) + 1
    for det, pin in PIN.items():
        g = got[det]
        assert g["records"] == pin["records"], \
            "%s records %d != pin %d" % (det, g["records"], pin["records"])
        assert g["hits"] == pin["hits"], \
            "%s hits %d != pin %d" % (det, g["hits"], pin["hits"])
        assert len(g["forms"]) == pin["forms"], \
            "%s forms %d != pin %d" % (det, len(g["forms"]), pin["forms"])
        for code, n in pin.get("codes", {}).items():
            assert g["codes"].get(code) == n, \
                "%s code %s: %r != pin %d" % (det, code,
                                              g["codes"].get(code), n)
    assert len(slot_forms) == PIN["D14_name_slot"]["forms_with_slot"], \
        "D14 forms có slot %d != pin %d" % (
            len(slot_forms), PIN["D14_name_slot"]["forms_with_slot"])


def _has_slot(pages: list[dict]) -> bool:
    for raw in pages[0]["text"].split("\n"):
        f = gate._fold(raw.strip())
        if not f:
            continue
        mi = gate._D14_INLINE.match(f)
        mp = gate._D14_PAREN.match(f)
        if (mi and not gate._D14_NOISE.search(f[:f.find(":")])) or \
                (mp and not gate._D14_NOISE.search(mp.group(1))):
            return True
    return False


# ---------------------------------------------------------------------------
# V1b — D13 mutations
# ---------------------------------------------------------------------------

@check("V1b_d13_mutations")
def test_v1b_d13():
    bad = _pdf_pages(TMP / "d13_bad.pdf", [
        "Hà Nội, ngày04tháng05năm2026",
        "Tôi là1 (ghi họ tên bằng chữ in hoa):CÔNG TY TEN",
        "Điện thoại: 0900000014Fax: 024",
        "Thư điện tử: a@b.vnWebsite: https://x.vn",
    ])
    hits = gate.det_skeleton_glue(TMP / "noop.docx", bad)
    codes = {h["code"] for h in hits}
    assert "DATE_NUM" in codes and "PAREN_VALUE" in codes \
        and "CONTACT_GLUE" in codes, "D13 phải bắt cả 3 lớp glue: %r" % hits
    good = _pdf_pages(TMP / "d13_good.pdf", [
        "Hà Nội, ngày 04 tháng 05 năm 2026",
        "Tôi là1 (ghi họ tên bằng chữ in hoa): CÔNG TY TEN",
        "Điện thoại: 0900000014 Fax: 024",
        "Thư điện tử: a@b.vn Website: https://x.vn",
    ])
    assert gate.det_skeleton_glue(TMP / "noop.docx", good) == [], \
        "D13 không được bắt bản đúng (có space separator)"
    # nguồn XML: glue bị PDF wrap che vẫn phải bắt (source=docx)
    docx = _min_docx(TMP / "d13_xml.docx",
                     _p("ngày04tháng") + _p("05"))
    pages = _pdf_pages(TMP / "d13_xml.pdf", ["ngày04", "tháng"])
    hits = gate.det_skeleton_glue(docx, pages)
    assert any(h.get("source") == "docx" and h["code"] == "DATE_NUM"
               for h in hits), "XML-only glue phải bắt với source=docx: %r" \
        % hits


# ---------------------------------------------------------------------------
# V1c — D14 mutations
# ---------------------------------------------------------------------------

@check("V1c_d14_mutations")
def test_v1c_d14():
    # LƯU Ý: PDF tự dựng bằng font pymupdf mặc định không render dấu tiếng
    # Việt (ộ → ·) — mutation viết không dấu; detector fold (bỏ dấu) nên
    # ngữ nghĩa giữ nguyên.
    # slot trống: dòng kế là label khác → RED
    bad = _pdf_pages(TMP / "d14_bad.pdf", [
        "THONG BAO", "(Ten ho kinh doanh)", "Tru so cua ho kinh doanh:"])
    assert gate.det_name_slot(bad, "TEST", {"forms": {}}), \
        "slot trống (dòng kế là label) phải RED"
    # slot nhận gạch/chấm → RED
    dots = _pdf_pages(TMP / "d14_dots.pdf", [
        "Ten ho kinh doanh (ghi bang chu in hoa): .............."])
    assert gate.det_name_slot(dots, "TEST", {"forms": {}}), \
        "slot chỉ có gạch/chấm phải RED"
    # slot bound cùng dòng → pass
    ok1 = _pdf_pages(TMP / "d14_ok1.pdf", [
        "Ten ho kinh doanh (ghi bang chu in hoa): CONG TY TNHH ABC"])
    assert gate.det_name_slot(ok1, "TEST", {"forms": {}}) == [], \
        "slot bound cùng dòng phải pass"
    # slot bound dòng kế (title-block) → pass
    ok2 = _pdf_pages(TMP / "d14_ok2.pdf", [
        "GIAY DE NGHI", "(Ten doanh nghiep)", "CONG TY TNHH ABC"])
    assert gate.det_name_slot(ok2, "TEST", {"forms": {}}) == [], \
        "slot bound ở dòng kế phải pass"
    # mention trong câu (có từ nối) không phải slot → pass
    noise = _pdf_pages(TMP / "d14_noise.pdf", [
        "ve viec thay doi cua (ten ho kinh doanh) nhu sau:"])
    assert gate.det_name_slot(noise, "TEST", {"forms": {}}) == [], \
        "mention trong câu không phải slot"
    # form trong registry handwriting → miễn
    reg = _pdf_pages(TMP / "d14_reg.pdf", [
        "(Ten ho kinh doanh)", "Tru so cua ho kinh doanh:"])
    assert gate.det_name_slot(reg, "TEST", {"forms": {"TEST": {
        "reason": "ban giay dien tay"}}}) == [], \
        "form trong registry handwriting phải được miễn"


# ---------------------------------------------------------------------------
# V1d — D15 mutations
# ---------------------------------------------------------------------------

_CHK_META = {"fields": [{"key": "chk_a", "type": "chk"}]}
_NOCHK_META = {"fields": [{"key": "ten", "type": "text"}]}


@check("V1d_d15_mutations")
def test_v1d_d15():
    pages = [{"pno": 0, "text": "x"}]
    # X trần trong paragraph thường → RED
    d1 = _min_docx(TMP / "d15_bare.docx", _p("X Phương pháp kê khai"))
    hits = gate.det_chk_glyph(d1, pages, _CHK_META)
    assert [h["code"] for h in hits] == ["BARE_X_PARAGRAPH"], hits
    # glue cuối dòng "Thành lập mớiX" → RED
    d2 = _min_docx(TMP / "d15_glued.docx", _p("Thành lập mớiX"))
    assert gate.det_chk_glyph(d2, pages, _CHK_META), "glued-end X phải RED"
    # câu hướng dẫn (X giữa câu) → KHÔNG bắt
    d3 = _min_docx(TMP / "d15_instr.docx",
                   _p("1. Tình trạng (đánh dấu X vào ô thích hợp):"))
    assert gate.det_chk_glyph(d3, pages, _CHK_META) == [], \
        "câu hướng dẫn không phải tick"
    # glyph ☒ → hợp pháp
    d4 = _min_docx(TMP / "d15_glyph.docx", _p("☒ Phương pháp kê khai"))
    assert gate.det_chk_glyph(d4, pages, _CHK_META) == [], \
        "tick glyph ☒ phải hợp pháp"
    # X trong cell CÓ viền → hợp pháp (FP guard)
    d5 = _min_docx(TMP / "d15_cell.docx", _tbl([900, 3000], borders=True))
    assert gate.det_chk_glyph(d5, pages, _CHK_META) == [], \
        "X trong cell có viền phải hợp pháp"
    # X trong cell KHÔNG viền → RED (bảng dựng 2 cell X → 2 hit cùng mã)
    d6 = _min_docx(TMP / "d15_cell0.docx", _tbl([900, 3000], borders=False))
    hits = gate.det_chk_glyph(d6, pages, _CHK_META)
    assert len(hits) == 2 and {h["code"] for h in hits} == \
        {"BARE_X_BORDERLESS_CELL"}, hits
    # [6V-V2/C3, Q-V1] X trong RUN có w:bdr (ô vuông vẽ viền) → hợp pháp
    bordered = ('<w:p><w:r><w:rPr><w:rFonts w:ascii="Arial"/>'
                '<w:bdr w:val="single" w:sz="8" w:space="1" w:color="auto"/>'
                "</w:rPr><w:t>X</w:t></w:r>"
                "<w:r><w:t> Phương pháp kê khai</w:t></w:r></w:p>")
    d8 = _min_docx(TMP / "d15_bordered.docx", bordered)
    assert gate.det_chk_glyph(d8, pages, _CHK_META) == [], \
        "X trong run viền (w:bdr) phải hợp pháp (hình thức C3)"
    # [6V-V2/C3] ô trống (run viền quanh nbsp) cạnh X TRẦN vẫn phải RED —
    # legality tính theo run chứa tick, không theo paragraph
    mixed = ('<w:p><w:r><w:rPr><w:bdr w:val="single" w:sz="8" w:space="1" '
             'w:color="auto"/></w:rPr>'
             '<w:t xml:space="preserve">\u00a0</w:t></w:r>'
             "<w:r><w:t>Nhãn</w:t></w:r>"
             "<w:r><w:t>X</w:t></w:r></w:p>")
    d9 = _min_docx(TMP / "d15_mixed.docx", mixed)
    hits = gate.det_chk_glyph(d9, pages, _CHK_META)
    assert hits and hits[0]["code"] == "BARE_X_PARAGRAPH", \
        "X trần cạnh ô vuông trống vẫn phải bắt: %r" % hits
    # form không có chk field → không chạy
    assert gate.det_chk_glyph(d1, pages, _NOCHK_META) == []
    # PDF: X rơi dòng riêng
    pp = _pdf_pages(TMP / "d15_own.pdf", ["Tình trạng:", "X"])
    d7 = _min_docx(TMP / "d15_own.docx", _p("Tình trạng: X"))
    hits = gate.det_chk_glyph(d7, pp, _CHK_META)
    assert any(h["code"] == "X_OWN_LINE" for h in hits), hits
    # [F-V5-2] mọi X hợp pháp ở XML (cell có viền) + PDF wrap tách X riêng
    # một dòng → KHÔNG được bắn X_OWN_LINE (artifact ô viền, không phải lỗi)
    pp2 = _pdf_pages(TMP / "d15_own_legal.pdf", ["Công ty dài tên lắm", "X"])
    assert gate.det_chk_glyph(d5, pp2, _CHK_META) == [], \
        "X trong cell viền bị PDF wrap dòng riêng phải được miễn (F-V5-2)"
    # [F-V5-2 mutation] X trần thật (XML RED) + PDF dòng riêng → vẫn bắt đủ
    # cả hai lớp: mutation phải chứng minh miễn trừ không che lỗi thật.
    hits = gate.det_chk_glyph(d7, pp2, _CHK_META)
    codes = {h["code"] for h in hits}
    assert "BARE_X_PARAGRAPH" in codes and "X_OWN_LINE" in codes, hits


# ---------------------------------------------------------------------------
# V1e — D16 mutations
# ---------------------------------------------------------------------------

@check("V1e_d16_mutations")
def test_v1e_d16():
    bad = _pdf_pages(TMP / "d16_bad.pdf", [
        "Nơi ở hiện tại: NOI_O_HIEN_TAI_123",
        "_TAI_1",
        "NOI_T",
    ])
    hits = gate.det_token_values(bad)
    codes = [h["code"] for h in hits]
    assert "TOKEN_VALUE" in codes and "TOKEN_FRAGMENT" in codes, hits
    vals = {h["value"] for h in hits}
    assert "NOI_O_HIEN_TAI_123" in vals and "_TAI_1" in vals \
        and "NOI_T" in vals, vals
    good = _pdf_pages(TMP / "d16_good.pdf", [
        "Nơi ở hiện tại: Số 25 Nguyễn Huệ, phường Bến Nghé",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "Số: 00001/2026",
        "Giấy đề nghị đăng ký doanh nghiệp",
        "___________________",            # [6V-V2/Lead] đường điền bản giấy
        "_______________________",
    ])
    assert gate.det_token_values(good) == [], \
        "text tiếng Việt thường/đường điền toàn gạch không được bắt"


# ---------------------------------------------------------------------------
# V1f — D9 mutations (policy 2 tầng)
# ---------------------------------------------------------------------------

@check("V1f_d9_two_tier_mutations")
def test_v1f_d9():
    wide = _min_docx(TMP / "d9_wide.docx",
                     _tbl([566] + [897] * 9))          # 10 cột, min 566
    hits = gate.det_table_grid(wide)
    assert [h["code"] for h in hits] == ["NARROW_COL_WIDE"], \
        "bảng 10 cột min 566 <900 phải NARROW_COL_WIDE: %r" % hits
    ok_wide = _min_docx(TMP / "d9_okwide.docx",
                        _tbl([900] + [900] * 9))       # 10 cột, min = 900
    assert gate.det_table_grid(ok_wide) == [], \
        "bảng 10 cột min 900 twips phải pass"
    legacy = _min_docx(TMP / "d9_legacy.docx",
                       _tbl([560] + [2000] * 7))       # 8 cột, min 560
    hits = gate.det_table_grid(legacy)
    assert [h["code"] for h in hits] == ["NARROW_COL"], \
        "bảng 8 cột min 560 <566 phải NARROW_COL (legacy): %r" % hits
    i4 = _min_docx(TMP / "d9_i4.docx",
                   _tbl([566] + [2000] * 7))           # 8 cột, min đúng 566
    assert gate.det_table_grid(i4) == [], \
        "I4: bảng 8 cột min đúng 566 phải pass (sàn làm tròn xuống)"


# ---------------------------------------------------------------------------
# V1g — hợp đồng verdict: detector mới chỉ PHÁT VÀO gate_candidates
# (PLAN 6V V1: "chưa hard-fail, Lead quyết nâng hard sau V2")
# ---------------------------------------------------------------------------

@check("V1g_new_detectors_are_candidates_only")
def test_v1g_verdict_contract():
    rec = {"form": "TEST", "fixture": "valid-full", "tag": "main",
           "detectors": {
               "D13_skeleton_glue": [{"code": "DATE_NUM"}],
               "D14_name_slot": [{"kind": "paren"}],
               "D15_chk_glyph": [{"code": "BARE_X_PARAGRAPH"}],
               "D16_token_values": [{"code": "TOKEN_VALUE"}],
               "D9_table_grid": [{"code": "NARROW_COL_WIDE"}],
               # hard-fail cũ phải giữ nguyên hành vi
               "D1_source_indicator": ["QUỐC HIỆU"],
           }}
    gate.record_verdicts([rec], {})
    fails = {f["detector"] for f in rec["gate_fails"]}
    cands = {c["detector"] for c in rec["gate_candidates"]}
    assert fails == {"D1_source_indicator"}, \
        "chỉ D1 được hard-fail, có %r" % fails
    for det in ("D13_skeleton_glue", "D14_name_slot", "D15_chk_glyph",
                "D16_token_values", "D9_table_grid"):
        assert det in cands, "%s phải nằm gate_candidates" % det
        assert det not in fails, "%s KHÔNG được hard-fail ở V1" % det
    assert rec["gate_verdict"] == "FAIL"  # do D1, không phải detector mới


# ---------------------------------------------------------------------------
# V2 — [WAVE v7] SIGNATURE-USABILITY-SPACE: mutation bắt buộc cho D6/D8
# (sàn 72pt, grammar census, page-edge, "Đã ký", SIG_MISSING, split,
# orientation). Mutation PHẢI đỏ trước fix và giữ bất biến sau fix.
# ---------------------------------------------------------------------------

def _sig_word(blk: int, ln: int, x0: float, y0: float, text: str,
              y1: float | None = None):
    w = 6.0 * len(text) + 2
    return (x0, y0, x0 + w, y1 if y1 is not None else y0 + 12, text,
            blk, ln, 0)


def _sig_page(pno: int, lines: list[tuple[int, float, str]],
              page_bottom: float = 842.0) -> dict:
    """lines: [(block, y0, text)] — mỗi phần tử một dòng logic riêng."""
    words: list[tuple] = []
    for blk, y0, text in lines:
        words.append(_sig_word(blk, blk, 100.0, y0, text, y1=y0 + 12))
    return {"pno": pno, "words": words, "page_bottom": page_bottom}


_CLUSTER = [(1, 700.0, "NGƯỜI LẬP BIỂU"), (2, 720.0, "(Ký và ghi họ tên)")]


def _sig_expect(orientation=None, signers=1, gap=72):
    # registry phải key theo FORM ID (det_signatures expectations.get(fid))
    sig = {"signers": signers, "keep_together": True,
           "min_write_gap_pt": gap}
    if orientation:
        sig["orientation"] = orientation
    return {"TEST": {"signature": sig}}


@check("V2a_d8_write_space_mutations")
def test_v2a_d8():
    # gap 71pt < 72 → HARD FAIL
    p = _sig_page(0, _CLUSTER + [(9, 803.0, "Ghi chú thêm mời người xem")])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    ws = [f for f in res["fails"] if f["code"] == "SIG_WRITE_SPACE"]
    assert ws and abs(ws[0]["gap_pt"] - 71.0) < 0.5, res["fails"]

    # gap 72pt → PASS
    p = _sig_page(0, _CLUSTER + [(9, 804.5, "Ghi chú thêm mời người xem")])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert not [f for f in res["fails"]
                if f["code"] == "SIG_WRITE_SPACE"], res["fails"]

    # cụm cuối trang: KHÔNG có dòng dưới vẫn phải đo — tới mép trang
    # (mutation: mép 802 → gap 70 FAIL; mép 807 → gap 75 PASS; instr y1=732)
    p = _sig_page(0, _CLUSTER, page_bottom=802.0)
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    ws = [f for f in res["fails"] if f["code"] == "SIG_WRITE_SPACE"]
    assert ws and abs(ws[0]["gap_pt"] - 70.0) < 0.5, \
        "instruction cuối trang phải được đo đến page edge: %r" % res["fails"]
    p = _sig_page(0, _CLUSTER, page_bottom=807.0)
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert not [f for f in res["fails"]
                if f["code"] == "SIG_WRITE_SPACE"], res["fails"]

    # "Đã ký" KHÔNG bị ép vùng viết tay (owner v7) — gap 30 vẫn PASS
    daky = [(1, 700.0, "CHỦ SỞ HỮU CŨ"), (2, 720.0, "(Đã ký)"),
            (9, 762.0, "Ghi chú kế tiếp")]
    p = _sig_page(0, daky)
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert not [f for f in res["fails"]
                if f["code"] == "SIG_WRITE_SPACE"], res["fails"]

    # registry pin CAO hơn sàn (80pt) phải được tôn trọng: gap 75 → FAIL
    p = _sig_page(0, _CLUSTER + [(9, 797.0, "Ghi chú thêm mời người xem")])
    res = gate.det_signatures([p], _sig_expect(gap=80), "TEST")
    assert [f for f in res["fails"] if f["code"] == "SIG_WRITE_SPACE"], \
        res["fails"]


@check("V2b_d6_grammar_coverage_split_orientation_mutations")
def test_v2b_d6():
    # 1) "ký, ghi họ tên và đóng dấu" (có ngoặc) phải được nhận diện + đo
    p = _sig_page(0, [(1, 700.0, "TRƯỞNG PHÒNG"),
                      (2, 720.0, "(Ký, ghi họ tên và đóng dấu)"),
                      (9, 745.0, "Ghi chú kế dưới")])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert len(res["clusters"]) == 1, res["clusters"]
    assert [f for f in res["fails"] if f["code"] == "SIG_WRITE_SPACE"], \
        "cụm đóng dấu gap 25pt phải FAIL: %r" % res["fails"]

    # 2) "Ký và ghi họ tên từng thành viên" KHÔNG ngoặc phải được nhận diện
    p = _sig_page(0, [(1, 700.0, "CÁC THÀNH VIÊN"),
                      (2, 720.0, "Ký và ghi họ tên từng thành viên"),
                      (9, 740.0, "Ghi chú kế dưới")])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert len(res["clusters"]) == 1 and \
        [f for f in res["fails"] if f["code"] == "SIG_WRITE_SPACE"], res

    # 3) chỉ thị dòng riêng "Ký, ghi họ tên và đóng dấu" (không ngoặc) của
    #    giấy chứng nhận cũng phải được nhận
    p = _sig_page(0, [(1, 700.0, "GIẤY CHỨNG NHẬN"),
                      (2, 720.0, "Ký, ghi họ tên và đóng dấu"),
                      (9, 790.0, "Nơi nhận")])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert len(res["clusters"]) == 1, res["clusters"]

    # 4) expected signature nhưng zero detected → SIG_MISSING hard fail
    p = _sig_page(0, [])
    res = gate.det_signatures([p], _sig_expect(), "TEST")
    assert any(f["code"] == "SIG_MISSING" for f in res["fails"]), res["fails"]
    # form không pin registry: không fail (không đòi cụm ở nơi không có)
    res = gate.det_signatures([p], {}, "TEST")
    assert not res["fails"], res["fails"]

    # 5) tách title/instruction qua trang: instruction đầu trang 2 không có
    #    title cùng trang → SIG_SPLIT
    p1 = _sig_page(0, [(1, 300.0, "TRANG NỘI DUNG DÀI")])
    p2 = _sig_page(1, [(2, 40.0, "(Ký và ghi họ tên)")])
    res = gate.det_signatures([p1, p2], _sig_expect(), "TEST")
    assert any(f["code"] == "SIG_SPLIT" for f in res["fails"]), res["fails"]

    # 6) sai orientation: registry horizontal, cụm xếp dọc → SIG_ORIENTATION
    p = _sig_page(0, [(1, 700.0, "NGƯỜI NỘP"),
                      (2, 720.0, "(Ký và ghi họ tên)"),
                      (3, 800.0, "NGƯỜI NHẬN"),
                      (4, 820.0, "(Ký và ghi họ tên)"),
                      (9, 855.0, "Ghi chú dưới")], page_bottom=900.0)
    res = gate.det_signatures([p], _sig_expect(orientation="horizontal",
                                               signers=2), "TEST")
    assert any(f["code"] == "SIG_ORIENTATION" for f in res["fails"]), \
        res["fails"]


@check("V2c_d17_header_name_sync_mutations")
def test_v2c_d17():
    reg = {"forms": {"PLI_M32": {"key": "dn.ten_tieng_viet",
                                 "label": "TÊN DOANH NGHIỆP"}}}
    val = "CONG TY TNHH A BỘ ĐỘI"
    # 1) band còn dòng kẻ '-------' → HDR_NAME_UNBOUND
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"),
                      (2, 720.0, "-------")])
    hits = gate.det_header_name([p], "PLI_M32", reg, val + "\n" + val)
    assert [h["code"] for h in hits] == ["HDR_NAME_UNBOUND"], hits

    # 2) band bound + giá trị khớp thân (xuất hiện 2 lần: band + thân) → PASS
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"),
                      (2, 720.0, val)])
    hits = gate.det_header_name([p], "PLI_M32", reg, val + "\n" + val)
    assert hits == [], hits

    # 3) band có giá trị KHÁC thân (chỉ thấy 1 lần — bind nhầm key) → SYNC
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"),
                      (2, 720.0, "TEN SAI GIA TRI")])
    hits = gate.det_header_name([p], "PLI_M32", reg, val + "\n" + val)
    assert [h["code"] for h in hits] == ["HDR_NAME_SYNC"], hits

    # 4) band giá trị trống (token render rỗng trên valid-full là lỗi) → SYNC
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"),
                      (2, 720.0, "Số: 000001")])
    hits = gate.det_header_name([p], "PLI_M32", reg, val)
    assert hits and hits[0]["code"] in ("HDR_NAME_SYNC",
                                        "HDR_NAME_LABEL_MISSING"), hits

    # 5) form không nằm registry → detector bỏ qua
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"), (2, 720.0, "-------")])
    assert gate.det_header_name([p], "PLI_M33", reg, "") == []

    # 6) D17 là HARD gate: record_verdicts phải đẩy vào gate_fails
    rec = {"form": "PLI_M32", "fixture": "valid-full", "tag": "main",
           "detectors": {"D17_header_name": [{"code": "HDR_NAME_UNBOUND"}]}}
    gate.record_verdicts([rec], {})
    assert any(f["detector"] == "D17_header_name"
               for f in rec["gate_fails"]), rec["gate_fails"]
    assert rec["gate_verdict"] == "FAIL"


@check("V2c_d17_band_input_mutations")
def test_v2c_d17_band_input():
    # [F3B 2026-09-07] mode=band_input (N-v1/N-v2 DECIDED A — PLI_M33,
    # PLII_M06): band là ô nhập pháp định DUY NHẤT, thân KHÔNG có trường
    # tên → giá trị band xuất hiện ĐÚNG 1 LẦN là ĐÚNG; >=2 (double-slot
    # quay lại) phải FAIL HDR_NAME_SYNC.
    reg = {"forms": {"PLII_M06": {"key": "hkd_ten_tieng_viet_2",
                                  "label": "TÊN HỘ KINH DOANH",
                                  "mode": "band_input"}}}
    val = "HO KINH DOANH AN CAO"
    # 1) chỉ band có tên (count == 1) → PASS
    p = _sig_page(0, [(1, 700.0, "TÊN HỘ KINH DOANH"),
                      (2, 720.0, val)])
    assert gate.det_header_name([p], "PLII_M06", reg, val) == []
    # 2) double-slot: tên quay lại ở thân (count == 2) → HDR_NAME_SYNC
    p = _sig_page(0, [(1, 700.0, "TÊN HỘ KINH DOANH"),
                      (2, 720.0, val)])
    hits = gate.det_header_name([p], "PLII_M06", reg, val + "\n" + val)
    assert [h["code"] for h in hits] == ["HDR_NAME_SYNC"], hits
    # 3) mode mặc định (mirror) vẫn giữ hợp đồng >=2: count == 1 → SYNC
    reg_mirror = {"forms": {"PLI_M32": {"key": "dn.ten_tieng_viet",
                                        "label": "TÊN DOANH NGHIỆP"}}}
    p = _sig_page(0, [(1, 700.0, "TÊN DOANH NGHIỆP"),
                      (2, 720.0, val)])
    hits = gate.det_header_name([p], "PLI_M32", reg_mirror, val)
    assert [h["code"] for h in hits] == ["HDR_NAME_SYNC"], hits


# ---------------------------------------------------------------------------
# V3 — [F3T] D18_row_placement: structural DOCX + PDF + hard-gate verdict.
# Mutation ĐỎ cho từng case F3T.4: K-blank-then-data (K+N), blank giữa hai
# dòng dữ liệu, STT trên hàng trắng, STT đảo thứ tự, lệch tổng hàng max(K,N),
# và bản đúng (K=4,N=2)/(K=4,N=0)/(K=0,N=3) phải PASS. Đăng ký gate: HARD.
# ---------------------------------------------------------------------------

def _loop_tbl(rows_cells: list[list[str]]) -> str:
    """Bảng w:tbl tối thiểu 3 cột từ list hàng (list ô text)."""
    body = "".join(
        "<w:tr>%s</w:tr>" % "".join(
            "<w:tc><w:p><w:r><w:t>%s</w:t></w:r></w:p></w:tc>" % c
            for c in cells)
        for cells in rows_cells)
    return ("<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr>"
            '<w:tblGrid><w:gridCol w:w="600"/><w:gridCol w:w="3000"/>'
            '<w:gridCol w:w="2000"/></w:tblGrid>' + body + "</w:tbl>")


_HDR = ["STT", "Tên ngành", "Mã ngành"]
# registry như blocks sinh ra: loop ds_x K=4, header 1 hàng,
# signature = header row0 đã fold_squeeze
from tools.row_placement import (  # noqa: E402
    det_row_placement, det_row_placement_pdf, fold_squeeze,
)

_D18_REG = [{"loop": "ds_x", "k": 4, "header_rows": 1,
             "sig": fold_squeeze(" ".join(_HDR))}]


def _d18(rows_cells):
    p = _min_docx(TMP / "d18_case.docx", _loop_tbl(rows_cells))
    return det_row_placement(p, _D18_REG)


@check("V3a_d18_row_placement_structural_mutations")
def test_v3a_d18_structural():
    # bản ĐÚNG (K=4, N=2): header + 2 data + 2 trắng → PASS
    hits = _d18([_HDR, ["1", "Trồng lúa", "0111"], ["2", "Chăn nuôi", "0141"],
                 ["", "", ""], ["", "", ""]])
    assert hits == [], "bản đúng (4,2) không được bắn: %r" % hits
    # bản ĐÚNG (K=4, N=6 ≥ K): đúng 6 hàng data, KHÔNG append trắng → PASS
    hits = _d18([_HDR] + [[str(i + 1), "Ngành %d" % (i + 1), "%04d" % (i + 1)]
                          for i in range(6)])
    assert hits == [], "bản đúng (4,6) không được bắn: %r" % hits
    # bản ĐÚNG (K=4, N=0): header + 4 trắng (giữ sức chứa in tay) → PASS
    hits = _d18([_HDR, ["", "", ""], ["", "", ""], ["", "", ""], ["", "", ""]])
    assert hits == [], "N=0 giữ K trắng không được bắn: %r" % hits
    # MUTATION ĐỎ: K-blank-then-data (K+N) — defect F3T.1 tái hiện
    hits = _d18([_HDR, ["", "", ""], ["", "", ""], ["", "", ""], ["", "", ""],
                 ["1", "Trồng lúa", "0111"]])
    codes = {h["code"] for h in hits}
    assert {"BLANK_BEFORE_DATA", "ROW_COUNT_MISMATCH"} <= codes, hits
    # MUTATION ĐỎ: blank chen giữa hai dòng dữ liệu
    hits = _d18([_HDR, ["1", "Trồng lúa", "0111"], ["", "", ""],
                 ["2", "Chăn nuôi", "0141"], ["", "", ""]])
    assert "BLANK_BEFORE_DATA" in {h["code"] for h in hits}, hits
    # MUTATION ĐỎ: đánh STT cho hàng trắng (đuôi)
    hits = _d18([_HDR, ["1", "Trồng lúa", "0111"], ["2", "", ""],
                 ["3", "", ""]])
    assert "STT_ON_BLANK" in {h["code"] for h in hits}, hits
    # MUTATION ĐỎ: STT đảo thứ tự (mutation "đảo thứ tự" F3T.4)
    hits = _d18([_HDR, ["2", "Chăn nuôi", "0141"], ["1", "Trồng lúa", "0111"],
                 ["", "", ""], ["", "", ""]])
    assert "STT_BREAK" in {h["code"] for h in hits}, hits
    # MUTATION ĐỎ: mất một hàng trắng (tổng 4 != 1 + max(4,1)) — thiếu K−N
    hits = _d18([_HDR, ["1", "Trồng lúa", "0111"], ["", "", ""],
                 ["", "", ""]])
    assert "ROW_COUNT_MISMATCH" in {h["code"] for h in hits}, hits
    # K=0 (loop không có blankRows): N=3 data thuần → PASS
    reg0 = [{"loop": "ds_y", "k": 0, "header_rows": 1,
             "sig": _D18_REG[0]["sig"]}]
    p = _min_docx(TMP / "d18_k0.docx", _loop_tbl(
        [_HDR, ["1", "A", "1"], ["2", "B", "2"], ["3", "C", "3"]]))
    assert det_row_placement(p, reg0) == [], "K=0/N=3 phải PASS"


@check("V3b_d18_row_placement_pdf_gap_mutations")
def test_v3b_d18_pdf():
    # PDF mutation dựng trực tiếp words (băng trống không thể dựng bằng text
    # pymupdf). w(x0, y0, txt) -> word tuple như pdf_pages trả.
    def _page(words):
        return [{"pno": 0, "text": "", "words": words}]

    def w(x0, y0, txt):
        return (x0, y0, x0 + 6.0 * len(txt), y0 + 10.0, txt, 0, 0, 0)

    # MUTATION ĐỎ: header rồi băng trống ~70pt (≈4 hàng trắng) trước dòng STT=1
    bad = _page([w(50, 700, "STT"), w(80, 700, "Tên"), w(160, 700, "Mã"),
                 w(50, 780, "1"), w(80, 780, "0111"), w(160, 780, "Trồng"),
                 w(50, 796, "2"), w(80, 796, "0141"), w(160, 796, "Chăn")])
    hits = det_row_placement_pdf(bad)
    assert len(hits) == 1 and hits[0]["code"] == "PDF_BLANK_GAP", hits
    assert hits[0]["gap_pt"] > 40, hits
    # bản ĐÚNG: dòng 1 nằm ngay dưới header (~18pt pitch) → PASS
    good = _page([w(50, 700, "STT"), w(80, 700, "Tên"), w(160, 700, "Mã"),
                  w(50, 718, "1"), w(80, 718, "0111"), w(160, 718, "Trồng"),
                  w(50, 736, "2"), w(80, 736, "0141"), w(160, 736, "Chăn")])
    assert det_row_placement_pdf(good) == [], \
        "gap thường không được bắn (F-V3b)"
    # N=0 (không có chuỗi STT) không được bắn — K trắng hợp pháp
    noblank = _page([w(50, 700, "STT"), w(80, 700, "Tên")])
    assert det_row_placement_pdf(noblank) == []


@check("V3c_d18_row_placement_is_hard_gate")
def test_v3c_d18_hard():
    # fail-loud contract: D18 phải nằm HARD_FAIL_KEYS — hit → gate_fails,
    # verdict FAIL (không phải candidate).
    assert "D18_row_placement" in gate.HARD_FAIL_KEYS
    rec = {"form": "PLI_M72", "fixture": "valid-full", "tag": "main",
           "detectors": {"D18_row_placement": [
               {"table": 2, "code": "BLANK_BEFORE_DATA",
                "blank_rows": [2, 3, 4, 5], "first_data_row": 6}]}}
    gate.record_verdicts([rec], {})
    assert rec["gate_verdict"] == "FAIL"
    assert any(f["detector"] == "D18_row_placement"
               for f in rec["gate_fails"]), rec["gate_fails"]
    assert not any(c["detector"] == "D18_row_placement"
                   for c in rec["gate_candidates"])




def main() -> int:
    test_v1a_pin()
    test_v1b_d13()
    test_v1c_d14()
    test_v1d_d15()
    test_v1e_d16()
    test_v1f_d9()
    test_v1g_verdict_contract()
    test_v2a_d8()
    test_v2b_d6()
    test_v2c_d17()
    test_v2c_d17_band_input()
    test_v3a_d18_structural()
    test_v3b_d18_pdf()
    test_v3c_d18_hard()
    passed = [r for r in _RESULTS if r[1]]
    failed = [r for r in _RESULTS if not r[1]]
    for name, ok, msg in _RESULTS:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                           (" — %s" % msg) if msg else ""))
    for s in _SKIPPED:
        print("SKIP", s)
    print("-" * 60)
    print("Tổng kết: %d PASS / %d FAIL / %d SKIP" % (
        len(passed), len(failed), len(_SKIPPED)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

