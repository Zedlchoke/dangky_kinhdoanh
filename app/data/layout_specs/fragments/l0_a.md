# L0-A Layout Census Fragment — PLI_M01..PLI_M12

- Agent: L0-A. Worktree: `dangky_kinhdoanh-worktrees/l0-a-pli-early`, branch `l0/a-pli-early` @ `0ee70d3`.
- Pham vi: dung 12 mau PLI_M01-PLI_M12. READ-ONLY production; chi tao moi 2 file fragment nay (`l0_a.md`, `l0_a_evidence.json`).
- Nguon kiem tra: `app/data/blocks/PLI_Mxx.json`; `app/templates/PLI_Mxx.docx` (giai nen OOXML bang zipfile+ElementTree); nguon import goc `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_01..11.docx` va `02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_12_tach_tu_file_full.docx`; wrapper `app_web/ui/index.html`, `app_web/ui/app.js`, `app_web/ui/render.js`, `app_web/main.py`. Khong sua file nao trong cac nguon nay.
- Data tho machine-readable: `app/data/layout_specs/fragments/l0_a_evidence.json` (cung muc noi dung, co day du context).

## SUMMARY COUNTS

| Metric | Value |
|---|---|
| forms_scanned | **12/12** |
| forms_co_source_indicator_trong_blocks | 11/12 (M01, M02, M03, M04, M05, M06, M07, M08, M09, M10, M11); PLI_M12 khong co marker o block hay template hay nguon |
| tong_block_source_indicator | 11 (luon block dau tien, align=left) |
| marker_leak_qua_wrapper/title/caption | 0/12 - title tab = `ten_mau` sach (chi tiet o muc Wrapper audit) |
| dong_form_number_hop_le ('Mau so N') | 15: 11 dong dau (block idx 1, M01-M11) + 4 heading phu nhung trong PLI_M09 |
| forms_co_newline-collapse risk | 10/12 (tru PLI_M07, PLI_M10); tong 29 block 'p' chua \n trong run text |
| forms_co_quoc_hieu_3_dong_1_run (collapse) | 6 (M01, M02, M03, M04, M05, M12) |
| candidate_digit_glued (regex letter+digit) | 73 occurrence: 11 marker-self, 55 footnote-khop-OOXML, 0 footnote-chua-xac-minh, 7 legit-digit |
| forms_co_superscript_OOXML (w:vertAlign=superscript) | 11/12 (thieu M07); tong 186 paragraph co sup-run; khong form nao dung w:footnoteReference (footnotes.xml KHONG ton tai) |
| hard break OOXML | tong w:br = 59 (w:cr = 0); blocks quyet thanh '\n' trong 1 run -> HTML collapse |
| tab | w:tab trong template = 38; blocks giu literal \t trong 37 block text -> HTML collapse thanh 1 space |
| indent (w:ind) | 0 tren ca 12 template - khong ton khoan indent mat du lieu trong pham vi nay |
| spacing | chi before/after=120tw (=6pt); khong line-spacing/keep-with-next; blocks khong giu bat ky gia tri spacing nao |
| UI screenshot trang dau | NOT RUN - thieu browser backend (moi truong khong co automation; KHONG cai dependency moi theo de bai) |

## Wrapper audit (title/caption do app sinh - khong lo marker)

- `app_web/ui/index.html:5` - `<title>Trợ lý hồ sơ ĐKKD</title>` tinh, khong marker.
- `app_web/ui/app.js:668-675` `updateDocTitle()` - `#doc-title` = `case.ten · doc.ten_mau || id`; `ten_mau` trong blocks JSON la ten sach (vd "Giấy đề nghị đăng ký doanh nghiệp - Doanh nghiệp tư nhân"), khong chua 'PL1 - Mau so'.
- `app_web/ui/app.js:692-695` `shortName()` cat 34 ky tu cho tab list - van tu `ten_mau`.
- `app_web/ui/render.js:536` nut form list = `escapeHtml(d.ten_mau || d.id)` - sach.
- `app_web/main.py:106,128` chi dialog title tinh. Khong thay window.title dong.
- Ket luan: marker KY THUAT chi ton tai trong blocks (block 0), khong qua wrapper. Voi 11/12 mau; PLI_M12 khong co marker ca hai noi.

---

## PLI_M01 — Giấy đề nghị đăng ký doanh nghiệp - Doanh nghiệp tư nhân

blocks=170 · template paras=240 · w:br=5 · w:tab=4 · sup-paras=14 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M01 | source-indicator | block 0 (p) | `PL1 - Mau so 1: Giấy đề nghị đăng ký doanh nghiệp - Doanh nghiệp tư nhân` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M01 | form-number (dong dau) | block 1 | `Mẫu số 1` align=left | form-number | KEEP-HIEN-THI |
| PLI_M01 | national-header/motto/separator | block 2 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M01 | hard-break-collapse | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nDOANH NGHIỆP TƯ NHÂN` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M01 | hard-break-collapse | block 83 | `Giá trị vốn của từng tài sản trong vốn đầu tư\n(bằng số, VNĐ)` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M01 | hard-break-collapse | block 158 | `CHỦ DOANH NGHIỆP TƯ NHÂN\n(Ký và ghi họ tên)7` align=center (\n x1) | signature | OPEN-L2-br |
| PLI_M01 | candidate-footnote | block 6 (p/runs) | 'Tôi là1 (ghi họ tên bằ' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | candidate-footnote | block 27 (chk/label) | 'ội/quỹ xã hội/quỹ từ thiện2' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | candidate-footnote | block 123 (p/runs) | 'Ngày bắt đầu hoạt động3 (trường hợp do' truoc digit `3` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | candidate-footnote | block 140 (p/runs) | 'Phương pháp tính thuế GTGT5:' truoc digit `5` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | candidate-footnote | block 145 (p/runs) | ' việc đóng bảo hiểm xã hội6:' truoc digit `6` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | tab-loss | block 6 | `Tôi là1 (ghi họ tên bằng chữ in hoa): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M01 | tab-loss | block 9 | `Số định danh cá nhân: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M01 | tab-loss | block 18 | `Ngày cấp:  Nơi cấp:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M01 | tab-loss | block 34 | `Tên chủ hộ kinh doanh: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M01 | date-line | tpl para / block 3 | `{dia_diem_ky}, ngày {ngay_ky_vb}tháng {thang_ky_vb} năm {nam_ky_vb}` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M01 | salutation | tpl para / block 5 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M01 | form-title | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nDOANH NGHIỆP TƯ NHÂN` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M01 | signature | tpl para | `CHỦ DOANH NGHIỆP TƯ NHÂN(Ký và ghi họ tên)7` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M01 | superscript-OOXML | 14 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M01 | src-vs-template | - | nguon=DN_PL1_Mau_01_giay_de_nghi_dang_ky_doanh_nghiep_doanh_nghiep_tu_nhan.docx paras=219 vs template=240 | - | INFO |

---

## PLI_M02 — Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn một thành viên

blocks=270 · template paras=358 · w:br=6 · w:tab=8 · sup-paras=26 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M02 | source-indicator | block 0 (p) | `PL1 - Mau so 2: Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn một thành viên` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M02 | form-number (dong dau) | block 1 | `Mẫu số 2` align=left | form-number | KEEP-HIEN-THI |
| PLI_M02 | national-header/motto/separator | block 2 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M02 | hard-break-collapse | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY TRÁCH NHIỆM HỮU HẠN MỘT THÀNH VIÊN` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M02 | hard-break-collapse | block 253 | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG \nTHÀNH VIÊN CỦA CÔNG TY\n(Ký và ghi họ tên)15` align=center (\n x3) | signature | OPEN-L2-br |
| PLI_M02 | candidate-footnote | block 6 (p/runs) | 'Tôi là1 (ghi họ tên bằ' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 25 (p/runs) | 'ủ tịch Hội đồng thành viên2 với các nội du' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 33 (chk/label) | 'ội/quỹ xã hội/quỹ từ thiện3' truoc digit `3` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 85 (p/runs) | 'ng đến quốc phòng, an ninh4: Có  Không ' truoc digit `4` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 126 (p/runs) | 'iấy tờ pháp lý của cá nhân5Quốc tịchDân tộ' truoc digit `5` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-legit-digit | block 126 (p/runs) | 'hời điểm đại diện phần vốn12345678910111213- Thông tin về ' truoc digit `12345678910111213` - chuoi so dai (cot so / lien tiep) | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M02 | candidate-footnote | block 168 (p/runs) | 'ời đại diện theo pháp luật9: ' truoc digit `9` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 214 (p/runs) | 'Ngày bắt đầu hoạt động10 (trường hợp do' truoc digit `10` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 236 (p/runs) | ' việc đóng bảo hiểm xã hội13:' truoc digit `13` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | candidate-footnote | block 244 (p/runs) | 'hưởng lợi của doanh nghiệp14:' truoc digit `14` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | tab-loss | block 79 | `Thư điện tử (nếu có):  Website (nếu có): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M02 | tab-loss | block 112 | `Ngày cấp:  Cơ quan cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M02 | tab-loss | block 115 | `Tên tổ chức (ghi bằng chữ in hoa): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M02 | tab-loss | block 117 | `Ngày cấp:  Nơi cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M02 | tab-loss | blocks 123, 128, 137, 183 | (cung pattern) | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M02 | date-line | tpl para / block 3 | `{dia_diem_ky}, ngày {ngay_ky_vb}tháng {thang_ky_vb} năm {nam_ky_vb}` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M02 | salutation | tpl para / block 5 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M02 | form-title | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY TRÁCH NHIỆM HỮU HẠN MỘT THÀNH VIÊN` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M02 | signature | tpl para | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA ` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M02 | superscript-OOXML | 26 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M02 | src-vs-template | - | nguon=DN_PL1_Mau_02_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_mot_thanh_vien.docx paras=331 vs template=358 | - | INFO |

---

## PLI_M03 — Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn hai thành viên trở lên

blocks=102 · template paras=151 · w:br=3 · w:tab=5 · sup-paras=4 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M03 | source-indicator | block 0 (p) | `PL1 - Mau so 3: Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn hai thành viên trở lên` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M03 | form-number (dong dau) | block 1 | `Mẫu số 3` align=left | form-number | KEEP-HIEN-THI |
| PLI_M03 | national-header/motto/separator | block 2 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M03 | hard-break-collapse | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M03 | candidate-footnote | block 6 (p/runs) | 'Tôi là1 (ghi họ tên bằ' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M03 | candidate-footnote | block 25 (p/runs) | 'ủ tịch Hội đồng thành viên2 với nội dung s' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M03 | candidate-footnote | block 33 (chk/label) | 'ội/quỹ xã hội/quỹ từ thiện3' truoc digit `3` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M03 | candidate-footnote | block 85 (p/runs) | 'ng đến quốc phòng, an ninh4: Có  Không ' truoc digit `4` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M03 | tab-loss | block 19 | `Ngày cấp:  Nơi cấp:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M03 | tab-loss | block 42 | `Ngày cấp:  Nơi cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M03 | tab-loss | block 45 | `Tên chủ hộ kinh doanh: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M03 | tab-loss | block 79 | `Thư điện tử (nếu có):  Website (nếu có): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M03 | tab-loss | blocks 91 | (cung pattern) | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M03 | date-line | tpl para / block 3 | `{dia_diem_ky}, ngày {ngay_ky_vb}tháng {thang_ky_vb} năm {nam_ky_vb}` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M03 | salutation | tpl para / block 5 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M03 | form-title | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M03 | superscript-OOXML | 4 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M03 | src-vs-template | - | nguon=DN_PL1_Mau_03_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx paras=130 vs template=151 | - | INFO |

---

## PLI_M04 — Giấy đề nghị đăng ký doanh nghiệp - Công ty cổ phần

blocks=135 · template paras=208 · w:br=4 · w:tab=5 · sup-paras=4 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M04 | source-indicator | block 0 (p) | `PL1 - Mau so 4: Giấy đề nghị đăng ký doanh nghiệp - Công ty cổ phần` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M04 | form-number (dong dau) | block 1 | `Mẫu số 4` align=left | form-number | KEEP-HIEN-THI |
| PLI_M04 | national-header/motto/separator | block 2 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M04 | hard-break-collapse | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY CỔ PHẦN` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M04 | hard-break-collapse | block 85 | `- Doanh nghiệp có Giấy chứng nhận quyền sử dụng đất tại đảo và xã, phường biên giới; xã, phường ven biển; khu vực khác c` align=left (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M04 | candidate-footnote | block 6 (p/runs) | 'Tôi là1 (ghi họ tên bằ' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M04 | candidate-footnote | block 25 (p/runs) | 'n trị với các nội dung sau2:' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M04 | candidate-footnote | block 33 (chk/label) | 'ội/quỹ xã hội/quỹ từ thiện3' truoc digit `3` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M04 | candidate-footnote | block 85 (p/runs) | 'ng đến quốc phòng, an ninh4:\nCó  Không ' truoc digit `4` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M04 | tab-loss | block 19 | `Ngày cấp:  Nơi cấp:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M04 | tab-loss | block 58 | `Tên người đại diện cơ sở bảo trợ xã hội/quỹ xã hội/quỹ từ thiện: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M04 | tab-loss | block 79 | `Thư điện tử (nếu có):  Website (nếu có): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M04 | tab-loss | block 91 | `Giá trị tương đương theo đơn vị tiền nước ngoài (nếu có, bằng số, loại` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M04 | tab-loss | blocks 103 | (cung pattern) | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M04 | date-line | tpl para / block 3 | `{dia_diem_ky}, ngày {ngay_ky_vb}tháng {thang_ky_vb} năm {nam_ky_vb}` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M04 | salutation | tpl para / block 5 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M04 | form-title | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY CỔ PHẦN` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M04 | superscript-OOXML | 4 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M04 | src-vs-template | - | nguon=DN_PL1_Mau_04_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_co_phan.docx paras=187 vs template=208 | - | INFO |

---

## PLI_M05 — Giấy đề nghị đăng ký doanh nghiệp - Công ty hợp danh

blocks=81 · template paras=128 · w:br=4 · w:tab=7 · sup-paras=3 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M05 | source-indicator | block 0 (p) | `PL1 - Mau so 5: Giấy đề nghị đăng ký doanh nghiệp - Công ty hợp danh` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M05 | form-number (dong dau) | block 1 | `Mẫu số 5` align=left | form-number | KEEP-HIEN-THI |
| PLI_M05 | national-header/motto/separator | block 2 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M05 | hard-break-collapse | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY HỢP DANH` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M05 | hard-break-collapse | block 64 | `- Doanh nghiệp có Giấy chứng nhận quyền sử dụng đất tại đảo và xã, phường biên giới; xã, phường ven biển; khu vực khác c` align=left (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M05 | candidate-footnote | block 6 (p/runs) | 'Chúng tôi1 là các thành v' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M05 | candidate-footnote | block 13 (chk/label) | 'ội/quỹ xã hội/quỹ từ thiện2' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M05 | candidate-footnote | block 64 (p/runs) | 'ng đến quốc phòng, an ninh3:\nCó  Không ' truoc digit `3` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M05 | tab-loss | block 25 | `Tên chủ hộ kinh doanh: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M05 | tab-loss | block 26 | `Loại giấy tờ pháp lý của cá nhân (kê khai theo giấy tờ pháp lý của cá ` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M05 | tab-loss | block 31 | `Số giấy tờ pháp lý của cá nhân (kê khai theo giấy tờ pháp lý của cá nh` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M05 | tab-loss | block 57 | `Điện thoại:  Số fax (nếu có): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M05 | tab-loss | blocks 58, 68 | (cung pattern) | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M05 | date-line | tpl para / block 3 | `{dia_diem_ky}, ngày … tháng … năm {ngay_ky_vb}` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M05 | salutation | tpl para / block 5 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M05 | form-title | block 4 | `GIẤY ĐỀ NGHỊ ĐĂNG KÝ DOANH NGHIỆP\nCÔNG TY HỢP DANH` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M05 | superscript-OOXML | 3 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M05 | src-vs-template | - | nguon=DN_PL1_Mau_05_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_hop_danh.docx paras=107 vs template=128 | - | INFO |

---

## PLI_M06 — Danh sách thành viên công ty trách nhiệm hữu hạn hai thành viên trở lên

blocks=107 · template paras=202 · w:br=2 · w:tab=2 · sup-paras=18 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M06 | source-indicator | block 0 (p) | `PL1 - Mau so 6: Danh sách thành viên công ty trách nhiệm hữu hạn hai thành viên trở lên` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M06 | form-number (dong dau) | block 1 | `Mẫu số 6` align=left | form-number | KEEP-HIEN-THI |
| PLI_M06 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M06 | hard-break-collapse | block 91 | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký và ghi họ tên)11` align=center (\n x2) | signature | OPEN-L2-br |
| PLI_M06 | candidate-footnote | block 6 (p/runs) | 'ời đại diện theo pháp luật5:' truoc digit `5` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M06 | candidate-footnote | block 52 (p/runs) | 'Ngày bắt đầu hoạt động6 (trường hợp do' truoc digit `6` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M06 | candidate-footnote | block 74 (p/runs) | ' việc đóng bảo hiểm xã hội9:' truoc digit `9` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M06 | candidate-footnote | block 82 (p/runs) | 'hưởng lợi của doanh nghiệp10:' truoc digit `10` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M06 | tab-loss | block 5 | `Ngày cấp:  Cơ quan cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M06 | tab-loss | block 21 | `Ngày cấp:  Nơi cấp:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M06 | signature | tpl para | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY(Ký và ghi` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M06 | superscript-OOXML | 18 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M06 | src-vs-template | - | nguon=DN_PL1_Mau_06_danh_sach_thanh_vien_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx paras=129 vs template=202 | - | INFO |

---

## PLI_M07 — Danh sách cổ đông sáng lập công ty cổ phần

blocks=3 · template paras=69 · w:br=0 · w:tab=0 · sup-paras=0 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M07 | source-indicator | block 0 (p) | `PL1 - Mau so 7: Danh sách cổ đông sáng lập công ty cổ phần` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M07 | form-number (dong dau) | block 1 | `Mẫu số 7` align=left | form-number | KEEP-HIEN-THI |
| PLI_M07 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M07 | src-vs-template | - | nguon=DN_PL1_Mau_07_danh_sach_co_dong_sang_lap_cong_ty_co_phan.docx paras=2 vs template=69; file nguon tach ra gan nhu trong (2 doan); noi dung that nam trong _Bieu_mau_PL_I_II_full.docx | - | INFO |

---

## PLI_M08 — Danh sách cổ đông là nhà đầu tư nước ngoài

blocks=107 · template paras=176 · w:br=2 · w:tab=3 · sup-paras=18 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M08 | source-indicator | block 0 (p) | `PL1 - Mau so 8: Danh sách cổ đông là nhà đầu tư nước ngoài` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M08 | form-number (dong dau) | block 1 | `Mẫu số 8` align=left | form-number | KEEP-HIEN-THI |
| PLI_M08 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M08 | hard-break-collapse | block 91 | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY\n(Ký và ghi họ tên)11` align=center (\n x2) | signature | OPEN-L2-br |
| PLI_M08 | candidate-footnote | block 6 (p/runs) | 'ời đại diện theo pháp luật5:' truoc digit `5` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M08 | candidate-footnote | block 52 (p/runs) | 'Ngày bắt đầu hoạt động6 (trường hợp do' truoc digit `6` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M08 | candidate-footnote | block 74 (p/runs) | ' việc đóng bảo hiểm xã hội9:' truoc digit `9` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M08 | candidate-footnote | block 82 (p/runs) | 'hưởng lợi của doanh nghiệp10:' truoc digit `10` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M08 | tab-loss | block 5 | `Ngày cấp:  Cơ quan cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M08 | tab-loss | block 19 | `Dân tộc:  Quốc tịch:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M08 | tab-loss | block 21 | `Ngày cấp:  Nơi cấp:  \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M08 | signature | tpl para | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY(Ký và ghi h` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M08 | superscript-OOXML | 18 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M08 | src-vs-template | - | nguon=DN_PL1_Mau_08_danh_sach_co_dong_la_nha_dau_tu_nuoc_ngoai.docx paras=127 vs template=176 | - | INFO |

---

## PLI_M09 — Danh sách thành viên công ty hợp danh

blocks=193 · template paras=294 · w:br=12 · w:tab=1 · sup-paras=71 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M09 | source-indicator | block 0 (p) | `PL1 - Mau so 9: Danh sách thành viên công ty hợp danh` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M09 | form-number (dong dau) | block 1 | `Mẫu số 9` align=left | form-number | KEEP-HIEN-THI |
| PLI_M09 | form-number (heading con, tham chieu mau khac) | block 108 | `Mẫu số 7` align=right | form-number | KEEP-HIEN-THI |
| PLI_M09 | form-number (heading con, tham chieu mau khac) | block 128 | `Mẫu số 8` align=right | form-number | KEEP-HIEN-THI |
| PLI_M09 | form-number (heading con, tham chieu mau khac) | block 149 | `Mẫu số 9` align=right | form-number | KEEP-HIEN-THI |
| PLI_M09 | form-number (heading con, tham chieu mau khac) | block 178 | `Mẫu số 10` align=right | form-number | KEEP-HIEN-THI |
| PLI_M09 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M09 | hard-break-collapse | block 70 | `CÁC THÀNH VIÊN HỢP DANH\n(Ký và ghi họ tên từng thành viên)9` align=center (\n x1) | signature | OPEN-L2-br |
| PLI_M09 | hard-break-collapse | block 89 | `, ngàythángnăm\nNGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN CỦA CÔNG TY\n(Ký và ghi họ tên)13` align=center (\n x2) | signature | OPEN-L2-br |
| PLI_M09 | hard-break-collapse | block 112 | `, ngàythángnăm\nNGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY\n(Ký và ghi họ tên)13` align=center (\n x2) | signature | OPEN-L2-br |
| PLI_M09 | hard-break-collapse | block 133 | `, ngàythángnăm\nNGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY\n(Ký và ghi họ tên)13` align=center (\n x2) | signature | OPEN-L2-br |
| PLI_M09 | hard-break-collapse | block 180 | `, ngàythángnăm\nNGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN/\nCHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY\n(Ký v` align=center (\n x4) | signature | OPEN-L2-br |
| PLI_M09 | candidate-footnote | block 31 (p/runs) | 'Ngày bắt đầu hoạt động4 (trường hợp do' truoc digit `4` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-footnote | block 53 (p/runs) | ' việc đóng bảo hiểm xã hội7:' truoc digit `7` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-footnote | block 61 (p/runs) | 'hưởng lợi của doanh nghiệp8:' truoc digit `8` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-footnote | block 88 (p/runs) | 'ínhVốn gópThời hạn góp vốn8Ghi chú (nếu có' truoc digit `8` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-legit-digit | block 88 (p/runs) | 'g, giá trị tài sản góp vốn71234567892. Thông tin ngư' truoc digit `71234567892` - chuoi so dai (cot so / lien tiep) | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M09 | candidate-footnote | block 132 (p/runs) | 'pháp lý tương đươngVốn góp6Thời hạn góp vố' truoc digit `6` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-legit-digit | block 132 (p/runs) | 'ượngGiá trịSố lượngGiá trị1279101112131415161718202. Thông tin ngư' truoc digit `1279101112131415161718202` - chuoi so dai (cot so / lien tiep) | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M09 | candidate-footnote | block 161 (p/runs) | 'Thời hạn góp vốn8' truoc digit `8` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-footnote | block 163 (p/runs) | 'Phần vốn góp6 (bằng số; VNĐ ' truoc digit `6` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | candidate-legit-digit | block 163 (p/runs) | 'g, giá trị tài sản góp vốn71234567892. Thông tin ngư' truoc digit `71234567892` - chuoi so dai (cot so / lien tiep) | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M09 | tab-loss | block 5 | `Ngày cấp:  Cơ quan cấp: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M09 | date-line | tpl para / gom chung block signature 70 | `{dia_diem_ky}, ngày{ngay_ky_vb}tháng{thang_ky_vb}năm{nam_ky_vb}NGƯỜI ĐẠI DIỆN TH` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M09 | signature | tpl para | `CÁC THÀNH VIÊN HỢP DANH(Ký và ghi họ tên từng thành viên)9` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M09 | superscript-OOXML | 71 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M09 | src-vs-template | - | nguon=DN_PL1_Mau_09_danh_sach_thanh_vien_cong_ty_hop_danh.docx paras=232 vs template=294 | - | INFO |

---

## PLI_M10 — Danh sách chủ sở hữu hưởng lợi của doanh nghiệp

blocks=5 · template paras=72 · w:br=0 · w:tab=0 · sup-paras=1 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M10 | source-indicator | block 0 (p) | `PL1 - Mau so 10: Danh sách chủ sở hữu hưởng lợi của doanh nghiệp` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M10 | form-number (dong dau) | block 1 | `Mẫu số 10` align=left | form-number | KEEP-HIEN-THI |
| PLI_M10 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M10 | superscript-OOXML | 1 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M10 | src-vs-template | - | nguon=DN_PL1_Mau_10_danh_sach_chu_so_huu_huong_loi_cua_doanh_nghiep.docx paras=5 vs template=72; file nguon tach ra gan nhu trong (5 doan); noi dung that nam trong _Bieu_mau_PL_I_II_full.docx | - | INFO |

---

## PLI_M11 — Kê khai thông tin để xác định chủ sở hữu hưởng lợi của doanh nghiệp

blocks=10 · template paras=59 · w:br=3 · w:tab=0 · sup-paras=3 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M11 | source-indicator | block 0 (p) | `PL1 - Mau so 11: Kê khai thông tin để xác định chủ sở hữu hưởng lợi của doanh nghiệp` align=left | source-indicator (uiHidden=true) | OPEN-L2-hide |
| PLI_M11 | form-number (dong dau) | block 1 | `Mẫu số 11` align=left | form-number | KEEP-HIEN-THI |
| PLI_M11 | national-header | - | Khong co quoc hieu (mau danh sach) - dung voi nguon | - | OK-NONE |
| PLI_M11 | hard-break-collapse | block 5 | `, ngàythángnăm\nNGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ CỦA CÔNG TY\n(Ký và ghi họ tên)2` align=center (\n x3) | signature | OPEN-L2-br |
| PLI_M11 | date-line | tpl para / block 5 | `{dia_diem_ky}, ngày{ngay_ky_vb}tháng{thang_ky_vb}năm{nam_ky_vb}NGƯỜI ĐẠI DIỆN TH` - jc=center spacing=before=120 | date-line | INFO-role |
| PLI_M11 | form-title | block 2 | `DANH SÁCH ĐỂ XÁC ĐỊNH CHỦ SỞ HỮU HƯỞNG LỢI CỦA DOANH NGHIỆP` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M11 | signature | tpl para | `{dia_diem_ky}, ngày{ngay_ky_vb}tháng{thang_ky_vb}năm{nam_ky_vb}NGƯỜI ĐẠI DIỆN TH` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M11 | superscript-OOXML | 3 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M11 | src-vs-template | - | nguon=DN_PL1_Mau_11_ke_khai_thong_tin_de_xac_dinh_chu_so_huu_huong_loi_cua_doanh_nghiep.docx paras=11 vs template=59; file nguon tach ra gan nhu trong (11 doan); noi dung that nam trong _Bieu_mau_PL_I_II_full.docx | - | INFO |

---

## PLI_M12 — Giấy đề nghị đăng ký thay đổi nội dung Giấy chứng nhận đăng ký doanh nghiệp/Thông báo thay đổi nội dung đăng ký doanh nghiệp

blocks=236 · template paras=409 · w:br=18 · w:tab=3 · sup-paras=24 · footnotes.xml=KHONG · w:ind=0

| form_id | category | block_idx/para | evidence (trich nguyen van, escape) | expected role/style | status |
|---|---|---|---|---|---|
| PLI_M12 | source-indicator | - | Khong tim thay pattern 'PL\d - Mau so' trong blocks/template/nguon (M12 tach tu file full khong keo marker) | source-indicator (uiHidden=true) | OK-NONE |
| PLI_M12 | form-number | - | Khong co dong 'Mau so N'; chi co truong 'So: {so_van_ban}' (so van ban, khong phai so mau) | form-number | OK-NONE |
| PLI_M12 | national-header/motto/separator | block 0 | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc \n---------------` bold=True align=center - 3 dong trong 1 run, \n x2; OOXML: 1 para jc=center spacing before=120, cac dong phan cach bang w:br | national-header + national-motto + national-separator (3 visual line rieng) | OPEN-L2-br |
| PLI_M12 | hard-break-collapse | block 42 | `ĐĂNG KÝ THAY ĐỔI THÀNH VIÊN CÔNG TY TNHH/\nTHÀNH VIÊN HỢP DANH CÔNG TY HỢP DANH` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M12 | hard-break-collapse | block 45 | `ĐĂNG KÝ THAY ĐỔI VỐN ĐIỀU LỆ, PHẦN VỐN GÓP, \nTỶ LỆ PHẦN VỐN GÓP` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M12 | hard-break-collapse | block 118 | `ĐĂNG KÝ THAY ĐỔI VỐN ĐẦU TƯ\nCỦA CHỦ DOANH NGHIỆP TƯ NHÂN` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M12 | hard-break-collapse | block 150 | `THÔNG BÁO THAY ĐỔI CỔ ĐÔNG SÁNG LẬP/ \nTHÔNG BÁO THAY ĐỔI CỔ ĐÔNG LÀ NHÀ ĐẦU TƯ NƯỚC NGOÀI CÔNG TY CỔ PHẦN1` align=center (\n x1) | body/form-title... - giu hard break (<br> sau escape) | OPEN-L2-br |
| PLI_M12 | hard-break-collapse | block 232 | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/\nCHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN/CHỦ TỊCH HỘI ĐỒNG QUẢN TRỊ/\nNGƯỜI ĐƯỢC ỦY Q` align=center (\n x3) | signature | OPEN-L2-br |
| PLI_M12 | candidate-footnote | block 18 (p/runs) | 'ng đến quốc phòng, an ninh1: Có  Không ' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-footnote | block 102 (p/runs) | 'ĐỔI NGÀNH, NGHỀ KINH DOANH1' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-footnote | block 143 (p/runs) | 'ĐÔNG LÀ TỔ CHỨC NƯỚC NGOÀI1' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-footnote | block 145 (p/runs) | 'iấy tờ pháp lý của cá nhân2Quốc tịchDân tộ' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-legit-digit | block 145 (p/runs) | 'hời điểm đại diện phần vốn1234567891011121314_______________' truoc digit `1234567891011121314` - chuoi so dai (cot so / lien tiep) | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M12 | candidate-footnote | block 150 (p/runs) | 'NƯỚC NGOÀI CÔNG TY CỔ PHẦN1' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-footnote | block 181 (p/runs) | 'Ngày bắt đầu hoạt động2: //' truoc digit `2` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | candidate-legit-digit | block 213 (p/runs) | ' Điều 3 Luật số 76/2025/QH15 ngày 17/6/2025' truoc digit `15` - trich dan van ban phap luat (so VB/QH15/NĐ-CP), khong phai chu thich | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M12 | candidate-legit-digit | block 214 (p/runs) | ' Điều 3 Luật số 76/2025/QH15 ngày 17/6/2025' truoc digit `15` - trich dan van ban phap luat (so VB/QH15/NĐ-CP), khong phai chu thich | body (digit hop le, khong duoc regex xa) | INFO-KEEP |
| PLI_M12 | candidate-footnote | block 215 (p/runs) | 'G TIN ĐĂNG KÝ DOANH NGHIỆP1' truoc digit `1` - digit co w:vertAlign=superscript tuong ung trong template | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | tab-loss | block 34 | `Thư điện tử (nếu có):  Website (nếu có): \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M12 | tab-loss | block 51 | `Thời điểm thay đổi vốn: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M12 | tab-loss | block 123 | `Thời điểm thay đổi vốn: \t` chua literal <TAB> | body - tab stop chuyen layout semantic, khong &nbsp; | OPEN-L1-extract |
| PLI_M12 | date-line | tpl para / block 2 | `{dia_diem_ky}, ngày{ngay_ky_vb} tháng{thang_ky_vb} năm {nam_ky_vb}` - jc=right spacing=before=120 | date-line | INFO-role |
| PLI_M12 | salutation | tpl para / block 6 | `Kính gửi: (Cơ quan đăng ký kinh doanh cấp tỉnh) {co_quan_dkkd}` - jc=center spacing=before=120 | salutation | INFO-role |
| PLI_M12 | form-title | block 3 | `GIẤY ĐỀ NGHỊ` bold=True align=center | form-title / form-subtitle | INFO-role |
| PLI_M12 | signature | tpl para | `NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/CHỦ TỊCH CÔNG TY/CHỦ TỊCH HỘI ĐỒNG THÀNH VIÊN/CHỦ ` - jc=center spacing=before=120 | signature | INFO-role |
| PLI_M12 | superscript-OOXML | 24 paras | VD: 'Tôi là<sup>1</sup>', '(Ký và ghi họ tên)<sup>N</sup>' - run so la w:vertAlign=superscript rieng; blocks da hap vao baseline text | footnote-ref run (vertAlign) + footnote body role=footnote | OPEN-L1-extract |
| PLI_M12 | src-vs-template | - | nguon=PL1_Mau_12_tach_tu_file_full.docx paras=346 vs template=409 | - | INFO |

---

## Root cause (evidence-based, cho L1/L2)

1. Marker: converter (`tools/docx_to_blocks.py`) giu nguyen paragraph dau 'PL1 - Mau so N: ...' tu nguon goc (nguon import da chua marker - xem src_first trong evidence). 11/12 mau bi anh huong; PLI_M12 tach tu `_Bieu_mau_PL_I_II_full.docx` khong mang marker. Wrapper app khong them marker.
2. Newline collapse: OOXML giu 3 dong quoc hieu/tieu de/chu ky trong 1 `<w:p>` phan cach bang `<w:br/>`; blocks nen thanh 1 run text chua `\n`; `render.js:148` chi `escapeHtml(run.text)` roi dat vao `<span>`, `.bp` khong co `white-space: pre-line` -> browser collapse thanh mot dong.
3. Footnote: KHONG form nao dung `w:footnoteReference` (0/12, footnotes.xml khong ton tai). So chu thich la run `w:vertAlign="superscript"` dung canh run chu + paragraph chu thich cuoi van ban (run so cung superscript). Converter hap sup-run vao baseline -> 'Tôi là1'. Khong duoc regex xa digit: cac truong hop legit da liet ke (cot so '123456789101112...', trich dan 'Luật số 76/2025/QH15', 'Nghị định số 168/2025/NĐ-CP').
4. Tab: `<w:tab/>` trong template -> literal `\t` trong run text blocks -> HTML collapse thanh space, mat vai tro can le (vd 'Tôi là1 (ghi họ tên...): \t').
5. Spacing/format: template co spacing before/after=120tw rai rac (khong deu 100% paragraph - xem spacing_before120_paras/paras trong evidence); blocks khong giu gia tri nao. w:ind = 0 toan bo 12 mau.

## De xuan chuan hoa cho Lead khi merge manifest (87/87)

- Ghi nhan PLI_M12 la NGOAI LE: khong co source-indicator; detector khong duoc bat buoc moi form phai co marker de an.
- Form-number hop le can KEEP: 11 dong dau + 4 heading con cua PLI_M09 (block idx 108='Mẫu số 7', 128='Mẫu số 8', 149='Mẫu số 9', 178='Mẫu số 10') - day la heading cua cac danh sach kem theo trong cung mau, tuyet doi khong an vi nham la marker.
- Role mapping de nghi cho khoi header chung: block 'CỘNG HÒA...' -> national-header/motto/separator (tach 3 line khi render); block 'Mẫu số N' -> form-number; ', ngay...thang...nam...' -> date-line (M01-M05: center; M12: right); 'Kính gửi:' -> salutation; block title uppercase center -> form-title; block '(Ký và ghi họ tên)...' -> signature.
- Footnote-ref: contract can `runs[].vertAlign='superscript'` + role `footnote-ref`; footnote body cuoi van ban gan role `footnote`. Danh so footnote restart theo tung mau (1..7 hoac 1..15...) - khong dung so thu tu global.
- Tab: chuyen thanh first-line/left indent semantic hoac flex gap; cam nhung `&nbsp;` hang loat.
- Phan loai digit-glued: 55/62 occurrence da khop ground-truth vertAlign cua template; 0 truong hop con lai o trang thai 'unverified'. Cac truong legit-digit (7) deu co ly do ro trong bang - L1 khong duoc de regex xa nham.
- Screenshot UI: NOT RUN (thieu browser backend). Bu bang evidence text/OOXML trich nguyen van trong fragment nay; gate screenshot thuoc L3.

## NOT RUN / gioi han pham vi

- Screenshot trang dau UI tung mau: NOT RUN - thieu browser backend (de bai cam cai dependency).
- Khong chay generator/docx_to_blocks (read-only census); khong hoi quy test vi khong sua code.
- Phan loại footnote/legit dua tren ground-truth vertAlign cua TEMPLATE (file dang dung trong production); file nguon goc khong duoc dung de phan loai vi trung lap tinh trang flatten o mot so mau (M07/M10/M11 nguon gan nhu trong - da ghi trong bang src-vs-template).