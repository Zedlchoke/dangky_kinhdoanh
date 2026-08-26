# -*- coding: utf-8 -*-
"""Census T0-A (CHỈ ĐỌC production) cho PLI_M01..M12.

Đối chiếu 3 nguồn cho từng mẫu:
  1. app/data/blocks/<FORM_ID>.json   - block p/chk/table/loop + input keys
  2. app/templates/<FORM_ID>.docx     - python-docx body walk + raw OOXML w:tbl
                                        (bao gồm header/footer)
  3. app/data/form_maps.json          - fields + dynamic_tables (loops)

Kèm nguồn pháp lý gốc (thư mục số 02..06, cùng luật chọn file
find_source của build_form_maps: thư mục đầu tiên thắng) để audit cột.

Script KHÔNG BAO GIỜ ghi vào app/data/blocks, app/templates hay
form_maps. Output duy nhất là fragment JSON ghi ra --out
(mặc định app/data/table_specs/fragments/t0_a.json).

Chạy: python tools/census/t0_a_census.py --out app/data/table_specs/fragments/t0_a.json
"""
import argparse
import json
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
TEMPLATES_DIR = ROOT / "app" / "templates"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"

SOURCE_FOLDERS = [
    "01_dang_ky_thanh_lap_doanh_nghiep",
    "02_thay_doi_thong_tin_doanh_nghiep",
    "03_chi_nhanh_van_phong_dai_dien_dia_diem",
    "04_tam_ngung_cham_dut_giai_the",
    "05_cong_bo_cung_cap_thong_tin",
    "06_ho_kinh_doanh_va_chuyen_doi",
]
FORM_IDS = ["PLI_M%02d" % i for i in range(1, 13)]
VALID_FORM_STATUS = ("NO_TABLE", "TABLE_COMPLETE", "BLOCKED_LEGAL_REVIEW")
VALID_SECTION_STATUS = (
    "missing_grid", "already_complete", "partial_columns",
    "partial", "output_only", "no_table", "unknown",
)

STT_ALONE_RE = re.compile(r"^stt$")
STT_WORD_RE = re.compile(r"^stt\b")
GLUED_STT_RE = re.compile(r"^stt(?=[a-z])")  # fold() đã bỏ dấu
LIST_HINT_RE = re.compile(r"\b(danh sach|liet ke)\b.{0,60}\b(sau|duoi day)\b")


def fold(text):
    norm = unicodedata.normalize("NFD", text or "")
    no_mark = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", no_mark.replace("đ", "d").replace("Đ", "D")).strip().lower()


def iter_source_docx():
    for folder in SOURCE_FOLDERS:
        d = ROOT / folder
        if d.is_dir():
            yield from sorted(p for p in d.rglob("*.docx")
                              if not p.name.startswith("~$") and not p.name.startswith("_"))


def parse_form_id(path):
    m = re.match(r"(?:DN_)?PL(\d)_Mau_(\d+)", path.stem)
    if not m:
        return None, None
    pl = "I" if m.group(1) == "1" else "II"
    return f"PL{pl}_M{int(m.group(2)):02d}", int(m.group(2))


def find_source(form_id):
    """File nguồn đầu tiên thắng theo luật find_source của build_form_maps."""
    mau = int(form_id.split("_M")[1])
    for path in iter_source_docx():
        fid, n = parse_form_id(path)
        if fid == form_id and n == mau:
            return path
    return None


def scan_docx(path):
    """Body walk + raw OOXML w:tbl count (body và header/footer)."""
    doc = Document(str(path))
    paragraphs = []       # (index, text) - index đếm MỌI w:p kể cả rỗng
    tables = []           # bảng body-level theo thứ tự
    idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            txt = re.sub(r"\s+", " ", Paragraph(child, doc).text).strip()
            if txt:
                paragraphs.append((idx, txt))
            idx += 1
        elif tag == "tbl":
            tbl = Table(child, doc)
            header_cells = []
            seen = set()
            if tbl.rows:
                for c in tbl.rows[0].cells:
                    if id(c._tc) in seen:
                        continue
                    seen.add(id(c._tc))
                    header_cells.append(re.sub(r"\s+", " ", c.text).strip())
            loop_row_tags = []
            if len(tbl.rows) > 1:
                row_txt = " ".join(c.text for c in tbl.rows[-1].cells)
                loop_row_tags = re.findall(r"\{[^{}]+\}", row_txt)
            tables.append({
                "rows": len(tbl.rows),
                "cols": len(tbl.columns),
                "header_cells": header_cells,
                "last_row_tags": loop_row_tags,
            })
    with zipfile.ZipFile(str(path)) as z:
        names = [n for n in z.namelist()
                 if re.match(r"word/(document|header\d*|footer\d*)\.xml$", n)]
        raw_tbl = 0
        for n in names:
            xml = z.read(n).decode("utf-8", "ignore")
            raw_tbl += len(re.findall(r"<w:tbl[ >]", xml))

    markers = []
    for i, txt in paragraphs:
        fd = fold(txt)
        kind = None
        if GLUED_STT_RE.match(fd):
            kind = "glued_stt_header"
        elif STT_ALONE_RE.match(fd):
            kind = "stt_alone"
        elif STT_WORD_RE.match(fd):
            kind = "stt_paragraph"
        elif LIST_HINT_RE.search(fd):
            kind = "list_intro"
        if kind:
            markers.append({"para": i, "kind": kind, "text": txt[:160]})
    return {
        "paragraph_count": idx,
        "nonempty_paragraphs": [(i, t) for i, t in paragraphs],
        "tables": tables,
        "raw_ooxml_w_tbl_all_parts": raw_tbl,
        "markers": markers,
    }


def scan_blocks(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    counts = {"p": 0, "chk": 0, "table": 0, "loop": 0}
    input_keys, chk_keys, loops = [], set(), []

    def walk(blocks):
        for b in blocks or []:
            t = b.get("t")
            counts[t] = counts.get(t, 0) + 1
            if t == "chk":
                if b.get("key"):
                    chk_keys.add(b["key"])
            elif t == "p":
                for r in b.get("runs", []) or []:
                    inp = r.get("input")
                    if isinstance(inp, dict) and inp.get("key"):
                        input_keys.append(inp["key"])
                    if r.get("chk") and (r["chk"] or {}).get("key"):
                        chk_keys.add(r["chk"]["key"])
            elif t == "table":
                for row in b.get("rows", []) or []:
                    for c in row.get("cells", []) or []:
                        for r in c.get("runs", []) or []:
                            inp = r.get("input")
                            if isinstance(inp, dict) and inp.get("key"):
                                input_keys.append(inp["key"])
            elif t == "loop":
                loops.append({
                    "loop": b.get("loop"),
                    "cols": sorted(c.get("col") for c in b.get("cols", []) or []),
                })

    walk(data.get("blocks", []))
    return {
        "ten_mau": data.get("ten_mau", ""),
        "counts": {k: counts.get(k, 0) for k in ("p", "chk", "table", "loop")},
        "input_keys": sorted(set(input_keys)),
        "chk_keys": sorted(chk_keys),
        "loops": loops,
    }


def audit_loops(fid, blocks_info, form_maps_entry, tpl_tables):
    """So cột loop/dynamic_tables với header w:tbl của template."""
    results = []
    dts = (form_maps_entry or {}).get("dynamic_tables") or []
    for dt in dts:
        ti = dt.get("table_index")
        tagged = set(c.get("col") for c in dt.get("columns", []) or [])
        missing = []
        if ti is not None and ti < len(tpl_tables):
            hdr = tpl_tables[ti]["header_cells"]
            for ci, cell in enumerate(hdr):
                if ci > 0 and ci not in tagged and cell.strip():
                    missing.append({"col": ci, "header": cell})
        results.append({
            "table_index": ti,
            "loop": dt.get("loop"),
            "tagged_cols": sorted(tagged),
            "missing_cols": missing,
        })
    return results


# ---------------------------------------------------------------------------
# Phân loại census (kết quả audit thủ công 3 nguồn, được script kiểm chứng
# lại bằng guards bên dưới trước khi ghi fragment).
# locator: start/end là regex trên text đã fold; 're:' = match từ đầu dòng,
# 'in:' = containment. end=None nghĩa là đến hết tài liệu.
# ---------------------------------------------------------------------------
S = dict  # gọn

CURATED = {
    "PLI_M01": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_nganh_dntn", title="4. Ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="ds_nganh",
              required_columns=["stt", "ten_nganh", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="ds_nganh",
              start=r"re:^4\. nganh, nghe kinh doanh", end=r"re:^5\. von dau tu",
              notes="Bảng w:tbl 6x4 rebuild Wave 2A: STT | Tên ngành | Mã ngành | Ngành chính khớp loop ds_nganh (cols 1,2,3 + _stt) và dynamic_tables."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (KCNC/KCX/KT/KCNC cao)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"re:^4\. nganh, nghe kinh doanh",
              notes="4 ô lựa chọn cố định không STT đã map đủ 4 chk_khu_*."),
            S(section_id="tai_san_gop_von_von_dau_tu", title="Tài sản góp vốn (trong vốn đầu tư)",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_tai_san_gop_von_dau_tu",
              required_columns=["stt", "loai_tai_san", "chi_tiet_ngoai_te_tai_san_khac", "gia_tri_vnd", "ty_le"],
              status="missing_grid",
              start=r"re:^tai san gop von:$", end=r"re:^6\. thong tin dang ky thue",
              notes="Toàn bộ là chuỗi paragraph rời (STT/Tên/Giá trị/Tỷ lệ + 6 dòng cố định: Đồng Việt Nam, ngoại tệ tự do chuyển đổi, vàng, QSDĐ, QSHTT, các tài sản khác + Tổng số); không có w:tbl, blocks không có bất kỳ input nào cho vùng này. Dòng 'Các tài sản khác' mẫu cho phép lập danh mục riêng → candidate sub-grid."),
            S(section_id="thue_chi_tieu_6_1_6_9", title="6. Thông tin đăng ký thuế (6.1-6.9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_dntn",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"re:^6\. thong tin dang ky thue", end=r"re:^7\. thong tin ve viec dong bao hiem",
              notes="9 chỉ tiêu cố định map đủ: gd.*, kt.*, địa chỉ TB thuế, ngày BD hoạt động, chk hạch toán (độc lập/hợp nhất/phụ thuộc), ap_dung_tu, so_lao_dong, chk BOT (co/khong), 4 chk GTGT. Lưu ý defect: cặp ô Có/Không 'hiển thị giá trị tương đương ngoại tệ' cùng trỏ key chk_khong."),
            S(section_id="bhxh_phuong_thuc_dong", title="7. Thông tin về việc đóng bảo hiểm xã hội (phương thức đóng)",
              kind="fixed-matrix", semantic_key_suggestion="phuong_thuc_dong_bhxh_dntn",
              required_columns=["hang_thang", "ba_thang_mot_lan", "sau_thang_mot_lan"],
              status="partial",
              start=r"re:^7\. thong tin ve viec dong bao hiem", end=r"re:^luu y:$",
              notes="3 phương thức cố định nhưng ô '□ 3 tháng một lần' là ký tự □ literal KHÔNG có token (blocks không có chk_bc_03_thang, trong khi M02/M06/M08/M09 đều có). Cần bổ sung binding."),
        ],
        legal_questions=[
            "Ô '3 tháng một lần' (mục 7 BHXH) thiếu hoàn toàn checkbox token trong template/blocks - xác nhận dùng chung key chk_bc_03_thang như các mẫu khác?",
            "'Các tài sản khác' trong Tài sản góp vốn: mẫu cho phép 'lập thành danh mục riêng kèm theo hồ sơ' - có cần sub-grid danh mục tài sản con không?",
            "Cặp ô Có/Không dùng chung key chk_khong (hiển thị ngoại tệ trên GCN; QSDĐ đảo/biên giới): tách key riêng để tránh liên động?",
        ],
    ),
    "PLI_M02": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_nganh_tnmv", title="4. Ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="ds_nganh",
              required_columns=["stt", "ma_nganh", "ten_nganh_vsic", "chi_tiet_hoat_dong", "la_nganh_chinh"],
              status="already_complete", loop_name="ds_nganh",
              start=r"re:^4\. nganh, nghe kinh doanh", end=r"re:^5\. chu so huu:",
              notes="Bảng w:tbl 6x5 (duy nhất trong range có cột 'Chi tiết hoạt động') khớp loop ds_nganh cols 1-4."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (KCNC/KCX/KT/KCNC cao)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"re:^4\. nganh, nghe kinh doanh",
              notes="Đủ 4 chk_khu_*. Cặp Có/Không QSDĐ đảo-biên giới ngay sau vẫn dùng chung chk_khong (ghi nhận defect)."),
            S(section_id="nddpl_uy_quyen_chu_so_huu", title="- Thông tin về người đại diện theo pháp luật/người đại diện theo ủy quyền của chủ sở hữu (header nối dính)",
              kind="nested-grid", semantic_key_suggestion="ds_nddpl_uy_quyen_chu_so_huu",
              required_columns=["stt", "ten_ndd_pl_or_uy_quyen", "ngay_thang_nam_sinh", "gioi_tinh", "so_ngay_cap_co_quan_cap_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "von_duoc_uy_quyen", "chu_ky_output_only", "ghi_chu", "tong_gia_tri_von_du_dai_dien", "ty_le", "thoi_diem_dai_dien_phan_von"],
              status="missing_grid",
              start=r"in:- thong tin ve nguoi dai dien theo phap luat/nguoi dai dien theo uy quyen cua chu so huu", end=r"in:- mo hinh to chuc cong ty",
              notes="Header bị nối thành 1 paragraph 'STTTên người đại diện...Thời điểm đại diện phần vốn' (13 cột). Blocks chỉ có 1 bộ field ndd.* đơn (không thêm/xóa dòng, không đủ cột vốn được ủy quyền/tổng giá trị được đại diện/thời điểm đại diện). Chân trang 5/6/7/8 quy định cột điều kiện."),
            S(section_id="mo_hinh_to_chuc_cong_ty", title="- Mô hình tổ chức công ty (HĐTV-GĐ/TGĐ vs Chủ tịch công ty-GĐ/TGĐ)",
              kind="fixed-matrix", semantic_key_suggestion="mo_hinh_to_chuc_cty_tnmv",
              required_columns=["hd_tv_giam_doc", "chu_tich_cong_ty_giam_doc"],
              status="missing_grid",
              start=r"in:- mo hinh to chuc cong ty", end=r"re:^6\. von dieu le",
              notes="2 lựa chọn cố định dạng ô □ literal, không có token/chk key nào trong blocks."),
            S(section_id="nguon_von_dieule", title="7. Nguồn vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="nguon_von_dieu_le",
              required_columns=["loai_nguon_von", "so_tien_vnd_va_tuong_duong", "ty_le"],
              fixed_rows=["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai", "von_khac", "tong_cong"],
              status="missing_grid",
              start=r"re:^7\. nguon von dieu le", end=r"re:^8\. tai san gop von",
              notes="5 dòng pháp lý cố định (vốn NSNN/tư nhân/nước ngoài/khác/tổng cộng) hiện là paragraph rời, không w:tbl, không input."),
            S(section_id="tai_san_gop_von_von_dieu_le", title="8. Tài sản góp vốn (trong vốn điều lệ)",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_tai_san_gop_von_dieu_le",
              required_columns=["stt", "loai_tai_san", "chi_tiet_ngoai_te_tai_san_khac", "gia_tri_vnd", "ty_le"],
              status="missing_grid",
              start=r"re:^8\. tai san gop von", end=r"re:^9\. nguoi dai dien theo phap luat",
              notes="6 dòng cố định + Tổng số, paragraph rời như M01, chưa có input."),
            S(section_id="thue_chi_tieu_10_1_10_9", title="10. Thông tin đăng ký thuế (10.1-10.9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_tnmv",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"re:^10\. thong tin dang ky thue", end=r"re:^11\. thong tin ve viec dong bao hiem",
              notes="Map đủ 9 chỉ tiêu (gd/kt/địa chỉ TB thuế/ngày BD/hạch toán/năm TC/lao động/BOT/GTGT)."),
            S(section_id="bhxh_phuong_thuc_dong", title="11. Thông tin về việc đóng bảo hiểm xã hội (phương thức đóng)",
              kind="fixed-matrix", semantic_key_suggestion="phuong_thuc_dong_bhxh_tnmv",
              required_columns=["hang_thang", "ba_thang_mot_lan", "sau_thang_mot_lan"],
              status="already_complete",
              start=r"re:^11\. thong tin ve viec dong bao hiem", end=r"re:^12\. thong tin ve chu so huu huong loi",
              notes="Đủ 3 chk_bc_hang_thang/03/06."),
            S(section_id="lua_chon_co_cshhl", title="12. Doanh nghiệp có chủ sở hữu hưởng lợi không?",
              kind="fixed-matrix", semantic_key_suggestion="co_cshhl",
              required_columns=["co", "khong"],
              status="already_complete",
              start=r"re:^12\. thong tin ve chu so huu huong loi", end=r"in:truong hop ho so dang ky doanh nghiep hop le",
              notes="Cặp chk_co/chk_khong riêng biệt, map đúng."),
        ],
        legal_questions=[
            "Row contract danh sách NĐDPL/người đại diện theo ủy quyền: NĐDPL không kê khai vốn được ủy quyền (chân trang 6) còn người ủy quyền có tỷ lệ % (chân trang 7) - phân biệt kiểu dòng thế nào?",
            "Nguồn vốn điều lệ: tỷ lệ (%) và Tổng cộng có phải computed/outputOnly, tổng phải đối chiếu vốn điều lệ?",
            "Mô hình tổ chức công ty: dựng fixed-matrix radio chọn-1 hay giữ 2 chk độc lập?",
        ],
    ),
    "PLI_M03": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_nganh_tnhh2tv", title="4. Ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="ds_nganh",
              required_columns=["stt", "ten_nganh", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="ds_nganh",
              start=r"re:^4\. nganh, nghe kinh doanh", end=r"re:^5\. von dieu le:",
              notes="Bảng w:tbl 6x4 rebuild Wave 2A khớp loop."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (KCNC/KCX/KT/KCNC cao)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"re:^4\. nganh, nghe kinh doanh",
              notes="Đủ 4 chk_khu_*."),
            S(section_id="nguon_von_dieule", title="6. Nguồn vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="nguon_von_dieu_le",
              required_columns=["loai_nguon_von", "so_tien_vnd_va_tuong_duong", "ty_le"],
              fixed_rows=["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai", "von_khac", "tong_cong"],
              status="missing_grid",
              start=r"re:^6\. nguon von dieu le", end=None,
              notes="5 dòng cố định paragraph rời, không input. Template NGUỒN kết thúc ngay sau 'Tổng cộng' (file DN_PL1_Mau_03..., mục cuối cùng là 6. Nguồn vốn điều lệ) - không có mục thuế/BHXH/CSHHL như Mẫu 2."),
        ],
        legal_questions=[
            "Template/nguồn PLI_M03 kết thúc ngay sau mục 6 Nguồn vốn điều lệ (không có thông tin đăng ký thuế/BHXH/CSHHL như Mẫu 2): đây là đầy đủ nội dung biểu mẫu hay file nguồn bị cắt khi tách từ file full? Cần đối chiếu bản gốc.",
        ],
    ),
    "PLI_M04": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_nganh_ctcp", title="4. Ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="ds_nganh",
              required_columns=["stt", "ten_nganh", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="ds_nganh",
              start=r"re:^4\. nganh, nghe kinh doanh", end=r"re:^5\. von dieu le:",
              notes="Bảng w:tbl 6x4 rebuild Wave 2A khớp loop."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (KCNC/KCX/KT/KCNC cao)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"re:^4\. nganh, nghe kinh doanh",
              notes="Đủ 4 chk_khu_*."),
            S(section_id="nguon_von_dieule", title="6. Nguồn vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="nguon_von_dieu_le",
              required_columns=["loai_nguon_von", "so_tien_vnd_va_tuong_duong", "ty_le"],
              fixed_rows=["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai", "von_khac", "tong_cong"],
              status="missing_grid",
              start=r"re:^6\. nguon von dieu le", end=r"re:^7\. thong tin ve co phan",
              notes="5 dòng cố định paragraph rời, không input."),
            S(section_id="co_cau_loai_co_phan", title="7. Thông tin về cổ phần (mệnh giá + loại cổ phần)",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_loai_co_phan",
              required_columns=["menh_gia_co_phan", "stt", "loai_co_phan", "so_luong", "gia_tri_vnd", "ty_le_so_von_dieule"],
              fixed_rows=["co_phan_pho_thong", "cp_uu_dai_bieu_quyet", "cp_uu_dai_co_tuc", "cp_uu_dai_hoan_lai", "cp_uu_dai_khac", "tong_so"],
              status="missing_grid",
              start=r"re:^7\. thong tin ve co phan", end=r"in:thong tin ve co phan duoc quyen chao ban",
              notes="menh_gia_co_phan đã map; bảng 5 loại cổ phần + Tổng số (Số lượng | Giá trị VNĐ | Tỷ lệ so VĐL%) vẫn là paragraph rời, không input."),
            S(section_id="co_phan_duoc_quyen_chao_ban", title="Thông tin về cổ phần được quyền chào bán",
              kind="fixed-matrix", semantic_key_suggestion="co_phan_duoc_quyen_chao_ban",
              required_columns=["stt", "loai_co_phan_chao_ban", "so_luong"],
              fixed_rows=["co_phan_pho_thong", "cp_uu_dai_bieu_quyet", "cp_uu_dai_co_tuc", "cp_uu_dai_hoan_lai", "cp_uu_dai_khac", "tong_so"],
              status="missing_grid",
              start=r"in:thong tin ve co phan duoc quyen chao ban", end=None,
              notes="5 loại + Tổng số, paragraph rời, không input. Template kết thúc sau 'Tổng số' này (nguồn tương tự) - không có mục thuế/BHXH như Mẫu 2."),
        ],
        legal_questions=[
            "Giá trị loại cổ phần = số lượng × mệnh giá, Tổng số đối chiếu vốn điều lệ: xác nhận formula/computed policy trước khi dựng fixed-matrix?",
            "Template/nguồn PLI_M04 kết thúc tại mục 7 (cổ phần được quyền chào bán) mà không có mục thuế/BHXH/CSHHL như Mẫu 2: đủ nội dung pháp lý hay file nguồn bị cắt?",
        ],
    ),
    "PLI_M05": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_nganh_hop_danh", title="4. Ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="ds_nganh",
              required_columns=["stt", "ten_nganh", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="ds_nganh",
              start=r"re:^4\. nganh, nghe kinh doanh", end=r"re:^5\. von dieu le:",
              notes="Bảng w:tbl 6x4 rebuild Wave 2A khớp loop."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (KCNC/KCX/KT/KCNC cao)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"re:^4\. nganh, nghe kinh doanh",
              notes="Đủ 4 chk_khu_*."),
            S(section_id="nguon_von_dieule", title="6. Nguồn vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="nguon_von_dieu_le",
              required_columns=["loai_nguon_von", "so_tien_vnd_va_tuong_duong", "ty_le"],
              fixed_rows=["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai", "von_khac", "tong_cong"],
              status="missing_grid",
              start=r"re:^6\. nguon von dieu le", end=None,
              notes="5 dòng cố định paragraph rời, không input. Template NGUỒN kết thúc ngay sau 'Tổng cộng' (giống M03). Lưu ý thêm: Mẫu 5 không có bảng thành viên hợp danh trong mẫu (theo Mẫu 9 gửi kèm) nhưng template cũng chưa có phần danh sách thành viên hợp danh nào."),
        ],
        legal_questions=[
            "Template/nguồn PLI_M05 kết thúc ngay sau mục 6 Nguồn vốn điều lệ: đủ nội dung biểu mẫu hay file nguồn bị cắt khi tách? Thành viên hợp danh kê khai theo Mẫu 9 gửi kèm - xác nhận M05 không cần lưới thành viên inline?",
        ],
    ),
    "PLI_M06": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_thanh_vien_tnhh", title="Danh sách thành viên công ty TNHH hai thành viên trở lên",
              kind="editable-grid", semantic_key_suggestion="ds_thanh_vien_tnhh",
              required_columns=["stt", "ho_ten", "ngay_thang_nam_sinh", "gioi_tinh", "so_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "phan_von_gop", "ty_le_von_gop", "thoi_han_gop_von", "chu_ky_output_only"],
              status="partial_columns", loop_name="ds_thanh_vien",
              start=None, end=r"in:- thong tin ve giay chung nhan dang ky dau tu",
              notes="Loop cũ tồn tại nhưng THIẾU cột 10 'Thời hạn góp vốn' (template có cột, ô loop rỗng không tag). So với header mẫu gốc (14 cột, glued trong nguồn M09): thiếu cột Ghi chú và nhóm cột 'Loại tài sản, số lượng, giá trị tài sản góp vốn' dưới nhóm Vốn góp; mẫu gốc có cấu trúc I.a cá nhân/I.b tổ chức + mục 'Thông tin người đại diện theo pháp luật/ủy quyền' (Vốn được ủy quyền, Tổng giá trị vốn được đại diện, Tỷ lệ, Thời điểm đại diện phần vốn) chưa có trong template phẳng hiện tại. Chữ ký là outputOnly ({chu_ky})."),
            S(section_id="thue_chi_tieu_9_1_9_9", title="9. Thông tin đăng ký thuế (9.1-9.9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_tnhh2tv",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"re:^9\. thong tin dang ky thue", end=r"re:^10\. thong tin ve viec dong bao hiem",
              notes="Map đủ 9 chỉ tiêu."),
            S(section_id="bhxh_phuong_thuc_dong", title="10. Thông tin về việc đóng bảo hiểm xã hội",
              kind="fixed-matrix", semantic_key_suggestion="phuong_thuc_dong_bhxh_tnhh2tv",
              required_columns=["hang_thang", "ba_thang_mot_lan", "sau_thang_mot_lan"],
              status="already_complete",
              start=r"re:^10\. thong tin ve viec dong bao hiem", end=r"re:^11\. thong tin ve chu so huu huong loi",
              notes="Đủ 3 chk_bc_*."),
            S(section_id="lua_chon_co_cshhl", title="11. Doanh nghiệp có chủ sở hữu hưởng lợi không?",
              kind="fixed-matrix", semantic_key_suggestion="co_cshhl",
              required_columns=["co", "khong"],
              status="already_complete",
              start=r"re:^11\. thong tin ve chu so huu huong loi", end=r"in:truong hop ho so dang ky doanh nghiep hop le",
              notes="Cặp chk_co/chk_khong map đúng."),
        ],
        legal_questions=[
            "Thành viên TNHH: giữ editable-grid phẳng đủ cột (bổ sung Thời hạn góp vốn/Ghi chú/Loại tài sản...) hay dựng nested-grid đúng mẫu gốc (cá nhân/tổ chức/người đại diện theo ủy quyền với tổng giá trị vốn được đại diện)?",
            "Cột Chữ ký xác nhận là outputOnly (không phải text input)?",
        ],
    ),
    "PLI_M07": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_co_dong_sang_lap", title="Danh sách cổ đông sáng lập công ty cổ phần",
              kind="editable-grid", semantic_key_suggestion="ds_co_dong_sang_lap",
              required_columns=["stt", "ho_ten", "ngay_thang_nam_sinh", "gioi_tinh", "so_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "tong_so_co_phan", "ty_le", "chu_ky_output_only"],
              status="partial_columns", loop_name="ds_co_dong_sang_lap",
              start=None, end=None,
              notes="Loop cũ THIẾU cột 6 'Dân tộc' (template có cột, ô loop rỗng). So với header mẫu gốc (19 cột, glued trong nguồn M09): thiếu Loại cổ phần, nhóm 'Loại tài sản, số lượng, giá trị tài sản góp vốn', Vốn góp, Thời hạn góp vốn, Ghi chú; mẫu gốc có cấu trúc cá nhân/tổ chức + mục người đại diện theo ủy quyền chưa có trong template phẳng. Toàn form chỉ gồm tiêu đề + bảng (blocks p=2)."),
        ],
        legal_questions=[
            "Cổ đông sáng lập: nâng cấp lên nested-grid đúng mẫu gốc (19 cột, cá nhân/tổ chức/NĐD ủy quyền) hay giữ bảng phẳng và chỉ bổ sung cột Dân tộc? Cần quyết định trước khi rollout.",
        ],
    ),
    "PLI_M08": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_co_dong_nn", title="Danh sách cổ đông là nhà đầu tư nước ngoài",
              kind="editable-grid", semantic_key_suggestion="ds_co_dong_nn",
              required_columns=["stt", "ten_co_dong", "quoc_gia", "ma_so_dn_gtpl", "dia_chi", "tong_so_co_phan", "ty_le", "chu_ky_output_only"],
              status="partial_columns", loop_name="ds_co_dong_nn",
              start=None, end=r"in:- thong tin ve giay chung nhan dang ky dau tu",
              notes="Khớp 8/8 cột template production HIỆN TẠI (loop đủ tag) nên không thiếu so với template; nhưng so với header mẫu gốc (18 cột cá nhân + biến thể tổ chức + mục NĐD ủy quyền, glued trong nguồn M09): bị đơn giản hóa mất Vốn góp, Thời hạn góp vốn, Ghi chú, Loại cổ phần, nhóm 'Loại tài sản, số lượng, giá trị tài sản góp vốn'. Đánh partial theo chuẩn audit-so-với-mẫu-gốc của PLAN."),
            S(section_id="thue_chi_tieu_11_1_11_9", title="11. Thông tin đăng ký thuế (11.1-11.9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_cdnn",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"re:^11\. thong tin dang ky thue", end=r"re:^12\. thong tin ve viec dong bao hiem",
              notes="Map đủ 9 chỉ tiêu."),
            S(section_id="bhxh_phuong_thuc_dong", title="12. Thông tin về việc đóng bảo hiểm xã hội",
              kind="fixed-matrix", semantic_key_suggestion="phuong_thuc_dong_bhxh_cdnn",
              required_columns=["hang_thang", "ba_thang_mot_lan", "sau_thang_mot_lan"],
              status="already_complete",
              start=r"re:^12\. thong tin ve viec dong bao hiem", end=r"re:^13\. thong tin ve chu so huu huong loi",
              notes="Đủ 3 chk_bc_*."),
            S(section_id="lua_chon_co_cshhl", title="13. Doanh nghiệp có chủ sở hữu hưởng lợi không?",
              kind="fixed-matrix", semantic_key_suggestion="co_cshhl",
              required_columns=["co", "khong"],
              status="already_complete",
              start=r"re:^13\. thong tin ve chu so huu huong loi", end=r"in:truong hop ho so dang ky doanh nghiep hop le",
              notes="Cặp chk_co/chk_khong map đúng."),
        ],
        legal_questions=[
            "Cổ đông NĐT nước ngoài: giữ bản phẳng 8 cột hiện tại hay dựng nested-grid đúng mẫu gốc (cá nhân/tổ chức, vốn góp, loại cổ phần, loại tài sản góp vốn)?",
        ],
    ),
    "PLI_M09": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_thanh_vien_hop_danh", title="Mẫu 9 (bảng chính): Danh sách thành viên công ty hợp danh",
              kind="editable-grid", semantic_key_suggestion="ds_thanh_vien_hop_danh",
              required_columns=["stt", "ho_ten", "ngay_thang_nam_sinh", "gioi_tinh", "so_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "phan_von_gop", "ty_le_von_gop", "thoi_han_gop_von", "chu_ky_output_only"],
              status="partial_columns", loop_name="ds_thanh_vien",
              start=None, end=r"in:- thong tin ve giay chung nhan dang ky dau tu",
              notes="TBL[0] 6x12 giống M06: loop THIẾU cột 10 'Thời hạn góp vốn'; so mẫu gốc còn thiếu Ghi chú/nhóm loại tài sản góp vốn và cấu trúc A.Thành viên hợp danh/B.Thành viên góp vốn/II.tổ chức/NĐD ủy quyền."),
            S(section_id="thue_chi_tieu_8_1_8_9", title="8. Thông tin đăng ký thuế (8.1-8.9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_hop_danh",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"re:^8\. thong tin dang ky thue", end=r"re:^9\. thong tin ve viec dong bao hiem",
              notes="Map đủ 9 chỉ tiêu."),
            S(section_id="bhxh_phuong_thuc_dong", title="9. Thông tin về việc đóng bảo hiểm xã hội",
              kind="fixed-matrix", semantic_key_suggestion="phuong_thuc_dong_bhxh_hop_danh",
              required_columns=["hang_thang", "ba_thang_mot_lan", "sau_thang_mot_lan"],
              status="already_complete",
              start=r"re:^9\. thong tin ve viec dong bao hiem", end=r"re:^10\. thong tin ve chu so huu huong loi",
              notes="Đủ 3 chk_bc_*."),
            S(section_id="lua_chon_co_cshhl", title="10. Doanh nghiệp có chủ sở hữu hưởng lợi không?",
              kind="fixed-matrix", semantic_key_suggestion="co_cshhl",
              required_columns=["co", "khong"],
              status="already_complete",
              start=r"re:^10\. thong tin ve chu so huu huong loi", end=r"in:cac thanh vien hop danh cam ket",
              notes="Cặp chk_co/chk_khong map đúng."),
            S(section_id="vung_nhiem_mau_6789_10", title="Vùng nghi nhiễm: bản copy Mẫu số 6, 7, 8, Mẫu 9 (lần 2) và Mẫu số 10 nằm trong template PLI_M09.docx",
              kind="unknown", semantic_key_suggestion=None,
              required_columns=[],
              status="missing_grid",
              start=r"in:mau so 6",
              end=None,
              notes="Sau chân trang của Mẫu 9 thật, template chứa tiếp toàn văn 'DANH SÁCH THÀNH VIÊN CÔNG TY TNHH HAI THÀNH VIÊN TRỞ LÊN' (Mẫu 6), 'DANH SÁCH CỔ ĐÔNG SÁNG LẬP' (Mẫu 7), 'DANH SÁCH CỔ ĐÔNG LÀ NHÀ ĐẦU TƯ NƯỚC NGOÀI' (Mẫu 8), một bản 'DANH SÁCH THÀNH VIÊN CÔNG TY HỢP DANH' thứ hai (header đầy đủ 14 cột dạng paragraph + glued 'STTTên thành viênSố, ngày cấp, nơi cấp...') và 'DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI' (Mẫu 10) - tất cả là paragraph rời, không w:tbl. File nguồn DN_PL1_Mau_09... cũng nhiễm đúng cấu trúc này → lỗi tách từ file full, KHÔNG phải nội dung của Mẫu 9."),
        ],
        legal_questions=[
            "Xác định phạm vi pháp lý thật của Mẫu 9: vùng Mẫu 6/7/8/9(lần 2)/10 trong template+nguồn PLI_M09 là dư thừa do tách nguồn sai - được phép loại khỏi template khi rebuild?",
            "Nếu bản Mẫu 9 thứ hai (header 14 cột đầy đủ) mới là cấu trúc đúng: chọn nó thay TBL[0] phẳng hiện tại hay giữ phẳng?",
        ],
    ),
    "PLI_M10": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="ds_cshhl_doanh_nghiep", title="Danh sách chủ sở hữu hưởng lợi của doanh nghiệp",
              kind="editable-grid", semantic_key_suggestion="ds_cshhl",
              required_columns=["stt", "ho_ten", "ngay_thang_nam_sinh", "gioi_tinh", "so_ngay_cap_co_quan_cap_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "ty_le_so_huu_von_dieule", "ty_le_co_phan_bieu_quyet", "quyen_chi_phoi", "ghi_chu"],
              status="partial_columns", loop_name="ds_cshhl",
              start=None, end=r"re:^15?- nguoi dai dien|^15 - nguoi dai dien|- nguoi dai dien theo phap luat cua doanh nghiep ky truc tiep",
              notes="Loop đủ tag 10/10 cột dữ liệu của template production hiện tại (11 cột kể STT) - khớp template. Nhưng so với header mẫu gốc 12 cột (glued trong nguồn M09): nhóm 'Chủ sở hữu hưởng lợi của doanh nghiệp được xác định...' có 3 cột con: Tỷ lệ sở hữu vốn điều lệ | Tỷ lệ sở hữu cổ phần có quyền biểu quyết | QUYỀN CHI PHỐI - template hiện tại thiếu cột Quyền chi phối (chân trang 4 NĐ 168/2025 yêu cầu ghi rõ quyền chi phối; hiện không có chỗ kê khai riêng)."),
        ],
        legal_questions=[
            "Quyền chi phối của CSHHL (điểm b khoản 1 Điều 17 NĐ 168/2025, chân trang 4 mẫu): là cột riêng trong bảng hay ghi vào cột Ghi chú?",
        ],
    ),
    "PLI_M11": S(
        form_status="TABLE_COMPLETE",
        sections=[
            S(section_id="ds_to_chuc_xd_cshhl", title="Danh sách để xác định chủ sở hữu hưởng lợi (cổ đông tổ chức ≥25%)",
              kind="editable-grid", semantic_key_suggestion="ds_to_chuc_xac_dinh_cshhl",
              required_columns=["stt", "ten_to_chuc", "ma_so_dn_qd_thanh_lap", "ngay_cap", "noi_cap", "dia_chi_tru_so_chinh", "ty_le_cp_bieu_quyet", "ghi_chu"],
              status="already_complete", loop_name="ds_cshhl",
              start=None, end=r"in:nguoi dai dien theo phap luat/ chu tich hoi dong quan tri",
              notes="8 cột template khớp TỪNG CỘT với header mẫu gốc (glued nguồn: STT|Tên tổ chức|Mã số DN/số QĐ thành lập|Ngày cấp|Nơi cấp|Địa chỉ trụ sở chính|Tỷ lệ sở hữu CP có quyền biểu quyết|Ghi chú (nếu có)); loop đủ tag 7/7 cột dữ liệu. Không còn vùng bảng khác trong mẫu."),
        ],
        legal_questions=[],
    ),
    "PLI_M12": S(
        form_status="BLOCKED_LEGAL_REVIEW",
        sections=[
            S(section_id="nganh_bo_sung", title="THÔNG BÁO THAY ĐỔI NGÀNH, NGHỀ KINH DOANH - 1. Bổ sung ngành nghề",
              kind="editable-grid", semantic_key_suggestion="nganh_bo_sung",
              required_columns=["stt", "ten_nganh_bo_sung", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="nganh_bo_sung",
              start=r"re:^1\. bo sung nganh, nghe kinh doanh sau", end=r"re:^2\. bo nganh, nghe kinh doanh sau",
              notes="Rebuild Wave 2B: w:tbl 6x4 khớp loop semantic."),
            S(section_id="nganh_xoa_bo", title="2. Bỏ ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="nganh_xoa_bo",
              required_columns=["stt", "ten_nganh_xoa_bo", "ma_nganh", "ghi_chu"],
              status="already_complete", loop_name="nganh_xoa_bo",
              start=r"re:^2\. bo nganh, nghe kinh doanh sau", end=r"re:^3\. sua doi chi tiet nganh, nghe kinh doanh sau",
              notes="Rebuild Wave 2B: cột Ghi chú thay Ngành chính, khớp loop semantic."),
            S(section_id="nganh_sua_doi_chi_tiet", title="3. Sửa đổi chi tiết ngành, nghề kinh doanh",
              kind="editable-grid", semantic_key_suggestion="nganh_sua_doi_chi_tiet",
              required_columns=["stt", "ten_nganh_sua_doi", "ma_nganh", "la_nganh_chinh"],
              status="already_complete", loop_name="nganh_sua_doi_chi_tiet",
              start=r"re:^3\. sua doi chi tiet nganh, nghe kinh doanh sau", end=r"in:doanh nghiep cam ket dap ung dieu kien tiep can thi truong",
              notes="Rebuild Wave 2B: khớp loop semantic."),
            S(section_id="lua_chon_khu_san_xuat", title="Doanh nghiệp nằm trong (mục thay đổi địa chỉ trụ sở)",
              kind="fixed-matrix", semantic_key_suggestion="lua_chon_khu_san_xuat",
              required_columns=["khu_cong_nghiep", "khu_che_xuat", "khu_kinh_te", "khu_cong_nghe_cao"],
              status="already_complete",
              start=r"in:doanh nghiep nam trong", end=r"in:cam ket tru so doanh nghiep",
              notes="Đủ 4 chk_khu_*."),
            S(section_id="nguon_von_dieule_sau_thay_doi", title="Nguồn vốn điều lệ sau khi thay đổi vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="nguon_von_dieu_le_sau_thay_doi",
              required_columns=["loai_nguon_von", "so_tien_vnd_va_tuong_duong", "ty_le"],
              fixed_rows=["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai", "von_khac", "tong_cong"],
              status="missing_grid",
              start=r"in:nguon von dieu le sau khi thay doi von dieu le", end=r"in:tai san gop von sau khi thay doi von dieu le",
              notes="5 dòng cố định paragraph rời, không input. Ngữ cảnh riêng của M12 (sau thay đổi), không dùng chung data với mẫu thành lập."),
            S(section_id="tai_san_gop_von_sau_thay_doi_vdl", title="Tài sản góp vốn sau khi thay đổi vốn điều lệ",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_tai_san_gop_von_sau_thay_doi_vdl",
              required_columns=["stt", "loai_tai_san", "chi_tiet_ngoai_te_tai_san_khac", "gia_tri_vnd", "ty_le"],
              status="missing_grid",
              start=r"in:tai san gop von sau khi thay doi von dieu le", end=r"in:thong tin ve co phan (chi ke khai doi voi cong ty co phan)",
              notes="6 dòng cố định + Tổng số, paragraph rời, không input."),
            S(section_id="co_cau_loai_co_phan_sau_thay_doi", title="Thông tin về cổ phần (chỉ kê khai đối với công ty cổ phần)",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_loai_co_phan_sau_thay_doi",
              required_columns=["menh_gia_co_phan", "stt", "loai_co_phan", "so_luong", "gia_tri_vnd", "ty_le_so_von_dieule"],
              fixed_rows=["co_phan_pho_thong", "cp_uu_dai_bieu_quyet", "cp_uu_dai_co_tuc", "cp_uu_dai_hoan_lai", "cp_uu_dai_khac", "tong_so"],
              status="missing_grid",
              start=r"in:thong tin ve co phan (chi ke khai doi voi cong ty co phan)", end=r"re:^2\. dang ky thay doi phan von gop",
              notes="menh_gia_co_phan đã map; bảng 5 loại cổ phần + Tổng số paragraph rời, không input."),
            S(section_id="tai_san_gop_von_sau_thay_doi_von_dau_tu", title="Tài sản góp vốn sau khi thay đổi vốn đầu tư (chủ DNTN)",
              kind="fixed-matrix", semantic_key_suggestion="co_cau_tai_san_gop_von_sau_thay_doi_vdt",
              required_columns=["stt", "loai_tai_san", "chi_tiet_ngoai_te_tai_san_khac", "gia_tri_vnd", "ty_le"],
              status="missing_grid",
              start=r"in:tai san gop von sau khi thay doi von dau tu", end=r"in:thong bao thay doi nguoi dai dien theo uy quyen cua chu so huu",
              notes="Ngữ cảnh vốn đầu tư RIÊNG (DNTN) - PLAN yêu cầu không dùng chung data với ngữ cảnh vốn điều lệ. Paragraph rời, không input."),
            S(section_id="ndd_uy_quyen_sau_thay_doi", title="THÔNG BÁO THAY ĐỔI NGƯỜI ĐẠI DIỆN THEO ỦY QUYỀN (header nối dính)",
              kind="nested-grid", semantic_key_suggestion="ds_ndd_uy_quyen_sau_thay_doi",
              required_columns=["stt", "chu_so_huu_tvtnhh_cdnn_to_chuc", "ten_ndd_uy_quyen", "ngay_thang_nam_sinh", "gioi_tinh", "so_ngay_cap_co_quan_cap_gtpl", "quoc_tich", "dan_toc", "dia_chi_lien_lac", "von_duoc_uy_quyen", "chu_ky_output_only", "ghi_chu", "tong_gia_tri_von_du_dai_dien", "ty_le", "thoi_diem_dai_dien_phan_von"],
              status="missing_grid",
              start=r"in:thong bao thay doi nguoi dai dien theo uy quyen cua chu so huu", end=r"in:thong bao thay doi co dong sang lap",
              notes="Header nối dính 14 cột ('STTChủ sở hữu/Thành viên công ty TNHH...Thời điểm đại diện phần vốn'). Blocks không có input/loop cho vùng này; PLAN yêu cầu audit dựng editable/nested grid thay vì field đơn."),
            S(section_id="thue_thay_doi_1_9", title="THÔNG BÁO THAY ĐỔI THÔNG TIN ĐĂNG KÝ THUẾ (chỉ tiêu 1-9)",
              kind="fixed-matrix", semantic_key_suggestion="chi_tieu_thue_thay_doi",
              required_columns=["stt", "chi_tieu", "noi_dung"],
              status="already_complete",
              start=r"in:thong bao thay doi thong tin dang ky thue", end=r"in:thong bao thay doi thong tin ve chu so huu huong loi",
              notes="9 chỉ tiêu map đủ (gd/kt/địa chỉ TB thuế/ngày BD/hạch toán/năm TC/lao động/BOT/GTGT)."),
        ],
        legal_questions=[
            "Người đại diện theo ủy quyền sau thay đổi: dựng nested-grid 14 cột đúng header nối hay editable-grid phẳng? Row contract theo loại chủ sở hữu (TNHH/CTCP tổ chức nước ngoài)?",
            "Hai ngữ cảnh tài sản góp vốn (sau thay đổi vốn điều lệ vs vốn đầu tư): xác nhận tách semantic key + draft riêng, không đồng bộ data?",
            "Nguồn vốn điều lệ sau thay đổi: Tổng cộng/Tỷ lệ computed và đối chiếu vốn điều lệ sau thay đổi?",
        ],
    ),
}

# Guard: input-key patterns chứng minh "chưa có grid" cho các section missing_grid
ABSENT_KEY_PATTERNS = {
    "tai_san_gop_von": ["tai_san", "ts_gop"],
    "nguon_von": ["nguon_von", "von_nnsn", "von_nsnn", "von_tu_nhan"],
    "co_phan": ["loai_co_phan", "so_luong_cp", "cp_pho_thong"],
    "mo_hinh": ["mo_hinh"],
}
SECTION_PATTERN_KEY = {
    "tai_san_gop_von_von_dau_tu": "tai_san_gop_von",
    "tai_san_gop_von_von_dieu_le": "tai_san_gop_von",
    "tai_san_gop_von_sau_thay_doi_vdl": "tai_san_gop_von",
    "tai_san_gop_von_sau_thay_doi_von_dau_tu": "tai_san_gop_von",
    "nguon_von_dieule": "nguon_von",
    "nguon_von_dieule_sau_thay_doi": "nguon_von",
    "co_cau_loai_co_phan": "co_phan",
    "co_cau_loai_co_phan_sau_thay_doi": "co_phan",
    "co_phan_duoc_quyen_chao_ban": "co_phan",
    "mo_hinh_to_chuc_cong_ty": "mo_hinh",
}

# Guard: key bắt buộc phải có khi đánh already_complete
REQUIRED_KEYS_BY_SECTION = {
    "thue": ["gd.ho_ten", "kt.ho_ten", "ap_dung_tu", "so_lao_dong"],
    "thue_chk": ["chk_ht_doc_lap", "chk_gtgt_khoan_tru", "chk_co"],
    "bhxh": ["chk_bc_hang_thang", "chk_bc_03_thang", "chk_bc_06_thang"],
    "cshhl": ["chk_co", "chk_khong"],
    "khu": ["chk_khu_cong_nghiep", "chk_khu_che_xuat", "chk_khu_kinh_te", "chk_khu_cong_nghe_cao"],
}


def resolve_locator(paras, spec, folded):
    """Trả về (from_idx, to_idx) theo locator start/end. to exclusive, None = hết."""
    def find(pattern, nth=1):
        mode = "re"
        pat = pattern
        if pat.startswith("in:"):
            mode, pat = "in", pat[3:]
        elif pat.startswith("re:"):
            pat = pat[3:]
        hits = []
        rx = re.compile(pat) if mode == "re" else None
        for i, t in paras:
            fd = folded[i]
            ok = (rx.search(fd) if mode == "re" else (pat in fd))
            if ok:
                hits.append(i)
        if len(hits) < nth:
            return None
        return hits[nth - 1]

    start = 0
    if spec.get("start"):
        if spec.get("special_start") == "second_occurrence":
            start = find(spec["start"], nth=2)
        else:
            start = find(spec["start"])
        if start is None:
            return None, None
    end = find(spec["end"]) if spec.get("end") else None
    return start, end


def build():
    maps = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
    sources = {}
    src_path_by_rel = {}
    for fid in FORM_IDS:
        sp = find_source(fid)
        sources[fid] = sp.relative_to(ROOT).as_posix() if sp else None
        if sp:
            src_path_by_rel[fid] = sp

    forms, unclassified = [], []
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    for fid in FORM_IDS:
        cur = CURATED[fid]
        blk = scan_blocks(BLOCKS_DIR / f"{fid}.json")
        tpl_scan = scan_docx(TEMPLATES_DIR / f"{fid}.docx")
        fm_entry = maps.get(fid)
        loop_audit = audit_loops(fid, blk, fm_entry, tpl_scan["tables"])

        paras = tpl_scan["nonempty_paragraphs"]
        folded = {i: fold(t) for i, t in paras}

        sections_out = []
        covered = []
        for spec in cur["sections"]:
            check(spec["status"] in VALID_SECTION_STATUS,
                  f"{fid}/{spec['section_id']}: status khong hop le")
            f, t = resolve_locator(paras, spec, folded)
            check(f is not None,
                  f"{fid}/{spec['section_id']}: khong tim thay heading start "
                  f"{spec.get('start')!r}")
            if spec.get("end"):
                check(t is not None and t > f,
                      f"{fid}/{spec['section_id']}: khong tim thay end hop le")
            covered.append((f if f is not None else 0,
                            t if t is not None else 10 ** 9))

            sec = {
                "section_id": spec["section_id"],
                "title": spec["title"],
                "kind": spec["kind"],
                "semantic_key_suggestion": spec.get("semantic_key_suggestion"),
                "required_columns": spec["required_columns"],
                "status": spec["status"],
                "source_evidence": {
                    "template": f"app/templates/{fid}.docx",
                    "heading": next((txt for i, txt in paras if i >= (f or 0)),"")[:180],
                    "anchor": "app/templates/%s.docx#p%s-p%s" % (
                        fid,
                        f if f is not None else 0,
                        t if t is not None else tpl_scan["paragraph_count"]),
                    "para_range": [f, t],
                },
                "notes": spec["notes"],
            }
            if spec.get("fixed_rows"):
                sec["fixed_rows"] = spec["fixed_rows"]
            if spec.get("loop_name"):
                la = next((x for x in loop_audit if x["loop"] == spec["loop_name"]), None)
                if la:
                    sec["loop_audit"] = la
            sections_out.append(sec)

            # ---- guards -------------------------------------------------
            keys = set(blk["input_keys"])
            chk = set(blk["chk_keys"])
            pkey = SECTION_PATTERN_KEY.get(spec["section_id"])
            if spec["status"] == "missing_grid" and pkey:
                hit = [k for k in keys if any(p in k for p in ABSENT_KEY_PATTERNS[pkey])]
                check(not hit,
                      f"{fid}/{spec['section_id']}: doi missing_grid nhung blocks co keys {hit}")
            if spec["status"] == "already_complete":
                base = spec["section_id"]
                req, reqchk = [], []
                if "thue" in base or "thue_" in base:
                    req += REQUIRED_KEYS_BY_SECTION["thue"]
                    reqchk += REQUIRED_KEYS_BY_SECTION["thue_chk"]
                if base.startswith("bhxh"):
                    reqchk += REQUIRED_KEYS_BY_SECTION["bhxh"]
                if base.startswith("lua_chon_co_cshhl"):
                    reqchk += REQUIRED_KEYS_BY_SECTION["cshhl"]
                if base.startswith("lua_chon_khu"):
                    reqchk += REQUIRED_KEYS_BY_SECTION["khu"]
                miss = [k for k in req if k not in keys] + \
                       [k for k in reqchk if k not in chk]
                check(not miss,
                      f"{fid}/{spec['section_id']}: already_complete nhung thieu keys {miss}")
            if spec.get("loop_name"):
                ln = spec["loop_name"]
                lp = next((x for x in blk["loops"] if x["loop"] == ln), None)
                check(lp is not None,
                      f"{fid}/{spec['section_id']}: loop {ln} khong ton tai trong blocks")
                if spec["status"] == "already_complete":
                    la = next(x for x in loop_audit if x["loop"] == ln)
                    check(not la["missing_cols"],
                          f"{fid}/{spec['section_id']}: already_complete nhung loop thieu cot "
                          f"{la['missing_cols']}")

        # guard đặc thù
        if fid == "PLI_M01":
            check("chk_bc_03_thang" not in chk,
                  "M01: mong doi KHONG co chk_bc_03_thang")
            check(any("3 tháng một lần" in txt for _, txt in paras),
                  "M01: khong thay o □ 3 tháng mot lan literal")
            check(any(x["loop"] == "ds_nganh" for x in blk["loops"]),
                  "M01: thieu loop ds_nganh")
        if fid == "PLI_M09":
            check(len(paras) > 150,
                  "M09: template nhat dinh phai chua vung nhiem (paras=%d)" % len(paras))
        if fid == "PLI_M11":
            la = loop_audit[0]
            check(not la["missing_cols"], "M11: loop thieu cot %s" % la["missing_cols"])
        if fid == "PLI_M06" or fid == "PLI_M09":
            la = next(x for x in loop_audit if x["loop"] == "ds_thanh_vien")
            check([m["col"] for m in la["missing_cols"]] == [10],
                  "M06/M09: mong doi loop thieu dung cot 10 (thoi han gop von)")
        if fid == "PLI_M07":
            la = loop_audit[0]
            check([m["col"] for m in la["missing_cols"]] == [6],
                  "M07: mong doi loop thieu dung cot 6 (dan toc)")

        # marker chưa classify?
        for m in tpl_scan["markers"]:
            p = m["para"]
            if not any(a <= p < b for a, b in covered):
                unclassified.append({"form_id": fid, **m})

        forms.append({
            "form_id": fid,
            "ten_mau": blk["ten_mau"],
            "form_status": cur["form_status"],
            "summary_counts": blk["counts"],
            "template_evidence": {
                "w_tbl_body_python_docx": len(tpl_scan["tables"]),
                "raw_ooxml_w_tbl_incl_headers_footers": tpl_scan["raw_ooxml_w_tbl_all_parts"],
                "paragraph_count": tpl_scan["paragraph_count"],
            },
            "source_docx": sources[fid],
            "sections": sections_out,
            "legal_questions": cur["legal_questions"],
        })
        check(cur["form_status"] in VALID_FORM_STATUS,
              f"{fid}: form_status khong hop le")

    check(not unclassified,
          "Con marker STT/glued/list-intro chua classify: %s" % unclassified)
    if errors:
        for e in errors:
            print("[GUARD-FAIL]", e, file=sys.stderr)
        raise SystemExit(2)

    frag = {
        "generated_by": "t0-a",
        "range": "PLI_M01-M12",
        "method": {
            "blocks": "app/data/blocks/<FORM_ID>.json (block types p/chk/table/loop, input keys)",
            "template": "app/templates/<FORM_ID>.docx (python-docx body walk + raw OOXML w:tbl incl header/footer)",
            "form_maps": "app/data/form_maps.json (fields + dynamic_tables)",
            "legal_source": "thư mục số 02..06, luật find_source: folder đầu tiên thắng (M01-M11: 06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn, M12: 02_thay_doi_thong_tin_doanh_nghiep)",
            "classification": "curated per-form audit + automated guards (counts, loop-vs-template column audit, absent/present key checks, marker coverage)",
            "idempotent": True,
            "write_scope": ["--out fragment only"],
        },
        "forms": forms,
        "unclassified_signatures": unclassified,
        "counts": {
            "forms": len(forms),
            "by_form_status": {},
            "sections_total": sum(len(f["sections"]) for f in forms),
            "sections_by_kind": {},
            "sections_by_status": {},
            "legal_questions_total": sum(len(f["legal_questions"]) for f in forms),
        },
    }
    for f in forms:
        frag["counts"]["by_form_status"][f["form_status"]] = \
            frag["counts"]["by_form_status"].get(f["form_status"], 0) + 1
        for s in f["sections"]:
            frag["counts"]["sections_by_kind"][s["kind"]] = \
                frag["counts"]["sections_by_kind"].get(s["kind"], 0) + 1
            frag["counts"]["sections_by_status"][s["status"]] = \
                frag["counts"]["sections_by_status"].get(s["status"], 0) + 1
    return frag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="app/data/table_specs/fragments/t0_a.json")
    ap.add_argument("--report", default=None,
                    help="dump evidence tho them de review (khong bat buoc)")
    args = ap.parse_args()

    frag = build()

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(frag, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")

    c = frag["counts"]
    print("[t0-a] forms=%d %s | sections=%d kinds=%s | statuses=%s | LQ=%d" % (
        c["forms"], c["by_form_status"], c["sections_total"],
        c["sections_by_kind"], c["sections_by_status"], c["legal_questions_total"]))
    print("[t0-a] unclassified_signatures=%d out=%s" % (
        len(frag["unclassified_signatures"]), out))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
