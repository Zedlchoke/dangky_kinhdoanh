/* test_acceptance.js - BỘ ACCEPTANCE TEST BẮT BUỘC theo PLAN.md mục
 * "Acceptance tests bắt buộc" (14 mục) cho pilot bảng ngành `ds_nganh`.
 *
 * Chạy trên PRODUCTION BLOCKS (app/data/blocks/*.json) + danh mục thật
 * (app/data/nganh_vsic.json) - KHÔNG dùng mock. Đầu file assert rằng nạp
 * được blocks/catalog thật và loop ds_nganh tồn tại (AC14); thiếu -> exit 1.
 *
 * Chạy:  node app_web/test_acceptance.js
 *
 * Luồng "controller" được mô phỏng đúng phần THUẦN của app_web/ui/app.js:
 *  - gõ mã ngành   : GridCtl.vsicResolve -> exact: điền ten; invalid: xóa ten
 *                    (handleMaNganhInput);
 *  - Enter/chọn gợi ý: searchVsic -> pick -> điền CẢ mã+tên cùng dòng
 *                    (applyVsicPick);
 *  - thao tác bảng : GridCtl.addRow/deleteRows/moveRow/setExclusiveRadio;
 *  - confirm xóa   : mô phỏng confirm=false KHÔNG gọi deleteRows
 *                    (uiDeleteRows + GRID_META.confirmDeleteNonEmpty).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

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

const DATA_DIR = path.join(ROOT, 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
const M02 = loadProd('PLI_M02');               // pilot: loop ds_nganh 5 cột
const M01 = loadProd('PLII_M01');              // ds_nganh + ds_tv_ho_gia_dinh
const M06 = loadProd('PLI_M06');               // ds_thanh_vien (minRows)
const VSIC = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'app', 'data', 'nganh_vsic.json'), 'utf8')
).nganh;
let UI_LAYOUT_M02 = null;
try {
  UI_LAYOUT_M02 = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'app', 'data', 'ui_layouts', 'PLI_M02.json'), 'utf8'));
} catch (e) { /* layout tuỳ chọn - production có thể chưa có */ }

/* AC14 - assert ĐẦU FILE: fixtures phải là production thật, không mock. */
(function headAssert() {
  const loops02 = (M02.blocks || []).filter(b => b.t === 'loop');
  const ng02 = loops02.filter(b => b.loop === 'ds_nganh')[0];
  const loops01 = (M01.blocks || []).filter(b => b.t === 'loop');
  const ng01 = loops01.filter(b => b.loop === 'ds_nganh')[0];
  const okFixture =
    Array.isArray(M02.blocks) && M02.blocks.length > 100 &&
    !!ng02 && !!ng01 &&
    ['ma_nganh', 'ten_nganh', 'chi_tiet', 'la_nganh_chinh']
      .every(t => (ng02.cols || []).some(c => c.tag === t)) &&
    loops01.some(b => b.loop === 'ds_tv_ho_gia_dinh') &&
    Array.isArray(VSIC) && VSIC.length > 500 &&
    VSIC.some(x => String(x.ma) === '0111' && x.ten === 'Trồng lúa');
  check('AC14: nap duoc PRODUCTION blocks PLI_M02/PLII_M01 + nganh_vsic.json ' +
        '(loop ds_nganh ton tai, khong fallback mock)', okFixture,
    'M02.blocks=' + (M02.blocks || []).length +
    ' loops02=' + loops02.map(b => b.loop) +
    ' vsic=' + (VSIC || []).length);
  if (!okFixture) {
    console.log('Dung lai: khong co production fixture thi acceptance khac khong co gia tri.');
    process.exit(1);
  }
})();

// ------------------------------------------------------------- html utils

function findLoopBlock(doc, loopName) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === loopName)[0] || null;
}

/* Render đúng cách app.js renderActiveDoc: fieldMeta + gridMeta (+uiLayout). */
function renderDoc(doc, store) {
  return R.renderBlocks(doc, store, {
    docId: doc.id, fieldMeta: FD.FIELD_META, gridMeta: FD.GRID_META,
    uiLayout: doc.id === 'PLI_M02' ? UI_LAYOUT_M02 : null
  });
}

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

function unesc(s) {
  return String(s == null ? '' : s).replace(/&amp;/g, '&').replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}

// ------------------------------------- mô phỏng thuần luồng controller app.js

/* handleMaNganhInput (app_web/ui/app.js): generic input handler đã lưu ô mã
 * vào row; sau đó controller phân loại qua GridCtl.vsicResolve. */
function flowTypeMaNganh(row, raw) {
  row.ma_nganh = raw;                          // sự kiện input thường
  const res = G.vsicResolve(VSIC, raw);
  if (res.st === 'exact') row.ten_nganh = res.item.ten;     // tự điền tên
  else if (res.st === 'invalid') row.ten_nganh = '';        // đổi mã: bỏ tên cũ
  /* empty: đã xóa tên; typing: chỉ gợi ý - cả hai xử lý ở nhánh tương ứng */
  else if (res.st === 'empty') row.ten_nganh = '';
  return res;
}

/* applyVsicPick (app_web/ui/app.js): chọn 1 kết quả (chuột/Enter) điền CẢ
 * mã + tên vào CÙNG dòng. */
function flowPickVsicItem(row, item) {
  row.ma_nganh = String(item.ma);
  row.ten_nganh = String(item.ten);
}

/* uiDeleteRows (app_web/ui/app.js) - nhánh 1 dòng: confirm chặn splice. */
function uiDeleteRowsPure(store, loop, rowId, confirmFn) {
  const gm = G.meta(loop);
  if (gm && gm.allowDelete === false) return 'blocked-meta';
  const rows = store.loops[loop] || [];
  if (!rows.length) return 'empty';
  const ix = G.findRowIndex(rows, rowId);
  if (ix < 0) return 'not-found';
  const r = rows[ix];
  const hasData = Object.keys(r || {}).some(k =>
    k.charAt(0) !== '_' && String(r[k] == null ? '' : r[k]).trim() !== '');
  const needConfirm = !gm || gm.confirmDeleteNonEmpty !== false;
  if (hasData && needConfirm && !confirmFn(r, ix)) return 'cancelled';
  G.deleteRows(store, loop, [rowId]);
  return 'deleted';
}

function industryStore(rowsSpec) {
  const s = R.newStore();
  s.loops.ds_nganh = rowsSpec.map(r =>
    Object.assign({ _row_id: G.nextId() }, r));
  return s;
}

const CTX = () => ({ vsicList: VSIC });
function errsDoc(docId, blocks, store) {
  return FD.validateDocument(docId, blocks, store, CTX());
}
function blockingOf(errs, code) {
  return errs.filter(e => e.code === code && e.severity === 'blocking');
}

/* Chạy script python phụ (AC13); trả {code, out}. */
function runPy(scriptRel) {
  try {
    const out = execSync('python -X utf8 "' + scriptRel + '"', {
      cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']
    });
    return { code: 0, out: String(out) };
  } catch (e) {
    return {
      code: (e && e.status != null) ? e.status : 1,
      out: String((e && e.stdout) || '') + String((e && e.stderr) || '')
    };
  }
}

// ======================================================================
// AC1 - Nhập '0111' -> vsicResolve exact -> ten_nganh tự thành 'Trồng lúa'
// ======================================================================
{
  const row = {};
  const res = flowTypeMaNganh(row, '0111');
  check("AC1: go '0111' -> vsicResolve exact",
    res.st === 'exact' && !!res.item, JSON.stringify(res));
  check("AC1: ten_nganh TU THANH 'Trồng lúa' cung dong voi ma",
    row.ma_nganh === '0111' && row.ten_nganh === 'Trồng lúa',
    JSON.stringify(row));

  // Cùng hành vi nhìn từ renderer: giá trị nằm đúng ô trên production blocks
  const store = industryStore([{ ma_nganh: row.ma_nganh, ten_nganh: row.ten_nganh }]);
  store.loops.ds_nganh[0].la_nganh_chinh = 'X';
  const html = renderDoc(M02, store);
  const tbl = loopTable(html, 'ds_nganh');
  check('AC1: tren PLI_M02 production, o ma/ten hien dung gia tri',
    cellValueAt(tbl, 0, 'ma_nganh') === '0111' &&
      unesc(cellValueAt(tbl, 0, 'ten_nganh')) === 'Trồng lúa',
    cellValueAt(tbl, 0, 'ma_nganh') + '/' + cellValueAt(tbl, 0, 'ten_nganh'));
}

// ======================================================================
// AC2 - Draft round-trip giữ '0111' dạng chuỗi (số 0 đầu không mất)
// ======================================================================
{
  const store = industryStore([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]);
  store.loops.ds_nganh[0].la_nganh_chinh = 'X';
  const draft = {
    v: 2, caseId: 'thanh_lap_tnhh_1tv', checkedForms: ['PLI_M02'],
    activeDocId: 'PLI_M02', autoSum: false, viewState: {}, savedAt: null,
    store: JSON.parse(JSON.stringify(store))
  };
  const roundTrip = FD.migrateDraft(JSON.parse(JSON.stringify(draft)));
  const r0 = roundTrip.store.loops.ds_nganh[0];
  check("AC2: draft round-trip giu ma_nganh '0111' KIEU CHUOI (khong mat so 0 dau)",
    typeof r0.ma_nganh === 'string' && r0.ma_nganh === '0111',
    typeof r0.ma_nganh + ':' + JSON.stringify(r0.ma_nganh));

  // Export payload DOCX (buildExportData -> GridCtl.exportLoops) cũng là chuỗi
  const payload = G.exportLoops(roundTrip.store);
  check("AC2: payload export van giu '0111' chuoi + bo _row_id",
    payload.ds_nganh.length === 1 &&
      typeof payload.ds_nganh[0].ma_nganh === 'string' &&
      payload.ds_nganh[0].ma_nganh === '0111' &&
      !('_row_id' in payload.ds_nganh[0]),
    JSON.stringify(payload.ds_nganh));

  // Renderer đọc từ store round-trip: ô nhập hiện lại '0111'
  const html = renderDoc(M02, roundTrip.store);
  check('AC2: reload xong UI hien lai 0111 (khong bi bien thanh 111)',
    cellValueAt(loopTable(html, 'ds_nganh'), 0, 'ma_nganh') === '0111',
    cellValueAt(loopTable(html, 'ds_nganh'), 0, 'ma_nganh'));
}

// ======================================================================
// AC3 - Tìm 'trong lua' -> 0111 đầu; Enter chọn -> mã+tên set cùng row
// ======================================================================
{
  const hits = R.searchVsic(VSIC, 'trong lua', 12);
  check("AC3: searchVsic('trong lua') tra 0111 o vi tri DAU",
    hits.length > 0 && String(hits[0].ma) === '0111',
    JSON.stringify(hits.slice(0, 3).map(x => x.ma)));

  // Mô phỏng popup: state.vsicItems = hits; ArrowDown không di; Enter chọn
  const store = industryStore([{}]);           // dòng đang nhập trống mã
  const idx = 0;
  const item = hits[idx];                      // Enter -> state.vsicItems[idx]
  flowPickVsicItem(store.loops.ds_nganh[idx], item);
  const row = store.loops.ds_nganh[idx];
  check('AC3: ENTER chon goi y -> CA ma + ten duoc set cung mot dong',
    row.ma_nganh === '0111' && row.ten_nganh === 'Trồng lúa',
    JSON.stringify(row));
}

// ======================================================================
// AC4 - Mã '999999' invalid -> VSIC_INVALID blocking; ten KHÔNG tự điền
// ======================================================================
{
  const store = industryStore([{}]);
  const row = store.loops.ds_nganh[0];
  const res = flowTypeMaNganh(row, '999999');          // trước đó chưa có tên
  check("AC4: '999999' -> vsicResolve INVALID", res.st === 'invalid', res.st);

  // Người dùng lỡ có tên cũ từ mã khác -> đổi mã sai phải XÓA tên, không giả
  const store2 = industryStore([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]);
  const row2 = store2.loops.ds_nganh[0];
  flowTypeMaNganh(row2, '999999');
  check('AC4: ma sai KHONG tu dien/giu ten gia (ten ve rong)',
    row2.ten_nganh === '' && row2.ma_nganh === '999999',
    JSON.stringify(row2));

  const errs = errsDoc('PLI_M02', M02.blocks, store2);
  const inv = blockingOf(errs, 'VSIC_INVALID');
  check('AC4: validateDocument(PLI_M02 prod) co VSIC_INVALID blocking theo row_id',
    inv.length === 1 &&
      inv[0].key.indexOf('loop:ds_nganh:' + row2._row_id + ':ma_nganh') === 0,
    JSON.stringify(inv));

  const dossier = FD.validateDossier(
    [{ id: 'PLI_M02', blocks: M02.blocks }], store2, CTX());
  const nBlocking = dossier.filter(e => e.severity === 'blocking').length;
  check('AC4: validateDossier co blocking > 0 (chan export)', nBlocking > 0,
    'blocking=' + nBlocking);
}

// ======================================================================
// AC5 - Đổi '0111' -> '0112': ten cập nhật, KHÔNG giữ 'Trồng lúa'
// ======================================================================
{
  const store = industryStore([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]);
  const row = store.loops.ds_nganh[0];
  const res = flowTypeMaNganh(row, '0112');
  check('AC5: doi ma hop le khac -> ten cap nhat NGAY sang ten moi',
    res.st === 'exact' &&
      row.ma_nganh === '0112' &&
      row.ten_nganh === 'Trồng ngô và cây lương thực có hạt khác' &&
      row.ten_nganh !== 'Trồng lúa',
    JSON.stringify(row));

  // Lưới an toàn kép: ngay khi store bị lệch tên (draft cũ), validator TỰ SỬA
  const stale = industryStore([{ ma_nganh: '0112', ten_nganh: 'Trồng lúa' }]);
  const errs = errsDoc('PLII_M01', M01.blocks, stale);
  check('AC5: validator tu sua ten lech theo danh muc (khong bao loi ten)',
    stale.loops.ds_nganh[0].ten_nganh === 'Trồng ngô và cây lương thực có hạt khác' &&
      !errs.some(e => e.code === 'VSIC_INVALID' || e.code === 'NAME_MISMATCH'),
    stale.loops.ds_nganh[0].ten_nganh);
}

// ======================================================================
// AC6 - addRow x3 -> STT 1/2/3; deleteRows dòng giữa -> STT còn 1/2
// ======================================================================
{
  const store = R.newStore();
  const added = [];
  for (let i = 0; i < 3; i++) added.push(G.addRow(store, 'ds_nganh', null).id);
  const codes = ['0111', '0124', '6201'];
  codes.forEach((c, i) => {
    store.loops.ds_nganh[i].ma_nganh = c;
    store.loops.ds_nganh[i].ten_nganh =
      (G.vsicResolve(VSIC, c).item || {}).ten || '';
  });

  const html = renderDoc(M02, store);
  const tbl = loopTable(html, 'ds_nganh');
  const stts = sttsOf(tbl);

  // Production PLI_M02 giữ 4 blankRows để in nên tổng hàng hiển thị
  // max(3, 4): 3 dòng dữ liệu đầu phải mang STT 1/2/3, dãy STT liên tục từ 1.
  check('AC6: them 3 dong -> 3 dong dau co STT 1/2/3 (regex td.stt)',
    stts.length >= 3 && stts.slice(0, 3).join(',') === '1,2,3', stts.join(','));
  check('AC6: day STT lien tuc bat dau tu 1 (tu danh lai theo thu tu)',
    stts.length > 0 &&
      stts.every((v, i) => Number(v) === i + 1), stts.join(','));
  check('AC6: thu tu ma tren UI dung nhu thu tu mang',
    [0, 1, 2].every(i => cellValueAt(tbl, i, 'ma_nganh') === codes[i]),
    [0, 1, 2].map(i => cellValueAt(tbl, i, 'ma_nganh')).join(','));

  // Xóa dòng GIỮA (dòng 2 - mã 0124)
  const midId = store.loops.ds_nganh[1]._row_id;
  const removed = G.deleteRows(store, 'ds_nganh', [midId]);
  const html2 = renderDoc(M02, store);
  const tbl2 = loopTable(html2, 'ds_nganh');
  const stts2 = sttsOf(tbl2);
  check('AC6: xoa dong giua -> STT con 1/2 dung thu tu cho 2 dong du lieu',
    removed === 1 && stts2.length >= 2 &&
      stts2.slice(0, 2).join(',') === '1,2' &&
      stts2.every((v, i) => Number(v) === i + 1),
    'removed=' + removed + ' stts=' + stts2.join(','));
  check('AC6: du lieu sau xoa giu dung thu tu con lai (0111, 6201)',
    cellValueAt(tbl2, 0, 'ma_nganh') === '0111' &&
      cellValueAt(tbl2, 1, 'ma_nganh') === '6201',
    cellValueAt(tbl2, 0, 'ma_nganh') + ',' + cellValueAt(tbl2, 1, 'ma_nganh'));
}

// ======================================================================
// AC7 - Xóa dòng có dữ liệu: confirm cancel -> dữ liệu nguyên vẹn
// ======================================================================
{
  const gm = FD.getGridMeta('ds_nganh');
  check('AC7: meta ds_nganh bat confirmDeleteNonEmpty + cho phep xoa',
    !!gm && gm.confirmDeleteNonEmpty === true && gm.allowDelete !== false,
    JSON.stringify({ c: gm && gm.confirmDeleteNonEmpty, d: gm && gm.allowDelete }));

  const store = industryStore([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]);
  const before = JSON.stringify(store.loops.ds_nganh);
  let askedWith = null;
  const verdict = uiDeleteRowsPure(store, 'ds_nganh',
    store.loops.ds_nganh[0]._row_id,
    (row, ix) => { askedWith = { ma: row.ma_nganh, ten: row.ten_nganh, ix }; return false; });
  check('AC7: cancel confirm -> KHONG splice, du lieu con nguyen ven',
    verdict === 'cancelled' &&
      JSON.stringify(store.loops.ds_nganh) === before,
    verdict + ' vs ' + before);
  check('AC7: confirm hoi DUNG dong co du lieu (du ma + ten de bao nguoi dung)',
    !!askedWith && askedWith.ma === '0111' && askedWith.ten === 'Trồng lúa',
    JSON.stringify(askedWith));

  const verdict2 = uiDeleteRowsPure(store, 'ds_nganh',
    store.loops.ds_nganh[0]._rowId || store.loops.ds_nganh[0]._row_id,
    () => true);
  check('AC7: xac nhan OK -> moi xoa that (1 dong)',
    verdict2 === 'deleted' && store.loops.ds_nganh.length === 0, verdict2);

  // Dòng TRỐNG xóa không cần confirm (không hỏi)
  const store3 = industryStore([{}]);
  let askedEmpty = false;
  const verdict3 = uiDeleteRowsPure(store3, 'ds_nganh',
    store3.loops.ds_nganh[0]._row_id, () => { askedEmpty = true; return false; });
  check('AC7: dong trong xoa thang, khong bat confirm',
    verdict3 === 'deleted' && !askedEmpty, verdict3);
}

// ======================================================================
// AC8 - Trùng mã 2 dòng -> DUPLICATE_INDUSTRY blocking, trỏ đủ cả hai row_id
// ======================================================================
{
  const store = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
  ]);
  const errs = errsDoc('PLI_M02', M02.blocks, store);
  const dupErrs = blockingOf(errs, 'DUPLICATE_INDUSTRY');
  const dupKeys = new Set(dupErrs.map(e => e.key));
  const id0 = store.loops.ds_nganh[0]._row_id;
  const id1 = store.loops.ds_nganh[1]._row_id;
  check('AC8: trung ma -> DUPLICATE_INDUSTRY blocking tro DU ca hai row_id',
    dupErrs.length >= 2 &&
      dupKeys.has('loop:ds_nganh:' + id0 + ':ma_nganh') &&
      dupKeys.has('loop:ds_nganh:' + id1 + ':ma_nganh'),
    JSON.stringify([...dupKeys]));

  const dossier = FD.validateDossier(
    [{ id: 'PLI_M02', blocks: M02.blocks }, { id: 'PLII_M01', blocks: M01.blocks }],
    store, CTX());
  const nBlocking = dossier.filter(e => e.severity === 'blocking').length;
  check('AC8: validateDossier ho so nhieu mau van blocking > 0', nBlocking > 0,
    'blocking=' + nBlocking);
}

// ======================================================================
// AC9 - setExclusiveRadio dòng 2 la_nganh_chinh -> 'X', các dòng khác ''
// ======================================================================
{
  const store = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' },
    { ma_nganh: '6201', ten_nganh: 'Hoạt động lập trình máy vi tính' }
  ]);
  const id2 = store.loops.ds_nganh[1]._row_id;         // dòng 2
  G.setExclusiveRadio(store, 'ds_nganh', id2, 'la_nganh_chinh', true);
  const marks = store.loops.ds_nganh.map(r => r.la_nganh_chinh);
  check("AC9: chon nganh chinh dong 2 -> dong do 'X', moi dong khac ''",
    marks[1] === 'X' && marks[0] === '' && marks[2] === '',
    JSON.stringify(marks));

  // Radio trên renderer: đúng 1 ô checked, thuộc dòng 2
  const ngBlankRows = Number((findLoopBlock(M02, 'ds_nganh') || {}).blankRows || 0);
  const html = renderDoc(M02, store);
  const tbl = loopTable(html, 'ds_nganh');
  const radios = tbl.match(/<input type="radio"[^>]*>/g) || [];
  const checkedIdx = [];
  radios.forEach(r => {
    const m = r.match(/data-row="(\d+)"/);
    if (/checked/.test(r) && m) checkedIdx.push(Number(m[1]));
  });
  check('AC9: renderer chi dung 1 radio checked va la dong da chon',
    radios.length === Math.max(3, Number(ngBlankRows), 1) &&
      checkedIdx.length === 1 && checkedIdx[0] === 1,
    'radios=' + radios.length + ' checked@' + checkedIdx.join(','));
}

// ======================================================================
// AC10 - Xóa dòng đang là ngành chính -> PRIMARY_INDUSTRY_REQUIRED blocking
// ======================================================================
{
  const store = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
  ]);
  const primaryId = store.loops.ds_nganh[0]._row_id;
  const removed = G.deleteRows(store, 'ds_nganh', [primaryId]);
  const leftFilled = store.loops.ds_nganh.filter(r =>
    String(r.ma_nganh || '').trim() !== '').length;
  check('AC10: thao tac xoa duoc phep, bang con >=1 dong du lieu',
    removed === 1 && leftFilled >= 1,
    'removed=' + removed + ' leftFilled=' + leftFilled);

  const errs = errsDoc('PLI_M02', M02.blocks, store);
  const pir = blockingOf(errs, 'PRIMARY_INDUSTRY_REQUIRED');
  check('AC10: xoa nganh chinh -> PRIMARY_INDUSTRY_REQUIRED blocking (phai chon lai truoc export)',
    pir.length === 1, JSON.stringify(pir));

  // Chọn lại ngành chính -> hết lỗi
  G.setExclusiveRadio(store, 'ds_nganh',
    store.loops.ds_nganh[0]._row_id, 'la_nganh_chinh', true);
  const errs2 = errsDoc('PLI_M02', M02.blocks, store);
  check('AC10: chon lai nganh chinh -> het PRIMARY_INDUSTRY_REQUIRED',
    blockingOf(errs2, 'PRIMARY_INDUSTRY_REQUIRED').length === 0);
}

// ======================================================================
// AC11 - Cùng store.loops.ds_nganh render qua PLI_M02 VÀ PLII_M01
// ======================================================================
{
  const rows = [
    { ma_nganh: '6201', ten_nganh: 'Hoạt động lập trình máy vi tính', la_nganh_chinh: 'X' },
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
  ];
  const shared = { values: {}, checks: {}, loops: { ds_nganh: rows.map(r => Object.assign({ _row_id: G.nextId() }, r)) } };

  const h02 = renderDoc(M02, shared);
  const h01 = renderDoc(M01, shared);
  const t02 = loopTable(h02, 'ds_nganh');
  const t01 = loopTable(h01, 'ds_nganh');
  const rows02 = bodyRows(t02);
  const rows01 = bodyRows(t01);
  const codes02 = rows.map((_, i) => cellValueAt(t02, i, 'ma_nganh'));
  const codes01 = rows.map((_, i) => cellValueAt(t01, i, 'ma_nganh'));

  check('AC11: hai mau cung hien CUNG SO DONG cho cung mot store',
    rows02.length === rows01.length && rows02.length >= rows.length,
    'M02=' + rows02.length + ' M01=' + rows01.length);
  check('AC11: cung THU TU ma o ca hai mau (dong bo lien mau)',
    codes02.join(',') === codes01.join(',') &&
      codes02.join(',') === '6201,0111,0112',
    'M02=[' + codes02 + '] M01=[' + codes01 + ']');
  check('AC11: STT hai mau giong nhau',
    sttsOf(t02).slice(0, rows.length).join(',') ===
      sttsOf(t01).slice(0, rows.length).join(','),
    sttsOf(t02).join(',') + ' vs ' + sttsOf(t01).join(','));

  // Đổi store (thêm/xóa) rồi render lại -> cả hai mẫu thấy cùng thay đổi
  G.deleteRows(shared, 'ds_nganh', [shared.loops.ds_nganh[0]._row_id]);
  G.addRow(shared, 'ds_nganh', null);
  shared.loops.ds_nganh[shared.loops.ds_nganh.length - 1].ma_nganh = '4712';
  const codesAfter = shared.loops.ds_nganh.map(r => r.ma_nganh);
  const again02 = [0, 1, 2].map(i => cellValueAt(loopTable(renderDoc(M02, shared), 'ds_nganh'), i, 'ma_nganh'));
  const again01 = [0, 1, 2].map(i => cellValueAt(loopTable(renderDoc(M01, shared), 'ds_nganh'), i, 'ma_nganh'));
  check('AC11: sau thay doi store, ca hai mau van cung danh sach + thu tu',
    again02.join(',') === again01.join(',') &&
      again01.join(',') === codesAfter.join(','),
    'M02=[' + again02 + '] M01=[' + again01 + '] want=[' + codesAfter + ']');
}

// ======================================================================
// AC12 - migrateDraft v2/v1 round-trip không mất rows/thứ tự/_row_id/field
// ======================================================================
{
  // (a) v2 với 2 dòng đầy đủ chi_tiet + la_nganh_chinh
  const store = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', chi_tiet: 'Vu Dong Trieu', la_nganh_chinh: 'X' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác', chi_tiet: '', la_nganh_chinh: '' }
  ]);
  const snapBefore = JSON.stringify(store.loops.ds_nganh);
  const draft = {
    v: 2, caseId: 'x', checkedForms: ['PLI_M02'], activeDocId: 'PLI_M02',
    autoSum: false, viewState: {}, savedAt: '2026-08-25T00:00:00Z',
    store: JSON.parse(JSON.stringify(store))
  };
  const mig = FD.migrateDraft(JSON.parse(JSON.stringify(draft)));
  check('AC12: draft v2 round-trip GIU NGUYEN rows/thu tu/_row_id/chi_tiet/nganh chinh',
    JSON.stringify(mig.store.loops.ds_nganh) === snapBefore,
    mig.store.loops.ds_nganh.map(r => r._row_id + ':' + r.ma_nganh).join(' | ') +
      '\nBEFORE=' + snapBefore);

  // (b) v1 cũ dùng ds_nganh_kinh_doanh -> đổi thành ds_nganh không mất数据
  const draftV1 = {
    v: 1, caseId: 'ho_kinh_doanh', checkedForms: [], autoSum: false,
    store: {
      values: { ghi_chu: 'giu' }, checks: {},
      loops: {
        ds_nganh_kinh_doanh: [
          { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy vi tính', chi_tiet: 'kem lap dat', la_nganh_chinh: 'X' },
          { ma_nganh: '0111', ten_nganh: 'Trồng lúa', chi_tiet: '', la_nganh_chinh: '' }
        ]
      }
    }
  };
  const up = FD.migrateDraft(draftV1);
  const migrated = (up.store.loops.ds_nganh || []);
  check('AC12: migrate v1 doi ds_nganh_kinh_doanh -> ds_nganh, du 2 dong dung thu tu + du lieu',
    Number(up.v) === 2 && migrated.length === 2 &&
      migrated[0].ma_nganh === '4711' && migrated[0].ten_nganh === 'Bán lẻ máy vi tính' &&
      migrated[0].chi_tiet === 'kem lap dat' && migrated[0].la_nganh_chinh === 'X' &&
      migrated[1].ma_nganh === '0111' &&
      !Object.prototype.hasOwnProperty.call(up.store.loops, 'ds_nganh_kinh_doanh'),
    JSON.stringify(migrated));
  check('AC12: migrate v1 gan _row_id on dinh cho row cu (draft cu chua co)',
    migrated.every(r => /^r\d+_[a-z0-9]+$/.test(String(r._row_id))),
    migrated.map(r => r._row_id).join(','));
}

// ======================================================================
// AC13 - PYTHON SIDE: DOCX PLI_M02 (script sẵn có) + PLII_M01 (script mới)
// ======================================================================
{
  const r1 = runPy(path.join('tools', 'test_pli_m02_industry.py'));
  check('AC13: python tools/test_pli_m02_industry.py exit 0 (DOCX PLI_M02 3 dong dung o + STT 1/2/3)',
    r1.code === 0 && /\d PASS \/ 0 FAIL/.test(r1.out),
    'exit=' + r1.code + '\n' + r1.out.slice(-600));

  const r2 = runPy(path.join('tools', 'test_acceptance_docx.py'));
  check('AC13: python tools/test_acceptance_docx.py exit 0 (DOCX PLII_M01 ds_nganh dung dong/cot, khong sot token)',
    r2.code === 0 && /\d PASS \/ 0 FAIL/.test(r2.out),
    'exit=' + r2.code + '\n' + r2.out.slice(-600));
}

// ======================================================================
// AC14 - mọi check dùng dữ liệu production (assert thêm về fixtures thật)
// ======================================================================
{
  const ng02 = findLoopBlock(M02, 'ds_nganh');
  const cols02 = (ng02.cols || []).map(c => c.col);
  check('AC14: PLI_M02 loop ds_nganh la schema production (cols zero-based, cot 0 STT khong tag, blankRows de in)',
    !!ng02 &&
      ['ma_nganh', 'ten_nganh', 'chi_tiet', 'la_nganh_chinh'].every(t =>
        (ng02.cols || []).some(c => c.tag === t)) &&
      !(ng02.cols || []).some(c => Number(c.col) === 0) &&
      Math.min.apply(null, cols02) === 1 &&
      Number(ng02.blankRows) >= 1,
    'cols=' + JSON.stringify(ng02.cols) + ' blankRows=' + ng02.blankRows);
  check('AC14: danh muc VSIC that co du 0111/0112/6201 (du lieu tra cuu production)',
    ['0111', '0112', '6201'].every(ma =>
      VSIC.some(x => String(x.ma) === ma)),
    'vsic=' + VSIC.length + ' entries');
  check('AC14: GRID_META.ds_nganh khoi production metadata (required + requirePrimary + autoName)',
    (() => {
      const g = FD.getGridMeta('ds_nganh');
      return g.required === true && g.requirePrimary === true &&
        g.autoName && g.autoName.codeTag === 'ma_nganh' &&
        g.autoName.nameTag === 'ten_nganh';
    })());
}

// ======================================================================
// EXTRA - MIN_ROWS vi phạm: chặn export nhưng add/delete vẫn thao tác được
// ======================================================================
{
  // ds_thanh_vien (production PLI_M06) yêu cầu tối thiểu 2 thành viên
  const store = R.newStore();
  G.addRow(store, 'ds_thanh_vien', null);
  store.loops.ds_thanh_vien[0].ho_ten = 'NGUYEN VAN A';
  store.loops.ds_thanh_vien[0].von_dong_gop = '100.000.000';
  store.loops.ds_thanh_vien[0].ty_le_von = '100';

  const errs = errsDoc('PLI_M06', M06.blocks, store);
  const mr = blockingOf(errs, 'MIN_ROWS');
  check('EXTRA: MIN_ROWS vi pham (1/2 thanh vien) -> loi BLOCKING chan export',
    mr.length === 1, JSON.stringify(errs.map(e => e.code)));

  // Nhưng thao tác chỉnh sửa KHÔNG bị khóa/không exception
  let opOk = true;
  try {
    const added = G.addRow(store, 'ds_thanh_vien', null);       // thêm được
    const removed = G.deleteRows(store, 'ds_thanh_vien', [
      added.id, store.loops.ds_thanh_vien[0]._row_id]);          // xóa dưới min vẫn được
    if (!(added && added.id && removed === 2 &&
          store.loops.ds_thanh_vien.length === 0)) opOk = false;
    // UI vẫn render bình thường khi bảng rỗng (>=1 dòng trống)
    const tbl = loopTable(renderDoc(M06, store), 'ds_thanh_vien');
    if (bodyRows(tbl).length < 1) opOk = false;
    // ds_nganh cũng vậy: xóa hết vẫn thao tác tiếp được
    const s2 = industryStore([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]);
    G.deleteRows(s2, 'ds_nganh', [s2.loops.ds_nganh[0]._row_id]);
    G.addRow(s2, 'ds_nganh', null);
    if (s2.loops.ds_nganh.length !== 1) opOk = false;
  } catch (e) {
    opOk = false;
  }
  check('EXTRA: vi pham minRows KHONG khoa UI - addRow/deleteRows/render van chay, khong exception',
    opOk);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Acceptance (PLAN.md 14 muc + EXTRA): %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
