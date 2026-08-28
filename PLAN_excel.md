# PLAN_excel — Excel thu thập thông tin khách hàng (BẢN LƯU — ĐÃ HỢP NHẤT)

> **Trạng thái 2026-08-28:** Nội dung bản này đã được hợp nhất nguyên vẹn vào
> **`PLAN.md` mục 4** (kèm wave triển khai X1–X6). Bản lưu giữ nguyên để tra
> cứu lịch sử; KHÔNG cập nhật nữa — mọi sửa đổi sau này làm trực tiếp trên
> `PLAN.md`. Implement vẫn chỉ mở theo lệnh owner ("Bắt đầu Excel").

## 0. Quy trình đích (owner xác định 2026-08-27 — BẮT BUỘC theo đúng thứ tự)

```
(1) Owner xác định khách muốn làm dịch vụ nào
        │
(2) Owner CHỌN thủ tục trong app
        │
(3) App XUẤT file Excel riêng cho thủ tục đó
      — đẹp, dễ dùng, câu hỏi viết bằng ngôn ngữ đời thường
        │
(4) Khách nhận file, tự điền thông tin (app không cần chạy)
        │
(5) Owner nạp file Excel vào app
        │
(6) App tự điền toàn bộ thông tin vào đúng biểu mẫu
      + chỉ rõ những ô CÒN THIẾU cần owner bổ sung
        │
(7) Owner rà, bổ sung, xuất DOCX như quy trình hiện tại
```

Excel = **phiếu thu thập thông tin đối mặt khách hàng**, không phải bản sao
biểu mẫu pháp lý. Sau bước (6), Excel hết vai trò; draft trong app là nguồn
chân lý duy nhất.

## 1. Nguyên tắc "câu hỏi dễ hiểu" (yêu cầu cứng của owner)

File Excel KHÔNG dùng nhãn biểu mẫu khô cứng. Mỗi ô điền là một **câu hỏi/
nhóm câu hỏi đời thường** có mapping ngầm về data-key của app:

| Trong Excel (khách đọc) | Mapping ngầm | Trong biểu mẫu (app tự điền) |
|---|---|---|
| "Bạn muốn đặt tên công ty là gì? (tiếng Việt)" | `dn.ten_tieng_viet` | Tên công ty viết bằng tiếng Việt |
| "Công ty do ai đứng tên chịu trách nhiệm? Họ tên đầy đủ" | `ndd.ho_ten` | Người đại diện theo pháp luật |
| "Vốn bạn đăng ký góp là bao nhiêu (VNĐ)?" | `von_dieu_le` | Vốn điều lệ |
| "Công ty hoạt động trong lĩnh vực nào? Ghi tên ngành bạn muốn" | `ds_nganh.ten_nganh` | Ngành nghề kinh doanh (app tra mã VSIC giúp) |

Quy tắc soạn câu hỏi:
- Một câu hỏi một ý; có **ví dụ điền mẫu** (chữ mờ) ngay dưới ô;
- Tùy chọn dạng chọn dùng **dropdown** (loại hình DN, phương án thuế…) — khách
  không phải gõ;
- Gom câu theo **nhóm đời thường** ("Về người đại diện", "Về vốn", "Về ngành
  nghề") thay vì mục 1/2/3 của biểu mẫu;
- Câu hỏi nào app **tự sinh được** thì không hỏi khách (tổng vốn, số lượng thành
  viên suy từ danh sách, ngày nộp hồ sơ…).

## 2. Hình thức file Excel — "đẹp, dễ dùng" (yêu cầu cứng của owner)

- Sheet mở đầu: tiêu đề dịch vụ, hướng dẫn 5 dòng, cách điền (ô vàng = điền,
  ô xám = app tự làm, đừng đụng);
- **Khóa bảo vệ** mọi ô ngoài vùng điền (Excel protection) — khách không thể
  phá khung cột;
- Màu nhóm phần, viền rõ, cột rộng vừa, không cuộn ngang trên màn hình thường;
- Điền ví dụ mẫu (xám mờ) ngay trong ô;
- Cuối file: bảng "Giấy tờ bạn cần chuẩn bị" liệt kê hồ sơ kèm theo của thủ
  tục đã chọn (từ `ho_so_bao_gom` khi đã DECIDED).

## 3. Kiến trúc kỹ thuật (khi mở — mọi thứ sinh từ nguồn có sẵn)

- **Lớp questionnaire** (mới): mapping `question_id → data-key` + câu hỏi +
  ví dụ + dropdown options. KHUNG sinh tự động từ `form_maps`/registry; **nội
  dung câu hỏi là sản phẩm** — Lead soạn thảo, owner duyệt từng cụm trước khi
  dùng thật. Lớp này tách biệt, không sửa form_maps/templates.
- **Xuất Excel** (bước 3): app đọc thủ tục đang chọn → lấy lớp questionnaire
  → viết .xlsx (openpyxl, pin version) — gồm protection + styling.
- **Nạp Excel** (bước 5): kiểm cấu trúc file trước (sai khung → fail-loud mã
  lỗi riêng), rồi dịch question_id→data-key vào draft, chạy validator chuẩn,
  panel lỗi hiện có làm "danh sách còn thiếu".
- Round-trip test: draft→xlsx→draft giữ 100% giá trị; file khách sửa khung →
  báo lỗi rõ ràng; bảng lặp nhiều dòng; file rỗng trường bắt buộc.

## 4. Rủi ro chính & chặn

| Rủi ro | Chặn bằng |
|---|---|
| Khách phá khung/sheet | Excel protection + kiểm cấu trúc lúc nạp, fail-loud |
| Khách gõ tự do ô dropdown | Data Validation + validator blocking |
| Câu hỏi thân thiện lệch nghĩa pháp lý | Owner duyệt từng cụm câu hỏi trước dùng thật; câu hỏi gắn version |
| Mẫu giấy đổi → câu hỏi cũ sai | Regen questionnaire cùng đợt regen template; diff review như generated artifacts |
| Excel cũ/không cài Excel trên máy khách | .xlsx mở được LibreOffice/Excel/Google Sheets; app không cần Excel khi nạp |
| Phá Windows packaging (R6) | openpyxl thuần Python, pin version, test trên máy sạch |

## 5. Điều kiện mở triển khai

1. P4 đóng; canonical keys ổn định.
2. Owner duyệt: hình dạng file + BỘ CÂU HỎI cụm đầu tiên (khuyến nghị bắt đầu
   bằng "Thành lập doanh nghiệp" — nhóm thủ tục đông khách nhất).
3. Chốt openpyxl + requirements pin.
4. Contract test round-trip + negative (file sai, file rỗng, ô lạ).
5. UI: nút "Xuất phiếu Excel cho khách" (trong màn hồ sơ) + "Nạp phiếu Excel"
   (cạnh "Mở hồ sơ (.json)").

## 6. Câu hỏi owner trả khi MỞ (không gấp)

- E1: Xuất phiếu theo **một thủ tục đã chọn** (như quy trình mục 0) — cần cả
  biến thể gì kèm theo không (VD: thành lập có kèm ngành đặc biệt)?
- E2: Khách điền tiếng Việt có dấu — app chuẩn hóa gì thêm (hoa/lthường, ngày
  01/02/2026, số tiền có dấu chấm nghìn)?
- E3: Ngành nghề: khách ghi tên tự do, app tra VSIC đề xuất rồi owner chọn —
  đúng ý không?
- E4: Danh sách "còn thiếu" sau nạp: dùng panel lỗi hiện có hay thêm chế độ
  "checklist bổ sung" theo từng nhóm câu?
- E5: Có cần xuất ngược hồ sơ đã điền ra Excel để khách xác nhận lại không?
- E6: Bộ câu hỏi đầu tiên owner muốn tự soạn hay Lead soạn nháp rồi owner sửa?
