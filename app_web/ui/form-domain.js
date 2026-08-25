/* form-domain.js - module THUẦN cho field metadata + validation (không DOM).
 * Dùng chung app.js (webview) và test (node require). UMD như render.js.
 * Contract: docs/htkk-ui-contract.md
 *  - getFieldMeta(key) -> meta|null
 *  - parseMoney / formatMoney : tiền hiển thị '1.000.000', tính trên số thật
 *  - validateField / validateDocument / validateDossier -> error[]
 *    error = { key, docId, code, message, severity: 'blocking'|'warning' }
 *  - collectKeys(blocks), migrateDraft(draft) (v1 -> v2)
 */
(function (root) {
  'use strict';

  // ------------------------------------------------------------- money utils

  /* '1.000.000' | '1000000' | '50,5' -> số | null. Rỗng/rác không có số -> null. */
  function parseMoney(v) {
    if (v == null) return null;
    var s = String(v).trim();
    if (!s) return null;
    var neg = /^\(.*\)$/.test(s);
    var clean = s.replace(/[^\d.,]/g, '');
    if (!clean || !/\d/.test(clean)) return null;
    var dot = (clean.match(/\./g) || []).length;
    var comma = (clean.match(/,/g) || []).length;
    if (dot > 1 || comma > 1) {
      clean = clean.replace(/[.,]/g, '');            // 1.234.567 hoặc 1,234,567
    } else if (dot === 1 && comma === 1) {
      clean = clean.indexOf('.') < clean.indexOf(',')
        ? clean.replace(/\./g, '').replace(',', '.') // 1.234,56 kiểu VN
        : clean.replace(/,/g, '');                   // 1,234.56 kiểu EN
    } else {
      var sepPos = Math.max(clean.lastIndexOf('.'), clean.lastIndexOf(','));
      var decimals = clean.length - sepPos - 1;
      if (sepPos > -1 && decimals === 3 && /^\d{1,3}([.,]\d{3})+$/.test(clean)) {
        clean = clean.replace(/[.,]/g, '');          // nhóm nghìn
      } else if (sepPos > -1 && decimals > 0 && decimals <= 2) {
        clean = clean.replace(',', '.');             // thập phân ngắn
      } else {
        clean = clean.replace(/[.,]/g, '');
      }
    }
    var n = parseFloat(clean);
    if (isNaN(n)) return null;
    return neg ? -n : n;
  }

  function formatMoney(n) {
    n = Math.round(Number(n));
    if (isNaN(n)) return '';
    var neg = n < 0;
    var s = String(Math.abs(n));
    var out = '';
    while (s.length > 3) {
      out = '.' + s.slice(-3) + out;
      s = s.slice(0, -3);
    }
    return (neg ? '-' : '') + s + out;
  }

  // ------------------------------------------------------------- field metadata

  /* Metadata theo canonical key. Key ngoài danh sách này vẫn render/validation
   * cơ bản (text tuỳ chọn) - tương thích ngược, KHÔNG đổi key cũ. */
  var FIELD_META = {
    'dn.ten_tieng_viet': {
      key: 'dn.ten_tieng_viet',
      label: 'Tên công ty bằng tiếng Việt',
      type: 'text', required: true,
      help: 'Ghi bằng chữ in hoa; bắt buộc để xuất hồ sơ.'
    },
    'dn.ten_nuoc_ngoai': { key: 'dn.ten_nuoc_ngoai', label: 'Tên công ty bằng tiếng nước ngoài', type: 'text' },
    'dn.ten_viet_tat':   { key: 'dn.ten_viet_tat',   label: 'Tên công ty viết tắt', type: 'text' },
    'von_dieu_le':       { key: 'von_dieu_le', label: 'Vốn điều lệ (VNĐ)', type: 'money', inputMode: 'numeric',
                           help: 'Nhập số dạng 1.000.000; tự cộng từ bảng lặp khi bật Tự cộng.' },
    'von_kinh_doanh':    { key: 'von_kinh_doanh', label: 'Vốn kinh doanh (VNĐ)', type: 'money', inputMode: 'numeric' },
    'chu_hkd.ho_ten':    { key: 'chu_hkd.ho_ten', label: 'Họ tên người đăng ký/chủ sở hữu', type: 'text' },
    'ndd.ho_ten':        { key: 'ndd.ho_ten', label: 'Họ tên người đại diện theo pháp luật', type: 'text' },
    'gd.ho_ten':         { key: 'gd.ho_ten', label: 'Họ tên Giám đốc/Tổng giám đốc', type: 'text' },
    'kt.ho_ten':         { key: 'kt.ho_ten', label: 'Họ tên Kế toán trưởng', type: 'text' },
    'chu_hkd.so_cccd':   { key: 'chu_hkd.so_cccd', label: 'Số định danh cá nhân/giấy tờ pháp lý', type: 'cccd' },
    'ndd.so_cccd':       { key: 'ndd.so_cccd', label: 'Số định danh cá nhân người đại diện', type: 'cccd' },
    'ndd.email':         { key: 'ndd.email', label: 'Thư điện tử người đại diện', type: 'email', inputMode: 'email' },
    'email_tru_so':      { key: 'email_tru_so', label: 'Thư điện tử trụ sở chính', type: 'email', inputMode: 'email' },
    'dn.ma_so_dn':       { key: 'dn.ma_so_dn', label: 'Mã số doanh nghiệp/Mã số thuế chủ sở hữu', type: 'mst' },
    'dn_goc.ma_so_dn':   { key: 'dn_goc.ma_so_dn', label: 'Mã số doanh nghiệp bị chia/tách/hợp nhất', type: 'mst' },
    'hkd_cd.ma_so_thue': { key: 'hkd_cd.ma_so_thue', label: 'Mã số thuế hộ kinh doanh chuyển đổi', type: 'mst' },
    'csbt.ma_so_thue':   { key: 'csbt.ma_so_thue', label: 'Mã số thuế cơ sở bảo trợ xã hội/quỹ', type: 'mst' },
    'so_lao_dong':       { key: 'so_lao_dong', label: 'Tổng số lao động (dự kiến)', type: 'number', inputMode: 'numeric' }
  };

  /* Rule bảng lặp. minRowsFilled: số dòng CÓ DỮ LIỆU tối thiểu (0 = bỏ qua);
   * moneyTags phải là tiền hợp lệ; percentTags tổng ~100 (warning);
   * vsicTags phải có trong danh mục VSIC khi ctx.vsicList được cung cấp. */
  var LOOP_META = {
    ds_thanh_vien: {
      label: 'Danh sách thành viên', minRowsFilled: 2,
      moneyTags: ['von_dong_gop'], percentTags: ['ty_le_von'], vsicTags: []
    },
    ds_nganh_kinh_doanh: {
      label: 'Danh sách ngành nghề kinh doanh', minRowsFilled: 0,
      moneyTags: [], percentTags: [], vsicTags: ['ma_nganh']
    }
  };

  function getFieldMeta(key) {
    return FIELD_META[key] || null;
  }

  function getLoopMeta(name) {
    return LOOP_META[name] || null;
  }

  // ------------------------------------------------------------- block walker

  /* Đi qua blocks schema (JSON thuần): keys thường unique giữ thứ tự và
   * loops: { ten_loop: [tag,...] }. Không phụ thuộc DOM. */
  function collectKeys(blocks) {
    var seen = {};
    var keys = [];
    var loops = {};
    function addKey(k) {
      if (k && !seen[k]) { seen[k] = true; keys.push(k); }
    }
    function walkRuns(runs) {
      (runs || []).forEach(function (r) { if (r && r.input) addKey(r.input.key); });
    }
    (blocks || []).forEach(function (b) {
      if (!b) return;
      if (b.t === 'p') walkRuns(b.runs);
      else if (b.t === 'chk') addKey(b.key);
      else if (b.t === 'table') {
        (b.rows || []).forEach(function (row) {
          (row.cells || []).forEach(function (c) { walkRuns(c.runs); });
        });
      } else if (b.t === 'loop') {
        var tags = loops[b.loop] || (loops[b.loop] = []);
        (b.cols || []).forEach(function (c) {
          if (c.tag && tags.indexOf(c.tag) < 0) tags.push(c.tag);
        });
        (b.rows || []).forEach(function (row) {
          (row.cells || []).forEach(function (c) { walkRuns(c.runs); });
        });
      }
    });
    return { keys: keys, loops: loops };
  }

  // ---------------------------------------------------------------- validators

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function stripSep(s) { return String(s).replace(/[\s.\-]/g, ''); }

  /* Validate MỘT giá trị theo meta. meta thiếu -> text tuỳ chọn cơ bản. */
  function validateField(meta, value, ctx) {
    ctx = ctx || {};
    var m = meta || { type: 'text', required: false };
    var v = value == null ? '' : String(value).trim();
    function err(code, message, severity) {
      return [{
        key: m.key,
        docId: ctx.docId != null ? ctx.docId : null,
        code: code,
        message: message,
        severity: severity || 'blocking'
      }];
    }
    if (!v) {
      return m.required
        ? err('REQUIRED', 'Thiếu thông tin bắt buộc: ' + (m.label || m.key))
        : [];
    }
    switch (m.type) {
      case 'email':
        if (!EMAIL_RE.test(v)) return err('EMAIL', 'Email không đúng định dạng: ' + v);
        break;
      case 'cccd': {
        var d = stripSep(v);
        if (!/^(\d{9}|\d{12})$/.test(d))
          return err('CCCD', 'Số định danh/giấy tờ pháp lý phải 9 hoặc 12 số: ' + v);
        break;
      }
      case 'mst': {
        var t = String(v).replace(/[\s.]/g, ''); // giữ '-' cho cú pháp 10-3
        if (!/^\d{10}(-\d{3})?$/.test(t))
          return err('MST', 'Mã số DN/Mã số thuế phải 10 số (hoặc 13 số cú pháp 10-3): ' + v);
        break;
      }
      case 'money':
        if (parseMoney(v) == null)
          return err('MONEY', 'Giá trị tiền không hợp lệ (ví dụ đúng: 1.000.000): ' + v);
        break;
      case 'number':
        if (!/^\d+$/.test(stripSep(v)))
          return err('NUMERIC', 'Chỉ được nhập số: ' + v);
        break;
      case 'vsic':
        if (ctx.vsicList && !isValidMaNganh(ctx.vsicList, v))
          return err('VSIC', 'Mã ngành không có trong danh mục VSIC: ' + v);
        break;
      default:
        break; // text: chỉ required ở trên
    }
    return [];
  }

  function isValidMaNganh(list, val) {
    var v = String(val == null ? '' : val).trim();
    if (!v) return true;
    return (list || []).some(function (x) { return String(x.ma) === v; });
  }

  /* Validate một mẫu biểu. store = {values, checks, loops}. Trả error[]. */
  function validateDocument(docId, blocks, store, ctx) {
    ctx = ctx || {};
    var st = store || {};
    st.values = st.values || {};
    st.checks = st.checks || {};
    st.loops = st.loops || {};
    var info = collectKeys(blocks);
    var errors = [];
    var seenErr = {};

    function push(e) {
      var id = [e.docId, e.key, e.code].join('|');
      if (seenErr[id]) return;
      seenErr[id] = true;
      errors.push(e);
    }

    info.keys.forEach(function (key) {
      if (Object.prototype.hasOwnProperty.call(st.checks, key)) return; // checkbox bỏ qua
      var meta = getFieldMeta(key);
      if (!meta) return; // key chưa metadata hoá: không check thêm
      validateField(meta, st.values[key], { docId: docId, vsicList: ctx.vsicList })
        .forEach(push);
    });

    Object.keys(info.loops).forEach(function (name) {
      var lm = getLoopMeta(name);
      if (!lm) return;
      var tags = info.loops[name];
      var rows = st.loops[name] || [];
      var filled = rows.filter(function (r) {
        return tags.some(function (t) { return String((r || {})[t] == null ? '' : r[t]).trim() !== ''; });
      });
      if (lm.minRowsFilled > 0 && filled.length > 0 && filled.length < lm.minRowsFilled) {
        push({
          key: name, docId: docId, code: 'MIN_ROWS',
          message: lm.label + ': cần tối thiểu ' + lm.minRowsFilled +
            ' dòng có dữ liệu (đang có ' + filled.length + ')',
          severity: 'blocking'
        });
      }
      lm.moneyTags.forEach(function (tag) {
        for (var i = 0; i < rows.length; i++) {
          var raw = String((rows[i] || {})[tag] == null ? '' : rows[i][tag]).trim();
          if (!raw) continue;
          if (parseMoney(raw) == null) {
            push({
              key: name + '.' + tag, docId: docId, code: 'MONEY',
              message: lm.label + ' dòng ' + (i + 1) + ': giá trị tiền không hợp lệ: ' + raw,
              severity: 'blocking'
            });
            return;
          }
        }
      });
      lm.percentTags.forEach(function (tag) {
        var sum = 0, hasVal = false;
        rows.forEach(function (r) {
          var n = parseMoney((r || {})[tag]);
          if (n != null) { sum += n; hasVal = true; }
        });
        if (hasVal && Math.round(sum) !== 100) {
          push({
            key: name + '.' + tag, docId: docId, code: 'PERCENT_SUM',
            message: lm.label + ': tổng tỷ lệ ' + tag + ' = ' + sum + '% (cần đúng 100%)',
            severity: 'warning'
          });
        }
      });
      (lm.vsicTags || []).forEach(function (tag) {
        if (!ctx.vsicList) return;
        for (var i = 0; i < rows.length; i++) {
          var raw = String((rows[i] || {})[tag] == null ? '' : rows[i][tag]).trim();
          if (!raw) continue;
          if (!isValidMaNganh(ctx.vsicList, raw)) {
            push({
              key: name + '.' + tag, docId: docId, code: 'VSIC',
              message: lm.label + ' dòng ' + (i + 1) + ': mã ngành không hợp lệ: ' + raw,
              severity: 'blocking'
            });
            return;
          }
        }
      });
    });

    return errors;
  }

  /* Gộp lỗi nhiều mẫu trong hồ sơ. docs = [{id, blocks}] đã chọn. */
  function validateDossier(docs, store, ctx) {
    var all = [];
    (docs || []).forEach(function (d) {
      validateDocument(d.id, d.blocks, store, ctx).forEach(function (e) { all.push(e); });
    });
    return all;
  }

  // ----------------------------------------------------------- draft migration

  /* v2 = v1 + activeDocId/viewState/savedAt. Draft cũ v1 giữ nguyên dữ liệu. */
  function migrateDraft(draft) {
    if (!draft || typeof draft !== 'object') return null;
    if (Number(draft.v) >= 2) return draft;
    if (!draft.store) return null; // draft không hiểu -> bỏ qua
    return {
      v: 2,
      caseId: draft.caseId != null ? draft.caseId : null,
      checkedForms: Array.isArray(draft.checkedForms) ? draft.checkedForms.slice() : [],
      activeDocId: null,
      autoSum: !!draft.autoSum,
      viewState: {},
      store: {
        values: Object.assign({}, draft.store.values),
        checks: Object.assign({}, draft.store.checks),
        loops: draft.store.loops || {}
      },
      savedAt: null
    };
  }

  // ----------------------------------------------------------------- exports

  root.parseMoney = parseMoney;
  root.formatMoney = formatMoney;
  root.FIELD_META = FIELD_META;
  root.LOOP_META = LOOP_META;
  root.getFieldMeta = getFieldMeta;
  root.getLoopMeta = getLoopMeta;
  root.collectKeys = collectKeys;
  root.validateField = validateField;
  root.validateDocument = validateDocument;
  root.validateDossier = validateDossier;
  root.isValidMaNganh = isValidMaNganh;
  root.migrateDraft = migrateDraft;

})(typeof module !== 'undefined' && module.exports ? module.exports : (window.FormDomain = window.FormDomain || {}));
