# -*- coding: utf-8 -*-
"""launch_app_web.py — entry script PyInstaller cho macOS .app (wave P1).

Tương tự tools/windows_handoff/launch_app_web.py: app_web/main.py tính MỌI
đường dẫn (ROOT, APP_DIR, generated_ho_so, ui/index.html) từ __file__ của
chính nó. Khi đóng băng, bootloader đặt __file__ của entry tại tầng gốc
của bundle (_MEIPASS), nên nếu dùng thẳng app_web/main.py làm entry thì
ROOT trỏ sai -> app/ và app_web/ui/ không tồn tại ở đó.

Launcher này chạy lại BẢN main.py đã bundle kèm đúng __file__
(<_MEIPASS>/app_web/main.py) để mọi đường dẫn khớp layout repo như khi chạy
từ source. KHÔNG sửa app_web/main.py (ràng buộc wave P1).

Khác biệt so với Windows (lý do):
- onedir macOS: bundle KHÔNG bị xoá khi thoát (khác onefile Windows), nhưng
  ROOT/generated_ho_so nằm TRONG DangKyKinhDoanh.app/Contents/Frameworks —
  (a) dễ bị bỏ sót vì ẩn trong Contents/, (b) vỡ seal codesign nếu có ký,
  (c) chạy từ DMG read-only thì không ghi được. Vì vậy vẫn rescue-copy
  generated_ho_so sang ~/Documents/DangKyKinhDoanh/generated_ho_so khi app
  đóng (idempotent, không ghi đè, không bao giờ raise).
- Chế độ engine-probe chỉ cho smoke structural (S-eng): biến môi trường
  DKKD_ENGINE_PROBE trỏ tới script .py — launcher chạy script đó BÊN TRONG
  môi trường frozen (import tools.docx_render … từ PYZ của bundle) thay vì
  mở GUI. Không set biến -> app mở GUI bình thường. Chỉ bật khi frozen.

Chạy từ source (dev) cũng được: base = repo root, chạy lại app_web/main.py
giống hệt `python app_web/main.py`.
"""
from __future__ import annotations

import os
import runpy
import shutil
import sys
from pathlib import Path


def _bundle_base() -> Path:
    """Thư mục chứa app_web/ : _MEIPASS khi frozen, repo root khi chạy source."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass)
        # onedir (PyInstaller >= 6, macOS): thư mục _internal nằm cạnh
        # executable trong Contents/MacOS — dự phòng nếu _MEIPASS vắng.
        return Path(sys.executable).resolve().parent
    # tools/macos_handoff/launch_app_web.py -> root repo là 3 cấp trên
    return Path(__file__).resolve().parent.parent.parent


def _rescue_generated_ho_so(base: Path) -> None:
    """Copy generated_ho_so trong bundle ra ~/Documents/DangKyKinhDoanh.

    Chỉ chạy khi frozen (chạy source thì generated_ho_so vốn đã ở repo).
    Idempotent: item đã tồn tại ở đích thì bỏ qua (không ghi đè). Mọi lỗi
    bỏ qua — lưới an toàn không được raise.
    """
    if not getattr(sys, "frozen", False):
        return
    src = base / "generated_ho_so"
    if not src.is_dir():
        return
    dst_root = Path.home() / "Documents" / "DangKyKinhDoanh" / "generated_ho_so"
    try:
        dst_root.mkdir(parents=True, exist_ok=True)
        copied = 0
        for child in src.iterdir():
            dst = dst_root / child.name
            if dst.exists():
                continue  # idempotent: không ghi đè lần rescue trước
            if child.is_dir():
                shutil.copytree(child, dst)
            else:
                shutil.copy2(child, dst)
            copied += 1
        if copied:
            print("DA CUU HO SO tu bundle sang: %s (%d muc)"
                  % (dst_root, copied))
    except Exception as exc:  # noqa: BLE001 — lưới an toàn không được raise
        print("CANH BAO: khong rescue duoc generated_ho_so (%s: %s). "
              "File export van con trong bundle tai: %s"
              % (type(exc).__name__, exc, src))


def _engine_probe() -> int:
    """Chạy script probe BÊN TRONG môi trường frozen (smoke structural).

    DKKD_ENGINE_PROBE=<đường dẫn script>. Script được runpy với run_name
    '__main__' nên có thể import tools.* từ PYZ của bundle. Exit code của
    script (SystemExit) được truyền thẳng. Chỉ chấp nhận khi frozen để
    không biến thành backdoor khi chạy từ source.
    """
    probe = os.environ.get("DKKD_ENGINE_PROBE") or ""
    probe_path = Path(probe).expanduser()
    if not probe or not probe_path.is_file():
        print("DKKD_ENGINE_PROBE khong tro toi file hop le: %r" % probe)
        return 2
    try:
        runpy.run_path(str(probe_path), run_name="__main__")
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    return 0


def main() -> int:
    base = _bundle_base()

    # Engine probe (smoke structural): chạy code bên trong bundle frozen.
    if getattr(sys, "frozen", False) and os.environ.get("DKKD_ENGINE_PROBE"):
        return _engine_probe()

    target = base / "app_web" / "main.py"
    if not target.exists():
        print("Khong tim thay bundle app_web/main.py tai: %s" % target)
        print("Build phai bundle app_web/main.py + app_web/ui/ + app/ "
              "(xem tools/macos_handoff/dangky_kinhdoanh_mac.spec).")
        return 2
    # app_web/main.py đọc --mock từ sys.argv[1:] và dùng sys.argv[0] cho log;
    # giữ nguyên tham số người dùng, chỉ trỏ argv[0] về bản bundle.
    sys.argv = [str(target)] + sys.argv[1:]
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:  # main.py kết thúc bằng sys.exit(main())
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    finally:
        _rescue_generated_ho_so(base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
