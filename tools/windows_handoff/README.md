# Windows handoff — README cho người chạy SMOKE/BUILD trên máy thật

> **TRẠNG THÁI: HANDOFF CHƯA CHẠY THẬT.** Toàn bộ file trong thư mục này
> được soạn trên máy dev macOS, nơi KHÔNG có Windows/pywebview/WebView2.
> Verdict S1–S8 hiện là **NOT RUN** và KHÔNG ĐƯỢC coi là PASS cho tới khi
> một người có máy Windows thật chạy xong và ghi evidence
> (PLAN F6: "macOS/compileall không thay thế gate này").
>
> Hướng dẫn đầy đủ từng bước: `docs/windows_handoff.md`.
> Checklist gốc: `docs/platform_smoke_checklist.md`.

## Nội dung thư mục

| File | Vai trò |
|---|---|
| `run_smoke_s1_s8.ps1` | Chạy tuần tự S1–S7 (+S8 với `-UseExe`), ghi log `evidence/Windows_S<N>.log`, các bước cần nhìn màn hình in `[MANUAL]` và chờ người chạy nhập PASS/FAIL — script KHÔNG tự đánh PASS bước visual. |
| `dangky_kinhdoanh.spec` | PyInstaller spec build `.exe` onefile tái lập được (bundle `app_web/ui`, `app/data`, `app/templates`, loại `profiles/`, `generated_ho_so/`, evidence). |
| `launch_app_web.py` | Entry script cho spec — chạy lại `app_web/main.py` trong bundle với đúng `__file__` (main.py tính mọi đường dẫn từ `__file__`), kèm rescue-copy `generated_ho_so` khi chạy .exe. |

## ĐIỀU PHẢI KIỂM TRÊN MÁY THẬT (không bỏ mục nào)

1. **Python 3.11+ 64-bit** chạy được từ PATH (`python --version`); tick
   "tcl/tk" khi cài (dialog mở/lưu draft và phiếu Excel dùng tkinter).
2. **`pip install -r requirements-dev.txt`** thành công offline-sau-cài;
   `python -c "import webview"` ra version — KHÔNG có `requirements.txt`,
   `requirements-dev.txt` là nguồn deps duy nhất (đã gồm `pywebview>=5.0`).
3. **WebView2 Runtime (Evergreen)** có trong Control Panel → Programs; ghi
   version vào evidence.
4. **LibreOffice** (`soffice` trong PATH) — có thì S6 đủ docx+PDF+normalize
   Word-compat; không có thì S6 chỉ docx và phải ghi rõ điều đó vào evidence.
5. **Đường dẫn chứa dấu tiếng Việt và/hoặc space** (ví dụ
   `C:\Users\Nguyễn Văn A\dkkd test\`): clone/copy repo vào vị trí như vậy
   và chạy lại smoke ít nhất một lần để chứng minh không vỡ.
6. **User KHÔNG có quyền admin**: toàn bộ quy trình (launch + build + chạy
   .exe) phải chạy được không cần admin; nếu bước nào cần admin → FAIL/ghi
   defect.
7. **Chạy từ checkout SẠCH** (không file untracked lạ), và **build .exe hai
   lần từ checkout sạch** rồi so sánh inventory nội dung + SHA-256
   (PLAN F6.3).
8. **S7 offline thật**: rút cáp/tắt wifi; script không tải xuống gì sau khi
   deps đã cài.
9. **S8 clean-machine**: máy KHÔNG có Python, chỉ có `.exe`; `.exe` chưa ký
   có thể bị SmartScreen chặn — nếu vậy ghi nguyên nhân + hash, KHÔNG tắt
   bảo mật để ép PASS.
10. **Export trong .exe**: mở thư mục export và chép file ra NGAY trong
    phiên (thư mục extract tạm bị xoá khi đóng app; `launch_app_web.py` có
    rescue-copy sang `Documents\DangKyKinhDoanh\generated_ho_so` — kiểm tra
    cả hai chỗ).
11. **Không commit** `generated_ho_so/`, `profiles/`, evidence chứa dữ liệu
    người thật vào git/artifact (PLAN F6.2).

## Quy tắc verdict (bắt buộc)

- Mỗi bước S1–S8: PASS / FAIL / NOT RUN kèm lệnh thật + output thật. Không
  PASS theo ước lượng; FAIL ở bước nào dừng ở đó, ghi nguyên nhân.
- Console/log của app là evidence: `run_smoke_s1_s8.ps1` tự gom vào
  `evidence/Windows_S<N>.log`; các bước `[MANUAL]` chỉ PASS khi người chạy
  thật sự nhìn màn hình.
- Kết quả append vào `docs/execution_ledger.md` kèm ngày + người chạy +
  SHA-256 artifact nếu là `.exe`.

## Mẫu bảng evidence (điền khi chạy thật)

Run: `____-__-__ __:__` | Người chạy: `____` | Máy: `Windows 10/11 ____, CPU ____, RAM ____`
Python: `3.__.__` | pywebview: `____` | WebView2 Runtime: `____` | LibreOffice: `có/không`
Repo commit: `________` | Đường dẫn repo chứa dấu/space: `có/không`

| # | Bước | Lệnh thật đã chạy | Kết quả (PASS/FAIL/NOT RUN) | Evidence (log/screenshot/SHA-256) |
|---|---|---|---|---|
| S1 | Khởi chạy app desktop | `powershell -ExecutionPolicy Bypass -File tools\windows_handoff\run_smoke_s1_s8.ps1` | | `evidence/Windows_S1.log`, `evidence/img/Windows_S1_*.png` |
| S2 | UI render danh sách thủ tục | (trong script) | | `evidence/Windows_S2.log`, ảnh |
| S3 | Nhập từng kind dữ liệu | (trong script) | | `evidence/Windows_S3.log`, ảnh từng kind |
| S4 | Dialog mở hồ sơ .json | (trong script) | | `evidence/Windows_S4.log`, ảnh |
| S5 | Dialog lưu hồ sơ | (trong script) | | `evidence/Windows_S5.log`, ảnh |
| S6 | Xuất DOCX/ZIP (blocked + sạch) | (trong script) | | `evidence/Windows_S6.log`, ảnh Word mở file |
| S7 | Offline (ngắt mạng, lặp S2–S6) | (trong script) | | `evidence/Windows_S7.log` |
| S8 | Clean-machine .exe (không Python) | `... run_smoke_s1_s8.ps1 -UseExe` | | `evidence/Windows_S8.log`, SHA-256 exe |

Build manifest (ghi vào `evidence/Windows_build_manifest.txt` trước khi build):
`python --version`, `pip freeze`, `pyinstaller --version`, version WebView2,
hash `.exe` build lần 1 và lần 2, diff inventory archive hai lần build.

## Lệnh build .exe tái lập

```
python -m pip install pyinstaller          # pin version vào build manifest
pyinstaller --clean --noconfirm tools\windows_handoff\dangky_kinhdoanh.spec
# -> dist\DangKyKinhDoanh.exe
```

Lần lượt 1 và lần 2 đều từ checkout sạch; so inventory bằng
`pyi-archive_viewer -l dist\DangKyKinhDoanh.exe > evidence\Windows_exe_inventory_1.txt`
(đổi tên lần 2) rồi diff hai file — nội dung archive phải giống nhau.
