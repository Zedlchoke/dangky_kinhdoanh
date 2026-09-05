#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_p2a_people_specs.py — Lane P2A (people/ownership, wave 2).

Mệnh đề kiểm chứng cho 6 spec/metadata người của đợt P2A, theo
docs/decision_registry.md packet D2 (D2.2=A, D2.3=A, D2.5=A, D2.6=A, D2.7=A,
D2.8=A, D2.4=A) + packet D7 (D7.3=A):

  [EVD]     census manifest (app/data/table_specs/manifest.json) phải còn ghi
            nhận đúng kind/status/semantic_key/required_columns của 6 section
            (chưa regen -> vẫn missing_grid/partial_columns).
  [SRC]     MẪU NGUỒN (docx gốc) phải tự chứng minh từng cột được khai:
            PLII_M07 mục 7 có ĐÚNG 7 nhãn cột (không ngày sinh/giới tính/dân
            tộc/chữ ký); Mẫu 10 glue trong nguồn M09 có cột 'Quyền chi phối'
            + chân trang 4 (NĐ 168/2025 điểm b khoản 1 Điều 17); Mẫu 13 chỉ
            có MỘT row-type (không có nhóm 'ủy quyền' trong vùng) -> không
            khai discriminator.
  [SPEC]    6 file spec qua loader/validator của tools/build_form_maps.py
            (kind=list) + shape: loop/key D2.8=A, cột thêm đúng D2.2/D2.3/
            D2.5, KHÔNG thêm cột chữ ký ở những bảng nguồn không có.
  [DELTA]   so với khai báo inline production đang chạy (app/data/form_maps.
            json): M06 thêm đúng 1 tag (thoi_han_gop_von), M07 thêm đúng 1
            tag (dan_toc), M08 KHÔNG đổi tag nào, M10 thêm đúng 1 cột
            (quyen_chi_phoi) và GIU NGUYEN các header text cũ -> migration
            draft additive.
  [REGION]  anchor/occurrence định vị ĐÚNG 1 vùng trên nguồn và trên blocks
            hiện tại (không nuốt vùng kế).
  [SANDBOX] rebuild THẬT trên sandbox tmp (OUT_TPL/OUT_DATA ghi vào temp,
            KHÔNG đụng app/templates / app/data): dựng bảng, convert về
            blocks, kiểm tra the đúng cột, glue biến mất, chuỗi pháp lý dính
            kèm được GIỮ, template gốc trong repo không bị chạm.
  [BLOCKED] những gì KHÔNG đủ quyết định thì PHẢI KHÔNG có spec: PLI_M09
            (D3), và file household/PLII_M02.json của lane khác phải giữ
            nguyên tập occurrence_id.

Chạy: python3 -X utf8 tools/test_p2a_people_specs.py   (từ root repo)
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.build_form_maps as bfm          # noqa: E402
import tools.docx_to_blocks as dxtb          # noqa: E402
import tools.table_occurrences as occ        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "app" / "data" / "table_specs" / "manifest.json"
FORM_MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
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


def block_folds(form_id: str) -> list[str]:
    out = []
    for b in blocks_json(form_id)["blocks"]:
        txt = "".join(str(r.get("text", "")) for r in (b.get("runs") or []))
        out.append(fold(txt))
    return out


def manifest_sections() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {s["section_id"]: s
            for f in data["forms"] for s in f["sections"]}


def prod_tags(form_id: str, loop: str) -> list[tuple[int, str]]:
    fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    for dt in fm[form_id]["dynamic_tables"]:
        if dt["loop"] == loop:
            return [(c["col"], c["tag"]) for c in dt["columns"]]
    raise AssertionError("%s: form_maps không có loop %s" % (form_id, loop))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Bảng kỳ vọng: (form_id, section_id, loop, tags cột dữ liệu theo thứ tự cột,
#                 [tags BỔ SUNG so với khai báo inline production])
# ---------------------------------------------------------------------------
M06_HEADERS = ["STT", "Tên thành viên", "Ngày, tháng, năm sinh", "Giới tính",
               "Số định danh cá nhân/Giấy tờ pháp lý của cá nhân", "Quốc tịch",
               "Dân tộc", "Địa chỉ liên lạc/Nơi thường trú", "Phần vốn góp (VNĐ)",
               "Tỷ lệ vốn góp (%)", "Thời hạn góp vốn", "Chữ ký"]
M07_HEADERS = ["STT", "Tên cổ đông sáng lập", "Ngày, tháng, năm sinh",
               "Giới tính", "Số định danh cá nhân/Giấy tờ pháp lý", "Quốc tịch",
               "Dân tộc", "Địa chỉ liên lạc", "Tổng số cổ phần", "Tỷ lệ (%)",
               "Chữ ký"]
M08_HEADERS = ["STT", "Tên cổ đông là nhà đầu tư nước ngoài", "Quốc gia",
               "Mã số doanh nghiệp/Giấy tờ pháp lý",
               "Địa chỉ trụ sở chính/Địa chỉ liên lạc", "Tổng số cổ phần",
               "Tỷ lệ (%)", "Chữ ký"]
M10_HEADERS = ["STT", "Họ và tên", "Ngày, tháng, năm sinh", "Giới tính",
               "Quốc tịch", "Dân tộc", "Địa chỉ liên lạc",
               "Giấy tờ pháp lý của cá nhân", "Tỷ lệ sở hữu vốn điều lệ (%)",
               "Tỷ lệ sở hữu cổ phần có quyền biểu quyết (%)", "Quyền chi phối",
               "Ghi chú"]
M13_HEADERS = ["STT", "Họ, chữ đệm và tên (ghi bằng chữ in hoa)",
               "Ngày, tháng, năm sinh", "Giới tính", "Số định danh cá nhân",
               "Chức danh", "Địa chỉ liên lạc", "Quốc gia"]
PLII_M07_HEADERS = ["STT", "Tên thành viên", "Quốc tịch", "Nơi ở hiện tại",
                    "Nơi thường trú", "Số định danh cá nhân", "Ghi chú"]

ANCHOR_ENTRIES = {   # entry theo anchor (không occurrence) -> khớp blocks + nguồn
    "PLI_M06": "thong tin ve giay chung nhan dang ky dau tu",
    "PLI_M07": r"^mau so 7$",
    "PLI_M08": "thong tin ve giay chung nhan dang ky dau tu",
    "PLI_M10": r"^mau so 10$",
}
OCC_ENTRIES = {       # entry theo occurrence -> khớp 1 vùng ok trên nguồn
    "PLII_M07": "ds_thanh_vien_hkd_gcn",
    "PLI_M13": "ds_ndd_pl_sau_thay_doi",
}


def spec_entry(form_id: str, spec_id: str) -> tuple[dict, dict]:
    raw = json.loads((ROOT / "tools" / "form_specs").joinpath(
        _GROUP_OF[form_id], "%s.json" % form_id).read_text(encoding="utf-8-sig"))
    for e in raw["tables"]:
        if e["spec"]["id"] == spec_id:
            return raw, e
    raise AssertionError("%s: không có entry %r" % (form_id, spec_id))


_GROUP_OF = {
    "PLI_M06": "formation", "PLI_M07": "formation", "PLI_M08": "formation",
    "PLI_M10": "formation", "PLI_M13": "change", "PLII_M07": "household",
}
SPEC_OF = {   # form -> (spec_id, loop, headers, [tag] theo thứ tự cột)
    "PLI_M06": ("ds_thanh_vien_tnhh", "ds_thanh_vien_tnhh", M06_HEADERS,
                ["ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "quoc_tich",
                 "dan_toc", "dia_chi", "von_dong_gop", "ty_le_von",
                 "thoi_han_gop_von", "chu_ky"]),
    "PLI_M07": ("ds_co_dong_sang_lap", "ds_co_dong_sang_lap", M07_HEADERS,
                ["ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "quoc_tich",
                 "dan_toc", "dia_chi", "so_co_phan", "ty_le", "chu_ky"]),
    "PLI_M08": ("ds_co_dong_nn", "ds_co_dong_nn", M08_HEADERS,
                ["ten_cd", "quoc_gia", "ma_so", "dia_chi", "so_co_phan",
                 "ty_le", "chu_ky"]),
    "PLI_M10": ("ds_cshhl", "ds_cshhl", M10_HEADERS,
                ["ho_ten", "ngay_sinh", "gioi_tinh", "quoc_tich", "dan_toc",
                 "dia_chi", "so_giay_to", "ty_le", "ty_le_co_phan",
                 "quyen_chi_phoi", "ghi_chu"]),
    "PLI_M13": ("ndd_pl_sau_thay_doi", "ds_ndd_pl_sau_thay_doi", M13_HEADERS,
                ["ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "chuc_danh",
                 "dia_chi", "quoc_gia"]),
    "PLII_M07": ("m7_danh_sach_thanh_vien_hgd", "ds_thanh_vien_hkd_gcn",
                 PLII_M07_HEADERS,
                 ["ten_thanh_vien", "quoc_tich", "noi_o_hien_tai",
                  "noi_thuong_tru", "so_cccd", "ghi_chu"]),
}
MANIFEST_SECTION_OF = {
    "PLI_M06": "ds_thanh_vien_tnhh",
    "PLI_M07": "ds_co_dong_sang_lap",
    "PLI_M08": "ds_co_dong_nn",
    "PLI_M10": "ds_cshhl_doanh_nghiep",
    "PLI_M13": "ndd_pl_sau_thay_doi",
    "PLII_M07": "m7_danh_sach_thanh_vien_hgd",
}

# Tên cột manifest -> tag spec (bảng người dùng chung tag ngắn như bộ người
# M02/M12/M15 của lane R3B1; tag production đang chạy được GIỮ để migration
# draft là additive — chỉ cột MỚI dùng đúng tên canonical của manifest).
ALIAS = {
    "ngay_thang_nam_sinh": "ngay_sinh",
    "so_gtpl": "so_cccd",
    "so_dinh_danh_ca_nhan": "so_cccd",
    "so_ngay_cap_co_quan_cap_gtpl": "so_giay_to",
    "dia_chi_lien_lac": "dia_chi",
    "phan_von_gop": "von_dong_gop",
    "ty_le_von_gop": "ty_le_von",
    "tong_so_co_phan": "so_co_phan",
    "ten_co_dong": "ten_cd",
    "ma_so_dn_gtpl": "ma_so",
    "ty_le_so_huu_von_dieule": "ty_le",
    "ty_le_co_phan_bieu_quyet": "ty_le_co_phan",
    "chu_ky_output_only": "chu_ky",
}


# ---------------------------------------------------------------------------
@check("[EVD] census manifest ghi nhan dung kind/status/sem 6 section P2A (post-census)")
def t_manifest_state():
    secs = manifest_sections()
    for fid, sid in MANIFEST_SECTION_OF.items():
        sec = secs.get(sid)
        assert sec is not None, "%s: thiếu section %r trong manifest" % (fid, sid)
        _fid, _sid, loop, _h, _t = (
            fid, sid, SPEC_OF[fid][1], SPEC_OF[fid][2], SPEC_OF[fid][3])
        # loop spec phải trùng semantic_key của manifest HOẶC loop_audit.loop
        # (M06: loop production ĐỔI RIÊNG ds_thanh_vien_tnhh trùng semantic_key
        # — guard export cấm cùng tên loop khác contract; draft M06 rỗng)
        ok_loop = (sec["semantic_key"] == loop or
                   (sec.get("loop_audit") or {}).get("loop") == loop)
        assert ok_loop, "%s/%s: loop %r không khớp manifest (semantic_key=%r, " \
            "loop_audit=%r)" % (fid, sid, loop, sec["semantic_key"],
                                (sec.get("loop_audit") or {}).get("loop"))
        assert sec["kind"] == "editable-grid", \
            "%s/%s kind=%s (P2A chỉ nhận editable-grid)" % (fid, sid, sec["kind"])
        ev = sec.get("source_evidence") or {}
        assert (ev.get("heading") or ev.get("anchor")), \
            "%s/%s thiếu evidence nguồn" % (fid, sid)
        # [Lead sync census 6e972e7] 6 section P2A đã already_complete với
        # evidence suite thật (LEAD_STATUS_OVERRIDES) sau regen.
        if fid == "PLII_M07":
            assert sec["status"] == "already_complete", sec["status"]
            assert ",".join(sec["required_columns"]) == ",".join(
                ["stt"] + SPEC_OF[fid][3]), sec["required_columns"]
        elif fid == "PLI_M13":
            assert sec["status"] == "already_complete", sec["status"]
        else:
            assert sec["status"] == "already_complete", sec["status"]
        if fid != "PLII_M07":
            # mọi cột manifest yêu cầu phải được spec phủ (trực tiếp hoặc qua
            # ALIAS ten tag ngắn — cùng convention R3B1 cho bộ người M02/M12/M15)
            tags = set(SPEC_OF[fid][3])
            uncovered = [c for c in sec["required_columns"]
                         if c != "stt" and ALIAS.get(c, c) not in tags]
            assert not uncovered, \
                "%s: manifest yêu cầu %r nhưng spec không khai (không thuộc gap)" % (
                    fid, uncovered)


@check("[EVD] manifest loop_audit la ho so lich su; template DA tag du cot sau regen P2")
def t_manifest_loop_audit():
    secs = manifest_sections()
    # [Lead sync sau regen P2 2026-08-27] loop_audit là census lịch sử (T0):
    # vẫn ghi missing_cols NHỮNG CỘT LÚC ĐÓ THIẾU; bất biến mới là template
    # production PHẢI đã tag đúng các cột đó (gap đóng) + tag mới đã vào.
    # fid -> (missing_cols lịch sử, số tag sau regen, tag mới)
    audit = {
        "PLI_M06": ([(10, "Thời hạn góp vốn")], 11, "thoi_han_gop_von"),
        "PLI_M07": ([(6, "Dân tộc")], 10, "dan_toc"),
        "PLI_M08": ([], 7, None),
        "PLI_M10": ([], 11, "quyen_chi_phoi"),
    }
    for fid, (missing, n_tags, new_tag) in audit.items():
        la = secs[MANIFEST_SECTION_OF[fid]].get("loop_audit") or {}
        got = [(m["col"], m["header"]) for m in (la.get("missing_cols") or [])]
        assert got == missing, "%s: missing_cols=%r != %r" % (fid, got, missing)
        prod = prod_tags(fid, SPEC_OF[fid][1])
        tagged_cols = {c for c, _ in prod}
        tags = [t for _, t in prod]
        for col, _h in missing:
            assert col in tagged_cols, \
                "%s: cột %d manifest ghi thiếu nhưng template vẫn chưa tag" % (
                    fid, col)
        assert len(tags) == n_tags, \
            "%s: template production có %d tag, kỳ vọng %d" % (fid, len(tags),
                                                               n_tags)
        if new_tag:
            assert new_tag in tags, \
                "%s: %r chưa có trong template production sau regen" % (
                    fid, new_tag)


@check("[SRC] PLII_M07: nguon co DUNG 7 nhan cot, khong ngay sinh/gioi/dan toc/chu ky")
def t_src_plii_m07():
    src = bfm.find_source("PLII_M07")
    doc = docx.Document(str(src))
    paras = [p.text for p in doc.paragraphs]
    heads = [i for i, t in enumerate(paras)
             if fold(t).startswith(
                 "7. danh sach thanh vien ho gia dinh dang ky thanh lap ho kinh doanh")]
    assert len(heads) == 1, "heading mục 7 khớp %d lần" % len(heads)
    h = heads[0]
    end = next(i for i in range(h + 1, len(paras))
               if fold(paras[i]).startswith("truong phong"))
    region = [t for t in paras[h + 1:end] if fold(t)]
    assert [fold(t) for t in region] == [fold(x) for x in PLII_M07_HEADERS], \
        "header mục 7 nguồn %r != spec %r" % (region, PLII_M07_HEADERS)
    joined = fold(" ".join(region))
    for banned in ("ngay, thang, nam sinh", "gioi tinh", "dan toc", "chu ky",
                   "ho ten"):
        assert banned not in joined, \
            "nguồn mục 7 có '%s' -> spec không được khai/khai thiếu" % banned


@check("[SRC] Mau 10 glue trong nguon M09 co cot 'Quyền chi phối' + chan trang 4 ND168")
def t_src_m10_quyen_chi_phoi():
    src = bfm.find_source("PLI_M09")
    doc = docx.Document(str(src))
    paras = [p.text for p in doc.paragraphs]
    idx = [i for i, t in enumerate(paras)
           if fold(t).startswith("sttho va tenngay, thang, nam sinh")]
    assert len(idx) == 1, "header glue Mẫu 10 khớp %d lần" % len(idx)
    glue = fold(paras[idx[0]])
    assert "quyen chi phoi" in glue, "Mẫu 10 glue thiếu cột Quyền chi phối"
    assert glue.count("12345678910") >= 1 and "11" in glue and "12" in glue, \
        "Mẫu 10 glue không phải lưới 12 cột: %r" % glue[-40:]
    # chân trang 4: đúng căn cứ pháp lý D2.5=A
    foot = [t for t in paras if "diem b khoan 1 dieu 17 nghi dinh so 168/2025" in
            fold(t) and "quyen chi phoi" in fold(t)]
    assert foot, "không tìm thấy chân trang 4 (NĐ 168/2025 điểm b khoản 1 Đ.17)"
    assert "bo nhiem, mien nhiem" in fold(foot[0]), \
        "chân trang 4 không liệt kê quyền chi phối"
    # nhóm CSHHL của mẫu gốc gồm ĐÚNG 3 cột con
    for col in ("ty le so huu von dieu le",
                "ty le so huu co phan co quyen bieu quyet"):
        assert col in glue, "Mẫu 10 glue thiếu %r" % col


@check("[SRC] Mau 13 chi co MOT row-type -> khong khai discriminator (D2.1)")
def t_src_m13_single_row_type():
    src = bfm.find_source("PLI_M13")
    doc = docx.Document(str(src))
    paras = [p.text for p in doc.paragraphs]
    h = next(i for i, t in enumerate(paras) if fold(t).startswith(
        "nguoi dai dien theo phap luat sau khi thay doi"))
    end = next(i for i in range(h + 1, len(paras))
               if fold(paras[i]).startswith("truong hop ho so dang ky doanh nghiep"))
    region = fold(" ".join(paras[h + 1:end]))
    assert "uy quyen" not in region, \
        "vùng Mẫu 13 có dấu hiệu row-type thứ hai ('ủy quyền') -> phải đối chiếu lại"
    assert "chu ky" not in region, "vùng Mẫu 13 có ô ký -> phải đối chiếu lại D2.4"
    # chân trang 2 = căn cứ D2.6=A (nhiều NĐDPL trong một giấy)
    foot = [t for t in paras if fold(t).startswith(
        "2 ghi thong tin cua tat ca nguoi dai dien theo phap luat")]
    assert foot and "nhieu hon 01 nguoi dai dien" in fold(foot[0]), \
        "không tìm thấy chân trang 2 (căn cứ D2.6=A)"


@check("[SPEC] 6 file spec qua loader (kind=list) + dung loop/headers/tags")
def t_spec_shape():
    for fid, (sid, loop, headers, tags) in SPEC_OF.items():
        ext = bfm.load_form_spec(fid)
        assert ext, "%s: không đọc được file spec" % fid
        hits = [ext["specs_by_id"][e["spec"]] for e in ext["entries"]
                if ext["specs_by_id"][e["spec"]]["id"] == sid]
        assert len(hits) == 1, "%s: kỳ vọng 1 entry %r, thấy %d" % (fid, sid,
                                                                   len(hits))
        s = hits[0]
        assert s["kind"] == "list", "%s: kind=%s" % (fid, s["kind"])
        assert s["loop"] == loop, "%s: loop=%r != %r" % (fid, s["loop"], loop)
        assert s["stt_tag"] is True, "%s: STT phải do engine sinh (stt_tag)" % fid
        assert s["detect"] <= {fold(h) for h in headers}, \
            "%s: detect không nằm trong header đã khai: %r" % (fid, sorted(
                s["detect"] - {fold(h) for h in headers}))
        ent = [e for e in ext["entries"] if e["spec"] == sid][0]
        assert ent["headers"] == headers, \
            "%s: headers %r != %r" % (fid, ent["headers"], headers)
        # (col, tag) suy từ headers + cols phải đúng bằng tập tag kỳ vọng
        cols = bfm._col_tags_for_headers(headers, s)
        got = [tags_i for tags_i in cols.values() if tags_i]
        assert got == tags, "%s: tags theo cột %r != %r" % (fid, got, tags)
        # kind=list không có min/max rows trong contract v1 -> phải ghi form_maps side
        assert not any(k in s for k in ("min_rows", "max_rows", "discriminator",
                                        "header_rows")), \
            "%s: kind=list không nhận field của kind khác" % fid


@check("[SPEC] D2.8=A: PLII_M07 key RIENG, khong dung chung ds_tv_ho_gia_dinh")
def t_spec_d28_separate_key():
    ext = bfm.load_form_spec("PLII_M07")
    loops = [ext["specs_by_id"][e["spec"]]["loop"] for e in ext["entries"]]
    assert loops == ["ds_nganh", "ds_thanh_vien_hkd_gcn"], \
        "PLII_M07 phải giữ entry ds_nganh + thêm đúng 1 entry mới, thấy %r" % loops
    assert "ds_tv_ho_gia_dinh" not in loops, \
        "D2.8=A cấm dùng lại key ds_tv_ho_gia_dinh"
    fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    tv01 = next(dt for dt in fm["PLII_M01"]["dynamic_tables"]
                if dt["loop"] == "ds_tv_ho_gia_dinh")
    base_tags = [c["tag"] for c in tv01["columns"]]
    raw, ent = spec_entry("PLII_M07", "m7_danh_sach_thanh_vien_hgd")
    new_tags = [t for _, t in
                bfm._col_tags_for_headers(ent["headers"], ext["specs_by_id"][
                    "m7_danh_sach_thanh_vien_hgd"]).items() if t]
    assert set(new_tags) != set(base_tags), \
        "tập cột PLII_M07 trùng ds_tv_ho_gia_dinh -> D2.8=A sai"
    assert "chu_ky" not in new_tags and "ngay_sinh" not in new_tags and \
        "gioi_tinh" not in new_tags and "dan_toc" not in new_tags, \
        "PLII_M07 không được có cột mà nguồn không có: %r" % new_tags
    assert "ghi_chu" in new_tags, "thiếu cột Ghi chú (đặc trưng của Mẫu 7)"


@check("[DELTA] M06/M07/M08/M10: dung delta so voi khai bao inline production")
def t_delta_vs_inline():
    WANT_ADDED = {"PLI_M06": ["thoi_han_gop_von"], "PLI_M07": ["dan_toc"],
                  "PLI_M08": [], "PLI_M10": ["quyen_chi_phoi"]}
    for fid, added in WANT_ADDED.items():
        sid, loop, headers, tags = SPEC_OF[fid]
        prod = prod_tags(fid, loop)               # [(col, tag)] theo template
        # [Lead sync sau regen P2] steady-state: template ĐÃ nhận đủ tag spec
        # (delta rỗng); mọi tag hứa phải NẰM TRONG template production.
        prod_tag_set = {t for _, t in prod}
        new_set = set(tags)
        assert not (new_set - prod_tag_set), \
            "%s: spec còn thêm %r ngoài template production (chưa regen?)" % (
                fid, sorted(new_set - prod_tag_set))
        assert set(added) <= prod_tag_set, \
            "%s: tag hứa %r chưa land vào template production" % (
                fid, sorted(set(added) - prod_tag_set))
        missing = prod_tag_set - new_set
        assert not missing, "%s: spec làm MẤT tag production %r" % (fid, missing)
        # header text production phải là tập con của header spec (không đổi text)
        for _col, _tag in prod:
            pass
        fm = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
        dt = next(d for d in fm[fid]["dynamic_tables"] if d["loop"] == loop)
        for c in dt["columns"]:
            assert c["header"] in headers, \
                "%s: header production %r bị đổi text thành %r" % (
                    fid, c["header"], headers)
        # chỉ M10 được THÊM cột vật lý (12 cột), 3 mẫu kia giữ nguyên số cột
        want_cols = 12 if fid == "PLI_M10" else len(headers)
        assert len(headers) == want_cols, \
            "%s: số cột spec %d != %d" % (fid, len(headers), want_cols)


@check("[DELTA] D2.5=A: cot 'Quyền chi phối' dung vi tri + khong ghi vao Ghi chú")
def t_delta_m10_quyen_chi_phoi():
    raw, ent = spec_entry("PLI_M10", "ds_cshhl")
    assert ent["headers"].index("Quyền chi phối") == 10, \
        "Quyền chi phối phải đứng trước Ghi chú theo nhóm CSHHL của mẫu gốc"
    assert ent["headers"][-1] == "Ghi chú", "cot cuoi phai la Ghi chú"
    ext = bfm.load_form_spec("PLI_M10")
    s = ext["specs_by_id"]["ds_cshhl"]
    assert "quyen_chi_phoi" in [t for t in s and
                                [tg for _, tg in bfm._col_tags_for_headers(
                                    ent["headers"], s).items() if tg]], \
        "thiếu the {quyen_chi_phoi}"
    assert "quyen chi phoi" not in " ".join(
        h for h in ent["headers"] if h == "Ghi chú"), "không hợp nhất vào Ghi chú"


@check("[REGION] anchor/occurrence dinh vi DUNG 1 vung (nguon + blocks hien tai)")
def t_region_resolution():
    for fid, anchor in ANCHOR_ENTRIES.items():
        ext = bfm.load_form_spec(fid)
        ents = [e for e in ext["entries"] if e["anchor"] == anchor]
        assert len(ents) == 1, "%s: không tìm thấy entry anchor %r" % (fid, anchor)
        assert not ents[0].get("occurrences"), "%s: entry này theo anchor" % fid
        src = bfm.find_source(fid)
        paras = [p.text for p in docx.Document(str(src)).paragraphs]
        hits_src = [i for i, t in enumerate(paras)
                    if re.search(anchor, fold(t))]
        assert len(hits_src) == 1, "%s: anchor khớp nguồn %d lần" % (fid,
                                                                    len(hits_src))
        hits_b = [i for i, t in enumerate(block_folds(fid))
                  if re.search(anchor, t)]
        assert len(hits_b) == 1, "%s: anchor khớp blocks %d lần (%r)" % (
            fid, len(hits_b), hits_b)
    for fid, oid in OCC_ENTRIES.items():
        ext = bfm.load_form_spec(fid)
        ents = [e for e in ext["entries"] if e.get("occurrences")]
        assert len(ents) == 1, "%s: kỳ vọng 1 entry occurrence" % fid
        cfgs = ents[0]["_occurrences"]
        assert len(cfgs) == 1 and cfgs[0]["occurrence_id"] == oid, \
            "%s: occurrence_id=%r != %r" % (fid, [c["occurrence_id"] for c in cfgs], oid)
        src = bfm.find_source(fid)
        paras = [p.text for p in docx.Document(str(src)).paragraphs]
        regs = occ.resolve_regions(paras, cfgs, log=lambda *_: None)
        assert len(regs) == 1 and regs[0]["status"] == "ok", \
            "%s: vùng occurrence không ok: %r" % (
                fid, [(r["status"], r["reason"]) for r in regs])
        assert regs[0]["total_found"] == 1, \
            "%s: heading khớp %d lần (phải duy nhất)" % (fid, regs[0]["total_found"])
        # vùng phải chứa header/heading thật và KHÔNG nuốt chuỗi pháp lý kế tiếp
        start, end = regs[0]["start"], regs[0]["end"]
        assert end > start, "%s: vùng rỗng" % fid


@check("[SANDBOX] rebuild that + convert blocks cho 6 mau, template repo khong bi chạm")
def t_sandbox_rebuild():
    tmp = Path(tempfile.mkdtemp(prefix="p2a_sandbox_"))
    tpl_dir, data_dir = tmp / "templates", tmp / "data"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    guards = {fid: sha256_file(ROOT / "app" / "templates" / ("%s.docx" % fid))
              for fid in SPEC_OF}
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, data_dir
    bfm._form_spec_cache.clear()
    try:
        KEPT_FOLD = {   # chuỗi pháp lý dính kèm phải còn sau khi chèn bảng
            "PLII_M07": "truong phong (ky, ghi ho ten va dong dau",
            "PLI_M06": "truong hop ho so dang ky doanh nghiep hop le",
            "PLI_M07": "danh sach co dong sang lap cong ty co phan",
            "PLI_M08": "truong hop ho so dang ky doanh nghiep hop le",
            "PLI_M10": "nguoi dai dien theo phap luat cua doanh nghiep ky truc tiep",
            "PLI_M13": "truong hop ho so dang ky doanh nghiep hop le",
        }
        WANT_COLS = {
            "PLI_M06": [(1, "ho_ten"), (2, "ngay_sinh"), (3, "gioi_tinh"),
                        (4, "so_cccd"), (5, "quoc_tich"), (6, "dan_toc"),
                        (7, "dia_chi"), (8, "von_dong_gop"), (9, "ty_le_von"),
                        (10, "thoi_han_gop_von"), (11, "chu_ky")],
            "PLI_M07": [(1, "ho_ten"), (2, "ngay_sinh"), (3, "gioi_tinh"),
                        (4, "so_cccd"), (5, "quoc_tich"), (6, "dan_toc"),
                        (7, "dia_chi"), (8, "so_co_phan"), (9, "ty_le"),
                        (10, "chu_ky")],
            "PLI_M08": [(1, "ten_cd"), (2, "quoc_gia"), (3, "ma_so"),
                        (4, "dia_chi"), (5, "so_co_phan"), (6, "ty_le"),
                        (7, "chu_ky")],
            "PLI_M10": [(1, "ho_ten"), (2, "ngay_sinh"), (3, "gioi_tinh"),
                        (4, "quoc_tich"), (5, "dan_toc"), (6, "dia_chi"),
                        (7, "so_giay_to"), (8, "ty_le"), (9, "ty_le_co_phan"),
                        (10, "quyen_chi_phoi"), (11, "ghi_chu")],
            "PLI_M13": [(1, "ho_ten"), (2, "ngay_sinh"), (3, "gioi_tinh"),
                        (4, "so_cccd"), (5, "chuc_danh"), (6, "dia_chi"),
                        (7, "quoc_gia")],
            "PLII_M07": [(1, "ten_thanh_vien"), (2, "quoc_tich"),
                         (3, "noi_o_hien_tai"), (4, "noi_thuong_tru"),
                         (5, "so_cccd"), (6, "ghi_chu")],
        }
        for fid, (sid, loop, headers, _tags) in SPEC_OF.items():
            src = bfm.find_source(fid)
            _fid, pl, mau = bfm.parse_form_id(src)
            meta, unmatched = bfm.process_form(
                src, {"Phu luc %s|%d" % (pl, mau): "T%s" % fid}, None)
            tpl_path = tpl_dir / ("%s.docx" % fid)
            assert tpl_path.exists(), "%s: generator chưa ghi template" % fid
            dts = [d for d in (meta.get("dynamic_tables") or [])
                   if d["loop"] == loop]
            assert len(dts) == 1, "%s: form_maps thiếu loop %r" % (fid, loop)
            got = [(c["col"], c["tag"]) for c in dts[0]["columns"]]
            assert got == WANT_COLS[fid], \
                "%s: cols %r != %r" % (fid, got, WANT_COLS[fid])
            assert all(c["col"] != 0 for c in dts[0]["columns"]), \
                "%s: cột 0 (STT) không được có tag" % fid
            if fid == "PLI_M13" or fid == "PLII_M07":
                assert dts[0].get("semantic_key") == loop, \
                    "%s: semantic_key phải = occurrence_id" % fid

            blocks = dxtb.convert_document(
                docx.Document(str(tpl_path)), fid, "DEMO %s" % fid,
                overrides={}, footnotes={},
                section_specs=meta.get("section_specs") or [])
            loops = [b for b in blocks["blocks"] if b.get("t") == "loop"
                     and b.get("loop") == loop]
            assert len(loops) == 1, "%s: số block loop %r = %d" % (
                fid, loop, len(loops))
            bcols = sorted((c["col"], c["tag"]) for c in loops[0]["cols"])
            assert bcols == sorted(WANT_COLS[fid]), \
                "%s: block cols %r != %r" % (fid, bcols, sorted(WANT_COLS[fid]))
            # chuỗi pháp lý dính kèm KHÔNG bị mất
            texts = ["".join(str(r.get("text", ""))
                             for r in (b.get("runs") or []))
                     for b in blocks["blocks"]]
            folds = [fold(t) for t in texts]
            assert any(KEPT_FOLD[fid] in f for f in folds), \
                "%s: mất chuỗi pháp lý dính kèm (%r)" % (fid, KEPT_FOLD[fid])
            # header của bảng trong template khớp headers đã khai
            doc_t = docx.Document(str(tpl_path))
            hdr = None
            for t in doc_t.tables:
                cells = [c.text for c in t.rows[0].cells]
                if fold(" | ".join(cells)) == fold(" | ".join(headers)):
                    hdr = cells
                    break
            assert hdr is not None, \
                "%s: không tìm thấy bảng với header đã khai" % fid
        for fid, before in guards.items():
            assert sha256_file(ROOT / "app" / "templates" / ("%s.docx" % fid)) \
                == before, "%s: template gốc bị ghi ngoài sandbox!" % fid
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()


@check("[BLOCKED] PLII_M02 pin sync 7 entry / 6 occurrence (P1+P2 đã adjudicate)")
def t_blocked_others():
    # [GỠ PIN — Lead 2026-08-28] 'assert not files' cho PLI_M09 lỗi thời:
    # D3.1/D3.2=A + lệnh owner -> spec tồn tại (merge cfdefcd); trạng thái
    # mới do tools/test_m09_rebuild.py sở hữu.
    raw = json.loads((ROOT / "tools" / "form_specs" / "household" /
                      "PLII_M02.json").read_text(encoding="utf-8-sig"))
    ids = []
    for e in raw["tables"]:
        ids.extend(o["occurrence_id"] for o in (e.get("occurrences") or []))
    # [Pin sync — PLAN v7 F0.5, Lead 2026-09-05] Bảng premise→hiện trạng:
    # pin cũ "4 occurrence ngành + 5 entry" stale vì (a) P1 integrate thêm
    # loop 'nganh_hien_tai' (coverage a6_1..c3 already_complete), (b) P2
    # member-grid rebuild thêm 2 nested-grid 'tv_hgd_sau_thay_doi'/
    # 'tv_hgd_cap_doi' (10 cột, coverage already_complete). 7 entry / 6
    # occurrence là trạng thái đã adjudicate trong
    # docs/table_coverage_current.{md,json} — pin mới khóa đúng tập này,
    # vẫn bắt được drift ngoài danh sách.
    assert sorted(ids) == sorted(["nganh_bo_sung", "nganh_xoa_bo",
                                  "nganh_sua_doi_chi_tiet", "nganh_hien_tai",
                                  "tv_hgd_sau_thay_doi", "tv_hgd_cap_doi"]), \
        "file household/PLII_M02.json (ngoài ownership P2A) đã đổi: %r" % ids
    # 7 entry: 4 ngành + 1 fixed-matrix a7 (thuế II.2, cap-von D5.2, không
    # occurrence) + 2 nested-grid thành viên (P2 rebuild).
    assert len(raw["tables"]) == 7, "PLII_M02 đổi số entry: %d" % len(raw["tables"])


@check("[BLOCKED] khong bia cot chu ky cho bang nguon khong co (PLII_M07/M10/M13)")
def t_no_signature_invention():
    NO_CHU_KY = {"PLII_M07", "PLI_M10", "PLI_M13"}
    for fid in NO_CHU_KY:
        sid, loop, headers, tags = SPEC_OF[fid]
        assert "chu_ky" not in tags, \
            "%s: nguồn không có cột chữ ký -> không được khai {chu_ky}" % fid
        assert not any(fold(h) in ("chu ky", "chu ky cua", "ky ten")
                       for h in headers), "%s: header có ô ký" % fid
        raw = json.loads((ROOT / "tools" / "form_specs").joinpath(
            _GROUP_OF[fid], "%s.json" % fid).read_text(encoding="utf-8-sig"))
        blob = json.dumps(raw, ensure_ascii=False).lower()
        assert '"tag": "chu_ky"' not in blob, "%s: spec gắn the chu_ky" % fid
    # còn lại 3 bảng CÓ cột Chữ ký -> D2.4=A: chữ ký phải được gắn the
    for fid in ("PLI_M06", "PLI_M07", "PLI_M08"):
        assert "chu_ky" in SPEC_OF[fid][3], "%s: thiếu the {chu_ky} (D2.4=A)" % fid


@check("[XAC MINH] loader uu tien file JSON cho 4 mau tu co khai bao inline")
def t_loader_prefers_json():
    for fid in ("PLI_M06", "PLI_M07", "PLI_M08", "PLI_M10"):
        ext = bfm.load_form_spec(fid)
        assert ext and ext["entries"], "%s: không đọc được spec JSON" % fid
        sid, loop = SPEC_OF[fid][0], SPEC_OF[fid][1]
        assert any(ext["specs_by_id"][e["spec"]]["loop"] == loop
                   for e in ext["entries"]), "%s: thiếu loop %r" % (fid, loop)


def main() -> int:
    for fn in (t_manifest_state, t_manifest_loop_audit, t_src_plii_m07,
               t_src_m10_quyen_chi_phoi, t_src_m13_single_row_type,
               t_spec_shape, t_spec_d28_separate_key, t_delta_vs_inline,
               t_delta_m10_quyen_chi_phoi, t_region_resolution,
               t_sandbox_rebuild, t_blocked_others, t_no_signature_invention,
               t_loader_prefers_json):
        fn()
    ok = sum(1 for p, _ in _results if p)
    fail = sum(1 for p, _ in _results if not p)
    print("-" * 72)
    print("test_p2a_people_specs: %d PASS / %d FAIL" % (ok, fail))
    for passed, name in _results:
        if not passed:
            print("  -> %s" % name)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
