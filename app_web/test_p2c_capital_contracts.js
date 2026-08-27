/* test_p2c_capital_contracts.js — Lane P2C (capital/assets: vốn + tài sản góp).
 *
 * Kiểm chứng phía runtime cho 3 section fixed-matrix mới của lane (spec JSON
 * tools/form_specs/{formation/PLI_M01,core/PLI_M02}.json), theo packet D1:
 *   D1.1=A — tổng/tỷ lệ computed outputOnly + đối chiếu vốn điều lệ blocking;
 *   D1.2=B CHO M01 — "Các tài sản khác" là ô mô tả text, KHÔNG sub-grid.
 *
 * Mệnh đề:
 *  1. [SPEC]  spec JSON của lane qua được validator v1 (shape fixed-matrix:
 *             1 cột nhãn tag=null ở index 0, đúng 1 dòng tổng output_only).
 *  2. [WIRE]  module thuần app_web/ui/fixed-matrix.js chạy được với spec của
 *             lane sau khi map đúng shape runtime (input_type -> inputType,
 *             totals[].target_row -> totals[].id) — đây chính là adapter mà
 *             Lead phải cắm khi đăng ký FORM_TABLE_CONTRACTS.
 *  3. [D1.1A] recompute/validate của engine: tổng tự tính từ ô dữ liệu, dòng
 *             không kê khai không bị tính thành 0, ôMoney/% sai bị chặn,
 *             draft KHÔNG BAO GIỜ bị ghi số tổng (projection).
 *  4. [PARITY] kết quả JS == kết quả Python (tools/test_p2c_capital_specs.py
 *             [EXPORT]) cho cùng draft — hai engine không được lệch nhau.
 *  5. [GATE]  registry runtime CHƯA có contract cho 3 section này ( Lead phải
 *             wire ), còn F2/F3 (M03/M04) dùng ĐÚNG bộ row id/tag canonical
 *             mà lane đã khai -> không lệch key giữa generator và UI/export.
 *  6. [GAP]   cross_field đối chiếu vốn điều lệ (CAPITAL_MISMATCH, D1.1=A):
 *             cơ chế có sẵn ở F2/F3 nhưng CHƯA wire cho M01/M02 -> gap ghi rõ.
 *
 * Chạy: node app_web/test_p2c_capital_contracts.js   (từ root repo, không GUI)
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const Matrix = require('./ui/fixed-matrix.js');
const FD = require('./ui/form-domain.js');

const RESULTS = [];
let passed = 0;
let failed = 0;

function check(name, pass, expect, actual) {
  const ok = !!pass;
  RESULTS.push({ name, pass: ok });
  if (ok) passed++;
  else failed++;
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name +
    (ok ? '' : '\n        EXPECT : ' + (expect || '') +
      '\n        ACTUAL : ' + (actual === undefined ? '(none)' : String(actual))));
}

function loadJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}

// ---------------------------------------------------------------------------
// Nguồn: spec JSON của lane + census manifest
// ---------------------------------------------------------------------------
const MANIFEST = loadJson('app/data/table_specs/manifest.json');
const FORMS = {};
MANIFEST.forms.forEach(f => {
  FORMS[f.form_id] = {};
  (f.sections || []).forEach(s => { FORMS[f.form_id][s.section_id] = s; });
});

const SPECS = [
  { docId: 'PLI_M01', sectionId: 'tai_san_gop_von_von_dau_tu',
    file: 'tools/form_specs/formation/PLI_M01.json',
    sem: 'co_cau_tai_san_gop_von_dau_tu',
    detailTag: 'chi_tiet_ngoai_te_tai_san_khac',
    totalRow: 'tong_so',
    rows: ['dong_viet_nam', 'ngoai_te_tu_do_chuyen_doi', 'vang',
      'quyen_su_dung_dat', 'quyen_so_huu_tri_tue', 'tai_san_khac', 'tong_so'],
    firstLabel: 'Đồng Việt Nam', totalLabel: 'Tổng số' },
  { docId: 'PLI_M02', sectionId: 'nguon_von_dieule',
    file: 'tools/form_specs/core/PLI_M02.json',
    sem: 'nguon_von_dieu_le',
    detailTag: null,
    totalRow: 'tong_cong',
    rows: ['von_ngan_sach_nha_nuoc', 'von_tu_nhan', 'von_nuoc_ngoai',
      'von_khac', 'tong_cong'],
    firstLabel: 'Vốn ngân sách nhà nước', totalLabel: 'Tổng cộng' },
  { docId: 'PLI_M02', sectionId: 'tai_san_gop_von_von_dieu_le',
    file: 'tools/form_specs/core/PLI_M02.json',
    sem: 'co_cau_tai_san_gop_von_dieu_le',
    detailTag: 'chi_tiet_ngoai_te_tai_san_khac',
    totalRow: 'tong_so',
    rows: ['dong_viet_nam', 'ngoai_te_tu_do_chuyen_doi', 'vang',
      'quyen_su_dung_dat', 'quyen_so_huu_tri_tue', 'tai_san_khac', 'tong_so'],
    firstLabel: 'Đồng Việt Nam', totalLabel: 'Tổng số' },
];

function entriesOf(rel) {
  return loadJson(rel).tables || [];
}

function findEntry(rel, sectionId) {
  const hits = entriesOf(rel).filter(e =>
    ((e.spec.section_id) || e.spec.id) === sectionId);
  return hits.length === 1 ? hits[0] : null;
}

/* Adapter shape generator -> runtime (đúng việc Lead phải cắm lúc wire;
 * KHÔNG thêm/bớt field nào khác của contract v1). */
function toRuntimeSpec(entry) {
  const s = entry.spec;
  return {
    form_id: entry.spec.id,
    kind: 'fixed-matrix',
    section_id: s.section_id,
    semantic_key: s.semantic_key,
    fixed_rows: (s.fixed_rows || []).map(r => ({
      id: r.id, label: r.label, output_only: r.output_only === true })),
    columns: (s.columns || []).map(c => ({
      tag: c.tag,
      inputType: c.input_type,
      header: c.header,
      computed: c.computed === true,
      output_only: c.output_only === true,
      required: c.required === true })),
    totals: (s.totals || []).map(t => ({
      id: t.target_row, formula: t.formula, target_tag: t.target_tag })),
  };
}

function draftOf(pairs) {
  const draft = { values: {} };
  Object.keys(pairs || {}).forEach(k => { draft.values[k] = pairs[k]; });
  return draft;
}

// ===========================================================================
// 1. [SPEC] shape fixed-matrix v1 của 3 entry
// ===========================================================================
SPECS.forEach(want => {
  const entry = findEntry(want.file, want.sectionId);
  check(want.docId + '/' + want.sectionId + ': spec JSON co dung 1 entry',
    !!entry && entry.spec.kind === 'fixed-matrix', 'kind=fixed-matrix',
    entry && entry.spec.kind);
  if (!entry) return;
  const s = entry.spec;

  check(want.docId + '/' + want.sectionId + ': semantic_key khop manifest',
    FORMS[want.docId][want.sectionId].semantic_key === s.semantic_key &&
      s.semantic_key === want.sem,
    want.sem, s.semantic_key);

  check(want.docId + '/' + want.sectionId + ': khong bi block legal review',
    entry.legal_status && entry.legal_status.blocked === false,
    'legal_status.blocked=false',
    entry.legal_status && entry.legal_status.blocked);

  check(want.docId + '/' + want.sectionId + ': 1 cot nhan tag=null o index 0',
    s.columns[0].tag === null && s.columns[0].input_type === 'readonly',
    'columns[0].tag=null,readonly', JSON.stringify(s.columns[0]));

  const tags = s.columns.filter(c => c.tag).map(c => c.tag);
  check(want.docId + '/' + want.sectionId + ': du cot du lieu theo manifest',
    tags.join(',') === want.detailTag
      ? ['chi_tiet_ngoai_te_tai_san_khac', 'gia_tri_vnd', 'ty_le'].join(',')
      : ['so_tien_vnd_va_tuong_duong', 'ty_le'].join(','),
    'tags canonical', tags.join(','));

  check(want.docId + '/' + want.sectionId + ': du dong phap ly + dong tong cuoi',
    JSON.stringify(s.fixed_rows.map(r => r.id)) === JSON.stringify(want.rows) &&
      s.fixed_rows[s.fixed_rows.length - 1].output_only === true,
    want.rows.join(','), s.fixed_rows.map(r => r.id).join(','));

  check(want.docId + '/' + want.sectionId + ': tong = sum() tren moi cot so (D1.1=A)',
    s.totals.length === (want.detailTag ? 2 : 2) &&
      s.totals.every(t => /^sum\([a-z0-9_]+\)$/.test(t.formula) &&
        t.target_row === want.totalRow),
    'sum(gia_tri_vnd)/sum(ty_le) -> ' + want.totalRow,
    JSON.stringify(s.totals));

  // D1.2: "Các tài sản khác" là ô mô tả text — KHÔNG sub-grid/loop con
  check(want.docId + '/' + want.sectionId + ': khong sub-grid cho "Tài sản khác"',
    !s.loop && !(entry.spec.columns || []).some(c => c.tag === 'ds_tai_san_khac'),
    'không có loop/sub-grid', String(s.loop || 'none'));

  // D1.2=B cho M01 (+ mô tả text cho tài sản M02 theo chính mẫu)
  if (want.detailTag) {
    const detail = s.columns.filter(c => c.tag === want.detailTag)[0];
    check(want.docId + '/' + want.sectionId +
        ': "Tài sản khác" la o mo ta text do nguoi dung nhap',
      !!detail && detail.input_type === 'text' && !detail.computed &&
        !detail.output_only,
      'input_type=text', JSON.stringify(detail));
  } else {
    check(want.docId + '/' + want.sectionId +
        ': "Vốn khác" KHONG bi tu che cot mo ta (mau khong co o mo ta)',
      !tags.some(t => t.indexOf('chi_tiet') >= 0),
      'không có cột chi_tiet', tags.join(','));
  }
});

// ===========================================================================
// 2-3-4. [WIRE] [D1.1A] [PARITY] engine 2 phía cùng ngữ nghĩa
// ===========================================================================
const PARITY = {
  // draft: Đồng Việt Nam 1.000.000 (60%) + tài sản khác 500.000 (40%)
  // Python [EXPORT] chốt: tổng giá trị 1500000, tổng tỷ lệ 100
  'PLI_M01/tai_san_gop_von_von_dau_tu': { giaTri: '1500000', tyLe: '100' },
  // draft: Vốn tư nhân 2.000.000.000 (100%)
  'PLI_M02/nguon_von_dieule': { soTien: '2000000000', tyLe: '100' },
  // draft: Đồng Việt Nam 1.000.000 (60%) + tài sản khác 500.000 (40%)
  'PLI_M02/tai_san_gop_von_von_dieu_le': { giaTri: '1500000', tyLe: '100' },
};

SPECS.forEach(want => {
  const entry = findEntry(want.file, want.sectionId);
  if (!entry) return;
  const spec = toRuntimeSpec(entry);
  const sem = spec.semantic_key;

  check(want.docId + '/' + want.sectionId + ': fixedRows doc du nhan dong',
    JSON.stringify(Matrix.fixedRows(spec).map(r => r.label)) ===
      JSON.stringify(entry.spec.fixed_rows.map(r => r.label)) &&
      Matrix.fixedRows(spec)[0].label === want.firstLabel &&
      Matrix.fixedRows(spec)[Matrix.fixedRows(spec).length - 1].label ===
        want.totalLabel,
    want.firstLabel + ' … ' + want.totalLabel,
    Matrix.fixedRows(spec).map(r => r.label).join('|'));

  // dòng pháp lý KHÔNG thể xóa/thêm (fixed-matrix: không có row-op)
  const legalRow = want.rows[0];
  check(want.docId + '/' + want.sectionId + ': khong xoa duoc dong phap ly',
    Matrix.canDelete(spec, legalRow) === false &&
      Matrix.deleteRow(draftOf(), spec, legalRow) === false,
    'canDelete=false, deleteRow=0/false',
    String(Matrix.canDelete(spec, legalRow)) + '/' +
      String(Matrix.deleteRow(draftOf(), spec, legalRow)));

  // D1.1=A: tổng tự tính, dòng trống không thành 0, draft không bị ghi
  const filled = {};
  if (want.sectionId === 'nguon_von_dieule') {
    filled[sem + '.von_tu_nhan.so_tien_vnd_va_tuong_duong'] = '2.000.000.000';
    filled[sem + '.von_tu_nhan.ty_le'] = '100';
  } else {
    filled[sem + '.dong_viet_nam.gia_tri_vnd'] = '1.000.000';
    filled[sem + '.dong_viet_nam.ty_le'] = '60';
    filled[sem + '.tai_san_khac.' + want.detailTag] =
      'Xe hơi phục vụ lãnh đạo, giá trị còn lại 500 triệu';
    filled[sem + '.tai_san_khac.gia_tri_vnd'] = '500000';
    filled[sem + '.tai_san_khac.ty_le'] = '40';
  }
  const draft = draftOf(filled);
  const matrix = Matrix.recompute(spec, draft);
  const totalRow = matrix.rows.filter(r => r.id === want.totalRow)[0];
  const valueTag = want.sectionId === 'nguon_von_dieule'
    ? 'so_tien_vnd_va_tuong_duong' : 'gia_tri_vnd';
  const parity = PARITY[want.docId + '/' + want.sectionId];
  const gotValue = String(totalRow.cells[valueTag]);
  const gotPercent = String(totalRow.cells.ty_le);

  check(want.docId + '/' + want.sectionId + ': tong gia tri = ' + parity.giaTri,
    gotValue === (parity.soTien || parity.giaTri),
    parity.soTien || parity.giaTri, gotValue);
  check(want.docId + '/' + want.sectionId + ': tong ty le = ' + parity.tyLe,
    gotPercent === parity.tyLe, parity.tyLe, gotPercent);
  check(want.docId + '/' + want.sectionId + ': draft khong bi ghi so tong',
    Object.keys(draft.values).every(k =>
      k.indexOf('.' + want.totalRow + '.') < 0),
    'values không chứa <sem>.<tong>.<tag>',
    Object.keys(draft.values).filter(k =>
      k.indexOf('.' + want.totalRow + '.') >= 0).join(','));

  // ô mô tả (D1.2=B) đi thẳng vào ô text của dòng "Tài sản khác"
  if (want.detailTag) {
    const other = matrix.rows.filter(r => r.id === 'tai_san_khac')[0];
    check(want.docId + '/' + want.sectionId +
        ': mo ta "Tài sản khác" nam o cot chi tiet',
      String(other.cells[want.detailTag]).indexOf('Xe hơi') === 0,
      'Xe hơi phục vụ lãnh đạo…', String(other.cells[want.detailTag]));
  }

  // validator của engine: money/% sai phải bị chặn, % > 100 bị chặn
  const bad = draftOf(filled);
  bad.values[sem + '.' + legalRow + '.' + valueTag] = 'khong phai so';
  const errs = Matrix.validate(spec, bad);
  check(want.docId + '/' + want.sectionId + ': MONEY bi chan khi sai so',
    errs.some(e => e.code === 'MONEY' && e.key.indexOf(legalRow) >= 0),
    'code=MONEY', JSON.stringify(errs.map(e => e.code)));
  const badPct = draftOf(filled);
  badPct.values[sem + '.' + legalRow + '.ty_le'] = '150';
  const errsPct = Matrix.validate(spec, badPct);
  check(want.docId + '/' + want.sectionId + ': PERCENT >100 bi chan',
    errsPct.some(e => e.code === 'PERCENT'),
    'code=PERCENT', JSON.stringify(errsPct.map(e => e.code)));
  check(want.docId + '/' + want.sectionId + ': du lieu hop le khong co loi',
    Matrix.validate(spec, draftOf(filled)).length === 0,
    '0 error', JSON.stringify(Matrix.validate(spec, draftOf(filled))));
});

// ===========================================================================
// 5. [GATE] registry runtime chưa wire 3 section (Lead phải đăng ký)
// ===========================================================================
SPECS.forEach(want => {
  const bySection = FD.getSectionContract(want.docId, want.sectionId);
  const bySem = FD.getSectionContract(want.docId, want.sem);
  check('GATE ' + want.docId + '/' + want.sectionId +
      ': CHUA co contract runtime (gap can Lead wire)',
    bySection === null && bySem === null, 'null (chưa đăng ký)',
    String(!!bySection || !!bySem));
});

// F2 (M03) cùng section nguon_von_dieule phải dùng đúng bộ key canonical
const f2 = FD.getSectionContract('PLI_M03', 'nguon_von_dieule');
const m02 = findEntry('tools/form_specs/core/PLI_M02.json', 'nguon_von_dieule');
const inputTagsOf = spec => (spec.columns || [])
  .filter(c => c.tag && c.inputType !== 'readonly' && c.input_type !== 'readonly')
  .map(c => c.tag);
check('CANON nguon_von_dieule: F2(M03) cung row id + tag cot nhap voi spec PLI_M02',
  !!f2 && !!m02 &&
    JSON.stringify(f2.spec.fixed_rows.map(r => r.id)) ===
      JSON.stringify(m02.spec.fixed_rows.map(r => r.id)) &&
    JSON.stringify(inputTagsOf(f2.spec)) ===
      JSON.stringify(inputTagsOf(m02.spec)),
  'von_ngan_sach_nha_nuoc…tong_cong | so_tien_vnd_va_tuong_duong,ty_le',
  f2 && m02 ? JSON.stringify(f2.spec.fixed_rows.map(r => r.id)) + ' / ' +
       JSON.stringify(inputTagsOf(f2.spec)) + ' vs ' +
       JSON.stringify(inputTagsOf(m02.spec)) : 'thiếu F2 hoặc spec');

// LECH SHAPE DA GHI NHAN (gap cho Lead/B2): cột nhãn của F2 mang tag
// 'loai_nguon_von' (shape runtime), còn spec generator v1 BẮT BUỘC tag=null ở
// cột nhãn (validator: "tối đa 1 cột tag=null, phải ở chỉ số 0") — nếu gắn tag
// thì generator in token thay vì NHÃN PHÁP LÝ, mất dòng "Vốn ngân sách nhà
// nước"… Muốn thống nhất 100% key thì phải mở rộng contract v1 (readonly có
// tag) — không làm trong lane này.
check('GAP cot nhan: F2 dat tag, generator v1 bat buoc tag=null (can Lead chot)',
  !!f2 && !!m02 &&
    f2.spec.columns[0].tag === 'loai_nguon_von' &&
    m02.spec.columns[0].tag === null,
  'F2 tag=loai_nguon_von vs spec tag=null',
  JSON.stringify([f2 && f2.spec.columns[0].tag, m02 && m02.spec.columns[0].tag]));

// ===========================================================================
// 6. [GAP] cross_field đối chiếu vốn điều lệ (D1.1=A) chưa wire cho M01/M02
// ===========================================================================
const f2Rules = (f2 && f2.spec.cross_field_rules) || [];
check('GAP M01/M02: chua co rule CAPITAL_MISMATCH dang ky trong runtime',
  SPECS.every(w => FD.getSectionContract(w.docId, w.sectionId) === null) &&
    f2Rules.some(r => r.type === 'sumEqualsKey' && r.severity === 'blocking' &&
      r.valueKey === 'von_dieu_le' && r.code === 'CAPITAL_MISMATCH'),
  'F2(M03) có sample sumEqualsKey/valueKey=von_dieu_le; M01/M02 chưa có',
  JSON.stringify(f2Rules.map(r => [r.type, r.valueKey, r.code])));

// Mismatch thật của PLI_M01 không sinh CAPITAL_MISMATCH nào hôm nay
const mismatch = {
  'von_dau_tu_so': '9000000',
  'co_cau_tai_san_gop_von_dau_tu.dong_viet_nam.gia_tri_vnd': '8000000',
};
const errs01 = FD.validateFormSections('PLI_M01', { values: mismatch });
check('GAP PLI_M01: lệch vốn đầu tư chua bi chan (khong co contract)',
  errs01.length === 0, '0 error (chưa wire)',
  JSON.stringify(errs01.map(e => e.code)));

// ---------------------------------------------------------------------------
console.log('-'.repeat(72));
RESULTS.forEach(r => { if (!r.pass) console.log('  -> ' + r.name); });
console.log('test_p2c_capital_contracts: %d PASS / %d FAIL', passed, failed);
process.exit(failed ? 1 : 0);
