/* test_p2a_people_contracts.js — Lane P2A (people/ownership, wave 2).
 *
 * Kiểm chứng phía runtime/form-domain cho 6 section người của đợt P2A, theo
 * docs/decision_registry.md packet D2 (D2.2/A D2.3/A D2.5/A D2.6/A D2.7/A
 * D2.8/A D2.4/A) + packet D7 (D7.3=A):
 *   1. Hai grid MỚI (PLI_M13 `ds_ndd_pl_sau_thay_doi` — D2.6/A + D2.7/A,
 *      PLII_M07 `ds_thanh_vien_hkd_gcn` — D2.8/A key RIÊNG) có metadata
 *      form-scoped trong FORM_GRID_META, resolve được theo docId+loop và
 *      theo semanticKey, là CLONE riêng (P2.0), không auto-sync.
 *   2. Hai cột bổ sung ở metadata toàn cục: ds_co_dong_sang_lap.dan_toc
 *      (D2.3=A) và ds_cshhl.quyen_chi_phoi (D2.5/A, NĐ 168/2025 điểm b
 *      khoản 1 Điều 17); GRID_META.ds_thanh_vien giữ NGUYÊN (gap đã ghi:
 *      bị test_form_grid_meta check 10/11 ghim identity + columns.length).
 *   3. Khớp chéo ba nguồn cho mọi section: census manifest (kind/semantic_key)
 *      <-> spec generator (tools/form_specs/**) <-> metadata runtime; với 4
 *      mẫu có khai báo inline production thì đối chiếu thêm
 *      app/data/form_maps.json để chốt DELTA additive (không mất tag cũ).
 *   4. D7.3=A: 5 loop ngành PLI_M72 required:true + minRows:1, activeWhen
 *      selector giữ nguyên; section ĐƯỢC CHỌN nhưng TRỐNG -> INDUSTRY_REQUIRED
 *      blocking; KHÔNG chọn loại hình -> vẫn chỉ có SELECTOR_REQUIRED.
 *   5. Cổng registry: mọi section P2A đều kind=editable-grid (manifest) nên
 *      KHÔNG đăng ký vào FORM_TABLE_CONTRACTS (chỉ nhận fixed-matrix/
 *      nested-grid/output-table; render.js coi editable-grid là no-op) —
 *      registry editable-grid đúng là FORM_GRID_META (tiền lệ PLII_M02).
 *   6. Probe PRE-INTEGRATION: nếu blocks đã có loop mới (sau khi Lead regen)
 *      thì assert thêm cols theo spec; chưa có thì ghi nhận rõ, không pass giả.
 *
 * Chạy: node app_web/test_p2a_people_contracts.js   (từ root repo, không GUI)
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const App = require('./ui/app.js');

const RESULTS = [];
let passed = 0;
let failed = 0;
let preIntegration = 0;

function check(name, cond, expect, actual) {
  const ok = !!cond;
  RESULTS.push({ name, pass: ok });
  if (ok) passed++;
  else failed++;
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name +
    (ok ? '' : '\n        EXPECT : ' + (expect || '') +
      '\n        ACTUAL : ' + (actual === undefined ? '(none)' : String(actual))));
}
function pre(name) {          // probe: capability chưa có trong artifact hiện tại
  preIntegration++;
  console.log('PRE-INTEGRATION  ' + name);
}

function loadJson(p) { return JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8')); }
function loadBlocks(id) { return loadJson('app/data/blocks/' + id + '.json'); }

const MANIFEST = {};
loadJson('app/data/table_specs/manifest.json').forms.forEach(f => {
  MANIFEST[f.form_id] = {};
  f.sections.forEach(s => { MANIFEST[f.form_id][s.section_id] = s; });
});
const FORM_MAPS = loadJson('app/data/form_maps.json');
const VSIC = loadJson('app/data/nganh_vsic.json').nganh;

// ---------------------------------------------------------------------------
// Hợp đồng P2A: một nguồn sự thật cho cả hai đầu (spec JSON <-> runtime)
// ALIAS: tên cột manifest -> tag spec/runtime (tag ngắn, migration additive)
const ALIAS = {
  ngay_thang_nam_sinh: 'ngay_sinh', so_gtpl: 'so_cccd',
  so_dinh_danh_ca_nhan: 'so_cccd', so_ngay_cap_co_quan_cap_gtpl: 'so_giay_to',
  dia_chi_lien_lac: 'dia_chi', phan_von_gop: 'von_dong_gop',
  ty_le_von_gop: 'ty_le_von', tong_so_co_phan: 'so_co_phan',
  ten_co_dong: 'ten_cd', ma_so_dn_gtpl: 'ma_so',
  ty_le_so_huu_von_dieule: 'ty_le', ty_le_co_phan_bieu_quyet: 'ty_le_co_phan',
  chu_ky_output_only: 'chu_ky'
};

const P2A = [
  {
    docId: 'PLII_M07', sectionId: 'm7_danh_sach_thanh_vien_hgd',
    specFile: 'tools/form_specs/household/PLII_M07.json',
    specId: 'm7_danh_sach_thanh_vien_hgd', loop: 'ds_thanh_vien_hkd_gcn',
    minRows: 0, required: false, decision: 'D2.8=A key riêng',
    tags: ['ten_thanh_vien', 'quoc_tich', 'noi_o_hien_tai', 'noi_thuong_tru',
      'so_cccd', 'ghi_chu'],
    noSignature: true, newLoop: true
  },
  {
    docId: 'PLI_M06', sectionId: 'ds_thanh_vien_tnhh',
    specFile: 'tools/form_specs/formation/PLI_M06.json',
    specId: 'ds_thanh_vien_tnhh', loop: 'ds_thanh_vien',
    added: ['thoi_han_gop_von'], decision: 'D2.2=A phẳng + bổ sung cột thiếu',
    tags: null /* lấy từ form_maps production + added */
  },
  {
    docId: 'PLI_M07', sectionId: 'ds_co_dong_sang_lap',
    specFile: 'tools/form_specs/formation/PLI_M07.json',
    specId: 'ds_co_dong_sang_lap', loop: 'ds_co_dong_sang_lap',
    added: ['dan_toc'], decision: 'D2.3=A phẳng (cùng kiến trúc M08)'
  },
  {
    docId: 'PLI_M08', sectionId: 'ds_co_dong_nn',
    specFile: 'tools/form_specs/formation/PLI_M08.json',
    specId: 'ds_co_dong_nn', loop: 'ds_co_dong_nn',
    added: [], decision: 'D2.3=A phẳng (cùng kiến trúc M07)'
  },
  {
    docId: 'PLI_M10', sectionId: 'ds_cshhl_doanh_nghiep',
    specFile: 'tools/form_specs/formation/PLI_M10.json',
    specId: 'ds_cshhl', loop: 'ds_cshhl',
    added: ['quyen_chi_phoi'], decision: 'D2.5=A cột riêng quyền chi phối',
    noSignature: true
  },
  {
    docId: 'PLI_M13', sectionId: 'ndd_pl_sau_thay_doi',
    specFile: 'tools/form_specs/change/PLI_M13.json',
    specId: 'ndd_pl_sau_thay_doi', loop: 'ds_ndd_pl_sau_thay_doi',
    minRows: 1, required: false, decision: 'D2.6=A grid + D2.7=A min 1/max null',
    tags: ['ho_ten', 'ngay_sinh', 'gioi_tinh', 'so_cccd', 'chuc_danh',
      'dia_chi', 'quoc_gia'],
    noSignature: true, noDiscriminator: true, newLoop: true
  }
];

// ===========================================================================
// 1. Hai grid MỚI: metadata form-scoped (M13 + PLII_M07)
// ===========================================================================
P2A.filter(s => s.newLoop).forEach(s => {
  const g = FD.getGridMeta({ docId: s.docId, loop: s.loop });
  check(s.docId + '/' + s.loop + ': resolver tra meta form-scoped',
    !!g && !!FD.FORM_GRID_META[s.docId].loops[s.loop] &&
      FD.FORM_GRID_META[s.docId].bySemanticKey[s.loop] === g,
    'meta + bySemanticKey', JSON.stringify(g && g.semanticKey));
  check(s.docId + '/' + s.loop + ': ' + s.decision,
    !!g && (s.docId === 'PLI_M13'
      ? g.minRows === 1 && g.maxRows === null
      : g.minRows === 0 && g.maxRows === null));
  check(s.docId + '/' + s.loop + ': semanticKey rieng = ' + s.loop,
    !!g && g.semanticKey === s.loop && g.loop === s.loop,
    s.loop, g && g.semanticKey);
  check(s.docId + '/' + s.loop + ': dung tap cot spec/manifest (qua ALIAS)',
    !!g && JSON.stringify((g.columns || []).map(c => c.tag)) ===
      JSON.stringify(s.tags),
    s.tags.join(','),
    g && (g.columns || []).map(c => c.tag).join(','));
  check(s.docId + '/' + s.loop + ': khong co cot chu ky (nguon khong co)',
    !!g && (g.columns || []).every(c => c.tag !== 'chu_ky') &&
      JSON.stringify(g.outputOnlyTags) === '[]');
  check(s.docId + '/' + s.loop + ': khong discriminator / khong row_groups',
    !!g && !g.discriminator && !g.row_groups &&
      FD.sectionContractForLoop(s.docId, s.loop) === null,
    'null (kind=editable-grid, khong phai nested-grid)');
  check(s.docId + '/' + s.loop + ': khong ke thua syncGroup (khong auto-sync)',
    !!g && !g.syncGroup);

  // clone riêng (P2.0): mutate meta KHÔNG lan vào GRID_META toàn cục
  const beforeBase = JSON.stringify(FD.GRID_META.ds_tv_ho_gia_dinh);
  const snap = JSON.stringify(g);
  g.columns[0].type = '__mutated__';
  g.minRows = 99;
  check(s.docId + '/' + s.loop + ': meta la clone rieng (P2.0)',
    JSON.stringify(FD.GRID_META.ds_tv_ho_gia_dinh) === beforeBase &&
      JSON.stringify(g) !== snap);
  g.columns[0].type = JSON.parse(snap).columns[0].type;
  g.minRows = JSON.parse(snap).minRows;
  check(s.docId + '/' + s.loop + ': restored dung gia tri sau mutate',
    JSON.stringify(g) === snap);
});

check('PLI_M13: khong ton tai key dung chung voi bo nguoi M02/M15',
  !FD.FORM_GRID_META.PLI_M13.loops.ds_nddpl_uy_quyen_chu_so_huu &&
    !FD.FORM_GRID_META.PLI_M13.loops.ds_ndd_uy_quyen_sau_thay_doi);
check('PLII_M07: khong dung lai ds_tv_ho_gia_dinh cua M01/M02 (D2.8=A)',
  !FD.FORM_GRID_META.PLII_M07.loops.ds_tv_ho_gia_dinh &&
    Object.keys(FD.FORM_GRID_META.PLII_M07.loops).sort().join(',') ===
      'ds_thanh_vien_hkd_gcn');

// ===========================================================================
// 2. Hai cột bổ sung ở metadata toàn cục + gap ds_thanh_vien
// ===========================================================================
check('GRID_META.ds_co_dong_sang_lap: co cot dan_toc (D2.3=A)',
  FD.GRID_META.ds_co_dong_sang_lap.columns.filter(c => c.tag === 'dan_toc')
    .length === 1 &&
    FD.GRID_META.ds_co_dong_sang_lap.columns.map(c => c.tag).join(',') ===
      'ho_ten,ngay_sinh,gioi_tinh,so_cccd,quoc_tich,dan_toc,dia_chi,so_co_phan,ty_le,chu_ky',
  '...quoc_tich,dan_toc,dia_chi...',
  FD.GRID_META.ds_co_dong_sang_lap.columns.map(c => c.tag).join(','));
check('GRID_META.ds_cshhl: co cot quyen_chi_phoi TRUOC ghi_chu (D2.5=A)',
  (() => {
    const t = FD.GRID_META.ds_cshhl.columns.map(c => c.tag);
    return t.indexOf('quyen_chi_phoi') === t.length - 2 &&
      t[t.length - 1] === 'ghi_chu';
  })(),
  '...,quyen_chi_phoi,ghi_chu',
  FD.GRID_META.ds_cshhl.columns.map(c => c.tag).join(','));
check('GRID_META.ds_thanh_vien GIU NGUYEN 10 cot (gap: test_form_grid_meta ghim)',
  FD.GRID_META.ds_thanh_vien.columns.length === 10 &&
    FD.getGridMeta({ docId: 'PLI_M06', loop: 'ds_thanh_vien' }) ===
      FD.GRID_META.ds_thanh_vien &&
    FD.GRID_META.ds_thanh_vien.columns.every(c => c.tag !== 'thoi_han_gop_von'),
  '10 cot, khong co thoi_han_gop_von',
  FD.GRID_META.ds_thanh_vien.columns.map(c => c.tag).join(','));
check('GRID_META.ds_nganh/ds_tv_ho_gia_dinh khong bi xuyen tach',
  FD.GRID_META.ds_nganh.columns.length === 4 &&
    FD.GRID_META.ds_tv_ho_gia_dinh.columns.length === 9);

// ===========================================================================
// 3. Khớp chéo manifest <-> spec generator <-> runtime (+ form_maps production)
// ===========================================================================
P2A.forEach(s => {
  const sec = (MANIFEST[s.docId] || {})[s.sectionId];
  check(s.docId + '/' + s.sectionId + ': ton tai trong census manifest',
    !!sec && sec.kind === 'editable-grid',
    'kind=editable-grid', sec && sec.kind);

  const raw = loadJson(s.specFile);
  const ent = (raw.tables || []).filter(t => t.spec.id === s.specId)[0];
  check(s.docId + '/' + s.specId + ': spec JSON co entry (kind=list)',
    !!ent && ent.spec.kind === 'list' && !ent.legal_status,
    'kind=list, khong legal_status (kind=list khong dung co che blocked)',
    ent && ent.spec.kind);
  const hdrs = ent ? ent.headers : [];
  const cols = ent ? ent.spec.cols : [];
  const tagsFromSpec = hdrs.map((h, i) => {
    const hf = R.normText(h).replace(/\s+/g, ' ').trim()
      .toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/đ/g, 'd');
    const hit = cols.filter(c => new RegExp(c[0]).test(hf))[0];
    return hit ? hit[1] : null;
  });
  check(s.docId + '/' + s.specId + ': loop/key khop manifest semantic_key hoac loop_audit',
    !!sec && (sec.semantic_key === s.loop ||
      ((sec.loop_audit || {}).loop === s.loop)),
    s.loop, sec && (sec.semantic_key + ' / ' + (sec.loop_audit || {}).loop));

  // DELTA additive so với khai báo inline production đang chạy
  const dt = ((FORM_MAPS[s.docId].dynamic_tables || []) || [])
    .filter(d => d.loop === s.loop)[0];
  if (!dt) {
    check(s.docId + '/' + s.loop + ': form_maps chua co loop (pre-integration)',
      s.newLoop === true, 'newLoop', String(!!dt));
  } else {
    const prodTags = dt.columns.map(c => c.tag);
    const want = (s.added || []);
    const specTags = tagsFromSpec.filter(t => t);
    const added = specTags.filter(t => prodTags.indexOf(t) < 0);
    const lost = prodTags.filter(t => specTags.indexOf(t) < 0);
    check(s.docId + '/' + s.loop + ': DELTA additive = [' + want.join(',') + ']',
      JSON.stringify(added.sort()) === JSON.stringify(want.slice().sort()) &&
        lost.length === 0,
      'added=[' + want.join(',') + '] lost=[]',
      'added=[' + added.join(',') + '] lost=[' + lost.join(',') + ']');
    check(s.docId + '/' + s.loop + ': header text production duoc giu nguyen',
      dt.columns.every(c => hdrs.indexOf(c.header) >= 0),
      'moi header cu con trong spec', JSON.stringify(
        dt.columns.map(c => c.header).filter(h => hdrs.indexOf(h) < 0)));
    // cột mới phải có metadata runtime trừ ds_thanh_vien (gap đã ghi)
    const meta = FD.getGridMeta({ docId: s.docId, loop: s.loop });
    const metaTags = ((meta && meta.columns) || []).map(c => c.tag);
    const unMeta = want.filter(t => metaTags.indexOf(t) < 0);
    check(s.docId + '/' + s.loop + ': cot moi co metadata runtime (tru gap da ghi)',
      JSON.stringify(unMeta) ===
        JSON.stringify(s.docId === 'PLI_M06' ? ['thoi_han_gop_von'] : []),
      '[] (PLI_M06 gap da ghi o spec + report)', JSON.stringify(unMeta));
  }

  // PRE-INTEGRATION probe: với loop ĐÃ có trong blocks thì đối chiếu hiện
  // trạng; cột MỚI chỉ được assert sau khi Lead regen (cột chưa tồn tại)
  const blk = loadBlocks(s.docId).blocks
    .filter(b => b.t === 'loop' && b.loop === s.loop)[0];
  if (!blk) {
    pre(s.docId + '/' + s.loop + ': blocks chua co loop (can Lead regen de bat ' +
      'assert cols theo spec)');
  } else {
    const got = blk.cols.map(c => [c.col, c.tag]);
    check(s.docId + '/' + s.loop + ': blocks hien tai khop form_maps production',
      JSON.stringify(got.slice().sort()) ===
        JSON.stringify((dt.columns.map(c => [c.col, c.tag])).slice().sort()),
      JSON.stringify((dt.columns.map(c => [c.col, c.tag])).slice().sort()),
      JSON.stringify(got.slice().sort()));
    const blkTags = blk.cols.map(c => c.tag);
    const added = s.added || [];
    const regenerated = added.every(t => blkTags.indexOf(t) >= 0);
    if (!regenerated) {
      pre(s.docId + '/' + s.loop + ': cot moi [' + added.join(',') +
        '] chua co trong blocks (can Lead regen de bat assert cols theo spec)');
    } else {
      const want = tagsFromSpec.map((t, i) => [i, t]).filter(x => x[1]);
      check(s.docId + '/' + s.loop + ': blocks cols khop spec (post-regen)',
        JSON.stringify(got.slice().sort()) === JSON.stringify(want.slice().sort()),
        JSON.stringify(want.slice().sort()), JSON.stringify(got.slice().sort()));
    }
  }
});

// manifest không tự suy: PLI_M13 và PLII_M07 vẫn missing_grid, 4 mẫu kia
// vẫn partial_columns cho tới khi Lead regen
check('manifest: status 6 section P2A chua doi (chua regen)',
  MANIFEST.PLI_M13.ndd_pl_sau_thay_doi.status === 'missing_grid' &&
    MANIFEST.PLII_M07.m7_danh_sach_thanh_vien_hgd.status === 'missing_grid' &&
    [['PLI_M06', 'ds_thanh_vien_tnhh'], ['PLI_M07', 'ds_co_dong_sang_lap'],
      ['PLI_M08', 'ds_co_dong_nn'], ['PLI_M10', 'ds_cshhl_doanh_nghiep']]
      .every(([fid, sid]) => (MANIFEST[fid][sid] || {})
        .status === 'partial_columns'));

// ===========================================================================
// 4. D7.3=A: 5 loop ngành PLI_M72 bắt buộc >= 1 ngành
// ===========================================================================
const M72_LOOPS = ['ds_nganh_dntn', 'ds_nganh_tnhh_1tv', 'ds_nganh_tnhh_2tv',
  'ds_nganh_ctcp', 'ds_nganh_dhdn'];
M72_LOOPS.forEach(ln => {
  const g = FD.getGridMeta({ docId: 'PLI_M72', loop: ln });
  check('PLI_M72/' + ln + ': D7.3=A required:true + minRows:1',
    !!g && g.required === true && g.minRows === 1 && g.maxRows === null,
    'required=true,minRows=1',
    g && ('required=' + g.required + ',minRows=' + g.minRows));
  check('PLI_M72/' + ln + ': selector P1.2 giu nguyen (khong bi D7.3 lam loi)',
    !!g && !!g.activeWhen && !!g.activeWhen.valueOf &&
      g.activeWhen.valueOf.key === 'dn.loai_hinh' &&
      g.activeWhen.valueOf.equals.length === 1 &&
      FD.activationModeOf(g) === 'selector' &&
      g.syncGroup === 'ds_nganh_pli_m72');
});

{
  const blocks = loadBlocks('PLI_M72');
  const errsOf = st => FD.validateDocument('PLI_M72', blocks.blocks, st,
    { vsicList: VSIC });
  const loopErrs = e => e.filter(x => String(x.key).indexOf('loop:') === 0);

  // chưa chọn loại hình: 5 grid inactive -> KHÔNG lỗi loop nào (chỉ selector)
  const stNone = R.newStore();
  const eNone = errsOf(stNone);
  check('D7.3: chua chon loai hinh -> 0 loi loop (chi SELECTOR_REQUIRED)',
    loopErrs(eNone).length === 0 &&
      eNone.filter(e => e.code === 'SELECTOR_REQUIRED').length === 1,
    '0 loop err, 1 SELECTOR_REQUIRED',
    JSON.stringify(loopErrs(eNone).map(e => e.code)));

  // chọn CTCP mà chưa kê khai ngành -> INDUSTRY_REQUIRED blocking đúng section
  const stEmpty = R.newStore();
  stEmpty.values['dn.loai_hinh'] = 'CTCP';
  const eEmpty = errsOf(stEmpty);
  const req = eEmpty.filter(e => e.code === 'INDUSTRY_REQUIRED');
  check('D7.3: chon CTCP + 0 nganh -> INDUSTRY_REQUIRED blocking dung section',
    req.length === 1 && req[0].severity === 'blocking' &&
      req[0].key === 'loop:ds_nganh_ctcp',
    'loop:ds_nganh_ctcp', JSON.stringify(req.map(e => e.key)));
  check('D7.3: 4 section khac van im lang khi khong duoc chon',
    loopErrs(eEmpty).every(e => e.key.indexOf('loop:ds_nganh_ctcp') === 0),
    'chi ds_nganh_ctcp', JSON.stringify(loopErrs(eEmpty).map(e => e.key)));

  // có 1 ngành hợp lệ (đủ primary) -> hết lỗi loop
  const stOk = R.newStore();
  stOk.values['dn.loai_hinh'] = 'CTCP';
  const vs = VSIC.filter(x => /^[1-9]/.test(String(x.ma)) &&
    String(x.ma).length === 4 && x.ten)[0];
  stOk.loops.ds_nganh_ctcp = [{ _row_id: 'r1_p2a', ma_nganh: String(vs.ma),
    ten_nganh: String(vs.ten), la_nganh_chinh: 'X' }];
  check('D7.3: du 1 nganh hop le + nganh chinh -> 0 loi loop',
    loopErrs(errsOf(stOk)).length === 0,
    '[]', JSON.stringify(loopErrs(errsOf(stOk)).map(e => e.code + '@' + e.key)));

  // D7.3 KHÔNG đụng mẫu khác: PLI_M06 vẫn minRows=2 (2 thành viên) như cũ
  const m06 = loadBlocks('PLI_M06');
  const s06 = R.newStore();
  s06.loops.ds_thanh_vien = [{ _row_id: 'r1', ho_ten: 'A',
    von_dong_gop: '1', ty_le_von: '100' }];
  const e06 = FD.validateDocument('PLI_M06', m06.blocks, s06, { vsicList: VSIC });
  check('D7.3: PLI_M06 giu nguyen rule minRows 2 (khong bi keo theo)',
    e06.some(e => e.code === 'MIN_ROWS') &&
      !e06.some(e => e.code === 'INDUSTRY_REQUIRED'),
    'MIN_ROWS, khong INDUSTRY_REQUIRED',
    JSON.stringify(e06.map(e => e.code)));
}

// ===========================================================================
// 5. Cổng registry: P2A KHÔNG thêm contract kind mới
// ===========================================================================
const WANT_CONTRACT_FORMS = ['PLI_M02', 'PLI_M03', 'PLI_M04', 'PLI_M70',
  'PLI_M71', 'PLI_M12', 'PLI_M15'];
check('FORM_TABLE_CONTRACTS giu nguyen 7 fixture (P2A la editable-grid)',
  Object.keys(FD.FORM_TABLE_CONTRACTS).sort().join(',') ===
    WANT_CONTRACT_FORMS.sort().join(','),
  WANT_CONTRACT_FORMS.sort().join(','),
  Object.keys(FD.FORM_TABLE_CONTRACTS).sort().join(','));
check('P2A khong dang ky section kind moi cho 6 mau',
  P2A.every(s => !FD.FORM_TABLE_CONTRACTS[s.docId] &&
    FD.getSectionContract(s.docId, s.loop) === null &&
    FD.sectionContractForLoop(s.docId, s.loop) === null));
check('dispatcher van de khong nuot: editable-grid di duong getGridMeta cu',
  FD.P2_SECTION_KINDS.join(',') ===
    'editable-grid,fixed-matrix,nested-grid,output-table');

// ===========================================================================
// console.log('-'.repeat(72));
console.log('test_p2a_people_contracts: %d PASS / %d FAIL (%d pre-integration)',
  passed, failed, preIntegration);
RESULTS.filter(r => !r.pass).forEach(r => console.log('  -> ' + r.name));
process.exitCode = failed ? 1 : 0;
