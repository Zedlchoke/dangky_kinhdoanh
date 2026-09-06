# HEADER-NAME CENSUS — F0L (post-migration current-law, READ-ONLY)

- Generated: 2026-09-06  |  base HEAD: `e268038`
- Phạm vi: vùng band (từ đầu tài liệu tới tiêu đề biểu mẫu) của 87 template `app/templates/<fid>.docx`. Phân loại toàn corpus + no-signature verdicts: xem `header_name_census_2026-09-05.*` (vẫn còn hiệu lực).
- Mục đích: rebaseline census sau migrate L-2026 (TT 121/2026/TT-BTC) — đối chiếu.allowlist HEADER_BAND_FORMS (23 mẫu) + tools/header_name_binding.json.

## 1. Tóm tắt vùng band

| Chỉ số | Giá trị |
|---|---|
| Band-region occurrences | 35 |
| fillable-header-slot | **23** (2026-09-05: 22; +PLI_M12) |
| — đã bind (header_name_binding.json) | 21 |
| — blocked_owner | 2 (`PLI_M33`, `PLII_M06`) |
| — unadjudicated | 0 (phải = 0) |
| legal-title/subtitle trong vùng band | 12 |

## 2. Delta so với census 2026-09-05

| Mẫu | Trước | Sau | Evidence |
|---|---|---|---|
| PLI_M12 | needs-owner (premise cũ: nguồn mất ô tên + TT 121 đã thay mẫu) | **fillable-header-slot, BOUND `dn.ten_tieng_viet`** | template M12 2026 (ảnh p50) có band 'TÊN DOANH NGHIỆP' ở trang đầu; nguồn migrate có khối 4 paragraph header chuẩn; thân có `{dn.ten_tieng_viet}` (form_maps fields[6]) |
| Các mẫu migrate còn lại (PLII_M01, PLI_M02–M05, PLI_M27, PLI_M30) | — | **không phát sinh band mới** | census raw: không occurrence loại fillable-header-slot mới ngoài M12; PLI_M27/M30 giữ band đã allowlist từ 2026-09-05 |

## 3. Bảng 23 fillable-header-slot

| Form | Label | Vị trí | Adjudication | Key |
|---|---|---|---|---|
| PLII_M02 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | bound | hkd_ten_tieng_viet_2 |
| PLII_M03 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | bound | hkd_ten_tieng_viet_2 |
| PLII_M04 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | bound | hkd_ten_tieng_viet_2 |
| PLII_M05 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | bound | hkd_ten_tieng_viet_2 |
| PLII_M06 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | blocked_owner | blocked: band fillable nhưng thân không có input tên hộ — cần owner c… |
| PLI_M12 | TÊN DOANH NGHIỆP | `para 0` | bound | dn.ten_tieng_viet |
| PLI_M13 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M14 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M15 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M17 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M18 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M19 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M21 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M23 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M25 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M26 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M27 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M28 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M29 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M30 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M31 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M32 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | bound | dn.ten_tieng_viet |
| PLI_M33 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | blocked_owner | blocked: band fillable nhưng thân CHỈ có chu_hkd.ho_ten (tên người nộ… |

## 4. Dữ liệu thô từng form

Xem `header_name_census_f0l_2026-09-06.json` — `forms[<fid>]`: band_occurrences (đã phân loại), band_end_idx, title_idx, quoc_hieu_idx, no_band.

---
Sinh tự động bởi `tools/census/header_name_census_f0l.py` [integ(F0L)]; raw scan: `tools/census/header_name_census.py`.