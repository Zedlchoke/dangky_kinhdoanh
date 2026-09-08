# -*- coding: utf-8 -*-
"""test_f3h_fixtures.py — [F3H 2026-09-08] fixture phân biệt bắt buộc + E2E
mirror theo chỉ thị owner docs/f3h_f3t_directive_2026-09-08.md mục 2:

  F1  registry roles khớp census 1:1 (21 mirror + 2 band_input + 45
      output_mirror + 19 no_band) và khớp nội bộ forms/output_mirrors;
  F2  converter role-aware: band chỉ bind khi role band-required; band_input
      giữ input; 10 form output_mirrors có run mirror READ-ONLY;
  F3  FIXTURE PLI_M31: band + fill-line NGAY DƯỚI nhãn pháp định (giữ nhãn +
      điền tên; bản rỗng còn fill-line);
  F4  FIXTURE PLI_M72: KHÔNG band — mutation tự thêm band phải ĐỎ
      (BAND_FORBIDDEN_PRESENT);
  F5  PLI_M32 mirror A→B E2E: viết tên ở thân → band đổi → PDF khớp.

Chạy:  python3 -X utf8 -m tools.test_f3h_fixtures
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import docx_render as dr                       # noqa: E402
from tools import header_semantics as hs                  # noqa: E402
from tools.phase5_visual_gate import (                    # noqa: E402
    det_header_name, load_header_name_binding, pdf_pages)

MAPS = json.loads((ROOT / "app" / "data" / "form_maps.json")
                  .read_text(encoding="utf-8"))
MAPS = {k: v for k, v in MAPS.items()
        if re.match(r"^PL[IX]+_M\d+$", k)}          # bỏ key metadata
BINDING = load_header_name_binding()
ROLES = {k: v for k, v in BINDING["roles"].items() if k != "comment"}
OUTPUT_MIRRORS = {k: v for k, v in BINDING["output_mirrors"].items()
                  if k != "comment"}
CENSUS = json.loads((ROOT / "docs" / "audits" / "header_semantic_census.json")
                    .read_text(encoding="utf-8"))


def _xml_text(xml: str) -> str:
    """Text nhìn thấy của document.xml (nối w:t, giữ <w:br/> thành \n)."""
    parts = []
    for m in re.finditer(r"<w:t[^>]*>([^<]*)</w:t>|<w:br/?>", xml):
        parts.append("\n" if m.group(0).startswith("<w:br")
                     else m.group(1))
    return "".join(parts)


def _norm(text: str) -> str:
    """Chuẩn hoá whitespace để match giá trị bị PDF/Word wrap."""
    return re.sub(r"\s+", " ", text)

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                import traceback
                traceback.print_exc()
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def _blocks(fid: str) -> dict:
    return json.loads((ROOT / "app" / "data" / "blocks" / (
        "%s.json" % fid)).read_text(encoding="utf-8"))


def _nest(data: dict) -> dict:
    from app_web.main import _nest
    return _nest(data)


def _render(fid: str, data: dict) -> str:
    xml = dr.render(ROOT / "app" / MAPS[fid]["template"], _nest(data))
    return zipfile.ZipFile(io.BytesIO(xml)).read(
        "word/document.xml").decode("utf-8")


def _export(fid: str, data: dict, tmp: Path, case: str):
    """Export 1 form qua đường production (Bridge.export) -> (pdf, pages)."""
    from app_web.main import Bridge
    bridge = Bridge()
    payload = {"case_id": "f3h_%s_%s" % (fid.lower(), case),
               "format": "both",
               "forms": [{"id": fid}], "data": dict(data)}
    r = bridge.export(payload)
    assert not r.get("errors"), "export lỗi: %r" % (r.get("errors"),)
    out = Path(r["dir"])
    pdf = out / ("%s.pdf" % fid)
    assert pdf.exists(), "thiếu PDF: %s" % pdf
    doc, pages = pdf_pages(pdf)
    return doc, pages, out


def _valid_full(fid: str) -> dict:
    from tools.phase5_fixtures import ValueFactory, build_fixture
    return build_fixture(fid, MAPS[fid], "valid-full", _blocks(fid),
                         ValueFactory())


# ---------------------------------------------------------------------------
# F1 — registry roles ↔ census ↔ forms/output_mirrors
# ---------------------------------------------------------------------------

@check("F1_roles_registry_matches_census")
def f1_roles():
    roles = ROLES
    cen = CENSUS["forms"]
    assert set(roles) == set(cen), \
        "roles phải khớp census 87 form; lệch: %r" % (
            set(roles) ^ set(cen))
    from collections import Counter
    got = Counter(e["role"] for e in roles.values())
    pin = CENSUS["summary"]["role_counts"]
    assert got["required_band_mirror"] == pin["required_band_mirror"] == 21
    assert got["required_band_input"] == pin["required_band_input"] == 2
    assert got["output_mirror"] == pin["output_mirror"] == 45
    assert got["no_subject_band"] == pin["no_subject_band"] == 19
    for fid, e in roles.items():
        assert e["role"] == cen[fid]["form_role"], fid
        assert e["subject_kind"] == cen[fid]["subject_kind"], fid
        assert e["canonical_key"] == cen[fid]["canonical_key"], \
            "%s: canonical key lệch census" % fid
    # mọi form trong form_maps phải có role (census phủ 87/87)
    missing = sorted(set(MAPS) - set(roles))
    assert not missing, "form thiếu role: %r" % missing
    # nhất quán nội bộ: forms registry ⊆ band-required; output_mirrors ⊆
    # output_mirror; band-required phủ đủ forms registry
    band_roles = {"required_band_mirror", "required_band_input"}
    for fid, bind in BINDING["forms"].items():
        assert roles[fid]["role"] in band_roles, \
            "%s có entry forms nhưng role không band-required" % fid
        assert bind["key"] == roles[fid]["canonical_key"], fid
    for fid, e in OUTPUT_MIRRORS.items():
        assert roles[fid]["role"] == "output_mirror", \
            "%s trong output_mirrors nhưng role=%r" % (fid, roles[fid]["role"])
        assert e["key"] == roles[fid]["canonical_key"], fid
    # 7 form F3H mới phải nằm output_mirrors
    for fid in ("PLI_M47", "PLI_M50", "PLI_M51", "PLI_M53", "PLI_M71",
                "PLI_M76", "PLII_M26"):
        assert fid in BINDING["output_mirrors"], fid


# ---------------------------------------------------------------------------
# F2 — converter role-aware trên blocks thật
# ---------------------------------------------------------------------------

@check("F2_converter_role_aware_blocks")
def f2_converter():
    from tools.docx_to_blocks import convert
    roles = ROLES
    for fid, e in sorted(roles.items()):
        blocks = convert(fid, MAPS)
        band = [b for b in blocks["blocks"]
                if b.get("t") == "table" and b.get("band") == "header"]
        subj_inputs, subj_mirrors = [], []
        for blk in blocks["blocks"]:
            runs = []
            if blk.get("t") == "p":
                runs = blk.get("runs") or []
            elif blk.get("t") == "table":
                for row in blk.get("rows") or []:
                    for cell in row.get("cells") or []:
                        runs += cell.get("runs") or []
            for r in runs:
                if r.get("input", {}).get("key") == e["canonical_key"]:
                    subj_inputs.append(r)
                if r.get("mirror", {}).get("key") == e["canonical_key"]:
                    subj_mirrors.append(r)
        if e["role"] in ("required_band_mirror", "required_band_input"):
            assert band, "%s: thiếu band table" % fid
        else:
            assert not band, "%s: role %s không được có band" % (
                fid, e["role"])
        if e["role"] == "required_band_input":
            # band LÀ ô nhập duy nhất: input tại band, không mirror tại band
            cell_runs = band[0]["rows"][0]["cells"][0]["runs"]
            assert any(r.get("input", {}).get("key") == e["canonical_key"]
                       for r in cell_runs), "%s: band thiếu input" % fid
            assert not any("mirror" in r for r in cell_runs), \
                "%s: band_input không được mirror" % fid
        elif e["role"] == "required_band_mirror":
            cell_runs = band[0]["rows"][0]["cells"][0]["runs"]
            assert any(r.get("mirror", {}).get("key") == e["canonical_key"]
                       for r in cell_runs), "%s: band thiếu mirror" % fid
            assert not any("input" in r for r in cell_runs), \
                "%s: band mirror không được chứa input" % fid
        # output_mirror: occurrence chủ thể phải là mirror READ-ONLY
        # (hoặc chưa bind — form ngoài output_mirrors giữ hiện trạng F1)
        if e["role"] == "output_mirror" and fid in OUTPUT_MIRRORS:
            assert subj_mirrors, "%s: thiếu run mirror chủ thể" % fid
            assert not subj_inputs, \
                "%s: occurrence output phải read-only, thấy input: %r" % (
                    fid, subj_inputs)


# ---------------------------------------------------------------------------
# F3 — FIXTURE PLI_M31: band + fill-line dưới nhãn pháp định
# ---------------------------------------------------------------------------

@check("F3_fixture_pli_m31_band_with_fill_line")
def f3_m31():
    fid, key = "PLI_M31", "dn.ten_tieng_viet"
    # (a) bản rỗng: nhãn pháp định + fill-line còn nhìn thấy (không dash,
    #     không token kỹ thuật) ở CẢ band lẫn thân
    xml = _render(fid, {})
    txt = _xml_text(xml)
    assert key not in xml, "band blank còn token"
    assert "TÊN DOANH NGHIỆP" in txt, "band mất nhãn pháp định"
    assert "Tên doanh nghiệp (ghi bằng chữ in hoa):" in _norm(txt), \
        "thân mất nhãn + fill-line"
    # (b) valid-full E2E: giá trị đổ ở CẢ band (dưới nhãn) lẫn thân
    data = _valid_full(fid)
    value = data[key]
    assert value, "valid-full phải có giá trị tên"
    doc, pages, out = _export(fid, data, Path("/tmp/f3h_fixtures"), "full")
    try:
        raw = "\n".join(p["text"] for p in pages)
        text = _norm(raw)
        assert value in text, "PDF không có giá trị tên"
        # band: nhãn trang 1, giá trị nằm dưới nhãn trong cùng cột
        first = raw.split("\n")
        li = next(i for i, ln in enumerate(first)
                  if hs._squeeze(ln) == "ten doanh nghiep")
        assert value in _norm("\n".join(first[li:li + 4])), \
            "giá trị band không nằm dưới nhãn: %r" % first[li:li + 4]
        # thân: nhãn pháp định + giá trị cùng dòng
        assert re.search(r"Tên doanh nghiệp \(ghi bằng chữ in hoa\):\s*%s"
                         % re.escape(value), text), \
            "thân mất 'nhãn: giá trị'"
        # detector: D19 + D17 đều sạch trên PDF production
        hits = hs.det_pdf(pages, fid, data, text, BINDING)
        assert not hits, "D19 bắt trên M31 hợp lệ: %r" % hits
        assert not det_header_name(pages, fid, BINDING, text), \
            "D17 bắt trên M31 hợp lệ"
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# F4 — FIXTURE PLI_M72: KHÔNG band, cấm tự thêm
# ---------------------------------------------------------------------------

@check("F4_fixture_pli_m72_no_band_ever")
def f4_m72():
    fid, key = "PLI_M72", "dn.ten_tieng_viet"
    # (a) template/blocks thật: không band chủ thể + subtitle pháp định nguyên
    b = _blocks(fid)
    assert not [x for x in b["blocks"]
                if x.get("t") == "table" and x.get("band") == "header"], \
        "M72 template không được có band chủ thể"
    assert hs.det_structural(fid, b) == []
    # subtitle pháp định nằm trong TEMPLATE (render rỗng bỏ section điều kiện
    # vì không biến thể nào truthy — engine chỉ xuất biến thể được chọn)
    tpl_xml = zipfile.ZipFile(
        ROOT / "app" / MAPS[fid]["template"]).read(
            "word/document.xml").decode("utf-8")
    assert "TÊN DOANH NGHIỆP TƯ NHÂN" in _xml_text(tpl_xml), \
        "subtitle pháp định bị mất khỏi template"
    # (b) E2E valid-full (biến thể DNTN): '1. Tên doanh nghiệp' là section
    #     output — giá trị nằm ở thân, KHÔNG có band mirror
    data = _valid_full(fid)
    data["dn.loai_hinh"] = "DNTN"
    data["loai_hinh_dntn"] = "X"
    doc, pages, out = _export(fid, data, Path("/tmp/f3h_fixtures"), "full")
    try:
        text = _norm("\n".join(p["text"] for p in pages))
        assert data[key] in text, "M72 PDF thiếu tên công bố"
        # D19 pdf layer bỏ qua form không band-required
        assert hs.det_pdf(pages, fid, data, text, BINDING) == []
    finally:
        doc.close()
    # (c) MUTATION tự thêm band phải ĐỎ (detector chặn ngay ở structural)
    mutated = json.loads(json.dumps(b, ensure_ascii=False))
    mutated["blocks"].insert(0, {
        "t": "table", "band": "header", "widths": None, "rows": [
            {"cells": [
                {"runs": [{"text": "TÊN DOANH NGHIỆP\n", "b": True},
                          {"mirror": {"key": key}}]},
                {"runs": [{"text": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"}]}]}]})
    hits = hs.det_structural(fid, mutated)
    assert [h["code"] for h in hits] == ["BAND_FORBIDDEN_PRESENT"], hits


# ---------------------------------------------------------------------------
# F5 — PLI_M32 mirror A→B E2E: thân đổi → band đổi → PDF khớp
# ---------------------------------------------------------------------------

@check("F5_pli_m32_mirror_a_to_b_e2e")
def f5_m32():
    fid, key = "PLI_M32", "dn.ten_tieng_viet"
    data = _valid_full(fid)
    name_a = "CÔNG TY TNHH MỘT THÀNH VIÊN AN PHÁT A"
    name_b = "CÔNG TY CP ĐẦU TƯ MINH TRÍ B"
    for case, cur, old in (("a", name_a, name_b), ("b", name_b, name_a)):
        data[key] = cur
        doc, pages, out = _export(fid, data, Path("/tmp/f3h_fixtures"), case)
        try:
            text = _norm("\n".join(p["text"] for p in pages))
            assert cur in text and old not in text, \
                "%s: PDF còn giá trị cũ/stale" % case
            # band + thân đồng bộ: giá trị xuất hiện >= 2 lần (band + thân)
            assert text.count(cur) >= 2, \
                "%s: giá trị chỉ %d lần (band + thân phải >=2)" % (
                    case, text.count(cur))
            hits = hs.det_pdf(pages, fid, data, text, BINDING)
            assert not hits, "%s: D19 bắt: %r" % (case, hits)
            assert not det_header_name(pages, fid, BINDING, text), \
                "%s: D17 bắt: %r" % (case, det_header_name(
                    pages, fid, BINDING, text))
        finally:
            doc.close()


def main() -> int:
    f1_roles()
    f2_converter()
    f3_m31()
    f4_m72()
    f5_m32()
    print("-" * 60)
    passed = sum(1 for ok, _ in _results if ok)
    failed = sum(1 for ok, _ in _results if not ok)
    print("Tổng kết: %d PASS / %d FAIL / %d test" % (
        passed, failed, len(_results)))
    for ok, name in _results:
        if not ok:
            print(" -", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
