# Audit bố cục trực quan — Excel case-level (2026-09-10)

- HEAD: `47c1805` — tool: `tools/excel_case_visual.py`
- LibreOffice: `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77` — render: pymupdf 1.28.2 (PNG ~150dpi)
- Meta xuất: `{"today": "10/09/2026", "exported_at": "10/09/2026 20:31"}`
- Bằng chứng: `generated_ho_so/_visual_layout/excel_case_20260910/<caseId>/` (`page-NN.png`, `contact-sheet.png`, `*.pdf`, `*.xlsx`)
- Phạm vi: case READY đọc từ đĩa lúc chạy. Case PENDING (chưa có câu hỏi) = NOT RUN, chờ lane content bật.

## Bảng tổng hợp

| case | sheet | trang PDF | cắt cột / clip | tràn trang | font tiếng Việt | số hàng bảng |
|---|---|---|---|---|---|---|
| bo_sung_cap_nhat_thong_tin_dkdn | 5 | 12 | PASS | WARN (spill 8 trang; trang đầu: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| cap_doi_gcdkkd_sang_gcdn | 5 | 10 | PASS | WARN (spill 6 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 3, "01_Giấy đề nghị cấp đổi sang Gi": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| cap_lai_gcdn_va_giay_pham_dkkd | 5 | 12 | PASS | WARN (spill 8 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 3, "01_Giấy đề nghị cấp lại Giấy ch": null, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| cham_dut_hoat_dong_cn_vpdd_ddkd | 5 | 10 | PASS | WARN (spill 6 trang; trang đầu: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Thông báo về việc chấm dứt h": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| cham_dut_hoat_dong_hkd | 5 | 8 | PASS | WARN (spill 4 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc chấm dứt h": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| chuyen_doi_hkd_sang_dn | 9 | 89 | PASS | WARN (spill 82 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Giấy đề nghị đăng ký doanh n": null, "03_Giấy đề nghị đăng ký doanh n": null, "04_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| cong_bo_noi_dung_dkdn | 6 | 8 | PASS | WARN (spill 4 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị công bố nội dun": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| cung_cap_thong_tin_dkdn | 6 | 10 | PASS | WARN (spill 6 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị cung cấp thông": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| dang_ky_ho_kinh_doanh_lan_dau | 6 | 11 | PASS | WARN (spill 7 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hộ kinh": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| giai_the_doanh_nghiep | 5 | 8 | PASS | WARN (spill 4 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc giải thể d": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| huy_quyet_dinh_giai_the | 5 | 8 | PASS | WARN (spill 4 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc huỷ bỏ Ngh": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| lap_chi_nhanh_vpdd | 6 | 14 | PASS | WARN (spill 10 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hoạt độ": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| lap_dia_diem_kinh_doanh | 6 | 14 | PASS | WARN (spill 10 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hoạt độ": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| pilot_ui_m02_m06 | 7 | 40 | PASS | WARN (spill 35 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| tam_ngung_tiep_tuc_kinh_doanh_dn | 5 | 10 | PASS | WARN (spill 6 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc tạm ngừng": 4, "Giấy_tờ_cần_gửi": 6}) | WARN | PASS |
| tam_ngung_tiep_tuc_kinh_doanh_hkd | 5 | 8 | PASS | WARN (spill 4 trang; trang đầu: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký tạm ngừ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| thanh_lap_ctcp | 8 | 42 | PASS | WARN (spill 36 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách cổ đông sáng lập c": null, "03_Danh sách cổ đông là nhà đầu": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| thanh_lap_dntn | 6 | 20 | PASS | WARN (spill 16 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| thanh_lap_hop_danh | 7 | 29 | PASS | WARN (spill 24 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| thanh_lap_tnhh_1tv | 6 | 25 | PASS | WARN (spill 21 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| thanh_lap_tnhh_2tv | 7 | 37 | PASS | WARN (spill 32 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| thay_doi_chusohuu_chudn | 7 | 20 | PASS | WARN (spill 15 trang; trang đầu: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": null, "02_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| thay_doi_nganh_nghe | 5 | 12 | PASS | WARN (spill 8 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| thay_doi_nguoi_dai_dien_pl | 6 | 11 | PASS | WARN (spill 7 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 3}) | WARN | PASS |
| thay_doi_noi_dung_dang_ky_hkd | 6 | 13 | PASS | WARN (spill 9 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| thay_doi_noi_dung_hoat_dong_cn_vpdd | 6 | 14 | PASS | WARN (spill 10 trang; trang đầu: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 4}) | WARN | PASS |
| thay_doi_ten_va_tru_so | 5 | 12 | PASS | WARN (spill 8 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |
| thay_doi_von_dieu_le | 5 | 12 | PASS | WARN (spill 8 trang; trang đầu: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}) | WARN | PASS |

Chi tiết `pages_per_sheet` (trang đầu chứa TOÀN VĂN tiêu đề sheet — dò qua text-layer, tham khảo). LƯU Ý: với sheet rộng hơn khổ giấy, tiêu đề hàng 1 có thể bị CẮT tại mép phải trang thật (vd `tam_ngung_tiep_tuc_kinh_doanh_hkd`: tiêu đề guide dừng ở "…hộ kinh doa") — khi đó 'trang đầu' lệch về trang sau; việc cắt tiêu đề này tự nó là phát hiện layout, thuộc WARN tràn trang:

- **bo_sung_cap_nhat_thong_tin_dkdn**: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}
- **cap_doi_gcdkkd_sang_gcdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 3, "01_Giấy đề nghị cấp đổi sang Gi": null, "Giấy_tờ_cần_gửi": 4}
- **cap_lai_gcdn_va_giay_pham_dkkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 3, "01_Giấy đề nghị cấp lại Giấy ch": null, "Giấy_tờ_cần_gửi": 5}
- **cham_dut_hoat_dong_cn_vpdd_ddkd**: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Thông báo về việc chấm dứt h": null, "Giấy_tờ_cần_gửi": 4}
- **cham_dut_hoat_dong_hkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc chấm dứt h": 4, "Giấy_tờ_cần_gửi": 5}
- **chuyen_doi_hkd_sang_dn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Giấy đề nghị đăng ký doanh n": null, "03_Giấy đề nghị đăng ký doanh n": null, "04_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 3}
- **cong_bo_noi_dung_dkdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị công bố nội dun": null, "Giấy_tờ_cần_gửi": 3}
- **cung_cap_thong_tin_dkdn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị cung cấp thông": null, "Giấy_tờ_cần_gửi": 3}
- **dang_ky_ho_kinh_doanh_lan_dau**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hộ kinh": 4, "Giấy_tờ_cần_gửi": 5}
- **giai_the_doanh_nghiep**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc giải thể d": null, "Giấy_tờ_cần_gửi": 4}
- **huy_quyet_dinh_giai_the**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc huỷ bỏ Ngh": null, "Giấy_tờ_cần_gửi": 3}
- **lap_chi_nhanh_vpdd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hoạt độ": null, "Giấy_tờ_cần_gửi": 3}
- **lap_dia_diem_kinh_doanh**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký hoạt độ": null, "Giấy_tờ_cần_gửi": 3}
- **pilot_ui_m02_m06**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}
- **tam_ngung_tiep_tuc_kinh_doanh_dn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Thông báo về việc tạm ngừng": 4, "Giấy_tờ_cần_gửi": 6}
- **tam_ngung_tiep_tuc_kinh_doanh_hkd**: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký tạm ngừ": 4, "Giấy_tờ_cần_gửi": 5}
- **thanh_lap_ctcp**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách cổ đông sáng lập c": null, "03_Danh sách cổ đông là nhà đầu": null, "Giấy_tờ_cần_gửi": 3}
- **thanh_lap_dntn**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 4}
- **thanh_lap_hop_danh**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}
- **thanh_lap_tnhh_1tv**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "Giấy_tờ_cần_gửi": 3}
- **thanh_lap_tnhh_2tv**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký doanh n": null, "02_Danh sách thành viên công ty": null, "Giấy_tờ_cần_gửi": 3}
- **thay_doi_chusohuu_chudn**: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": null, "02_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 4}
- **thay_doi_nganh_nghe**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_nguoi_dai_dien_pl**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 3}
- **thay_doi_noi_dung_dang_ky_hkd**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: {"Hướng_dẫn": 2, "Thông_tin_chung": 3, "01_Giấy đề nghị đăng ký thay đổ": null, "Giấy_tờ_cần_gửi": 4}
- **thay_doi_ten_va_tru_so**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}
- **thay_doi_von_dieu_le**: {"Hướng_dẫn": 0, "Thông_tin_chung": 2, "01_Giấy đề nghị đăng ký thay đổ": 4, "Giấy_tờ_cần_gửi": 5}

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
- **lap_dia_diem_kinh_doanh**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans, IAAAAA+DejaVuSerif-Italic`
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
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thay_doi_ten_va_tru_so**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`
- **thay_doi_von_dieu_le**: `BAAAAA+Caladea-Bold, CAAAAA+LinuxLibertineGB, DAAAAA+Caladea-Italic, EAAAAA+LinuxLibertineGI, FAAAAA+Caladea-Regular, GAAAAA+LinuxLibertineG, HAAAAA+DejaVuSans`

## Độ trung thực text-layer (đối chiếu chuỗi nội dung ô với PDF)

Text-layer được TÁI LẬP từ toạ độ ký tự (LibreOffice xuất glyph dấu tiếng Việt trong các text-run riêng lệch baseline). 4 tầng khớp: nguyên văn / đủ chữ mất dấu / đủ bộ ký tự xen kẽ (wrap, glyph dịch vị) / thiếu ký tự. Lớp PDF dùng font thay thế Calibri (Caladea/Libertine) nên HÌNH DẠNG dấu vẫn cần xem mắt — mã ký tự thì đối chiếu được.

- **bo_sung_cap_nhat_thong_tin_dkdn**: 66/87 nguyên văn, 1 mất dấu (fold-only), 20 xen kẽ (bag-only), 0 thiếu ký tự.
- **cap_doi_gcdkkd_sang_gcdn**: 6/21 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **cap_lai_gcdn_va_giay_pham_dkkd**: 6/21 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **cham_dut_hoat_dong_cn_vpdd_ddkd**: 7/22 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **cham_dut_hoat_dong_hkd**: 13/28 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **chuyen_doi_hkd_sang_dn**: 10/27 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **cong_bo_noi_dung_dkdn**: 7/21 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **cung_cap_thong_tin_dkdn**: 7/21 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **dang_ky_ho_kinh_doanh_lan_dau**: 54/78 nguyên văn, 1 mất dấu (fold-only), 23 xen kẽ (bag-only), 0 thiếu ký tự.
- **giai_the_doanh_nghiep**: 7/23 nguyên văn, 1 mất dấu (fold-only), 15 xen kẽ (bag-only), 0 thiếu ký tự.
- **huy_quyet_dinh_giai_the**: 7/22 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **lap_chi_nhanh_vpdd**: 7/24 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **lap_dia_diem_kinh_doanh**: 7/21 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **pilot_ui_m02_m06**: 8/22 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **tam_ngung_tiep_tuc_kinh_doanh_dn**: 31/52 nguyên văn, 1 mất dấu (fold-only), 20 xen kẽ (bag-only), 0 thiếu ký tự.
- **tam_ngung_tiep_tuc_kinh_doanh_hkd**: 23/37 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_ctcp**: 9/26 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_dntn**: 7/22 nguyên văn, 1 mất dấu (fold-only), 14 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_hop_danh**: 8/24 nguyên văn, 1 mất dấu (fold-only), 15 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_tnhh_1tv**: 7/24 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **thanh_lap_tnhh_2tv**: 8/25 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_chusohuu_chudn**: 8/25 nguyên văn, 1 mất dấu (fold-only), 16 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_nganh_nghe**: 66/88 nguyên văn, 1 mất dấu (fold-only), 21 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_nguoi_dai_dien_pl**: 7/23 nguyên văn, 1 mất dấu (fold-only), 15 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_noi_dung_dang_ky_hkd**: 68/92 nguyên văn, 1 mất dấu (fold-only), 23 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_noi_dung_hoat_dong_cn_vpdd**: 7/21 nguyên văn, 1 mất dấu (fold-only), 13 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_ten_va_tru_so**: 66/89 nguyên văn, 1 mất dấu (fold-only), 22 xen kẽ (bag-only), 0 thiếu ký tự.
- **thay_doi_von_dieu_le**: 66/92 nguyên văn, 1 mất dấu (fold-only), 25 xen kẽ (bag-only), 0 thiếu ký tự.

## Chuỗi THIẾU KÝ TỰ trong text-layer PDF (ứng viên cắt cột/clip thật)

(không có — mọi chuỗi nội dung ô đều đủ ký tự trong PDF)

## Chuỗi ĐỦ CHỮ NHƯNG MẤT DẤU trong text-layer (mã ký tự lệch — artefact font)

**bo_sung_cap_nhat_thong_tin_dkdn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cap_doi_gcdkkd_sang_gcdn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cap_lai_gcdn_va_giay_pham_dkkd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cham_dut_hoat_dong_cn_vpdd_ddkd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cham_dut_hoat_dong_hkd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**chuyen_doi_hkd_sang_dn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cong_bo_noi_dung_dkdn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**cung_cap_thong_tin_dkdn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**dang_ky_ho_kinh_doanh_lan_dau** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**giai_the_doanh_nghiep** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**huy_quyet_dinh_giai_the** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**lap_chi_nhanh_vpdd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**lap_dia_diem_kinh_doanh** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**pilot_ui_m02_m06** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**tam_ngung_tiep_tuc_kinh_doanh_dn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**tam_ngung_tiep_tuc_kinh_doanh_hkd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thanh_lap_ctcp** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thanh_lap_dntn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thanh_lap_hop_danh** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thanh_lap_tnhh_1tv** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thanh_lap_tnhh_2tv** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_chusohuu_chudn** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_nganh_nghe** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_nguoi_dai_dien_pl** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_noi_dung_dang_ky_hkd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_noi_dung_hoat_dong_cn_vpdd** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_ten_va_tru_so** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`

**thay_doi_von_dieu_le** (1):

- `•ÔNỀNVÀNGlàphầnbạnđiền.ÔNỀNXÁMphầnứngdụngtựđiềngiúpbạn,khôngcầnlàmgì.`


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


