# -*- coding: utf-8 -*-
"""P1-C — Script tự verify điểm mù ngành nghề của PLII_M02 (lane PLII_M02).

Audit độc lập trên 3 tầng artifact, KHÔNG qua generator:

1. TEMPLATE NGUỒN (06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/
   PL2_Mau_02_*.docx): điển 4 vùng ngành theo heading gốc, chứng minh
   toàn bộ lưới bị mất khi convert (0 w:tbl) và các tiêu đề cột Mục A
   bị tách thành paragraph rời.
2. TEMPLATE LÀM VIỆC (app/templates/PLII_M02.docx) + FORM_MAPS: mỗi w:tbl
   phải nằm trong đúng 1 vùng ngành và đồng bộ 1-1 với dynamic_tables.
3. BLOCKS (app/data/blocks/PLII_M02.json — READ ONLY): phân loại từng vùng
   DONE (có loop) / MISSING (chỉ có paragraph rơi) / NO_TABLE, kèm evidence
   chỉ số block.

Đồng thời kiểm tra contract occurrences trong
tools/form_specs/household/PLII_M02.json: đủ 6 occurrence_id ngữ nghĩa
(4 ngành: nganh_bo_sung, nganh_xoa_bo, nganh_sua_doi_chi_tiet,
nganh_hien_tai + 2 thành viên hộ gia đình P2: tv_hgd_sau_thay_doi,
tv_hgd_cap_doi), match_heading khớp đúng nth lần trong template, end_markers
tồn tại, sync_group=null (PLAN mục A cấm auto-sync giữa các loop khác nghĩa).

Lưu ý R0 triage (2026-08-26): match_heading trong spec lưu TEXT THƯỜNG
(vd '1. bo sung nganh, nghe kinh doanh') trong khi bảng REGIONS ở đây dùng
pattern regex có anchor '^'. So sánh phải theo HÀNH VI (hai pattern chọn
cùng một tập đoạn trong template), không so chuỗi strict equality — quy ước
giống p1_b_verify_m72.py (match_heading == HEADING_TEXT plain).

Kết luận câu hỏi của Lead: template M02 CÓ vùng thứ 4 "ngành hiện tại/
đăng ký lại" — chính là bảng ngành Mục C.3 (cấp đổi GCN ĐKHKD); đây là
w:tbl duy nhất của mẫu sau rebuild, đã có loop ds_nganh từ Wave 2C.

Exit code 0 = artifact nhất quán với spec; != 0 = mâu thuẫn cần xử lý.
Trạng thái MISSING của 3 vùng Mục A là HIỆN TRẠNG đã biết pre-integration,
không làm script fail.

Chạy:  $env:PYTHONIOENCODING='utf-8'; python -X utf8 tools/census/p1_c_verify_plii_m02.py
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document                    # noqa: E402
from docx.oxml.ns import qn                 # noqa: E402
from docx.text.paragraph import Paragraph   # noqa: E402

SPEC_PATH = ROOT / "tools" / "form_specs" / "household" / "PLII_M02.json"
WORKING_TMPL = ROOT / "app" / "templates" / "PLII_M02.docx"
BLOCKS_PATH = ROOT / "app" / "data" / "blocks" / "PLII_M02.json"
FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
SOURCE_DIR = ROOT / "06_ho_kinh_doanh_va_chuyen_doi" / "01_mau_ho_kinh_doanh"

LOOP_CARRIER_HIEN_TAI = "ds_nganh"  # bảng C.3 giữ loop production từ Wave 2C

# [P2 pin sync 2026-09-03] P2 rebuild them 2 luoi thanh vien ho gia dinh
# (nested-grid) vao PLII_M02: tv_hgd_sau_thay_doi (dau Muc A) +
# tv_hgd_cap_doi (Muc C.7) -> 4 vung nganh + 2 vung thanh vien = 6 vung ngu
# nghia, sap theo thu tu document (region_spans yeu cau heading tang dan).
MEMBER_REGION_IDS = {"tv_hgd_sau_thay_doi", "tv_hgd_cap_doi"}
TV_HGD_HDRS = ["STT", "Họ tên", "Ngày, tháng, năm sinh",
               "Số định danh cá nhân", "Giới tính", "Quốc tịch", "Dân tộc",
               "Nơi thường trú", "Nơi ở hiện tại", "Chữ ký"]

# (occurrence_id, heading_folded_regex, end_markers, headers, loop_name)
REGIONS = [
    ("tv_hgd_sau_thay_doi",
     r"^danh sach cac thanh vien ho gia dinh dang ky ho kinh doanh sau khi "
     r"thay doi",
     [r"^dang ky thay doi von kinh doanh"], TV_HGD_HDRS,
     "tv_hgd_sau_thay_doi"),
    ("nganh_bo_sung", r"^1\. bo sung nganh, nghe kinh doanh",
     [r"^2\. bo nganh, nghe kinh doanh"],
     ["STT", "Tên ngành, nghề kinh doanh được bổ sung", "Mã ngành",
      "Ngành, nghề kinh doanh chính"], "nganh_bo_sung"),
    ("nganh_xoa_bo", r"^2\. bo nganh, nghe kinh doanh",
     [r"^3\. sua doi nganh, nghe kinh doanh"],
     ["STT", "Tên ngành, nghề kinh doanh được bỏ khỏi danh sách đã đăng ký",
      "Mã ngành", "Ngành, nghề kinh doanh chính"], "nganh_xoa_bo"),
    ("nganh_sua_doi_chi_tiet", r"^3\. sua doi nganh, nghe kinh doanh",
     [r"^luu y: truong hop ho kinh doanh thay doi nganh",
      r"^dang ky thay doi noi dung dang ky thue"],
     ["STT", "Tên ngành, nghề kinh doanh", "Mã ngành"],
     "nganh_sua_doi_chi_tiet"),
    ("nganh_hien_tai", r"^3\. nganh, nghe kinh doanh",
     [r"^4\. von kinh doanh"],
     ["STT", "Tên ngành", "Mã ngành", "Ngành, nghề kinh doanh chính"],
     LOOP_CARRIER_HIEN_TAI),
    ("tv_hgd_cap_doi",
     r"^7\. thong tin ve cac thanh vien ho gia dinh dang ky ho kinh doanh",
     [r"^chu ho kinh doanh \(ky"], TV_HGD_HDRS, "tv_hgd_cap_doi"),
]

_problems: list[str] = []


def fail(msg: str) -> None:
    _problems.append(msg)
    print("  [X] %s" % msg)


def ok(msg: str) -> None:
    print("  [.] %s" % msg)


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def same_region(paras: list[str], pattern_audit: str, pattern_spec: str) -> bool:
    """Spec match_heading phải chọn ĐÚNG tập đoạn như pattern chuẩn audit.

    So theo hành vi trên danh sách paragraph (đã fold), không so chuỗi
    pattern — spec lưu plain text, REGIONS dùng regex có anchor.
    [P2 pin sync 2026-09-03] entry nested-grid (tv_hgd_*) lưu match_heading
    dạng tiếng Việt CÓ dấu -> fold pattern trước khi so khớp với paras đã
    fold; pattern đã fold sẵn đi qua fold() không đổi nên 4 vùng ngành giữ
    nguyên hành vi.
    """
    hits_a = [t for t in paras if re.search(pattern_audit, t)]
    hits_s = [t for t in paras if re.search(fold(pattern_spec), t)]
    return hits_a == hits_s


def selftest_same_region() -> None:
    """Negative selftest cho same_region — chạy mọi lần, fail nhanh nếu sai."""
    paras = ["3. nganh, nghe kinh doanh", "nganh khac", "4. von kinh doanh"]
    assert same_region(paras, r"^3\. nganh", "3. nganh, nghe kinh doanh"), \
        "anchor-less tương đương phải PASS"
    assert not same_region(paras, r"^3\. nganh", "3. sua doi nganh"), \
        "heading sai nội dung phải FAIL"
    assert not same_region(paras, r"^3\. nganh", "nganh"), \
        "pattern khớp nhiều hơn chuẩn audit phải FAIL"
    assert not same_region(paras, r"^3\. nganh", ""), \
        "match_heading rỗng phải FAIL"


def body_seq(doc):
    """[("p", text gập dấu) / ("tbl", chỉ số bảng)] theo thứ tự thân tài liệu."""
    seq = []
    ti = 0
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            txt = fold(re.sub(r"\s+", " ", Paragraph(child, doc).text)).strip()
            seq.append(("p", txt))
        elif child.tag == qn("w:tbl"):
            seq.append(("tbl", ti))
            ti += 1
    return seq


def region_spans(seq):
    """[(occ_id, start, end)] — assert heading duy nhất, theo thứ tự, có end."""
    spans = []
    prev = -1
    for occ_id, heading, ends, _hdrs, _loop in REGIONS:
        hits = [i for i, (k, t) in enumerate(seq)
                if k == "p" and re.search(heading, t)]
        if len(hits) != 1:
            fail("%s: heading %r khớp %d đoạn != 1" % (occ_id, heading,
                                                       len(hits)))
            continue
        h = hits[0]
        if h <= prev:
            fail("%s: heading (%d) không sau vùng trước (%d)" % (occ_id, h,
                                                                 prev))
        end = next((i for i in range(h + 1, len(seq))
                    if seq[i][0] == "p" and any(re.search(m, seq[i][1])
                                                for m in ends)), None)
        if end is None:
            fail("%s: không thấy end_marker sau heading" % occ_id)
            continue
        spans.append((occ_id, h, end))
        prev = h
    return spans


def classify_table(tbl) -> str:
    """Wave A (PLAN v4): phân loại bảng theo NỘI DUNG header, không theo vị
    trí trong tài liệu. Trả về:
      'band'     — header band (tên hộ/doanh nghiệp + quốc hiệu);
      'tax'      — bảng thuế a7 (header 'Chỉ tiêu');
      'industry' — bảng ngành.
    """
    if not tbl.rows or not tbl.rows[0].cells:
        return "industry"
    c0 = fold(tbl.rows[0].cells[0].text)
    if c0.startswith(("ten ho kinh doanh", "ten doanh nghiep")):
        return "band"
    if c0.startswith("chi tieu"):
        return "tax"
    # [Pin sync — F1-IN 2026-09-06] bảng thuế C5 cấp đổi (O1): header
    # 'STT / Các chỉ tiêu thông tin đăng ký thuế'
    if c0.startswith("stt / cac chi tieu"):
        return "tax_c5"
    return "industry"


def industry_owner_sequence(spans, tbl_entries):
    """Phép đối chiếu THEO THỨ TỰ vùng (Wave A, thay skip theo vị trí).

    tbl_entries: [(tbl_idx, cls)] theo thứ tự tài liệu. Bảng industry phải
    nằm trong đúng 1 vùng và xuất hiện đúng thứ tự vùng trong tài liệu —
    bắt được thiếu, thừa, ĐẢO region (so sánh sorted sẽ không bắt được đảo)
    và table_index lệch. Trả về (owners, problems).
    """
    owners: list[str] = []
    problems: list[str] = []
    for idx, cls in tbl_entries:
        # [Pin sync — F1-IN 2026-09-06] tax_c5 = bảng thuế C5 cấp đổi (O1):
        # không thuộc vùng ngành, không phải lỗi
        if cls in ("tax", "band", "tax_c5"):
            continue
        if cls != "industry":
            continue
        owner = next((oid for oid, h, e in spans if h < idx < e), None)
        if owner is None:
            # [P2 pin sync 2026-09-03] đối chiếu trên 6 vùng (4 nganh + 2 tv_hgd)
            problems.append("w:tbl thứ %d nằm ngoài 6 vùng ngành/thành viên"
                            % idx)
        else:
            owners.append(owner)
    return owners, problems


def selftest_table_classification() -> None:
    """Negative mutations (Wave A bước 3): band/thuế chen giữa các vùng ngành
    không được làm lệch phép đối chiếu; thiếu/đảo/ngoài vùng phải bị phát
    hiện."""
    from docx import Document as _Doc
    d = _Doc()
    band = d.add_table(rows=1, cols=2)
    band.rows[0].cells[0].text = "Tên hộ kinh doanh"
    band.rows[0].cells[1].text = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    tax = d.add_table(rows=1, cols=3)
    tax.rows[0].cells[0].text = "Chỉ tiêu"
    ind = d.add_table(rows=1, cols=4)
    ind.rows[0].cells[0].text = "STT"
    assert classify_table(band) == "band", "band phải nhận qua nội dung ô"
    assert classify_table(tax) == "tax", "thuế phải nhận qua header Chỉ tiêu"
    assert classify_table(ind) == "industry"

    spans = [("nganh_bo_sung", 0, 5), ("nganh_xoa_bo", 6, 10),
             ("nganh_sua_doi_chi_tiet", 11, 15), ("nganh_hien_tai", 16, 20)]
    expected = [oid for oid, _h, _e in spans]

    entries = [(1, "industry"), (3, "band"), (7, "industry"), (9, "tax"),
               (12, "industry"), (18, "industry")]
    owners, problems = industry_owner_sequence(spans, entries)
    assert owners == expected, owners
    assert not problems, problems

    # thiếu bảng vùng đầu → sequence hụt đầu
    owners2, _p = industry_owner_sequence(
        spans, [(7, "industry"), (12, "industry"), (18, "industry")])
    assert owners2 == expected[1:], "thiếu bảng phải lệch sequence: %r" % owners2

    owners3, _p = industry_owner_sequence(
        spans, [(1, "industry"), (7, "industry"), (18, "industry"),
                (12, "industry")])
    assert owners3 != expected, "đảo region phải bị gate thứ tự bắt: %r" % owners3

    _o4, problems4 = industry_owner_sequence(
        spans, [(1, "industry"), (22, "industry")])
    assert problems4, "bảng industry ngoài vùng phải ghi problem"


def find_source():
    if SOURCE_DIR.is_dir():
        hits = sorted(SOURCE_DIR.glob("PL2_Mau_02*.docx"))
        hits = [p for p in hits
                if not p.name.startswith("~$") and not p.name.startswith("_")]
        if hits:
            return hits[0]
    return None


def audit_source_template() -> None:
    print("== 1. TEMPLATE NGUON (goc chua qua generator) ==")
    src = find_source()
    if src is None or not src.exists():
        fail("không tìm thấy template nguồn trong %s" % SOURCE_DIR)
        return
    ok("nguon: %s" % src.name)
    doc = Document(str(src))
    seq = body_seq(doc)
    n_tbl = sum(1 for k, _ in seq if k == "tbl")
    if n_tbl != 0:
        fail("template nguồn có %d w:tbl, kỳ vọng 0 (mọi lưới bị converter "
             "mất khi convert)" % n_tbl)
    else:
        ok("0 w:tbl — mọi lưới ngành (cả bảng C.3) đã mất khi convert")

    spans = region_spans(seq)
    if len(spans) != len(REGIONS):
        fail("điển chỉ được %d/%d vùng" % (len(spans), len(REGIONS)))
        return
    for (occ_id, h, end), (_o, _h, _e, hdrs, _lp) in zip(spans, REGIONS):
        hdr_folds = [fold(re.sub(r"\s+", " ", hh)).strip() for hh in hdrs]
        texts = [t for k, t in seq[h + 1:end] if k == "p" and t]
        matched = {fi for fi, hf in enumerate(hdr_folds)
                   for t in texts if t.startswith(hf)}
        extra = [t for t in texts
                 if not any(t.startswith(hf) for hf in hdr_folds)]
        if occ_id == "nganh_hien_tai":
            # nguồn mất cả lưới C.3: vùng chỉ còn heading + đoạn trắng
            stray = [t for t in texts if t and not t.isdigit()]
            if stray:
                print("      (vùng C.3 nguồn còn: %r)" % stray[:3])
            ok("%s: heading '%s...' có ở nguồn, lưới đã mất (rebuild bởi "
               "generator)" % (occ_id, texts and "3. nganh"))
            continue
        if occ_id in MEMBER_REGION_IDS:
            # [P2 pin sync 2026-09-03] nguồn mất cả 2 lưới thành viên hộ gia
            # đình khi convert: tiêu đề cột bị dán thành 1 đoạn (glued
            # 'sttho ten...chu ky') — lưới thật được generator rebuild vào
            # app/templates + blocks (P2); ở nguồn chỉ pin đủ 10 tiêu đề cột.
            glued = " ".join(texts)
            missing_hdr = [hf for hf in hdr_folds if hf not in glued]
            if missing_hdr:
                fail("%s: nguồn thiếu tiêu đề cột (glued): %s"
                     % (occ_id, missing_hdr))
            else:
                ok("%s: nguồn còn đủ %d tiêu đề cột dán 1 đoạn (glued) — "
                   "lưới được generator rebuild (P2)"
                   % (occ_id, len(hdr_folds)))
            continue
        if extra:
            fail("%s: vùng chứa paragraph lạ %r" % (occ_id, extra[:3]))
        if matched != set(range(len(hdrs))):
            fail("%s: thiếu tiêu đề cột ở nguồn: %d/%d" % (
                occ_id, len(matched), len(hdrs)))
        else:
            ok("%s: đủ %d tiêu đề cột dạng paragraph rời (header tan du)"
               % (occ_id, len(hdrs)))


def audit_working_template_and_maps() -> None:
    print("== 2. TEMPLATE LAM VIEC + FORM_MAPS ==")
    doc = Document(str(WORKING_TMPL))
    seq = body_seq(doc)
    spans = region_spans(seq)

    fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))["PLII_M02"]
    fm_loops = sorted(t.get("loop") for t in
                      fm.get("dynamic_tables") or [] if t.get("loop"))
    ok("dynamic_tables khai báo: %r" % fm_loops)

    loop_to_occ = {lp: oid for oid, _h, _e, _hd, lp in REGIONS}
    unknown = [l for l in fm_loops if l not in loop_to_occ]
    if unknown:
        # [P2 pin sync 2026-09-03] 6 semantic region (4 nganh + 2 tv_hgd)
        fail("loop lạ ngoài 6 semantic region: %r" % unknown)

    # [Wave A 2026-09-02] Hủy skip theo vị trí (`first_tbl_seen`, `tax_start`):
    # band/thuế được nhận qua NỘI DUNG header (classify_table) nên skip mù
    # bảng đầu tiên/bảng sau mốc thuế đã ăn nhầm bảng ngành thật
    # (nganh_bo_sung / nganh_hien_tai). Đối chiếu giờ theo THỨ TỰ vùng.
    tbl_entries = []
    for i, (k, _v) in enumerate(seq):
        if k != "tbl":
            continue
        tbl_entries.append((i, classify_table(doc.tables[_v])))
    owners, problems = industry_owner_sequence(spans, tbl_entries)
    for p in problems:
        fail(p)
    expected = [oid for oid, _h, _e in spans]
    if owners != expected:
        fail("bảng ngành lệch thứ tự/thiếu/thừa so với vùng: %r vs %r"
             % (owners, expected))
    else:
        ok("đủ %d bảng ngành đúng vùng, đúng thứ tự: %r" % (len(owners),
                                                            owners))
    fm_declared = sorted(loop_to_occ[l] for l in fm_loops if l in loop_to_occ)
    if sorted(owners) != fm_declared:
        fail("mất đồng bộ template<->form_maps: bảng ngành ở %r vs khai báo %r"
             % (sorted(owners), fm_declared))
    else:
        ok("mỗi dynamic_tables có đúng 1 bảng thật trong vùng tương ứng: %r"
           % fm_declared)


def audit_blocks() -> list[tuple[str, str, str]]:
    print("== 3. BLOCKS (READ ONLY) — phan loai DONE/MISSING/NO_TABLE ==")
    data = json.loads(BLOCKS_PATH.read_text(encoding="utf-8"))

    def blk_text(b):
        if b.get("t") == "p":
            return fold("".join(r.get("text", "") for r in b.get("runs", [])))
        if b.get("t") == "loop":
            rows = b.get("rows") or []
            if rows and b.get("headerRows"):
                cells = rows[b["headerRows"][0]].get("cells") or []
                return fold(" ".join(
                    "".join(r.get("text", "") for r in c.get("runs", []))
                    for c in cells))
            return fold(b.get("loop", ""))
        return ""

    bseq = [(b.get("t"), blk_text(b)) for b in data["blocks"]]
    spans = []
    prev = -1
    for occ_id, heading, ends, _hdrs, _lp in REGIONS:
        h = next((i for i, (k, t) in enumerate(bseq)
                  if k == "p" and re.search(heading, t)), None)
        e = None
        if h is not None:
            e = next((i for i in range(h + 1, len(bseq))
                      if bseq[i][0] == "p" and any(re.search(m, bseq[i][1])
                                                   for m in ends)), None)
        if h is None or e is None:
            fail("%s: không điển được vùng trong blocks (h=%r, e=%r)"
                 % (occ_id, h, e))
            continue
        if h <= prev:
            fail("%s: vùng blocks chồng lấn/không theo thứ tự" % occ_id)
        spans.append((occ_id, h, e))
        prev = h

    loop_at = {}  # block index -> loop name
    for i, b in enumerate(data["blocks"]):
        if b.get("t") == "loop":
            loop_at[i] = b.get("loop")

    results = []
    for occ_id, _h, _e, _hdrs, lp in REGIONS:
        span = next((s for s in spans if s[0] == occ_id), None)
        if span is None:
            results.append((occ_id, "NO_TABLE", "không điển được vùng"))
            continue
        _oid, h, e = span
        inside = [(i, ln) for i, ln in loop_at.items() if h < i < e]
        ev = ("blocks B%03d-B%03d" % (h, e))
        if inside:
            names = sorted({ln for _i, ln in inside})
            if names != [lp]:
                fail("%s: vùng chứa loop %r, kỳ vọng [%r]" % (occ_id, names,
                                                              lp))
                results.append((occ_id, "DONE?", "%s, loop=%r" % (ev, names)))
            else:
                idxs = ", ".join("B%03d" % i for i, _l in inside)
                results.append((occ_id, "DONE", "%s, loop %s tại %s"
                                % (ev, lp, idxs)))
        else:
            hdr_idx = [i for i in range(h + 1, e) if bseq[i][1]]
            ev2 = "%s, header tan du %s" % (
                ev, ", ".join("B%03d" % i for i in hdr_idx) or "(trống)")
            results.append((occ_id, "MISSING", ev2))
    for occ_id, st, ev in results:
        print("  %-24s %-9s %s" % (occ_id, st, ev))
    return results


def audit_spec_contract() -> None:
    print("== 4. SPEC OCCURRENCE CONTRACT ==")
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    entries = raw.get("tables") or []
    seen = {}
    for e in entries:
        # [Lead sync 2026-08-28] entry fixed-matrix (a7_thue_chi_tieu_cu_moi,
        # D5.2 — lane cap-von) không dùng cơ chế occurrences; chỉ các entry
        # ngành dạng list mới cần occurrences 1/entry.
        if (e.get("spec") or {}).get("kind") == "fixed-matrix":
            continue
        occs = e.get("occurrences") or []
        if not occs:
            fail("entry %r thiếu occurrences" % e.get("spec", {}).get("id"))
            continue
        if len(occs) != 1:
            fail("entry %r có %d occurrences (M02 kỳ vọng 1/entry)"
                 % (e.get("spec", {}).get("id"), len(occs)))
        for occ in occs:
            oid = occ.get("occurrence_id")
            seen[oid] = e
            missing_keys = [k for k in ("occurrence_id", "match_heading",
                                        "nth", "sync_group", "end_markers")
                            if k not in occ]
            if missing_keys:
                fail("%s: thiếu key %r" % (oid, missing_keys))
            if occ.get("sync_group") is not None:
                fail("%s: sync_group phải null (PLAN mục A: không auto-sync "
                     "giữa các loop khác nghĩa)" % oid)
    want_ids = {o[0] for o in REGIONS}
    if set(seen) != want_ids:
        fail("occurrence_id %r != %r" % (sorted(seen), sorted(want_ids)))
        return
    # [P2 pin sync 2026-09-03] 6 occurrence_id ngữ nghĩa (4 ngành + 2 tv_hgd)
    ok("đủ %d occurrence_id ngữ nghĩa: %r" % (len(REGIONS), sorted(seen)))

    doc = Document(str(WORKING_TMPL))
    paras = [fold(re.sub(r"\s+", " ", Paragraph(child, doc).text)).strip()
             for child in doc.element.body.iterchildren()
             if child.tag == qn("w:p")]
    for oid, heading, ends, _hdrs, lp in REGIONS:
        occ = seen[oid]["occurrences"][0]
        if not same_region(paras, heading, occ.get("match_heading") or ""):
            fail("%s: match_heading lệch chuẩn audit" % oid)
        if occ.get("nth") != 1:
            fail("%s: nth != 1" % oid)
        # [P2 pin sync 2026-09-03] match_heading nested-grid có dấu -> fold
        n_hit = sum(1 for t in paras
                    if re.search(fold(occ["match_heading"]), t))
        if n_hit != occ.get("nth"):
            fail("%s: heading khớp %d lần != nth" % (oid, n_hit))
        for m in occ.get("end_markers") or []:
            if not any(re.search(m, t) for t in paras):
                fail("%s: end_marker %r không có trong template" % (oid, m))
        # [P2 pin sync 2026-09-03] entry nested-grid không có spec.loop —
        # tên loop trùng spec.id (semantic_key) theo convention P2.
        got_loop = (seen[oid]["spec"].get("loop")
                    or seen[oid]["spec"].get("id"))
        if got_loop != lp:
            fail("%s: entry spec.loop %r != %r" % (oid, got_loop, lp))
    if not _problems:
        ok("contract hợp lệ: heading/nth/end_markers/sync_group/loop khớp")


def main() -> int:
    print("P1-C VERIFY PLII_M02 — worktree %s" % ROOT)
    selftest_same_region()
    ok("selftest same_region (negative mutations) PASS")
    selftest_table_classification()
    ok("selftest classify_table/industry_owner_sequence (negative mutations) "
       "PASS")
    audit_source_template()
    audit_working_template_and_maps()
    results = audit_blocks()
    audit_spec_contract()

    print("-" * 72)
    print("BANG REGION NGANH PLII_M02:")
    print("  %-24s %-9s %s" % ("region", "TRANG THAI", "evidence"))
    for occ_id, st, ev in results:
        print("  %-24s %-9s %s" % (occ_id, st, ev))

    done = sum(1 for _o, s, _e in results if s == "DONE")
    missing = sum(1 for _o, s, _e in results if s == "MISSING")
    print("-" * 72)
    print("Tong: %d DONE / %d MISSING / %d tong so region ngang"
          % (done, missing, len(results)))
    # [P2 pin sync 2026-09-03] sau rebuild P2, mẫu có 6 w:tbl thật: 4 bảng
    # ngành + 2 lưới thành viên hộ gia đình (tv_hgd_sau_thay_doi B069,
    # tv_hgd_cap_doi B122); band/thuế được classify_table loại riêng.
    print("Cau tra loi Lead: template CO 6 vung ngu nghia = 4 vung nganh "
          "(bo_sung/xoa_bo/sua_doi_chi_tiet/hien_tai=Muc C.3, loop %s tu "
          "Wave 2C) + 2 luoi thanh vien ho gia dinh tv_hgd_sau_thay_doi/"
          "tv_hgd_cap_doi rebuild boi lane P2." % LOOP_CARRIER_HIEN_TAI)
    if _problems:
        print("VERIFY: FAIL — %d mâu thuẫn:" % len(_problems))
        for p in _problems:
            print(" -", p)
        return 1
    print("VERIFY: PASS — spec/template/blocks/form_maps nhất quán "
          "(MISSING la hien trang pre-integration da biet).")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
