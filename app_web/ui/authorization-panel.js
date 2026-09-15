/* Panel ủy quyền dịch vụ — profile người làm thủ tục + sinh giấy ủy quyền theo case.
 * Phụ thuộc: pywebview bridge (I1+), AuthorizationPanel.init() từ app.js */
(function (global) {
  'use strict';

  var ctx = null;
  var profiles = [];
  var templates = [];
  var selectedAgentId = '';
  var editingAgent = null;
  var lastResult = null;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function bridge(fn, arg) {
    var a = ctx.api();
    if (!a || typeof a[fn] !== 'function') {
      return Promise.reject(new Error('Cần chạy app desktop (pywebview).'));
    }
    /* pywebview gọi API với 0 hoặc 1 đối số — không truyền undefined. */
    var call = (arg === undefined) ? a[fn]() : a[fn](arg);
    return Promise.resolve(call).then(function (res) {
      if (typeof res === 'string') return JSON.parse(res);
      return res;
    });
  }

  function bridgeErrorsText(res) {
    if (!res) return 'Lỗi không xác định';
    if (res.error) return String(res.error);
    if (res.errors && res.errors.length) {
      return res.errors.map(function (e) {
        return e.message || e.code || String(e);
      }).join('; ');
    }
    return 'Thao tác thất bại';
  }

  function renderProfiles() {
    var sel = $('#auth-agent-select');
    if (!sel) return;
    var html = '<option value="">— Chọn người làm thủ tục —</option>';
    profiles.forEach(function (p) {
      var label = p.ho_ten + (p.so_cccd ? ' (' + p.so_cccd.slice(-4) + ')' : '');
      if (p.trang_thai === 'locked') label += ' [khóa]';
      html += '<option value="' + ctx.esc(p.agent_id) + '"' +
        (p.agent_id === selectedAgentId ? ' selected' : '') + '>' +
        ctx.esc(label) + '</option>';
    });
    sel.innerHTML = html;
  }

  function renderTemplates() {
    var box = $('#auth-template-list');
    if (!box) return;
    if (!templates.length) {
      box.innerHTML = '<div class="auth-muted">Case này chưa có mẫu ủy quyền trong catalog.</div>';
      return;
    }
    box.innerHTML = '<ul class="auth-tpl-list">' + templates.map(function (t) {
      return '<li><b>' + ctx.esc(t.id) + '</b> — ' + ctx.esc(t.label || '') + '</li>';
    }).join('') + '</ul>';
  }

  function renderStoreInfo(info) {
    var el = $('#auth-store-info');
    if (!el || !info) return;
    el.textContent = info.active_profiles + ' profile đang hoạt động';
  }

  function fillProfileForm(p) {
    var editor = $('#auth-profile-editor');
    if (!editor) return;
    var fields = [
      'ho_ten', 'ngay_sinh', 'gioi_tinh', 'quoc_tich', 'so_cccd', 'ngay_cap',
      'noi_cap', 'dia_chi_lien_he', 'dien_thoai', 'email', 'chuc_danh',
      'don_vi_dich_vu', 'ghi_chu'
    ];
    fields.forEach(function (f) {
      var inp = editor.querySelector('[name="' + f + '"]');
      if (inp) inp.value = (p && p[f]) ? p[f] : '';
    });
    var aid = $('#auth-agent-id');
    if (aid) aid.value = (p && p.agent_id) ? p.agent_id : '';
  }

  function readProfileForm() {
    var editor = $('#auth-profile-editor');
    var data = {};
    if (!editor) return data;
    editor.querySelectorAll('input, textarea, select').forEach(function (inp) {
      if (!inp.name) return;
      data[inp.name] = inp.value;
    });
    var aid = $('#auth-agent-id');
    if (aid && aid.value) data.agent_id = aid.value;
    return data;
  }

  function loadProfiles() {
    return bridge('list_authorized_agent_profiles', JSON.stringify({ status: 'active' }))
      .then(function (res) {
        if (!res.ok) throw new Error(bridgeErrorsText(res));
        profiles = res.profiles || [];
        if (selectedAgentId && !profiles.some(function (p) { return p.agent_id === selectedAgentId; })) {
          selectedAgentId = '';
        }
        renderProfiles();
      });
  }

  function loadTemplatesForCase() {
    var caseId = ctx.getCaseId();
    var box = $('#auth-template-list');
    if (!caseId) {
      templates = [];
      if (box) box.innerHTML = '<div class="auth-muted">Chọn thủ tục để xem mẫu ủy quyền.</div>';
      return Promise.resolve();
    }
    return bridge('get_authorization_templates', JSON.stringify({ case_id: caseId }))
      .then(function (res) {
        if (!res.ok) {
          templates = [];
          if (box) box.innerHTML = '<div class="auth-muted">' + ctx.esc(bridgeErrorsText(res)) + '</div>';
          return;
        }
        templates = res.templates || [];
        renderTemplates();
      });
  }

  function loadStoreInfo() {
    return bridge('get_authorization_store_info').then(function (res) {
      if (res.ok) renderStoreInfo(res);
    });
  }

  function refresh() {
    if (!ctx) return Promise.resolve();
    return Promise.all([loadProfiles(), loadTemplatesForCase(), loadStoreInfo()])
      .catch(function (e) {
        ctx.toast('Ủy quyền: ' + ctx.esc(String(e.message || e)), 'err');
      });
  }

  function onCaseChanged() {
    loadTemplatesForCase();
  }

  function saveProfile() {
    var data = readProfileForm();
    if (!data.ho_ten || !data.so_cccd) {
      ctx.toast('Họ tên và số CCCD là bắt buộc.', 'err');
      return;
    }
    bridge('save_authorized_agent_profile', JSON.stringify(data))
      .then(function (res) {
        if (!res.ok) {
          ctx.toast(bridgeErrorsText(res), 'err', true);
          return;
        }
        selectedAgentId = res.profile.agent_id;
        editingAgent = null;
        $('#auth-profile-editor').hidden = true;
        ctx.toast('Đã lưu profile: ' + ctx.esc(res.profile.ho_ten), 'ok');
        return refresh();
      })
      .catch(function (e) {
        ctx.toast('Lưu profile: ' + ctx.esc(String(e)), 'err');
      });
  }

  function generatePackage() {
    var caseId = ctx.getCaseId();
    if (!caseId) { ctx.toast('Chưa chọn thủ tục.', 'err'); return; }
    if (!selectedAgentId) { ctx.toast('Chọn người làm thủ tục.', 'err'); return; }
    var coQuan = ($('#auth-co-quan') || {}).value || '';
    var thoiHan = ($('#auth-thoi-han') || {}).value || '';
    var payload = {
      case_id: caseId,
      case_ten: ctx.getCaseTen(),
      agent_id: selectedAgentId,
      values: ctx.getStoreValues(),
      co_quan_tiep_nhan: coQuan,
      thoi_han_den: thoiHan,
      export_format: 'both'
    };
    var box = ctx.toast('Đang sinh hồ sơ ủy quyền…', '', true);
    bridge('generate_authorization_package', JSON.stringify(payload))
      .then(function (res) {
        if (box && box.remove) box.remove();
        if (!res.ok) {
          ctx.toast('<b>Không sinh được hồ sơ</b><br>' + ctx.esc(bridgeErrorsText(res)), 'err', true);
          return;
        }
        lastResult = res;
        var html = '<b>Đã sinh hồ sơ ủy quyền</b><br>' +
          (res.files || []).map(ctx.esc).join(', ');
        if (res.errors && res.errors.length) {
          html += '<br><span class="auth-warn">' + ctx.esc(res.errors.join('; ')) + '</span>';
        }
        $('#auth-last-result').innerHTML = html;
        ctx.toast('Đã sinh hồ sơ ủy quyền.', 'ok');
      })
      .catch(function (e) {
        if (box && box.remove) box.remove();
        ctx.toast('Sinh hồ sơ: ' + ctx.esc(String(e)), 'err');
      });
  }

  function openOutputDir() {
    if (!lastResult || !lastResult.dir) {
      ctx.toast('Chưa có hồ sơ được sinh trong phiên này.', 'err');
      return;
    }
    bridge('open_dir', lastResult.dir).then(function (res) {
      if (!res.ok) ctx.toast('Không mở thư mục: ' + ctx.esc(res.error || ''), 'err');
    });
  }

  function exportBackup() {
    bridge('export_authorization_backup').then(function (res) {
      if (res.cancelled) return;
      if (!res.ok) ctx.toast(bridgeErrorsText(res), 'err');
      else ctx.toast('Đã sao lưu: ' + ctx.esc(res.path || ''), 'ok', true);
    });
  }

  function importBackup() {
    bridge('import_authorization_backup').then(function (res) {
      if (res.cancelled) return;
      if (!res.ok) ctx.toast(bridgeErrorsText(res), 'err');
      else {
        ctx.toast('Đã khôi phục profile từ backup.', 'ok');
        refresh();
      }
    });
  }

  function wirePanel() {
    var root = $('#auth-panel');
    if (!root || root.dataset.wired === '1') return;
    root.dataset.wired = '1';

    $('#auth-agent-select').addEventListener('change', function (e) {
      selectedAgentId = e.target.value;
    });

    $('#auth-btn-new-profile').addEventListener('click', function () {
      editingAgent = null;
      fillProfileForm({});
      $('#auth-profile-editor').hidden = false;
    });

    $('#auth-btn-edit-profile').addEventListener('click', function () {
      if (!selectedAgentId) { ctx.toast('Chọn profile trước.', 'err'); return; }
      var p = profiles.filter(function (x) { return x.agent_id === selectedAgentId; })[0];
      if (!p) return;
      editingAgent = p;
      fillProfileForm(p);
      $('#auth-profile-editor').hidden = false;
    });

    $('#auth-btn-cancel-profile').addEventListener('click', function () {
      $('#auth-profile-editor').hidden = true;
    });

    $('#auth-btn-save-profile').addEventListener('click', saveProfile);

    $('#auth-btn-generate').addEventListener('click', generatePackage);
    $('#auth-btn-open-dir').addEventListener('click', openOutputDir);
    $('#auth-btn-backup').addEventListener('click', exportBackup);
    $('#auth-btn-restore').addEventListener('click', importBackup);
  }

  function init(options) {
    ctx = options;
    wirePanel();
    /* Chờ pywebviewready — gọi sớm sẽ báo lỗi giả "cần desktop". */
    if (ctx.api()) refresh();
    window.addEventListener('pywebviewready', function () { refresh(); }, { once: true });
  }

  global.AuthorizationPanel = {
    init: init,
    refresh: refresh,
    onCaseChanged: onCaseChanged
  };
})(window);
