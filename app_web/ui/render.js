/* render.js - các hàm THUẦN sinh HTML từ blocks schema (không phụ thuộc DOM).
 * Dùng chung cho app.js (trong webview) và test_dom.js (node require).
 * UMD nhẹ: gắn vào module.exports (node) hoặc window.Render (browser). */
(function (root) {
  'use strict';

  // ------------------------------------------------------------------ utils

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /* Chữ thường + bỏ dấu (đ -> d): dùng cho tra cứu VSIC không dấu. */
  function normText(s) {
    return String(s == null ? '' : s)
      .toLowerCase()
      .replace(/đ/g, 'd')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  function formatVnd(n) {
    var neg = n < 0;
    var s = String(Math.abs(Math.round(n)));
    var out = '';
    while (s.length > 3) {
      out = '.' + s.slice(-3) + out;
      s = s.slice(0, -3);
    }
    return (neg ? '-' : '') + s + out;
  }

  function parseNum(v) {
    if (v == null) return null;
    var s = String(v).replace(/[^\d.,-]/g, '').replace(/\./g, '').replace(/,/g, '');
    if (!s || s === '-') return null;
    var n = parseFloat(s);
    return isNaN(n) ? null : n;
  }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  // ------------------------------------------------- L2: layout contract v3

  /* Wave L2 (blocks-v3, docs/layout_l1_contract.md): CHỈ các key format này
   * được map sang CSS custom property. Giá trị lạ/không hợp lệ bị BỎ (fail-soft)
   * - không bao giờ đưa chuỗi style tự do từ JSON vào HTML. */
  var FORMAT_ALLOWLIST = {
    leftIndentPt:      '--pt-left-indent',
    rightIndentPt:     '--pt-right-indent',
    firstLineIndentPt: '--pt-first-line-indent',
    spaceBeforePt:     '--pt-space-before',
    spaceAfterPt:      '--pt-space-after',
    lineSpacing:       '--pt-line-spacing',
    lineSpacingPt:     '--pt-line-spacing-pt',
    keepWithNext:      '--pt-keep-with-next'
  };

  var ROLES_L2 = ['source-indicator', 'form-number', 'national-header',
    'national-motto', 'national-separator', 'date-line', 'form-title',
    'form-subtitle', 'salutation', 'body', 'section-heading', 'note',
    'footnote', 'signature'];

  /* Chỉ cho phép ký tự an toàn trong class/attr sinh từ dữ liệu. */
  function safeToken(s) {
    return String(s == null ? '' : s).replace(/[^A-Za-z0-9_-]/g, '');
  }

  /* Số pt hợp lệ (hỗ trợ âm - hanging indent) -> "6" | "-9.5" | null. */
  function safeNum(v) {
    if (typeof v !== 'number' || !isFinite(v)) return null;
    var s = String(Math.round(v * 100) / 100);
    return /^-?\d+(\.\d+)?$/.test(s) ? s : null;
  }

  /* format JSON -> attr style chỉ chứa custom property đã khai allowlist.
   * Đơn vị gắn tại đây: pt cho khoảng cách, lineSpacing giữ không đơn vị
   * (multiple của line-height), keepWithNext=true -> "avoid". */
  function formatStyleAttr(format) {
    if (!format || typeof format !== 'object') return '';
    var out = '';
    Object.keys(FORMAT_ALLOWLIST).forEach(function (k) {
      if (!(k in format)) return;
      var v = format[k];
      if (k === 'keepWithNext') {
        if (v === true) out += FORMAT_ALLOWLIST[k] + ':avoid;';
        return;
      }
      if (k === 'lineSpacing') { // multiple, không đơn vị
        if (safeNum(v) != null && v > 0) {
          out += FORMAT_ALLOWLIST[k] + ':' + safeNum(v) + ';';
        }
        return;
      }
      var n = safeNum(v);
      if (n != null) out += FORMAT_ALLOWLIST[k] + ':' + n + 'pt;';
    });
    return out ? ' style="' + escapeHtml(out) + '"' : '';
  }

  /* Role -> class bổ sung cho block p. Role lạ/rỗng => rỗng (block cũ v2). */
  function roleClassOf(role) {
    if (!role || ROLES_L2.indexOf(role) < 0) return '';
    return ' bp-role-' + safeToken(role);
  }

  /* Escape TRƯỚC, sau đó mới chuyển break hợp lệ: \n -> <br>,
   * \t -> span tab có bề rộng (không dùng &nbsp; hàng loạt). */
  function textToHtml(s) {
    return escapeHtml(s)
      .split('\t').join('<span class="tb" aria-hidden="true"></span>')
      .split('\n').join('<br>');
  }

  /* Run footnote-ref -> <sup class="fn-ref">; id chỉ nhận token an toàn.
   * Block không có footnotes vẫn hiện số (fail-soft theo contract L1 mục 4). */
  function footnoteRefHtml(run) {
    var id = safeToken(run.footnoteId);
    if (!id) return '';
    return '<sup class="fn-ref" data-fn="' + id + '" tabindex="0">' + id + '</sup>';
  }

  /* Vùng chú thích cuối block p có b.footnotes (map id_string -> text). */
  function footnotesListHtml(footnotes) {
    if (!footnotes || typeof footnotes !== 'object') return '';
    var lis = '';
    Object.keys(footnotes).forEach(function (idStr) {
      var id = safeToken(idStr);
      if (!id) return;
      lis += '<li id="fn-' + id + '">' + textToHtml(footnotes[idStr]) + '</li>';
    });
    return lis ? '<ol class="fn-list">' + lis + '</ol>' : '';
  }

  /* Progressive enhancement cho .fn-ref (click/focus scroll tới li#fn-*).
   * Thuần tùy chọn: không gọi thì số chú thích vẫn hiển thị bình thường. */
  function bindFootnoteRefs(rootEl) {
    if (!rootEl || typeof rootEl.addEventListener !== 'function') return null;
    function go(e) {
      var t = e.target;
      while (t && t !== rootEl && !(t.classList && t.classList.contains('fn-ref'))) {
        t = t.parentNode;
      }
      if (!t || t === rootEl || !t.getAttribute) return;
      var li = document.getElementById('fn-' + t.getAttribute('data-fn'));
      if (!li) return;
      e.preventDefault();
      li.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (li.setAttribute) {
        li.setAttribute('tabindex', '-1');
        li.focus({ preventScroll: true });
      }
    }
    rootEl.addEventListener('click', go);
    rootEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') go(e);
    });
    return rootEl;
  }

  /* F-P3-A11Y-LABEL: input .chk-box sinh từ block chk / run.input.chk PHẢI giữ
   * nguyên chuỗi attribute (test_dom + test_layout_l2_render pin đúng chuỗi
   * '<input type="checkbox" class="chk-box" data-key="..." checked>'), nên nhãn
   * cho trình đọc màn hình được gắn ở bước enhancement phía DOM — cùng pattern
   * với enhanceEditableGrids của controller: caller cũ vẫn nhận HTML y như cũ.
   * Nguồn nhãn: <label> bọc ngoài (block chk đã có chữ hiển thị) > chữ tĩnh
   * đứng trước ô trong cùng cha (như prevStaticText: gom lại, lấy 90 ký tự
   * cuối) > data-key. Checkbox bảng lặp (loop-chk/loop-radio) đã có aria-label
   * từ fieldAriaAttrs nên được bỏ qua; chạy lại nhiều lần vẫn idempotent. */
  function enhanceChkLabels(rootEl) {
    if (!rootEl || typeof rootEl.querySelectorAll !== 'function') return null;
    Array.prototype.forEach.call(rootEl.querySelectorAll('input.chk-box'),
      function (el) {
        if ((el.getAttribute('aria-label') || '').trim()) return;
        var wrap = el.closest ? el.closest('label') : null;
        var label = wrap ? (wrap.textContent || '').replace(/\s+/g, ' ').trim() : '';
        if (!label) {
          var parts = [], hops = 0, node = el.previousSibling;
          while (node && hops++ < 24) {
            var t = (node.nodeType === 3 ? node.nodeValue : node.textContent) || '';
            if (t.replace(/\s+/g, ' ').trim()) parts.unshift(t);
            node = node.previousSibling;
          }
          var s = parts.join(' ').replace(/\s+/g, ' ').trim();
          label = s.length > 90 ? s.slice(s.length - 90).trim() : s;
        }
        el.setAttribute('aria-label',
          label || el.getAttribute('data-key') || 'Ô chọn');
      });
    return rootEl;
  }

  /* Enhancement DOM cho một section VỪA gắn vào cây: footnote ref (như cũ) +
   * aria-label cho checkbox. entry point duy nhất của harness (snapshot.html
   * gọi bindFootnoteRefs) và controller (app.js gọi sau renderActiveDoc). */
  function enhanceSectionDom(rootEl) {
    bindFootnoteRefs(rootEl);
    enhanceChkLabels(rootEl);
    return rootEl;
  }

  // ------------------------------------------------------------------ store

  function newStore() {
    return { values: {}, checks: {}, loops: {} };
  }

  function cloneStore(store) {
    var loops = {};
    Object.keys(store.loops || {}).forEach(function (name) {
      loops[name] = (store.loops[name] || []).map(function (row) {
        return Object.assign({}, row);
      });
    });
    return {
      values: Object.assign({}, store.values || {}),
      checks: Object.assign({}, store.checks || {}),
      loops: loops
    };
  }

  /* Accessor đọc giá trị từ store. Ô trong bảng lặp có key dạng
   * "loop:<ten_loop>:<chi_so_hang>:<tag>". */
  function makeAccessors(store) {
    function getVal(key) {
      if (key.indexOf('loop:') === 0) {
        var parts = key.split(':');
        var row = ((store.loops || {})[parts[1]] || [])[+parts[2]] || {};
        return row[parts[3]] == null ? '' : String(row[parts[3]]);
      }
      return (store.values || {})[key] == null ? '' : String(store.values[key]);
    }
    function getChk(key) {
      return !!(store.checks || {})[key];
    }
    return { getVal: getVal, getChk: getChk, storeRef: store };
  }

  // ------------------------------------------------------------- render runs

  /* rctx: ngữ cảnh metadata tuỳ chọn {fieldMeta, docId, ids}. Không truyền
   * (renderBlocks 2 tham số như cũ) => hành vi giống bản cũ 100%. */
  function sanitizeFieldId(key) {
    return String(key).replace(/[^A-Za-z0-9_.:-]/g, '_');
  }

  function nextFieldId(rctx, key) {
    var base = 'f_' + sanitizeFieldId(key);
    var n = (rctx.ids[base] || 0) + 1;
    rctx.ids[base] = n;
    return n === 1 ? base : base + '_' + n;
  }

  /* Fallback nhãn: chuỗi text tĩnh liền TRƯỚC input trong cùng đoạn/ô. */
  function prevStaticText(runs, idx) {
    var parts = [];
    for (var i = 0; i < idx; i++) {
      var r = runs[i];
      if (r && r.text != null) parts.push(String(r.text));
    }
    var s = parts.join(' ').replace(/\s+/g, ' ').trim();
    return s.length > 90 ? s.slice(s.length - 90).trim() : s;
  }

  /* data-field-id + aria-label/inputmode/aria-required từ fieldMeta (nếu có). */
  function fieldAriaAttrs(key, rctx, runs, idx, fallbackLabel) {
    var m = rctx.fieldMeta ? (rctx.fieldMeta[key] || null) : null;
    var label = (m && m.label) || fallbackLabel || prevStaticText(runs, idx) ||
      (rctx.docId ? rctx.docId + ' - ' : '') + key;
    var attrs = ' data-field-id="' + escapeHtml(nextFieldId(rctx, key)) +
      '" aria-label="' + escapeHtml(label) + '"';
    if (m && m.required) attrs += ' aria-required="true"';
    var extraCls = '';
    if (m && (m.type === 'money' || m.type === 'number')) {
      attrs += ' inputmode="numeric"';
      extraCls = ' num';
    } else if (m && m.type === 'email') {
      attrs += ' inputmode="email"';
    }
    return { attrs: attrs, extraCls: extraCls };
  }

  function renderRun(run, ac, rctx, runs, idx) {
    rctx = rctx || { fieldMeta: null, docId: '', ids: {} };
    if (run && run.input) {
      var inp = run.input;
      if (inp.chk !== undefined) {
        // giữ nguyên cấu trúc attribute của checkbox (test_dom phụ thuộc)
        return '<input type="checkbox" class="chk-box" data-key="' + escapeHtml(inp.key) + '"' +
          (ac.getChk(inp.key) ? ' checked' : '') + '>';
      }
      var w = inp.w || 20;
      var fa = fieldAriaAttrs(inp.key, rctx, runs, idx);
      var cls = 'fld' + fa.extraCls;
      if (AUTO_KEYS[inp.key] === 'calc') cls += ' calc';
      return '<input type="text" class="' + cls + '" data-key="' + escapeHtml(inp.key) +
        '" style="width:' + w + 'ch"' + fa.attrs +
        ' value="' + escapeHtml(ac.getVal(inp.key)) + '">';
    }
    if (!run) return '';
    if (run.role === 'footnote-ref') return footnoteRefHtml(run);
    /* L2: sup/sub SEMANTIC (blocks-v3 run.vertAlign); \n/\t bảo toàn qua
     * textToHtml (escape trước). Run không đổi nghĩa với blocks cũ. */
    var tag = run.vertAlign === 'superscript' ? 'sup'
      : (run.vertAlign === 'subscript' ? 'sub' : 'span');
    var cn = 'rn' + (run.b ? ' rn-b' : '') + (run.i ? ' rn-i' : '') + (run.u ? ' rn-u' : '');
    return '<' + tag + ' class="' + cn + '">' + textToHtml(run.text) + '</' + tag + '>';
  }

  function renderRuns(runs, ac, rctx) {
    return (runs || []).map(function (r, i) {
      return renderRun(r, ac, rctx, runs, i);
    }).join('');
  }

  // ----------------------------------------------------------- render blocks

  /* Wave L2 (contract blocks-v3):
   * - role=source-indicator: BỎ khỏi DOM hoàn toàn (marker kỹ thuật), đếm
   *   vào rctx.siSkipped để renderBlocks log console.debug đúng 1 lần/form.
   *   KHÔNG bao giờ ẩn role=form-number (dòng pháp lý "Mẫu số N" phải hiện,
   *   giữ align từ dữ liệu).
   * - class: bp + bp-<align> + bp-role-<role> (14 role L1).
   * - format -> inline CSS custom property qua FORMAT_ALLOWLIST (mục trên).
   * - b.footnotes -> <ol class="fn-list"> ngay sau đoạn chứa ref.
   * - date-line KHÔNG chứa input -> thêm bp-flex (flex wrap an toàn thay
   *   giả tab bằng &nbsp;; có input thì giữ block layout thường). */
  function renderBlockP(b, ac, rctx) {
    rctx = rctx || { fieldMeta: null, docId: '', ids: {}, siSkipped: [] };
    if (!rctx.siSkipped) rctx.siSkipped = [];
    if (b.role === 'source-indicator') {
      rctx.siSkipped.push(b);
      return '';
    }
    var cls = 'bp bp-' + (b.align || 'left') + roleClassOf(b.role);
    if (b.role === 'date-line' && !(b.runs || []).some(function (r) {
      return r && r.input;
    })) cls += ' bp-flex';
    var html = '<p class="' + cls + '"' + formatStyleAttr(b.format) + '>' +
      renderRuns(b.runs, ac, rctx) + '</p>' + footnotesListHtml(b.footnotes);
    return html;
  }

  function renderBlock(b, ac, rctx) {
    switch (b.t) {
      case 'p':
        return renderBlockP(b, ac, rctx);
      case 'chk':
        return '<label class="bchk"><input type="checkbox" class="chk-box" data-key="' +
          escapeHtml(b.key) + '"' + (ac.getChk(b.key) ? ' checked' : '') +
          '><span>' + escapeHtml(b.label || '') + '</span></label>';
      case 'table':
        return renderTableRows(b, ac, rctx);
      case 'loop':
        return renderLoop(b, ac, rctx);
      default:
        return '';
    }
  }

  /* b.band === 'header' (Việc 2 — hdr2col): bảng header 2 band không viền,
   * đúng hình học DOCX 42%/58% — chỉ bảng header band có band:header trong
   * blocks (tools/docx_to_blocks.py is_header_band_table). */
  function renderTableRows(b, ac, rctx) {
    var rows = b.rows || [];
    var body = rows.map(function (r) {
      var cells = (r.cells || []).map(function (c) {
        var attrs = '';
        if ((c.colspan || 1) > 1) attrs += ' colspan="' + c.colspan + '"';
        if ((c.rowspan || 1) > 1) attrs += ' rowspan="' + c.rowspan + '"';
        return '<td' + attrs + '>' + renderRuns(c.runs, ac, rctx) + '</td>';
      }).join('');
      return '<tr>' + cells + '</tr>';
    }).join('');
    var cls = 'btable' + (b.band === 'header' ? ' hdr-band' : '');
    return '<table class="' + cls + '"><tbody>' + body + '</tbody></table>';
  }

  /* Bảng lặp - CONTRACT:
   * - cols[].col là CHỈ SỐ CỘT GRID ZERO-BASED (khớp tools/docx_to_blocks.py).
   * - Tổng số cột vật lý N tính từ HEADER GRID: duyệt b.headerRows, cộng dồn
   *   occupancy qua colspan/rowspan giữa các hàng tiêu đề. KHÔNG suy từ
   *   max(cols[].col). Thiếu headerRows thì mới fallback theo cols.
   * - <th> giữ nguyên colspan/rowspan từ cell schema.
   * - Cột 0 không có tag VÀ tiêu đề tương ứng chứa "stt" (so normText trên
   *   text đã bỏ thẻ) -> td class="stt" tự đánh số i+1; cột không tag khác
   *   -> td rỗng đúng vị trí (field không trượt cột).
   * - type cho từng cols[] entry: 'text' mặc định | 'money' | 'percent' |
   *   'checkbox' (checked khi row[tag]==='X', data-key vẫn
   *   loop:<loop>:<idx>:<tag>) | 'radio' (name="loop:<loop>:<tag>",
   *   browser tự chọn-1-trong-cột) | 'readonly' | 'outputOnly' (ô rỗng).
   * - opts.gridMeta: map {loop: meta} cho bảng lặp - controller build theo
 *   mẫu (GRID_META toàn cục + overlay form-scoped FORM_GRID_META[docId],
 *   vd app.js gridMetaForDoc): override type THEO TAG và bổ
   *   sung tag cho cột vật lý chưa có trong cols[] (vd cột ngành chính của
   *   các mẫu cũ trước khi generator sinh đủ cols). Không truyền -> hành vi
   *   thuần theo blocks như bản cũ.
   * - Số hàng hiển thị = max(số dòng dữ liệu, blankRows; grid có meta và cho
   *   thêm dòng thì tối thiểu 1 dòng). Mỗi tr dữ liệu mang data-row-index +
   *   data-row-id (=_row_id ổn định của row trong store) + data-loop để
   *   controller chọn dòng; bảng bọc trong .btable-wrap để cuộn ngang.
   * - Nút action (.loop-btns): có gridMeta -> đầy đủ Thêm/Xóa/Lên/Xuống/
   *   Nhân bản/Xóa tất cả theo allowAdd/allowDelete/allowReorder, mỗi nút
   *   mang data-act + data-loop; không gridMeta -> giữ cụm legacy Thêm/Xóa. */

  /* Duyệt header grid: trả { nCols, title } với title[col] là text ô đầu tiên
   * phủ cột đó (đã chuẩn hoá khoảng trắng). */
  function loopHeaderGrid(b) {
    var headerIdx = b.headerRows || [];
    var occ = {};    // "row:col" -> true: ô bị chiếm bởi colspan/rowspan
    var title = {};
    var nCols = 0;
    (b.rows || []).forEach(function (row, ri) {
      if (headerIdx.indexOf(ri) < 0) return;
      var col = 0;
      (row.cells || []).forEach(function (c) {
        while (occ[ri + ':' + col]) col++; // nhảy qua ô span từ hàng trên
        var cs = Math.max(1, c.colspan | 0 || 1);
        var rs = Math.max(1, c.rowspan | 0 || 1);
        var txt = (c.runs || []).map(function (r) {
          return (r && r.text != null) ? String(r.text) : '';
        }).join(' ').replace(/\s+/g, ' ').trim();
        for (var dr = 0; dr < rs; dr++) {
          for (var dc = 0; dc < cs; dc++) {
            occ[(ri + dr) + ':' + (col + dc)] = true;
            if (!title[col + dc] && txt) title[col + dc] = txt;
          }
        }
        col += cs;
      });
      var w = 0;
      while (occ[ri + ':' + w]) w++;
      if (w > nCols) nCols = w;
    });
    return { nCols: nCols, title: title };
  }

  function renderLoop(b, ac, rctx) {
    rctx = rctx || { fieldMeta: null, docId: '', ids: {} };
    var rows = ac.storeRef.loops[b.loop] || [];
    var headerIdx = b.headerRows || [];
    var grid = loopHeaderGrid(b);
    var colTitle = grid.title;
    var nCols = grid.nCols;
    var gm = rctx.gridMeta ? (rctx.gridMeta[b.loop] || null) : null;

    var headHtml = (b.rows || [])
      .map(function (r, i) { return { r: r, i: i }; })
      .filter(function (x) { return headerIdx.indexOf(x.i) >= 0; })
      .map(function (x) {
        var cells = (x.r.cells || []).map(function (c) {
          var attrs = '';
          if ((c.colspan || 1) > 1) attrs += ' colspan="' + (c.colspan | 0) + '"';
          if ((c.rowspan || 1) > 1) attrs += ' rowspan="' + (c.rowspan | 0) + '"';
          return '<th' + attrs + '>' + renderRuns(c.runs, ac, rctx) + '</th>';
        }).join('');
        return '<tr>' + cells + '</tr>';
      }).join('');

    var tagByCol = {};
    var typeByCol = {};
    (b.cols || []).forEach(function (c) {
      tagByCol[c.col] = c.tag;
      typeByCol[c.col] = c.type || 'text';
      if (!nCols && c.col + 1 > nCols) nCols = c.col + 1; // fallback khi không có header
    });
    // gridMeta: override type theo tag đã map + bổ sung tag cho cột vật lý
    // chưa được blocks.cols map (chỉ khi cột đó nằm trong header grid).
    if (gm && gm.columns) {
      gm.columns.forEach(function (mc) {
        if (!mc || !mc.tag) return;
        var foundCol = -1;
        (b.cols || []).forEach(function (c) { if (c.tag === mc.tag) foundCol = c.col; });
        if (foundCol >= 0) {
          if (mc.type) typeByCol[foundCol] = mc.type;
        } else if (mc.col != null && mc.col >= 0 &&
                   !tagByCol[mc.col] && nCols && mc.col < nCols) {
          tagByCol[mc.col] = mc.tag;
          typeByCol[mc.col] = mc.type || 'text';
        }
      });
    }
    // cột 0 không tag + tiêu đề chứa "stt" -> dùng làm cột STT tự đánh số
    var hasStt = !tagByCol[0] &&
      normText(colTitle[0] || '').indexOf('stt') >= 0;

    // luôn còn ít nhất 1 dòng trống trên UI khi bảng cho thêm dòng
    var minUiRows = (gm && gm.allowAdd !== false) ? 1 : 0;
    var nRows = Math.max(rows.length, b.blankRows || 0, minUiRows);
    var body = '';
    for (var i = 0; i < nRows; i++) {
      var tds = '';
      for (var col = 0; col < nCols; col++) {
        var tag = tagByCol[col];
        if (!tag) {
          tds += (col === 0 && hasStt)
            ? '<td class="stt">' + (i + 1) + '</td>'
            : '<td></td>';
          continue;
        }
        var type = typeByCol[col];
        var key = 'loop:' + b.loop + ':' + i + ':' + tag;
        if (type === 'outputOnly') { tds += '<td></td>'; continue; }
        var fa = fieldAriaAttrs(key, rctx, [], -1,
          (b.label ? b.label + ' - ' : '') +
          (colTitle[col] || tag) + ' - dòng ' + (i + 1));
        var common = ' data-key="' + escapeHtml(key) +
          '" data-tag="' + escapeHtml(tag) +
          '" data-loop="' + escapeHtml(b.loop) +
          '" data-row="' + i + '"' + fa.attrs;
        if (type === 'checkbox') {
          tds += '<td><input type="checkbox" class="chk-box loop-chk"' + common +
            (String(ac.getVal(key)) === 'X' ? ' checked' : '') + '></td>';
          continue;
        }
        if (type === 'radio') {
          tds += '<td><input type="radio" class="chk-box loop-radio"' + common +
            ' name="loop:' + escapeHtml(b.loop) + ':' + escapeHtml(tag) +
            '" value="X"' + (String(ac.getVal(key)) === 'X' ? ' checked' : '') + '></td>';
          continue;
        }
        var cls = 'fld loop-fld' + fa.extraCls;
        if (type === 'money' || type === 'percent') cls += ' num';
        if (/^(ma_nganh|ten_nganh)$/.test(tag)) cls += ' vsic-fld';
        if (/^von_/.test(tag)) cls += ' num';
        tds += '<td><input type="text" class="' + cls + '" data-key="' + escapeHtml(key) +
          '" data-tag="' + escapeHtml(tag) + '" data-loop="' + escapeHtml(b.loop) +
          '" data-row="' + i + '"' + (type === 'readonly' ? ' readonly' : '') + fa.attrs +
          ' value="' + escapeHtml(ac.getVal(key)) + '"></td>';
      }
      var rowId = i < rows.length && rows[i] && rows[i]._row_id
        ? String(rows[i]._row_id) : '';
      body += '<tr data-row-index="' + i + '"' +
        (rowId ? ' data-row-id="' + escapeHtml(rowId) + '"' : '') +
        ' data-loop="' + escapeHtml(b.loop) + '">' + tds + '</tr>';
    }
    var btns;
    /* F-P3-A11Y-BUTTON: nút row-op chỉ có title= (screen reader không đọc) ->
     * thêm aria-label đúng ngữ nghĩa với title/chữ hiển thị. */
    if (gm) {
      btns = '<div class="loop-btns" data-loop="' + escapeHtml(b.loop) + '">' +
        (gm.allowAdd !== false
          ? '<button type="button" class="btn-row-add" data-act="add" data-loop="' +
            escapeHtml(b.loop) + '" title="Thêm dòng trống" aria-label="Thêm dòng">[+ Thêm dòng]</button>' +
            '<button type="button" class="btn-row-dup" data-act="dup" data-loop="' +
            escapeHtml(b.loop) + '" title="Nhân bản dòng đang chọn (bỏ field định danh)" aria-label="Nhân bản dòng đang chọn">[⧉ Nhân bản]</button>'
          : '') +
        (gm.allowDelete !== false
          ? '<button type="button" class="btn-row-del" data-act="del" data-loop="' +
            escapeHtml(b.loop) + '" title="Xóa dòng đang chọn (Ctrl+click để chọn nhiều)" aria-label="Xóa dòng đang chọn">[- Xóa dòng]</button>' +
            '<button type="button" class="btn-row-clear btn-danger-row" data-act="clear" data-loop="' +
            escapeHtml(b.loop) + '" title="Xóa dữ liệu TẤT CẢ các dòng" aria-label="Xóa tất cả các dòng">[× Xóa tất cả]</button>'
          : '') +
        (gm.allowReorder !== false
          ? '<button type="button" class="btn-row-up" data-act="up" data-loop="' +
            escapeHtml(b.loop) + '" title="Chuyển dòng đang chọn lên trên" aria-label="Chuyển dòng đang chọn lên trên">[↑ Lên]</button>' +
            '<button type="button" class="btn-row-down" data-act="down" data-loop="' +
            escapeHtml(b.loop) + '" title="Chuyển dòng đang chọn xuống dưới" aria-label="Chuyển dòng đang chọn xuống dưới">[↓ Xuống]</button>'
          : '') +
        '</div>';
    } else {
      btns = '<div class="loop-btns" data-loop="' + escapeHtml(b.loop) + '">' +
        '<button type="button" class="btn-row-add" data-act="add" data-loop="' + escapeHtml(b.loop) +
        '" title="Thêm dòng trống" aria-label="Thêm dòng">[+ Thêm dòng]</button>' +
        '<button type="button" class="btn-row-del" data-act="del" data-loop="' + escapeHtml(b.loop) +
        '" title="Xóa dòng đang chọn" aria-label="Xóa dòng đang chọn">[- Xóa dòng]</button>' +
        '</div>';
    }
    /* F-P3-A11Y-TABLE: role=grid + aria-colcount (số cột vật lý từ header grid)
     * + aria-rowcount (header + số dòng dữ liệu đang render). Controller
     * (app.js enhanceEditableGrids) cập nhật lại aria-rowcount sau thêm/xóa
     * dòng nên hai đường phải cùng chuẩn. */
    var nHeadRows = (b.rows || []).filter(function (r, i) {
      return headerIdx.indexOf(i) >= 0;
    }).length;
    return '<div class="loop-wrap"><div class="btable-wrap"><table class="btable loop-table" data-loop="' +
      escapeHtml(b.loop) + '" role="grid" aria-colcount="' + nCols +
      '" aria-rowcount="' + (nHeadRows + nRows) + '"><thead>' + headHtml +
      '</thead><tbody>' + body + '</tbody></table></div>' + btns + '</div>';
  }

  // ------------------------------------------------- PHASE 6: field-grid

  /* Các canonical key input xuất hiện trong MỘT block (để tìm anchor). */
  function blockInputKeys(b) {
    var keys = [];
    function walkRuns(runs) {
      (runs || []).forEach(function (r) {
        if (r && r.input && r.input.key && keys.indexOf(r.input.key) < 0) {
          keys.push(r.input.key);
        }
      });
    }
    if (!b) return keys;
    if (b.t === 'p') walkRuns(b.runs);
    else if (b.t === 'chk') { if (b.key) keys.push(b.key); }
    else if (b.t === 'table' || b.t === 'loop') {
      (b.rows || []).forEach(function (row) {
        (row.cells || []).forEach(function (c) { walkRuns(c.runs); });
      });
    }
    return keys;
  }

  /* CONTRACT uiLayout (app/data/ui_layouts/<id>.json - metadata UI THUẦN):
   * { id: '<PLI_Mxx>',
   *   grids: [{
   *     anchor|afterKey: '<canonical_key>',  // chèn ngay SAU block chứa ô
   *                                          // input có key này (không dùng
   *                                          // chỉ số block -> generator chạy
   *                                          // lại không vỡ layout)
   *     title: 'Vốn điều lệ',
   *     hideAnchor: true | ['key',...],      // ẩn THỊ GIÁC block gốc chứa key
   *                                          // bằng wrapper .dupe-anchor
   *                                          // (display:none qua CSS) - block
   *                                          // vẫn render, dữ liệu/export
   *                                          // không đổi; true = ẩn block
   *                                          // chứa chính anchor
   *     cols: [{key,type,label,w}]           // key = canonical key (đồng bộ
   *                                          // store tự chạy nhờ data-key);
   *                                          // type: text|money|readonly|
   *                                          // computed (computed/readonly:
   *                                          // attr readonly + nền xám nhạt
   *                                          // class .calc sẵn có)
   *   }] }
   * Grid là NHÓM UI BỔ SUNG: không xóa/thay đổi block gốc. Anchor không tìm
   * thấy trong blocks -> bỏ qua grid đó (fallback an toàn). */

  function fieldGridHtml(grid, ac, rctx) {
    var anchor = grid.anchor || grid.afterKey || '';
    var gid = sanitizeFieldId(anchor + '_' + (grid.title || 'grid'));
    var html = '<div class="field-grid" data-grid="' + escapeHtml(gid) +
      '" data-anchor="' + escapeHtml(anchor) + '">';
    if (grid.title) {
      html += '<div class="fg-title">' + escapeHtml(grid.title) + '</div>';
    }
    (grid.cols || []).forEach(function (c) {
      if (!c || !c.key) return;
      var type = c.type || 'text';
      var fid = nextFieldId(rctx, c.key);
      var label = c.label ||
        ((rctx.fieldMeta && rctx.fieldMeta[c.key] &&
          rctx.fieldMeta[c.key].label) || c.key);
      var cls = 'fld fg-fld';
      var attrs = '';
      if (type === 'money' || type === 'number') {
        attrs += ' inputmode="numeric"';
        cls += ' num';
      } else if (type === 'email') {
        attrs += ' inputmode="email"';
      }
      if (type === 'readonly' || type === 'computed') {
        attrs += ' readonly';
        cls += ' calc';
      } else if (AUTO_KEYS[c.key] === 'calc') {
        cls += ' calc'; // ô tự cộng (tổng vốn, ngày ký): nền xanh dương nhạt
      }
      html += '<label class="fg-label" for="' + escapeHtml(fid) + '">' +
        escapeHtml(label) + '</label>' +
        '<span class="fg-cell"><input type="text" id="' + escapeHtml(fid) +
        '" class="' + cls + '" data-key="' + escapeHtml(c.key) +
        '" style="width:' + (c.w ? (+c.w) + 'ch' : '100%') + '"' + attrs +
        ' aria-label="' + escapeHtml(label) +
        '" value="' + escapeHtml(ac.getVal(c.key)) + '"></span>';
    });
    return html + '</div>';
  }

  /* Chèn grid sau block anchor + bọc .dupe-anchor các block cần ẩn thị giác.
   * parts: [{b, html}] theo thứ tự blocks. Trả mảng html đã xử lý. */
  function applyUiLayout(parts, uiLayout, ac, rctx) {
    var grids = (uiLayout && uiLayout.grids) || [];
    var insertAt = {}; // index gốc -> [html grid]
    var wrapped = {};
    grids.forEach(function (g) {
      if (!g) return;
      var anchor = g.anchor || g.afterKey;
      if (!anchor) return;
      var at = -1;
      for (var i = 0; i < parts.length; i++) {
        if (blockInputKeys(parts[i].b).indexOf(anchor) >= 0) { at = i; break; }
      }
      if (at < 0) return; // anchor không tồn tại -> bỏ qua grid này
      (insertAt[at + 1] = insertAt[at + 1] || []).push(fieldGridHtml(g, ac, rctx));
      var hide = g.hideAnchor === true ? [anchor]
        : (Array.isArray(g.hideAnchor) ? g.hideAnchor : []);
      hide.forEach(function (hk) {
        if (wrapped[hk]) return;
        for (var j = 0; j < parts.length; j++) {
          if (parts[j].hidden) continue;
          if (blockInputKeys(parts[j].b).indexOf(hk) >= 0) {
            parts[j].html =
              '<div class="dupe-anchor">' + parts[j].html + '</div>';
            parts[j].hidden = true;
            wrapped[hk] = true;
            break; // chỉ ẩn block ĐẦU TIÊN chứa key
          }
        }
      });
    });
    var out = [];
    parts.forEach(function (p, i) {
      out.push(p.html);
      (insertAt[i] || []).forEach(function (h) { out.push(h); });
    });
    return out;
  }

  // ------------------------------------- P1.2: cond blocks + selector UI

  /* Block có điều kiện (converter gắn "cond": [flag,...] từ marker
   * {?flag}/{/flag} của template): chỉ render khi MỌI flag truthy trong
   * opts.flags. Không có cond -> luôn render (tương thích ngược 100%). */
  function condAllows(b, flags) {
    var c = b && b.cond;
    if (!c || !c.length) return true;
    flags = flags || {};
    for (var i = 0; i < c.length; i++) {
      if (!flags[c[i]]) return false;
    }
    return true;
  }

  /* HTML selector metadata hồ sơ (P1.2 Option D) - THUẦN, không biết form
   * ID. Radio cùng name theo key => browser tự ép chọn đúng một (không thể
   * chọn nhiều); chưa chọn = không radio nào checked. Giá trị KHÔNG ghi
   * data-field-id kiểu ô nhập; app.js xử lý change riêng qua .sel-radio.
   * Đây là điều khiển ứng dụng, KHÔNG phải nội dung in ra văn bản. */
  function selectorHtml(selMeta, ac) {
    if (!selMeta || !selMeta.key) return '';
    var cur = ac ? String(ac.getVal(selMeta.key) || '').trim() : '';
    var gid = 'selsel_' + sanitizeFieldId(selMeta.key);
    var html = '<div class="doc-selector" role="radiogroup" data-sel-key="' +
      escapeHtml(selMeta.key) + '" aria-labelledby="' + gid + '"' +
      (selMeta.required ? ' aria-required="true"' : '') + '>';
    html += '<div class="doc-sel-title" id="' + gid + '">' +
      escapeHtml(selMeta.label || '') +
      (selMeta.required ? ' <span class="req" title="Bắt buộc">*</span>' : '') +
      '</div>';
    (selMeta.options || []).forEach(function (o, i) {
      if (!o || !o.value) return;
      var rid = gid + '_opt' + i;
      html += '<label class="doc-sel-opt"><input type="radio" class="sel-radio"' +
        ' name="sel:' + escapeHtml(selMeta.key) + '"' +
        ' id="' + escapeHtml(rid) + '"' +
        ' data-sel-key="' + escapeHtml(selMeta.key) + '"' +
        ' data-key="' + escapeHtml(selMeta.key) + '"' +
        ' value="' + escapeHtml(o.value) + '"' +
        (cur === String(o.value) ? ' checked' : '') +
        '> ' + escapeHtml(o.label || o.value) + '</label>';
    });
    if (selMeta.help) {
      html += '<div class="doc-sel-help">' + escapeHtml(selMeta.help) + '</div>';
    }
    return html + '</div>';
  }

  // ---------------------- P2 R2 runtime wiring: dispatcher theo section.kind
  /* Nối 3 kind mới (fixed-matrix/nested-grid/output-table) vào pipeline render
   * MÀ KHÔNG viết lại component: markup được dựng TỪ output của module thuần
   * đã merge (fixed-matrix.js, nested-grid.js, output-table.js). Module nào
   * không nạp được -> trả '' và renderer GIỮ NGUYÊN blocks cũ (degrade an toàn,
   * tuyệt đối không ẩn nội dung pháp lý vì lỗi wiring).
   *
   * Contract section (kind + spec + anchor) đến từ FormDomain.sectionContractsOf
   * qua opts.sectionContracts; renderer GENERIC: không biết form ID. Kinds:
   *   editable-grid : NO-OP (đường renderLoop hiện hành giữ nguyên 100%).
   *   fixed-matrix  : bảng dòng pháp lý cố định, ô tổng readonly recompute.
   *   nested-grid   : header nhiều hàng rowspan/colspan vật lý + rows có _row_id.
   *   output-table  : delegate thẳng OutputTable.renderOutputTable (0 input).
   *
   * Block nguồn của các section vẫn là paragraph rời (generator lane B2 chưa
   * rebuild thành w:tbl). Section được dispatch sẽ được bọc .dupe-anchor
   * (display:none - cùng cơ chế uiLayout grids dùng sẵn, dữ liệu/không đụng)
   * để không còn hai bản hiển thị. */

  function p2TableModule(name) {
    var fileMap = { FixedMatrix: './fixed-matrix.js', NestedGrid: './nested-grid.js',
      OutputTable: './output-table.js' };
    var seen = null;
    if (typeof self !== 'undefined') seen = self;
    else if (typeof window !== 'undefined') seen = window;
    if (seen) {
      if (seen.P2Tables && seen.P2Tables[name]) return seen.P2Tables[name];
      if (name === 'OutputTable' && seen.OutputTable) return seen.OutputTable;
    }
    // Node harness (test không GUI): require cùng thư mục ui/.
    if (typeof require === 'function' && fileMap[name]) {
      try { return require(fileMap[name]); } catch (e) { /* chưa nối */ }
    }
    return null;
  }

  /* Text phẳng của một block (dùng để khớp anchor khai trong contract -
   * matching chỉ nằm ở renderer, metadata domain không biết gì về blocks). */
  function blockPlainText(b) {
    var out = [];
    function walkRuns(runs) {
      (runs || []).forEach(function (r) { out.push((r && r.text) || ''); });
    }
    if (!b || typeof b !== 'object') return '';
    if (b.t === 'p') walkRuns(b.runs);
    else if (b.t === 'chk') out.push(b.label || '');
    else if (b.t === 'table' || b.t === 'loop') {
      (b.rows || []).forEach(function (row) {
        (row.cells || []).forEach(function (c) { walkRuns(c && c.runs); });
      });
    }
    return out.join(' ');
  }

  /* Khóa so sánh anchor: normText + bỏ TOÀN BỘ khoảng trắng. Lý do: cùng một
   * dòng pháp lý trong blocks-v3 có thể tách thành nhiều run ("NGƯỜI NỘP\n" +
   * "(" + "Ký và ghi họ tên" + ")"), khoảng trắng/giãn dòng không mang ý nghĩa
   * khi khớp tiêu đề section. So theo chữ: chứa-substr một chiều. */
  function anchorKey(s) {
    return normText(s).replace(/\s+/g, '');
  }

  /* Khớp(anchor): role phải bằng khi khai, text so trên anchorKey chứa-substr.
   * end: thiếu cả endMatch lẫn endRole -> chạy tới hết mẫu (EOF). */
  function blockMatchesAnchor(block, anchorSpec, which) {
    var needle = which === 'end' ? anchorSpec.endMatch : anchorSpec.match;
    var wantRole = which === 'end' ? anchorSpec.endRole : anchorSpec.matchRole;
    if (needle == null && !wantRole) return true; // chỉ có ở vòng EOF
    var ok = true;
    if (wantRole && (!block || block.role !== wantRole)) ok = false;
    if (ok && needle != null &&
        anchorKey(blockPlainText(block)).indexOf(anchorKey(needle)) < 0) {
      ok = false;
    }
    return ok;
  }

  /* Vị trí vùng section trong danh sách parts: [start, end) - end EXCLUSIVE.
   * Không tìm thấy start -> null (không đụng blocks của section này). */
  function sectionSpanOfParts(parts, anchor) {
    var start = -1;
    for (var i = 0; i < parts.length; i++) {
      if (blockMatchesAnchor(parts[i].b, anchor, 'match')) { start = i; break; }
    }
    if (start < 0) return null;
    var end = parts.length;
    if (anchor.endMatch != null || anchor.endRole) {
      end = -1;
      for (var j = start + 1; j < parts.length; j++) {
        if (blockMatchesAnchor(parts[j].b, anchor, 'end')) { end = j; break; }
      }
      if (end < 0) return null; // boundary khai mà không thấy -> fail-closed
    } else {
      /* [Wave E fix] Không có boundary tường minh: vùng nguồn kết thúc ở
       * BẢNG CUỐI của section (block t="table"), không nuốt paragraph mồ côi
       * sau bảng — dòng mục kế khôi phục từ nguồn ở cuối tài liệu
       * (PLI_M03 mục 7 / PLI_M04 mục 8-9, batch 2) từng bị .dupe-anchor
       * ẩn vì span kéo tới EOF. */
      var lastTbl = -1;
      for (var j2 = start; j2 < parts.length; j2++) {
        if (parts[j2].b && parts[j2].b.t === 'table') lastTbl = j2;
      }
      if (lastTbl >= 0) end = lastTbl + 1;
    }
    return { start: start, end: end };
  }

  /* Số định dạng hiển thị ô readonly/computed (money -> dấu chấm ngăn nghìn
   * như formatVnd; percent/text giữ nguyên giá trị projection). */
  function componentNumberText(value, type) {
    if (value == null || String(value).trim() === '') return '';
    var typeKey = type === 'money' || type === 'percent' ? type : null;
    var n = parseNum(value);
    if (typeKey === 'money' && n != null) return formatVnd(n);
    if (typeKey === 'percent' && n != null) {
      var s = String(n);
      return s.indexOf('.') >= 0 ? s.replace(/\.?0+$/, '') : s;
    }
    return String(value);
  }

  /* ------------------------------- fixed-matrix */
  function fixedMatrixHtml(entry, ac, rctx) {
    var FM = p2TableModule('FixedMatrix');
    var spec = entry.spec || entry.contract || {};
    if (!FM || typeof FM.recompute !== 'function' ||
        !Array.isArray(spec.fixed_rows) || !spec.fixed_rows.length) return '';
    var cols = Array.isArray(spec.columns) ? spec.columns : [];
    var proj = FM.recompute(spec, ac.storeRef);
    var rowById = {};
    proj.rows.forEach(function (r) { rowById[String(r.id)] = r; });

    var head = '<tr>' + cols.map(function (c) {
      return '<th>' + escapeHtml(c.header || c.tag) + '</th>';
    }).join('') + '</tr>';

    function cellsFor(rowId, isTotalRow) {
      var cells = (rowById[String(rowId)] || {}).cells || {};
      return cols.map(function (c) {
        var tag = c.tag;
        if (c.inputType === 'readonly') {
          // Cột nhãn pháp lý: nội dung = label của dòng (isOutputColumn không
          // thuộc trường hợp này nên không trùng với cột computed).
          return '<td class="fm-label">' + escapeHtml(rowLabelById(spec, rowId)) +
            '</td>';
        }
        var vkey = spec.semantic_key + '.' + rowId + '.' + tag;
        if ((FM.isOutputColumn && FM.isOutputColumn(c)) || isTotalRow) {
          return '<td class="calc fm-out" data-computed-key="' + escapeHtml(vkey) +
            '">' + escapeHtml(componentNumberText(cells[tag], c.inputType)) + '</td>';
        }
        var fa = fieldAriaAttrs(vkey, rctx, [], -1,
          (rowLabelById(spec, rowId)) + ' - ' + (c.header || tag));
        var cls = 'fld comp-fld' + fa.extraCls +
          (c.inputType === 'money' || c.inputType === 'percent' ? ' num' : '');
        return '<td><input type="text" class="' + cls + '" data-key="' +
          escapeHtml(vkey) + '" data-tag="' + escapeHtml(tag) +
          '" data-fixed-row="' + escapeHtml(String(rowId)) + '" data-section-kind="fixed-matrix"' +
          fa.attrs + ' value="' + escapeHtml(ac.getVal(vkey)) + '"></td>';
      }).join('');
    }

    var body = (spec.fixed_rows || []).map(function (row, i) {
      // Dòng tổng: mọi ô là projection readonly (outputOnly), KHÔNG có input
      // -> không bao giờ tạo hai nguồn số liệu cho cùng một con số.
      var total = (spec.totals || []).some(function (t) {
          return String(t.id) === String(row.id); }) ||
        row.output_only === true || row.outputOnly === true;
      var sttCell = (spec.stt && spec.stt.mode === 'generated')
        ? '<td class="stt">' + (i + 1) + '</td>' : '';
      return '<tr data-row-id="' + escapeHtml(String(row.id)) +
        '" data-section-kind="fixed-matrix" data-semantic-key="' +
        escapeHtml(spec.semantic_key) + '"' +
        (total ? ' data-total-row="true"' : '') + '>' +
        sttCell + cellsFor(row.id, total) + '</tr>';
    }).join('');

    /* F-P3-A11Y-TABLE: bảng component cũng cần colcount/rowcount như loop-table
     * (fixed-matrix là bảng tĩnh: 1 hàng tiêu đề + mọi hàng khai). */
    return '<div class="loop-wrap"><div class="btable-wrap"><table ' +
      'class="btable component-table" data-component="fixed-matrix" ' +
      'data-semantic-key="' + escapeHtml(spec.semantic_key) + '" ' +
      'data-section-kind="fixed-matrix" role="grid" aria-colcount="' +
      (cols.length || 1) + '" aria-rowcount="' + ((spec.fixed_rows || []).length + 1) +
      '"><thead>' + head +
      '</thead><tbody>' + body + '</tbody></table></div></div>';
  }

  function rowLabelById(spec, id) {
    var hit = (spec.fixed_rows || []).filter(function (r) {
      return String(r.id) === String(id);
    })[0];
    return hit ? (hit.label == null ? '' : String(hit.label)) : '';
  }

  /* -------------------------------- nested-grid */
  function nestedGridHtml(entry, ac, rctx) {
    var NG = p2TableModule('NestedGrid');
    var spec = entry.spec || entry.contract || {};
    if (!NG || typeof NG.headerLayout !== 'function') return '';
    var layout = NG.headerLayout(spec);
    if (!layout.rows.length) return ''; // contract hỏng -> giữ blocks cũ

    var loop = spec.loop || spec.semantic_key;
    // KHÔNG tạo mảng rỗng trong store khi section chưa có dữ liệu: render phải
    // side-effect-free, draft/export không bị thêm key lạ.
    var storeRows = Array.isArray(ac.storeRef.loops[loop])
      ? ac.storeRef.loops[loop] : [];
    var normalized = NG.normalizeRows(spec, storeRows);
    var rows = normalized.errors.length ? storeRows.slice() : normalized.rows;
    if (normalized.errors.length && typeof console !== 'undefined' &&
        console.warn) {
      console.warn('[runtime-tables] nested-grid rows lenh contract (' +
        loop + '): ' + JSON.stringify(normalized.errors));
    }
    var minUiRows = entry.policy && entry.policy.allowAdd === false ? 0 : 1;
    var nRows = Math.max(storeRows.length, rows.length, minUiRows);

    var head = layout.rows.map(function (row) {
      return '<tr>' + row.map(function (cell) {
        var attrs = '';
        if (cell.rowspan > 1) attrs += ' rowspan="' + cell.rowspan + '"';
        if (cell.colspan > 1) attrs += ' colspan="' + cell.colspan + '"';
        return '<th' + attrs + '>' + escapeHtml(cell.text) + '</th>';
      }).join('') + '</tr>';
    }).join('');

    var colByIndex = layout.columns; // đã sort theo col_index vật lý
    var discTag = (spec.discriminator && spec.discriminator.tag) || null;
    var discValues = (spec.discriminator && spec.discriminator.values) || [];

    /* Ô vai trò dòng (discriminator): KHÔNG phải cột vật lý của bảng nên
     * nhúng vào ô STT để không làm lệch header/cột vật lý. Chỉ cho chọn giá
     * trị canonical của contract -> row_groups quyết định tập cột bắt buộc. */
    function discriminatorSelect(i) {
      if (!discTag) return '';
      var cur = String((storeRows[i] || {})[discTag] == null
        ? '' : (storeRows[i] || {})[discTag]);
      var opts = discValues.map(function (v) {
        var lab = entry.groupLabels ? (entry.groupLabels[v] || v) : String(v);
        return '<option value="' + escapeHtml(String(v)) + '"' +
          (cur === String(v) ? ' selected' : '') + '>' +
          escapeHtml(lab) + '</option>';
      }).join('');
      return '<select class="fld ng-discriminator"' +
        ' aria-label="Vai trò dòng ' + (i + 1) + '" data-key="loop:' +
        escapeHtml(loop) + ':' + i + ':' + escapeHtml(discTag) +
        '" data-tag="' + escapeHtml(discTag) + '" data-loop="' +
        escapeHtml(loop) + '" data-row="' + i + '"><option value=""' +
        (cur === '' ? ' selected' : '') + '>—</option>' + opts + '</select>';
    }

    var body = '';
    for (var i = 0; i < nRows; i++) {
      var tds = '';
      colByIndex.forEach(function (col) {
        var colType = col.type || 'text';
        if (colType === 'stt') {
          tds += '<td class="stt">' + (i + 1) + discriminatorSelect(i) + '</td>';
          return;
        }
        if (!col.tag) { tds += '<td></td>'; return; }
        if (colType === 'outputOnly') { tds += '<td></td>'; return; }
        var vkey = 'loop:' + loop + ':' + i + ':' + col.tag;
        var rawVal = storeRows[i] ? storeRows[i][col.tag] : undefined;
        var shown = rawVal == null ? '' : String(rawVal);
        var fa = fieldAriaAttrs(vkey, rctx, [], -1,
          'Dòng ' + (i + 1) + ' - ' + col.tag);
        var cls = 'fld loop-fld comp-fld' + fa.extraCls +
          (colType === 'money' || colType === 'percent' ? ' num' : '');
        tds += '<td><input type="text" class="' + cls + '" data-key="' +
          escapeHtml(vkey) + '" data-tag="' + escapeHtml(col.tag) +
          '" data-loop="' + escapeHtml(loop) + '" data-row="' + i + '"' +
          fa.attrs + ' value="' + escapeHtml(shown) + '"></td>';
      });
      var rid = storeRows[i] && storeRows[i]._row_id ?
        String(storeRows[i]._row_id) : '';
      body += '<tr data-row-index="' + i + '" data-loop="' + escapeHtml(loop) +
        '" data-section-kind="nested-grid"' +
        (rid ? ' data-row-id="' + escapeHtml(rid) + '"' : '') +
        '>' + tds + '</tr>';
    }

    var pol = entry.policy || {};
    /* F-P3-A11Y-BUTTON: cùng chuẩn aria-label với renderLoop. */
    var btns = '<div class="loop-btns" data-loop="' + escapeHtml(loop) +
      '" data-component="nested-grid">' +
      (pol.allowAdd !== false
        ? '<button type="button" class="btn-row-add" data-act="add" data-loop="' +
          escapeHtml(loop) + '" title="Thêm dòng trống" aria-label="Thêm dòng">[+ Thêm dòng]</button>'
        : '') +
      (pol.allowDelete !== false
        ? '<button type="button" class="btn-row-del" data-act="del" data-loop="' +
          escapeHtml(loop) + '" title="Xóa dòng đang chọn" aria-label="Xóa dòng đang chọn">[- Xóa dòng]</button>'
        : '') +
      (pol.allowReorder !== false
        ? '<button type="button" class="btn-row-up" data-act="up" data-loop="' +
          escapeHtml(loop) + '" title="Chuyển dòng đang chọn lên trên" aria-label="Chuyển dòng đang chọn lên trên">[↑ Lên]</button>' +
          '<button type="button" class="btn-row-down" data-act="down" data-loop="' +
          escapeHtml(loop) + '" title="Chuyển dòng đang chọn xuống dưới" aria-label="Chuyển dòng đang chọn xuống dưới">[↓ Xuống]</button>'
        : '') +
      '</div>';

    /* F-P3-A11Y-TABLE: nested-grid đã có role=grid + aria-colcount, bổ sung
     * aria-rowcount (header nhiều hàng vật lý + số dòng đang render). */
    return '<div class="loop-wrap"><div class="btable-wrap"><table ' +
      'class="btable loop-table component-table" data-component="nested-grid" ' +
      'data-loop="' + escapeHtml(loop) + '" data-semantic-key="' +
      escapeHtml(spec.semantic_key) + '" data-section-kind="nested-grid" ' +
      'role="grid" aria-colcount="' + colByIndex.length +
      '" aria-rowcount="' + (layout.rows.length + nRows) + '">' +
      '<thead>' + head + '</thead><tbody>' + body +
      '</tbody></table></div>' + btns + '</div>';
  }

  /* -------------------------------- output-table */
  function outputTableHtml(entry, ac, rctx) {
    var OT = p2TableModule('OutputTable');
    var spec = entry.spec || entry.contract || {};
    if (!OT || typeof OT.renderOutputTable !== 'function') return '';
    // Delegate NGUYÊN văn: module chịu trách nhiệm active_when/fail-closed.
    return OT.renderOutputTable(spec,
      { values: ac.storeRef.values, checks: ac.storeRef.checks }) || '';
  }

  /* Dispatcher: entry.kind -> builder tương ứng. Kind lạ/'editable-grid'
   * đều trả '' (giữ đường legacy), giúp metadata sai không nuốt pipeline. */
  function renderSectionComponentHtml(entry, ac, rctx) {
    if (!entry || !ac) return '';
    switch (entry.kind) {
      case 'fixed-matrix': return fixedMatrixHtml(entry, ac, rctx);
      case 'nested-grid': return nestedGridHtml(entry, ac, rctx);
      case 'output-table': return outputTableHtml(entry, ac, rctx);
      default: return '';
    }
  }

  /* Đẩy component vào pipeline: ẩn blocks nguồn của section (.dupe-anchor) rồi
   * CHÈN 1 phần tử giả {b:null, html} ngay sau block cuối của vùng (splice nên
   * cả EOF cũng đúng; các contract sau khớp trên mảng đã cập nhật). */
  function applySectionComponents(parts, contracts, ac, rctx) {
    (contracts || []).forEach(function (entry) {
      if (!entry || !entry.anchor) return;
      var span = sectionSpanOfParts(parts, entry.anchor);
      if (!span) return;
      var html = renderSectionComponentHtml(entry, ac, rctx);
      if (!html) return; // degrade: module thiếu/contract hỏng -> giữ blocks cũ
      for (var i = span.start; i < span.end; i++) {
        if (!parts[i]) break;
        if (parts[i].hidden) continue;
        /* [Fix ISS-5 re-shoot P2] anchor của fixed-matrix CHÍNH LÀ heading
         * đánh số của section ("7. Nguồn vốn điều lệ:") mà builder không phát
         * lại — giữ block đầu hiển thị, chỉ ẩn các block nguồn còn lại. */
        if (i === span.start && entry.kind === 'fixed-matrix') continue;
        parts[i].html = '<div class="dupe-anchor">' + parts[i].html + '</div>';
        parts[i].hidden = true;
      }
      parts.splice(span.end, 0, { b: null, html: html,
        componentKind: entry.kind, componentKey: entry.semanticKey });
    });
  }

  /* Render toàn bộ một mẫu biểu thành HTML string.
   * opts tuỳ chọn: { fieldMeta: {key: meta}, gridMeta: {loop: meta},
   * uiLayout: {grids:[...]}, docId, flags: {flag: bool} - điều kiện cond
   * blocks P1.2, selectorHtml: chuỗi HTML chèn trước tờ khai,
   * sectionContracts: [entry] metadata SECTION theo kind (P2 R2) - không
   * truyền / truyền rỗng -> tương thích ngược hoàn toàn với bản cũ. */
  function renderBlocks(doc, store, opts) {
    var ac = makeAccessors(store || newStore());
    var rctx = {
      fieldMeta: (opts && opts.fieldMeta) || null,
      gridMeta: (opts && opts.gridMeta) || null,
      docId: (opts && opts.docId) || (doc && doc.id) || '',
      ids: {},
      siSkipped: []
    };
    var parts = (doc.blocks || [])
      .filter(function (b) { return condAllows(b, opts && opts.flags); })
      .map(function (b) { return { b: b, html: renderBlock(b, ac, rctx) }; });
    // P2 R2 dispatcher theo section.kind (editable-grid giữ đường cũ).
    if (opts && Array.isArray(opts.sectionContracts) &&
        opts.sectionContracts.length) {
      applySectionComponents(parts, opts.sectionContracts, ac, rctx);
    }
    /* Audit L2: marker kỹ thuật bị ẩn -> log ĐÚNG 1 LẦN/form (không render
     * vào DOM; giữ evidence cho detector/gate LAYOUT_DONE). */
    if (rctx.siSkipped.length && typeof console !== 'undefined' &&
        typeof console.debug === 'function') {
      console.debug('[layout-l2] an ' + rctx.siSkipped.length +
        ' block role=source-indicator khoi DOM (' +
        (rctx.docId || '?') + ')');
    }
    var seq = (opts && opts.uiLayout)
      ? applyUiLayout(parts, opts.uiLayout, ac, rctx)
      : parts.map(function (p) { return p.html; });
    var pre = (opts && opts.selectorHtml) || '';
    return pre + seq.join('\n');
  }

  /* HTML cho tablist đáy (controller gắn sự kiện qua [data-doc-id]). */
  function buildTabsHtml(docs) {
    return (docs || []).map(function (d) {
      return '<button type="button" role="tab" id="tab_' + escapeHtml(d.id) +
        '" data-doc-id="' + escapeHtml(d.id) +
        '" aria-selected="false" aria-controls="pages" tabindex="-1">' +
        escapeHtml(d.ten_mau || d.id) + '</button>';
    }).join('');
  }

  // ------------------------------------------------------------ auto tính

  /* Key tự điền/tự cộng: calc = nền xanh dương #dce6f1 (tổng vốn, ngày ký). */
  var AUTO_KEYS = {
    'von_dieu_le': 'calc',
    'von_kinh_doanh': 'calc',
    'ngay_ky_vb': 'calc',
    'thang_ky_vb': 'calc',
    'nam_ky_vb': 'calc'
  };

  /* Cộng dồn tag nguồn trên MỌI bảng lặp -> ô đích.
   * von_dong_gop  -> von_dieu_le ; von_kinh_doanh -> von_kinh_doanh */
  var TOTAL_RULES = [
    { srcTag: 'von_dong_gop', targetKey: 'von_dieu_le' },
    { srcTag: 'von_kinh_doanh', targetKey: 'von_kinh_doanh' }
  ];

  function sumLoopTag(store, srcTag) {
    var sum = 0;
    Object.keys(store.loops || {}).forEach(function (name) {
      (store.loops[name] || []).forEach(function (row) {
        var n = parseNum(row[srcTag]);
        if (n != null) sum += n;
      });
    });
    return sum;
  }

  /* Trả về map {targetKey: chuỗi số định dạng} cần điền.
   * autoSum=true  : luôn ghi đè (không có số nào -> '0').
   * autoSum=false : chỉ điền khi ô đích đang trống và tổng > 0. */
  function calcTotals(store, autoSum) {
    var out = {};
    TOTAL_RULES.forEach(function (rule) {
      var sum = sumLoopTag(store, rule.srcTag);
      var cur = store.values[rule.targetKey];
      if (autoSum) {
        out[rule.targetKey] = formatVnd(sum);
      } else if ((cur == null || String(cur).trim() === '') && sum > 0) {
        out[rule.targetKey] = formatVnd(sum);
      }
    });
    return out;
  }

  /* Bản sao store đã áp mọi tự tính:
   * (c) ngay/thang/nam_ky_vb = hôm nay nếu trống; (a) tổng vốn theo autoSum. */
  function applyAutoFills(store, autoSum, now) {
    var s = cloneStore(store);
    var t = now instanceof Date ? now : new Date();
    if (!String(s.values['ngay_ky_vb'] || '').trim()) s.values['ngay_ky_vb'] = pad2(t.getDate());
    if (!String(s.values['thang_ky_vb'] || '').trim()) s.values['thang_ky_vb'] = pad2(t.getMonth() + 1);
    if (!String(s.values['nam_ky_vb'] || '').trim()) s.values['nam_ky_vb'] = String(t.getFullYear());
    var totals = calcTotals(s, autoSum);
    Object.keys(totals).forEach(function (k) { s.values[k] = totals[k]; });
    return s;
  }

  // ----------------------------------------------------------------- VSIC

  /* Tìm mã ngành: khớp KHÔNG DẤU trên ten hoặc tiền tố trên ma.
   * Ưu tiên: khớp ma chính xác > tên bắt đầu bằng > tên chứa; cùng nhóm thì
   * cap 4 trước (chi tiết hơn), rồi tới cap 3, cap 2; cuối cùng sort theo ma. */
  function searchVsic(list, query, limit) {
    limit = limit || 12;
    var q = normText(query).trim();
    if (!q) return [];
    var hits = [];
    (list || []).forEach(function (x) {
      var nm = normText(x.ten);
      var score;
      if (x.ma === q || x.ma.indexOf(q) === 0) score = 0;
      else if (nm.indexOf(q) === 0) score = 1;
      else if (nm.indexOf(q) >= 0) score = 2;
      else return;
      hits.push({ item: x, score: score, capRank: x.cap === 4 ? 0 : (x.cap === 3 ? 1 : 2) });
    });
    hits.sort(function (a, b) {
      return a.score - b.score || a.capRank - b.capRank ||
        String(a.item.ma).localeCompare(String(b.item.ma));
    });
    return hits.slice(0, limit).map(function (h) { return h.item; });
  }

  function isValidMaNganh(list, val) {
    var v = String(val == null ? '' : val).trim();
    if (!v) return true; // rỗng không tô đỏ
    return (list || []).some(function (x) { return String(x.ma) === v; });
  }

  // --------------------------------------------------------------- exports

  root.escapeHtml = escapeHtml;
  root.normText = normText;
  root.formatVnd = formatVnd;
  root.parseNum = parseNum;
  root.newStore = newStore;
  root.cloneStore = cloneStore;
  root.makeAccessors = makeAccessors;
  root.renderBlocks = renderBlocks;
  root.condAllows = condAllows;
  root.selectorHtml = selectorHtml;
  root.buildTabsHtml = buildTabsHtml;
  root.sanitizeFieldId = sanitizeFieldId;
  root.AUTO_KEYS = AUTO_KEYS;
  root.TOTAL_RULES = TOTAL_RULES;
  root.calcTotals = calcTotals;
  root.applyAutoFills = applyAutoFills;
  root.searchVsic = searchVsic;
  root.isValidMaNganh = isValidMaNganh;
  /* L2 layout (blocks-v3) */
  root.FORMAT_ALLOWLIST = FORMAT_ALLOWLIST;
  root.ROLES_L2 = ROLES_L2;
  root.textToHtml = textToHtml;
  root.formatStyleAttr = formatStyleAttr;
  root.roleClassOf = roleClassOf;
  root.bindFootnoteRefs = enhanceSectionDom;
  root.enhanceSectionDom = enhanceSectionDom;
  root.enhanceChkLabels = enhanceChkLabels;

  /* P2 R2 runtime wiring: dispatcher theo section.kind (3 module platform chỉ
   * được require/gọi, không sửa). Renderer GENERIC - contracts đến qua opts. */
  root.renderSectionComponentHtml = renderSectionComponentHtml;
  root.applySectionComponents = applySectionComponents;
  root.sectionSpanOfParts = sectionSpanOfParts;

})(typeof module !== 'undefined' && module.exports ? module.exports : (window.Render = window.Render || {}));
