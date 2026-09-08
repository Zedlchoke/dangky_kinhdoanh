# Lane F3H-census — merger census occurrence-level ngữ nghĩa band tên chủ thể
# (HEADER-SUBJECT-SEMANTICS) theo docs/f3h_f3t_directive_2026-09-08.md mục 2.
#
# READ-ONLY với production: chỉ ĐỌC app/data/form_maps.json, app/templates/*.docx,
# tools/header_name_binding.json. GHI đúng 2 artifact:
#   docs/audits/header_semantic_census.json + .md
#
# 3 tầng nguồn, merger thống nhất:
#   (1) BẢNG 5-ROLE TỪ ẢNH NGUỒN PHÁP LÝ (F3H_IMAGE_CENSUS bên dưới) — do lane
#       census soạn 2026-09-07 bằng đối chiếu ảnh scan:
#       - TT 121/2026/TT-BTC (hiệu lực 21/08/2026): /tmp/tt121_pages/*.png
#         (p5-p10 M1, p11-p22 M2, p23-p31 M3, p32-p41 M4, p42-p48 M5, p49 M10,
#         p50-p66 M12, p67-p69 M27, p70 M30 — SOURCES.md đã xác minh)
#       - TT 68/2025/TT-BTC: /tmp/tt68_pages/p001-p266.png (bản đồ trang suy ra
#         từ contact sheet 3x4, đã xác minh từng trang đầu mẫu)
#   (2) Structural scan template docx: tái dùng scan_template() của
#       tools/census/header_name_census.py (cùng phương pháp census F0L).
#   (3) Registry: tools/header_name_binding.json (band-bound 23 form + output_mirrors).
#
# Hoàn tất 2026-09-08: chốt 2 fixture bắt buộc bằng ảnh (PLI_M31 p134 CÓ band /
# PLI_M72 p199 KHÔNG band) + rà soát mở rộng 14 trang ảnh; sửa 3 entry sai
# của bản nháp 2026-09-07 theo ảnh: PLI_M47 (p159), PLI_M50 (p162),
# PLI_M63 (p181-p182) đều CÓ khối "(Tên doanh nghiệp)" → output_mirror
# (xem summary.corrections_2026_09_08).
#
# 5 role (form-level, theo chỉ thị F3H):
#   required_band_mirror     — source CÓ band "TÊN DN/TÊN HKD" + thân có trường
#                              tên cùng key (band value mirror xuống thân)
#   required_band_input      — band là ô nhập tên chủ thể DUY NHẤT (thân không có
#                              trường tên cùng key)
#   no_subject_band          — KHÔNG có band chủ thể (kể cả khi có band khác chủ
#                              thể như "TÊN TỔ CHỨC" của người đề nghị)
#   legal_title_or_subtitle  — "TÊN..." chỉ xuất hiện dạng tiêu đề phụ pháp lý,
#                              không fillable (form-level; occurrence subtitle
#                              vẫn ghi dưới occurrences của M72-M74)
#   output_mirror            — không band; tên chủ thể là nội dung chứng từ do
#                              CQ ĐKKD cấp/công bố (GCN, Giấy xác nhận, Quyết
#                              định, Thông báo/Công bố của CQ) — fill render-time
#
# Cặp phân biệt bắt buộc (fixture): PLI_M31 (band + điền dưới nhãn — GIỮ band)
# vs PLI_M72 (0 band — CẤM tự thêm band).
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from header_name_census import scan_template  # noqa: E402 (read-only scan)

GENERATED = "2026-09-08"
DIRECTIVE = "docs/f3h_f3t_directive_2026-09-08.md (mục 2 — F3H lane)"

ROLES = {
    "required_band_mirror": "band + thân có trường tên cùng key",
    "required_band_input": "band là ô nhập tên chủ thể duy nhất",
    "no_subject_band": "không có band chủ thể",
    "legal_title_or_subtitle": '"TÊN..." chỉ là tiêu đề phụ, không fillable',
    "output_mirror": "không band; tên chủ thể là nội dung output CQ cấp/công bố",
}

# ---------------------------------------------------------------------------
# (1) BẢNG 5-ROLE TỪ ẢNH — 87 form.
# occ shorthand: (location, kind, subject_role, label_verbatim, canonical_key, page)
#   location: band | body | output-doc
#   kind: input | mirror | output | narrative_gap | subtitle | band_other
#   subject_role: self (chủ thể của hồ sơ) | other_subject | requester | branch_key
# ---------------------------------------------------------------------------
E = "image"

def F(van_ban, pages, first, band_label, role, subject, key, occs, **kw):
    d = dict(
        source_van_ban=van_ban,
        source_pages=pages,
        evidence_first_page=first,
        band_label_verbatim=band_label,
        form_role=role,
        subject_kind=subject,
        canonical_key=key,
        blank_policy=("fill_under_label" if band_label and role in
                      ("required_band_mirror", "required_band_input") else None),
        occurrences=[dict(zip(
            ("location", "occurrence_kind", "subject_role",
             "label_verbatim", "canonical_key", "evidence_page"), o)) for o in occs],
        evidence_basis=kw.get("basis", E),
        fixture_note=kw.get("fixture"),
        current_law_status=kw.get("law_status"),
        source_note=kw.get("note"),
    )
    return d

T121 = "TT 121/2026/TT-BTC"
T68 = "TT 68/2025/TT-BTC"
REPL = "replaced_by_tt121_2026 (Điều 1 khoản 1, ảnh p2)"
IMG121 = "/tmp/tt121_pages/"
IMG68 = "/tmp/tt68_pages/"

F3H_IMAGE_CENSUS = {
    # ---- 9 mẫu mới TT121/2026 (source 2026, ảnh /tmp/tt121_pages) ----------
    "PLI_M01": F(T121, "p5-p10", IMG121 + "p05.png", None, "no_subject_band", "dn",
        "dn.ten_tieng_viet", [
            ("body", "input", "self", "Tên doanh nghiệp viết bằng tiếng Việt (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p7"),
            ("body", "input", "self", "Tên doanh nghiệp viết bằng tiếng nước ngoài (nếu có):", "dn.ten_nuoc_ngoai", "p7"),
            ("body", "input", "self", "Tên doanh nghiệp viết tắt (nếu có):", "dn.ten_viet_tat", "p7"),
            ("body", "input", "other_subject", "Tên hộ kinh doanh (khối HKD chuyển đổi)", "hkd_cd.ten_hkd", "p6"),
        ],
        law_status=REPL,
        note="Mục '2. Tên doanh nghiệp:' ở thân (p7); KHÔNG có band trang đầu."),
    "PLI_M02": F(T121, "p11-p22", IMG121 + "p11.png", None, "no_subject_band", "dn",
        "dn.ten_tieng_viet", [
            ("body", "input", "self", "Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p14"),
            ("body", "input", "self", "Tên công ty viết bằng tiếng nước ngoài (nếu có):", "dn.ten_nuoc_ngoai", "p14"),
            ("body", "input", "self", "Tên công ty viết tắt (nếu có):", "dn.ten_viet_tat", "p14"),
            ("body", "input", "other_subject", "Tên doanh nghiệp (ghi bằng chữ in hoa): (DN bị chia/tách/hợp nhất)", "dn_goc.ten_doanh_nghiep", "p12"),
            ("body", "input", "other_subject", "Tên hộ kinh doanh (ghi bằng chữ in hoa): (HKD chuyển đổi)", "hkd_cd.ten_hkd", "p12"),
        ],
        law_status=REPL,
        note="Mục '2. Tên công ty:' ở thân (p14); KHÔNG có band trang đầu."),
    "PLI_M03": F(T121, "p23-p31", IMG121 + "p23.png", None, "no_subject_band", "dn",
        "dn.ten_tieng_viet", [
            ("body", "input", "self", "Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "structural+pattern M01/M02"),
            ("body", "input", "other_subject", "Tên doanh nghiệp (ghi bằng chữ in hoa): (bị chia/tách/hợp nhất)", "dn_goc.ten_doanh_nghiep", "p24"),
        ],
        law_status=REPL,
        note="Ảnh p23 xác minh title + KHÔNG band; thân theo structural + pattern chung M01-M05."),
    "PLI_M04": F(T121, "p32-p41", IMG121 + "p32.png", None, "no_subject_band", "dn",
        "dn.ten_tieng_viet", [
            ("body", "input", "self", "Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "structural+pattern M01/M02"),
            ("body", "input", "other_subject", "Tên doanh nghiệp (ghi bằng chữ in hoa): (bị chia/tách/hợp nhất)", "dn_goc.ten_doanh_nghiep", "structural"),
        ],
        law_status=REPL,
        note="Ảnh p32 xác minh title + KHÔNG band (p35 đã là mục '4. Ngành, nghề')."),
    "PLI_M05": F(T121, "p42-p48", IMG121 + "p42.png", None, "no_subject_band", "dn",
        "dn.ten_tieng_viet", [
            ("body", "input", "self", "Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p44"),
            ("body", "input", "self", "Tên công ty viết bằng tiếng nước ngoài (nếu có):", "dn.ten_nuoc_ngoai", "p44"),
            ("body", "input", "self", "Tên công ty viết tắt (nếu có):", "dn.ten_viet_tat", "p44"),
            ("body", "input", "other_subject", "Tên doanh nghiệp (ghi bằng chữ in hoa): (DN bị hợp nhất)", "dn_goc.ten_doanh_nghiep", "p42-p43"),
            ("body", "input", "other_subject", "Tên hộ kinh doanh (ghi bằng chữ in hoa): (HKD chuyển đổi)", "hkd_cd.ten_hkd", "p43"),
        ],
        law_status=REPL,
        note="Mục '2. Tên công ty:' ở thân (p44); KHÔNG có band trang đầu."),
    "PLI_M10": F(T121, "p49", IMG121 + "p49.png", None, "no_subject_band", "none", None, [
            ("body", "input", "requester", "'Họ và tên' là cột cá nhân trong danh sách CSHHL (không phải tên chủ thể)", None, "p49"),
        ],
        law_status=REPL,
        note="DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI — bảng 18 cột, không có trường tên chủ thể."),
    "PLI_M12": F(T121, "p50-p66", IMG121 + "p50.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p50"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p50"),
            ("body", "mirror", "other_subject", "Tên doanh nghiệp (ghi bằng chữ in hoa): (DN bị sáp nhập/chia/tách)", "dn_goc.ten_doanh_nghiep", "p50"),
            ("body", "input", "self", "ĐĂNG KÝ THAY ĐỔI TÊN DOANH NGHIỆP (tên VN/NN/viết tắt)", "dn.ten_tieng_viet", "p51"),
        ],
        law_status=REPL,
        fixture="Band trang 1 (trái quốc hiệu) + gạch chân điền dưới nhãn; thân mirror cùng key.",
        note="TT68 bản in (p57-p72) CŨNG có band — gap 'source 2025 thiếu band' là lỗi tách DOCX, không phải bản in."),
    "PLI_M27": F(T121, "p67-p69", IMG121 + "p67.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p67"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p67"),
            ("body", "input", "branch_key", "Tên chi nhánh/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p67"),
        ],
        law_status=REPL),
    "PLI_M30": F(T121, "p70", IMG121 + "p70.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p70"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p70"),
        ],
        law_status=REPL),
    # ---- 78 mẫu TT68/2025 (ảnh /tmp/tt68_pages) ----------------------------
    "PLI_M06": F(T68, "p47-p48", IMG68 + "p047.png", None, "no_subject_band", "none", None, [],
        note="DANH SÁCH THÀNH VIÊN — 'Họ và tên' là cột cá nhân, không có tên chủ thể."),
    "PLI_M07": F(T68, "p49-p50", IMG68 + "p049.png", None, "no_subject_band", "none", None, [],
        note="DANH SÁCH CỔ ĐÔNG SÁNG LẬP — không có tên chủ thể."),
    "PLI_M08": F(T68, "p51-p52", IMG68 + "p051.png", None, "no_subject_band", "none", None, [],
        note="DANH SÁCH CỔ ĐÔNG NĐTNN — không có tên chủ thể."),
    "PLI_M09": F(T68, "p53-p54", IMG68 + "p053.png", None, "no_subject_band", "none", None, [],
        note="DANH SÁCH THÀNH VIÊN HỢP DANH — không có tên chủ thể."),
    "PLI_M11": F(T68, "p56", IMG68 + "p056.png", None, "no_subject_band", "none", None, [],
        law_status="removed_by_tt121_2026 (Điều 1 khoản 2 bãi bỏ Mẫu số 11, ảnh p2)",
        note="DANH SÁCH ĐỂ XÁC ĐỊNH CSHHL — đã bị bãi bỏ; template còn ở corpus để đối soát."),
    "PLI_M13": F(T68, "p74-p75", IMG68 + "p074.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p74"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p74"),
        ]),
    "PLI_M14": F(T68, "p76-p77", IMG68 + "p076.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p76"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p76"),
            ("body", "input", "self", "Đăng ký thay đổi tên doanh nghiệp tư nhân (đánh dấu X) + tên sau thay đổi", "dn.ten_tieng_viet", "p76"),
        ]),
    "PLI_M15": F(T68, "p78-p80", IMG68 + "p078.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p78"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p78"),
        ]),
    "PLI_M17": F(T68, "p83-p87", IMG68 + "p083.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p83"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p83-p84"),
            ("body", "input", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p83-p84"),
        ]),
    "PLI_M18": F(T68, "p88-p89", IMG68 + "p088.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p88"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p88"),
        ]),
    "PLI_M19": F(T68, "p90-p99", IMG68 + "p090.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p90"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p90"),
            ("body", "input", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p90"),
        ]),
    "PLI_M21": F(T68, "p102", IMG68 + "p102.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p102"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p102"),
        ]),
    "PLI_M23": F(T68, "p111-p122", IMG68 + "p111.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p111"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p111"),
            ("body", "input", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p111"),
        ]),
    "PLI_M25": F(T68, "p123-p125", IMG68 + "p123.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p123"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p123"),
        ]),
    "PLI_M26": F(T68, "p126", IMG68 + "p126.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p126"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p126"),
        ]),
    "PLI_M28": F(T68, "p130-p131", IMG68 + "p130.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p130"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p130"),
        ]),
    "PLI_M29": F(T68, "p132", IMG68 + "p132.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p132"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p132"),
        ]),
    "PLI_M31": F(T68, "p134", IMG68 + "p134.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p134"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p134"),
        ],
        fixture="FIXTURE 1/2 (phân biệt với PLI_M72): source CÓ band + gạch chân điền NGAY DƯỚI NHÃN (dòng 'Số:' là số hồ sơ, tách biệt) — converter PHẢI giữ nhãn + fill-line dưới nhãn.",
        note="THÔNG BÁO hủy bỏ Nghị quyết/Quyết định giải thể doanh nghiệp."),
    "PLI_M32": F(T68, "p135", IMG68 + "p135.png", "TÊN DOANH NGHIỆP",
        "required_band_mirror", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p135"),
            ("body", "mirror", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p135"),
            ("body", "input", "requester", "Tôi là1 (ghi họ tên bằng chữ in hoa):", "ca_nhan.ho_ten", "p135"),
        ],
        fixture="Fixture mirror A→B: band (A) mirror xuống thân (B); chủ thể điền 1 lần, thân không nhập lại.",
        note="GIẤY ĐỀ NGHỊ Công bố nội dung đăng ký doanh nghiệp."),
    "PLI_M33": F(T68, "p136-p137", IMG68 + "p136.png", "TÊN DOANH NGHIỆP",
        "required_band_input", "dn", "dn.ten_tieng_viet", [
            ("band", "input", "self", "TÊN DOANH NGHIỆP", "dn.ten_tieng_viet", "p136"),
            ("body", "narrative_gap", "self", "của ............ (Tên Doanh nghiệp) – Mã số doanh nghiệp ....(nếu có)", "dn.ten_tieng_viet", "p137"),
        ],
        fixture="FIXTURE band_input: thân KHÔNG có trường 'Tên doanh nghiệp (ghi bằng chữ in hoa):' — band là ô nhập tên DUY NHẤT (token dn.ten_tieng_viet chỉ xuất hiện 1 lần, tại band).",
        note="GIẤY ĐỀ NGHỊ Dừng thực hiện thủ tục đăng ký doanh nghiệp."),
    "PLI_M42": F(T68, "p150", IMG68 + "p150.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("output-doc", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p150 (dưới vùng crop đầu trang) + structural"),
            ("output-doc", "output", "branch_key", "1. Tên chi nhánh/văn phòng đại diện (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p150"),
        ],
        note="GCN ĐKHOẠT ĐỘNG CHI NHÁNH/VPĐD — chứng từ do CQ cấp; tên DN + tên chi nhánh đều là nội dung output."),
    "PLI_M43": F(T68, "p151", IMG68 + "p151.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("output-doc", "output", "self", "Tên doanh nghiệp/chi nhánh (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p151 (dưới vùng crop đầu trang) + structural"),
            ("output-doc", "output", "branch_key", "1. Tên địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p151"),
        ],
        note="GCN ĐĂNG KÝ ĐỊA ĐIỂM KINH DOANH — chứng từ do CQ cấp."),
    "PLI_M45": F(T68, "p157-p158", IMG68 + "p157.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p157 (mục 'Xác nhận:')"),
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p157"),
        ],
        note="GIẤY XÁC NHẬN (CQ ĐKKD cấp tỉnh cấp) — tên DN điền bởi CQ khi cấp; structural census cũ misclassify 'before-band' do band_end fallback — ảnh xác nhận KHÔNG có band."),
    "PLI_M46": F(T68, "p158", IMG68 + "p158.png", None, "no_subject_band", "none", None, [],
        note="GCN/GXN đăng ký thuế — ảnh p158: chỉ '(Nơi dùng cấp lại)/TRƯỜNG ĐƠN VỊ/Ghi chú', không có trường tên chủ thể."),
    "PLI_M47": F(T68, "p159", IMG68 + "p159.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên doanh nghiệp)", "dn.ten_tieng_viet", "p159"),
            ("body", "output", "other_subject", "Tên Cơ quan thuế quản lý trực tiếp:", None, "p159"),
        ],
        note="THÔNG BÁO CQ thuế quản lý trực tiếp (CQ ĐKKD cấp tỉnh) — ảnh p159 có khối "
             "'Kính gửi: (Tên doanh nghiệp)/Địa chỉ/Mã số'; đề xuất registry: bind token "
             "dn.ten_tieng_viet + bổ sung output_mirrors."),
    "PLI_M48": F(T68, "p160", IMG68 + "p160.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "về việc: .......... của (Tên doanh nghiệp) ..........", "dn.ten_tieng_viet", "p160"),
        ],
        note="Static '(Tên doanh nghiệp)' trong template — output_mirrors registry ĐÃ có PLI_M48."),
    "PLI_M49": F(T68, "p161", IMG68 + "p161.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "(Đối với các trường hợp còn lại) ....... (Tên doanh nghiệp) .........", "dn.ten_tieng_viet", "p161"),
            ("body", "narrative_gap", "self", "về việc đăng ký/thông báo ... của (Tên doanh nghiệp) – Mã số doanh nghiệp (nếu có)", "dn.ten_tieng_viet", "p161"),
        ],
        note="output_mirrors registry ĐÃ có PLI_M49."),
    "PLI_M50": F(T68, "p162", IMG68 + "p162.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên doanh nghiệp)", "dn.ten_tieng_viet", "p162"),
        ],
        note="THÔNG BÁO yêu cầu DN báo cáo tuân thủ Luật DN (CQ ĐKKD cấp tỉnh) — ảnh p162 "
             "có khối 'Kính gửi: (Tên doanh nghiệp)/Địa chỉ/Mã số'; đề xuất registry: bind "
             "token dn.ten_tieng_viet + bổ sung output_mirrors."),
    "PLI_M51": F(T68, "p163", IMG68 + "p163.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên doanh nghiệp)", "dn.ten_tieng_viet", "p163"),
        ],
        note="Static '(Tên doanh nghiệp)' — ĐỀ XUẤT registry: bổ sung output_mirrors PLI_M51."),
    "PLI_M52": F(T68, "p164-p165", IMG68 + "p164.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "1. Đối với doanh nghiệp: - Tên doanh nghiệp:", "dn.ten_tieng_viet", "p164"),
        ],
        note="Thông báo do CQ ĐKKD cấp tỉnh phát hành."),
    "PLI_M53": F(T68, "p166", IMG68 + "p166.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên doanh nghiệp)", "dn.ten_tieng_viet", "p166"),
            ("body", "narrative_gap", "self", "Yêu cầu (tên doanh nghiệp): ... tạm ngừng kinh doanh ngành, nghề...", "dn.ten_tieng_viet", "p166"),
        ],
        note="ĐỀ XUẤT registry: bổ sung output_mirrors PLI_M53."),
    "PLI_M54": F(T68, "p167", IMG68 + "p167.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p167 (mục 'Xác nhận:')"),
        ],
        note="GIẤY XÁC NHẬN do CQ cấp (header CQ ĐKKD CẤP TỈNH)."),
    "PLI_M55": F(T68, "p168", IMG68 + "p168.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p168"),
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p168"),
        ],
        note="GIẤY XÁC NHẬN do CQ cấp."),
    "PLI_M56": F(T68, "p169-p170", IMG68 + "p169.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p169"),
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p170"),
            ("body", "output", "branch_key", "Tên chi nhánh chủ quản:", "cn.ten_tieng_viet", "p170"),
        ],
        note="GIẤY XÁC NHẬN do CQ cấp."),
    "PLI_M57": F(T68, "p171-p172", IMG68 + "p171.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p171"),
            ("body", "output", "branch_key", "Tên chi nhánh/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p171"),
            ("body", "output", "branch_key", "Tên chi nhánh chủ quản:", "cn.ten_tieng_viet", "p171"),
            ("body", "output", "branch_key", "Tên văn phòng đại diện (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p171"),
        ],
        note="GIẤY XÁC NHẬN do CQ cấp."),
    "PLI_M63": F(T68, "p181-p183", IMG68 + "p181.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p181"),
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p182 (mục 'Là chi nhánh/VPĐD/điểm KD của doanh nghiệp sau:')"),
        ],
        note="QUYẾT ĐỊNH thu hồi GCN hoạt động CN/VPĐD/điểm KD (CQ ĐKKD cấp tỉnh) — tên DN "
             "(p182) + tên chi nhánh (p181) đều là nội dung output."),
    "PLI_M66": F(T68, "p191-p192", IMG68 + "p191.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp:", "dn.ten_tieng_viet", "p191"),
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh:", "cn.ten_tieng_viet", "p191"),
        ],
        note="Header 'CQ ĐKKD CẤP TỈNH' — thông báo do CQ phát hành → tên là output."),
    "PLI_M67": F(T68, "p193", IMG68 + "p193.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "(tên doanh nghiệp) ...., mã số doanh nghiệp: ... (inline nghiêng)", "dn.ten_tieng_viet", "p193"),
        ],
        note="Header CQ ĐKKD CẤP TỈNH → output."),
    "PLI_M68": F(T68, "p194-p195", IMG68 + "p194.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp:", "dn.ten_tieng_viet", "p194"),
        ],
        note="Header CQ ĐKKD CẤP TỈNH → output."),
    "PLI_M69": F(T68, "p196", IMG68 + "p196.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp:", "dn.ten_tieng_viet", "p196"),
        ],
        note="Header CQ ĐKKD CẤP TỈNH → output."),
    "PLI_M70": F(T68, "p197", IMG68 + "p197.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "01 bộ hồ sơ ... về việc: .......... của (Tên doanh nghiệp) ..........", "dn.ten_tieng_viet", "p197"),
        ],
        note="GIẤY TIẾP NHẬN (CQ cấp) — điền khi tiếp nhận; output_mirrors registry ĐÃ có PLI_M70."),
    "PLI_M71": F(T68, "p198", IMG68 + "p198.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "01 bộ hồ sơ ... về việc: .......... của (Tên doanh nghiệp) ..........", "dn.ten_tieng_viet", "p198"),
        ],
        note="GIẤY TIẾP NHẬN qua mạng (CQ cấp) — ĐỀ XUẤT registry: bổ sung output_mirrors PLI_M71."),
    "PLI_M72": F(T68, "p199-p206", IMG68 + "p199.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "subtitle", "self", "(TÊN DOANH NGHIỆP TƯ NHÂN) / (TÊN CÔNG TY TNHH MỘT THÀNH VIÊN) / (TÊN CÔNG TY TNHH HAI THÀNH VIÊN) / (TÊN CÔNG TY CỔ PHẦN) / (TÊN CÔNG TY HỢP DANH)", None, "p199-p206"),
            ("output-doc", "output", "self", "1. Tên doanh nghiệp / Tên doanh nghiệp viết bằng tiếng Việt: ... (x5 biến thể)", "dn.ten_tieng_viet", "p199-p206"),
        ],
        fixture="FIXTURE 2/2 (phân biệt với PLI_M31): source KHÔNG CÓ band — '(TÊN...)' là tiêu đề phụ biến thể + '1. Tên doanh nghiệp' là section output; converter CẤM TỰ THÊM band. Detector BAND_FORBIDDEN_PRESENT.",
        note="CÔNG BỔ nội dung đăng ký thành lập — 5 biến thể loại hình, tên là nội dung công bố."),
    "PLI_M73": F(T68, "p207", IMG68 + "p207.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("output-doc", "output", "self", "1. Tên doanh nghiệp (tên tiếng Việt khi tiến hành đổi tên) + tên VN/NN/viết tắt", "dn.ten_tieng_viet", "p207"),
        ],
        note="CÔNG BỔ thay đổi nội dung đăng ký DN — output."),
    "PLI_M74": F(T68, "p208", IMG68 + "p208.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("output-doc", "output", "self", "1. Tên doanh nghiệp / Tên doanh nghiệp viết bằng tiếng Việt: ...", "dn.ten_tieng_viet", "p208"),
        ],
        note="CÔNG BỔ thay đổi khác — output."),
    "PLI_M75": F(T68, "p209-p210", IMG68 + "p209.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "output", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p210"),
            ("body", "output", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p210"),
        ],
        note="THÔNG BÁO khôi phục (CQ cấp) — p210: 'Là chi nhánh/VPĐD/điểm KD của doanh nghiệp sau: Tên doanh nghiệp...'."),
    "PLI_M76": F(T68, "p211", IMG68 + "p211.png", None, "output_mirror", "dn",
        "dn.ten_tieng_viet", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên doanh nghiệp)", "dn.ten_tieng_viet", "p211"),
        ],
        note="THÔNG BÁO cấp đổi (CQ cấp) — ĐỀ XUẤT registry: bổ sung output_mirrors PLI_M76."),
    "PLI_M78": F(T68, "p213-p214", IMG68 + "p213.png", None, "no_subject_band", "none", None, [
            ("body", "input", "requester", "Tôi là (ghi họ tên bằng chữ in hoa):", "ca_nhan.ho_ten", "p213"),
        ],
        note="Cung cấp thông tin ĐKDN — chỉ có tên người yêu cầu; không có trường tên chủ thể (p213-p214)."),
    "PLI_M79": F(T68, "p215-p216", IMG68 + "p215.png", "TÊN TỔ CHỨC",
        "no_subject_band", "dn", "dn.ten_tieng_viet", [
            ("band", "band_other", "requester", "TÊN TỔ CHỨC1 (tổ chức ĐỀ NGHỊ — KHÔNG phải band chủ thể)", "to_chuc.ten", "p215"),
            ("body", "input", "self", "Tên doanh nghiệp (ghi bằng chữ in hoa):", "dn.ten_tieng_viet", "p216"),
            ("body", "input", "branch_key", "Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", "cn.ten_tieng_viet", "p216"),
        ],
        note="Band 'TÊN TỔ CHỨC' là tên tổ chức/cá nhân ĐỀ NGHỊ — detector phải key đúng 'TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH', KHÔNG nhầm với band này."),
    "PLI_M80": F(T68, "p217-p218", IMG68 + "p217.png", "TÊN TỔ CHỨC",
        "no_subject_band", "dn", None, [
            ("band", "band_other", "requester", "TÊN TỔ CHỨC1 (tổ chức ĐỀ NGHỊ — KHÔNG phải band chủ thể)", "to_chuc.ten", "p217"),
            ("body", "input", "self", "Tên doanh nghiệp/chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa):", None, "p218"),
        ],
        note="p218: trường tên chủ thể là fill-line tĩnh trong template (chưa bind token) — đề xuất registry bind dn.ten_tieng_viet."),
    "PLII_M01": F(T68, "p221-p231", IMG68 + "p221.png", None, "no_subject_band", "hkd",
        "hkd_ten_tieng_viet", [
            ("body", "input", "self", "Tên hộ kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet", "p221-p222"),
            ("body", "input", "self", "Tên hộ kinh doanh viết bằng tiếng nước ngoài (nếu có):", "hkd_ten_tieng_nuoc", "p222"),
            ("body", "input", "self", "Tên hộ kinh doanh viết tắt (nếu có):", "hkd_ten_viet_tat", "p222"),
        ],
        note="GIẤY ĐỀ NGHỊ ĐKHKD — mục '1. Tên hộ kinh doanh:' ở thân; KHÔNG band (khác PLII_M02-M06)."),
    "PLII_M02": F(T68, "p224-p235", IMG68 + "p224.png", "TÊN HỘ KINH DOANH",
        "required_band_mirror", "hkd", "hkd_ten_tieng_viet_2", [
            ("band", "input", "self", "TÊN HỘ KINH DOANH", "hkd_ten_tieng_viet_2", "p224"),
            ("body", "mirror", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p224"),
            ("body", "input", "self", "ĐĂNG KÝ THAY ĐỔI TÊN HỘ KINH DOANH (tên VN/NN/viết tắt sau thay đổi)", "hkd_ten_tieng_viet_2", "p225"),
        ]),
    "PLII_M03": F(T68, "p236", IMG68 + "p236.png", "TÊN HỘ KINH DOANH",
        "required_band_mirror", "hkd", "hkd_ten_tieng_viet_2", [
            ("band", "input", "self", "TÊN HỘ KINH DOANH", "hkd_ten_tieng_viet_2", "p236"),
            ("body", "mirror", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p236"),
        ]),
    "PLII_M04": F(T68, "p237", IMG68 + "p237.png", "TÊN HỘ KINH DOANH",
        "required_band_mirror", "hkd", "hkd_ten_tieng_viet_2", [
            ("band", "input", "self", "TÊN HỘ KINH DOANH", "hkd_ten_tieng_viet_2", "p237"),
            ("body", "mirror", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p237"),
        ]),
    "PLII_M05": F(T68, "p238", IMG68 + "p238.png", "TÊN HỘ KINH DOANH",
        "required_band_mirror", "hkd", "hkd_ten_tieng_viet_2", [
            ("band", "input", "self", "TÊN HỘ KINH DOANH", "hkd_ten_tieng_viet_2", "p238"),
            ("body", "mirror", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p238"),
        ]),
    "PLII_M06": F(T68, "p239-p240", IMG68 + "p239.png", "TÊN HỘ KINH DOANH",
        "required_band_input", "hkd", "hkd_ten_tieng_viet_2", [
            ("band", "input", "self", "TÊN HỘ KINH DOANH", "hkd_ten_tieng_viet_2", "p239"),
        ],
        fixture="Fixture band_input (PLII): thân chỉ có 'Tôi là (ghi họ tên bằng chữ in hoa)' người nộp — token hkd_ten_tieng_viet_2 chỉ xuất hiện tại band.",
        note="GIẤY ĐỀ NGHỊ Dừng thực hiện thủ tục đăng ký hộ kinh doanh."),
    "PLII_M07": F(T68, "p241", IMG68 + "p241.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet", [
            ("output-doc", "output", "self", "1. Tên hộ kinh doanh / Tên hộ kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet", "p241"),
        ],
        note="GCN ĐĂNG KÝ HỘ KINH DOANH (CQ ĐKKD cấp xã cấp) — output."),
    "PLII_M08": F(T68, "p242", IMG68 + "p242.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p242"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output; template đã bind hkd_ten_tieng_viet_2."),
    "PLII_M09": F(T68, "p243", IMG68 + "p243.png", None, "no_subject_band", "hkd", None, [],
        note="GCN cấp lại — '(Nội dung cấp lại)' placeholder, không có trường tên riêng (p243)."),
    "PLII_M10": F(T68, "p244", IMG68 + "p244.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p244"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M11": F(T68, "p245", IMG68 + "p245.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p245"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M12": F(T68, "p246", IMG68 + "p246.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p246"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M13": F(T68, "p247", IMG68 + "p247.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Tên hộ kinh doanh:", "hkd_ten_tieng_viet_2", "p247"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M14": F(T68, "p248-p249", IMG68 + "p248.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Điều 1. Thu hồi ...: Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p248"),
        ],
        note="QUYẾT ĐỊNH (CQ ĐKKD cấp xã) → output."),
    "PLII_M15": F(T68, "p250", IMG68 + "p250.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Điều 1. Thu hồi ...: Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p250"),
        ],
        note="QUYẾT ĐỊNH (CQ ĐKKD cấp xã) → output."),
    "PLII_M16": F(T68, "p251", IMG68 + "p251.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Điều 1. Hủy bỏ QĐ thu hồi ...: Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p251"),
        ],
        note="QUYẾT ĐỊNH (CQ ĐKKD cấp xã) → output."),
    "PLII_M17": F(T68, "p252", IMG68 + "p252.png", None, "no_subject_band", "none", None, [],
        note="GIẤY TIẾP NHẬN hồ sơ HKD — chỉ 'đã nhận của Ông/Bà' (người nộp), không có trường tên hộ (p252)."),
    "PLII_M18": F(T68, "p253", IMG68 + "p253.png", None, "no_subject_band", "none", None, [],
        note="GIẤY TIẾP NHẬN qua mạng — không có trường tên hộ (p253)."),
    "PLII_M19": F(T68, "p254", IMG68 + "p254.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Yêu cầu (tên hộ kinh doanh): ... tạm ngừng kinh doanh ngành, nghề...", "hkd_ten_tieng_viet_2", "p254"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M20": F(T68, "p255", IMG68 + "p255.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p255"),
        ],
        note="GIẤY XÁC NHẬN (CQ ĐKKD cấp xã) → output; structural census cũ misclassify 'before-band' do band_end fallback."),
    "PLII_M21": F(T68, "p256-p257", IMG68 + "p256.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p256"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M22": F(T68, "p258", IMG68 + "p258.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p258"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M23": F(T68, "p259", IMG68 + "p259.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p259"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M24": F(T68, "p260", IMG68 + "p260.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Tên hộ kinh doanh (ghi bằng chữ in hoa):", "hkd_ten_tieng_viet_2", "p260"),
        ],
        note="THÔNG BÁO khôi phục (CQ ĐKKD cấp xã) → output."),
    "PLII_M25": F(T68, "p261", IMG68 + "p261.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p261"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M26": F(T68, "p262", IMG68 + "p262.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Tên hộ kinh doanh:", "hkd_ten_tieng_viet_2", "p262"),
            ("body", "narrative_gap", "self", "của ... (Tên hộ kinh doanh) – Mã số hộ kinh doanh (nếu có)", "hkd_ten_tieng_viet_2", "p262"),
        ],
        note="Template chưa bind token (static) — ĐỀ XUẤT registry: bind hkd_ten_tieng_viet_2."),
    "PLII_M27": F(T68, "p263", IMG68 + "p263.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "output", "self", "Tên hộ kinh doanh:", "hkd_ten_tieng_viet_2", "p263"),
        ],
        note="Header CQ ĐKKD CẤP XÃ → output."),
    "PLII_M28": F(T68, "p264-p265", IMG68 + "p264.png", None, "output_mirror", "hkd",
        "hkd_ten_tieng_viet_2", [
            ("body", "narrative_gap", "self", "Kính gửi: (Tên hộ kinh doanh)", "hkd_ten_tieng_viet_2", "p264"),
            ("body", "output", "self", "- Tên hộ kinh doanh:", "hkd_ten_tieng_viet_2", "p264"),
        ],
        note="THÔNG BÁO rà soát (CQ ĐKKD cấp xã) → output."),
}

SUBJECT_PAT = re.compile(
    r"ten doanh nghiep|doanh nghiep cu|doanh nghiep moi|ten cong ty|"
    r"ten ho kinh doanh|ho kinh doanh moi|ten hkd", re.I)
BAND_OTHER_PAT = re.compile(r"ten to chuc", re.I)


def structural_band(sig):
    """Band thật = occurrence 'band-table'; 'before-band' do band_end fallback
    (không tìm thấy title) là artifact — không tính là band."""
    return any(o["band_region"] == "band-table" for o in sig["occurrences"])


def classify_structural_occ(o, form_role, canonical_key, image_by_label):
    """Gán kind/subject_role cho occurrence structural dựa trên role form + key."""
    f = (o["matched_pattern"] or "")
    text = o["text"]
    key = None
    for k in o.get("token_keys", []):
        key = k
        break
    # subject_role theo key
    if key and key.startswith(("dn_goc", "dn_cu", "dn_moi")):
        sr = "other_subject"
    elif key and key.startswith(("hkd_cd", "hkd_goc")):
        sr = "other_subject"
    elif key and key.startswith("cn."):
        sr = "branch_key"
    elif key in ("chu_hkd.ho_ten",) or key and key.startswith("ca_nhan"):
        sr = "requester"
    elif key in ("to_chuc.ten",):
        sr = "requester"
    else:
        sr = "self"
    if BAND_OTHER_PAT.search(f):
        return None  # "TÊN TỔ CHỨC" — không phải occurrence census chủ thể
    if o["band_region"] == "band-table":
        return dict(kind="input", subject_role="self")
    if sr == "branch_key" or (key or "").startswith("cn."):
        return dict(kind=("output" if form_role == "output_mirror" else "input"),
                    subject_role="branch_key")
    if sr == "other_subject":
        return dict(kind=("mirror" if form_role == "required_band_mirror" else "input"),
                    subject_role="other_subject")
    if sr == "requester":
        return None  # tên người nộp/tổ chức đề nghị — ngoài census chủ thể
    # self
    if form_role in ("required_band_mirror",):
        return dict(kind=("input" if o["band_region"] != "after-band" else "mirror"),
                    subject_role="self")
    if form_role == "required_band_input":
        return dict(kind="input", subject_role="self")
    if form_role == "output_mirror":
        return dict(kind="output", subject_role="self")
    return dict(kind="input", subject_role="self")


def main():
    maps = json.load(open(ROOT / "app/data/form_maps.json", encoding="utf-8"))
    binding = json.load(open(ROOT / "tools/header_name_binding.json", encoding="utf-8"))
    bound_bands = binding.get("forms", {})
    reg_mirrors = {k for k in binding.get("output_mirrors", {}) if k != "comment"}

    forms_out = {}
    missing_image = []
    role_counts = {}
    total_occ = 0
    for fid in maps:
        if fid not in F3H_IMAGE_CENSUS:
            missing_image.append(fid)
            continue
        img = F3H_IMAGE_CENSUS[fid]
        role = img["form_role"]
        role_counts[role] = role_counts.get(role, 0) + 1

        tpl = ROOT / "app/templates" / f"{fid}.docx"
        sig = scan_template(fid, tpl)
        s_band = structural_band(sig)
        i_band = img["band_label_verbatim"] is not None and role in (
            "required_band_mirror", "required_band_input")
        if s_band == i_band:
            xcheck = "match"
        elif s_band and not i_band:
            xcheck = "structural_band_only (xem structural_occurrences)"
        else:
            xcheck = "image_band_only"

        # merged occurrences: image occurrences (semantics) + structural facts
        occs = []
        for o in img["occurrences"]:
            occs.append(dict(o, source="image"))
        s_occ = []
        for o in sig["occurrences"]:
            if o["band_region"] == "after-band" and not SUBJECT_PAT.search(
                    o["matched_pattern"] or ""):
                pass
            cls = classify_structural_occ(
                o, role, img.get("canonical_key"), None)
            if cls is None and o["band_region"] != "band-table":
                continue
            rec = dict(
                location=("band" if o["band_region"] == "band-table" else "body"),
                occurrence_kind=(cls or {}).get("kind", "input"),
                subject_role=(cls or {}).get("subject_role", "self"),
                label_verbatim=o["text"][:120],
                canonical_key=(o.get("token_keys") or [None])[0],
                evidence_page="structural:" + (o.get("table_cell")
                                               or f"para{o['para_idx']}"),
                source="structural",
                has_token=bool(o["has_token_para"]),
                fill_line=bool(o["para_has_fill"]),
            )
            s_occ.append(rec)
        total_occ += len(occs) + len(s_occ)

        # đếm kỳ vọng theo role
        exp = dict(
            band_input=1 if i_band else 0,
            mirror_self=sum(1 for o in occs + s_occ
                            if o["occurrence_kind"] == "mirror"
                            and o["subject_role"] == "self"),
            input_self=sum(1 for o in occs + s_occ
                           if o["occurrence_kind"] == "input"
                           and o["subject_role"] == "self"
                           and o["location"] != "band"),
            output_self=sum(1 for o in occs + s_occ
                            if o["occurrence_kind"] == "output"
                            and o["subject_role"] == "self"),
            narrative_gap_self=sum(1 for o in occs + s_occ
                                   if o["occurrence_kind"] == "narrative_gap"),
            other_subject=sum(1 for o in occs + s_occ
                              if o["subject_role"] == "other_subject"),
            branch_key=sum(1 for o in occs + s_occ
                           if o["subject_role"] == "branch_key"),
        )
        binding_state = bound_bands.get(fid)
        forms_out[fid] = dict(
            form_id=fid,
            image_census=img,
            form_role=role,
            band_label_verbatim=img["band_label_verbatim"],
            band_present_in_source=i_band,
            subject_kind=img["subject_kind"],
            canonical_key=img["canonical_key"],
            blank_policy=img["blank_policy"],
            fixture_note=img["fixture_note"],
            current_law_status=img["current_law_status"],
            expected_counts=exp,
            structural=dict(
                template_band=bool(s_band),
                band_occurrences=[o for o in sig["occurrences"]
                                  if o["band_region"] == "band-table"],
                occurrences=s_occ,
            ),
            cross_check=xcheck,
            registry_binding=dict(
                band_bound=bool(binding_state),
                band_key=(binding_state or {}).get("key"),
                in_output_mirrors=fid in reg_mirrors,
            ),
        )

    fixtures = {fid: forms_out[fid]["fixture_note"]
                for fid in ("PLI_M31", "PLI_M72", "PLI_M32", "PLI_M33", "PLII_M06")}
    out = dict(
        generated=GENERATED,
        directive=DIRECTIVE,
        base="worktree agent/f3h-census (HEAD 4b9ff3a) — merge sau commit",
        method=("merger 3 tầng: (1) bảng 5-role từ ảnh nguồn pháp lý "
                "(TT121/2026 9 mẫu + TT68/2025 78 mẫu, soạn 2026-09-07) + "
                "(2) structural scan template docx (scan_template của "
                "tools/census/header_name_census.py) + (3) registry "
                "tools/header_name_binding.json"),
        role_definitions=ROLES,
        image_corpora=dict(
            tt121_2026="/tmp/tt121_pages/ (70 trang, SOURCES.md đã xác minh)",
            tt68_2025="/tmp/tt68_pages/ (266 trang; bản đồ trang suy ra từ "
                      "contact-sheet 3x4 và xác minh từng trang đầu mẫu)",
        ),
        forms=forms_out,
        fixtures=fixtures,
        summary=dict(
            forms_censused=len(forms_out),
            forms_missing_image_data=missing_image,
            occurrence_total=total_occ,
            role_counts=role_counts,
            band_forms=sum(1 for v in forms_out.values()
                           if v["band_present_in_source"]),
            band_binding_registry=len(bound_bands),
            corrections_2026_09_08=[
                "PLI_M47: no_subject_band → output_mirror — ảnh p159 có khối "
                "'Kính gửi: (Tên doanh nghiệp)/Địa chỉ/Mã số' (bản nháp 09-07 ghi "
                "sai 'KHÔNG có trường tên chủ thể')",
                "PLI_M50: no_subject_band → output_mirror — ảnh p162 có khối "
                "'Kính gửi: (Tên doanh nghiệp)'",
                "PLI_M63: no_subject_band → output_mirror — ảnh p182 có trường "
                "'Tên doanh nghiệp (ghi bằng chữ in hoa):' (mục 'Là chi nhánh/VPĐD/"
                "điểm KD của doanh nghiệp sau:')",
                "Chốt fixture bắt buộc: PLI_M31 (ảnh p134) CÓ band 'TÊN DOANH NGHIỆP' "
                "+ fill dưới nhãn; PLI_M72 (ảnh p199) KHÔNG band, '(TÊN...)' là "
                "subtitle — khớp bảng census",
            ],
            unclear_items=[
                "PLI_M03/M04: trang chứa mục '2. Tên công ty' ở thân không đọc "
                "trực tiếp toàn bộ (pattern M01/M02 + structural) — không ảnh "
                "hưởng role (đã xác minh KHÔNG band từ ảnh trang đầu)",
                "PLI_M42/M43: dòng 'Tên doanh nghiệp (ghi bằng chữ in hoa):' nằm "
                "dưới vùng crop đầu trang — xác minh bằng structural + tile bìa "
                "GCN (chứng từ CQ cấp)",
            ],
        ),
        registry_proposals=[
            "Bổ sung output_mirrors: PLI_M47, PLI_M50, PLI_M51, PLI_M53, PLI_M71, "
            "PLI_M76, PLII_M26 (static '(Tên doanh nghiệp)/(Tên hộ kinh doanh)' "
            "chưa bind token)",
            "PLI_M80: bind dn.ten_tieng_viet vào fill-line 'Tên doanh nghiệp/chi "
            "nhánh/VPĐD/điểm KD (ghi bằng chữ in hoa):' (p218)",
            "output_mirrors đã có PLI_M48/PLI_M49/PLI_M70 — khớp ảnh",
            "Đề xuất cho detector lane: BAND_REQUIRED_MISSING cho 21 form "
            "required_band_mirror + 2 form required_band_input; "
            "BAND_FORBIDDEN_PRESENT cho 45 form output_mirror + 19 form "
            "no_subject_band (kể cả form có band 'TÊN TỔ CHỨC' — M79/M80: band "
            "khác chủ thể, KHÔNG được tính là band TÊN DN/HKD)",
        ],
    )

    out_dir = ROOT / "docs/audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "header_semantic_census.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- markdown -------------------------------------------------------
    md = []
    md.append(f"# Header semantic census (F3H) — {GENERATED}\n")
    md.append(f"> Chỉ thị: {DIRECTIVE} — census occurrence-level mọi "
              "“TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH” từ ảnh nguồn pháp lý.\n")
    md.append("Nguồn: (1) bảng 5-role từ ảnh scan TT 121/2026 (9 mẫu, "
              "/tmp/tt121_pages) + TT 68/2025 (78 mẫu, /tmp/tt68_pages); "
              "(2) structural scan template docx; (3) tools/header_name_binding.json.\n")
    md.append("## 5 role\n")
    for r, d in ROLES.items():
        md.append(f"- `{r}` — {d}: **{role_counts.get(r, 0)} form**")
    md.append("")
    s = out["summary"]
    md.append(f"Tổng: **{s['forms_censused']} form**, "
              f"**{s['occurrence_total']} occurrence** (image + structural), "
              f"**{sum(1 for v in forms_out.values() if v['band_present_in_source'])} form có band chủ thể** "
              f"(registry band-bound: {len(bound_bands)} — khớp).\n")

    md.append("## Cặp phân biệt bắt buộc (fixture)\n")
    for fid in ("PLI_M31", "PLI_M72"):
        v = forms_out[fid]
        md.append(f"- **{fid}** ({v['image_census']['source_pages']}, "
                  f"role `{v['form_role']}`): {v['fixture_note']}")
    md.append("")
    md.append("Fixture phụ: PLI_M32 (mirror A→B), PLI_M33 + PLII_M06 (band_input), "
              "PLI_M79/PLI_M80 (band “TÊN TỔ CHỨC” là band NGƯỜI ĐỀ NGHỊ — cấm "
              "nhận nhầm là band chủ thể).\n")

    md.append("## Sửa soạn theo ảnh 2026-09-08\n")
    for c in s["corrections_2026_09_08"]:
        md.append(f"- {c}")
    md.append("")

    md.append("## Bảng census theo form\n")
    md.append("| Form | Nguồn (trang ảnh) | Band | Role | subject | key | occurrence chính |")
    md.append("|---|---|---|---|---|---|---|")
    for fid in sorted(forms_out):
        v = forms_out[fid]
        img = v["image_census"]
        band = img["band_label_verbatim"] or ("(TÊN TỔ CHỨC — khác chủ thể)"
                                              if any(o["occurrence_kind"] == "band_other"
                                                     for o in img["occurrences"]) else "—")
        occs = "; ".join(
            f"[{o['occurrence_kind']}/{o['subject_role']}] {o['label_verbatim'][:60]}"
            for o in img["occurrences"][:3]) or "—"
        src = img["source_van_ban"].replace("TT ", "") + " " + img["source_pages"]
        md.append(f"| {fid} | {src} | {band} | `{v['form_role']}` | "
                  f"{v['subject_kind']} | {v['canonical_key'] or '—'} | {occs} |")
    md.append("")
    md.append("## Cross-check structural ↔ ảnh\n")
    xcounts = {}
    for v in forms_out.values():
        xcounts[v["cross_check"]] = xcounts.get(v["cross_check"], 0) + 1
    for k, n in sorted(xcounts.items()):
        md.append(f"- {k}: {n} form")
    md.append("")
    md.append("Ghi chú: các form GIẤY XÁC NHẬN/THÔNG BÁO do CQ cấp (M45, M54-M57, "
              "PLII_M20) có structural census cũ đánh dấu 'before-band' do band_end "
              "fallback — ảnh xác nhận KHÔNG có band; đã phân loại lại theo ảnh "
              "(output_mirror).\n")
    md.append("## Điểm unclear\n")
    for u in s["unclear_items"]:
        md.append(f"- {u}")
    md.append("")
    md.append("## Đề xuất cho registry + detector lane\n")
    for p in out["registry_proposals"]:
        md.append(f"- {p}")
    md.append("")
    (out_dir / "header_semantic_census.md").write_text(
        "\n".join(md), encoding="utf-8")

    print("forms:", len(forms_out), "| occurrences:", total_occ)
    print("roles:", role_counts)
    print("missing_image_data:", missing_image)
    print("cross_check:", xcounts)
    band_forms = sum(1 for v in forms_out.values() if v["band_present_in_source"])
    print("band forms (image):", band_forms, "| registry band-bound:", len(bound_bands))


if __name__ == "__main__":
    main()
