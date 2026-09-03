# -*- coding: utf-8 -*-
"""test_phase5r_tables.py — Phase 5R Lane C (tables): census bảng rộng +
policy WLAY-008 + pin chất lượng bảng render + census matrix PLI_M12
(WLAY-005).

==== Phương pháp ====

C1 (census bảng >= 10 cột, 87 template):
  Quét word/document.xml của TỪNG app/templates/PL*.docx bằng phép đếm cân
  bằng <w:tbl>/<w:tr> (chịu bảng lồng — detector D9 của gate dùng regex
  `<w:tbl>.*?</w:tbl>` nên MÙ với tag `<w:tbl ...>` có attribute và với bảng
  lồng; census lane C KHÔNG kế thừa blind-spot đó, see detector_notes trong
  tools/phase5r_table_policies.json). Mỗi bảng ghi (form, table_index, số
  cột, tổng width, min col width). Kết quả bảng >= 10 cột được EMBED dạng
  fixture (WIDE_TABLE_FIXTURE) — regen làm trôi census sẽ làm test đỏ ngay.

C2 (pin chất lượng bảng ở render — mọi bảng, không chỉ rộng):
  docx_render._pin_table_quality phải, với mọi bảng trong body:
  (a) hàng tiêu đề thật (không phải band quốc hiệu) có w:tblHeader — heuristic
      band replicate is_header_band_table của docx_to_blocks; hàng tier-2 có
      w:vMerge-continuation cũng được mark để Word repeat cả khối header;
  (b) MỌI hàng (kể cả hàng bảng lồng) có w:cantSplit;
  (c) w:tblW type="dxa" w:w = tổng gridCol (thiếu/sai/auto -> set; 'pct'
      giữ nguyên).
  Idempotent; bảng đã đúng -> byte-identical.

C3 (WLAY-008 — policy bảng rộng áp dụng ở generator):
  build_form_maps._content_col_widths phân bổ width theo nội dung
  (weight = max(len(fold(header)), 4), min 567 twips, tổng giữ nguyên);
  builder chỉ áp cho bảng >= 10 cột. Sandbox regen (out_tpl=/tmp) chứng minh
  template sinh ra có grid không đều theo nội dung — KHÔNG đụng template
  production. Landscape bị LOẠI bằng evidence: 0/87 nguồn có
  w:orient="landscape". Split-table chỉ là candidate (chưa có owner duyệt).

C4 (WLAY-005 — census matrix PLI_M12):
  5 entry spec M12 (3 lưới ngành + nested-grid NĐD ủy quyền + fixed-matrix
  nguồn vốn) phải tồn tại trong template dưới dạng w:tbl đủ hàng/cột. 3
  matrix còn lại trong manifest (2 tài sản góp vốn + cơ cấu cổ phần) vẫn
  missing_grid -> BLOCKED_OWNER (D1.2 chỉ chốt cho M01; D1.4=A là quyết định
  formula, chưa kèm cấu trúc biểu mẫu được owner duyệt để viết spec entry).

Chạy:  python3 -X utf8 -m tools.test_phase5r_tables
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_OUT = Path("/tmp/p5r_laneC_tables")
POLICIES_PATH = ROOT / "tools" / "phase5r_table_policies.json"
MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
TEMPLATES = ROOT / "app" / "templates"

MIN_COL_TWIPS = 567          # 1 cm — trùng ngưỡng D9 của gate
MAX_TOTAL_TWIPS = 16850      # trùng ngưỡng D9 của gate
WIDE_COLS = 10               # ngưỡng "bảng rộng" của census WLAY-008


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _docx_xml(docx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        return z.read("word/document.xml").decode("utf-8")


def _write_min_docx(path: Path, body_parts: list[str]) -> Path:
    """DOCX tối thiểu tự viết document.xml (kiểm soát từng phần tử)."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>%s'
        "<w:sectPr/></w:body></w:document>" % "".join(body_parts))
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.'
            'openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", xml)
    return path


def _iter_balanced_tbls(body: str):
    """(start, end) của MỖI bảng cân bằng trong body (chịu bảng lồng)."""
    pos = 0
    while True:
        m = re.search(r"<w:tbl[ >]", body[pos:])
        if not m:
            return
        start = pos + m.start()
        depth = 1
        scan = pos + m.end()
        while depth:
            mm = re.search(r"<w:tbl[ >]|</w:tbl>", body[scan:])
            if not mm:
                raise ValueError("w:tbl khong dong")
            depth += -1 if mm.group(0).startswith("</") else 1
            scan += mm.end()
        yield start, scan
        pos = scan


def _table_depths(body: str) -> list[tuple[int, int, int]]:
    """[(start, end, depth)] — depth 1 = bảng top-level."""
    spans = list(_iter_balanced_tbls(body))
    out = []
    for s, e in spans:
        depth = 1 + sum(1 for s2, e2 in spans
                        if s2 < s and e < e2)
        out.append((s, e, depth))
    return out


def _census_template(path: Path) -> list[dict]:
    """Census mọi bảng có w:tblGrid của một template."""
    xml = _docx_xml(path.read_bytes())
    body = re.search(r"<w:body[^>]*>(.*)</w:body>", xml, re.S).group(1)
    rows = []
    for ti, (s, e) in enumerate(_iter_balanced_tbls(body)):
        seg = body[s:e]
        grid_m = re.search(r"<w:tblGrid>(.*?)</w:tblGrid>", seg, re.S)
        if not grid_m:
            continue
        grid = [int(w) if w else 0 for w in re.findall(
            r'<w:gridCol[^>]*w:w="(\d+)"', grid_m.group(1))]
        if not grid:
            continue
        rows.append({
            "form": path.stem,
            "table_index": ti,
            "cols": len(grid),
            "total_width": sum(grid),
            "min_col_width": min(grid),
        })
    return rows


def census_all_templates() -> list[dict]:
    rows: list[dict] = []
    for f in sorted(TEMPLATES.glob("PL*.docx")):
        rows.extend(_census_template(f))
    return rows


# ---------------------------------------------------------------------------
# C1 — census fixture: bảng >= 10 cột trên 87 template (base a2a5301)
# ---------------------------------------------------------------------------

WIDE_TABLE_FIXTURE = [
    # form, table_index, cols, total_width, min_col_width, loop
    # (5R3-lead rebaseline sau regen width_policy 12/12: min col chạm sàn
    #  567 twips = 1cm, cột dài nội dung nhận width lớn hơn — đo thực tế)
    ("PLII_M01", 1, 10, 8640, 567, "ds_tv_ho_gia_dinh"),
    ("PLII_M02", 1, 10, 8640, 567, "tv_hgd_sau_thay_doi"),
    ("PLII_M02", 7, 10, 8640, 567, "tv_hgd_cap_doi"),
    ("PLI_M02", 1, 14, 8638, 567, "ds_nddpl_uy_quyen_chu_so_huu"),
    ("PLI_M06", 0, 12, 8640, 567, "ds_thanh_vien_tnhh"),
    ("PLI_M07", 0, 11, 8635, 567, "ds_co_dong_sang_lap"),
    ("PLI_M09", 0, 14, 8638, 567, "ds_thanh_vien_hop_danh"),
    ("PLI_M10", 0, 12, 8640, 567, "ds_cshhl"),
    ("PLI_M12", 4, 15, 8640, 567, "ds_ndd_uy_quyen_sau_thay_doi"),
    ("PLI_M15", 1, 14, 8638, 567, "ds_nddpl_uy_quyen_chu_so_huu_moi"),
    ("PLI_M72", 5, 10, 8640, 567, "ds_co_dong_sang_lap_ctcp"),
    ("PLI_M72", 6, 10, 8640, 567, "ds_co_dong_nuoc_ngoai_ctcp"),
]

_EXPECTED_TABLE_COUNT = 76   # số bảng có w:tblGrid trên toàn corpus
_EXPECTED_TEMPLATE_COUNT = 87


def _check(fn):
    fn._is_check = True
    return fn


_RESULTS: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        @_check
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
        wrapped._label = name
        return wrapped
    return deco


# ---------------------------------------------------------------------------
# C1 tests
# ---------------------------------------------------------------------------

@check("C1a_census_wide_fixture_matches")
def test_c1a_census_fixture():
    census = census_all_templates()
    n_tpl = len(sorted(TEMPLATES.glob("PL*.docx")))
    assert n_tpl == _EXPECTED_TEMPLATE_COUNT, \
        "số template đổi: %d != %d" % (n_tpl, _EXPECTED_TEMPLATE_COUNT)
    assert len(census) == _EXPECTED_TABLE_COUNT, \
        ("tổng số bảng có grid đổi: %d != %d — fixture census phải được "
         "cập nhật có chủ đích" % (len(census), _EXPECTED_TABLE_COUNT))
    wide = [(r["form"], r["table_index"], r["cols"], r["total_width"],
             r["min_col_width"]) for r in census if r["cols"] >= WIDE_COLS]
    expect = [t[:5] for t in WIDE_TABLE_FIXTURE]
    assert sorted(wide) == sorted(expect), (
        "census bảng >=10 cột lệch fixture:\n  census=%s\n  fixture=%s"
        % (sorted(wide), sorted(expect)))
    # loop khớp thực tế trong template
    loops_by_key = {t[:2]: t[5] for t in WIDE_TABLE_FIXTURE}
    for (form, ti), loop in loops_by_key.items():
        xml = _docx_xml((TEMPLATES / ("%s.docx" % form)).read_bytes())
        body = re.search(r"<w:body[^>]*>(.*)</w:body>", xml, re.S).group(1)
        segs = list(_iter_balanced_tbls(body))
        seg = body[segs[ti][0]:segs[ti][1]]
        assert ("{#%s}" % loop) in seg or loop in seg, \
            "%s#%d không còn loop %s" % (form, ti, loop)


@check("C1b_d9_threshold_invariants_hold")
def test_c1b_thresholds():
    for r in census_all_templates():
        assert r["total_width"] <= MAX_TOTAL_TWIPS, \
            "%s#%d tổng width %d > %d (WLAY-008 WIDTH_OVERFLOW)" % (
                r["form"], r["table_index"], r["total_width"],
                MAX_TOTAL_TWIPS)
        assert r["min_col_width"] >= MIN_COL_TWIPS, \
            "%s#%d min col %d < %d twips (WLAY-008 NARROW_COL)" % (
                r["form"], r["table_index"], r["min_col_width"],
                MIN_COL_TWIPS)


@check("C1c_policies_cover_wide_tables")
def test_c1c_policies_json():
    assert POLICIES_PATH.exists(), "thiếu tools/phase5r_table_policies.json"
    pol = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
    entries = pol.get("wide_table_policies", [])
    by_key = {(e.get("form"), e.get("table_index")): e for e in entries}
    for form, ti, cols, total, min_w, loop in WIDE_TABLE_FIXTURE:
        e = by_key.get((form, ti))
        assert e is not None, "thiếu policy cho %s#%d" % (form, ti)
        assert (e.get("cols"), e.get("total_width"),
                e.get("min_col_width")) == (cols, total, min_w), \
            "%s#%d: policy census lệch fixture" % (form, ti)
        assert e.get("policy") in pol.get("policy_values", {}), \
            "%s#%d: policy %r không nằm trong policy_values" % (
                form, ti, e.get("policy"))
        assert e.get("source_evidence"), "%s#%d thiếu source_evidence" % (
            form, ti)
        assert e.get("spec_ref"), "%s#%d thiếu spec_ref" % (form, ti)
        assert e.get("landscape") is False, \
            "%s#%d: không có nguồn landscape nào (0/87) để chọn landscape" % (
                form, ti)
        assert e.get("render_pins") == ["tblHeader", "cantSplit", "tblW"], \
            "%s#%d thiếu render_pins" % (form, ti)
    # mọi policy entry đều trỏ tới bảng thật trong fixture (không policy ma)
    fixture_keys = {(f, t) for f, t, *_ in WIDE_TABLE_FIXTURE}
    for k in by_key:
        assert k in fixture_keys, "policy cho bảng ngoài census: %s" % (k,)


# ---------------------------------------------------------------------------
# C2 tests — pin chất lượng bảng ở render
# ---------------------------------------------------------------------------

def _tbl_xml(rows_xml: list[str], widths: list[int], tblw: str = "",
             tblpr_inner: str = "") -> str:
    grid = "".join('<w:gridCol w:w="%d"/>' % w for w in widths)
    tblpr = "<w:tblPr>%s%s</w:tblPr>" % (tblpr_inner, tblw) \
        if tblpr_inner or tblw else "<w:tblPr/>"
    return ("<w:tbl>%s<w:tblGrid>%s</w:tblGrid>%s</w:tbl>"
            % (tblpr, grid, "".join(rows_xml)))


def _cell_xml(text: str, width: int, extra_tcpr: str = "") -> str:
    return ('<w:tc><w:tcPr>%s<w:tcW w:w="%d" w:type="dxa"/></w:tcPr>'
            "<w:p><w:r><w:t>%s</w:t></w:r></w:p></w:tc>"
            % (extra_tcpr, width, text))


@check("C2a_pin_unit_missing_all")
def test_c2a_pin_unit():
    from tools import docx_render as dr
    rows = [
        "<w:tr>%s%s</w:tr>" % (_cell_xml("STT", 500), _cell_xml("Họ tên",
                                                                4000)),
        "<w:tr>%s%s</w:tr>" % (_cell_xml("1", 500), _cell_xml("Nguyễn A",
                                                              4000)),
    ]
    tbl = _tbl_xml(rows, [500, 4000])
    src = _write_min_docx(TEST_OUT / "c2a.docx", [tbl,
                                                  "<w:p><w:r><w:t>x</w:t>"
                                                  "</w:r></w:p>"])
    xml = _docx_xml(dr.render(src, {}))
    # bảng còn nguyên (không bị render guard khác đụng)
    segs = list(_iter_balanced_tbls(_body_of(xml)))
    assert len(segs) == 1, "bảng test bị đụng bởi guard khác: %d bảng" % (
        len(segs),)
    seg = _body_of(xml)[segs[0][0]:segs[0][1]]
    assert "<w:tblHeader/>" in seg, "hàng 0 thiếu tblHeader sau pin"
    assert seg.count("<w:cantSplit/>") == 2, \
        "2 hàng dữ liệu phải đủ cantSplit, thấy %d" % seg.count(
            "<w:cantSplit/>")
    m = re.search(r'<w:tblW w:w="(\d+)" w:type="dxa"/>', seg)
    assert m and int(m.group(1)) == 4500, \
        "tblW phải = grid sum 4500 dxa, thấy %r" % (m and m.group(0),)
    # idempotent: pin lần 2 trên output đã pin -> không đổi
    xml2 = dr._pin_table_quality(xml)
    assert xml2 == xml, "pin không idempotent"
    # bảng đã đúng -> byte-identical
    good_tbl = _tbl_xml(
        ['<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>%s%s</w:tr>'
         % (_cell_xml("STT", 500), _cell_xml("Họ tên", 4000)),
         '<w:tr><w:trPr><w:cantSplit/></w:trPr>%s%s</w:tr>'
         % (_cell_xml("1", 500), _cell_xml("Nguyễn A", 4000))],
        [500, 4000], tblw='<w:tblW w:w="4500" w:type="dxa"/>')
    good_xml = ("<w:body>%s</w:body>" % good_tbl)
    assert dr._pin_table_quality(good_xml) == good_xml, \
        "bảng đã đúng bị đổi bytes"


@check("C2b_pin_pct_and_band_and_two_tier")
def test_c2b_pin_specials():
    from tools import docx_render as dr
    # (1) tblW pct -> giữ nguyên
    rows = ["<w:tr>%s</w:tr>" % _cell_xml("A", 1000),
            "<w:tr>%s</w:tr>" % _cell_xml("1", 1000)]
    tbl = _tbl_xml(rows, [1000], tblw='<w:tblW w:w="5000" w:type="pct"/>')
    out = dr._pin_table_quality("<w:body>%s</w:body>" % tbl)
    assert '<w:tblW w:w="5000" w:type="pct"/>' in out, "tblW pct bị đổi"
    assert "<w:cantSplit/>" in out and "<w:tblHeader/>" in out
    # (2) band quốc hiệu -> KHÔNG tblHeader
    band_rows = [
        "<w:tr><w:tc><w:tcPr><w:tcW w:w=\"5000\"/></w:tcPr><w:p><w:r>"
        "<w:t>TÊN DOANH NGHIỆP</w:t></w:r></w:p></w:tc></w:tr>",
        "<w:tr><w:tc><w:tcPr><w:tcW w:w=\"5000\"/></w:tcPr><w:p><w:r>"
        "<w:t>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</w:t></w:r>"
        "<w:p><w:r><w:t>Độc lập - Tự do - Hạnh phúc</w:t></w:r></w:p>"
        "</w:tc></w:tr>"]
    band = _tbl_xml(band_rows, [5000])
    out2 = dr._pin_table_quality("<w:body>%s</w:body>" % band)
    assert "<w:tblHeader" not in out2, \
        "band quốc hiệu (layout) không được mark tblHeader"
    assert out2.count("<w:cantSplit/>") == 2
    # (3) header 2 tier có vMerge -> tblHeader rows 0+1, không row 2
    tier2 = ('<w:tr><w:tc><w:tcPr><w:vMerge/><w:tcW w:w="1000"/></w:tcPr>'
             "<w:p/></w:tc><w:tc><w:tcPr><w:vMerge/><w:tcW w:w=\"2000\"/>"
             '</w:tcPr><w:p><w:r><w:t>cột A</w:t></w:r></w:p></w:tc></w:tr>')
    h1 = ("<w:tr><w:tc><w:tcPr><w:vMerge w:val=\"restart\"/>"
          '<w:tcW w:w="1000"/></w:tcPr><w:p><w:r><w:t>STT</w:t></w:r></w:p>'
          "</w:tc><w:tc><w:tcPr><w:tcW w:w=\"2000\"/></w:tcPr><w:p><w:r>"
          "<w:t>nhóm A</w:t></w:r></w:p></w:tc></w:tr>")
    data = ("<w:tr><w:tc><w:tcPr><w:tcW w:w=\"1000\"/></w:tcPr><w:p><w:r>"
            "<w:t>1</w:t></w:r></w:p></w:tc><w:tc><w:tcPr>"
            '<w:tcW w:w="2000"/></w:tcPr><w:p><w:r><w:t>x</w:t></w:r></w:p>'
            "</w:tc></w:tr>")
    tbl3 = _tbl_xml([h1, tier2, data], [1000, 2000])
    out3 = dr._pin_table_quality("<w:body>%s</w:body>" % tbl3)
    trs = re.findall(r"<w:tr>.*?</w:tr>", out3, re.S)
    assert len(trs) == 3
    assert "<w:tblHeader/>" in trs[0] and "<w:tblHeader/>" in trs[1], \
        "header 2 tier cần tblHeader ở cả 2 hàng đầu"
    assert "<w:tblHeader/>" not in trs[2], "hàng dữ liệu bị mark tblHeader"


@check("C2c_pin_integration_real_templates")
def test_c2c_integration():
    from tools import docx_render as dr
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    if (TEST_OUT / "render").exists():
        shutil.rmtree(TEST_OUT / "render")
    for fid in ("PLI_M02", "PLI_M12", "PLI_M72", "PLII_M01"):
        fmap = maps[fid]
        data = dr.dummy_data_from_map(fmap)
        out = dr.render(ROOT / "app" / fmap["template"], data)
        xml = _docx_xml(out)
        body = _body_of(xml)
        for s, e, depth in _table_depths(body):
            seg = body[s:e]
            grid = [int(w) for w in re.findall(
                r'<w:gridCol[^>]*w:w="(\d+)"', seg)]
            if not grid:
                continue
            label = "%s tbl@%d" % (fid, segs_index(body, s))
            tblw = re.search(r"<w:tblW\b[^>]*/>", seg)
            assert tblw, "%s: thiếu tblW" % label
            if 'w:type="pct"' in tblw.group(0):
                continue
            mw = re.search(r'w:w="(\d+)"', tblw.group(0))
            assert mw and int(mw.group(1)) == sum(grid), \
                "%s: tblW %s != grid sum %d" % (label, tblw.group(0),
                                                sum(grid))
            trs = _direct_rows(seg)
            assert trs, "%s: không tách được hàng" % label
            for rseg in trs:
                assert "<w:cantSplit/>" in rseg, \
                    "%s: hàng thiếu cantSplit" % label
            if depth == 1 and len(trs) >= 2:
                texts = "".join(re.findall(
                    r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", trs[0]))
                is_band = (("TÊN DOANH NGHIỆP" in texts or
                            "TÊN HỘ KINH DOANH" in texts) and
                           "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in seg)
                row0_has_text = texts.strip() != ""
                if row0_has_text and not is_band:
                    assert "<w:tblHeader/>" in trs[0], \
                        "%s: hàng header thật thiếu tblHeader" % label


def _body_of(xml: str) -> str:
    return re.search(r"<w:body[^>]*>(.*)</w:body>", xml, re.S).group(1)


def segs_index(body: str, start: int) -> int:
    for i, (s, _e) in enumerate(_iter_balanced_tbls(body)):
        if s == start:
            return i
    return -1


def _direct_rows(seg: str) -> list[str]:
    """Các hàng TRỰC TIẾP của bảng (bỏ hàng của bảng lồng bên trong).

    `seg` BAO GỒM tag mở <w:tbl ...> của bảng nên depth khởi đầu 0; tag mở
    bảng đầu tiên đưa depth lên 1 — hàng gặp ở depth 1 là hàng trực tiếp.
    """
    rows = []
    pos = 0
    tbl_depth = 0
    while True:
        m = re.search(r"<w:tr[ >]|</w:tr>|<w:tbl[ >]|</w:tbl>", seg[pos:])
        if not m:
            break
        tok = m.group(0)
        if tok.startswith("<w:tbl"):
            tbl_depth += 1
            pos += m.end()
            continue
        if tok == "</w:tbl>":
            tbl_depth -= 1
            pos += m.end()
            continue
        if tok.startswith("<w:tr"):
            if tbl_depth == 1:
                start = pos + m.start()
                d = 1
                scan = pos + m.end()
                while d:
                    mm = re.search(r"<w:tr[ >]|</w:tr>", seg[scan:])
                    d += -1 if mm.group(0) == "</w:tr>" else 1
                    scan += mm.end()
                rows.append(seg[start:scan])
                pos = scan
                continue
            pos += m.end()
            continue
        pos += m.end()
    return rows


# ---------------------------------------------------------------------------
# C3 tests — width redistribution trong generator
# ---------------------------------------------------------------------------

@check("C3a_content_widths_unit")
def test_c3a_unit():
    from tools import build_form_maps as bfm
    weights = [3, 60, 8, 12]           # STT vs header dài vs cột ngắn
    total = 8640
    ws = bfm._content_col_widths(weights, total, min_w=MIN_COL_TWIPS)
    assert len(ws) == 4
    assert sum(ws) == total, "tổng width phải giữ nguyên: %s" % (ws,)
    assert all(w >= MIN_COL_TWIPS for w in ws), \
        "mọi cột >= 567: %s" % (ws,)
    assert ws[1] > ws[0] and ws[1] > ws[2], \
        "header dài phải nhận width lớn hơn: %s" % (ws,)
    assert ws == bfm._content_col_widths(weights, total,
                                         min_w=MIN_COL_TWIPS), \
        "phân bổ không deterministic"
    # min floor: 15 cột nội dung ngang nhau -> đều, đủ sàn, đúng tổng
    ws2 = bfm._content_col_widths([4] * 15, total, min_w=MIN_COL_TWIPS)
    assert sum(ws2) == total and all(w >= MIN_COL_TWIPS for w in ws2)


@check("C3b_sandbox_regen_wide_grid")
def test_c3b_sandbox_regen():
    from tools import build_form_maps as bfm
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    prod_before = {
        fid: (ROOT / "app" / maps[fid]["template"]).read_bytes()
        for fid in ("PLI_M12", "PLI_M72")}
    out = TEST_OUT / "sandbox_regen"
    if out.exists():
        shutil.rmtree(out)
    titles = bfm.load_csv_titles()
    for fid in ("PLI_M12", "PLI_M72"):
        meta, _u = bfm.process_form(bfm.find_source(fid), titles, None,
                                    out_tpl=out)
        xml = _docx_xml((out / ("%s.docx" % fid)).read_bytes())
        body = _body_of(xml)
        found_wide = False
        for s, e in _iter_balanced_tbls(body):
            seg = body[s:e]
            grid = [int(w) for w in re.findall(
                r'<w:gridCol[^>]*w:w="(\d+)"', seg)]
            if len(grid) < WIDE_COLS:
                continue
            found_wide = True
            assert sum(grid) == 8640, "tổng width phải giữ 8640: %s" % (grid,)
            assert min(grid) >= MIN_COL_TWIPS
            assert max(grid) > min(grid), \
                "%s: grid đều %s — width không phân bổ theo nội dung" % (
                    fid, grid)
            # cột STT (nhãn 3 ký tự) phải hẹp hơn cột nhãn dài nhất
            texts = re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", seg)
            assert any(len(t) > 20 for t in texts), "thiếu header dài"
        assert found_wide, "%s: sandbox regen mất bảng rộng?" % fid
    # template production KHÔNG bị sandbox regen đụng (byte trước == sau)
    for fid in ("PLI_M12", "PLI_M72"):
        tpl = ROOT / "app" / maps[fid]["template"]
        assert tpl.read_bytes() == prod_before[fid], \
            "%s: production template bị sandbox regen đụng" % fid


# ---------------------------------------------------------------------------
# C4 tests — WLAY-005 PLI_M12 matrix census
# ---------------------------------------------------------------------------

# (section_id, template table_index, rows, cols, expect_present)
M12_SPEC_MATRICES = [
    ("nguon_von_dieule_sau_thay_doi", 0, 6, 3, True),
    ("nganh_bo_sung", 1, 6, 4, True),
    ("nganh_xoa_bo", 2, 6, 4, True),
    ("nganh_sua_doi_chi_tiet", 3, 6, 4, True),
    ("ndd_uy_quyen_sau_thay_doi", 4, 8, 15, True),
]

# 3 matrix còn lại của manifest vẫn missing_grid -> BLOCKED_OWNER
M12_BLOCKED_MATRICES = [
    "tai_san_gop_von_sau_thay_doi_vdl",
    "co_cau_loai_co_phan_sau_thay_doi",
    "tai_san_gop_von_sau_thay_doi_von_dau_tu",
]


@check("C4a_m12_spec_matrices_materialized")
def test_c4a_m12_tables():
    xml = _docx_xml((TEMPLATES / "PLI_M12.docx").read_bytes())
    body = _body_of(xml)
    segs = list(_iter_balanced_tbls(body))
    assert len(segs) == 5, "M12 phải đúng 5 bảng (census): %d" % len(segs)
    for sid, ti, rows, cols, _present in M12_SPEC_MATRICES:
        seg = body[segs[ti][0]:segs[ti][1]]
        grid = [int(w) for w in re.findall(
            r'<w:gridCol[^>]*w:w="(\d+)"', seg)]
        n_rows = len(_direct_rows(seg))
        assert len(grid) == cols, \
            "%s: bảng %d có %d cột, kỳ vọng %d" % (sid, ti, len(grid), cols)
        assert n_rows == rows, \
            "%s: bảng %d có %d hàng, kỳ vọng %d" % (sid, ti, n_rows, rows)


@check("C4b_m12_matrix_status_json")
def test_c4b_m12_status():
    pol = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
    entries = {e["section_id"]: e for e in pol.get("m12_matrix_census", [])}
    for sid, ti, rows, cols, present in M12_SPEC_MATRICES:
        e = entries.get(sid)
        assert e is not None, "thiếu census cho matrix %s" % sid
        assert e.get("status") in ("matrix-ok", "display-pinned"), \
            "%s: status %r không đúng cho matrix đã dựng" % (
                sid, e.get("status"))
        assert (e.get("template_table_index") == ti
                and e.get("rows") == rows and e.get("cols") == cols), \
            "%s: census lệch thực tế template" % sid
    for sid in M12_BLOCKED_MATRICES:
        e = entries.get(sid)
        assert e is not None, "thiếu census cho matrix %s" % sid
        st = e.get("status", "")
        assert st.startswith("BLOCKED_OWNER"), \
            "%s: phải BLOCKED_OWNER, thấy %r" % (sid, st)
        assert len(st) > len("BLOCKED_OWNER") + 2, \
            "%s: BLOCKED_OWNER phải kèm lý do" % sid
    # blocked matrix KHÔNG được tồn tại dưới dạng bảng trong template
    xml = _docx_xml((TEMPLATES / "PLI_M12.docx").read_bytes())
    body = _body_of(xml)
    for s, e in _iter_balanced_tbls(body):
        seg = body[s:e]
        for marker in ("Tài sản góp vốn sau khi thay đổi vốn điều lệ",
                       "Thông tin về cổ phần",
                       "sau khi thay đổi vốn đầu tư"):
            assert marker not in seg, \
                "matrix BLOCKED_OWNER %r lại xuất hiện như w:tbl" % marker


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    TEST_OUT.mkdir(parents=True, exist_ok=True)
    import tools.test_phase5r_tables as _self  # noqa: F401
    for name, fn in sorted(globals().items()):
        obj = fn
        if callable(obj) and getattr(obj, "_is_check", False):
            obj()
    passed = [r for r in _RESULTS if r[1]]
    failed = [r for r in _RESULTS if not r[1]]
    for name, ok, msg in _RESULTS:
        print(("PASS " if ok else "FAIL ") + name +
              ("" if ok else "\n      -> " + msg))
    print("-" * 60)
    print("Tổng kết: %d PASS / %d FAIL" % (len(passed), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
