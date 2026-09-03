# Phase 5R — sửa hoàn chỉnh Word layout

Tài liệu này là kế hoạch có hiệu lực cho Word/DOCX layout. Bằng chứng đầu vào:
`docs/word_layout_audit_2026-09-03.md`.

## 1. Definition of done

Phase 5R chỉ được đóng khi tất cả điều kiện sau cùng đúng trên một commit sạch:

1. 87 form canonical và đủ 5 biến thể M72 export qua đường production.
2. Word mở trực tiếp **91/91**, không dialog recovery.
3. Mọi trang output được render và review; evidence map chỉ đến từng
   `form/variant/page`, source và fixture.
4. 0 source indicator, 0 field-code literal, 0 marker, 0
   `undefined/null/NaN`, 0 trang trắng ngoài allowlist có lý do.
5. Mọi chữ ký giữ đúng số cột/orientation của source, không tách title khỏi dòng
   hướng dẫn và có vùng viết đủ theo contract.
6. Mọi bảng bắt buộc có đủ cột/hàng pháp định, đọc được, không có header/cell
   vỡ thành ký tự rời; bảng rộng có policy được duyệt và test.
7. Không có next-form/next-appendix contamination; footnote/legal note không bị
   orphan trái contract.
8. Coverage 111/111 drift=0, row contract, numbering, deep idempotency,
   compileall, manifest và release runner đều xanh.
9. Auditor độc lập xác minh lại từ commit sạch. Structural PASS không thay thế
   visual PASS; Word, LibreOffice/PDF và Windows ghi riêng PASS/FAIL/NOT RUN.

## 2. Rào chắn trước khi sửa

- Hiện `main@403ca1a` có thay đổi Phase 5 chưa commit trong production/tests.
  Lead phải yêu cầu lane hiện tại commit hoặc ghi handoff/diff allowlist trước;
  không chồng sửa lên các file dirty.
- Chụp `git status --short`, HEAD, tool versions, hashes corpus và inventory
  trước mỗi batch.
- Không sửa tay `app/templates/**`, `app/data/blocks/**`, `form_maps.*` hoặc
  manifest. Lead giữ quyền regen một lần sau khi lane nguồn đã merge.
- Không hạ assertion, tăng allowlist, xóa nội dung pháp lý hoặc thêm bảng/cột
  không có source chỉ để gate xanh.

## 3. Phase 5R0 — dựng gate visual có thể tin

Owner: Lead/infrastructure. Không mở lane sửa production trước khi gate đỏ tái
hiện các ảnh owner.

1. Nâng corpus runner để sinh năm fixture tách biệt:
   - `empty-paper`: tất cả field trống hợp lệ;
   - `valid-minimal`: hồ sơ tối thiểu hợp lệ;
   - `valid-full`: đủ grid/section active;
   - `long-boundary`: dữ liệu sát giới hạn, nhiều dòng để ép pagination;
   - `choice-variants`: mỗi radio/exclusive group đúng một lựa chọn.
2. Manifest evidence cho từng file: source hash, template hash, fixture hash,
   DOCX hash, Word-open result, PDF/page count, screenshot từng trang và verdict.
3. Thêm detector/test đỏ tối thiểu:
   - source-indicator và next-form contamination;
   - Word field code còn literal;
   - unexpected blank/sparse page;
   - signer count/orientation và signature keep-together;
   - table grid/width/readability, field/column fidelity;
   - placeholder adjacency/spacing;
   - checkbox/radio exclusivity trong fixture.
4. Gate visual chỉ nhận PASS khi reviewer đã xem tất cả trang. Ảnh trang 1 hoặc
   đếm XML không được tự nâng thành PASS.

Exit: WLAY-001..012 đều có test đỏ hoặc mục `BLOCKED_OWNER` chỉ rõ source/decision
thiếu; corpus và lệnh chạy tái lập được từ checkout sạch.

## 4. Phase 5R1 — batch P0 metadata và boundary

Sửa theo nguồn chung, regen toàn bộ một lần:

1. Loại `role=source-indicator` khỏi DOCX builder/export, không chỉ khỏi UI.
   Negative test bao phủ đủ 44 form đã bắt được và toàn corpus.
2. Materialize hoặc loại field code page-number đúng OOXML; pin
   `PLII_M28` không còn `PAGE \\* MERGEFORMAT` literal.
3. Sửa extractor boundary của `PLI_M80`; không đưa tiêu đề phụ lục/mẫu kế tiếp
   vào blocks/template hiện tại.
4. Xử lý trang trắng M72 từ section/page-break cuối, không xóa paragraph bắt
   buộc cuối table một cách mù quáng.

Exit: detector 0 leak; source/template/block regen idempotent; review lại mọi
trang của 44 form và các form boundary.

## 5. Phase 5R2 — signature contract và pagination

1. Định nghĩa `signature_block` có schema: signer count, rows/columns,
   alignment, title, instruction, minimum writing height, `keepTogether` và
   `allowPageBreakBefore`.
2. Rebuild `PLI_M70` thành hai signer ngang theo evidence nguồn/owner; test phải
   fail với 2x1 và pass với layout đúng.
3. Sửa `PLI_M15` để từng signer có vùng viết rõ, không xếp title nối nhau.
4. Áp OOXML pagination có chủ đích (`keepNext`, `keepLines`, `cantSplit` hoặc
   container table phù hợp). Không hard-code page break theo fixture.
5. Census 87 form để xác nhận mọi block ký; ưu tiên danh sách WLAY-003/009.
   Long-boundary fixture phải chứng minh block chuyển cả khối sang trang mới.

Exit: 0 signer-title/instruction split; 0 signature-only orphan page; orientation
và khoảng viết khớp source/contract trên cả Word lẫn PDF render.

## 6. Phase 5R3 — fixed matrix và bảng rộng

Thực hiện theo domain, sau khi source/owner decision rõ:

1. `PLI_M12`: lập bảng source-evidence cho từng matrix tài sản/vốn/cổ phần;
   rebuild từ spec, không sao chép text đã flatten.
2. Census các form có bảng 10+ cột. Với từng bảng, chọn một policy có bằng
   chứng: landscape section, split thành hai bảng có khóa lặp, đổi kích thước
   giấy/margin/font trong ngưỡng, hoặc giữ portrait nếu source chứng minh đọc
   được.
3. Pin header repeat, `cantSplit` row, width sum, min readable font, vertical
   alignment, nested-grid và row/blank-row contract.
4. Mỗi bảng phải đối chiếu `source -> spec -> form_maps -> UI -> payload ->
   DOCX`; không chỉ kiểm số `w:tbl`.

Exit: không còn matrix thiếu/phẳng và không có cột/header không đọc được.
Trường thiếu căn cứ pháp lý vẫn là `BLOCKED_OWNER`, không tính PASS.

## 7. Phase 5R4 — typography, spacing và orphan pages

1. Chạy fixture semantic để lập census thật cho label/value glue; sửa ở
   run/paragraph assembly, không chèn space mù vào mọi placeholder.
2. Định nghĩa orphan-page policy cho footnote/legal note/signature; compare page
   count và block flow với source, không ép tất cả tài liệu ít trang hơn.
3. Chuẩn hóa paragraph spacing, tab stops, underline/blank writing line,
   checkbox glyph và baseline/superscript.
4. Re-run empty/minimal/full/long/choice fixtures để phát hiện fix một case làm
   hỏng case khác.

Exit: WLAY-008..011 đóng hoặc có owner block rõ; không còn regression typography
trên contact sheet và high-resolution review.

## 8. Worktree và agent topology

Chỉ tạo lane sau 5R0 và khi main sạch. Mỗi lane dùng worktree riêng, không dùng
chung generated files.

| Lane | Branch | Quyền file | Không được sửa |
|---|---|---|---|
| A metadata/boundary | `agent/p5r-metadata` | extractor, DOCX source-role logic, test WLAY-001/006/007 | generated, manifest, PLAN |
| B signature | `agent/p5r-signature` | signature spec/builder/renderer và test WLAY-002/003/004 | extractor của A, generated |
| C tables | `agent/p5r-tables` | domain specs/builder tests cho WLAY-005/008 sau owner decision | global regen, PLAN |
| D audit read-only | `agent/p5r-audit` | evidence/report only | production và generated |

Lead merge tuần tự A -> regen/gates -> B -> regen/gates -> C -> regen/gates.
Lane D không tự merge và không được audit chính code do mình viết. Nếu A/B cùng
chạm một renderer, tách theo batch tuần tự thay vì merge xung đột.

Mỗi lane handoff: base/head, commits, `git diff --name-only`, files touched,
test PASS/FAIL/NOT RUN, evidence paths, risks và owner blockers. Sau merge Lead
chạy lại gate trên main rồi mới dọn worktree.

## 9. Commands/gates bắt buộc

Agent phải đọc lệnh canonical hiện có trong repo; không bịa tên suite. Bộ gate
tối thiểu sau mỗi merge:

```bash
python3 -X utf8 -m compileall app app_web tools
python3 -X utf8 -m tools.release_runner
python3 -X utf8 tools/census/check_layout_l1.py
python3 -X utf8 -m tools.census.numbering_audit --gate
python3 -X utf8 tools/test_generator_deep_idempotency.py
python3 -X utf8 -m tools.census.table_coverage_audit
```

Sau đó chạy corpus production, Word-open loop, LibreOffice/PDF render và visual
review 91 output. Nếu tên CLI tại HEAD khác, ghi đúng lệnh tìm được và kết quả;
không đánh dấu PASS cho command không chạy.

## 10. Final audit và điểm dừng

Auditor độc lập nhận commit sạch, không nhận verdict của các lane. Auditor:

1. regen từ đầu và kiểm tra git zero-diff;
2. chạy full automated matrix;
3. mở Word 91/91;
4. xem tất cả trang của cả năm fixture bắt buộc, ít nhất empty/minimal/full cho
   toàn corpus và long/choice cho form liên quan;
5. đối chiếu source fidelity của mọi defect đã sửa;
6. công bố PASS/FAIL/NOT RUN từng gate và danh sách form/page còn lỗi.

Kết thúc Phase 5R phải báo commit, diff allowlist, corpus/evidence path, số
form/trang, defect closed/open, owner decisions và môi trường chưa chạy. **Dừng
trước Phase 6/Excel/Windows packaging** cho tới khi owner duyệt báo cáo Phase 5R.
