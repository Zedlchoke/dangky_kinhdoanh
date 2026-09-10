# -*- coding: utf-8 -*-
"""E4/E5 — SELF-CHECK PHỦ KEY cho TOÀN BỘ questionnaire form-level.

Rủi ro số 1 của luồng Excel case-level là `data_key` LỆCH form_maps (dữ liệu
không vào được DOCX). Test này là rào fail-loud độc lập với generator:

[CV1]  MỖI form được ≥1 case tham chiếu đều CÓ file questionnaire; mọi file
       validate schema v1 đối chiếu form_maps (sai key/type = raise).
[CV2]  PHỦ KEY: mọi key fillable của form (fields + dynamic_tables loop.tag)
       trừ bộ EXCLUDED có tài liệu hóa (khối đầu thư app tự điền, cột chữ ký
       giấy, cột phản chiếu hồ sơ cũ) phải được ≥1 câu hỏi nhắm tới — thiếu
       key nào, in đúng key đó và FAIL (generator build_form_questionnaires
       dùng cùng bộ loại trừ — hai bên phải luôn khớp).
[CV3]  Ô NHÍP (mark/select) luôn có options; câu mark không có options thì
       importer sẽ BAD_SELECT khi khách điền 'X'.
[CV4]  Không key nào bị HAI câu hỏi khác nhắm trùng (trong cùng form) — trùng
       sẽ sinh hai ô nhập cho một ô DOCX.
[CV5]  Generator dựng lại (build_one) từng file khớp artifact (payload)
       — không drift giữa file đã ghi và generator hiện hành.
[CV6]  required chỉ nằm trong tập cho phép (tiền lệ X1/validator runtime) —
       chặn `required: true` bừa gây MISSING_REQUIRED oan phiếu trắng.

Chạy:  python3 -X utf8 -m tools.test_questionnaire_coverage  (exit 0 = PASS)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_form_questionnaires import (  # noqa: E402
    EXCLUDED_KEYS, EXCLUDED_SUFFIXES, FORMS, GenError, build_one,
    coverage_of,
)
from tools.questionnaire.schema import validate  # noqa: E402

QDIR = ROOT / "app" / "data" / "questionnaire"
USE_CASES = ROOT / "app" / "data" / "use_cases.json"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"

# `required` hợp lệ — tiền lệ 7 questionnaire X1 + validator runtime
REQUIRED_ALLOWED_EXACT = {
    "dn.ten_tieng_viet", "dn.ma_so_dn", "dn.dia_chi_tru_so",
    "chu_hkd.ho_ten", "chu_hkd.so_cccd", "ho_ten_in_hoa",
    "chu_so_huu.ho_ten", "ndd.ho_ten", "ndd.so_cccd",
    "cn.ten_tieng_viet", "cn.ma_so",
    "dia_chi_chi_tiet", "xa_phuong", "tinh_thanh",
    "hkd_ten_tieng_viet", "hkd_ten_tieng_viet_2", "hkd_ma_so",
    "hkd_dia_chi", "diachi", "xa_phuong_hkd", "tinh_thanh_hkd",
    "von_kinh_doanh", "dn.loai_hinh",   # X1: selector variant (SELECTOR_ALLOW)
}
REQUIRED_ALLOWED_TABLE_FIRST = {
    "ho_ten", "ten_nganh", "ten_cd", "ten_thanh_vien",
}

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


def _cases() -> list[dict]:
    return json.loads(USE_CASES.read_text(encoding="utf-8"))["cases"]


def _form_maps() -> dict:
    return json.loads(FORM_MAPS.read_text(encoding="utf-8"))


def _referenced_forms() -> set[str]:
    out = set()
    for c in _cases():
        for r in c.get("forms", []):
            out.add("PL%s_M%02d" % (r.get("pl"), r.get("mau")))
    return out


def _keys_of_question(item: dict) -> list[str]:
    dk = item["data_key"]
    if isinstance(dk, str):
        return [dk]
    return [t["key"] for t in dk]


@check("[CV1] đủ questionnaire cho mọi form được case tham chiếu + schema v1")
def cv1():
    form_maps = _form_maps()
    forms = _referenced_forms()
    docs = {p.stem for p in QDIR.glob("*.json")}
    missing = sorted(forms - docs)
    assert not missing, "form chưa có questionnaire: %s" % missing
    for doc in sorted(docs):
        q = json.loads((QDIR / ("%s.json" % doc)).read_text(encoding="utf-8"))
        assert q["doc_id"] == doc, doc
        validate(q, form_maps)
        assert q["questionnaire_version"] == 1, doc
    assert set(FORMS) <= docs


@check("[CV2] phủ key: 21 form E4/E5 — mọi key fillable (trừ EXCLUDED) có câu")
def cv2():
    form_maps = _form_maps()
    report = []
    for doc in sorted(p.stem for p in QDIR.glob("*.json")):
        q = json.loads((QDIR / ("%s.json" % doc)).read_text(encoding="utf-8"))
        need, got = coverage_of(doc, form_maps[doc], q["questions"])
        report.append((doc, len(q["questions"]), len(got), len(need),
                       sorted(need - got)))
    # 21 form wave E4/E5: PHỦ 100% — thiếu key nào in đúng key đó rồi FAIL
    for doc, n_q, n_got, n_need, uncovered in report:
        if doc not in FORMS:
            continue
        assert not uncovered, "%s: %d key chưa được câu hỏi nào nhắm tới: %s" \
            % (doc, len(uncovered), ", ".join(uncovered))
    print("   phủ key (form, câu, key phủ, key fillable):")
    for doc, n_q, n_got, n_need, uncovered in report:
        note = "" if not uncovered else "  (X1 legacy: %d key không hỏi)" \
            % len(uncovered)
        print("     %s: %d câu, %d/%d key%s" % (doc, n_q, n_got, n_need,
                                                note))


@check("[CV3] select/mark đều có options; mark chỉ nhận giá trị 'X'")
def cv3():
    for path in sorted(QDIR.glob("*.json")):
        q = json.loads(path.read_text(encoding="utf-8"))
        for item in q["questions"]:
            if item["type"] in ("select", "mark"):
                assert item.get("options"), \
                    "%s/%s: thiếu options" % (path.stem, item["question_id"])
            if item["type"] == "mark":
                assert all(o.get("value") == "X" for o in item["options"]), \
                    "%s/%s: mark phải nhận 'X'" % (path.stem,
                                                   item["question_id"])


@check("[CV4] không key nào bị hai câu khác trong cùng form nhắm trùng")
def cv4():
    for path in sorted(QDIR.glob("*.json")):
        q = json.loads(path.read_text(encoding="utf-8"))
        seen: dict[str, str] = {}
        for item in q["questions"]:
            for key in _keys_of_question(item):
                owner = seen.setdefault(key, item["question_id"])
                assert owner == item["question_id"], \
                    "%s: key %r do hai câu nhắm (%s, %s)" % (
                        path.stem, key, owner, item["question_id"])


@check("[CV5] generator dựng lại khớp artifact (không drift)")
def cv5():
    form_maps = _form_maps()
    for form_id in FORMS:
        path = QDIR / ("%s.json" % form_id)
        rebuilt = build_one(form_id, form_maps)
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert rebuilt == stored, \
            "%s: artifact lệch generator (chạy generator --force)" % form_id


@check("[CV6] `required` chỉ nằm trong tập cho phép (không chặn oan)")
def cv6():
    for path in sorted(QDIR.glob("*.json")):
        q = json.loads(path.read_text(encoding="utf-8"))
        for item in q["questions"]:
            if not item.get("required"):
                continue
            keys = _keys_of_question(item)
            if item.get("row_group"):
                leaf_ok = any(k.rsplit(".", 1)[-1] in
                              REQUIRED_ALLOWED_TABLE_FIRST for k in keys)
                assert leaf_ok, "%s/%s: required bảng lạ %s" % (
                    path.stem, item["question_id"], keys)
            else:
                assert all(k in REQUIRED_ALLOWED_EXACT for k in keys), \
                    "%s/%s: required lạ %s" % (path.stem,
                                               item["question_id"], keys)


def main() -> int:
    for fn in (cv1, cv2, cv3, cv4, cv5, cv6):
        fn()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 64)
    print("test_questionnaire_coverage: %d PASS / %d FAIL" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
