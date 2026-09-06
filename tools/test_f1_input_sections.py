#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_f1_input_sections.py — Lane F1-IN (O1: 10 section USER-INPUT).

Mệnh đề kiểm chứng cho đợt implement 10 section BLOCKED_OWNER -> USER-INPUT
(owner packet v7: O1 adjudicate 22 section, O2 WLAY-005/M12, D5.2=A, D6.4,
D6.5=A, D6.6=A), theo docs/decision_registry.md + census manifest:

  [O1-MANIFEST] 10 section có status already_complete + lead_status_override
                evidence trong census manifest; 2 section có evidence override
                (required_columns/heading) khớp nguồn hiện hành.
  [SPEC]        6 file spec qua validator v1 của tools/build_form_maps.py
                (M12 3 fixed-matrix; M27 2 list entry/3 occurrence; M78 1
                fixed-matrix; M79/M80 1 list; PLII_M02 +1 fixed-matrix C5).
                Sai cấu trúc (thiếu cột/totals target sai/trung row id/occurrence
                sai) phải bị validator CHẶN.
  [ANCHOR/BLOCKS] blocks hiện tại chứa bảng/loop của đủ 10 section: 3 bảng
                M12, 3 loop M27, bảng M78, loop M79/M80, bảng C5 PLII_M02,
                cặp chk_auto_* M02 (Q-V1 radio chọn-1).
  [COMPUTED]    O2/D1.1=A: tổng fixed-matrix M12 được recompute từ ô dữ liệu
                khi export (recompute_totals), ghi đè stored; stored != computed
                -> ExportTotalsError code EXPORT_TOTALS_RECOMPUTE_CONFLICT
                (blocking).
  [NEGATIVE]    tổng sai phải blocking (conflict test); thiếu cột/totals target
                lạ phải bị validator chặn; draft cũ không có key mới -> render
                vẫn ra template hoàn chỉnh (blank pháp định), không crash.
  [COVERAGE]    coverage audit xếp đủ 10 section IMPLEMENTED_VERIFIED.

Chạy: python3 -X utf8 tools/test_f1_input_sections.py   (từ root repo)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.build_form_maps as bfm                      # noqa: E402
from tools.docx_render import (                          # noqa: E402
    ExportTotalsError, recompute_totals)

MANIFEST = json.loads(
    (ROOT / "app" / "data" / "table_specs" / "manifest.json").read_text(
        encoding="utf-8"))
FORM_MAPS = json.loads(
    (ROOT / "app" / "data" / "form_maps.json").read_text(encoding="utf-8"))

RESULTS: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(*args, **kw):
            try:
                fn(*args, **kw)
                RESULTS.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                RESULTS.append((False, name))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                RESULTS.append((False, name))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def note(name: str):
    """Không phải mệnh đề fail — ghi nhận hiện trạng (luôn PASS)."""
    RESULTS.append((True, name))
    print("NOTE %s" % name)


def manifest_section(fid, sid):
    for f in MANIFEST["forms"]:
        if f["form_id"] == fid:
            for s in f["sections"]:
                if s["section_id"] == sid:
                    return s
    raise AssertionError("manifest thieu section %s/%s" % (fid, sid))


def blocks_of(fid):
    return json.loads(
        (ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)).read_text(
            encoding="utf-8"))["blocks"]


def cell_text(cell):
    out = ""
    for r in cell.get("runs", []):
        if isinstance(r.get("text"), str):
            out += r["text"]
        elif isinstance(r.get("input"), dict):
            out += "{%s}" % r["input"].get("key", "")
    return out


def find_loop(blocks, name):
    hits = [b for b in blocks if b.get("t") == "loop" and b.get("loop") == name]
    assert len(hits) == 1, "ky vong dung 1 loop %r, thay %d" % (name, len(hits))
    return hits[0]


def find_table_by_header(blocks, needle):
    for b in blocks:
        if b.get("t") != "table" or not b.get("rows"):
            continue
        hdr = " | ".join(cell_text(c) for c in b["rows"][0]["cells"])
        if needle in hdr:
            return b
    raise AssertionError("khong tim thay bang header chua %r" % needle)


def section_spec(fid, spec_id):
    fm = FORM_MAPS[fid]
    for ss in fm.get("section_specs") or []:
        if ss.get("id") == spec_id:
            return ss
    for dt in fm.get("dynamic_tables") or []:
        if dt.get("id") == spec_id:
            return dt
    raise AssertionError("form_maps %s thieu %s" % (fid, spec_id))


# ---------------------------------------------------------------------------
SECTIONS_10 = [
    ("PLI_M02", "mo_hinh_to_chuc_cong_ty"),
    ("PLI_M12", "tai_san_gop_von_sau_thay_doi_vdl"),
    ("PLI_M12", "tai_san_gop_von_sau_thay_doi_von_dau_tu"),
    ("PLI_M12", "co_cau_loai_co_phan_sau_thay_doi"),
    ("PLI_M27", "danh_sach_ndd_pl_thong_bao"),
    ("PLI_M27", "don_vi_tam_ngung_tiep_tuc"),
    ("PLI_M78", "san_pham_cung_cap_thong_tin"),
    ("PLI_M79", "tai_lieu_kem_theo_de_nghi"),
    ("PLI_M80", "tai_lieu_kem_theo_thu_hoi"),
    ("PLII_M02", "c5_thue_chi_tieu_cap_doi"),
]


# --------------------------------------------------------------- [O1-MANIFEST]
@check("[O1-MANIFEST] 10 section da_complete + lead_status_override")
def t_manifest():
    for fid, sid in SECTIONS_10:
        s = manifest_section(fid, sid)
        assert s.get("status") == "already_complete", \
            "%s/%s status=%s" % (fid, sid, s.get("status"))
        ov = s.get("lead_status_override") or {}
        assert ov.get("evidence"), "%s/%s thieu override evidence" % (fid, sid)


@check("[O1-MANIFEST] evidence override M02/M27 theo nguon hien hanh")
def t_evidence_overrides():
    s = manifest_section("PLI_M02", "mo_hinh_to_chuc_cong_ty")
    assert s["required_columns"] == [
        "chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g",
        "chk_auto_chu_tich_cong_ty_giam_doc_hoac_tong_giam",
    ]
    s = manifest_section("PLI_M27", "danh_sach_ndd_pl_thong_bao")
    assert s["required_columns"] == ["stt", "ho_ten", "dien_thoai", "email"]
    s = manifest_section("PLI_M78", "san_pham_cung_cap_thong_tin")
    assert s["source_evidence"]["heading"] == "3. Thông tin yêu cầu:"


# --------------------------------------------------------------------- [SPEC]
@check("[SPEC] spec files qua validator v1 (load_form_spec)")
def t_specs_valid():
    expect = {
        "PLI_M12": {"tai_san_gop_von_sau_thay_doi_vdl",
                    "tai_san_gop_von_sau_thay_doi_von_dau_tu",
                    "co_cau_loai_co_phan_sau_thay_doi"},
        "PLI_M27": {"danh_sach_ndd_pl_thong_bao", "don_vi_tam_ngung_tiep_tuc"},
        "PLI_M78": {"san_pham_cung_cap_thong_tin"},
        "PLI_M79": {"tai_lieu_kem_theo_de_nghi"},
        "PLI_M80": {"tai_lieu_kem_theo_thu_hoi"},
        "PLII_M02": {"c5_thue_chi_tieu_cap_doi"},
    }
    for fid, ids in expect.items():
        ext = bfm.load_form_spec(fid)
        got = set(ext["specs_by_id"].keys())
        assert ids <= got, "%s thieu spec %s" % (fid, ids - got)
    # M27: 2 occurrence cho entry don_vi
    ext = bfm.load_form_spec("PLI_M27")
    ent = [e for e in ext["entries"]
           if isinstance(e.get("spec"), str)
           and e["spec"] == "don_vi_tam_ngung_tiep_tuc"][0]
    occs = ent.get("_occurrences") or []
    assert [o["occurrence_id"] for o in occs] == [
        "don_vi_truc_thuoc_tam_ngung_tiep_tuc", "don_vi_tiep_tuc_truoc_han"]


@check("[SPEC][NEGATIVE] sai structure bi validator chan")
def t_spec_negative():
    import copy
    base = {
        "id": "x", "kind": "fixed-matrix", "semantic_key": "x",
        "columns": [
            {"header": "A", "tag": None, "input_type": "readonly"},
            {"header": "B", "tag": "t1", "input_type": "money"},
        ],
        "fixed_rows": [
            {"id": "r1", "label": "R1"},
            {"id": "tong", "label": "Tổng", "output_only": True},
        ],
        "totals": [{"formula": "sum(t1)", "target_row": "tong",
                    "target_tag": "t1"}],
    }
    # totals target_tag lạ -> chặn
    bad = copy.deepcopy(base)
    bad["totals"][0]["target_tag"] = "tag_la"
    try:
        bfm._validate_kind_spec(bad, "TEST")
        raise AssertionError("totals target_tag phai bi chan")
    except ValueError:
        pass
    # dòng tổng không output_only -> chặn
    bad = copy.deepcopy(base)
    bad["fixed_rows"][1]["output_only"] = False
    try:
        bfm._validate_kind_spec(bad, "TEST")
        raise AssertionError("hang tong thieu output_only phai bi chan")
    except ValueError:
        pass
    # trùng row id -> chặn
    bad = copy.deepcopy(base)
    bad["fixed_rows"][0]["id"] = "tong"
    try:
        bfm._validate_kind_spec(bad, "TEST")
        raise AssertionError("row id trung phai bi chan")
    except ValueError:
        pass
    # 2 cột tag=null -> chặn
    bad = copy.deepcopy(base)
    bad["columns"].append({"header": "C", "tag": None,
                           "input_type": "readonly"})
    try:
        bfm._validate_kind_spec(bad, "TEST")
        raise AssertionError("2 cot nhan phai bi chan")
    except ValueError:
        pass


# ---------------------------------------------------------- [ANCHOR / BLOCKS]
@check("[BLOCKS] M12: 3 bang fixed-matrix dung dong/the")
def t_blocks_m12():
    blocks = blocks_of("PLI_M12")
    vdl = find_table_by_header(blocks, "Giá trị vốn của từng tài sản trong vốn điều lệ")
    assert len(vdl["rows"]) == 8  # header + 6 dòng + Tổng số
    ss = section_spec("PLI_M12", "tai_san_gop_von_sau_thay_doi_vdl")
    assert ss["semantic_key"] == "co_cau_tai_san_gop_von_sau_thay_doi_vdl"
    key = "{co_cau_tai_san_gop_von_sau_thay_doi_vdl.dong_viet_nam.gia_tri_vnd}"
    assert key in cell_text(vdl["rows"][1]["cells"][2]), cell_text(vdl["rows"][1]["cells"][2])
    # O2 verbatim theo bản in hiện hành (thiếu 'i' là của bản in, giữ nguyên)
    cp = find_table_by_header(blocks, "Tỉ lệ so với vốn điều lệ")
    labels = [cell_text(r["cells"][0]) for r in cp["rows"][1:]]
    assert "Cổ phần ưu đã biểu quyết" in labels, labels
    assert len(cp["rows"]) == 7
    # các bảng đều có dòng tổng gắn the
    tong = cell_text(cp["rows"][-1]["cells"][-1])
    assert "tong_so" in tong, tong


@check("[BLOCKS] M27: 3 loop dung cot; field cu vung don vi da thu hoi")
def t_blocks_m27():
    blocks = blocks_of("PLI_M27")
    ndd = find_loop(blocks, "ds_ndd_pl_thong_bao_tam_ngung")
    tags = [c.get("tag") for c in ndd["cols"]]
    assert tags == ["ho_ten", "dien_thoai", "email"], tags
    tn = find_loop(blocks, "don_vi_truc_thuoc_tam_ngung_tiep_tuc")
    tags = [c.get("tag") for c in tn["cols"]]
    assert tags == ["loai_don_vi", "ten_don_vi", "ma_so_don_vi",
                    "tu_ngay", "den_ngay", "ly_do",
                    "ten_chi_nhanh_chu_quan", "ma_so_chi_nhanh_chu_quan"], tags
    tt = find_loop(blocks, "don_vi_tiep_tuc_truoc_han")
    assert [c.get("tag") for c in tt["cols"]] == tags
    # field cũ của vùng NĐD/đơn vị KHÔNG còn (grid thay trọn bộ chức năng)
    keys = set()
    for b in blocks:
        for r in b.get("runs", []):
            if isinstance(r.get("input"), dict):
                keys.add(r["input"]["key"])
    for gone in ("ho_ten_in_hoa_2",):
        assert gone not in keys, "field cu %s van con" % gone
    # field doanh-nghiệp (ngoài vùng grid) GIỮ nguyên
    for keep in ("tu_ngay", "den_ngay", "ly_do_tam_ngung", "ly_do_tiep_tuc"):
        assert keep in keys, "field %s mat" % keep


@check("[BLOCKS] M78: bang 4 dong, cot SL + mo ta; M79/M80 loop tai lieu")
def t_blocks_m78_79_80():
    blocks = blocks_of("PLI_M78")
    tbl = find_table_by_header(blocks, "Số lượng sản phẩm")
    assert len(tbl["rows"]) == 5  # header + 4 dòng
    labels = [cell_text(r["cells"][0]) for r in tbl["rows"][1:]]
    assert labels == [
        "Giấy chứng nhận đăng ký doanh nghiệp của …",
        "Thông tin lịch sử 3 năm của doanh nghiệp …",
        "Thông tin doanh nghiệp mới nhất của …",
        "Sản phẩm khác",
    ], labels
    key = "{ds_san_pham_yeu_cau.san_pham_khac.so_luong_san_pham}"
    assert key in cell_text(tbl["rows"][4]["cells"][2])

    for fid, loop in (("PLI_M79", "ds_tai_lieu_kem_theo_m79"),
                      ("PLI_M80", "ds_tai_lieu_kem_theo_m80")):
        lp = find_loop(blocks_of(fid), loop)
        tags = [c.get("tag") for c in lp["cols"]]
        assert tags == ["mo_ta_tai_lieu", "so_ban", "so_trang"], tags


@check("[BLOCKS] PLII_M02 C5: dung 2 chi tieu that cua Muc C")
def t_blocks_c5():
    blocks = blocks_of("PLII_M02")
    tbl = find_table_by_header(blocks, "Các chỉ tiêu thông tin đăng ký thuế")
    assert len(tbl["rows"]) == 3  # header + 5.1 + 5.2 (D5.2=A: khong dong '…')
    labels = [cell_text(r["cells"][0]) for r in tbl["rows"][1:]]
    assert labels[0].startswith("5.1 Địa chỉ nhận thông báo thuế"), labels
    assert labels[1].startswith("5.2 Tổng số lao động"), labels
    key = "{thue_chi_tieu_cap_doi.chi_tieu_5_2_tong_so_lao_dong.so_lao_dong}"
    assert key in cell_text(tbl["rows"][2]["cells"][2])


@check("[BLOCKS] PLI_M02 mo_hinh: cap chk_auto_* ton tai (radio Q-V1)")
def t_blocks_m02():
    blocks = blocks_of("PLI_M02")
    chk_keys = [b["key"] for b in blocks if b.get("t") == "chk"]
    assert "chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g" in chk_keys
    assert "chk_auto_chu_tich_cong_ty_giam_doc_hoac_tong_giam" in chk_keys


# --------------------------------------------------------------- [COMPUTED]
def _nested(payload_flat):
    out = {}
    for k, v in payload_flat.items():
        parts = k.split(".")
        cur = out
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return out


@check("[COMPUTED] M12 tong duoc tinh lai tu o du lieu (ghi de stored)")
def t_totals_recompute():
    ss = [s for s in FORM_MAPS["PLI_M12"]["section_specs"]
          if s["id"] == "tai_san_gop_von_sau_thay_doi_vdl"][0]
    flat = {
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.dong_viet_nam.gia_tri_vnd": "7000000000",
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.dong_viet_nam.ty_le": "70",
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.vang.gia_tri_vnd": "3000000000",
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.vang.ty_le": "30",
        # stored SAI của ô tổng (draft cũ/gõ tay) -> blocking (O2: mismatch
        # computed vs stored là validation error blocking, không im lặng)
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.tong_so.gia_tri_vnd": "1",
    }
    payload = _nested(flat)
    try:
        recompute_totals(payload, [ss], strict=True)
        raise AssertionError("stored tong sai phai raise ExportTotalsError")
    except ExportTotalsError as exc:
        assert "EXPORT_TOTALS_RECOMPUTE_CONFLICT" in str(exc), str(exc)
    # strict=False: vẫn ghi đè kết quả tính lại vào payload (draft không
    # được quyết định tổng); report nêu đúng ô xung đột
    report = recompute_totals(payload, [ss], strict=False)
    node = payload["co_cau_tai_san_gop_von_sau_thay_doi_vdl"]["tong_so"]
    assert node["gia_tri_vnd"] == "10000000000", node
    assert node["ty_le"] == "100", node
    conflicts = [r for r in report
                 if r.get("semantic_key") == "co_cau_tai_san_gop_von_sau_thay_doi_vdl"
                 and r.get("row") == "tong_so"
                 and r.get("stored") not in (None, "")]
    assert conflicts, report


@check("[NEGATIVE] M12 chua khai tong -> engine ghi ket qua tinh lai")
def t_totals_blank():
    ss = [s for s in FORM_MAPS["PLI_M12"]["section_specs"]
          if s["id"] == "co_cau_loai_co_phan_sau_thay_doi"][0]
    payload = _nested({
        "co_cau_loai_co_phan_sau_thay_doi.co_phan_pho_thong.so_luong": "10",
    })
    recompute_totals(payload, [ss], strict=True)  # không conflict -> không raise
    node = payload["co_cau_loai_co_phan_sau_thay_doi"]["tong_so"]
    assert node["so_luong"] == "10", node


@check("[NEGATIVE] formula la -> FORMULA_UNSUPPORTED blocking")
def t_totals_conflict():
    ss = [s for s in FORM_MAPS["PLI_M12"]["section_specs"]
          if s["id"] == "tai_san_gop_von_sau_thay_doi_vdl"][0]
    bad = json.loads(json.dumps(ss))
    bad["totals"][0]["formula"] = "khong_la_formula(t1)"
    payload = _nested({
        "co_cau_tai_san_gop_von_sau_thay_doi_vdl.dong_viet_nam.gia_tri_vnd": "1",
    })
    try:
        recompute_totals(payload, [bad], strict=True)
        raise AssertionError("formula lạ phải raise ExportTotalsError")
    except ExportTotalsError as exc:
        assert "FORMULA_UNSUPPORTED" in str(exc)


@check("[NEGATIVE] draft rong -> render van ra template hoan chinh")
def t_blank_render():
    from tools.docx_render import write_rendered
    import tempfile
    import zipfile
    import re as _re
    for fid in ("PLI_M12", "PLI_M27", "PLI_M78", "PLI_M79", "PLI_M80",
                "PLII_M02"):
        fm = FORM_MAPS[fid]
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as fh:
            out = fh.name
        write_rendered("app/templates/%s.docx" % fid, {}, out,
                       tables_meta=fm.get("section_specs"))
        xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
        assert "{" not in _re.sub(r"<[^>]+>", "", xml)[:0]  # no-op guard
        leftover = _re.findall(r"\{[a-z][a-z0-9_.]*\}", xml)
        assert not leftover, "%s con token %s" % (fid, leftover[:5])


# ---------------------------------------------------------------- [COVERAGE]
@check("[COVERAGE] audit xep 10/10 section IMPLEMENTED_VERIFIED")
def t_coverage():
    import subprocess
    r = subprocess.run(
        [sys.executable, "-X", "utf8", "-m",
         "tools.census.table_coverage_audit"], cwd=str(ROOT),
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    cov = ROOT / "docs" / "table_coverage_current.json"
    data = json.loads(cov.read_text(encoding="utf-8"))
    by_key = {(r["form_id"], r["section_id"]): r for r in data["rows"]}
    for fid, sid in SECTIONS_10:
        r = by_key.get((fid, sid))
        assert r is not None, "thieu row %s/%s" % (fid, sid)
        assert r["final_status"] == "IMPLEMENTED_VERIFIED", \
            "%s/%s -> %s (%s)" % (fid, sid, r["final_status"],
                                  r.get("detail"))


def main() -> int:
    t_manifest()
    t_evidence_overrides()
    t_specs_valid()
    t_spec_negative()
    t_blocks_m12()
    t_blocks_m27()
    t_blocks_m78_79_80()
    t_blocks_c5()
    t_blocks_m02()
    t_totals_recompute()
    t_totals_blank()
    t_totals_conflict()
    t_blank_render()
    t_coverage()
    ok = sum(1 for good, _ in RESULTS if good)
    fail = len(RESULTS) - ok
    print("test_f1_input_sections: %d PASS / %d FAIL" % (ok, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
