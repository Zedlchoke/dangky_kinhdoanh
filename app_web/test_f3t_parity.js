/* test_f3t_parity.js — F3T Lane B: PARITY UI ↔ DOCX ↔ PDF trên TEMPLATE
 * PRODUCTION (app/templates + app/data/blocks, chỉ đọc), theo chỉ thị owner
 * docs/f3h_f3t_directive_2026-09-08.md (lane B của F3T).
 *
 * Chạy:  node app_web/test_f3t_parity.js
 * Biến môi trường:
 *   F3T_PARITY_PDF=0   tắt chân PDF (mặc định BẬT khi có soffice)
 *   F3T_PYTHON=...     binary python (mặc định python3)
 *
 * Mỗi form anchor (PLII_M01, PLII_M02, PLI_M02, PLI_M10, PLI_M12, PLI_M27,
 * PLI_M79, PLI_M80 + PLI_M72 đủ 5 variant DNTN/TNHH_1TV/TNHH_2TV/CTCP/DHDN),
 * mỗi scenario (paper N=0, n1, nK, nK2=N>K, mixed [data,blank,data,blank],
 * full = fixture valid-full của tools/phase5_fixtures, loop trống inject 3):
 *   (a) UI: app_web/ui/render.js renderBlocks trên blocks production với
 *       store dựng từ CÙNG fixture — đếm hàng hiển thị/data/trống cho mỗi
 *       loop theo ĐÚNG công thức render.js (N-only 2026-09-08):
 *           nRows = max(storeRows.length, minUiRows)
 *       (minUiRows=1 khi gridMeta allowAdd, như controller production);
 *   (b) DOCX: payload export dựng bằng ĐÚNG đường export thật của app
 *       (buildExportData: values + checks 'X' + FD.selectorFlagsOf +
 *       GridCtl.exportLoopsStrict) -> worker Python render qua
 *       tools.docx_render.render với tables_meta=section_specs (như
 *       app_web/main.py Bridge.export) -> python-docx-free đo từng bảng
 *       loop theo registry blankRows (tools.row_placement);
 *   (c) assert cụ thể cho TỪNG loop — [Pin sync — owner N-only 2026-09-08]
 *       hợp đồng mới CHỈ N hàng dữ liệu, KHÔNG hàng trắng:
 *       - parity N-only 2 chiều: UI số hàng chứa dữ liệu == N_store và
 *         DOCX (total - lead - header) == N_export; scenario sạch
 *         (mọi dòng store là business data) hai vế BẰNG NHAU;
 *       - vị trí data NGAY SAU header theo cả 2 hướng: UI tbody row j chứa
 *         dữ liệu store row j (không trống chen trước); DOCX body row j
 *         (sau lead+header) không trống, đúng giá trị payload theo THỨ TỰ,
 *         không có trống chen giữa (mid_gaps=0);
 *       - STT liên tục: UI 1..displayed; DOCX 1..N trên dòng dữ liệu,
 *         không có hàng trống đuôi (tail_blanks=0);
 *       - M72: chỉ variant được chọn xuất — UI chỉ render bảng loop của
 *         variant đó (cond blocks), DOCX chỉ còn bảng variant đó (vùng
 *         {?loai_hinh_*} drop), số bảng = số loop variant;
 *       - detector D18_row_placement (tools/row_placement) 0 hit trên DOCX;
 *       - không còn marker {...} sót trong word/document.xml.
 *   (d) PDF (chân 3 của parity): scenario 'n1' của mỗi form/variant được
 *       convert DOCX→PDF bằng soffice (đường production của main.py) rồi
 *       det_row_placement(pages) — 0 hit. soffice vắng mặt -> in NOT RUN
 *       (không bị coi là PASS kém).
 *
 * Fixture valid-full sinh bởi tools/phase5_fixtures.build_fixture (worker
 * Python); DOCX/PDF output ghi vào /tmp/f3t_parity — GENERATED, không commit.
 * Không sửa production code: test chỉ ĐỌC render.js/form-domain/app.js qua
 * require và ĐỌC tools.* qua worker.
 *
 * Exit 0 = toàn bộ PASS / 1 = FAIL.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const R = require('./ui/render.js');
const App = require('./ui/app.js');
const FD = require('./ui/form-domain.js');
const G = App.GridCtl;

const ROOT = path.join(__dirname, '..');
const BLOCKS_DIR = path.join(ROOT, 'app', 'data', 'blocks');
const TMP = path.join(os.tmpdir(), 'f3t_parity');
const PYTHON = process.env.F3T_PYTHON || 'python3';
const PDF_ON = process.env.F3T_PARITY_PDF !== '0';

/* 8 form anchor của owner directive (M72 xử lý riêng theo variant). */
const ANCHORS = ['PLII_M01', 'PLII_M02', 'PLI_M02', 'PLI_M10', 'PLI_M12',
  'PLI_M27', 'PLI_M79', 'PLI_M80'];

/* PLI_M72: variant -> (giá trị canonical selector 'dn.loai_hinh', flag,
 * loops vùng biến thể) — khớp FORM_SELECTOR_META + M72_CASES anchors lane C. */
const M72_VARIANTS = [
  { label: 'DNTN', value: 'DNTN', flag: 'loai_hinh_dntn',
    loops: ['ds_nganh_dntn'] },
  { label: 'TNHH_1TV', value: 'TNHH_1TV', flag: 'loai_hinh_tnhh_1tv',
    loops: ['ds_nganh_tnhh_1tv'] },
  { label: 'TNHH_2TV', value: 'TNHH_2TV', flag: 'loai_hinh_tnhh_2tv',
    loops: ['ds_nganh_tnhh_2tv', 'ds_thanh_vien_tnhh_2tv'] },
  { label: 'CTCP', value: 'CTCP', flag: 'loai_hinh_ctcp',
    loops: ['ds_nganh_ctcp', 'ds_co_dong_sang_lap_ctcp',
      'ds_co_dong_nuoc_ngoai_ctcp'] },
  { label: 'DHDN', value: 'DHDN', flag: 'loai_hinh_dhdn',
    loops: ['ds_nganh_dhdn', 'ds_thanh_vien_hop_danh_dhdn'] },
];

const SCENARIOS = ['paper', 'n1', 'nK', 'nK2', 'mixed', 'full'];

/* ------------------------------------------------------------------ checks */

let passed = 0;
let failed = 0;
const failLines = [];
function check(name, ok, extra) {
  if (ok) { passed += 1; console.log('PASS  ' + name); }
  else {
    failed += 1;
    const msg = name + (extra ? '  | ' + extra : '');
    failLines.push(msg);
    console.log('FAIL  ' + msg);
  }
}

/* ---------------------------------------------------------------- worker PY */

/* Worker Python GENERATED lúc chạy (ghi vào $TMPDIR/f3t_parity) — không commit.
 * String.raw để giữ nguyên backslash cho phía Python; trong code worker CẤM
 * backtick và "${". */
const PY_WORKER = String.raw`
# -*- coding: utf-8 -*-
"""f3t_parity_worker.py - worker DOCX/PDF cho app_web/test_f3t_parity.js.

File GENERATED boi test (ghi vao /tmp), KHONG commit. Nhan payload export
(dung hinh dang data ma app_web/ui/app.js buildExportData dua cho
Bridge.export), render template production qua tools.docx_render.render voi
tables_meta=section_specs (duong export that cua app_web/main.py), do tung
bang loop theo registry blankRows (tools.row_placement, docx-free) va chay
detector D18 (DOCX + PDF khi co soffice). Ket qua JSON tra stdout.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def _clean(s):
    """Bo entity XML con sot trong trich xuat regex + fold (xoa moi khoang
    trang) - de so khop voi chuoi payload da fold o phia JS."""
    s = (s or '')
    for a, b in (('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                 ('&quot;', '"'), ('&#39;', "'")):
        s = s.replace(a, b)
    return fold_squeeze(s)


def _measure(docx_path, registry):
    """Do tung bang co header khop signature mot loop registry: (lead, header,
    total, n_data, stts, mid_gaps, tail_blanks, body_texts, blank_flags)."""
    with zipfile.ZipFile(str(docx_path)) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    sig_map = {}
    for e in registry:
        if e.get('sig'):
            sig_map.setdefault(e['sig'], []).append(e)
    out = []
    for ti, (ts, te) in enumerate(_balanced_tbls(xml)):
        rows = _top_level_rows(xml[ts:te])
        if not rows:
            continue
        cells = [_row_cells(r) for r in rows]
        texts = [_clean(''.join(cs)) for cs in cells]
        blank = [_row_is_blank(cs) for cs in cells]
        nb = [i for i in range(len(rows)) if not blank[i]]
        if not nb:
            continue
        first_nb, last_nb = nb[0], nb[-1]
        cands = sig_map.get(texts[first_nb], [])
        if not cands:
            continue
        h = min(c['header_rows'] for c in cands)
        body = list(range(first_nb + h, len(rows)))
        data_idx = [i for i in body if not blank[i]]
        out.append({
            'table': ti,
            'loops': sorted(c['loop'] for c in cands),
            'lead': first_nb,
            'header_rows': h,
            'total': len(rows),
            'n_data': len(data_idx),
            'stts': [(cells[i][0].strip() if cells[i] else '')
                     for i in data_idx],
            'mid_gaps': sum(1 for i in range(first_nb, last_nb) if blank[i]),
            'tail_blanks': len(rows) - 1 - last_nb,
            'body_texts': [texts[i] for i in body],
            'blank_flags': [bool(blank[i]) for i in body],
        })
    return out


def _marker_values(data):
    """Gia tri cua CAC DONG LOOP trong payload export (n1 la marker duy nhat
    'loop::tag::i'). Dung de adjudicate hit D18-PDF: hit thuoc bang loop chi
    khi trang PDF co chua gia tri dong data; hit tren trang chi co chu thich/
    noi dung tinh (vd so thu tu chu thich 1..6 doc lam cot STT) la noise cua
    detector generic - khong phai parity loop."""
    out = set()
    for _k, v in (data or {}).items():
        if not isinstance(v, list):
            continue
        for row in v:
            if isinstance(row, dict):
                for vv in row.values():
                    if isinstance(vv, str) and len(vv.strip()) >= 4:
                        out.add(vv.strip())
    return out


def _to_pdf(soffice, src, outdir):
    """DOCX -> PDF qua soffice, profile cach ly per-call (pattern main.py:
    2 call chong nhau qua profile chung -> exit 1 gia)."""
    pdf = outdir / (src.stem + '.pdf')
    if pdf.exists():
        pdf.unlink()
    proc = None
    for suffix in ('', '_retry'):
        prof = Path('/tmp/lo_prof_f3tparity_%d%s' % (os.getpid(), suffix))
        try:
            proc = subprocess.run(
                [soffice, '--headless', '--norestore',
                 '-env:UserInstallation=file://' + str(prof),
                 '--convert-to', 'pdf', '--outdir', str(outdir), str(src)],
                capture_output=True, text=True, timeout=180,
                env=dict(os.environ, HOME=os.environ.get('HOME', '/tmp')))
        finally:
            shutil.rmtree(prof, ignore_errors=True)
        if proc.returncode == 0 and pdf.exists() and pdf.stat().st_size > 0:
            return pdf
    raise RuntimeError('soffice rc=%s' % (proc.returncode if proc else '?'))


def _pdf_pages(pdf_path):
    """Trang PDF -> list {pno, words} cho det_row_placement_pdf.
    Uu tien import pymupdf (khong warning); fitz la shim deprecated can in
    warning ra STDOUT va lam hong giao thuc JSON cho JS."""
    try:
        import pymupdf as fitz
    except ImportError:
        import warnings
        warnings.filterwarnings('ignore')
        import fitz
    doc = fitz.open(str(pdf_path))
    pages = []
    for pno in range(doc.page_count):
        pg = doc.load_page(pno)
        pages.append({'pno': pno,
                      'words': [list(w) for w in pg.get_text('words')]})
    doc.close()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--form')
    ap.add_argument('--outdir', default=None)
    ap.add_argument('--pdf', default='1')
    ap.add_argument('mode', choices=['prepare', 'render'])
    args = ap.parse_args()

    root = Path(args.root)
    sys.path.insert(0, str(root))
    from tools.docx_render import LEFTOVER_RE, render
    from tools.phase5_fixtures import ValueFactory, build_fixture
    from tools.row_placement import (_balanced_tbls, _row_cells, _row_is_blank,
                                     _top_level_rows, det_row_placement,
                                     fold_squeeze, load_loop_registry)
    globals().update(dict(_balanced_tbls=_balanced_tbls, _row_cells=_row_cells,
                          _row_is_blank=_row_is_blank,
                          _top_level_rows=_top_level_rows,
                          fold_squeeze=fold_squeeze))

    blocks = json.loads((root / 'app' / 'data' / 'blocks' /
                         (args.form + '.json')).read_text(encoding='utf-8'))
    maps = json.loads((root / 'app' / 'data' / 'form_maps.json')
                      .read_text(encoding='utf-8'))

    if args.mode == 'prepare':
        data = build_fixture(args.form, maps[args.form], 'valid-full',
                             blocks, ValueFactory())
        json.dump({'fixture': data}, sys.stdout, ensure_ascii=False)
        return

    registry = load_loop_registry(blocks)
    jobs = json.loads(sys.stdin.read())['jobs']
    outdir = Path(args.outdir or '/tmp/f3t_parity')
    outdir.mkdir(parents=True, exist_ok=True)
    tpl = root / 'app' / maps[args.form]['template']
    tables_meta = maps[args.form].get('section_specs') or None
    soffice = shutil.which('soffice') or \
        '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    soffice_ok = bool(shutil.which('soffice')) or Path(soffice).exists()

    results = []
    for job in jobs:
        out = outdir / ('%s__%s.docx' % (args.form, job['scenario']))
        out.write_bytes(render(str(tpl), job['data'],
                               tables_meta=tables_meta))
        with zipfile.ZipFile(str(out)) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        res = {
            'scenario': job['scenario'],
            'docx': out.name,
            'tables': _measure(out, registry),
            'd18': det_row_placement(str(out), registry),
            'leftover': LEFTOVER_RE.findall(xml),
            'pdf': 'not-run',
            'd18_pdf': None,
        }
        if args.pdf == '1' and job.get('pdf'):
            if soffice_ok:
                try:
                    pdf = _to_pdf(soffice, out, outdir)
                    pages = _pdf_pages(pdf)
                    res['pdf'] = pdf.name
                    res['d18_pdf'] = det_row_placement(str(out), registry,
                                                       pages)
                    # adjudicate: hit thuoc bang loop chi khi trang bi bắn
                    # co chua gia tri dong data loop (marker n1); trang chi
                    # co chu thich/noi dung tinh -> noise detector generic.
                    markers = _marker_values(job['data'])
                    for hit in res['d18_pdf']:
                        pno = int(hit.get('page', 1)) - 1
                        ptxt = ''
                        if 0 <= pno < len(pages):
                            ptxt = ' '.join(w[4] for w in
                                            pages[pno]['words'])
                        hit['adj'] = ('loop-table'
                                      if any(m in ptxt for m in markers)
                                      else 'non-loop-content')
                except Exception as exc:  # noqa: BLE001
                    res['pdf'] = 'error'
                    res['d18_pdf'] = [{'code': 'PDF_CONVERT_FAIL',
                                       'detail': type(exc).__name__}]
            else:
                res['pdf'] = 'not-run'
        results.append(res)
    json.dump({'registry': registry, 'results': results}, sys.stdout,
              ensure_ascii=False)


if __name__ == '__main__':
    main()
`;

function ensureWorker() {
  fs.mkdirSync(TMP, { recursive: true });
  const p = path.join(TMP, 'f3t_parity_worker.py');
  fs.writeFileSync(p, PY_WORKER);
  return p;
}

function pyCall(worker, args, input) {
  const out = execFileSync(PYTHON, ['-X', 'utf8', worker].concat(args),
    { input: input || '', maxBuffer: 256 * 1024 * 1024, cwd: ROOT });
  return JSON.parse(out.toString('utf8'));
}

/* ------------------------------------------------------- blocks / registry */

function loadBlocks(fid) {
  return JSON.parse(
    fs.readFileSync(path.join(BLOCKS_DIR, fid + '.json'), 'utf8'));
}

/* Mirror tools.row_placement.load_loop_registry: mọi block t=loop có
 * blankRows>0 -> {loop, k, headerRows, cols}. */
function loopMetaOf(doc) {
  const out = [];
  (function walk(x) {
    if (Array.isArray(x)) { x.forEach(walk); return; }
    if (x && typeof x === 'object') {
      if (x.t === 'loop' && (x.loop || x.name) &&
          (x.blankRows | 0) > 0) {
        out.push({
          loop: x.loop || x.name,
          k: x.blankRows | 0,
          headerRows: x.headerRows || [],
          cols: x.cols || [],
          rows: x.rows || [],
        });
      }
      Object.keys(x).forEach(k => walk(x[k]));
    }
  })(doc.blocks || doc);
  return out;
}

/* Mirror loopHeaderGrid của render.js: nCols + title theo cột từ header grid
 * (occupancy qua colspan/rowspan) — để suy hasStt đúng như renderer. */
function headerGridOf(meta) {
  const idx = meta.headerRows || [];
  const occ = {};
  const title = {};
  let nCols = 0;
  meta.rows.forEach((row, ri) => {
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
    if (w > nCols) nCols = w;
  });
  return { nCols, title };
}

/* Cột mapping của loop — mirror render.js renderLoop: type theo tag từ
 * blocks cols, gridMeta override; outputOnly/checkbox/radio KHÔNG render
 * giá trị text (radio/checkbox hardcode value="X", outputOnly td trống).
 * valTags = tag có giá trị hiển thị trong input text (dùng đối chiếu
 * giá trị store ↔ UI); tag0 = cột có tag đầu (đối chiếu DOCX ↔ payload);
 * hasStt đúng điều kiện render.js (cột 0 không tag + tiêu đề chứa "stt"). */
function colInfoOf(meta, gm) {
  const grid = headerGridOf(meta);
  const typeByTag = {};
  (meta.cols || []).forEach(c => {
    if (c && c.tag) typeByTag[c.tag] = c.type || 'text';
  });
  if (gm && gm.columns) {
    gm.columns.forEach(mc => {
      if (mc && mc.tag && mc.type && typeByTag[mc.tag] !== undefined) {
        typeByTag[mc.tag] = mc.type;
      }
    });
  }
  const tagged = (meta.cols || []).filter(c => c && c.tag)
    .slice().sort((a, b) => a.col - b.col);
  const tags = tagged.map(c => c.tag);
  const valTags = tags.filter(t => {
    const ty = typeByTag[t] || 'text';
    return ty !== 'outputOnly' && ty !== 'checkbox' && ty !== 'radio';
  });
  const col0Tagged = tagged.some(c => c.col === 0);
  const hasStt = !col0Tagged &&
    R.normText(grid.title[0] || '').indexOf('stt') >= 0;
  return { tags, tag0: tags.length ? tags[0] : null, valTags, hasStt };
}

/* ------------------------------------------------------------- UI extract */

function escRe(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function loopTableHtml(html, loop) {
  const m = html.match(
    new RegExp('<table[^>]*data-loop="' + escRe(loop) + '"[^>]*>[\\s\\S]*?</table>'));
  return m ? m[0] : null;
}

function tbodyTrs(tableHtml) {
  const m = tableHtml.match(/<tbody>([\s\S]*?)<\/tbody>/);
  return m ? (m[1].match(/<tr[\s\S]*?<\/tr>/g) || []) : [];
}

function rowStt(trHtml) {
  const m = trHtml.match(/<td class="stt">([^<]*)<\/td>/);
  return m ? m[1] : null;
}

/* Chỉ input TEXT mang giá trị store (text/readonly/money/percent đều render
 * type="text"). Radio/checkbox hardcode value="X" trong HTML nên PHẢI loại
 * để không nhiễu so khớp giá trị. */
function rowInputs(trHtml) {
  const vals = [];
  const re = /<input type="text"[^>]*>/g;
  let m;
  while ((m = re.exec(trHtml))) {
    const vm = m[0].match(/value="([^"]*)"/);
    vals.push(vm ? unesc(vm[1]) : null);
  }
  return vals;
}

function unesc(s) {
  return String(s)
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

function fold(s) { return String(s == null ? '' : s).replace(/\s+/g, ''); }

/* ----------------------------------------------------- store / scenarios */

function newStoreFrom(fixture) {
  const store = { values: {}, checks: {}, loops: {} };
  Object.keys(fixture).forEach(k => {
    const v = fixture[k];
    if (Array.isArray(v)) store.loops[k] = v.map(r => Object.assign({}, r));
    else store.values[k] = v;
  });
  return store;
}

function genRow(loop, tags, i) {
  const r = {};
  tags.forEach(t => { r[t] = loop + '::' + t + '::' + (i + 1); });
  return r;
}

function isBusinessRow(row) {
  return Object.keys(row || {}).some(k =>
    k.charAt(0) !== '_' && String(row[k] == null ? '' : row[k]).trim() !== '');
}

/* Scenario: tất cả loop registry nhận cùng chính sách số dòng (giữ dữ liệu
 * fixture cho 'full', loop trống inject 3 — như anchors lane C). */
function applyScenario(store, scenario, metas) {
  metas.forEach(meta => {
    const tags = colInfoOf(meta).tags;
    let rows = (store.loops[meta.loop] || []).map(r => Object.assign({}, r));
    if (scenario === 'paper') rows = [];
    else if (scenario === 'n1') rows = [genRow(meta.loop, tags, 0)];
    else if (scenario === 'nK') {
      rows = []; for (let i = 0; i < meta.k; i++) rows.push(genRow(meta.loop, tags, i));
    } else if (scenario === 'nK2') {
      rows = []; for (let i = 0; i < meta.k + 2; i++) rows.push(genRow(meta.loop, tags, i));
    } else if (scenario === 'mixed') {
      rows = [genRow(meta.loop, tags, 0), {}, genRow(meta.loop, tags, 1), {}];
    } else if (scenario === 'full') {
      if (!rows.length) {
        for (let i = 0; i < 3; i++) rows.push(genRow(meta.loop, tags, i));
      }
    }
    store.loops[meta.loop] = rows;
  });
}

/* ĐÚNG buildExportData của app_web/ui/app.js (chốt export thật):
 * values + checks 'X' + selectorFlagsOf từng mẫu + exportLoopsStrict. */
function exportDataOf(store, fid) {
  const data = {};
  Object.keys(store.values).forEach(k => { data[k] = store.values[k]; });
  Object.keys(store.checks).forEach(k => { data[k] = store.checks[k] ? 'X' : ''; });
  const flags = FD.selectorFlagsOf(fid, store);
  Object.keys(flags).forEach(k => { data[k] = flags[k]; });
  const loops = G.exportLoopsStrict(store, [fid]);
  Object.keys(loops).forEach(name => { data[name] = loops[name]; });
  return { data, flags, loops };
}

/* ----------------------------------------------------- contract assertors */

/* DOCX contract của một bảng loop (F3T.2 N-only — [Pin sync — owner N-only
 * 2026-09-08]: CHỈ N hàng dữ liệu sau header, KHÔNG hàng trắng, N = nExport). */
function docxTableErrors(meta, n, t, exportedRows, tag0) {
  const errs = [];
  const L = meta.loop;
  // [Pin sync — owner N-only 2026-09-08] tổng body = N (không max(K,N))
  const expectBody = n;
  if (t.total !== t.lead + t.header_rows + expectBody) {
    errs.push('DOCX %s: total=%d != lead=%d + header=%d + N=%d'
      .replace('%s', L).replace('%d', String(t.total))
      .replace('%d', String(t.lead)).replace('%d', String(t.header_rows))
      .replace('%d', String(n)));
  }
  if (t.n_data !== n) errs.push('DOCX %s: n_data=%d != N=%d'
    .replace('%s', L).replace('%d', String(t.n_data)).replace('%d', String(n)));
  const sttExpect = []; for (let i = 1; i <= n; i++) sttExpect.push(String(i));
  if (JSON.stringify(t.stts) !== JSON.stringify(sttExpect)) {
    errs.push('DOCX %s: STT data %s != 1..%d (STT lien tuc tren data)'
      .replace('%s', L).replace('%s', JSON.stringify(t.stts))
      .replace('%d', String(n)));
  }
  if (t.mid_gaps !== 0) errs.push('DOCX %s: %d blank chen giua header/data'
    .replace('%s', L).replace('%d', String(t.mid_gaps)));
  // [Pin sync — owner N-only 2026-09-08] KHÔNG hàng trắng đuôi (bỏ hợp đồng
  // max(K-N,0) trắng in sẵn)
  if (t.tail_blanks !== 0) {
    errs.push('DOCX %s: tail_blanks=%d != 0 (N-only: khong hang trang)'
      .replace('%s', L).replace('%d', String(t.tail_blanks)));
  }
  t.blank_flags.forEach((b, i) => {
    // [Pin sync — owner N-only 2026-09-08] mọi body row phải là dữ liệu
    // (body chỉ còn đúng N hàng, data liền kề sau header)
    if (b !== false) {
      errs.push('DOCX %s: body row %d blank=%s (N-only: moi body row phai la data)'
        .replace('%s', L).replace('%d', String(i))
        .replace('%s', String(b)));
    }
  });
  // giá trị theo THỨ TỰ: body row j chứa giá trị cột đầu của payload row j
  for (let j = 0; j < n && j < exportedRows.length; j++) {
    const exp = exportedRows[j] ? exportedRows[j][tag0] : '';
    if (exp != null && String(exp).trim() !== '' &&
        t.body_texts[j] !== undefined &&
        t.body_texts[j].indexOf(fold(exp)) < 0) {
      errs.push('DOCX %s: body row %d khong chua gia tri payload %j (thu tu data)'
        .replace('%s', L).replace('%d', String(j))
        .replace('%j', JSON.stringify(String(exp).trim())));
    }
  }
  return errs;
}

/* UI contract của một loop (công thức render.js N-only — [Pin sync — owner
 * N-only 2026-09-08]: số hàng tbody = max(storeRows.length, minUiRows),
 * KHÔNG còn blankRows K; data ngay sau thead). */
function uiLoopErrors(meta, info, storeRows, nExport, scenario, html, minUi) {
  const errs = [];
  const L = meta.loop;
  const tbl = loopTableHtml(html, L);
  if (!tbl) { errs.push('UI ' + L + ': khong tim thay bang loop'); return errs; }
  const trs = tbodyTrs(tbl);
  // [Pin sync — owner N-only 2026-09-08] chỉ N hàng dữ liệu (ghì tối đa
  // minUiRows khi trống) — bỏ max(K, …) hàng trắng
  const expectRows = Math.max(storeRows.length, minUi);
  if (trs.length !== expectRows) {
    errs.push('UI ' + L + ': displayed=' + trs.length +
      ' != max(store=' + storeRows.length +
      ', minUi=' + minUi + ')=' + expectRows);
  }
  // STT lien tuc 1..displayed (UI danh so moi hang hien thi)
  if (info.hasStt) {
    for (let i = 0; i < trs.length; i++) {
      const stt = rowStt(trs[i]);
      if (stt !== String(i + 1)) {
        errs.push('UI ' + L + ': STT row ' + i + '=' + JSON.stringify(stt) +
          ', ky vong ' + (i + 1) + ' (STT lien tuc)');
        break;
      }
    }
  }
  // vị trí data: scenario sạch -> data = row 0..N-1, trống đuôi; mixed -> data
  // đúng vị trí store (UI hiển thị data nơi người dùng nhập).
  if (scenario !== 'mixed') {
    for (let j = 0; j < nExport && j < storeRows.length; j++) {
      const nonEmpty = rowInputs(trs[j])
        .filter(v => v != null && String(v).trim() !== '');
      if (!nonEmpty.length) {
        errs.push('UI ' + L + ': row ' + j + ' trong khi la dong data (data phai ngay sau header)');
        break;
      }
      // data->UI: mọi giá trị cột hiển thị được (khác rỗng) của store row j
      // phải hiện đúng ở row j (không trượt hàng)
      const missing = info.valTags.filter(t =>
        storeRows[j][t] != null && String(storeRows[j][t]).trim() !== '' &&
        nonEmpty.indexOf(String(storeRows[j][t])) < 0);
      if (missing.length) {
        errs.push('UI ' + L + ': row ' + j + ' thieu gia tri store ' + JSON.stringify(missing));
        break;
      }
    }
    for (let j = nExport; j < trs.length; j++) {
      const nonEmpty = rowInputs(trs[j])
        .filter(v => v != null && String(v).trim() !== '');
      if (nonEmpty.length) {
        errs.push('UI ' + L + ': row duoi ' + j + ' co du lieu ' + JSON.stringify(nonEmpty[0]) +
          ' (K-N dong trang phai trong)');
        break;
      }
    }
  } else {
    // mixed: UI giữ data đúng vị trí store (0,2), blank store (1,3) vẫn hiển thị
    for (let i = 0; i < storeRows.length && i < trs.length; i++) {
      const nonEmpty = rowInputs(trs[i])
        .filter(v => v != null && String(v).trim() !== '');
      if (isBusinessRow(storeRows[i]) && !nonEmpty.length) {
        errs.push('UI ' + L + ' mixed: row ' + i + ' chua data store');
        break;
      }
      if (!isBusinessRow(storeRows[i]) && nonEmpty.length) {
        errs.push('UI ' + L + ' mixed: row ' + i + ' khong trong du store blank');
        break;
      }
    }
  }
  return errs;
}

/* ------------------------------------------------------------ run one case */

function runCase(worker, fid, variant) {
  const label = fid + (variant ? '[' + variant.label + ']' : '');
  const doc = loadBlocks(fid);
  const metas = loopMetaOf(doc);
  const activeLoops = variant ? variant.loops : metas.map(m => m.loop);
  const activeSet = {};
  activeLoops.forEach(l => { activeSet[l] = true; });
  const metaByLoop = {};
  metas.forEach(m => { metaByLoop[m.loop] = m; });

  // gridMeta production-like (controller build từ FORM_GRID_META/GRID_META)
  const gridMeta = {};
  metas.forEach(m => {
    const gm = FD.getGridMeta({ docId: fid, loop: m.loop });
    if (gm) gridMeta[m.loop] = gm;
  });
  // colInfo một lần/loop (effective type đã gồm gridMeta override)
  const infoByLoop = {};
  metas.forEach(m => {
    infoByLoop[m.loop] = colInfoOf(m, gridMeta[m.loop]);
  });

  const fixture = pyCall(worker, ['--root', ROOT, '--form', fid,
    'prepare']).fixture;

  const jobs = [];
  const ctx = {};   // scenario -> {store, flags, loops, nOf}
  SCENARIOS.forEach(sc => {
    const store = newStoreFrom(fixture);
    if (variant) store.values['dn.loai_hinh'] = variant.value;
    applyScenario(store, sc, metas);
    G.ensureIds(store);
    const ex = exportDataOf(store, fid);
    ctx[sc] = { store, flags: ex.flags, loops: ex.loops, data: ex.data };
    ctx[sc].nOf = {};
    metas.forEach(m => {
      ctx[sc].nOf[m.loop] = (ex.loops[m.loop] || []).length;
    });
    jobs.push({ scenario: sc, data: ex.data, pdf: sc === 'n1' });
  });

  const res = pyCall(worker, ['--root', ROOT, '--form', fid,
    '--outdir', TMP, '--pdf', PDF_ON ? '1' : '0', 'render'],
    JSON.stringify({ jobs }));
  const resBy = {};
  res.results.forEach(r => { resBy[r.scenario] = r; });

  // tổng số bảng registry-matched = số loop active (M72: bảng variant khác bị drop)
  SCENARIOS.forEach(sc => {
    const r = resBy[sc];
    check(label + ' ' + sc + ' [bang-table-count]',
      r.tables.length === activeLoops.length,
      'DOCX tables=' + r.tables.length + ' != active loops=' + activeLoops.length +
      ' (' + r.tables.map(t => t.loops.join('/')).join(', ') + ')');
  });

  SCENARIOS.forEach(sc => {
    const c = ctx[sc];
    const r = resBy[sc];
    const html = R.renderBlocks(doc, c.store, {
      docId: fid, flags: c.flags, gridMeta,
    });
    const errs = [];

    // M72: chỉ variant được chọn hiển thị/xuất
    if (variant) {
      metas.forEach(m => {
        const present = loopTableHtml(html, m.loop) !== null;
        if (!!activeSet[m.loop] !== present) {
          errs.push('UI presence ' + m.loop + '=' + present +
            ' (chi variant ' + variant.label + ' duoc render)');
        }
      });
      Object.keys(c.flags).forEach(fl => {
        const expect = fl === variant.flag ? 'X' : '';
        if (String(c.flags[fl]) !== expect) {
          errs.push('flags ' + fl + '=' + c.flags[fl] + ' != ' + expect);
        }
      });
    }

    // UI contract per loop
    metas.forEach(m => {
      if (!activeSet[m.loop]) return;
      const gm = gridMeta[m.loop];
      const minUi = (gm && gm.allowAdd !== false) ? 1 : 0;
      errs.push.apply(errs, uiLoopErrors(m, infoByLoop[m.loop],
        c.store.loops[m.loop], c.nOf[m.loop], sc, html, minUi));
    });

    // DOCX contract per loop + max parity 2 chiều
    const tables = r.tables;
    const groups = [];
    tables.forEach(t => {
      let g = null;
      groups.forEach(x => {
        if (!g && x.loops.join('|') === t.loops.join('|')) g = x;
      });
      if (!g) { g = { loops: t.loops, tables: [] }; groups.push(g); }
      g.tables.push(t);
    });
    groups.forEach(g => {
      const active = g.loops.filter(l => activeSet[l]);
      if (g.tables.length !== active.length) {
        errs.push('DOCX nhom sig [' + g.loops.join('/') + ']: ' +
          g.tables.length + ' bang != ' + active.length + ' loop active');
        return;
      }
      const used = {};
      active.forEach(loop => {
        const meta = metaByLoop[loop];
        const info = infoByLoop[loop];
        const n = c.nOf[loop];
        const exported = c.loops[loop] || [];
        let best = null;
        g.tables.forEach((t, i) => {
          if (used[i]) return;
          const te = docxTableErrors(meta, n, t, exported, info.tag0);
          if (!best || te.length < best.errs.length) {
            best = { i, errs: te };
          }
        });
        if (best && !best.errs.length) { used[best.i] = true; return; }
        if (best) errs.push.apply(errs, best.errs);
        else errs.push('DOCX ' + loop + ': khong con bang nao de khop trong nhom');
      });

      // max parity 2 chiều cho scenario sạch (mọi dòng store là business):
      //   UI tbody = max(K,N) == DOCX total - lead - header
      if (sc !== 'mixed') {
        active.forEach(loop => {
          const meta = metaByLoop[loop];
          const storeLen = (c.store.loops[loop] || []).length;
          const n = c.nOf[loop];
          if (storeLen !== n) return;   // đã là mixed-style; contract riêng vẫn assert
          const tbl = loopTableHtml(html, loop);
          if (!tbl) return;
          const uiBody = tbodyTrs(tbl).length;
          const t = g.tables.find(tt =>
            !docxTableErrors(meta, n, tt, c.loops[loop] || [],
              infoByLoop[loop].tag0).length) || g.tables[0];
          if (uiBody !== t.total - t.lead - t.header_rows) {
            errs.push('PARITY ' + loop + ': UI body=' + uiBody +
              ' != DOCX body=' + (t.total - t.lead - t.header_rows) +
              ' (max(K=' + meta.k + ',N=' + n + ') lech giua UI va DOCX)');
          }
        });
      } else {
        // mixed: hai engine phải ĐỒNG NHẤT về N (exportLoops ↔ last-mile guard)
        active.forEach(loop => {
          const storeLen = (c.store.loops[loop] || []).length;
          const nBiz = (c.store.loops[loop] || []).filter(isBusinessRow).length;
          const t = g.tables[0];
          if (t.n_data !== nBiz) {
            errs.push('PARITY mixed ' + loop + ': DOCX n_data=' + t.n_data +
              ' != N business=' + nBiz + ' (hai engine lech ve N)');
          }
          if (storeLen !== 4 || nBiz !== 2) {
            errs.push('PARITY mixed ' + loop + ': fixture store=' + storeLen +
              '/biz=' + nBiz + ' khong dung mau [data,blank,data,blank]');
          }
        });
      }
    });

    // detector + leftover + PDF
    if (r.d18.length) errs.push('D18: ' + JSON.stringify(r.d18));
    if (r.leftover.length) errs.push('leftover marker: ' + JSON.stringify(r.leftover));
    if (sc === 'n1' && PDF_ON) {
      if (r.d18_pdf === null || r.pdf === 'not-run') {
        console.log('NOTE  ' + label + ' n1: PDF leg NOT RUN (khong co soffice)');
      } else {
        const real = r.d18_pdf.filter(h => h.adj !== 'non-loop-content');
        const noise = r.d18_pdf.filter(h => h.adj === 'non-loop-content');
        if (real.length) errs.push('D18-PDF: ' + JSON.stringify(real));
        noise.forEach(h => {
          console.log('NOTE  ' + label + ' n1: D18-PDF hit phan loai ' +
            'non-loop-content (trang khong chua du lieu loop - noise cua ' +
            'detector generic tren noi dung tinh): ' + JSON.stringify(h));
        });
      }
    }

    check(label + ' ' + sc, errs.length === 0, errs.join(' | '));
  });
}

/* ------------------------------------------------------------------- main */

function main() {
  console.log('test_f3t_parity — F3T Lane B: parity UI (render.js) <-> DOCX' +
    ' (docx_render) <-> PDF (soffice + D18) tren production templates');
  console.log('PDF leg: ' + (PDF_ON ? 'ON (so sang n1 per form/variant)' : 'OFF'));
  const worker = ensureWorker();

  ANCHORS.forEach(fid => runCase(worker, fid, null));
  M72_VARIANTS.forEach(v => runCase(worker, 'PLI_M72', v));

  console.log('-'.repeat(72));
  console.log('test_f3t_parity: %d PASS / %d FAIL', passed, failed);
  if (failed) {
    console.log('Cac fail:');
    failLines.forEach(l => console.log(' - ' + l));
    console.log('Parity FAIL = defect -> bao Lead quyet (khong va production code).');
  }
  return failed === 0 ? 0 : 1;
}

process.exit(main());
