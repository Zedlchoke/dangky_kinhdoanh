# -*- coding: utf-8 -*-
"""Nạp .xlsx phiếu khách → data draft (wave X3 — PLAN.md mục 4.4).

Đọc lại file Excel app xuất cho khách (wave X2) và dịch ngược
`question_id -> data_key` thành data cho draft:

    data = {data_key: giá_trị, ...}                 # key phẳng, đúng chuỗi
    data["ds_nganh_dntn"] = [{tag: giá_trị}, ...]   # row_group -> list hàng

THUẦN FUNCTION: chỉ đọc đúng file được truyền vào, KHÔNG đụng draft/IO khác,
KHÔNG in ra (selftest mới in). Fail-loud — có lỗi là trả `ok=False, data=None`,
KHÔNG BAO GIỜ trả data một phần (draft cũ không bị ghi đè).

Hợp đồng đối xứng với bridge X5 (KHÔNG được lệch):
    import_questionnaire(path, questionnaire) -> {"ok", "errors", "data"}

Sheet map ẩn `___map` (wave X2 ghi) là hợp đồng vị trí ô. ĐỌC PHÒNG THỦ:
- Hàng metadata `key=value` trước header: `questionnaire_version=1`,
  `doc_id=PLI_M72`, `sheet=Phieu` (tùy chọn — thiếu thì lấy sheet phiếu là
  sheet đầu tiên khác `___map`; `questionnaire_version` thì BẮT BUỘC).
- Hàng header (tên cột, thứ tự tự do): `question_id | key | when | transform |
  row_group | cell`. Bắt buộc `question_id`, `key`, `cell`.
- Mỗi hàng sau = MỘT ô điền. `when` là chuỗi JSON; `cell` là địa chỉ ô ("B7")
  hoặc cặp số "row,col". `row_group` + số hàng sheet -> group từng BẢNG: mỗi
  hàng sheet có ít nhất một ô điền = một record, hàng trắng bỏ qua.
- MỘT ô có thể sinh NHIỀU data_key: (a) câu date tách 3 key
  (date_day/date_month/date_year) — N hàng cùng địa chỉ ô, khác `transform`;
  (b) câu có nhiều nhánh `when` (loại hình do KHÁCH điền nên người xuất không
  biết nhánh nào) — N hàng cùng địa chỉ ô, khác `key`/`when`. Lúc nạp chỉ
  nhánh khớp câu trả lời được lấy, nhánh khác bỏ qua. Khai báo trùng lặp Y
  HỆT nhau (cả key + when + transform + ô) mới là khung hỏng (BAD_HEADER);
  một ô phục vụ HAI question_id khác nhau thì luôn là khung hỏng.

`when`/`transform`/`row_group` trong map chỉ để ĐỐI CHIẾU: value khác rỗng mà
lệch questionnaire -> khung hỏng; ô trống thì lấy giá trị trong questionnaire
dict (nguồn chân lý) — không đoán thêm.

UNKNOWN_CELL là heuristic có chủ đích (bắt khách phá khung nhưng không nhầm
label tĩnh): ô có dữ liệu KHÔNG nằm trong map chỉ bị lỗi khi (a) cột của nó có
ô map, (b) hàng của nó có ô map, và (c) nội dung không phải chuỗi tĩnh app tự
render (title/group/text/example/option lấy từ questionnaire dict).
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_to_tuple

from tools.questionnaire.schema import TRANSFORMS

# ---------------------------------------------------------------------------
# Hằng số hợp đồng (export ra — bridge X5 so code theo đúng chuỗi này)
# ---------------------------------------------------------------------------

MAP_SHEET = "___map"
"""Tên sheet ẩn chứa map vị trí ô (khớp brief lane X2)."""

MAP_COLUMNS = ("question_id", "key", "when", "transform", "row_group", "cell")
"""Tên cột header của sheet map (so tên sau trim/lower, thứ tự tự do)."""

BAD_HEADER = "BAD_HEADER"
"""Sai khung: thiếu/hỏng sheet map, ô map lạ, layout lệch questionnaire."""

BAD_VERSION = "BAD_VERSION"
"""`questionnaire_version` hoặc tập question_id của phiếu lệch questionnaire."""

UNKNOWN_CELL = "UNKNOWN_CELL"
"""Ô có dữ liệu nhưng không khớp vùng điền nào — khách phá khung."""

MISSING_REQUIRED = "MISSING_REQUIRED"
"""Câu required trống (kèm `question_id`)."""

BAD_SELECT = "BAD_SELECT"
"""Giá trị không nằm trong options của câu select/mark."""

BAD_DATE = "BAD_DATE"
"""Không parse được ngày dd/mm/yyyy."""

BAD_NUMBER = "BAD_NUMBER"
"""money/integer không parse được sau khi bỏ dấu ngăn cách nghìn."""

__all__ = [
    "MAP_SHEET", "MAP_COLUMNS",
    "BAD_HEADER", "BAD_VERSION", "UNKNOWN_CELL", "MISSING_REQUIRED",
    "BAD_SELECT", "BAD_DATE", "BAD_NUMBER",
    "import_questionnaire",
]

_META_VERSION = "questionnaire_version"  # bắt buộc trong metadata map
_META_SHEET = "sheet"                    # tùy chọn: tên sheet phiếu
_META_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_COORD_RE = re.compile(r"^\$?[A-Za-z]{1,3}\$?\d{1,7}$")
_PAIR_RE = re.compile(r"^(\d{1,7})\s*[,;/xX]\s*(\d{1,7})$")

def _err(code: str, message: str, cell: str | None = None,
         question_id: str | None = None) -> dict:
    """Một phần tử của `errors` — hình dạng cố định cho bridge X5."""
    return {
        "code": code,
        "message": message,
        "cell": cell,
        "question_id": question_id,
    }


def _fail(errors: list[dict]) -> dict:
    """Kết quả lỗi: KHÔNG BAO GIỜ kèm data một phần."""
    return {"ok": False, "errors": errors, "data": None}


# ---------------------------------------------------------------------------
# Chuẩn hoá giá trị ô Excel
# ---------------------------------------------------------------------------

def _cell_text(value: Any) -> str:
    """Ô Excel -> chuỗi đã trim (số -> chữ, ngày -> dd/mm/yyyy)."""
    if value is None:
        return ""
    if isinstance(value, str):
        # Nbsp / zero-width do copy-paste — không tính là nội dung.
        return value.replace(" ", " ").replace("​", "").strip()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value).strip()


def _norm_label(text: str) -> str:
    """Chuẩn hoá để so chuỗi tĩnh: gọn khoảng trắng, không phân biệt hoa/thường."""
    return " ".join(text.split()).casefold()


def _parse_number(raw: str, kind: str) -> int | float:
    """money/integer -> số. Bỏ khoảng trắng + dấu chấm/phẩy ngăn cách nghìn.

    "5.000.000" -> 5000000; "5.500,50" -> 5500.5. Phần thập phân chỉ nhận khi
    nằm CUỐI chuỗi và có 1-2 chữ số (tránh nuốt ".000" của nhóm nghìn).
    """
    text = "".join(_cell_text(raw).split()).replace("−", "-")
    if not text:
        raise ValueError("ô trống")
    sign = -1 if text[0] == "-" else 1
    if text[0] in "+-":
        text = text[1:]

    dec = 0
    tail = re.search(r"[.,](\d{1,2})$", text)
    if tail and re.fullmatch(r"[\d.,]*\d", text[:tail.start()]):
        frac = tail.group(1)
        dec = int(frac) * (10 if len(frac) == 1 else 1)
        text = text[:tail.start()]

    digits = text.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise ValueError("không phải số: %r" % _cell_text(raw))
    value = sign * int(digits)
    if dec:
        value += sign * dec / 100.0
    if kind == "integer" and isinstance(value, float) and not value.is_integer():
        raise ValueError("integer phải nguyên, nhận %r" % _cell_text(raw))
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return value


def _parse_date(raw: str) -> tuple[int, int, int]:
    """dd/mm/yyyy -> (ngày, tháng, năm). Sai dạng/ngày không có thật -> lỗi."""
    m = _DATE_RE.match(_cell_text(raw))
    if not m:
        raise ValueError("không phải dd/mm/yyyy: %r" % _cell_text(raw))
    day, month, year = (int(g) for g in m.groups())
    datetime(year, month, day)  # 32/13/2020 -> ValueError
    return day, month, year


# ---------------------------------------------------------------------------
# Map sheet `___map`
# ---------------------------------------------------------------------------

@dataclass
class _MapEntry:
    """Một ô điền trong phiếu (đã đối chiếu questionnaire ở bước 4)."""

    question_id: str
    key: str          # data_key đầy đủ, vd "ds_nganh_dntn.ten_nganh"
    address: str      # "B7"
    row: int
    col: int
    row_group: str | None = None
    when: dict | None = None
    transform: str | None = None
    value: Any = None
    filled: bool = False
    resolved: bool = False   # target khớp điều kiện `when`
    value_error: bool = False  # ô có lỗi giá trị (đừng báo MISSING_REQUIRED thêm)


def _parse_cell_address(text: str) -> tuple[int, int] | None:
    """"B7" -> (7, 2); "7,2" -> (7, 2). Không nhận diện được -> None."""
    if _COORD_RE.match(text):
        return coordinate_to_tuple(text.replace("$", ""))
    m = _PAIR_RE.match(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _read_map(wb) -> tuple[dict[str, str], list[_MapEntry], list[dict]]:
    """Đọc phòng thủ sheet map. Trả (metadata, entries, lỗi khung)."""
    meta: dict[str, str] = {}
    errors: list[dict] = []
    if MAP_SHEET not in wb.sheetnames:
        return meta, [], [_err(
            BAD_HEADER,
            "File thiếu sheet map %r — không phải phiếu app xuất" % MAP_SHEET)]

    rows = [list(r) for r in wb[MAP_SHEET].iter_rows(values_only=True)]
    header_idx: int | None = None
    col_of: dict[str, int] = {}
    for idx, row in enumerate(rows):
        texts = [_cell_text(v) for v in row]
        if "question_id" in [t.lower() for t in texts if t]:
            header_idx = idx
            for pos, text in enumerate(texts):
                if text:
                    col_of.setdefault(text.lower(), pos)
            break
        # Metadata `key=value` — chỉ đọc TRƯỚC header.
        for text in texts:
            key, sep, val = text.partition("=")
            if sep and _META_KEY_RE.fullmatch(key.strip()):
                meta.setdefault(key.strip(), val.strip())

    if header_idx is None:
        return meta, [], [_err(
            BAD_HEADER, "Sheet %r không có hàng header (cần cột %s)"
            % (MAP_SHEET, " | ".join(MAP_COLUMNS)))]
    missing = [name for name in ("question_id", "key", "cell")
               if name not in col_of]
    if missing:
        return meta, [], [_err(
            BAD_HEADER, "Sheet %r thiếu cột bắt buộc: %s"
            % (MAP_SHEET, ", ".join(missing)))]

    col_when = col_of.get("when")
    col_transform = col_of.get("transform")
    col_row_group = col_of.get("row_group")
    entries: list[_MapEntry] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for line_no, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        texts = [_cell_text(v) for v in row]

        def opt(col: int | None) -> str:
            return "" if col is None or col >= len(texts) else texts[col]

        qid = opt(col_of["question_id"])
        if not qid and not any(texts):
            continue  # hàng trắng trong map — bỏ qua
        if not qid:
            errors.append(_err(BAD_HEADER,
                               "Sheet %r hàng %d thiếu question_id"
                               % (MAP_SHEET, line_no)))
            continue
        key = opt(col_of["key"])
        address = opt(col_of["cell"])
        if not key or not address:
            errors.append(_err(
                BAD_HEADER, "Sheet %r hàng %d (%s): thiếu key hoặc cell"
                % (MAP_SHEET, line_no, qid), question_id=qid))
            continue
        coord = _parse_cell_address(address)
        if coord is None:
            errors.append(_err(
                BAD_HEADER, "Sheet %r hàng %d (%s): cell %r không hợp lệ"
                % (MAP_SHEET, line_no, qid, address), cell=address,
                question_id=qid))
            continue

        when: dict | None = None
        when_raw = opt(col_when)
        if when_raw:
            try:
                parsed = json.loads(when_raw)
            except ValueError:
                errors.append(_err(
                    BAD_HEADER, "Sheet %r hàng %d (%s): when không phải JSON: %r"
                    % (MAP_SHEET, line_no, qid, when_raw), cell=address,
                    question_id=qid))
                continue
            if not isinstance(parsed, dict) or not all(
                    isinstance(v, list) for v in parsed.values()):
                errors.append(_err(
                    BAD_HEADER,
                    "Sheet %r hàng %d (%s): when phải là {key: [giá trị]}"
                    % (MAP_SHEET, line_no, qid), cell=address, question_id=qid))
                continue
            when = parsed

        transform = opt(col_transform) or None
        if transform is not None and transform not in TRANSFORMS:
            errors.append(_err(
                BAD_HEADER, "Sheet %r hàng %d (%s): transform lạ %r"
                % (MAP_SHEET, line_no, qid, transform), cell=address,
                question_id=qid))
            continue

        # Khai báo y hệt nhau 2 lần = writer hỏng (khác transform/when thì
        # hợp lệ — câu date tách 3 key cùng một ô).
        fingerprint = (qid, key, address, transform or "", opt(col_row_group))
        if fingerprint in seen:
            errors.append(_err(
                BAD_HEADER, "Sheet %r hàng %d (%s): ô %s khai báo trùng lặp"
                % (MAP_SHEET, line_no, qid, address), cell=address,
                question_id=qid))
            continue
        seen.add(fingerprint)

        entries.append(_MapEntry(
            question_id=qid, key=key, address=address,
            row=coord[0], col=coord[1],
            row_group=opt(col_row_group) or None,
            when=when, transform=transform))
    return meta, entries, errors


# ---------------------------------------------------------------------------
# Câu hỏi / target
# ---------------------------------------------------------------------------

def _targets_of(question: dict) -> list[dict]:
    """data_key (string | list target) -> list {key, when, transform}."""
    raw = question.get("data_key")
    items = [raw] if isinstance(raw, str) else list(raw or [])
    out: list[dict] = []
    for item in items:
        if isinstance(item, str):
            out.append({"key": item, "when": None, "transform": None})
        elif isinstance(item, dict) and isinstance(item.get("key"), str):
            out.append({"key": item["key"], "when": item.get("when") or None,
                        "transform": item.get("transform")})
    return out


def _when_match(when: dict | None, answers: dict[str, Any]) -> bool:
    """Target có `when` chỉ bật khi mọi điều kiện khớp answers đã đọc.

    So sau trim, phân biệt hoa/thường (cùng idiom activeWhen runtime — X1).
    """
    if not when:
        return True
    for cond_key, expected in when.items():
        got = answers.get(cond_key)
        if not isinstance(got, str):
            return False  # câu điều kiện chưa điền / là bảng lặp -> không khớp
        if got not in expected:
            return False
    return True


def _split_loop_key(key: str) -> tuple[str, str]:
    """data_key của row_group -> (loop_name, tag).

    "ds_nganh_dntn.ten_nganh" -> ("ds_nganh_dntn", "ten_nganh");
    key không có dấu chấm -> tag = chính key.
    """
    if "." in key:
        prefix, tag = key.rsplit(".", 1)
        return prefix, tag
    return key, key


def _json_canon(value: Any) -> str:
    """Chuẩn hoá để so `when` giữa map và questionnaire (key sort, gọn)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _static_texts(questionnaire: dict) -> set[str]:
    """Chuỗi tĩnh app tự render — để không nhầm label với ô khách gõ."""
    out = {_norm_label(str(questionnaire.get("title", ""))),
           _norm_label(str(questionnaire.get("doc_id", "")))}
    for q in questionnaire.get("questions", []):
        if not isinstance(q, dict):
            continue
        for name in ("group", "text", "example"):
            if q.get(name):
                out.add(_norm_label(str(q[name])))
        for opt in q.get("options") or []:
            if isinstance(opt, dict):
                for name in ("label", "value"):
                    if opt.get(name):
                        out.add(_norm_label(str(opt[name])))
    out.discard("")
    return out


def _find_unknown_cells(ws, entries: list[_MapEntry],
                        questionnaire: dict) -> list[dict]:
    """Ô có dữ liệu ngoài vùng điền -> UNKNOWN_CELL (xem docstring module)."""
    mapped = {(e.row, e.col) for e in entries}
    mapped_cols = {c for _, c in mapped}
    mapped_rows = {r for r, _ in mapped}
    static = _static_texts(questionnaire)
    errors: list[dict] = []
    for row in ws.iter_rows():
        for cell in row:
            if (cell.row, cell.column) in mapped:
                continue
            if cell.column not in mapped_cols or cell.row not in mapped_rows:
                continue  # ngoài vùng điền: label / hướng dẫn / giấy tờ kèm theo
            text = _cell_text(cell.value)
            if not text or _norm_label(text) in static:
                continue  # ô trống hoặc chuỗi tĩnh app tự render
            errors.append(_err(
                UNKNOWN_CELL,
                "Ô %s có dữ liệu %r nhưng không khớp vùng điền nào"
                % (cell.coordinate, text), cell=cell.coordinate))
    return errors


# ---------------------------------------------------------------------------
# Đọc giá trị từng ô theo type câu hỏi
# ---------------------------------------------------------------------------

def _match_option(question: dict, text: str) -> str | None:
    """So ô select/mark với options: khớp label trước, rồi value. Trả value."""
    exact: dict[str, str] = {}
    loose: dict[str, str] = {}
    for opt in question.get("options") or []:
        if not isinstance(opt, dict):
            continue
        value = str(opt.get("value", ""))
        for name in ("label", "value"):
            raw = str(opt.get(name, "")).strip()
            if not raw:
                continue
            if raw == text:
                exact[raw] = value
            else:
                loose.setdefault(_norm_label(raw), value)
    if text in exact:
        return exact[text]
    return loose.get(_norm_label(text))  # None -> BAD_SELECT


def _normalize_value(question: dict, entry: _MapEntry, raw: Any
                     ) -> tuple[Any, dict | None]:
    """Giá trị ô -> (giá trị data, lỗi). Ô trống -> (None, None).

    Lỗi giá trị KHÔNG làm dừng đọc các ô khác (gom đủ cho panel "còn thiếu").
    """
    text = _cell_text(raw)
    if not text:
        return None, None
    qtype = str(question.get("type") or "")
    try:
        if qtype in ("select", "mark"):
            value = _match_option(question, text)
            if value is None:
                raise ValueError(
                    "giá trị %r không nằm trong options (%s)" % (
                        text, " / ".join(
                            str(o.get("label", o.get("value", "")))
                            for o in question.get("options") or [])))
            return value, None
        if qtype == "date":
            day, month, year = _parse_date(text)
            transform = entry.transform
            if transform == "date_day":
                return "%02d" % day, None
            if transform == "date_month":
                return "%02d" % month, None
            if transform == "date_year":
                return "%04d" % year, None
            # Không có transform: giữ nguyên dd/mm/yyyy (đủ 2 chữ số ngày/tháng).
            return "%02d/%02d/%04d" % (day, month, year), None
        if qtype in ("money", "integer"):
            return _parse_number(text, qtype), None
        # text / tel / email (và type lạ): giữ nguyên văn đã trim.
        return text, None
    except ValueError as exc:
        code = {"select": BAD_SELECT, "mark": BAD_SELECT,
                "date": BAD_DATE, "money": BAD_NUMBER,
                "integer": BAD_NUMBER}.get(qtype, BAD_HEADER)
        return None, _err(code, "Ô %s (%s): %s" % (entry.address,
                                                   entry.question_id, exc),
                          cell=entry.address, question_id=entry.question_id)


# ---------------------------------------------------------------------------
# API chính
# ---------------------------------------------------------------------------

def import_questionnaire(path: str | Path, questionnaire: dict) -> dict:
    """Nạp phiếu .xlsx khách điền -> data draft. Thuần function, fail-loud.

    Trả {"ok": bool, "errors": [...], "data": dict | None}. Có lỗi -> data
    luôn None (draft cũ không bị ghi đè một phần).
    """
    # -- 0. Mở file ---------------------------------------------------------
    try:
        wb = load_workbook(filename=str(path), read_only=False, data_only=True)
    except Exception as exc:  # noqa: BLE001 — sai đuôi / file hỏng / không phải xlsx
        return _fail([_err(BAD_HEADER, "Không mở được file .xlsx: %s" % exc)])

    # -- 1. Sheet map -------------------------------------------------------
    meta, entries, errors = _read_map(wb)
    if errors:
        return _fail(errors)
    if not entries:
        return _fail([_err(BAD_HEADER, "Sheet %r không khai báo ô điền nào"
                           % MAP_SHEET)])

    # -- 2. Version + tập question_id --------------------------------------
    declared = meta.get(_META_VERSION, "")
    expected = questionnaire.get("questionnaire_version")
    if declared != str(expected):
        return _fail([_err(
            BAD_VERSION,
            "Phiếu khai báo questionnaire_version=%r, questionnaire là %r"
            % (declared, expected))])

    questions: dict[str, dict] = {}
    for q in questionnaire.get("questions", []):
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            questions[q["question_id"]] = q
    map_ids = {e.question_id for e in entries}
    if map_ids != set(questions):
        return _fail([_err(
            BAD_VERSION,
            "Tập question_id lệch — phiếu thiếu %s, thừa %s"
            % (sorted(set(questions) - map_ids) or "[]",
               sorted(map_ids - set(questions)) or "[]"))])

    # -- 3. Sheet phiếu -----------------------------------------------------
    declared_sheet = meta.get(_META_SHEET, "")
    if declared_sheet and declared_sheet in wb.sheetnames:
        ws = wb[declared_sheet]
    else:
        others = [name for name in wb.sheetnames if name != MAP_SHEET]
        if not others:
            return _fail([_err(BAD_HEADER,
                               "File không có sheet phiếu (chỉ có %r)" % MAP_SHEET)])
        ws = wb[others[0]]

    # -- 4. Đối chiếu map <-> questionnaire (khung phải khớp) ---------------
    by_qid: dict[str, list[_MapEntry]] = {}
    for entry in entries:
        question = questions[entry.question_id]
        target = next((t for t in _targets_of(question)
                       if t["key"] == entry.key), None)
        if target is None:
            return _fail([_err(
                BAD_HEADER,
                "Ô %s (%s): key %r không thuộc câu hỏi trong questionnaire"
                % (entry.address, entry.question_id, entry.key),
                cell=entry.address, question_id=entry.question_id)])
        # Map ghi value khác rỗng thì phải khớp questionnaire; trống thì lấy
        # giá trị questionnaire (nguồn chân lý) — không đoán thêm.
        if entry.when is not None and \
                _json_canon(entry.when) != _json_canon(target["when"] or {}):
            return _fail([_err(
                BAD_HEADER,
                "Ô %s (%s): when trong map lệch questionnaire (%s != %s)"
                % (entry.address, entry.question_id, _json_canon(entry.when),
                   _json_canon(target["when"] or {})),
                cell=entry.address, question_id=entry.question_id)])
        entry.when = target["when"]
        if entry.transform is not None and entry.transform != target["transform"]:
            return _fail([_err(
                BAD_HEADER,
                "Ô %s (%s): transform trong map lệch questionnaire (%r != %r)"
                % (entry.address, entry.question_id, entry.transform,
                   target["transform"]),
                cell=entry.address, question_id=entry.question_id)])
        entry.transform = target["transform"]
        if (entry.row_group or None) != (question.get("row_group") or None):
            return _fail([_err(
                BAD_HEADER,
                "Ô %s (%s): row_group %r lệch questionnaire %r"
                % (entry.address, entry.question_id, entry.row_group,
                   question.get("row_group")),
                cell=entry.address, question_id=entry.question_id)])
        entry.row_group = question.get("row_group") or None
        by_qid.setdefault(entry.question_id, []).append(entry)

    # Câu KHÔNG lặp: mỗi key đúng một ô, mỗi key đúng một transform.
    for qid, q_entries in by_qid.items():
        if questions[qid].get("row_group"):
            continue
        for key in {e.key for e in q_entries}:
            cells = {e.address for e in q_entries if e.key == key}
            transforms = {e.transform for e in q_entries if e.key == key}
            if len(cells) > 1 or len(transforms) > 1:
                return _fail([_err(
                    BAD_HEADER,
                    "Câu %s (không lặp) key %r có %d ô / %d transform — khung hỏng"
                    % (qid, key, len(cells), len(transforms)))])

    # MỘT ô chỉ phục vụ MỘT câu hỏi — hai câu giành một ô là map hỏng.
    cell_owner: dict[str, str] = {}
    for entry in entries:
        if cell_owner.setdefault(entry.address, entry.question_id) != \
                entry.question_id:
            return _fail([_err(
                BAD_HEADER,
                "Ô %s phục vụ hai câu hỏi (%s và %s) — khung hỏng"
                % (entry.address, cell_owner[entry.address], entry.question_id),
                cell=entry.address, question_id=entry.question_id)])

    # -- 5. Ô lạ ngoài vùng điền (khách phá khung) --------------------------
    stray = _find_unknown_cells(ws, entries, questionnaire)
    if stray:
        return _fail(stray)

    # -- 6. Đọc + chuẩn hoá giá trị ----------------------------------------
    errors = []
    for qid, q_entries in by_qid.items():
        for entry in q_entries:
            entry.value, issue = _normalize_value(
                questions[qid], entry,
                ws.cell(row=entry.row, column=entry.col).value)
            entry.filled = entry.value is not None
            if issue:
                entry.value_error = True
                errors.append(issue)

    # answers cho `when`: chỉ câu có MỘT data_key (string) mới làm điều kiện.
    answers: dict[str, Any] = {}
    for qid, q_entries in by_qid.items():
        if not isinstance(questions[qid].get("data_key"), str):
            continue
        for entry in q_entries:
            if entry.filled:
                answers[entry.key] = entry.value

    # -- 7. Resolve `when` + dựng data -------------------------------------
    data: dict[str, Any] = {}
    # loop_name -> (số hàng sheet -> {tag: giá trị})
    loops: dict[str, dict[int, dict[str, Any]]] = {}
    resolved_by_qid: dict[str, list[_MapEntry]] = {}

    for qid, question in questions.items():
        kept: list[_MapEntry] = []
        active = {t["key"] for t in _targets_of(question)
                  if _when_match(t["when"], answers)}
        # Nhóm theo Ô: một ô có thể sinh nhiều key (date tách 3) và nhiều nhánh
        # `when` (người xuất không biết khách chọn gì) — chỉ nhánh khớp câu trả
        # lời được lấy; ô có dữ liệu mà KHÔNG nhánh nào khớp mới là khung hỏng.
        groups: dict[str, list[_MapEntry]] = {}
        for entry in by_qid.get(qid, []):
            groups.setdefault(entry.address, []).append(entry)
        for address, group in groups.items():
            hits = [e for e in group if e.key in active]
            if not hits:
                if any(e.filled for e in group):
                    errors.append(_err(
                        BAD_HEADER,
                        "Ô %s (%s): có dữ liệu nhưng không có target nào khớp "
                        "điều kiện when — phiếu lệch questionnaire"
                        % (address, qid),
                        cell=address, question_id=qid))
                continue  # ô không kích hoạt theo `when` -> bỏ qua
            for entry in hits:
                entry.resolved = True
                kept.append(entry)
                if not entry.filled:
                    continue
                if entry.row_group:
                    loop_name, tag = _split_loop_key(entry.key)
                    loops.setdefault(loop_name, {}).setdefault(entry.row, {})[tag] = \
                        entry.value
                else:
                    data[entry.key] = entry.value
        resolved_by_qid[qid] = kept

    # -- 8. Required trống --------------------------------------------------
    for qid, question in questions.items():
        if not question.get("required"):
            continue
        kept = resolved_by_qid.get(qid, [])
        if not kept:
            continue  # câu không kích hoạt theo `when` — lỗi khung đã báo ở bước 7
        if any(e.value_error for e in by_qid.get(qid, [])):
            continue  # ô có lỗi giá trị — đã báo BAD_* , đừng báo "trống" thêm
        if question.get("row_group"):
            rows_map: dict[int, list[_MapEntry]] = {}
            for entry in kept:
                rows_map.setdefault(entry.row, []).append(entry)
            filled_rows = sorted(row for row, cells in rows_map.items()
                                 if any(c.filled for c in cells))
            if not filled_rows:
                errors.append(_err(
                    MISSING_REQUIRED, "Câu bắt buộc %s chưa điền dòng nào" % qid,
                    cell=kept[0].address, question_id=qid))
                continue
            for row_no in filled_rows:
                for entry in rows_map[row_no]:
                    if not entry.filled:
                        errors.append(_err(
                            MISSING_REQUIRED,
                            "Ô %s (%s) bắt buộc nhưng trống" % (entry.address, qid),
                            cell=entry.address, question_id=qid))
            continue
        if not any(e.filled for e in kept):
            errors.append(_err(
                MISSING_REQUIRED, "Ô %s (%s) bắt buộc nhưng trống"
                % (kept[0].address, qid),
                cell=kept[0].address, question_id=qid))

    if errors:
        return _fail(errors)

    # -- 9. Gộp bảng lặp (thứ tự theo hàng sheet) --------------------------
    for loop_name, rows_map in loops.items():
        data[loop_name] = [rows_map[row] for row in sorted(rows_map)]

    return {"ok": True, "errors": [], "data": data}


# ---------------------------------------------------------------------------
# Selftest — python3 -X utf8 -m tools.excel_import --selftest
# ---------------------------------------------------------------------------

def _load_pli_m72() -> dict:
    root = Path(__file__).resolve().parent.parent
    return json.loads(
        (root / "app" / "data" / "questionnaire" / "PLI_M72.json")
        .read_text(encoding="utf-8"))


def _fixture_value(qid: str) -> Any:
    """Giá trị điền mẫu cho phiếu TỐT (None = bỏ trống)."""
    return {
        "q_loai_hinh": "Doanh nghiệp tư nhân",    # label -> value DNTN
        "q_ten_tieng_viet": "  Công ty A ",        # trim -> "Công ty A"
        "q_dia_chi_tru_so": "123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
        "q_ho_ten": "nguyễn văn a",                # app tự in hoa, giữ nguyên
        "q_gioi_tinh": "Nam",
        "q_so_cccd": 79085001234,                  # khách gõ số -> vẫn là text
        "q_ngay_sinh": "5/12/1985",                # 1 chữ số ngày -> "05"
        "q_cccd_ngay_cap": datetime(2015, 3, 2),   # ô ngày Excel -> "02/03/2015"
        "q_von": "5.000.000",                      # dấu chấm nghìn -> 5000000
    }.get(qid)


def _map_rows_for(question: dict) -> list[tuple[str, str, str]]:
    """Target map của một câu trong phiếu mẫu: TOÀN BỘ target của câu.

    Người xuất KHÔNG biết khách sẽ chọn gì (ô loại hình do khách điền) nên map
    phải khai đủ mọi nhánh `when` trỏ cùng một ô — lúc nạp chỉ nhánh khớp câu
    trả lời được lấy, nhánh khác bỏ qua. Câu date tách 3 key (ngay/thang/nam)
    dùng chung MỘT ô -> 3 hàng map, mỗi hàng một transform.
    Trả list (key, when_json, transform).
    """
    return [(t["key"],
             json.dumps(t["when"] or {}, ensure_ascii=False, sort_keys=True),
             str(t["transform"] or ""))
            for t in _targets_of(question)]


def _write_phieu(path: Path, version: int = 1,
                 stray: dict[str, Any] | None = None,
                 overrides: dict[str, Any] | None = None,
                 drop_map_sheet: bool = False,
                 broken_header: bool = False) -> None:
    """Dựng phiếu .xlsx trong tmp (KHÔNG ghi vào repo) theo format map X3."""
    from openpyxl import Workbook

    questionnaire = _load_pli_m72()
    questions = {q["question_id"]: q for q in questionnaire["questions"]}
    overrides = overrides or {}

    wb = Workbook()
    ws = wb.active
    ws.title = "Phieu"
    ws["A1"] = questionnaire["title"]
    map_rows: list[list[str]] = []

    def fill(qid: str, address: str, value: Any) -> None:
        ws[address] = value
        for key, when, transform in _map_rows_for(questions[qid]):
            map_rows.append([qid, key, when, transform,
                             str(questions[qid].get("row_group") or ""), address])

    # Câu đơn: label ở cột A (chuỗi tĩnh), ô điền ở cột B.
    row_no = 1
    for q in questionnaire["questions"]:
        if q.get("row_group"):
            continue
        row_no += 1
        ws.cell(row=row_no, column=1, value=q["text"])
        fill(q["question_id"], "B%d" % row_no,
             overrides.get(q["question_id"], _fixture_value(q["question_id"])))

    # Bảng `nganh`: header hàng 25, 2 hàng điền (26-27) ở cột B/C/D.
    ws["A25"] = "Ngành bạn muốn kinh doanh"
    ws["B25"] = "Tên ngành"
    ws["C25"] = "Mã ngành (app tra VSIC giúp — không cần điền)"
    ws["D25"] = "Đây có phải ngành nghề chính không? (đánh X vào đúng một dòng)"
    table = {"q_nganh_ten": ("B", ["Bán lẻ hàng điện tử", "Cho thuê xe"]),
             "q_nganh_ma": ("C", [4774, None]),
             "q_nganh_chinh": ("D", ["X", None])}
    for table_row, sheet_row in ((0, 26), (1, 27)):
        for qid, (col, values) in table.items():
            fill(qid, "%s%d" % (col, sheet_row), values[table_row])

    for address, value in (stray or {}).items():
        ws[address] = value

    if drop_map_sheet:
        wb.save(path)
        return

    mws = wb.create_sheet(MAP_SHEET)
    mws.sheet_state = "hidden"
    if broken_header:
        mws.append(("qid", "khoa", "when_json", "transform", "row_group", "o"))
        mws.append(("q_loai_hinh", "dn.loai_hinh", "", "", "", "B2"))
    else:
        mws.append(("questionnaire_version=%d" % version,
                    "doc_id=%s" % questionnaire["doc_id"], "sheet=Phieu"))
        mws.append(list(MAP_COLUMNS))
        for row in map_rows:
            mws.append(row)
    wb.save(path)


_EXPECTED_DNTN = {
    "dn.loai_hinh": "DNTN",
    "dn.ten_tieng_viet": "Công ty A",
    "dn.dia_chi_tru_so": "123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
    "ho_ten_in_hoa": "nguyễn văn a",
    "chu_hkd.gioi_tinh": "Nam",
    "chu_hkd.so_cccd": "79085001234",
    "ngay_sinh": "05",
    "thang_sinh": "12",
    "nam_sinh": "1985",
    "ngay_cap": "02/03/2015",
    "von_dau_tu_so": 5000000,
    "ds_nganh_dntn": [
        {"ten_nganh": "Bán lẻ hàng điện tử", "ma_nganh": "4774",
         "la_nganh_chinh": "X"},
        {"ten_nganh": "Cho thuê xe"},
    ],
}


def _codes(errors: list[dict]) -> list[str]:
    return [e["code"] for e in errors]


def _selftest() -> int:
    """Kịch bản tự kiểm: dựng xlsx trong tmp, không ghi gì vào repo."""
    results: list[tuple[bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            fn()
            results.append((True, name))
            print("PASS %s" % name)
        except AssertionError as exc:
            results.append((False, "%s: %s" % (name, exc)))
            print("FAIL %s: %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001
            results.append((False, "%s: exception %r" % (name, exc)))
            print("FAIL %s: exception %r" % (name, exc))

    questionnaire = _load_pli_m72()

    def case_good() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phieu_ok.xlsx"
            _write_phieu(path)
            out = import_questionnaire(path, questionnaire)
            assert out["ok"] is True, out["errors"]
            assert out["errors"] == [], out["errors"]
            assert out["data"] == _EXPECTED_DNTN, out["data"]

    def case_bad_header() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            no_map = Path(tmp) / "khong_map.xlsx"
            _write_phieu(no_map, drop_map_sheet=True)
            out = import_questionnaire(no_map, questionnaire)
            assert out["ok"] is False and out["data"] is None, out
            assert _codes(out["errors"]) == [BAD_HEADER], out["errors"]

            bad_head = Path(tmp) / "sai_header.xlsx"
            _write_phieu(bad_head, broken_header=True)
            out2 = import_questionnaire(bad_head, questionnaire)
            assert out2["ok"] is False and out2["data"] is None, out2
            assert _codes(out2["errors"]) == [BAD_HEADER], out2["errors"]

            not_xlsx = Path(tmp) / "khong_phai_xlsx.xlsx"
            not_xlsx.write_text("không phải zip", encoding="utf-8")
            out3 = import_questionnaire(not_xlsx, questionnaire)
            assert out3["ok"] is False and out3["data"] is None, out3
            assert _codes(out3["errors"]) == [BAD_HEADER], out3["errors"]

    def case_unknown_cell() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "o_la.xlsx"
            _write_phieu(path, stray={"C5": "phần thừa khách gõ"})
            out = import_questionnaire(path, questionnaire)
            assert out["ok"] is False and out["data"] is None, out
            assert _codes(out["errors"]) == [UNKNOWN_CELL], out["errors"]
            assert out["errors"][0]["cell"] == "C5", out["errors"]

    def case_required_and_select() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thieu_va_sai.xlsx"
            _write_phieu(path, overrides={
                "q_ten_tieng_viet": None,               # required trống
                "q_loai_hinh": "Công ty cổ phần 123",   # không có trong options
            })
            out = import_questionnaire(path, questionnaire)
            assert out["ok"] is False and out["data"] is None, out
            codes = _codes(out["errors"])
            assert MISSING_REQUIRED in codes, out["errors"]
            assert BAD_SELECT in codes, out["errors"]
            miss = [e for e in out["errors"] if e["code"] == MISSING_REQUIRED]
            assert [e["question_id"] for e in miss] == ["q_ten_tieng_viet"], miss
            assert miss[0]["cell"], miss

    def case_bad_date_number() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sai_dinh_dang.xlsx"
            _write_phieu(path, overrides={
                "q_ngay_sinh": "32/13/2020",   # ngày không có thật
                "q_von": "năm triệu",          # không parse được
            })
            out = import_questionnaire(path, questionnaire)
            assert out["ok"] is False and out["data"] is None, out
            codes = _codes(out["errors"])
            assert BAD_DATE in codes, out["errors"]
            assert BAD_NUMBER in codes, out["errors"]

    def case_bad_version() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sai_version.xlsx"
            _write_phieu(path, version=2)
            out = import_questionnaire(path, questionnaire)
            assert out["ok"] is False and out["data"] is None, out
            assert _codes(out["errors"]) == [BAD_VERSION], out["errors"]
            assert "questionnaire_version" in out["errors"][0]["message"], out

    check("[X3a] phiếu tốt DNTN -> data phẳng + bảng nganh 2 hàng", case_good)
    check("[X3b] sai khung (thiếu map / header lạ / không phải xlsx) -> BAD_HEADER",
          case_bad_header)
    check("[X3c] ô lạ ngoài vùng điền -> UNKNOWN_CELL", case_unknown_cell)
    check("[X3d] required trống + select sai giá trị -> MISSING_REQUIRED + "
          "BAD_SELECT", case_required_and_select)
    check("[X3e] ngày/số sai định dạng -> BAD_DATE + BAD_NUMBER",
          case_bad_date_number)
    check("[X3f] questionnaire_version lệch -> BAD_VERSION", case_bad_version)

    passed = sum(1 for ok, _ in results if ok)
    failed = len(results) - passed
    print("-" * 64)
    print("excel_import selftest: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return _selftest()
    print("Dùng: python3 -X utf8 -m tools.excel_import --selftest")
    return 2


if __name__ == "__main__":
    sys.exit(main())
