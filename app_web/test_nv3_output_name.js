/*
 * N-v3 (owner decision packet v7 — "Quyết định cuối" 2026-09-06):
 * PLI_M48 p17, PLI_M49 p9, PLI_M70 p14 — ô "TÊN DOANH NGHIỆP" trong khối
 * output của cơ quan được bind RENDER-TIME từ `dn.ten_tieng_viet`:
 *   - read-only: KHÔNG tạo input, KHÔNG tạo tab-stop, KHÔNG draft key mới;
 *   - giá trị lấy từ store tại thời điểm render (một lần nhập ở thân);
 *   - M49 PHÂN BIỆT NHÁNH: nhánh thành lập mới phần người nhận dùng dữ liệu
 *     CÁ NHÂN (không có mirror tên DN); chỉ nhánh doanh nghiệp HIỆN HỮU mới
 *     render tên DN;
 *   - thiếu giá trị canonical -> span RỖNG (blank pháp định), không in token
 *     kỹ thuật (undefined/null/NaN/{...}).
 *
 * CƠ CHẾ ĐÃ CÓ (không phải code mới): renderRun trong app_web/ui/render.js
 * xử lý run `{mirror: {key}}` -> span.mirror-fld data-key (WAVE v7
 * HEADER-NAME-SYNC, gate tools/audit_blocks_check.py
 * ALLOWED_RUN_KEYS_MIRROR = {'key'}); tools/header_name_binding.json là
 * nguồn chân lý bind band. 20/22 slot band đã bind; N-v3 mở rộng cơ chế này
 * sang các Ô OUTPUT của M48/M49/M70.
 *
 * *** NOTE HỢP ĐỒNG ***: blocks thật của M48/M49/M70 TRÊN NHÁNH NÀY chưa có
 * run mirror (verified: 0 mirror run trong app/data/blocks/{M48,M49,M70}.json
 * thời điểm viết test) — Lead sẽ regen blocks theo quyết định N-v3. Test này
 * MÔ PHỎNG entry blocks đúng HỢP ĐỒNG regen (run mirror {key:
 * 'dn.ten_tieng_viet'} tại ô output) và chốt hành vi render: sau khi Lead
 * merge blocks thật, cùng shape đó phải render đúng như dưới đây.
 *
 * Run: node app_web/test_nv3_output_name.js
 */
'use strict';

const R = require('./ui/render.js');

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else { failed++; console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

const TEN_DN = 'CÔNG TY TNHH MỘT HAI BA';

/* Ô output "TÊN …" đúng hợp đồng regen: run mirror {key} tại ô 'TÊN DOANH
 * NGHIỆP' của khối output cơ quan (M48 p17 / M70 p14 / M49 p9 - nhánh hiện hữu). */
function outputNameDoc(formId, opts) {
  opts = opts || {};
  const runs = [{ text: 'TÊN DOANH NGHIỆP: ', b: true }];
  if (!opts.noMirror) runs.push({ mirror: { key: 'dn.ten_tieng_viet' } });
  return {
    id: formId, ten_mau: 'nv3-fixture',
    blocks: [{
      t: 'table', band: null, widths: null,
      rows: [
        { cells: [
          { runs: runs.slice() },
          { runs: [{ text: '   ' }] }
        ] },
        { cells: [
          { runs: [{ text: 'Số: ………………………' }] },
          { runs: [{ text: 'CHỈ TRƯỞNG CƠ QUAN ĐĂNG KÝ KINH DOANH' }] }
        ] }
      ]
    }]
  };
}

function newStore() {
  const st = R.newStore();
  st.values['dn.ten_tieng_viet'] = TEN_DN;
  return st;
}

console.log('--- 1. M48/M70: ô output "TÊN DOANH NGHIỆP" render mirror read-only');
['PLI_M48', 'PLI_M70'].forEach(formId => {
  const st = newStore();
  const html = R.renderBlocks(outputNameDoc(formId), st);
  check(formId + ': mirror render span.mirror-fld với ĐÚNG giá trị store',
    html.indexOf('<span class="mirror-fld" data-key="dn.ten_tieng_viet">' +
      TEN_DN + '</span>') >= 0, html.slice(0, 240));
  check(formId + ': KHÔNG input nào cho dn.ten_tieng_viet (read-only, '
    + 'không tab-stop thứ hai)',
    (html.match(/<input[^>]*data-key="dn\.ten_tieng_viet"/g) || []).length === 0);
  check(formId + ': render không tạo draft key mới (store bất biến)',
    JSON.stringify(st) === JSON.stringify(newStore()));
});

console.log('--- 2. Giá trị canonical thiếu -> blank pháp định, không token kỹ thuật');
{
  const html = R.renderBlocks(outputNameDoc('PLI_M48'), R.newStore());
  check('M48: store trống -> span mirror rỗng',
    html.indexOf('<span class="mirror-fld" data-key="dn.ten_tieng_viet">' +
      '</span>') >= 0, html.slice(0, 240));
  check('M48: không in token kỹ thuật (undefined/null/NaN)',
    html.indexOf('undefined') < 0 && !/>\s*null\s*</.test(html) &&
      html.indexOf('NaN') < 0, html.slice(0, 240));
}

console.log('--- 3. M49 phân biệt nhánh');
{
  // Nhánh DOANH NGHIỆP HIỆN HỮU: run mirror tên DN.
  const hHienHuu = R.renderBlocks(outputNameDoc('PLI_M49'), newStore());
  check('M49 nhánh hiện hữu: render mirror dn.ten_tieng_viet đúng giá trị',
    hHienHuu.indexOf('<span class="mirror-fld" data-key="dn.ten_tieng_viet">' +
      TEN_DN + '</span>') >= 0, hHienHuu.slice(0, 240));

  // Nhánh THÀNH LẬP MỚI: blocks KHÔNG có mirror — ô output giữ line chờ /
  // dữ liệu cá nhân; tuyệt đối không render tên DN (còn không tồn tại).
  const stMoi = R.newStore();
  stMoi.values['dn.ten_tieng_viet'] = TEN_DN; // kyhan: key rỗng ở nhánh này
  const hMoi = R.renderBlocks(outputNameDoc('PLI_M49', { noMirror: true }), stMoi);
  check('M49 nhánh thành lập mới: KHÔNG mirror tên DN (dùng dữ liệu cá nhân)',
    hMoi.indexOf('mirror-fld') < 0 &&
      hMoi.indexOf(TEN_DN) < 0, hMoi.slice(0, 240));
}

console.log('--- 4. Mirror là cơ chế chung: đúng key canonical, không hard-code form');
{
  // Cùng run mirror trên form khác (PLII mirror key khác) vẫn render đúng —
  // cơ chế KHÔNG hard-code form_id (điều kiện để Lead regen hàng loạt).
  const doc = outputNameDoc('PLI_M48');
  doc.blocks[0].rows[0].cells[0].runs = [
    { text: 'TÊN HỘ KINH DOANH: ' },
    { mirror: { key: 'hkd_ten_tieng_viet_2' } }];
  const st = R.newStore();
  st.values['hkd_ten_tieng_viet_2'] = 'HỘ KHU BÁNH NGỌT HẢI PHÒNG';
  const html = R.renderBlocks(doc, st);
  check('mirror key khác (hkd) render đúng giá trị của key đó',
    html.indexOf('<span class="mirror-fld" data-key="hkd_ten_tieng_viet_2">' +
      'HỘ KHU BÁNH NGỌT HẢI PHÒNG</span>') >= 0, html.slice(0, 240));
}

console.log('----------------------------------------------------------------');
console.log('test_nv3_output_name: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
