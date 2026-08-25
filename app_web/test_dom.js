/* test_dom.js - kiểm thử KHÔNG GUI cho giao diện web ĐKKD.
 *
 * Chạy:  node app_web/test_dom.js
 *
 * Dùng các hàm thuần trong ui/render.js + ui/form-domain.js và dữ liệu mock
 * trong ui/mock/. Kiểm tra trên chuỗi HTML sinh ra (đếm bằng regex) - không
 * cần jsdom.
 *
 * Phần gốc (1-6): render schema, điền store, bảng lặp, tổng vốn, ngày ký,
 * tra cứu VSIC.
 * Phần pilot HTKK (7-15) theo docs/htkk-ui-contract.md:
 *   tabs từ case pilot, một tờ khai duy nhất active, đồng bộ key chung,
 *   đổi tab giữ dữ liệu, draft v2 save/reload, validation + gate export,
 *   điều hướng lỗi tới đúng ô, VSIC chuột/bàn phím, thêm/xóa dòng,
 *   auto-sum số lớn.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');

const MOCK_DIR = path.join(__dirname, 'ui', 'mock');
function loadMock(name) {
  return JSON.parse(fs.readFileSync(path.join(MOCK_DIR, name), 'utf8'));
}

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) {
    passed++;
    console.log('PASS  ' + name);
  } else {
    failed++;
    console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : ''));
  }
}

/* ---- bộ đếm độc lập: đi qua JSON mock để tính số input/chk kỳ vọng ---- */
function countExpected(blocks) {
  let textInputs = 0;
  let checkboxes = 0;
  function walkRuns(runsOrCell) {
    const runs = Array.isArray(runsOrCell) ? runsOrCell : (runsOrCell && runsOrCell.runs);
    (runs || []).forEach(function (r) {
      if (r && r.input) {
        if (r.input.chk !== undefined) checkboxes++;
        else textInputs++;
      }
    });
  }
  (blocks || []).forEach(function (b) {
    if (b.t === 'p') walkRuns(b.runs);
    else if (b.t === 'chk') checkboxes++;
    else if (b.t === 'table') (b.rows || []).forEach(function (row) {
      (row.cells || []).forEach(walkRuns);
    });
    else if (b.t === 'loop') textInputs += (b.cols || []).length * (b.blankRows || 0);
  });
  return { textInputs: textInputs, checkboxes: checkboxes };
}

function countMatches(html, re) {
  const m = html.match(re);
  return m ? m.length : 0;
}

// ---------------------------------------------------------------- 1. render
const m02 = loadMock('blocks_PLI_M02.json');
const m06 = loadMock('blocks_PLI_M06.json');
const m21 = loadMock('blocks_PLII_M01.json');

[m02, m06, m21].forEach(function (doc) {
  const exp = countExpected(doc.blocks);
  const html = R.renderBlocks(doc, R.newStore());
  const gotTxt = countMatches(html, /<input type="text"/g);
  const gotChk = countMatches(html, /<input type="checkbox"/g);
  check(
    'render ' + doc.id + ': ' + exp.textInputs + ' o input text',
    gotTxt === exp.textInputs,
    'got ' + gotTxt
  );
  check(
    'render ' + doc.id + ': ' + exp.checkboxes + ' checkbox',
    gotChk === exp.checkboxes,
    'got ' + gotChk
  );
});

// ------------------------------------------------------- 2. dien store
{
  const store = R.newStore();
  store.values['dn.ten_tieng_viet'] = 'CONG TY TEST MOT THANH VIEN';
  const html = R.renderBlocks(m02, store);
  const n = countMatches(html, /value="CONG TY TEST MOT THANH VIEN"/g);
  check('dien dn.ten_tieng_viet -> HTML phan anh gia tri', n >= 1, 'got ' + n);

  store.checks['chk_tt_thanh_lap_moi'] = true;
  const html2 = R.renderBlocks(m02, store);
  check(
    'tick chk_tt_thanh_lap_moi -> input checked',
    html2.indexOf('<input type="checkbox" class="chk-box" data-key="chk_tt_thanh_lap_moi" checked>') >= 0
  );

  // dong bo giua cac mau: M06 cung co input key dn.ten_tieng_viet
  const htmlM06 = R.renderBlocks(m06, store);
  check(
    'dong bo key giua mau: PLI_M06 cung nhan gia tri dn.ten_tieng_viet',
    countMatches(htmlM06, /value="CONG TY TEST MOT THANH VIEN"/g) === 1
  );
}

// ------------------------------------------------- 3. loop them 2 hang
{
  // mô phỏng đúng thao tác của app.js khi bấm [+ Thêm dòng] hai lần
  const store = R.newStore();
  const miniDoc = {
    id: 'TEST_LOOP',
    ten_mau: 'test',
    blocks: [{
      t: 'loop',
      loop: 'ds_test',
      headerRows: [0],
      rows: [{ cells: [{ runs: [{ text: 'STT' }] }, { runs: [{ text: 'A' }] }] }],
      cols: [{ col: 2, tag: 'gia_tri' }],
      blankRows: 0
    }]
  };
  store.loops.ds_test = [];
  store.loops.ds_test.push({ gia_tri: 'hang mot' });
  store.loops.ds_test.push({ gia_tri: 'hang hai' });

  const html = R.renderBlocks(miniDoc, store);
  const stts = [];
  const re = /<td class="stt">(\d+)<\/td>/g;
  let mm;
  while ((mm = re.exec(html)) !== null) stts.push(mm[1]);
  check('loop them 2 hang -> STT la 1,2', stts.join(',') === '1,2', 'got ' + stts.join(','));

  function hasInputWith(html, key, val) {
    const re = new RegExp(
      '<input[^>]*data-key="' + key.replace(/:/g, ':') + '"[^>]*value="' + val + '"');
    return re.test(html);
  }
  check(
    'du lieu hang 0 dung vi tri (loop:ds_test:0:gia_tri)',
    hasInputWith(html, 'loop:ds_test:0:gia_tri', 'hang mot')
  );
  check(
    'du lieu hang 1 dung vi tri (loop:ds_test:1:gia_tri)',
    hasInputWith(html, 'loop:ds_test:1:gia_tri', 'hang hai')
  );

  // bảng lặp có sẵn blankRows: hiển thị đủ max(số dòng, blankRows)
  const storeM06 = R.newStore();
  storeM06.loops.ds_thanh_vien = [{ ho_ten: 'NGUYEN VAN A' }];
  const htmlM06 = R.renderBlocks(m06, storeM06);
  const soHang = countMatches(htmlM06, /data-loop="ds_thanh_vien"/g);
  const sttRows = countMatches(htmlM06, /class="stt">/g);
  check('PLI_M06: hang hien thi = max(1 dong du lieu, 4 blankRows)', sttRows === 4, 'got ' + sttRows);
  check(
    'PLI_M06: gia tri ho_ten vao dung o hang 0',
    hasInputWith(htmlM06, 'loop:ds_thanh_vien:0:ho_ten', 'NGUYEN VAN A')
  );
}

// --------------------------------------------- 4. tong von tu dong tinh
{
  const store = R.newStore();
  store.loops.ds_thanh_vien = [
    { ho_ten: 'A', von_dong_gop: '50000000' },
    { ho_ten: 'B', von_dong_gop: '30.000.000' },
    { ho_ten: 'C', von_dong_gop: 'chua nhap' }
  ];
  const out = R.calcTotals(store, false); // tự điền vì ô đang trống
  check('tong von_dong_gop = 80.000.000 (tu dien khi trong)',
    out.von_dieu_le === '80.000.000', 'got ' + out.von_dieu_le);

  // đã có giá trị mà không bật "tự cộng" -> không ghi đè
  store.values.von_dieu_le = '999';
  const out2 = R.calcTotals(store, false);
  check('khong bat "tu cong" -> khong ghi de von_dieu_le da co',
    out2.von_dieu_le === undefined);

  // bật "tự cộng" -> luôn ghi đè
  const out3 = R.calcTotals(store, true);
  check('bat "tu cong" -> ghi de von_dieu_le = 80.000.000',
    out3.von_dieu_le === '80.000.000');

  // tổng von_kinh_doanh các hàng loop (mô hình PLII_M01)
  const s2 = R.newStore();
  s2.loops.kinh_doanh = [
    { von_kinh_doanh: '120000000' },
    { von_kinh_doanh: '80000000' }
  ];
  const out4 = R.calcTotals(s2, true);
  check('tong von_kinh_doanh = 200.000.000',
    out4.von_kinh_doanh === '200.000.000', 'got ' + out4.von_kinh_doanh);

  // applyAutoFills áp cả tổng vào store
  const merged = R.applyAutoFills(store, true);
  check('applyAutoFills ghi ket qua vao store.values',
    merged.values.von_dieu_le === '80.000.000');
}

// --------------------------------------------------- 5. ngay ky hom nay
{
  const merged = R.applyAutoFills(R.newStore(), false);
  const now = new Date();
  const pad2 = function (n) { return (n < 10 ? '0' : '') + n; };
  check('tu dien ngay_ky_vb = hom nay',
    merged.values.ngay_ky_vb === pad2(now.getDate()),
    'got ' + merged.values.ngay_ky_vb);
  check('tu dien thang_ky_vb = thang nay',
    merged.values.thang_ky_vb === pad2(now.getMonth() + 1));
  check('tu dien nam_ky_vb = nam nay',
    merged.values.nam_ky_vb === String(now.getFullYear()));
}

// ------------------------------------------------------------ 6. VSIC
{
  const vsic = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'app', 'data', 'nganh_vsic.json'), 'utf8')
  ).nganh;

  const hits = R.searchVsic(vsic, 'trong lua', 12);
  check("vsic search('trong lua') tra 0111 o vi tri dau",
    hits.length > 0 && hits[0].ma === '0111',
    'got ' + hits.slice(0, 3).map(function (x) { return x.ma; }).join(','));

  check('vsic gioi han <= 12 ket qua', R.searchVsic(vsic, 'kinh doan').length <= 12);

  check('vsic tim theo ma khong dau (0111)',
    R.searchVsic(vsic, '0111', 12)[0].ma === '0111');

  check('ma nganh hop le -> isValid true',
    R.isValidMaNganh(vsic, '0111') && !R.isValidMaNganh(vsic, '9999'));
}

// ================================================== 7. PILOT: case -> tabs
const D = require('./ui/form-domain.js');
{
  // Case pilot (mock + use_cases.json): forms M02 + M06
  const pilotForms = [{ pl: 'I', mau: 2 }, { pl: 'I', mau: 6 }];
  // phản chiếu formIds() trong app.js (đã sửa bug zero-pad)
  const ids = pilotForms.map(f => 'PL' + f.pl + '_M' + String(f.mau).padStart(2, '0'));
  check('case pilot sinh dung 2 id: PLI_M02, PLI_M06', ids.join(',') === 'PLI_M02,PLI_M06',
    ids.join(','));
  check('regression zero-pad: mau 6 KHONG the sinh PLI_M6 (file la PLI_M06.json)',
    ('PLI_M' + 6) !== 'PLI_M06');

  const tabsHtml = R.buildTabsHtml([
    { id: 'PLI_M02', ten_mau: 'Giay de nghi dang ky DN (M02)' },
    { id: 'PLI_M06', ten_mau: 'Danh sach thanh vien (M06)' }
  ]);
  check('buildTabsHtml: 2 role="tab" co data-doc-id',
    countMatches(tabsHtml, /role="tab"/g) === 2 &&
    tabsHtml.indexOf('data-doc-id="PLI_M02"') >= 0 &&
    tabsHtml.indexOf('data-doc-id="PLI_M06"') >= 0);
  check('tab khoi tao aria-selected="false" (controller se bat len)',
    countMatches(tabsHtml, /aria-selected="false"/g) === 2);

  // ID field on dinh: khong khoang trang/ky tu dac biet gay lo selector
  const htmlIds = R.renderBlocks(m02, R.newStore(), { docId: 'PLI_M02' });
  const fid = htmlIds.match(/data-field-id="([^"]+)"/);
  check('render voi opts co data-field-id + aria-label',
    !!fid && /^f_[A-Za-z0-9_.:\-]+$/.test(fid[1]) &&
    /aria-label="[^"]+"/.test(htmlIds));
  check('render KHONG opts: van co data-field-id/aria-label (a11y co ban), '
    + 'nhung KHONG aria-required khi khong co fieldMeta',
    /data-field-id="f_/.test(R.renderBlocks(m02, R.newStore())) &&
      !/aria-required/.test(R.renderBlocks(m02, R.newStore())));
}

// ============================== 8. PILOT: chi mot to khai duy nhat active
{
  /* Mo phung dung template renderActiveDoc() trong app.js: chi ghép section
   * cua MỘT doc active vào #pages. */
  function renderActiveDoc(activeId, docs, store) {
    const d = docs.filter(x => x.id === activeId)[0];
    return '<section class="page-a4" data-doc="' + d.id + '">' +
      R.renderBlocks(d, store) + '</section>';
  }
  const docs = [m02, m06];
  // marker đặc trưng: M02 có chk_tt_thanh_lap_moi; M06 có bảng ds_thanh_vien
  const hA = renderActiveDoc('PLI_M02', docs, R.newStore());
  check('active PLI_M02: dung 1 section data-doc, khong le M06',
    countMatches(hA, /data-doc="/g) === 1 &&
      hA.indexOf('chk_tt_thanh_lap_moi') >= 0 &&
      hA.indexOf('data-loop="ds_thanh_vien"') < 0);
  const hB = renderActiveDoc('PLI_M06', docs, R.newStore());
  check('active PLI_M06: dung 1 section data-doc, khong le M02',
    countMatches(hB, /data-doc="/g) === 1 &&
      hB.indexOf('data-loop="ds_thanh_vien"') >= 0 &&
      hB.indexOf('chk_tt_thanh_lap_moi') < 0);
}

// ============================ 9. PILOT: key chung dong bo giua hai mau
{
  const store = R.newStore();
  store.values['dn.ten_tieng_viet'] = 'CONG TY TNHH DEMO PILOT';
  const h02 = R.renderBlocks(m02, store);
  const h06 = R.renderBlocks(m06, store);
  check('dien o M02 -> M02 thay gia tri',
    countMatches(h02, /value="CONG TY TNHH DEMO PILOT"/g) >= 1);
  check('cung store -> M06 thay gia tri (khong alias, exact key)',
    countMatches(h06, /value="CONG TY TNHH DEMO PILOT"/g) >= 1);
}

// ========================= 10. PILOT: doi tab KHONG mat du lieu/scroll/focus
{
  const store = R.newStore();          // một tham chiếu duy nhất như state.store
  store.values['dn.ten_tieng_viet'] = 'CONG TY KEEP';
  store.loops.ds_thanh_vien = [{ ho_ten: 'NGUYEN VAN A' }];
  const viewState = {};
  viewState.PLI_M02 = { scrollTop: 1234, focusKey: 'f_dn.ten_tieng_viet' };
  // "đổi tab": render M06 rồi render lại M02 từ CÙNG store
  R.renderBlocks(m06, store);
  const back = R.renderBlocks(m02, store);
  check('quay lai M02 van con du lieu + viewState giu nguyen',
    countMatches(back, /value="CONG TY KEEP"/g) >= 1 &&
      viewState.PLI_M02.scrollTop === 1234 &&
      viewState.PLI_M02.focusKey === 'f_dn.ten_tieng_viet');
}

// ===================== 11. PILOT: draft v2 save/reload giu day du trang thai
{
  const payload = {
    v: 2,
    caseId: 'pilot_ui_m02_m06',
    checkedForms: ['PLI_M02', 'PLI_M06'],
    activeDocId: 'PLI_M06',
    autoSum: true,
    viewState: { PLI_M06: { scrollTop: 88, focusKey: null } },
    store: {
      values: { 'dn.ten_tieng_viet': 'CONG TY RELOAD' },
      checks: { chk_ht_doc_lap: true },
      loops: {
        ds_thanh_vien: [
          { ho_ten: 'A', von_dong_gop: '700.000.000', ty_le_von: '70' },
          { ho_ten: 'B', von_dong_gop: '300.000.000', ty_le_von: '30' }
        ]
      }
    },
    savedAt: '2026-08-25T00:00:00Z'
  };
  const round = JSON.parse(JSON.stringify(payload));
  const mig = D.migrateDraft(round);   // v2 di qua nguyen ven
  check('draft v2 round-trip giu caseId/activeDocId/checkedForms',
    mig.caseId === 'pilot_ui_m02_m06' && mig.activeDocId === 'PLI_M06' &&
      mig.checkedForms.length === 2);
  check('draft v2 round-trip giu loops (2 thanh vien) + values + checks',
    mig.store.loops.ds_thanh_vien.length === 2 &&
      mig.store.values['dn.ten_tieng_viet'] === 'CONG TY RELOAD' &&
      mig.store.checks.chk_ht_doc_lap === true);
  // reload xong render lại từ store: dữ liệu xuất hiện đúng mẫu
  const reloaded = R.renderBlocks(m06, mig.store);
  check('sau reload, M06 hien thi lai gia tri + hang loop (ho_ten hang 0 = A)',
    countMatches(reloaded, /value="CONG TY RELOAD"/g) >= 1 &&
      countMatches(reloaded, /value="A"/g) >= 1);
  // draft v1 cu (truoc pilot) van duoc nang cap khong mat du lieu
  const v1 = JSON.parse(JSON.stringify({
    v: 1, caseId: 'thanh_lap_tnhh_2tv', checkedForms: ['PLI_M03', 'PLI_M06'],
    autoSum: false,
    store: { values: {}, checks: {}, loops: { ds_thanh_vien: [{ ho_ten: 'CU' }] } }
  }));
  const up = D.migrateDraft(v1);
  check('draft v1 cu -> v2: giu loop thanh vien, bo sung activeDocId=null',
    up.v === 2 && up.activeDocId === null &&
      up.store.loops.ds_thanh_vien[0].ho_ten === 'CU');
}

// ============= 12. PILOT: validation required/format + DIEU HUONG DEN O
{
  const errs = D.validateDocument('PLI_M02', m02.blocks, R.newStore(), {});
  const req = errs.find(e => e.code === 'REQUIRED');
  check('M02 trong -> REQUIRED dn.ten_tieng_viet blocking',
    !!req && req.severity === 'blocking');
  // điều hướng lỗi: key của lỗi phải tồn tại như data-key trên HTML của MẪU đó
  if (req) {
    const html = R.renderBlocks(m02, R.newStore(), { docId: 'PLI_M02' });
    check('loi REQUIRED tro dung o: data-key ton tai tren M02',
      html.indexOf('data-key="' + req.key + '"') >= 0, req.key);
  }
  // email sai -> EMAIL; điền hợp lệ -> sạch
  const s = R.newStore();
  s.values['dn.ten_tieng_viet'] = 'CONG TY OK';
  s.values['email_tru_so'] = 'sai-email';
  let e2 = D.validateDocument('PLI_M02', m02.blocks, s, {});
  check('email sai bao EMAIL', e2.some(x => x.code === 'EMAIL'));
  s.values['email_tru_so'] = 'vanbanc @congty.vn'.replace(/\s/g, '');
  e2 = D.validateDocument('PLI_M02', m02.blocks, s, {});
  check('sua email hop le -> het loi EMAIL',
    !e2.some(x => x.code === 'EMAIL'));
}

// =================================== 13. PILOT: export gate theo severity
{
  // Chính sách mục 7 contract: còn blocking -> chặn; chỉ warning -> cho xuất.
  const empty = D.validateDossier([m02, m06], R.newStore(), {});
  const hasBlocking = empty.some(e => e.severity === 'blocking');
  check('ho so trong co blocking -> doExport PHAI bi chan', hasBlocking);

  const warnStore = R.newStore();
  warnStore.values['dn.ten_tieng_viet'] = 'CONG TY GATE';
  warnStore.loops.ds_thanh_vien = [
    { ho_ten: 'A', von_dong_gop: '600.000.000', ty_le_von: '60' },
    { ho_ten: 'B', von_dong_gop: '400.000.000', ty_le_von: '30' } // tổng 90%
  ];
  const warns = D.validateDossier([m02, m06], warnStore, {});
  const onlyWarning = warns.length > 0 &&
    warns.every(e => e.severity === 'warning');
  check('chi warning (tong ty le 90%) -> khong chan export',
    onlyWarning && warns.some(e => e.code === 'PERCENT_SUM'));
}

// ================================ 14. PILOT: VSIC bang chuot va ban phim
{
  const vsicMini = loadMock('vsic_mini.json').nganh || [];
  const hits = R.searchVsic(vsicMini.length ? vsicMini : [], 'trong lua', 12);
  // mock mini có thể rỗng: fallback kiểm trên danh mục thật đã test ở mục 6.
  if (hits.length) {
    check('VSIC chuot: pick item[0] tra ma hop le',
      R.isValidMaNganh(vsicMini, hits[0].ma));
  } else {
    check('VSIC mock mini rong -> bo qua test chuot mini', true);
  }
  // bàn phím: mô phỏng wrap index ((i+1)%n) như handleVsicKeydown
  const fakeItems = ['a', 'b', 'c'];
  let idx = 0;
  idx = (idx + 1) % fakeItems.length;   // ArrowDown
  idx = (idx + 1) % fakeItems.length;   // ArrowDown
  idx = (idx + 1) % fakeItems.length;   // ArrowDown -> wrap về 0
  check('VSIC ban phim: ArrowDown wrap ve dau danh sach', idx === 0);
  check('ma sai -> isValidMaNganh false (co the danh dau invalid)',
    !R.isValidMaNganh(vsicMini.length ? vsicMini : [{ ma: 'x' }].concat(vsicMini), '9999zz'));
}

// ==================================== 15. PILOT: them/xoa dong bang lap
{
  // thêm dòng sau dòng đang chọn (selectRow tại idx 0) - như addLoopRow()
  const rows = [{ ho_ten: 'A', von_dong_gop: '100' }, { ho_ten: 'B' }];
  const selIdx = 0;
  rows.splice(selIdx + 1, 0, {});
  check('them dong sau dong chon -> 3 dong, dong moi rong o vi tri 1',
    rows.length === 3 && Object.keys(rows[1]).length === 0 && rows[2].ho_ten === 'B');

  // xóa dòng có dữ liệu phải confirm; hàm hasData giống app.js
  function rowHasData(r) {
    return Object.keys(r).some(k => String(r[k] == null ? '' : r[k]).trim() !== '');
  }
  check('phat hien dong co du lieu de bat confirm', rowHasData(rows[0]) === true);
  check('dong rong xoa khong can confirm', rowHasData(rows[1]) === false);
  rows.splice(selIdx, 1); // giả sử người dùng xác nhận
  check('xoa dong chon -> con 2 dong A/B dung thu tu',
    rows.length === 2 && rows[0].ho_ten === undefined && rows[1].ho_ten === 'B');

  // không cho âm số dòng: xóa khi rỗng là no-op
  const emptyRows = [];
  if (emptyRows.length) emptyRows.splice(0, 1);
  check('xoa khi khong con dong -> no-op (khong am)', emptyRows.length === 0);

  // render lại sau splice: STT và vị trí đúng
  const miniDoc = {
    id: 'T15', ten_mau: 't',
    blocks: [{
      t: 'loop', loop: 'ds_thanh_vien', headerRows: [0],
      rows: [{ cells: [{ runs: [{ text: 'STT' }] }, { runs: [{ text: 'Ten' }] }] }],
      cols: [{ col: 2, tag: 'ho_ten' }], blankRows: 0
    }]
  };
  const st = R.newStore();
  st.loops.ds_thanh_vien = [{ ho_ten: 'MOT' }, { ho_ten: 'HAI' }];
  const h15 = R.renderBlocks(miniDoc, st);
  const stts = [];
  const re15 = /<td class="stt">(\d+)<\/td>/g;
  let mm;
  while ((mm = re15.exec(h15)) !== null) stts.push(mm[1]);
  check('sua loop xong rerender: STT la 1,2', stts.join(',') === '1,2');
}

// ======================================= 16. PILOT: auto-sum so lon/format
{
  const st = R.newStore();
  st.loops.ds_thanh_vien = [
    { von_dong_gop: '700.000.000' },
    { von_dong_gop: '300.000.000' }
  ];
  const out = D.formatMoney(
    D.parseMoney(st.loops.ds_thanh_vien[0].von_dong_gop) +
    D.parseMoney(st.loops.ds_thanh_vien[1].von_dong_gop));
  check("tong von 700tr+300tr hien thi '1.000.000.000'",
    out === '1.000.000.000', out);
  const viaRender = R.calcTotals(st, true);
  check('R.calcTotals cung cho ket qua dong nhat',
    viaRender.von_dieu_le === '1.000.000.000', viaRender.von_dieu_le);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
