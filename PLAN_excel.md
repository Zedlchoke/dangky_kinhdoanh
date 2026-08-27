# PLAN_excel — phác thảo tính năng Excel (DRAFT, chưa thuộc release hiện tại)

> **Trạng thái:** DRAFT do yêu cầu owner ngày 2026-08-27. Tài liệu này KHÔNG mở
> scope làm việc; `PLAN.md` mục 2 vẫn coi Excel ngoài phạm vi release hiện tại.
> **Mốc xem xét bắt buộc:** sau khi chạy hết **P4** (hoàn tất Wave E — R3 domain
> rollout phần DECIDED và Wave F — R4 E2E/a11y/resilience), Lead đánh giá lại tính
> khả thi trên nền kiến trúc đã ổn định và báo cáo cho owner quyết định mở/đóng.

## 1. Vì sao phải đợi tới sau P4

Excel chạm trực tiếp vào hai lớp đang còn biến động trước P4:

1. **Schema draft + registry section** (P2/P3): mọi mapping Excel↔app phải bám
   `data-key`/`semantic_key` canonical; vocabulary N1 và các section legal-blocked
   chưa chốt thì mapping sẽ phải viết lại.
2. **Pipeline xuất** (bridge export + recompute totals): mọi đường xuất dữ liệu
   phải đi qua cùng một gate chặn blocking errors — Excel không được là "cửa sau"
   bỏ qua validation.

## 2. Ba hướng khả năng (owner chọn khi mở — KHÔNG làm cả ba cùng lúc)

| Hướng | Mô tả | Người hưởng chính |
|---|---|---|
| **E-A Xuất hồ sơ → Excel** | Một hồ sơ (case) đã khai → 1 file .xlsx: mỗi form 1 sheet, ô khớp vị trí như bản giấy, bảng lặp mỗi dòng 1 hàng | Đối chiếu/lưu kho nội bộ |
| **E-B Nhập hàng loạt Excel → nhiều hồ sơ** | File mẫu cố định nhiều cột → sinh N draft JSON (validate từng hồ sơ, báo lỗi theo dòng) | Nhập liệu số lượng lớn |
| **E-C Bảng kê quản trị** | VSIC, chỉ tiêu thuế, danh mục tài liệu… đọc từ .xlsx thay vì JSON khi owner cập nhật | Người giữ nội dung |

Mặc định đề xuất: **E-A trước** (ít rủi ro, tái dùng toàn bộ export gate), sau đó
E-B nếu có nhu cầu thật, E-C chỉ khi owner muốn tự维护 danh mục.

## 3. Nền kỹ thuật có sẵn (điểm tựa khi triển khai)

- Draft JSON v2 (`{values, checks, loops}` + `_row_id`) là nguồn chân lý duy nhất —
  Excel chỉ là **lớp chuyển đổi qua lại**, không phải nơi lưu thứ hai.
- `form_maps` + `section_specs` + registry runtime đã mô tả đủ cấu trúc từng mẫu →
  sinh/bản đồ ô Excel có thể generate, không vẽ tay.
- Validation tập trung FormDomain: xuất/nhập Excel phải chạy cùng validator
  (blocking chặn, warning hiển thị) — không viết validator song song.
- Engine DOCX render tách biệt → Excel engine là module mới song song, không đụng
  đường DOCX hiện hành.

## 4. Điều kiện tiên quyết khi mở (checklist gate riêng của Excel)

1. P4 đóng; draft schema + canonical keys ổn định (không còn "vocabulary chờ chốt").
2. Owner cung cấp **file Excel mẫu chuẩn** theo hình dạng mong muốn (hoặc duyệt
   mẫu Lead đề xuất) — không tự chế layout.
3. Quyết định thư viện: `openpyxl` (đọc/ghi .xlsx thuần, không cần Excel cài máy)
   — chốt trong requirements + pin version.
4. Contract test: round-trip (draft → xlsx → draft) giữ nguyên 100% giá trị; file
   hỏng/khung cột sai → fail-loud có mã lỗi riêng, không "đoán mò" ô.
5. Windows packaging (R6) không bị phá: thư viện phải đóng gói được không cần
   Excel cài trên máy sạch.

## 5. Rủi ro chính

| Rủi ro | Giảm thiểu |
|---|---|
| Mapping trôi khi schema đổi (cùng bài học zip-timestamp/anchor drift) | Sinh mapping TỪ form_maps/registry, cấm hard-code ô; test round-trip chặn mọi đợt regen |
| Hai nguồn số liệu (Excel cũ vs draft mới) | Excel là xuất/nhập ONE-SHOT; không đồng bộ hai chiều nền tảng |
| Công thức tính trong Excel bị coi là dữ liệu | Chỉ ghi giá trị kết quả; công thức output-only vẫn do app recompute |
| Phạm vi pháp lý trôi (bản mẫu giấy đổi) | Excel phải regen cùng đợt template — thêm vào allowlist + idempotency |

## 6. Câu hỏi owner cần trả khi MỞ (đóng gói sẵn để trả lời nhanh)

- E1: Chọn hướng nào trước (E-A/E-B/E-C)?
- E2: Phạm vi mẫu: mọi 87 form hay nhóm thủ tục nào trước?
- E3: File Excel chuẩn do ai thiết kế (owner cung cấp / Lead đề xuất rồi duyệt)?
- E4: Cần bảo mật gì (mở bằng, chỉ đọc, dấu vết)?
- E5: Có cần xuất ngược từ app sang Excel **tự động** mỗi lần lưu, hay chỉ bấm
  lệnh xuất thủ công?
