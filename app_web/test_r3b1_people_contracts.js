/* test_r3b1_people_contracts.js — Lane R3B1 (people/ownership tables).
 *
 * Kiểm chứng phía runtime/form-domain cho đợt sửa audit V1 "bảng người bị dẹt
 * thành text glue" (audit Wave D liệt kê), theo docs/decision_registry.md:
 *   1. Contract SECTION mới (nested-grid) PLI_M12 (N6) + PLI_M15 (N7) đăng ký
 *      qua FORM_TABLE_CONTRACTS và resolve được theo sectionId/semanticKey/loop.
 *   2. Khớp chéo artifact-generator <-> artifact-runtime: cột/tag/col_index của
 *      spec JSON (tools/form_specs/**) BẰNG contract JS, gồm cả N1 (PLI_M02)
 *      có sẵn -> không bao giờ lệch key giữa rebuild DOCX và UI/export.
 *   3. Header nhiều hàng phủ kín đúng lưới vật lý (headerLayout tiling giống
 *      build_form_maps._header_layout) + D2.4=A (chu_ky outputOnly).
 *   4. Anchor của mỗi contract tìm thấy trong blocks HIỆN TẠI (Render.
 *      sectionSpanOfParts, so theo blockPlainText như renderer thật) và trỏ
 *      đúng vùng evidence audit chỉ ra.
 *   5. Metadata editable-grid PLII_M02 cho HAI bảng thành viên hộ gia đình
 *      (a4/c7): resolver trả meta đủ 10 cột, clone riêng (P2.0), semanticKey
 *      riêng - trong khi entry spec rebuild còn BLOCKED bởi test contract
 *      ghim tập occurrence_id của file household/PLII_M02.json.
 *   6. CỔNG BLOCKED: những bảng chưa đủ quyết định/nguồn KHÔNG được đăng ký
 *      contract (PLI_M09, PLII_M02 2 lưới thành viên, PLI_M72 N2-N5).
 *
 * Chạy: node app_web/test_r3b1_people_contracts.js   (từ root repo, không GUI)
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');
const NestedGrid = require('./ui/nested-grid.js');

const RESULTS = [];
let passed = 0;
let failed = 0;

function check(name, pass, expect, actual) {
  const ok = !!pass;
  RESULTS.push({ name, pass: ok });
  if (ok) passed++;
  else failed++;
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name +
    (ok ? '' : '\n        EXPECT : ' + (expect || '') +
      '\n        ACTUAL : ' + (actual === undefined ? '(none)' : String(actual))));
}

function loadJson(relPath) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, relPath), 'utf8'));
}

function plainText(b) {
  if (!b) return '';
  let out = '';
  if (Array.isArray(b.runs)) {
    b.runs.forEach(r => { out += (r && r.text != null ? String(r.text) : ''); });
  } else if (Array.isArray(b.rows)) {
    b.rows.forEach(row => (row.cells || []).forEach(c =>
      (c.runs || []).forEach(r => { out += r.text || ''; })));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Artifact nguồn: blocks hiện trạng + census manifest + spec generator
// ---------------------------------------------------------------------------
const BLOCKS = {};
for (const fid of ['PLI_M02', 'PLII_M02', 'PLI_M09', 'PLI_M12', 'PLI_M15',
  'PLI_M72']) {
  BLOCKS[fid] = loadJson(path.join('app/data/blocks', fid + '.json')).blocks;
}
const MANIFEST = loadJson('app/data/table_specs/manifest.json');
const SPEC_FILES = {
  PLI_M02: loadJson('tools/form_specs/core/PLI_M02.json'),
  PLI_M12: loadJson('tools/form_specs/change/PLI_M12.json'),
  PLI_M15: loadJson('tools/form_specs/change/PLI_M15.json'),
};
const SPEC_LOOPS = [
  { docId: 'PLI_M02', loop: 'ds_nddpl_uy_quyen_chu_so_huu' },
  { docId: 'PLI_M12', loop: 'ds_ndd_uy_quyen_sau_thay_doi' },
  { docId: 'PLI_M15', loop: 'ds_nddpl_uy_quyen_chu_so_huu_moi' },
];

// ===========================================================================
// 1-2-3. Contract mới + khớp chéo với spec generator
// ===========================================================================

SPEC_LOOPS.forEach(({ docId, loop }) => {
  const jsC = FD.sectionContractForLoop(docId, loop);
  check(docId + '/' + loop + ': contract nested-grid resolve theo loop',
    !!jsC && jsC.kind === 'nested-grid', 'kind=nested-grid',
    jsC && jsC.kind);

  const bySem = FD.getSectionContract(docId,
    jsC && jsC.semanticKey);
  const bySection = FD.getSectionContract(docId, jsC && jsC.sectionId);
  check(docId + '/' + loop + ': resolve theo semanticKey va sectionId',
    bySem === jsC && bySection === jsC);

  // ---- khớp chéo với spec generator (một row-contract duy nhất hai đầu)
  const raw = SPEC_FILES[docId];
  const ent = (raw.tables || []).find(t => ((t.spec || {}).loop) === loop);
  check(docId + '/' + loop + ': spec JSON co entry tuong ung (validator v1)',
    !!ent && ent.spec && ent.spec.kind === 'nested-grid' &&
      !ent.legal_status.blocked);
  if (!ent) return;
  const pySpec = ent.spec;
  const jsTags = (jsC.spec.columns || []).map(c => c.tag);
  const pyTags = ['stt'].concat(pySpec.columns.map(c => c.tag));
  check(docId + '/' + loop + ': cung day tag giua spec DOCX va contract UI',
    JSON.stringify(jsTags) === JSON.stringify(pyTags),
    pyTags.join(','), jsTags.join(','));
  check(docId + '/' + loop + ': col_index vat ly lien ke 0..width-1',
    (jsC.spec.columns || []).every((c, i) => c.col_index === i),
    '0..' + (pySpec.width - 1));
  check(docId + '/' + loop + ': header_rows giong nhau hai ben',
    JSON.stringify(jsC.spec.header_rows) === JSON.stringify(pySpec.header_rows));

  // ---- validator thuần của module phải thấy contract hợp lệ
  check(docId + '/' + loop + ': NestedGrid.validateContract (docId=' + docId +
    ')', NestedGrid.validateContract(jsC.spec).length === 0,
    '[] loi contract', JSON.stringify(NestedGrid.validateContract(jsC.spec)));

  // ---- layout header phủ kín lưới vật lý (cùng thuật toán tiling)
  const layout = NestedGrid.headerLayout(jsC.spec);
  const covered = [];
  layout.rows.forEach((rowCells, ri) => rowCells.forEach(cell => {
    for (let r = ri; r < ri + cell.rowspan; r++) {
      for (let c = cell.col_index; c < cell.col_index + cell.colspan; c++) {
        covered.push([r, c]);
      }
    }
  }));
  const uniq = new Set(covered.map(p => p.join(':')));
  const widthPhys = NestedGrid.physicalColumns(jsC.spec).columns.length;
  const tilesWant = widthPhys * layout.rows.length;
  check(docId + '/' + loop + ': header phu kin ' + layout.rows.length + 'x' +
      widthPhys + ' khong de` len nhau',
    !(Array.isArray(layout.errors) && layout.errors.length) &&
      uniq.size === covered.length && covered.length === tilesWant &&
      widthPhys - 1 /* STT */ === pySpec.columns.length,
    'tiles=' + tilesWant,
    'tiles_seen=' + covered.length + ' unique=' + uniq.size);

  // ---- D2.4=A chu_ky outputOnly; min/max D2.7 với hai entry MỚI của lane
  const ck = jsC.spec.columns.find(c => c.tag === 'chu_ky');
  check(docId + '/' + loop + ': D2.4=A chu_ky outputOnly',
    !!ck && ck.type === 'outputOnly');
  const isR3B1New = docId !== 'PLI_M02';
  check(docId + '/' + loop + ': min_rows/max_rows' +
      (isR3B1New ? ' dung D2.7=A (min 1, max null)' : ' giu nguyen hien trang N1'),
    isR3B1New
      ? jsC.spec.min_rows === 1 && jsC.spec.max_rows === null
      : typeof jsC.spec.min_rows === 'number');

  // ---- discriminator: chỉ khai khi đã có quyết định nguồn (D2.1=A cho
  //      bộ M02/M13/M15); M12 KHÔNG khai thay vì tự chế key
  const hasDiscr = jsC.spec.discriminator != null;
  if (docId === 'PLI_M02' || docId === 'PLI_M15') {
    check(docId + '/' + loop + ': D2.1=A discriminator loai_dong',
      hasDiscr && jsC.spec.discriminator.tag === 'loai_dong' &&
        JSON.stringify(jsC.spec.discriminator.values) ===
          JSON.stringify(['ndd_pl', 'ndd_uy_quyen']));
  } else {
    check(docId + '/N6: khong khai discriminator (chua co evidence 2 row-type)',
      !hasDiscr && !Array.isArray(jsC.spec.row_groups));
  }

  // ---- validator runtime bắt lỗi dòng dữ liệu đúng group/quy tắc
  const rowsGood = [{ _row_id: 'r1',
    loai_dong: docId === 'PLI_M12' ? undefined : 'ndd_pl',
    ten_nguoi_dai_dien: 'NGUYEN VAN A',
    ten_ndd_uy_quyen: docId === 'PLI_M12' ? 'NGUYEN VAN A' : undefined }];
  const errsGood = NestedGrid.validate(jsC.spec, rowsGood);
  const errsEmpty = NestedGrid.validate(jsC.spec, []);
  check(docId + '/' + loop + ': validate 0 loi cho dong du lieu dung row-type',
    errsGood.length === 0 && errsEmpty.length === 0,
    '[]',
    JSON.stringify(errsGood.map(e => e.code)));
});

check('PLI_M02/N1: index cot khong doi sot voi before (regression guard)',
  JSON.stringify(FD.getSectionContract('PLI_M02',
    'ds_nddpl_uy_quyen_chu_so_huu').spec.columns.map(c => c.tag)) ===
    JSON.stringify(['stt', 'ten_nguoi_dai_dien', 'ngay_sinh', 'gioi_tinh',
      'giay_to_so', 'giay_to_ngay', 'giay_to_co_quan', 'quoc_tich',
      'dan_toc', 'dia_chi', 'von_duoc_uy_quyen_vnd', 'ty_le', 'chu_ky',
      'ghi_chu']));

// ===========================================================================
// 4. anchor trả về vùng đúng trên blocks HIỆN TẠI
// ===========================================================================
const ANCHOR_EVIDENCE = [
  { docId: 'PLI_M02', sem: 'ds_nddpl_uy_quyen_chu_so_huu', headingBlock: 125 },
  { docId: 'PLI_M12', sem: 'ds_ndd_uy_quyen_sau_thay_doi', headingBlock: 144 },
  { docId: 'PLI_M15', sem: 'ds_nddpl_uy_quyen_chu_so_huu_moi', headingBlock: 48 },
];
ANCHOR_EVIDENCE.forEach(({ docId, sem, headingBlock }) => {
  const c = FD.getSectionContract(docId, sem);
  const blocks = BLOCKS[docId];
  const parts = blocks.map(b => ({ b }));
  const span = R.sectionSpanOfParts(parts, c.anchor);
  check(docId + ': anchor tim thay va ton tai vung [start,end) trong blocks',
    !!span && span.start >= 0 && span.end > span.start &&
      span.end <= blocks.length,
    'span hop le', JSON.stringify(span));
  check(docId + ': anchor tro dung block heading theo evidence audit (' +
      headingBlock + ')',
    !!span && span.start === headingBlock,
    String(headingBlock), span && String(span.start));
});

// ===========================================================================
// 5. metadata editable-grid PLII_M02 cho hai bảng thành viên hộ gia đình
// ===========================================================================
const HD_BASE = FD.GRID_META.ds_tv_ho_gia_dinh;
const BASE_TAGS = (HD_BASE.columns || []).map(c => c.tag);
['tv_hgd_sau_thay_doi', 'tv_hgd_cap_doi'].forEach(loopName => {
  const g = FD.getGridMeta({ docId: 'PLII_M02', loop: loopName });
  check('PLII_M02/' + loopName + ': resolver tra meta form-scoped',
    !!g && !!FD.FORM_GRID_META.PLII_M02.loops[loopName] &&
      FD.FORM_GRID_META.PLII_M02.bySemanticKey[loopName] === g);
  check('PLII_M02/' + loopName + ': 10 cot khop ds_tv_ho_gia_dinh + chu_ky outputOnly',
    JSON.stringify((g.columns || []).map(c => c.tag)) ===
      JSON.stringify(BASE_TAGS) &&
      BASE_TAGS.length === 9 /* + STT do engine sinh khi rebuild */ &&
      (g.columns.find(c => c.tag === 'chu_ky') || {}).type === 'outputOnly',
    BASE_TAGS.join(','), (g.columns || []).map(c => c.tag).join(','));
  check('PLII_M02/' + loopName + ': semanticKey rieng, khong auto-sync nhau',
    g.semanticKey === loopName &&
      FD.getGridMeta({ docId: 'PLII_M02', loop: 'tv_hgd_sau_thay_doi' })
        .semanticKey !==
        FD.getGridMeta({ docId: 'PLII_M02', loop: 'tv_hgd_cap_doi' })
          .semanticKey);
  check('PLII_M02/' + loopName + ': meta la clone (P2.0) khong share GRID_META',
    (() => {
      const beforeG = JSON.stringify(HD_BASE);
      const snap = JSON.stringify(g);
      g.columns[0].type = '__mutated__';
      const sameBase = JSON.stringify(HD_BASE) === beforeG;
      g.columns[0].type = JSON.parse(snap).columns[0].type;
      return sameBase && JSON.stringify(g) === snap;
    })());
});
check('PLII_M02: hai luoi tv_hgd khong ke thua syncGroup (khong auto-sync)',
  !FD.FORM_GRID_META.PLII_M02.loops.tv_hgd_sau_thay_doi.syncGroup &&
    !FD.FORM_GRID_META.PLII_M02.loops.tv_hgd_cap_doi.syncGroup);

// ===========================================================================
// 6. cổng BLOCKED — section chưa đủ quyết định/nguồn thì KHÔNG có contract/spec
// ===========================================================================
check('PLI_M09: chua dang ky contract nao cho nguoi hop danh (D3 chua kien trung)',
  FD.sectionContractsOf('PLI_M09').length === 0 &&
    FD.sectionContractForLoop('PLI_M09', 'ds_thanh_vien_hop_danh') === null);
check('PLII_M02: CHUA co contract table cho tv_hgd_* (metadata san sang, spec blocked)',
  !FD.FORM_TABLE_CONTRACTS.PLII_M02 &&
    FD.sectionContractForLoop('PLII_M02', 'tv_hgd_sau_thay_doi') === null &&
    FD.sectionContractForLoop('PLII_M02', 'tv_hgd_cap_doi') === null);
const M72_PEOPLE = ['ds_thanh_vien_tnhh_cong_bo', 'ds_co_dong_sang_lap_cong_bo',
  'ds_co_dong_nn_cong_bo', 'ds_thanh_vien_hop_danh_cong_bo'];
check('PLI_M72: N2-N5 van khong contract, con grid nganh san co khong anh huong',
  M72_PEOPLE.every(name =>
    FD.sectionContractForLoop('PLI_M72', name) === null &&
      FD.getSectionContract('PLI_M72', name) === null) &&
    !!FD.getGridMeta({ docId: 'PLI_M72', loop: 'ds_nganh_ctcp' }));

// glue hiện trạng của các bảng BLOCKED vẫn nguyên (chưa regen)
{
  const fold = s => R.normText(s).replace(/\s+/g, '');
  const m09folds = BLOCKS.PLI_M09.map(b => fold(plainText(b)));
  const m72folds = BLOCKS.PLI_M72.map(b => fold(plainText(b)));
  const m02folds = BLOCKS.PLII_M02.map(b => fold(plainText(b)));
  check('PLI_M09: region nhiem (B087/B132/B163) con nguyen nhu evidence',
    m09folds[87].indexOf(fold('STTTên thành viênSố, ngày cấp, nơi cấp')) === 0 &&
      m09folds[132].indexOf(fold('Giấy chứng nhận đăng ký doanh nghiệp')) === 0 &&
      m09folds[163].indexOf(fold('Phần vốn góp')) === 0);
  /* [Lead sync sau L1FIX regen] blocks M72 tăng 2 heading section (149→151)
   * nên index tuyệt đối trượt — tra theo NỘI DUNG glue thay vì index. */
  const m72glued = m72folds.filter(f =>
    f.indexOf(fold('STTTên cổ đôngQuốc tịch')) === 0);
  check('PLI_M72: header ghep co dong sang lap con nguyen (tra theo text)',
    m72glued.length >= 2);
  const m02glued1 = m02folds.filter(f =>
    f.indexOf(fold('STTHọ tênNgày, tháng, năm sinh')) === 0);
  const m02glued2 = m02folds.some(f =>
    f.indexOf(fold('Hộ kinh doanh cam kết về tính hợp pháp')) > 0);
  check('PLII_M02: 2 paragraph glue thanh vien ho gia dinh con nguyen (tra theo text)',
    m02glued1.length >= 1 && m02glued2);
}

// manifest vẫn ghi nhận các section này là missing_grid (không tự suy)
{
  const secs = {};
  MANIFEST.forms.forEach(f => {
    secs[f.form_id] = {};
    f.sections.forEach(s => { secs[f.form_id][s.section_id] = s; });
  });
  check('manifest: cac bang BLOCKED van missing_grid/partial_columns (khong suy dien)',
    ['thanh_vien_tnhhh_hai_tv_tro_len', 'co_dong_sang_lap_cp',
      'co_dong_nuoc_ngoai_cp', 'thanh_vien_hop_danh']
      .every(sid => secs.PLI_M72[sid].status === 'missing_grid') &&
      secs.PLI_M09.ds_thanh_vien_hop_danh.status === 'partial_columns' &&
      secs.PLI_M09.vung_nhiem_mau_6789_10.status === 'contaminated');
}

// ---------------------------------------------------------------------------
console.log('-'.repeat(72));
console.log('test_r3b1_people_contracts: %d PASS / %d FAIL', passed, failed);
RESULTS.filter(r => !r.pass).forEach(r => console.log('  -> ' + r.name));
process.exitCode = failed ? 1 : 0;
