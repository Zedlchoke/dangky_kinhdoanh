# -*- coding: utf-8 -*-
"""Lead tool: hop nhat 3 census fragment thanh app/data/table_specs/manifest.json
va kiem tra gate T0 (87/87, status hop le, detector signature STT).

Read-only tren production blocks/templates; chi ghi manifest.json (--write).
"""
import argparse
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCKS_DIR = os.path.join(ROOT, "app", "data", "blocks")
TEMPLATES_DIR = os.path.join(ROOT, "app", "templates")
FRAG_DIR = os.path.join(ROOT, "app", "data", "table_specs", "fragments")
MANIFEST_PATH = os.path.join(ROOT, "app", "data", "table_specs", "manifest.json")

FRAGMENTS = [
    ("t0_a", "PLI_M01-M12", "149eb63"),
    ("t0_b", "PLI_M13-M80", "ff09541"),
    ("t0_c", "PLII_M01-M28", "cd144a8"),
]

REVIEWS = {
    "t0_b": {"commit": "f91129b", "verdict": "MERGE-READY", "agree": 47, "disagree": 0},
    "t0_c": {"commit": "9fcee27", "verdict": "NEEDS-FIXES(1)", "agree": 27, "disagree": 1},
}

VALID_STATUS = ("NO_TABLE", "TABLE_COMPLETE", "BLOCKED_LEGAL_REVIEW")

# Form da chu dong tien hoa SAU census qua wave P1 (regenerate lam thay doi
# p/loop counts). Khong phai drift ro rang; moi dong la mot quyet dinh integrate.
EVOLVED_FORMS = {
    # F1-IN regen 2026-09-06 (O1: 10 section USER-INPUT): 3 grid M27 (NDD +
    # 2 don_vi), fixed-matrix M78, tai_lieu M79/M80; M07 chi thay doi do LANE
    # KHAC (F0L N-v4 rebuild PLI_M07 truoc do) — gia tri ghi de nhan dien.
    "PLI_M07": "F1-IN baseline: F0L N-v4 rebuild M07 (muc I/II + chu ky + 13 chu thich)",
    "PLI_M78":
        "F1-IN O1+D6.4: san_pham_cung_cap_thong_tin -> w:tbl fixed-matrix 4 dong",
    "PLI_M79":
        "F1-IN O1+D6.5: tai_lieu_kem_theo_de_nghi -> loop ds_tai_lieu_kem_theo_m79",
    "PLI_M80":
        "F1-IN O1+D6.5: tai_lieu_kem_theo_thu_hoi -> loop ds_tai_lieu_kem_theo_m80",
    "PLI_M27":
        "F1-IN O1: +3 loop (ds_ndd_pl_thong_bao_tam_ngung, "
        "don_vi_truc_thuoc_tam_ngung_tiep_tuc, don_vi_tiep_tuc_truoc_han)",
    "PLI_M72": "P1: 1 loop -> 5 occurrence ds_nganh_*",
    "PLII_M02": "P1: them 3 loop Muc A (bo_sung/xoa_bo/sua_doi)",
    # W1 regen 2026-08-27 (commit d48eb7d): chu ky tro thanh w:tbl that
    "PLI_M70": "W1: 2 paragraph chu ky -> w:tbl output-table 2x1 (spec publication)",
    "PLI_M71": "W1: heading chu ky -> w:tbl output-table 1x1, giu national-separator",
    # R3B1 regen 2026-08-27 (merge 2202937/29b1efa): glue header nguoi/uy quyen
    # tro thanh loop nested-grid that, theo specs D2.1/D2.4/D2.7 da chot
    "PLI_M02":
        "R3B1: +loop nested-grid ds_nddpl_uy_quyen_chu_so_huu; P2C: +2 "
        "fixed-matrix nguon_von/tai_san (section_specs)",
    "PLI_M12":
        "R3B1: them loop nested-grid ds_ndd_uy_quyen_sau_thay_doi (3->4 loop)",
    "PLI_M15":
        "R3B1: glue header B49 -> loop nested-grid "
        "ds_nddpl_uy_quyen_chu_so_huu_moi (0->1 loop)",
    # Wave P2 regen 2026-08-27 (abe6084/1691728 + Lead regen batch)
    "PLII_M07":
        "P2A D2.8=A: +loop ds_thanh_vien_hkd_gcn (1->2 loop, 7 p -> w:tbl)",
    "PLI_M01":
        "P2C D1.1=A/D1.2=B: tai_san_gop_von_von_dau_tu -> w:tbl fixed-matrix",
    "PLI_M13":
        "P2A D2.6/D2.7=A: glue header -> loop grid ndd_pl_sau_thay_doi (0->1)",


    # hdr2col merge 084444d (2026-08-28): 4 paragraph header dọc (ô tên /
    # quốc hiệu / Số: / ngày ký) -> 1 w:tbl header band 2x2 (Việc 2 — lệnh
    # owner). summary_counts.p giảm 3-4, table 0 -> 1 ở TOÀN BỘ 22 mẫu census.
    # m09-rebuild merge cfdefcd + Lead chèn mục 7 (11861b6): decontaminate
    # D3.1=A xóa vùng nhiễm p103-p222 (~104 paragraph), bảng 14 cột thay
    # grid phẳng; summary_counts.p 178 -> 74.
    "PLI_M09": "m09-rebuild: decontaminate 14-cot + chen muc 7 (D3.1/D3.2=A)",
    # [integ(F0L) 2026-09-06] N-v4 (laneA2 0f5e9f4): M07 stub 2 dòng -> nội
    # dung đầy đủ theo bản in TT 68 p49-50 (mục I/II.1/II.2, chữ ký, 13 chú
    # thích); evidence: recount blocks hiện tại p=25 vs fragment stub p=2.
    "PLI_M07": "N-v4 laneA2: stub 2 dong -> day du TT 68 p49-50 (p 2 -> 25)",
    "PLII_M02": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLII_M03": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLII_M04": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLII_M05": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLII_M06": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M13": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M14": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M15": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M17": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M18": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M19": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M21": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M23": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M25": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M26": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M27": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M28": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M29": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M30": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M31": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M32": "hdr2col: 4 p header -> w:tbl header band (band:header)",
    "PLI_M33": "hdr2col: 4 p header -> w:tbl header band (band:header)",

    # cap-von regen (merge fc07c69 + Lead regen 5 mẫu): bảng nguồn vốn/
    # cấu cổ phần/chào bán/thuế II.2 thay paragraph glue — p giảm, table +1..+3.
    "PLI_M03": "cap-von: nguon_von -> w:tbl fixed-matrix",
    "PLI_M04": "cap-von: nguon_von + co_cau + chao_ban -> 3 w:tbl",
    "PLI_M05": "cap-von: nguon_von -> w:tbl fixed-matrix",
    "PLI_M12": "cap-von: nguon_von_sau -> w:tbl fixed-matrix",
    "PLII_M02": "cap-von: a7_thue -> w:tbl fixed-matrix",

    # Phase 5R1 (merge c7ff269 + Lead regen): dọn defect bố cục theo audit
    # 2026-09-03 — generator drop_flat_field_code_paras bỏ 1 p field-code
    # stale của bản nguồn M28; drop_foreign_annex_tail cắt 3 p banner
    # "PHỤ LỤC II" của phụ lục kế khỏi đuôi M80 (WLAY-006/WLAY-007b).
    "PLII_M28": "5R1: drop field code PAGE \\* MERGEFORMAT flatten cua nguon",
    "PLI_M80": "5R1: cat banner PHU LUC II cua phu luc ke khoi duoi mau",
}

TABLE_KINDS = ("editable-grid", "fixed-matrix", "nested-grid", "output-table")
NON_TABLE_KINDS = ("prose-block", "scalar-fields", "source-contamination")
SECTION_KINDS = TABLE_KINDS + NON_TABLE_KINDS
SECTION_STATUSES = (
    "missing_grid", "partial_columns", "partial", "already_complete",
    "output_only", "no_table", "contaminated",
    # [F0L O1 2026-09-06] vùng nhiễm đã bị XÓA khỏi nguồn có evidence
    # (decontaminate + gate test riêng) — không ngụy trang thành output.
    "removed_by_source_cleanup",
)
NO_TABLE_SECTION_KINDS = ("prose-block", "scalar-fields")

# Heading reconcile (Phase 3 phát hiện): các fix heading của Phase 2 (commits
# 0aedd80/b9d9d48/a54b0ca) từng sửa TRỰC TIẾP manifest.json — vi phạm bất biến
# "không sửa tay generated artifact" và làm manifest không tái lập được. Fix
# được đưa về generator: áp lên source_evidence của fragment lúc build.
HEADING_OVERRIDES = {
    ("PLI_M23", "thue_chi_tieu_6_1_6"): {
        "heading": "7. Thông tin đăng ký thuế:",
        "heading_note": "Numbering nguồn gốc là mục 6, sau P1 source swap đã "
                        "đúng thành mục 7. section_id giữ '6_1_6' để JOIN "
                        "spec/tests.",
    },
    ("PLI_M72", "co_dong_sang_lap_cp"): {
        "heading": "7. Cổ đông sáng lập:",
    },
    ("PLI_M72", "co_dong_nuoc_ngoai_cp"): {
        "heading": "8. Cổ đông là nhà đầu tư nước ngoài:",
    },
}

# [F1-IN 2026-09-06] Ghi đè EVIDENCE census stale cho section lane F1-IN
# (O1 adjudicate 22 section — docs/owner_decision_packet_v7.md). Chỉ sửa
# metadata mô tả (notes / required_columns) khi NGUỒN HIỆN HÀNH đã đổi so
# với snapshot census T0; KHÔNG đụng status (status đi qua
# LEAD_STATUS_OVERRIDES riêng). Shape additive như HEADING_OVERRIDES.
SECTION_EVIDENCE_OVERRIDES = {
    # Mẫu 2 2026 in '- Mô hình tổ chức công ty:' với 2 ô □; template/blocks
    # hiện hành đã map thành cặp chk_auto_* (ô vuông viền Q-V1, radio
    # chọn-1 qua EXCLUSIVE_CHK_GROUPS). required_columns census
    # (hd_tv_giam_doc|chu_tich_cong_ty_giam_doc) là tên hóa planned, không
    # khớp key thật.
    ("PLI_M02", "mo_hinh_to_chuc_cong_ty"): {
        "required_columns": [
            "chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g",
            "chk_auto_chu_tich_cong_ty_giam_doc_hoac_tong_giam",
        ],
        "notes": "O1 IMPLEMENTED AS USER INPUT: chọn-1 radio semantics qua "
                 "cặp chk_auto_* (blocks B130-B131; Q-V1 ô vuông viền + X; "
                 "chọn 2 -> CHK_EXCLUSIVE_CONFLICT blocking tại "
                 "EXCLUSIVE_CHK_GROUPS nhóm mo_hinh_to_chuc). Census T0 stale "
                 "(ghi 'ô □ literal, không token' — đã regen theo TT121).",
    },
    # Mẫu 27 2026 (TT 121/2026) mục NĐD chỉ còn 3 trường: Họ, chữ đệm và
    # tên / Số điện thoại / Địa chỉ thư điện tử (chan trang 2: kê khai 01
    # hoặc nhiều NĐDPL). required_columns 7 cột của census T0 (ngày sinh/
    # giới tính/số định danh/địa chỉ liên lạc) đã bị văn bản hiện hành bỏ.
    ("PLI_M27", "danh_sach_ndd_pl_thong_bao"): {
        "required_columns": ["stt", "ho_ten", "dien_thoai", "email"],
        "notes": "O1 IMPLEMENTED AS USER INPUT: grid nhiều dòng NĐDPL theo "
                 "Mẫu 27 2026 (3 trường); loop ds_ndd_pl_thong_bao_tam_ngung; "
                 "minRows 1 (footnote 2). required_columns 7 cột 2025 stale.",
    },
    # Census T0 gộp cả header bảng vào heading (dạng '...: STT | Tên sản
    # phẩm | ...') khiến anchor không khớp blocks/template thật. Heading
    # thật của nguồn: '3. Thông tin yêu cầu:' (p19).
    ("PLI_M78", "san_pham_cung_cap_thong_tin"): {
        "heading": "3. Thông tin yêu cầu:",
        "heading_note": "Census T0 ghép mô tả cột vào heading; tách lại để "
                        "anchor khớp blocks/template (F1-IN 2026-09-06).",
    },
}

RECLASSIFICATIONS = {
    ("PLII_M17", "ho_so_bao_gom"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Blocks b016-b019 la 3 dong cham tay '1....2....3....' khong input; co quan cap xa viet tay, trung thanh mau."},
    ("PLII_M18", "ho_so_bao_gom"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Giong PLII_M17 (ban nop online): dong cham tay khong input, khong luoi."},
    # --- [F1-OUT 2026-09-06] 11 section OUTPUT_ONLY theo O1 KHONG nam o day:
    # RECLASSIFICATIONS la map "sua kind census" (entry bat buoc co kind +
    # reason; thieu -> KeyError tai normalize_section). 11 section nay census
    # fragment da dung kind/status=output_only, chi can evidence ghi de ->
    # LEAD_STATUS_OVERRIDES (xem dau map do).
    ("PLI_M09", "vung_nhiem_mau_6789_10"): {
        "kind": "source-contamination", "status": "removed_by_source_cleanup",
        "reason": "[F0L O1 2026-09-06] Vung nhiem da bi XOA KHOI NGUON "
                  "(129 para Mau 6/7/8/9-lan2/10, laneC 3eb9a55/merge "
                  "29c850f); 41/41 tag that giu nguyen; gate "
                  "tools.test_m09_decontaminate 8/8 — verdict "
                  "REMOVED_BY_SOURCE_CLEANUP (xoa that, khong nguy trang "
                  "output)."},
    ("PLI_M27", "don_vi_tam_ngung_tiep_tuc"): {
        "kind": "editable-grid", "status": "missing_grid",
        "reason": "6 khoi don vi (tam ngung/tiep tuc x CN/VPDD/DDKD) moi khoi 1 bo cn.*; ban chat danh sach don vi -> editable-grid du kien, cho quyet dinh 1-nhieu."},
    ("PLI_M28", "don_vi_cham_dut_hoat_dong"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "Cau truc danh so 1..4 la thong tin MOT don vi/giay; blocks map du cn.dia_chi/cn.ma_so; khong dong lap, khong STT."},
    ("PLI_M50", "noi_dung_yeu_cau_bao_cao"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Blocks b016-b018 la dong cham '......' khong input cho co quan dien noi dung; khong phai output-table."},
    ("PLI_M54", "xac_nhan_tam_ngung_toan_bo_don_vi"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "Mot cau xac nhan ap dung TOAN BO don vi, da map tu_ngay/den_ngay; census bac bo du doan danh sach cua PLAN muc E."},
    ("PLI_M55", "don_vi_tam_ngung_xac_nhan"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "'sau:' so it, mot giay = mot don vi; blocks map tu_ngay/den_ngay; khong dong lap."},
    ("PLI_M57", "don_vi_tiep_tuc_xac_nhan"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "So it, mot giay = mot don vi; blocks map truong ngay thang; khong dong lap."},
    # [F1-OUT 2026-09-06] O1 adjudicate supersede verdict missing_grid cua P1:
    # '(cac)' don vi = grid mirror tu ho so (CQDKKD phat hanh, khong input).
    # Census fragment dang kind=unknown -> chuan hoa kind o day (map dung de
    # sua kind); status + evidence chi tiet o LEAD_STATUS_OVERRIDES. Truoc do
    # dict literal nay co 2 entry trung key (missing_grid cua P1 khai sau nen
    # ghi de entry O1) — chi giu 1 entry dung.
    ("PLI_M67", "don_vi_cham_dut_sau_day"): {
        "kind": "editable-grid", "status": "output_only",
        "reason": "O1 OUTPUT_ONLY (supersede P1 missing_grid): '(cac) don vi' "
                  "= grid mirror tu ho so; census fragment kind=unknown -> "
                  "chuan hoa editable-grid."},
}

STT_RE = re.compile(r"^\s*STT\b")
GLUED_STT_RE = re.compile(r"^STT[A-ZÀ-Ỹ]")
LIST_HINT_RE = re.compile(r"\b(Danh sách|Liệt kê|Các)\b.{0,60}(sau|dưới đây)", re.I)

DEFECTS = [
    # (đã gỡ plii_m01_stt_thieu_tag_ho_gia_dinh: stt_tag=true cho
    #  ds_tv_ho_gia_dinh đã integrate + test_plii_m01_member_stt PASS 5/5)
    {
        "form_id": "PLI_M23",
        "id": "pli_m23_heading_numbering",
        "detail": "Fragment ghi heading '6.' nhưng template thật là '7.' (sai số đánh số, không đổi bản chất).",
        "evidence": "app/data/table_specs/fragments/review_t0_b.md",
        "queue": "P1-spec-cleanup",
    },
    {
        "form_id": "PLI_M66",
        "id": "pli_m66_bo_ten_ma_x23",
        "detail": "Note '1 bộ tên+mã' thực tế lặp ×2/×3 trong mẫu; cần tách section khi rollout.",
        "evidence": "app/data/table_specs/fragments/review_t0_b.md",
        "queue": "P3-branches-products-admin",
    },
]

SIGNATURE_CLASSIFICATIONS = {
    "PLII_M06": [{"block": 14, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "Cau van huong dan ke khai khi mat ket noi CSDL; review_t0_c xac minh 0 w:tbl."}],
    "PLII_M11": [{"block": 18, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "'bao cao ve cac noi dung sau' la chu thich muc; khong co luoi theo sau."}],
    "PLII_M21": [{"block": 24, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "Cau van ve nop ho so moi/gop noi dung thay doi; khong co luoi theo sau."}],
    "PLI_M18": [{"block": 35, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M32": [{"block": 14, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M33": [{"block": 19, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M50": [{"block": 15, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "'Yeu cầu doanh nghiệp báo cáo về các nội dung sau' la dau muc van ban; vung tuong ung da duoc ghi section noi_dung_yeu_cau_bao_cao (output-table/no_table)."}],


    # hdr2col merge 084444d: bảng header band (band:header) KHÔNG phải bảng
    # dữ liệu — 4 mẫu NO_TABLE duy nhất có w:tbl mới sau regen.
    "PLII_M06": [{"block": 11, "verdict": "FALSE_POSITIVE_HEADER_BAND",
                  "reason": "hdr2col: w:tbl header 2 band - khong phai bang du lieu."}],
    "PLI_M18": [{"block": 32, "verdict": "FALSE_POSITIVE_HEADER_BAND",
                 "reason": "hdr2col: w:tbl header 2 band - khong phai bang du lieu."}],
    "PLI_M32": [{"block": 11, "verdict": "FALSE_POSITIVE_HEADER_BAND",
                 "reason": "hdr2col: w:tbl header 2 band - khong phai bang du lieu."}],
    "PLI_M33": [{"block": 16, "verdict": "FALSE_POSITIVE_HEADER_BAND",
                 "reason": "hdr2col: w:tbl header 2 band - khong phai bang du lieu."}],
}

LEAD_STATUS_OVERRIDES = {
    # --- F1-OUT (2026-09-06, O1 adjudicate: 11 section OUTPUT_ONLY) — lưới do
    # CQĐKKD phát hành, render từ hồ sơ qua mirror cell (không input).
    # Evidence: spec publication/* + blocks mirror run + form-domain output
    # dispatch + tools/test_f1_output_sections 7/7 + app_web
    # test_f1_output_ui 63/63. (Trước đây đặt nhầm trong RECLASSIFICATIONS —
    # map đó bắt buộc kind + reason nên normalize_section văng KeyError;
    # ghi đè status-only phải nằm ở đây.) ---
    ("PLI_M52", "khung_ra_soat_4_nhom"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY: khung rà soát 4 nhóm do CQĐKKD phát hành; "
                    "spec publication/PLI_M52.json + mirror cell; tách key "
                    "ma_so_van_ban theo D4.2=A.",
    },
    ("PLI_M56", "cn_vppd_ddkd_tiep_tuc_truoc_han"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY: giấy xác nhận của CQĐKKD; grid mirror "
                    "'một hoặc một số' đơn vị từ hồ sơ.",
    },
    ("PLI_M63", "dia_diem_truc_thuoc_bi_thu_hoi"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY: quyết định thu hồi của CQĐKKD; grid mirror.",
    },
    ("PLI_M66", "don_vi_dang_lam_thu_tuc_cham_dut"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY + tách section theo defect bo_ten_ma_x23 "
                    "(mỗi đơn vị 1 bộ tên+mã).",
    },
    ("PLI_M66", "ddkd_truc_thuoc_dang_cham_dut"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY; grid mirror từ hồ sơ.",
    },
    ("PLI_M67", "don_vi_cham_dut_sau_day"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY (supersede P1 missing_grid); '(các)' đơn vị "
                    "= grid mirror; kind chuẩn hóa editable-grid qua "
                    "RECLASSIFICATIONS (census fragment kind=unknown).",
    },
    ("PLI_M68", "don_vi_cham_dut_khi_doanh_nghiep_giai_the"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY; grid mirror; thong_bao_dang_giai_the "
                    "đã output-table từ trước.",
    },
    ("PLI_M70", "ho_so_bao_gom"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY (supersede D6.3): hồ sơ bao gồm in 3 dòng "
                    "pháp định theo giấy; fixed-matrix mirror.",
    },
    ("PLI_M71", "ho_so_bao_gom_online"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY; bản điện tử 3 dòng pháp định; "
                    "fixed-matrix mirror.",
    },
    ("PLI_M75", "cn_vppd_ddkd_khoi_phuc"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY; grid 3 loại đơn vị theo giấy.",
    },
    ("PLI_M75", "ddkd_truc_thuoc_khoi_phuc"): {
        "status": "output_only",
        "evidence": "O1 OUTPUT_ONLY; grid mirror từ hồ sơ.",
    },
    # --- Wave P2 (2026-08-27): merge abe6084 (P2A) / 1691728 (P2C) /
    # a61cdfb (P2D) + Lead regen batch 8 mẫu. Evidence = suite thật đã chạy
    # trên main sau merge; loop_audit census giữ nguyên như hồ sơ lịch sử. ---
    ("PLI_M06", "ds_thanh_vien_tnhh"): {
        "status": "already_complete",
        "evidence": "P2A D2.2=A: cột 10 thoi_han_gop_von đã tag sau regen "
                    "(template 11 tag); test_p2a_people_specs [EVD]/[DELTA] 14 PASS.",
    },
    ("PLI_M07", "ds_co_dong_sang_lap"): {
        "status": "already_complete",
        "evidence": "P2A D2.3=A: +dan_toc cột 6 sau regen (10 tag); cùng kiến "
                    "trúc phẳng với PLI_M08; suite P2A 14 PASS.",
    },
    ("PLI_M08", "ds_co_dong_nn"): {
        "status": "already_complete",
        "evidence": "P2A D2.3=A: ghim spec khớp template (7 tag, thiếu 0); "
                    "suite P2A 14 PASS.",
    },
    ("PLI_M10", "ds_cshhl_doanh_nghiep"): {
        "status": "already_complete",
        "evidence": "P2A D2.5=A: cột quyen_chi_phoi trước Ghi chú (11 tag); "
                    "NĐ 168/2025 đ.b.k1 Đ17; suite P2A 14 PASS.",
    },
    ("PLI_M13", "ndd_pl_sau_thay_doi"): {
        "status": "already_complete",
        "evidence": "P2A D2.6/D2.7=A: loop grid 7 cột + minRows1; nguồn 1 "
                    "row-type nên KHÔNG discriminator (không mislabel); 14 PASS.",
    },
    ("PLII_M07", "m7_danh_sach_thanh_vien_hgd"): {
        "status": "already_complete",
        "evidence": "P2A D2.8=A: key riêng ds_thanh_vien_hkd_gcn đúng 7 cột "
                    "nguồn; test_industry_household 13 PASS (loop ngành không "
                    "xâm lấn).",
    },
    ("PLI_M17", "thue_chi_tieu_6_1_8"): {
        "status": "already_complete",
        "evidence": "P2D audit: chk_* đã gắn tag đủ 17 ô tại base cdf8803; "
                    "manifest census T0 stale; test_p2d_tax_specs 10 PASS.",
    },
    ("PLI_M17", "lua_chon_khu_cn_cxc_kt_kccn"): {
        "status": "already_complete",
        "evidence": "P2D D5.1=A: nhóm checkbox đã tag đủ tại base; census stale.",
    },
    ("PLI_M17", "phuong_thuc_dong_bhxh"): {
        "status": "already_complete",
        "evidence": "P2D D5.1=A: nhóm BHXH đã tag đủ tại base; census stale; "
                    "entry trùng sẽ tạo 2 nguồn sự thật nên không khai thêm.",
    },
    ("PLI_M19", "thue_thay_doi_A"): {
        "status": "already_complete",
        "evidence": "P2D: 9 ô chọn-1 đã tag đủ tại base; test_p2d 10 PASS.",
    },
    ("PLI_M23", "thue_chi_tieu_6_1_6"): {
        "status": "already_complete",
        "evidence": "P2D: 10 ô đã tag đủ tại base; numbering nguồn là mục 7 "
                    "(defect đã ghi); section_id giữ nguyên để JOIN spec/tests.",
    },
    ("PLI_M25", "thue_chi_tieu_6_1_6_ctck"): {
        "status": "already_complete",
        "evidence": "P2D: 10 ô đã tag đủ tại base (CTCK); census stale.",
    },
    ("PLI_M01", "tai_san_gop_von_von_dau_tu"): {
        "status": "already_complete",
        "evidence": "P2C D1.1=A/D1.2=B: fixed-matrix 7 dòng + Tổng số computed, "
                    "'tài sản khác' là ô mô tả text; regen template + "
                    "section_specs; suite P2C 16 PASS, runtime contract wired.",
    },
    ("PLI_M01", "bhxh_phuong_thuc_dong"): {
        "status": "already_complete",
        "evidence": "Phase 3 (2026-09-03): census stale — notes than thiếu "
                    "chk_bc_03_thang nhưng ba64f29 (fix checkbox det rule "
                    "0?3/0?6 thang) đã đủ 3/3 token chk_bc_hang_thang/"
                    "chk_bc_03_thang/chk_bc_06_thang trong vùng anchor mục 7 "
                    "(test_phase3_m01_m02 PASS); cùng kiến trúc nhóm chk qua "
                    "đường chung như tiền lệ PLI_M17 phuong_thuc_dong_bhxh "
                    "(P2D D5.1=A) — không khai spec/grid riêng để tránh 2 "
                    "nguồn sự thật; audit scalar_credited tự verify region keys.",
    },
    ("PLI_M02", "nguon_von_dieule"): {
        "status": "already_complete",
        "evidence": "P2C D1.1=A: 5 dòng + Tổng cộng output_only, cùng key "
                    "canonical F2(M03); regen + section_specs; 16 PASS.",
    },
    ("PLI_M02", "tai_san_gop_von_von_dieu_le"): {
        "status": "already_complete",
        "evidence": "P2C: 6 dòng + Tổng số; 'tài sản khác' ô mô tả theo chữ "
                    "mẫu; regen + section_specs; 16 PASS.",
    },
    # --- R3B1 rebuild (b9bc572): 3 nested-grid thành bảng thật; 2 nhóm cột
    # cuối vẫn KHAI THIẾU chờ owner -> partial_columns (như tiền lệ M09). ---
    ("PLI_M02", "nddpl_uy_quyen_chu_so_huu"): {
        "status": "partial_columns",
        "evidence": "N1 rebuild 14 cột w:tbl thật (visual pilot PASS); thiếu 2 "
                    "nhóm header chưa có evidence tag canonical (gap đã ghi).",
    },
    ("PLI_M12", "ndd_uy_quyen_sau_thay_doi"): {
        "status": "partial_columns",
        "evidence": "N6 rebuild 15 cột; cùng gap 2 nhóm cuối như N1.",
    },
    ("PLI_M15", "ndd_pl_uy_quyen_chu_so_huu_moi"): {
        "status": "partial_columns",
        "evidence": "N7 rebuild 14 cột; cùng gap 2 nhóm cuối như N1.",
    },
    ("PLI_M72", "nganh_nghe_5_loai_hinh"): {
        "status": "already_complete",
        "evidence": "P1 integrate: generator occurrence identity + spec 5 occurrence "
                    "(ds_nganh_dntn/tnhh_1tv/tnhh_2tv/ctcp/dhdn) rebuild du 5 bang; "
                    "tools/test_industry_change.py 6 PASS (spec+blocks+render tung loai hinh, khong tron du lieu).",
    },
    ("PLII_M02", "a6_1_nganh_bo_sung"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_bo_sung (4 cot) qua occurrence contract; "
                    "tools/test_industry_household.py 13 PASS incl. render isolation.",
    },
    ("PLII_M02", "a6_2_nganh_bo"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_xoa_bo; suite household 13 PASS.",
    },
    ("PLII_M02", "a6_3_nganh_sua_chinh"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_sua_doi_chi_tiet (3 cot, khong co nganh chinh theo template); "
                    "suite household 13 PASS.",
    },
    # --- Owner P1/P2/P3 (2026-09-03): lanes merged, evidence verified ---
    ("PLII_M02", "a4_tv_hgd_sau_thay_doi"): {"status": "already_complete", "evidence": "P2 member grid rebuild 10 cột; test_member_grids_rebuild PASS."},
    ("PLII_M02", "a7_thue_chi_tieu_cu_moi"): {"status": "already_complete", "evidence": "cap-von D5.2=A fixed-matrix 3 cột."},
    ("PLII_M02", "c7_tv_hgd_cap_doi"): {"status": "already_complete", "evidence": "P2 member grid rebuild 10 cột."},
    ("PLI_M03", "nguon_von_dieule"): {"status": "already_complete", "evidence": "cap-von D1.1=A fixed-matrix 3 cột."},
    ("PLI_M04", "nguon_von_dieule"): {"status": "already_complete", "evidence": "cap-von D1.1=A fixed-matrix."},
    ("PLI_M04", "co_cau_loai_co_phan"): {"status": "already_complete", "evidence": "cap-von D1.4=A fixed-matrix."},
    ("PLI_M04", "co_phan_duoc_quyen_chao_ban"): {"status": "already_complete", "evidence": "cap-von D1.4=A fixed-matrix."},
    ("PLI_M05", "nguon_von_dieule"): {"status": "already_complete", "evidence": "cap-von D1.1=A fixed-matrix."},
    ("PLI_M12", "nguon_von_dieule_sau_thay_doi"): {"status": "already_complete", "evidence": "cap-von D1.1=A fixed-matrix."},
    ("PLI_M72", "thanh_vien_tnhhh_hai_tv_tro_len"): {"status": "already_complete", "evidence": "P2 member grid rebuild 8 cột."},
    ("PLI_M72", "thanh_vien_hop_danh"): {"status": "already_complete", "evidence": "P2 member grid rebuild 7 cột."},
    ("PLI_M72", "co_dong_sang_lap_cp"): {"status": "already_complete", "evidence": "P2 member grid rebuild 10 cột."},
    ("PLI_M72", "co_dong_nuoc_ngoai_cp"): {"status": "already_complete", "evidence": "P2 member grid rebuild 10 cột."},
    # --- F1-IN (2026-09-06, O1 adjudicate: 10 section IMPLEMENTED AS USER
    # INPUT) — specs tools/form_specs + regen + runtime contracts + suites
    # tools/test_f1_input_sections.py / app_web/test_f1_input_ui.js ---
    ("PLI_M02", "mo_hinh_to_chuc_cong_ty"): {
        "status": "already_complete",
        "evidence": "O1: chọn-1 radio qua cặp chk_auto_* (Q-V1 ô vuông viền "
                    "+ X; EXCLUSIVE_CHK_GROUPS mo_hinh_to_chuc chặn tick "
                    "đôi); scalar/check-token đường chung collectKeys.",
    },
    ("PLI_M12", "tai_san_gop_von_sau_thay_doi_vdl"): {
        "status": "already_complete",
        "evidence": "O1+O2 fixed-matrix 7 dòng (TT121 Mẫu 12 p81-p111), tổng "
                    "computed outputOnly; loop riêng don_vi_truc_thuoc_tam_"
                    "ngung_tiep_tuc thuộc M27. Suite test_f1_input_sections.",
    },
    ("PLI_M12", "tai_san_gop_von_sau_thay_doi_von_dau_tu"): {
        "status": "already_complete",
        "evidence": "O1+O2 fixed-matrix 7 dòng (TT121 Mẫu 12 p197-p226, ngữ "
                    "cảnh vốn đầu tư DNTN riêng); suite "
                    "test_f1_input_sections.",
    },
    ("PLI_M12", "co_cau_loai_co_phan_sau_thay_doi"): {
        "status": "already_complete",
        "evidence": "O1+O2 fixed-matrix 6 dòng (TT121 Mẫu 12 p113-p147, "
                    "verbatim 'Cổ phần ưu đã biểu quyết' theo bản in; "
                    "menh_gia_co_phan scalar vùng anchor); "
                    "test_f1_input_sections.",
    },
    ("PLI_M27", "danh_sach_ndd_pl_thong_bao"): {
        "status": "already_complete",
        "evidence": "O1 grid nhiều dòng NĐDPL 3 trường 2026; loop riêng "
                    "ds_ndd_pl_thong_bao_tam_ngung; minRows1 (footnote 2); "
                    "test_f1_input_sections + test_f1_input_ui.",
    },
    ("PLI_M27", "don_vi_tam_ngung_tiep_tuc"): {
        "status": "already_complete",
        "evidence": "O1 editable-grid đơn vị (loai_don_vi là cột thay heading "
                    "b/c); 2 occurrence cùng entry spec: loop riêng "
                    "don_vi_truc_thuoc_tam_ngung_tiep_tuc (mục 1) + "
                    "don_vi_tiep_tuc_truoc_han (mục 2); "
                    "test_f1_input_sections + test_f1_input_ui.",
    },
    ("PLI_M78", "san_pham_cung_cap_thong_tin"): {
        "status": "already_complete",
        "evidence": "O1+D6.4 fixed-matrix 4 dòng (3 sản phẩm cố định verbatim "
                    "'của …' + Sản phẩm khác; SL >=0; mô tả bắt buộc khi "
                    "SL>0 qua requiredIfPositive DESC_REQUIRED); "
                    "test_f1_input_sections + test_f1_input_ui.",
    },
    ("PLI_M79", "tai_lieu_kem_theo_de_nghi"): {
        "status": "already_complete",
        "evidence": "O1+D6.5/D6.6 editable-grid 3+ dòng metadata only "
                    "(mo_ta_tai_lieu required, so_ban/so_trang optional, "
                    "không upload); loop ds_tai_lieu_kem_theo_m79; "
                    "test_f1_input_sections + test_f1_input_ui.",
    },
    ("PLI_M80", "tai_lieu_kem_theo_thu_hoi"): {
        "status": "already_complete",
        "evidence": "O1+D6.5/D6.6 editable-grid như M79; loop "
                    "ds_tai_lieu_kem_theo_m80; test_f1_input_sections.",
    },
    ("PLII_M02", "c5_thue_chi_tieu_cap_doi"): {
        "status": "already_complete",
        "evidence": "O1+D5.2=A fixed-matrix 2 chỉ tiêu thật của Mục C cấp đổi "
                    "(5.1 địa chỉ nhận thông báo thuế / 5.2 tổng số lao "
                    "động; nguồn Mục C không có dòng '…'); row id canonical "
                    "a7; test_f1_input_sections.",
    },
}

CAVEATS = [
    "~34 anchor trong t0_b viết tắt '...docx#pN' không resolve được bằng máy (đã review xác minh tay); chuẩn hóa khi sinh spec.",
    "PLI_M72: P1 đã integrate đủ 5 lưới ngành theo occurrence contract (anchor nguồn thật p13/42/85/134/168); 4 lưới nested-grid thành viên/cổ đông vẫn BLOCKED chờ legal + people-ownership.",
    "PLII_M02: vùng C.3 giữ tên loop canonical ds_nganh (dùng chung PLI_M02/M07) kèm metadata occurrence_id=nganh_hien_tai.",
    "GRID_META phía app hiện là map phẳng theo tên loop: các loop mới PLI_M72 (5) và PLII_M02 (3 loop Mục A) tạm chạy legacy path, chưa có VSIC/primary validation riêng — queue P1-UI/P2 form-scoped meta.",
    "Form BLOCKED_LEGAL_REVIEW không tính TABLE_COMPLETE; cần quyết định người dùng trước khi rollout tương ứng.",
]


def load_fragments():
    forms = []
    for tag, rng, commit in FRAGMENTS:
        path = os.path.join(FRAG_DIR, "%s.json" % tag)
        data = json.load(open(path, encoding="utf-8"))
        for f in data["forms"]:
            f["_source_fragment"] = tag
            f["_source_commit"] = commit
            f["_range"] = rng
            forms.append(f)
    return forms


def normalize_section(fid, sec):
    out = dict(sec)
    sk = out.pop("semantic_key_suggestion", None)
    if sk is not None:
        out["semantic_key"] = sk
    rc = RECLASSIFICATIONS.get((fid, out.get("section_id")))
    if rc is not None:
        out["kind"] = rc["kind"]
        if "status" in rc:
            out["status"] = rc["status"]
        out["lead_reclassification"] = {"reason": rc["reason"]}
    ho = HEADING_OVERRIDES.get((fid, out.get("section_id")))
    if ho is not None:
        se = dict(out.get("source_evidence") or {})
        se.update(ho)
        out["source_evidence"] = se
    # [F1-IN] evidence override (notes / required_columns) — metadata mô tả
    # stale của census T0 khi nguồn hiện hành đã đổi; status không đụng.
    eo = SECTION_EVIDENCE_OVERRIDES.get((fid, out.get("section_id")))
    if eo is not None:
        if "required_columns" in eo:
            out["required_columns"] = list(eo["required_columns"])
        if "notes" in eo:
            out["notes"] = eo["notes"]
        # heading/heading_note merge vào source_evidence như HEADING_OVERRIDES
        se_keys = {"heading", "heading_note"} & set(eo)
        if se_keys:
            se = dict(out.get("source_evidence") or {})
            se.update({k: eo[k] for k in se_keys})
            out["source_evidence"] = se
    return out


def para_text(block):
    parts = []
    for run in block.get("runs", []):
        if isinstance(run, dict) and isinstance(run.get("text"), str):
            parts.append(run["text"])
    return "".join(parts)


def recount_blocks(form_id):
    path = os.path.join(BLOCKS_DIR, "%s.json" % form_id)
    data = json.load(open(path, encoding="utf-8"))
    counts = {"p": 0, "chk": 0, "table": 0, "loop": 0}
    sig_p = 0
    hints = 0
    hits = []
    for bi, b in enumerate(data["blocks"]):
        t = b.get("t")
        if t in counts:
            counts[t] += 1
        if t == "p":
            txt = para_text(b)
            stt_hit = bool(STT_RE.search(txt) or GLUED_STT_RE.match(txt.strip()))
            hint_hit = bool(LIST_HINT_RE.search(txt))
            if stt_hit:
                sig_p += 1
            if hint_hit:
                hints += 1
            if stt_hit or hint_hit:
                hits.append({"block": bi, "stt": stt_hit, "list_hint": hint_hit,
                             "excerpt": txt.strip()[:120]})
    return counts, sig_p, hints, hits


def deep_template_tables(form_id):
    from docx import Document

    path = os.path.join(TEMPLATES_DIR, "%s.docx" % form_id)
    doc = Document(path)
    n = len(doc.tables)

    def _is_header_band(tbl) -> bool:
        """hdr2col merge 084444d: bảng header 2 band là layout artifact
        (ô tên + quốc hiệu + Số/ngày), KHÔNG phải bảng dữ liệu — không đếm."""
        if not tbl.rows or not tbl.rows[0].cells:
            return False
        first = tbl.rows[0].cells[0].text or ""
        if not ("TÊN DOANH NGHIỆP" in first or "TÊN HỘ KINH DOANH" in first):
            return False
        all_text = "\n".join(c.text for r in tbl.rows for c in r.cells)
        return "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in all_text

    n -= sum(1 for t in doc.tables if _is_header_band(t))
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for part in (doc.part.header_parts if hasattr(doc.part, "header_parts") else []):
        pass
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/header") or rel.reltype.endswith("/footer"):
            root = rel.target_part._element if hasattr(rel.target_part, "_element") else None
            if root is not None:
                n += len(root.findall(".//%stbl" % W))
    body_root = doc.element.body
    body_tbls = body_root.findall(".//%stbl" % W)
    body_bands = sum(1 for t in body_tbls
                     if any(t is tt._tbl for tt in doc.tables if _is_header_band(tt)))
    raw_tbl = len(body_tbls) - body_bands
    return max(n, raw_tbl)


def build(forms):
    forms_sorted = sorted(forms, key=lambda f: f["form_id"])
    out_forms = []
    for f in forms_sorted:
        fid = f["form_id"]
        counts, sig_p, hints, hits = recount_blocks(fid)
        frag_counts = f.get("summary_counts", {})
        entry = {
            "form_id": fid,
            "form_status": f["form_status"],
            "source_fragment": f["_source_fragment"],
            "source_commit": f["_source_commit"],
            "sections": [normalize_section(fid, s) for s in f.get("sections", [])],
            "legal_questions": f.get("legal_questions", []),
            "defects": [d for d in DEFECTS if d["form_id"] == fid],
            "summary_counts_fragment": frag_counts,
            "summary_counts_recount": counts,
            "detector": {"p_signatures": sig_p, "list_hints": hints,
                         "hits": hits,
                         "classifications": SIGNATURE_CLASSIFICATIONS.get(fid, [])},
        }
        for s in entry["sections"]:
            ov = LEAD_STATUS_OVERRIDES.get((fid, s.get("section_id")))
            if ov is not None:
                s["status"] = ov["status"]
                s["lead_status_override"] = {"evidence": ov["evidence"]}
        out_forms.append(entry)
    return {
        "version": "table-manifest-v1",
        "generated_by": "lead/tools/census/build_manifest.py",
        "sources": [
            {"fragment": tag, "range": rng, "commit": commit} for tag, rng, commit in FRAGMENTS
        ],
        "reviews": REVIEWS,
        "caveats": CAVEATS,
        "totals": {},
        "forms": out_forms,
    }

def validate(manifest, deep):
    errors = []
    block_files = sorted(
        os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(BLOCKS_DIR, "*.json"))
    )
    mids = sorted(f["form_id"] for f in manifest["forms"])
    if len(mids) != 87:
        errors.append("manifest co %d form, can 87" % len(mids))
    if mids != block_files:
        errors.append("manifest ids khac danh sach blocks: %s" % (
            set(mids) ^ set(block_files)))
    tot_status = {}
    tot_sections = {}
    tot_sig = 0
    stale = []
    for f in manifest["forms"]:
        fid = f["form_id"]
        st = f["form_status"]
        if st not in VALID_STATUS:
            errors.append("%s: form_status '%s' khong hop le" % (fid, st))
        tot_status[st] = tot_status.get(st, 0) + 1
        rc = f["summary_counts_recount"]
        fc = f.get("summary_counts_fragment", {})
        for k in ("p", "chk", "table", "loop"):
            if fc and fc.get(k, -1) != rc[k]:
                if fid in EVOLVED_FORMS:
                    print("INFO %s: %s fragment=%s recount=%s (%s)" % (
                        fid, k, fc.get(k), rc[k], EVOLVED_FORMS[fid]))
                else:
                    errors.append("%s: summary_counts.%s fragment=%s recount=%s" % (fid, k, fc.get(k), rc[k]))
        det = f["detector"]
        hits = det.get("hits", [])
        cls_by_block = {c["block"]: c for c in det.get("classifications", [])}
        uncovered = [h for h in hits if h["block"] not in cls_by_block]
        for blk, c in sorted(cls_by_block.items()):
            if not any(h["block"] == blk for h in hits):
                stale.append("%s#b%03d" % (fid, blk))
            if st == "NO_TABLE" and not c["verdict"].startswith("FALSE_POSITIVE"):
                errors.append("%s: NO_TABLE nhung classification %s khong phai false positive" % (fid, c["verdict"]))
        for s in f["sections"]:
            kind = s.get("kind")
            stat = s.get("status")
            sid = s.get("section_id")
            if kind not in SECTION_KINDS:
                errors.append("%s/%s: section kind '%s' KHONG HOP LE (unknown/planned bi cam)" % (fid, sid, kind))
            if stat not in SECTION_STATUSES:
                errors.append("%s/%s: section status '%s' khong hop le (planned/TODO bi cam)" % (fid, sid, stat))
            if kind == "source-contamination" and st != "BLOCKED_LEGAL_REVIEW":
                errors.append("%s/%s: source-contamination chi cho phep tren form BLOCKED_LEGAL_REVIEW" % (fid, sid))
        if st == "NO_TABLE":
            if uncovered:
                tot_sig += len(uncovered)
                errors.append("%s: NO_TABLE co %d signature chua classify: blocks %s" % (
                    fid, len(uncovered), [h["block"] for h in uncovered]))
            bad_secs = [
                s for s in f["sections"]
                if not (s.get("kind") in NO_TABLE_SECTION_KINDS and s.get("status") == "no_table")
            ]
            if bad_secs:
                errors.append("%s: NO_TABLE nhung co section khong phai prose/scalar thuan thong tin: %s" % (
                    fid, [(s.get("section_id"), s.get("kind"), s.get("status")) for s in bad_secs]))
        elif not f["sections"]:
            errors.append("%s: %s phai co it nhat 1 section entry" % (fid, st))
        for kind in SECTION_KINDS:
            tot_sections[kind] = tot_sections.get(kind, 0) + sum(
                1 for s in f["sections"] if s.get("kind") == kind
            )
        if deep:
            ntbl = deep_template_tables(fid)
            f["detector"]["template_w_tbl"] = ntbl
            if st == "NO_TABLE" and ntbl != 0:
                errors.append("%s: NO_TABLE nhung template co %d w:tbl" % (fid, ntbl))
    if stale:
        print("WARNING: classification stale (khong con hit): %s" % ", ".join(stale))
    total_secs = sum(len(f["sections"]) for f in manifest["forms"])
    kind_sum = sum(tot_sections.values())
    if total_secs != kind_sum:
        errors.append("tong so section (%d) khac tong sections_by_kind (%d)" % (total_secs, kind_sum))
    manifest["totals"] = {
        "forms": len(manifest["forms"]),
        "by_form_status": tot_status,
        "sections_total": total_secs,
        "sections_by_kind": tot_sections,
        "unclassified_signatures": tot_sig,
    }
    return errors


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="dem w:tpl trong templates (cham hon)")
    ap.add_argument("--write", action="store_true", help="ghi manifest.json")
    args = ap.parse_args()

    forms = load_fragments()
    manifest = build(forms)
    errors = validate(manifest, args.deep)

    print("Manifest forms:", len(manifest["forms"]))
    print("Totals:", json.dumps(manifest["totals"], ensure_ascii=False, indent=1))
    blocked = [f["form_id"] for f in manifest["forms"] if f["form_status"] == "BLOCKED_LEGAL_REVIEW"]
    print("BLOCKED_LEGAL_REVIEW (%d): %s" % (len(blocked), ", ".join(blocked)))
    if errors:
        print("GATE FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("GATE PASS: 87/87, moi signature da classify, counts khop.")
    if args.write:
        os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1)
        print("Wrote", os.path.relpath(MANIFEST_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
