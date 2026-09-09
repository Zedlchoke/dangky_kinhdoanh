# -*- coding: utf-8 -*-
"""test_wave2_fixture_lane.py — hồi quy cho các fix lớp B (wave2-fixture).

Pin từng finding corpus đã adjudicate, KHÔNG cần soffice/export:

  B1  _nest (app_web/main.py) không được đè LIST dòng grid của form khác
      bằng dict từ key dotted trùng prefix (bảng ngành/CSHHL/thành viên mất
      dòng trên PLI_M01/02/03, PLII_M01/02/07, PLI_M10/11); kèm test mức
      fixture-merge gọi ĐÚNG merge_fixture_data mà run_export dùng.
  B2  slot ngày thành phần phải CÙNG namespace: cột grid ngày (ngay_sinh/
      ngay_cap) nhận FULL dd/mm/yyyy dù form có bộ 3 scalar trần của chủ
      thể khác; bộ 3 scalar THẬT (trần và 'gd.'/'kt.') vẫn nhận ngày (dd);
      cụm 3-ô TRONG cùng loop (tổng hợp) vẫn nhận ngày.
  B3  'bằng chữ' (_chu/bang_chu) và 'tỷ lệ' (ty_le/phan_tram) phải thắng
      họ 'von': von_dieu_le_chu trả chữ có 'đồng', ty_le_so_von_dieule/
      ty_le_von trả % 0-100, von_dieu_le vẫn trả số.
  B4  cụm loại-trừ tick ĐÚNG 1 ô trong choice-variants: (a) la_nganh_chinh
      chỉ dòng đầu; (b) cặp Có/Không đất đảo + hiển thị GTNT; (c) tình
      trạng thành lập; (d) M12 tách/sáp nhập; (e) PLII_M02 thay đổi chủ hộ;
      kèm sweep toàn corpus + validator V1/V1b.
  B5  inventory động: active_form_ids loại PLI_M11 (REMOVED_BY_CURRENT_LAW);
      render-unit/fixture = non72 + M72 variants (90 ở corpus hiện tại).

Chạy:  python3 -X utf8 -m tools.test_wave2_fixture_lane
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_web.main import _nest                       # noqa: E402
from tools.phase5_fixtures import (                  # noqa: E402
    EXCLUSIVE_GROUPS, ValueFactory, active_form_ids, build_fixture,
    chk_groups, validate_fixture,
)
from tools.phase5_visual_gate import merge_fixture_data  # noqa: E402

MAPS = json.loads((ROOT / "app" / "data" / "form_maps.json")
                  .read_text(encoding="utf-8"))
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
ACTIVE_IDS, SKIPPED = active_form_ids(MAPS)


def _blocks(fid: str) -> dict:
    p = BLOCKS_DIR / ("%s.json" % fid)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _fixture(fid: str, fixture: str) -> dict:
    return build_fixture(fid, MAPS[fid], fixture, _blocks(fid),
                         ValueFactory())


def _ticked(data: dict) -> set:
    return {k for k, v in data.items()
            if k.startswith("chk") and str(v or "").strip()}


def _exactly_one(ticked: set, keys: list) -> bool:
    return sum(1 for k in keys if k in ticked) == 1


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
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


# ---------------------------------------------------------------------------
# B1 — _nest giữ nguyên list
# ---------------------------------------------------------------------------

@check("[B1-unit] _nest: list sẵn có + key dotted trùng prefix -> list còn "
       "nguyên, dotted bị bỏ, dotted khác vẫn lồng đúng")
def b1_unit():
    flat = {
        "ds_nganh": [{"ma_nganh": "0111", "la_nganh_chinh": "X"},
                     {"ma_nganh": "0112"}],
        "ds_nganh.la_nganh_chinh": "x",
        "ds_nganh.ten_nganh": "Trồng lúa",
        "dn.ten_tieng_viet": "CÔNG TY TNHH A",
    }
    nested = _nest(flat)
    assert isinstance(nested.get("ds_nganh"), list) and \
        len(nested["ds_nganh"]) == 2, nested.get("ds_nganh")
    # dotted trùng prefix bị bỏ (không được đè, không được nhét vào list)
    assert "la_nganh_chinh" not in nested and "ten_nganh" not in nested, \
        nested.keys()
    # key dotted KHÔNG xung đột vẫn lồng đúng
    assert nested["dn"]["ten_tieng_viet"] == "CÔNG TY TNHH A"
    # thứ tự ngược (list tới SAU dotted) cũng phải thắng
    nested2 = _nest({"ds_nganh.la_nganh_chinh": "x",
                     "ds_nganh": [{"ma_nganh": "0111"}]})
    assert isinstance(nested2.get("ds_nganh"), list), nested2.get("ds_nganh")
    # scalar sẵn có ở node trung gian cũng được giữ (không đè bằng dict)
    nested3 = _nest({"x": "5", "x.y": "7"})
    assert nested3.get("x") == "5", nested3.get("x")


@check("[B1-merge] merge_fixture_data (hàm run_export dùng) + _nest trên "
       "toàn corpus: mọi loop của mọi form active còn là LIST")
def b1_merge():
    for fixture in ("valid-full", "choice-variants"):
        data = merge_fixture_data(MAPS, {}, fixture, ACTIVE_IDS)
        # pin điều kiện phát sinh lỗi: flat chứa VỪA list 'ds_nganh' VỪA key
        # dotted mirror 'ds_nganh.la_nganh_chinh' (cơ chế phá list cũ)
        assert "ds_nganh" in data and "ds_nganh.la_nganh_chinh" in data
        nested = _nest(data)
        lost = []
        for fid in ACTIVE_IDS:
            for t in MAPS[fid].get("dynamic_tables", []):
                if not isinstance(nested.get(t["loop"]), list):
                    lost.append("%s/%s" % (fid, t["loop"]))
        assert not lost, "loop bị phá sau _nest: %s" % lost[:10]


# ---------------------------------------------------------------------------
# B2 — slot ngày thành phần theo namespace
# ---------------------------------------------------------------------------

_FULL_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_DAY_ONLY = re.compile(r"^\d{2}$")


@check("[B2-grid] cột grid ngày (ngay_sinh/ngay_cap) nhận FULL dd/mm/yyyy "
       "kể cả khi form có bộ 3 scalar trần của chủ thể khác")
def b2_grid():
    cases = [("PLII_M01", "ds_tv_ho_gia_dinh", "ngay_sinh"),
             ("PLI_M02", "ds_nddpl_uy_quyen_chu_so_huu", "ngay_sinh"),
             ("PLI_M06", "ds_thanh_vien_tnhh", "ngay_sinh"),
             ("PLI_M10", "ds_cshhl", "ngay_sinh"),
             ("PLI_M11", "ds_cshhl", "ngay_cap")]
    for fid, loop, tag in cases:
        if fid not in MAPS:
            continue  # form có thể bị owner loại khỏi catalog sau này
        data = _fixture(fid, "valid-full")
        rows = data.get(loop)
        assert isinstance(rows, list) and rows, "%s/%s mất dòng" % (fid, loop)
        for row in rows:
            val = str(row.get(tag) or "")
            assert _FULL_DATE.match(val), \
                "%s/%s.%s = %r (mong full date)" % (fid, loop, tag, val)


@check("[B2-scalar] bộ 3 scalar THẬT cùng namespace vẫn nhận NGÀY (dd): "
       "trần (ngay_sinh/ngay_bd), gd./kt., và cụm 3-ô trong cùng loop "
       "(tổng hợp)")
def b2_scalar():
    # trần: PLI_M01 có scalar ngay_sinh/thang_sinh/nam_sinh
    data = _fixture("PLI_M01", "valid-full")
    assert _DAY_ONLY.match(str(data["ngay_sinh"])), data["ngay_sinh"]
    assert _DAY_ONLY.match(str(data["gd.ngay_sinh"])), data["gd.ngay_sinh"]
    assert _DAY_ONLY.match(str(data["kt.ngay_sinh"])), data["kt.ngay_sinh"]
    assert _DAY_ONLY.match(str(data["ngay_bd"])), data["ngay_bd"]
    # tổng hợp: loop CÓ ĐỦ 3 cột ngay_X/thang_X/nam_X -> ngày (dd)
    fm = {"fields": [],
          "dynamic_tables": [{"loop": "ds_tv", "columns": [
              {"tag": "ho_ten"}, {"tag": "ngay_sinh"},
              {"tag": "thang_sinh"}, {"tag": "nam_sinh"}]}]}
    data = build_fixture("PLI_M00X", fm, "valid-full", {}, ValueFactory())
    row = data["ds_tv"][0]
    assert _DAY_ONLY.match(str(row["ngay_sinh"])), row["ngay_sinh"]
    assert _DAY_ONLY.match(str(row["thang_sinh"])), row["thang_sinh"]
    # ...nhưng loop CHỈ có cột ngày (không đủ bộ 3) -> FULL date
    fm2 = {"fields": [],
           "dynamic_tables": [{"loop": "ds_tv", "columns": [
               {"tag": "ho_ten"}, {"tag": "ngay_sinh"}]}]}
    data2 = build_fixture("PLI_M00Y", fm2, "valid-full", {}, ValueFactory())
    assert _FULL_DATE.match(str(data2["ds_tv"][0]["ngay_sinh"])), \
        data2["ds_tv"][0]["ngay_sinh"]


# ---------------------------------------------------------------------------
# B3 — ưu tiên 'bằng chữ' / 'tỷ lệ' trước họ von
# ---------------------------------------------------------------------------

@check("[B3-value] von_dieu_le (số) / von_dieu_le_chu (chữ có 'đồng') / "
       "ty_le_so_von_dieule + ty_le_von (0-100)")
def b3_value():
    f = ValueFactory()
    von = f.value("von_dieu_le")
    assert re.match(r"^\d+$", von) and int(von) >= 100000000, von
    chu = f.value("von_dieu_le_chu")
    assert "đồng" in chu.lower() and not re.match(r"^\d+$", chu), chu
    ty_le = int(f.value("ty_le_so_von_dieule"))
    assert 0 <= ty_le <= 100, ty_le
    ty_le_von = int(f.value("ty_le_von"))
    assert 0 <= ty_le_von <= 100, ty_le_von
    # đường _fallback_value (key không rơi nhánh chuyên dụng của value())
    from tools.phase5_fixtures import _fallback_value
    fb = _fallback_value(f, "ty_le_von_khac", 3, "", "tỷ lệ vốn khác")
    assert re.match(r"^\d+$", fb) and 0 <= int(fb) <= 100, fb


# ---------------------------------------------------------------------------
# B4 — cụm loại-trừ tick đúng 1
# ---------------------------------------------------------------------------

@check("[B4a] la_nganh_chinh: chỉ dòng đầu nhận 'X', các dòng còn trống "
       "(PLI_M72 ×2 loop, PLI_M01, mọi fixture có dòng)")
def b4a_la_nganh_chinh():
    for fid, loops in (("PLI_M72", ("ds_nganh_dntn", "ds_nganh_ctcp")),
                       ("PLI_M01", ("ds_nganh",))):
        for fixture in ("valid-full", "choice-variants", "long-boundary"):
            data = _fixture(fid, fixture)
            for loop in loops:
                marks = [str(r.get("la_nganh_chinh") or "")
                         for r in data[loop]]
                assert marks[0] == "X", (fid, fixture, loop, marks[:3])
                assert all(m == "" for m in marks[1:]), \
                    (fid, fixture, loop, marks[:3])


@check("[B4b] cặp Có/Không 'đất đảo' + 'hiển thị GTNT': đúng 1 ô mỗi cặp "
       "(PLI_M02/03/04/05/12)")
def b4b_co_khong_pairs():
    dat_dao = ["chk_auto_co", "chk_auto_khong"]
    for fid in ("PLI_M02", "PLI_M03", "PLI_M04", "PLI_M05", "PLI_M12"):
        tk = _ticked(_fixture(fid, "choice-variants"))
        assert _exactly_one(tk, dat_dao), \
            "%s đất đảo tick: %s" % (fid, sorted(tk & set(dat_dao)))
    gtnt = ["chk_auto_co_hien_thi_thong_tin_ve_gia_tri_tuong_d",
            "chk_auto_khong_2"]
    for fid in ("PLI_M03", "PLI_M04", "PLI_M05"):
        tk = _ticked(_fixture(fid, "choice-variants"))
        assert _exactly_one(tk, gtnt), \
            "%s GTNT tick: %s" % (fid, sorted(tk & set(gtnt)))
    # PLI_M02 dùng cặp generic cho GTNT; PLI_M12 có THÊM cặp GTNT thứ hai
    tk2 = _ticked(_fixture("PLI_M02", "choice-variants"))
    assert _exactly_one(tk2, ["chk_auto_co_2", "chk_auto_khong_2"]), \
        "PLI_M02 GTNT (generic) tick sai"
    tk12 = _ticked(_fixture("PLI_M12", "choice-variants"))
    assert _exactly_one(tk12, gtnt), "PLI_M12 GTNT 1 tick sai"
    assert _exactly_one(
        tk12, ["chk_auto_co_hien_thi_thong_tin_ve_gia_tri_tuong_d_2",
               "chk_auto_khong_3"]), "PLI_M12 GTNT 2 tick sai"


@check("[B4c] cụm 'tình trạng thành lập' đúng 1 ô (PLI_M02/03/04/05)")
def b4c_thanh_lap():
    cluster = ["chk_tt_thanh_lap_moi", "chk_tt_tach_dn", "chk_tt_chia_dn",
               "chk_tt_hop_nhat_dn", "chk_tt_chuyen_doi_loai_hinh",
               "chk_tt_chuyen_doi_tu_hkd", "chk_tt_chuyen_doi_tu_csbt"]
    for fid in ("PLI_M02", "PLI_M03", "PLI_M04", "PLI_M05"):
        tk = _ticked(_fixture(fid, "choice-variants"))
        present = [k for k in cluster if k in
                   {f["key"] for f in MAPS[fid]["fields"]}]
        assert _exactly_one(tk, present), \
            "%s tick %s" % (fid, sorted(tk & set(present)))


@check("[B4d] PLI_M12 cụm tách/sáp nhập đúng 1 ô")
def b4d_tach_sap():
    tk = _ticked(_fixture("PLI_M12", "choice-variants"))
    assert _exactly_one(tk, ["chk_tt_tach_dn", "chk_tt_sap_nhap_dn"]), \
        sorted(tk & {"chk_tt_tach_dn", "chk_tt_sap_nhap_dn"})


@check("[B4e] PLII_M02 'thay đổi chủ hộ do' đúng 1 ô; cặp chủ thể cũng "
       "đúng 1 (member chung chk_ct_ho_gia_dinh thỏa cả hai cụm)")
def b4e_pliim02():
    tk = _ticked(_fixture("PLII_M02", "choice-variants"))
    assert _exactly_one(tk, ["chk_ct_ho_gia_dinh",
                             "chk_auto_chu_ho_kinh_doanh_chet_hoac_"
                             "bi_toa_an_tu"]), sorted(tk)
    assert _exactly_one(tk, ["chk_ct_ca_nhan", "chk_ct_ho_gia_dinh"]), \
        sorted(tk)


@check("[B4-sweep] toàn corpus: mọi cụm loại-trừ của mọi form active có "
       "ĐÚNG 1 ô tick trong choice-variants")
def b4_sweep():
    bad = []
    for fid in ACTIVE_IDS:
        data = _fixture(fid, "choice-variants")
        tk = _ticked(data)
        for members in chk_groups(MAPS[fid], _blocks(fid)):
            n = sum(1 for k in members if k in tk)
            if n != 1:
                bad.append("%s %s=%d" % (fid, members[0], n))
    assert not bad, bad[:10]


@check("[B4-validator] V1 chặn tick 2, V1b chặn tick 0 cho choice-variants")
def b4_validator():
    fm = {"fields": [
        {"key": "chk_a", "type": "chk"}, {"key": "chk_b", "type": "chk"}],
        "dynamic_tables": []}
    blocks = {"blocks": [
        {"t": "chk", "key": "chk_a", "label": "Có"},
        {"t": "chk", "key": "chk_b", "label": "Không"}]}
    groups = chk_groups(fm, blocks)
    assert groups == [["chk_a", "chk_b"]], groups
    two = validate_fixture(fm, blocks, {"chk_a": "X", "chk_b": "X"},
                           "choice-variants")
    assert any(e.startswith("V1:") for e in two), two
    none = validate_fixture(fm, blocks, {}, "choice-variants")
    assert any(e.startswith("V1b:") for e in none), none
    one = validate_fixture(fm, blocks, {"chk_a": "X"}, "choice-variants")
    assert not one, one
    # fixture khác (valid-full không tick chk) KHÔNG bị V1b bắt
    ok_full = validate_fixture(fm, blocks, {}, "valid-full")
    assert not any(e.startswith("V1") for e in ok_full), ok_full


@check("[B4-registry] EXCLUSIVE_GROUPS: pattern mới có mặt, pattern generic "
       "co/không đã bỏ (thay bằng cụm khối)")
def b4_registry():
    names = [n for n, _p, _k in EXCLUSIVE_GROUPS]
    assert "thay_doi_chu_ho_hkd" in names, names
    assert "co_khong" not in names and "auto_co_khong" not in names, names
    tt = [p for n, p, _k in EXCLUSIVE_GROUPS
          if n == "tinh_trang_thanh_lap"][0]
    assert "sap_nhap_dn" in tt, tt
    # đồng bộ bên runtime (form-domain.js) — 2 gid mới phải xuất hiện
    js = (ROOT / "app_web" / "ui" / "form-domain.js").read_text(
        encoding="utf-8")
    assert "thay_doi_chu_ho_hkd" in js and "tinh_trang_thanh_lap" in js, \
        "EXCLUSIVE_CHK_GROUPS chưa đồng bộ"


# ---------------------------------------------------------------------------
# B5 — inventory động
# ---------------------------------------------------------------------------

@check("[B5] active_form_ids loại PLI_M11 (REMOVED_BY_CURRENT_LAW); "
       "render-unit/fixture = non72 + M72 variants (đếm động)")
def b5_inventory():
    assert ("PLI_M11", "removed_by_current_law") in SKIPPED, SKIPPED
    assert "PLI_M11" not in ACTIVE_IDS
    assert "PLI_M72" in ACTIVE_IDS
    non72 = [f for f in ACTIVE_IDS if f != "PLI_M72"]
    render_units = len(non72) + 5  # 5 = len(M72_VARIANTS)
    assert len(ACTIVE_IDS) == 86, len(ACTIVE_IDS)
    assert render_units == 90, render_units


def main() -> int:
    for fn in (b1_unit, b1_merge, b2_grid, b2_scalar, b3_value,
               b4a_la_nganh_chinh, b4b_co_khong_pairs, b4c_thanh_lap,
               b4d_tach_sap, b4e_pliim02, b4_sweep, b4_validator,
               b4_registry, b5_inventory):
        fn()
    fails = [r for r in _results if not r[0]]
    print("-" * 60)
    print("test_wave2_fixture_lane: %d PASS / %d FAIL"
          % (len(_results) - len(fails), len(fails)))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
