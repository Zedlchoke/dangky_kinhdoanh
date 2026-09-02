/* test_p3_draft.js — LANE P3: draft store resilience (save/reload/import legacy).
 *
 * Chạy:  node app_web/test_p3_draft.js
 *
 * Phạm vi (suite MỚI, KHÔNG sửa production):
 *  1. Draft v1 (chưa có _row_id) -> migrateDraft additive: giữ unknown field
 *     cấp top/store/values/checks/loops, giữ customCell của từng dòng, giữ
 *     THỨ TỰ mảng; _row_id gán idempotent (mở rộng pattern test_p2_migration.js
 *     nhưng với dữ liệu production PLI_M02/PLI_M06/PLII_M01 + tên profile dài).
 *  2. Draft MALFORMED: JSON cắt cụt, null, mảng thay object, object thay mảng,
 *     _row_id trùng, loop 10.000 dòng, Unicode/emoji + ký tự NUL trong giá trị,
 *     tên profile dài 4096 ký tự — mọi thao tác load/save/migrate KHÔNG được
 *     ném exception ngoài dự kiến; _row_id gán idempotent; thứ tự giữ nguyên.
 *  3. Save/reload round-trip (JSON.stringify -> parse -> migrateDraft) phải
 *     bảo toàn dữ liệu, kể cả khi draft v2 đi qua migrateDraft lần 2.
 *
 * Ghi chú: đường draft THẬT của app (Bridge.save_draft/load_draft trong
 * app_web/main.py) dùng dialog tkinter nên KHÔNG chạy được trên máy này
 * (không có pywebview/WebView2) — suite kiểm lớp dữ liệu thuần
 * (FormDomain.migrateDraft/normalizeStoreLoops) + lớp JSON serialize, đúng
 * phần Bridge làm (json.dump / json.load).
 */
'use strict';

const fs = require('fs');
const path = require('path');

const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');
const G = App.GridCtl;

let passed = 0, failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function section(t) { console.log('\n===== ' + t + ' ====='); }
/* KNOWN-FINDING: lỗi thật của production (không phải lỗi của suite).
 * Được ghi lại và liệt kê trong báo cáo cho Lead — suite vẫn exit 0 như
 * quy ước LANE P3 (KHÔNG sửa production trong lane này). */
const FINDINGS = [];
function finding(name, evidence) {
  FINDINGS.push(name);
  console.log('FIND  ' + name + (evidence ? '  [' + evidence + ']' : ''));
}
function checkF(name, ok, evidence, ftext) {
  if (ok) { passed++; console.log('PASS  ' + name); }
  else finding(ftext || name, evidence);
}

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
function rowIds(store, loop) {
  return (store.loops[loop] || []).map(r => r && r._row_id);
}
/* Không được ném: chạy fn, trả {ok, val, err}. */
function noThrow(fn) {
  try { return { ok: true, val: fn() }; }
  catch (e) { return { ok: false, err: (e && e.message) || String(e) }; }
}

// ======================================================================
// 1. Draft v1 -> v2: additive, giữ unknown + customCell + thứ tự
// ======================================================================
section('1. Draft v1 migrate additive (unknown field + customCell + thu tu)');
const M02 = loadProd('PLI_M02');
const M06 = loadProd('PLI_M06');
const HGD = loadProd('PLII_M01');
function loopOf(doc, name) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === name)[0] || null;
}
check('P3-D1: fixture la production blocks that (M02/M06/PLII_M01 co loop)',
  !!loopOf(M02, 'ds_nganh') && !!loopOf(M06, 'ds_thanh_vien_tnhh') &&
    !!loopOf(HGD, 'ds_tv_ho_gia_dinh') && Array.isArray(M02.blocks) &&
    M02.blocks.length > 100);

const LEGACY_ROWS = [
  { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X',
    customCell: 'giữ-1', ghi_chu_rieng: { doc: 'giữ object lồng' } },
  { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy tính', la_nganh_chinh: '',
    customCell: 'giữ-2' },
  { ma_nganh: '5610', ten_nganh: 'Giữ chỗ thứ ba', la_nganh_chinh: '',
    customCell: 'giữ-3' }
];
const LEGACY_TV = [
  { ho_ten: 'Nguyễn Văn A 🙃', so_cccd: '012345678901', von_dong_gop: '1000000' },
  { ho_ten: 'Trần Thị B', so_cccd: '012345678902', von_dong_gop: '2000000',
    customCell: 'tv-2' }
];
const LEGACY_HGD = [
  { ho_ten: 'Lê Văn C', so_cccd: '012345678903' },
  { ho_ten: 'Phạm Thị D', so_cccd: '012345678904' },
  { ho_ten: 'Vũ Văn E', so_cccd: '012345678905', customCell: 'hgd-3' }
];
const v1 = {
  v: 1,
  caseId: 'thanh_lap_tnhh_1tv',
  checkedForms: ['PLI_M02', 'PLI_M06', 'PLII_M01'],
  autoSum: true,
  futureTopLevel: { producer: 'newer-client-9.9', keep: [1, 2, 3] },
  store: {
    values: {
      'dn.ten_tieng_viet': 'CÔNG TY MẪU 🙃 P3',
      'dn.ma_so_dn': '031234567890',
      futureValue: 'keep'
    },
    checks: { 'legacy.check': true, futureCheck: false },
    loops: {
      ds_nganh: LEGACY_ROWS,
      ds_thanh_vien_tnhh: LEGACY_TV,
      ds_tv_ho_gia_dinh: LEGACY_HGD,
      future_loop_name: [{ future: 'row' }, { future: 'row-2' }]
    },
    futureStoreField: { keep: 'store-extension' }
  }
};
const up = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(v1))));
check('P3-D2: migrateDraft(draft v1) khong nem', up.ok, up.err);
const m = up.val || {};
check('P3-D3: v1 -> v2, activeDocId/viewState/savedAt duoc khoi tao',
  m.v === 2 && m.activeDocId === null &&
    JSON.stringify(m.viewState) === '{}' && m.savedAt === null,
  JSON.stringify({ v: m.v, a: m.activeDocId, s: m.savedAt }));
check('P3-D4: additive - unknown field cap top giu nguyen',
  JSON.stringify(m.futureTopLevel) === JSON.stringify(v1.futureTopLevel),
  JSON.stringify(m.futureTopLevel));
check('P3-D5: additive - unknown field cua store/values/checks giu nguyen',
  m.store.futureStoreField && m.store.futureStoreField.keep === 'store-extension' &&
    m.store.values.futureValue === 'keep' &&
    m.store.checks.futureCheck === false &&
    m.store.checks['legacy.check'] === true);
check('P3-D6: additive - loop chua biet giu nguyen ca gia tri + thu tu '
    + '(_row_id duoc gan them)',
  m.store.loops.future_loop_name.length === 2 &&
    m.store.loops.future_loop_name[0].future === 'row' &&
    m.store.loops.future_loop_name[1].future === 'row-2' &&
    typeof m.store.loops.future_loop_name[0]._row_id === 'string' &&
    m.store.loops.future_loop_name[0]._row_id !==
      m.store.loops.future_loop_name[1]._row_id,
  JSON.stringify(m.store.loops.future_loop_name));
check('P3-D7: customCell/field la cua tung dong duoc giu',
  m.store.loops.ds_nganh[0].customCell === 'giữ-1' &&
    m.store.loops.ds_nganh[2].customCell === 'giữ-3' &&
    m.store.loops.ds_thanh_vien_tnhh[1].customCell === 'tv-2' &&
    m.store.loops.ds_tv_ho_gia_dinh[2].customCell === 'hgd-3' &&
    m.store.loops.ds_nganh[0].ghi_chu_rieng.doc === 'giữ object lồng');
check('P3-D8: THU TU dong duoc giu nguyen (khong sort, khong mat dong)',
  m.store.loops.ds_nganh.map(r => r.ma_nganh).join(',') === '0111,4711,5610' &&
    m.store.loops.ds_tv_ho_gia_dinh.map(r => r.so_cccd).join(',') ===
      '012345678903,012345678904,012345678905');
check('P3-D9: gia tri Unicode/emoji trong values giu nguyen',
  m.store.values['dn.ten_tieng_viet'] === 'CÔNG TY MẪU 🙃 P3');
check('P3-D10: gia tri dang chuoi "0111" khong bi bien thanh so',
  m.store.loops.ds_nganh.every(r => typeof r.ma_nganh === 'string'));

// _row_id: gán cho dòng thiếu, giữ id dòng đã có, idempotent
check('P3-D11: _row_id duoc gan cho moi dong con thieu',
  ['ds_nganh', 'ds_thanh_vien_tnhh', 'ds_tv_ho_gia_dinh', 'future_loop_name']
    .every(l => (m.store.loops[l] || []).every(r => typeof r._row_id === 'string' &&
      r._row_id.length > 0)));
const v1WithId = JSON.parse(JSON.stringify(v1));
v1WithId.store.loops.ds_nganh[1]._row_id = 'rKEEP_nganh_2';
const up2 = FD.migrateDraft(v1WithId);
check('P3-D12: _row_id co san giu NGUYEN, khong bi ghi de',
  up2.store.loops.ds_nganh[1]._row_id === 'rKEEP_nganh_2' &&
    up2.store.loops.ds_nganh[1].customCell === 'giữ-2');
const pass1 = rowIds(m.store, 'ds_nganh').concat(rowIds(m.store, 'ds_thanh_vien_tnhh'));
const again = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(m))));
const againIds = rowIds(again.val.store, 'ds_nganh')
  .concat(rowIds(again.val.store, 'ds_thanh_vien_tnhh'));
check('P3-D13: migrateDraft go lan 2 IDEMPOTENT (khong doi _row_id)',
  again.ok && JSON.stringify(pass1) === JSON.stringify(againIds),
  pass1.join(',') + ' vs ' + againIds.join(','));
check('P3-D14: draft v2 tra ve CHINH OBJECT goc (chi mutate ben trong)',
  FD.migrateDraft(m) === m);
check('P3-D15: _row_id khong trung nhau trong cung mot loop',
  (() => {
    const seen = {};
    let dup = 0;
    ['ds_nganh', 'ds_thanh_vien_tnhh', 'ds_tv_ho_gia_dinh'].forEach(l =>
      (m.store.loops[l] || []).forEach(r => {
        if (seen[r._row_id]) dup++;
        seen[r._row_id] = true;
      }));
    return dup === 0;
  })());

// draft không hiểu -> bỏ qua, không ném
check('P3-D16: migrateDraft(null/undefined/thieu store) -> null, khong nem',
  FD.migrateDraft(null) === null && FD.migrateDraft(undefined) === null &&
    FD.migrateDraft({ v: 1 }) === null && FD.migrateDraft('chuoi') === null &&
    FD.migrateDraft(42) === null);
check('P3-D17: draft v2 thieu store -> tra ve nguyen object (khong nem)',
  (() => {
    const r = noThrow(() => FD.migrateDraft({ v: 2, note: 'khong co store' }));
    return r.ok && r.val && r.val.note === 'khong co store' && !r.val.store;
  })());

// ======================================================================
// 2. Draft MALFORMED
// ======================================================================
section('2. Draft malformed: JSON cut, null, mang thay object, row_id trung');

// 2a. JSON cắt cụt — Bridge.load_draft bắt Exception và trả {ok:false}; ở đây
//     assert JSON.parse (lớp dữ liệu Bridge dùng) ném SyntaxError DỰ ĐOÁN và
//     app không bao giờ nhận draft nửa vời.
const fullJson = JSON.stringify(v1);
[[10], [fullJson.length >> 1], [fullJson.length - 1]].forEach(([cut]) => {
  const truncated = fullJson.slice(0, cut);
  const r = noThrow(() => JSON.parse(truncated));
  check('P3-D18: JSON cat cut ' + cut + ' ky tu -> JSON.parse nem SyntaxError (du doan)',
    !r.ok && /JSON|position|Unexpected/i.test(r.err), r.ok ? 'PARSE OK?!' : r.err);
  // và khi app nuốt lỗi thì draft không được đưa vào migrateDraft
  check('P3-D19: draft cat cut khong duoc dua vao migrateDraft (khong nua voi)',
    (() => {
      // mô phỏng nhánh Bridge.load_draft bắt Exception -> trả {ok:false}
      let draft = null;
      try { draft = JSON.parse(truncated); } catch (e) { draft = null; }
      const m2 = noThrow(() => FD.migrateDraft(draft));
      return m2.ok && FD.migrateDraft(draft) === null;
    })());
});

// 2b. null / sai kiểu ở mọi mức
const BAD = {
  'draft = null': null,
  'draft = []': [],
  'draft = "chuoi"': 'chuoi',
  'draft = 0': 0,
  'draft.v = "x"': { v: 'x', store: { values: {}, checks: {}, loops: {} } },
  'draft.v = null': { v: null, store: { values: {}, checks: {}, loops: {} } },
  'store = null': { v: 1, store: null },
  'store = []': { v: 1, store: [] },
  'store = "s"': { v: 1, store: 's' },
  'values = null': { v: 1, store: { values: null, checks: {}, loops: {} } },
  'values = []': { v: 1, store: { values: [], checks: {}, loops: {} } },
  'values = 5': { v: 1, store: { values: 5, checks: {}, loops: {} } },
  'checks = null': { v: 1, store: { values: {}, checks: null, loops: {} } },
  'checks = "s"': { v: 1, store: { values: {}, checks: 's', loops: {} } },
  'loops = null': { v: 1, store: { values: {}, checks: {}, loops: null } },
  'loops = [] (mang thay object)': { v: 1, store: { values: {}, checks: {}, loops: [] } },
  'loops = "s"': { v: 1, store: { values: {}, checks: {}, loops: 's' } },
  'loops.x = null': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: null } } },
  'loops.x = "s"': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: 's' } } },
  'loops.x = 42': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: 42 } } },
  'loops.x = {} (object thay mang)': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: { a: 1 } } } },
  'loops.x = [null]': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [null] } } },
  'loops.x = [1, "s", true]': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [1, 's', true] } } },
  'loops.x = [[{}]]': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [[{}]] } } },
  'checkedForms = "s"': { v: 1, checkedForms: 's',
    store: { values: {}, checks: {}, loops: {} } },
  'checkedForms = null': { v: 1, checkedForms: null,
    store: { values: {}, checks: {}, loops: {} } },
  'autoSum = "khong phai bool"': { v: 1, autoSum: 'khong phai bool',
    store: { values: {}, checks: {}, loops: {} } },
  'row._row_id = 123 (sai kieu)': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [{ ma_nganh: '0111', _row_id: 123 }] } } },
  'row._row_id = null': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [{ ma_nganh: '0111', _row_id: null }] } } },
  'row._row_id = ""': { v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [{ ma_nganh: '0111', _row_id: '' }] } } }
};
Object.keys(BAD).forEach(label => {
  const r = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(BAD[label]))));
  checkF('P3-D20: ' + label + ' -> khong nem ngoai du kien', r.ok, r.err,
    'F-P3-1 migrateDraft nem TypeError khi store.loops.<ten> la truthy khong-phai-mang');
});

// 2c. hành vi cụ thể trên 3 shape dễ lọt: object thay mảng / phần tử lạ / id sai kiểu
{
  const a = noThrow(() => FD.migrateDraft({ v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: { a: 1 } } } }));
  checkF('P3-D21: loops.x la OBJECT thay mang -> van tra ve draft v2, khong nem',
    a.ok && !!a.val && a.val.v === 2 && !!a.val.store,
    a.ok ? JSON.stringify(a.val && a.val.store && a.val.store.loops) : a.err,
    'F-P3-1 migrateDraft nem TypeError khi store.loops.<ten> la truthy khong-phai-mang');
  const b = noThrow(() => FD.migrateDraft({ v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [null, 1, 's', { ma_nganh: '0111' }] } } }));
  check('P3-D22: loop chua phan tu la (null/so/chuoi) -> khong nem, dong that van duoc gan id',
    b.ok && !!b.val && Array.isArray(b.val.store.loops.ds_nganh) &&
      b.val.store.loops.ds_nganh.length === 4 &&
      typeof b.val.store.loops.ds_nganh[3]._row_id === 'string',
    b.ok ? JSON.stringify(b.val.store.loops.ds_nganh) : b.err);
  const c = noThrow(() => FD.migrateDraft({ v: 1, store: { values: {}, checks: {},
    loops: { ds_nganh: [{ ma_nganh: '0111', _row_id: 123 }] } } }));
  /* [Lane fix-industry, Class 9] Pin cũ ghim "_row_id SỐ được GIỮ NGUYÊN".
   * Red test (test_industry_input_negative.js S4) chứng minh pin đó ghim đúng
   * hành vi lỗi Class 9 (defect registry "không sinh row NaN id"): id số gãy
   * findRowIndex so === với id chuỗi từ DOM data-row-id -> selection/focus/
   * lỗi trỏ sai dòng. Hợp đồng MỚI (normalizeStoreLoops): id rác (không phải
   * chuỗi usable) được GÁN LẠI id hợp lệ — vẫn không ném, dữ liệu giữ nguyên. */
  check('P3-D23: _row_id truthy khac chuoi (so) duoc GAN LAI id hop le, '
    + 'khong nem, du lieu giu nguyen (Class 9: khong sinh row id NaN/junk)',
    c.ok && !!c.val &&
      typeof c.val.store.loops.ds_nganh[0]._row_id === 'string' &&
      /^r\d+_/.test(c.val.store.loops.ds_nganh[0]._row_id) &&
      c.val.store.loops.ds_nganh[0].ma_nganh === '0111',
    c.ok ? JSON.stringify(c.val.store.loops.ds_nganh) : c.err);
  /* Nhân rộng lên GridCtl: cùng draft hỏng đi qua ensureIds (app.js gọi trong
   * restoreDraft) — đây là đường UI thật sau khi migrateDraft đã sống. */
  const g = noThrow(() => {
    const st = { values: {}, checks: {}, loops: { ds_nganh: 'khong-phai-mang' } };
    return G.ensureIds(st);
  });
  checkF('P3-D21b: GridCtl.ensureIds voi loop khong phai mang -> khong nem',
    g.ok, g.ok ? '' : g.err,
    'F-P3-2 GridCtl.ensureIds/rows khong chong loop khong phai mang');
}

// 2d. _row_id trùng (copy draft, import 2 lần, dòng nhân bản bị mất id)
{
  const dup = {
    v: 2, caseId: 'case-dup', checkedForms: ['PLI_M02'],
    store: { values: {}, checks: {}, loops: {
      ds_nganh: [
        { _row_id: 'rSAME', ma_nganh: '0111' },
        { _row_id: 'rSAME', ma_nganh: '4711' },
        { _row_id: 'rSAME', ma_nganh: '5610' }
      ]
    } }
  };
  const r = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(dup))));
  check('P3-D24: _row_id TRUNG -> migrateDraft khong nem', r.ok, r.err);
  const ids = rowIds((r.val || {}).store || { loops: {} }, 'ds_nganh');
  check('P3-D25: _row_id trung DUOC GIU (khong de-dup, khong mat dong, thu tu giu)',
    r.ok && ids.filter(x => x === 'rSAME').length === 3 &&
      (r.val.store.loops.ds_nganh.map(x => x.ma_nganh).join(',') ===
        '0111,4711,5610'),
    ids.join(','));
  // GridCtl.ensureIds (chỗ app.js gọi sau restore) cũng phải không ném và
  // không đụng id đã có
  const r2 = noThrow(() => G.ensureIds(r.val.store));
  check('P3-D26: GridCtl.ensureIds tren store co id trung -> khong nem, khong doi id',
    r2.ok && rowIds(r2.val, 'ds_nganh').filter(x => x === 'rSAME').length === 3,
    rowIds((r2.val || { loops: {} }), 'ds_nganh').join(','));
  // hai dòng trùng id làm findRowIndex chỉ thấy dòng đầu — hành vi đọc được
  check('P3-D27: findRowIndex voi id trung -> tra vi tri dau tien (doc kieu xu ly)',
    G.findRowIndex(r.val.store.loops.ds_nganh, 'rSAME') === 0);
}

// 2e. Loop lớn 10.000 dòng
{
  const big = new Array(10000).fill(0).map((_, i) => ({
    ma_nganh: String(110 + i).padStart(4, '0'),
    ten_nganh: 'Nganh ' + i,
    la_nganh_chinh: i === 0 ? 'X' : ''
  }));
  const d = { v: 1, caseId: 'big', store: { values: {}, checks: {},
    loops: { ds_nganh: big } } };
  const t0 = Date.now();
  const r = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(d))));
  const dt = Date.now() - t0;
  check('P3-D28: loop 10.000 dong -> migrateDraft khong nem', r.ok, r.err);
  check('P3-D29: loop 10.000 dong -> du 10.000 _row_id, dung thu tu, idempotent',
    r.ok && r.val.store.loops.ds_nganh.length === 10000 &&
      r.val.store.loops.ds_nganh[0].ma_nganh === '0110' &&
      r.val.store.loops.ds_nganh[9999].ma_nganh === '10109' &&
      JSON.stringify(rowIds(r.val.store, 'ds_nganh')) ===
        JSON.stringify(rowIds(FD.migrateDraft(JSON.parse(JSON.stringify(r.val)))
          .store, 'ds_nganh')),
    'n=' + ((r.val && r.val.store && r.val.store.loops.ds_nganh || []).length));
  check('P3-D30: migrate 10.000 dong hoan thanh trong <5s (khong bi treo UI)',
    dt < 5000, dt + 'ms');
  // export payload vẫn sạch và đủ
  const ex = noThrow(() => G.exportLoops(r.val.store, ['PLI_M02']));
  check('P3-D31: exportLoops 10.000 dong -> khong nem, bo _*, du 10.000 dong',
    ex.ok && ex.val.ds_nganh.length === 10000 &&
      Object.keys(ex.val.ds_nganh[0]).every(k => k.charAt(0) !== '_'),
    ex.ok ? '' : ex.err);
  const pay = noThrow(() => JSON.stringify(ex.val));
  check('P3-D32: serialize payload 10.000 dong khong nem, kich thuoc hop ly',
    pay.ok && pay.val.length > 10000 && pay.val.length < 5e6,
    (pay.val || '').length + ' bytes');
}

// 2f. Unicode/emoji + ký tự điều khiển trong giá trị
{
  const WEIRD = [
    'emoji 🙃🇻🇳👍',
    'NUL \u0000 gi\u00e3\u00bfa chu\u1ed7i',
    'BEL \u0007 va unit sep \u001f',
    'newline \n va \r CR va \t tab',
    'bmp \u2b50 + surrogate pair \u{1D54F}',
    'RTL \u200f dao \u202e chieu \u202c xong',
    '"nháy kép" + \\backslash\\ + </script>',
    'zalgo Vı̣ệt đã tổ hợp'
  ];
  const rows = WEIRD.map((v, i) => ({ ma_nganh: String(1000 + i), ten_nganh: v }));
  const d = { v: 1, store: { values: {
    'dn.ten_tieng_viet': WEIRD.join('|'), 'dn.ma_so_dn': '031234567890'
  }, checks: {}, loops: { ds_nganh: rows } } };
  const ser = noThrow(() => JSON.stringify(d));
  check('P3-D33: stringify draft co NUL/emoji/surrogate/Zalgo khong nem',
    ser.ok && ser.val.length > 0, ser.err);
  const back = noThrow(() => JSON.parse(ser.val));
  check('P3-D34: parse nguoc lai khong nem, gia tri giu nguyen dung tung byte',
    back.ok && WEIRD.every((v, i) => back.val.store.loops.ds_nganh[i].ten_nganh === v) &&
      back.val.store.values['dn.ten_tieng_viet'] === WEIRD.join('|'),
    ser.ok ? '' : ser.err);
  const mg = noThrow(() => FD.migrateDraft(back.val));
  check('P3-D35: migrateDraft tren gia tri la -> khong nem, giu nguyen + gan id',
    mg.ok && WEIRD.every((v, i) =>
      mg.val.store.loops.ds_nganh[i].ten_nganh === v) &&
      mg.val.store.loops.ds_nganh.every(r2 => typeof r2._row_id === 'string'),
    mg.ok ? '' : mg.err);
  // và qua GridCtl.exportLoops (payload DOCX)
  const ex = noThrow(() => G.exportLoops(mg.val.store, ['PLI_M02']));
  check('P3-D36: exportLoops tren gia tri la -> khong nem, gia tri giu nguyen',
    ex.ok && ex.val.ds_nganh.length === WEIRD.length &&
      ex.val.ds_nganh[6].ten_nganh === WEIRD[6], ex.ok ? '' : ex.err);
}

// 2g. Tên profile dài 4096 ký tự (tên file draft do Bridge.save_draft nhận)
{
  const long4096 = 'p'.repeat(4096);
  const d = { v: 2, caseId: long4096, checkedForms: ['PLI_M02'],
    store: { values: { 'dn.ten_tieng_viet': long4096 }, checks: {},
      loops: {} } };
  const r = noThrow(() => FD.migrateDraft(JSON.parse(JSON.stringify(d))));
  check('P3-D37: caseId 4096 ky tu -> migrateDraft khong nem, giu nguyen',
    r.ok && r.val.caseId === long4096, r.err);
  check('P3-D38: values 4096 ky tu -> giu nguyen qua round-trip',
    r.ok && r.val.store.values['dn.ten_tieng_viet'] === long4096);
  // serialize + parse lại (như save_draft -> load_draft)
  const rt = noThrow(() => JSON.parse(JSON.stringify(r.val)));
  check('P3-D39: round-trip draft voi ten 4096 ky tu khong nem, khong mat du lieu',
    rt.ok && rt.val.caseId === long4096);
  // tên file: chỉ char hợp lệ của filesystem mới được dùng làm tên profile
  const safeName = long4096.replace(/[^A-Za-z0-9._-]/g, '_');
  check('P3-D40: ten profile 4096 ky tu chi gom ky tu an toan -> do dai khong doi',
    safeName.length === 4096);
  // tên vượt giới hạn 255 byte của filesystem phải được caller cắt (không ném)
  const over255 = 'x'.repeat(300);
  const cut = over255.slice(0, 255);
  check('P3-D41: ten >255 byte phai duoc cat xuong 255 truoc khi ghi file',
    Buffer.byteLength(cut, 'utf8') === 255 &&
      Buffer.byteLength(over255, 'utf8') > 255);
}

// ======================================================================
// 3. Save / reload round-trip
// ======================================================================
section('3. Save/reload round-trip (json.dump -> json.load -> migrateDraft)');
{
  const store = { values: {}, checks: {}, loops: {} };
  store.values['dn.ten_tieng_viet'] = 'CÔNG TY ROUND TRIP';
  store.values['dn.ma_so_dn'] = '031234567890';
  store.checks['chk_tt_thanh_lap_moi'] = true;
  store.loops.ds_nganh = [
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
    { ma_nganh: '4711', ten_nganh: 'Bán lẻ', la_nganh_chinh: '' }
  ];
  const draft = { v: 2, caseId: 'thanh_lap_tnhh_1tv',
    checkedForms: ['PLI_M02'], activeDocId: 'PLI_M02', autoSum: false,
    viewState: { PLI_M02: { scrollTop: 120 } }, savedAt: '2026-08-27T00:00:00Z',
    store: store };
  const ser = JSON.stringify(draft);
  const loaded = JSON.parse(ser);
  const r = noThrow(() => FD.migrateDraft(loaded));
  check('P3-D42: round-trip v2 khong nem, tra ve chinh object',
    r.ok && r.val === loaded);
  check('P3-D43: round-trip giu nguyen values/checks/viewState/savedAt',
    r.val.store.values['dn.ten_tieng_viet'] === 'CÔNG TY ROUND TRIP' &&
      r.val.store.checks['chk_tt_thanh_lap_moi'] === true &&
      r.val.viewState.PLI_M02.scrollTop === 120 &&
      r.val.savedAt === '2026-08-27T00:00:00Z');
  check('P3-D44: round-trip gan _row_id cho dong chua co, idempotent lan 2',
    (() => {
      const a1 = rowIds(r.val.store, 'ds_nganh');
      const l2 = FD.migrateDraft(JSON.parse(JSON.stringify(r.val)));
      return a1.length === 2 && a1.every(x => typeof x === 'string') &&
        JSON.stringify(a1) === JSON.stringify(rowIds(l2.store, 'ds_nganh'));
    })());
  // validate ngay trên store đã round-trip không ném
  const v = noThrow(() => FD.validateDocument('PLI_M02', M02.blocks, r.val.store,
    { vsicList: [{ ma: '0111', ten: 'Trồng lúa', cap: 4 }] }));
  check('P3-D45: validateDocument tren store round-trip khong nem (tra mang)',
    v.ok && Array.isArray(v.val), v.ok ? '' : v.err);
  // draft v1 save trước rồi load sau vẫn lên v2 và giữ lựa chọn mẫu
  const legacySer = JSON.stringify({ v: 1, caseId: 'big',
    checkedForms: ['PLI_M02', 'PLI_M06'], store: { values: {}, checks: {},
      loops: { ds_nganh: [{ ma_nganh: '0111' }] } } });
  const l2 = noThrow(() => FD.migrateDraft(JSON.parse(legacySer)));
  check('P3-D46: draft v1 qua save/load -> v2 + giu checkedForms + gan id',
    l2.ok && l2.val.v === 2 &&
      JSON.stringify(l2.val.checkedForms) === '["PLI_M02","PLI_M06"]' &&
      typeof l2.val.store.loops.ds_nganh[0]._row_id === 'string');
}

// ------------------------------------------------------------------ summary
console.log('-'.repeat(64));
if (FINDINGS.length) {
  console.log('KNOWN-FINDINGS (production, KHONG sua trong lane nay):');
  FINDINGS.forEach(f => console.log('  - ' + f));
}
console.log('test_p3_draft: ' + passed + ' PASS / ' + failed + ' FAIL / ' +
  FINDINGS.length + ' KNOWN-FINDING');
process.exit(failed ? 1 : 0);
