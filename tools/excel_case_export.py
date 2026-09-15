# -*- coding: utf-8 -*-
"""Xuất workbook Excel CASE-LEVEL cho khách — wave E1 (PLAN_hoan_thien_pfat_hanh §2.1, §5-E1).

Khác `tools/excel_export.py` (phiếu theo MỘT form đang mở, wave X2), module này
xuất MỘT workbook cho TOÀN BỘ case theo manifest case-level
(`app/data/case_questionnaires/<caseId>.json`, wave E0):

  DKKD_<caseId>_<8-ký-tự-hash>.xlsx
    ├─ Hướng_dẫn          7 bước + phiên bản + trạng thái form + lưu ý case
    ├─ Thông_tin_chung    trường data-key dùng chung ≥2 form — hỏi MỘT lần
    ├─ 01_<tên mẫu>…      mỗi form approved một sheet, chỉ câu của form đó
    ├─ Giấy_tờ_cần_gửi    watermark "chờ duyệt" (ho_so_bao_gom chưa DECIDED,
    │                     docs/p4_excel_review_gate.md mục 4) — fail-safe
    ├─ __lists  veryHidden  danh mục dropdown + named range LST_nnnn
    └─ __map    veryHidden  hợp đồng máy đọc: schema/case/hash/forms + MỖI ô
                          điền một dòng + CHECKSUM sha256 (import verify
                          TRƯỚC khi đọc answers — wave E2)

Style giữ nguyên triết lý X2: ô VÀNG `locked=False` chỉ vùng nhập; ô XÁM là
app tự làm (`autofill`); `number_format="@"` chống mất số 0 đầu/ngày tự đổi;
sheet protection không mật khẩu (sai khung bị import bắt lỗi — fail-loud, nhờ
vậy failure mode "khách mất mật khẩu" không tồn tại).

Shared key (nhiều form dùng chung một data-key): MỘT ô canonical ở
`Thông_tin_chung`, các form khác là ô mirror READ-ONLY chứa công thức tham
chiếu về ô canonical — CẤM last-write-wins. Import chỉ đọc ô canonical; ô
mirror bị khách sửa tay (vượt protection) bị từ chối (MIRROR_CELL).

Escape formula: openpyxl tự biến chuỗi bắt đầu `=` thành công thức nên mọi
chuỗi app ghi vào ô đi qua `_set_text` — chuỗi bắt đầu `=`, `+`, `-`, `@` bị
ép `data_type="s"` (lưu nguyên văn dạng Text; Excel mở lên là chữ, không bao
giờ được tính). Chiều ngược lại, importer TỪ CHỐI mọi ô điền chứa công thức
(khách gõ `=cmd|…` vào ô vàng).

Đối tác đọc lại: `tools/excel_case_import.py` (wave E2) — hai module ĐỐI XỨNG
theo contract hằng dưới đây; KHÔNG đổi một bên mà không đồng bộ bên kia.

KHÔNG dùng pandas; chỉ openpyxl (an toàn đóng gói Windows R6).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.protection import Protection
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

# Style + hằng render dùng chung với lane X2 — MỘT nguồn triết lý màu/bố cục
# (excel_export nhập tiếp từ tools.questionnaire.schema, không import chéo ngược).
from tools.excel_export import (
    BORDER_HEX, COLUMN_WIDTHS, GOLD_HEX, GRAY_HEX, GROUP_PALETTE,
    GUIDE_FONT_HEX, MARK_VALUE, META_FONT_HEX, NOTE_FONT_HEX, REPEAT_ROWS,
)
from tools.excel_import import _when_match
from tools.questionnaire.schema import DATE_NOTE, EXAMPLE_PREFIX, SELECT_NOTE

__all__ = [
    "CASE_MAP_VERSION", "COMMON_SHEET", "CONTRACT", "CUSTOMER_SHEET",
    "DOCS_SHEET", "EXPORT_MODE_CUSTOMER", "EXPORT_MODE_FULL",
    "ExcelCaseExportError", "GUIDE_SHEET", "LISTS_SHEET", "MAP_COLUMNS",
    "MAP_MARKER", "MAP_SHEET", "ONEOF_KEY_PREFIX",
    "OPTIONAL_FORM_KEY_PREFIX", "REVIEW_APPROVED", "REVIEW_DELEGATED",
    "REVIEW_PENDING", "expand_wizard_answers", "sheet_display_name",
    "is_review_approved", "is_selector_question", "workbook_stem",
    "write_case_workbook",
]

# ---------------------------------------------------------------------------
# Contract cố định (tools/excel_case_import.py đọc; KHÔNG đổi một phía)
# ---------------------------------------------------------------------------
CONTRACT = "EXCEL_CASE_V2"          # marker loại file trong metadata __map
CASE_MAP_VERSION = 1
MAP_MARKER = "__EXCEL_CASE_MAP_V2__"

GUIDE_SHEET = "Hướng_dẫn"
COMMON_SHEET = "Thông_tin_chung"
CUSTOMER_SHEET = "Phiếu_khách"
DOCS_SHEET = "Giấy_tờ_cần_gửi"
MAP_SHEET = "__map"
LISTS_SHEET = "__lists"

EXPORT_MODE_FULL = "full"
EXPORT_MODE_CUSTOMER = "customer"
_EXPORT_MODES = (EXPORT_MODE_FULL, EXPORT_MODE_CUSTOMER)

# --- Wave E4: mức content review + câu SELECTOR pseudo-key ------------------
# (hợp đồng với build_case_questionnaires / excel_case_import — đổi một bên
# phải đồng bộ bên kia.)
REVIEW_APPROVED = "approved"
REVIEW_DELEGATED = "owner_delegated_2026-09-10"
REVIEW_PENDING = "pending"
APPROVED_EQUIV = (REVIEW_APPROVED, REVIEW_DELEGATED)

ONEOF_KEY_PREFIX = "oneOf."              # chọn 1 mẫu trong nhóm forms_oneOf
OPTIONAL_FORM_KEY_PREFIX = "optionalForm."   # tick "có làm mẫu này không?"


def is_review_approved(review) -> bool:
    """`approved` (X1) lẫn `owner_delegated_2026-09-10` (E4/E5) đều ok."""
    return review in APPROVED_EQUIV


def is_selector_question(item: dict) -> bool:
    """Câu SELECTOR do builder nhúng (data_key `oneOf.*`/`optionalForm.*`):
    render MỘT lần ở `Thông_tin_chung`, KHÔNG render trên sheet form."""
    raw = item.get("data_key")
    keys = [raw] if isinstance(raw, str) else \
        [t.get("key") for t in raw or []]
    return any(isinstance(k, str) and
               (k.startswith(ONEOF_KEY_PREFIX) or
                k.startswith(OPTIONAL_FORM_KEY_PREFIX))
               for k in keys)

TITLE_ROW = 1
META_ROW = 2
GUIDE_FIRST_ROW = 3
GUIDE_ROWS = 5
FIRST_BODY_ROW = 9                   # giống lane X2: hàng 8 là đệm
# Thông_tin_chung DÙNG CÙNG khối header/hướng dẫn (hàng 3..7 merge A:D) nên
# body cũng phải bắt đầu SAU hàng 8 — bắt đầu sớm hơn sẽ ghi đè vùng merge.
COMMON_BODY_ROW = FIRST_BODY_ROW

CUSTOMER_BODY_ROW = 7   # customer: hàng 1 tiêu đề, 2–6 hướng dẫn, body từ hàng 7

COL_LABEL = 1
COL_FILL = 2
COL_NOTE = 3
COL_DATE_NOTE = 4
MAX_FILL_COLUMN = 6

# Cột bảng __map — thứ tự cố định, importer đọc theo tên cột
MAP_COLUMNS = (
    "form_id", "sheet", "question_id", "key", "when", "transform",
    "row_group", "layout", "cell", "row_last", "repeatable", "autofill",
    "required", "version", "multi_key", "shared", "mirror",
    "canonical_sheet", "canonical_cell",
)
MAP_HEADER_ROW = 3
MAP_FIRST_ROW = 4

MAX_SHEET_NAME = 31                  # giới hạn cứng tên sheet Excel
_SHEET_BAD_CHARS = set("[]:*?/\\")

GUIDE_LINES = (
    "Đây là phiếu thu thập thông tin cho TOÀN BỘ hồ sơ (một file cho cả case), "
    "không phải biểu mẫu pháp lý — ứng dụng sẽ tự điền vào mẫu chính thức.",
    "Ô NỀN VÀNG là phần bạn điền. Ô NỀN XÁM phần ứng dụng tự điền giúp bạn, "
    "không cần làm gì.",
    "CHỈ điền vào ô vàng. Không sửa, xóa, chèn/xóa hàng hay đổi tên sheet/cột — "
    "phiếu lệch khung sẽ bị từ chối lúc nạp kèm danh sách lỗi có ô cụ thể.",
    "Ô có mũi tên ▾ là danh sách chọn: bấm mũi tên rồi CHỌN một dòng, "
    "không gõ tay.",
    "Ngày ghi theo dạng dd/mm/yyyy (ví dụ 05/12/1985). Số tiền/số lượng ghi "
    "bằng số, có thể dùng dấu chấm ngăn cách nghìn (ví dụ 5.000.000).",
    "Chữ mờ ngay dưới nhãn là VÍ DỤ điền mẫu — làm theo mẫu. Bỏ trống ô bạn "
    "chưa có thông tin, sẽ được nhắc lại lúc nạp phiếu.",
    "Trả lại đúng file .xlsx này cho người gửi. Không đổi tên sheet, không "
    "xóa sheet ẩn.",
)

CUSTOMER_GUIDE_LINES = (
    "Đây là phiếu thu thập thông tin rút gọn — không phải biểu mẫu pháp lý.",
    "Điền các câu ở đầu phiếu (trường hợp thành lập, loại giấy tờ…) TRƯỚC "
    "khi điền các mục «(nếu có)» bên dưới.",
    "Ô NỀN VÀNG là phần bạn điền. CHỈ điền vào ô vàng; không sửa khung sheet.",
    "Ô có mũi tên ▾: bấm và CHỌN một dòng trong danh sách, không gõ tay.",
    "Ngày ghi dd/mm/yyyy (ví dụ 05/12/1985). Ngành nghề: chỉ ghi MÃ VSIC cấp 4 "
    "(ví dụ 6201) — app tự tra tên ngành.",
)


class ExcelCaseExportError(ValueError):
    """Lỗi manifest/meta khi xuất workbook case — fail-loud, có `code`."""

    def __init__(self, code: str, message: str):
        super().__init__("[%s] %s" % (code, message))
        self.code = code


# ---------------------------------------------------------------------------
# Style helpers (mỗi lần gọi tạo mới — style object không dùng chung)
# ---------------------------------------------------------------------------

_THIN = Side(style="thin", color=BORDER_HEX)


def _border() -> Border:
    return Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _fill(hex_color: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=hex_color)


def _wrap(vertical: str = "top") -> Alignment:
    return Alignment(wrap_text=True, vertical=vertical, horizontal="left")


def _set_text(cell, text) -> None:
    """Ghi chuỗi vào ô; ép dạng Text nếu bắt đầu `=`, `+`, `-`, `@` (escape).

    openpyxl gán `data_type="f"` cho chuỗi đầu `=` (thành công thức khi mở
    file). Ép lại `"s"` để lưu nguyên văn — đây là "escape" theo contract.
    """
    cell.value = text
    if isinstance(text, str) and text[:1] in ("=", "+", "-", "@"):
        cell.data_type = "s"


def _canonical_json(payload) -> str:
    """Chuỗi canonical để tính checksum — sort key, ASCII, không khoảng trắng."""
    return json.dumps(payload, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"))


# ---------------------------------------------------------------------------
# Kiểm tra manifest — fail-loud trước khi đụng file
# ---------------------------------------------------------------------------

def _validate_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        raise ExcelCaseExportError("NOT_OBJECT", "manifest phải là dict")
    for field in ("case_id", "case_title", "manifest_hash", "forms"):
        if field not in manifest:
            raise ExcelCaseExportError("MISSING_FIELD", "manifest thiếu %r" % field)
    forms = manifest["forms"]
    if not isinstance(forms, list) or not forms:
        raise ExcelCaseExportError("NO_FORMS", "manifest không có form nào")
    approved = 0
    qids: set[str] = set()
    for form in forms:
        for field in ("form_id", "content_review", "questions"):
            if field not in form:
                raise ExcelCaseExportError(
                    "MISSING_FIELD", "%s: thiếu %r" % (form.get("form_id"), field))
        review = form["content_review"]
        # approved = owner duyệt nguyên văn (wave X1);
        # owner_delegated_2026-09-10 = nội dung sinh theo ủy quyền của owner
        # cùng ngày (wave E4/E5) — hai mức ĐỀU đủ điều kiện phát hành.
        if review not in APPROVED_EQUIV and review != REVIEW_PENDING:
            raise ExcelCaseExportError(
                "BAD_REVIEW", "%s: content_review lạ %r" % (form["form_id"], review))
        if not isinstance(form["questions"], list):
            raise ExcelCaseExportError(
                "BAD_QUESTIONS", "%s: questions phải là list" % form["form_id"])
        if review in APPROVED_EQUIV and not form["questions"]:
            raise ExcelCaseExportError(
                "EMPTY_APPROVED",
                "%s: approved nhưng questions rỗng — manifest hỏng" % form["form_id"])
        if review == REVIEW_PENDING and form["questions"]:
            raise ExcelCaseExportError(
                "PENDING_WITH_QUESTIONS",
                "%s: pending nhưng có questions — cấm tự sáng tác nội dung"
                % form["form_id"])
        if review in APPROVED_EQUIV:
            approved += 1
        for item in form["questions"]:
            qid = item.get("question_id")
            if not isinstance(qid, str) or not qid:
                raise ExcelCaseExportError(
                    "BAD_QUESTION", "%s: câu thiếu question_id" % form["form_id"])
            if qid in qids:
                raise ExcelCaseExportError(
                    "DUP_ID", "question_id trùng toàn case: %r" % qid)
            qids.add(qid)
    if not approved:
        raise ExcelCaseExportError(
            "CASE_NOT_READY",
            "case %s chưa có form nào được duyệt nội dung — KHÔNG phát hành "
            "workbook khuyết cho khách (gate E4)" % manifest["case_id"])
    return manifest


def _validate_meta(meta: dict | None) -> dict:
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise ExcelCaseExportError("BAD_META", "meta phải là dict hoặc None")
    for key in ("today", "exported_at"):
        value = meta.get(key)
        if value is not None and not isinstance(value, str):
            raise ExcelCaseExportError(
                "BAD_META", "meta[%r] phải là chuỗi" % key)
    return meta


def _targets(item: dict) -> list[dict]:
    """`data_key` (string | list target) -> list target {key, when, transform}."""
    raw = item["data_key"]
    q_when = item.get("when")
    if isinstance(raw, str):
        target = {"key": raw}
        if q_when:
            target["when"] = q_when
        return [target]
    return list(raw)


def _question_when(item: dict) -> dict:
    """Điều kiện `when` cấp câu hỏi (string hoặc target đầu list)."""
    when = item.get("when")
    if when:
        return when
    raw = item.get("data_key")
    if isinstance(raw, list):
        for target in raw:
            if isinstance(target, dict) and target.get("when"):
                return target["when"]
    return {}


def _customer_branch(item: dict) -> dict:
    """Nhánh bật câu ở export customer — không ghi vào __map/import."""
    branch = item.get("customer_branch")
    return branch if isinstance(branch, dict) else {}


def _customer_gate(item: dict, virtual_answers: dict[str, str]) -> bool:
    """True nếu mọi điều kiện customer (when + customer_branch) thỏa."""
    for cond in (_question_when(item), _customer_branch(item)):
        if cond and not _when_match(cond, virtual_answers):
            return False
    return True


def _effective_tier(item: dict) -> str:
    if item.get("wizard"):
        return "wizard"
    tier = item.get("tier")
    if tier:
        return tier
    if _question_when(item):
        return "conditional"
    if not item.get("required"):
        return "conditional"
    return "core"


def _wizard_sets_for_value(item: dict, value) -> dict[str, str]:
    if item.get("type") != "select" or value is None:
        return {}
    for opt in item.get("options") or []:
        if not isinstance(opt, dict):
            continue
        if opt.get("value") == value or opt.get("label") == value:
            sets = opt.get("wizard_sets") or {}
            if isinstance(sets, dict):
                return {str(k): str(v) for k, v in sets.items()}
    return {}


def expand_wizard_answers(questions: list[dict],
                            wizard_answers: dict | None) -> dict[str, str]:
    """Gom wizard_answers (theo data_key) + wizard_sets từ option đã chọn."""
    base = dict(wizard_answers or {})
    out: dict[str, str] = {}
    q_by_key: dict[str, dict] = {}
    for item in questions:
        for target in _targets(item):
            q_by_key[target["key"]] = item
    for key, value in base.items():
        if value is None:
            continue
        out[key] = str(value)
        item = q_by_key.get(key)
        if item:
            out.update(_wizard_sets_for_value(item, value))
    return out


def _customer_includes_question(item: dict,
                                virtual_answers: dict[str, str]) -> bool:
    """Customer: đủ câu khách cần điền — chỉ ẩn audience=staff (mark nội bộ)."""
    del virtual_answers  # wizard_sets chỉ dùng lúc import
    return item.get("audience") != "staff"


def _filter_questions(questions: list[dict], export_mode: str,
                      virtual_answers: dict[str, str],
                      *, exclude_wizard: bool = False) -> list[dict]:
    if export_mode == EXPORT_MODE_FULL:
        return [q for q in questions if not q.get("wizard")]
    out: list[dict] = []
    for item in questions:
        if exclude_wizard and item.get("wizard"):
            continue
        if _customer_includes_question(item, virtual_answers):
            out.append(item)
    return out


def _all_questions(forms: list[dict]) -> list[dict]:
    qs: list[dict] = []
    for form in forms:
        qs.extend(form.get("questions") or [])
    return qs


def _wizard_rows(approved: list[dict], export_mode: str) -> list[tuple[str, dict]]:
    if export_mode != EXPORT_MODE_CUSTOMER:
        return []
    rows: list[tuple[str, dict]] = []
    for form in approved:
        for item in form.get("questions") or []:
            if item.get("wizard"):
                rows.append((form["form_id"], item))
    return rows


def _shared_analysis(forms: list[dict]) -> dict:
    """Tìm câu hỏi có data-key dùng chung ≥2 form -> chuyển sang COMMON.

    Câu có BẤT KỲ target key nào shared thì nguyên câu chuyển (một câu một ô —
    không tách nửa vời). Trả {(form_id, question_id): True}.
    """
    key_forms: dict[str, set[str]] = {}
    for form in forms:
        for item in form["questions"]:
            for t in _targets(item):
                key_forms.setdefault(t["key"], set()).add(form["form_id"])
    shared_keys = {k for k, fs in key_forms.items() if len(fs) > 1}
    out: dict[tuple[str, str], bool] = {}
    for form in forms:
        for item in form["questions"]:
            out[(form["form_id"], item["question_id"])] = any(
                t["key"] in shared_keys for t in _targets(item))
    return out


def sheet_display_name(index: int, form: dict) -> str:
    """`01_<tên mẫu>` — ≤31 ký tự, bỏ []:*?/\\, duy nhất nhờ tiền tố số."""
    base = str(form.get("ten_mau") or form["form_id"])
    base = "".join(ch for ch in base if ch not in _SHEET_BAD_CHARS)
    base = " ".join(base.split())
    prefix = "%02d_" % index
    keep = MAX_SHEET_NAME - len(prefix)
    base = base[:keep].strip() or form["form_id"][:keep]
    return prefix + base


def workbook_stem(manifest: dict) -> str:
    """Tên file mặc định `DKKD_<caseId>_<hash8>` (contract tên file E1)."""
    safe = "".join(ch for ch in str(manifest["case_id"])
                   if ch not in _SHEET_BAD_CHARS and ch not in "/\\")
    return "DKKD_%s_%s" % (safe or "case", str(manifest["manifest_hash"])[:8])


def _plan_blocks(questions: list[dict]) -> list[dict]:
    """Gom câu thành khối theo thứ tự file; câu `row_group` gom thành một bảng."""
    grouped: dict[str, list[dict]] = {}
    for item in questions:
        rg = item.get("row_group")
        if rg:
            grouped.setdefault(rg, []).append(item)
    blocks: list[dict] = []
    done: set[str] = set()
    for item in questions:
        rg = item.get("row_group")
        if rg:
            if rg in done:
                continue
            done.add(rg)
            blocks.append({"kind": "table", "group": item["group"],
                           "items": grouped[rg]})
        else:
            blocks.append({"kind": "question", "group": item["group"],
                           "item": item})
    return blocks


# ---------------------------------------------------------------------------
# Ghi một sheet câu hỏi (dùng cho cả Thông_tin_chung lẫn sheet form)
# ---------------------------------------------------------------------------

class _SheetWriter:
    """Ghi vùng body của MỘT sheet + thu map rows.

    `lst_cols`: {question_id: chỉ số cột trên __lists} — câu select nhận
    dropdown trỏ named range `LST_nnnn`; câu mark dùng list inline 'X'.
    `mirror_mode`: sheet đang ghi có phải dạng mirror không (COMMON=False).
    """

    def __init__(self, ws, lst_cols: dict[str, int]):
        self.ws = ws
        self.lst_cols = lst_cols
        self.rows: list[dict] = []

    # ---- ô điền ----
    def _style_fill(self, cell, item: dict) -> None:
        autofill = item.get("autofill") is not None
        cell.fill = _fill(GRAY_HEX if autofill else GOLD_HEX)
        cell.border = _border()
        cell.alignment = _wrap()
        cell.number_format = "@"          # giữ nguyên chuỗi khách gõ
        cell.protection = Protection(locked=autofill)

    def _style_mirror(self, cell, formula: str) -> None:
        cell.value = formula
        cell.fill = _fill(GRAY_HEX)
        cell.border = _border()
        cell.alignment = _wrap()
        cell.number_format = "@"
        cell.protection = Protection(locked=True)

    # ---- dropdown ----
    def _add_list_dv(self, coordinate: str, lst_name: str) -> None:
        dv = DataValidation(type="list", formula1=lst_name, allow_blank=True,
                            showErrorMessage=True)
        dv.errorTitle = "Giá trị không hợp lệ"
        dv.error = "Chỉ chọn một dòng trong danh sách (bấm mũi tên ▾)."
        dv.promptTitle = "Chọn từ danh sách"
        dv.prompt = "Bấm mũi tên ▾ rồi chọn một dòng, không gõ tay."
        self.ws.add_data_validation(dv)
        dv.add(coordinate)

    def _add_mark_dv(self, coordinate: str) -> None:
        dv = DataValidation(type="list", formula1='"%s"' % MARK_VALUE,
                            allow_blank=True, showErrorMessage=True)
        self.ws.add_data_validation(dv)
        dv.add(coordinate)

    # ---- các thành phần bố cục ----
    def _write_section(self, row: int, group: str, color_index: int,
                       span: int) -> None:
        cell = self.ws.cell(row=row, column=COL_LABEL, value=group)
        cell.font = Font(bold=True, size=11, color="1F3864")
        cell.fill = _fill(GROUP_PALETTE[color_index % len(GROUP_PALETTE)])
        cell.alignment = Alignment(vertical="center", horizontal="left")
        cell.border = _border()
        self.ws.merge_cells(start_row=row, start_column=COL_LABEL,
                            end_row=row, end_column=max(span, COL_DATE_NOTE))

    def _note_cells(self, row: int, item: dict) -> None:
        note = item.get("example")
        if note:
            note_text = EXAMPLE_PREFIX + str(note)
        elif item["type"] == "select":
            note_text = SELECT_NOTE
        else:
            note_text = ""
        if note_text:
            cell = self.ws.cell(row=row, column=COL_NOTE)
            _set_text(cell, note_text)
            cell.font = Font(size=10, italic=True, color=NOTE_FONT_HEX)
            cell.alignment = _wrap()
        if item["type"] == "date":
            cell = self.ws.cell(row=row, column=COL_DATE_NOTE, value=DATE_NOTE)
            cell.font = Font(size=10, italic=True, color=NOTE_FONT_HEX)
            cell.alignment = _wrap()

    def _map_entry(self, form_id: str, sheet: str, item: dict, target: dict,
                   row: int, col: int, row_last: int, layout: str,
                   shared: str = "", mirror: str = "",
                   canonical_sheet: str = "", canonical_cell: str = "") -> dict:
        when = target.get("when") or {}
        return {
            "form_id": form_id,
            "sheet": sheet,
            "question_id": item["question_id"],
            "key": target["key"],
            "when": json.dumps(when, ensure_ascii=True, sort_keys=True),
            "transform": target.get("transform") or "",
            "row_group": item.get("row_group") or "",
            "layout": layout,
            "cell": "%s%d" % (get_column_letter(col), row),
            "row_last": row_last,
            "repeatable": "yes" if item.get("repeatable") else "",
            "autofill": item.get("autofill") or "",
            "required": "yes" if item.get("required") else "",
            "version": item.get("version") or "",
            "multi_key": "yes" if isinstance(item["data_key"], list) else "",
            "shared": shared,
            "mirror": mirror,
            "canonical_sheet": canonical_sheet,
            "canonical_cell": canonical_cell,
        }

    # ---- câu đơn ----
    def write_question(self, form_id: str, sheet: str, row: int, item: dict,
                       canonical: dict | None) -> tuple[list[dict], int]:
        """Câu đơn = 1 hàng. `canonical is None` -> ô canonical (VÀNG, điền
        tại đây); ngược lại ô mirror XÁM KHÓA chứa công thức tham chiếu."""
        label = self.ws.cell(row=row, column=COL_LABEL)
        _set_text(label, item["text"])
        label.font = Font(size=11)
        label.alignment = _wrap()
        label.border = _border()

        fill_cell = self.ws.cell(row=row, column=COL_FILL)
        if canonical is not None:
            self._style_mirror(
                fill_cell, "='%s'!%s" % (canonical["sheet"], canonical["cell"]))
            note = self.ws.cell(row=row, column=COL_NOTE)
            _set_text(note, "Đã điền ở sheet %s — ô này tự phản chiếu, không "
                            "điền lại" % canonical["sheet"])
            note.font = Font(size=10, italic=True, color=NOTE_FONT_HEX)
            note.alignment = _wrap()
            entries = [self._map_entry(form_id, sheet, item, t, row, COL_FILL,
                                       row, "mirror", mirror="yes",
                                       canonical_sheet=canonical["sheet"],
                                       canonical_cell=canonical["cell"])
                       for t in _targets(item)]
            return entries, row

        self._style_fill(fill_cell, item)
        if item["type"] == "select":
            self._add_list_dv(fill_cell.coordinate,
                              "LST_%04d" % self.lst_cols[item["question_id"]])
        elif item["type"] == "mark":
            self._add_mark_dv(fill_cell.coordinate)
        self._note_cells(row, item)
        entries = [self._map_entry(form_id, sheet, item, t, row, COL_FILL,
                                   row, "single")
                   for t in _targets(item)]
        return entries, row

    # ---- bảng row_group ----
    def write_table(self, form_id: str, sheet: str, row: int,
                    items: list[dict], color_index: int,
                    canonical_of) -> tuple[list[dict], int]:
        """Bảng = header + REPEAT_ROWS hàng. `canonical_of(item, offset,
        data_row)` trả địa chỉ canonical cho ô mirror, hoặc None nếu ô ĐÓ là
        canonical (khách điền tại đây) — quyết định theo TỪNG CỘT (wave E4:
        bảng có thể nửa mirror nửa canonical, vd M02.ds_nganh chỉ 3/4 cột
        dùng chung với M01–M04)."""
        entries: list[dict] = []
        first_data_row = row + 1
        last_data_row = row + REPEAT_ROWS
        for offset, item in enumerate(items):
            col = COL_FILL + offset
            head = self.ws.cell(row=row, column=col)
            _set_text(head, item["text"])
            head.font = Font(bold=True, size=10, color="1F3864")
            head.fill = _fill(GROUP_PALETTE[color_index % len(GROUP_PALETTE)])
            head.alignment = _wrap()
            head.border = _border()
            mirror = canonical_of is not None and \
                canonical_of(item, offset, first_data_row) is not None
            for data_row in range(first_data_row, last_data_row + 1):
                cell = self.ws.cell(row=data_row, column=col)
                canon = canonical_of(item, offset, data_row) \
                    if mirror else None
                if canon is not None:
                    self._style_mirror(
                        cell, "='%s'!%s" % (canon["sheet"], canon["cell"]))
                else:
                    self._style_fill(cell, item)
            if not mirror:
                if item["type"] == "select":
                    self._add_list_dv(
                        "%s%d:%s%d" % (get_column_letter(col), first_data_row,
                                       get_column_letter(col), last_data_row),
                        "LST_%04d" % self.lst_cols[item["question_id"]])
                elif item["type"] == "mark":
                    self._add_mark_dv(
                        "%s%d:%s%d" % (get_column_letter(col), first_data_row,
                                       get_column_letter(col), last_data_row))
            for target in _targets(item):
                if mirror:
                    # MỖI ô mirror MỘT dòng map — importer tra canonical theo
                    # từng ô (không dò công thức vùng).
                    for data_row in range(first_data_row, last_data_row + 1):
                        canon = canonical_of(item, offset, data_row)
                        entries.append(self._map_entry(
                            form_id, sheet, item, target, data_row, col,
                            last_data_row, "mirror", mirror="yes",
                            canonical_sheet=canon["sheet"],
                            canonical_cell=canon["cell"]))
                else:
                    # MỖI ô điền MỘT dòng map (contract X4 giữ nguyên ở đây)
                    for data_row in range(first_data_row, last_data_row + 1):
                        entries.append(self._map_entry(
                            form_id, sheet, item, target, data_row, col,
                            last_data_row, "table"))
        return entries, last_data_row


# ---------------------------------------------------------------------------
# Các sheet cố định
# ---------------------------------------------------------------------------

def _write_header_block(ws, title: str, meta_line: str) -> None:
    """Hàng 1 tiêu đề, hàng 2 dòng hồ sơ, hàng 3..7 hướng dẫn (gọn hơn X2)."""
    cell = ws.cell(row=TITLE_ROW, column=COL_LABEL, value=title)
    cell.font = Font(bold=True, size=14, color="1F3864")
    cell.alignment = Alignment(vertical="center", horizontal="left")
    ws.merge_cells(start_row=TITLE_ROW, start_column=COL_LABEL,
                   end_row=TITLE_ROW, end_column=COL_DATE_NOTE)
    ws.row_dimensions[TITLE_ROW].height = 24

    if meta_line:
        cell = ws.cell(row=META_ROW, column=COL_LABEL, value=meta_line)
        cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
        cell.alignment = _wrap("center")
        ws.merge_cells(start_row=META_ROW, start_column=COL_LABEL,
                       end_row=META_ROW, end_column=COL_DATE_NOTE)

    for offset, line in enumerate(GUIDE_LINES):
        cell = ws.cell(row=GUIDE_FIRST_ROW + offset, column=COL_LABEL,
                       value=line)
        cell.font = Font(size=10, color=GUIDE_FONT_HEX)
        cell.alignment = _wrap("center")
        ws.merge_cells(start_row=GUIDE_FIRST_ROW + offset, start_column=COL_LABEL,
                       end_row=GUIDE_FIRST_ROW + offset, end_column=COL_DATE_NOTE)

    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width


def _protect(ws, freeze_at: str | None = None) -> None:
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    if freeze_at:
        ws.freeze_panes = freeze_at
    ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# API chính
# ---------------------------------------------------------------------------

def _setup_print(ws) -> None:
    """[fitToWidth 2026-09-10 — owner chốt] In/PDF đủ bề ngang 1 trang.

    Sheet nghiệp vụ rộng hơn khổ A4 dọc từng tràn cột phải (note ví dụ) sang
    trang riêng khi in/PDF (WARN page_overflow của gate
    `tools.excel_case_visual`). fitToWidth=1 + fitToHeight=0: Excel/LibreOffice
    tự co tỉ lệ để MỌI cột nằm trong MỘT trang ngang, chiều dọc tự nhiên chia
    trang. Gotcha openpyxl: `fitToWidth` CHỈ có hiệu lực khi
    `sheet_properties.pageSetUpPr.fitToPage = True` — thiếu là thuộc tính được
    ghi nhưng trình đọc in bỏ qua. Áp cho sheet công khai; `__map`/`__lists`
    veryHidden không in nên không cần.
    """
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0  # 0 = không giới hạn số trang dọc
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.5


def _write_customer_sheet_header(ws, title: str) -> None:
    """Phiếu_khách: hàng 1 tiêu đề + hàng 2–6 hướng dẫn ngắn."""
    cell = ws.cell(row=1, column=COL_LABEL, value=title)
    cell.font = Font(bold=True, size=14, color="1F3864")
    cell.alignment = Alignment(vertical="center", horizontal="left")
    ws.merge_cells(start_row=1, start_column=COL_LABEL,
                   end_row=1, end_column=COL_DATE_NOTE)
    ws.row_dimensions[1].height = 24
    row = 2
    for line in CUSTOMER_GUIDE_LINES:
        gcell = ws.cell(row=row, column=COL_LABEL, value="• " + line)
        gcell.font = Font(size=10, italic=True, color=GUIDE_FONT_HEX)
        gcell.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=COL_LABEL,
                       end_row=row, end_column=COL_DATE_NOTE)
        row += 1
    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width


def _is_ten_nganh_question(item: dict) -> bool:
    for target in _targets(item):
        key = target["key"]
        if key.endswith(".ten_nganh") or key == "ten_nganh":
            return True
    return False


def _customer_normalize_question(item: dict) -> dict | None:
    """Customer: ẩn cột tên ngành; mã VSIC do khách gõ (không khóa autofill)."""
    if _is_ten_nganh_question(item):
        return None
    out = dict(item)
    for target in _targets(out):
        key = target["key"]
        if key.endswith(".ma_nganh") or key == "ma_nganh":
            out.pop("autofill", None)
            out["text"] = "Mã ngành VSIC cấp 4?"
            out["example"] = out.get("example") or "6201"
            out["required"] = True
            break
    return out


def _customer_form_questions(approved: list[dict]) -> list[dict]:
    """Form đã bỏ wizard + audience staff — giữ optional/conditional/when."""
    out: list[dict] = []
    for form in approved:
        fq: list[dict] = []
        for q in form.get("questions") or []:
            if q.get("audience") == "staff" or q.get("wizard"):
                continue
            norm = _customer_normalize_question(q)
            if norm:
                fq.append(norm)
        out.append({**form, "questions": fq})
    return out


def _write_customer_workbook(manifest: dict, out_path: "str | Path",
                             meta: dict, approved: list[dict]) -> Path:
    """Customer export: MỘT sheet Phiếu_khách + __map/__lists (veryHidden)."""
    form_iter = _customer_form_questions(approved)
    wizard_rows = _wizard_rows(approved, EXPORT_MODE_CUSTOMER)
    shared_q = _shared_analysis(form_iter)

    lst_cols: dict[str, int] = {}
    next_col = 1
    for form in form_iter:
        for item in form["questions"]:
            if item["type"] == "select":
                lst_cols[item["question_id"]] = next_col
                next_col += 1
    for _, item in wizard_rows:
        if item["type"] == "select":
            lst_cols[item["question_id"]] = next_col
            next_col += 1

    wb = Workbook()
    ws = wb.active
    ws.title = CUSTOMER_SHEET
    _write_customer_sheet_header(ws, str(manifest.get("case_title") or ""))
    writer = _SheetWriter(ws, lst_cols)
    map_rows: list[dict] = []
    row = CUSTOMER_BODY_ROW
    color_index = 0
    seen_qids: set[str] = set()
    ordered: list[tuple[str, dict]] = []

    for owner_fid, item in wizard_rows:
        ordered.append((owner_fid, item))
        seen_qids.add(item["question_id"])

    for form in form_iter:
        for item in form["questions"]:
            if not is_selector_question(item):
                continue
            if item["question_id"] in seen_qids:
                continue
            ordered.append((form["form_id"], item))
            seen_qids.add(item["question_id"])

    for form in form_iter:
        for item in form["questions"]:
            if not shared_q.get((form["form_id"], item["question_id"])) or \
                    is_selector_question(item):
                continue
            if item["question_id"] in seen_qids:
                continue
            ordered.append((form["form_id"], item))
            seen_qids.add(item["question_id"])

    for form in form_iter:
        for item in form["questions"]:
            qid = item["question_id"]
            if qid in seen_qids or is_selector_question(item):
                continue
            ordered.append((form["form_id"], item))
            seen_qids.add(qid)

    current_group = None
    for block in _plan_blocks([q for _, q in ordered]):
        items = block["items"] if block["kind"] == "table" else [block["item"]]
        fid = next(f for f, q in ordered if q["question_id"] == items[0]["question_id"])
        span = COL_DATE_NOTE if block["kind"] == "question" \
            else COL_FILL + len(items) - 1
        if block["group"] != current_group:
            current_group = block["group"]
            writer._write_section(row, block["group"], color_index, span)
            color_index += 1
            row += 1
        if block["kind"] == "question":
            entries, row_last = writer.write_question(
                fid, CUSTOMER_SHEET, row, block["item"], None)
        else:
            entries, row_last = writer.write_table(
                fid, CUSTOMER_SHEET, row, items, color_index - 1, None)
        map_rows.extend(entries)
        row = row_last + 2

    _protect(ws, freeze_at="A%d" % CUSTOMER_BODY_ROW)

    if lst_cols:
        _write_lists_sheet(wb.create_sheet(LISTS_SHEET), wb, form_iter,
                           lst_cols, wizard_rows)
    _write_map_sheet(wb.create_sheet(MAP_SHEET), manifest, meta, map_rows,
                     export_mode=EXPORT_MODE_CUSTOMER)
    _setup_print(ws)

    path = Path(out_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def write_case_workbook(manifest: dict, out_path: "str | Path",
                        meta: dict | None = None,
                        include_authorization: bool | None = None,
                        export_mode: str = EXPORT_MODE_FULL,
                        wizard_answers: dict | None = None) -> Path:
    """Ghi workbook .xlsx cho TOÀN BỘ case và trả `Path` file đã ghi.

    `manifest`: dict case-level (wave E0). `meta`: tùy chọn
    `{"today": "dd/mm/yyyy", "exported_at": "dd/mm/yyyy HH:MM"}` — in lên
    dòng hồ sơ và metadata __map (nên truyền để file tái lập được).

    `export_mode`: ``"full"`` (mặc định, nội bộ đầy đủ) hoặc ``"customer"``
    (một sheet ``Phiếu_khách`` đủ câu khách điền, không sheet/form dư).

    `wizard_answers`: dict tùy chọn {data_key: value} — dùng khi cần lọc nhánh
    lúc xuất (UI có thể truyền sau dialog wizard).

    Raises `ExcelCaseExportError` (có `code`) khi manifest sai khung hoặc case
    chưa có form approved nào (CASE_NOT_READY — gate E4 chặn phát hành).
    """
    manifest = _validate_manifest(manifest)
    meta = _validate_meta(meta)
    if export_mode not in _EXPORT_MODES:
        raise ExcelCaseExportError(
            "BAD_EXPORT_MODE",
            "export_mode phải là %r hoặc %r" % _EXPORT_MODES)
    if include_authorization is None:
        include_authorization = export_mode == EXPORT_MODE_FULL
    approved = [f for f in manifest["forms"] if is_review_approved(
        f.get("content_review"))]
    customer = export_mode == EXPORT_MODE_CUSTOMER
    if customer:
        return _write_customer_workbook(manifest, out_path, meta, approved)
    form_iter = [{**f, "questions": [q for q in f["questions"]
                                     if not q.get("wizard")]}
                 for f in approved]
    shared_q = _shared_analysis(form_iter)

    # ---- dropdown registry: qid select -> cột trên __lists -----------------
    lst_cols: dict[str, int] = {}
    next_col = 1
    q_source = form_iter
    for form in q_source:
        for item in form["questions"]:
            if item["type"] == "select":
                lst_cols[item["question_id"]] = next_col
                next_col += 1

    # ---- câu SELECTOR (oneOf / form tùy chọn) — render 1 lần ở COMMON ------
    selector_rows: list[tuple[str, dict]] = [
        (f["form_id"], item) for f in form_iter
        for item in f["questions"] if is_selector_question(item)]

    wb = Workbook()
    ws_guide = wb.active
    ws_guide.title = GUIDE_SHEET
    ws_common = wb.create_sheet(COMMON_SHEET)

    hash8 = str(manifest["manifest_hash"])[:8]
    meta_line = "Hồ sơ: %s (%s) — Mã phiếu: %s — Ngày lập: %s" % (
        manifest["case_title"], manifest["case_id"], hash8,
        meta.get("today") or "")

    today = meta.get("today") or ""
    map_rows: list[dict] = []

    # ---- Thông_tin_chung: câu shared hỏi MỘT lần (canonical) ---------------
    # canonical_of[key] = {"sheet", "cell"} (câu đơn) | {"sheet", "cells": [...]}
    canonical_of: dict[str, dict] = {}
    writer = _SheetWriter(ws_common, lst_cols)
    _write_header_block(
        ws_common, "Thông tin dùng chung cho cả hồ sơ",
        meta_line + (" — Các ô dưới đây dùng chung cho nhiều mẫu, chỉ điền MỘT lần"
                     if any(shared_q.values()) else ""))
    row = COMMON_BODY_ROW
    color_index = 0

    # ---- (E4) câu SELECTOR ở đầu Thông_tin_chung ---------------------------
    if selector_rows:
        current_group = None
        for owner_fid, item in selector_rows:
            if item["group"] != current_group:
                current_group = item["group"]
                writer._write_section(row, current_group, color_index,
                                      COL_DATE_NOTE)
                color_index += 1
                row += 1
            entries, row = writer.write_question(
                owner_fid, COMMON_SHEET, row, item, None)
            map_rows.extend(entries)
            row += 1

    shared_questions: list[tuple[str, dict]] = []
    owner_of: dict[str, str] = {}          # question_id -> form chủ canonical
    owned_keys: set[str] = set()
    for form in form_iter:
        for item in form["questions"]:
            if not shared_q.get((form["form_id"], item["question_id"])) or \
                    is_selector_question(item):
                continue
            # CHỦ canonical = câu ĐẦU TIÊN (theo thứ tự manifest) tuyên bố
            # key shared; các câu sau (kể cả form khác) là mirror trỏ về ô
            # của chủ — không sinh ô canonical thứ hai (cấm last-write-wins).
            keys = [t["key"] for t in _targets(item)]
            if any(k not in owned_keys for k in keys):
                shared_questions.append((form["form_id"], item))
                owner_of[item["question_id"]] = form["form_id"]
                owned_keys.update(keys)
    if shared_questions:
        blocks = _plan_blocks([q for _, q in shared_questions])
        common_entries: list[dict] = []
        for block in blocks:
            items = block["items"] if block["kind"] == "table" \
                else [block["item"]]
            span = COL_DATE_NOTE if block["kind"] == "question" \
                else COL_FILL + len(items) - 1
            writer._write_section(row, block["group"], color_index, span)
            color_index += 1
            row += 1
            if block["kind"] == "question":
                item = block["item"]
                entries, row_last = writer.write_question(
                    owner_of[item["question_id"]], COMMON_SHEET, row, item,
                    None)
                common_entries.extend(entries)
                for t in _targets(item):
                    canonical_of.setdefault(t["key"], {
                        "sheet": COMMON_SHEET,
                        "cell": entries[0]["cell"]})
                row = row_last + 1
            else:
                entries, row_last = writer.write_table(
                    owner_of[items[0]["question_id"]], COMMON_SHEET, row,
                    items, color_index - 1, None)
                common_entries.extend(entries)
                # ghi nhận canonical từng ô của bảng theo key (theo thứ tự
                # hàng sheet — map rows đã sinh theo đúng thứ tự đó)
                by_key: dict[str, list[str]] = {}
                for entry in entries:
                    by_key.setdefault(entry["key"], []).append(entry["cell"])
                for item in items:
                    for t in _targets(item):
                        cells = by_key.get(t["key"]) or []
                        canonical_of.setdefault(t["key"], {
                            "sheet": COMMON_SHEET,
                            "cell": cells[0] if cells else "",
                            "cells": cells})
                row = row_last + 1
            row += 1
        map_rows.extend(common_entries)
    else:
        if not selector_rows:
            note = ws_common.cell(
                row=row, column=COL_LABEL,
                value="Case này không có trường dùng chung nào giữa các mẫu "
                      "— điền trực tiếp ở sheet các mẫu bên dưới.")
            note.font = Font(size=11, italic=True, color=META_FONT_HEX)
            note.alignment = _wrap()
    _protect(ws_common, freeze_at="A%d" % COMMON_BODY_ROW)

    # ---- Sheet từng form (full) ---------------------------------------------
    for index, form in enumerate(form_iter, start=1):
        sheet = sheet_display_name(index, form)
        ws = wb.create_sheet(sheet)
        _write_header_block(ws, str(form.get("title") or form["ten_mau"]),
                            meta_line)
        writer = _SheetWriter(ws, lst_cols)
        blocks = _plan_blocks([q for q in form["questions"]
                               if not is_selector_question(q)])
        row = FIRST_BODY_ROW
        current_group = None
        color_index = 0
        for block in blocks:
            items = block["items"] if block["kind"] == "table" \
                else [block["item"]]
            shared = shared_q.get((form["form_id"], items[0]["question_id"]),
                                  False)
            span = COL_DATE_NOTE if block["kind"] == "question" \
                else COL_FILL + len(items) - 1
            if block["group"] != current_group:
                current_group = block["group"]
                writer._write_section(row, current_group, color_index, span)
                color_index += 1
                row += 1
            if block["kind"] == "question":
                item = block["item"]
                canon = None
                if shared:
                    target0 = _targets(item)[0]
                    c = canonical_of.get(target0["key"])
                    if not c or not c.get("cell"):
                        raise ExcelCaseExportError(
                            "SHARED_MISSING_CANONICAL",
                            "%s: câu %s đánh dấu shared nhưng không có ô "
                            "canonical ở %s" % (form["form_id"],
                                                item["question_id"],
                                                COMMON_SHEET))
                    canon = {"sheet": c["sheet"], "cell": c["cell"]}
                entries, row_last = writer.write_question(
                    form["form_id"], sheet, row, item, canon)
            else:
                def canonical_of_cell(item, offset, data_row):
                    if not shared_q.get((form["form_id"],
                                         item["question_id"]), False):
                        return None
                    key0 = _targets(item)[0]["key"]
                    c = canonical_of.get(key0)
                    if not c or not (c.get("cells") or c.get("cell")):
                        raise ExcelCaseExportError(
                            "SHARED_MISSING_CANONICAL",
                            "%s: câu %s đánh dấu shared nhưng không có ô "
                            "canonical ở %s" % (form["form_id"],
                                                item["question_id"],
                                                COMMON_SHEET))
                    cells = c.get("cells") or []
                    cell_addr = cells[data_row - (row + 1)] \
                        if cells else c["cell"]
                    return {"sheet": c["sheet"], "cell": cell_addr}

                entries, row_last = writer.write_table(
                    form["form_id"], sheet, row, items, color_index - 1,
                    canonical_of_cell)
            row = row_last + 1
            map_rows.extend(entries)
            row += 1
        _protect(ws, freeze_at="A%d" % FIRST_BODY_ROW)

    # ---- Giấy_tờ_cần_gửi (fail-safe: chưa DECIDED -> watermark) ------------
    _write_docs_sheet(wb.create_sheet(DOCS_SHEET), manifest)

    # ---- __lists + named ranges --------------------------------------------
    if lst_cols:
        _write_lists_sheet(wb.create_sheet(LISTS_SHEET), wb,
                           q_source, lst_cols, None)

    # ---- __map --------------------------------------------------------------
    _write_map_sheet(wb.create_sheet(MAP_SHEET), manifest, meta, map_rows,
                     export_mode=export_mode)

    # ---- Hướng_dẫn (nội dung đầy đủ: phiên bản + trạng thái + lưu ý) -------
    _write_guide_sheet(ws_guide, manifest, meta, hash8, form_iter,
                       export_mode=export_mode)

    # ---- AUTH_* (wave I5 — ủy quyền dịch vụ; không nằm __map) ---------------
    if include_authorization:
        try:
            from tools.excel_authorization_sheets import append_auth_sheets  # noqa: WPS433

            append_auth_sheets(wb, str(manifest["case_id"]), meta)
        except Exception:  # noqa: BLE001 — thiếu kho auth không chặn xuất case
            pass

    # [fitToWidth 2026-09-10] mọi sheet công khai in/PDF đủ 1 trang ngang
    for ws in wb.worksheets:
        if ws.title not in (MAP_SHEET, LISTS_SHEET):
            _setup_print(ws)

    path = Path(out_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


DOCS_SOURCE_LINE = ("Nguồn: Nghị định 168/2025/NĐ-CP, TT 121/2026/TT-BTC — "
                    "watermark pháp lý")

DOCS_DO_NOT_EDIT = ("Sheet này chỉ là CHECKLIST để bạn đối chiếu — không "
                    "phần nào của sheet này được app đọc lại khi nạp phiếu.")


def _write_docs_sheet(ws, manifest: dict) -> None:
    """Sheet giấy tờ — wave E4 (owner chốt 2026-09-10): in DANH MỤC THẬT từ
    manifest `giay_to_kem` thành checklist có ô tick X, cuối sheet in
    `co_so_phap_ly` + dòng phiên bản nguồn pháp lý. Không còn khối
    "CHỜ DUYỆT" (ho_so_bao_gom đã DECIDED — docs/p4_excel_review_gate.md
    được gỡ gate bởi owner 2026-09-10)."""
    big = ws.cell(row=1, column=1, value="GIẤY TỜ CẦN CHUẨN BỊ NỘP KÈM")
    big.font = Font(bold=True, size=14, color="1F3864")
    big.alignment = Alignment(vertical="center", horizontal="left")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    ws.row_dimensions[1].height = 26

    cell = ws.cell(row=2, column=1, value=(
        "Đánh dấu X vào ô thứ nhất cho từng giấy tờ BẠN ĐÃ CÓ SẴN. "
        + DOCS_DO_NOT_EDIT))
    cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
    cell.alignment = _wrap()
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)

    row = 4
    head = ws.cell(row=row, column=1, value="Đã có?")
    head.font = Font(bold=True, size=11, color="1F3864")
    head.fill = _fill(GRAY_HEX)
    head.border = _border()
    head.alignment = _wrap()
    label = ws.cell(row=row, column=2, value="Giấy tờ nộp kèm hồ sơ")
    label.font = Font(bold=True, size=11, color="1F3864")
    label.fill = _fill(GRAY_HEX)
    label.border = _border()
    label.alignment = _wrap()
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
    row += 1

    items = manifest.get("giay_to_kem") or []
    for item in items:
        tick = ws.cell(row=row, column=1)
        tick.fill = _fill(GOLD_HEX)
        tick.border = _border()
        tick.alignment = Alignment(horizontal="center", vertical="center")
        tick.number_format = "@"
        tick.protection = Protection(locked=False)
        dv = DataValidation(type="list", formula1='"%s"' % MARK_VALUE,
                            allow_blank=True, showErrorMessage=True)
        ws.add_data_validation(dv)
        dv.add(tick.coordinate)
        text = ws.cell(row=row, column=2)
        _set_text(text, str(item))
        text.font = Font(size=11)
        text.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=2, end_row=row,
                       end_column=6)
        row += 1
    if not items:
        cell = ws.cell(row=row, column=1,
                       value="(Hồ sơ này không khai danh mục giấy tờ nộp "
                             "kèm riêng — xem Lưu ý ở sheet Hướng_dẫn.)")
        cell.font = Font(size=11, italic=True, color=META_FONT_HEX)
        cell.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                       end_column=6)
        row += 2

    row += 1
    cell = ws.cell(row=row, column=1, value="Cơ sở pháp lý (bản hiện hành):")
    cell.font = Font(bold=True, size=11, color="1F3864")
    row += 1
    for ref in manifest.get("co_so_phap_ly") or []:
        cell = ws.cell(row=row, column=1)
        _set_text(cell, "• %s" % ref)
        cell.font = Font(size=10, color=GUIDE_FONT_HEX)
        cell.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                       end_column=6)
        row += 1
    if not (manifest.get("co_so_phap_ly") or []):
        cell = ws.cell(row=row, column=1,
                       value="(manifest không ghi cơ sở pháp lý)")
        cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
        row += 1
    row += 1
    cell = ws.cell(row=row, column=1, value=DOCS_SOURCE_LINE)
    cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
    cell.alignment = _wrap()
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width
    _protect(ws)


def _write_lists_sheet(ws, wb, approved: list[dict],
                       lst_cols: dict[str, int],
                       wizard_rows: list[tuple[str, dict]] | None = None) -> None:
    """__lists: mỗi câu select một cột (header = question_id, giá trị options).

    Dropdown tham chiếu qua named range `LST_nnnn` (không nhúng danh sách vào
    vùng khách điền — PLAN §2.1). Sheet veryHidden + khóa.
    """
    qid_of_col = {v: k for k, v in lst_cols.items()}
    wizard_qids = {item["question_id"] for _, item in (wizard_rows or [])}
    for col in sorted(qid_of_col):
        qid = qid_of_col[col]
        ws.cell(row=1, column=col, value=qid).font = Font(bold=True, size=10)
        options: list[str] = []
        if qid in wizard_qids:
            for _, item in wizard_rows or []:
                if item["question_id"] == qid:
                    options = _dropdown_labels(item)
                    break
        else:
            for form in approved:
                for item in form["questions"]:
                    if item["question_id"] == qid and item["type"] == "select":
                        options = _dropdown_labels(item)
                        break
                if options:
                    break
        for offset, label in enumerate(options):
            ws.cell(row=2 + offset, column=col, value=label)
        letter = get_column_letter(col)
        ws.column_dimensions[letter].width = 30
        # named range dùng cho DataValidation — Excel/LibreOffice tra theo tên
        wb.defined_names.add(DefinedName(
            "LST_%04d" % col,
            attr_text="'%s'!$%s$2:$%s$%d" % (LISTS_SHEET, letter, letter,
                                             1 + len(options))))
    ws.sheet_state = "veryHidden"
    ws.protection.sheet = True


def _dropdown_labels(item: dict) -> list[str]:
    if item["type"] == "mark":
        return [MARK_VALUE]
    labels = []
    for opt in item.get("options") or []:
        label = str(opt.get("label", "")).strip()
        if label:
            labels.append(label)
    if not labels:
        raise ExcelCaseExportError(
            "NO_OPTIONS", "%s: select phải có options" % item["question_id"])
    return labels


def _write_guide_sheet(ws, manifest: dict, meta: dict, hash8: str,
                       approved: list[dict],
                       export_mode: str = EXPORT_MODE_FULL) -> None:
    customer = export_mode == EXPORT_MODE_CUSTOMER
    row = 1
    cell = ws.cell(row=row, column=1, value=manifest["case_title"])
    cell.font = Font(bold=True, size=16, color="1F3864")
    row += 1
    cell = ws.cell(row=row, column=1,
                   value="Mã phiếu: %s — case: %s — schema: v%s — xuất ngày: %s"
                         % (hash8, manifest["case_id"],
                            manifest.get("schema_version", 1),
                            meta.get("today") or ""))
    cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
    row += 2
    guide_lines = CUSTOMER_GUIDE_LINES if customer else GUIDE_LINES
    for line in guide_lines:
        cell = ws.cell(row=row, column=1, value="• " + line)
        cell.font = Font(size=11, color=GUIDE_FONT_HEX)
        cell.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                       end_column=6)
        row += 1
    if customer:
        row += 1
        cell = ws.cell(row=row, column=1,
                       value="Phiếu rút gọn cho khách — điền sheet %s và "
                             "%s." % (CUSTOMER_SHEET, COMMON_SHEET))
        cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
        cell.alignment = _wrap()
        ws.merge_cells(start_row=row, start_column=1, end_row=row,
                       end_column=6)
        row += 1
    else:
        row += 1
        cell = ws.cell(row=row, column=1, value="Các mẫu trong phiếu này:")
        cell.font = Font(bold=True, size=12, color="1F3864")
        row += 1
        for index, form in enumerate(manifest.get("forms") or [], start=1):
            status = {
                REVIEW_APPROVED: "đã duyệt nội dung",
                REVIEW_DELEGATED: "nội dung sinh theo ủy quyền owner "
                                  "(owner_delegated_2026-09-10)",
                REVIEW_PENDING: "CHỜ duyệt nội dung (không có trong phiếu)",
            }.get(form.get("content_review"), form.get("content_review"))
            name = sheet_display_name(index, form) \
                if form.get("content_review") == "approved" \
                else str(form.get("form_id"))
            cell = ws.cell(row=row, column=1)
            _set_text(cell, "%s — %s (%s)" % (name, form.get("ghi_chu") or
                                              form.get("ten_mau") or "", status))
            cell.font = Font(size=11)
            cell.alignment = _wrap()
            ws.merge_cells(start_row=row, start_column=1, end_row=row,
                           end_column=6)
            row += 1
    row += 1
    notes = manifest.get("luu_y") or []
    if notes:
        cell = ws.cell(row=row, column=1, value="Lưu ý về case này:")
        cell.font = Font(bold=True, size=12, color="1F3864")
        row += 1
        for note in notes:
            cell = ws.cell(row=row, column=1)
            _set_text(cell, "• %s" % note)
            cell.font = Font(size=10, color=GUIDE_FONT_HEX)
            cell.alignment = _wrap()
            ws.merge_cells(start_row=row, start_column=1, end_row=row,
                           end_column=6)
            row += 1
    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width
    _protect(ws)


def _write_map_sheet(ws, manifest: dict, meta: dict, rows: list[dict],
                     export_mode: str = EXPORT_MODE_FULL) -> None:
    """__map veryHidden: metadata `key=value` + bảng map + CHECKSUM sha256.

    Checksum tính trên payload canonical gồm metadata (trừ chính checksum) và
    TOÀN BỘ map rows — importer tính lại và từ chối mọi lệch (CHECKSUM).
    """
    ws.sheet_state = "veryHidden"
    meta_rows = [
        ("contract", CONTRACT),
        ("map_version", str(CASE_MAP_VERSION)),
        ("schema_version", str(manifest.get("schema_version", 1))),
        ("manifest_id", str(manifest.get("manifest_id") or "")),
        ("manifest_version", str(manifest.get("manifest_version") or "")),
        ("manifest_hash", str(manifest["manifest_hash"])),
        ("case_id", str(manifest["case_id"])),
        ("case_title", str(manifest["case_title"])),
        ("export_mode", export_mode),
        ("forms", ",".join(f["form_id"] for f in manifest["forms"]
                           if f["content_review"] == "approved")),
        ("today", str(meta.get("today") or "")),
        ("exported_at", str(meta.get("exported_at") or "")),
    ]
    checksum = hashlib.sha256(_canonical_json({
        "meta": dict(meta_rows), "rows": rows,
    }).encode("utf-8")).hexdigest()
    meta_rows.append(("checksum", checksum))

    ws.cell(row=1, column=1, value=MAP_MARKER)
    for index, (mkey, mval) in enumerate(meta_rows):
        ws.cell(row=1, column=2 + index, value="%s=%s" % (mkey, mval))

    for offset, name in enumerate(MAP_COLUMNS):
        cell = ws.cell(row=MAP_HEADER_ROW, column=1 + offset, value=name)
        cell.font = Font(bold=True, size=10)
        cell.fill = _fill(GRAY_HEX)
        cell.border = _border()
        cell.alignment = _wrap()
    for rindex, entry in enumerate(rows):
        for offset, name in enumerate(MAP_COLUMNS):
            ws.cell(row=MAP_FIRST_ROW + rindex, column=1 + offset,
                    value=entry[name])
    widths = {"A": 12, "B": 22, "C": 24, "D": 30, "E": 30, "F": 11,
              "G": 14, "H": 9, "I": 9, "J": 9, "K": 11, "L": 10, "M": 10,
              "N": 9, "O": 10, "P": 8, "Q": 8, "R": 18, "S": 9}
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width
    ws.protection.sheet = True
