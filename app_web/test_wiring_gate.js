/* test_wiring_gate.js — P2 WIRING GATE (Lane B3, QA/contract/audit tooling).
 *
 * Mục đích: GATE ĐỘC LẬP bắt integration của runtime P2 với 3 component mới
 * `fixed-matrix` / `nested-grid` / `output-table`. Gate này KHÔNG phụ thuộc
 * artifact generated (không đọc app/data): mọi fixture được viết inline theo
 * SHAPE CONTRACT đã khóa trong docs/p2_component_contracts.md (mục 2.2 / 3.2 /
 * 4.2) và fixture candidates docs/p2_fixture_candidates.md (F2 / N1 / O1).
 *
 * Gate gồm 5 nhóm mệnh đề:
 *   [S] self-check harness: fixture phải tuân schema contract qua CHÍNH module
 *       thuần (require('./ui/*.js')). Nhóm này PHẢI xanh — nếu đỏ thì lỗi nằm ở
 *       harness/fixture, không kết luận gì về runtime.
 *   [A] plumbing tĩnh: app_web/ui/index.html phải NẠP được script của cả 3
 *       module và script đó phải sống sót trong môi trường browser-thật
 *       (sandbox vm KHÔNG có module/exports/require).
 *   [B] dispatcher render: render runtime (cùng entry mà app.js dùng:
 *       Render.renderBlocks) phải sinh đúng marker DOM đặc trưng của từng kind.
 *   [C] draft round-trip: `_row_id` ổn định qua migrateDraft/ensureIds, dữ liệu
 *       phẳng của kind mới không bị mất khi upgrade v1 -> v2.
 *   [D] validation: lỗi của kind mới phải mount ĐÚNG channel FormDomain
 *       (validateDocument/validateDossier) với shape contract
 *       {key, docId, code, message, severity}.
 *
 * Chạy: node app_web/test_wiring_gate.js  (từ root repo, clone bất kỳ).
 *
 * Kỳ vọng tại HEAD ngày 2026-08-27: gate ĐANG ĐỎ CÓ KIỂM SOÁT vì runtime chưa
 * wire 3 module (0 reference trong ui/*). FAIL MESSAGE luôn in đủ
 * "EXPECT / ACTUAL / HÌNH NHƯ CẦN" để hành động hóa. Khi Lane B1 wire xong,
 * gate phải tự chuyển xanh mà KHÔNG cần sửa gì file này.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const UI_DIR = path.join(__dirname, 'ui');
const INDEX_HTML_PATH = path.join(UI_DIR, 'index.html');

const R = require('./ui/render.js');            // window.Render trong browser
const FD = require('./ui/form-domain.js');      // window.FormDomain
const App = require('./ui/app.js');             // Helpers (GridCtl, ...)
const FixedMatrix = require('./ui/fixed-matrix.js');
const NestedGrid = require('./ui/nested-grid.js');
const OutputTable = require('./ui/output-table.js');

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const RESULTS = [];
let passed = 0;
let failed = 0;

function record(name, pass, expect, actual, fix) {
  const item = {
    name: name,
    pass: !!pass,
    expect: expect || '',
    actual: actual === undefined || actual === null ? '(none)' : String(actual),
    fix: fix || ''
  };
  RESULTS.push(item);
  if (item.pass) passed++;
  else failed++;
  console.log((item.pass ? 'PASS  ' : 'FAIL  ') + name +
    (item.pass ? '' : '\n        EXPECT : ' + item.expect +
      '\n        ACTUAL : ' + item.actual +
      (item.fix ? '\n        HÌNH NHƯ CẦN: ' + item.fix : '')));
}

/* Mọi mệnh đề bọc trong safe(): nếu harness/runtime ném exception thì đó là 1
 * mệnh đề đỏ CÓ THÔNG BÁO, không làm chết cả suite. */
function safe(name, fn) {
  try {
    const r = fn();
    record(name, r.pass, r.expect, r.actual, r.fix);
  } catch (e) {
    record(name, false,
      'harness chạy tới hết mệnh đề mà không ném exception',
      (e && e.name ? e.name + ': ' : '') + (e && e.message ? e.message : String(e)),
      'nếu exception đến từ fixture trong file test này thì sửa TEST; nếu đến từ ' +
      'runtime khi gọi API chuẩn (Render/FormDomain/GridCtl) thì đó là bug thật ' +
      'cần report cho lane sở hữu — không váProductionCode từ gate.');
  }
}

// ---------------------------------------------------------------------------
// FIXTURE INLINE — viết từ SHAPE CONTRACT (docs/p2_component_contracts.md),
// KHÔNG đọc artifact generated.
// ---------------------------------------------------------------------------

/* F2 — PLI_M03 nguồn vốn điều lệ (contract mục 2.2). */
const FM_SPEC = {
  form_id: 'PLI_M03',
  kind: 'fixed-matrix',
  section_id: 'nguon_von_dieule',
  semantic_key: 'nguon_von_dieu_le',
  stt: { mode: 'none' },
  fixed_rows: [
    { id: 'von_nsnn', label: 'Vốn ngân sách nhà nước' },
    { id: 'von_tu_nhan', label: 'Vốn tư nhân' },
    { id: 'von_nuoc_ngoai', label: 'Vốn nước ngoài' },
    { id: 'von_khac', label: 'Loại nguồn vốn khác',
      detail_required_when_filled: true },
    { id: 'tong_cong', label: 'Tổng cộng', output_only: true }
  ],
  columns: [
    { tag: 'loai_nguon_von', inputType: 'readonly' },
    { tag: 'so_tien_vnd_va_tuong_duong', inputType: 'money' },
    { tag: 'ty_le', inputType: 'percent', computed: true }
  ],
  totals: [
    { id: 'tong_cong', formula: 'sum(so_tien_vnd_va_tuong_duong)',
      target: 'outputOnly', target_tag: 'so_tien_vnd_va_tuong_duong' }
  ],
  active_when: []
};

/* Draft phẳng theo contract mục 2.4: values["<semantic_key>.<row>.<tag>"]. */
const FLAT_KEY_TN =
  'nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong';
const FLAT_KEY_KHAC =
  'nguon_von_dieu_le.von_khac.so_tien_vnd_va_tuong_duong';
const FM_DRAFT_OK = {
  values: {},
  checks: {},
  loops: {}
};
FM_DRAFT_OK.values[FLAT_KEY_TN] = '60.000.000';
FM_DRAFT_OK.values[FLAT_KEY_KHAC] = '40.000.000';
const FM_TOTAL_OK_VND = 100000000;          // tổng suy ra từ formula

/* Vi phạm để kiểm validation channel. */
const FM_DRAFT_BAD = {
  values: {},
  checks: {},
  loops: {}
};
FM_DRAFT_BAD.values[FLAT_KEY_TN] = 'not-money';
FM_DRAFT_BAD.values['nguon_von_dieu_le.von_khac.ty_le'] = '150'; // > 100%

/* N1-lite — PLI_M02 người đại diện phần vốn góp / người ủy quyền
 * (contract mục 3.2: header_rows + columns col_index + discriminator +
 * row_groups). 4 cột vật lý: STT | tên | VNĐ | tỷ lệ %. */
const NG_LOOP = 'ds_nddpl_uy_quyen_chu_so_huu';
const NG_SPEC = {
  form_id: 'PLI_M02',
  kind: 'nested-grid',
  section_id: 'nddpl_uy_quyen_chu_so_huu',
  loop: NG_LOOP,
  semantic_key: NG_LOOP,
  header_rows: [
    [{ text: 'STT', rowspan: 2 },
     { text: 'Tên người đại diện phần vốn góp', rowspan: 2 },
     { text: 'Phần vốn góp', colspan: 2 }],
    [{ text: 'VNĐ' }, { text: 'Tỷ lệ %' }]
  ],
  columns: [
    { tag: 'stt', col_index: 0, inputType: 'outputOnly' },
    { tag: 'ho_ten', col_index: 1, required: true },
    { tag: 'so_tien_vnd_va_tuong_duong', col_index: 2 },
    { tag: 'ty_le', col_index: 3 }
  ],
  discriminator: { tag: 'loai_dong', values: ['ndd_pl', 'ndd_uy_quyen'] },
  row_groups: [
    { group_id: 'ca_nhan', match: 'gtinh!=null', required_columns: ['so_cccd'] },
    { group_id: 'to_chuc', match: 'ten_to_chuc!=null',
      required_columns: ['ma_so_thue'] }
  ],
  min_rows: 0,
  max_rows: null
};

const NG_ROW_ID_1 = 'rG1_ax17qk';
const NG_ROW_ID_2 = 'rU2_by93md';
const NG_ROWS_OK = [
  { _row_id: NG_ROW_ID_1, loai_dong: 'ndd_pl', gtinh: 'Nam',
    ho_ten: 'NGUYEN VAN A',
    so_tien_vnd_va_tuong_duong: '500.000.000', ty_le: '50' },
  { _row_id: NG_ROW_ID_2, loai_dong: 'ndd_uy_quyen', ten_to_chuc: 'CONG TY B',
    ty_le: '50' }
];
const NG_PHYSICAL_COLS = 4;

/* Vi phạm validation cho nested-grid: thiếu field bắt buộc theo nhóm +
 * giá trị discriminator ngoài contract. */
const NG_ROWS_MISSING_REQUIRED = [
  { _row_id: NG_ROW_ID_1, loai_dong: 'ndd_pl', gtinh: 'Nam' }
];
const NG_ROWS_BAD_DISCRIMINATOR = [
  { _row_id: 'rX9_oop21z', loai_dong: 'vai_tro_khac', ho_ten: 'NGUYEN VAN C' }
];

/* O1 — PLI_M70 chữ ký người nộp/người nhận (contract mục 4.2). */
const OT_SPEC = {
  form_id: 'PLI_M70',
  kind: 'output-table',
  section_id: 'chu_ky_nguoi_nop_nguoi_nhan',
  semantic_key: 'chu_ky_tiep_nhan_ho_so',
  grid: { rows: 2, cols: 1,
    labels: ['NGƯỜI NỘP HỒ SƠ', 'NGƯỜI NHẬN HỒ SƠ'] },
  inputs: [],
  active_when: [],
  notes: 'Giữ grid khi xuất DOCX dù không nhập liệu (PLAN mục G)'
};

// ---------------------------------------------------------------------------
// [S] SELF-CHECK: fixture phải khớp contract qua chính module thuần.
// Nếu nhóm này đỏ thì harness sai — các nhóm sau KHÔNG dùng để kết luận.
// ---------------------------------------------------------------------------

console.log('\n== [S] self-check harness (fixture theo shape contract) ==');

safe('S1. module thuần fixed-matrix/nested-grid/output-table expose đúng API '
  + 'gate dùng', () => {
    const need = [
      ['recompute', typeof FixedMatrix.recompute],
      ['setCell', typeof FixedMatrix.setCell],
      ['validate', typeof FixedMatrix.validate]
    ];
    const needNg = [
      ['validateContract', typeof NestedGrid.validateContract],
      ['headerLayout', typeof NestedGrid.headerLayout],
      ['validate', typeof NestedGrid.validate]
    ];
    const needOt = [['renderOutputTable', typeof OutputTable.renderOutputTable]];
    const missing = [].concat(
      need.filter(x => x[1] !== 'function'),
      needNg.filter(x => x[1] !== 'function'),
      needOt.filter(x => x[1] !== 'function')
    ).map(x => x[0] + '=' + x[1]);
    return {
      pass: missing.length === 0,
      expect: 'mọi API listed là function',
      actual: missing.length ? 'missing: ' + missing.join(', ')
        : 'API đầy đủ trên cả 3 module',
      fix: 'API thuần đổi tên/không còn export -> cập nhật contract ' +
        'docs/p2_component_contracts.md TRƯỚC rồi mới đổi gate.'
    };
  });

safe('S2. fixture NG_SPEC hợp lệ theo validateContract (schema v1 khóa)', () => {
  const errs = NestedGrid.validateContract(NG_SPEC);
  return {
    pass: errs.length === 0,
    expect: 'validateContract(NG_SPEC) = [] (fixture đúng contract)',
    actual: errs.length ? JSON.stringify(errs.map(e => e.code + ':' + e.path))
      : '[] — fixture nested-grid hợp lệ',
    fix: 'fixture trong test_wiring_gate.js lệch schema contract — SỬA TEST, '
      + 'không đụng runtime.'
  };
});

safe('S3. fixture NG_SPEC headerLayout phủ kín 4 cột vật lý x 2 hàng header',
  () => {
    const layout = NestedGrid.headerLayout(NG_SPEC);
    const errs = layout.errors || [];
    const nRows = (layout.rows || []).length;
    return {
      pass: errs.length === 0 && nRows === 2 &&
        NestedGrid.physicalColumns(NG_SPEC).columns.length === NG_PHYSICAL_COLS,
      expect: 'errors=[] , rows=2, physicalColumns=' + NG_PHYSICAL_COLS,
      actual: 'errors=' + JSON.stringify(errs.map(e => e.code)) +
        ', rows=' + nRows + ', cols=' +
        NestedGrid.physicalColumns(NG_SPEC).columns.length,
      fix: 'fixture header_rows/columns lệch nhau — SỬA TEST.'
    };
  });

safe('S4. fixture FM_SPEC: recompute tổng = ' + FM_TOTAL_OK_VND +
  ', không ghi đè ngược draft', () => {
    const draft = clone(FM_DRAFT_OK);
    const before = JSON.stringify(draft);
    const matrix = FixedMatrix.recompute(FM_SPEC, draft);
    const row = (matrix.rows || []).filter(r => r.id === 'tong_cong')[0];
    const got = row && row.cells.so_tien_vnd_va_tuong_duong;
    return {
      pass: got === FM_TOTAL_OK_VND && JSON.stringify(draft) === before &&
        matrix.semantic_key === 'nguon_von_dieu_le',
      expect: 'tong_cong.so_tien=' + FM_TOTAL_OK_VND + ' (projection), draft '
        + 'nguyên vẹn sau recompute, semantic_key đúng',
      actual: 'total=' + JSON.stringify(got) +
        ', draftMutated=' + (JSON.stringify(draft) !== before) +
        ', semanticKey=' + matrix.semantic_key,
      fix: 'fixture/formula lệch — SỬA TEST.'
    };
  });

safe('S5. fixture OT_SPEC: renderOutputTable thuần cho lưới 2x1, 0 input',
  () => {
    const html = OutputTable.renderOutputTable(OT_SPEC, FM_DRAFT_OK);
    const nTr = (html.match(/<tr\b/g) || []).length;
    const nInput = (html.match(/<input\b/g) || []).length;
    return {
      pass: html.indexOf('<table') >= 0 && nTr === 2 && nInput === 0 &&
        html.indexOf('NGƯỜI NỘP HỒ SƠ') >= 0,
      expect: 'html có <table>, 2 <tr>, 0 <input>, giữ nhãn NGƯỜI NỘP HỒ SƠ',
      actual: 'len=' + html.length + ', tr=' + nTr + ', input=' + nInput,
      fix: 'fixture/spec output-table lệch contract — SỬA TEST.'
    };
  });

// ---------------------------------------------------------------------------
// Helpers đọc index.html + sandbox browser
// ---------------------------------------------------------------------------

function readIndexHtml() {
  return fs.readFileSync(INDEX_HTML_PATH, 'utf8');
}

function parseScripts(html) {
  const out = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const attrs = m[1] || '';
    const srcMatch = attrs.match(/src\s*=\s*["']([^"']+)["']/i);
    out.push({
      src: srcMatch ? srcMatch[1] : null,
      raw: srcMatch ? srcMatch[1] : '',
      /* <script type="module"> là cách nạp hợp lệ khác trong browser (ESM có
       * scope riêng, không rò CommonJS) — A2 chấp nhận nhánh này. */
      typeModule: /(^|\s)type\s*=\s*["']module["']/i.test(attrs),
      inline: m[2] || ''
    });
  }
  return out;
}

function baseName(p) {
  return String(p || '').split('?')[0].split('#')[0].split('/').pop();
}

/* Sandbox browser-thật: KHÔNG có module/exports/require — y như trang web mở
 * bằng trình duyệt. Trả {ok, index, errorName, errorMessage}.
 * [Lead sync 2026-08-27] Browser THẬT có window === globalThis: inline script
 * gán window.module thì bare identifier `module` trong script kế tiếp phải
 * thấy được. Bản cũ contextify một object riêng khiến `window.module` nằm ở
 * thế giới khác với global host -> mọi shim đúng semantics đều báo lỗi ảo.
 * Sửa harness cho MÔ PHỎNG ĐÚNG trình duyệt, không hạ chuẩn mệnh đề nào. */
function evalInBrowser(scriptTexts) {
  const noop = function () {};
  const G = {
    document: {
      addEventListener: noop,
      removeEventListener: noop,
      querySelector: function () { return null; },
      querySelectorAll: function () { return []; },
      createElement: function () {
        return { style: {}, setAttribute: noop, appendChild: noop };
      },
      body: { appendChild: noop },
      documentElement: { style: {} }
    },
    location: { search: '', href: 'http://localhost/ui/index.html' },
    navigator: { userAgent: 'qa-wiring-gate' },
    console: { log: noop, debug: noop, info: noop, warn: noop, error: noop },
    setTimeout: function () { return 0; },
    clearTimeout: noop,
    setInterval: function () { return 0; },
    clearInterval: noop,
    requestAnimationFrame: noop,
    URLSearchParams: URLSearchParams,
    fetch: function () { return Promise.resolve({ json: function () {
      return Promise.resolve([]); }, text: function () { return ''; },
      ok: true }); }
  };
  G.window = G;
  G.self = G;
  G.globalThis = G;
  let ctx;
  try {
    ctx = vm.createContext(G);
  } catch (e) {
    return { ok: false, errorName: 'HarnessError', errorMessage: e.message };
  }
  for (let i = 0; i < scriptTexts.length; i++) {
    try {
      vm.runInContext(String(scriptTexts[i]) + '\n;void 0;', ctx,
        { filename: 'qa_wiring_gate_browser_' + (i + 1) });
    } catch (e) {
      return {
        ok: false, index: i,
        errorName: (e && e.name) ? e.name : 'Error',
        errorMessage: (e && e.message) ? e.message : String(e)
      };
    }
  }
  return { ok: true };
}

// ---------------------------------------------------------------------------
// [A] PLUMBING TĨNH: index.html phải nạp được cả 3 module
// ---------------------------------------------------------------------------

console.log('\n== [A] static scan: app_web/ui/index.html nạp module P2 ==');

const MODULE_FILES = ['fixed-matrix.js', 'nested-grid.js', 'output-table.js'];

safe('A0. index.html đọc được từ app_web/ui/ (path tương đối __dirname)', () => ({
  pass: readIndexHtml().indexOf('<!DOCTYPE html>') === 0 ||
    readIndexHtml().indexOf('<html') >= 0,
  expect: 'index.html tồn tại trong worktree',
  actual: 'bytes=' + readIndexHtml().length,
  fix: 'SỬA TEST nếu đường dẫn UI_DIR sai.'
}));

MODULE_FILES.forEach(function (file) {
  const name = file.replace(/\.js$/, '');
  safe('A1.' + file + ': index.html khai báo <script> nạp module này', () => {
    const html = readIndexHtml();
    const loaded = parseScripts(html)
      .some(function (s) { return baseName(s.src) === file; });
    return {
      pass: loaded,
      expect: 'index.html chứa <script src="' + file + '"> (hoặc bundle/loader '
        + 'được nạp trước app.js)',
      actual: 'thẻ script hiện có: ' +
        parseScripts(html).map(function (s) { return s.src || '(inline)'; })
          .join(', '),
      fix: 'thêm <script src="' + file + '"></script> vào app_web/ui/index.html '
        + 'TRƯỚC <script src="render.js">/app.js (Lane B1 sở hữu index.html).'
    };
  });
});

MODULE_FILES.forEach(function (file) {
  safe('A2.' + file + ': script sống sót trong sandbox browser (không CommonJS)',
    () => {
      const html = readIndexHtml();
      const source = fs.readFileSync(path.join(UI_DIR, file), 'utf8');
      const scripts = parseScripts(html);
      let entry = null;
      scripts.forEach(function (s) {
        if (!s.src && !entry) return;
        if (baseName(s.src) === file) entry = s;
      });
      /* Nhánh 0: nạp kiểu ES module — browser tự xử lý scope, không rò
       * CommonJS, không cần UMD guard. */
      if (entry && entry.typeModule) {
        return {
          pass: true,
          expect: 'script chạy được trong browser thật (UMD / shim / ESM)',
          actual: 'nạp qua <script type="module"> (ESM scope riêng)'
        };
      }
      const standalone = evalInBrowser([source]);
      if (standalone.ok) {
        return {
          pass: true,
          expect: 'eval không ném trong ngữ cảnh chỉ có window/document',
          actual: 'browser-safe (UMD/self-contained)'
        };
      }
      /* Ngã tải thứ hai được chấp nhận: index.html khai báo shim/bootstrap
       * (module/exports/require/define) TRƯỚC thẻ script của module. */
      let idx = -1;
      for (let i = 0; i < scripts.length; i++) {
        if (baseName(scripts[i].src) === file) { idx = i; break; }
      }
      const earlierInline = idx > 0
        ? scripts.slice(0, idx).filter(function (s) { return !s.src; })
          .map(function (s) { return s.inline; })
        : [];
      const hasShim = earlierInline.some(function (t) {
        return /\b(module|exports|require|define)\b/.test(t);
      });
      if (hasShim) {
        const seq = evalInBrowser(earlierInline.concat([source]));
        if (seq.ok) {
          return { pass: true, expect: '-', actual: 'qua loader shim inline' };
        }
        return {
          pass: false,
          expect: 'toàn bộ chuỗi script index.html (shim + ' + file +
            ') eval sạch trong browser sandbox',
          actual: 'throw tại đoạn nạp module: ' + seq.errorName + ': ' +
            seq.errorMessage,
          fix: 'shim inline chưa đủ/nạp sai thứ tự — shim phải chạy TRƯỚC và '
            + 'publish module lên window (vd window.FixedMatrix = …).'
        };
      }
      return {
        pass: false,
        expect: file + ' chạy được khi trình duyệt không có module/exports/' +
          'require (UMD guard giống render.js/output-table.js), HOẶC index.html '
          + 'có shim CommonJS khai báo trước, HOẶC nạp qua type="module"',
        actual: 'throw ' + standalone.errorName + ': ' + standalone.errorMessage +
          '; index.html không có shim inline nào đứng trước',
        fix: 'bọc UMD guard trong ' + file + ' (Lane sở hữu module) HOẶC thêm '
          + 'bootstrap loader inline TRƯỚC thẻ <script src="' + file + '"> trong '
          + 'app_web/ui/index.html.'
      };
    });
});

safe('A3. toàn bộ chuỗi <script> của index.html eval sạch trong browser sandbox',
  () => {
    const html = readIndexHtml();
    const scripts = parseScripts(html);
    const texts = [];
    const labels = [];
    scripts.forEach(function (s) {
      if (s.src) {
        const p = path.join(UI_DIR, baseName(s.src));
        if (!fs.existsSync(p)) {
          texts.push(null);
          labels.push(baseName(s.src) + ' (FILE KHÔNG TỒN TẠI)');
          return;
        }
        if (s.typeModule) {
          labels.push(baseName(s.src) + ' (type=module — khỏi eval cổ điển)');
          return;
        }
        texts.push(fs.readFileSync(p, 'utf8'));
        labels.push(baseName(s.src));
      } else {
        texts.push(s.inline);
        labels.push('(inline)');
      }
    });
    const run = evalInBrowser(texts.filter(function (t) { return t !== null; }));
    return {
      pass: run.ok,
      expect: 'chuỗi script đúng thứ tự khai báo eval không ném exception nào',
      actual: run.ok ? '(' + labels.length + ' script đều OK)' :
        ('throw ở script #' + ((run.index || 0) + 1) + ' [' +
          (labels[run.index] || '?') + '] : ' + run.errorName + ': ' +
          run.errorMessage + ' — danh sách script: ' + labels.join(', ')),
      fix: 'script bị ném lỗi sẽ giết TOÀN BỘ init trang (init không chạy). '
        + 'Nếu lỗi đến từ một module P2 chưa UMD-guard, xem A2.'
    };
  });

// ---------------------------------------------------------------------------
// [B] DISPATCHER RENDER: kind mới phải sinh marker DOM đặc trưng
// ---------------------------------------------------------------------------

/* Transport候选: mỗi transport là một cách HỢP LỆ để đưa (section, spec) vào
 * renderer runtime. PASS theo mỗi kind yêu cầu ÍT NHẤT một transport sinh đủ
 * marker. Fail message liệt kê từng transport + kết quả để lần ra chỗ wire.
 *
 * [Lead sync 2026-08-27] Kiến trúc đã merge dùng opts.sectionContracts:
 * entry từ registry FormDomain (app.js truyền FD.sectionContractsOf(docId)).
 * Gate thêm transport này vào danh sách probe — fixture blocks vẫn tự dựng
 * inline (anchor override trỏ về text của chính fixture), KHÔNG đọc artifact
 * generated; marker assertions giữ nguyên 100%. */

function qaRegistryEntry(docId, sectionId, anchorText) {
  const e = FD.getSectionContract(docId, sectionId);
  if (!e) {
    throw new Error('FORM_TABLE_CONTRACTS thiếu ' + docId + '/' + sectionId);
  }
  const entry = clone(e);
  entry.anchor = { match: anchorText };
  return entry;
}

function transportsFor(kind) {
  const mk = function (label, fn) { return { label: label, run: fn }; };
  const reg = function (docId, sectionId, anchorText, docBlocks, store,
    extraOpts) {
    return mk('opts.sectionContracts (production registry: ' + docId +
      '/' + sectionId + ')', function () {
      return R.renderBlocks(
        { id: docId, ten_mau: 'qa', blocks: clone(docBlocks) }, store,
        Object.assign({ docId: docId,
          sectionContracts: [qaRegistryEntry(docId, sectionId, anchorText)] },
          extraOpts || {}));
    });
  };
  switch (kind) {
    case 'fixed-matrix':
      return [
        mk('block.t = "fixed-matrix"', function () {
          return R.renderBlocks({
            id: 'QA_FM', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'fixed-matrix' }, clone(FM_SPEC))]
          }, cloneStoreOf(FM_DRAFT_OK));
        }),
        mk('block.t="table" + block.kind="fixed-matrix"', function () {
          return R.renderBlocks({
            id: 'QA_FM2', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'table', rows: [] }, clone(FM_SPEC))]
          }, cloneStoreOf(FM_DRAFT_OK));
        }),
        mk('opts.sectionSpecs theo section_id', function () {
          const o = {};
          o[FM_SPEC.section_id] = clone(FM_SPEC);
          return R.renderBlocks({
            id: 'QA_FM3', ten_mau: 'qa', blocks: [
              { t: 'table', rows: [], section_id: FM_SPEC.section_id,
                kind: 'fixed-matrix' }]
          }, cloneStoreOf(FM_DRAFT_OK), { sectionSpecs: o });
        }),
        reg('PLI_M03', FM_SPEC.section_id, 'NGUỒN VỐN ĐIỀU LỆ',
          [{ t: 'p', runs: [{ text: 'NGUỒN VỐN ĐIỀU LỆ' }] }],
          cloneStoreOf(FM_DRAFT_OK))
      ];
    case 'nested-grid':
      return [
        mk('block.t = "nested-grid"', function () {
          return R.renderBlocks({
            id: 'QA_NG', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'nested-grid' }, clone(NG_SPEC))]
          }, ngStore(NG_ROWS_OK));
        }),
        mk('block.t="loop" + block.kind="nested-grid"', function () {
          return R.renderBlocks({
            id: 'QA_NG2', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'loop', loop: NG_LOOP, headerRows: [],
                rows: [], cols: [] }, clone(NG_SPEC))]
          }, ngStore(NG_ROWS_OK));
        }),
        mk('opts.sectionSpecs theo section_id', function () {
          const o = {};
          o[NG_SPEC.section_id] = clone(NG_SPEC);
          return R.renderBlocks({
            id: 'QA_NG3', ten_mau: 'qa', blocks: [
              { t: 'loop', loop: NG_LOOP, headerRows: [], rows: [], cols: [],
                section_id: NG_SPEC.section_id, kind: 'nested-grid' }]
          }, ngStore(NG_ROWS_OK), { sectionSpecs: o });
        }),
        reg('PLI_M02', NG_SPEC.section_id,
          'DANH SÁCH NGƯỜI ĐẠI DIỆN PHẦN VỐN GÓP / NGƯỜI ỦY QUYỆN',
          [{ t: 'p', runs: [{ text: 'DANH SÁCH NGƯỜI ĐẠI DIỆN PHẦN VỐN GÓP / '
            + 'NGƯỜI ỦY QUYỆN' }] }],
          ngStore(NG_ROWS_OK))
      ];
    case 'output-table':
      return [
        mk('block.t = "output-table"', function () {
          return R.renderBlocks({
            id: 'QA_OT', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'output-table' }, clone(OT_SPEC))]
          }, R.newStore());
        }),
        mk('block.t="table" + block.kind="output-table"', function () {
          return R.renderBlocks({
            id: 'QA_OT2', ten_mau: 'qa', blocks: [
              Object.assign({ t: 'table', rows: [] }, clone(OT_SPEC))]
          }, R.newStore());
        }),
        mk('opts.sectionSpecs theo section_id', function () {
          const o = {};
          o[OT_SPEC.section_id] = clone(OT_SPEC);
          return R.renderBlocks({
            id: 'QA_OT3', ten_mau: 'qa', blocks: [
              { t: 'table', rows: [], section_id: OT_SPEC.section_id,
                kind: 'output-table' }]
          }, R.newStore(), { sectionSpecs: o });
        }),
        reg('PLI_M70', OT_SPEC.section_id, 'GIẤY TIẾP NHẬN HỒ SƠ',
          [{ t: 'p', runs: [{ text: 'GIẤY TIẾP NHẬN HỒ SƠ' }] }],
          R.newStore())
      ];
    default:
      return [];
  }
}

function clone(v) { return JSON.parse(JSON.stringify(v)); }

function cloneStoreOf(draftFlat) {
  const st = R.newStore();
  Object.keys(draftFlat.values || {}).forEach(function (k) {
    st.values[k] = draftFlat.values[k];
  });
  return st;
}

function ngStore(rows) {
  const st = R.newStore();
  st.loops[NG_LOOP] = clone(rows || []);
  return st;
}

/* Chạy an toàn từng transport; trả {ok, html, err}. */
function runTransport(tr) {
  try {
    const html = tr.run();
    return { ok: true, html: typeof html === 'string' ? html : String(html) };
  } catch (e) {
    return {
      ok: false, html: '',
      err: (e && e.name ? e.name + ': ' : '') + (e && e.message ? e.message : '')
    };
  }
}

function bestTransport(kind) {
  const markers = MARKERS[kind];
  let best = null;
  transportsFor(kind).forEach(function (tr) {
    const run = runTransport(tr);
    /* HTML rỗng / không đáng tin = không mệnh đề nào được tính đạt: tránh
     * "PASS giả tạo" cho các marker kiểu phủ định (vd "không có nút xóa"). */
    const meaningful = run.ok && String(run.html).trim() !== '';
    const hits = meaningful ? markers.filter(function (m) {
      try { return !!m.test(run.html); } catch (e) { return false; }
    }).length : -1;
    if (!best || hits > best.hit) {
      best = {
        transport: tr, run: run, hit: hits,
        satisfied: meaningful ? markers.filter(function (m) {
          try { return !!m.test(run.html); } catch (e) { return false; }
        }) : []
      };
    }
  });
  return best;
}

/* Marker DOM đặc trưng từng kind — suy trực tiếp từ contract mục 2.3/3.3/4.3. */
const MARKERS = {
  'fixed-matrix': [
    { id: 'fm-flat-key',
      desc: 'ô nhập tiền mang flat key "' + FLAT_KEY_TN + '"',
      test: function (h) { return h.indexOf(FLAT_KEY_TN) >= 0; } },
    { id: 'fm-value-reflected',
      desc: 'giá trị người dùng phản chiếu vào ô (value="60.000.000")',
      test: function (h) { return h.indexOf('60.000.000') >= 0; } },
    { id: 'fm-blank-legal-rows',
      desc: 'dòng pháp lý vẫn render dù trống (Vốn ngân sách nhà nước / '
        + 'Vốn tư nhân / Vốn nước ngoài)',
      test: function (h) {
        return h.indexOf('Vốn ngân sách nhà nước') >= 0 &&
          h.indexOf('Vốn tư nhân') >= 0 &&
          h.indexOf('Vốn nước ngoài') >= 0; } },
    { id: 'fm-no-row-op',
      desc: 'KHÔNG nút thao tác dòng (data-act=add/del/clear/dup/up/down) '
        + 'trong ma trận cố định',
      test: function (h) { return !/data-act="/.test(h); } },
    { id: 'fm-total-readonly-computed',
      desc: 'ô Tổng cộng = 100.000.000 (projection từ formula, không tin '
        + 'giá trị lưu) và KHÔNG sinh <input cho row tổng',
      test: function (h) {
        const hasTotal = h.indexOf('100.000.000') >= 0 ||
          h.indexOf('100000000') >= 0;
        if (!hasTotal) return false;
        return ((h.match(/<input[^>]*tong_cong/g) || []).length === 0);
      } }
  ],
  'nested-grid': [
    { id: 'ng-multi-row-header',
      desc: 'header nhiều hàng bảo toàn: <thead> có >= 2 <tr>',
      test: function (h) {
        const seg = h.match(/<thead[\s\S]*?<\/thead>/i);
        if (!seg) return false;
        return (seg[0].match(/<tr\b/g) || []).length >= 2;
      } },
    { id: 'ng-colspan-preserved',
      /* [Lead sync] Invariant cấu trúc: header nhiều tầng PHẢI có gộp ngang
       * (colspan>=2) và ít nhất một gộp dọc (rowspan>=2) như nguồn thật
       * (PLI_M02 N1: "Số, ngày cấp…" colspan=3, STT rowspan=2). Text cụ thể
       * thuộc vocabulary từng mẫu — đối chiếu chéo với manifest nằm ở
       * test_runtime_tables.js; tên cột canonical còn chờ owner (ledger). */
      desc: 'header bảo toàn gộp ngang/dọc vật lý (colspan>=2 và rowspan>=2 '
        + 'hiện diện trong <thead>)',
      test: function (h) {
        const seg = h.match(/<thead[\s\S]*?<\/thead>/i);
        if (!seg) return false;
        const spans = seg[0].match(/<(?:th|td)\b[^>]*>/g) || [];
        let colspan = 0, rowspan = 0;
        spans.forEach(function (t) {
          const c = t.match(/\bcolspan="(\d+)"/);
          if (c && Number(c[1]) > 1) colspan++;
          const r = t.match(/\browspan="(\d+)"/);
          if (r && Number(r[1]) > 1) rowspan++;
        });
        return colspan >= 1 && rowspan >= 1;
      } },
    { id: 'ng-row-id-stable',
      desc: 'mỗi hàng dữ liệu mang _row_id ổn định (' + NG_ROW_ID_1 + ', ' +
        NG_ROW_ID_2 + ')',
      test: function (h) {
        return h.indexOf('_row_id="' + NG_ROW_ID_1) >= 0 ||
          h.indexOf('data-row-id="' + NG_ROW_ID_1) >= 0;
      } },
    { id: 'ng-no-flatten',
      /* [Lead sync] Bất biến "không làm phẳng": MỌI data-row cùng số <td>
       * (= số cột vật lý của bảng đang dispatch) và >= 2. Số tuyệt đối theo
       * từng mẫu do test_runtime_tables đối chiếu registry/manifest; số cột
       * canonical toàn mẫu còn chờ owner chốt (ledger gap N1). */
      desc: 'KHÔNG làm phẳng: mọi hàng dữ liệu cùng số ô vật lý (>=2)',
      test: function (h) {
        const rows = h.match(/<tr\b[^>]*>[\s\S]*?<\/tr>/g) || [];
        const dataRows = rows.filter(function (r) {
          return /data-row-id|_row_id/.test(r);
        });
        if (!dataRows.length) return false;
        let prev = -1;
        for (let i = 0; i < dataRows.length; i++) {
          const n = (dataRows[i].match(/<td\b/g) || []).length;
          if (n < 2) return false;
          if (prev < 0) prev = n;
          else if (prev !== n) return false;
        }
        return true;
      } },
  ],
  'output-table': [
    { id: 'ot-presence',
      desc: 'lưới CHỈ ĐỌC vẫn tồn tại trong DOM dù 0 input (role="grid" / '
        + 'data-output-only="true" / class="output-table")',
      test: function (h) {
        return /data-output-only="true"/.test(h) ||
          /role="grid"/.test(h) || /output-table/.test(h);
      } },
    { id: 'ot-dimensions-labels',
      /* [Lead sync] Nhãn pháp lý THẬT của PLI_M70 trong registry là
       * "NGƯỜI NỘP\n(Ký và ghi họ tên)" / "NGƯỜI NHẬN\n…" — marker đòi hai
       * VAI TRÒ ký hiện diện (không phụ thuộc fixture text) + bảng >=2 hàng. */
      desc: 'nhãn pháp lý hai vai trò ký được giữ (NGƯỜI NỘP / NGƯỜI NHẬN) '
        + 'trên bảng >= 2 hàng',
      test: function (h) {
        const rows = h.match(/<tr\b/g) || [];
        return h.indexOf('NGƯỜI NỘP') >= 0 &&
          h.indexOf('NGƯỜI NHẬN') >= 0 && rows.length >= 2 &&
          h.indexOf('<table') >= 0;
      } },
    { id: 'ot-zero-input',
      desc: 'renderer KHÔNG sinh bất kỳ <input>/<textarea>/<select> nào',
      test: function (h) {
        return !/<input\b/.test(h) && !/<textarea\b/.test(h) &&
          !/<select\b/.test(h);
      } }
  ]
};

console.log('\n== [B] dispatcher render theo section.kind ==');

['fixed-matrix', 'nested-grid', 'output-table'].forEach(function (kind) {
  const result = bestTransport(kind);
  const nMarkers = MARKERS[kind].length;

  safe('B.' + kind + '.dispatcher: >=1 transport render sinh đủ ' + nMarkers +
    '/' + nMarkers + ' marker DOM', () => {
      const detail = transportsFor(kind).map(function (tr) {
        const r = runTransport(tr);
        if (!r.ok) return '[' + tr.label + '] RUNTIME THROW: ' + r.err;
        if (!String(r.html).trim()) {
          return '[' + tr.label + '] 0/' + nMarkers +
            ' — html RỖNG (markup bị nuốt)';
        }
        const hits = MARKERS[kind].filter(function (m) {
          try { return !!m.test(r.html); } catch (e) { return false; }
        }).length;
        return '[' + tr.label + '] ' + hits + '/' + nMarkers + ' marker' +
          (hits < nMarkers ? ' — html=' + r.html.slice(0, 140) : '');
      }).join(' | ');
      const ok = result && result.hit === nMarkers;
      return {
        pass: ok,
        expect: 'runtime phải dispatch kind "' + kind + '" sang component riêng '
          + '(hôm nay renderBlock chỉ biết p/chk/table/loop, default trả "")',
        actual: 'best=' + (result ? '[' + result.transport.label + '] ' +
          result.hit + '/' + nMarkers : 'không có transport') + ' — chi tiết: ' +
          detail,
        fix: 'wire dispatcher theo section.kind trong app_web/ui/render.js '
          + '(renderBlock default case đang nuốt) + đăng ký module trong '
          + 'app_web/ui/index.html; fallback legacy chỉ dành cho schema cũ đã '
          + 'classify (PLAN Lane B1).'
      };
    });

  MARKERS[kind].forEach(function (marker) {
    safe('B.' + kind + '.' + marker.id + ': ' + marker.desc, () => {
      const b = bestTransport(kind);
      /* Mệnh đề marker chỉ PASS khi CÓ một transport đạt đủ chuẩn của kind
       * (đúng transport dispatch thật); nếu chưa, mọi marker của kind đỏ cùng
       * nhau — tránh "đạt 1/n rồi tưởng đã wire". */
      const dispatcherOk = !!b && b.hit === MARKERS[kind].length;
      const pass = dispatcherOk && b.satisfied.indexOf(marker) >= 0;
      let actual;
      if (!b || !b.run || b.run.err) {
        actual = 'mọi transport ném exception, không đánh giá được marker';
      } else if (!dispatcherOk) {
        actual = 'chưa có transport nào đạt đủ ' + MARKERS[kind].length +
          '/' + MARKERS[kind].length + ' marker nên mệnh đề này CHƯA thể xanh '
          + '(best [' + b.transport.label + '] đạt ' + Math.max(0, b.hit) + '/' +
          MARKERS[kind].length + ', mệnh đề này ở trạng thái: ' +
          (b.satisfied.indexOf(marker) >= 0 ? 'thỏa cục bộ' : 'chưa thỏa') + ')';
      } else {
        actual = '[dispatched bởi ' + b.transport.label + '] marker thỏa trên '
          + 'HTML (' + b.run.html.length + ' bytes)';
      }
      return {
        pass: pass,
        expect: marker.desc + ' (contract p2_component_contracts.md; chỉ tính '
          + 'khi runtime thực sự dispatch kind)',
        actual: actual,
        fix: 'xem mệnh đề B.' + kind + '.dispatcher.'
      };
    });
  });
});

// ---------------------------------------------------------------------------
// [C] DRAFT ROUND-TRIP: _row_id ổn định + dữ liệu phẳng kind mới không mất
// ---------------------------------------------------------------------------

console.log('\n== [C] draft round-trip (_row_id ổn định) ==');

safe('C1. migrateDraft(v2) chạy 2 lần: _row_id của loop nested-grid KHÔNG đổi '
  + '(idempotent)', () => {
    const p1 = {
      v: 2, caseId: 'qa_wave_b3', checkedForms: ['PLI_M02'],
      activeDocId: 'PLI_M02', autoSum: false, viewState: {},
      store: { values: {}, checks: {}, loops: {} },
      savedAt: '2026-08-27T00:00:00Z'
    };
    p1.store.loops[NG_LOOP] = clone(NG_ROWS_OK);
    const a = FD.migrateDraft(JSON.parse(JSON.stringify(p1)));
    const b = FD.migrateDraft(JSON.parse(JSON.stringify(a)));
    const ids = function (draft) {
      return ((draft && draft.store && draft.store.loops &&
        draft.store.loops[NG_LOOP]) || []).map(function (r) {
        return r._row_id;
      });
    };
    const ia = ids(a);
    const ib = ids(b);
    return {
      pass: JSON.stringify(ia) === JSON.stringify(ib) &&
        ia[0] === NG_ROW_ID_1 && ia[1] === NG_ROW_ID_2,
      expect: '_row_id giữ nguyên qua 2 vòng migrateDraft: [' + NG_ROW_ID_1 +
        ', ' + NG_ROW_ID_2 + ']',
      actual: 'lan1=[' + ia.join(',') + '] lan2=[' + ib.join(',') + ']',
      fix: 'normalizeStoreLoops/migrateDraft (form-domain.js) đang sinh lại id '
        + 'hoặc drop id — phải idempotent theo contract mục 1.7/3.4.'
    };
  });

safe('C2. GridCtl.ensureIds (channel runtime finishApplyDraft) gán id còn thiếu '
  + 'và KHÔNG đụng id đã có', () => {
    const st = ngStore([
      { ho_ten: 'HAS_ID', _row_id: NG_ROW_ID_1 },
      { ten_to_chuc: 'NO_ID' }
    ]);
    App.GridCtl.ensureIds(st);
    const idsBefore = st.loops[NG_LOOP][0]._row_id;
    App.GridCtl.ensureIds(st);
    const idsAfterFirst = st.loops[NG_LOOP][1]._row_id;
    App.GridCtl.ensureIds(st);
    const idsAfterSecond = st.loops[NG_LOOP][1]._row_id;
    return {
      pass: idsBefore === NG_ROW_ID_1 && !!idsAfterFirst &&
        idsAfterFirst === idsAfterSecond,
      expect: 'row 0 giữ ' + NG_ROW_ID_1 + ', row 1 nhận id ổn định giữa 2 lần '
        + 'ensureIds',
      actual: 'row0=' + idsBefore + ', row1(lan1)=' + idsAfterFirst +
        ', row1(lan2)=' + idsAfterSecond,
      fix: 'GridCtl.ensureIds không idempotent — đây là regression đối với '
        + 'editable-grid, báo lane sở hữu app.js.'
    };
  });

safe('C3. upgrade v1->v2 GIỮ nguyên dữ liệu phẳng của kind mới (fixed-matrix '
  + 'flat values + nested loop rows) và unknown key khác', () => {
    const v1 = {
      v: 1, caseId: 'qa_wave_b3_legacy', checkedForms: ['PLI_M03', 'PLI_M02'],
      autoSum: false,
      store: { values: {}, checks: {}, loops: {} }
    };
    v1.store.values[FLAT_KEY_TN] = '60.000.000';
    v1.store.values.chu_ky_tiep_nhan_ho_so_note = 'fixture unknown key';
    v1.store.loops[NG_LOOP] = clone(NG_ROWS_OK);
    const up = FD.migrateDraft(JSON.parse(JSON.stringify(v1)));
    const keptValue = up && up.store && up.store.values &&
      up.store.values[FLAT_KEY_TN];
    const keptUnknown = up && up.store && up.store.values &&
      up.store.values.chu_ky_tiep_nhan_ho_so_note;
    const rows = up && up.store && up.store.loops &&
      up.store.loops[NG_LOOP] || [];
    return {
      pass: up && up.v === 2 && keptValue === '60.000.000' &&
        keptUnknown === 'fixture unknown key' && rows.length === 2 &&
        !!rows[0]._row_id,
      expect: 'migration additive: v=2, flat value "' + FLAT_KEY_TN +
        '" + unknown key + 2 row nested loop đều còn (row được gán _row_id)',
      actual: 'v=' + (up && up.v) + ', flat=' + JSON.stringify(keptValue) +
        ', unknown=' + JSON.stringify(keptUnknown) + ', rows=' + rows.length +
        ', row0._row_id=' + (rows[0] ? rows[0]._row_id : undefined),
      fix: 'migrateDraft (form-domain.js) đang mất dữ liệu kind mới — vi phạm '
        + '"preserve unknown fields"; đây là prereq của Lane B1 (integration).'
    };
  });

// ---------------------------------------------------------------------------
// [D] VALIDATION CHANNEL FormDomain cho kind mới
// ---------------------------------------------------------------------------

console.log('\n== [D] validation mount đúng channel FormDomain ==');

function contractShapeOk(err) {
  return err && typeof err.key === 'string' &&
    ['code' in err, 'message' in err, 'severity' in err].every(Boolean) &&
    (err.severity === 'blocking' || err.severity === 'warning');
}

safe('D.fixed-matrix.MONEY: validateDocument surfaces lỗi MONEY blocking đúng '
  + 'như module thuần', () => {
    const baseline = FixedMatrix.validate(FM_SPEC,
      { values: clone(FM_DRAFT_BAD.values) });
    const baselineKeys = baseline.map(function (e) {
      return e.code + '@' + e.key + '#' + e.severity;
    });
    /* [Lead sync 2026-08-27] Kênh thật là docId CÓ entry trong registry
     * (validation form-scoped): dùng PLI_M03 thay docId qa không đăng ký. */
    const doc = {
      id: 'PLI_M03', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'table', rows: [], kind: 'fixed-matrix' }, clone(FM_SPEC))]
    };
    const st = { values: clone(FM_DRAFT_BAD.values), checks: {}, loops: {} };
    const got = FD.validateDocument(doc.id, doc.blocks, st, {});
    const matched = got.filter(function (e) {
      return e.code === 'MONEY' && e.severity === 'blocking' &&
        String(e.key).indexOf('nguon_von_dieu_le.') === 0;
    });
    return {
      pass: baseline.length > 0 && matched.length >= baseline.filter(function (e) {
        return e.code === 'MONEY';
      }).length,
      expect: 'validateDocument trả >= 1 lỗi MONEY blocking keyed '
        + '"nguon_von_dieu_le.<row>.<tag>" (baseline module thuần: ' +
        baselineKeys.join('; ') + ')',
      actual: 'validateDocument trả ' + got.length + ' lỗi: ' +
        JSON.stringify(got.map(function (e) {
          return e.code + '@' + e.key;
        })),
      fix: 'wire validate() của app_web/ui/fixed-matrix.js vào FormDomain '
        + '(FD.validateDocument / validateGridLoop analog) thay vì validator '
        + 'hard-code trong app.js — channel đúng là FormDomain.'
    };
  });

safe('D.fixed-matrix.error-key-navigable: key lỗi tồn tại như data-key trên '
  + 'HTML mẫu tương ứng', () => {
    const doc = {
      id: 'PLI_M03', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'table', rows: [], kind: 'fixed-matrix' }, clone(FM_SPEC))]
    };
    const st = { values: clone(FM_DRAFT_BAD.values), checks: {}, loops: {} };
    const got = FD.validateDocument(doc.id, doc.blocks, st, {});
    if (!got.length) {
      return {
        pass: false,
        expect: 'key của lỗi MONEY phải trỏ đúng ô trên DOM (navigateToError)',
        actual: 'không có lỗi nào -> không thể xác minh kênh điều hướng',
        fix: 'mệnh đề D.fixed-matrix.MONEY phải xanh trước.'
      };
    }
    /* [Lead sync 2026-08-27] Navigable phải kiểm trên CHÍNH kênh render
     * production: truyền sectionContracts registry qua anchor override như
     * transport-4. Key lỗi ảo '.cross_field.' không phải ô input — được loại
     * khỏi yêu cầu data-key, panel lỗi hiển thị ở document level. */
    const anchorText = 'NGUỒN VỐN ĐIỀU LỆ';
    const contracts = [qaRegistryEntry('PLI_M03',
      FM_SPEC.section_id, anchorText)];
    const html = R.renderBlocks(
      { id: 'PLI_M03', ten_mau: 'qa', blocks: [
        { t: 'p', runs: [{ text: anchorText }] }] }, st,
      { docId: 'PLI_M03', sectionContracts: contracts });
    const missing = got.filter(function (e) {
      if (String(e.key).indexOf('.cross_field.') >= 0) return false;
      return html.indexOf('data-key="' + e.key + '"') < 0 &&
        html.indexOf(e.key) < 0;
    }).map(function (e) { return e.key; });
    return {
      pass: missing.length === 0,
      expect: 'mọi key lỗi đều tìm thấy trong HTML render (data-key="…")',
      actual: missing.length ? 'missing data-key: ' + missing.join(', ') +
        ' — html=' + (html.trim() ? html.slice(0, 160) : '(RỖNG)')
        : 'mọi key đều navigable',
      fix: 'markup ô nhập fixed-matrix phải mang data-key = flat key '
        + '"<semantic_key>.<row_id>.<tag>" (contract mục 2.4).'
    };
  });

safe('D.nested-grid.REQUIRED_FIELD: validateDocument surfaces REQUIRED_FIELD '
  + 'đúng như module thuần', () => {
    const baseline = NestedGrid.validate(clone(NG_SPEC),
      clone(NG_ROWS_MISSING_REQUIRED)).filter(function (e) {
      return e.code === 'REQUIRED_FIELD';
    });
    const doc = {
      id: 'PLI_M02', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'loop', loop: NG_LOOP, headerRows: [], rows: [],
          cols: [], kind: 'nested-grid' }, clone(NG_SPEC))]
    };
    const st = ngStore(NG_ROWS_MISSING_REQUIRED);
    const got = FD.validateDocument(doc.id, doc.blocks, st, {});
    const matched = got.filter(function (e) {
      return e.code === 'REQUIRED_FIELD';
    });
    /* [Lead sync 2026-08-27] Mệnh đề này chứng minh KÊNH (channel): lỗi kind
     * mới surface qua validateDocument theo loop name + shape + severity.
     * Parity tuyệt đối về VOCABULARY cột (ho_ten vs ten_nguoi_dai_dien...)
     * phụ thuộc quyết định owner về tag canonical N1 (đã ghi ledger gap) —
     * đối chiếu số lượng từng tag thuộc test_runtime_tables + B2 regen. */
    const ok = matched.length >= 1 && matched.every(function (e) {
      return String(e.key).indexOf(NG_LOOP + '.') === 0 &&
        e.severity === 'blocking';
    });
    return {
      pass: ok,
      expect: '>= 1 lỗi REQUIRED_FIELD blocking surface qua validateDocument '
        + 'keyed "<semantic_key>.<_row_id>.<tag>" (baseline module thuần: ' +
        baseline.map(function (e) { return e.code + '@' + e.key; }).join('; ') +
        '; vocabulary cột canonical đang chờ owner — ledger gap N1)',
      actual: 'validateDocument trả ' + got.length + ' lỗi: ' +
        JSON.stringify(got.map(function (e) { return e.code + '@' + e.key; })),
      fix: 'wire validate()/normalizeRows của app_web/ui/nested-grid.js vào '
        + 'FormDomain với row-group required_columns (contract mục 3.2/3.3).'
    };
  });

safe('D.nested-grid.DISCRIMINATOR_INVALID: giá trị loai_dong ngoài contract '
  + 'phải bị chặn blocking', () => {
    const baseline = NestedGrid.validate(clone(NG_SPEC),
      clone(NG_ROWS_BAD_DISCRIMINATOR));
    const doc = {
      id: 'PLI_M02', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'loop', loop: NG_LOOP, headerRows: [], rows: [],
          cols: [], kind: 'nested-grid' }, clone(NG_SPEC))]
    };
    const st = ngStore(NG_ROWS_BAD_DISCRIMINATOR);
    const got = FD.validateDocument(doc.id, doc.blocks, st, {});
    const matched = got.filter(function (e) {
      return e.code === 'DISCRIMINATOR_INVALID' && e.severity === 'blocking';
    });
    return {
      pass: baseline.some(function (e) { return e.code === 'DISCRIMINATOR_INVALID'; }) &&
        matched.length >= 1,
      expect: '>= 1 lỗi DISCRIMINATOR_INVALID blocking (baseline module thuần: ' +
        baseline.map(function (e) { return e.code; }).join(';') + ')',
      actual: 'validateDocument trả ' + JSON.stringify(got.map(function (e) {
        return e.code + '@' + e.key;
      })),
      fix: 'discriminator/row_groups của nested-grid chưa nối vào FormDomain '
        + '(contract mục 3.3: duplicate/validity theo vai trò dòng).'
    };
  });

safe('D.nested-grid.error-contract-shape: mọi lỗi trả về đủ 5 trường contract '
  + '{key,docId,code,message,severity}', () => {
    const doc = {
      id: 'PLI_M02', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'loop', loop: NG_LOOP, headerRows: [], rows: [],
          cols: [], kind: 'nested-grid' }, clone(NG_SPEC))]
    };
    const st = ngStore(NG_ROWS_MISSING_REQUIRED.concat(NG_ROWS_BAD_DISCRIMINATOR));
    const got = FD.validateDocument(doc.id, doc.blocks, st, {});
    if (!got.length) {
      return {
        pass: false,
        expect: 'mỗi lỗi đều mang đủ {key,docId,code,message,severity} theo '
          + 'docs/htkk-ui-contract.md',
        actual: 'không có lỗi nào để kiểm (validateDocument bỏ qua kind mới)',
        fix: 'mệnh đề D.nested-grid.* phải xanh trước.'
      };
    }
    const bad = got.filter(function (e) { return !contractShapeOk(e); });
    return {
      pass: bad.length === 0,
      expect: 'shape lỗi tuân docs/htkk-ui-contract.md',
      actual: bad.length ? JSON.stringify(bad) : 'mọi lỗi đúng shape',
      fix: 'mapper lỗi của kind mới phải phát theo shape cũ, không phát struct lạ.'
    };
  });

safe('D.output-table.no-phantom-error: output-table CHỈ ĐỌC hợp lệ KHÔNG sinh '
  + 'lỗi dữ liệu giả nhưng vẫn được audit presence (không bị nuốt)', () => {
    const doc = {
      id: 'QA_OT_VAL', ten_mau: 'qa', blocks: [
        Object.assign({ t: 'table', rows: [], kind: 'output-table' }, clone(OT_SPEC))]
    };
    const got = FD.validateDocument(doc.id, doc.blocks, R.newStore(), {});
    const phantom = got.filter(function (e) {
      return String(e.key).indexOf('chu_ky_tiep_nhan_ho_so') >= 0 ||
        String(e.docId) === 'PLI_M70';
    });
    const dossier = FD.validateDossier([doc], R.newStore(), {});
    const shapeBad = dossier.filter(function (e) { return !contractShapeOk(e); });
    const markdowned = phantom.filter(function (e) {
      return e.code === 'REQUIRED' || e.code === 'MIN_ROWS';
    });
    return {
      pass: markdowned.length === 0 && shapeBad.length === 0,
      expect: 'output-table hợp lệ không bị áp rule dữ liệu giả (REQUIRED/' +
        'MIN_ROWS/...) và mọi lỗi trong dossier đúng shape contract. LƯU Ý: '
        + 'mệnh đề này chỉ có giá trị chặn sau khi validation được wire; hôm '
        + 'nay nó xanh vì runtime trả 0 lỗi cho toàn bộ kind mới.',
      actual: 'phantom=' + JSON.stringify(markdowned.map(function (e) {
        return e.code + '@' + e.key;
      })) + ', badShape=' + shapeBad.length +
        ', validateDocument trả ' + got.length + ' lỗi (baseline dựng sẵn: '
        + '(trống là bình thường với output-table))',
      fix: 'validator đang áp rule editable-grid lên output-table — chỉ audit '
        + 'presence của grid (contract mục 4.3), không đòi input.'
    };
  });

// ---------------------------------------------------------------------------
// Kết luận
// ---------------------------------------------------------------------------

const GROUP_OF = function (name) {
  return String(name).charAt(0);
};
const groups = {};
RESULTS.forEach(function (item) {
  const g = GROUP_OF(item.name);
  groups[g] = groups[g] || { pass: 0, fail: 0 };
  if (item.pass) groups[g].pass++;
  else groups[g].fail++;
});

console.log('-'.repeat(72));
Object.keys(groups).sort().forEach(function (g) {
  const label = {
    S: '[S] self-check harness',
    A: '[A] index.html nạp module P2',
    B: '[B] dispatcher render theo section.kind',
    C: '[C] draft round-trip _row_id',
    D: '[D] validation channel FormDomain'
  }[g] || '[?] khác';
  console.log('%s : %d PASS / %d FAIL', label, groups[g].pass, groups[g].fail);
});
console.log('-'.repeat(72));

if (failed > 0) {
  console.log('NHỮNG MỆNH ĐỎ (điều kiện để gate XANH):');
  RESULTS.filter(function (i) { return !i.pass; }).forEach(function (item, i) {
    console.log('  ' + (i + 1) + '. ' + item.name);
  });
  console.log('-'.repeat(72));
  console.log('Gate ĐANG ĐỎ CÓ KIỂM SOÁT: runtime P2 chưa wire 3 module mới.');
  console.log('Thứ tự xử lý khuyến nghị: A (nạp script + UMD) -> B (dispatcher '
    + 'render) -> D (validation FormDomain) -> C kiểm lại round-trip.');
  console.log('Chi tiết EXPECT/ACTUAL/HÌNH NHƯ CẦN nằm ở từng dòng FAIL phía trên.');
}

console.log('Ket qua wiring gate: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
