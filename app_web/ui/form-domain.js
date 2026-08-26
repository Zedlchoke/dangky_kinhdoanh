/* form-domain.js - module THUẦN cho field metadata + validation (không DOM).
 * Dùng chung app.js (webview) và test (node require). UMD như render.js.
 * Contract: docs/htkk-ui-contract.md
 *  - getFieldMeta(key) -> meta|null
 *  - parseMoney / formatMoney : tiền hiển thị '1.000.000', tính trên số thật
 *  - validateField / validateDocument / validateDossier -> error[]
 *    error = { key, docId, code, message, severity: 'blocking'|'warning' }
 *  - collectKeys(blocks), migrateDraft(draft) (v1 -> v2)
 *  - GRID_META / FORM_GRID_META / getGridMeta: metadata editable-grid dùng
 *    chung + metadata theo mẫu (resolver docId+semanticKey -> docId+loop ->
 *    toàn cục -> null); makeRowId/normalizeStoreLoops: _row_id ổn định +
 *    migration ds_nganh.
 *  - evalActiveWhen / activationModeOf / isActiveGrid / registerFormGridMeta:
 *    activation của grid khai báo thuần dữ liệu (activeWhen) - selector
 *    (checkedKey/valueOf) là nguồn chính, minFilledRows chỉ INTERIM chờ
 *    owner chốt contract loại hình (docs/m72_activation_proposal.md).
 *  - FORM_SELECTOR_META / getFormSelector / validateSelector /
 *    selectedSelectorOption / selectorFlagsOf: P1.2 Option D - selector
 *    'Loại hình doanh nghiệp' của PLI_M72 là metadata hồ sơ (store.values),
 *    bắt buộc chọn đúng một trong 5 giá trị canonical; quyết định grid/
 *    block active và flags xuất DOCX. KHÔNG render vào văn bản.
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
   * vsicTags phải có trong danh mục VSIC khi ctx.vsicList được cung cấp.
   * LOOP_META giữ cho tương thích ngược; metadata mới nằm ở GRID_META. */
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

  /* Metadata editable-grid dùng chung (PLAN.md mục "editable-grid").
   * - minRows/maxRows: số dòng CÓ DỮ LIỆU tối thiểu/tối đa; vi phạm KHÔNG khóa
   *   thao tác, chỉ validator chặn trước export.
   * - required: bảng bắt buộc phải có ít nhất 1 dòng dữ liệu (ngược lại 0 dòng
   *   là hợp lệ) -> lỗi INDUSTRY_REQUIRED khi required && 0 dòng.
   * - allowAdd/allowDelete/allowReorder: ẩn nút action tương ứng trên UI.
   * - confirmDeleteNonEmpty: xác nhận trước khi xóa dòng có dữ liệu.
   * - columns[]: {tag, type, required?, col?}; type: text|money|percent|
   *   checkbox|radio|readonly|vsic|outputOnly. col dùng khi template có cột
   *   vật lý chưa được map tag trong blocks.cols (vd la_nganh_chinh ở PLII_M01).
   * - duplicateKeys: field định danh/khóa -> bị bỏ khi nhân bản dòng và được
   *   check trùng lặp; riêng ds_nganh.ma_nganh sinh lỗi DUPLICATE_INDUSTRY.
   * - outputOnlyTags: cột chỉ dùng cho bản in, không nhập trên UI.
   * - requirePrimary: phải chọn đúng MỘT dòng la_nganh_chinh (radio).
   * - autoName: {codeTag, nameTag} - tự điền tên từ danh mục theo mã (VSIC). */
  var GRID_META = {
    ds_thanh_vien: {
      label: 'Danh sách thành viên',
      minRows: 2, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'so_cccd', type: 'text' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'von_dong_gop', type: 'money' },
        { tag: 'ty_le_von', type: 'percent' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ],
      duplicateKeys: ['so_cccd'],
      outputOnlyTags: ['chu_ky']
    },
    ds_co_dong_sang_lap: {
      label: 'Danh sách cổ đông sáng lập',
      minRows: 1, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'so_cccd', type: 'text' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'so_co_phan', type: 'money' },
        { tag: 'ty_le', type: 'percent' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ],
      duplicateKeys: ['so_cccd'],
      outputOnlyTags: ['chu_ky']
    },
    ds_co_dong_nn: {
      label: 'Danh sách cổ đông là nhà đầu tư nước ngoài',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ten_cd', type: 'text', required: true },
        { tag: 'quoc_gia', type: 'text' },
        { tag: 'ma_so', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'so_co_phan', type: 'money' },
        { tag: 'ty_le', type: 'percent' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ],
      duplicateKeys: [],
      outputOnlyTags: ['chu_ky']
    },
    ds_cshhl: {
      label: 'Chủ sở hữu hưởng lợi',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      // hợp nhất 2 biến thể production (PLI_M10 cá nhân, PLI_M11 tổ chức):
      // row cá nhân có ho_ten..., row tổ chức có ten_to_chuc...
      columns: [
        { tag: 'ho_ten', type: 'text' },
        { tag: 'ten_to_chuc', type: 'text' },
        { tag: 'ma_so_dn', type: 'text' },
        { tag: 'ngay_cap', type: 'text' },
        { tag: 'noi_cap', type: 'text' },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'so_giay_to', type: 'text' },
        { tag: 'ty_le', type: 'percent' },
        { tag: 'ty_le_co_phan', type: 'percent' },
        { tag: 'ghi_chu', type: 'text' }
      ],
      duplicateKeys: ['so_giay_to', 'ma_so_dn'],
      outputOnlyTags: []
    },
    ds_tv_ho_gia_dinh: {
      label: 'Các thành viên hộ gia đình',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'so_cccd', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'noi_thuong_tru', type: 'text' },
        { tag: 'noi_o_hien_tai', type: 'text' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ],
      duplicateKeys: ['so_cccd'],
      outputOnlyTags: ['chu_ky']
    },
    ds_nganh: {
      label: 'Danh sách ngành nghề kinh doanh',
      minRows: 1, maxRows: null, required: true,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: true,
      columns: [
        { tag: 'ten_nganh', type: 'readonly', required: true },
        { tag: 'ma_nganh', type: 'vsic', required: true },
        { tag: 'chi_tiet', type: 'text' },
        { tag: 'la_nganh_chinh', type: 'radio', col: 3 }
      ],
      duplicateKeys: ['ma_nganh'],
      outputOnlyTags: [],
      autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh' }
    },
    /* PLI_M12 mục 1: bổ sung ngành vào danh sách đã đăng ký. Danh sách độc
     * lập với ds_nganh -> minRows 0, không chặn trùng mã, không bắt buộc
     * chọn ngành chính (template cho phép đánh X tùy chọn). */
    nganh_bo_sung: {
      label: 'Ngành, nghề kinh doanh được bổ sung',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ten_nganh', type: 'text', required: true },
        { tag: 'ma_nganh', type: 'vsic' },
        { tag: 'la_nganh_chinh', type: 'radio' }
      ],
      duplicateKeys: [],
      outputOnlyTags: []
    },
    /* PLI_M12 mục 2: bỏ ngành khỏi danh sách đã đăng ký. Cột 4 theo template
     * là Ghi chú (KHÔNG có cột ngành chính) -> ghi_chu dạng text. */
    nganh_xoa_bo: {
      label: 'Ngành, nghề kinh doanh được bỏ khỏi danh sách đã đăng ký',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ten_nganh', type: 'text', required: true },
        { tag: 'ma_nganh', type: 'vsic' },
        { tag: 'ghi_chu', type: 'text' }
      ],
      duplicateKeys: [],
      outputOnlyTags: []
    },
    /* PLI_M12 mục 3: sửa đổi chi tiết ngành đã đăng ký (tên loop do agent 2B
     * chốt - PLAN.md chỉ định danh nganh_bo_sung/nganh_xoa_bo). */
    nganh_sua_doi_chi_tiet: {
      label: 'Ngành, nghề kinh doanh được sửa đổi chi tiết',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ten_nganh', type: 'text', required: true },
        { tag: 'ma_nganh', type: 'vsic' },
        { tag: 'la_nganh_chinh', type: 'radio' }
      ],
      duplicateKeys: [],
      outputOnlyTags: []
    }
  };

  /* Clone giá trị metadata (P2.0 hardening): object/array -> bản sao ĐỆ QUY
   * mọi mức, scalar (string/number/bool/null/undefined) giữ nguyên.
   * Không dependency - chỉ dùng cho metadata JSON-thuần của grid. */
  function deepCloneVal(v) {
    if (v == null || typeof v !== 'object') return v;
    if (Array.isArray(v)) return v.map(deepCloneVal);
    var o = {};
    Object.keys(v).forEach(function (k) { o[k] = deepCloneVal(v[k]); });
    return o;
  }

  /* Tạo meta grid mới từ base dùng chung: CLONE SÂU toàn bộ field để meta
   * trả về KHÔNG chia sẻ bất kỳ tham chiếu nào với GRID_META gốc hay giữa
   * các loop/mẫu - mutate một chỗ không bao giờ lan sang chỗ khác:
   *  - columns[]          : mảng mới + từng column object mới;
   *  - autoName           : object mới {codeTag, nameTag};
   *  - duplicateKeys,
   *    outputOnlyTags     : mảng copy;
   *  - activeWhen         : object mới (kể cả valueOf bên trong);
   *  - label/syncGroup/
   *    semanticKey...     : string gán thẳng là đủ (immutable theo giá trị). */
  function mkGrid(base, extra) {
    var merged = Object.assign({}, base, extra || {});
    var m = {};
    Object.keys(merged).forEach(function (k) { m[k] = deepCloneVal(merged[k]); });
    return m;
  }

  function getFieldMeta(key) {
    return FIELD_META[key] || null;
  }

  function getLoopMeta(name) {
    return LOOP_META[name] || null;
  }

  /* ------------------------------------------- form-scoped grid metadata
   * Metadata editable-grid THEO MẪU (PLAN.md mục "editable-grid" + đặc tả
   * bảng ngành): cùng tên loop ở hai mẫu khác nhau có thể có cột/rule khác
   * nhau (vd nganh_bo_sung của PLII_M02 dùng tag ten_nganh_bo_sung, khác
   * PLI_M12) -> KHÔNG kế thừa mù qua GRID_META toàn cục.
   * - Shape mỗi entry: như GRID_META + semanticKey (khớp
   *   app/data/form_maps.json dynamic_tables.semantic_key), syncGroup
   *   (chỉ ghi nhận, CHƯA auto-sync - P2), activeWhen (điều kiện kích hoạt
   *   rule khai báo trong dữ liệu - xem evalActiveWhen).
   * - Resolver getGridMeta(): (a) docId+semanticKey -> (b) docId+loop ->
   *   (c) GRID_META[loop] -> (d) null. */
  var FORM_GRID_META = {
    /* PLI_M72: mẫu gồm 5 phần theo loại hình DN. P1.2 Option D (owner đã
     * chốt): selector metadata hồ sơ 'dn.loai_hinh' (FORM_SELECTOR_META)
     * là NGUỒN CHÍNH duy nhất - mỗi loop chỉ active khi giá trị selector
     * trùng đúng biến thể của nó (valueOf). KHÔNG còn cơ chế INTERIM
     * minFilledRows: draft cũ chưa có selector -> mọi grid inactive và
     * export bị chặn bởi SELECTOR_REQUIRED cho tới khi người dùng chọn.
     * required:false/minRows:0 giữ nguyên hiện trạng (không tự suy thêm
     * rule pháp lý ngoài quyết định 5 loại hình đã chốt). */
    'PLI_M72': {
      loops: {
        ds_nganh_dntn: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Doanh nghiệp tư nhân)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['DNTN'] } },
          semanticKey: 'ds_nganh_dntn', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_tnhh_1tv: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty TNHH một thành viên)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['TNHH_1TV'] } },
          semanticKey: 'ds_nganh_tnhh_1tv', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_tnhh_2tv: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty TNHH hai thành viên trở lên)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['TNHH_2TV'] } },
          semanticKey: 'ds_nganh_tnhh_2tv', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_ctcp: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty cổ phần)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['CTCP'] } },
          semanticKey: 'ds_nganh_ctcp', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_dhdn: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty hợp danh)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['DHDN'] } },
          semanticKey: 'ds_nganh_dhdn', syncGroup: 'ds_nganh_pli_m72'
        })
      }
    },
    /* PLII_M02: 4 vùng ngành ĐỘC LẬP (điền vùng này không đổi vùng kia;
     * mỗi loop store key riêng, không copy dữ liệu vì trùng tên cột).
     * Cột ten-tag THẬT theo blocks/form_maps từng vùng. Vùng C.3 giữ loop
     * canonical ds_nganh với semanticKey=nganh_hien_tai và requirePrimary
     * cho RIÊNG mẫu này; required=false/minRows=0 để điền một vùng khác
     * không bị chặn oan bởi danh sách hiện tại (tính độc lập vùng). */
    'PLII_M02': {
      loops: {
        nganh_bo_sung: {
          label: 'Ngành, nghề kinh doanh được bổ sung',
          minRows: 0, maxRows: null, required: false,
          allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: true, requirePrimary: false,
          columns: [
            { tag: 'ten_nganh_bo_sung', type: 'text', required: true },
            { tag: 'ma_nganh', type: 'vsic' },
            { tag: 'la_nganh_chinh', type: 'radio' }
          ],
          duplicateKeys: [],
          outputOnlyTags: [],
          autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh_bo_sung' },
          semanticKey: 'nganh_bo_sung'
        },
        nganh_xoa_bo: {
          label: 'Ngành, nghề kinh doanh được bỏ khỏi danh sách đã đăng ký',
          minRows: 0, maxRows: null, required: false,
          allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: true, requirePrimary: false,
          columns: [
            { tag: 'ten_nganh_bo', type: 'text', required: true },
            { tag: 'ma_nganh', type: 'vsic' },
            { tag: 'la_nganh_chinh', type: 'radio' }
          ],
          duplicateKeys: [],
          outputOnlyTags: [],
          autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh_bo' },
          semanticKey: 'nganh_xoa_bo'
        },
        nganh_sua_doi_chi_tiet: {
          label: 'Ngành, nghề kinh doanh được sửa đổi chi tiết',
          minRows: 0, maxRows: null, required: false,
          allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: true, requirePrimary: false,
          columns: [
            { tag: 'ten_nganh', type: 'text', required: true },
            { tag: 'ma_nganh', type: 'vsic' }
          ],
          duplicateKeys: [],
          outputOnlyTags: [],
          autoName: { codeTag: 'ma_nganh', nameTag: 'ten_nganh' },
          semanticKey: 'nganh_sua_doi_chi_tiet'
        },
        ds_nganh: mkGrid(GRID_META.ds_nganh, {
          required: false, minRows: 0,
          semanticKey: 'nganh_hien_tai'
        })
      }
    }
  };

  /* Gắn chỉ mục tra cứu theo semanticKey + trace info cho từng entry.
   * Entry nào do mkGrid sinh ra là object RIÊNG (columns đã clone) nên mutate
   * an toàn; entry khai literal cũng là object riêng của mẫu đó. */
  function indexFormMeta(fm, fid) {
    fm.formId = fid;
    fm.loops = fm.loops || {};
    fm.bySemanticKey = {};
    Object.keys(fm.loops).forEach(function (ln) {
      var m = fm.loops[ln];
      m.loop = ln;
      m.formId = fid;
      if (m.semanticKey) fm.bySemanticKey[m.semanticKey] = m;
    });
    return fm;
  }

  Object.keys(FORM_GRID_META).forEach(function (fid) {
    indexFormMeta(FORM_GRID_META[fid], fid);
  });

  /* ------------------------------------------- form-scoped selector metadata
   * P1.2 "Option D" cho PLI_M72: selector 'Loại hình doanh nghiệp' là
   * METADATA HỒ SƠ/APP (store.values[key]) - KHÔNG phải nội dung pháp lý,
   * KHÔNG render/in vào DOCX. Nó quyết định:
   *  - grid nào active (FORM_GRID_META activeWhen.valueOf cùng key);
   *  - block nào hiển thị trên UI (render lọc theo flags, khớp cond blocks);
   *  - phần nào của DOCX được xuất (engine vùng {?flag}/{/flag} + flags
   *    do selectorFlagsOf suy ra từ ĐÚNG metadata này).
   * Giá trị canonical đúng 5 loại; người dùng bắt buộc chọn đúng MỘT.
   * flag phải khớp tools/form_specs/change/PLI_M72.json (section_cond)
   * và marker trong app/templates/PLI_M72.docx - test đối chiếu chéo. */
  var FORM_SELECTOR_META = {
    'PLI_M72': {
      formId: 'PLI_M72',
      key: 'dn.loai_hinh',
      label: 'Loại hình doanh nghiệp',
      required: true,
      help: 'Chọn đúng MỘT loại hình doanh nghiệp. Ứng dụng chỉ hiện, kiểm '
        + 'tra và xuất phần công bố tương ứng; lựa chọn này là dữ liệu hồ '
        + 'sơ trong ứng dụng, không in thành ô tick trên văn bản.',
      options: [
        { value: 'DNTN', label: 'Doanh nghiệp tư nhân', flag: 'loai_hinh_dntn' },
        { value: 'TNHH_1TV', label: 'Công ty TNHH một thành viên', flag: 'loai_hinh_tnhh_1tv' },
        { value: 'TNHH_2TV', label: 'Công ty TNHH hai thành viên trở lên', flag: 'loai_hinh_tnhh_2tv' },
        { value: 'CTCP', label: 'Công ty cổ phần', flag: 'loai_hinh_ctcp' },
        { value: 'DHDN', label: 'Công ty hợp danh', flag: 'loai_hinh_dhdn' }
      ]
    }
  };

  function getFormSelector(docId) {
    return FORM_SELECTOR_META[docId] || null;
  }

  /* Option đang chọn trong store (so trim, phân biệt hoa/thường như
   * evalActiveWhen.value). Trả null khi chưa chọn/giá trị lạ. */
  function selectedSelectorOption(selMeta, store) {
    if (!selMeta) return null;
    var cur = ((store || {}).values || {})[selMeta.key];
    cur = cur == null ? '' : String(cur).trim();
    if (!cur) return null;
    var hit = null;
    (selMeta.options || []).forEach(function (o) {
      if (o && String(o.value) === cur) hit = o;
    });
    return hit;
  }

  /* Validation thuần của selector: chưa chọn -> SELECTOR_REQUIRED;
   * giá trị ngoài danh sách canonical (draft hỏng/sửa tay) ->
   * SELECTOR_INVALID. Cả hai blocking. */
  function validateSelector(docId, selMeta, store) {
    if (!selMeta) return [];
    var errs = [];
    var opt = selectedSelectorOption(selMeta, store);
    if (!opt) {
      var raw = ((store || {}).values || {})[selMeta.key];
      var typed = raw == null ? '' : String(raw).trim();
      errs.push({
        key: '@selector:' + selMeta.key,
        docId: docId,
        code: typed ? 'SELECTOR_INVALID' : 'SELECTOR_REQUIRED',
        severity: 'blocking',
        message: typed
          ? (selMeta.label + ': giá trị "' + typed +
             '" không thuộc danh mục cho phép - hãy chọn lại.')
          : (selMeta.label + ': bắt buộc chọn đúng một loại trước khi kiểm '
             + 'tra/xuất hồ sơ.')
      });
    }
    return errs;
  }

  /* Flags điều kiện xuất/render suy từ selector ('X'/'' như checks) -
   * nguồn duy nhất của payload export và renderer cond blocks. */
  function selectorFlagsOf(docId, store) {
    var out = {};
    var selMeta = getFormSelector(docId);
    if (!selMeta) return out;
    (selMeta.options || []).forEach(function (o) {
      if (o && o.flag) out[o.flag] = '';
    });
    var opt = selectedSelectorOption(selMeta, store);
    if (opt && opt.flag) out[opt.flag] = 'X';
    return out;
  }

  /* Đăng ký/thay thế metadata form-scoped lúc RUNTIME và đánh chỉ mục như
   * các entry khai sẵn. Dùng cho test fixture (metadata giả định selector
   * loại hình - KHÔNG đưa key giả định vào production) và sau này cho dữ
   * liệu activation owner chốt mà không phải sửa code validator. */
  function registerFormGridMeta(fid, fm) {
    FORM_GRID_META[fid] = fm || { loops: {} };
    return indexFormMeta(FORM_GRID_META[fid], fid);
  }

  /* Resolver metadata editable-grid. Tham số:
   *  - getGridMeta('<loop>')            : BACKWARD COMPAT - đúng như cũ,
   *                                       trả GRID_META[name] || null.
   *  - getGridMeta({docId, loop, semanticKey}) : resolve theo thứ tự
   *      (a) docId + semanticKey  (b) docId + loop
   *      (c) GRID_META[loop] toàn cục (contract dùng chung cũ)
   *      (d) null. */
  function getGridMeta(nameOrQuery) {
    if (typeof nameOrQuery === 'string') return GRID_META[nameOrQuery] || null;
    if (!nameOrQuery || typeof nameOrQuery !== 'object') return null;
    var fm = nameOrQuery.docId ? FORM_GRID_META[nameOrQuery.docId] : null;
    if (fm) {
      if (nameOrQuery.semanticKey && fm.bySemanticKey[nameOrQuery.semanticKey])
        return fm.bySemanticKey[nameOrQuery.semanticKey];
      if (nameOrQuery.loop && fm.loops[nameOrQuery.loop])
        return fm.loops[nameOrQuery.loop];
    }
    return nameOrQuery.loop ? (GRID_META[nameOrQuery.loop] || null) : null;
  }

  // ------------------------------------------------------- stable row ids

  var _idSeq = 0;
  /* '_row_id' ổn định trong phiên: 'r'<seq tăng dần>+'_'+random suffix.
   * Sinh khi tạo row, giữ qua draft save/load; loại khỏi payload export. */
  function makeRowId() {
    _idSeq += 1;
    return 'r' + _idSeq + '_' + Math.random().toString(36).slice(2, 8);
  }

  /* Đảm bảo mọi row trong store.loops có _row_id (mutate tại chỗ).
   * Đồng thời migration canonical: ds_nganh_kinh_doanh -> ds_nganh khi chưa
   * có ds_nganh (giữ nguyên dữ liệu); KHÔNG đụng nganh_bo_sung/nganh_xoa_bo/
   * nganh_truoc_thay_doi. */
  function normalizeStoreLoops(store) {
    if (!store || typeof store !== 'object') return store;
    var loops = store.loops = store.loops || {};
    if (loops.ds_nganh_kinh_doanh && !loops.ds_nganh) {
      loops.ds_nganh = loops.ds_nganh_kinh_doanh;
      delete loops.ds_nganh_kinh_doanh;
    }
    Object.keys(loops).forEach(function (name) {
      (loops[name] || []).forEach(function (r) {
        if (r && typeof r === 'object' && !r._row_id) r._row_id = makeRowId();
      });
    });
    return store;
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

  // ------------------------------------------------- helpers editable-grid

  function colsByType(g, type) {
    return (g.columns || []).filter(function (c) { return c && c.type === type; })
      .map(function (c) { return c.tag; });
  }

  /* Cột tính là "dữ liệu" khi xét dòng trống/có dữ liệu: loại trừ
   * checkbox/radio/outputOnly (ô tick và cột chỉ dùng để in). */
  function dataTagsOf(g) {
    return (g.columns || []).filter(function (c) {
      return c && c.type !== 'outputOnly' && c.type !== 'radio' && c.type !== 'checkbox';
    }).map(function (c) { return c.tag; });
  }

  function requiredTagsOf(g) {
    return (g.columns || []).filter(function (c) { return c && c.required; })
      .map(function (c) { return c.tag; });
  }

  function cellStr(r, tag) {
    return String((r || {})[tag] == null ? '' : r[tag]).trim();
  }

  function rowFilledOn(r, tags) {
    return tags.some(function (t) { return cellStr(r, t) !== ''; });
  }

  /* activeWhen có khai SELECTOR (nguồn chính quyết định active) không?
   * Selector = checkedKey (store.checks) hoặc valueOf {key, equals:[...]}
   * (so store.values[key] với danh sách giá trị). KHÔNG hard-code form ID -
   * toàn bộ nằm trong metadata của từng grid. */
  function hasSelectorAw(aw) {
    if (aw.checkedKey != null) return true;
    return !!(aw.valueOf && aw.valueOf.key != null);
  }

  /* Điều kiện kích hoạt rule của grid - KHAI BÁO trong metadata (dữ liệu),
   * đánh giá THUẦN trên store: không DOM, không hard-code form ID.
   * THỨ TỰ ƯU TIÊN RÕ RÀNG:
   *  - activeWhen CÓ selector (checkedKey/valueOf): selector là NGUỒN CHÍNH
   *    duy nhất quyết định active; minFilledRows bị BỎ QUA (không cộng dồn).
   *  - activeWhen KHÔNG có selector: minFilledRows là cơ chế INTERIM chờ
   *    owner chốt contract loại hình (vd PLI_M72) - grid chỉ active khi đã
   *    có >= N dòng CÓ DỮ LIỆU; KHÔNG phải nguồn xác định loại hình chính.
   *  - checkedKey + valueOf cùng khai -> cả hai phải thoả (AND).
   * Không khai báo activeWhen -> luôn active (hành vi cũ 100%). */
  function evalActiveWhen(aw, filledCount, st) {
    if (!aw) return true;
    st = st || {};
    if (!hasSelectorAw(aw)) {
      // INTERIM (chờ owner): chỉ dữ liệu thật kích hoạt rule
      if (aw.minFilledRows != null && filledCount < aw.minFilledRows) return false;
      return true;
    }
    if (aw.checkedKey != null && !((st.checks || {})[aw.checkedKey])) return false;
    if (aw.valueOf && aw.valueOf.key != null) {
      var want = aw.valueOf.equals || [];
      var cur = (st.values || {})[aw.valueOf.key];
      cur = cur == null ? '' : String(cur).trim();
      var hit = false;
      for (var i = 0; i < want.length; i++) {
        if (String(want[i]) === cur) { hit = true; break; }
      }
      if (!hit) return false;
    }
    return true;
  }

  /* Chế độ activation HIỆU LỰC của một grid meta - suy từ chính activeWhen,
   * phục vụ audit/test/export guard (meta không thể khai lệch):
   *  - null                  : không có activeWhen -> luôn active (hành vi cũ)
   *  - 'selector'            : checkedKey/valueOf quyết định (nguồn chính,
   *                            dùng khi owner đã chốt contract loại hình)
   *  - 'interim-filled-data' : chỉ minFilledRows (INTERIM tạm chờ owner) */
  function activationModeOf(g) {
    var aw = g && g.activeWhen;
    if (!aw) return null;
    return hasSelectorAw(aw) ? 'selector' : 'interim-filled-data';
  }

  /* Grid đang ACTIVE với store cho trước? Thuần, không DOM: đếm dòng CÓ DỮ
   * LIỆU theo cột data của meta rồi gọi evalActiveWhen. Dùng chung bởi
   * validateGridLoop và export guard. */
  function isActiveGrid(g, rows, st) {
    if (!g || !g.activeWhen) return true;
    var dTags = dataTagsOf(g);
    var filled = (rows || []).filter(function (r) { return rowFilledOn(r, dTags); });
    return evalActiveWhen(g.activeWhen, filled.length, st);
  }

  /* Validate một bảng lặp CÓ grid meta (toàn cục hoặc form-scoped). Lỗi
   * row-level mang key
   * "loop:<name>:<row_id>:<tag>" nên reorder/xóa dòng không làm lỗi trỏ sai
   * dòng. Tự sửa tên-lệch TRƯỚC khi báo lỗi nếu tìm thấy trong danh mục
   * (mutate store tại chỗ); chỉ báo NAME_MISMATCH khi không tìm thấy tên. */
  function validateGridLoop(docId, name, g, tags, st, ctx, push) {
    var label = g.label || name;
    var rows = st.loops[name] || [];
    var lm = getLoopMeta(name) || {};

    rows.forEach(function (r) {
      if (r && typeof r === 'object' && !r._row_id) r._row_id = makeRowId();
    });

    function errAt(r, tag, code, msg) {
      push({
        key: 'loop:' + name + ':' + r._row_id + (tag ? ':' + tag : ''),
        docId: docId, code: code, message: msg, severity: 'blocking'
      });
    }
    function dispIdx(r) { return rows.indexOf(r) + 1; }

    var dTags = dataTagsOf(g);
    var reqTags = requiredTagsOf(g);
    var moneyTags = lm.moneyTags || colsByType(g, 'money');
    var percentTags = lm.percentTags || colsByType(g, 'percent');
    var vsicTags = (lm.vsicTags && lm.vsicTags.length) ? lm.vsicTags : colsByType(g, 'vsic');

    var filled = rows.filter(function (r) { return rowFilledOn(r, dTags); });

    // activeWhen khai báo trong metadata (selector hoặc INTERIM minFilledRows):
    // grid không active -> KHÔNG sinh lỗi nào (cả blocking lẫn warning).
    // vd PLI_M72: 5 phần loại hình, phần không áp dụng phải im hoàn toàn;
    // khi owner chốt selector thì phần KHÔNG được chọn cũng im dù có dữ liệu.
    if (!evalActiveWhen(g.activeWhen, filled.length, st)) return;

    // Bảng bắt buộc mà 0 dòng dữ liệu (vd ds_nganh ở thủ tục bắt buộc kê khai)
    if (g.required && filled.length === 0) {
      push({
        key: 'loop:' + name, docId: docId, code: 'INDUSTRY_REQUIRED',
        message: label + ': bắt buộc kê khai ít nhất một dòng dữ liệu',
        severity: 'blocking'
      });
    }
    // Vi phạm minRows KHÔNG khóa thao tác - chỉ chặn trước export
    var minReq = (lm.minRowsFilled != null) ? lm.minRowsFilled : (g.minRows || 0);
    if (minReq > 0 && filled.length > 0 && filled.length < minReq) {
      push({
        // bảng có rule legacy (LOOP_META.minRowsFilled) giữ nguyên key cũ để
        // tương thích ngược; bảng mới dùng key "loop:<name>"
        key: (lm.minRowsFilled != null) ? name : 'loop:' + name,
        docId: docId, code: 'MIN_ROWS',
        message: label + ': cần tối thiểu ' + minReq +
          ' dòng có dữ liệu (đang có ' + filled.length + ')',
        severity: 'blocking'
      });
    }
    // maxRows: chỉ cảnh báo (UI chặn thêm dòng; draft cũ có thể vượt)
    if (g.maxRows != null && rows.length > g.maxRows) {
      push({
        key: 'loop:' + name, docId: docId, code: 'MAX_ROWS',
        message: label + ': vượt quá tối đa ' + g.maxRows + ' dòng (đang có ' + rows.length + ')',
        severity: 'warning'
      });
    }

    // ROW_INCOMPLETE: dòng có một phần dữ liệu nhưng thiếu column required
    rows.forEach(function (r) {
      if (!r || !rowFilledOn(r, dTags)) return;
      var missing = reqTags.filter(function (t) { return cellStr(r, t) === ''; });
      if (missing.length) {
        errAt(r, missing[0], 'ROW_INCOMPLETE',
          label + ' dòng ' + dispIdx(r) + ': thiếu thông tin bắt buộc: ' + missing.join(', '));
      }
    });

    // VSIC_INVALID + tự sửa ten_nganh lệch danh mục trước khi báo lỗi
    var autoName = g.autoName || null;
    if (ctx.vsicList) {
      rows.forEach(function (r) {
        if (!r) return;
        vsicTags.forEach(function (tag) {
          var raw = cellStr(r, tag);
          if (!raw) return;
          var entry = null;
          for (var i = 0; i < ctx.vsicList.length; i++) {
            if (String(ctx.vsicList[i].ma) === raw) { entry = ctx.vsicList[i]; break; }
          }
          if (!entry) {
            errAt(r, tag, 'VSIC_INVALID',
              label + ' dòng ' + dispIdx(r) + ': mã ngành không có trong danh mục VSIC: ' + raw);
            return;
          }
          if (autoName && autoName.codeTag === tag &&
              (g.columns || []).some(function (c) { return c.tag === autoName.nameTag; })) {
            var cur = cellStr(r, autoName.nameTag);
            var official = entry.ten == null ? '' : String(entry.ten);
            if (official && cur !== official) {
              r[autoName.nameTag] = official; // tự sửa lại tên theo danh mục
            } else if (!official && cur) {
              errAt(r, autoName.nameTag, 'NAME_MISMATCH',
                label + ' dòng ' + dispIdx(r) +
                ': không tìm thấy tên chính thức trong danh mục VSIC cho mã: ' + raw);
            }
          }
        });
      });
    }

    // Trùng khóa: ds_nganh.ma_nganh -> DUPLICATE_INDUSTRY blocking trỏ CẢ HAI
    // dòng; bảng khác -> DUPLICATE_ROWS warning.
    (g.duplicateKeys || []).forEach(function (k) {
      if ((tags || []).indexOf(k) < 0) return; // cột không nằm trong mẫu này
      var seen = {};
      rows.forEach(function (r, ix) {
        var v = cellStr(r, k);
        if (!v) return;
        if (seen[v] != null) {
          var industry = !!g.requirePrimary || name === 'ds_nganh';
          [seen[v], ix].forEach(function (rix) {
            push({
              key: 'loop:' + name + ':' + rows[rix]._row_id + ':' + k,
              docId: docId,
              code: industry ? 'DUPLICATE_INDUSTRY' : 'DUPLICATE_ROWS',
              message: label + ' dòng ' + (rix + 1) + ': giá trị trùng "' + v + '" (cột ' + k + ')',
              severity: industry ? 'blocking' : 'warning'
            });
          });
        } else {
          seen[v] = ix;
        }
      });
    });

    // Ngành chính: có >=1 dòng dữ liệu nhưng chưa đánh dấu ngành nào
    if (g.requirePrimary && filled.length > 0) {
      var hasPrimary = rows.some(function (r) {
        return r && (r.la_nganh_chinh === 'X' || r.la_nganh_chinh === true);
      });
      if (!hasPrimary) {
        push({
          key: 'loop:' + name + ':' + (filled[0]._row_id || ''),
          docId: docId, code: 'PRIMARY_INDUSTRY_REQUIRED',
          message: label + ': hãy đánh dấu X chọn MỘT ngành, nghề kinh doanh chính',
          severity: 'blocking'
        });
      }
    }

    // money/percent kế thừa hành vi cũ nhưng key theo row_id
    moneyTags.forEach(function (tag) {
      if ((tags || []).indexOf(tag) < 0) return;
      rows.forEach(function (r) {
        var raw = cellStr(r, tag);
        if (!raw) return;
        if (parseMoney(raw) == null) {
          errAt(r, tag, 'MONEY',
            label + ' dòng ' + dispIdx(r) + ': giá trị tiền không hợp lệ: ' + raw);
        }
      });
    });
    percentTags.forEach(function (tag) {
      if ((tags || []).indexOf(tag) < 0) return;
      var sum = 0, hasVal = false;
      rows.forEach(function (r) {
        var n = parseMoney((r || {})[tag]);
        if (n != null) { sum += n; hasVal = true; }
      });
      if (hasVal && Math.round(sum) !== 100) {
        push({
          key: name + '.' + tag, docId: docId, code: 'PERCENT_SUM',
          message: label + ': tổng tỷ lệ ' + tag + ' = ' + sum + '% (cần đúng 100%)',
          severity: 'warning'
        });
      }
    });
  }

  /* Path legacy cho loop KHÔNG có GRID_META (vd ds_nganh_kinh_doanh cũ). */
  function validateLegacyLoop(docId, name, tags, st, ctx, push) {
    var lm = getLoopMeta(name);
    if (!lm) return;
    var rows = st.loops[name] || [];
    var filled = rows.filter(function (r) {
      return tags.some(function (t) { return cellStr(r, t) !== ''; });
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
        var raw = cellStr(rows[i], tag);
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
        var raw2 = cellStr(rows[i], tag);
        if (!raw2) continue;
        if (!isValidMaNganh(ctx.vsicList, raw2)) {
          push({
            key: name + '.' + tag, docId: docId, code: 'VSIC',
            message: lm.label + ' dòng ' + (i + 1) + ': mã ngành không hợp lệ: ' + raw2,
            severity: 'blocking'
          });
          return;
        }
      }
    });
  }

  /* Validate một mẫu biểu. store = {values, checks, loops}. Trả error[].
   * Loop có grid meta (resolve theo docId: form-scoped trước, rồi toàn cục)
   * -> validate editable-grid với lỗi key theo _row_id:
   * "loop:<name>:<row_id>[:<tag>]"; loop khác giữ hành vi legacy. */
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
      var g = getGridMeta({ docId: docId, loop: name });
      if (g) validateGridLoop(docId, name, g, info.loops[name], st, ctx, push);
      else validateLegacyLoop(docId, name, info.loops[name], st, ctx, push);
    });

    // Selector form-scoped (P1.2 Option D): M72 bắt buộc chọn đúng một
    // loại hình - chưa chọn/giá trị lạ là blocking chặn export.
    validateSelector(docId, getFormSelector(docId), st).forEach(push);

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

  /* v2 = v1 + activeDocId/viewState/savedAt. Draft cũ v1 giữ nguyên dữ liệu.
   * Cả v1 lẫn v2 đều được chuẩn hoá tại chỗ: gán _row_id cho row còn thiếu
   * và migration ds_nganh_kinh_doanh -> ds_nganh (khi chưa có ds_nganh).
   * Draft v2 được trả về CHÍNH OBJECT GỐC (chỉ mutate bên trong). */
  function migrateDraft(draft) {
    if (!draft || typeof draft !== 'object') return null;
    if (Number(draft.v) >= 2) {
      normalizeStoreLoops(draft.store);
      return draft;
    }
    if (!draft.store) return null; // draft không hiểu -> bỏ qua
    var up = {
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
    normalizeStoreLoops(up.store);
    return up;
  }

  // ----------------------------------------------------------------- exports

  root.parseMoney = parseMoney;
  root.formatMoney = formatMoney;
  root.FIELD_META = FIELD_META;
  root.LOOP_META = LOOP_META;
  root.GRID_META = GRID_META;
  root.FORM_GRID_META = FORM_GRID_META;
  root.FORM_SELECTOR_META = FORM_SELECTOR_META;
  root.getFieldMeta = getFieldMeta;
  root.getLoopMeta = getLoopMeta;
  root.getGridMeta = getGridMeta;
  root.getFormSelector = getFormSelector;
  root.selectedSelectorOption = selectedSelectorOption;
  root.validateSelector = validateSelector;
  root.selectorFlagsOf = selectorFlagsOf;
  root.registerFormGridMeta = registerFormGridMeta;
  root.evalActiveWhen = evalActiveWhen;
  root.activationModeOf = activationModeOf;
  root.isActiveGrid = isActiveGrid;
  root.makeRowId = makeRowId;
  root.normalizeStoreLoops = normalizeStoreLoops;
  root.collectKeys = collectKeys;
  root.validateField = validateField;
  root.validateDocument = validateDocument;
  root.validateDossier = validateDossier;
  root.isValidMaNganh = isValidMaNganh;
  root.migrateDraft = migrateDraft;

})(typeof module !== 'undefined' && module.exports ? module.exports : (window.FormDomain = window.FormDomain || {}));
