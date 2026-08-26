# -*- coding: utf-8 -*-
"""Semantic role classifier cho block "p" — Wave L1 (lane layout-l1).

Module THUẦN (không import python-docx, không IO) để dễ test và tái sử dụng:
    classify_role(text_folded, format, runs) -> str  (một giá trị trong ROLES)

Contract:
- text_folded: text đầy đủ của block (bao gồm ký tự xuống hàng "\\n" từ hard
  break) đã qua fold() — bỏ dấu, lowercase, đ→d, dồn whitespace. fold() DỜN
  cả "\\n" thành khoảng trắng; khi cần cấu trúc nhiều dòng, classifier tự dựng
  raw text từ `runs` (các run dict có key "text").
- format: dict paragraph format của block (có thể None/rỗng) — hiện tại chỉ
  dùng làm ngữ cảnh dự phòng, rule chính dựa trên text.
- runs: list run dict theo schema blocks ({"text":...} / {"input":...} /
  {"role":"footnote-ref",...}); dùng để nhận diện input ngày/tháng/năm và
  dựng raw text.

Thứ tự rule cố định (match đầu tiên thắng), xem ROLE_RULES_ORDER trong test.
Override tường minh nằm ngoài module này (tools/layout_role_overrides.json,
do Lead/owner điền — converter áp trước khi emit).
"""
from __future__ import annotations

import re
import unicodedata

ROLES = frozenset(
    {
        "source-indicator",
        "form-number",
        "national-header",
        "national-motto",
        "national-separator",
        "date-line",
        "form-title",
        "form-subtitle",
        "salutation",
        "body",
        "section-heading",
        "note",
        "footnote",
        "signature",
    }
)

DEFAULT_ROLE = "body"


def fold(text: str) -> str:
    """Gập dấu giống tools/census/p1_c_verify_plii_m02.py: NFD bỏ Mn, đ->d,
    dồn whitespace (kể cả \\n) thành một khoảng trắng."""
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


# ---------------------------------------------------------------------------
# Pattern (áp trên text đã fold)
# ---------------------------------------------------------------------------

# Marker kỹ thuật kiểu "PL1 - Mau so 1: ...", "PL2-Mau so ...", "PLI_M12 - ..."
SOURCE_INDICATOR_RE = re.compile(r"^pl\d+\s*[-–]?\s*mau\s+so\b")
# Tên file đuôi tài liệu xuất hiện trong text block
FILENAME_RE = re.compile(
    r"(^|\s)[a-z0-9_\-\. ]{0,64}\.(docx?|pdf|xlsm?|png|jpe?g)(\s|$|[.,;:)])"
)
# Nhãn import/scrape/descriptor kỹ thuật
IMPORT_LABEL_RE = re.compile(
    r"^(nguon du lieu|nguon:|source:|file:|scrape|scraper|import|nhap tu file|"
    r"du lieu nhap tu|descriptor)\b"
)
FORM_NUMBER_RE = re.compile(r"^mau so\s*\d{1,4}\b")
MOTTO_RE = re.compile(r"^doc lap\s*[-–—]\s*tu do\s*[-–—]\s*hanh phuc\b")
NATIONAL_HEADER_RE = re.compile(r"^cong hoa xa hoi chu nghia viet nam")
SALUTATION_RE = re.compile(r"^(kinh gui|kinh thua)\b")
NOTE_RE = re.compile(r"^(ghi chu|chu y|luu y|luu y:)\b")
SEPARATOR_ONLY_RE = re.compile(r"^[-_.~—–−•*=\s]{3,}$")

DATE_LITERAL_RE = re.compile(r"\bngay\b.{0,20}\bthang\b.{0,20}\bnam\b")
DATE_KEY_RE = re.compile(r"(ngay|thang|nam)[a-z0-9_]*ky|^dia_diem_ky$")

TITLE_KEYWORD_RE = re.compile(
    r"(giay de nghi|giay chung nhan|giay xac nhan|don de nghi|to khai|"
    r"thong bao|phu luc|bang ke|bieu mau|de nghi cap)"
)
SUBTITLE_WORD_RE = re.compile(
    r"(cong ty|doanh nghiep|ho kinh doanh|trach nhiem huu han|"
    r"cong hop tac|hop danh|mot thanh vien|hai thanh vien tro len|nha nuoc)"
)
SIGNER_LABEL_RE = re.compile(
    r"^(chu ho kinh doanh|dai dien chu ho|chu doanh nghiep|nguoi dai dien theo "
    r"phap luat|dai dien theo phap luat|nguoi khai ho so|nguoi nop ho so|"
    r"nguoi uy quyen|nguoi ky|truong ban|giam doc|ketoan|ke toan|ban giao dich|"
    r"dai dien cong ty|chu tich|thu ky)\b"
)
SIGN_PAREN_RE = re.compile(
    r"\((?:[^()]{0,40}?)?(ky va ghi ho ten|ky ten|ky, ghi ro ho ten|"
    r"ky, ho ten|ghi ro ho ten|ky, ho ten, dong dau|da ky)\b"
)
FOOTNOTE_BODY_RE = re.compile(r"^\d{1,2}(?![.)])\s+\S")
SECTION_HEADING_NUM_RE = re.compile(
    r"^(\d+(\.\d+)*|[a-z][.)]|i{1,3}|iv|v|vi{1,3}|ix|x)[.)]?\s+\S"
)


def _raw_text_from_runs(runs) -> str:
    parts = []
    for r in runs or ():
        if isinstance(r, dict) and "text" in r:
            parts.append(str(r.get("text") or ""))
    return "".join(parts)


def _input_keys(runs) -> list[str]:
    keys = []
    for r in runs or ():
        if isinstance(r, dict) and "input" in r:
            k = (r["input"] or {}).get("key")
            if k:
                keys.append(str(k))
    return keys


def _caps_ratio(text: str) -> float:
    alpha = [c for c in text if c.isalpha()]
    if len(alpha) < 4:
        return 0.0
    upper = sum(1 for c in alpha if c.isupper())
    return upper / len(alpha)


def _is_date_line(folded: str, runs) -> bool:
    if DATE_LITERAL_RE.search(folded):
        return True
    keys = [k.lower().replace("đ", "d") for k in _input_keys(runs)]
    date_keys = [k for k in keys if DATE_KEY_RE.search(k)]
    return len(date_keys) >= 2


def classify_role(text_folded: str, format=None, runs=None) -> str:
    """Trả về role cho một block "p". Match đầu tiên theo thứ tự dưới đây."""
    folded = (text_folded or "").strip()
    if not folded:
        return DEFAULT_ROLE
    raw = _raw_text_from_runs(runs)
    # Caller không truyền runs -> coi text đưa vào vừa là raw (giữ hoa/\n)
    # vừa là bản gập dấu; các rule cấu trúc vẫn chạy được.
    raw_stripped = raw.strip() if raw.strip() else folded

    # 1. Marker kỹ thuật / tên file / nhãn import — KHÔNG ĐƯỢC nhầm với
    #    form-number pháp lý (rule này phải đứng trước FORM_NUMBER_RE vì
    #    "PL1 - Mau so 1: ..." cũng chứa "mau so").
    if SOURCE_INDICATOR_RE.match(folded):
        return "source-indicator"
    if IMPORT_LABEL_RE.match(folded):
        return "source-indicator"
    if FILENAME_RE.search(folded) and len(folded) <= 200:
        return "source-indicator"

    # 2. Quốc hiệu khối nhiều dòng ("CỘNG HÒA ...\\nĐộc lập ...\\n-----")
    first_line = raw.split("\n", 1)[0].strip() if raw else ""
    if NATIONAL_HEADER_RE.match(fold(first_line)):
        return "national-header"

    # 3. Tiêu ngữ đơn dòng + đường kẻ ngang
    if MOTTO_RE.match(folded):
        return "national-motto"
    if SEPARATOR_ONLY_RE.match(raw_stripped):
        return "national-separator"

    # 4. Dòng pháp lý "Mẫu số N" — hiển thị bình thường, không được ẩn
    if FORM_NUMBER_RE.match(folded) and len(folded) <= 80:
        return "form-number"

    # 5. Kính gửi / Kính thưa
    if SALUTATION_RE.match(folded):
        return "salutation"

    # 6. Dòng ngày tháng (địa điểm ký, ngày … tháng … năm …)
    if _is_date_line(folded, runs) and len(folded) <= 120:
        return "date-line"

    # 7. Chữ ký — "(Ký và ghi họ tên)" hoặc nhãn người ký IN HOA đứng đầu dòng
    if SIGN_PAREN_RE.search(folded):
        return "signature"
    if (
        SIGNER_LABEL_RE.match(folded)
        and len(folded) <= 80
        and _caps_ratio(raw_stripped or folded) >= 0.6
    ):
        return "signature"

    # 8. Ghi chú
    if NOTE_RE.match(folded):
        return "note"

    # 9. Tiêu đề biểu mẫu (chữ IN, có từ khóa tiêu đề); phụ đề IN còn lại
    caps = _caps_ratio(raw_stripped or folded)
    if caps >= 0.7 and TITLE_KEYWORD_RE.search(folded) and len(folded) <= 200:
        return "form-title"
    # 10. Thân chú thích chân trang "6 Chủ hộ kinh doanh ký trực tiếp…" —
    #     số đứng trước chữ KHÔNG có dấu chấm/ngoặc (tránh nhầm mục lục "1.")
    if FOOTNOTE_BODY_RE.match(folded) and len(folded) <= 160:
        return "footnote"

    # 11. Heading đánh số "1." / "I." kết thúc dấu ":" hoặc chữ IN ngắn
    if SECTION_HEADING_NUM_RE.match(folded) and len(folded) <= 120:
        return "section-heading"
    if caps >= 0.7 and len(folded) <= 120:
        if folded.endswith(":"):
            return "section-heading"
        if SUBTITLE_WORD_RE.search(folded):
            return "form-subtitle"
        return "form-subtitle"

    return DEFAULT_ROLE
