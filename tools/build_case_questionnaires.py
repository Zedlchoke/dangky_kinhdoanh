# -*- coding: utf-8 -*-
"""Builder manifest questionnaire CASE-LEVEL — wave E0 (PLAN_hoan_thien_phat_hanh §2.1, §5-E0).

Sinh `app/data/case_questionnaires/<caseId>.json` TỪ ba nguồn đã có:

  1. `app/data/use_cases.json`   — 28 case, mỗi case tham chiếu form dạng
     `{'pl':'I','mau':12,...}` -> form_id `PLI_M12` (đúng idiom
     `schema_forms` đọc bởi app_web/ui/app.js).
  2. `app/data/form_maps.json`   — registry form (ten_mau, fields); chỉ dùng
     để KIỂM tra form tồn tại, KHÔNG bao giờ sửa.
  3. `app/data/questionnaire/<form_id>.json` — 7 questionnaire form-level
     (wave X1) đã được owner duyệt nội dung.

Manifest có: `manifest_id`/`manifest_version`/`manifest_hash` (sha256 payload
canonical không gồm hash), `schema_version` (schema câu hỏi = v1),
`content_review` PER FORM:

- `approved`  — 7 form wave X1, owner duyệt nguyên văn (không chỉnh sửa).
- `owner_delegated_2026-09-10` — wave E4/E5: questionnaire sinh bởi
  `tools.build_form_questionnaires` theo ủy quyền "tôi duyệt và chốt hết"
  của owner ngày 2026-09-10; được ĐỐI XỬ NHƯ approved ở mọi gate.
- `pending`   — form CHƯA có questionnaire: manifest VẪN liệt kê form
  (bat_buoc/ghi_chu từ use case) nhưng `questions: []` — KHÔNG TỰ SÁNG TÁC
  nội dung pháp lý. Workbook của case có form pending bị CHẶN phát hành
  (E4) nhưng vẫn sinh đủ manifest để pilot nội bộ.

Wave E4: builder còn NHÚNG vào manifest hai loại câu SELECTOR (pseudo-key,
không thuộc form_maps — exporter/importer nhận diện theo prefix):
- `oneOf.<n>`  — câu select bắt buộc "Trường hợp hồ sơ của bạn là trường hợp
  nào?" cho mỗi nhóm `forms_oneOf` (chọn 1 trong các mẫu, vd M01–M04 khi
  chuyển đổi HKD sang DN); value = form_id được chọn.
- `optionalForm.<form_id>` — câu mark "Có làm mẫu này không?" cho form
  bat_buoc=false NGOÀI nhóm oneOf; đánh X mới đưa form vào checkedForms.

Migration read-only: builder KHÔNG đụng 7 questionnaire cũ lẫn API cũ
(`tools.excel_export.write_questionnaire` /
`tools.excel_import.import_questionnaire`) — backward-compat được test ở
`tools.test_case_questionnaires`.

Fail-loud (exit 1, KHÔNG ghi artifact): form không có trong form_maps
(DOC_NOT_FOUND), questionnaire tồn tại nhưng sai schema (QuestionnaireError),
question_id trùng GIỮA CÁC FORM trong cùng case (DUP_ID — importer case-level
đòi question_id duy nhất toàn case), thiếu 'forms' trong case.

Chạy (từ ROOT):
  python3 -X utf8 -m tools.build_case_questionnaires            # sinh hết
  python3 -X utf8 -m tools.build_case_questionnaires --check    # chỉ kiểm
  python3 -X utf8 -m tools.build_case_questionnaires --one thanh_lap_dntn
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.questionnaire.schema import (  # noqa: E402
    FILE_VERSION, QuestionnaireError, load_form_maps, validate)

USE_CASES = ROOT / "app" / "data" / "use_cases.json"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
QUESTIONNAIRE_DIR = ROOT / "app" / "data" / "questionnaire"
OUT_DIR = ROOT / "app" / "data" / "case_questionnaires"

MANIFEST_VERSION = 1
INDEX_NAME = "_index.json"

# --- Wave E4/E5 (owner ủy quyền nội dung 2026-09-10) ------------------------
# Hai mức "đủ điều kiện phát hành": `approved` (7 questionnaire wave X1,
# owner duyệt từng cụm) và `owner_delegated_2026-09-10` (nội dung sinh bởi
# tools.build_form_questionnaires theo ủy quyền "tôi duyệt và chốt hết" của
# owner ngày 2026-09-10) — cả hai đều được đối xử như approved ở mọi gate.
REVIEW_APPROVED = "approved"
REVIEW_DELEGATED = "owner_delegated_2026-09-10"
REVIEW_PENDING = "pending"
APPROVED_EQUIV = (REVIEW_APPROVED, REVIEW_DELEGATED)
# 7 questionnaire wave X1 owner duyệt nguyên văn — giữ review "approved"
LEGACY_APPROVED_FORMS = {
    "PLII_M01", "PLII_M02", "PLII_M03", "PLII_M04",
    "PLI_M12", "PLI_M27", "PLI_M72",
}
# prefix data_key của câu SELECTOR do builder NHÚNG (không thuộc form_maps):
# `oneOf.<n>` = chọn một mẫu trong nhóm forms_oneOf[n];
# `optionalForm.<form_id>` = tick "có làm mẫu tùy chọn này không".
# (hợp đồng với excel_case_export/import — đổi một bên phải đồng bộ bên kia.)
ONEOF_KEY_PREFIX = "oneOf."
OPTIONAL_FORM_KEY_PREFIX = "optionalForm."
ONEOF_GROUP_NAME = "Trường hợp hồ sơ"
OPTIONAL_FORM_GROUP_NAME = "Các mẫu tùy chọn trong hồ sơ"


def oneof_questions(case_id: str, groups: list, form_entries: dict) -> list:
    """Câu select "Trường hợp hồ sơ của bạn là trường hợp nào?" cho MỖI nhóm
    forms_oneOf — Lead chốt design E4: câu select bắt buộc đầu sheet
    `Thông_tin_chung`; option label = ghi_chu (thân thiện) fallback ten_mau;
    value = form_id (importer đọc value -> checkedForms)."""
    out: list = []
    for index, group in enumerate(groups or [], start=1):
        ids = [str(fid) for fid in (group.get("ids") or [])]
        if not ids:
            continue
        options = []
        for fid in ids:
            entry = form_entries.get(fid) or {}
            label = str(entry.get("ghi_chu") or entry.get("ten_mau")
                        or fid).strip()
            options.append({"value": fid, "label": label})
        out.append({
            "question_id": "q_oneof_%d" % index,
            "group": ONEOF_GROUP_NAME,
            "text": "Trường hợp hồ sơ của bạn là trường hợp nào? "
                    "(chọn MỘT dòng ▾)",
            "type": "select",
            "options": options,
            "required": True,
            "version": 1,
            "data_key": "%s%d" % (ONEOF_KEY_PREFIX, index),
        })
    return out


def optional_form_question(form_id: str, form_entries: dict) -> dict:
    """Câu mark "Có làm mẫu này không?" cho form TÙY CHỌN NGOÀI oneOf
    (bat_buoc=false) — đánh X mới đưa form vào checkedForms."""
    entry = form_entries.get(form_id) or {}
    name = str(entry.get("ghi_chu") or entry.get("ten_mau") or form_id)
    return {
        "question_id": "q_opt_%s" % form_id,
        "group": OPTIONAL_FORM_GROUP_NAME,
        "text": "Bạn có làm mẫu «%s» không? (đánh X nếu CÓ làm mẫu này)"
                % name,
        "type": "mark",
        "options": [{"value": "X", "label": "Có"}],
        "version": 1,
        "data_key": "%s%s" % (OPTIONAL_FORM_KEY_PREFIX, form_id),
    }


class CaseManifestError(ValueError):
    """Lỗi nguồn khi sinh manifest case — fail-loud, cùng idiom X1."""

    def __init__(self, code: str, message: str):
        super().__init__("[%s] %s" % (code, message))
        self.code = code


def form_id_of(form_ref: dict) -> str:
    """`{'pl':'I','mau':12}` -> 'PLI_M12' (đúng contract schema_forms)."""
    pl = str(form_ref.get("pl") or "").strip().upper()
    mau = form_ref.get("mau")
    if pl not in ("I", "II") or not isinstance(mau, int) or mau < 0:
        raise CaseManifestError(
            "BAD_FORM_REF", "form ref lạ: %r" % (form_ref,))
    return "PL%s_M%02d" % (pl, mau)


def canonical_json(payload: dict) -> str:
    """Chuỗi canonical dùng để hash — sort key, ASCII, không khoảng trắng thừa."""
    return json.dumps(payload, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"))


def manifest_hash(payload: dict) -> str:
    """sha256 hex của manifest KHÔNG gồm trường `manifest_hash`."""
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _load_questionnaire(doc_id: str, form_maps: dict) -> dict | None:
    """Đọc questionnaire form-level nếu có; sai schema = fail-loud."""
    path = QUESTIONNAIRE_DIR / ("%s.json" % doc_id)
    if not path.exists():
        return None
    try:
        q = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CaseManifestError(
            "BAD_JSON", "%s: questionnaire không parse được (%s)"
            % (doc_id, type(exc).__name__))
    if q.get("doc_id") != doc_id:
        raise CaseManifestError(
            "DOC_MISMATCH", "%s: file khai báo doc_id=%r" % (doc_id, q.get("doc_id")))
    # schema v1 validate đối chiếu registry — sai key/type/when = fail build
    validate(q, form_maps)
    return q


def build_manifest(case: dict, form_maps: dict) -> dict:
    """Một case (dict trong use_cases.json) -> manifest case-level."""
    case_id = case.get("id")
    if not case_id or not isinstance(case_id, str):
        raise CaseManifestError("BAD_CASE", "case thiếu 'id': %r" % (case,))
    refs = case.get("forms")
    if not isinstance(refs, list) or not refs:
        raise CaseManifestError("NO_FORMS", "%s: case không có forms" % case_id)

    # question_id phải DUY NHẤT toàn case (importer case-level tra theo qid)
    seen_qids: set[str] = set()
    forms_out: list[dict] = []
    for ref in refs:
        fid = form_id_of(ref)
        entry = form_maps.get(fid)
        if not entry:
            raise CaseManifestError(
                "DOC_NOT_FOUND", "%s: form %s không có trong form_maps.json"
                % (case_id, fid))
        q = _load_questionnaire(fid, form_maps)
        # bat_buoc mặc định TRUE theo contract schema_forms (thiếu coi như true)
        bat_buoc = ref.get("bat_buoc")
        bat_buoc = True if bat_buoc is None else bool(bat_buoc)
        if q is None:
            # form chưa có questionnaire: liệt kê nhưng KHÔNG sáng tác câu hỏi
            forms_out.append({
                "form_id": fid,
                "ten_mau": entry.get("ten_mau") or fid,
                "bat_buoc": bat_buoc,
                "ghi_chu": ref.get("ghi_chu") or "",
                "questionnaire_version": None,
                "cluster": None,
                "title": entry.get("ten_mau") or fid,
                "content_review": REVIEW_PENDING,
                "questions": [],
            })
            continue
        for item in q.get("questions", []):
            qid = item.get("question_id")
            if qid in seen_qids:
                raise CaseManifestError(
                    "DUP_ID", "%s: question_id %r trùng giữa các form"
                    % (case_id, qid))
            seen_qids.add(qid)
        forms_out.append({
            "form_id": fid,
            "ten_mau": entry.get("ten_mau") or fid,
            "bat_buoc": bat_buoc,
            "ghi_chu": ref.get("ghi_chu") or "",
            "questionnaire_version": q.get("questionnaire_version"),
            "cluster": q.get("cluster"),
            "title": q.get("title") or entry.get("ten_mau") or fid,
            "content_review": REVIEW_APPROVED if fid in LEGACY_APPROVED_FORMS
            else REVIEW_DELEGATED,
            "questions": list(q.get("questions", [])),
        })

    # --- Wave E4: nhúng câu selector oneOf + câu mark form tùy chọn --------
    # Câu pseudo-key (oneOf.*, optionalForm.*) KHÔNG thuộc form_maps — chỉ
    # sinh tại đây (builder), exporter/importer nhận diện theo prefix.
    groups = list(case.get("forms_oneOf") or [])
    form_entries = {f["form_id"]: f for f in forms_out}
    if groups:
        for item in oneof_questions(case_id, groups, form_entries):
            first_fid = (groups[int(item["data_key"].split(".")[1]) - 1]
                         .get("ids") or [None])[0]
            if item["question_id"] in seen_qids:
                raise CaseManifestError(
                    "DUP_ID", "%s: question_id %r trùng giữa các form"
                    % (case_id, item["question_id"]))
            seen_qids.add(item["question_id"])
            if first_fid in form_entries:
                form_entries[first_fid]["questions"].insert(0, dict(item))
    oneof_ids = {fid for g in groups for fid in (g.get("ids") or [])}
    for form in forms_out:
        if form["bat_buoc"] or form["form_id"] in oneof_ids:
            continue
        item = optional_form_question(form["form_id"], form_entries)
        if item["question_id"] in seen_qids:
            raise CaseManifestError(
                "DUP_ID", "%s: question_id %r trùng giữa các form"
                % (case_id, item["question_id"]))
        seen_qids.add(item["question_id"])
        form["questions"].append(item)

    manifest = {
        "manifest_id": case_id,
        "manifest_version": MANIFEST_VERSION,
        "schema_version": FILE_VERSION,
        "case_id": case_id,
        "case_title": case.get("ten") or case_id,
        "nhom": case.get("nhom") or "",
        "mo_ta": case.get("mo_ta") or "",
        "co_so_phap_ly": list(case.get("co_so_phap_ly") or []),
        "luu_y": list(case.get("luu_y") or []),
        "giay_to_kem": list(case.get("giay_to_kem") or []),
        "forms_oneOf": list(case.get("forms_oneOf") or []),
        "forms": forms_out,
    }
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def build_all(write: bool, only: str | None = None) -> list[dict]:
    """Sinh (hoặc kiểm) manifest cho mọi case. Trả list index-entry."""
    cases = json.loads(USE_CASES.read_text(encoding="utf-8"))["cases"]
    form_maps = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    if only:
        cases = [c for c in cases if c.get("id") == only]
        if not cases:
            raise CaseManifestError("NO_CASE", "không có case %r" % only)

    index: list[dict] = []
    for case in cases:
        manifest = build_manifest(case, form_maps)
        out_path = OUT_DIR / ("%s.json" % manifest["case_id"])
        payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if write:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path.write_text(payload, encoding="utf-8")
        elif out_path.exists() and out_path.read_text(encoding="utf-8") != payload:
            raise CaseManifestError(
                "DRIFT", "%s: artifact khác build hiện tại (chạy không --check)"
                % manifest["case_id"])
        approved = [f["form_id"] for f in manifest["forms"]
                    if f["content_review"] in APPROVED_EQUIV]
        pending = [f["form_id"] for f in manifest["forms"]
                   if f["content_review"] == REVIEW_PENDING]
        delegated = [f["form_id"] for f in manifest["forms"]
                     if f["content_review"] == REVIEW_DELEGATED]
        index.append({
            "case_id": manifest["case_id"],
            "case_title": manifest["case_title"],
            "manifest_hash": manifest["manifest_hash"],
            "n_forms": len(manifest["forms"]),
            "approved_forms": approved,
            "pending_forms": pending,
            "delegated_forms": delegated,
            "all_approved": not pending,
        })

    if write:
        (OUT_DIR / INDEX_NAME).write_text(
            json.dumps({
                "generated_by": "tools.build_case_questionnaires",
                "cases": index,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one", help="chỉ build case này (case_id)")
    ap.add_argument("--check", action="store_true",
                    help="chỉ kiểm tra artifact khớp build, không ghi")
    args = ap.parse_args(argv)
    try:
        index = build_all(write=not args.check, only=args.one)
    except (CaseManifestError, QuestionnaireError) as exc:
        print("FAIL %s" % exc, file=sys.stderr)
        return 1
    ready = sum(1 for e in index if e["all_approved"])
    action = "KIỂM" if args.check else "SINH"
    print("%s OK %d manifest case (%d case READY — approved hoặc delegated "
          "%s, %d chờ content review) -> %s"
          % (action, len(index), ready, REVIEW_DELEGATED,
             len(index) - ready, OUT_DIR))
    for e in index:
        flag = "READY" if e["all_approved"] else "PENDING"
        print("  [%s] %s: %s" % (flag, e["case_id"],
                                 ", ".join(e["pending_forms"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
