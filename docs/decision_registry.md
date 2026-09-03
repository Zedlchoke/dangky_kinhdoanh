# Decision registry — consolidated packets từ 33 BLOCKED_LEGAL_REVIEW

> R0.3 master plan. Thay việc hỏi rời rạc 33 form, mọi câu hỏi pháp lý được
> gom thành **7 packet** theo policy dùng chung. Owner trả lời theo packet
> (mỗi câu chọn A/B/…); section thuộc packet chỉ rollout khi status `DECIDED`.
> Evidence gốc giữ nguyên văn trong `docs/legal_review_backlog.md` và
> `app/data/table_specs/manifest.json` (`legal_questions`) — không suy diễn.

## Cách đọc

- `DECIDED` — đã chốt, có ngày + nguồn quyết định; lane được phép triển khai.
- `OPEN` — chờ owner; các section liên quan KHÔNG được rollout (các lane độc
  lập khác vẫn chạy: layout, P2 platform, spec/test).
- Migration impact = thay đổi bắt buộc lên draft/blocks/form_maps khi áp dụng.

## Owner decisions 2026-09-03 (trả lời packet `docs/owner_decision_packet_2026-09-03.md`)

| Packet | Quyết định | Ghi chú triển khai |
|---|---|---|
| P1 (D1.3/D1.5/D3.3 — đuôi M03/M04) | **DECIDED: A** | khôi phục phần đuôi đầy đủ + implement input theo source chính thức hiện hành → lane `fix-tails-m0304` |
| P2 (member grids PLII_M02 ×2 + PLI_M72 N2–N5) | **DECIDED: A** | rebuild → lane `fix-member-grids` |
| P3 (bảng thuế PLII_M03–M06) | **DECIDED: A** | rebuild → lane `fix-tax-m0306` |
| P4 (PLI_M11) | **DECIDED CÓ ĐIỀU KIỆN** | chỉ gỡ sau khi đối chiếu văn bản chính thức hiệu lực + ghi source evidence; chưa chứng minh được → giữ BLOCKED_OWNER, không tự gỡ |
| P5 (AUD-010 hình thức "ngành chính") | **DECIDED: B** | control ô vuông, giữ radio semantics + keyboard/ARIA; DOCX xuất `X` |
| P6 (Excel rollout) | **DECIDED: C** | theo cụm: M72 → hộ kinh doanh → thay đổi ngành → thuế; Google Forms ngoài scope wave này |
| P7 (app_tk) | Deprecated sau khi pywebview Windows smoke PASS | Wave G |
| P8a (Word visual) | Owner đã cấp quyền — probe OK (Word 16.16.27, exit 0) | chạy 87/87 khi pipeline ổn |
| P8b (Windows) | Chờ máy/VM sạch; giữ NOT RUN | Wave G |
| Push remote | KHÔNG push cho tới lệnh owner | toàn bộ |

## Đã DECIDED trước registry

| ID | Quyết định | Ngày | Evidence |
|---|---|---|---|
| D-M72-ACT | M72 Option D: selector `dn.loai_hinh` metadata hồ sơ, đúng 1 variant UI+DOCX | 2026-08-26 P1.2 (commit d882793) | `docs/m72_activation_proposal.md` phụ lục 9 |
| D-P1C-HEADING | Spec lưu `match_heading` plain-text; verifier so theo hành vi trên template | 2026-08-26 R0 (commit 1caabd5) | `tools/census/p1_c_verify_plii_m02.py` |

---

## Packet D1 — Capital / formulas (6 form)

**Forms:** PLI_M01, PLI_M02, PLI_M03, PLI_M04, PLI_M05, PLI_M12
**Status: OPEN**

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D1.1 | Totals & tỷ lệ trong nguồn vốn/tài sản/cổ phần: computed outputOnly, đối chiếu vốn điều lệ? | A) YES computed+blocking mismatch · B) cho nhập tay tổng | A — khớp contract P2 proposed, tránh hai nguồn số liệu mâu thuẫn |
| D1.2 | "Các tài sản khác" trong Tài sản góp vốn (M01/M02/M12): sub-grid danh mục con hay ô mô tả text? | A) sub-grid editable · B) text mô tả | B cho M01 (nguồn ghi "lập danh mục riêng kèm hồ sơ" = đính kèm), A nếu owner muốn nhập tại chỗ |
| D1.3 | Nguồn PLI_M03 kết thúc sau mục 6 (không thuế/BHXH/CSHHL như Mẫu 2): đủ nội dung hay nguồn bị cắt? | A) đủ → dựng ngay · B) cắt → lấy bản gốc, mở lại census | B — cần đối chiếu bản gốc trước khi khẳng định phạm vi pháp lý |
| D1.4 | Giá trị loại cổ phần = số lượng × mệnh giá (M04/M12): formula computed? | A) YES formula · B) nhập tay tổng | A |
| D1.5 | Nguồn PLI_M04 kết thúc tại mục 7: đủ nội dung hay bị cắt? | A/B như D1.3 | B |
| D1.6 | PLI_M05 không có bảng thành viên hợp danh inline (theo Mẫu 9 gửi kèm): xác nhận? | A) không cần lưới inline · B) thêm section mới | A |

**Migration impact:** D1.1/D1.4 thêm field computed outputOnly (không phá draft);
D1.2-A thêm loop mới; D1.3/D1.5-B thay template nguồn → regenerate blocks.

---

## Packet D2 — People / nested rows (10 form)

**Forms:** PLII_M02, PLII_M07, PLI_M06, PLI_M07, PLI_M08, PLI_M09, PLI_M10,
PLI_M13, PLI_M15, PLI_M72
**Status: OPEN**

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D2.1 | Row contract NĐDPL vs người đại diện theo ủy quyền (M02/M13/M15): discriminator 2 row-type trong 1 bảng hay tách 2 bảng? | A) discriminator `{loai_dong}` · B) 2 bảng riêng | A — một policy chung cho cả 3 mẫu, khớp header nối 13 cột nguồn |
| D2.2 | Thành viên TNHH M06: grid phẳng đủ cột hay nested-grid đúng mẫu gốc (cá nhân/tổ chức/NĐD)? | A) phẳng bổ sung cột thiếu · B) nested | A cho wave đầu (nhanh, ít rủi ro); B khi nested-grid sẵn sàng |
| D2.3 | Cổ đông sáng lập M07 & cổ đông NĐT NN M08: phẳng+nâng cột hay nested 19/18 cột? | A) phẳng · B) nested đúng mẫu gốc | phải chọn CÙNG architecture với nhau; khuyến nghị A trước, B theo roadmap nested |
| D2.4 | Cột Chữ ký xác nhận các bảng người: outputOnly? | A) YES · B) text input | A — khớp GRID_META hiện tại |
| D2.5 | Quyền chi phối CSHHL (M10): cột riêng hay ghi vào Ghi chú? | A) cột riêng + migration · B) Ghi chú | A — đúng NĐ 168/2025 điểm b khoản 1 Điều 17 |
| D2.6 | M13: một giấy được phép nhiều NĐDPL — dựng grid hay 1 bộ field + nhiều hồ sơ? | A) grid · B) 1 bộ field | A |
| D2.7 | Min/max rows danh sách NĐDPL/ủy quyền (M02/M13/M15/M27)? | số cụ thể do owner khai | đề xuất min 1 / max null (không giới hạn vô căn cứ) |
| D2.8 | PLII_M07 GCN Mẫu 7: key riêng `ds_thanh_vien_hkd_gcn` hay subset contract `ds_tv_ho_gia_dinh`? | A) key riêng · B) subset | A — tập cột khác thật (có Ghi chú, không ngày sinh/giới tính/dân tộc/chữ ký) |
| D2.9 | 4 nested-grid thành viên/cổ đông PLI_M72: namespacing key trùng giữa 5 phần loại hình? | A) prefix theo variant · B) dùng chung key + activeWhen | A — an toàn draft; render vẫn chỉ variant active (Option D) |

**Migration impact:** D2.5-A thêm column tag + migration draft additive;
D2.8-A tạo loop mới; D2.9-A đổi key blocks M72 (regenerate, draft cũ chưa có
dữ liệu M72 nên an toàn).

---

## Packet D3 — Source integrity (4 form)

**Forms:** PLI_M03, PLI_M04, PLI_M05, PLI_M09
**Status: OPEN** (D1.3/D1.5 là mặt vốn của cùng vấn đề; gộp quyết định)

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D3.1 | Vùng Mẫu 6/7/8/9(lần 2)/10 nhiễm trong template+blocks PLI_M09 (p103-p222): được phép xóa khỏi template khi rebuild? | A) xóa (decontaminate) · B) giữ nguyên, chỉ đánh dấu output | A |
| D3.2 | Nếu bản Mẫu 9 thứ hai (header 14 cột đầy đủ) mới là cấu trúc đúng: chọn nó thay TBL[0] phẳng hiện tại? | A) chọn bản 14 cột · B) giữ phẳng | A — đúng luật; kéo theo rebuild lớn hơn nhưng xử lý luôn D2.2/D2.3 header glued nằm trong file này |
| D3.3 | M03/M04/M05: lấy lại bản nguồn pháp lý gốc để đối chiếu trước khi dựng fixed-matrix? | A) YES · B) tin nguồn hiện tại | A — tiền điều kiện D1.3/D1.5 |

**Migration impact:** D3.1-A regenerate template/blocks M09; D3.2-A thay loop
contract `ds_thanh_vien_hop_danh`; draft cũ M09 gần như rỗng nên rủi ro thấp.

---

## Packet D4 — Canonical sharing (2 form)

**Forms:** PLII_M02, PLI_M52
**Status: OPEN**

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D4.1 | PLII_M02 Mục C (cấp đổi): ngành/thành viên/thuế kê khai độc lập hay đồng bộ từ đăng ký hiện tại của hộ? | A) độc lập hoàn toàn · B) đồng bộ tự động · C) copy tường minh 1 lệnh | A hoặc C — PLAN cấm auto-sync giữa loop khác nghĩa; C cần thiết kế UI copy |
| D4.2 | PLI_M52: key `ma_so_van_ban` đang mang 3 ngữ nghĩa (MSDN/mã CN/mã VPĐD) — tách key riêng từng nhóm? | A) tách + migration · B) giữ chung | A |

**Migration impact:** D4.2-A bắt buộc migration draft rename key (additive,
giữ key cũ đọc-only); D4.1-A không đổi gì.

---

## Packet D5 — Tax fixed rows (5 form)

**Forms:** PLI_M17, PLI_M19, PLI_M23, PLI_M25, PLII_M02 (section thuế)
**Status: OPEN**

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D5.1 | Các nhóm checkbox chọn-1 (hạch toán, GTGT, BHXH, khu CN): fixed-matrix radio chọn-1 dùng chung pattern cho M17/M19/M23/M25? | A) YES một spec pattern · B) spec từng mẫu | A |
| D5.2 | Tập chỉ tiêu cố định thuế cũ/mới PLII_M02 gồm những gì (nguồn chỉ in "- Chỉ tiêu 5.1…")? | owner liệt kê canonical list | cần văn bản gốc; không suy diễn |
| D5.3 | Validation chéo BHXH (ngành nông-lâm-ngư-diêm trả lương theo sản phẩm): cần cross-field rule? | A) YES · B) NO | A nếu D5.1-A |
| D5.4 | Chỉ tiêu 8 CTCK nước ngoài (M17): mục riêng ngoài bảng thuế? | A) YES · B) trong bảng | A |

**Migration impact:** thêm fixed_rows catalog + checkbox group keys mới
(additive); defect numbering M23 sửa lúc rebuild.

---

## Packet D6 — Branches / admin / output (13 form)

**Forms:** PLI_M27, M52, M56, M63, M66, M67, M68, M70, M71, M75, M78, M79, M80
**Status: OPEN**

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D6.1 | Một thông báo được liệt kê nhiều đơn vị cùng lúc (M27/M56/M66/M67/M68/M75): grid nhiều dòng hay scalar-fields một đơn vị/giấy? | A) grid · B) scalar | A với mẫu nguồn dùng "(các)/một hoặc một số"; B với mẫu trình bày đơn khối (tiền lệ M28/M55) — owner duyệt từng mẫu theo bảng evidence |
| D6.2 | Chủ thể nhập các section do CQĐKKD phát hành (M52/M63/M66/M68/M75): DN nhập hay output-only khi tích hợp cơ quan? | A) DN nhập phần được yêu cầu · B) output-only toàn bộ | A cho phần DN phải khai; output-table O3–O6 chỉ render có điều kiện |
| D6.3 | "Hồ sơ bao gồm" M70/M71: cố định 3 dòng hay n tài liệu biến thiên? | A) fixed-matrix 3 dòng · B) editable min/max | B nếu thực tế hồ sơ >3 tài liệu; owner chốt min/max |
| D6.4 | Số lượng sản phẩm M78: integer ≥0 max?, hàng 4 "Sản phẩm khác" bắt buộc mô tả khi SL>0, placeholder tên DN hàng 1-3? | owner chốt tham số | cross-field "SP khác mô tả khi SL>0" = YES |
| D6.5 | Tài liệu kèm theo M79/M80: min/max dòng? Có cần upload file thật (scope mới) hay chỉ metadata? | A) metadata only · B) upload binary | A — B là scope mới cần Lead duyệt riêng |
| D6.6 | Attachment metadata: trường nào bắt buộc (tên, số bản, trang)? | owner chốt | đề xuất tên tài liệu bắt buộc, còn lại optional |

**Migration impact:** hầu hết additive; D6.2 quy định kind cuối cùng
(output-table vs editable-grid) của 6 section O3–O6.

---

## Packet D7 — M72 còn lại (sau Option D)

**Form:** PLI_M72
**Status: OPEN** (4 mục từ phụ lục 9.5 proposal + namespacing D2.9)

| # | Câu hỏi | Lựa chọn hữu hạn | Khuyến nghị |
|---|---|---|---|
| D7.1 | Khối cuối tài liệu (dòng gạch dưới + đoạn trắng sau section hợp danh): dùng chung mọi biến thể hay gắn vào 1 biến thể? | A) dùng chung (hiện trạng) · B) gắn variant | A |
| D7.2 | Ghi chú chân trang số 1 mất chữ số ở nguồn: khôi phục ký hiệu chú thích? | A) khôi phục "¹" · B) giữ bọc theo vị trí | A nếu có bản gốc đối chiếu; B chấp nhận được |
| D7.3 | Bảng ngành variant active hiện `required:false/minRows:0`: có bắt buộc ≥1 ngành khi công bố thành lập? | A) required minRows 1 · B) giữ tự do | A về nguyên tắc công bố; owner xác nhận |
| D7.4 | 4 nested-grid thành viên/cổ đông: xem D2.9 (namespacing) — tiền điều kiện fixture N2 | theo D2.9 | A |

**Migration impact:** D7.3-A đổi meta `required/minRows` 5 loop (không đổi
draft shape).

---

## Thống kê & thứ tự ưu tiên

| Packet | Forms | Section kinds bị chặn chính |
|---|---|---|
| D1 capital/formulas | 6 | fixed-matrix ~12, nested 1 |
| D2 people/nested | 10 | editable ~8, nested 7 |
| D3 source-integrity | 4 | decontamination + rebuild M09 |
| D4 canonical-sharing | 2 | migration key |
| D5 tax-fixed-rows | 5 | fixed-matrix ~6 |
| D6 branches/admin/output | 13 | editable ~9, output 6 |
| D7 m72-remaining | 1 | meta required + 4 nested |

Trả lời theo cụm (a) D1 → (b) D3 → (c) D2/D7 → (d) D5 → (e) D4/D6 sẽ mở đường
rollout R3A→R3B→R3C→R3D tương ứng. Trong lúc chờ: LAYOUT (R1) và P2 platform
(R2) không phụ thuộc packet nào ở trên.

## Owner response checkpoint — 2026-08-27

Owner đã chọn bundle khuyến nghị cho D1–D7 qua checkpoint execution. Các lựa
chọn đã ghi nhận: D1.1=A, D1.2=B cho M01, D1.3=B, D1.4=A, D1.5=B,
D1.6=A; D2.1–D2.6=A, D2.7=min 1/max null, D2.8=A, D2.9=A; D3.1=A,
D3.2=A, D3.3=A; D4.1=A, D4.2=A; D5.1=A, D5.3=A, D5.4=A; D6.2=A,
D6.3=B, D6.5=A, D6.6=tên tài liệu bắt buộc/các trường còn lại optional;
D7.1=A, D7.2=A nếu có nguồn đối chiếu, D7.3=A, D7.4=A.

Các packet **chưa được đóng DECIDED** vì còn thiếu thông tin/biên quyết định:

- D1/D3: D1.3, D1.5 yêu cầu lấy bản nguồn gốc để đối chiếu; D1.2 chưa
  xác định policy cho mọi form ngoài M01.
- D5: D5.2 canonical list chỉ tiêu thuế PLII_M02 chưa được cung cấp; section
  này tiếp tục `BLOCKED_LEGAL_REVIEW`.
- D6: owner chọn lập evidence theo từng mẫu cho D6.1; D6.4 mới chốt rule
  mô tả “Sản phẩm khác” khi số lượng > 0, chưa chốt max/placeholder.
- D4, D2 và D7 có thể mở phần kỹ thuật tương ứng theo các lựa chọn đã đủ,
  nhưng không tự động đóng các packet khác còn phụ thuộc source evidence.

## Owner response checkpoint — 2026-08-28 (lần 2, cùng ngày)

Owner ra lệnh mở các nhóm bảng blocked bằng NGUỒN PHÁP LÝ MỚI (thay việc chờ
bản gốc giấy — trả lời D1.3/D1.5/D3.3=B cũ):

- **Nguồn chuẩn được phép dùng:** Nghị định 168/2025/NĐ-CP (30/6/2025) +
  **Thông tư 68/2025/TT-BTC** (biểu mẫu phụ lục I/II chính là các mẫu trong
  app). Owner cho phép Lead/agent **tự tra cứu trên mạng** và **hỏi owner bất
  cứ thông tin pháp lý nào** cần. Mọi spec bắt buộc trích dẫn điều/dòng nguồn
  vào `source_evidence`.
- **Phạm vi mở (5 nhóm):** (1) nguồn vốn PLI_M03/M04/M05/M12; (2) thuế
  PLII_M02 (D5.2 — danh mục chỉ tiêu theo mẫu II.2 TT 68); (3) M09 rebuild
  14 cột (D3.1=A decontaminate + D3.2=A); (4) M72 N2–N5 + N-tail (D2.9/D7.4=A);
  (5) thuế fixed-matrix PLI_M17/M19/M23/M25 (D5.1=A).
- **Use case mới:** "Thay đổi nội dung đăng ký hộ kinh doanh" (PLII_M02, do
  chủ hộ ký) — data-only, Điều 100/101 NĐ 168.
- **Layout header:** tên DN/HKD TRÁI + khối quốc hiệu PHẢI cùng band; dòng
  "Số:" TRÁI / ngày-tháng-năm PHẢI — theo bản Word gốc Phụ lục II Mẫu 2 /
  Phụ lục I Mẫu 13. Sửa qua spec + Lead regen, cấm sửa tay generated; visual
  re-shoot (UI + DOCX qua Word) bắt buộc.
- **Defect hunt (lệnh bổ sung trong ngày):** các lớp lỗi như "M09 nhảy mục
  6→8 (mất mục 7)", "thiếu checkbox 3 tháng phương thức đóng BHXH", "bảng
  ngành nghề" phải được **identify tận gốc rồi loại bỏ** trước khi bàn giao —
  mở Wave D2 census/audit hệ thống, không vá tay từng mẫu.
- Lưu ý nguồn pháp lý đang theo dõi: TT 121/2026/TT-BTC (hiệu lực 21/8/2026)
  sửa đổi TT 68/2025, thay 09 biểu mẫu — các lane rebuild phải kiểm tra mẫu
  của mình có thuộc số bị thay không, ưu tiên bản hiện hành, ghi rõ trong
  spec; mơ hồ thì hỏi owner.

## Owner questions Phase 4 — row/blank-row contract (2026-09-03, session Phase 4)

**Q-P4-1. `min_rows` của 3 nested-grid — enforce hay bỏ khai báo?**
- Hiện trạng: `spec.min_rows: 1` khai tại PLI_M02 `nddpl_uy_quyen_chu_so_huu`,
  PLI_M12 `ndd_uy_quyen_sau_thay_doi`, PLI_M15 `ndd_pl_uy_quyen_chu_so_huu_moi`
  nhưng KHÔNG tầng nào enforce (nested-grid.js `validate()` không đọc;
  `rowOpMeta` chỉ đọc `max_rows`) — inventory: `docs/row_contract_inventory.json`
  gaps[0].
- Câu hỏi: (a) nếu enforce vô điều kiện (filled < min_rows → blocking) thì hồ
  sơ KHÔNG ủy quyền (section trống hợp lệ) sẽ bị chặn export — có đúng nghiệp
  vụ không? hay (b) chỉ enforce khi section đã có ít nhất 1 dòng có dữ liệu
  (khi đó min_rows=1 gần như hiển nhiên, chỉ còn ý nghĩa với min_rows ≥ 2),
  hay (c) xóa khai báo để tránh ảo tưởng đã có ràng buộc?
- Mặc định nếu owner chưa trả lời: giữ nguyên khai báo, KHÔNG enforce, giữ
  BLOCKED_OWNER cho gap này (không tự chọn semantics).

**Q-P4-2 (đã chốt, ghi nhận lại trong scope Phase 4).** Blank row: dòng MỌI ô
trống không trở thành business data — lọc ở export (JS `exportLoops` +
Python `_expand_loops` guard), draft giữ nguyên; blank rows IN SẴN của bản giấy
(blocks `blankRows`) là cấu trúc pháp định, không lọc. Đã implement + corpus
test (test_row_contract_corpus / test_row_contract_export).
