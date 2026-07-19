#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def slug(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:80] or "field"


def text_of(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.findall(".//w:t", NS)).strip()


def load_docx(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as z:
        return ET.fromstring(z.read("word/document.xml"))


def field_type(label: str) -> str:
    low = label.lower()
    if any(k in low for k in ["ngày", "tháng", "năm sinh", "thời hạn"]):
        return "date"
    if any(k in low for k in ["điện thoại", "số fax"]):
        return "phone"
    if any(k in low for k in ["thư điện tử", "email"]):
        return "email"
    if any(k in low for k in ["vốn", "mệnh giá", "tổng số", "tỷ lệ", "số lượng"]):
        return "money_or_number"
    if len(label) > 80 or any(k in low for k in ["nội dung", "lý do", "ngành", "địa chỉ"]):
        return "textarea"
    return "text"


SECTION_HINTS = [
    "đánh dấu x",
    "đánh dấu vào",
    "chọn một trong",
    "ô thích hợp",
    "kê khai trong trường hợp",
    "doanh nghiệp phải đánh dấu",
]

TABLE_HEADER_LABELS = {
    "stt",
    "tên ngành",
    "mã ngành",
    "ghi chú",
    "chữ ký",
    "tỷ lệ",
    "giá trị",
    "số lượng",
}


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().strip(":").lower()


def has_blank_after_colon(text: str) -> bool:
    if ":" not in text:
        return False
    after = text.split(":", 1)[1]
    return bool(re.search(r"[.…_\-]{3,}", after)) or not after.strip()


def is_section_heading(label: str, text: str) -> bool:
    low = normalize_label(label)
    full = normalize_label(text)
    if any(hint in full for hint in SECTION_HINTS):
        return True
    if re.match(r"^\d+[\.\)]\s+", low) and not has_blank_after_colon(text):
        return True
    if "ngành, nghề kinh doanh" in low and "ghi tên và mã" in low:
        return True
    if "thông báo thay đổi ngành, nghề kinh doanh" in low:
        return True
    if "tên ngành, nghề kinh doanh được" in low:
        return True
    if low.startswith("- trường hợp"):
        return True
    if low in TABLE_HEADER_LABELS:
        return True
    if low.startswith(("lưu ý", "ghi chú")):
        return True
    return False


def infer_common_key(label: str) -> str | None:
    low = label.lower()
    rules = [
        ("company_name", ["tên doanh nghiệp", "tên công ty", "tên hộ kinh doanh"]),
        ("company_code", ["mã số doanh nghiệp", "mã số thuế", "mã số hộ kinh doanh"]),
        ("owner_name", ["tôi là", "chủ hộ", "tên chủ hộ", "họ, chữ đệm và tên"]),
        ("owner_birth", ["ngày, tháng, năm sinh", "sinh ngày"]),
        ("owner_gender", ["giới tính"]),
        ("owner_id", ["số định danh cá nhân"]),
        ("owner_phone", ["điện thoại"]),
        ("owner_email", ["thư điện tử", "email"]),
        ("street", ["số nhà/phòng"]),
        ("ward", ["xã/phường/đặc khu"]),
        ("province", ["tỉnh/thành phố"]),
        ("charter_capital", ["vốn điều lệ", "vốn đầu tư", "vốn kinh doanh"]),
        ("business_lines", ["ngành, nghề", "ngành nghề"]),
        ("change_content", ["nội dung đăng ký thay đổi", "nội dung thay đổi"]),
        ("dissolve_reason", ["lý do giải thể", "lý do chấm dứt"]),
    ]
    for key, needles in rules:
        if any(needle in low for needle in needles):
            return key
    return None


def extract_fields(root: ET.Element) -> list[dict]:
    fields: list[dict] = []
    seen: set[str] = set()
    for idx, p in enumerate(root.findall(".//w:p", NS)):
        text = re.sub(r"\s+", " ", text_of(p))
        if not text:
            continue
        if "□" in text:
            continue
        candidates = []
        if ":" in text and any(ch in text for ch in ".…_"):
            label = text.split(":", 1)[0].strip() + ":"
            candidates.append(label)
        if re.match(r"^(Tôi là|Kính gửi|Tên|Mã số|Số|Ngày|Địa chỉ|Điện thoại|Thư điện tử|Vốn|Lý do|Nội dung|Họ, chữ đệm)", text):
            label = text.split(":", 1)[0].strip() + (":" if ":" in text else "")
            if 4 <= len(label) <= 140:
                candidates.append(label)
        for label in candidates:
            if is_section_heading(label, text):
                continue
            key = slug(label)
            if key in seen:
                continue
            seen.add(key)
            fields.append(
                {
                    "id": key,
                    "label": label,
                    "type": field_type(label),
                    "commonKey": infer_common_key(label),
                    "paragraphIndex": idx,
                    "requiredGuess": any(k in label.lower() for k in ["tên", "mã số", "địa chỉ", "số định danh", "vốn"]),
                }
            )
    return fields


def extract_structured_tables(root: ET.Element) -> list[dict]:
    paragraphs = [re.sub(r"\s+", " ", text_of(p)) for p in root.findall(".//w:p", NS)]
    tables: list[dict] = []
    seen: set[str] = set()

    def add(table_id: str, title: str, anchor: int, columns: list[dict]) -> None:
        if table_id in seen:
            return
        seen.add(table_id)
        tables.append({"id": table_id, "title": title, "anchorParagraph": anchor, "columns": columns})

    business_columns = [
        {"key": "code", "label": "Mã ngành cấp 4"},
        {"key": "name", "label": "Tên ngành, nghề kinh doanh"},
        {"key": "detail", "label": "Chi tiết ngành nghề nếu cần ghi rõ", "optional": True},
        {"key": "isPrimary", "label": "Là ngành nghề kinh doanh chính", "type": "checkbox"},
    ]
    change_columns = [
        {"key": "action", "label": "Loại thay đổi", "type": "select", "options": ["Bổ sung", "Bỏ", "Sửa chi tiết"]},
        {"key": "code", "label": "Mã ngành"},
        {"key": "name", "label": "Tên ngành, nghề"},
        {"key": "detail", "label": "Chi tiết/Ghi chú", "optional": True},
        {"key": "isPrimary", "label": "Là ngành nghề chính", "type": "checkbox"},
    ]
    organization_owner_columns = [
        {"key": "name", "label": "Tên tổ chức"},
        {"key": "idNumber", "label": "Mã số doanh nghiệp/số QĐ thành lập"},
        {"key": "issuedDate", "label": "Ngày cấp", "optional": True},
        {"key": "issuedPlace", "label": "Nơi cấp", "optional": True},
        {"key": "address", "label": "Địa chỉ trụ sở chính"},
        {"key": "ratio", "label": "Tỷ lệ sở hữu cổ phần có quyền biểu quyết"},
        {"key": "role", "label": "Ghi chú", "optional": True},
    ]

    for idx, text in enumerate(paragraphs):
        low = text.lower()
        if "danh sách để xác định chủ sở hữu hưởng lợi" in low or "cổ đông là tổ chức sở hữu từ 25%" in low:
            add("organization_beneficial_owner_basis", "Danh sách tổ chức để xác định chủ sở hữu hưởng lợi", idx, organization_owner_columns)
        if "ngành, nghề kinh doanh" in low and "ghi tên và mã" in low:
            add("business_lines", "Ngành, nghề kinh doanh", idx, business_columns)
        if "bổ sung ngành, nghề kinh doanh" in low:
            add("business_lines_change", "Bảng thay đổi ngành, nghề kinh doanh", idx, change_columns)
        if "danh sách thành viên" in low and "công ty trách nhiệm hữu hạn" in low:
            add("members", "Danh sách thành viên góp vốn", idx, [
                {"key": "name", "label": "Họ tên/Tên tổ chức"},
                {"key": "idNumber", "label": "Số giấy tờ pháp lý/MST"},
                {"key": "address", "label": "Địa chỉ liên lạc/trụ sở"},
                {"key": "capital", "label": "Giá trị phần vốn góp"},
                {"key": "ratio", "label": "Tỷ lệ phần vốn góp (%)"},
                {"key": "role", "label": "Vai trò", "optional": True},
            ])
        if "danh sách cổ đông" in low:
            add("shareholders", "Danh sách cổ đông", idx, [
                {"key": "name", "label": "Họ tên/Tên tổ chức"},
                {"key": "idNumber", "label": "Số giấy tờ pháp lý/MST"},
                {"key": "address", "label": "Địa chỉ liên lạc/trụ sở"},
                {"key": "shareType", "label": "Loại cổ phần"},
                {"key": "shares", "label": "Số cổ phần"},
                {"key": "ratio", "label": "Tỷ lệ (%)"},
            ])
        if "chủ sở hữu hưởng lợi" in low and "xác định chủ sở hữu hưởng lợi" not in low:
            add("beneficial_owners", "Danh sách chủ sở hữu hưởng lợi", idx, [
                {"key": "name", "label": "Họ tên cá nhân hưởng lợi"},
                {"key": "idNumber", "label": "Số định danh cá nhân"},
                {"key": "address", "label": "Địa chỉ liên lạc"},
                {"key": "basis", "label": "Căn cứ xác định hưởng lợi"},
                {"key": "ratio", "label": "Tỷ lệ sở hữu/quyền biểu quyết (%)", "optional": True},
            ])
    return tables


def extract_checkboxes(root: ET.Element) -> list[dict]:
    items: list[dict] = []
    prev = ""
    seen: set[str] = set()
    for idx, p in enumerate(root.findall(".//w:p", NS)):
        text = re.sub(r"\s+", " ", text_of(p))
        if "□" in text or text == "☒":
            label = prev if text in {"□", "☒"} else text.replace("□", "").strip()
            key = slug(label)
            if label and key not in seen:
                seen.add(key)
                items.append({"id": key, "label": label, "paragraphIndex": idx})
        if text and "□" not in text:
            prev = text
    return items


def extract_tables(root: ET.Element) -> list[dict]:
    tables = []
    for idx, tbl in enumerate(root.findall(".//w:tbl", NS)):
        rows = []
        for tr in tbl.findall(".//w:tr", NS)[:3]:
            rows.append([re.sub(r"\s+", " ", text_of(tc)) for tc in tr.findall("./w:tc", NS)])
        flat = " ".join(" ".join(row) for row in rows).strip()
        if flat:
            tables.append({"id": f"table_{idx+1}", "sample": flat[:500], "columnsGuess": rows[0] if rows else []})
    return tables


def catalog() -> dict[tuple[str, int], str]:
    out: dict[tuple[str, int], str] = {}
    csv_path = ROOT / "99_muc_luc" / "muc_luc_bieu_mau.csv"
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pl = "PL2" if "II" in row["phu_luc"] else "PL1"
            out[(pl, int(row["mau_so"]))] = row["ten_mau"]
    return out


def choose_unique_paths() -> list[Path]:
    chosen: dict[tuple[str, int], Path] = {}
    for path in sorted(ROOT.glob("**/PL*_Mau_*.docx")):
        m = re.search(r"(PL[12])_Mau_(\d+)", path.name)
        if not m:
            continue
        key = (m.group(1), int(m.group(2)))
        if key not in chosen:
            chosen[key] = path
    return [chosen[key] for key in sorted(chosen, key=lambda x: (x[0], x[1]))]


def main() -> None:
    names = catalog()
    forms = []
    for path in choose_unique_paths():
        m = re.search(r"(PL[12])_Mau_(\d+)", path.name)
        if not m:
            continue
        pl, num = m.group(1), int(m.group(2))
        root = load_docx(path)
        forms.append(
            {
                "id": f"{pl.lower()}_{num}",
                "pl": pl,
                "num": num,
                "title": names.get((pl, num), path.stem),
                "path": str(path.relative_to(ROOT)),
                "fields": extract_fields(root),
                "checkboxes": extract_checkboxes(root),
                "tables": extract_tables(root),
                "structuredTables": extract_structured_tables(root),
            }
        )
    data = {"generatedFrom": "tools/build_form_maps.py", "count": len(forms), "forms": forms}
    out_json = ROOT / "app" / "data" / "form_maps.json"
    out_js = ROOT / "app" / "data" / "form_maps.js"
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    out_js.write_text("window.FORM_MAPS = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"mapped {len(forms)} forms")
    print(out_json)


if __name__ == "__main__":
    main()
