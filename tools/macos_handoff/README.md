# macOS handoff — build `.app` + smoke cho "Trợ lý hồ sơ ĐKKD" (wave P1)

> **TRẠNG THÁI:** Kit được soạn VÀ build/smoke structural THẬT trên máy dev
> macOS arm64 (Python 3.13.14, PyInstaller 6.21.0, pywebview 6.2.1, soffice
> Homebrew). Toàn bộ bước MÁY ĐỌC được (build 2 lần, engine probe trong
> bundle, GUI launch/restart, rescue-copy, privacy bundle) đã PASS bằng lệnh
> thật — evidence tại `~/Documents/DangKyKinhDoanh/evidence_macos/`.
> Các bước cần NHÌN MÀN HÌNH (S2–S6 visual, S7 ngắt mạng thật, S8 clean
> machine) vẫn **NOT RUN** cho tới khi người chạy điền verdict vào bảng
> evidence dưới. KHÔNG coi app là phát hành được trước khi đủ.

## Nội dung thư mục

| File | Vai trò |
|---|---|
| `dangky_kinhdoanh_mac.spec` | PyInstaller spec **windowed + onedir** (`.app`), bundle `app_web/main.py` (DATA), `app_web/ui`, `app/data`, `app/templates` (87 .docx), `tools/phase5r_expectations.json`, pywebview data. KHÔNG bundle `profiles/`, `generated_ho_so/`, docs, `99_muc_luc/`, `app_tk/`, test suite. |
| `launch_app_web.py` | Entry của spec: chạy lại `app_web/main.py` trong bundle với đúng `__file__` (main.py tính ROOT/APP_DIR từ `__file__`). Kèm rescue-copy `generated_ho_so` sang `~/Documents/DangKyKinhDoanh/` khi đóng app, và chế độ engine-probe (`DKKD_ENGINE_PROBE`) cho smoke structural. |
| `build_app.sh` | Build **2 lần từ checkout sạch**, ghi build manifest + inventory SHA-256 từng file + diff 2 lần build vào evidence NGOÀI git. |
| `run_smoke_mac.sh` | Smoke S1–S7 (+S8) bản macOS + các bước AUTO: S-eng (engine probe trong bundle), S-path (đường dẫn Unicode+space), S-restart, S-privacy, S-viewer. Bước visual in `[MANUAL]` và chờ người chạy nhập P/F/S — KHÔNG tự PASS bước nhìn mắt. |
| `entitlements.plist` | Entitlement tối thiểu (allow-jit, allow-unsigned-executable-memory, disable-library-validation). **ASCII-only** — bộ parse entitlements của codesign (AMFI) từ chối cả comment XML. |

## Build

```
bash tools/macos_handoff/build_app.sh
# -> dist/DangKyKinhDoanh.app  (+ dist/_build1_DangKyKinhDoanh.app để đối chiếu)
# Evidence: ~/Documents/DangKyKinhDoanh/evidence_macos (ngoài git)
```

Build ghi sẵn `.git/info/exclude` cho `build/`, `dist/` (local-only; repo chưa
có chúng trong `.gitignore` — cần Lead quyết định thêm vào `.gitignore`).

**Reproducibility (đã chạy thật 2026-09-10, commit d7ec076):** 629 file
inventory; 2 lần build khác nhau ĐÚNG 3 file, đều giải thích được:
`Contents/MacOS/DangKyKinhDoanh` + `Contents/_CodeSignature/CodeResources`
(ad-hoc signature có timestamp) và `base_library.zip` (zip ghi mtime). Toàn bộ
nội dung module + data + template GIỐNG NHAU 100%.

## Codesign / Gatekeeper

Máy build KHÔNG có Apple Developer identity (`security find-identity` = 0) —
app chỉ **ad-hoc sign** (bắt buộc để Apple Silicon chịu chạy), KHÔNG phải
bản public-ready (PLAN §7.6). Với app chưa ký: lần mở đầu cần right-click →
Open, và `spctl -a -vv` sẽ REJECTED — ghi verdict vào evidence, KHÔNG tắt
Gatekeeper để ép PASS. Khi owner cung cấp cert:

```
codesign --deep --force --options runtime \
  --entitlements tools/macos_handoff/entitlements.plist \
  --sign "Developer ID Application: …" dist/DangKyKinhDoanh.app
```

## Smoke

```
bash tools/macos_handoff/run_smoke_mac.sh
```

Lưu ý vận hành khi chạy:
- S1/S6/S7/S-restart **mở cửa sổ app thật** trên máy — người chạy phải nhìn
  màn hình, thao tác UI và nhập P/F/S.
- S6: sau khi export trong app, ĐÓNG CỨA SỔ app (không force-quit) —
  rescue-copy chạy lúc đó và đưa hồ sơ sang
  `~/Documents/DangKyKinhDoanh/generated_ho_so/`; kiểm CẢ HAI chỗ (bundle
  `Contents/Frameworks/generated_ho_so` + Documents) khi ghi evidence.
  Force-quit (SIGKILL/quit event hệ thống) NHƯỜNG bước rescue — đó là giới
  hạn đã biết, README Windows cũng ghi same-trừ-hờ cho onefile.
- S7 offline: ngắt wifi THẬT (app không gọi mạng nào; WKWebView chỉ load
  file local).
- S8 clean-machine: cần máy Mac KHÁC không cài Python; copy `.app` sang đó,
  right-click → Open, lặp S2–S6, ghi spctl/Gatekeeper verdict.

## Quy tắc verdict (bắt buộc, như Windows)

- PASS / FAIL / NOT RUN kèm lệnh thật + output thật. Không PASS theo ước
  lượng; FAIL ở bước nào dừng ở đó, ghi nguyên nhân.
- Bước `[MANUAL]` chỉ PASS khi người chạy thật sự nhìn màn hình.
- Kết quả append `docs/execution_ledger.md` kèm ngày + người chạy + SHA-256.

## Bảng evidence (điền khi chạy thật)

Run: `____-__-__ __:__` | Người chạy: `____` | Máy: macOS ____, arm64/Intel
pywebview: `6.2.1` | PyInstaller: `6.21.0` | soffice: có/không | commit: `d7ec076+`

| # | Bước | Kết quả thực tế 2026-09-10 | Còn cần người chạy |
|---|---|---|---|
| S1 | Launch `.app`, process sống | **PASS (AUTO)** — launch 12s sống, console sạch, cửa sổ "Trợ lý hồ sơ ĐKKD" tồn tại (System Events xác nhận) | Nhìn mắt: cửa sổ render đúng, không trắng trang |
| S2 | UI render danh sách | NOT RUN (visual) | Nhập P/F/S khi chạy script |
| S3 | Nhập từng kind dữ liệu | NOT RUN (visual) | text/money/percent/checkbox/radio/vsic/grids |
| S4 | Dialog mở .json (tkinter) | NOT RUN (visual) | tkinter dialog trên macOS |
| S5 | Dialog lưu draft | NOT RUN (visual) | lưu + mở lại đúng dữ liệu |
| S6 | Export DOCX/PDF/ZIP | **PASS (AUTO, engine-level)** — render DOCX 5288B + PDF 16000B bằng engine TRONG bundle; import Excel fail-loud kiểm chứng (phiếu thiếu câu bắt buộc bị từ chối MISSING_REQUIRED) | Export qua UI, ZIP, mở file bằng Word for Mac thật |
| S-eng | Engine probe trong bundle | **PASS (AUTO)** 11/11 — import PYZ, data 87 blocks/87 templates/87 form_maps/7 questionnaire, DOCX, PDF, Excel round-trip | — |
| S-path | Đường dẫn Unicode + space | **PASS (AUTO)** — probe ALL PASS từ `…/thư mục thử nghiệm ĐKKD có dấu và khoảng trắng/` | — |
| S-restart | Assets bền qua restart | **PASS (AUTO)** — GUI launch lần 2 sống; probe render lần 2 OK | Nhìn mắt UI lần 2 |
| Rescue-copy | `~/Documents/DangKyKinhDoanh/` | **PASS (AUTO)** — marker rescued khi đóng cửa sổ sạch (rc=0) | — |
| S-privacy | Bundle sạch | **PASS (AUTO)** — không profiles/generated_ho_so/99_muc_luc/docs/app_tk/evidence, không draft/xlsx lạ | — |
| S-viewer | Module trong PYZ | **PASS (AUTO)** — tools.docx_render/excel_export/excel_import/questionnaire.schema/layout_roles, webview.platforms.cocoa, tkinter.filedialog; 0 module test | — |
| S7 | Offline thật | NOT RUN | ngắt wifi thật, lặp S2–S6 |
| S8 | Clean-machine (máy khác) | NOT RUN | máy Mac không Python + Gatekeeper verdict |

Evidence máy dev: `~/Documents/DangKyKinhDoanh/evidence_macos/`
(`macOS_build_manifest.txt`, `macOS_app_inventory_{1,2}.txt`,
`macOS_app_inventory_diff.txt`, `macOS_exec_sha256_{1,2}.txt`,
`macOS_pyz_inventory.txt`, `macOS_S-eng_console.log`,
`engine_probe_out/probe_*.{docx,pdf,xlsx}`, `macOS_codesign_status.txt`,
`macOS_spctl.txt`).

## Khác biệt so với Windows kit (chủ ý)

| Điểm | Windows | macOS |
|---|---|---|
| Build | onefile (extract tạm, xoá khi thoát) | onedir `.app` — bundle còn sau restart (PLAN §7.3) |
| Rescue-copy | lưới an toàn vì extract tạm bị xoá | vẫn cần: generated_ho_so nằm trong `Contents/` (ẩn, vỡ seal khi ký, DMG read-only) → Documents |
| Backend pywebview | `webview.platforms.edgechromium`/`winforms` (WebView2) | `webview.platforms.cocoa` (WKWebView/PyObjC) |
| DevTools | WebView2 có | WKWebView không mở DevTools trực tiếp — kiểm bằng thao tác UI |
| open_dir (Bridge) | `os.startfile` hoạt động | `os.startfile` KHÔNG tồn tại trên macOS → Bridge.open_dir trả `{ok:false}` (app không chết; đã ghi defect cho Lead) |
