# Bo bieu mau dang ky doanh nghiep - Thong tu 68/2025/TT-BTC

Nguon tai va doi chieu:
- Trang Thu vien Phap luat nguoi dung cung cap: https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/tai-phu-luc-bieu-mau-thong-tu-682025ttbtc-file-word-pdf-ve-dang-ky-doanh-nghiep-day-du-224133.html
- File Word day du da tai/trich xuat: `00_nguon_goc/Bieu_mau_PL_I_II_full.docx`
- File Word van ban goc kem OLE/ZIP: `00_nguon_goc/TT_68_2025_TT_BTC_full.docx`

## Cach sap xep

- `01_dang_ky_thanh_lap_doanh_nghiep`: mau dang ky thanh lap DNTN, TNHH 1TV, TNHH 2TV+, CTCP, hop danh; danh sach thanh vien/co dong/chu so huu huong loi; giay chung nhan tuong ung.
- `02_thay_doi_thong_tin_doanh_nghiep`: mau thay doi noi dung dang ky doanh nghiep, nguoi dai dien, chu DNTN, chu so huu TNHH 1TV, cap doi/cap lai/bo sung/cap nhat/hieu dinh/thu hoi/lien quan thay doi.
- `03_chi_nhanh_van_phong_dai_dien_dia_diem`: mau lap/thay doi/cham dut/tam ngung/cap giay chung nhan cho chi nhanh, van phong dai dien, dia diem kinh doanh.
- `04_tam_ngung_cham_dut_giai_the`: mau tam ngung, tiep tuc kinh doanh, cham dut hoat dong, giai the, huy giai the, thu hoi/khoi phuc.
- `05_cong_bo_cung_cap_thong_tin`: mau cong bo, cung cap thong tin, tiep nhan ho so, thong bao co quan thue, sua doi/bo sung, ra soat/hieu dinh.
- `06_ho_kinh_doanh_va_chuyen_doi`: toan bo mau ho kinh doanh Phu luc II va ban copy cac mau doanh nghiep thuong dung khi chuyen tu ho kinh doanh sang doanh nghiep.

Ghi chu: Thong tu 68/2025/TT-BTC khong co mot bieu mau rieng ten "chuyen doi ho kinh doanh sang doanh nghiep"; ho so thuong dung nhom mau dang ky thanh lap doanh nghiep tuong ung voi loai hinh du kien, kem xu ly dang ky ho kinh doanh theo Phu luc II khi can.

Xem bang day du tai `muc_luc_bieu_mau.csv`.

## App ho tro lap checklist

Mo `app/index.html` bang trinh duyet de chon nghiep vu, loai hinh va cac dieu kien lien quan. App se tra ve:

- Mau Word can dung.
- Giay to ngoai bieu mau can chuan bi.
- Cau hoi can chot truoc khi nop.
- Luu y rui ro theo Nghi dinh 168/2025/ND-CP va Thong tu 68/2025/TT-BTC.

De dung che do tu dong sinh file Word, chay:

```bash
python3 run_app.py
```

Sau do mo `http://127.0.0.1:8787/`. Ho so da sinh nam trong `generated_ho_so/`, kem file ZIP, checklist va JSON thong tin da nhap.

Gioi han cua ban hien tai: engine da dien cac truong chinh tren mau dang ky/thay doi/chi nhanh/tam ngung/giai the/ho kinh doanh. Cac bang lap lai nhu danh sach thanh vien, danh sach co dong, danh sach chu so huu huong loi can mo rong them man hinh nhap danh sach nhieu dong de dien hoan hao tung o trong bang.

Ban tu dong hoa uu tien hien tai da bo sung:

- 3 cum nghiep vu uu tien: thanh lap doanh nghiep, chuyen ho kinh doanh sang doanh nghiep, thay doi doanh nghiep.
- O nhap co quan dang ky kinh doanh va dia gioi hanh chinh theo dang tu do.
- Bang nhap nhieu dong cho thanh vien, co dong, chu so huu huong loi, nha dau tu nuoc ngoai.
- Sinh them Word phu tro: danh muc ho so, giay uy quyen, dieu le khung can ra soat, bang thong tin thanh vien/co dong/CSHHL, quyet dinh thay doi, bien ban hop thay doi, ghi chu nghia vu thue HKD khi chuyen doi.
- Kiem thu tu dong bang lenh:

```bash
python3 run_app.py --self-test
```

Bao cao self-test nam tai `generated_ho_so/SELF_TEST_REPORT.json`.

## Ban macOS .app

Da tao app native:

`Trợ lý hồ sơ ĐKKD.app`

App nay dung WebKit ben trong cua macOS va tu chay `run_app.py`, khong can mo Safari/Chrome. App dang gan voi folder hien tai:

`/Users/hoangminhlong/Downloads/xuly_dangky_doanhnghiep`

Neu di chuyen ca folder sang noi khac, can build lai bang:

```bash
bash macos_app/build_app.sh
```

## Map sau toan bo Word

Da tao ban do field cho 108 mau tai:

- `app/data/form_maps.json`
- `app/data/form_maps.js`

Lenh tao lai map:

```bash
python3 tools/build_form_maps.py
```

Lenh test engine voi toan bo 108 mau:

```bash
python3 run_app.py --map-test
```

Bao cao map-test nam tai `generated_ho_so/MAP_TEST_108_REPORT.json`.
