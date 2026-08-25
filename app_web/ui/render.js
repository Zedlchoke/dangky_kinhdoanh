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
    var cn = 'rn' + (run.b ? ' rn-b' : '') + (run.i ? ' rn-i' : '') + (run.u ? ' rn-u' : '');
    return '<span class="' + cn + '">' + escapeHtml(run.text) + '</span>';
  }

  function renderRuns(runs, ac, rctx) {
    return (runs || []).map(function (r, i) {
      return renderRun(r, ac, rctx, runs, i);
    }).join('');
  }

  // ----------------------------------------------------------- render blocks

  function renderBlock(b, ac, rctx) {
    switch (b.t) {
      case 'p':
        return '<p class="bp bp-' + (b.align || 'left') + '">' + renderRuns(b.runs, ac, rctx) + '</p>';
      case 'chk':
        return '<label class="bchk"><input type="checkbox" class="chk-box" data-key="' +
          escapeHtml(b.key) + '"' + (ac.getChk(b.key) ? ' checked' : '') +
          '><span>' + escapeHtml(b.label || '') + '</span></label>';
      case 'table':
        return renderTableRows(b.rows || [], ac, rctx);
      case 'loop':
        return renderLoop(b, ac, rctx);
      default:
        return '';
    }
  }

  function renderTableRows(rows, ac, rctx) {
    var body = rows.map(function (r) {
      var cells = (r.cells || []).map(function (c) {
        var attrs = '';
        if ((c.colspan || 1) > 1) attrs += ' colspan="' + c.colspan + '"';
        if ((c.rowspan || 1) > 1) attrs += ' rowspan="' + c.rowspan + '"';
        return '<td' + attrs + '>' + renderRuns(c.runs, ac, rctx) + '</td>';
      }).join('');
      return '<tr>' + cells + '</tr>';
    }).join('');
    return '<table class="btable"><tbody>' + body + '</tbody></table>';
  }

  /* Bảng lặp: các hàng có chỉ số nằm trong headerRows là hàng tiêu đề tĩnh,
   * sau đó sinh hàng dữ liệu động theo cols (cột 1 không có tag nào phủ ->
   * tự đánh số STT), số hàng hiển thị = max(số dòng dữ liệu, blankRows).
   * Mỗi tr dữ liệu mang data-row-index + data-loop để controller chọn dòng;
   * bảng bọc trong .btable-wrap để cuộn ngang màn hình nhỏ. */
  function renderLoop(b, ac, rctx) {
    rctx = rctx || { fieldMeta: null, docId: '', ids: {} };
    var rows = ac.storeRef.loops[b.loop] || [];
    var headerIdx = b.headerRows || [];
    var allRows = b.rows || [];
    var colTitle = {};
    allRows
      .map(function (r, i) { return { r: r, i: i }; })
      .filter(function (x) { return headerIdx.indexOf(x.i) >= 0; })
      .forEach(function (x) {
        (x.r.cells || []).forEach(function (c, ci) {
          var no = ci + 1; // tiêu đề theo vị trí cột hiển thị
          var txt = (c.runs || []).map(function (r) {
            return (r && r.text != null) ? String(r.text) : '';
          }).join(' ').replace(/\s+/g, ' ').trim();
          if (!colTitle[no] && txt) colTitle[no] = txt;
        });
      });
    var headHtml = allRows
      .map(function (r, i) { return { r: r, i: i }; })
      .filter(function (x) { return headerIdx.indexOf(x.i) >= 0; })
      .map(function (x) {
        var cells = (x.r.cells || []).map(function (c) {
          return '<th>' + renderRuns(c.runs, ac, rctx) + '</th>';
        }).join('');
        return '<tr>' + cells + '</tr>';
      }).join('');

    var colByNo = {};
    var maxCol = 0;
    (b.cols || []).forEach(function (c) {
      colByNo[c.col] = c.tag;
      if (c.col > maxCol) maxCol = c.col;
    });
    // cột 1 không có tag nào phủ -> dùng làm cột STT tự đánh số
    var hasStt = !colByNo[1];
    var nCols = hasStt ? Math.max(maxCol + 1, 2) : Math.max(maxCol, 1);

    var nRows = Math.max(rows.length, b.blankRows || 0);
    var body = '';
    for (var i = 0; i < nRows; i++) {
      var tds = '';
      for (var col = 1; col <= nCols; col++) {
        if (col === 1 && hasStt) {
          tds += '<td class="stt">' + (i + 1) + '</td>';
          continue;
        }
        var tag = colByNo[col];
        if (!tag) { tds += '<td></td>'; continue; }
        var key = 'loop:' + b.loop + ':' + i + ':' + tag;
        var fa = fieldAriaAttrs(key, rctx, [], -1,
          (b.label ? b.label + ' - ' : '') +
          (colTitle[col] || tag) + ' - dòng ' + (i + 1));
        var cls = 'fld loop-fld' + fa.extraCls;
        if (/^(ma_nganh|ten_nganh)$/.test(tag)) cls += ' vsic-fld';
        if (/^von_/.test(tag)) cls += ' num';
        tds += '<td><input type="text" class="' + cls + '" data-key="' + escapeHtml(key) +
          '" data-tag="' + escapeHtml(tag) + '" data-loop="' + escapeHtml(b.loop) +
          '" data-row="' + i + '"' + fa.attrs +
          ' value="' + escapeHtml(ac.getVal(key)) + '"></td>';
      }
      body += '<tr data-row-index="' + i + '" data-loop="' + escapeHtml(b.loop) + '">' + tds + '</tr>';
    }
    var btns = '<div class="loop-btns" data-loop="' + escapeHtml(b.loop) + '">' +
      '<button type="button" class="btn-row-add" data-loop="' + escapeHtml(b.loop) +
      '">[+ Thêm dòng]</button>' +
      '<button type="button" class="btn-row-del" data-loop="' + escapeHtml(b.loop) +
      '">[- Xóa dòng]</button>' +
      '</div>';
    return '<div class="loop-wrap"><div class="btable-wrap"><table class="btable loop-table" data-loop="' +
      escapeHtml(b.loop) + '"><thead>' + headHtml +
      '</thead><tbody>' + body + '</tbody></table></div>' + btns + '</div>';
  }

  /* Render toàn bộ một mẫu biểu thành HTML string.
   * opts tuỳ chọn: { fieldMeta: {key: meta}, docId } — không truyền thì
   * tương thích ngược hoàn toàn với bản cũ. */
  function renderBlocks(doc, store, opts) {
    var ac = makeAccessors(store || newStore());
    var rctx = {
      fieldMeta: (opts && opts.fieldMeta) || null,
      docId: (opts && opts.docId) || (doc && doc.id) || '',
      ids: {}
    };
    return (doc.blocks || []).map(function (b) { return renderBlock(b, ac, rctx); }).join('\n');
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
  root.buildTabsHtml = buildTabsHtml;
  root.sanitizeFieldId = sanitizeFieldId;
  root.AUTO_KEYS = AUTO_KEYS;
  root.TOTAL_RULES = TOTAL_RULES;
  root.calcTotals = calcTotals;
  root.applyAutoFills = applyAutoFills;
  root.searchVsic = searchVsic;
  root.isValidMaNganh = isValidMaNganh;

})(typeof module !== 'undefined' && module.exports ? module.exports : (window.Render = window.Render || {}));
