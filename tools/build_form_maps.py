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
"""
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
    (r"03 thang mot lan", "bc_03_thang"),
    (r"06 thang mot lan", "bc_06_thang"),
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
        if el.get(_OCC_TEMP_ATTR) is not None:
            del el.attrib[_OCC_TEMP_ATTR]


def _json_spec(raw_spec):
    """JSON spec -> dict spec cùng hình dạng phần tử DYNAMIC_TABLES."""
    return {
        "id": raw_spec["id"],
        "detect": set(raw_spec.get("detect") or []),
        "stt_tag": bool(raw_spec.get("stt_tag")),
        "cols": [(pat, tag) for pat, tag in raw_spec.get("cols") or []],
        "loop": raw_spec["loop"],
        "fields": list(raw_spec.get("fields") or []),
    }


def load_form_spec(form_id):
    """Đọc tools/form_specs/*/<form_id>.json nếu có.

    Trả về None khi không có file spec (mẫu dùng REBUILD_TABLES inline);
    ngược lại {"entries": [entry...], "specs_by_id": {spec_id: spec}} với
    entry là dict giống phần tử REBUILD_TABLES (trừ "spec" đã tách ra).
    Kết quả cache theo form_id trong tiến trình.
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
        specs_by_id = {}
        entries = []
        for e in raw.get("tables") or []:
            s = _json_spec(e["spec"])
            specs_by_id[s["id"]] = s
            ent = {k: v for k, v in e.items() if k != "spec"}
            ent["spec"] = s["id"]  # giữ hình dạng entry như REBUILD_TABLES inline
            entries.append(ent)
        # Occurrence (P1): validate som de chan spec sai truoc khi sua document.
        # Spec KHONG co "occurrences" khong bi anh huong gi (backward-compat).
        all_loops = {s["loop"] for s in specs_by_id.values()}
        for ent in entries:
            if ent.get("occurrences"):
                ent["_occurrences"] = table_occurrences.validate_occurrences(
                    ent["occurrences"], all_loops, form_id)
        result = {"entries": entries, "specs_by_id": specs_by_id}
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
    return tbl


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
        spec = resolve_rebuild_spec(e["spec"], ext)
        cfg = reg["cfg"]
        occ_spec = dict(spec)
        occ_spec["loop"] = cfg["occurrence_id"]
        tbl = _build_list_table(doc, e["headers"], occ_spec)
        _mark_table_occurrence(tbl._tbl, {
            "occurrence_id": cfg["occurrence_id"],
            "sync_group": cfg.get("sync_group"),
            "spec_id": spec["id"],
        })
        head_para = paras[reg["head"]]
        if e.get("pos", "after") == "before":
            head_para._p.addprevious(tbl._tbl)
        else:
            head_para._p.addnext(tbl._tbl)
        spacer = OxmlElement("w:p")
        tbl._tbl.addnext(spacer)
    # 3) chèn bảng mới tại điểm neo (entry legacy — bỏ qua entry occurrence
    # vì đã chèn ở bước 3a)
    for e in entries:
        if e.get("_occurrences"):
            continue
        spec = resolve_rebuild_spec(e["spec"], ext)
        anchor_p = None
        for para in _body_paragraphs(doc):
            if re.search(e["anchor"], _para_folded(para)):
                anchor_p = para
                break
        if anchor_p is None:
            print("[rebuild] KHONG tim thay anchor cho %s: %r" % (form_id, e["anchor"]))
            continue
        tbl = _build_list_table(doc, e["headers"], spec)
        if e.get("pos", "after") == "before":
            anchor_p._p.addprevious(tbl._tbl)
        else:
            anchor_p._p.addnext(tbl._tbl)
        spacer = OxmlElement("w:p")
        tbl._tbl.addnext(spacer)


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


def cell_first_para(cell):
    return cell.paragraphs[0] if cell.paragraphs else None


def match_chk(label_folded):
    for pat, name in CHK_RULES:
        if re.search(pat, label_folded.strip()):
            return name
    return None


def process_checkboxes(doc, form_id, add_field, unmatched):
    """Quét mọi paragraph (cả trong bảng), thay □/☐ bằng the {chk_*}."""
    from docx.text.paragraph import Paragraph

    last_label = ""
    for p_el in doc.element.body.iter(qn("w:p")):
        para = Paragraph(p_el, doc)
        full = "".join(r.text for r in para.runs)
        if not full.strip():
            continue
        pos = [i for i, ch in enumerate(full) if ch in CHK_SYMBOLS]
        if not pos:
            last_label = fold(full)
            continue
        assignments = []
        for k, i in enumerate(pos):
            seg_after = full[i + 1: pos[k + 1] if k + 1 < len(pos) else len(full)]
            seg_before = full[0:i] if k == 0 else full[pos[k - 1] + 1:i]
            name = None
            # ưu tiên: chữ ngay sau ô -> chữ trước ô -> paragraph trước đó
            for cand in (seg_after, seg_before, last_label if not seg_after.strip() else ""):
                if cand and cand.strip():
                    name = match_chk(fold(cand))
                    if name:
                        break
            if name:
                assignments.append((i, i + 1, "{chk_%s}" % name))
                add_field("chk_%s" % name, (seg_after or seg_before or last_label).strip(),
                          type_="chk")
            else:
                unmatched.append({"form": form_id, "where": "chk[p]",
                                  "label": (seg_after or seg_before or last_label).strip()[:100]})
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


def process_form(path, titles, coverage):
    form_id, pl, mau = parse_form_id(path)
    rel = path.relative_to(ROOT).as_posix()
    doc = Document(str(path))
    # tái dựng bảng danh sách đã mất khi convert (spec từ tools/form_specs/ hoặc
    # fallback khai báo inline REBUILD_TABLES)
    ext = load_form_spec(form_id)
    rebuild_list_tables(doc, form_id, ext)
    fields = []          # [{key,label,(type)}]
    dyn_tables = []
    unmatched = []

    def add_field(key, label, type_=None):
        if key and not any(f["key"] == key for f in fields):
            entry = {"key": key, "label": label.strip()[:120]}
            if type_:
                entry["type"] = type_
            fields.append(entry)

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
                if t and len(fold(t)) >= 8:
                    section_ctx = fold(re.sub(r"\s+", " ", t))[:400]
                pending_label = t if t.endswith(":") else ""
                continue
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
                    unmatched.append({"form": form_id, "where": f"p[{bi}]",
                                      "label": label.strip()[:100]})
                    prev_end = g_end
                    gi += 1
            apply_tags_to_para(para, assignments)
        elif child.tag == qn("w:tbl"):
            tbl_idx += 1
            from docx.table import Table
            table = Table(child, doc)
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
                # loop hieu luc: occurrence_id khi la bang occurrence
                loop_name = (occ_info["occurrence_id"] if occ_info
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

    title = titles.get(f"Phu luc {pl}|{mau}", path.stem)
    OUT_TPL.mkdir(parents=True, exist_ok=True)
    # don sach thuoc tinh XML tam cua occurrence truoc khi luu template
    _scrub_occurrence_attrs(doc)
    tmp_copy = OUT_TPL / f"{form_id}.docx"
    doc.save(str(tmp_copy))
    meta = {
        "id": form_id, "phu_luc": pl, "mau_so": mau,
        "ten_mau": title, "file": rel, "template": f"templates/{form_id}.docx",
        "fields": fields,
    }
    if dyn_tables:
        meta["dynamic_tables"] = dyn_tables
    return meta, unmatched


def find_source(form_id):
    """Tìm file nguồn docx của một form_id (quét các thư mục nguồn)."""
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
        meta, unmatched = process_form(path, titles, None)
        all_meta.append(meta)
        all_unmatched.extend(unmatched)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    ordered = {m["id"]: m for m in all_meta}
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
