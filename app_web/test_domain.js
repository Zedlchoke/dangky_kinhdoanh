/* test_domain.js - unit test THUẦN cho app_web/ui/form-domain.js (không DOM).
 *
 * Chạy:  node app_web/test_domain.js
 *
 * Phủ mọi public API theo docs/htkk-ui-contract.md:
 *   parseMoney, formatMoney, getFieldMeta, getLoopMeta, collectKeys,
 *   validateField, validateDocument, validateDossier, isValidMaNganh,
 *   migrateDraft (v1 -> v2).
 *
 * GHI CHÚ CONTRACT MỚI (sync_mock_blocks sau khi production PLI_M02/M06 đổi):
 *  - PLI_M02 có bảng lặp thật "ds_nganh" (ma_nganh/ten_nganh/chi_tiet/
 *    la_nganh_chinh); tên cũ ds_nganh_kinh_doanh chỉ còn trong draft v1 và
 *    được migrateDraft đổi sang ds_nganh.
 *  - dn.ten_tieng_viet chỉ còn ở PLI_M02; PLI_M06 không còn field bắt buộc
 *    nào (các test REQUIRED tương ứng chuyển sang mẫu M02 - giữ nguyên ý định
 *    "mẫu trống chứa field bắt buộc -> lỗi blocking đúng key/docId").
 */
'use strict';

const fs = require('fs');
const path = require('path');
const D = require('./ui/form-domain.js');
const R = require('./ui/render.js');

const MOCK_DIR = path.join(__dirname, 'ui', 'mock');
function loadMock(name) {
  return JSON.parse(fs.readFileSync(path.join(MOCK_DIR, name), 'utf8'));
}

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}

// ------------------------------------------------------------ 1. money utils
check("parseMoney('1.000.000') === 1000000", D.parseMoney('1.000.000') === 1000000,
  D.parseMoney('1.000.000'));
check("parseMoney('1000000') === 1000000", D.parseMoney('1000000') === 1000000);
check("parseMoney(' 80.000.000 ') === 80000000", D.parseMoney(' 80.000.000 ') === 80000000);
check("parseMoney('50,5') === 50.5", Math.abs(D.parseMoney('50,5') - 50.5) < 1e-9);
check("parseMoney('(5.000)') === -5000", D.parseMoney('(5.000)') === -5000);
check("parseMoney('abc') === null", D.parseMoney('abc') === null);
check("parseMoney('') === null", D.parseMoney('') === null);
check('parseMoney(null) === null', D.parseMoney(null) === null);
check("parseMoney('chua nhap') === null", D.parseMoney('chua nhap') === null);

check("formatMoney(1000000) === '1.000.000'", D.formatMoney(1000000) === '1.000.000',
  D.formatMoney(1000000));
check("formatMoney(0) === '0'", D.formatMoney(0) === '0');
check("formatMoney(-25000) === '-25.000'", D.formatMoney(-25000) === '-25.000');
check("formatMoney(NaN) === ''", D.formatMoney(NaN) === '');
check('round-trip: format(parse(x)) ổn định',
  D.formatMoney(D.parseMoney('2.147.483.647')) === '2.147.483.647');

// --------------------------------------------------------- 2. field metadata
{
  const m = D.getFieldMeta('dn.ten_tieng_viet');
  check("getFieldMeta('dn.ten_tieng_viet').required === true", !!m && m.required === true);
  check("getFieldMeta('von_dieu_le').type === 'money'",
    D.getFieldMeta('von_dieu_le') && D.getFieldMeta('von_dieu_le').type === 'money');
  check("getFieldMeta('key_khong_ton_tai') === null",
    D.getFieldMeta('key_khong_ton_tai') === null);
  const lv = D.getLoopMeta('ds_thanh_vien');
  check('getLoopMeta(ds_thanh_vien).minRowsFilled === 2', !!lv && lv.minRowsFilled === 2);
  check('LOOP_META ds_thanh_vien có von_dong_gop là moneyTag',
    !!(lv && lv.moneyTags.indexOf('von_dong_gop') >= 0));
  // tương thích ngược: key cũ không metadata vẫn được collect và không lỗi
  check('metadata KHÔNG đổi key cũ (đếm số entry pilot <= 20)',
    Object.keys(D.FIELD_META).length > 0 && Object.keys(D.FIELD_META).length <= 20);
}

// ------------------------------------------------------------- 3. collectKeys
const m02 = loadMock('blocks_PLI_M02.json');
const m06 = loadMock('blocks_PLI_M06.json');
{
  const k02 = D.collectKeys(m02.blocks);
  const k06 = D.collectKeys(m06.blocks);
  check('collectKeys M02 có dn.ten_tieng_viet', k02.keys.indexOf('dn.ten_tieng_viet') >= 0);
  // production mới: tên công ty chỉ kê ở M02; M06 dùng key meta khác thật sự
  check('collectKeys M06 có ndd.ho_ten (key meta thay dn.ten_tieng_viet)',
    k06.keys.indexOf('ndd.ho_ten') >= 0 &&
      k06.keys.indexOf('dn.ten_tieng_viet') < 0);
  check('collectKeys M02 không trùng lặp key', new Set(k02.keys).size === k02.keys.length);
  check('collectKeys M06 loops.ds_thanh_vien có ho_ten',
    k06.loops.ds_thanh_vien && k06.loops.ds_thanh_vien.indexOf('ho_ten') >= 0);
  check('collectKeys M06 loops.ds_thanh_vien có von_dong_gop, ty_le_von',
    k06.loops.ds_thanh_vien.indexOf('von_dong_gop') >= 0 &&
    k06.loops.ds_thanh_vien.indexOf('ty_le_von') >= 0);
  // contract mới: loop ngành canonical là ds_nganh (tên cũ đã migrate)
  check('collectKeys M02 loops.ds_nganh có ma_nganh, ten_nganh, la_nganh_chinh (VSIC)',
    !!k02.loops.ds_nganh &&
    ['ma_nganh', 'ten_nganh', 'la_nganh_chinh'].every(t =>
      k02.loops.ds_nganh.indexOf(t) >= 0) &&
    !k02.loops.ds_nganh_kinh_doanh);
}

// ------------------------------------------------------------ 4. validateField
{
  let e = D.validateField({ key: 'dn.ten_tieng_viet', label: 'Tên công ty', required: true },
    '', { docId: 'PLI_M02' });
  check('required rỗng -> 1 lỗi REQUIRED blocking', e.length === 1 &&
    e[0].code === 'REQUIRED' && e[0].severity === 'blocking');
  check('lỗi có đủ contract fields {key,docId,code,message,severity}',
    ['key', 'docId', 'code', 'message', 'severity'].every(k => Object.prototype.hasOwnProperty.call(e[0], k)));
  check('lỗi gắn đúng docId', e[0].docId === 'PLI_M02');

  e = D.validateField({ key: 'dn.ten_tieng_viet', required: true }, 'CONG TY A', {});
  check('required có giá trị -> 0 lỗi', e.length === 0);

  const em = { key: 'email_tru_so', type: 'email' };
  check('email hợp lệ -> 0 lỗi', D.validateField(em, 'a@b.com.vn', {}).length === 0);
  check('email sai -> EMAIL', D.validateField(em, 'khong-phai-email', {})[0].code === 'EMAIL');

  const cc = { key: 'chu_hkd.so_cccd', type: 'cccd' };
  check('CCCD 12 số -> 0 lỗi', D.validateField(cc, '012345678901', {}).length === 0);
  check('CCCD 9 số -> 0 lỗi', D.validateField(cc, '012345678', {}).length === 0);
  check('CCCD 8 số -> CCCD error', D.validateField(cc, '12345678', {})[0].code === 'CCCD');
  check('CCCD chữ -> CCCD error', D.validateField(cc, 'abc-def', {})[0].code === 'CCCD');

  const ms = { key: 'dn.ma_so_dn', type: 'mst' };
  check('MST 10 số -> 0 lỗi', D.validateField(ms, '0123456789', {}).length === 0);
  check('MST 13 số cú pháp 10-3 -> 0 lỗi', D.validateField(ms, '0123456789-001', {}).length === 0);
  check('MST 11 số -> MST error', D.validateField(ms, '01234567891', {})[0].code === 'MST');

  const mn = { key: 'von_dieu_le', type: 'money' };
  check("money '5.000.000' -> 0 lỗi", D.validateField(mn, '5.000.000', {}).length === 0);
  check("money 'năm triệu' -> MONEY", D.validateField(mn, 'nam trieu', {})[0].code === 'MONEY');

  const num = { key: 'so_lao_dong', type: 'number' };
  check("number '25' -> 0 lỗi", D.validateField(num, '25', {}).length === 0);
  check("number '25a' -> NUMERIC", D.validateField(num, '25a', {})[0].code === 'NUMERIC');

  const vsicMeta = { key: 'ds_nganh_kinh_doanh.ma_nganh', type: 'vsic' };
  const vsicFake = [{ ma: '0111', ten: 'Trồng lúa', cap: 4 }];
  check('vsic mã hợp lệ -> 0 lỗi',
    D.validateField(vsicMeta, '0111', { vsicList: vsicFake }).length === 0);
  check('vsic mã sai -> VSIC',
    D.validateField(vsicMeta, '9999', { vsicList: vsicFake })[0].code === 'VSIC');
  // text thường không bắt buộc: giá trị bất kỳ đều qua
  check('text tuỳ chọn không check format',
    D.validateField({ key: 'dia_chi_chi_tiet', type: 'text' }, 'giá trị gì cũng được', {}).length === 0);
}

// ------------------------------------------------------- 5. validateDocument
{
  // Ý định giữ nguyên: mẫu trống chứa field bắt buộc -> REQUIRED blocking đúng
  // key/docId. Production mới: dn.ten_tieng_viet chỉ còn ở M02 (xem ghi chú
  // đầu file), nên assertion chuyển sang M02; M06 trống giờ sạch hoàn toàn.
  let errs = D.validateDocument('PLI_M02', m02.blocks, R.newStore(), {});
  let req = errs.find(e => e.code === 'REQUIRED');
  check('M02 trống -> có REQUIRED dn.ten_tieng_viet blocking',
    !!req && req.key === 'dn.ten_tieng_viet' && req.severity === 'blocking' &&
    req.docId === 'PLI_M02');
  check('M06 trống -> KHÔNG MIN_ROWS (bảng chưa điền)',
    !errs.some(e => e.code === 'MIN_ROWS') &&
    !D.validateDocument('PLI_M06', m06.blocks, R.newStore(), {})
      .some(e => e.code === 'MIN_ROWS'));

  // 1 thành viên -> MIN_ROWS
  const s1 = R.newStore();
  s1.values['dn.ten_tieng_viet'] = 'CONG TY TNHH HAI THANH VIEN';
  s1.loops.ds_thanh_vien = [{ ho_ten: 'NGUYEN VAN A', von_dong_gop: '500.000.000', ty_le_von: '100' }];
  errs = D.validateDocument('PLI_M06', m06.blocks, s1, {});
  const mr = errs.find(e => e.code === 'MIN_ROWS');
  check('M06 1 thành viên -> MIN_ROWS blocking', !!mr && mr.severity === 'blocking' &&
    mr.docId === 'PLI_M06' && mr.key === 'ds_thanh_vien');

  // 2 thành viên đầy đủ -> sạch
  const s2 = R.newStore();
  s2.values['dn.ten_tieng_viet'] = 'CONG TY TNHH HAI THANH VIEN';
  s2.loops.ds_thanh_vien = [
    { ho_ten: 'NGUYEN VAN A', von_dong_gop: '700.000.000', ty_le_von: '70' },
    { ho_ten: 'TRAN THI B', von_dong_gop: '300.000.000', ty_le_von: '30' }
  ];
  errs = D.validateDocument('PLI_M06', m06.blocks, s2, {});
  check('M06 2 thành viên tỷ lệ 70/30 -> 0 lỗi', errs.length === 0,
    JSON.stringify(errs));

  // tiền rác + tỷ lệ lệch
  const s3 = R.newStore();
  s3.values['dn.ten_tieng_viet'] = 'CONG TY X';
  s3.loops.ds_thanh_vien = [
    { ho_ten: 'A', von_dong_gop: 'nam chuc trieu', ty_le_von: '60' },
    { ho_ten: 'B', von_dong_gop: '30000000', ty_le_von: '30' }
  ];
  errs = D.validateDocument('PLI_M06', m06.blocks, s3, {});
  const me = errs.find(e => e.code === 'MONEY');
  const pe = errs.find(e => e.code === 'PERCENT_SUM');
  check('tiền rác trong dòng -> MONEY blocking', !!me && me.severity === 'blocking');
  check('tỷ lệ 60+30=90 -> PERCENT_SUM warning (không chặn)',
    !!pe && pe.severity === 'warning');

  // checkbox key không sinh lỗi validateField
  const s4 = R.newStore();
  s4.values['dn.ten_tieng_viet'] = 'CONG TY Y';
  s4.checks['chk_ht_doc_lap'] = true;
  errs = D.validateDocument('PLI_M06', m06.blocks, s4, {});
  check('checkbox tick không sinh lỗi', !errs.some(e => e.key === 'chk_ht_doc_lap'));

  // dedupe cùng key xuất hiện nhiều lần trong một mẫu
  const docDup = {
    id: 'DUP', ten_mau: 'dup',
    blocks: [
      { t: 'p', runs: [{ input: { key: 'email_tru_so', w: 10 } }] },
      { t: 'p', runs: [{ input: { key: 'email_tru_so', w: 10 } }] }
    ]
  };
  errs = D.validateDocument('DUP', docDup.blocks,
    { values: { email_tru_so: 'sai-email' }, checks: {}, loops: {} }, {});
  check('cùng key 2 chỗ -> chỉ 1 lỗi EMAIL (dedupe)',
    errs.filter(e => e.code === 'EMAIL').length === 1);
}

// -------------------------------------------------------- 6. validateDossier
{
  // Cả hai mẫu phải góp lỗi: M02 lỗi ds_nganh bắt buộc (INDUSTRY_REQUIRED),
  // M06 lỗi MIN_ROWS (1/2 thành viên) - tên công ty đã điền nên không còn
  // REQUIRED che các lỗi kia.
  const store = R.newStore();
  store.values['dn.ten_tieng_viet'] = 'CONG TY CO LOI O HAI MAU';
  store.loops.ds_thanh_vien = [
    { ho_ten: 'NGUYEN VAN A', von_dong_gop: '500.000.000', ty_le_von: '100' }];
  const errs = D.validateDossier([m02, m06], store, {});
  const byDoc = {};
  errs.forEach(e => { byDoc[e.docId] = (byDoc[e.docId] || 0) + 1; });
  check('validateDossier gộp lỗi từ M02 và M06',
    byDoc.PLI_M02 > 0 && byDoc.PLI_M06 > 0, JSON.stringify(byDoc));
  const blockingCount = errs.filter(e => e.severity === 'blocking').length;
  check('hồ sơ trống có ít nhất 1 lỗi blocking (chặn export)', blockingCount >= 1);

  // hồ sơ hợp lệ: M02 đủ tên + ds_nganh có ngành chính; M06 2 thành viên 70/30
  const ok = R.newStore();
  ok.values['dn.ten_tieng_viet'] = 'CONG TY TNHH DEMO';
  ok.loops.ds_nganh = [
    { ma_nganh: '6201', ten_nganh: 'Lập trình máy vi tính', la_nganh_chinh: 'X' }];
  ok.loops.ds_thanh_vien = [
    { ho_ten: 'NGUYEN VAN A', von_dong_gop: '700.000.000', ty_le_von: '70' },
    { ho_ten: 'TRAN THI B', von_dong_gop: '300.000.000', ty_le_von: '30' }
  ];
  check('hồ sơ demo hợp lệ -> 0 lỗi',
    D.validateDossier([m02, m06], ok, {}).length === 0,
    JSON.stringify(D.validateDossier([m02, m06], ok, {})));
}

// ------------------------------------------------------------ 7. migrateDraft
{
  const v1 = {
    v: 1, caseId: 'thanh_lap_tnhh_1tv',
    checkedForms: ['PLI_M02'], autoSum: true,
    store: { values: { a: '1' }, checks: { b: true }, loops: { L: [{ x: '2' }] } }
  };
  const up = D.migrateDraft(v1);
  check('migrateDraft v1 -> v2', up.v === 2);
  check('migrate giữ caseId/checkedForms/autoSum',
    up.caseId === 'thanh_lap_tnhh_1tv' && up.checkedForms[0] === 'PLI_M02' && up.autoSum === true);
  check('migrate giữ nguyên dữ liệu store',
    up.store.values.a === '1' && up.store.checks.b === true && up.store.loops.L[0].x === '2');
  check('migrate bổ sung activeDocId=null, viewState={}',
    up.activeDocId === null && typeof up.viewState === 'object');

  const v2 = { v: 2, activeDocId: 'PLI_M06', store: { values: {}, checks: {}, loops: {} } };
  check('draft v2 đi qua nguyên vẹn (same object)', D.migrateDraft(v2) === v2);
  check('draft rác/junk -> null', D.migrateDraft(null) === null &&
    D.migrateDraft({ foo: 1 }) === null);
  check('draft thiếu store -> null', D.migrateDraft({ v: 1, caseId: 'x' }) === null);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
