/* test_m72_activation.js - P1.1 "M72 ACTIVATION CONTRACT" (mechanism only).
 *
 * PLI_M72 CHƯA có contract owner cho selector loại hình DN (audit:
 * docs/m72_activation_proposal.md) -> production giữ activation INTERIM
 * (minFilledRows). File này chứng minh CƠ CHẾ data-driven đã sẵn sàng bằng
 * METADATA GIẢ ĐỊNH chỉ tồn tại trong fixture (registerFormGridMeta),
 * KHÔNG đụng FORM_GRID_META production và KHÔNG tự chế mapping pháp lý:
 *  1. Đúng MỘT section M72 active khi selector chọn đúng 1 loại hình.
 *  2. Section active TRỐNG + required -> blocking (INDUSTRY_REQUIRED).
 *  3. Các section inactive KHÔNG sinh lỗi nào (kể cả khi đang chứa dữ liệu).
 *  4. Section active có ngành nhưng thiếu ngành chính -> PRIMARY_INDUSTRY_REQUIRED.
 *  5. Dữ liệu ở section inactive KHÔNG vào payload export (exportLoops lọc);
 *     grid INTERIM (production M72) giữ nguyên payload hành vi cũ.
 *  6. Đổi loại hình (đổi selector) không làm lẫn dữ liệu giữa các loop
 *     (store key riêng, chỉ trạng thái active đổi).
 *  7. Draft migrateDraft round-trip giữ dữ liệu đúng section kèm _row_id;
 *     checks trong draft lái lại trạng thái active.
 *  8. PLI_M72 không hồi quy structural: blocks vẫn 5 loop + 144 paragraph,
 *     KHÔNG có ô chọn loại hình; artifact (app/data, tools) nguyên vẹn theo
 *     git (structural DOCX 5 occurrence thuộc gate Lead: test_industry_change).
 *  N9 (negative). Mutate meta form-scoped (fixture) KHÔNG lan sang GRID_META
 *     gốc hay meta production khác (mkGrid clone isolation 2 chiều).
 * Thêm: unit evalActiveWhen - thứ tự ưu tiên selector > interim; valueOf
 * membership; activationModeOf audit; đăng ký runtime qua
 * registerFormGridMeta index đúng bySemanticKey.
 *
 * Chạy: node app_web/test_m72_activation.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
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

/* Key checkbox GIẢ ĐỊNH cho selector loại hình - CHỈ nằm trong test fixture,
 * KHÔNG đưa vào production FORM_GRID_META (cấm tự tạo mapping pháp lý). */
const SEL_KEYS = {
  ds_nganh_dntn: 'chk_loai_hinh_dntn',
  ds_nganh_tnhh_1tv: 'chk_loai_hinh_tnhh_1tv',
  ds_nganh_tnhh_2tv: 'chk_loai_hinh_tnhh_2tv',
  ds_nganh_ctcp: 'chk_loai_hinh_ctcp',
  ds_nganh_dhdn: 'chk_loai_hinh_dhdn'
};
const VOF_KEY = 'loai_hinh_dn_fixture'; // key values GIẢ ĐỊNH cho fixture valueOf

/* Clone SÂU mức-1 như mkGrid nội bộ của form-domain (không đụng base). */
function cloneGrid(extra) {
  const base = FD.GRID_META.ds_nganh;
  const m = Object.assign({}, base, extra || {});
  m.columns = base.columns.map(c => Object.assign({}, c));
  return m;
}

/* FIXTURE A: selector kiểu checkedKey (5 ô tick loại hình giả định). */
const FIX_A = 'FIX_M72_SEL';
(function registerFixtureA() {
  const loops = {};
  M72_LOOPS.forEach(ln => {
    loops[ln] = cloneGrid({
      // required:true để chứng minh mục 2 (active trống + required -> chặn)
      required: true, minRows: 0,
      activeWhen: { checkedKey: SEL_KEYS[ln] },
      semanticKey: ln, syncGroup: 'ds_nganh_fixture_sel'
    });
  });
  FD.registerFormGridMeta(FIX_A, { loops: loops });
})();

/* FIXTURE B: selector kiểu valueOf {key, equals:[...]} (một key giá trị). */
const FIX_B = 'FIX_M72_VOF';
(function registerFixtureB() {
  FD.registerFormGridMeta(FIX_B, {
    loops: {
      vof_ctcp: cloneGrid({
        required: true, minRows: 0,
        activeWhen: { valueOf: { key: VOF_KEY, equals: ['CTCP'] } },
        semanticKey: 'vof_ctcp'
      }),
      vof_dhdn: cloneGrid({
        required: true, minRows: 0,
        activeWhen: { valueOf: { key: VOF_KEY, equals: ['DHDN', 'DNTN'] } },
        semanticKey: 'vof_dhdn'
      })
    }
  });
})();

/* Blocks TỔNG HỢP (không đọc app/data): đủ cho collectKeys thấy loop + cột. */
function loopBlock(name) {
  return {
    t: 'loop', loop: name,
    cols: [{ tag: 'ten_nganh' }, { tag: 'ma_nganh' }, { tag: 'la_nganh_chinh' }],
    rows: []
  };
}
const BLOCKS_A = M72_LOOPS.map(loopBlock);
const BLOCKS_B = ['vof_ctcp', 'vof_dhdn'].map(loopBlock);

function mkStore(init) {
  const s = { values: {}, checks: {}, loops: {} };
  Object.keys(init || {}).forEach(k => { s.loops[k] = init[k]; });
  return s;
}
function withRowId(rows) {
  return (rows || []).map(r => Object.assign({ _row_id: FD.makeRowId() }, r));
}
function errsOf(docId, blocks, store) {
  return FD.validateDocument(docId, blocks, store, { vsicList: VSIC_MOCK });
}
function loopErrs(errs) {
  return errs.filter(e => String(e.key).indexOf('loop:') === 0);
}
function activeMap(docId, loops, st) {
  const out = {};
  loops.forEach(ln => {
    out[ln] = FD.isActiveGrid(FD.getGridMeta({ docId: docId, loop: ln }),
      st.loops[ln] || [], st);
  });
  return out;
}

// ==== S0. activationModeOf audit + đăng ký runtime ==========================

check('S0. production PLI_M72: activation INTERIM (minFilledRows, chua co selector)',
  M72_LOOPS.every(ln =>
    FD.activationModeOf(FD.getGridMeta({ docId: 'PLI_M72', loop: ln })) ===
      'interim-filled-data'));
check('S0. GRID_META.ds_nganh khong activeWhen -> activationModeOf null (luon active)',
  FD.activationModeOf(FD.GRID_META.ds_nganh) === null);
check('S0. fixture checkedKey/valueOf deu duoc nhan dien la selector',
  M72_LOOPS.every(ln =>
    FD.activationModeOf(FD.getGridMeta({ docId: FIX_A, loop: ln })) === 'selector') &&
    ['vof_ctcp', 'vof_dhdn'].every(ln =>
      FD.activationModeOf(FD.getGridMeta({ docId: FIX_B, loop: ln })) === 'selector'));
check('S0. registerFormGridMeta danh chi muc bySemanticKey dung (runtime)',
  FD.FORM_GRID_META[FIX_A].bySemanticKey.ds_nganh_ctcp ===
    FD.getGridMeta({ docId: FIX_A, loop: 'ds_nganh_ctcp' }) &&
    FD.FORM_GRID_META[FIX_A].formId === FIX_A &&
    FD.FORM_GRID_META[FIX_B].bySemanticKey.vof_dhdn.semanticKey === 'vof_dhdn');
check('S0. fixture KHONG anh huong resolver production (isolation)',
  FD.getGridMeta({ docId: 'PLI_M72', loop: 'vof_ctcp' }) === null &&
    FD.getGridMeta({ docId: FIX_A, semanticKey: 'vof_ctcp' }) === null);

// ==== 1. Dung MOT section active khi selector chi chon 1 loai hinh ==========

{
  const bait = {}; // dữ liệu "mồi" ở CẢ 5 section: chỉ section active được phét
  M72_LOOPS.forEach(ln => {
    bait[ln] = withRowId([{ ma_nganh: '999999', ten_nganh: 'Bai ' + ln }]);
  });
  const st = mkStore(bait);
  st.checks[SEL_KEYS.ds_nganh_tnhh_2tv] = true;

  const am = activeMap(FIX_A, M72_LOOPS, st);
  check('1. isActiveGrid: dung mot section (tnhh_2tv) active, 4 section con inactive',
    am.ds_nganh_tnhh_2tv === true &&
      M72_LOOPS.filter(l => l !== 'ds_nganh_tnhh_2tv')
        .every(l => am[l] === false),
    JSON.stringify(am));

  const errs = loopErrs(errsOf(FIX_A, BLOCKS_A, st));
  check('1. chi section duoc chon sinh loi (VSIC_INVALID o day), 3 section con im',
    errs.every(e => e.key.indexOf('loop:ds_nganh_tnhh_2tv') === 0) &&
      errs.some(e => e.code === 'VSIC_INVALID'),
    JSON.stringify(errs.map(e => e.key)));
}

// ==== 2. Section active TRONG + required -> blocking ========================

{
  const st = mkStore({});
  st.checks[SEL_KEYS.ds_nganh_ctcp] = true;
  const errs = loopErrs(errsOf(FIX_A, BLOCKS_A, st));
  check('2. section duoc chon ma TRONG + required -> INDUSTRY_REQUIRED blocking',
    errs.length === 1 && errs[0].code === 'INDUSTRY_REQUIRED' &&
      errs[0].severity === 'blocking' && errs[0].key === 'loop:ds_nganh_ctcp',
    JSON.stringify(errs));

  // selector KHÔNG chọn gì -> mọi section inactive -> dù required cũng 0 lỗi
  const stNone = mkStore({});
  check('2. khong chon loai hinh nao -> 0 loi (khong section nao active)',
    loopErrs(errsOf(FIX_A, BLOCKS_A, stNone)).length === 0);
}

// ==== 3. Section inactive KHONG sinh loi nao (ca khi chua du lieu ban) ======

{
  const dirty = {};
  dirty.ds_nganh_dntn = withRowId([
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },                 // thiếu primary
    { ma_nganh: '0111', ten_nganh: 'Trồng lúa' }                  // trùng mã
  ]);
  dirty.ds_nganh_dhdn = withRowId([{ ma_nganh: 'RAC', ten_nganh: '' }]); // VSIC sai
  const st = mkStore(dirty);
  st.checks[SEL_KEYS.ds_nganh_tnhh_1tv] = true; // chọn section KHÔNG có dữ liệu bẩn

  const errs = loopErrs(errsOf(FIX_A, BLOCKS_A, st));
  check('3. du lieu ban o section inactive KHONG sinh bat ky loi nao',
    errs.length === 1 && errs[0].code === 'INDUSTRY_REQUIRED' &&
      errs[0].key === 'loop:ds_nganh_tnhh_1tv',
    JSON.stringify(errs.map(e => e.code + '@' + e.key)));
}

// ==== 4. Section active thieu nganh chinh -> PRIMARY_INDUSTRY_REQUIRED ======

{
  const st = mkStore({
    ds_nganh_tnhh_2tv: withRowId([
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa' },
      { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy tính' }
    ])
  });
  st.checks[SEL_KEYS.ds_nganh_tnhh_2tv] = true;

  let errs = errsOf(FIX_A, BLOCKS_A, st)
    .filter(e => e.code === 'PRIMARY_INDUSTRY_REQUIRED');
  check('4. active co nganh nhung thieu nganh chinh -> PRIMARY_INDUSTRY_REQUIRED blocking',
    errs.length === 1 && errs[0].severity === 'blocking' &&
      errs[0].key === 'loop:ds_nganh_tnhh_2tv:' +
        st.loops.ds_nganh_tnhh_2tv[0]._row_id,
    JSON.stringify(errs.map(e => e.key)));

  G.setExclusiveRadio(st, 'ds_nganh_tnhh_2tv',
    st.loops.ds_nganh_tnhh_2tv[1]._row_id, 'la_nganh_chinh', true);
  check('4. da danh dau X nganh chinh -> het loi, ho so sang',
    loopErrs(errsOf(FIX_A, BLOCKS_A, st)).length === 0);
}

// ==== 5. Export guard: section inactive khong vao payload ===================

{
  const st = mkStore({
    ds_nganh_tnhh_2tv: withRowId([{ ma_nganh: '6201', ten_nganh: 'Lap trinh' }]),
    ds_nganh_dntn: withRowId([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]),
    ds_nganh_ctcp: withRowId([{ ma_nganh: '4711', ten_nganh: 'Ban le' }])
  });
  st.checks[SEL_KEYS.ds_nganh_tnhh_2tv] = true;

  const ex = G.exportLoops(st, [FIX_A]);
  check('5. section DUOC chon giu nguyen du lieu trong payload',
    ex.ds_nganh_tnhh_2tv.length === 1 && ex.ds_nganh_tnhh_2tv[0].ma_nganh === '6201');
  check('5. section INACTIVE bi loa KHOI payload (khong con dong nao)',
    ex.ds_nganh_dntn.length === 0 && ex.ds_nganh_ctcp.length === 0,
    JSON.stringify({ dntn: ex.ds_nganh_dntn.length, ctcp: ex.ds_nganh_ctcp.length }));

  // REGRESSION INTERIM: production M72 (minFilledRows) - grid inactive vốn
  // không có dòng CÓ DỮ LIỆU -> payload PHẢI GIỮ NGUYÊN 100% hành vi cũ
  // (kể cả dòng trống chỉ có _row_id vẫn được xuất như trước khi có guard).
  const stInterim = mkStore({
    ds_nganh_dntn: withRowId([{}]), // dòng trống người dùng lỡ bấm thêm
    ds_nganh_ctcp: withRowId([{ ma_nganh: '0111', ten_nganh: 'T', la_nganh_chinh: 'X' }])
  });
  const exInterim = G.exportLoops(stInterim, ['PLI_M72']);
  check('5. regression INTERIM: grid trong-van-co-dong-trong duoc xuat nhu cu',
    exInterim.ds_nganh_dntn.length === 1 &&
      JSON.stringify(exInterim.ds_nganh_dntn[0]) === '{"la_nganh_chinh":""}',
    JSON.stringify(exInterim.ds_nganh_dntn));
  check('5. regression INTERIM: grid co du lieu van xuat day du + map X',
    exInterim.ds_nganh_ctcp.length === 1 &&
      exInterim.ds_nganh_ctcp[0].la_nganh_chinh === 'X');

  // Grid KHÔNG có activeWhen (vd ds_thanh_vien toàn cục) không bị guard đụng
  const stTv = mkStore({ ds_thanh_vien: withRowId([{ ho_ten: 'Nguyen Van A' }]) });
  const exTv = G.exportLoops(stTv, ['PLI_M06']);
  check('5. grid khong co activeWhen khong bi loc (hanh vi cu nguyen ven)',
    exTv.ds_thanh_vien.length === 1 && exTv.ds_thanh_vien[0].ho_ten === 'Nguyen Van A');

  // Ghi nhận hợp đồng resolve theo THỨ TỰ docIds: meta đầu tiên thắng
  // (PLI_M72 interim đứng trước fixture selector -> không filter). Owner cần
  /// biết điều này khi wiring production (xem proposal, mục rủi ro).
  const exOrder = G.exportLoops(st, ['PLI_M72', FIX_A]);
  check('5. thu tu docIds quyet dinh meta: PLI_M72 (interim) truoc -> khong filter',
    exOrder.ds_nganh_dntn.length === 1,
    'len=' + exOrder.ds_nganh_dntn.length);
}

// ==== 5b. valueOf membership ================================================

{
  const am0 = activeMap(FIX_B, ['vof_ctcp', 'vof_dhdn'], mkStore({}));
  check('5b. valueOf: khong co gia tri -> ca hai inactive',
    am0.vof_ctcp === false && am0.vof_dhdn === false);

  const stCtcp = mkStore({}); stCtcp.values[VOF_KEY] = 'CTCP';
  const amC = activeMap(FIX_B, ['vof_ctcp', 'vof_dhdn'], stCtcp);
  check('5b. valueOf CTCP -> vof_ctcp active, vof_dhdn inactive',
    amC.vof_ctcp === true && amC.vof_dhdn === false);

  const stDntn = mkStore({}); stDntn.values[VOF_KEY] = 'DNTN';
  const amD = activeMap(FIX_B, ['vof_ctcp', 'vof_dhdn'], stDntn);
  check('5b. valueOf DNTN (thuoc equals nhieu phan tu) -> vof_dhdn active',
    amD.vof_ctcp === false && amD.vof_dhdn === true);

  const stX = mkStore({}); stX.values[VOF_KEY] = 'GIATRI_LA';
  const amX = activeMap(FIX_B, ['vof_ctcp', 'vof_dhdn'], stX);
  check('5b. gia tri ngoai equals -> ca hai inactive',
    amX.vof_ctcp === false && amX.vof_dhdn === false);

  const stBad = mkStore({
    vof_ctcp: withRowId([{ ma_nganh: 'RAC', ten_nganh: 'x' }]),
    vof_dhdn: withRowId([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }])
  });
  stBad.values[VOF_KEY] = 'CTCP';
  const errs = loopErrs(errsOf(FIX_B, BLOCKS_B, stBad));
  check('5b. validation theo valueOf: chi section khop gia tri bi phet loi',
    errs.length === 2 &&
      ['VSIC_INVALID', 'PRIMARY_INDUSTRY_REQUIRED'].every(want =>
        errs.some(e => e.code === want)) &&
      errs.every(e => e.key.indexOf('loop:vof_ctcp:') === 0),
    JSON.stringify(errs.map(e => e.code + '@' + e.key)));
}

// ==== 6. Doi loai hinh: khong lan du lieu giua cac loop section =============

{
  const st = mkStore({
    ds_nganh_dntn: withRowId([{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }]),
    ds_nganh_ctcp: withRowId([])
  });
  st.checks[SEL_KEYS.ds_nganh_dntn] = true;
  const snap = JSON.stringify(st.loops);

  // "đổi loại hình": bỏ tick DNTN, tick CTCP - KHÔNG dịch chuyển dữ liệu
  delete st.checks[SEL_KEYS.ds_nganh_dntn];
  st.checks[SEL_KEYS.ds_nganh_ctcp] = true;

  check('6. doi selector KHONG dich du lieu: snapshot 5 loop giu nguyen',
    JSON.stringify(st.loops) === snap);
  const am = activeMap(FIX_A, M72_LOOPS, st);
  check('6. chi trang thai active doi: dntn -> inactive, ctcp -> active',
    am.ds_nganh_dntn === false && am.ds_nganh_ctcp === true);
  check('6. du lieu van nam dung store key rieng cua no',
    st.loops.ds_nganh_dntn.length === 1 && st.loops.ds_nganh_dntn[0].ma_nganh === '0111' &&
      st.loops.ds_nganh_ctcp.length === 0);
}

// ==== 7. Draft round-trip giu du lieu dung section + _row_id ================

{
  const loopsIn = {
    ds_nganh_ctcp: withRowId([
      { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X' },
      { ma_nganh: '4711', ten_nganh: 'Bán lẻ máy tính' }
    ]),
    ds_nganh_dntn: withRowId([{ ma_nganh: '0112', ten_nganh: 'Trong ngo' }])
  };
  const draft = {
    v: 2, caseId: 'fixture_m72_case', checkedForms: [], activeDocId: null,
    autoSum: false, viewState: {}, savedAt: null,
    store: {
      values: {},
      checks: {},
      loops: JSON.parse(JSON.stringify(loopsIn))
    }
  };
  draft.store.checks[SEL_KEYS.ds_nganh_ctcp] = true;
  draft.store.checks['chk_khong_lien_quan'] = false;
  const idsBefore = {
    ctcp: loopsIn.ds_nganh_ctcp.map(r => r._row_id),
    dntn: loopsIn.ds_nganh_dntn.map(r => r._row_id)
  };

  const mig = FD.migrateDraft(JSON.parse(JSON.stringify(draft)));
  check('7. migrateDraft: du lieu tung section giu dung thu tu + _row_id',
    JSON.stringify(mig.store.loops.ds_nganh_ctcp.map(r => r.ma_nganh)) ===
      JSON.stringify(['0111', '4711']) &&
      mig.store.loops.ds_nganh_ctcp.map(r => r._row_id).join() === idsBefore.ctcp.join() &&
      mig.store.loops.ds_nganh_dntn.map(r => r._row_id).join() === idsBefore.dntn.join());
  check('7. migrateDraft: checks (selector) giu nguyen qua round-trip',
    mig.store.checks[SEL_KEYS.ds_nganh_ctcp] === true &&
      mig.store.checks.chk_khong_lien_quan === false);

  // draft lái lại trạng thái active sau khi restore
  const am = activeMap(FIX_A, M72_LOOPS, mig.store);
  check('7. draft restored -> selector trong draft quyet dinh section active',
    am.ds_nganh_ctcp === true && am.ds_nganh_dntn === false);

  // draft v1 cũ thiếu checks cũng không làm cơ chế sập
  const up = FD.migrateDraft({
    v: 1, caseId: 'x', checkedForms: [], autoSum: false,
    store: { values: {}, checks: {}, loops: loopsIn }
  });
  check('7. draft v1: normalize khong mat du lieu section, checks ve rong an toan',
    up.store.loops.ds_nganh_ctcp.length === 2 &&
      !up.store.checks[SEL_KEYS.ds_nganh_ctcp]);
}

// ==== 8. Khong hoi quy structural PLI_M72 + artifact nguyen ven =============

{
  const counts = {};
  let chkBlocks = 0;
  let loaiHinhKeys = 0;
  (M72.blocks || []).forEach(b => {
    counts[b.t] = (counts[b.t] || 0) + 1;
    if (b.t === 'chk') chkBlocks++;
    if (b.t === 'p') (b.runs || []).forEach(r => {
      if (r && r.input && /loai_hinh/i.test(String(r.input.key))) loaiHinhKeys++;
    });
  });
  const loopNames = (M72.blocks || []).filter(b => b.t === 'loop').map(b => b.loop);
  check('8. blocks PLI_M72: dung 5 loop dung ten (structural khong doi)',
    JSON.stringify(loopNames.slice().sort()) ===
      JSON.stringify(M72_LOOPS.slice().sort()));
  check('8. blocks PLI_M72: 144 paragraph nhu evidence audit',
    counts.p === 144, 'p=' + counts.p);
  check('8. blocks PLI_M72: VAN khong co o chon loai hinh (0 chk, 0 key loai_hinh)',
    chkBlocks === 0 && loaiHinhKeys === 0);

  // artifact không bị đụng: git worktree sạch trên đường dẫn dữ liệu/tools/M72
  // (thay đổi dưới app_web/ là code+test của agent này - được phép)
  let dirtyArtifacts = [];
  try {
    const out = execSync('git status --porcelain', { encoding: 'utf8' }) || '';
    dirtyArtifacts = out.split('\n').map(l => l.trim()).filter(Boolean)
      .filter(l => {
        const p = l.replace(/^\S+\s+/, '');
        if (/^(app\/data\/|tools\/|templates\/)/.test(p)) return true;
        if (/M72/i.test(p) && !/^app_web\//.test(p)) return true;
        return false;
      });
  } catch (e) { dirtyArtifacts = ['GIT_ERROR: ' + e.message]; }
  check('8. git: khong thay doi nao tren app/data, tools, templates hay file M72',
    dirtyArtifacts.length === 0, JSON.stringify(dirtyArtifacts));
}

// ==== N9. NEGATIVE: mutate meta form-scoped khong lan sang giong goc ========

{
  const fixG = FD.getGridMeta({ docId: FIX_A, loop: 'ds_nganh_dntn' });
  fixG.columns.push({ tag: 'hack_col', type: 'text' });
  fixG.required = false;
  fixG.label = 'HACK';

  const base = FD.GRID_META.ds_nganh;
  check('N9. GRID_META.ds_nganh nguyen ven sau khi mutate fixture meta',
    base.columns.length === 4 &&
      base.columns.every(c => c.tag !== 'hack_col') &&
      base.required === true && base.minRows === 1 &&
      base.label === 'Danh sách ngành nghề kinh doanh');

  const prodG = FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_dntn;
  check('N9. meta production PLI_M72 khong bi lan mutation tu fixture',
    prodG.columns.length === 4 && prodG.required === false &&
      prodG.activeWhen.minFilledRows === 1 && !prodG.columns.some(c => c.tag === 'hack_col'));

  // chiều ngược lại: meta production là bản clone mkGrid, không chia sẻ cột với gốc
  check('N9. meta form-scoped production la clone RIENG (khong share mang columns)',
    prodG.columns !== base.columns && prodG.columns[0] !== base.columns[0]);

  // sửa lại fixture cho các check phía trên (nếu chạy tiếp) rồi xác nhận resolver
  fixG.required = true;
  check('N9. resolver tra dung object fixture da mutate (cung reference)',
    FD.getGridMeta({ docId: FIX_A, loop: 'ds_nganh_dntn' }) === fixG);
}

// ==== S10. Unit evalActiveWhen: thu tu uu tien selector > interim ===========

{
  check('S10. khong activeWhen -> luon active',
    FD.evalActiveWhen(null, 0, {}) === true);
  check('S10. INTERIM minFilledRows: du it dong -> inactive, du dong -> active',
    FD.evalActiveWhen({ minFilledRows: 2 }, 1, {}) === false &&
      FD.evalActiveWhen({ minFilledRows: 2 }, 2, {}) === true);
  check('S10. SELECTOR UU TIEN: checkedKey true thang ca khi minFilledRows vo ly',
    FD.evalActiveWhen({ checkedKey: 'k', minFilledRows: 99 }, 0,
      { checks: { k: true } }) === true);
  check('S10. checkedKey false -> inactive du dang co nhieu du lieu',
    FD.evalActiveWhen({ checkedKey: 'k' }, 5, { checks: { k: false } }) === false);
  check('S10. checkedKey thieu trong store -> inactive (an toan)',
    FD.evalActiveWhen({ checkedKey: 'k' }, 5, { checks: {} }) === false);
  check('S10. valueOf so khop chinh xac sau trim (phan biet hoa/thuong)',
    FD.evalActiveWhen({ valueOf: { key: 'lh', equals: ['CTCP'] } }, 0,
      { values: { lh: ' CTCP ' } }) === true &&
      FD.evalActiveWhen({ valueOf: { key: 'lh', equals: ['CTCP'] } }, 0,
        { values: { lh: 'ctcp' } }) === false);
  check('S10. checkedKey + valueOf cung khai -> AND (ca hai phai thoả)',
    FD.evalActiveWhen(
      { checkedKey: 'a', valueOf: { key: 'b', equals: ['X'] } }, 0,
      { checks: { a: true }, values: { b: 'X' } }) === true &&
      FD.evalActiveWhen(
        { checkedKey: 'a', valueOf: { key: 'b', equals: ['X'] } }, 0,
        { checks: { a: true }, values: { b: 'Y' } }) === false);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('test_m72_activation: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
