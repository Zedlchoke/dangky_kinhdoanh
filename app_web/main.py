"""Khởi chạy cửa sổ desktop pywebview (Edge WebView2) cho giao diện web ĐKKD.

Chạy:  python app_web/main.py
       python app_web/main.py --mock   (mở thẳng chế độ dữ liệu mock)

Bridge (window.pywebview.api trong JS):
- list_cases()                  -> nội dung app/data/use_cases.json
- get_blocks(json_ids)          -> {docs:{id:block_json}, errors:{id:msg}}
                                  đọc app/data/blocks/<id>.json (do converter sinh)
- load_draft()                  -> dialog mở .json, trả {ok,path,draft}
- save_draft(payload_str)       -> dialog lưu .json, trả {ok,path}
- export(payload)               -> render .docx bằng tools/docx_render, ZIP,
                                  trả {ok,files,errors,dir,zip}
- open_dir(path)                -> mở thư mục bằng Explorer

Không đụng tools/*, app_tk/*, app/data/* (chỉ đọc).
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"

# Thư viện pywebview được chở sẵn trong .webview_deps — phải thêm vào path
# TRƯỚC khi import webview.
sys.path.insert(0, str(ROOT / ".webview_deps"))
sys.path.insert(0, str(ROOT))

try:
    import webview  # noqa: E402
except Exception as exc:  # noqa: BLE001
    print("KHONG khoi dong duoc pywebview:", exc)
    print("Da them '%s' vao sys.path nhung import webview that bai." % (ROOT / ".webview_deps"))
    traceback.print_exc()
    sys.exit(1)


def _as_dict(obj):
    """pywebview có thể truyền chuỗi JSON hoặc dict tuỳ phiên bản."""
    if isinstance(obj, str):
        return json.loads(obj)
    return obj


def _nest(data: dict) -> dict:
    """Chuyển key phẳng dạng 'a.b.c' thành dict lồng nhau vì engine render
    (tools/docx_render._lookup) tra cứu theo đường dẫn lồng nhau."""
    out: dict = {}
    for k, v in data.items():
        parts = str(k).split(".")
        if len(parts) == 1:
            out[k] = v
            continue
        cur = out
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = v
    return out


class Bridge:
    """Các method Python mà JS gọi qua window.pywebview.api."""

    # ------------------------------------------------------------- danh mục
    def list_cases(self):
        with open(APP_DIR / "data" / "use_cases.json", encoding="utf-8") as f:
            return json.load(f)

    def get_blocks(self, ids):
        ids = _as_dict(ids)
        if isinstance(ids, str):  # một id đơn lẻ
            ids = [ids]
        docs, errors = {}, {}
        for fid in ids:
            p = APP_DIR / "data" / "blocks" / ("%s.json" % fid)
            try:
                with open(p, encoding="utf-8") as f:
                    docs[fid] = json.load(f)
            except FileNotFoundError:
                errors[fid] = "không tìm thấy %s" % p
            except Exception as exc:  # noqa: BLE001
                errors[fid] = "lỗi đọc blocks: %r" % (exc,)
        return {"docs": docs, "errors": errors}

    # ---------------------------------------------------------------- nháp
    def load_draft(self):
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Mở hồ sơ đã lưu",
            filetypes=[("Hồ sơ JSON", "*.json"), ("Tất cả file", "*.*")],
            parent=root,
        )
        root.destroy()
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            with open(path, encoding="utf-8") as f:
                return {"ok": True, "path": path, "draft": json.load(f)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}

    def save_draft(self, payload):
        payload = _as_dict(payload)
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            title="Lưu hồ sơ",
            defaultextension=".json",
            initialfile="ho_so_dkkd.json",
            filetypes=[("Hồ sơ JSON", "*.json")],
            parent=root,
        )
        root.destroy()
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            return {"ok": True, "path": path}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}

    # ---------------------------------------------------------------- xuất
    def export(self, payload):
        payload = _as_dict(payload)
        case_id = str(payload.get("case_id") or "ho_so")
        forms = payload.get("forms") or []
        data = _nest(payload.get("data") or {})

        try:
            with open(APP_DIR / "data" / "form_maps.json", encoding="utf-8") as f:
                maps = json.load(f)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "errors": ["không đọc được form_maps.json: %r" % (exc,)]}

        ts = time.strftime("%Y%m%d_%H%M%S")
        out_dir = ROOT / "generated_ho_so" / ("%s_%s" % (case_id, ts))
        out_dir.mkdir(parents=True, exist_ok=True)

        # import engine render từ thư mục gốc dự án
        from tools.docx_render import write_rendered  # noqa: E402

        files, errors = [], []
        for form in forms:
            fid = form.get("id") if isinstance(form, dict) else str(form)
            fmap = maps.get(fid)
            if not fmap:
                errors.append("%s: không có trong form_maps.json" % fid)
                continue
            template = APP_DIR / fmap["template"]
            out_file = out_dir / ("%s.docx" % fid)
            try:
                write_rendered(template, data, out_file)
                files.append(out_file.name)
            except Exception as exc:  # noqa: BLE001
                errors.append("%s: lỗi render %r" % (fid, exc))

        zip_path = None
        if files and not errors:
            zip_path = str(out_dir.parent / ("%s.zip" % out_dir.name))
            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for name in files:
                        z.write(out_dir / name, name)
            except Exception as exc:  # noqa: BLE001
                errors.append("lỗi nén ZIP: %r" % (exc,))
                zip_path = None

        if not files and errors:
            return {"ok": False, "files": [], "errors": errors,
                    "dir": str(out_dir), "zip": None}
        return {"ok": len(errors) == 0, "files": files, "errors": errors,
                "dir": str(out_dir), "zip": zip_path}

    def open_dir(self, path):
        try:
            os.startfile(str(path))  # Windows Explorer
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}


def main() -> int:
    url = str(Path(__file__).resolve().parent / "ui" / "index.html")
    if "--mock" in sys.argv[1:]:
        url += "?mock=1"
    bridge = Bridge()
    webview.create_window(
        "Trợ lý hồ sơ ĐKKD",
        url=url,
        js_api=bridge,
        width=1200,
        height=850,
    )
    try:
        webview.start()
    except Exception as exc:  # noqa: BLE001
        print("Loi khoi dong cua so webview (can Edge WebView2 runtime):", exc)
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
