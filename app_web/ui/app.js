/* app.js - wiring giao diện "khai trực tiếp kiểu HTKK".
 *
 * - Chỉ render MỘT tờ khai active (state.activeDocId) vào #pages; tab đáy
 *   chuyển mẫu thật, giữ dữ liệu/scroll/focus qua state.viewState.
 * - Store chung (values/checks/loops) là nguồn chân lý: các ô cùng exact
 *   data-key tự đồng bộ; render lại từ store khi đổi mẫu nên dữ liệu chung
 *   giữa các mẫu luôn nhất quán.
 * - Validation dùng module thuần FormDomain; lỗi nhóm theo mẫu ở panel phải,
 *   bấm lỗi nhảy đúng tab + focus đúng ô.
 * - Dirty/save machine: Chưa lưu / Đang lưu / Đã lưu / Lỗi lưu; Ctrl+S lưu
 *   nhanh localStorage; Ctrl+PgUp/PgDn đổi tab; VSIC hỗ trợ bàn phím.
 * - Draft v2 (docs/htkk-ui-contract.md mục 4) + migration v1 qua migrateDraft.
 * - Chọn mẫu biểu: metadata từng form (bat_buoc, nhóm oneOf) từ use_cases.json
 *   giữ trong state.formMeta; bắt buộc checked+disabled, tùy chọn mặc định bỏ;
 *   nhóm oneOf tự loại trừ. Gate export kiểm lựa chọn mẫu bằng hàm thuần
 *   checkFormSelection (Helpers.FormFlow). Race đổi case chặn bằng
 *   RequestToken; autosave thành công mới đặt dirty=false (saveOutcome).
 */
(function () {
  'use strict';

  /* Trong browser dùng global window.Render/FormDomain; khi require từ node
   * (chỉ để test Helpers thuần) nạp qua module. */
  var IS_NODE = typeof window === 'undefined';
  var R = IS_NODE ? require('./render.js') : window.Render;
  var FD = IS_NODE ? require('./form-domain.js') : window.FormDomain;

  // ------------------------------------------------------------- trạng thái
  var state = {
    mock: (typeof location !== 'undefined') &&
          new URLSearchParams(location.search).get('mock') === '1',
    vsic: [],
    cases: [],
    groups: [],
    caseId: null,
    docs: [],            // [{id, ten_mau, blocks}] đã nạp của case hiện tại
    formMeta: {},        // docId -> metadata form {bat_buoc, ghi_chu, oneOf}
    checkedForms: {},    // docId -> bool: nguồn chân lý lựa chọn mẫu (DOM chỉ phản chiếu)
    store: R.newStore(),
    autoSum: false,
    activeDocId: null,   // mẫu DUY NHẤT đang hiển thị
    dirty: false,
    saveState: 'unsaved',
    autosaveTimer: null,
    errors: [],          // kết quả Kiểm tra gần nhất
    selectedLoopRow: {}, // loopName -> rowIndex đang chọn (tương thích cũ)
    selRowId: {},        // loopName -> _row_id đang chọn
    multiSel: {},        // loopName -> { _row_id: true } chọn nhiều (Ctrl+click)
    viewState: {},       // docId -> {scrollTop, focusKey}
    pendingDraft: null,  // draft chờ docs nạp xong để khôi phục
    uiLayouts: {},       // docId -> ui_layouts JSON (PHASE 6) | null nếu 404
    vsicItems: [],
    vsicIndex: 0
  };

  function $(sel) { return document.querySelector(sel); }
  function api() {
    return (window.pywebview && window.pywebview.api) || null;
  }
  function esc(s) { return R.escapeHtml(s); }
  function cssEsc(s) {
    return (typeof window !== 'undefined' && window.CSS && CSS.escape)
      ? CSS.escape(s) : String(s).replace(/"/g, '\\"');
  }

  // ------------------------------------------- GridCtl: editable-grid thuần
  /* Controller GENERIC cho mọi bảng lặp (PLAN.md PHASE 1B/5): add/delete/
   * reorder/duplicate/clear trên store {loops}. Toàn bộ hàm THUẦN (không DOM,
   * nhận store làm tham số) để node-test trực tiếp; wrapper UI bên dưới chỉ
   * lo confirm/focus/rerender. Metadata từng bảng resolve qua
 * FormDomain.getGridMeta (form-scoped FORM_GRID_META trước, rồi GRID_META).
   * Mỗi row mang _row_id ổn định ('r<seq>_<rand>') giữ qua draft round-trip
   * và bị LOẠI khỏi payload export. STT không lưu - luôn suy từ thứ tự mảng. */
  var _rowIdSeq = 0;
  var GridCtl = {
    nextId: function () {
      _rowIdSeq += 1;
      return 'r' + _rowIdSeq + '_' + Math.random().toString(36).slice(2, 8);
    },

    /* Metadata bảng: resolve form-scoped trước (FORM_GRID_META[docId]) rồi
     * mới tới GRID_META toàn cục. Không truyền docId -> hành vi cũ (toàn cục). */
    meta: function (loop, docId) {
      return docId ? FD.getGridMeta({ docId: docId, loop: loop })
                   : FD.getGridMeta(loop);
    },

    /* Trả mảng row của loop (mutate tại chỗ): giá trị KHÔNG phải mảng
     * (truthy nhưng hỏng) được thay bằng mảng rỗng thay vì trả nguyên về cho
     * caller rồi ném TypeError ở .forEach/.splice. */
    rows: function (store, loop) {
      if (!Array.isArray(store.loops[loop])) store.loops[loop] = [];
      return store.loops[loop];
    },

    findRowIndex: function (rows, rowId) {
      for (var i = 0; i < rows.length; i++) {
        if (rows[i] && rows[i]._row_id === rowId) return i;
      }
      return -1;
    },

    /* Gán _row_id cho mọi row còn thiếu (mutate tại chỗ, idempotent). */
    ensureIds: function (store) {
      var loops = store.loops || {};
      /* Guard draft hỏng: loops là primitive thì bỏ qua, không ném. */
      if (typeof loops !== 'object') return store;
      Object.keys(loops).forEach(function (name) {
        GridCtl.rows(store, name).forEach(function (r) {
          if (r && typeof r === 'object' && !r._row_id) r._row_id = GridCtl.nextId();
        });
      });
      return store;
    },

    /* Thêm dòng trống sau afterRowId (nếu có và còn tồn tại), nếu không thì
     * ở cuối. Trả về vị trí + id dòng mới. KHÔNG tự chặn maxRows ở mức data:
     * UI chặn trước khi gọi; vi phạm metadata chỉ là lỗi validator. */
    addRow: function (store, loop, afterRowId) {
      var rows = GridCtl.rows(store, loop);
      var row = { _row_id: GridCtl.nextId() };
      var at = (afterRowId != null) ? GridCtl.findRowIndex(rows, afterRowId) : -1;
      if (at >= 0) rows.splice(at + 1, 0, row);
      else rows.push(row);
      return { index: rows.indexOf(row), id: row._row_id };
    },

    /* Xóa nhiều dòng theo _row_id (bỏ qua id lạ). Trả số dòng đã xóa. */
    deleteRows: function (store, loop, rowIds) {
      var rows = GridCtl.rows(store, loop);
      var kill = {};
      (rowIds || []).forEach(function (id) { kill[id] = true; });
      var kept = rows.filter(function (r) { return !(r && kill[r._row_id]); });
      var removed = rows.length - kept.length;
      if (removed) store.loops[loop] = kept;
      return removed;
    },

    /* Xóa dữ liệu toàn bộ bảng. UI vẫn render ít nhất 1 dòng trống. */
    clearRows: function (store, loop) {
      var n = GridCtl.rows(store, loop).length;
      store.loops[loop] = [];
      return n;
    },

    /* Đổi thứ tự: dir=-1 lên, +1 xuống. Trả index mới hoặc -1 nếu không đổi. */
    moveRow: function (store, loop, rowId, dir) {
      var rows = GridCtl.rows(store, loop);
      var i = GridCtl.findRowIndex(rows, rowId);
      var j = i + (dir < 0 ? -1 : 1);
      if (i < 0 || j < 0 || j >= rows.length) return -1;
      var t = rows[i]; rows[i] = rows[j]; rows[j] = t;
      return j;
    },

    /* Nhân bản dòng rowId ngay sau chính nó, BỎ các field định danh/khóa theo
     * metadata duplicateKeys (vd so_cccd, ma_nganh) và _row_id cũ.
     * docId tùy chọn để resolve metadata form-scoped.
     * Trả {_row_id mới, index} hoặc null khi không tìm thấy dòng nguồn. */
    duplicateRow: function (store, loop, rowId, docId) {
      var rows = GridCtl.rows(store, loop);
      var i = GridCtl.findRowIndex(rows, rowId);
      if (i < 0) return null;
      var gm = GridCtl.meta(loop, docId) || {};
      var clone = Object.assign({}, rows[i]);
      delete clone._row_id;
      (gm.duplicateKeys || []).forEach(function (k) { delete clone[k]; });
      clone._row_id = GridCtl.nextId();
      rows.splice(i + 1, 0, clone);
      return { id: clone._row_id, index: i + 1 };
    },

    /* Radio một-lựa-chọn trong cột tag của loop: đặt 'X' cho dòng rowId,
     * gỡ ('') mọi dòng khác cùng cột (dùng chung bởi handler change UI). */
    setExclusiveRadio: function (store, loop, rowId, tag, checked) {
      var rows = GridCtl.rows(store, loop);
      rows.forEach(function (r) {
        if (!r) return;
        if (checked && r._row_id === rowId) r[tag] = 'X';
        else r[tag] = '';
      });
    },

    /* Bản sao loops SẠCH để payload DOCX (Bridge.export): bỏ mọi field nội bộ
     * (_row_id...) và map la_nganh_chinh -> 'X'/'' đúng the trong template pháp
     * lý (ô {la_nganh_chinh} phải in dấu X, không in chữ True/False). Store/
     * draft giữ nguyên 'X'/'' như radio; đây là CHỐ ĐƠN NHẤT trên đường export
     * (buildExportData cũng đi qua hàm này nên không bị lệch hai nơi).
     * docIds tùy chọn (các mẫu đang chọn trong hồ sơ): resolve metadata
     * form-scoped trước khi fallback toàn cục.
     * EXPORT GUARD theo activation: grid INACTIVE-THEO-SELECTOR (meta khai
     * checkedKey/valueOf - nguồn chính khi owner chốt) không được lọt dòng
     * nào vào payload (section không áp dụng phải rỗng trong văn bản).
     * Grid inactive vì INTERIM minFilledRows vốn không có dòng có dữ liệu ->
     * KHÔNG filter để payload giữ nguyên 100% hành vi cũ; grid KHÔNG có
     * activeWhen cũng không bị đụng tới.
     *
     * P2.0 EXPORT CONFLICT GUARD (chống 'first-doc-wins' ÂM THẦM): loop cùng
     * tên có thể được resolve sang metadata có contract khác nhau tùy mẫu
     * (vd nganh_bo_sung của PLI_M12 rơi về GRID_META toàn cục cols
     * [ten_nganh,...] trong khi PLII_M02 tự khai form-scoped cols
     * [ten_nganh_bo_sung,...]) trong khi payload là MỘT mảng duy nhất theo
     * tên loop - không thể phục vụ hai contract cùng lúc. Khi resolve meta
     * cho một loop, guard chạy theo MỘT chỗ duy nhất này với hai bước:
     *  1. Với TỪNG docId được truyền, resolve meta ĐÚNG NHƯ CŨ (form-scoped
     *     FORM_GRID_META[docId].loops trước, fallback GRID_META toàn cục)
     *     rồi thu thập sides = các {docId, metaRef} KHÁC NHAU VỀ REFERENCE.
     *     SHORT-CIRCUIT chống false-positive: nếu mọi sample trỏ CÙNG MỘT
     *     object (trường hợp phổ biến nhất - nhiều mẫu cùng fallback về
     *     GRID_META[name], hoặc chỉ 1 mẫu có meta) -> tương đương TUYỆT ĐỐI,
     *     không so signature, không flag.
     *  2. Có >=2 reference khác nhau -> so signature 'export contract':
     *     requirePrimary, autoName{codeTag,nameTag}, tập tag cột
     *     (columns[].tag sort), chế độ activation (activationModeOf).
     *     Signature BẰNG vẫn coi là tương đương (vd PLII_M02.ds_nganh là
     *     clone mkGrid của GRID_META.ds_nganh nhưng cùng requirePrimary/
     *     autoName/colTags/actMode -> dossier ghép mẫu KHÔNG bị flag).
     *     Khác nhau -> ghi vào report GridCtl.lastExportConflicts (reset
     *     mỗi lần gọi); đường export THẬT phải gọi GridCtl.exportLoopsStrict
     *     - chỗ DUY NHẤT ném lỗi có cấu trúc để FAIL LOUD, không xuất
     *     payload nửa vời. Payload do HÀM NÀY trả luôn giữ nguyên hành vi
     *     first-doc-wins cũ 100% (tương thích ngược cho caller cũ/test). */
    lastExportConflicts: [],
    exportLoops: function (store, docIds) {
      var out = {};
      var conflicts = [];
      Object.keys(store.loops || {}).forEach(function (name) {
        var cf = GridCtl.loopContractConflict(name, docIds);
        if (cf) conflicts.push(cf);
        var gm = null;
        (docIds || []).some(function (id) {
          gm = FD.getGridMeta({ docId: id, loop: name });
          return !!gm;
        });
        if (!gm) gm = FD.getGridMeta(name);
        var rows = store.loops[name] || [];
        if (gm && FD.activationModeOf(gm) === 'selector' &&
            !FD.isActiveGrid(gm, rows, store)) {
          rows = []; // selector nói section không áp dụng -> payload rỗng
        }
        out[name] = rows.map(function (row) {
          var clean = {};
          Object.keys(row || {}).forEach(function (k) {
            if (k.charAt(0) === '_') return; // _row_id và field nội bộ khác
            clean[k] = row[k];
          });
          if (Object.prototype.hasOwnProperty.call(clean, 'la_nganh_chinh')) {
            clean.la_nganh_chinh =
              (clean.la_nganh_chinh === 'X' || clean.la_nganh_chinh === true)
                ? 'X' : '';
          } else if (gm && gm.requirePrimary) {
            clean.la_nganh_chinh = '';
          }
          return clean;
        });
      });
      GridCtl.lastExportConflicts = conflicts;
      return out;
    },

    /* -------------------------------------- P2.0: export contract guard */
    /* Signature 'export contract' của một grid meta - mọi field ảnh hưởng
     * trực tiếp đến PAYLOAD export của loop:
     *  - requirePrimary       : có điền '' cho la_nganh_chinh thiếu hay không
     *  - autoName code/nameTag: cặp tag mã->tên mà template mong đợi
     *  - colTags              : tập tag cột (sort) template mong đợi
     *  - actMode              : activationModeOf - null | 'selector' |
     *                           'interim-filled-data' (quyết định việc lọc
     *                           section inactive khỏi payload)
     * Hai meta tương đương <=> JSON signature bằng. */
    exportContractSig: function (gm) {
      var tags = ((gm && gm.columns) || [])
        .map(function (c) { return c && c.tag; })
        .filter(Boolean).slice().sort();
      return {
        requirePrimary: !!(gm && gm.requirePrimary),
        autoNameCodeTag: (gm && gm.autoName && gm.autoName.codeTag) || null,
        autoNameNameTag: (gm && gm.autoName && gm.autoName.nameTag) || null,
        colTags: tags.join('|'),
        actMode: FD.activationModeOf(gm)
      };
    },

    /* Lý do hai signature khác nhau (đưa vào message lỗi/report). */
    exportSigDiff: function (sa, sb) {
      var reasons = [];
      if (sa.requirePrimary !== sb.requirePrimary)
        reasons.push('requirePrimary: ' + sa.requirePrimary + ' != ' + sb.requirePrimary);
      if (sa.autoNameCodeTag !== sb.autoNameCodeTag ||
          sa.autoNameNameTag !== sb.autoNameNameTag)
        reasons.push('autoName: [' + sa.autoNameCodeTag + ' -> ' + sa.autoNameNameTag +
          '] != [' + sb.autoNameCodeTag + ' -> ' + sb.autoNameNameTag + ']');
      if (sa.colTags !== sb.colTags)
        reasons.push('tap tag cot: [' + sa.colTags + '] != [' + sb.colTags + ']');
      if (sa.actMode !== sb.actMode)
        reasons.push('che do activation (activationModeOf): ' + sa.actMode +
          ' != ' + sb.actMode);
      return reasons;
    },

    /* Thu thập sides của MỘT loop theo ĐÚNG resolver cũ cho TỪNG docId
     * (form-scoped trước, fallback GRID_META toàn cục - getGridMeta).
     * Trả các side {docId, semanticKey, metaRef} KHÁC NHAU VỀ REFERENCE,
     * giữ thứ tự docIds (side đầu = winner của payload first-wins); docId
     * không resolve được meta hoặc trùng reference side trước thì bỏ. */
    collectLoopSides: function (name, docIds) {
      var seenRef = [];
      var out = [];
      (docIds || []).forEach(function (id) {
        var gm = FD.getGridMeta({ docId: id, loop: name });
        if (!gm || seenRef.indexOf(gm) >= 0) return;
        seenRef.push(gm);
        out.push({
          docId: id,
          semanticKey: gm.semanticKey || null,
          metaRef: gm
        });
      });
      return out;
    },

    /* Đối chiếu contract các meta của MỘT loop theo tên:
     *  1. <2 side khác reference -> null (SHORT-CIRCUIT tương đương tuyệt
     *     đối - mọi mẫu cùng fallback chung một object là trường hợp điển hình).
     *  2. >=2 reference -> so signature; mọi signature BẰNG -> null (vd
     *     clone mkGrid vs bản global cùng contract); LỆCH -> conflict có cấu
     *     trúc {code, loop, winner, sides[], reasons[], message} - winner là
     *     meta đầu tiên theo thứ tự docIds (đúng first-doc-wins cũ, chỉ BÁO
     *     thay vì im lặng). */
    loopContractConflict: function (name, docIds) {
      var sides = GridCtl.collectLoopSides(name, docIds);
      if (sides.length < 2) return null;
      var sigs = sides.map(function (s) {
        return { side: s, sig: GridCtl.exportContractSig(s.metaRef) };
      });
      var first = sigs[0];
      var reasons = [];
      for (var i = 1; i < sigs.length; i++) {
        GridCtl.exportSigDiff(first.sig, sigs[i].sig).forEach(function (r) {
          function tag(s) {
            return s.docId + (s.semanticKey ? '(' + s.semanticKey + ')' : '');
          }
          var msg = tag(first.side) + ' khac ' + tag(sigs[i].side) + ' - ' + r;
          if (reasons.indexOf(msg) < 0) reasons.push(msg);
        });
      }
      if (!reasons.length) return null; // signature THỰC SỰ tương đương
      return {
        code: 'EXPORT_LOOP_CONTRACT_CONFLICT',
        loop: name,
        winner: {
          docId: first.side.docId,
          semanticKey: first.side.semanticKey,
          signature: first.sig
        },
        sides: sigs.map(function (x) {
          return {
            docId: x.side.docId,
            semanticKey: x.side.semanticKey,
            signature: x.sig
          };
        }),
        reasons: reasons,
        message: 'Loop "' + name + '" co nhieu contract export khac nhau giua cac mau (' +
          sides.map(function (s) { return s.docId; }).join(', ') +
          '). Khong duoc am tham chon meta cua mau dau tien. Ly do khac: ' +
          reasons.join('; ')
      };
    },

    /* Quét TẤT CẢ loop đang có dữ liệu trong store, trả danh sách conflict. */
    detectExportConflicts: function (store, docIds) {
      var found = [];
      Object.keys((store && store.loops) || {}).forEach(function (name) {
        var cf = GridCtl.loopContractConflict(name, docIds);
        if (cf) found.push(cf);
      });
      return found;
    },

    /* CHỐ DUY NHẤT cho đường export thật (buildExportData/UI export):
     * giống exportLoops nhưng NÉM lỗi có cấu trúc khi phát hiện xung đột
     * contract (err.code='EXPORT_LOOP_CONTRACT_CONFLICT', err.conflicts=
     * report đầy đủ) -> export FAIL LOUD, không payload nửa vời. Caller
     * bắt lỗi này phải chặn toàn bộ phần loops, không xuất cục bộ. */
    exportLoopsStrict: function (store, docIds) {
      var conflicts = GridCtl.detectExportConflicts(store, docIds);
      if (conflicts.length) {
        var e = new Error(conflicts.map(function (c) { return c.message; }).join(' | '));
        e.code = 'EXPORT_LOOP_CONTRACT_CONFLICT';
        e.conflicts = conflicts;
        throw e;
      }
      return GridCtl.exportLoops(store, docIds);
    },

    /* Phân loại trạng thái ô mã ngành theo PLAN.md PHASE 4 (thuần, offline):
     *  ''             -> { st:'empty' }   : xóa ten cùng dòng, gỡ invalid
     *  mã khớp danh mục -> { st:'exact', item }  : tự điền ten chính thức
     *  chữ (tên có/không dấu) có kết quả -> { st:'typing', items }: gợi ý,
     *                     KHÔNG báo blocking (tìm ngược bằng tên)
     *  1-3 chữ số     -> { st:'typing', items }  : mở gợi ý, chưa blocking
     *  còn lại        -> { st:'invalid' } : viền đỏ VSIC_INVALID, giữ giá trị
     *                  người nhập, KHÔNG tự chế tên */
    vsicResolve: function (list, raw) {
      var v = String(raw == null ? '' : raw).trim();
      if (!v) return { st: 'empty', items: [] };
      for (var i = 0; i < (list || []).length; i++) {
        if (String(list[i].ma) === v) return { st: 'exact', item: list[i], items: [list[i]] };
      }
      if (!/^\d+$/.test(v)) {
        // tìm ngược bằng tên ngành (có dấu/không dấu)
        var byName = R.searchVsic(list || [], v, 12);
        return byName.length ? { st: 'typing', items: byName } : { st: 'invalid', items: [] };
      }
      if (/^\d{1,3}$/.test(v)) {
        return { st: 'typing', items: R.searchVsic(list || [], v, 12) };
      }
      return { st: 'invalid', items: [] };
    }
  };


  // --------------------------- FormFlow: helpers thuần chọn mẫu biểu/race
  /* Các hàm THUẦN (không DOM) cho nghiệp vụ chọn mẫu theo PLAN.md Agent 1B:
   * metadata bat_buoc + nhóm loại trừ oneOf ĐỀU nằm trong dữ liệu
   * use_cases.json (schema_forms ở đầu file) - renderer/controller KHÔNG suy
   * đoán nhóm từ tên mẫu/id. Node-test trực tiếp qua Helpers.FormFlow. */

  /* blocks/form_maps dùng ID zero-pad 2 chữ số: PLI_M02, PLII_M01... */
  function formIdOf(f) {
    return 'PL' + f.pl + '_M' + String(f.mau).padStart(2, '0');
  }

  function formIds(cs) {
    return ((cs && cs.forms) || []).map(formIdOf);
  }

  /* Map case.forms (+ case.forms_oneOf) -> metadata theo docId.
   * bat_buoc thiếu trường coi như true (tương thích dữ liệu cũ/mock).
   * oneOf = {gid, ids, max} gắn vào từng form thuộc nhóm; max mặc định 1. */
  function buildFormMeta(cs) {
    var meta = {};
    ((cs && cs.forms) || []).forEach(function (f) {
      meta[formIdOf(f)] = { bat_buoc: f.bat_buoc !== false, ghi_chu: f.ghi_chu || '', oneOf: null };
    });
    ((cs && cs.forms_oneOf) || []).forEach(function (g, gi) {
      if (!g || !Array.isArray(g.ids)) return;
      var max = (g.max == null || g.max < 1) ? 1 : g.max;
      var gid = 'oneof_' + gi;
      g.ids.forEach(function (id) {
        if (!meta[id]) meta[id] = { bat_buoc: false, ghi_chu: '', oneOf: null };
        meta[id].oneOf = { gid: gid, ids: g.ids.slice(), max: max };
      });
    });
    return meta;
  }

  /* Tick/bỏ tick docId rồi TỰ LOẠI TRỪ trong nhóm oneOf để không vượt max
   * (max=1: tick một mẫu -> bỏ tick mọi mẫu khác cùng nhóm). Trả map MỚI,
   * không mutate map đầu vào; mẫu vừa tick luôn giữ nguyên trạng thái on. */
  function applyOneOfExclusive(meta, checkedMap, changedId) {
    var out = Object.assign({}, checkedMap);
    var g = (meta[changedId] || {}).oneOf;
    if (!g || !out[changedId]) return out;
    var over = g.ids.filter(function (id) { return out[id]; }).length - g.max;
    for (var i = 0; over > 0 && i < g.ids.length; i++) {
      var id = g.ids[i];
      if (id !== changedId && out[id]) { out[id] = false; over--; }
    }
    return out;
  }

  /* GATE EXPORT THUẦN: kiểm LỰA CHỌN MẪU trước khi gọi Bridge.export.
   * Trả error[] cùng shape contract (docs mục 2):
   *  - thiếu mẫu bắt buộc            -> FORM_REQUIRED_MISSING (blocking)
   *  - nhóm oneOf chưa chọn mẫu nào  -> FORM_ONEOF_EMPTY     (blocking)
   *  - nhóm oneOf vượt max (dữ liệu) -> FORM_ONEOF_EXCEED    (blocking)
   * titles (tùy chọn): {docId: ten_mau} để thông điệp dễ đọc hơn. */
  function checkFormSelection(meta, checkedIds, titles) {
    var errs = [];
    var checked = {};
    (checkedIds || []).forEach(function (id) { checked[id] = true; });
    function nameOf(id) {
      return (titles && titles[id]) ? (titles[id] + ' (' + id + ')') : id;
    }
    Object.keys(meta).forEach(function (id) {
      if (meta[id].bat_buoc && !checked[id]) {
        errs.push({
          key: '@forms:' + id, docId: id, code: 'FORM_REQUIRED_MISSING',
          severity: 'blocking',
          message: 'Mẫu bắt buộc chưa được chọn: ' + nameOf(id)
        });
      }
    });
    var groups = {};
    Object.keys(meta).forEach(function (id) {
      var g = meta[id].oneOf;
      if (!g) return;
      var gr = groups[g.gid] = groups[g.gid] ||
        { ids: g.ids.slice(), max: g.max, picked: [] };
      if (checked[id] && gr.picked.indexOf(id) < 0) gr.picked.push(id);
    });
    Object.keys(groups).forEach(function (gid) {
      var gr = groups[gid];
      if (!gr.picked.length) {
        errs.push({
          key: '@forms:oneof:' + gid, docId: gr.ids[0], code: 'FORM_ONEOF_EMPTY',
          severity: 'blocking',
          message: 'Phải chọn đúng một mẫu trong nhóm loại trừ: ' +
            gr.ids.map(nameOf).join(', ')
        });
      } else if (gr.picked.length > gr.max) {
        errs.push({
          key: '@forms:oneof:' + gid, docId: gr.picked[0], code: 'FORM_ONEOF_EXCEED',
          severity: 'blocking',
          message: 'Chỉ được chọn tối đa ' + gr.max + ' mẫu trong nhóm loại trừ: ' +
            gr.ids.map(nameOf).join(', ') +
            ' (đang chọn: ' + gr.picked.map(nameOf).join(', ') + ')'
        });
      }
    });
    return errs;
  }

  /* Khôi phục lựa chọn mẫu từ draft (thuần): bắt buộc LUÔN tick kể cả draft
   * cũ thiếu; tùy chọn chỉ tick khi draft.checkedForms có; nhóm oneOf nếu
   * vượt max thì giữ mẫu được chọn SAU CÙNG theo draft.checkedForms (khớp
   * hành vi UI "tick sau thắng"; form bắt buộc - nếu dữ liệu cấu hình lệch -
   * luôn được giữ trước); activeDocId chỉ chấp nhận doc HỢP LỆ và đang được
   * chọn, nếu không fallback về mẫu được chọn đầu tiên. */
  function restoreSelection(meta, docs, draft) {
    var list = docs || [];
    var want = {};
    ((draft && draft.checkedForms) || []).forEach(function (id) { want[id] = true; });
    var cf = {};
    list.forEach(function (d) {
      cf[d.id] = !!((meta[d.id] || {}).bat_buoc) || !!want[d.id];
    });
    // oneOf: nhóm nào vượt max thì bỏ ưu tiên thấp nhất trước
    var groups = {};
    list.forEach(function (d) {
      var g = (meta[d.id] || {}).oneOf;
      if (g) groups[g.gid] = g;
    });
    Object.keys(groups).forEach(function (gid) {
      var g = groups[gid];
      // xếp hạng giữ: draft muộn nhất đầu tiên, rồi tới bắt buộc, rồi còn lại
      var ranked = ((draft && draft.checkedForms) || [])
        .filter(function (id) { return g.ids.indexOf(id) >= 0 && cf[id]; })
        .reverse();
      list.forEach(function (d) {
        var id = d.id;
        if (g.ids.indexOf(id) >= 0 && cf[id] && ranked.indexOf(id) < 0) {
          if (meta[id].bat_buoc) ranked.unshift(id);
          else ranked.push(id);
        }
      });
      while (ranked.length > g.max) cf[ranked.pop()] = false;
    });
    var active = (draft && draft.activeDocId && cf[draft.activeDocId] &&
      list.some(function (x) { return x.id === draft.activeDocId; }))
      ? draft.activeDocId : null;
    if (!active) {
      var vis = list.filter(function (x) { return cf[x.id]; });
      active = vis.length ? vis[0].id : null;
    }
    return { checkedForms: cf, activeDocId: active };
  }

  /* HTML danh sách mẫu (thuần): bắt buộc checked+disabled kèm nhãn
   * "(Bắt buộc)"; tùy chọn unchecked trừ khi checkedMap có, nhãn "(Tùy chọn)". */
  function formListHtml(docs, meta, checkedMap) {
    return (docs || []).map(function (d) {
      var m = meta[d.id] || {};
      var req = !!m.bat_buoc;
      var on = req || !!checkedMap[d.id];
      return '<label class="' + (req ? 'form-req' : 'form-opt') + '">' +
        '<input type="checkbox" class="form-tick" value="' + esc(d.id) + '"' +
        (on ? ' checked' : '') + (req ? ' disabled aria-disabled="true"' : '') +
        '> ' + esc(d.ten_mau || d.id) +
        ' <span class="form-tag">' + (req ? '(Bắt buộc)' : '(Tùy chọn)') +
        '</span></label>';
    }).join('');
  }

  /* Token chuỗi request chống race onCaseChange/restore draft: kết quả async
   * của request CŨ resolve muộn không được ghi state khi user đã đổi case.
   * Thuần để node-test mô phỏng Promise cũ resolve sau một cách tất định. */
  var RequestToken = {
    _seq: 0,
    next: function () { return ++RequestToken._seq; },
    fresh: function (seq) { return seq === RequestToken._seq; }
  };

  /* Kết quả trạng thái sau MỘT lần lưu (autosave lẫn quickSave): chỉ thành
   * công mới xóa cờ dirty; thất bại giữ dirty=true và saveState='error'. */
  function saveOutcome(ok) {
    return ok ? { dirty: false, saveState: 'saved' }
              : { dirty: true, saveState: 'error' };
  }

  /* Case dùng khi chạy ?mock=1 (không đọc use_cases.json thật). */
  var MOCK_CASES = [
    {
      id: 'pilot_ui_m02_m06', nhom: 'Thành lập doanh nghiệp',
      ten: '(PILOT UI) Đồng bộ M02 + M06',
      mo_ta: '(MOCK) Case kiểm thử pilot: điền tên ở M02, sang M06 vẫn thấy giá trị.',
      forms: [{ pl: 'I', mau: 2, bat_buoc: true }, { pl: 'I', mau: 6, bat_buoc: true }],
      giay_to_kem: [],
      luu_y: ['Đây là case PILOT cho giao diện mới - không phải thủ tục thật.']
    },
    {
      id: 'thanh_lap_tnhh_1tv', nhom: 'Thành lập doanh nghiệp',
      ten: 'Thành lập Công ty TNHH một thành viên',
      mo_ta: '(MOCK) Lập công ty TNHH một thành viên.',
      forms: [{ pl: 'I', mau: 2, bat_buoc: true }],
      giay_to_kem: ['Bản Điều lệ công ty (MOCK)'],
      luu_y: ['Đây là chế độ mock - xuất hồ sơ cần Bridge Python.']
    },
    {
      id: 'thanh_lap_tnhh_2tv', nhom: 'Thành lập doanh nghiệp',
      ten: 'Thành lập Công ty TNHH hai thành viên trở lên',
      mo_ta: '(MOCK) Lập công ty TNHH hai thành viên trở lên.',
      forms: [{ pl: 'I', mau: 6, bat_buoc: true }],
      giay_to_kem: ['Bản Điều lệ công ty (MOCK)'],
      luu_y: ['Danh sách thành viên tự cộng tổng vốn góp.']
    },
    {
      id: 'dang_ky_ho_kinh_doanh_lan_dau', nhom: 'Hộ kinh doanh',
      ten: 'Đăng ký hộ kinh doanh lần đầu',
      mo_ta: '(MOCK) Đăng ký hộ kinh doanh lần đầu.',
      forms: [{ pl: 'II', mau: 1, bat_buoc: true }],
      giay_to_kem: [],
      luu_y: []
    }
  ];

  // ---------------------------------------------------------------- toast
  function toast(html, kind, sticky) {
    var box = document.createElement('div');
    box.className = 'toast' + (kind ? ' ' + kind : '');
    box.innerHTML = html;
    if (!sticky) setTimeout(function () { box.remove(); }, kind === 'err' ? 8000 : 4000);
    $('#toasts').appendChild(box);
    return box;
  }

  // ------------------------------------------------------------ dirty/save
  function setSaveState(s, customText) {
    state.saveState = s;
    var el = $('#save-status');
    if (!el) return;
    el.setAttribute('data-state', s);
    el.textContent = customText || ({
      unsaved: 'Chưa lưu',
      saving: 'Đang lưu…',
      saved: 'Đã lưu lúc ' + new Date().toLocaleTimeString(),
      error: 'Lỗi lưu'
    })[s] || s;
  }

  function markDirty() {
    state.dirty = true;
    setSaveState('unsaved');
    scheduleAutosave();
  }

  function persistLocal() {
    try {
      localStorage.setItem('hoso_draft_autosave', JSON.stringify(draftPayload()));
      return true;
    } catch (e) { return false; } // localStorage đầy/không khả dụng
  }

  function scheduleAutosave() {
    clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(function () {
      setSaveState('saving');
      // thành công mới dirty=false; thất bại giữ dirty=true + báo lỗi lưu
      var oc = saveOutcome(persistLocal());
      state.dirty = oc.dirty;
      setSaveState(oc.saveState);
    }, 800);
  }

  /* Ctrl+S / nút Lưu: ghi ngay không chờ debounce. */
  function quickSave() {
    clearTimeout(state.autosaveTimer);
    setSaveState('saving');
    var oc = saveOutcome(persistLocal());
    state.dirty = oc.dirty;
    setSaveState(oc.saveState);
  }

  // ------------------------------------------------------------ nạp dữ liệu
  function loadMockJson(id) {
    return fetch('mock/blocks_' + id + '.json').then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function getBlocks(ids) {
    if (state.mock) {
      return Promise.all(ids.map(function (id) {
        return loadMockJson(id).then(function (doc) {
          return { doc: doc, error: null };
        }).catch(function (e) {
          return { doc: null, error: id + ': ' + e.message };
        });
      }));
    }
    return Promise.resolve(api().get_blocks(JSON.stringify(ids))).then(function (res) {
      if (typeof res === 'string') res = JSON.parse(res);
      var docs = res.docs || {};
      var errors = res.errors || [];
      return ids.map(function (id) {
        return docs[id]
          ? { doc: docs[id], error: null }
          : { doc: null, error: id + ': ' + (errors[id] || 'không có blocks') };
      });
    });
  }

  /* PHASE 6: nạp metadata field-grid cho một mẫu (app/data/ui_layouts/<id>.json).
   * Thử đường canonical '../app/data/ui_layouts/' trước; fallback bản sao local
   * 'ui_layouts/<id>.json' (chế độ mock/gói độc lập); 404/lỗi -> cache null và
   * render như cũ (bỏ qua layout, không bao giờ chặn việc nạp mẫu). */
  function loadUiLayout(id) {
    if (Object.prototype.hasOwnProperty.call(state.uiLayouts, id)) {
      return Promise.resolve(state.uiLayouts[id]);
    }
    var read = function (url) {
      return fetch(url).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
    };
    return read('../app/data/ui_layouts/' + id + '.json')
      .catch(function () { return read('ui_layouts/' + id + '.json'); })
      .then(function (j) { state.uiLayouts[id] = j || null; return j || null; })
      .catch(function () { state.uiLayouts[id] = null; return null; });
  }

  function loadCases() {
    if (state.mock) {
      state.cases = MOCK_CASES.slice();
      fillGroupAndCaseSelects();
      return;
    }
    var a = api();
    if (!a) {
      window.addEventListener('pywebviewready', function () { loadCases(); }, { once: true });
      return;
    }
    Promise.resolve(a.list_cases()).then(function (data) {
      if (typeof data === 'string') data = JSON.parse(data);
      state.cases = data.cases || [];
      fillGroupAndCaseSelects();
    }).catch(function (e) {
      toast('Lỗi nạp danh mục thủ tục: ' + esc(String(e)), 'err');
    });
  }

  function fillGroupAndCaseSelects() {
    var seen = {};
    state.groups = [];
    state.cases.forEach(function (c) {
      if (!seen[c.nhom]) { seen[c.nhom] = true; state.groups.push(c.nhom); }
    });
    $('#sel-nhom').innerHTML = state.groups.map(function (g) {
      return '<option value="' + esc(g) + '">' + esc(g) + '</option>';
    }).join('');
    onGroupChange();
  }

  function onGroupChange() {
    var g = $('#sel-nhom').value;
    var inG = state.cases.filter(function (c) { return c.nhom === g; });
    $('#sel-case').innerHTML = inG.map(function (c) {
      return '<option value="' + esc(c.id) + '">' + esc(c.ten) + '</option>';
    }).join('');
    if ($('#sel-case').value) onCaseChange(true);
  }

  function currentCase() {
    return state.cases.filter(function (c) { return c.id === state.caseId; })[0] || null;
  }

  function onCaseChange(keepSelectionIfSame) {
    var id = $('#sel-case').value;
    if (keepSelectionIfSame && id === state.caseId) return;
    if (state.caseId && state.dirty &&
        !confirm('Hồ sơ hiện tại chưa lưu. Đổi thủ tục sẽ mất dữ liệu chưa lưu. Tiếp tục?')) {
      // trả lại select theo case cũ
      var cs0 = currentCase();
      if (cs0) $('#sel-case').value = cs0.id;
      return;
    }
    state.caseId = id;
    // race guard: kết quả getBlocks của request CŨ resolve muộn thì bỏ qua
    var seq = RequestToken.next();
    var cs = currentCase();
    renderCaseInfo(cs);
    updateDocTitle();
    var wanted = formIds(cs);
    getBlocks(wanted).then(function (results) {
      if (!RequestToken.fresh(seq)) return; // case cũ muộn: KHÔNG ghi state
      state.docs = [];
      results.forEach(function (r) {
        if (r.doc) state.docs.push(r.doc);
        else toast('Không nạp được mẫu: ' + esc(r.error), 'err');
      });
      // giữ metadata từng form (bat_buoc/nhóm oneOf) vào state theo docId
      state.formMeta = buildFormMeta(cs);
      // PHASE 6: nạp ui_layouts (nếu có) trước khi render; thiếu -> bỏ qua
      Promise.all(state.docs.map(function (d) { return loadUiLayout(d.id); }))
        .then(function () {
          if (!RequestToken.fresh(seq)) return; // vẫn chặn sau các await
          if (state.pendingDraft) { finishApplyDraft(); return; }
          var sel = restoreSelection(state.formMeta, state.docs, null);
          state.checkedForms = sel.checkedForms;
          state.activeDocId = sel.activeDocId;
          state.errors = [];
          state.selectedLoopRow = {};
          state.selRowId = {};
          state.multiSel = {};
          renderAllPages();
        });
    });
  }

  function renderCaseInfo(cs) {
    var el = $('#case-info');
    if (!cs) { el.innerHTML = ''; return; }
    var html = '<h3>' + esc(cs.ten) + '</h3>';
    if (cs.mo_ta) html += '<p>' + esc(cs.mo_ta) + '</p>';
    if ((cs.giay_to_kem || []).length) {
      html += '<div class="lbl">Giấy tờ nộp kèm</div><ul>' +
        cs.giay_to_kem.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
    }
    if ((cs.luu_y || []).length) {
      html += '<div class="lbl">Lưu ý</div>' +
        cs.luu_y.map(function (x) { return '<div class="warn-box">' + esc(x) + '</div>'; }).join('');
    }
    if ((cs.co_so_phap_ly || []).length) {
      html += '<div class="lbl">Căn cứ pháp lý</div><ul>' +
        cs.co_so_phap_ly.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
    }
    el.innerHTML = html;
  }

  function updateDocTitle() {
    var cs = currentCase();
    var d = activeDoc();
    var t = [];
    if (cs) t.push(cs.ten);
    if (d) t.push(d.ten_mau || d.id);
    $('#doc-title').textContent = t.join(' · ');
  }

  function renderFormList() {
    // DOM chỉ phản chiếu state.checkedForms (nguồn chân lý); bắt buộc luôn
    // checked+disabled, tùy chọn unchecked trừ khi draft/user đã chọn
    $('#form-list').innerHTML =
      formListHtml(state.docs, state.formMeta, state.checkedForms);
  }

  function visibleDocs() {
    return state.docs.filter(function (d) { return !!state.checkedForms[d.id]; });
  }

  function activeDoc() {
    return state.docs.filter(function (d) { return d.id === state.activeDocId; })[0] || null;
  }

  function shortName(d) {
    var m = d.ten_mau || d.id;
    return m.length > 34 ? m.slice(0, 33) + '…' : m;
  }

  // ------------------------------------------- render một tờ khai active
  function captureViewState() {
    if (!state.activeDocId) return;
    var scroller = $('#scroller');
    var ae = document.activeElement;
    var fk = (ae && ae.getAttribute) ? ae.getAttribute('data-field-id') : null;
    state.viewState[state.activeDocId] = { scrollTop: scroller.scrollTop, focusKey: fk || null };
  }

  /* Map gridMeta cho MỘT mẫu: GRID_META toàn cục + overlay form-scoped
   * (FD.FORM_GRID_META[docId].loops - resolve theo docId). Renderer vẫn
   * GENERIC: chỉ đọc map {loop: meta} này, không biết gì về form ID. */
  function gridMetaForDoc(docId) {
    var m = Object.assign({}, FD.GRID_META);
    var fm = FD.FORM_GRID_META && FD.FORM_GRID_META[docId];
    if (fm && fm.loops) Object.assign(m, fm.loops);
    return m;
  }

  /* P2 R2 runtime wiring: chính sách CRUD dòng theo SECTION KIND.
   * - nested-grid : add/delete/reorder theo policy contract (giữ _row_id).
   * - fixed-matrix: KHÔNG add/delete/reorder dòng pháp lý (policy=false).
   * - output-table: không có dòng dữ liệu nào.
   * Trả null cho loop editable-grid/schema legacy -> caller dùng GridCtl.meta
   * như cũ, hành vi cũ KHÔNG đổi một bit. Thuần (node test qua Helpers). */
  function sectionRowMeta(docId, loop) {
    var e = FD.sectionContractForLoop(docId, loop);
    if (!e) return null;
    var spec = e.spec || {};
    var pol = e.policy || {};
    return {
      kind: e.kind,
      semanticKey: spec.semantic_key,
      label: (spec.section_id || spec.semantic_key) + ' (' + e.kind + ')',
      allowAdd: pol.allowAdd !== false && e.kind === 'nested-grid',
      allowDelete: pol.allowDelete !== false && e.kind === 'nested-grid',
      allowReorder: pol.allowReorder !== false && e.kind === 'nested-grid',
      confirmDeleteNonEmpty: pol.confirmDeleteNonEmpty !== false,
      maxRows: spec.max_rows != null ? spec.max_rows :
        (spec.maxRows != null ? spec.maxRows : null),
      columns: (spec.columns || []).map(function (c) {
        return { tag: c.tag,
          type: c.type === 'stt' ? 'readonly' : (c.type || 'text'),
          outputOnly: !!(c.outputOnly || c.output_only) };
      })
    };
  }

  /* Metadata DÙNG CHO row-op/focus: section kind mới ưu tiên; bảng cũ rơi về
   * resolver editable-grid hiện hành. */
  function rowOpMeta(loop) {
    return sectionRowMeta(state.activeDocId, loop) ||
      GridCtl.meta(loop, state.activeDocId);
  }

  /* Text hiển thị ô tổng outputOnly từ projection {value, inputType}. */
  function componentComputedText(proj) {
    if (!proj || proj.value == null) return '';
    if (proj.inputType === 'money') return R.formatVnd(proj.value);
    return String(proj.value);
  }

  /* Điền lại giá trị ô tổng (data-computed-key) sau mỗi thay đổi store. Chỉ
   * GHI VÀO DOM readonly cell: draft luôn giữ dữ liệu người dùng nhập, con số
   * tổng luôn là projection recompute -> không thể có hai nguồn lệch nhau. */
  function refreshComponentComputed() {
    var docId = state.activeDocId;
    if (!docId) return;
    var proj = FD.recomputeSections(docId, state.store);
    Object.keys(proj).forEach(function (keyPath) {
      var text = componentComputedText(proj[keyPath]);
      document.querySelectorAll(
        '#pages [data-computed-key="' + cssEsc(keyPath) + '"]').forEach(function (el) {
          if (el.textContent !== text) el.textContent = text;
        });
    });
  }

  function renderActiveDoc() {
    var d = activeDoc();
    var pages = $('#pages');
    if (!d) {
      pages.innerHTML = '<section class="page-a4"><p class="bp bp-center rn-i">' +
        '(Chưa chọn mẫu biểu nào)</p></section>';
      return;
    }
    // R2: mọi dòng lặp mang _row_id ổn định trước khi render (idempotent)
    GridCtl.ensureIds(state.store);
    // P1.2 Option D: selector metadata hồ sơ (vd M72 'Loại hình doanh
    // nghiệp') + flags điều kiện render - block cond không thoả bị bỏ khỏi
    // UI nên CHỈ biến thể đang chọn được render.
    var sel = FD.getFormSelector(d.id);
    var selHtml = sel ? R.selectorHtml(sel, R.makeAccessors(state.store)) : '';
    pages.innerHTML = '<section class="page-a4" id="doc_' + esc(d.id) +
      '" data-doc="' + esc(d.id) + '" tabindex="-1">' +
      R.renderBlocks(d, state.store, {
        docId: d.id, fieldMeta: FD.FIELD_META, gridMeta: gridMetaForDoc(d.id),
        uiLayout: state.uiLayouts[d.id] || null,
        sectionContracts: FD.sectionContractsOf(d.id),
        flags: FD.selectorFlagsOf(d.id, state.store),
        selectorHtml: selHtml
      }) +
      '</section>';
    /* F-P3-A11Y-LABEL: nhãn cho checkbox .chk-box gắn ở bước enhancement DOM
     * (HTML renderer giữ nguyên cho caller cũ — xem render.enhanceChkLabels). */
    R.enhanceChkLabels(pages);
    enhanceEditableGrids();
    applyReadonlyTotals();
    refreshComponentComputed();
    patchErrorsDom();
  }

  /* Số cột VẬT LÝ của bảng: duyệt header grid, cộng dồn chiếm chỗ qua
   * colspan/rowspan (cùng thuật toán với loopHeaderGrid của renderer để hai
   * đường render/enhance không lệch nhau). Không có thead -> lấy max ô/tr. */
  function tableColCount(table) {
    var head = table.tHead;
    if (!head || !head.rows.length) {
      var maxCells = 0;
      Array.prototype.forEach.call(table.rows, function (tr) {
        if (tr.cells.length > maxCells) maxCells = tr.cells.length;
      });
      return maxCells;
    }
    var occ = {}, nCols = 0;
    Array.prototype.forEach.call(head.rows, function (tr, ri) {
      var col = 0;
      Array.prototype.forEach.call(tr.cells, function (cell) {
        while (occ[ri + ':' + col]) col++;
        var cs = Math.max(1, cell.colSpan | 0 || 1);
        var rs = Math.max(1, cell.rowSpan | 0 || 1);
        for (var dr = 0; dr < rs; dr++) {
          for (var dc = 0; dc < cs; dc++) occ[(ri + dr) + ':' + (col + dc)] = true;
        }
        col += cs;
      });
      var w = 0;
      while (occ[ri + ':' + w]) w++;
      if (w > nCols) nCols = w;
    });
    return nCols;
  }

  /* R2.2: add grid semantics after the shared renderer emits production HTML.
   * The renderer remains unchanged and older callers still receive identical
   * data attributes/content. F-P3-A11Y-TABLE: role=grid + aria-colcount (cột
   * vật lý) + aria-rowcount (header + dòng hiện có) — gọi lại sau MỌI lần
   * render lại (thêm/xóa dòng đi qua renderActiveDoc) nên rowcount luôn khớp. */
  function enhanceEditableGrids() {
    document.querySelectorAll('#pages table.loop-table').forEach(function (table) {
      table.setAttribute('role', 'grid');
      table.setAttribute('aria-colcount', String(tableColCount(table)));
      var allRows = table.querySelectorAll('thead tr, tbody tr');
      table.setAttribute('aria-rowcount', String(allRows.length));
      allRows.forEach(function (tr, ri) {
        tr.setAttribute('role', 'row');
        tr.setAttribute('aria-rowindex', String(ri + 1));
        Array.prototype.forEach.call(tr.children, function (cell, ci) {
          cell.setAttribute('aria-colindex', String(ci + 1));
          cell.setAttribute('role', cell.tagName.toLowerCase() === 'th' ? 'columnheader' : 'gridcell');
        });
      });
    });
  }

  function updateTabsSelection(focusCurrent) {
    var tabs = document.querySelectorAll('#tabs [role="tab"]');
    tabs.forEach(function (tab) {
      var sel = tab.getAttribute('data-doc-id') === state.activeDocId;
      tab.setAttribute('aria-selected', sel ? 'true' : 'false');
      tab.classList.toggle('active', sel);
      tab.tabIndex = sel ? 0 : -1;
      if (sel && focusCurrent) tab.focus();
    });
  }

  function renderTabs() {
    var docs = visibleDocs().map(function (d) {
      return { id: d.id, ten_mau: shortName(d) };
    });
    $('#tabs').innerHTML = R.buildTabsHtml(docs);
    renderTabBadges();
    updateTabsSelection(false);
  }

  function setActiveDoc(id, opts) {
    opts = opts || {};
    if (!state.docs.some(function (d) { return d.id === id; })) return;
    captureViewState();
    state.activeDocId = id;
    renderActiveDoc();
    updateTabsSelection(false);
    updateDocTitle();
    var vs = state.viewState[id];
    var scroller = $('#scroller');
    scroller.scrollTop = opts.restoreScroll && vs ? vs.scrollTop : 0;
    if (opts.restoreFocus && vs && vs.focusKey) {
      var el = document.querySelector('[data-field-id="' + cssEsc(vs.focusKey) + '"]');
      if (el) { el.focus(); return; }
    }
    if (opts.focusPage) {
      var page = document.querySelector('#pages .page-a4');
      if (page) page.focus({ preventScroll: false });
    }
  }

  function renderAllPages(opts) {
    opts = opts || {};
    renderFormList();
    if (!visibleDocs().some(function (d) { return d.id === state.activeDocId; })) {
      state.activeDocId = visibleDocs().length ? visibleDocs()[0].id : null;
    }
    renderActiveDoc();
    renderTabs();
    updateDocTitle();
    if (opts.keepScroll) return; // caller tự quản scroll
    $('#scroller').scrollTop = 0;
  }

  function applyReadonlyTotals() {
    document.querySelectorAll('#pages .fld.calc').forEach(function (inp) {
      var key = inp.getAttribute('data-key');
      inp.readOnly = state.autoSum &&
        (key === 'von_dieu_le' || key === 'von_kinh_doanh');
    });
  }

  // ------------------------------------------------------- store <-> input
  function parseLoopKey(key) {
    if (key.indexOf('loop:') !== 0) return null;
    var p = key.split(':');           // loop:<name>:<idx>:<tag>
    return { loop: p[1], idx: +p[2], tag: p[3] };
  }

  function setKeyValue(key, value) {
    var lk = parseLoopKey(key);
    if (lk) {
      var rows = state.store.loops[lk.loop] = state.store.loops[lk.loop] || [];
      while (rows.length <= lk.idx) rows.push({});
      rows[lk.idx][lk.tag] = value;
    } else {
      state.store.values[key] = value;
    }
  }

  function getKeyValue(key) {
    var lk = parseLoopKey(key);
    if (lk) return ((state.store.loops[lk.loop] || [])[lk.idx] || {})[lk.tag] || '';
    return state.store.values[key] == null ? '' : state.store.values[key];
  }

  /* Một key chung một giá trị: cập nhật mọi input khác cùng data-key. */
  function mirrorKey(key, exceptEl) {
    var val = getKeyValue(key);
    document.querySelectorAll('#pages [data-key="' + cssEsc(key) + '"]').forEach(function (el) {
      if (el === exceptEl || el === document.activeElement) return;
      if (el.type === 'checkbox') el.checked = !!val;
      else el.value = val;
    });
  }

  // ------------------------------------------------------------- tự tính
  function runAutoFills() {
    state.store = R.applyAutoFills(state.store, state.autoSum);
    Object.keys(state.store.values).forEach(function (key) {
      if (R.AUTO_KEYS[key]) mirrorKey(key);
    });
    applyReadonlyTotals();
    // R2: tổng outputOnly của fixed-matrix luôn là projection recompute
    refreshComponentComputed();
  }

  function validateAllMaNganh() {
    document.querySelectorAll('#pages .vsic-fld[data-tag="ma_nganh"]').forEach(function (inp) {
      var ok = R.isValidMaNganh(state.vsic, inp.value);
      inp.classList.toggle('invalid', !ok);
    });
  }

  // ------------------------------------------------------------- bảng lặp
  function rowHasData(r) {
    return Object.keys(r || {}).some(function (k) {
      if (k.charAt(0) === '_') return false; // _row_id không tính là dữ liệu
      return String(r[k] == null ? '' : r[k]).trim() !== '';
    });
  }

  /* Chọn dòng: click thường -> chọn 1 (reset multi); Ctrl+click -> toggle
   * chọn nhiều để Xóa nhiều dòng confirm MỘT lần. */
  function selectRow(tr, e) {
    var table = tr.closest('.loop-table');
    var loop = tr.getAttribute('data-loop');
    var id = tr.getAttribute('data-row-id') || null;
    var idx = +tr.getAttribute('data-row-index');
    var multi = state.multiSel[loop] = state.multiSel[loop] || {};
    if (!id) { // dòng blank ngoài store: chỉ highlight, không vào selection
      table.querySelectorAll('tbody tr').forEach(function (r) {
        r.classList.remove('row-sel', 'row-sel-multi');
        r.setAttribute('aria-selected', 'false');
      });
      tr.classList.add('row-sel');
      tr.setAttribute('aria-selected', 'true');
      state.selRowId[loop] = null;
      state.selectedLoopRow[loop] = idx;
      return;
    }
    if (e && e.ctrlKey) {
      if (multi[id]) {
        delete multi[id];
        tr.classList.remove('row-sel-multi');
        if (state.selRowId[loop] === id) state.selRowId[loop] = null;
      } else {
        multi[id] = true;
        tr.classList.add('row-sel-multi');
        state.selRowId[loop] = id;
        state.selectedLoopRow[loop] = idx;
      }
      return;
    }
    // click thường: chọn 1
    Object.keys(multi).forEach(function (k) { delete multi[k]; });
    table.querySelectorAll('tbody tr').forEach(function (r) {
      var sel = r === tr;
      r.classList.toggle('row-sel', sel);
      r.classList.remove('row-sel-multi');
      r.setAttribute('aria-selected', sel ? 'true' : 'false');
    });
    state.selRowId[loop] = id;
    state.selectedLoopRow[loop] = idx;
  }

  function clearLoopSelection(loop) {
    state.selRowId[loop] = null;
    delete state.selectedLoopRow[loop];
    state.multiSel[loop] = {};
  }

  /* Dòng đích cho del/up/down/dup khi chưa chọn: dòng dữ liệu CUỐI. */
  function targetRowId(loop) {
    var id = state.selRowId[loop];
    var rows = state.store.loops[loop] || [];
    if (id && GridCtl.findRowIndex(rows, id) >= 0) return id;
    var last = rows[rows.length - 1];
    return last ? last._row_id : null;
  }

  // ------------------------------------- focus sau row operation (P2.0)
  /* [PURE] Tag ô đích focus sau ADD/DUPLICATE, suy từ metadata bảng:
   *  - grid có cột ma_nganh -> 'ma_nganh' (ô mã ngành của dòng mới, ưu tiên
   *    cao nhất bất kể vị trí cột - vd nganh_bo_sung có ten_nganh editable
   *    đứng trước vẫn focus mã ngành);
   *  - ngược lại -> tag EDITABLE ĐẦU TIÊN theo meta columns (bỏ qua loại
   *    readonly/outputOnly/radio/checkbox - không phải ô gõ được);
   *  - không suy được (meta thiếu/rỗng) -> null, caller fallback DOM. */
  function focusTagOfGrid(gm) {
    var cols = (gm && gm.columns) || [];
    for (var i = 0; i < cols.length; i++) {
      if (cols[i] && cols[i].tag === 'ma_nganh') return 'ma_nganh';
    }
    for (var j = 0; j < cols.length; j++) {
      var c = cols[j];
      if (!c || !c.tag) continue;
      var t = c.type || 'text';
      if (t === 'readonly' || t === 'outputOnly' ||
          t === 'radio' || t === 'checkbox') continue;
      return c.tag;
    }
    return null;
  }

  /* [PURE] _row_id cần GIỮ selection/focus sau DELETE:
   *  - id đang chọn còn tồn tại trong rowsAfter -> giữ nguyên;
   *  - bị xóa (hoặc chưa chọn) -> dòng KỀ theo index cũ trong rowsBefore,
   *    clamp về cuối để không trỏ ra ngoài;
   *  - bảng rỗng sau xóa -> null. Không bao giờ ném exception. */
  function nextSelAfterDelete(rowsBefore, rowsAfter, prevRowId) {
    function idx(rows, id) {
      for (var i = 0; i < rows.length; i++) {
        if (rows[i] && rows[i]._row_id === id) return i;
      }
      return -1;
    }
    if (!rowsAfter || !rowsAfter.length) return null;
    if (prevRowId && idx(rowsAfter, prevRowId) >= 0) return prevRowId;
    var at = prevRowId ? idx(rowsBefore || [], prevRowId) : -1;
    if (at < 0) at = (rowsBefore || []).length - 1;
    if (at < 0) at = 0;
    var row = rowsAfter[Math.min(at, rowsAfter.length - 1)];
    return (row && row._row_id) ? row._row_id : null;
  }

  /* Focus một dòng của bảng lặp sau row-op (DOM): tìm tr theo _row_id
   * (fallback theo index khi row vừa render chưa kịp mang id), rồi chọn ô:
   *  1. [data-tag=tag] nếu caller chỉ định tag (focusTagOfGrid);
   *  2. input.loop-fld KHÔNG readonly đầu tiên của dòng (ten_nganh readonly
   *     của bảng ngành không bao giờ bị focus nhầm);
   *  3. input bất kỳ đầu dòng.
   * Trả true nếu đã focus; KHÔNG BAO GIỜ ném exception khi bảng rỗng/dòng
   * không tồn tại/DOM lạ - thao tác row-op phải luôn thành công kể cả khi
   * focus thất bại. */
  function focusGridRow(loop, opts) {
    try {
      opts = opts || {};
      var tbl = document.querySelector(
        '.loop-table[data-loop="' + cssEsc(loop) + '"]');
      if (!tbl) return false;
      var tr = ((opts.rowId != null) &&
        tbl.querySelector('tr[data-row-id="' + cssEsc(opts.rowId) + '"]')) ||
        tbl.querySelectorAll('tbody tr')[opts.idx] || null;
      if (!tr) return false;
      var el = opts.tag ?
        tr.querySelector('[data-tag="' + cssEsc(opts.tag) + '"]') : null;
      if (!el) {
        var flds = tr.querySelectorAll('input.loop-fld');
        for (var i = 0; i < flds.length; i++) {
          // attr boolean: có mặt -> ''/giá trị nào đó; vắng -> null
          if (flds[i].getAttribute('readonly') == null) { el = flds[i]; break; }
        }
      }
      if (!el) el = tr.querySelector('input');
      if (!el) return false;
      if (typeof el.focus === 'function') el.focus();
      if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
      return true;
    } catch (e) {
      return false; // DOM lạ/bảng rỗng: bỏ qua, không chặn thao tác dữ liệu
    }
  }

  /* Pure index movement shared by keyboard UI and contract tests. */
  function gridNavigationIndex(row, col, key, rowCount, colCount) {
    var r = row, c = col;
    if (key === 'ArrowLeft') c--;
    else if (key === 'ArrowRight') c++;
    else if (key === 'ArrowUp') r--;
    else if (key === 'ArrowDown') r++;
    else return null;
    if (r < 0 || c < 0 || r >= rowCount || c >= colCount) return null;
    return { row: r, col: c };
  }

  function handleGridKeydown(e) {
    var input = e.target;
    if (!input || !input.matches || !input.matches(
      '.loop-table tbody input[data-key]')) return false;
    var tr = input.closest('tr');
    var table = input.closest('table.loop-table');
    if (!tr || !table) return false;
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    var row = rows.indexOf(tr);
    var td = input.closest('td');
    var currentCol = td ? (+td.getAttribute('aria-colindex') - 1) : -1;
    var colCount = tr.children.length;
    var target = gridNavigationIndex(row, currentCol, e.key, rows.length, colCount);
    if (!target) return false;
    var targetRow = rows[target.row];
    var targetCell = targetRow.children[target.col];
    var targetInput = targetCell && targetCell.querySelector('input[data-key]');
    if (!targetInput) return false;
    e.preventDefault();
    targetInput.focus();
    return true;
  }

  function uiAddRow(loop) {
    var gm = rowOpMeta(loop); // R2: policy theo section.kind (fixed-matrix chặn)
    if (gm && gm.allowAdd === false) return;
    var rows = state.store.loops[loop] || [];
    var gmMax = gm && gm.maxRows != null ? gm.maxRows : null;
    if (gmMax != null && rows.length >= gmMax) {
      toast('Bảng "' + ((gm && gm.label) || loop) + '" tối đa ' + gmMax + ' dòng.', 'err');
      return;
    }
    var res = GridCtl.addRow(state.store, loop,
      targetRowId(loop)); // thêm sau dòng đang chọn / cuối nếu chưa chọn
    clearLoopSelection(loop);
    state.selRowId[loop] = res.id;
    markDirty();
    rerenderKeepView();
    // P2.0: grid có ma_nganh -> focus ô mã ngành dòng mới; không có -> ô
    // editable đầu theo meta (fallback input.loop-fld đầu dòng trong DOM)
    focusGridRow(loop, { rowId: res.id, idx: res.index, tag: focusTagOfGrid(gm) });
  }

  function uiDeleteRows(loop) {
    var gm = rowOpMeta(loop); // R2: fixed-matrix KHÔNG xóa dòng pháp lý
    if (gm && gm.allowDelete === false) return;
    var rows = state.store.loops[loop] || [];
    if (!rows.length) return;
    var label = (gm && gm.label) || loop;
    // P2.0: chụp selection TRƯỚC khi xóa để focus/selection bám _row_id
    var beforeRows = rows.slice();
    var prevId = targetRowId(loop);
    var multi = Object.keys(state.multiSel[loop] || {}).filter(function (id) {
      return GridCtl.findRowIndex(rows, id) >= 0;
    });
    var ids = multi.length > 1 ? multi : [targetRowId(loop)].filter(Boolean);
    if (!ids.length) ids = [rows[rows.length - 1]._row_id];
    if (!ids.length) return;
    if (ids.length > 1) {
      // xóa nhiều dòng: xác nhận MỘT lần kèm số dòng
      if (!confirm('Xóa ' + ids.length + ' dòng đã chọn của bảng "' + label +
          '"?\nThao tác này không thể hoàn tác.')) return;
    } else {
      var ix = GridCtl.findRowIndex(rows, ids[0]);
      var hasData = rowHasData(rows[ix]);
      var needConfirm = !gm || gm.confirmDeleteNonEmpty !== false;
      if (hasData && needConfirm &&
          !confirm('Dòng ' + (ix + 1) + ' của "' + label + '" đang có dữ liệu.\n' +
            (loop === 'ds_nganh'
              ? ('Ngành sắp xóa: ' +
                 [rows[ix].ma_nganh, rows[ix].ten_nganh].filter(Boolean).join(' - ') + '.\n')
              : '') +
            'Xóa dòng này?')) {
        return; // cancel -> không mất dữ liệu
      }
    }
    GridCtl.deleteRows(state.store, loop, ids);
    // P2.0: selection/focus bám _row_id - id đang chọn còn sống thì giữ,
    // bị xóa thì dòng kề theo index an toàn (clamp cuối); bảng rỗng -> bỏ
    var afterRows = state.store.loops[loop] || [];
    var nid = nextSelAfterDelete(beforeRows, afterRows, prevId);
    clearLoopSelection(loop);
    if (nid) {
      state.selRowId[loop] = nid;
      state.selectedLoopRow[loop] = GridCtl.findRowIndex(afterRows, nid);
    }
    markDirty();
    rerenderKeepView();
    focusGridRow(loop, {
      rowId: nid,
      idx: nid != null ? state.selectedLoopRow[loop] : 0,
      tag: focusTagOfGrid(gm)
    });
  }

  function uiClearRows(loop) {
    var gm = rowOpMeta(loop); // R2: policy theo section.kind
    if (gm && gm.allowDelete === false) return;
    var rows = state.store.loops[loop] || [];
    if (!rows.length) return;
    var label = (gm && gm.label) || loop;
    // xác nhận rõ phạm vi trước khi xóa tất cả
    if (!confirm('Xóa TẤT CẢ dữ liệu (' + rows.length + ' dòng) của bảng "' + label +
        '"?\nChỉ xóa dữ liệu kê khai, bảng vẫn giữ lại dòng trống trên giao diện.')) return;
    GridCtl.clearRows(state.store, loop);
    clearLoopSelection(loop);
    markDirty();
    rerenderKeepView();
  }

  function uiMoveRow(loop, dir) {
    var gm = rowOpMeta(loop); // R2: fixed-matrix/output-table KHÔNG reorder
    if (gm && gm.allowReorder === false) return;
    var id = targetRowId(loop);
    if (!id) return;
    var at = GridCtl.moveRow(state.store, loop, id, dir);
    if (at < 0) return;
    state.selRowId[loop] = id; // P2.0: selection bám _row_id, không theo index
    state.selectedLoopRow[loop] = at; // _row_id giữ nguyên -> lỗi vẫn đúng dòng
    markDirty();
    rerenderKeepView();
    // P2.0: focus đi CÙNG dòng vừa di chuyển (tra cứu lại theo _row_id sau
    // rerender nên không bao giờ trỏ sai row khi thứ tự đã đổi)
    focusGridRow(loop, { rowId: id, idx: at, tag: focusTagOfGrid(gm) });
  }

  function uiDuplicateRow(loop) {
    var gm = rowOpMeta(loop); // R2: policy theo section.kind
    if (gm && gm.allowAdd === false) return;
    var id = targetRowId(loop);
    if (!id) return;
    var res = GridCtl.duplicateRow(state.store, loop, id, state.activeDocId);
    if (!res) return;
    clearLoopSelection(loop);
    state.selRowId[loop] = res.id;
    state.selectedLoopRow[loop] = res.index;
    markDirty();
    rerenderKeepView();
    focusGridRow(loop, { rowId: res.id, idx: res.index, tag: focusTagOfGrid(gm) });
  }

  function handleLoopAction(btn) {
    var act = btn.getAttribute('data-act');
    var loop = btn.getAttribute('data-loop') ||
      (btn.closest('.loop-btns') && btn.closest('.loop-btns').getAttribute('data-loop'));
    if (!loop) return;
    if (act === 'add') uiAddRow(loop);
    else if (act === 'del') uiDeleteRows(loop);
    else if (act === 'clear') uiClearRows(loop);
    else if (act === 'up') uiMoveRow(loop, -1);
    else if (act === 'down') uiMoveRow(loop, 1);
    else if (act === 'dup') uiDuplicateRow(loop);
  }

  /* Rerender tờ khai active giữ nguyên scroll (thêm/xóa dòng). */
  function rerenderKeepView() {
    var top = $('#scroller').scrollTop;
    renderActiveDoc();
    runAutoFills();
    $('#scroller').scrollTop = top;
  }

  // ------------------------------------------------------------- tra cứu VSIC
  var pop = null;
  function hideVsic() {
    if (pop) {
      pop.hidden = true;
      state.vsicItems = [];
      state.vsicIndex = 0;
    }
  }

  function showVsic(anchor, query, onPick) {
    var items = R.searchVsic(state.vsic, query, 12);
    state.vsicItems = items;
    state.vsicIndex = 0;
    pop = $('#vsic-pop');
    pop.innerHTML = items.length
      ? items.map(function (x, i) {
          return '<div class="vsic-item' + (i === 0 ? ' sel' : '') +
            '" role="option" aria-selected="' + (i === 0 ? 'true' : 'false') +
            '" data-i="' + i + '">' +
            '<span class="ma">' + esc(x.ma) + '</span>' + esc(x.ten) + ' <i>(cấp ' + x.cap + ')</i></div>';
        }).join('')
      : '<div id="vsic-empty">Không tìm thấy mã ngành phù hợp</div>';
    pop.hidden = false;
    var r = anchor.getBoundingClientRect();
    pop.style.left = Math.min(r.left, window.innerWidth - 340) + 'px';
    pop.style.top = (r.bottom + 2) + 'px';
    pop.onmousedown = function (e) {
      var item = e.target.closest('.vsic-item');
      if (!item) return;
      e.preventDefault();               // giữ focus của ô nhập
      onPick(items[+item.getAttribute('data-i')]);
      hideVsic();
    };
  }

  function vsicHighlight(idx) {
    var items = pop.querySelectorAll('.vsic-item');
    if (!items.length) return;
    if (idx < 0) idx = items.length - 1;
    if (idx >= items.length) idx = 0;
    state.vsicIndex = idx;
    items.forEach(function (el, i) {
      el.classList.toggle('sel', i === idx);
      el.setAttribute('aria-selected', i === idx ? 'true' : 'false');
    });
    items[idx].scrollIntoView({ block: 'nearest' });
  }

  function isNganhTag(tag) { return tag === 'ma_nganh' || tag === 'ten_nganh'; }

  function loopCellDom(key, val, exceptEl) {
    document.querySelectorAll('#pages [data-key="' + cssEsc(key) + '"]').forEach(function (el) {
      if (el === exceptEl) return;
      el.value = val;
    });
  }

  /* Chọn 1 kết quả từ popup (chuột hoặc Enter): điền CẢ mã + tên vào cùng
   * dòng, gỡ đỏ, đóng popup. Tên ghi đúng tag của loop theo metadata
   * autoName.nameTag (vd PLII_M02: ten_nganh_bo_sung/ten_nganh_bo). */
  function applyVsicPick(inp, item) {
    var lk = parseLoopKey(inp.getAttribute('data-key'));
    if (!lk || !item) return;
    var gm = GridCtl.meta(lk.loop, state.activeDocId);
    var nameTag = (gm && gm.autoName && gm.autoName.nameTag) || 'ten_nganh';
    ['ma_nganh', nameTag].forEach(function (t) {
      var key = 'loop:' + lk.loop + ':' + lk.idx + ':' + t;
      setKeyValue(key, item[t]);
      loopCellDom(key, item[t], t === 'ma_nganh' ? inp : null);
    });
    inp.classList.remove('invalid');
    inp.removeAttribute('aria-invalid');
    hideVsic();
    validateAllMaNganh();
    markDirty();
  }

  /* Luồng nhập MÃ ngành (PLAN.md PHASE 4):
   *  - rỗng        -> xóa ten_nganh cùng dòng + gỡ invalid;
   *  - đủ mã khớp  -> tự điền ten chính thức ngay, đóng popup, gỡ đỏ;
   *  - 1-3 chữ số  -> mở gợi ý nhưng KHÔNG báo blocking;
   *  - sai/không có-> giữ giá trị, viền đỏ (VSIC_INVALID), KHÔNG tự chế tên,
   *                  xóa tên cũ của mã khác (đổi mã thì tên phải cập nhật). */
  function handleMaNganhInput(inp, fromFocus) {
    if (inp.getAttribute('data-tag') !== 'ma_nganh') return false;
    var lk = parseLoopKey(inp.getAttribute('data-key'));
    if (!lk) return false;
    // tên điền cùng dòng theo đúng tag của loop (autoName trong metadata)
    var gm = GridCtl.meta(lk.loop, state.activeDocId);
    var nameTag = (gm && gm.autoName && gm.autoName.nameTag) || 'ten_nganh';
    var tenKey = 'loop:' + lk.loop + ':' + lk.idx + ':' + nameTag;
    var res = GridCtl.vsicResolve(state.vsic, inp.value);
    if (res.st === 'empty') {
      setKeyValue(tenKey, '');
      loopCellDom(tenKey, '', inp);
      inp.classList.remove('invalid');
      inp.removeAttribute('aria-invalid');
      hideVsic();
      return true;
    }
    if (res.st === 'exact') {
      setKeyValue(tenKey, res.item.ten);
      loopCellDom(tenKey, res.item.ten, inp);
      inp.classList.remove('invalid');
      inp.removeAttribute('aria-invalid');
      hideVsic();
      markDirty();
      return true;
    }
    if (res.st === 'typing') {
      // đang gõ chưa đủ: chỉ gợi ý, không đánh lỗi
      inp.classList.remove('invalid');
      inp.removeAttribute('aria-invalid');
      showVsic(inp, inp.value, function (item) { applyVsicPick(inp, item); });
      return true;
    }
    // invalid: giữ giá trị để người dùng sửa; không giữ tên cũ
    setKeyValue(tenKey, '');
    loopCellDom(tenKey, '', inp);
    inp.classList.add('invalid');
    inp.setAttribute('aria-invalid', 'true');
    if (!fromFocus && res.items.length) {
      // vẫn gợi ý theo tiền tố/tên để đỡ gõ lại; chọn sẽ sửa cả mã
      showVsic(inp, inp.value, function (item) { applyVsicPick(inp, item); });
    } else {
      hideVsic();
    }
    markDirty();
    return true;
  }

  function handleVsicKeydown(e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('vsic-fld')) return false;
    if (!pop || pop.hidden) {
      if (e.key === 'ArrowDown' && String(inp.value || '').trim()) {
        handleMaNganhInput(inp, true) ||
          showVsic(inp, inp.value, function (item) { applyVsicPick(inp, item); });
        return true;
      }
      return false;
    }
    var n = pop.querySelectorAll('.vsic-item').length;
    if (!n) return false;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault(); vsicHighlight(state.vsicIndex + 1); return true;
      case 'ArrowUp':
        e.preventDefault(); vsicHighlight(state.vsicIndex - 1); return true;
      case 'Enter':
        e.preventDefault();
        var item = (state.vsicItems || [])[state.vsicIndex];
        if (item) applyVsicPick(inp, item);
        return true;
      case 'Escape':
        e.preventDefault(); hideVsic(); return true;
    }
    return false;
  }

  // ------------------------------------------------------------- validation
  /* Nhóm errors theo docId (giữ thứ tự xuất hiện) - hàm thuần để node-test. */
  function groupErrorsByDoc(errors) {
    var out = [];
    var byId = {};
    (errors || []).forEach(function (e) {
      var id = e.docId || '';
      if (!byId[id]) { byId[id] = { docId: id, errors: [] }; out.push(byId[id]); }
      byId[id].errors.push(e);
    });
    return out;
  }

  function ctxValidate() {
    return { vsicList: state.vsic && state.vsic.length ? state.vsic : null };
  }

  function runCheck(scopeAll) {
    var errs;
    if (scopeAll) errs = FD.validateDossier(visibleDocs(), state.store, ctxValidate());
    else {
      var d = activeDoc();
      if (!d) return;
      errs = FD.validateDocument(d.id, d.blocks, state.store, ctxValidate());
    }
    state.errors = errs;
    renderErrorPanel();
    patchErrorsDom();
    renderTabBadges();
    var blocking = errs.filter(function (e) { return e.severity === 'blocking'; }).length;
    if (!errs.length) toast('Không phát hiện lỗi.', 'ok');
    else toast('Phát hiện <b>' + errs.length + '</b> lỗi (' + blocking + ' chặn xuất).', errs.some(function (e) { return e.severity === 'blocking'; }) ? 'err' : '');
  }

  function renderErrorPanel() {
    var box = $('#err-list');
    if (!box) return;
    var groups = groupErrorsByDoc(state.errors);
    if (!groups.length) {
      box.innerHTML = '<div class="err-empty">Không có lỗi.</div>';
      return;
    }
    var titleOf = {};
    visibleDocs().forEach(function (d) { titleOf[d.id] = shortName(d); });
    box.innerHTML = groups.map(function (g) {
      return '<div class="err-group-title">' + esc(titleOf[g.docId] || g.docId || 'Hồ sơ') + '</div>' +
        g.errors.map(function (e) {
          return '<button type="button" role="listitem" class="err-item' +
            (e.severity === 'warning' ? ' warning' : '') +
            '" data-doc-id="' + esc(g.docId) + '" data-key="' + esc(e.key) + '">' +
            esc(e.message) + '</button>';
        }).join('');
    }).join('');
  }

  function renderTabBadges() {
    var counts = {};
    state.errors.forEach(function (e) {
      var id = e.docId || '';
      counts[id] = (counts[id] || 0) + 1;
    });
    document.querySelectorAll('#tabs [role="tab"]').forEach(function (tab) {
      var old = tab.querySelector('.tab-badge');
      if (old) old.remove();
      var n = counts[tab.getAttribute('data-doc-id')] || 0;
      if (n) {
        var b = document.createElement('span');
        b.className = 'tab-badge';
        b.textContent = String(n);
        tab.appendChild(b);
      }
    });
  }

  /* Đánh dấu ô lỗi trên tờ khai active: .invalid + aria-invalid + span msg. */
  function patchErrorsDom() {
    var page = $('#pages');
    page.querySelectorAll('.fld-msg').forEach(function (m) { m.remove(); });
    page.querySelectorAll('.invalid').forEach(function (el) {
      el.classList.remove('invalid');
      el.removeAttribute('aria-invalid');
      el.removeAttribute('aria-describedby');
    });
    state.errors.forEach(function (e) {
      if (!e.docId || e.docId !== state.activeDocId) return;
      var el = findErrorField(e);
      if (!el) return;
      el.classList.add('invalid');
      el.setAttribute('aria-invalid', 'true');
      var fid = el.getAttribute('data-field-id') ||
        ('f_' + R.sanitizeFieldId(el.getAttribute('data-key') || e.key));
      var mid = 'msg_' + fid;
      el.setAttribute('aria-describedby', mid);
      var msg = document.createElement('span');
      msg.id = mid;
      msg.className = 'fld-msg';
      msg.setAttribute('role', 'alert');
      msg.textContent = e.message;
      el.parentNode.insertBefore(msg, el.nextSibling);
    });
  }

  /* Key lỗi dạng:
   *  - loop:<loop>:<row_id>:<tag> : ô cụ thể của dòng theo STABLE ID -> resolve
   *    qua [data-row-id], nên reorder/xóa không làm lỗi trỏ sai dòng;
   *  - loop:<loop>:<row_id>       : input đầu tiên của dòng đó;
   *  - loop:<loop>                : bảng lỗi -> ô nhập đầu tiên của tbody;
   *  - loop:<loop>:<idx>:<tag> (idx số) : key legacy theo chỉ số hàng,
   *    resolve qua [data-key] như cũ;
   *  - <loop>.<tag>               : tổng hợp legacy -> ô đầu của tag. */
  function findErrorField(e) {
    var key = e.key || '';
    if (key.indexOf('loop:') === 0) {
      var p = key.split(':');
      var tbl0 = document.querySelector(
        '#pages .loop-table[data-loop="' + cssEsc(p[1] || '') + '"]');
      if (!tbl0) return null;
      if (p.length >= 4 && /^\d+$/.test(p[2])) { // key legacy theo chỉ số
        return document.querySelector('#pages [data-key="' + cssEsc(key) + '"]') ||
          tbl0.querySelector('tbody tr [data-tag="' + cssEsc(p[3]) + '"]');
      }
      if (p.length >= 4) {
        var tr4 = tbl0.querySelector('tr[data-row-id="' + cssEsc(p[2]) + '"]');
        if (!tr4) return null;
        return tr4.querySelector('[data-tag="' + cssEsc(p[3]) + '"]') ||
          tr4.querySelector('input');
      }
      if (p.length === 3) {
        var tr3 = tbl0.querySelector('tr[data-row-id="' + cssEsc(p[2]) + '"]');
        return tr3 ? tr3.querySelector('input') : null;
      }
      return tbl0.querySelector('tbody tr input');
    }
    if (key.indexOf('.') > 0 && key.split('.')[0] in (state.store.loops || {})) {
      // key tổng hợp dạng <loop>.<tag>: trỏ tới ô đầu tiên của tag đó
      var parts = key.split('.');
      var tbl = document.querySelector('#pages .loop-table[data-loop="' + cssEsc(parts[0]) + '"]');
      return tbl ? tbl.querySelector('[data-tag="' + cssEsc(parts[1]) + '"]') : null;
    }
    // field-grid (PHASE 6): cùng key có thể có ô gốc bị ẩn .dupe-anchor ->
    // ưu tiên ô HIỂN THỊ đầu tiên để scroll/focus có tác dụng
    var cands = document.querySelectorAll('#pages [data-key="' + cssEsc(key) + '"]');
    for (var ci = 0; ci < cands.length; ci++) {
      if (!(cands[ci].closest && cands[ci].closest('.dupe-anchor'))) return cands[ci];
    }
    return cands.length ? cands[0] : null;
  }

  function navigateToError(docId, key) {
    setActiveDoc(docId, {});
    // đợi render frame kế tiếp rồi cuộn + focus
    requestAnimationFrame(function () {
      var fake = { key: key, docId: docId };
      var el = findErrorField(fake);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.focus();
      }
    });
  }

  // ------------------------------------------------------------- draft v2
  function draftPayload() {
    return {
      v: 2,
      caseId: state.caseId,
      checkedForms: visibleDocs().map(function (d) { return d.id; }),
      activeDocId: state.activeDocId,
      autoSum: state.autoSum,
      viewState: state.viewState,
      store: JSON.parse(JSON.stringify(state.store)),
      savedAt: new Date().toISOString()
    };
  }

  function applyDraft(raw) {
    var draft = FD.migrateDraft(raw);
    if (!draft || !draft.store) {
      toast('Tệp hồ sơ không hợp lệ hoặc quá cũ.', 'err');
      return;
    }
    state.pendingDraft = draft;
    var cs = state.cases.filter(function (c) { return c.id === draft.caseId; })[0];
    if (cs) {
      if ($('#sel-nhom').value !== cs.nhom) {
        $('#sel-nhom').value = cs.nhom;
        onGroupChange();
      }
      $('#sel-case').value = cs.id;
      onCaseChange(false);
    } else {
      finishApplyDraft();
    }
  }

  /* Giai đoạn 2 của restore: docs đã nạp đúng case. */
  function finishApplyDraft() {
    var draft = state.pendingDraft;
    state.pendingDraft = null;
    if (!draft) return;
    state.autoSum = !!draft.autoSum;
    $('#chk-autosum').checked = state.autoSum;
    var st = draft.store;
    state.store = {
      values: Object.assign({}, st.values),
      checks: Object.assign({}, st.checks),
      loops: st.loops || {}
    };
    state.viewState = draft.viewState || {};
    GridCtl.ensureIds(state.store); // _row_id ổn định sau draft round-trip
    // khôi phục lựa chọn mẫu từ draft: bắt buộc luôn tick, tùy chọn theo
    // draft.checkedForms, oneOf loại trừ; activeDocId chỉ nhận doc hợp lệ
    // (renderFormList sẽ phản chiếu state.checkedForms ra checkbox)
    var sel = restoreSelection(state.formMeta, state.docs, draft);
    state.checkedForms = sel.checkedForms;
    state.activeDocId = sel.activeDocId;
    runAutoFills();
    renderAllPages();
    var vs = state.viewState[state.activeDocId];
    if (vs) $('#scroller').scrollTop = vs.scrollTop || 0;
    state.dirty = false;
    setSaveState('saved', 'Đã khôi phục hồ sơ');
  }

  // ------------------------------------------------------------- export
  /* buildExportData đi qua GridCtl.exportLoopsStrict - CHỐ DUY NHẤT của
   * đường export (P2.0): phát hiện xung đột contract export giữa các mẫu
   * (loop cùng tên, form-scoped meta khác nhau) -> ném lỗi có cấu trúc,
   * doExport bắt và chặn export LOUD thay vì âm thầm dùng meta mẫu đầu. */
  function buildExportData() {
    var data = {};
    Object.keys(state.store.values).forEach(function (k) {
      data[k] = state.store.values[k];
    });
    Object.keys(state.store.checks).forEach(function (k) {
      data[k] = state.store.checks[k] ? 'X' : '';
    });
    // P1.2 Option D: flags điều kiện vùng DOCX (vd M72 loai_hinh_*) suy từ
    // selector metadata của TỪNG mẫu đang chọn - engine chỉ xuất biến thể
    // có flag 'X'; grid inactive-theo-selector đã bị exportLoops lọc rows.
    visibleDocs().forEach(function (d) {
      Object.assign(data, FD.selectorFlagsOf(d.id, state.store));
    });
    // loops: bỏ _row_id/field nội bộ; la_nganh_chinh map 'X'/'' cho template
    // (đi qua GridCtl.exportLoopsStrict - chỗ duy nhất quyết định định dạng
    // payload + guard xung đột contract; resolve meta form-scoped theo các
    // mẫu đang chọn)
    var loops = GridCtl.exportLoopsStrict(state.store,
      visibleDocs().map(function (d) { return d.id; }));
    Object.keys(loops).forEach(function (name) {
      data[name] = loops[name];
    });
    return data;
  }

  function doExport() {
    if (state.mock) {
      toast('Đang ở chế độ <b>?mock=1</b>: chỉ có dữ liệu giả, chức năng xuất cần chạy qua <code>python app_web/main.py</code>.', 'err');
      return;
    }
    if (!visibleDocs().length) {
      toast('Chưa chọn mẫu biểu nào để xuất.', 'err');
      return;
    }
    // CHÍNH SÁCH CHẶN EXPORT: còn lỗi blocking (của field LẪN LỰA CHỌN MẪU)
    // thì không gọi Bridge.export. Gate chọn mẫu là hàm thuần
    // checkFormSelection(): thiếu bắt buộc / oneOf chưa chọn hoặc quá max.
    var selectedIds = visibleDocs().map(function (d) { return d.id; });
    var titles = {};
    visibleDocs().forEach(function (d) { titles[d.id] = d.ten_mau || d.id; });
    var errs = FD.validateDossier(visibleDocs(), state.store, ctxValidate())
      .concat(checkFormSelection(state.formMeta, selectedIds, titles));
    var blocking = errs.filter(function (e) { return e.severity === 'blocking'; });
    if (blocking.length) {
      state.errors = errs;
      renderErrorPanel();
      patchErrorsDom();
      renderTabBadges();
      openRightPanel();
      toast('<b>Không thể xuất hồ sơ: còn ' + blocking.length +
        ' lỗi bắt buộc phải sửa.</b><br>Xem danh sách ở panel "Kiểm tra lỗi".', 'err', true);
      return;
    }
    var btnBox = toast('Đang xuất hồ sơ…', '', true);
    var payload;
    try {
      payload = {
        case_id: state.caseId,
        forms: visibleDocs().map(function (d) { return { id: d.id }; }),
        data: buildExportData() // exportLoopsStrict: ném lỗi nếu conflict
      };
    } catch (ex) {
      btnBox.remove();
      // P2.0: xung đột contract export giữa các mẫu -> chặn LOUD kèm chi tiết
      if (ex && ex.code === 'EXPORT_LOOP_CONTRACT_CONFLICT') {
        state.errors = (ex.conflicts || []).map(function (c) {
          return {
            key: '@export-conflict:' + c.loop, docId: c.winner && c.winner.docId,
            code: 'EXPORT_LOOP_CONTRACT_CONFLICT', severity: 'blocking',
            message: c.message
          };
        });
        renderErrorPanel();
        patchErrorsDom();
        openRightPanel();
        toast('<b>Không thể xuất hồ sơ: xung đột contract export.</b><br>' +
          esc((ex.conflicts || []).map(function (c) { return c.message; })
            .join('<br>')), 'err', true);
        return;
      }
      throw ex; // lỗi lạ không nuốt im lặng
    }
    Promise.resolve(api().export(payload)).then(function (res) {
      if (typeof res === 'string') res = JSON.parse(res);
      btnBox.remove();
      if (res.ok) {
        var html = '<b>Xuất thành công!</b><br>' +
          (res.files || []).map(esc).join('<br>') +
          '<br><button type="button" id="btn-open-dir">Mở thư mục</button>';
        if (res.zip) html += '<br>ZIP: ' + esc(res.zip);
        var b = toast(html, 'ok', true);
        b.querySelector('#btn-open-dir').onclick = function () {
          api().open_dir(res.dir);
        };
      } else {
        toast('<b>Xuất thất bại</b><br>' + esc((res.errors || []).join('<br>') || 'lỗi không rõ'), 'err', true);
      }
    }).catch(function (e) {
      btnBox.remove();
      toast('Lỗi export: ' + esc(String(e)), 'err', true);
    });
  }

  // ------------------------------------------------------------- draft file
  function saveDraftFile() {
    var a = api();
    if (!a) { toast('Cần chạy qua python app_web/main.py để lưu/mở file.', 'err'); return; }
    Promise.resolve(a.save_draft(JSON.stringify(draftPayload()))).then(function (res) {
      if (typeof res === 'string') res = JSON.parse(res);
      if (res.ok) {
        state.dirty = false;
        setSaveState('saved');
        toast('Đã lưu: ' + esc(res.path), 'ok');
      } else if (!res.cancelled) toast('Không lưu được: ' + esc(res.error || ''), 'err');
    });
  }

  function openDraftFile() {
    var a = api();
    if (!a) { toast('Cần chạy qua python app_web/main.py để lưu/mở file.', 'err'); return; }
    Promise.resolve(a.load_draft()).then(function (res) {
      if (typeof res === 'string') res = JSON.parse(res);
      if (res.ok) {
        applyDraft(res.draft);
        toast('Đã mở: ' + esc(res.path), 'ok');
      } else if (!res.cancelled) {
        toast('Không mở được: ' + esc(res.error || ''), 'err');
      }
    });
  }

  function resetDossier() {
    if (state.dirty &&
        !confirm('Nhập lại sẽ XÓA toàn bộ dữ liệu đang khai. Tiếp tục?')) return;
    state.store = R.newStore();
    state.errors = [];
    state.selectedLoopRow = {};
    state.selRowId = {};
    state.multiSel = {};
    runAutoFills();       // tự điền ngày ký hôm nay
    renderAllPages();
    markDirty();
    toast('Đã nhập lại hồ sơ (dữ liệu trống).');
  }

  function openRightPanel() {
    var rb = $('#rightbar');
    if (rb.classList.contains('collapsed')) toggleRightPanel(true);
    rb.classList.add('open'); // mobile drawer
  }

  function toggleRightPanel(expand) {
    var rb = $('#rightbar');
    var collapsed = expand === undefined ? !rb.classList.contains('collapsed') : !expand;
    rb.classList.toggle('collapsed', collapsed);
    $('#btn-toggle-right').setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }

  function cycleTab(delta) {
    var docs = visibleDocs();
    if (!docs.length) return;
    var i = docs.findIndex(function (d) { return d.id === state.activeDocId; });
    if (i < 0) i = 0;
    var next = docs[(i + delta + docs.length) % docs.length];
    setActiveDoc(next.id, { restoreScroll: true, restoreFocus: true });
    updateTabsSelection(true);
  }

  // ------------------------------------------------------------- sự kiện
  function wireEvents() {
    // user TỰ đổi nhóm/case: hủy draft đang chờ khôi phục của case khác
    // (draft nạp qua applyDraft không đi qua listener này nên không bị hủy)
    $('#sel-nhom').addEventListener('change', function () {
      state.pendingDraft = null;
      onGroupChange();
    });
    $('#sel-case').addEventListener('change', function () {
      state.pendingDraft = null;
      onCaseChange(false);
    });

    var pages = $('#pages');

    pages.addEventListener('input', function (e) {
      var t = e.target;
      var key = t.getAttribute && t.getAttribute('data-key');
      // checkbox/radio tự xử lý ở listener 'change' (radio = selector P1.2)
      if (!key || t.type === 'checkbox' || t.type === 'radio') return;
      setKeyValue(key, t.value);
      mirrorKey(key, t);
      if (t.classList.contains('vsic-fld') &&
          t.getAttribute('data-tag') === 'ma_nganh') {
        handleMaNganhInput(t); // VSIC flow: tự điền tên / gợi ý / viền đỏ
      }
      runAutoFills();
      markDirty();
    });

    pages.addEventListener('change', function (e) {
      var t = e.target;
      // P1.2 Option D: selector metadata hồ sơ (vd 'dn.loai_hinh' của M72)
      // - radio cùng name nên browser đã ép chọn đúng một; ghi giá trị
      // canonical vào store.values rồi render lại để CHỈ biến thể được
      // chọn hiển thị (block cond không thoả bị bỏ khỏi UI).
      if (t.classList && t.classList.contains('sel-radio')) {
        var sk = t.getAttribute('data-sel-key');
        if (sk && t.value != null) {
          state.store.values[sk] = t.value;
          markDirty();
          rerenderKeepView();
        }
        return;
      }
      if (!t.classList || !t.classList.contains('chk-box')) return;
      var key = t.getAttribute('data-key');
      var lk = parseLoopKey(key);
      if (lk) {
        // checkbox/radio trong bảng lặp: giá trị lưu vào hàng của loop ('X'/'')
        var rows = state.store.loops[lk.loop] = state.store.loops[lk.loop] || [];
        while (rows.length <= lk.idx) rows.push({});
        GridCtl.ensureIds(state.store); // hàng sinh muộn vẫn có _row_id
        var rowId = rows[lk.idx]._row_id;
        var gm = FD.getGridMeta({ docId: state.activeDocId, loop: lk.loop });
        var colMeta = gm ? (gm.columns || []).filter(function (c) {
          return c.tag === lk.tag;
        })[0] : null;
        if (colMeta && colMeta.type === 'radio') {
          // la_nganh_chinh: chọn một dòng -> 'X', mọi dòng khác cùng cột -> ''
          GridCtl.setExclusiveRadio(state.store, lk.loop, rowId, lk.tag, t.checked);
        } else {
          rows[lk.idx][lk.tag] = t.checked ? 'X' : '';
        }
      } else {
        state.store.checks[key] = t.checked;
        var val = t.checked;
        document.querySelectorAll('#pages [data-key="' + cssEsc(key) + '"]').forEach(function (el) {
          if (el !== t) el.checked = val;
        });
      }
      markDirty();
    });

    pages.addEventListener('click', function (e) {
      var actBtn = e.target.closest('.loop-btns button[data-act]');
      if (actBtn) {
        handleLoopAction(actBtn);
        return;
      }
      var tr = e.target.closest('tr[data-row-index]');
      if (tr) selectRow(tr, e);
    });

    pages.addEventListener('focusin', function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains('vsic-fld')) {
        var key = t.getAttribute('data-key');
        if (!parseLoopKey(key)) return;
        if (t.getAttribute('data-tag') === 'ma_nganh') {
          handleMaNganhInput(t, true); // fromFocus: không xóa dữ liệu, chỉ gợi ý
        } else if (String(t.value || '').trim()) {
          showVsic(t, t.value, function (item) { applyVsicPick(t, item); });
        }
      }
    });

    document.addEventListener('mousedown', function (e) {
      if (pop && !pop.hidden && !e.target.closest('#vsic-pop') &&
          e.target !== document.activeElement) hideVsic();
    });

    document.addEventListener('keydown', function (e) {
      // VSIC keyboard trước hết
      if (handleVsicKeydown(e)) return;
      if (handleGridKeydown(e)) return;
      if (e.key === 'Escape' && pop && !pop.hidden) { hideVsic(); return; }
      // Ctrl+S lưu nhanh
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey &&
          String(e.key).toLowerCase() === 's') {
        e.preventDefault();
        quickSave();
        return;
      }
      // Ctrl+PageUp/PageDown đổi tab
      if (e.ctrlKey && e.key === 'PageUp') { e.preventDefault(); cycleTab(-1); return; }
      if (e.ctrlKey && e.key === 'PageDown') { e.preventDefault(); cycleTab(1); return; }
    });

    // tablist đáy: chuyển mẫu THẬT + phím mũi tên di focus (roving tabindex)
    $('#tabs').addEventListener('click', function (e) {
      var tab = e.target.closest('[role="tab"]');
      if (!tab) return;
      setActiveDoc(tab.getAttribute('data-doc-id'),
        { restoreScroll: true, restoreFocus: true });
      updateTabsSelection(true);
    });
    $('#tabs').addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      var tabs = Array.prototype.slice.call(document.querySelectorAll('#tabs [role="tab"]'));
      var i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      var j = (i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      tabs[j].focus();
      setActiveDoc(tabs[j].getAttribute('data-doc-id'), { restoreScroll: true });
    });

    // điều hướng từ danh sách lỗi
    $('#err-list').addEventListener('click', function (e) {
      var btn = e.target.closest('.err-item');
      if (!btn) return;
      navigateToError(btn.getAttribute('data-doc-id'), btn.getAttribute('data-key'));
    });

    // tick/bỏ tick mẫu: cập nhật state.checkedForms rồi tự loại trừ oneOf;
    // render lại để DOM khớp state (các mẫu bị loại trừ được bỏ tick)
    $('#form-list').addEventListener('change', function (e) {
      if (!e.target.classList.contains('form-tick')) return;
      var cf = Object.assign({}, state.checkedForms);
      cf[e.target.value] = e.target.checked;
      state.checkedForms = applyOneOfExclusive(state.formMeta, cf, e.target.value);
      renderAllPages({ keepScroll: true });
      scheduleAutosave();
    });

    $('#chk-autosum').addEventListener('change', function (e) {
      state.autoSum = e.target.checked;
      runAutoFills();
      applyReadonlyTotals();
      markDirty();
    });

    $('#btn-check').addEventListener('click', function () {
      runCheck($('#chk-check-all').checked);
      openRightPanel();
    });
    $('#btn-save').addEventListener('click', quickSave);
    $('#btn-reset').addEventListener('click', resetDossier);
    $('#btn-export').addEventListener('click', doExport);
    $('#btn-export2').addEventListener('click', doExport);
    $('#btn-save-draft').addEventListener('click', saveDraftFile);
    $('#btn-open-draft').addEventListener('click', openDraftFile);

    $('#btn-toggle-right').addEventListener('click', function () { toggleRightPanel(); });
    $('#btn-toggle-side').addEventListener('click', function () {
      $('#sidebar').classList.toggle('open');
    });
  }

  // ------------------------------------------------------------- khởi động
  function init() {
    wireEvents();
    loadCases();

    // danh mục VSIC: thử đọc dữ liệu chung (read-only), mock có bản rút gọn dự phòng
    var vsicUrl = '../app/data/nganh_vsic.json';
    var loadVsic = fetch(vsicUrl)
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function () {
        return fetch('mock/vsic_mini.json').then(function (r) { return r.ok ? r.json() : { nganh: [] }; });
      });
    loadVsic.then(function (j) { state.vsic = j.nganh || []; })
      .catch(function () { state.vsic = []; });

    // phục hồi bản nháp tự lưu (chờ docs nạp xong, tối đa 5s)
    try {
      var saved = localStorage.getItem('hoso_draft_autosave');
      if (saved) {
        var draft = JSON.parse(saved);
        var tries = 0;
        var waitDocs = setInterval(function () {
          if (state.docs.length || ++tries > 25) {
            clearInterval(waitDocs);
            if (state.docs.length) applyDraft(draft);
          }
        }, 200);
      }
    } catch (e) { /* bỏ qua */ }

    if (state.mock) {
      $('#side-status').textContent = 'Chế độ MOCK (?mock=1)';
      setSaveState('unsaved');
    }
  }

  /* Helpers thuần phục vụ test node (không DOM): GridCtl là controller
   * editable-grid generic (add/delete/reorder/duplicate/clear/export/radio/
   * vsicResolve), groupErrorsByDoc nhóm lỗi theo mẫu, gridMetaForDoc build
   * map {loop: meta} form-scoped cho renderer, GridFocus gom focus sau row
   * operation (focusTagOfGrid/nextSelAfterDelete thuần + focusGridRow DOM -
   * uiAddRow/uiDuplicateRow/uiMoveRow/uiDeleteRows đều đi qua đây),
   * FormFlow gom nghiệp vụ chọn mẫu (bat_buoc/oneOf/gate export/draft
   * restore), RequestToken chống race đổi case, saveOutcome đồng bộ
   * dirty/saveState. */
  var Helpers = {
    groupErrorsByDoc: groupErrorsByDoc,
    GridCtl: GridCtl,
    gridMetaForDoc: gridMetaForDoc,
    GridFocus: {
      focusTagOfGrid: focusTagOfGrid,
      nextSelAfterDelete: nextSelAfterDelete,
      focusGridRow: focusGridRow,
      enhanceEditableGrids: enhanceEditableGrids,
      gridNavigationIndex: gridNavigationIndex
    },
    /* P2 R2 runtime wiring 3 kind mới (fixed-matrix/nested-grid/output-table):
     * policy CRUD theo kind + projection tổng outputOnly. SectionCtl thành phần
     * THUẦN (trừ refresh có DOM) để node-test không GUI. */
    SectionCtl: {
      rowMeta: sectionRowMeta,
      rowOpMeta: rowOpMeta,
      computedText: componentComputedText,
      projectionOf: function (docId, store) {
        return FD.recomputeSections(docId, store);
      },
      contractsOf: function (docId) { return FD.sectionContractsOf(docId); },
      validateFormSections: function (docId, store) {
        return FD.validateFormSections(docId, store || {});
      }
    },
    FormFlow: {
      formIdOf: formIdOf,
      formIds: formIds,
      buildFormMeta: buildFormMeta,
      applyOneOfExclusive: applyOneOfExclusive,
      checkFormSelection: checkFormSelection,
      restoreSelection: restoreSelection,
      formListHtml: formListHtml,
      RequestToken: RequestToken,
      saveOutcome: saveOutcome
    }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Helpers;
  if (!IS_NODE) window.ControllerHelpers = Helpers;

  if (!IS_NODE) document.addEventListener('DOMContentLoaded', init);
})();
