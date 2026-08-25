"""Widget dùng chung: khung cuộn, nhóm checkbox/radio, bảng lặp."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

CHK = "X"  # giá trị tích chọn trong dữ liệu render


class ScrollableFrame(ttk.Frame):
    """Khung cuộn dọc bằng Canvas (hỗ trợ con lăn chuột)."""

    def __init__(self, master, bg="#f0f0f0", **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=bg)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, background=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Con lăn chuột chỉ hoạt động khi rê chuột lên khung này
        self.inner.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.inner.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")


class ChkFieldGroup(ttk.LabelFrame):
    """Một cụm checkbox: >=2 key cùng tiền tố -> Radiobutton loại trừ,
    1 key -> Checkbutton độc lập. Biến nội bộ là StringVar "X"/""."""

    def __init__(self, master, keys_with_labels: list[tuple[str, str]], on_change=None,
                 vars_map: dict[str, tk.StringVar] | None = None):
        """vars_map: dict key -> StringVar có sẵn (dùng chung VarBag của phiên);
        nếu không truyền thì nhóm tự tạo StringVar nội bộ như trước."""
        title = keys_with_labels[0][1] if len(keys_with_labels) == 1 else "Chọn một"
        super().__init__(master, text=title)
        self.on_change = on_change
        self.vars: dict[str, tk.StringVar] = {}
        if len(keys_with_labels) == 1:
            key, label = keys_with_labels[0]
            var = vars_map.get(key) if vars_map else None
            if var is None:
                var = tk.StringVar(value="")
            self.vars[key] = var
            cb = tk.Checkbutton(
                self, text=label or key, variable=var,
                onvalue=CHK, offvalue="", anchor="w", justify="left",
            )
            cb.pack(fill="x", padx=4, pady=1)
            var.trace_add("write", lambda *_: self._changed())
        else:
            for i, (key, label) in enumerate(keys_with_labels):
                var = vars_map.get(key) if vars_map else None
                if var is None:
                    var = tk.StringVar(value="")
                self.vars[key] = var
                rb = tk.Radiobutton(
                    self, text=label or key, value=CHK, variable=var,
                    anchor="w", justify="left",
                )
                rb.pack(fill="x", padx=4, pady=1)
                # Chọn một thì bỏ chọn các key còn lại trong cụm
                var.trace_add(
                    "write",
                    lambda *_ , v=var, k=key: self._radio_changed(v, k),
                )

    def _radio_changed(self, var: tk.StringVar, chosen_key: str):
        if var.get() == CHK:
            for key, v in self.vars.items():
                if key != chosen_key and v.get():
                    v.set("")
        self._changed()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def values(self) -> dict[str, str]:
        return {k: v.get() for k, v in self.vars.items()}

    def set_values(self, vals: dict[str, str]) -> None:
        for k, v in self.vars.items():
            v.set(CHK if str(vals.get(k, "")).strip().upper() == CHK else "")


class DynamicTableEditor(ttk.LabelFrame):
    """Bảng nhập nhiều dòng cho dynamic_tables: Thêm dòng / Xóa dòng cuối."""

    def __init__(self, master, table_def: dict, on_change=None):
        super().__init__(
            master,
            text="%s (%s)" % (table_def.get("loop", ""), "bảng lặp"),
        )
        self.columns = [(c["tag"], c.get("header", c["tag"])) for c in table_def.get("columns", [])]
        self.on_change = on_change
        self._rows: list[dict[str, tk.StringVar]] = []

        head = ttk.Frame(self)
        head.pack(fill="x")
        col_w = max(12, 60 // max(1, len(self.columns)))
        for _col, header in self.columns:
            ttk.Label(head, text=header, width=col_w, font=("", 9, "bold")).pack(
                side="left", padx=1
            )

        self.body = ttk.Frame(self)
        self.body.pack(fill="x")

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=2)
        ttk.Button(bar, text="Thêm dòng", command=self.add_row).pack(side="left")
        ttk.Button(bar, text="Xóa dòng cuối", command=self.remove_last).pack(side="left", padx=4)

        self.add_row()  # sẵn một dòng trống

    def add_row(self):
        row_idx = len(self._rows)
        frame = ttk.Frame(self.body)
        frame.pack(fill="x", pady=1)
        vars_by_tag: dict[str, tk.StringVar] = {}
        for col, _header in self.columns:
            var = tk.StringVar()
            vars_by_tag[col] = var
            var.trace_add("write", lambda *_: self._changed())
            ttk.Entry(frame, textvariable=var, width=max(12, 60 // len(self.columns))).pack(
                side="left", expand=True, fill="x", padx=1
            )
        ttk.Button(
            frame, text="✕", width=3,
            command=lambda fi=row_idx: self.remove_row(fi),
        ).pack(side="left")
        self._rows.append(vars_by_tag)

    def remove_last(self):
        if self._rows:
            self.remove_row(len(self._rows) - 1)

    def remove_row(self, idx: int):
        if not (0 <= idx < len(self._rows)):
            return
        # Xóa widget của các dòng sau rồi dựng lại phần còn lại cho đơn giản
        rows_data = [self.row_values(i) for i in range(len(self._rows)) if i != idx]
        for child in self.body.winfo_children():
            child.destroy()
        self._rows = []
        for rd in rows_data:
            self.add_row()
            for tag, val in rd.items():
                self._rows[-1][tag].set(val)
        self._changed()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def row_values(self, idx: int) -> dict[str, str]:
        return {tag: v.get() for tag, v in self._rows[idx].items()}

    def get_rows(self) -> list[dict[str, str]]:
        return [self.row_values(i) for i in range(len(self._rows))]

    def set_rows(self, rows: list[dict]) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self._rows = []
        for r in rows or []:
            self.add_row()
            for tag, v in self._rows[-1].items():
                v.set(str(r.get(tag, "")))
