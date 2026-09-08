/* test_layout_l2_render.js - Wave L2: renderer/CSS cho blocks-v3
 * (docs/layout_l1_contract.md). Kiểm thử KHÔNG GUI trên chuỗi HTML sinh ra
 * từ ui/render.js - cùng harness style với test_dom.js (jsdom-free).
 *
 * Phủ: escape trước rồi mới \n-><br>/\t, sup/sub semantic, footnote-ref +
 * fn-list, source-indicator biến khỏi DOM (form-number phải còn), 14 role
 * class, format -> CSS custom property theo FORMAT_ALLOWLIST, cond M72 với
 * blocks THẬT + selectorFlagsOf, input/chk giữ nguyên attrs quan trọng,
 * cấu trúc harness app_web/dev/snapshot.html.
 *
 * Giới hạn đã biết (ghi rõ): harness chỉ được assert CẤU TRÚC + endpoint
 * tham chiếu (không có DOM/fetch trong node thuần); phần chạy thật bằng
 * http.server được kiểm thủ công - xem báo cáo lane L2.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');
const D = require('./ui/form-domain.js');

const BLOCKS_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadBlocks(id) {
  return JSON.parse(fs.readFileSync(path.join(BLOCKS_DIR, id + '.json'), 'utf8'));
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

/* ------------------------- helper: doc tối thiểu từ danh sách block p ---- */
function miniDoc(blocks) {
  return { id: 'T_L2', ten_mau: 'test l2', blocks: blocks };
}
function p(text, extra) {
  return Object.assign({ t: 'p', align: 'left', runs: [{ text: text }] }, extra || {});
}

const m02 = loadBlocks('PLI_M02');
const plii01 = loadBlocks('PLII_M01');
const m72 = loadBlocks('PLI_M72');

// =============================================== 1. ESCAPE TRƯỚC, BR SAU ====
{
  const html = R.renderBlocks(miniDoc([
    p('<script>alert("x")</script> & it\'s')
  ]), R.newStore());
  check('L2 escape: <script> không bao giờ xuất raw',
    html.indexOf('<script>') < 0 && html.indexOf('&lt;script&gt;') >= 0);
  check('L2 escape: " -> &quot;', html.indexOf('&quot;x&quot;') >= 0);
  check("L2 escape: ' -> &#39;", html.indexOf('it&#39;s') >= 0);
  check('L2 escape: & -> &amp;', html.indexOf(' &amp; ') >= 0);

  const nl = R.renderBlocks(miniDoc([p('a\nb\nc')]), R.newStore());
  check('L2 \\n -> <br> sau escape (2 break cho 3 dòng)',
    (nl.match(/<br>/g) || []).length === 2 && nl.indexOf('a<br>b<br>c') >= 0);

  const tb = R.renderBlocks(miniDoc([p('Chức danh:\tGiám đốc')]), R.newStore());
  check('L2 \\t -> span.tb (không &nbsp; hàng loạt)',
    tb.indexOf('<span class="tb" aria-hidden="true"></span>') >= 0 &&
      tb.indexOf('&nbsp;') < 0 && tb.indexOf('\t') < 0);

  check('L2 textToHtml: escape CHẠY TRƯỚC split br (tag trong text không sống sót)',
    R.textToHtml('<b>x</b>\ny').indexOf('&lt;b&gt;') >= 0 &&
      R.textToHtml('<b>x</b>\ny').indexOf('<br>') > 0);

  // quốc hiệu THẬT PLI_M02: 3 dòng -> đúng 2 <br>, còn bọc bold
  const h02 = R.renderBlocks(m02, R.newStore());
  const nh = h02.match(/<p class="bp bp-center bp-role-national-header"[^>]*>([\s\S]*?)<\/p>/);
  check('L2 PLI_M02 national-header: 3 dòng riêng bằng 2 <br>',
    !!nh && (nh[1].match(/<br>/g) || []).length === 2, nh && nh[1]);
}

// ==================================================== 2. SUP/SUB SEMANTIC ===
{
  const h = R.renderBlocks(miniDoc([
    { t: 'p', align: 'left', runs: [
      { text: 'Tôi là' }, { text: '1', vertAlign: 'superscript' },
      { text: 'x' }, { text: '2', vertAlign: 'subscript' }
    ] }
  ]), R.newStore());
  check('L2 superscript run -> <sup class="rn">1</sup>', h.indexOf('<sup class="rn">1</sup>') >= 0);
  check('L2 subscript run -> <sub class="rn">2</sub>', h.indexOf('<sub class="rn">2</sub>') >= 0);
  // acceptance PLAN: KHÔNG có baseline "Tôi là1" (digit dính chữ trong HTML thô)
  check('L2 không còn baseline "Tôi là1"', /Tôi là\d/.test(h) === false);
  // b/i/u vẫn giữ trên phần tử sup/sub
  const hb = R.renderBlocks(miniDoc([
    p('a', {}), { t: 'p', align: 'left', runs: [{ text: 'z', b: true, vertAlign: 'superscript' }] }
  ]), R.newStore());
  check('L2 sup giữ run style (rn-b)', hb.indexOf('<sup class="rn rn-b">z</sup>') >= 0);
  // chuỗi sup THẬT trong PLI_M02 ("15" sau chữ ký)
  const h02 = R.renderBlocks(m02, R.newStore());
  check('L2 PLI_M02: run superscript thật render <sup>', /<sup class="rn[^"]*">\d+<\/sup>/.test(h02));
}

// ============================================ 3. FOOTNOTE-REF + FN-LIST =====
{
  const doc = miniDoc([
    { t: 'p', align: 'left', role: 'body',
      runs: [
        { text: 'Tôi là' },
        { role: 'footnote-ref', footnoteId: 3 },
        { text: ' đại diện...' }
      ],
      footnotes: { '3': 'Ghi chú giải thích\ndòng hai' } },
    { t: 'p', align: 'left', role: 'body',
      runs: [{ text: 'khác ' }, { role: 'footnote-ref', footnoteId: 9 }] }
  ]);
  const h = R.renderBlocks(doc, R.newStore());
  check('L2 fn-ref: <sup class="fn-ref" data-fn tabindex="0"> số ID',
    h.indexOf('<sup class="fn-ref" data-fn="3" tabindex="0">3</sup>') >= 0);
  check('L2 fn-list: <ol class="fn-list"><li id="fn-ID">text</li></ol>',
    h.indexOf('<ol class="fn-list"><li id="fn-3">') >= 0);
  check('L2 fn-list text cũng qua pipeline \\n-><br>',
    h.indexOf('Ghi chú giải thích<br>dòng hai') >= 0);
  check('L2 fail-soft: ref không có footnotes map vẫn hiện số',
    h.indexOf('data-fn="9"') >= 0 && h.indexOf('id="fn-9"') < 0);
  check('L2 bindFootnoteRefs là function (progressive enhancement)', typeof R.bindFootnoteRefs === 'function');
  check('L2 bindFootnoteRefs an toàn khi truyền rỗng', R.bindFootnoteRefs(null) === null);

  // id lạ -> token an toàn, không injection qua attr
  const hinj = R.renderBlocks(miniDoc([
    { t: 'p', align: 'left', runs: [{ role: 'footnote-ref', footnoteId: '"><img>' }] }
  ]), R.newStore());
  check('L2 fn-ref id lạ bị sanitize (fail-soft bỏ run)', hinj.indexOf('<img') < 0);
}

// ============================== 4. SOURCE-INDICATOR ẨN / FORM-NUMBER CÒN ===
{
  let dbg = 0;
  const origDebug = console.debug;
  console.debug = function () { dbg++; };
  const h02 = R.renderBlocks(m02, R.newStore(), { docId: 'PLI_M02' });
  console.debug = origDebug;
  check('L2 source-indicator biến mất khỏi DOM (marker PL1/PL2 - Mau so)',
    h02.indexOf('Mau so') < 0 && h02.indexOf('.docx') < 0);
  check('L2 console.debug log ĐÚNG 1 LẦN/form', dbg === 1, 'got ' + dbg);
  const h02again = (() => {
    let n = 0; const od = console.debug;
    console.debug = function () { n++; };
    const x = R.renderBlocks(m02, R.newStore(), { docId: 'PLI_M02' });
    console.debug = od;
    if (n !== 1) throw new Error('debug count ' + n);
    return x;
  })();
  check('L2 render lại lần nữa vẫn ổn định (idempotent string)',
    h02again === h02);
  check('L2 form-number "Mẫu số 2" VẪN hiện', h02.indexOf('Mẫu số 2') >= 0);
  check('L2 form-number giữ align từ dữ liệu (bp-role-form-number + bp-left)',
    /class="bp bp-left bp-role-form-number"/.test(h02));
  const hplii = R.renderBlocks(plii01, R.newStore());
  check('L2 PLII_M01: source-indicator ẩn, national-header còn',
    hplii.indexOf('Mau so') < 0 && hplii.indexOf('bp-role-national-header') >= 0);
}

// ======================================================= 5. 14 ROLE CLASS ===
{
  const ROLES = ['source-indicator', 'form-number', 'national-header',
    'national-motto', 'national-separator', 'date-line', 'form-title',
    'form-subtitle', 'salutation', 'body', 'section-heading', 'note',
    'footnote', 'signature'];
  ROLES.forEach(function (role) {
    const blocks = [p('x', { role: role })];
    if (role !== 'date-line' && role !== 'source-indicator') blocks.push(p('y', {
      role: role, runs: [{ text: 'ngày ' }, { input: { key: 'k_' + role.replace(/-/g, '_') } }]
    }));
    const h = R.renderBlocks(miniDoc(blocks), R.newStore());
    if (role === 'source-indicator') {
      // contract L2: source-indicator BỎ khỏi DOM hoàn toàn -> không có class
      check('L2 role source-indicator: KHÔNG render gì (ẩn theo role)',
        h.trim() === '' && h.indexOf('bp-role-source-indicator') < 0, h);
      return;
    }
    check('L2 role class bp-role-' + role, h.indexOf('bp-role-' + role) >= 0);
  });
  check('L2 date-line CÓ input -> KHÔNG bp-flex (giữ layout ô điền)',
    R.renderBlocks(miniDoc([{ t: 'p', align: 'left', role: 'date-line',
      runs: [{ text: 'ngày ' }, { input: { key: 'ngay_ky_vb' } }] }]), R.newStore())
      .indexOf('bp-flex') < 0);
  check('L2 date-line KHÔNG input -> có bp-flex (wrap an toàn)',
    R.renderBlocks(miniDoc([p('Ngày ... tháng ... năm ...', { role: 'date-line' })]),
      R.newStore()).indexOf('bp-flex') >= 0);
  check('L2 role lạ/không có -> không sinh class rác',
    R.roleClassOf('tôi-là-role-xấu') === '' && R.roleClassOf(undefined) === '');
}

// ===================================== 6. FORMAT -> CSS VAR (ALLOWLIST) =====
{
  const KEYS = ['leftIndentPt', 'rightIndentPt', 'firstLineIndentPt',
    'spaceBeforePt', 'spaceAfterPt', 'lineSpacing', 'lineSpacingPt',
    'keepWithNext'];
  check('L2 FORMAT_ALLOWLIST đủ 8 key contract L1',
    JSON.stringify(Object.keys(R.FORMAT_ALLOWLIST).sort()) === JSON.stringify(KEYS.slice().sort()));

  const s = R.formatStyleAttr({
    leftIndentPt: 12.5, rightIndentPt: 4, firstLineIndentPt: -9.5,
    spaceBeforePt: 6, spaceAfterPt: 3, lineSpacing: 1.15,
    lineSpacingPt: 18, keepWithNext: true
  });
  KEYS.forEach(function (k) {
    check('L2 format ' + k + ' -> var ' + R.FORMAT_ALLOWLIST[k],
      s.indexOf(R.FORMAT_ALLOWLIST[k] + ':') >= 0, s);
  });
  check('L2 đơn vị pt gắn đúng (lineSpacing không đơn vị, keepWithNext=avoid)',
    s.indexOf('--pt-space-before:6pt;') >= 0 &&
      s.indexOf('--pt-line-spacing:1.15;') >= 0 &&
      s.indexOf('--pt-line-spacing-pt:18pt;') >= 0 &&
      s.indexOf('--pt-keep-with-next:avoid;') >= 0 &&
      s.indexOf('--pt-first-line-indent:-9.5pt;') >= 0);

  // style string CHỈ chứa var đã khai - không đưa chuỗi tự do từ JSON
  const sinj = R.formatStyleAttr({
    spaceBeforePt: '6pt; background:url(http://x)',
    evilKey: 'red', leftIndentPt: NaN, rightIndentPt: Infinity,
    firstLineIndentPt: 'abc'
  });
  check('L2 injection/format sai kiểu -> bị bỏ, không có url( hay key lạ',
    sinj.indexOf('url(') < 0 && sinj.indexOf('evilKey') < 0 &&
      sinj.indexOf('background') < 0 && sinj.indexOf('NaN') < 0 &&
      sinj.indexOf('Infinity') < 0, sinj);

  const hfmt = R.renderBlocks(miniDoc([p('x', {
    role: 'body', format: { spaceBeforePt: 6, keepWithNext: true }
  })]), R.newStore());
  check('L2 format áp lên <p> qua attr style chỉ chứa allowlist var',
    /<p class="bp bp-left bp-role-body" style="--pt-space-before:6pt;--pt-keep-with-next:avoid;">/.test(hfmt));
}

// ============================ 7. COND M72 (BLOCKS THẬT + selectorFlagsOf) ===
let stDntn; // dùng lại ở mục 8 (selectorHtml)
{
  const empty = R.renderBlocks(m72, R.newStore(), { docId: 'PLI_M72', flags: {} });
  check('L2 M72 flags rỗng: không render section DNTN lẫn biến thể khác',
    empty.indexOf('DOANH NGHIỆP TƯ NHÂN') < 0 &&
      empty.indexOf('CÔNG TY TNHH HAI THÀNH VIÊN') < 0);

  stDntn = R.newStore();
  stDntn.values['dn.loai_hinh'] = 'DNTN';
  const flagsDntn = D.selectorFlagsOf('PLI_M72', stDntn);
  check('L2 selectorFlagsOf DNTN -> flag loai_hinh_dntn=X',
    flagsDntn.loai_hinh_dntn === 'X');
  const hDntn = R.renderBlocks(m72, stDntn, { docId: 'PLI_M72', flags: flagsDntn });
  check('L2 M72 DNTN-only: section DNTN hiện',
    hDntn.indexOf('DOANH NGHIỆP TƯ NHÂN') >= 0 &&
      hDntn.indexOf('1. Tên doanh nghiệp') >= 0);
  check('L2 M72 DNTN-only: các biến thể khác vẫn ẩn',
    hDntn.indexOf('CÔNG TY TNHH HAI THÀNH VIÊN') < 0 &&
      hDntn.indexOf('CÔNG TY CỔ PHẦN') < 0);

  const st2tv = R.newStore();
  st2tv.values['dn.loai_hinh'] = 'TNHH_2TV';
  const h2tv = R.renderBlocks(m72, st2tv, {
    docId: 'PLI_M72', flags: D.selectorFlagsOf('PLI_M72', st2tv)
  });
  check('L2 M72 đổi flag -> biến thể khác thay thế đúng',
    h2tv.indexOf('CÔNG TY TNHH HAI THÀNH VIÊN') >= 0 &&
      h2tv.indexOf('1. Tên công ty') >= 0 &&
      h2tv.indexOf('DOANH NGHIỆP TƯ NHÂN') < 0);

  // cond + SI cùng lúc: block cond=false thì không cần log SI
  const before = (() => { let n = 0; const od = console.debug;
    console.debug = function () { n++; }; R.renderBlocks(miniDoc([
      p('SI marker', { role: 'source-indicator', cond: ['flag_khong_co'] })
    ]), R.newStore(), { flags: {} }); console.debug = od; return n; })();
  check('L2 cond chặn trước SI: block bị filter -> không log', before === 0);
}

// ================================ 8. INPUT/CHK KHÔNG ĐỔI ATTRS QUAN TRỌNG ===
{
  const store = R.newStore();
  store.values['dn.ten_tieng_viet'] = 'CONG TY L2';
  store.checks['chk_tt_thanh_lap_moi'] = true;
  const h = R.renderBlocks(m02, store, { docId: 'PLI_M02' });
  check('L2 input value vẫn điền đúng từ store', h.indexOf('value="CONG TY L2"') >= 0);
  check('L2 checkbox checked attr giữ nguyên chuỗi contract cũ',
    h.indexOf('<input type="checkbox" class="chk-box" data-key="chk_tt_thanh_lap_moi" checked>') >= 0);
  check('L2 data-key input text giữ nguyên', /<input type="text" class="fld[^"]*" data-key="dn\.ten_tieng_viet"/.test(h));
  check('L2 data-field-id/aria-label vẫn sinh', /data-field-id="f_/.test(h));

  // đếm tổng input khớp walk schema (như countExpected của test_dom, đủ loop)
  function countExpected(blocks) {
    let ti = 0, cb = 0;
    function walk(runs) {
      (runs || []).forEach(function (r) {
        if (r && r.input) { if (r.input.chk !== undefined) cb++; else ti++; }
      });
    }
    (blocks || []).forEach(function (b) {
      if (b.t === 'p') walk(b.runs);
      else if (b.t === 'chk') cb++;
      else if (b.t === 'table') (b.rows || []).forEach(function (row) {
        row.cells.forEach(function (c) { walk(c.runs); });
      });
      // [Pin sync — owner N-only 2026-09-08] loop chỉ in N dòng dữ liệu,
      // không hàng trắng; render dưới dùng store rỗng (N=0) và không truyền
      // gridMeta (minUiRows=0) -> loop đóng góp 0 input (trước đây cols×blankRows)
      else if (b.t === 'loop') ti += 0;
    });
    return { ti: ti, cb: cb };
  }
  [m02, plii01].forEach(function (doc) {
    const exp = countExpected(doc.blocks);
    const html = R.renderBlocks(doc, R.newStore());
    const gotTi = (html.match(/<input type="text"/g) || []).length;
    const gotCb = (html.match(/<input type="checkbox"/g) || []).length;
    check('L2 ' + doc.id + ': tổng input text không đổi (' + exp.ti + ')', gotTi === exp.ti, 'got ' + gotTi);
    check('L2 ' + doc.id + ': tổng checkbox không đổi (' + exp.cb + ')', gotCb === exp.cb, 'got ' + gotCb);
  });

  // selectorHtml nguyên vẹn
  const selMeta = D.getFormSelector('PLI_M72');
  const selHtml = R.selectorHtml(selMeta, R.makeAccessors(stDntn));
  check('L2 selectorHtml: radio group + checked theo store',
    /class="doc-selector" role="radiogroup"/.test(selHtml) &&
      selHtml.indexOf('checked') >= 0);

  // bảng lặp vẫn render API cũ
  const stLoop = R.newStore();
  stLoop.loops.ds_nganh = [{ ma_nganh: '0111', ten_nganh: 'Trồng lúa' }];
  const hloop = R.renderBlocks(m02, stLoop);
  check('L2 loop ds_nganh: data-key loop:...:ma_nganh giữ nguyên',
    hloop.indexOf('loop:ds_nganh:0:ma_nganh') >= 0);
}

// ================================ 9. HARNESS app_web/dev/snapshot.html ======
{
  const hp = path.join(__dirname, 'dev', 'snapshot.html');
  check('L2 harness tồn tại app_web/dev/snapshot.html', fs.existsSync(hp));
  const sh = fs.readFileSync(hp, 'utf8');
  check('L2 harness tham chiếu ui/render.js + ui/style.css',
    sh.indexOf('/app_web/ui/render.js') >= 0 && sh.indexOf('/app_web/ui/style.css') >= 0);
  check('L2 harness fetch endpoint blocks + form_maps.json',
    sh.indexOf("/app/data/blocks/' + encodeURIComponent(docId) + '.json") >= 0 &&
      sh.indexOf('/app/data/form_maps.json') >= 0);
  check('L2 harness gọi renderBlocks + bindFootnoteRefs',
    sh.indexOf('R.renderBlocks(doc, store') >= 0 &&
      sh.indexOf('R.bindFootnoteRefs(section)') >= 0);
  check('L2 harness dựng store {values,checks,loops} + đọc ?values=',
    sh.indexOf('R.newStore()') >= 0 &&
      sh.indexOf("parseJsonParam('values')") >= 0 &&
      sh.indexOf("parseJsonParam('checks')") >= 0);
  check('L2 harness parse flag_ query + selectorFlagsOf',
    sh.indexOf('flag_') >= 0 && sh.indexOf('selectorFlagsOf') >= 0);
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
