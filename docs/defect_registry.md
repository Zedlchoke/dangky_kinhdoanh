# Defect registry — Wave D2 Defect Hunt (lệnh owner 2026-08-28)

> Owner lệnh: các lớp lỗi hiển thị/nội dung phải được **identify tận gốc rồi
> loại bỏ** trước khi bàn giao — không vá tay từng mẫu. Sổ này track từng lớp
> lỗi: bằng chứng → gốc rễ → cách sửa → trạng thái. Một lớp lỗi = một fix hệ
> thống + test/census chống hồi quy, KHÔNG sửa từng file generated.

## Class 1 — Checkbox dẹt thành text (BHXH "3 tháng một lần")

- **Bằng chứng:** owner báo thiếu checkbox "3 tháng" cho phương thức đóng
  BHXH. Nguồn Word PLI_M01 mục 7 có "Phương thức đóng BHXH (chọn 1 trong 3
  phương thức)" + "□ 3 tháng một lần"; blocks PLI_M01 b132 là `p body` text
  "□ 3 tháng một lần" (không tick được) giữa 2 block `chk` chuẩn.
- **Gốc rễ:** `build_form_maps.process_checkboxes` chỉ gắn the `{chk_*}` khi
  nhãn khớp whitelist `CHK_RULES`; "3 thang mot lan" (không số 0 đầu) không
  khớp rule "03 thang mot lan" → glyph ở lại nguyên văn.
- **Fix hệ thống:** rule `0?3/0?6 thang mot lan` + fallback `_auto_chk_key`
  (mọi ô □/☐ không khớp rule đều được gắn the `chk_auto_<slug>`, dedupe).
  Không phụ thuộc whitelist nữa — lớp lỗi xóa sổ.
- **Trạng thái: FIXED** @ `ba64f29` — regen 4 mẫu (M01/M02/M15/PLII_M02),
  6 glyph → 6 chk, sandbox 0 glyph, visual re-shoot 4/4
  (`generated_ho_so/_visual_layout/chkfix/`), runner 46/0/0.

## Class 2 — Đứt đánh số mục / mất mục giữa các mẫu companion

- **Bằng chứng:** owner báo M09 (tab Danh sách thành viên công ty hợp danh)
  nhảy mục 6 → mục 8, mất mục 7. Census `tools/census/numbering_audit.py`:
  CHAIN GAP M03→M06 (6→8), M04→M08 (7→10), M05→M09 (6→8); M09 còn thiếu cả
  mục 1..7 và nhiễm lặp "I./1." (vùng p103-p222, D3.1).
- **Gốc rễ:** nguồn docx các mẫu chính bị CẮT (M03 hết mục 6, M04 hết 7,
  M05 hết 6 — D1.3/D1.5 cũ) trong khi companion (DS thành viên/cổ đông)
  tiếp tục đánh số từ mục 8/10 theo biểu mẫu gốc.
- **Fix:** rebuild theo Phụ lục I TT 68 (lệnh owner 2026-08-28) — lane
  `cap-von` (M03/M04/M05/M12 + thuế PLII_M02) và lane `m09-rebuild` (M09 14
  cột + đánh số liên tục). Sau merge: đăng ký `numbering_audit --gate` vào
  release_runner (EXCEPTIONS rỗng).
- **Trạng thái: IN FIX** (3 lane đang chạy).

## Class 3 — GLUE chữ số chú thích chân trang trong heading/body

- **Bằng chứng:** census GLUE 23/87 mẫu: "9. Thông tin về việc đóng bảo hiểm
  xã hội7:", "11. Thông tin về chủ sở hữu hưởng lợi của doanh nghiệp14:"…
  (số chú thích superscript bị flatten dính vào chữ).
- **Gốc rễ:** extractor L1 (docx_to_blocks) chưa có rule tách superscript
  footnote khỏi run text — gap V3 đã ghi ở Wave D audit lần 1.
- **Fix dự kiến:** rule V3 ở `docx_to_blocks.py` (Lead sở hữu) — khôi phục
  ký hiệu chú thích (D7.2=A) hoặc tách run superscript; regen toàn cục +
  visual re-shoot + runner. Chạy SAU batch-1 merge để regen gộp một đợt.
- **Trạng thái: OPEN** (Lead, xếp hàng sau batch-1).

## Class 4 — Layout header: TÊN DN/HKD + quốc hiệu xếp dọc

- **Bằng chứng:** nguồn docx PLII_M02 P2–P5 xếp dọc, "Số:" căn GIỮA (sai);
  bản Word gốc (PLII Mẫu 2 / PLI Mẫu 13): band 1 tên TRÁI + quốc hiệu PHẢI,
  band 2 "Số:" TRÁI + ngày-tháng-năm PHẢI.
- **Fix:** lane `hdr2col` — tái cấu trúc header thành bảng không viền 2 cột
  ở lớp build_form_maps (cấm sửa tay generated); Lead regen + visual re-shoot
  từng mẫu ảnh hưởng (UI + DOCX qua Word).
- **Trạng thái: IN FIX** (lane đang chạy).

## Class 5 — "Vấn đề nhập trong bảng ngành nghề" (chưa tái hiện được)

- **Bằng chứng probe 2026-08-28 (Playwright trên snapshot thật):** PLI_M05
  `ds_nganh` render bảng có `data-loop`, nút "[+ Thêm dòng]" hoạt động
  (3→4 hàng), gõ được vào ô (DOM nhận "0110"), 0 page error. Suite
  `test_industry_formation` phủ M01/M03/M04/M05 end-to-end 9/0 PASS;
  `test_p3_e2e` P3-RP5 phủ loop dùng chung 4 mẫu.
- **Kết luận trung thực:** KHÔNG tái hiện được lỗi ở tầng renderer/runtime
  cho M05. Cần owner chỉ rõ: mẫu nào, bước nào, hiện tượng gì (không gõ
  được / mất dữ liệu khi chuyển tab / không in ra DOCX / thiếu tra cứu VSIC /
  bảng không hiện?).
- **Trạng thái: NEEDS OWNER CLARIFICATION.**

## Class 6 — Số mồ côi trong PDF xuất (bảng thuế bị dẹt ở mẫu NGOÀI 5 nhóm)

- **Bằng chứng:** owner duyệt `generated_ho_so/_visual_layout/hdr2col/pdf/PLII_M06.pdf`
  (Word render bản export thật) và báo "có các số lẩn lơ mất thẩm mỹ" — các số
  "4/5/6/1/2" đứng riêng một dòng quanh mục 6 Thông tin đăng ký thuế.
- **Gốc rễ:** census blocks PLII_M06 KHÔNG có paragraph số standalone — các số
  đó là STT/số mục của BẢNG CHỈ TIÊU THUẾ bị dẹt thành text ở nguồn (mẫu
  tạm ngừng HKD — KHÔNG thuộc 5 nhóm được duyệt rebuild, các lớp fixed-matrix
  thuế của nhóm này còn BLOCKED).
- **Hướng xử lý:** cần owner mở phạm vi rebuild bảng thuế cho nhóm PLII_M03–M06
  (tạm ngừng/chấm dứt HKD) theo TT 68/121, hoặc chấp nhận REMAP các số tàn dư
  vào layout dạng danh sách như bản gốc. KHÔNG tự mở phạm vi.
- **Trạng thái: CẦN OWNER CHỐT PHẠM VI.**

## Class 7 — Chữ ký không có chỗ trống để ký

- **Bằng chứng:** owner: "ký họ tên phải chừa chỗ ra cho đúng để người ta ký".
  Blocks PLII_M06 b25 `signature` = "CHỦ HỘ KINH DOANH\n(Ký và ghi họ tên)1"
  — không có khoảng trống dọc nào trên chữ ký; bản Word gốc có 2–4 dòng trắng.
- **Gốc rễ:** extractor giữ nguyên đoạn nguồn không có dòng trống; renderer
  không cộng thêm chỗ ký. (Glue số "1" sau "(Ký và ghi họ tên)" = Class 3.)
- **Hướng xử lý:** rule layout cho block role `signature` (spaceBefore hoặc
  N dòng trắng) ở extractor/renderer — thuộc đợt V3/GLUE + P5R gate G5/G7.
- **Trạng thái: OPEN** (xếp hàng đợt extractor V3, Lead sở hữu).

## Class 8 — Dấu X checkbox rơi riêng dòng trong PDF xuất

- **Bằng chứng:** PLII_M06.pdf: "Khấu trừ" / "X" tách 2 dòng; "Có X" và
  "Không X" mỗi cái một dòng (bản gốc in "Có □  Không □" cùng hàng).
- **Gốc rễ:** template đặt nhãn và ô {chk_*} ở paragraph kế nhau; export
  docxtemplater đổ giá trị "X" xuống dòng riêng. Cần gộp nhãn+tag cùng
  paragraph ở template/extractor, hoặc renderer chk ghép inline.
- **Trạng thái: OPEN** (Lead, đợt layout DOCX cùng Class 7).

## Phương pháp chống hồi quy cho Wave D2

- `tools/census/numbering_audit.py` (JUMP/CHAIN/GLUE) — inventory hiện tại,
  lên **gate** trong release_runner khi Class 2/3 đóng (EXCEPTIONS rỗng).
- Census glyph □/☐ = 0 trong mọi block — đã xanh từ `ba64f29`, sẽ ghép vào
  audit suite khi đăng ký gate numbering.
