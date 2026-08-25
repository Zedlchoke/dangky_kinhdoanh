"""Khởi chạy ứng dụng desktop Trợ lý đăng ký kinh doanh.

Chạy:  python run_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bảo đảm nạp được app_tk/ và tools/ khi chạy từ bất kỳ thư mục nào
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_tk

if __name__ == "__main__":
    sys.exit(app_tk.main())
