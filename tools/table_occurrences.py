# -*- coding: utf-8 -*-
"""Dinh vi OCCURRENCE (nhieu section cung tieu de) cho pipeline rebuild bang.

Contract P1 (Lead chot 2026-08-26): entry spec trong
tools/form_specs/<nhom>/<FORM_ID>.json duoc them truong tuy chon
"occurrences": danh sach object

    {"occurrence_id": "ds_nganh_dntn",
     "match_heading": "5. Nganh, nghe kinh doanh",
     "nth": 1,
     "sync_group": "ds_nganh_cong_bo",
     "end_markers": ["^\\\\d+\\\\.", "^Ghi chu"]}

Y nghia: quet body paragraph theo thu tu form; moi paragraph khop PREFIX
match_heading (so sanh da fold: thuong, bo dau, gom khoang trang) duoc danh
so lan xuat hien; occurrence thu nth chay tu heading den dong dau tien khop
mot end_marker. Neu thieu end_markers: ket thuc tai heading danh so
"\\d+." ke tiep hoac het than bai.

Boundary an toan (bai hoc PLI_M09): neu trong vung phat hien dau hieu nhiem
mau khac ("Mau so <so>" hoac heading lon khong thuoc vung: heading danh so
cap top-level arabic/roman) -> SKIP occurrence do + canh bao ra log; vung
bi SKIP KHONG duoc xoa paragraph tan du (khong nuot chuoi lang gieng).

Module nay THUAN function tren list text: khong import python-docx de de
unit test. build_form_maps.py truyen raw paragraph.text vao.
"""
from __future__ import annotations

import re
import unicodedata

# Heading danh so cap top-level: "5. ..." / "12.-" (khong khop "5.1 ..."
# vi sau dau cham la chu so). Can mot ky tu trang hoac ket thuoc dong sau cham.
NUMBERED_HEADING_RE = re.compile(r"^\d+\.(?!\d)(?:\s|$)")
# Heading la ma so la ma roman top-level: "I." "II." "IV." ... (da fold thuong).
ROMAN_HEADING_RE = re.compile(r"^(?:viii|vii|vi|iv|ix|iii|ii|x|v|i)\.(?!\w)")
# Dau hieu nhiem mau khac bat dau trong vung: "Mẫu số 07", "Mẫu số: 06a".
MAU_SO_RE = re.compile(r"^mau so[:\s]*\w+")
# occurrence_id phai la ten loop docxtemplater hop le ({#id}/{/id} va key draft).
OCC_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")

_STATUS_OK = "ok"
_STATUS_SKIPPED = "skipped"


def fold_text(text):
    """Thuong, bo dau, doi 'đ'->'d', gom khoang trang — dung de so sanh
    prefix match_heading va ap regex end_markers/contamination."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    out = out.replace("đ", "d")
    return re.sub(r"\s+", " ", out).strip()


def _default_log(msg):
    print("[occ-rebuild] %s" % msg)


def validate_occurrences(raw_list, existing_loop_names=(), form_id="?"):
    """Kiem tra + chuan hoa list "occurrences" trong 1 entry spec.

    Tra ve list config dict co khoa: occurrence_id, match_heading, nth,
    sync_group, end_markers. Raise ValueError voi spec sai de chan som
    (truoc khi sua document). Unknown key duoc bo qua (forward-compat).
    """
    seen = set()
    seen_eff = set()
    loop_names = set(existing_loop_names or ())
    out = []
    for i, raw in enumerate(raw_list or []):
        if not isinstance(raw, dict):
            raise ValueError(
                "%s: occurrences[%d] phai la object, nhan %r"
                % (form_id, i, type(raw).__name__))
        oid = raw.get("occurrence_id")
        if not isinstance(oid, str) or not OCC_ID_RE.match(oid):
            raise ValueError(
                "%s: occurrences[%d].occurrence_id khong hop le: %r "
                "(phai khop [A-Za-z0-9_]+)" % (form_id, i, oid))
        if oid in seen:
            raise ValueError(
                "%s: occurrence_id '%s' trung trong cung entry" % (form_id, oid))
        if oid in loop_names:
            raise ValueError(
                "%s: occurrence_id '%s' trung ten loop cua spec khac "
                "-> semantic_key phai duy nhat trong form" % (form_id, oid))
        heading = raw.get("match_heading")
        if not isinstance(heading, str) or not heading.strip():
            raise ValueError(
                "%s: occurrences[%d] (%s) thieu match_heading"
                % (form_id, i, oid))
        # match_heading la VAN BAN prefix (duoc fold 2 phia truoc khi so
        # sanh), KHONG PHAI regex -> chan som ky tu regex de tranh SKIP
        # nguoc doi (bai hoc PLII_M02 P1).
        if heading.strip().startswith("^") or "\\" in heading:
            raise ValueError(
                "%s: occurrences[%d] (%s) match_heading phai la van ban "
                "thuong (co giu dau, khong regex): %r"
                % (form_id, i, oid, heading))
        nth = raw.get("nth", 1)
        if not isinstance(nth, int) or isinstance(nth, bool) or nth < 1:
            raise ValueError(
                "%s: occurrences[%d] (%s) nth phai la so nguyen >= 1, nhan %r"
                % (form_id, i, oid, nth))
        end_markers = raw.get("end_markers") or []
        if not isinstance(end_markers, (list, tuple)) or \
                not all(isinstance(m, str) for m in end_markers):
            raise ValueError(
                "%s: occurrences[%d] (%s) end_markers phai la list regex str"
                % (form_id, i, oid))
        sync_group = raw.get("sync_group")
        if sync_group is not None and not isinstance(sync_group, str):
            raise ValueError(
                "%s: occurrences[%d] (%s) sync_group phai la string hoac null"
                % (form_id, i, oid))
        # Loop name tuyen minh (tuy chon): bao toan canonical key khi vung
        # du lieu do la danh dung chung (vd ds_nganh PLII_M02 vung C.3).
        loop = raw.get("loop")
        if loop is not None:
            if not isinstance(loop, str) or not OCC_ID_RE.match(loop):
                raise ValueError(
                    "%s: occurrences[%d] (%s) loop khong hop le: %r "
                    "(phai khop [A-Za-z0-9_]+)" % (form_id, i, oid, loop))
            if loop in seen_eff or (loop in loop_names and loop != oid):
                raise ValueError(
                    "%s: occurrence '%s' dat loop '%s' trung ten loop khac "
                    "-> semantic_key phai duy nhat trong form" % (
                        form_id, oid, loop))
        eff_loop = loop or oid
        if eff_loop in seen_eff or (eff_loop in loop_names and eff_loop != oid):
            raise ValueError(
                "%s: occurrence_id '%s' trung ten loop cua spec khac "
                "-> semantic_key phai duy nhat trong form" % (form_id, oid))
        seen_eff.add(eff_loop)
        seen.add(oid)
        out.append({
            "occurrence_id": oid,
            "match_heading": heading,
            "nth": nth,
            "sync_group": sync_group,
            "end_markers": list(end_markers),
            "loop": loop,
        })
    return out


def find_occurrence_head(paragraph_texts, match_heading, nth):
    """Chi so paragraph dau tien cua occurrence thu nth, hoac None.

    Tra ve (head_index|None, tong_so_lan_khop). Paragraph khop khi text DA
    FOLD bat dau bang match_heading DA FOLD (prefix match)."""
    needle = fold_text(match_heading)
    heads = [i for i, t in enumerate(paragraph_texts)
             if fold_text(t).startswith(needle)]
    if len(heads) < nth:
        return None, len(heads)
    return heads[nth - 1], len(heads)


def find_region_end(paragraph_texts, head, end_markers):
    """Chi so DONG KET THUC (exclusive-boundary line) cua vung sau heading.

    Co end_markers: dong dau tien sau head khop bat ky regex nao (re.search
    tren text da fold). Khong tim thay -> het than bai.
    Khong co end_markers: heading danh so "\\d+." ke tiep hoac het than bai.
    """
    n = len(paragraph_texts)
    if end_markers:
        # marker viet kieu du tieng trong JSON ("^Ghi chu") -> cung phai fold
        # de khop tren text da fold (regex meta ky tu giu nguyen).
        compiled = [re.compile(fold_text(m)) for m in end_markers]
        for j in range(head + 1, n):
            ft = fold_text(paragraph_texts[j])
            if any(rx.search(ft) for rx in compiled):
                return j
        return n
    for j in range(head + 1, n):
        if NUMBERED_HEADING_RE.match(fold_text(paragraph_texts[j])):
            return j
    return n


def scan_contamination(paragraph_texts, start, end):
    """Quet vung noi dung [start, end) tim dau hielnhiem mau khac.

    Tra ve None neu sach; ngược lại chuoi ly do ("...", dong <i>).
    Dau hieu: paragraph "Mau so <so>", heading danh so top-level arabic
    ("5. ...") hoac roman ("II. ...") khong phai dong ket thuc vung."""
    for i in range(max(0, start), min(end, len(paragraph_texts))):
        ft = fold_text(paragraph_texts[i])
        if MAU_SO_RE.match(ft):
            return "nhiem mau khac %r o dong %d" % (
                paragraph_texts[i].strip()[:80], i)
        if NUMBERED_HEADING_RE.match(ft) or ROMAN_HEADING_RE.match(ft):
            return "heading lon khong thuoc vung %r o dong %d" % (
                paragraph_texts[i].strip()[:80], i)
    return None


def resolve_regions(paragraph_texts, occurrences, log=None):
    """Giai quyet tung occurrence config thanh vung [head, end).

    Tra ve list dict theo thu tu input:
      {"cfg", "head", "start", "end", "status": "ok"|"skipped",
       "total_found", "reason"}
    Occurrence bi SKIP (thieu lan xuat hien / nhiem) van nam trong ket qua
    voi status="skipped" + ly do; caller KHONG duoc drop/chen vung skipped.
    """
    log = log or _default_log
    label = lambda lst: ",".join(  # noqa: E731
        c["occurrence_id"] for c in lst)
    regions = []
    for cfg in occurrences:
        oid = cfg["occurrence_id"]
        head, total = find_occurrence_head(
            paragraph_texts, cfg["match_heading"], cfg["nth"])
        if head is None:
            reason = ("tim thay %d heading khop %r, khong du lan thu %d"
                      % (total, cfg["match_heading"], cfg["nth"]))
            log("%s: SKIP (%s)" % (oid, reason))
            regions.append({"cfg": cfg, "head": None, "start": None,
                            "end": None, "status": _STATUS_SKIPPED,
                            "total_found": total, "reason": reason})
            continue
        end = find_region_end(paragraph_texts, head, cfg["end_markers"])
        problem = scan_contamination(paragraph_texts, head + 1, end)
        if problem:
            log("%s: SKIP vung [%d,%d) vi %s" % (oid, head, end, problem))
            regions.append({"cfg": cfg, "head": head, "start": head + 1,
                            "end": end, "status": _STATUS_SKIPPED,
                            "total_found": total, "reason": problem})
            continue
        log("%s: vung [%d,%d) (lan %d/%d, end=%s)" % (
            oid, head, end, cfg["nth"], total,
            "marker" if cfg["end_markers"] else
            "heading-so/het-than-bai"))
        regions.append({"cfg": cfg, "head": head, "start": head + 1,
                        "end": end, "status": _STATUS_OK,
                        "total_found": total, "reason": None})
    return regions
