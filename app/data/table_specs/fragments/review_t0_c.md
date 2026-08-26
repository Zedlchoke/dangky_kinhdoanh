# Review T0-C — Kiểm toán độc lập fragment `t0_c.json` (PLII_M01–M28)

- **Reviewer:** Agent Review-C · **Nhánh:** `agent/t0-c-plii` @ `cd144a8`
- **Đối tượng review:** `app/data/table_specs/fragments/t0_c.json` (28 mẫu) + `tools/census/t0_c_census.py`
- **Chuẩn đối chiếu:** PLAN.md — "Chương trình hoàn thiện toàn bộ bảng trong 87 biểu mẫu" (định nghĩa DONE, taxonomy `editable-grid`/`fixed-matrix`/`nested-grid`/`output-table`, trạng thái `NO_TABLE`/`TABLE_COMPLETE`/`BLOCKED_LEGAL_REVIEW`, Wave T0-C)
- **Nguyên tắc:** bằng chứng thực tế (blocks JSON + DOCX python-docx + raw OOXML zip + render thử) > lời khai fragment. Read-only, chỉ tạo đúng 1 file này.

## 1. Lệnh đã chạy và kết quả trung thực

| # | Lệnh | Phạm vi | Kết quả |
|---|------|---------|---------|
| 1 | `python review_c_audit.py` (script tạm ngoài repo): đếm lại `p/chk/table/loop` từ `app/data/blocks/PLII_M*.json`, đếm `w:tbl` body + **raw OOXML toàn part** (header/footer), quét chữ ký `STT`/`STT<nối>`/"Danh sách…sau", so `summary_counts` fragment | 28/28 form | **PASS** — 28/28 `summary_counts` khớp 100%, 0 mismatch |
| 2 | `python -X utf8 tools/census/t0_c_census.py --out <temp>/t0_c_evidence.json` | script được fragment dẫn làm nguồn | **PASS** — chạy sạch, exit 0, sinh đủ evidence 28 form |
| 3 | Dump đầy đủ paragraph + bảng (python-docx) từng template `PLII_M01–M28.docx`; dump blocks theo chỉ số B để đối chiếu anchor | 28 template + blocks M01/M02/M07/M17/M18 | **PASS** |
| 4 | Render thử `tools/docx_render.render()` trên `PLII_M01.docx` với dummy data từ `form_maps.json`, mở kết quả bằng python-docx | M01 (TABLE_COMPLETE) | **PASS** — và **phát hiện lỗi**: cột STT bảng thành viên render TRỐNG (mục 4.1) |

Không có lệnh nào FAIL; mọi kết luận dưới đây đều dựa trên output thật của các lệnh trên.

## 2. Bảng verdict 28 form

| Form | Fragment | Thực tế xác minh (blocks/docx/render/form_maps) | Verdict |
|------|----------|--------------------------------------------------|---------|
| PLII_M01 | TABLE_COMPLETE, 2 sections already_complete | 2 `w:tbl` (6×4 ngành, 6×10 thành viên), tags `#ds_nganh`/`#ds_tv_ho_gia_dinh` khớp loop B034/B052; **nhưng render thử: cột STT bảng thành viên trống** (template thiếu `{_stt}` ở ô r5c0) | **DISAGREE** (mục 4.1) |
| PLII_M02 | BLOCKED_LEGAL_REVIEW, 8 sections | Đủ 8 vùng bảng thật của template; anchor B072/B079‑B082/B084‑B087/B089‑B091/B095‑B099/B118/B122‑B132/B137 khớp **từng chỉ số block**; `w:tbl` duy nhất = bảng ngành C.3 tagged `#ds_nganh` (already_complete đúng sau Wave 2C); 2 glued‑STT thành viên + 4 STT rời = đúng 4 section còn lại | **AGREE** |
| PLII_M03 | NO_TABLE | 0 `w:tbl` (raw OOXML), văn thư thuần, 0 signature | **AGREE** |
| PLII_M04 | NO_TABLE | 0 `w:tbl`, thông báo chấm dứt hoạt động thuần chữ | **AGREE** |
| PLII_M05 | NO_TABLE | 0 `w:tbl`, giấy đề nghị cấp lại thuần chữ | **AGREE** |
| PLII_M06 | NO_TABLE | 0 `w:tbl`; hint regex "…dưới đây:" là false positive (kèm trường dân tộc/quốc tịch, không phải bảng) | **AGREE** |
| PLII_M07 | BLOCKED_LEGAL_REVIEW, 2 sections | `w:tbl` duy nhất 6×4 tagged `#ds_nganh` = already_complete đúng (Wave 2C); mục 7 là 7 header paragraph rời B027–B033 (`STT\|Tên thành viên\|Quốc tịch\|Nơi ở hiện tại\|Nơi thường trú\|Số định danh cá nhân\|Ghi chú`) — đúng thứ tự/cột như fragment ghi, không có `w:tbl` tương ứng | **AGREE** |
| PLII_M08 | NO_TABLE | 0 `w:tbl`, thông báo cơ quan thuế quản lý | **AGREE** |
| PLII_M09 | NO_TABLE | 0 `w:tbl`, GCN cấp lại dạng trống | **AGREE** |
| PLII_M10 | NO_TABLE | 0 `w:tbl`, thông báo sửa đổi bổ sung hồ sơ | **AGREE** |
| PLII_M11 | NO_TABLE | 0 `w:tbl`; "các nội dung sau" = dòng chấm tự do, không bảng | **AGREE** |
| PLII_M12 | NO_TABLE | 0 `w:tbl`, thông báo vi phạm/thu hồi | **AGREE** |
| PLII_M13 | NO_TABLE | 0 `w:tbl`, thông báo chấm dứt hoạt động | **AGREE** |
| PLII_M14 | NO_TABLE | 0 `w:tbl`, quyết định thu hồi (Điều 1–4, không bảng) | **AGREE** |
| PLII_M15 | NO_TABLE | 0 `w:tbl`, quyết định thu hồi lần thay đổi | **AGREE** |
| PLII_M16 | NO_TABLE | 0 `w:tbl`, quyết định hủy bỏ thu hồi/khôi phục | **AGREE** |
| PLII_M17 | NO_TABLE (+ section `ho_so_bao_gom` no_table) | Anchor B016–B019 khớp tuyệt đối: "Hồ sơ bao gồm:" + 3 dòng chấm 1./2./3.; 0 `w:tbl`. Free-text là trung thành mẫu theo PLAN G | **AGREE** |
| PLII_M18 | NO_TABLE (+ section `ho_so_bao_gom` no_table) | Anchor quanh B017 khớp (B017 heading, B018–B020 dòng chấm); 0 `w:tbl` | **AGREE** |
| PLII_M19 | NO_TABLE | 0 `w:tbl`, thông báo tạm ngừng ngành có điều kiện | **AGREE** |
| PLII_M20 | NO_TABLE | 0 `w:tbl`, giấy xác nhận tạm ngừng/tiếp tục KD | **AGREE** |
| PLII_M21 | NO_TABLE | 0 `w:tbl`; "ghi tương ứng với từng loại" = văn bản điều khoản, không bảng | **AGREE** |
| PLII_M22 | NO_TABLE | 0 `w:tbl`, thông báo yêu cầu thay đổi thành viên | **AGREE** |
| PLII_M23 | NO_TABLE | 0 `w:tbl`, thông báo xử lý hồ sơ sai quy định | **AGREE** |
| PLII_M24 | NO_TABLE | 0 `w:tbl`, thông báo khôi phục GCN | **AGREE** |
| PLII_M25 | NO_TABLE | 0 `w:tbl`, thông báo hiệu đính nội dung GCN | **AGREE** |
| PLII_M26 | NO_TABLE | 0 `w:tbl`, thông báo dừng/từ chối dừng thủ tục | **AGREE** |
| PLII_M27 | NO_TABLE | 0 `w:tbl`, thông báo đang làm thủ tục chấm dứt | **AGREE** |
| PLII_M28 | NO_TABLE | 0 `w:tbl`, thông báo rà soát thông tin (danh sách `-`/`+` gạch đầu dòng, không lưới) | **AGREE** |

**Tổng: 27 AGREE · 1 DISAGREE · 0 NEEDS_EVIDENCE.**
Con số khai của fragment: **2 BLOCKED_LEGAL_REVIEW (M02, M07) · 1 TABLE_COMPLETE (M01) · 25 NO_TABLE — xác minh ĐÚNG**, khớp danh sách 28 file `app/data/blocks/PLII_*.json`.

## 3. Đối chiếu cấu trúc & số liệu (tự động, cả 28 form)

- `summary_counts {p,chk,table,loop}` so đếm độc lập theo đúng quy ước của script (`counts[t]` với `t ∈ {p,chk,table,loop}`): **28/28 khớp tuyệt đối**, ví dụ M01 63/4/0/2, M02 155/3/0/1, M07 34/0/0/1.
- `form_status` hợp lệ: chỉ dùng 3 giá trị cho phép của PLAN, không có TODO/trống.
- Mỗi section đủ trường bắt buộc (`section_id/title/kind/semantic_key_suggestion/required_columns/status/source_evidence{template,heading,anchor}`); `status` section dùng đúng bộ `{already_complete, missing_grid, no_table}`.
- `kind` dùng đúng taxonomy: `editable-grid` cho danh sách thay đổi dòng (ngành, thành viên), `fixed-matrix` cho chỉ tiêu thuế cũ/mới (a7) và chỉ tiêu thuế cấp đổi (c5).
- Anchor `heading` khớp nguyên văn template kể cả footnote nối dính (vd `"3. Ngành, nghề kinh doanh1:"`, `"Danh sách các thành viên hộ gia đình đăng ký hộ kinh doanh sau khi thay đổi2:"`).

## 4. Misclassification chi tiết

### 4.1 PLII_M01 — DISAGREE (duy nhất): `TABLE_COMPLETE` chưa đạt chuẩn DONE vì STT bảng thành viên không tự sinh

- **Bằng chứng:** template `PLII_M01.docx` `w:tbl[1]` (thành viên hộ gia đình) hàng khuôn r5 có cột 0 **rỗng** — khác với `w:tbl[0]` (ngành) có `{_stt}` ở cột 0. Tags thực tế của tbl1: `#ds_tv_ho_gia_dinh, ho_ten, ngay_sinh, so_cccd, gioi_tinh, quoc_tich, dan_toc, noi_thuong_tru, noi_o_hien_tai, chu_ky` — **không có `_stt`**.
- **Render thử** (`tools/docx_render.py`, 2 dòng dummy): bảng ngành sinh STT `1`,`2` đúng; **bảng thành viên sinh ô STT trống** ở mọi dòng dữ liệu. Engine render chỉ thay `{_stt}` khi template có sẵn tag (docx_render.py:96); test hiện có `t_plii_m01_stt_x` chỉ kiểm tra bảng ngành, không phủ bảng thành viên.
- **Đối chiếu DONE:** vi phạm tiêu chí #8 "DOCX … không lệch cột/STT" (và #3 nếu không phân loại lại). Fragment ghi `required_columns` có `stt` + `already_complete` nhưng không nêu khoảng trống này trong `notes`.
- **Fix cụ thể (cho lead, ngoài phạm vi review):** gắn `{_stt}` vào ô r5c0 của `w:tbl[1]` trong `app/templates/PLII_M01.docx` qua generator (spec `stt_tag=True`, tương tự build_form_maps.py:708‑723), rồi mới giữ `TABLE_COMPLETE`; hoặc hạ section thành `partial_columns` kèm legal/technical question. Các phần còn lại của M01 (cột 10/10 khớp header mẫu, `chu_ky` outputOnly, blankRows=4, chú thích chân trang cột 1‑5+10) đã xác minh đúng.

### 4.2 Kiểm tra các nghi vấn theo checkpoint lead — kết quả fragment ĐÚNG reality

1. **ds_nganh PLII_M02 & PLII_M07 (Wave 2C):** fragment đánh `already_complete` cho `c3_nganh_cap_doi` (M02) và `m3_nganh_kinh_doanh` (M07) — khớp thực tế: mỗi file có đúng 1 `w:tbl` 6×4 tagged `#ds_nganh` (`{_stt}|ten_nganh|ma_nganh|la_nganh_chinh`), loop blocks B118 (M02)/B016 (M07) `cols=[1,2,3], headerRows=[0], blankRows=4`, header `'STT|Tên ngành|Mã ngành|Ngành, nghề kinh doanh chính'`, form_maps có `ds_nganh.*`. **Không có misclassification missing_grid nào trên ds_nganh.**
2. **PLII_M02 đủ semantic loop ngành riêng:** fragment liệt kê đủ 3 bảng ngữ cảnh Mục A — `a6_1_nganh_bo_sung` (4 cột, B079–B082), `a6_2_nganh_bo` (4 cột, B084–B087), `a6_3_nganh_sua_chinh` (3 cột, B089–B091) — tất cả `missing_grid` đúng vì header bị converter tách thành paragraph rời, template không có `w:tbl` cho vùng này. Vùng "ngành trong phần thông tin hiện tại/đăng ký lại" theo PLAN mục A chính là bảng C.3 đã `already_complete`; **template M02 không còn vùng danh sách ngành nào khác** (đã dump toàn bộ 159 paragraph). Fragment không gộp một `ds_nganh` là xong → đạt yêu cầu lead.
3. **Phát hiện mới của fragment có giá trị thật:** `a7_thue_chi_tieu_cu_moi` (ma trận 3 cột `Chỉ tiêu|Thông tin đăng ký cũ|Thông tin đăng ký mới`, B095–B099, dòng `- Chỉ tiêu 5.1` + `-…..`) là cấu trúc cũ/mới mà inventory PLAN D trước đây chưa liệt kê cho M02 — xác minh có thật trong template (P094–P100).

### 4.3 Missed signatures (hunt sót bảng) — KHÔNG tìm thấy sót

- Quét **raw OOXML toàn bộ part** (document + header/footer) 25 mẫu NO_TABLE: **0 `w:tbl`** ở tất cả — không thể có bảng bị fragment bỏ qua ở tầng XML.
- Quét chữ ký đầu đoạn `^STT` và nối dính `^STT<Aa>`: **0 hit** trong 25 mẫu NO_TABLE (toàn bộ chữ ký dạng này nằm ở M02/M07 và đã được fragment classify).
- Regex "Danh sách/Liệt kê/Các … sau": 3 hit (M06, M11, M21) — kiểm tra tay toàn văn: đều là cụm dẫn nhập + dòng chấm/free-text, **không phải bảng** (false positive của detector, đúng như PLAN cảnh báo).
- Đọc tay toàn văn 25/25 mẫu NO_TABLE (vượt yêu cầu sample ≥8): gồm cả nhóm đông paragraph nhất M06(32p)/M14(30p)/M15(28p)/M28(32p): toàn bộ là giấy đề nghị/thông báo/quyết định/GCN hành chính, vùng nhiều dòng duy nhất là dòng chấm tự do (M11 P019–021, M17/M18 "Hồ sơ bao gồm", M28 gạch đầu dòng `-`/`+`) — không có hàng/cột pháp lý cần grid.
- `form_maps.json`: các prefix `chu_hkd.*`, `dn.*` ở mẫu NO_TABLE là nhóm field phẳng (không có block `t=loop` — xác minh qua đếm blocks); loop tags thật chỉ tồn tại ở M01 (`ds_nganh`, `ds_tv_ho_gia_dinh`), M02/M07 (`ds_nganh`) — **đều có section tương ứng trong fragment, không flag nào**.

## 5. Kết luận: **NEEDS-FIXES (1 fix nhỏ, còn lại merge-ready)**

Fragment chất lượng cao: 28/28 form đủ, 28/28 `summary_counts` khớp máy móc 100%, anchor trúng từng chỉ số block, con số 2 BLOCKED/1 TABLE_COMPLETE/25 NO_TABLE chính xác, không sót bảng nào trong 25 mẫu NO_TABLE, phản ánh đúng reality hậu Wave 2C (ds_nganh M02/M07 already_complete + đủ 3 loop ngành riêng của M02).

**Fix bắt buộc trước khi tính M01 là TABLE_COMPLETE (blocker duy nhất):**

> `PLII_M01/m7_thanh_vien_ho_gia_dinh`: template `w:tbl[1]` thiếu thẻ engine `{_stt}` ở ô (r5, c0) ⇒ xuất DOCX ra cột STT trống (đã chứng minh bằng render). Sửa bằng generator (gắn `{_stt}`, spec `stt_tag=True`) + thêm assert STT bảng thành viên vào test contract; đồng thời cập nhật `notes` của section. Nếu chưa sửa ngay, phải hạ section xuống `partial_columns` để không vi phạm DONE #8.

Không có mismatch nào khác; sau fix trên, fragment đạt MERGE-READY.

---

*Lệnh chạy: xem bảng mục 1 — PASS 4/4, FAIL 0, NOT RUN 0. File tạm phục vụ audit nằm ngoài repo (`%TEMP%\opencode\`), không thay đổi file production nào.*
