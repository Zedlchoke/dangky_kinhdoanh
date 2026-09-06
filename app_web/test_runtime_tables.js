/* test_runtime_tables.js - Wave B1 (R2 runtime wiring): dispatcher theo
 * section.kind cho fixed-matrix / nested-grid / output-table.
 *
 * Chạy:  node app_web/test_runtime_tables.js
 *
 * Harness giống test_dom/test_layout_l2_render: jsdom-free, kiểm tra trên
 * CHUỖI HTML sinh ra + hàm thuần trong ui/render.js, ui/form-domain.js,
 * ui/app.js (Helpers qua require) và 3 platform module CHỈ được require/gọi.
 *
 * Phủ:
 *  1. index.html nạp đúng thứ tự dependency; shim CommonJS không rò rỉ global
 *     `module`; toàn chuỗi nạp được trong mô phỏng browser (node vm).
 *  2. Dispatcher: editable-grid/schema legacy giữ nguyên; kind mới đi đúng
 *     module của nó; contract hỏng -> degrade giữ blocks cũ (không nuốt UI).
 *  3. Controller: CRUD policy theo kind (fixed-matrix không xóa dòng pháp lý;
 *     nested-grid add/delete giữ _row_id; output-table không có input nào).
 *  4. Validation qua FormDomain: MONEY/PERCENT_SUM/CAPITAL_MISMATCH đúng
 *     severity contract; tổng là projection recompute (không hai nguồn số).
 *  5. Draft round-trip qua migrateDraft: giá trị phẳng + loops/_row_id +
 *     unknown field đều sống sót, idempotent, không sinh dữ liệu giả vào
 *     section inactive.
 *  6. Fixture production tối thiểu O1 PLI_M70 / O2 PLI_M71 / F2 PLI_M03 /
 *     F3 PLI_M04 / N1 PLI_M02 đối chiếu chéo với app/data/table_specs/
 *     manifest.json (chống trôi schema).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const UI = path.join(__dirname, 'ui');

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const H = require('./ui/app.js');            // Helpers thuần (IS_NODE mode)
const Matrix = require('./ui/fixed-matrix.js');
const NestedGrid = require('./ui/nested-grid.js');
const OutputTable = require('./ui/output-table.js');

function read(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}
function loadBlocks(id) {
  return read(path.join(ROOT, 'app', 'data', 'blocks', id + '.json'));
}

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
function section(name) {
  console.log('\n--- ' + name + ' ---');
}

function emptyStore(values, loops) {
  return { values: values || {}, checks: {}, loops: loops || {} };
}

/* ------------------------------------------------------------------ 0. fixtures */
const MANIFEST = read(path.join(ROOT, 'app', 'data', 'table_specs',
  'manifest.json'));
const FIXTURES = [
  ['PLI_M70', 'chu_ky_nguoi_nop_nguoi_nhan', 'output-table'],
  ['PLI_M71', 'chu_ky_co_quan_cap_tinh', 'output-table'],
  ['PLI_M03', 'nguon_von_dieule', 'fixed-matrix'],
  ['PLI_M04', 'co_cau_loai_co_phan', 'fixed-matrix'],
  ['PLI_M02', 'nddpl_uy_quyen_chu_so_huu', 'nested-grid'],
  /* R3B1 (2026-08-27): người đại diện ủy quyền — D2.1=A, D2.4=A, D2.7=A */
  ['PLI_M12', 'ndd_uy_quyen_sau_thay_doi', 'nested-grid'],
  ['PLI_M15', 'ndd_pl_uy_quyen_chu_so_huu_moi', 'nested-grid'],
  /* P2C (merge 1691728 + Lead wire): D1.1=A/D1.2=B — fixed-matrix nguồn vốn
   * và tài sản góp vốn; M02 nguồn vốn dùng cùng key canonical với F2(M03). */
  ['PLI_M01', 'tai_san_gop_von_von_dau_tu', 'fixed-matrix'],
  ['PLI_M02', 'nguon_von_dieule', 'fixed-matrix'],
  ['PLI_M02', 'tai_san_gop_von_von_dieu_le', 'fixed-matrix'],
  /* Wave cap-von + m09-rebuild (Lead wire @ fc07c69/cfdefcd, lệnh owner
   * 2026-08-28): nguồn vốn M03/M04/M05/M12 theo TT 121/2026; thuế PLII_M02
   * D5.2 (mục 5 phần C — 5.1/5.2/chỉ tiêu khác). */
  ['PLI_M05', 'nguon_von_dieule', 'fixed-matrix'],
  ['PLI_M12', 'nguon_von_dieule_sau_thay_doi', 'fixed-matrix'],
  ['PLI_M04', 'co_phan_duoc_quyen_chao_ban', 'fixed-matrix'],
  ['PLII_M02', 'a7_thue_chi_tieu_cu_moi', 'fixed-matrix'],
  /* F1-IN (2026-09-06, O1): +M12 2 tài sản/cổ phần, +C5 cấp đổi PLII_M02,
   * +M78 sản phẩm cung cấp thông tin (D6.4). */
  ['PLI_M12', 'tai_san_gop_von_sau_thay_doi_vdl', 'fixed-matrix'],
  ['PLI_M12', 'tai_san_gop_von_sau_thay_doi_von_dau_tu', 'fixed-matrix'],
  ['PLI_M12', 'co_cau_loai_co_phan_sau_thay_doi', 'fixed-matrix'],
  ['PLII_M02', 'c5_thue_chi_tieu_cap_doi', 'fixed-matrix'],
  ['PLI_M78', 'san_pham_cung_cap_thong_tin', 'fixed-matrix']
];

section('6. registry khớp census manifest (không tự chế section/kind)');
FIXTURES.forEach(function ([formId, sectionId, kind]) {
  const form = MANIFEST.forms.filter(f => f.form_id === formId)[0];
  const sec = form && form.sections.filter(s => s.section_id === sectionId)[0];
  check(formId + '/' + sectionId + ' tồn tại trong manifest', !!sec);
  if (!sec) return;
  check(formId + '/' + sectionId + ' kind == census', sec.kind === kind,
    'manifest=' + sec.kind);
  const entry = FD.getSectionContract(formId, sectionId);
  check(formId + '/' + sectionId + ' đã đăng ký runtime', !!entry);
  if (!entry) return;
  check(formId + '/semanticKey khớp manifest',
    entry.semanticKey === sec.semantic_key,
    entry.semanticKey + ' != ' + sec.semantic_key);
  check(formId + '/spec.kind trùng entry.kind', entry.spec.kind === kind);
});
check('PLI_M72 KHÔNG bị đăng ký kind mới (cô lập editable-grid/M72)',
  !FD.FORM_TABLE_CONTRACTS.PLI_M72);
check('danh sách mẫu đăng ký đúng ' + FIXTURES.length + ' fixture',
  Object.keys(FD.FORM_TABLE_CONTRACTS).sort().join(',') ===
  [...new Set(FIXTURES.map(f => f[0]))].sort().join(','));

/* ---------------------------------------------- 1. index.html + vm load order */
section('1. index.html nạp script đúng thứ tự dependency');
const html = fs.readFileSync(path.join(UI, 'index.html'), 'utf8');
const srcOrder = [];
const tagRe = /<script\b[^>]*\bsrc="([^"]+)"/g;
let mTag;
while ((mTag = tagRe.exec(html))) srcOrder.push(mTag[1]);
const posOf = n => srcOrder.indexOf(n);
check('có cả 5 script runtime trong index.html',
  ['fixed-matrix.js', 'nested-grid.js', 'output-table.js', 'form-domain.js',
    'render.js', 'app.js'].every(n => posOf(n) >= 0));
check('thứ tự: fixed-matrix -> nested-grid -> output-table -> form-domain',
  posOf('fixed-matrix.js') < posOf('nested-grid.js') &&
  posOf('nested-grid.js') < posOf('output-table.js') &&
  posOf('output-table.js') < posOf('form-domain.js'),
  JSON.stringify(srcOrder));
check('form-domain -> render -> app (smoke_web_assets lock)',
  posOf('form-domain.js') < posOf('render.js') &&
  posOf('render.js') < posOf('app.js'));
check('shim CommonJS đứng TRƯỚC fixed-matrix và sau nested-grid',
  html.indexOf('window.module = { exports: {} }') >= 0 &&
  html.indexOf('delete window.module') >= 0);

/* Mô phỏng browser: chạy từng <script> theo đúng thứ tự xuất hiện trong
 * index.html (kể cả inline shim xen giữa) trong một vm context riêng. */
function simulateBrowserLoad() {
  const sandbox = {
    console: { debug: () => {}, warn: () => {}, log: () => {} },
    document: { addEventListener: () => {} }
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);

  const loaded = [];
  const tagReAll = /<script\b([^>]*)>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = tagReAll.exec(html))) {
    const attrs = m[1];
    const body = m[2].trim();
    const srcM = attrs.match(/src="([^"]+)"/);
    if (srcM) {
      const file = path.join(UI, srcM[1]);
      if (!fs.existsSync(file)) continue;   // asset ngoài phạm vi test này
      vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox,
        { filename: srcM[1] });
      loaded.push(srcM[1]);
      continue;
    }
    vm.runInContext(body, sandbox, { filename: '<inline#' + loaded.length + '>' });
  }
  return { sandbox, loaded };
}

section('1b. mô phỏng nạp browser (vm) - globals phải sẵn sàng cho runtime');
const sim = simulateBrowserLoad();
const sb = sim.sandbox;
check('P2Tables.FixedMatrix gắn qua shim', typeof (
  sb.P2Tables && sb.P2Tables.FixedMatrix) === 'object' &&
  typeof (sb.P2Tables && sb.P2Tables.FixedMatrix.setCell) === 'function');
check('P2Tables.NestedGrid gắn qua shim', typeof (
  sb.P2Tables && sb.P2Tables.NestedGrid) === 'object' &&
  typeof (sb.P2Tables && sb.P2Tables.NestedGrid.headerLayout) === 'function');
check('OutputTable UMD tự gắn window.OutputTable',
  typeof (sb.OutputTable && sb.OutputTable.renderOutputTable) === 'function');
check('shim không rò rỉ global `module` sau khi nạp xong',
  sb.module === undefined, String(sb.module));
check('toàn chuỗi runtime nạp xong: Render/FormDomain/ControllerHelpers',
  !!(sb.Render && sb.FormDomain && sb.ControllerHelpers));
check('FormDomain trong browser resolve module từ global (không degrade)',
  (() => {
    try {
      const st = emptyStore({
        'nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong': 'abc'
      });
      const errs = sb.FormDomain.validateFormSections('PLI_M03', st);
      return errs.some(e => e.code === 'MONEY');
    } catch (e) { return 'throw: ' + e.message; }
  })());
check('Render trong browser nhận đúng module từ global (component xuất hiện)',
  (() => {
    try {
      const doc = loadBlocks('PLI_M70');
      const out = sb.Render.renderBlocks(doc, emptyStore(), {
        docId: 'PLI_M70', sectionContracts: sb.FormDomain.sectionContractsOf('PLI_M70')
      });
      return out.indexOf('data-component="output-table"') >= 0;
    } catch (e) { return 'throw: ' + e.message; }
  })());

/* --------------------------------------------------- 2. dispatcher render */
section('2. dispatcher theo section.kind');
function renderDoc(docId, store, opts) {
  const doc = loadBlocks(docId);
  const o = Object.assign({ docId, fieldMeta: FD.FIELD_META }, opts || {});
  return R.renderBlocks(doc, store, o);
}

// --- editable-grid không đổi: không truyền contracts vs truyền [] như nhau
{
  const st = emptyStore();
  const base = renderDoc('PLI_M03', st);
  const withEmpty = renderDoc('PLI_M03', st, { sectionContracts: [] });
  check('không đăng ký sectionContracts => HTML giữ nguyên bit-to-bit',
    base === withEmpty);
  check('không có component khi chưa đăng ký',
    base.indexOf('data-component=') < 0);
  check('blocks paragraph nguồn còn hiển thị bình thường',
    base.indexOf('>Vốn tư nhân<') >= 0);

  // M72 cô lập: chọn selector loại hình rồi render - grid editable-grid phải
  // đi ĐÚNG đường cũ, không có component kind mới nào xuất hiện.
  const m72Store = emptyStore({ 'dn.loai_hinh': 'CTCP' }, {
    ds_nganh_ctcp: [{ _row_id: 'r1_x', ma_nganh: '01110' }]
  });
  const m72flags = { loai_hinh_dntn: '', loai_hinh_tnhh_1tv: '',
    loai_hinh_tnhh_2tv: '', loai_hinh_ctcp: 'X', loai_hinh_dhdn: '' };
  const m72a = renderDoc('PLI_M72', m72Store,
    { flags: m72flags, gridMeta: null });
  const m72b = renderDoc('PLI_M72', m72Store,
    Object.assign({ sectionContracts: [] }, { flags: m72flags }));
  check('PLI_M72 render giống hệt khi opts.sectionContracts=[]', m72a === m72b);
  check('PLI_M72 vẫn là loop-table editable-grid thông thường',
    m72b.indexOf('class="btable loop-table"') >= 0 &&
    m72b.indexOf('[+ Thêm dòng]') >= 0 &&
    m72b.indexOf('data-component=') < 0);
}

// --- fixed-matrix F2: dữ liệu thật nhỏ (điền 1 dòng vốn tư nhân)
{
  const store = emptyStore({
    'nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong': '60.000.000',
    'nguon_von_dieu_le.von_tu_nhan.ty_le': '100'
  });
  const out = renderDoc('PLI_M03', store,
    { sectionContracts: FD.sectionContractsOf('PLI_M03') });
  check('F2: component fixed-matrix xuất hiện',
    out.indexOf('data-component="fixed-matrix"') >= 0);
  check('F2: đủ 5 dòng pháp lý kể cả dòng trống',
    (out.match(/data-fixed-row="/g) || []).length === 8, // 4 dòng nhập x 2 cột
    String((out.match(/data-fixed-row="/g) || []).length));

  // Đếm chính xác bằng số <tr> của bảng component
  const tblStart = out.indexOf('<table class="btable component-table"');
  const tblEnd = out.indexOf('</tbody></table>', tblStart);
  const tbl = out.slice(tblStart, tblEnd);
  const rowCount = (tbl.match(/<tr data-row-id=/g) || []).length;
  check('F2: bảng component có đúng 5 <tr>', rowCount === 5, String(rowCount));
  check('F2: nhãn pháp lý render đúng từ blocks nguồn',
    ['Vốn ngân sách nhà nước', 'Vốn tư nhân', 'Vốn nước ngoài', 'Vốn khác',
      'Tổng cộng'].every(lb => tbl.indexOf('>' + lb + '</td>') >= 0));
  check('F2: chỉ 4 dòng nhập có input (dòng tổng là outputOnly)',
    (tbl.match(/<input/g) || []).length === 8, String((tbl.match(/<input/g) || []).length));
  check('F2: dòng tổng mang data-total-row và KHÔNG input',
    tbl.indexOf('data-total-row="true"') >= 0 &&
    (() => {
      const i = tbl.indexOf('data-total-row="true"');
      const j = tbl.indexOf('</tr>', i);
      return tbl.slice(i, j).indexOf('<input') < 0;
    })());
  check('F2: tổng là projection recompute (60.000.000 | 100)',
    tbl.indexOf('data-computed-key="nguon_von_dieu_le.tong_cong.so_tien_vnd_va_tuong_duong">60.000.000</td>') >= 0 &&
    tbl.indexOf('data-computed-key="nguon_von_dieu_le.tong_cong.ty_le">100</td>') >= 0);
  check('F2: KHÔNG nút thêm/xóa/sắp xếp dòng nào',
    tbl.indexOf('[+ Thêm dòng]') < 0 && tbl.indexOf('[- Xóa dòng]') < 0 &&
    tbl.indexOf('data-act=') < 0);
  check('F2: blocks paragraph cũ bị ẩn (.dupe-anchor) nên không hiển thị 2 lần',
    (out.match(/class="dupe-anchor"/g) || []).length > 0);
}

// --- fixed-matrix F3: cơ cấu loại cổ phần (điền cổ phần phổ thông)
{
  const store = emptyStore({
    'co_cau_loai_co_phan.co_phan_pho_thong.so_luong': '1000000',
    'co_cau_loai_co_phan.co_phan_pho_thong.gia_tri_vnd': '1000000000'
  });
  const out = renderDoc('PLI_M04', store,
    { sectionContracts: FD.sectionContractsOf('PLI_M04') });
  check('F3: component fixed-matrix xuất hiện trong PLI_M04',
    out.indexOf('data-component="fixed-matrix"') >= 0);
  check('F3: STT generated tự đánh số', out.indexOf('<td class="stt">1</td>') >= 0);
  check('F3: các mẫu khác cùng form KHÔNG bị dispatch (lua_chon) — chao_ban ĐÃ wire (cap-von fc07c69)',
    out.indexOf('data-semantic-key="lua_chon_khu_san_xuat"') < 0 &&
    out.indexOf('data-semantic-key="co_phan_duoc_quyen_chao_ban"') >= 0);
  const proj = FD.recomputeSections('PLI_M04', store);
  check('F3: tổng số lượng/giá trị được recompute từ công thức khai',
    proj['co_cau_loai_co_phan.tong_so.so_luong'].value === 1000000 &&
    proj['co_cau_loai_co_phan.tong_so.gia_tri_vnd'].value === 1000000000);
}

// --- nested-grid N1
{
  const loop = 'ds_nddpl_uy_quyen_chu_so_huu';
  const store = emptyStore({}, {
    [loop]: [
      { _row_id: 'rA', loai_dong: 'ndd_uy_quyen', ten_nguoi_dai_dien: 'NGUYEN A' },
      { _row_id: 'rB', loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'TRAN B' }
    ]
  });
  const out = renderDoc('PLI_M02', store,
    { sectionContracts: FD.sectionContractsOf('PLI_M02') });
  check('N1: component nested-grid xuất hiện',
    out.indexOf('data-component="nested-grid"') >= 0);
  const tStart = out.indexOf('<thead><tr><th rowspan="2">STT</th>');
  const tEnd = out.indexOf('</table>', tStart);
  const tbl = out.slice(tStart, tEnd);
  check('N1: header nhiều hàng vật lý - rowspan/colspan giữ nguyên',
    tStart >= 0 && (tbl.match(/rowspan="2"/g) || []).length >= 9 &&
    tbl.indexOf('colspan="3"') >= 0 && tbl.indexOf('colspan="2"') >= 0);
  const layout = NestedGrid.headerLayout(
    FD.getSectionContract('PLI_M02', 'ds_nddpl_uy_quyen_chu_so_huu').spec);
  check('N1: số cột vật lý khai khớp layout (headerLayout 0 lỗi)',
    layout.errors.length === 0 && layout.columns.length === 14,
    'cols=' + layout.columns.length);
  check('N1: body mỗi dòng mang _row_id ổn định từ store',
    tbl.indexOf('data-row-id="rA"') >= 0 && tbl.indexOf('data-row-id="rB"') >= 0);
  check('N1: vai trò dòng (discriminator) là select canonical, nhúng ô STT '
    + 'KHÔNG lệch cột vật lý',
    (() => {
      const body = out.slice(out.indexOf('<tbody>', out.indexOf(
        '<table class="btable loop-table component-table"')));
      return body.indexOf('class="fld ng-discriminator"') >= 0 &&
        body.indexOf('<option value="ndd_uy_quyen" selected>') >= 0 &&
        body.indexOf('<option value="ndd_pl" selected>') >= 0;
    })());
  check('N1: policy cho phép thêm/xóa dòng (nút action có mặt)',
    out.slice(tEnd).indexOf('[+ Thêm dòng]') >= 0 &&
    out.slice(tEnd).indexOf('[- Xóa dòng]') >= 0);
  check('N1: cột outputOnly (chu_ky) KHÔNG sinh input',
    (() => {
      const cells = tbl.slice(tbl.indexOf('<tbody>'));
      const i = cells.indexOf('data-tag="chu_ky"');
      return i < 0; // chu_ky outputOnly => không bao giờ có input
    })());
  check('N1: ô nhập theo key lặp chuẩn (controller dùng lại đường cũ)',
    tbl.indexOf('"data-key="loop:' + loop + ':0:ten_nguoi_dai_dien"'.replace('"', '') ) >= 0 ||
    tbl.indexOf('loop:' + loop + ':0:ten_nguoi_dai_dien') >= 0);
}

// --- degrade an toàn khi contract hỏng
{
  const entry = JSON.parse(JSON.stringify(
    FD.getSectionContract('PLI_M02', 'ds_nddpl_uy_quyen_chu_so_huu')));
  entry.spec.header_rows = [[{ text: 'broken', colspan: 99 }]];
  const got = R.renderSectionComponentHtml(entry, {
    getVal: () => '', getChk: () => false, storeRef: emptyStore()
  }, { ids: {}, docId: 'PLI_M02', fieldMeta: null });
  check('N1: contract hỏng -> builder trả "" (giữ blocks cũ, không crash)',
    got === '');
  const otEntry = JSON.parse(JSON.stringify(
    FD.getSectionContract('PLI_M70', 'chu_ky_nguoi_nop_nguoi_nhan')));
  otEntry.kind = 'mystery-kind';
  check('kind lạ -> dispatcher trả "" (KHÔNG nuốt pipeline)',
    R.renderSectionComponentHtml(otEntry, {
      getVal: () => '', getChk: () => false, storeRef: emptyStore()
    }, { ids: {} }) === '');
  check('kind editable-grid ở cấp section -> dispatcher trả "" (đường cũ lo)',
    R.renderSectionComponentHtml(Object.assign({}, otEntry, { kind: 'editable-grid' }),
      { getVal: () => '', getChk: () => false, storeRef: emptyStore() },
      { ids: {} }) === '');
}

// --- output-table O1/O2
function componentMarkup(out) {
  const start = out.indexOf('<table class="btable output-table"');
  if (start < 0) return '';
  const end = out.indexOf('</table>', start);
  return out.slice(start, end < 0 ? out.length : end + '</table>'.length);
}
section('3. output-table: không input nào nhưng grid vẫn xuất hiện');
{
  ['PLI_M70', 'PLI_M71'].forEach(fid => {
    const out = renderDoc(fid, emptyStore(),
      { sectionContracts: FD.sectionContractsOf(fid) });
    const comp = componentMarkup(out);
    check(fid + ': grid output-table render ra', comp.length > 0);
    check(fid + ': KHÔNG sinh bất kỳ input/textarea/select nào',
      comp.indexOf('<input') < 0 && comp.indexOf('<select') < 0 &&
      comp.indexOf('<button') < 0);
    check(fid + ': đánh dấu output-only + role grid (module tự gắn)',
      comp.indexOf('data-output-only="true"') >= 0 &&
      comp.indexOf('role="grid"') >= 0 &&
      comp.indexOf('data-component="output-table"') >= 0);
    check(fid + ': blocks chữ ký nguồn bị thay bằng grid (.dupe-anchor)',
      (out.match(/class="dupe-anchor"/g) || []).length >= 1);
    if (fid === 'PLI_M70') {
      check('O1: 1 hàng x 2 cột (người nộp | người nhận ngang — 5R2)',
        comp.indexOf('aria-rowcount="1"') >= 0 &&
        comp.indexOf('aria-colcount="2"') >= 0);
      check('O1: nhãn lấy đúng text chữ ký của blocks nguồn',
        comp.indexOf('NGƯỜI NỘP<br>(Ký và ghi họ tên)') >= 0 &&
        comp.indexOf('NGƯỜI NHẬN<br>(Ký và ghi họ tên)') >= 0);
    } else {
      check('O2: biến thể 1 ô ký cơ quan',
        comp.indexOf('aria-rowcount="1"') >= 0 &&
        comp.indexOf('aria-colcount="1"') >= 0 &&
        comp.indexOf('(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)') >= 0);
      check('O2: footnote sau vùng ký KHÔNG bị cuốn vào component',
        (() => {
          const blocks = loadBlocks('PLI_M71').blocks;
          const span = R.sectionSpanOfParts(blocks.map(b => ({ b })),
            FD.getSectionContract(fid, 'chu_ky_co_quan_cap_tinh').anchor);
          return span.start < span.end && span.end < blocks.length;
        })());
    }
  });

  // active_when rỗng -> luôn render; active_when fail-closed nếu khai lạ
  const sp = OutputTable.renderOutputTable(
    Object.assign({}, FD.getSectionContract('PLI_M70',
      'chu_ky_nguoi_nop_nguoi_nhan').spec, { active_when: [{ nonsense: true }] }),
    { values: {}, checks: {} });
  check('O1: active_when không hỗ trợ -> fail-closed (không render)', sp === '');
}

/* --------------------------------------------- 4. controller CRUD policy */
section('4. controller: CRUD policy theo kind');
{
  const nestedLoop = 'ds_nddpl_uy_quyen_chu_so_huu';
  const meta = H.SectionCtl.rowMeta('PLI_M02', nestedLoop);
  check('nested-grid policy cho phép add/delete/reorder',
    !!meta && meta.allowAdd === true && meta.allowDelete === true &&
    meta.allowReorder === true);
  check('nested-grid policy expose columns vật lý cho focus/keyboard',
    Array.isArray(meta.columns) && meta.columns.length === 14);
  check('editable-grid đi đường cũ: rowMeta trả null cho loop cũ',
    H.SectionCtl.rowMeta('PLI_M02', 'ds_nganh') === null);
  check('fixed-matrix KHÔNG có dòng dữ liệu thao tác được (policy chặn + '
    + 'canDelete=false)',
    Matrix.canDelete({}, 'von_tu_nhan') === false &&
    Matrix.deleteRows(emptyStore(), 'x', ['von_tu_nhan']) === 0);

  // GridCtl thuần trên loop nested-grid: _row_id ổn định + không đổi khác
  const store = emptyStore({}, { [nestedLoop]: [
    { loai_dong: 'ndd_uy_quyen', ten_nguoi_dai_dien: 'A' }] });
  H.GridCtl.ensureIds(store);
  const firstId = store.loops[nestedLoop][0]._row_id;
  check('_row_id được gán idempotent cho dòng lặp nested-grid',
    !!firstId && (H.GridCtl.ensureIds(store),
      store.loops[nestedLoop][0]._row_id === firstId));
  const added = H.GridCtl.addRow(store, nestedLoop, firstId);
  check('addRow chèn đúng vị trí và sinh _row_id mới',
    added.index === 1 && added.id !== firstId &&
    store.loops[nestedLoop][1]._row_id === added.id);
  const dup = H.GridCtl.duplicateRow(store, nestedLoop, firstId, 'PLI_M02');
  check('duplicateRow giữ vai trò dòng (discriminator) và bỏ _row_id cũ',
    !!dup && store.loops[nestedLoop][dup.index].loai_dong === 'ndd_uy_quyen' &&
    store.loops[nestedLoop][dup.index]._row_id === dup.id &&
    dup.id !== firstId);
  const moved = H.GridCtl.moveRow(store, nestedLoop, added.id, -1);
  check('moveRow theo _row_id - dòng kề đã bị nhân bản chiếm chỗ',
    moved === dup.index && store.loops[nestedLoop][moved]._row_id === added.id,
    'moved=' + moved);
  const killed = H.GridCtl.deleteRows(store, nestedLoop, [added.id]);
  check('deleteRows theo _row_id trả đúng số dòng đã xóa', killed === 1);
}

/* ------------------------------------------- 5. validation qua FormDomain */
section('5. validation: severity contract + tổng projection');
{
  const sk = 'nguon_von_dieu_le';
  const entry = FD.getSectionContract('PLI_M03', 'nguon_von_dieule');
  const C = (p, k) => sk + '.' + p + '.' + k;

  // 5a. hợp lệ: 1 dòng vốn tư nhân
  const ok = emptyStore({ [C('von_tu_nhan', 'so_tien_vnd_va_tuong_duong')]: '60.000.000',
    [C('von_tu_nhan', 'ty_le')]: '100', 'von_dieu_le': '60000000' });
  check('F2: dữ liệu hợp lệ -> 0 lỗi', FD.validateSectionEntry('PLI_M03', entry, ok).length === 0,
    JSON.stringify(FD.validateSectionEntry('PLI_M03', entry, ok)));
  check('F2: tổng recompute = dữ liệu nhập (projection)',
    FD.recomputeSections('PLI_M03', ok)[C('tong_cong', 'so_tien_vnd_va_tuong_duong')].value === 60000000);

  // 5b. MONEY blocking
  const badMoney = emptyStore({ [C('von_khac', 'so_tien_vnd_va_tuong_duong')]: 'không phải số' });
  const errsMoney = FD.validateSectionEntry('PLI_M03', entry, badMoney);
  check('F2: ô tiền sai định dạng -> MONEY blocking, key trỏ ô cụ thể',
    errsMoney.some(e => e.code === 'MONEY' && e.severity === 'blocking' &&
      e.key === C('von_khac', 'so_tien_vnd_va_tuong_duong')),
    JSON.stringify(errsMoney));

  // 5c. PERCENT_SUM warning "khi co ke khai"
  const pct90 = emptyStore({ [C('von_tu_nhan', 'ty_le')]: '90' });
  const errsPct = FD.validateSectionEntry('PLI_M03', entry, pct90);
  check('F2: tổng tỷ lệ lệch -> PERCENT_SUM severity warning',
    errsPct.some(e => e.code === 'PERCENT_SUM' && e.severity === 'warning'),
    JSON.stringify(errsPct));
  check('F2: section chưa kê khai -> không sinh lỗi giả',
    FD.validateSectionEntry('PLI_M03', entry, emptyStore()).length === 0);

  // 5c'. shape rút gọn: percentSum không khai equals vẫn ngầm định ==100
  const slim = JSON.parse(JSON.stringify(entry));
  slim.spec.cross_field_rules = [{ type: 'percentSum', tag: 'ty_le' }];
  check('cross-field: percentSum thiếu equals -> ngầm định ==100 (warning)',
    FD.validateSectionEntry('PLI_M03', slim, pct90)
      .some(e => e.code === 'PERCENT_SUM' && e.severity === 'warning'));
  delete slim.spec.cross_field_rules;

  // 5d. cross-field đối chiếu vốn điều lệ: blocking đúng severity contract
  const mismatch = emptyStore({ [C('von_tu_nhan', 'so_tien_vnd_va_tuong_duong')]: '60.000.000',
    'von_dieu_le': '50.000.000' });
  const errsCap = FD.validateSectionEntry('PLI_M03', entry, mismatch);
  check('F2: tổng cộng != vốn điều lệ -> blocking CAPITAL_MISMATCH',
    errsCap.some(e => e.code === 'CAPITAL_MISMATCH' && e.severity === 'blocking'),
    JSON.stringify(errsCap));
  check('F2: khớp vốn điều lệ -> hết lỗi đối chiếu',
    !FD.validateSectionEntry('PLI_M03', entry, ok).some(e => e.code === 'CAPITAL_MISMATCH'));

  // 5e. tổng lưu sẵn SAI thì không thắng projection (một nguồn số liệu)
  const stale = emptyStore({ [C('von_tu_nhan', 'so_tien_vnd_va_tuong_duong')]: '60.000.000',
    [C('tong_cong', 'so_tien_vnd_va_tuong_duong')]: '999' });
  const beforeJson = JSON.stringify(stale);
  const proj = FD.recomputeSections('PLI_M03', stale);
  check('F2: tổng đọc từ formula chứ không tin con số đã lưu',
    proj[C('tong_cong', 'so_tien_vnd_va_tuong_duong')].value === 60000000);
  check('F2: recompute KHÔNG ghi ngược draft (JSON bất biến)',
    JSON.stringify(stale) === beforeJson);

  // 5f. dispatcher không nuốt kind mới: loop khai trong blocks vẫn đi nested
  const loopKey = 'ds_nddpl_uy_quyen_chu_so_huu';
  const docFake = {
    id: 'PLI_M02', ten_mau: 'fake', blocks: [
      { t: 'loop', loop: loopKey, blankRows: 0, headerRows: [], cols: [
        { col: 1, tag: 'ten_nguoi_dai_dien' }], rows: [] }
    ]
  };
  const discBad = emptyStore({}, { [loopKey]: [
    { _row_id: 'rX', ten_nguoi_dai_dien: 'A', loai_dong: 'unknown' },
    { _row_id: 'rY', ten_nguoi_dai_dien: 'B', loai_dong: '' }
  ] });
  const errsDoc = FD.validateDocument('PLI_M02', docFake.blocks, discBad, {});
  check('N1: validator đi qua NestedGrid (DISCRIMINATOR_INVALID), '
    + 'KHÔNG rơi legacy MIN_ROWS/MONEY',
    errsDoc.some(e => e.code === 'DISCRIMINATOR_INVALID' &&
      e.key.indexOf(loopKey + '.rX.loai_dong') === 0) &&
    !errsDoc.some(e => e.code === 'MIN_ROWS' || e.code === 'MONEY'),
    JSON.stringify(errsDoc.map(e => e.code)));

  const groupMissing = emptyStore({}, { [loopKey]: [
    { _row_id: 'rZ', loai_dong: 'ndd_uy_quyen', dia_chi: 'HN' }
  ] });
  const errsGroup = FD.validateFormSections('PLI_M02', groupMissing);
  check('N1: row_groups quyết định tập cột bắt buộc (REQUIRED_FIELD trỏ tag)',
    errsGroup.some(e => e.code === 'REQUIRED_FIELD' &&
      e.key === loopKey + '.rZ.von_duoc_uy_quyen_vnd'),
    JSON.stringify(errsGroup));
  check('N1: nhóm ndd_pl chỉ yêu cầu tên (không đòi cột vốn của nhóm '
    + 'cá nhân người ủy quyền)',
    (() => {
      const errs = FD.validateFormSections('PLI_M02', emptyStore({}, { [loopKey]: [
        { _row_id: 'rP', loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'TRAN B' } ] }));
      return errs.every(e => e.code !== 'REQUIRED_FIELD' ||
        e.key.indexOf('von_duoc_uy_quyen_vnd') < 0);
    })());
  const noRole = FD.validateFormSections('PLI_M02', emptyStore({}, { [loopKey]: [
    { _row_id: 'rQ', ten_nguoi_dai_dien: 'CHON VAI TRO TRUOC' } ] }));
  check('N1: vai trò dòng chưa chọn -> DISCRIMINATOR_INVALID (fail-closed)',
    noRole.some(e => e.code === 'DISCRIMINATOR_INVALID'), JSON.stringify(noRole));
}

/* -------------------------------------------------- 6. draft round-trip */
section('6. draft round-trip qua migrateDraft');
{
  const loopKey = 'ds_nddpl_uy_quyen_chu_so_huu';
  const draftV2 = {
    v: 2, caseId: 'case-x', checkedForms: ['PLI_M03'],
    activeDocId: 'PLI_M03', autoSum: false, viewState: {},
    savedAt: '2026-08-27T00:00:00.000Z',
    store: {
      values: {
        'nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong': '60.000.000',
        'nguon_von_dieu_le.von_tu_nhan.ty_le': '100',
        'future.unknown.field': 'giữ lại (additive migration)'
      },
      checks: { chk_tt_thanh_lap_moi: true },
      loops: {
        [loopKey]: [
          { _row_id: 'rKEEP1', loai_dong: 'ndd_uy_quyen', ten_nguoi_dai_dien: 'NGUYEN A' },
          { loai_dong: 'ndd_pl', ten_nguoi_dai_dien: 'TRAN B' }
        ]
      }
    }
  };
  const up = FD.migrateDraft(JSON.parse(JSON.stringify(draftV2)));
  check('draft v2: flat values fixed-matrix sống sót đúng nguyên văn',
    up.store.values['nguon_von_dieu_le.von_tu_nhan.so_tien_vnd_va_tuong_duong']
      === '60.000.000');
  check('draft v2: unknown field được bảo toàn (migration additive-only)',
    up.store.values['future.unknown.field'] === 'giữ lại (additive migration)');
  check('draft v2: checks giữ nguyên',
    up.store.checks.chk_tt_thanh_lap_moi === true);
  check('draft v2: _row_id có sẵn được giữ KHÔNG đổi',
    up.store.loops[loopKey][0]._row_id === 'rKEEP1');
  check('draft v2: dòng thiếu _row_id được gán ổn định/idempotent',
    typeof up.store.loops[loopKey][1]._row_id === 'string' &&
    up.store.loops[loopKey][1]._row_id.length > 0);
  const secondPass = JSON.stringify(FD.migrateDraft(
    JSON.parse(JSON.stringify(up))));
  check('draft v2: migrateDraft hai lần cho kết quả giống nhau (idempotent)',
    secondPass.replace(/"(r\d+_[a-z0-9]+)"/g, '"ID"') ===
    JSON.stringify(up).replace(/"(r\d+_[a-z0-9]+)"/g, '"ID"'));

  // validation vẫn thấy lỗi sau round-trip (không mất ngữ cảnh)
  const errsAfter = FD.validateFormSections('PLI_M03', up.store);
  check('draft round-trip: store hợp lệ sau restore -> 0 lỗi section',
    errsAfter.length === 0, JSON.stringify(errsAfter));

  // section inactive KHÔNG sinh dữ liệu giả
  const valuesSnapshot = JSON.stringify(Object.keys(up.store.values).sort());
  FD.recomputeSections('PLI_M03', up.store);
  FD.recomputeSections('PLI_M04', up.store);
  FD.recomputeSections('PLI_M70', up.store);
  check('section inactive: recompute không sinh key mới vào draft',
    JSON.stringify(Object.keys(up.store.values).sort()) === valuesSnapshot);
  check('section inactive: không ai tự chế key cho F3/O1/O2 khi chưa điền',
    Object.keys(up.store.values)
      .filter(k => k.indexOf('co_cau_loai_co_phan.') === 0 ||
        k.indexOf('chu_ky_tiep_nhan_ho_so.') === 0 ||
        k.indexOf('chu_ky_cqb_m71.') === 0).length === 0);

  // payload export: nested-grid không lộ field nội bộ (_row_id)
  const loopsOut = H.GridCtl.exportLoops(up.store, ['PLI_M02']);
  check('export payload nested-grid: bỏ mọi field nội bộ _*',
    loopsOut[loopKey].length === 2 &&
    loopsOut[loopKey].every(r => Object.keys(r).every(k => k.charAt(0) !== '_')));
  check('export payload nested-grid: giữ dữ liệu nghiệp vụ',
    loopsOut[loopKey][0].loai_dong === 'ndd_uy_quyen' &&
    loopsOut[loopKey][0].ten_nguoi_dai_dien === 'NGUYEN A');

  // draft v1 legacy (chưa có viewState) vẫn lên được shape mới
  const legacy = {
    v: 1, caseId: 'case-old',
    checkedForms: ['PLI_M03'],
    store: { values: { 'nguon_von_dieu_le.von_tu_nhan.ty_le': '55' }, checks: {}, loops: {} }
  };
  const upLegacy = FD.migrateDraft(legacy);
  check('draft v1 legacy: giá trị phẳng giữ nguyên sau migration',
    upLegacy.store.values['nguon_von_dieu_le.von_tu_nhan.ty_le'] === '55' &&
    upLegacy.v === 2);
  check('draft v1 legacy: validate ngay trên store đã migrate',
    FD.validateFormSections('PLI_M03', upLegacy.store)
      .some(e => e.code === 'PERCENT_SUM'));
}

/* --------------------------------------------------- 7. fixture nhóm nhỏ */
section('7. fixture production đủ đặc tính khó nhất của từng kind');
{
  // O2/O1: nhãn khớp text thực tế trong blocks (không phải chuỗi chế tay).
  // [Lead sync sau regen W1 d48eb7d] nhãn ký giờ nằm trong Ô của w:tbl
  // output-table — đọc cell text thay vì paragraph role cũ; bản chất khẳng
  // định (labels lấy từ blocks production) giữ nguyên.
  const cellTextOf = cell => ((cell && cell.runs) || [])
    .map(r => (r && r.text) || '').join('');
  const tableCellTexts = blocks => (blocks || [])
    .filter(b => b.t === 'table')
    .flatMap(b => (b.rows || []).map(row =>
      (row.cells || []).map(cellTextOf).join('\n')));
  const m71 = loadBlocks('PLI_M71');
  const sub = tableCellTexts(m71.blocks)
    .find(t => t.toUpperCase().indexOf('TÊN CƠ QUAN') >= 0);
  const o2spec = FD.getSectionContract('PLI_M71', 'chu_ky_co_quan_cap_tinh').spec;
  check('O2: label component = text thật trong blocks (bỏ xuống dòng)',
    String(o2spec.grid.labels[0][0]).replace(/\s+/g, '') ===
    String(sub).replace(/\s+/g, ''),
    JSON.stringify([o2spec.grid.labels[0][0], sub]));
  const m70 = loadBlocks('PLI_M70');
  // 5R2: bảng ký PLI_M70 là 1 hàng × 2 cột — so theo Ô (mỗi ô 1 signer)
  const sigs = (m70.blocks || []).filter(b => b.t === 'table')
    .flatMap(b => (b.rows || []).flatMap(row =>
      (row.cells || []).map(cellTextOf)))
    .filter(t => t.indexOf('NGƯỜI') >= 0);
  const o1spec = FD.getSectionContract('PLI_M70', 'chu_ky_nguoi_nop_nguoi_nhan').spec;
  check('O1: 2 ô ký khớp 2 ô của w:tbl output-table PLI_M70 (1x2)',
    sigs.length === 2 && o1spec.grid.labels.every((lb, i) =>
      String(lb).replace(/\s+/g, '') === String(sigs[i]).replace(/\s+/g, '')),
    JSON.stringify(sigs));

  // F2 khớp 5 nhãn dòng trong blocks nguồn (không STT)
  // [Lead sync 2026-08-28] sau regen cap-von, nhãn dòng nằm TRONG ô w:tbl
  // (block t=table có rows[].cells[].runs) — gộp thêm text bảng vào phép tìm.
  const m03Text = (loadBlocks('PLI_M03').blocks.map(b => (b.runs || [])
    .map(r => (r && r.text) || '').join('')
    + (b.rows || []).map(row => (row.cells || []).map(c => (c.runs || [])
      .map(r => (r && r.text) || '').join('')).join('')).join(''))).join('|');
  const f2 = FD.getSectionContract('PLI_M03', 'nguon_von_dieule').spec;
  check('F2: 5 id fixed_rows khớp manifest (census là nguồn chân lý)',
    JSON.stringify((MANIFEST.forms.filter(f => f.form_id === 'PLI_M03')[0]
      .sections.find(s => s.section_id === 'nguon_von_dieule').fixed_rows)) ===
    JSON.stringify(f2.fixed_rows.map(r => r.id)));
  check('F2: từng nhãn dòng xuất hiện trong blocks nguồn PLI_M03',
    f2.fixed_rows.every(r => m03Text.indexOf(r.label) >= 0), m03Text.slice(-200));

  // F3: 6 dòng cố định khớp manifest
  const f3 = FD.getSectionContract('PLI_M04', 'co_cau_loai_co_phan').spec;
  check('F3: fixed_rows khớp manifest PLI_M04',
    JSON.stringify(MANIFEST.forms.filter(x => x.form_id === 'PLI_M04')[0]
      .sections.find(s => s.section_id === 'co_cau_loai_co_phan').fixed_rows) ===
    JSON.stringify(f3.fixed_rows.map(r => r.id)));
  check('F3: tag cột dùng đúng danh sách manifest required_columns',
    (() => {
      const want = MANIFEST.forms.filter(x => x.form_id === 'PLI_M04')[0]
        .sections.find(s => s.section_id === 'co_cau_loai_co_phan')
        .required_columns;
      const tags = f3.columns.map(c => c.tag);
      return tags.every(t => want.indexOf(t) >= 0);
    })());

  // N1: header N1 khớp headerRows của loop block thật sau regen R3B1
  // (block glue 'STTTên người đại diện…' KHÔNG còn tồn tại — đã dựng w:tbl).
  const m02Blocks = loadBlocks('PLI_M02').blocks;
  const n1Loop = m02Blocks.find(b => b.t === 'loop' &&
    b.loop === 'ds_nddpl_uy_quyen_chu_so_huu');
  const joinedHeader = n1Loop ? n1Loop.headerRows.map(ri =>
    (n1Loop.rows[ri].cells || []).map(c => (c.runs || [])
      .map(r => (r && r.text) || '').join('')).join('')).join('') : '';
  const n1 = FD.getSectionContract('PLI_M02', 'ds_nddpl_uy_quyen_chu_so_huu').spec;
  check('N1: mọi tiêu đề cột khai đều nằm trong header nguồn đã join '
    + '(bỏ số chú thích chân trang/khoảng trắng/không phân biệt hoa thường)',
    n1.header_rows.flat().every(cell =>
      joinedHeader.replace(/[0-9\s]/g, '').toLowerCase()
        .indexOf(String(cell.text).replace(/[0-9\s]/g, '').toLowerCase()) >= 0),
    JSON.stringify(n1.header_rows.flat().map(c => c.text)));
  check('N1: Chữ ký/Ghi chú là cột riêng (rowspan 2, bề rộng 1)',
    n1.header_rows[0].slice(-2).every(c => (c.rowspan || 1) === 2 &&
      (c.colspan || 1) === 1));
}

console.log('-'.repeat(60));
console.log('Ket qua: ' + passed + ' PASS / ' + failed + ' FAIL');
process.exit(failed ? 1 : 0);
