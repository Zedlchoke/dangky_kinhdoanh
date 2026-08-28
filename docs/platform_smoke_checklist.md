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
| S7 | Offline | ngắt mạng, lặp S2–S6 | mọi bước vẫn chạy (app không gọi mạng) |
| S8 | Clean-machine | máy KHÔNG có Python (chỉ khi đã có `.exe` từ P6) | cài đặt/mở `.exe`, lặp S2–S6 |

## Quy tắc verdict

- Mỗi bước ghi PASS/FAIL kèm lệnh thật + output; FAIL ở bước nào dừng ở đó,
  ghi nguyên nhân. Không đánh PASS theo ước lượng.
- Kết quả append vào `docs/execution_ledger.md` (wave P3/P6) kèm ngày + người
  chạy + hash artifact nếu là `.exe`.
- Trước khi chạy thật: mọi báo cáo release ghi suite này **NOT RUN (critical
  với P6)** — không được tính là PASS.
