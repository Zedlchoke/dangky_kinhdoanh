# Platform smoke checklist — pywebview/WebView2 + tkinter (Windows)

> Trạng thái: **NOT RUN — CHƯA TỪNG CHẠY** (tính tới checkpoint P3,
> 2026-08-28). Máy dev là macOS; pywebview/WebView2 và dialog tkinter chỉ
> smoke được trên Windows thật do owner cung cấp (PLAN P3.4, P6).
> File này là hướng dẫn chuẩn để chạy khi có máy — KHÔNG tính macOS/Linux/
> compileall là kết quả platform (PLAN P6: "macOS/Linux/compileall KHÔNG được
> tính là Windows smoke").

## Điều kiện trước khi chạy

1. Máy Windows 10/11 thật (hoặc VM do owner chấp thuận), KHÔNG phải máy dev.
2. WebView2 Runtime (Evergreen) đã cài — kiểm tra `Control Panel → Programs`
   có "Microsoft Edge WebView2 Runtime", ghi version.
3. Python 3.x (hoặc `.exe` build từ P6 — khi đó bỏ cột "lệnh").

## Các bước smoke + evidence phải ghi

| # | Bước | Lệnh / thao tác | Evidence ghi lại |
|---|---|---|---|
| S1 | Khởi chạy app desktop | `python -X utf8 app_web/main.py` | Cửa sổ mở, không traceback console; version OS + WebView2 |
| S2 | UI render | nhìn màn hình hồ sơ | danh sách thủ tục hiển thị; DevTools không bắt lỗi JS nghiêm trọng |
| S3 | Chọn thủ tục + nhập dữ liệu | nhập từng kind: text, money, percent, checkbox, radio, vsic, editable-grid, fixed-matrix, nested-grid, output-table | screenshot từng kind |
| S4 | Dialog mở hồ sơ (tkinter) | nút "Mở hồ sơ .json" | dialog tkinter mở được, chọn file trả đúng path vào app |
| S5 | Dialog lưu hồ sơ | nút lưu draft | file .json ghi được, mở lại bằng S4 ra đúng dữ liệu |
| S6 | Xuất DOCX/ZIP | nút export với hồ sơ có blocking error (phải bị chặn) rồi hồ sơ sạch | file sinh trong `generated_ho_so/`; mở bằng Word thật |
| S6b | Phiếu Excel cho khách (wave X5) | chọn thủ tục CÓ questionnaire (PLI_M12, PLI_M27, PLI_M72, PLII_M01–M04) → "Xuất phiếu Excel cho khách" → điền bằng Excel Desktop/Calc → "Nạp phiếu Excel" | file .xlsx mở được, ô lock đúng; nạp lại tái tạo dữ liệu; thiếu câu bắt buộc → báo `MISSING_REQUIRED` cụ thể, draft cũ giữ nguyên; sửa `__map`/đổi case → bị từ chối |
| S7 | Offline | ngắt mạng, lặp S2–S6 | mọi bước vẫn chạy (app không gọi mạng) |
| S8 | Clean-machine | máy KHÔNG có Python (chỉ khi đã có `.exe` từ P6) | cài đặt/mở `.exe`, lặp S2–S6 |

### Scenario bổ sung bắt buộc theo PLAN §6.4

Ngoài S1–S8, wave P0/P1 phải chứng minh thêm 4 kịch bản này (ghi evidence
riêng từng cái, không gộp ước lượng):

| Scenario | Cách chạy | Evidence |
|---|---|---|
| Excel case-level | S6b ở trên — xuất → điền → nạp lại nguyên vòng, gồm cả nhánh fail-loud | log `*_S6b` + ảnh Excel Desktop mở file |
| Đường dẫn có dấu/space | copy repo (Windows) hoặc `.app`/`.exe` (macOS) vào thư mục có dấu tiếng Việt + space, chạy lại S1–S6b tại đó | log session tại đường dẫn lạ |
| User KHÔNG admin | toàn bộ launch + build + chạy `.exe`/`.app` trên user thường | preflight log ghi admin=yes/no; nếu chạy trên admin phải lặp lại trên user thường |
| Offline | S7 ở trên (ngắt mạng thật, không chỉ tắt wifi icon) | log `*_S7` |

## Quy tắc verdict

- Mỗi bước ghi PASS/FAIL kèm lệnh thật + output; FAIL ở bước nào dừng ở đó,
  ghi nguyên nhân. Không đánh PASS theo ước lượng.
- Kết quả append vào `docs/execution_ledger.md` (wave P3/P6) kèm ngày + người
  chạy + hash artifact nếu là `.exe`.
- Trước khi chạy thật: mọi báo cáo release ghi suite này **NOT RUN (critical
  với P6)** — không được tính là PASS.
