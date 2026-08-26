/* test_form_grid_meta.js - P1-D "UI FORM-SCOPED GRID META" (PLAN.md mục
 * "editable-grid" + đặc tả bảng ngành):
 *  1. 5 loop PLI_M72 nhận metadata form-scoped đúng, không còn legacy path.
 *  2. Chỉ section PLI_M72 có dữ liệu mới chịu rule (required cột/ngành chính/
 *     VSIC/trùng mã); 4 section còn lại TRỐNG -> 0 lỗi blocking.
 *  3. 4 vùng ngành PLII_M02 ĐỘC LẬP, đúng ten-tag thật từng vùng; C.3 resolve
 *     semanticKey=nganh_hien_tai -> loop ds_nganh requirePrimary riêng mẫu.
 *  4. VSIC tự ghi tên vào đúng row/loop theo autoName.nameTag (mock vsicList).
 *  5. Không copy dữ liệu giữa các vùng sau add/delete/reorder.
 *  6. add/delete/reorder/duplicate generic trên cả 8 loop mới.
 *  7. _row_id ổn định + điều hướng lỗi đúng dòng sau reorder (render HTML).
 *  8. Draft v2 round-trip giữ đủ 8 loop mới + ds_nganh.
 *  9. Export payload sạch _row_id + map la_nganh_chinh 'X'/'' theo meta
 *     form-scoped.
 * 10. Grid cũ không hồi quy (fall-through toàn cục nguyên vẹn).
 * 11. BACKWARD COMPAT: getGridMeta('<loop>') trả GRID_META[name]||null như cũ.
 *
 * Chạy: node app_web/test_form_grid_meta.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');            // Helpers.GridCtl/gridMetaForDoc
const G = App.GridCtl;

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
const VSIC_FULL = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', 'app', 'data', 'nganh_vsic.json'), 'utf8')
).nganh;
/* mock vsicList nhỏ, deterministic cho case 4 */
const VSIC_MOCK = [
  { ma: '0111', ten: 'Trồng lúa', cap: 4 },
  { ma: '4711', ten: 'Bán lẻ máy tính', cap: 4 }
];

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

// ------------------------------------------------------------------ helpers

const M72 = loadProd('PLI_M72');
const M02 = loadProd('PLII_M02');

function findLoopBlock(doc, loopName) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === loopName)[0] || null;
}

/* render đúng cách app.js renderActiveDoc: gridMeta build theo docId */
function renderDoc(doc, store) {
  return R.renderBlocks(doc, store || R.newStore(), {
    docId: doc.id, fieldMeta: FD.FIELD_META,
    gridMeta: App.gridMetaForDoc(doc.id)
  });
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

function attrVal(attrs, name) {
  const m = String(attrs).match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1] : null;
}

function errsOf(docId, blocks, store, vsicList) {
  return FD.validateDocument(docId, blocks, store,
    { vsicList: vsicList == null ? VSIC_FULL : vsicList });
}
function loopErrs(errs) {
  return errs.filter(e => String(e.key).indexOf('loop:') === 0);
}
function blockingLoopErrs(errs) {
  return loopErrs(errs).filter(e => e.severity === 'blocking');
}
function mkStore(loops) {
  const s = R.newStore();
  Object.keys(loops || {}).forEach(k => {
    s.loops[k] = (loops[k] || []).map(r => Object.assign({ _row_id: FD.makeRowId() }, r));
  });
  return s;
}
const tagsOf = g => (g.columns || []).map(c => c.tag);
const colOf = (g, t) => (g.columns || []).filter(c => c.tag === t)[0] || null;

// ============ 1. 5 loop PLI_M72 nhan meta dung, khong con legacy path =======

const M72_LOOPS = ['ds_nganh_dntn', 'ds_nganh_tnhh_1tv', 'ds_nganh_tnhh_2tv',
  'ds_nganh_ctcp', 'ds_nganh_dhdn'];

M72_LOOPS.forEach(loop => {
  const b = findLoopBlock(M72, loop);
  const g = FD.getGridMeta({ docId: 'PLI_M72', loop: loop });
  check('1. PLI_M72/' + loop + ': resolver tra meta form-scoped (truoc day null)',
    !!b && !!g && !!FD.FORM_GRID_META.PLI_M72.loops[loop] &&
      g !== FD.GRID_META.ds_nganh && FD.getGridMeta(loop) === null);
  check('1. PLI_M72/' + loop + ': semanticKey + sync_group + row contract',
    g.semanticKey === loop &&
      g.syncGroup === 'ds_nganh_pli_m72' &&
      FD.FORM_GRID_META.PLI_M72.bySemanticKey[loop] === g &&
      ['ten_nganh', 'ma_nganh', 'la_nganh_chinh'].every(t => colOf(g, t)) &&
      colOf(g, 'ten_nganh').type === 'readonly' &&
      colOf(g, 'ma_nganh').type === 'vsic' &&
      colOf(g, 'la_nganh_chinh').type === 'radio' &&
      g.requirePrimary === true &&
      g.activeWhen && g.activeWhen.minFilledRows === 1);
});

{
  // chứng minh đi qua validateGridLoop (không legacy): lỗi mang key row_id
  const st = mkStore({ ds_nganh_dntn: [{ ma_nganh: '9999', ten_nganh: 'X' }] });
  const errs = blockingLoopErrs(errsOf('PLI_M72', M72.blocks, st));
  check('1. PLI_M72 loop co du lieu di qua validateGridLoop (loi theo row_id)',
    errs.some(e => e.code === 'VSIC_INVALID' &&
      e.key === 'loop:ds_nganh_dntn:' + st.loops.ds_nganh_dntn[0]._row_id + ':ma_nganh'),
    JSON.stringify(errs.map(e => e.key)));
}

// ======== 2. chi section co du lieu bi required/primary, trong -> 0 loi =====

{
  const eEmpty = blockingLoopErrs(errsOf('PLI_M72', M72.blocks, R.newStore()));
  check('2. M72 ca 5 section TRONG -> 0 loi blocking o moi loop (activeWhen)',
    eEmpty.length === 0, JSON.stringify(eEmpty.map(e => e.key)));

  // chỉ 1 section có dữ liệu thiếu ngành chính -> lỗi CHỈ ở section đó
  const st = mkStore({
    ds_nganh_tnhh_1tv: [
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
      { ma_nganh: '0112', ten_nganh: 'Trồng ngô và cây lương thực có hạt khác' }
    ]
  });
  const errs = errsOf('PLI_M72', M72.blocks, st);
  const pir = errs.filter(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED');
  check('2. section CO du lieu chua chon nganh chinh -> PRIMARY_INDUSTRY_REQUIRED',
    pir.length === 1 && pir[0].key === 'loop:ds_nganh_tnhh_1tv:' +
      st.loops.ds_nganh_tnhh_1tv[0]._row_id, JSON.stringify(pir));
  check('2. 4 section khong du lieu KHONG sinh bat ky loi loop nao',
    loopErrs(errs).every(e => e.key.indexOf('loop:ds_nganh_tnhh_1tv') === 0),
    JSON.stringify(loopErrs(errs).map(e => e.key)));

  // chọn ngành chính ở section đó -> hết lỗi loop (các section khác vẫn im)
  G.setExclusiveRadio(st, 'ds_nganh_tnhh_1tv',
    st.loops.ds_nganh_tnhh_1tv[1]._row_id, 'la_nganh_chinh', true);
  check('2. da chon nganh chinh dung section -> 0 loi loop toan mau',
    blockingLoopErrs(errsOf('PLI_M72', M72.blocks, st)).length === 0);

  // trùng mã trong một section -> DUPLICATE_INDUSTRY blocking cả hai dòng
  const dup = mkStore({
    ds_nganh_ctcp: [
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa' }
    ]
  });
  const dErrs = errsOf('PLI_M72', M72.blocks, dup)
    .filter(e => e.code === 'DUPLICATE_INDUSTRY');
  const ids = dup.loops.ds_nganh_ctcp.map(r => r._row_id);
  check('2. trung ma trong 1 section -> DUPLICATE_INDUSTRY tro CA HAI dong',
    dErrs.length === 2 &&
      dErrs.every(e => e.severity === 'blocking' && e.key.indexOf('loop:ds_nganh_ctcp:') === 0) &&
      dErrs.every(e => ids.some(id => e.key.indexOf(':' + id + ':') > 0)),
    JSON.stringify(dErrs.map(e => e.key)));
}

// ==== 3. PLII_M02: 4 region doc lap + dung tag tung vung + C.3 resolve ======

{
  const boSung = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_bo_sung' });
  const xoaBo = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_xoa_bo' });
  const suaDoi = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_sua_doi_chi_tiet' });
  const c3BySk = FD.getGridMeta({ docId: 'PLII_M02', semanticKey: 'nganh_hien_tai' });
  const c3ByLoop = FD.getGridMeta({ docId: 'PLII_M02', loop: 'ds_nganh' });

  check('3. nganh_bo_sung dung cot that (ten_nganh_bo_sung, khong ke thua PLI_M12)',
    JSON.stringify(tagsOf(boSung)) ===
      JSON.stringify(['ten_nganh_bo_sung', 'ma_nganh', 'la_nganh_chinh']) &&
      boSung.semanticKey === 'nganh_bo_sung' && boSung.requirePrimary === false);
  check('3. nganh_xoa_bo dung cot that (ten_nganh_bo + co cot nganh chinh)',
    JSON.stringify(tagsOf(xoaBo)) ===
      JSON.stringify(['ten_nganh_bo', 'ma_nganh', 'la_nganh_chinh']) &&
      xoaBo.semanticKey === 'nganh_xoa_bo' && xoaBo.requirePrimary === false);
  check('3. nganh_sua_doi_chi_tiet KHONG co cot nganh chinh, requirePrimary=false',
    JSON.stringify(tagsOf(suaDoi)) === JSON.stringify(['ten_nganh', 'ma_nganh']) &&
      suaDoi.requirePrimary === false && !colOf(suaDoi, 'la_nganh_chinh'));
  check('3. C.3 resolve semanticKey=nganh_hien_tai === loop ds_nganh, requirePrimary RIENG mau nay',
    c3BySk === c3ByLoop && !!c3BySk && c3BySk.semanticKey === 'nganh_hien_tai' &&
      c3BySk.requirePrimary === true &&
      // vẫn là bản form-scoped: khác object với canonical dùng chung
      c3BySk !== FD.GRID_META.ds_nganh);

  // regression bug đã audit: dong co du lieu THAT khong bi bao thieu ten_nganh
  const stA = mkStore({ nganh_bo_sung: [{ ten_nganh_bo_sung: 'Bán lẻ', ma_nganh: '4711' }] });
  const eA = loopErrs(errsOf('PLII_M02', M02.blocks, stA, VSIC_MOCK));
  check('3. region A co du lieu -> KHONG con ROW_INCOMPLETE gia (bug ke thua meta PLI_M12)',
    eA.length === 0, JSON.stringify(eA.map(e => e.code + '@' + e.key)));

  // độc lập validation: điền 1 region không sinh nghĩa vụ ở region kia
  const eOnlyA = blockingLoopErrs(errsOf('PLII_M02', M02.blocks, stA, VSIC_MOCK));
  check('3. dien rieng region A -> C.3 va cac region khac im (khong INDUSTRY_REQUIRED)',
    eOnlyA.length === 0, JSON.stringify(eOnlyA.map(e => e.key)));

  // C.3 có dữ liệu mà chưa chọn ngành chính -> lỗi riêng của nó
  const stC3 = mkStore({ ds_nganh: [
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
    { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy tính' }
  ] });
  const eC3 = blockingLoopErrs(errsOf('PLII_M02', M02.blocks, stC3, VSIC_MOCK));
  check('3. C.3 co du lieu chua chon nganh chinh -> PRIMARY_INDUSTRY_REQUIRED tai ds_nganh',
    eC3.length === 1 && eC3[0].code === 'PRIMARY_INDUSTRY_REQUIRED' &&
      eC3[0].key === 'loop:ds_nganh:' + stC3.loops.ds_nganh[0]._row_id,
    JSON.stringify(eC3.map(e => e.key)));

  // isolation 2 chiều: PLI_M12 vẫn nhận meta toàn cục của chính nó
  const m12BoSung = FD.getGridMeta({ docId: 'PLI_M12', loop: 'nganh_bo_sung' });
  check('3. PLI_M12/nganh_bo_sung van nhan meta cu (isolation 2 chieu)',
    m12BoSung === FD.GRID_META.nganh_bo_sung &&
      tagsOf(m12BoSung)[0] === 'ten_nganh' && m12BoSung !== boSung);

  // renderer GENERIC: bảng nào cũng render theo map truyền vào, đúng tag/radio
  const stAll = mkStore({
    nganh_bo_sung: [{ ten_nganh_bo_sung: 'A-region', ma_nganh: '0111', la_nganh_chinh: 'X' }],
    nganh_xoa_bo: [{ ten_nganh_bo: 'B-region', ma_nganh: '0111' }],
    nganh_sua_doi_chi_tiet: [{ ten_nganh: 'C-region', ma_nganh: '0111' }],
    ds_nganh: [{ ten_nganh: 'D-region', ma_nganh: '0111', la_nganh_chinh: 'X' }]
  });
  const html = renderDoc(M02, stAll);
  const segBoSung = loopTable(html, 'nganh_bo_sung');
  const segXoa = loopTable(html, 'nganh_xoa_bo');
  const segSua = loopTable(html, 'nganh_sua_doi_chi_tiet');
  const segC3 = loopTable(html, 'ds_nganh');
  check('3. renderer tung bang hien dung tag/gia tri vung do (generic, khong hard-code)',
    /value="A-region"/.test(segBoSung) &&
      /data-tag="ten_nganh_bo_sung"/.test(segBoSung) &&
      /value="B-region"/.test(segXoa) && /data-tag="ten_nganh_bo"/.test(segXoa) &&
      /value="C-region"/.test(segSua) &&
      /value="D-region"/.test(segC3) && /data-tag="ten_nganh"/.test(segC3));
  check('3. renderer: radio nganh chinh co o region co cot, KHONG co o sua_doi',
    /type="radio"/.test(segBoSung) && /type="radio"/.test(segXoa) &&
      /type="radio"/.test(segC3) && !/type="radio"/.test(segSua));
  check('3. renderer M72: 5 bang deu radio + ten_nganh readonly theo meta form-scoped',
    (() => {
      const h72 = renderDoc(M72, mkStore({
        ds_nganh_dntn: [{ ma_nganh: '0111', ten_nganh: 'T', la_nganh_chinh: 'X' }]
      }));
      return M72_LOOPS.every(l => {
        const seg = loopTable(h72, l);
        return seg && /type="radio"/.test(seg) && /\sreadonly/.test(seg);
      }) && /checked/.test(loopTable(h72, 'ds_nganh_dntn'));
    })());
}

// ======== 4. VSIC tu ghi ten dung row/loop (autoName.nameTag tung vung) =====

{
  const cases = [
    { loop: 'nganh_bo_sung', nameTag: 'ten_nganh_bo_sung' },
    { loop: 'nganh_xoa_bo', nameTag: 'ten_nganh_bo' },
    { loop: 'nganh_sua_doi_chi_tiet', nameTag: 'ten_nganh' },
    { loop: 'ds_nganh', nameTag: 'ten_nganh' },
    { loop: 'ds_nganh_ctcp', docId: 'PLI_M72', nameTag: 'ten_nganh' }
  ];
  cases.forEach(c => {
    const docId = c.docId || 'PLII_M02';
    const st = mkStore({ [c.loop]: [{ ma_nganh: '0111', [c.nameTag]: 'Ten sai choi' }] });
    const errs = errsOf(docId, docId === 'PLI_M72' ? M72.blocks : M02.blocks, st, VSIC_MOCK);
    const row = st.loops[c.loop][0];
    const othersOk = Object.keys(row).every(k =>
      k !== 'ten_nganh' || k === c.nameTag ? true : row[k] === '');
    check('4. ' + docId + '/' + c.loop + ': ten chinh thuc ghi dung tag "' + c.nameTag + '"',
      row[c.nameTag] === 'Trồng lúa' &&
        !errs.some(e => e.code === 'NAME_MISMATCH' || e.code === 'VSIC_INVALID'),
      JSON.stringify(row));
    if (c.nameTag !== 'ten_nganh') {
      check('4. ' + docId + '/' + c.loop + ': KHONG leak sang tag ten_nganh khac',
        !('ten_nganh' in row), Object.keys(row).join(','));
    }
    void othersOk;
  });
}

// ==== 5. khong copy du lieu giua cac region sau add/delete/reorder ==========

{
  const st = mkStore({
    nganh_bo_sung: [{ ma_nganh: '0111', ten_nganh_bo_sung: 'Giong A' }],
    nganh_xoa_bo: [{ ma_nganh: '4711', ten_nganh_bo: 'Rieng B' }],
    ds_nganh: [{ ma_nganh: '0111', ten_nganh: 'Hien tai D' }]
  });
  const snapB = JSON.stringify(st.loops.nganh_xoa_bo);
  const snapD = JSON.stringify(st.loops.ds_nganh);

  const added = G.addRow(st, 'nganh_bo_sung', null);
  st.loops.nganh_bo_sung[added.index].ma_nganh = '0112';
  G.moveRow(st, 'nganh_bo_sung', added.id, -1);
  G.deleteRows(st, 'nganh_xoa_bo', [st.loops.nganh_xoa_bo[0]._row_id]);

  check('5. xoa chu dong region B (khong dong B tu region khac) -> B ve rong',
    st.loops.nganh_xoa_bo.length === 0);
  check('5. region C.3 (ds_nganh) khong bi anh huong boi region khac',
    JSON.stringify(st.loops.ds_nganh) === snapD);
  check('5. du lieu region A di theo _row_id sau reorder',
    st.loops.nganh_bo_sung.length === 2 &&
      st.loops.nganh_bo_sung[0].ma_nganh === '0112' &&
      st.loops.nganh_bo_sung[1].ma_nganh === '0111');

  // render: mỗi bảng vẫn chỉ hiển thị dữ liệu của loop riêng nó
  const html = renderDoc(M02, st);
  check('5. renderer khong lan du lieu giua bang sau thay doi',
    /value="Hien tai D"/.test(loopTable(html, 'ds_nganh')) &&
      !/value="Hien tai D"/.test(loopTable(html, 'nganh_bo_sung')) &&
      !/value="Giong A"/.test(loopTable(html, 'ds_nganh')));
}

// ============ 6. contract generic tren 8 loop moi ============================

function runMiniContract(docId, doc, loop) {
  const label = docId + '/' + loop;
  const st = R.newStore();
  const a1 = G.addRow(st, loop, null);
  const a2 = G.addRow(st, loop, null);
  const a3 = G.addRow(st, loop, a1.id);
  check('6. ' + label + ': addRow giua -> thu tu [a1,a3,a2]',
    st.loops[loop].map(r => r._row_id).join(',') === [a1.id, a3.id, a2.id].join(','));

  const rowsPre = st.loops[loop];
  rowsPre[0].ma_nganh = '0111';
  rowsPre[2].ma_nganh = '0112';
  const snapA2 = JSON.stringify(rowsPre[2]);
  G.moveRow(st, loop, a2.id, -1);
  const after = st.loops[loop];
  check('6. ' + label + ': reorder giu _row_id + du lieu di theo row',
    after[1]._row_id === a2.id && JSON.stringify(after[1]) === snapA2);

  const del = G.deleteRows(st, loop, [after[0]._row_id]);
  check('6. ' + label + ': deleteRows theo id', del === 1 && st.loops[loop].length === 2);

  // duplicate: PHẢI truyền docId để nhân bản theo đúng metadata form-scoped
  // (UI uiDuplicateRow luôn truyền state.activeDocId). Field bị bỏ theo ĐÚNG
  // duplicateKeys metadata: M72 khai ['ma_nganh'] -> bỏ; region PLII_M02
  // khai [] (không chặn trùng) -> giữ nguyên, chỉ _row_id mới.
  const src = st.loops[loop][0];
  src.ma_nganh = '6201';
  src._src_mark = 'giu';
  const dres = G.duplicateRow(st, loop, src._row_id, docId);
  const clone = st.loops[loop][dres.index];
  const stripsMaNganh = docId === 'PLI_M72';
  check('6. ' + label + ': duplicate theo duplicateKeys meta (' +
      (stripsMaNganh ? 'bo ma_nganh' : 'giu ma_nganh vi duplicateKeys=[]') +
      ') + _row_id moi',
    !!clone && (stripsMaNganh ? !('ma_nganh' in clone) : clone.ma_nganh === '6201') &&
      clone._row_id !== src._row_id && clone._src_mark === 'giu');
}

M72_LOOPS.forEach(l => runMiniContract('PLI_M72', M72, l));
['nganh_bo_sung', 'nganh_xoa_bo', 'nganh_sua_doi_chi_tiet']
  .forEach(l => runMiniContract('PLII_M02', M02, l));

// ==== 7. stable row id + error nav dung dong sau reorder (render HTML) ======

{
  const st = mkStore({
    ds_nganh_dntn: [
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
      { ma_nganh: '9999', ten_nganh: 'Ma sai' }
    ]
  });
  const badId = st.loops.ds_nganh_dntn[1]._row_id;
  const errs = errsOf('PLI_M72', M72.blocks, st);
  const cellErr = errs.find(e => e.severity === 'blocking' &&
    e.key === 'loop:ds_nganh_dntn:' + badId + ':ma_nganh');
  G.moveRow(st, 'ds_nganh_dntn', badId, -1);   // dòng lỗi lên vị trí 0
  const html = renderDoc(M72, st);
  const tbl = loopTable(html, 'ds_nganh_dntn');
  const rows = bodyRows(tbl);
  const idxNow = G.findRowIndex(st.loops.ds_nganh_dntn, badId);
  const errTr = rows.filter(r => attrVal(r.attrs, 'data-row-id') === badId)[0];
  // mô phỏng findErrorField: trỏ đúng Ô ma_nganh (không phải ô đầu của dòng)
  const maNganhTd = errTr ? errTr.inner.split('<td').filter(seg =>
    seg.indexOf('data-tag="ma_nganh"') >= 0)[0] : null;
  const resolvedKey = maNganhTd
    ? ((maNganhTd.match(/data-key="(loop:[^"]+)"/) || [])[1] || null)
    : null;
  check('7. loi VSIC theo row_id van tro dung dong sau reorder (data-row-id)',
    !!cellErr && idxNow === 0 &&
      resolvedKey === 'loop:ds_nganh_dntn:' + idxNow + ':ma_nganh',
    'resolvedKey=' + resolvedKey + ' idxNow=' + idxNow);
  check('7. STT danh lai theo thu tu moi, _row_id giu nguyen',
    rows.map(r => (r.inner.match(/<td class="stt">(\d+)<\/td>/) || [])[1])
      .filter(Boolean).join(',') === '1,2,3,4' &&
      attrVal(rows[idxNow].attrs, 'data-row-id') === badId);
}

// ==== 8. draft round-trip giu du 8 loop moi + ds_nganh ======================

{
  const loopsIn = {
    ds_nganh_dntn: [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }],
    ds_nganh_tnhh_1tv: [{ ma_nganh: '0112', ten_nganh: 'Trong ngo' }],
    ds_nganh_tnhh_2tv: [{ ma_nganh: '6201', ten_nganh: 'Lap trinh' }],
    ds_nganh_ctcp: [],
    ds_nganh_dhdn: [{ ma_nganh: '4711' }],
    nganh_bo_sung: [{ ma_nganh: '0111', ten_nganh_bo_sung: 'Bo sung' }],
    nganh_xoa_bo: [{ ma_nganh: '4711', ten_nganh_bo: 'Xoa bo' }],
    nganh_sua_doi_chi_tiet: [{ ma_nganh: '0112', ten_nganh: 'Sua chi tiet' }],
    ds_nganh: [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }]
  };
  const before = mkStore(loopsIn);
  const idsBefore = {};
  Object.keys(before.loops).forEach(k => {
    idsBefore[k] = before.loops[k].map(r => r._row_id);
  });
  const draft = {
    v: 2, caseId: 'thay_doi_m72_hkd', checkedForms: [], activeDocId: null,
    autoSum: false, viewState: {}, savedAt: null,
    store: JSON.parse(JSON.stringify(before))
  };
  const mig = FD.migrateDraft(draft);
  let okLen = true, okOrder = true, okIds = true, okData = true;
  Object.keys(loopsIn).forEach(k => {
    const rows = mig.store.loops[k] || [];
    if (rows.length !== loopsIn[k].length) okLen = false;
    if (JSON.stringify(rows.map(r => r.ma_nganh)) !==
        JSON.stringify(loopsIn[k].map(r => r.ma_nganh))) okOrder = false;
    if (loopsIn[k].length &&
        JSON.stringify(rows.map(r => r._row_id)) !== JSON.stringify(idsBefore[k])) {
      okIds = false;
    }
    if (!loopsIn[k].length) return;
    const wantKeys = Object.keys(loopsIn[k][0]).concat(['_row_id']).sort();
    if (JSON.stringify(Object.keys(rows[0]).sort()) !== JSON.stringify(wantKeys)) {
      okData = false;
    }
  });
  check('8. draft v2 round-trip: du 9 loop (8 moi + ds_nganh) dung so dong',
    okLen && Object.keys(mig.store.loops).length >= 9);
  check('8. draft v2 round-trip: thu tu du lieu + _row_id nguyen ven', okOrder && okIds);
  check('8. draft v2 round-trip: du lieu tung vung giu dung tag rieng', okData);

  // draft cũ thiếu _row_id -> migrateDraft gán id ổn định khi nạp
  const old = {
    v: 1, caseId: 'x', checkedForms: [], autoSum: false,
    store: { values: {}, checks: {}, loops: {
      ds_nganh_dntn: [{ ma_nganh: '0111' }],
      nganh_bo_sung: [{ ma_nganh: '0112', ten_nganh_bo_sung: 'A' }]
    } }
  };
  const up = FD.migrateDraft(old);
  check('8. draft v1: row moi thieu _row_id duoc gan luc nap (ca 2 loop)',
    /^r\d+_/.test(up.store.loops.ds_nganh_dntn[0]._row_id) &&
      /^r\d+_/.test(up.store.loops.nganh_bo_sung[0]._row_id));
}

// ==== 9. export payload sach _row_id + map X/'' theo meta form-scoped =======

{
  const st = mkStore({
    ds_nganh_ctcp: [
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
      { ma_nganh: '0112', ten_nganh: 'Trong ngo' }          // thiếu prop
    ],
    nganh_sua_doi_chi_tiet: [{ ma_nganh: '6201', ten_nganh: 'Lap trinh' }]
  });
  const ex = G.exportLoops(st, ['PLI_M72']);
  const allRows = [].concat(ex.ds_nganh_ctcp || [], ex.nganh_sua_doi_chi_tiet || []);
  check('9. exportLoops(co docIds): khong con field noi bo (_*) trong payload',
    allRows.every(r => Object.keys(r).every(k => k.charAt(0) !== '_')));
  check('9. exportLoops: la_nganh_chinh map X/"" ; row thieu prop duoc dien "" khi requirePrimary',
    ex.ds_nganh_ctcp[0].la_nganh_chinh === 'X' &&
      ex.ds_nganh_ctcp[1].la_nganh_chinh === '');

  // backward compat: 1 tham số - hành vi cũ (resolve toàn cục, không thêm prop)
  const stOld = mkStore({
    ds_nganh_ctcp: [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]
  });
  const exOld = G.exportLoops(stOld);
  check('9. exportLoops(1 tham so) giu hanh vi cu: khong them prop khi meta la null',
    !Object.prototype.hasOwnProperty.call(exOld.ds_nganh_ctcp[0], 'la_nganh_chinh'));
}

// ==== 10. grid cu khong hoi quy (fall-through toan cuc nguyen ven) ==========

{
  check('10. loop cu resolve ve dung object GRID_META toan cuc (same ref)',
    FD.getGridMeta({ docId: 'PLI_M06', loop: 'ds_thanh_vien' }) === FD.GRID_META.ds_thanh_vien &&
      FD.getGridMeta({ docId: 'PLII_M01', loop: 'ds_nganh' }) === FD.GRID_META.ds_nganh &&
      FD.getGridMeta({ docId: 'PLI_M02', loop: 'ds_nganh' }) === FD.GRID_META.ds_nganh);
  check('10. GRID_META.ds_nganh khong bi mutate khi khai FORM_GRID_META (clone isolation)',
    FD.GRID_META.ds_nganh.columns[0].tag === 'ten_nganh' &&
      FD.GRID_META.ds_nganh.required === true &&
      FD.GRID_META.ds_nganh.minRows === 1);
  // validator mẫu cũ vẫn chạy đúng đường cũ (regression nhanh)
  const M01 = loadProd('PLII_M01');
  const e0 = blockingLoopErrs(errsOf('PLII_M01', M01.blocks, R.newStore()));
  check('10. PLII_M01 ds_nganh TRONG van INDUSTRY_REQUIRED nhu cu (grid cu khong doi)',
    e0.length === 1 && e0[0].code === 'INDUSTRY_REQUIRED' && e0[0].key === 'loop:ds_nganh',
    JSON.stringify(e0.map(e => e.key)));
  const M06 = loadProd('PLI_M06');
  const s1 = mkStore({ ds_thanh_vien: [
    { ho_ten: 'A', von_dong_gop: 'chuwa nhap', ty_le_von: '100' }] });
  const e1 = errsOf('PLI_M06', M06.blocks, s1);
  check('10. PLI_M06 MIN_ROWS/MONEY van hoat dong tren meta toan cuc',
    e1.some(e => e.code === 'MIN_ROWS') && e1.some(e => e.code === 'MONEY'));
  check('10. query lac quan: loop khong ton tai / docId la -> null an toan',
    FD.getGridMeta({ loop: 'khong_co' }) === null &&
      FD.getGridMeta({ docId: 'KHONG_CO', loop: 'ds_nganh' }) === FD.GRID_META.ds_nganh &&
      FD.getGridMeta({}) === null);
}

// ==== 11. BACKWARD COMPAT string call =======================================

{
  check("11. getGridMeta('ds_thanh_vien') tra meta cu Y NGUYEN (minRows=2)",
    FD.getGridMeta('ds_thanh_vien') === FD.GRID_META.ds_thanh_vien &&
      FD.getGridMeta('ds_thanh_vien').minRows === 2 &&
      FD.getGridMeta('ds_thanh_vien').columns.length === 10);
  check("11. getGridMeta('ds_nganh') === GRID_META.ds_nganh; loop la -> null",
    FD.getGridMeta('ds_nganh') === FD.GRID_META.ds_nganh &&
      FD.getGridMeta('ds_nganh_kinh_doanh') === null &&
      FD.getGridMeta('ds_nganh_dntn') === null);
  check('11. root exports: GRID_META + FORM_GRID_META + getGridMeta ton tai',
    !!FD.GRID_META && !!FD.FORM_GRID_META && typeof FD.getGridMeta === 'function');
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
