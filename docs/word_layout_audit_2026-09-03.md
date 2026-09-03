# Word layout audit — 2026-09-03

## 1. Kết luận

**VISUAL LAYOUT: FAIL.** Corpus hiện tại mở được bằng Word không đồng nghĩa với
bố cục đúng. Các ảnh owner cung cấp đã được tái hiện/đối chiếu với corpus export
mới nhất và cho thấy lỗi hệ thống ở metadata, chữ ký, phân trang và bảng.

Không được dùng các gate structural, số lượng bảng, XML parse, hay ảnh chụp duy
nhất trang 1 để tuyên bố visual PASS.

## 2. Phạm vi và phương pháp

- Repo: `main@403ca1a`; working tree có thay đổi Phase 5 chưa commit của lane
  khác. Vì vậy kết quả này mang nhãn `AUDITED_WIP_CORPUS`, chưa phải release
  baseline tái lập chỉ từ HEAD.
- Corpus: 86 output trong
  `generated_ho_so/phase5_word_open_20260903_180625/` cộng 5 biến thể M72 trong
  các thư mục `phase5_word_open_*_20260903_1809*`.
- Tổng: **91 DOCX, 91 PDF, 264 trang**.
- Đường sinh file của corpus: `Bridge.export -> write_rendered -> LibreOffice
  normalize` theo `tools/phase5_export_corpus.py`.
- Tất cả 91 DOCX được convert lại bằng LibreOffice. Toàn bộ 264 trang được render
  thành contact sheet và xem; trang nghi vấn được render lại độ phân giải cao.
- Kiểm máy bổ sung: marker template, `undefined/null/NaN`, nhãn nguồn, field
  code, trang trắng/thưa, content vượt page box và dấu hiệu tách khối ký.
- Word 16.16.27 inventory hiện ghi **91/91 PASS_OPEN_DIRECT**. Đây chỉ là gate
  mở file, không phải gate layout.

## 3. Defect ledger

| ID | Mức | Trạng thái | Lỗi và bằng chứng |
|---|---|---|---|
| WLAY-001 | P0 | CONFIRMED | `role=source-indicator` bị ẩn trên UI nhưng lộ trong DOCX ở **44 form**, ví dụ ảnh owner `PL2 - Mau so 9...`. |
| WLAY-002 | P0 | CONFIRMED | Chữ ký hai cột sập thành hai hàng dọc. `PLI_M70` template sinh bảng **2x1** thay vì hai signer song song; ảnh owner và XML cùng xác nhận. |
| WLAY-003 | P0 | CONFIRMED | Khối ký bị cắt qua trang. Xác nhận rõ ở `PLII_M06`, `PLII_M17`, `PLII_M22`, `PLII_M23`, `PLI_M42`, `PLI_M43`; các trang thưa khác phải review theo danh sách dưới. |
| WLAY-004 | P0 | CONFIRMED | Không có vùng viết chữ ký hợp lý. `PLI_M15` đặt `CHỦ SỞ HỮU MỚI` và `CHỦ SỞ HỮU CŨ` nối dọc, gần như không có khoảng viết; ảnh owner xác nhận. |
| WLAY-005 | P0 | CONFIRMED/BLOCKED_OWNER | Fixed matrix bị làm phẳng hoặc thiếu. `PLI_M12` trang 7–8 hiện các nhãn và STT rời thay vì bảng tài sản/vốn/cổ phần dùng được. Nguồn DOCX cũ cũng đã phẳng nên cần source pháp lý/cấu trúc được owner duyệt trước khi rebuild. |
| WLAY-006 | P0 | CONFIRMED | `PLII_M28` trang 2 lộ literal `PAGE \\* MERGEFORMAT 2`. |
| WLAY-007 | P0 | CONFIRMED | Trang/boundary thừa: `PLI_M72_tnhh_2tv` có trang 3 trắng; `PLI_M80` kéo cả tiêu đề `PHỤ LỤC II...` của phần kế tiếp sang trang 3. |
| WLAY-008 | P1 | CONFIRMED/CENSUS_OPEN | Bảng quá rộng làm header/cell vỡ thành cụm 1–3 ký tự. Thấy rõ ở các bảng thành viên/cổ đông M72 và một số form 10–15 cột như `PLI_M02`, `M06`–`M11`, `M13`, `M15`. Cần đối chiếu source từng bảng để chọn landscape, split table hay width/font policy. |
| WLAY-009 | P1 | CONFIRMED/CENSUS_OPEN | Orphan page: chữ ký, một dòng hoặc footnote bị đẩy riêng sang trang gần trống. Thấy ở `PLII_M01`, `M10`, `M17`, `M19`, `M22`, `M23`, `PLI_M13`, `M29`, `M42`, `M43`, `M45`, `M48`, `M50`, `M51`, `M53`, `M55`, `M57`, `M70`, một số M72. |
| WLAY-010 | P1 | CONFIRMED | Fixture visual dùng `TEST` và có thể tick mọi lựa chọn loại trừ nhau; ảnh owner cho thấy nhiều loại giấy tờ đều `X`. Fixture này không đại diện hồ sơ hợp lệ và che/mạo tạo lỗi layout. |
| WLAY-011 | P1 | OPEN | Có nhiều chuỗi dính quanh dữ liệu mẫu (`TESTTEST`, thiếu khoảng giữa label/value). Kết quả regex trên fixture toàn `TEST` nhiễu cao; phải thay fixture semantic rồi mới census chính xác. |
| WLAY-012 | P0 process | CONFIRMED | Gate chứng minh sai: inventory chữ ký chỉ kiểm blank paragraph/spacing và một vài ảnh trang 1 nhưng ghi `signature_fail: 0`. Gate phải tách `OPEN_DIRECT`, `STRUCTURAL`, `SOURCE_FIDELITY`, `VISUAL_LAYOUT`. |

## 4. Danh sách chính xác WLAY-001

44 form lộ source indicator ở trang 1:

`PLII_M01`–`PLII_M19`; `PLI_M01`, `PLI_M02`, `PLI_M05`, `PLI_M06`,
`PLI_M07`, `PLI_M08`, `PLI_M09`, `PLI_M10`, `PLI_M11`, `PLI_M17`,
`PLI_M23`, `PLI_M25`, `PLI_M27`, `PLI_M28`, `PLI_M29`, `PLI_M30`,
`PLI_M31`, `PLI_M32`, `PLI_M33`, `PLI_M42`, `PLI_M43`, `PLI_M45`,
`PLI_M46`, `PLI_M47`, `PLI_M48`.

## 5. Kết quả detector không phát hiện lỗi

- Marker `{...}` lộ ra output: **0**.
- Literal `undefined`, `null`, `NaN`: **0**.
- Text block vượt page bounding box trong PDF LibreOffice: **0**.

Ba kết quả này chỉ đóng đúng ba loại lỗi tương ứng; không suy rộng thành visual
PASS. Ảnh Word owner chụp có thể khác pagination LibreOffice, vì vậy sau khi
sửa vẫn phải chạy lại cả Word và LibreOffice/PDF.

## 6. Giới hạn và trạng thái các form còn lại

- Các form không có tên trong ledger chỉ đạt
  `VISUAL_REVIEWED_NO_DEFECT_AT_CONTACT_SHEET_RESOLUTION`; chưa đạt final PASS
  cho tới khi đối chiếu source fidelity và chụp đầy đủ tất cả trang trong Word.
- Các trang thưa là tập ứng viên, không tự động là lỗi: trang footnote dài có
  thể hợp lệ. Chỉ đóng sau khi so với mẫu nguồn và áp dụng quy tắc orphan-page.
- Ảnh owner `Đăng ký thay đổi...` bị cắt bên phải có thể do viewport Word, trong
  khi PDF scan chưa thấy object vượt page box; chưa ghi thành overflow defect.
- Nội dung pháp lý/bảng không có source đáng tin phải giữ `BLOCKED_OWNER`, không
  tự sáng tác cột hoặc hàng để làm đẹp.

## 7. Verdict hiện tại

| Gate | Kết quả |
|---|---|
| DOCX package/open direct Word | **PASS 91/91** theo inventory hiện có |
| LibreOffice convert corpus | **PASS 91/91** |
| Toàn bộ trang đã được xem ở contact-sheet resolution | **PASS 264/264** |
| Word visual layout | **FAIL** — WLAY-001..012 |
| Source fidelity từng form | **NOT RUN đầy đủ** |
| Windows Word/.exe smoke | **NOT RUN** |

