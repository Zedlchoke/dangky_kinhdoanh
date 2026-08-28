/* Integration tests for the contract dispatcher in the production browser path. */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
function load(formId) {
  return JSON.parse(fs.readFileSync(
    path.join(BLOCKS, formId + '.json'), 'utf8'));
}

const m02 = load('PLI_M02');
const legacy = R.renderBlocks(m02, R.newStore());
assert.ok(legacy.includes('data-loop="ds_nganh"'));
assert.ok(!legacy.includes('data-component="output-table"'));

const outputContract = {
  kind: 'output-table',
  section_id: 'production-signatures',
  semantic_key: 'production_signature_grid',
  grid: { rows: 1, cols: 2, labels: ['NGƯỜI NỘP', 'NGƯỜI NHẬN'] }
};
const withMetadata = R.renderBlocks(m02, R.newStore(), {
  components: [outputContract]
});
assert.strictEqual(
  (withMetadata.match(/data-component="output-table"/g) || []).length, 1);
assert.ok(withMetadata.includes('NGƯỜI NỘP'));
assert.ok(withMetadata.includes('data-output-only="true"'));

const escaped = R.renderComponentContracts([{
  kind: 'output-table',
  section_id: '" onload="bad',
  semantic_key: '<bad>',
  grid: { rows: 1, cols: 1, labels: ['<script>alert(1)</script>'] }
}], R.newStore());
assert.ok(escaped.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
assert.ok(!escaped.includes('<script>'));

const calls = [];
const custom = R.renderComponentContracts([
  { kind: 'fixed-matrix', semantic_key: 'matrix-contract' },
  { kind: 'nested-grid', semantic_key: 'nested-contract' }
], { values: { preserved: 'yes' }, checks: {}, loops: {} }, {
  componentHandlers: {
    'fixed-matrix': function (contract, context) {
      calls.push([contract.kind, context.values.preserved]);
      return '<div data-component="fixed-matrix">matrix</div>';
    },
    'nested-grid': {
      render: function (contract, context) {
        calls.push([contract.kind, context.store.values.preserved]);
        return '<div data-component="nested-grid">nested</div>';
      }
    }
  }
});
assert.ok(custom.includes('data-component="fixed-matrix"'));
assert.ok(custom.includes('data-component="nested-grid"'));
assert.deepStrictEqual(calls, [
  ['fixed-matrix', 'yes'], ['nested-grid', 'yes']
]);

const index = fs.readFileSync(path.join(__dirname, 'ui', 'index.html'), 'utf8');
assert.ok(index.indexOf('src="output-table.js"') <
  index.indexOf('src="render.js"'));

console.log('PASS component dispatch: metadata, escaping, legacy, custom handlers');
