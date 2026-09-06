# -*- coding: utf-8 -*-
"""launch_app_web.py — entry script cho PyInstaller (F6/O6 handoff).

Vì sao cần file này: app_web/main.py tính MỌI đường dẫn (ROOT, APP_DIR,
generated_ho_so, ui/index.html) từ __file__ của chính nó. Khi đóng băng
onefile, bootloader PyInstaller đặt __file__ của entry script tại
<_MEIPASS>/<ten_entry>.py (tầng GỐC của thư mục extract), nên nếu dùng thẳng
app_web/main.py làm entry thì ROOT trỏ ra NGOÀI bundle -> app/ và
app_web/ui/ không tồn tại ở đó -> app chết lúc mở hồ sơ.

Launcher này chạy lại BẢN main.py đã bundle kèm đúng __file__
(<_MEIPASS>/app_web/main.py) để mọi đường dẫn khớp layout repo như khi chạy
từ source. Không sửa app_web/main.py (quy tắc wave: chỉ thêm file mới).

Hành vi phụ (chỉ khi frozen): nếu app ghi generated_ho_so/ vào thư mục
extract tạm (onefile xoá thư mục này khi thoát), launcher sao chép khẩn
sang %USERPROFILE%\\Documents\\DangKyKinhDoanh\\generated_ho_so trước khi
process đóng. Không bao giờ raise — chỉ in cảnh báo.

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
        # onedir: file exe nằm cạnh thư mục _internal (PyInstaller >= 6)
        return Path(sys.executable).resolve().parent
    # tools/windows_handoff/launch_app_web.py -> root repo là 3 cấp trên
    return Path(__file__).resolve().parent.parent.parent


def _rescue_generated_ho_so(base: Path) -> None:
    """Copy generated_ho_so ra chỗ bền trước khi onefile dọn thư mục extract.

    Chỉ chạy khi frozen (chạy source thì generated_ho_so vốn đã ở repo,
    không cần copy). Mọi lỗi bỏ qua — đây là lưới an toàn, không phải luồng
    chính; người chạy vẫn phải MỞ THƯ MỤC và chép file ra ngay trong phiên
    làm việc theo README (mục S6).
    """
    if not getattr(sys, "frozen", False):
        return
    src = base / "generated_ho_so"
    if not src.is_dir():
        return
    user_home = os.environ.get("USERPROFILE") or str(Path.home())
    dst_root = Path(user_home) / "Documents" / "DangKyKinhDoanh" / "generated_ho_so"
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
            print("DA CUU HO SO tu thu muc tam sang: %s (%d muc)"
                  % (dst_root, copied))
    except Exception as exc:  # noqa: BLE001 — lưới an toàn không được raise
        print("CANH BAO: khong rescue duoc generated_ho_so (%s: %s). "
              "Neu ban da export trong phien nay, file co the mat khi dong app."
              % (type(exc).__name__, exc))


def main() -> int:
    base = _bundle_base()
    target = base / "app_web" / "main.py"
    if not target.exists():
        print("Khong tim thay bundle app_web/main.py tai: %s" % target)
        print("Build phai bundle app_web/main.py + app_web/ui/ + app/ "
              "(xem tools/windows_handoff/dangky_kinhdoanh.spec).")
        return 2
    # app_web/main.py dùng sys.argv[0] và sys.argv[1:] (--mock); giữ nguyên
    # tham số người dùng, chỉ trỏ argv[0] về bản bundle cho log đúng chỗ.
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
