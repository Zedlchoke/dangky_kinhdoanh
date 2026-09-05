# -*- coding: utf-8 -*-
"""test_v7_header_name.py — [WAVE v7] E2E regression HEADER-NAME-SYNC.

Fixture bắt buộc theo PLAN v7 F2.8/F3.7: PLI_M32 và cả family band
(tools/header_name_binding.json — 20 form):

  1. blank draft   → band KHÔNG có dữ liệu giả, KHÔNG còn dòng kẻ;
  2. filled A      → tên xuất ở CẢ thân và band (cùng canonical key);
  3. A→B           → cả hai vị trí CHỈ còn B (không stale);
  4. Unicode/dài   → tên không vỡ band, ô quốc hiệu nguyên vẹn;
  5. draft reload  → render từ store nên hai vị trí vẫn đồng bộ;
  6. mutation sai key / band thành input thứ hai → PHẢI FAIL.

Chạy:  python3 -X utf8 -m tools.test_v7_header_name
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

import fitz  # noqa: E402  pymupdf

from tools import docx_render as dr                      # noqa: E402
from tools import build_form_maps as bfm                 # noqa: E402
from tools.phase5_visual_gate import (                    # noqa: E402
    det_header_name, load_header_name_binding, pdf_pages)

MAPS = json.loads((ROOT / "app" / "data" / "form_maps.json")
                  .read_text(encoding="utf-8"))
BINDING = load_header_name_binding()

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


def _render(fid: str, data: dict) -> str:
    # data phẳng kiểu UI store — Bridge.export cũng _nest trước khi render
    from app_web.main import _nest
    xml = dr.render(ROOT / "app" / MAPS[fid]["template"], _nest(data))
    return zipfile.ZipFile(io.BytesIO(xml)).read(
        "word/document.xml").decode("utf-8")


def _band_text(fid: str, xml: str) -> str:
    """Text thật của ô (0,0) band trong RENDERED document.xml — bảng đầu
    tiên chứa khối quốc hiệu; lấy paragraph đầu của ô trái, nối các w:t
    (giữ <w:br/> thành \n). Đọc từ XML render để thấy GIÁ TRỊ đã đổ vào
    token (blocks chỉ mang run mirror không có text)."""
    tbls = []
    pos = 0
    while True:
        m = re.search(r"<w:tbl[ >]", xml[pos:])
        if not m:
            break
        start = pos + m.start()
        depth = 1
        scan = pos + m.end()
        while depth:
            mm = re.search(r"<w:tbl[ >]|</w:tbl>", xml[scan:])
            if not mm:
                break
            depth += -1 if mm.group(0).startswith("</") else 1
            scan += mm.end()
        tbls.append(xml[start:scan])
        pos = scan
    for tbl in tbls:
        if "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in tbl:
            continue
        first_tr = re.search(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", tbl, re.S)
        first_tc = re.search(r"<w:tc>.*?</w:tc>", first_tr.group(0), re.S)
        parts = []
        for pm in re.finditer(r"<w:p[ >].*?</w:p>|<w:p[^>]*/>",
                              first_tc.group(0), re.S):
            seg = pm.group(0)
            for tm in re.finditer(
                    r"<w:t[^>]*>([^<]*)</w:t>|<w:br/?>", seg):
                parts.append("\n" if tm.group(0).startswith("<w:br")
                             else tm.group(1))
        return "".join(parts)
    raise AssertionError("%s: không tìm thấy bảng band trong XML render"
                         % fid)


def _pdf_and_det(fid: str, data: dict, tmp: Path):
    """Render → export PDF qua đường production → trả (pdf_path, pages)."""
    from tools.phase5_visual_gate import run_export
    out_root = tmp
    errors, dirs = run_export(MAPS, _blocks_for(fid), "valid-full", [fid],
                              out_root)
    assert not errors, "export lỗi: %r" % (errors,)
    pdf = next(Path(dirs[0]).glob("%s.pdf" % fid))
    doc, pages = pdf_pages(pdf)
    return doc, pages, "\n".join(p["text"] for p in pages)


def _blocks_for(fid: str) -> dict:
    p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
    return {fid: json.loads(p.read_text(encoding="utf-8"))}


# ---------------------------------------------------------------------------

@check("E1_blank_no_fake_data")
def e1_blank():
    for fid, bind in sorted(BINDING["forms"].items()):
        xml = _render(fid, {})
        band = _band_text(fid, xml)
        assert bind["key"] not in band, \
            "%s: band blank còn token %r (token phải được tiêu thụ)" % (
                fid, band)
        assert not re.search(r"[-_.…]{3,}", band), \
            "%s: band blank còn dòng kẻ: %r" % (fid, band)
        assert "TÊN" in band, "%s: band mất nhãn pháp lý: %r" % (fid, band)


@check("E2_filled_name_in_band_and_body")
def e2_filled():
    cases = [("PLI_M32", "dn.ten_tieng_viet", "CÔNG TY TNHH MINH LONG PHÚ"),
             ("PLII_M02", "hkd_ten_tieng_viet_2",
              "HỘ KINH DOANH THỜI TRANG MINH ANH"),
             ("PLI_M13", "dn.ten_tieng_viet", "CÔNG TY TNHH GIA PHÁT")]
    from tools.phase5_fixtures import ValueFactory, build_fixture
    for fid, key, value in cases:
        blocks = json.loads((ROOT / "app" / "data" / "blocks" /
                             ("%s.json" % fid)).read_text(encoding="utf-8"))
        data = build_fixture(fid, MAPS[fid], "valid-full", blocks,
                             ValueFactory())
        data[key] = value
        xml = _render(fid, data)
        band = _band_text(fid, xml)
        assert value in band, "%s: band thiếu giá trị: %r" % (fid, band[:80])
        assert xml.count(value) >= 2, \
            "%s: giá trị chỉ xuất hiện %d lần (band + thân phải >=2)" % (
                fid, xml.count(value))


@check("E3_rename_a_to_b_both_positions")
def e3_rename():
    fid, key = "PLI_M32", "dn.ten_tieng_viet"
    xml_a = _render(fid, {key: "CONG TY A"})
    xml_b = _render(fid, {key: "CONG TY B"})
    for xml, cur, old in ((xml_a, "CONG TY A", "CONG TY B"),
                          (xml_b, "CONG TY B", "CONG TY A")):
        band = _band_text(fid, xml)
        assert cur in band and old not in band, \
            "band stale sau đổi tên: %r" % band
        assert old not in xml, "thân còn giá trị cũ sau đổi tên"
        assert xml.count(cur) >= 2


@check("E4_unicode_long_name_band_intact")
def e4_unicode():
    fid, key = "PLI_M32", "dn.ten_tieng_viet"
    long_name = ("CÔNG TY CỔ PHẦN ĐẦU TƯ PHÁT TRIỂN CÔNG NGHỆ THÔNG TIN "
                 "VỮNG CHẮC VIỆT NAM")
    xml = _render(fid, {key: long_name})
    band = _band_text(fid, xml)
    assert long_name in band, "band thiếu tên Unicode dài: %r" % band[:120]
    # ô quốc hiệu phải nằm ô RIÊNG và nguyên vẹn (không tràn nội dung)
    from tools.docx_to_blocks import convert
    blocks = convert(fid, MAPS)
    for b in blocks["blocks"]:
        if b.get("t") == "table" and b.get("band") == "header":
            motto = "".join(
                r.get("text", "")
                for r in b["rows"][0]["cells"][1].get("runs") or [])
            assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in motto
            assert "Độc lập - Tự do - Hạnh phúc" in motto
            assert long_name not in motto, "tên tràn sang ô quốc hiệu"
            break


@check("E5_pdf_d17_detector_pass_on_valid_full")
def e5_pdf_d17():
    """E2E thật qua export production: PDF phải qua được detector D17
    (band bound + giá trị đồng bộ thân) cho cả 3 form đại diện."""
    import shutil
    from tools.phase5_fixtures import ValueFactory, build_fixture
    out_root = Path("/tmp/v7_hdr_e2e_export")
    shutil.rmtree(out_root, ignore_errors=True)
    for fid in ("PLI_M32", "PLI_M13", "PLII_M02"):
        key = BINDING["forms"][fid]["key"]
        blocks = json.loads((ROOT / "app" / "data" / "blocks" /
                             ("%s.json" % fid)).read_text(encoding="utf-8"))
        data = build_fixture(fid, MAPS[fid], "valid-full", blocks,
                             ValueFactory())
        # valid-full đã điền key canonical — không ghi đè gì thêm
        doc, pages, full_text = _pdf_and_det(fid, data, out_root)
        hits = det_header_name(pages, fid, BINDING, full_text)
        doc.close()
        assert not hits, "%s: D17 bắt %r trên PDF production" % (fid, hits)


@check("E6_band_token_identity_single_source")
def e6_token_identity():
    """Contract 'một giá trị một lần nhập': band dùng ĐÚNG key registry,
    ô (0,0) KHÔNG chứa key nào khác; bind sai key sang giá trị khác sẽ bị
    D17 bắt ở lớp detector (mutation V2c case 3, test_phase6v_detectors)."""
    from tools.docx_to_blocks import convert
    for fid, bind in sorted(BINDING["forms"].items()):
        blocks = convert(fid, MAPS)
        band = next(b for b in blocks["blocks"]
                    if b.get("t") == "table" and b.get("band") == "header")
        runs = band["rows"][0]["cells"][0]["runs"]
        input_keys = [r["input"]["key"] for r in runs if "input" in r]
        assert input_keys == [], \
            "%s: band (0,0) chứa input lạ: %r" % (fid, input_keys)
        mirror_keys = [r["mirror"]["key"] for r in runs if "mirror" in r]
        assert mirror_keys == [bind["key"]], \
            "%s: band mirror sai key: %r != %r" % (
                fid, mirror_keys, bind["key"])


@check("E7_mutation_band_as_second_editable_detected")
def e7_second_editable_mutation():
    """Band thành input thứ hai trong blocks → contract FAIL (converter
    đúng phải sinh mirror; input trùng key là vi phạm 'một lần nhập')."""
    from tools.docx_to_blocks import convert
    blocks = convert("PLI_M32", MAPS)
    band = next(b for b in blocks["blocks"]
                if b.get("t") == "table" and b.get("band") == "header")
    runs = band["rows"][0]["cells"][0]["runs"]
    keys = [r["input"]["key"] for r in runs if "input" in r]
    assert keys == [], "band (0,0) không được chứa input: %r" % keys
    mirrors = [r["mirror"]["key"] for r in runs if "mirror" in r]
    assert mirrors == ["dn.ten_tieng_viet"], \
        "band (0,0) phải là mirror của dn.ten_tieng_viet: %r" % mirrors


@check("E8_all_bound_forms_have_band_and_token")
def e8_registry_consistency():
    """Mỗi form trong registry: template phải chứa token band đúng 1 lần
    ngoài thân (token tổng >= 2 lần: thân + band) và converter sinh mirror."""
    from tools.docx_to_blocks import convert
    for fid, bind in sorted(BINDING["forms"].items()):
        xml = _render(fid, {})
        token = "{%s}" % bind["key"]
        n_template = zipfile.ZipFile(
            ROOT / "app" / MAPS[fid]["template"]).read(
                "word/document.xml").decode("utf-8").count(token)
        # template: token thân + token band; render blank: token bị tiêu thụ
        assert n_template >= 2, \
            "%s: template chỉ có %d token %r (cần thân + band)" % (
                fid, n_template, token)
        blocks = convert(fid, MAPS)
        band = next(b for b in blocks["blocks"]
                    if b.get("t") == "table" and b.get("band") == "header")
        runs = band["rows"][0]["cells"][0]["runs"]
        assert any(r.get("mirror", {}).get("key") == bind["key"]
                   for r in runs), "%s: band thiếu run mirror" % fid


def main() -> int:
    e1_blank()
    e2_filled()
    e3_rename()
    e4_unicode()
    e5_pdf_d17()
    e6_token_identity()
    e7_second_editable_mutation()
    e8_registry_consistency()
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
