'use strict';

/*
 * Lane W2 — formula `product(<col_tag>[, <col_tag>...])` cho fixed-matrix.
 *
 * Quyết định owner D1.4=A: "giá trị loại cổ phần = số lượng × mệnh giá" là
 * projection nên app_web/ui/fixed-matrix.js phải TÍNH LẠI từ các ô input,
 * không tin giá trị lưu trong draft. Grammar được khai báo lại ở
 * tools/form_specs/schema/table_kinds.schema.json (fixed_matrix.totals), và
 * phía Python đối ứng là tools/docx_render.py::_TOTALS_FORMULA_RE — hai phía
 * cùng một ngữ nghĩa:
 *
 * [W2]  product() cộng dồn tích từng dòng; dòng KHÔNG kê khai gì bị bỏ qua
 *       (như sum bỏ ô rỗng); dòng có kê khai mà THIẾU >= 1 thừa số làm ô tổng
 *       KHÔNG XÁC ĐỊNH -> in TRỐNG (''), tuyệt đối không in 0;
 * [NEG] formula/tag lạ ('sqrt(x)', 'PRODUCT(...)', tag không khai báo) vẫn fail
 *       loud blocking FORMULA_UNSUPPORTED như cũ;
 * [SUM] hành vi sum() không đổi (bỏ ô rỗng, trắng tinh -> 0) và hai formula
 *       sống chung trong cùng spec không phá nhau;
 * [FIX] recompute viết kết quả vào ô tổng: đủ dữ liệu -> số thô, thiếu ->
 *       chuỗi rỗng; con số cũ trong draft không được thắng.
 *
 * Chạy: node app_web/test_fixed_matrix_product.js
 */

const assert = require('assert');
const Matrix = require('./ui/fixed-matrix.js');

const SEM = 'co_cau_loai_co_phan';
const PRODUCT_FORMULA = 'product(so_luong, menh_gia_co_phan)';

function makeSpec(totals) {
  return {
    form_id: 'PLI_M04_W2_DEMO',
    kind: 'fixed-matrix',
    semantic_key: SEM,
    columns: [
      { header: 'Loại cổ phần', tag: null, inputType: 'readonly' },
      { header: 'Số lượng', tag: 'so_luong', inputType: 'money' },
      { header: 'Mệnh giá cổ phần (VNĐ)', tag: 'menh_gia_co_phan',
        inputType: 'money' },
      { header: 'Giá trị (VNĐ)', tag: 'gia_tri_vnd', inputType: 'money' }
    ],
    fixed_rows: [
      { id: 'cp_pho_thong', label: 'Cổ phần phổ thông' },
      { id: 'cp_uu_dai_khac', label: 'Các cổ phần ưu đãi khác' },
      { id: 'tong_so', label: 'Tổng số', output_only: true }
    ],
    totals: totals
  };
}

const KEY_SPEC = { semantic_key: SEM };

const PRODUCT_TOTAL = {
  id: 'tong_so',
  formula: PRODUCT_FORMULA,
  target: 'outputOnly',
  target_tag: 'gia_tri_vnd'
};

function emptyDraft() {
  return { values: {} };
}

function fill(cells) {
  const draft = emptyDraft();
  Object.keys(cells).forEach(function (key) {
    const parts = key.split('.');
    Matrix.setCell(draft, KEY_SPEC, parts[0], parts[1], cells[key]);
  });
  return draft;
}

function totalCell(spec, draft, tag) {
  const projection = Matrix.recompute(spec, draft);
  const row = projection.rows.filter(r => r.id === 'tong_so')[0];
  assert(row, 'spec thiếu hàng tổng tong_so');
  return row.cells[tag];
}

/* ---------------------------------------------------------------- [W2] */

// 10.000 x 10.000 + 5.000 x 20.000 = 200.000.000
const SPEC = makeSpec([PRODUCT_TOTAL]);
const FULL_DRAFT = fill({
  'cp_pho_thong.so_luong': '10.000',
  'cp_pho_thong.menh_gia_co_phan': '10.000',
  'cp_uu_dai_khac.so_luong': '5.000',
  'cp_uu_dai_khac.menh_gia_co_phan': '20.000'
});
const beforeExport = JSON.stringify(FULL_DRAFT);
assert.strictEqual(totalCell(SPEC, FULL_DRAFT, 'gia_tri_vnd'), 200000000);
assert.deepStrictEqual(Matrix.validate(SPEC, FULL_DRAFT), [],
  'dữ liệu hợp lệ không được sinh blocking error');

// thập phân dấu phẩy + nghìn dấu chấm vẫn đi qua numberValue() hiện có
assert.strictEqual(totalCell(SPEC, fill({
  'cp_pho_thong.so_luong': '3',
  'cp_pho_thong.menh_gia_co_phan': '0,5'
}), 'gia_tri_vnd'), 1.5);
assert.strictEqual(totalCell(SPEC, fill({
  'cp_pho_thong.so_luong': '3.500',
  'cp_pho_thong.menh_gia_co_phan': '10.000,25'
}), 'gia_tri_vnd'), 35000875);

// một dòng khai thiếu mệnh giá -> tổng KHÔNG XÁC ĐỊNH -> trống, không phải 0
assert.strictEqual(totalCell(SPEC, fill({
  'cp_pho_thong.so_luong': '10.000',
  'cp_pho_thong.menh_gia_co_phan': '10.000',
  'cp_uu_dai_khac.so_luong': '5.000'
}), 'gia_tri_vnd'), '');

// dòng bỏ trống hoàn toàn bị bỏ qua chứ không tính thành 0 đồng
assert.strictEqual(totalCell(SPEC, fill({
  'cp_pho_thong.so_luong': '7',
  'cp_pho_thong.menh_gia_co_phan': '1.000'
}), 'gia_tri_vnd'), 7000);

// chưa kê khai gì -> trống (không in 0), draft gốc không bị ghi đè
const EMPTY_DRAFT = emptyDraft();
assert.strictEqual(totalCell(SPEC, EMPTY_DRAFT, 'gia_tri_vnd'), '');
assert.deepStrictEqual(EMPTY_DRAFT.values, {});
assert.strictEqual(JSON.stringify(FULL_DRAFT), beforeExport,
  'recompute/export không được mutate draft');

/* --------------------------------------------------------------- [NEG] */

[{
  name: 'sqrt(x)',
  formula: 'sqrt(gia_tri_vnd)'
}, {
  name: 'PRODUCT viết hoa',
  formula: 'PRODUCT(so_luong, menh_gia_co_phan)'
}, {
  name: 'tag không khai báo',
  formula: 'product(so_luong, gia_tri_khong_ton_tai)'
}, {
  name: 'product() không tham số',
  formula: 'product()'
}].forEach(function (variant) {
  const badSpec = makeSpec([Object.assign({}, PRODUCT_TOTAL,
    { formula: variant.formula })]);
  const message = variant.name + ' phải fail loud';
  const validation = Matrix.validate(badSpec, fill({
    'cp_pho_thong.so_luong': '1',
    'cp_pho_thong.menh_gia_co_phan': '1'
  }));
  const unsupported = validation.filter(e => e.code === 'FORMULA_UNSUPPORTED');
  assert(unsupported.length > 0, message + ': %j'.replace('%j',
    JSON.stringify(validation)));
  assert(unsupported.every(e => e.severity === 'blocking'),
    variant.name + ': lỗi formula lạ phải blocking');
  assert.strictEqual(
    Matrix.formulaValue(variant.formula, badSpec, emptyDraft()).supported,
    false);

  // exportMatrix cũng phải bơm error blocking ra ngoài cho runtime chặn
  const exported = Matrix.exportMatrix(badSpec, emptyDraft());
  assert(exported.errors.some(e => e.code === 'FORMULA_UNSUPPORTED' &&
    e.severity === 'blocking'), variant.name + ': exportMatrix mất lỗi');
});

/* --------------------------------------------------------------- [SUM] */

const MIXED_SPEC = makeSpec([
  PRODUCT_TOTAL,
  { id: 'tong_so', formula: 'sum(so_luong)', target: 'outputOnly',
    target_tag: 'so_luong' }
]);
const MIXED_DRAFT = fill({
  'cp_pho_thong.so_luong': '10.000',
  'cp_pho_thong.menh_gia_co_phan': '10.000'
});
assert.strictEqual(totalCell(MIXED_SPEC, MIXED_DRAFT, 'so_luong'), 10000,
  'sum giữ hành vi v1: bỏ ô rỗng rồi cộng');
assert.strictEqual(totalCell(MIXED_SPEC, MIXED_DRAFT, 'gia_tri_vnd'),
  100000000, 'product và sum sống chung không phá nhau');

// regress: sum khi trắng tinh vẫn là 0 như cũ
assert.strictEqual(totalCell(makeSpec([{ id: 'tong_so',
  formula: 'sum(so_luong)', target: 'outputOnly', target_tag: 'so_luong' }]),
emptyDraft(), 'so_luong'), 0);

// helper mới được expose đúng flag supported / rejected
assert.strictEqual(Matrix.sumFormula('sum(so_luong)', SPEC,
  emptyDraft()).supported, true);
assert.strictEqual(Matrix.productFormula(PRODUCT_FORMULA, SPEC,
  emptyDraft()).supported, true);
assert.strictEqual(Matrix.productFormula('sqrt(so_luong)', SPEC,
  emptyDraft()).supported, false);
// cột thừa số không tồn tại trong spec -> coi là spec hỏng, fail loud
const NARROW_SPEC = {
  form_id: 'PLI_M04_W2_DEMO',
  kind: 'fixed-matrix',
  semantic_key: SEM,
  columns: [
    { header: 'Loại cổ phần', tag: null, inputType: 'readonly' },
    { header: 'Số lượng', tag: 'so_luong', inputType: 'money' }
  ],
  fixed_rows: [
    { id: 'cp_pho_thong', label: 'Cổ phần phổ thông' },
    { id: 'tong_so', label: 'Tổng số', output_only: true }
  ],
  totals: [{ id: 'tong_so', formula: 'product(so_luong, menh_gia_co_phan)',
    target_tag: 'so_luong' }]
};
assert.strictEqual(Matrix.productFormula(NARROW_SPEC.totals[0].formula,
  NARROW_SPEC, emptyDraft()).supported, false,
  'thừa số không nằm trong columns phải bị từ chối');
assert.strictEqual(Matrix.productFormula('sum(so_luong)', SPEC,
  emptyDraft()).supported, false, 'productFormula chỉ nhận product()');

/* --------------------------------------------------------------- [FIX] */

{
  const spec = SPEC;
  const filled = fill({
    'cp_pho_thong.so_luong': '2',
    'cp_pho_thong.menh_gia_co_phan': '500'
  });
  Matrix.setCell(filled, KEY_SPEC, 'tong_so', 'gia_tri_vnd', '999999');
  const exported = Matrix.exportMatrix(spec, filled);
  const totalRow = exported.rows.filter(r => r.id === 'tong_so')[0];
  assert.strictEqual(totalRow.cells.gia_tri_vnd, 1000,
    'draft không được thắng projection');
  assert.deepStrictEqual(exported.errors, []);

  // chiều ngược lại: tổng KHÔNG xác định mà draft còn giữ số cũ -> in trống
  const staleBlank = fill({
    'cp_pho_thong.so_luong': '2',
    'cp_uu_dai_khac.so_luong': '3'   // có số lượng nhưng thiếu mệnh giá
  });
  Matrix.setCell(staleBlank, KEY_SPEC, 'tong_so', 'gia_tri_vnd', '12345');
  const projected = Matrix.exportMatrix(spec, staleBlank);
  assert.strictEqual(projected.rows.filter(r => r.id === 'tong_so')[0]
    .cells.gia_tri_vnd, '', 'ô tổng không xác định phải in trống');
  assert.deepStrictEqual(projected.errors, [],
    'trống không phải là lỗi validation');

  console.log('fixed-matrix product contract: [W2]+[NEG]+[SUM]+[FIX] PASS');
}
