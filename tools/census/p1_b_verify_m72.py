# -*- coding: utf-8 -*-
"""P1-B verify PLI_M72 (ban 2 — sau P1.2 Option D): bang chung may tinh cho
5 occurrence luoi nganh + cau truc DOCX that cua ban sao production.

Hai mat bang chung:

A. SPEC + FILE NGUON (giu nguyen tu ban 1):
   1. Spec tools/form_specs/change/PLI_M72.json: 5 occurrence
      (id/nth/match_heading/sync_group/end_markers) + pos/no_default_drops/
      drop_until/headers + section_cond 5 option (value_key, value/flag/
      occurrence_id khop 1-1 voi occurrences theo thu tu).
   2. Nguon generator 05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_*.docx:
      5 vung anchor->end marker, tan du tieu de cot, KHONG w:tbl top-level;
      regions dict khoa (13,22),(42,52),(85,95),(134,141),(168,175).

B. TEMPLATE app/templates/PLI_M72.docx — cau truc that sau P1.2:
   analyze_document_xml(xml) -> issues[] voi ma loi ro rang:
   - MISSING_HEADING / HEADING_NOT_ADJACENT : dung 5 heading
     '5. Ngành, nghề kinh doanh' dung thu tu, moi heading dung ngay truoc
     bang cua no;
   - TABLE_COUNT_MISMATCH : dung 9 w:tbl top-level (5 nganh + 4 thanh vien/
      co dong — [P2 pin sync 2026-09-03]);
   - WRONG_LOOP_ORDER : bang thu k chua dung cap {#EXPECTED_IDS[k]}...{/...};
   - LOOP_TAG_CROSS_CONTAMINATION : khong loop tag cua bien the khac lot vao;
   - HEADER_MISSING_COL : header 4 o fold-match
     stt | ten nganh | ma nganh | nganh, nghe kinh doanh chinh;
   - TABLE_ROW_MISSING_STT / TABLE_ROW_MISSING_COL : hang khuon co {_stt} +
     du 3 tag cot ten_nganh/ma_nganh/la_nganh_chinh;
   - COND_SEQUENCE_BROKEN : chuoi 16 marker dieu kien trong body khop CHINH
     XAC sequence (5 cap section chinh + 3 cap footnote), stack can bang;
   - COND_SECTION_MISMATCH : moi vung [open,close) chinh chua dung 1 w:tbl
     loop DUNG bien the theo section_cond; vung footnote khong chua bang;
   - COND_MARKER_NOT_BEFORE_ANCHOR : marker mo dung ngay truoc anchor
     '(TÊN ...)' tuong ung; marker dong dung truoc marker mo ke / dong ke
     ket thuc chung; footnote dung truoc dong 'Ghi ten...';
   - COND_MARKER_IN_TABLE : khong marker nao nam trong w:tbl.

Nhom NEGATIVE bat buoc: mutate ban copy XML trong bo nho roi assert
analyze() bat dung ma — (a) xoa text o header; (b) hoan doi loop 2 bang;
(c) hoan doi 2 flag section; (d) bo 1 cap marker; (e) nhan doi 1 marker mo;
(f) chen marker vao trong cell bang.

Exit code 0 = moi check PASS, 1 = co FAIL. Khong ghi file.

Chay:  python -X utf8 -m tools.census.p1_b_verify_m72
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document                    # noqa: E402
from docx.oxml.ns import qn                  # noqa: E402
from docx.text.paragraph import Paragraph    # noqa: E402

SPEC_PATH = ROOT / "tools" / "form_specs" / "change" / "PLI_M72.json"
SOURCE_GLOB = "05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_*.docx"
TEMPLATE_PATH = ROOT / "app" / "templates" / "PLI_M72.docx"

EXPECTED_IDS = ["ds_nganh_dntn", "ds_nganh_tnhh_1tv", "ds_nganh_tnhh_2tv",
                "ds_nganh_ctcp", "ds_nganh_dhdn"]

# [P2 pin sync 2026-09-03] P2 rebuild 4 luoi thanh vien/co dong (nested-grid)
# trong template M72: 9 w:tbl top-level = 5 bang nganh + 4 luoi thanh vien,
# moi luoi nam trong vung section_cond cua dung bien the.
EXPECTED_TABLE_LOOPS = [
    "ds_nganh_dntn", "ds_nganh_tnhh_1tv", "ds_nganh_tnhh_2tv",
    "ds_thanh_vien_tnhh_2tv",
    "ds_nganh_ctcp", "ds_co_dong_sang_lap_ctcp", "ds_co_dong_nuoc_ngoai_ctcp",
    "ds_nganh_dhdn", "ds_thanh_vien_hop_danh_dhdn",
]
# cac bang nganh (giu checklist heading-adjacent + header 4 o cua P1.2)
INDUSTRY_TABLE_INDEXES = [0, 1, 2, 4, 7]
# header (da fold) cua 4 luoi thanh vien — pin chinh xac tung o
MEMBER_HEADERS_FOLD = {
    "ds_thanh_vien_tnhh_2tv": [
        "stt", "ten thanh vien", "quoc tich",
        "so giay to phap ly cua ca nhan/to chuc",
        "dia chi lien lac doi voi ca nhan; dia chi tru so chinh doi voi to chuc",
        "phan von gop (vnd va gia tri tuong duong theo don vi tien nuoc ngoai, neu co)",
        "ty le (%)", "ghi chu (neu co)"],
    "ds_co_dong_sang_lap_ctcp": [
        "stt", "ten co dong", "quoc tich",
        "so giay to phap ly cua ca nhan/to chuc",
        "dia chi lien lac doi voi ca nhan; dia chi tru so chinh doi voi to chuc",
        "loai co phan", "so co phan",
        "gia tri co phan (vnd va gia tri tuong duong theo don vi tien nuoc ngoai, neu co)",
        "ty le (%)", "ghi chu (neu co)"],
    "ds_co_dong_nuoc_ngoai_ctcp": [
        "stt", "ten co dong", "quoc tich",
        "so giay to phap ly cua ca nhan/to chuc",
        "dia chi lien lac doi voi ca nhan; dia chi tru so chinh doi voi to chuc",
        "loai co phan", "so co phan",
        "gia tri co phan (vnd va gia tri tuong duong theo don vi tien nuoc ngoai, neu co)",
        "ty le (%)", "ghi chu (neu co)"],
    "ds_thanh_vien_hop_danh_dhdn": [
        "stt", "ten thanh vien hop danh", "quoc tich",
        "so dinh danh ca nhan/so ho chieu/ho chieu nuoc ngoai hoac giay to co "
        "gia tri thay the ho chieu nuoc ngoai",
        "dia chi lien lac",
        "phan von gop (vnd va gia tri tuong duong theo don vi tien nuoc ngoai, neu co)",
        "ty le (%)"],
}
# tag cot tren hang khuon {_stt} cua 4 luoi thanh vien (ngoai {_stt})
MEMBER_COL_TAGS = {
    "ds_thanh_vien_tnhh_2tv": ["ten_thanh_vien", "quoc_tich",
                               "so_gtpl_ca_nhan_to_chuc", "dia_chi_lien_lac",
                               "phan_von_gop", "ty_le", "ghi_chu"],
    "ds_co_dong_sang_lap_ctcp": ["ten_co_dong", "quoc_tich", "so_gtpl",
                                 "dia_chi_lien_lac", "loai_co_phan",
                                 "so_co_phan", "gia_tri_co_phan", "ty_le",
                                 "ghi_chu"],
    "ds_co_dong_nuoc_ngoai_ctcp": ["ten_co_dong", "quoc_tich", "so_gtpl",
                                   "dia_chi_lien_lac", "loai_co_phan",
                                   "so_co_phan", "gia_tri_co_phan", "ty_le",
                                   "ghi_chu"],
    "ds_thanh_vien_hop_danh_dhdn": ["ten_thanh_vien_hop_danh", "quoc_tich",
                                    "so_dinh_danh_ho_chieu",
                                    "dia_chi_lien_lac", "phan_von_gop",
                                    "ty_le"],
}
# so w:tbl / dung thu tu loop trong moi vung section chinh (P2)
SECTION_TABLE_LOOPS = {
    "loai_hinh_dntn": ["ds_nganh_dntn"],
    "loai_hinh_tnhh_1tv": ["ds_nganh_tnhh_1tv"],
    "loai_hinh_tnhh_2tv": ["ds_nganh_tnhh_2tv", "ds_thanh_vien_tnhh_2tv"],
    "loai_hinh_ctcp": ["ds_nganh_ctcp", "ds_co_dong_sang_lap_ctcp",
                       "ds_co_dong_nuoc_ngoai_ctcp"],
    "loai_hinh_dhdn": ["ds_nganh_dhdn", "ds_thanh_vien_hop_danh_dhdn"],
}

# ---------------------------------------------------------------------------
# Hop dong P1.2 Option D: 16 marker dieu kien tren template that
# ---------------------------------------------------------------------------
MAIN_FLAGS = ["loai_hinh_dntn", "loai_hinh_tnhh_1tv", "loai_hinh_tnhh_2tv",
              "loai_hinh_ctcp", "loai_hinh_dhdn"]
# 3 cap footnote cuoi tai lieu ('Ghi tên của tất cả người đại diện...' 1/2/3)
FOOTNOTE_FLAGS = ["loai_hinh_tnhh_1tv", "loai_hinh_tnhh_2tv", "loai_hinh_ctcp"]
FLAG_VALUE = {"loai_hinh_dntn": "DNTN", "loai_hinh_tnhh_1tv": "TNHH_1TV",
              "loai_hinh_tnhh_2tv": "TNHH_2TV", "loai_hinh_ctcp": "CTCP",
              "loai_hinh_dhdn": "DHDN"}
FLAG_TO_LOOP = dict(zip(MAIN_FLAGS, EXPECTED_IDS))
EXPECTED_SEQUENCE = (
    [tok for f in MAIN_FLAGS for tok in ("{?%s}" % f, "{/%s}" % f)] +
    [tok for f in FOOTNOTE_FLAGS for tok in ("{?%s}" % f, "{/%s}" % f)]
)

HEADING_TEXT = "5. Ngành, nghề kinh doanh"
HEADERS_FOLD = ["stt", "ten nganh", "ma nganh",
                "nganh, nghe kinh doanh chinh"]
COL_TAGS = ["ten_nganh", "ma_nganh", "la_nganh_chinh"]
# anchor '(TÊN ...)' cua tung bien the (da fold) — marker mo dung ngay truoc
VARIANT_ANCHOR_FOLD = {
    "loai_hinh_dntn": "(ten doanh nghiep tu nhan)",
    "loai_hinh_tnhh_1tv": "(ten cong ty tnhh mot thanh vien)",
    "loai_hinh_tnhh_2tv": "(ten cong ty tnhh hai thanh vien)",
    "loai_hinh_ctcp": "(ten cong ty co phan)",
    "loai_hinh_dhdn": "(ten cong ty hop danh)",
}

# Tieu de cot tan du ky vong TRONG VUNG tren file NGUON (phan theo loai file);
# template khong con tan du — 5 vung deu la w:tbl that, kiem bang analyze().
EXPECTED_REMNANTS = {
    "ds_nganh_dntn": ["stt", "ten nganh", "ma nganh",
                      "nganh, nghe kinh doanh chinh"],
    "ds_nganh_tnhh_1tv": ["stt", "ten nganh", "ma nganh"],
    "ds_nganh_tnhh_2tv": ["stt", "ten nganh", "ma nganh"],
    "ds_nganh_ctcp": ["stt", "ten nganh", "ma nganh"],
    "ds_nganh_dhdn": ["stt", "ten nganh", "ma nganh"],
}

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(tag: str) -> str:
    return "{%s}%s" % (W_NS, tag.split(":")[-1])


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


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def body_paragraphs(doc):
    return [Paragraph(el, doc) for el in doc.element.body.iterchildren()
            if el.tag == qn("w:p")]


def top_level_tables(doc):
    return [el for el in doc.element.body.iterchildren() if el.tag == qn("w:tbl")]


def para_bold(para) -> bool:
    return any(r.bold for r in para.runs if r.text.strip())


def find_heading_hits(paras, match_heading: str):
    """Tat ca chi so paragraph co text (da fold) == match_heading (da fold)."""
    want = fold(one_line(match_heading))
    return [i for i, p in enumerate(paras) if fold(one_line(p.text)) == want]


def find_end_marker(paras, start: int, end_markers: list):
    """Paragraph dau tien sau start khop mot end_marker (regex tren text fold)."""
    for j in range(start + 1, len(paras)):
        ft = fold(one_line(paras[j].text))
        if not ft:
            continue
        for pat in end_markers:
            if re.search(pat, ft):
                return j, pat
    return None, None


def find_section_marker(paras, start: int):
    """Marker loai hinh gan nhat TRUOC start: '(TÊN ...)' hoac 'CÔNG BỐ ...'."""
    for j in range(start - 1, -1, -1):
        t = one_line(paras[j].text)
        if t.startswith("(") and "TÊN" in t.upper():
            return j, t
    return None, ""


def remnant_headers_in_region(paras, start: int, end: int):
    """Cac paragraph khong rong giua heading va end marker (tieu de cot tan du)."""
    out = []
    for j in range(start + 1, end):
        t = one_line(paras[j].text)
        if t:
            out.append((j, t, fold(t)))
    return out


def verify_file(label: str, path: Path, occurrences: list,
                remnant_map: dict) -> dict:
    """Verify 5 occurrence tren mot file; tra ve {occurrence_id: (anchor,end)}."""
    print()
    print("=" * 74)
    print("FILE [%s]: %s" % (label, path.relative_to(ROOT)))
    doc = Document(str(path))
    paras = body_paragraphs(doc)
    tbls = top_level_tables(doc)
    print("body paragraphs: %d | top-level tables: %d" % (len(paras), len(tbls)))

    regions = {}
    match_heading = occurrences[0]["match_heading"]
    hits_all = find_heading_hits(paras, match_heading)
    print("heading khop %r: %d lan tai chi so %s"
          % (match_heading, len(hits_all), hits_all))
    assert len(hits_all) == 5, \
        "%s: ky vong dung 5 heading %r, thay %d" % (label, match_heading,
                                                    len(hits_all))

    for occ in occurrences:
        oid = occ["occurrence_id"]
        nth = occ["nth"]
        assert 1 <= nth <= len(hits_all), \
            "%s/%s: nth=%d vuot so heading tim thay (%d)" % (
                label, oid, nth, len(hits_all))
        anchor_idx = hits_all[nth - 1]
        hp = paras[anchor_idx]
        sec_idx, sec_text = find_section_marker(paras, anchor_idx)
        end_idx, end_pat = find_end_marker(paras, anchor_idx, occ["end_markers"])
        assert end_idx is not None, \
            "%s/%s: khong tim thay end_marker %s sau p%04d" % (
                label, oid, occ["end_markers"], anchor_idx)
        regions[oid] = (anchor_idx, end_idx)

        print("-" * 74)
        print("[%s] nth=%d  id=%s  sync_group=%s"
              % (label, nth, oid, occ.get("sync_group")))
        print("  loai hinh : p%04d %r" % (sec_idx if sec_idx is not None else -1,
                                          sec_text[:70]))
        print("  ANCHOR    : p%04d bold=%s text=%r"
              % (anchor_idx, para_bold(hp), one_line(hp.text)))
        remnants = remnant_headers_in_region(paras, anchor_idx, end_idx)
        for j, t, f in remnants:
            print("  remnant   : p%04d %r (fold=%r)" % (j, t[:60], f[:60]))
        got_folded = [f for _j, _t, f in remnants]
        want_remnants = remnant_map.get(oid, [])
        missing = [h for h in want_remnants if h not in got_folded]
        extra = [f for f in got_folded if f not in want_remnants]
        assert not missing, "%s/%s: thieu tieu de cot tan du %s" % (
            label, oid, missing)
        assert not extra, "%s/%s: co paragraph la trong vung: %s" % (
            label, oid, extra)
        ep = paras[end_idx]
        print("  END MARKER: p%04d regex=%r text=%r"
              % (end_idx, end_pat, one_line(ep.text)[:80]))
    return regions


# ---------------------------------------------------------------------------
# Phan B: phân tích cấu trúc XML thật của template (thuần ElementTree)
# ---------------------------------------------------------------------------

def el_text(el) -> str:
    """Nối toàn bộ <w:t> trong phần tử (mô phỏng cách engine đọc text)."""
    return "".join(t.text or "" for t in el.iter(q("w:t")))


def marker_kind(text: str):
    """('open'|'close', ten_flag) nếu TOÀN BỘ text là một marker điều kiện."""
    s = one_line(text)
    m = re.fullmatch(r"\{\?([A-Za-z0-9_]+)\}", s)
    if m:
        return ("open", m.group(1))
    m = re.fullmatch(r"\{/([A-Za-z0-9_]+)\}", s)
    if m:
        return ("close", m.group(1))
    return None


def analyze_document_xml(xml: str) -> list[tuple[str, str]]:
    """Phân tích cấu trúc document.xml của PLI_M72 -> danh sách (code, chi tiết).

    Danh sách rỗng = template đúng cấu trúc P1.2 (5 heading, 5 w:tbl loop
    đúng biến thể, 16 marker điều kiện đúng sequence/vị trí).
    """
    issues: list[tuple[str, str]] = []

    def add(code: str, msg: str) -> None:
        issues.append((code, msg))

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        return [("PARSE_ERROR", "document.xml không parse được: %s" % exc)]
    body = root.find(q("w:body"))
    if body is None:
        return [("PARSE_ERROR", "thiếu w:body")]
    children = list(body)

    # ---- 1. heading '5. Ngành, nghề kinh doanh' --------------------------
    heading_idx = [i for i, el in enumerate(children)
                   if el.tag == q("w:p")
                   and fold(one_line(el_text(el))) == fold(HEADING_TEXT)]
    if len(heading_idx) != 5:
        add("MISSING_HEADING",
            "kỳ vọng đúng 5 heading %r, thấy %d tại %s"
            % (HEADING_TEXT, len(heading_idx), heading_idx))

    # ---- 2. [P2 pin sync 2026-09-03] 9 w:tbl top-level (5 nganh + 4 TV/CD) -
    tbl_idx = [i for i, el in enumerate(children) if el.tag == q("w:tbl")]
    tbls = [children[i] for i in tbl_idx]
    if len(tbls) != len(EXPECTED_TABLE_LOOPS):
        add("TABLE_COUNT_MISMATCH",
            "kỳ vọng đúng %d w:tbl top-level, thấy %d"
            % (len(EXPECTED_TABLE_LOOPS), len(tbls)))

    # heading '5. Ngành...' đứng NGAY TRƯỚC đúng 5 BẢNG NGÀNH; 4 lưới thành
    # viên nằm tiếp sau bảng ngành của cùng biến thể (không có heading riêng)
    for k in INDUSTRY_TABLE_INDEXES:
        if k >= len(tbl_idx):
            continue
        ti = tbl_idx[k]
        prev = children[ti - 1] if ti > 0 else None
        if (prev is None or prev.tag != q("w:p")
                or fold(one_line(el_text(prev))) != fold(HEADING_TEXT)):
            add("HEADING_NOT_ADJACENT",
                "bảng %d không đứng ngay sau heading %r" % (k, HEADING_TEXT))

    # ---- 3+4. từng bảng: header + hàng khuôn {_stt} + loop đúng biến thể ---
    # [P2 pin sync 2026-09-03] áp cho cả 9 bảng: 5 bảng nganh giữ header 4 ô
    # P1.2; 4 lưới thành viên pin header/tag cột riêng theo MEMBER_*.
    for k, tbl in enumerate(tbls[:len(EXPECTED_TABLE_LOOPS)]):
        want_id = EXPECTED_TABLE_LOOPS[k]
        want_member = want_id in MEMBER_HEADERS_FOLD
        want_hdrs = (MEMBER_HEADERS_FOLD.get(want_id)
                     if want_member else HEADERS_FOLD)
        want_cols = (MEMBER_COL_TAGS.get(want_id)
                     if want_member else COL_TAGS)
        rows = tbl.findall(q("w:tr"))

        hdr_cells = ([one_line(el_text(tc))
                      for tc in rows[0].findall(q("w:tc"))] if rows else [])
        got_hdr = [fold(c) for c in hdr_cells]
        if got_hdr != want_hdrs:
            if len(got_hdr) != len(want_hdrs):
                add("HEADER_MISSING_COL",
                    "bảng %d (%s): hàng đầu có %d ô != %d" % (k, want_id,
                                                              len(got_hdr),
                                                              len(want_hdrs)))
            else:
                for ci, (g, w) in enumerate(zip(got_hdr, want_hdrs)):
                    if g != w:
                        add("HEADER_MISSING_COL",
                            "bảng %d (%s): ô header %d = %r != %r"
                            % (k, want_id, ci, g, w))

        text_all = el_text(tbl)
        opens = re.findall(r"\{#([A-Za-z0-9_]+)\}", text_all)
        closes = re.findall(r"\{/([A-Za-z0-9_]+)\}", text_all)
        foreign = sorted(set(opens + closes) - {want_id})
        if foreign:
            add("LOOP_TAG_CROSS_CONTAMINATION",
                "bảng %d chứa loop tag của biến thể khác: %s (chỉ được %s)"
                % (k, foreign, want_id))
        if opens != [want_id] or closes != [want_id]:
            add("WRONG_LOOP_ORDER",
                "bảng %d: loop mở=%s đóng=%s != [%s]"
                % (k, opens, closes, want_id))

        khuon = [ri for ri, r in enumerate(rows) if "{_stt}" in el_text(r)]
        if not khuon:
            add("TABLE_ROW_MISSING_STT",
                "bảng %d (%s): không có hàng khuôn {_stt}" % (k, want_id))
        else:
            rt = el_text(rows[khuon[0]])
            missing_cols = [c for c in want_cols if "{%s}" % c not in rt]
            if missing_cols:
                add("TABLE_ROW_MISSING_COL",
                    "bảng %d (%s): hàng khuôn thiếu tag cột %s"
                    % (k, want_id, missing_cols))
            if len(khuon) != 1:
                add("TABLE_ROW_MISSING_STT",
                    "bảng %d (%s): có %d hàng khuôn {_stt} != 1"
                    % (k, want_id, len(khuon)))

    # ---- 5. marker điều kiện ----------------------------------------------
    events = []  # (child_index, kind, name)
    for i, el in enumerate(children):
        if el.tag != q("w:p"):
            continue
        mk = marker_kind(el_text(el))
        if mk:
            events.append((i, mk[0], mk[1]))
    seq = ["{%s%s}" % ("?" if kind == "open" else "/", name)
           for _i, kind, name in events]
    if seq != EXPECTED_SEQUENCE:
        add("COND_SEQUENCE_BROKEN",
            "chuỗi marker %s != kỳ vọng %s" % (seq, EXPECTED_SEQUENCE))

    # marker KHONG được nằm trong w:tbl (engine chỉ xử lý con trực tiếp body)
    for k, tbl in enumerate(tbls):
        for p_el in tbl.iter(q("w:p")):
            if marker_kind(el_text(p_el)):
                add("COND_MARKER_IN_TABLE",
                    "marker điều kiện nằm TRONG w:tbl %d" % k)

    # ghép cặp open/close bằng stack (độc lập với việc seq có khớp hay không)
    pairs: list[tuple[str, int, int]] = []
    stack_err = None
    stack: list[tuple[str, int]] = []
    for i, kind, name in events:
        if kind == "open":
            stack.append((name, i))
        else:
            if not stack:
                stack_err = "{/%s} đóng mà không có {?} mở" % name
                break
            oname, oi = stack.pop()
            if oname != name:
                stack_err = "{?%s} bị đóng bởi {/%s} sai cặp (lồng chéo)" % (
                    oname, name)
                break
            pairs.append((oname, oi, i))
    if stack_err is None and stack:
        stack_err = "{?%s} không được đóng trước hết body" % stack[-1][0]
    if stack_err:
        add("COND_SEQUENCE_BROKEN", stack_err)

    if stack_err is None:
        mains, foots = pairs[:5], pairs[5:]
        # mỗi vùng CHÍNH [open, close): đúng các w:tbl loop theo biến thể
        # [P2 pin sync 2026-09-03] vùng TNHH_2TV chứa thêm lưới thành viên,
        # CTCP chứa thêm 2 lưới cổ đông, DHDN chứa thêm lưới thành viên HD.
        for j, (name, oi, ci) in enumerate(mains):
            inside_tbls = [el for el in children[oi + 1:ci]
                           if el.tag == q("w:tbl")]
            want_loops = SECTION_TABLE_LOOPS.get(name)
            if want_loops is None:
                add("COND_SECTION_MISMATCH",
                    "flag ?%s không có trong section_cond options" % name)
            elif len(inside_tbls) != len(want_loops):
                add("COND_SECTION_MISMATCH",
                    "vùng chính #%d {?%s}: %d w:tbl trong vùng != %d"
                    % (j, name, len(inside_tbls), len(want_loops)))
            else:
                for n, tbl_el in enumerate(inside_tbls):
                    got = re.findall(r"\{#([A-Za-z0-9_]+)\}",
                                     el_text(tbl_el))
                    if got != [want_loops[n]]:
                        add("COND_SECTION_MISMATCH",
                            "vùng {?%s} bảng #%d loop %s != [%s]"
                            % (name, n, got, want_loops[n]))
            # marker mở đứng ngay trước anchor '(TÊN ...)' của đúng biến thể
            nxt = children[oi + 1] if oi + 1 < len(children) else None
            want_anchor = VARIANT_ANCHOR_FOLD.get(name)
            if (want_anchor is None or nxt is None or nxt.tag != q("w:p")
                    or fold(one_line(el_text(nxt))) != want_anchor):
                add("COND_MARKER_NOT_BEFORE_ANCHOR",
                    "{?%s} phải đứng ngay trước anchor %r" % (name,
                                                              want_anchor))
            # marker đóng đứng ngay trước marker mở kế / dòng gạch dưới cuối
            after = children[ci + 1] if ci + 1 < len(children) else None
            if j < len(mains) - 1:
                nxt_flag = mains[j + 1][0]
                if (after is None or after.tag != q("w:p")
                        or marker_kind(el_text(after)) != ("open", nxt_flag)):
                    add("COND_MARKER_NOT_BEFORE_ANCHOR",
                        "{/%s} phải đứng ngay trước marker mở kế ({?%s})"
                        % (name, nxt_flag))
            else:
                if (after is None or after.tag != q("w:p")
                        or not one_line(el_text(after)).startswith("_")):
                    add("COND_MARKER_NOT_BEFORE_ANCHOR",
                        "{/%s} phải đứng ngay trước dòng gạch dưới kết thúc "
                        "chung '____'" % name)
        # vùng FOOTNOTE: không được chứa bảng; marker mở trước dòng ghi chú
        for name, oi, ci in foots:
            inside_tbls = [el for el in children[oi + 1:ci]
                           if el.tag == q("w:tbl")]
            if inside_tbls:
                add("COND_SECTION_MISMATCH",
                    "vùng footnote {?%s} không được chứa w:tbl" % name)
            nxt = children[oi + 1] if oi + 1 < len(children) else None
            txt = (fold(one_line(el_text(nxt)))
                   if nxt is not None and nxt.tag == q("w:p") else "")
            if not re.sub(r"^[\d\s]*", "", txt).startswith(
                    "ghi ten cua tat ca nguoi dai dien"):
                add("COND_MARKER_NOT_BEFORE_ANCHOR",
                    "{?%s} (footnote) phải đứng ngay trước dòng "
                    "'Ghi tên của tất cả người đại diện...'" % name)
    return issues


def template_document_xml() -> str:
    with zipfile.ZipFile(TEMPLATE_PATH) as z:
        return z.read("word/document.xml").decode("utf-8")


# ---------------------------------------------------------------------------
# Các đột biến NEGATIVE (trên bản copy XML trong bộ nhớ, không ghi file)
# ---------------------------------------------------------------------------

def _enclosing_para_bounds(xml: str, idx: int) -> tuple[int, int]:
    start = max(xml.rfind("<w:p ", 0, idx), xml.rfind("<w:p>", 0, idx))
    assert start >= 0, "không tìm thấy <w:p> bao quanh token tại %d" % idx
    end = xml.index("</w:p>", idx) + len("</w:p>")
    return start, end


def _replace_nth(s: str, old: str, new: str, n: int) -> str:
    idx = -1
    for _ in range(n):
        idx = s.index(old, idx + 1)
    return s[:idx] + new + s[idx + len(old):]


def mutate_blank_header_cell(xml: str) -> str:
    """(a) xoá text ô header 'Tên ngành' của bảng 0."""
    return xml.replace(">Tên ngành<", "><", 1)


def mutate_swap_loops(xml: str) -> str:
    """(b) hoán đổi tên loop: bảng 0 (dntn) <-> bảng 4 (ctcp)."""
    xml = xml.replace("{#ds_nganh_dntn}", "{#ds_nganh_ctcp}")
    xml = xml.replace("{/ds_nganh_dntn}", "{/ds_nganh_ctcp}")
    return xml


def mutate_swap_section_flags(xml: str) -> str:
    """(c) hoán đổi 2 flag trong sequence: cặp chính tnhh_1tv -> ctcp."""
    xml = _replace_nth(xml, "{?loai_hinh_tnhh_1tv}", "{?loai_hinh_ctcp}", 1)
    xml = _replace_nth(xml, "{/loai_hinh_tnhh_1tv}", "{/loai_hinh_ctcp}", 1)
    return xml


def mutate_drop_marker_pair(xml: str) -> str:
    """(d) bỏ cả cặp marker của DHDN (mở + đóng)."""
    for tok in ("{?loai_hinh_dhdn}", "{/loai_hinh_dhdn}"):
        i = xml.index(tok)
        a, b = _enclosing_para_bounds(xml, i)
        xml = xml[:a] + xml[b:]
    return xml


def mutate_duplicate_open(xml: str) -> str:
    """(e) nhân đôi marker mở {?loai_hinh_dntn}."""
    i = xml.index("{?loai_hinh_dntn}")
    a, b = _enclosing_para_bounds(xml, i)
    return xml[:b] + xml[a:b] + xml[b:]


def mutate_marker_into_table(xml: str) -> str:
    """(f) chèn một marker vào trong cell của bảng 0."""
    i = xml.index("{#ds_nganh_dntn}")
    j = xml.index("</w:tc>", i)
    inject = ('<w:p><w:r><w:t xml:space="preserve">'
              "{?loai_hinh_dntn}</w:t></w:r></w:p>")
    return xml[:j] + inject + xml[j:]


def codes_of(xml: str) -> set:
    return {code for code, _msg in analyze_document_xml(xml)}


def show_issues(label: str, issues: list) -> None:
    if issues:
        print("  [%s] %d issue:" % (label, len(issues)))
        for code, msg in issues:
            print("    - %s: %s" % (code, msg))


# ---------------------------------------------------------------------------
# Các check
# ---------------------------------------------------------------------------

@check("spec JSON: entry nganh 5 occurrence + 4 entry thanh vien P2 + "
       "section_cond 5 option khop 1-1 theo thu tu")
def t_spec_contract():
    raw = SPEC_PATH.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    entries = data.get("tables") or []
    # [P2 pin sync 2026-09-03] spec M72 gio co 5 table entry: 1 entry nganh
    # (5 occurrence, sync_group chung) + 4 entry nested-grid thanh vien/co dong
    # (moi entry 1 occurrence, sync_group=null) do lane P2 rebuild them.
    assert len(entries) == 5, "ky vong 5 table entry, thay %d" % len(entries)
    occs = entries[0].get("occurrences") or []
    assert [o["occurrence_id"] for o in occs] == EXPECTED_IDS, \
        "occurrence_id sai thu tu/sai ten: %s" % [o.get("occurrence_id")
                                                  for o in occs]
    for k, o in enumerate(occs, 1):
        assert o["nth"] == k, "%s: nth=%r != %d" % (o["occurrence_id"], o["nth"], k)
        assert o["match_heading"].strip() == HEADING_TEXT, \
            "match_heading khac text da xac minh: %r" % o["match_heading"]
        assert o["sync_group"] == "ds_nganh_pli_m72", \
            "sync_group sai: %r" % o["sync_group"]
        for pat in o["end_markers"]:
            re.compile(pat)
    # cau hinh hop le cu phai duoc giu nguyen
    ent = entries[0]
    assert ent["pos"] == "after" and ent["no_default_drops"] is True
    assert ent["drop_until"] == "^6\\. von"
    assert len(ent["headers"]) == 4

    # P2: 4 entry thanh vien — pin contract nested-grid moi
    member_ids = [lid for lid in EXPECTED_TABLE_LOOPS if lid not in EXPECTED_IDS]
    got_member_ids = [e["occurrences"][0]["occurrence_id"] for e in entries[1:]]
    assert got_member_ids == member_ids, \
        "entry thanh vien sai thu tu/sai ten: %s" % got_member_ids
    for e in entries[1:]:
        oid = e["occurrences"][0]["occurrence_id"]
        assert e.get("spec", {}).get("kind") == "nested-grid", \
            "%s: spec.kind phai nested-grid" % oid
        assert e.get("spec", {}).get("id") == oid, \
            "%s: spec.id phai = occurrence_id (ten loop)" % oid
        assert len(e.get("occurrences") or []) == 1, \
            "%s: ky vong 1 occurrence" % oid
        o = e["occurrences"][0]
        assert o["nth"] == 1, "%s: nth != 1" % oid
        assert o["sync_group"] is None, \
            "%s: sync_group phai null (khong auto-sync giua cac luoi khac nghia)" % oid
        for pat in o["end_markers"]:
            re.compile(pat)

    # P1.2: section_consistency giua occurrences va section_cond
    sc = data.get("section_cond") or {}
    assert sc.get("value_key") == "dn.loai_hinh", \
        "section_cond.value_key sai: %r" % sc.get("value_key")
    opts = sc.get("options") or []
    assert len(opts) == 5, \
        "section_cond phai co dung 5 option, thay %d" % len(opts)
    for k, opt in enumerate(opts):
        oid, want_flag = EXPECTED_IDS[k], MAIN_FLAGS[k]
        assert opt.get("occurrence_id") == oid, \
            "option %d occurrence_id %r != %r" % (k, opt.get("occurrence_id"), oid)
        assert opt.get("flag") == want_flag, \
            "option %d flag %r != %r" % (k, opt.get("flag"), want_flag)
        assert opt.get("value") == FLAG_VALUE[want_flag], \
            "option %d value %r != %r" % (k, opt.get("value"),
                                          FLAG_VALUE[want_flag])
    assert [o["flag"] for o in opts] == MAIN_FLAGS, \
        "flags cua section_cond khac thu tu 5 marker section chinh"


@check("file NGUON: 5 vung dung anchor/end marker/tan du nhu evidence P1-B")
def t_source_regions():
    occs = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))["tables"][0][
        "occurrences"]
    path = source_path()
    doc = Document(str(path))
    assert not top_level_tables(doc), \
        "file nguon khong duoc co w:tbl top-level (moi luoi deu la paragraph roi)"
    regions = verify_file("NGUON", path, occs, EXPECTED_REMNANTS)
    expect = {"ds_nganh_dntn": (13, 22), "ds_nganh_tnhh_1tv": (42, 52),
              "ds_nganh_tnhh_2tv": (85, 95), "ds_nganh_ctcp": (134, 141),
              "ds_nganh_dhdn": (168, 175)}
    assert regions == expect, \
        "anchor/end NGUON %s != evidence da khoa %s" % (regions, expect)


@check("TEMPLATE cau truc that: analyze_document_xml tra ve 0 issue "
       "(5 heading + 9 w:tbl + 16 marker dieu kien)")
def t_template_structure():
    xml = template_document_xml()
    issues = analyze_document_xml(xml)
    print("  template: %d w:tbl top-level, %d marker dieu kien"
          % (len([e for e in ET.fromstring(xml).find(q("w:body"))
                  if e.tag == q("w:tbl")]),
             sum(1 for tok in EXPECTED_SEQUENCE if xml.count(tok))))
    show_issues("POSITIVE", issues)
    assert issues == [], \
        "template that phai dat 0 issue cau truc, thay: %s" % (issues,)


@check("NEG (a): xoa text 1 o header -> HEADER_MISSING_COL")
def t_neg_header_missing_col():
    codes = codes_of(mutate_blank_header_cell(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "HEADER_MISSING_COL" in codes, \
        "mutate (a) phai bat duoc HEADER_MISSING_COL, thay %s" % sorted(codes)


@check("NEG (b): hoan doi ten loop 2 bang -> WRONG_LOOP_ORDER + "
       "LOOP_TAG_CROSS_CONTAMINATION")
def t_neg_wrong_loop_order():
    codes = codes_of(mutate_swap_loops(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "WRONG_LOOP_ORDER" in codes, \
        "mutate (b) phai bat duoc WRONG_LOOP_ORDER, thay %s" % sorted(codes)
    assert "LOOP_TAG_CROSS_CONTAMINATION" in codes, \
        "mutate (b) phai bat duoc LOOP_TAG_CROSS_CONTAMINATION, thay %s" % (
            sorted(codes),)


@check("NEG (c): hoan doi 2 flag section -> COND_SECTION_MISMATCH")
def t_neg_cond_section_mismatch():
    codes = codes_of(mutate_swap_section_flags(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "COND_SECTION_MISMATCH" in codes, \
        "mutate (c) phai bat duoc COND_SECTION_MISMATCH, thay %s" % sorted(codes)


@check("NEG (d): bo 1 cap marker -> COND_SEQUENCE_BROKEN")
def t_neg_sequence_drop_pair():
    codes = codes_of(mutate_drop_marker_pair(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "COND_SEQUENCE_BROKEN" in codes, \
        "mutate (d) phai bat duoc COND_SEQUENCE_BROKEN, thay %s" % sorted(codes)


@check("NEG (e): nhan doi 1 marker mo -> COND_SEQUENCE_BROKEN")
def t_neg_sequence_duplicate_open():
    codes = codes_of(mutate_duplicate_open(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "COND_SEQUENCE_BROKEN" in codes, \
        "mutate (e) phai bat duoc COND_SEQUENCE_BROKEN, thay %s" % sorted(codes)


@check("NEG (f): chen marker vao trong cell bang -> COND_MARKER_IN_TABLE")
def t_neg_marker_in_table():
    codes = codes_of(mutate_marker_into_table(template_document_xml()))
    print("  codes =", sorted(codes))
    assert "PARSE_ERROR" not in codes
    assert "COND_MARKER_IN_TABLE" in codes, \
        "mutate (f) phai bat duoc COND_MARKER_IN_TABLE, thay %s" % sorted(codes)


def source_path() -> Path:
    hits = sorted(ROOT.glob(SOURCE_GLOB))
    assert hits, "khong tim thay file nguon %s" % SOURCE_GLOB
    return hits[0]


def main() -> int:
    print("p1_b_verify_m72 (ban 2) — bang chung 5 occurrence + cau truc that "
          "PLI_M72 sau P1.2")
    t_spec_contract()
    t_source_regions()
    t_template_structure()
    t_neg_header_missing_col()
    t_neg_wrong_loop_order()
    t_neg_cond_section_mismatch()
    t_neg_sequence_drop_pair()
    t_neg_sequence_duplicate_open()
    t_neg_marker_in_table()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 74)
    print("p1_b_verify_m72: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    print()
    print("GHI CHU anchor manifest: T0 ghi '~#p1648,p1673,p1710,p1745,p1776'")
    print("(uoc luong tay, build_manifest.py:122 noi ro khong resolve duoc bang")
    print("may). Chi so dung bang may tren NGUON (paragraph space): "
          "13/42/85/134/168. TEMPLATE khong con tan du — 5 vung deu la w:tbl")
    print("that + 16 marker dieu kien, kiem bang analyze_document_xml().")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
