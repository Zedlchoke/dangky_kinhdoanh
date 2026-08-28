'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const Matrix = require('./ui/fixed-matrix.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
function load(formId) {
  return JSON.parse(fs.readFileSync(
    path.join(BLOCKS, formId + '.json'), 'utf8'));
}

function paragraphLabels(doc, start, end) {
  /* [Lead sync 2026-08-28] sau regen cap-von (merge fc07c69), bảng nguồn vốn
   * là w:tbl thật trong blocks: nhãn cột nằm ở cells hàng đầu, nhãn dòng nằm
   * ở cells[0] các hàng sau — không còn paragraph phẳng. Trích theo cấu trúc
   * bảng: header cells + cells[0] từng hàng, dừng ở nhãn `end`. */
  const labels = [];
  let done = false;
  (doc.blocks || []).forEach(function (block) {
    if (!Array.isArray(block.rows) || done) return;
    const firstCell = (((block.rows[0] || {}).cells || [])[0] || {}).runs;
    const head = (firstCell || []).map(r => r.text || '').join('').trim();
    if (head !== start) return;
    (block.rows || []).forEach(function (row, ri) {
      (row.cells || []).slice(0, ri === 0 ? row.cells.length : 1)
        .forEach(function (cell) {
          const cellText = (cell.runs || []).map(r => r.text || '').join('').trim();
          if (cellText) labels.push(cellText);
        });
    });
    done = true;
  });
  return labels;
}

function draft() {
  return { values: {} };
}

const m03 = load('PLI_M03');
const sourceRows = paragraphLabels(m03, 'Loại nguồn vốn', 'Tổng cộng');
assert.deepStrictEqual(sourceRows, [
  'Loại nguồn vốn', 'Số tiền (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)',
  'Tỷ lệ (%)', 'Vốn ngân sách nhà nước', 'Vốn tư nhân', 'Vốn nước ngoài',
  'Vốn khác', 'Tổng cộng'
]);

const sourceLabels = sourceRows.slice(3).map(function (label) {
  return label === 'Tổng cộng' ? 'Tổng cộng' : label;
});
const spec = {
  form_id: 'PLI_M03',
  kind: 'fixed-matrix',
  semantic_key: 'nguon_von_dieu_le',
  fixed_rows: sourceLabels.map(function (label, index) {
    return { id: ['von_nsnn', 'von_tu_nhan', 'von_nuoc_ngoai',
      'von_khac', 'tong_cong'][index], label: label };
  }),
  columns: [
    { tag: 'so_tien', inputType: 'money' },
    { tag: 'ty_le', inputType: 'percent' }
  ],
  totals: [
    { id: 'tong_cong', formula: 'sum(so_tien)', target: 'outputOnly',
      target_tag: 'so_tien' },
    { id: 'tong_cong', formula: 'sum(ty_le)', target: 'outputOnly',
      target_tag: 'ty_le' }
  ]
};

assert.deepStrictEqual(Matrix.fixedRows(spec).map(r => r.label), [
  'Vốn ngân sách nhà nước', 'Vốn tư nhân', 'Vốn nước ngoài', 'Vốn khác',
  'Tổng cộng'
]);
assert.strictEqual(Matrix.canDelete(spec, 'von_tu_nhan'), false);
assert.strictEqual(Matrix.deleteRow(draft(), spec, 'von_tu_nhan'), false);
assert.strictEqual(Matrix.deleteRows(draft(), spec, ['von_tu_nhan']), 0);

const d = draft();
Matrix.setCell(d, spec, 'von_tu_nhan', 'so_tien', '60.000.000');
Matrix.setCell(d, spec, 'von_tu_nhan', 'ty_le', '60');
Matrix.setCell(d, spec, 'von_khac', 'so_tien', '40.000.000');
Matrix.setCell(d, spec, 'von_khac', 'ty_le', '40');
// A stale total in the draft must not win over the declared formula.
Matrix.setCell(d, spec, 'tong_cong', 'so_tien', '999');
const beforeExport = JSON.stringify(d);
const exported = Matrix.exportMatrix(spec, d);
const total = exported.rows.filter(r => r.id === 'tong_cong')[0];
assert.strictEqual(total.cells.so_tien, 100000000);
assert.strictEqual(total.cells.ty_le, 100);
assert.strictEqual(JSON.stringify(d), beforeExport);
assert.strictEqual(exported.errors.length, 0);

const hookCalls = [];
const bad = draft();
Matrix.setCell(bad, spec, 'von_tu_nhan', 'so_tien', 'not-money');
Matrix.setCell(bad, spec, 'von_tu_nhan', 'ty_le', '101');
const validation = Matrix.validate(spec, bad, {
  money: function (value, context) {
    hookCalls.push(context.column.tag);
    return value === 'not-money' ? {
      code: 'MONEY_HOOK', message: 'money rejected', severity: 'blocking'
    } : true;
  },
  percent: function () {
    hookCalls.push('percent');
    return { code: 'PERCENT_HOOK', message: 'percent rejected',
      severity: 'warning' };
  }
});
assert(validation.some(e => e.code === 'MONEY'));
assert(validation.some(e => e.code === 'PERCENT'));
assert(hookCalls.indexOf('percent') >= 0);

const m04 = load('PLI_M04');
// [Lead sync 2026-08-28] bảng co_cau sinh mới không có cột STT in sẵn
// (engine tự đánh số {_stt}) — nhãn bắt đầu từ 'Loại cổ phần'. Lưu ý nguyên
// văn TT 121: bảng co_cau giữ 'Các cổ phần ưu đãi khác', bảng chào bán dùng
// 'Cổ phần ưu đãi khác' (khác biệt có chủ đích giữa 2 bảng).
const shareRows = paragraphLabels(m04, 'Loại cổ phần', 'Tổng số');
assert(shareRows.some(label => label === 'Cổ phần phổ thông'));
assert(shareRows.some(label => label === 'Các cổ phần ưu đãi khác'));
assert(shareRows.indexOf('Tổng số') >
  shareRows.indexOf('Các cổ phần ưu đãi khác'));

console.log('fixed-matrix contract: production fixtures, fixed rows, totals, hooks PASS');
