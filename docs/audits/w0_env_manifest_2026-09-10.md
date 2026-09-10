# W0 — Manifest môi trường render (release audit lane W0)

- Ngày: 2026-09-10
- HEAD: `d7ec0765d11118d216973edbc91ea73ba399b7b9` (branch `main`)
- Lane: W0 audit (manifest môi trường + estate NGOÀI `tools.release_runner`)
- Phạm vi: từng mục ghi kèm lệnh đo thật + output. Word open chỉ ghi nhận
  evidence cũ (corpus `phase9_bandfix_v2`), KHÔNG ký PASS mới.

## 1. Runtime lõi

| Hạng mục | Lệnh đo | Output | Đánh giá |
|---|---|---|---|
| Python | `python3 --version` | `Python 3.13.14` | OK |
| LibreOffice (renderer) | `soffice --version` | `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77` (`which soffice` → `/opt/homebrew/bin/soffice`) | OK |
| Node (js test) | `node --version` | `v24.5.0` | OK — 5 node suite của lane chạy được bằng runtime này |

## 2. Python packages then chốt (import thử từng cái)

Đo bằng `importlib.metadata.version(...)`, mọi package đều import được:

| Package | Version | Pin `requirements-dev.txt` | Đánh giá |
|---|---|---|---|
| python-docx | 1.2.0 | `python-docx==1.2.0` | KHỚP pin |
| openpyxl | 3.1.5 | `openpyxl==3.1.5` | KHỚP pin |
| PyMuPDF | 1.28.2 | `pymupdf==1.28.2` | KHỚP pin |
| lxml | 6.1.1 | `lxml==6.1.1` | KHỚP pin |
| pywebview | 6.2.1 | `pywebview>=5.0` | ĐẠT (>= 5.0) |
| playwright | 1.61.0 | (không pin trong requirements; tiện ích chọn lọc) | CÓ |

Không có package nào MISSING trong danh sách then chốt.

## 3. Microsoft Word (chỉ ghi nhận evidence cũ)

- `ls -d "/Applications/Microsoft Word.app"` → tồn tại.
- `defaults read .../Info.plist CFBundleShortVersionString` → `16.16.27`;
  `CFBundleVersion` → `16.16.20101200`.
- Evidence cũ (không chạy Word open mới trong lane này):
  `generated_ho_so/_visual_layout/phase9_bandfix_v2/word_open/inventory.json`
  — `word_version: 16.16.27`, `generated: 2026-09-09T15:03:00`,
  `elapsed_s: 727.4`, **90/90 record `PASS_OPEN_DIRECT`**.
- Khớp tuyên bố phase9_bandfix_audit §5 ("Word open-direct 16.16.27: 90/90").

## 4. Node runtime cho js test

- `node --version` → `v24.5.0` (đã dùng thật chạy 5 node suite của lane, xem
  báo cáo estate; mọi suite import `app_web/ui/*` bằng `require` chuẩn, không
  cần browser runtime).

## 5. Browser runtime (playwright chromium)

- `p.chromium.executable_path` →
  `~/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`
  — `exists=True`.
- Cache `~/Library/Caches/ms-playwright/` có: `chromium-1228` (khớp playwright
  1.61.0), `chromium-1208`, `chromium_headless_shell-1228`, `ffmpeg-1011`.
- Không suite nào trong lane W0 cần browser runtime; các suite chromium-based
  (nếu có) không bị chặn bởi thiếu browser.

## 6. Kết luận W0

- **LibreOffice renderer: SẴN SÀNG.** `soffice` 26.8.0.3 khả dụng trên PATH;
  toàn bộ pin Python khớp `requirements-dev.txt`; Word 16.16.27 vẫn nằm ở đúng
  version của evidence corpus v2.
- **Không còn suite nào phụ thuộc môi trường thiếu** trong phạm vi estate đã
  chạy bởi lane (node + python-docx + census): mọi dependency đều có mặt.
- Suite pin version: `test_excel_export` có check `openpyxl==3.1.5` trong
  `requirements-dev.txt` — env đang khớp (25/25 PASS).
