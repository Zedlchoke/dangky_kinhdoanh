/* test_form_flow.js - kiểm thử KHÔNG GUI cho nghiệp vụ chọn mẫu biểu & state
 * (PLAN.md "Agent 1B — form-flow-state").
 *
 * Chạy:  node app_web/test_form_flow.js
 *
 * Dùng hàm THUẦN qua Helpers.FormFlow của ui/app.js (không DOM, không timer
 * trừ phần mô phỏng race tất định bằng Promise + setTimeout):
 *   1. Dữ liệu use_cases.json thật: bat_buoc trên mọi form; case
 *      chuyen_doi_hkd_sang_dn có forms_oneOf 4 mẫu loại trừ max=1.
 *   2. buildFormMeta: metadata theo docId (bat_buoc/ghi_chu/oneOf).
 *   3. formListHtml: bắt buộc checked+disabled kèm nhãn (Bắt buộc);
 *      tùy chọn mặc định unchecked, nhãn (Tùy chọn); draft override.
 *   4. applyOneOfExclusive: tick một mẫu trong nhóm -> bỏ tick mẫu khác
 *      cùng nhóm; generic với max>1.
 *   5. Gate export thuần: thiếu bắt buộc / oneOf rỗng / oneOf quá max ->
 *      blocking; đủ điều kiện -> không lỗi.
 *   6. Race token: Promise case cũ resolve MUỘN không được ghi state.
 *   7. saveOutcome: autosave thành công dirty=false; thất bại dirty=true.
 *   8. Draft round-trip: restoreSelection giữ đúng bắt buộc/tùy chọn/oneOf,
 *      activeDocId chỉ nhận doc hợp lệ; draft v1 qua migrateDraft vẫn nạp.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const App = require('./ui/app.js');            // Helpers.GridCtl + Helpers.FormFlow
const F = App.FormFlow;
const D = require('./ui/form-domain.js');      // migrateDraft cho test draft v1

const UC_PATH = path.join(__dirname, '..', 'app', 'data', 'use_cases.json');
const UC = JSON.parse(fs.readFileSync(UC_PATH, 'utf8'));

let passed = 0;
let failed = 0;
function check(name, cond, extra) {
  if (cond) {
    passed++;
    console.log('PASS  ' + name);
  } else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function countMatches(html, re) {
  const m = html.match(re);
  return m ? m.length : 0;
}
function caseById(id) {
  return UC.cases.filter(c => c.id === id)[0];
}

// ============================ 1. dữ liệu use_cases.json (schema_forms)
{
  const cd = caseById('chuyen_doi_hkd_sang_dn');
  check('case chuyen_doi_hkd_sang_dn ton tai', !!cd);
  const g = (cd.forms_oneOf || [])[0];
  check('chuyen_doi co forms_oneOf [{ids: 4 mau PLI_M01..M04, max:1}]',
    Array.isArray(cd.forms_oneOf) && cd.forms_oneOf.length === 1 &&
    JSON.stringify(g.ids.slice().sort()) ===
      JSON.stringify(['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']) &&
    g.max === 1, JSON.stringify(cd.forms_oneOf));
  check('4 form cua chuyen_doi deu bat_buoc=false (nhom loai tru)',
    cd.forms.length === 4 && cd.forms.every(f => f.bat_buoc === false));

  const missingMeta = [];
  UC.cases.forEach(c => (c.forms || []).forEach(f => {
    if (typeof f.bat_buoc !== 'boolean') missingMeta.push(c.id + ':' + f.mau);
  }));
  check('moi form trong moi case deu khai bao bat_buoc boolean',
    missingMeta.length === 0, missingMeta.join(','));

  check('use_cases.json co ghi chu contract schema_forms o dau file',
    !!UC.schema_forms && typeof UC.schema_forms.forms_oneOf === 'string' &&
    Object.keys(UC)[0] === 'schema_forms');
}

// ============================ 2. buildFormMeta
const metaCd = F.buildFormMeta(caseById('chuyen_doi_hkd_sang_dn'));
const metaCtcp = F.buildFormMeta(caseById('thanh_lap_ctcp'));
{
  check('buildFormMeta(chuyen_doi): dung 4 docId zero-pad',
    JSON.stringify(Object.keys(metaCd).sort()) ===
      JSON.stringify(['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']),
    JSON.stringify(Object.keys(metaCd).sort()));
  const oneGid = new Set(Object.keys(metaCd).map(id => metaCd[id].oneOf.gid));
  check('ca 4 form cung MOT nhom oneOf, max=1, bat_buoc=false',
    oneGid.size === 1 &&
    Object.keys(metaCd).every(id => !metaCd[id].bat_buoc &&
      metaCd[id].oneOf.max === 1 &&
      metaCd[id].oneOf.ids.length === 4));

  check('buildFormMeta(ctcp): M04/M07 bat buoc, M08 tuy chon, khong oneOf',
    metaCtcp.PLI_M04.bat_buoc === true && metaCtcp.PLI_M07.bat_buoc === true &&
    metaCtcp.PLI_M08.bat_buoc === false &&
    !metaCtcp.PLI_M04.oneOf && !metaCtcp.PLI_M08.oneOf);

  // formIdOf zero-pad regression (mau 6 phai ra PLI_M06)
  check('formIdOf({pl:I,mau:6}) = PLI_M06 (khong mat so 0)',
    F.formIdOf({ pl: 'I', mau: 6 }) === 'PLI_M06');
}

// ============================ 3. formListHtml (render danh sách mẫu)
{
  const docsCtcp = [
    { id: 'PLI_M04', ten_mau: 'Giấy đề nghị đăng ký DN (CTCP)' },
    { id: 'PLI_M07', ten_mau: 'Danh sách cổ đông sáng lập' },
    { id: 'PLI_M08', ten_mau: 'Danh sách cổ đông nước ngoài' }
  ];
  const html = F.formListHtml(docsCtcp, metaCtcp, {});
  check('required -> input checked VA disabled',
    /value="PLI_M04" checked disabled/.test(html) &&
    /value="PLI_M07" checked disabled/.test(html));
  check('optional -> mac dinh KHONG checked, khong disabled',
    html.indexOf('<input type="checkbox" class="form-tick" value="PLI_M08">') >= 0);
  check('nhan ro ràng: 2 (Bắt buộc) + 1 (Tùy chọn)',
    countMatches(html, /\(Bắt buộc\)/g) === 2 &&
    countMatches(html, /\(Tùy chọn\)/g) === 1);

  const docsCd = ['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']
    .map(id => ({ id, ten_mau: id }));
  const htmlCd = F.formListHtml(docsCd, metaCd, {});
  check('chuyen_doi: ca 4 form tùy chon DEU chưa tick mặc định',
    countMatches(htmlCd, /checked/g) === 0 &&
    countMatches(htmlCd, /disabled/g) === 0 &&
    countMatches(htmlCd, /\(Tùy chọn\)/g) === 4);

  // draft đã chọn optional -> tick lại khi restore (checkedMap override),
  // nhưng KHÔNG bao giờ được disabled
  const htmlDraft = F.formListHtml(docsCtcp, metaCtcp, { PLI_M08: true });
  check('draft.checkedForms co PLI_M08 -> optional duoc tick lai (khong disabled)',
    /value="PLI_M08" checked/.test(htmlDraft) &&
    !new RegExp('value="PLI_M08" checked disabled').test(htmlDraft));

  // esc() chống XSS qua ten_mau
  const htmlEsc = F.formListHtml([{ id: 'X1', ten_mau: '<b>&x</b>' }],
    { X1: { bat_buoc: true } }, {});
  check('ten_mau duoc escape trong formListHtml',
    htmlEsc.indexOf('&lt;b&gt;&amp;x&lt;/b&gt;') >= 0);
}

// ============================ 4. oneOf loại trừ (case thật 4 form)
{
  /* Contract giống call-site trong app.js: caller cập nhật trạng thái mới
   * của changedId trong map TRƯỚC khi gọi (như handler .form-tick). */
  let cf = { PLI_M01: true };
  cf = F.applyOneOfExclusive(metaCd, cf, 'PLI_M01');
  check('tick PLI_M01 -> chi PLI_M01 duoc chon',
    cf.PLI_M01 === true && !cf.PLI_M02 && !cf.PLI_M03 && !cf.PLI_M04);

  cf.PLI_M03 = true; // người dùng vừa tick thêm PLI_M03
  cf = F.applyOneOfExclusive(metaCd, cf, 'PLI_M03');
  check('tick PLI_M03 -> tu bo tick PLI_M01 (loai tru max=1)',
    cf.PLI_M03 === true && !cf.PLI_M01 && !cf.PLI_M02 && !cf.PLI_M04,
    JSON.stringify(cf));

  const before = JSON.stringify(cf);
  cf.PLI_M03 = false; // người dùng bỏ tick
  cf = F.applyOneOfExclusive(metaCd, cf, 'PLI_M03');
  check('bo tick khong anh huong form khac',
    !cf.PLI_M03 && !cf.PLI_M01 && JSON.stringify(cf) !== before);

  // generic max=2: tick thu tu 3 -> phan tu tick SOM NHAT bi loai
  const metaMax2 = F.buildFormMeta({
    forms: [
      { pl: 'X', mau: 1 }, { pl: 'X', mau: 2 }, { pl: 'X', mau: 3 }
    ],
    forms_oneOf: [{ ids: ['PLX_M01', 'PLX_M02', 'PLX_M03'], max: 2 }]
  });
  let m2 = {};
  ['PLX_M01', 'PLX_M02', 'PLX_M03'].forEach(id => {
    m2[id] = true;
    m2 = F.applyOneOfExclusive(metaMax2, m2, id);
  });
  check('max=2: tick thu 3 tu loai phan tu dau (dung luat chung)',
    m2.PLX_M01 === false && m2.PLX_M02 === true && m2.PLX_M03 === true,
    JSON.stringify(m2));
}

// ============================ 5. gate export thuần
{
  let errs = F.checkFormSelection(metaCd, [], {});
  check('chuyen_doi chua chon mau nao -> blocking FORM_ONEOF_EMPTY',
    errs.length === 1 && errs[0].code === 'FORM_ONEOF_EMPTY' &&
    errs[0].severity === 'blocking', JSON.stringify(errs));

  errs = F.checkFormSelection(metaCd, ['PLI_M02'], {});
  check('chuyen_doi chon dung 1 mau -> khong loi gate',
    errs.length === 0, JSON.stringify(errs));

  errs = F.checkFormSelection(metaCd, ['PLI_M02', 'PLI_M04'], {});
  check('du lieu 2 mau cung nhom (UI da khoa nhung van validate) -> FORM_ONEOF_EXCEED blocking',
    errs.length === 1 && errs[0].code === 'FORM_ONEOF_EXCEED' &&
    errs[0].severity === 'blocking', JSON.stringify(errs));

  errs = F.checkFormSelection(metaCtcp, ['PLI_M07'], {});
  check('ctcp thieu PLI_M04 -> FORM_REQUIRED_MISSING blocking tro dung docId',
    errs.length === 1 && errs[0].code === 'FORM_REQUIRED_MISSING' &&
    errs[0].severity === 'blocking' && errs[0].docId === 'PLI_M04');

  errs = F.checkFormSelection(metaCtcp, ['PLI_M04', 'PLI_M07', 'PLI_M08'], {});
  check('ctcp du bat buoc (+optional) -> khong loi gate', errs.length === 0,
    JSON.stringify(errs));

  // shape error khop contract {key, docId, code, message, severity}
  const e = F.checkFormSelection(metaCtcp, [], {})[0];
  check('loi gate co day du key/docId/code/message/severity',
    ['key', 'docId', 'code', 'message', 'severity'].every(k => typeof e[k] !== 'undefined'));
}

// ============================ 7. saveOutcome (autosave/quickSave)
{
  const ok = F.saveOutcome(true);
  const bad = F.saveOutcome(false);
  check('autosave thanh cong -> dirty=false + saveState=saved',
    ok.dirty === false && ok.saveState === 'saved');
  check('autosave that bai -> dirty=true + saveState=error (bao loi luu)',
    bad.dirty === true && bad.saveState === 'error');
}

// ============================ 8. draft round-trip (restoreSelection)
{
  const docsCd = ['PLI_M01', 'PLI_M02', 'PLI_M03', 'PLI_M04']
    .map(id => ({ id, ten_mau: id }));
  const docsCtcp = [
    { id: 'PLI_M04', ten_mau: 'M04' },
    { id: 'PLI_M07', ten_mau: 'M07' },
    { id: 'PLI_M08', ten_mau: 'M08' }
  ];

  let r = F.restoreSelection(metaCd, docsCd,
    { checkedForms: ['PLI_M02'], activeDocId: 'PLI_M02' });
  check('draft round-trip: giu dung selection PLI_M02 (cac mau khac bo tick)',
    r.checkedForms.PLI_M02 === true &&
    !r.checkedForms.PLI_M01 && !r.checkedForms.PLI_M03 && !r.checkedForms.PLI_M04 &&
    r.activeDocId === 'PLI_M02');

  r = F.restoreSelection(metaCd, docsCd,
    { checkedForms: ['PLI_M01', 'PLI_M04'], activeDocId: 'PLI_M01' });
  check('draft chua 2 mau cung nhom oneOf -> tick sau thang (PLI_M04), '
    + 'activeDocId khong con duoc chon -> fallback ve mau dang chon',
    r.checkedForms.PLI_M04 === true && !r.checkedForms.PLI_M01 &&
    r.activeDocId === 'PLI_M04', JSON.stringify(r));

  r = F.restoreSelection(metaCtcp, docsCtcp, { checkedForms: ['PLI_M08'] });
  check('draft thieu required -> bat buoc van duoc tick lai + giu optional',
    r.checkedForms.PLI_M04 === true && r.checkedForms.PLI_M07 === true &&
    r.checkedForms.PLI_M08 === true && r.activeDocId === 'PLI_M04',
    JSON.stringify(r));

  r = F.restoreSelection(metaCd, docsCd,
    { checkedForms: ['PLI_M03'], activeDocId: 'PLI_M99' });
  check('activeDocId khong hop le -> fallback mau dau tien dang chon',
    r.activeDocId === 'PLI_M03');

  r = F.restoreSelection(metaCd, docsCd, null);
  check('khong co draft -> mac dinh: chang ai duoc tick, activeDocId=null '
    + '(cho user chon loai hinh truoc)',
    Object.keys(r.checkedForms).every(k => !r.checkedForms[k]) &&
    r.activeDocId === null);

  // draft v1 cu qua migrateDraft: checkedForms=[] -> van nap duoc an toan
  const v1 = D.migrateDraft({
    v: 1, caseId: 'chuyen_doi_hkd_sang_dn', autoSum: false,
    store: { values: {}, checks: {}, loops: {} }
  });
  r = F.restoreSelection(metaCd, docsCd, v1);
  check('draft v1 (checkedForms=[]) -> restore khong roi, mac dinh khong tick optional',
    Array.isArray(v1.checkedForms) && v1.checkedForms.length === 0 &&
    Object.keys(r.checkedForms).every(k => !r.checkedForms[k]));
}

// ============================ 9. GridCtl van song (bao ve test lien quan)
{
  const store = { loops: {} };
  const res = App.GridCtl.addRow(store, 'ds_test');
  check('GridCtl (Helpers.GridCtl) van hoat dong sau cac thay doi',
    res.index === 0 && !!res.id && store.loops.ds_test.length === 1);
}

// ============ 6. race token: Promise case cũ resolve MUỘN (tất định)
/* Mô phỏng đúng guard mà onCaseChange() dùng: request cũ cấp seq trước,
 * resolve sau RequestToken mới -> phải BỊ bỏ qua, không ghi state. */
function simulateRace() {
  return new Promise(function (resolve) {
    const sim = { docs: [], caseId: null, renders: [] };

    function loadCase(caseName, delayMs, onDone) {
      const seq = F.RequestToken.next();          // như var seq = RequestToken.next()
      setTimeout(function () {                    // getBlocks(...) resolve muộn/sớm
        if (!F.RequestToken.fresh(seq)) {         // guard trong onCaseChange()
          onDone('stale-skipped');
          return;
        }
        sim.docs = ['blocks_' + caseName];
        sim.caseId = caseName;
        sim.renders.push(caseName);
        onDone('applied');
      }, delayMs);
    }

    // case CŨ cấp token TRƯỚC nhưng resolve SAU (delay lớn hơn)
    loadCase('CASE_OLD', 60, function (oldResult) {
      // case MỚI đã cấp token sau và resolve trước
      check('race: request moi (token moi) duoc ghi vao state',
        sim.caseId === 'CASE_NEW' && sim.docs.join() === 'blocks_CASE_NEW');
      check('race: ket qua case CU resolve muon BI BO QUA (khong ghi de)',
        oldResult === 'stale-skipped' &&
        sim.renders.indexOf('CASE_OLD') < 0);
      check('RequestToken semantics: token cu khong bao gio fresh lai',
        !F.RequestToken.fresh(F.RequestToken.next() - 1));

      // double-guard: sau await trung gian (ui_layouts), token cũ vẫn bị chặn
      // nếu user kịp đổi case thêm lần nữa trong lúc chờ
      const seqLate = F.RequestToken.next();   // request đang chờ ui_layouts
      F.RequestToken.next();                   // user đổi case tiếp trong lúc chờ
      Promise.resolve().then(function () {
        check('race: guard van dung sau Promise trung gian (uiLayouts path)',
          !F.RequestToken.fresh(seqLate));
        resolve();
      });
    });
    loadCase('CASE_NEW', 10, function () {});
  });
}

simulateRace().then(function () {
  console.log('-'.repeat(60));
  console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
  process.exit(failed === 0 ? 0 : 1);
}).catch(function (e) {
  console.error('LOI TEST:', e);
  process.exit(1);
});
