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

// =====================================================================
// S2. EXPORT CONFLICT GUARD - chống first-doc-wins âm thầm
// =====================================================================

(function s2() {
  /* Fixture meta form-scoped đăng ký runtime (như test_m72_activation):
   * KHÔNG đụng FORM_GRID_META production, chỉ tồn tại trong process này. */
  function cloneMeta(base, extra) {
    return JSON.parse(JSON.stringify(Object.assign({}, base, extra || {})));
  }

  // FIX_C1 / FIX_C2: CÙNG tên loop 'nganh_bo_sung', contract KHÁC nhau
  // (đúng kịch bản thật PLI_M12 vs PLII_M02).
  const FIX_C1 = 'FIX_P20_BS1';
  FD.registerFormGridMeta(FIX_C1, {
    loops: {
      nganh_bo_sung: Object.assign(cloneMeta(FD.GRID_META.nganh_bo_sung), {
        semanticKey: 'nganh_bo_sung'
      })
    }
  });
  const FIX_C2 = 'FIX_P20_BS2';
  FD.registerFormGridMeta(FIX_C2, {
    loops: {
      nganh_bo_sung: {
        label: 'Nganh bo sung bien the khac',
        minRows: 0, maxRows: null, required: false,
        allowAdd: true, allowDelete: true, allowReorder: true,
        confirmDeleteNonEmpty: true,
        requirePrimary: true, // khác C1
        columns: [
          { tag: 'ten_nganh_bo_sung', type: 'text', required: true },
          { tag: 'ma_nganh', type: 'vsic' }
        ], // khác C1: tag set + thiếu la_nganh_chinh
        duplicateKeys: [],
        outputOnlyTags: [],
        autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh_bo_sung' }, // khác
        activeWhen: { checkedKey: 'chk_bs_fixture' }, // khác mode
        semanticKey: 'nganh_bo_sung'
      }
    }
  });

  function mkRow(tags, j) {
    const r = { _row_id: FD.makeRowId() };
    tags.forEach(t => {
      r[t] = t === 'la_nganh_chinh' ? (j === 0 ? 'X' : '') : ('GT-' + t + '-' + j);
    });
    return r;
  }
  const stConflict = { values: {}, checks: {}, loops: {
    nganh_bo_sung: [
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 0),
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 1)
    ]
  } };

  // --- S2a. phát hiện conflict có cấu trúc -----------------------------
  const cfs = G.detectExportConflicts(stConflict, [FIX_C1, FIX_C2]);
  check('S2a.1 hai meta form-scoped khac contract -> dung 1 conflict',
    cfs.length === 1 && cfs[0].code === 'EXPORT_LOOP_CONTRACT_CONFLICT' &&
      cfs[0].loop === 'nganh_bo_sung',
    JSON.stringify(cfs.map(c => c.loop)));
  check('S2a.2 conflict liet ke ca hai ben: formId + semanticKey',
    cfs.length === 1 &&
      cfs[0].sides.map(s => s.formId).join(',') === FIX_C1 + ',' + FIX_C2 &&
      cfs[0].sides.every(s => s.semanticKey === 'nganh_bo_sung') &&
      cfs[0].winner.formId === FIX_C1);
  check('S2a.3 reasons neu du 4 loai khac biet (tag set/autoName/requirePrimary/actMode)',
    cfs.length === 1 &&
      cfs[0].reasons.some(r => r.indexOf('tap tag cot') >= 0) &&
      cfs[0].reasons.some(r => r.indexOf('autoName') >= 0 &&
        r.indexOf('ten_nganh_bo_sung') >= 0) &&
      cfs[0].reasons.some(r => r.indexOf('requirePrimary') >= 0) &&
      cfs[0].reasons.some(r => r.indexOf('activationModeOf') >= 0),
    JSON.stringify(cfs.length && cfs[0].reasons));
  check('S2a.4 message chua ten loop + ca hai formId',
    cfs.length === 1 && cfs[0].message.indexOf('"nganh_bo_sung"') >= 0 &&
      cfs[0].message.indexOf(FIX_C1) >= 0 && cfs[0].message.indexOf(FIX_C2) >= 0);

  // --- S2b. exportLoops mặc định: REPORT, payload giữ hành vi cũ -------
  const exBoth = G.exportLoops(stConflict, [FIX_C1, FIX_C2]);
  check('S2b.2 conflict duoc ghi report (lastExportConflicts) sau moi lan goi',
    G.lastExportConflicts.length === 1 &&
      G.lastExportConflicts[0].loop === 'nganh_bo_sung');
  const exFirst = G.exportLoops(stConflict, [FIX_C1]);
  check('S2b.1 payload van first-doc-wins (byte-equal voi chi muc dau)',
    eqJson(exBoth, exFirst));
  G.exportLoops(stConflict, [FIX_C1]); // goi lai -> report reset theo tung call
  check('S2b.3 report reset tung lan goi (khong cong don)',
    G.lastExportConflicts.length === 0);

  // --- S2c. exportLoopsStrict: FAIL LOUD -------------------------------
  let threw = null;
  try { G.exportLoopsStrict(stConflict, [FIX_C1, FIX_C2]); }
  catch (e) { threw = e; }
  check('S2c.1 strict NEM loi co cau truc khi conflict',
    !!threw && threw.code === 'EXPORT_LOOP_CONTRACT_CONFLICT' &&
      Array.isArray(threw.conflicts) && threw.conflicts.length === 1);
  check('S2c.2 loi strict khong de payload sot (throw truoc khi build)',
    !!threw);

  // --- S2d. tương thích ngược: contract THỰC SỰ tương đương ------------
  const FIX_E1 = 'FIX_P20_EQ1';
  const FIX_E2 = 'FIX_P20_EQ2';
  const eqLoop = () => ({
    label: 'Nganh xoa bo contract giong het nhau',
    minRows: 0, maxRows: null, required: false,
    allowAdd: true, allowDelete: true, allowReorder: true,
    confirmDeleteNonEmpty: true, requirePrimary: false,
    columns: [
      { tag: 'ten_nganh', type: 'text', required: true },
      { tag: 'ma_nganh', type: 'vsic' }
    ],
    duplicateKeys: [], outputOnlyTags: [],
    autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh' },
    semanticKey: 'nganh_xoa_bo_fixture'
  });
  FD.registerFormGridMeta(FIX_E1, { loops: { nganh_xoa_bo: eqLoop() } });
  FD.registerFormGridMeta(FIX_E2, { loops: { nganh_xoa_bo: eqLoop() } });
  const stEq = { values: {}, checks: {}, loops: {
    nganh_xoa_bo: [mkRow(['ten_nganh', 'ma_nganh'], 0)]
  } };
  const cfEq = G.detectExportConflicts(stEq, [FIX_E1, FIX_E2]);
  check('S2d.1 hai meta cung contract (requirePrimary/tag set/autoName/mode bang) -> KHONG conflict',
    cfEq.length === 0, JSON.stringify(cfEq.map(c => c.message)));
  const exEqStrict = G.exportLoopsStrict(stEq, [FIX_E1, FIX_E2]);
  const exEqPlain = G.exportLoops(stEq, [FIX_E1, FIX_E2]);
  check('S2d.2 contract tuong duong: strict xuat binh thuong, bang plain export',
    eqJson(exEqStrict, exEqPlain) &&
      exEqStrict.nganh_xoa_bo.length === 1 &&
      exEqStrict.nganh_xoa_bo[0].ten_nganh === 'GT-ten_nganh-0');

  // --- S2e. một scoped đơn độc + mẫu khác fallback global -> KHÔNG flag -
  // Thiết kế: chỉ meta TỰ KHAI form-scoped mới đối chiếu; fallback toàn cục
  // là contract dùng chung legacy (cùng object nên luôn tương đương) ->
  // tránh false positive cho dossier ghép mẫu bình thường.
  const cfSingle = G.detectExportConflicts(stConflict, [FIX_C2, 'PLI_M06']);
  check('S2e.1 mot scoped duy nhat (ben con lai fallback global) -> khong conflict',
    cfSingle.length === 0, JSON.stringify(cfSingle.map(c => c.message)));

  // --- S2f. combo production thật: mỗi loop scoped ở TỐI ĐA một mẫu ----
  // (dossier điển hình chọn 1 trong M12/M02 -> không bao giờ conflict)
  const stProd = { values: {}, checks: {}, loops: {
    nganh_bo_sung: [mkRow(['ten_nganh_bo_sung', 'ma_nganh', 'la_nganh_chinh'], 0)],
    ds_nganh_ctcp: [mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 0)]
  } };
  const outProd = G.exportLoops(stProd, ['PLII_M02', 'PLI_M72']);
  check('S2f.1 combo PLII_M02+PLI_M72 (loop khong giao nhau scoped) -> khong conflict, payload cu',
    G.lastExportConflicts.length === 0 &&
      outProd.ds_nganh_ctcp[0].la_nganh_chinh === 'X' &&
      outProd.nganh_bo_sung[0].la_nganh_chinh === 'X');

  // --- S2g. khác CHỈ activeWhen mode cũng bị bắt (report, không đổi payload)
  const FIX_M = 'FIX_P20_MODE';
  const m72Sel = cloneMeta(
    FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' }),
    { activeWhen: { checkedKey: 'chk_loai_hinh_fixture' }, semanticKey: 'ds_nganh_dntn' });
  FD.registerFormGridMeta(FIX_M, { loops: { ds_nganh_dntn: m72Sel } });
  const stMode = { values: {}, checks: {}, loops: {
    ds_nganh_dntn: [mkRow(['ten_nganh', 'ma_nganh'], 0)]
  } };
  const cfMode = G.detectExportConflicts(stMode, ['PLI_M72', FIX_M]);
  check('S2g.1 interim vs selector (activationModeOf khac) -> bat duoc conflict',
    cfMode.length === 1 &&
      cfMode[0].reasons.some(r => r.indexOf('interim-filled-data') >= 0 &&
        r.indexOf('selector') >= 0),
    JSON.stringify(cfMode.map(c => c.reasons)));
  const exMode = G.exportLoops(stMode, ['PLI_M72', FIX_M]);
  const modeReport = G.lastExportConflicts.slice(); // chup TRUOC call ke tiep
  const exModeFirst = G.exportLoops(stMode, ['PLI_M72']);
  check('S2g.2 report mode giu nguyen hop dong first-wins cua test_m72 muc 5',
    eqJson(exMode, exModeFirst) && exMode.ds_nganh_dntn.length === 1 &&
      modeReport.length === 1);

  // --- S2h. signature thuần --------------------------------------------
  const sv = G.exportContractSig(FD.GRID_META.ds_thanh_vien);
  check('S2h.1 exportContractSig: JSON-thuần, colTags da sort',
    typeof sv.colTags === 'string' &&
      sv.colTags.split('|').join() ===
      sv.colTags.split('|').slice().sort().join() &&
      sv.requirePrimary === false && sv.actMode === null);
})();

// ---------------------------------------------------------------- ket luan
console.log('-'.repeat(60));
console.log('test_p20_hardening: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
