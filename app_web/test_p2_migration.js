/* test_p2_migration.js - locked P2 draft migration contract.
 *
 * Chạy: node app_web/test_p2_migration.js
 * Fixture rows follow production loop shapes; blocks are loaded directly from
 * app/data/blocks so this test does not invent a legal field mapping.
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const FD = require('./ui/form-domain.js');

const BLOCKS = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(BLOCKS, id + '.json'), 'utf8'));
}
function loopBlock(doc, name) {
  return (doc.blocks || []).find(b => b.t === 'loop' && b.loop === name);
}
function tagsOf(block) {
  return (block.cols || []).map(c => c.tag).filter(Boolean);
}

const m06 = loadProd('PLI_M06');
const members = loopBlock(m06, 'ds_thanh_vien');
assert(members, 'production PLI_M06 member loop is required by fixture');
assert(tagsOf(members).includes('ho_ten'), 'fixture uses a production member column');

const legacyRows = [
  { ma_nganh: '0111', ten_nganh: 'Trồng lúa', la_nganh_chinh: 'X', customCell: 'keep' },
  { ma_nganh: '4711', ten_nganh: 'Bán lẻ', la_nganh_chinh: '', customCell: 'keep-2' }
];
const memberRows = [
  { _row_id: 'member-stable-1', ho_ten: 'Nguyễn Văn A', so_cccd: '012345678901', von_dong_gop: '1000000', customCell: 'member' },
  { ho_ten: 'Trần Thị B', so_cccd: '012345678901', von_dong_gop: '2000000', customCell: 'member-2' }
];
const legacy = {
  v: 1,
  caseId: 'production-shaped-case',
  checkedForms: ['PLI_M06'],
  autoSum: true,
  futureTopLevel: { producer: 'newer-client', keep: true },
  store: {
    values: { 'dn.ten_tieng_viet': 'CÔNG TY MẪU', futureValue: 'keep' },
    checks: { 'legacy.check': true, futureCheck: false },
    loops: {
      ds_nganh_kinh_doanh: legacyRows,
      ds_thanh_vien: memberRows,
      future_loop_name: [{ future: 'row' }]
    },
    futureStoreField: { keep: 'store-extension' }
  }
};

const migrated = FD.migrateDraft(legacy);
assert.strictEqual(migrated.v, 2);
assert.strictEqual(migrated.activeDocId, null);
assert.deepStrictEqual(migrated.viewState, {});
assert.strictEqual(migrated.savedAt, null);

// Additive preservation: unknown fields, values, checks, loops and row cells.
assert.deepStrictEqual(migrated.futureTopLevel, legacy.futureTopLevel);
assert.strictEqual(migrated.store.futureStoreField.keep, 'store-extension');
assert.strictEqual(migrated.store.values.futureValue, 'keep');
assert.strictEqual(migrated.store.checks.futureCheck, false);
assert.strictEqual(migrated.store.loops.future_loop_name[0].future, 'row');
assert.strictEqual(migrated.store.loops.ds_thanh_vien[0].customCell, 'member');

// The only migration mapping is explicit and does not alter unrelated loops.
assert.strictEqual(migrated.store.loops.ds_nganh, legacyRows);
assert.strictEqual(migrated.store.loops.ds_nganh_kinh_doanh, undefined);
assert.strictEqual(migrated.store.loops.ds_nganh[0].customCell, 'keep');
assert.strictEqual(migrated.store.loops.ds_thanh_vien, memberRows);
assert.strictEqual(migrated.store.loops.future_loop_name[0].future, 'row');
assert(migrated.store.loops.ds_nganh.every(row => /^r\d+_/.test(row._row_id)));
assert.strictEqual(migrated.store.loops.ds_thanh_vien[0]._row_id, 'member-stable-1');
assert(/^r\d+_/.test(migrated.store.loops.ds_thanh_vien[1]._row_id));

const ids = {
  industry: migrated.store.loops.ds_nganh.map(row => row._row_id),
  members: migrated.store.loops.ds_thanh_vien.map(row => row._row_id)
};
assert.strictEqual(FD.migrateDraft(migrated), migrated);
assert.deepStrictEqual(migrated.store.loops.ds_nganh.map(row => row._row_id), ids.industry);
assert.deepStrictEqual(migrated.store.loops.ds_thanh_vien.map(row => row._row_id), ids.members);

// Canonical data wins; the legacy key is not deleted or merged implicitly.
const both = {
  v: 1,
  store: {
    values: {}, checks: {},
    loops: {
      ds_nganh: [{ ma_nganh: '9999', preserved: 'canonical' }],
      ds_nganh_kinh_doanh: [{ ma_nganh: '0111', preserved: 'legacy' }]
    }
  }
};
const bothOut = FD.migrateDraft(both);
assert.strictEqual(bothOut.store.loops.ds_nganh[0].preserved, 'canonical');
assert.strictEqual(bothOut.store.loops.ds_nganh_kinh_doanh[0].preserved, 'legacy');
assert.notStrictEqual(bothOut.store.loops.ds_nganh[0]._row_id, bothOut.store.loops.ds_nganh_kinh_doanh[0]._row_id);

console.log('P2 migration: PASS (additive, explicit, stable, idempotent)');
