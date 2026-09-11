# Branding — logo/icon app "Trợ lý hồ sơ ĐKKD"

> **QUYẾT ĐỊNH OWNER 2026-09-11:** dùng ảnh chân dung cá nhân do owner cung
> cấp làm icon app (đã nâng sáng gamma 0.48 + crop vuông neo đáy 1980px từ
> gốc 2316×3088, EXIF-rotated). Owner xác nhận chấp nhận khuôn mặt xuất hiện
> trong icon bản phát hành.

## Kỷ luật riêng tư (bắt buộc)

- **Ảnh gốc và mọi icon derived KHÔNG được commit vào git** — thư mục
  `local/` nằm trong `.gitignore` (PII: khuôn mặt người thật — kỷ luật
  PLAN.md F6.2/§6.5 và mandate "không commit profile thật/PII").
- Icon derived (`.icns`/`.ico`) chỉ sống local trên máy build và đi vào
  **bundle phát hành** (.app/.exe) — đúng phạm vi owner đã chấp nhận.

## Bố cục local (tự dựng, không commit)

```
tools/branding/local/
├── logo_master_1024.png   master đã xử lý (crop + gamma + contrast + sharp)
├── icon.iconset/          10 kích thước chuẩn Apple
├── dangky_kinhdoanh.icns  macOS (iconutil -c icns)
└── dangky_kinhdoanh.ico   Windows (Pillow, 16→256px)
```

## Tái lập

```bash
# 1) đặt ảnh nguồn (owner giữ, ngoài git) rồi chạy script biến đổi — xem
#    commit message wave(branding) cho đúng tham số: crop side=1980 neo đáy,
#    gamma 0.48 LUT, Contrast 1.06, Sharpness 1.25, resize LANCZOS 1024
# 2) dựng iconset + icns + ico (lệnh trong spec-check của build)
iconutil -c icns tools/branding/local/icon.iconset -o tools/branding/local/dangky_kinhdoanh.icns
# 3) build app — spec tự nhận icon khi file tồn tại
bash tools/macos_handoff/build_app.sh
```

Không có `local/` thì spec build với icon mặc định PyInstaller — build vẫn
XANH, chỉ là không có icon riêng (điều kiện tường minh trong cả 2 spec).
