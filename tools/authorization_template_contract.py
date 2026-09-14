# -*- coding: utf-8 -*-
"""Hợp đồng placeholder giữa template DOCX và authorization_render."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "app" / "templates" / "authorization"

TAG_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")

# Khóa payload flat do build_render_payload() sinh ra
RENDER_PAYLOAD_KEYS = frozenset({
    "ngay", "thang", "nam", "case_ten",
    "uy_quyen_ten_chu_the", "uy_quyen_ma_so", "uy_quyen_dia_chi",
    "uy_quyen_nguoi_ky", "uy_quyen_chuc_danh", "uy_quyen_so_cccd",
    "agent_ho_ten", "agent_ngay_sinh", "agent_so_cccd",
    "agent_ngay_cap", "agent_noi_cap", "agent_dia_chi",
    "agent_dien_thoai", "agent_email",
    "pham_vi_uy_quyen", "thoi_han_uy_quyen", "co_quan_tiep_nhan",
})

TEMPLATE_FILES = {
    "AUTH-UQ-DN-01": TEMPLATE_DIR / "AUTH-UQ-DN-01.docx",
    "AUTH-UQ-HKD-01": TEMPLATE_DIR / "AUTH-UQ-HKD-01.docx",
}


def extract_placeholders(docx_path: Path) -> set[str]:
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    return set(TAG_RE.findall(xml))


def validate_template(template_id: str, docx_path: Path | None = None) -> dict:
    """Kiểm tra tag trong DOCX ⊆ RENDER_PAYLOAD_KEYS."""
    path = docx_path or TEMPLATE_FILES.get(template_id)
    if not path or not path.is_file():
        return {
            "ok": False,
            "template_id": template_id,
            "error": "TEMPLATE_NOT_FOUND",
            "path": str(path) if path else None,
        }
    tags = extract_placeholders(path)
    unknown = sorted(tags - RENDER_PAYLOAD_KEYS)
    return {
        "ok": not unknown,
        "template_id": template_id,
        "path": str(path),
        "tags": sorted(tags),
        "unknown_tags": unknown,
    }


def validate_all_templates() -> dict:
    results = [validate_template(tid) for tid in TEMPLATE_FILES]
    return {
        "ok": all(r["ok"] for r in results),
        "templates": results,
    }
