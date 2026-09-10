# -*- coding: utf-8 -*-
"""E0 — manifest questionnaire case-level: build + migration read-only
(PLAN_hoan_thien_pfat_hanh §5-E0).

[CQ1] Builder sinh đủ 28 manifest case (mỗi case 1 file) + `_index.json`.
[CQ2] 9 case đủ điều kiện E1/E2 (mọi form có questionnaire -> approved),
      19 case còn lại pending: form pending `questions: []`, KHÔNG tự sáng
      tác nội dung; form approved `questions` không rỗng.
[CQ3] Hash tự-consistent + deterministic: tính lại sha256 canonical của
      manifest (bỏ `manifest_hash`) == `manifest_hash` đã lưu; chạy builder
      lần nữa (không ghi) không báo DRIFT.
[CQ4] Migration read-only: 7 questionnaire form-level cũ KHÔNG bị đụng —
      vẫn schema-validate pass đối chiếu form_maps; API cũ
      excel_export.write_questionnaire / excel_import.import_questionnaire
      vẫn hoạt động đúng contract (phiếu trắng -> ok=False MISSING_REQUIRED,
      không data một phần).
[CQ5] Fail-loud builder: form không có trong form_maps (DOC_NOT_FOUND),
      form ref sai (BAD_FORM_REF) — không ghi artifact.
[CQ6] `_index.json` khớp manifest: đủ case, `all_approved` đúng dấu.

Chạy:  python3 -X utf8 -m tools.test_case_questionnaires   (exit 0 = PASS)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_case_questionnaires import (  # noqa: E402
    INDEX_NAME, CaseManifestError, OUT_DIR, build_all, build_manifest,
    form_id_of, manifest_hash,
)
from tools.questionnaire.schema import load_form_maps, validate  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def _on_disk(case_id: str) -> dict:
    return json.loads(
        (OUT_DIR / ("%s.json" % case_id)).read_text(encoding="utf-8"))


def _index() -> dict:
    return json.loads((OUT_DIR / INDEX_NAME).read_text(encoding="utf-8"))


@check("[CQ1] đủ 28 manifest case + _index.json, khung manifest đúng trường")
def cq1():
    cases = json.loads(
        (ROOT / "app" / "data" / "use_cases.json").read_text(encoding="utf-8")
    )["cases"]
    files = sorted(p.stem for p in OUT_DIR.glob("*.json")
                   if p.stem != "_index")
    assert files == sorted(c["id"] for c in cases), \
        "thiếu/thừa manifest: %s" % set(files) ^ set(c["id"] for c in cases)
    assert (OUT_DIR / INDEX_NAME).exists(), "thiếu _index.json"
    for case_id in files:
        m = _on_disk(case_id)
        for field in ("manifest_id", "manifest_version", "schema_version",
                      "case_id", "case_title", "forms", "manifest_hash",
                      "co_so_phap_ly", "giay_to_kem"):
            assert field in m, "%s: thiếu %r" % (case_id, field)
        assert m["manifest_id"] == m["case_id"] == case_id
        for form in m["forms"]:
            for field in ("form_id", "ten_mau", "bat_buoc", "ghi_chu",
                          "content_review", "questions"):
                assert field in form, \
                    "%s/%s: thiếu %r" % (case_id, form.get("form_id"), field)
            assert form["content_review"] in ("approved", "pending")
            assert (form["content_review"] == "approved") == \
                bool(form["questions"]), \
                "%s/%s: approved/pending lệch questions" % (
                    case_id, form["form_id"])


@check("[CQ2] đúng 9 case READY (E1/E2) — form pending questions rỗng")
def cq2():
    ready = sorted(e["case_id"] for e in _index()["cases"]
                   if e["all_approved"])
    assert ready == sorted([
        "dang_ky_ho_kinh_doanh_lan_dau",
        "thay_doi_ten_va_tru_so",
        "thay_doi_nganh_nghe",
        "thay_doi_von_dieu_le",
        "thay_doi_noi_dung_dang_ky_hkd",
        "tam_ngung_tiep_tuc_kinh_doanh_dn",
        "tam_ngung_tiep_tuc_kinh_doanh_hkd",
        "cham_dut_hoat_dong_hkd",
        "bo_sung_cap_nhat_thong_tin_dkdn",
    ]), ready
    index = _index()
    assert len(index["cases"]) == 28, len(index["cases"])
    assert sum(1 for e in index["cases"] if not e["all_approved"]) == 19
    # spot-check hai đầu: READY đủ câu, pending rỗng và có ghi chú form
    m = _on_disk("dang_ky_ho_kinh_doanh_lan_dau")
    assert m["forms"][0]["form_id"] == "PLII_M01"
    assert m["forms"][0]["content_review"] == "approved"
    assert len(m["forms"][0]["questions"]) >= 30
    m2 = _on_disk("thanh_lap_dntn")
    assert m2["forms"][0]["form_id"] == "PLI_M01"
    assert m2["forms"][0]["content_review"] == "pending"
    assert m2["forms"][0]["questions"] == []
    assert m2["forms"][0]["bat_buoc"] is True          # từ use case
    assert m2["forms"][0]["ghi_chu"], "pending vẫn giữ ghi_chu use case"


@check("[CQ3] hash manifest tự-consistent + build lại không DRIFT")
def cq3():
    cases = json.loads(
        (ROOT / "app" / "data" / "use_cases.json").read_text(encoding="utf-8")
    )["cases"]
    form_maps = load_form_maps(ROOT)
    for case in cases:
        rebuilt = build_manifest(case, form_maps)
        stored = _on_disk(case["id"])
        assert manifest_hash(rebuilt) == rebuilt["manifest_hash"], \
            "%s: hash không khớp payload" % case["id"]
        assert rebuilt == stored, "%s: build lại lệch artifact" % case["id"]
    # build_all(write=False) == chế độ --check: DRIFT sẽ raise
    build_all(write=False)


@check("[CQ4] migration read-only: 7 questionnaire cũ nguyên vẹn + API cũ chạy")
def cq4():
    form_maps = load_form_maps(ROOT)
    qdir = ROOT / "app" / "data" / "questionnaire"
    docs = sorted(p.stem for p in qdir.glob("*.json"))
    assert docs == ["PLII_M01", "PLII_M02", "PLII_M03", "PLII_M04",
                    "PLI_M12", "PLI_M27", "PLI_M72"], docs
    for doc in docs:
        q = json.loads((qdir / ("%s.json" % doc)).read_text(encoding="utf-8"))
        assert q["doc_id"] == doc
        validate(q, form_maps)          # sai schema sẽ raise QuestionnaireError
        assert q["questionnaire_version"] == 1
    # API cũ xuất/nạp phiếu theo doc_id vẫn hoạt động (PLII_M03 — phiếu nhỏ)
    from tools.excel_export import write_questionnaire
    from tools.excel_import import BAD_HEADER, import_questionnaire

    q = json.loads((qdir / "PLII_M03.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        path = write_questionnaire(q, Path(tmp) / "phieu.xlsx")
        res = import_questionnaire(path, q)   # phiếu trắng -> thiếu bắt buộc
        assert res["ok"] is False and res["data"] is None, res
        codes = {e["code"] for e in res["errors"]}
        assert "MISSING_REQUIRED" in codes, codes
        # file không phải phiếu -> BAD_HEADER, vẫn contract cũ
        junk = Path(tmp) / "junk.xlsx"
        junk.write_text("khong phai xlsx", encoding="utf-8")
        res2 = import_questionnaire(junk, q)
        assert res2["ok"] is False and \
            res2["errors"][0]["code"] == BAD_HEADER, res2


@check("[CQ5] fail-loud: form lạ trong use case -> DOC_NOT_FOUND / BAD_FORM_REF")
def cq5():
    form_maps = load_form_maps(ROOT)
    try:
        build_manifest({"id": "case_ma", "forms": [{"pl": "I", "mau": 99}]},
                       form_maps)
        raise AssertionError("phải raise DOC_NOT_FOUND")
    except CaseManifestError as exc:
        assert exc.code == "DOC_NOT_FOUND", exc.code
    try:
        build_manifest({"id": "case_ma2",
                        "forms": [{"pl": "III", "mau": 1}]}, form_maps)
        raise AssertionError("phải raise BAD_FORM_REF")
    except CaseManifestError as exc:
        assert exc.code == "BAD_FORM_REF", exc.code
    # form_id_of đúng contract schema_forms
    assert form_id_of({"pl": "I", "mau": 12}) == "PLI_M12"
    assert form_id_of({"pl": "II", "mau": 4}) == "PLII_M04"


@check("[CQ6] _index.json khớp manifest từng case")
def cq6():
    index = _index()
    assert index["generated_by"] == "tools.build_case_questionnaires"
    for entry in index["cases"]:
        m = _on_disk(entry["case_id"])
        assert entry["manifest_hash"] == m["manifest_hash"], entry["case_id"]
        approved = [f["form_id"] for f in m["forms"]
                    if f["content_review"] == "approved"]
        pending = [f["form_id"] for f in m["forms"]
                   if f["content_review"] == "pending"]
        assert entry["approved_forms"] == approved, entry["case_id"]
        assert entry["pending_forms"] == pending, entry["case_id"]
        assert entry["all_approved"] == (not pending), entry["case_id"]
        assert entry["n_forms"] == len(m["forms"]), entry["case_id"]


def main() -> int:
    for fn in (cq1, cq2, cq3, cq4, cq5, cq6):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_case_questionnaires: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
