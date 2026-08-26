# -*- coding: utf-8 -*-
"""P1-B verify PLI_M72: bang chung may tinh cho 5 occurrence luoi nganh.

Khoi luong contract P1 (Lead chot): entry spec duoc them "occurrences"
= [{occurrence_id, match_heading, nth, sync_group?, end_markers?}];
Vung = tu heading khop lan thu nth den end_marker ke tiep;
semantic_key cua loop = occurrence_id.

Script nay KHONG sua gi — chi doc va in bang chung (evidence) theo tung
occurrence tren HAI file:
  1. Nguon generator: 05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_*.docx
     (file ma tools/build_form_maps.py thuc su doc khi regenerate).
  2. Ban sao production: app/templates/PLI_M72.docx
     (da qua Wave 2B rebuild: vung DNTN co 1 w:tbl that loop ds_nganh).

Moi occurrence in ra:
  - vi tri heading chinh xac (chi so paragraph body walk python-docx),
    van ban goc repr, in dam hay khong, marker loai hinh phan truoc;
  - cac paragraph tan du tieu de cot trong vung (STT/Ten nganh/Ma nganh/
    Nganh chinh);
  - end marker tim thay (muc '6.'), text goc + regex nao khop;
  - doi chieu voi khai bao trong tools/form_specs/change/PLI_M72.json.

Lu y tra cuu: manifest T0 ghi anchor '~#p1648,p1673,p1710,p1745,p1776'
la uoc luong tay khong resolve duoc bang may (xem build_manifest.py ghi chu
'anchor viet tat khong resolve duoc'). Chi so dung bang may duoc in o day.

Exit code 0 = moi check PASS, 1 = co FAIL. Khong ghi file.

Chay:  python -X utf8 tools/census/p1_b_verify_m72.py
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
from docx.oxml.ns import qn                  # noqa: E402
from docx.text.paragraph import Paragraph    # noqa: E402

SPEC_PATH = ROOT / "tools" / "form_specs" / "change" / "PLI_M72.json"
SOURCE_GLOB = "05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_*.docx"
TEMPLATE_PATH = ROOT / "app" / "templates" / "PLI_M72.docx"

EXPECTED_IDS = ["ds_nganh_dntn", "ds_nganh_tnhh_1tv", "ds_nganh_tnhh_2tv",
                "ds_nganh_ctcp", "ds_nganh_dhdn"]
# Tieu de cot tan du ky vong TRONG VUNG, phan theo loai file:
# - nguon: vung 1 con du 4 tieu de cot (ke ca 'Nganh chinh'), vung 2-5 mat cot 4;
# - template: vung 1 da duoc Wave 2B rebuild thanh w:tbl that -> khong con
#   paragraph tan du nao; vung 2-5 van giu nguyen 3 paragraph nhu nguon.
EXPECTED_REMNANTS = {
    "nguon": {
        "ds_nganh_dntn": ["stt", "ten nganh", "ma nganh",
                          "nganh, nghe kinh doanh chinh"],
        "ds_nganh_tnhh_1tv": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_tnhh_2tv": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_ctcp": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_dhdn": ["stt", "ten nganh", "ma nganh"],
    },
    "template": {
        "ds_nganh_dntn": [],
        "ds_nganh_tnhh_1tv": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_tnhh_2tv": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_ctcp": ["stt", "ten nganh", "ma nganh"],
        "ds_nganh_dhdn": ["stt", "ten nganh", "ma nganh"],
    },
}

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


@check("spec JSON: load duoc, dung 5 occurrence theo contract P1")
def t_spec_contract():
    raw = SPEC_PATH.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    entries = data.get("tables") or []
    assert len(entries) == 1, "ky vong 1 table entry, thay %d" % len(entries)
    occs = entries[0].get("occurrences") or []
    assert [o["occurrence_id"] for o in occs] == EXPECTED_IDS, \
        "occurrence_id sai thu tu/sai ten: %s" % [o.get("occurrence_id")
                                                  for o in occs]
    for k, o in enumerate(occs, 1):
        assert o["nth"] == k, "%s: nth=%r != %d" % (o["occurrence_id"], o["nth"], k)
        assert o["match_heading"].strip() == "5. Ngành, nghề kinh doanh", \
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


def source_path() -> Path:
    hits = sorted(ROOT.glob(SOURCE_GLOB))
    assert hits, "khong tim thay file nguon %s" % SOURCE_GLOB
    return hits[0]


@check("file NGUON: 5 vung dung anchor/end marker/tan du nhu evidence P1-B")
def t_source_regions():
    occs = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))["tables"][0][
        "occurrences"]
    path = source_path()
    doc = Document(str(path))
    assert not top_level_tables(doc), \
        "file nguon khong duoc co w:tbl top-level (moi luoi deu la paragraph roi)"
    regions = verify_file("NGUON", path, occs, EXPECTED_REMNANTS["nguon"])
    expect = {"ds_nganh_dntn": (13, 22), "ds_nganh_tnhh_1tv": (42, 52),
              "ds_nganh_tnhh_2tv": (85, 95), "ds_nganh_ctcp": (134, 141),
              "ds_nganh_dhdn": (168, 175)}
    assert regions == expect, \
        "anchor/end NGUON %s != evidence da khoa %s" % (regions, expect)


@check("ban sao TEMPLATE: cung 5 vung; vung 1 co w:tbl Wave 2B loop ds_nganh")
def t_template_regions():
    occs = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))["tables"][0][
        "occurrences"]
    regions = verify_file("TEMPLATE", TEMPLATE_PATH, occs, EXPECTED_REMNANTS["template"])
    expect = {"ds_nganh_dntn": (13, 19), "ds_nganh_tnhh_1tv": (39, 49),
              "ds_nganh_tnhh_2tv": (82, 92), "ds_nganh_ctcp": (131, 138),
              "ds_nganh_dhdn": (165, 172)}
    assert regions == expect, \
        "anchor/end TEMPLATE %s != evidence da khoa %s" % (regions, expect)
    # vung DNTN: dung 1 bang that da rebuild (loop ds_nganh) ngay sau heading
    doc = Document(str(TEMPLATE_PATH))
    paras = body_paragraphs(doc)
    blocks = list(doc.element.body.iterchildren())
    a, e = regions["ds_nganh_dntn"]
    inside = [b for b in blocks[a:e + 1] if b.tag == qn("w:tbl")]
    assert len(inside) == 1, \
        "vung DNTN template phai co dung 1 w:tbl Wave 2B, thay %d" % len(inside)
    xml = inside[0].xml
    assert "{#ds_nganh}" in xml and "{/ds_nganh}" in xml and "{_stt}" in xml, \
        "bang Wave 2B vung DNTN thieu the loop ds_nganh/{_stt}"
    # 4 vung con lai CHUA duoc rebuild (chua co w:tbl) - day la khoang trong P1
    for oid in EXPECTED_IDS[1:]:
        a, e = regions[oid]
        n_tbl = sum(1 for b in blocks[a:e + 1] if b.tag == qn("w:tbl"))
        assert n_tbl == 0, "%s: vung template da co %d w:tbl?" % (oid, n_tbl)


def main() -> int:
    print("p1_b_verify_m72 — bang chung 5 occurrence luoi nganh PLI_M72")
    t_spec_contract()
    t_source_regions()
    t_template_regions()
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
    print("may). Chi so dung bang may: NGUON 13/42/85/134/168, TEMPLATE")
    print("13/39/82/131/165 — dung lam anchor that cho generator.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
