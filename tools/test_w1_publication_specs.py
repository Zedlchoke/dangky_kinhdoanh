# -*- coding: utf-8 -*-
"""Lane W1 — test đăng ký per-form spec cho R2 closure (publication O1/O2).

Base 0cddd7f. Chỉ ĐỌC app_web/** và app/** (registry runtime, manifest,
blocks, form_maps, nguồn DOCX); KHÔNG đụng generated artifacts: mọi lần chạy
generator diễn ra trong SANDBOX tmp (monkeypatch build_form_maps.ROOT /
OUT_TPL / OUT_DATA / FORM_SPECS_DIR giống tools/test_generator_deep_idempotency.py).

Phạm vi mệnh đề:

[W1-SPEC] tools/form_specs/publication/{PLI_M70,PLI_M71}.json tồn tại, hợp lệ
          JSON, không có legal_status.blocked (D6.2=A đã chốt).
[W1-LOAD] Loader thật build_form_maps.load_form_spec() nhận 2 file đó.
[W1-REG]  Validator v1 (_json_spec / _validate_legal_status) pass VÀ khớp 1-1
          FORM_TABLE_CONTRACTS của app_web/ui/form-domain.js (sectionId /
          semanticKey / kind / grid), nhãn phải có thật trong blocks.
[W1-BND]  Trên nguồn thật: anchor khớp paragraph sống sót, mỗi drop pattern
          chạm đúng 1 paragraph cũ; lưới output-table đúng kích thước + nhãn,
          KHÔNG chứa any the input, không in trùng nhãn.
[W1-E2E]  Build gắn form_maps.section_specs đúng shape và converter
          annotate_and_verify_section_specs ghép được section mà không raise.
[W1-IDEM] Generator lần 1 vs lần 2 từ cùng nguồn -> hash template canonical +
          blocks JSON giống hệt.
[W1-GAP]  PLI_M01: hai fixed-matrix already_complete CHƯA có đường đăng ký ở
          schema v1 — test khoá để không ai thêm entry rebuild đốt lại vùng
          đã map chk_khu_* / gd.* / kt.*, và khoá việc chế root key mới.

Chạy: python -X utf8 -m tools.test_w1_publication_specs   (exit 0 = PASS)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document                       # noqa: E402
from docx.oxml.ns import qn                     # noqa: E402

from tools import build_form_maps as bfm        # noqa: E402
from tools import docx_to_blocks as dxtb        # noqa: E402


# ---------------------------------------------------------------------------
# Đầu vào của lane này (chỉ đọc)
# ---------------------------------------------------------------------------
GROUP_DIR = ROOT / "tools" / "form_specs" / "publication"
M01_SPEC = ROOT / "tools" / "form_specs" / "formation" / "PLI_M01.json"
REGISTRY_JS = ROOT / "app_web" / "ui" / "form-domain.js"
MANIFEST = ROOT / "app" / "data" / "table_specs" / "manifest.json"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
SOURCE_DIR = "03_chi_nhanh_van_phong_dai_dien_dia_diem"

SPEC_FORM_IDS = ("PLI_M70", "PLI_M71")
SPEC_FILES = {fid: GROUP_DIR / ("%s.json" % fid) for fid in SPEC_FORM_IDS}
BLOCKS = {fid: ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
          for fid in ("PLI_M70", "PLI_M71", "PLI_M01")}

# Bản sao dự phòng contract registry (chỉ dùng khi môi trường không có node).
# Giá trị SOI TỪ app_web/ui/form-domain.js — không tự chế.
_REGISTRY_FALLBACK = {
    "PLI_M70": {
        "sectionId": "chu_ky_nguoi_nop_nguoi_nhan",
        "semanticKey": "chu_ky_tiep_nhan_ho_so",
        "kind": "output-table",
        "grid": {"rows": 2, "cols": 1, "labels": [
            "NGƯỜI NỘP\n(Ký và ghi họ tên)", "NGƯỜI NHẬN\n(Ký và ghi họ tên)"]},
    },
    "PLI_M71": {
        "sectionId": "chu_ky_co_quan_cap_tinh",
        "semanticKey": "chu_ky_cqb_m71",
        "kind": "output-table",
        "grid": {"rows": 1, "cols": 1,
                 "labels": [["(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)"]]},
    },
}

# Hai fixed-matrix ALREADY_COMPLETE của PLI_M01 theo census manifest
M01_ALREADY = (
    {"section_id": "lua_chon_khu_san_xuat",
     "semantic_key": "lua_chon_khu_san_xuat", "kind": "fixed-matrix"},
    {"section_id": "thue_chi_tieu_6_1_6_9",
     "semantic_key": "chi_tieu_thue_dntn", "kind": "fixed-matrix"},
)


def layout_fold(text: str) -> str:
    """Cùng quy tắc fold với tools/layout_roles.fold."""
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------------------
# Registry runtime (node require app_web/ui/form-domain.js — chỉ ĐỌC)
# ---------------------------------------------------------------------------
def load_runtime_registry() -> dict:
    node = shutil.which("node")
    if not node:
        return dict(_REGISTRY_FALLBACK)
    script = ("var m=require(process.argv[1]);var o={};"
              "Object.keys(m.FORM_TABLE_CONTRACTS||{}).forEach(function(k){"
              "o[k]=(m.FORM_TABLE_CONTRACTS[k].sections||[]).map(function(s){"
              "return {sectionId:s.sectionId,semanticKey:s.semanticKey,"
              "kind:s.kind,spec:s.spec};});});"
              "process.stdout.write(JSON.stringify(o));")
    proc = subprocess.run([node, "-e", script, str(REGISTRY_JS)],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0 or not proc.stdout.strip():
        return dict(_REGISTRY_FALLBACK)
    data = json.loads(proc.stdout)
    for fid in SPEC_FORM_IDS:
        assert fid in data, "registry runtime thiếu %s (soi lại JS)" % fid
    return data


# ===========================================================================
# Sandbox helpers
# ===========================================================================
SBX: dict = {"paths": None, "templates": {}, "metas": {}, "hashes": {}}


def new_sandbox() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="w1_spec_"))
    paths = {"root": tmp / "repo", "specs": tmp / "form_specs",
             "templates": tmp / "templates", "data": tmp / "data"}
    for p in list(paths.values()) + [paths["root"] / SOURCE_DIR]:
        p.mkdir(parents=True, exist_ok=True)
    return paths


def apply_sandbox(paths: dict) -> dict:
    saved = {"ROOT": bfm.ROOT, "OUT_TPL": bfm.OUT_TPL, "OUT_DATA": bfm.OUT_DATA,
             "FORM_SPECS_DIR": bfm.FORM_SPECS_DIR}
    bfm.ROOT = paths["root"]
    bfm.OUT_TPL = paths["templates"]
    bfm.OUT_DATA = paths["data"]
    bfm.FORM_SPECS_DIR = paths["specs"]
    bfm._form_spec_cache.clear()
    return saved


def restore(saved: dict) -> None:
    bfm.ROOT = saved["ROOT"]
    bfm.OUT_TPL = saved["OUT_TPL"]
    bfm.OUT_DATA = saved["OUT_DATA"]
    bfm.FORM_SPECS_DIR = saved["FORM_SPECS_DIR"]
    bfm._form_spec_cache.clear()


def real_source_path(form_id: str) -> Path:
    for path in sorted((ROOT / SOURCE_DIR).glob("*.docx")):
        if bfm.parse_form_id(path)[0] == form_id:
            return path
    raise AssertionError("không tìm thấy nguồn thật của %s trong %s"
                         % (form_id, ROOT / SOURCE_DIR))


def copy_real_source(paths: dict, form_id: str) -> None:
    src = real_source_path(form_id)
    shutil.copy2(src, paths["root"] / SOURCE_DIR / src.name)


def read_raw(fid: str) -> dict:
    return json.loads(SPEC_FILES[fid].read_text(encoding="utf-8-sig"))


def prepare_sandbox(paths: dict, form_ids=SPEC_FORM_IDS) -> None:
    """Copy nguồn thật + spec thật vào sandbox rồi chạy generator 1 lần/mẫu."""
    titles = {}
    for fid in form_ids:
        copy_real_source(paths, fid)
        group = paths["specs"] / "publication"
        group.mkdir(parents=True, exist_ok=True)
        raw = read_raw(fid)
        (group / ("%s.json" % fid)).write_text(
            json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        mau = int(bfm.parse_form_id(real_source_path(fid))[2])
        titles[fid] = mau
    for fid in form_ids:
        run_generation(fid, titles[fid])


def run_generation(form_id: str, mau: int) -> tuple[dict, Path]:
    source = bfm.find_source(form_id)
    assert source is not None, "%s: find_source trống trong sandbox" % form_id
    meta, _unmatched = bfm.process_form(
        source, {"Phu luc I|%d" % mau: "DEMO %s" % form_id}, None)
    bfm.write_maps({form_id: meta})
    tpl = bfm.OUT_TPL / ("%s.docx" % form_id)
    assert tpl.exists(), "generator chưa ghi template cho %s" % form_id
    SBX["metas"][form_id] = meta
    return meta, tpl


def convert_blocks(template: Path, meta: dict) -> dict:
    doc = Document(str(template))
    return dxtb.convert_document(doc, meta["id"], meta.get("ten_mau", ""),
                                 overrides={}, footnotes={},
                                 section_specs=meta.get("section_specs"))


# ---------------------------------------------------------------------------
# Soi cấu trúc DOCX cùng ngữ nghĩa với engine (_body_paragraphs / w:tbl)
# ---------------------------------------------------------------------------
def body_para_folds(docx_path: Path) -> list[str]:
    """Fold của mọi PARAGRAPH con trực tiếp của body — dùng NGUYÊN hàm
    bfm._body_paragraphs + bfm._para_folded (para.text có '\n' cho w:br, còn
    duyệt w:t thuần thì mất) để test khớp chính xác ngữ nghĩa anchor/drop."""
    doc = Document(str(docx_path))
    return [bfm._para_folded(p) for p in bfm._body_paragraphs(doc)]


def collect_all_strings(obj) -> list[str]:
    """Text của mỗi "leaf" có runs (paragraph / ô bảng) — nối đúng thứ tự run
    để một nhãn tách thành nhiều run (vd 'NGƯỜI NỘP\\n' + '(' + italic 'Ký và
    ghi họ tên' + ')') vẫn được soi như một chuỗi liền."""
    out: list[str] = []
    if isinstance(obj, dict):
        runs = obj.get("runs")
        if isinstance(runs, list):
            out.append("".join(
                r.get("text", "") if isinstance(r, dict) else str(r)
                for r in runs))
        for v in obj.values():
            out.extend(collect_all_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(collect_all_strings(v))
    return out


def cell_text(tc_el) -> str:
    """Text của một w:tc: w:t + '\n' cho w:br/w:cr (giống Paragraph.text của
    python-docx mà engine dùng để khớp nhãn)."""
    parts = []
    for node in tc_el.iter():
        if node.tag == qn("w:t"):
            parts.append(node.text or "")
        elif node.tag in (qn("w:br"), qn("w:cr")):
            parts.append("\n")
    return "".join(parts)


def tables_shape(docx_path: Path) -> list[tuple[int, int, list[list[str]]]]:
    """[(rows, ncols(gridCol), [[cell_text]])] cho mọi w:tbl con trực tiếp."""
    doc = Document(str(docx_path))
    shapes = []
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:tbl"):
            continue
        grid = child.find(qn("w:tblGrid"))
        ncols = len([el for el in grid.iterchildren()
                     if el.tag == qn("w:gridCol")]) if grid is not None else 0
        rows_txt = []
        for tr in child.tr_lst:
            row_txt = [re.sub(r"\s+", " ", cell_text(tc)).strip()
                       for tc in tr.iterchildren() if tc.tag == qn("w:tc")]
            rows_txt.append(row_txt)
        shapes.append((len(rows_txt), ncols, rows_txt))
    return shapes


def canon_element(el) -> dict:
    tag = el.tag.split("}")[-1]
    return {"tag": tag,
            "attrs": sorted((k.split("}")[-1], v) for k, v in el.attrib.items()),
            "text": el.text or "",
            "children": [canon_element(child) for child in el]}


def template_hash(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as zf:
        raw = zf.read("word/document.xml")
    blob = json.dumps(canon_element(ET.fromstring(raw)), sort_keys=True,
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def blocks_hash(data: dict) -> str:
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def flat_labels(grid: dict) -> list[str]:
    out = []
    for lab in grid["labels"]:
        out.extend(lab if isinstance(lab, list) else [lab])
    return out


# ===========================================================================
# Harness @check
# ===========================================================================
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


# ===========================================================================
# Mệnh đề
# ===========================================================================
@check("[W1-SPEC] file publication ton tai, JSON hop le, KHONG blocked (D6.2=A)")
def spec_files_valid():
    for fid in SPEC_FORM_IDS:
        path = SPEC_FILES[fid]
        assert path.exists(), "thiếu file spec %s" % path
        raw = read_raw(fid)
        assert raw["form_id"] == fid, \
            "%s: form_id=%r không khớp tên file" % (path.name, raw["form_id"])
        assert raw.get("group") == "publication", \
            "%s: group=%r (kỳ vọng publication)" % (path.name, raw.get("group"))
        note = raw.get("note") or ""
        assert "app/data/blocks/" in note, \
            "%s: note thiếu tham chiếu evidence blocks" % fid
        assert "manifest.json" in note, \
            "%s: note thiếu tham chiếu census manifest" % fid
        assert len(raw["tables"]) == 1, \
            "%s: kỳ vọng đúng 1 entry output-table" % fid
        for ent in raw["tables"]:
            ls = ent.get("legal_status") or {}
            assert ls.get("blocked") is False, (
                "%s/%s: legal_status.blocked=%r — D6.2=A đã DECIDED, section "
                "output_only KHÔNG được khai blocked" % (
                    fid, ent["spec"]["id"], ls.get("blocked")))
            assert "D6.2" in (ls.get("ref") or ""), \
                "%s: legal_status.ref phải truy về D6.2" % fid
            assert ent.get("anchor"), "%s: entry thiếu anchor" % fid


@check("[W1-LOAD] loader build_form_maps chap nhan 2 file spec moi")
def loader_accepts_specs():
    for fid in SPEC_FORM_IDS:
        bfm._form_spec_cache.clear()
        ext = bfm.load_form_spec(fid)
        assert ext is not None, "%s: loader trả None (không thấy file)" % fid
        assert len(ext["entries"]) == 1, "%s: kỳ vọng đúng 1 entry" % fid
        ent = ext["entries"][0]
        spec = ext["specs_by_id"][ent["spec"]]
        assert ent["_blocked"] is False, "%s: entry đang BLOCKED" % fid
        assert spec["kind"] == "output-table", "%s: kind=%r" % (fid, spec["kind"])
        bfm._form_spec_cache.clear()


@check("[W1-REG] validator v1 pass + khop 1-1 FORM_TABLE_CONTRACTS runtime")
def registry_one_to_one(registry):
    block_blob = {}
    for fid in SPEC_FORM_IDS:
        blk = json.loads(BLOCKS[fid].read_text(encoding="utf-8"))
        block_blob[fid] = re.sub(
            r"\s+", " ", "\n".join(collect_all_strings(blk))).strip()

    for fid in SPEC_FORM_IDS:
        entry = read_raw(fid)["tables"][0]
        norm = bfm._json_spec(entry["spec"], fid)           # validator v1
        bfm._validate_legal_status(entry, fid, norm["id"])   # tầng entry
        sections = registry.get(fid) or []
        assert len(sections) == 1, \
            "%s: registry có %d section, kỳ vọng 1" % (fid, len(sections))
        sec = sections[0]
        assert norm["kind"] == sec["kind"], "%s: kind lệch registry" % fid
        assert norm["semantic_key"] == sec["semanticKey"], \
            "%s: semantic_key %r != registry %r" % (fid, norm["semantic_key"],
                                                    sec["semanticKey"])
        want_sid = sec.get("spec", {}).get("section_id") or sec["sectionId"]
        assert norm["section_id"] == want_sid, \
            "%s: section_id %r != registry %r" % (fid, norm["section_id"],
                                                  want_sid)
        assert norm["grid"] == sec["spec"]["grid"], (
            "%s: grid lệch registry:\n  spec : %r\n  regis: %r"
            % (fid, norm["grid"], sec["spec"]["grid"]))
        assert sec["spec"].get("inputs") == [], \
            "%s: registry phải giữ inputs=[] cho output-table" % fid
        # nhãn phải là text THẬT của mẫu (đã fold, dồn whitespace) — không bia
        blob_ws = re.sub(r"\s+", " ", block_blob[fid])
        for lab in flat_labels(norm["grid"]):
            probe = norm_ws(lab)
            assert probe in blob_ws, \
                "%s: label %r không có trong blocks thật" % (fid, lab)


@check("[W1-BND] anchor/drop cham dung 1 paragraph cu, khong in trung nhan")
def boundary_precise():
    from docx import Document as Doc
    for fid in SPEC_FORM_IDS:
        raw = read_raw(fid)
        ent = raw["tables"][0]
        folds_src = body_para_folds(real_source_path(fid))

        # mỗi drop pattern phải chạm ĐÚNG 1 paragraph vùng lưới cũ
        for pat in ent.get("drop") or []:
            hits = [t for t in folds_src if re.match(pat, t)]
            assert len(hits) == 1, \
                "%s: drop %r chạm %d paragraph (%r)" % (fid, pat, len(hits),
                                                        hits[:4])

        # anchor phải khớp nguồn thật và KHÔNG bị chính entry đó xoá
        # (anchor bị drop => bảng sẽ KHÔNG bao giờ được chèn)
        hits_anchor = [t for t in folds_src if re.search(ent["anchor"], t)]
        assert hits_anchor, "%s: anchor %r không khớp nguồn thật" % (
            fid, ent["anchor"])
        for pat in ent.get("drop") or []:
            assert all(not re.match(pat, t) for t in hits_anchor), \
                "%s: anchor cũng khớp drop pattern -> rebuild sẽ skip insert" % fid

        tpl = SBX["templates"][fid]
        folds_tpl = body_para_folds(tpl)
        assert any(re.search(ent["anchor"], t) for t in folds_tpl), \
            "%s: mất điểm neo sau rebuild" % fid
        for pat in ent.get("drop") or []:
            left = [t for t in folds_tpl if re.match(pat, t)]
            assert not left, \
                "%s: paragraph cũ vẫn còn ở dạng rời (in trùng): %r" % (fid, left)

        expect = _REGISTRY_FALLBACK[fid]["grid"]
        shapes = tables_shape(tpl)
        assert len(shapes) == 1, "%s: kỳ vọng đúng 1 w:tbl, thấy %d" % (
            fid, len(shapes))
        rows, cols, cell_texts = shapes[0]
        assert (rows, cols) == (expect["rows"], expect["cols"]), \
            "%s: lưới %dx%d != %dx%d" % (fid, rows, cols, expect["rows"],
                                         expect["cols"])
        joined = "\n".join("\n".join(r) for r in cell_texts)
        for lab in flat_labels(expect):
            assert layout_fold(norm_ws(lab)) in layout_fold(joined), \
                "%s: thiếu nhãn %r trong lưới mới" % (fid, norm_ws(lab))
        # lưới chỉ để in/ký: không được có bất kỳ the nào
        tpl_doc = Doc(str(tpl))
        for tbl in tpl_doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        assert "{" not in para.text, \
                            "%s: lưới output-table không được có the input: %r" \
                            % (fid, para.text)


@check("[W1-E2E] build gan form_maps.section_specs + converter verify pass")
def end_to_end_checks():
    for fid in SPEC_FORM_IDS:
        meta = SBX["metas"][fid]
        specs = meta.get("section_specs") or []
        assert len(specs) == 1, \
            "%s: form_maps thiếu section_specs (%r)" % (fid, specs)
        ss = specs[0]
        assert ss["kind"] == "output-table", "%s: kind=%r" % (fid, ss["kind"])
        assert ss["inputs"] == [], "%s: inputs phải rỗng" % fid
        norm = bfm._json_spec(read_raw(fid)["tables"][0]["spec"], fid)
        assert ss["semantic_key"] == norm["semantic_key"], \
            "%s: semantic_key lệch giữa form_maps và spec" % fid
        assert ss["section_id"] == norm["section_id"], \
            "%s: section_id lệch giữa form_maps và spec" % fid
        assert ss["grid"] == norm["grid"], \
            "%s: grid form_maps khác spec khai báo" % fid
        doc_json = convert_blocks(SBX["templates"][fid], meta)
        matched = dxtb.annotate_and_verify_section_specs(
            doc_json["blocks"], meta["section_specs"])
        assert matched == 1, "%s: converter ghép %d section (kỳ vọng 1)" % (
            fid, matched)


@check("[W1-IDEM] lan 1 == lan 2 (hash template canonical + blocks JSON)")
def idempotency_checks():
    titles_by_mau = {}
    for fid in SPEC_FORM_IDS:
        titles_by_mau[fid] = int(bfm.parse_form_id(real_source_path(fid))[2])
    for fid in SPEC_FORM_IDS:
        _meta, tpl = run_generation(fid, titles_by_mau[fid])
        first_tpl = template_hash(tpl)
        first_blk = blocks_hash(convert_blocks(tpl, SBX["metas"][fid]))
        bfm._form_spec_cache.clear()
        _meta2, tpl2 = run_generation(fid, titles_by_mau[fid])
        second_tpl = template_hash(tpl2)
        second_blk = blocks_hash(convert_blocks(tpl2, SBX["metas"][fid]))
        assert first_tpl == second_tpl, (
            "%s: hash template đổi giữa 2 lần chạy (%s… vs %s…)"
            % (fid, first_tpl[:12], second_tpl[:12]))
        assert first_blk == second_blk, \
            "%s: hash blocks đổi giữa 2 lần chạy" % fid


@check("[W1-GAP] PLI_M01 already_complete CHUA co duong dang ky v1")
def pli_m01_gap_guard():
    raw = json.loads(M01_SPEC.read_text(encoding="utf-8-sig"))
    # [Lead sync P2C 1691728] guard thu hẹp theo SECTION: ý đồ gốc là bảo vệ
    # vùng ĐÃ map (chk_khu_* / gd.* / kt.*) khỏi bị rebuild đè — không phải cấm
    # mọi entry kind bảng. Entry fixed-matrix `tai_san_gop_von_von_dau_tu`
    # (D1.1=A/D1.2=B, lane P2C) nhắm section missing_grid nên HỢP LỆ.
    GUARDED_ALREADY_MAPPED = {"lua_chon_khu_san_xuat", "thue_chi_tieu_6_1_6_9"}
    for e in raw["tables"]:
        sid = ((e.get("spec") or {}).get("id")) or (e.get("id") or "")
        kind = (e.get("spec") or {}).get("kind") or e.get("kind") or "list"
        if sid in GUARDED_ALREADY_MAPPED:
            assert kind == "list", (
                "PLI_M01 section đã-map %s không được rebuild (kind=%r) — "
                "sẽ đè binding chk_khu_* / gd.* / kt. của census" % (sid, kind))
        else:
            assert kind != "list" or sid == "ds_nganh", (
                "PLI_M01 entry %s kind=%r: entry bảng phải khai kind rõ "
                "(fixed-matrix/…) trừ entry ngành legacy" % (sid, kind))
    forms = json.loads(MANIFEST.read_text(encoding="utf-8"))["forms"]
    m01 = [f for f in forms if f["form_id"] == "PLI_M01"][0]
    by_sid = {s["section_id"]: s for s in m01["sections"]}
    for want in M01_ALREADY:
        sec = by_sid.get(want["section_id"])
        assert sec is not None, "manifest thiếu %s" % want["section_id"]
        assert sec["kind"] == want["kind"], \
            "%s: manifest kind=%r" % (want["section_id"], sec["kind"])
        assert sec["status"] == "already_complete", \
            "%s: status=%r (kỳ vọng already_complete)" % (want["section_id"],
                                                           sec["status"])
        assert sec["semantic_key"] == want["semantic_key"], \
            "%s: semantic_key=%r" % (want["section_id"], sec["semantic_key"])
    # vùng đó ĐÃ có binding thật -> không cần rebuild để sinh input
    blk_blob = BLOCKS["PLI_M01"].read_text(encoding="utf-8")
    blk_keys = set(re.findall(r'"key"\s*:\s*"([^"]+)"', blk_blob))
    for need in ("chk_khu_cong_nghiep", "chk_khu_che_xuat", "chk_khu_kinh_te",
                 "chk_khu_cong_nghe_cao"):
        assert need in blk_keys, "blocks PLI_M01 thiếu ô đã map %s" % need
    fm = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    fields = {f["key"] for f in fm["PLI_M01"]["fields"]}
    assert {"ap_dung_tu", "so_lao_dong"} <= fields, \
        "form_maps PLI_M01 mất mapping vùng thuế"
    assert any(k.startswith(("gd.", "kt.")) for k in fields), \
        "form_maps PLI_M01 mất mapping gd./kt."


@check("[W1-GAP] root key ngoai hop dong v1 BI LOADER chan (khong che mechanism)")
def unknown_root_key_rejected():
    bad = {"form_id": "PLI_W1_NEG",
           "already_mapped_sections": [{"section_id":
                                        "lua_chon_khu_san_xuat",
                                        "semantic_key":
                                        "lua_chon_khu_san_xuat"}],
           "tables": []}
    paths = new_sandbox()
    saved = apply_sandbox(paths)
    try:
        group = paths["specs"] / "formation"
        group.mkdir(parents=True, exist_ok=True)
        (group / "PLI_W1_NEG.json").write_text(
            json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")
        raised = None
        try:
            bfm.load_form_spec("PLI_W1_NEG")
        except ValueError as exc:
            raised = exc
        assert isinstance(raised, ValueError), (
            "loader nuốt im lặng root key ngoài hợp đồng v1 ('%s') -> một lane "
            "khác có thể CHE mechanism mới mà không ai biết" %
            "already_mapped_sections")
        assert "root" in str(raised), "lỗi sai nguồn gốc: %r" % raised
    finally:
        restore(saved)
        shutil.rmtree(paths["root"].parent, ignore_errors=True)


# ===========================================================================
# main
# ===========================================================================
def main() -> int:
    registry = load_runtime_registry()

    # -- các mệnh đề đọc production paths (chỉ đọc) --------------------------
    spec_files_valid()
    loader_accepts_specs()
    registry_one_to_one(registry)
    pli_m01_gap_guard()

    # -- các mệnh đề chạy generator trên NGUỒN THẬT trong sandbox -------------
    paths = new_sandbox()
    saved = apply_sandbox(paths)
    try:
        SBX["paths"] = paths
        prepare_sandbox(paths)
        for fid in SPEC_FORM_IDS:
            SBX["templates"][fid] = paths["templates"] / ("%s.docx" % fid)
            assert SBX["metas"].get(fid), "%s: chưa có meta sau lần build 1" % fid
        boundary_precise()
        idempotency_checks()
        end_to_end_checks()
    finally:
        SBX.update({"templates": {}, "metas": {}, "hashes": {}, "paths": None})
        restore(saved)
        shutil.rmtree(paths["root"].parent, ignore_errors=True)

    unknown_root_key_rejected()

    print("")
    total = len(_results)
    passed = sum(1 for ok, _ in _results if ok)
    for ok, name in _results:
        if not ok:
            print("DETAIL FAIL -> %s" % name)
    print("KET QUA W1 spec registration: %d/%d check PASS%s"
          % (passed, total, "" if passed == total else " -> FAIL"))
    return 0 if passed == total else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
