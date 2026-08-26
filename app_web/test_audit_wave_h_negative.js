/* test_audit_wave_h_negative.js - INDEPENDENT AUDIT (wave P1.1/P2.0 + L0).
 *
 * Negative tests bổ sung do auditor tự thiết kế (không tham gia code wave),
 * phủ 7 nhóm H1-H7 theo phạm vi audit:
 *  H1 selector precedence: checkedKey/valueOf là NGUỒN CHÍNH; minFilledRows
 *     chỉ INTERIM và bị BỎ QUA khi có selector.
 *  H2 valueOf: so giá trị sau TRIM, phân biệt HOA-THƯỜNG, equals nhiều phần tử.
 *  H3 export guard theo selector: grid inactive-theo-selector -> payload rỗng
 *     dù store còn rows (production PLI_M72 giờ là selector P1.2 Option D);
 *     grid không activeWhen -> payload giữ nguyên hành vi cũ.
 *  H4 conflict matrix: same-ref short-circuit / clone-vs-global tương đương /
 *     combo thật PLI_M12(global)+PLII_M02(scoped) / strict throw có cấu trúc,
 *     plain ghi lastExportConflicts + payload first-wins byte-nguyên.
 *  H5 deep-clone isolation: mutate autoName/outputOnlyTags/duplicateKeys/
 *     activeWhen.valueOf qua meta trả về không lan sang GRID_META gốc hay
 *     meta mẫu khác.
 *  H6 focus sau row-op: focusTagOfGrid ưu tiên ma_nganh -> editable đầu
 *     (bỏ readonly/outputOnly/radio/checkbox); nextSelAfterDelete theo _row_id;
 *     focusGridRow an toàn trên DOM giả, bảng rỗng không exception.
 *  H7 allowlist ĐỘC LẬP: tự chạy git diff --name-only baseline/p1.2-d882793..HEAD, đối chiếu
 *     tập file với danh sách auditor TỰ LẬP từ ownership check (không dùng
 *     mảng ALLOW của test_audit_p1_negative).
 *
 * Chạy: node app_web/test_audit_wave_h_negative.js
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
function snap(o) { return JSON.parse(JSON.stringify(o)); }
function cloneMeta(base, extra) {
  return Object.assign(snap(base), extra || {});
}
function mkRow(tags, j) {
  const r = { _row_id: FD.makeRowId() };
  tags.forEach(t => {
    r[t] = t === 'la_nganh_chinh' ? (j === 0 ? 'X' : '') : ('GT-' + t + '-' + j);
  });
  return r;
}

// =====================================================================
// H1. SELECTOR PRECEDENCE - selector thắng tuyệt đối minFilledRows
// =====================================================================

(function h1() {
  const metaBoth = {
    label: 'H1 fixture', requirePrimary: true,
    columns: [
      { tag: 'ma_nganh', type: 'vsic', required: true },
      { tag: 'ten_nganh', type: 'readonly' }
    ],
    // mồi nhử minFilledRows=5: nếu precedence sai sẽ lật kết quả H1.2/H1.3
    activeWhen: { checkedKey: 'chk_h1', minFilledRows: 5 },
    semanticKey: 'h1'
  };
  const filledRow = () => ({ _row_id: FD.makeRowId(), ma_nganh: '0111' });
  const blankRow = () => ({ _row_id: FD.makeRowId(), ma_nganh: '' });

  check('H1.1 checkedKey+minFilledRows cung khai -> activationModeOf = "selector"',
    FD.activationModeOf(metaBoth) === 'selector');

  check('H1.2 selector TRUE thang ca khi 0 dong du lieu (minFilledRows=5 bi bo qua)',
    FD.isActiveGrid(metaBoth, [blankRow(), blankRow()],
      { values: {}, checks: { chk_h1: true } }) === true);

  check('H1.3 selector FALSE -> inactive DU dang co >=minFilledRows dong du lieu',
    FD.isActiveGrid(metaBoth,
      [filledRow(), filledRow(), filledRow(), filledRow(), filledRow(), filledRow()],
      { values: {}, checks: {} }) === false);

  check('H1.4 checkedKey thieu trong store -> inactive (an toan)',
    FD.isActiveGrid(metaBoth, [filledRow()], { values: {}, checks: {} }) === false);

  // Bỏ selector -> INTERIM trở lại đúng nghĩa "dòng có dữ liệu";
  // checks=true trong store PHẢI bị lãng quên hoàn toàn.
  const metaInterim = cloneMeta(metaBoth, { activeWhen: { minFilledRows: 2 } });
  const stChecksOn = { values: {}, checks: { chk_h1: true } };
  check('H1.5 bo selector -> mode ve "interim-filled-data"',
    FD.activationModeOf(metaInterim) === 'interim-filled-data');
  check('H1.6 interim: checks khong con tac dung, 1/2 dong du lieu -> inactive',
    FD.isActiveGrid(metaInterim, [filledRow(), blankRow()], stChecksOn) === false);
  check('H1.7 interim: du 2 dong co du lieu -> active',
    FD.isActiveGrid(metaInterim, [filledRow(), filledRow(), blankRow()],
      stChecksOn) === true);

  check('H1.8 khong activeWhen -> mode null va luon active (hanh vi cu)',
    FD.activationModeOf(FD.GRID_META.ds_nganh) === null &&
      FD.isActiveGrid(FD.GRID_META.ds_nganh, [], {}) === true);
})();

// =====================================================================
// H2. VALUEOF SELECTOR - trim + case-sensitive + AND với checkedKey
// =====================================================================

(function h2() {
  const meta = {
    label: 'H2 fixture', requirePrimary: false,
    columns: [{ tag: 'ma_nganh', type: 'vsic' }],
    activeWhen: { valueOf: { key: 'dn.loai_hinh_h2', equals: ['CTCP', 'DHDN'] } },
    semanticKey: 'h2'
  };
  const rows = [{ _row_id: FD.makeRowId(), ma_nganh: '0111' }];
  const st = v => ({ values: { 'dn.loai_hinh_h2': v }, checks: {} });

  check('H2.1 value co khoang trang quanh -> trim truoc khi so -> active',
    FD.isActiveGrid(meta, rows, st('  CTCP ')) === true);

  check('H2.2 sai hoa-thuong ("ctcp") -> KHONG khop -> inactive',
    FD.isActiveGrid(meta, rows, st('ctcp')) === false);

  check('H2.3 key thieu trong store -> inactive',
    FD.isActiveGrid(meta, rows, { values: {}, checks: {} }) === false);

  check('H2.4 gia tri nam trong equals nhieu phan tu ("DHDN") -> active',
    FD.isActiveGrid(meta, rows, st('DHDN')) === true);

  check('H2.5 gia tri ngoai equals ("TNHH") -> inactive',
    FD.isActiveGrid(meta, rows, st('TNHH')) === false);

  // checkedKey + valueOf cùng khai -> AND (cả hai phải thoả)
  const metaAnd = cloneMeta(meta, {
    activeWhen: {
      checkedKey: 'chk_and',
      valueOf: { key: 'dn.loai_hinh_h2', equals: ['CTCP'] }
    }
  });
  check('H2.6 AND: ca checkedKey=true VA value khop -> active',
    FD.isActiveGrid(metaAnd, rows,
      { values: { 'dn.loai_hinh_h2': 'CTCP' }, checks: { chk_and: true } }) === true);
  check('H2.7 AND: value khop nhung checkedKey=false -> inactive',
    FD.isActiveGrid(metaAnd, rows,
      { values: { 'dn.loai_hinh_h2': 'CTCP' }, checks: {} }) === false);
})();

// =====================================================================
// H3. EXPORT GUARD THEO SELECTOR - lọc payload, không đụng store
// =====================================================================

(function h3() {
  const FIX_H3 = 'FIX_AUDIT_H3';
  FD.registerFormGridMeta(FIX_H3, {
    loops: {
      ds_nganh_dntn: cloneMeta(
        FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' }),
        { activeWhen: { checkedKey: 'chk_h3' }, semanticKey: 'ds_nganh_dntn' })
    }
  });

  function storeH3() {
    return { values: {}, checks: {}, loops: {
      ds_nganh_dntn: [
        mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 0),
        mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 1)
      ]
    } };
  }

  // Selector FALSE: grid inactive-theo-selector -> payload RỖNG dù store còn rows
  const stOff = storeH3();
  stOff.checks = {};
  const exOff = G.exportLoops(stOff, [FIX_H3]);
  check('H3.1 grid inactive-theo-selector -> payload rong []',
    Array.isArray(exOff.ds_nganh_dntn) && exOff.ds_nganh_dntn.length === 0,
    JSON.stringify(exOff.ds_nganh_dntn));
  check('H3.2 guard CHI loc payload - store nguyen ven 2 rows',
    stOff.loops.ds_nganh_dntn.length === 2);

  // Selector TRUE: giữ nguyên rows + map la_nganh_chinh X/''
  const stOn = storeH3();
  stOn.checks = { chk_h3: true };
  const exOn = G.exportLoops(stOn, [FIX_H3]);
  check('H3.3 grid active-theo-selector -> payload day du + map X/"',
    exOn.ds_nganh_dntn.length === 2 &&
      exOn.ds_nganh_dntn[0].la_nganh_chinh === 'X' &&
      exOn.ds_nganh_dntn[1].la_nganh_chinh === '');

  // P1.2 Option D: production PLI_M72 là SELECTOR (valueOf dn.loai_hinh),
  // KHÔNG còn INTERIM. Chưa chọn loại hình -> grid inactive -> payload RỖNG
  // (dòng trống cũng không sot vào payload nữa).
  const stBlank = { values: {}, checks: {}, loops: {
    ds_nganh_dntn: [{ _row_id: FD.makeRowId(),
      ten_nganh: '', ma_nganh: '', la_nganh_chinh: '' }]
  } };
  const prodM72 = FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' });
  check('H3.4 production M72 la selector (valueOf dn.loai_hinh)',
    prodM72.activeWhen != null &&
      FD.activationModeOf(prodM72) === 'selector' &&
      prodM72.activeWhen.valueOf.key === 'dn.loai_hinh');
  const exSelNone = G.exportLoops(stBlank, ['PLI_M72']);
  check('H3.5 selector inactive (chua chon loai hinh) -> payload rong (khong sot token)',
    exSelNone.ds_nganh_dntn.length === 0,
    JSON.stringify(exSelNone.ds_nganh_dntn));
  // Chọn đúng biến thể -> giữ nguyên dòng (hành vi active-theo-selector)
  const stOnDntn = { values: { 'dn.loai_hinh': 'DNTN' }, checks: {},
    loops: { ds_nganh_dntn: [{ _row_id: FD.makeRowId(),
      ten_nganh: '', ma_nganh: '', la_nganh_chinh: '' }] } };
  check('H3.5b selector DNTN -> payload giu nguyen dong',
    G.exportLoops(stOnDntn, ['PLI_M72']).ds_nganh_dntn.length === 1);

  // Grid không có activeWhen: không bao giờ bị lọc
  const stOld = { values: {}, checks: {}, loops: { ds_thanh_vien:
    [mkRow(['ho_ten'], 0)] } };
  check('H3.6 grid khong activeWhen -> khong filter (hanh vi cu nguyen ven)',
    G.exportLoops(stOld, ['PLI_M06']).ds_thanh_vien.length === 1);
})();

// =====================================================================
// H4. CONFLICT MATRIX - same-ref / clone-vs-global / combo thật / strict
// =====================================================================

(function h4() {
  function sides(name, docIds) { return G.collectLoopSides(name, docIds); }

  // (a) global+global cùng reference: mọi mẫu fallback chung GRID_META
  check('H4a.1 hai mau cung fallback global -> 1 side (same-reference short-circuit)',
    sides('ds_thanh_vien', ['PLI_M02', 'PLI_M06']).length === 1);
  const stGlobal = { values: {}, checks: {}, loops: {
    ds_thanh_vien: [mkRow(['ho_ten', 'von_dong_gop'], 0)] } };
  check('H4a.2 global+global same-ref -> khong flag',
    G.detectExportConflicts(stGlobal, ['PLI_M02', 'PLI_M06']).length === 0);

  // (b) scoped-clone vs global TƯƠNG ĐƯƠNG signature: không false-positive
  const stClone = { values: {}, checks: {}, loops: {
    ds_nganh: [
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 0),
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 1)
    ] } };
  const cloneIds = ['PLII_M02', 'PLI_M02', 'PLI_M06'];
  check('H4b.1 clone mkGrid (M02.ds_nganh) vs global cung signature -> khong flag',
    G.detectExportConflicts(stClone, cloneIds).length === 0,
    JSON.stringify(G.detectExportConflicts(stClone, cloneIds).map(c => c.message)));
  const exCloneS = G.exportLoopsStrict(stClone, cloneIds);
  check('H4b.2 strict xuat binh thuong bang plain khi contract tuong duong',
    eqJson(exCloneS, G.exportLoops(stClone, cloneIds)) &&
      exCloneS.ds_nganh[0].la_nganh_chinh === 'X' &&
      G.lastExportConflicts.length === 0);

  // (c) combo THẬT: PLI_M12 dùng GRID_META.nganh_bo_sung (global),
  //     PLII_M02 khai literal scoped khác tag/autoName -> conflict đúng reasons
  const stReal = { values: {}, checks: {}, loops: {
    nganh_bo_sung: [
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 0),
      mkRow(['ten_nganh', 'ma_nganh', 'la_nganh_chinh'], 1)
    ] } };
  const realIds = ['PLI_M12', 'PLII_M02'];
  const cfReal = G.detectExportConflicts(stReal, realIds);
  check('H4c.1 combo that M12(global)+M02(scoped) -> dung 1 conflict',
    cfReal.length === 1 && cfReal[0].code === 'EXPORT_LOOP_CONTRACT_CONFLICT' &&
      cfReal[0].loop === 'nganh_bo_sung');
  check('H4c.2 winner la mau dau theo docIds (PLI_M12), du 2 sides khac reference',
    cfReal.length === 1 && cfReal[0].winner.docId === 'PLI_M12' &&
      cfReal[0].sides.length === 2 &&
      cfReal[0].sides[0].docId === 'PLI_M12' &&
      cfReal[0].sides[1].docId === 'PLII_M02' &&
      cfReal[0].sides[1].semanticKey === 'nganh_bo_sung');
  check('H4c.3 reasons neu ro lech tap tag cot + autoName',
    cfReal.length === 1 &&
      cfReal[0].reasons.some(r => r.indexOf('tap tag cot') >= 0 &&
        r.indexOf('ten_nganh_bo_sung') >= 0) &&
      cfReal[0].reasons.some(r => r.indexOf('autoName') >= 0),
    JSON.stringify(cfReal.length ? cfReal[0].reasons : []));

  // (d) strict throw có cấu trúc; plain ghi report + payload first-wins nguyên
  let threw = null;
  try { G.exportLoopsStrict(stReal, realIds); }
  catch (e) { threw = e; }
  const c0 = threw && threw.conflicts && threw.conflicts[0];
  check('H4d.1 strict nem EXPORT_LOOP_CONTRACT_CONFLICT du truong loop/winner/sides/reasons',
    !!threw && threw.code === 'EXPORT_LOOP_CONTRACT_CONFLICT' &&
      !!c0 && typeof c0.loop === 'string' &&
      c0.winner && typeof c0.winner.docId === 'string' &&
      Array.isArray(c0.sides) && c0.sides.length >= 2 &&
      Array.isArray(c0.reasons) && c0.reasons.length >= 1);

  const exBoth = G.exportLoops(stReal, realIds);
  const report = G.lastExportConflicts.slice(); // chụp TRƯỚC lần gọi kế (reset)
  const exFirst = G.exportLoops(stReal, ['PLI_M12']);
  check('H4d.2 plain ghi lastExportConflicts (reset tung lan goi)',
    report.length === 1 && G.lastExportConflicts.length !== undefined);
  check('H4d.3 payload first-wins byte-nguyen (ghep 2 mau == chi mau dau)',
    eqJson(exBoth, exFirst) && exBoth.nganh_bo_sung.length === 2);
})();

// =====================================================================
// H5. DEEP-CLONE ISOLATION - mutate mọi loại field nested qua meta trả về
// =====================================================================

(function h5() {
  const m72 = FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' });
  const m02ds = FD.getGridMeta({ docId: 'PLII_M02', loop: 'ds_nganh' });
  const beforeGlobal = snap(FD.GRID_META.ds_nganh);
  const beforeSibling = snap(FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_ctcp);
  const beforeM72Self = snap(m72);
  const beforeM02ds = snap(m02ds);

  // Không chia sẻ bất kỳ reference nested nào với bản gốc
  const gds = FD.GRID_META.ds_nganh;
  check('H5.1 meta tra ve khong share columns/autoName/dupKeys/outTags/activeWhen voi GRID_META',
    m72.columns !== gds.columns && m72.columns[0] !== gds.columns[0] &&
      (!m72.autoName || m72.autoName !== gds.autoName) &&
      m72.duplicateKeys !== gds.duplicateKeys &&
      m72.outputOnlyTags !== gds.outputOnlyTags &&
      (!m72.activeWhen || m72.activeWhen !== gds.activeWhen));

  function mutateAll(m) {
    if (m.autoName) {
      m.autoName.codeTag = 'hack_code';
      m.autoName.nameTag = 'hack_name';
    }
    m.outputOnlyTags.push('hack_out');
    m.duplicateKeys.push('hack_key');
    // activeWhen lồng valueOf - kiểm cả object sâu 2 mức
    if (m.activeWhen) {
      m.activeWhen.valueOf = { key: 'hack_vof', equals: ['X'] };
      m.activeWhen.minFilledRows = 999;
    }
    return m;
  }

  const snapM72 = JSON.stringify(m72);
  mutateAll(m72);
  check('H5.2 mutate meta M72 -> GRID_META.ds_nganh nguyen ven (JSON)',
    eqJson(FD.GRID_META.ds_nganh, beforeGlobal));
  check('H5.3 mutate meta M72 -> loop anh em (ds_nganh_ctcp) nguyen ven',
    eqJson(FD.FORM_GRID_META.PLI_M72.loops.ds_nganh_ctcp, beforeSibling));
  check('H5.4 mutate meta M72 -> meta mau khac (M02.ds_nganh) nguyen ven',
    eqJson(m02ds, beforeM02ds));
  // khôi phục tại chỗ giữ nguyên reference trong FORM_GRID_META
  const fresh = JSON.parse(snapM72);
  Object.keys(m72).forEach(k => delete m72[k]);
  Object.assign(m72, fresh);
  check('H5.5 khoi phuc tai cho giu dung reference trong resolver',
    FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_dntn' }) === m72 &&
      eqJson(m72, beforeM72Self));

  const snapG = JSON.stringify(gds);
  mutateAll(m02ds); // clone của global qua mkGrid
  check('H5.6 mutate clone M02.ds_nganh -> GRID_META.ds_nganh nguyen ven',
    eqJson(FD.GRID_META.ds_nganh, beforeGlobal));
  // khôi phục từ snapshot CỦA CHÍNH nó (clone có override riêng:
  // required/minRows/semanticKey - không phải bản sao GRID_META)
  const freshM02 = JSON.parse(beforeM02ds && JSON.stringify(beforeM02ds));
  Object.keys(m02ds).forEach(k => delete m02ds[k]);
  Object.assign(m02ds, freshM02);
  check('H5.7 khoi phuc M02.ds_nganh ve dung snapshot ban dau (giu override)',
    eqJson(m02ds, beforeM02ds) &&
      m02ds.semanticKey === 'nganh_hien_tai' && m02ds.required === false);
})();

// =====================================================================
// H6. FOCUS SAU ROW-OP - pure helpers + DOM giả an toàn
// =====================================================================

(function h6() {
  const GF = App.GridFocus;

  check('H6.1 grid co ma_nganh -> target ma_nganh (du ten editable dung truoc)',
    GF.focusTagOfGrid({
      columns: [
        { tag: 'ten_nganh', type: 'text' },
        { tag: 'ma_nganh', type: 'vsic' },
        { tag: 'la_nganh_chinh', type: 'radio' }
      ]
    }) === 'ma_nganh' &&
      GF.focusTagOfGrid(FD.GRID_META.ds_nganh) === 'ma_nganh');

  check('H6.2 khong co ma_nganh -> editable dau theo meta columns',
    GF.focusTagOfGrid({
      columns: [
        { tag: 'stt_c', type: 'readonly' },
        { tag: 'ho_ten', type: 'text' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ]
    }) === 'ho_ten');

  check('H6.3 bo qua readonly/outputOnly/radio/checkbox khi suy editable dau',
    GF.focusTagOfGrid({
      columns: [
        { tag: 'a', type: 'checkbox' }, { tag: 'b', type: 'radio' },
        { tag: 'c', type: 'outputOnly' }, { tag: 'd', type: 'text' }
      ]
    }) === 'd');

  check('H6.4 chi co cot khong goc duoc -> null; meta null/rong -> null',
    GF.focusTagOfGrid({
      columns: [
        { tag: 'a', type: 'readonly' }, { tag: 'b', type: 'outputOnly' },
        { tag: 'c', type: 'radio' }, { tag: 'd', type: 'checkbox' }
      ]
    }) === null && GF.focusTagOfGrid(null) === null &&
      GF.focusTagOfGrid({}) === null);

  // nextSelAfterDelete: selection bám _row_id, clamp cuối, bảng rỗng an toàn
  const rr = ids => ids.map(id => ({ _row_id: id }));
  check('H6.5 id dang chon con song -> giu nguyen',
    GF.nextSelAfterDelete(rr(['r1', 'r2', 'r3']), rr(['r1', 'r3']), 'r1') === 'r1');
  check('H6.6 xoa dong giua -> dong ke theo index cu',
    GF.nextSelAfterDelete(rr(['r1', 'r2', 'r3']), rr(['r1', 'r3']), 'r2') === 'r3');
  check('H6.7 xoa dong CUOI -> clamp ve dong truoc',
    GF.nextSelAfterDelete(rr(['r1', 'r2', 'r3']), rr(['r1', 'r2']), 'r3') === 'r2');
  check('H6.8 chua chon (null) -> dong cuoi truoc khi xoa',
    GF.nextSelAfterDelete(rr(['a', 'b', 'c']), rr(['a', 'b']), null) === 'b');
  check('H6.9 bang rong sau xoa -> null, khong exception',
    GF.nextSelAfterDelete(rr(['a']), [], 'a') === null);

  // --- DOM giả thủ công mô phỏng markup renderLoop ---------------------
  let __focusLog = [];
  const fakeDoc = { activeElement: null };
  global.document = fakeDoc;

  class FEl {
    constructor(tag, attrs, children) {
      this.tag = String(tag).toLowerCase();
      this.attrs = attrs || {};
      this.children = [];
      (children || []).forEach(c => this.append(c));
    }
    append(c) { this.children.push(c); return c; }
    getAttribute(k) {
      return Object.prototype.hasOwnProperty.call(this.attrs, k)
        ? this.attrs[k] : null;
    }
    classes() {
      return String(this.attrs['class'] || '').split(/\s+/).filter(Boolean);
    }
    focus() { fakeDoc.activeElement = this; __focusLog.push(this); }
    scrollIntoView() {}
    querySelector(sel) { return qsa(this, toks(sel))[0] || null; }
    querySelectorAll(sel) { return qsa(this, toks(sel)); }
  }
  function parseTok(tok) {
    const t = { tag: null, cls: [], attrs: [] };
    const m = tok.match(/^([a-zA-Z][\w-]*)/);
    if (m) { t.tag = m[1].toLowerCase(); tok = tok.slice(m[1].length); }
    let mm;
    const reCls = /\.([\w-]+)/g; // hoist regex: literal trong while sẽ lặp vô hạn
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
  function qsa(el, ts, ti, out) {
    ti = ti || 0; out = out || [];
    if (ti >= ts.length) return out; // hết chuỗi token: dừng đệ quy
    el.children.forEach(function (ch) {
      if (matchTok(ch, ts[ti])) {
        if (ti === ts.length - 1) out.push(ch);
        qsa(ch, ts, ti + 1, out);
      }
      qsa(ch, ts, ti, out);
    });
    return out;
  }
  function toks(sel) { return sel.trim().split(/\s+/).map(parseTok); }
  fakeDoc.querySelector = s => qsa(fakeDoc, toks(s))[0] || null;
  fakeDoc.querySelectorAll = s => qsa(fakeDoc, toks(s));

  function fld(tag, opts) {
    opts = opts || {};
    return new FEl('input', {
      type: 'text',
      'class': 'fld loop-fld' + (opts.vsic ? ' vsic-fld' : ''),
      'data-tag': tag,
      readonly: opts.readonly ? '' : null
    });
  }
  function trOf(rowId, inputs) {
    return new FEl('tr', { 'data-row-id': rowId, 'data-loop': 'L' },
      [new FEl('td', {}, inputs)]);
  }
  function tableOf(loop, trs) {
    return new FEl('table', { 'class': 'btable loop-table', 'data-loop': loop },
      [new FEl('tbody', {}, trs)]);
  }

  // add trên grid ngành: focus ô ma_nganh DÒNG MỚI (không nhầm ô readonly)
  fakeDoc.children = [tableOf('ds_nganh', [
    trOf('old', [fld('ten_nganh', { readonly: true }), fld('ma_nganh', { vsic: true })]),
    trOf('new', [fld('ten_nganh', { readonly: true }), fld('ma_nganh', { vsic: true })])
  ])];
  __focusLog = [];
  const okFocus = GF.focusGridRow('ds_nganh',
    { rowId: 'new', idx: 1, tag: GF.focusTagOfGrid(FD.GRID_META.ds_nganh) });
  check('H6.10 focusGridRow: focus dung o data-tag=ma_nganh tren row moi',
    okFocus === true && __focusLog.length === 1 &&
      __focusLog[0].getAttribute('data-tag') === 'ma_nganh');

  // grid không có ma_nganh: fallback input.loop-fld đầu dòng KHÔNG readonly
  fakeDoc.children = [tableOf('ds_tv', [
    trOf('x1', [fld('ho_ten'), fld('ghi_chu', { readonly: true })])
  ])];
  __focusLog = [];
  check('H6.11 focusGridRow fallback: input loop-fld dau tien KHONG readonly',
    GF.focusGridRow('ds_tv', { rowId: 'x1', idx: 0 }) === true &&
      __focusLog.length === 1 &&
      __focusLog[0].getAttribute('data-tag') === 'ho_ten');

  // bảng rỗng / bảng vắng mặt / idx lệch: trả false, KHÔNG exception
  fakeDoc.children = [tableOf('empty_loop', [])];
  let emptyThrew = null;
  let emptyRes = null;
  try {
    emptyRes = GF.focusGridRow('empty_loop', { idx: 99, tag: 'ma_nganh' });
  } catch (e) { emptyThrew = e; }
  check('H6.12 bang rong/idx le -> false, khong exception',
    emptyThrew === null && emptyRes === false);
  check('H6.13 bang khong ton tai trong DOM -> false, khong exception',
    GF.focusGridRow('missing_loop', {}) === false);

  delete global.document;
})();

// =====================================================================
// H7. ALLOWLIST ĐỘC LẬP - tự chạy git diff, tự lập danh sách từ ownership
// =====================================================================
//
// Danh sách auditor tự lập từ ownership check Giai đoạn 1
// (git log/diff baseline/p1.2-d882793..HEAD), KHÔNG đọc mảng ALLOW của test cũ:
//   A  (P1.1): app_web/ui/form-domain.js, app_web/ui/app.js,
//              app_web/test_m72_activation.js, docs/m72_activation_proposal.md
//   B  (P2.0): app_web/ui/form-domain.js, app_web/ui/app.js,
//              app_web/test_p20_hardening.js,
//              app_web/test_audit_p1_negative.js (chỉ sync ALLOW)
//   C  (docs): docs/p2_component_contracts.md, docs/p2_dependency_graph.md,
//              docs/legal_review_backlog.md
//   Lead      : PLAN.md (docs-only),
//               tools/census/build_layout_manifest.py,
//               app/data/layout_specs/layout_manifest.json,
//               app_web/test_audit_p1_negative.js (thêm path manifest)
//   L0 census: 6 file fragment md+evidence.json (merge L0-A/B/C)
//   Lead P1.2 (commit 5c75238): engine vung dieu kien {?flag}/{/flag} +
//               converter cond blocks + tagger idempotent M72 ->
//               tools/docx_render.py, tools/docx_to_blocks.py,
//               tools/tag_m72_sections.py, tools/audit_blocks_check.py,
//               tools/form_specs/change/PLI_M72.json,
//               app/templates/PLI_M72.docx, app/data/blocks/PLI_M72.json
//   Lane A P1.2: ui/render.js (condAllows + selectorHtml),
//               test_form_grid_meta.js, test_acceptance.js,
//               test_p12_m72_selector.js (test mới theo hợp đồng selector)
// File generated/doc dưới app/templates/ + app/data/ ĐƯỢC PHÉP duy nhất là:
//   - app/data/layout_specs/layout_manifest.json (Lead, commit 6047c1d)
//   - 6 fragment layout_specs (census L0-A/B/C)
//   - app/templates/PLI_M72.docx + app/data/blocks/PLI_M72.json
//     (Lead P1.2, commit 5c75238 - regen theo spec change PLI_M72)
(function h7() {
  const cp = require('child_process');
  const fs = require('fs');
  const path = require('path');
  let files = [];
  try {
    files = cp.execSync('git diff --name-only baseline/p1.2-d882793..HEAD',
      { cwd: path.join(__dirname, '..'), maxBuffer: 32 * 1024 * 1024 })
      .toString('utf8').split(/\r?\n/).filter(Boolean);
  } catch (e) {
    check('H7.0 chay duoc git diff baseline/p1.2-d882793..HEAD', false, String(e.message || e));
    return;
  }

  // R1 Lead (de55824+): allowlist tĩnh trong code gãy ở MỌI lần integrate mới
  // (mỗi commit hợp lệ đều làm EXPECTED lệch). Chuyển sang manifest dữ liệu
  // `tools/audit_expected_diff_files.txt` do Lead cập nhật CÓ CHỦ ĐÍCH tại
  // mỗi integrate; độ cứng giữ nguyên: exact-set equality + cấm entry "ma"
  // + templates giới hạn. Mọi file mới phải đi qua review rồi mới được thêm
  // vào manifest — không phải nới lỏng, chỉ tách dữ liệu khỏi code.
  const SELF = 'app_web/test_audit_wave_h_negative.js';
  const MANIFEST = 'tools/audit_expected_diff_files.txt';
  let expected;
  try {
    expected = fs.readFileSync(path.join(__dirname, '..', MANIFEST), 'utf8')
      .split(/\r?\n/)
      .map(l => l.replace(/#.*$/, '').trim())
      .filter(Boolean);
  } catch (e) {
    check('H7.0b doc duoc manifest ' + MANIFEST, false, String(e.message));
    return;
  }

  const rest = files.filter(f => f !== SELF);
  const genTouched = files.filter(f =>
    f.indexOf('app/templates/') === 0 || f.indexOf('app/data/') === 0);
  const expGen = expected.filter(f =>
    f.indexOf('app/templates/') === 0 || f.indexOf('app/data/') === 0);

  check('H7.1 moi file app/templates|app/data trong diff thuoc manifest',
    genTouched.every(f => expGen.indexOf(f) >= 0),
    JSON.stringify(genTouched.filter(f => expGen.indexOf(f) < 0)));

  check('H7.2 file thuoc app/templates trong diff chi la PLI_M72.docx (Lead P1.2)',
    files.every(f => f.indexOf('app/templates/') !== 0 ||
      f === 'app/templates/PLI_M72.docx'),
    JSON.stringify(files.filter(f =>
      f.indexOf('app/templates/') === 0 && f !== 'app/templates/PLI_M72.docx')));

  check('H7.3 manifest KHONG co entry "ma" (moi entry co mat trong diff)',
    expected.every(f => files.indexOf(f) >= 0 || f === SELF),
    JSON.stringify(expected.filter(f => files.indexOf(f) < 0 && f !== SELF)));

  check('H7.4 diff (tru file test nay) dung bang tap manifest (' +
      rest.length + ' file trong diff)',
    rest.length === expected.length &&
      expected.every(f => rest.indexOf(f) >= 0),
    JSON.stringify(rest.concat(expected)
      .filter(f => rest.indexOf(f) < 0 || expected.indexOf(f) < 0)));
})();

// ------------------------------------------------------------------ summary

console.log('-'.repeat(64));
console.log('test_audit_wave_h_negative: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
