# -*- coding: utf-8 -*-
"""phase5_fixtures.py — Phase 5R0: dữ liệu fixture SEMANTIC cho gate visual.

WLAY-010/011: fixture cũ (dummy_data_from_map) gắn "TEST" cho mọi field và
tick X mọi checkbox kể cả nhóm loại-trừ → không đại diện hồ sơ hợp lệ, che lỗi
layout và làm nhiễu census glue. Module này sinh 5 fixture tách biệt:

  empty-paper   mọi field trống hợp lệ (chỉ khung giấy);
  valid-minimal hồ sơ tối thiểu: định danh hồ sơ + MỖI grid active đúng 1 dòng;
  valid-full    mọi section active, giá trị phân biệt theo ngữ nghĩa từng field;
  long-boundary grid 25 dòng + giá trị dài → ép pagination sát mép trang;
  choice-variants  nhóm loại-trừ chọn ĐÚNG 1, checkbox độc lập chọn đồng thời.

Nguyên tắc:
- Giá trị phân biệt theo họ key (ten/địa chỉ/CCCD/ngày/tháng/số tiền…), mỗi
  giá trị mang đuôi số thứ tự riêng → hai field không bao giờ cùng chuỗi,
  detector glue/đổi-chỗ hoạt động được.
- Nhánh default của ValueFactory (C4/B4) sinh GIÁ TRỊ TIẾNG VIỆT THỰC theo
  họ key (nơi ở, địa điểm ký, cơ quan, tên hộ KD…) — KHÔNG còn token kỹ thuật
  dạng NHAN_HOA_N: giá trị có space nên Word wrap tại space, D16 token/fragment
  về 0; _selftest chặn hồi quy token.
- Nhóm loại-trừ (EXCLUSIVE_GROUPS): pattern key + nhóm theo paragraph (các
  chk inline cùng block `p` = cùng câu hỏi). Validator từ chối payload có
  nhóm được chọn >1 — chống hồi quy WLAY-010.
- Không tự sáng tạo dữ liệu pháp lý: giá trị chỉ là ví dụ đại diện định dạng.

Chạy:  python3 -X utf8 tools/phase5_fixtures.py  (selftest nhanh)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIXTURES = ("empty-paper", "valid-minimal", "valid-full",
            "long-boundary", "choice-variants")

# ---------------------------------------------------------------------------
# [Lane C F3, 2026-09-06] Render-unit inventory đọc ĐỘNG từ form_maps.
# Corpus cuối (vd phase8f) không được kẹp cứng 87 form: khi catalog pháp
# lý loại một mẫu (vd PLI_M11 bị bãi bỏ theo TT 121/2026 — entry sẽ mang
# marker 'current_law_status' trong form_maps), corpus phải tự loại form đó.
# Marker CHƯA tồn tại trong form_maps hiện tại -> mọi form được giữ (không
# skip) — code phải chịu thiếu marker, KHÔNG suy diễn inactive.
# ---------------------------------------------------------------------------
INACTIVE_CATALOG_STATES = {
    "inactive", "removed", "repealed", "bo_loai", "khoi_catalog",
    "disabled", "withdrawn",
    # [F0L] PLI_M11 bãi bỏ theo TT 121/2026 Đ1 k2 — generator stamp
    # current_law_status.status = "REMOVED_BY_CURRENT_LAW" (lowercase ở trên).
    "removed_by_current_law",}


def current_law_status(form_map: dict):
    """Đọc marker 'current_law_status' của 1 entry form_maps.

    Trả về:
      None  -> không có marker (hoặc giá trị rỗng/active) => form còn hiệu lực
      str   -> trạng thái bất thường đã lowercase (caller quyết định skip)
    """
    st = (form_map or {}).get("current_law_status")
    if st is None:
        return None
    if isinstance(st, dict):
        st = st.get("status") or st.get("state") or ""
    s = str(st).strip().lower()
    if not s or s in ("active", "hieu_luc", "in_force"):
        return None
    return s


def active_form_ids(maps: dict, log=None) -> tuple[list[str], list[tuple[str, str]]]:
    """Inventory render-unit động: sorted(maps) trừ form inactive theo marker.

    Trả về (active_ids, skipped) với skipped = [(form_id, trạng thái)].
    `log` là callable nhận 1 dòng thông báo (vd print) — skip luôn được ghi
    log để số form corpus không bao giờ đổi ngầm.
    """
    active: list[str] = []
    skipped: list[tuple[str, str]] = []
    for fid in sorted(maps):
        st = current_law_status(maps[fid])
        if st and st in INACTIVE_CATALOG_STATES:
            skipped.append((fid, st))
            if log is not None:
                log("[corpus-inventory] skip %s (current_law_status=%s)"
                    % (fid, st))
            continue
        if st:
            # trạng thái lạ: KHÔNG tự suy skip (fail-open có log) — marker
            # chỉ khi owner chốt mới đưa form ra khỏi corpus
            if log is not None:
                log("[corpus-inventory] %s current_law_status=%r không nhận "
                    "diện -> vẫn đưa vào corpus" % (fid, st))
        active.append(fid)
    return active, skipped

M72_VARIANTS = [
    ("DNTN", "loai_hinh_dntn"),
    ("TNHH_1TV", "loai_hinh_tnhh_1tv"),
    ("TNHH_2TV", "loai_hinh_tnhh_2tv"),
    ("CTCP", "loai_hinh_ctcp"),
    ("DHDN", "loai_hinh_dhdn"),
]

# ---------------------------------------------------------------------------
# Nhóm loại-trừ theo pattern key (phần shared-prefix của key chk).
# Mỗi entry: (tên nhóm, regex khớp key chk, lựa chọn mặc định của fixture
# choice-variants). Nhóm = các option tranh nhau MỘT lựa chọn pháp lý.
# Checkbox ĐỘC LẬP (không khớp nhóm nào) được phép chọn đồng thời.
# ---------------------------------------------------------------------------
EXCLUSIVE_GROUPS = [
    # kỳ báo cáo BHXH: hàng tháng / 3 tháng / 6 tháng (chọn 1 trong 3)
    ("ky_bao_cao", r"^chk_bc_(hang_thang|03_thang|06_thang)$", "chk_bc_03_thang"),
    # phương thức nộp GTGT: khấu trừ / trực tiếp GTGT / trực tiếp doanh số /
    # không phải nộp — chọn 1
    ("gtgt", r"^chk_gtgt_(khoan_tru|truc_tiep_tren_gtgt|truc_tiep_doanh_so|khong_phai_nop)$", "chk_gtgt_khoan_tru"),
    # hạch toán phụ thuộc / độc lập / hợp nhất — chọn 1
    ("hach_toan", r"^chk_ht_(doc_lap|hop_nhat|phu_thuoc)$", "chk_ht_doc_lap"),
    # loại thành lập: mới / chuyển đổi từ HKD / chuyển đổi CSBT — chọn 1
    ("loai_thanh_lap", r"^chk_tt_(thanh_lap_moi|chuyen_doi_tu_hkd|chuyen_doi_tu_csbt)$", "chk_tt_thanh_lap_moi"),
    # loại giấy tờ định danh: CMND / CCCD / hộ chiếu / khác — chọn 1 mỗi người
    ("giay_to_dd", r"^chk_gt_(cmnd|cccd|ho_chieu|loai_khac)$", "chk_gt_cccd"),
    # khu vị trí: CN / chế xuất / kinh tế / công nghệ cao — chọn 1
    ("khu_vuc", r"^chk_khu_(cong_nghiep|che_xuat|kinh_te|cong_nghe_cao)$", "chk_khu_cong_nghiep"),
    # cặp Có/Không (chk_co/chk_khong hoặc chk_auto_*_co/_khong) — chọn 1;
    # đuôi _2/_3 là lặp câu hỏi giống nhau trong cùng mẫu
    ("co_khong", r"^chk_(auto_)?(co|khong)(_\d+)?$", "chk_khong"),
    # [F5-dryrun fix] chủ thể hộ kinh doanh: hộ gia đình / cá nhân — chọn 1
    ("chu_the_hkd", r"^chk_ct_(ho_gia_dinh|ca_nhan)$", "chk_ct_ho_gia_dinh"),
    # [F5 judge-1a fix 2026-09-07] tình trạng thành lập/thay đổi — M01 3 lựa
    # chọn, M02 7 lựa chọn (mới/tách/chia/hợp nhất/chuyển đổi loại hình/
    # chuyển đổi từ HKD/chuyển đổi từ CSBT) — MỘT nhóm mở rộng
    ("tinh_trang_thanh_lap",
     r"^chk_tt_(thanh_lap_moi|tach_dn|chia_dn|hop_nhat_dn|chuyen_doi_loai_hinh"
     r"|chuyen_doi_tu_hkd|chuyen_doi_tu_csbt)$", "chk_tt_thanh_lap_moi"),
    # cặp auto Có/Không theo ngữ cảnh (hiển thị giá trị tương đương ngoại tệ,
    # đã đăng ký đầu tư đặc biệt...) — đuôi _2 là lặp câu hỏi trong cùng mẫu
    ("auto_co_khong",
     r"^chk_auto_(co|khong)(_\d+)?$", "chk_auto_khong"),
    # bộ 3 chủ thể đặc biệt M02: đầu tư đặc biệt / DN xã hội / CTCK — các
    # khai báo độc lập KHÔNG loại-trừ (doanh nghiệp có thể đồng thời) →
    # KHÔNG đưa vào nhóm; choice giữ tick-all là chủ đích của fixture cho
    # nhóm này (ghi rõ reason khi review).
    # mô hình tổ chức công ty: Hội đồng thành viên (hoặc Hội đồng quản trị)
    # / Chủ tịch công ty — hai mô hình quản trị loại-trừ nhau về pháp lý
    # [F5-dryrun fix 2026-09-07] đồng bộ runtime EXCLUSIVE_CHK_GROUPS
    # (form-domain.js): chk_auto_chu_ho_kinh_doanh_chet_hoac_bi_toa_an_tu là
    # checkbox ĐỘC LẬP (trường hợp chủ hộ chết/bị Tòa tuyên bố mất tích) —
    # không được nuốt vào nhóm cặp Có/Không; cặp chủ thể PLII_M02
    # (chk_ct_ho_gia_dinh | chk_ct_ca_nhan) chọn-1 theo mẫu.
    # (F-V5-3: trước đây choice-variants tick cả hai trên M02/M15). Key auto
    # bị cắt ở 48 ký tự slug nên pattern phải khớp đúng 2 slug này.
    ("mo_hinh_to_chuc",
     r"^chk_auto_(hoi_dong_thanh_vien_giam_doc_hoac_tong_g"
     r"|chu_tich_cong_ty_giam_doc_hoac_tong_giam)$",
     "chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g"),
]

_GROUP_CACHE: dict = {}


def _fold(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def load_vsic() -> list[dict]:
    """Danh mục ngành VSIC chính thức — dùng cho dòng grid ngành (tên thật)."""
    p = ROOT / "app" / "data" / "nganh_vsic.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("nganh", [])


# ---------------------------------------------------------------------------
# Value pools — giá trị đại diện theo NGỮ NGHĨA key, đuôi _n giữ tính phân biệt
# ---------------------------------------------------------------------------

_TEN_DN = ["CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ AN PHÁT {}",
           "CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ PHÁT TRIỂN BÌNH MINH {}",
           "CÔNG TY TNHH SẢN XUẤT THƯƠNG MẠI HOÀNG GIA {}",
           "CÔNG TY TNHH MTV KỸ THUẬT - XÂY DỰNG TRƯỜNG THÀNH {}",
           "CÔNG TY CỔ PHẦN CHỨNG KHOÁN KINH ĐÔ {}"]
_HO_TEN = ["NGUYỄN VĂN ANH {}", "TRẦN THỊ BÌNH {}", "LÊ VĂN CƯỜNG {}",
           "PHẠM THỊ DUNG {}", "HOÀNG VĂN ĐẠT {}", "VŨ THỊ HẰNG {}",
           "ĐẶNG MINH HẢI {}", "BÙI NGỌC LAN {}", "NGÔ QUANG HUY {}",
           "DƯƠNG THỊ MAI {}"]
_DIA_CHI = ["Số {} đường Láng Hạ, phường Láng Hạ, quận Đống Đa, TP. Hà Nội",
            "Tầng {}, toà nhà Sunrise, số 25 Nguyễn Huệ, phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
            "Số {} đường Nguyễn Văn Linh, phường Vĩnh Niệm, quận Lê Chân, TP. Hải Phòng",
            "Thôn {}, xã Hoà Lâm, huyện Hoà Vang, TP. Đà Nẵng",
            "Số {} đại lộ Thăng Long, phường Mễ Trì, quận Nam Từ Liêm, TP. Hà Nội"]
_CO_QUAN = ["Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hà Nội",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hồ Chí Minh",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Hải Phòng",
            "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư thành phố Đà Nẵng"]
_QUOC_TICH = ["Việt Nam", "Nhật Bản", "Hàn Quốc", "Singapore", "Pháp"]
_TINH_TP = ["TP. Hà Nội", "TP. Hồ Chí Minh", "TP. Đà Nẵng", "TP. Hải Phòng",
            "Tỉnh Bình Dương", "Tỉnh Đồng Nai", "Tỉnh Nghệ An",
            "Tỉnh Khánh Hòa"]
_XA_PHUONG = ["Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
              "Phường Láng Hạ, Quận Đống Đa, TP. Hà Nội",
              "Phường Vĩnh Niệm, Quận Lê Chân, TP. Hải Phòng",
              "Phường Hoà Cường, Quận Hải Châu, TP. Đà Nẵng",
              "Phường Tân Kiểng, Quận 7, TP. Hồ Chí Minh",
              "Phường Mễ Trì, Quận Nam Từ Liêm, TP. Hà Nội"]
_TEN_HKD = ["HỘ KINH DOANH AN PHÁT {}",
            "HỘ KINH DOANH TÂN PHÁT {}",
            "HỘ KINH DOANH HOÀNG LONG {}",
            "HỘ KINH DOANH THỊNH VƯỜNG {}"]
_TEN_NUOC_NGOAI = ["An Phat Trading Company Limited {}",
                   "Binh Minh Investment Development Company Limited {}",
                   "Hoang Gia Manufacturing and Trading Company Limited {}"]
_DAN_TOC = ["Kinh", "Tày", "Thái", "Mường", "Nùng", "Khmer", "Hoa", "Ê Đê"]
_CQ_THUE = ["Chi cục Thuế quận Đống Đa - Cục Thuế thành phố Hà Nội",
            "Chi cục Thuế khu vực 1 - Cục Thuế thành phố Hồ Chí Minh",
            "Chi cục Thuế quận Hải Châu - Cục Thuế thành phố Đà Nẵng"]
# cơ quan cho fallback (noi_cap/noi_nhan/giay_to_co_quan): ĐẢO cấu trúc so
# với pool _CO_QUAN của nhánh chuyên dụng co_quan_dkkd/co_quan_cap → chuỗi
# không bao giờ đụng nhau trong cùng form (giá trị phân biệt)
_CO_QUAN_R = ["Sở Kế hoạch và Đầu tư thành phố Hà Nội - Phòng Đăng ký kinh doanh",
              "Sở Kế hoạch và Đầu tư thành phố Hồ Chí Minh - Phòng Đăng ký kinh doanh",
              "Sở Kế hoạch và Đầu tư thành phố Hải Phòng - Phòng Đăng ký kinh doanh",
              "Sở Kế hoạch và Đầu tư thành phố Đà Nẵng - Phòng Đăng ký kinh doanh"]
# quốc gia cho key quoc_gia: KHÔNG chứa member của pool quoc_tich (nhánh
# chuyên dụng) → cùng form có cả hai họ vẫn phân biệt
_QUOC_GIA = ["Hoa Kỳ", "Thái Lan", "Malaysia", "Đài Loan", "Úc", "Canada"]
# chức danh cho key chuc_vu: KHÁC pool chuc_danh (nhánh chuyên dụng)
_CHUC_VU = ["Chủ tịch Hội đồng thành viên", "Thành viên Hội đồng thành viên",
            "Chủ tịch Hội đồng quản trị", "Thành viên Hội đồng quản trị"]
_TINH_TRANG = ["Đang hoạt động", "Đã giải thể", "Đang tạm ngừng hoạt động",
               "Đã chấm dứt hoạt động"]
_LOAI_CP = ["Cổ phần phổ thông", "Cổ phần ưu đãi cổ tức",
            "Cổ phần ưu đãi hoàn lại", "Cổ phần ưu đãi khác"]
_LOAI_TAI_SAN = ["Tiền Việt Nam", "Ngoại tệ tự do chuyển đổi",
                 "Quyền sử dụng đất", "Máy móc thiết bị", "Tài sản khác"]
_QUYEN_CHI_PHOI = ["Hoàn toàn quyền chi phối", "Đồng quyền chi phối"]


def _fallback_value(f: "ValueFactory", k: str, n: int, lf: str,
                    raw: str) -> str:
    """Giá trị tiếng Việt thật cho key KHÔNG thuộc họ chuyên dụng (B4/C4).

    Thay token 'NHAN_HOA_N' cũ: mỗi họ key nhận mẫu câu đọc được, chỉ số n
    nhúng trong chuỗi (hoặc xoay vòng pool theo n) để hai field không cùng
    một chuỗi — detector glue/đổi-chỗ vẫn hoạt động. Giá trị không chứa '_'
    và luôn có chữ thường → Word wrap tại space, D16 (TOKEN_VALUE /
    TOKEN_FRAGMENT) không còn gì để bắt. Pool xoay qua f._pool chống trùng
    trong 1 form; pool cho họ có nhánh chuyên dụng kề (_CO_QUAN, _QUOC_TICH,
    chuc_danh) dùng chuỗi cấu trúc khác để không đụng giá trị của nhánh đó."""
    # --- ngành chính trong grid: đánh dấu như bản giấy ---
    if k.endswith("la_nganh_chinh"):
        return "×"
    # --- ngày/tháng/năm thành phần + thời điểm ---
    if "thoi_diem" in k or "thoi_diem" in lf:
        return f._unique("%02d/%02d/%04d"
                         % (n % 28 + 1, n % 12 + 1, 2024 + n % 3))
    if "ngay" in k or "ngay" in lf:
        return "%02d" % (n % 28 + 1)
    if "thang" in k or "thang" in lf:
        return "%02d" % (n % 12 + 1)
    if "nam" in k and "viet_nam" not in k and "tai_san" not in k:
        return "20%d" % (20 + n % 7)
    if "lan_thu" in k:
        return str(n)
    # --- mã số / giấy tờ / GCN (đặt trước khối tên: key số không được nuốt) ---
    if "ma_so" in k or "ma_ho_so" in k:
        return "01%010d" % n
    if "giay_to_so" in k or "so_giay_to" in k or "so_gtpl" in k:
        return "0%d%011d" % (n % 9 + 1, n)
    if "so_gcn" in k or "gp_ucsn" in k or "giay_phep" in k or \
            "giay chung nhan" in lf:
        return "41J8%06d" % n
    # --- địa danh ---
    if "dia_diem" in k:
        return f._pool(_TINH_TP, n)
    if "tinh_thanh" in k or "thanh_pho" in k:
        return f._pool(_TINH_TP, n)
    if "xa_phuong" in k or "phuong_xa" in k:
        return f._pool(_XA_PHUONG, n)
    if "noi_o" in k or "thuong_tru" in k or "tru_so" in k:
        return f._unique(_DIA_CHI[n % len(_DIA_CHI)].format(n * 3))
    # --- cơ quan (pool đảo — không đụng nhánh co_quan_dkkd/co_quan_cap) ---
    if "cq_thue" in k or ("thue" in k and "quan_ly" in k):
        return f._pool(_CQ_THUE, n)
    if "co_quan" in k or "noi_cap" in k or "noi_nhan" in k or \
            "giay_to_co_quan" in k:
        return f._pool(_CO_QUAN_R, n)
    # --- nhân khẩu học ---
    if "quoc_gia" in k:
        return f._pool(_QUOC_GIA, n)
    if "gioi_tinh" in k:
        return "Nam" if n % 2 else "Nữ"
    if "dan_toc" in k:
        return f._pool(_DAN_TOC, n)
    if "chuc_vu" in k:
        return f._pool(_CHUC_VU, n)
    # --- tên người / tên tổ chức / tên nước ngoài ---
    if "ong_ba" in k or "chu_ky" in k or "nguoi_dung_dau" in k or \
            k.endswith("ten_cd") or ("ten" in k and "uy_quyen" in k):
        return f._unique(_HO_TEN[n % len(_HO_TEN)].format(n))
    if "ten_nuoc_ngoai" in k or "tieng_nuoc" in k:
        return f._unique(_TEN_NUOC_NGOAI[n % len(_TEN_NUOC_NGOAI)].format(n))
    if "ten_hkd" in k or ("ho_kinh_doanh" in k and "ten" in k):
        return f._unique(_TEN_HKD[n % len(_TEN_HKD)].format(n))
    if ("to_chuc" in k and ("ten" in k or k.endswith("to_chuc"))) or \
            k.endswith(".ten") or ("ten" in lf and "doanh nghiep" in lf):
        return f._unique(_TEN_DN[n % len(_TEN_DN)].format(n))
    # --- số tiền / tài sản ---
    if "thoi_han" in k:
        return "%d năm" % (5 + n % 36)
    if "loai_tai_san" in k:
        return f._pool(_LOAI_TAI_SAN, n)
    if "tang_giam" in k:
        return "Tăng vốn điều lệ" if n % 2 else "Giảm vốn điều lệ"
    if k.endswith("_chu") or "bang_chu" in k:
        return f._unique("Năm trăm triệu Việt Nam đồng chẵn "
                         "(phần góp số %d)" % n)
    if "von" in k or "tai_san" in k or "chi_phi" in k:
        return str(n * 500000000)
    # --- con số ---
    if "so_lao_dong" in k:
        return str(n * 7 + 3)
    if "so_luong" in k or "so_co_phan" in k:
        return str(n * 100000)
    # --- câu chữ khai báo ---
    if "ly_do" in k:
        return f._unique(
            "Lý do được trình bày chi tiết tại hồ sơ đề nghị số %d" % n)
    if "can_cu" in k:
        return f._unique("Thông tư số %02d/2026/TT-BKHĐT" % n
                         if "khac" not in k else
                         "Quyết định số %04d/2026/QĐ-UBND" % n)
    if "ve_viec" in k:
        return f._unique("Đăng ký thay đổi theo đề nghị số %d" % n)
    if "tinh_trang" in k:
        return f._pool(_TINH_TRANG, n)
    if "loai_co_phan" in k:
        return f._pool(_LOAI_CP, n)
    if "quyen_chi_phoi" in k:
        return f._pool(_QUYEN_CHI_PHOI, n)
    if "thong_tin_dang_ky" in k:
        cu_moi = "cũ" if k.endswith("cu") else "mới"
        return f._unique("Thông tin đăng ký %s (bản khai số %d)"
                         % (cu_moi, n))
    if "chi_tiet" in k:
        return f._unique("Chi tiết kèm theo bản kê khai số %d" % n)
    if k.endswith("luu") or "luu_vb" in k:
        return f._unique("Lưu hồ sơ gốc số %d" % n)
    # --- hết họ key biết: dùng nhãn gốc đọc được + số thứ tự ---
    base = re.sub(r"\s*[:;/].*$", "", raw).strip()
    base = re.sub(r"[_\s]+", " ", base)
    if len(base) > 48:
        base = base[:48].rstrip()
    if base and any(c.isalpha() for c in base):
        return f._unique("%s — giá trị minh hoạ số %d"
                         % (base[0].upper() + base[1:], n))
    return "Giá trị kê khai số %d" % n


class ValueFactory:
    """Sinh giá trị phân biệt theo họ key; đếm toàn cục để không trùng lặp."""

    def __init__(self, vsic: list[dict] | None = None):
        self.n = 0
        self.vsic = vsic if vsic is not None else load_vsic()
        self._vsic_i = 0
        self._used: set[str] = set()
        # [F5-dryrun fix 2026-09-07] tập key của form đang sinh (build_fixture
        # set trước khi value()) — dùng để phân biệt slot ngày ĐỘC LẬP vs slot
        # NGÀY THÀNH PHẦN trong pattern {ngay_X}/{thang_X}/{nam_X}.
        self._form_keys: set[str] = set()

    def set_form_keys(self, keys: set[str]) -> None:
        self._form_keys = {k for k in keys}

    def _date_slot_is_component(self, k: str) -> bool:
        """True khi key ngày này là thành phần của pattern 3-token
        ({ngay_X}/{thang_X}/{nam_X} cùng prefix loop/scalar) — giá trị phải
        là NGÀY (dd), không phải full dd/mm/yyyy. Tránh hồi quy 6V-V4b 7a:
        full-date chỉ đúng cho slot ngày độc lập (vd {ngay_cap} một mình)."""
        fam = k.rsplit(".", 1)[0] if "." in k else ""
        base = k.split(".")[-1]
        if not (base.startswith("ngay_") or base == "ngay"):
            return False
        suffix = base[5:]  # 'sinh', 'cap', ... ('ngay_' = 5 ký tự)
        thang = ("%s.thang_%s" % (fam, suffix)) if fam else ("thang_%s" % suffix)
        nam = ("%s.nam_%s" % (fam, suffix)) if fam else ("nam_%s" % suffix)
        return thang in self._form_keys and nam in self._form_keys

    def _next(self) -> int:
        self.n += 1
        return self.n

    def _pool(self, pool: list[str], start: int) -> str:
        """Member pool chưa dùng trong form (giá trị ≥8 ký tự phải phân biệt
        — test 'giá trị phân biệt'/D12); cạn pool thì gắn chỉ số lượt."""
        L = len(pool)
        for i in range(L):
            cand = pool[(start + i) % L]
            if len(cand) < 8:
                return cand
            if cand not in self._used:
                self._used.add(cand)
                return cand
        cand = "%s (lần %d)" % (pool[start % L], self.n)
        self._used.add(cand)
        return cand

    def _unique(self, cand: str) -> str:
        """Đăng ký giá trị ≥8 ký tự vào memo; trùng thì gắn chỉ số tách."""
        if len(cand) >= 8:
            if cand in self._used:
                cand = "%s (lần %d)" % (cand, self.n)
            self._used.add(cand)
        return cand

    def _vsic_row(self) -> tuple[str, str]:
        if self.vsic:
            row = self.vsic[self._vsic_i % len(self.vsic)]
            self._vsic_i += 1
            return str(row.get("ma") or "0112"), str(row.get("ten") or "Trồng ngô")
        return "0112", "Trồng ngô và cây lương thực có hạt khác"

    def value(self, key: str, label: str = "") -> str:
        n = self._next()
        k = _fold(key)
        if "ma_nganh" in k or k.endswith("ma_so_nganh"):
            return self._vsic_row()[0]
        if "ten_nganh" in k or "nganh_nghe" in k:
            return self._vsic_row()[1]
        if "quoc_tich" in k:
            return _QUOC_TICH[n % len(_QUOC_TICH)]
        if "ma_so_thue" in k or "ma_so_dn" in k or "ma_so_ho" in k:
            return "010%s%04d" % (n % 90 + 10, n)
        if "cccd" in k or "can_cuoc" in k or "so_dinh_danh" in k or "cmnd" in k:
            return "0%s%011d" % (n % 9 + 1, n)
        if "ho_chieu" in k:
            return "C%d%07d" % (n % 9 + 1, n)
        if "dien_thoai" in k:
            return "09%08d" % n
        if "fax" in k:
            return "024.%08d" % n
        if "email" in k or "thu_dien_tu" in k:
            return "contact%d@congty.example.vn" % n
        if "website" in k:
            return "https://congty%d.example.vn" % n
        if "ten_tieng_viet" in k or "ten_doanh_nghiep" in k or \
                k.endswith("ten_cn") or "ten_don_vi" in k:
            return _TEN_DN[n % len(_TEN_DN)].format(n)
        if "ho_ten" in k or "ten_chu" in k or "ten_nguoi" in k or \
                "ten_thanh_vien" in k or "ten_co_dong" in k or \
                "ten_dai_dien" in k or k.endswith("nguoi_uy_quyen"):
            return _HO_TEN[n % len(_HO_TEN)].format(n)
        if "dia_chi" in k:
            return _DIA_CHI[n % len(_DIA_CHI)].format(n * 3)
        if "co_quan_dkkd" in k or "co_quan_cap" in k:
            return _CO_QUAN[n % len(_CO_QUAN)]
        if "von_dieu_le" in k or "von_dang_ky" in k or "gia_tri" in k or \
                "menh_gia" in k or "so_tien" in k or "tong" in k or \
                "muc_von" in k or "so_von" in k:
            return str(n * 500000000)
        if "ty_le" in k or "phan_tram" in k:
            return str((n * 7) % 100 + 1)
        if k.endswith("ngay") or "ngay_ky" in k:
            return "%02d" % (n % 28 + 1)
        if "ngay_sinh" in k or "ngay_cap" in k:
            # [6V-V4b việc 7a] slot ngày ĐỘC LẬP là TRƯỜNG NGÀY ĐỦ dd/mm/yyyy
            # theo bản giấy. [F5-dryrun fix 2026-09-07] slot NGÀY THÀNH PHẦN
            # (pattern {ngay_X}/{thang_X}/{nam_X} — template ghép 3 token bằng
            # '/', hoặc cột grid tách ngày/tháng/năm) chỉ được điền NGÀY (dd):
            # full-date ghép với thang/nam kề nhau thành double-date
            # '09/09/1978/10/1980' (finding #1 dryrun 20 record).
            if self._date_slot_is_component(k):
                return "%02d" % (n % 28 + 1)
            if "ngay_sinh" in k:
                return "%02d/%02d/19%02d" % (n % 28 + 1, n % 12 + 1,
                                             70 + n % 30)
            return "%02d/%02d/20%02d" % (n % 28 + 1, n % 12 + 1, 24 + n % 3)
        if k.endswith("thang"):
            return "%02d" % (n % 12 + 1)
        if k.endswith("nam"):
            return "20%d" % (20 + n % 7)
        if "nam_sinh" in k:
            return "19%d" % (70 + n % 30)
        if "so_nha" in k:
            return str(n * 3)
        if "chuc_danh" in k:
            return "Giám đốc" if n % 2 else "Kế toán trưởng"
        if "mo_ta" in k or "ghi_chu" in k or "noi_dung" in k:
            return "Nội dung kê khai số %d — mô tả đầy đủ, có dấu tiếng Việt" % n
        if "loai_giay_to" in k or "ten_giay_to" in k or "ten_tai_lieu" in k:
            return "Giấy chứng nhận đăng ký doanh nghiệp bản gốc số %d" % n
        if "so_ban" in k:
            return str(n % 3 + 1)
        if "so_trang" in k:
            return str(n % 10 + 1)
        if "so_van_ban" in k or "so_ho_so" in k or "so_cn" in k:
            return "%05d/%d" % (n, 2026)
        if "viet_tat" in k:
            return "ANPHAT%d" % n
        # mặc định (C4/B4): giá trị tiếng Việt thật theo họ key thay token
        # NHAN_HOA_N cũ; chỉ số n nhúng trong chuỗi giữ tính phân biệt
        return _fallback_value(self, k, n, _fold(label or ""), label or key)


# ---------------------------------------------------------------------------
# Nhóm loại-trừ: pattern + paragraph-level
# ---------------------------------------------------------------------------

def chk_groups(form_map: dict, blocks: dict | list) -> list[list[str]]:
    """Trả danh sách nhóm loại-trừ: mỗi nhóm là list key chk tranh nhau.

    Hai nguồn: (1) EXCLUSIVE_GROUPS theo pattern key; (2) mọi tập chk inline
    xuất hiện trong CÙNG một block `p` (cùng câu hỏi trên giấy). Nhóm pattern
    và nhóm paragraph có thể trùng member — dedupe giữ nhóm dài hơn."""
    fields = form_map.get("fields", [])
    chk_keys = [f["key"] for f in fields if f.get("type") == "chk"]
    keyset = set(chk_keys)
    groups: list[list[str]] = []

    # (1) theo pattern
    for _name, pat, _pick in EXCLUSIVE_GROUPS:
        rx = re.compile(pat)
        members = [k for k in chk_keys if rx.match(k)]
        if len(members) >= 2:
            groups.append(members)

    # (2) theo paragraph (chk inline cùng block p)
    for grp in _paragraph_groups(blocks):
        members = [k for k in grp if k in keyset]
        if len(members) >= 2:
            groups.append(members)
    return _merge_overlapping(groups)


def _merge_overlapping(groups: list[list[str]]) -> list[list[str]]:
    """Gộp các nhóm chia member (cùng một câu hỏi bị bắt bởi 2 nguồn) —
    tránh pick 2 lựa chọn cho cùng một câu."""
    merged: list[set[str]] = []
    for g in groups:
        gs = set(g)
        hit = [m for m in merged if m & gs]
        if hit:
            union = gs.union(*hit)
            merged = [m for m in merged if m not in hit]
            merged.append(union)
        else:
            merged.append(gs)
    return [sorted(m) for m in merged]


def _paragraph_groups(blocks) -> list[list[str]]:
    out: list[list[str]] = []
    items = blocks.get("blocks") if isinstance(blocks, dict) else blocks
    for b in items or []:
        if not isinstance(b, dict) or b.get("t") != "p":
            continue
        keys = []
        for r in b.get("runs") or []:
            if isinstance(r, dict) and isinstance(r.get("input"), dict):
                k = r["input"].get("key") or ""
                if k.startswith("chk"):
                    keys.append(k)
        if len(keys) >= 2:
            out.append(keys)
    return out


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# [6V-V4b việc 7b] cột chữ ký trong bảng = vùng viết tay theo bản giấy —
# KHÔNG nhận dữ liệu fixture (adjudicate auditor/6v-visual 2026-09-05,
# Finding ngoài phạm vi #3: cột 'Chữ ký' PLII_M02 p4 / PLI_M09 p16 bị điền
# tên + chỉ số trên vùng điền tay). Đây là phần mở rộng bảng của chính sách
# handwriting-only: registry tools/phase6v_handwriting_slots.json chỉ phủ
# slot tên dưới tiêu đề (D14 tự chạy, không đụng cột bảng).
_HANDWRITING_COL_TAG = "chu_ky"


def is_handwriting_column(tag: str, label: str = "") -> bool:
    """Cột bảng chữ ký (vùng viết tay) — fixture để trống."""
    k = _fold(tag or "")
    if k == _HANDWRITING_COL_TAG or k.endswith("." + _HANDWRITING_COL_TAG):
        return True
    lf = _fold(label or "")
    return lf == "chu ky" or lf.startswith("chu ky ")


def build_fixture(fid: str, form_map: dict, fixture: str,
                  blocks=None, factory: ValueFactory | None = None) -> dict:
    """Sinh data dict cho (form, fixture). Không đụng draft/validation —
    đây là dữ liệu export để gate visual xem bố cục."""
    if fixture not in FIXTURES:
        raise ValueError("fixture không hợp lệ: %r" % fixture)
    f = factory or ValueFactory()
    # [F5-dryrun fix] cung tập key form để value() phân biệt slot ngày
    # độc lập vs thành phần (loop columns có dạng 'loop.tag').
    keys: set[str] = {fld["key"] for fld in form_map.get("fields", [])}
    for t in form_map.get("dynamic_tables", []):
        for c in t.get("columns", []):
            if c.get("tag"):
                keys.add("%s.%s" % (t.get("loop") or t.get("id"), c["tag"]))
    f.set_form_keys(keys)
    data: dict = {}
    if fixture == "empty-paper":
        return data
    is_minimal = fixture == "valid-minimal"
    is_long = fixture == "long-boundary"

    # ---- scalar fields ----
    for field in form_map.get("fields", []):
        key, ftype = field["key"], field.get("type", "text")
        if ftype == "chk":
            # chk xử lý ở chọn nhóm / choice fixture phía dưới; valid-full
            # KHÔNG tick tất (đó chính là bug WLAY-010).
            continue
        if is_minimal and not _minimal_key(key):
            continue
        data[key] = f.value(key, field.get("label") or "")
        if is_long and _stretchable(key):
            data[key] = "%s %s" % (data[key],
                                   "kèm theo phần mô tả mở rộng số %d để ép "
                                   "dòng văn bản xuống dòng nhiều lần trong ô"
                                   % f.n)

    # ---- chk: chỉ fixture choice tick ----
    if fixture == "choice-variants":
        groups = chk_groups(form_map, blocks or {})
        members_in_groups: set[str] = set()
        picked: set[str] = set()
        for members in groups:
            members_in_groups.update(members)
            pick = _group_pick(members)
            if pick:
                picked.add(pick)
        for field in form_map.get("fields", []):
            if field.get("type") != "chk":
                continue
            key = field["key"]
            if key in picked:
                data[key] = "X"
            elif key not in members_in_groups:
                # checkbox độc lập (không thuộc nhóm nào) chọn đồng thời
                data[key] = "X"

    # ---- dynamic tables (loop) ----
    rows_n = 1 if is_minimal else (25 if is_long else 3)
    for t in form_map.get("dynamic_tables", []):
        loop, cols = t["loop"], t.get("columns", [])
        rows = []
        for _ in range(rows_n):
            row = {c["tag"]: f.value(c["tag"], c.get("label") or "")
                   for c in cols}
            # [6V-V4b việc 7b] cột chữ ký = vùng viết tay: giá trị VẼ RA
            # rồi MỚI loại — giữ nguyên chuỗi gọi ValueFactory (n) để việc
            # bỏ cột ký KHÔNG xô lệch giá trị của mọi field phía sau
            # (xô lệch n đã gây drift pagination toàn corpus, tái hiện
            # m72_ctcp p2 trang 29 ký tự)
            rows.append({k: v for k, v in row.items()
                         if not is_handwriting_column(k)})
        data[loop] = rows

    # ---- fixed-matrix cells (spec-driven) ----
    specs = [s for s in (form_map.get("section_specs") or [])
             if s.get("kind") == "fixed-matrix"]
    for spec in specs:
        sem = spec.get("semantic_key")
        editable = {r["id"] for r in spec.get("fixed_rows", [])
                    if not r.get("output_only")}
        for row_id in sorted(editable):
            for c in spec.get("columns", []):
                if c.get("tag") and not c.get("computed"):
                    if is_minimal and not _minimal_key(c["tag"]):
                        continue
                    data["%s.%s.%s" % (sem, row_id, c["tag"])] = \
                        f.value(c["tag"], c.get("label") or "")
    return data


def _group_pick(members: list[str]) -> str:
    """Chọn thành viên đại diện cho nhóm: ưu tiên pick khai báo trong
    EXCLUSIVE_GROUPS nếu còn trong members, nếu không thì member đầu."""
    for _name, pat, pick in EXCLUSIVE_GROUPS:
        rx = re.compile(pat)
        if pick in members and all(rx.match(m) for m in members):
            return pick
    return members[0]


def _minimal_key(key: str) -> bool:
    """Field bắt buộc cho hồ sơ tối thiểu: định danh + liên hệ + ngày ký."""
    k = _fold(key)
    return bool(re.search(
        r"(ten_tieng_viet|ten_chu_ho|ho_ten|ten_doanh_nghiep|ma_so_thue|"
        r"ma_so_dn|ma_so_ho|dia_chi_tru_so|dia_chi|ngay_ky|thang_ky|nam_ky|"
        r"dia_diem_ky|co_quan_dkkd|ngay|thang|nam$)", k))


def _stretchable(key: str) -> bool:
    k = _fold(key)
    return bool(re.search(r"(dia_chi|mo_ta|ghi_chu|ten_nganh|ten_doanh_nghiep|"
                          r"ten_tieng_viet|noi_dung)", k))


# ---------------------------------------------------------------------------
# Validator — chống hồi quy WLAY-010 (tick tràn nhóm loại-trừ)
# ---------------------------------------------------------------------------

def validate_fixture(form_map: dict, blocks, data: dict,
                     fixture: str) -> list[str]:
    """Trả list vi phạm (rỗng = hợp lệ). Kiểm:
    (V1) nhóm loại-trừ chọn đúng <=1;
    (V2) empty-paper không có giá trị nào;
    (V3) fixture khác: mỗi grid active có dữ liệu (trừ empty);
    (V4) không dùng chuỗi 'TEST' chung mọi field."""
    errs: list[str] = []
    if fixture == "empty-paper":
        if any(str(v).strip() for v in data.values()):
            errs.append("V2: empty-paper phải trống hoàn toàn")
        return errs
    # (V1)
    for members in chk_groups(form_map, blocks):
        chosen = [k for k in members if str(data.get(k) or "").strip()]
        if len(chosen) > 1:
            errs.append("V1: nhóm loại-trừ %s được chọn %d: %s"
                        % (members[0], len(chosen), ",".join(chosen)))
    # (V3)
    if fixture != "valid-minimal":
        for t in form_map.get("dynamic_tables", []):
            if not isinstance(data.get(t["loop"]), list) or \
                    not data[t["loop"]]:
                errs.append("V3: grid %s không có dòng dữ liệu" % t["loop"])
    # (V4)
    vals = [str(v) for v in data.values() if str(v).strip()]
    if vals and all(v == "TEST" for v in vals):
        errs.append("V4: fixture dùng chung chuỗi TEST cho mọi field")
    return errs


# ---------------------------------------------------------------------------
# CLI selftest
# ---------------------------------------------------------------------------
# Grammar token D16 (bản sao cục bộ — tránh import ngược phase5_visual_gate):
# token nguyên = MỘT từ toàn HOA/chữ số/gạch dưới, kết thúc bằng chữ số, có
# "_" (VD NOI_O_HIEN_TAI_123). C4/B4: nhánh default không được sinh ra kiểu
# này nữa — check mọi giá trị của mọi form × fixture.
_SELFTEST_TOKEN = re.compile(r"[A-Z][A-Z0-9_]*_[0-9]+")


def _selftest() -> int:
    import sys
    sys.path.insert(0, str(ROOT))
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    ok = fail = 0
    token_hits: list[str] = []
    for fid in sorted(maps):
        blocks_p = ROOT / "app" / "data" / "blocks" / ("%s.json" % fid)
        blocks = (json.loads(blocks_p.read_text(encoding="utf-8"))
                  if blocks_p.exists() else {})
        for fixture in FIXTURES:
            f = ValueFactory()
            data = build_fixture(fid, maps[fid], fixture, blocks, f)
            errs = validate_fixture(maps[fid], blocks, data, fixture)
            # (B4/C4) không giá trị nào được là token kỹ thuật LABEL_HOA_N —
            # quét cả phần ghép chuỗi (long-boundary nối suffix) như PDF thấy
            for key, val in data.items():
                hay = " ".join(str(x) for x in
                               (val if isinstance(val, list) else [val]))
                for w in hay.replace("/", " / ").split():
                    if _SELFTEST_TOKEN.fullmatch(w):
                        token_hits.append("%s/%s [%s] %r"
                                          % (fid, fixture, key, w[:40]))
            if errs:
                fail += 1
                print("FAIL %s/%s: %s" % (fid, fixture, "; ".join(errs)))
            else:
                ok += 1
    if token_hits:
        fail += 1
        print("FAIL B4 token giá trị (%d): %s" % (len(token_hits),
                                                  token_hits[:5]))
    else:
        ok += 1
        print("PASS B4: 0 giá trị khớp grammar token D16 trên %d form × %s"
              % (len(maps), "/".join(FIXTURES)))
    # fixture cũ (dummy tick mọi chk) phải bị validator chặn
    from tools.docx_render import dummy_data_from_map
    old = dummy_data_from_map(maps["PLI_M01"])
    blocks = json.loads((ROOT / "app" / "data" / "blocks" / "PLI_M01.json")
                        .read_text(encoding="utf-8"))
    old_errs = validate_fixture(maps["PLI_M01"], blocks, old, "choice-variants")
    if any(e.startswith("V1") for e in old_errs):
        ok += 1
        print("PASS regression WLAY-010: dummy cũ bị chặn (V1)")
    else:
        fail += 1
        print("FAIL: dummy cũ KHÔNG bị chặn: %r" % old_errs)
    print("-" * 60)
    print("phase5_fixtures selftest: %d PASS / %d FAIL" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
