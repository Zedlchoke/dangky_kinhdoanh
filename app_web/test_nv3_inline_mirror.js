/*
 * N-v3 (owner decision 2026-09-06): occurrence output "Tên doanh nghiệp"
 * PLI_M48 p17 / PLI_M49 p9 (NHÁNH doanh nghiệp hiện hữu) / PLI_M70 p14 —
 * bind RENDER-TIME từ `dn.ten_tieng_viet`, READ-ONLY (mirror):
 *   - render run {"mirror":{"key":"dn.ten_tieng_viet"}} -> span.mirror-fld
 *     data-key với ĐÚNG giá trị store (một lần nhập ở thân/draft case);
 *   - KHÔNG tạo <input> cùng key (không tab-stop/validation/draft thứ hai);
 *   - store không bị render đụng vào (không draft key mới);
 *   - draft thiếu canonical -> span RỖNG (blank pháp định), không in token
 *     kỹ thuật (undefined/null/NaN);
 *   - M49 PHÂN BIỆT NHÁNH: mirror nằm SAU marker "(Đối với các trường hợp
 *     còn lại)"; nhánh thành lập mới giữ nguyên input dữ liệu cá nhân và
 *     KHÔNG render tên DN.
 *
 * NGUỒN blocks: đọc app/data/blocks/{fid}.json THẬT. Nếu Lead đã regen
 * (blocks chứa đúng 1 run mirror) -> test trên artifact thật; nếu chưa ->
 * dùng fixture HỢP ĐỒNG nhúng dưới đây (trích nguyên runs của blocks regen
 * theo registry tools/header_name_binding.json section "output_mirrors")
 * để chốt hành vi render ngay từ branch. Cả hai đường đều phải PASS.
 *
 * Run: node app_web/test_nv3_inline_mirror.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else { failed++; console.log('FAIL  ' + name + (extra ? '  [' + extra + ']' : '')); }
}

const KEY = 'dn.ten_tieng_viet';
const TEN_DN = 'CÔNG TY TNHH MỘT HAI BA';

/* Fixture HỢP ĐỒNG — nguyên runs của block chứa mirror trong blocks regen
 * (registry output_mirrors). Chỉ dùng khi app/data/blocks chưa regen. */
const FIXTURE_RUNS = {
  PLI_M48: [
    { text: 'về việc: ' }, { input: { key: 've_viec', w: 12 } },
    { text: ' của ' }, { mirror: { key: KEY } },
    { text: ' Mã số doanh nghiệp (' }, { text: 'nếu có', i: true },
    { text: '): ' }, { input: { key: 'dn.ma_so_dn', w: 23 } }
  ],
  PLI_M49: [
    { text: '(' }, { text: 'Đối với hồ sơ thành lập mới doanh nghiệp', i: true },
    { text: ')\nÔng/Bà: ………………………………………………………. \nSố giấy tờ pháp lý của cá nhân: ' },
    { input: { key: 'so_giay_to_ca_nhan', w: 60 } },
    { text: '\nĐịa chỉ liên lạc: ' }, { input: { key: 'dia_chi_lien_lac', w: 17 } },
    { text: '\n(' }, { text: 'Đối với các trường hợp còn lại', i: true },
    { text: ')\n' }, { mirror: { key: KEY } }, { text: '\n', i: true },
    { text: 'Địa chỉ trụ sở chính:' }, { text: ' ', i: true },
    { input: { key: 'dn.dia_chi_tru_so', w: 19 } }, { text: '\n', i: true },
    { text: 'Mã số doanh nghiệp/Số Giấy chứng nhận đăng ký kinh doanh đối với doanh nghiệp: ' },
    { input: { key: 'dn.ma_so_dn', w: 48 } }
  ],
  PLI_M70: [
    { text: 'Điện thoại: ' }, { input: { key: 'dien_thoai_khac', w: 14 } },
    { text: ' Thư điện tử: ' }, { input: { key: 'email_khac', w: 15 } },
    { text: ' 01 bộ hồ sơ đăng ký doanh nghiệp/chi nhánh/văn phòng đại diện/địa điểm kinh doanh mã số: ……………. về việc ' },
    { input: { key: 've_viec', w: 60 } },
    { text: ' của ' }, { mirror: { key: KEY } },
    { text: ' Mã số doanh nghiệp (' }, { text: 'nếu có', i: true },
    { text: '): ' }, { input: { key: 'dn.ma_so_dn', w: 23 } }
  ]
};

/* Đọc blocks thật; nếu đã regen (đúng 1 mirror + 0 input cùng key) trả
 * {runs, real: true}, không thì fixture {runs, real: false}. */
function occurrenceRuns(formId) {
  const p = path.join(__dirname, '..', 'app', 'data', 'blocks',
    formId + '.json');
  try {
    const data = JSON.parse(fs.readFileSync(p, 'utf8'));
    const found = [];
    let inputs = 0;
    (data.blocks || []).forEach(function (blk) {
      const rows = blk.t === 'p' ? [{ cells: [{ runs: blk.runs || [] }] }]
        : (blk.t === 'table' ? (blk.rows || []) : []);
      rows.forEach(function (row) {
        (row.cells || []).forEach(function (cell) {
          (cell.runs || []).forEach(function (r) {
            if (r.mirror && r.mirror.key === KEY) found.push(runsOf(blk, cell));
            if (r.input && r.input.key === KEY) inputs++;
          });
        });
      });
    });
    function runsOf(blk, cell) { return cell.runs; }
    if (found.length === 1 && inputs === 0) {
      return { runs: found[0], real: true };
    }
  } catch (e) { /* chưa có file / chưa regen -> fixture */ }
  return { runs: FIXTURE_RUNS[formId], real: false };
}

function docWith(runs) {
  return {
    id: 'nv3-fixture', ten_mau: 'nv3-inline-mirror',
    blocks: [{ t: 'p', align: 'left', runs: runs }]
  };
}

function stripTags(html) { return html.replace(/<[^>]+>/g, ''); }

console.log('--- 1. Mirror output render span.mirror-fld ĐÚNG vị trí + giá trị');
['PLI_M48', 'PLI_M49', 'PLI_M70'].forEach(function (fid) {
  const occ = occurrenceRuns(fid);
  const st = R.newStore();
  st.values[KEY] = TEN_DN;
  const html = R.renderBlocks(docWith(occ.runs), st);
  const tag = '<span class="mirror-fld" data-key="' + KEY + '">' + TEN_DN + '</span>';
  check(fid + ': span.mirror-fld data-key giá trị store (' +
    (occ.real ? 'blocks THẬT' : 'fixture hợp đồng') + ')',
    html.indexOf(tag) >= 0, html.slice(0, 200));
  // vị trí đúng occurrence: M48/M70 sau ' của ', M49 sau marker nhánh DN
  const before = fid === 'PLI_M49'
    ? html.indexOf('Đối với các trường hợp còn lại') : html.indexOf(' của ');
  check(fid + ': mirror nằm ĐÚNG sau ngữ cảnh occurrence',
    before >= 0 && html.indexOf(tag) > before, html.slice(0, 200));
  // READ-ONLY: không input nào cùng key
  check(fid + ': KHÔNG <input> data-key="' + KEY + '" (read-only)',
    (html.match(new RegExp('<input[^>]*data-key="' +
      KEY.replace(/\./g, '\\.') + '"', 'g')) || []).length === 0);
  // render không đụng store (không draft key mới)
  const expected = {};
  expected[KEY] = TEN_DN;
  check(fid + ': store bất biến sau render',
    JSON.stringify(st.values) === JSON.stringify(expected),
    JSON.stringify(st.values));
});

console.log('--- 2. Draft thiếu canonical -> span RỖNG (blank pháp định)');
['PLI_M48', 'PLI_M49', 'PLI_M70'].forEach(function (fid) {
  const occ = occurrenceRuns(fid);
  const html = R.renderBlocks(docWith(occ.runs), R.newStore());
  check(fid + ': store trống -> span mirror rỗng, không token kỹ thuật',
    html.indexOf('<span class="mirror-fld" data-key="' + KEY + '"></span>') >= 0 &&
    html.indexOf('undefined') < 0 && html.indexOf('NaN') < 0 &&
    !/null/.test(html), html.slice(0, 200));
});

console.log('--- 3. M49 phân biệt nhánh: cá nhân nhập riêng, DN ở nhánh hiện hữu');
{
  const occ = occurrenceRuns('PLI_M49');
  const st = R.newStore();
  st.values[KEY] = TEN_DN;
  st.values['so_giay_to_ca_nhan'] = '012345678901';
  const html = R.renderBlocks(docWith(occ.runs), st);
  const iMark = html.indexOf('Đối với các trường hợp còn lại');
  const iMirror = html.indexOf('mirror-fld');
  const iCccd = html.indexOf('data-key="so_giay_to_ca_nhan"');
  check('M49: input dữ liệu cá nhân vẫn là <input> editable',
    iCccd > 0 && iCccd < iMark);
  check('M49: mirror tên DN nằm SAU marker nhánh DN (không lẫn nhánh cá nhân)',
    iMark >= 0 && iMirror > iMark);
  check('M49: đúng 1 mirror trong toàn form',
    (html.match(/mirror-fld/g) || []).length === 1);
  check('M49: giá trị cá nhân và tên DN cùng render đúng',
    html.indexOf('012345678901') > 0 &&
      html.indexOf(TEN_DN) > iMark);
}

console.log('--- 4. Mirror đồng bộ store: đổi giá trị -> render theo giá trị mới');
{
  const occ = occurrenceRuns('PLI_M48');
  const st = R.newStore();
  st.values[KEY] = 'TÊN CŨ';
  const h1 = R.renderBlocks(docWith(occ.runs), st);
  st.values[KEY] = 'TÊN MỚI';           // render lại từ store (không stale)
  const h2 = R.renderBlocks(docWith(occ.runs), st);
  check('M48: đổi store -> render CHỈ còn giá trị mới (không stale)',
    h1.indexOf('TÊN CŨ') >= 0 && h2.indexOf('TÊN CŨ') < 0 &&
      h2.indexOf('TÊN MỚI') >= 0 && stripTags(h2).indexOf('TÊN MỚI') >= 0);
}

console.log('----------------------------------------------------------------');
console.log('test_nv3_inline_mirror: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
