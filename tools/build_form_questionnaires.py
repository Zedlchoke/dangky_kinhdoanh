# -*- coding: utf-8 -*-
"""Sinh questionnaire form-level cho CÁC FORM CÒN THIẾU — wave E4/E5
(PLAN_hoan_thien_phat_hanh; owner ủy quyền toàn bộ quyết định nội dung
"tôi duyệt và chốt hết" ngày 2026-09-10 — provenance:
manifest `content_review="owner_delegated_2026-09-10"`, được đối xử như
approved; 7 questionnaire wave X1 giữ nguyên `approved`).

Sinh `app/data/questionnaire/<form_id>.json` cho 21 form được ≥1 case tham
chiếu trong `use_cases.json` mà chưa có questionnaire:
  PLI_M01..M09, M13, M14, M15, M17, M19, M21, M26, M28, M30, M31, M32, M78.
File nào ĐÃ tồn tại thì KHÔNG đụng (7 file X1 là nội dung owner duyệt).

Cách sinh (deterministic, KHÔNG sáng tác ngoài form_maps/blocks):
- `data_key` lấy TRỰC TIẾP từ `form_maps[form].fields[].key` +
  `dynamic_tables[].loop/columns.tag` — sai key là lỗi nghiêm trọng nhất nên
  generator KHÔNG bao giờ tự chế key; cuối cùng chạy self-check phủ key,
  thiếu key nào → exit 1, KHÔNG ghi file nào.
- Nhãn câu hỏi: bảng văn phong theo từng key/family (giọng đời thường như
  7 file X1, có `example`); nhãn ô tick lấy từ `blocks/<form>.json`
  (run `t=="chk"` — nhãn pháp lý gốc của ô).
- Ô KHÔNG hỏi (tài liệu hóa ở EXCLUDED_KEYS / EXCLUDED_SUFFIXES):
  + khối đầu thư `so_van_ban, dia_diem_ky, ngay/thang/nam_ky_vb,
    co_quan_dkkd, hs_nop_ngay` — ngày ký app tự điền ngày hiện hành
    (app_web/ui/render.js AUTO_KEYS), số văn bản/kính gửi là phần đầu thư do
    người xử lý hồ sơ quyết (đúng tiền lệ 7 questionnaire X1 không hỏi);
  + cột `*.chu_ky` — chữ ký trên giấy in (form-domain.js outputOnlyTags);
  + cột `*.thong_tin_dang_ky_cu` — cột "thông tin đăng ký hiện tại" phản
    chiếu từ hồ sơ cũ (tiền lệ PLI_M12 X1 không hỏi).
- `when`: chỉ dùng cho biến thể có ô tick tương ứng trên mẫu
  (hkd_cd.* theo chk_tt_chuyen_doi_tu_hkd, csbt.* theo
  chk_tt_chuyen_doi_tu_csbt, gp_ucsn_so theo chk_ctck) — không đoán thêm.
- `required`: CHỈ true theo tiền lệ X1/validator runtime:
  dn.ten_tieng_viet + dn.ma_so_dn (PLI_M12/M27), họ tên người khai/chủ,
  bộ địa chỉ trụ sở, cột tên của bảng ngành (INDUSTRY_REQUIRED) ở các
  "Giấy đề nghị" và cột tên của bảng thành viên/cổ đông khi bảng đó là nội
  dung chính của mẫu (GRID_META ho_ten required). Còn lại false để không
  chặn oan phiếu trắng (quyết định do owner ủy quyền, ghi tại đây).

Chạy (từ ROOT):
  python3 -X utf8 -m tools.build_form_questionnaires            # sinh
  python3 -X utf8 -m tools.build_form_questionnaires --check    # chỉ kiểm
  python3 -X utf8 -m tools.build_form_questionnaires --one PLI_M78
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.questionnaire.schema import validate  # noqa: E402

FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
OUT_DIR = ROOT / "app" / "data" / "questionnaire"

PROVENANCE = "owner_delegated_2026-09-10"

# 21 form được case tham chiếu mà chưa có questionnaire (2026-09-10)
FORMS = [
    "PLI_M01", "PLI_M02", "PLI_M03", "PLI_M04", "PLI_M05", "PLI_M06",
    "PLI_M07", "PLI_M08", "PLI_M09", "PLI_M13", "PLI_M14", "PLI_M15",
    "PLI_M17", "PLI_M19", "PLI_M21", "PLI_M26", "PLI_M28", "PLI_M30",
    "PLI_M31", "PLI_M32", "PLI_M78",
]

# Khối đầu thư / ô phản chiếu — KHÔNG hỏi (xem docstring)
EXCLUDED_KEYS = {
    "so_van_ban", "dia_diem_ky", "ngay_ky_vb", "thang_ky_vb", "nam_ky_vb",
    "co_quan_dkkd", "hs_nop_ngay",
}
EXCLUDED_SUFFIXES = (".chu_ky", ".thong_tin_dang_ky_cu")

GIOI_TINH_OPTIONS = [{"value": "Nam", "label": "Nam"},
                     {"value": "Nữ", "label": "Nữ"}]


# ---------------------------------------------------------------------------
# Bảng văn phong — theo KEY chính xác (dùng chung mọi form có key đó)
# ---------------------------------------------------------------------------

# (text, type, example) — type None = suy theo family
KEY_TEXT: dict = {
    # --- người khai / chủ ---
    "chu_hkd.ho_ten": ("Họ và tên của bạn là gì? (bạn ghi thường, app tự in "
                       "hoa)", "text", "Nguyễn Văn A"),
    "chu_hkd.gioi_tinh": ("Giới tính của bạn?", "select", None),
    "chu_hkd.dan_toc": ("Dân tộc của bạn?", "text", "Kinh"),
    "chu_hkd.quoc_tich": ("Quốc tịch của bạn?", "text", "Việt Nam"),
    "chu_hkd.so_cccd": ("Số giấy tờ pháp lý của bạn (số định danh cá nhân / "
                        "hộ chiếu)?", "text", "079085001234"),
    "ho_ten_in_hoa": ("Họ và tên của bạn là gì? (bạn ghi thường, app tự in "
                      "hoa)", "text", "Nguyễn Văn A"),
    "chu_so_huu.ho_ten": ("Họ và tên chủ sở hữu (mới) là gì? (bạn ghi thường, "
                          "app tự in hoa)", "text", "Nguyễn Văn B"),
    "ndd.ho_ten": ("Họ và tên người đại diện theo pháp luật? (bạn ghi thường, "
                   "app tự in hoa)", "text", "Nguyễn Văn C"),
    "ndd.so_cccd": ("Số định danh cá nhân của người đại diện đang đăng ký?",
                    "text", "079085001234"),
    "ndd.chuc_vu": ("Chức danh của người đại diện (Chủ tịch HĐTV, Chủ tịch "
                    "công ty…)?", "text", "Chủ tịch công ty"),
    "ndd.dien_thoai": ("Số điện thoại của người đại diện (nếu có)?", "tel",
                       "0901234567"),
    "ndd.email": ("Email của người đại diện (nếu có)?", "email", None),
    "ndd.quoc_gia": ("Người đại diện mang quốc gia nào (nếu khác Việt Nam)?",
                     "text", None),
    "quoc_gia": ("Quốc gia (nếu khác Việt Nam)?", "text", None),
    "gd.ho_ten": ("Giám đốc/Tổng giám đốc — họ và tên? (ghi thường, app tự "
                  "in hoa)", "text", "Nguyễn Văn D"),
    "gd.so_cccd": ("Giám đốc/Tổng giám đốc — số định danh cá nhân?", "text",
                   "079085009999"),
    "gd.gioi_tinh": ("Giám đốc/Tổng giám đốc — giới tính?", "select", None),
    "gd.dien_thoai": ("Giám đốc/Tổng giám đốc — số điện thoại (nếu có)?",
                      "tel", "0901234567"),
    "kt.ho_ten": ("Kế toán trưởng/người phụ trách kế toán — họ và tên? (nếu "
                  "chưa có, bỏ trống)", "text", None),
    "kt.so_cccd": ("Kế toán trưởng — số định danh cá nhân?", "text", None),
    "kt.gioi_tinh": ("Kế toán trưởng — giới tính?", "select", None),
    "kt.dien_thoai": ("Kế toán trưởng — số điện thoại (nếu có)?", "tel",
                      None),
    # --- liên hệ, trụ sở ---
    "dia_chi_chi_tiet": ("Địa chỉ trụ sở chính ở đâu? (số nhà/phòng, ngách/"
                         "hẻm, ngõ/kiệt, đường/phố, tổ/xóm/ấp/thôn)", "text",
                         "25 Nguyễn Trãi, Phường Bến Thành"),
    "xa_phuong": ("Trụ sở ở xã/phường/đặc khu nào?", "text",
                  "Phường Bến Thành"),
    "tinh_thanh": ("Trụ sở ở tỉnh/thành phố nào?", "text",
                   "TP. Hồ Chí Minh"),
    "dien_thoai_lien_he": ("Số điện thoại liên hệ (nếu có)?", "tel",
                           "0901234567"),
    "dien_thoai_khac": ("Số điện thoại khác (nếu có)?", "tel", None),
    "email_tru_so": ("Email liên hệ (nếu có)?", "email", None),
    "fax": ("Số fax (nếu có)?", "text", None),
    "website": ("Website (nếu có)?", "text", None),
    # --- giấy tờ cá nhân ---
    "ngay_cap": ("Giấy tờ pháp lý của bạn được cấp ngày nào? (dd/mm/yyyy)",
                 "date", "10/01/2021"),
    "noi_cap": ("Giấy tờ pháp lý của bạn do nơi nào cấp?", "text",
                "Cục Trưởng Cục CSCĐ"),
    "ngay_het_han": ("Giấy tờ pháp lý có ngày hết hạn không? (dd/mm/yyyy, "
                     "bỏ trống nếu không có)", "date", None),
    # --- tên doanh nghiệp ---
    "dn.ten_tieng_viet": ("Tên doanh nghiệp (bạn ghi thường, app tự in hoa)?",
                          "text", "Công ty TNHH An Phát"),
    "dn.ten_nuoc_ngoai": ("Tên doanh nghiệp viết bằng tiếng nước ngoài (nếu "
                          "có)?", "text", None),
    "dn.ten_viet_tat": ("Tên doanh nghiệp viết tắt (nếu có)?", "text", None),
    "dn.ma_so_dn": ("Mã số doanh nghiệp/mã số thuế của doanh nghiệp?",
                    "text", "0312345678"),
    # --- hộ kinh doanh được chuyển đổi / doanh nghiệp gốc ---
    "hkd_cd.ten_hkd": ("Tên hộ kinh doanh được chuyển đổi là gì?", "text",
                       "Hộ kinh doanh An Phát"),
    "hkd_ma_so": ("Mã số hộ kinh doanh/mã số thuế của hộ được chuyển đổi?",
                  "text", "0312345678"),
    "hkd_cd.dia_chi": ("Địa chỉ trụ sở hộ kinh doanh được chuyển đổi?",
                       "text", "25 Nguyễn Trãi, Phường Bến Thành"),
    "hkd_cd.ten_chu_ho": ("Tên chủ hộ kinh doanh được chuyển đổi?", "text",
                          "Nguyễn Văn A"),
    "dn_goc.ten_doanh_nghiep": ("Tên doanh nghiệp gốc (trường hợp tách/chia/"
                                "hợp nhất/chuyển đổi — nếu có)?", "text",
                                None),
    "dn_goc.ma_so_dn": ("Mã số doanh nghiệp/mã số thuế của doanh nghiệp gốc "
                        "(nếu có)?", "text", None),
    "so_giay_to_ca_nhan": ("Số giấy tờ pháp lý của cá nhân theo Giấy chứng "
                           "nhận đã cấp (nếu có)?", "text", None),
    # --- cơ sở bảo trợ xã hội ---
    "csbt.ten": ("Tên cơ sở bảo trợ xã hội/quỹ xã hội/quỹ từ thiện được "
                 "chuyển đổi?", "text", None),
    "csbt.so_gcn": ("Số Giấy chứng nhận đăng ký thành lập/Giấy phép thành "
                    "lập của cơ sở đó?", "text", None),
    "csbt.ngay_cap": ("Giấy đó được cấp ngày nào? (dd/mm/yyyy)", "date",
                      None),
    "csbt.ma_so_thue": ("Mã số thuế của cơ sở đó (10 số, nếu có)?", "text",
                        None),
    "csbt.dia_chi": ("Địa chỉ trụ sở chính của cơ sở đó?", "text", None),
    "csbt.ten_nguoi_dai_dien": ("Tên người đại diện của cơ sở đó?", "text",
                                None),
    # --- vốn ---
    "von_dau_tu_so": ("Vốn đầu tư là bao nhiêu? (VNĐ, ghi bằng số)",
                      "money", "500.000.000"),
    "von_dau_tu_chu": ("Vốn đầu tư viết bằng chữ?", "text",
                       "Năm trăm triệu đồng"),
    "von_dieu_le": ("Vốn điều lệ là bao nhiêu? (VNĐ, ghi bằng số)", "money",
                    "5.000.000.000"),
    "von_dieu_le_chu": ("Vốn điều lệ viết bằng chữ?", "text",
                        "Năm tỷ đồng"),
    "gia_tri_ntte": ("Nếu góp vốn bằng ngoại tệ: giá trị tương đương và loại "
                     "ngoại tệ?", "text", "20.000 USD"),
    "menh_gia_co_phan": ("Mệnh giá một cổ phần là bao nhiêu? (VNĐ)", "money",
                         "10.000"),
    "ma_so_du_an": ("Mã số dự án đầu tư (nếu có)?", "text", None),
    "co_quan_cap": ("Mã số dự án do cơ quan nào cấp?", "text", None),
    # --- hoạt động ---
    "so_lao_dong": ("Dự kiến dùng bao nhiêu lao động?", "integer", "10"),
    "ap_dung_tu": ("Mức đóng bảo hiểm xã hội áp dụng từ ngày nào? "
                   "(dd/mm/yyyy, nếu có)", "date", None),
    "vppd_noi_dung": ("Nội dung hoạt động của văn phòng đại diện là gì? "
                      "(chỉ kê khai đối với VPĐĐ)", "text",
                      "Liên hệ, thị trường"),
    # --- chi nhánh / địa điểm ---
    "cn.ten_tieng_viet": ("Tên chi nhánh/văn phòng đại diện/địa điểm kinh "
                          "doanh? (ghi thường, app tự in hoa)", "text",
                          "Chi nhánh Quận 1"),
    "cn.ten_viet_tat": ("Tên viết tắt (nếu có)?", "text", None),
    "cn.ten_nuoc_ngoai": ("Tên viết bằng tiếng nước ngoài sau khi thay đổi "
                          "(nếu có)?", "text", None),
    "cn.ma_so": ("Mã số chi nhánh/mã số thuế của chi nhánh (nếu đã cấp)?",
                 "text", None),
    "cn.dia_chi": ("Địa chỉ chi nhánh?", "text", None),
    # --- giấy chứng nhận hiện có ---
    "so_gcn_dkkd": ("Số Giấy chứng nhận đăng ký kinh doanh (chỉ kê khai nếu "
                    "chưa có mã số doanh nghiệp)?", "text", None),
    "ly_do_de_nghi": ("Lý do đề nghị cấp lại là gì? (bị rách nát, mất, thay "
                      "đổi nội dung…)", "text", "Giấy chứng nhận bị mất"),
    "ve_viec": ("Nghị quyết/quyết định giải thể bị hủy mang số mấy?", "text",
                "12/2026/NQ-HĐTV"),
    # --- M32: công bố nội dung ---
    "dk_thay_doi_lan_thu": ("Doanh nghiệp đã đăng ký thay đổi nội dung lần "
                            "thứ mấy?", "integer", "1"),
}

# --- key giống nhau, cách hỏi khác nhau theo FORM --------------------------
FORM_KEY_TEXT: dict = {
    ("PLI_M02", "to_chuc.ten"): ("Nếu chủ sở hữu là TỔ CHỨC: tên tổ chức là "
                                 "gì? (ghi thường, app tự in hoa)", "text",
                                 "Công ty CP Đầu tư ABC"),
    ("PLI_M02", "dn.ma_so_dn"): ("Mã số doanh nghiệp/Số Quyết định thành lập "
                                 "của tổ chức chủ sở hữu?", "text",
                                 "0312345678"),
    ("PLI_M03", "to_chuc.ten"): ("Nếu thành viên là TỔ CHỨC: tên tổ chức là "
                                 "gì? (ghi thường, app tự in hoa)", "text",
                                 "Công ty CP Đầu tư ABC"),
    ("PLI_M03", "dn.ma_so_dn"): ("Mã số doanh nghiệp/Số Quyết định thành lập "
                                 "của tổ chức thành viên?", "text",
                                 "0312345678"),
    ("PLI_M04", "to_chuc.ten"): ("Nếu cổ đông sáng lập lớn nhất là TỔ CHỨC: "
                                 "tên tổ chức là gì?", "text",
                                 "Công ty CP Đầu tư ABC"),
    ("PLI_M04", "dn.ma_so_dn"): ("Mã số doanh nghiệp/Số Quyết định thành lập "
                                 "của tổ chức đó?", "text", "0312345678"),
    ("PLI_M04", "ho_ten_in_hoa"): ("Cổ đông sáng lập là cá nhân lớn nhất — "
                                   "họ và tên? (bạn ghi thường, app tự in "
                                   "hoa)", "text", "Nguyễn Văn A"),
    ("PLI_M05", "ho_ten_in_hoa"): ("Thành viên hợp danh chịu trách nhiệm vô "
                                   "hạn — họ và tên người đại diện? (ghi "
                                   "thường, app tự in hoa)", "text",
                                   "Nguyễn Văn A"),
    ("PLI_M13", "ndd.ho_ten"): ("Người đại diện theo pháp luật MỚI là ai — "
                                "họ và tên? (bạn ghi thường, app tự in hoa)",
                                "text", "Nguyễn Văn C"),
    ("PLI_M19", "cn.ten_tieng_viet"): ("Tên chi nhánh/VPĐĐ/địa điểm kinh "
                                       "doanh đang đăng ký là gì?", "text",
                                       "Chi nhánh Quận 1"),
    ("PLI_M19", "cn.dia_chi"): ("Địa chỉ chi nhánh đang đăng ký?", "text",
                                "25 Nguyễn Trãi, Phường Bến Thành"),
    # M26/M28: tên CN trong đề nghị/chấm dứt là chi nhánh cụ thể
    ("PLI_M28", "ngay_cap"): ("Giấy chứng nhận đăng ký kinh doanh được cấp "
                              "ngày nào? (dd/mm/yyyy)", "date", None),
    ("PLI_M30", "ngay_cap"): ("Giấy chứng nhận đăng ký kinh doanh được cấp "
                              "ngày nào? (dd/mm/yyyy)", "date", None),
    ("PLI_M31", "ngay_cap"): ("Giấy chứng nhận đăng ký kinh doanh được cấp "
                              "ngày nào? (dd/mm/yyyy)", "date", None),
    ("PLI_M78", "dien_thoai_khac"): ("Số điện thoại liên hệ của bạn?", "tel",
                                     "0901234567"),
}

# --- nhãn ô tick: ghi đè cho các checkbox mơ hồ -----------------------------
CHK_TEXT: dict = {
    "chk_co": "Có",
    "chk_khong": "Không",
    "chk_auto_co": "Có (có GCN quyền sử dụng đất tại đảo/xã phường biên giới)",
    "chk_auto_khong": ("Không (không có GCN quyền sử dụng đất tại đảo/xã "
                       "phường biên giới)"),
    "chk_auto_co_2": "Có hiển thị giá trị tương đương ngoại tệ trên GCN",
    "chk_auto_khong_2":
        "Không hiển thị giá trị tương đương ngoại tệ trên GCN",
    "chk_auto_co_hien_thi_thong_tin_ve_gia_tri_tuong_d":
        "Có hiển thị giá trị tương đương ngoại tệ trên GCN",
}

# nhóm câu hỏi theo prefix key
GROUP_BY_PREFIX = [
    ("chk_tt_", "Trường hợp thành lập doanh nghiệp"),
    ("chk_gt_", "Loại giấy tờ pháp lý của cá nhân"),
    ("chk_ht_", "Chế độ kế toán và báo cáo tài chính"),
    ("chk_gtgt_", "Thuế giá trị gia tăng"),
    ("chk_bc_", "Bảo hiểm xã hội (phương thức đóng)"),
    ("chk_khu_", "Vị trí đặt trụ sở/địa điểm"),
    ("csbt.", "Chuyển đổi từ cơ sở bảo trợ xã hội/quỹ (nếu có)"),
    ("hkd_cd.", "Chuyển đổi từ hộ kinh doanh (nếu có)"),
    ("ds_nganh", "Ngành, nghề kinh doanh"),
    ("ds_thanh_vien_tnhh", "Danh sách thành viên công ty"),
    ("ds_co_dong_sang_lap", "Danh sách cổ đông sáng lập"),
    ("ds_co_dong_nn", "Cổ đông là nhà đầu tư nước ngoài"),
    ("ds_thanh_vien_hop_danh", "Danh sách thành viên công ty hợp danh"),
    ("ds_ndd_pl_sau_thay_doi", "Người đại diện theo pháp luật sau thay đổi"),
    ("ds_nddpl_uy_quyen_chu_so_huu_moi",
     "Người đại diện được ủy quyền của chủ sở hữu mới (nếu tổ chức)"),
    ("ds_nddpl_uy_quyen_chu_so_huu",
     "Người đại diện được ủy quyền của chủ sở hữu tổ chức (nếu có)"),
    ("ds_san_pham_yeu_cau", "Sản phẩm thông tin yêu cầu"),
    ("nguon_von_dieu_le", "Nguồn vốn điều lệ"),
    ("co_cau_loai_co_phan", "Cơ cấu loại cổ phần"),
    ("co_phan_duoc_quyen_chao_ban", "Cổ phần được quyền chào bán"),
    ("co_cau_tai_san_gop_von_dau_tu", "Cơ cấu tài sản góp vốn đầu tư"),
    ("co_cau_tai_san_gop_von_dieu_le", "Cơ cấu tài sản góp vốn điều lệ"),
    ("gd.", "Giám đốc/Tổng giám đốc"),
    ("kt.", "Kế toán trưởng/người phụ trách kế toán"),
    ("ndd.", "Người đại diện theo pháp luật"),
    ("chu_so_huu.", "Chủ sở hữu công ty"),
    ("chu_hkd.", "Về người khai hồ sơ"),
    ("dn_goc.", "Doanh nghiệp gốc (tách/chia/hợp nhất — nếu có)"),
    ("cn.", "Về chi nhánh/văn phòng đại diện/địa điểm kinh doanh"),
    ("to_chuc.", "Chủ sở hữu/thành viên là tổ chức (nếu có)"),
    ("dk_thay_doi", "Thông tin đăng ký thay đổi"),
    ("dn.ten_", "Về tên doanh nghiệp"),
    ("dn.", "Thông tin doanh nghiệp"),
    ("dia_chi_chi_tiet", "Về trụ sở chính"),
    ("xa_phuong", "Về trụ sở chính"),
    ("tinh_thanh", "Về trụ sở chính"),
    ("ngay_cap", "Giấy tờ pháp lý đã cấp"),
    ("noi_cap", "Giấy tờ pháp lý đã cấp"),
    ("ngay_het_han", "Giấy tờ pháp lý đã cấp"),
    ("so_giay_to_ca_nhan", "Giấy tờ pháp lý đã cấp"),
    ("so_gcn_dkkd", "Giấy chứng nhận hiện có"),
    ("dien_thoai_lien_he", "Số liên hệ"),
    ("dien_thoai_khac", "Số liên hệ"),
    ("email_tru_so", "Số liên hệ"),
    ("fax", "Số liên hệ"),
    ("website", "Số liên hệ"),
    ("von_dieu_le", "Vốn"),
    ("von_dau_tu", "Vốn"),
    ("menh_gia_co_phan", "Vốn"),
    ("gia_tri_ntte", "Vốn"),
    ("ma_so_du_an", "Dự án đầu tư / giấy phép (nếu có)"),
    ("co_quan_cap", "Dự án đầu tư / giấy phép (nếu có)"),
    ("gp_ucsn_so", "Dự án đầu tư / giấy phép (nếu có)"),
    ("so_lao_dong", "Bắt đầu hoạt động và lao động"),
    ("ap_dung_tu", "Bảo hiểm xã hội (phương thức đóng)"),
    ("ly_do_de_nghi", "Nội dung đề nghị"),
    ("ve_viec", "Nội dung đề nghị"),
    ("vppd_noi_dung", "Nội dung đề nghị"),
]

# family theo TÊN CUỐI của key (fallback khi KEY_TEXT không có)
SUFFIX_TEXT: dict = {
    "ho_ten": ("Họ và tên?", "text", "Nguyễn Văn A"),
    "ten_doanh_nghiep": ("Tên doanh nghiệp?", "text", None),
    "ten_cd": ("Tên cổ đông?", "text", None),
    "ten_nguoi_dai_dien": ("Tên người đại diện?", "text", None),
    "ten_thanh_vien": ("Tên thành viên?", "text", None),
    "ten_san_pham": ("Tên sản phẩm (ghi rõ, nếu có)?", "text", None),
    "gioi_tinh": ("Giới tính?", "select", None),
    "dan_toc": ("Dân tộc?", "text", "Kinh"),
    "quoc_tich": ("Quốc tịch?", "text", "Việt Nam"),
    "quoc_gia": ("Quốc gia (nếu khác Việt Nam)?", "text", None),
    "dia_chi": ("Địa chỉ liên lạc?", "text", "25 Nguyễn Trãi"),
    "dien_thoai": ("Số điện thoại (nếu có)?", "tel", None),
    "so_cccd": ("Số định danh cá nhân/số giấy tờ pháp lý?", "text",
                "079085001234"),
    "giay_to_so": ("Số giấy tờ pháp lý?", "text", None),
    "giay_to_ngay": ("Giấy tờ cấp ngày nào? (dd/mm/yyyy)", "date", None),
    "giay_to_co_quan": ("Giấy tờ do cơ quan nào cấp?", "text", None),
    "ngay_sinh": ("Ngày, tháng, năm sinh? (dd/mm/yyyy)", "date",
                  "05/12/1985"),
    "von_dong_gop": ("Phần vốn góp là bao nhiêu? (VNĐ)", "money",
                     "2.000.000.000"),
    "von_duoc_uy_quyen_vnd": ("Phần vốn được ủy quyền (VNĐ)?", "money", None),
    "ty_le_von": ("Tỷ lệ vốn góp (%)?", "text", "40"),
    "ty_le": ("Tỷ lệ (%)?", "text", "40"),
    "thoi_han_gop_von": ("Thời hạn góp vốn?", "text", "Trước 31/12/2026"),
    "loai_tai_san_gop_von": ("Loại tài sản góp vốn (nếu góp bằng tài sản)?",
                             "text", None),
    "so_co_phan": ("Tổng số cổ phần?", "integer", "1000"),
    "so_luong": ("Số lượng?", "integer", None),
    "so_luong_san_pham": ("Số lượng sản phẩm yêu cầu?", "money", "1"),
    "ghi_chu": ("Ghi chú thêm (nếu có)?", "text", None),
    "ma_nganh": ("Mã ngành (app tra VSIC giúp — không cần điền)", "text",
                 None),
    "ten_nganh": ("Tên ngành, nghề kinh doanh?", "text",
                  "Bán lẻ hàng điện tử"),
    "chi_tiet": ("Chi tiết hoạt động ngành?", "text", None),
    "la_nganh_chinh": ("Đây có phải ngành nghề chính không? (đánh X vào đúng "
                       "một dòng)", "mark", None),
    "so_tien_vnd_va_tuong_duong": ("Số tiền (VNĐ, nếu có)?", "money", None),
    "chi_tiet_ngoai_te_tai_san_khac": ("Chi tiết bằng ngoại tệ (loại ngoại "
                                       "tệ, nếu có)?", "text", None),
    "gia_tri_vnd": ("Giá trị (VNĐ, nếu có)?", "money", None),
}

ASSET_TYPE_TEXT = {
    "dong_viet_nam": "Tiền Việt Nam",
    "ngoai_te_tu_do_chuyen_doi": "Ngoại tệ tự do chuyển đổi",
    "quyen_so_huu_tri_tue": "Quyền sở hữu trí tuệ",
    "quyen_su_dung_dat": "Quyền sử dụng đất",
    "tai_san_khac": "Tài sản khác",
    "vang": "Vàng",
}
CO_PHAN_TYPE_TEXT = {
    "co_phan_pho_thong": "Cổ phần phổ thông",
    "cp_uu_dai_bieu_quyet": "Cổ phần ưu đãi biểu quyết",
    "cp_uu_dai_co_tuc": "Cổ phần ưu đãi cổ tức",
    "cp_uu_dai_hoan_lai": "Cổ phần ưu đãi hoàn lại",
    "cp_uu_dai_khac": "Cổ phần ưu đãi khác",
}
NGUON_VON_TEXT = {
    "von_khac": "Vốn khác",
    "von_ngan_sach_nha_nuoc": "Vốn ngân sách nhà nước",
    "von_nuoc_ngoai": "Vốn đầu tư nước ngoài",
    "von_tu_nhan": "Vốn tư nhân trong nước",
}
SAN_PHAM_TEXT = {
    "sp_gcn_dkdn": "Bản Giấy chứng nhận đăng ký doanh nghiệp",
    "sp_lich_su_3_nam": "Thông tin lịch sử 3 năm của doanh nghiệp",
    "sp_thong_tin_moi_nhat": "Thông tin doanh nghiệp mới nhất",
    "san_pham_khac": "Sản phẩm khác",
}

# required=true CHỈ theo tiền lệ X1/validator (xem docstring)
REQUIRED_EXACT = {
    "dn.ten_tieng_viet", "dn.ma_so_dn",
    "chu_hkd.ho_ten", "chu_so_huu.ho_ten",
    "dia_chi_chi_tiet", "xa_phuong", "tinh_thanh",
}
# (form, key) required thêm — form-specific
FORM_REQUIRED_EXACT = {
    ("PLI_M28", "cn.ten_tieng_viet"),   # chấm dứt hoạt động: phải xác định CN
    ("PLI_M28", "cn.ma_so"),
    ("PLI_M13", "ndd.ho_ten"),          # cốt lõi M13: người đại diện MỚI
    # chủ sở hữu/chủ DN là chủ thể của mẫu — bắt buộc; M03/M04/M17/M19 có
    # ho_ten_in_hoa ở section phụ nên KHÔNG bắt buộc để không chặn oan
    ("PLI_M02", "ho_ten_in_hoa"),
    ("PLI_M14", "ho_ten_in_hoa"),
}
REQUIRED_TABLE_FIRST = {
    ("ds_nganh", "ten_nganh"),
    ("ds_thanh_vien_tnhh", "ho_ten"),
    ("ds_co_dong_sang_lap", "ho_ten"),
    ("ds_thanh_vien_hop_danh", "ho_ten"),
    ("ds_ndd_pl_sau_thay_doi", "ho_ten"),
}
# bảng ngành chỉ bắt buộc ở CÁC "Giấy đề nghị" (INDUSTRY_REQUIRED + minRows 1);
# cột tên bảng thành viên/cổ đông chỉ bắt buộc khi bảng là nội dung chính mẫu.
FORMS_INDUSTRY_REQUIRED = {
    "PLI_M01", "PLI_M02", "PLI_M03", "PLI_M04", "PLI_M05",
    "PLI_M17", "PLI_M19", "PLI_M21",
}
FORMS_TABLE_REQUIRED = {
    "PLI_M06": "ds_thanh_vien_tnhh",
    "PLI_M07": "ds_co_dong_sang_lap",
    "PLI_M09": "ds_thanh_vien_hop_danh",
    "PLI_M13": "ds_ndd_pl_sau_thay_doi",
}
# form "thay đổi" mới có dn.ma_so_dn bắt buộc; form thành lập không có key này
FORMS_CHANGE = {
    "PLI_M13", "PLI_M14", "PLI_M15", "PLI_M17", "PLI_M19", "PLI_M21",
    "PLI_M26", "PLI_M28", "PLI_M30", "PLI_M31", "PLI_M32",
}

# biến thể có ô tick tương ứng -> when
WHEN_BY_PREFIX = [
    ("csbt.", "chk_tt_chuyen_doi_tu_csbt"),
    ("hkd_cd.", "chk_tt_chuyen_doi_tu_hkd"),
]

DATE_TRIPLETS = {  # key ngày -> (tháng, năm)
    "ngay_sinh": ("thang_sinh", "nam_sinh"),
    "ngay_bd": ("thang_bd", "nam_bd"),
}


class GenError(ValueError):
    """Lỗi sinh questionnaire — fail-loud, không ghi artifact."""


# ---------------------------------------------------------------------------
# Đọc nhãn checkbox từ blocks (nguồn nhãn pháp lý gốc)
# ---------------------------------------------------------------------------

def chk_labels_of(form_id: str) -> dict:
    """key checkbox -> nhãn gốc trên mẫu (blocks runs t=='chk')."""
    path = BLOCKS_DIR / ("%s.json" % form_id)
    out: dict = {}
    if not path.exists():
        return out
    data = json.loads(path.read_text(encoding="utf-8"))
    for blk in data.get("blocks", []):
        for run in blk.get("runs", []):
            if isinstance(run, dict) and run.get("t") == "chk" and \
                    run.get("key"):
                out.setdefault(str(run["key"]), str(run.get("label") or ""))
    return out


# ---------------------------------------------------------------------------
# Sinh câu hỏi
# ---------------------------------------------------------------------------

def _clean_label(label) -> str:
    text = " ".join(str(label or "").split())
    while text and (text[-1].isdigit() or text[-1] == ")") and "(" in text:
        text = text[:text.rfind("(")].strip()
    while text and text[-1].isdigit():          # footnote "Tôi là1"
        text = text[:-1].rstrip(" .:,")
    return text.strip(" .:,?").strip()


def _group_of(key: str) -> str:
    for prefix, group in GROUP_BY_PREFIX:
        if key.startswith(prefix):
            return group
    return "Các khai báo khác"


def _base_type(key: str) -> str:
    leaf = key.rsplit(".", 1)[-1]
    if leaf.startswith("dien_thoai"):
        return "tel"
    if leaf.startswith("email"):
        return "email"
    if leaf.startswith(("von_", "gia_tri", "menh_gia", "so_tien",
                        "phan_von")):
        return "money"
    if leaf in ("so_lao_dong", "so_luong", "dk_thay_doi_lan_thu") or \
            leaf.endswith("so_co_phan") or leaf.endswith(".so_luong"):
        return "integer"
    if leaf.startswith("ngay") or leaf == "ap_dung_tu" or \
            leaf == "giay_to_ngay" or leaf.endswith("ngay_cap"):
        return "date"
    return "text"


def _nice_leaf_prefix(key: str):
    """key dạng group.<mid>.<leaf> -> (nhãn đẹp của mid, leaf)."""
    parts = key.split(".")
    leaf = parts[-1]
    for prefix, labels in (
            ("co_cau_tai_san_gop_von_dau_tu.", ASSET_TYPE_TEXT),
            ("co_cau_tai_san_gop_von_dieu_le.", ASSET_TYPE_TEXT),
            ("nguon_von_dieu_le.", NGUON_VON_TEXT),
            ("ds_san_pham_yeu_cau.", SAN_PHAM_TEXT)):
        if key.startswith(prefix):
            mid = key[len(prefix):].split(".")[0]
            return labels.get(mid), leaf
    if key.startswith("co_cau_loai_co_phan.") or \
            key.startswith("co_phan_duoc_quyen_chao_ban."):
        mid = key.split(".")[1]
        return CO_PHAN_TYPE_TEXT.get(mid), leaf
    return None, leaf


def _scalar_spec(form_id: str, key: str, chk_labels: dict):
    """key đơn -> (text, type, example, options) hoặc None nếu không biết."""
    if key.startswith("chk_"):
        label = CHK_TEXT.get(key) or _clean_label(chk_labels.get(key)) or \
            _clean_label(key[4:].replace("_", " "))
        return ("Bạn có thuộc/không — đánh X vào ô: %s?" % label,
                "mark", None, [{"value": "X", "label": label}])

    spec = FORM_KEY_TEXT.get((form_id, key)) or KEY_TEXT.get(key)
    if spec:
        text, qtype, example = spec
        return (text, qtype, example,
                GIOI_TINH_OPTIONS if qtype == "select" else None)

    nice, leaf = _nice_leaf_prefix(key)
    if nice is not None:
        if leaf == "ty_le" or leaf == "ty_le_so_von_dieule":
            return ("%s — chiếm tỷ lệ (%%)?" % nice, "text", None, None)
        if leaf == "so_luong":
            return ("%s — số lượng là bao nhiêu?" % nice, "integer", None,
                    None)
        if leaf == "so_luong_san_pham":
            return ("%s — bạn cần bao nhiêu bản?" % nice, "money", "1", None)
        if leaf == "gia_tri_vnd":
            return ("%s — giá trị bao nhiêu (VNĐ, nếu có)?" % nice, "money",
                    None, None)
        if leaf == "so_co_phan":
            return ("%s — số cổ phần?" % nice, "integer", None, None)
        if leaf == "so_tien_vnd_va_tuong_duong":
            return ("%s — số tiền (VNĐ, nếu có)?" % nice, "money", None,
                    None)
        if leaf == "chi_tiet_ngoai_te_tai_san_khac":
            return ("%s — chi tiết bằng ngoại tệ (loại ngoại tệ, nếu có)?"
                    % nice, "text", None, None)
        if leaf == "ten_san_pham":
            return ("%s — ghi rõ tên/mô tả (nếu có)?" % nice, "text", None,
                    None)
        return ("%s — %s?" % (nice, _clean_label(leaf)), None, None, None)

    if leaf in SUFFIX_TEXT:
        text, qtype, example = SUFFIX_TEXT[leaf]
        if qtype == "mark":
            return (text, qtype, example, [{"value": "X", "label": "X"}])
        return (text, qtype, example,
                GIOI_TINH_OPTIONS if qtype == "select" else None)
    return None


def _required_of(form_id: str, key: str) -> bool:
    if (form_id, key) in FORM_REQUIRED_EXACT:
        return True
    if key in REQUIRED_EXACT:
        if key == "dn.ma_so_dn":
            return form_id in FORMS_CHANGE
        return True
    return False


def _slug(key: str, seq: int) -> str:
    """key -> đoạn cuối của question_id; dùng CẢ key (dots->_) để không trùng
    giữa `ngay_cap` và `csbt.ngay_cap` trong cùng form."""
    slug = str(key).replace(".", "_").strip("_") or "k%d" % seq
    return slug[:60]


def build_questions(form_id: str, entry: dict) -> list:
    """form_maps entry -> list câu hỏi (đúng schema v1, phủ mọi key cần hỏi)."""
    fields = entry.get("fields", [])
    labels = {f["key"]: f.get("label") or "" for f in fields}
    raw_keys = [f["key"] for f in fields if f.get("key")]
    chk_labels = chk_labels_of(form_id)

    # key bảng lặp (dynamic_tables) xử lý riêng
    table_keys: set = set()
    tables: list = []
    for dt in entry.get("dynamic_tables", []):
        loop = dt.get("loop")
        if not loop:
            continue
        tables.append(dt)
        for col in dt.get("columns", []):
            if col.get("tag"):
                table_keys.add("%s.%s" % (loop, col["tag"]))

    # key cần hỏi (single): trừ bảng lặp + excluded
    single_keys: list = []
    for key in raw_keys:
        if key in table_keys or key in EXCLUDED_KEYS:
            continue
        if key.endswith(EXCLUDED_SUFFIXES):
            continue
        single_keys.append(key)

    questions: list = []
    seq = 0

    # ---- bộ ba ngày -------------------------------------------------------
    # prefix-aware: "ngay_sinh" lẫn "gd.ngay_sinh"/"kt.ngay_sinh"/"ndd.…"
    keys_set = set(single_keys)
    triplets: dict = {}
    for prefix in ("", "gd.", "kt.", "ndd."):
        for day_leaf, (mleaf, yleaf) in DATE_TRIPLETS.items():
            day_key, mkey, ykey = prefix + day_leaf, prefix + mleaf, \
                prefix + yleaf
            if {day_key, mkey, ykey} <= keys_set:
                triplets[day_key] = [day_key, mkey, ykey]
    if {"dk_thay_doi_ngay", "dk_thay_doi_thang",
        "dk_thay_doi_nam"} <= keys_set:
        triplets["dk_thay_doi_ngay"] = ["dk_thay_doi_ngay",
                                        "dk_thay_doi_thang",
                                        "dk_thay_doi_nam"]
    triplet_members = {k for trio in triplets.values() for k in trio}

    # ---- key đơn -----------------------------------------------------------
    for key in single_keys:
        if key in triplet_members:
            continue
        spec = _scalar_spec(form_id, key, chk_labels)
        if spec is None:
            clean = _clean_label(labels.get(key))
            if not clean:
                raise GenError(
                    "%s: không sinh được câu cho key %r — thêm bảng văn "
                    "phong" % (form_id, key))
            qtype = _base_type(key)
            spec = ("%s?" % clean, qtype, None,
                    GIOI_TINH_OPTIONS if qtype == "select" else None)
        text, qtype, example, options = spec
        seq += 1
        item = {
            "question_id": "q_%s_%s" % (_form_slug(form_id),
                                        _slug(key, seq)),
            "group": _group_of(key),
            "text": text,
            "type": qtype,
        }
        if options:
            item["options"] = options
        if example:
            item["example"] = example
        if _required_of(form_id, key):
            item["required"] = True
        item["version"] = 1
        for prefix, mark_key in WHEN_BY_PREFIX:
            if key.startswith(prefix):
                item["when"] = {mark_key: ["X"]}
        if key == "gp_ucsn_so":
            item["when"] = {"chk_ctck": ["X"]}
        item["data_key"] = key
        questions.append(item)

    # ---- câu ngày bộ ba ----------------------------------------------------
    for day_key, trio in triplets.items():
        prefix = day_key.split(".")[0] if "." in day_key else ""
        if day_key == "dk_thay_doi_ngay":
            text = "Việc đăng ký thay đổi nội dung được đăng ký vào ngày " \
                   "nào? (dd/mm/yyyy)"
            group = "Thông tin đăng ký thay đổi"
        elif "sinh" in day_key:
            who = {"gd": "Giám đốc/Tổng giám đốc",
                   "kt": "Kế toán trưởng",
                   "ndd": "Người đại diện theo pháp luật",
                   "": "Bạn"}.get(prefix, prefix)
            text = "%s — ngày, tháng, năm sinh? (dd/mm/yyyy)" % who
            group = _group_of(day_key)
        else:
            who = {"gd": "Giám đốc/Tổng giám đốc", "kt": "Kế toán trưởng",
                   "ndd": "Người đại diện"}.get(prefix, "")
            head = ("%s — " % who) if who else ""
            text = "%sDoanh nghiệp dự kiến bắt đầu hoạt động từ ngày nào? " \
                   "(dd/mm/yyyy)" % head
            group = "Bắt đầu hoạt động và lao động"
        questions.append({
            "question_id": "q_%s_%s" % (_form_slug(form_id),
                                        _slug(day_key, 0)),
            "group": group,
            "text": text,
            "type": "date",
            "example": "05/12/1985" if "sinh" in day_key else "01/10/2026",
            "version": 1,
            "data_key": [
                {"key": trio[0], "transform": "date_day"},
                {"key": trio[1], "transform": "date_month"},
                {"key": trio[2], "transform": "date_year"},
            ],
        })

    # ---- bảng lặp ----------------------------------------------------------
    for dt in tables:
        loop = dt["loop"]
        group = _group_of(loop + ".x")
        for col in dt.get("columns", []):
            tag = col.get("tag")
            if not tag:
                continue
            key = "%s.%s" % (loop, tag)
            if key.endswith(EXCLUDED_SUFFIXES):
                continue
            header = col.get("header") or labels.get(key) or tag
            spec = _scalar_spec(form_id, key, chk_labels)
            if spec is not None:
                text, qtype, example, options = spec
            else:
                clean = _clean_label(header)
                if not clean:
                    raise GenError(
                        "%s: không sinh được câu cho cột bảng %r"
                        % (form_id, key))
                text, qtype, example, options = \
                    ("%s?" % clean, _base_type(key), None, None)
                if qtype == "select":
                    options = GIOI_TINH_OPTIONS
            if not str(text).endswith("?"):
                text = "%s?" % text.rstrip(".")
            item = {
                "question_id": "q_%s_%s_%s" % (_form_slug(form_id), loop,
                                               tag),
                "group": group,
                "text": text,
                "type": qtype,
                "repeatable": True,
                "row_group": loop,
                "version": 1,
                "data_key": key,
            }
            if options:
                item["options"] = options
            if example and tag != "ten_nganh":
                item["example"] = example
            if tag == "ten_nganh":
                item["example"] = "Bán lẻ hàng điện tử"
            if tag == "ma_nganh":
                item["autofill"] = "vsic"
            if (loop, tag) in REQUIRED_TABLE_FIRST:
                if loop == "ds_nganh":
                    if form_id in FORMS_INDUSTRY_REQUIRED:
                        item["required"] = True
                elif FORMS_TABLE_REQUIRED.get(form_id) == loop:
                    item["required"] = True
            questions.append(item)

    return questions


def _form_slug(form_id: str) -> str:
    """PLI_M01 -> m01 (duy nhất giữa các form trong cùng case)."""
    pl, num = form_id.split("_M")
    return "%s%s" % (pl.replace("PL", "").lower(), num)


# ---------------------------------------------------------------------------
# Self-check phủ key + ghi file
# ---------------------------------------------------------------------------

def coverage_of(form_id: str, entry: dict, questions: list) -> tuple:
    """(keys cần hỏi — đã dedupe, keys đã phủ) — thiếu key do caller fail."""
    need: set = set()
    for f in entry.get("fields", []):
        key = f.get("key")
        if not key or key in EXCLUDED_KEYS or \
                key.endswith(EXCLUDED_SUFFIXES):
            continue
        need.add(key)
    for dt in entry.get("dynamic_tables", []):
        for col in dt.get("columns", []):
            key = "%s.%s" % (dt.get("loop"), col.get("tag"))
            if not col.get("tag") or key.endswith(EXCLUDED_SUFFIXES):
                continue
            need.add(key)
    got: set = set()
    for item in questions:
        dk = item["data_key"]
        if isinstance(dk, str):
            got.add(dk)
        else:
            got.update(t["key"] for t in dk)
    return need, got


def build_one(form_id: str, form_maps: dict) -> dict:
    entry = form_maps.get(form_id)
    if not entry:
        raise GenError("DOC_NOT_FOUND: form_maps.json không có %r" % form_id)
    questions = build_questions(form_id, entry)
    if not questions:
        raise GenError("%s: không sinh được câu nào" % form_id)

    need, got = coverage_of(form_id, entry, questions)
    missing = sorted(need - got)
    if missing:
        raise GenError("%s: self-check PHỦ KEY THẤT BẠI — %d key chưa có câu "
                       "hỏi: %s" % (form_id, len(missing), ", ".join(missing)))

    q = {
        "doc_id": form_id,
        "title": entry.get("ten_mau") or form_id,
        "questionnaire_version": 1,
        "cluster": _cluster_of(form_id),
        "content_note": ("Nội dung sinh bởi tools.build_form_questionnaires "
                         "theo ủy quyền owner %s (owner_delegated_2026-09-10)"
                         % PROVENANCE),
        "questions": questions,
    }
    for item in questions:   # mark không có options thì importer BAD_SELECT
        if item["type"] in ("mark", "select") and not item.get("options"):
            raise GenError("%s: câu %s thiếu options" % (form_id,
                                                         item["question_id"]))
    validate(q, form_maps)          # schema v1 — sai key/type = fail-loud
    return q


CLUSTER_OF = {
    "PLI_M01": "dn_thanh_lap", "PLI_M02": "dn_thanh_lap",
    "PLI_M03": "dn_thanh_lap", "PLI_M04": "dn_thanh_lap",
    "PLI_M05": "dn_thanh_lap", "PLI_M06": "dn_thanh_lap",
    "PLI_M07": "dn_thanh_lap", "PLI_M08": "dn_thanh_lap",
    "PLI_M09": "dn_thanh_lap", "PLI_M13": "dn_thay_doi",
    "PLI_M14": "dn_thay_doi", "PLI_M15": "dn_thay_doi",
    "PLI_M17": "cn_vpdd", "PLI_M19": "cn_vpdd",
    "PLI_M21": "cap_doi_cn", "PLI_M26": "cap_doi_cn",
    "PLI_M28": "cn_vpdd", "PLI_M30": "giai_the", "PLI_M31": "giai_the",
    "PLI_M32": "cong_bo_tt", "PLI_M78": "cong_bo_tt",
}


def _cluster_of(form_id: str) -> str:
    return CLUSTER_OF.get(form_id, "khac")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="chỉ dựng + validate + phủ key, KHÔNG ghi file")
    ap.add_argument("--force", action="store_true",
                    help="ghi ĐÈ form thuộc danh sách E4/E5 dù file đã có "
                         "(7 file X1 vẫn không bao giờ bị đụng)")
    ap.add_argument("--one", metavar="FORM_ID",
                    help="chỉ sinh form này (vd PLI_M78)")
    args = ap.parse_args(argv)

    form_maps = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    forms = [args.one] if args.one else FORMS
    try:
        results = []
        for form_id in forms:
            if not args.force and args.one is None and \
                    (OUT_DIR / ("%s.json" % form_id)).exists():
                print("SKIP %s (đã có questionnaire — không đụng)" % form_id)
                continue
            q = build_one(form_id, form_maps)
            results.append((form_id, q))
    except GenError as exc:
        print("FAIL %s" % exc, file=sys.stderr)
        return 1

    if not args.check:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for form_id, q in results:
            path = OUT_DIR / ("%s.json" % form_id)
            path.write_text(
                json.dumps(q, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
    for form_id, q in results:
        entry = form_maps[form_id]
        need, got = coverage_of(form_id, entry, q["questions"])
        print("OK %s: %d câu, phủ %d/%d key fillable"
              % (form_id, len(q["questions"]), len(got), len(need)))
    action = "KIỂM" if args.check else "SINH"
    print("%s OK %d questionnaire (%s) -> %s"
          % (action, len(results), PROVENANCE, OUT_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
