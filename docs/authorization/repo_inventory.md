# Repo inventory — sẵn sàng cho module ủy quyền

> Wave R3 — 2026-09-14. Kiểm kê hiện trạng code; không kết luận pháp lý.

## 1. Tóm tắt

| Hạng mục | Hiện trạng | Cần làm (Wave I) |
|---|---|---|
| Module `authorization` | **Chưa có** | I1–I6 |
| `docs/authorization/` | **Có** (Wave R) | Duy trì |
| Profile người làm thủ tục | **Chưa có** | SQLite `authorized_agent_profile` |
| UI panel phải | `#rightbar` — hướng dẫn + lỗi | Thêm section profile + ủy quyền |
| 28 case | `app/data/use_cases.json` | Catalog `case_id → templates` |
| Draft JSON v2 | `load_draft` / `save_draft` | Giữ; link `authorization_id` tùy chọn |
| DOCX engine | `tools/docx_render.py` | Template `app/templates/authorization/` |
| Excel case | `tools/excel_case_export.py` | Sheet `AUTH_*` (phase sau I5) |
| PII trong git | `profiles/` gitignored | SQLite user data gitignored |

## 2. Case inventory (27 thật + 1 pilot)

Nguồn: `app/data/use_cases.json`.

| Nhóm | Số case | case_id |
|---|---|---|
| Thành lập DN | 5 | `thanh_lap_*` |
| HKD | 1 + 4 thay đổi/chấm dứt | `dang_ky_ho_kinh_doanh_*`, `thay_doi_noi_dung_dang_ky_hkd`, `tam_ngung_*_hkd`, `cham_dut_hoat_dong_hkd` |
| Chuyển đổi | 1 | `chuyen_doi_hkd_sang_dn` |
| Thay đổi DN | 5 | `thay_doi_*` |
| Chi nhánh/ĐDKD | 4 | `lap_*`, `thay_doi_noi_dung_hoat_dong_*`, `cham_dut_hoat_dong_*` |
| Tạm ngừng DN | 1 | `tam_ngung_tiep_tuc_kinh_doanh_dn` |
| Giải thể | 2 | `giai_the_*`, `huy_quyet_dinh_*` |
| Công bố/cấp lại | 4 | `cong_bo_*`, `cung_cap_*`, `cap_*`, `bo_sung_*` |
| Pilot | 1 | `pilot_ui_m02_m06` — **không ship** |

## 3. Field map sẵn có trong `form_maps.json`

### Doanh nghiệp (dùng cho bên ủy quyền DN)

| Key | Mô tả | Độ phủ |
|---|---|---|
| `dn.ten_tieng_viet` | Tên DN | Rộng (hầu hết PLI) |
| `dn.ma_so_dn` | Mã số DN | Rộng |
| `dn.dia_chi_tru_so` | Trụ sở | Nhiều mẫu |
| `ndd.ho_ten` | NDĐPL | Rộng |
| `ndd.chuc_vu` | Chức danh | Rộng |
| `ndd.so_cccd` | CCCD NDĐPL | Rộng |
| `ndd.ngay_cap` / `ndd.noi_cap` | Giấy tờ NDĐPL | Một số mẫu |
| `ndd.dien_thoai` / `ndd.email` | Liên hệ | Một số mẫu |

### Hộ kinh doanh

Cần inventory chi tiết `chu_ho.*` / `hkd.*` từ blocks PLII — **chưa liệt kê đầy đủ trong Wave R**; lane I3 phải quét `app/data/blocks/PLII_M*.json` trước render HKD.

### Tách biệt — KHÔNG dùng cho module dịch vụ

| Key pattern | Ý nghĩa |
|---|---|
| `ds_ndd_uy_quyen_*` | Đại diện theo ủy quyền **trong tờ khai** (vd. PLI_M15) |
| `ds_nddpl_uy_quyen_*` | Ủy quyền vốn/thành viên — nội bộ DN |

## 4. UI / Bridge hiện có

### Layout (`app_web/ui/index.html`)

```
#sidebar     — case, form list, export
#scroller    — tờ khai
#rightbar    — case-info + validation errors  ← mở rộng panel ủy quyền
```

### Bridge API (`app_web/main.py`) — pattern tái sử dụng

| API hiện có | Gợi ý tương đương authorization |
|---|---|
| `load_draft` / `save_draft` | Draft hồ sơ ĐKKD (giữ) |
| `export` | `generate_authorization_case` |
| `export_case_workbook` | Sau: `export_authorization_excel` |
| `import_case_workbook` | Candidate/confirm pattern |
| `open_dir` | Mở thư mục ZIP đã sinh |

### Lưu trữ hiện tại

| Cơ chế | Vai trò | Module ủy quyền |
|---|---|---|
| `localStorage` (`hoso_draft_autosave`) | Autosave tạm UI | **Không** dùng cho profile |
| File JSON draft (dialog) | Hồ sơ ĐKKD | Giữ |
| SQLite | Chưa có | **Mới** — profile + authorization_case |

### Đường dẫn dữ liệu người dùng (đề xuất I1)

```
Windows:  %APPDATA%\DangKyKinhDoanh\
  profiles.db
  authorization\          ← DOCX/PDF/ZIP đã sinh
  backups\                ← export zip do user tạo

macOS:    ~/Library/Application Support/DangKyKinhDoanh/
```

Handoff kit Windows/macOS (`tools/windows_handoff/`, `tools/macos_handoff/`) đã có pattern `%APPDATA%` — align khi bundle.

## 5. Generator / template

| Thành phần | Path | Ghi chú |
|---|---|---|
| Template ĐKKD | `app/templates/PLI_*`, `PLII_*` | 87 form — không sửa cho auth |
| Blocks | `app/data/blocks/` | Generated |
| DOCX render | `tools/docx_render.py` | Dùng lại engine |
| Template ủy quyền | `app/templates/authorization/` | **Chưa có** — I3 sau legal pilot |

## 6. Thiếu / chưa có (không blocker Wave R)

1. `app/data/authorization/catalog.json` — case → template + scope.
2. `tools/authorization_store.py` — SQLite CRUD + migration.
3. `tools/authorization_render.py` — fill template + ZIP/MANIFEST.
4. Test suite authorization (round-trip profile backup, render golden).
5. Pin keys `chu_ho.*` cho PLII trong field map HKD.

## 7. Rủi ro kỹ thuật

| Rủi ro | Mức | Giảm |
|---|---|---|
| Bên ủy quyền thiếu field khi draft trống | Cao | Validation trước preview; checklist "còn thiếu" |
| Nhầm module với loop ủy quyền PLI | Trung bình | Tách namespace `agent.*` vs `ds_ndd_uy_quyen_*` |
| PyInstaller bundle SQLite path | Trung bình | Probe user dir giống `generated_ho_so` |
| Ký số | Thấp (giai đoạn 1) | Chỉ DOCX + checklist |

## 8. File ownership dự kiến (Wave I)

| Agent | Files |
|---|---|
| I1 | `tools/authorization_store.py`, `app/data/authorization/schema.sql` |
| I2 | `app_web/ui/index.html`, `app_web/ui/app.js`, `app_web/ui/authorization-panel.js` (mới) |
| I3 | `app/data/authorization/catalog.json`, `app/templates/authorization/*.docx` |
| I4 | `tools/authorization_render.py`, `app_web/main.py` (bridge) |
| I5 | `tools/excel_case_export.py` (sheet AUTH_*) |
