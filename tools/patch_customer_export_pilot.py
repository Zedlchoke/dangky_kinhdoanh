# -*- coding: utf-8 -*-
"""One-shot pilot tagging for customer Excel export (wave P0)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TNHH_WIZARD = [
    {
        "question_id": "wiz_tt_loai",
        "group": "Xác định trường hợp thành lập",
        "text": "Trường hợp thành lập doanh nghiệp của bạn?",
        "type": "select",
        "required": True,
        "wizard": True,
        "audience": "customer",
        "tier": "wizard",
        "options": [
            {"value": "moi", "label": "Thành lập mới"},
            {
                "value": "tu_hkd",
                "label": "Chuyển đổi từ hộ kinh doanh",
                "wizard_sets": {"chk_tt_chuyen_doi_tu_hkd": "X"},
            },
            {
                "value": "tu_csbt",
                "label": "Chuyển đổi từ cơ sở bảo trợ xã hội/quỹ",
                "wizard_sets": {"chk_tt_chuyen_doi_tu_csbt": "X"},
            },
            {
                "value": "chuyen_doi_loai_hinh",
                "label": "Chuyển đổi loại hình doanh nghiệp",
                "wizard_sets": {"chk_tt_chuyen_doi_loai_hinh": "X"},
            },
        ],
        "version": 1,
        "data_key": "wiz_tt_loai",
    },
    {
        "question_id": "wiz_chu_so_huu",
        "group": "Xác định trường hợp thành lập",
        "text": "Chủ sở hữu công ty là?",
        "type": "select",
        "required": True,
        "wizard": True,
        "audience": "customer",
        "tier": "wizard",
        "options": [
            {"value": "ca_nhan", "label": "Cá nhân"},
            {"value": "to_chuc", "label": "Tổ chức"},
        ],
        "version": 1,
        "data_key": "wiz_chu_so_huu",
    },
]

DNTN_WIZARD = [
    {
        "question_id": "wiz_tt_loai",
        "group": "Xác định trường hợp thành lập",
        "text": "Trường hợp thành lập doanh nghiệp của bạn?",
        "type": "select",
        "required": True,
        "wizard": True,
        "audience": "customer",
        "tier": "wizard",
        "options": [
            {"value": "moi", "label": "Thành lập mới"},
            {
                "value": "tu_hkd",
                "label": "Chuyển đổi từ hộ kinh doanh",
                "wizard_sets": {"chk_tt_chuyen_doi_tu_hkd": "X"},
            },
            {
                "value": "tu_csbt",
                "label": "Chuyển đổi từ cơ sở bảo trợ xã hội/quỹ",
                "wizard_sets": {"chk_tt_chuyen_doi_tu_csbt": "X"},
            },
        ],
        "version": 1,
        "data_key": "wiz_tt_loai",
    },
    {
        "question_id": "wiz_gt_loai",
        "group": "Giấy tờ pháp lý của bạn",
        "text": "Bạn đang dùng loại giấy tờ pháp lý nào?",
        "type": "select",
        "required": True,
        "wizard": True,
        "audience": "customer",
        "tier": "wizard",
        "options": [
            {
                "value": "cccd",
                "label": "Căn cước công dân / CMND gắn chip",
                "wizard_sets": {"chk_gt_cccd": "X"},
            },
            {
                "value": "cmnd",
                "label": "Chứng minh nhân dân (9 số)",
                "wizard_sets": {"chk_gt_cmnd": "X"},
            },
            {
                "value": "ho_chieu",
                "label": "Hộ chiếu",
                "wizard_sets": {"chk_gt_ho_chieu": "X"},
            },
            {
                "value": "khac",
                "label": "Giấy tờ khác",
                "wizard_sets": {"chk_gt_loai_khac": "X"},
            },
        ],
        "version": 1,
        "data_key": "wiz_gt_loai",
    },
]

HKD_WIZARD = [
    {
        "question_id": "wiz_loai_chu_ho",
        "group": "Xác định loại hình hộ kinh doanh",
        "text": "Hộ kinh doanh của bạn thuộc trường hợp nào?",
        "type": "select",
        "required": True,
        "wizard": True,
        "audience": "customer",
        "tier": "wizard",
        "options": [
            {"value": "ca_nhan", "label": "Một cá nhân làm chủ hộ"},
            {
                "value": "ho_gia_dinh",
                "label": "Các thành viên hộ gia đình ủy quyền",
                "wizard_sets": {"chk_ct_ho_gia_dinh": "X"},
            },
        ],
        "version": 1,
        "data_key": "wiz_loai_chu_ho",
    },
]


def _tag_tnhh(questions: list[dict]) -> None:
    staff_prefixes = (
        "q_i02_chk_",
        "q_i02_ds_nddpl_",
    )
    staff_groups = (
        "Chuyển đổi từ hộ kinh doanh (nếu có)",
        "Chuyển đổi từ cơ sở bảo trợ xã hội/quỹ (nếu có)",
        "Doanh nghiệp gốc (tách/chia/hợp nhất — nếu có)",
        "Dự án đầu tư / giấy phép (nếu có)",
        "Trường hợp thành lập doanh nghiệp",
        "Loại giấy tờ pháp lý của cá nhân",
        "Người đại diện được ủy quyền của chủ sở hữu tổ chức (nếu có)",
    )
    for item in questions:
        qid = item.get("question_id") or ""
        if qid.startswith(staff_prefixes):
            item["audience"] = "staff"
        elif item.get("group") in staff_groups:
            item["audience"] = "staff"
        elif _is_ten_nganh_question(item):
            item["audience"] = "staff"
        elif isinstance(item.get("data_key"), str) and \
                item["data_key"].endswith(".ma_nganh"):
            item.pop("autofill", None)
            item["text"] = "Mã ngành VSIC cấp 4?"
            item["example"] = "6201"
            item["required"] = True
        elif item.get("when"):
            item.setdefault("tier", "conditional")
        elif not item.get("required"):
            item.setdefault("tier", "conditional")
        elif item.get("required"):
            item.setdefault("tier", "core")
            item.setdefault("audience", "customer")


def _tag_dntn(questions: list[dict]) -> None:
    staff_prefixes = ("q_i01_chk_",)
    staff_groups = (
        "Chuyển đổi từ hộ kinh doanh (nếu có)",
        "Chuyển đổi từ cơ sở bảo trợ xã hội/quỹ (nếu có)",
        "Trường hợp thành lập doanh nghiệp",
        "Loại giấy tờ pháp lý của cá nhân",
        "Vị trí đặt trụ sở/địa điểm",
        "Chế độ kế toán và báo cáo tài chính",
        "Thuế giá trị gia tăng",
        "Bảo hiểm xã hội (phương thức đóng)",
    )
    for item in questions:
        qid = item.get("question_id") or ""
        if qid.startswith(staff_prefixes):
            item["audience"] = "staff"
        elif item.get("group") in staff_groups:
            item["audience"] = "staff"
        elif _is_ten_nganh_question(item):
            item["audience"] = "staff"
        elif item.get("data_key") == "ds_nganh.ma_nganh":
            item.pop("autofill", None)
            item["text"] = "Mã ngành VSIC cấp 4?"
            item["example"] = "6201"
            item["required"] = True
        elif item.get("when"):
            item.setdefault("tier", "conditional")
        elif not item.get("required"):
            item.setdefault("tier", "conditional")
        elif item.get("required"):
            item.setdefault("tier", "core")
            item.setdefault("audience", "customer")


def _is_ten_nganh_question(item: dict) -> bool:
    key = item.get("data_key")
    if isinstance(key, str):
        return key.endswith(".ten_nganh") or key == "ten_nganh"
    if isinstance(key, list):
        return any(isinstance(k, dict) and str(k.get("key", "")).endswith(
            ".ten_nganh") for k in key)
    return False


def _tag_hkd(questions: list[dict]) -> None:
    for item in questions:
        qid = item.get("question_id") or ""
        if qid in ("q_chu_ho_la_ca_nhan", "q_chu_ho_la_ho_gia_dinh"):
            item["audience"] = "staff"
        elif qid.startswith("q_tv_hgd_"):
            item.pop("when", None)
            item["customer_branch"] = {"chk_ct_ho_gia_dinh": ["X"]}
            item["tier"] = "conditional"
        elif not item.get("required"):
            item.setdefault("tier", "conditional")
        elif item.get("required"):
            item.setdefault("tier", "core")
            item.setdefault("audience", "customer")


def patch(path: Path, wizard: list[dict], tag_fn) -> None:
    from tools.build_case_questionnaires import manifest_hash

    data = json.loads(path.read_text(encoding="utf-8"))
    for form in data.get("forms") or []:
        qs = form.get("questions") or []
        tag_fn(qs)
        have = {q.get("question_id") for q in qs if q.get("wizard")}
        prepend = [w for w in wizard if w["question_id"] not in have]
        form["questions"] = prepend + qs
    data["manifest_hash"] = manifest_hash(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("patched", path.name)


def main() -> None:
    base = ROOT / "app" / "data" / "case_questionnaires"
    patch(base / "thanh_lap_tnhh_1tv.json", TNHH_WIZARD, _tag_tnhh)
    patch(base / "dang_ky_ho_kinh_doanh_lan_dau.json", HKD_WIZARD, _tag_hkd)
    patch(base / "thanh_lap_dntn.json", DNTN_WIZARD, _tag_dntn)


if __name__ == "__main__":
    main()
