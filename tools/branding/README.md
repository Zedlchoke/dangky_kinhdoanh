# Branding — logo/icon app "Trợ lý hồ sơ ĐKKD"

> **QUYẾT ĐỊNH OWNER 2026-09-11:** dùng hình minh họa owner cung cấp làm icon
> app. Icon Windows tái lập được nằm tại `dangky_kinhdoanh.ico`; asset local
> chỉ giữ bản master/nguồn để chỉnh sửa tiếp.

## Kỷ luật riêng tư (bắt buộc)

- Ảnh gốc và master local nằm trong `local/` và không commit.
- Icon `.ico` phát hành đã được owner chốt và commit để build từ clone mới
  luôn có cùng logo; `.icns` macOS vẫn có thể sinh local trên runner macOS.

## Bố cục local (tự dựng, không commit)

```
tools/branding/local/
├── logo_master_1024.png   master đã xử lý (crop + gamma + contrast + sharp)
├── icon.iconset/          10 kích thước chuẩn Apple
├── dangky_kinhdoanh.icns  macOS (iconutil -c icns)
└── dangky_kinhdoanh.ico   Windows (Pillow, 16→256px)

tools/branding/dangky_kinhdoanh.ico  # asset Windows tracked cho PyInstaller
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
