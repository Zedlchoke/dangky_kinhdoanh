# Owner decision packet — 2026-09-03 @ main `2593e3e`

> Gom TẤT CẢ quyết định đang chờ owner theo đúng format: vấn đề → bằng chứng
> nguồn → lựa chọn → khuyến nghị → hậu quả. Trong lúc chờ, phần việc không phụ
> thuộc quyết định đã chạy tới hạn (xem cuối file). Số liệu đo tại HEAD nêu trên.

## P1 — Phần đuôi bị cắt của PLI_M03/M04 (D1.3/D1.5/D3.3)

- **Vấn đề:** nguồn `DN_PL1_Mau_03/04` (thư mục `02_chuyen_doi_hkd_sang_dn/`)
  mất toàn bộ phần đuôi mẫu: M03 còn mục 1–7 (mất 8–11: NĐDPL, thuế 9.1–9.9,
  BHXH 10, CSHHL 11); M04 còn 1–9 (mất 10–13). Chain mục 7/8–9 đã khôi phục ở
  `fe0c680` (spec `inserts`, nguyên văn para 847/1161/1162 của bản gốc).
- **Bằng chứng:** đo trực tiếp — DN_M03 116 dòng vs bản gốc full 226 dòng;
  DN_M04 149 vs 260. Bản gốc `_Bieu_mau_PL_I_II_full.docx` nằm ngay trong repo.
- **Lựa chọn:**
  - A) Swap nguồn sang bản tách từ bản gốc + regen + mở implementation đuôi
    (thuế/BHXH/CSHHL) theo wave riêng.
  - B) Giữ nguyên trạng thái cắt (chỉ 1–7 / 1–9 như hiện tại).
  - C) Regen với bản đầy đủ nhưng phần đuôi chỉ là paragraph output (không
    implement input) — hồ sơ in đủ, app chưa khai được.
- **Khuyến nghị:** C ngay (trung thành nguồn, chi phí thấp), A cho wave sau.
- **Hậu quả:** A = phạm vi +2 fixed-matrix/checkblock mỗi mẫu, ~1–2 wave; B =
  hồ sơ in thiếu mục so với mẫu gốc (risk pháp lý khi đối chiếu); C = DOCX đầy
  đủ hơn, UI chưa nhập được đuôi, coverage matrix +~10 section mới.

## P2 — Lưới thành viên PLII_M02 (ghim occurrence) + M72 N2–N5

- **Vấn đề:** 2 lưới thành viên PLII_M02 (a4/c7) và 4 lưới cổ đông M72
  (N2–N5) chưa có bảng thật trong template — header còn là paragraph dán chữ
  (`STTHọ tên…` ×2 + `STTTên cổ đông…` ×2 + digit-run `12345678910` ×2, gate
  L1 (e)/(f) đỏ đúng 6 vị trí này).
- **Bằng chứng:** `check_layout_l1` @ `2593e3e`; blocks PLII_M02 chỉ có 4 loop
  ngành; coverage matrix adjudicate a4/c7 "PARTIAL_COLUMNS" là over-bridge.
- **Lựa chọn:** A) mở rebuild theo mẫu hiện hành (nested-grid, D2.1/D2.9);
  B) giữ BLOCKED_OWNER.
- **Khuyến nghị:** A — hợp nhất với quyết định D2.9=A (prefix theo variant).
- **Hậu quả:** A = hết 6 vị trí L1 đỏ, thêm 6 section implemented; B = gate L1
  giữ exception owner, P5R G3 phải ghi exception.

## P3 — Bảng thuế PLII_M03–M06 số mồ côi (Class 6)

- **Vấn đề:** dấu hiệu bảng thuế bị làm phẳng thành số mồ côi trên 4 mẫu đổi
  thông tin thuế; chưa có rebuild chính thức.
- **Bằng chứng:** evidence Word/PDF cũ (không đủ đóng gate — cần re-render).
- **Lựa chọn:** A) mở rebuild bảng thuế theo mẫu hiện hành; B) giữ blocker.
- **Khuyến nghị:** A, làm chung wave với P1.
- **Hậu quả:** A = +4 section; B = P5R G5 phải liệt kê exception.

## P4 — PLI_M11 đã bị bãi bỏ

- **Vấn đề:** section `ds_to_chuc_xd_cshhl` của PLI_M11 không có evidence ở
  tầng nào (spec/template/form_maps/blocks/runtime đều trống) trong khi census
  cũ ghi already_complete.
- **Lựa chọn:** A) gỡ PLI_M11 khỏi app/pipeline (REMOVED_BY_CURRENT_LAW);
  B) giữ legacy-supported + ghi exception.
- **Khuyến nghị:** A nếu văn bản hiện hành không còn dùng mẫu này (cần owner
  xác nhận nội dung pháp lý — không tự suy diễn).
- **Hậu quả:** A = −1 form, coverage −1 section, use case rà lại; B = exception.

## P5 — Hình thức control "Ngành nghề kinh doanh chính" (AUD-010)

- **Vấn đề:** UI dùng radio tròn (semantics chọn-1 đúng); mẫu giấy dùng ô □.
- **Lựa chọn:** A) giữ radio tròn; B) render ô vuông (giữ semantics + ARIA
  radio) và DOCX xuất `X`.
- **Khuyến nghị:** B (đúng hình thức mẫu, không đổi behavior).
- **Hậu quả:** B = CSS + DOCX `X` ở cột ngành chính, 1 wave nhỏ + re-shoot.

## P6 — Phạm vi Excel cho `FULL_PRODUCT_DONE`

- **Vấn đề:** Excel hiện là pilot PLI_M72 (round-trip/negative PASS, owner đã
  duyệt hình phiếu). `CORE_APP_DONE` không cần Excel; `FULL_PRODUCT_DONE`
  cần định nghĩa rollout.
- **Lựa chọn:** A) pilot đủ; B) rollout mọi thủ tục ( questionnaire 24 câu v1
  + map key từng procedure); C) rollout theo cụm ưu tiên (M72 → hộ KD → đổi
  ngành → thuế).
- **Khuyến nghị:** C.
- **Hậu quả:** B ~ 9–13 phiên; C ~ 4–6 phiên; A = chốt luôn.

## P7 — `app_tk` legacy-supported hay deprecated

- **Vấn đề:** mã Tk cũ không mở rộng; chưa chốt trạng thái.
- **Khuyến nghị:** deprecated sau khi Windows package (Wave G) chứng minh
  pywebview path ổn định.
- **Hậu quả:** deprecated = bớt bề mặt smoke/maintenance.

## P8 — Môi trường: quyền Word visual + máy Windows

- **Vấn đề (a):** Word visual PDF 87/87 = NOT RUN. AppleScript bị TCC chặn
  (-1712/-609); computer-use bị chặn (Accessibility + Screen Recording denied).
  Không thể tự cấp quyền.
- **Lựa chọn:** A) owner cấp quyền (System Settings → Privacy & Security →
  Automation + Accessibility cho terminal/ZCode) rồi Lead chạy lại 87/87 bằng
  Word + pymupdf; B) owner tự mở 87 file bằng Word kiểm bằng mắt theo
  checklist `docs/platform_smoke_checklist.md`; C) chấp nhận Word visual =
  NOT RUN vĩnh viễn.
- **Hậu quả:** với A/B → G6 có thể PASS thật; C → `CORE_APP_DONE` KHÔNG thể
  tuyên bố trung thực (G6 bắt buộc 87/87 mở bằng Word).
- **Vấn đề (b):** Wave G cần Windows sạch không Python. Không có trong môi
  trường này → build + smoke = NOT RUN trừ khi owner cung cấp máy/VM.

## Việc đã chạy tới hạn trong lúc chờ owner

- Runner 46/0/0, numbering gate exit 0, deep idempotency 17/0, header 11/0.
- Wave E auditor đã re-audit delta (kết quả ghi ledger khi có).
- Docs/coverage/defect registry cập nhật trung thực đến `2593e3e`.
- Không gate nào bị hạ标准; mọi NOT RUN đều có lý do môi trường/owner.
