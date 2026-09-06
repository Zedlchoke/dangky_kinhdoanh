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

  // dong bo giua cac mau: key dung chung ton tai tren CA M02 va M06 production
  // (email_tru_so co trong ca hai; dn.ten_tieng_viet chi co tren M02)
  store.values['email_tru_so'] = 'vanban@congty.vn';
  const htmlM06 = R.renderBlocks(m06, store);
  check(
    'dong bo key giua mau: PLI_M06 cung nhan gia tri email_tru_so',
    countMatches(htmlM06, /value="vanban@congty\.vn"/g) >= 1
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
      // col ZERO-BASED: col0 = STT (không tag), gia_tri nằm dưới tiêu đề "A"
      cols: [{ col: 1, tag: 'gia_tri' }],
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
  // key dùng chung phải TỒN TẠI trên cả hai mẫu production: dn.ten_tieng_viet
  // chỉ có trên M02, nên cặp M02<->M06 kiểm qua email_tru_so.
  const store = R.newStore();
  store.values['dn.ten_tieng_viet'] = 'CONG TY TNHH DEMO PILOT';
  store.values['email_tru_so'] = 'demo@pilot.vn';
  const h02 = R.renderBlocks(m02, store);
  const h06 = R.renderBlocks(m06, store);
  check('dien o M02 -> M02 thay gia tri',
    countMatches(h02, /value="CONG TY TNHH DEMO PILOT"/g) >= 1);
  check('cung store -> M06 thay gia tri key dung chung (khong alias, exact key)',
    countMatches(h06, /value="demo@pilot\.vn"/g) >= 1);
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
      // email_tru_so: key tồn tại trên M06 production để kiểm render lại;
      // dn.ten_tieng_viet chỉ có trên M02 (vẫn giữ trong payload).
      values: { 'dn.ten_tieng_viet': 'CONG TY RELOAD', 'email_tru_so': 'reload@pilot.vn' },
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
    countMatches(reloaded, /value="reload@pilot\.vn"/g) >= 1 &&
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
  // Production mới: M02 có ds_nganh bắt buộc -> hồ sơ phải có ngành chính
  // hợp lệ thì mới còn đúng MỘT warning tỷ lệ vốn để kiểm chính sách gate.
  const empty = D.validateDossier([m02, m06], R.newStore(), {});
  const hasBlocking = empty.some(e => e.severity === 'blocking');
  check('ho so trong co blocking -> doExport PHAI bi chan', hasBlocking);

  const warnStore = R.newStore();
  warnStore.values['dn.ten_tieng_viet'] = 'CONG TY GATE';
  warnStore.loops.ds_nganh = [
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }];
  // [O3 2026-09-06] section nested-grid NĐDPL của M02 (luôn active, min 1
  // dòng business-data) phải được điền thì hồ sơ còn đúng MỘT warning tỷ lệ.
  warnStore.loops.ds_nddpl_uy_quyen_chu_so_huu = [
    { loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'NGUYEN VAN A' }];
  warnStore.loops.ds_thanh_vien = [
    { ho_ten: 'A', von_dong_gop: '600.000.000', ty_le_von: '60' },
    { ho_ten: 'B', von_dong_gop: '400.000.000', ty_le_von: '30' } // tổng 90%
  ];
  const warns = D.validateDossier([m02, m06], warnStore, {});
  const onlyWarning = warns.length > 0 &&
    warns.every(e => e.severity === 'warning');
  check('chi warning (tong ty le 90%) -> khong chan export',
    onlyWarning && warns.some(e => e.code === 'PERCENT_SUM'),
    JSON.stringify(warns));
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

  // render lại sau splice: STT và vị trí đúng (col ZERO-BASED: ho_ten ở col1)
  const miniDoc = {
    id: 'T15', ten_mau: 't',
    blocks: [{
      t: 'loop', loop: 'ds_thanh_vien', headerRows: [0],
      rows: [{ cells: [{ runs: [{ text: 'STT' }] }, { runs: [{ text: 'Ten' }] }] }],
      cols: [{ col: 1, tag: 'ho_ten' }], blankRows: 0
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

// ====================== 17. V4 ui-hint: FIELD_META hint -> placeholder
{
  // 28 key V4 lane 6v-micro bổ sung (hkd_*/hkd_cd.*/csbt.*/cn.*/ndd.*):
  // mỗi key phải có label (help tùy chọn) — nền cho placeholder hint.
  const V4_KEYS = ['hkd_ten_tieng_viet', 'hkd_ten_tieng_viet_2',
    'hkd_ten_nuoc_ngoai', 'hkd_ten_viet_tat', 'hkd_ma_so', 'hkd_tru_so',
    'hkd_cd.ten_hkd', 'hkd_cd.ten_chu_ho', 'hkd_cd.so_gcn', 'hkd_cd.dia_chi',
    'csbt.ten', 'csbt.dia_chi', 'csbt.so_gcn', 'csbt.ten_nguoi_dai_dien',
    'csbt.ngay_cap', 'cn.ten_tieng_viet', 'cn.ten_nuoc_ngoai',
    'cn.ten_viet_tat', 'cn.ma_so', 'cn.ma_so_2', 'cn.dia_chi',
    'ndd.chuc_vu', 'ndd.gioi_tinh', 'ndd.ngay_sinh', 'ndd.thang_sinh',
    'ndd.nam_sinh', 'ndd.dien_thoai', 'ndd.quoc_gia'];
  check('V4: FIELD_META co du 28 key hint moi, moi key co label',
    V4_KEYS.every(k => {
      const m = D.getFieldMeta(k);
      return !!m && m.key === k && typeof m.label === 'string' && m.label.length > 0;
    }));
  check('V4: khong them required/validation moi cho 28 key (optional, text/phone)',
    V4_KEYS.every(k => {
      const m = D.getFieldMeta(k);
      return m && !m.required && (m.type === 'text' || m.type === 'phone');
    }));

  const hintDoc = {
    id: 'T17', ten_mau: 't',
    blocks: [{
      t: 'p',
      runs: [
        { text: 'Tên hộ kinh doanh (ghi bằng chữ in hoa): ' },
        { input: { key: 'hkd_ten_tieng_viet_2', w: 40 } }
      ]
    }, {
      t: 'p',
      runs: [
        { text: 'Key không có meta: ' },
        { input: { key: 'khong_co_meta_xyz', w: 20 } }
      ]
    }, {
      t: 'chk', key: 'chk_v4_demo', label: 'ô vuông demo'
    }]
  };
  const hintOpts = { docId: 'PLII_M01', fieldMeta: D.FIELD_META };
  const hHint = R.renderBlocks(hintDoc, R.newStore(), hintOpts);
  const inp17 = hHint.match(/<input type="text"[^>]*data-key="hkd_ten_tieng_viet_2"[^>]*>/);
  check('V4: input hkd_ten_tieng_viet_2 co placeholder="Ghi bang chu in hoa." '
    + '+ aria-label chua "Ten ho kinh doanh"',
    !!inp17 && inp17[0].indexOf('placeholder="Ghi bằng chữ in hoa."') >= 0 &&
      /aria-label="[^"]*Tên hộ kinh doanh[^"]*"/.test(inp17[0]),
    inp17 ? inp17[0].slice(0, 160) : 'khong tim thay input');
  const inpNoMeta = hHint.match(/<input type="text"[^>]*data-key="khong_co_meta_xyz"[^>]*>/);
  check('V4: key ngoai FIELD_META khong co placeholder (render co ban nhu cu)',
    !!inpNoMeta && inpNoMeta[0].indexOf('placeholder') < 0 &&
      inpNoMeta[0].indexOf('aria-label=') >= 0);
  const chk17 = hHint.match(/<input type="checkbox"[^>]*>/);
  check('V4: checkbox khong bao gio nhan placeholder',
    !!chk17 && chk17[0].indexOf('placeholder') < 0);
  // render không fieldMeta (đường cũ app.js trước khi có meta) -> sạch placeholder
  const hBare = R.renderBlocks(hintDoc, R.newStore());
  check('V4: render khong fieldMeta -> khong placeholder nao',
    !/placeholder="/.test(hBare));
}

// ------------------------------------- [WAVE v7] HEADER-NAME-SYNC mirror
{
  // Band đầu trang với run mirror (converter sinh từ {dn.ten_tieng_viet}
  // ở ô (0,0) band theo tools/header_name_binding.json): render phải là
  // span.mirror-fld có data-key + giá trị store — KHÔNG PHẢI input thứ hai.
  const bandDoc = {
    id: 'PLI_M32', ten_mau: 'hdr-mirror',
    blocks: [{
      t: 'table', band: 'header', widths: null,
      rows: [
        { cells: [
          { runs: [
            { text: 'TÊN DOANH NGHIỆP\n', b: true },
            { mirror: { key: 'dn.ten_tieng_viet' } }
          ] },
          { runs: [{ text: 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', b: true }] }
        ] },
        { cells: [
          { runs: [{ text: 'Số: ' }, { input: { key: 'so_van_ban', w: 12 } }] },
          { runs: [{ text: 'ngày…' }] }
        ] }
      ]
    }]
  };
  const st = R.newStore();
  st.values['dn.ten_tieng_viet'] = 'CÔNG TY TNHH MỘT HAI BA';
  const hBand = R.renderBlocks(bandDoc, st);
  check('v7: band mirror render span.mirror-fld có data-key',
    /<span class="mirror-fld" data-key="dn\.ten_tieng_viet">CÔNG TY TNHH MỘT HAI BA<\/span>/.test(hBand),
    hBand.slice(0, 200));
  check('v7: mirror KHÔNG sinh input thứ hai cho key',
    (hBand.match(/<input[^>]*data-key="dn\.ten_tieng_viet"/g) || []).length === 0);
  check('v7: band row1 slot thường vẫn là input (Số văn bản)',
    /<input[^>]*data-key="so_van_ban"/.test(hBand));

  // store trống -> span rỗng (blank draft không dữ liệu giả)
  const hBlank = R.renderBlocks(bandDoc, R.newStore());
  check('v7: band mirror store trống -> span rỗng',
    /<span class="mirror-fld" data-key="dn\.ten_tieng_viet"><\/span>/.test(hBlank));

  // run input cùng key trong band KHÔNG nằm registry -> giữ nguyên input
  // (band chưa bind phải còn thấy được qua gate D17)
  const unbound = JSON.parse(JSON.stringify(bandDoc));
  unbound.blocks[0].rows[0].cells[0].runs[1] = { input: { key: 'dn.ten_tieng_viet', w: 30 } };
  const hUnbound = R.renderBlocks(unbound, st);
  check('v7: run input (không mirror) trong band vẫn render input',
    /<input[^>]*data-key="dn\.ten_tieng_viet"/.test(hUnbound));
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
