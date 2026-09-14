# Form / legal matrix — case × mẫu ủy quyền dịch vụ

> Wave R2 — 2026-09-14. Ma trận cho **ủy quyền cá nhân nộp hồ sơ** (Điều 12/93 NĐ 168).  
> Mẫu không có số trong TT 68 — cột `template_id` là ID nội bộ app, nội dung bám Điều 12/93 + mẫu tham chiếu owner duyệt.

## 1. Catalog mẫu (template_id)

| template_id | Tên hiển thị | Cơ sở pháp lý | Người ký (bên A) | Công chứng |
|---|---|---|---|---|
| `AUTH-UQ-DN-01` | Giấy ủy quyền thực hiện thủ tục đăng ký doanh nghiệp (cá nhân) | Điều 12 k1 NĐ 168 | Người có thẩm quyền ký Giấy đề nghị (thường NDĐPL) | Không |
| `AUTH-UQ-HKD-01` | Giấy ủy quyền thực hiện thủ tục đăng ký hộ kinh doanh (cá nhân) | Điều 93 k1 NĐ 168 | Chủ hộ kinh doanh | Không |
| `AUTH-CHECKLIST-01` | Phiếu kiểm kê hồ sơ ủy quyền (nội bộ dịch vụ) | Quy trình nội bộ | Không gửi cơ quan | — |
| `AUTH-COVER-01` | Trang bìa / hướng dẫn ký (nội bộ) | Quy trình nội bộ | — | — |

**Không dùng trong giai đoạn 1:** `AUTH-UQ-ORG-*` (tổ chức), `AUTH-HGD-*` (hộ gia đình nội bộ HKD — công chứng bắt buộc).

### Biến thể nội dung theo case (trong cùng template_id)

Mỗi case gắn `scope_text` — đoạn "phạm vi ủy quyền" điền vào mẫu:

| Nhóm case | `scope_text` (tóm tắt) |
|---|---|
| Thành lập DN | thành lập doanh nghiệp [loại hình], nộp hồ sơ, bổ sung, nhận kết quả |
| Thay đổi ĐKDN | thay đổi nội dung đăng ký doanh nghiệp: [mô tả case], nộp hồ sơ, bổ sung, nhận kết quả |
| HKD | đăng ký / thay đổi / tạm ngừng / chấm dứt hộ kinh doanh: [mô tả case] |
| Chi nhánh/VPĐĐ/ĐDKD | đăng ký / thay đổi / chấm dứt hoạt động chi nhánh, VPĐĐ, địa điểm KD |
| Giải thể | thủ tục giải thể / hủy nghị quyết giải thể doanh nghiệp |
| Công bố/cấp lại | công bố nội dung ĐKDN; cấp lại/cấp đổi GCN; cập nhật thông tin |

## 2. Ma trận 27 case thật (loại pilot)

| case_id | Tên thủ tục | Mẫu ủy quyền | Bên ủy quyền (từ draft) | Ghi chú |
|---|---|---|---|---|
| `thanh_lap_dntn` | Thành lập DNTN | AUTH-UQ-DN-01 | Chủ DN (`chu_dn.*` / người ký đề nghị) | Chủ = cá nhân |
| `thanh_lap_tnhh_1tv` | Thành lập TNHH 1TV | AUTH-UQ-DN-01 | NDĐPL hoặc chủ sở hữu tùy cấu trúc | `ndd.*` |
| `thanh_lap_tnhh_2tv` | Thành lập TNHH 2TV+ | AUTH-UQ-DN-01 | NDĐPL / Chủ tịch HĐTV | `ndd.*` |
| `thanh_lap_ctcp` | Thành lập CTCP | AUTH-UQ-DN-01 | NDĐPL / Chủ tịch HĐQT | `ndd.*` |
| `thanh_lap_hop_danh` | Thành lập hợp danh | AUTH-UQ-DN-01 | NDĐPL / Chủ tịch HĐTV | `ndd.*` |
| `dang_ky_ho_kinh_doanh_lan_dau` | Đăng ký HKD lần đầu | AUTH-UQ-HKD-01 | Chủ hộ | `chu_ho.*` |
| `chuyen_doi_hkd_sang_dn` | Chuyển đổi HKD → DN | AUTH-UQ-DN-01 | Chủ hộ (ủy quyền trước chuyển đổi) | Phạm vi: chuyển đổi + thành lập DN |
| `thay_doi_ten_va_tru_so` | Đổi tên / trụ sở | AUTH-UQ-DN-01 | NDĐPL | Mẫu 12 |
| `thay_doi_nganh_nghe` | Đổi ngành nghề | AUTH-UQ-DN-01 | NDĐPL | Thông báo |
| `thay_doi_von_dieu_le` | Đổi vốn điều lệ | AUTH-UQ-DN-01 | NDĐPL | |
| `thay_doi_nguoi_dai_dien_pl` | Đổi NDĐPL | AUTH-UQ-DN-01 | Người ký theo Đ43 (thường CT HĐTV/HĐQT) | Ai ký đề nghị ≠ NDĐPL mới |
| `thay_doi_chusohuu_chudn` | Đổi chủ sở hữu/chủ DN | AUTH-UQ-DN-01 | Chủ mới hoặc NDĐPL chủ mới | |
| `thay_doi_noi_dung_dang_ky_hkd` | Thay đổi nội dung ĐK HKD | AUTH-UQ-HKD-01 | Chủ hộ | |
| `lap_chi_nhanh_vpdd` | Lập chi nhánh/VPĐĐ | AUTH-UQ-DN-01 | NDĐPL | |
| `lap_dia_diem_kinh_doanh` | Lập địa điểm KD | AUTH-UQ-DN-01 | NDĐPL | |
| `thay_doi_noi_dung_hoat_dong_cn_vpdd` | Đổi nội dung CN/VPĐĐ/ĐDKD | AUTH-UQ-DN-01 | NDĐPL | |
| `cham_dut_hoat_dong_cn_vpdd_ddkd` | Chấm dứt CN/VPĐĐ/ĐDKD | AUTH-UQ-DN-01 | NDĐPL | |
| `tam_ngung_tiep_tuc_kinh_doanh_dn` | Tạm ngừng/tiếp tục KD DN | AUTH-UQ-DN-01 | NDĐPL | |
| `tam_ngung_tiep_tuc_kinh_doanh_hkd` | Tạm ngừng/tiếp tục HKD | AUTH-UQ-HKD-01 | Chủ hộ | |
| `cham_dut_hoat_dong_hkd` | Chấm dứt HKD | AUTH-UQ-HKD-01 | Chủ hộ | |
| `giai_the_doanh_nghiep` | Giải thể DN | AUTH-UQ-DN-01 | NDĐPL / người ký theo Đ64 | 2 giai đoạn — scope ghi rõ |
| `huy_quyet_dinh_giai_the` | Hủy NQ giải thể | AUTH-UQ-DN-01 | NDĐPL | |
| `cong_bo_noi_dung_dkdn` | Công bố nội dung ĐKDN | AUTH-UQ-DN-01 | NDĐPL | |
| `cung_cap_thong_tin_dkdn` | Đề nghị cung cấp thông tin | — | — | **Không áp dụng** — không phải ủy quyền nộp hồ sơ dịch vụ |
| `cap_lai_gcdn_va_giay_pham_dkkd` | Cấp lại GCN | AUTH-UQ-DN-01 | NDĐPL | |
| `cap_doi_gcdkkd_sang_gcdn` | Cấp đổi GCN | AUTH-UQ-DN-01 | NDĐPL | |
| `bo_sung_cap_nhat_thong_tin_dkdn` | Bổ sung/cập nhật thông tin | AUTH-UQ-DN-01 | NDĐPL | |
| `pilot_ui_m02_m06` | (PILOT UI) | — | — | **Loại** |

Mỗi dòng có thủ tục còn kèm: `AUTH-CHECKLIST-01` + tùy chọn `AUTH-COVER-01`.

## 3. Field map — profile + draft → mẫu

### 3.1 Profile người làm thủ tục (`agent.*`)

| Placeholder mẫu | Trường profile | Bắt buộc |
|---|---|---|
| `{agent.ho_ten}` | `ho_ten` | ✓ |
| `{agent.ngay_sinh}` | `ngay_sinh` | ✓ |
| `{agent.so_cccd}` | `so_cccd` | ✓ |
| `{agent.ngay_cap}` | `ngay_cap` | ✓ |
| `{agent.noi_cap}` | `noi_cap` | ✓ |
| `{agent.dia_chi}` | `dia_chi_lien_he` | ✓ |
| `{agent.dien_thoai}` | `dien_thoai` | ✓ |
| `{agent.email}` | `email` | Khuyến nghị |

### 3.2 Bên ủy quyền — doanh nghiệp (`dn.*` + `ndd.*`)

| Placeholder | Key draft (ưu tiên) | Form nguồn |
|---|---|---|
| `{uy_quyen.ten_chu_the}` | `dn.ten_tieng_viet` | PLI_M01–M05, M12… |
| `{uy_quyen.ma_so}` | `dn.ma_so_dn` | Các mẫu DN đã thành lập |
| `{uy_quyen.dia_chi}` | `dn.dia_chi_tru_so` | |
| `{uy_quyen.nguoi_ky}` | `ndd.ho_ten` | |
| `{uy_quyen.chuc_danh}` | `ndd.chuc_vu` | |
| `{uy_quyen.so_cccd}` | `ndd.so_cccd` | Khi cần nhận diện người ký |

### 3.3 Bên ủy quyền — hộ kinh doanh (`chu_ho.*`)

| Placeholder | Key draft | Ghi chú |
|---|---|---|
| `{uy_quyen.ten_chu_the}` | `hkd.ten_ho` / tên HKD trong PLII | Cần inventory chính xác từ blocks |
| `{uy_quyen.nguoi_ky}` | `chu_ho.ho_ten` | Chủ hộ |
| `{uy_quyen.so_cccd}` | `chu_ho.so_cccd` | |

### 3.4 Metadata thủ tục (từ case + UI)

| Placeholder | Nguồn |
|---|---|
| `{case.ten}` | `use_cases.json` → `ten` |
| `{case.scope}` | Sinh từ nhóm + `mo_ta` + form đang chọn |
| `{co_quan.tiep_nhan}` | User chọn / mặc định theo case (cấp tỉnh / cấp xã) |
| `{uy_quyen.ngay_lap}` | Ngày sinh hồ sơ |
| `{uy_quyen.thoi_han}` | User nhập (ngày hết hạn) |

## 4. Luồng UI (theo owner)

```
Chọn case (sidebar)
    → catalog lọc template_id + scope_text
Chọn profile (panel phải)
    → validate CCCD đủ
Ghép draft hiện tại
    → map dn.* / ndd.* / chu_ho.*
Preview → Sinh DOCX/PDF/ZIP
```

## 5. Điều kiện legal gate

| Gate | PASS khi |
|---|---|
| R2 matrix | 27 case có template hoặc lý do loại rõ |
| Owner pilot | Chấp nhận nội dung `AUTH-UQ-DN-01` + `AUTH-UQ-HKD-01` (file Word tham chiếu đính kèm sau) |
| Không BLOCKER | Không case active thiếu bên ủy quyền trong draft mà vẫn cho sinh im lặng |

**LEGAL_GATE hiện tại:** `CONDITIONAL` — chờ owner duyệt 2 mẫu pilot.
