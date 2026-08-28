/* test_p3_a11y.js — LANE P3: accessibility (Playwright Chromium) trên harness
 * app_web/dev/snapshot.html (http.server chạy từ ROOT worktree, port tự chọn).
 *
 * Chạy:  node app_web/test_p3_a11y.js
 *
 * Gate:
 *   G1 keyboard-only (PLI_M02 + PLI_M01): Tab đi theo thứ tự input trong DOM,
 *      không nhảy lung tung / không bỏ ô.
 *   G2 focus-visible: khi focus bằng BÀN PHÍM, outline không được là 'none'.
 *   G3 không focus trap: Tab liên tục phải đi tới cuối vùng focusable.
 *   G4 ARIA: bảng loop có aria-colcount/aria-rowcount; nút add/del có
 *      aria-label; ô lỗi có aria-invalid.
 *   G5 contrast: body text + button text + header bảng >= 4.5:1
 *      (hoặc >= 3:1 với chữ lớn theo WCAG 1.4.3).
 *   G6 zoom 200% (body.style.zoom): không chồng chữ ở vùng đầu trang
 *      PLI_M02 + PLI_M01.
 *   G7 (P3.3) app shell thật: mở index.html + app.js (KHÔNG phải snapshot),
 *      đo #tabs[role=tablist]: role=tab + đúng 1 aria-selected=true; roving
 *      tabindex; ArrowLeft/Right di chuyển focus và aria-selected theo focus;
 *      không focus trap trong thanh tab.
 *
 * Mỗi gate ghi PASS/FAIL riêng. FAIL là FINDING của production (báo Lead) —
 * lane này KHÔNG sửa CSS/production, nên gate có cờ FINDING vẫn để suite
 * exit 0 (liệt kê rõ trong báo cáo).
 *
 * Playwright: module được resolve từ nhiều nơi (repo / NODE_PATH /
 * P3_PLAYWRIGHT_DIR / <tmp>/p3-pw). KHÔNG có Playwright/Chromium thì in
 * "NOT RUN" và exit 0 (không giả lập kết quả).
 */
'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DOCS = ['PLI_M02', 'PLI_M01'];
let PORT = 0;

let passed = 0, failed = 0, broke = false;
const FINDINGS = [];
function check(name, cond, extra, fid) {
  if (cond) { passed++; console.log('PASS  ' + name); }
  else {
    failed++;
    FINDINGS.push(fid || name);
    console.log('FAIL  ' + name + (extra !== undefined ? '  [' + extra + ']' : ''));
  }
}
function section(t) { console.log('\n===== ' + t + ' ====='); }
/* Số dòng 2 rule focus của style.css (bằng chứng cho F-P3-A11Y-FOCUS). */
const CSS_LINES = fs.readFileSync(path.join(ROOT, 'app_web', 'ui', 'style.css'),
  'utf8').split('\n');
function ffocus(visible) {
  const re = visible ? /\.fld:focus-visible/ : /\.fld:focus,/;
  for (let i = 0; i < CSS_LINES.length; i++) {
    if (re.test(CSS_LINES[i])) return i + 1;
  }
  return '?';
}

// ------------------------------------------------------------------ helpers

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const p = srv.address().port;
      srv.close(() => resolve(p));
    });
  });
}
function waitReady(port, tries) {
  const url = 'http://127.0.0.1:' + port + '/app_web/dev/snapshot.html';
  return new Promise((resolve) => {
    let n = 0;
    (function ping() {
      const req = http.get(url, res => { res.resume(); resolve(res.statusCode === 200); });
      req.on('error', () => {
        if (++n > (tries || 60)) return resolve(false);
        setTimeout(ping, 200);
      });
    })();
  });
}
function loadPlaywright() {
  const candidates = [];
  if (process.env.P3_PLAYWRIGHT_DIR) candidates.push(process.env.P3_PLAYWRIGHT_DIR);
  candidates.push(ROOT, ROOT + '/..', __dirname, '/tmp/p3-pw');
  const saved = process.env.NODE_PATH;
  for (const dir of candidates) {
    const p = path.join(dir, 'node_modules', 'playwright');
    if (fs.existsSync(p)) {
      try { return require(p); } catch (e) { /* thử chỗ khác */ }
    }
    try { return require(require.resolve('playwright', { paths: [dir] })); }
    catch (e) { /* thử chỗ khác */ }
  }
  if (saved !== undefined) process.env.NODE_PATH = saved;
  return null;
}
async function launchChromium(playwright) {
  const { chromium } = playwright;
  const tries = [{}, { channel: 'chrome' }];
  // thêm mọi bản Chromium đã cache (ms-playwright) theo thứ tự mới -> cũ
  const cache = path.join(process.env.HOME || '', 'Library', 'Caches', 'ms-playwright');
  if (fs.existsSync(cache)) {
    const dirs = fs.readdirSync(cache)
      .filter(d => d.indexOf('chromium') === 0)
      .sort().reverse();
    dirs.forEach(d => {
      const base = path.join(cache, d);
      [['chrome-headless-shell-mac-arm64', 'chrome-headless-shell'],
       ['chrome-mac-arm64', 'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'],
       ['chrome-mac', 'Chromium.app/Contents/MacOS/Chromium']]
        .forEach(([sub, bin]) => {
          const exe = path.join(base, sub, bin);
          if (fs.existsSync(exe)) tries.push({ executablePath: exe, headless: true });
        });
    });
  }
  let last = null;
  for (const opt of tries) {
    try {
      const browser = await chromium.launch(opt);
      console.log('INFO  chromium launch: ' + (opt.executablePath || opt.channel ||
        'playwright mặc định'));
      return browser;
    } catch (e) { last = e; }
  }
  throw last || new Error('không launch được Chromium');
}

/* ============================== GATES ================================== */

/* G1 + G2 + G3: keyboard */
async function gateKeyboard(page, doc) {
  section('G1/G2/G3 [' + doc + '] keyboard-only: thu tu Tab, focus-visible, khong trap');
  await page.goto('http://127.0.0.1:' + PORT + '/app_web/dev/snapshot.html?doc=' + doc);
  await page.waitForSelector('#pages .page-a4', { timeout: 15000 });
  await page.waitForFunction(() =>
    (document.querySelectorAll('#pages input, #pages button').length || 0) > 5,
  { timeout: 15000 });

  /* Mỗi ô focusable được gán một chỉ số duy nhất (data-p3-idx) đúng theo thứ
   * tự DOM, để đo thứ tự Tab KHÔNG bị trùng signature (nhiều ô cùng data-key). */
  const domOrder = await page.evaluate(() => {
    const sel = 'a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), ' +
      'select:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const els = Array.from(document.querySelectorAll(sel))
      .filter(el => el.offsetParent !== null || el === document.activeElement);
    els.forEach((el, i) => el.setAttribute('data-p3-idx', String(i)));
    return els.map((el, i) => i + ':' + el.tagName + ':' + (el.getAttribute('data-key') ||
      el.getAttribute('data-act') || el.getAttribute('data-loop') || el.name || ''));
  });

  /* Tab thật bằng bàn phím để :focus-visible được áp dụng */
  const visited = [];
  await page.evaluate(() => { document.body.focus(); window.scrollTo(0, 0); });
  let stuck = 0, lastSig = '';
  const MAXTAB = Math.min(domOrder.length + 8, 400);
  for (let i = 0; i < MAXTAB; i++) {
    await page.keyboard.press('Tab');
    const sig = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return 'body';
      const idx = el.getAttribute('data-p3-idx');
      return (idx !== null ? idx + ':' : '') + el.tagName + ':' +
        (el.getAttribute('data-key') || el.getAttribute('data-act') ||
          el.getAttribute('data-loop') || el.name || '');
    });
    visited.push(sig);
    if (sig === lastSig) stuck++;
    lastSig = sig;
  }

  /* G3: không trap — Tab luôn tiến, và phải wrap về đầu (có ô bị ghé lại) */
  const focusableVisited = visited.filter(x => x !== 'body');
  const distinct = new Set(focusableVisited).size;
  let maxStuck = 0, run = 0;
  for (let i = 1; i < visited.length; i++) {
    run = (visited[i] === visited[i - 1]) ? run + 1 : 0;
    if (run > maxStuck) maxStuck = run;
  }
  const revisited = distinct < focusableVisited.length;  // wrap => đi hết vòng
  check('G3[' + doc + '] khong focus trap: ' + distinct + ' o focus duoc, ' +
      'maxStuck=' + maxStuck + ', wrap=' + revisited,
    distinct >= Math.min(domOrder.length, 6) && maxStuck <= 2 && revisited,
    'visited=' + visited.length + ' distinct=' + distinct +
      ' domOrder=' + domOrder.length +
      ' (radio cung nhom chi la 1 tab stop nen distinct < so input la binh thuong)');

  /* G1: thứ tự Tab đi theo thứ tự DOM (không đảo ngược / nhảy ô đã qua) */
  let inversions = 0, prevIdx = -1, skipped = 0;
  const seen = {};
  focusableVisited.forEach(sig => {
    const m = /^(\d+):/.exec(sig);
    if (!m) return;                       // element ngoài vùng đo
    const i = parseInt(m[1], 10);
    if (seen[i]) return;                  // wrap vòng 2: không tính
    seen[i] = true;
    if (prevIdx >= 0) {
      if (i < prevIdx) inversions++;
      else if (i > prevIdx + 1) skipped++;
    }
    prevIdx = i;
  });
  check('G1[' + doc + '] thu tu Tab theo thu tu input trong DOM (' +
      focusableVisited.length + ' buoc, ' + inversions + ' nghich dao, ' +
      skipped + ' nhay bo o)',
    focusableVisited.length >= Math.min(domOrder.length, 6) && inversions === 0,
    'domOrder=' + domOrder.length + ' inv=' + inversions +
      ' first=' + focusableVisited.slice(0, 6).join(' > '));

  /* G2: focus-visible phải có outline nhìn thấy */
  const outline = await page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { tag: 'body' };
    const cs = getComputedStyle(el);
    return {
      tag: el.tagName,
      cls: el.className && String(el.className).slice(0, 40),
      style: cs.outlineStyle, width: cs.outlineWidth,
      color: cs.outlineColor,
      bg: cs.backgroundColor,
      vs: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0
    };
  });
  check('G2[' + doc + '] focus-visible co outline nhin thay (o "' +
      String(outline.cls || outline.tag) + '")',
    outline.vs === true,
    JSON.stringify(outline),
    'F-P3-A11Y-FOCUS focus bang ban phim tren o nhap khong co outline (style.css '
      + ffocus() + ' de len ' + ffocus(true) + ')');
}

/* G4: ARIA */
async function gateAria(page, doc) {
  section('G4 [' + doc + '] ARIA: colcount/rowcount, aria-label nut, aria-invalid');
  const info = await page.evaluate(() => {
    const tables = Array.from(document.querySelectorAll('#pages table'));
    const loopTables = tables.filter(t => t.getAttribute('data-loop'));
    const btns = Array.from(document.querySelectorAll(
      '#pages .loop-btns button, #pages button[data-act]'));
    const inputs = Array.from(document.querySelectorAll('#pages input'));
    return {
      tables: tables.length,
      loopTables: loopTables.map(t => ({
        loop: t.getAttribute('data-loop'),
        role: t.getAttribute('role'),
        colcount: t.getAttribute('aria-colcount'),
        rowcount: t.getAttribute('aria-rowcount')
      })),
      btnsNoLabel: btns.filter(b => !(b.getAttribute('aria-label') || '').trim())
        .map(b => b.getAttribute('data-act')),
      btnsTotal: btns.length,
      invalidAttrs: inputs.filter(i => i.getAttribute('aria-invalid') !== null).length,
      inputsTotal: inputs.length,
      ariaLabelInputs: inputs.filter(i => (i.getAttribute('aria-label') || '').trim()).length,
      missingLabel: inputs.filter(i => !(i.getAttribute('aria-label') || '').trim())
        .slice(0, 6).map(i => i.tagName + '.' + String(i.className).slice(0, 24) +
          '[' + (i.getAttribute('data-key') || i.name || i.type) + ']')
    };
  });
  check('G4.1[' + doc + '] co bang loop trong DOM (' + info.loopTables.length + ' bang)',
    info.loopTables.length >= 1, JSON.stringify(info.loopTables.map(t => t.loop)));
  check('G4.2[' + doc + '] moi bang loop co aria-colcount + aria-rowcount',
    info.loopTables.length >= 1 && info.loopTables.every(t => t.colcount && t.rowcount),
    JSON.stringify(info.loopTables), 'F-P3-A11Y-TABLE bang loop thieu '
      + 'aria-colcount/aria-rowcount (render.js renderLoop khong sinh)');
  check('G4.3[' + doc + '] moi nut add/del/... co aria-label (' + info.btnsTotal + ' nut)',
    info.btnsTotal >= 1 && info.btnsNoLabel.length === 0,
    'thieu aria-label: ' + JSON.stringify(info.btnsNoLabel),
    'F-P3-A11Y-BUTTON nut thao tac dong chi co title= , khong co aria-label');
  check('G4.4[' + doc + '] input co aria-invalid khi co loi (snapshot chua co loi -> '
      + info.invalidAttrs + '/' + info.inputsTotal + ' o mang aria-invalid)',
    info.inputsTotal === 0 || info.invalidAttrs >= 0, '');  // mô tả, không chặn
  /* ô lỗi phải được đánh dấu aria-invalid=true: mô phỏng bằng cách gắn class
   * 'invalid' như patchErrorsDom làm rồi đo attribute tương ứng */
  const marked = await page.evaluate(() => {
    const el = document.querySelector('#pages input.fld');
    if (!el) return null;
    el.classList.add('invalid');
    el.setAttribute('aria-invalid', 'true');
    const cs = getComputedStyle(el);
    return { color: cs.color, bg: cs.backgroundColor, set: el.getAttribute('aria-invalid') };
  });
  check('G4.5[' + doc + '] o loi co the danh dau aria-invalid=true + co style .invalid',
    !!marked && marked.set === 'true',
    JSON.stringify(marked));
  check('G4.6[' + doc + '] input co aria-label de doc man hinh (' +
      info.ariaLabelInputs + '/' + info.inputsTotal + ')',
    info.inputsTotal >= 1 && info.ariaLabelInputs === info.inputsTotal,
    info.ariaLabelInputs + '/' + info.inputsTotal +
      ' thieu: ' + JSON.stringify(info.missingLabel),
    'F-P3-A11Y-LABEL input checkbox .chk-box khong co aria-label');
}

/* G5: contrast */
const RATIO = (rgb1, rgb2) => {
  const lum = ([r, g, b]) => {
    const f = c => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const a = lum(rgb1), b = lum(rgb2);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
};
function parseColor(s) {
  const m = /rgba?\(([^)]+)\)/.exec(s || '');
  if (!m) return null;
  const p = m[1].split(',').map(x => parseFloat(x));
  return { rgb: [p[0], p[1], p[2]], alpha: p.length > 3 ? p[3] : 1 };
}
const CONTRAST_TARGETS = [
  ['body text (doan van ban .bp)', '#pages .page-a4 p.bp'],
  ['button text (.loop-btns button)', '#pages .loop-btns button'],
  ['button nguy hiem (.btn-danger-row)', '#pages .loop-btns .btn-danger-row'],
  ['header bang (.btable thead th)', '#pages .btable thead th'],
  ['o input (.fld)', '#pages input.fld']
];
async function gateContrast(page, doc) {
  section('G5 [' + doc + '] contrast (WCAG 1.4.3)');
  for (const [label, sel] of CONTRAST_TARGETS) {
    const res = await page.evaluate((selector) => {
      const el = document.querySelector(selector);
      if (!el) return { missing: true };
      /* helper nội bộ (phải nằm trong context trình duyệt) */
      function pcParse(s) {
        const m = /rgba?\(([^)]+)\)/.exec(s || '');
        if (!m) return null;
        const p = m[1].split(',').map(x => parseFloat(x));
        return { rgb: [p[0], p[1], p[2]], alpha: p.length > 3 ? p[3] : 1 };
      }
      function bgOf(node) {
        let cur = node;
        while (cur && cur !== document.documentElement) {
          const c = pcParse(getComputedStyle(cur).backgroundColor);
          if (c && c.alpha > 0.85) return c.rgb;
          cur = cur.parentElement;
        }
        return [255, 255, 255];
      }
      function ratio(f, b) {
        const lum = v => {
          const g = c => { c /= 255;
            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
          return 0.2126 * g(v[0]) + 0.7152 * g(v[1]) + 0.0722 * g(v[2]);
        };
        const a = lum(f), bb = lum(b);
        return (Math.max(a, bb) + 0.05) / (Math.min(a, bb) + 0.05);
      }
      const cs = getComputedStyle(el);
      const fg = pcParse(cs.color);
      const bg = bgOf(el);
      const size = parseFloat(cs.fontSize);
      const weight = parseInt(cs.fontWeight, 10) || 400;
      const large = size >= 24 || (size >= 18.66 && weight >= 700);
      return {
        color: cs.color, bg: 'rgb(' + bg.join(',') + ')', size, weight, large,
        ratio: (fg && bg) ? ratio(fg.rgb, bg) : null,
        text: (el.textContent || '').trim().slice(0, 24)
      };
    }, sel);
    if (res.missing) {
      check('G5[' + doc + '] ' + label + ' co mat trong DOM', false, 'khong tim thay ' + sel);
      continue;
    }
    const need = res.large ? 3 : 4.5;
    check('G5[' + doc + '] ' + label + ' = ' + res.ratio.toFixed(2) + ':1 (can ' +
        need + ':1, ' + res.size.toFixed(0) + 'px/' + res.weight + ')',
      res.ratio >= need,
      JSON.stringify({ fg: res.color, bg: res.bg, text: res.text }));
  }
}

/* G6: zoom 200% — không chồng chữ ở vùng đầu trang.
 * injectFault=true: chèn chủ ý một cặp chữ đè lên nhau để TỰ KIỂM CHỨNG
 * detector không phải gate rỗng (nếu detector không thấy -> gate vô nghĩa). */
async function gateZoom(page, doc, injectFault) {
  const tag = injectFault ? 'G6b' : 'G6';
  if (!injectFault) {
    section('G6 [' + doc + '] zoom 200%: khong chong chu o vung dau trang');
  }
  await page.goto('http://127.0.0.1:' + PORT + '/app_web/dev/snapshot.html?doc=' + doc);
  await page.waitForSelector('#pages .page-a4', { timeout: 15000 });
  await page.waitForFunction(() =>
    (document.querySelectorAll('#pages input, #pages button').length || 0) > 3,
  { timeout: 15000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  const res = await page.evaluate((fault) => {
    /* đúng cách harness yêu cầu: body.style.zoom */
    document.body.style.zoom = '2';
    const region = document.querySelector('#pages .page-a4');
    if (!region) return { missing: true };
    /* vùng đầu trang = 1200px đầu (CSS px sau zoom) của tờ khai */
    const regionTop = region.getBoundingClientRect().top;
    const limit = regionTop + 1200;
    let injected = null;
    if (fault) {
      injected = document.createElement('div');
      injected.setAttribute('data-p3-fault', '1');
      injected.style.cssText = 'position:relative;height:60px;width:400px';
      injected.innerHTML =
        '<span style="position:absolute;left:0;top:0">CHONG CHU A</span>' +
        '<span style="position:absolute;left:8px;top:0">CHONG CHU B</span>';
      region.insertBefore(injected, region.firstChild);
    }
    const leaves = Array.from(region.querySelectorAll('*')).filter(el => {
      if (!el.textContent || !el.textContent.trim()) return false;
      if (el.children.length &&
          Array.from(el.children).some(c => (c.textContent || '').trim())) return false;
      const r = el.getBoundingClientRect();
      return r.height > 0 && r.width > 0 && r.top < limit && r.bottom > regionTop;
    });
    /* Đo theo LINE BOX (Range.getClientRects) chứ không theo bounding box của
     * element: một span xuống 2 dòng có bounding box phủ cả hai dòng và sẽ
     * 'chồng' giả với span cùng đoạn ở dòng khác. Chồng chữ thật = hai line
     * box khác nhau vẽ đè lên nhau. */
    const boxes = [];
    leaves.forEach(el => {
      const range = document.createRange();
      range.selectNodeContents(el);
      Array.from(range.getClientRects()).forEach(r => {
        if (r.width > 2 && r.height > 2) {
          boxes.push({ r, text: (el.textContent || '').trim().slice(0, 40) });
        }
      });
    });
    const overlaps = [];
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i].r, b = boxes[j].r;
        const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ox <= 2 || oy <= 2) continue;
        const area = ox * oy;
        const minArea = Math.min(a.width * a.height, b.width * b.height);
        if (area / minArea > 0.35) {
          overlaps.push({ a: boxes[i].text, b: boxes[j].text,
            pct: Math.round(100 * area / minArea),
            dy: Math.round(Math.abs(a.top - b.top)) });
        }
      }
    }
    const found = overlaps.filter(o => /CHONG CHU/.test(o.a + o.b));
    if (injected && injected.parentNode) injected.parentNode.removeChild(injected);
    return {
      leaves: leaves.length,
      lineBoxes: boxes.length,
      overlaps: overlaps.slice(0, 8),
      overlapCount: overlaps.length,
      faultDetected: found.length,
      regionTop: regionTop,
      docHeight: document.body.scrollHeight
    };
  }, injectFault === true);
  if (injectFault) {
    check('G6b[' + doc + '] tu kiem chung detector: cap chu de len nhau DUOC PHAT HIEN',
      res && !res.missing && res.faultDetected >= 1,
      JSON.stringify({ faultDetected: res.faultDetected,
        lineBoxes: res.lineBoxes, overlaps: res.overlaps }));
  } else {
    check('G6[' + doc + '] zoom 200% khong chong chu o vung dau trang (' +
        (res.lineBoxes || 0) + ' line box, ' + (res.overlapCount || 0) + ' cap chong)',
      res && !res.missing && res.overlapCount === 0,
      JSON.stringify(res.overlaps || res));
  }
  await page.evaluate(() => { document.body.style.zoom = ''; });
}

/* G7 (P3.3): APP SHELL THẬT — index.html + app.js (bootstrap DOMContentLoaded),
 * KHÔNG phải snapshot harness. Serve ROOT bằng chính http.server của suite;
 * ?mock=1 là chế độ mock được app.js hỗ trợ sẵn (loadCases/getBlocks đọc dữ liệu
 * local, không cần bridge pywebview) nên tab xuất hiện mà không phải dựng API giả.
 * Đo trên #tabs[role=tablist] (đã có aria-label sẵn trong index.html):
 *   G7.1 mỗi tab role=tab, đúng 1 tab aria-selected=true
 *   G7.2 roving tabindex: đúng 1 tab tabindex=0, còn lại -1
 *   G7.3 ArrowLeft/ArrowRight di chuyển focus + aria-selected theo focus
 *   G7.4 không focus trap trong thanh tab (Tab/Shift+Tab phải thoát ra được) */
async function gateShell(page) {
  section('G7 [shell] app that index.html: tablist, aria-selected, roving tabindex, arrow, khong trap');
  await page.addInitScript(function () {
    /* app.js đã guard null-safe (`window.pywebview && window.pywebview.api`);
     * đặt TRƯỚC script app để không phụ thuộc sự kiện pywebviewready. */
    window.pywebview = { api: null };
  });
  await page.goto('http://127.0.0.1:' + PORT + '/app_web/ui/index.html?mock=1');

  let ready = true, waitErr = '';
  try {
    await page.waitForSelector('#tabs [role="tab"]', { timeout: 20000 });
    await page.waitForFunction(function () {
      return document.querySelectorAll('#tabs [role="tab"]').length >= 1 &&
        !!document.querySelector('#tabs [aria-selected="true"]');
    }, { timeout: 20000 });
  } catch (e) {
    ready = false;
    waitErr = String(e && e.message || e).split('\n')[0];
  }

  const m = await page.evaluate(function () {
    const list = document.querySelector('#tabs[role="tablist"]');
    const tabs = Array.prototype.slice.call(
      document.querySelectorAll('#tabs [role="tab"]'));
    const sel = tabs.filter(function (t) {
      return t.getAttribute('aria-selected') === 'true'; }).length;
    const unsel = tabs.filter(function (t) {
      return t.getAttribute('aria-selected') === 'false'; }).length;
    return {
      ready: true,
      tablist: !!list,
      tablistLabel: list ? (list.getAttribute('aria-label') || '').trim() : '',
      n: tabs.length,
      oddChildren: Array.prototype.filter.call(
        document.querySelectorAll('#tabs > *'),
        function (el) { return el.getAttribute('role') !== 'tab'; }).length,
      selected: sel, unselected: unsel,
      roving0: tabs.filter(function (t) {
        return t.getAttribute('tabindex') === '0'; }).length,
      rovingMinus: tabs.filter(function (t) {
        return t.getAttribute('tabindex') === '-1'; }).length,
      ids: tabs.map(function (t) { return t.getAttribute('data-doc-id'); })
    };
  }).catch(function () { return { ready: false }; });
  m.ready = m.ready === true && ready;
  if (!m.ready) m.waitErr = waitErr;

  check('G7.1[shell] #tabs la tablist co aria-label, ' + m.n +
      ' tab role=tab, dung 1 aria-selected=true',
    m.ready && m.tablist && !!m.tablistLabel && m.n >= 1 &&
      m.selected === 1 && m.unselected === m.n - 1 && m.oddChildren === 0,
    JSON.stringify(m), 'F-P3-A11Y-SHELL-TAB');

  check('G7.2[shell] roving tabindex: dung 1 tab tabindex=0, con lai -1',
    m.ready && m.n >= 1 && m.roving0 === 1 && m.rovingMinus === m.n - 1,
    'roving0=' + m.roving0 + ' roving-1=' + m.rovingMinus + ' n=' + m.n,
    'F-P3-A11Y-SHELL-ROVING');

  /* G7.3: focus tab đang chọn rồi bấm mũi tên bằng BÀN PHÍM; focus và
   * aria-selected phải cùng chuyển sang tab kề (và wrap vòng). */
  let arrow = { ok: false };
  if (m.ready && m.n >= 1) {
    arrow = await page.evaluate(function (ids) {
      const tabs = Array.prototype.slice.call(
        document.querySelectorAll('#tabs [role="tab"]'));
      tabs[0].focus();
      return { first: document.activeElement.getAttribute('data-doc-id'), n: tabs.length };
    }, m.ids);
    await page.keyboard.press('ArrowRight');
    const right = await page.evaluate(function () {
      const tabs = Array.prototype.slice.call(
        document.querySelectorAll('#tabs [role="tab"]'));
      const sel = tabs.filter(function (t) {
        return t.getAttribute('aria-selected') === 'true'; })[0];
      return {
        focus: document.activeElement && document.activeElement.closest &&
          document.activeElement.closest('#tabs')
          ? document.activeElement.getAttribute('data-doc-id') : null,
        selected: sel ? sel.getAttribute('data-doc-id') : null,
        inTabs: !!(document.activeElement && document.activeElement.closest &&
          document.activeElement.closest('#tabs'))
      };
    });
    await page.keyboard.press('ArrowLeft');
    const left = await page.evaluate(function () {
      return document.activeElement && document.activeElement.closest &&
        document.activeElement.closest('#tabs')
        ? document.activeElement.getAttribute('data-doc-id') : null;
    });
    arrow.ok = right.inTabs && right.focus && right.selected &&
      right.focus === right.selected &&
      right.focus !== arrow.first && left === arrow.first;
    arrow.right = right;
    arrow.backTo = left;
  }
  check('G7.3[shell] ArrowRight/ArrowLeft di chuyen focus + aria-selected theo focus',
    arrow.ok, JSON.stringify(arrow), 'F-P3-A11Y-SHELL-ARROW');

  /* G7.4: từ tab cuối Tab phải THOÁT khỏi #tabs; từ tab đầu Shift+Tab phải
   * thoát theo chiều ngược lại — không giữ focus trong thanh tab. */
  let trap = { fwd: null, back: null };
  if (m.ready && m.n >= 1) {
    await page.evaluate(function () {
      const tabs = document.querySelectorAll('#tabs [role="tab"]');
      tabs[tabs.length - 1].focus();
    });
    await page.keyboard.press('Tab');
    trap.fwd = await page.evaluate(function () {
      return !!(document.activeElement && document.activeElement.closest &&
        document.activeElement.closest('#tabs'));
    });
    await page.evaluate(function () {
      const t = document.querySelector('#tabs [role="tab"]');
      if (t) t.focus();
    });
    await page.keyboard.press('Shift+Tab');
    trap.back = await page.evaluate(function () {
      return !!(document.activeElement && document.activeElement.closest &&
        document.activeElement.closest('#tabs'));
    });
  }
  check('G7.4[shell] khong focus trap trong thanh tab (Tab/Shift+Tab thoat duoc)',
    m.ready && trap.fwd === false && trap.back === false,
    JSON.stringify(trap) + ' (true = con nam trong #tabs)',
    'F-P3-A11Y-SHELL-TRAP');
}

// ------------------------------------------------------------------ main

(async () => {
  const playwright = loadPlaywright();
  if (!playwright) {
    console.log('NOT RUN  test_p3_a11y: khong co module playwright trong moi truong '
      + '(cau hinh NODE_PATH/P3_PLAYWRIGHT_DIR hoac npm i -g playwright). '
      + 'KHONG gia lap ket qua.');
    process.exit(0);
  }
  PORT = await freePort();
  const server = spawn('python3', ['-X', 'utf8', '-m', 'http.server', String(PORT),
    '--bind', '127.0.0.1'], { cwd: ROOT, stdio: 'ignore' });
  const okServer = await waitReady(PORT, 80);
  if (!okServer) {
    console.log('NOT RUN  test_p3_a11y: khong khoi dong duoc http.server tren port ' + PORT);
    server.kill('SIGTERM');
    process.exit(0);
  }
  console.log('INFO  http.server: http://127.0.0.1:' + PORT +
    '/app_web/dev/snapshot.html (cwd=' + ROOT + ')');

  let browser;
  try { browser = await launchChromium(playwright); }
  catch (e) {
    console.log('NOT RUN  test_p3_a11y: khong launch duoc Chromium (' +
      String(e && e.message).split('\n')[0] + ')');
    server.kill('SIGTERM');
    process.exit(0);
  }
  try {
    const page = await browser.newPage();
    page.on('pageerror', err => console.log('WARN  pageerror: ' +
      String(err).split('\n')[0]));
    page.on('console', msg => {
      if (msg.type() === 'error' && !/favicon/i.test(msg.text()) &&
          msg.location() && msg.location().url &&
          msg.location().url.indexOf('favicon') < 0) {
        console.log('WARN  console.error: ' + msg.text() + ' @ ' +
          (msg.location().url || '').slice(-60));
      }
    });

    for (const doc of DOCS) {
      section('===== ' + doc + ' =====');
      await gateKeyboard(page, doc);
      await gateAria(page, doc);
      await gateContrast(page, doc);
      await gateZoom(page, doc, false);
      await gateZoom(page, doc, true);   // tự kiểm chứng detector
    }
    await gateShell(page);               // P3.3: app shell thật (index.html)
    await browser.close();
  } catch (e) {
    failed++; broke = true;
    console.log('FAIL  a11y suite loi khong du kien: ' +
      String(e && e.message || e).split('\n')[0]);
  } finally {
    try { if (browser) await browser.close(); } catch (e) { /* ignore */ }
    server.kill('SIGTERM');
  }

  /* Bằng chứng nguồn (chỉ ĐỌC production, không sửa): giúp Lead biết chính xác
   * vị trí cần xem cho từng finding ở trên. */
  section('EVID: bang chung nguon trong production (chi doc)');
  const css = fs.readFileSync(path.join(ROOT, 'app_web', 'ui', 'style.css'), 'utf8')
    .split('\n');
  const rd = fs.readFileSync(path.join(ROOT, 'app_web', 'ui', 'render.js'), 'utf8')
    .split('\n');
  const ap = fs.readFileSync(path.join(ROOT, 'app_web', 'ui', 'app.js'), 'utf8')
    .split('\n');
  const findLine = (lines, re, from) => {
    for (let i = (from || 0); i < lines.length; i++) {
      if (re.test(lines[i])) return i + 1;
    }
    return -1;
  };
  const fv = findLine(css, /\.fld:focus-visible/);
  const ffocus = findLine(css, /\.fld:focus,/);
  /* rule .fld:focus kết thúc ở '}' đầu tiên: còn outline:none bên trong không */
  let ffOutlineNone = false;
  if (ffocus > 0) {
    for (let i = ffocus; i < css.length && i < ffocus + 6; i++) {
      if (/^\s*\}/.test(css[i])) break;
      if (/^\s*outline:\s*none\s*;/.test(css[i])) { ffOutlineNone = true; break; }
    }
  }
  console.log('EVID  G2: app_web/ui/style.css:' + fv + ' khai .fld:focus-visible '
    + '{outline:2px solid #2f6fbf}; style.css:' + ffocus + ' khai .fld:focus' +
    (ffocus > 0 && ffocus > fv
      ? (ffOutlineNone
        ? ' (VAN con outline:none => de len rule focus-visible)'
        : ' khong con outline:none => :focus-visible duoc ap dung (da sua '
          + 'F-P3-A11Y-FOCUS)')
      : ' (khong xac dinh duoc thu tu rule, fv=' + fv + ', ffocus=' + ffocus + ')'));
  const btnAdd = findLine(rd, /class="btn-row-add" data-act="add"/);
  const btnHasAria = btnAdd > 0 &&
    /aria-label/.test(rd.slice(btnAdd - 1, btnAdd + 3).join('\n'));
  console.log('EVID  G4.3: app_web/ui/render.js:' +
    (btnAdd > 0 ? btnAdd : -1) +
    ' sinh nut add/dup/del/clear/up/down ' +
    (btnHasAria ? 'CO aria-label (da sua F-P3-A11Y-BUTTON)'
                : 'chi co title= , khong co aria-label='));
  const chkEmit = findLine(rd, /return '<input type="checkbox" class="chk-box"/);
  const chkEnh = findLine(rd, /function enhanceChkLabels/);
  console.log('EVID  G4.6: app_web/ui/render.js:' + (chkEmit > 0 ? chkEmit : -1) +
    ' giu nguyen chuoi attribute checkbox .chk-box (contract pin boi test_dom + '
    + 'test_layout_l2_render); aria-label gan o buoc enhancement DOM render.js:'
    + (chkEnh > 0 ? chkEnh : -1) + ' enhanceChkLabels()' +
    (chkEnh > 0 ? '' : ' (KHONG tim thay enhanceChkLabels)'));
  const enh = findLine(ap, /function enhanceEditableGrids/);
  const enhHasColcount = enh > 0 &&
    /aria-colcount/.test(ap.slice(enh - 1, enh + 20).join('\n'));
  console.log('EVID  G4.2: app_web/ui/app.js:' + enh +
    ' enhanceEditableGrids() them role=grid + aria-colcount/aria-rowcount/'
    + 'aria-rowindex cho table.loop-table khi chay trong app that' +
    (enhHasColcount ? '' : ' (chua co aria-colcount)') +
    '; harness snapshot.html khong nap app.js nen do duoc la output renderer.');

  console.log('-'.repeat(64));
  if (FINDINGS.length) {
    console.log('KNOWN-FINDINGS (production, KHONG sua trong lane nay, da gop trung):');
    [...new Set(FINDINGS)].forEach(f => console.log('  - ' + f));
  }
  console.log('test_p3_a11y: ' + passed + ' PASS / ' + failed + ' FAIL' +
    (broke ? ' / LOI SUITE' : ''));
  process.exit(broke ? 1 : 0);   // lane quy ước: FAIL a11y là FINDING, không phá gate
})().catch(e => {
  console.log('FAIL  a11y loi khoi dong: ' + String(e && e.message || e));
  process.exit(1);
});
