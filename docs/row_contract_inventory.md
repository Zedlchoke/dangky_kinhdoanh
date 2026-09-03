# Row/blank-row contract inventory (Phase 4)

Sinh bởi `tools/census/row_contract_inventory.py` tại HEAD `28df5cb`.

| họ contract | số entry |
|---|---|
| global_grids | 11 |
| form_grids | 18 |
| section_contracts | 14 |
| dynamic_tables | 42 |
| section_specs | 21 |
| blocks_blank_rows | 42 |

Gate phủ: **PASS**

## Policies (hợp đồng hiện hành)

- **blank_row**: Dòng MỌI ô trống (bỏ key nội bộ _*) không trở thành business data: GridCtl.exportLoops (app.js) lọc trước, _expand_loops (docx_render.py) guard last-mile; {_stt} đánh lại trên dòng dữ liệu in ra.
- **blank_helper_ui**: UI render tối thiểu 1 dòng trống helper cho grid cho-phép-thêm (render.js renderLoop/nested) — dòng ảo KHÔNG nằm trong store cho tới khi người dùng gõ.
- **partial_row**: Dòng điền một phần được GIỮ (không âm thầm mất); validator chặn theo contract: ROW_INCOMPLETE (thiếu cột required), MIN_ROWS, INDUSTRY_REQUIRED, MAX_ROWS (warn).
- **fixed_legal_row**: fixed-matrix in ĐỦ dòng pháp định bất kể ô nhập trống (kể cả dòng Tổng output_only, tổng recompute strict fail-loud). blankRows của blocks là hàng trắng IN SẴN theo bản giấy — không bị lọc, không bị đếm là dữ liệu.
- **inactive_variant**: M72: grid inactive-theo-selector (valueOf dn.loai_hinh) -> payload rỗng cho grid đó; block DOCX {?flag} của variant sai bị drop.
- **stt**: STT KHÔNG lưu: suy từ thứ tự mảng sau lọc — engine {_stt} 1-based; fixed-matrix chỉ khi spec.stt.mode='generated'.
- **draft**: store.loops[loop] là mảng — thứ tự + _row_id bảo toàn qua draft save/load; blank row SỐNG trong draft, chỉ lọc ở export; migrateDraft v1->v2 additive.
- **grid_ops**: add/delete/reorder/duplicate/clear scope theo tên loop (GridCtl); policy theo kind: fixed-matrix/output-table F/F/F, nested-grid + editable-grid T/T/T; duplicate bỏ duplicateKeys + _row_id; confirm xóa dòng có dữ liệu.

## Gaps (chờ owner)

- **nested_grid_min_rows_declared_not_enforced**: spec.min_rows=1 khai tại 3 nested-grid (PLI_M02 nddpl_uy_quyen_chu_so_huu, PLI_M12 ndd_uy_quyen_sau_thay_doi, PLI_M15 ndd_pl_uy_quyen_chu_so_huu_moi) nhưng KHÔNG tầng nào enforce (nested-grid.js validate không đọc; rowOpMeta chỉ đọc max_rows). Nghĩa nghiệp vụ chưa chốt: (a) bắt buộc ≥1 dòng khi section ĐANG trống sẽ chặn export hợp lệ của hồ sơ không ủy quyền; (b) enforce khi section có dữ liệu thì min_rows=1 là hiển nhiên. -> BLOCKED_OWNER, xem docs/decision_registry.md câu hỏi owner Phase 4.

Chi tiết đầy đủ: `docs/row_contract_inventory.json`.
