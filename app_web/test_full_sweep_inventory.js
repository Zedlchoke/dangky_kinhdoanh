/*
 * test_full_sweep_inventory.js — chuẩn bị F2: full-sweep 28 use case × forms.
 *
 * Đọc inventory từ app/data/use_cases.json (nguồn chân lý thủ tục), render
 * MỖI form production bằng đúng harness DOM thuần đang có (renderBlocks từ
 * test_dom/test_runtime_tables — không jsdom), và assert trên CHUỖI HTML:
 *   S1. blocks + form_maps tồn tại cho mọi form trong inventory;
 *   S2. render ổn định: 2 lần render liên tiếp byte-identical;
 *   S3. console.error = 0 trong toàn bộ sweep (console.warn được ghi nhận
 *       riêng — degrade có chủ đích của contract hỏng);
 *   S4. không undefined / NaN / value="null" lọt vào HTML;
 *   S5. MỖI key blocks khai là input (run.input.key/chk) phải có control
 *       trong HTML: data-key="<key>"; key lạ đối chiếu form_maps.json được
 *       ghi chú INVENTORY-META (không thuộc registry của form);
 *   S6. section contracts: fixed-matrix phủ đủ ô nhập <sk>.<row>.<tag>,
 *       nested-grid/output-table có component tương ứng; output-table không
 *       có input nào;
 *   S7. inactive leakage: validateDocument trên store rỗng KHÔNG được sinh
 *       blocking error nào trỏ vào loop/section đang INACTIVE (activeWhen).
 *
 * Form nào FAIL → liệt kê cuối chạy, CHỜ LEAD (không tự sửa blocks/specs).
 * Viewport/a11y: harness hiện có là chuỗi-HTML thuần (không jsdom/layout
 * engine) — viewport thật và đo a11y tự động cần framework mới, NGOÀI phạm
 * vi lane này; NOTE thiết kế: nâng cấp lên jsdom/playwright + axe-core khi
 * Lead mở F2, tái sử dụng đúng danh sách key/section của file này.
 *
 * Run: node app_web/test_full_sweep_inventory.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');

const ROOT = path.join(__dirname, '..');

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}

const UC = readJson('app/data/use_cases.json');
const FORM_MAPS = readJson('app/data/form_maps.json');

/* ---------------------------------------------- inventory 28 use case */
const ucIds = UC.cases.map(c => c.id);
const formsByCase = {};
const allForms = new Set();
UC.cases.forEach(c => {
  const ids = (c.forms || []).map(f =>
    'PL' + f.pl + '_M' + String(f.mau).padStart(2, '0'));
  ((c.forms_oneOf || [])).forEach(g => (g.ids || []).forEach(id => ids.push(id)));
  formsByCase[c.id] = ids;
  ids.forEach(id => allForms.add(id));
});
const forms = Array.from(allForms).sort();

/* ------------------------------------------- console capture per form */
const realError = console.error;
const realWarn = console.warn;
function capture(fn) {
  const errs = [], warns = [];
  console.error = (...a) => errs.push(a.join(' '));
  console.warn = (...a) => warns.push(a.join(' '));
  try { return fn(); } finally { console.error = realError; console.warn = realWarn; }
}

/* --------------------------------------------- blocks walk: input keys */
function walkInputs(node, out) {
  if (!node || typeof node !== 'object') return out;
  if (Array.isArray(node)) { node.forEach(n => walkInputs(n, out)); return out; }
  const inp = node.input;
  if (inp && typeof inp === 'object') {
    if (typeof inp.key === 'string') out.keys.add(inp.key);
    if (inp.chk !== undefined && typeof inp.key === 'string') out.chks.add(inp.key);
  }
  Object.keys(node).forEach(k => {
    if (k !== 'input') walkInputs(node[k], out);
  });
  return out;
}

function loopTagsOf(blocks) {
  const tags = {};   // loop name -> [tag]
  (blocks || []).forEach(b => {
    if (b && b.t === 'loop' && b.loop) {
      tags[b.loop] = (b.cols || []).map(c => c && c.tag).filter(Boolean);
    }
  });
  return tags;
}

/* ----------------------------------------------------- kiểm 1 form */
function sweepForm(docId) {
  const res = { docId, fails: [], metas: [], consoleErrors: [], consoleWarns: 0 };
  const fail = (name, extra) =>
    res.fails.push(name + (extra ? ' [' + extra + ']' : ''));

  const blocksPath = path.join(ROOT, 'app', 'data', 'blocks', docId + '.json');
  if (!fs.existsSync(blocksPath)) {
    fail('S1 blocks tồn tại', 'app/data/blocks/' + docId + '.json');
    return res;
  }
  if (!FORM_MAPS[docId]) fail('S1 form_maps tồn tại', docId);
  const doc = JSON.parse(fs.readFileSync(blocksPath, 'utf8'));
  const store = R.newStore();

  function renderWith(st) {
    return capture(() =>
      R.renderBlocks(doc, st, {
        docId, fieldMeta: FD.FIELD_META,
        sectionContracts: FD.sectionContractsOf(docId),
        // cond blocks (P1.2) đọc opts.flags do caller tính từ selector
        flags: FD.selectorFlagsOf(docId, st)
      }));
  }

  /* Form có SELECTOR (P1.2 Option D, vd PLI_M72): key trong block `cond`
   * chỉ render khi flag đúng biến thể. Sweep theo biến thể:
   *  - render store rỗng (chưa chọn) + render TỪNG option;
   *  - key khai input phải có control trong TỔNG HỢP các biến thể;
   *  - key chỉ thuộc biến thể mà store rỗng KHÔNG được lọt (inactive leak).
   * Form không selector: một lần render store rỗng như cũ. */
  const sel = FD.getFormSelector(docId);
  const selOpts = sel ? (sel.options || []) : [];
  const perVariant = [{ label: null, html: renderWith(store) }];
  selOpts.forEach(o => {
    const st = R.newStore();
    st.values[sel.key] = o.value;
    perVariant.push({ label: o.value, html: renderWith(st) });
  });
  const html = perVariant[0].html;
  const unionHtml = perVariant.map(v => v.html).join('\n');

  // Render lần 2 (store rỗng): bắt console.error/warn thật + S2 bất biến.
  const errs2 = [];
  const realErr = console.error, realWrn = console.warn;
  console.error = (...a) => errs2.push(a.join(' '));
  console.warn = () => { res.consoleWarns++; };
  let html2 = '';
  try {
    html2 = R.renderBlocks(doc, store, {
      docId, fieldMeta: FD.FIELD_META,
      sectionContracts: FD.sectionContractsOf(docId),
      flags: FD.selectorFlagsOf(docId, store)
    });
  } finally { console.error = realErr; console.warn = realWrn; }
  res.consoleErrors = errs2;

  // S2 render ổn định
  if (html !== html2) fail('S2 render 2 lần không identical');

  // S3 console error
  if (res.consoleErrors.length) {
    fail('S3 console.error = ' + res.consoleErrors.length,
      res.consoleErrors[0].slice(0, 120));
  }

  // S4 undefined / NaN / value="null" (mọi biến thể)
  if (unionHtml.indexOf('undefined') >= 0) fail('S4 chuỗi "undefined" lọt HTML');
  if (/NaN/.test(unionHtml)) fail('S4 "NaN" lọt HTML');
  if (/value="null"/.test(unionHtml)) fail('S4 value="null" lọt HTML');

  // S5 mỗi key input khai trong blocks có control TRONG ÍT NHẤT MỘT biến thể
  // (form selector: key theo biến thể là INACTIVE khi chưa chọn — không phải
  // thiếu control) + đối chiếu form_maps/FIELD_META.
  const declared = walkInputs(doc.blocks, { keys: new Set(), chks: new Set() });
  const registry = new Set((FORM_MAPS[docId] && FORM_MAPS[docId].fields || [])
    .map(f => f && f.key).filter(Boolean));
  let gated = 0;
  declared.keys.forEach(k => {
    if (unionHtml.indexOf('data-key="' + k + '"') < 0) {
      fail('S5 key input thiếu control: ' + k);
    } else if (html.indexOf('data-key="' + k + '"') < 0) {
      gated++; // key chỉ xuất hiện khi chọn biến thể; chiều ngược lại phủ bởi S7
    }
    if (!registry.has(k) && !FD.getFieldMeta(k)) {
      res.metas.push(k);
    }
  });

  // S6 section contracts render đủ (đối chiếu trên TỔNG HỢP biến thể)
  FD.sectionContractsOf(docId).forEach(entry => {
    const spec = entry.spec || {};
    if (entry.kind === 'fixed-matrix') {
      (spec.fixed_rows || []).forEach(row => {
        if (row.output_only === true || row.outputOnly === true) return;
        (spec.columns || []).forEach(col => {
          if (!col || !col.tag) return;
          if (col.inputType === 'readonly' || col.computed) return;
          const k = spec.semantic_key + '.' + row.id + '.' + col.tag;
          if (unionHtml.indexOf('data-key="' + k + '"') < 0) {
            fail('S6 fixed-matrix thiếu ô: ' + k);
          }
        });
      });
    } else if (entry.kind === 'nested-grid') {
      if (unionHtml.indexOf('data-component="nested-grid"') < 0 &&
          unionHtml.indexOf('data-section-kind="nested-grid"') < 0) {
        fail('S6 nested-grid thiếu component: ' + spec.semantic_key);
      }
    } else if (entry.kind === 'output-table') {
      if (unionHtml.indexOf('data-component="output-table"') < 0 &&
          unionHtml.indexOf('data-section-kind="output-table"') < 0) {
        fail('S6 output-table thiếu component: ' + spec.semantic_key);
      }
      // output-table KHÔNG có input nào (O1: OUTPUT_ONLY) — mọi biến thể
      perVariant.forEach(v => (spec.columns || []).forEach(col => {
        if (col && col.tag &&
            v.html.indexOf('data-key="' + spec.semantic_key + '.' + col.tag) >= 0) {
          fail('S6 output-table có input (' + (v.label || 'rỗng') + '): ' +
            spec.semantic_key + '.' + col.tag);
        }
      }));
    }
  });

  // S7 inactive leakage: blocking error trên store rỗng phải trỏ vào phần ACTIVE
  const errs = FD.validateDocument(docId, doc.blocks, store, {});
  errs.filter(e => e.severity === 'blocking').forEach(e => {
    const key = String(e.key || '');
    if (key.indexOf('loop:') === 0) {
      const name = key.slice(5).split(':')[0];
      const gm = FD.getGridMeta({ docId, loop: name });
      if (gm && FD.activationModeOf(gm) === 'selector' &&
          !FD.isActiveGrid(gm, (store.loops || {})[name] || [], store)) {
        fail('S7 blocking leak vào grid inactive: ' + name + ' (' + e.code + ')');
      }
      const sec = FD.sectionContractForLoop(docId, name);
      if (sec && !FD.isActiveSection(sec, (store.loops || {})[name] || [], store)) {
        fail('S7 blocking leak vào section inactive: ' + name + ' (' + e.code + ')');
      }
    }
    const secBySk = FD.sectionContractsOf(docId).find(en =>
      (en.spec || {}).semantic_key === key);
    if (secBySk && !FD.isActiveSection(secBySk, [], store)) {
      fail('S7 blocking leak vào section inactive: ' + key + ' (' + e.code + ')');
    }
  });

  return res;
}

/* =============================================================== sweep */
const extraForms = Object.keys(FORM_MAPS).filter(id => !allForms.has(id)).sort();
const corpus = forms.concat(extraForms); // inventory trước, corpus extra sau

console.log('FULL-SWEEP INVENTORY (F2 prep) — ' + ucIds.length +
  ' use case -> ' + forms.length + ' form duy nhất; + ' + extraForms.length +
  ' form corpus ngoài inventory (form_maps 87) = ' + corpus.length + ' form');
console.log('');

const results = [];
let passedForms = 0;
const failLines = [];
corpus.forEach((docId, idx) => {
  const r = sweepForm(docId);
  r.inInventory = idx < forms.length;
  results.push(r);
  if (r.fails.length === 0) passedForms++;
  else {
    failLines.push((r.inInventory ? '[inventory] ' : '[corpus]    ') +
      docId + ' (' + r.fails.length + ' lỗi)');
  }
});

// In chi tiết CHỈ form fail (giữ output gọn).
results.filter(r => r.fails.length).forEach(r => {
  console.log('FAIL  ' + (r.inInventory ? '[inventory] ' : '[corpus]    ') +
    r.docId);
  r.fails.forEach(f => console.log('        - ' + f));
});

console.log('');
console.log('Render OK: ' + passedForms + '/' + corpus.length);
const totalConsole = results.reduce((s, r) => s + r.consoleErrors.length, 0);
console.log('console.error tổng: ' + totalConsole +
  '; console.warn tổng: ' + results.reduce((s, r) => s + r.consoleWarns, 0));
const metas = {};
results.forEach(r => r.metas.forEach(k => { (metas[k] = metas[k] || []).push(r.docId); }));
const metaKeys = Object.keys(metas);
console.log('INVENTORY-META (key input ngoài registry form_maps + FIELD_META, '
  + 'đối chiếu thủ công): ' + metaKeys.length);
metaKeys.forEach(k =>
  console.log('  - ' + k + '  @ ' + metas[k].slice(0, 5).join(',')));
const failedForms = results.filter(r => r.fails.length);
if (failedForms.length) {
  console.log('');
  console.log('Danh sách form FAIL chờ Lead:');
  failLines.forEach(l => console.log('  ' + l));
}
console.log('-'.repeat(64));
console.log('test_full_sweep_inventory: ' + passedForms + '/' + corpus.length +
  ' form sạch; ' + (failedForms.length) + ' form cần Lead');
process.exit(failedForms.length ? 1 : 0);
