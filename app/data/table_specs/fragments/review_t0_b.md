# Review T0-B — Kiểm toán độc lập fragment census PLI_M13–M80

- **Reviewer:** Agent Review-B
- **Đối tượng review:** `app/data/table_specs/fragments/t0_b.json` @ `ff09541` (nhánh `agent/t0-b-pli-late`), sinh bởi `tools/census/t0_b_census.py`
- **Chuẩn đối chiếu:** PLAN.md — chương trình toàn bộ bảng (taxonomy `editable-grid`/`fixed-matrix`/`nested-grid`/`output-table`, trạng thái `already_complete`/`missing_grid`/`partial_columns`/`output_only`/`no_table`, Wave T0 census chỉ đọc)
- **Nguyên tắc:** bằng chứng thực tế (DOCX/blocks/form_maps quét lại độc lập) > lời khai fragment

## 1. Bảng verdict 47/47 form

| Form | Status fragment | Verdict | Ghi chú |
|---|---|---|---|
| PLI_M13 | BLOCKED_LEGAL_REVIEW | **AGREE** | Footer "Ghi thông tin của tất cả NĐDPL…" đúng literal tại nguồn `#p40`; blocks đúng 1 bộ `ndd.*`, không thêm/xóa dòng |
| PLI_M14 | TABLE_COMPLETE | **AGREE** | Template p11–p17: 3 nhãn lựa chọn + `{chk_cd_dntn_tang}`/`{chk_cd_dntn_chu_chet}`/(bán); 0 `w:tbl` còn lại; chk=3 khớp |
| PLI_M15 | BLOCKED_LEGAL_REVIEW | **AGREE** | Header nối `STTTên người đại diện…` xác thực tại tpl idx48 và src `#p50`; 0 input cho vùng lưới trong blocks |
| PLI_M17 | BLOCKED_LEGAL_REVIEW | **AGREE** | Loop `ds_nganh` có thật (blocks+form_maps); thiếu khu CN/CXC/KT/KCCN (tpl p23–p30, 0 key chk_khu), thiếu BHXH, thiếu hạch toán/BOT/GTGT (0 key tương ứng) |
| PLI_M18 | NO_TABLE | **AGREE** | Dump toàn văn: văn bản đánh số 1.–5., một đơn vị/giấy, 0 bảng |
| PLI_M19 | BLOCKED_LEGAL_REVIEW | **AGREE** | Loop ds_nganh backed; heading thuế HIT idx70; thiếu hạch toán/BOT xác nhận qua keys |
| PLI_M21 | TABLE_COMPLETE | **AGREE** | `w:tbl` duy nhất row0 = `STT\|Tên ngành\|Mã ngành\|Ngành, nghề kinh doanh chính` = đúng loop ds_nganh; src chỉ 1 marker STT |
| PLI_M23 | BLOCKED_LEGAL_REVIEW | **AGREE*** | Phân loại đúng; nhưng heading evidence ghi "6. Thông tin đăng ký thuế:" — template thật là **"7. Thông tin đăng ký thuế:"** (tpl p52) ⇒ lỗi evidence nhỏ |
| PLI_M25 | BLOCKED_LEGAL_REVIEW | **AGREE** | 2 heading HIT; loop backed; thiếu hạch toán/BOT/GTGT xác nhận qua keys |
| PLI_M26 | NO_TABLE | **AGREE** | 0 bảng, chỉ 1 bộ cn.ten/cn.ma_so + lý do |
| PLI_M27 | BLOCKED_LEGAL_REVIEW | **AGREE** | Vùng NĐDPL "1. Họ…"/"2. Họ…" tpl p17–p24 khớp; 6 khối đơn vị tpl p27/p35/p44/p52 ↔ blocks `cn.ten_tieng_viet`×6; `ho_ten_in_hoa_2`×2 đúng như notes |
| PLI_M28 | NO_TABLE | **AGREE** | "sau:" p13 + mục 1..4 là thông tin MỘT đơn vị; blocks map đủ cn.* |
| PLI_M29 | NO_TABLE | **AGREE** | "sau:" p12 → 1 bộ trường đơn vị nước ngoài; không lưới |
| PLI_M30 | NO_TABLE | **AGREE** | "như sau:" p13 → giải thể, 1 DN |
| PLI_M31 | NO_TABLE | **AGREE** | "như sau:" p13 → hủy bỏ NQ/QĐ giải thể |
| PLI_M32 | NO_TABLE | **AGREE** | "như sau:" p23 → công bố nội dung ĐKDN |
| PLI_M33 | NO_TABLE | **AGREE** | 0 bảng, 0 marker |
| PLI_M42 | NO_TABLE | **AGREE** | GCN hoạt động CN/VPĐD — giấy kết quả, không có vùng danh sách |
| PLI_M43 | NO_TABLE | **AGREE** | GCN đăng ký ĐĐKD — tương tự M42 |
| PLI_M45 | NO_TABLE | **AGREE** | "sau:" p16 → 1 bộ ten+mã+sản thay đổi; blocks khớp |
| PLI_M46 | NO_TABLE | **AGREE** | 1 key `cap_lai_ngay`, giấy chứng nhận |
| PLI_M47 | NO_TABLE | **AGREE** | Thông báo CQ thuế quản lý trực tiếp — output |
| PLI_M48 | NO_TABLE | **AGREE** | "sau:" p18 là mệnh đề trong câu, không phải intro danh sách |
| PLI_M49 | NO_TABLE | **AGREE** | Tương tự — "sau" nằm trong câu điều kiện |
| PLI_M50 | NO_TABLE | **AGREE** | Anchor `#p16-p19` xác thực: heading p16 + đúng 3 dòng chấm p17–p19 |
| PLI_M51 | NO_TABLE | **AGREE** | Hiệu định GCN — 0 bảng |
| PLI_M52 | BLOCKED_LEGAL_REVIEW | **AGREE** | Claim xác thực từng điểm: tpl p22 "- Người đại diện theo pháp luật:" không có key; tpl p39 "- Đơn vị chủ quản:" không có key riêng; `ma_so_van_ban`×4 tái sử dụng cho DN+3 nhóm |
| PLI_M53 | NO_TABLE | **AGREE** | Yêu cầu tạm ngừng nghề ĐKKD — text tự do (`yeu_cau_dn`, `tn_nganh_nghe`) |
| PLI_M54 | NO_TABLE | **AGREE** | Heading HIT p14; census bác dự đoán PLAN mục E là đúng: chỉ 1 câu xác nhận + tu_ngay/den_ngay |
| PLI_M55 | NO_TABLE | **AGREE** | 2 vùng "đối với…sau:" (CN/ĐĐKD p16, VPĐD p25) đều số ít 1 đơn vị; blocks map đủ |
| PLI_M56 | BLOCKED_LEGAL_REVIEW | **AGREE** | tpl p15 (tất cả) / p16 (một hoặc một số) có thật; case grid p16 chỉ có 1 bộ `cn.ten`+`ma_so_van_ban` (key sai ngữ nghĩa đúng như notes) |
| PLI_M57 | NO_TABLE | **AGREE** | 2 vùng "sau:" số ít; blocks map đủ |
| PLI_M63 | BLOCKED_LEGAL_REVIEW | **AGREE** | "Có các ĐĐKD trực thuộc chi nhánh:" HIT p31; 0 key cho danh sách; QUYẾT ĐỊNH tpl p6–p7 = output_only đúng |
| PLI_M66 | BLOCKED_LEGAL_REVIEW | **AGREE*** | 3 heading đều HIT; nhóm ĐĐKD trực thuộc 0 key; nhưng notes "Blocks chỉ có 1 bộ tên+mã" không chính xác: thực tế `cn.ten_tieng_viet`×2, `cn.ma_so_2`×3 (vẫn không multi-row) |
| PLI_M67 | BLOCKED_LEGAL_REVIEW | **AGREE** | tpl p8 khớp literal "(các) chi nhánh…sau đây"; blocks lặp đúng 2 bộ như notes |
| PLI_M68 | BLOCKED_LEGAL_REVIEW | **AGREE** | Marker list_intro "Các chi nhánh…sau" phát hiện đúng; 1 bộ cn.ten/cn.ma_so; phần CQB output_only HIT p7 |
| PLI_M69 | NO_TABLE | **AGREE** | "sau:" p8 là mệnh đề, 1 DN |
| PLI_M70 | BLOCKED_LEGAL_REVIEW | **AGREE** | "Hồ sơ bao gồm:" + NGƯỜI NỘP/NGƯỜI NHẬN đều HIT; 0 key cho 3 dòng tài liệu |
| PLI_M71 | BLOCKED_LEGAL_REVIEW | **AGREE** | "Hồ sơ bao gồm:" HIT; chữ ký chỉ cơ quan (khác M70) đúng; 0 key tài liệu |
| PLI_M72 | BLOCKED_LEGAL_REVIEW | **AGREE** | Cấu trúc khớp tuyệt đối: 5×"5. Ngành, nghề kinh doanh" (1 w:tbl thật = loop + 4 dải STT rời), 2 header nối `STTTên cổ đông…` (cổ đông sáng lập + NN), TNHH 2TV+ và HD hợp danh 0 key. Xem §3.3 |
| PLI_M73 | NO_TABLE | **AGREE** | Công bố thay đổi — 6 key đầu trang |
| PLI_M74 | NO_TABLE | **AGREE** | Công bố nội dung — 0 bảng |
| PLI_M75 | BLOCKED_LEGAL_REVIEW | **AGREE** | 3 heading HIT (CN/VPĐD/ĐĐKD, ĐĐKD trực thuộc, thông báo khôi phục); 0 key cho 2 danh sách |
| PLI_M76 | NO_TABLE | **AGREE** | Thông báo cấp ĐKDN qua mạng — 0 bảng |
| PLI_M78 | BLOCKED_LEGAL_REVIEW | **AGREE** | Heading ghép xác thực từng thành phần: p18 "3. Thông tin yêu cầu:", p19 `STT`, p20–21 tên/SL sản phẩm, hàng cố định "1 / GCNĐKDN của…"; 0 key sản phẩm (fm chỉ 17 key người yêu cầu/biên lai) |
| PLI_M79 | BLOCKED_LEGAL_REVIEW | **AGREE** | p32 "Kèm theo…có:" + đúng 3 dòng 1./2./3. + dấu "…" p36; 0 key |
| PLI_M80 | BLOCKED_LEGAL_REVIEW | **AGREE** | Như M79; heading HIT; 0 key |

\* AGREE có ghi chú evidence cần chỉnh (không đổi phân loại).

**Tổng: 47 AGREE — 0 DISAGREE — 0 NEEDS_EVIDENCE.** Không có case "khai missing_grid nhưng blocks/form_maps đã có loop/table đủ cột" (kiểm tra ngược trên toàn bộ 20 form BLOCKED + 2 TABLE_COMPLETE).

## 2. Kiểm tra cấu trúc (tự động 47/47)

Viết script Python độc lập (`cen.analyze_blocks` reimplement walk giống census + đối chiếu JSON):

| Hạng mục | Kết quả |
|---|---|
| Đủ 47 form PLI_M13–M80 (toàn bộ `app/data/blocks/PLI_*.json` trừ M01–M12) | **PASS** — tập ID khớp 1:1, không thiếu/thừa |
| `form_status` ∈ {NO_TABLE, TABLE_COMPLETE, BLOCKED_LEGAL_REVIEW} | **PASS** — 25/2/20, không giá trị lạ |
| Section đủ trường: section_id, title, kind, semantic_key_suggestion, required_columns, status, source_evidence{template,heading,anchor}, notes | **PASS** — 41 section × 47 form, không thiếu trường; kind/status đều thuộc taxonomy PLAN |
| `summary_counts` {p,chk,table,loop} khớp `app/data/blocks/<id>.json` | **PASS 47/47** — đồng thời chạy lại chính `tools/census/t0_b_census.py --out <temp>`: 47 forms, **0 lệch số liệu**, `forms_without_blocks_in_range=[]` |

## 3. Bằng chứng anchor (22 form BLOCKED + TABLE_COMPLETE)

### 3.1 Heading tồn tại trong `app/templates/<id>.docx`
40/41 section khớp (exact hoặc fuzzy sau khi bỏ dấu/ellipsis). 12 trường hợp miss ban đầu đều do heading trong fragment viết tắt bằng "…" — đã resolve hết bằng fuzzy match, ví dụ:
- M17 khu CN: tpl p23 "- Chi nhánh/Văn phòng đại diện/Địa điểm kinh doanh nằm trong (Doanh nghiệp phải đánh dấu X…" + p26 "Khu chế xuất" + p30 "Khu công nghệ cao".
- M63: "QUYẾT ĐỊNH" p6 + "Về việc thu hồi GCNĐKHĐ…" p7 (2 paragraph liền nhau).
- M72 co_dong_sang_lap / co_dong_nuoc_ngoai: đúng 2 paragraph nối `STTTên cổ đôngQuốc tịchSố Giấy tờ pháp lý…` (p143, p145).

### 3.2 Anchor `#pN` resolvable (5 section)
- M13 `#p12` → đúng heading; footer claim "dòng 40 nguồn" → đúng literal `p40`.
- M14 `#p11`, M21 `#p12` (=STT), M15 `#p50` (=đúng paragraph header nối) — tất cả khớp.

### 3.3 Nhận định missing_grid/already_complete
- **already_complete (6):** M17/M19/M21/M23/M25 loop `ds_nganh` có thật trong blocks + `form_maps.dynamic_tables`; M14 fixed-matrix đã làm phẳng thành 3 chk (chk=3, template còn nguyên nhãn + token chk).
- **missing_grid/partial_columns (không có input nào bị map sẵn):** đối chiếu toàn bộ input keys từng form — M13 (1 bộ ndd.*), M15 (0 key vùng lưới), M17 (thiếu khu/BHXH/hạch toán/BOT/GTGT), M27 (6 khối × 1 bộ), M56/M63/M66/M67/M68/M70/M71/M75/M78/M79/M80 (0 key cho các danh sách), M72 (chỉ 1 loop ngành, 0 key thành viên/cổ đông). **Không có case DISAGREE kiểu "khai missing mà thực tế đã có loop/table đủ cột".**
- **Cross-check form_maps (mục 4 của nhiệm vụ):** form duy nhất có loop tag là M72 — fragment **có** section tương ứng (`nganh_nghe_5_loai_hinh`, partial_columns, notes nêu rõ 1 loop + 4 vùng rời) ⇒ không flag mất section; chỉ khuyến nghị tách section `already_complete` riêng cho phần loop khi lead merge (xem §5).

## 4. Missed signatures (sample sâu NO_TABLE)

Phương pháp: (a) đếm `<w:tbl>` trong **toàn bộ XML** (document + header + footer, bao phủ cả textbox) của cả template lẫn nguồn gốc cho **cả 47 form**; (b) quét marker `^STT$`, `^STT<Tên cột>…`, `Danh sách/Liệt kê`, `^Các…sau`, và từ khóa giữa câu ("danh sách", "liệt kê", "sau đây", "sau:", "kèm theo", "bao gồm", "trực thuộc") trên 100% paragraph của 25 form NO_TABLE; (c) dump + đọc toàn văn 10 mẫu: M18, M26, M28, M29, M42, M45, M50, M53, M54, M76 (các mẫu còn lại được phủ bởi (a)+(b)).

**Kết quả: 0 MISSED_SIGNATURE.**
- 25/25 form NO_TABLE: 0 `w:tbl` ở mọi vị trí XML (template + nguồn).
- Mọi cụm "…sau:"/"như sau:" tìm thấy đều là intro của khối trường đơn-vị (1. Tên / 2. Địa chỉ / 3.… theo mẫu giấy) hoặc mệnh đề trong câu (M47/M48/M49/M69), không phải dòng lặp.
- Các vùng đặc biệt đã được fragment classify đúng: M28/M50/M54/M55/M57 (section `no_table` riêng), M68 (list_intro → BLOCKED).

## 5. Mismatch / sai lệch evidence cần lead xử lý (không đổi phân loại, không block merge)

1. **[EVIDENCE-FIX] M23 heading sai số thứ tự:** `source_evidence.heading` ghi `"6. Thông tin đăng ký thuế:"` — template thật là **`"7. Thông tin đăng ký thuế:"`** (`app/templates/PLI_M23.docx` p52; không tồn tại heading "6."). Cần sửa heading (và cân nhắc đổi `section_id: thue_chi_tieu_6_1_6` cho nhất quán).
2. **[EVIDENCE-FIX] ~34 anchor dùng tên file viết tắt** dạng `03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_17_....docx#p67` — không resolve được file thật (report census gốc có đủ path dài). Khuyến nghị thay bằng canonical path để audit machine-checkable; 5 anchor dạng `tools/form_specs/change/PLI_M*.json + loop ds_nganh` đã verify tồn tại + chứa `ds_nganh` (chấp nhận được).
3. **[NOTE-FIX] M66:** notes "Blocks chỉ có 1 bộ tên+mã" — thực tế `cn.ten_tieng_viet`×2 / `cn.ma_so_2`×3. Bản chất (không multi-row) vẫn đúng, nên sửa câu mô tả.
4. **[MERGE-TIP] M72:** phần loop `ds_nganh` đang gộp trong section `partial_columns`; khi gộp manifest chung nên tách 1 entry `already_complete` cho loop này + giữ 4 vùng STT rời là scope bắt buộc (fragment đã ghi đúng hướng này trong notes).

## 6. Kết luận tổng

**VERDICT: MERGE-READY** (kèm 2 EVIDENCE-FIX + 1 NOTE-FIX + 1 MERGE-TIP nêu trên — đều là chỉnh sửa metadata, không ảnh hưởng form_status/kind/columns đã được xác thực bằng DOCX và blocks).

Cơ sở: cấu trúc 47/47 PASS; summary_counts 47/47 khớp blocks (kiểm tra 2 lần độc lập); bằng chứng heading/anchor xác thực cho 22 form BLOCKED/TABLE_COMPLETE; 0 missed signature trên 25 form NO_TABLE; 0 case misclassification missing↔complete.

## 7. Lệnh đã chạy (trung thực)

| # | Lệnh / bước | Kết quả |
|---|---|---|
| 1 | `git log --oneline -3`, `git status --short` (worktree sạch @ff09541) | PASS |
| 2 | Script audit #1: tập form, form_status, trường section, **summary_counts×47 tự động**, cross-check form_maps, quét DOCX template+nguồn | PASS |
| 3 | Script audit #2: verify anchor `#pN`, đếm `w:tbl` toàn XML (document/header/footer) 47×(tpl+src), keyword sweep 25 NO_TABLE | PASS |
| 4 | Script audit #3: fuzzy heading 12 case MISS, ngữ cảnh 8 marker STT của M72, tồn tại `tools/form_specs/change/PLI_M{17,19,23,25}.json`, dump toàn văn 10 mẫu NO_TABLE, spot-check M27/M50/M52/M66 | PASS |
| 5 | `python tools/census/t0_b_census.py --out <temp>/t0_b_report_rerun.json` (chạy end-to-end, out ngoài repo) | PASS — 47 forms, 94 nguồn, 0 diff counts |
| 6 | Script audit #4: diff rerun↔fragment, spot-check M13 (#p40), M14 (3 chk), M15 (footnote tỷ lệ), M78 (hàng STT), M79 (3 dòng + …) | PASS |
| 7 | Lint / typecheck / test suite production repo | NOT RUN — review chỉ đọc, không sửa code; artifact duy nhất là file markdown này |

*(Mọi script audit đặt ở thư mục temp ngoài repo; repo không bị ghi ngoài file `review_t0_b.md`.)*
