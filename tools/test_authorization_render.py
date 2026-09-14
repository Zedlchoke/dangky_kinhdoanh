# -*- coding: utf-8 -*-
"""I4 — render hồ sơ ủy quyền (DOCX + ZIP + snapshot).

Chạy: python -X utf8 -m tools.test_authorization_render   (exit 0 = PASS)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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


def _with_temp_store():
    tmp = tempfile.mkdtemp(prefix="dkkd_auth_render_")
    os.environ["DKKD_AUTH_DATA_DIR"] = tmp
    import importlib
    import tools.authorization_store as store
    import tools.authorization_render as render
    importlib.reload(store)
    importlib.reload(render)
    return store, render, Path(tmp)


@check("AUTH-R01: build_render_payload DN")
def t_payload_dn():
    _store, render, _tmp = _with_temp_store()
    payload = render.build_render_payload(
        "thanh_lap_tnhh_1tv",
        "Thành lập TNHH 1TV",
        {
            "dn.ten_tieng_viet": "Công ty ABC",
            "dn.ma_so_dn": "0123456789",
            "dn.dia_chi_tru_so": "123 Lê Lợi, Hà Nội",
            "ndd.ho_ten": "Nguyễn Văn A",
            "ndd.chuc_vu": "Giám đốc",
        },
        {
            "ho_ten": "Trần Lan",
            "so_cccd": "001234567890",
            "ngay_sinh": "01/01/1990",
        },
        "thành lập doanh nghiệp",
        "Phòng ĐKKD",
        "31/12/2026",
    )
    assert payload["uy_quyen_ten_chu_the"] == "Công ty ABC"
    assert payload["agent_ho_ten"] == "Trần Lan"
    assert payload["co_quan_tiep_nhan"] == "Phòng ĐKKD"


@check("AUTH-R02: build_render_payload HKD")
def t_payload_hkd():
    _store, render, _tmp = _with_temp_store()
    payload = render.build_render_payload(
        "dang_ky_ho_kinh_doanh_lan_dau",
        "Đăng ký HKD",
        {
            "hkd_ten_tieng_viet": "Hộ kinh doanh XYZ",
            "chu_hkd.ho_ten": "Lê B",
            "chu_hkd.so_cccd": "098765432109",
            "dia_chi_chi_tiet": "45 Trần Phú",
            "xa_phuong": "Phường 1",
            "tinh_thanh": "Đà Nẵng",
        },
        {"ho_ten": "Minh Long", "so_cccd": "001122334455"},
        "đăng ký hộ kinh doanh",
        "",
        "",
    )
    assert payload["uy_quyen_ten_chu_the"] == "Hộ kinh doanh XYZ"
    assert payload["uy_quyen_nguoi_ky"] == "Lê B"
    assert "Đà Nẵng" in payload["uy_quyen_dia_chi"]


@check("AUTH-R03: generate_package DN — DOCX + ZIP + snapshot")
def t_generate_dn():
    store, render, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Nguyễn Văn Minh Long",
        "so_cccd": "001234567890",
        "dien_thoai": "0901234567",
    })
    res = render.generate_package(
        "thanh_lap_tnhh_1tv",
        "Thành lập TNHH 1TV",
        agent_id,
        {
            "dn.ten_tieng_viet": "Công ty Test",
            "ndd.ho_ten": "Người ký",
            "ndd.chuc_vu": "Giám đốc",
        },
    )
    assert res["ok"] is True, res
    out_dir = Path(res["dir"])
    assert out_dir.is_dir()
    assert (out_dir / "AUTH-UQ-DN-01.docx").is_file()
    assert (out_dir / "ho_so_uy_quyen.zip").is_file()
    assert (out_dir / "MANIFEST.json").is_file()
    with zipfile.ZipFile(out_dir / "ho_so_uy_quyen.zip") as zf:
        names = zf.namelist()
        assert "AUTH-UQ-DN-01.docx" in names
    draft = store.get_authorization_draft(res["authorization_id"])
    assert draft["ok"] is True
    assert draft.get("frozen") is True
    snap = draft["authorization"]
    assert snap["payload"]["uy_quyen_ten_chu_the"] == "Công ty Test"


@check("AUTH-R04: generate_package thiếu dữ liệu — báo lỗi")
def t_generate_missing():
    store, render, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Agent",
        "so_cccd": "001234567890",
    })
    res = render.generate_package(
        "thanh_lap_tnhh_1tv",
        "Thành lập",
        agent_id,
        {},
    )
    assert res["ok"] is False
    assert res.get("errors")


@check("AUTH-R05: hợp đồng placeholder — mẫu owner ⊆ payload keys")
def t_template_contract():
    from tools.authorization_template_contract import validate_all_templates

    res = validate_all_templates()
    assert res["ok"] is True, res
    for t in res["templates"]:
        assert t["ok"] is True, t
        assert len(t["tags"]) >= 10, t


@check("AUTH-R06: render mẫu owner — không còn tag sót (DN + HKD)")
def t_render_owner_templates():
    import tempfile
    from tools.docx_render import check_output, write_rendered
    from tools.authorization_template_contract import TEMPLATE_FILES

    _store, render, _tmp = _with_temp_store()
    base_payload = render.build_render_payload(
        "thanh_lap_tnhh_1tv",
        "Thành lập",
        {
            "dn.ten_tieng_viet": "Công ty Kiểm thử",
            "dn.ma_so_dn": "0312345678",
            "dn.dia_chi_tru_so": "1 Test",
            "ndd.ho_ten": "Người A",
            "ndd.chuc_vu": "Giám đốc",
        },
        {
            "ho_ten": "Agent X",
            "so_cccd": "001234567890",
            "ngay_sinh": "01/01/1990",
            "ngay_cap": "01/01/2020",
            "noi_cap": "CA HN",
            "dia_chi_lien_he": "HN",
            "dien_thoai": "090",
            "email": "a@b.c",
        },
        "thành lập doanh nghiệp",
        "Phòng ĐKKD",
        "31/12/2026",
    )
    hkd_payload = render.build_render_payload(
        "dang_ky_ho_kinh_doanh_lan_dau",
        "HKD",
        {
            "hkd_ten_tieng_viet": "Hộ Test",
            "chu_hkd.ho_ten": "Chủ B",
            "chu_hkd.so_cccd": "098765432109",
            "dia_chi_chi_tiet": "2 Test",
            "tinh_thanh": "HCM",
        },
        {
            "ho_ten": "Agent X",
            "so_cccd": "001234567890",
        },
        "đăng ký hộ kinh doanh",
        "Phòng ĐKKD",
        "31/12/2026",
    )
    with tempfile.TemporaryDirectory() as td:
        for tid, payload in (
            ("AUTH-UQ-DN-01", base_payload),
            ("AUTH-UQ-HKD-01", hkd_payload),
        ):
            src = TEMPLATE_FILES[tid]
            out = Path(td) / ("%s_out.docx" % tid)
            write_rendered(src, payload, out)
            ok, msg = check_output(out)
            assert ok is True, "%s: %s" % (tid, msg)


def main() -> int:
    t_payload_dn()
    t_payload_hkd()
    t_generate_dn()
    t_generate_missing()
    t_template_contract()
    t_render_owner_templates()
    failed = [n for ok, n in _results if not ok]
    print("\n%d/%d PASS" % (len(_results) - len(failed), len(_results)))
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
