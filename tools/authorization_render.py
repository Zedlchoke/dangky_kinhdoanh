# -*- coding: utf-8 -*-
"""Render hồ sơ ủy quyền: ghép case + profile + draft → DOCX/PDF/ZIP."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
TEMPLATE_DIR = APP_DIR / "templates" / "authorization"

HKD_CASE_PREFIXES = (
    "dang_ky_ho_kinh_doanh",
    "thay_doi_noi_dung_dang_ky_hkd",
    "tam_ngung_tiep_tuc_kinh_doanh_hkd",
    "cham_dut_hoat_dong_hkd",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick(values: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = values.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _is_hkd_case(case_id: str) -> bool:
    return any(case_id.startswith(p) for p in HKD_CASE_PREFIXES)


def build_render_payload(
    case_id: str,
    case_ten: str,
    values: dict[str, Any],
    agent: dict[str, Any],
    scope_text: str,
    co_quan: str,
    thoi_han: str,
) -> dict[str, str]:
    now = datetime.now()
    if _is_hkd_case(case_id):
        uy_ten = _pick(values, "hkd_ten_tieng_viet", "hkd_cd.ten_hkd")
        uy_nguoi = _pick(values, "chu_hkd.ho_ten")
        uy_cccd = _pick(values, "chu_hkd.so_cccd")
        uy_dc = " ".join(filter(None, [
            _pick(values, "dia_chi_chi_tiet"),
            _pick(values, "xa_phuong"),
            _pick(values, "tinh_thanh"),
        ])).strip()
        co_quan_default = co_quan or "Cơ quan đăng ký kinh doanh cấp xã"
    else:
        uy_ten = _pick(values, "dn.ten_tieng_viet")
        uy_nguoi = _pick(values, "ndd.ho_ten")
        uy_cccd = _pick(values, "ndd.so_cccd")
        uy_dc = _pick(values, "dn.dia_chi_tru_so")
        co_quan_default = co_quan or "Phòng Đăng ký kinh doanh – Sở Tài chính"

    return {
        "ngay": str(now.day),
        "thang": str(now.month),
        "nam": str(now.year),
        "case_ten": case_ten,
        "uy_quyen_ten_chu_the": uy_ten,
        "uy_quyen_ma_so": _pick(values, "dn.ma_so_dn"),
        "uy_quyen_dia_chi": uy_dc,
        "uy_quyen_nguoi_ky": uy_nguoi,
        "uy_quyen_chuc_danh": _pick(values, "ndd.chuc_vu"),
        "uy_quyen_so_cccd": uy_cccd,
        "agent_ho_ten": _pick(agent, "ho_ten"),
        "agent_ngay_sinh": _pick(agent, "ngay_sinh"),
        "agent_so_cccd": _pick(agent, "so_cccd"),
        "agent_ngay_cap": _pick(agent, "ngay_cap"),
        "agent_noi_cap": _pick(agent, "noi_cap"),
        "agent_dia_chi": _pick(agent, "dia_chi_lien_he"),
        "agent_dien_thoai": _pick(agent, "dien_thoai"),
        "agent_email": _pick(agent, "email"),
        "pham_vi_uy_quyen": scope_text,
        "thoi_han_uy_quyen": thoi_han or "30 ngày kể từ ngày ký",
        "co_quan_tiep_nhan": co_quan_default,
    }


def _ensure_templates() -> None:
    """Chỉ sinh mẫu mặc định khi thiếu file — không ghi đè mẫu owner đã chỉnh."""
    dn = TEMPLATE_DIR / "AUTH-UQ-DN-01.docx"
    hkd = TEMPLATE_DIR / "AUTH-UQ-HKD-01.docx"
    if dn.is_file() and hkd.is_file():
        return
    from tools.build_authorization_templates import build_all  # noqa: WPS433

    build_all(force=False)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_package(
    case_id: str,
    case_ten: str,
    agent_id: str,
    values: dict[str, Any],
    *,
    authorization_id: str | None = None,
    co_quan_tiep_nhan: str = "",
    thoi_han_den: str = "",
    export_format: str = "both",
) -> dict[str, Any]:
    """Sinh DOCX/PDF/ZIP cho hồ sơ ủy quyền; cập nhật snapshot trong store."""
    from tools.authorization_store import (  # noqa: WPS433
        authorization_output_dir,
        create_authorization_draft,
        get_agent_profile,
        load_catalog,
        templates_for_case,
    )
    from tools.authorization_store import connect, _audit  # noqa: WPS433

    _ensure_templates()
    tpl_info = templates_for_case(case_id)
    if not tpl_info.get("ok"):
        return tpl_info

    prof = get_agent_profile(agent_id)
    if not prof.get("ok"):
        return {"ok": False, "error": "AGENT_NOT_FOUND"}

    catalog = load_catalog()
    scope_key = tpl_info.get("scope_key") or "thanh_lap"
    scope_text = (catalog.get("scope_texts") or {}).get(scope_key, case_ten)

    payload = build_render_payload(
        case_id, case_ten, values, prof["profile"],
        scope_text, co_quan_tiep_nhan, thoi_han_den,
    )

    missing = []
    if not payload["uy_quyen_ten_chu_the"]:
        missing.append("Tên doanh nghiệp/hộ kinh doanh")
    if not payload["uy_quyen_nguoi_ky"]:
        missing.append("Người ủy quyền (NDĐPL/chủ hộ)")
    if not payload["agent_ho_ten"] or not payload["agent_so_cccd"]:
        missing.append("Thông tin profile người làm thủ tục")
    if missing:
        return {
            "ok": False,
            "errors": [{"code": "MISSING_DATA", "message": "Thiếu: " + ", ".join(missing)}],
        }

    auth_id = authorization_id
    if not auth_id:
        draft_res = create_authorization_draft(
            case_id, agent_id,
            {"co_quan_tiep_nhan": co_quan_tiep_nhan, "thoi_han_den": thoi_han_den},
        )
        if not draft_res.get("ok"):
            return draft_res
        auth_id = draft_res["authorization"]["authorization_id"]

    from tools.docx_render import write_rendered  # noqa: WPS433

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = authorization_output_dir() / ("%s_%s" % (auth_id[:8], ts))
    out_dir.mkdir(parents=True, exist_ok=True)

    files: list[str] = []
    errors: list[str] = []
    manifest_docs: list[dict[str, Any]] = []

    for tid in tpl_info["template_ids"]:
        if tid == "AUTH-CHECKLIST-01":
            checklist = out_dir / "PHIEU_KIEM_KE.txt"
            checklist.write_text(
                "PHIẾU KIỂM KÊ HỒ SƠ ỦY QUYỀN (nội bộ)\n"
                "Case: %s\nAgent: %s\n"
                "- [ ] Giấy ủy quyền (ký tay hoặc ký số)\n"
                "- [ ] CCCD bản sao (nếu cơ quan yêu cầu)\n"
                "- [ ] Hồ sơ đăng ký đã điền\n"
                % (case_ten, prof["profile"]["ho_ten"]),
                encoding="utf-8",
            )
            files.append(checklist.name)
            continue

        meta = (catalog.get("templates") or {}).get(tid) or {}
        rel = meta.get("docx_template")
        if not rel:
            continue
        template = APP_DIR / "templates" / rel
        if not template.is_file():
            template = TEMPLATE_DIR / ("%s.docx" % tid)
        if not template.is_file():
            errors.append("%s: thiếu template %s" % (tid, template))
            continue

        out_file = out_dir / ("%s.docx" % tid)
        try:
            write_rendered(template, payload, out_file)
            files.append(out_file.name)
            manifest_docs.append({
                "template_id": tid,
                "file": out_file.name,
                "sha256": _file_sha256(out_file),
            })
        except Exception as exc:  # noqa: BLE001
            errors.append("%s: %s" % (tid, type(exc).__name__))

    export_format = (export_format or "both").lower()
    want_pdf = export_format in ("pdf", "both")
    soffice = shutil.which("soffice")
    if want_pdf and soffice:
        for name in list(files):
            if not name.endswith(".docx"):
                continue
            docx = out_dir / name
            try:
                import subprocess

                subprocess.run(
                    [soffice, "--headless", "--convert-to", "pdf",
                     "--outdir", str(out_dir), str(docx)],
                    check=False, timeout=120,
                    capture_output=True,
                )
                pdf_name = name.replace(".docx", ".pdf")
                if (out_dir / pdf_name).is_file():
                    files.append(pdf_name)
            except Exception:  # noqa: BLE001
                pass

    snapshot = {
        "authorization_id": auth_id,
        "case_id": case_id,
        "agent_id": agent_id,
        "payload": payload,
        "documents": manifest_docs,
        "generated_at": _utc_now(),
    }

    manifest = {
        "authorization_id": auth_id,
        "case_id": case_id,
        "agent_id": agent_id,
        "schema_version": 1,
        "documents": manifest_docs,
        "generated_at": snapshot["generated_at"],
    }
    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    readme = out_dir / "README.txt"
    readme.write_text(
        "Hồ sơ ủy quyền dịch vụ đăng ký kinh doanh.\n"
        "1. In DOCX hoặc ký số theo quy trình nội bộ.\n"
        "2. Đính kèm khi nộp hồ sơ tại cơ quan đăng ký.\n",
        encoding="utf-8",
    )
    files.extend(["MANIFEST.json", "README.txt"])

    zip_path = out_dir / "ho_so_uy_quyen.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in files:
            p = out_dir / name
            if p.is_file():
                zf.write(p, arcname=name)

    with connect() as conn:
        conn.execute(
            "UPDATE authorization_cases SET status = 'ready', snapshot_json = ?, "
            "updated_at = ? WHERE authorization_id = ?",
            (json.dumps(snapshot, ensure_ascii=False), _utc_now(), auth_id),
        )
        _audit(conn, "authorization.generate", auth_id,
               "files=%d" % len(manifest_docs))

    if errors and not manifest_docs:
        return {"ok": False, "errors": errors}

    return {
        "ok": True,
        "authorization_id": auth_id,
        "dir": str(out_dir),
        "zip": str(zip_path),
        "files": files,
        "errors": errors,
        "manifest": manifest,
    }
