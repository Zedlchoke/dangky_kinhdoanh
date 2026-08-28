/* test_loop_prod.js - kiểm thử renderLoop theo contract ZERO-BASED trên dữ
 * liệu PRODUCTION (app/data/blocks), không qua mock.
 *
 * Chạy:  node app_web/test_loop_prod.js
 *
 * Load TRỰC TIẾP 8 bảng lặp production:
 *   PLI_M06 ds_thanh_vien_tnhh (rename P2), PLI_M07 ds_co_dong_sang_lap, PLI_M08 ds_co_dong_nn,
 *   PLI_M09 ds_thanh_vien_hop_danh, PLI_M10 ds_cshhl, PLI_M11 ds_cshhl,
 *   PLII_M01 ds_nganh, PLII_M01 ds_tv_ho_gia_dinh
 * và assert cho từng loop:
 *   - tổng cột grid header == số td mỗi hàng body;
 *   - mỗi tag nằm đúng dưới tiêu đề tương ứng (col zero-based);
 *   - colspan/rowspan giữ ở th;
 *   - STT 1..n khi col0 trống + header chứa "stt";
 *   - cột không map render td rỗng đúng vị trí;
 *   - money/percent thêm class num (kèm type tổng hợp);
 *   - radio name="loop:<loop>:<tag>";
 *   - outputOnly render ô rỗng.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('./ui/render.js');

const DATA_DIR = path.join(__dirname, '..', 'app', 'data', 'blocks');
function loadProd(id) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, id + '.json'), 'utf8'));
}

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

/* ---------------- bộ giải lập độc lập (đọc thẳng JSON production) --------- */

/* Header grid walker viết RIÊNG trong test để đối chiếu chéo với renderer:
 * occupancy qua colspan/rowspan giữa các hàng header -> N + tiêu đề theo cột. */
function headerGridOf(b) {
  const idx = b.headerRows || [];
  const occ = {};
  const title = {};
  let n = 0;
  (b.rows || []).forEach((row, ri) => {
    if (idx.indexOf(ri) < 0) return;
    let col = 0;
    (row.cells || []).forEach(c => {
      while (occ[ri + ':' + col]) col++;
      const cs = Math.max(1, (c.colspan | 0) || 1);
      const rs = Math.max(1, (c.rowspan | 0) || 1);
      const txt = (c.runs || [])
        .map(r => (r && r.text != null ? String(r.text) : ''))
        .join(' ').replace(/\s+/g, ' ').trim();
      for (let dr = 0; dr < rs; dr++) {
        for (let dc = 0; dc < cs; dc++) {
          occ[(ri + dr) + ':' + (col + dc)] = true;
          if (!title[col + dc] && txt) title[col + dc] = txt;
        }
      }
      col += cs;
    });
    let w = 0;
    while (occ[ri + ':' + w]) w++;
    if (w > n) n = w;
  });
  return { n, title };
}

function findLoopBlock(doc, loopName) {
  return (doc.blocks || []).filter(b => b.t === 'loop' && b.loop === loopName)[0] || null;
}

function renderLoopOnly(b, store) {
  return R.renderBlocks({ id: 'T', blocks: [b] }, store || R.newStore());
}

function extractLoopTable(html, loopName) {
  const re = new RegExp(
    '<table[^>]*data-loop="' + loopName.replace(/[:.]/g, '\\$&') + '"[^>]*>[\\s\\S]*?</table>');
  const m = html.match(re);
  return m ? m[0] : '';
}

function extractSection(tableHtml, tag) {
  const m = tableHtml.match(new RegExp('<' + tag + '>[\\s\\S]*?</' + tag + '>'));
  return m ? m[0] : '';
}

function extractCells(sectionHtml, cellTag) {
  const out = [];
  const re = new RegExp('<' + cellTag + '([^>]*)>([\\s\\S]*?)</' + cellTag + '>', 'g');
  let m;
  while ((m = re.exec(sectionHtml)) !== null) {
    out.push({ attrs: m[1], inner: m[2] });
  }
  return out;
}

function extractHeaderRows(tableHtml) {
  const thead = extractSection(tableHtml, 'thead');
  const rows = [];
  const re = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  let m;
  while ((m = re.exec(thead)) !== null) rows.push(extractCells(m[1], 'th'));
  return rows;
}

function extractBodyRows(tableHtml) {
  const tbody = extractSection(tableHtml, 'tbody');
  const rows = [];
  const re = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  let m;
  while ((m = re.exec(tbody)) !== null) rows.push(extractCells(m[1], 'td'));
  return rows;
}

function unescapeHtml(s) {
  return String(s)
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}
function cellText(cell) {
  return unescapeHtml(cell.inner.replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
}
function attrNum(attrs, name) {
  const m = attrs.match(new RegExp(name + '="(\\d+)"'));
  return m ? +m[1] : 1;
}

/* Mở rộng hàng header thành slot theo colspan -> [{title, colspan, rowspan}] */
function expandHeaderRow(thCells) {
  const slots = [];
  thCells.forEach(c => {
    const cs = attrNum(c.attrs, 'colspan');
    const rs = attrNum(c.attrs, 'rowspan');
    for (let k = 0; k < cs; k++) slots.push({ title: cellText(c), colspan: cs, rowspan: rs });
  });
  return slots;
}

/* ------------------------- A. 8 bảng lặp PRODUCTION ------------------------ */

const PROD_LOOPS = [
  { doc: 'PLI_M06', loop: 'ds_thanh_vien_tnhh' }, /* rename P2 */
  { doc: 'PLI_M07', loop: 'ds_co_dong_sang_lap' },
  { doc: 'PLI_M08', loop: 'ds_co_dong_nn' },
  { doc: 'PLI_M09', loop: 'ds_thanh_vien_hop_danh' },
  { doc: 'PLI_M10', loop: 'ds_cshhl' },
  { doc: 'PLI_M11', loop: 'ds_cshhl' },
  { doc: 'PLII_M01', loop: 'ds_nganh' },
  { doc: 'PLII_M01', loop: 'ds_tv_ho_gia_dinh' }
];

PROD_LOOPS.forEach(function (spec) {
  const doc = loadProd(spec.doc);
  const b = findLoopBlock(doc, spec.loop);
  const label = spec.doc + '/' + spec.loop;

  check(label + ': ton tai block loop trong du lieu production', !!b);
  if (!b) return;

  const grid = headerGridOf(b);
  const tagByCol = {};
  (b.cols || []).forEach(c => { tagByCol[c.col] = c.tag; });
  const unmappedCols = [];
  for (let c = 0; c < grid.n; c++) if (!tagByCol[c]) unmappedCols.push(c);

  const tableHtml = extractLoopTable(renderLoopOnly(b), spec.loop);
  check(label + ': render ra table loop-table', /class="btable loop-table"/.test(tableHtml));
  if (!tableHtml) return;

  // 1. tổng cột grid header == số td mỗi hàng body
  const headRows = extractHeaderRows(tableHtml);
  const bodyRows = extractBodyRows(tableHtml);
  const headRowsJson = (b.rows || []).filter((r, i) => (b.headerRows || []).indexOf(i) >= 0);
  check(label + ': so hang header render dung schema (' + headRowsJson.length + ')',
    headRows.length === headRowsJson.length, 'got ' + headRows.length);
  const widthsOk = headRows.length > 0 &&
    headRows.every(r => expandHeaderRow(r).length === grid.n);
  check(label + ': header grid co ' + grid.n + ' cot vat ly (mo rong colspan)',
    widthsOk, 'got ' + headRows.map(r => expandHeaderRow(r).length).join(','));
  check(label + ': moi hang body co dung ' + grid.n + ' td',
    bodyRows.length > 0 && bodyRows.every(r => r.length === grid.n),
    'got ' + bodyRows.map(r => r.length).join(','));

  const expBodyRows = Math.max(0, b.blankRows || 0);
  check(label + ': so hang body = max(0 du lieu, ' + expBodyRows + ' blankRows)',
    bodyRows.length === expBodyRows, 'got ' + bodyRows.length);

  // 2. mỗi tag nằm đúng dưới tiêu đề tương ứng (col ZERO-BASED)
  let tagPosOk = true;
  let tagPosBad = '';
  const headSlots = headRows.length ? expandHeaderRow(headRows[headRows.length - 1]) : [];
  (b.cols || []).forEach(c => {
    const td = bodyRows.length ? bodyRows[0][c.col] : null;
    const key = 'loop:' + spec.loop + ':0:' + c.tag;
    if (!td || td.attrs.indexOf('data-key') >= 0 ||
        td.inner.indexOf('data-key="' + key + '"') < 0) {
      tagPosOk = false;
      tagPosBad = c.tag + ' o cot ' + c.col;
      return;
    }
    // tiêu đề phía trên đúng cột đó phải khớp tiêu đề suy từ header grid
    if (headSlots[c.col] && grid.title[c.col] != null &&
        headSlots[c.col].title !== grid.title[c.col]) {
      tagPosOk = false;
      tagPosBad = c.tag + ': title "' + headSlots[c.col].title + '" != "' + grid.title[c.col] + '"';
    }
  });
  check(label + ': moi tag nam dung o duoi tieu de tuong ung', tagPosOk, tagPosBad);

  // 3. colspan/rowspan giữ ở th (đối chiếu từng ô header với schema)
  let thAttrsOk = headRows.length === headRowsJson.length;
  for (let ri = 0; thAttrsOk && ri < headRows.length; ri++) {
    const cellsJson = headRowsJson[ri].cells || [];
    const ths = headRows[ri];
    if (ths.length !== cellsJson.length) { thAttrsOk = false; break; }
    for (let ci = 0; ci < cellsJson.length; ci++) {
      const cs = attrNum(ths[ci].attrs, 'colspan');
      const rs = attrNum(ths[ci].attrs, 'rowspan');
      if (cs !== ((cellsJson[ci].colspan | 0) || 1) ||
          rs !== ((cellsJson[ci].rowspan | 0) || 1)) { thAttrsOk = false; break; }
      if (((cellsJson[ci].colspan | 0) || 1) > 1 && ths[ci].attrs.indexOf('colspan') < 0) {
        thAttrsOk = false; break;
      }
      if (((cellsJson[ci].rowspan | 0) || 1) > 1 && ths[ci].attrs.indexOf('rowspan') < 0) {
        thAttrsOk = false; break;
      }
    }
  }
  check(label + ': th giu nguyen colspan/rowspan tu cell schema', thAttrsOk);

  // 4. STT 1..n khi col0 trống + header chứa "stt"
  const isSttCol = !tagByCol[0] &&
    R.normText(grid.title[0] || '').indexOf('stt') >= 0;
  if (isSttCol) {
    const sttsOk = bodyRows.every((r, i) =>
      r[0] && r[0].attrs.indexOf('class="stt"') >= 0 && r[0].inner === String(i + 1));
    check(label + ': STT tu danh so 1..' + bodyRows.length + ' o cot 0',
      sttsOk, 'got ' + bodyRows.map(r => r[0] ? r[0].inner : '?').join(','));
  } else {
    check(label + ': khong co cot STT (cot 0 hoac co tag hoac header khong noi STT)',
      true);
  }

  // 5. cột không map render td rỗng đúng vị trí (field không trượt cột)
  const emptyCols = unmappedCols.filter(c => !(c === 0 && isSttCol));
  const emptyOk = emptyCols.every(c => bodyRows.every(r =>
    r[c] && r[c].attrs.trim() === '' && r[c].inner.trim() === ''));
  check(label + ': cot khong map (' + emptyCols.join(',') + ') la td rong dung vi tri',
    emptyOk);

  // 6. tag von_* (tiền) giữ class num như hành vi cũ
  const vonTags = (b.cols || []).filter(c => /^von_/.test(c.tag));
  const vonOk = vonTags.every(c => {
    const td = bodyRows[0] && bodyRows[0][c.col];
    return td && /class="fld loop-fld num"/.test(td.inner);
  });
  check(label + ': tag von_* co class num (' + vonTags.map(c => c.tag).join(',') + ')',
    vonOk);

  // 7. mọi input giữ data-key chuẩn loop:<loop>:<idx>:<tag>
  const keyOk = bodyRows.every((r, i) => r.every(td => {
    const m = td.inner.match(/data-key="([^"]+)"/);
    return !m || m[1] === 'loop:' + spec.loop + ':' + i + ':' +
      (m[1].split(':')[3] || '');
  }));
  check(label + ': data-key dung dinh dang loop:<loop>:<idx>:<tag>', keyOk);
});

/* --------------- B. type tổng hợp + header nhiều hàng (tổng hợp) ----------- */

{
  // money / percent -> class num; readonly -> attr readonly; outputOnly -> rỗng
  const bMoney = {
    t: 'loop', loop: 'ds_tong_hop', headerRows: [0], blankRows: 1,
    rows: [{ cells: [
      { runs: [{ text: 'STT' }] },
      { runs: [{ text: 'Von' }] },
      { runs: [{ text: 'Ty le' }] },
      { runs: [{ text: 'Ghichu' }] },
      { runs: [{ text: 'Ro' }] }
    ] }],
    cols: [
      { col: 1, tag: 'von', type: 'money' },
      { col: 2, tag: 'ty_le', type: 'percent' },
      { col: 3, tag: 'ghi_chu', type: 'readonly' },
      { col: 4, tag: 'an', type: 'outputOnly' }
    ]
  };
  const html = renderLoopOnly(bMoney);
  const bodyRow = extractBodyRows(extractLoopTable(html, 'ds_tong_hop'))[0];
  check('type money -> input co class num', !!bodyRow &&
    /class="fld loop-fld num"/.test(bodyRow[1].inner));
  check('type percent -> input co class num', !!bodyRow &&
    /class="fld loop-fld num"/.test(bodyRow[2].inner));
  check('type readonly -> input co attr readonly', !!bodyRow &&
    /\sreadonly[\s>]/.test(bodyRow[3].inner));
  check('type outputOnly -> o rong (khong input)', !!bodyRow &&
    bodyRow[4].inner.trim() === '');
  check('loop tong hop: 5 td/hang dung bang header grid', !!bodyRow && bodyRow.length === 5,
    'got ' + (bodyRow ? bodyRow.length : '?'));

  // checkbox/radio: checked theo row[tag]==='X', data-key vẫn loop:<loop>:<idx>:<tag>
  const bChk = {
    t: 'loop', loop: 'ds_chk', headerRows: [0], blankRows: 0,
    rows: [{ cells: [
      { runs: [{ text: 'STT' }] }, { runs: [{ text: 'Chon' }] }, { runs: [{ text: 'Gioi tinh' }] }]
    }],
    cols: [
      { col: 1, tag: 'chon', type: 'checkbox' },
      { col: 2, tag: 'gioi_tinh', type: 'radio' }
    ]
  };
  const st = R.newStore();
  st.loops.ds_chk = [
    { chon: 'X', gioi_tinh: 'X' },
    {}
  ];
  const htmlChk = renderLoopOnly(bChk, st);
  const chkRows = extractBodyRows(extractLoopTable(htmlChk, 'ds_chk'));
  check('checkbox checked khi row[tag]=="X"',
    /type="checkbox"[^>]*data-key="loop:ds_chk:0:chon"[^>]*checked>/.test(chkRows[0][1].inner) ||
    /type="checkbox"[^>]*checked[^>]*>/.test(chkRows[0][1].inner) &&
    chkRows[0][1].inner.indexOf('data-key="loop:ds_chk:0:chon"') >= 0,
    chkRows[0][1].inner);
  check('checkbox khong checked khi trong (hang 1)',
    chkRows[1][1].inner.indexOf('type="checkbox"') >= 0 &&
    chkRows[1][1].inner.indexOf('checked') < 0, chkRows[1][1].inner);
  const name0 = (chkRows[0][2].inner.match(/name="([^"]+)"/) || [])[1];
  const name1 = (chkRows[1][2].inner.match(/name="([^"]+)"/) || [])[1];
  check('radio name="loop:<loop>:<tag>" giong nhau giua cac hang (browser chon 1/cot)',
    name0 === 'loop:ds_chk:gioi_tinh' && name1 === name0, name0 + ' vs ' + name1);
  check('radio checked theo gia tri X',
    /type="radio"[^>]*checked/.test(chkRows[0][2].inner) &&
    chkRows[1][2].inner.indexOf('checked') < 0);
  check('checkbox/radio van giu data-key loop:<loop>:<idx>:<tag>',
    chkRows[0][1].inner.indexOf('data-key="loop:ds_chk:0:chon"') >= 0 &&
    chkRows[1][2].inner.indexOf('data-key="loop:ds_chk:1:gioi_tinh"') >= 0);
}

{
  // header nhiều hàng: colspan + rowspan overlap -> N tính từ HEADER GRID
  const bMulti = {
    t: 'loop', loop: 'ds_multi', headerRows: [0, 1], blankRows: 2,
    rows: [
      { cells: [
        { runs: [{ text: 'Nhom A' }], colspan: 2 },
        { runs: [{ text: 'Nhom B' }] }
      ] },
      { cells: [
        { runs: [{ text: 'Cot 1' }] },
        { runs: [{ text: 'Cot 2' }] },
        { runs: [{ text: 'Ghi chu' }] }
      ] }
    ],
    cols: [
      { col: 1, tag: 'cot_2', type: 'money' },
      { col: 2, tag: 'ghi_chu' }
    ]
  };
  const grid = headerGridOf(bMulti);
  const htmlMulti = renderLoopOnly(bMulti);
  const table = extractLoopTable(htmlMulti, 'ds_multi');
  const headRows = extractHeaderRows(table);
  const bodyRows = extractBodyRows(table);
  check('header nhieu hang: N = 3 (colspan 2 + 1 o, khong suy tu max col)',
    grid.n === 3 && bodyRows.every(r => r.length === 3),
    'grid.n=' + grid.n + ' tds=' + bodyRows.map(r => r.length).join(','));
  check('header nhieu hang: th dong 0 giu colspan="2"',
    headRows[0].length === 2 && attrNum(headRows[0][0].attrs, 'colspan') === 2);
  check('header nhieu hang: tag dung duoi tieu de con (cot_2 -> "Cot 2")',
    bodyRows[0][1].inner.indexOf('data-key="loop:ds_multi:0:cot_2"') >= 0 &&
    cellText(headRows[1][1]) === 'Cot 2');

  // rowspan: ô X chiếm col0 của 2 hàng header
  const bSpan = {
    t: 'loop', loop: 'ds_span', headerRows: [0, 1], blankRows: 1,
    rows: [
      { cells: [
        { runs: [{ text: 'X' }], rowspan: 2 },
        { runs: [{ text: 'Y' }] }
      ] },
      { cells: [{ runs: [{ text: 'Z' }] }] }
    ],
    cols: [{ col: 1, tag: 'y' }]
  };
  const htmlSpan = renderLoopOnly(bSpan);
  const tSpan = extractLoopTable(htmlSpan, 'ds_span');
  const hSpan = extractHeaderRows(tSpan);
  const bSpan2 = extractBodyRows(tSpan);
  check('rowspan header: X phu col0 hai hang -> N=2, hang 2 bat dau cot 1',
    hSpan[0].length === 2 && attrNum(hSpan[0][0].attrs, 'rowspan') === 2 &&
      hSpan[1].length === 1 && cellText(hSpan[1][0]) === 'Z' &&
      bSpan2.every(r => r.length === 2),
    'h0=' + hSpan[0].length + ' h1=' + hSpan[1].length);
  check('cot 0 co tag bi rowspan phu nhung khong co tag -> td rong (khong STT)',
    bSpan2.every(r => r[0].attrs.trim() === '' && r[0].inner.trim() === ''));

  // NEGATIVE STT: col0 không tag nhưng header KHÔNG chứa "stt" -> không đánh số
  const bNoStt = {
    t: 'loop', loop: 'ds_no_stt', headerRows: [0], blankRows: 2,
    rows: [{ cells: [{ runs: [{ text: 'Ten' }] }, { runs: [{ text: 'A' }] }] }],
    cols: [{ col: 1, tag: 'gia_tri' }]
  };
  const rowsNoStt = extractBodyRows(extractLoopTable(renderLoopOnly(bNoStt), 'ds_no_stt'));
  check('col0 khong tag + header khong co "stt" -> td rong, KHONG tu danh so',
    rowsNoStt.length === 2 &&
      rowsNoStt.every(r => r[0].attrs.trim() === '' && r[0].inner.trim() === ''),
    JSON.stringify(rowsNoStt.map(r => r[0])));
}

// ---------------------------------------------------------------- kết luận
console.log('-'.repeat(60));
console.log('Ket qua: %d PASS / %d FAIL', passed, failed);
process.exit(failed === 0 ? 0 : 1);
