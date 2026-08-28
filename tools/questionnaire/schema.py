# -*- coding: utf-8 -*-
"""Schema questionnaire v1 (PLAN.md mục 4 — luồng Excel, wave X1).

Questionnaire = phiếu thu thập thông tin ĐỐI MẶT KHÁCH, KHÔNG phải bản sao
biểu mẫu pháp lý. Mỗi file questionnaire thuộc MỘT thủ tục (doc_id) và mô tả
các câu hỏi đời thường + ánh xạ `question_id -> data_key` để app tự điền biểu
mẫu (X3). KHUNG sinh tự động từ form_maps/registry; NỘI DUNG câu hỏi là sản
phẩm (Lead soạn, owner duyệt từng cụm — owner duyệt cụm đầu 2026-08-28).

Nguyên tắc bất biến:
- Một câu hỏi một ý; mỗi câu PHẢI có `data_key` trỏ vào key có thật của
  form_maps (hoặc SELECTOR_ALLOW) — thiếu/sai key = fail build (fail-loud).
- Mapping per-procedure: file theo doc_id, key resolve trong phạm vi doc đó
  (bài học P4.1: 138 key flat vs 243 prefixed — cấm map key toàn cục).
- Question thay đổi phải bump `version` (câu hỏi gắn version theo PLAN 4.5).
- `when` trên target = điều kiện bật câu theo câu trả lời khác trong cùng
  phiếu (ví dụ theo loại hình `dn.loai_hinh`) — cùng idiom activeWhen runtime
  (valueOf/equals), so sau trim, phân biệt hoa/thường.
"""
from __future__ import annotations

import json
from pathlib import Path

# Key metadata hồ sơ/app được phép hỏi dù không nằm trong form_maps.fields
# (nó không in ra văn bản nhưng quyết định variant hiển thị — D-M72-ACT
# Option D, FORM_SELECTOR_META form-domain.js:630).
SELECTOR_ALLOW = {
    "dn.loai_hinh",
}

TYPES = {"text", "select", "money", "integer", "date", "tel", "email", "mark"}
TRANSFORMS = {None, "date_day", "date_month", "date_year"}
AUTOFILLS = {None, "vsic"}  # ô xám "app tự làm" theo quy ước màu PLAN 4.3

FILE_VERSION = 1


class QuestionnaireError(ValueError):
    """Lỗi cấu trúc/registry questionnaire — builder import phải fail-loud."""

    def __init__(self, code: str, message: str):
        super().__init__("[%s] %s" % (code, message))
        self.code = code


def _registry_keys(form_maps: dict, doc_id: str) -> set:
    entry = (form_maps or {}).get(doc_id)
    if not entry:
        raise QuestionnaireError(
            "DOC_NOT_FOUND", "form_maps.json không có %r" % doc_id)
    return {f.get("key") for f in entry.get("fields", []) if f.get("key")}


def validate(q: dict, form_maps: dict) -> list[str]:
    """Kiểm tra questionnaire `q` đối chiếu registry `form_maps`.

    Trả về danh sách cảnh báo (không chặn); lỗi cấu trúc raise
    QuestionnaireError. Được test_questionnaire gọi trực tiếp cho negative.
    """
    warnings: list[str] = []
    if not isinstance(q, dict):
        raise QuestionnaireError("NOT_OBJECT", "questionnaire phải là object")
    for field in ("doc_id", "title", "questionnaire_version", "questions"):
        if field not in q:
            raise QuestionnaireError("MISSING_FIELD", "thiếu %r" % field)
    if q["questionnaire_version"] != FILE_VERSION:
        raise QuestionnaireError(
            "BAD_VERSION", "questionnaire_version=%r không hỗ trợ"
            % (q["questionnaire_version"],))
    questions = q["questions"]
    if not isinstance(questions, list) or not questions:
        raise QuestionnaireError("NO_QUESTIONS", "questions rỗng")

    allowed = _registry_keys(form_maps, q["doc_id"])
    by_id: dict[str, dict] = {}
    row_groups: dict[str, list[str]] = {}
    for item in questions:
        if not isinstance(item, dict):
            raise QuestionnaireError("BAD_QUESTION", "question phải là object")
        for field in ("question_id", "group", "text", "type", "version",
                      "data_key"):
            if field not in item:
                raise QuestionnaireError(
                    "MISSING_FIELD", "%s: thiếu %r"
                    % (item.get("question_id", "?"), field))
        qid = item["question_id"]
        if qid in by_id:
            raise QuestionnaireError("DUP_ID", "question_id trùng: %r" % qid)
        by_id[qid] = item
        if item["type"] not in TYPES:
            raise QuestionnaireError(
                "BAD_TYPE", "%s: type lạ %r" % (qid, item["type"]))
        if not isinstance(item["version"], int) or item["version"] < 1:
            raise QuestionnaireError("BAD_VERSION", "%s: version phải ≥1" % qid)
        if item["type"] == "select":
            if not item.get("options"):
                raise QuestionnaireError(
                    "NO_OPTIONS", "%s: select phải có options" % qid)
        if item.get("autofill") not in AUTOFILLS:
            raise QuestionnaireError(
                "BAD_AUTOFILL", "%s: autofill lạ %r" % (qid, item["autofill"]))

        def check_target(t: dict) -> None:
            if not isinstance(t, dict) or not t.get("key"):
                raise QuestionnaireError(
                    "NO_DATA_KEY", "%s: target thiếu key — câu hỏi không có "
                    "data-key = fail build (PLAN X1)" % qid)
            key = t["key"]
            if key not in allowed and key not in SELECTOR_ALLOW:
                raise QuestionnaireError(
                    "KEY_NOT_IN_REGISTRY",
                    "%s: data_key %r không có trong form_maps[%s]"
                    % (qid, key, q["doc_id"]))
            if t.get("transform") not in TRANSFORMS:
                raise QuestionnaireError(
                    "BAD_TRANSFORM", "%s: transform lạ %r"
                    % (qid, t.get("transform")))
            for cond_key, equals in (t.get("when") or {}).items():
                if cond_key not in SELECTOR_ALLOW and \
                        cond_key not in {i2.get("data_key") for i2 in questions
                                         if isinstance(i2.get("data_key"), str)}:
                    ref = [
                        i2["question_id"] for i2 in questions
                        if isinstance(i2.get("data_key"), str)
                        and i2["data_key"] == cond_key]
                    if not ref:
                        raise QuestionnaireError(
                            "BAD_WHEN", "%s: when %r không trỏ câu hỏi nào "
                            "trong phiếu" % (qid, cond_key))
                if not isinstance(equals, list) or not equals:
                    raise QuestionnaireError(
                        "BAD_WHEN", "%s: when %r phải là list giá trị"
                        % (qid, cond_key))

        dk = item["data_key"]
        if isinstance(dk, str):
            check_target({"key": dk})
        elif isinstance(dk, list):
            if not dk:
                raise QuestionnaireError(
                    "NO_DATA_KEY", "%s: data_key rỗng" % qid)
            for t in dk:
                check_target(t)
        else:
            raise QuestionnaireError(
                "BAD_DATA_KEY", "%s: data_key phải là string hoặc list" % qid)

        rg = item.get("row_group")
        if rg is not None:
            if not isinstance(rg, str) or not rg:
                raise QuestionnaireError("BAD_ROW_GROUP", "%s: row_group" % qid)
            row_groups.setdefault(rg, []).append(qid)

    for rg, qids in row_groups.items():
        if len(qids) < 2:
            warnings.append(
                "row_group %r chỉ có 1 câu (%s) — cân nhắc gộp thành dòng"
                % (rg, qids[0]))
    return warnings


def load_form_maps(root: Path) -> dict:
    return json.loads(
        (root / "app" / "data" / "form_maps.json").read_text(encoding="utf-8"))
