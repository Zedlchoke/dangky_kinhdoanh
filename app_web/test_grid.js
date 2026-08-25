/* test_grid.js - kiểm thử PHASE 1B+2+4+5 (PLAN.md): editable-grid generic,
 * canonical ds_nganh + VSIC flow, chạy trên BLOCKS PRODUCTION (app/data/blocks,
 * chỉ đọc) - không phụ thuộc mock.
 *
 * Chạy:  node app_web/test_grid.js
 *
 * Phủ:
 *  A. GRID_META phủ đủ tag của 8 bảng lặp production.
 *  B. Contract chung add/delete/reorder/duplicate/clear cho ds_nganh,
 *     ds_thanh_vien, ds_co_dong_sang_lap, ds_tv_ho_gia_dinh:
 *     STT đánh lại từ thứ tự mảng, _row_id ổn định sau moveRow, duplicate bỏ
 *     field định danh, export strip _row_id, lỗi theo row_id vẫn đúng dòng
 *     sau reorder, clear vẫn còn >=1 dòng trống trên UI.
 *  C. Canonical ds_nganh: row contract {ma_nganh, ten_nganh, chi_tiet,
 *     la_nganh_chinh}; radio một-lựa-chọn; blocking errors INDUSTRY_REQUIRED,
 *     ROW_INCOMPLETE, VSIC_INVALID, DUPLICATE_INDUSTRY, tự sửa tên-lệch,
 *     PRIMARY_INDUSTRY_REQUIRED; migration ds_nganh_kinh_doanh -> ds_nganh.
 *  D. VSIC flow thuần: mã rỗng/hợp lệ/1-3 số/sai; đổi mã -> tên cập nhật;
 *     tìm ngược bằng tên không dấu.
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

// ------------------------------------------------------------ html helpers

function findLoopBlock(doc, loopName) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === loopName)[0] || null;
}

/* render đúng cách app.js: fieldMeta + gridMeta */
function renderDoc(doc, store) {
  return R.renderBlocks(doc, store || R.newStore(),
    { docId: doc.id, fieldMeta: FD.FIELD_META, gridMeta: FD.GRID_META });
}

function loopTable(html, loop) {
  const m = html.match(new RegExp('<table[^>]*data-loop="' + loop + '"[\\s\\S]*?</table>'));
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

function tdsOf(rowInner) {
  const out = [];
  const re = /<td([^>]*)>([\s\S]*?)<\/td>/g;
  let m;
  while ((m = re.exec(rowInner)) !== null) out.push({ attrs: m[1], inner: m[2] });
  return out;
}

function attrVal(attrs, name) {
  const m = String(attrs).match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1] : null;
}

function sttsOf(tableHtml) {
  const out = [];
  const re = /<td class="stt">(\d+)<\/td>/g;
  let m;
  while ((m = re.exec(tableHtml)) !== null) out.push(m[1]);
  return out;
}

function unesc(s) {
  return String(s).replace(/&amp;/g, '&').replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}

/* Mô phỏng findErrorField (app.js) trên HTML: key loop:<loop>:<row_id>:<tag>
 * resolve qua [data-row-id] rồi mới tới [data-tag]. */
function resolveErrorCell(html, key) {
  const p = key.split(':');               // loop | name | rowid? | tag?
  const tbl = loopTable(html, p[1]);
  if (!tbl) return null;
  let tr = null;
  if (p.length >= 3) {
    const rows = bodyRows(tbl);
    tr = rows.filter(r => attrVal(r.attrs, 'data-row-id') === p[2])[0] || null;
    if (!tr) return null;
  }
  if (p.length >= 4 && tr) {
    const td = tdsOf(tr.inner).filter(td => td.inner.indexOf('data-tag="' + p[3] + '"') >= 0)[0];
    return td ? { dataKey: (td.inner.match(/data-key="([^"]+)"/) || [])[1] || null } : null;
  }
  if (tr) {
    const k = (tr.inner.match(/data-key="([^"]+)"/) || [])[1];
    return { dataKey: k || null };
  }
  return null;
}

function errsOf(docId, blocks, store, vsicList) {
  return FD.validateDocument(docId, blocks, store, { vsicList: vsicList || null });
}

// --------------------------------------------------- A. GRID_META coverage

const PROD_LOOPS = [
  { doc: 'PLI_M06', loop: 'ds_thanh_vien' },
  { doc: 'PLI_M07', loop: 'ds_co_dong_sang_lap' },
  { doc: 'PLI_M08', loop: 'ds_co_dong_nn' },
  { doc: 'PLI_M09', loop: 'ds_thanh_vien' },
  { doc: 'PLI_M10', loop: 'ds_cshhl' },
  { doc: 'PLI_M11', loop: 'ds_cshhl' },
  { doc: 'PLII_M01', loop: 'ds_nganh' },
  { doc: 'PLII_M01', loop: 'ds_tv_ho_gia_dinh' }
];

PROD_LOOPS.forEach(function (spec) {
  const b = findLoopBlock(loadProd(spec.doc), spec.loop);
  const metaTags = ((FD.getGridMeta(spec.loop) || {}).columns || []).map(c => c.tag);
  const missing = (b ? (b.cols || []) : []).filter(c => metaTags.indexOf(c.tag) < 0);
  check('GRID_META.' + spec.loop + ' phu tag cua ' + spec.doc +
        (missing.length ? ' (thieu: ' + missing.map(c => c.tag) + ')' : ''),
    !!b && missing.length === 0);
});

check('GRID_META.ds_nganh co dung row contract 4 cot',
  (() => {
    const tags = FD.GRID_META.ds_nganh.columns.map(c => c.tag);
    return ['ma_nganh', 'ten_nganh', 'chi_tiet', 'la_nganh_chinh']
      .every(t => tags.indexOf(t) >= 0);
  })());
check('GRID_META.ds_nganh: ten_nganh readonly + ma_nganh required + requirePrimary',
  (() => {
    const g = FD.GRID_META.ds_nganh;
    const col = t => g.columns.filter(c => c.tag === t)[0];
    return col('ten_nganh').type === 'readonly' &&
      col('ma_nganh').required === true &&
      g.requirePrimary === true && g.required === true && g.minRows >= 1;
  })());

// ------------------------------------- B. contract chung tren blocks that

function runGridContract(docId, loopName, fillRow, identityTag) {
  const doc = loadProd(docId);
  const label = docId + '/' + loopName;

  // add: cuoi + giua (afterRowId)
  let store = R.newStore();
  const a1 = G.addRow(store, loopName, null);
  const a2 = G.addRow(store, loopName, null);
  const a3 = G.addRow(store, loopName, a1.id);       // chen sau dong 1
  check(label + ': addRow giua -> thu tu [a1,a3,a2]',
    store.loops[loopName].map(r => r._row_id).join(',') ===
      [a1.id, a3.id, a2.id].join(','));

  // _row_id duy nhat + dung dinh dang r<seq>_<suffix>
  const ids = store.loops[loopName].map(r => r._row_id);
  check(label + ': _row_id duy nhat, dung dinh dang',
    new Set(ids).size === 3 && ids.every(id => /^r\d+_[a-z0-9]+$/.test(id)));

  // du lieu gan voi _row_id: sau moveRow gia tri van di theo row
  const rowsPre = store.loops[loopName];             // [a1, a3, a2]
  fillRow(rowsPre[0]);                               // a1 co du lieu
  fillRow(rowsPre[2]);                               // a2 co du lieu
  const snapA2 = JSON.stringify(rowsPre[2]);
  const moved = G.moveRow(store, loopName, a2.id, -1); // a2 len tren a3
  check(label + ': moveRow len tren thanh cong (vi tri moi = 1)', moved === 1,
    'got ' + moved);
  const afterMove = store.loops[loopName];           // [a1, a2, a3]
  check(label + ': thu tu moi [a1,a2,a3]',
    afterMove.map(r => r._row_id).join(',') === [a1.id, a2.id, a3.id].join(','));
  check(label + ': _row_id on dinh sau reorder, du lieu di theo row',
    afterMove[1]._row_id === a2.id && JSON.stringify(afterMove[1]) === snapA2);

  // STT luon tu thu tu mang (render lai sau thao tac)
  const html = renderDoc(doc, store);
  const stts = sttsOf(loopTable(html, loopName));
  const nShow = Math.max(afterMove.length,
    findLoopBlock(doc, loopName).blankRows || 0);
  check(label + ': STT danh lai 1..' + nShow + ' theo thu tu hien tai',
    stts.join(',') === Array.from({ length: nShow }, (_, i) => i + 1).join(','),
    stts.join(','));

  // error theo row_id van dung dong sau khi doi thu tu
  const errStore = R.newStore();
  G.addRow(errStore, loopName, null);
  G.addRow(errStore, loopName, null);
  fillRow(errStore.loops[loopName][0]);
  const gmMeta = FD.getGridMeta(loopName);
  const moneyTag = ((gmMeta.columns || []).filter(c => c.type === 'money')[0] || {}).tag;
  if (moneyTag) errStore.loops[loopName][0][moneyTag] = 'chuwa nhap';   // MONEY
  else {
    // bảng text-only: làm rỗng 1 cột required đang có dữ liệu -> ROW_INCOMPLETE
    const reqTag = ((gmMeta.columns || []).filter(c => c.required)[0] || {}).tag;
    errStore.loops[loopName][0][reqTag] = '';
  }
  const errs = errsOf(docId, doc.blocks, errStore, VSIC);
  const badId = errStore.loops[loopName][0]._row_id;
  const cellErr = errs.find(e =>
    e.severity === 'blocking' && e.key.indexOf('loop:' + loopName + ':' + badId + ':') === 0);
  check(label + ': loi row-level co key theo _row_id (' +
      (cellErr ? cellErr.code : 'khong co') + ')', !!cellErr);
  const errTag = cellErr ? cellErr.key.split(':')[3] : null;
  G.moveRow(errStore, loopName, badId, -1);           // doi vi tri dong loi
  const html2 = renderDoc(doc, errStore);
  const idxNow = G.findRowIndex(errStore.loops[loopName], badId);
  const resolved = cellErr && resolveErrorCell(html2, cellErr.key);
  check(label + ': loi sau reorder van tro dung dong (data-row-id -> index moi)',
    !!resolved && resolved.dataKey ===
      'loop:' + loopName + ':' + idxNow + ':' + errTag,
    JSON.stringify(resolved) + ' idx=' + idxNow);

  // duplicate: chen ngay sau nguon + bo field dinh danh + id moi
  const dupSrc = afterMove[1]._row_id;
  const beforeDupIds = afterMove.map(r => r._row_id);
  const dres = G.duplicateRow(store, loopName, dupSrc);
  const srcRow = store.loops[loopName][beforeDupIds.indexOf(dupSrc)];
  const cloneRow = store.loops[loopName][dres.index];
  check(label + ': duplicateRow chen ngay sau dong nguon',
    dres.index === beforeDupIds.indexOf(dupSrc) + 1);
  check(label + ': clone bo field dinh danh (' + identityTag + ') va co _row_id moi',
    !(identityTag in cloneRow) && cloneRow._row_id && cloneRow._row_id !== dupSrc);
  check(label + ': clone giu cac field khac cua nguon',
    Object.keys(srcRow).every(k =>
      k === identityTag || k === '_row_id' ||
      String(cloneRow[k]) === String(srcRow[k])));

  // deleteRows nhieu dong 1 lan goi (id khong ton tai duoc bo qua)
  const delTargets = [afterMove[0]._row_id, dres.id, 'r999_khongtonnai'];
  const delCount = G.deleteRows(store, loopName, delTargets);
  check(label + ': deleteRows xoa dung so dong, bo qua id la',
    delCount === 2 &&
      store.loops[loopName].length === beforeDupIds.length + 1 - 2,
    'removed=' + delCount + ' left=' + store.loops[loopName].length);

  // clearRows -> rong nhung UI van con it nhat 1 dong trong
  G.clearRows(store, loopName);
  check(label + ': clearRows -> loops rong', store.loops[loopName].length === 0);
  const htmlClear = renderDoc(doc, store);
  const rowsAfterClear = bodyRows(loopTable(htmlClear, loopName));
  check(label + ': sau clear UI van render >=1 dong trong',
    rowsAfterClear.length >= 1 &&
      rowsAfterClear.every(r => !r.inner
        .replace(/<input[^>]*type="(?:radio|checkbox)"[^>]*>/g, '')
        .match(/value="[^"]+"/)), '');
}

runGridContract('PLII_M01', 'ds_nganh',
  function fill(row) {
    row.ma_nganh = '6201';
    row.ten_nganh = 'Lập trình máy vi tính';
  }, 'ma_nganh');

runGridContract('PLI_M06', 'ds_thanh_vien',
  function fill(row) {
    row.ho_ten = 'NGUYEN VAN TEST';
    row.von_dong_gop = '100.000.000';
    row.ty_le_von = '50';
  }, 'so_cccd');

runGridContract('PLI_M07', 'ds_co_dong_sang_lap',
  function fill(row) {
    row.ho_ten = 'TRAN THI TEST';
    row.so_co_phan = '1.000';
  }, 'so_cccd');

runGridContract('PLII_M01', 'ds_tv_ho_gia_dinh',
  function fill(row) {
    row.ho_ten='LE VAN TEST'; row.so_cccd = '012345678901';
  }, 'so_cccd');

// ------------------------------- B2. export strip _row_id + radio X/''

{
  const store = R.newStore();
  G.addRow(store, 'ds_nganh', null);
  G.addRow(store, 'ds_nganh', null);
  store.loops.ds_nganh[0].ma_nganh = '0111';
  store.loops.ds_nganh[0].ten_nganh = 'Trồng lúa';
  store.loops.ds_nganh[0].la_nganh_chinh = 'X';
  store.loops.ds_nganh[1].ma_nganh = '0112';
  store.loops.ds_nganh[1].ten_nganh = 'Trồng ngô và cây lương thực có hạt khác';
  const exported = G.exportLoops(store);
  check('exportLoops: bo _row_id khoi payload',
    exported.ds_nganh.every(r => !('_row_id' in r)) &&
      Object.keys(exported.ds_nganh[0]).every(k => k.charAt(0) !== '_'));
  // Payload DOCX: the {la_nganh_chinh} trong template phải in dấu X (dòng
  // ngành chính) / rỗng (dòng thường) - KHÔNG được là boolean true/false
  // (trước đây in chữ "True" vào ô pháp lý).
  check('exportLoops: la_nganh_chinh dong chinh -> "X", dong thuong -> ""',
    exported.ds_nganh[0].la_nganh_chinh === 'X' &&
      exported.ds_nganh[1].la_nganh_chinh === '',
    JSON.stringify(exported.ds_nganh.map(r => r.la_nganh_chinh)));
  check('exportLoops: KHONG con boolean trong payload la_nganh_chinh',
    exported.ds_nganh.every(r =>
      typeof r.la_nganh_chinh === 'string' &&
        r.la_nganh_chinh !== true && r.la_nganh_chinh !== false));
  // buildExportData đi qua cùng exportLoops -> payload cho Bridge.export
  // cũng là 'X'/'' (kiểm gián tiếp qua chính hàm được gọi duy nhất đó).
}

// ------------------------------------------- B3. draft round-trip _row_id

{
  const store = R.newStore();
  G.addRow(store, 'ds_nganh', null);
  G.addRow(store, 'ds_nganh', null);
  store.loops.ds_nganh[0].ma_nganh = '0111';
  store.loops.ds_nganh[1].ma_nganh = '4711';
  const idsBefore = store.loops.ds_nganh.map(r => r._row_id);
  const draft = JSON.parse(JSON.stringify({
    v: 2, caseId: 'x', checkedForms: [], activeDocId: null, autoSum: false,
    viewState: {}, savedAt: null,
    store: JSON.parse(JSON.stringify(store))
  }));
  const mig = FD.migrateDraft(draft);          // v2: same object + ensure ids
  const idsAfter = mig.store.loops.ds_nganh.map(r => r._row_id);
  check('draft v2 round-trip: giu rows + thu tu + _row_id nguyen ven',
    JSON.stringify(idsBefore) === JSON.stringify(idsAfter));
  check('migrateDraft idempotent: goi lan 2 khong doi _row_id',
    (() => {
      FD.migrateDraft(mig);
      return JSON.stringify(mig.store.loops.ds_nganh.map(r => r._row_id)) ===
        JSON.stringify(idsAfter);
    })());
}

// --------------------------------- C. migration ds_nganh_kinh_doanh -> ds_nganh

{
  const draftV1 = {
    v: 1, caseId: 'ho_kinh_doanh', checkedForms: [], autoSum: false,
    store: {
      values: {}, checks: {},
      loops: {
        ds_nganh_kinh_doanh: [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }],
        nganh_bo_sung: [{ ghi_chu: 'giu nguyen' }],
        nganh_xoa_bo: [{ ma_nganh: '9999' }]
      }
    }
  };
  const up = FD.migrateDraft(draftV1);
  check('migration v1: ds_nganh_kinh_doanh -> ds_nganh, giu nguyen du lieu',
    !!up.store.loops.ds_nganh && up.store.loops.ds_nganh.length === 1 &&
      up.store.loops.ds_nganh[0].ma_nganh === '0111' &&
      up.store.loops.ds_nganh[0].ten_nganh === 'Trồng lúa' &&
      !up.store.loops.ds_nganh_kinh_doanh);
  check('migration v1: KHONG dong vung nganh_bo_sung/nganh_xoa_bo (du lieu con)',
    up.store.loops.nganh_bo_sung[0].ghi_chu === 'giu nguyen' &&
      up.store.loops.nganh_xoa_bo[0].ma_nganh === '9999');
  check('migration v1: row cu thieu _row_id duoc gan luc nap',
    /^r\d+_/.test(up.store.loops.ds_nganh[0]._row_id));

  const draftV2 = {
    v: 2, caseId: 'x', store: {
      values: {}, checks: {},
      loops: { ds_nganh_kinh_doanh: [{ ma_nganh: '4711', ten_nganh: 'Ban le...' }] }
    }
  };
  const up2 = FD.migrateDraft(draftV2);
  check('migration v2: doi ten loop giu du lieu + gan _row_id (same object)',
    up2 === draftV2 && !!up2.store.loops.ds_nganh &&
      up2.store.loops.ds_nganh[0].ma_nganh === '4711' &&
      !!up2.store.loops.ds_nganh[0]._row_id);
}

// ------------------------------------------------- C2. validator ds_nganh

const M01 = loadProd('PLII_M01');

function industryStore(rows) {
  const s = R.newStore();
  s.loops.ds_nganh = rows.map(r => {
    const row = Object.assign({ _row_id: FD.makeRowId() }, r);
    return row;
  });
  return s;
}

{
  // bảng bắt buộc mà 0 dòng dữ liệu
  const e0 = errsOf('PLII_M01', M01.blocks, R.newStore(), VSIC);
  const ind = e0.find(e => e.code === 'INDUSTRY_REQUIRED');
  check('ds_nganh trong -> INDUSTRY_REQUIRED blocking (key bang)',
    !!ind && ind.severity === 'blocking' && ind.key === 'loop:ds_nganh');

  // dòng có một phần dữ liệu nhưng thiếu column required
  const part = industryStore([{ chi_tiet: 'mo ta chung' }]);
  const e1 = errsOf('PLII_M01', M01.blocks, part, VSIC);
  const inc = e1.find(e => e.code === 'ROW_INCOMPLETE');
  check('dong thieu ma/ten -> ROW_INCOMPLETE blocking, key theo row_id + tag',
    !!inc && inc.severity === 'blocking' &&
      inc.key.indexOf('loop:ds_nganh:' + part.loops.ds_nganh[0]._row_id + ':') === 0 &&
      /:(ma_nganh|ten_nganh)$/.test(inc.key),
    inc && inc.key);

  // mã sai -> VSIC_INVALID, KHONG tu che ten
  const bad = industryStore([{ ma_nganh: '9999', ten_nganh: '' }]);
  const e2 = errsOf('PLII_M01', M01.blocks, bad, VSIC);
  check('ma sai -> VSIC_INVALID blocking theo row_id',
    e2.some(e => e.code === 'VSIC_INVALID' && e.severity === 'blocking' &&
      e.key === 'loop:ds_nganh:' + bad.loops.ds_nganh[0]._row_id + ':ma_nganh') &&
      bad.loops.ds_nganh[0].ten_nganh === '');

  // tên-lệch: TỰ SỬA lại theo danh mục trước khi báo lỗi
  const heal = industryStore([{ ma_nganh: '0111', ten_nganh: 'Sai ten nganh' }]);
  const e3 = errsOf('PLII_M01', M01.blocks, heal, VSIC);
  check('ten lech ma hop le -> tu sua ten theo danh muc, khong bao loi ten/VSIC',
    heal.loops.ds_nganh[0].ten_nganh === 'Trồng lúa' &&
      !e3.some(e => e.code === 'NAME_MISMATCH' || e.code === 'VSIC_INVALID'));

  // trùng mã -> DUPLICATE_INDUSTRY blocking trỏ CẢ HAI dòng
  const dup = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
  ]);
  const e4 = errsOf('PLII_M01', M01.blocks, dup, VSIC);
  const dupErrs = e4.filter(e => e.code === 'DUPLICATE_INDUSTRY');
  const dupKeys = new Set(dupErrs.map(e => e.key));
  check('trung ma -> DUPLICATE_INDUSTRY blocking tro CA HAI dong',
    dupErrs.length >= 2 && dupErrs.every(e => e.severity === 'blocking') &&
      dupKeys.has('loop:ds_nganh:' + dup.loops.ds_nganh[0]._row_id + ':ma_nganh') &&
      dupKeys.has('loop:ds_nganh:' + dup.loops.ds_nganh[1]._row_id + ':ma_nganh'));

  // ngành chính: chưa chọn -> PRIMARY_INDUSTRY_REQUIRED; chọn -> hết
  const noPrimary = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
  ]);
  const e5 = errsOf('PLII_M01', M01.blocks, noPrimary, VSIC);
  const pir = e5.find(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED');
  check('chua chon nganh chinh -> PRIMARY_INDUSTRY_REQUIRED blocking',
    !!pir && pir.severity === 'blocking');
  G.setExclusiveRadio(noPrimary, 'ds_nganh',
    noPrimary.loops.ds_nganh[1]._row_id, 'la_nganh_chinh', true);
  check('setExclusiveRadio: dung 1 dong X, cac dong khac rong',
    noPrimary.loops.ds_nganh[0].la_nganh_chinh === '' &&
      noPrimary.loops.ds_nganh[1].la_nganh_chinh === 'X');
  const e6 = errsOf('PLII_M01', M01.blocks, noPrimary, VSIC);
  check('da chon nganh chinh -> het PRIMARY_INDUSTRY_REQUIRED',
    !e6.some(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED'));
  G.setExclusiveRadio(noPrimary, 'ds_nganh',
    noPrimary.loops.ds_nganh[0]._row_id, 'la_nganh_chinh', true);
  check('doi chon nganh chinh: X chuyen sang dong khac (cu tu go)',
    noPrimary.loops.ds_nganh[0].la_nganh_chinh === 'X' &&
      !noPrimary.loops.ds_nganh[1].la_nganh_chinh);

  // hồ sơ M01 sạch hoàn toàn với 2 ngành hợp lệ + đã chọn ngành chính
  const clean = industryStore(noPrimary.loops.ds_nganh.slice());
  clean.values = {};
  const e7 = errsOf('PLII_M01', M01.blocks, clean, VSIC);
  check('M01: 2 nganh hop le + nganh chinh -> 0 loi toan mau',
    e7.length === 0, JSON.stringify(e7));

  // minRows của ds_nganh: 0 dòng là INDUSTRY_REQUIRED (đã test), 1 dòng OK
  const one = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }]);
  const e8 = errsOf('PLII_M01', M01.blocks, one, VSIC);
  check('ds_nganh 1 dong hop le -> khong MIN_ROWS/INDUSTRY_REQUIRED',
    !e8.some(e => e.code === 'MIN_ROWS' || e.code === 'INDUSTRY_REQUIRED'));
}

// MIN_ROWS ds_thanh_vien giữ hành vi cũ (regression)
{
  const M06 = loadProd('PLI_M06');
  const s1 = R.newStore();
  s1.loops.ds_thanh_vien = [
    { ho_ten: 'A', von_dong_gop: '500.000.000', ty_le_von: '100' }];
  const e = errsOf('PLI_M06', M06.blocks, s1, VSIC);
  const mr = e.find(x => x.code === 'MIN_ROWS');
  check('ds_thanh_vien 1 thanh vien -> MIN_ROWS blocking (regression)',
    !!mr && mr.severity === 'blocking');
  check('minRows khong khoa thao tac: deleteRows van chap nhan duoi 2 dong',
    G.deleteRows(s1, 'ds_thanh_vien', [s1.loops.ds_thanh_vien[0]._row_id]) === 1 &&
      s1.loops.ds_thanh_vien.length === 0);
}

// ----------------------------------------------- D. VSIC flow (thuần)

{
  check("vsicResolve('0111') -> exact + ten chinh thuc",
    (() => {
      const r = G.vsicResolve(VSIC, '0111');
      return r.st === 'exact' && r.item.ten === 'Trồng lúa';
    })());
  check("vsicResolve('') -> empty", G.vsicResolve(VSIC, '').st === 'empty');
  // tiền tố chưa đủ mà CHƯA trùng mã cấp 2/3 trong danh mục -> typing
  const partial = ['0', '0112'.slice(0, 3), '0112'.slice(0, 2), '0112'.slice(0, 1)]
    .find(p => p && !VSIC.some(x => String(x.ma) === p));
  if (partial) {
    check("vsicResolve('" + partial + "') -> typing (goi y, CHUA blocking)",
      (() => {
        const r = G.vsicResolve(VSIC, partial);
        return r.st === 'typing' && r.items.length > 0;
      })());
  } else {
    check('vsicResolve: moi tien so deu la ma danh muc -> bo qua case typing', true);
  }
  check("vsicResolve('9999') -> invalid (khong items)",
    G.vsicResolve(VSIC, '9999').st === 'invalid');
  check("vsicResolve('trong lua') -> typing tim nguoc khong dau",
    (() => {
      const r = G.vsicResolve(VSIC, 'trong lua');
      return r.st === 'typing' && r.items[0].ma === '0111';
    })());

  // đổi mã hợp lệ sang mã khác -> tên phải cập nhật (tự điền theo danh mục)
  const s = industryStore([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }]);
  s.loops.ds_nganh[0].ma_nganh = '0112';
  const e = errsOf('PLII_M01', M01.blocks, s, VSIC);
  check('doi 0111 -> 0112: ten cap nhat ngay theo danh muc, khong giu ten cu',
    s.loops.ds_nganh[0].ten_nganh === 'Trồng ngô và cây lương thực có hạt khác' &&
      !e.some(x => x.code === 'VSIC_INVALID' || x.code === 'NAME_MISMATCH'));

  // giữ số 0 đầu: ma lưu dạng chuỗi
  check('ma "0111" luu chuỗi, không mất số 0 đầu',
    typeof s.loops.ds_nganh[0].ma_nganh === 'string' &&
      s.loops.ds_nganh[0].ma_nganh === '0112');
}

// --------------------------------------------- E. renderer + gridMeta

{
  const store = R.newStore();
  G.addRow(store, 'ds_nganh', null);
  G.addRow(store, 'ds_nganh', null);
  store.loops.ds_nganh[0].ma_nganh = '0111';
  store.loops.ds_nganh[0].ten_nganh = 'Trồng lúa';
  store.loops.ds_nganh[0].la_nganh_chinh = 'X';
  store.loops.ds_nganh[1].ma_nganh = '6201';
  store.loops.ds_nganh[1].ten_nganh = 'Lập trình máy vi tính';

  const html = renderDoc(M01, store);
  const tbl = loopTable(html, 'ds_nganh');
  const rows = bodyRows(tbl);
  function btnsDiv(h, loop) {
    const m = h.match(new RegExp(
      '<div class="loop-btns" data-loop="' + loop + '">[\\s\\S]*?</div>'));
    return m ? m[0] : '';
  }
  const btnsNganh = btnsDiv(html, 'ds_nganh');

  check('renderer: moi tr mang data-row-id = _row_id cua store',
    rows.length >= 2 &&
      rows.slice(0, 2).every((r, i) =>
        attrVal(r.attrs, 'data-row-id') === store.loops.ds_nganh[i]._row_id));
  check('renderer: tr van giu data-row-index + data-loop (tuong thich test cu)',
    rows.every((r, i) =>
      attrVal(r.attrs, 'data-row-index') === String(i) &&
        attrVal(r.attrs, 'data-loop') === 'ds_nganh'));

  // radio la_nganh_chinh nam dung o cot "Ngành, nghề kinh doanh chính" (cot 3)
  const cells0 = tdsOf(rows[0].inner);
  check('renderer: radio la_nganh_chinh o cot 3 (duoi tieu de Nganh chinh)',
    /type="radio"/.test(cells0[3].inner) &&
      /name="loop:ds_nganh:la_nganh_chinh"/.test(cells0[3].inner),
    cells0[3].inner.slice(0, 80));
  check('renderer: radio checked dung dong la_nganh_chinh=X, dong kia khong',
    /checked/.test(cells0[3].inner) &&
      !/checked/.test(tdsOf(rows[1].inner)[3].inner));

  check('renderer: ten_nganh readonly theo GRID_META',
    /\sreadonly[\s>]/.test(cells0[1].inner));
  check('renderer: buttons day du 6 action co data-act + data-loop',
    ['add', 'del', 'clear', 'up', 'down', 'dup'].every(act =>
      btnsNganh.indexOf('data-act="' + act + '"') >= 0 &&
        btnsNganh.indexOf('data-loop="ds_nganh"') >= 0),
    btnsNganh);

  // allowAdd=false -> an nut Them/Nhan ban; allowReorder=false -> an Len/Xuong
  const roMeta = Object.assign({}, FD.GRID_META, {
    ds_nganh: Object.assign({}, FD.GRID_META.ds_nganh,
      { allowAdd: false, allowReorder: false })
  });
  const htmlRo = R.renderBlocks(M01, store,
    { docId: 'PLII_M01', gridMeta: roMeta });
  const segRo = btnsDiv(htmlRo, 'ds_nganh');
  check('metadata allowAdd=false/allowReorder=false -> an nut tuong ung',
    !segRo.includes('btn-row-add') && !segRo.includes('btn-row-dup') &&
      !segRo.includes('btn-row-up') && !segRo.includes('btn-row-down') &&
      segRo.includes('btn-row-del') && segRo.includes('btn-row-clear'),
    segRo);
}

// --------------------------------- F. PHASE 6: field-grid theo uiLayout

{
  const docF = {
    id: 'FG_TEST', ten_mau: 'fixture field-grid',
    blocks: [
      { t: 'p', runs: [{ text: 'Vốn điều lệ (bằng số): ' },
                       { input: { key: 'von_dieu_le', w: 12 } }] },
      { t: 'p', runs: [{ text: 'Vốn điều lệ (bằng chữ): ' },
                       { input: { key: 'von_dieu_le_chu', w: 14 } }] },
      { t: 'p', runs: [{ text: 'Email: ' },
                       { input: { key: 'email_tru_so', w: 12 } }] }
    ]
  };
  const stF = R.newStore();
  stF.values.von_dieu_le = '1.000.000';
  stF.values.von_dieu_le_chu = 'Mot trieu dong';
  const layoutF = {
    id: 'FG_TEST',
    grids: [{
      anchor: 'von_dieu_le',
      title: 'Vốn điều lệ',
      hideAnchor: ['von_dieu_le', 'von_dieu_le_chu'],
      cols: [
        { key: 'von_dieu_le', type: 'money', label: 'Vốn bằng số', w: 16 },
        { key: 'von_dieu_le_chu', type: 'computed', label: 'Vốn bằng chữ' }
      ]
    }]
  };
  const hF = R.renderBlocks(docF, stF,
    { docId: 'FG_TEST', fieldMeta: FD.FIELD_META, uiLayout: layoutF });

  // grid xuất hiện SAU block chứa anchor và TRƯỚC các block còn lại
  const iGrid = hF.indexOf('<div class="field-grid"');
  const iAnchorInp = hF.indexOf('data-key="von_dieu_le"');
  const iEmail = hF.indexOf('data-key="email_tru_so"');
  check('field-grid: grid chen ngay sau block chua anchor key',
    iGrid > iAnchorInp && iAnchorInp < iEmail && iGrid < iEmail,
    'anchor=' + iAnchorInp + ' grid=' + iGrid + ' email=' + iEmail);

  // grid input mang dung canonical data-key + gia tri tu store (dong bo tu dong)
  const seg = hF.slice(iGrid);
  const inpVon = (seg.match(/<input[^>]*data-key="von_dieu_le"[^>]*>/) || [''])[0];
  const inpChu = (seg.match(/<input[^>]*data-key="von_dieu_le_chu"[^>]*>/) || [''])[0];
  check('field-grid: o input mang dung canonical data-key + value tu store',
    /value="1\.000\.000"/.test(inpVon) && /class="fld fg-fld num/.test(inpVon) &&
      /inputmode="numeric"/.test(inpVon) && !/\sreadonly[\s>]/.test(inpVon),
    inpVon);
  check('field-grid: col computed -> attr readonly + class .calc (nen xam nhat)',
    /\sreadonly[\s>]/.test(inpChu) && /fg-fld calc/.test(inpChu) &&
      !/readonly/.test(inpVon), inpChu);

  // block gốc KHÔNG bị xóa - chỉ bọc .dupe-anchor để ẩn thị giác
  check('field-grid: block anchor van render, chi an thi giac qua .dupe-anchor',
    (hF.match(/<div class="dupe-anchor">/g) || []).length === 2 &&
      hF.indexOf('data-key="von_dieu_le"') < iGrid);

  // không truyền uiLayout -> không có grid/dupe, số input giữ nguyên như cũ
  const hNo = R.renderBlocks(docF, stF,
    { docId: 'FG_TEST', fieldMeta: FD.FIELD_META });
  const cntInp = h => (h.match(/<input type="text"/g) || []).length;
  check('field-grid: khong truyen layout -> khong grid, khong dupe, input nguyen ven',
    hNo.indexOf('field-grid') < 0 && hNo.indexOf('dupe-anchor') < 0 &&
      cntInp(hNo) === 3 && cntInp(hF) === 5); // 3 gốc + 2 ô trong grid

  // anchor không tồn tại trong blocks -> bỏ qua grid, không vỡ render
  const layoutMiss = { id: 'FG_TEST', grids: [{
    anchor: 'key_khong_ton_tai', title: '?',
    cols: [{ key: 'von_dieu_le', type: 'money', label: 'V' }] }] };
  const hMiss = R.renderBlocks(docF, stF,
    { docId: 'FG_TEST', uiLayout: layoutMiss });
  check('field-grid: anchor khong ton tai -> bo qua grid (fallback an toan)',
    hMiss.indexOf('<div class="field-grid"') < 0 &&
      cntInp(hMiss) === 3);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
