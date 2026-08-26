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
tools/form_specs/household/PLII_M02.json: đủ 4 occurrence_id ngữ nghĩa
(nganh_bo_sung, nganh_xoa_bo, nganh_sua_doi_chi_tiet, nganh_hien_tai),
match_heading khớp đúng nth lần trong template, end_markers tồn tại,
sync_group=null (PLAN mục A cấm auto-sync giữa các loop khác nghĩa).

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

# (occurrence_id, heading_folded_regex, end_markers, headers, loop_name)
REGIONS = [
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
        fail("loop lạ ngoài 4 semantic region: %r" % unknown)

    tbl_owner = []
    for i, (k, _v) in enumerate(seq):
        if k != "tbl":
            continue
        owner = next((oid for oid, h, e in spans if h < i < e), None)
        if owner is None:
            fail("w:tbl thứ %d nằm ngoài 4 vùng ngành" % i)
        else:
            tbl_owner.append(owner)
    declared = sorted(loop_to_occ[l] for l in fm_loops if l in loop_to_occ)
    if sorted(tbl_owner) != declared:
        fail("mất đồng bộ template<->form_maps: bảng ở %r vs khai báo %r"
             % (sorted(tbl_owner), declared))
    else:
        ok("mỗi dynamic_tables có đúng 1 bảng thật trong vùng tương ứng: %r"
           % declared)


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
    ok("đủ 4 occurrence_id ngữ nghĩa: %r" % sorted(seen))

    doc = Document(str(WORKING_TMPL))
    paras = [fold(re.sub(r"\s+", " ", Paragraph(child, doc).text)).strip()
             for child in doc.element.body.iterchildren()
             if child.tag == qn("w:p")]
    for oid, heading, ends, _hdrs, lp in REGIONS:
        occ = seen[oid]["occurrences"][0]
        if occ.get("match_heading") != heading:
            fail("%s: match_heading lệch chuẩn audit" % oid)
        if occ.get("nth") != 1:
            fail("%s: nth != 1" % oid)
        n_hit = sum(1 for t in paras if re.search(occ["match_heading"], t))
        if n_hit != occ.get("nth"):
            fail("%s: heading khớp %d lần != nth" % (oid, n_hit))
        for m in occ.get("end_markers") or []:
            if not any(re.search(m, t) for t in paras):
                fail("%s: end_marker %r không có trong template" % (oid, m))
        if seen[oid]["spec"].get("loop") != lp:
            fail("%s: entry spec.loop %r != %r" % (
                oid, seen[oid]["spec"].get("loop"), lp))
    if not _problems:
        ok("contract hợp lệ: heading/nth/end_markers/sync_group/loop khớp")


def main() -> int:
    print("P1-C VERIFY PLII_M02 — worktree %s" % ROOT)
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
    print("Cau tra loi Lead: template CO vung thu 4 (nganh_hien_tai) = bang "
          "nganh Muc C.3 cap doi/dang ky lai; day la w:tbl duy nhat cua mau "
          "sau rebuild, da co loop %s tu Wave 2C." % LOOP_CARRIER_HIEN_TAI)
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
