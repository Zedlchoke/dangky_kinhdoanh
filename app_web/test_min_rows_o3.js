/*
 * O3 min_rows enforcement (owner decision packet v7, 2026-09-06).
 *
 * Quyết định O3: `min_rows` chỉ enforce KHI section ACTIVE (activeWhen);
 * section inactive có 0 dòng là HỢP LỆ; section active phải có ít nhất
 * `min_rows` dòng BUSINESS-DATA; blank UI row không được tính; max_rows=null
 * khi luật không giới hạn.
 *
 * Phạm vi test:
 *  1. nested-grid.js validate(): đọc spec.min_rows/max_rows, đếm business
 *     rows qua businessRowsOf (loại cột outputOnly/stt/discriminator/_key),
 *     ctx.isActive=false -> không MIN_ROWS.
 *  2. form-domain.js validateSectionEntry/validateDocument: section
 *     nested-grid thật của PLI_M02 surface MIN_ROWS blocking; activeWhen
 *     (entry|spec) đánh giá qua evalActiveWhen — một nguồn chân lý.
 *  3. Export guard HAI CHIỀU:
 *     - chiều chặn: MIN_ROWS là blocking -> chính sách chặn export hiện có
 *       (app.js buildExportData lọc severity==='blocking') chặn hồ sơ;
 *     - chiều không-lọt: GridCtl.exportLoops lọc payload của section
 *       inactive có activeWhen (dữ liệu cũ không lọt DOCX).
 *     Python side (tools/docx_render.py _expand_loops) giữ guard blank-row:
     * nó KHÔNG biết activeWhen (chỉ nhận payload) nên điểm enforce O3 là
     * lớp export JS; render trực tiếp vẫn được guard blank-row chặn dòng
     * trống in ra giấy.
 *
 * Run: node app_web/test_min_rows_o3.js
 */
'use strict';

const assert = require('assert');
const NestedGrid = require('./ui/nested-grid.js');
const FD = require('./ui/form-domain.js');
const H = require('./ui/app.js');

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else { failed++; console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

/* Spec nested-grid production-shape (PLI_M02 N1) — min_rows 1, có discriminator
 * + cột outputOnly (chu_ky) + cột stt để phủ đúng các trường hợp cấu trúc. */
function mkSpec(extra) {
  return Object.assign({
    kind: 'nested-grid',
    form_id: 'PLI_M02',
    section_id: 'nddpl_uy_quyen_chu_so_huu',
    semantic_key: 'ds_nddpl_uy_quyen_chu_so_huu',
    loop: 'ds_nddpl_uy_quyen_chu_so_huu',
    header_rows: [[
      { text: 'STT', rowspan: 2 },
      { text: 'Tên người đại diện', rowspan: 2 },
      { text: 'Số giấy tờ', rowspan: 2 },
      { text: 'Chữ ký', rowspan: 2 }
    ]],
    row_groups: [{
      group_id: 'ndd_pl',
      match: { tag: 'loai_dong', equals: 'ndd_pl' },
      required_columns: ['ten_nguoi_dai_dien']
    }],
    discriminator: { tag: 'loai_dong', values: ['ndd_pl'] },
    columns: [
      { tag: 'stt', col_index: 0, type: 'stt' },
      { tag: 'ten_nguoi_dai_dien', col_index: 1, type: 'text' },
      { tag: 'giay_to_so', col_index: 2, type: 'text' },
      { tag: 'chu_ky', col_index: 3, type: 'outputOnly' }
    ],
    min_rows: 1,
    max_rows: null
  }, extra || {});
}

const BIZ_ROW = { loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'TRAN B' };

console.log('--- 1. nested-grid.validate: O3 min_rows/max_rows');
{
  const spec = mkSpec();

  // (a) ACTIVE + 0 dòng -> MIN_ROWS blocking, đúng key section.
  const a = NestedGrid.validate(spec, []);
  check('(a) active + 0 dòng -> MIN_ROWS blocking',
    a.some(e => e.code === 'MIN_ROWS' && e.severity === 'blocking' &&
      e.key === spec.semantic_key && e.docId === 'PLI_M02'),
    JSON.stringify(a));

  // (b) ACTIVE + 1 blank row (mọi ô rỗng) -> MIN_ROWS blocking.
  const b = NestedGrid.validate(spec, [{ _row_id: 'r1' }]);
  check('(b) active + 1 blank row -> MIN_ROWS blocking',
    b.some(e => e.code === 'MIN_ROWS' && e.severity === 'blocking'),
    JSON.stringify(b.map(e => e.code)));

  // (b2) ACTIVE + dòng chỉ có discriminator -> vẫn MIN_ROWS (vai trò dòng
  // chưa phải business data; REQUIRED_FIELD của row-group vẫn song song).
  const b2 = NestedGrid.validate(spec, [{ _row_id: 'r1', loai_dong: 'ndd_pl' }]);
  check('(b2) active + dòng chỉ có discriminator -> MIN_ROWS blocking',
    b2.some(e => e.code === 'MIN_ROWS') &&
      b2.some(e => e.code === 'REQUIRED_FIELD'),
    JSON.stringify(b2.map(e => e.code)));

  // (b3) ACTIVE + dòng chỉ có ô cấu trúc (stt + chu_ky outputOnly) -> MIN_ROWS.
  const b3 = NestedGrid.validate(spec, [
    { _row_id: 'r1', stt: '1', chu_ky: 'AB' }]);
  check('(b3) active + dòng chỉ có ô stt/outputOnly -> MIN_ROWS blocking',
    b3.some(e => e.code === 'MIN_ROWS'), JSON.stringify(b3.map(e => e.code)));

  // (b4) ACTIVE + 1 dòng business-data -> không MIN_ROWS.
  const b4 = NestedGrid.validate(spec, [Object.assign({ _row_id: 'r1' }, BIZ_ROW)]);
  check('(b4) active + 1 dòng business-data -> 0 MIN_ROWS',
    !b4.some(e => e.code === 'MIN_ROWS'), JSON.stringify(b4.map(e => e.code)));

  // (c) INACTIVE + 0 dòng -> PASS (0 dòng hợp lệ cho section inactive).
  const c = NestedGrid.validate(spec, [], { isActive: false });
  check('(c) inactive + 0 dòng -> PASS (không MIN_ROWS)',
    c.length === 0, JSON.stringify(c));

  // (d) INACTIVE có dữ liệu cũ -> không block ở lớp validate.
  const d = NestedGrid.validate(spec,
    [{ _row_id: 'rOld', loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'CU' }],
    { isActive: false });
  check('(d) inactive + dữ liệu cũ -> validate không block MIN_ROWS',
    !d.some(e => e.code === 'MIN_ROWS'), JSON.stringify(d.map(e => e.code)));

  // max_rows=null -> không bao giờ MAX_ROWS; max_rows số -> warning (không block).
  const big = [
    { _row_id: 'r1' }, { _row_id: 'r2' }, { _row_id: 'r3' }].map((r, i) =>
      Object.assign(r, { loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'X' + i }));
  const noMax = NestedGrid.validate(mkSpec({ max_rows: null }), big);
  check('max_rows=null -> không MAX_ROWS (luật không giới hạn)',
    !noMax.some(e => e.code === 'MAX_ROWS'), JSON.stringify(noMax.map(e => e.code)));
  const withMax = NestedGrid.validate(mkSpec({ min_rows: 0, max_rows: 2 }), big);
  check('max_rows=2 vượt -> MAX_ROWS warning (không blocking)',
    withMax.some(e => e.code === 'MAX_ROWS' && e.severity === 'warning') &&
      !withMax.some(e => e.code === 'MAX_ROWS' && e.severity === 'blocking'),
    JSON.stringify(withMax.map(e => e.code)));
  // Không khai min_rows -> hành vi cũ (không MIN_ROWS).
  const noMin = NestedGrid.validate(mkSpec({ min_rows: undefined }), []);
  check('spec không khai min_rows -> không MIN_ROWS (back-compat)',
    !noMin.some(e => e.code === 'MIN_ROWS'), JSON.stringify(noMin.map(e => e.code)));

  // businessRowsOf: helper đếm dùng chung export guard.
  check('businessRowsOf loại dòng chỉ có _key/discriminator/stt/outputOnly',
    NestedGrid.businessRowsOf(spec, [
      { _row_id: 'x' },
      { loai_dong: 'ndd_pl' },
      { stt: '1', chu_ky: 'Y' },
      BIZ_ROW
    ]).length === 1);
}

console.log('--- 2. form-domain: validateDocument surface MIN_ROWS cho PLI_M02');
const M02_LOOP = 'ds_nddpl_uy_quyen_chu_so_huu';
function fakeM02Doc() {
  return { id: 'PLI_M02', ten_mau: 'o3-fixture', blocks: [
    { t: 'loop', loop: M02_LOOP, blankRows: 0, headerRows: [], cols: [
      { col: 1, tag: 'ten_nguoi_dai_dien' }], rows: [] }
  ] };
}
{
  // Section nested-grid của M02 KHÔNG khai activeWhen -> luôn active:
  // 0 dòng dữ liệu là blocking chặn export (chính sách blocking hiện có).
  const empty = FD.validateDocument('PLI_M02', fakeM02Doc().blocks,
    { values: {}, checks: {}, loops: {} }, {});
  check('M02 nested section rỗng -> validateDocument surface MIN_ROWS blocking',
    empty.some(e => e.code === 'MIN_ROWS' && e.severity === 'blocking' &&
      e.docId === 'PLI_M02' && e.key === M02_LOOP),
    JSON.stringify(empty.map(e => e.code)));

  const oneRow = FD.validateDocument('PLI_M02', fakeM02Doc().blocks,
    { values: {}, checks: {}, loops: {
      [M02_LOOP]: [{ _row_id: 'r1', loai_dong: 'ndd_pl',
        ten_nguoi_dai_dien: 'TRAN B' }] } }, {});
  check('M02 nested section 1 dòng business-data -> không MIN_ROWS',
    !oneRow.some(e => e.code === 'MIN_ROWS'), JSON.stringify(oneRow.map(e => e.code)));

  // (2 chiều - chiều chặn) blocking errors -> đường export chặn hồ sơ:
  // kiểm đúng tiền đề chính sách của app.js (lọc severity blocking).
  const blocking = empty.filter(e => e.severity === 'blocking');
  check('chiều chặn: MIN_ROWS nằm trong tập blocking chặn export',
    blocking.some(e => e.code === 'MIN_ROWS'));
}

console.log('--- 3. activeWhen trên section nested-grid (wiring evalActiveWhen)');
{
  const contract = FD.FORM_TABLE_CONTRACTS['PLI_M02'];
  const entry = contract.sections.find(s => s.sectionId === 'nddpl_uy_quyen_chu_so_huu');
  assert.ok(entry, 'M02 nddpl entry tồn tại');
  const backup = entry.activeWhen;
  try {
    // Selector checkedKey: section chỉ active khi tick ủy quyền.
    entry.activeWhen = { checkedKey: 'chk_o3_uy_quyen' };

    // (c-wiring) chưa tick + 0 dòng -> không block.
    const cW = FD.validateSectionEntry('PLI_M02', entry,
      { values: {}, checks: {}, loops: {} });
    check('(c) wiring: activeWhen chưa thỏa + 0 dòng -> không MIN_ROWS',
      !cW.some(e => e.code === 'MIN_ROWS'), JSON.stringify(cW.map(e => e.code)));

    // (d-wiring) chưa tick + dữ liệu cũ -> không block (validate).
    const dW = FD.validateSectionEntry('PLI_M02', entry,
      { values: {}, checks: {}, loops: {
        [M02_LOOP]: [{ _row_id: 'rOld', loai_dong: 'ndd_pl',
          ten_nguoi_dai_dien: 'CU' }] } });
    check('(d) wiring: inactive + dữ liệu cũ -> không MIN_ROWS',
      !dW.some(e => e.code === 'MIN_ROWS'), JSON.stringify(dW.map(e => e.code)));

    // Tick rồi nhưng chưa điền -> MIN_ROWS blocking.
    const aW = FD.validateSectionEntry('PLI_M02', entry,
      { values: {}, checks: { chk_o3_uy_quyen: true }, loops: {} });
    check('wiring: active (đã tick) + 0 dòng -> MIN_ROWS blocking',
      aW.some(e => e.code === 'MIN_ROWS' && e.severity === 'blocking'),
      JSON.stringify(aW.map(e => e.code)));

    // FD.isActiveSection dùng chung validate + export guard.
    check('isActiveSection: checkedKey false -> inactive; true -> active',
      FD.isActiveSection(entry, [], { values: {}, checks: {} }) === false &&
      FD.isActiveSection(entry, [], { values: {}, checks: {
        chk_o3_uy_quyen: true } }) === true);
  } finally {
    entry.activeWhen = backup; // restore registry - không rò rỉ fixture
  }
}

console.log('--- 4. Export guard hai chiều: inactive dữ liệu cũ KHÔNG lọt export');
{
  const contract = FD.FORM_TABLE_CONTRACTS['PLI_M02'];
  const entry = contract.sections.find(s => s.sectionId === 'nddpl_uy_quyen_chu_so_huu');
  const backup = entry.activeWhen;
  try {
    entry.activeWhen = { checkedKey: 'chk_o3_uy_quyen' };
    const oldData = [{ _row_id: 'rOld', loai_dong: 'ndd_pl',
      ten_nguoi_dai_dien: 'DU LIEU CU' }, { _row_id: 'rBlank' }];
    const store = { values: {}, checks: { chk_o3_uy_quyen: false },
      loops: { [M02_LOOP]: oldData } };

    // (d) chiều không-lọt: section inactive -> payload loop RỖNG.
    const payloadOff = H.GridCtl.exportLoops(store, ['PLI_M02']);
    check('(d) export: inactive + dữ liệu cũ -> payload loop rỗng (không lọt)',
      Array.isArray(payloadOff[M02_LOOP]) && payloadOff[M02_LOOP].length === 0,
      JSON.stringify(payloadOff[M02_LOOP]));

    // Active -> payload giữ dòng business, lọc blank row (hợp đồng cũ).
    store.checks.chk_o3_uy_quyen = true;
    const payloadOn = H.GridCtl.exportLoops(store, ['PLI_M02']);
    check('export: active -> giữ dòng business, blank row bị lọc',
      payloadOn[M02_LOOP].length === 1 &&
        payloadOn[M02_LOOP][0].ten_nguoi_dai_dien === 'DU LIEU CU',
      JSON.stringify(payloadOn[M02_LOOP]));

    // Không khai activeWhen (backup null) -> payload giữ nguyên (hành vi cũ).
    entry.activeWhen = backup;
    const payloadLegacy = H.GridCtl.exportLoops(store, ['PLI_M02']);
    check('export: không activeWhen -> payload giữ nguyên (back-compat)',
      payloadLegacy[M02_LOOP].length === 1,
      JSON.stringify(payloadLegacy[M02_LOOP]));
  } finally {
    entry.activeWhen = backup;
  }
}

console.log('--- 5. Contract thật: 3 spec nested-grid khai min_rows đúng D2.7=A');
{
  ['PLI_M02', 'PLI_M12', 'PLI_M15'].forEach(fid => {
    FD.sectionContractsOf(fid).filter(s => s.kind === 'nested-grid').forEach(s => {
      check(fid + '/' + s.spec.section_id + ': min_rows=1, max_rows=null',
        s.spec.min_rows === 1 && s.spec.max_rows === null,
        'min=' + s.spec.min_rows + ' max=' + s.spec.max_rows);
    });
  });
  // M12/M15 thật sự có section nested-grid (không phải fixture ảo).
  check('corpus có đủ 3 section nested-grid kiểm O3',
    ['PLI_M02', 'PLI_M12', 'PLI_M15'].every(fid =>
      FD.sectionContractsOf(fid).some(s => s.kind === 'nested-grid')));
}

console.log('----------------------------------------------------------------');
console.log('test_min_rows_o3: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
