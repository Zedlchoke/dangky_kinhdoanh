# HEADER-NAME CENSUS — 87 form đăng ký kinh doanh (Lane C, READ-ONLY)

- Lưu ý base: census đọc app/templates + app/data lúc HEAD `77b992a`; HEAD hiện tại `f927b96` không thay đổi 2 thư mục này (git diff 77b992a..f927b96 cho app/templates, app/data = rỗng) → kết quả còn nguyên giá trị. 4 file `tools/*` dirty là WIP của lane khác, không liên quan.
- Generated: 2026-09-05T20:51:12  |  base HEAD: `77b992a`  |  repo: `/Users/hoangminhlong/orca/dangky_kinhdoanh`
- Phạm vi: `word/document.xml` của 87 template `app/templates/<fid>.docx` (KHÔNG đụng `word/header*.xml` — các template không có header part riêng, band nằm trong body).
- Định nghĩa band: các body element từ đầu tới tiêu đề biểu mẫu (regex ^GIẤY ĐỀ NGHỊ/^ĐƠN/^THÔNG BÁO/^BÁO CÁO/^CÔNG BỐ/^GIẤY TIẾP NHẬN/^GIẤY CHỨNG NHẬN/^GIẤY XÁC NHẬN/^DANH SÁCH/^QUYẾT ĐỊNH... , fold dấu) hoặc 25 element đầu — lấy min. Bảng band 2 cột (tên trái + quốc hiệu phải) tính là band. Dòng logic tách theo `<w:br/>`.
- Literal lookup: fold hoa/thường + dấu theo 12 pattern nhiệm vụ ("Họ và tên" chỉ tính trong band).

## 1. Tóm tắt theo classification (216 occurrence / 87 form)

| Classification | Số occurrence | Số form | Ý nghĩa |
|---|---|---|---|
| **fillable-header-slot** | 22 | 22 | band tên chủ thể + fill-line, CHƯA bind token → cần mirror canonical key |
| already-bound (band) | 0 | 0 | KHÔNG form nào có band tên đã bind token |
| output-admin-only | 88 | — | tên chủ thể là nội dung output của cơ quan (giấy chứng nhận/xác nhận/quyết định/thông báo/công bố/giấy tiếp nhận), đã hoặc chưa bind |
| legal-title/subtitle | 97 | — | nhãn câu hỏi thân (đa số đã bind), tiêu đề mục, subtitle loại hình — ngoài band |
| not-applicable | 9 | — | prose/chú thích nhắc cụm tên; tiêu đề cột bảng danh sách (M10 "Họ và tên") |

- **22 form có fillable-header-slot** (cần mirror): 17 form DN (PLI_M13–M33) + 5 form hộ (PLII_M02–M06).
- **65 form không có band tên chủ thể nào** (band chỉ có quốc hiệu/Số/ngày hoặc là form danh sách/output): `PLII_M01` `PLII_M07` `PLII_M08` `PLII_M09` `PLII_M10` `PLII_M11` `PLII_M12` `PLII_M13` `PLII_M14` `PLII_M15` `PLII_M16` `PLII_M17` `PLII_M18` `PLII_M19` `PLII_M20` `PLII_M21` `PLII_M22` `PLII_M23` `PLII_M24` `PLII_M25` `PLII_M26` `PLII_M27` `PLII_M28` `PLI_M01` `PLI_M02` `PLI_M03` `PLI_M04` `PLI_M05` `PLI_M06` `PLI_M07` `PLI_M08` `PLI_M09` `PLI_M10` `PLI_M11` `PLI_M12` `PLI_M42` `PLI_M43` `PLI_M45` `PLI_M46` `PLI_M47` `PLI_M48` `PLI_M49` `PLI_M50` `PLI_M51` `PLI_M52` `PLI_M53` `PLI_M54` `PLI_M55` `PLI_M56` `PLI_M57` `PLI_M63` `PLI_M66` `PLI_M67` `PLI_M68` `PLI_M69` `PLI_M70` `PLI_M71` `PLI_M72` `PLI_M73` `PLI_M74` `PLI_M75` `PLI_M76` `PLI_M78` `PLI_M79` `PLI_M80`.
- RED FLAG `template-lost-signature` (nguồn CÓ cụm ký mà template MẤT): **KHÔNG có form nào** trong cả 87 form khảo sát nguồn 9 mẫu no-signature.

## 2. Bảng 22 form fillable-header-slot → proposed key

Band của cả 22 form cùng một kiểu: bảng đầu trang 2 ô, ô trái label + dòng gạch `-------` (2 run 1 paragraph tách `<w:br/>`), ô phải quốc hiệu; label nằm **cùng hàng** với quốc hiệu (`quoc_hieu_pos = same-band`); không ô nào có token.

| Form | Band label | Vị trí | Proposed key | Ghi chú |
|---|---|---|---|---|
| PLI_M13 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M14 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M15 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M21 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M26 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M17 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M18 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M19 | TÊN DOANH NGHIỆP | `tbl@1.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M23 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M25 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M28 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M29 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M27 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M30 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M31 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `dn.ten_tieng_viet` | |
| PLI_M32 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `chu_hkd.ho_ten`; `dn.ten_tieng_viet` | |
| PLI_M33 | TÊN DOANH NGHIỆP | `tbl@2.row0.cell0.para0` | `chu_hkd.ho_ten` | ⚠ needs-owner |
| PLII_M02 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | `hkd_ten_tieng_viet_2` | |
| PLII_M03 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | `hkd_ten_tieng_viet_2` | |
| PLII_M04 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | `hkd_ten_tieng_viet_2` | |
| PLII_M05 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | `hkd_ten_tieng_viet_2` | |
| PLII_M06 | TÊN HỘ KINH DOANH | `tbl@2.row0.cell0.para0` | `chu_hkd.ho_ten` | ⚠ needs-owner |

### Ghi chú riêng
- **PLI_M32**: owner đã chỉ định mirror `chu_hkd.ho_ten` (thân: "Tôi là (ghi họ tên bằng chữ in hoa): {chu_hkd.ho_ten}" — para 7). Literal "TÊN DOANH NGHIỆP" cũng khớp `dn.ten_tieng_viet` (para 16) — liệt kê làm alternative, cần owner chốt.
- **PLI_M33** ⚠ needs-owner: form kiểu M32 nhưng **không có input tên DN nào ở thân** (fields chỉ có `chu_hkd.ho_ten`). Options: (a) mirror `chu_hkd.ho_ten`; (b) thêm input tên DN mới nếu muốn band đúng literal.
- **PLII_M06** ⚠ needs-owner: band "TÊN HỘ KINH DOANH" nhưng thân không có input tên hộ; thân chỉ có `chu_hkd.ho_ten` + nhãn không bind "Là chủ hộ kinh doanh (Tên hộ kinh doanh) ....." (para 22). Options: (a) mirror `chu_hkd.ho_ten`; (b) bổ sung key tên hộ.
- PLII_M02–M05: key đề xuất `hkd_ten_tieng_viet_2` = key đang bind ở nhãn "Tên hộ kinh doanh (ghi bằng chữ in hoa)" ngay đầu thân. Riêng PLII_M02, các field tên SAU thay đổi đã bind qua token-đoạn-cách-dòng (`{hkd_ten_tieng_viet}`, `{hkd_ten_tieng_nuoc}`, `{hkd_ten_viet_tat}` ở para 18/20/22) — khác key, không thuộc phạm vi band.
- 17 form DN: `dn.ten_tieng_viet` đều là key bind ở nhãn "Tên doanh nghiệp (ghi bằng chữ in hoa)" 2–5 element sau band (PLI_M25 nhãn dài "Tên doanh nghiệp/Tên chi nhánh ..."). Đã verify token tồn tại trong document.xml của từng form.

## 3. Nhóm output-admin-only (88) — form do cơ quan phát hành

Gồm 44 form output (Giấy chứng nhận/Giấy xác nhận/Quyết định/Thông báo của CQĐKKD/Công bố 72–74/Giấy tiếp nhận M70–M71, PLII_M17–M18): tên chủ thể trong thân là nội dung được in ra. 85/88 occurrence đã bind token (`dn.ten_tieng_viet`, `hkd_ten_tieng_viet_2`, `yeu_cau_dn`...).

**3 ô output chưa bind — needs-owner (cân nhắc bind khi render, không thuộc sync band):**

| Form | Para | Dòng |
|---|---|---|
| PLI_M70 | 14 | `Điện thoại: {dien_thoai_khac} Thư điện tử: {email_khac} 01 bộ hồ sơ đăng ký doanh nghiệp/c` |
| PLI_M48 | 17 | `về việc: {ve_viec} của (Tên doanh nghiệp) ……………… Mã số doanh nghiệp (nếu có): {dn.ma_so_dn` |
| PLI_M49 | 9 | `……….(Tên doanh nghiệp)…………..` |

- Đặc biệt **PLI_M70 vs PLI_M71**: M70 (bản nộp trực tiếp) có bảng ký 2 ô `NGƯỜI NỘP (Ký và ghi họ tên) | NGƯỜI NHẬN (Ký và ghi họ tên)` — section_spec `chu_ky_nguoi_nop_nguoi_nhan`; M71 (qua mạng điện tử) chỉ có bảng 1 ô `(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)` — section_spec `chu_ky_co_quan_cap_tinh`. Bảng ký cơ quan thuộc **M71**, không phải M70; đúng theo `tools/form_specs/publication/PLI_M71.json`.

## 4. 9 FORM KHÔNG CÓ CỤM KÝ — verdict

| Form | Nguồn gốc (find_source) | Nguồn có chỉ thị ký | Template có chỉ thị ký | Verdict |
|---|---|---|---|---|
| PLII_M18 | `06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_18_giay_tiep_nhan_ho_so_va_hen_tra_ket_qua_ho_so_dang_ky_ho_kinh_doanh_qua_mang_thong_tin_dien_tu.docx` | False | False | **absence-correct** |
| PLI_M05 | `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_05_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_hop_danh.docx` | False | False | **absence-correct** |
| PLI_M07 | `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_07_danh_sach_co_dong_sang_lap_cong_ty_co_phan.docx` | False | False | **absence-correct (nguồn-stub)** |
| PLI_M10 | `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_10_danh_sach_chu_so_huu_huong_loi_cua_doanh_nghiep.docx` | False | False | **absence-correct** |
| PLI_M71 | `03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_71_giay_tiep_nhan_ho_so_va_hen_tra_ket_qua_ho_so_dang_ky_doanh_nghiep_chi_nhanh_van_phong_dai_dien.docx` | False | False | **absence-correct** |
| PLI_M72 | `05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_cong_bo_noi_dung_dang_ky_thanh_lap_doanh_nghiep.docx` | False | False | **absence-correct** |
| PLI_M73 | `05_cong_bo_cung_cap_thong_tin/PL1_Mau_73_cong_bo_thay_doi_noi_dung_dang_ky_doanh_nghiep.docx` | False | False | **absence-correct** |
| PLI_M74 | `05_cong_bo_cung_cap_thong_tin/PL1_Mau_74_cong_bo_noi_dung_dang_ky_doanh_nghiep.docx` | False | False | **absence-correct** |
| PLI_M76 | `05_cong_bo_cung_cap_thong_tin/PL1_Mau_76_thong_bao_ve_viec_cap_dang_ky_doanh_nghiep.docx` | False | False | **absence-correct** |

*("có chỉ thị ký" = chỉ đếm cụm chỉ thị ký thật: "Ký và ghi rõ họ tên", "Ký, ghi họ tên và đóng dấu", "Ký tên", "Đã ký", "Người khai", "Người nộp", "Ngày...ký". Các phrase "Người đại diện"/"Chủ hộ" chỉ khớp NHÃN TRƯỜNG DỮ LIỆU/tiêu đề mục ở M05/M10/M72 — không phải khối ký; chi tiết ở từng form bên dưới. JSON giữ cả hai cờ: `source_has_signature` = khớp thô theo danh sách phrase nhiệm vụ, `source_has_signature_directive` = chỉ thị ký thật.)*

**RED FLAG `template-lost-signature`: không có.** Chi tiết từng form + bằng chứng:

### PLII_M18 — absence-correct

- Nguồn: `06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_18_giay_tiep_nhan_ho_so_va_hen_tra_ket_qua_ho_so_dang_ky_ho_kinh_doanh_qua_mang_thong_tin_dien_tu.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Giấy tiếp nhận hồ sơ & hẹn trả kết quả (qua mạng) do CQĐKKD cấp xã phát hành; khối cuối nguồn là ô ký cơ quan '(Cơ quan đăng ký kinh doanh cấp xã) ………' KHÔNG kèm chỉ thị 'Ký...'; không có ô ký người nộp trong nguồn. Template khớp nguồn.
- 3 dòng cuối nguồn (bằng chứng):

  > (Cơ quan đăng ký kinh doanh cấp xã) …………………
  > _______________________________________
  > 1 Trường hợp hồ sơ được tiếp nhận trên Hệ thống thông tin về đăng ký hộ kinh doanh sau giờ hành chính hoặc vào ngày nghỉ, ngày lễ, Tết theo quy định thì thời hạn trả kết quả theo quy định được tính từ

### PLI_M05 — absence-correct

- Nguồn: `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_05_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_hop_danh.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: True | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Giấy đề nghị đăng ký DN - công ty hợp danh (form người dùng). Các hit 'người đại diện'/'chủ hộ' là NHÃN TRƯỜNG DỮ LIỆU ('Tên người đại diện cơ sở bảo trợ...','Tên chủ hộ kinh doanh: ……') tồn tại y hệt ở template — không phải cụm ký. Cả nguồn và template kết thúc ở bảng vốn; so sánh với bản phát hành chính thức của Mẫu 05 nằm ngoài phạm vi repo (needs-owner-light).
- 3 dòng cuối nguồn (bằng chứng):

  > Vốn nước ngoài
  > Vốn khác
  > Tổng cộng

### PLI_M07 — absence-correct (nguồn-stub)

- Nguồn: `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_07_danh_sach_co_dong_sang_lap_cong_ty_co_phan.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: NGUỒN LÀ STUB: chỉ 2 dòng (caption + 'Mẫu số 7'), không có bảng. Template tự dựng bảng danh sách (có cột 'Chữ ký' {chu_ky}) — chiều NGƯỢC lại (template có thêm, không mất cụm ký từ nguồn). Không phải template-lost-signature; cảnh báo nguồn-stub cho regen.
- 3 dòng cuối nguồn (bằng chứng):

  > PL1 - Mau so 7: Danh sách cổ đông sáng lập công ty cổ phần
  > Mẫu số 7

### PLI_M10 — absence-correct

- Nguồn: `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_10_danh_sach_chu_so_huu_huong_loi_cua_doanh_nghiep.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: True | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Danh sách CSHHL. Hit 'người đại diện...ký trực tiếp' là CHÚ THÍCH mồ côi (footnote 15) tồn tại ở CẢ nguồn và template — không có khối ký thật.
- 3 dòng cuối nguồn (bằng chứng):

  > Mẫu số 10
  > 15 - Người đại diện theo pháp luật của doanh nghiệp ký trực tiếp vào phần này.
  > - Trường hợp đăng ký chuyển đổi loại hình doanh nghiệp đồng thời đăng ký thay đổi người đại diện theo pháp luật thì Chủ tịch công ty/Chủ tịch Hội đồng thành viên của công ty sau chuyển đổi ký trực tiế

### PLI_M71 — absence-correct

- Nguồn: `03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_71_giay_tiep_nhan_ho_so_va_hen_tra_ket_qua_ho_so_dang_ky_doanh_nghiep_chi_nhanh_van_phong_dai_dien.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Giấy tiếp nhận hồ sơ (qua mạng). 2 bản alias nguồn (03_ và 05_) IDENTICAL (sha256 d95a68360db3). Khối cuối = bảng 1 ô '(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)' — section_spec chu_ky_co_quan_cap_tinh thuộc M71 (form_maps section_specs), CHỈ có ô ký cơ quan, KHÔNG ô ký người nộp — đúng theo W1 spec tools/form_specs/publication/PLI_M71.json (khác M70).
- 3 dòng cuối nguồn (bằng chứng):

  > DOANH CẤP TỈNH)
  > _______________________________________
  > Trường hợp hồ sơ được tiếp nhận trên Hệ thống thông tin quốc gia về đăng ký doanh nghiệp sau giờ hành chính hoặc vào ngày nghỉ, ngày lễ, Tết theo quy định thì thời hạn trả kết quả theo quy định được t

### PLI_M72 — absence-correct

- Nguồn: `05_cong_bo_cung_cap_thong_tin/PL1_Mau_72_cong_bo_noi_dung_dang_ky_thanh_lap_doanh_nghiep.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: True | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Công bố nội dung đăng ký thành lập — form TỔNG HỢP 5 BIẾN THỂ (DNTN; TNHH 1TV; TNHH 2TV+; CTy CP; hợp danh — 5 khối 'Nơi đăng ký' ở cả nguồn lẫn template). Đã kiểm TẤT CẢ 5 biến thể: không biến thể nào có chỉ thị ký; nguồn và template khớp nhau. Hit 'người đại diện' là tiêu đề mục 8 của nội dung công bố.
- 3 dòng cuối nguồn (bằng chứng):

  > Ghi tên của tất cả người đại diện theo pháp luật trong trường hợp công ty có nhiều hơn 01 người đại diện theo pháp luật.
  > 2 Ghi tên của tất cả người đại diện theo pháp luật trong trường hợp công ty có nhiều hơn 01 người đại diện theo pháp luật.
  > 3 Ghi tên của tất cả người đại diện theo pháp luật trong trường hợp công ty có nhiều hơn 01 người đại diện theo pháp luật.

### PLI_M73 — absence-correct

- Nguồn: `05_cong_bo_cung_cap_thong_tin/PL1_Mau_73_cong_bo_thay_doi_noi_dung_dang_ky_doanh_nghiep.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Công bố thay đổi nội dung đăng ký. Không có cụm ký ở nguồn lẫn template; khối cuối là mục 5 'Nơi đăng ký: (Cơ quan đăng ký kinh doanh cấp tỉnh)....'
- 3 dòng cuối nguồn (bằng chứng):

  > ……………………………………………………………………………..........................
  > 4. Ngày cấp đăng ký thay đổi: …………………………………………………................
  > 5. Nơi đăng ký: (Cơ quan đăng ký kinh doanh cấp tỉnh) ............................................

### PLI_M74 — absence-correct

- Nguồn: `05_cong_bo_cung_cap_thong_tin/PL1_Mau_74_cong_bo_noi_dung_dang_ky_doanh_nghiep.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: Công bố nội dung đăng ký (khác 72/73). Không có cụm ký ở nguồn lẫn template; khối cuối là mục 6 'Nội dung thông báo:' + fill-line.
- 3 dòng cuối nguồn (bằng chứng):

  > 6. Nội dung thông báo:
  > ……………………………………………………………………………………………...................
  > …………………………………………………………………………..........................................

### PLI_M76 — absence-correct

- Nguồn: `05_cong_bo_cung_cap_thong_tin/PL1_Mau_76_thong_bao_ve_viec_cap_dang_ky_doanh_nghiep.docx`
- Nguồn khớp phrase danh sách nhiệm vụ: False | Chỉ thị ký THẬT ở nguồn: False | Template có chỉ thị ký: False
- Tính chất: THÔNG BÁO chấp thuận hồ sơ đăng ký qua mạng do CQĐKKD cấp tỉnh phát hành (output điện tử, không dành cho ký của người khai). Không có cụm ký ở nguồn lẫn template.
- 3 dòng cuối nguồn (bằng chứng):

  > Thông tin đăng ký doanh nghiệp của doanh nghiệp sẽ được cập nhật trong Cơ sở dữ liệu quốc gia về đăng ký doanh nghiệp/đăng tải trên Cổng thông tin quốc gia về đăng ký doanh nghiệp.
  > Trường hợp Cơ quan đăng ký kinh doanh cấp tỉnh trả kết quả là giấy chứng nhận/giấy xác nhận/thông báo cho doanh nghiệp thì ghi:
  > Đề nghị Ông/Bà liên hệ (Cơ quan đăng ký kinh doanh cấp tỉnh) để nhận kết quả.

### Ghi chú bổ sung cụm ký
- **PLI_M70/M71**: `chu_ky_co_quan_cap_tinh` nằm trong `app/data/form_maps.json` → `section_specs` của **PLI_M71** (không phải M70); M70 dùng `chu_ky_nguoi_nop_nguoi_nhan`. Cả hai là output-table render lúc runtime, không phải cụm ký bị mất trong docx.
- **PLI_M72**: kiểm đủ 5 biến thể (DNTN, TNHH 1TV, TNHH 2TV+; CTCP, hợp danh — 5 khối "Nơi đăng ký" ở cả nguồn lẫn template): không biến thể nào có chỉ thị ký. Nguồn ↔ template khớp.
- **PLI_M07**: nguồn gốc là **stub 2 dòng** (caption + "Mẫu số 7"); template tự dựng bảng + cột `Chữ ký {chu_ky}` — chiều ngược (template CÓ thêm phần ký so với nguồn, không phải mất). Cảnh báo cho Lead regen: nguồn M07 không đủ để tái sinh template.
- **PLI_M10**: cụm "Người đại diện theo pháp luật ... ký trực tiếp" là chú thích mồ côi (footnote 15) tồn tại ở CẢ nguồn và template — không phải khối ký.
- **PLI_M05**: các hit "người đại diện"/"chủ hộ" là nhãn trường dữ liệu, có y hệt ở template.

## 5. Danh sách 65 form không có band tên (`no_band = true`)

`PLII_M01` `PLII_M07` `PLII_M08` `PLII_M09` `PLII_M10` `PLII_M11` `PLII_M12` `PLII_M13` `PLII_M14` `PLII_M15` `PLII_M16` `PLII_M17` `PLII_M18` `PLII_M19` `PLII_M20` `PLII_M21` `PLII_M22` `PLII_M23` `PLII_M24` `PLII_M25` `PLII_M26` `PLII_M27` `PLII_M28` `PLI_M01` `PLI_M02` `PLI_M03` `PLI_M04` `PLI_M05` `PLI_M06` `PLI_M07` `PLI_M08` `PLI_M09` `PLI_M10` `PLI_M11` `PLI_M12` `PLI_M42` `PLI_M43` `PLI_M45` `PLI_M46` `PLI_M47` `PLI_M48` `PLI_M49` `PLI_M50` `PLI_M51` `PLI_M52` `PLI_M53` `PLI_M54` `PLI_M55` `PLI_M56` `PLI_M57` `PLI_M63` `PLI_M66` `PLI_M67` `PLI_M68` `PLI_M69` `PLI_M70` `PLI_M71` `PLI_M72` `PLI_M73` `PLI_M74` `PLI_M75` `PLI_M76` `PLI_M78` `PLI_M79` `PLI_M80`

---
Sinh tự động bởi Lane C (read-only); dữ liệu thô: `/tmp/header_name_census.json`; script: `/tmp/census_work/`.