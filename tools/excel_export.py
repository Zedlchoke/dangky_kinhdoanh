# -*- coding: utf-8 -*-
"""Xuất phiếu thu thập thông tin .xlsx cho khách — wave X2 (PLAN.md mục 4.4).

Đọc questionnaire schema v1 (wave X1, `tools/questionnaire/schema.py`, artifact
`app/data/questionnaire/<doc_id>.json`) và ghi MỘT file .xlsx bằng openpyxl
thuần (không pandas, không dependency hệ thống — an toàn cho đóng gói Windows
R6). Đối tác đọc lại file là wave X3 (`tools/excel_import.py`) và bridge X5 —
cả hai đang code ĐỐI XỨNG theo contract chốt: hàm `write_questionnaire()`,
sheet `Phieu` + sheet ẩn `MAP_SHEET`, hằng `MAP_SHEET` export ra dùng chung
(`from tools.excel_export import MAP_SHEET, write_questionnaire`).

Bố cục sheet `Phieu` (hàng/cột cố định, X3 không phải dò):
  hàng 1      tiêu đề dịch vụ = `questionnaire["title"]` (merge A:D)
  hàng 2      dòng hồ sơ từ `meta` ("Hồ sơ: <case_id> — Ngày lập phiếu: <today>");
              khi không có `meta` hàng này để trống nhưng VẪN được giữ chỗ
  hàng 3..7   5 dòng hướng dẫn (quy ước màu, không sửa ô khác, dropdown,
              ngày dd/mm/yyyy, ví dụ điền mờ)
  hàng 8      trống (đệm)
  hàng 9+     nội dung: mỗi `group` = một hàng tiêu đề nhóm (màu riêng); mỗi
              câu = 1 hàng (A nhãn câu, B ô điền, C ví dụ mờ/ghi chú, D ghi
              chú định dạng cho câu date); các câu cùng `row_group` = MỘT
              bảng nhỏ (hàng đầu là header = text các câu, theo sau là
              `REPEAT_ROWS` hàng trống để khách điền từng dòng)

Quy ước màu (PLAN 4.3, yêu cầu cứng):
  - NỀN VÀNG  `GOLD_HEX`  = khách điền  -> `Protection(locked=False)`
  - NỀN XÁM   `GRAY_HEX`  = app tự làm (`autofill`, ví dụ tra VSIC) -> khóa
  - tiêu đề nhóm = màu pastel luân phiên từ `GROUP_PALETTE` (không trùng
    vàng/xám), chữ đậm
Khóa bảo vệ: `ws.protection.sheet = True`, MỌI ô ngoài vùng điền giữ
`locked=True` (mặc định). Không đặt mật khẩu: khách vẫn đọc được toàn bộ và
nếu khung bị sửa thì X3 bắt lỗi lúc nạp (fail-loud) — nhờ vậy failure mode
"khách mất mật khẩu" không tồn tại. Cho phép chỉnh độ rộng cột/hàng
(`formatColumns/formatRows` mở) để khách đọc chữ dài dễ hơn, không đụng dữ liệu.

Dropdown chọn-là-chọn: `DataValidation(type="list")` từ `options[].label` với
`allow_blank=True`; `showDropDown` để mặc định (False) vì attribute OOXML
nghịch dấu — đặt True sẽ LÀM MẤT mũi tên trong Excel. Ô `mark` luôn chỉ nhận
"X" (`MARK_VALUE`). Nhãn chứa dấu phẩy/ngoặc kép hoặc danh sách vượt 255 ký tự
= fail-loud (Excel list separator không cho phép).

Định dạng ô điền: toàn bộ `number_format="@"` (Text) để Excel KHÔNG tự đổi
"05/12/1985" thành serial ngày, không mất số 0 đầu của CCCD/SĐT, và round-trip
(X4) giữ 100% chuỗi khách gõ. Chuẩn hóa số/ngày là việc của app lúc nạp
(PLAN E2 — bỏ dấu chấm nghìn, tách ngày/tháng/năm).

Sheet `MAP_SHEET` (ẩn) = bảng metadata máy đọc cho X3, KHÔNG dò lại layout:
  A1 = `MAP_MARKER`                    B1 = JSON thông tin file (doc_id,
      version, sheet, hàng nội dung đầu…)
  hàng 3 = header `MAP_COLUMNS`; hàng 4+ = MỘT dòng cho MỖI target
  `data_key` (câu nhiều key / nhiều `when` → nhiều dòng): question_id, nhóm,
  type, key, `when_json` (JSON string), transform, row_group, layout
  ("single"/"table"), ô điền đầu (vd "B12"), hàng đầu/cuối vùng điền,
  repeatable, autofill, required, version, multi_key.
  Lưu ý khi đọc: ô map không có giá trị đọc lại là None (openpyxl bỏ chuỗi
  rỗng khi ghi) — X3 chuẩn hóa None -> "" cho cột chữ.

KHÔNG sinh bảng "Giấy tờ bạn cần chuẩn bị" ở v1: `ho_so_bao_gom` của cụm đầu
chưa DECIDED (gap đã ghi `docs/p4_excel_review_gate.md` mục 4) — chờ owner
duyệt nội dung rồi mới in vào phiếu.

Chạy suite:  python3 -X utf8 -m tools.test_excel_export   (exit 0 = PASS)
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.protection import Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from tools.questionnaire.schema import TYPES as QUESTION_TYPES

__all__ = [
    "ExcelExportError", "MAP_COLUMNS", "MAP_MARKER", "MAP_SHEET",
    "MAP_VERSION", "MARK_VALUE", "REPEAT_ROWS", "SHEET_NAME", "write_questionnaire",
]

# ---------------------------------------------------------------------------
# Contract cố định (lane x3-import / bridge X5 đọc; KHÔNG đổi nếu chưa đồng bộ)
# ---------------------------------------------------------------------------

SHEET_NAME = "Phieu"          # sheet khách nhìn thấy
MAP_SHEET = "___map"          # sheet ẩn, metadata cho X3
MAP_MARKER = "__EXCEL_QUESTIONNAIRE_MAP_V1__"
MAP_VERSION = 1

TITLE_ROW = 1                 # tiêu đề dịch vụ
META_ROW = 2                  # dòng "Hồ sơ: … — Ngày lập phiếu: …" (có thể trống)
GUIDE_FIRST_ROW = 3           # 5 dòng hướng dẫn: hàng 3..7
GUIDE_ROWS = 5
FIRST_BODY_ROW = 9            # hàng nội dung đầu tiên (hàng 8 là đệm)

COL_LABEL = 1                 # A: text câu hỏi / nhãn cột bảng
COL_FILL = 2                  # B: ô điền đầu tiên
COL_NOTE = 3                  # C: ví dụ mờ hoặc ghi chú
COL_DATE_NOTE = 4             # D: ghi chú định dạng cho câu date
MAX_FILL_COLUMN = 6           # cột F — cột điền xa nhất (không cuộn ngang)

REPEAT_ROWS = 10              # số hàng trống của bảng row_group
MARK_VALUE = "X"              # quy ước ô mark (contract X2)

GOLD_HEX = "FFF2CC"           # Ô VÀNG = khách điền
GRAY_HEX = "D9D9D9"           # Ô XÁM = app tự làm
NOTE_FONT_HEX = "808080"      # chữ mờ cho ví dụ/ghi chú
BORDER_HEX = "9C9C9C"         # viền rõ quanh ô
META_FONT_HEX = "595959"
GUIDE_FONT_HEX = "404040"
# Màu pastel cho tiêu đề nhóm — không trùng GOLD/GRAY, luân phiên theo thứ tự
# nhóm xuất hiện. PLI_M72 có 4 nhóm -> mỗi nhóm một màu.
GROUP_PALETTE = ("DDEBF7", "E2EFDA", "FCE4D6", "E4DFEC", "D0E0E3")

# Cột A..D là vùng đọc thường xuyên (nhãn + ô điền + ví dụ + ghi chú): tổng
# ~118 đơn vị = vừa màn hình thường, KHÔNG cuộn ngang (PLAN 4.3). E..G chỉ
# dùng khi bảng row_group có > 3 cột — giữ hẹp để không phá bố cục.
COLUMN_WIDTHS = {"A": 44, "B": 30, "C": 30, "D": 14, "E": 16, "F": 16,
                 "G": 16}

# Header bảng map trên MAP_SHEET — thứ tự cố định, X3 đọc theo tên cột.
MAP_COLUMNS = (
    "question_id", "group", "type", "data_key", "when_json", "transform",
    "row_group", "layout", "cell", "cell_row", "cell_col", "row_last",
    "repeatable", "autofill", "required", "version", "multi_key",
)
MAP_HEADER_ROW = 3            # hàng header của bảng map
MAP_FIRST_ROW = 4             # dòng map đầu tiên

DATE_NOTE = "dd/mm/yyyy"
SELECT_NOTE = "Chọn một dòng trong danh sách ▾"
MAX_FORMULA_LEN = 255         # giới hạn formula1 của DataValidation (Excel)

GUIDE_LINES = (
    "Ô NỀN VÀNG là phần bạn điền. Ô NỀN XÁM phần ứng dụng tự điền giúp bạn, "
    "không cần làm gì.",
    "CHỈ điền vào ô vàng. Không sửa, xóa, chèn/xóa hàng hay đổi tên cột — "
    "phiếu lệch khung sẽ bị từ chối lúc nạp kèm danh sách lỗi.",
    "Ô có mũi tên ▾ là danh sách chọn: bấm mũi tên rồi CHỌN một dòng, "
    "không gõ tay.",
    "Ngày ghi theo dạng dd/mm/yyyy (ví dụ 05/12/1985). Số tiền/số lượng ghi "
    "bằng số, có thể dùng dấu chấm ngăn cách nghìn (ví dụ 5.000.000).",
    "Chữ mờ ngay dưới nhãn là VÍ DỤ điền mẫu — làm theo mẫu. Bỏ trống ô bạn "
    "chưa có thông tin, sẽ được nhắc lại lúc nạp phiếu.",
)


class ExcelExportError(ValueError):
    """Lỗi cấu trúc questionnaire / meta khi xuất phiếu — fail-loud.

    Bắt theo `code` như `QuestionnaireError` của wave X1 (cùng idiom), để
    bridge X5 map thẳng sang thông báo người dùng.
    """

    def __init__(self, code: str, message: str):
        super().__init__("[%s] %s" % (code, message))
        self.code = code


# ---------------------------------------------------------------------------
# Style helpers (tạo mới mỗi lần gọi: openpyxl style object không được dùng chung)
# ---------------------------------------------------------------------------

_THIN = Side(style="thin", color=BORDER_HEX)


def _border() -> Border:
    return Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _fill(hex_color: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=hex_color)


def _wrap(vertical: str = "top") -> Alignment:
    return Alignment(wrap_text=True, vertical=vertical, horizontal="left")


# ---------------------------------------------------------------------------
# Kiểm tra đầu vào — fail-loud trước khi đụng file
# ---------------------------------------------------------------------------

def _targets(item: dict) -> list[dict]:
    """Chuẩn hóa `data_key` (string | list target) thành list target."""
    dk = item["data_key"]
    if isinstance(dk, str):
        return [{"key": dk}]
    return list(dk)


def _validate_questionnaire(questionnaire: dict) -> dict:
    if not isinstance(questionnaire, dict):
        raise ExcelExportError(
            "NOT_OBJECT", "questionnaire phải là dict, nhận %s"
            % type(questionnaire).__name__)
    for field in ("title", "questions"):
        if field not in questionnaire:
            raise ExcelExportError("MISSING_FIELD", "thiếu %r" % field)
    if not isinstance(questionnaire["title"], str) or \
            not questionnaire["title"].strip():
        raise ExcelExportError("MISSING_FIELD", "title phải là chuỗi khác rỗng")
    questions = questionnaire["questions"]
    if not isinstance(questions, list) or not questions:
        raise ExcelExportError("NO_QUESTIONS", "questions rỗng")

    seen: set[str] = set()
    row_groups: dict[str, list[dict]] = {}
    for item in questions:
        if not isinstance(item, dict):
            raise ExcelExportError("BAD_QUESTION", "question phải là dict")
        for field in ("question_id", "group", "text", "type"):
            if field not in item:
                raise ExcelExportError(
                    "MISSING_FIELD", "%s: thiếu %r"
                    % (item.get("question_id", "?"), field))
        qid = item["question_id"]
        if not isinstance(qid, str) or not qid:
            raise ExcelExportError("BAD_QUESTION", "question_id phải là chuỗi")
        if qid in seen:
            raise ExcelExportError("DUP_ID", "question_id trùng: %r" % qid)
        seen.add(qid)
        if not isinstance(item["text"], str) or not item["text"].strip():
            raise ExcelExportError("BAD_QUESTION", "%s: text câu hỏi rỗng" % qid)
        if item["type"] not in QUESTION_TYPES:
            raise ExcelExportError(
                "BAD_TYPE", "%s: type lạ %r (schema v1: %s)"
                % (qid, item["type"], ", ".join(sorted(QUESTION_TYPES))))
        rg = item.get("row_group")
        if rg is not None and (not isinstance(rg, str) or not rg):
            raise ExcelExportError("BAD_ROW_GROUP", "%s: row_group" % qid)
        # ô điền phải biết mình là dropdown hay ô gõ tay
        if item["type"] in ("select", "mark"):
            _dropdown_formula(item)
        row_groups.setdefault(rg, []).append(item)

    max_table_cols = MAX_FILL_COLUMN - COL_FILL + 1
    for rg, items in row_groups.items():
        if rg is None:
            continue
        if len(items) > max_table_cols:
            raise ExcelExportError(
                "TOO_MANY_COLUMNS", "row_group %r có %d câu (> %d cột)"
                % (rg, len(items), max_table_cols))
    return questionnaire


def _dropdown_formula(item: dict) -> str:
    """formula1 cho ô chọn-là-chọn: select dùng labels, mark luôn 'X'."""
    if item["type"] == "mark":
        return '"%s"' % MARK_VALUE
    options = item.get("options")
    if not options or not isinstance(options, list):
        raise ExcelExportError(
            "NO_OPTIONS", "%s: select phải có options" % item["question_id"])
    labels: list[str] = []
    for opt in options:
        if not isinstance(opt, dict):
            raise ExcelExportError(
                "BAD_OPTION_LABEL", "%s: option phải là dict"
                % item["question_id"])
        label = opt.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ExcelExportError(
                "BAD_OPTION_LABEL", "%s: option thiếu label" % item["question_id"])
        if any(ch in label for ch in (",", '"', "\n", "\r")):
            raise ExcelExportError(
                "BAD_OPTION_LABEL",
                "%s: label %r chứa dấu phẩy/ngoặc kép/xuống dòng — Excel list "
                "không cho phép" % (item["question_id"], label))
        if label in labels:
            raise ExcelExportError(
                "BAD_OPTION_LABEL", "%s: label trùng %r" % (item["question_id"], label))
        labels.append(label)
    formula = '"%s"' % ",".join(labels)
    if len(formula) > MAX_FORMULA_LEN:
        raise ExcelExportError(
            "LIST_TOO_LONG", "%s: danh sách chọn dài %d ký tự (> %d)"
            % (item["question_id"], len(formula), MAX_FORMULA_LEN))
    return formula


def _validate_meta(meta: dict | None) -> dict:
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise ExcelExportError(
            "BAD_META", "meta phải là dict hoặc None, nhận %s"
            % type(meta).__name__)
    for key in ("case_id", "today"):
        value = meta.get(key)
        if value is not None and not isinstance(value, str):
            raise ExcelExportError(
                "BAD_META", "meta[%r] phải là chuỗi, nhận %s"
                % (key, type(value).__name__))
    return meta


# ---------------------------------------------------------------------------
# Ghi sheet "Phieu"
# ---------------------------------------------------------------------------

def _write_header(ws, questionnaire: dict, meta: dict) -> None:
    """Hàng 1 tiêu đề, hàng 2 dòng hồ sơ, hàng 3..7 hướng dẫn, hàng 8 đệm."""
    last_col = COL_DATE_NOTE
    title = ws.cell(row=TITLE_ROW, column=COL_LABEL,
                    value=questionnaire["title"].strip())
    title.font = Font(bold=True, size=14, color="1F3864")
    title.alignment = Alignment(vertical="center", horizontal="left")
    ws.merge_cells(start_row=TITLE_ROW, start_column=COL_LABEL,
                   end_row=TITLE_ROW, end_column=last_col)
    ws.row_dimensions[TITLE_ROW].height = 24

    case_id = meta.get("case_id")
    today = meta.get("today")
    if case_id or today:
        parts = []
        if case_id:
            parts.append("Hồ sơ: %s" % case_id)
        if today:
            parts.append("Ngày lập phiếu: %s" % today)
        meta_cell = ws.cell(row=META_ROW, column=COL_LABEL, value=" — ".join(parts))
        meta_cell.font = Font(size=10, italic=True, color=META_FONT_HEX)
        meta_cell.alignment = _wrap("center")
    ws.merge_cells(start_row=META_ROW, start_column=COL_LABEL,
                   end_row=META_ROW, end_column=last_col)

    for offset, line in enumerate(GUIDE_LINES):
        cell = ws.cell(row=GUIDE_FIRST_ROW + offset, column=COL_LABEL, value=line)
        cell.font = Font(size=10, color=GUIDE_FONT_HEX)
        cell.alignment = _wrap("center")
        ws.merge_cells(start_row=GUIDE_FIRST_ROW + offset, start_column=COL_LABEL,
                       end_row=GUIDE_FIRST_ROW + offset, end_column=last_col)

    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width


def _style_fill_cell(cell, item: dict) -> None:
    """Ô điền: vàng mở khóa (khách điền) hoặc xám khóa (app tự làm)."""
    autofill = item.get("autofill") is not None
    cell.fill = _fill(GRAY_HEX if autofill else GOLD_HEX)
    cell.border = _border()
    cell.alignment = _wrap()
    cell.number_format = "@"          # giữ nguyên chuỗi khách gõ (E2 lúc nạp)
    cell.protection = Protection(locked=autofill)


def _write_section(ws, row: int, group: str, color_index: int, span: int) -> None:
    """Hàng tiêu đề nhóm — màu pastel riêng theo thứ tự nhóm."""
    cell = ws.cell(row=row, column=COL_LABEL, value=group)
    cell.font = Font(bold=True, size=11, color="1F3864")
    cell.fill = _fill(GROUP_PALETTE[color_index % len(GROUP_PALETTE)])
    cell.alignment = Alignment(vertical="center", horizontal="left")
    cell.border = _border()
    ws.merge_cells(start_row=row, start_column=COL_LABEL, end_row=row,
                   end_column=max(span, COL_DATE_NOTE))


def _map_entry(item: dict, target: dict, row: int, col: int, row_last: int,
               layout: str) -> dict:
    """Một dòng của bảng MAP_SHEET: ô điền -> key (X3 dịch ngược, không dò)."""
    when = target.get("when") or {}
    return {
        "question_id": item["question_id"],
        "group": item["group"],
        "type": item["type"],
        "data_key": target["key"],
        "when_json": json.dumps(when, ensure_ascii=True, sort_keys=True),
        "transform": target.get("transform") or "",
        "row_group": item.get("row_group") or "",
        "layout": layout,
        "cell": "%s%d" % (get_column_letter(col), row),
        "cell_row": row,
        "cell_col": col,
        "row_last": row_last,
        "repeatable": "yes" if item.get("repeatable") else "",
        "autofill": item.get("autofill") or "",
        "required": "yes" if item.get("required") else "",
        "version": item.get("version") or "",
        "multi_key": "yes" if isinstance(item["data_key"], list) else "",
    }


def _write_question(ws, row: int, item: dict) -> tuple[list[dict], int]:
    """Một câu = 1 hàng: A nhãn, B ô điền, C ví dụ mờ/ghi chú, D ghi chú date."""
    label = ws.cell(row=row, column=COL_LABEL, value=item["text"])
    label.font = Font(size=11)
    label.alignment = _wrap()
    label.border = _border()

    fill_cell = ws.cell(row=row, column=COL_FILL)
    _style_fill_cell(fill_cell, item)
    if item["type"] in ("select", "mark"):
        _add_dropdown(ws, fill_cell.coordinate, _dropdown_formula(item))

    note = item.get("example")
    if note:
        note_text = "ví dụ: %s" % note          # ví dụ điền mẫu — chữ mờ
    elif item["type"] == "select":
        note_text = SELECT_NOTE                  # ghi chú cách chọn
    else:
        note_text = ""
    if note_text:
        note_cell = ws.cell(row=row, column=COL_NOTE, value=note_text)
        note_cell.font = Font(size=10, italic=True, color=NOTE_FONT_HEX)
        note_cell.alignment = _wrap()
    if item["type"] == "date":
        date_cell = ws.cell(row=row, column=COL_DATE_NOTE, value=DATE_NOTE)
        date_cell.font = Font(size=10, italic=True, color=NOTE_FONT_HEX)
        date_cell.alignment = _wrap()

    row_last = row
    return [_map_entry(item, t, row, COL_FILL, row_last, "single")
            for t in _targets(item)], row_last


def _add_dropdown(ws, coordinate: str, formula1: str) -> None:
    dv = DataValidation(type="list", formula1=formula1, allow_blank=True,
                        showErrorMessage=True)
    dv.errorTitle = "Giá trị không hợp lệ"
    dv.error = "Chỉ chọn một dòng trong danh sách (bấm mũi tên ▾)."
    dv.promptTitle = "Chọn từ danh sách"
    dv.prompt = "Bấm mũi tên ▾ rồi chọn một dòng, không gõ tay."
    ws.add_data_validation(dv)
    dv.add(coordinate)


def _write_table(ws, row: int, items: list[dict],
                 color_index: int) -> tuple[list[dict], int]:
    """Câu `row_group` = một bảng nhỏ: header + `REPEAT_ROWS` hàng điền.

    Header = text các câu (cột lần lượt từ B), nền màu của nhóm. Cột thuộc
    câu có `autofill` là Ô XÁM KHÓA (app tự làm, ví dụ mã VSIC), các cột còn
    lại Ô VÀNG mở khóa để khách điền từng dòng.
    """
    entries: list[dict] = []
    first_data_row = row + 1
    last_data_row = row + REPEAT_ROWS
    for offset, item in enumerate(items):
        col = COL_FILL + offset
        head = ws.cell(row=row, column=col, value=item["text"])
        head.font = Font(bold=True, size=10, color="1F3864")
        head.fill = _fill(GROUP_PALETTE[color_index % len(GROUP_PALETTE)])
        head.alignment = _wrap()
        head.border = _border()
        for data_row in range(first_data_row, last_data_row + 1):
            _style_fill_cell(ws.cell(row=data_row, column=col), item)
        if item["type"] in ("select", "mark"):
            _add_dropdown(
                ws, "%s%d:%s%d" % (get_column_letter(col), first_data_row,
                                   get_column_letter(col), last_data_row),
                _dropdown_formula(item))
        for target in _targets(item):
            entries.append(_map_entry(item, target, first_data_row, col,
                                      last_data_row, "table"))
    return entries, last_data_row


def _plan_blocks(questions: list[dict]) -> list[dict]:
    """Gom câu thành khối theo thứ tự file; câu `row_group` gom về một bảng."""
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


def _write_body(ws, questions: list[dict]) -> list[dict]:
    blocks = _plan_blocks(questions)
    entries: list[dict] = []
    row = FIRST_BODY_ROW
    current_group = None
    color_index = 0
    for block in blocks:
        span = COL_DATE_NOTE if block["kind"] == "question" \
            else COL_FILL + len(block["items"]) - 1
        if block["group"] != current_group:
            current_group = block["group"]
            _write_section(ws, row, current_group, color_index, span)
            color_index += 1
            row += 1
        if block["kind"] == "question":
            block_entries, row_last = _write_question(ws, row, block["item"])
            row = row_last + 1
        else:
            block_entries, row_last = _write_table(ws, row, block["items"],
                                                   color_index - 1)
            row = row_last + 1
        entries.extend(block_entries)
        row += 1          # hàng đệm giữa các khối cho dễ đọc
    return entries


def _finish_protection(ws) -> None:
    """Khóa sheet, cho phép khách chọn ô và chỉnh độ rộng cột/hàng."""
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.freeze_panes = "A%d" % FIRST_BODY_ROW
    ws.sheet_view.showGridLines = False


# ---------------------------------------------------------------------------
# Ghi sheet MAP_SHEET (metadata cho X3)
# ---------------------------------------------------------------------------

def _write_map(wb: Workbook, questionnaire: dict, meta: dict,
               entries: list[dict]) -> None:
    ws = wb.create_sheet(MAP_SHEET)
    ws.sheet_state = "hidden"

    ws.cell(row=1, column=1, value=MAP_MARKER)
    head = ws.cell(row=1, column=2, value=json.dumps(
        {
            "doc_id": questionnaire.get("doc_id"),
            "title": questionnaire.get("title"),
            "cluster": questionnaire.get("cluster"),
            "questionnaire_version": questionnaire.get("questionnaire_version"),
            "map_version": MAP_VERSION,
            "sheet": SHEET_NAME,
            "generator": "tools/excel_export.py",
            "first_body_row": FIRST_BODY_ROW,
            "repeat_rows": REPEAT_ROWS,
            "case_id": meta.get("case_id") or "",
            "today": meta.get("today") or "",
        },
        ensure_ascii=True, sort_keys=True))
    head.alignment = _wrap()

    for offset, name in enumerate(MAP_COLUMNS):
        cell = ws.cell(row=MAP_HEADER_ROW, column=1 + offset, value=name)
        cell.font = Font(bold=True, size=10)
        cell.fill = _fill(GRAY_HEX)
        cell.border = _border()
        cell.alignment = _wrap()
    for index, entry in enumerate(entries):
        for offset, name in enumerate(MAP_COLUMNS):
            cell = ws.cell(row=MAP_FIRST_ROW + index, column=1 + offset,
                           value=entry[name])
            cell.alignment = _wrap()

    widths = {"A": 26, "B": 26, "C": 10, "D": 30, "E": 34, "F": 12, "G": 14,
              "H": 10, "I": 9, "J": 9, "K": 9, "L": 10, "M": 11, "N": 10,
              "O": 10, "P": 9, "Q": 10}
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width

    # map cũng khóa: khách không cần thấy (sheet ẩn) và không sửa được
    ws.protection.sheet = True


# ---------------------------------------------------------------------------
# API chính
# ---------------------------------------------------------------------------

def write_questionnaire(questionnaire: dict, out_path: "str | Path",
                        meta: dict | None = None) -> Path:
    """Ghi phiếu .xlsx cho khách và trả về `Path` file đã ghi.

    `questionnaire`: dict schema v1 (artifact `app/data/questionnaire/*.json`).
    `meta`: tùy chọn `{"case_id": str, "today": "dd/mm/yyyy"}` — in lên dòng
        hồ sơ dưới tiêu đề, không bắt buộc.
    Cấu trúc questionnaire KHÔNG bị sửa đổi (hàm thuần đọc).

    Raises `ExcelExportError` (có `code`) khi questionnaire/meta sai khung.
    """
    _validate_questionnaire(questionnaire)
    meta = _validate_meta(meta)

    path = Path(out_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    _write_header(ws, questionnaire, meta)
    entries = _write_body(ws, questionnaire["questions"])
    _finish_protection(ws)
    _write_map(wb, questionnaire, meta, entries)
    wb.save(path)
    return path
