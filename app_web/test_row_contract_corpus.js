/* test_row_contract_corpus.js — PHASE 4 row/blank-row contract: corpus test
 * cho HÀNH VI BẢNG khi người dùng nhập 0/1/nhiều dòng, blank row, inactive
 * variant và draft round-trip. Chạy trên BLOCKS/META PRODUCTION (chỉ đọc).
 *
 * Chạy:  node app_web/test_row_contract_corpus.js
 *
 * Phủ (theo nhóm contract cùng semantics):
 *  G1 editable-grid (GRID_META/FORM_GRID_META):
 *    R1 blank-only row KHÔNG xuất thành business data (exportLoops lọc);
 *    R2 one-row input -> đúng 1 data row, thứ tự bảo toàn;
 *    R3 blank đầu/giữa/cuối/nhiều blank -> chỉ các dòng CÓ dữ liệu được xuất,
 *       KHÔNG âm thầm mất dòng partial (ít nhất 1 ô có giá trị);
 *    R4 add/delete/reorder/duplicate/clear KHÔNG tác động nhầm grid khác
 *       cùng form (isolation theo tên loop);
 *    R5 draft round-trip: thứ tự + dữ liệu + _row_id + BLANK ROW giữ nguyên
 *       (chỉ đường export lọc, draft không mất row);
 *    R6 STT không lưu trong payload — luôn suy từ thứ tự mảng sau lọc.
 *  G2 M72 5 variant:
 *    R7 chỉ variant được chọn có dòng trong payload; 5 variant không
 *       cross-contaminate; chưa chọn -> mọi variant grid rỗng;
 *    R8 draft round-trip per-variant không đổi activation.
 *  G3 nested-grid (M02/M12/M15): policy T/T/T, discriminator giữ nguyên,
 *    dòng chỉ có discriminator (không có dữ liệu khác) vẫn được giữ
 *    (conservative — không coi discriminator là blank).
 *
 * Blank row = row mà MỌI giá trị dữ liệu (bỏ key nội bộ _*) là chuỗi rỗng.
 * "Fixed legal row" của fixed-matrix KHÔNG thuộc corpus này (bảng tĩnh, được
 * phủ bởi tools/test_export_grid_kinds.py TS1-TS6 + test_row_contract_export).
 */
'use strict';

const path = require('path');
const App = require('./ui/app.js');
const FD = require('./ui/form-domain.js');
const G = App.GridCtl;

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed += 1; console.log('PASS  ' + name); }
  else {
    failed += 1;
    console.log('FAIL  ' + name + (extra ? '  | ' + extra : ''));
  }
}
function eqJson(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function blankStore() {
  return { values: {}, checks: {}, loops: {} };
}
/* Row chỉ có dữ liệu ở các tag khai báo; _row_id do GridCtl cấp. */
function row(tags) {
  return Object.assign({}, tags);
}

/* ============================== G1/R1: blank-only row không thành data === */
(function t_blank_only_not_exported() {
  const st = blankStore();
  st.loops.ds_nganh = [row({ ma_nganh: '6100', ten_nganh: 'Bán lẻ' })];
  st.loops.ds_co_dong_nn = [row({})];           // blank hoàn toàn
  const ex = G.exportLoops(st, ['PLI_M08']);
  check('R1: blank-only row KHÔNG xuất thành data row (ds_co_dong_nn)',
    Array.isArray(ex.ds_co_dong_nn) && ex.ds_co_dong_nn.length === 0,
    'got ' + JSON.stringify(ex.ds_co_dong_nn));
  check('R1: dòng CÓ dữ liệu cùng store vẫn xuất nguyên vẹn',
    ex.ds_nganh.length === 1 && ex.ds_nganh[0].ma_nganh === '6100',
    JSON.stringify(ex.ds_nganh));
})();

/* ====================== G1/R2+R3: 1 dòng, blank đầu/giữa/cuối, partial === */
(function t_row_scenarios() {
  const st = blankStore();
  st.loops.ds_nganh = [
    row({}),                                       // blank đầu
    row({ ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }),
    row({}),                                       // blank giữa
    row({ ma_nganh: '0140', ten_nganh: 'Chăn nuôi' }), // partial (không primary)
    row({}),                                       // blank cuối
    row({}),                                       // nhiều blank
  ];
  const ex = G.exportLoops(st, ['PLI_M06']);
  const got = ex.ds_nganh.map(function (r) { return r.ma_nganh; });
  check('R3: blank đầu/giữa/cuối + nhiều blank bị lọc, giữ đúng 2 dòng data',
    eqJson(got, ['0111', '0140']), 'got ' + JSON.stringify(got));
  check('R2: one-row giữa các blank vẫn đúng thứ tự dữ liệu',
    ex.ds_nganh[0].ten_nganh === 'Trồng lúa' &&
      ex.ds_nganh[1].ten_nganh === 'Chăn nuôi',
    JSON.stringify(ex.ds_nganh));
  check('R3: partial row (thiếu primary) KHÔNG bị mất âm thầm',
    ex.ds_nganh[1].ten_nganh === 'Chăn nuôi' &&
      ex.ds_nganh[1].la_nganh_chinh === '',
    JSON.stringify(ex.ds_nganh[1]));
  check('R6: payload KHÔNG chứa field nội bộ _* hay STT lưu sẵn',
    ex.ds_nganh.every(function (r) {
      return Object.keys(r).every(function (k) { return k.charAt(0) !== '_'; }) &&
        !('_stt' in r);
    }), JSON.stringify(ex.ds_nganh));
})();

/* ============ G1/R4: add/delete/reorder/duplicate không đụng grid khác === */
(function t_grid_isolation() {
  const st = blankStore();
  G.addRow(st, 'ds_nganh');
  G.setCell(st, 'ds_nganh', { idx: 0 }, 'ma_nganh', '4711');
  G.addRow(st, 'ds_thanh_vien');
  G.setCell(st, 'ds_thanh_vien', { idx: 0 }, 'ho_ten', 'Nguyễn Văn A');
  const beforeTv = JSON.stringify(st.loops.ds_thanh_vien);

  G.addRow(st, 'ds_nganh');                       // add
  G.moveRow(st, 'ds_nganh', st.loops.ds_nganh[1]._row_id, -1); // reorder
  G.duplicateRow(st, 'ds_nganh', st.loops.ds_nganh[0]._row_id, 'PLI_M06');
  const afterAddDup = JSON.stringify(st.loops.ds_thanh_vien);
  check('R4: add/reorder/duplicate trên ds_nganh không đổi ds_thanh_vien',
    afterAddDup === beforeTv);

  G.deleteRows(st, 'ds_nganh', [st.loops.ds_nganh[0]._row_id]);
  check('R4: delete trên ds_nganh không đổi ds_thanh_vien',
    JSON.stringify(st.loops.ds_thanh_vien) === beforeTv);
  check('R4: duplicate KHÔNG mang duplicateKeys (ma_nganh) sang dòng mới',
    st.loops.ds_nganh.filter(function (r) { return r.ma_nganh === '4711'; })
      .length === 1,
    JSON.stringify(st.loops.ds_nganh));

  G.clearRows(st, 'ds_thanh_vien');
  check('R4: clearRows chỉ clear đúng loop của nó',
    st.loops.ds_thanh_vien.length === 0 && st.loops.ds_nganh.length >= 2);
})();

/* ================================ G1/R5: draft round-trip bảo toàn row === */
(function t_draft_roundtrip() {
  const st = blankStore();
  st.loops.ds_nganh = [
    row({ ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }),
    row({}),                                      // blank row phải SỐNG trong draft
    row({ ma_nganh: '0140', ten_nganh: 'Chăn nuôi' }),
  ];
  G.ensureIds(st);
  const draft = JSON.parse(JSON.stringify({
    v: 2, store: st, checkedForms: ['PLI_M06'], activeDocId: 'PLI_M06',
  }));
  const st2 = draft.store;
  check('R5: draft round-trip không mất row (kể cả blank)',
    st2.loops.ds_nganh.length === 3 &&
      Object.keys(st2.loops.ds_nganh[1]).length > 0,
    JSON.stringify(st2.loops.ds_nganh));
  check('R5: thứ tự và dữ liệu bảo toàn',
    st2.loops.ds_nganh[0].ma_nganh === '0111' &&
      st2.loops.ds_nganh[2].ma_nganh === '0140');
  const ex = G.exportLoops(st2, ['PLI_M06']);
  check('R5: sau round-trip, export vẫn lọc đúng còn 2 dòng data',
    ex.ds_nganh.length === 2, JSON.stringify(ex.ds_nganh));

  /* Legacy-ish: draft cũ có thể chứa row null/garbage — export không ném,
   * không xuất row rác. */
  const st3 = blankStore();
  st3.loops.ds_nganh = [null, { ma_nganh: '0111', ten_nganh: 'Trồng lúa' }, {}];
  const ex3 = G.exportLoops(st3, ['PLI_M06']);
  check('R5: draft legacy (row null/rỗng) export còn đúng 1 dòng data',
    ex3.ds_nganh.length === 1 && ex3.ds_nganh[0].ma_nganh === '0111',
    JSON.stringify(ex3.ds_nganh));
})();

/* ============================= G2/R7+R8: M72 5 variant, no cross-mixing === */
const LOAI_HINH = {
  dntn: 'ds_nganh_dntn',
  tnhh_1tv: 'ds_nganh_tnhh_1tv',
  tnhh_2tv: 'ds_nganh_tnhh_2tv',
  ctcp: 'ds_nganh_ctcp',
  dhdn: 'ds_nganh_dhdn',
};
(function t_m72_variant_isolation() {
  const ids = ['PLI_M72'];
  /* Chưa chọn loại hình: mọi variant grid payload RỖNG. */
  const stNone = blankStore();
  Object.keys(LOAI_HINH).forEach(function (k) {
    stNone.loops[LOAI_HINH[k]] = [row({ ma_nganh: '0111', ten_nganh: 'X' })];
  });
  const exNone = G.exportLoops(stNone, ids);
  check('R7: chưa chọn loai_hinh -> CẢ 5 variant grid payload rỗng',
    Object.keys(LOAI_HINH).every(function (k) {
      return Array.isArray(exNone[LOAI_HINH[k]]) &&
        exNone[LOAI_HINH[k]].length === 0;
    }), JSON.stringify(Object.keys(LOAI_HINH).map(function (k) {
      return (exNone[LOAI_HINH[k]] || []).length;
    })));

  /* Chọn TNHH 2TV trở lên: CHỈ variant đó có dòng; 4 variant còn lại rỗng
   * dù store vẫn giữ dữ liệu của chúng (không cross-contaminate). */
  const st2tv = blankStore();
  st2tv.values['dn.loai_hinh'] = 'TNHH_2TV';
  Object.keys(LOAI_HINH).forEach(function (k) {
    st2tv.loops[LOAI_HINH[k]] = [row({ ma_nganh: '0' + k.length + '00',
      ten_nganh: 'nganh-' + k })];
  });
  const ex2tv = G.exportLoops(st2tv, ids);
  check('R7: chọn TNHH_2TV -> chỉ ds_nganh_tnhh_2tv có dòng',
    (ex2tv.ds_nganh_tnhh_2tv || []).length === 1 &&
      Object.keys(LOAI_HINH).filter(function (k) { return k !== 'tnhh_2tv'; })
        .every(function (k) {
          return (ex2tv[LOAI_HINH[k]] || []).length === 0;
        }),
    JSON.stringify(Object.keys(LOAI_HINH).map(function (k) {
      return [k, (ex2tv[LOAI_HINH[k]] || []).length];
    })));

  /* R8: draft round-trip per-variant — activation không đổi sau reload. */
  const draft = JSON.parse(JSON.stringify(st2tv));
  const exRe = G.exportLoops(draft, ids);
  check('R8: draft round-trip giữ activation (vẫn chỉ TNHH_2TV xuất)',
    (exRe.ds_nganh_tnhh_2tv || []).length === 1 &&
      (exRe.ds_nganh_ctcp || []).length === 0);
})();

/* ============================ G3: nested-grid discriminator không bị lọc === */
(function t_nested_discriminator_kept() {
  const st = blankStore();
  /* Row chỉ có loai_dong (discriminator) — conservative: coi là CÓ cấu trúc,
   * không phải blank, giữ nguyên (không âm thầm mất cấu trúc dòng). */
  st.loops.nddpl_uy_quyen_chu_so_huu = [
    { loai_dong: 'nddpl', ho_ten: 'Trần Thị B' },
    { loai_dong: 'chu_so_huu' },
  ];
  const ex = G.exportLoops(st, ['PLI_M02']);
  check('G3: nested-grid dòng có discriminator được giữ (kể cả dòng chỉ có discriminator)',
    Array.isArray(ex.nddpl_uy_quyen_chu_so_huu) &&
      ex.nddpl_uy_quyen_chu_so_huu.length === 2,
    JSON.stringify(ex.nddpl_uy_quyen_chu_so_huu));
})();

/* ---------------------------------------------------------------- kết luận */
console.log('-'.repeat(60));
console.log('test_row_contract_corpus: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
