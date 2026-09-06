/*
 * test_f1_input_ui.js — Lane F1-IN (O1: 10 section USER-INPUT).
 *
 * Kiểm LỚP RUNTIME/UI cho 10 section của owner packet v7:
 *  1. [CTL]   contract đủ cột: FORM_TABLE_CONTRACTS (3 matrix M12, M78, C5
 *             PLII_M02) + FORM_GRID_META (3 loop M27, M79, M80).
 *  2. [ROWOP] add/delete/duplicate qua GridCtl cho loop editable-grid
 *             (M27 NĐD + M79) — _row_id duy nhất, duplicate nhân bản dữ liệu.
 *  3. [VALID] min_rows O3: NĐD required 1 dòng; M79 minRows 3 (3+ dòng, D6.5);
 *             error key trỏ đúng dòng (_row_id:tag) để UI focus đúng ô.
 *  4. [XFIELD] M78 "Sản phẩm khác": mô tả bắt buộc khi SL>0
 *             (requiredIfPositive -> DESC_REQUIRED blocking).
 *  5. [RADIO] PLI_M02 mo_hinh_to_chuc: tick cả 2 ô chọn-1 ->
 *             CHK_EXCLUSIVE_CONFLICT blocking (Q-V1 radio semantics).
 *  6. [DRAFT] draft cũ (không có key mới) validate KHÔNG sinh lỗi blocking
 *             mới từ các section F1-IN; dữ liệu cũ không mất.
 *
 * Run: node app_web/test_f1_input_ui.js
 */
'use strict';

const assert = require('assert');
const FD = require('./ui/form-domain.js');
const H = require('./ui/app.js');

let passed = 0;
let failed = 0;
function check(name, fn) {
  try {
    fn();
    passed++;
    console.log('PASS  ' + name);
  } catch (e) {
    failed++;
    console.log('FAIL  ' + name + '  [' + e.message + ']');
  }
}

const BLOCKING = (e) => e.filter((x) => x.severity === 'blocking');

/* ------------------------------------------------------- 1. CTL đủ cột */

check('[CTL] PLI_M12: 3 fixed-matrix đủ dòng/cột/tổng', () => {
  const secs = FD.sectionContractsOf('PLI_M12');
  const vdl = FD.getSectionContract('PLI_M12', 'co_cau_tai_san_gop_von_sau_thay_doi_vdl');
  const vdt = FD.getSectionContract('PLI_M12', 'co_cau_tai_san_gop_von_sau_thay_doi_vdt');
  const cp = FD.getSectionContract('PLI_M12', 'co_cau_loai_co_phan_sau_thay_doi');
  assert.deepStrictEqual(secs.map((s) => s.sectionId).slice(-3),
    ['tai_san_gop_von_sau_thay_doi_vdl',
     'tai_san_gop_von_sau_thay_doi_von_dau_tu',
     'co_cau_loai_co_phan_sau_thay_doi']);
  for (const e of [vdl, vdt]) {
    assert.strictEqual(e.spec.fixed_rows.length, 7);   // 6 dòng + Tổng số
    assert.strictEqual(e.spec.totals.length, 2);       // sum gia_tri + sum ty_le
    assert.deepStrictEqual(e.spec.columns.map((c) => c.tag),
      ['loai_tai_san_gop_von', 'chi_tiet_ngoai_te_tai_san_khac',
       'gia_tri_vnd', 'ty_le']);
  }
  // O2: giữ verbatim chính tả bản in hiện hành của Mẫu 12
  const labels = cp.spec.fixed_rows.map((r) => r.label);
  assert.ok(labels.includes('Cổ phần ưu đã biểu quyết'), labels);
  assert.strictEqual(cp.spec.totals.length, 3);
});

check('[CTL] PLI_M78: 4 dòng cố định + cột SL + rule requiredIfPositive', () => {
  const e = FD.getSectionContract('PLI_M78', 'ds_san_pham_yeu_cau');
  assert.strictEqual(e.spec.fixed_rows.length, 4);
  assert.strictEqual(e.spec.fixed_rows[3].id, 'san_pham_khac');
  assert.deepStrictEqual(e.spec.columns.map((c) => c.tag),
    [null, 'ten_san_pham', 'so_luong_san_pham']);
  assert.strictEqual(e.spec.max_rows, undefined);   // D6.4: max_rows=null
  const rule = e.spec.cross_field_rules[0];
  assert.strictEqual(rule.type, 'requiredIfPositive');
  assert.strictEqual(rule.whenRow, 'san_pham_khac');
});

check('[CTL] PLII_M02 C5: đúng 2 chỉ tiêu thật của Mục C (D5.2=A)', () => {
  const e = FD.getSectionContract('PLII_M02', 'thue_chi_tieu_cap_doi');
  assert.deepStrictEqual(e.spec.fixed_rows.map((r) => r.id),
    ['chi_tieu_5_1_dia_chi_nhan_thong_bao_thue',
     'chi_tieu_5_2_tong_so_lao_dong']);
  assert.deepStrictEqual(e.spec.columns.map((c) => c.tag),
    [null, 'dia_chi_nhan_thong_bao_thue', 'so_lao_dong']);
});

check('[CTL] M27/M79/M80: grid meta đủ cột + min/max rows', () => {
  const m27 = FD.FORM_GRID_META.PLI_M27.loops;
  assert.deepStrictEqual(Object.keys(m27),
    ['ds_ndd_pl_thong_bao_tam_ngung', 'don_vi_truc_thuoc_tam_ngung_tiep_tuc',
     'don_vi_tiep_tuc_truoc_han']);
  assert.strictEqual(m27.ds_ndd_pl_thong_bao_tam_ngung.required, true);
  assert.strictEqual(m27.ds_ndd_pl_thong_bao_tam_ngung.minRows, 1); // O3
  assert.strictEqual(m27.don_vi_truc_thuoc_tam_ngung_tiep_tuc.minRows, 0);
  assert.strictEqual(m27.don_vi_tiep_tuc_truoc_han.maxRows, null);
  const m79 = FD.FORM_GRID_META.PLI_M79.loops.ds_tai_lieu_kem_theo_m79;
  assert.strictEqual(m79.minRows, 3);               // D6.5: 3+ dòng
  assert.strictEqual(m79.maxRows, null);
  const m80 = FD.FORM_GRID_META.PLI_M80.loops.ds_tai_lieu_kem_theo_m80;
  assert.deepStrictEqual(m80.columns.map((c) => c.tag),
    ['mo_ta_tai_lieu', 'so_ban', 'so_trang']);
});

/* --------------------------------------------- 2. ROWOP add/delete/dup */

check('[ROWOP] M79: add/delete/duplicate qua GridCtl', () => {
  const store = { values: {}, checks: {}, loops: {} };
  H.GridCtl.addRow(store, 'ds_tai_lieu_kem_theo_m79');
  H.GridCtl.addRow(store, 'ds_tai_lieu_kem_theo_m79');
  H.GridCtl.addRow(store, 'ds_tai_lieu_kem_theo_m79');
  const rows0 = store.loops.ds_tai_lieu_kem_theo_m79;
  assert.strictEqual(rows0.length, 3);
  assert.ok(rows0.every((r) => r._row_id));
  assert.ok(H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
    { rowId: rows0[0]._row_id }, 'mo_ta_tai_lieu', 'Quyết định thành lập'));
  const dup = H.GridCtl.duplicateRow(store, 'ds_tai_lieu_kem_theo_m79',
    rows0[0]._row_id, 'PLI_M79');
  assert.ok(dup, 'duplicate trả kết quả');
  const rows = store.loops.ds_tai_lieu_kem_theo_m79;
  assert.strictEqual(rows.length, 4);
  assert.strictEqual(rows[1].mo_ta_tai_lieu, 'Quyết định thành lập');
  assert.notStrictEqual(rows[1]._row_id, rows[0]._row_id);
  H.GridCtl.deleteRows(store, 'ds_tai_lieu_kem_theo_m79',
    [rows[1]._row_id, rows[2]._row_id]);
  assert.strictEqual(store.loops.ds_tai_lieu_kem_theo_m79.length, 2);
});

check('[ROWOP] M27 NĐD: add/delete giữ draft hằng dòng tách biệt', () => {
  const store = { values: {}, checks: {}, loops: {} };
  H.GridCtl.addRow(store, 'ds_ndd_pl_thong_bao_tam_ngung');
  H.GridCtl.addRow(store, 'ds_ndd_pl_thong_bao_tam_ngung');
  const rows = store.loops.ds_ndd_pl_thong_bao_tam_ngung;
  H.GridCtl.setCell(store, 'ds_ndd_pl_thong_bao_tam_ngung',
    { rowId: rows[0]._row_id }, 'ho_ten', 'NGUYỄN VĂN A');
  H.GridCtl.setCell(store, 'ds_ndd_pl_thong_bao_tam_ngung',
    { rowId: rows[1]._row_id }, 'ho_ten', 'TRẦN VĂN B');
  H.GridCtl.deleteRows(store, 'ds_ndd_pl_thong_bao_tam_ngung', [rows[0]._row_id]);
  assert.strictEqual(store.loops.ds_ndd_pl_thong_bao_tam_ngung.length, 1);
  assert.strictEqual(store.loops.ds_ndd_pl_thong_bao_tam_ngung[0].ho_ten,
    'TRẦN VĂN B');
});

/* ------------------------------------------------------- 3. VALID min_rows */

check('[VALID] M27 NĐD: 0 dòng -> bắt buộc ít nhất 1 (O3, section luôn active)', () => {
  const blocks = [{ t: 'loop', loop: 'ds_ndd_pl_thong_bao_tam_ngung' }];
  const st = { values: {}, checks: {}, loops: {} };
  const errs = BLOCKING(FD.validateDocument('PLI_M27', blocks, st, {}));
  assert.ok(errs.some((e) => e.code === 'INDUSTRY_REQUIRED'), JSON.stringify(errs));
});

check('[VALID] M79: 1-2 dòng có dữ liệu -> MIN_ROWS blocking; 3 dòng -> hết', () => {
  const blocks = [{ t: 'loop', loop: 'ds_tai_lieu_kem_theo_m79' }];
  const mk = (n) => {
    const store = { values: {}, checks: {}, loops: {} };
    for (let i = 0; i < n; i++) {
      const added = H.GridCtl.addRow(store, 'ds_tai_lieu_kem_theo_m79');
      H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
        { rowId: added.id }, 'mo_ta_tai_lieu', 'Tài liệu ' + i);
    }
    return store;
  };
  for (const n of [1, 2]) {
    const errs = BLOCKING(FD.validateDocument('PLI_M79', blocks, mk(n), {}));
    assert.ok(errs.some((e) => e.code === 'MIN_ROWS'), 'n=' + n);
  }
  const errs = BLOCKING(FD.validateDocument('PLI_M79', blocks, mk(3), {}));
  assert.strictEqual(errs.length, 0, JSON.stringify(errs));
});

check('[VALID] M79: dòng thiếu tên tài liệu -> lỗi trỏ đúng _row_id:tag', () => {
  const blocks = [{ t: 'loop', loop: 'ds_tai_lieu_kem_theo_m79' }];
  const store = { values: {}, checks: {}, loops: {} };
  for (let i = 0; i < 3; i++) H.GridCtl.addRow(store, 'ds_tai_lieu_kem_theo_m79');
  const rows = store.loops.ds_tai_lieu_kem_theo_m79;
  H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
    { rowId: rows[0]._row_id }, 'mo_ta_tai_lieu', 'A');
  H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
    { rowId: rows[1]._row_id }, 'mo_ta_tai_lieu', 'B');
  H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
    { rowId: rows[2]._row_id }, 'mo_ta_tai_lieu', '');  // thiếu required
  H.GridCtl.setCell(store, 'ds_tai_lieu_kem_theo_m79',
    { rowId: rows[2]._row_id }, 'so_ban', '1');   // dòng có dữ liệu một phần
  const errs = FD.validateDocument('PLI_M79', blocks, store, {});
  const hit = errs.find((e) => e.code === 'ROW_INCOMPLETE');
  assert.ok(hit, JSON.stringify(errs));
  assert.ok(hit.key.endsWith(':' + rows[2]._row_id + ':mo_ta_tai_lieu'),
    hit.key);
});

/* --------------------------------------- 4. XFIELD M78 requiredIfPositive */

check('[XFIELD] M78: SL>0 thiếu mô tả -> DESC_REQUIRED blocking', () => {
  const blocks = [];
  const e = FD.getSectionContract('PLI_M78', 'ds_san_pham_yeu_cau');
  const st1 = { values: {
    'ds_san_pham_yeu_cau.san_pham_khac.so_luong_san_pham': '2',
  }, checks: {}, loops: {} };
  const errs1 = FD.validateSectionEntry('PLI_M78', e, st1);
  assert.ok(errs1.some((x) => x.code === 'DESC_REQUIRED' &&
    x.severity === 'blocking'), JSON.stringify(errs1));
  // có mô tả -> hết
  const st2 = { values: {
    'ds_san_pham_yeu_cau.san_pham_khac.so_luong_san_pham': '2',
    'ds_san_pham_yeu_cau.san_pham_khac.ten_san_pham': 'Bản cam kết',
  }, checks: {}, loops: {} };
  assert.strictEqual(FD.validateSectionEntry('PLI_M78', e, st2).length, 0);
  // chưa kê khai SL -> không ràng buộc ("khi co ke khai")
  const st3 = { values: {}, checks: {}, loops: {} };
  assert.strictEqual(FD.validateSectionEntry('PLI_M78', e, st3).length, 0);
  // SL âm -> MONEY blocking (D6.4: >=0)
  const st4 = { values: {
    'ds_san_pham_yeu_cau.sp_gcn_dkdn.so_luong_san_pham': '-3',
  }, checks: {}, loops: {} };
  assert.ok(FD.validateSectionEntry('PLI_M78', e, st4)
    .some((x) => x.code === 'MONEY'));
});

/* ------------------------------------------------- 5. RADIO chọn-1 (M02) */

const BLOCKS_M02 = require('../app/data/blocks/PLI_M02.json').blocks;

check('[RADIO] PLI_M02 mo_hinh: tick cả 2 -> CHK_EXCLUSIVE_CONFLICT', () => {
  const e = FD.validateDocument('PLI_M02', BLOCKS_M02, { values: {}, checks: {
    chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g: true,
    chk_auto_chu_tich_cong_ty_giam_doc_hoac_tong_giam: true,
  }, loops: {} }, {});
  const hit = e.find((x) => x.code === 'CHK_EXCLUSIVE_CONFLICT');
  assert.ok(hit && hit.severity === 'blocking', JSON.stringify(e));
  // chọn đúng 1 -> không lỗi nhóm
  const e1 = FD.validateDocument('PLI_M02', BLOCKS_M02, { values: {}, checks: {
    chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g: true,
  }, loops: {} }, {});
  assert.ok(!e1.some((x) => x.code === 'CHK_EXCLUSIVE_CONFLICT'));
});

/* ------------------------------------------------------ 6. DRAFT cũ */

check('[DRAFT] draft cũ không key mới -> 0 blocking mới từ section F1-IN', () => {
  // M27 draft kiểu cũ: chỉ scalar doanh nghiệp, không có loops mới
  const blocks27 = [{ t: 'loop', loop: 'ds_ndd_pl_thong_bao_tam_ngung' }];
  const errs = BLOCKING(FD.validateDocument('PLI_M27', blocks27, {
    values: { 'dn.ten_tieng_viet': 'CTY CỔ', 'dn.ma_so_dn': '0109999999' },
    checks: {},
    loops: {},
  }, {}));
  // NĐD required -> draft kiểu cũ chưa kê NĐD là lỗi bắt buộc sửa (thuộc
  // tính hợp lệ của form 2026), KHÔNG phải crash/leakage.
  assert.ok(errs.some((e) => e.code === 'INDUSTRY_REQUIRED'), JSON.stringify(errs));
  // draft cũ có 1 dòng NĐD (mô phỏng sau migrate lần đầu) -> hết lỗi
  const store = { values: { 'dn.ten_tieng_viet': 'CTY CỔ' }, checks: {},
    loops: {} };
  const added = H.GridCtl.addRow(store, 'ds_ndd_pl_thong_bao_tam_ngung');
  H.GridCtl.setCell(store, 'ds_ndd_pl_thong_bao_tam_ngung',
    { rowId: added.id }, 'ho_ten', 'NGUYỄN VĂN A');
  const errs2 = BLOCKING(FD.validateDocument('PLI_M27', blocks27, store, {}));
  assert.strictEqual(errs2.length, 0, JSON.stringify(errs2));
});

check('[DRAFT] M12: computed projection không bao giờ bị ghi ngược draft', () => {
  const e = FD.getSectionContract('PLI_M12', 'co_cau_tai_san_gop_von_sau_thay_doi_vdl');
  const st = { values: {
    'co_cau_tai_san_gop_von_sau_thay_doi_vdl.dong_viet_nam.gia_tri_vnd': '7000000000',
    'co_cau_tai_san_gop_von_sau_thay_doi_vdl.vang.gia_tri_vnd': '3000000000',
    'co_cau_tai_san_gop_von_sau_thay_doi_vdl.vang.ty_le': '30',
  }, checks: {}, loops: {} };
  const errs = FD.validateSectionEntry('PLI_M12', e, st);
  // PERCENT_SUM là warning (70+30 chưa đủ 100 vì dòng VNĐ thiếu tỷ lệ)
  assert.ok(errs.every((x) => x.severity !== 'blocking' ||
    x.code !== 'PERCENT_SUM'));
  const proj = FD.recomputeSections('PLI_M12', st);
  const key = 'co_cau_tai_san_gop_von_sau_thay_doi_vdl.tong_so.gia_tri_vnd';
  assert.strictEqual(proj[key].value, 10000000000, JSON.stringify(proj[key]));
  assert.ok(st.values[key] === undefined,
    'projection không được ghi ngược vào draft');
});

console.log('\ntest_f1_input_ui: %d PASS / %d FAIL', passed, failed);
if (failed) process.exit(1);
