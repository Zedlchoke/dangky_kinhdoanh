#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import posixpath
import re
import shutil
import socketserver
import subprocess
import sys
import time
import urllib.parse
import zipfile
from copy import deepcopy
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "generated_ho_so"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)

FORM_PATHS = {
    "pl1_1": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_01_giay_de_nghi_dang_ky_doanh_nghiep_doanh_nghiep_tu_nhan.docx",
    "pl1_2": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_02_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_mot_thanh_vien.docx",
    "pl1_3": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_03_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx",
    "pl1_4": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_04_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_co_phan.docx",
    "pl1_5": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_05_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_hop_danh.docx",
    "pl1_6": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_06_danh_sach_thanh_vien_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx",
    "pl1_7": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_07_danh_sach_co_dong_sang_lap_cong_ty_co_phan.docx",
    "pl1_8": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_08_danh_sach_co_dong_la_nha_dau_tu_nuoc_ngoai.docx",
    "pl1_9": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_09_danh_sach_thanh_vien_cong_ty_hop_danh.docx",
    "pl1_10": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_10_danh_sach_chu_so_huu_huong_loi_cua_doanh_nghiep.docx",
    "pl1_11": "01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_11_ke_khai_thong_tin_de_xac_dinh_chu_so_huu_huong_loi_cua_doanh_nghiep.docx",
    "pl1_12": "02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_12_giay_de_nghi_dang_ky_thay_doi_noi_dung_giay_chung_nhan_dang_ky_doanh_nghiep_thong_bao_thay_doi_n.docx",
    "pl1_13": "02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_13_giay_de_nghi_dang_ky_thay_doi_nguoi_dai_dien_theo_phap_luat.docx",
    "pl1_14": "02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_14_giay_de_nghi_dang_ky_thay_doi_chu_doanh_nghiep_tu_nhan.docx",
    "pl1_15": "02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_15_giay_de_nghi_dang_ky_thay_doi_chu_so_huu_cong_ty_tnhh_mot_thanh_vien.docx",
    "pl1_17": "03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_17_giay_de_nghi_dang_ky_hoat_dong_chi_nhanh_van_phong_dai_dien_thong_bao_lap_dia_diem_kinh_doanh.docx",
    "pl1_19": "03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_19_giay_de_nghi_dang_ky_thay_doi_noi_dung_dang_ky_hoat_dong_chi_nhanh_van_phong_dai_dien_dia_diem_k.docx",
    "pl1_27": "04_tam_ngung_cham_dut_giai_the/PL1_Mau_27_thong_bao_ve_viec_tam_ngung_kinh_doanh_tiep_tuc_kinh_doanh_truoc_thoi_han_da_thong_bao_cua_doanh.docx",
    "pl1_28": "04_tam_ngung_cham_dut_giai_the/PL1_Mau_28_thong_bao_ve_viec_cham_dut_hoat_dong_chi_nhanh_van_phong_dai_dien_dia_diem_kinh_doanh.docx",
    "pl1_30": "04_tam_ngung_cham_dut_giai_the/PL1_Mau_30_thong_bao_ve_viec_giai_the_doanh_nghiep.docx",
    "pl2_1": "06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_01_giay_de_nghi_dang_ky_ho_kinh_doanh.docx",
    "pl2_2": "06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_02_giay_de_nghi_dang_ky_thay_doi_noi_dung_dang_ky_ho_kinh_doanh.docx",
    "pl2_3": "06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_03_giay_de_nghi_dang_ky_tam_ngung_kinh_doanh_tiep_tuc_kinh_doanh_truoc_thoi_han_da_dang_ky_cua_ho_k.docx",
    "pl2_4": "06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_04_thong_bao_ve_viec_cham_dut_hoat_dong_ho_kinh_doanh.docx",
}


def load_form_maps() -> dict:
    path = ROOT / "app" / "data" / "form_maps.json"
    if not path.exists():
        return {"forms": []}
    return json.loads(path.read_text(encoding="utf-8"))


def form_paths() -> dict[str, str]:
    paths = dict(FORM_PATHS)
    for form in load_form_maps().get("forms", []):
        paths.setdefault(form["id"], form["path"])
    return paths


def form_map_by_id() -> dict[str, dict]:
    return {form["id"]: form for form in load_form_maps().get("forms", [])}

DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOCX_DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""

FIELD_PROMPTS = {
    "company_name": "Tên doanh nghiệp",
    "company_code": "Mã số doanh nghiệp/Mã số thuế",
    "owner_name": "Họ tên chủ doanh nghiệp/chủ hộ/người đại diện",
    "owner_birth": "Ngày sinh",
    "owner_gender": "Giới tính",
    "owner_id": "Số định danh cá nhân",
    "owner_phone": "Điện thoại",
    "owner_email": "Email",
    "street": "Số nhà, đường, tổ/xóm",
    "ward": "Xã/Phường/Đặc khu",
    "province": "Tỉnh/Thành phố",
    "hq_street": "Số nhà, đường, tổ/xóm của trụ sở",
    "hq_ward": "Xã/Phường/Đặc khu của trụ sở",
    "hq_province": "Tỉnh/Thành phố của trụ sở",
    "registry_office": "Cơ quan đăng ký kinh doanh",
    "filing_place": "Nơi nộp hồ sơ / tỉnh thành",
    "business_lines": "Ngành nghề kinh doanh",
    "charter_capital": "Vốn điều lệ/vốn đầu tư",
    "tax_method": "Phương pháp tính thuế GTGT",
    "director_name": "Giám đốc/Tổng giám đốc",
    "accountant_name": "Kế toán trưởng/Phụ trách kế toán",
    "change_content": "Nội dung thay đổi",
    "new_address": "Địa chỉ mới",
    "new_name": "Tên doanh nghiệp mới",
    "new_legal_rep": "Người đại diện theo pháp luật mới",
    "branch_name": "Tên chi nhánh/VPĐD/địa điểm",
    "branch_address": "Địa chỉ chi nhánh/VPĐD/địa điểm",
    "pause_from": "Tạm ngừng từ ngày",
    "pause_to": "Tạm ngừng đến ngày",
    "dissolve_reason": "Lý do giải thể/chấm dứt",
    "hkd_certificate": "Số Giấy chứng nhận đăng ký hộ kinh doanh",
    "hkd_name": "Tên hộ kinh doanh được chuyển đổi",
    "hkd_tax_code": "Mã số thuế hộ kinh doanh",
    "hkd_address": "Địa chỉ trụ sở hộ kinh doanh",
}

COMMON_LINE_RULES = [
    ("Ngày, tháng, năm sinh:", "owner_birth"),
    ("Sinh ngày:", "owner_birth"),
    ("Giới tính:", "owner_gender"),
    ("Số định danh cá nhân:", "owner_id"),
    ("Xã/Phường/Đặc khu:", "ward"),
    ("Tỉnh/Thành phố trực thuộc trung ương:", "province"),
    ("Họ, chữ đệm và tên Giám đốc/Tổng giám đốc:", "director_name"),
    ("Họ, chữ đệm và tên Kế toán trưởng/Phụ trách kế toán:", "accountant_name"),
]

FORM_LINE_RULES = {
    "pl1_1": [("Tên doanh nghiệp viết bằng tiếng Việt (ghi bằng chữ in hoa):", "company_name_upper"), ("Vốn đầu tư:", "charter_capital")],
    "pl1_2": [("Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "company_name_upper"), ("Vốn điều lệ:", "charter_capital")],
    "pl1_3": [("Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "company_name_upper"), ("Vốn điều lệ:", "charter_capital")],
    "pl1_4": [("Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "company_name_upper"), ("Vốn điều lệ:", "charter_capital")],
    "pl1_5": [("Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "company_name_upper"), ("Vốn điều lệ:", "charter_capital")],
    "pl1_12": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code"), ("Nội dung đăng ký thay đổi:", "change_content")],
    "pl1_13": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code")],
    "pl1_14": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code")],
    "pl1_15": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code")],
    "pl1_17": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code"), ("Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh:", "branch_name"), ("Địa chỉ chi nhánh/văn phòng đại diện/địa điểm kinh doanh:", "branch_address")],
    "pl1_19": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code"), ("Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh:", "branch_name")],
    "pl1_27": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code")],
    "pl1_28": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code"), ("Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh:", "branch_name")],
    "pl1_30": [("Tên doanh nghiệp (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số doanh nghiệp/Mã số thuế:", "company_code"), ("Lý do giải thể:", "dissolve_reason")],
    "pl2_1": [("Tên hộ kinh doanh:", "company_name_upper"), ("Vốn kinh doanh:", "charter_capital")],
    "pl2_2": [("Tên hộ kinh doanh (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số hộ kinh doanh/Mã số thuế:", "company_code"), ("Nội dung đăng ký thay đổi:", "change_content")],
    "pl2_3": [("Tên hộ kinh doanh (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số hộ kinh doanh/Mã số thuế:", "company_code")],
    "pl2_4": [("Tên hộ kinh doanh (ghi bằng chữ in hoa):", "company_name_upper"), ("Mã số hộ kinh doanh/Mã số thuế:", "company_code")],
}


def normalize_data(payload: dict) -> dict:
    data = {k: str(v).strip() for k, v in payload.get("data", {}).items() if str(v).strip()}
    business_rows = business_line_rows(payload)
    if business_rows:
        data["_business_line_rows"] = business_rows
        data["business_lines"] = business_line_summary(business_rows)
    people_rows = payload.get("people", []) or []
    if people_rows:
        data["_people_rows"] = people_rows
    if data.get("company_name"):
        data["company_name_upper"] = data["company_name"].upper()
    if data.get("street") and data.get("ward") and data.get("province"):
        data["full_address"] = f"{data['street']}, {data['ward']}, {data['province']}"
    data.setdefault("hq_street", data.get("street", ""))
    data.setdefault("hq_ward", data.get("ward", ""))
    data.setdefault("hq_province", data.get("province", ""))
    return data


def scenario_context(data: dict) -> dict[str, str]:
    return {
        "procedure": str(data.get("_procedure", "")),
        "scenario": str(data.get("_scenario", "")),
        "entity_type": str(data.get("_entity_type", "")),
    }


def unsafe_field_for_context(label: str, data: dict) -> bool:
    low = label.lower()
    ctx = scenario_context(data)
    proc = ctx["procedure"]
    scenario = ctx["scenario"]
    if "tình trạng thành lập" in low or "đánh dấu x vào ô thích hợp" in low:
        return True
    if low in {"stt", "tên ngành", "mã ngành", "số lượng"}:
        return True
    conversion_words = ["bị chia", "bị tách", "bị hợp nhất", "chuyển đổi loại hình", "lý do chuyển đổi"]
    if scenario not in {"splitMerge"} and any(word in low for word in conversion_words):
        return True
    hkd_words = ["hộ kinh doanh", "chủ hộ kinh doanh"]
    if proc != "convertHkd" and any(word in low for word in hkd_words):
        return True
    social_words = ["cơ sở bảo trợ", "quỹ xã hội", "quỹ từ thiện"]
    if scenario != "social" and any(word in low for word in social_words):
        return True
    if "ngành, nghề kinh doanh" in low:
        return True
    return False


def sanitize_auto_fields(form_id: str, auto_fields: dict, data: dict) -> dict:
    form = form_map_by_id().get(form_id, {})
    allowed = {field["id"]: field for field in form.get("fields", [])}
    sanitized = {}
    for field_id, value in (auto_fields or {}).items():
        field = allowed.get(field_id)
        if not field:
            continue
        if field.get("commonKey") in FIELD_PROMPTS:
            continue
        label = str(value.get("label") or field.get("label") or "")
        if unsafe_field_for_context(label, data):
            continue
        sanitized[field_id] = value
    return sanitized


def unsafe_checkbox_for_context(label: str, data: dict) -> bool:
    low = label.lower()
    ctx = scenario_context(data)
    scenario = ctx["scenario"]
    if "thành lập mới" in low or "thành lập trên cơ sở" in low:
        return True
    if scenario != "social" and "doanh nghiệp xã hội" in low:
        return True
    if scenario != "splitMerge" and any(word in low for word in ["tách doanh nghiệp", "chia doanh nghiệp", "hợp nhất doanh nghiệp", "chuyển đổi loại hình"]):
        return True
    return False


def sanitize_auto_checkboxes(form_id: str, auto_checkboxes: dict, data: dict) -> dict:
    form = form_map_by_id().get(form_id, {})
    allowed = {box["id"]: box for box in form.get("checkboxes", [])}
    sanitized = {}
    for box_id, value in (auto_checkboxes or {}).items():
        box = allowed.get(box_id)
        if not box:
            continue
        label = str(value.get("label") or box.get("label") or "")
        if unsafe_checkbox_for_context(label, data):
            continue
        sanitized[box_id] = value
    return sanitized


def business_line_rows(payload: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in payload.get("businessLines", []) or []:
        row = {
            "action": str(item.get("action") or "Bổ sung").strip(),
            "code": str(item.get("code") or "").strip(),
            "name": str(item.get("name") or "").strip(),
            "detail": str(item.get("detail") or "").strip(),
            "isPrimary": bool(item.get("isPrimary")),
        }
        if row["code"] or row["name"] or row["detail"]:
            rows.append(row)
    return rows


def business_line_summary(rows: list[dict[str, object]]) -> str:
    lines = []
    for idx, row in enumerate(rows, start=1):
        action = f"{row.get('action')} - " if row.get("action") else ""
        primary = " | Ngành chính" if row.get("isPrimary") else ""
        detail = f" | Chi tiết: {row.get('detail')}" if row.get("detail") else ""
        lines.append(f"{idx}. {action}{row.get('code', '')} - {row.get('name', '')}{primary}{detail}")
    return "\n".join(lines)


def paragraph_text(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.findall(".//w:t", NS))


def escape_xml(text: object) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def w_p(text: str, bold: bool = False) -> str:
    b = "<w:b/>" if bold else ""
    return f"<w:p><w:r><w:rPr>{b}</w:rPr><w:t xml:space=\"preserve\">{escape_xml(text)}</w:t></w:r></w:p>"


def w_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object, bold: bool = False) -> str:
        b = "<w:b/>" if bold else ""
        return f"<w:tc><w:p><w:r><w:rPr>{b}</w:rPr><w:t xml:space=\"preserve\">{escape_xml(value)}</w:t></w:r></w:p></w:tc>"

    header = "<w:tr>" + "".join(cell(h, True) for h in headers) + "</w:tr>"
    body = "".join("<w:tr>" + "".join(cell(v) for v in row) + "</w:tr>" for row in rows)
    return f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/><w:tblBorders><w:top w:val=\"single\" w:sz=\"4\"/><w:left w:val=\"single\" w:sz=\"4\"/><w:bottom w:val=\"single\" w:sz=\"4\"/><w:right w:val=\"single\" w:sz=\"4\"/><w:insideH w:val=\"single\" w:sz=\"4\"/><w:insideV w:val=\"single\" w:sz=\"4\"/></w:tblBorders></w:tblPr>{header}{body}</w:tbl>"


def w_table_element(headers: list[str], rows: list[list[object]]) -> ET.Element:
    wrapped = f"<root xmlns:w=\"{W_NS}\">{w_table(headers, rows)}</root>"
    return ET.fromstring(wrapped)[0]


def insert_table_after_anchor(root: ET.Element, anchor: str, headers: list[str], rows: list[list[object]]) -> bool:
    if not rows:
        return False
    body = root.find("w:body", NS)
    if body is None:
        return False
    anchor_low = anchor.lower()
    children = list(body)
    for idx, child in enumerate(children):
        if child.tag == f"{{{W_NS}}}p" and anchor_low in paragraph_text(child).lower():
            body.insert(idx + 1, w_table_element(headers, rows))
            return True
    return False


def business_rows_for_docx(rows: list[dict[str, object]]) -> list[list[object]]:
    return [
        [
            idx,
            row.get("name", ""),
            row.get("code", ""),
            "X" if row.get("isPrimary") else "",
            row.get("detail", ""),
        ]
        for idx, row in enumerate(rows, start=1)
    ]


def insert_business_tables(root: ET.Element, form_id: str, data: dict) -> None:
    rows = data.get("_business_line_rows") or []
    if not rows:
        return
    headers = ["STT", "Tên ngành, nghề kinh doanh", "Mã ngành", "Ngành chính", "Chi tiết/Ghi chú"]
    if form_id in {"pl1_1", "pl1_2", "pl1_3", "pl1_4", "pl1_5", "pl2_1", "pl2_2", "pl1_17", "pl1_19"}:
        insert_table_after_anchor(root, "ngành, nghề kinh doanh", headers, business_rows_for_docx(rows))
    if form_id == "pl1_12":
        groups = {
            "Bổ sung": "bổ sung ngành, nghề kinh doanh",
            "Bỏ": "bỏ ngành, nghề kinh doanh",
            "Sửa chi tiết": "sửa đổi chi tiết ngành, nghề kinh doanh",
        }
        for action, anchor in groups.items():
            filtered = [row for row in rows if row.get("action") == action]
            insert_table_after_anchor(root, anchor, headers, business_rows_for_docx(filtered))


def people_rows_for_docx(rows: list[dict[str, object]]) -> list[list[object]]:
    return [
        [
            idx,
            row.get("name", ""),
            row.get("type", ""),
            row.get("idNumber", ""),
            row.get("address", ""),
            row.get("capital", ""),
            row.get("ratio", ""),
            row.get("role", ""),
        ]
        for idx, row in enumerate(rows, start=1)
    ]


def organization_owner_rows_for_docx(rows: list[dict[str, object]]) -> list[list[object]]:
    organization_rows = [
        row
        for row in rows
        if "tổ chức" in str(row.get("type", "")).lower()
    ]
    return [
        [
            idx,
            row.get("name", ""),
            row.get("idNumber", ""),
            "",
            "",
            row.get("address", ""),
            row.get("ratio", ""),
            row.get("role", ""),
        ]
        for idx, row in enumerate(organization_rows, start=1)
    ]


def insert_people_tables(root: ET.Element, form_id: str, data: dict) -> None:
    rows = data.get("_people_rows") or []
    if not rows:
        return
    if form_id == "pl1_11":
        headers = [
            "STT",
            "Tên tổ chức",
            "Mã số doanh nghiệp/số QĐ thành lập",
            "Ngày cấp",
            "Nơi cấp",
            "Địa chỉ trụ sở chính",
            "Tỷ lệ sở hữu cổ phần có quyền biểu quyết",
            "Ghi chú",
        ]
        insert_table_after_anchor(
            root,
            "DANH SÁCH ĐỂ XÁC ĐỊNH CHỦ SỞ HỮU HƯỞNG LỢI",
            headers,
            organization_owner_rows_for_docx(rows),
        )
        return
    headers = ["STT", "Họ tên/Tổ chức", "Loại", "Số giấy tờ/MST", "Địa chỉ", "Vốn góp", "Tỷ lệ", "Vai trò/Ghi chú"]
    anchors = {
        "pl1_6": "I. Thành viên là cá nhân",
        "pl1_7": "I. Cổ đông sáng lập là cá nhân",
        "pl1_8": "I. Cổ đông là nhà đầu tư nước ngoài là cá nhân",
        "pl1_9": "I. Thành viên là cá nhân",
        "pl1_10": "DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI",
    }
    anchor = anchors.get(form_id)
    if anchor:
        insert_table_after_anchor(root, anchor, headers, people_rows_for_docx(rows))


def write_simple_docx(path: Path, title: str, sections: list[tuple[str, list[str] | list[list[object]]]], table_headers: dict[str, list[str]] | None = None) -> None:
    body = [w_p(title.upper(), True), w_p("")]
    table_headers = table_headers or {}
    for heading, content in sections:
        body.append(w_p(heading, True))
        if heading in table_headers:
            rows = content if isinstance(content, list) else []
            body.append(w_table(table_headers[heading], rows))  # type: ignore[arg-type]
        else:
            for line in content:  # type: ignore[assignment]
                body.append(w_p(str(line)))
        body.append(w_p(""))
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{''.join(body)}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body>
</w:document>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", DOCX_CONTENT_TYPES)
        z.writestr("_rels/.rels", DOCX_RELS)
        z.writestr("word/_rels/document.xml.rels", DOCX_DOCUMENT_RELS)
        z.writestr("word/document.xml", document)


def set_paragraph_text(p: ET.Element, text: str) -> None:
    runs = p.findall(".//w:t", NS)
    if not runs:
        r = ET.SubElement(p, f"{{{W_NS}}}r")
        t = ET.SubElement(r, f"{{{W_NS}}}t")
        t.text = text
        return
    runs[0].text = text
    for t in runs[1:]:
        t.text = ""


def clean_fill_line(text: str, label: str, value: str) -> str:
    if not value:
        return text
    escaped = re.escape(label)
    if re.search(escaped + r"\s*[.:]*\s*[.…\-_ ]{3,}", text):
        return re.sub(escaped + r"\s*[.:]*\s*[.…\-_ ]{3,}", f"{label} {value}", text, count=1)
    if label in text and value not in text:
        return text.replace(label, f"{label} {value}", 1)
    return text


def fill_whole_line(text: str, label: str, value: str) -> str:
    if not value or label not in text:
        return text
    return f"{label} {value}"


def fill_person_intro(text: str, value: str) -> str:
    if not value or "Tôi là" not in text:
        return text
    if ":" in text:
        return re.sub(r"Tôi là.*?:.*", f"Tôi là: {value.upper()}", text, count=1)
    return text


def fill_phone_email(text: str, data: dict) -> str:
    if "Điện thoại" not in text and "Thư điện tử" not in text:
        return text
    phone = data.get("owner_phone")
    email = data.get("owner_email")
    if phone and "Điện thoại" in text:
        text = re.sub(r"Điện thoại[^:]*:\s*[.…\-_ ]*", f"Điện thoại: {phone} ", text, count=1)
    if email and "Thư điện tử" in text:
        text = re.sub(r"Thư điện tử[^:]*:\s*[.…\-_ ]*", f"Thư điện tử: {email} ", text, count=1)
    return text


def mark_next_checkbox(previous_text: str, text: str, targets: set[str]) -> str:
    if text.strip() == "□" and any(target in previous_text for target in targets):
        return "☒"
    return text


def fill_docx(src: Path, dest: Path, data: dict, form_id: str, auto_fields: dict | None = None, auto_checkboxes: dict | None = None) -> None:
    auto_fields = auto_fields or {}
    auto_checkboxes = auto_checkboxes or {}
    auto_map = {str(v.get("paragraphIndex")): v for v in auto_fields.values() if str(v.get("value", "")).strip()}
    checked_labels = {str(v.get("label", "")) for v in auto_checkboxes.values() if v.get("checked")}
    with zipfile.ZipFile(src) as zin:
        document_xml = zin.read("word/document.xml")
        root = ET.fromstring(document_xml)
        line_counts: dict[str, int] = {}
        previous_text = ""
        hq_lines_remaining = 0
        paragraphs = root.findall(".//w:p", NS)
        for paragraph_index, p in enumerate(paragraphs):
            text = paragraph_text(p)
            original = text
            auto = auto_map.get(str(paragraph_index))
            if auto:
                text = fill_whole_line(text, auto.get("label", ""), auto.get("value", ""))
            if text.strip() == "□" and previous_text in checked_labels:
                text = "☒"
            if "Địa chỉ trụ sở chính:" in text:
                hq_lines_remaining = 4
            if form_id in {"pl1_1", "pl1_2", "pl1_3", "pl1_4", "pl1_5"}:
                scenario = data.get("_scenario", "normal")
                targets = {"Thành lập mới"}
                if scenario == "convert":
                    targets = {"Thành lập trên cơ sở chuyển đổi từ hộ kinh doanh"}
                elif scenario == "social":
                    targets = {"Doanh nghiệp xã hội"}
                text = mark_next_checkbox(previous_text, text, targets)
            text = fill_person_intro(text, data.get("owner_name", ""))
            text = fill_phone_email(text, data)
            for label, key in COMMON_LINE_RULES + FORM_LINE_RULES.get(form_id, []):
                occurrence_key = f"{form_id}:{label}"
                if label in text and line_counts.get(occurrence_key, 0) == 0:
                    text = fill_whole_line(text, label, data.get(key, ""))
                    line_counts[occurrence_key] = line_counts.get(occurrence_key, 0) + 1
            if "Số nhà/phòng, ngách/hẻm" in text and data.get("street"):
                count_key = f"{form_id}:street"
                if line_counts.get(count_key, 0) < 1:
                    text = fill_whole_line(text, "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn:", data["street"])
                    line_counts[count_key] = line_counts.get(count_key, 0) + 1
            if hq_lines_remaining and "Số nhà/phòng, ngách/hẻm" in text and data.get("hq_street"):
                text = fill_whole_line(text, "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn:", data["hq_street"])
            if hq_lines_remaining and "Xã/Phường/Đặc khu:" in text and data.get("hq_ward"):
                text = fill_whole_line(text, "Xã/Phường/Đặc khu:", data["hq_ward"])
            if hq_lines_remaining and "Tỉnh/Thành phố trực thuộc trung ương:" in text and data.get("hq_province"):
                text = fill_whole_line(text, "Tỉnh/Thành phố trực thuộc trung ương:", data["hq_province"])
            if form_id in {"pl1_1", "pl1_2", "pl1_3", "pl1_4", "pl1_5"} and data.get("_procedure") == "convertHkd":
                hkd_map = {
                    "Tên hộ kinh doanh (ghi bằng chữ in hoa):": data.get("hkd_name", "").upper(),
                    "Số Giấy chứng nhận đăng ký hộ kinh doanh (nếu có):": data.get("hkd_certificate", ""),
                    "Mã số thuế của hộ kinh doanh:": data.get("hkd_tax_code", ""),
                    "Địa chỉ trụ sở hộ kinh doanh:": data.get("hkd_address", ""),
                    "Tên chủ hộ kinh doanh:": data.get("owner_name", ""),
                }
                for label, value in hkd_map.items():
                    if label in text and value:
                        text = fill_whole_line(text, label, value)
            if form_id == "pl1_12" and data.get("new_address") and "Địa chỉ trụ sở chính sau khi thay đổi:" in text:
                text = clean_fill_line(text, "Địa chỉ trụ sở chính sau khi thay đổi:", data["new_address"])
            if form_id == "pl1_12" and data.get("new_name") and "Tên doanh nghiệp viết bằng tiếng Việt sau khi thay đổi:" in text:
                text = clean_fill_line(text, "Tên doanh nghiệp viết bằng tiếng Việt sau khi thay đổi:", data["new_name"].upper())
            if form_id == "pl1_13" and data.get("new_legal_rep") and "Họ, chữ đệm và tên" in text:
                text = clean_fill_line(text, "Họ, chữ đệm và tên:", data["new_legal_rep"])
            if text != original:
                set_paragraph_text(p, text)
            previous_text = text
            if hq_lines_remaining:
                hq_lines_remaining -= 1
        insert_business_tables(root, form_id, data)
        insert_people_tables(root, form_id, data)
        rendered = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                content = rendered if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, content)


def build_checklist(payload: dict, data: dict, form_ids: list[str]) -> str:
    flags = payload.get("flags", {})
    paths = form_paths()
    lines = [
        "CHECKLIST HO SO",
        f"Nghiep vu: {payload.get('procedureLabel', '')}",
        f"Loai hinh/doi tuong: {payload.get('entityLabel', '')}",
        f"Noi dung: {payload.get('scenarioLabel', '')}",
        "",
        "1. Bieu mau da sinh",
    ]
    for form_id in form_ids:
        lines.append(f"- {form_id}: {paths.get(form_id, '')}")
    lines.extend(["", "2. Thong tin da nhap"])
    for key, label in FIELD_PROMPTS.items():
        if data.get(key):
            lines.append(f"- {label}: {data[key]}")
    business_rows = data.get("_business_line_rows") or []
    if business_rows:
        lines.extend(["", "Bang nganh, nghe kinh doanh"])
        for idx, row in enumerate(business_rows, start=1):
            primary = " - nganh chinh" if row.get("isPrimary") else ""
            detail = f" - {row.get('detail')}" if row.get("detail") else ""
            lines.append(f"- {idx}. {row.get('action', '')} {row.get('code', '')} {row.get('name', '')}{primary}{detail}")
    lines.extend(["", "3. Giay to can dinh kem/doi chieu"])
    if payload.get("procedure") in {"formation", "convertHkd"}:
        lines.append("- Dieu le cong ty, tru doanh nghiep tu nhan.")
        lines.append("- Giay to phap ly cua ca nhan/to chuc lien quan neu khong duoc mien theo so dinh danh ca nhan.")
    if payload.get("procedure") == "convertHkd":
        lines.append("- Ban sao Giay chung nhan dang ky ho kinh doanh.")
        lines.append("- Hoan thanh nghia vu thue cua ho kinh doanh truoc/sau khi chuyen doi theo yeu cau co quan thue.")
    if flags.get("authorizedFiler"):
        lines.append("- Van ban uy quyen va giay to phap ly cua nguoi duoc uy quyen.")
    if flags.get("foreignInvestor"):
        lines.append("- Kiem tra thu tuc dau tu/chap thuan gop von, mua co phan, phan von gop.")
    if flags.get("taxMove"):
        lines.append("- Hoan tat thu tuc voi co quan thue khi thay doi dia chi lam doi co quan thue quan ly.")
    lines.extend(["", "4. Luu y truoc khi nop"])
    lines.append("- Kiem tra lai tham quyen ky: chu so huu, Hoi dong thanh vien, Dai hoi dong co dong, Hoi dong quan tri hoac chu ho kinh doanh.")
    lines.append("- Kiem tra ngay thang, dia gioi hanh chinh, so dinh danh ca nhan, ma nganh va thong tin thue.")
    lines.append("- Ho so sinh tu app can duoc nguoi co tham quyen doc lai, ky va dinh kem dung ban sao/ban chinh theo tung truong hop.")
    return "\n".join(lines)


def row_people(payload: dict) -> list[list[object]]:
    rows = []
    for idx, person in enumerate(payload.get("people", []) or [], start=1):
        rows.append([
            idx,
            person.get("name", ""),
            person.get("type", ""),
            person.get("idNumber", ""),
            person.get("address", ""),
            person.get("capital", ""),
            person.get("ratio", ""),
            person.get("role", ""),
        ])
    return rows


def build_supporting_docs(payload: dict, data: dict, out_dir: Path) -> list[Path]:
    proc = payload.get("procedure")
    scenario = payload.get("scenario")
    entity = payload.get("entityLabel", "")
    signer = data.get("owner_name", "")
    company = data.get("company_name", "")
    today = time.strftime("ngay %d thang %m nam %Y")
    created: list[Path] = []

    checklist_lines = [
        f"Doanh nghiệp/hộ kinh doanh: {company}",
        f"Nghiệp vụ: {payload.get('procedureLabel', '')}",
        f"Loại hình: {entity}",
        f"Nội dung: {payload.get('scenarioLabel', '')}",
        "Kiểm tra bản ký, bản sao giấy tờ pháp lý, số định danh cá nhân, địa chỉ, mã ngành, thông tin thuế trước khi nộp.",
    ]
    checklist = out_dir / "00_DANH_MUC_HO_SO.docx"
    write_simple_docx(checklist, "Danh mục hồ sơ đăng ký kinh doanh", [("Thông tin hồ sơ", checklist_lines)])
    created.append(checklist)

    if payload.get("flags", {}).get("authorizedFiler"):
        auth = out_dir / "01_GIAY_UY_QUYEN_NOP_HO_SO.docx"
        write_simple_docx(auth, "Giấy ủy quyền thực hiện thủ tục đăng ký kinh doanh", [
            ("Bên ủy quyền", [f"Họ tên/tổ chức: {signer}", f"Liên quan hồ sơ: {company}"]),
            ("Bên được ủy quyền", ["Họ tên: ................................................", "Số định danh cá nhân: ................................", "Điện thoại: ............................................"]),
            ("Phạm vi ủy quyền", ["Thay mặt bên ủy quyền nộp, sửa đổi, bổ sung, nhận kết quả và thực hiện các công việc cần thiết liên quan đến hồ sơ đăng ký kinh doanh nêu trên."]),
            ("Ký xác nhận", [f"Lập tại ................, {today}", "BÊN ỦY QUYỀN                         BÊN ĐƯỢC ỦY QUYỀN"]),
        ])
        created.append(auth)

    if proc in {"formation", "convertHkd"} and payload.get("entityType") != "private":
        charter = out_dir / "02_DIEU_LE_KHUNG_CAN_RA_SOAT.docx"
        write_simple_docx(charter, f"Điều lệ khung - {company}", [
            ("Thông tin doanh nghiệp", [f"Tên: {company}", f"Loại hình: {entity}", f"Trụ sở: {data.get('hq_street', '')}, {data.get('hq_ward', '')}, {data.get('hq_province', '')}", f"Vốn điều lệ: {data.get('charter_capital', '')}"]),
            ("Người đại diện theo pháp luật", [signer]),
            ("Nội dung cần hoàn thiện trước khi ký", ["Ngành nghề kinh doanh", "Cơ cấu quản trị", "Quyền và nghĩa vụ của thành viên/cổ đông", "Nguyên tắc chuyển nhượng vốn/cổ phần", "Thể thức thông qua quyết định nội bộ"]),
        ])
        created.append(charter)

    people_rows = row_people(payload)
    if people_rows:
        roster = out_dir / "03_BANG_THONG_TIN_THANH_VIEN_CO_DONG_CSHHL.docx"
        write_simple_docx(
            roster,
            "Bảng thông tin thành viên, cổ đông, chủ sở hữu hưởng lợi",
            [("Danh sách", people_rows)],
            {"Danh sách": ["STT", "Họ tên/Tổ chức", "Loại", "Số giấy tờ/MST", "Địa chỉ", "Vốn góp", "Tỷ lệ", "Vai trò"]},
        )
        created.append(roster)

    business_rows = data.get("_business_line_rows") or []
    if business_rows:
        business_doc = out_dir / "07_BANG_NGANH_NGHE_KINH_DOANH.docx"
        write_simple_docx(
            business_doc,
            "Bảng ngành, nghề kinh doanh",
            [("Danh sách", [
                [
                    idx,
                    row.get("action", ""),
                    row.get("code", ""),
                    row.get("name", ""),
                    "X" if row.get("isPrimary") else "",
                    row.get("detail", ""),
                ]
                for idx, row in enumerate(business_rows, start=1)
            ])],
            {"Danh sách": ["STT", "Loại", "Mã ngành", "Tên ngành, nghề", "Ngành chính", "Chi tiết/Ghi chú"]},
        )
        created.append(business_doc)

    if proc == "change":
        decision = out_dir / "04_QUYET_DINH_THAY_DOI.docx"
        write_simple_docx(decision, "Quyết định về việc thay đổi nội dung đăng ký doanh nghiệp", [
            ("Thông tin", [f"Doanh nghiệp: {company}", f"Mã số: {data.get('company_code', '')}", f"Nội dung thay đổi: {data.get('change_content') or data.get('new_name') or data.get('new_address') or data.get('new_legal_rep') or data.get('charter_capital', '')}"]),
            ("Quyết định", ["Thông qua nội dung thay đổi nêu trên.", "Giao người đại diện theo pháp luật hoặc người được ủy quyền thực hiện thủ tục đăng ký thay đổi với Cơ quan đăng ký kinh doanh."]),
            ("Ký xác nhận", [f"Lập tại ................, {today}", "NGƯỜI CÓ THẨM QUYỀN KÝ"]),
        ])
        minutes = out_dir / "05_BIEN_BAN_HOP_THAY_DOI.docx"
        write_simple_docx(minutes, "Biên bản họp về việc thay đổi nội dung đăng ký doanh nghiệp", [
            ("Cuộc họp", [f"Doanh nghiệp: {company}", "Thời gian: ............................................", "Địa điểm: ............................................", "Thành phần tham dự: theo danh sách ký tên/ủy quyền kèm theo."]),
            ("Nội dung biểu quyết", [data.get("change_content") or "Thông qua nội dung thay đổi đăng ký doanh nghiệp theo hồ sơ kèm theo."]),
            ("Kết quả", ["Tỷ lệ tán thành: ..........%", "Tỷ lệ không tán thành: ..........%", "Tỷ lệ không có ý kiến: ..........%"]),
        ])
        created.extend([decision, minutes])

    if proc == "convertHkd":
        tax_note = out_dir / "06_GHI_CHU_NGHIA_VU_THUE_HKD.docx"
        write_simple_docx(tax_note, "Ghi chú xử lý hộ kinh doanh khi chuyển đổi", [
            ("Thông tin hộ kinh doanh", [f"Tên hộ kinh doanh: {data.get('hkd_name', '')}", f"Số GCN ĐKHKD: {data.get('hkd_certificate', '')}", f"Mã số thuế: {data.get('hkd_tax_code', '')}", f"Địa chỉ: {data.get('hkd_address', '')}"]),
            ("Việc cần làm", ["Chuẩn bị bản sao Giấy chứng nhận đăng ký hộ kinh doanh.", "Theo dõi/hoàn tất nghĩa vụ thuế để Cơ quan đăng ký kinh doanh cấp xã cập nhật tình trạng đã chấm dứt hoạt động.", "Không tiếp tục hoạt động hộ kinh doanh kể từ thời điểm doanh nghiệp chuyển đổi được cấp Giấy chứng nhận đăng ký doanh nghiệp."]),
        ])
        created.append(tax_note)

    return created


def generate(payload: dict) -> dict:
    paths = form_paths()
    form_ids = [x for x in payload.get("formIds", []) if x in paths]
    if not form_ids:
        raise ValueError("Khong co bieu mau hop le de sinh ho so.")
    data = normalize_data(payload)
    data["_procedure"] = payload.get("procedure", "")
    data["_scenario"] = "convert" if payload.get("procedure") == "convertHkd" else payload.get("scenario", "normal")
    data["_entity_type"] = payload.get("entityType", "")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", data.get("company_name", "ho_so"))[:60].strip("_") or "ho_so"
    out_dir = OUTPUT_DIR / f"{stamp}_{safe_name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    filled_files = []
    for form_id in form_ids:
        src = ROOT / paths[form_id]
        dest = out_dir / f"{form_id}_{src.name}"
        fill_docx(
            src,
            dest,
            data,
            form_id,
            sanitize_auto_fields(form_id, (payload.get("autoFields") or {}).get(form_id, {}), data),
            sanitize_auto_checkboxes(form_id, (payload.get("autoCheckboxes") or {}).get(form_id, {}), data),
        )
        filled_files.append(dest)
    supporting = build_supporting_docs(payload, data, out_dir)
    filled_files.extend(supporting)
    (out_dir / "CHECKLIST.txt").write_text(build_checklist(payload, data, form_ids), encoding="utf-8")
    (out_dir / "THONG_TIN_DA_NHAP.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    zip_path = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in out_dir.rglob("*"):
            z.write(path, path.relative_to(out_dir))
    return {"folder": str(out_dir.relative_to(ROOT)), "zip": str(zip_path.relative_to(ROOT)), "count": len(filled_files)}


def self_test() -> dict:
    samples = [
        {
            "name": "formation_llc2",
            "payload": {
                "procedure": "formation",
                "scenario": "normal",
                "entityType": "llc2",
                "procedureLabel": "Thành lập doanh nghiệp",
                "entityLabel": "Công ty TNHH hai thành viên trở lên",
                "scenarioLabel": "Thành lập mới thông thường",
                "flags": {"onlineFiling": True, "authorizedFiler": True},
                "data": {
                    "company_name": "Công ty TNHH Hai Thành Viên Mẫu",
                    "owner_name": "Nguyễn Văn A",
                    "owner_id": "001090000001",
                    "owner_phone": "0901000001",
                    "owner_birth": "01/01/1990",
                    "owner_gender": "Nam",
                    "owner_email": "a@example.com",
                    "street": "1 Lý Thường Kiệt",
                    "ward": "Phường Cửa Nam",
                    "province": "Hà Nội",
                    "hq_street": "10 Trần Hưng Đạo",
                    "hq_ward": "Phường Cửa Nam",
                    "hq_province": "Hà Nội",
                    "registry_office": "Cơ quan đăng ký kinh doanh cấp tỉnh Hà Nội",
                    "filing_place": "Hà Nội",
                    "business_lines": "6201 - Lập trình máy vi tính",
                    "charter_capital": "3.000.000.000 đồng",
                    "director_name": "Nguyễn Văn A",
                    "accountant_name": "Trần Thị B",
                    "tax_method": "Khấu trừ",
                },
                "people": [
                    {"name": "Nguyễn Văn A", "type": "Cá nhân", "idNumber": "001090000001", "address": "Hà Nội", "capital": "2.000.000.000", "ratio": "66.67", "role": "Thành viên"},
                    {"name": "Trần Thị B", "type": "Cá nhân", "idNumber": "001091000002", "address": "Hà Nội", "capital": "1.000.000.000", "ratio": "33.33", "role": "Thành viên"},
                ],
                "businessLines": [
                    {"code": "6201", "name": "Lập trình máy vi tính", "detail": "Sản xuất phần mềm", "isPrimary": True},
                    {"code": "6311", "name": "Xử lý dữ liệu, cho thuê và các hoạt động liên quan", "detail": "", "isPrimary": False},
                ],
                "formIds": ["pl1_3", "pl1_6"],
            },
        },
        {
            "name": "convert_hkd_llc1",
            "payload": {
                "procedure": "convertHkd",
                "scenario": "convert",
                "entityType": "llc1",
                "procedureLabel": "Chuyển hộ kinh doanh sang doanh nghiệp",
                "entityLabel": "Công ty TNHH một thành viên",
                "scenarioLabel": "Đăng ký thành lập DN trên cơ sở chuyển đổi từ HKD",
                "flags": {"onlineFiling": True},
                "data": {
                    "company_name": "Công ty TNHH Chuyển Đổi Kiểm Thử",
                    "owner_name": "Lê Văn C",
                    "owner_id": "079090000003",
                    "owner_phone": "0902000002",
                    "owner_birth": "02/02/1990",
                    "owner_gender": "Nam",
                    "owner_email": "c@example.com",
                    "street": "22 Nguyễn Huệ",
                    "ward": "Phường Sài Gòn",
                    "province": "TP. Hồ Chí Minh",
                    "hq_street": "22 Nguyễn Huệ",
                    "hq_ward": "Phường Sài Gòn",
                    "hq_province": "TP. Hồ Chí Minh",
                    "registry_office": "Cơ quan đăng ký kinh doanh cấp tỉnh TP. Hồ Chí Minh",
                    "filing_place": "TP. Hồ Chí Minh",
                    "business_lines": "5610 - Nhà hàng",
                    "charter_capital": "2.000.000.000 đồng",
                    "director_name": "Lê Văn C",
                    "accountant_name": "Phạm Thị D",
                    "tax_method": "Khấu trừ",
                    "hkd_name": "Hộ kinh doanh Lê Văn C",
                    "hkd_certificate": "41A8001234",
                    "hkd_tax_code": "0312345678",
                    "hkd_address": "22 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
                },
                "people": [],
                "businessLines": [
                    {"code": "5610", "name": "Nhà hàng và các dịch vụ ăn uống phục vụ lưu động", "detail": "Không bao gồm kinh doanh quán bar", "isPrimary": True},
                ],
                "formIds": ["pl1_2"],
            },
        },
        {
            "name": "change_legal_rep",
            "payload": {
                "procedure": "change",
                "scenario": "legalRep",
                "entityType": "jsc",
                "procedureLabel": "Thay đổi thông tin doanh nghiệp",
                "entityLabel": "Công ty cổ phần",
                "scenarioLabel": "Đổi người đại diện theo pháp luật",
                "flags": {"onlineFiling": True, "authorizedFiler": True},
                "data": {
                    "company_name": "Công ty Cổ phần Kiểm Thử",
                    "company_code": "0109999999",
                    "owner_name": "Vũ Thị E",
                    "owner_id": "001092000004",
                    "owner_phone": "0903000003",
                    "registry_office": "Cơ quan đăng ký kinh doanh cấp tỉnh Hà Nội",
                    "filing_place": "Hà Nội",
                    "change_content": "Thay đổi người đại diện theo pháp luật",
                    "new_legal_rep": "Vũ Thị E",
                    "owner_birth": "03/03/1992",
                    "owner_gender": "Nữ",
                },
                "people": [],
                "formIds": ["pl1_13"],
            },
        },
    ]
    results = []
    for sample in samples:
        result = generate(sample["payload"])
        folder = ROOT / result["folder"]
        checks = {
            "zip_exists": (ROOT / result["zip"]).exists(),
            "checklist_exists": (folder / "CHECKLIST.txt").exists(),
            "has_support_docs": any(path.name.endswith(".docx") and path.name.startswith(("00_", "01_", "02_", "03_", "04_", "05_", "06_")) for path in folder.iterdir()),
        }
        results.append({"name": sample["name"], "result": result, "checks": checks})
    report = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "samples": results}
    report_path = OUTPUT_DIR / "SELF_TEST_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def map_test() -> dict:
    maps = load_form_maps().get("forms", [])
    data = {
        "company_name": "Công ty TNHH Kiểm Thử Toàn Bộ Mẫu",
        "owner_name": "Nguyễn Văn Kiểm Thử",
        "owner_id": "001090123456",
        "owner_phone": "0900000000",
        "street": "1 Đường Mẫu",
        "ward": "Phường Mẫu",
        "province": "Thành phố Mẫu",
        "hq_street": "2 Đường Trụ Sở",
        "hq_ward": "Phường Trụ Sở",
        "hq_province": "Thành phố Mẫu",
        "charter_capital": "1.000.000.000 đồng",
        "_scenario": "normal",
    }
    paths = form_paths()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_DIR / f"{stamp}_MAP_TEST_108_MAU"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for form in maps:
        form_id = form["id"]
        src = ROOT / paths[form_id]
        dest = out_dir / f"{form_id}_{src.name}"
        auto = {}
        for field in form.get("fields", [])[:5]:
            value = data.get(field.get("commonKey") or "", f"Dữ liệu kiểm thử {field['label']}")
            auto[field["id"]] = {
                "label": field["label"],
                "paragraphIndex": field["paragraphIndex"],
                "value": value,
            }
        try:
            fill_docx(src, dest, data, form_id, auto, {})
            results.append({"id": form_id, "ok": True, "file": str(dest.relative_to(ROOT))})
        except Exception as exc:
            results.append({"id": form_id, "ok": False, "error": str(exc)})
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": [item for item in results if not item["ok"]],
        "folder": str(out_dir.relative_to(ROOT)),
    }
    (OUTPUT_DIR / "MAP_TEST_108_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = urllib.parse.urlparse(path).path
        if path == "/":
            path = "/app/index.html"
        normalized = posixpath.normpath(urllib.parse.unquote(path)).lstrip("/")
        return str(ROOT / normalized)

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = generate(payload)
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/download":
            self.handle_download(parsed)
            return
        if parsed.path == "/api/reveal":
            self.handle_reveal(parsed)
            return
        super().do_GET()

    def safe_requested_path(self, parsed) -> Path:
        query = urllib.parse.parse_qs(parsed.query)
        requested = query.get("path", [""])[0]
        target = (ROOT / requested).resolve()
        if ROOT.resolve() not in target.parents and target != ROOT.resolve():
            raise ValueError("Duong dan khong hop le.")
        if not target.exists():
            raise FileNotFoundError("Khong tim thay file/thu muc.")
        return target

    def handle_download(self, parsed) -> None:
        try:
            target = self.safe_requested_path(parsed)
            if not target.is_file():
                raise ValueError("Chi tai duoc file.")
            data = target.read_bytes()
            name = target.name.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/zip" if target.suffix == ".zip" else "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + urllib.parse.quote_from_bytes(name))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def handle_reveal(self, parsed) -> None:
        try:
            target = self.safe_requested_path(parsed)
            subprocess.run(["open", "-R", str(target)], check=False)
            body = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def validate_docx(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "word/document.xml" not in names:
                return {"path": str(path.relative_to(ROOT)), "ok": False, "error": "missing word/document.xml"}
            ET.fromstring(z.read("word/document.xml"))
        return {"path": str(path.relative_to(ROOT)), "ok": True}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "ok": False, "error": str(exc)}


def validate_zip(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            docx_count = sum(1 for name in z.namelist() if name.lower().endswith(".docx"))
        return {"path": str(path.relative_to(ROOT)), "ok": bad is None and docx_count > 0, "bad_file": bad, "docx_count": docx_count}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "ok": False, "error": str(exc)}


def docx_text_summary(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paragraphs = [
        paragraph_text(p).strip()
        for p in root.findall(".//w:p", NS)
        if paragraph_text(p).strip()
    ]
    text = "\n".join(paragraphs)
    return {
        "text": text,
        "paragraphs": paragraphs,
        "paragraph_count": len(paragraphs),
        "table_count": len(root.findall(".//w:tbl", NS)),
        "chars": len(text),
        "sample_label_count": text.count("Mẫu số"),
    }


def template_sanity_report() -> dict:
    failed = []
    for form_id, rel_path in sorted(form_paths().items()):
        path = ROOT / rel_path
        try:
            summary = docx_text_summary(path)
            reasons = []
            if summary["chars"] < 500:
                reasons.append("too_short")
            if summary["sample_label_count"] > 15:
                reasons.append("likely_contains_multiple_templates")
            if reasons:
                failed.append({
                    "form": form_id,
                    "path": rel_path,
                    "chars": summary["chars"],
                    "paragraphs": summary["paragraph_count"],
                    "sample_labels": summary["sample_label_count"],
                    "reasons": reasons,
                })
        except Exception as exc:
            failed.append({"form": form_id, "path": rel_path, "error": str(exc), "reasons": ["unreadable_docx"]})
    return {"checked": len(form_paths()), "failed": failed[:20], "failed_count": len(failed)}


def my_test_replay_report() -> dict:
    fixture = ROOT / "my_test" / "THONG_TIN_DA_NHAP.json"
    if not fixture.exists():
        return {"name": "my_test_replay", "ok": True, "skipped": True}
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["formIds"] = [form_id for form_id in ["pl1_4", "pl1_7"] if form_id in form_paths()]
    result = generate(payload)
    folder = ROOT / result["folder"]
    pl14 = next(folder.glob("pl1_4_*.docx"), None)
    pl17 = next(folder.glob("pl1_7_*.docx"), None)
    checks = {}
    if pl14:
        summary14 = docx_text_summary(pl14)
        text14 = summary14["text"]
        hkd_labels = r"(Tên hộ kinh doanh|Số Giấy chứng nhận đăng ký hộ kinh doanh|Mã số thuế của hộ kinh doanh|Địa chỉ trụ sở hộ kinh doanh|Tên chủ hộ kinh doanh)"
        checks.update({
            "pl1_4_has_company": "ÁDSA" in text14.upper(),
            "pl1_4_no_status_value": not re.search(r"Tình trạng thành lập[^\n]*ádsa", text14, re.I),
            "pl1_4_no_hkd_value_for_normal_formation": not re.search(hkd_labels + r"[^\n]*ádsa", text14, re.I),
            "pl1_4_no_extra_split_merge_checked": "☒Tách doanh nghiệp" not in text14 and "☒Hợp nhất doanh nghiệp" not in text14 and "☒Chia doanh nghiệp" not in text14,
            "pl1_4_one_checked_box": text14.count("☒") == 1,
        })
    else:
        checks["pl1_4_generated"] = False
    if pl17:
        summary17 = docx_text_summary(pl17)
        checks.update({
            "pl1_7_nontrivial": summary17["paragraph_count"] > 20,
            "pl1_7_has_table": summary17["table_count"] >= 1,
            "pl1_7_has_person_data": "ádsa" in summary17["text"],
        })
    else:
        checks["pl1_7_generated"] = False
    return {
        "name": "my_test_replay",
        "ok": bool(checks) and all(checks.values()),
        "folder": result["folder"],
        "zip": result["zip"],
        "checks": checks,
    }


def pl1_11_org_table_report() -> dict:
    payload = {
        "procedure": "formation",
        "scenario": "normal",
        "entityType": "jsc",
        "procedureLabel": "Thành lập doanh nghiệp",
        "entityLabel": "Công ty cổ phần",
        "scenarioLabel": "Thành lập mới thông thường",
        "flags": {"onlineFiling": True, "beneficialOwner": True, "orgMember": True},
        "data": {
            "company_name": "Công ty Cổ phần Kiểm thử PL1 11",
            "owner_name": "Nguyễn Văn A",
            "owner_id": "001090000001",
            "owner_phone": "0901000001",
            "owner_birth": "01/01/1990",
            "owner_gender": "Nam",
            "owner_email": "a@example.com",
            "street": "1 Lý Thường Kiệt",
            "ward": "Phường Cửa Nam",
            "province": "Hà Nội",
            "hq_street": "10 Trần Hưng Đạo",
            "hq_ward": "Phường Cửa Nam",
            "hq_province": "Hà Nội",
            "registry_office": "Cơ quan đăng ký kinh doanh cấp tỉnh Hà Nội",
            "filing_place": "Hà Nội",
            "business_lines": "6201 - Lập trình máy vi tính",
            "charter_capital": "3.000.000.000 đồng",
            "director_name": "Nguyễn Văn A",
            "accountant_name": "Trần Thị B",
            "tax_method": "Khấu trừ",
        },
        "people": [
            {
                "name": "Công ty TNHH Tổ chức Audit",
                "type": "Tổ chức",
                "idNumber": "0101234567",
                "address": "Hà Nội",
                "capital": "1.500.000.000",
                "ratio": "50",
                "role": "Cổ đông tổ chức sở hữu từ 25% quyền biểu quyết",
            },
            {
                "name": "Nguyễn Văn A",
                "type": "Cá nhân",
                "idNumber": "001090000001",
                "address": "Hà Nội",
                "capital": "1.500.000.000",
                "ratio": "50",
                "role": "Cổ đông sáng lập",
            },
        ],
        "businessLines": [{"code": "6201", "name": "Lập trình máy vi tính", "detail": "", "isPrimary": True}],
        "formIds": ["pl1_11"],
    }
    result = generate(payload)
    folder = ROOT / result["folder"]
    docx = next(folder.glob("pl1_11_*.docx"), None)
    checks = {"pl1_11_generated": docx is not None}
    if docx:
        summary = docx_text_summary(docx)
        text = summary["text"].lower()
        checks.update({
            "pl1_11_has_inserted_table": summary["table_count"] >= 1,
            "pl1_11_has_org_name": "công ty tnhh tổ chức audit" in text,
            "pl1_11_has_org_code": "0101234567" in text,
            "pl1_11_excludes_individual_from_org_table": "001090000001" not in text,
        })
    return {
        "name": "pl1_11_org_table",
        "ok": all(checks.values()),
        "folder": result["folder"],
        "zip": result["zip"],
        "checks": checks,
    }


def run_check(name: str, command: list[str]) -> dict:
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
        return {
            "name": name,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except FileNotFoundError as exc:
        return {"name": name, "ok": False, "error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"name": name, "ok": False, "error": f"timeout: {exc}"}


def full_test() -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)
    checks: list[dict] = []
    index_html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "app" / "app.js").read_text(encoding="utf-8")
    asset_refs = ["/app/styles.css", "/app/data/form_maps.js", "/app/app.js"]
    checks.append({"name": "html_asset_refs", "ok": all(ref in index_html for ref in asset_refs), "refs": asset_refs})
    for asset in ["app/styles.css", "app/app.js", "app/data/form_maps.js", "app/data/form_maps.json"]:
        path = ROOT / asset
        checks.append({"name": f"asset:{asset}", "ok": path.exists() and path.stat().st_size > 0, "bytes": path.stat().st_size if path.exists() else 0})
    checks.append({
        "name": "catalog_uses_full_form_map",
        "ok": "mappedItems = mappedForms().map" in app_js and "mappedItems.length ? mappedItems : fallbackItems" in app_js,
    })

    maps = load_form_maps().get("forms", [])
    missing_templates = [form for form in maps if not (ROOT / form["path"]).exists()]
    checks.append({"name": "form_map_108", "ok": len(maps) == 108 and not missing_templates, "total": len(maps), "missing": missing_templates[:10]})
    pl1_11_map = next((form for form in maps if form.get("id") == "pl1_11"), {})
    pl1_11_structured = [table.get("id") for table in pl1_11_map.get("structuredTables", [])]
    checks.append({
        "name": "pl1_11_structured_table_map",
        "ok": "organization_beneficial_owner_basis" in pl1_11_structured,
        "structuredTables": pl1_11_structured,
    })
    bad_field_labels = []
    for form in maps:
        for field in form.get("fields", []):
            low = str(field.get("label", "")).lower()
            if "tình trạng thành lập" in low or low in {"stt", "tên ngành", "mã ngành"} or "đánh dấu x vào ô thích hợp" in low:
                bad_field_labels.append({"form": form.get("id"), "label": field.get("label")})
    checks.append({"name": "field_map_no_section_placeholders", "ok": not bad_field_labels, "failed": bad_field_labels[:20]})
    template_report = template_sanity_report()
    checks.append({"name": "template_sanity", "ok": template_report["failed_count"] == 0, **template_report})
    checks.append(run_check("python_compile", [sys.executable, "-m", "py_compile", "run_app.py", "tools/build_form_maps.py", "tools/rebuild_templates_from_full.py"]))
    checks.append(run_check("javascript_syntax", ["node", "--check", "app/app.js"]))

    self_report = self_test()
    map_report = map_test()
    checks.append({"name": "self_test_generation", "ok": all(all(item["checks"].values()) for item in self_report["samples"]), "samples": self_report["samples"]})
    checks.append({"name": "map_test_108_generation", "ok": map_report["total"] == 108 and map_report["ok"] == 108, "summary": map_report})
    checks.append(my_test_replay_report())
    checks.append(pl1_11_org_table_report())

    generated_docx = sorted(OUTPUT_DIR.glob("**/*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)[:160]
    docx_results = [validate_docx(path) for path in generated_docx]
    checks.append({
        "name": "generated_docx_openxml",
        "ok": bool(docx_results) and all(item["ok"] for item in docx_results),
        "checked": len(docx_results),
        "failed": [item for item in docx_results if not item["ok"]][:10],
    })

    generated_zips = sorted(OUTPUT_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    zip_results = [validate_zip(path) for path in generated_zips]
    checks.append({
        "name": "generated_zip_integrity",
        "ok": bool(zip_results) and all(item["ok"] for item in zip_results),
        "checked": len(zip_results),
        "failed": [item for item in zip_results if not item["ok"]][:10],
    })

    mac_sources = [
        ROOT / "macos_app" / "BusinessDossierApp.m",
        ROOT / "macos_app" / "Info.plist",
        ROOT / "macos_app" / "build_app.sh",
    ]
    checks.append({
        "name": "mac_app_source_files",
        "ok": all(path.exists() and path.stat().st_size > 0 for path in mac_sources),
        "files": [str(path.relative_to(ROOT)) for path in mac_sources],
    })
    app_bundle = ROOT / "BusinessDossier.app"
    if app_bundle.exists():
        checks.append(run_check("codesign_verify", ["codesign", "--verify", "--deep", "--strict", str(app_bundle)]))

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ok": all(item.get("ok") for item in checks),
        "checks": checks,
    }
    (OUTPUT_DIR / "FULL_TEST_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--map-test":
        print(json.dumps(map_test(), ensure_ascii=False, indent=2))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--full-test":
        print(json.dumps(full_test(), ensure_ascii=False, indent=2))
        return
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    OUTPUT_DIR.mkdir(exist_ok=True)
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"App dang chay tai http://127.0.0.1:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
