/*
 * Contract test for nested-grid using the production PLI_M02 N1 header block.
 * Run with: node app_web/test_nested_grid.js
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const NestedGrid = require('./ui/nested-grid.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
const production = JSON.parse(fs.readFileSync(
  path.join(BLOCKS, 'PLI_M02.json'), 'utf8'));

function paragraphText(block) {
  return (block.runs || []).map(run => run && run.text || '').join('');
}

const headerText = production.blocks
  .map(paragraphText)
  .find(text => text.includes('STTTên người đại diện') &&
    text.includes('Tổng giá trị vốn được đại diện'));
assert.ok(headerText, 'PLI_M02 N1 production header exists');
assert.ok(headerText.includes('Thời điểm đại diện phần vốn'));
assert.ok(headerText.endsWith('12345678910111213' +
  '- Thông tin về Giấy chứng nhận đăng ký đầu tư (chỉ kê khai nếu chủ sở hữu là nhà đầu tư nước ngoài):'));

const columns = [
  'stt', 'ten_nguoi_dai_dien', 'ngay_sinh', 'gioi_tinh',
  'giay_to_so', 'giay_to_ngay', 'giay_to_co_quan',
  'quoc_tich', 'dan_toc', 'dia_chi', 'von_duoc_uy_quyen_vnd',
  'chu_ky', 'ghi_chu'
].map((tag, col_index) => ({ tag, col_index }));

const spec = {
  form_id: 'PLI_M02',
  kind: 'nested-grid',
  section_id: 'nddpl_uy_quyen_chu_so_huu',
  semantic_key: 'nddpl_uy_quyen_chu_so_huu',
  header_rows: [
    [
      { text: 'STT', rowspan: 2 },
      { text: 'Tên người đại diện', rowspan: 2 },
      { text: 'Ngày, tháng, năm sinh', rowspan: 2 },
      { text: 'Giới tính', rowspan: 2 },
      { text: 'Số, ngày cấp, cơ quan cấp Giấy tờ pháp lý', colspan: 3 },
      { text: 'Quốc tịch', rowspan: 2 },
      { text: 'Dân tộc', rowspan: 2 },
      { text: 'Địa chỉ liên lạc', rowspan: 2 },
      { text: 'Vốn được ủy quyền', colspan: 2 },
      { text: 'Chữ ký', rowspan: 2 },
      { text: 'Ghi chú', rowspan: 2 }
    ],
    [
      { text: 'Số' }, { text: 'Ngày cấp' }, { text: 'Cơ quan cấp' },
      { text: 'VNĐ' }, { text: 'Tỷ lệ (%)' }
    ]
  ],
  row_groups: [
    { group_id: 'ndd_uy_quyen',
      match: { tag: 'loai_dong', equals: 'ndd_uy_quyen' },
      required_columns: ['ten_nguoi_dai_dien', 'von_duoc_uy_quyen_vnd'] },
    { group_id: 'ndd_pl',
      match: { tag: 'loai_dong', equals: 'ndd_pl' },
      required_columns: ['ten_nguoi_dai_dien'] }
  ],
  columns: columns,
  discriminator: { tag: 'loai_dong', values: ['ndd_pl', 'ndd_uy_quyen'] },
  min_rows: 0,
  max_rows: null
};

assert.deepStrictEqual(NestedGrid.validateContract(spec), []);
const layout = NestedGrid.headerLayout(spec);
assert.deepStrictEqual(layout.errors, []);
assert.strictEqual(layout.columns.length, 13);
assert.deepStrictEqual(layout.columns.map(column => column.col_index),
  Array.from({ length: 13 }, (_, index) => index));
assert.strictEqual(layout.rows[0][0].rowspan, 2);
assert.strictEqual(layout.rows[0][4].colspan, 3);
assert.strictEqual(layout.rows[0][8].colspan, 2);
assert.strictEqual(layout.rows[1].length, 5);

const sourceRows = [
  { loai_dong: 'ndd_uy_quyen', ten_nguoi_dai_dien: 'Nguyễn A',
    von_duoc_uy_quyen_vnd: '1000000' },
  { loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'Trần B' }
];
const normalized = NestedGrid.normalizeRows(spec, sourceRows);
assert.deepStrictEqual(normalized.errors, []);
assert.deepStrictEqual(normalized.rows.map(row => row._row_id), ['r1', 'r2']);
assert.deepStrictEqual(NestedGrid.validate(spec, normalized.rows), []);

const missingGroupField = sourceRows.map(row => Object.assign({}, row));
missingGroupField[0].von_duoc_uy_quyen_vnd = '';
assert.ok(NestedGrid.validate(spec, missingGroupField)
  .some(error => error.code === 'REQUIRED_FIELD' &&
    error.key.endsWith('.r1.von_duoc_uy_quyen_vnd')));

const badDiscriminator = [{ loai_dong: 'unknown', ten_nguoi_dai_dien: 'Nguyễn A' }];
assert.ok(NestedGrid.validate(spec, badDiscriminator)
  .some(error => error.code === 'DISCRIMINATOR_INVALID'));

const malformed = Object.assign({}, spec, {
  header_rows: [[{ text: 'broken', colspan: 14 }]]
});
assert.ok(NestedGrid.headerLayout(malformed).errors.length);
assert.ok(NestedGrid.validate(Object.assign({}, spec, {
  row_groups: [{ group_id: 'bad', match: { nonsense: true } }]
}), sourceRows).some(error => error.code === 'NESTED_CONTRACT_INVALID'));

console.log('PASS nested-grid production contract: PLI_M02 N1 headers, columns, discriminator');
