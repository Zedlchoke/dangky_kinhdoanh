/* test_household_shared.js - Wave 2 Agent 2C (industry-household):
 * store.loops.ds_nganh là DỮ LIỆU DÙNG CHUNG (canonical semantics) giữa mẫu
 * hộ kinh doanh PLII_M02, PLII_M07 và chuẩn gốc PLI_M02 — cùng một store
 * render qua cả ba template phải cho CÙNG danh sách ngành, cùng thứ tự,
 * cùng STT và đúng MỘT dòng ngành chính (radio checked).
 *
 * Phong cách AC11 trong app_web/test_acceptance.js, viết lại thành bộ test
 * riêng của nhóm household. Chạy trên PRODUCTION BLOCKS (app/data/blocks/)
 * — KHÔNG dùng mock; đầu file assert fixture thật, thiếu -> exit 1.
 *
 * Chạy:  node app_web/test_household_shared.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');            // Helpers.GridCtl (thuần)
const G = App.GridCtl;

const ROOT = path.join(__dirname, '..');

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

// --------------------------------------------------- dữ liệu PRODUCTION

function loadProd(id) {
  return JSON.parse(fs.readFileSync(
    path.join(ROOT, 'app', 'data', 'blocks', id + '.json'), 'utf8'));
}
const CANON = loadProd('PLI_M02');             // chuẩn gốc (pilot)
const HH02 = loadProd('PLII_M02');             // hộ KD: đề nghị thay đổi
const HH07 = loadProd('PLII_M07');             // hộ KD: giấy chứng nhận

function dsLoop(doc) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === 'ds_nganh')[0] || null;
}

/* Head assert: fixture phải là production thật có loop ds_nganh đủ cột. */
(function headAssert() {
  const l02 = dsLoop(HH02);
  const l07 = dsLoop(HH07);
  const lc = dsLoop(CANON);
  const colsOf = b => (b && b.cols || []).map(c => c.tag).sort().join(',');
  const okFixture =
    !!l02 && !!l07 && !!lc &&
    ['la_nganh_chinh', 'ma_nganh', 'ten_nganh']
      .every(t => l02.cols.some(c => c.tag === t)) &&
    ['la_nganh_chinh', 'ma_nganh', 'ten_nganh']
      .every(t => l07.cols.some(c => c.tag === t)) &&
    ['chi_tiet', 'la_nganh_chinh', 'ma_nganh', 'ten_nganh']
      .every(t => lc.cols.some(c => c.tag === t));
  check('HEAD: nap duoc PRODUCTION blocks PLI_M02/PLII_M02/PLII_M07 co loop ds_nganh',
    okFixture,
    'cols02=' + colsOf(l02) + ' cols07=' + colsOf(l07) + ' canon=' + colsOf(lc));
  if (!okFixture) {
    console.log('Dung lai: khong co production fixture thi test khong co gia tri.');
    process.exit(1);
  }
})();

// ------------------------------------------------------------- html utils

/* Render đúng cách app.js renderActiveDoc: fieldMeta + gridMeta (+uiLayout). */
function renderDoc(doc, store) {
  return R.renderBlocks(doc, store, {
    docId: doc.id, fieldMeta: FD.FIELD_META, gridMeta: FD.GRID_META,
    uiLayout: doc.id === 'PLI_M02' ? UI_LAYOUT_CANON : null
  });
}

let UI_LAYOUT_CANON = null;
try {
  UI_LAYOUT_CANON = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'app', 'data', 'ui_layouts', 'PLI_M02.json'), 'utf8'));
} catch (e) { /* layout tuỳ chọn - production có thể chưa có */ }

function loopTable(html, loop) {
  const m = html.match(new RegExp(
    '<table[^>]*data-loop="' + loop + '"[\\s\\S]*?</table>'));
  return m ? m[0] : '';
}

function bodyRows(tableHtml) {
  const tb = (tableHtml.match(/<tbody>([\s\S]*?)<\/tbody>/) || ['', ''])[1];
  const out = [];
  const re = /<tr([^>]*)>([\s\S]*?)<\/tr>/g;
  let m;
  while ((m = re.exec(tb)) !== null) out.push({ attrs: m[1], inner: m[2] });
  return out;
}

function sttsOf(tableHtml) {
  const out = [];
  const re = /<td class="stt">(\d+)<\/td>/g;
  let m;
  while ((m = re.exec(tableHtml)) !== null) out.push(m[1]);
  return out;
}

/* Giá trị ô (theo tag) của hàng hiển thị thứ i trong bảng loop. */
function cellValueAt(tableHtml, i, tag) {
  const m = tableHtml.match(new RegExp(
    'data-key="loop:[^"]+:' + i + ':' + tag + '"[\\s\\S]*?value="([^"]*)"'));
  return m ? m[1] : null;
}

/* Số radio ngành chính ĐANG tick trong bảng loop. */
function checkedRadios(tableHtml) {
  return (tableHtml.match(/<input type="radio"[^>]*checked/g) || []).length;
}

/* Chỉ số hàng chứa radio ngành chính đang tick (-1 nếu không có). */
function checkedRadioRowAt(tableHtml) {
  const m = tableHtml.match(
    /<input type="radio"[^>]*data-row="(\d+)"[^>]*checked/);
  return m ? Number(m[1]) : -1;
}

// ----------------------------------------------------------------- tests

// Shared store 3 dòng, dòng đầu là ngành chính — giống kịch bản AC11.
const rows = [
  { ma_nganh: '6201', ten_nganh: 'Hoạt động lập trình máy vi tính', la_nganh_chinh: 'X' },
  { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
  { ma_nganh: '4711', ten_nganh: 'Bán lẻ lương thực trong cửa hàng' }
];
const shared = {
  values: {}, checks: {},
  loops: { ds_nganh: rows.map(r => Object.assign({ _row_id: G.nextId() }, r)) }
};

const hCanon = renderDoc(CANON, shared);
const h02 = renderDoc(HH02, shared);
const h07 = renderDoc(HH07, shared);

const tCanon = loopTable(hCanon, 'ds_nganh');
const t02 = loopTable(h02, 'ds_nganh');
const t07 = loopTable(h07, 'ds_nganh');

check('SHARED: ba mau deu tim thay bang loop ds_nganh khi render cung mot store',
  tCanon.length > 0 && t02.length > 0 && t07.length > 0);

const nCanon = bodyRows(tCanon).length;
const n02 = bodyRows(t02).length;
const n07 = bodyRows(t07).length;
check('SHARED: ba mau cung hien CUNG SO DONG cho cung mot store',
  n02 === n07 && n02 === nCanon && n02 >= rows.length,
  'canon=' + nCanon + ' M02=' + n02 + ' M07=' + n07);

const codesWant = rows.map(r => r.ma_nganh).join(',');
const codesCanon = rows.map((_, i) => cellValueAt(tCanon, i, 'ma_nganh')).join(',');
const codes02 = rows.map((_, i) => cellValueAt(t02, i, 'ma_nganh')).join(',');
const codes07 = rows.map((_, i) => cellValueAt(t07, i, 'ma_nganh')).join(',');
check('SHARED: cung THU TU ma o ca ba mau (dong bo lien mau voi canonical)',
  codes02 === codes07 && codes07 === codesCanon && codes02 === codesWant,
  'canon=[' + codesCanon + '] M02=[' + codes02 + '] M07=[' + codes07 + '] want=[' + codesWant + ']');

const tens02 = rows.map((_, i) => cellValueAt(t02, i, 'ten_nganh')).join('|');
const tens07 = rows.map((_, i) => cellValueAt(t07, i, 'ten_nganh')).join('|');
const tensWant = rows.map(r => r.ten_nganh).join('|');
check('SHARED: dung TEN NGANH tung dong o ca hai mau ho kinh doanh',
  tens02 === tens07 && tens02 === tensWant,
  'M02=[' + tens02 + '] M07=[' + tens07 + '] want=[' + tensWant + ']');

const sttsWant = rows.map((_, i) => String(i + 1)).join(',');
check('SHARED: STT ba mau giong nhau (1..n)',
  sttsOf(t02).slice(0, rows.length).join(',') === sttsWant &&
  sttsOf(t07).slice(0, rows.length).join(',') === sttsWant &&
  sttsOf(tCanon).slice(0, rows.length).join(',') === sttsWant,
  'M02=[' + sttsOf(t02) + '] M07=[' + sttsOf(t07) + '] canon=[' + sttsOf(tCanon) + ']');

check('SHARED: dung MOT dong duoc tick nganh chinh o tung bang (radio checked x1)',
  checkedRadios(tCanon) === 1 && checkedRadios(t02) === 1 && checkedRadios(t07) === 1,
  'canon=' + checkedRadios(tCanon) + ' M02=' + checkedRadios(t02) +
  ' M07=' + checkedRadios(t07));

check('SHARED: dong nganh chinh la DONG DAU (row 0)',
  checkedRadioRowAt(tCanon) === 0 && checkedRadioRowAt(t02) === 0 &&
    checkedRadioRowAt(t07) === 0,
  'canon@' + checkedRadioRowAt(tCanon) + ' M02@' + checkedRadioRowAt(t02) +
  ' M07@' + checkedRadioRowAt(t07));

// Đổi store (xóa dòng ngành chính, thêm dòng mới) rồi render lại ->
// cả ba mẫu thấy cùng thay đổi, không còn dòng nào tick ngành chính.
G.deleteRows(shared, 'ds_nganh', [shared.loops.ds_nganh[0]._row_id]);
G.addRow(shared, 'ds_nganh', null);
shared.loops.ds_nganh[shared.loops.ds_nganh.length - 1].ma_nganh = '4712';
const codesAfter = shared.loops.ds_nganh.map(r => r.ma_nganh);
const againCanon = [0, 1, 2].map(i =>
  cellValueAt(loopTable(renderDoc(CANON, shared), 'ds_nganh'), i, 'ma_nganh'));
const again02 = [0, 1, 2].map(i =>
  cellValueAt(loopTable(renderDoc(HH02, shared), 'ds_nganh'), i, 'ma_nganh'));
const again07 = [0, 1, 2].map(i =>
  cellValueAt(loopTable(renderDoc(HH07, shared), 'ds_nganh'), i, 'ma_nganh'));
check('SHARED: sau thay doi store, ba mau van cung danh sach + thu tu',
  again02.join(',') === again07.join(',') &&
  again07.join(',') === againCanon.join(',') &&
  again02.join(',') === codesAfter.join(','),
  'canon=[' + againCanon + '] M02=[' + again02 + '] M07=[' + again07 +
  '] want=[' + codesAfter + ']');
const re02 = loopTable(renderDoc(HH02, shared), 'ds_nganh');
const re07 = loopTable(renderDoc(HH07, shared), 'ds_nganh');
check('SHARED: sau thay doi khong con dong nao tick nganh chinh (can xoa chon lai)',
  checkedRadios(re02) === 0 && checkedRadios(re07) === 0,
  'M02=' + checkedRadios(re02) + ' M07=' + checkedRadios(re07));

// ----------------------------------------------------------------- summary

console.log('-'.repeat(60));
console.log('test_household_shared: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed === 0 ? 0 : 1);
