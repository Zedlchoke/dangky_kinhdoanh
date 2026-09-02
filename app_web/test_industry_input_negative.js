/* test_industry_input_negative.js — LANE fix-industry (Wave D batch 1): Class 9
 * "bảng ngành: ô Tên ngành hiện 'undefined', Mã ngành tự có '6'" (defect
 * registry Class 9, ảnh owner 2026-08-28 14:13).
 *
 * Chạy:  node app_web/test_industry_input_negative.js
 *
 * ĐỎ TRƯỚC khi sửa (red-first): suite này phải FAIL trên source chưa fix ở
 * các nhóm S1..S7, rồi PASS sau khi fix ở lớp normalize/binding
 * (app_web/ui/form-domain.js + app_web/ui/app.js) — KHÔNG vá từng chỗ hiển thị.
 *
 * Phủ (6 yêu cầu của lane):
 *  S1. Draft row thiếu ten_nganh/ma_nganh (undefined/null) -> sau load
 *      (migrateDraft/normalizeStoreLoops) KHÔNG còn giá trị nullish; binding
 *      hiển thị (render.makeAccessors.getVal) cho chuỗi rỗng, không 'undefined'.
 *  S2. Draft legacy shape: loop ngành chứa row dạng scalar (vd 6) hoặc null
 *      -> normalize an toàn (dòng object rỗng, không ném, không hiện rác).
 *  S3. VSIC async selection: danh mục {ma, ten, cap} map ĐÚNG vào row
 *      (ma_nganh/ten_nganh theo autoName.nameTag) — gốc rễ ô 'undefined' là
 *      nhầm key item['ma_nganh']/item['ten_nganh']; + selection bám _row_id
 *      (reload/reorder giữa chừng không ghi nhầm dòng).
 *  S4. Autosave giữa lúc thêm/xóa row -> draft round-trip không sinh row id
 *      NaN/junk; ghi ô với index NaN bị từ chối, không tạo row rác.
 *  S5. la_nganh_chinh: đúng MỘT ngành chính sau add/delete/reorder; xóa dòng
 *      đang là ngành chính -> 0 ngành chính (HỢP LỆ, KHÔNG tự chọn hộ) và
 *      validator báo PRIMARY_INDUSTRY_REQUIRED blocking.
 *  S6. Export payload: Bridge export payload KHÔNG chứa undefined/NaN (kiểm
 *      cả in-memory lẫn chuỗi JSON thật của payload).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');            // Helpers.GridCtl (thuần)
const G = App.GridCtl;

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
const VSIC = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'app', 'data', 'nganh_vsic.json'), 'utf8')
).nganh;

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) {
    passed++;
    console.log('PASS  ' + name);
  } else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function section(t) { console.log('\n===== ' + t + ' ====='); }

/* Mã ngành thật trong danh mục để test autoName không báo NAME_MISMATCH. */
function vsicByMa(ma) {
  return VSIC.filter(x => String(x.ma) === String(ma))[0] || null;
}
const MA_1 = '0111';                       // Trồng lúa (cap 3)
const ITEM_1 = vsicByMa(MA_1);
const ITEM_CAP4 = VSIC.filter(x => x.cap === 4)[0];

function newStore() { return { values: {}, checks: {}, loops: {} }; }

/* Row còn giá trị nullish (undefined/null) ở bất kỳ key nào? */
function hasNullish(row) {
  return Object.keys(row).some(k => row[k] === undefined || row[k] === null);
}

// ============================================================ S1: draft row thiếu key
section('S1. Draft row thiếu ten_nganh/ma_nganh (undefined/null)');

{
  const draft = {
    v: 2, caseId: 'c1', checkedForms: ['PLI_M01'], activeDocId: 'PLI_M01',
    autoSum: false, viewState: {}, savedAt: null,
    store: {
      values: {}, checks: {},
      loops: {
        ds_nganh: [
          { ten_nganh: undefined, ma_nganh: null, chi_tiet: 'có chi tiết' },
          {}                                                    // thiếu cả 3 key
        ]
      }
    }
  };
  let out = null;
  try { out = FD.migrateDraft(draft); } catch (e) { check('S1 load draft không ném', false, String(e)); }
  const rows = out && out.store && out.store.loops.ds_nganh;
  check('S1 load draft không ném + đủ 2 dòng', Array.isArray(rows) && rows.length === 2,
    JSON.stringify(rows));
  if (Array.isArray(rows)) {
    check('S1 không còn giá trị nullish (undefined/null) trong row',
      rows.every(r => !hasNullish(r)),
      JSON.stringify(rows));
    check('S1 giá trị thiếu key -> chuỗi rỗng (không chữ "undefined")',
      rows[0].ten_nganh === '' && rows[0].ma_nganh === '' && rows[1].ten_nganh === '',
      JSON.stringify(rows));
    check('S1 dữ liệu thật giữ nguyên + _row_id được gán',
      rows[0].chi_tiet === 'có chi tiết' &&
        rows.every(r => typeof r._row_id === 'string' && /^r\d+_/.test(r._row_id)),
      JSON.stringify(rows.map(r => r._row_id)));
  }
  // Binding hiển thị chuẩn (cùng accessor render.js dùng): thiếu key -> ''
  if (rows) {
    const acc = R.makeAccessors(out.store);
    check('S1 getVal ô ten_nganh -> chuỗi rỗng, không "undefined"',
      acc.getVal('loop:ds_nganh:0:ten_nganh') === '' &&
        acc.getVal('loop:ds_nganh:1:ma_nganh') === '',
      JSON.stringify([acc.getVal('loop:ds_nganh:0:ten_nganh'),
        acc.getVal('loop:ds_nganh:1:ma_nganh')]));
  }
}

// ============================================================ S2: legacy shape scalar/null
section('S2. Draft legacy: loop ngành chứa row scalar/null');

{
  const draft = {
    v: 1, caseId: 'c2', checkedForms: [], autoSum: false,
    store: {
      values: {}, checks: {},
      loops: { ds_nganh_kinh_doanh: [null, 6, '0111', { ma_nganh: '0111' }] }
    }
  };
  let out = null;
  try { out = FD.migrateDraft(draft); } catch (e) { check('S2 migrate legacy không ném', false, String(e)); }
  const rows = out && out.store && out.store.loops.ds_nganh;
  check('S2 migrate legacy không ném + giữ số dòng/thứ tự',
    Array.isArray(rows) && rows.length === 4, JSON.stringify(rows));
  if (Array.isArray(rows)) {
    check('S2 mọi row sau normalize là object (không scalar/null lộ ra)',
      rows.every(r => r && typeof r === 'object' && !Array.isArray(r)),
      JSON.stringify(rows));
    check('S2 row scalar "6"/null không hiện rác (ten/ma đọc ra chuỗi rỗng)',
      String((rows[0] || {}).ten_nganh) === '' &&
        String((rows[1] || {}).ten_nganh) === '' &&
        String((rows[1] || {}).ma_nganh) === '',
      JSON.stringify(rows));
    check('S2 row object thật giữ nguyên dữ liệu + mọi row có _row_id',
      (rows[3] || {}).ma_nganh === '0111' &&
        rows.every(r => r && typeof r === 'object' &&
          typeof r._row_id === 'string' && /^r\d+_/.test(r._row_id)),
      JSON.stringify(rows));
  }
}

// ============================================================ S3: VSIC pick đúng key + bám _row_id
section('S3. VSIC selection: map {ma,ten} đúng tag + bám _row_id');

{
  check('S3a helper vsicPickValues tồn tại (chốt map thuần để test được)',
    typeof App.vsicPickValues === 'function');
  if (typeof App.vsicPickValues === 'function') {
    const vals = App.vsicPickValues(ITEM_1, 'ten_nganh');
    check('S3a pick map ma -> ma_nganh (không còn item["ma_nganh"]=undefined)',
      vals.ma_nganh === String(ITEM_1.ma), JSON.stringify(vals));
    check('S3a pick map ten -> autoName.nameTag (không undefined)',
      vals.ten_nganh === String(ITEM_1.ten), JSON.stringify(vals));
    const vals2 = App.Helpers.vsicPickValues(ITEM_CAP4, 'ten_nganh_bo_sung');
    check('S3a loop khác nameTag (PLII_M02) vẫn nhận đúng tên ngành',
      vals2.ten_nganh_bo_sung === String(ITEM_CAP4.ten) &&
        vals2.ma_nganh === String(ITEM_CAP4.ma),
      JSON.stringify(vals2));
    check('S3a pick KHÔNG trả giá trị nullish',
      Object.keys(vals).every(k => vals[k] !== undefined && vals[k] !== null),
      JSON.stringify(vals));
  }

  // S3b: ghi ô qua tham chiếu ổn định (_row_id ưu tiên, index chỉ fallback)
  check('S3b GridCtl.setCell tồn tại (ghi ô bám _row_id)',
    typeof G.setCell === 'function');
  if (typeof G.setCell === 'function') {
    const store = newStore();
    store.loops.ds_nganh = [
      { _row_id: 'r1_aaa', ma_nganh: '', ten_nganh: '' },
      { _row_id: 'r2_bbb', ma_nganh: '', ten_nganh: '' }
    ];
    // Sau reorder, dòng r1_aaa đang ở index 1; ref cũ (idx 0) vẫn phải ghi
    // ĐÚNG dòng r1_aaa (reload/reorder giữa chừng không đổi nhầm dòng).
    const reordered = [store.loops.ds_nganh[1], store.loops.ds_nganh[0]];
    store.loops.ds_nganh = reordered;
    const ok = G.setCell(store, 'ds_nganh',
      { rowId: 'r1_aaa', idx: 0 }, 'ma_nganh', String(ITEM_1.ma));
    check('S3b setCell bám _row_id dù index đã đổi sau reorder',
      ok &&
        store.loops.ds_nganh[1].ma_nganh === String(ITEM_1.ma) &&
        store.loops.ds_nganh[0].ma_nganh === '',
      JSON.stringify(store.loops.ds_nganh));
    // Dòng đã bị xóa -> từ chối ghi, không tạo row rác
    const ok2 = G.setCell(store, 'ds_nganh',
      { rowId: 'r9_deleted', idx: 99 }, 'ten_nganh', 'RÁC');
    check('S3b setCell dòng không tồn tại -> false, store nguyên vẹn',
      ok2 === false && store.loops.ds_nganh.length === 2 &&
        !hasNullish(store.loops.ds_nganh[0]) && !hasNullish(store.loops.ds_nganh[1]),
      JSON.stringify(store.loops.ds_nganh));
    // Index NaN (key hỏng kiểu loop:x:NaN:tag) -> từ chối, không sinh row NaN
    const ok3 = G.setCell(store, 'ds_nganh',
      { rowId: null, idx: NaN }, 'ma_nganh', '0111');
    check('S3b setCell index NaN -> false, không tạo row mới / không ném',
      ok3 === false && store.loops.ds_nganh.length === 2,
      JSON.stringify(store.loops.ds_nganh.map(r => r._row_id)));
    // Ghi giá trị nullish -> chuỗi rỗng, không bao giờ undefined vào store
    const ok4 = G.setCell(store, 'ds_nganh',
      { rowId: 'r2_bbb', idx: 0 }, 'ten_nganh', undefined);
    check('S3b setCell giá trị nullish -> chuỗi rỗng',
      ok4 === true && store.loops.ds_nganh[1].ten_nganh === '',
      JSON.stringify(store.loops.ds_nganh[1]));
  }
}

// ============================================================ S4: autosave giữa add/delete
section('S4. Autosave giữa lúc thêm/xóa row: không sinh row id NaN/junk');

{
  const store = newStore();
  G.addRow(store, 'ds_nganh', null);
  const keep = store.loops.ds_nganh[0];
  keep.ma_nganh = MA_1;
  keep.ten_nganh = ITEM_1.ten;
  keep.la_nganh_chinh = 'X';
  const added = G.addRow(store, 'ds_nganh', keep._row_id); // đang thêm dòng mới
  G.deleteRows(store, 'ds_nganh', [added.id]);              // ...rồi xóa ngay

  // autosave: đúng những gì draftPayload() làm (JSON.stringify -> parse)
  const saved = JSON.parse(JSON.stringify(
    { v: 2, caseId: 'c4', store: JSON.parse(JSON.stringify(store)) }));
  let out = null;
  try { out = FD.migrateDraft(saved); } catch (e) { check('S4 round-trip không ném', false, String(e)); }
  const rows = out && out.store && out.store.loops.ds_nganh;
  check('S4 round-trip giữ đúng 1 dòng (không row rác)',
    Array.isArray(rows) && rows.length === 1, JSON.stringify(rows));
  if (Array.isArray(rows)) {
    check('S4 mọi row id là chuỗi hợp lệ, KHÔNG NaN/undefined/junk',
      rows.every(r => r && typeof r === 'object' &&
        typeof r._row_id === 'string' && /^r\d+_|^[A-Za-z0-9-]+$/.test(r._row_id) &&
        r._row_id !== 'NaN' && r._row_id !== 'undefined'),
      JSON.stringify(rows.map(r => r && r._row_id)));
    check('S4 id dòng sống sót giữ nguyên qua autosave (ổn định)',
      rows[0] && rows[0]._row_id === keep._row_id,
      String(rows[0] && rows[0]._row_id) + ' != ' + keep._row_id);
  }

  // Draft hỏng với id rác (NaN/undefined/số) -> normalize gán lại id hợp lệ
  const junk = FD.migrateDraft({
    v: 2, store: { values: {}, checks: {}, loops: { ds_nganh: [
      { _row_id: 'NaN', ma_nganh: MA_1 },
      { _row_id: 'undefined' },
      { _row_id: 6 }
    ] } }
  });
  const jrows = junk.store.loops.ds_nganh;
  check('S4 row id rác (NaN/undefined/số) được gán lại id hợp lệ',
    jrows.every(r => typeof r._row_id === 'string' &&
      r._row_id !== 'NaN' && r._row_id !== 'undefined' &&
      /^r\d+_/.test(r._row_id)),
    JSON.stringify(jrows.map(r => r._row_id)));
  check('S4 dữ liệu row id rác vẫn giữ nguyên sau khi gán lại',
    jrows[0].ma_nganh === MA_1, JSON.stringify(jrows[0]));
}

// ============================================================ S5: la_nganh_chinh
section('S5. Đúng MỘT ngành chính sau add/delete/reorder');

{
  const doc = loadProd('PLI_M01');
  const ctx = { vsicList: VSIC };
  const store = newStore();
  const mk = (ma) => ({
    ma_nganh: ma, ten_nganh: (vsicByMa(ma) || {}).ten || '', chi_tiet: '',
    la_nganh_chinh: ''
  });
  const a = { _row_id: 'r1_pma', ...mk(MA_1) };
  const b = { _row_id: 'r2_pmb', ...mk('0112') };
  const c = { _row_id: 'r3_pmc', ...mk('0121') };
  store.loops.ds_nganh = [a, b, c];

  // radio một lựa chọn: chọn c -> đúng 1 'X'
  G.setExclusiveRadio(store, 'ds_nganh', 'r3_pmc', 'la_nganh_chinh', true);
  const cntX = () => store.loops.ds_nganh.filter(r => r.la_nganh_chinh === 'X').length;
  check('S5 chọn radio -> đúng 1 dòng la_nganh_chinh = "X"', cntX() === 1,
    JSON.stringify(store.loops.ds_nganh.map(r => r.la_nganh_chinh)));

  // reorder (chuyển dòng chính lên trên 1 vị trí: index 2 -> 1)
  // -> vẫn đúng 1, vẫn là dòng cũ
  G.moveRow(store, 'ds_nganh', 'r3_pmc', -1);
  check('S5 sau reorder vẫn đúng 1 ngành chính, đúng dòng cũ',
    cntX() === 1 && store.loops.ds_nganh[1]._row_id === 'r3_pmc' &&
      store.loops.ds_nganh[1].la_nganh_chinh === 'X',
    JSON.stringify(store.loops.ds_nganh.map(r => r.la_nganh_chinh)));

  // thêm dòng -> không tự sinh thêm ngành chính
  G.addRow(store, 'ds_nganh', null);
  check('S5 sau add vẫn đúng 1 ngành chính (không tự chọn hộ)', cntX() === 1,
    JSON.stringify(store.loops.ds_nganh.map(r => r.la_nganh_chinh)));

  // xóa dòng KHÔNG phải ngành chính -> ngành chính còn nguyên
  G.deleteRows(store, 'ds_nganh', ['r2_pmb']);
  check('S5 xóa dòng thường -> ngành chính giữ nguyên', cntX() === 1 &&
    store.loops.ds_nganh.some(r => r._row_id === 'r3_pmc' && r.la_nganh_chinh === 'X'),
    JSON.stringify(store.loops.ds_nganh.map(r => [r._row_id, r.la_nganh_chinh])));

  // xóa ĐÚNG dòng ngành chính -> 0 ngành chính là HỢP LỆ về dữ liệu
  // (KHÔNG tự chọn hộ) nhưng validator chặn export (blocking).
  G.deleteRows(store, 'ds_nganh', ['r3_pmc']);
  check('S5 xóa dòng ngành chính -> KHÔNG tự chọn hộ (0 dòng "X")', cntX() === 0,
    JSON.stringify(store.loops.ds_nganh.map(r => r.la_nganh_chinh)));
  const errs = FD.validateDocument('PLI_M01', doc.blocks, store, ctx);
  const primary = errs.filter(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED');
  check('S5 0 ngành chính -> PRIMARY_INDUSTRY_REQUIRED blocking',
    primary.length === 1 && primary[0].severity === 'blocking',
    JSON.stringify(errs.map(e => e.code)));
  // có dữ liệu + đủ 1 ngành chính -> không còn lỗi primary
  G.setExclusiveRadio(store, 'ds_nganh', store.loops.ds_nganh[0]._row_id,
    'la_nganh_chinh', true);
  const errs2 = FD.validateDocument('PLI_M01', doc.blocks, store, ctx);
  check('S5 đủ 1 ngành chính -> hết lỗi PRIMARY_INDUSTRY_REQUIRED',
    !errs2.some(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED'),
    JSON.stringify(errs2.map(e => e.code)));
}

// ============================================================ S6: export payload sạch
section('S6. Export payload không chứa undefined/NaN');

{
  const store = newStore();
  store.loops.ds_nganh = [
    { _row_id: 'r1_exp', ma_nganh: MA_1, ten_nganh: ITEM_1.ten,
      chi_tiet: undefined, la_nganh_chinh: 'X' },
    { _row_id: 'r2_exp', ma_nganh: null, ten_nganh: 'Rác chưa normalize',
      chi_tiet: NaN, la_nganh_chinh: false }
  ];
  const exported = G.exportLoops(store, ['PLI_M01']);
  const flat = exported.ds_nganh || [];
  check('S6 payload in-memory không còn giá trị undefined',
    flat.every(r => Object.keys(r).every(k => r[k] !== undefined)),
    JSON.stringify(flat));
  check('S6 payload in-memory không còn giá trị null/NaN',
    flat.every(r => Object.keys(r).every(k =>
      r[k] !== null && !(typeof r[k] === 'number' && !isFinite(r[k])))),
    JSON.stringify(flat));
  const json = JSON.stringify(exported);
  check('S6 chuỗi JSON payload không chứa "undefined"/"NaN"',
    json.indexOf('undefined') < 0 && json.indexOf('NaN') < 0, json);
  check('S6 la_nganh_chinh chỉ là "X"/"" trong payload',
    flat.every(r => r.la_nganh_chinh === 'X' || r.la_nganh_chinh === ''),
    JSON.stringify(flat.map(r => r.la_nganh_chinh)));
  check('S6 _row_id bị loại khỏi payload export',
    flat.every(r => Object.keys(r).every(k => k.charAt(0) !== '_')),
    JSON.stringify(Object.keys(flat[0] || {})));
}

// ============================================================ tổng kết
console.log('\n=========================================');
console.log('PASSED: ' + passed + '  FAILED: ' + failed);
process.exit(failed ? 1 : 0);
