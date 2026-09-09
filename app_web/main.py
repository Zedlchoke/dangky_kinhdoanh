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
import shutil
import subprocess
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


def _run_soffice(soffice: str, case_id: str, args: list, src_name: str,
                 timeout: int = 60):
    """Chạy MỘT lời gọi soffice với LibreOffice profile CÁCH LY per-call.

    Profile mặc định dùng chung mọi tiến trình: 2 soffice chồng nhau (2
    worktree/2 runner song song) → thằng sau exit=1; run bị kill giữa chừng
    để lại .lock/zombie → MỌI lời gọi sau qua profile mặc định đều exit=1
    (gate đỏ giả 56/1 ngày 2026-09-04). Mỗi call dùng profile riêng
    /tmp/lo_prof_<case_id>_<pid><suffix> (2 run song song → 2 pid → 2
    profile), dọn bằng shutil.rmtree trong try/finally.

    Exit != 0 ở lần 1 → retry ĐÚNG 1 lần với profile mới (suffix khác).
    subprocess.TimeoutExpired vẫn ném ra để call-site xử lý như cũ.

    Trả (returncode, error_message): error_message None khi exit 0; sau
    retry vẫn fail → "LO_PROFILE_BUSY"/"LO_CRASH <file>: stderr=<200 ký tự
    cuối>" — không còn message mơ hồ "soffice exit=1".
    """
    base = _sanitize_name(case_id, "ho_so", 120)
    rc, tail = 1, ""
    for suffix in ("", "_retry"):
        prof = Path("/tmp/lo_prof_%s_%d%s" % (base, os.getpid(), suffix))
        try:
            proc = subprocess.run(
                [soffice, "--headless", "--norestore",
                 "-env:UserInstallation=file://%s" % prof, *args],
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "HOME": os.environ.get("HOME", "/tmp")})
            rc = proc.returncode
            if rc == 0:
                return rc, None
            tail = " ".join(((proc.stderr or "") + " " + (proc.stdout or ""))
                            .split())[-200:]
        finally:
            shutil.rmtree(prof, ignore_errors=True)
    code = ("LO_PROFILE_BUSY"
            if re.search(r"lock|another instance|busy", tail, re.I)
            else "LO_CRASH")
    return rc, "%s %s: stderr=%s" % (code, src_name, tail)


def _nest(data: dict) -> dict:
    """Chuyển key phẳng dạng 'a.b.c' thành dict lồng nhau vì engine render
    (tools/docx_render._lookup) tra cứu theo đường dẫn lồng nhau.

    [wave2-B1] Batch corpus gộp payload phẳng của ~86 form: một prefix có thể
    ĐÃ giữ LIST dòng grid của form khác (vd 'ds_nganh' bảng ngành, 'ds_cshhl'
    PLI_M10/11) trong khi một form khác đóng góp key dotted cùng prefix
    (vd mirror scalar 'ds_nganh.la_nganh_chinh'). Code cũ đè list bằng dict
    → bảng ngành/CSHHL/thành viên mất toàn bộ dòng (finding corpus lớp B).
    Quy tắc mới: node trung gian phi-dict ĐÃ CÓ GIÁ TRỊ được giữ nguyên,
    key dotted trùng prefix bị bỏ qua.

    Trade-off (chọn ít xâm lấn nhất): giá trị scalar dotted bị bỏ trong ca
    xung đột này — dữ liệu từng dòng đã nằm trong list nên bảng không mất
    gì; mirror scalar là đại diện cấp form của chính cột đó. Chỉ breaker
    node phi-dict; dict gặp dict vẫn đi sâu như cũ, và key KHÔNG dotted
    (assignment trực tiếp) vẫn 'người sau thắng' như trước.
    """
    out: dict = {}
    for k, v in data.items():
        parts = str(k).split(".")
        if len(parts) == 1:
            out[k] = v
            continue
        cur = out
        placed = True
        for p in parts[:-1]:
            nxt = cur.get(p)
            if isinstance(nxt, dict):
                cur = nxt
                continue
            if nxt is not None:
                # list/scalar sẵn có ở node trung gian: KHÔNG đè bằng dict
                placed = False
                break
            nxt = {}
            cur[p] = nxt
            cur = nxt
        if placed:
            cur[parts[-1]] = v
    return out


class Bridge:
    """Các method Python mà JS gọi qua window.pywebview.api."""

    # ------------------------------------------------------------- danh mục
    # [Phase 5] Dữ liệu chung app/data mà UI cần qua Bridge. pywebview load
    # UI qua internal server CHỈ phục vụ app_web — fetch('../app/data/..')
    # 404 và UI âm thầm rơi vào mock/vsic_mini.json (15/794 mã, 9 tên sai,
    # thiếu 455 ngành cấp 4) → tên ngành kê khai thiếu/không chính thức
    # (bug owner quan sát Phase 5). Danh sách CHỈ ĐỌC, allowlist cứng:
    # không có route dữ liệu nào khác qua cửa này.
    READ_ONLY_DATA_FILES = ("nganh_vsic.json",)

    def read_data_json(self, name):
        name = str(name or "")
        if name not in self.READ_ONLY_DATA_FILES:
            return {"ok": False, "error": "FILE_NOT_ALLOWED"}
        try:
            with open(APP_DIR / "data" / name, encoding="utf-8") as f:
                return {"ok": True, "name": name, "data": json.load(f)}
        except Exception:
            # không nhúng repr(exception) (F-P3-SEC-LOG)
            return {"ok": False, "error": "READ_FAILED"}

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
            # exist_ok=False: 2 Bridge.export song song cùng case_id trong
            # cùng giây (2 runner / 2 worktree) sinh CÙNG đường dẫn vì ts chỉ
            # chính xác tới giây — mkdir exist_ok=True cũ cho cả 2 ghi CHUNG
            # thư mục: write_rendered đè nhau, _lo_norm bị xoá dưới chân
            # soffice đang chạy → exit=0 mà không có file (tái hiện 2/2 trong
            # test_export_concurrency 2026-09-04). Đụng → nhánh vành đai theo
            # pid; run đơn hoàn toàn không đổi tên.
            out_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            out_dir = ROOT / "generated_ho_so" / (
                "%s_%s_p%d" % (case_id, ts, os.getpid()))
            try:
                # cùng process export 2 lần trong cùng giây → tái dùng như
                # hành vi cũ (tuần tự, không race).
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "errors": [
                    "EXPORT_DIR_CREATE_FAILED: không tạo được thư mục export "
                    "(%s: %s)" % (out_dir.name, type(exc).__name__)]}
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

        # ------------------------------------------------- Word compat + PDF
        # [Owner decision 2026-09-03] Xuất ĐA ĐỊNH DẠNG + Word compat:
        #   payload.format = "docx" | "pdf" | "both" (mặc định both)
        # Bước 1: LO normalize từng .docx (re-save qua LO = fix Word 16.16
        #         "unreadable content" — Class 16, thủ phạm là serialization
        #         của nguồn convert cũ, generator giữ nguyên).
        # Bước 2: LO convert normalized .docx → PDF.
        export_format = str(payload.get("format") or "both").strip().lower()
        if export_format not in ("docx", "pdf", "both"):
            export_format = "both"
        want_pdf = export_format in ("pdf", "both")
        want_docx = export_format in ("docx", "both")
        soffice = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        soffice_ok = Path(soffice).exists() if "/" in soffice else bool(shutil.which("soffice"))

        # Bước 1: LO normalize (fix Class 16 — Word compat)
        # [Phase 5 fix] normalize cũ chạy `--outdir out_dir` TRÙNG thư mục
        # nguồn -> LibreOffice không tự ghi đè file đang convert -> BƯỚC NÀY
        # ÂM THẦM FAIL TỪ ĐẦU (except: pass nuốt lỗi) và Word 16.16 nhận file
        # RAW của write_rendered = "file is corrupt" (đã tái hiện + chụp
        # dialog). Sửa: convert vào thư mục tạm rồi thay file; fail → báo
        # errors[] (không nuốt) vì file không normalize KHÔNG mở được bằng
        # Word 16.16.
        if soffice_ok:
            norm_dir = out_dir / "_lo_norm"
            for name in files:
                src = out_dir / name
                try:
                    shutil.rmtree(norm_dir, ignore_errors=True)
                    norm_dir.mkdir(parents=True, exist_ok=True)
                    _rc, lo_err = _run_soffice(
                        soffice, case_id,
                        ["--convert-to", "docx", "--outdir", str(norm_dir),
                         str(src)],
                        src_name=name)
                    normalized = norm_dir / name
                    if (lo_err is None and normalized.exists()
                            and normalized.stat().st_size > 0):
                        shutil.move(str(normalized), str(src))
                    else:
                        if lo_err is None:
                            lo_err = ("LO_NO_OUTPUT %s: convert exit=0 nhưng "
                                      "không sinh file" % name)
                        errors.append(
                            "%s: LO normalize thất bại (%s) — giữ file gốc, "
                            "Word 16.16 có thể từ chối mở" % (name, lo_err))
                except Exception:
                    errors.append("%s: LO normalize exception — giữ file gốc"
                                  % name)
                finally:
                    shutil.rmtree(norm_dir, ignore_errors=True)

        pdf_files, pdf_errors = [], []
        if want_pdf and not soffice_ok:
            errors.append("PDF_EXPORT_UNAVAILABLE: soffice không tìm thấy — "
                          "chỉ có file .docx" if want_docx else
                          "PDF_EXPORT_UNAVAILABLE: soffice không tìm thấy")
        if want_pdf and soffice_ok:
            for name in files:
                src = out_dir / name
                pdf_name = name.rsplit(".", 1)[0] + ".pdf"
                try:
                    _rc, lo_err = _run_soffice(
                        soffice, case_id,
                        ["--convert-to", "pdf", "--outdir", str(out_dir),
                         str(src)],
                        src_name=pdf_name)
                    pdf_path = out_dir / pdf_name
                    if (lo_err is None and pdf_path.exists()
                            and pdf_path.stat().st_size > 0):
                        pdf_files.append(pdf_name)
                    else:
                        if lo_err is None:
                            lo_err = ("LO_NO_OUTPUT %s: convert exit=0 nhưng "
                                      "không sinh file" % pdf_name)
                        pdf_errors.append(lo_err)
                except Exception as exc:
                    pdf_errors.append("%s: %s: %s" % (pdf_name, type(exc).__name__, _safe_error(exc)))
            if pdf_errors:
                errors.extend(pdf_errors)
        if export_format == "pdf":
            # chỉ PDF: xoá .docx trung gian khỏi thư mục export
            for name in files:
                (out_dir / name).unlink(missing_ok=True)

        zip_path = None
        if files and not errors:
            # ZIP chứa đúng định dạng người dùng chọn
            if export_format == "pdf":
                zip_entries = pdf_files
            elif export_format == "docx":
                zip_entries = files
            else:
                zip_entries = files + pdf_files
            zip_path = str(out_dir.parent / ("%s.zip" % out_dir.name))
            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for name in zip_entries:
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

            # Contract X3: import_questionnaire(path, questionnaire) — path
            # file khách điền TRƯỚC, questionnaire (đã đọc ở trên) sau.
            return import_questionnaire(path, q)
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
