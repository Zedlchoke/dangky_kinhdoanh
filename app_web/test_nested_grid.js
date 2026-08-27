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

/* [Lead sync sau regen R3B1] N1 đã dựng thành w:tbl thật (loop block, headerRows
 * 2 tầng) — paragraph glue "STTTên người đại diện…12345678910" không còn là nguồn.
 * Header production tra theo NỘI DUNG của loop block, không phải index tuyệt đối. */
const n1Loop = production.blocks.find(block =>
  block.t === 'loop' && block.loop === 'ds_nddpl_uy_quyen_chu_so_huu');
assert.ok(n1Loop, 'PLI_M02 N1 production loop block exists (rebuild R3B1)');
assert.strictEqual(n1Loop.headerRows.length, 2,
  'N1 header hai tầng (nhóm cột gộp + dòng con)');
const cellText = cell =>
  (cell.runs || []).map(run => run && run.text || '').join('');
const headerText = n1Loop.headerRows.map(ri =>
  (n1Loop.rows[ri].cells || []).map(cellText).join('')).join('');
assert.ok(headerText.includes('Tên người đại diện theo pháp luật'),
  'N1 header mất cột Tên người đại diện');
assert.ok(headerText.includes('Vốn được ủy quyền') &&
  headerText.includes('Tỷ lệ (%)'), 'N1 header mất nhóm Vốn được ủy quyền');
/* Gap đã ghi nhận: 2 nhóm cuối ("Tổng giá trị vốn được đại diện", "Thời điểm
 * đại diện phần vốn") chưa đủ evidence khai tag canonical → KHAI THIẾU trong
 * bảng rebuild. Nếu xuất hiện lại mà không có quyết định owner là sai policy. */
assert.ok(!headerText.includes('Tổng giá trị vốn được đại diện'),
  'N1 không được tự khai nhóm chưa có evidence');
assert.ok(!headerText.includes('Thời điểm đại diện phần vốn'),
  'N1 không được tự khai nhóm chưa có evidence');
/* Trim keep_from giữ chuỗi pháp lý dính kèm thành paragraph riêng; digit-run
 * glue phải biến mất hoàn toàn khỏi các đoạn văn bản của form. */
const paraTexts = production.blocks.filter(b => b.t === 'p').map(paragraphText);
assert.ok(paraTexts.some(text =>
  text.includes('- Thông tin về Giấy chứng nhận đăng ký đầu tư')),
  'N1 mất chuỗi pháp lý trim đã GIỮ');
assert.ok(!paraTexts.some(text => /12345678910/.test(text)),
  'glue digit-run phải biến mất sau rebuild');

/* [Lead sync] 14 cột vật lý khớp contract production FORM_GRID_META PLI_M02
 * (form-domain.js): thêm ty_le là cột con thứ hai của "Vốn được ủy quyền". */
const columns = [
  'stt', 'ten_nguoi_dai_dien', 'ngay_sinh', 'gioi_tinh',
  'giay_to_so', 'giay_to_ngay', 'giay_to_co_quan',
  'quoc_tich', 'dan_toc', 'dia_chi', 'von_duoc_uy_quyen_vnd',
  'ty_le', 'chu_ky', 'ghi_chu'
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
      /* [Lead sync] nhãn khớp nguồn/template thật sau regen R3B1 */
      { text: 'Số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân', colspan: 3 },
      { text: 'Quốc tịch', rowspan: 2 },
      { text: 'Dân tộc', rowspan: 2 },
      { text: 'Địa chỉ liên lạc', rowspan: 2 },
      { text: 'Vốn được ủy quyền', colspan: 2 },
      { text: 'Chữ ký của người đại diện theo pháp luật/người đại diện theo ủy quyền', rowspan: 2 },
      { text: 'Ghi chú (nếu có)', rowspan: 2 }
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
  /* D2.7=A (commit 29b1efa): min 1 dòng / max không giới hạn — khớp contract. */
  min_rows: 1,
  max_rows: null
};

assert.deepStrictEqual(NestedGrid.validateContract(spec), []);
const layout = NestedGrid.headerLayout(spec);
assert.deepStrictEqual(layout.errors, []);
assert.strictEqual(layout.columns.length, 14);
assert.deepStrictEqual(layout.columns.map(column => column.col_index),
  Array.from({ length: 14 }, (_, index) => index));
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

/* [Lead sync] lưới giờ rộng 14 cột vật lý nên colspan 14 là HỢP LỆ;
 * cell sai vẫn phải là colspan vượt tổng bề rộng (15). */
const malformed = Object.assign({}, spec, {
  header_rows: [[{ text: 'broken', colspan: 15 }]]
});
assert.ok(NestedGrid.headerLayout(malformed).errors.length);
assert.ok(NestedGrid.validate(Object.assign({}, spec, {
  row_groups: [{ group_id: 'bad', match: { nonsense: true } }]
}), sourceRows).some(error => error.code === 'NESTED_CONTRACT_INVALID'));

console.log('PASS nested-grid production contract: PLI_M02 N1 headers, columns, discriminator');
