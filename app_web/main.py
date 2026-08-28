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
- export_questionnaire(payload) -> xuất phiếu Excel cho khách
                                  (tools/excel_export): {ok,path} |
                                  {ok:False,cancelled} | {ok:False,errors:[…]}
- import_questionnaire(payload) -> nạp phiếu Excel khách điền
                                  (tools/excel_import): {ok,errors,data}
- open_dir(path)                -> mở thư mục bằng Explorer

Không đụng tools/*, app_tk/*, app/data/* (chỉ đọc).
"""

from __future__ import annotations

import json
import os
import re
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


# Ký tự điều khiển (NUL, BEL, ESC, …) không được nằm trong tên thư mục/file.
_NAME_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize_name(value, fallback: str = "ho_so", limit: int = 255) -> str:
    """Làm sạch tên lấy từ payload trước khi ghép vào đường dẫn export.

    `case_id` và `forms[].id` đến thẳng từ Bridge nên KHÔNG được tin:
    '../x' hoặc '..\\x' ghi thoát ra ngoài generated_ho_so, NUL/ký tự điều
    khiển làm mkdir ném exception (ValueError: embedded null character),
    tên quá dài vượt giới hạn filesystem (OSError: File name too long).
    Quy tắc: '/' và '\\' coi là phân cách và thay bằng '_', bỏ segment
    rỗng/'.',/'..', bỏ ký tự điều khiển, rút gọn còn tối đa `limit` byte
    UTF-8 (không cắt giữa codepoint, bỏ surrogate không mã hoá được).
    Kết quả rỗng -> dùng `fallback`. Tên hợp lệ giữ nguyên 100%.
    """
    text = "_".join(p for p in re.split(r"[/\\]+", str(value or ""))
                    if p not in ("", ".", ".."))
    text = _NAME_CTRL_RE.sub("", text).strip()
    if not text:
        return fallback
    safe = text.encode("utf-8", "ignore")[:limit].decode("utf-8", "ignore")
    return safe.strip() or fallback


def _safe_error(exc: BaseException, limit: int = 160) -> str:
    """Message lỗi an toàn để trả về UI: một dòng, đã cắt ngắn, KHÔNG repr.

    Dùng repr() (hoặc str() chưa lọc) của exception khi đưa vào errors[] là
    có thể lộ giá trị người dùng (F-P3-SEC-LOG) — Bridge chỉ trả loại lỗi và
    message đã lọc; mã lỗi/row của ExportTotalsError vẫn giữ để debug.
    """
    text = " ".join(str(exc).split())
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text or type(exc).__name__


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
        # case_id là giá trị người dùng: phải sanitize TRƯỚC khi ghép đường
        # dẫn (F-P3-SEC-PATH). `limit` để dành 16 byte cho đuôi "_%Y%m%d_%H%M%S"
        # nên "%s_%s" không bao giờ vượt giới hạn 255 byte của filesystem.
        case_id = _sanitize_name(case_id, "ho_so", 255 - 1 - len(ts))
        out_dir = ROOT / "generated_ho_so" / ("%s_%s" % (case_id, ts))
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            # không để exception (đĩa đầy, tên lạ, quyền…) bay ra ngoài Bridge
            return {"ok": False, "errors": [
                "EXPORT_DIR_CREATE_FAILED: không tạo được thư mục export "
                "(%s: %s)" % (out_dir.name, type(exc).__name__)]}

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
            # sanitize CHỈ phần dùng để đặt tên file; key tra cứu maps ở trên
            # giữ nguyên id gốc (fid lạ phải rơi vào nhánh errors như cũ).
            out_file = out_dir / ("%s.docx" % _sanitize_name(fid, "form", 250))
            try:
                # R2: section_specs (metadata bảng kind mới) -> recompute tổng
                # lúc export, fail-loud nếu stored lệch computed. Form không có
                # specs giữ hành vi cũ.
                write_rendered(template, data, out_file,
                               tables_meta=(fmap.get("section_specs") or None))
                files.append(out_file.name)
            except Exception as exc:  # noqa: BLE001
                # KHÔNG nhúng repr(exception) vào errors[] trả về UI: message
                # gốc có thể mang giá trị người dùng (F-P3-SEC-LOG) — chỉ trả
                # loại lỗi + message đã lọc.
                errors.append("%s: lỗi render %s: %s"
                              % (fid, type(exc).__name__, _safe_error(exc)))

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

    # ------------------------------------------------- phiếu Excel (X5)
    def _questionnaire_path(self, payload) -> tuple[str, Path]:
        """doc_id từ payload -> đường dẫn questionnaire JSON tương ứng.

        doc_id đến thẳng từ Bridge nên KHÔNG được tin: ghép đường dẫn qua
        _sanitize_name để '../x' không đọc thoát ra ngoài app/data (F-P3-SEC-PATH),
        id hợp lệ giữ nguyên 100% nên tra cứu thật không bị ảnh hưởng.
        """
        payload = _as_dict(payload) or {}
        doc_id = _sanitize_name(str(payload.get("doc_id") or ""), "form", 120)
        return doc_id, APP_DIR / "data" / "questionnaire" / ("%s.json" % doc_id)

    def export_questionnaire(self, payload):
        """Xuất phiếu Excel thu thập thông tin khách cho MỘT thủ tục.

        payload: {doc_id, case_id?}. Hỏi chỗ lưu (dialog .xlsx), đọc lớp
        questionnaire của thủ tục rồi gọi tools/excel_export.write_questionnaire.
        Không đụng draft/store: xuất là đường một chiều sang file cho khách.
        """
        payload = _as_dict(payload) or {}
        doc_id, q_path = self._questionnaire_path(payload)
        if not q_path.exists():
            return {"ok": False, "errors": [{"code": "NO_QUESTIONNAIRE",
                    "message": "Chưa có phiếu câu hỏi cho thủ tục này."}]}
        try:
            with open(q_path, encoding="utf-8") as f:
                q = json.load(f)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "errors": [{"code": "NO_QUESTIONNAIRE",
                    "message": "không đọc được phiếu câu hỏi (%s: %s)"
                               % (type(exc).__name__, _safe_error(exc))}]}

        import tkinter as tk
        from tkinter import filedialog

        case_id = _sanitize_name(str(payload.get("case_id") or ""), "phieu_excel", 80)
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            title="Xuất phiếu Excel cho khách",
            defaultextension=".xlsx",
            initialfile="%s.xlsx" % case_id,
            filetypes=[("Phiếu Excel", "*.xlsx"), ("Tất cả file", "*.*")],
            parent=root,
        )
        root.destroy()
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            # import bên trong hàm như Bridge.export làm với docx_render: module
            # chỉ cần openpyxl khi dùng phiếu Excel, không chặn khởi động app.
            from tools.excel_export import write_questionnaire  # noqa: E402

            write_questionnaire(q, path, meta={
                "case_id": str(payload.get("case_id") or ""),
                "today": time.strftime("%d/%m/%Y"),
            })
            return {"ok": True, "path": str(path)}
        except Exception as exc:  # noqa: BLE001
            # KHÔNG nhúng repr(exception): message gốc có thể mang giá trị người
            # dùng (F-P3-SEC-LOG) — chỉ trả loại lỗi + message đã lọc.
            return {"ok": False, "errors": [{"code": "EXPORT_FAILED",
                    "message": "%s: %s" % (type(exc).__name__, _safe_error(exc))}]}

    def import_questionnaire(self, payload):
        """Nạp phiếu Excel khách đã điền cho thủ tục đang mở.

        payload: {doc_id} bắt buộc (UI luôn biết thủ tục đang mở) — lớp
        questionnaire cần thiết để excel_import dịch question_id -> data_key.
        Trả thẳng {"ok", "errors", "data"} của tools/excel_import; ok=false thì
        UI KHÔNG đụng store (draft hiện tại giữ nguyên — yêu cầu X3).
        """
        payload = _as_dict(payload) or {}
        doc_id, q_path = self._questionnaire_path(payload)
        if not q_path.exists():
            return {"ok": False, "errors": [{"code": "NO_QUESTIONNAIRE",
                    "message": "Chưa có phiếu câu hỏi cho thủ tục này."}]}
        try:
            with open(q_path, encoding="utf-8") as f:
                q = json.load(f)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "errors": [{"code": "NO_QUESTIONNAIRE",
                    "message": "không đọc được phiếu câu hỏi (%s: %s)"
                               % (type(exc).__name__, _safe_error(exc))}]}

        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Nạp phiếu Excel",
            filetypes=[("Phiếu Excel", "*.xlsx"), ("Tất cả file", "*.*")],
            parent=root,
        )
        root.destroy()
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            from tools.excel_import import import_questionnaire  # noqa: E402

            return import_questionnaire(q, path)
        except Exception as exc:  # noqa: BLE001
            # module excel_import tự trả lỗi có cấu trúc; nhánh này chỉ còn lại
            # lỗi bất thường của chính Bridge (không ném exception ra webview).
            return {"ok": False, "errors": [{"code": "IMPORT_FAILED",
                    "message": "%s: %s" % (type(exc).__name__, _safe_error(exc))}]}

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
