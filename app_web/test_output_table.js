/* Contract test for output-table using production PLI_M70/PLI_M71 blocks.
 * Run with: node app_web/test_output_table.js */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const OutputTable = require('./ui/output-table.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProduction(formId) {
  return JSON.parse(fs.readFileSync(
    path.join(BLOCKS, formId + '.json'), 'utf8'));
}

/* [Lead sync sau regen W1 d48eb7d] Nhãn chữ ký PLI_M70/M71 KHÔNG còn là
 * paragraph role 'signature'/'form-subtitle' nữa — regen chuyển chúng thành
 * Ô của w:tbl output-table (1 bảng 2x1 / 1x1). Fixture đọc cell text của
 * bảng thật thay vì paragraph; bản chất khẳng định (labels lấy từ blocks
 * production) giữ nguyên. */
function signatureText(block) {
  if (block.t === 'table') {
    return (block.rows || []).map(row => (row.cells || []).map(cell =>
      (cell.runs || []).map(run => run && run.text || '').join('')
    ).join('\n')).join('\n');
  }
  return (block.runs || []).map(run => run && run.text || '').join('');
}

function gridCellTexts(document) {
  return (document.blocks || [])
    .filter(block => block.t === 'table')
    .flatMap(block => (block.rows || []).map(row =>
      (row.cells || []).map(cell => signatureText(cell)).join('\n')));
}

const m70Labels = (() => {
  const cells = gridCellTexts(loadProduction('PLI_M70'))
    .filter(text => text.includes('NGƯỜI'));
  assert.strictEqual(cells.length, 2, 'PLI_M70 signature grid cells');
  cells.forEach((text, index) => {
    assert.ok(text.includes(['NGƯỜI NỘP', 'NGƯỜI NHẬN'][index]),
      'PLI_M70 production signature label ' + index);
  });
  return cells.map(text => text.split('\n')[0].trim());
})();
const m71 = loadProduction('PLI_M71');
const m71LabelsFromBlocks = gridCellTexts(m71)
  .filter(text => text.includes('TÊN CƠ QUAN ĐĂNG KÝ KINH'));
assert.strictEqual(m71LabelsFromBlocks.length, 1,
  'PLI_M71 production signing heading exists');

const m70Contract = {
  kind: 'output-table',
  section_id: 'chu_ky_nguoi_nop_nguoi_nhan',
  semantic_key: 'chu_ky_tiep_nhan_ho_so',
  grid: { rows: 2, cols: 1, labels: m70Labels }
};
const m71Contract = {
  kind: 'output-table',
  section_id: 'chu_ky_co_quan_cap_tinh',
  semantic_key: 'chu_ky_cqb_m71',
  grid: { rows: 1, cols: 1, labels: [m71LabelsFromBlocks[0]] }
};

const m70Before = JSON.stringify(m70Contract);
const m70Html = OutputTable.renderOutputTable(m70Contract, {});
assert.ok(m70Html.includes('data-component="output-table"'));
assert.ok(m70Html.includes('data-output-only="true"'));
assert.ok(m70Html.includes('data-section-id="chu_ky_nguoi_nop_nguoi_nhan"'));
assert.ok(m70Html.includes('NGƯỜI NỘP') && m70Html.includes('NGƯỜI NHẬN'));
assert.strictEqual((m70Html.match(/<tr\b/g) || []).length, 2);
assert.strictEqual((m70Html.match(/<td\b/g) || []).length, 2);
assert.strictEqual((m70Html.match(/<input\b/gi) || []).length, 0);
assert.strictEqual(JSON.stringify(m70Contract), m70Before,
  'render does not mutate contract');

const m71Html = OutputTable.renderOutputTable(m71Contract, {});
assert.strictEqual((m71Html.match(/<tr\b/g) || []).length, 1);
assert.strictEqual((m71Html.match(/<td\b/g) || []).length, 1);
assert.strictEqual((m71Html.match(/<input\b/gi) || []).length, 0);

const conditional = Object.assign({}, m70Contract, {
  active_when: { checkedKey: 'engine.ready' }
});
assert.strictEqual(OutputTable.renderOutputTable(conditional, {
  checks: { 'engine.ready': false }
}), '');
const activeHtml = OutputTable.renderOutputTable(conditional, {
  checks: { 'engine.ready': true }
});
assert.ok(activeHtml.includes('data-output-only="true"'));

const valueConditional = Object.assign({}, m71Contract, {
  active_when: { valueOf: { key: 'workflow.state', equals: ['READY'] } }
});
assert.strictEqual(OutputTable.renderOutputTable(valueConditional, {
  values: { 'workflow.state': 'pending' }
}), '');
assert.ok(OutputTable.renderOutputTable(valueConditional, {
  values: { 'workflow.state': ' READY ' }
}).includes('data-semantic-key="chu_ky_cqb_m71"'));

const escaped = OutputTable.renderOutputTable({
  kind: 'output-table',
  section_id: 'x" onmouseover="bad',
  semantic_key: '<key>',
  grid: { rows: 1, cols: 1, labels: ['<script>alert("x")</script>'] }
}, {});
assert.ok(escaped.includes('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'));
assert.ok(!escaped.includes('<script>'));
assert.strictEqual((escaped.match(/<input\b/gi) || []).length, 0);

console.log('PASS output-table production contract: PLI_M70/PLI_M71');
