# P2 — Production fixture candidates cho 4 table component

Trạng thái: **LOCKED v1 — Lead review 2026-08-27**. Chọn fixture production NHỎ từ
`app/data/table_specs/manifest.json` (87 form / 111 section) để làm fixture +
contract test cho từng loại component trước khi rollout domain (P2 mục 5 của
PLAN). Tiêu chí: số cột/dòng tối thiểu nhưng vẫn đụng đặc tính khó nhất của
component (totals, rowspan, row-type).

---

## 1. `editable-grid` (43 section)

| # | form_id | section_id | Status | Lý do chọn |
|---|---|---|---|---|
| E1 | PLII_M01 | m3_nganh_kinh_doanh | already_complete | TABLE_COMPLETE; `ds_nganh` đầy đủ đặc tính: VSIC + requirePrimary radio + `_stt` + blankRows. Fixture "vàng" hiện trạng GridCtl |
| E2 | PLII_M01 | m7_thanh_vien_ho_gia_dinh | already_complete | TABLE_COMPLETE; 10 cột, `chu_ky` outputOnly, validation có điều kiện (kê khai cột 1–5 và 10 theo số định danh) |
| E3 (pending) | PLI_M79 | tai_lieu_kem_theo_de_nghi | missing_grid | Schema nhỏ nhất (stt + mo_ta_tai_lieu), kiểm thử rebuild grid + min/max dòng biến thiên; câu hỏi pháp lý chỉ ảnh hưởng bound maxRows, không chặn contract |

- Phạm vi dữ liệu tối thiểu: 3 dòng ngành (1 chính) cho E1; 2 thành viên đủ
  cột cho E2; 4 dòng tài liệu cho E3.
- Test bắt buộc: add/delete/reorder/duplicate giữ `_row_id`; duplicate bỏ
  khóa (`ma_nganh`); MIN_ROWS/MAX_ROWS; export loại `_row_id` và map
  `la_nganh_chinh` → X; draft round-trip.
- Ghi chú: mọi section editable-grid còn lại đang `missing_grid` đều thuộc
  form BLOCKED_LEGAL_REVIEW nên không dùng fixture đầu được.

## 2. `fixed-matrix` (47 section)

| # | form_id | section_id | Status | Đặc tính phủ | Lý do nhỏ nhất |
|---|---|---|---|---|---|
| F1 | PLI_M01 | thue_chi_tieu_6_1_6_9 | already_complete | chỉ tiêu đánh số cố định + checkbox nhóm | 9 chỉ tiêu đã map đủ; fixture render hiện trạng, không cần rebuild |
| F2 | PLI_M03 | nguon_von_dieule | missing_grid | totals computed + đối chiếu vốn điều lệ | 5 dòng × 3 cột, không STT — bảng vốn nhỏ nhất trong nhóm nguồn vốn M02/M03/M04/M05/M12 |
| F3 | PLI_M04 | co_cau_loai_co_phan | missing_grid | formula giá trị = số lượng × mệnh giá; tổng đối chiếu VĐL | 5 loại cổ phần + Tổng số; đại diện nhóm cơ cấu cổ phần M04/M12 |
| F4 | PLI_M02 | tai_san_gop_von_von_dieu_le | missing_grid | chi tiết ngoại tệ/tài sản khác; tỷ lệ tổng 100% | 6 dòng cố định + Tổng số; dòng "Tài sản khác" mở sub-detail |

Fixture bổ sung tùy chọn: `lua_chon_khu_san_xuat` (PLI_M01,
already_complete) — ma trận lựa chọn 4 ô checkbox không STT, dùng smoke test
renderer mà không cần input tiền.

- Phạm vi dữ liệu tối thiểu: F2 điền 1 dòng vốn tư nhân + tổng tự sinh;
  F3 điền 1 loại cổ phần (số lượng, mệnh giá); F4 điền dòng Đồng Việt Nam +
  1 dòng tài sản khác có mô tả.
- Test bắt buộc: không xóa được dòng pháp lý; ô tổng outputOnly recompute;
  PERCENT_SUM; cross-check tổng = vốn điều lệ (blocking); anchor/boundary
  không xóa paragraph bảng kế tiếp; idempotency generator chạy 2 lần.

## 3. `nested-grid` (7 section — tất cả missing_grid, form BLOCKED)

| # | form_id | section_id | Khả thi làm fixture đầu | Lý do / blocker |
|---|---|---|---|---|
| N1 | PLI_M02 | nddpl_uy_quyen_chu_so_huu | **KHẢ THI NHẤT** | Template production sẵn (`app/templates/PLI_M02.docx#p140-p144`), nằm trong mẫu pilot HTKK đã ổn định; header nối 13 cột cần rebuild. Blocker pháp lý: phân biệt kiểu dòng NĐDPL vs người ủy quyền — ảnh hưởng row-contract, KHÔNG chặn dựng header/renderer skeleton |
| N2 | PLI_M72 | thanh_vien_tnhhh_hai_tv_tro_len | Thứ hai, sau khi namespacing chốt | Header nhiều hàng thật (Phần vốn góp gộp chú thích VNĐ/ngoại tệ) — fixture chuẩn để test colspan/rowspan; blocker: key trùng giữa 5 phần loại hình cần namespacing + policy render theo phần được chọn |
| N3 | PLI_M72 | co_dong_sang_lap_cp | backlog | header nối stt_joined ×2; phụ thuộc quyết định N2 |
| N4 | PLI_M72 | co_dong_nuoc_ngoai_cp | backlog | như N3, thêm chú thích đơn vị tiền |
| N5 | PLI_M72 | thanh_vien_hop_danh | backlog | blocks không có input nào |
| N6 | PLI_M12 | ndd_uy_quyen_sau_thay_doi | backlog | header nối 14 cột; ngữ cảnh sau-thay-đổi phải tách draft riêng |
| N7 | PLI_M15 | ndd_pl_uy_quyen_chu_so_huu_moi | backlog | nguồn tách file full; cùng cấu trúc N1/N6 |

- Phạm vi dữ liệu tối thiểu N1: 2 dòng — 1 người ủy quyền (có tỷ lệ %) +
  1 NĐDPL; N2: 2 thành viên cá nhân với phần vốn góp VNĐ/ngoại tệ.
- Test bắt buộc: header nhiều hàng render đúng rowspan/colspan; DOCX xuất ra
  không mất cột/lệch STT (Gate #8); duplicate key theo vai trò;
  reorder/xóa dòng theo `_row_id`.

## 4. `output-table` (6 section)

| # | form_id | section_id | Chọn | Lý do |
|---|---|---|---|---|
| O1 | PLI_M70 | chu_ky_nguoi_nop_nguoi_nhan | **Fixture đầu** | Bảng chữ ký 2 ô độc lập, không phụ thuộc biến thể Điều 2–4 hay chủ thể nhập |
| O2 | PLI_M71 | chu_ky_co_quan_cap_tinh | Fixture hai | Biến thể 1 ô ký (khác M70) — test shape khác nhau cùng kind |
| O3 | PLI_M63 | noi_dung_quyet_dinh_thu_hoi | backlog | cần legal chốt chủ thể nhập + activeWhen biến thể Điều 2–4 |
| O4 | PLI_M66 | thong_bao_cqb | backlog | cần legal chốt ai kê khai (DN xem hay cán bộ nhập) |
| O5 | PLI_M68 | thong_bao_dang_giai_the | backlog | như O4 |
| O6 | PLI_M75 | thong_bao_khoi_phuc_gcn | backlog | như O4/O5 |

- Phạm vi dữ liệu tối thiểu: không có input; fixture là template + khối
  assertions về presence của grid trong DOCX xuất.
- Test bắt buộc: renderer không sinh input nào; grid vẫn tồn tại trong DOCX
  (PLAN mục G); audit nhận diện `output_only` không đòi spec input.

---

## 5. Tổng hợp thứ tự làm fixture

1. E1/E2 (đã hoàn thiện) — khóa contract editable-grid ngay, không cần regenerate.
2. O1/O2 — nhẹ, xác nhận pipeline fixture/test chạy được.
3. F1 → F2/F3/F4 — sau khi fixed-matrix renderer + formula có; F2–F4 cần Lead regenerate PLI_M03/M04/M02.
4. E3 — regenerate PLI_M79 (grid đơn giản).
5. N1 — skeleton nested-grid trên PLI_M02; N2 khi people-ownership/namespacing sẵn sàng.
