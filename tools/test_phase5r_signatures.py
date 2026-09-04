# -*- coding: utf-8 -*-
"""test_phase5r_signatures.py — Phase 5R2 Lane B: contract khối ký + census
87 form + test đỏ-xanh cho WLAY-002/003/004/009.

==== Phương pháp census (B1 — độ phủ 87 form) ====

Mỗi form trong app/data/form_maps.json được census TỪ TEMPLATE (app/templates
/<form>.docx — chính là nguồn render) theo 3 bước:

  1. Quét mọi <w:p> trong word/document.xml (body + trong ô bảng, phân biệt
     bằng depth đếm <w:tbl>/<w:tr>). Mỗi paragraph tách thành các DÒNG logic
     theo <w:br/> (cụm ký nguồn thường là "TITLE<br/>(Ký …)" trong 1 p).
  2. Gập dấu bằng tools.layout_roles.fold rồi xếp loại từng dòng:
     nhãn ký  = SIG_TITLE_LINE_RE (bảng nhãn SIGNER của layout_roles mở rộng
                "truong phong", "chu tich hoi dong thanh vien", "to chuc",
                "ca nhan", "nguoi nop", "nguoi nhan", "chu so huu …" — khớp
                _SIG_TITLE_FOLD của gate) — dòng NGẮN, không paren;
     chỉ thị  = SIG_INSTR_FOLD_RE — "(ký …"/"(đã ký …"/"(ký, ghi họ tên và
                đóng dấu)" (bộ alternating của gate D6 MỞ RỘNG thêm biến thể
                "ky, ghi ho ten va dong dau" mà gate chưa bắt).
  3. Cụm ký (cluster) = paragraph chứa dòng chỉ thị; title của cụm là nhãn
     ký cùng paragraph (dòng trước br) HOẶC paragraph NHÃN liền trước trong
     cùng container.

Pin orientation vào registry (tools/phase5r_expectations.json — Lead cho
Lane B quyền sửa mục signature) CHỈ khi có bằng chứng:
  - horizontal: ảnh owner/audit (docs/word_layout_audit_2026-09-03.md
    WLAY-002) — hiện chỉ PLI_M70;
  - vertical:  cụm đơn (không có hỏi题 horizontal) hoặc entry do owner chốt
    (PLI_M15 "xếp dọc là đúng hướng");
  - KHÔNG pin (BLOCKED_OWNER cho orientation): form >=2 signer xếp dọc trong
    nguồn nhưng không có bằng chứng bản giấy (nguồn M70 cũng xếp dọc dù bản
    giấy là ngang → nguồn KHÔNG đủ kết luận) — PLI_M14, PLII_M17.
  - KHÔNG pin (ngoài phạm vi detector): form chỉ có chỉ thị không-paren
    "Ký, ghi họ tên và đóng dấu" (giấy chứng nhận M42/M43/M47/M50…) —
    detector D6 không thấy cụm nên không thể đo orientation.

==== Các test ====
  B2: sandbox regen PLI_M70 (process_form out_tpl=/tmp) phải sinh bảng ký
      KHÔNG VIỀN 1 hàng × 2 ô với 2 title registry + cantSplit, trong khi
      app/templates/PLI_M70.docx KHÔNG ĐỔI MỘT BYTE (sandbox-only).
  B3: render() phải gắn keepLines/keepNext cho cụm ký + cantSplit cho hàng
      bảng ký (docx tổng hợp), idempotent, không đụng paragraph thường.
  B4: render M15 phải chèn vùng viết exact-height dưới mỗi instruction; đo
      PDF (pymupdf) gap >= min_write_gap_pt (40pt).
  B5: policy orphan-signature-page — trang thưa/trắng chứa chỉ thị ký mà
      KHÔNG có title cùng trang là lỗi; đo trên corpus export cục bộ subset
      đại diện. Baseline đỏ: PLII_M25 (long-boundary p2), PLI_M09
      (empty-paper p6) — fix bằng keep-together B3.

Chạy:  python3 -X utf8 -m tools.test_phase5r_signatures
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.layout_roles import fold   # noqa: E402

MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
EXPECT_PATH = ROOT / "tools" / "phase5r_expectations.json"
# [6V-V0/Lead] suffix pid: 2 process chạy cùng suite song song (2 runner
# song song — gate V0(a)) phải 2 sandbox RỜI NHAU; path cố định cũ khiến
# process này rmtree sandbox của process kia → FileNotFoundError/
# FileExistsError đỏ giả (không phải lỗi soffice — V0-I1 đã đóng lớp đó).
SANDBOX_TPL = Path("/tmp/p5r_laneB_sandbox_tpl_p%d" % os.getpid())
TEST_OUT = Path("/tmp/p5r_laneB_sig_tests_p%d" % os.getpid())

# ---------------------------------------------------------------------------
# Ngữ pháp census (mở rộng có chủ đích của gate D6 — ghi trong docstring)
# ---------------------------------------------------------------------------

_SIG_TITLE_LINE_RE = re.compile(
    r"^(chu ho kinh doanh|dai dien chu ho|chu doanh nghiep|nguoi dai dien "
    r"theo phap luat|dai dien theo phap luat|nguoi khai ho so|nguoi nop ho "
    r"so|nguoi nop|nguoi nhan|nguoi uy quyen|nguoi ky|truong ban|giam doc|"
    r"tong giam doc|truong phong|ke toan|ke toan truong|ban giao dich|"
    r"dai dien cong ty|chu tich|chu tich hoi dong thanh vien|thu ky|"
    r"chu so huu( moi| cu)?|dai dien cac thanh vien khong yeu cau thanh lap|"
    r"hoi dong thanh vien|nguoi chuyen doi|chu doanh nghiep tu nhan|"
    r"dai dien phap luat cua to chuc|to chuc|ca nhan|nguoi duoc tang cho|"
    r"nguoi thua ke|nguoi mua|cac thanh vien hop danh|nguoi de nghi)"
    r"[0-9]{0,2}$")
_SIG_INSTR_FOLD_RE = re.compile(
    r"\((ky va ghi ro ho ten|ky ghi ro ho ten|ky va ghi ho ten|ky ten|"
    r"ky, ghi ro ho ten|ky, ho ten|ky ho ten|da ky|ky, ho ten, dong dau|"
    r"ky ten, dong dau|ky, ghi ho ten va dong dau)\b")
_SIG_INSTR_NOPAREN_RE = re.compile(
    r"^ky(,| va)? ghi ho ten( va)?( dong dau)?[0-9]{0,2}$")

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
            except Exception as exc:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


# ---------------------------------------------------------------------------
# Census (B1)
# ---------------------------------------------------------------------------

def _para_lines(p_xml: str) -> list[str]:
    """Tách paragraph XML thành dòng logic theo <w:br/>."""
    parts: list[str] = [""]
    for m in re.finditer(r"<w:t[^>]*>([^<]*)</w:t>|<w:br/?>", p_xml):
        if m.group(0).startswith("<w:br"):
            parts.append("")
        else:
            parts[-1] += m.group(1)
    return [p for p in parts if p.strip()]


def census_form(fid: str, maps: dict) -> dict:
    """Census khối ký của 1 form từ template. Trả:
    {clusters: [{titles, instr, in_table}], signers, titles, has_noparen}"""
    tp = ROOT / "app" / maps[fid]["template"]
    with zipfile.ZipFile(tp) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    body = re.search(r"<w:body>(.*)</w:body>", xml, re.S).group(1)
    clusters: list[dict] = []
    pending_label = ""      # nhãn IN HOA liền trước trong cùng container
    in_table = 0
    has_noparen = False
    for m in re.finditer(
            r"<w:tbl[ >]|</w:tbl>|<w:p[ >].*?</w:p>|<w:p[^>]*/>", body, re.S):
        tok = m.group(0)
        if tok.startswith("<w:tbl"):
            in_table += 1
            pending_label = ""
            continue
        if tok == "</w:tbl>":
            in_table -= 1
            pending_label = ""
            continue
        lines = _para_lines(tok)
        text_all = " ".join(lines)
        instr_m = None
        for ln in lines:
            im = _SIG_INSTR_FOLD_RE.search(fold(ln))
            if im:
                instr_m = (ln, im)
                break
        if instr_m is None:
            # chỉ thị không-paren (dòng riêng "Ký, ghi họ tên và đóng dấu")
            for ln in lines:
                if _SIG_INSTR_NOPAREN_RE.match(fold(ln)):
                    has_noparen = True
                    clusters.append({
                        "titles": [pending_label] if pending_label else [],
                        "instr": ln, "in_table": bool(in_table),
                        "detected_by_gate": False})
                    pending_label = ""
                    break
            if not lines:
                continue
            # nhãn IN HOA đơn (title para kiểu riêng — cho cụm title/instr)
            f0 = fold(lines[0])
            if (len(lines) == 1 and len(f0) <= 40
                    and _SIG_TITLE_LINE_RE.match(f0)):
                pending_label = lines[0]
            else:
                pending_label = ""
            continue
        instr_line = instr_m[0]
        titles: list[str] = []
        for ln in lines:
            if ln == instr_line:
                break
            f = fold(ln)
            f_clean = re.sub(r"[0-9]{1,2}$", "", f)
            if _SIG_TITLE_LINE_RE.match(f_clean) or _SIG_TITLE_LINE_RE.match(f):
                titles.append(ln.strip())
        if not titles and pending_label:
            titles = [pending_label]
        clusters.append({"titles": titles, "instr": instr_line,
                         "in_table": bool(in_table),
                         "detected_by_gate": True})
        pending_label = ""
    return {
        "clusters": clusters,
        "signers": len(clusters),
        "titles": [t for c in clusters for t in c["titles"]],
        "has_noparen": has_noparen,
    }


def census_all() -> tuple[dict, dict]:
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    return {fid: census_form(fid, maps) for fid in sorted(maps)}, maps


# ---------------------------------------------------------------------------
# Helpers dùng chung cho test render/export
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


def _sig_pdf_lines(page) -> list[dict]:
    """Dòng chữ ký TRÊN PDF (pymupdf) — ngữ pháp census (rộng hơn gate)."""
    lines: dict[tuple, list] = {}
    for w in page.get_text("words"):
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for _bk, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        text = " ".join(w[4] for w in ws)
        f = fold(text)
        out.append({
            "text": text, "x0": min(w[0] for w in ws),
            "x1": max(w[2] for w in ws), "y0": min(w[1] for w in ws),
            "y1": max(w[3] for w in ws),
            "title": bool(_SIG_TITLE_LINE_RE.match(
                re.sub(r"[0-9]{1,2}$", "", f))),
            "instr": bool(_SIG_INSTR_FOLD_RE.search(f)
                          or _SIG_INSTR_NOPAREN_RE.match(f)),
        })
    return out


def _export_subset(form_ids: list[str], fixtures: list[str],
                   out_root: Path) -> list[Path]:
    """Export qua ĐƯỜNG PRODUCTION (Bridge.export — docx+pdf+LibreOffice)
    cho subset form × fixtures; trả các thư mục evidence."""
    from tools.phase5_visual_gate import run_export  # noqa: E402
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    blocks_all = {}
    for fid in form_ids:
        p = BLOCKS_DIR / ("%s.json" % fid)
        if p.exists():
            blocks_all[fid] = json.loads(p.read_text(encoding="utf-8"))
    dirs: list[Path] = []
    for fixture in fixtures:
        errors, dirs_fx = run_export(maps, blocks_all, fixture,
                                     form_ids, out_root)
        assert not errors, "export lỗi: %r" % (errors,)
        dirs += dirs_fx
    return dirs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@check("B1_census_registry_consistency")
def test_census_registry():
    """Registry mục signature phải khớp census (signers/titles) cho mọi form
    có khối ký; form không khối ký KHÔNG được có entry."""
    census, maps = census_all()
    reg = json.loads(EXPECT_PATH.read_text(encoding="utf-8"))
    for fid, c in census.items():
        entry = (reg.get(fid) or {}).get("signature")
        if c["signers"] == 0 and not c["has_noparen"]:
            assert entry is None, \
                "%s không có khối ký nhưng có entry registry" % fid
            continue
        assert entry is not None, "%s có khối ký nhưng thiếu entry" % fid
        assert entry.get("signers") == c["signers"], \
            "%s signers registry=%s census=%s" % (
                fid, entry.get("signers"), c["signers"])
        # titles khớp (so gập dấu, giữ thứ tự)
        rt = [fold(t) for t in entry.get("titles") or []]
        ct = [fold(t) for t in c["titles"]]
        assert rt == ct, "%s titles registry=%r census=%r" % (fid, rt, ct)
        assert entry.get("keep_together") is True, \
            "%s thiếu keep_together=true" % fid
        assert entry.get("evidence"), "%s thiếu evidence" % fid


@check("B2_m70_sandbox_regen_1x2_table")
def test_b2_m70_table():
    """WLAY-002: sandbox regen PLI_M70 sinh bảng ký không viền 1x2; template
    production KHÔNG đổi byte."""
    from tools import build_form_maps as bfm
    prod = ROOT / "app" / "templates" / "PLI_M70.docx"
    before = prod.read_bytes()
    import shutil
    if SANDBOX_TPL.exists():
        shutil.rmtree(SANDBOX_TPL)
    titles = bfm.load_csv_titles()
    meta, _unmatched = bfm.process_form(
        bfm.find_source("PLI_M70"), titles, None, out_tpl=SANDBOX_TPL)
    after = prod.read_bytes()
    assert before == after, \
        "app/templates/PLI_M70.docx bị đổi trong sandbox regen — CẤM"
    xml = _docx_xml((SANDBOX_TPL / "PLI_M70.docx").read_bytes())
    tbls = re.findall(r"<w:tbl[ >].*?</w:tbl>", xml, re.S)
    sig_tbls = [t for t in tbls
                if "NGƯỜI NỘP" in t and "NGƯỜI NHẬN" in t]
    assert len(sig_tbls) == 1, \
        "mong đúng 1 bảng ký M70, thấy %d" % len(sig_tbls)
    t = sig_tbls[0]
    rows = re.findall(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", t, re.S)
    assert len(rows) == 1, "bảng ký phải 1 HÀNG, thấy %d" % len(rows)
    cells = re.findall(r"<w:tc>.*?</w:tc>", rows[0], re.S)
    assert len(cells) == 2, "bảng ký phải 2 Ô, thấy %d" % len(cells)
    assert '"nil"' in t and '<w:top w:val="nil"/>' in t, \
        "bảng ký phải KHÔNG VIỀN"
    assert "<w:cantSplit/>" in t, "hàng ký phải cantSplit"
    for title, cell in zip(("NGƯỜI NỘP", "NGƯỜI NHẬN"), cells):
        assert title in cell, "ô thiếu title %s" % title
        assert "(Ký và ghi họ tên)" in cell, "ô thiếu instruction %s" % title
    # metadata form_maps đồng bộ (grid 1x2) — test chạy trên meta trả về
    grids = [s.get("grid") for s in meta.get("section_specs", [])
             if s.get("kind") == "output-table"
             and "chu_ky" in str(s.get("semantic_key"))]
    assert grids and grids[0].get("rows") == 1 and grids[0].get("cols") == 2, \
        "section_spec grid chưa đồng bộ 1x2: %r" % (grids,)
    # Render-guard: template production CHƯA regen vẫn phải in ngang qua
    # render (guard mirror — sửa app/templates là CẤM, sửa render là đúng lớp)
    from tools import docx_render as dr
    rxml = _docx_xml(dr.render(prod, {"noi_nhan": "X"}))
    r_tbls = [t for t in re.findall(r"<w:tbl[ >].*?</w:tbl>", rxml, re.S)
              if "NGƯỜI NỘP" in t and "NGƯỜI NHẬN" in t]
    assert len(r_tbls) == 1, "render: mong 1 bảng ký M70, thấy %d" % len(r_tbls)
    rt = r_tbls[0]
    r_rows = re.findall(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", rt, re.S)
    assert len(r_rows) == 1, \
        "render: bảng ký phải 1 hàng (đang %d)" % len(r_rows)
    assert len(re.findall(r"<w:tc>", rt)) == 2, "render: bảng ký phải 2 ô"
    assert rt.count('"nil"') >= 6 and "<w:cantSplit/>" in rt, \
        "render: bảng ký phải không viền + cantSplit"


@check("B2_no_collateral_unregistered_forms")
def test_b2_no_collateral():
    """Form KHÔNG pin horizontal phải regen không sinh bảng ký mới."""
    from tools import build_form_maps as bfm
    import shutil
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    out = Path("/tmp/p5r_laneB_sandbox_neg_p%d" % os.getpid())
    if out.exists():
        shutil.rmtree(out)
    titles = bfm.load_csv_titles()
    for fid in ("PLI_M15", "PLI_M09"):
        meta, _u = bfm.process_form(bfm.find_source(fid), titles, None,
                                    out_tpl=out)
        xml = _docx_xml((out / ("%s.docx" % fid)).read_bytes())
        n_before = len(re.findall(
            r"<w:tbl[ >]", _docx_xml(
                (ROOT / "app" / maps[fid]["template"]).read_bytes())))
        n_after = len(re.findall(r"<w:tbl[ >]", xml))
        assert n_after == n_before, \
            "%s: số bảng đổi %d -> %d dù không pin horizontal" % (
                fid, n_before, n_after)


@check("B3_keep_together_render_properties")
def test_b3_keep_properties():
    """WLAY-003: render gắn keepLines/keepNext/cantSplit đúng chỗ,
    idempotent, không đụng paragraph thường."""
    from tools import docx_render as dr
    # (a) cụm đơn 1 paragraph title+br+instr
    p_sig = ('<w:p><w:r><w:t xml:space="preserve">NGƯỜI NỘP</w:t><w:br/>'
             "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p>")
    p_plain = "<w:p><w:r><w:t>Nội dung thường</w:t></w:r></w:p>"
    p_tbl = (
        "<w:tbl><w:tblPr/><w:tblGrid>"
        '<w:gridCol w:w="4000"/><w:gridCol w:w="4000"/></w:tblGrid>'
        "<w:tr><w:tc><w:tcPr><w:tcW w:w=\"4000\"/></w:tcPr>"
        "<w:p><w:r><w:t>NGƯỜI NỘP</w:t><w:br/>"
        "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:tcPr><w:tcW w:w=\"4000\"/></w:tcPr>"
        "<w:p><w:r><w:t>NGƯỜI NHẬN</w:t><w:br/>"
        "<w:t>(Ký và ghi họ tên)</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>")
    src = _write_min_docx(TEST_OUT / "b3_src.docx",
                          [p_plain, p_sig, p_plain, p_tbl])
    out1 = dr.render(src, {})
    out2 = dr.render(src, {})
    assert out1 == out2, "render không idempotent (2 lần khác bytes)"
    xml = _docx_xml(out1)
    # cụm đơn: keepLines trên đúng 1 paragraph chứa instruction
    sig_paras = [p for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
                 if "(Ký và ghi họ tên)" in p and "NGƯỜI NỘP" in p]
    body_sig = [p for p in sig_paras if "<w:tbl" not in p
                and "<w:trPr" not in p]
    assert body_sig and all("<w:keepLines/>" in p for p in body_sig), \
        "paragraph instruction ký thiếu keepLines"
    # paragraph thường KHÔNG bị gắn property
    plain = [p for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
             if "Nội dung thường" in p]
    assert plain and all("<w:keepLines" not in p and "<w:keepNext" not in p
                         for p in plain), "paragraph thường bị gắn keep flag"
    # bảng ký: cantSplit
    assert "<w:cantSplit/>" in xml, "hàng bảng ký thiếu cantSplit"
    # (b) cặp title-para + instr-para riêng: title phải keepNext
    p_title = "<w:p><w:r><w:t>NGƯỜI NHẬN</w:t></w:r></w:p>"
    p_instr = "<w:p><w:r><w:t>(Đã ký)</w:t></w:r></w:p>"
    src2 = _write_min_docx(TEST_OUT / "b3_pair.docx", [p_title, p_instr])
    xml2 = _docx_xml(dr.render(src2, {}))
    tpara = [p for p in re.findall(r"<w:p[ >].*?</w:p>", xml2, re.S)
             if ">NGƯỜI NHẬN<" in p]
    assert tpara and "<w:keepNext/>" in tpara[0] \
        and "<w:keepLines/>" in tpara[0], \
        "title para liền trước instruction thiếu keepNext/keepLines"
    ipara = [p for p in re.findall(r"<w:p[ >].*?</w:p>", xml2, re.S)
             if "(Đã ký)" in p]
    assert ipara and "<w:keepLines/>" in ipara[0], \
        "instruction para thiếu keepLines"


@check("B4_m15_write_space_xml_and_pdf")
def test_b4_write_space():
    """WLAY-004: M15 — XML có spacer exact-height dưới mỗi instruction;
    PDF đo gap >= min_write_gap_pt (40pt) cho TỪNG cụm."""
    from tools import docx_render as dr
    from tools.phase5_fixtures import ValueFactory, build_fixture
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))
    blocks = json.loads((BLOCKS_DIR / "PLI_M15.json").read_text(
        encoding="utf-8"))
    data = build_fixture("PLI_M15", maps["PLI_M15"], "valid-full",
                         blocks, ValueFactory())
    xml = _docx_xml(dr.render(ROOT / "app" / maps["PLI_M15"]["template"],
                              data))
    spacers = [int(m) for m in re.findall(
        r'w:line="(\d+)" w:lineRule="exact"', xml)]
    assert len(spacers) >= 2, \
        "M15 cần spacer vùng viết cho >=2 cụm, thấy %r" % (spacers,)
    # PDF measure qua đường production
    out_root = TEST_OUT / "b4_export"
    import shutil
    if out_root.exists():
        shutil.rmtree(out_root)
    dirs = _export_subset(["PLI_M15"], ["valid-full"], out_root)
    import fitz  # pymupdf
    gaps = []
    for d in dirs:
        pdf = next(Path(d).glob("PLI_M15.pdf"))
        doc = fitz.open(str(pdf))
        for page in doc:
            for instr in [l for l in _sig_pdf_lines(page) if l["instr"]]:
                below = [l for l in _sig_pdf_lines(page)
                         if l["y0"] > instr["y1"] + 2
                         and not (l["x1"] < instr["x0"] - 60
                                  or l["x0"] > instr["x1"] + 60)
                         and not (l["title"] or l["instr"])]
                if below:
                    gaps.append(
                        min(l["y0"] for l in below) - instr["y1"])
        doc.close()
    assert gaps, "không đo được gap nào dưới instruction M15"
    for g in gaps:
        assert g >= 40.0, \
            "gap vùng viết M15 = %.1fpt < min_write_gap_pt 40" % g


@check("B5_no_orphan_split_signature_page")
def test_b5_orphan():
    """WLAY-009 policy: trang thưa/trắng chứa instruction ký KHÔNG có title
    cùng trang = lỗi orphan-split. Đo subset đại diện qua export production.
    Trang chỉ chứa KHỐI ký HOÀN CHỈNH (title+instr) khi trang trước đầy là
    pagination hợp lệ — không phải lỗi (khối còn nguyên vẹn)."""
    form_ids = ["PLI_M09", "PLII_M20", "PLII_M25", "PLI_M70", "PLI_M15"]
    out_root = TEST_OUT / "b5_export"
    import shutil
    if out_root.exists():
        shutil.rmtree(out_root)
    dirs = _export_subset(form_ids,
                          ["long-boundary", "empty-paper"], out_root)
    import fitz  # pymupdf
    orphans: list[str] = []
    pages_seen = 0
    for d in dirs:
        for pdf_path in sorted(Path(d).glob("*.pdf")):
            fid = pdf_path.stem
            doc = fitz.open(str(pdf_path))
            for pno in range(doc.page_count):
                page = doc[pno]
                chars = len(re.sub(r"\s+", "", page.get_text("text")))
                if chars >= 120:
                    continue  # trang đủ nội dung — không phải orphan
                pages_seen += 1
                lines = _sig_pdf_lines(page)
                has_instr = any(l["instr"] for l in lines)
                has_title = any(l["title"] for l in lines)
                if has_instr and not has_title:
                    orphans.append(
                        "%s p%d: instruction ký không có title cùng trang"
                        " (chars=%d)" % (fid, pno + 1, chars))
            doc.close()
    assert pages_seen > 0, "subset không có trang thưa nào để đo"
    assert not orphans, "orphan-split signature page: %r" % (orphans,)


def main() -> int:
    test_census_registry()
    test_b2_m70_table()
    test_b2_no_collateral()
    test_b3_keep_properties()
    test_b4_write_space()
    test_b5_orphan()
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
