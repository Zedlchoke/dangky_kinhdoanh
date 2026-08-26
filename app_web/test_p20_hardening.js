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

// =====================================================================
// S3. FOCUS SAU ROW OPERATION (thuần + DOM giả thủ công)
// =====================================================================

(function s3() {
  const GF = App.GridFocus;
  check('S3.0 seam GridFocus duoc export (thuan + DOM)',
    typeof GF.focusTagOfGrid === 'function' &&
      typeof GF.nextSelAfterDelete === 'function' &&
      typeof GF.focusGridRow === 'function');

  // --- S3a. [PURE] focusTagOfGrid --------------------------------------
  check('S3a.1 ds_nganh (toan cuc) -> ma_nganh',
    GF.focusTagOfGrid(FD.GRID_META.ds_nganh) === 'ma_nganh');
  check('S3a.2 ds_tv_ho_gia_dinh (khong co ma_nganh) -> editable dau = ho_ten',
    GF.focusTagOfGrid(FD.GRID_META.ds_tv_ho_gia_dinh) === 'ho_ten');
  check('S3a.3 form-scoped: M02.ds_nganh va M02.nganh_bo_sung deu uu tien ma_nganh',
    GF.focusTagOfGrid(FD.getGridMeta({ docId: 'PLII_M02', loop: 'ds_nganh' })) ===
      'ma_nganh' &&
      GF.focusTagOfGrid(
        FD.getGridMeta({ docId: 'PLII_M02', loop: 'nganh_bo_sung' })) === 'ma_nganh');
  check('S3a.4 meta null/rong -> null',
    GF.focusTagOfGrid(null) === null && GF.focusTagOfGrid({}) === null);
  check('S3a.5 chi co cot khong goc duoc (readonly/outputOnly/radio/checkbox) -> null',
    GF.focusTagOfGrid({ columns: [
      { tag: 'a', type: 'readonly' }, { tag: 'b', type: 'outputOnly' },
      { tag: 'c', type: 'radio' }, { tag: 'd', type: 'checkbox' }
    ] }) === null);

  // --- S3b. [PURE] nextSelAfterDelete ----------------------------------
  function ridRows(ids) {
    return ids.map(id => ({ _row_id: id }));
  }
  check('S3b.1 id dang chon con song -> giu nguyen',
    GF.nextSelAfterDelete(ridRows(['r1', 'r2', 'r3']), ridRows(['r1', 'r2', 'r3']),
      'r2') === 'r2');
  check('S3b.2 xoa dong giua -> dong ke theo index (row thay cho vi tri cu)',
    GF.nextSelAfterDelete(ridRows(['r1', 'r2', 'r3']), ridRows(['r1', 'r3']),
      'r2') === 'r3');
  check('S3b.3 xoa dong CUOI -> lui ve dong truoc (clamp cuoi)',
    GF.nextSelAfterDelete(ridRows(['r1', 'r2', 'r3']), ridRows(['r1', 'r2']),
      'r3') === 'r2');
  check('S3b.4 xoa dong DAU -> lay dong tai index 0 sau xoa',
    GF.nextSelAfterDelete(ridRows(['r1', 'r2']), ridRows(['r2']), 'r1') === 'r2');
  check('S3b.5 chua chon gi (null) -> dong cuoi truoc khi xoa',
    GF.nextSelAfterDelete(ridRows(['a', 'b', 'c']), ridRows(['a', 'c']),
      null) === 'c');
  check('S3b.6 bang rong sau xoa -> null (khong exception)',
    GF.nextSelAfterDelete(ridRows(['a']), [], 'a') === null);

  // --- S3c. DOM giả thủ công (mô phỏng markup của render.renderLoop) ----
  let __focusLog = [];
  let __scrollLog = [];
  const fakeDoc = { activeElement: null };
  // focusGridRow đọc global `document` tại thời điểm gọi -> gắn DOM giả vào
  // global để node-test chạy đúng đường code browser.
  global.document = fakeDoc;

  class FEl {
    constructor(tag, attrs, children) {
      this.tag = String(tag).toLowerCase();
      this.attrs = attrs || {};
      this.children = [];
      this.parent = null;
      (children || []).forEach(c => this.append(c));
    }
    append(c) { c.parent = this; this.children.push(c); return c; }
    getAttribute(k) {
      return Object.prototype.hasOwnProperty.call(this.attrs, k)
        ? this.attrs[k] : null;
    }
    classes() { return String(this.attrs['class'] || '').split(/\s+/).filter(Boolean); }
    focus() { fakeDoc.activeElement = this; __focusLog.push(this); }
    scrollIntoView(o) { __scrollLog.push(o); }
    querySelector(sel) { return qsa(this, selToToks(sel))[0] || null; }
    querySelectorAll(sel) { return qsa(this, selToToks(sel)); }
  }

  function parseTok(tok) {
    const t = { tag: null, cls: [], attrs: [] };
    const m = tok.match(/^([a-zA-Z][\w-]*)/);
    if (m) { t.tag = m[1].toLowerCase(); tok = tok.slice(m[1].length); }
    let mm;
    const reCls = /\.([\w-]+)/g;
    while ((mm = reCls.exec(tok))) t.cls.push(mm[1]);
    const reAttr = /\[([^\]=]+)="([^"]*)"\]/g;
    while ((mm = reAttr.exec(tok))) t.attrs.push([mm[1], mm[2]]);
    return t;
  }
  function matchTok(el, tk) {
    if (tk.tag && el.tag !== tk.tag) return false;
    const cs = el.classes();
    for (let i = 0; i < tk.cls.length; i++) {
      if (cs.indexOf(tk.cls[i]) < 0) return false;
    }
    for (let j = 0; j < tk.attrs.length; j++) {
      if (String(el.getAttribute(tk.attrs[j][0])) !== tk.attrs[j][1]) return false;
    }
    return true;
  }
  /* Descendant combinator thuần: mọi node khớp chuỗi token với các bước
   * trung gian lồng đúng (khớp browser cho tập selector hẹp ta dùng). */
  function qsa(el, toks, ti, out) {
    ti = ti || 0; out = out || [];
    if (ti >= toks.length) return out; // hết chuỗi token: dừng đệ quy
    el.children.forEach(function (ch) {
      if (matchTok(ch, toks[ti])) {
        if (ti === toks.length - 1) out.push(ch);
        qsa(ch, toks, ti + 1, out);
      }
      qsa(ch, toks, ti, out);
    });
    return out;
  }
  function selToToks(sel) { return sel.trim().split(/\s+/).map(parseTok); }
  fakeDoc.querySelector = function (sel) { return qsa(fakeDoc, selToToks(sel))[0] || null; };
  fakeDoc.querySelectorAll = function (sel) { return qsa(fakeDoc, selToToks(sel)); };

  /* Ô input như renderLoop xuất (P2.0 chỉ cần: class/data-tag/readonly). */
  function fld(tag, opts) {
    opts = opts || {};
    return new FEl('input', {
      type: opts.radio ? 'radio' : 'text',
      'class': opts.radio ? 'chk-box loop-radio'
        : 'fld loop-fld' + (opts.vsic ? ' vsic-fld' : ''),
      'data-tag': tag,
      'data-key': 'loop:L:0:' + tag,
      readonly: opts.readonly ? '' : null
    });
  }
  function trOf(rowId, inputs) {
    return new FEl('tr', {
      'data-row-index': '0',
      'data-row-id': rowId || null,
      'data-loop': 'L'
    }, [new FEl('td', {}, inputs)]);
  }
  function tableOf(loop, trs) {
    return new FEl('table',
      { 'class': 'btable loop-table', 'data-loop': loop },
      [new FEl('tbody', {}, trs)]);
  }
  function installDoc(tables) {
    fakeDoc.children = tables.slice();
  }
  function resetLogs() { __focusLog = []; __scrollLog = []; fakeDoc.activeElement = null; }

  // Bảng ngành (ds_nganh): ten_nganh readonly, ma_nganh, chi_tiet, radio
  const nganhMeta = FD.GRID_META.ds_nganh;
  installDoc([
    tableOf('ds_nganh', [
      trOf('ra', [fld('ten_nganh', { readonly: true, vsic: true }),
        fld('ma_nganh', { vsic: true }), fld('chi_tiet'),
        fld('la_nganh_chinh', { radio: true })]),
      trOf('rb', [fld('ten_nganh', { readonly: true, vsic: true }),
        fld('ma_nganh', { vsic: true }), fld('chi_tiet'),
        fld('la_nganh_chinh', { radio: true })]),
      trOf('rc', [fld('ten_nganh', { readonly: true, vsic: true }),
        fld('ma_nganh', { vsic: true }), fld('chi_tiet'),
        fld('la_nganh_chinh', { radio: true })])
    ]),
    // Bảng hộ gia đình: ho_ten đầu tiên, chu_ky outputOnly (KHÔNG có input)
    tableOf('ds_tv_ho_gia_dinh', [
      trOf('ha', [fld('ho_ten'), fld('ngay_sinh'), fld('so_cccd')]),
      trOf('hb', [fld('ho_ten'), fld('ngay_sinh'), fld('so_cccd')])
    ])
  ]);

  // ADD trên bảng ngành: focus ô mã ngành dòng mới
  resetLogs();
  let okAdd = GF.focusGridRow('ds_nganh', {
    rowId: 'rb', idx: 1,
    tag: GF.focusTagOfGrid(nganhMeta)
  });
  check('S3c.1 add ds_nganh -> focus o ma_nganh DONG MOI (khong phai ten_nganh readonly)',
    okAdd && __focusLog.length === 1 &&
      __focusLog[0].getAttribute('data-tag') === 'ma_nganh' &&
      __focusLog[0].getAttribute('readonly') === null &&
      __focusLog[0].parent.parent.getAttribute('data-row-id') === 'rb');

  // ADD trên bảng hộ gia đình: focus editable đầu = ho_ten
  resetLogs();
  let okHgd = GF.focusGridRow('ds_tv_ho_gia_dinh', {
    rowId: 'hb', idx: 1,
    tag: GF.focusTagOfGrid(FD.GRID_META.ds_tv_ho_gia_dinh)
  });
  check('S3c.2 add ds_tv_ho_gia_dinh -> focus editable dau = ho_ten',
    okHgd && __focusLog.length === 1 &&
      __focusLog[0].getAttribute('data-tag') === 'ho_ten' &&
      __scrollLog.length === 1);

  // REORDER: selection/focus bám _row_id dù index đổi
  // mô phỏng uiMoveRow: GridCtl.moveRow rồi focus theo id + index mới
  const stMove = { values: {}, checks: {}, loops: {} };
  stMove.loops.L = ridRows(['ra', 'rb', 'rc']);
  installDoc([tableOf('L', [
    trOf('ra', [fld('chi_tiet')]), trOf('rb', [fld('chi_tiet')]),
    trOf('rc', [fld('chi_tiet')]) ]) ]);
  let atDown = G.moveRow(stMove, 'L', 'rc', -1);   // rc: 2 -> 1
  resetLogs();
  GF.focusGridRow('L', { rowId: 'rc', idx: atDown, tag: null });
  const fMove1 = __focusLog[0];
  let atUp = G.moveRow(stMove, 'L', 'ra', 1);       // ra: 0 -> 1
  resetLogs();
  GF.focusGridRow('L', { rowId: 'ra', idx: atUp, tag: null });
  const fMove2 = __focusLog[0];
  check('S3c.3 move down/up: focus dung ROW theo _row_id sau khi thu tu doi',
    atDown === 1 && atUp === 1 &&
      fMove1 && fMove1.parent.parent.getAttribute('data-row-id') === 'rc' &&
      fMove2 && fMove2.parent.parent.getAttribute('data-row-id') === 'ra' &&
      JSON.stringify(stMove.loops.L.map(r => r._row_id)) === '["rc","ra","rb"]');

  // DELETE: dòng đang chọn bị xóa -> focus dòng kề theo index an toàn
  const stDel = { values: {}, checks: {}, loops: {} };
  stDel.loops.ds_nganh = ridRows(['r1', 'r2', 'r3']);
  installDoc([tableOf('ds_nganh', [
    trOf('r1', [fld('ma_nganh', { vsic: true })]),
    trOf('r2', [fld('ma_nganh', { vsic: true })]),
    trOf('r3', [fld('ma_nganh', { vsic: true })]) ]) ]);
  const beforeRows = stDel.loops.ds_nganh.slice();
  G.deleteRows(stDel, 'ds_nganh', ['r2']);
  const nid = GF.nextSelAfterDelete(beforeRows, stDel.loops.ds_nganh, 'r2');
  resetLogs();
  GF.focusGridRow('ds_nganh', {
    rowId: nid, idx: G.findRowIndex(stDel.loops.ds_nganh, nid),
    tag: GF.focusTagOfGrid(nganhMeta)
  });
  check('S3d.1 delete dong giua -> selection + focus chuyen sang row ke (r3)',
    nid === 'r3' && __focusLog.length === 1 &&
      __focusLog[0].parent.parent.getAttribute('data-row-id') === 'r3');

  // DELETE dòng cuối -> focus lùi về dòng trước
  const stDel2 = { values: {}, checks: {}, loops: {} };
  stDel2.loops.ds_nganh = ridRows(['r1', 'r2']);
  installDoc([tableOf('ds_nganh', [
    trOf('r1', [fld('ma_nganh', { vsic: true })]),
    trOf('r2', [fld('ma_nganh', { vsic: true })]) ]) ]);
  const b2 = stDel2.loops.ds_nganh.slice();
  G.deleteRows(stDel2, 'ds_nganh', ['r2']);
  const nid2 = GF.nextSelAfterDelete(b2, stDel2.loops.ds_nganh, 'r2');
  resetLogs();
  GF.focusGridRow('ds_nganh', { rowId: nid2, idx: 0, tag: 'ma_nganh' });
  check('S3d.2 delete dong CUOI duoc chon -> focus ve row truoc (r1)',
    nid2 === 'r1' &&
      __focusLog[0].parent.parent.getAttribute('data-row-id') === 'r1');

  // Bảng rỗng / row không tồn tại / bảng vắng mặt: false, KHÔNG exception
  resetLogs();
  installDoc([tableOf('empty_loop', [])]);
  let threwEmpty = null;
  try {
    const r1e = GF.focusGridRow('empty_loop', { rowId: 'x', idx: 0, tag: 'y' });
    const r2e = GF.focusGridRow('missing_loop', { rowId: 'x', idx: 0, tag: 'y' });
    const r3e = GF.focusGridRow('empty_loop', {});
    threwEmpty = (r1e === false && r2e === false && r3e === false);
  } catch (e) { threwEmpty = false; }
  check('S3e.1 bang rong/bang mat/idx le -> tra false, khong exception, khong focus lac',
    threwEmpty === true && __focusLog.length === 0);

  // Chuỗi fallback: thiếu ô tag -> input.loop-fld không readonly đầu dòng;
  // dòng chỉ có radio -> input bất kỳ
  installDoc([tableOf('fx', [
    trOf('f1', [fld('ma_nganh', { vsic: true }), fld('chi_tiet')]), // đủ
    trOf('f2', [fld('chi_tiet'), fld('ghi_chu')]),                  // thiếu tag
    trOf('f3', [fld('la_nganh_chinh', { radio: true })])            // chỉ radio
  ]) ]);
  resetLogs(); GF.focusGridRow('fx', { rowId: 'f2', idx: 1, tag: 'ma_nganh' });
  const fb2 = __focusLog[0];
  resetLogs(); GF.focusGridRow('fx', { rowId: 'f3', idx: 2, tag: 'ma_nganh' });
  const fb3 = __focusLog[0];
  check('S3e.2 fallback: thieu o tag -> loop-fld dau tien khong readonly',
    fb2 && fb2.getAttribute('data-tag') === 'chi_tiet');
  check('S3e.3 fallback cuoi: chi con radio -> van focus input do, khong roi',
    fb3 && fb3.getAttribute('data-tag') === 'la_nganh_chinh');
})();

// ---------------------------------------------------------------- ket luan
console.log('-'.repeat(60));
console.log('test_p20_hardening: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
