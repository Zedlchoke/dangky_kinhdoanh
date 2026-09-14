# Schema contract — module ủy quyền (v1)

> Wave I1 — 2026-09-14. SQLite local, không cloud.

## Vị trí dữ liệu

| OS | Đường dẫn |
|---|---|
| Windows | `%APPDATA%\DangKyKinhDoanh\profiles.db` |
| macOS | `~/Library/Application Support/DangKyKinhDoanh/profiles.db` |
| Linux | `~/.local/share/DangKyKinhDoanh/profiles.db` |

Override test: biến môi trường `DKKD_AUTH_DATA_DIR`.

## Bảng

### `authorized_agent_profiles`

Profile nhân viên dịch vụ (bên được ủy quyền — cá nhân).

| Cột | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `agent_id` | TEXT PK | ✓ | UUID |
| `ho_ten` | TEXT | ✓ | |
| `so_cccd` | TEXT | ✓ | 9–12 chữ số |
| `ngay_sinh`, `gioi_tinh`, `quoc_tich` | TEXT | | |
| `ngay_cap`, `noi_cap` | TEXT | | |
| `dia_chi_lien_he`, `dien_thoai`, `email` | TEXT | | Không lưu scan |
| `chuc_danh`, `don_vi_dich_vu` | TEXT | | |
| `trang_thai` | TEXT | ✓ | `active` \| `locked` \| `expired` |
| `ghi_chu` | TEXT | | |
| `created_at`, `updated_at` | TEXT ISO UTC | ✓ | |

### `authorization_cases`

Nháp / hồ sơ ủy quyền gắn `case_id` + `agent_id`.

- `status = draft`: đọc profile **live** (cập nhật khi đổi CCCD).
- `status >= ready`: `snapshot_json` bất biến (Wave I4).

### `authorization_audit`

Sự kiện không PII — `detail` dùng `mask_pii()`.

## Backup format (`.zip`)

```
profiles.db
authorization_backup_manifest.json   # schema_version, exported_at, db_sha256
```

Import: sao lưu DB cũ vào `backups/profiles_pre_restore_*.db` trước khi thay.

## API Python (`tools/authorization_store.py`)

| Hàm | Mô tả |
|---|---|
| `list_agent_profiles(filter)` | Danh sách + tìm kiếm |
| `save_agent_profile(payload)` | Tạo/cập nhật |
| `lock_agent_profile(agent_id)` | Khóa profile |
| `templates_for_case(case_id)` | Catalog mẫu theo thủ tục |
| `create_authorization_draft(...)` | Nháp ủy quyền |
| `get_authorization_draft(id)` | Merge profile live nếu draft |
| `export_backup(path)` / `import_backup(path)` | Chuyển máy |
| `store_info()` | Empty state UI |
| `generate_package(...)` | `tools/authorization_render` — DOCX/ZIP + snapshot |

## Bridge (`window.pywebview.api`)

| Method | Bridge |
|---|---|
| `list_authorized_agent_profiles` | ✓ |
| `save_authorized_agent_profile` | ✓ |
| `lock_authorized_agent_profile` | ✓ |
| `get_authorization_templates` | ✓ (theo case_id) |
| `create_authorization_draft` | ✓ |
| `get_authorization_draft` | ✓ |
| `generate_authorization_package` | ✓ |
| `get_authorization_store_info` | ✓ |
| `export_authorization_backup` | ✓ |
| `import_authorization_backup` | ✓ |

## Template placeholder (flat keys)

Mẫu `AUTH-UQ-DN-01` / `AUTH-UQ-HKD-01` dùng `{key}` flat — danh sách đầy đủ trong
`tools/authorization_template_contract.py` (`RENDER_PAYLOAD_KEYS`). Owner chỉnh bố cục
Word được giữ; script `build_authorization_templates.py` không ghi đè trừ khi `--force`.

## Catalog

`app/data/authorization/catalog.json` — map `case_id` → `template_ids` + `scope_key`.
