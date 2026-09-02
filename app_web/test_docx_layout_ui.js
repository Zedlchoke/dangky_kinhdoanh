/* test_docx_layout_ui.js — Wave D batch 1, lane fix-docx-layout.
 * Khóa hành vi UI cho Class 4 (header 2 band) + mặt UI của Class 8
 * (checkbox). Harness chuỗi HTML thuần node (jsdom-free), cùng style với
 * test_layout_l2_render.js — KHÔNG GUI.
 *
 * [C4-BAND]  blocks có band:header (22 mẫu — khớp allowlist HEADER_BAND của
 *            tools/test_header_layout.py phía DOCX) phải render
 *            <table class="btable hdr-band">, ô TRÁI (42%) là tên
 *            DN/HKD đứng TRƯỚC ô PHẢI (58%) quốc hiệu; mẫu KHÔNG band
 *            (PLI_M02/PLI_M12/PLI_M72 — false positive theo test DOCX)
 *            KHÔNG được dính class hdr-band.
 * [C4-CSS]   style.css phải giữ: hdr-band KHÔNG viền (border:none), hình học
 *            42%/58%, vertical-align: bottom; .rn-u gạch chân dòng
 *            "Độc lập - Tự do - Hạnh phúc" của band phải.
 * [C8-CHK]   block t:chk render <label class="bchk"><input.chk-box> với
 *            trạng thái checked theo store; block p có run input.chk giữ
 *            cấu trúc attribute (đối ứng DOCX: 'X' chỉ đi kèm label cùng
 *            đoạn — phần structural DOCX đo ở tools/test_docx_layout_signatures.py).
 *
 * Chạy:  node app_web/test_docx_layout_ui.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');

const ROOT = path.join(__dirname, '..');
const BLOCKS_DIR = path.join(ROOT, 'app', 'data', 'blocks');
const CSS = fs.readFileSync(path.join(__dirname, 'ui', 'style.css'), 'utf8');

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) {
    passed++;
    console.log('PASS  ' + name);
  } else {
    failed++;
    console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : ''));
  }
}

function loadBlocks(id) {
  return JSON.parse(fs.readFileSync(path.join(BLOCKS_DIR, id + '.json'), 'utf8'));
}

// ---------------------------------------------- C4-BAND: corpus band header
const bandForms = [];
const noBandForms = [];
for (const f of fs.readdirSync(BLOCKS_DIR).filter(function (n) {
  return /^PL[I]{1,2}_M\d+\.json$/.test(n);
}).sort()) {
  const d = loadBlocks(f.replace(/\.json$/, ''));
  const has = (d.blocks || []).some(function (b) {
    return b && b.t === 'table' && b.band === 'header';
  });
  (has ? bandForms : noBandForms).push(f.replace(/\.json$/, ''));
}
check('C4 corpus: đúng 22 blocks JSON có band:header (khớp DOCX allowlist)',
  bandForms.length === 22, 'thấy ' + bandForms.length + ': ' + bandForms.join(','));

{
  const d = loadBlocks('PLII_M02');
  const store = R.newStore();
  const html = R.renderBlocks(d, store);
  const bandTbls = html.match(/<table class="btable hdr-band">[\s\S]*?<\/table>/g) || [];
  check('C4 PLII_M02: render đúng bảng hdr-band', bandTbls.length >= 1);
  const band = bandTbls[0] || '';
  const leftPos = band.indexOf('TÊN H');
  const rightPos = band.indexOf('CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM');
  check('C4 PLII_M02: band trái là TÊN HỘ/DN, phải là quốc hiệu',
    leftPos >= 0 && rightPos > leftPos,
    'left=' + leftPos + ' right=' + rightPos);
  check('C4 PLII_M02: dòng "Độc lập - Tự do - Hạnh phúc" nằm trong band phải',
    band.indexOf('Độc lập - Tự do - Hạnh phúc') > rightPos && rightPos >= 0);
  check('C4 PLII_M02: band không lẫn header grid khác (1 hàng table band)',
    (html.match(/btable hdr-band/g) || []).length === 1);
}

// mẫu KHÔNG band: không được dính class hdr-band
for (const fid of ['PLI_M02', 'PLI_M12', 'PLI_M72']) {
  if (bandForms.indexOf(fid) >= 0) continue; // nếu regen đổi tập band thì bỏ
  const html = R.renderBlocks(loadBlocks(fid), R.newStore());
  check('C4 ' + fid + ': không band -> không class hdr-band',
    html.indexOf('hdr-band') < 0);
}

// ---------------------------------------------- C4-CSS: pin hình học/borders
check('C4 css: table.hdr-band + td KHÔNG viền (border: none)',
  /table\.hdr-band,\s*table\.hdr-band td\s*\{\s*border:\s*none;/.test(CSS));
check('C4 css: hình học band 42% (ô trái)', /table\.hdr-band td:first-child\s*\{\s*width:\s*42%;\s*\}/.test(CSS));
check('C4 css: hình học band 58% (ô phải)', /table\.hdr-band td:last-child\s*\{\s*width:\s*58%;\s*\}/.test(CSS));
check('C4 css: band vertical-align: bottom', /table\.hdr-band td\s*\{\s*vertical-align:\s*bottom;\s*\}/.test(CSS));
check('C4 css: .rn-u gạch chân (dòng band phải)', /\.rn-u\s*\{[^}]*text-decoration:[^}]*underline/.test(CSS));

// ---------------------------------------------- C8-CHK: mặt UI checkbox
{
  const store = R.newStore();
  const html0 = R.renderBlocks({
    id: 'T_UI_CHK', ten_mau: 'test', blocks: [
      { t: 'chk', label: 'Có', key: 'chk_co' }
    ]
  }, store);
  check('C8 UI: block chk -> label.bchk + input.chk-box unchecked',
    html0.indexOf('<label class="bchk"><input type="checkbox" class="chk-box" data-key="chk_co">') >= 0
    && html0.indexOf(' checked') < 0);
  store.checks = { chk_co: true };
  const html1 = R.renderBlocks({
    id: 'T_UI_CHK', ten_mau: 'test', blocks: [
      { t: 'chk', label: 'Có', key: 'chk_co' }
    ]
  }, store);
  check('C8 UI: checked -> input mang checked, label giữ nguyên cùng đoạn',
    /<label class="bchk"><input type="checkbox" class="chk-box" data-key="chk_co" checked><span>Có<\/span><\/label>/.test(html1));
  // run input.chk inline (nguồn cùng dòng, vd ': Có □ Không □')
  const html2 = R.renderBlocks({
    id: 'T_UI_CHK2', ten_mau: 'test', blocks: [
      { t: 'p', align: 'left', runs: [
        { text: ': Có ' }, { input: { key: 'chk_khong', chk: true } },
        { text: ' Không ' }, { input: { key: 'chk_khong', chk: true } }
      ] }
    ]
  }, R.newStore());
  const inputs = (html2.match(/<input type="checkbox" class="chk-box" data-key="chk_khong"/g) || []).length;
  check('C8 UI: run input.chk inline giữ 2 checkbox cùng paragraph', inputs === 2);
}

console.log('-'.repeat(60));
console.log('Ket qua: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed === 0 ? 0 : 1);
