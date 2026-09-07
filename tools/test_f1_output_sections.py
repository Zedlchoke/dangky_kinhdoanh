# -*- coding: utf-8 -*-
"""Lane F1-OUT — test 11 section OUTPUT_ONLY (O1) cho 9 mẫu publication.

Base e268038. Chỉ ĐỌC app_web/**; generator chạy trong SANDBOX tmp
(monkeypatch build_form_maps.ROOT / OUT_TPL / OUT_DATA / FORM_SPECS_DIR — cùng
kỹ thuật tools/test_w1_publication_specs.py), KHÔNG đụng generated artifacts.

Các section thuộc O1 OUTPUT_ONLY (docs/owner_decision_packet_v7.md mục O1):
  PLI_M52/kung... (xem SECTIONS) — 11 section / 9 form.

Mỗi section kiểm:
  [SPEC]   file tồn tại, entry duy nhất, kind output-table, không blocked;
  [LOAD]   loader thật nhận spec, grid.cells chuẩn hoá đúng shape;
  [BOUND]  anchor khớp ĐÚNG 1 paragraph nguồn; drop_until khớp sau anchor;
           mỗi drop pattern chạm >=1 paragraph trong vùng [anchor, drop_until);
  [BUILD]  template sandbox có bảng đúng shape + inputs đăng ký rỗng;
  [BLOCKS] converter ghép section, mirror run đúng key tại đúng ô, KHÔNG có
           input run nào trong lưới; lưới trống pháp định không tự sinh mirror;
  [EXPORT] docx_render: draft trống -> không token sót; có dữ liệu canonical
           (payload lồng nhau như collect_from_map) -> giá trị đổ vào ô mirror.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import docx                                    # noqa: E402

from tools import build_form_maps as bfm       # noqa: E402
from tools import docx_to_blocks as dxtb       # noqa: E402
from tools import docx_render                  # noqa: E402

GROUP_DIR = ROOT / "tools" / "form_specs" / "publication"

# (form_id, section_id, source_dir) — source_dir = thư mục find_source chọn.
SECTIONS = [
    ("PLI_M52", "khung_ra_soat_4_nhom", "05_cong_bo_cung_cap_thong_tin"),
    ("PLI_M56", "cn_vppd_ddkd_tiep_tuc_truoc_han",
     "04_tam_ngung_cham_dut_giai_the"),
    ("PLI_M63", "dia_diem_truc_thuoc_bi_thu_hoi",
     "03_chi_nhanh_van_phong_dai_dien_dia_diem"),
    ("PLI_M66", "don_vi_dang_lam_thu_tuc_cham_dut",
     "04_tam_ngung_cham_dut_giai_the"),
    ("PLI_M66", "ddkd_truc_thuoc_dang_cham_dut",
     "04_tam_ngung_cham_dut_giai_the"),
    ("PLI_M67", "don_vi_cham_dut_sau_day",
     "03_chi_nhanh_van_phong_dai_dien_dia_diem"),
    ("PLI_M68", "don_vi_cham_dut_khi_doanh_nghiep_giai_the",
     "04_tam_ngung_cham_dut_giai_the"),
    ("PLI_M70", "ho_so_bao_gom", "03_chi_nhanh_van_phong_dai_dien_dia_diem"),
    ("PLI_M71", "ho_so_bao_gom_online",
     "03_chi_nhanh_van_phong_dai_dien_dia_diem"),
    ("PLI_M75", "cn_vppd_ddkd_khoi_phuc", "04_tam_ngung_cham_dut_giai_the"),
    ("PLI_M75", "ddkd_truc_thuoc_khoi_phuc", "04_tam_ngung_cham_dut_giai_the"),
]

FORM_IDS = sorted({fid for fid, _sid, _dir in SECTIONS})


def raw_spec(fid: str) -> dict:
    return json.loads((GROUP_DIR / ("%s.json" % fid)).read_text(
        encoding="utf-8-sig"))


def raw_entry(fid: str, sid: str) -> dict:
    hits = [t for t in raw_spec(fid)["tables"]
            if (t.get("spec") or {}).get("id") == sid]
    assert len(hits) == 1, "%s/%s: entry không duy nhất" % (fid, sid)
    return hits[0]


def expected_mirrors(fid: str, sid: str) -> list:
    """[(r, c, key)] từ grid.cells của spec (nguồn chân lý duy nhất)."""
    out = []
    cells = raw_entry(fid, sid)["spec"]["grid"].get("cells") or []
    for ri, row in enumerate(cells):
        for ci, cell in enumerate(row):
            if cell and cell.get("mirror"):
                out.append((ri, ci, cell["mirror"]))
    return out


def real_source(fid: str) -> Path:
    src_dir = next(d for f, _s, d in SECTIONS if f == fid)
    return next(pth for pth in sorted((ROOT / src_dir).glob("*.docx"))
                if bfm.parse_form_id(pth)[0] == fid)


# ---------------------------------------------------------------------------
# Sandbox dựng MỘT lần cho cả module; xoá ở tearDownModule.
# ---------------------------------------------------------------------------

_SBX: dict = {"paths": None, "metas": {}, "blocks": {}, "tpls": {}}


def _build_sandbox() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="f1out_spec_"))
    paths = {"root": tmp / "repo", "specs": tmp / "form_specs",
             "templates": tmp / "templates", "data": tmp / "data"}
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    saved = {"ROOT": bfm.ROOT, "OUT_TPL": bfm.OUT_TPL,
             "OUT_DATA": bfm.OUT_DATA, "FORM_SPECS_DIR": bfm.FORM_SPECS_DIR}
    bfm.ROOT = paths["root"]
    bfm.OUT_TPL = paths["templates"]
    bfm.OUT_DATA = paths["data"]
    bfm.FORM_SPECS_DIR = paths["specs"]
    bfm._form_spec_cache.clear()
    try:
        titles = {}
        for fid in FORM_IDS:
            src = real_source(fid)
            src_dir = src.parent.name
            dst = paths["root"] / src_dir
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / src.name)
            group = paths["specs"] / "publication"
            group.mkdir(parents=True, exist_ok=True)
            (group / ("%s.json" % fid)).write_text(
                json.dumps(raw_spec(fid), ensure_ascii=False, indent=1),
                encoding="utf-8")
            mau = int(bfm.parse_form_id(src)[2])
            titles[fid] = {"Phu luc I|%d" % mau: "DEMO %s" % fid}
        for fid in FORM_IDS:
            source = bfm.find_source(fid)
            assert source is not None, "%s: find_source trống" % fid
            meta, _unmatched = bfm.process_form(source, titles[fid], None)
            bfm.write_maps({fid: meta})
            tpl = bfm.OUT_TPL / ("%s.docx" % fid)
            assert tpl.exists(), "%s: chưa ghi template sandbox" % fid
            _SBX["metas"][fid] = meta
            _SBX["tpls"][fid] = tpl
            _SBX["blocks"][fid] = dxtb.convert_document(
                docx.Document(str(tpl)), fid, meta.get("ten_mau", ""),
                overrides={}, footnotes={},
                section_specs=meta.get("section_specs"))
        _SBX["paths"] = tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    finally:
        bfm.ROOT = saved["ROOT"]
        bfm.OUT_TPL = saved["OUT_TPL"]
        bfm.OUT_DATA = saved["OUT_DATA"]
        bfm.FORM_SPECS_DIR = saved["FORM_SPECS_DIR"]
        bfm._form_spec_cache.clear()


def setUpModule():
    _build_sandbox()


def tearDownModule():
    if _SBX["paths"] is not None:
        shutil.rmtree(_SBX["paths"], ignore_errors=True)
        _SBX["paths"] = None


def _para_folds(path: Path) -> list:
    doc = docx.Document(str(path))
    return [bfm._para_folded(p) for p in bfm._body_paragraphs(doc)]


def _cell_runs(cell: dict) -> list:
    return [r for r in cell.get("runs", []) if isinstance(r, dict)]


def _section_spec(fid: str, sid: str) -> dict:
    return next(s for s in _SBX["metas"][fid]["section_specs"]
                if s["section_id"] == sid)


def _find_output_table(blocks_doc: dict, spec: dict):
    """Tìm lại block bảng khớp labels của section (cùng thuật toán signature
    với converter _find_output_grid_block)."""
    grid = spec["grid"]
    labels = grid.get("labels") or []
    matrix = bool(labels) and all(isinstance(x, list) for x in labels)
    horizontal = (not matrix and int(grid.get("rows", 0) or 0) == 1
                  and int(grid.get("cols", 1)) > 1
                  and len(labels) == int(grid["cols"]))

    def fold_txt(x):
        return bfm.fold(re.sub(r"\s+", " ", x or "")).strip()

    rows_txt = []
    for r in (range(1) if horizontal else range(len(labels))):
        if matrix:
            cells = [labels[r][c] if c < len(labels[r]) else ""
                     for c in range(grid["cols"])]
        elif horizontal:
            cells = [labels[c] if c < len(labels) else ""
                     for c in range(grid["cols"])]
        else:
            cells = [labels[r] if (c == 0 and r < len(labels)) else ""
                     for c in range(grid["cols"])]
        rows_txt.append("|".join(fold_txt(x) for x in cells))
    want = "#".join(rows_txt)
    for blk in blocks_doc["blocks"]:
        if blk.get("t") != "table" or not blk.get("rows"):
            continue
        lines = []
        for row in blk["rows"]:
            cells = []
            for cell in row["cells"]:
                cells.append(fold_txt("".join(
                    r.get("text", "") for r in _cell_runs(cell))))
            lines.append("|".join(cells))
        if "#".join(lines) == want:
            return blk
    return None


class F1OutputSections(unittest.TestCase):
    maxDiff = None

    def test_spec_files_exist_and_not_blocked(self):
        for fid, sid, _d in SECTIONS:
            ent = raw_entry(fid, sid)
            ls = ent.get("legal_status") or {}
            self.assertIs(ls.get("blocked"), False,
                          "%s/%s: O1 đã DECIDED, không được khai blocked"
                          % (fid, sid))
            self.assertEqual(ent.get("kind"), "output-table")
            self.assertEqual(ent["spec"]["kind"], "output-table")
            self.assertEqual(ent["spec"].get("section_id"), sid)
            self.assertIn("O1", ls.get("ref") or "",
                          "%s/%s: ref phải truy về O1" % (fid, sid))

    def test_loader_accepts_specs(self):
        for fid in FORM_IDS:
            bfm._form_spec_cache.clear()
            ext = bfm.load_form_spec(fid)
            self.assertIsNotNone(ext)
            for f2, sid, _d in SECTIONS:
                if f2 != fid:
                    continue
                self.assertIn(sid, ext["specs_by_id"],
                              "%s thiếu %s" % (fid, sid))
                norm = ext["specs_by_id"][sid]
                self.assertEqual(norm["kind"], "output-table")
                ent = raw_entry(fid, sid)
                if ent["spec"]["grid"].get("cells") is not None:
                    self.assertIn("cells", norm["grid"])
                    self.assertEqual(len(norm["grid"]["cells"]),
                                     norm["grid"]["rows"])
                    self.assertEqual(len(norm["grid"]["labels"]),
                                     norm["grid"]["rows"])
            bfm._form_spec_cache.clear()

    def test_anchor_unique_and_drops_hit_scope(self):
        for fid, sid, _d in SECTIONS:
            ent = raw_entry(fid, sid)
            folds = _para_folds(real_source(fid))
            ahits = [t for t in folds if re.search(ent["anchor"], t)]
            self.assertEqual(len(ahits), 1,
                             "%s/%s: anchor khớp %d paragraph (mong 1)"
                             % (fid, sid, len(ahits)))
            for pat in ent.get("drop") or []:
                if not ent.get("drop_until"):
                    continue
                start = next(i for i, t in enumerate(folds)
                             if re.search(ent["anchor"], t)) + 1
                end = next((i for i in range(start, len(folds))
                            if re.search(ent["drop_until"], folds[i])), None)
                self.assertIsNotNone(
                    end, "%s/%s: drop_until không khớp sau anchor"
                    % (fid, sid))
                scope = folds[start:end]
                hits = [t for t in scope if re.match(pat, t)]
                self.assertGreaterEqual(
                    len(hits), 1,
                    "%s/%s: drop %r không chạm paragraph nào trong vùng"
                    % (fid, sid, pat))

    def test_template_grid_shape_and_inputs_empty(self):
        for fid, sid, _d in SECTIONS:
            ss = _section_spec(fid, sid)
            self.assertEqual(ss["inputs"], [],
                             "%s/%s: inputs phải rỗng" % (fid, sid))
            blk = _find_output_table(_SBX["blocks"][fid], ss)
            self.assertIsNotNone(
                blk, "%s/%s: không tìm thấy bảng khớp labels" % (fid, sid))
            self.assertEqual(len(blk["rows"]), ss["grid"]["rows"],
                             "%s/%s: sai số hàng" % (fid, sid))
            for row in blk["rows"]:
                width = sum(int(c.get("colspan") or 1) for c in row["cells"])
                self.assertEqual(width, ss["grid"]["cols"],
                                 "%s/%s: sai số cột vật lý" % (fid, sid))
            inputs = [r["input"]["key"]
                      for row in blk["rows"] for cell in row["cells"]
                      for r in _cell_runs(cell) if "input" in r]
            self.assertEqual(inputs, [],
                             "%s/%s: lưới output chứa input %s"
                             % (fid, sid, inputs))

    def test_blocks_mirror_runs_exact_positions(self):
        for fid, sid, _d in SECTIONS:
            wants = expected_mirrors(fid, sid)
            ss = _section_spec(fid, sid)
            blk = _find_output_table(_SBX["blocks"][fid], ss)
            self.assertIsNotNone(blk)
            for (ri, ci, key) in wants:
                cell = blk["rows"][ri]["cells"][ci]
                mirrors = [r["mirror"]["key"] for r in _cell_runs(cell)
                           if "mirror" in r]
                self.assertEqual(mirrors, [key],
                                 "%s/%s: ô (%d,%d) mirror %s != [%s]"
                                 % (fid, sid, ri, ci, mirrors, key))
                for r in _cell_runs(cell):
                    self.assertNotIn("input", r,
                                     "%s/%s: ô mirror (%d,%d) còn input"
                                     % (fid, sid, ri, ci))
            if not wants:
                n_mirrors = sum(
                    1 for row in blk["rows"] for cell in row["cells"]
                    for r in _cell_runs(cell) if "mirror" in r)
                self.assertEqual(
                    n_mirrors, 0,
                    "%s/%s: lưới trống pháp định không được tự sinh mirror"
                    % (fid, sid))

    @staticmethod
    def _render_to_xml(tpl_path: Path, flat_data: dict) -> str:
        def setn(d, k, v):
            cur = d
            parts = k.split(".")
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = v
        data: dict = {}
        for k, v in flat_data.items():
            setn(data, k, v)
        out = docx_render.render(str(tpl_path), data)
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            return z.read("word/document.xml").decode("utf-8")

    def test_export_blank_stays_blank_and_data_fills(self):
        for fid, sid, _d in SECTIONS:
            wants = expected_mirrors(fid, sid)
            if not wants:
                continue
            ss = _section_spec(fid, sid)
            blk = _find_output_table(_SBX["blocks"][fid], ss)
            # blocks: ô mirror KHÔNG mang token kỹ thuật dạng text
            for (ri, ci, _key) in wants:
                text = "".join(r_.get("text", "") for r_ in
                               _cell_runs(blk["rows"][ri]["cells"][ci]))
                self.assertNotIn("{", text,
                                 "%s/%s: ô mirror (%d,%d) còn token"
                                 % (fid, sid, ri, ci))
            # export: draft trống -> KHÔNG token nào sót trong document.xml
            xml_blank = self._render_to_xml(_SBX["tpls"][fid], {})
            body_blank = re.sub(r"<[^>]+>", "", xml_blank)
            self.assertNotIn("{", body_blank,
                             "%s: render draft trống còn token" % fid)
            # export: dữ liệu canonical (payload lồng như collect_from_map)
            # -> giá trị đổ vào đúng ô mirror
            fill = {}
            for (_r, _c, key) in wants:
                fill[key] = "VAL_" + key.replace(".", "_")
            xml_fill = self._render_to_xml(_SBX["tpls"][fid], fill)
            for (_r, _c, key) in wants:
                self.assertIn("VAL_" + key.replace(".", "_"), xml_fill,
                              "%s: giá trị %s không đổ vào ô mirror"
                              % (fid, key))

    def test_runtime_contracts_in_form_domain(self):
        js = (ROOT / "app_web" / "ui" / "form-domain.js").read_text(
            encoding="utf-8")
        for fid, sid, _d in SECTIONS:
            self.assertIn("sectionId: '%s'" % sid, js,
                          "%s thiếu sectionId runtime %s" % (fid, sid))
        # section mới khai outputOnlyTags + inputs rỗng (W1 cũ giữ nguyên shape):
        # chunk của mỗi form = từ key `'<FORM>': {` tới key cấp form kế tiếp.
        for fid in ("PLI_M52", "PLI_M56", "PLI_M63", "PLI_M66", "PLI_M67",
                    "PLI_M68", "PLI_M75"):
            start = js.index("'%s': {" % fid)
            nxt = js.find("\n    '", start + 1)
            chunk = js[start:nxt if nxt > 0 else len(js)]
            self.assertIn("outputOnlyTags", chunk,
                          "%s: spec runtime thiếu outputOnlyTags" % fid)
            self.assertIn("inputs: []", chunk)


if __name__ == "__main__":
    unittest.main(verbosity=2)
