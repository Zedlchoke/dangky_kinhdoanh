"""Gói giao diện desktop Tkinter cho trợ lý đăng ký kinh doanh.

Chạy ứng dụng:  python run_app.py   (ở thư mục gốc dự án)
"""

from __future__ import annotations

import sys


def main() -> int:
    """Khởi tạo cửa sổ chính và chạy vòng lặp Tkinter."""
    # Import muộn để `import app_tk` thuần không cần tạo cửa sổ
    from .ui_wizard import App

    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
