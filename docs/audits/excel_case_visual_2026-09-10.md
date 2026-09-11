# Audit bố cục trực quan — Excel case-level (2026-09-10)

- HEAD: `e9bd9c4` — tool: `tools/excel_case_visual.py`
- LibreOffice: `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77` — render: pymupdf 1.28.2 (PNG ~150dpi)
- Meta xuất: `{"today": "11/09/2026", "exported_at": "11/09/2026 08:15"}`
- Bằng chứng: `generated_ho_so/_visual_layout/excel_case_20260910/<caseId>/` (`page-NN.png`, `contact-sheet.png`, `*.pdf`, `*.xlsx`)
- Phạm vi: case READY đọc từ đĩa lúc chạy. Case PENDING (chưa có câu hỏi) = NOT RUN, chờ lane content bật.

## Bảng tổng hợp

| case | sheet | trang PDF | cắt cột / clip | tràn trang | font tiếng Việt | số hàng bảng |
|---|---|---|---|---|---|---|
| bo_sung_cap_nhat_thong_tin_dkdn | 5 | 6 | PASS | PASS | PASS | PASS |
| cap_doi_gcdkkd_sang_gcdn | 5 | 4 | PASS | PASS | PASS | PASS |
| cap_lai_gcdn_va_giay_pham_dkkd | 5 | 4 | PASS | PASS | PASS | PASS |
| cham_dut_hoat_dong_cn_vpdd_ddkd | 5 | 4 | PASS | PASS | PASS | PASS |
| cham_dut_hoat_dong_hkd | 5 | 4 | PASS | PASS | PASS | PASS |
| chuyen_doi_hkd_sang_dn | 9 | 33 | PASS | PASS | PASS | PASS |
| cong_bo_noi_dung_dkdn | 6 | 4 | PASS | PASS | PASS | PASS |
| cung_cap_thong_tin_dkdn | 6 | 4 | PASS | PASS | PASS | PASS |
| dang_ky_ho_kinh_doanh_lan_dau | 6 | 5 | PASS | PASS | PASS | PASS |
| giai_the_doanh_nghiep | 5 | 4 | PASS | PASS | PASS | PASS |
| huy_quyet_dinh_giai_the | 5 | 4 | PASS | PASS | PASS | PASS |
| lap_chi_nhanh_vpdd | 6 | 6 | PASS | PASS | PASS | PASS |
| lap_dia_diem_kinh_doanh | 6 | 6 | PASS | PASS | PASS | PASS |
| pilot_ui_m02_m06 | 7 | 11 | PASS | PASS | PASS | PASS |
| tam_ngung_tiep_tuc_kinh_doanh_dn | 5 | 5 | PASS | PASS | PASS | PASS |
| tam_ngung_tiep_tuc_kinh_doanh_hkd | 5 | 4 | PASS | PASS | PASS | PASS |
| thanh_lap_ctcp | 8 | 15 | PASS | PASS | PASS | PASS |
| thanh_lap_dntn | 6 | 8 | PASS | PASS | PASS | PASS |
| thanh_lap_hop_danh | 7 | 12 | PASS | PASS | PASS | PASS |
| thanh_lap_tnhh_1tv | 6 | 7 | PASS | PASS | PASS | PASS |
| thanh_lap_tnhh_2tv | 7 | 13 | PASS | PASS | PASS | PASS |
| thay_doi_chusohuu_chudn | 7 | 7 | PASS | PASS | PASS | PASS |
| thay_doi_nganh_nghe | 5 | 6 | PASS | PASS | PASS | PASS |
| thay_doi_nguoi_dai_dien_pl | 6 | 4 | PASS | PASS | PASS | PASS |
| thay_doi_noi_dung_dang_ky_hkd | 6 | 5 | PASS | PASS | PASS | PASS |
| thay_doi_noi_dung_hoat_dong_cn_vpdd | 6 | 6 | PASS | PASS | PASS | PASS |
| thay_doi_ten_va_tru_so | 5 | 6 | PASS | PASS | PASS | PASS |
| thay_doi_von_dieu_le | 5 | 6 | PASS | PASS | PASS | PASS |

Chi tiết `pages_per_sheet` (trang đầu chứa TOÀN VĂN tiêu đề sheet — dò qua text-layer, tham khảo). LƯU Ý: với sheet rộng hơn khổ giấy, tiêu đề hàng 1 có thể bị CẮT tại mép phải trang thật (vd `tam_ngung_tiep_tuc_kinh_doanh_hkd`: tiêu đề guide dừng ở "…hộ kinh doa") — khi đó 'trang đầu' lệch về trang sau; việc cắt tiêu đề này tự nó là phát hiện layout, thuộc WARN tràn trang:

- **bo_sung_cap_nhat_thong_tin_dkdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 5}
- **cap_doi_gcdkkd_sang_gcdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị cấp đổi sang Gi": 2, "Giấy_tờ_cần_gửi": 3}
- **cap_lai_gcdn_va_giay_pham_dkkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị cấp lại Giấy ch": 2, "Giấy_tờ_cần_gửi": 3}
- **cham_dut_hoat_dong_cn_vpdd_ddkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Thông báo về việc chấm dứt h": 2, "Giấy_tờ_cần_gửi": 3}
- **cham_dut_hoat_dong_hkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Thông báo về việc chấm dứt h": 2, "Giấy_tờ_cần_gửi": 3}
- **chuyen_doi_hkd_sang_dn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 8, "02_Giấy đề nghị đăng ký doanh n": 14, "03_Giấy đề nghị đăng ký doanh n": 18, "04_Giấy đề nghị đăng ký doanh n": 25, "Giấy_tờ_cần_gửi": 32}
- **cong_bo_noi_dung_dkdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị công bố nội dun": 2, "Giấy_tờ_cần_gửi": 3}
- **cung_cap_thong_tin_dkdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị cung cấp thông": 2, "Giấy_tờ_cần_gửi": 3}
- **dang_ky_ho_kinh_doanh_lan_dau**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký hộ kinh": 2, "Giấy_tờ_cần_gửi": 4}
- **giai_the_doanh_nghiep**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Thông báo về việc giải thể d": 2, "Giấy_tờ_cần_gửi": 3}
- **huy_quyet_dinh_giai_the**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Thông báo về việc huỷ bỏ Ngh": 2, "Giấy_tờ_cần_gửi": 3}
- **lap_chi_nhanh_vpdd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký hoạt độ": 2, "Giấy_tờ_cần_gửi": 5}
- **lap_dia_diem_kinh_doanh**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký hoạt độ": 2, "Giấy_tờ_cần_gửi": 5}
- **pilot_ui_m02_m06**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 4, "02_Danh sách thành viên công ty": 8, "Giấy_tờ_cần_gửi": 10}
- **tam_ngung_tiep_tuc_kinh_doanh_dn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Thông báo về việc tạm ngừng": 2, "Giấy_tờ_cần_gửi": 4}
- **tam_ngung_tiep_tuc_kinh_doanh_hkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký tạm ngừ": 2, "Giấy_tờ_cần_gửi": 3}
- **thanh_lap_ctcp**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 4, "02_Danh sách cổ đông sáng lập c": 11, "03_Danh sách cổ đông là nhà đầu": 12, "Giấy_tờ_cần_gửi": 14}
- **thanh_lap_dntn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 2, "Giấy_tờ_cần_gửi": 7}
- **thanh_lap_hop_danh**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 4, "02_Danh sách thành viên công ty": 9, "Giấy_tờ_cần_gửi": 11}
- **thanh_lap_tnhh_1tv**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 2, "Giấy_tờ_cần_gửi": 6}
- **thanh_lap_tnhh_2tv**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký doanh n": 4, "02_Danh sách thành viên công ty": 10, "Giấy_tờ_cần_gửi": 12}
- **thay_doi_chusohuu_chudn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 3, "02_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 6}
- **thay_doi_nganh_nghe**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_nguoi_dai_dien_pl**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 3}
- **thay_doi_noi_dung_dang_ky_hkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 4}
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_ten_va_tru_so**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_von_dieu_le**: {"Hướng_dẫn": 0, "Thông_tin_chung": 1, "01_Giấy đề nghị đăng ký thay đổ": 2, "Giấy_tờ_cần_gửi": 5}

Font PDF dùng (tham khảo — tự động không adjudicate được hình dục chữ):

- **bo_sung_cap_nhat_thong_tin_dkdn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **cap_doi_gcdkkd_sang_gcdn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **cap_lai_gcdn_va_giay_pham_dkkd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **cham_dut_hoat_dong_cn_vpdd_ddkd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **cham_dut_hoat_dong_hkd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **chuyen_doi_hkd_sang_dn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+Carlito`
- **cong_bo_noi_dung_dkdn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **cung_cap_thong_tin_dkdn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic`
- **dang_ky_ho_kinh_doanh_lan_dau**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **giai_the_doanh_nghiep**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **huy_quyet_dinh_giai_the**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **lap_chi_nhanh_vpdd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **lap_dia_diem_kinh_doanh**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSerif-Italic`
- **pilot_ui_m02_m06**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+Carlito`
- **tam_ngung_tiep_tuc_kinh_doanh_dn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **tam_ngung_tiep_tuc_kinh_doanh_hkd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thanh_lap_ctcp**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic, JAAAAA+Carlito`
- **thanh_lap_dntn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic`
- **thanh_lap_hop_danh**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic, JAAAAA+Carlito`
- **thanh_lap_tnhh_1tv**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thanh_lap_tnhh_2tv**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic, JAAAAA+Carlito`
- **thay_doi_chusohuu_chudn**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic, JAAAAA+Carlito`
- **thay_doi_nganh_nghe**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thay_doi_nguoi_dai_dien_pl**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic`
- **thay_doi_noi_dung_dang_ky_hkd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+LinuxLibertineGZI`
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG`
- **thay_doi_ten_va_tru_so**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thay_doi_von_dieu_le**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`

## Độ trung thực text-layer (đối chiếu chuỗi nội dung ô với PDF)

Text-layer được TÁI LẬP từ toạ độ ký tự (LibreOffice xuất glyph dấu tiếng Việt trong các text-run riêng lệch baseline). 4 tầng khớp: nguyên văn / đủ chữ mất dấu / đủ bộ ký tự xen kẽ (wrap, glyph dịch vị) / thiếu ký tự. Lớp PDF dùng font thay thế Calibri (Caladea/Libertine) nên HÌNH DẠNG dấu vẫn cần xem mắt — mã ký tự thì đối chiếu được.

- **bo_sung_cap_nhat_thong_tin_dkdn**: 61/87 nguyên văn, 0 mất dấu (fold-only), 26 xen kẽ (bag-only), 0 thiếu ký tự.
- **cap_doi_gcdkkd_sang_gcdn**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **cap_lai_gcdn_va_giay_pham_dkkd**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **cham_dut_hoat_dong_cn_vpdd_ddkd**: 17/22 nguyên văn, 0 mất dấu (fold-only), 5 xen kẽ (bag-only), 0 thiếu ký tự.
- **cham_dut_hoat_dong_hkd**: 22/28 nguyên văn, 0 mất dấu (fold-only), 6 xen kẽ (bag-only), 0 thiếu ký tự.
- **chuyen_doi_hkd_sang_dn**: 20/27 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **cong_bo_noi_dung_dkdn**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **cung_cap_thong_tin_dkdn**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **dang_ky_ho_kinh_doanh_lan_dau**: 57/78 nguyên văn, 0 mất dấu (fold-only), 21 xen kẽ (bag-only), 0 thiếu ký tự.
- **giai_the_doanh_nghiep**: 17/23 nguyên văn, 0 mất dấu (fold-only), 6 xen kẽ (bag-only), 0 thiếu ký tự.
- **huy_quyet_dinh_giai_the**: 17/22 nguyên văn, 0 mất dấu (fold-only), 5 xen kẽ (bag-only), 0 thiếu ký tự.
- **lap_chi_nhanh_vpdd**: 17/24 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **lap_dia_diem_kinh_doanh**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **pilot_ui_m02_m06**: 18/22 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **tam_ngung_tiep_tuc_kinh_doanh_dn**: 33/52 nguyên văn, 0 mất dấu (fold-only), 19 xen kẽ (bag-only), 0 thiếu ký tự.
- **tam_ngung_tiep_tuc_kinh_doanh_hkd**: 31/37 nguyên văn, 0 mất dấu (fold-only), 6 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_ctcp**: 19/26 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_dntn**: 17/22 nguyên văn, 0 mất dấu (fold-only), 5 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_hop_danh**: 18/24 nguyên văn, 0 mất dấu (fold-only), 6 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_tnhh_1tv**: 17/24 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_tnhh_2tv**: 18/25 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_chusohuu_chudn**: 18/25 nguyên văn, 0 mất dấu (fold-only), 7 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_nganh_nghe**: 61/88 nguyên văn, 0 mất dấu (fold-only), 27 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_nguoi_dai_dien_pl**: 17/23 nguyên văn, 0 mất dấu (fold-only), 6 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_noi_dung_dang_ky_hkd**: 68/92 nguyên văn, 0 mất dấu (fold-only), 24 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: 17/21 nguyên văn, 0 mất dấu (fold-only), 4 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_ten_va_tru_so**: 61/89 nguyên văn, 0 mất dấu (fold-only), 28 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_von_dieu_le**: 61/92 nguyên văn, 0 mất dấu (fold-only), 31 xen kẽ (bag-only), 0 thiếu ký tự.

## Chuỗi THIẾU KÝ TỰ trong text-layer PDF (ứng viên cắt cột/clip thật)

(không có — mọi chuỗi nội dung ô đều đủ ký tự trong PDF)

## Chuỗi ĐỦ CHỮ NHƯNG MẤT DẤU trong text-layer (mã ký tự lệch — artefact font)

(không có)

## CẦN NGƯỜI NHÌN MẮT — MANUAL NOT RUN

Text-layer PDF không adjudicate được các mục dưới đây. Cần mở `page-NN.png` (đã kèm) và TỐT NHẤT là mở file `.xlsx` trong Excel thật, zoom 100%/125%:

1. **Tofu/glyph sai** cho ký tự đặc biệt (▾, •, ơ ư + dấu) — đã thấy LibreOffice vẽ lệch một số glyph dấu khi render PDF (xem mục 'Độ trung thực text-layer'); text-layer không adjudicate được hình dạng chữ — phải nhìn ảnh PNG và Excel thật (zoom 100%/125%).
2. **Màu nền ô** VÀNG (`FFF2CC`) / XÁM (`D9D9D9`) và palette nhóm câu.
3. **Mũi tên dropdown** trên ô select (Calc in PDF không vẽ mũi tên — xác nhận trên Excel thật có ▾ khi bấm ô).
4. **Chỗ ngắt trang in** của sheet dài (mục tràn trang WARN phía trên chỉ báo số trang, không đánh giá chỗ cắt có làm mất ô vàng không).
5. **Watermark đỏ** `Giấy_tờ_cần_gửi` hiển thị đúng mức đáng sợ (đỏ `C00000`, không lấn chữ thường).
6. **Độ rộng cột thực tế trên Excel** (Calc render gần đúng; Excel có thể xuống hàng khác với PDF).

## Khuyến nghị cho Lead (từ quan sát tự động — lane visual KHÔNG sửa exporter/importer)

1. **In ấn tràn cột**: nhiều case có số trang PDF > số sheet — sheet rộng hơn khổ A4 dọc, cột phải (ghi chú ví dụ, cột E/F) tràn sang trang riêng. Đề xuất exporter thêm `ws.page_setup.fitToWidth = 1` (hoặc orientation landscape cho sheet có bảng row_group) để khách in không mất cột. Cần Lead duyệt trước khi đưa vào `tools/excel_case_export.py`.
2. **veryHidden -> hidden**: LibreOffice hạ `__map`/`__lists` về `hidden` khi mở/lưu lại (đã adjudicate ở lane Calc round-trip, `tools/test_excel_calc_roundtrip.py`) — checksum + presence vẫn khớp nên tamper-check KHÔNG yếu đi; đề xuất audit/check nào yêu cầu veryHidden trên file khách nạp lại hãy hạ thành CẢNH BÁO.

## NOT RUN


