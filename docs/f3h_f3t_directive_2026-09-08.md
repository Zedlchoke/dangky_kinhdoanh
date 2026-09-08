# LỆNH TRIỂN KHAI F3H + F3T — từ owner qua side chat, 2026-09-08

> Owner xác nhận: **triển khai F3H + F3T ngay** theo PLAN.md mục F3H/F3T
> (đã reopen 2026-09-08). File này là chỉ thị điều phối cho main session —
> xóa mục này khỏi "câu hỏi chờ" và bắt đầu thực thi. Trình tự bắt buộc:
> F3H + F3T → corpus mới → F5 AI/human review → F7 auditor.

## 0. Trạng thái đang chạy phải xử lý trước

| Agent/việc | Quyết định |
|---|---|
| Render-fix agent (M10 width + M05 token + M01 data-row + M72 fragment) | Cho **hoàn tất M10 + M05 + M72 fragment** (độc lập F3T/F3H). **DỪNG phần M01 data-row vá riêng** — đó là biểu hiện của F3T.1 (`_expand_loops`), xử lý trong F3T lane. Nếu agent đã fix M01 thì để nguyên nhưng KHÔNG coi là đóng F3T. |
| 7 judge wave-2 (batch 6–12) | Để chạy hết; verdict files /tmp/f5_verdicts/batch_*.json vẫn thu về làm **findings đầu vào** cho review trên corpus mới (không đóng gate F5). |
| F5 verdicts đã thu (150 record) | Giữ làm findings; gate F5 phải chạy lại trên corpus mới sau F3H+F3T. |

## 1. F3T lane (TABLE-ROW-PLACEMENT) — theo ownership F3T.5

- **Lane C**: `tools/docx_render.py::_expand_loops` — hợp đồng `max(K,N)`
  (N data điền từ hàng đầu, K−N trắng sau; blank không STT; N≥K không append).
  Detector structural/PDF + mutation đỏ cho từng case F3T.4.
- **Lane B**: UI/store/export payload parity — `render.js` đã đúng, kiểm
  đồng bộ store/_row_id/radio/discriminator; parity test UI↔DOCX↔PDF.
- **Lane A (read-only)**: census 47 loop/26 form blankRows tại HEAD →
  inventory động sau fix; classification mode cho ngoại lệ K-blank cố định
  (phải có source-evidence, cấm allowlist mù).
- **Lead**: merge A→B→C, cập nhật Q-P4-2 + row_contract_inventory theo hợp
  đồng mới, regen ×2 zero-diff, allowlist, runner, corpus mới.
- Production anchors tối thiểu: M72 đủ 5 variant, PLII_M01, PLII_M02,
  PLI_M02, PLI_M10, PLI_M12, PLI_M27, PLI_M79, PLI_M80.
- Fixture engine phải production-like: header + K blank + marker; pin
  (K,N)=(4,0),(4,1),(4,4),(4,6),(5,2). Suite cũ `test_row_contract_export`
  phải nâng cấp để bắt được K+N (hiện 8/8 là blind spot).

## 2. F3H lane (HEADER-SUBJECT-SEMANTICS)

- **Census occurrence-level từ ảnh nguồn pháp lý hiện hành** (9 mẫu TT121
  dùng source 2026): mọi occurrence "TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH"
  được gán 1 trong 5 role (required_band_mirror / required_band_input /
  no_subject_band / legal_title_or_subtitle / output_mirror) + subject_kind +
  canonical key + label_required + blank_policy + số input/mirror kỳ vọng.
- Fixture phân biệt bắt buộc: **PLI_M31** (giữ band + điền dưới nhãn),
  **PLI_M72** (0 band, cấm tự thêm); PLI_M33/PLII_M06 (band_input),
  PLI_M32 (mirror A→B).
- Detector hard mới (tách khỏi D17): BAND_REQUIRED_MISSING,
  BAND_FORBIDDEN_PRESENT, BAND_LABEL_REMOVED, BAND_VALUE_OR_SLOT_MISSING,
  BAND_WRONG_KEY, DUPLICATE_EDITABLE, STALE_MIRROR, LEGAL_SUBTITLE_MUTATED
  + mutation từng case phải đỏ.
- UX: tên nhập đúng 1 lần theo role; DOCX giữ nhãn pháp định + giá trị/slot
  điền nhìn thấy; bản rỗng được xuất phải còn fill-line.

## 3. Merge order & gates

1. Render-fix hoàn tất M10/M05/M72-fragment (merge trước, độc lập).
2. F3T lanes A(census) → C(_expand_loops+detector) → B(parity) — Lead merge
   từng lane, regen ×2 zero-diff, exact allowlist, runner.
3. F3H lanes (census → registry → converter/UI theo role → detector mới +
   mutation) — Lead merge tương tự.
4. Corpus mới (phase8f sau hai wave) từ HEAD sạch; visual gate HARD 0 +
   candidate adjudicated 0; Word-open inventory động; determinism.
5. F5 review lại trên corpus mới (tận dụng findings đã thu); F7 auditor.

Gate G3/G4/G5 mới đã cập nhật trong PLAN.md — không tuyên bố PASS thiếu
evidence; Word/visual chưa chạy thì ghi NOT RUN.
