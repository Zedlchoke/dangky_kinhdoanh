/* test_p3_e2e.js — LANE P3: E2E use-case + export DOCX gate (suite MỚI, chỉ test).
 *
 * Chạy:  node app_web/test_p3_e2e.js
 *
 * Phạm vi (không sửa production):
 *  1. Đi qua TẤT CẢ use case trong app/data/use_cases.json:
 *     - tập form bắt buộc / tùy chọn resolve đúng qua FormFlow.buildFormMeta;
 *     - forms_oneOf resolve đúng nhóm loại trừ + max, gate chọn mẫu
 *       (checkFormSelection) và tự loại trừ (applyOneOfExclusive);
 *     - restoreSelection từ draft: bắt buộc luôn tick, nhóm không vượt max;
 *     - mọi docId tồn tại thật trong app/data/blocks (không mock).
 *  2. Một use case representative (chuyen_doi_hkd_sang_dn: PLI_M01..M04 —
 *     case duy nhất vừa có nhóm oneOf vừa có key dùng chung dn.ten_* và loop
 *     dùng chung ds_nganh trên cả 4 mẫu) — assert giá trị đặt MỘT LẦN lan sang
 *     payload export của >=2 mẫu:
 *       - HTML render của từng mẫu chứa đúng giá trị đó;
 *       - GridCtl.exportLoops / exportLoopsStrict trả payload sạch (_* bị bỏ),
 *         không xung đột contract;
 *       - section payload (FD.recomputeSections) cùng store cho PLI_M04;
 *       - DOCX render thật của >=2 mẫu chứa giá trị shared key.
 *  3. DOCX export gate qua tools/docx_render.write_rendered (sandbox temp dir,
 *     không đụng generated_ho_so): >=3 mẫu đại diện
 *        - editable-grid : PLI_M06 (ds_thanh_vien_tnhh);
 *        - fixed-matrix  : PLI_M02 + PLI_M01 (nguon_von_dieu_le / co_cau_...);
 *        - cùng case representative: PLI_M04 (mẫu khác trong nhóm oneOf);
 *        - M72 với selector dn.loai_hinh (5 biến thể + 1 case không chọn).
 *     assert output KHÔNG còn token `{`, `}`, `{#`, `{/`, `{?`, `{_stt`
 *     (dùng cả LEFTOVER_RE của chính engine) và với M72 render 5 lần sel khác
 *     nhau thì mỗi bản chỉ chứa bảng ngành của ĐÚNG 1 biến thể (scan marker
 *     ds_nganh_dntn... trong XML template vs XML render + anchor đặc trưng).
 *
 * Ghi chú NOT RUN: môi trường Windows/WebView2/pywebview KHÔNG có trên máy
 * này nên đường Bridge.export thật (app_web/main.py) không chạy được — suite
 * này dựng đúng bước render python của Bridge (write_rendered) thay thế.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');
const G = App.GridCtl;
const FF = App.FormFlow;

const ROOT = path.join(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'app', 'data', 'blocks');
const UC = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'app', 'data', 'use_cases.json'), 'utf8'));
const FMAPS = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'app', 'data', 'form_maps.json'), 'utf8'));

let passed = 0, failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function section(t) { console.log('\n===== ' + t + ' ====='); }

function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
function loopBlock(doc, name) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === name)[0] || null;
}
function inputKeysOf(doc) {
  const keys = [];
  (function walk(x) {
    if (Array.isArray(x)) return x.forEach(walk);
    if (!x || typeof x !== 'object') return;
    if (x.input && x.input.key) keys.push(x.input.key);
    if (x.key) keys.push(x.key);
    Object.keys(x).forEach(k => walk(x[k]));
  })(doc.blocks);
  return keys;
}
function newStore() { return { values: {}, checks: {}, loops: {} }; }
/* gridMetaForDoc — giống app.js (form-scoped trước, fallback toàn cục). */
function gridMetaForDoc(docId) {
  const m = Object.assign({}, FD.GRID_META);
  const fm = FD.FORM_GRID_META[docId];
  if (fm && fm.loops) Object.assign(m, fm.loops);
  return m;
}
/* Render đúng cách renderActiveDoc của app.js. */
function renderDoc(docId, store) {
  const doc = loadProd(docId);
  const sel = FD.getFormSelector(docId);
  const selHtml = sel ? R.selectorHtml(sel, R.makeAccessors(store)) : '';
  return R.renderBlocks(doc, store, {
    docId: docId,
    fieldMeta: FD.FIELD_META,
    gridMeta: gridMetaForDoc(docId),
    sectionContracts: FD.sectionContractsOf(docId),
    flags: FD.selectorFlagsOf(docId, store),
    selectorHtml: selHtml
  });
}
/* Bản flatten payload export — đúng hình dạng buildExportData() của app.js:
 * values phẳng + checks -> 'X'/'' + flags selector của từng mẫu + loops. */
function buildExportData(store, docIds) {
  const data = {};
  Object.keys(store.values).forEach(k => { data[k] = store.values[k]; });
  Object.keys(store.checks).forEach(k => { data[k] = store.checks[k] ? 'X' : ''; });
  docIds.forEach(id => Object.assign(data, FD.selectorFlagsOf(id, store)));
  const loops = G.exportLoopsStrict(store, docIds);
  Object.keys(loops).forEach(name => { data[name] = loops[name]; });
  return data;
}

// ======================================================================
// 1. Dữ liệu use_cases.json — 27 use case
// ======================================================================
section('1. use_cases.json: 27 use case, id duy nhat, moi case co forms');
const CASES = UC.cases || [];
check('P3-UC1: dung 27 use case trong use_cases.json', CASES.length === 27,
  'n=' + CASES.length);
check('P3-UC2: id use case duy nhat',
  new Set(CASES.map(c => c.id)).size === CASES.length);
check('P3-UC3: moi case khai bao >=1 form',
  CASES.every(c => Array.isArray(c.forms) && c.forms.length > 0));

// ======================================================================
// 2. Resolve tập form bắt buộc / tùy chọn / oneOf cho TẤT CẢ case
// ======================================================================
section('2. Resolve form bat buoc / tuy chon / oneOf cho tung case');
let allResolved = true, allGates = true, allExclusive = true, allRestore = true;
const DETAIL = [];
CASES.forEach(cs => {
  const ids = FF.formIds(cs);
  const meta = FF.buildFormMeta(cs);
  const required = ids.filter(id => meta[id] && meta[id].bat_buoc);
  const optional = ids.filter(id => meta[id] && !meta[id].bat_buoc);
  const groups = cs.forms_oneOf || [];

  // 2a. mọi docId trỏ tới blocks thật
  const missing = ids.filter(id => {
    try {
      const doc = loadProd(id);
      return !(Array.isArray(doc.blocks) && doc.blocks.length) || doc.id !== id;
    } catch (e) { return true; }
  });
  if (missing.length) { allResolved = false; DETAIL.push(cs.id + ' missing ' + missing); }

  // 2b. metadata bắt buộc / tùy chọn khớp dữ liệu nguồn (bat_buoc thiếu = true)
  const wantReq = (cs.forms || []).filter(f => f.bat_buoc !== false)
    .map(FF.formIdOf).sort();
  if (JSON.stringify(wantReq) !== JSON.stringify(required.slice().sort())) {
    allResolved = false;
    DETAIL.push(cs.id + ' req ' + required + ' != ' + wantReq);
  }
  if (required.length + optional.length !== ids.length) {
    allResolved = false; DETAIL.push(cs.id + ' req/opt khong cover toan bo form');
  }

  // 2c. nhóm oneOf: max >= 1, gid nhất quán, ids không trỏ ra ngoài case
  let grpOk = true;
  groups.forEach((g, gi) => {
    if (!Array.isArray(g.ids) || !g.ids.length) grpOk = false;
    if (g.max != null && g.max < 1) grpOk = false;
    const gid = 'oneof_' + gi;
    g.ids.forEach(id => {
      if (!meta[id]) { grpOk = false; return; }
      if (!meta[id].oneOf || meta[id].oneOf.gid !== gid ||
          meta[id].oneOf.max !== (g.max == null ? 1 : g.max)) grpOk = false;
      if (ids.indexOf(id) < 0) grpOk = false; // nhóm không trỏ ra ngoài case
    });
  });
  if (!grpOk) { allResolved = false; DETAIL.push(cs.id + ' oneOf contract'); }

  // 2d. gate chọn mẫu: bỏ trống -> thiếu bắt buộc (+ oneOf rỗng nếu có nhóm)
  const errsEmpty = FF.checkFormSelection(meta, [], {});
  const missReq = errsEmpty.filter(e => e.code === 'FORM_REQUIRED_MISSING');
  if (missReq.length !== required.length) {
    allGates = false; DETAIL.push(cs.id + ' empty-gate ' + missReq.length + '/' + required.length);
  }
  const hasGrp = groups.length > 0;
  if (hasGrp !== errsEmpty.some(e => e.code === 'FORM_ONEOF_EMPTY')) {
    allGates = false; DETAIL.push(cs.id + ' oneof-empty-gate');
  }

  // 2e. gate chọn đúng: mọi bắt buộc + đúng 1 (hoặc max) mẫu của mỗi nhóm
  const picked = required.slice();
  groups.forEach(g => picked.push(g.ids[0]));
  const errsOk = FF.checkFormSelection(meta, picked, {});
  if (errsOk.some(e => e.severity === 'blocking')) {
    allGates = false; DETAIL.push(cs.id + ' valid-gate ' + JSON.stringify(errsOk));
  }

  // 2f. vượt max: tick toàn bộ nhóm -> FORM_ONEOF_EXCEED
  groups.forEach(g => {
    if (g.ids.length <= (g.max == null ? 1 : g.max)) return;
    const errsAll = FF.checkFormSelection(meta, required.concat(g.ids), {});
    if (!errsAll.some(e => e.code === 'FORM_ONEOF_EXCEED')) {
      allGates = false; DETAIL.push(cs.id + ' exceed-gate');
    }
  });

  // 2g. applyOneOfExclusive: mẫu vừa tick luôn còn tick, nhóm không vượt max
  groups.forEach(g => {
    const max = g.max == null ? 1 : g.max;
    const state0 = {};
    g.ids.forEach(id => { state0[id] = true; }); // cố tình vượt max
    g.ids.forEach(id => {
      const out = FF.applyOneOfExclusive(meta, state0, id);
      if (!out[id]) { allExclusive = false; DETAIL.push(cs.id + ' tick-lost ' + id); }
      const on = g.ids.filter(x => out[x]).length;
      if (on > max) { allExclusive = false; DETAIL.push(cs.id + ' over-max ' + on); }
    });
  });

  // 2h. restoreSelection: bắt buộc luôn tick; nhóm <= max; active hợp lệ
  const firstPick = groups.length ? groups[0].ids[0] : required[0];
  const docs = ids.map(id => ({ id, ten_mau: id }));
  const rs = FF.restoreSelection(meta, docs, {
    checkedForms: firstPick ? [firstPick] : [],
    activeDocId: firstPick || null
  });
  if (!required.every(id => rs.checkedForms[id])) {
    allRestore = false; DETAIL.push(cs.id + ' restore-required');
  }
  groups.forEach(g => {
    const on = g.ids.filter(id => rs.checkedForms[id]).length;
    if (on > (g.max == null ? 1 : g.max)) {
      allRestore = false; DETAIL.push(cs.id + ' restore-over-max');
    }
  });
  if (rs.activeDocId && ids.indexOf(rs.activeDocId) < 0) {
    allRestore = false; DETAIL.push(cs.id + ' restore-active');
  }
  /* case có >=1 mẫu bắt buộc thì active phải rơi về một mẫu đang được chọn;
   * case toàn mẫu tùy chọn chưa tick gì -> active rỗng là hành vi đúng. */
  if (required.length && !rs.activeDocId) {
    allRestore = false; DETAIL.push(cs.id + ' restore-no-active');
  }
});

check('P3-UC4: 27/27 case resolve du tap form + blocks that ton tai (' +
  CASES.length + ' case)', allResolved, DETAIL.slice(0, 4).join(' | '));
check('P3-UC5: gate chon mau (bat buoc thieu / oneOf trong / vuot max) dung cho 27/27 case',
  allGates, DETAIL.slice(0, 4).join(' | '));
check('P3-UC6: applyOneOfExclusive khong mat mau vua tick + khong vuot max',
  allExclusive, DETAIL.slice(0, 4).join(' | '));
check('P3-UC7: restoreSelection tu draft — bat buoc luon tick, nhom <= max',
  allRestore, DETAIL.slice(0, 4).join(' | '));

// case chuyen_doi_hkd_sang_dn: nhom oneOf 4 mau loai tru max=1 (contract data)
{
  const cs = CASES.filter(c => c.id === 'chuyen_doi_hkd_sang_dn')[0];
  const g = (cs.forms_oneOf || [])[0];
  check('P3-UC8: chuyen_doi_hkd_sang_dn co nhom loai tru 4 mau PLI_M01..M04 max=1',
    !!g && g.ids.length === 4 && g.max === 1 &&
    JSON.stringify(g.ids) === JSON.stringify(['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']),
    JSON.stringify(g));
  const meta = FF.buildFormMeta(cs);
  const only2 = FF.applyOneOfExclusive(meta, { PLI_M01: true, PLI_M02: true, PLI_M03: true }, PLI_M03());
  function PLI_M03() { return 'PLI_M03'; }
  check('P3-UC9: tick sau thang — chi mau vua tick con lai trong nhom',
    only2.PLI_M03 === true && !only2.PLI_M01 && !only2.PLI_M02,
    JSON.stringify(only2));
}

// ======================================================================
// 3. Representative case: chuyen_doi_hkd_sang_dn — shared key lan sang >=2 mau
// ======================================================================
section('3. Case dai dien chuyen_doi_hkd_sang_dn (PLI_M01..M04) - shared key');
/* Đây là case DUY NHẤT của bộ 27 vừa có nhóm oneOf vừa có key dùng chung
 * (dn.ten_tieng_viet / dn.ten_nuoc_ngoai / dn.ten_viet_tat) và loop dùng chung
 * (ds_nganh) trên cả 4 mẫu. Nhóm oneOf max=1 nghĩa là MỘT thời điểm chỉ in một
 * mẫu: giá trị đặt MỘT LẦN trong store phải lan sang payload của BẤT KỲ mẫu
 * nào được chọn (không được phụ thuộc mẫu được chọn đầu tiên).
 * Selector dn.loai_hinh chỉ tồn tại trên PLI_M72 và PLI_M72 KHÔNG thuộc use
 * case nào trong 27 case -> phần selector được kiểm ở mục 4 (DOCX M72 ×5 sel)
 * và P3-DX9 (UI render theo sel). */
const REP = CASES.filter(c => c.id === 'chuyen_doi_hkd_sang_dn')[0];
const REP_IDS = FF.formIds(REP);              // [PLI_M01, PLI_M02, PLI_M03, PLI_M04]
const REP_GROUP = (REP.forms_oneOf || [])[0];
const SHARED_KEYS = ['dn.ten_tieng_viet', 'dn.ten_nuoc_ngoai', 'dn.ten_viet_tat'];
const SHARED_VALS = {
  'dn.ten_tieng_viet': 'CONG TY P3 E2E',
  'dn.ten_nuoc_ngoai': 'P3 E2E CO., LTD',
  'dn.ten_viet_tat': 'P3E2E'
};
check('P3-RP0: khong use case nao trong 27 case chua PLI_M72 (mang selector) '
  + '-> selector kiem o muc DOCX/M72',
  CASES.every(c => FF.formIds(c).indexOf('PLI_M72') < 0) &&
    Object.keys(FD.FORM_SELECTOR_META).join(',') === 'PLI_M72',
  JSON.stringify(CASES.filter(c => FF.formIds(c).indexOf('PLI_M72') >= 0).map(c => c.id)));
check('P3-RP1: case dai dien gom PLI_M01 + PLI_M02 + PLI_M03 + PLI_M04',
  JSON.stringify(REP_IDS) === JSON.stringify(['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']),
  JSON.stringify(REP_IDS));
check('P3-RP2: key dung chung dn.ten_* co tren ca 4 mau',
  REP_IDS.every(id => {
    const keys = inputKeysOf(loadProd(id));
    return SHARED_KEYS.every(k => keys.indexOf(k) >= 0);
  }),
  REP_IDS.map(id => inputKeysOf(loadProd(id))
    .filter(k => SHARED_KEYS.indexOf(k) >= 0).join(',')).join(' | '));

const repStore = newStore();
Object.assign(repStore.values, SHARED_VALS);
repStore.loops.ds_nganh = [
  { _row_id: 'rP3_1', ten_nganh: 'Trong lua', ma_nganh: '0111',
    chi_tiet: '', la_nganh_chinh: 'X' },
  { _row_id: 'rP3_2', ten_nganh: 'Ban le may tinh', ma_nganh: '4711',
    chi_tiet: '', la_nganh_chinh: '' }
];
/* PLI_M04 còn section fixed-matrix co_cau_loai_co_phan — điền đúng shape để
 * kiểm section payload cùng store. */
repStore.values['co_cau_loai_co_phan.co_phan_pho_thong.so_luong'] = '1000000';
repStore.values['co_cau_loai_co_phan.co_phan_pho_thong.gia_tri_vnd'] = '1000000000';

const repPayload = G.exportLoops(repStore, REP_IDS);
check('P3-RP3: exportLoopsStrict 4 mau — khong nem, khong conflict contract',
  (() => {
    try {
      const out = G.exportLoopsStrict(repStore, REP_IDS);
      return G.lastExportConflicts.length === 0 &&
        !!out.ds_nganh && out.ds_nganh.length === 2;
    } catch (e) { return 'THROW ' + e.message; }
  })(),
  JSON.stringify(G.lastExportConflicts));
check('P3-RP4: payload bo field noi bo _* (giu du lieu nghiep vu)',
  repPayload.ds_nganh.every(r => Object.keys(r).every(k => k.charAt(0) !== '_')) &&
    repPayload.ds_nganh[0].ma_nganh === '0111' &&
    repPayload.ds_nganh[0].la_nganh_chinh === 'X' &&
    repPayload.ds_nganh[1].la_nganh_chinh === '',
  JSON.stringify(repPayload.ds_nganh));

// loop ds_nganh la TEN CHUNG cua ca 4 mau -> payload mot mang phuc vu 4 mau
check('P3-RP5: loop ds_nganh dung chung boi ca 4 mau (payload 1 mang)',
  REP_IDS.every(id => !!loopBlock(loadProd(id), 'ds_nganh')) &&
    repPayload.ds_nganh.length === 2,
  REP_IDS.map(id => String(!!loopBlock(loadProd(id), 'ds_nganh'))).join(','));

// giá trị shared key lan sang render của TỪNG mẫu trong nhóm oneOf
const repHtml = {};
REP_IDS.forEach(id => { repHtml[id] = renderDoc(id, repStore); });
check('P3-RP6: shared key LAN sang render cua >=2 mau (ca 4 mau deu thay gia tri)',
  REP_IDS.filter(id => SHARED_KEYS.every(k =>
    repHtml[id].indexOf('value="' + SHARED_VALS[k] + '"') >= 0)).length >= 2,
  REP_IDS.map(id => SHARED_KEYS.map(k =>
    repHtml[id].indexOf('value="' + SHARED_VALS[k] + '"') >= 0).join('/')).join(' | '));

// section payload: cùng store cho PLI_M04 -> tổng recompute từ công thức khai
const repProj = FD.recomputeSections('PLI_M04', repStore);
check('P3-RP7: section payload PLI_M04 recompute tu cung store',
  repProj['co_cau_loai_co_phan.tong_so.so_luong'] &&
    repProj['co_cau_loai_co_phan.tong_so.so_luong'].value === 1000000 &&
    repProj['co_cau_loai_co_phan.tong_so.gia_tri_vnd'].value === 1000000000,
  JSON.stringify(repProj));
check('P3-RP8: section payload khong ro ra field noi bo _*',
  Object.keys(repProj).every(k => k.charAt(0) !== '_') &&
    Object.keys(repProj).every(k => Object.keys(repProj[k])
      .every(x => x.charAt(0) !== '_')));

// ======================================================================
// 4. DOCX export gate — sandbox write_rendered (temp dir, không đụng repo)
// ======================================================================
section('4. DOCX export gate qua tools/docx_render.write_rendered');
const M72_LOOPS = ['ds_nganh_dntn', 'ds_nganh_tnhh_1tv', 'ds_nganh_tnhh_2tv',
  'ds_nganh_ctcp', 'ds_nganh_dhdn'];
const M72_ANCHOR = {
  ds_nganh_dntn: 'Chủ doanh nghiệp',
  ds_nganh_tnhh_1tv: 'Thông tin về chủ sở hữu',
  ds_nganh_tnhh_2tv: 'Danh sách thành viên:',
  ds_nganh_ctcp: 'Cổ đông sáng lập',
  ds_nganh_dhdn: 'Danh sách thành viên hợp danh'
};
const NGANH_ROWS = [
  { ten_nganh: 'Trong lua', ma_nganh: '0111', chi_tiet: '', la_nganh_chinh: 'X' },
  { ten_nganh: 'Ban le may tinh', ma_nganh: '4711', chi_tiet: '', la_nganh_chinh: '' }
];

function m72Data(sel) {
  const d = {
    'dn.ten_tieng_viet': 'CONG TY CO PHAN P3 E2E',
    'dn.ma_so_dn': '031234567890'
  };
  M72_LOOPS.forEach(l => {
    const flag = 'loai_hinh_' + l.replace('ds_nganh_', '').toLowerCase();
    d[flag] = (sel && l === 'ds_nganh_' + sel.toLowerCase()) ? 'X' : '';
    d[l] = JSON.parse(JSON.stringify(NGANH_ROWS));
  });
  return d;
}

/* Payload export của case representative đi thẳng vào render DOCX. */
const repExportData = buildExportData(repStore, REP_IDS);
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-e2e-'));
const SPEC = { renders: [] };
function addRender(id, data, extra) {
  const fmap = FMAPS[id];
  if (!fmap || !fmap.template) throw new Error('form_maps thieu template ' + id);
  SPEC.renders.push(Object.assign({
    id: id,
    template: path.join(ROOT, 'app', fmap.template),
    out: path.join(TMP, id + '_' + SPEC.renders.length + '.docx'),
    data: data,
    /* main.py goi write_rendered voi (fmap.get("section_specs") or None):
     * mang rong phai tro thanh null, khong truyen [] xuong engine. */
    tables_meta: (fmap.section_specs && fmap.section_specs.length)
      ? fmap.section_specs : null,
    markers: (id === 'PLI_M72') ? M72_LOOPS : []
  }, extra || {}));
}
addRender('PLI_M06', (() => {                 // editable-grid
  const d = Object.assign({}, repExportData);
  d['ds_thanh_vien_tnhh'] = G.exportLoops({
    values: {}, checks: {},
    loops: { ds_thanh_vien_tnhh: [
      { _row_id: 'rP3_a', ho_ten: 'NGUYEN VAN A', so_cccd: '012345678901',
        von_dong_gop: '1000000' },
      { _row_id: 'rP3_b', ho_ten: 'TRAN THI B', so_cccd: '012345678902',
        von_dong_gop: '2000000' }
    ] }
  })['ds_thanh_vien_tnhh'];
  return d;
})(), { expect_present: ['NGUYEN VAN A', '012345678901', '1000000', '2000000'] });
/* Hai mẫu của case representative (nhóm oneOf) nhận CÙNG payload export ->
 * shared key phải xuất hiện trên CẢ HAI file DOCX. */
addRender('PLI_M02', Object.assign({}, repExportData, {
  // fixed-matrix theo semantic_key = đường dẫn tag của template
  'nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong': '5000000000',
  'nguon_von_dieu_le.von_tu_nhan.ty_le': '100'
}), { expect_present: ['5000000000', '100', SHARED_VALS['dn.ten_tieng_viet'],
  SHARED_VALS['dn.ten_viet_tat']] });
addRender('PLI_M04', Object.assign({}, repExportData, {
  'co_cau_loai_co_phan.co_phan_pho_thong.so_luong': '1000000',
}), { expect_present: [SHARED_VALS['dn.ten_tieng_viet'],
  SHARED_VALS['dn.ten_nuoc_ngoai'], SHARED_VALS['dn.ten_viet_tat']] });
addRender('PLI_M01', Object.assign({}, repExportData, {
  'co_cau_tai_san_gop_von_dau_tu.dong_viet_nam.gia_tri_vnd': '1200000000',
  'co_cau_tai_san_gop_von_dau_tu.dong_viet_nam.ty_le': '60'
}), { expect_present: ['1200000000', '60'] });
M72_LOOPS.forEach(l => {
  const sel = l.replace('ds_nganh_', '').toUpperCase();
  addRender('PLI_M72', m72Data(sel), {
    label: 'M72/' + sel,
    expect_present: [M72_ANCHOR[l]],
    expect_absent: M72_LOOPS.filter(x => x !== l).map(x => M72_ANCHOR[x]),
    expect_tables: 1, expect_anchor_of: M72_LOOPS
  });
});
addRender('PLI_M72', m72Data(''), {
  label: 'M72/<khong chon>',
  expect_present: [],
  expect_absent: M72_LOOPS.map(x => M72_ANCHOR[x]),
  expect_tables: 0, expect_anchor_of: M72_LOOPS
});
const specPath = path.join(TMP, 'spec.json');
fs.writeFileSync(specPath, JSON.stringify(SPEC), 'utf8');
/* Spec phụ: chỉ scan template M72 trước khi render (nhập liệu cho P3-DX0). */
const tplSpecPath = path.join(TMP, 'spec_tpl.json');
fs.writeFileSync(tplSpecPath, JSON.stringify({ renders: [{
  id: 'PLI_M72_TEMPLATE', label: 'M72/template',
  template: path.join(ROOT, 'app', FMAPS['PLI_M72'].template),
  out: '', template_only: true, data: {}, tables_meta: null,
  markers: M72_LOOPS
}] }), 'utf8');

/* Driver python ghi vào TMP (KHÔNG tạo file trong repo). */
const PY = [
  'import json, os, re, sys, zipfile',
  'sys.path.insert(0, os.getcwd())',
  'from tools.docx_render import write_rendered, LEFTOVER_RE',
  'spec = json.load(open(sys.argv[1], encoding="utf-8"))',
  'def nest(data):',
  '    out = {}',
  '    for k, v in data.items():',
  '        parts = str(k).split(".")',
  '        if len(parts) == 1:',
  '            out[k] = v; continue',
  '        cur = out',
  '        for p in parts[:-1]:',
  '            nxt = cur.get(p)',
  '            if not isinstance(nxt, dict):',
  '                nxt = {}; cur[p] = nxt',
  '            cur = nxt',
  '        cur[parts[-1]] = v',
  '    return out',
  'results = []',
  'for r in spec["renders"]:',
  '    item = {"id": r["id"], "label": r.get("label") or r["id"]}',
  '    try:',
  '        if r.get("template_only"):',
  '            z = zipfile.ZipFile(r["template"])',
  '            xml = "".join(z.read(n).decode("utf-8") for n in z.namelist()',
  '                          if n.startswith("word/") and (n.endswith("document.xml") or "header" in n or "footer" in n))',
  '            z.close()',
  '            item["markers"] = {m: xml.count(m) for m in r.get("markers", [])}',
  '            item["bytes"] = len(xml)',
  '            results.append(item)',
  '            continue',
  '        write_rendered(r["template"], nest(r["data"]), r["out"],',
  '                       tables_meta=r.get("tables_meta"))',
  '        z = zipfile.ZipFile(r["out"])',
  '        xml = "".join(z.read(n).decode("utf-8") for n in z.namelist()',
  '                      if n.startswith("word/") and (n.endswith("document.xml") or "header" in n or "footer" in n))',
  '        z.close()',
  '        item["bytes"] = len(xml)',
  '        item["leftover"] = sorted(set(LEFTOVER_RE.findall(xml)))',
  '        item["raw_braces"] = xml.count("{") + xml.count("}")',
  '        item["tokens"] = {t: xml.count(t) for t in ("{#", "{/", "{?", "{_stt")}',
  '        item["markers"] = {m: xml.count(m) for m in r.get("markers", [])}',
  '        item["tables"] = len(re.findall(r"<w:tbl[ >]", xml))',
  '        item["present"] = {s: (s in xml) for s in r.get("expect_present", [])}',
  '        item["absent"] = {s: (s not in xml) for s in r.get("expect_absent", [])}',
  '        item["stt_tokens"] = len(re.findall(r"<w:t[^>]*>[1-9][0-9]*</w:t>", xml))',
  '    except Exception as exc:',
  '        item["error"] = "%s: %s" % (type(exc).__name__, exc)',
  '    results.append(item)',
  'print(json.dumps(results, ensure_ascii=False))'
].join('\n');
const pyPath = path.join(TMP, 'driver.py');
fs.writeFileSync(pyPath, PY, 'utf8');

function runPyDriver(specFile) {
  const INTERPS = ['python -X utf8', 'python3 -X utf8'];
  let last = null;
  for (let i = 0; i < INTERPS.length; i++) {
    try {
      const out = execSync(INTERPS[i] + ' "' + pyPath + '" "' +
        (specFile || specPath) + '"', {
        cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      return JSON.parse(String(out).trim().split(/\r?\n/).pop());
    } catch (e) {
      last = e;
      const status = (e && e.status != null) ? e.status : 1;
      const noInterp = status === 127 || (e && e.code === 'ENOENT');
      if (!noInterp || i === INTERPS.length - 1) {
        return [{
          id: '@driver', label: '@driver',
          error: 'python exit ' + status + ': ' +
            String((e && e.stderr) || (e && e.message) || '').slice(0, 400)
        }];
      }
    }
  }
  return [{ id: '@driver', label: '@driver', error: String(last) }];
}
const RESULTS = runPyDriver();
const byLabel = {};
RESULTS.forEach(r => { byLabel[r.label || r.id] = r; });

// 4a. template trước khi render phải còn đủ marker -> phép scan có nghĩa
const tplResult = (runPyDriver(tplSpecPath) || [])[0] || null;
check('P3-DX0: template PLI_M72 con du 5 marker loop de scan (nhap lieu gate)',
  !!tplResult && !tplResult.error &&
    M72_LOOPS.every(l => (tplResult.markers || {})[l] >= 1),
  JSON.stringify(tplResult && tplResult.markers));

const NO_TOKEN_DOCS = ['M72/DNTN', 'M72/TNHH_1TV', 'M72/TNHH_2TV', 'M72/CTCP',
  'M72/DHDN', 'M72/<khong chon>', 'PLI_M02', 'PLI_M04', 'PLI_M01', 'PLI_M06'];
check('P3-DX1: driver python chay duoc, du ' + NO_TOKEN_DOCS.length + ' ban render',
  NO_TOKEN_DOCS.every(l => byLabel[l] && !byLabel[l].error),
  JSON.stringify(RESULTS.filter(r => r.error).map(r => r.label + ':' + r.error)));

NO_TOKEN_DOCS.forEach(l => {
  const r = byLabel[l] || {};
  const ok = !r.error && r.leftover && r.leftover.length === 0 &&
    r.raw_braces === 0 && Object.values(r.tokens || {}).every(n => n === 0);
  check('P3-DX2[' + l + ']: output KHONG con token { } {# {/ {? {_stt (' +
    (r.bytes || 0) + ' bytes xml)', ok,
    JSON.stringify({ leftover: r.leftover, raw_braces: r.raw_braces, tokens: r.tokens,
      error: r.error }));
});

// >=3 mau dai dien: editable (PLI_M06) + fixed-matrix (PLI_M02, PLI_M01)
check('P3-DX3: PLI_M06 (editable-grid) nhan du dong thanh vien tu payload',
  (() => { const r = byLabel['PLI_M06'] || {}; const p = r.present || {};
    return !r.error && ['NGUYEN VAN A', '012345678901', '1000000', '2000000']
      .every(s => p[s] === true); })(),
  JSON.stringify((byLabel['PLI_M06'] || {}).present));
check('P3-DX4: PLI_M02 (fixed-matrix) nhan gia tri nguon_von_dieu_le + shared key',
  (() => { const r = byLabel['PLI_M02'] || {}; const p = r.present || {};
    return !r.error && ['5000000000', '100', SHARED_VALS['dn.ten_tieng_viet'],
      SHARED_VALS['dn.ten_viet_tat']].every(s => p[s] === true); })(),
  JSON.stringify((byLabel['PLI_M02'] || {}).present));
check('P3-DX4b: PLI_M04 (cung case, mau khac trong nhom oneOf) cung nhan shared key',
  (() => { const r = byLabel['PLI_M04'] || {}; const p = r.present || {};
    return !r.error && [SHARED_VALS['dn.ten_tieng_viet'],
      SHARED_VALS['dn.ten_nuoc_ngoai'], SHARED_VALS['dn.ten_viet_tat']]
      .every(s => p[s] === true); })(),
  JSON.stringify((byLabel['PLI_M04'] || {}).present));
check('P3-DX5: PLI_M01 (fixed-matrix) nhan gia tri tai san gop von',
  (() => { const r = byLabel['PLI_M01'] || {}; const p = r.present || {};
    return !r.error && ['1200000000', '60'].every(s => p[s] === true); })(),
  JSON.stringify((byLabel['PLI_M01'] || {}).present));
check('P3-DX6: PLI_M02 giu du bang nganh {_stt} da thay bang so 1/2 (khong con _stt)',
  (() => { const r = byLabel['PLI_M02'] || {};
    return !r.error && (r.tokens || {})['{_stt'] === 0 &&
      (r.stt_tokens || 0) >= 2; })(),
  JSON.stringify({ tokens: (byLabel['PLI_M02'] || {}).tokens,
    stt: (byLabel['PLI_M02'] || {}).stt_tokens }));

// M72: 5 sel khác nhau -> mỗi bản chỉ chứa bảng ngành của đúng 1 biến thể
const m72Detail = RESULTS
  .filter(r => (r.label || '').indexOf('M72/') === 0)
  .map(r => ({
    l: r.label,
    tables: r.tables,
    markers_sot: Object.keys(r.markers || {}).filter(k => r.markers[k] > 0),
    anchor_on: Object.keys(r.present || {}).filter(k => r.present[k]),
    anchor_vang: Object.keys(r.absent || {}).filter(k => r.absent[k])
  }));
check('P3-DX7: M72 render 5 lan sel khac nhau — moi ban dung 1 bang + dung 1 anchor',
  M72_LOOPS.every(l => {
    const r = byLabel['M72/' + l.replace('ds_nganh_', '').toUpperCase()] || {};
    if (r.error || r.tables !== 1) return false;
    // marker loop bi engine tieu thu khi render: KHONG con marker nao sot
    if (M72_LOOPS.some(x => (r.markers || {})[x] > 0)) return false;
    // dung anchor cua bien the duoc chon, 4 anchor con lai phai VANG
    if ((r.present || {})[M72_ANCHOR[l]] !== true) return false;
    return M72_LOOPS.filter(x => x !== l)
      .every(x => (r.absent || {})[M72_ANCHOR[x]] === true);
  }),
  JSON.stringify(m72Detail));

check('P3-DX8: M72 khong chon loai hinh -> khong con bang nganh nao',
  (() => { const r = byLabel['M72/<khong chon>'] || {};
    return !r.error && r.tables === 0 &&
      M72_LOOPS.every(x => !((r.present || {})[M72_ANCHOR[x]])) &&
      M72_LOOPS.every(x => (r.absent || {})[M72_ANCHOR[x]] === true); })(),
  JSON.stringify(byLabel['M72/<khong chon>']));

// M72 phía UI: selector chỉ để đúng 1 biến thể vào DOM
check('P3-DX9: UI PLI_M72 render theo sel -> dung 1 bang nganh trong HTML',
  (() => {
    const st = newStore();
    st.values['dn.loai_hinh'] = 'CTCP';
    const html = renderDoc('PLI_M72', st);
    const on = M72_LOOPS.filter(l => html.indexOf('data-loop="' + l + '"') >= 0);
    return on.length === 1 && on[0] === 'ds_nganh_ctcp';
  })(),
  (() => {
    const st = newStore(); st.values['dn.loai_hinh'] = 'CTCP';
    return M72_LOOPS.filter(l =>
      renderDoc('PLI_M72', st).indexOf('data-loop="' + l + '"') >= 0).join(',');
  })());

// dọn dẹp temp dir (ngoài repo)
try { fs.rmSync(TMP, { recursive: true, force: true }); } catch (e) { /* ignore */ }

// ------------------------------------------------------------------ summary
console.log('-'.repeat(64));
console.log('test_p3_e2e: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
