// [N-v1/N-v2 2026-09-06] PLI_M33 + PLII_M06: band "TÊN ..." là Ô NHẬP DUY NHẤT
// (mode band_input). Contract: blocks band cell có ĐÚNG 1 run input registry
// key; render.js vẽ <input> editable; không mirror; blank draft → band trống
// (không dữ liệu giả); không có input/mirror trùng key ở thân mẫu.
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');
global.window = {};
const R = require(path.join(ROOT, 'app_web/ui/render.js'));

let passed = 0, failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; console.log('PASS ', name); }
  else { failed++; console.log('FAIL ', name, detail || ''); }
}

const CASES = [
  { fid: 'PLI_M33', key: 'dn.ten_tieng_viet', label: 'TÊN DOANH NGHIỆP' },
  { fid: 'PLII_M06', key: 'hkd_ten_tieng_viet_2', label: 'TÊN HỘ KINH DOANH' },
];

for (const c of CASES) {
  const blocks = JSON.parse(fs.readFileSync(
    path.join(ROOT, 'app/data/blocks/' + c.fid + '.json'), 'utf8'));
  const band = blocks.blocks.find(b => b.t === 'table' && b.band === 'header');
  check(c.fid + ': có band header', !!band);
  const runs = band.rows[0].cells[0].runs;
  const inputs = runs.filter(r => r.input).map(r => r.input.key);
  const mirrors = runs.filter(r => r.mirror).map(r => r.mirror.key);
  check(c.fid + ': band đúng 1 input registry key', JSON.stringify(inputs) === JSON.stringify([c.key]), inputs);
  check(c.fid + ': band không mirror', mirrors.length === 0, mirrors);
  // không trùng key ở thân mẫu (một nguồn nhập duy nhất)
  let bodyDup = 0;
  (function walk(bs) {
    for (const b of bs) {
      if (b.runs) bodyDup += b.runs.filter(r =>
        (r.input && r.input.key === c.key) || (r.mirror && r.mirror.key === c.key)).length;
      if (b.cells) for (const row of b.rows || []) for (const cell of row.cells || []) walk([]) /* cells handled via rows */;
      if (b.rows) for (const row of b.rows) for (const cell of row.cells || []) {
        if (cell.runs) bodyDup += cell.runs.filter(r =>
          (r.input && r.input.key === c.key) || (r.mirror && r.mirror.key === c.key)).length;
      }
      if (b.blocks) walk(b.blocks);
    }
  })(blocks.blocks);
  bodyDup -= 1; // trừ chính band input
  check(c.fid + ': không ô nhập/mirror thứ hai cùng key ở thân', bodyDup === 0, 'extra=' + bodyDup);
  // render: blank → input rỗng (không dữ liệu giả)
  const store0 = R.newStore();
  const html0 = R.renderBlocks({ id: c.fid, blocks: blocks.blocks }, store0);
  check(c.fid + ': render blank có input data-key', html0.indexOf('data-key="' + c.key + '"') >= 0);
  check(c.fid + ': render blank KHÔNG mirror span cùng key',
    html0.indexOf('mirror-fld" data-key="' + c.key + '"') < 0);
  // filled → giá trị vào value attribute của input (A→B qua store cùng key)
  const store1 = R.newStore();
  store1.values[c.key] = 'CÔNG TY TEST ABC';
  const html1 = R.renderBlocks({ id: c.fid, blocks: blocks.blocks }, store1);
  const m = html1.match(new RegExp('data-key="' + c.key + '"[^>]*value="([^"]*)"'));
  check(c.fid + ': filled → value đúng ở band', !!m && decodeURIComponent(m[1]) !== '' &&
    /CÔNG TY TEST ABC/.test(m[1].replace(/&amp;/g, '&').replace(/&#39;/g, "'")), m && m[1]);
}

console.log('-'.repeat(64));
console.log('test_nv1_nv2_band_input: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
