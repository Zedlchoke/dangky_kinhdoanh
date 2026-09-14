# -*- coding: utf-8 -*-
"""I1 — SQLite profile store + backup/restore (module ủy quyền dịch vụ).

Chạy: python -X utf8 -m tools.test_authorization_store   (exit 0 = PASS)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
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
    tmp = tempfile.mkdtemp(prefix="dkkd_auth_test_")
    os.environ["DKKD_AUTH_DATA_DIR"] = tmp
    # Re-import để module đọc env mới
    import importlib
    import tools.authorization_store as store
    importlib.reload(store)
    return store, Path(tmp)


@check("AUTH-01: fresh install — DB rỗng, không profile")
def t_fresh():
    store, tmp = _with_temp_store()
    info = store.store_info()
    assert info["active_profiles"] == 0
    assert info["db_exists"] is True
    assert str(tmp) in info["data_dir"]


@check("AUTH-02: save + list profile")
def t_save_list():
    store, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    res = store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Nguyễn Văn Minh Long",
        "so_cccd": "001234567890",
        "dien_thoai": "0901234567",
        "email": "minhlong@example.com",
    })
    assert res["ok"] is True
    listed = store.list_agent_profiles()
    assert len(listed["profiles"]) == 1
    assert listed["profiles"][0]["ho_ten"] == "Nguyễn Văn Minh Long"


@check("AUTH-03: cập nhật CCCD — cùng agent_id, giá trị mới")
def t_update_cccd():
    store, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Trần Lan",
        "so_cccd": "001111111111",
    })
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Trần Lan",
        "so_cccd": "009999999999",
        "ngay_cap": "01/01/2020",
    })
    got = store.get_agent_profile(agent_id)
    assert got["profile"]["so_cccd"] == "009999999999"
    assert got["profile"]["ngay_cap"] == "01/01/2020"


@check("AUTH-04: thiếu ho_ten → MISSING_REQUIRED")
def t_missing_required():
    store, _tmp = _with_temp_store()
    res = store.save_agent_profile({"so_cccd": "001234567890"})
    assert res["ok"] is False
    codes = [e["code"] for e in res["errors"]]
    assert "MISSING_REQUIRED" in codes


@check("AUTH-05: lock profile")
def t_lock():
    store, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Phạm Hùng",
        "so_cccd": "002222222222",
    })
    store.lock_agent_profile(agent_id)
    listed = store.list_agent_profiles({"status": "locked"})
    assert len(listed["profiles"]) == 1


@check("AUTH-06: backup → restore → profile còn")
def t_backup_restore():
    store, tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Lê Thị Hoa",
        "so_cccd": "003333333333",
    })
    zip_path = tmp / "backup.zip"
    exp = store.export_backup(zip_path)
    assert exp["ok"] is True

    # Xóa DB và restore
    store.db_path().unlink()
    imp = store.import_backup(zip_path)
    assert imp["ok"] is True
    got = store.get_agent_profile(agent_id)
    assert got["ok"] is True
    assert got["profile"]["ho_ten"] == "Lê Thị Hoa"


@check("AUTH-07: catalog case → templates")
def t_catalog():
    store, _tmp = _with_temp_store()
    tpl = store.templates_for_case("thanh_lap_dntn")
    assert tpl["ok"] is True
    assert "AUTH-UQ-DN-01" in tpl["template_ids"]
    hkd = store.templates_for_case("dang_ky_ho_kinh_doanh_lan_dau")
    assert "AUTH-UQ-HKD-01" in hkd["template_ids"]
    missing = store.templates_for_case("cung_cap_thong_tin_dkdn")
    assert missing["ok"] is False


@check("AUTH-08: draft merge profile khi CCCD đổi")
def t_draft_merge():
    store, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Võ Nam",
        "so_cccd": "004444444444",
    })
    draft = store.create_authorization_draft("thanh_lap_dntn", agent_id)
    assert draft["ok"] is True
    auth_id = draft["authorization"]["authorization_id"]
    assert draft["authorization"]["agent"]["so_cccd"] == "004444444444"

    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Võ Nam",
        "so_cccd": "005555555555",
    })
    again = store.get_authorization_draft(auth_id)
    assert again["authorization"]["agent"]["so_cccd"] == "005555555555"


@check("AUTH-09: audit không chứa CCCD đầy đủ")
def t_audit_mask():
    store, _tmp = _with_temp_store()
    agent_id = str(uuid.uuid4())
    store.save_agent_profile({
        "agent_id": agent_id,
        "ho_ten": "Test Audit",
        "so_cccd": "006666666666",
    })
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT detail FROM authorization_audit WHERE event_type = 'profile.save'"
        ).fetchall()
    assert rows
    detail = rows[-1]["detail"] or ""
    assert "006666666666" not in detail
    assert "6666" in detail or "*" in detail


def main() -> int:
    tests = [
        t_fresh, t_save_list, t_update_cccd, t_missing_required, t_lock,
        t_backup_restore, t_catalog, t_draft_merge, t_audit_mask,
    ]
    for fn in tests:
        fn()
    fails = [n for ok, n in _results if not ok]
    print("\n%d PASS / %d FAIL" % (
        sum(1 for ok, _ in _results if ok),
        len(fails),
    ))
    if fails:
        for n in fails:
            print("  - %s" % n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
