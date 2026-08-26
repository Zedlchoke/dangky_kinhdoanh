/* test_p20_hardening.js - P2.0 HARDENING (Agent B).
 *
 * Ba nhóm hardening trên app_web/ui/form-domain.js + ui/app.js:
 *  S1. mkGrid DEEP CLONE: meta lấy từ getGridMeta() (mkGrid sinh ra) KHÔNG
 *      chia sẻ tham chiếu nested nào với GRID_META gốc / meta mẫu khác -
 *      mutate từng loại field (columns[i].*, autoName.*, duplicateKeys,
 *      outputOnlyTags, activeWhen.*) phải không đổi gì bản gốc (so JSON
 *      trước/sau). Entry khai LITERAL trong FORM_GRID_META (không qua
 *      mkGrid) được chứng minh ranh giới: isolate với form/global KHÁC,
 *      còn chính nó là object sống (cùng contract với fixture N9 của
 *      test_m72_activation - getGridMeta trả đúng reference).
 *  S2. EXPORT CONFLICT GUARD: loop cùng tên do >=2 mẫu tự khai form-scoped
 *      meta với contract export KHÁC nhau -> exportLoops ghi report rõ ràng,
 *      exportLoopsStrict NÉM lỗi có cấu trúc (FAIL LOUD, payload không nửa
 *      vời); contract THỰC SỰ tương đương -> xuất bình thường như cũ.
 *  S3. FOCUS SAU ROW OPERATION: focusTagOfGrid/nextSelAfterDelete thuần +
 *      focusGridRow trên DOM giả thủ công (add/duplicate/move/delete/bảng
 *      rỗng), selection bám _row_id.
 *
 * Chạy: node app_web/test_p20_hardening.js
 */
'use strict';

const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');
const G = App.GridCtl;

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
function eqJson(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

// =====================================================================
// S1. mkGrid DEEP CLONE - negative isolation tests
// =====================================================================

(function s1() {
  // Snapshot TRƯỚC của mọi vùng có thể bị lan mutation
  const before = {
    gridDsNganh: JSON.parse(JSON.stringify(FD.GRID_META.ds_nganh)),
    gridNganhBs: JSON.parse(JSON.stringify(FD.GRID_META.nganh_bo_sung)),
    m72All: JSON.parse(JSON.stringify(FD.FORM_GRID_META.PLI_M72)),
    m02All: JSON.parse(JSON.stringify(FD.FORM_GRID_META.PLII_M02))
  };

  function mutateEveryNestedKind(m) {
    // columns[]: từng column object + chính mảng
    m.columns[0].required = !m.columns[0].required;
    if (m.columns[1]) m.columns[1].type = 'HACKED';
    m.columns.push({ tag: 'hack_col', type: 'text' });
    m.columns.shift();
    // autoName: object lồng
    if (m.autoName) {
      m.autoName.codeTag = 'hack_code';
      m.autoName.nameTag = 'hack_name';
      m.autoName.extra = true;
    }
    // duplicateKeys / outputOnlyTags: mảng copy mức-1
    m.duplicateKeys.push('hack_key');
    m.outputOnlyTags.push('hack_out');
    // activeWhen: object (kể cả valueOf lồng)
    if (m.activeWhen) {
      m.activeWhen.minFilledRows = 999;
      m.activeWhen.checkedKey = 'hack_chk';
      m.activeWhen.valueOf = { key: 'hack_vof', equals: ['X'] };
    }
    return m;
  }

  /* Mutate rồi KHÔI PHỤC tại chỗ (giữ nguyên reference của meta trong
   * FORM_GRID_META) để các block so sánh sau không bị nhiễm mutation trước. */
  function withMutation(m, fn, body) {
    const snap = JSON.stringify(m);
    fn(m);
    try { body(); } finally {
      const fresh = JSON.parse(snap);
      Object.keys(m).forEach(k => delete m[k]);
      Object.assign(m, fresh);
    }
  }

  // --- S1a. PLI_M72 (meta do mkGrid sinh) ------------------------------
  const m72a = FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' });
  check('S1a.0 meta PLI_M72 la object rieng, khong phai GRID_META',
    m72a && m72a !== FD.GRID_META.ds_nganh);
  withMutation(m72a, mutateEveryNestedKind, function () {
    check('S1a.1 GRID_META.ds_nganh nguyen ven sau mutate meta M72',
      eqJson(FD.GRID_META.ds_nganh, before.gridDsNganh),
      JSON.stringify(FD.GRID_META.ds_nganh));
    check('S1a.2 loop anh em cung mau (ds_nganh_ctcp) khong doi',
      eqJson(FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_ctcp,
        before.m72All.loops.ds_nganh_ctcp));
    check('S1a.3 meta form khac (PLII_M02.toan bo loops) khong doi',
      eqJson(FD.FORM_GRID_META.PLII_M02, before.m02All));
  });
  check('S1a.4 khoi phuc tai cho giu nguyen reference meta trong FORM_GRID_META',
    FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' }) === m72a &&
      eqJson(m72a, before.m72All.loops.ds_nganh_dntn));

  // --- S1b. PLII_M02.ds_nganh (cung do mkGrid sinh) --------------------
  const m02ds = FD.getGridMeta({ docId: 'PLII_M02', loop: 'ds_nganh' });
  withMutation(m02ds, mutateEveryNestedKind, function () {
    check('S1b.1 GRID_META.ds_nganh van nguyen ven sau mutate meta M02.ds_nganh',
      eqJson(FD.GRID_META.ds_nganh, before.gridDsNganh));
    check('S1b.2 cac meta PLI_M72 khong bi lan mutation tu M02',
      eqJson(FD.FORM_GRID_META.PLI_M72, before.m72All));
  });

  // --- S1c. entry LITERAL trong FORM_GRID_META (nganh_bo_sung M02) -----
  // Ranh giới: literal KHONG qua mkGrid nen isolation chi cam ket GIUA CAC
  // vung (form/global khac); chinh no tra dung reference (khop N9 m72).
  const m02bs = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_bo_sung' });
  check('S1c.0 resolver tra dung reference literal cua mau',
    m02bs === FD.FORM_GRID_META.PLII_M02.loops.nganh_bo_sung);
  withMutation(m02bs, mutateEveryNestedKind, function () {
    check('S1c.1 GRID_META.nganh_bo_sung khong doi (khong share voi literal)',
      eqJson(FD.GRID_META.nganh_bo_sung, before.gridNganhBs));
    check('S1c.2 meta PLI_M72 khong doi sau mutate literal M02',
      eqJson(FD.FORM_GRID_META.PLI_M72, before.m72All));
    check('S1c.3 meta mkGrid khac (M02.ds_nganh da clone) khong doi',
      eqJson(FD.FORM_GRID_META.PLII_M02.loops.ds_nganh,
        before.m02All.loops.ds_nganh));
  });
  check('S1c.4 khoi phuc literal xong FORM_GRID_META.PLIIM02 ve dung snapshot',
    eqJson(FD.FORM_GRID_META.PLII_M02, before.m02All));

  // --- S1d. deep clone giua CAC loop M72: khong share ca mang con ------
  const a = FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_dntn;
  const b = FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_tnhh_2tv;
  check('S1d.1 hai loop M72: columns/autoName/dupKeys/outTags/activeWhen deu reference rieng',
    a.columns !== b.columns && a.columns[0] !== b.columns[0] &&
      a.autoName !== b.autoName && a.duplicateKeys !== b.duplicateKeys &&
      a.outputOnlyTags !== b.outputOnlyTags &&
      a.activeWhen !== b.activeWhen);
})();

// ---------------------------------------------------------------- kết luận tạm
console.log('-'.repeat(60));
console.log('test_p20_hardening: %d PASS / %d FAIL (section hien tai)', passed, failed);
if (failed) process.exit(1);
