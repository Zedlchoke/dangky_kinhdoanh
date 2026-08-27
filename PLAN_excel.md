# PLAN_excel — nhập hồ sơ từ file Excel khách hàng điền (DRAFT, chờ P4)

> **Trạng thái:** DRAFT do yêu cầu owner ngày 2026-08-27. KHÔNG thuộc release
> hiện tại; `PLAN.md` mục 2 vẫn giữ Excel ngoài scope cho đến khi owner mở.
> **Mốc xem xét bắt buộc:** sau khi chạy hết **P4** (Wave E R3 domain rollout +
> Wave F R4 E2E), Lead đánh giá khả thi trên kiến trúc ổn định và báo owner.
>
> **Mục đích do owner xác định (2026-08-27):** khách hàng của dịch vụ đăng ký
> kinh doanh **tự ghi thông tin vào một file Excel** theo mẫu do owner phát;
> nạp file đó vào app; app **tự điền toàn bộ thông tin vào đúng biểu mẫu**;
> owner chỉ cần **bổ sung những ô app chưa có dữ liệu** là hồ sơ hoàn chỉnh.

## 1. Luồng nghiệp vụ đích

```
Owner phát file Excel mẫu cho khách
        │  (khách điền ở nhà — app không cần chạy)
        ▼
Khách trả lại file .xlsx đã điền
        │
        ▼  [Nạp file vào app]
App đọc Excel → sinh draft {values, checks, loops}
        │  + chạy validator FormDomain như khi gõ tay
        ▼
App hiển thị hồ sơ đã điền + DANH SÁCH Ô CÒN THIẾU (đánh dấu)
        │
        ▼  Owner rà, bổ sung phần thiếu trên biểu mẫu
Xuất DOCX/ZIP như quy trình hiện tại (cùng gate chặn lỗi)
```

Điểm mấu chốt: Excel chỉ là **lớp "phiếu thu thông tin"**. Sau khi nạp, mọi thứ
chạy đúng một đường như nhập tay — draft JSON vẫn là nguồn chân lý duy nhất.

## 2. Vì sao kiến trúc hiện tại làm được (điểm tựa)

| Nền có sẵn | Vai trò với Excel |
|---|---|
| Draft v2 `{values, checks, loops}` + `_row_id` | Translator Excel→draft ghi vào đúng store; sau đó mọi tính năng (đồng bộ key, bảng lặp, M72 selector) tự hoạt động |
| `form_maps` + `section_specs` + registry runtime | Sinh file Excel mẫu **tự động** theo từng nhóm thủ tục (mỗi form một vùng/sheet), không vẽ tay ô |
| Validator tập trung FormDomain | Sau import chạy đúng validator; ô thiếu/bị chặn hiện lên trong panel lỗi hiện có — đúng "bổ sung phần thiếu" |
| Conditional blocks (`cond`, selector M72) | Giá trị loại hình/điều kiện trong Excel quyết định variant — không cần logic mới |
| Xuất DOCX/ZIP + recompute totals | Không đổi; Excel không phải "cửa sau" bỏ validation |

## 3. Thiết kế file Excel gốc (cần owner chốt khi mở — không tự chế)

- **Một khách = một file**. Cấu trúc đề xuất: 1 sheet "Thông tin chung" (loại
  thủ tục, loại hình DN…) + mỗi nhóm biểu một sheet; hàng = trường, cột =
  `Nhãn (người đọc)` | `Ô điền` | `Ghi chú`.
- File mẫu **sinh tự động từ form_maps** kèm chú thích bắt buộc/tùy chọn — tránh
  drift khi mẫu giấy đổi: regen file mẫu cùng đợt regen template.
- Ô điều kiện dạng chọn (loại hình DN, hạch toán…) dùng Data Validation dropdown
  trong Excel để hạn chế khách gõ sai.
- Bảng lặp (thành viên, ngành nghề, tài sản): mỗi dòng một hàng Excel; số dòng
  linh hoạt; cột "STT" là số thứ tự hiển thị, không phải dữ liệu nhập.

## 4. Rủi ro chính & cách chặn

| Rủi ro | Chặn bằng |
|---|---|
| Khách gửi file lệch khung / đổi tên sheet | Import kiểm cấu trúc trước, sai → fail-loud kèm mã lỗi riêng + chỉ đúng ô sai; không đoán mò |
| Khách gõ tự do vào ô chọn (loại hình, GTGT…) | Dropdown + validator giá trị; sai severity blocking |
| Nhãn mẫu giấy đổi theo thời gian | File mẫu regenerate từ nguồn; round-trip test chặn |
| Hồ sơ lớn (nhiều thành viên/nhiều ngành) | Giới hạn dòng hợp lý + test dữ liệu biên |
| Hai nguồn dữ liệu (Excel cũ vs draft chỉnh tay sau import) | Import one-shot: sau nạp, Excel không còn vai trò; mọi chỉnh sửa diễn ra trên app |

## 5. Điều kiện mở triển khai (checklist gate riêng)

1. P4 đóng; canonical keys ổn định (hết "vocabulary chờ chốt" N1).
2. Owner duyệt **hình dạng file Excel** (Lead đề xuất từ form_maps → owner duyệt).
3. Chốt thư viện `openpyxl` (pin version) — đóng gói được trên máy Windows sạch
   không cần cài Excel (không phá R6).
4. Contract test: round-trip draft→xlsx→draft giữ 100% giá trị; file sai cấu
   trúc → fail-loud; bảng lặp nhiều dòng; file rỗng/trống trường bắt buộc.
5. UI import: một nút "Nạp hồ sơ từ Excel" cạnh "Mở hồ sơ (.json)" hiện có;
   báo lỗi hiển thị trong panel lỗi chuẩn.

## 6. Câu hỏi owner trả khi MỘT bộ hồ sơ Excel (trả lời được ngay, không gấp)

- E1: Mỗi file Excel phủ **một nhóm thủ tục** (VD chỉ "thành lập TNHH") hay
  **gộp mọi loại thủ tục** trong một file (nhiều sheet, app tự chọn phần dùng)?
- E2: Khách điền **tiếng Việt có dấu** thoải mái — cần app chuẩn hóa gì thêm
  (hoa/lthường, ngày tháng dạng 01/02/2026…)?
- E3: Ngành nghề: khách ghi **tên ngành tự do** rồi app tra VSIC giúp, hay yêu
  cầu khách có sẵn mã ngành?
- E4: Sau import, ô còn thiếu cần hiển thị thế nào cho đủ nhanh: đếm tổng +
  danh sách theo mẫu (panel lỗi hiện có) hay thêm chế độ "checklist bổ sung"?
- E5: Có cần xuất ngược **đã điền ra Excel** (để khách xác nhận lại) không,
  hay chỉ một chiều khách→app?
