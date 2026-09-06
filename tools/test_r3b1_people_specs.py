#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_r3b1_people_specs.py — Lane R3B1 (people/ownership tables, sửa audit V1).

Mệnh đề kiểm chứng cho đợt spec rebuild các bảng người/tài sản bị dẹt thành
text glue (audit Wave D liệt kê), theo docs/decision_registry.md packet D2:

  [EVD]      evidence table: mọi bảng auditor liệt kê phải tìm thấy trong census
             manifest (app/data/table_specs/manifest.json) với đúng kind /
             semantic_key / status + evidence heading; bảng BLOCKED cũng phải
             có nguồn ghi rõ (không suy diễn).
  [SPEC]     3 file spec của lane (core/PLI_M02.json, change/PLI_M12.json,
             change/PLI_M15.json) qua validator v1 của tools/build_form_maps.py;
             shape nested-grid (width, loop, chu_ky outputOnly, discriminator).
  [ANCHOR]   anchor regex khớp ĐÚNG 1 paragraph đã fold trong blocks HIỆN TẠI và
             trong template (khớp vùng audit chỉ ra), trim gắn đúng paragraph
             glue và keep_from nằm thật trong raw text.
  [SANDBOX]  rebuild THẬT trên sandbox tmp (OUT_TPL/OUT_DATA ghi vào temp,
             KHÔNG đụng app/templates / app/data): dựng bảng nested-grid,
             convert về blocks kèm annotate_and_verify_section_specs, kiểm tra
             glue đã biến mất và chuỗi pháp lý dính kèm được GIỮ.
  [BLOCKED]  những bảng KHÔNG đủ quyết định/nguồn thì PHẢI KHÔNG có spec:
             PLII_M02 (2 lưới thành viên hộ gia đình — file spec bị test
             contract lane khác ghim tập occurrence_id), PLI_M09 (nhiễm nguồn,
             D3 chưa đối chiếu bản gốc), PLI_M72 (N2-N5 — file spec bị ghim
             len(entries)==1 + loader từ chối root key `section_cond`).

Chạy: python3 -X utf8 -m tools.test_r3b1_people_specs   (từ root repo)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import docx
from docx.text.paragraph import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.build_form_maps as bfm          # noqa: E402
import tools.docx_to_blocks as dxtb          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "app" / "data" / "table_specs" / "manifest.json"
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(*args, **kw):
            try:
                fn(*args, **kw)
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    """Chung quy tắc với build_form_maps.fold (thường, bỏ dấu, đ->d)."""
    s = re.sub(r"\s+", " ", text or "").strip()
    nfkd = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace(
        "đ", "d")


def blocks_json(form_id: str) -> dict:
    return json.loads((BLOCKS_DIR / ("%s.json" % form_id)).read_text(
        encoding="utf-8"))


def block_texts(blocks: list[dict]) -> list[str]:
    out = []
    for b in blocks:
        runs = b.get("runs") or []
        txt = "".join(str(r.get("text", "")) for r in runs)
        out.append(txt if b.get("t") != "table" else "[TBL]")
    return out


def block_folds(form_id: str) -> list[str]:
    return [fold(t) for t in block_texts(blocks_json(form_id)["blocks"])]


def template_folds(form_id: str) -> list[str]:
    doc = docx.Document(str(ROOT / "app" / "templates" / ("%s.docx" % form_id)))
    out = []
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            out.append(fold(Paragraph(el, doc).text))
        elif el.tag.endswith("}tbl"):
            out.append("[TBL]")
    return out


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Evidence table (cổng trước khi làm)
# ---------------------------------------------------------------------------
FORMS_SECTIONS = {
    "PLI_M02": ["nddpl_uy_quyen_chu_so_huu"],
    "PLII_M02": ["a4_tv_hgd_sau_thay_doi", "c7_tv_hgd_cap_doi"],
    "PLI_M09": ["ds_thanh_vien_hop_danh", "vung_nhiem_mau_6789_10"],
    "PLI_M12": ["ndd_uy_quyen_sau_thay_doi"],
    "PLI_M15": ["ndd_pl_uy_quyen_chu_so_huu_moi"],
    "PLI_M72": ["thanh_vien_tnhhh_hai_tv_tro_len", "co_dong_sang_lap_cp",
                "co_dong_nuoc_ngoai_cp", "thanh_vien_hop_danh"],
}
SPEC_DONE = {  # entry nested-grid được phép khai ở đợt này
    ("PLI_M02", "nddpl_uy_quyen_chu_so_huu"): {
        "loop": "ds_nddpl_uy_quyen_chu_so_huu", "width": 14,
        "tags": ["stt", "ten_nguoi_dai_dien", "ngay_sinh", "gioi_tinh",
                 "giay_to_so", "giay_to_ngay", "giay_to_co_quan", "quoc_tich",
                 "dan_toc", "dia_chi", "von_duoc_uy_quyen_vnd", "ty_le",
                 "chu_ky", "ghi_chu"]},
    ("PLI_M12", "ndd_uy_quyen_sau_thay_doi"): {
        "loop": "ds_ndd_uy_quyen_sau_thay_doi", "width": 15,
        "tags": ["stt", "chu_so_huu_tvtnhh_cdnn_to_chuc", "ten_ndd_uy_quyen",
                 "ngay_sinh", "gioi_tinh", "giay_to_so", "giay_to_ngay",
                 "giay_to_co_quan", "quoc_tich", "dan_toc", "dia_chi",
                 "von_duoc_uy_quyen_vnd", "ty_le", "chu_ky", "ghi_chu"]},
    ("PLI_M15", "ndd_pl_uy_quyen_chu_so_huu_moi"): {
        "loop": "ds_nddpl_uy_quyen_chu_so_huu_moi", "width": 14,
        "tags": ["stt", "ten_nguoi_dai_dien", "ngay_sinh", "gioi_tinh",
                 "giay_to_so", "giay_to_ngay", "giay_to_co_quan", "quoc_tich",
                 "dan_toc", "dia_chi", "von_duoc_uy_quyen_vnd", "ty_le",
                 "chu_ky", "ghi_chu"]},
}


@check("[EVD] census manifest co evidence cho MOI bang auditor liet ke")
def t_evidence_manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    forms = {f["form_id"]: {s["section_id"]: s for s in f["sections"]}
             for f in data["forms"]}
    for fid, sec_ids in FORMS_SECTIONS.items():
        for sid in sec_ids:
            sec = forms[fid].get(sid)
            assert sec is not None, "%s: thiếu section %r trong manifest" % (
                fid, sid)
            ev = sec.get("source_evidence") or {}
            assert sec.get("kind"), "%s/%s thiếu kind" % (fid, sid)
            assert (ev.get("heading") or ev.get("anchor")), \
                "%s/%s thiếu evidence nguồn" % (fid, sid)
    # [Pin sync — F0L 2026-09-06] nhiễm nguồn Mẫu 6/7/8/9(lần 2)/10:
    # premise cũ "phải còn nguyên được ghi nhận" đã chết — vùng nhiễm bị
    # XÓA KHỎI NGUỒN theo O1 verdict REMOVED_BY_SOURCE_CLEANUP (laneC
    # 3eb9a55 / merge 29c850f; gate tools.test_m09_decontaminate 8/8).
    # Pin mới: manifest ghi TRẠNG THÁI SAU decontaminate có evidence.
    contam = forms["PLI_M09"]["vung_nhiem_mau_6789_10"]
    assert contam["kind"] == "source-contamination" and \
        contam["status"] == "removed_by_source_cleanup", \
        "vung_nhiem phải ghi trạng thái đã decontaminate (không quay lại " \
        "'contaminated' hay ngụy trang thành output)"
    # hai lưới thành viên hộ gia đình PLII_M02 cùng tập cột 10 cột
    # [Pin sync — PLAN v7 F0.5] P2 member-grid rebuild (merge P2A) đã rebuild
    # 2 lưới này: status missing_grid -> already_complete, giữ đúng 10 cột.
    # Ownership trạng thái mới: tools/test_member_grids_rebuild.py.
    for sid in ("a4_tv_hgd_sau_thay_doi", "c7_tv_hgd_cap_doi"):
        sec = forms["PLII_M02"][sid]
        assert sec["kind"] == "editable-grid" and sec["status"] == "already_complete"
        assert ",".join(sec["required_columns"]) == (
            "stt,ho_ten,ngay_sinh,so_cccd,gioi_tinh,quoc_tich,dan_toc,"
            "noi_thuong_tru,noi_o_hien_tai,chu_ky")


@check("[EVD] 3 section lam spec co kind/semantic_key trung manifest + du cot khai")
def t_spec_done_kinds_match_manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    forms = {f["form_id"]: {s["section_id"]: s for s in f["sections"]}
             for f in data["forms"]}
    # gap đã ghi nhận của N1 policy: 2 nhóm header cuối chưa có tag canonical
    DOCUMENTED_GAPS = {"tong_gia_tri_von_du_dai_dien",
                       "thoi_diem_dai_dien_phan_von"}
    ALIAS = {   # tên manifest -> tập tag canonical tôi khai trong spec
        "stt": {"stt"},
        "ten_ndd_pl_or_uy_quyen": {"ten_nguoi_dai_dien"},
        "ngay_thang_nam_sinh": {"ngay_sinh"},
        "so_ngay_cap_co_quan_cap_gtpl": {"giay_to_so", "giay_to_ngay",
                                         "giay_to_co_quan"},
        "so_ngay_cap_co_quan_cap_gtpl_ca_nhan": {"giay_to_so", "giay_to_ngay",
                                                 "giay_to_co_quan"},
        "dia_chi_lien_lac": {"dia_chi"},
        "von_duoc_uy_quyen": {"von_duoc_uy_quyen_vnd", "ty_le"},
        "ty_le": {"ty_le"},
        "chu_ky_output_only": {"chu_ky"},
        "ty_le_phan_von_du_uy_quyen": {"ty_le"},
    }
    for (fid, sid), want in SPEC_DONE.items():
        sec = forms[fid][sid]
        assert sec["kind"] == "nested-grid", "%s/%s kind=%s" % (fid, sid,
                                                               sec["kind"])
        assert sec["semantic_key"] == want["loop"], \
            "%s/%s semantic_key=%r != %r" % (fid, sid, sec["semantic_key"],
                                             want["loop"])
        tags = set(want["tags"])
        uncovered = [c for c in sec["required_columns"]
                     if c not in DOCUMENTED_GAPS
                     and not (ALIAS.get(c) or {c}) & tags]
        assert not uncovered, \
            "%s/%s: manifest yêu cầu %r nhưng spec không khai (không thuộc gap)" % (
                fid, sid, uncovered)


@check("[SPEC] 3 file spec qua validator v1 (_validate_kind_spec)")
def t_spec_validate():
    for (fid, _sid), want in SPEC_DONE.items():
        ext = bfm.load_form_spec(fid)
        assert ext, "%s: không đọc được file spec" % fid
        hits = [ext["specs_by_id"][e["spec"]] for e in ext["entries"]
                if ext["specs_by_id"][e["spec"]].get("semantic_key")
                == want["loop"]]
        assert len(hits) == 1, "%s: kỳ vọng 1 nested-grid entry, thấy %d" % (
            fid, len(hits))
        s = hits[0]
        assert s["kind"] == "nested-grid", s["kind"]
        assert s["loop"] == want["loop"]
        assert s["width"] == want["width"], \
            "%s: width=%s != %s" % (fid, s["width"], want["width"])
        tags = [c["tag"] for c in s["columns"]]
        assert "chu_ky" in tags, "%s: thiếu cột chu_ky (D2.4=A)" % fid
        ck = s["columns"][tags.index("chu_ky")]
        assert ck["input_type"] == "outputOnly" and ck["output_only"], \
            "%s: chu_ky phải outputOnly (D2.4=A)" % fid
        assert s["totals"] == [], "nested-grid v1 bắt buộc totals=[]"
        spans_ok = []
        for row in s["header_rows"]:
            spans_ok.extend(c["colspan"] * c["rowspan"] > 0 for c in row)
        assert all(spans_ok)
        # STT cột sinh tự động tại 0, cột dữ liệu liền kề từ 1
        assert s["stt"] == {"mode": "generated", "col_index": 0}
        assert [c["col_index"] for c in s["columns"]] == list(
            range(1, s["width"]))
        if fid in ("PLI_M02", "PLI_M15"):
            assert s["discriminator"] == {
                "tag": "loai_dong", "values": ["ndd_pl", "ndd_uy_quyen"]}, \
                "%s: D2.1=A yêu cầu discriminator loai_dong" % fid
        else:
            assert s["discriminator"] is None, \
                "PLI_M12: chưa có evidence 2 row-type -> không khai discriminator"


@check("[SPEC] quy rule an toan: drop mac dinh TAT ca nhieu truoc drop de khong nuot vung ke")
def t_no_default_drops_set():
    for fid in ("PLI_M02", "PLI_M12", "PLI_M15"):
        ext = bfm.load_form_spec(fid)
        for e in ext["entries"]:
            assert e.get("no_default_drops") is True, \
                "%s/%s: cần no_default_drops=true" % (fid, e["spec"])


@check("[ANCHOR] anchor dung duy nhat 1 paragraph trong blocks hien tai VA template")
def t_anchor_unique():
    EXPECTED_ANCHOR_BLOCK = {
        # [Pin sync — F0L 2026-09-06] 125 -> 124: premise cũ (audit Wave D):
        # blk126 là glue, B125 là heading. Hiện trạng: sau các merge F0L,
        # block liền trước heading M02 dính thành 1 ('thu dien tu (neu co):
        # website (neu co):' gộp) -> heading 'nguoi dai dien theo phap
        # luat/...' nằm ở 124; evidence: fold[124] == '- thong tin ve nguoi
        # dai dien theo phap luat/nguoi dai dien theo uy quyen cua chu so
        # huu:', anchor khớp template đúng 1 (index 130) — uniqueness giữ
        # nguyên.
        "PLI_M02": 124,
        # [Pin sync — F0L 2026-09-06] 134 -> 135: band "TÊN DOANH NGHIỆP"
        # thêm ở đầu M12 theo TT 121/2026 (ảnh p50; laneA 3b50306) — pin này
        # viết theo GIẢ ĐỊNH band là +1 paragraph.
        # [Pin sync — F0L 2026-09-06, integ] 135 -> 132: premise trên hết
        # hiệu lực sau regen THẬT — hdr2col biến 4 paragraph header thành
        # MỘT w:tbl 2x2 (blocks[0]='[tbl]') nên trượt ròng là -3 (135-3=132);
        # evidence: fold[132] == 'thong tin ve nguoi dai dien theo uy quyen
        # sau khi thay doi:' (đúng heading), anchor khớp template đúng 1.
        "PLI_M12": 132,
        "PLI_M15": 43,        # blk49 glue — hdr2col (084444d): bảng header
                              # band thay 4 p header -> index dịch 48 -> 43
    }
    for fid, idx in EXPECTED_ANCHOR_BLOCK.items():
        ext = bfm.load_form_spec(fid)
        ent = [e for e in ext["entries"]
               if ext["specs_by_id"][e["spec"]]["kind"] == "nested-grid"][0]
        folds_b = block_folds(fid)
        hits_b = [i for i, t in enumerate(folds_b) if re.search(ent["anchor"], t)]
        assert hits_b == [idx], \
            "%s: anchor khớp blocks %r != [%d]" % (fid, hits_b, idx)
        hits_t = [i for i, t in enumerate(template_folds(fid))
                  if re.search(ent["anchor"], t)]
        assert len(hits_t) == 1, "%s: anchor khớp template %d lần" % (
            fid, len(hits_t))


@check("[ANCHOR] trim gan DUNG paragraph glue va giu duoc chu phap ly din kem")
def t_trim_matches_glue():
    KEEP_CONTAINS = {
        "PLI_M02": "Thông tin về Giấy chứng nhận đăng ký đầu tư",
        "PLI_M12": "____________________",
        "PLI_M15": "Trường hợp hồ sơ đăng ký doanh nghiệp hợp lệ",
    }
    GLUE_FOLD_PREFIX = {
        "PLI_M02": "sttten nguoi dai dien theo phap luat",
        "PLI_M12": "sttchu so huu/thanh vien cong ty tnhh",
        "PLI_M15": "sttten nguoi dai dien theo phap luat",
    }
    for fid, keep in KEEP_CONTAINS.items():
        ext = bfm.load_form_spec(fid)
        ent = [e for e in ext["entries"]
               if ext["specs_by_id"][e["spec"]]["kind"] == "nested-grid"][0]
        pats = ent.get("trim") or []
        assert pats, "%s: header glue cần trim/keep_from" % fid
        # [Lead sync sau regen R3B1] trim chạy lúc REBUILD trên NGUỒN
        # (build_form_maps.process_form -> find_source), trước khi paragraph
        # glue bị thay bằng w:tbl; sau đó cả app/templates lẫn blocks đều là
        # artifact đã rebuild nên không còn glue (sandbox tự chứng minh qua
        # assert leftovers rỗng). Tra đúng stage nguồn mà generator dùng.
        src = bfm.find_source(fid)
        assert src is not None, "%s: không tìm thấy nguồn docx" % fid
        doc = docx.Document(str(src))
        raws = [p.text for p in doc.paragraphs]
        hits = [i for i, t in enumerate(raws) if any(re.match(p, fold(t))
                                                     for p in pats)]
        assert len(hits) == 1, "%s: trim khớp %d paragraph nguồn (%r)" % (
            fid, len(hits), hits)
        raw = raws[hits[0]]
        m = re.search(keep, raw)
        assert m, "%s: keep_from %r không nằm trong paragraph glue thật" % (
            fid, keep)
        kept = raw[m.start():].strip()
        # sau khi cắt, phần giữ lại KHÔNG còn prefix glue
        assert not fold(kept).startswith("stt"), \
            "%s: phần giữ lại vẫn dính glue (%r)" % (fid, kept[:60])


@check("[SANDBOX] rebuild that + converter kiem dinh nested-grid cho 3 mau")
def t_sandbox_rebuild_and_convert():
    tmp = Path(tempfile.mkdtemp(prefix="r3b1_sandbox_"))
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    tpl_dir = tmp / "templates"
    data_dir = tmp / "data"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    guards = {}
    for fid in ("PLI_M02", "PLI_M12", "PLI_M15"):
        p = ROOT / "app" / "templates" / ("%s.docx" % fid)
        guards[p.name] = (sha256_file(p), None)
    bfm.OUT_TPL = tpl_dir
    bfm.OUT_DATA = data_dir
    bfm._form_spec_cache.clear()
    try:
        GLUE_FOLD_PREFIX = {
            "PLI_M02": "sttten nguoi dai dien theo phap luat",
            "PLI_M12": "sttchu so huu/thanh vien cong ty tnhh",
            "PLI_M15": "sttten nguoi dai dien theo phap luat",
        }
        KEPT_FOLD = {   # pattern re.search trên text đã fold (phần GIỮ lại)
            "PLI_M02":
                "^-\\s*thong tin ve giay chung nhan dang ky dau tu \\(chi ke khai",
            "PLI_M15": "^truong hop ho so dang ky doanh nghiep hop le",
            "PLI_M12": "^_{4,}$",
        }
        for (fid, _sid), want in SPEC_DONE.items():
            src = bfm.find_source(fid)
            assert src is not None, "%s: không tìm thấy nguồn docx" % fid
            mau = int(re.search(r"Mau_(\d+)", src.name).group(1))
            titles = {"Phu luc I|%d" % mau: "T%s" % fid}
            meta, unmatched = bfm.process_form(src, titles, None)
            tpl_path = tpl_dir / ("%s.docx" % fid)
            assert tpl_path.exists(), "%s: generator chưa ghi template" % fid
            specs = [sp for sp in meta.get("section_specs") or []
                     if sp.get("loop") == want["loop"]]
            assert len(specs) == 1, "%s: form_maps thiếu %r" % (
                fid, want["loop"])
            sp = specs[0]
            assert int(sp["width"]) == want["width"]

            blocks = dxtb.convert_document(
                docx.Document(str(tpl_path)), fid, "DEMO %s" % fid,
                overrides={}, footnotes={}, section_specs=meta["section_specs"])
            loops = [b for b in blocks["blocks"] if b.get("t") == "loop"
                     and b.get("loop") == want["loop"]]
            assert len(loops) == 1, "%s: số block loop %r = %d" % (
                fid, want["loop"], len(loops))
            # cột tag theo đúng thứ tự khai báo (cột 0 là STT engine)
            got = [(c["col"], c["tag"]) for c in loops[0]["cols"]]
            want_cols = [(c["col_index"], c["tag"]) for c in sp["columns"]
                         if c["tag"]]
            assert got == want_cols, "%s: cols %r != %r" % (
                fid, got, want_cols)

            tpl_doc = docx.Document(str(tpl_path))
            texts = [Paragraph(el, tpl_doc).text
                     for el in tpl_doc.element.body.iterchildren()
                     if el.tag.endswith("}p")]
            leftovers = [t for t in texts if fold(t).startswith(
                GLUE_FOLD_PREFIX[fid])]
            assert not leftovers, "%s: glue còn sót %r" % (fid, leftovers[:2])
            assert any(re.search(KEPT_FOLD[fid], fold(t)) for t in texts), \
                "%s: chuỗi pháp lý dính kèm bị mất khi trim" % fid
        # template gốc trong repo KHÔNG bị chạm
        for name, before in list(guards.items()):
            after = sha256_file(ROOT / "app" / "templates" / name)
            assert after == before[0], "%s bị ghi ngoài sandbox!" % name
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()


@check("[BLOCKED] PLII_M02 pin sync: 4 nganh + a7 + 2 nested thanh vien (P2 rebuilt)")
def t_blocked_plii_m02():
    path = ROOT / "tools" / "form_specs" / "household" / "PLII_M02.json"
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    ids = []
    kinds = []
    for e in raw["tables"]:
        sid = e["spec"]["id"]
        kinds.append(e["spec"].get("kind") or "list")
        # [Đổi pin — lane cap-von 2026-08-28] entry fixed-matrix thuế mẫu II.2
        # (D5.2, owner 2026-08-28).
        # [Pin sync — PLAN v7 F0.5] packet D2 ĐÃ có quyết định cho 2 lưới
        # thành viên hộ gia đình (P2 member-grid rebuild 10 cột, merge P2A;
        # ownership trạng thái mới: tools/test_member_grids_rebuild.py) nên
        # pin "nested-grid == 0" stale — cập nhật: đúng 2 nested-grid tv_hgd.
        if sid.startswith(("a7_thue_", "c5_thue_")):
            # [Pin sync — F1-IN 2026-09-06] +c5_thue_chi_tieu_cap_doi (O1:
            # 10 section USER-INPUT, D5.2=A Mục C cấp đổi)
            assert e["spec"].get("kind") == "fixed-matrix", \
                "entry ngoài nhóm ngành phải là fixed-matrix: %r" % sid
            continue
        assert sid.startswith(("nganh_", "ds_nganh", "tv_hgd_")), \
            "PLII_M02 xuất hiện entry ngoài nhóm ngành/thuế/thành viên: %r" % sid
        occs = e.get("occurrences") or []
        ids.extend(o["occurrence_id"] for o in occs)
    want_ids = ["nganh_bo_sung", "nganh_xoa_bo", "nganh_sua_doi_chi_tiet",
                "nganh_hien_tai", "tv_hgd_sau_thay_doi", "tv_hgd_cap_doi"]
    assert sorted(ids) == sorted(want_ids), (
        "tập occurrence_id PLII_M02 đã đổi -> phải cập nhật "
        "tools/test_industry_household.py + tools/census/p1_c_verify_plii_m02.py "
        "(hiện %r)" % ids)
    assert kinds.count("nested-grid") == 2, \
        "PLII_M02: đúng 2 nested-grid thành viên (P2 rebuild), thấy %d" % \
        kinds.count("nested-grid")
    # [Pin sync — F1-IN 2026-09-06] +c5_thue_chi_tieu_cap_doi (O1) -> 2
    assert kinds.count("fixed-matrix") == 2, \
        "PLII_M02: đúng 2 entry fixed-matrix thuế (D5.2 a7 + O1 c5), thấy %d" % \
        kinds.count("fixed-matrix")
    # [Pin sync — PLAN v7 F0.5] Evidence glue cũ ("sttho ten…so dinh danh",
    # B069/B126) đã biến mất DO DESIGN: P2 member-grid rebuild thay paragraph
    # glue bằng loop block có header cấu trúc thật. Pin mới: 2 loop tv_hgd
    # đủ 9 cột dữ liệu (STT generated ở col 0) theo đúng thứ tự required
    # 10 cột; chuỗi cam kết hộ kinh doanh còn nguyên (tra theo nội dung).
    loops = {b.get("loop"): b for b in blocks_json("PLII_M02")["blocks"]
             if b.get("t") == "loop"}
    want_cols = ["ho_ten", "ngay_sinh", "so_cccd", "gioi_tinh", "quoc_tich",
                 "dan_toc", "noi_thuong_tru", "noi_o_hien_tai", "chu_ky"]
    for lname in ("tv_hgd_sau_thay_doi", "tv_hgd_cap_doi"):
        b = loops.get(lname)
        assert b, "mất loop %s sau P2 member-grid rebuild" % lname
        assert [c["tag"] for c in b.get("cols", [])] == want_cols, \
            "%s: cols lệch evidence 10 cột: %r" % (
                lname, [c["tag"] for c in b.get("cols", [])])
    folds = block_folds("PLII_M02")
    assert any("ho kinh doanh cam ket ve tinh hop phap" in f for f in folds), \
        "mất chuỗi cam kết hộ kinh doanh trong blocks"


@check("[BLOCKED] PLI_M09: khong spec moi khi nguon con nhiem va chua doi chieu ban goc")
@check("[BLOCKED] PLI_M09: khong spec moi khi nguon con nhiem va chua doi chieu ban goc")
def t_blocked_pli_m09():
    # [GỠ PIN — Lead 2026-08-28] premise lỗi thời sau lệnh owner 2026-08-28:
    # D3.1=A/D3.2=A + nguồn TT 68/121 -> lane m09-rebuild ĐÃ tạo spec
    # formation/PLI_M09.json (14 cột, decontaminate) và merge @ cfdefcd.
    # Toàn bộ evidence cũ (bảng nhiễm B087/B132/B163 còn nguyên, cột 10
    # chưa tag) sẽ mất sau Lead regen — trạng thái mới do
    # tools/test_m09_rebuild.py sở hữu. Clause giữ lại phần còn đúng:
    # PLI_M09 KHÔNG được khai entry NGƯỜI ngoài lưới đã quyết (14 cột).
    ext = bfm.load_form_spec("PLI_M09")
    for e in ext["entries"]:
        sp = ext["specs_by_id"][e["spec"]]
        assert sp.get("kind") in ("list", None), \
            "PLI_M09 xuất hiện kind ngoài quyết định D3.2=A: %r" % sp.get("kind")
        assert sp.get("loop") == "ds_thanh_vien_hop_danh", \
            "PLI_M09 loop lạ: %r" % sp.get("loop")


@check("[BLOCKED] PLI_M72 pin sync: 5 entry (5 occ nganh + 4 nested N2-N5 rebuilt)")
def t_blocked_pli_m72():
    path = ROOT / "tools" / "form_specs" / "change" / "PLI_M72.json"
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    # [Pin sync — PLAN v7 F0.5] P2 rebuild M72 (merge P2A/P2 pin sync) đã
    # khai đủ 4 lưới N2-N5: spec 1 -> 5 entry; manifest 4 section nested
    # missing_grid -> already_complete. Ownership trạng thái mới:
    # tools/test_member_grids_rebuild.py + test_m72_conditional_export.
    assert len(raw["tables"]) == 5, "PLI_M72 đổi số entry: %d" % len(raw["tables"])
    kinds = [(e["spec"].get("kind") or "list") for e in raw["tables"]]
    assert kinds.count("nested-grid") == 4, \
        "PLI_M72: đúng 4 nested-grid N2-N5, thấy %d" % kinds.count("nested-grid")
    assert "section_cond" in raw, "mất section_cond (fixture selector phụ thuộc)"
    blocks = blocks_json("PLI_M72")["blocks"]
    # [Pin sync — PLAN v7 F0.5] Evidence "glue header cổ đông >=2" stale do
    # P2 rebuild thay glue bằng loop block cấu trúc. Pin mới: 4 nested-grid
    # N2-N5 tồn tại làm loop block, mỗi loop có cột quốc tịch (col 2).
    loops = {b.get("loop"): b for b in blocks if b.get("t") == "loop"}
    for lname in ("ds_thanh_vien_tnhh_2tv", "ds_co_dong_sang_lap_ctcp",
                  "ds_co_dong_nuoc_ngoai_ctcp", "ds_thanh_vien_hop_danh_dhdn"):
        b = loops.get(lname)
        assert b, "mất loop N2-N5 %s sau P2 rebuild" % lname
        tags = [c["tag"] for c in b.get("cols", [])]
        assert "quoc_tich" in tags, "%s: mất cột quốc tịch: %r" % (lname, tags)
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sec = {s["section_id"]: s for f in data["forms"] if f["form_id"] == "PLI_M72"
           for s in f["sections"]}
    for sid in ("thanh_vien_tnhhh_hai_tv_tro_len", "co_dong_sang_lap_cp",
                "co_dong_nuoc_ngoai_cp", "thanh_vien_hop_danh"):
        assert sec[sid]["status"] == "already_complete", "%s đổi trạng thái" % sid


@check("[XAC MINH] loader chi doc 1 file spec cho moi mau (khong nghiengo khi them nhom)")
def t_loader_single_file_policy():
    # phòng ngừa: nếu Lead thêm nhóm mới chứa cùng form id thì loader im lặng
    # lấy file đầu tiên -> giữ thông tin này để report, không chặn
    ext = bfm.load_form_spec("PLI_M15")
    assert ext and len(ext["entries"]) == 1
    ent = ext["entries"][0]
    assert ent["anchor"].startswith("- thong tin ve nguoi dai dien")
    assert ent["_blocked"] is False


def main() -> int:
    for fn in (t_evidence_manifest, t_spec_done_kinds_match_manifest,
               t_spec_validate, t_no_default_drops_set, t_anchor_unique,
               t_trim_matches_glue, t_sandbox_rebuild_and_convert,
               t_blocked_plii_m02, t_blocked_pli_m09, t_blocked_pli_m72,
               t_loader_single_file_policy):
        fn()
    ok = sum(1 for p, _ in _results if p)
    fail = sum(1 for p, _ in _results if not p)
    print("-" * 72)
    print("test_r3b1_people_specs: %d PASS / %d FAIL" % (ok, fail))
    for passed, name in _results:
        if not passed:
            print("  -> %s" % name)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
