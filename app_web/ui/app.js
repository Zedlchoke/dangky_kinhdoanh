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
    store: R.newStore(),
    autoSum: false,
    activeDocId: null,   // mẫu DUY NHẤT đang hiển thị
    dirty: false,
    saveState: 'unsaved',
    autosaveTimer: null,
    errors: [],          // kết quả Kiểm tra gần nhất
    selectedLoopRow: {}, // loopName -> rowIndex đang chọn
    viewState: {},       // docId -> {scrollTop, focusKey}
    pendingDraft: null,  // draft chờ docs nạp xong để khôi phục
    vsicItems: [],
    vsicIndex: 0
  };

  function $(sel) { return document.querySelector(sel); }
  function api() {
    return (window.pywebview && window.pywebview.api) || null;
  }
  function esc(s) { return R.escapeHtml(s); }
  function cssEsc(s) {
    return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/"/g, '\\"');
  }

  /* Case dùng khi chạy ?mock=1 (không đọc use_cases.json thật). */
  var MOCK_CASES = [
    {
      id: 'pilot_ui_m02_m06', nhom: 'Thành lập doanh nghiệp',
      ten: '(PILOT UI) Đồng bộ M02 + M06',
      mo_ta: '(MOCK) Case kiểm thử pilot: điền tên ở M02, sang M06 vẫn thấy giá trị.',
      forms: [{ pl: 'I', mau: 2 }, { pl: 'I', mau: 6 }],
      giay_to_kem: [],
      luu_y: ['Đây là case PILOT cho giao diện mới - không phải thủ tục thật.']
    },
    {
      id: 'thanh_lap_tnhh_1tv', nhom: 'Thành lập doanh nghiệp',
      ten: 'Thành lập Công ty TNHH một thành viên',
      mo_ta: '(MOCK) Lập công ty TNHH một thành viên.',
      forms: [{ pl: 'I', mau: 2 }],
      giay_to_kem: ['Bản Điều lệ công ty (MOCK)'],
      luu_y: ['Đây là chế độ mock - xuất hồ sơ cần Bridge Python.']
    },
    {
      id: 'thanh_lap_tnhh_2tv', nhom: 'Thành lập doanh nghiệp',
      ten: 'Thành lập Công ty TNHH hai thành viên trở lên',
      mo_ta: '(MOCK) Lập công ty TNHH hai thành viên trở lên.',
      forms: [{ pl: 'I', mau: 6 }],
      giay_to_kem: ['Bản Điều lệ công ty (MOCK)'],
      luu_y: ['Danh sách thành viên tự cộng tổng vốn góp.']
    },
    {
      id: 'dang_ky_ho_kinh_doanh_lan_dau', nhom: 'Hộ kinh doanh',
      ten: 'Đăng ký hộ kinh doanh lần đầu',
      mo_ta: '(MOCK) Đăng ký hộ kinh doanh lần đầu.',
      forms: [{ pl: 'II', mau: 1 }],
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
      if (persistLocal()) setSaveState('saved');
      else setSaveState('error');
    }, 800);
  }

  /* Ctrl+S / nút Lưu: ghi ngay không chờ debounce. */
  function quickSave() {
    clearTimeout(state.autosaveTimer);
    setSaveState('saving');
    if (persistLocal()) {
      state.dirty = false;
      setSaveState('saved');
    } else {
      setSaveState('error');
    }
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
    var cs = currentCase();
    renderCaseInfo(cs);
    updateDocTitle();
    var wanted = formIds(cs);
    getBlocks(wanted).then(function (results) {
      state.docs = [];
      results.forEach(function (r) {
        if (r.doc) state.docs.push(r.doc);
        else toast('Không nạp được mẫu: ' + esc(r.error), 'err');
      });
      if (state.pendingDraft) { finishApplyDraft(); return; }
      state.activeDocId = state.docs.length ? state.docs[0].id : null;
      state.errors = [];
      state.selectedLoopRow = {};
      renderAllPages();
    });
  }

  function formIds(cs) {
    return (cs.forms || []).map(function (f) { return 'PL' + f.pl + '_M' + f.mau; });
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
    var el = $('#form-list');
    el.innerHTML = state.docs.map(function (d) {
      return '<label><input type="checkbox" class="form-tick" value="' + esc(d.id) +
        '" checked> ' + esc(d.ten_mau || d.id) + '</label>';
    }).join('');
  }

  function visibleDocs() {
    var ticks = {};
    document.querySelectorAll('.form-tick').forEach(function (t) {
      if (t.checked) ticks[t.value] = true;
    });
    return state.docs.filter(function (d) { return ticks[d.id]; });
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

  function renderActiveDoc() {
    var d = activeDoc();
    var pages = $('#pages');
    if (!d) {
      pages.innerHTML = '<section class="page-a4"><p class="bp bp-center rn-i">' +
        '(Chưa chọn mẫu biểu nào)</p></section>';
      return;
    }
    pages.innerHTML = '<section class="page-a4" id="doc_' + esc(d.id) +
      '" data-doc="' + esc(d.id) + '" tabindex="-1">' +
      R.renderBlocks(d, state.store, { docId: d.id, fieldMeta: FD.FIELD_META }) +
      '</section>';
    applyReadonlyTotals();
    patchErrorsDom();
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
  }

  function validateAllMaNganh() {
    document.querySelectorAll('#pages .vsic-fld[data-tag="ma_nganh"]').forEach(function (inp) {
      var ok = R.isValidMaNganh(state.vsic, inp.value);
      inp.classList.toggle('invalid', !ok);
    });
  }

  // ------------------------------------------------------------- bảng lặp
  function selectRow(tr) {
    var table = tr.closest('.loop-table');
    var loop = tr.getAttribute('data-loop');
    var idx = +tr.getAttribute('data-row-index');
    table.querySelectorAll('tbody tr').forEach(function (r) {
      var sel = r === tr;
      r.classList.toggle('row-sel', sel);
      r.setAttribute('aria-selected', sel ? 'true' : 'false');
    });
    state.selectedLoopRow[loop] = idx;
  }

  function addLoopRow(loop) {
    var rows = state.store.loops[loop] = state.store.loops[loop] || [];
    var at = state.selectedLoopRow[loop];
    if (at != null && at < rows.length) rows.splice(at + 1, 0, {});
    else rows.push({});
    markDirty();
    rerenderKeepView();
  }

  function deleteLoopRow(loop) {
    var rows = state.store.loops[loop] = state.store.loops[loop] || [];
    if (!rows.length) return;
    var wrap = document.querySelector('.loop-table[data-loop="' + cssEsc(loop) + '"]');
    var shown = wrap ? wrap.querySelectorAll('tbody tr').length : rows.length;
    var idx = state.selectedLoopRow[loop];
    if (idx == null || idx >= shown || idx >= rows.length) idx = Math.min(rows.length - 1, shown - 1);
    if (idx < 0) idx = 0;
    var row = rows[idx] || {};
    var hasData = Object.keys(row).some(function (k) {
      return String(row[k] == null ? '' : row[k]).trim() !== '';
    });
    if (hasData &&
        !confirm('Dòng ' + (idx + 1) + ' của "' + loop + '" đang có dữ liệu.\nXóa dòng này?')) {
      return;
    }
    rows.splice(idx, 1);
    delete state.selectedLoopRow[loop];
    markDirty();
    rerenderKeepView();
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

  function handleVsicInput(inp) {
    var tag = inp.getAttribute('data-tag');
    if (!isNganhTag(tag)) return;
    var lk = parseLoopKey(inp.getAttribute('data-key'));
    if (!lk) return;
    showVsic(inp, inp.value, function (item) {
      // điền cả mã + tên vào CÙNG hàng
      ['ma_nganh', 'ten_nganh'].forEach(function (t) {
        setKeyValue('loop:' + lk.loop + ':' + lk.idx + ':' + t, item[t]);
        var el = document.querySelector(
          '#pages [data-key="' + cssEsc('loop:' + lk.loop + ':' + lk.idx + ':' + t) + '"]');
        if (el) el.value = item[t];
      });
      validateAllMaNganh();
      markDirty();
    });
  }

  function handleVsicKeydown(e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('vsic-fld')) return false;
    if (!pop || pop.hidden) {
      if (e.key === 'ArrowDown') { handleVsicInput(inp); return true; }
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
        if (item) {
          var lk = parseLoopKey(inp.getAttribute('data-key'));
          ['ma_nganh', 'ten_nganh'].forEach(function (t) {
            setKeyValue('loop:' + lk.loop + ':' + lk.idx + ':' + t, item[t]);
            var el = document.querySelector(
              '#pages [data-key="' + cssEsc('loop:' + lk.loop + ':' + lk.idx + ':' + t) + '"]');
            if (el) el.value = item[t];
          });
          hideVsic();
          validateAllMaNganh();
          markDirty();
        }
        return true;
      case 'Escape':
        e.preventDefault(); hideVsic(); return true;
    }
    return false;
  }

  function handleMaNganhValidation(inp) {
    if (inp.getAttribute('data-tag') !== 'ma_nganh') return;
    var ok = R.isValidMaNganh(state.vsic, inp.value);
    inp.classList.toggle('invalid', !ok);
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

  function findErrorField(e) {
    if (e.key.indexOf('loop:') === 0) {
      return document.querySelector('#pages [data-key="' + cssEsc(e.key) + '"]');
    }
    if (e.key.indexOf('.') > 0 && e.key.split('.')[0] in (state.store.loops || {})) {
      // key tổng hợp dạng <loop>.<tag>: trỏ tới ô đầu tiên của tag đó
      var parts = e.key.split('.');
      var tbl = document.querySelector('#pages .loop-table[data-loop="' + cssEsc(parts[0]) + '"]');
      return tbl ? tbl.querySelector('[data-tag="' + cssEsc(parts[1]) + '"]') : null;
    }
    return document.querySelector('#pages [data-key="' + cssEsc(e.key) + '"]');
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
    if (draft.checkedForms && draft.checkedForms.length) {
      document.querySelectorAll('.form-tick').forEach(function (t) {
        t.checked = draft.checkedForms.indexOf(t.value) >= 0;
      });
    }
    state.activeDocId = (draft.activeDocId &&
      state.docs.some(function (d) { return d.id === draft.activeDocId; }))
      ? draft.activeDocId
      : (visibleDocs()[0] ? visibleDocs()[0].id : null);
    runAutoFills();
    renderAllPages();
    var vs = state.viewState[state.activeDocId];
    if (vs) $('#scroller').scrollTop = vs.scrollTop || 0;
    state.dirty = false;
    setSaveState('saved', 'Đã khôi phục hồ sơ');
  }

  // ------------------------------------------------------------- export
  function buildExportData() {
    var data = {};
    Object.keys(state.store.values).forEach(function (k) {
      data[k] = state.store.values[k];
    });
    Object.keys(state.store.checks).forEach(function (k) {
      data[k] = state.store.checks[k] ? 'X' : '';
    });
    Object.keys(state.store.loops).forEach(function (name) {
      data[name] = state.store.loops[name].map(function (row) {
        return Object.assign({}, row);
      });
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
    // CHÍNH SÁCH CHẶN EXPORT: còn lỗi blocking thì không gọi Bridge.export
    var errs = FD.validateDossier(visibleDocs(), state.store, ctxValidate());
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
    var payload = {
      case_id: state.caseId,
      forms: visibleDocs().map(function (d) { return { id: d.id }; }),
      data: buildExportData()
    };
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
    $('#sel-nhom').addEventListener('change', onGroupChange);
    $('#sel-case').addEventListener('change', function () { onCaseChange(false); });

    var pages = $('#pages');

    pages.addEventListener('input', function (e) {
      var t = e.target;
      var key = t.getAttribute && t.getAttribute('data-key');
      if (!key || t.type === 'checkbox') return;
      setKeyValue(key, t.value);
      mirrorKey(key, t);
      handleMaNganhValidation(t);
      handleVsicInput(t);
      runAutoFills();
      markDirty();
    });

    pages.addEventListener('change', function (e) {
      var t = e.target;
      if (!t.classList || !t.classList.contains('chk-box')) return;
      var key = t.getAttribute('data-key');
      state.store.checks[key] = t.checked;
      var val = t.checked;
      document.querySelectorAll('#pages [data-key="' + cssEsc(key) + '"]').forEach(function (el) {
        if (el !== t) el.checked = val;
      });
      markDirty();
    });

    pages.addEventListener('click', function (e) {
      var add = e.target.closest('.btn-row-add');
      var del = e.target.closest('.btn-row-del');
      if (add || del) {
        var loop = (add || del).getAttribute('data-loop') ||
          (add || del).closest('.loop-btns').getAttribute('data-loop');
        if (add) addLoopRow(loop); else deleteLoopRow(loop);
        return;
      }
      var tr = e.target.closest('tr[data-row-index]');
      if (tr) selectRow(tr);
    });

    pages.addEventListener('focusin', function (e) {
      var t = e.target;
      if (t.classList && t.classList.contains('vsic-fld')) {
        var key = t.getAttribute('data-key');
        if (parseLoopKey(key)) handleVsicInput(t);
      }
    });

    document.addEventListener('mousedown', function (e) {
      if (pop && !pop.hidden && !e.target.closest('#vsic-pop') &&
          e.target !== document.activeElement) hideVsic();
    });

    document.addEventListener('keydown', function (e) {
      // VSIC keyboard trước hết
      if (handleVsicKeydown(e)) return;
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

    // tick/bỏ tick mẫu
    $('#form-list').addEventListener('change', function (e) {
      if (e.target.classList.contains('form-tick')) {
        renderAllPages({ keepScroll: true });
        scheduleAutosave();
      }
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

  /* Helpers thuần phục vụ test node (không DOM). */
  var Helpers = { groupErrorsByDoc: groupErrorsByDoc };
  if (typeof module !== 'undefined' && module.exports) module.exports = Helpers;
  if (!IS_NODE) window.ControllerHelpers = Helpers;

  if (!IS_NODE) document.addEventListener('DOMContentLoaded', init);
})();
