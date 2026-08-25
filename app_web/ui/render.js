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
   * - opts.gridMeta (từ FormDomain.GRID_META): override type THEO TAG và bổ
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
    if (gm) {
      btns = '<div class="loop-btns" data-loop="' + escapeHtml(b.loop) + '">' +
        (gm.allowAdd !== false
          ? '<button type="button" class="btn-row-add" data-act="add" data-loop="' +
            escapeHtml(b.loop) + '" title="Thêm dòng trống">[+ Thêm dòng]</button>' +
            '<button type="button" class="btn-row-dup" data-act="dup" data-loop="' +
            escapeHtml(b.loop) + '" title="Nhân bản dòng đang chọn (bỏ field định danh)">[⧉ Nhân bản]</button>'
          : '') +
        (gm.allowDelete !== false
          ? '<button type="button" class="btn-row-del" data-act="del" data-loop="' +
            escapeHtml(b.loop) + '" title="Xóa dòng đang chọn (Ctrl+click để chọn nhiều)">[- Xóa dòng]</button>' +
            '<button type="button" class="btn-row-clear btn-danger-row" data-act="clear" data-loop="' +
            escapeHtml(b.loop) + '" title="Xóa dữ liệu TẤT CẢ các dòng">[× Xóa tất cả]</button>'
          : '') +
        (gm.allowReorder !== false
          ? '<button type="button" class="btn-row-up" data-act="up" data-loop="' +
            escapeHtml(b.loop) + '" title="Chuyển dòng đang chọn lên trên">[↑ Lên]</button>' +
            '<button type="button" class="btn-row-down" data-act="down" data-loop="' +
            escapeHtml(b.loop) + '" title="Chuyển dòng đang chọn xuống dưới">[↓ Xuống]</button>'
          : '') +
        '</div>';
    } else {
      btns = '<div class="loop-btns" data-loop="' + escapeHtml(b.loop) + '">' +
        '<button type="button" class="btn-row-add" data-act="add" data-loop="' + escapeHtml(b.loop) +
        '">[+ Thêm dòng]</button>' +
        '<button type="button" class="btn-row-del" data-act="del" data-loop="' + escapeHtml(b.loop) +
        '">[- Xóa dòng]</button>' +
        '</div>';
    }
    return '<div class="loop-wrap"><div class="btable-wrap"><table class="btable loop-table" data-loop="' +
      escapeHtml(b.loop) + '"><thead>' + headHtml +
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

  /* Render toàn bộ một mẫu biểu thành HTML string.
   * opts tuỳ chọn: { fieldMeta: {key: meta}, gridMeta: {loop: meta},
   * uiLayout: {grids:[...]}, docId }
   * — không truyền thì tương thích ngược hoàn toàn với bản cũ. */
  function renderBlocks(doc, store, opts) {
    var ac = makeAccessors(store || newStore());
    var rctx = {
      fieldMeta: (opts && opts.fieldMeta) || null,
      gridMeta: (opts && opts.gridMeta) || null,
      docId: (opts && opts.docId) || (doc && doc.id) || '',
      ids: {}
    };
    var parts = (doc.blocks || []).map(function (b) {
      return { b: b, html: renderBlock(b, ac, rctx) };
    });
    var seq = (opts && opts.uiLayout)
      ? applyUiLayout(parts, opts.uiLayout, ac, rctx)
      : parts.map(function (p) { return p.html; });
    return seq.join('\n');
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
