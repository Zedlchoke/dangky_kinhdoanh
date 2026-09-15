# -*- coding: utf-8 -*-
"""Kho SQLite local — profile người làm thủ tục và hồ sơ ủy quyền (module dịch vụ).

Dữ liệu nằm ngoài git:
  Windows: %APPDATA%\\DangKyKinhDoanh\\profiles.db
  macOS:   ~/Library/Application Support/DangKyKinhDoanh/profiles.db
  Linux:   ~/.local/share/DangKyKinhDoanh/profiles.db

Test/CI: đặt biến môi trường DKKD_AUTH_DATA_DIR trước import.

Chạy test: python -X utf8 -m tools.test_authorization_store
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
CATALOG_PATH = APP_DIR / "data" / "authorization" / "catalog.json"
SCHEMA_PATH = APP_DIR / "data" / "authorization" / "schema_v1.sql"

SCHEMA_VERSION = 1
BACKUP_MANIFEST_NAME = "authorization_backup_manifest.json"
DB_FILENAME = "profiles.db"

PROFILE_COLUMNS = (
    "agent_id", "ho_ten", "ngay_sinh", "gioi_tinh", "quoc_tich",
    "so_cccd", "ngay_cap", "noi_cap", "dia_chi_lien_he", "dien_thoai",
    "email", "chuc_danh", "don_vi_dich_vu", "trang_thai", "ghi_chu",
    "created_at", "updated_at",
)

REQUIRED_PROFILE_FIELDS = ("ho_ten", "so_cccd")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def user_data_dir() -> Path:
    """Thư mục dữ liệu người dùng (override bằng DKKD_AUTH_DATA_DIR khi test)."""
    override = os.environ.get("DKKD_AUTH_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "DangKyKinhDoanh"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "DangKyKinhDoanh"
    return Path.home() / ".local" / "share" / "DangKyKinhDoanh"


def db_path() -> Path:
    return user_data_dir() / DB_FILENAME


def authorization_output_dir() -> Path:
    return user_data_dir() / "authorization"


def backups_dir() -> Path:
    return user_data_dir() / "backups"


def mask_pii(value: str | None, visible_tail: int = 4) -> str:
    """Che PII cho log/audit — không dùng cho hiển thị UI."""
    if not value:
        return ""
    text = str(value).strip()
    if len(text) <= visible_tail:
        return "*" * len(text)
    return "*" * (len(text) - visible_tail) + text[-visible_tail:]


def _normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload or {})
    agent_id = str(data.get("agent_id") or "").strip() or str(uuid.uuid4())
    out: dict[str, Any] = {"agent_id": agent_id}
    for col in PROFILE_COLUMNS:
        if col in ("agent_id", "created_at", "updated_at"):
            continue
        val = data.get(col)
        if val is None or (isinstance(val, str) and not val.strip()):
            out[col] = None
            continue
        if col == "trang_thai":
            status = str(val).strip().lower()
            if status not in ("active", "locked", "expired"):
                raise ValueError("INVALID_STATUS")
            out[col] = status
        else:
            out[col] = str(val).strip()
    if not out.get("trang_thai"):
        out["trang_thai"] = "active"
    if not out.get("quoc_tich"):
        out["quoc_tich"] = "Việt Nam"
    return out


def _validate_profile(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for field in REQUIRED_PROFILE_FIELDS:
        if not str(data.get(field) or "").strip():
            errors.append({
                "code": "MISSING_REQUIRED",
                "field": field,
                "message": "Thiếu trường bắt buộc: %s" % field,
            })
    cccd = str(data.get("so_cccd") or "").strip()
    if cccd and not re.fullmatch(r"\d{9,12}", cccd):
        errors.append({
            "code": "INVALID_CCCD",
            "field": "so_cccd",
            "message": "Số CCCD không hợp lệ (9–12 chữ số).",
        })
    email = str(data.get("email") or "").strip()
    if email and "@" not in email:
        errors.append({
            "code": "INVALID_EMAIL",
            "field": "email",
            "message": "Email không hợp lệ.",
        })
    return errors


def _row_to_profile(row: sqlite3.Row) -> dict[str, Any]:
    return {col: row[col] for col in PROFILE_COLUMNS}


@contextmanager
def connect(db_file: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_file or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _current_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT MAX(version) AS v FROM schema_migrations"
        ).fetchone()
        return int(row["v"] or 0)
    except sqlite3.OperationalError:
        return 0


def migrate(conn: sqlite3.Connection | None = None) -> int:
    """Áp schema nếu cần; trả schema version hiện tại."""
    if conn is None:
        with connect() as c:
            return migrate(c)

    version = _current_schema_version(conn)
    if version >= SCHEMA_VERSION:
        return version

    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.execute(
        "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (SCHEMA_VERSION, _utc_now()),
    )
    return SCHEMA_VERSION


def ensure_store() -> Path:
    """Khởi tạo DB nếu chưa có; trả đường dẫn file DB."""
    with connect() as conn:
        migrate(conn)
    return db_path()


def list_agent_profiles(
    filter_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Danh sách profile; filter: status, q (tìm tên/cccd/điện thoại)."""
    filt = filter_json or {}
    status = str(filt.get("status") or "").strip().lower()
    query = str(filt.get("q") or "").strip().lower()

    ensure_store()
    clauses: list[str] = []
    params: list[Any] = []
    if status in ("active", "locked", "expired"):
        clauses.append("trang_thai = ?")
        params.append(status)
    if query:
        clauses.append(
            "(LOWER(ho_ten) LIKE ? OR so_cccd LIKE ? OR LOWER(COALESCE(dien_thoai,'')) LIKE ?)"
        )
        like = "%%%s%%" % query
        params.extend([like, like, like])

    sql = "SELECT %s FROM authorized_agent_profiles" % ", ".join(PROFILE_COLUMNS)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY ho_ten COLLATE NOCASE"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"ok": True, "profiles": [_row_to_profile(r) for r in rows]}


def get_agent_profile(agent_id: str) -> dict[str, Any]:
    ensure_store()
    with connect() as conn:
        row = conn.execute(
            "SELECT %s FROM authorized_agent_profiles WHERE agent_id = ?"
            % ", ".join(PROFILE_COLUMNS),
            (agent_id,),
        ).fetchone()
    if not row:
        return {"ok": False, "error": "NOT_FOUND"}
    return {"ok": True, "profile": _row_to_profile(row)}


def save_agent_profile(payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_profile(payload)
    errors = _validate_profile(data)
    if errors:
        return {"ok": False, "errors": errors}

    now = _utc_now()
    ensure_store()
    with connect() as conn:
        existing = conn.execute(
            "SELECT agent_id, created_at FROM authorized_agent_profiles WHERE agent_id = ?",
            (data["agent_id"],),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        data["created_at"] = created_at
        data["updated_at"] = now

        placeholders = ", ".join("?" for _ in PROFILE_COLUMNS)
        updates = ", ".join(
            "%s = excluded.%s" % (c, c) for c in PROFILE_COLUMNS if c != "agent_id"
        )
        conn.execute(
            "INSERT INTO authorized_agent_profiles (%s) VALUES (%s) "
            "ON CONFLICT(agent_id) DO UPDATE SET %s"
            % (", ".join(PROFILE_COLUMNS), placeholders, updates),
            tuple(data[c] for c in PROFILE_COLUMNS),
        )
        _audit(conn, "profile.save", data["agent_id"],
               "cccd=%s" % mask_pii(data.get("so_cccd")))

    return {"ok": True, "profile": data}


def lock_agent_profile(agent_id: str) -> dict[str, Any]:
    ensure_store()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE authorized_agent_profiles SET trang_thai = 'locked', updated_at = ? "
            "WHERE agent_id = ? AND trang_thai != 'locked'",
            (_utc_now(), agent_id),
        )
        if cur.rowcount == 0:
            row = conn.execute(
                "SELECT agent_id FROM authorized_agent_profiles WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            if not row:
                return {"ok": False, "error": "NOT_FOUND"}
            return {"ok": True, "already_locked": True}
        _audit(conn, "profile.lock", agent_id, None)
    return {"ok": True}


def delete_agent_profile(agent_id: str) -> dict[str, Any]:
    """Xóa profile người làm thủ tục và các hồ sơ ủy quyền gắn agent đó."""
    aid = str(agent_id or "").strip()
    if not aid:
        return {"ok": False, "error": "MISSING_AGENT_ID"}
    ensure_store()
    with connect() as conn:
        row = conn.execute(
            "SELECT ho_ten FROM authorized_agent_profiles WHERE agent_id = ?",
            (aid,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "NOT_FOUND"}
        conn.execute(
            "DELETE FROM authorization_cases WHERE agent_id = ?",
            (aid,),
        )
        conn.execute(
            "DELETE FROM authorized_agent_profiles WHERE agent_id = ?",
            (aid,),
        )
        _audit(conn, "profile.delete", aid,
               "name=%s" % mask_pii(str(row["ho_ten"] or "")))
    return {"ok": True, "agent_id": aid}


def _audit(
    conn: sqlite3.Connection,
    event_type: str,
    entity_id: str | None,
    detail: str | None,
) -> None:
    conn.execute(
        "INSERT INTO authorization_audit(event_id, event_type, entity_id, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), event_type, entity_id, detail, _utc_now()),
    )


def load_catalog() -> dict[str, Any]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def templates_for_case(case_id: str) -> dict[str, Any]:
    """Mẫu ủy quyền gắn với case (từ catalog.json)."""
    catalog = load_catalog()
    entry = (catalog.get("cases") or {}).get(case_id)
    if not entry:
        return {
            "ok": False,
            "error": "CASE_NOT_IN_CATALOG",
            "case_id": case_id,
        }
    templates = catalog.get("templates") or {}
    ids = entry.get("template_ids") or []
    return {
        "ok": True,
        "case_id": case_id,
        "scope_key": entry.get("scope_key"),
        "templates": [templates[tid] for tid in ids if tid in templates],
        "template_ids": ids,
    }


def create_authorization_draft(
    case_id: str,
    agent_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tạo nháp hồ sơ ủy quyền — draft luôn trỏ agent_id (cập nhật khi profile đổi)."""
    extra = extra or {}
    tpl = templates_for_case(case_id)
    if not tpl.get("ok"):
        return tpl

    prof = get_agent_profile(agent_id)
    if not prof.get("ok"):
        return {"ok": False, "error": "AGENT_NOT_FOUND"}
    if prof["profile"].get("trang_thai") != "active":
        return {"ok": False, "error": "AGENT_NOT_ACTIVE"}

    auth_id = str(extra.get("authorization_id") or uuid.uuid4())
    now = _utc_now()
    scope = str(extra.get("scope_text") or tpl.get("scope_key") or case_id)

    record = {
        "authorization_id": auth_id,
        "case_id": case_id,
        "agent_id": agent_id,
        "template_ids_json": json.dumps(tpl["template_ids"], ensure_ascii=False),
        "status": "draft",
        "scope_text": scope,
        "co_quan_tiep_nhan": str(extra.get("co_quan_tiep_nhan") or "").strip() or None,
        "thoi_han_den": str(extra.get("thoi_han_den") or "").strip() or None,
        "draft_meta_json": json.dumps(extra.get("meta") or {}, ensure_ascii=False),
        "snapshot_json": None,
        "created_at": now,
        "updated_at": now,
    }

    ensure_store()
    with connect() as conn:
        conn.execute(
            "INSERT INTO authorization_cases "
            "(authorization_id, case_id, agent_id, template_ids_json, status, "
            "scope_text, co_quan_tiep_nhan, thoi_han_den, draft_meta_json, "
            "snapshot_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(record[k] for k in (
                "authorization_id", "case_id", "agent_id", "template_ids_json",
                "status", "scope_text", "co_quan_tiep_nhan", "thoi_han_den",
                "draft_meta_json", "snapshot_json", "created_at", "updated_at",
            )),
        )
        _audit(conn, "authorization.draft_create", auth_id, "case=%s" % case_id)

    merged = merge_draft_with_profile(record, prof["profile"], tpl)
    return {"ok": True, "authorization": merged}


def merge_draft_with_profile(
    case_row: dict[str, Any],
    profile: dict[str, Any],
    tpl_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ghép draft + profile hiện tại (draft cập nhật khi CCCD đổi)."""
    out = dict(case_row)
    out["agent"] = profile
    out["template_ids"] = json.loads(case_row.get("template_ids_json") or "[]")
    if tpl_info and tpl_info.get("ok"):
        out["templates"] = tpl_info.get("templates") or []
    else:
        catalog = load_catalog()
        templates = catalog.get("templates") or {}
        out["templates"] = [
            templates[tid] for tid in out["template_ids"] if tid in templates
        ]
    return out


def get_authorization_draft(authorization_id: str) -> dict[str, Any]:
    ensure_store()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM authorization_cases WHERE authorization_id = ?",
            (authorization_id,),
        ).fetchone()
    if not row:
        return {"ok": False, "error": "NOT_FOUND"}

    case_row = dict(row)
    if case_row.get("status") != "draft":
        snap = case_row.get("snapshot_json")
        if snap:
            return {"ok": True, "authorization": json.loads(snap), "frozen": True}
        return {"ok": True, "authorization": case_row, "frozen": True}

    prof = get_agent_profile(case_row["agent_id"])
    if not prof.get("ok"):
        return {"ok": False, "error": "AGENT_NOT_FOUND"}
    tpl = templates_for_case(case_row["case_id"])
    merged = merge_draft_with_profile(case_row, prof["profile"], tpl)
    return {"ok": True, "authorization": merged, "frozen": False}


def list_authorization_drafts(
    agent_id: str | None = None,
    case_id: str | None = None,
) -> dict[str, Any]:
    ensure_store()
    clauses: list[str] = []
    params: list[Any] = []
    if agent_id:
        clauses.append("agent_id = ?")
        params.append(agent_id)
    if case_id:
        clauses.append("case_id = ?")
        params.append(case_id)
    sql = "SELECT authorization_id, case_id, agent_id, status, updated_at FROM authorization_cases"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY updated_at DESC"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"ok": True, "items": [dict(r) for r in rows]}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def export_backup(dest_zip: str | Path) -> dict[str, Any]:
    """Xuất profiles.db (+ manifest) ra file .zip để chuyển máy."""
    ensure_store()
    path = Path(dest_zip)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = db_path()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": _utc_now(),
        "db_sha256": _file_sha256(db),
        "app_module": "authorization_store",
    }
    backups_dir().mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(db, arcname=DB_FILENAME)
        zf.writestr(BACKUP_MANIFEST_NAME, json.dumps(manifest, indent=2))

    with connect() as conn:
        _audit(conn, "backup.export", None, "sha256=%s…" % manifest["db_sha256"][:12])

    return {"ok": True, "path": str(path), "manifest": manifest}


def import_backup(
    src_zip: str | Path,
    *,
    replace: bool = True,
) -> dict[str, Any]:
    """Nhập backup .zip; thay thế profiles.db hiện tại khi replace=True."""
    src = Path(src_zip)
    if not src.is_file():
        return {"ok": False, "error": "FILE_NOT_FOUND"}

    user_data_dir().mkdir(parents=True, exist_ok=True)
    staging = user_data_dir() / "_restore_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        with zipfile.ZipFile(src, "r") as zf:
            names = zf.namelist()
            if DB_FILENAME not in names:
                return {"ok": False, "error": "INVALID_BACKUP"}
            if BACKUP_MANIFEST_NAME in names:
                manifest = json.loads(zf.read(BACKUP_MANIFEST_NAME).decode("utf-8"))
                if manifest.get("schema_version", 0) > SCHEMA_VERSION:
                    return {"ok": False, "error": "SCHEMA_TOO_NEW"}
            else:
                manifest = {}
            zf.extract(DB_FILENAME, staging)

        new_db = staging / DB_FILENAME
        target = db_path()
        if target.exists() and replace:
            bak = backups_dir() / ("profiles_pre_restore_%s.db" % _utc_now().replace(":", ""))
            shutil.copy2(target, bak)

        shutil.copy2(new_db, target)
        with connect() as conn:
            migrate(conn)
            _audit(conn, "backup.import", None,
                   "from=%s" % mask_pii(str(src.name), 8))

        return {"ok": True, "path": str(target), "manifest": manifest}
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def store_info() -> dict[str, Any]:
    """Thông tin kho (không PII) — cho UI empty state."""
    ensure_store()
    path = db_path()
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM authorized_agent_profiles WHERE trang_thai = 'active'"
        ).fetchone()
        count = int(row["n"])
    return {
        "ok": True,
        "data_dir": str(user_data_dir()),
        "db_path": str(path),
        "db_exists": path.is_file(),
        "active_profiles": count,
        "schema_version": SCHEMA_VERSION,
    }


def bundle_for_excel(case_id: str) -> dict[str, Any]:
    """Gom dữ liệu AUTH_* cho workbook case-level."""
    ensure_store()
    agents = list_agent_profiles()["profiles"]
    documents: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    auth_ids: list[str] = []
    agent_ids: set[str] = set()

    with connect() as conn:
        set_rows = conn.execute(
            "SELECT * FROM authorization_cases WHERE case_id = ? "
            "ORDER BY updated_at DESC",
            (case_id,),
        ).fetchall()
        sets = [dict(r) for r in set_rows]
        for row in sets:
            auth_ids.append(row["authorization_id"])
            agent_ids.add(row["agent_id"])
            snap_raw = row.get("snapshot_json")
            if not snap_raw:
                continue
            try:
                snap = json.loads(snap_raw)
            except json.JSONDecodeError:
                continue
            for doc in snap.get("documents") or []:
                documents.append({
                    "document_id": "%s:%s" % (
                        row["authorization_id"], doc.get("template_id", "")),
                    "authorization_id": row["authorization_id"],
                    "template_id": doc.get("template_id", ""),
                    "file_name": doc.get("file", ""),
                    "sha256": doc.get("sha256", ""),
                    "status": row.get("status", ""),
                    "generated_at": snap.get("generated_at", ""),
                })
            out_dir = snap.get("dir") or ""
            if out_dir:
                attachments.append({
                    "attachment_id": "%s:zip" % row["authorization_id"],
                    "authorization_id": row["authorization_id"],
                    "rel_path": "ho_so_uy_quyen.zip",
                    "sha256": "",
                    "mime": "application/zip",
                    "size_bytes": "",
                })

        audit_rows: list[dict[str, Any]] = []
        entity_ids = list(dict.fromkeys(auth_ids + list(agent_ids)))
        if entity_ids:
            placeholders = ",".join("?" for _ in entity_ids)
            sql = (
                "SELECT event_id, event_type, entity_id, detail, created_at "
                "FROM authorization_audit WHERE entity_id IN (%s) "
                "ORDER BY created_at DESC LIMIT 200" % placeholders
            )
            audit_rows = [dict(r) for r in conn.execute(sql, entity_ids).fetchall()]

    export_agents = [
        p for p in agents
        if p["agent_id"] in agent_ids or p.get("trang_thai") == "active"
    ]
    if not export_agents and agents:
        export_agents = agents

    return {
        "schema_version": 1,
        "case_id": case_id,
        "agents": export_agents,
        "sets": sets,
        "documents": documents,
        "attachments": attachments,
        "audit": audit_rows,
    }


def apply_excel_bundle(bundle: dict[str, Any], *, case_id: str) -> dict[str, Any]:
    """Áp candidate AUTH_* từ Excel vào SQLite (upsert theo ID)."""
    errors: list[dict[str, str]] = []
    if str(bundle.get("case_id") or "") != case_id:
        return {
            "ok": False,
            "errors": [{
                "code": "AUTH_WRONG_CASE",
                "message": "Bundle case_id không khớp",
            }],
        }

    applied = {"agents": 0, "sets": 0, "documents": 0}
    for row in bundle.get("agents") or []:
        res = save_agent_profile(row)
        if not res.get("ok"):
            errors.append({
                "code": "AUTH_AGENT_SAVE",
                "message": "Không lưu agent %s" % row.get("agent_id"),
            })
            continue
        applied["agents"] += 1

    ensure_store()
    now = _utc_now()
    with connect() as conn:
        for row in bundle.get("sets") or []:
            auth_id = str(row.get("authorization_id") or "").strip()
            if not auth_id:
                continue
            if str(row.get("case_id") or "") != case_id:
                errors.append({
                    "code": "AUTH_WRONG_CASE",
                    "message": "Set %s case_id lệch" % auth_id,
                })
                continue
            agent_id = str(row.get("agent_id") or "").strip()
            prof = get_agent_profile(agent_id)
            if not prof.get("ok"):
                errors.append({
                    "code": "AUTH_UNKNOWN_AGENT",
                    "message": "Set %s: agent %s không tồn tại" % (auth_id, agent_id),
                })
                continue
            record = {
                "authorization_id": auth_id,
                "case_id": case_id,
                "agent_id": agent_id,
                "template_ids_json": row.get("template_ids_json") or "[]",
                "status": row.get("status") or "draft",
                "scope_text": row.get("scope_text"),
                "co_quan_tiep_nhan": row.get("co_quan_tiep_nhan"),
                "thoi_han_den": row.get("thoi_han_den"),
                "draft_meta_json": "{}",
                "snapshot_json": None,
                "created_at": row.get("created_at") or now,
                "updated_at": now,
            }
            conn.execute(
                "INSERT INTO authorization_cases "
                "(authorization_id, case_id, agent_id, template_ids_json, status, "
                "scope_text, co_quan_tiep_nhan, thoi_han_den, draft_meta_json, "
                "snapshot_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(authorization_id) DO UPDATE SET "
                "agent_id=excluded.agent_id, template_ids_json=excluded.template_ids_json, "
                "status=excluded.status, scope_text=excluded.scope_text, "
                "co_quan_tiep_nhan=excluded.co_quan_tiep_nhan, "
                "thoi_han_den=excluded.thoi_han_den, "
                "snapshot_json=authorization_cases.snapshot_json, "
                "updated_at=excluded.updated_at",
                tuple(record[k] for k in (
                    "authorization_id", "case_id", "agent_id", "template_ids_json",
                    "status", "scope_text", "co_quan_tiep_nhan", "thoi_han_den",
                    "draft_meta_json", "snapshot_json", "created_at", "updated_at",
                )),
            )
            applied["sets"] += 1
            _audit(conn, "excel.import_set", auth_id, "case=%s" % case_id)

    applied["documents"] = len(bundle.get("documents") or [])

    if errors:
        return {"ok": False, "errors": errors, "applied": applied}
    return {"ok": True, "applied": applied}
