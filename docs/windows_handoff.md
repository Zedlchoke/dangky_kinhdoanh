# Windows handoff — chạy smoke S1–S8 + build .exe trên máy Windows thật (F6/O6)

> **Trạng thái hiện tại: NOT RUN — handoff, CHƯA có evidence Windows thật.**
> Máy dev là macOS (không có Windows/pywebview/WebView2), nên toàn bộ công
> cụ trong `tools/windows_handoff/` được soạn sẵn để một người có máy
> **Windows 10/11 sạch** chạy theo đúng quy trình. Cho tới khi có evidence,
> mọi báo cáo release phải ghi S1–S8 = **NOT RUN (critical với F6)** —
> không được tính PASS; macOS/Linux/compileall **không** thay thế gate này
> (PLAN F6, `docs/platform_smoke_checklist.md`).

## Công cụ đã chuẩn bị sẵn

| File | Dùng để |
|---|---|
| `tools/windows_handoff/run_smoke_s1_s8.ps1` | Chạy S1–S7 tuần tự (+S8 với `-UseExe`), ghi `evidence/Windows_S<N>.log`, in `[MANUAL]` ở các bước cần nhìn màn hình, KHÔNG tự PASS bước visual. |
| `tools/windows_handoff/dangky_kinhdoanh.spec` | Spec PyInstaller onefile tái lập được; bundle `app_web/ui`, `app/data` (blocks/form_maps/use_cases/VSIC/questionnaire), `app/templates` (87 .docx); KHÔNG bundle `profiles/`, `generated_ho_so/`, evidence/test. |
| `tools/windows_handoff/launch_app_web.py` | Entry của spec: chạy lại `app_web/main.py` trong bundle với đúng `__file__` (main.py tính ROOT/APP_DIR từ `__file__` — nếu dùng thẳng main.py làm entry thì ROOT trỏ ra ngoài bundle). |
| `tools/windows_handoff/README.md` | Danh sách điều PHẢI kiểm trên máy thật + mẫu bảng evidence. |

---

## Bước 1 — Chuẩn bị máy + lấy repo

1. Máy **Windows 10/11 thật** (hoặc VM được owner chấp thuận), KHÔNG phải
   máy dev. Ghi lại: edition + version, CPU/RAM, user có/không admin.
2. Lấy code: `git clone` repo và checkout branch chứa handoff này, hoặc
   tải zip checkout sạch. **Khuyến nghị thử thêm một đường dẫn có dấu
   tiếng Việt và/hoặc space** (ví dụ `C:\Users\NV A\dkkd\`) để chứng minh
   path lạ không vỡ (PLAN F6.6).
3. Ghi lại commit hash đang chạy — evidence phải gắn với commit.

## Bước 2 — Cài Python 3.11+ (hoặc chỉ dùng .exe build)

- Tải **Python 3.11+ 64-bit** từ python.org; khi cài tick **"Add
  python.exe to PATH"** và giữ tùy chọn **tcl/tk** (dialog mở/lưu draft và
  phiếu Excel dùng tkinter). Kiểm tra: `python --version`.
- Nói rõ đây là bước cài tay có mạng; các bước SAU (chạy app + smoke) phải
  chạy được **không cần mạng** (S7 offline).
- Máy clean-machine cho S8 thì ngược lại: **KHÔNG cài Python**, chỉ có
  `.exe` (bước 4).

## Bước 3 — Cài dependencies (KHÔNG có requirements.txt)

Repo **không có `requirements.txt`**; nguồn deps duy nhất là
`requirements-dev.txt` (đã pin version và đã gồm `pywebview>=5.0` cho
Windows, `openpyxl` cho phiếu Excel, `python-docx`/`lxml` cho render).
Từ root repo:

```
python -m pip install -r requirements-dev.txt
python -c "import webview; print(webview.__version__)"   # phải ra version
```

Kiểm tra thêm trên máy thật:

- **WebView2 Runtime (Evergreen)**: Control Panel → Programs phải có
  "Microsoft Edge WebView2 Runtime" — ghi version. (Win11 thường có sẵn.)
- **LibreOffice** (khuyến nghị): `soffice` trong PATH để S6 có đủ
  DOCX+PDF+normalize Word-compat; nếu không cài, S6 chỉ xuất .docx và
  phải ghi rõ vào evidence (main.py bỏ qua normalize khi thiếu soffice).

Lưu ý pin version: `requirements-dev.txt` cố tình **chưa pin** pywebview/
PyInstaller ("không pin mù" từ máy macOS). Sau khi Windows runner probe
thật lần đầu, owner/Lead cập nhật pin đúng version đã chạy — đó là điều
kiện của PLAN F6.1 (khóa dependency theo probe thật).

## Bước 4 — Chạy smoke S1–S8

Từ root repo (PowerShell):

```
powershell -ExecutionPolicy Bypass -File tools\windows_handoff\run_smoke_s1_s8.ps1
```

Script làm hộ phần máy: pre-flight (python, pywebview, WebView2 registry,
soffice — chỉ log, không cài gì), launch `python -X utf8 app_web\main.py`,
kiểm tra process còn sống / exit code, ghi console output vào
`evidence/Windows_S<N>.log`, kiểm tra thư mục mới trong `generated_ho_so\`
ở S6.

**Các bước cần nhìn màn hình do NGƯỜI CHẠY làm và tự ghi PASS/FAIL** khi
script in `[MANUAL]`:

| Bước | Người chạy phải làm gì |
|---|---|
| S1 | Xác nhận cửa sổ app mở, không traceback; ghi version OS + WebView2 |
| S2 | Xác nhận danh sách thủ tục render đủ, không JS error nghiêm trọng |
| S3 | Nhập từng kind: text/money/percent/checkbox/radio/vsic/editable-grid/fixed-matrix/nested-grid/output-table; screenshot từng kind |
| S4 | Nút "Mở hồ sơ .json" → dialog tkinter mở, chọn file nạp đúng |
| S5 | Lưu draft → mở lại bằng S4 ra đúng dữ liệu |
| S6 | Export hồ sơ CÓ blocking error (phải bị chặn) rồi hồ sơ sạch; mở .docx bằng Word thật |
| S7 | Ngắt mạng (rút cáp/tắt wifi), script launch lại, lặp nhanh S2–S6 |
| S8 | Máy KHÔNG Python, chỉ `.exe`: `... run_smoke_s1_s8.ps1 -UseExe` |

Quy tắc (từ `docs/platform_smoke_checklist.md`): mỗi bước PASS/FAIL kèm
lệnh + output thật; **FAIL ở bước nào dừng ở đó**, ghi nguyên nhân; không
PASS theo ước lượng. Script có hỏi "Tiep tuc?" khi bạn nhập FAIL — trả lời
N để đúng quy tắc dừng.

Chấp thuận nhỏ của script (ghi rõ trong README thư mục): khi chạy từ
`.exe` (onefile), thư mục extract tạm bị xoá khi đóng app, nên hãy mở thư
mục export và chép file ra NGAY trong phiên; `launch_app_web.py` sẽ cố
rescue-copy sang `Documents\DangKyKinhDoanh\generated_ho_so` khi app đóng
— kiểm tra cả hai chỗ khi ghi evidence S8.

## Bước 5 — Build .exe tái lập

```
python -m pip install pyinstaller
pyinstaller --clean --noconfirm tools\windows_handoff\dangky_kinhdoanh.spec
# -> dist\DangKyKinhDoanh.exe (onefile, console=True)
```

Yêu cầu tái lập (PLAN F6.1, F6.3):

1. Ghi build manifest TRƯỚC khi build vào
   `evidence/Windows_build_manifest.txt`: `python --version`, `pip freeze`,
   `pyinstaller --version`, version WebView2, commit hash.
2. **Build hai lần từ checkout sạch**, lưu SHA-256 mỗi lần
   (`Get-FileHash -Algorithm SHA256 dist\DangKyKinhDoanh.exe`) và so
   **inventory nội dung** bằng `pyi-archive_viewer -l` (onefile có thể lệch
   byte do timestamp — nội dung archive phải giống nhau).
3. Kiểm negative của bundle: không được có `profiles/`,
   `generated_ho_so/`, docs/evidence bên trong archive; phải có
   `app_web/ui`, `app/data/blocks` (87), `app/data/nganh_vsic.json`
   (VSIC đầy đủ, không phải mock mini), `app/data/questionnaire`,
   `app/templates` (87 .docx).

## Bước 6 — Ghi evidence + cập nhật verdict

1. Mỗi bước S1–S8: log script đã tự ghi (`evidence/Windows_S<N>.log`) +
   screenshot đặt `evidence/img/Windows_S<N>_*.png` + (S8) SHA-256 exe.
2. Điền mẫu bảng evidence trong `tools/windows_handoff/README.md`.
3. Append kết quả vào `docs/execution_ledger.md`: ngày + người chạy +
   PASS/FAIL/NOT RUN từng bước + hash artifact.
4. FAIL nào → tạo defect theo `docs/defect_registry.md` (class, bước,
   screenshot, nguyên nhân) — KHÔNG sửa code tu tiện trong phiên smoke.
5. Sau khi có evidence: Lead/owner cập nhật trạng thái gate F6; khi pywebview
   PASS thì theo quyết định P7 (`app_tk` deprecated, loại khỏi package).

## Rủi ro đã biết khi chạy thật

- `.exe` chưa ký → SmartScreen/AV có thể chặn; ghi nguyên nhân + hash,
  không tắt bảo mật để ép PASS (upx đã tắt trong spec để giảm rủi ro).
- Thiếu LibreOffice → S6 thiếu PDF/normalize, Word 16.x có thể báo
  "unreadable content" với .docx chưa normalize — phải ghi rõ trong evidence
  thay vì coi là PASS đủ điều kiện.
- `requirements-dev.txt` chưa pin pywebview/PyInstaller — version cài được
  có thể mới hơn đã probe; nhất thiết ghi `pip freeze` vào build manifest
  và cập nhật pin sau probe.
- Onefile extract tạm: export trong .exe nằm trong thư mục tạm (đã mô tả ở
  trên) — đây là hành vi đã ghi, không phải bug, nhưng người chạy phải biết.
