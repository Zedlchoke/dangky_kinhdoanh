/* test_p3_security.js — LANE P3: escaping/injection, tên file export, log.
 *
 * Chạy:  node app_web/test_p3_security.js
 *
 * Phạm vi (suite MỚI, KHÔNG sửa production):
 *  1. HTML escaping của Render.renderBlocks: giá trị người dùng chứa
 *     `<script>`, `"><img onerror>`, `" onmouseover=`, `' onfocus=`, `{{7*7}}`,
 *     `{#loop}`, backtick, ` / `, entity đã escape, `javascript:` … phải được
 *     escape — KHÔNG xuất hiện thô trong HTML (không tự sinh tag/attribute).
 *  2. DOCX injection (tools/docx_render): giá trị chứa `{{7*7}}`, `{tag}`,
 *     `{#loop}`, `{?flag}`, `{_stt}`, XML spec chars — không được suy diễn thành
 *     tag/loop/cond của engine, XML đầu ra phải well-formed, không còn token.
 *  3. Tên hồ sơ / tên file export: giá trị chứa `../`, `..\`, NUL, ký tự điều
 *     khiển, tên >255 byte — chạy đường export THẬT (Bridge.export của
 *     app_web/main.py, dựng module `webview` giả để import được trên máy
 *     không có pywebview) và đo xem thư mục đích có thoát ra ngoài repo hay
 *     không. Production sanitize qua _sanitize_name() (lane P3.2, commit
 *     "fix(P3.2 export)") -> case này là check PASS/FAIL, không còn finding.
 *  4. Log: quét tĩnh app_web/ui/*.js + app_web/main.py — không được in giá trị
 *     nhạy cảm (MST/CCCD/họ tên) vào console.
 *
 * Mọi lỗi thật của production được ghi bằng finding() (suite vẫn exit 0,
 * theo quy ước lane: KHÔNG sửa production trong lane này).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const R = require('./ui/render.js');
const FD = require('./ui/form-domain.js');

const ROOT = path.join(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'app', 'data', 'blocks');

let passed = 0, failed = 0;
const FINDINGS = [];
function check(name, cond, extra) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else {
    failed++;
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function finding(name, evidence) {
  FINDINGS.push(name);
  console.log('FIND  ' + name + (evidence ? '  [' + evidence + ']' : ''));
}
function checkSec(name, ok, evidence, ftext) {
  if (ok) { passed++; console.log('PASS  ' + name); }
  else finding(ftext || name, evidence);
}
function section(t) { console.log('\n===== ' + t + ' ====='); }
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}
function noThrow(fn) {
  try { return { ok: true, val: fn() }; }
  catch (e) { return { ok: false, err: (e && e.message) || String(e) }; }
}
function newStore() { return { values: {}, checks: {}, loops: {} }; }
function gridMetaForDoc(docId) {
  const m = Object.assign({}, FD.GRID_META);
  const fm = FD.FORM_GRID_META[docId];
  if (fm && fm.loops) Object.assign(m, fm.loops);
  return m;
}
/* PLI_M72 chỉ render ra nội dung khi selector loại hình đã chọn. */
const SEED_VALUES = { PLI_M72: { 'dn.loai_hinh': 'DNTN' } };
function renderDoc(docId, store) {
  const doc = loadProd(docId);
  Object.assign(store.values, SEED_VALUES[docId] || {});
  const sel = FD.getFormSelector(docId);
  const selHtml = sel ? R.selectorHtml(sel, R.makeAccessors(store)) : '';
  return R.renderBlocks(doc, store, {
    docId: docId,
    fieldMeta: FD.FIELD_META,
    gridMeta: gridMetaForDoc(docId),
    sectionContracts: FD.sectionContractsOf(docId),
    flags: FD.selectorFlagsOf(docId, store),
    selectorHtml: selHtml
  });
}
function count(hay, needle) {
  let n = 0, i = 0;
  if (!needle) return 0;
  while ((i = hay.indexOf(needle, i)) >= 0) { n++; i += needle.length; }
  return n;
}

// ======================================================================
// 1. HTML escaping — renderBlocks với giá trị hostil
// ======================================================================
section('1. renderBlocks: gia tri hostil phai duoc escape');
/* Tự kiểm: suite này cố tình dùng ký tự điều khiển trong PAYLOAD, nhưng phải
 * ở dạng escape \uXXXX — file nguồn KHÔNG được chứa byte điều khiển thô
 * (git sẽ coi là file nhị phân, review/không thể diff). */
check('P3-S0: nguon suite khong chua byte dieu khien tho (file van la text)',
  !/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(
    fs.readFileSync(__filename, 'utf8')));
/* payload: chuỗi người dùng gõ.
 *  rawForbidden : chuỗi KHÔNG được xuất hiện thô trong HTML (phải bị escape)
 *  expectEscaped: chuỗi escape tương ứng PHẢI xuất hiện */
const PAYLOADS = [
  ['<script>alert(1)</script>', ['<script>', '<script>alert'], ['&lt;script&gt;alert(1)&lt;/script&gt;']],
  ['"><img src=x onerror=alert(1)>', ['<img', '<img src=x', '<img onerror'], ['&lt;img src=x onerror=alert(1)&gt;']],
  ['" onmouseover="alert(1)', ['" onmouseover=', '" onmouseover="alert'], ['&quot; onmouseover=&quot;alert(1)']],
  ["' onfocus='alert(1)' autofocus='", ["' onfocus='"], ['&#39; onfocus=&#39;alert(1)&#39; autofocus=&#39;']],
  ['`backtick` + ${tpl} + <<>>', [], ['`backtick` + ${tpl} + &lt;&lt;&gt;&gt;']],
  ['{{7*7}}', [], ['{{7*7}}']],
  ['{{#ds_nganh}} {/ds_nganh} {_stt}', [], ['{{#ds_nganh}} {/ds_nganh} {_stt}']],
  ['{#ds_nganh}{/ds_nganh}', [], ['{#ds_nganh}{/ds_nganh}']],
  ['a / b // c \\\\ d', [], ['a / b // c']],
  ['&lt;script&gt; đã escape', [], ['&amp;lt;script&amp;gt;']],
  ['javascript:alert(1)', [], ['javascript:alert(1)']],
  ['Đại lý Điện tử 🙃 \u0000 NUL', [], ['Đại lý Điện tử 🙃 \u0000 NUL']]
];
const HOSTILE_DOCS = ['PLI_M02', 'PLI_M06', 'PLI_M72'];
/* Ô đưa payload vào: giá trị trường + ô text của bảng lặp.
 * Mỗi mẫu có metadata riêng (PLI_M06 KHÔNG có dn.ten_tieng_viet, bảng của nó
 * là ds_thanh_vien_tnhh; PLI_M72 có 5 bảng ds_nganh_*) nên vị trí được resolve
 * THEO MẪU qua inputKeysOf / loopBlock đầu tiên của chính mẫu đó. */
function inputKeysOf(doc) {
  const keys = [];
  (function walk(x) {
    if (Array.isArray(x)) return x.forEach(walk);
    if (!x || typeof x !== 'object') return;
    if (x.input && x.input.key) keys.push(x.input.key);
    Object.keys(x).forEach(k => walk(x[k]));
  })(doc.blocks);
  return keys;
}
function firstLoopOf(doc) {
  return (doc.blocks || []).filter(b => b.t === 'loop')[0] || null;
}
function firstTextTag(loopBlock) {
  const c = (loopBlock.cols || []).filter(x => (x.type || 'text') === 'text')[0] ||
    (loopBlock.cols || [])[0];
  return c ? c.tag : null;
}
function positionsFor(docId) {
  const doc = loadProd(docId);
  const out = [];
  if (inputKeysOf(doc).indexOf('dn.ten_tieng_viet') >= 0) {
    out.push({ label: 'field dn.ten_tieng_viet',
      put: (st, v) => { st.values['dn.ten_tieng_viet'] = v; },
      probe: 'dn.ten_tieng_viet' });
  }
  const lb = firstLoopOf(doc);
  const tag = lb && firstTextTag(lb);
  if (lb && tag) {
    out.push({ label: 'loop ' + lb.loop + '.' + tag,
      put: (st, v) => { st.loops[lb.loop] = [{ la_nganh_chinh: 'X', [tag]: v }]; },
      probe: 'loop:' + lb.loop });
  }
  return out;
}
const ALL_DOCS_HTML = {};
const POS_COUNT = {};
HOSTILE_DOCS.forEach(id => {
  const POSITIONS = positionsFor(id);
  POS_COUNT[id] = POSITIONS.length;
  PAYLOADS.forEach(([payload, rawForbidden, expectEscaped], pi) => {
    POSITIONS.forEach((pos, oi) => {
      const st = newStore();
      pos.put(st, payload);
      const key = id + '|' + pi + '|' + oi;
      const r = noThrow(() => renderDoc(id, st));
      if (!r.ok) {
        check('P3-S1[' + key + '] render khong nem', false, r.err);
        return;
      }
      const html = r.val;
      ALL_DOCS_HTML[key] = html;
      if (html.indexOf(pos.probe) < 0) {
        check('P3-S1[' + key + '] payload vao dung o "' + pos.label + '"',
          false, 'khong tim thay ' + pos.probe + ' trong HTML');
        return;
      }
      /* 1) giá trị phải vào được DOM (đã escape) */
      const escOk = expectEscaped.every(e => count(html, e) >= 1) ||
        (expectEscaped.length === 0 && count(html, payload) >= 1);
      /* 2) không token nguy hiểm nào xuất hiện thô */
      const leak = rawForbidden.filter(f => count(html, f) >= 1);
      checkSec('P3-S1[' + key + '] ' + id + ' ' + pos.label + ' "<' +
          payload.slice(0, 22) + '…" escaped, khong thô',
        escOk && leak.length === 0,
        leak.length ? 'leak=' + JSON.stringify(leak) +
          (escOk ? '' : ' | khong thay chuoi escaped ' + JSON.stringify(expectEscaped))
          : JSON.stringify(expectEscaped),
        'F-P3-SEC-HTML renderBlocks xuất giá trị người dùng thô (không escape)');
    });
  });
});
/* Đánh dấu mốc: số check ở mục 1 = |docs| × |payloads| × |positions| */
check('P3-S1b: moi payload xuat hien DUNG mot lan trong output (khong nhan ban)',
  (() => {
    const html = ALL_DOCS_HTML['PLI_M02|0|0'] || '';
    return count(html, '&lt;script&gt;alert(1)&lt;/script&gt;') === 1;
  })(), 'so lan xuat hien khong dung 1');

/* `{{7*7}}` không được suy diễn ở lớp JS: phải còn nguyên literal, không có 14 */
check('P3-S1c: {{7*7}} giu nguyen literal (khong bi tinh thanh 14)',
  (() => {
    const html = ALL_DOCS_HTML['PLI_M02|5|0'] || '';
    /* '>14<' là số footnote hợp lệ của mẫu nên chỉ được soi đúng ô value= */
    return count(html, '{{7*7}}') === 1 && count(html, 'value="14"') === 0;
  })());
/* `{#ds_nganh}` trong GIÁ TRỊ không được tạo thêm bảng: số bảng ds_nganh không đổi */
check('P3-S1d: {#ds_nganh} trong gia tri KHONG sinh them bang loop',
  (() => {
    const clean = renderDoc('PLI_M02', (() => {
      const st = newStore();
      st.loops.ds_nganh = [{ ma_nganh: '0111', ten_nganh: 'Ngành', la_nganh_chinh: 'X' }];
      return st;
    })());
    const hostile = ALL_DOCS_HTML['PLI_M02|7|1'] || '';
    const nClean = count(clean, 'data-loop="ds_nganh"');
    const nHost = count(hostile, 'data-loop="ds_nganh"');
    return nClean === nHost && nHost >= 1;
  })(), 'so bang ds_nganh doi lech khi gia tri chua token loop');

// ======================================================================
// 2. DOCX injection — tools/docx_render qua driver python
// ======================================================================
section('2. DOCX render: gia tri hostil khong duoc thanh tag/loop/cond');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-sec-'));
const DOCX_PAYLOADS = ['{{7*7}}', '{dn.ten_tieng_viet}', '{#ds_nganh}{/ds_nganh}',
  '{?loai_hinh_dntn}{/loai_hinh_dntn}', '{_stt}', '<script>alert(1)</script>',
  '&<>\'"', ']]>CDATA]]>', 'A&B<C>D', '🙂\u0000NUL'];
const spec = { renders: [] };
DOCX_PAYLOADS.forEach((p, i) => {
  spec.renders.push({
    id: 'PLI_M02', label: 'PLI_M02#' + i,
    template: path.join(ROOT, 'app', 'templates', 'PLI_M02.docx'),
    out: path.join(TMP, 'm02_' + i + '.docx'),
    data: {
      'dn.ten_tieng_viet': p,
      'dn.ma_so_dn': '031234567890',
      ds_nganh: [{ ten_nganh: p, ma_nganh: '0111', chi_tiet: '', la_nganh_chinh: 'X' }]
    },
    tables_meta: null,
    expect_present: [], expect_absent: [], markers: [],
    /* engine PHẢI escape ngoặc nhọn của dữ liệu (safe_escape) */
    expect_escaped: (p === '{{7*7}}') ? '&#123;&#123;7*7&#125;&#125;' : null,
    forbid_raw: (p.indexOf('{') >= 0) ? p : null
  });
});
/* đo mốc: 1 dòng ds_nganh khi giá trị sạch -> để so số dòng khi giá trị hostil */
spec.renders.push({
  id: 'PLI_M02', label: 'PLI_M02#clean',
  template: path.join(ROOT, 'app', 'templates', 'PLI_M02.docx'),
  out: path.join(TMP, 'm02_clean.docx'),
  data: { 'dn.ten_tieng_viet': 'SACH', 'dn.ma_so_dn': '031234567890',
    ds_nganh: [{ ten_nganh: 'SACH', ma_nganh: '0111', chi_tiet: '', la_nganh_chinh: 'X' }] },
  tables_meta: null, expect_present: [], expect_absent: [], markers: []
});
const specPath = path.join(TMP, 'spec.json');
fs.writeFileSync(specPath, JSON.stringify(spec), 'utf8');
const driverSrc = [
  'import json, os, re, sys, zipfile',
  'import xml.etree.ElementTree as ET',
  'sys.path.insert(0, os.getcwd())',
  'from tools.docx_render import write_rendered, LEFTOVER_RE',
  'def nest(data):',
  '    out = {}',
  '    for k, v in data.items():',
  '        parts = str(k).split(".")',
  '        if len(parts) == 1:',
  '            out[k] = v; continue',
  '        cur = out',
  '        for p in parts[:-1]:',
  '            nxt = cur.get(p)',
  '            if not isinstance(nxt, dict):',
  '                nxt = {}; cur[p] = nxt',
  '            cur = nxt',
  '        cur[parts[-1]] = v',
  '    return out',
  'results = []',
  'spec = json.load(open(sys.argv[1], encoding="utf-8"))',
  'for r in spec["renders"]:',
  '    item = {"label": r.get("label") or r["id"]}',
  '    try:',
  '        write_rendered(r["template"], nest(r["data"]), r["out"],',
  '                       tables_meta=r.get("tables_meta"))',
  '        z = zipfile.ZipFile(r["out"])',
  '        parts = [n for n in z.namelist()',
  '                 if n.startswith("word/") and (n.endswith("document.xml")',
  '                    or "header" in n or "footer" in n)]',
  '        xml = "".join(z.read(n).decode("utf-8") for n in parts)',
  '        z.close()',
  '        try:',
  '            ET.fromstring(xml.encode("utf-8"))',
  '            item["wellformed"] = True',
  '        except Exception as exc:',
  '            item["wellformed"] = False',
  '            item["xml_err"] = "%s: %s" % (type(exc).__name__, exc)',
  '        item["bytes"] = len(xml)',
  '        item["leftover"] = sorted(set(LEFTOVER_RE.findall(xml)))',
  '        item["raw_braces"] = xml.count("{") + xml.count("}")',
  '        item["rows_ds_nganh"] = xml.count(r.get("row_probe", "0101"))',
  '        item["forbid_eval_hit"] = (xml.count(r["forbid_raw"]) if r.get("forbid_raw") else 0)',
  '        item["escaped_form_ok"] = (xml.count(r["expect_escaped"]) if r.get("expect_escaped") else 1)',
  '    except Exception as exc:',
  '        item["error"] = "%s: %s" % (type(exc).__name__, exc)',
  '    results.append(item)',
  'print(json.dumps(results, ensure_ascii=False))'
].join('\n');
const pyPath = path.join(TMP, 'driver.py');
fs.writeFileSync(pyPath, driverSrc, 'utf8');
/* row_probe: mã ngành 0111 chỉ có ở dòng dữ liệu ds_nganh -> đếm số dòng */
spec.renders.forEach(r => { r.row_probe = '0101'; });
fs.writeFileSync(specPath, JSON.stringify(spec), 'utf8');

function runPy(specFile) {
  const { execSync } = require('child_process');
  const INTERPS = ['python -X utf8', 'python3 -X utf8'];
  for (let i = 0; i < INTERPS.length; i++) {
    try {
      const out = execSync(INTERPS[i] + ' "' + pyPath + '" "' + specFile + '"', {
        cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      return JSON.parse(String(out).trim().split(/\r?\n/).pop());
    } catch (e) {
      const status = (e && e.status != null) ? e.status : 1;
      const noInterp = status === 127 || (e && e.code === 'ENOENT');
      if (!noInterp || i === INTERPS.length - 1) {
        return [{ label: '@driver',
          error: 'python exit ' + status + ': ' +
            String((e && e.stderr) || (e && e.message) || '').slice(0, 300) }];
      }
    }
  }
  return [{ label: '@driver', error: 'khong chay duoc python' }];
}
const RES = runPy(specPath);
const byLabel = {};
RES.forEach(r => { byLabel[r.label] = r; });

check('P3-S2a: driver python chay duoc, du ' + (DOCX_PAYLOADS.length + 1) + ' ban render',
  DOCX_PAYLOADS.every((p, i) => byLabel['PLI_M02#' + i] && !byLabel['PLI_M02#' + i].error),
  JSON.stringify(RES.filter(r => r.error).map(r => r.label + ': ' + r.error)));

DOCX_PAYLOADS.forEach((p, i) => {
  const r = byLabel['PLI_M02#' + i] || {};
  const ok = !r.error && r.wellformed === true && r.leftover && r.leftover.length === 0 &&
    r.raw_braces === 0 && !(r.forbid_eval_hit > 0) && r.escaped_form_ok >= 1;
  const isCtrl = /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(p);
  checkSec('P3-S2[' + i + '] DOCX gia tri "' + p.slice(0, 24) +
      '" -> XML well-formed, khong con token, khong bi suy dien', ok,
    JSON.stringify({ error: r.error, wf: r.wellformed, xml_err: r.xml_err,
      leftover: r.leftover, raw_braces: r.raw_braces,
      raw_token_con_so: r.forbid_eval_hit, escaped: r.escaped_form_ok }),
    isCtrl
      ? 'F-P3-SEC-NUL gia tri chua ky tu dieu khien (NUL) lam XML DOCX KHONG '
        + 'well-formed (Word se khong mo duoc file)'
      : 'F-P3-SEC-DOCX gia tri nguoi dung bi engine doc thanh tag/loop/cond');
});
check('P3-S2b: gia tri hostil KHONG lam doi so dong bang nganh (chong loop injection)',
  (() => {
    const clean = byLabel['PLI_M02#clean'] || {};
    return DOCX_PAYLOADS.every((p, i) => {
      const r = byLabel['PLI_M02#' + i] || {};
      return !r.error && r.rows_ds_nganh === clean.rows_ds_nganh;
    });
  })(),
  JSON.stringify(RES.map(r => ({ l: r.label, rows: r.rows_ds_nganh }))));
check('P3-S2c: ky tu XML dac biet (& < >) duoc escape trong w:t',
  (() => {
    const rA = byLabel['PLI_M02#8'] || {};   // 'A&B<C>D'
    const rQ = byLabel['PLI_M02#6'] || {};   // '&<>'"'
    return !rA.error && rA.wellformed === true && !rQ.error;
  })(), JSON.stringify([byLabel['PLI_M02#8'], byLabel['PLI_M02#6']]));

// ======================================================================
// 3. Tên hồ sơ / tên file export — đường export THẬT (Bridge.export)
// ======================================================================
section('3. Export: ten ho so chua ../ ..\\ NUL control >255 byte');
/* Production main.py:
 *   case_id = _sanitize_name(case_id, "ho_so", 255 - 1 - len(ts))
 *   out_dir = ROOT / "generated_ho_so" / ("%s_%s" % (case_id, ts))
 *   out_file = out_dir / ("%s.docx" % _sanitize_name(fid, "form", 250))
 * kiểm chứng bằng cách chạy thật qua Bridge.export. */
const mainSrc = fs.readFileSync(path.join(ROOT, 'app_web', 'main.py'), 'utf8');
const hasSanitize = /(sanitize|secure_filename|basename|\bname\b\s*=|re\.sub|\.replace\(["']\.\.)/
  .test(mainSrc.split('def export').slice(1).join('def export'));
checkSec('P3-S3a: main.py export CO buoc sanitize ten ho so/ten file',
  hasSanitize,
  'khong tim thay sanitize/basename/re.sub trong Bridge.export (app_web/main.py)',
  'F-P3-SEC-PATH Bridge.export khong sanitize case_id truoc khi ghep vao duong dan');

/* Chạy thật qua fake `webview` module (máy này không có pywebview/WebView2). */
const HOSTILE_NAMES = [
  ['../P3_SEC_ESCAPE_A', 'dấu ../'],
  ['../../../P3_SEC_ESCAPE_B', 'ba dấu ../'],
  ['..\\P3_SEC_BACKSLASH', 'dấu ..\\'],
  ['\u0000NUL', 'ky tu NUL'],
  ['ten\u0007bel\u001fus', 'ky tu dieu khien'],
  ['t'.repeat(300), 'ten 300 byte'],
  ['Đại lý 🙃/con', 'dau gach cheo + unicode']
];
const pyPath3 = path.join(TMP, 'export_probe.py');
const spec3 = { names: HOSTILE_NAMES.map(n => n[0]), forms: [{ id: 'PLI_M02' }] };
const spec3Path = path.join(TMP, 'spec3.json');
fs.writeFileSync(pyPath3, [
  'import json, os, sys, types, shutil',
  'fake = types.ModuleType("webview")',
  'fake.create_window = lambda *a, **k: None',
  'fake.start = lambda *a, **k: None',
  'sys.modules["webview"] = fake',
  'sys.path.insert(0, os.getcwd())',
  'import importlib.util',
  'spec = importlib.util.spec_from_file_location("p3main", "app_web/main.py")',
  'mod = importlib.util.module_from_spec(spec)',
  'spec.loader.exec_module(mod)',
  'b = mod.Bridge()',
  'ROOT = os.path.abspath(".")',
  'spec = json.load(open(sys.argv[1], encoding="utf-8"))',
  'out = []',
  'ghs = os.path.join(ROOT, "generated_ho_so")',
  'before = set(os.listdir(ghs)) if os.path.isdir(ghs) else set()',
  'for name in spec["names"]:',
  '    item = {"name": name}',
  '    try:',
  '        res = b.export({"case_id": name, "forms": spec["forms"],',
  '                        "data": {"dn.ten_tieng_viet": "P3SEC"}})',
  '        item["ok"] = res.get("ok")',
  '        item["dir"] = res.get("dir")',
  '        item["files"] = res.get("files")',
  '        item["errors"] = res.get("errors")',
  '        if res.get("dir"):',
  '            item["escaped"] = not os.path.abspath(res["dir"]).startswith(ROOT + os.sep)',
  '            shutil.rmtree(res["dir"], ignore_errors=True)',
  '        if res.get("zip") and os.path.exists(res["zip"]):',
  '            item["zip_escaped"] = not os.path.abspath(res["zip"]).startswith(ROOT + os.sep)',
  '            os.unlink(res["zip"])',
  '    except Exception as exc:',
  '        item["threw"] = "%s: %s" % (type(exc).__name__, exc)',
  '    out.append(item)',
  '# rac con lai trong generated_ho_so do ten khong hop le -> don sach',
  'if os.path.isdir(ghs):',
  '    for n in os.listdir(ghs):',
  '        if n not in before:',
  '            p = os.path.join(ghs, n)',
  '            shutil.rmtree(p, ignore_errors=True)',
  '            if os.path.exists(p): os.unlink(p)',
  'print("leftover", sorted(set(os.listdir(ghs)) - before) if os.path.isdir(ghs) else [])',
  'print(json.dumps(out, ensure_ascii=False))'
].join('\n'), 'utf8');
fs.writeFileSync(spec3Path, JSON.stringify(spec3), 'utf8');
const RES3 = runPy3();
function runPy3() {
  const { execSync } = require('child_process');
  const INTERPS = ['python -X utf8', 'python3 -X utf8'];
  for (let i = 0; i < INTERPS.length; i++) {
    try {
      const out = execSync(INTERPS[i] + ' "' + pyPath3 + '" "' + spec3Path + '"', {
        cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      return JSON.parse(String(out).trim().split(/\r?\n/).pop());
    } catch (e) {
      const status = (e && e.status != null) ? e.status : 1;
      const noInterp = status === 127 || (e && e.code === 'ENOENT');
      if (!noInterp || i === INTERPS.length - 1) {
        return [{ name: '@driver',
          threw: 'python exit ' + status + ': ' +
            String((e && e.stderr) || (e && e.message) || '').slice(0, 300) }];
      }
    }
  }
  return [{ name: '@driver', threw: 'khong chay duoc python' }];
}

check('P3-S3b: probe export chay duoc cho ' + HOSTILE_NAMES.length + ' ten hostil',
  RES3.length === HOSTILE_NAMES.length && !RES3.some(r => r.name === '@driver'),
  JSON.stringify(RES3.filter(r => r.name === '@driver')));

RES3.forEach(r => {
  if (r.name === '@driver') return;
  const label = (HOSTILE_NAMES.find(h => h[0] === r.name) || [])[1] || r.name;
  const short = String(r.name).slice(0, 18).replace(/\n/g, '\\n');
  if (r.escaped) {
    finding('F-P3-SEC-PATH ten ho so "' + short + '" (' + label +
      ') ghi THOAT ra ngoai thu muc export',
      'dir=' + r.dir);
  } else if (r.threw) {
    finding('F-P3-SEC-PATH ten ho so "' + short + '" (' + label +
      ') lam Bridge.export NEM exception khong duoc bat', r.threw);
  } else {
    check('P3-S3c: ten "' + short + '" (' + label + ') nam trong thu muc export, khong nem',
      r.ok === true || (r.errors && r.errors.length) || r.ok === false,
      JSON.stringify({ ok: r.ok, errors: r.errors, dir: r.dir }));
  }
});
/* forms[].id có thoát không? (production tra cứu form_maps TRƯỚC khi ghép tên) */
const fidProbe = path.join(TMP, 'fid_probe.py');
fs.writeFileSync(fidProbe, [
  'import json, os, sys, types, shutil',
  'fake = types.ModuleType("webview")',
  'fake.create_window = lambda *a, **k: None',
  'fake.start = lambda *a, **k: None',
  'sys.modules["webview"] = fake',
  'sys.path.insert(0, os.getcwd())',
  'import importlib.util',
  'spec = importlib.util.spec_from_file_location("p3main", "app_web/main.py")',
  'mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)',
  'b = mod.Bridge()',
  'ROOT = os.path.abspath(".")',
  'res = b.export({"case_id": "p3sec_fid", "forms": [{"id": "../../P3_SEC_FID"}],',
  '                "data": {}})',
  'out = {"ok": res.get("ok"), "errors": res.get("errors"), "files": res.get("files"),',
  '       "dir": res.get("dir")}',
  'if res.get("dir"):',
  '    out["escaped"] = not os.path.abspath(res["dir"]).startswith(ROOT + os.sep)',
  '    shutil.rmtree(res["dir"], ignore_errors=True)',
  'if res.get("zip") and os.path.exists(res["zip"]): os.unlink(res["zip"])',
  'print(json.dumps(out, ensure_ascii=False))'
].join('\n'), 'utf8');
const RES_FID = runPyAt(fidProbe, path.join(TMP, 'spec_fid.json'),
  JSON.stringify({ names: [], forms: [{ id: '../../P3_SEC_FID' }] }));
function runPyAt(script, specFile, specBody) {
  const { execSync } = require('child_process');
  if (specFile) fs.writeFileSync(specFile, specBody, 'utf8');
  const INTERPS = ['python -X utf8', 'python3 -X utf8'];
  for (let i = 0; i < INTERPS.length; i++) {
    try {
      const out = execSync(INTERPS[i] + ' "' + script + '" "' + specFile + '"', {
        cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
        stdio: ['ignore', 'pipe', 'pipe']
      });
      return JSON.parse(String(out).trim().split(/\r?\n/).pop());
    } catch (e) {
      const status = (e && e.status != null) ? e.status : 1;
      const noInterp = status === 127 || (e && e.code === 'ENOENT');
      if (!noInterp || i === INTERPS.length - 1) {
        return { error: 'python exit ' + status + ': ' +
          String((e && e.stderr) || '').slice(0, 200) };
      }
    }
  }
  return { error: 'khong chay duoc python' };
}
checkSec('P3-S3d: forms[].id chua "../" KHONG ghi file thoat ra ngoai '
  + '(bi chan o buoc tra cuu form_maps.json)',
  !RES_FID.error && RES_FID.escaped !== true &&
    Array.isArray(RES_FID.errors) && RES_FID.errors.length >= 1,
  JSON.stringify(RES_FID),
  'F-P3-SEC-FID forms[].id ghi file thoat ra ngoai thu muc export');

// ======================================================================
// 4. Log: không in giá trị nhạy cảm ra console
// ======================================================================
section('4. Log: khong in MST/CCCD/ho ten ra console');
const SENSITIVE = ['so_cccd', 'ma_so_dn', 'ma_so_thue', 'hkd_ma_so', 'cmnd',
  'hc_ho_chieu', 'so_giay_to', 'ho_ten', 'dn.ten'];
const UI_FILES = fs.readdirSync(path.join(ROOT, 'app_web', 'ui'))
  .filter(f => f.endsWith('.js')).map(f => path.join(ROOT, 'app_web', 'ui', f));
const hits = [];
UI_FILES.forEach(f => {
  const src = fs.readFileSync(f, 'utf8');
  src.split('\n').forEach((line, i) => {
    if (/\bconsole\.(log|info|error)\s*\(/.test(line)) {
      hits.push(path.relative(ROOT, f) + ':' + (i + 1) + ': ' + line.trim());
      return;
    }
    if (/\bconsole\.(warn|debug)\s*\(/.test(line) &&
        SENSITIVE.some(k => line.indexOf(k) >= 0)) {
      hits.push(path.relative(ROOT, f) + ':' + (i + 1) + ': ' + line.trim());
    }
  });
});
check('P3-S4a: app_web/ui/*.js KHONG co console.log/info/error',
  hits.length === 0, JSON.stringify(hits));
const pyPrintHits = [];
fs.readFileSync(path.join(ROOT, 'app_web', 'main.py'), 'utf8').split('\n')
  .forEach((line, i) => {
    if (/\bprint\s*\(/.test(line) &&
        SENSITIVE.some(k => line.indexOf(k) >= 0)) {
      pyPrintHits.push('app_web/main.py:' + (i + 1) + ': ' + line.trim());
    }
  });
check('P3-S4b: app_web/main.py KHONG print gia tri nhay cam',
  pyPrintHits.length === 0, JSON.stringify(pyPrintHits));
/* Lỗi render trả về UI có mang giá trị người dùng không? (ExportTotalsError
 * nhúng `stored %r` — mức INFORMATIONAL: hiển thị trong panel lỗi, không log) */
checkSec('P3-S4c: thong bao loi export KHONG nhung gia tri nguoi dung (stored %r)',
  (() => {
    const dr = fs.readFileSync(path.join(ROOT, 'tools', 'docx_render.py'), 'utf8');
    const leaks = [];
    if (dr.indexOf('stored %r != computed %r') >= 0) {
      leaks.push('tools/docx_render.py: "stored %r != computed %r"');
    }
    const mp = fs.readFileSync(path.join(ROOT, 'app_web', 'main.py'), 'utf8');
    if (/"%s: lỗi render %r"/.test(mp) || mp.indexOf('lỗi render %r') >= 0) {
      leaks.push('app_web/main.py: errors.append("%s: lỗi render %r")');
    }
    return leaks.length === 0;
  })(),
  'tools/docx_render.py nhung "stored %r" va app_web/main.py noi %r exc vao '
    + 'errors[] tra ve UI (khong qua console) -> INFORMATIONAL',
  'F-P3-SEC-LOG thong bao loi export chua gia tri nguoi dung (stored/exception %r)');

// dọn temp dir (ngoài repo)
try { fs.rmSync(TMP, { recursive: true, force: true }); } catch (e) { /* ignore */ }

// ------------------------------------------------------------------ summary
console.log('-'.repeat(64));
if (FINDINGS.length) {
  console.log('KNOWN-FINDINGS (production, KHONG sua trong lane nay):');
  FINDINGS.forEach(f => console.log('  - ' + f));
}
console.log('test_p3_security: ' + passed + ' PASS / ' + failed + ' FAIL / ' +
  FINDINGS.length + ' KNOWN-FINDING');
process.exit(failed ? 1 : 0);
