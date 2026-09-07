/* test_f1_output_ui.js — Lane F1-OUT: 11 section O1 OUTPUT_ONLY.
 * Kiểm thử KHÔNG GUI trên chuỗi HTML sinh ra từ ui/render.js +
 * ui/output-table.js + contract runtime trong ui/form-domain.js.
 *
 * Phủ:
 *  1. renderBlocks + sectionContracts: component output-table chèn đúng chỗ,
 *     mirror cell render span.mirror-fld read-only với giá trị canonical store;
 *     KHÔNG có <input>/tab-stop nào trong vùng component; store thiếu key ->
 *     span trống (không placeholder, không token).
 *  2. Anchor heading-paragraph của output-table KHÔNG bị bọc dupe-anchor
 *     (heading thuộc bản giấy) — block nguồn phía sau thì bị ẩn.
 *  3. output-table.js: grid.cells per-cell mirror + text; chuỗi contract tĩnh
 *     (labels) render GIỐNG HỆT hành vi cũ (backward-compat); cell lạ fail
 *     closed về text rỗng, không crash, không input.
 *  4. Escape: giá trị store không bao giờ ra raw HTML.
 *
 * Chạy: node app_web/test_f1_output_ui.js  (exit 0 = PASS)
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const OutputTable = require('./ui/output-table.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProduction(formId) {
  return JSON.parse(fs.readFileSync(path.join(BLOCKS, formId + '.json'),
    'utf8'));
}

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else { failed++; console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

function storeWith(values) {
  const st = R.newStore();
  Object.keys(values || {}).forEach(function (k) { st.values[k] = values[k]; });
  return st;
}

/* Vùng HTML của 1 component output-table: từ data-section-id="..." tới
 * </table> kế tiếp (component output-table luôn là 1 <table> duy nhất). */
function componentHtml(html, sectionId) {
  const marker = 'data-section-id="' + sectionId + '"';
  const start = html.indexOf(marker);
  if (start < 0) return '';
  const open = html.lastIndexOf('<table', start);
  const end = html.indexOf('</table>', start);
  return (open < 0 || end < 0) ? '' : html.slice(open, end + '</table>'.length);
}

/* ===================================================== 1. blocks + contract */
const CASES = [
  ['PLI_M52', 'khung_ra_soat_4_nhom', {
    'dn.ten_tieng_viet': 'CONG TY TNHH ABC', 'ma_so_van_ban': '0312345678',
    'ma_so_cn': '0300999', 'ma_so_vpdd': '', 'ma_so_ddkd': ''
  }],
  ['PLI_M56', 'cn_vppd_ddkd_tiep_tuc_truoc_han', {
    'cn.ten_tieng_viet': 'CHI NHANH A', 'cn.ma_so': '0300999001'
  }],
  ['PLI_M63', 'dia_diem_truc_thuoc_bi_thu_hoi', {}],
  ['PLI_M66', 'don_vi_dang_lam_thu_tuc_cham_dut', {
    'cn.ten_tieng_viet': 'CHI NHANH B', 'cn.ma_so_2': '0311222333'
  }],
  ['PLI_M66', 'ddkd_truc_thuoc_dang_cham_dut', {}],
  ['PLI_M67', 'don_vi_cham_dut_sau_day', { 'cn.dia_chi': 'HA LONG, QUANG NINH' }],
  ['PLI_M68', 'don_vi_cham_dut_khi_doanh_nghiep_giai_the', {}],
  ['PLI_M70', 'ho_so_bao_gom', {}],
  ['PLI_M71', 'ho_so_bao_gom_online', {}],
  ['PLI_M75', 'cn_vppd_ddkd_khoi_phuc', {}],
  ['PLI_M75', 'ddkd_truc_thuoc_khoi_phuc', {}]
];

for (const [formId, sectionId, values] of CASES) {
  const doc = loadProduction(formId);
  const contracts = FD.sectionContractsOf(formId)
    .filter(function (e) { return e.sectionId === sectionId; });
  assert.strictEqual(contracts.length, 1,
    formId + '/' + sectionId + ': đúng 1 contract runtime');
  const html = R.renderBlocks(doc, storeWith(values), {
    docId: formId,
    sectionContracts: contracts
  });
  const comp = componentHtml(html, sectionId);
  check(formId + '/' + sectionId + ': component output-table render',
    comp.includes('data-component="output-table"') &&
    comp.includes('data-output-only="true"'));
  check(formId + '/' + sectionId + ': KHÔNG <input> trong vùng output',
    (comp.match(/<input\b/gi) || []).length === 0);
  check(formId + '/' + sectionId + ': KHÔNG tab-stop (tabindex) trong vùng',
    (comp.match(/tabindex=/gi) || []).length === 0);

  // mirror spans: khớp với số mirror key của contract
  const spec = contracts[0].spec;
  const cells = (spec.grid && spec.grid.cells) || [];
  const wantMirrors = [];
  cells.forEach(function (row) {
    (row || []).forEach(function (c) {
      if (c && typeof c === 'object' && c.mirror) wantMirrors.push(c.mirror);
    });
  });
  const spans = comp.match(/<span class="mirror-fld" data-key="[^"]+">[^<]*<\/span>/g) || [];
  check(formId + '/' + sectionId + ': đúng số mirror span (' +
    wantMirrors.length + ')', spans.length === wantMirrors.length);
  // giá trị canonical đổ vào span; store thiếu -> trống
  for (const key of wantMirrors) {
    const esc = String(values[key] == null ? '' : values[key])
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    const wantSpan = '<span class="mirror-fld" data-key="' + key + '">' +
      esc + '</span>';
    if (!comp.includes(wantSpan)) {
      check(formId + '/' + sectionId + ': mirror ' + key +
        ' = "' + (values[key] == null ? '' : values[key]) + '"', false,
        wantSpan);
      break;
    }
  }
  check(formId + '/' + sectionId + ': mirror values đúng store',
    true);
}

/* ============================================== 2. heading không bị ẩn ===== */
{
  const doc = loadProduction('PLI_M52');
  const html = R.renderBlocks(doc, storeWith({}), {
    docId: 'PLI_M52',
    sectionContracts: FD.sectionContractsOf('PLI_M52')
      .filter(function (e) { return e.sectionId === 'khung_ra_soat_4_nhom'; })
  });
  const needle = 'Đề nghị doanh nghiệp rà soát';
  const at = html.indexOf(needle);
  check('M52: heading anchor còn hiển thị', at >= 0);
  const prefix = html.slice(Math.max(0, at - 40), at);
  check('M52: heading KHÔNG bị bọc dupe-anchor',
    !prefix.includes('dupe-anchor'));
}

/* ============================ 3. output-table.js cells + backward-compat === */
{
  // cells mirror + text; store thiếu key -> span trống
  const spec = {
    kind: 'output-table', section_id: 'x', semantic_key: 'x',
    grid: {
      rows: 2, cols: 2,
      labels: [['Nhóm', ''], ['1.', '']],
      cells: [
        [{ text: 'Nhóm' }, { mirror: 'dn.ten_tieng_viet' }],
        [{ text: 'Mã số: ', mirror: 'ma_so_van_ban' }, { text: '' }]
      ]
    },
    inputs: [], outputOnlyTags: ['dn.ten_tieng_viet', 'ma_so_van_ban']
  };
  const html1 = OutputTable.renderOutputTable(spec, {
    values: { 'dn.ten_tieng_viet': 'ABC <Co., Ltd>', 'ma_so_van_ban': '' }
  });
  check('output-table cells: text tĩnh render', html1.includes('Nhóm') &&
    html1.includes('Mã số: '));
  check('output-table cells: mirror có giá trị store',
    html1.includes('data-key="dn.ten_tieng_viet">ABC &lt;Co., Ltd&gt;</span>'));
  check('output-table cells: store thiếu -> span trống (không placeholder)',
    html1.includes('data-key="ma_so_van_ban"></span>'));
  check('output-table cells: không input/tabindex',
    (html1.match(/<input\b/gi) || []).length === 0 &&
    (html1.match(/tabindex=/gi) || []).length === 0);

  // labels tĩnh thuần: hành vi cũ GIỐNG HỆT (không có cells -> cellLabel)
  const staticSpec = {
    kind: 'output-table', section_id: 'chu_ky', semantic_key: 'chu_ky',
    grid: { rows: 1, cols: 2, labels: ['NGƯỜI NỘP', 'NGƯỜI NHẬN'] },
    inputs: []
  };
  const html2 = OutputTable.renderOutputTable(staticSpec, { values: {} });
  check('output-table labels tĩnh: 2 ô như cũ',
    (html2.match(/<td\b/g) || []).length === 2 &&
    html2.includes('NGƯỜI NỘP') && html2.includes('NGƯỜI NHẬN') &&
    (html2.match(/<input\b/gi) || []).length === 0);

  // cell spec sai kiểu -> fail closed về text rỗng, không crash
  const bad = {
    kind: 'output-table', section_id: 'b', semantic_key: 'b',
    grid: { rows: 1, cols: 2, labels: [['a', 'b']],
      cells: [[{ text: 42, mirror: 7 }, null]] },
    inputs: []
  };
  const html3 = OutputTable.renderOutputTable(bad, { values: {} });
  check('output-table cell lạ: fail closed, không crash, không input',
    (html3.match(/<td\b/g) || []).length === 2 &&
    !html3.includes('data-key') &&
    (html3.match(/<input\b/gi) || []).length === 0);
}

console.log('\nKET QUA F1-OUT UI: %d/%d PASS%s', passed, passed + failed,
  failed === 0 ? '' : ' -> FAIL');
process.exit(failed === 0 ? 0 : 1);
