"""Khung xem tài liệu A4 "điền trực tiếp lên biểu mẫu" (kiểu trang Word/HTKK).

Dựng lại bố cục template .docx bằng python-docx rồi thể hiện trên GIẤY A4:
- Khổ giấy chuẩn 210x297mm tại 96dpi (794x1123px), lề trái 25mm / phải 20mm /
  trên-dưới 20mm; nền xám kiểu Word, tờ giấy trắng nổi bật, có vạch phân trang
  khi nội dung vượt một trang (không cắt đôi bảng/paragraph).
- Phông Times New Roman cỡ 12 như văn bản hành chính VN.
- Paragraph không có the {..} -> Label chỉ đọc (giữ căn lề, chữ in đậm).
- Paragraph có the -> tk.Text không viền, chèn ttk.Entry NGAY TẠI vị trí the
  bằng window_create; ô TRỐNG nền vàng nhạt (slot), điền xong về trắng.
- Ô bảng thường -> Label giãn dòng; ô chứa the -> Entry/mini-Text tương tự.
  Bảng vẽ viền ke đen mảnh theo đúng tỉ lệ cột của template (gridCol).
- Hàng chứa {#loop}...{/loop} -> vùng bảng lặp (thêm/xóa dòng), dữ liệu là
  list[dict] lưu trong kho dùng chung `tables` của phiên; bảng ngành có cột
  ma_nganh bật tra cứu gợi ý VSIC.
Mọi StringVar lấy từ VarBag dùng chung theo key nên hai mẫu cùng hiển thị một
key (vd co_quan_dkkd) luôn đồng bộ giá trị với nhau.
"""

from __future__ import annotations

import datetime
import math
import re
import tkinter as tk
import unicodedata
from tkinter import font as tkfont
from tkinter import ttk

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from . import engine_io as eio
from .widgets import CHK, ScrollableFrame

# Tag biến: {key} hoặc {a.b.c} — khớp engine tools/docx_render.py
TAG_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")
LOOP_OPEN_RE = re.compile(r"\{#([A-Za-z0-9_]+)\}")
LOOP_CLOSE_RE = re.compile(r"\{/([A-Za-z0-9_]+)\}")

# ---------------------------------------------------------------------------
# Hình học A4 @96dpi: 210x297mm -> 794x1123 px
# ---------------------------------------------------------------------------
_MM = 96 / 25.4
PAGE_W = round(210 * _MM)            # 794
PAGE_H = round(297 * _MM)            # 1123
MGN_L = round(25 * _MM)              # 94
MGN_R = round(20 * _MM)              # 75
MGN_T = round(20 * _MM)              # 75
MGN_B = round(20 * _MM)
CONTENT_W = PAGE_W - MGN_L - MGN_R   # ~625

DESK_BG = "#808080"      # nền "bàn" quanh giấy như Word
SHEET_BG = "#FFFFFF"
SHEET_EDGE = "#5a5a5a"
RULE = "#444444"         # viền bảng
SLOT_BG = "#FFF6CE"      # nền ô nhập còn trống (slot)
GAP_PAGE = 28            # khe giữa hai trang

FONT_FAMILY = "Times New Roman"
F_SIZE = 12


def f_base() -> tuple:
    return (FONT_FAMILY, F_SIZE)


def f_bold() -> tuple:
    return (FONT_FAMILY, F_SIZE, "bold")


_CHAR_W: int | None = None


def char_w() -> int:
    """Bề rộng tham chiếu 1 ký tự (px) của phông cơ sở — để quy đổi px->chars."""
    global _CHAR_W
    if _CHAR_W is None:
        try:
            f = tkfont.Font(family=FONT_FAMILY, size=F_SIZE)
            _CHAR_W = max(4, f.measure("0"))
        except tk.TclError:
            _CHAR_W = 8
    return _CHAR_W


def px2chars(px: int) -> int:
    return max(4, int(px // char_w()))


class VarBag:
    """Kho StringVar dùng chung theo key cho toàn phiên làm việc.

    Một key = một StringVar: mọi widget ở mọi mẫu/kiểu điền gắn vào cùng biến
    nên tự động đồng bộ. Cụm chk >=2 key đăng ký qua register_cluster() sẽ
    loại trừ nhau như radio (gán "X" cho một key thì xóa các key còn lại).
    """

    def __init__(self, on_change=None):
        self.vars: dict[str, tk.StringVar] = {}
        self.on_change = on_change
        self._cluster_of: dict[str, list[str]] = {}
        self._registered: set[frozenset] = set()
        today = datetime.date.today()
        self.defaults = {
            "ngay_ky_vb": str(today.day),
            "thang_ky_vb": str(today.month),
            "nam_ky_vb": str(today.year),
        }

    def var(self, key: str) -> tk.StringVar:
        v = self.vars.get(key)
        if v is None:
            v = tk.StringVar(value=self.defaults.get(key, ""))
            v.trace_add("write", lambda *_a, k=key: self._on_write(k))
            self.vars[key] = v
        return v

    def get(self, key: str) -> str:
        v = self.vars.get(key)
        return v.get() if v is not None else ""

    def set(self, key: str, value) -> None:
        self.var(key).set("" if value is None else str(value))

    def register_cluster(self, keys) -> None:
        keys = list(keys)
        fs = frozenset(keys)
        if len(fs) < 2 or fs in self._registered:
            return
        self._registered.add(fs)
        for k in keys:
            self._cluster_of[k] = list(keys)

    def _on_write(self, key: str):
        cluster = self._cluster_of.get(key)
        if cluster:
            v = self.vars.get(key)
            if v is not None and v.get() == CHK:
                for other_key in cluster:
                    if other_key == key:
                        continue
                    ov = self.vars.get(other_key)
                    if ov is not None and ov.get():
                        ov.set("")
        if self.on_change:
            self.on_change()

    def clear(self):
        """Xóa trắng mọi giá trị (mặc định ngày/tháng/năm được đặt lại)."""
        for k in list(self.vars):
            self.vars[k].set(self.defaults.get(k, ""))


def iter_blocks(doc):
    """Duyệt body theo thứ tự block: paragraph / bảng (như dump_structure)."""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", Table(child, doc))


# ---------------------------------------------------------------------------
# Tra cứu mã ngành VSIC (dùng cho cột ten_nganh / ma_nganh của bảng lặp)
# ---------------------------------------------------------------------------
def _fold(text: str) -> str:
    """Chữ thường bỏ dấu (NFD) giống fold() trong tools/build_form_maps.py."""
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return out.replace("đ", "d")


_VSIC_MA_SET: set[str] | None = None


def _vsic_ma_set() -> set[str]:
    global _VSIC_MA_SET
    if _VSIC_MA_SET is None:
        _VSIC_MA_SET = {ma for ma, _ten, _cap in eio.load_nganh_vsic()}
    return _VSIC_MA_SET


def vsic_search(query: str, limit: int = 12) -> list[tuple[str, str]]:
    """Gợi ý ngành theo từ khóa (không dấu, khớp chứa); ưu tiên cấp 4."""
    q = _fold(query).strip()
    if not q:
        return []
    hits = []
    for ma, ten, cap in eio.load_nganh_vsic():
        fm, ft = ma.lower(), _fold(ten)
        if q in ft or fm.startswith(q) or q in fm:
            # Ưu tiên cấp 4 (mức dùng đăng ký kinh doanh), rồi khớp mạnh hơn
            strong = q == fm or ft.startswith(q)
            hits.append((0 if cap == 4 else 1, 0 if strong else 1,
                         len(ft), ma, ten))
    hits.sort()
    return [(ma, ten) for *_r, ma, ten in hits[:limit]]


def apply_vsic_pick(row_vars: dict[str, tk.StringVar], ma: str, ten: str):
    """Chọn một gợi ý -> điền CẢ tên và mã vào cùng hàng của bảng lặp."""
    if "ma_nganh" in row_vars:
        row_vars["ma_nganh"].set(ma)
    if "ten_nganh" in row_vars:
        row_vars["ten_nganh"].set(ten)


class VsicPopup(tk.Toplevel):
    """Popup gợi ý ngành dưới ô nhập; đóng khi Esc/mất focus/chọn xong."""

    def __init__(self, entry, results, on_pick):
        super().__init__()
        self.withdraw()
        self.overrideredirect(True)
        self.entry = entry
        self.on_pick = on_pick
        self.results = list(results)
        self.closed = False
        self.picked = False
        self.lb = tk.Listbox(self, activestyle="dotbox", exportselection=False,
                             highlightthickness=1, highlightbackground="#9a9a9a",
                             font=f_base())
        self.lb.pack(fill="both", expand=True)
        self._fill(results)
        self.lb.selection_set(0)
        self.lb.activate(0)
        self.lb.bind("<ButtonRelease-1>", self._on_click)
        self.lb.bind("<Return>", self._on_click)
        self.lb.bind("<Escape>", lambda _e: self.close())
        self.lb.bind("<MouseWheel>", lambda e: self.lb.yview_scroll(
            -e.delta // 120, "units"))
        self.lb.bind("<Motion>", lambda _e: None)

    def _fill(self, results):
        self.lb.delete(0, "end")
        for ma, ten in results:
            self.lb.insert("end", "%s   —   %s" % (ma, ten))

    def update_results(self, results):
        self.results = list(results)
        self._fill(self.results)
        if self.results:
            self.lb.selection_set(0)
            self.lb.activate(0)

    def show(self):
        if self.closed or not self.results:
            return
        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            w = max(self.entry.winfo_width(), 420)
            h = min(len(self.results), 12) * 24 + 8
            self.geometry("%dx%d+%d+%d" % (w, h, x, y))
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
        except tk.TclError:
            self.close()

    def move(self, delta: int):
        if not self.results:
            return
        cur = self.lb.curselection()
        idx = (cur[0] if cur else 0) + delta
        idx = max(0, min(idx, len(self.results) - 1))
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(idx)
        self.lb.activate(idx)
        self.lb.see(idx)

    def choose_current(self):
        cur = self.lb.curselection()
        if not cur and self.results:
            self.lb.selection_set(0)
            cur = (0,)
        if cur:
            ma, ten = self.results[cur[0]]
            self._do_pick(ma, ten)

    def _on_click(self, event=None):
        del event
        cur = self.lb.curselection()
        if cur:
            ma, ten = self.results[cur[0]]
            self._do_pick(ma, ten)

    def _do_pick(self, ma: str, ten: str):
        self.picked = True
        self.on_pick(ma, ten)
        self.close()

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.destroy()
            except tk.TclError:
                pass


def attach_vsic_completion(entry, var: tk.StringVar, row_vars: dict):
    """Gắn tra cứu gợi ý VSIC cho một Entry (ô Tên ngành hoặc Mã ngành).

    - Gõ từ khóa -> popup tối đa 12 kết quả khớp (ưu tiên cấp 4).
    - Chọn gợi ý -> tự điền cả ten_nganh + ma_nganh trong cùng hàng.
    - Esc / mất focus / cuộn away -> đóng popup (không chặn cuộn).
    """
    box: dict = {"popup": None}

    def close_popup(_event=None):
        p = box.get("popup")
        if p is not None and not p.closed:
            p.close()
        box["popup"] = None

    def pick(ma: str, ten: str):
        apply_vsic_pick(row_vars, ma, ten)
        close_popup()
        try:
            entry.focus_set()
        except tk.TclError:
            pass

    def refresh(_event=None):
        res = vsic_search(var.get())
        if not var.get().strip() or not res:
            close_popup()
            return
        p = box.get("popup")
        if p is None or p.closed:
            p = VsicPopup(entry, res, pick)
            box["popup"] = p
        else:
            p.update_results(res)
        p.show()

    def on_focus_out(_event=None):
        p = box.get("popup")
        if p is not None and not p.closed:
            # chậm một nhịp để click chọn trên Listbox kịp xử lý
            p.after(160, lambda: (not p.picked) and p.close())

    def on_key(event):
        keysym = event.keysym
        if keysym == "Escape":
            close_popup()
            return "break"
        p = box.get("popup")
        if keysym == "Down":
            if p is None or p.closed:
                refresh()
            else:
                p.move(1)
            return "break"
        if keysym == "Up" and p is not None and not p.closed:
            p.move(-1)
            return "break"
        if keysym in ("Return", "KP_Enter") and p is not None and not p.closed:
            p.choose_current()
            return "break"
        entry.after_idle(refresh)
        return None

    entry.bind("<Key>", on_key)
    entry.bind("<FocusOut>", on_focus_out)
    entry.bind("<Destroy>", close_popup)


_VSIC_STYLE_READY = False


def _mark_ma_validity(var: tk.StringVar, entry):
    """Ô Mã ngành: gõ mã không có trong danh mục -> nền đỏ nhẹ (không chặn)."""
    global _VSIC_STYLE_READY
    val = var.get().strip()
    ok = not val or val in _vsic_ma_set()
    try:
        if not _VSIC_STYLE_READY:
            ttk.Style().configure("VsicErr.TEntry", fieldbackground="#ffe9e7")
            _VSIC_STYLE_READY = True
        if getattr(entry, "_vsic_bad", False) != (not ok):
            entry.configure(style="VsicErr.TEntry" if not ok else "TEntry")
            entry._vsic_bad = not ok
    except tk.TclError:
        pass


def _cell_text(cell: _Cell) -> str:
    return "\n".join(pp.text for pp in cell.paragraphs)


def _layout_cells(table: Table) -> list[dict]:
    """Tọa độ hiển thị các ô hợp nhất của bảng.

    Trả về list record {tc, row, col, colspan, rowspan, text}; ô trùng do
    merge bị gộp nhờ so sánh identity của cell._tc (không in ô trùng).
    """
    placements: dict[int, dict] = {}
    recs: list[dict] = []
    for ri, row in enumerate(table.rows):
        cells = list(row.cells)
        ci = 0
        while ci < len(cells):
            tc = cells[ci]._tc
            tid = id(tc)
            span = 1
            while ci + span < len(cells) and cells[ci + span]._tc is tc:
                span += 1
            rec = placements.get(tid)
            if rec is None:
                rec = {
                    "tc": tc, "row": ri, "col": ci,
                    "colspan": span, "rowspan": 1,
                    "text": _cell_text(_Cell(tc, table)),
                }
                placements[tid] = rec
                recs.append(rec)
            else:  # merge dọc: mở rộng rowspan của ô đã đặt
                rec["rowspan"] += 1
            ci += span
    return recs


def _table_col_px(table: Table, ncols: int) -> list[int]:
    """Bề rộng px từng cột theo tblGrid của template; lệch nhiều thì co giãn."""
    ws: list[int | None] = []
    grid = table._tbl.tblGrid
    if grid is not None:
        for gc in grid.findall(qn("w:gridCol")):
            raw = gc.get(qn("w:w"))
            ws.append(int(round(int(raw) / 914400 * 96)) if raw else None)
    while len(ws) < ncols:
        ws.append(None)
    ws = ws[:ncols]
    if any(w is None for w in ws) or sum(ws) <= 0:
        each = max(30, CONTENT_W // ncols)
        return [each] * ncols
    s = sum(ws)
    if abs(s - CONTENT_W) > 10:  # chuẩn hóa về đúng bề rộng vùng chữ
        k = CONTENT_W / s
        ws = [max(18, int(w * k)) for w in ws]
    return [int(w) for w in ws]


def _para_meta(p: Paragraph):
    """(text, [(a,b,key)...], centered?, right?, bold_spans) của paragraph."""
    text = p.text
    tags = [(m.start(), m.end(), m.group(1)) for m in TAG_RE.finditer(text)]
    centered = p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    right = p.alignment == WD_ALIGN_PARAGRAPH.RIGHT
    bold_spans = []
    pos = 0
    for run in p.runs:
        if run.bold:
            bold_spans.append((pos, pos + len(run.text)))
        pos += len(run.text)
    return text, tags, centered, right, bold_spans


def _seg_bold(bold_spans, a: int, b: int) -> bool:
    return any(not (e <= a or s >= b) for s, e in bold_spans)


class _RichLineFactory:
    """Dựng dòng văn bản chứa widget nhập tại vị trí the {..}.

    Dùng chung cho paragraph và ô bảng; ghi nhận các tk.Text đã tạo để sau
    khi idle tinh chỉnh đúng số dòng hiển thị (wrap thật của Text).
    """

    def __init__(self, view: "DocumentView"):
        self.view = view
        self.texts: list[tk.Text] = []

    def build(self, parent, text: str, tags, bold_spans,
              width_px: int, justify: str = "left") -> int:
        bag = self.view.bag
        labels = self.view.labels
        chk_keys = self.view.chk_keys

        txt = tk.Text(
            parent, wrap="word", relief="flat", bd=0,
            highlightthickness=0, takefocus=False, cursor="arrow",
            background=SHEET_BG, font=f_base(),
        )
        base = tkfont.nametofont("TkTextFont")
        txt.tag_configure("b", font=(FONT_FAMILY, F_SIZE, "bold"))
        if justify != "left":
            txt.tag_configure("j", justify=justify)
            txt.tag_add("j", "1.0", "end")

        est = 0

        def put(seg: str, a: int, b: int):
            nonlocal est
            if not seg:
                return
            txt.insert("end", seg, ("j", "b") if _seg_bold(bold_spans, a, b)
                       else (("j",) if justify != "left" else ()))
            est += len(seg)

        n = 0
        pos = 0
        for a, b, key in tags:
            put(text[pos:a], pos, a)
            if key in chk_keys:
                cb = tk.Checkbutton(txt, variable=bag.var(key),
                                    onvalue=CHK, offvalue="",
                                    takefocus=False, bg=SHEET_BG,
                                    activebackground=SHEET_BG)
                txt.window_create("end", window=cb)
                est += 3
            else:
                label = labels.get(key) or key
                w = min(ENTRY_MAX_W, max(ENTRY_MIN_W, int(len(label) * 0.8) + 4))
                ent = ttk.Entry(txt, textvariable=bag.var(key), width=w)
                self.view._bind_slot(ent, bag.var(key))
                if _seg_bold(bold_spans, a, b):
                    ent.configure(font=f_bold())
                txt.window_create("end", window=ent)
                est += w
            n += 1
            pos = b
        put(text[pos:], pos, len(text))

        lines = max(1, math.ceil(est / max(20, px2chars(width_px))))
        # trừ 1 ký tự bù cho padding nội tại của Text để không vượt bề rộng trang
        txt.configure(height=min(lines, 14), width=max(8, px2chars(width_px) - 1),
                      state="disabled")
        self.texts.append(txt)
        return n, txt


ENTRY_MIN_W = 8
ENTRY_MAX_W = 40


class LoopRowsEditor(tk.Frame):
    """Vùng lặp trong bản mẫu A4: header + các dòng dữ liệu + Thêm/Xóa."""

    def __init__(self, master, columns: list[tuple[str, str]],
                 rows: list[dict] | None = None, on_change=None,
                 col_px: list[int] | None = None, total_px: int = CONTENT_W):
        super().__init__(master, background=SHEET_BG)
        self.columns = columns
        self.on_change = on_change
        self.total_px = total_px
        self._rows: list[dict[str, tk.StringVar]] = []
        # Bảng ngành (có cột ma_nganh): bật tra cứu gợi ý VSIC cho 2 ô
        tags = [t for t, _h in columns]
        self.vsic_tags = ([t for t in ("ten_nganh", "ma_nganh") if t in tags]
                          if "ma_nganh" in tags else [])

        if not col_px or len(col_px) != len(columns):
            each = max(36, total_px // max(1, len(columns)))
            col_px = [each] * len(columns)
        self.col_px = col_px

        head = tk.Frame(self, background="#EFEFEF",
                        highlightthickness=1, highlightbackground=RULE)
        head.pack(fill="x")
        for j, (_tag, hdr) in enumerate(columns):
            tk.Label(head, text=hdr, font=f_bold(), background="#EFEFEF",
                     wraplength=max(30, col_px[j] - 8), justify="left",
                     anchor="w").grid(row=0, column=j, sticky="nsew",
                                      padx=3, pady=2)
            head.grid_columnconfigure(j, weight=col_px[j])

        self.body = tk.Frame(self, background=SHEET_BG)
        self.body.pack(fill="x")

        bar = tk.Frame(self, background=SHEET_BG)
        bar.pack(fill="x", pady=(3, 0))
        tk.Button(bar, text="+ Thêm dòng", font=(FONT_FAMILY, 10),
                  command=self.add_row, relief="groove").pack(side="left")
        tk.Button(bar, text="− Xóa dòng cuối", font=(FONT_FAMILY, 10),
                  command=self.remove_last, relief="groove").pack(
            side="left", padx=6)

        if rows:
            for r in rows:
                self.add_row(r)
        else:
            self.add_row()

    def add_row(self, values: dict | None = None):
        frame = tk.Frame(self.body, background=SHEET_BG,
                         highlightthickness=1, highlightbackground=RULE)
        frame.pack(fill="x")
        vars_by_tag: dict[str, tk.StringVar] = {}
        entries_by_tag: dict[str, ttk.Entry] = {}
        for j, (tag, _hdr) in enumerate(self.columns):
            var = tk.StringVar(value=str((values or {}).get(tag, "") or ""))
            var.trace_add("write", lambda *_: self._changed())
            vars_by_tag[tag] = var
            ent = ttk.Entry(frame, textvariable=var,
                            width=px2chars(max(28, self.col_px[j] - 6)))
            ent.grid(row=0, column=j, padx=2, pady=1, sticky="we")
            frame.grid_columnconfigure(j, weight=max(1, self.col_px[j]))
            entries_by_tag[tag] = ent
        self._rows.append(vars_by_tag)
        # Tra cứu VSIC + kiểm tra mã ngành (nếu bảng có cột ma_nganh)
        if "ma_nganh" in vars_by_tag:
            ma_var = vars_by_tag["ma_nganh"]
            ma_ent = entries_by_tag["ma_nganh"]
            for tag in self.vsic_tags:
                attach_vsic_completion(entries_by_tag[tag], vars_by_tag[tag],
                                       vars_by_tag)
            ma_var.trace_add(
                "write", lambda *_a, v=ma_var, e=ma_ent: _mark_ma_validity(v, e))
            _mark_ma_validity(ma_var, ma_ent)

    def has_invalid_ma(self) -> bool:
        """True nếu có ô Mã ngành đang mang mã ngoài danh mục VSIC."""
        if "ma_nganh" not in dict(self.columns):
            return False
        valid = _vsic_ma_set()
        for row in self._rows:
            val = row["ma_nganh"].get().strip()
            if val and val not in valid:
                return True
        return False

    def remove_last(self):
        if self._rows:
            self.remove_row(len(self._rows) - 1)

    def remove_row(self, idx: int):
        if not (0 <= idx < len(self._rows)):
            return
        rows_data = [self.row_values(i) for i in range(len(self._rows)) if i != idx]
        for child in self.body.winfo_children():
            child.destroy()
        self._rows = []
        for rd in rows_data:
            self.add_row(rd)
        self._changed()

    def row_values(self, idx: int) -> dict[str, str]:
        return {tag: v.get() for tag, v in self._rows[idx].items()}

    def get_rows(self) -> list[dict]:
        return [self.row_values(i) for i in range(len(self._rows))]

    def set_rows(self, rows: list[dict]):
        for child in self.body.winfo_children():
            child.destroy()
        self._rows = []
        for r in rows or []:
            self.add_row(r)

    def _changed(self):
        if self.on_change:
            self.on_change()


class DocumentView(ttk.Frame):
    """Khung xem một biểu mẫu trên giấy A4: bố cục template + ô nhập tại chỗ."""

    def __init__(self, master, fmap: dict, bag: VarBag, tables: dict,
                 on_change=None):
        super().__init__(master)
        self.fmap = fmap
        self.bag = bag          # kho StringVar trung tâm của phiên
        self.tables = tables    # {(map_id, loop): list[dict]} dùng chung
        self.on_change = on_change
        self.labels = {f["key"]: (f.get("label") or "")
                       for f in fmap.get("fields", [])}
        self.chk_keys = {f["key"] for f in fmap.get("fields", [])
                         if f.get("type") == "chk"}
        self.loop_editors: dict[str, LoopRowsEditor] = {}  # loop -> editor
        self.n_entries = 0
        self.built = False
        self._rich = _RichLineFactory(self)

    # ------------------------------------------------------------------
    def has_invalid_ma(self) -> bool:
        """True nếu bất kỳ vùng lặp nào đang có mã ngành sai danh mục."""
        return any(ed.has_invalid_ma() for ed in self.loop_editors.values())

    def _bind_slot(self, entry: ttk.Entry, var: tk.StringVar):
        """Ô trống -> nền vàng nhạt (slot chờ điền); có dữ liệu -> trắng."""
        style_ready = getattr(DocumentView, "_slot_style_ok", False)
        try:
            if not style_ready:
                st = ttk.Style()
                st.configure("Slot.TEntry", fieldbackground=SLOT_BG)
                st.map("Slot.TEntry",
                       fieldbackground=[("readonly", SLOT_BG)])
                DocumentView._slot_style_ok = True
        except tk.TclError:
            pass

        def upd(*_a):
            try:
                filled = bool(var.get().strip())
                bad = getattr(entry, "_vsic_bad", False)
                if filled and not bad:
                    entry.configure(style="TEntry")
                elif not filled and not bad:
                    entry.configure(style="Slot.TEntry")
            except tk.TclError:
                pass
        var.trace_add("write", upd)
        upd()

    # ------------------------------------------------------------------
    def build(self):
        """Dựng khung xem (lazy: chỉ gọi khi người dùng mở tab / bấm nút)."""
        if self.built:
            return
        self.built = True
        for child in self.winfo_children():
            child.destroy()

        # Đăng ký cụm chk để radio loại trừ hoạt động cả trên bản mẫu
        from . import fields as fld
        chks = [f["key"] for f in self.fmap.get("fields", [])
                if f.get("type") == "chk"]
        for cluster in fld.chk_clusters(chks):
            self.bag.register_cluster(cluster)

        desk = ScrollableFrame(self, bg=DESK_BG)
        desk.pack(fill="both", expand=True)

        sheet = tk.Frame(desk.inner, background=SHEET_BG,
                         highlightthickness=1, highlightbackground=SHEET_EDGE)
        sheet.pack(anchor="center", pady=12)
        # ép tờ giấy đúng bề rộng A4 dù nội dung ngắn
        tk.Frame(sheet, width=MGN_L + CONTENT_W + MGN_R, height=1,
                 background=SHEET_BG).pack(fill="x")

        top_pad = tk.Frame(sheet, height=MGN_T, background=SHEET_BG)
        top_pad.pack(fill="x")
        content = tk.Frame(sheet, background=SHEET_BG)
        # pack padx dạng tuple để CHỈ co lề trái/phải đúng mm (không nhân đôi)
        content.pack(fill="x", padx=(MGN_L, MGN_R))
        self._content = content

        doc = Document(str(eio.APP_DIR / self.fmap["template"]))
        t_index = -1
        for kind, obj in iter_blocks(doc):
            if kind == "p":
                self._add_paragraph(content, obj)
            else:
                t_index += 1
                self._add_table(content, obj, t_index)

        bottom_pad = tk.Frame(sheet, height=MGN_B, background=SHEET_BG)
        bottom_pad.pack(fill="x")

        # Tinh chỉnh chiều cao Text theo wrap thật rồi mới chia trang
        self.after_idle(lambda: self._refine_heights(self._paginate))

    # ------------------------------------------------------------------
    def _add_paragraph(self, parent, p: Paragraph):
        text, tags, centered, right, bold_spans = _para_meta(p)
        if not text.strip():
            tk.Frame(parent, height=6, background=SHEET_BG).pack(fill="x")
            return
        if not tags:
            alpha_len = len(text.strip())
            covered = sum(min(e, len(text)) - s for s, e in bold_spans)
            kw = {"font": f_bold()} if alpha_len and covered >= alpha_len * 0.8 \
                else {"font": f_base()}
            tk.Label(parent, text=text, wraplength=CONTENT_W,
                     justify="center" if centered else "left",
                     background=SHEET_BG, fg="#111111",
                     anchor="w", **kw).pack(anchor="w", fill="x", pady=1)
            return
        justify = "center" if centered else "right" if right else "left"
        n, _txt = self._rich.build(parent, text, tags, bold_spans,
                                   width_px=CONTENT_W, justify=justify)
        _txt.pack(anchor="w", fill="x", pady=1)
        self.n_entries += n

    # ------------------------------------------------------------------
    def _add_table(self, parent, table: Table, t_index: int):
        tdefs = {t["loop"]: t for t in self.fmap.get("dynamic_tables", [])
                 if int(t.get("table_index", -1)) == t_index}
        recs = _layout_cells(table)

        # Hàng khuôn loop: {#ten} ... {/ten} nằm trọn trong MỘT hàng <w:tr>
        row_texts: dict[int, str] = {}
        for rec in recs:
            row_texts[rec["row"]] = row_texts.get(rec["row"], "") + "\n" + rec["text"]
        loop_rows: dict[int, str] = {}
        for ri, txt in row_texts.items():
            for m in LOOP_OPEN_RE.finditer(txt):
                if "{/%s}" % m.group(1) in txt:
                    loop_rows.setdefault(ri, m.group(1))

        ncols = max(1, len(table.columns))
        col_px = _table_col_px(table, ncols)
        outer = tk.Frame(parent, background=SHEET_BG)
        outer.pack(fill="x", pady=3)

        if ncols > 8:  # bảng rộng -> cuộn ngang trong phạm vi trang
            canvas = tk.Canvas(outer, highlightthickness=0,
                               background=SHEET_BG, height=60)
            hsb = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
            canvas.configure(xscrollcommand=hsb.set)
            hsb.pack(side="bottom", fill="x")
            canvas.pack(fill="x", expand=False)
            host = tk.Frame(canvas, background=SHEET_BG)
            canvas.create_window((0, 0), window=host, anchor="nw")

            def _cfg(_e=None):
                canvas.configure(scrollregion=canvas.bbox("all"))
                h = min(host.winfo_reqheight(), 430)
                canvas.configure(height=max(h, 60))
            host.bind("<Configure>", _cfg)
        else:
            host = outer

        gridf = tk.Frame(host, background=RULE,
                         highlightthickness=1, highlightbackground=RULE)
        gridf.pack(fill="x")
        for c in range(ncols):
            gridf.grid_columnconfigure(c, weight=col_px[c])
        for rec in recs:
            if rec["row"] in loop_rows:
                continue  # hàng khuôn -> thay bằng vùng lặp bên dưới
            self._place_cell(gridf, table, rec, col_px)
        for row_idx in sorted(loop_rows):
            self._add_loop_editor(host, loop_rows[row_idx],
                                  tdefs.get(loop_rows[row_idx]),
                                  recs, row_idx, ncols, col_px)

    def _place_cell(self, gridf, table: Table, rec: dict, col_px: list[int]):
        cell_w = sum(col_px[rec["col"]:rec["col"] + rec["colspan"]])
        frame = tk.Frame(gridf, background=SHEET_BG,
                         highlightthickness=1, highlightbackground=RULE)
        frame.grid(row=rec["row"], column=rec["col"],
                   columnspan=rec["colspan"], rowspan=rec["rowspan"],
                   sticky="nsew", padx=0, pady=0)
        inner = tk.Frame(frame, background=SHEET_BG)
        inner.pack(fill="both", expand=True)
        text = rec["text"]

        # Ô có thể gồm nhiều paragraph; dựng lần lượt
        paras = text.split("\n") if "\n" in text else [text]
        any_tag = any(TAG_RE.search(pp) for pp in paras)
        if not text.strip():
            tk.Label(inner, text=" ", background=SHEET_BG,
                     font=f_base()).pack(anchor="w", padx=3, pady=1)
            return
        if not any_tag:
            tk.Label(inner, text=text.strip(), wraplength=max(30, cell_w - 8),
                     justify="left", background=SHEET_BG, fg="#111111",
                     font=f_base(), anchor="w").pack(
                anchor="w", fill="x", padx=3, pady=1)
            return
        for pp in paras:
            if not pp.strip():
                tk.Frame(inner, height=4, background=SHEET_BG).pack(fill="x")
                continue
            mtags = [(m.start(), m.end(), m.group(1))
                     for m in TAG_RE.finditer(pp)]
            if not mtags:
                tk.Label(inner, text=pp.strip(), wraplength=max(30, cell_w - 8),
                         justify="left", background=SHEET_BG, fg="#111111",
                         font=f_base(), anchor="w").pack(
                    anchor="w", fill="x", padx=3, pady=0)
                continue
            n, _txt = self._rich.build(inner, pp, mtags, [],
                                       width_px=max(40, cell_w - 8))
            _txt.pack(anchor="w", fill="x", padx=2, pady=0)
            self.n_entries += n

    def _add_loop_editor(self, host, loop_name: str, tdef: dict | None,
                         recs: list[dict], row_idx: int, ncols: int,
                         col_px: list[int]):
        if tdef:
            cols = sorted(tdef.get("columns", []), key=lambda c: c.get("col", 0))
            columns = [(c["tag"], c.get("header") or c["tag"]) for c in cols]
            # bề rộng cột loop: map 'col' -> độ rộng gộp các cột template
            col_px_loop = []
            for c in cols:
                ci = int(c.get("col", 0))
                span = int(c.get("colspan", 1) or 1)
                lo = min(ci, max(0, ncols - 1))
                col_px_loop.append(sum(col_px[lo:lo + max(1, span)]))
        else:
            # Không khớp dynamic_tables -> suy cột từ các the trong hàng khuôn
            seen: list[str] = []
            for rec in recs:
                if rec["row"] != row_idx:
                    continue
                for m in TAG_RE.finditer(rec["text"]):
                    if m.group(1) not in seen:
                        seen.append(m.group(1))
            columns = [(k, k) for k in seen]
            col_px_loop = []
        key = (self.fmap["id"], loop_name)
        ed = LoopRowsEditor(host, columns, self.tables.get(key) or [],
                            col_px=col_px_loop or None,
                            total_px=sum(col_px))
        ed.on_change = lambda: self._store_rows(loop_name, ed)
        ed.pack(fill="x", pady=(4, 2))
        self.loop_editors[loop_name] = ed
        self._store_rows(loop_name, ed)  # ghi nhận dòng khởi tạo vào kho chung

    def _store_rows(self, loop_name: str, ed: LoopRowsEditor):
        self.tables[(self.fmap["id"], loop_name)] = ed.get_rows()
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------------
    # Hoàn thiện hình ảnh: chiều cao Text theo wrap thật + vạch phân trang
    # ------------------------------------------------------------------
    def _refine_heights(self, done):
        for txt in self._rich.texts:
            try:
                cnt = txt.count("1.0", "end", "displaylines")
                lines = int(cnt if isinstance(cnt, int) else (cnt[0] if cnt else 1))
                txt.configure(height=max(1, min(lines, 16)))
            except Exception:  # noqa: BLE001 — đo thất bại giữ ước lượng
                continue
        done()

    def _paginate(self):
        """Chèn khe xám giữa các trang A4 (không cắt block).

        Chạy sau khi mọi con của vùng nội dung đã có reqheight thật.
        Không phá hủy widget — chỉ pack lại theo thứ tự với separator
        ở ranh giới trang. Duyệt con TRỰC TIẾP của vùng nội dung (content),
        không phải của tờ giấy (sheet).
        """
        content = getattr(self, "_content", None)
        if content is None or not content.winfo_exists():
            return
        blocks = list(content.winfo_children())
        capacity = PAGE_H - MGN_T - MGN_B
        page_used = 0
        cut_before: set[int] = set()
        for i, c in enumerate(blocks):
            h = c.winfo_reqheight()
            if page_used > 0 and page_used + h > capacity:
                cut_before.add(i)
                page_used = h
            else:
                page_used += h + 2
        if not cut_before:
            return
        seq: list[tk.Widget] = []
        for i, c in enumerate(blocks):
            if i in cut_before:
                seq.append(self._make_page_sep(content))
            seq.append(c)
        for c in blocks:
            c.pack_forget()
        for w in seq:
            w.pack(fill="x")

    def _make_page_sep(self, master) -> tk.Frame:
        gap = tk.Frame(master, height=GAP_PAGE, background=DESK_BG)
        line_top = tk.Frame(gap, height=2, background="#6d6d6d")
        line_bot = tk.Frame(gap, height=2, background="#909090")
        line_top.pack(side="top", fill="x", pady=(GAP_PAGE // 2 - 2, 0))
        line_bot.pack(side="bottom", fill="x", pady=(0, GAP_PAGE // 2 - 2))
        gap.pack_propagate(False)
        return gap


def collect_from_map(fmap: dict, bag: VarBag, tables: dict) -> dict:
    """Dữ liệu render của 1 mẫu từ kho trung tâm (bag + tables)."""
    data: dict = {}
    for f in fmap.get("fields", []):
        eio.nested_set(data, f["key"], bag.get(f["key"]))
    for t in fmap.get("dynamic_tables", []):
        data[t["loop"]] = [dict(r) for r in tables.get((fmap["id"], t["loop"]), [])]
    return data
