# -*- coding: utf-8 -*-
"""Trich xuat cau truc toan bo bieu mau docx va tao:
  - app/templates/<form_id>.docx : ban sao da gan the {placeholder} (dung cho docxtemplater)
  - app/data/form_maps.json      : metadata cac truong cua tung mau
  - app/data/form_maps.js        : ban JS (global FORM_MAPS) de app chay offline qua file://
  - generated_ho_so/_coverage_report.json : cac slot chua khop tu dien

Nguyen ly:
  - Slot = chuoi dau cham (".", "…" x3+) trong van ban. Nhan (label) la doan van ban
    truoc slot (tu cuoi slot truoc den dau slot hien tai).
  - RULES khop nhan -> key. Nhieu slot lien ke trong cung cau -> truong nhom (ngay/thang/nam).
    Rule co the khai bao ctx=<regex> de chi khop khi ngu canh phan (tieu de phan gan nhat,
    paragraph khong chua slot) khop regex — dung de phan biet cac nhan trung nhau o nhieu muc.
  - O checkbox □/☐ duoc gan the {chk_<ten>} (app dien "X" hoac ""), field kieu "chk".
  - Bang dong (danh sach thanh vien/nganh nghe...) phat hien qua HEADER_SYNONYMS,
    cot duoc gan the theo tieu de cot, hang mau duoc boc vao loop {#ten_list}.
  - Cac mau dang DANH SACH mat luoi bang khi convert nguoc (PLI_M06..M11, PLII_M01)
    duoc TAI DUNG bang REBUILD_TABLES: xoa paragraph tan du cua luoi cu roi chen
    bang moi (hang tieu de in dam + 5 hang trang, hang mau cuoi gan san the loop)
    vao ban sao trong bo nho truoc khi gắn the.
  - Cau hinh bang tai dung co the dat thanh FILE SPEC RIENG
    tools/form_specs/<nhom>/<FORM_ID>.json (nhom: formation | change | household |
    core). Generator uu tien doc file spec theo form_id; khong co file thi
    fallback ve khai bao inline REBUILD_TABLES nhu cu. Schema JSON: ghi chu o
    tools/form_specs/README.md.
  - P2/Lane B2: entry spec co the khai bao "kind" la "fixed-matrix",
    "nested-grid" hoac "output-table" ben canh "list" truyen thong — du dung
    bang dong phap ly co dinh, header nhieu tang rowspan/colspan va luoi chi
    de in. Hop dong truong: tools/form_specs/schema/table_kinds.schema.json.
    Entry dang BLOCKED_LEGAL_REVIEW khai "legal_status": {"blocked": true}
    se van duoc validate NHUNG bi BO QUA hoan toan khi rebuild (khong suy
    doan noi dung phap ly).
"""
import copy
import csv
import json
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

try:
    from tools import table_occurrences
except ImportError:  # chay truc tiep: python tools/build_form_maps.py
    import table_occurrences

ROOT = Path(__file__).resolve().parent.parent
OUT_TPL = ROOT / "app" / "templates"
OUT_DATA = ROOT / "app" / "data"

DOT_RUN = re.compile(r"[.…]{2,}|…(?:[./]…)+")
CHK_SYMBOLS = "□☐"

# ---------------------------------------------------------------------------
# Tu dien quy tac: (pattern_ascii_lowercase, key, groups, ctx)
# groups: danh sách key cho từng nhóm dấu chấm theo thứ tự; None = dùng key chính;
#         "" = nhóm đó được bỏ qua im lặng (ví dụ các ô /…/… trong ngày tháng).
# ctx   : regex (ascii không dấu) phải khớp NGỮ CẢNH PHẦN gần nhất thì rule mới xét.
# Thứ tự = độ ưu tiên (khớp trước thắng) → rule có ctx đặt TRƯỚC rule chung.
# ---------------------------------------------------------------------------
R = []

# Ngữ cảnh các phần hay trùng nhãn
CTX_HKD_CD = r"ho kinh doanh duoc chuyen doi|chuyen doi tu ho kinh doanh"
CTX_CSBT = r"bao tro xa hoi|quy xa hoi|quy tu thien"
CTX_DN_GOC = r"bi chia|bi tach|hop nhat|sap nhap|chuyen doi loai hinh|chuyen doi tu|tiep nhan"
CTX_NDD = r"nguoi dai dien theo phap luat"
CTX_GD = r"giam doc|tong giam doc"
CTX_KT = r"ke toan truong|phu trach ke toan"


def rule(pat, key=None, groups=None, ctx=None):
    R.append((pat, key, groups, ctx))


# ===========================================================================
# A. RULE CÓ NGỮ CẢNH — phân biệt nhãn trùng ở các phần khác nhau
# ===========================================================================
# Nhãn thuần dấu chấm/phẩy/số (đoạn giữa ngày tháng, đánh số mục, phần "Lưu:") -> bỏ qua im lặng
rule(r"^[/.,:;()\s\d]*$", None)
# --- Hộ kinh doanh được chuyển đổi thành DN ---
rule(r"^ten ho kinh doan.*in hoa|^ten ho kinh doan$", "hkd_cd.ten_hkd", ctx=CTX_HKD_CD)
rule(r"^so giay chung nhan dang ky ho kinh doan", "hkd_cd.so_gcn", ctx=CTX_HKD_CD)
rule(r"^ma so thue cua ho kinh doan", "hkd_cd.ma_so_thue", ctx=CTX_HKD_CD)
rule(r"^dia chi tru so ho kinh doan", "hkd_cd.dia_chi", ctx=CTX_HKD_CD)
rule(r"^ten chu ho kinh doan", "hkd_cd.ten_chu_ho", ctx=CTX_HKD_CD)
rule(r"so giay to phap ly cua ca nhan", "hkd_cd.so_giay_to", ctx=CTX_HKD_CD)
rule(r"^ngay het han", "hkd_cd.ngay_het_han", ["hkd_cd.ngay_het_han", "", ""], ctx=CTX_HKD_CD)
rule(r"^ngay cap", "hkd_cd.ngay_cap", ["hkd_cd.ngay_cap", "", ""], ctx=CTX_HKD_CD)
rule(r"^noi cap", "hkd_cd.noi_cap", ctx=CTX_HKD_CD)
# --- Cơ sở bảo trợ xã hội/quỹ được chuyển đổi ---
rule(r"^ten co so bao tro.*in hoa", "csbt.ten", ctx=CTX_CSBT)
rule(r"^so giay chung nhan dang ky thanh lap|so giay phep thanh lap va cong nhan", "csbt.so_gcn",
     ctx=CTX_CSBT)
rule(r"^ma so thue cua co so bao tro", "csbt.ma_so_thue", ctx=CTX_CSBT)
rule(r"^dia chi tru so chinh", "csbt.dia_chi", ctx=CTX_CSBT)
rule(r"^ten nguoi dai dien", "csbt.ten_nguoi_dai_dien", ctx=CTX_CSBT)
rule(r"so giay to phap ly cua ca nhan", "csbt.so_giay_to", ctx=CTX_CSBT)
rule(r"^ngay het han", "csbt.ngay_het_han", ["csbt.ngay_het_han", "", ""], ctx=CTX_CSBT)
rule(r"^ngay cap", "csbt.ngay_cap", ["csbt.ngay_cap", "", ""], ctx=CTX_CSBT)
rule(r"^noi cap", "csbt.noi_cap", ctx=CTX_CSBT)
# --- Doanh nghiệp gốc (bị chia/tách/hợp nhất/chuyển đổi loại hình) ---
rule(r"^ten doanh nghiep \(ghi bang chu in hoa\)|^ten doanh nghiep/chi nhanh.*in hoa",
     "dn_goc.ten_doanh_nghiep", ctx=CTX_DN_GOC)
rule(r"^ma so doanh nghiep/ma so thue|^ma so doanh nghiep:", "dn_goc.ma_so_dn", ctx=CTX_DN_GOC)
rule(r"dia chi tru so chinh", "dn_goc.dia_chi_tru_so", ctx=CTX_DN_GOC)
rule(r"^ngay cap", "dn_goc.ngay_cap", ["dn_goc.ngay_cap", "", ""], ctx=CTX_DN_GOC)
rule(r"^noi cap", "dn_goc.noi_cap", ctx=CTX_DN_GOC)
# --- Người đại diện theo pháp luật ---
rule(r"^ho, chu dem va ten \(ghi bang chu in hoa", "ndd.ho_ten", ctx=CTX_NDD)
rule(r"^ngay, thang, nam sinh|^sinh ngay", "ndd.ngay_sinh",
     ["ndd.ngay_sinh", "ndd.thang_sinh", "ndd.nam_sinh"], ctx=CTX_NDD)
rule(r"^gioi tinh", "ndd.gioi_tinh", ctx=CTX_NDD)
rule(r"dinh danh ca nhan", "ndd.so_cccd", ctx=CTX_NDD)
rule(r"^chuc danh", "ndd.chuc_vu", ctx=CTX_NDD)
rule(r"^quoc gia", "ndd.quoc_gia", ctx=CTX_NDD)
rule(r"^dan toc", "ndd.dan_toc", ["ndd.dan_toc", "ndd.quoc_tich"], ctx=CTX_NDD)
rule(r"ho chieu", "ndd.so_ho_chieu", ctx=CTX_NDD)
rule(r"^dien thoai", "ndd.dien_thoai", ["ndd.dien_thoai", "ndd.email"], ctx=CTX_NDD)
rule(r"^ngay het han", "ndd.ngay_het_han", ["ndd.ngay_het_han", "", ""], ctx=CTX_NDD)
rule(r"^ngay cap", "ndd.ngay_cap", ["ndd.ngay_cap", "", ""], ctx=CTX_NDD)
rule(r"^noi cap", "ndd.noi_cap", ctx=CTX_NDD)
# --- Giám đốc/Tổng giám đốc ---
rule(r"ten giam doc|ho, chu dem va ten giam doc", "gd.ho_ten", ctx=CTX_GD)
rule(r"^ngay, thang, nam sinh|^sinh ngay", "gd.ngay_sinh",
     ["gd.ngay_sinh", "gd.thang_sinh", "gd.nam_sinh"], ctx=CTX_GD)
rule(r"^gioi tinh", "gd.gioi_tinh", ctx=CTX_GD)
rule(r"dinh danh ca nhan", "gd.so_cccd", ctx=CTX_GD)
rule(r"^dien thoai", "gd.dien_thoai", ["gd.dien_thoai", "gd.email"], ctx=CTX_GD)
# --- Kế toán trưởng/Phụ trách kế toán ---
rule(r"ten ke toan truong|ho, chu dem va ten ke toan", "kt.ho_ten", ctx=CTX_KT)
rule(r"^ngay, thang, nam sinh|^sinh ngay", "kt.ngay_sinh",
     ["kt.ngay_sinh", "kt.thang_sinh", "kt.nam_sinh"], ctx=CTX_KT)
rule(r"^gioi tinh", "kt.gioi_tinh", ctx=CTX_KT)
rule(r"dinh danh ca nhan", "kt.so_cccd", ctx=CTX_KT)
rule(r"^dien thoai", "kt.dien_thoai", ["kt.dien_thoai", "kt.email"], ctx=CTX_KT)

# ===========================================================================
# B. RULE GỐC (trước đây) + RULE CHUNG MỚI
# ===========================================================================
# --- Ngày tháng nơi ký (đầu trang) ---
rule(r"^ngay\s+.*thang", "ngay_thang_vb", ["ngay_ky_vb", "thang_ky_vb", "nam_ky_vb"])
# --- Cơ quan tiếp nhận ---
rule(r"kinh gui|co quan dang ky kinh doanh cap", "co_quan_dkkd")
# --- Chủ thể cá nhân (HKD) ---
rule(r"ghi ho ten bang chu in hoa", "chu_hkd.ho_ten")
rule(r"^sinh ngay", "chu_hkd.ngay_sinh", ["ngay_sinh", "thang_sinh", "nam_sinh"])
rule(r"^gioi tinh", "chu_hkd.gioi_tinh")
rule(r"dinh danh ca nhan", "chu_hkd.so_cccd")
rule(r"dien thoai \(neu co\).*thu dien tu", None, ["dien_thoai_ca_nhan", "email_ca_nhan"])
rule(r"^dien thoai.*fax", None, ["dien_thoai_co_quan", "fax"])
rule(r"^dien thoai \(neu co\)", "dien_thoai_lien_he")
rule(r"^dan toc", "chu_hkd.dan_toc")
rule(r"^quoc tich", "chu_hkd.quoc_tich")
# --- Địa chỉ ---
rule(r"^so nha/phong.*to/xom/ap/thon", "dia_chi_chi_tiet")
rule(r"^xa/phuong/dac khu", "xa_phuong")
rule(r"^tinh/thanh pho truc thuoc trung uong", "tinh_thanh")
# --- Tên HKD ---
rule(r"ten ho kinh doanh viet bang tieng viet", "hkd_ten_tieng_viet")
rule(r"ten ho kinh doanh viet bang tieng nuoc ngoai", "hkd_ten_tieng_nuoc")
rule(r"ten ho kinh doanh viet tat", "hkd_ten_viet_tat")
# --- Trụ sở hộ ---
rule(r"^website", "website")
rule(r"^thu dien tu \(neu co\)", "email_tru_so")
# --- Vốn ---
rule(r"tong so \(bang so", "von_kinh_doanh")
rule(r"von dieu le \(bang so", "von_dieu_le")
# --- Thuế ---
rule(r"ngay bat dau hoat dong", "ngay_bd_hoat_dong", ["ngay_bd", "thang_bd", "nam_bd"])
rule(r"tong so lao dong", "so_lao_dong")

# --- Tên doanh nghiệp/công ty (PL1) ---
rule(r"^ten doanh nghiep viet bang tieng viet|^ten cong ty viet bang tieng viet"
     r"|^ten doanh nghiep \(ghi bang chu in hoa\)|^ten cong ty \(ghi bang chu in hoa\)"
     r"|^ten doanh nghiep$|^ten cong ty$|^ten doanh nghiep/ten chi nhanh.*in hoa",
     "dn.ten_tieng_viet")
rule(r"ten doanh nghiep/cong ty.*tieng nuoc ngoai|ten doanh nghiep viet bang tieng nuoc ngoai"
     r"|ten cong ty viet bang tieng nuoc ngoai", "dn.ten_nuoc_ngoai")
rule(r"ten doanh nghiep viet tat|ten cong ty viet tat", "dn.ten_viet_tat")
rule(r"^ma so doanh nghiep", "dn.ma_so_dn")
rule(r"^dia chi tru so chinh|^dia chi tru so:", "dn.dia_chi_tru_so")
rule(r"^von dau tu.*bang so", "von_dau_tu_so")
rule(r"^von dau tu.*bang chu", "von_dau_tu_chu")
rule(r"von dieu le.*bang chu", "von_dieu_le_chu")
rule(r"gia tri tuong duong", "gia_tri_ntte")
rule(r"menh gia co phan", "menh_gia_co_phan")
rule(r"^ma so du an", "ma_so_du_an")
rule(r"giay phep thanh lap va hoat dong so", "gp_ucsn_so")
rule(r"cap ngay:", "gp_ngay_cap", ["gp_ngay_cap", "", ""])
rule(r"^ten to chuc \(ghi bang chu in hoa\)", "to_chuc.ten")
rule(r"ma so doanh nghiep/so quyet dinh thanh lap", "to_chuc.ma_so")
# --- Thông tin hộ kinh doanh (ngoài ngữ cảnh chuyển đổi) ---
rule(r"^so giay chung nhan dang ky ho kinh doan", "hkd_so_gcn")
rule(r"^ma so ho kinh doan|^ma so thue cua ho kinh doan", "hkd_ma_so")
rule(r"^dia chi tru so ho kinh doan", "hkd_dia_chi")
rule(r"^ten chu ho kinh doan", "hkd_ten_chu_ho")
rule(r"^von kinh doanh sau khi thay doi", "von_kd_moi")
rule(r"^thoi diem thay doi von", "thoi_diem_thay_doi_von")
rule(r"^hinh thuc tang, giam von", "hinh_thuc_tang_giam_von")
rule(r"^ten ho kinh doan.*in hoa|^ten ho kinh doan$", "hkd_ten_tieng_viet_2")
# --- Cá nhân nói chung ---
rule(r"^ngay, thang, nam sinh", None, ["ngay_sinh", "thang_sinh", "nam_sinh"])
rule(r"^quoc gia", "quoc_gia")
rule(r"ho chieu", "so_ho_chieu")
rule(r"^chuc danh", "chuc_vu")
rule(r"^ho, chu dem va ten nguoi dung dau", "nguoi_dung_dau.ho_ten")
rule(r"^ngay het han", "ngay_het_han", ["ngay_het_han", "", ""])
rule(r"^ngay cap", "ngay_cap", ["ngay_cap", "", ""])
rule(r"^noi cap", "noi_cap")
rule(r"^co quan cap", "co_quan_cap")
# --- Chi nhánh/văn phòng đại diện/địa điểm kinh doanh ---
rule(r"chi nhan.*tieng nuoc ngoai|van phong dai dien.*tieng nuoc ngoai"
     r"|dia diem kinh doanh.*tieng nuoc ngoai", "cn.ten_nuoc_ngoai")
rule(r"chi nhan.*viet tat|van phong dai dien.*viet tat|dia diem kinh doanh.*viet tat",
     "cn.ten_viet_tat")
rule(r"^ten chi nhan|^ten van phong dai dien|^ten dia diem kinh doanh|^1\. ten chi nhan",
     "cn.ten_tieng_viet")
rule(r"^ma so chi nhan|^ma so van phong|^ma so dia diem", "cn.ma_so")
rule(r"^2\. dia chi|^dia chi chi nhan|^dia chi van phong|^dia chi dia diem", "cn.dia_chi")
rule(r"ten chi nhan chu quan", "cn_chu_quan.ten")
rule(r"tinh trang phap ly cua chi nhan", "cn_tinh_trang_phap_ly")
rule(r"nganh, nghe kinh doanh \(doi voi chi nhan\)", "cn_nganh_nghe")
rule(r"noi dung hoat dong.*van phong dai dien", "vppd_noi_dung")
rule(r"^so giay chung nhan dang ky kinh doanh", "so_gcn_dkkd")
rule(r"so giay chung nhan hoat dong chi nhanh", "cn_so_gcn_hd")
# --- Thời gian tạm ngừng/tiếp tục ---
rule(r"ap dung tu ngay", "ap_dung_tu", ["ap_dung_tu", "", ""])
rule(r"^den het ngay|^den ngay", "den_ngay", ["den_ngay", "", ""])
rule(r"ke tu ngay", "tu_ngay", ["tu_ngay", "", ""])
rule(r"^ly do tam ngung", "ly_do_tam_ngung")
rule(r"^ly do tiep tuc", "ly_do_tiep_tuc")
rule(r"^can cu khac", "can_cu_khac")
rule(r"nop ngay$", "hs_nop_ngay", ["hs_nop_ngay", "", ""])
# --- Văn bản do cơ quan đăng ký ban hành: chỉ cần số/ngày/quyết định ---
rule(r"^so quyet dinh", "so_quyet_dinh")
rule(r"^ma ho so", "ma_ho_so")
rule(r"^so$", "so_van_ban")
rule(r"^ma so$", "ma_so_van_ban")
rule(r"^noi nhan", "noi_nhan")
# --- Liên lạc còn lại (đặt cuối để không giành của rule cặp) ---
rule(r"^so fax|^fax", "fax")
rule(r"^thu dien tu", "email_khac")
rule(r"^dien thoai", "dien_thoai_khac")
# --- Bổ sung chung (đợt 2) ---
rule(r"^thang$", "thang_ky_vb")
rule(r"^nam$", "nam_ky_vb")
rule(r"^ngay$", "ngay_ky_vb")
rule(r"dia chi tru so( chinh)?$", "dn.dia_chi_tru_so")
rule(r"^dia chi lien lac", "dia_chi_lien_lac")
rule(r"^tru so cua ho kinh doan", "hkd_tru_so")
rule(r"^noi thuong tru", "noi_thuong_tru")
rule(r"^noi o hien tai|^noi o$", "noi_o_hien_tai")
rule(r"^von dieu le", "von_dieu_le")
rule(r"^so giay to phap ly cua ca nhan", "so_giay_to_ca_nhan")
rule(r"duoc cap giay chung nhan dang ky doanh nghiep lan dau", "ngay_cap_lan_dau",
     ["ngay_cap_lan_dau", "", ""])
rule(r"^ma so/ma so thue cua chi nhan|ma so/ma so thue cua chi nhan.*dia diem", "cn.ma_so_2")
rule(r"so giay chung nhan dang ky hoat dong", "so_gcn_hoat_dong")
rule(r"tam ngung kinh doanh nganh, nghe", "tn_nganh_nghe")
rule(r"da nhan cua ong/ba", "ngay_nhan_hs", ["ngay_nhan_hs", "", ""])
rule(r"dang ky lan dau, ngay", "dk_lan_dau_ngay",
     ["dk_lan_dau_ngay", "dk_lan_dau_thang", "dk_lan_dau_nam"])
rule(r"dang ky thay doi lan thu", "dk_thay_doi_lan_thu",
     ["dk_thay_doi_lan_thu", "dk_thay_doi_ngay", "dk_thay_doi_thang", "dk_thay_doi_nam"])
rule(r"^ve viec", "ve_viec")
rule(r"^can cu", "can_cu")
rule(r"^ly do de nghi", "ly_do_de_nghi")
rule(r"^ong/ba", "ong_ba")
rule(r"^tinh trang hoat dong", "tinh_trang_hoat_dong")
rule(r"^nguoi dung dau", "nguoi_dung_dau.ten")
rule(r"^ho, chu dem va ten.*in hoa", "ho_ten_in_hoa")
# --- Ô "ghi rõ" sau checkbox: bỏ qua im lặng (checkbox pass tự gắn the □) ---
rule(r"^loai khac", None)
rule(r"^luu$", "luu_vb")
# --- Bổ sung đợt 3 (form thay đổi / thông báo) ---
rule(r"hoi dong thanh vien.*giam doc|chu tich cong ty.*giam doc", "nguoi_ky_chuc_danh",
     ["nguoi_ky_chuc_danh", "nguoi_ky_ngay", "", "nguoi_ky_thang", "nguoi_ky_nam"])
rule(r"^tinh trang phap ly", "tinh_trang_phap_ly")
rule(r"da nhan ngay", "da_nhan_ngay", ["da_nhan_ngay", "", ""])
rule(r"^cap ngay", "cap_ngay_vv", ["cap_ngay_vv", "", ""])
rule(r"cua ong/ba", "ong_ba_nhan_hs")
rule(r"^ten to chuc", "to_chuc.ten")
rule(r"^ho, chu dem va ten nguoi dai dien", "nguoi_dai_dien.ho_ten")
rule(r"^ho, chu dem va ten$", "ho_ten_in_hoa_2")
rule(r"^ten chu so huu", "chu_so_huu.ho_ten")
rule(r"^so dien thoai", "dien_thoai_khac")
rule(r"^dia chi lien he", "dia_chi_lien_he")
rule(r"^ly do giai the", "ly_do_giai_the")
rule(r"^ly do cham dut", "ly_do_cham_dut_ton_tai")
rule(r"^ly do$", "ly_do")
rule(r"^yeu cau \(ten doanh nghiep\)", "yeu_cau_dn")
rule(r"^dia chi$", "dia_chi_khac")
rule(r"duoc cap lai ngay", "cap_lai_ngay", ["cap_lai_ngay", "", ""])
rule(r"^tong so co phan", "tong_so_co_phan")
rule(r"co quan thue quan ly truc tiep", "cq_thue_quan_ly")

ASCII_MAP = {}


def fold(text):
    """Chữ thường bỏ dấu để khớp quy tiện."""
    if text in ASCII_MAP:
        return ASCII_MAP[text]
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    out = out.replace("đ", "d")
    if len(ASCII_MAP) < 200000:
        ASCII_MAP[text] = out
    return out


def norm_label(s):
    s = re.sub(r"\s+", " ", s).strip(" :.;…-□☐+")
    s = re.sub(r"^\d+\s*[.)]\s*", "", s)   # bỏ đánh số đầu nhãn: "1. Tên..." -> "Ten..."
    s = re.sub(r"^[a-h]\)\s*", "", s)      # bỏ đánh số chữ: "a) Ngành..."
    s = re.sub(r"^[-–—•]+\s*", "", s)      # bỏ gạch đầu dòng
    return fold(s)


# ---------------------------------------------------------------------------
# Checkbox: quy tac (pattern_ascii, ten) -> the {chk_<ten>}, thu tu = uu tien
# ---------------------------------------------------------------------------
CHK_RULES = [
    (r"thanh lap moi", "tt_thanh_lap_moi"),
    (r"hop nhat doanh nghiep", "tt_hop_nhat_dn"),
    (r"sap nhap doanh nghiep", "tt_sap_nhap_dn"),
    (r"tach doanh nghiep", "tt_tach_dn"),
    (r"chia doanh nghiep", "tt_chia_dn"),
    (r"chuyen doi loai hinh doanh nghiep", "tt_chuyen_doi_loai_hinh"),
    (r"chuyen doi tu ho kinh doanh", "tt_chuyen_doi_tu_hkd"),
    (r"bao tro xa hoi|quy xa hoi|quy tu thien", "tt_chuyen_doi_tu_csbt"),
    (r"dong thoi thay doi dia chi nhan thong bao thue", "doi_dia_chi_tb_thue"),
    (r"ban doanh nghiep tu nhan", "cd_dntn_ban"),
    (r"tang cho doanh nghiep tu nhan", "cd_dntn_tang"),
    (r"chu doanh nghiep chet", "cd_dntn_chu_chet"),
    (r"chung minh nhan dan", "gt_cmnd"),
    (r"can cuoc cong dan", "gt_cccd"),
    (r"^ho chieu$|^so ho chieu", "gt_ho_chieu"),
    (r"loai khac", "gt_loai_khac"),
    (r"khu cong nghe cao", "khu_cong_nghe_cao"),
    (r"khu cong nghiep", "khu_cong_nghiep"),
    (r"khu che xuat", "khu_che_xuat"),
    (r"khu kinh te", "khu_kinh_te"),
    (r"phuong phap ke khai", "pp_ke_khai"),
    (r"phuong phap khoan", "pp_khoan"),
    (r"khoan tru|khau tru", "gtgt_khoan_tru"),
    (r"truc tiep tren gtgt", "gtgt_truc_tiep_tren_gtgt"),
    (r"truc tiep tren doanh so", "gtgt_truc_tiep_doanh_so"),
    (r"khong phai nop thue gtgt", "gtgt_khong_phai_nop"),
    (r"hang thang", "bc_hang_thang"),
    (r"0?3 thang mot lan", "bc_03_thang"),
    (r"0?6 thang mot lan", "bc_06_thang"),
    (r"khong kinh doanh tai tru so", "khong_kd_tai_tru_so"),
    (r"doanh nghiep xa hoi", "dn_xa_hoi"),
    (r"dau tu dac biet", "dau_tu_dac_biet"),
    (r"hach toan doc lap", "ht_doc_lap"),
    (r"bao cao tai chinh hop nhat", "ht_hop_nhat"),
    (r"hach toan phu thuoc", "ht_phu_thuoc"),
    (r"cong ty chung khoan", "ctck"),
    (r"de nghi quy co quan cap", "de_nghi_cap_gcn"),
    (r"^ca nhan$|chu the la ca nhan", "ct_ca_nhan"),
    (r"thanh vien ho gia dinh", "ct_ho_gia_dinh"),
    (r"^co$", "co"),
    (r"^khong$", "khong"),
]


# ---------------------------------------------------------------------------
# Bảng động: nhận diện theo tiêu đề cột
# Lưu ý: nguồn docx hiện tại đã mất bảng thật khi convert; các spec dưới chạy
# khi file nguồn có <w:tbl> (vd bản gốc từ văn bản chính thức).
# ---------------------------------------------------------------------------
DYNAMIC_TABLES = [
    {
        # Bảng ngành nghề PLII_M01 (Phụ lục II Mẫu 1): STT | Tên ngành |
        # Mã ngành | Ngành, nghề kinh doanh chính. Cột STT không phải dữ liệu
        # người dùng: gắn the engine {_stt} (stt_tag=True). Cột thứ tư theo
        # template pháp lý là ô đánh dấu X chọn ngành chính (chú thích 3 của
        # mẫu) -> map tag la_nganh_chinh như spec ds_nganh_vsic (PLI_M02).
        "id": "ds_nganh_nghe",
        "detect": {"stt", "ten nganh", "ma nganh"},
        "stt_tag": True,
        "cols": [
            (r"^stt$", None),
            (r"ten nganh", "ten_nganh"),
            (r"ma nganh", "ma_nganh"),
            (r"^nganh chinh$|nganh, nghe kinh doanh chinh", "la_nganh_chinh"),
        ],
        "loop": "ds_nganh",
        "fields": ["ten_nganh", "ma_nganh", "la_nganh_chinh"],
    },
    {
        # Bảng ngành nghề 5 cột dựng lại cho PLI_M02 (PLAN PHASE 3):
        # STT | Mã ngành | Tên ngành theo VSIC | Chi tiết hoạt động | Ngành chính.
        # Cột STT không phải dữ liệu người dùng: gắn the engine {_stt}
        # (stt_tag=True) để renderer tự sinh số thứ tự 1-based khi nhân hàng.
        "id": "ds_nganh_vsic",
        "detect": {"stt", "ma nganh", "ten nganh theo vsic"},
        "stt_tag": True,
        "cols": [
            (r"^stt$", None),
            (r"^ma nganh", "ma_nganh"),
            (r"ten nganh", "ten_nganh"),
            (r"chi tiet hoat dong|^chi tiet$", "chi_tiet"),
            (r"^nganh chinh$|nganh, nghe kinh doanh chinh", "la_nganh_chinh"),
        ],
        "loop": "ds_nganh",
        "fields": ["ma_nganh", "ten_nganh", "chi_tiet", "la_nganh_chinh"],
    },
    {
        "id": "ds_thanh_vien_tnhh",
        "detect": {"stt", "ten thanh vien", "gioi tinh"},
        "cols": [
            (r"^stt$", None),
            (r"ho ten|ten thanh vien", "ho_ten"),
            (r"dinh danh|cccd", "so_cccd"),
            (r"sinh|nam sinh", "ngay_sinh"),
            (r"gioi tinh", "gioi_tinh"),
            (r"quoc tich", "quoc_tich"),
            (r"dan toc", "dan_toc"),
            (r"thuong tru|noi o|dia chi", "dia_chi"),
            (r"phan von gop|dong gop von|von dong gop", "von_dong_gop"),
            (r"ty le", "ty_le_von"),
            (r"ky ten|chu ky", "chu_ky"),
            (r"dai dien", "dai_dien"),
        ],
        "loop": "ds_thanh_vien",
        "fields": ["ho_ten", "so_cccd", "ngay_sinh", "gioi_tinh", "quoc_tich",
                   "dan_toc", "dia_chi", "von_dong_gop", "ty_le_von"],
    },
    {
        "id": "ds_co_dong_sang_lap",
        "detect": {"stt", "ten co dong sang lap", "tong so co phan"},
        "cols": [
            (r"^stt$", None),
            (r"ho ten|ten co dong sang lap", "ho_ten"),
            (r"dinh danh|cccd", "so_cccd"),
            (r"sinh|nam sinh", "ngay_sinh"),
            (r"gioi tinh", "gioi_tinh"),
            (r"quoc tich", "quoc_tich"),
            (r"thuong tru|noi o|dia chi", "dia_chi"),
            (r"so co phan", "so_co_phan"),
            (r"ty le", "ty_le"),
            (r"ky ten|chu ky", "chu_ky"),
        ],
        "loop": "ds_co_dong_sang_lap",
        "fields": ["ho_ten", "so_cccd", "ngay_sinh", "quoc_tich", "dia_chi",
                   "so_co_phan", "ty_le"],
    },
    {
        "id": "ds_co_dong_nn",
        "detect": {"stt", "quoc gia", "tong so co phan"},
        "cols": [
            (r"^stt$", None),
            (r"ten cong ty|ten to chuc|ho ten|ten co dong", "ten_cd"),
            (r"ma so doanh nghiep|ma so thue", "ma_so"),
            (r"quoc gia", "quoc_gia"),
            (r"dia chi", "dia_chi"),
            (r"so co phan", "so_co_phan"),
            (r"ty le", "ty_le"),
            (r"giay to phap ly", "giay_to"),
            (r"ky ten|chu ky", "chu_ky"),
        ],
        "loop": "ds_co_dong_nn",
        "fields": ["ten_cd", "ma_so", "quoc_gia", "dia_chi", "so_co_phan", "ty_le"],
    },
    {
        "id": "ds_cshhl",
        "detect": {"stt", "ho va ten", "gioi tinh"},
        "cols": [
            (r"^stt$", None),
            (r"ho va ten|ho ten|ten co dong", "ho_ten"),
            (r"sinh|nam sinh", "ngay_sinh"),
            (r"gioi tinh", "gioi_tinh"),
            (r"quoc tich|quoc gia", "quoc_tich"),
            (r"dan toc", "dan_toc"),
            (r"thuong tru|noi o|dia chi", "dia_chi"),
            (r"giay to phap ly|dinh danh|cccd|ma so", "so_giay_to"),
            (r"ty le so huu co phan", "ty_le_co_phan"),
            (r"ty le", "ty_le"),
            (r"ghi chu", "ghi_chu"),
            (r"ky ten|chu ky", "chu_ky"),
        ],
        "loop": "ds_cshhl",
        "fields": ["ho_ten", "ngay_sinh", "gioi_tinh", "quoc_tich", "dan_toc",
                   "dia_chi", "so_giay_to", "ty_le", "ty_le_co_phan"],
    },
    {
        # Mẫu 11: tổ chức sở hữu từ 25% cổ phần có quyền biểu quyết trở lên
        "id": "ds_to_chuc_cshhl",
        "detect": {"stt", "ten to chuc", "ngay cap"},
        "cols": [
            (r"^stt$", None),
            (r"ten to chuc", "ten_to_chuc"),
            (r"ma so doanh nghiep|ma so thue", "ma_so_dn"),
            (r"^ngay cap", "ngay_cap"),
            (r"^noi cap", "noi_cap"),
            (r"dia chi", "dia_chi"),
            (r"ty le", "ty_le"),
            (r"ghi chu", "ghi_chu"),
        ],
        "loop": "ds_cshhl",
        "fields": ["ten_to_chuc", "ma_so_dn", "ngay_cap", "noi_cap", "dia_chi", "ty_le"],
    },
    {
        "id": "ds_tv_ho_gia_dinh",
        "detect": {"stt", "ho ten", "chu ky", "quoc tich"},
        "cols": [
            (r"^stt$", None),
            (r"ho ten", "ho_ten"),
            (r"sinh|nam sinh", "ngay_sinh"),
            (r"dinh danh|cccd", "so_cccd"),
            (r"gioi tinh", "gioi_tinh"),
            (r"quoc tich", "quoc_tich"),
            (r"dan toc", "dan_toc"),
            (r"thuong tru", "noi_thuong_tru"),
            (r"noi o hien tai|hien tai", "noi_o_hien_tai"),
            (r"ky ten|chu ky", "chu_ky"),
        ],
        "loop": "ds_tv_ho_gia_dinh",
        "fields": ["ho_ten", "ngay_sinh", "so_cccd", "gioi_tinh", "quoc_tich",
                   "dan_toc", "noi_thuong_tru", "noi_o_hien_tai"],
    },
]

HEADER_STT = {"stt", "số tt", "stt*"}


# ---------------------------------------------------------------------------
# Tái dựng bảng danh sách bị mất khi convert nguồn (nguồn chỉ còn chữ nối).
# Mỗi mục: spec = id trong DYNAMIC_TABLES; headers = tiêu đề cột (phải khớp
# detect + cols của spec); anchor = regex trên text đã fold để định vị điểm
# chèn; pos = "after"/"before"; trim = paragraph nối dài cần CẮT GIỮ phần sau
# keep_from (trên text gốc, chưa fold); drop = regex (đã fold) xóa cả paragraph.
# ---------------------------------------------------------------------------
REBUILD_TABLES = {
    # PLI_M02 & PLII_M01 đã chuyển sang tools/form_specs/core/ (PLI_M02.json,
    # PLII_M01.json). Các mẫu còn lại dưới đây là fallback inline — chuyển dần
    # sang file spec khi chạm tới.
    "PLI_M06": [
        {"spec": "ds_thanh_vien_tnhh", "pos": "before",
         "anchor": r"thong tin ve giay chung nhan dang ky dau tu",
         "headers": ["STT", "Tên thành viên", "Ngày, tháng, năm sinh", "Giới tính",
                     "Số định danh cá nhân/Giấy tờ pháp lý của cá nhân", "Quốc tịch",
                     "Dân tộc", "Địa chỉ liên lạc/Nơi thường trú", "Phần vốn góp (VNĐ)",
                     "Tỷ lệ vốn góp (%)", "Thời hạn góp vốn", "Chữ ký"]},
    ],
    "PLI_M07": [
        {"spec": "ds_co_dong_sang_lap", "pos": "after",
         "anchor": r"^mau so 7$",
         "headers": ["STT", "Tên cổ đông sáng lập", "Ngày, tháng, năm sinh", "Giới tính",
                     "Số định danh cá nhân/Giấy tờ pháp lý", "Quốc tịch", "Dân tộc",
                     "Địa chỉ liên lạc", "Tổng số cổ phần", "Tỷ lệ (%)", "Chữ ký"]},
    ],
    "PLI_M08": [
        {"spec": "ds_co_dong_nn", "pos": "before",
         "anchor": r"thong tin ve giay chung nhan dang ky dau tu",
         "headers": ["STT", "Tên cổ đông là nhà đầu tư nước ngoài", "Quốc gia",
                     "Mã số doanh nghiệp/Giấy tờ pháp lý",
                     "Địa chỉ trụ sở chính/Địa chỉ liên lạc", "Tổng số cổ phần",
                     "Tỷ lệ (%)", "Chữ ký"]},
    ],
    "PLI_M09": [
        {"spec": "ds_thanh_vien_tnhh", "pos": "before",
         "anchor": r"thong tin ve giay chung nhan dang ky dau tu",
         "headers": ["STT", "Tên thành viên", "Ngày, tháng, năm sinh", "Giới tính",
                     "Số định danh cá nhân/Giấy tờ pháp lý của cá nhân", "Quốc tịch",
                     "Dân tộc", "Địa chỉ liên lạc/Nơi thường trú", "Phần vốn góp (VNĐ)",
                     "Tỷ lệ vốn góp (%)", "Thời hạn góp vốn", "Chữ ký"]},
    ],
    "PLI_M10": [
        {"spec": "ds_cshhl", "pos": "after",
         "anchor": r"^mau so 10$",
         "headers": ["STT", "Họ và tên", "Ngày, tháng, năm sinh", "Giới tính",
                     "Quốc tịch", "Dân tộc", "Địa chỉ liên lạc",
                     "Giấy tờ pháp lý của cá nhân", "Tỷ lệ sở hữu vốn điều lệ (%)",
                     "Tỷ lệ sở hữu cổ phần có quyền biểu quyết (%)", "Ghi chú"]},
    ],
    "PLI_M11": [
        {"spec": "ds_to_chuc_cshhl", "pos": "after",
         "anchor": r"danh cho cong ty co phan ke khai",
         "headers": ["STT", "Tên tổ chức", "Mã số doanh nghiệp/số QĐ thành lập",
                     "Ngày cấp", "Nơi cấp", "Địa chỉ trụ sở chính",
                     "Tỷ lệ sở hữu cổ phần có quyền biểu quyết (%)", "Ghi chú"]},
    ],
}

# Tàn dư lưới cũ: đoạn chữ nối dài bắt đầu bằng "STT..." hoặc chuỗi số hàng "12345678910..."
REBUILD_DROP_DEFAULT = [r"^stt.{40,}", r"^\d{5,}$"]
REBUILD_BLANK_ROWS = 5

_SPEC_BY_ID = {s["id"]: s for s in DYNAMIC_TABLES}

# ---------------------------------------------------------------------------
# Spec bảng rebuild dạng FILE JSON: tools/form_specs/<nhóm>/<FORM_ID>.json
# Ưu tiên cao hơn REBUILD_TABLES inline; JSON thuần, không chạy code.
# Root: {"form_id", "group", "note"?, "gap_nghiepvu"?, "tables": [entry...]}.
# entry = một bảng tái dựng: {"spec": {...}, "pos"?, "anchor", "headers",
#          "drop"?, "drop_until"?, "no_default_drops"?, "trim"?, "keep_from"?}
# spec  = {"id", "detect": [token_fold...], "stt_tag"?, "cols": [[regex, tag]...],
#          "loop", "fields": [tag...]} — tag null = cột không gắn the.
# ---------------------------------------------------------------------------
FORM_SPECS_DIR = ROOT / "tools" / "form_specs"
_form_spec_cache = {}

# ---------------------------------------------------------------------------
# Occurrence (P1): mot entry spec duoc phep khai bao truong tuy chon
# "occurrences" — xem tools/table_occurrences.py (contract + y nghia).
# Bang moi tao cho tung occurrence duoc DANH DAU bang thuoc tinh XML TAM
# tren element w:tbl trong bo nho de process_form biet loop nao thuoc
# occurrence nao; thuoc tinh bi don sach truoc khi luu template.
# ---------------------------------------------------------------------------
_OCC_TEMP_ATTR = "{urn:orca:p1a-temp}occurrence"


def _mark_table_occurrence(tbl_element, info):
    tbl_element.set(_OCC_TEMP_ATTR, json.dumps(info, ensure_ascii=False))


def _pop_table_occurrence(table):
    """Doc + xoa thuoc tinh tam khoi element w:tbl. Tra ve dict
    {"occurrence_id", "sync_group", "spec_id"} hoac None."""
    el = table._tbl
    raw = el.get(_OCC_TEMP_ATTR)
    if raw is None:
        return None
    del el.attrib[_OCC_TEMP_ATTR]
    try:
        info = json.loads(raw)
    except ValueError:
        print("[occ-rebuild] thuoc tinh tam hong, bo qua: %r" % raw[:100])
        return None
    if isinstance(info, dict) and info.get("occurrence_id"):
        return info
    return None


def _scrub_occurrence_attrs(doc):
    """Don sach moi thuoc tinh tam con sot truoc khi luu template."""
    for el in doc.element.body.iter(qn("w:tbl")):
        for attr in (_OCC_TEMP_ATTR, GRID_META_TEMP_ATTR, HEADER_BAND_TEMP_ATTR):
            if el.get(attr) is not None:
                del el.attrib[attr]


def _json_spec(raw_spec, form_id="<form>"):
    """JSON spec -> dict spec đã chuẩn hoá theo kind khai báo trong file.

    - kind "list" (mặc định, backward-compat): giữ nguyên hình dạng cũ giống
      phần tử DYNAMIC_TABLES.
    - kind "fixed-matrix" | "nested-grid" | "output-table": trả về spec đã
      validate + chuẩn hoá (xem _validate_kind_spec). Spec sai phải bị chặn
      ở bước đọc file, TRƯỚC khi đụng tới document.
    """
    kind = raw_spec.get("kind") or KIND_LIST
    if kind == KIND_LIST:
        out = {
            "id": raw_spec["id"],
            "kind": KIND_LIST,
            "detect": set(raw_spec.get("detect") or []),
            "stt_tag": bool(raw_spec.get("stt_tag")),
            "cols": [(pat, tag) for pat, tag in raw_spec.get("cols") or []],
            "loop": raw_spec["loop"],
            "fields": list(raw_spec.get("fields") or []),
        }
        # Lane C (WLAY-008): opt-in tái phân bổ width theo nội dung
        if raw_spec.get("width_policy"):
            out["width_policy"] = raw_spec["width_policy"]
        return out
    return _validate_kind_spec(raw_spec, form_id)


# ===========================================================================
# Section kinds P2 (Lane B2 generator + DOCX/export)
#
# Ngoài "list" (bảng danh sách {#loop}), file spec
# tools/form_specs/<nhóm>/<FORM_ID>.json được phép khai báo thêm 3 kind:
#   fixed-matrix  : bảng dòng pháp lý cố định + ô tổng computed
#   nested-grid   : bảng lặp header nhiều hàng (rowspan/colspan vật lý)
#   output-table  : lưới chỉ để in/ký, KHÔNG có input nào
# Hợp đồng v1 đầy đủ: tools/form_specs/schema/table_kinds.schema.json.
#
# Nguyên tắc số 0 của lane này: một section đang BLOCKED_LEGAL_REVIEW PHẢI
# được khai báo legal_status.blocked=true và khi đó generator BỎ QUA hoàn toàn
# (in ra log, không chạm document) — capability có sẵn nhưng không suy đoán
# nội dung pháp lý.
# ===========================================================================
KIND_LIST = "list"
KIND_FIXED_MATRIX = "fixed-matrix"
KIND_NESTED_GRID = "nested-grid"
KIND_OUTPUT_TABLE = "output-table"
SECTION_KINDS = (KIND_LIST, KIND_FIXED_MATRIX, KIND_NESTED_GRID, KIND_OUTPUT_TABLE)

# ENTRY KEYS cho phép theo kind; kind mới siết chặt để bắt lỗi đánh máy
# (vd header_rows vs headerRows) thay vì nuốt im lặng như kind legacy.
_ENTRY_KEYS = {
    KIND_LIST: None,  # legacy: permissive như trước, không đổi hành vi
    KIND_FIXED_MATRIX: {"kind", "pos", "anchor", "spec", "cond_flag",
                        "no_default_drops", "drop", "drop_until", "trim",
                        "keep_from", "occurrences", "legal_status"},
    KIND_NESTED_GRID: {"kind", "pos", "anchor", "spec", "cond_flag",
                       "no_default_drops", "drop", "drop_until", "trim",
                       "keep_from", "occurrences", "legal_status"},
    KIND_OUTPUT_TABLE: {"kind", "pos", "anchor", "spec", "cond_flag",
                        "no_default_drops", "drop", "drop_until", "trim",
                        "keep_from", "occurrences", "legal_status"},
}
_ID_RE = re.compile(r"^[A-Za-z0-9_.]+$")


def _speck(key, fmt, form_id, sid):
    """Gắn ngữ cảnh form/spec vào một thông báo lỗi spec."""
    return "[form_specs] %s/%s: %s" % (form_id, sid or "?", key % fmt)


def _form_context(form_id, sid):
    def fail(msg):
        raise ValueError("[form_specs] %s/%s: %s" % (form_id, sid or "?", msg))
    return fail


def _validate_legal_status(raw, form_id, sid):
    ls = raw.get("legal_status")
    if ls is None:
        return {}
    allowed = {"blocked", "ref", "question"}
    if not isinstance(ls, dict) or set(ls) - allowed:
        raise ValueError(
            "[form_specs] %s/%s: legal_status phai la object co cac truong "
            "{blocked, ref, question}, nhan %r" % (form_id, sid, ls))
    if not isinstance(ls.get("blocked"), bool):
        raise ValueError("[form_specs] %s/%s: legal_status.blocked phai la "
                         "boolean" % (form_id, sid))
    return ls


def _validate_kind_spec(raw_spec, form_id="<form>"):
    """Validate + chuẩn hoá spec của 3 kind mới. Raise ValueError khi sai."""
    sid_raw = raw_spec.get("id")
    if not isinstance(sid_raw, str) or not _ID_RE.match(sid_raw):
        raise ValueError(
            "[form_specs] %s: spec.id khong hop le: %r "
            "(phai khop [A-Za-z0-9_.]+)" % (form_id, sid_raw))
    kind = raw_spec["kind"]

    def fail(msg):
        raise ValueError("[form_specs] %s/%s (%s): %s"
                         % (form_id, sid_raw, kind, msg))

    # Siết khóa trường theo kind: mọi khoá lạ là lỗi đánh máy -> chặn sớm.
    # ("width_policy": Lane C WLAY-008 — opt-in 'content' tái phân bổ width
    # bảng rộng theo nội dung; giá trị khác 'content' bị chặn ở dưới.)
    spec_keys = {
        KIND_FIXED_MATRIX: {"id", "kind", "semantic_key", "section_id",
                            "columns", "fixed_rows", "totals", "width_policy"},
        KIND_NESTED_GRID: {"id", "kind", "semantic_key", "section_id", "loop",
                           "stt", "header_rows", "columns", "discriminator",
                           "totals", "width_policy"},
        KIND_OUTPUT_TABLE: {"id", "kind", "semantic_key", "section_id",
                            "grid", "width_policy"},
    }
    if kind in spec_keys:
        unknown = set(raw_spec) - spec_keys[kind]
        if unknown:
            fail("spec co truong khong thuoc hop dong v1: %s" % sorted(unknown))

    def need(condition, msg):
        if not condition:
            fail(msg)

    def norm_column(c, idx):
        need(isinstance(c, dict), "columns[%d] phai la object" % idx)
        need(set(c) <= {"header", "tag", "col_index", "input_type", "computed",
                        "output_only", "required"},
             "columns[%d] co truong le: %s" % (idx, sorted(set(c))))
        header = c.get("header")
        need(isinstance(header, str) and header.strip(),
             "columns[%d].header bat buoc" % idx)
        tag = c.get("tag")
        need(tag is None or isinstance(tag, str),
             "columns[%d].tag phai la string hoac null" % idx)
        return {
            "header": header.strip(),
            "tag": tag,
            "col_index": c.get("col_index"),
            "input_type": c.get("input_type") or ("readonly" if tag is None
                                                  else "text"),
            "computed": bool(c.get("computed")),
            "output_only": bool(c.get("output_only")) or bool(c.get("computed"))
            or c.get("input_type") == "outputOnly",
            "required": bool(c.get("required")),
        }

    common = {
        "id": sid_raw,
        # section_id: định danh theo manifest table-specs (JOIN với runtime/UI);
        # mặc định = id để spec không phải khai hai lần.
        "section_id": raw_spec.get("section_id") or sid_raw,
        "kind": kind,
    }
    # Lane C (WLAY-008): width_policy 'content' — chỉ nhận đúng giá trị này
    wp = raw_spec.get("width_policy")
    if wp is not None:
        if wp != WIDTH_POLICY_CONTENT:
            fail("width_policy chi nhan 'content', nhan %r" % (wp,))
        common["width_policy"] = wp
    if "section_id" in raw_spec and not (
            isinstance(raw_spec["section_id"], str)
            and _ID_RE.match(raw_spec["section_id"])):
        fail("section_id khong hop le: %r" % (raw_spec["section_id"],))
    if kind == KIND_FIXED_MATRIX:
        sem = raw_spec.get("semantic_key")
        need(isinstance(sem, str) and _ID_RE.match(sem),
             "semantic_key khong hop le: %r" % (sem,))
        common["semantic_key"] = sem
        cols = raw_spec.get("columns")
        need(isinstance(cols, list) and cols,
             "columns phai la list khong rong")
        columns = [norm_column(c, i) for i, c in enumerate(cols)]
        untagged = [i for i, c in enumerate(columns) if c["tag"] is None]
        need(len(untagged) <= 1,
             "chi duoi 1 cot nhan khong gan the (cot loai/hang doc)")
        if untagged:
            need(untagged == [0],
                 "cot nhan khong gan the phai o chi so 0")
        tags = [c["tag"] for c in columns if c["tag"]]
        need(len(tags) == len(set(tags)), "column.tag trung nhau: %s" % tags)
        rows_raw = raw_spec.get("fixed_rows")
        need(isinstance(rows_raw, list) and rows_raw,
             "fixed_rows phai la list khong rong")
        fixed_rows = []
        seen_ids = set()
        for i, r in enumerate(rows_raw):
            need(isinstance(r, dict), "fixed_rows[%d] phai la object" % i)
            rid = r.get("id")
            need(isinstance(rid, str) and _ID_RE.match(rid),
                 "fixed_rows[%d].id khong hop le: %r" % (i, rid))
            need(rid not in seen_ids, "fixed_rows[%d].id '%s' trung" % (i, rid))
            seen_ids.add(rid)
            label = r.get("label")
            need(isinstance(label, str) and label.strip(),
                 "fixed_rows[%d].label bat buoc" % i)
            fixed_rows.append({"id": rid, "label": label.strip(),
                               "output_only": bool(r.get("output_only"))})
        raw_totals = raw_spec.get("totals") or []
        need(isinstance(raw_totals, (list, tuple)), "totals phai la list")
        totals = []
        for i, t in enumerate(raw_totals or []):
            need(isinstance(t, dict), "totals[%d] phai la object" % i)
            need(set(t) <= {"formula", "target_row", "target_tag"},
                 "totals[%d] co truong le: %s" % (i, sorted(set(t))))
            formula = t.get("formula")
            need(isinstance(formula, str) and formula.strip(),
                 "totals[%d].formula bat buoc" % i)
            target_row = t.get("target_row")
            need(target_row in seen_ids,
                 "totals[%d].target_row '%r' khong nam trong fixed_rows"
                 % (i, target_row))
            target_tag = t.get("target_tag")
            need(target_tag in set(tags),
                 "totals[%d].target_tag '%r' khong phai cot dau vao hop le"
                 % (i, target_tag))
            by_id = {r["id"]: r for r in fixed_rows}
            need(by_id[target_row]["output_only"],
                 "hang tong '%s' phai khai bao output_only=true" % target_row)
            totals.append({"formula": formula.strip(),
                           "target_row": target_row,
                           "target_tag": target_tag})
        common.update({"columns": columns, "fixed_rows": fixed_rows,
                       "totals": totals})
        return common

    if kind == KIND_NESTED_GRID:
        sem = raw_spec.get("semantic_key")
        need(isinstance(sem, str) and _ID_RE.match(sem),
             "semantic_key khong hop le: %r" % (sem,))
        loop = raw_spec.get("loop") or sem
        need(bool(_ID_RE.match(loop)), "loop khong hop le: %r" % (loop,))
        common["semantic_key"] = sem
        common["loop"] = loop
        hdr = raw_spec.get("header_rows")
        need(isinstance(hdr, list) and hdr,
             "header_rows phai la list >=1 hang (nested-grid bat buoc)")
        header_rows = []
        for ri, row in enumerate(hdr):
            need(isinstance(row, list) and row,
                 "header_rows[%d] phai la list khong rong" % ri)
            norm_row = []
            for ci, c in enumerate(row):
                need(isinstance(c, dict) and isinstance(c.get("text"), str),
                     "header_rows[%d][%d] phai la object co 'text'" % (ri, ci))
                rs = c.get("rowspan", 1)
                cs = c.get("colspan", 1)
                need(isinstance(rs, int) and rs >= 1,
                     "header_rows[%d][%d].rowspan phai la int >=1" % (ri, ci))
                need(isinstance(cs, int) and cs >= 1,
                     "header_rows[%d][%d].colspan phai la int >=1" % (ri, ci))
                norm_row.append({"text": c["text"].strip(),
                                 "rowspan": rs, "colspan": cs})
            header_rows.append(norm_row)

        cols = raw_spec.get("columns")
        need(isinstance(cols, list) and cols,
             "columns phai la list khong rong")
        columns = []
        for i, c in enumerate(cols):
            norm = norm_column(c, i)
            ci = norm.pop("col_index")
            need(isinstance(ci, int) and ci >= 0,
                 "columns[%d].col_index phai la int >=0 (vi tri vat ly)" % i)
            norm["col_index"] = ci
            columns.append(norm)
        indexes = [c["col_index"] for c in columns]
        need(len(indexes) == len(set(indexes)),
             "col_index trung nhau: %s" % indexes)
        width = max(indexes) + 1
        need(sorted(indexes) == list(range(width)) or
             sorted(indexes) == list(range(1, width)),
             "col_index phai lien tu 0 hoac lien tu 1: %s" % sorted(indexes))

        stt = raw_spec.get("stt") or {"mode": "none"}
        need(isinstance(stt, dict) and set(stt) <= {"mode", "col_index"},
             "stt chi cho phep {mode, col_index}")
        mode = stt.get("mode") or "none"
        need(mode in ("generated", "none"), "stt.mode khong hop le: %r" % mode)
        stt_ci = stt.get("col_index")
        if mode == "generated":
            need(isinstance(stt_ci, int) and stt_ci >= 0,
                 "stt.col_index bat buoc khi mode='generated'")
            need(stt_ci not in indexes,
                 "stt.col_index %s bi trung voi cot du lieu" % stt_ci)
            width = max(width, stt_ci + 1)
        raw_disc = raw_spec.get("discriminator")
        discriminator = None
        if raw_disc is not None:
            need(isinstance(raw_disc, dict) and
                 isinstance(raw_disc.get("tag"), str) and
                 isinstance(raw_disc.get("values"), list) and
                 raw_disc["values"],
                 "discriminator can {tag, values[]}")
            discriminator = {"tag": raw_disc["tag"],
                             "values": [str(v) for v in raw_disc["values"]]}
        raw_totals = raw_spec.get("totals") or []
        need(isinstance(raw_totals, (list, tuple)), "totals phai la list")
        need(not raw_totals,
             "nested-grid v1 khong tinh target tong trong ban (hang tong phap "
             "ly thuoc pham vi nguon phap ly BLOCKED) — de totals=[] ")
        common.update({
            "header_rows": header_rows, "columns": columns, "width": width,
            "stt": {"mode": mode,
                    "col_index": stt_ci if mode == "generated" else None},
            "discriminator": discriminator, "totals": [],
        })
        return common

    if kind == KIND_OUTPUT_TABLE:
        sem = raw_spec.get("semantic_key")
        need(isinstance(sem, str) and _ID_RE.match(sem),
             "semantic_key khong hop le: %r" % (sem,))
        grid = raw_spec.get("grid")
        need(isinstance(grid, dict), "grid phai la object")
        need(set(grid) <= {"rows", "cols", "labels"},
             "grid co truong le: %s" % sorted(set(grid)))
        rows, ncols = grid.get("rows"), grid.get("cols")
        need(isinstance(rows, int) and rows > 0, "grid.rows phai la int >0")
        need(isinstance(ncols, int) and ncols > 0, "grid.cols phai la int >0")
        labels = grid.get("labels")
        need(isinstance(labels, list),
             "grid.labels phai la list (string tung hang hoặc ma tran)")
        if any(isinstance(x, list) for x in labels):
            need(all(isinstance(x, list) and len(x) == ncols for x in labels),
                 "grid.labels dang ma tran phai du %d cot moi hang" % ncols)
            need(len(labels) == rows, "grid.labels thieu hang")
        else:
            need(all(isinstance(x, str) for x in labels),
                 "grid.labels phai gom string")
            need(len(labels) <= rows,
                 "grid.labels nhieu hon grid.rows=%d" % rows)
            need(ncols == 1 or len(labels) == 0,
                 "grid.labels dang flat chi dung voi grid.cols=1")
        common.update({
            "semantic_key": sem,
            "grid": {"rows": rows, "cols": ncols, "labels": labels},
        })
        return common

    fail("kind khong ho tro: %r" % (kind,))
    raise AssertionError("unreachable")


def load_form_spec(form_id):
    """Đọc tools/form_specs/*/<form_id>.json nếu có.

    Trả về None khi không có file spec (mẫu dùng REBUILD_TABLES inline);
    ngược lại {"entries": [entry...], "specs_by_id": {spec_id: spec}} với
    entry là dict giống phần tử REBUILD_TABLES (trừ "spec" đã tách ra).
    Kết quả cache theo form_id trong tiến trình.

    Entry khai báo "legal_status": {"blocked": true, ...} vẫn được validate
    NHƯNG bị BỎ QUA hoàn toàn lúc rebuild (không chạm document) — cơ chế
    isolate đúng section BLOCKED_LEGAL_REVIEW, không suy đoán pháp lý.
    """
    if form_id in _form_spec_cache:
        return _form_spec_cache[form_id]
    raw = None
    path_used = None
    if FORM_SPECS_DIR.is_dir():
        for path in sorted(FORM_SPECS_DIR.glob("*/%s.json" % form_id)):
            # utf-8-sig: chịu được file lưu kèm BOM (notepad/PowerShell)
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
            path_used = path
            break
    result = None
    if raw is not None:
        if form_id in REBUILD_TABLES:
            print("[form_specs] %s co ca file JSON (%s) va khai bao inline "
                  "REBUILD_TABLES -> dung file JSON" % (form_id, path_used.name))
        if raw.get("gap_nghiepvu"):
            print("[form_specs] %s GAP NGHIEPVU: %s" % (form_id, raw["gap_nghiepvu"]))
        # section_cond: metadata điều kiện P1.2 Option D (M72 selector) —
        # đọc bởi census verifier (p1_b_verify_m72) và docx_render; loader
        # chỉ cần chấp nhận sự tồn tại, không tham gia rebuild bảng.
        # inserts: chèn paragraph văn bản (hdr2col-era capability, lệnh owner
        # 2026-08-28 — sửa M09 mất mục 7); validate shape fail-loud ở đây.
        allowed_root = {"form_id", "group", "note", "gap_nghiepvu", "tables",
                        "section_cond", "inserts"}
        extra_root = set(raw) - allowed_root
        if extra_root:
            raise ValueError(
                "[form_specs] %s (%s): truong root khong duoc phep: %s"
                % (form_id, path_used, sorted(extra_root)))
        for ins in raw.get("inserts") or []:
            if not isinstance(ins, dict) or not ins.get("runs"):
                raise ValueError(
                    "[form_specs] %s (%s): insert phải có runs: %r"
                    % (form_id, path_used, ins))
            if ins.get("pos", "after") not in ("after", "before", "end"):
                raise ValueError(
                    "[form_specs] %s (%s): insert.pos phải after|before|end: %r"
                    % (form_id, path_used, ins.get("pos")))
            if ins.get("pos") != "end" and not ins.get("anchor"):
                raise ValueError(
                    "[form_specs] %s (%s): insert after/before phải có anchor: %r"
                    % (form_id, path_used, ins))
        specs_by_id = {}
        entries = []
        for e in raw.get("tables") or []:
            s_kind = e.get("kind") or KIND_LIST
            if s_kind not in SECTION_KINDS:
                raise ValueError(
                    "[form_specs] %s (%s): kind khong hop le: %r "
                    "(cho phep: %s)" % (form_id, path_used,
                                        s_kind, ", ".join(SECTION_KINDS)))
            if s_kind != KIND_LIST:
                unknown = set(e) - _ENTRY_KEYS[s_kind]
                if unknown:
                    raise ValueError(
                        "[form_specs] %s (%s): entry kind=%s co truong le: %s"
                        % (form_id, path_used, s_kind, sorted(unknown)))
            s = _json_spec(e["spec"], form_id)
            specs_by_id[s["id"]] = s
            ent = {k: v for k, v in e.items() if k != "spec"}
            ent["spec"] = s["id"]  # giữ hình dạng entry như REBUILD_TABLES inline
            if s.get("kind", KIND_LIST) != KIND_LIST:
                legal = _validate_legal_status(ent, form_id, s["id"])
                ent["_blocked"] = bool(legal.get("blocked"))
                if ent["_blocked"]:
                    print("[form_specs] %s/%s BLOCKED LEGAL REVIEW (%s) -> "
                          "BO QUA rebuild entry nay"
                          % (form_id, s["id"], legal.get("ref") or "ref chua ghi"))
            entries.append(ent)
        # Occurrence (P1): validate som de chan spec sai truoc khi sua document.
        # Spec KHONG co "occurrences" khong bi anh huong gi (backward-compat).
        all_loops = {s["loop"] for s in specs_by_id.values() if "loop" in s}
        for ent in entries:
            if not ent.get("occurrences"):
                continue
            spec_k = specs_by_id[ent["spec"]].get("kind", KIND_LIST)
            if spec_k not in (KIND_LIST, KIND_NESTED_GRID):
                raise ValueError(
                    "[form_specs] %s/%s: chi list/nested-grid duoc khai bao "
                    "'occurrences'" % (form_id, spec_k))
            nth_set = [c.get("nth", 1) for c in ent["occurrences"]]
            if spec_k != KIND_LIST and sorted(nth_set) != list(
                    range(1, len(nth_set) + 1)):
                # heading giong het nhau nen nth la dinh danh duy nhat; bo sot
                # mot lan xuat hien nghia la mot bang bi bo lung -> chan som.
                raise ValueError(
                    "[form_specs] %s/%s: nth phai lien tu 1..%d de dinh vi "
                    "dung tung lan xuat hien, nhan %s"
                    % (form_id, ent["spec"], len(nth_set), sorted(nth_set)))
            # occurrence_id duoc phep trung voi loop cua CHINH entry do
            # (occ_spec["loop"] bi ghi de bang occurrence_id khi rebuild);
            # chi cam trung ten loop cua entry/spec khac trong cung form.
            own_loop = specs_by_id.get(ent.get("spec"), {}).get("loop")
            ent["_occurrences"] = table_occurrences.validate_occurrences(
                ent["occurrences"], all_loops - {own_loop}, form_id)
        result = {"entries": entries, "specs_by_id": specs_by_id}
        if raw.get("inserts"):
            result["inserts"] = raw["inserts"]
    _form_spec_cache[form_id] = result
    return result


def resolve_rebuild_spec(spec_id, ext):
    """Spec của một entry rebuild: ưu tiên spec từ file JSON (ext), sau đó đến
    DYNAMIC_TABLES inline."""
    if ext and spec_id in ext["specs_by_id"]:
        return ext["specs_by_id"][spec_id]
    return _SPEC_BY_ID[spec_id]


def _body_paragraphs(doc):
    from docx.text.paragraph import Paragraph
    return [Paragraph(el, doc) for el in doc.element.body.iterchildren()
            if el.tag == qn("w:p")]


def _para_folded(para):
    return fold(re.sub(r"\s+", " ", para.text)).strip()


def _set_table_borders(tbl):
    tbl_pr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:%s" % edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "000000")
        borders.append(el)
    tbl_pr.append(borders)


# ---------------------------------------------------------------------------
# Phase 5R Lane C (WLAY-008/C3): tái phân bổ width theo nội dung cho bảng rộng
#
# Bảng >= WIDE_TABLE_MIN_COLS cột do python-docx dựng MẶC ĐỊNH chia đều
# width (vd 15 cột -> 576 twips/cột ~ 1.0 cm) khiến header dài như "Chủ sở
# hữu/Thành viên công ty TNHH…" vỡ thành cụm 1-3 ký tự. Builder gọi
# _maybe_widen_table để phân bổ lại width tỉ lệ độ dài nội dung đại diện
# (header/nhãn) với sàn MIN_COL_TWIPS (567 = 1 cm, khớp ngưỡng D9 của gate):
#   - KHÔNG đổi số cột, KHÔNG xóa cột, tổng width giữ nguyên;
#   - deterministic (regen hai lần ra cùng grid);
#   - mọi ô (tcW) được đặt khớp span gridSpan để Word không tự chia lại.
# BẬT/TẮT theo ENTRY: chỉ spec khai "width_policy": "content" mới được tái
# phân bổ — default là hành vi cũ (chia đều) để regen form chưa flag KHÔNG
# trôi so với template đã commit (guard ID7 test_generator_deep_idempotency).
# Flag do lane C đặt trong tools/form_specs/** (tools/
# phase5r_table_policies.json ghi evidence từng bảng); Lead flip khi regen.
# Chỉ áp dụng cho bảng >= 10 cột — bảng nhỏ giữ hành vi cũ (zero churn).
# ---------------------------------------------------------------------------

WIDE_TABLE_MIN_COLS = 10
MIN_COL_TWIPS = 567  # 1 cm — trùng ngưỡng D9 (tools/phase5_visual_gate.py)
WIDTH_POLICY_CONTENT = "content"


def _content_col_widths(weights: list, total: int,
                        min_w: int = MIN_COL_TWIPS) -> list:
    """Phân bổ `total` twips cho các cột theo `weights` (độ dài nội dung).

    Sàn min_w cho mọi cột; phần lẻ làm tròn bù vào cột weight lớn trước
    (stable theo index) để tổng luôn đúng `total` khi khả thi."""
    n = len(weights)
    if n == 0:
        return []
    wsum = sum(max(w, 1) for w in weights)
    raw = [max(min_w, total * max(w, 1) // wsum) for w in weights]
    rem = total - sum(raw)
    order = sorted(range(n), key=lambda i: (-max(weights[i], 1), i))
    guard = 0
    while rem != 0 and guard <= 4 * total:
        idx = order[guard % n]
        step = 1 if rem > 0 else -1
        if raw[idx] + step >= min_w:
            raw[idx] += step
            rem -= step
        guard += 1
    return raw


def _apply_content_widths(tbl, weights: list) -> None:
    """Đặt gridCol + tcW (đúng span gridSpan) theo weights; tổng giữ nguyên."""
    tbl_el = tbl._tbl
    grid = tbl_el.find(qn("w:tblGrid"))
    if grid is None:
        return
    cols = [el for el in grid.iterchildren() if el.tag == qn("w:gridCol")]
    if len(cols) != len(weights):
        return
    total = sum(int(el.get(qn("w:w")) or 0) for el in cols)
    if total <= 0:
        return
    widths = _content_col_widths(weights, total)
    for el, w in zip(cols, widths):
        el.set(qn("w:w"), str(w))
    for tr in tbl_el.iterchildren(qn("w:tr")):
        cursor = 0
        for tc in tr.iterchildren(qn("w:tc")):
            span = 1
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is not None:
                gs = tcpr.find(qn("w:gridSpan"))
                if gs is not None:
                    span = int(gs.get(qn("w:val")) or 1)
            end = min(cursor + span, len(widths))
            w = sum(widths[cursor:end]) if end > cursor else \
                widths[min(cursor, len(widths) - 1)]
            if tcpr is None:
                tcpr = OxmlElement("w:tcPr")
                tc.insert(0, tcpr)
            tcw = tcpr.find(qn("w:tcW"))
            if tcw is None:
                # tcW đứng trước gridSpan trong CT_TcPr -> chèn đầu tcPr
                tcw = OxmlElement("w:tcW")
                tcpr.insert(0, tcw)
            tcw.set(qn("w:w"), str(w))
            tcw.set(qn("w:type"), "dxa")
            cursor += span


def _header_col_weights(header_rows: list, ncols: int) -> list:
    """Weight mỗi cột vật lý từ header nhiều tầng (text dài nhất phủ cột)."""
    weights = [4] * ncols
    occupied = {}
    for ri, row_cells in enumerate(header_rows):
        cursor = 0
        for src in row_cells:
            cs = src.get("colspan", 1)
            rs = src.get("rowspan", 1)
            text = fold(re.sub(r"\s+", " ", src.get("text", ""))).strip()
            for c in range(cursor, min(cursor + cs, ncols)):
                key = (ri, c)
                occupied[key] = text
                weights[c] = max(weights[c], len(text))
            # ô rowspan của hàng trên vẫn phủ cột này — trọng số đã tính
            cursor += cs
    return weights


def _maybe_widen_table(tbl, ncols: int, weights: list,
                       spec: dict | None = None) -> None:
    """Phân bổ lại width theo nội dung nếu spec bật width_policy='content'
    và bảng đủ rộng (>= 10 cột)."""
    if spec is None or spec.get("width_policy") != WIDTH_POLICY_CONTENT:
        return
    if ncols >= WIDE_TABLE_MIN_COLS:
        _apply_content_widths(tbl, weights)


def _col_tags_for_headers(headers, spec):
    tags = {}
    for ci, h in enumerate(headers):
        hf = fold(re.sub(r"\s+", " ", h)).strip()
        tag = None
        for pat, tg in spec["cols"]:
            if re.search(pat, hf):
                tag = tg
                break
        tags[ci] = tag
    return tags


def _build_list_table(doc, headers, spec):
    ncols = len(headers)
    missing = spec["detect"] - {fold(re.sub(r"\s+", " ", h)).strip() for h in headers}
    if missing:
        raise ValueError("Header cua bang tai dung %s thieu detect keys: %s"
                         % (spec["id"], sorted(missing)))
    tbl = doc.add_table(rows=1 + REBUILD_BLANK_ROWS, cols=ncols)
    _set_table_borders(tbl)
    # hàng tiêu đề in đậm
    for c, h in enumerate(headers):
        run = tbl.rows[0].cells[c].paragraphs[0].add_run(h)
        run.bold = True
    # hàng mẫu (hàng trắng cuối): gắn sẵn the loop theo cú pháp docxtemplater
    tagged = {c: t for c, t in _col_tags_for_headers(headers, spec).items() if t}
    # Cột STT tự sinh (spec khai báo stt_tag=True): gắn {_stt} — engine render
    # thay bằng số thứ tự 1-based khi nhân hàng; the mở loop đặt tại ô đầu.
    stt_cols = []
    if spec.get("stt_tag"):
        stt_cols = [c for c, h in enumerate(headers)
                    if fold(re.sub(r"\s+", " ", h)).strip() == "stt"]
    if tagged:
        open_c = min(stt_cols) if stt_cols else min(tagged)
        close_c = max(tagged)
        row = tbl.rows[-1]
        for c in range(ncols):
            txt = ""
            if tagged and c == open_c:
                txt += "{#%s}" % spec["loop"]
            if c in stt_cols:
                txt += "{_stt}"
            if c in tagged:
                txt += "{%s}" % tagged[c]
            if c == close_c:
                txt += "{/%s}" % spec["loop"]
            if txt:
                row.cells[c].paragraphs[0].add_run(txt)
    # Lane C (WLAY-008): bảng rộng -> width tỉ lệ nội dung header
    _maybe_widen_table(
        tbl, ncols,
        [max(len(fold(re.sub(r"\s+", " ", h)).strip()), 4) for h in headers],
        spec)
    return tbl


# ---------------------------------------------------------------------------
# Builder cho 3 kind mới. Mọi bảng đều dựng trong bộ nhớ rồi do
# rebuild_list_tables chèn đúng điểm neo — không đụng file nguồn.
# ---------------------------------------------------------------------------

def _new_grid(doc, nrows, ncols):
    """Bảng rỗng có viền, cùng style nền của bảng danh sách hiện có."""
    tbl = doc.add_table(rows=nrows, cols=ncols)
    _set_table_borders(tbl)
    return tbl


def _cell_set_text(cell, text, bold=False):
    """Ghi text vào ô (xoá sạch paragraph/run dư)."""
    paras = cell.paragraphs
    for extra in paras[1:]:
        extra._p.getparent().remove(extra._p)
    p0 = paras[0]
    for run in p0.runs:
        run.text = ""
    if text:
        run = p0.add_run(text)
        run.bold = bold
    return p0


def _fill_header_spans(tbl, header_rows):
    """Điền N HÀNG TIÊU ĐỀ nhiều tầng với rowspan/colspan vật lý.

    Tiling quét theo thứ tự trên->dưới, trái->phải: ô nào đã bị hàng trước
    rowspan chiếm thì bỏ qua; ô còn trống được merge hình chữ nhật
    (gridSpan + vMerge qua python-docx cell.merge) đúng span khai báo.
    Sai tiling -> raise ValueError (không bao giờ làm phẳng mất cột).
    """
    occupied = set()
    for ri, row_cells in enumerate(header_rows):
        cursor = 0
        for src in row_cells:
            while (ri, cursor) in occupied and cursor < tbl_cols_count(tbl):
                cursor += 1
            rs, cs = src["rowspan"], src["colspan"]
            if cursor + cs > tbl_cols_count(tbl) or ri + rs > len(header_rows):
                raise ValueError(
                    "[form_specs] header_rows: o %r vuot ra ngoai luoi vat ly "
                    "%dx%d" % (src.get("text"), len(header_rows),
                               tbl_cols_count(tbl)))
            base = tbl.rows[ri].cells[cursor]
            if rs > 1 or cs > 1:
                end_cell = tbl.rows[ri + rs - 1].cells[cursor + cs - 1]
                base = base.merge(end_cell)
            for r in range(ri, ri + rs):
                for c in range(cursor, cursor + cs):
                    if (r, c) in occupied:
                        raise ValueError(
                            "[form_specs] header_rows: span de` len nhau tai "
                            "(%d,%d)" % (r, c))
                    occupied.add((r, c))
            _cell_set_text(base, src["text"], bold=True)
            cursor += cs
    missing = [(r, c) for r in range(len(header_rows))
               for c in range(tbl_cols_count(tbl)) if (r, c) not in occupied]
    if missing:
        raise ValueError(
            "[form_specs] header_rows khong phu het luoi vat ly, thieu %d o "
            "vd %s" % (len(missing), missing[:6]))
    return tbl


def tbl_cols_count(tbl):
    """Số cột vật lý của bảng (đếm con w:gridCol của w:tblGrid)."""
    grid = tbl._tbl.find(qn("w:tblGrid"))
    if grid is None:
        return 0
    return len([el for el in grid.iterchildren() if el.tag == qn("w:gridCol")])


def _build_fixed_matrix_table(doc, spec):
    """fixed-matrix: hàng tiêu đề + TRỌN các dòng pháp lý khai báo.

    Mỗi ô giá trị được gắn sẵn the `"<semantic_key>.<row_id>.<tag>"`; ô tổng
    thuộc dòng output_only cũng được gắn the để engine TÍNH LẠI lúc export
    (không tin giá trị lưu trong draft).
    """
    cols = spec["columns"]
    rows = spec["fixed_rows"]
    ncols = len(cols)
    tbl = _new_grid(doc, len(rows) + 1, ncols)
    for ci, col in enumerate(cols):
        _cell_set_text(tbl.rows[0].cells[ci], col["header"], bold=True)
    sem = spec["semantic_key"]
    for ri, row in enumerate(rows):
        cells = tbl.rows[ri + 1].cells
        for ci, col in enumerate(cols):
            tag = col["tag"]
            if tag is None:
                _cell_set_text(cells[ci], row["label"] if ci == 0 else "")
                continue
            _cell_set_text(cells[ci], "{%s.%s.%s}" % (sem, row["id"], tag))
    # Lane C (WLAY-008): bảng rộng -> width tỉ lệ nội dung (cột nhãn lấy
    # max với nhãn dòng dài nhất)
    weights = [max(len(fold(re.sub(r"\s+", " ", c["header"])).strip()), 4)
               for c in cols]
    if rows:
        weights[0] = max(weights[0], max(
            len(fold(re.sub(r"\s+", " ", r.get("label", ""))).strip())
            for r in rows))
    _maybe_widen_table(tbl, ncols, weights, spec)
    return tbl


def _build_nested_grid_table(doc, spec):
    """nested-grid: header_rows nhiều tầng (rowspan/colspan) + hàng mẫu lặp.

    Cột dữ liệu giữ NGUYÊN vị trí vật lý col_index; STT tự sinh ở stt.col_index;
    cột không gắn the vẫn tồn tại như một cột vật lý (KHÔNG làm phẳng mất cột).
    """
    width = spec["width"]
    n_blank = REBUILD_BLANK_ROWS
    tbl = _new_grid(doc, len(spec["header_rows"]) + n_blank + 1, width)
    _fill_header_spans(tbl, spec["header_rows"])
    tagged = {c["col_index"]: c["tag"] for c in spec["columns"]}
    stt_ci = spec["stt"]["col_index"] if spec["stt"]["mode"] == "generated" \
        else None
    open_candidates = ([stt_ci] if stt_ci is not None else []) + \
        [c for c in sorted(tagged)]
    open_c = min(open_candidates) if open_candidates else None
    close_c = max(tagged) if tagged else None
    tpl_row = tbl.rows[-1]
    for c in range(width):
        txt = ""
        if c is not None and c == open_c:
            txt += "{#%s}" % spec["loop"]
        if stt_ci is not None and c == stt_ci:
            txt += "{_stt}"
        if c in tagged:
            txt += "{%s}" % tagged[c]
        if c is not None and c == close_c:
            txt += "{/%s}" % spec["loop"]
        if txt:
            _cell_set_text(tpl_row.cells[c], txt)
    # Lane C (WLAY-008): bảng rộng -> width tỉ lệ nội dung header nhiều tầng
    _maybe_widen_table(tbl, width,
                       _header_col_weights(spec["header_rows"], width), spec)
    return tbl


def _build_output_table_grid(doc, spec):
    """output-table: lưới chỉ để in/ký — KHÔNG the input nào."""
    grid = spec["grid"]
    labels = grid["labels"]
    matrix = all(isinstance(x, list) for x in labels)

    def label_at(r, c):
        if not labels:
            return ""
        if matrix:
            return labels[r][c] if r < len(labels) else ""
        return labels[r] if c == 0 else ""

    tbl = _new_grid(doc, grid["rows"], grid["cols"])
    for r in range(grid["rows"]):
        for c in range(grid["cols"]):
            text = label_at(r, c)
            if text:
                _cell_set_text(tbl.rows[r].cells[c], text, bold=True)
    return tbl


COND_MARKER_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _insert_cond_markers(tbl_element, flag):
    """Bọc bảng vừa dựng bằng cặp paragraph marker `{?flag}` ... `{/flag}`
    (contract P1.2 Option D dùng chung với PLI_M72): docx_render chỉ xuất
    vùng khi data[flag] truthy, docx_to_blocks gắn `cond` vào blocks.
    Marker luôn là CON TRỰC TIẾP của body và luôn cân đối."""
    if not COND_MARKER_RE.match(flag or ""):
        raise ValueError("[form_specs] cond_flag khong hop le: %r" % (flag,))
    spacer = tbl_element.getnext()  # đoạn trống chèn kèm sau bảng

    def marker(close):
        p = OxmlElement("w:p")
        r_ = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = ("{/%s}" if close else "{?%s}") % flag
        r_.append(t)
        p.append(r_)
        return p

    open_p = marker(False)
    close_p = marker(True)
    if spacer is None:
        tbl_element.addnext(close_p)
    else:
        spacer.addnext(close_p)
    tbl_element.addprevious(open_p)
    return open_p, close_p


GRID_META_TEMP_ATTR = "{urn:orca:p1b-temp}section_meta"


def _mark_grid_meta(tbl_element, info):
    """Thuộc tính XML tạm mang metadata cấu trúc của bảng kind mới để
    process_form map bảng -> section_spec khi gắn the/đăng ký form_maps.
    Bị xoá trước khi lưu template (xem _scrub_occurrence_attrs)."""
    tbl_element.set(GRID_META_TEMP_ATTR, json.dumps(info, ensure_ascii=False))


def _pop_grid_meta(table):
    """Đọc + xoá thuộc tính tạm; trả dict hoặc None."""
    el = table._tbl
    raw = el.get(GRID_META_TEMP_ATTR)
    if raw is None:
        return None
    del el.attrib[GRID_META_TEMP_ATTR]
    try:
        info = json.loads(raw)
    except ValueError:
        print("[rebuild] thuoc tinh meta tam hong, bo qua: %r" % raw[:100])
        return None
    if isinstance(info, dict) and info.get("kind") in SECTION_KINDS:
        return info
    return None


def rebuild_list_tables(doc, form_id, ext=None):
    """Xoa paragraph tan du cua luoi cu va chen bang danh sach moi vao ban sao
    trong bo nhiem (khong ghi đè file nguồn). Chạy TRƯỚC khi gắn the.
    ext = load_form_spec(form_id); None -> dùng khai báo inline REBUILD_TABLES.

    Occurrence (P1): entry co "_occurrences" (da validate trong
    load_form_spec) se tao MOT bang doc lap cho MOI occurrence khop:
    semantic_key/loop = occurrence_id. Vung occurrence duoc dinh vi boi
    tools/table_occurrences.resolve_regions; vung SKIP (nhiem/thieu lan)
    KHONG bi xoa paragraph va KHONG duoc chen bang.
    """
    entries = ext["entries"] if ext else REBUILD_TABLES.get(form_id)
    if not entries:
        return
    # Lưu ý proxy lxml/python-docx: id(element) không ổn định giữa hai lần
    # duyệt (proxy tạo mới, CPython tái dùng địa chỉ sau GC) nên trạng thái
    # "đã xử lý" theo dõi bằng CHỈ SỐ trên MỘT danh sách paragraph dựng sẵn.
    paras = _body_paragraphs(doc)
    para_texts = [p.text for p in paras]

    # 0) Occurrence: resolve TAT CA vung tren ban snapshot SACH (truoc khi
    #    sua/cut paragraph) — giu reference paragraph de chen an toan sau nay.
    occ_plan = []  # [(entry, region_ok)] — chi region status=ok
    has_occ_entries = any(e.get("_occurrences") for e in entries)
    if ext:
        for e in entries:
            cfgs = e.get("_occurrences")
            if not cfgs:
                continue
            for reg in table_occurrences.resolve_regions(para_texts, cfgs):
                if reg["status"] == "ok":
                    occ_plan.append((e, reg))

    def _entry_ok_regions(entry):
        return [reg for en, reg in occ_plan if en is entry]

    # 1) cắt giữ phần hợp lệ trong paragraph tàn dư có lẫn nội dung thật.
    # Entry occurrence: trim CHỈ áp trong vùng ok của chính nó (không đụng
    # ngoài vùng).
    protected = set()
    for e in entries:
        if e.get("_blocked"):
            continue  # BLOCKED: entry này không được đụng document
        trim_pats = e.get("trim") or []
        if not trim_pats:
            continue
        occ_regs = _entry_ok_regions(e) if e.get("_occurrences") else None
        for pat in trim_pats:
            for pi, para in enumerate(paras):
                if pi in protected:
                    continue
                if occ_regs is not None and not any(
                        r["start"] <= pi < r["end"] for r in occ_regs):
                    continue
                if re.match(pat, _para_folded(para)):
                    full = para.text
                    m = re.search(e["keep_from"], full)
                    keep = full[m.start():].strip() if m else ""
                    for r_ in para.runs:
                        r_.text = ""
                    if para.runs:
                        para.runs[0].text = keep
                    else:
                        para.add_run(keep)
                    protected.add(pi)
    # 2) xóa paragraph rác tàn dư của lưới cũ (chỉ khi khớp rõ ràng).
    # Drop mặc định áp dụng toàn-văn-bản; drop khai báo trong entry kèm
    # "drop_until" thì chỉ áp dụng trong vùng (sau anchor -> trước drop_until)
    # để không đụng các đoạn cùng nhãn ở mục khác của mẫu.
    # Entry OCCURRENCE: drop (kể cả default) CHỈ chạy scoped trong vùng ok
    # của chính nó — không bao giờ toàn văn bản (boundary an toàn, bài học
    # PLI_M09). Khi form có bất kỳ entry occurrence nào, drop mặc định toàn
    # văn bản bị tắt để không nuốt vùng của occurrence.
    drop_pats = ([] if any(e.get("no_default_drops") for e in entries)
                 else list(REBUILD_DROP_DEFAULT))
    if has_occ_entries:
        drop_pats = []
    scoped = []  # (start, end, pats) theo chỉ số paragraph
    for e in entries:
        if e.get("_blocked"):
            continue  # BLOCKED: entry này không được đụng document
        pats = list(e.get("drop") or [])
        if e.get("_occurrences"):
            regs = _entry_ok_regions(e)
            if not regs:
                continue  # mọi vùng đều skipped -> không drop gì cả
            if not e.get("no_default_drops"):
                pats += list(REBUILD_DROP_DEFAULT)
            for reg in regs:
                scoped.append((reg["start"], reg["end"], pats))
            continue
        if not pats:
            continue
        if e.get("drop_until"):
            start, end = 0, len(paras)
            for i, para in enumerate(paras):
                if re.search(e["anchor"], _para_folded(para)):
                    start = i + 1
                    break
            for i in range(start, len(paras)):
                if re.search(e["drop_until"], _para_folded(paras[i])):
                    end = i
                    break
            scoped.append((start, end, pats))
        else:
            drop_pats += pats
    for pi, para in enumerate(paras):
        if pi in protected:
            continue
        ft = _para_folded(para)
        if not ft:
            continue
        hit_global = any(re.match(p, ft) for p in drop_pats)
        hit_scoped = any(s <= pi < en and re.match(p, ft)
                         for s, en, pats in scoped for p in pats)
        if hit_global or hit_scoped:
            para._p.getparent().remove(para._p)
    # 3a) chèn bảng cho TỪNG occurrence (theo thứ tự heading trong form);
    # loop/semantic_key = occurrence_id; đánh dấu XML tạm để process_form
    # map đúng bảng -> occurrence khi gắn the.
    for e, reg in sorted(occ_plan, key=lambda item: item[1]["head"]):
        if e.get("_blocked"):
            continue  # BLOCKED_LEGAL_REVIEW: không chạm document
        spec = resolve_rebuild_spec(e["spec"], ext)
        cfg = reg["cfg"]
        kind = spec.get("kind", KIND_LIST)
        occ_spec = dict(spec)
        # Loop name mac dinh = occurrence_id; cho phep ghi de bang cfg["loop"]
        # de BAO TOAN canonical key (vd ds_nganh PLII_M02 vung C.3 giu ten
        # loop dung chung giua cac mau) trong khi semantic_key van rieng.
        occ_spec["loop"] = cfg.get("loop") or cfg["occurrence_id"]
        tbl = _build_kind_table(doc, occ_spec, e, kind)
        _mark_table_occurrence(tbl._tbl, {
            "occurrence_id": cfg["occurrence_id"],
            "sync_group": cfg.get("sync_group"),
            "spec_id": spec["id"],
            # bao toan canonical loop name (vd ds_nganh) neu co khai bao
            "loop": cfg.get("loop"),
        })
        if kind != KIND_LIST:
            # metadata cấu trúc của kind mới: process_form đăng ký section_spec
            # (header nhiều tầng/totals/cột vật lý) cho converter + export.
            _mark_grid_meta(tbl._tbl, {
                "kind": kind,
                "spec_id": spec["id"],
                "section_id": spec.get("section_id") or spec["id"],
                "occurrence_id": cfg["occurrence_id"],
                "loop": occ_spec["loop"],
                "semantic_key": cfg["occurrence_id"],
                "spec": _grid_meta_payload(spec),
            })
        head_para = paras[reg["head"]]
        if e.get("pos", "after") == "before":
            head_para._p.addprevious(tbl._tbl)
        else:
            head_para._p.addnext(tbl._tbl)
        spacer = OxmlElement("w:p")
        tbl._tbl.addnext(spacer)
        _maybe_wrap_cond(tbl._tbl, e, form_id, spec)
    # 3) chèn bảng mới tại điểm neo (entry legacy — bỏ qua entry occurrence
    # vì đã chèn ở bước 3a)
    for e in entries:
        if e.get("_occurrences") or e.get("_blocked"):
            continue
        spec = resolve_rebuild_spec(e["spec"], ext)
        kind = spec.get("kind", KIND_LIST)
        anchor_p = None
        for para in _body_paragraphs(doc):
            if re.search(e["anchor"], _para_folded(para)):
                anchor_p = para
                break
        if anchor_p is None:
            print("[rebuild] KHONG tim thay anchor cho %s: %r" % (form_id, e["anchor"]))
            continue
        tbl = _build_kind_table(doc, spec, e, kind)
        if kind != KIND_LIST:
            _mark_grid_meta(tbl._tbl, {
                "kind": kind,
                "spec_id": spec["id"],
                "section_id": spec.get("section_id") or spec["id"],
                "semantic_key": spec.get("semantic_key") or spec["id"],
                "loop": spec.get("loop"),
                "spec": _grid_meta_payload(spec),
            })
        if e.get("pos", "after") == "before":
            anchor_p._p.addprevious(tbl._tbl)
        else:
            anchor_p._p.addnext(tbl._tbl)
        spacer = OxmlElement("w:p")
        tbl._tbl.addnext(spacer)
        _maybe_wrap_cond(tbl._tbl, e, form_id, spec)
    # 4) chèn paragraph văn bản (capability mở theo lệnh owner 2026-08-28 —
    # sửa lỗi M09 mất mục 7; mọi chèn đều qua spec, KHÔNG sửa tay template):
    # spec khai top-level "inserts":
    #   {"pos": "after"|"before", "anchor": <regex trên text đã fold>,
    #    "runs": [{"text": "...", "b": true, "i": true}, ...]}
    # Anchor phải khớp ĐÚNG 1 paragraph — 0 hoặc >1 là SystemExit (fail-loud,
    # không bao giờ chèn mù).
    from docx.text.paragraph import Paragraph as _Paragraph
    for ins in (ext or {}).get("inserts") or []:
        if not ins.get("runs"):
            raise SystemExit("[rebuild] insert thiếu runs: %r" % ins)
        new_p = OxmlElement("w:p")
        if ins.get("pos") == "end":
            # [Wave D batch 2] pos="end": nối dòng nguồn bị mất ở CUỐI mẫu
            # (sau bảng cuối) — anchor không áp dụng vì đoạn cuối tài liệu có
            # thể là bảng/spacer. Thứ tự khai báo trong spec = thứ tự tài liệu.
            sect_pr = doc.element.body.find(qn("w:sectPr"))
            if sect_pr is not None:
                sect_pr.addprevious(new_p)
            else:
                doc.element.body.append(new_p)
            np = _Paragraph(new_p, doc.element.body)
        else:
            hits = [p for p in _body_paragraphs(doc)
                    if re.search(ins["anchor"], _para_folded(p))]
            if len(hits) != 1:
                raise SystemExit(
                    "[rebuild] insert anchor '%s' khớp %d paragraph (mong 1) "
                    "cho %s" % (ins["anchor"], len(hits), form_id))
            if ins.get("pos", "after") == "before":
                hits[0]._p.addprevious(new_p)
            else:
                hits[0]._p.addnext(new_p)
            np = _Paragraph(new_p, hits[0]._parent)
        for r in ins["runs"]:
            run = np.add_run(r.get("text", ""))
            if r.get("b"):
                run.bold = True
            if r.get("i"):
                run.italic = True


def _build_kind_table(doc, spec, entry, kind):
    """Chọn builder đúng kind; kind legacy "list" giữ nguyên hành vi cũ."""
    if kind == KIND_FIXED_MATRIX:
        return _build_fixed_matrix_table(doc, spec)
    if kind == KIND_NESTED_GRID:
        return _build_nested_grid_table(doc, spec)
    if kind == KIND_OUTPUT_TABLE:
        return _build_output_table_grid(doc, spec)
    return _build_list_table(doc, entry["headers"], spec)


def _grid_meta_payload(spec):
    """Phần metadata cấu trúc cần ghi vào form_maps cho converter/audit."""
    kind = spec.get("kind", KIND_LIST)
    if kind == KIND_FIXED_MATRIX:
        return {
            "columns": [{k: c[k] for k in
                         ("header", "tag", "input_type", "computed",
                          "output_only", "required")} for c in spec["columns"]],
            "fixed_rows": [{"id": r["id"], "label": r["label"],
                            "output_only": r["output_only"]}
                           for r in spec["fixed_rows"]],
            "totals": [dict(t) for t in spec.get("totals", [])],
        }
    if kind == KIND_NESTED_GRID:
        return {
            "header_rows": [[{"text": c["text"], "rowspan": c["rowspan"],
                              "colspan": c["colspan"]}
                             for c in row] for row in spec["header_rows"]],
            "width": spec["width"],
            "columns": [{k: c[k] for k in ("col_index", "tag", "required",
                                           "input_type", "output_only")}
                        for c in spec["columns"]],
            "stt": dict(spec["stt"]),
            "discriminator": (dict(spec["discriminator"])
                              if spec.get("discriminator") else None),
            "totals": [],
        }
    if kind == KIND_OUTPUT_TABLE:
        return {"grid": {k: spec["grid"][k]
                         for k in ("rows", "cols", "labels")},
                "inputs": []}
    raise ValueError("kind khong co grid meta payload: %r" % kind)


def _header_layout(spec):
    """Vị trí vật lý (col_index bắt đầu từ 0) của từng ô header_rows —
    cùng thuật toán tiling với `headerLayout` của app_web/ui/nested-grid.js
    để UI và DOCX không bao giờ lệch cột."""
    occupied = set()
    out = []
    for ri, row in enumerate(spec["header_rows"]):
        cursor = 0
        cells = []
        for src in row:
            while (ri, cursor) in occupied:
                cursor += 1
            rs, cs = src["rowspan"], src["colspan"]
            for r in range(ri, ri + rs):
                for c in range(cursor, cursor + cs):
                    occupied.add((r, c))
            cells.append({"text": src["text"], "rowspan": rs,
                          "colspan": cs, "col_index": cursor})
            cursor += cs
        out.append(cells)
    return out


def _maybe_wrap_cond(tbl_element, entry, form_id, spec):
    """Bọc `{?cond_flag}` ... `{/cond_flag}` khi spec khai báo presence có
    điều kiện. Đây là vùng do CHÍNH builder vừa dựng nên việc bọc luôn cân
    đối; converter/engine dùng chung cơ chế marker của PLI_M72."""
    flag = entry.get("cond_flag")
    if not flag:
        return
    open_p, close_p = _insert_cond_markers(tbl_element, flag)
    print("[rebuild] %s/%s: boc vung bang voi {?%s}...{/%s}"
          % (form_id, spec.get("id"), flag, flag))


def detect_dynamic(table, extra_specs=()):
    """Nhận diện bảng động. extra_specs: spec nạp từ tools/form_specs/ của
    mẫu đang xử lý — xét TRƯỚC DYNAMIC_TABLES để bảng vừa tái dựng từ file
    JSON khớp đúng spec nguồn gốc của nó."""
    if not table.rows:
        return None
    hdr_texts = []
    for cell in table.rows[0].cells:
        hdr_texts.append(norm_label(cell.text))
    # bảng có thể có >1 hàng tiêu đề; thử cả hàng 0 và 0+1
    for hdr_row in range(min(2, len(table.rows))):
        texts = []
        for cell in table.rows[hdr_row].cells:
            texts.append(fold(re.sub(r"\s+", " ", cell.text)).strip())
        joined = set(t for t in texts if t)
        for spec in list(extra_specs) + list(DYNAMIC_TABLES):
            # kind mới (fixed-matrix/nested-grid/output-table) KHÔNG có
            # "detect" — bảng của chúng được nhận diện qua meta XML tạm.
            if not spec.get("detect"):
                continue
            if spec["detect"] <= joined:
                return (spec, hdr_row)
    return None


def tc_iter(tr):
    """Các phần tử w:tc TRỰC TIẾP của hàng tr. Khác row.cells (nhân bản ô
    merge), mỗi ô xuất hiện đúng một lần — không cần dedup và tránh id() trên
    proxy lxml/python-docx (id() không ổn định vì proxy tạo mới mỗi lần truy
    cập, CPython tái dùng địa chỉ sau GC)."""
    for child in tr.iterchildren():
        if child.tag == qn("w:tc"):
            yield child


def tr_cells(table, ri):
    """Ô của hàng ri dạng _Cell, duyệt con trực tiếp w:tc của w:tr."""
    from docx.table import _Cell
    return [_Cell(tc, table) for tc in tc_iter(table._tbl.tr_lst[ri])]


# ---------------------------------------------------------------------------
# Xử lý run-level: tìm các đoạn dấu chấm và thay bằng the
# ---------------------------------------------------------------------------

def para_dot_groups(para):
    """Trả về [(start, end, run_idx_chars)] theo vị trí ký tự gộp của mọi run."""
    runs = [(r.text, i) for i, r in enumerate(para.runs)]
    full = "".join(t for t, _ in runs)
    groups = []
    for m in DOT_RUN.finditer(full):
        groups.append((m.start(), m.end()))
    return full, runs, groups


def apply_tags_to_para(para, assignments):
    """assignments: list (g_start, g_end, tag_text). Chỉnh sửa run trực tiếp."""
    if not assignments:
        return
    full, runs, _ = para_dot_groups(para)
    # dựng bản đồ ký tự -> (run_idx, offset_in_run)
    cmap = []
    for ri, (txt, _) in enumerate(runs):
        for off in range(len(txt)):
            cmap.append((ri, off))
    # áp từ cuối lên đầu để không lệch chỉ số
    new_runs = [list(t) for t, _ in runs]
    for g_start, g_end, tag in sorted(assignments, reverse=True):
        rs, ro = cmap[g_start]
        re_, eo = cmap[g_end - 1]
        if rs == re_:
            new_runs[rs][ro:eo + 1] = list(tag)
        else:
            new_runs[rs][ro:] = list(tag)
            for mid in range(rs + 1, re_):
                new_runs[mid][:] = []
                new_runs[mid].append("")  # giữ rỗng
            new_runs[re_][:eo + 1] = []
    for ri, r in enumerate(para.runs):
        r.text = "".join(new_runs[ri])


# ===========================================================================
# [6V-V2/C1] Chuẩn hóa skeleton glue — PLAN v6 C1, diệt B1 (detector D13)
# ===========================================================================
# Bản nguồn in "ngày…..tháng…..năm……": chỗ trống giữa các chữ là chỗ điền tay
# bằng mực, nên giấy KHÔNG có space. Generator thay nhóm chấm bằng {key} giữ
# nguyên độ dính -> render điền giá trị thật thành "ngày04tháng04năm2026",
# hai từ dính nhau không đọc được (B1: 323 record / 1104 hit / 77 form trên
# corpus v0_corpuscheck, detector D13).
#
# RULE (chốt sau khi census 3 ví dụ bản giấy — repr text nguồn nguyên vẹn):
#   Chèn MỘT space kề {tag} khi ký tự kề làm giá trị dính vào chữ kế:
#     - TRƯỚC `{`: word char (chữ/số, gồm tiếng Việt có dấu) hoặc ':'
#       (nhãn kết thúc, giá trị theo sau — separator "nhãn: giá trị").
#     - SAU  `}`: word char hoặc '(' (giá trị dính ngoặc mở chú thích).
#   KHÔNG chèn — không phải lỗi dính từ, giữ nguyên layout khác:
#     - '/' hai bên: vạch ngày có sẵn dính dấu "/" chủ đích (vd PLI_M32
#       "{...ngày{dk..ngay}/{dk..thang}/{dk..nam}", PLII_M18 "Ngày{..}/..../....").
#     - '.', ',', '…', ')', ';': dấu câu đóng — "giá trị," là chính tả chuẩn;
#       census 87 template: 0 occurrence dấu , . … ) ; liền TRƯỚC placeholder.
#     - cặp the dính "{a}{b}": '}' '{' không phải word char nên không chèn
#       (census 87 template hiện không có cặp nào).
#   3 ví dụ đối chứng bản giấy (nguồn -> template hiện tại -> sau normalize):
#     1) PLII_M08 <- 06_.../01_mau_ho_kinh_doanh/PL2_Mau_08_*.docx, body:
#        '……, ngày…..tháng…..năm……'
#        -> 'ngày{ngay_ky_vb}tháng{thang_ky_vb}năm{nam_ky_vb}'
#        -> 'ngày {ngay_ky_vb} tháng {thang_ky_vb} năm {nam_ky_vb}'.
#        Giấy dính vì nhóm chấm tự tạo khoảng trống thị giác; máy điền giá trị
#        thật cần space tường minh (đúng tinh thần Q-V3: form điền bằng máy).
#     2) PLII_M01 <- PL2_Mau_01_*.docx: '…tiếng Việt (ghi bằng chữ in
#        hoa):...........................' KHÔNG space sau ':', nhưng dòng
#        'Tôi là (ghi họ tên bằng chữ in hoa): ....' CÓ space — giấy không
#        nhất quán. Điền máy ra '):CÔNG TY…' là D13/PAREN_VALUE -> chuẩn hóa
#        space sau ':' ("label–value luôn có separator chuẩn", PLAN 5.1.1).
#     3) PLII_M13 <- PL2_Mau_13_*.docx: 'Điện thoại: ……….............Thư
#        điện tử (nếu có): …' — nhãn kế dính sát nhóm chấm; điền máy thành
#        '0900000014Thư điện tử' (D13/CONTACT_GLUE) -> chèn space giữa giá trị
#        và nhãn kế: '{dien_thoai_khac} Thư điện tử (nếu có): {email…}'.
# ============================================================================
_GLUETAG_RE = re.compile(r"\{[/#?]?[A-Za-z_][A-Za-z0-9_.]*\}")
_GLUED_BEFORE = re.compile(r"[\w:]")   # ký tự liền trước '{' -> chèn space
_GLUED_AFTER = re.compile(r"[\w(]")    # ký tự liền sau '}' -> chèn space


def _iter_all_paragraphs(doc):
    """Mọi paragraph của body + mọi bảng (lồng nhau). Header/footer của 87
    template KHÔNG chứa the nào (census 6V-V2/C1) nên không cần duyệt."""
    yield from doc.paragraphs

    def walk_table(tbl):
        seen = set()
        for row in tbl.rows:
            for cell in row.cells:
                if cell._tc in seen:
                    continue
                seen.add(cell._tc)
                yield from cell.paragraphs
                for nested in cell.tables:
                    yield from walk_table(nested)

    for tbl in doc.tables:
        yield from walk_table(tbl)


def normalize_skeleton_glue(doc) -> int:
    """Chèn space quanh {tag} khi kề word char / ':' / '(' (rule ghi ở khối
    comment trên _GLUETAG_RE). Chỉ sửa text của run, không đụng layout.
    Trả về số space đã chèn."""
    n_ins = 0
    for para in _iter_all_paragraphs(doc):
        runs = list(para.runs)
        if not runs:
            continue
        full = "".join(r.text for r in runs)
        if "{" not in full:
            continue
        ins = []
        for m in _GLUETAG_RE.finditer(full):
            if m.start() > 0 and _GLUED_BEFORE.match(full[m.start() - 1]):
                ins.append(m.start())
            if m.end() < len(full) and _GLUED_AFTER.match(full[m.end()]):
                ins.append(m.end())
        if not ins:
            continue
        cmap = []
        for ri, r in enumerate(runs):
            for off in range(len(r.text)):
                cmap.append((ri, off))
        chunks = [list(r.text) for r in runs]
        # chèn từ cuối lên đầu để không lệch chỉ số
        for pos in sorted(set(ins), reverse=True):
            ri, off = cmap[pos]
            chunks[ri].insert(off, " ")
            n_ins += 1
        for r, ch in zip(runs, chunks):
            new = "".join(ch)
            if new != r.text:
                r.text = new
    return n_ins


def _assign_para_slots(full, groups, add_field, unmatched, form_id, where,
                       section_ctx="", pending_label=""):
    """Gán the cho TẤT CẢ nhóm dấu chấm của MỘT paragraph -> [(s, e, tag)].

    Tách từ vòng lặp trong process_form (hành vi giữ nguyên 1:1) để dùng CHUNG
    cho quét thân tài liệu và cho 2 ô băng dưới của bảng header 2-band
    (xem _tag_header_band_slots). `where` chỉ dùng cho báo cáo unmatched.
    """
    assignments = []
    prev_end = 0
    gi = 0
    while gi < len(groups):
        g_start, g_end = groups[gi]
        label = full[prev_end:g_start]
        lab = norm_label(label)
        # trường hợp đặc biệt: "……, ngày ……tháng ……năm ……" (ký tên, có slot đầu dòng)
        if not lab.strip() and re.match(r"[,.]?\s*ngay\b", fold(full[g_end:g_end + 30])):
            names = ["dia_diem_ky", "ngay_ky_vb", "thang_ky_vb", "nam_ky_vb"]
            take = min(len(names), len(groups) - gi)
            for j in range(take):
                s, e = groups[gi + j]
                assignments.append((s, e, "{%s}" % names[j]))
                add_field(names[j], label if j == 0 else "")
            prev_end = groups[gi + take - 1][1]
            gi += take
            continue
        if not lab.strip() and pending_label:
            # slot ở đoạn riêng, nhãn nằm ở paragraph trước kết thúc bằng ":"
            lab = norm_label(pending_label)
        matched = None
        for pat, key, grps, ctx in R:
            if pat and re.search(pat, lab):
                if ctx and not re.search(ctx, section_ctx):
                    continue
                if grps:
                    need = len(grps)
                    avail = len(groups) - gi
                    take = min(need, avail)
                    last_ai = None
                    for j in range(take):
                        s, e = groups[gi + j]
                        if grps[j] == "":
                            # nhóm nối tiếp (vd …/… trong ngày tháng): kéo dài tag trước
                            # phủ luôn đoạn này thay vì để nguyên dấu chấm lửng
                            if last_ai is not None:
                                ps_, pe_, pt_ = assignments[last_ai]
                                assignments[last_ai] = (ps_, e, pt_)
                            continue
                        assignments.append((s, e, "{%s}" % grps[j]))
                        last_ai = len(assignments) - 1
                        add_field(grps[j], label if j == 0 else "")
                    prev_end = groups[min(gi + take - 1, len(groups) - 1)][1]
                    gi += take
                elif key:
                    assignments.append((g_start, g_end, "{%s}" % key))
                    add_field(key, label)
                    prev_end = g_end
                    gi += 1
                else:  # nhóm checkbox: bỏ qua không gắn the
                    prev_end = g_end
                    gi += 1
                matched = True
                break
        if not matched:
            unmatched.append({"form": form_id, "where": where,
                              "label": label.strip()[:100]})
            prev_end = g_end
            gi += 1
    return assignments


def cell_first_para(cell):
    return cell.paragraphs[0] if cell.paragraphs else None


def match_chk(label_folded):
    for pat, name in CHK_RULES:
        if re.search(pat, label_folded.strip()):
            return name
    return None


def _auto_chk_key(label_folded, seen):
    """Key chk dự phòng khi không khớp CHK_RULES — loại bỏ lớp lỗi 'checkbox
    dẹt thành text' (lệnh owner 2026-08-28): MỌI ô □/☐ phải được gắn the,
    không phụ thuộc whitelist nhãn. Key ổn định theo nội dung nhãn; trùng
    nhãn trong cùng mẫu -> _2, _3…"""
    slug = re.sub(r"[^a-z0-9]+", "_", label_folded).strip("_")[:40].strip("_")
    name = "auto_%s" % (slug or "o")
    n = seen.get(name, 0) + 1
    seen[name] = n
    return name if n == 1 else "%s_%d" % (name, n)


def process_checkboxes(doc, form_id, add_field, unmatched):
    """Quét mọi paragraph (cả trong bảng), thay □/☐ bằng the {chk_*}.

    [Wave D batch 2b] 2 PHA để key checkbox là ĐỘC NHẤT tầm FORM mà không
    làm lệch artifact của form không có lỗi:
      Pha A (legacy): gán theo heuristic gốc cho MỌI paragraph, chỉ thu thập
        (không add_field). Paragraph mà legacy sinh key TRÙNG trong đoạn ->
        đánh dấu repair.
      Pha B (convention): chỉ paragraph repair được gán lại theo quy ước
        nhãn trước/sau ô, với exclusion TẦM FORM (key legacy của bất kỳ
        paragraph nào + key đã gán ở pha B) — hết candidate -> auto key
        (tự _2). Đây là chỗ vá collision chéo giữa 2 CÂU HỎI khác dùng chung
        key (vd chk_co của câu đất/QTg-an-ninh và câu BOT trong PLI_M12).
      Pha C: apply tag + add_field theo thứ tự tài liệu.
    """
    from docx.text.paragraph import Paragraph

    last_label = ""
    seen_auto: dict = {}
    plans = []  # (para, full, pos, last_label_snapshot, legacy, repair)
    form_used: set = set()
    for p_el in doc.element.body.iter(qn("w:p")):
        para = Paragraph(p_el, doc)
        full = "".join(r.text for r in para.runs)
        if not full.strip():
            continue
        pos = [i for i, ch in enumerate(full) if ch in CHK_SYMBOLS]
        if not pos:
            last_label = fold(full)
            continue
        snap = last_label
        legacy = []
        for k, i in enumerate(pos):
            seg_after = full[i + 1: pos[k + 1] if k + 1 < len(pos) else len(full)]
            seg_before = full[0:i] if k == 0 else full[pos[k - 1] + 1:i]
            label_raw = (seg_after or seg_before or snap).strip()
            name = None
            for cand in (seg_after, seg_before,
                         snap if not seg_after.strip() else ""):
                if cand and cand.strip():
                    name = match_chk(fold(cand))
                    if name:
                        break
            if name is None:
                label_folded = norm_label(label_raw) if label_raw else ""
                if label_folded.strip():
                    name = _auto_chk_key(fold(label_folded), seen_auto)
            legacy.append((i, name, label_raw))
            if name:
                form_used.add(name)
        names = [n for _i, n, _l in legacy if n]
        plans.append((para, full, pos, snap, legacy,
                      len(names) != len(set(names))))
    # Pha B — chỉ repair paragraph key-trùng, exclusion tầm form
    seen_auto_b: dict = {}
    final = []  # (para, [(i, name, label_raw), ...])
    for para, full, pos, snap, legacy, repair in plans:
        if not repair:
            final.append((para, legacy))
            continue
        first_i = pos[0]
        before_txt = full[0:first_i]
        after_last = full[pos[-1] + 1:]
        if any(ch.isalpha() for ch in before_txt) and \
                not any(ch.isalpha() for ch in after_last):
            pair_mode = "before"
        elif any(ch.isalpha() for ch in after_last) and \
                not any(ch.isalpha() for ch in before_txt):
            pair_mode = "after"
        else:
            pair_mode = "mixed"
        para_used: set = set()
        chosen = []
        for k, i in enumerate(pos):
            seg_after = full[i + 1: pos[k + 1] if k + 1 < len(pos) else len(full)]
            seg_before = full[0:i] if k == 0 else full[pos[k - 1] + 1:i]
            if pair_mode == "before":
                parts = re.split(r"[:;]", seg_before)
                tail = re.sub(r"^[\s\d\.\)\]]+", "",
                              parts[-1] if parts else seg_before)
                if tail.strip():
                    seg_before = tail
            primary, secondary = {
                "before": (seg_before, seg_after),
                "after": (seg_after, seg_before),
                "mixed": (seg_after, seg_before),
            }[pair_mode]
            label_raw = (primary or secondary or snap).strip()
            name = None
            for cand in (primary, secondary,
                         snap if not primary.strip() else ""):
                if cand and cand.strip():
                    name = match_chk(fold(cand))
                    # [batch 2b] exclusion TẦM FORM: key trùng với câu hỏi
                    # khác (legacy hoặc pha B) thì thử candidate kế
                    if name and name not in para_used and \
                            name not in form_used:
                        break
                    name = None
            if name is None:
                label_folded = norm_label(label_raw) if label_raw else ""
                if label_folded.strip():
                    name = _auto_chk_key(fold(label_folded), seen_auto_b)
            chosen.append((i, name, label_raw))
            if name:
                para_used.add(name)
                form_used.add(name)
        final.append((para, chosen))
    # Pha C — apply + đăng ký field theo thứ tự tài liệu
    for para, chosen in final:
        assignments = []
        for i, name, label_raw in chosen:
            if name:
                assignments.append((i, i + 1, "{chk_%s}" % name))
                add_field("chk_%s" % name, label_raw, type_="chk")
            else:
                unmatched.append({"form": form_id, "where": "chk[p]",
                                  "label": label_raw[:100]})
        apply_tags_to_para(para, assignments)


# ---------------------------------------------------------------------------
# Header 2-band (Việc 2 — lệnh owner 2026-08-28)
#
# Hiện trạng nguồn docx scrape được xếp DỌC: "TÊN …/-----", "CỘNG HÒA …/Độc lập
# …/-----", "Số: …", "……, ngày … tháng … năm …" mỗi cái một paragraph canh
# giữa/trái riêng -> bản in lệch hẳn bản Word gốc (PL II Mẫu 2 / PL I Mẫu 13 —
# TT 68/2025/TT-BTC). Bản gốc là 2 băng ngang:
#     BAND 1 | TÊN ….. + dòng kẻ | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
#            |                    | Độc lập - Tự do - Hạnh phúc  (gạch chân)
#     BAND 2 | Số: …              | ……, ngày … tháng … năm …
#
# Cách làm: TRƯỚC khi gắn the, generator TÁI DỤNG 4 paragraph đó thành một
# w:tbl KHÔNG VIỀN 2 cột. Các paragraph nguồn được DI CHUYỂN nguyên vẹn
# (giữ w:r/w:rPr/w:jc/w:spacing) vào ô tương ứng nên KHÔNG có the {..} nào
# mất; the {so_van_ban} và nhóm ngày/tháng/năm được gắn SAU đó bằng đúng bộ
# rule R qua _assign_para_slots (section_ctx rỗng — giống vị trí cũ ở đầu
# tài liệu) nên form_maps KHÔNG đổi key/label.
# Idempotent: transformation chỉ đọc file nguồn pristine, chạy lại ra cùng
# kết quả (được chứng minh bằng test_header_layout + deep idempotency).
# ---------------------------------------------------------------------------

HEADER_BAND_TEMP_ATTR = "{urn:orca:hdr2col}band"

# Ô tiêu đề trái theo từng mẫu. Census 2026-08-28: grep
# 'TÊN DOANH NGHIỆP|TÊN HỘ KINH DOANH' trên app/data/blocks/*.json + đối chiếu
# trực tiếp nguồn docx trong 02_..06_:
#   PL I  (TÊN DOANH NGHIỆP) : 13,14,15,17,18,19,21,23,25,26,27,28,29,30,31,32,33
#   PL II (TÊN HỘ KINH DOANH): 02,03,04,05,06
# Các mẫu KHÔNG nằm trong danh sách (đã rà, không phải ô header 2-band):
#   PLI_M01..M05, M42, M43, M45..M57, M63, M66..M71, M75, M76, M78..M80 và
#   PLII_M01, M07..M28 — chỉ có khối quốc hiệu căn giữa (giấy chứng nhận /
#   thông báo / quyết định), KHÔNG có ô tên bên trái.
#   PLI_M11 — không có khối quốc hiệu; PLI_M06..M10 — không có header.
# Ngoại lệ CẦN OWNER (xem docs handoff):
#   PLI_M12 — nguồn docx MẤT ô "TÊN DOANH NGHIỆP" khi scrape; đồng thời
#             Thông tư 121/2026/TT-BTC (hiệu lực 21/8/2026) đã thay Mẫu 12
#             -> chờ nguồn mới theo TT 121, không tự chế nội dung.
#   PLI_M72 — "(TÊN DOANH NGHIỆP TƯ NHÂN)" là subtitle mục công bố, không
#             phải ô header; mẫu không có khối quốc hiệu.
#   PLI_M27, PLI_M30 — nằm trong census NƯNG cũng là 2/9 mẫu bị Thông tư
#             121/2026/TT-BTC thay thế; vẫn sửa layout (chỉ đổi hình thức,
#             không đổi nội dung) và đã ghi chú chờ đối chiếu bản TT 121.
HEADER_BAND_FORMS = {
    "PLI_M13": "TÊN DOANH NGHIỆP",
    "PLI_M14": "TÊN DOANH NGHIỆP",
    "PLI_M15": "TÊN DOANH NGHIỆP",
    "PLI_M17": "TÊN DOANH NGHIỆP",
    "PLI_M18": "TÊN DOANH NGHIỆP",
    "PLI_M19": "TÊN DOANH NGHIỆP",
    "PLI_M21": "TÊN DOANH NGHIỆP",
    "PLI_M23": "TÊN DOANH NGHIỆP",
    "PLI_M25": "TÊN DOANH NGHIỆP",
    "PLI_M26": "TÊN DOANH NGHIỆP",
    "PLI_M27": "TÊN DOANH NGHIỆP",
    "PLI_M28": "TÊN DOANH NGHIỆP",
    "PLI_M29": "TÊN DOANH NGHIỆP",
    "PLI_M30": "TÊN DOANH NGHIỆP",
    "PLI_M31": "TÊN DOANH NGHIỆP",
    "PLI_M32": "TÊN DOANH NGHIỆP",
    "PLI_M33": "TÊN DOANH NGHIỆP",
    "PLII_M02": "TÊN HỘ KINH DOANH",
    "PLII_M03": "TÊN HỘ KINH DOANH",
    "PLII_M04": "TÊN HỘ KINH DOANH",
    "PLII_M05": "TÊN HỘ KINH DOANH",
    "PLII_M06": "TÊN HỘ KINH DOANH",
}

# Dòng 2 khối quốc hiệu — bản Word gốc có gạch chân thật; bản scrape thay
# bằng một dòng kẻ "-----". Chuyển đổi: bỏ dòng kẻ scraped, gạch chân thật.
HEADER_BAND_MOTTO_LINE1 = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
HEADER_BAND_MOTTO_LINE2 = "Độc lập - Tự do - Hạnh phúc"
# Chỉ dòng kẻ thuần dấu gạch/chấm mới được coi là decoration bỏ được.
HEADER_BAND_RULE_RE = re.compile(r"^[\s\-_.…—–]+$")
# "……, ngày…… tháng…… năm ……" — băng dưới cột phải
_HEADER_BAND_DATE_RE = re.compile(r"^[\s.…,;:\-–—]*ngay\b.*\bthang\b.*\bnam\b")
# Tỉ lệ chiều rộng cột TRÁI (phần còn lại cho khối quốc hiệu + ngày ký).
HEADER_BAND_LEFT_RATIO = 0.42
_HEADER_BAND_ALIGN = {(0, 0): "left", (0, 1): "center",
                      (1, 0): "left", (1, 1): "right"}


def _hdr_fold(text):
    return fold(re.sub(r"\s+", " ", text or "")).strip()


def _hdr_is_label(text, label):
    """Ô "TÊN DOANH NGHIỆP" / "TÊN HỘ KINH DOANH" (+ dòng kẻ điền tên)."""
    f = _hdr_fold(text)
    lf = _hdr_fold(label)
    if not f.startswith(lf):
        return False
    rest = f[len(lf):].strip().strip(":").strip()
    return rest == "" or bool(HEADER_BAND_RULE_RE.match(rest))


def _hdr_is_motto(text):
    f = _hdr_fold(text)
    return (_hdr_fold(HEADER_BAND_MOTTO_LINE1) in f
            and _hdr_fold(HEADER_BAND_MOTTO_LINE2) in f)


def _hdr_is_so(text):
    t = re.sub(r"\s+", " ", text or "").strip()
    return t.startswith("Số") and bool(DOT_RUN.search(t))


def _hdr_is_date(text):
    # nguồn scrape có tiền tố dấu chấm "……, ngày…" -> bỏ qua phần đầu không chữ
    return bool(_HEADER_BAND_DATE_RE.match(_hdr_fold(text)))


def _hdr_para_align(p_el, mode):
    """Gán w:jc cho paragraph (trái/phải/giữa) — giữ mọi pPr khác."""
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_el.insert(0, pPr)
    jc = pPr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        pPr.append(jc)
    jc.set(qn("w:val"), mode)


def _restyle_national_motto(p_el, form_id):
    """Đưa khối quốc hiệu về 2 dòng như bản Word gốc:
      1. BỎ dòng kẻ scraped ("-----") ở cuối — chỉ khi thuần dấu kẻ;
      2. GẠCH CHÂN thật dòng "Độc lập - Tự do - Hạnh phúc" (w:u).
    Trả về True nếu đã xử lý; raise ValueError khi cấu trúc lạ (fail loud —
    22 mẫu trong allowlist phải đồng nhất, lệch dạng phải bị nhìn thấy)."""
    runs = [r for r in p_el if r.tag == qn("w:r")]

    def _flat_elems():
        # w:t rỗng/scrape thừa (vd run cuối rỗng của PLII_M02) không phải một
        # dòng hiển thị -> loại khỏi cấu trúc dòng trước khi xét.
        out = []
        for r in runs:
            for ch in list(r):
                if ch.tag not in (qn("w:t"), qn("w:br"), qn("w:cr")):
                    continue
                if ch.tag == qn("w:t") and not (ch.text or "").strip():
                    continue
                out.append(ch)
        return out

    flat = _flat_elems()
    texts = [ch for ch in flat if ch.tag == qn("w:t")]
    if len(texts) < 2:
        raise ValueError("[hdr2col] %s: khối quốc hiệu chỉ có %d dòng text, "
                         "không nhận dạng được dòng kẻ" % (form_id, len(texts)))
    # 1) dòng kẻ ở CUỐI khối
    last = len(flat) - 1
    while last >= 0 and flat[last].tag in (qn("w:br"), qn("w:cr")):
        last -= 1
    if last < 0 or flat[last].tag != qn("w:t") \
            or not HEADER_BAND_RULE_RE.match(flat[last].text or ""):
        raise ValueError("[hdr2col] %s: dòng cuối khối quốc hiệu %r không phải "
                         "dòng kẻ scraped" % (form_id, (flat[last].text if last >= 0 else None)))
    rule_el = flat[last]
    prev_el = flat[last - 1] if last >= 1 else None
    if prev_el is None or prev_el.tag not in (qn("w:br"), qn("w:cr")):
        raise ValueError("[hdr2col] %s: dòng kẻ quốc hiệu không đứng sau <w:br/>"
                         % form_id)
    rule_el.getparent().remove(rule_el)
    prev_el.getparent().remove(prev_el)
    # 2) gạch chân dòng text cuối còn lại
    tail = [ch for ch in _flat_elems() if ch.tag == qn("w:t")]
    if not tail:
        raise ValueError("[hdr2col] %s: mất dòng text sau khi bỏ dòng kẻ" % form_id)
    t_el = tail[-1]
    if _hdr_fold(t_el.text) != _hdr_fold(HEADER_BAND_MOTTO_LINE2):
        raise ValueError("[hdr2col] %s: dòng dưới cùng %r không phải %r"
                         % (form_id, t_el.text, HEADER_BAND_MOTTO_LINE2))
    run_el = t_el.getparent()
    new_r = OxmlElement("w:r")
    old_rPr = run_el.find(qn("w:rPr"))
    rPr = OxmlElement("w:rPr")
    if old_rPr is not None:
        for ch in old_rPr:
            rPr.append(copy.deepcopy(ch))
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)          # w:u đứng sau w:sz/w:szCs -> append cuối là đúng thứ tự
    new_r.append(rPr)
    new_r.append(t_el)     # di chuyển w:t sang run mới
    run_el.addnext(new_r)
    return True


def _band_usable_width_twips(doc):
    """Chiều rộng vùng chữ (twips) theo sectPr đầu tiên; fallback A4 trừ lề."""
    try:
        sec = doc.sections[0]
        usable = int(sec.page_width) - int(sec.left_margin) - int(sec.right_margin)
        if usable > 0:
            return usable // 635
    except (IndexError, TypeError):
        pass
    return 9026  # A4 (11906) - 2 lề 1440


def _band_set_borders_none(tbl_el):
    """Bảng layout: KHÔNG viền (mọi mức tbl + tc), không lề ô."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    def none_borders(tag):
        el = OxmlElement(tag)
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:%s" % edge)
            e.set(qn("w:val"), "nil")
            el.append(e)
        return el

    tblPr = tbl_el.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    tblPr.append(none_borders("w:tblBorders"))
    cell_mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        e = OxmlElement("w:%s" % side)
        e.set(qn("w:w"), "0")
        e.set(qn("w:type"), "dxa")
        cell_mar.append(e)
    tblPr.append(cell_mar)
    for tc in tbl_el.iter("{%s}tc" % ns):
        tcPr = tc.find(qn("w:tcPr"))
        if tcPr is None:
            tcPr = OxmlElement("w:tcPr")
            tc.insert(0, tcPr)
        for old in tcPr.findall(qn("w:tcBorders")):
            tcPr.remove(old)
        tcPr.append(none_borders("w:tcBorders"))


_TBLPR_ORDER = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual",
                "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
                "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout",
                "tblCellMar", "tblLook", "tblCaption", "tblDescription")


def _band_order_tblPr(tbl_el):
    """Sắp con của w:tblPr theo thứ tự schema OOXML (Word nghiêm với tblPr)."""
    tblPr = tbl_el.tblPr
    kids = list(tblPr)
    rank = {qn("w:%s" % n): i for i, n in enumerate(_TBLPR_ORDER)}
    known = sorted((k for k in kids if k.tag in rank), key=lambda k: rank[k.tag])
    unknown = [k for k in kids if k.tag not in rank]
    for k in kids:
        tblPr.remove(k)
    for k in known + unknown:
        tblPr.append(k)


def build_header_band_table(doc, form_id):
    """Tái dụng 4 paragraph header dọc thành w:tbl không viền 2 cột.

    Trả về (tbl_element, [các w:p đã di chuyển]) hoặc None khi mẫu không nằm
    trong HEADER_BAND_FORMS. raise ValueError khi mẫu nằm trong allowlist mà
    cấu trúc nguồn lệch khỏi dạng chuẩn (không bao giờ bỏ im).
    """
    label = HEADER_BAND_FORMS.get(form_id)
    if not label:
        return None
    body = doc.element.body
    children = list(body.iterchildren())
    anchor = None
    for i, el in enumerate(children):
        if el.tag != qn("w:p"):
            continue
        from docx.text.paragraph import Paragraph
        if _hdr_is_label(Paragraph(el, doc).text, label):
            anchor = i
            break
    if anchor is None:
        raise ValueError("[hdr2col] %s: không tìm thấy ô %r trong nguồn"
                         % (form_id, label))
    # vị trí chèn bảng — phải khoá TRƯỚC khi di chuyển 4 paragraph vào ô
    insert_at = children.index(children[anchor])
    window = children[anchor:anchor + 4]
    if len(window) < 4 or any(el.tag != qn("w:p") for el in window):
        raise ValueError("[hdr2col] %s: 4 paragraph header không liền khối"
                         % form_id)
    from docx.text.paragraph import Paragraph
    texts = [Paragraph(el, doc).text for el in window]
    checks = (_hdr_is_motto(texts[1]), _hdr_is_so(texts[2]), _hdr_is_date(texts[3]))
    if not all(checks):
        raise ValueError("[hdr2col] %s: cấu trúc header lệch dạng chuẩn "
                         "(quốc hiệu/Số/ngày ký khớp: %r): %r"
                         % (form_id, checks, [t[:60] for t in texts]))

    # --- dựng bảng 2x2 rồi DI CHUYỂN paragraph gốc vào ô ---
    tbl = doc.add_table(rows=2, cols=2)
    tbl.autofit = False
    tbl_el = tbl._tbl
    total = _band_usable_width_twips(doc)
    left = int(round(total * HEADER_BAND_LEFT_RATIO))
    widths = (left, total - left)
    for ci, w in enumerate(widths):
        tbl.columns[ci].width = w * 635          # twips -> EMU
    # layout fixed + tcW KhỚP gridCol: Word lấy tcW của hàng đầu để chia cột
    for ri in range(2):
        for ci, w in enumerate(widths):
            cell = tbl.rows[ri].cells[ci]
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.insert(0, tcW)
            tcW.set(qn("w:type"), "dxa")
            tcW.set(qn("w:w"), str(w))
    if tbl_el.tblPr.find(qn("w:tblLayout")) is None:
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tbl_el.tblPr.append(layout)
    tblW = tbl_el.tblPr.find(qn("w:tblW"))
    if tblW is not None:
        tblW.set(qn("w:type"), "dxa")
        tblW.set(qn("w:w"), str(total))
    _band_set_borders_none(tbl_el)
    _band_order_tblPr(tbl_el)

    for ri in range(2):
        for ci in range(2):
            src = window[ri * 2 + ci]
            tc = tbl.rows[ri].cells[ci]._tc
            for p in tc.findall(qn("w:p")):
                tc.remove(p)
            tc.append(src)                       # di chuyển (không copy)
            _hdr_para_align(src, _HEADER_BAND_ALIGN[(ri, ci)])
    _restyle_national_motto(window[1], form_id)

    parent = body                       # 4 paragraph là con trực tiếp của body
    parent.insert(insert_at, tbl_el)
    tbl_el.set(HEADER_BAND_TEMP_ATTR, form_id)
    return tbl_el, window


def _pop_header_band(table):
    """Đọc + xoá thuộc tính tạm của bảng header 2-band; trả form_id hoặc None."""
    el = table._tbl
    raw = el.get(HEADER_BAND_TEMP_ATTR)
    if raw is None:
        return None
    del el.attrib[HEADER_BAND_TEMP_ATTR]
    return raw


def _tag_header_band_slots(table, form_id, add_field, unmatched):
    """Gắn the cho 2 ô băng dưới: "Số: …" và "……, ngày … tháng … năm …".

    Dùng ĐÚNG bộ rule R qua _assign_para_slots với section_ctx rỗng — giống
    hệt ngữ cảnh các paragraph này ở đầu tài liệu trước khi tái dụng, nên
    key/label trong form_maps KHÔNG đổi."""
    for ri, ci, where in ((1, 0, "hdr[1][0]"), (1, 1, "hdr[1][1]")):
        para = cell_first_para(tr_cells(table, ri)[ci])
        if para is None:
            continue
        full, _runs, groups = para_dot_groups(para)
        if not groups:
            continue
        assignments = _assign_para_slots(full, groups, add_field, unmatched,
                                        form_id, where)
        apply_tags_to_para(para, assignments)


# ---------------------------------------------------------------------------
# Quy trình chính
# ---------------------------------------------------------------------------

def load_csv_titles():
    titles = {}
    with open(ROOT / "99_muc_luc" / "muc_luc_bieu_mau.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = f"{row['phu_luc']}|{int(row['mau_so'])}"
            titles[key] = row["ten_mau"]
    return titles


def parse_form_id(path):
    stem = path.stem
    m = re.match(r"(?:DN_)?PL(\d)_Mau_(\d+)", stem)
    if not m:
        return None, None, None
    pl, mau = ("I" if m.group(1) == "1" else "II", int(m.group(2)))
    return f"PL{pl}_M{mau:02d}", pl, mau


def iter_docx_files():
    for folder in ["01_dang_ky_thanh_lap_doanh_nghiep", "02_thay_doi_thong_tin_doanh_nghiep",
                   "03_chi_nhanh_van_phong_dai_dien_dia_diem", "04_tam_ngung_cham_dut_giai_the",
                   "05_cong_bo_cung_cap_thong_tin", "06_ho_kinh_doanh_va_chuyen_doi"]:
        d = ROOT / folder
        if d.is_dir():
            yield from sorted(d.rglob("*.docx"))


# ---------------------------------------------------------------------------
# Phase 5R1 (WLAY-006): field code Word bị làm phẳng thành text literal
#
# Bản nguồn (vd PL2_Mau_28) chứa số trang dạng field code Word của FOOTER,
# nhưng converter cũ làm phẳng thành literal ` PAGE   \* MERGEFORMAT 2`
# trong một w:t ở cuối thân tài liệu — giá trị "2" là số trang CỦA BẢN NGUỒN
# (stale), không phải nội dung pháp lý của biểu mẫu. Chọn LOẠI paragraph thay
# vì dựng lại thành <w:fldSimple> vì: (1) field gốc thuộc footer nguồn, dựng
# lại trong thân tài liệu là SAI bố cục so với mẫu phát hành; (2) giá trị
# flatten là stale (không tự cập nhật) nên giữ lại sẽ lộ chữ rác như ảnh
# owner PLII_M28 trang 2 (WLAY-006).
# Pattern dùng CÙNG ngữ pháp với detector D2 của tools/phase5_visual_gate.py
# (FIELD_CODE_RE) để gate và generator không lệch nhau.
# ---------------------------------------------------------------------------
FLAT_FIELD_CODE_RE = re.compile(
    r"\b(?:PAGE|NUMPAGES|TOC|HYPERLINK|SEQ|STYLEREF|IF)\s*\\\*|\bMERGEFORMAT\b")


def drop_flat_field_code_paras(doc):
    """Xoá mọi paragraph có text chứa field code Word bị làm phẳng (match
    ANYWHERE — trùng ngữ pháp detector D2 của gate nên sau regen D2=0 đảm
    bảo). Token 'MERGEFORMAT' không bao giờ là nội dung pháp lý hợp lệ của
    biểu mẫu nên không có rủi ro mất chữ thật. Áp cho mọi form (rule chung,
    không riêng PLII_M28)."""
    n = 0
    for p in list(doc.paragraphs):
        txt = p.text
        if txt.strip() and FLAT_FIELD_CODE_RE.search(txt):
            p._p.getparent().remove(p._p)
            n += 1
    return n


# ---------------------------------------------------------------------------
# Phase 5R1 (WLAY-007b): banner PHỤ LỤC của phụ lục KẾ lọt vào đuôi mẫu
#
# Bước tách nguồn auto-extract (per-form file không có spec riêng) có chỗ
# vượt ranh giới: PL1_Mau_80 kéo theo cả banner mở đầu phụ lục kế
# ('PHỤ LỤC II' / 'BIỂU MẪU SỬ DỤNG TRONG ĐĂNG KÝ HỘ KINH DOANH' /
# '(Kèm theo Thông tư số 68/2025...)') vào cuối tài liệu — template PLI_M80
# in contaminated sang trang cuối (detector D4 của gate bắt đúng lỗi này).
# Rule boundary CHUNG cho mọi form PLI/PLII khi extract: gặp body-level
# paragraph banner "PHỤ LỤC <số la mã>" với số la mã KHÁC phụ lục của form
# thì CẮT từ paragraph đó đến hết body (giữ lại sectPr cuối). Mọi nội dung
# sau banner của phụ lục khác đều không thuộc form đang tách.
# Banner khớp khi TOÀN BỘ text gập dấu là 'phu luc <roman>' (khớp full),
# nên câu thân viện dẫn '... theo Phụ lục II ...' không bao giờ bị cắt.
# ---------------------------------------------------------------------------
ANNEX_BANNER_RE = re.compile(
    r"^phu luc\s*(i{1,3}|iv|v|vi{1,3}|ix|x|xi{0,3})$")


def drop_foreign_annex_tail(doc, own_pl):
    """Cắt đuôi body từ banner PHỤ LỤC khác phụ lục của form (giữ sectPr).
    Trả số element đã bỏ; 0 nếu không có contamination."""
    own = (own_pl or "").strip().upper()
    body_el = doc.element.body
    cutoff = None
    for child in list(body_el):
        if child.tag != qn("w:p"):
            continue
        texts = child.findall(".//" + qn("w:t"))
        folded = fold(" ".join(
            (t.text or "") for t in texts).strip())
        m = ANNEX_BANNER_RE.match(folded)
        if m and m.group(1).upper() != own:
            cutoff = child
            break
    if cutoff is None:
        return 0
    n = 0
    removing = False
    for child in list(body_el):
        if child is cutoff:
            removing = True
        if removing and child.tag != qn("w:sectPr"):
            body_el.remove(child)
            n += 1
    return n


# ---------------------------------------------------------------------------
# Phase 5R2 (WLAY-002): cụm 2 chữ ký xếp NGANG sinh thành bảng không viền 1x2
#
# Bản giấy PLI_M70 (Giấy tiếp nhận hồ sơ) có 2 chữ ký NGƯỜI NỘP / NGƯỜI NHẬN
# nằm CÙNG HÀNG NGANG (ảnh owner + audit 2026-09-03, docs/
# word_layout_audit_2026-09-03.md mục WLAY-002) nhưng bản nguồn docx extract
# được đã sập thành 2 paragraph dọc liên tiếp (title→instr, title→instr) —
# template sinh ra theo nguồn nên in ra 2 cụm XẾP DỌC (detector D6 của gate đo
# SIG_ORIENTATION vertical ×5 fixture, registry phase5r_expectations.json pin
# horizontal).
#
# Điều trị ở LỚP GENERATOR (không sửa tay template): khi registry của form pin
# orientation=horizontal với signers=2 (evidence-based — KHÔNG tự suy từ nguồn
# vì nguồn M70 chính là bản đã sập dọc), process_form tìm body-level CẶP
# paragraph ký chạy kề (mỗi paragraph chứa title khớp registry + instruction
# paren "(Ký…") rồi THAY CẶP bằng bảng không viền 1 hàng × 2 ô; paragraph
# gốc được giữ nguyên (deepcopy) vào từng ô để bảo toàn font/in-đậm/căn giữa
# và spacing before=120 — kèm 1 paragraph trống ghi vùng viết trong ô và
# w:tr/cantSplit để cụm ký không bị cắt qua trang (WLAY-003).
#
# Ràng buộc evidence: form KHÔNG có entry horizontal trong registry → hàm là
# no-op (0 bảng) — sandbox regen demo của test_generator_deep_idempotency và
# mọi form khác không đổi một byte nào.
# ---------------------------------------------------------------------------

SIGNATURE_EXPECT_PATH = ROOT / "tools" / "phase5r_expectations.json"


def load_signature_expectations(path: Path | None = None) -> dict:
    """Đọc registry kỳ vọng khối ký (tools/phase5r_expectations.json).
    File vắng mặt/không parse được -> {} (generator không bao giờ chết vì
    registry; census của Lane B giữ file luôn tồn tại)."""
    p = path or SIGNATURE_EXPECT_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _para_sig_lines(p_el) -> list[str]:
    """Tách paragraph thành các dòng logic theo w:br (title/instr thường là
    2 dòng trong 1 paragraph)."""
    lines: list[str] = []
    cur: list[str] = []
    for node in p_el.iter():
        if node.tag == qn("w:t"):
            cur.append(node.text or "")
        elif node.tag == qn("w:br"):
            lines.append("".join(cur))
            cur = []
    lines.append("".join(cur))
    return [ln for ln in lines if ln.strip()]


def _para_is_sig_cluster(p_el, title_folded: str) -> bool:
    """Paragraph là cụm ký của title đã biết: có dòng đầu khớp title (gập dấu)
    VÀ có dòng instruction paren '(Ký…'/'(Đã ký…'."""
    lines = _para_sig_lines(p_el)
    if not lines:
        return False
    has_title = any(
        re.sub(r"\s+", " ", fold(ln)).strip() == title_folded for ln in lines)
    if not has_title:
        return False
    return any(re.search(r"\((?:ky|da ky)", fold(ln)) for ln in lines)


def _body_content_width(body_el) -> int:
    """Bề rộng vùng chữ (twips) = pgSz.w - pgMar.left - pgMar.right của
    sectPr cuối; fallback A4 legder mặc định của corpus (12240-3600=8640)."""
    sect = None
    for child in body_el.iterchildren():
        if child.tag == qn("w:sectPr"):
            sect = child
    if sect is None:
        return 8640
    sz = sect.find(qn("w:pgSz"))
    mar = sect.find(qn("w:pgMar"))
    try:
        w = int(sz.get(qn("w:w"))) if sz is not None else 11906
        left = int(mar.get(qn("w:left"))) if mar is not None else 1440
        right = int(mar.get(qn("w:right"))) if mar is not None else 1440
        return max(2880, w - left - right)
    except (TypeError, ValueError):
        return 8640


# Token thay bằng .replace (KHÔNG dùng .format cho vùng nhúng XML serialize:
# paragraph template chứa placeholder {tag} — .format sẽ đọc nhầm là field).
_SIG_TABLE_TEMPLATE = (
    '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:tblPr>'
    '<w:tblW w:w="@@TOTAL_W@@" w:type="dxa"/>'
    '<w:tblBorders>'
    '<w:top w:val="nil"/><w:left w:val="nil"/>'
    '<w:bottom w:val="nil"/><w:right w:val="nil"/>'
    '<w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
    '</w:tblBorders>'
    '<w:tblLayout w:type="fixed"/>'
    '</w:tblPr>'
    '<w:tblGrid>@@GRID@@</w:tblGrid>'
    '<w:tr><w:trPr><w:cantSplit/>'
    '<w:trHeight w:val="1200" w:hRule="atLeast"/></w:trPr>'
    '@@CELLS@@</w:tr>'
    '</w:tbl>'
)

# Ô ký: tcW dxa + paragraph cụm ký (deepcopy) + 1 paragraph trống exact 240
# twips làm vùng viết ngay dưới instruction trong ô.
_SIG_CELL_TEMPLATE = (
    '<w:tc><w:tcPr><w:tcW w:w="@@CELL_W@@" w:type="dxa"/>'
    '<w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/>'
    '<w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders></w:tcPr>'
    '@@PARA@@'
    '<w:p><w:pPr>'
    '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="exact"/>'
    '</w:pPr></w:p>'
    '</w:tc>'
)


def build_horizontal_signature_tables(doc, form_id, section_specs=None) -> int:
    """Hợp nhất cặp cụm ký DỌC thành bảng không viền 1 hàng × 2 ô cho form có
    registry pin horizontal (WLAY-002).

    Hai dạng nguồn được hỗ trợ:
      (a) 2 paragraph ký chạy kề ở body-level (nguồn extract thô);
      (b) bảng 2 hàng × 1 cột do spec rebuild (output-table W1) vừa chèn —
          mỗi ô chứa đúng 1 cụm ký khớp titles[0]/titles[1].
    Cả hai được thay bằng MỘT bảng không viền 1x2: mỗi ô giữ paragraph cụm ký
    (deepcopy) + 1 paragraph trống exact 240 twips làm vùng viết, hàng có
    cantSplit (chống cắt trang — WLAY-003). Trả số bảng đã tạo (0 = no-op)."""
    sig = ((load_signature_expectations().get(form_id) or {})
           .get("signature") or {})
    if sig.get("orientation") != "horizontal" or sig.get("signers") != 2:
        return 0
    titles_folded = [re.sub(r"\s+", " ", fold(t)).strip()
                     for t in (sig.get("titles") or [])]
    if len(titles_folded) != 2:
        return 0
    body_el = doc.element.body
    made = 0

    # --- (a) cặp paragraph dọc chạy kề ---
    children = list(body_el.iterchildren())
    i = 0
    while i < len(children) - 1:
        a, b = children[i], children[i + 1]
        paired = (
            a.tag == qn("w:p") and b.tag == qn("w:p")
            and _para_is_sig_cluster(a, titles_folded[0])
            and _para_is_sig_cluster(b, titles_folded[1]))
        if not paired:
            i += 1
            continue
        total_w = _body_content_width(body_el)
        cell_w = total_w // 2
        cells = []
        for p_el in (a, b):
            cells.append(_SIG_CELL_TEMPLATE
                         .replace("@@CELL_W@@", str(cell_w))
                         .replace("@@PARA@@", _ser_element(copy.deepcopy(p_el))))
        new_tbl = _parse_sig_table(total_w, cell_w, cells)
        body_el.replace(a, new_tbl)
        body_el.remove(b)
        _ensure_para_after(body_el, new_tbl)
        made += 1
        children = list(body_el.iterchildren())
        i += 1

    # --- (b) bảng 2x1 do spec rebuild (output-table W1) ---
    for tbl_el in list(body_el.iterchildren()):
        if tbl_el.tag != qn("w:tbl"):
            continue
        if not _is_vertical_sig_table(tbl_el, titles_folded):
            continue
        total_w = _body_content_width(body_el)
        cell_w = total_w // 2
        cells = []
        labels = []
        for tr in _tbl_rows(tbl_el):
            tc = _row_cells(tr)[0]
            p_el = _cell_sig_para(tc, titles_folded[len(cells)])
            para = copy.deepcopy(p_el)
            # Spec builder dựng ô grid từ nhãn thô (mất căn giữa + spacing
            # before của paragraph nguồn) — khôi phục đúng thuộc tính nguồn
            # (jc=center, spacing before=120) để ô ký in như bản giấy.
            _style_sig_para(para)
            labels.append("\n".join(_para_sig_lines(para)))
            cells.append(_SIG_CELL_TEMPLATE
                         .replace("@@CELL_W@@", str(cell_w))
                         .replace("@@PARA@@", _ser_element(para)))
        new_tbl = _parse_sig_table(total_w, cell_w, cells)
        body_el.replace(tbl_el, new_tbl)
        _ensure_para_after(body_el, new_tbl)
        made += 1
        # Đồng bộ metadata section_spec (output-table) theo hình dạng mới để
        # form_maps không mô tả lệch template (rows 2x1 -> 1x2). Ghép đúng
        # entry bằng grid labels khớp titles registry (không đoán theo index).
        if section_specs is not None:
            want = [re.sub(r"\s+", " ", fold(x)).strip()
                    for x in titles_folded]
            for base in section_specs:
                grid = base.get("grid") or {}
                lab = [re.sub(r"\s+", " ", fold(x)).strip()
                       for x in (grid.get("labels") or [])]
                if (base.get("kind") == "output-table"
                        and grid.get("rows") == 2 and grid.get("cols") == 1
                        and [re.sub(r"\s*\(.*$", "", x) for x in lab] == want):
                    base["grid"] = {"rows": 1, "cols": 2, "labels": labels}
    return made


def _tbl_rows(tbl_el) -> list:
    return [tr for tr in tbl_el if tr.tag == qn("w:tr")]


def _row_cells(tr_el) -> list:
    return [tc for tc in tr_el if tc.tag == qn("w:tc")]


def _is_vertical_sig_table(tbl_el, titles_folded) -> bool:
    """Bảng 2 hàng × 1 cột, ô hàng i chứa đúng cụm ký titles[i]."""
    trs = _tbl_rows(tbl_el)
    if len(trs) != 2:
        return False
    for i, tr in enumerate(trs):
        tcs = _row_cells(tr)
        if len(tcs) != 1:
            return False
        if _cell_sig_para(tcs[0], titles_folded[i]) is None:
            return False
    return True


def _cell_sig_para(tc_el, title_folded):
    """Paragraph cụm ký khớp title trong ô (duyệt mọi w:p của ô)."""
    for p in tc_el.iter(qn("w:p")):
        if _para_is_sig_cluster(p, title_folded):
            return p
    return None


def _style_sig_para(p_el) -> None:
    """Đảm bảo pPr có w:jc=center + w:spacing before=120 (thuộc tính paragraph
    ký trên bản nguồn; spec builder grid làm rơi)."""
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_el.insert(0, pPr)
    if pPr.find(qn("w:spacing")) is None:
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:before"), "120")
        # schema order: spacing đứng trước w:jc — chèn đầu pPr là an toàn cho
        # 2 thuộc tính này (pStyle/keep* không tồn tại trên ô grid builder).
        pPr.insert(0, sp)
    if pPr.find(qn("w:jc")) is None:
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "center")
        pPr.append(jc)


def _parse_sig_table(total_w: int, cell_w: int, cells_xml: list[str]):
    grid = "".join('<w:gridCol w:w="%d"/>' % cell_w for _ in cells_xml)
    tbl_xml = (_SIG_TABLE_TEMPLATE
               .replace("@@TOTAL_W@@", str(total_w))
               .replace("@@GRID@@", grid)
               .replace("@@CELLS@@", "".join(cells_xml)))
    from docx.oxml import parse_xml
    return parse_xml(tbl_xml)


def _ensure_para_after(body_el, tbl_el) -> None:
    """OOXML: sau bảng phải có w:p (không được kề bảng khác/sectPr)."""
    sib = tbl_el.getnext()
    if sib is None or sib.tag != qn("w:p"):
        tbl_el.addnext(OxmlElement("w:p"))


def _ser_element(el) -> str:
    """Serialize lxml element về chuỗi XML (để nhúng vào parse_xml template)."""
    from lxml import etree
    return etree.tostring(el, encoding="unicode")


def process_form(path, titles, coverage, out_tpl=None):
    form_id, pl, mau = parse_form_id(path)
    rel = path.relative_to(ROOT).as_posix()
    doc = Document(str(path))
    # WLAY-006: bỏ field code số trang bị làm phẳng của bản nguồn TRƯỚC khi
    # tái dựng/gắn the để không pass nào nhìn thấy nó.
    drop_flat_field_code_paras(doc)
    # WLAY-007b: cắt banner PHỤ LỤC khác phụ lục của form lọt vào đuôi
    # (contamination bước tách nguồn — bài học PLI_M80).
    drop_foreign_annex_tail(doc, pl)
    # tái dựng bảng danh sách đã mất khi convert (spec từ tools/form_specs/ hoặc
    # fallback khai báo inline REBUILD_TABLES)
    ext = load_form_spec(form_id)
    rebuild_list_tables(doc, form_id, ext)
    # Việc 2 (2026-08-28): tái dụng header dọc thành bảng 2-band không viền
    # TRƯỚC khi gắn the — các mẫu trong HEADER_BAND_FORMS, lệch dạng phải fail loud.
    build_header_band_table(doc, form_id)
    fields = []          # [{key,label,(type)}]
    dyn_tables = []
    section_specs = []   # metadata cấu trúc của kind mới (fixed-matrix, ...)
    unmatched = []

    def add_field(key, label, type_=None):
        if key and not any(f["key"] == key for f in fields):
            entry = {"key": key, "label": label.strip()[:120]}
            if type_:
                entry["type"] = type_
            fields.append(entry)

    def _register_section_spec(info, table, tbl_idx, fid, out, register_field):
        """Đăng ký bảng dựng từ kind mới: section_spec (cấu trúc) + fields.

        Chỉ ô người dùng nhập được đăng ký thành field form_maps; ô computed
        / output_only KHÔNG được đăng ký để không có dữ liệu giả nào ghi đè
        kết quả tính lại lúc export."""
        spec = info["spec"]
        kind = info["kind"]
        sem = info.get("semantic_key") or info.get("occurrence_id")
        base = {"kind": kind, "id": info["spec_id"], "semantic_key": sem,
                "section_id": info.get("section_id") or info["spec_id"],
                "table_index": tbl_idx}
        if kind == KIND_FIXED_MATRIX:
            cols = spec["columns"]
            base["columns"] = [{"col": ci, "header": c["header"],
                                "tag": c["tag"], "input_type": c["input_type"],
                                "computed": c["computed"],
                                "output_only": c["output_only"],
                                "required": c["required"]}
                               for ci, c in enumerate(cols)]
            base["fixed_rows"] = [dict(r) for r in spec["fixed_rows"]]
            base["totals"] = [dict(t) for t in spec["totals"]]
            editable_rows = {r["id"] for r in spec["fixed_rows"]
                             if not r["output_only"]}
            for c in cols:
                tag = c["tag"]
                if not tag or c["computed"]:
                    continue
                for r in sorted(editable_rows):
                    register_field("%s.%s.%s" % (sem, r, tag), "%s.%s" % (
                        r, tag))
        elif kind == KIND_NESTED_GRID:
            loop_name = info.get("loop") or sem
            header_texts = [[c["text"] for c in row]
                            for row in spec["header_rows"]]
            base.update({
                "loop": loop_name,
                "header_rows": [[{k: cell[k] for k in
                                  ("text", "rowspan", "colspan", "col_index")}
                                 for cell in row]
                                for row in _header_layout(spec)],
                "header_texts": header_texts,
                "width": spec["width"],
                "columns": [dict(c) for c in spec["columns"]],
                "stt": dict(spec["stt"]),
                "discriminator": (dict(spec["discriminator"])
                                  if spec.get("discriminator") else None),
                "totals": [],
            })
            # dòng dữ liệu trong dynamic_tables giữ đúng hình dạng cũ để UI/
            # GRID_META đọc không đổi (kèm semantic_key khi là occurrence).
            dyn = {
                "id": info["spec_id"], "table_index": tbl_idx,
                "template_row": len(table.rows) - 1,
                "loop": loop_name,
                "columns": [{"col": c["col_index"], "tag": c["tag"]}
                            for c in spec["columns"]],
            }
            dyn["header_row"] = 0
            if info.get("occurrence_id"):
                dyn["semantic_key"] = info["occurrence_id"]
                dyn["occurrence_id"] = info["occurrence_id"]
                if info.get("sync_group"):
                    dyn["sync_group"] = info["sync_group"]
            dyn_tables.append(dyn)
            for c in spec["columns"]:
                if c["tag"] and not c["output_only"]:
                    register_field("%s.%s" % (loop_name, c["tag"]), c["tag"])
        else:  # output-table
            base["grid"] = {k: spec["grid"][k] for k in ("rows", "cols",
                                                         "labels")}
            base["inputs"] = []
        out.append(base)

    body_blocks = list(doc.element.body.iterchildren())

    # ---- quét tuần tự các block ----
    section_ctx = ""     # ngữ cảnh phần: text gộp của paragraph gần nhất KHÔNG có slot
    pending_label = ""   # nhãn treo: paragraph không slot kết thúc bằng ":" (slot nằm ở đoạn sau)
    tbl_idx = -1
    for bi, child in enumerate(body_blocks):
        if child.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            full, runs, groups = para_dot_groups(para)
            if not groups:
                t = full.strip()
                # [Phase 5 fix bug owner] Tab-slot: dòng "Tôi là1 (ghi họ tên
                # bằng chữ in hoa): \t" của PLI_M01 dùng tab-stop thay nhóm
                # dấu chấm dẫn -> rule chu_hkd.ho_ten không có nhóm để gắn,
                # ô TEN CHỦ DOANH NGHIỆP bị thiếu hoàn toàn trong app và
                # trống trong DOCX export (M02/M03/PLII_M01 dùng dấu chấm
                # nên không bao giờ vào nhánh này). Chỉ áp cho ĐÚNG nhãn này
                # khi có tab — zero collateral với paragraph khác.
                if ("\t" in full and t and
                        re.search(r"toi ?la.*ghi ho ten bang chu in hoa",
                                  norm_label(t))):
                    ti_ = full.rfind("\t")
                    apply_tags_to_para(para, [(ti_, ti_ + 1,
                                               "{chu_hkd.ho_ten}")])
                    add_field("chu_hkd.ho_ten", t)
                if t and len(fold(t)) >= 8:
                    section_ctx = fold(re.sub(r"\s+", " ", t))[:400]
                pending_label = t if t.endswith(":") else ""
                continue
            assignments = _assign_para_slots(
                full, groups, add_field, unmatched, form_id, f"p[{bi}]",
                section_ctx=section_ctx, pending_label=pending_label)
            apply_tags_to_para(para, assignments)
        elif child.tag == qn("w:tbl"):
            tbl_idx += 1
            from docx.table import Table
            table = Table(child, doc)
            if _pop_header_band(table) is not None:
                # Bảng header 2-band (Việc 2): cấu trúc biết trước, the gắn
                # riêng cho 2 ô băng dưới; KHÔNG đi qua detect_dynamic để
                # không bị nhận nhầm là bảng danh sách.
                _tag_header_band_slots(table, form_id, add_field, unmatched)
                continue
            grid_info = _pop_grid_meta(table)
            if grid_info is not None:
                # Bảng dựng từ kind mới (fixed-matrix / nested-grid /
                # output-table): the đã được builder gắn sẵn — chỉ đăng ký
                # metadata cấu trúc + fields, KHÔNG đi qua nhánh detect/tag cũ.
                _register_section_spec(grid_info, table, tbl_idx, form_id,
                                       section_specs, add_field)
                continue
            det = detect_dynamic(
                table, tuple(ext["specs_by_id"].values()) if ext else ())
            # Occurrence (P1): bảng do rebuild chèn theo "occurrences" mang
            # thuộc tính XML tạm -> loop/semantic_key riêng theo occurrence_id.
            occ_info = _pop_table_occurrence(table)
            if occ_info is not None and det is None:
                print("[occ-rebuild] %s: bang occurrence %r khong khop spec "
                      "detect nao -> bo qua gan the rieng"
                      % (form_id, occ_info["occurrence_id"]))
            if det:
                spec, hdr_row = det
                # loop hieu luc: occurrence_id khi la bang occurrence; neu
                # occurrence khai bao "loop" rieng thi uu tien de bao toan
                # canonical key (semantic_key van = occurrence_id).
                loop_name = ((occ_info.get("loop")
                              or occ_info["occurrence_id"]) if occ_info
                             else spec["loop"])
                cols = []
                row_cells = tr_cells(table, hdr_row)
                col_tags = {}
                ci = 0
                for cell in row_cells:
                    h = fold(re.sub(r"\s+", " ", cell.text)).strip()
                    tag = None
                    for pat, tg in spec["cols"]:
                        if re.search(pat, h):
                            tag = tg
                            break
                    col_tags[ci] = tag
                    if tag:
                        cols.append({"col": ci, "header": cell.text.strip(), "tag": tag})
                    ci += 1
                # gan the vao hang du lieu mau: hang sau cung cua bang (de trong).
                # Bảng đã rebuild được gắn the sẵn (kèm {_stt} ở cột STT nếu có)
                # nên chỉ gắn lại khi hàng mẫu chưa chứa marker loop — tránh xóa
                # mất the {_stt} đã đặt bởi _build_list_table.
                tpl_row_idx = len(table.rows) - 1
                tagged_cols = {c: t for c, t in col_tags.items() if t}
                if not tagged_cols:
                    continue
                tpl_txt = "".join(cell.text for cell in tr_cells(table, tpl_row_idx))
                pre_tagged = ("{#%s}" % loop_name in tpl_txt
                              and "{/%s}" % loop_name in tpl_txt)
                if not pre_tagged:
                    first_col = min(tagged_cols)
                    last_col = max(tagged_cols)
                    for cidx, tag in tagged_cols.items():
                        try:
                            cell = table.rows[tpl_row_idx].cells[cidx]
                        except IndexError:
                            continue
                        p = cell_first_para(cell)
                        if p is None:
                            continue
                        if cidx == first_col:
                            prefix = "{#%s}" % loop_name
                        else:
                            prefix = ""
                        suffix = "{/%s}" % loop_name if cidx == last_col else ""
                        for r_ in p.runs:
                            r_.text = ""
                        if p.runs:
                            p.runs[0].text = f"{prefix}{{{tag}}}{suffix}"
                        else:
                            p.add_run(f"{prefix}{{{tag}}}{suffix}")
                for fldname in spec["fields"]:
                    add_field("%s.%s" % (loop_name, fldname), fldname)
                dyn = {
                    "id": spec["id"], "table_index": tbl_idx,
                    "header_row": hdr_row, "template_row": tpl_row_idx,
                    "loop": loop_name, "columns": cols,
                }
                if occ_info:
                    # GRID_META/đồng bộ draft phía app key theo occurrence_id;
                    # sync_group là tùy chọn để gộp draft giữa các occurrence.
                    dyn["semantic_key"] = occ_info["occurrence_id"]
                    dyn["occurrence_id"] = occ_info["occurrence_id"]
                    if occ_info.get("sync_group"):
                        dyn["sync_group"] = occ_info["sync_group"]
                dyn_tables.append(dyn)
            else:
                # bang tinh: slot trong o sau o nhan
                for ri in range(len(table.rows)):
                    row_cells = tr_cells(table, ri)
                    prev_label = ""
                    for cell in row_cells:
                        txt = cell.text
                        has_dots = bool(DOT_RUN.search(txt))
                        if has_dots:
                            lab = norm_label(prev_label or txt.split(DOT_RUN.search(txt)[0].group(0))[0])
                            matched = False
                            for pat, key, grps, ctx in R:
                                if pat and re.search(pat, lab):
                                    if ctx and not re.search(ctx, section_ctx):
                                        continue
                                    p = cell_first_para(cell)
                                    if p is not None:
                                        full, runs, groups = para_dot_groups(p)
                                        if groups:
                                            apply_tags_to_para(
                                                p, [(groups[0][0], groups[-1][1], "{%s}" % key)])
                                    add_field(key, prev_label)
                                    matched = True
                                    break
                            if not matched:
                                unmatched.append({"form": form_id,
                                                  "where": f"t[{tbl_idx}]({ri})",
                                                  "label": (prev_label or txt)[:100]})
                            prev_label = ""
                        else:
                            t = txt.strip()
                            if t:
                                prev_label = t

    # ---- checkbox pass (chạy sau khi gắn the slot) ----
    process_checkboxes(doc, form_id, add_field, unmatched)

    # Phase 5R2 (WLAY-002): cụm 2 cụm ký dọc chạy kề của form được registry
    # pin horizontal -> thay bằng bảng không viền 1x2 (no-op cho form khác).
    n_sig_tbl = build_horizontal_signature_tables(
        doc, form_id, section_specs=section_specs)
    if n_sig_tbl:
        print("[sig-1x2] %s: %d khoi ky gop thanh bang ngang" % (
            form_id, n_sig_tbl))

    # [6V-V2/C1] chuẩn hóa skeleton glue (B1/D13): chèn space quanh {tag}
    # khi kề word char / ':' / '(' — rule + 3 ví dụ đối chứng bản giấy ở
    # comment khối trên _GLUETAG_RE. Chạy SAU mọi pass gắn the (slot/chk/
    # header band/bảng ký) để thấy layout the cuối cùng.
    n_glue_fix = normalize_skeleton_glue(doc)
    if n_glue_fix:
        print("[glue-fix] %s: chen %d space quanh the" % (form_id, n_glue_fix))

    title = titles.get(f"Phu luc {pl}|{mau}", path.stem)
    # out_tpl cho phép sandbox regen ghi chỗ khác (test không đụng
    # app/templates — Lead sẽ regen chính thức)
    out_dir = out_tpl or OUT_TPL
    out_dir.mkdir(parents=True, exist_ok=True)
    # don sach thuoc tinh XML tam cua occurrence truoc khi luu template
    _scrub_occurrence_attrs(doc)
    tmp_copy = out_dir / f"{form_id}.docx"
    save_template_content_aware(doc, tmp_copy)
    meta = {
        "id": form_id, "phu_luc": pl, "mau_so": mau,
        "ten_mau": title, "file": rel, "template": f"templates/{form_id}.docx",
        "fields": fields,
    }
    if dyn_tables:
        meta["dynamic_tables"] = dyn_tables
    if section_specs:
        meta["section_specs"] = section_specs
    return meta, unmatched


def save_template_content_aware(doc, out_path: Path) -> bool:
    """Phase 5R1: ghi template CHỈ khi nội dung zip đổi thật.

    `doc.save()` serialize lại toàn bộ zip với timestamp MỚI mỗi lần chạy nên
    regen idempotent về nội dung vẫn churn byte toàn bộ 87 template — gate
    diff-vs-baseline (H7/N9a) mất ý nghĩa. So sánh per-entry decompressed
    bytes (timestamp nằm ở zip directory, không nằm trong entry bytes) giữa
    bản mới và file trên đĩa: identical -> KHÔNG ghi, giữ nguyên byte cũ.
    Trả True nếu đã ghi, False nếu skip."""
    import io

    buf = io.BytesIO()
    doc.save(buf)
    new_bytes = buf.getvalue()
    if out_path.exists():
        try:
            with zipfile.ZipFile(str(out_path)) as old, \
                    zipfile.ZipFile(io.BytesIO(new_bytes)) as new:
                on, nn = old.namelist(), new.namelist()
                if on == nn and all(
                        old.read(n) == new.read(n) for n in on):
                    return False
        except zipfile.BadZipFile:
            pass  # file cũ hỏng -> ghi đè bằng bản mới
    out_path.write_bytes(new_bytes)
    return True


# [Owner P1=A 2026-09-03] Nguồn canonical per-form — override first-hit
# aliasing (backlog W2 #5): PLI_M03/M04 dùng bản tách từ bản gốc ĐẦY ĐỦ
# (PL1_Mau_NN_tach_tu_file_full.docx) thay cho bản convert DN_* bị cắt
# phần đuôi mục 8–11/10–13 (delta 116→226 / 149→260 dòng — packet P1).
SOURCE_OVERRIDES = {
    "PLI_M03": ("06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/"
                "PL1_Mau_03_tach_tu_file_full.docx"),
    "PLI_M04": ("06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/"
                "PL1_Mau_04_tach_tu_file_full.docx"),
}


def find_source(form_id):
    """Tìm file nguồn docx của một form_id (quét các thư mục nguồn)."""
    if form_id in SOURCE_OVERRIDES:
        p = ROOT / SOURCE_OVERRIDES[form_id]
        if p.exists():
            return p
        raise SystemExit("SOURCE_OVERRIDES[%s] khong ton tai: %s"
                         % (form_id, p))
    for path in iter_docx_files():
        if path.name.startswith("~$") or path.name.startswith("_"):
            continue
        fid, _, _ = parse_form_id(path)
        if fid == form_id:
            return path
    raise SystemExit("Khong tim thay nguon cho %s" % form_id)


def write_maps(ordered):
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "form_maps.json").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")
    js = "// Sinh tu dong boi tools/build_form_maps.py - khong sua tay\nwindow.FORM_MAPS = "
    js += json.dumps(ordered, ensure_ascii=False, indent=1) + ";\n"
    (OUT_DATA / "form_maps.js").write_text(js, encoding="utf-8")


def main():
    args = sys.argv[1:]
    one_id = args[args.index("--one") + 1] if "--one" in args else None
    titles = load_csv_titles()
    if one_id:
        # Cập nhật ĐÚNG MỘT mẫu: ghi đè entry trong form_maps.json/form_maps.js
        # hiện có (giữ nguyên thứ tự và các mẫu khác) + template của mẫu đó.
        path = find_source(one_id)
        meta, unmatched = process_form(path, titles, None)
        ordered = json.loads(
            (OUT_DATA / "form_maps.json").read_text(encoding="utf-8"))
        ordered[meta["id"]] = meta  # key đã tồn tại -> giữ vị trí cũ
        write_maps(ordered)
        print("[--one] %s: %d fields, %d bang dong%s" % (
            meta["id"], len(meta["fields"]),
            len(meta.get("dynamic_tables", [])),
            "" if not unmatched else ", %d slot khong khop" % len(unmatched)))
        return
    all_meta = []
    all_unmatched = []
    for path in iter_docx_files():
        if path.name.startswith("~$") or path.name.startswith("_"):
            continue
        # SOURCE_OVERRIDES là nguồn canonical (vd M03/M04 tách từ bản gốc
        # đầy đủ): full-run phải BỎ các bản nguồn alias khác cùng form_id,
        # nếu không first/last-wins sẽ nhặt nhầm bản thô (Lane D F2 — --one
        # luôn đi qua find_source nên có override, full-run phải như vậy).
        fid, _, _ = parse_form_id(path)
        if fid in SOURCE_OVERRIDES and \
                path.relative_to(ROOT).as_posix() != SOURCE_OVERRIDES[fid]:
            continue
        meta, unmatched = process_form(path, titles, None)
        all_meta.append(meta)
        all_unmatched.extend(unmatched)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    # FIRST-WINS theo id (khớp find_source): hai thư mục nguồn alias cùng
    # một mẫu byte-identical (vd PLI_M70 ở 03_ và 05_) phải giữ path lần
    # ĐẦU — last-wins làm full-regen lật path so với committed (Lane D F2)
    ordered: dict = {}
    for m in all_meta:
        ordered.setdefault(m["id"], m)
    write_maps(ordered)
    report = {
        "total_forms": len(all_meta),
        "total_fields": sum(len(m["fields"]) for m in all_meta),
        "unmatched_slots": len(all_unmatched),
        "forms_without_any_field": [m["id"] for m in all_meta if not m["fields"]],
        "sample_unmatched": all_unmatched[:400],
    }
    rep_path = ROOT / "generated_ho_so" / "_coverage_report.json"
    rep_path.parent.mkdir(exist_ok=True)
    rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "sample_unmatched"},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
