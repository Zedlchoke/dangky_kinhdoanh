/* test_audit_p1_negative.js - INDEPENDENT AUDIT wave P1 (branch p1/g-audit-p1)
 * Negative tests auditor viet RIENG, khong dong vao production code.
 * Phu: N1 collision form-scoped, N2 M72 inactive, N3 M72 active loi,
 * N4 doc lap 4 vung PLII_M02, N5 semantic_key khac loop, N6 draft round-trip,
 * N7 export payload, N8 backward-compat + snapshot so BASELINE 6eaf4ee,
 * N9 allowlist file generated trong diff 6eaf4ee..HEAD.
 *
 * Marker EXPECTED-FAIL-AUDIT: chi xuat hien khi bug production duoc chung minh
 * (test do co chu dinh) - xem bao cao audit.
 * Chay: node app_web/test_audit_p1_negative.js
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const execSync = require('child_process').execSync;

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');
const G = App.GridCtl;

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
const VSIC_FULL = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'app', 'data', 'nganh_vsic.json'), 'utf8')).nganh;

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else { failed++; console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : '')); }
}
function eqJson(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function clone(x) { return JSON.parse(JSON.stringify(x)); }
function mkRow(fields, rid) {
  return Object.assign({ _row_id: rid || FD.makeRowId() }, fields || {});
}

const M72 = loadProd('PLI_M72');
const M02 = loadProd('PLII_M02');
const M06 = loadProd('PLI_M06');
const M72_LOOPS = ['ds_nganh_dntn', 'ds_nganh_tnhh_1tv', 'ds_nganh_tnhh_2tv',
  'ds_nganh_ctcp', 'ds_nganh_dhdn'];

function errsOf(docId, blocks, store, vsicList) {
  return FD.validateDocument(docId, blocks, store,
    { vsicList: vsicList == null ? VSIC_FULL : vsicList });
}
function errsOfLoop(errs, loop) {
  return errs.filter(function (e) { return String(e.key).indexOf('loop:' + loop) === 0; });
}
function vsicOf(ma) {
  return VSIC_FULL.filter(function (x) { return String(x.ma) === ma; })[0] || null;
}

// ===================== N1. Form-scoped collision nganh_bo_sung ==============

(function n1() {
  const m12 = FD.getGridMeta({ docId: 'PLI_M12', loop: 'nganh_bo_sung' });
  const m02 = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_bo_sung' });
  const gGlobal = FD.GRID_META.nganh_bo_sung;

  check('N1a. PLI_M12/nganh_bo_sung resolve meta cu (tag ten_nganh)',
    !!m12 && !!(m12.columns || []).some(function (c) { return c.tag === 'ten_nganh'; }));
  check('N1b. PLII_M02/nganh_bo_sung tag ten_nganh_bo_sung',
    !!m02 && (m02.columns || []).map(function (c) { return c.tag; })[0] === 'ten_nganh_bo_sung');
  check('N1c. hai meta KHAC object', m12 !== m02 && m02 !== gGlobal);
  const shared = m12.columns.filter(function (c) { return m02.columns.indexOf(c) >= 0; });
  check('N1d. KHONG chia se mang columns/object cot',
    m12.columns !== m02.columns && shared.length === 0);

  const before12 = clone(m12);
  const beforeG = clone(gGlobal);
  m02.columns.push({ tag: '__hack__' });
  m02.columns[0].required = false;
  m02.label = '__mutated__';
  check('N1e. mutate meta PLII_M02 khong lan sang meta PLI_M12', eqJson(m12, before12));
  check('N1f. mutate meta PLII_M02 khong lan sang GRID_META goc', eqJson(gGlobal, beforeG));

  const again = FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_bo_sung' });
  check('N1g. resolver uu tien form-scoped hon global', again === m02 && again !== gGlobal);
})();

// ===================== N2. PLI_M72 grid inactive im lang ====================

(function n2() {
  const vA = vsicOf('0111');

  // Truong hop 1: chi 1/5 grid co du lieu, chua chon nganh chinh
  const st1 = R.newStore();
  st1.loops.ds_nganh_tnhh_1tv = [mkRow({
    ten_nganh: vA.ten, ma_nganh: vA.ma, la_nganh_chinh: '' }, 'fx-a1')];
  const e1 = errsOf('PLI_M72', M72.blocks, st1);

  const prim = e1.filter(function (e) { return e.code === 'PRIMARY_INDUSTRY_REQUIRED'; });
  check('N2a. dung 1 loi PRIMARY_INDUSTRY_REQUIRED',
    prim.length === 1, JSON.stringify(prim.map(function (e) { return e.key; })));
  check('N2b. loi primary tro DUNG grid co du lieu (tnhh_1tv), blocking',
    prim.length === 1 && prim[0].key.indexOf('loop:ds_nganh_tnhh_1tv:') === 0 &&
    prim[0].severity === 'blocking');

  const noise = [];
  M72_LOOPS.forEach(function (l) {
    if (l === 'ds_nganh_tnhh_1tv') return;
    errsOfLoop(e1, l).forEach(function (e) { noise.push(l + '|' + e.code); });
  });
  check('N2c. 4 grid TRONG khong sinh bat ky error nao', noise.length === 0,
    JSON.stringify(noise));

  // Truong hop 2: ca 5 grid trong -> 0 error tu 5 grid nay
  const st2 = R.newStore();
  M72_LOOPS.forEach(function (l) { st2.loops[l] = []; });
  const e2 = errsOf('PLI_M72', M72.blocks, st2);
  const from5 = [];
  M72_LOOPS.forEach(function (l) {
    errsOfLoop(e2, l).forEach(function (e) { from5.push(l + '|' + e.code); });
  });
  check('N2d. ca 5 grid trong -> 0 error (moi severity) tu 5 grid',
    from5.length === 0, JSON.stringify(from5));
})();

// ===================== N3. PLI_M72 active: VSIC sai + trung ma ==============

(function n3() {
  const vB = vsicOf('4711');
  let vC = null;
  for (let i = 0; i < VSIC_FULL.length && !vC; i++) {
    const x = VSIC_FULL[i];
    if (/^[1-9]/.test(String(x.ma)) && String(x.ma).length === 4 &&
        x.ma !== '4711' && x.ma !== '0111' && String(x.ten || '').trim()) vC = x;
  }

  // VSIC sai: dung grid do blocking VSIC_INVALID, khong lan grid khac
  const st1 = R.newStore();
  st1.loops.ds_nganh_ctcp = [mkRow({
    ten_nganh: 'Ten tu nhap', ma_nganh: '999999', la_nganh_chinh: '' }, 'fx-b1')];
  const inv = errsOf('PLI_M72', M72.blocks, st1)
    .filter(function (e) { return e.code === 'VSIC_INVALID'; });
  check('N3a. VSIC sai -> dung 1 loi VSIC_INVALID blocking dung row',
    inv.length === 1 && inv[0].severity === 'blocking' &&
    inv[0].key === 'loop:ds_nganh_ctcp:fx-b1:ma_nganh',
    JSON.stringify(inv.map(function (e) { return e.key; })));

  // Trung ma: DUPLICATE_INDUSTRY blocking tro CA HAI row dung vi tri
  const st2 = R.newStore();
  st2.loops.ds_nganh_dhdn = [
    mkRow({ ten_nganh: vB.ten, ma_nganh: vB.ma, la_nganh_chinh: '' }, 'fx-c1'),
    mkRow({ ten_nganh: vC.ten, ma_nganh: vB.ma, la_nganh_chinh: '' }, 'fx-c2')
  ];
  const e2 = errsOf('PLI_M72', M72.blocks, st2);
  const dups = e2.filter(function (e) { return e.code === 'DUPLICATE_INDUSTRY'; })
    .map(function (e) { return e.key; }).sort();
  check('N3b. trung ma -> DUPLICATE_INDUSTRY blocking dung 2 row',
    eqJson(dups, ['loop:ds_nganh_dhdn:fx-c1:ma_nganh',
      'loop:ds_nganh_dhdn:fx-c2:ma_nganh']), JSON.stringify(dups));
  check('N3c. moi loi duplicate deu thuoc grid co du lieu',
    dups.every(function (k) { return k.indexOf('loop:ds_nganh_dhdn:') === 0; }));
})();

// ========== N4. PLII_M02: thao tac GridCtl 1 vung khong doi 3 vung ==========

(function n4() {
  const st = R.newStore();
  st.loops.nganh_bo_sung = [
    mkRow({ ten_nganh_bo_sung: 'Bo sung A', ma_nganh: '4711',
      la_nganh_chinh: 'X' }, 'r4-a1'),
    mkRow({ ten_nganh_bo_sung: 'Bo sung B', ma_nganh: '0111',
      la_nganh_chinh: '' }, 'r4-a2')
  ];
  st.loops.nganh_xoa_bo = [
    mkRow({ ten_nganh_bo: 'Xoa bo K', ma_nganh: '0111',
      la_nganh_chinh: '' }, 'r4-k1')];
  st.loops.nganh_sua_doi_chi_tiet = [
    mkRow({ ten_nganh: 'Sua doi M', ma_nganh: '0111' }, 'r4-m1')];
  st.loops.ds_nganh = [
    mkRow({ ten_nganh: 'Hien tai Z', ma_nganh: '0111',
      la_nganh_chinh: 'X' }, 'r4-z1')];

  const OTHERS = ['nganh_xoa_bo', 'nganh_sua_doi_chi_tiet', 'ds_nganh'];
  function snap() {
    const o = {};
    OTHERS.forEach(function (k) { o[k] = JSON.stringify(st.loops[k]); });
    return o;
  }
  const base = snap();
  let okAll = true;
  let where = '';
  function verify(op) {
    const s2 = snap();
    OTHERS.forEach(function (k) {
      if (s2[k] !== base[k]) { okAll = false; where += op + '->' + k + '; '; }
    });
  }

  const added = G.addRow(st, 'nganh_bo_sung');
  verify('add');
  const dup = G.duplicateRow(st, 'nganh_bo_sung', 'r4-a1', 'PLII_M02');
  verify('duplicate');
  check('N4a. duplicateRow cap id moi, khong nham id cu',
    !!dup && dup.id !== 'r4-a1' && dup.index >= 0);
  const moved = G.moveRow(st, 'nganh_bo_sung', 'r4-a2', -1);
  verify('reorder');
  check('N4b. moveRow di chuyen dung row theo _row_id',
    moved >= 0 && st.loops.nganh_bo_sung[moved]._row_id === 'r4-a2');
  G.deleteRows(st, 'nganh_bo_sung', ['r4-a1', added.id]);
  verify('delete');
  G.clearRows(st, 'nganh_bo_sung');
  verify('clear');
  check('N4c. clearRows chi lam rong vung bi thao tac',
    st.loops.nganh_bo_sung.length === 0 && st.loops.nganh_xoa_bo.length === 1);
  G.setExclusiveRadio(st, 'ds_nganh', 'r4-z1', 'la_nganh_chinh', true);
  verify('radio');
  check('N4d. 3 vung con lai byte-unchanged qua add/duplicate/reorder/delete/clear/radio',
    okAll, where);
})();

// ===================== N5. semantic_key khac ten loop =======================

(function n5() {
  const bySk = FD.getGridMeta({ docId: 'PLII_M02', semanticKey: 'nganh_hien_tai' });
  const byLp = FD.getGridMeta({ docId: 'PLII_M02', loop: 'ds_nganh' });
  check('N5a. semanticKey nganh_hien_tai -> loop ds_nganh requirePrimary=true',
    !!bySk && bySk.loop === 'ds_nganh' && bySk.requirePrimary === true);
  check('N5b. lookup theo semanticKey va theo loop cung mot reference', bySk === byLp);

  let okSk = true;
  M72_LOOPS.forEach(function (sk) {
    const m = FD.getGridMeta({ docId: 'PLI_M72', semanticKey: sk });
    if (!m || m.loop !== sk || m.formId !== 'PLI_M72') okSk = false;
  });
  check('N5c. 5 semanticKey PLI_M72 resolve dung loop/formId', okSk);

  check('N5d. semanticKey la -> null (khong fallback khi thieu loop)',
    FD.getGridMeta({ docId: 'PLII_M02', semanticKey: 'khong_co' }) === null);
})();

// ===================== N6. Draft round-trip 8 loop + _row_id ================

(function n6() {
  const loops = {};
  M72_LOOPS.forEach(function (l, i) {
    loops[l] = [mkRow({ ten_nganh: 'N' + i, ma_nganh: '0111',
      la_nganh_chinh: i === 0 ? 'X' : '' }, 'dr-' + l)];
  });
  loops.nganh_bo_sung = [mkRow({ ten_nganh_bo_sung: 'BS', ma_nganh: '4711',
    la_nganh_chinh: 'X' }, 'dr-bs')];
  loops.nganh_xoa_bo = [mkRow({ ten_nganh_bo: 'XB', ma_nganh: '4711' }, 'dr-xb')];
  loops.nganh_sua_doi_chi_tiet = [
    mkRow({ ten_nganh: 'SD', ma_nganh: '4711' }, 'dr-sd')];

  const draft = { v: 2, caseId: 'audit-case', checkedForms: { PLI_M72: true },
    activeDocId: 'PLI_M72', autoSum: false, viewState: {}, savedAt: null,
    store: { values: {}, checks: {}, loops: loops } };
  const idsBefore = {};
  Object.keys(loops).forEach(function (k) {
    idsBefore[k] = loops[k].map(function (r) { return r._row_id; });
  });

  const migrated = FD.migrateDraft(draft);
  check('N6a. draft v2 tra ve chinh object goc', migrated === draft);

  const gotLoops = Object.keys(migrated.store.loops).sort();
  const wantLoops = Object.keys(loops).sort();
  check('N6b. giu du 8 loop, khong them key la', eqJson(gotLoops, wantLoops),
    JSON.stringify(gotLoops));

  let idsOk = true;
  Object.keys(idsBefore).forEach(function (k) {
    const now = migrated.store.loops[k].map(function (r) { return r._row_id; });
    if (!eqJson(now, idsBefore[k])) idsOk = false;
  });
  check('N6c. _row_id nguyen ven sau migrate', idsOk);

  // draft THIEU _row_id: duoc cap id moi, idempotent qua cac lan migrate
  const draft2 = { v: 2, caseId: 'audit-case-2', checkedForms: {},
    activeDocId: null, autoSum: false, viewState: {}, savedAt: null,
    store: { values: {}, checks: {},
      loops: { nganh_bo_sung: [{ ten_nganh_bo_sung: 'NoID' }] } } };
  const m1 = FD.migrateDraft(draft2);
  const id1 = m1.store.loops.nganh_bo_sung[0]._row_id;
  check('N6d. row thieu id duoc cap id moi',
    typeof id1 === 'string' && id1.length > 0);
  const m2 = FD.migrateDraft(draft2);
  check('N6e. migrate lan 2 idempotent (id khong doi)',
    m2.store.loops.nganh_bo_sung[0]._row_id === id1);
})();

// ===================== N7. Export payload sach + map radio ==================

(function n7() {
  const st = R.newStore();
  st.loops.nganh_bo_sung = [
    mkRow({ ten_nganh_bo_sung: 'BS1', ma_nganh: '0111',
      la_nganh_chinh: 'X' }, 'ex-1'),
    mkRow({ ten_nganh_bo_sung: 'BS2', ma_nganh: '0111',
      la_nganh_chinh: '' }, 'ex-2'),
    mkRow({ ten_nganh_bo_sung: 'BS3', ma_nganh: '0111',
      la_nganh_chinh: true }, 'ex-3')
  ];
  st.loops.nganh_sua_doi_chi_tiet = [
    mkRow({ ten_nganh: 'SD khong co cot radio', ma_nganh: '0111' }, 'ex-4')];
  st.loops.ds_nganh_ctcp = [
    mkRow({ ten_nganh: 'CT1', ma_nganh: '0111', la_nganh_chinh: true }, 'ex-5'),
    mkRow({ ten_nganh: 'CT2', ma_nganh: '0111' }, 'ex-6')
  ];

  const out = G.exportLoops(st, ['PLII_M02', 'PLI_M72']);
  check('N7a. payload khong con _row_id',
    JSON.stringify(out).indexOf('_row_id') < 0);

  const bs = out.nganh_bo_sung;
  check('N7b. la_nganh_chinh map X/""/true->X dung meta form-scoped',
    bs[0].la_nganh_chinh === 'X' && bs[1].la_nganh_chinh === '' &&
    bs[2].la_nganh_chinh === 'X',
    JSON.stringify(bs.map(function (r) { return r.la_nganh_chinh; })));

  const sd = out.nganh_sua_doi_chi_tiet;
  check('N7c. sua_doi_chi_tiet (requirePrimary=false) KHONG bi gan la_nganh_chinh rong',
    sd.every(function (r) {
      return !Object.prototype.hasOwnProperty.call(r, 'la_nganh_chinh');
    }), JSON.stringify(sd));

  const ct = out.ds_nganh_ctcp;
  check('N7d. grid requirePrimary (M72) giu cot radio ca row thieu field',
    ct[0].la_nganh_chinh === 'X' && ct[1].la_nganh_chinh === '',
    JSON.stringify(ct.map(function (r) { return r.la_nganh_chinh; })));

  let noInternal = true;
  Object.keys(out).forEach(function (k) {
    out[k].forEach(function (row) {
      Object.keys(row).forEach(function (c) { if (c.charAt(0) === '_') noInternal = false; });
    });
  });
  check('N7e. khong field noi bo bat dau bang "_" sot lai', noInternal);
})();

// ====== N8. Backward compat + so snapshot loi voi BASELINE 6eaf4ee ==========

(function n8() {
  check('N8a. getGridMeta(string) tra chinh reference GRID_META',
    FD.getGridMeta('ds_thanh_vien') === FD.GRID_META.ds_thanh_vien &&
    FD.getGridMeta('ds_nganh') === FD.GRID_META.ds_nganh);
  check('N8b. getGridMeta ten khong ton tai -> null',
    FD.getGridMeta('khong_ton_tai') === null);

  // Nap form-domain.js BASELINE 6eaf4ee vao temp dir de so snapshot
  let FB = null;
  try {
    const src = execSync('git show 6eaf4ee:app_web/ui/form-domain.js',
      { cwd: path.join(__dirname, '..'), maxBuffer: 32 * 1024 * 1024 }).toString('utf8');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'audit-baseline-'));
    const p = path.join(dir, 'form-domain.baseline.js');
    fs.writeFileSync(p, src, 'utf8');
    FB = require(p);
  } catch (e) {
    check('N8c. nap baseline 6eaf4ee', false, String(e.message || e));
  }
  if (!FB) return;

  function zipRow(tags, j, rid) {
    const r = { _row_id: rid };
    tags.forEach(function (t) {
      if (t === 'ma_nganh') r[t] = '0111';
      else if (t === 'la_nganh_chinh') r[t] = (j === 0 ? 'X' : '');
      else r[t] = 'GT-' + t + '-' + j;
    });
    return r;
  }
  function fixtureStore(blocks) {
    const st = { values: {}, checks: {}, loops: {} };
    (blocks.blocks || []).forEach(function (b) {
      if (b.t !== 'loop') return;
      const tags = (b.cols || []).map(function (c) { return c.tag; });
      st.loops[b.loop] = [zipRow(tags, 0, 'fx1'), zipRow(tags, 1, 'fx2')];
    });
    return st;
  }

  ['PLI_M06', 'PLI_M12'].forEach(function (docId) {
    const blocks = loadProd(docId);
    const cur = errsOf(docId, blocks.blocks, fixtureStore(blocks), VSIC_FULL);
    const base = FB.validateDocument(docId, clone(blocks.blocks),
      fixtureStore(blocks), { vsicList: VSIC_FULL });
    check('N8c.' + docId + ' hanh vi validate khong doi so voi baseline',
      eqJson(cur, base), '\n  CUR=' + JSON.stringify(cur) +
      '\n  BASE=' + JSON.stringify(base));
  });
})();

// ===================== N9. Allowlist file generated trong diff ==============

(function n9() {
  // Allowlist: file generated DUOC PHEP xuat hien trong diff 6eaf4ee..HEAD.
  //  - 2 entry dau: allowlist gốc thời điểm viết test (P1 audit).
  //  - layout_specs/fragments/*: census layout L0-A/L0-B/L0-C được merge
  //    chính thức lên main (5ef9cad, 52de102, a5f30a7) - artifact đọc-only
  //    của công đoạn census, không phải đụng generated bởi agent sau.
  const ALLOW = [
    'app/templates/PLII_M01.docx',
    'app/data/table_specs/manifest.json',
    'app/data/layout_specs/fragments/l0_a.md',
    'app/data/layout_specs/fragments/l0_a_evidence.json',
    'app/data/layout_specs/fragments/l0_b.md',
    'app/data/layout_specs/fragments/l0_b_evidence.json',
    'app/data/layout_specs/fragments/l0_c.md',
    'app/data/layout_specs/fragments/l0_c_evidence.json',
    // layout-manifest-v1: hop nhat 3 fragment L0 do Lead sinh qua
    // tools/census/build_layout_manifest.py (commit 6047c1d) - artifact
    // census co chu dich, khong phai generated drift.
    'app/data/layout_specs/layout_manifest.json'
  ];
  let files = [];
  try {
    files = execSync('git diff --name-only 6eaf4ee..HEAD',
      { cwd: path.join(__dirname, '..'), maxBuffer: 32 * 1024 * 1024 })
      .toString('utf8').split(/\r?\n/).filter(Boolean);
  } catch (e) {
    check('N9a. liet ke diff 6eaf4ee..HEAD', false, String(e.message || e));
    return;
  }
  const GEN_PREFIX = ['app/templates/', 'app/data/'];
  const unexpected = files.filter(function (f) {
    return GEN_PREFIX.some(function (p) { return f.indexOf(p) === 0; }) &&
      ALLOW.indexOf(f) < 0;
  });
  check('N9a. moi file generated thay doi thuoc allowlist (' +
    files.length + ' file trong diff)', unexpected.length === 0,
    'file la: ' + JSON.stringify(unexpected));
})();

// ------------------------------------------------------------------ summary

console.log('-'.repeat(64));
console.log('test_audit_p1_negative: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
