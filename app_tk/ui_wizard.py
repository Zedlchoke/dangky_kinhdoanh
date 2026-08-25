"""Cửa sổ chính 3 bước: chọn trường hợp -> nhập thông tin -> xuất hồ sơ."""

from __future__ import annotations

import datetime
import os
import queue
import sys
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Cho phép nạp tools.docx_render khi chạy từ thư mục gốc dự án
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from tools.docx_render import render as render_docx  # noqa: E402

from . import engine_io as eio  # noqa: E402
from . import fields as fld  # noqa: E402
from .document_view import DocumentView, VarBag, collect_from_map  # noqa: E402
from .widgets import CHK, ChkFieldGroup, DynamicTableEditor, ScrollableFrame  # noqa: E402

# Gợi ý trường "bắt buộc" dùng cho cảnh báo (heuristic theo tên key)
REQUIRED_KEY_HINTS = (
    "ho_ten", "ten_tieng_viet", "ten_doanh_nghiep",
    "ma_so_dn", "ma_so_thue", "so_cccd", "co_quan_dkkd",
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trợ lý đăng ký kinh doanh — Xuất biểu mẫu .docx")
        self.geometry("1100x700")
        self.minsize(950, 600)

        # Dữ liệu đọc-chỉ
        self.uc = eio.load_use_cases()
        self.maps = eio.load_form_maps()
        eio.load_nganh_vsic()  # nạp danh mục ngành 1 lần khi khởi động
        self.cases = self.uc.get("cases", [])
        self.groups = sorted({c.get("nhom", "") for c in self.cases})

        # Trạng thái phiên làm việc
        self.case = None              # case đang chọn
        self.case_forms = []          # list dict từ forms_of_case()
        self.form_vars = {}           # map_id -> tk.BooleanVar (chọn mẫu xuất)
        self.bag = VarBag(on_change=self.schedule_autosave)  # kho StringVar trung tâm theo key
        self.var_owner = {}           # key -> "shared" | map_id (phục vụ lưu hồ sơ)
        self.chk_clusters = []        # các cụm chk đã đăng ký (lưu/mở hồ sơ)
        self.loop_rows = {}           # (map_id, loop) -> list[dict] — nguồn sự thật bảng lặp
        self.loop_editors = {}        # (map_id, loop) -> editor đang hiển thị
        self.doc_sections = []        # [{fmap, head, content, view, btn, open, built}]
        self._doc_build_queue = []    # các section chờ dựng lazy (1 mẫu/lượt idle)
        self._doc_build_job = None    # id after() của chuỗi dựng lazy
        self.form_choices = []        # [(nhãn, fmap, bat_buoc)] các mẫu đã tick

        self._autosave_job = None     # id after() của debounce autosave
        self._render_queue = queue.Queue()
        self._rendering = False       # cờ đang render (điều khiển vòng poll)

        self._build_menu()
        self._build_tabs()
        self._select_first_group()

    # ------------------------------------------------------------------
    # Khung giao diện chung
    # ------------------------------------------------------------------
    def _build_menu(self):
        m = tk.Menu(self)
        menu_hs = tk.Menu(m, tearoff=0)
        menu_hs.add_command(label="Lưu hồ sơ...", command=self.save_profile_as)
        menu_hs.add_command(label="Mở hồ sơ...", command=self.open_profile)
        menu_hs.add_separator()
        menu_hs.add_command(label="Nhập lại từ đầu", command=self.reset_case)
        menu_hs.add_separator()
        menu_hs.add_command(label="Thoát", command=self.destroy)
        m.add_cascade(label="Hồ sơ", menu=menu_hs)
        self.config(menu=m)

    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # Bước 1 — chọn trường hợp
        self.tab_case = ttk.Frame(self.nb)
        self.nb.add(self.tab_case, text="1. Chọn trường hợp")

        # Bước 2 — nhập thông tin
        self.tab_input = ttk.Frame(self.nb)
        self.nb.add(self.tab_input, text="2. Nhập thông tin")

        # Bước 3 — xuất hồ sơ
        self.tab_export = ttk.Frame(self.nb)
        self.nb.add(self.tab_export, text="3. Xuất hồ sơ")

        self._build_tab_case()
        self._build_tab_input()
        self._build_tab_export()

    # ------------------------------------------------------------------
    # Bước 1: chọn nhóm -> trường hợp -> xem chi tiết + tick mẫu
    # ------------------------------------------------------------------
    def _build_tab_case(self):
        pw = ttk.PanedWindow(self.tab_case, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(pw)
        pw.add(left, weight=1)

        ttk.Label(left, text="Nhóm nghiệp vụ").pack(anchor="w")
        self.lb_groups = tk.Listbox(left, exportselection=False, height=12)
        self.lb_groups.pack(fill="both", expand=True)
        for g in self.groups:
            self.lb_groups.insert("end", g)
        self.lb_groups.bind("<<ListboxSelect>>", lambda e: self._on_group_select())

        ttk.Label(left, text="Trường hợp").pack(anchor="w")
        self.lb_cases = tk.Listbox(left, exportselection=False)
        self.lb_cases.pack(fill="both", expand=True)
        self.lb_cases.bind("<<ListboxSelect>>", lambda e: self._on_case_select())

        right = ScrollableFrame(pw)
        pw.add(right, weight=3)
        d = right.inner

        self.lbl_case_title = ttk.Label(d, font=("", 13, "bold"))
        self.lbl_case_title.pack(anchor="w", pady=(4, 2))
        self.lbl_case_desc = ttk.Label(d, wraplength=640, justify="left")
        self.lbl_case_desc.pack(anchor="w", pady=(0, 8))

        ttk.Label(d, text="Mẫu biểu sẽ xuất (tick để chọn):", font=("", 10, "bold")).pack(anchor="w")
        self.frame_forms = ttk.Frame(d)
        self.frame_forms.pack(fill="x", pady=2)

        for title, attr in (
            ("Giấy tờ nộp kèm", "txt_giay_to"),
            ("Cơ sở pháp lý", "txt_phap_ly"),
            ("Lưu ý", "txt_luu_y"),
        ):
            ttk.Label(d, text=title + ":", font=("", 10, "bold")).pack(anchor="w", pady=(8, 0))
            txt = tk.Text(d, height=4, wrap="word", relief="flat", background="#f5f5f5")
            txt.pack(fill="x")
            txt.config(state="disabled")
            setattr(self, attr, txt)

    def _selected_group(self):
        sel = self.lb_groups.curselection()
        return self.groups[sel[0]] if sel else None

    def _select_first_group(self):
        if self.groups:
            self.lb_groups.selection_set(0)
            self._on_group_select()

    def _on_group_select(self):
        g = self._selected_group()
        self.lb_cases.delete(0, "end")
        for c in self.cases:
            if c.get("nhom", "") == g:
                self.lb_cases.insert("end", c["ten"])
        if self.lb_cases.size():
            self.lb_cases.selection_set(0)
            self._on_case_select()

    def _on_case_select(self):
        sel = self.lb_cases.curselection()
        if not sel:
            return
        self.case = next(c for c in self.cases if c.get("nhom", "") == self._selected_group()
                         and c["ten"] == self.lb_cases.get(sel[0]))
        self.case_forms = [f for f in eio.forms_of_case(self.case, self.maps)]

        self.lbl_case_title.config(text=self.case["ten"])
        self.lbl_case_desc.config(text=self.case.get("mo_ta", ""))

        # Danh sách mẫu biểu dạng checkbox
        for child in self.frame_forms.winfo_children():
            child.destroy()
        self.form_vars = {}
        for f in self.case_forms:
            var = tk.BooleanVar(value=bool(f["bat_buoc"]))
            self.form_vars[f["map_id"]] = var
            ten_mau = f["map"]["ten_mau"] if f["map"] else "(thiếu form map %s)" % f["map_id"]
            prefix = "PL %s — Mẫu %02d" % (f["pl"], f["mau"])
            star = " [BẮT BUỘC]" if f["bat_buoc"] else ""
            cb = tk.Checkbutton(
                self.frame_forms,
                text="%s%s\n   %s%s" % (prefix, star, ten_mau,
                                        (" — " + f["ghi_chu"]) if f["ghi_chu"] else ""),
                variable=var, anchor="w", justify="left",
            )
            cb.pack(fill="x", pady=1)

        def fill(txt_widget, items):
            txt_widget.config(state="normal")
            txt_widget.delete("1.0", "end")
            for i, it in enumerate(items or [], 1):
                txt_widget.insert("end", ("• %s\n" if i > 1 else "%s\n") % it)
            txt_widget.config(state="disabled")

        fill(self.txt_giay_to, self.case.get("giay_to_kem"))
        fill(self.txt_phap_ly, self.case.get("co_so_phap_ly"))
        fill(self.txt_luu_y, self.case.get("luu_y"))

        # Đổi case: xóa trắng kho dữ liệu trung tâm rồi nạp hồ sơ nháp (nếu có)
        self.bag.clear()
        self.var_owner = {}
        self.chk_clusters = []
        self.loop_rows = {}
        self.doc_sections = []
        self._doc_build_queue = []
        self._doc_build_job = None

        # Nạp hồ sơ nháp của case này nếu có
        draft = eio.load_json(eio.draft_path(self.case["id"]))
        self._rebuild_input_tab()
        if draft:
            self.apply_profile(draft)
            self.set_status_b3("Đã nạp hồ sơ nháp tự động: profiles/%s_draft.json" % self.case["id"])

    # ------------------------------------------------------------------
    # Bước 2: "Điền trực tiếp lên biểu mẫu" (mặc định) / Danh sách trường
    # ------------------------------------------------------------------
    def _build_tab_input(self):
        bar = ttk.Frame(self.tab_input)
        bar.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(bar, text="Kiểu điền:").pack(side="left")
        self.mode_combo = ttk.Combobox(
            bar, state="readonly", width=16,
            values=("Trên bản mẫu", "Danh sách trường"),
        )
        self.mode_combo.current(0)
        self.mode_combo.pack(side="left", padx=(2, 12))
        self.mode_combo.bind("<<ComboboxSelected>>", lambda _e: self._rebuild_input_tab())
        self.lbl_mode_hint = ttk.Label(bar, foreground="#666",
                                       text="Các mẫu đã tick hiển thị liên tục bên dưới")
        self.lbl_mode_hint.pack(side="left")

        self.input_container = ttk.Frame(self.tab_input)
        self.input_container.pack(fill="both", expand=True)

    def _selected_maps(self) -> list[dict]:
        """Các form map đang được tick ở bước 1 (giữ thứ tự trong case)."""
        out = []
        for f in self.case_forms:
            var = self.form_vars.get(f["map_id"])
            if var is not None and var.get() and f["map"]:
                out.append(f["map"])
        return out

    def _rebuild_input_tab(self):
        inner = self.input_container
        for child in inner.winfo_children():
            child.destroy()
        self.chk_clusters = []
        self.loop_editors = {}
        self.doc_sections = []
        self._doc_build_queue = []
        if self._doc_build_job:
            self.after_cancel(self._doc_build_job)
            self._doc_build_job = None

        selected = self._selected_maps()
        self._collect_form_choices(selected)
        if not selected:
            self.lbl_mode_hint.config(text="")
            ttk.Label(inner, text="Hãy quay lại Bước 1 và chọn ít nhất một mẫu biểu.",
                      font=("", 11, "italic")).pack(anchor="w", padx=8, pady=16)
            return

        # Sẵn sàng StringVar + cụm chk cho MỌI mẫu đã tick (dù chưa dựng khung)
        # -> dữ liệu draft/validate không phụ thuộc việc đã tải bản mẫu hay chưa
        for fmap in selected:
            for f in fmap.get("fields", []):
                self._own_var(f["key"], fmap["id"])
            chks = [f["key"] for f in fmap.get("fields", []) if f.get("type") == "chk"]
            for cluster in fld.chk_clusters(chks):
                self.bag.register_cluster(cluster)
                self.chk_clusters.append(cluster)

        if self.mode_combo.get() == "Danh sách trường":
            self.lbl_mode_hint.config(text="")
            self._build_field_list_ui(inner, selected)
        else:
            self._build_document_ui(inner)

    def _own_var(self, key: str, owner: str) -> tk.StringVar:
        """StringVar của key trong kho trung tâm; ghi nhận chủ sở hữu để lưu."""
        if key not in self.var_owner:
            self.var_owner[key] = "shared" if fld.classify(key) is not None else owner
        return self.bag.var(key)

    def _make_table_sync(self, mid: str, loop: str):
        key = (mid, loop)

        def sync():
            ed = self.loop_editors.get(key)
            if ed is not None:
                self.loop_rows[key] = ed.get_rows()
            self.schedule_autosave()
        return sync

    def _collect_form_choices(self, selected: list[dict]):
        self.form_choices = []
        for f in self.case_forms:
            fmap = f["map"]
            var = self.form_vars.get(f["map_id"])
            if not fmap or var is None or not var.get():
                continue
            label = "MẪU SỐ %02d — %s%s" % (
                fmap["mau_so"], fmap["ten_mau"],
                "   [BẮT BUỘC]" if f["bat_buoc"] else "")
            self.form_choices.append((label, fmap, bool(f["bat_buoc"])))

    def _build_document_ui(self, inner):
        """Chế độ "Trên bản mẫu": TẤT CẢ các mẫu đã tick nằm liên tục trong
        một khung cuộn dọc, mỗi mẫu có dải tiêu đề phân cách + nút thu gọn.

        Lazy: khung của từng mẫu dựng khi đến lượt (chuỗi after() idle,
        1 mẫu/lượt để không đơ UI) hoặc ngay khi người dùng mở rộng.
        """
        if not self.form_choices:
            return
        for i, (label, fmap, _b) in enumerate(self.form_choices):
            head = tk.Frame(inner, background="#d7d7d7")
            head.pack(fill="x", pady=(8, 0))
            lbl = tk.Label(head, text=label, background="#d7d7d7", anchor="w",
                           justify="left", wraplength=900, cursor="hand2",
                           font=("", 10, "bold"))
            lbl.pack(side="left", fill="x", expand=True, padx=6, pady=3)
            btn = tk.Label(head, text="▾", background="#d7d7d7", cursor="hand2",
                           font=("", 11, "bold"))
            btn.pack(side="right", padx=6)
            content = ttk.Frame(inner)
            content.pack(fill="x")
            view = DocumentView(content, fmap, self.bag, self.loop_rows,
                                on_change=self.schedule_autosave)
            sec = {"fmap": fmap, "label": label, "head": head, "content": content,
                   "view": view, "btn": btn, "open": True, "built": False}
            self.doc_sections.append(sec)
            self._doc_build_queue.append(sec)
            cmd = lambda _e=None, s=sec: self._toggle_doc_section(s)
            lbl.bind("<Button-1>", cmd)
            btn.bind("<Button-1>", cmd)

        # Dựng lần lượt: mỗi lượt idle dựng đúng 1 mẫu
        self._schedule_doc_builds()

    # ----- chuỗi dựng lazy theo lô -----
    def _schedule_doc_builds(self):
        if self._doc_build_job:
            self.after_cancel(self._doc_build_job)
        self._doc_build_job = self.after(10, self._build_next_doc_section)

    def _build_next_doc_section(self):
        self._doc_build_job = None
        if not self._doc_build_queue:
            return
        sec = self._doc_build_queue.pop(0)
        self._realize_doc_section(sec)
        if self._doc_build_queue:
            self._doc_build_job = self.after(10, self._build_next_doc_section)

    def _drain_doc_builds(self):
        """Dựng nốt toàn bộ section đồng bộ (phục vụ kiểm thử offscreen)."""
        if self._doc_build_job:
            self.after_cancel(self._doc_build_job)
            self._doc_build_job = None
        while self._doc_build_queue:
            self._build_next_doc_section()

    def _realize_doc_section(self, sec):
        if sec["built"]:
            return
        sec["built"] = True
        sec["view"].pack(fill="both", expand=True, padx=(10, 2))
        sec["view"].build()

    def _toggle_doc_section(self, sec):
        if not sec["open"]:
            self._realize_doc_section(sec)  # mở trước lúc đến lượt -> dựng luôn
            sec["btn"].config(text="▾")
            sec["view"].pack(fill="both", expand=True, padx=(10, 2), pady=(0, 4))
        else:
            sec["btn"].config(text="▸")
            sec["view"].pack_forget()
        sec["open"] = not sec["open"]

    def _build_field_list_ui(self, inner, selected):
        """Chế độ dự phòng "Danh sách trường": UI nhập nhóm theo namespace."""
        shared, per_form = fld.collect_fields(selected)

        ttk.Label(inner, text="THÔNG TIN DÙNG CHUNG (nhập 1 lần cho mọi mẫu)",
                  font=("", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        titles = dict(fld.SHARED_GROUPS)
        titles["ky"] = "Chữ ký & cơ quan tiếp nhận"
        for grp_key in ("dn", "chu_hkd", "cn", "ky"):
            items = shared.get(grp_key, [])
            if not items:
                continue
            box = ttk.LabelFrame(inner, text=" " + titles[grp_key] + " ")
            box.pack(fill="x", padx=8, pady=3)
            self._add_text_fields(box, items, "shared")
            self._add_chk_fields(box, items, "shared")

        for fmap in selected:
            rows = per_form.get(fmap["id"], [])
            tables = fmap.get("dynamic_tables", [])
            if not rows and not tables:
                continue
            box = ttk.LabelFrame(
                inner,
                text=" Trường riêng từng mẫu — PL%s Mẫu %02d: %s "
                     % (fmap["phu_luc"], fmap["mau_so"], fmap["ten_mau"][:80]),
            )
            box.pack(fill="x", padx=8, pady=4)
            self._add_text_fields(box, rows, fmap["id"])
            self._add_chk_fields(box, rows, fmap["id"])
            for tdef in tables:
                key = (fmap["id"], tdef.get("loop", ""))
                editor = DynamicTableEditor(box, tdef,
                                            on_change=self._make_table_sync(*key))
                editor.pack(fill="x", padx=4, pady=3)
                self.loop_editors[key] = editor
                self.loop_rows[key] = editor.get_rows()

    def _add_text_fields(self, master, items, owner: str):
        """Thêm Entry cho các field dạng text (bỏ qua chk — xử lý riêng)."""
        for f in items:
            if f.get("type") == "chk":
                continue
            var = self._own_var(f["key"], owner)
            row = ttk.Frame(master)
            row.pack(fill="x", padx=4, pady=1)
            lbl = f["label"] or f["key"]
            ttk.Label(row, text=lbl, wraplength=520, justify="left").pack(side="top", anchor="w")
            ttk.Entry(row, textvariable=var).pack(side="top", anchor="w", fill="x", pady=(0, 2))

    def _add_chk_fields(self, master, items, owner: str):
        """Checkbox đơn lẻ -> Checkbutton; cùng tiền tố -> Radiobutton loại trừ."""
        chks = [(f["key"], f.get("label") or f["key"]) for f in items if f.get("type") == "chk"]
        if not chks:
            return
        lookup = dict(chks)
        for cluster in fld.chk_clusters([k for k, _ in chks]):
            grp = ChkFieldGroup(master, [(k, lookup[k]) for k in cluster],
                                on_change=self.schedule_autosave,
                                vars_map={k: self._own_var(k, owner) for k in cluster})
            grp.pack(fill="x", padx=4, pady=2)

    # ------------------------------------------------------------------
    # Thu thập dữ liệu / áp dữ liệu
    # ------------------------------------------------------------------
    def collect_data_for_render(self, fmap: dict) -> dict:
        """Dữ liệu render của 1 mẫu từ kho trung tâm (VarBag + loop_rows)."""
        return collect_from_map(fmap, self.bag, self.loop_rows)

    def current_values(self) -> dict:
        """Toàn bộ giá trị đang nhập (phục vụ lưu/mở hồ sơ)."""
        shared: dict = {}
        private: dict = {}
        for key, var in self.bag.vars.items():
            owner = self.var_owner.get(key, "shared")
            bucket = shared if owner == "shared" else private.setdefault(owner, {})
            bucket[key] = var.get()
        return {
            "case_id": self.case["id"] if self.case else "",
            "forms": [mid for mid, v in self.form_vars.items() if v.get()],
            "shared": shared,
            "private": private,
            "chk": {str(i): {k: self.bag.get(k) for k in cluster}
                    for i, cluster in enumerate(self.chk_clusters)},
            "tables": {
                "%s|%s" % key: rows for key, rows in self.loop_rows.items()
            },
        }

    def apply_profile(self, prof: dict | None):
        """Nạp dữ liệu hồ sơ (draft hoặc file JSON) vào giao diện."""
        if not prof or not self.case or prof.get("case_id") != self.case["id"]:
            return
        for mid in prof.get("forms", []) or []:
            if mid in self.form_vars:
                self.form_vars[mid].set(True)
        # forms thay đổi có thể thêm/bớt ô nhập -> dựng lại trước khi nạp giá trị
        self._rebuild_input_tab()
        for key, val in (prof.get("shared") or {}).items():
            self.bag.set(key, val)
        for _mid, by_map in (prof.get("private") or {}).items():
            for key, val in by_map.items():
                self.bag.set(key, val)
        # Chỉ bật X; cụm radio loại trừ tự xử lý qua VarBag
        for _i, vals in (prof.get("chk") or {}).items():
            for key, val in vals.items():
                if str(val).strip().upper() == CHK:
                    self.bag.set(key, CHK)
        for key, rows in (prof.get("tables") or {}).items():
            try:
                mid, loop = key.split("|", 1)
            except ValueError:
                continue
            self.loop_rows[(mid, loop)] = rows
            ed = self.loop_editors.get((mid, loop))
            if ed is not None:
                ed.set_rows(rows)

    # ------------------------------------------------------------------
    # Hồ sơ nháp (autosave debounce 1s) + Lưu/Mở/Nhập lại
    # ------------------------------------------------------------------
    def schedule_autosave(self, *_args):
        if self.case is None:
            return
        if self._autosave_job:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(1000, self.autosave_now)

    def autosave_now(self):
        self._autosave_job = None
        if self.case is None:
            return
        try:
            eio.save_json(eio.draft_path(self.case["id"]), self.current_values())
        except Exception as exc:  # noqa: BLE001
            print("Autosave lỗi:", exc)

    def save_profile_as(self):
        if not self.case:
            messagebox.showinfo("Chưa chọn trường hợp", "Hãy chọn trường hợp ở Bước 1.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile="%s.json" % self.case["id"],
            filetypes=[("Hồ sơ JSON", "*.json")],
        )
        if not path:
            return
        eio.save_json(Path(path), self.current_values())
        messagebox.showinfo("Đã lưu", "Đã lưu hồ sơ:\n%s" % path)

    def open_profile(self):
        path = filedialog.askopenfilename(filetypes=[("Hồ sơ JSON", "*.json")])
        if not path:
            return
        prof = eio.load_json(Path(path))
        current_id = self.case["id"] if self.case else None
        if not prof or prof.get("case_id") != current_id:
            # Cho phép mở hồ sơ thuộc case khác: chuyển sang case tương ứng
            target = (prof or {}).get("case_id")
            idx = next((i for i, c in enumerate(self.cases) if c["id"] == target), None)
            if idx is None:
                messagebox.showerror("Lỗi", "File không hợp lệ hoặc không rõ trường hợp.")
                return
            case = self.cases[idx]
            gi = self.groups.index(case["nhom"])
            self.lb_groups.selection_clear(0, "end")
            self.lb_groups.selection_set(gi)
            self._on_group_select()
            ci = [c["id"] for c in self.cases if c.get("nhom") == case["nhom"]].index(target)
            self.lb_cases.selection_clear(0, "end")
            self.lb_cases.selection_set(ci)
            self._on_case_select()
        self.apply_profile(prof)
        self.set_status_b3("Đã mở hồ sơ: %s" % path)

    def reset_case(self):
        if not self.case:
            return
        p = eio.draft_path(self.case["id"])
        if p.exists():
            p.unlink()
        self.bag.clear()
        self.loop_rows = {}
        for f in self.case_forms:
            self.form_vars[f["map_id"]].set(bool(f["bat_buoc"]))
        self._rebuild_input_tab()
        self.set_status_b3("Đã nhập lại từ đầu.")

    # ------------------------------------------------------------------
    # Bước 3: kiểm tra + xuất hồ sơ
    # ------------------------------------------------------------------
    def _build_tab_export(self):
        f = self.tab_export
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="KIỂM TRA & XEM CẢNH BÁO", command=self.validate_and_show).pack(side="left")
        ttk.Button(bar, text="TẠO HỒ SƠ (.docx)", command=self.export_docx).pack(side="left", padx=6)
        self.btn_zip = ttk.Button(bar, text="Đóng ZIP", command=self.make_zip, state="disabled")
        self.btn_zip.pack(side="left")
        self.btn_open_dir = ttk.Button(
            bar, text="Mở thư mục kết quả", command=self.open_output_dir, state="disabled"
        )
        self.btn_open_dir.pack(side="left", padx=6)

        self.progress = ttk.Progressbar(f, mode="determinate")
        self.progress.pack(fill="x", padx=8)

        self.lbl_status_b3 = ttk.Label(f, text="", foreground="#444")
        self.lbl_status_b3.pack(anchor="w", padx=8)

        ttk.Label(f, text="Cảnh báo (không chặn xuất file):").pack(anchor="w", padx=8, pady=(6, 0))
        self.txt_warn = tk.Text(f, height=14, wrap="word")
        self.txt_warn.tag_configure("warn", background="#fff3bf")
        self.txt_warn.tag_configure("ok", background="#dcf5dc")
        self.txt_warn.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def set_status_b3(self, msg: str):
        self.lbl_status_b3.config(text=msg)

    def _all_value_of(self, fmap_id: str, key: str) -> str:
        del fmap_id  # một key chỉ có một StringVar chung trong kho trung tâm
        return self.bag.get(key).strip()

    @staticmethod
    def _digits(s: str) -> str:
        return "".join(c for c in s if c.isdigit())

    def validate_warnings(self) -> list[str]:
        """Cảnh báo vàng: bắt buộc trống, CCCD/MST sai định dạng, email thiếu @."""
        warns = []
        for f in self.case_forms:
            mid = f["map_id"]
            var = self.form_vars.get(mid)
            if var is None or not var.get() or not f["map"]:
                continue
            fmap = f["map"]
            tag = "PL%s M%02d" % (fmap["phu_luc"], fmap["mau_so"])
            if f["bat_buoc"]:
                for fld_def in fmap.get("fields", []):
                    key = fld_def["key"]
                    if any(h in key.lower() for h in REQUIRED_KEY_HINTS):
                        if not self._all_value_of(mid, key):
                            warns.append("%s: thiếu trường bắt buộc “%s” (%s)"
                                         % (tag, fld_def.get("label") or key, key))
            for fld_def in fmap.get("fields", []):
                key = fld_def["key"]
                val = self._all_value_of(mid, key)
                if not val:
                    continue
                kl = key.lower()
                if "cccd" in kl:
                    n = len(self._digits(val))
                    if not 9 <= n <= 12:
                        warns.append("%s: “%s” phải gồm 9–12 chữ số (đang nhập: %s)"
                                     % (tag, fld_def.get("label") or key, val))
                elif "ma_so" in kl or kl.endswith("mst"):
                    n = len(self._digits(val))
                    if n not in (10, 13):
                        warns.append("%s: “%s” phải là MST 10 hoặc 13 số (đang nhập: %s)"
                                     % (tag, fld_def.get("label") or key, val))
                elif "email" in kl and "@" not in val:
                    warns.append("%s: email “%s” thiếu dấu @" % (tag, val))
        # Mã ngành không khớp danh mục VSIC (cảnh báo mềm, không chặn xuất)
        for sec in self.doc_sections:
            view = sec.get("view")
            if view is not None and view.built and view.has_invalid_ma():
                warns.append("PL%s M%02d: có mã ngành không có trong danh mục VSIC "
                             "(kiểm tra lại ô Mã ngành)" % (view.fmap["phu_luc"],
                                                            view.fmap["mau_so"]))
        return warns

    def validate_and_show(self):
        warns = self.validate_warnings()
        self.txt_warn.delete("1.0", "end")
        if warns:
            for w in warns:
                self.txt_warn.insert("end", "⚠ %s\n" % w, "warn")
        else:
            self.txt_warn.insert("end", "Không có cảnh báo nào. Hồ sơ sẵn sàng xuất.\n", "ok")
        self.nb.select(self.tab_export)

    def export_docx(self):
        if not self.case:
            messagebox.showinfo("Chưa chọn trường hợp", "Hãy chọn trường hợp ở Bước 1.")
            return
        selected = [
            f for f in self.case_forms
            if self.form_vars.get(f["map_id"]) and self.form_vars[f["map_id"]].get() and f["map"]
        ]
        if not selected:
            messagebox.showinfo("Chưa chọn mẫu", "Tick ít nhất một mẫu biểu ở Bước 1.")
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        out_dir = eio.GENERATED_DIR / ("%s_%s" % (self.case["id"], stamp))
        self.btn_zip.config(state="disabled")
        self.btn_open_dir.config(state="disabled")
        self.progress.config(value=0, maximum=len(selected) + 1)
        self.set_status_b3("Đang tạo hồ sơ...")

        # Đọc toàn bộ dữ liệu nhập ở MAIN THREAD (Tk không cho phép luồng khác
        # đụng vào widget/var), rồi mới đưa sang thread chỉ làm việc với file.
        jobs = []
        for f in selected:
            fmap = f["map"]
            name = "Mau_%02d_%s.docx" % (f["mau"], eio.slugify(fmap["ten_mau"]))
            jobs.append((name, fmap["template"], self.collect_data_for_render(fmap)))

        def worker():
            ok, fail = [], []
            for i, (name, template_rel, data) in enumerate(jobs, 1):
                dest = out_dir / name
                try:
                    content = render_docx(eio.APP_DIR / template_rel, data)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
                    ok.append((name, selected[i - 1]["map"]))
                except Exception as exc:  # noqa: BLE001 — lỗi 1 mẫu không chặn mẫu khác
                    fail.append((name, repr(exc)))
                self._render_queue.put(("step", i))
            try:
                self._write_checklist(out_dir, selected, ok, fail)
            except Exception as exc:  # noqa: BLE001
                fail.append(("_checklist.txt", repr(exc)))
            self._render_queue.put(("done", (out_dir, ok, fail)))

        threading.Thread(target=worker, daemon=True).start()
        self._rendering = True
        self.after(120, self._poll_render_queue)

    def _write_checklist(self, out_dir: Path, selected: list[dict], ok: list, fail: list):
        lines = ["HỒ SƠ: %s — %s" % (self.case["ten"], self.case["id"]), "=" * 60, "",
                 "Các mẫu đã xuất:"]
        for name, fmap in ok:
            lines.append("  ✔ %s (PL%s Mẫu %02d: %s)" % (name, fmap["phu_luc"], fmap["mau_so"], fmap["ten_mau"]))
        for name, err in fail:
            lines.append("  ✖ %s — LỖI: %s" % (name, err))
        lines += ["", "GIẤY TỜ NỘP KÈM:"]
        lines += ["  %d. %s" % (i, g) for i, g in enumerate(self.case.get("giay_to_kem", []), 1)]
        if self.case.get("luu_y"):
            lines += ["", "LƯU Ý:"] + ["  - %s" % l for l in self.case["luu_y"]]
        if self.case.get("co_so_phap_ly"):
            lines += ["", "CƠ SỞ PHÁP LÝ:"] + ["  - %s" % l for l in self.case["co_so_phap_ly"]]
        (out_dir / "_checklist.txt").write_text("\n".join(lines), encoding="utf-8")

    def _poll_render_queue(self):
        try:
            while True:
                kind, payload = self._render_queue.get_nowait()
                if kind == "step":
                    self.progress.config(value=payload)
                elif kind == "done":
                    self._rendering = False
                    self._finish_export(payload)
                    return  # xong việc thì dừng vòng poll
        except queue.Empty:
            pass
        if self._rendering:
            self.after(120, self._poll_render_queue)

    def _finish_export(self, payload):
        out_dir, ok, fail = payload
        self.output_dir = out_dir
        self.progress.config(value=self.progress["maximum"])
        self.txt_warn.delete("1.0", "end")
        if fail:
            self.set_status_b3("Xong với %d lỗi / %d thành công." % (len(fail), len(ok)))
            for name, err in fail:
                self.txt_warn.insert("end", "✖ %s: %s\n" % (name, err), "warn")
        else:
            self.set_status_b3("Tạo hồ sơ thành công: %s" % out_dir)
            self.txt_warn.insert("end", "✔ Đã tạo %d file .docx + _checklist.txt tại:\n%s\n"
                                 % (len(ok), out_dir), "ok")
        self.btn_zip.config(state="normal")
        self.btn_open_dir.config(state="normal")
        self.autosave_now()

    def make_zip(self):
        if not self.output_dir or not self.output_dir.exists():
            return
        zip_path = eio.GENERATED_DIR / ("%s.zip" % self.case["id"])
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(self.output_dir.iterdir()):
                z.write(p, arcname="%s/%s" % (self.output_dir.name, p.name))
        self.set_status_b3("Đã đóng ZIP: %s" % zip_path)

    def open_output_dir(self):
        if self.output_dir and self.output_dir.exists():
            os.startfile(str(self.output_dir))  # noqa: S606 — chỉ Windows, do người dùng bấm


def run_smoke_import_check():  # pragma: no cover — phục vụ kiểm tra thủ công
    print("app_tk import OK; App chưa được khởi tạo.")
