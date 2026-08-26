# L0-C — Layout Census PLII_M01–PLII_M28

- Agent: L0-C (read-only census; chỉ tạo fragment này)
- Worktree: `dangky_kinhdoanh-worktrees/l0-c-plii`, branch `l0/c-plii` @ 0ee70d3
- Ngày: 2026-08-26
- Phạm vi: 28/28 mẫu `app/data/blocks/PLII_M01.json` … `PLII_M28.json` (hộ kinh doanh)
- Nguồn đối chiếu OOXML: `app/templates/PLII_Mxx.docx` giải nén bằng zipfile + ElementTree (namespace `w:`); python-docx 3.14.6 có sẵn nhưng census dùng XML thô để bắt `w:br/w:cr/w:vertAlign/w:footnoteReference/w:ind/w:spacing/w:jc`.
- Wrapper app (READ-ONLY, không phát hiện marker kỹ thuật do app ghép): `app_web/ui/index.html` (`#doc-title`, brand tĩnh), `app_web/ui/render.js:536` (tab caption = `ten_mau || id`, sạch), `app_web/main.py` (chỉ bridge load/export). Marker kỹ thuật nằm trong chính block data, không phải wrapper.
- Screenshot UI: **NOT RUN** — môi trường không có browser; không cài dependency mới theo phạm vi L0.

## SUMMARY COUNTS

| Chỉ số | Giá trị |
|---|---|
| Form quét (census) | **28/28** PLII_M01–PLII_M28, đủ 100% range |
| Source-indicator `PL2 - Mau so N: …` trong blocks | **19/28** (M01–M19, luôn block idx 0) |
| Form sạch marker (block 0 = `Mẫu số N`) | **9/28** (M20–M28) |
| `Mẫu số N` hợp lệ (role=form-number) | **28/28**: M01–M19 tại blk 1 align=left (DOCX jc mặc định trái); M20–M28 tại blk 0 align=right (DOCX jc=right) |
| Block chứa `\n` (nguy cơ collapse) | **100 block / 28 form**; đối chiếu DOCX: **100 paragraph có `w:br`/`w:cr`**, khớp 1-1 theo từng form |
| Digit-glued chân footnote (ref dính chữ) | **8 form** (M01, M02, M03, M04, M05, M06, M09, M18), **17 vị trí ref** + **12 block thân footnote** dạng `N <nội dung>` |
| Run `w:vertAlign=superscript` thật trong DOCX | **54 run / 10 form** (M01–M07, M09, M10, M18) |
| `w:footnoteReference` / `word/footnotes.xml` | **0 / 0** — toàn bộ 28 mẫu KHÔNG có footnote OOXML; footnote là superscript thủ công + dòng kẻ |
| Dòng kẻ `____` nằm trong run superscript | **8 paragraph / 8 form** (M01 p149, M02 p255, M03 p23, M04 p17, M05 p18, M06 p32, M09 p16, M18 p28) |
| Run superscript rỗng (rác) | **8 run / 5 form**: M05 (p2,p3), M06 (p3), M07 (p2,p3), M09 (p2,p3), M10 (p9) |
| Bảng bị nén thành paragraph text | **1 form (M02)**: blk 72 và blk 129 — header bảng thành viên + hàng đánh số cột `Chữ ký12345678910` dính 1 run; DOCX M02 có 4 `w:tbl` |
| Block schema hiện có | chỉ `t/align/runs` (+ meta loop/chk); **không** `role`, **không** `format` |
| `w:ind` đặc biệt trong DOCX | **0/28** — không mất indent khi convert (không có gì để mất) |

Role set dùng theo PLAN: source-indicator / form-number / national-header / national-motto / national-separator / date-line / form-title / form-subtitle / salutation / body / section-heading / note / footnote / signature.

## Bảng census per form (đủ 28/28)

| form_id | category | block_idx / para | evidence | expected role/style | status |
|---|---|---|---|---|---|
| PLII_M01 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 1: Giấy đề nghị đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 1` hợp lệ | OPEN |
| PLII_M01 | hard-break collapse | blk 2, 58 ↔ 3 w:br / 2 para | `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ⏎ Độc lập - Tự do - Hạnh phúc ⏎ ---` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M01 | footnote-glue/superscript | blk33 `3. Ngành, nghề kinh doanh1:`; blk43 `5.2. Ngày bắt đầu hoạt động4 (trường hợp hộ`; blk51 `hộ gia đình đăng ký hộ kinh doanh5:`; blk58 `HỘ KINH DOANH (Ký và ghi họ tên)6` | DOCX: `w:vertAlign=superscript` (vd p33), không có `footnoteReference`; thân footnote: blk63, blk64, blk65, blk68 | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M01 | roles/format | title blk4 center; salutation blk5 center; date-line blk3 right; signature×6 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 72 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M02 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 2: Giấy đề nghị đăng ký thay đổi nội dung đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 2` hợp lệ | OPEN |
| PLII_M02 | hard-break collapse | blk 2, 3, 132 ↔ 4 w:br / 3 para | `TÊN HỘ KINH DOANH ⏎ -------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M02 | footnote-glue/superscript | blk71 `ký hộ kinh doanh sau khi thay đổi2:`; blk77 `Ý THAY ĐỔI NGÀNH, NGHỀ KINH DOANH3`; blk82 `đổi ngành, nghề kinh doanh chính6 (kê khai t`; blk109 `3. Ngành, nghề kinh doanh7:` (+2) | DOCX: `w:vertAlign=superscript` (vd p10), không có `footnoteReference`; thân footnote: blk134, blk141, blk145, blk146 | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M02 | table-flatten | blk 72 | DOCX có 4 `w:tbl`; blocks nén header + hàng số cột: `STTHọ tênNgày, tháng, năm sinhSố định danh cá nhânGiới tínhQuốc tịchDân tộcNơi t` | Cần table contract/grid thay vì paragraph phẳng; `12345678910` là số thứ tự CỘT (legit-digit, không được regex xóa) | OPEN |
| PLII_M02 | roles/format | title blk6 center; salutation blk9 center; date-line blk5 right; signature×14 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 178 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M03 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 3: Giấy đề nghị đăng ký tạm ngừng kinh doanh/tiếp tục kinh doanh trước thời hạn đã ` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 3` hợp lệ | OPEN |
| PLII_M03 | hard-break collapse | blk 2, 3, 19 ↔ 4 w:br / 3 para | `TÊN HỘ KINH DOANH ⏎ -------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M03 | footnote-glue/superscript | blk19 `HỘ KINH DOANH (Ký và ghi họ tên)1` | DOCX: `w:vertAlign=superscript` (vd p22), không có `footnoteReference`; thân footnote: không thấy block `N …` | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M03 | roles/format | title blk6 center; salutation blk8 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 24 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M04 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 4: Thông báo về việc chấm dứt hoạt động hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 4` hợp lệ | OPEN |
| PLII_M04 | hard-break collapse | blk 2, 3, 13 ↔ 4 w:br / 3 para | `TÊN HỘ KINH DOANH ⏎ -------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M04 | footnote-glue/superscript | blk13 `/NGƯỜI THỪA KẾ (Ký và ghi họ tên)1` | DOCX: `w:vertAlign=superscript` (vd p16), không có `footnoteReference`; thân footnote: không thấy block `N …` | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M04 | roles/format | title blk6 center; salutation blk8 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 18 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M05 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 5: Giấy đề nghị cấp lại Giấy chứng nhận đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 5` hợp lệ | OPEN |
| PLII_M05 | hard-break collapse | blk 2, 3, 14 ↔ 4 w:br / 3 para | `TÊN HỘ KINH DOANH ⏎ --------------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M05 | footnote-glue/superscript | blk14 `HỘ KINH DOANH (Ký và ghi họ tên)1` | DOCX: `w:vertAlign=superscript` (vd p2), không có `footnoteReference`; thân footnote: blk16 | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M05 | roles/format | title blk6 center; salutation blk8 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 19 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M06 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 6: Giấy đề nghị dừng thực hiện thủ tục đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 6` hợp lệ | OPEN |
| PLII_M06 | hard-break collapse | blk 2, 3, 28 ↔ 4 w:br / 3 para | `TÊN HỘ KINH DOANH ⏎ -------------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M06 | footnote-glue/superscript | blk24 `Là chủ hộ kinh doanh1 (Tên hộ kinh do`; blk28 `HỘ KINH DOANH (Ký và ghi họ tên)1` | DOCX: `w:vertAlign=superscript` (vd p3), không có `footnoteReference`; thân footnote: blk30, blk31 | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M06 | roles/format | title blk6 center; salutation blk8 center; date-line blk5 right; signature×4 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 34 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M07 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 7: Giấy chứng nhận đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 7` hợp lệ | OPEN |
| PLII_M07 | hard-break collapse | blk 2, 3, 34 ↔ 5 w:br / 3 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M07 | roles/format | title blk4 center; date-line blk6 center; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 47 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M08 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 8: Thông báo về cơ quan thuế quản lý trực tiếp hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 8` hợp lệ | OPEN |
| PLII_M08 | hard-break collapse | blk 2, 3, 19, 20 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ ----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M08 | roles/format | title blk6 center; salutation blk8 left; date-line blk5 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 22 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M09 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 9: Giấy chứng nhận đăng ký hộ kinh doanh (Dùng trong trường hợp cấp lại do mất, chá` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 9` hợp lệ | OPEN |
| PLII_M09 | hard-break collapse | blk 2, 3, 7, 8 ↔ 6 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ ----------------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M09 | footnote-glue/superscript | blk7 `TRƯỞNG PHÒNG1 (Đã ký)` | DOCX: `w:vertAlign=superscript` (vd p2), không có `footnoteReference`; thân footnote: không thấy block `N …` | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M09 | roles/format | title blk4 center; date-line blk8 center; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 17 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M10 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 10: Thông báo về việc sửa đổi, bổ sung hồ sơ đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 10` hợp lệ | OPEN |
| PLII_M10 | hard-break collapse | blk 2, 3, 21, 22 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ ----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M10 | roles/format | title blk6 center; salutation blk8 left; date-line blk5 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 25 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M11 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 11: Thông báo yêu cầu hộ kinh doanh báo cáo về việc tuân thủ các quy định về hộ kin` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 11` hợp lệ | OPEN |
| PLII_M11 | hard-break collapse | blk 2, 3, 24, 25 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M11 | roles/format | title blk6 center; salutation blk8 left; date-line blk5 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 28 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M12 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 12: Thông báo về việc vi phạm của hộ kinh doanh thuộc trường hợp thu hồi Giấy chứng` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 12` hợp lệ | OPEN |
| PLII_M12 | hard-break collapse | blk 2, 3, 23, 24 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M12 | roles/format | title blk6 center; salutation blk8 left; date-line blk5 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 26 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M13 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 13: Thông báo về việc chấm dứt hoạt động hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 13` hợp lệ | OPEN |
| PLII_M13 | hard-break collapse | blk 2, 3, 21, 22 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M13 | roles/format | title blk6 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 24 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M14 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 14: Quyết định về việc thu hồi Giấy chứng nhận đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 14` hợp lệ | OPEN |
| PLII_M14 | hard-break collapse | blk 2, 3, 28, 29 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M14 | roles/format | title blk6 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 31 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M15 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 15: Quyết định về việc thu hồi Giấy chứng nhận đăng ký hộ kinh doanh của lần đăng k` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 15` hợp lệ | OPEN |
| PLII_M15 | hard-break collapse | blk 2, 3, 26, 27 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M15 | roles/format | title blk6 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 29 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M16 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 16: Quyết định về việc huỷ bỏ quyết định thu hồi và khôi phục Giấy chứng nhận đăng ` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 16` hợp lệ | OPEN |
| PLII_M16 | hard-break collapse | blk 2, 3, 22, 23 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M16 | roles/format | title blk6 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 25 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M17 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 17: Giấy tiếp nhận hồ sơ và hẹn trả kết quả hồ sơ đăng ký hộ kinh doanh` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 17` hợp lệ | OPEN |
| PLII_M17 | hard-break collapse | blk 2, 3, 23, 24 ↔ 6 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M17 | roles/format | title blk6 center; date-line blk5 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 26 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M18 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 18: Giấy tiếp nhận hồ sơ và hẹn trả kết quả hồ sơ đăng ký hộ kinh doanh qua mạng th` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 18` hợp lệ | OPEN |
| PLII_M18 | hard-break collapse | blk 2, 3 ↔ 4 w:br / 2 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M18 | footnote-glue/superscript | blk21 `quyết hồ sơ: ngày … tháng … năm …1` | DOCX: `w:vertAlign=superscript` (vd p22), không có `footnoteReference`; thân footnote: blk26 | runs[] tách `{text, vertAlign:superscript, role:footnote-ref}`; thân → role=footnote | OPEN |
| PLII_M18 | roles/format | title blk6 center; date-line blk5 right; signature×0 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 29 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M19 | source-indicator | blk 0 (left) | Nguyên văn: `PL2 - Mau so 19: Thông báo yêu cầu hộ kinh doanh tạm ngừng kinh doanh ngành, nghề đầu tư kinh do` | role=source-indicator + uiHidden=true; tách khỏi `Mẫu số 19` hợp lệ | OPEN |
| PLII_M19 | hard-break collapse | blk 2, 3, 21, 22 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M19 | roles/format | title blk6 center; salutation blk8 left; date-line blk5 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 24 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M20 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 20` | role=form-number, giữ nguyên | CLEAN |
| PLII_M20 | hard-break collapse | blk 1, 2, 20, 21 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M20 | roles/format | date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 25 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M21 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 21` | role=form-number, giữ nguyên | CLEAN |
| PLII_M21 | hard-break collapse | blk 1, 2, 25, 26 ↔ 9 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M21 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 30 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M22 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 22` | role=form-number, giữ nguyên | CLEAN |
| PLII_M22 | hard-break collapse | blk 1, 2, 19, 20 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M22 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 24 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M23 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 23` | role=form-number, giữ nguyên | CLEAN |
| PLII_M23 | hard-break collapse | blk 1, 2, 20, 21 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M23 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 25 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M24 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 24` | role=form-number, giữ nguyên | CLEAN |
| PLII_M24 | hard-break collapse | blk 1, 2, 14, 15 ↔ 10 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M24 | roles/format | title blk5 center; date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 19 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M25 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 25` | role=form-number, giữ nguyên | CLEAN |
| PLII_M25 | hard-break collapse | blk 1, 2, 17, 18 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M25 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 22 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M26 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 26` | role=form-number, giữ nguyên | CLEAN |
| PLII_M26 | hard-break collapse | blk 1, 2, 23, 24 ↔ 8 w:br / 4 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center/left | OPEN |
| PLII_M26 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×1 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 28 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M27 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 27` | role=form-number, giữ nguyên | CLEAN |
| PLII_M27 | hard-break collapse | blk 1, 2, 22 ↔ 5 w:br / 3 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M27 | roles/format | title blk5 center; date-line blk4 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 27 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |
| PLII_M28 | source-indicator | blk 0 | Không có marker `PL2 - Mau so`; block 0 là `Mẫu số 28` | role=form-number, giữ nguyên | CLEAN |
| PLII_M28 | hard-break collapse | blk 1, 2, 30 ↔ 5 w:br / 3 para | `CƠ QUAN ĐĂNG KÝ KINH DOANH ⏎ CẤP XÃ ⏎ -----------` | national-header/motto/separator: render `\n` sau escape thành `<br>`, giữ align center | OPEN |
| PLII_M28 | roles/format | title blk5 center; salutation blk7 left; date-line blk4 right; signature×2 | Schema block chỉ có t/align/runs; DOCX giữ `w:spacing` trên 48 paragraph — blocks không mang lại | Gán role (form-title/form-subtitle/date-line/signature/note…) + format.spaceBefore/After/lineSpacing/keepWithNext từ OOXML | OPEN |

## Ghi chú phân loại digit-glued

- **candidate-footnote** (digit superscript thật trong DOCX, dính vào chữ trong blocks): M01 blk33 `kinh doanh1:` / blk43 `hoạt động4` / blk51 `kinh doanh5:` / blk58 `)6`; M02 blk71 `thay đổi2:` / blk77 `KINH DOANH3` / blk82 `kinh doanh chính6` / blk109 `kinh doanh7:` / blk128 `kinh doanh9:` / blk132 `)10`; M03 blk19 `)1`; M04 blk13 `)1`; M05 blk14 `)1`; M06 blk24 `kinh doanh1` / blk28 `)1`; M09 blk7 `TRƯỞNG PHÒNG1` (thân chú thích mờ: blk10 ` Không có chữ ký, con dấu tại Mục này.` không mang số → nghi orphan-ref); M18 blk21 `năm …1`.
- **candidate-legit-digit** (KHÔNG được xóa bởi regex): `PL2` trong marker; `Mẫu số 1…28`; `5.1/5.2` mục con; mã ngành cấp 4; `Chữ ký12345678910` = hàng số cột 1–10 của bảng M02; ngày/tháng/năm; `{placeholder}`.
- Thân footnote tồn tại dưới dạng block riêng `N <nội dung>` tại (12 block): M01 blk63/64/65/68, M02 blk134/141/145/146, M05 blk16, M06 blk30–31 (hai thân khác nhau cùng số `1`), M18 blk26. M03/M04/M09 có ref nhưng thân không khớp số → cần Lead quyết policy hiển thị.

## Khác biệt nguồn (DOCX) vs blocks

1. `\n`: DOCX dùng `w:br` trong 1 paragraph; blocks giữ đúng ký tự `\n` trong run — khớp về nội dung, hỏng ở tầng render HTML (collapse whitespace). Không phải lỗi converter.
2. Superscript: DOCX có `w:vertAlign`; blocks làm phẳng digit vào chuỗi → mất thông tin định dạng (root cause `Tôi là1`).
3. Spacing: DOCX giữ `w:spacing` trước/sau/line-spacing trên phần lớn paragraph (M02 nhiều nhất: 178); schema block không có trường `format` → mất toàn bộ ở tầng render.
4. Alignment: khớp tốt (jc center/right/left ↔ align center/right/left; `Mẫu số N` M20–M28 giữ right đúng nguồn).
5. Bảng: chỉ M02 mất cấu trúc bảng thành viên; M01/M07 bảng được biểu diễn bằng chuỗi block riêng, chưa audit sâu grid (ngoài phạm vi hình thức paragraph của wave này).
6. Wrapper/title/tab caption app: dùng `ten_mau` từ JSON (sạch, tiếng Việt đầy đủ) — không phát hiện app tự chèn thêm marker kỹ thuật.

## Đề xuất chuẩn hoá (cho Lead merge L0)

1. Detector marker: `^PL\d\s*-\s*Mau so\s*\d+:?` → role=source-indicator, uiHidden; whitelist `^Mẫu số \d+$` → form-number. Áp 19 form PLII; M20–M28 làm mẫu đối chiếu.
2. Render `\n` trong run thành `<br>` sau escape (hoặc pre-line scoped theo block role national-header/motto/separator) — sửa 100 block/28 form một lần ở renderer, không sửa data.
3. Converter phải emit `runs:[{text, vertAlign}]` từ `w:vertAlign` và role=footnote-ref; thân footnote nhận diện `^\d\s+` → role=footnote. Riêng M09 xác minh orphan-ref; M06 có 2 thân cùng số `1` → cần numbering ổn định trước khi render `<sup>` tooltip.
4. Bổ sung `format.{spaceBeforePt,spaceAfterPt,lineSpacing,keepWithNext}` từ `w:spacing`/`w:keepNext`; `w:ind` không phát sinh ở PLII nhưng vẫn implement cho đồng nhất 87 mẫu.
5. M02: chuyển 2 đoạn bảng thành viên về table contract (grid) — hiện đang là defect cấu trúc, không chỉ hình thức.
6. Dọn run rác: 8 superscript rỗng + 8 dòng kẻ trong run superscript — đưa vào allowlist detector để tránh false positive `Tôi là1`.

## NOT RUN

- Screenshot UI (không browser/không cài dependency) — census dựa hoàn toàn blocks + OOXML + code đọc wrapper.
- Không chạy test suite production (read-only; chỉ tạo 2 file fragment).