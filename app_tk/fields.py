"""Phân nhóm trường nhập liệu dùng chung / riêng từng mẫu."""

from __future__ import annotations

# Các key thuộc nhóm "Chữ ký & cơ quan tiếp nhận"
SIGNATURE_KEYS = ("dia_diem_ky", "ngay_ky_vb", "thang_ky_vb", "nam_ky_vb", "co_quan_dkkd")

# Thứ tự hiển thị các nhóm dùng chung theo namespace
SHARED_GROUPS = [
    ("dn", "Doanh nghiệp"),
    ("chu_hkd", "Chủ hộ kinh doanh / cá nhân"),
    ("cn", "Chi nhánh"),
]


def classify(key: str) -> str | None:
    """Trả về mã nhóm dùng chung của key, hoặc None nếu hỏi riêng theo mẫu."""
    if key in SIGNATURE_KEYS:
        return "ky"
    if key.startswith("chu_hkd.") or key.startswith("hkd_"):
        return "chu_hkd"
    if key.startswith("dn."):
        return "dn"
    if key.startswith("cn."):
        return "cn"
    return None


def collect_fields(selected_maps: list[dict]):
    """Gom fields của các mẫu đã chọn thành (shared, per_form).

    - shared: dict {mã nhóm: [field, ...]} — key giống nhau giữa nhiều mẫu
      chỉ giữ một bản (nhãn lấy của mẫu đầu tiên).
    - per_form: dict {map_id: [field, ...]} — các trường không thuộc nhóm chung,
      kèm 'ten_mau' để làm tiêu đề mục.
    """
    shared: dict[str, list] = {}
    seen_shared: set[str] = set()
    per_form: dict[str, list] = {}

    for fmap in selected_maps:
        mid = fmap["id"]
        rows = []
        for f in fmap.get("fields", []):
            grp = classify(f["key"])
            if grp is not None:
                if f["key"] not in seen_shared:
                    seen_shared.add(f["key"])
                    shared.setdefault(grp, []).append(dict(f))
            else:
                # trùng key riêng giữa 2 mẫu (hiếm): vẫn nhập 2 ô riêng biệt
                rows.append(dict(f))
        if rows:
            per_form[mid] = rows
    return shared, per_form


def chk_clusters(chk_keys: list[str]) -> list[list[str]]:
    """Cụm hóa checkbox cùng nhóm logic theo tiền tố chung (2 token đầu).

    VD chk_tt_tach_dn & chk_tt_sap_nhap_dn -> cụm "chk_tt" (dùng Radiobutton
    loại trừ); checkbox đơn lẻ -> Checkbutton độc lập.
    """
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    for k in chk_keys:
        toks = k.split("_")
        prefix = "_".join(toks[:2])
        if prefix not in groups:
            groups[prefix] = []
            order.append(prefix)
        groups[prefix].append(k)
    return [groups[p] for p in order]
