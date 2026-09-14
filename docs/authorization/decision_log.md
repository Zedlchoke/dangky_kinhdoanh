# Decision log — module hồ sơ ủy quyền dịch vụ ĐKKD

> Ghi nhận quyết định owner từ phiên 2026-09-14. Wave R khởi chạy sau khi owner xác nhận "okay. Dứt".

## 2026-09-14 — Owner decisions (CHỐT)

| ID | Câu hỏi | Quyết định |
|---|---|---|
| D-AUTH-01 | Template Word | **Không tự viết mẫu.** Rà soát luật, tìm biểu mẫu ủy quyền chính thống/tham chiếu; app chỉ điền dữ liệu vào mẫu đã được pháp lý xác nhận. |
| D-AUTH-02 | Kho dữ liệu | **SQLite local** trong thư mục dữ liệu người dùng (`%APPDATA%\DangKyKinhDoanh` / `~/Library/Application Support/DangKyKinhDoanh`). Không cloud, không server. |
| D-AUTH-03 | Nhiều máy | Mỗi máy = kho riêng, **profile trống khi cài mới**. Có **export/import backup** (file `.zip`) để chuyển profile sang máy khác. |
| D-AUTH-04 | Bên được ủy quyền | **Cá nhân** (nhân viên dịch vụ, ví dụ Minh Long). Không triển khai luồng ủy quyền cho tổ chức/bưu chính ở giai đoạn 1. |
| D-AUTH-05 | Ký | Hỗ trợ **ký tay** (DOCX/PDF in) và **ký số** (chuẩn bị văn bản điện tử; tích hợp certificate/USB token = phase sau). |
| D-AUTH-06 | Scan CCCD | **Không lưu** bản scan trong kho. Chỉ lưu metadata (số CCCD, ngày cấp, nơi cấp…). |
| D-AUTH-07 | Đổi CCCD profile | **Draft/nháp cập nhật** theo profile mới. File đã sinh (`ready`+) giữ snapshot + hash; không tự sửa văn bản đã phát hành. |
| D-AUTH-08 | Case → mẫu | **Mỗi thủ tục (case) có bộ mẫu ủy quyền riêng.** Chọn case → mẫu tự gắn; chọn profile → tự điền đầy đủ. |
| D-AUTH-09 | Phạm vi module | Chỉ **ủy quyền thực hiện thủ tục ĐKKD/HKD cho đơn vị dịch vụ**. Không gộp "đại diện theo ủy quyền" nội bộ tờ khai PLI/PLII. |

## Legal gate

| Trạng thái | Điều kiện |
|---|---|
| `LEGAL_GATE=CONDITIONAL` | Wave R hoàn tất 2026-09-14. TT 68 **không** có mẫu ủy quyền riêng; catalog dùng **mẫu tham chiếu theo Điều 12/93 NĐ 168** + owner duyệt 1–2 mẫu pilot trước code I3/I4. |
| Chuyển `approved` | Sau owner xem `form_legal_matrix.md` và chấp nhận ít nhất mẫu `AUTH-UQ-DN-01` + `AUTH-UQ-HKD-01`. |

## 2026-09-14 — Owner duyệt bố cục mẫu pilot

| Template | Trạng thái |
|---|---|
| `AUTH-UQ-DN-01` | `layout_approved` — owner chỉnh sửa bố cục trong `app/templates/authorization/` |
| `AUTH-UQ-HKD-01` | `layout_approved` — owner chỉnh sửa bố cục |
| Placeholder | 19 tag (DN) / 18 tag (HKD) — khớp `build_render_payload()`; kiểm tra `tools/authorization_template_contract.py` |
| Script build | `build_authorization_templates.py` **không ghi đè** mẫu đã có (cần `--force` để tạo lại) |

`LEGAL_GATE` vẫn `CONDITIONAL` cho nội dung pháp lý văn bản; bố cục và placeholder đã khóa cho I4.

## 2026-09-14 — Wave I1–I4 hoàn tất (kỹ thuật)

| Hạng mục | Trạng thái |
|---|---|
| `tools/authorization_store.py` | ✓ SQLite + migration v1 |
| `app/data/authorization/catalog.json` | ✓ 26 case → template |
| Bridge API (`app_web/main.py`) | ✓ profile + draft + generate + backup |
| UI panel (`authorization-panel.js`) | ✓ |
| Template DOCX + render | ✓ `authorization_render.py` |
| Tests | ✓ `test_authorization_store` + `test_authorization_render` |

## Bước tiếp theo

1. Wave **I5**: sheet `AUTH_*` trong workbook case-level (export/import).
2. Ký số USB token (phase sau).
3. Owner rà nội dung pháp lý văn bản trước khi chuyển `LEGAL_GATE=approved`.
