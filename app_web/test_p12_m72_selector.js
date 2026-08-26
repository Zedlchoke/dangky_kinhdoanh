/* test_p12_m72_selector.js - P1.2 "OPTION D": SELECTOR LOẠI HÌNH DN (PLI_M72).
 *
 * Production contract sau khi Option D landing (không còn INTERIM):
 *  a. Contract meta: FORM_SELECTOR_META['PLI_M72'] đúng 5 giá trị canonical,
 *     mỗi option một flag; ĐỐI CHIÉU CHÉO với
 *     tools/form_specs/change/PLI_M72.json (section_cond: value + flag +
 *     occurrence_id) khớp từng đôi một; occurrence_id khớp 5 loop
 *     FORM_GRID_META và activeWhen.valueOf của đúng loop đó.
 *  b. validateSelector: chưa chọn -> SELECTOR_REQUIRED blocking; giá trị lạ
 *     'ABC'/chữ thường 'ctcp' -> SELECTOR_INVALID; chọn hợp lệ -> [];
 *     trim khoảng trắng vẫn hợp lệ; selectedSelectorOption đúng option/null.
 *  c. validateDocument trên blocks thật: chưa chọn + grid bẩn -> đúng 1 lỗi
 *     selector, 0 lỗi loop; chọn CTCP -> lỗi loop CHỈ thuộc ds_nganh_ctcp.
 *  d. selectorFlagsOf đúng 'X'/''; renderBlocks với blocks thật: chỉ biến thể
 *     được chọn xuất hiện (đúng tiêu đề + data-loop), 4 biến thể kia vắng mặt;
 *     không chọn -> còn 'Mẫu số 72' + tiêu đề chung + selector UI, KHÔNG bảng
 *     lặp nào; selectorHtml: 5 radio cùng name, checked theo store,
 *     data-sel-key/data-key/help đầy đủ.
 *  e. Export: exportLoops loại rows biến thể inactive; mô phỏng mức
 *     buildExportData (Object.assign(data, selectorFlagsOf)) đủ 5 flag.
 *  f. Draft cũ: migrateDraft draft v2 thiếu dn.loai_hinh -> GIỮ dữ liệu nhưng
 *     validateDocument vẫn chặn SELECTOR_REQUIRED + mọi grid inactive;
 *     draft CÓ dn.loai_hinh -> restore đúng trạng thái active.
 *  g. NEGATIVE: mutate meta fixture không lan production; 5 equals của
 *     activeWhen phân biệt hoàn toàn (hai loop không bao giờ cùng điều kiện).
 *
 * Chạy: node app_web/test_p12_m72_selector.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const FD = require('./ui/form-domain.js');
const R = require('./ui/render.js');
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

// ------------------------------------------------------------------ fixture

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
const M72 = loadProd('PLI_M72');

const VSIC_MOCK = [
  { ma: '0111', ten: 'Trồng lúa', cap: 4 },
  { ma: '4711', ten: 'Bán lẻ máy tính', cap: 4 }
];

const M72_LOOPS = ['ds_nganh_dntn', 'ds_nganh_tnhh_1tv', 'ds_nganh_tnhh_2tv',
  'ds_nganh_ctcp', 'ds_nganh_dhdn'];
const CANON_VALUES = ['DNTN', 'TNHH_1TV', 'TNHH_2TV', 'CTCP', 'DHDN'];
const KEY = 'dn.loai_hinh';
const SEL = FD.getFormSelector('PLI_M72');

function mkStore(init) {
  const s = { values: {}, checks: {}, loops: {} };
  Object.keys(init || {}).forEach(k => {
    if (k === 'values') { s.values = Object.assign({}, init[k]); return; }
    s.loops[k] = (init[k] || []).map(r => Object.assign({ _row_id: FD.makeRowId() }, r));
  });
  return s;
}
function errsOf(store) {
  return FD.validateDocument('PLI_M72', M72.blocks, store, { vsicList: VSIC_MOCK });
}
function loopErrs(errs) {
  return errs.filter(e => String(e.key).indexOf('loop:') === 0);
}
function selErrs(errs) {
  return errs.filter(e => String(e.key).indexOf('@selector:') === 0);
}

// ==== a. Contract meta + đối chiếu chéo spec change ==========================

(function a() {
  check('a1. getFormSelector(PLI_M72): key dn.loai_hinh, required, co options',
    !!SEL && SEL.key === KEY && SEL.required === true &&
      Array.isArray(SEL.options) && SEL.formId === 'PLI_M72');
  check('a2. dung 5 gia tri canonical, khong trung lap',
    SEL.options.length === 5 &&
      JSON.stringify(SEL.options.map(o => o.value)) === JSON.stringify(CANON_VALUES) &&
      new Set(SEL.options.map(o => o.value)).size === 5);
  const flags = SEL.options.map(o => o.flag);
  check('a3. moi option co flag duy nhat, khac rong, tien to loai_hinh_',
    flags.every(f => typeof f === 'string' && /^loai_hinh_/.test(f)) &&
      new Set(flags).size === 5);

  // ĐỐI CHIÉU CHÉO với spec change của Lead (artifact nguồn của marker DOCX)
  const SPEC = JSON.parse(fs.readFileSync(
    path.join(__dirname, '..', 'tools', 'form_specs', 'change', 'PLI_M72.json'),
    'utf8')).section_cond;
  const specByValue = {};
  (SPEC.options || []).forEach(o => { specByValue[o.value] = o; });
  check('a4. spec section_cond: value_key khop + 5 cap (value, flag) khop tung doi mot',
    SPEC.value_key === KEY && (SPEC.options || []).length === 5 &&
      CANON_VALUES.every(v => specByValue[v] &&
        SEL.options.some(o => o.value === v && o.flag === specByValue[v].flag)));
  check('a5. occurrence_id spec khop 5 loop FORM_GRID_META + activeWhen cua dung loop do',
    Object.keys(FD.FORM_GRID_META.PLI_M72.loops).length === 5 &&
      (SPEC.options || []).every(o => {
        const gm = FD.FORM_GRID_META.PLI_M72.loops[o.occurrence_id];
        return !!gm && gm.loop === o.occurrence_id &&
          FD.activationModeOf(gm) === 'selector' &&
          gm.activeWhen.valueOf.key === KEY &&
          JSON.stringify(gm.activeWhen.valueOf.equals) ===
            JSON.stringify([o.value]);
      }));
  check('a6. blocks: moi loop mang cond dung flag spec (nguon converter)',
    (SPEC.options || []).every(o => {
      const lb = (M72.blocks || []).filter(b => b.t === 'loop' &&
        b.loop === o.occurrence_id)[0];
      return !!lb && Array.isArray(lb.cond) && lb.cond.length === 1 &&
        lb.cond[0] === o.flag;
    }));
})();

// ==== b. validateSelector ====================================================

(function b() {
  function vs(values) { return { values: values || {}, checks: {}, loops: {} }; }

  const eNone = FD.validateSelector('PLI_M72', SEL, vs());
  check('b1. chua chon -> dung 1 loi SELECTOR_REQUIRED blocking @selector:dn.loai_hinh',
    eNone.length === 1 && eNone[0].code === 'SELECTOR_REQUIRED' &&
      eNone[0].severity === 'blocking' &&
      eNone[0].key === '@selector:' + KEY,
    JSON.stringify(eNone));

  const eWeird = FD.validateSelector('PLI_M72', SEL, vs({ [KEY]: 'ABC' }));
  check("b2. gia tri la 'ABC' -> SELECTOR_INVALID blocking",
    eWeird.length === 1 && eWeird[0].code === 'SELECTOR_INVALID' &&
      eWeird[0].severity === 'blocking' &&
      eWeird[0].key === '@selector:' + KEY,
    JSON.stringify(eWeird));

  const eLower = FD.validateSelector('PLI_M72', SEL, vs({ [KEY]: 'ctcp' }));
  check("b3. chu thuong 'ctcp' -> SELECTOR_INVALID (phan biet hoa/thuong)",
    eLower.length === 1 && eLower[0].code === 'SELECTOR_INVALID',
    JSON.stringify(eLower));

  check('b4. chon hop le CTCP -> khong loi',
    FD.validateSelector('PLI_M72', SEL, vs({ [KEY]: 'CTCP' })).length === 0);
  check('b4b. khoang trang quanh gia tri duoc trim truoc khi so -> van hop le',
    FD.validateSelector('PLI_M72', SEL, vs({ [KEY]: '  DHTN '.replace('DHTN', 'DHDN') + ' '
    })).length === 0 ||
      FD.validateSelector('PLI_M72', SEL, vs({ [KEY]: ' DHDN ' })).length === 0);

  check('b5. selectedSelectorOption: dung option hop le, null khi la/thieu',
    FD.selectedSelectorOption(SEL, vs({ [KEY]: 'TNHH_2TV' })).value === 'TNHH_2TV' &&
      FD.selectedSelectorOption(SEL, vs({ [KEY]: 'GIATRI_LA' })) === null &&
      FD.selectedSelectorOption(SEL, vs()) === null &&
      FD.selectedSelectorOption(null, vs()) === null);
})();

// ==== c. validateDocument tren blocks that ==================================

(function c() {
  // mọi biến thể đều có dữ liệu BẨN (VSIC sai + chưa đánh dấu ngành chính)
  function dirtyStore(values) {
    const st = mkStore({
      ds_nganh_dntn: [{ ma_nganh: '999999', ten_nganh: 'Bai dntn' }],
      ds_nganh_tnhh_1tv: [{ ma_nganh: '999999', ten_nganh: 'Bai t1' }],
      ds_nganh_tnhh_2tv: [{ ma_nganh: '999999', ten_nganh: 'Bai t2' }],
      ds_nganh_ctcp: [{ ma_nganh: '999999', ten_nganh: 'Bai ctcp' }],
      ds_nganh_dhdn: [{ ma_nganh: '999999', ten_nganh: 'Bai dhdn' }]
    });
    st.values = Object.assign(st.values, values || {});
    return st;
  }

  const stNone = dirtyStore();
  const errsNone = errsOf(stNone);
  check('c1. chua chon + grid ban -> dung 1 loi selector, 0 loi loop',
    selErrs(errsNone).length === 1 &&
      selErrs(errsNone)[0].code === 'SELECTOR_REQUIRED' &&
      selErrs(errsNone)[0].key === '@selector:' + KEY &&
      selErrs(errsNone)[0].severity === 'blocking' &&
      loopErrs(errsNone).length === 0,
    JSON.stringify(errsNone.map(e => e.code + '@' + e.key)));

  const stCtcp = dirtyStore({ [KEY]: 'CTCP' });
  const errsCtcp = errsOf(stCtcp);
  const le = loopErrs(errsCtcp);
  check('c2. chon CTCP -> chi grid ds_nganh_ctcp bi phet loi (VSIC + primary)',
    le.length >= 1 && le.every(e => e.key.indexOf('loop:ds_nganh_ctcp:') === 0) &&
      le.some(e => e.code === 'VSIC_INVALID') &&
      le.some(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED'),
    JSON.stringify(le.map(e => e.code + '@' + e.key)));
  check('c2b. chon CTCP xong KHONG con loi selector',
    selErrs(errsCtcp).length === 0);
})();

// ==== d. selectorFlagsOf + renderBlocks cond + selectorHtml =================

(function d() {
  const stEmpty = mkStore();
  const flagsNone = FD.selectorFlagsOf('PLI_M72', stEmpty);
  check('d1. flags khi chua chon: du 5 flag deu rong',
    Object.keys(flagsNone).length === 5 &&
      CANON_VALUES.every(v =>
        flagsNone[SEL.options.find(o => o.value === v).flag] === ''));

  const stCtcp = mkStore({ values: { [KEY]: 'CTCP' } });
  const flagsCtcp = FD.selectorFlagsOf('PLI_M72', stCtcp);
  check("d2. flags khi chon CTCP: 'X'/'' dung 5 flag",
    flagsCtcp.loai_hinh_ctcp === 'X' && flagsCtcp.loai_hinh_dntn === '' &&
      flagsCtcp.loai_hinh_tnhh_1tv === '' && flagsCtcp.loai_hinh_tnhh_2tv === '' &&
      flagsCtcp.loai_hinh_dhdn === '');

  // Tiêu đề biến thể đầu tiên của từng flag (từ blocks thật)
  const titleOfFlag = {};
  (M72.blocks || []).forEach(b => {
    if (b.t !== 'p' || !Array.isArray(b.cond) || b.cond.length !== 1) return;
    const f = b.cond[0];
    if (!titleOfFlag[f]) {
      titleOfFlag[f] = (b.runs || []).map(r => (r && r.text != null) ? r.text : '').join('');
    }
  });

  function renderWith(values) {
    const st = mkStore({ values: values || {} });
    return R.renderBlocks({ id: 'PLI_M72', blocks: M72.blocks }, st, {
      docId: 'PLI_M72', fieldMeta: FD.FIELD_META,
      gridMeta: App.gridMetaForDoc('PLI_M72'),
      flags: FD.selectorFlagsOf('PLI_M72', st),
      selectorHtml: R.selectorHtml(SEL, R.makeAccessors(st))
    });
  }

  const htmlDntn = renderWith({ [KEY]: 'DNTN' });
  check('d3. render chon DNTN: bien te dntn xuat hien (tieu de + data-loop)',
    htmlDntn.indexOf(titleOfFlag.loai_hinh_dntn) >= 0 &&
      htmlDntn.indexOf('data-loop="ds_nganh_dntn"') >= 0,
    'title=' + titleOfFlag.loai_hinh_dntn);
  check('d4. render chon DNTN: 4 bien te kia vang mat khoi HTML',
    ['tnhh_1tv', 'tnhh_2tv', 'ctcp', 'dhdn'].every(suf =>
      ['loai_hinh_' + suf, 'ds_nganh_' + suf].every(token => {
        if (token.indexOf('loai_hinh_') === 0) {
          return htmlDntn.indexOf(titleOfFlag[token]) < 0;
        }
        return htmlDntn.indexOf('data-loop="' + token + '"') < 0;
      })));

  const htmlNone = renderWith({});
  check('d5. khong chon: con "Mau so 72" + tieu de chung + selector UI, khong bang lap nao',
    htmlNone.indexOf('Mẫu số 72') >= 0 &&
      htmlNone.indexOf('CÔNG BỐ NỘI DUNG ĐĂNG KÝ THÀNH LẬP DOANH NGHIỆP') >= 0 &&
      htmlNone.indexOf('class="doc-selector"') >= 0 &&
      htmlNone.indexOf('data-loop=') < 0,
    'data-loop count=' + (htmlNone.match(/data-loop=/g) || []).length);

  // selectorHtml: cấu trúc radio group theo store
  function selHtmlOf(value) {
    const st = mkStore({ values: value == null ? {} : { [KEY]: value } });
    return R.selectorHtml(SEL, R.makeAccessors(st));
  }
  const shCtcp = selHtmlOf('CTCP');
  const radios = shCtcp.match(/<input type="radio" class="sel-radio"[^>]*>/g) || [];
  check('d6. selectorHtml: 5 radio cung name sel:dn.loai_hinh, co data-sel-key/data-key',
    radios.length === 5 &&
      new Set(radios.map(t => (t.match(/name="([^"]*)"/) || [])[1])).size === 1 &&
      radios.every(t => t.indexOf('name="sel:' + KEY + '"') >= 0 &&
        t.indexOf('data-sel-key="' + KEY + '"') >= 0 &&
        t.indexOf('data-key="' + KEY + '"') >= 0),
    JSON.stringify(radios));
  check('d7. selectorHtml: dung 1 radio checked khop gia tri trong store',
    (shCtcp.match(/ checked/g) || []).length === 1 &&
      radios.filter(t => t.indexOf(' checked') >= 0)[0]
        .indexOf('value="CTCP"') >= 0);
  check('d7b. doi store sang DNTN -> checked di theo radio DNTN',
    (() => {
      const sh = selHtmlOf('DNTN');
      const rs = sh.match(/<input type="radio" class="sel-radio"[^>]*>/g) || [];
      return (sh.match(/ checked/g) || []).length === 1 &&
        rs.filter(t => t.indexOf(' checked') >= 0)[0].indexOf('value="DNTN"') >= 0;
    })());
  check('d8. selectorHtml: radiogroup aria-required + help text hien dien',
    selHtmlOf().indexOf('role="radiogroup"') >= 0 &&
      selHtmlOf().indexOf('aria-required="true"') >= 0 &&
      selHtmlOf().indexOf('class="doc-sel-help"') >= 0);
})();

// ==== e. Export: exportLoops loc + merge flags muc buildExportData ==========

(function e() {
  const st = mkStore({
    ds_nganh_dntn: [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' }],
    ds_nganh_ctcp: [{ ma_nganh: '4711', ten_nganh: 'Ban le', la_nganh_chinh: true }],
    ds_nganh_tnhh_2tv: [{ ma_nganh: '6201', ten_nganh: 'Lap trinh', la_nganh_chinh: '' }]
  });
  st.values[KEY] = 'TNHH_2TV';

  const ex = G.exportLoops(st, ['PLI_M72']);
  check('e1. exportLoops: bien te DUOC chon giu du lieu + map X',
    ex.ds_nganh_tnhh_2tv.length === 1 &&
      ex.ds_nganh_tnhh_2tv[0].ma_nganh === '6201' &&
      ex.ds_nganh_tnhh_2tv[0].la_nganh_chinh === '');
  check('e2. exportLoops: bien te INACTIVE bi loa KHOI payload',
    ex.ds_nganh_dntn.length === 0 && ex.ds_nganh_ctcp.length === 0,
    JSON.stringify({ dntn: ex.ds_nganh_dntn.length, ctcp: ex.ds_nganh_ctcp.length }));

  // Mô phỏng đúng cách app.js buildExportData gộp flags vào payload hồ sơ
  const stSel = mkStore({ values: { [KEY]: 'DHDN' } });
  const data = {};
  Object.keys(stSel.values).forEach(k => { data[k] = stSel.values[k]; });
  Object.assign(data, FD.selectorFlagsOf('PLI_M72', stSel)); // như buildExportData
  const wantFlags = {
    loai_hinh_dntn: '', loai_hinh_tnhh_1tv: '', loai_hinh_tnhh_2tv: '',
    loai_hinh_ctcp: '', loai_hinh_dhdn: 'X'
  };
  check('e3. merge kieu buildExportData: du 5 flag dung X/"" cho DHDN',
    Object.keys(wantFlags).every(f => data[f] === wantFlags[f]),
    JSON.stringify(data));
  check('e4. exportLoopsStrict van thong qua khi khong conflict (payload nhu plain)',
    (() => {
      try {
        return JSON.stringify(G.exportLoopsStrict(st, ['PLI_M72'])) ===
          JSON.stringify(ex);
      } catch (err) { return false; }
    })());
})();

// ==== f. Draft cu: migrateDraft + selector gate =============================

(function f() {
  const loopsIn = {
    ds_nganh_ctcp: [
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
      { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy tính' }
    ],
    ds_nganh_dntn: [{ ma_nganh: '0112', ten_nganh: 'Trong ngo' }]
  };
  const idsBefore = {};
  const probe = mkStore(loopsIn);
  Object.keys(probe.loops).forEach(k => {
    idsBefore[k] = probe.loops[k].map(r => r._row_id);
  });

  // draft v2 TRƯỚC thời Option D: KHÔNG có dn.loai_hinh trong values
  const oldDraft = {
    v: 2, caseId: 'm72_truoc_option_d', checkedForms: [], activeDocId: null,
    autoSum: false, viewState: {}, savedAt: null,
    store: {
      values: {}, checks: {},
      loops: JSON.parse(JSON.stringify(probe.loops))
    }
  };
  const mig = FD.migrateDraft(JSON.parse(JSON.stringify(oldDraft)));
  check('f1. migrateDraft: du lieu cu giu nguyen thu tu + _row_id',
    JSON.stringify(mig.store.loops.ds_nganh_ctcp.map(r => r.ma_nganh)) ===
      JSON.stringify(['0111', '4711']) &&
      mig.store.loops.ds_nganh_ctcp.map(r => r._row_id).join() ===
        idsBefore.ds_nganh_ctcp.join() &&
      mig.store.loops.ds_nganh_dntn.map(r => r._row_id).join() ===
        idsBefore.ds_nganh_dntn.join());

  const errsOld = errsOf(mig.store);
  check('f2. draft thieu dn.loai_hinh: validateDocument VAN chan SELECTOR_REQUIRED',
    selErrs(errsOld).length === 1 &&
      selErrs(errsOld)[0].code === 'SELECTOR_REQUIRED' &&
      selErrs(errsOld)[0].severity === 'blocking');

  check('f3. draft thieu dn.loai_hinh: ca 5 grid deu inactive (isActiveGrid)',
    M72_LOOPS.every(ln => !FD.isActiveGrid(
      FD.getGridMeta({ docId: 'PLI_M72', loop: ln }),
      mig.store.loops[ln] || [], mig.store)));

  // draft MOI co dn.loai_hinh -> restore dung trang thai active
  const newDraft = JSON.parse(JSON.stringify(oldDraft));
  newDraft.store.values[KEY] = 'CTCP';
  const migNew = FD.migrateDraft(newDraft);
  const am = {};
  M72_LOOPS.forEach(ln => {
    am[ln] = FD.isActiveGrid(FD.getGridMeta({ docId: 'PLI_M72', loop: ln }),
      migNew.store.loops[ln] || [], migNew.store);
  });
  check('f4. draft CO dn.loai_hinh=CTCP: chi ds_nganh_ctcp active lai',
    am.ds_nganh_ctcp === true &&
      M72_LOOPS.filter(l => l !== 'ds_nganh_ctcp').every(l => am[l] === false),
    JSON.stringify(am));
  check('f5. restore xong: flags suy ra dung X cho loai_hinh_ctcp + het loi selector',
    FD.selectorFlagsOf('PLI_M72', migNew.store).loai_hinh_ctcp === 'X' &&
      selErrs(errsOf(migNew.store)).length === 0);
})();

// ==== g. NEGATIVE: isolate fixture + equals phan biet =======================

(function g() {
  // Snapshot TRƯỚC của production meta + global meta
  const beforeProd = JSON.parse(JSON.stringify(FD.FORM_GRID_META.PLI_M72));
  const beforeGlobal = JSON.parse(JSON.stringify(FD.GRID_META.ds_nganh));

  // Fixture riêng (pattern cũ test_m72_activation N9): clone từ GLOBAL meta
  // rồi mutate SÂU - không được lan sang meta production PLI_M72 hay global.
  const FIX_G = 'FIX_P12_SEL_G';
  const fixLoop = Object.assign(JSON.parse(JSON.stringify(FD.GRID_META.ds_nganh)), {
    semanticKey: 'ds_nganh_dntn',
    activeWhen: { checkedKey: 'chk_loai_hinh_fixture_g' }
  });
  FD.registerFormGridMeta(FIX_G, { loops: { ds_nganh_dntn: fixLoop } });

  const fm = FD.getGridMeta({ docId: FIX_G, loop: 'ds_nganh_dntn' });
  fm.columns.push({ tag: 'hack_col', type: 'text' });
  fm.required = false;
  fm.label = 'HACK';
  if (fm.activeWhen) fm.activeWhen.checkedKey = 'chk_hack';
  if (fm.activeWhen) fm.activeWhen.minFilledRows = 999;

  check('g1. mutate meta fixture KHONG lan sang FORM_GRID_META.PLI_M72',
    JSON.stringify(FD.FORM_GRID_META.PLI_M72) ===
      JSON.stringify(beforeProd),
    'prod changed!');
  check('g2. mutate meta fixture KHONG lan sang GRID_META.ds_nganh',
    JSON.stringify(FD.GRID_META.ds_nganh) === JSON.stringify(beforeGlobal));
  check('g3. resolver tra dung reference fixture da mutate (isolation 2 chieu)',
    FD.getGridMeta({ docId: FIX_G, loop: 'ds_nganh_dntn' }) === fm);
  const prodG = FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_dntn;
  check('g4. meta production van nguyen valueOf DNTN + mode selector',
    prodG.activeWhen.valueOf.key === KEY &&
      JSON.stringify(prodG.activeWhen.valueOf.equals) === '["DNTN"]' &&
      FD.activationModeOf(prodG) === 'selector' &&
      !prodG.columns.some(c => c.tag === 'hack_col'));

  // Hai loop không bao giờ cùng equals: 5 điều kiện phân biệt hoàn toàn
  const eqSigs = M72_LOOPS.map(ln => {
    const gm = FD.FORM_GRID_META.PLI_M72.loops[ln];
    return JSON.stringify(gm.activeWhen.valueOf.equals);
  });
  check('g5. 5 equals phan biet: moi loop dung 1 gia tri canonical rieng',
    new Set(eqSigs).size === 5 &&
      M72_LOOPS.every((ln, i) =>
        eqSigs[i] === JSON.stringify(
          [ln.replace(/^ds_nganh_/, '').toUpperCase()]) &&
        SEL.options.some(o => o.value ===
          ln.replace(/^ds_nganh_/, '').toUpperCase() &&
          FD.FORM_GRID_META.PLI_M72.loops[ln].activeWhen.valueOf.equals[0] === o.value)));
})();

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('test_p12_m72_selector: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
