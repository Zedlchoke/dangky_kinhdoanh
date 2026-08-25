# -*- coding: utf-8 -*-
"""Đồng bộ mock blocks của web UI từ dữ liệu production (app/data/blocks).

Copy app/data/blocks/<ID>.json -> app_web/ui/mock/blocks_<ID>.json cho các
mẫu dùng ở chế độ ?mock=1 và test node. Chạy:
    python -X utf8 tools/sync_mock_blocks.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IDS = ["PLI_M02", "PLI_M06", "PLII_M01"]


def main():
    src_dir = os.path.join(ROOT, "app", "data", "blocks")
    dst_dir = os.path.join(ROOT, "app_web", "ui", "mock")
    os.makedirs(dst_dir, exist_ok=True)
    for doc_id in IDS:
        src = os.path.join(src_dir, doc_id + ".json")
        dst = os.path.join(dst_dir, "blocks_" + doc_id + ".json")
        shutil.copyfile(src, dst)
        print("synced %s -> %s" % (src, os.path.relpath(dst, ROOT)))


if __name__ == "__main__":
    main()
