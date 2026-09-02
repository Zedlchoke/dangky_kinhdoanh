/* test_validation_contact.js — LANE fix-industry (Wave D batch 1): Class 14
 * "validation gap 20 form" (Wave C finding F1, Lead xác minh).
 *
 * Chạy:  node app_web/test_validation_contact.js
 *
 * ĐỎ TRƯỚC khi sửa: các field liên hệ dùng chung (email_khac, dien_thoai_khac,
 * fax, website) KHÔNG có metadata/rule nào trong FIELD_META nên rác in thẳng
 * vào DOCX; cột so_cccd của loop ds_co_dong_sang_lap (PLI_M07) nhận text rác
 * không lỗi. Sửa ở ĐÚNG LỚP: FIELD_META dùng chung + validator theo type
 * (form-domain.js) — KHÔNG liệt kê tay từng form.
 *
 * Phạm vi: ĐỦ 20 form PLII_M08/10/11/12/14/16/19/20/21/22/23/25/28,
 * PLI_M07/47/50/51/52/53/76 — test chạy THẬT blocks production từng form.
 *
 * Contract lỗi (chuẩn M01/M02 như email_tru_so):
 *  - sai format  -> error severity 'blocking', code đúng loại (EMAIL/PHONE/
 *    WEBSITE/CCCD), key === canonical key của field (findErrorField/
 *    navigateToError mở đúng tab + focus đúng ô qua [data-key]);
 *  - rỗng        -> KHÔNG lỗi (field không bắt buộc);
 *  - hợp lệ      -> KHÔNG lỗi.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const FD = require('./ui/form-domain.js');

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}

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

function newStore() { return { values: {}, checks: {}, loops: {} }; }

const FORMS_20 = [
  'PLII_M08', 'PLII_M10', 'PLII_M11', 'PLII_M12', 'PLII_M14', 'PLII_M16',
  'PLII_M19', 'PLII_M20', 'PLII_M21', 'PLII_M22', 'PLII_M23', 'PLII_M25',
  'PLII_M28', 'PLI_M07', 'PLI_M47', 'PLI_M50', 'PLI_M51', 'PLI_M52',
  'PLI_M53', 'PLI_M76'
];

/* {key: [loại, giá trị RÁC, giá trị HỢP LỆ, code mong đợi]} - field liên hệ
 * dùng chung bởi contact-block template của 19/20 form (PLI_M07 riêng chỉ
 * thiếu nhóm này, có ds_co_dong_sang_lap). */
const CONTACT_RULES = {
  email_khac: {
    type: 'email', code: 'EMAIL',
    garbage: 'khong-phai-email', valid: 'nguoi_dai_dien@congty.com.vn'
  },
  dien_thoai_khac: {
    type: 'phone', code: 'PHONE',
    garbage: 'dt: (028) 3825abc', valid: '0903 456 789'
  },
  fax: {
    type: 'phone', code: 'PHONE',
    garbage: 'fax=84-24-abcde', valid: '(028).3825-3123'
  },
  website: {
    type: 'website', code: 'WEBSITE',
    garbage: 'khong phai url', valid: 'https://congty.vn/lien-he?x=1'
  }
};

/* Lỗi blocking của ĐÚNG field (key === canonical key như email_tru_so) */
function fieldErrors(docId, blocks, store) {
  return FD.validateDocument(docId, blocks, store, {}).filter(e =>
    e.severity === 'blocking' &&
    Object.prototype.hasOwnProperty.call(CONTACT_RULES, e.key));
}

// ================================================= A. FIELD_META dùng chung
section('A. FIELD_META dùng chung có metadata cho 4 field liên hệ');

Object.keys(CONTACT_RULES).forEach(key => {
  const meta = FD.getFieldMeta(key);
  check(`A getFieldMeta('${key}') tồn tại (trước đây null -> rác không lỗi)`,
    !!meta, JSON.stringify(meta));
  if (meta) {
    check(`A '${key}' đúng type '${CONTACT_RULES[key].type}'`,
      meta.type === CONTACT_RULES[key].type, String(meta.type));
    check(`A '${key}' KHÔNG bắt buộc (rỗng hợp lệ)`,
      meta.required !== true, JSON.stringify(meta));
  }
});

// ================================================= B. validator theo type
section('B. validateField: email/phone/website + thông điệp tiếng Việt');

{
  /* Trả true khi validateField(metaKey, value) ra ĐÚNG 1 lỗi code mong đợi
   * (chịu lỗi khi meta chưa tồn tại — để thấy toàn cảnh ĐỎ thay vì crash). */
  const isErr = (k, v, code) => {
    const meta = FD.getFieldMeta(k);
    if (!meta) return false;
    const errs = FD.validateField(meta, v, {});
    return errs.length === 1 && errs[0].code === code;
  };
  const noErr = (k, v) => {
    const meta = FD.getFieldMeta(k);
    return !!meta && FD.validateField(meta, v, {}).length === 0;
  };

  check('B email_khac rác -> EMAIL', isErr('email_khac', CONTACT_RULES.email_khac.garbage, 'EMAIL'));
  check('B email_khac hợp lệ -> 0 lỗi',
    noErr('email_khac', CONTACT_RULES.email_khac.valid));
  check('B dien_thoai_khac chữ -> PHONE', isErr('dien_thoai_khac', 'abc def', 'PHONE'));
  check('B dien_thoai_khac khoảng trắng/gạch/ngoặc hợp lệ',
    noErr('dien_thoai_khac', '0903 456 789') &&
      noErr('dien_thoai_khac', '(028).3825-3123') &&
      noErr('dien_thoai_khac', '+84-24-38253123'));
  check('B dien_thoai_khac quá ngắn (7 số) -> PHONE',
    isErr('dien_thoai_khac', '0123456', 'PHONE'));
  check('B fax nhận số máy lọc chữ (0-9 và .-()+) -> 0 lỗi',
    noErr('fax', '84-24-38253123'));
  check('B fax rác -> PHONE', isErr('fax', 'khong co so', 'PHONE'));
  check('B website www.domain hợp lệ', noErr('website', 'www.congty.vn'));
  check('B website có scheme/path/query hợp lệ',
    noErr('website', 'https://congty.vn/lien-he?x=1'));
  check('B website rác/có khoảng trắng -> WEBSITE',
    isErr('website', 'khong phai url', 'WEBSITE') &&
      isErr('website', 'http://', 'WEBSITE') &&
      isErr('website', 'a b.c', 'WEBSITE'));
  const mPh = FD.getFieldMeta('dien_thoai_khac');
  const mWs = FD.getFieldMeta('website');
  const ph = mPh ? FD.validateField(mPh, 'abc', {}) : [];
  const ws = mWs ? FD.validateField(mWs, 'khong phai url', {}) : [];
  check('B thông điệp tiếng Việt dễ hiểu (có mô tả + giá trị rác)',
    ph.length === 1 && /điện thoại|số/i.test(ph[0].message) &&
      ph[0].message.includes('abc') &&
      ws.length === 1 && /website/i.test(ws[0].message) &&
      ws[0].message.includes('khong phai url'),
    JSON.stringify([ph[0] && ph[0].message, ws[0] && ws[0].message]));
}

// ================================================= C. chạy THẬT từng form trong 20
section('C. 20 form: rác -> blocking error đúng key; hợp lệ -> sạch');

FORMS_20.forEach(docId => {
  let doc;
  try { doc = loadProd(docId); } catch (e) {
    check(`C ${docId} nạp được blocks production`, false, String(e));
    return;
  }
  const present = Object.keys(CONTACT_RULES).filter(k =>
    FD.collectKeys(doc.blocks).keys.indexOf(k) >= 0);

  if (docId !== 'PLI_M07') {
    check(`C ${docId}: đủ 4 field liên hệ trong blocks (contact-block dùng chung)`,
      present.length === 4, JSON.stringify(present));
  }

  // rác từng field -> ĐÚNG 1 blocking error, đúng key + code
  const badDetails = [];
  let badOk = true;
  present.forEach(k => {
    const store = newStore();
    store.values[k] = CONTACT_RULES[k].garbage;
    const errs = fieldErrors(docId, doc.blocks, store);
    const hit = errs.filter(e => e.key === k && e.code === CONTACT_RULES[k].code);
    if (errs.length !== 1 || !hit.length) {
      badOk = false;
      badDetails.push(k + '->' + JSON.stringify(errs.map(e => [e.key, e.code])));
    }
  });
  check(`C ${docId}: rác ${present.length} field -> blocking error đúng key+code`,
    badOk, badDetails.join(' | '));

  // giá trị hợp lệ + rỗng -> KHÔNG lỗi nào trên nhóm field liên hệ
  const good = newStore();
  present.forEach(k => { good.values[k] = CONTACT_RULES[k].valid; });
  const errsGood = fieldErrors(docId, doc.blocks, good);
  check(`C ${docId}: giá trị hợp lệ -> 0 lỗi nhóm liên hệ`,
    errsGood.length === 0, JSON.stringify(errsGood.map(e => e.key)));

  // key focus: lỗi trỏ đúng [data-key] (chuẩn navigateToError M01/M02)
  if (present.length) {
    const store = newStore();
    store.values[present[0]] = CONTACT_RULES[present[0]].garbage;
    const errs = fieldErrors(docId, doc.blocks, store);
    check(`C ${docId}: error.key === canonical key (focus đúng field/tab)`,
      errs.length === 1 && errs[0].key === present[0],
      JSON.stringify(errs.map(e => e.key)));
  }
});

// ================================================= D. so_cccd trong ds_co_dong_sang_lap
section('D. PLI_M07: cột so_cccd của ds_co_dong_sang_lap (root fix ở GRID_META)');

{
  const doc = loadProd('PLI_M07');
  const g = FD.getGridMeta({ docId: 'PLI_M07', loop: 'ds_co_dong_sang_lap' }) ||
    FD.getGridMeta('ds_co_dong_sang_lap');
  check('D grid meta ds_co_dong_sang_lap tồn tại', !!g);
  const col = g && (g.columns || []).filter(c => c.tag === 'so_cccd')[0];
  check('D cột so_cccd type "cccd" (trước đây "text" nhận rác)',
    !!col && col.type === 'cccd', col && col.type);

  const rowId = 'rctest1';
  const mkStore = (cccd) => ({
    values: {}, checks: {},
    loops: { ds_co_dong_sang_lap: [
      { _row_id: rowId, ho_ten: 'NGUYEN VAN A', so_cccd: cccd,
        dia_chi: 'Hà Nội', so_co_phan: '1.000', ty_le: '100' }
    ] }
  });
  const cccdErrs = (v) => FD.validateDocument('PLI_M07', doc.blocks, mkStore(v), {})
    .filter(e => e.code === 'CCCD');

  const bad = cccdErrs('so cccnd lam rác');
  check('D so_cccd chữ rác -> CCCD blocking, trỏ đúng ô theo _row_id',
    bad.length === 1 && bad[0].severity === 'blocking' &&
      bad[0].key === 'loop:ds_co_dong_sang_lap:' + rowId + ':so_cccd' &&
      /9 hoặc 12 số/.test(bad[0].message),
    JSON.stringify(bad));

  check('D so_cccd 12 số hợp lệ -> 0 lỗi CCCD',
    cccdErrs('012345678901').length === 0);
  check('D so_cccd 9 số hợp lệ -> 0 lỗi CCCD',
    cccdErrs('012345678').length === 0);
  check('D so_cccd có khoảng trắng/gạch phân cách 12 số -> 0 lỗi CCCD',
    cccdErrs('0123 4567 8901').length === 0 && cccdErrs('0123-4567-8901').length === 0);
  check('D so_cccd 11 số (độ dài lạ) -> CCCD blocking',
    cccdErrs('01234567890').length === 1);
  check('D so_cccd rỗng -> KHÔNG lỗi (không bắt buộc ở mức này)',
    cccdErrs('').length === 0);

  // Không hồi quy: các bảng người dùng chung vẫn validate so_cccd khi có rác
  // (PLI_M06 blocks chứa loop ds_thanh_vien_tnhh với cột so_cccd)
  const doc2 = loadProd('PLI_M06');
  const st2 = { values: {}, checks: {}, loops: { ds_thanh_vien_tnhh: [
    { _row_id: 'rtv1', ho_ten: 'A', so_cccd: 'rac chu', von_dong_gop: '1000' }
  ] } };
  const tvErrs = FD.validateDocument('PLI_M06', doc2.blocks, st2, {})
    .filter(e => e.code === 'CCCD');
  check('D ds_thanh_vien_tnhh.so_cccd rác -> CCCD blocking (cùng meta dùng chung)',
    tvErrs.length === 1 &&
      tvErrs[0].key === 'loop:ds_thanh_vien_tnhh:rtv1:so_cccd',
    JSON.stringify(tvErrs));
}

// ================================================= tổng kết
console.log('\n=========================================');
console.log('PASSED: ' + passed + '  FAILED: ' + failed);
process.exit(failed ? 1 : 0);
