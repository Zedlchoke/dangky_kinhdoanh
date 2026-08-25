"""Kiểm thử E2E cho case "thanh_lap_tnhh_1tv" (không mở cửa sổ).

Chạy:  python -m tools.e2e_case_test

Luồng mô phỏng:
1. Nạp use_cases + form_maps, resolve các mẫu của case -> form map.
2. Dựng data đầy đủ theo fields của từng mẫu, gọi engine render ra file
   trong generated_ho_so/_e2e_case_test/, kiểm tra python-docx mở OK và
   không còn tag {..} sót.
3. Mô phỏng lớp giao diện App (cửa sổ ẩn): chọn case, sinh form nhập (cả 2
   kiểu điền "Trên bản mẫu" / "Danh sách trường"), điền dữ liệu, thu thập dữ
   liệu render khớp toàn bộ field, autosave + nạp lại hồ sơ nháp thành công.
4. Dựng DocumentView OFFSCREEN cho PLI_M02 / PLI_M06 / PLII_M01: đếm ô nhập,
   điền thử -> collect đúng, đồng bộ key dùng chung giữa hai mẫu.
5. Tab 2 chế độ bản mẫu hiển thị LIÊN TỤC nhiều mẫu (case ctcp M04+M07+M08)
   + tra cứu VSIC cho ds_nganh (search -> pick -> collect; mã sai bật cờ).
"""

from __future__ import annotations

import datetime
import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_tk import engine_io as eio  # noqa: E402
from app_tk.document_view import DocumentView, VarBag, collect_from_map  # noqa: E402
from tools.docx_render import check_output, render  # noqa: E402

CASE_ID = "thanh_lap_tnhh_1tv"
OUT_DIR = ROOT / "generated_ho_so" / "_e2e_case_test"

TODAY = datetime.date.today()


def value_for(key: str) -> str:
    """Sinh giá trị hợp lý theo tên key (dùng cho data dựng sẵn)."""
    kl = key.lower()
    if "cccd" in kl:
        return "012345678901"
    if "ma_so" in kl or kl.endswith("mst"):
        return "0123456789"
    if "email" in kl:
        return "test@example.com"
    if "dien_thoai" in kl or kl == "fax":
        return "0987654321"
    if "website" in kl:
        return "https://test.vn"
    if "ten_tieng_viet" in kl or "ten_doanh_nghiep" in kl:
        return "CÔNG TY TNHH THƯƠNG MẠI TEST"
    if "ho_ten" in kl:
        return "NGUYỄN VĂN A"
    if "ngay_ky_vb" in kl:
        return str(TODAY.day)
    if "thang_ky_vb" in kl:
        return str(TODAY.month)
    if "nam_ky_vb" in kl:
        return str(TODAY.year)
    if "ngay_sinh" in kl or "ngay_cap" in kl:
        return "01"
    if "thang_sinh" in kl or "thang_cap" in kl:
        return "12"
    if "nam_sinh" in kl or "nam_cap" in kl:
        return "1990"
    if "dia_diem_ky" in kl:
        return "Hà Nội"
    if "co_quan_dkkd" in kl:
        return "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư Hà Nội"
    if "dia_chi_chi_tiet" in kl:
        return "Số 1, ngách 2, ngõ 3, đường Test"
    if "xa_phuong" in kl:
        return "Phường Test"
    if "tinh_thanh" in kl:
        return "Thành phố Hà Nội"
    if "von" in kl or "gia_tri" in kl:
        return "1000000000"
    return "TEST"


def _loop_def(fmap: dict, key: str):
    """Trả dynamic_table def nếu key dạng '<loop>.<tag>' thuộc bảng lặp."""
    if "." not in key:
        return None
    lp = key.split(".", 1)[0]
    for t in fmap.get("dynamic_tables", []):
        if t["loop"] == lp:
            return t
    return None


def field_value(data: dict, fmap: dict, fld_def: dict):
    """Giá trị của field trong data dựng/collect được.

    Field dạng '<loop>.<tag>' (metadata trùng cột bảng lặp) KHÔNG nằm ở
    đường dict lồng nhau nữa - data[<loop>] giờ là LIST các dòng, nên tra
    qua các dòng của bảng."""
    got = eio.nested_get(data, fld_def["key"])
    if got is not None:
        return got
    dt = _loop_def(fmap, fld_def["key"])
    if dt is not None:
        tag = fld_def["key"].split(".", 1)[1]
        for row in data.get(dt["loop"]) or []:
            if isinstance(row, dict) and row.get(tag) is not None:
                return row[tag]
    return None


def build_data(fmap: dict) -> dict:
    data: dict = {}
    # Bảng lặp trước: data[<loop>] là list dòng; field '<loop>.<tag>' lấy
    # giá trị qua các dòng này (không dùng nested_set vì sẽ tạo dict trùng
    # tên rồi bị list ghi đè).
    for t in fmap.get("dynamic_tables", []):
        data[t["loop"]] = [{c["tag"]: "TEST" for c in t["columns"]} for _ in range(2)]
    for f in fmap.get("fields", []):
        val = "X" if f.get("type") == "chk" else value_for(f["key"])
        dt = _loop_def(fmap, f["key"])
        if dt is not None and any(c["tag"] == f["key"].split(".", 1)[1]
                                  for c in dt["columns"]):
            tag = f["key"].split(".", 1)[1]
            for row in data[dt["loop"]]:
                row[tag] = val
            continue
        eio.nested_set(data, f["key"], val)
    return data


def phase_headless(maps: dict, case: dict) -> list[str]:
    """Pha 1-2: dựng data + render + kiểm tra file."""
    errors = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    forms = eio.forms_of_case(case, maps)
    if not forms:
        return ["case %s không có mẫu nào" % CASE_ID]
    for f in forms:
        fmap = f["map"]
        if not fmap:
            errors.append("thiếu form map %s" % f["map_id"])
            continue
        data = build_data(fmap)
        # Bảo đảm mọi field đều có giá trị (cột loop tra qua các dòng bảng)
        for fld_def in fmap["fields"]:
            if field_value(data, fmap, fld_def) is None:
                errors.append("thiếu dữ liệu cho key %s" % fld_def["key"])
        name = "Mau_%02d_%s.docx" % (f["mau"], eio.slugify(fmap["ten_mau"]))
        out_path = OUT_DIR / name
        try:
            out_path.write_bytes(render(eio.APP_DIR / fmap["template"], data))
        except Exception as exc:  # noqa: BLE001
            errors.append("render %s lỗi: %r" % (name, exc))
            continue
        ok, msg = check_output(out_path)
        if not ok:
            errors.append("%s: %s" % (name, msg))
        else:
            print("PASS render %s -> %s" % (fmap["id"], out_path.relative_to(ROOT)))
    return errors


def _fill_all_fields(app, selected):
    """Điền dữ liệu hợp lý vào mọi field của các mẫu đã tick qua kho trung tâm."""
    for fmap in selected:
        for f in fmap["fields"]:
            app.bag.set(f["key"], "X" if f.get("type") == "chk" else value_for(f["key"]))
        # Bảng lặp: điền 2 dòng TEST vào kho trung tâm loop_rows (nguồn sự
        # thật của collect/render) để cột '<loop>.<tag>' được phủ đủ; editor
        # đang mở (nếu có) được đồng bộ lại từ kho.
        for t in fmap.get("dynamic_tables", []):
            k = (fmap["id"], t["loop"])
            app.loop_rows[k] = [{c["tag"]: value_for(c["tag"]) for c in t["columns"]}
                                for _ in range(2)]
            ed = app.loop_editors.get(k)
            if ed is not None:
                ed.set_rows(app.loop_rows[k])


def _check_collect_coverage(app, selected, errors):
    """Collect của từng mẫu phải phủ đủ mọi field text/chk (cột loop tra
    qua các dòng bảng lặp trong data collect được)."""
    for f in app.case_forms:
        fmap = f["map"]
        var = app.form_vars.get(f["map_id"])
        if not var or not var.get() or not fmap:
            continue
        data = app.collect_data_for_render(fmap)
        for fld_def in fmap["fields"]:
            got = field_value(data, fmap, fld_def)
            if got is None:
                errors.append("collect thiếu key %s của %s" % (fld_def["key"], fmap["id"]))
            elif fld_def.get("type") == "chk" and got not in ("X", ""):
                errors.append("chk %s có giá trị lạ: %r" % (fld_def["key"], got))


def phase_ui(case: dict, maps: dict) -> list[str]:
    """Pha 3: mô phỏng App với cửa sổ ẩn (không mainloop), cả 2 kiểu điền."""
    errors = []
    try:
        from app_tk.ui_wizard import App
    except Exception as exc:  # noqa: BLE001
        return ["không khởi tạo được App: %r" % (exc,)]

    app = App()
    app.withdraw()
    try:
        # Chọn nhóm & case như người dùng bấm Listbox
        gi = app.groups.index(next(c["nhom"] for c in app.cases if c["id"] == CASE_ID))
        app.lb_groups.selection_clear(0, "end")
        app.lb_groups.selection_set(gi)
        app._on_group_select()
        ci = [c["id"] for c in app.cases if c.get("nhom") == case["nhom"]].index(CASE_ID)
        app.lb_cases.selection_clear(0, "end")
        app.lb_cases.selection_set(ci)
        app._on_case_select()

        if not app.case or app.case["id"] != CASE_ID:
            return ["App không chọn đúng case %s" % CASE_ID]

        # Tick mọi mẫu rồi dựng lại khu nhập
        for var in app.form_vars.values():
            var.set(True)

        selected = app._selected_maps()
        if not selected:
            errors.append("_selected_maps() rỗng dù đã tick")
            return errors

        # --- Kiểu điền "Danh sách trường" (UI cũ, phương án dự phòng) ---
        app.mode_combo.set("Danh sách trường")
        app._rebuild_input_tab()
        _fill_all_fields(app, selected)
        _check_collect_coverage(app, selected, errors)

        # --- Kiểu điền "Trên bản mẫu" (mặc định): mọi mẫu hiện liên tục ---
        app.mode_combo.set("Trên bản mẫu")
        app._rebuild_input_tab()
        if len(app.doc_sections) != len(selected):
            errors.append("doc_sections=%d khác số mẫu đã tick=%d"
                          % (len(app.doc_sections), len(selected)))
        app._drain_doc_builds()
        if not all(s["built"] for s in app.doc_sections):
            errors.append("chuỗi lazy chưa dựng hết các mẫu đã tick")
        _fill_all_fields(app, selected)
        _check_collect_coverage(app, selected, errors)

        # Cảnh báo hợp lệ: dữ liệu vừa điền không được sinh cảnh báo sai định dạng
        fmt_warns = [w for w in app.validate_warnings()
                     if ("9–12 chữ số" in w) or ("10 hoặc 13 số" in w) or ("thiếu dấu @" in w)]
        if fmt_warns:
            errors.append("validate sinh cảnh báo định dạng sai: %s" % fmt_warns[:3])

        # Autosave + nạp lại hồ sơ nháp
        app.autosave_now()
        draft = eio.load_json(eio.draft_path(CASE_ID))
        if not draft:
            errors.append("autosave không tạo được profiles/%s_draft.json" % CASE_ID)
        else:
            app.reset_case()          # xóa trắng rồi nạp lại từ draft đã lưu ngoài
            eio.save_json(eio.draft_path(CASE_ID), draft)
            app._rebuild_input_tab()
            app.apply_profile(draft)
            # Kiểm tra khôi phục trên một key field thật của mẫu đã tick
            # (không dùng biến đầu tiên trong bag — draft cũ có thể nạp thêm
            # key lạ từ schema/form_maps phiên trước)
            sample_key = next(
                (f["key"] for f in selected[0]["fields"]
                 if f.get("type") != "chk"), None)
            if sample_key and not app.bag.get(sample_key):
                errors.append("apply_profile không khôi phục được giá trị kho trung tâm")
            sample_loop = next((t["loop"] for f in selected
                                for t in f.get("dynamic_tables", [])), None)
            if sample_loop:
                mid = next(f["id"] for f in selected
                           if any(t["loop"] == sample_loop for t in f.get("dynamic_tables", [])))
                if not app.loop_rows.get((mid, sample_loop)):
                    errors.append("apply_profile không khôi phục được bảng lặp %s" % sample_loop)
    finally:
        app.destroy()
    return errors


def _count_entries(widget) -> int:
    n = 0
    if isinstance(widget, tk.Entry):  # bao gồm ttk.Entry
        n += 1
    for child in widget.winfo_children():
        n += _count_entries(child)
    return n


def phase_document_view(maps: dict) -> list[str]:
    """Pha 4: dựng DocumentView OFFSCREEN cho 3 mẫu đại diện.

    - PLI_M02 : nhiều the đoạn văn.
    - PLI_M06 : bảng + loop ds_thanh_vien.
    - PLII_M01: 2 bảng + radio chk.
    Kiểm tra: số Entry >= số field của mẫu; điền thử -> collect đúng;
    hai mẫu chia sẻ key co_quan_dkkd đồng bộ giá trị.
    """
    errors: list[str] = []
    root = tk.Tk()
    root.withdraw()
    try:
        bag = VarBag()
        tables: dict = {}
        views: dict[str, DocumentView] = {}

        for mid in ("PLI_M02", "PLI_M06", "PLII_M01"):
            fmap = maps[mid]
            view = DocumentView(root, fmap, bag, tables)
            view.build()
            views[mid] = view

            loop_prefixes = {t["loop"] for t in fmap.get("dynamic_tables", [])}
            scalar_keys = {
                f["key"] for f in fmap["fields"]
                if f.get("type") != "chk"
                and not any(f["key"].startswith(lp + ".") for lp in loop_prefixes)
            }
            expected = len(scalar_keys) + sum(
                len(t["columns"]) for t in fmap.get("dynamic_tables", []))
            n_ent = _count_entries(view)
            if n_ent < expected:
                errors.append("%s: chỉ %d Entry < %d field/cột mong đợi"
                              % (mid, n_ent, expected))
            # Vùng lặp phải được nhận diện thay cho hàng khuôn
            want_loops = {"PLI_M06": {"ds_thanh_vien"},
                          "PLII_M01": {"ds_nganh", "ds_tv_ho_gia_dinh"}}.get(mid)
            if want_loops is not None and set(view.loop_editors) != want_loops:
                errors.append("%s: vùng lặp %s != kỳ vọng %s"
                              % (mid, sorted(view.loop_editors), sorted(want_loops)))
            print("PASS build %s — %d Entry / %d field+column mong đợi"
                  % (mid, n_ent, expected))

        # Điền thử vài ô qua bag rồi collect ra đúng giá trị
        for mid, keys in (
            ("PLI_M02", ["dn.ten_tieng_viet", "co_quan_dkkd"]),
            ("PLI_M06", ["ndd.ho_ten"]),
            ("PLII_M01", ["chu_hkd.ho_ten"]),
        ):
            for k in keys:
                bag.set(k, "GIÁ-TRỊ-TEST")
            data = collect_from_map(maps[mid], bag, tables)
            for k in keys:
                got = eio.nested_get(data, k)
                if got != "GIÁ-TRỊ-TEST":
                    errors.append("%s: collect(%s) = %r != giá trị đã điền" % (mid, k, got))

        # Bảng lặp M06: điền dòng trong editor -> tables/collect nhận đúng
        m06 = maps["PLI_M06"]
        tables[("PLI_M06", "ds_thanh_vien")] = [
            {"ho_ten": "NGUYỄN VĂN A", "so_cccd": "012345678901"}]
        data = collect_from_map(m06, bag, tables)
        row0 = (data.get("ds_thanh_vien") or [{}])[0]
        if row0.get("ho_ten") != "NGUYỄN VĂN A":
            errors.append("M06: bảng lặp ds_thanh_vien không collect đúng: %r" % row0)

        # Hai mẫu chia sẻ key co_quan_dkkd phải đồng bộ qua cùng StringVar
        bag.set("co_quan_dkkd", "Phòng ĐKKD TEST")
        var_name = str(bag.var("co_quan_dkkd"))

        def has_bound_entry(widget, name):
            stack = [widget]
            while stack:
                w = stack.pop()
                if isinstance(w, tk.Entry) and str(w.cget("textvariable")) == name:
                    if w.get() == "Phòng ĐKKD TEST":
                        return True
                stack.extend(w.winfo_children())
            return False

        for mid in ("PLI_M02", "PLII_M01"):
            if not has_bound_entry(views[mid], var_name):
                errors.append("%s: không có Entry hiển thị giá trị đồng bộ co_quan_dkkd" % mid)

        # Cụm chk kiểu radio trên bản mẫu: bật một key phải xóa key kia
        chk_pair = next(
            (cl for cl in _all_clusters(maps["PLII_M01"]) if len(cl) >= 2), None)
        if chk_pair:
            bag.set(chk_pair[0], "X")
            if bag.get(chk_pair[1]):
                errors.append("radio chk không loại trừ giữa các mẫu/bản mẫu: %s" % chk_pair)
    except Exception as exc:  # noqa: BLE001
        errors.append("lỗi dựng DocumentView: %r" % (exc,))
    finally:
        root.destroy()
    return errors


def _all_clusters(fmap: dict) -> list[list[str]]:
    from app_tk import fields as fld
    chks = [f["key"] for f in fmap.get("fields", []) if f.get("type") == "chk"]
    return fld.chk_clusters(chks)


def _select_case(app, case: dict) -> list[str]:
    """Chọn case trên App như thao tác người dùng; trả về list lỗi."""
    errors = []
    gi = app.groups.index(next(c["nhom"] for c in app.cases if c["id"] == case["id"]))
    app.lb_groups.selection_clear(0, "end")
    app.lb_groups.selection_set(gi)
    app._on_group_select()
    ci = [c["id"] for c in app.cases if c.get("nhom") == case["nhom"]].index(case["id"])
    app.lb_cases.selection_clear(0, "end")
    app.lb_cases.selection_set(ci)
    app._on_case_select()
    if not app.case or app.case["id"] != case["id"]:
        errors.append("App không chọn đúng case %s" % case["id"])
    return errors


def phase_stacked_and_vsic(maps: dict, uc: dict) -> list[str]:
    """Pha 5: (a) tab 2 hiển thị liên tục nhiều mẫu (case ctcp M04+M07+M08);
    (b) tra cứu VSIC cho ds_nganh của PLII_M01 qua đường search -> pick."""
    from app_tk.document_view import apply_vsic_pick, collect_from_map, vsic_search
    from app_tk.ui_wizard import App

    errors: list[str] = []

    # ---- (a) Stacked view cho case thanh_lap_ctcp ----
    ctcp = next((c for c in uc["cases"] if c["id"] == "thanh_lap_ctcp"), None)
    if ctcp is None:
        return ["không tìm thấy case thanh_lap_ctcp"]
    app = App()
    app.withdraw()
    try:
        errors += _select_case(app, ctcp)
        for var in app.form_vars.values():
            var.set(True)  # tick cả M08 (không bắt buộc)
        app.mode_combo.set("Trên bản mẫu")
        app._rebuild_input_tab()
        n_sel = len(app._selected_maps())
        if len(app.doc_sections) != n_sel:
            errors.append("ctcp: doc_sections=%d != số mẫu đã tick=%d"
                          % (len(app.doc_sections), n_sel))
        elif n_sel != 3:
            errors.append("ctcp: kỳ vọng 3 mẫu (M04+M07+M08), thực tế %d" % n_sel)
        app._drain_doc_builds()
        built = [s for s in app.doc_sections if s["built"]]
        if len(built) != len(app.doc_sections):
            errors.append("ctcp: chưa dựng hết section sau drain")
        mau_so = sorted(s["fmap"]["mau_so"] for s in built)
        print("PASS stacked ctcp — %d dải tiêu đề, các mẫu: %s"
              % (len(built), mau_so))
        # thu gọn/mở lại một section vẫn hoạt động
        sec = app.doc_sections[0]
        app._toggle_doc_section(sec)
        if sec["open"]:
            errors.append("toggle không thu gọn được section")
        app._toggle_doc_section(sec)
        if not sec["open"]:
            errors.append("toggle không mở lại được section")
    finally:
        app.destroy()

    # ---- (b) VSIC: search -> pick -> collect đúng cặp ten/ma ----
    res = vsic_search("trong lua")
    if not any(ma == "0111" and "Trồng lúa" in ten for ma, ten in res):
        errors.append('vsic_search("trong lua") không trả về 0111 Trồng lúa: %r'
                      % res[:3])
    if res and res[0][0] != "0111":
        errors.append("vsic_search không ưu tiên cấp 4 lên đầu: %r" % res[:2])
    res_ma = vsic_search("0111")
    if not res_ma or res_ma[0][0] != "0111":
        errors.append('vsic_search("0111") không khớp mã: %r' % res_ma[:2])
    if len(vsic_search("kinh doanh")) > 12:
        errors.append("vsic_search trả quá 12 kết quả")

    m01 = maps["PLII_M01"]
    root = tk.Tk()
    root.withdraw()
    try:
        bag = VarBag()
        tables: dict = {}
        view = DocumentView(root, m01, bag, tables)
        view.build()
        ed = view.loop_editors.get("ds_nganh")
        if ed is None:
            errors.append("PLII_M01: thiếu editor vùng lặp ds_nganh")
        else:
            row_vars = ed._rows[0]
            ma, ten = vsic_search("xay dung")[0]  # chọn kết quả đầu tiên
            apply_vsic_pick(row_vars, ma, ten)     # đường đi của popup chọn gợi ý
            data = collect_from_map(m01, bag, tables)
            r0 = (data.get("ds_nganh") or [{}])[0]
            if r0.get("ma_nganh") != ma or r0.get("ten_nganh") != ten:
                errors.append("ds_nganh collect sai cặp sau khi chọn gợi ý: %r (kỳ vọng %s/%s)"
                              % (r0, ma, ten))
            # mã sai -> cờ cảnh báo bật ở editor + view
            row_vars["ma_nganh"].set("9999")
            if not ed.has_invalid_ma() or not view.has_invalid_ma():
                errors.append("mã 9999 không bật cờ cảnh báo VSIC")
            else:
                print("PASS vsic PLII_M01 — mã %s/%s vào bảng; mã sai bật cờ" % (ma, ten))
    finally:
        root.destroy()

    # ---- Cảnh báo VSIC ở cấp App (case chứa PLII_M01) ----
    hkd = next((c for c in uc["cases"] if c["id"] == "dang_ky_ho_kinh_doanh_lan_dau"),
               None)
    if hkd is not None and any(
            f.get("pl") == "II" and f.get("mau") == 1 for f in hkd["forms"]):
        app2 = App()
        app2.withdraw()
        try:
            errors += _select_case(app2, hkd)
            app2.mode_combo.set("Trên bản mẫu")
            app2._rebuild_input_tab()
            app2._drain_doc_builds()
            views_m01 = [s["view"] for s in app2.doc_sections
                         if s["fmap"]["id"] == "PLII_M01" and s["built"]]
            if not views_m01:
                errors.append("App không dựng được PLII_M01 trong khung chung")
            else:
                v = views_m01[0]
                ed2 = v.loop_editors["ds_nganh"]
                ed2._rows[0]["ma_nganh"].set("9999")
                if not any("VSIC" in w for w in app2.validate_warnings()):
                    errors.append("validate_warnings không có cảnh báo VSIC khi mã sai")
                else:
                    ed2._rows[0]["ma_nganh"].set("")
                    if any("VSIC" in w for w in app2.validate_warnings()):
                        errors.append("vẫn còn cảnh báo VSIC sau khi xóa mã sai")
                    else:
                        print("PASS vsic App-level — validate_warnings bật/tắt đúng cờ")
        finally:
            app2.destroy()
    return errors


def main() -> int:
    maps = eio.load_form_maps()
    uc = eio.load_use_cases()
    case = next((c for c in uc["cases"] if c["id"] == CASE_ID), None)
    if case is None:
        print("KHÔNG tìm thấy case", CASE_ID)
        return 2

    print("=== E2E case:", CASE_ID, "===")
    errors = phase_headless(maps, case)
    errors += phase_ui(case, maps)
    errors += phase_document_view(maps)
    errors += phase_stacked_and_vsic(maps, uc)

    # Dọn hồ sơ nháp do test tạo để không ảnh hưởng phiên làm việc thật
    p = eio.draft_path(CASE_ID)
    if p.exists():
        p.unlink()

    if errors:
        print("\nFAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("\nE2E PASS: render + UI collect + autosave/restore đều đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
