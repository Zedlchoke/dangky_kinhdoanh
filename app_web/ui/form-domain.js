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
 *  - R2 runtime wiring: FORM_TABLE_CONTRACTS + sectionContractsOf /
 *    getSectionContract / sectionContractForLoop (metadata SECTION theo kind:
 *    fixed-matrix/nested-grid/output-table cho fixture P2), p2TableModule
 *    (resolve module thuần, chỉ require/gọi), validateSectionEntry /
 *    validateFormSections (dispatcher validation theo kind, severity đúng
 *    contract), recomputeSections (tổng outputOnly recompute - projection,
 *    không ghi ngược draft). editable-grid giữ nguyên đường getGridMeta cũ.
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
    /* Class 14 (Wave C finding F1, 20 form PLII_M08/10/11/12/14/16/19/20/21/
     * 22/23/25/28 + PLI_M07/47/50/51/52/53/76): 4 field liên hệ của
     * contact-block template dùng chung KHÔNG có rule nào -> rác in thẳng
     * vào DOCX. Sửa ở ĐÚNG LỚP - metadata dùng chung, KHÔNG liệt kê tay
     * từng form: mọi blocks chứa key này tự được validateDocument kiểm. */
    'email_khac':        { key: 'email_khac', label: 'Thư điện tử khác', type: 'email', inputMode: 'email' },
    'dien_thoai_khac':   { key: 'dien_thoai_khac', label: 'Điện thoại khác', type: 'phone', inputMode: 'tel' },
    'fax':               { key: 'fax', label: 'Fax', type: 'phone', inputMode: 'tel' },
    'website':           { key: 'website', label: 'Website', type: 'website', inputMode: 'url' },
    'dn.ma_so_dn':       { key: 'dn.ma_so_dn', label: 'Mã số doanh nghiệp/Mã số thuế chủ sở hữu', type: 'mst' },
    'dn_goc.ma_so_dn':   { key: 'dn_goc.ma_so_dn', label: 'Mã số doanh nghiệp bị chia/tách/hợp nhất', type: 'mst' },
    'hkd_cd.ma_so_thue': { key: 'hkd_cd.ma_so_thue', label: 'Mã số thuế hộ kinh doanh chuyển đổi', type: 'mst' },
    'csbt.ma_so_thue':   { key: 'csbt.ma_so_thue', label: 'Mã số thuế cơ sở bảo trợ xã hội/quỹ', type: 'mst' },
    'so_lao_dong':       { key: 'so_lao_dong', label: 'Tổng số lao động (dự kiến)', type: 'number', inputMode: 'numeric' },
    /* [V4 ui-hint lane 6v-micro] Bổ sung meta LABEL + HELP cho các họ key UI
     * hay gặp mà trước đây chỉ render cơ bản: hộ kinh doanh (hkd_* và
     * hkd_cd.* — tên/mã số/trụ sở hộ KD), cơ sở bảo trợ xã hội/quỹ (csbt.*),
     * chi nhánh/văn phòng đại diện/địa điểm kinh doanh (cn.* — PLI_M43...),
     * người đại diện theo pháp luật (ndd.*). Quy tắc giữ nguyên như comment
     * trên: KHÔNG đổi key cũ, chỉ THÊM. Mọi key mới đều optional, type 'text'
     * (riêng ndd.dien_thoai dùng 'phone' nhất quán dien_thoai_khac) — giúp
     * placeholder/aria trên UI, KHÔNG thêm ràng buộc validation mới. Riêng
     * hkd_ma_so để 'text' thay vì 'mst' vì mã số hộ KD có thể 12 số, ngoài
     * dải 10/13 số mà validator mst chấp nhận. */
    'hkd_ten_tieng_viet': { key: 'hkd_ten_tieng_viet', label: 'Tên hộ kinh doanh viết bằng tiếng Việt', type: 'text',
                            help: 'Ghi bằng chữ in hoa.' },
    'hkd_ten_tieng_viet_2': { key: 'hkd_ten_tieng_viet_2', label: 'Tên hộ kinh doanh', type: 'text',
                              help: 'Ghi bằng chữ in hoa.' },
    'hkd_ten_nuoc_ngoai': { key: 'hkd_ten_nuoc_ngoai', label: 'Tên hộ kinh doanh bằng tiếng nước ngoài', type: 'text' },
    'hkd_ten_viet_tat':   { key: 'hkd_ten_viet_tat', label: 'Tên hộ kinh doanh viết tắt', type: 'text' },
    'hkd_ma_so':          { key: 'hkd_ma_so', label: 'Mã số hộ kinh doanh/Mã số thuế', type: 'text',
                            help: 'Mã số đăng ký hộ kinh doanh (10 hoặc 12 số); nhập nguyên vẹn.' },
    'hkd_tru_so':         { key: 'hkd_tru_so', label: 'Trụ sở của hộ kinh doanh', type: 'text',
                            help: 'Ghi theo giấy tờ địa chính: số nhà, đường/phố, phường/xã, huyện/quận, tỉnh/thành phố.' },
    'hkd_cd.ten_hkd':     { key: 'hkd_cd.ten_hkd', label: 'Tên hộ kinh doanh chuyển đổi', type: 'text',
                            help: 'Tên hộ KD đã đăng ký trước khi chuyển đổi; ghi bằng chữ in hoa.' },
    'hkd_cd.ten_chu_ho':  { key: 'hkd_cd.ten_chu_ho', label: 'Tên chủ hộ kinh doanh', type: 'text' },
    'hkd_cd.so_gcn':      { key: 'hkd_cd.so_gcn', label: 'Số Giấy chứng nhận đăng ký hộ kinh doanh', type: 'text' },
    'hkd_cd.dia_chi':     { key: 'hkd_cd.dia_chi', label: 'Địa chỉ trụ sở hộ kinh doanh', type: 'text' },
    'csbt.ten':               { key: 'csbt.ten', label: 'Tên cơ sở bảo trợ xã hội/quỹ', type: 'text',
                                help: 'Ghi bằng chữ in hoa.' },
    'csbt.dia_chi':           { key: 'csbt.dia_chi', label: 'Địa chỉ trụ sở chính cơ sở bảo trợ xã hội/quỹ', type: 'text' },
    'csbt.so_gcn':            { key: 'csbt.so_gcn', label: 'Số Giấy chứng nhận đăng ký thành lập (cơ sở bảo trợ/quỹ)', type: 'text' },
    'csbt.ten_nguoi_dai_dien': { key: 'csbt.ten_nguoi_dai_dien', label: 'Tên người đại diện cơ sở bảo trợ xã hội/quỹ', type: 'text' },
    'csbt.ngay_cap':          { key: 'csbt.ngay_cap', label: 'Ngày cấp Giấy chứng nhận đăng ký (cơ sở bảo trợ/quỹ)', type: 'text',
                                help: 'Nhập ngày/tháng/năm cấp giấy chứng nhận.' },
    'cn.ten_tieng_viet': { key: 'cn.ten_tieng_viet', label: 'Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh', type: 'text',
                           help: 'Ghi bằng chữ in hoa.' },
    'cn.ten_nuoc_ngoai': { key: 'cn.ten_nuoc_ngoai', label: 'Tên chi nhánh/văn phòng đại diện/địa điểm bằng tiếng nước ngoài', type: 'text' },
    'cn.ten_viet_tat':   { key: 'cn.ten_viet_tat', label: 'Tên chi nhánh/văn phòng đại diện/địa điểm viết tắt', type: 'text' },
    'cn.ma_so':          { key: 'cn.ma_so', label: 'Mã số chi nhánh/văn phòng đại diện/địa điểm kinh doanh', type: 'text',
                           help: 'Mã số do cơ quan đăng ký kinh doanh cấp; hồ sơ mới để trống.' },
    'cn.ma_so_2':        { key: 'cn.ma_so_2', label: 'Mã số/mã số thuế của chi nhánh/văn phòng đại diện', type: 'text' },
    'cn.dia_chi':        { key: 'cn.dia_chi', label: 'Địa chỉ chi nhánh/văn phòng đại diện/địa điểm kinh doanh', type: 'text',
                           help: 'Số nhà, đường/phố, phường/xã, huyện/quận, tỉnh/thành phố.' },
    'ndd.chuc_vu':    { key: 'ndd.chuc_vu', label: 'Chức danh người đại diện theo pháp luật', type: 'text',
                        help: 'Ví dụ: Chủ tịch HĐTV, Chủ tịch HĐQT, Giám đốc, Tổng giám đốc.' },
    'ndd.gioi_tinh':  { key: 'ndd.gioi_tinh', label: 'Giới tính người đại diện', type: 'text' },
    'ndd.ngay_sinh':  { key: 'ndd.ngay_sinh', label: 'Ngày, tháng, năm sinh người đại diện', type: 'text' },
    'ndd.thang_sinh': { key: 'ndd.thang_sinh', label: 'Tháng sinh người đại diện', type: 'text' },
    'ndd.nam_sinh':   { key: 'ndd.nam_sinh', label: 'Năm sinh người đại diện', type: 'text' },
    'ndd.dien_thoai': { key: 'ndd.dien_thoai', label: 'Điện thoại người đại diện', type: 'phone', inputMode: 'tel' },
    'ndd.quoc_gia':   { key: 'ndd.quoc_gia', label: 'Quốc gia của người đại diện', type: 'text' }
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
        { tag: 'so_cccd', type: 'cccd' },
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
    /* Wave P2 Lead-wire (merge abe6084 + rename): PLI_M06 có THÊM cột
     * 'Thời hạn góp vốn' {thoi_han_gop_von} (D2.2=A) so với các mẫu khác cùng
     * tên loop nguồn 'ds_thanh_vien' (M09/M02...). Export conflict guard
     * (LOCKED v1) cấm cùng tên loop khác contract giữa các mẫu → M06 dùng
     * TÊN LOOP RIÊNG trùng semantic_key manifest; draft M06 thực tế rỗng
     * (section mới có meta) nên không cần migration — cùng chính sách D2.9. */
    ds_thanh_vien_tnhh: {
      label: 'Danh sách thành viên công ty TNHH (cập nhật)',
      minRows: 2, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'so_cccd', type: 'cccd' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'von_dong_gop', type: 'money' },
        { tag: 'ty_le_von', type: 'percent' },
        { tag: 'thoi_han_gop_von', type: 'text' },
        { tag: 'chu_ky', type: 'outputOnly' }
      ],
      duplicateKeys: ['so_cccd'],
      outputOnlyTags: ['chu_ky']
    },
    /* Wave m09-rebuild (merge cfdefcd + Lead chèn mục 7 @ 11861b6): D3.2=A —
     * PLI_M09 dùng TÊN LOOP RIÊNG ds_thanh_vien_hop_danh 14 cột theo Mẫu 9
     * Phụ lục I TT 68/121 (loop cũ ds_thanh_vien 10 cột trả lại cho M02).
     * 3 cột mới so với 10 cột cũ: loai_tai_san_gop_von, thoi_han_gop_von,
     * ghi_chu. Draft M09 thực tế rỗng nên migration chỉ là tiền tố
     * ds_thanh_vien. -> ds_thanh_vien_hop_danh. (chính sách D2.9). */
    ds_thanh_vien_hop_danh: {
      label: 'Danh sách thành viên công ty hợp danh',
      minRows: 2, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'so_cccd', type: 'cccd' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'von_dong_gop', type: 'money' },
        { tag: 'ty_le_von', type: 'percent' },
        { tag: 'loai_tai_san_gop_von', type: 'text' },
        { tag: 'thoi_han_gop_von', type: 'text' },
        { tag: 'ghi_chu', type: 'text' },
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
        { tag: 'so_cccd', type: 'cccd' },
        { tag: 'quoc_tich', type: 'text' },
        /* P2A (D2.3=A): cột Dân tộc của PLI_M07 trước đây không được gắn the
         * trong khai báo inline (manifest loop_audit.missing_cols col 6) ->
         * spec tools/form_specs/formation/PLI_M07.json đã gắn {dan_toc};
         * khai metadata tại đây để cột không rơi về text mặc định. */
        { tag: 'dan_toc', type: 'text' },
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
      /* [F0L 2026-09-06] TT 121/2026 thay Mẫu 10 — bảng 18 cột (ảnh p49,
       * inventory PLI_M10.json; spec formation/PLI_M10.json ds_cshhl_2026):
       * 'Quyền chi phối'/'Ghi chú' và 2 cột tỷ lệ đơn của 2025 bị THAY bằng
       * 6 cột tỷ lệ trực tiếp/gián tiếp/tổng (cột Tổng = output-only computed
       * 11=9+10 / 14=12+13 theo O2-policy) + Thành viên hợp danh + Nhóm cá
       * nhân quan hệ gia đình/hợp đồng + Kiểm soát doanh nghiệp + Người quản
       * lý DN. Tag 2025 (ty_le, ty_le_co_phan, quyen_chi_phoi, ghi_chu và bộ
       * tổ chức ten_to_chuc/ma_so_dn/ngay_cap/noi_cap của PLI_M11 bị bãi bỏ)
       * KHÔNG còn trong template — draft cũ giữ nguyên, render theo cột mới. */
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'gioi_tinh', type: 'text' },
        { tag: 'so_giay_to', type: 'text' },
        { tag: 'quoc_tich', type: 'text' },
        { tag: 'dan_toc', type: 'text' },
        { tag: 'dia_chi', type: 'text' },
        { tag: 'ty_le_von_dieule_truc_tiep', type: 'percent' },
        { tag: 'ty_le_von_dieule_gian_tiep', type: 'percent' },
        { tag: 'ty_le_von_dieule_tong', type: 'percent', outputOnly: true,
          computed: 'sum(ty_le_von_dieule_truc_tiep, ty_le_von_dieule_gian_tiep)' },
        { tag: 'ty_le_co_phan_truc_tiep', type: 'percent' },
        { tag: 'ty_le_co_phan_gian_tiep', type: 'percent' },
        { tag: 'ty_le_co_phan_tong', type: 'percent', outputOnly: true,
          computed: 'sum(ty_le_co_phan_truc_tiep, ty_le_co_phan_gian_tiep)' },
        { tag: 'thanh_vien_hop_danh', type: 'text' },
        { tag: 'nhom_ca_nhan_quan_he', type: 'text' },
        { tag: 'kiem_soat_doanh_nghiep', type: 'text' },
        { tag: 'nguoi_quan_ly_doanh_nghiep', type: 'text' }
      ],
      duplicateKeys: ['so_giay_to'],
      outputOnlyTags: ['ty_le_von_dieule_tong', 'ty_le_co_phan_tong']
    },
    ds_tv_ho_gia_dinh: {
      label: 'Các thành viên hộ gia đình',
      minRows: 0, maxRows: null, required: false,
      allowAdd: true, allowDelete: true, allowReorder: true,
      confirmDeleteNonEmpty: true, requirePrimary: false,
      columns: [
        { tag: 'ho_ten', type: 'text', required: true },
        { tag: 'ngay_sinh', type: 'text' },
        { tag: 'so_cccd', type: 'cccd' },
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

  /* Every editable-grid contract exposes this additive slot.  An empty slot
   * deliberately preserves the legacy validator path below; form/spec owners
   * can add declarative rules without changing existing hard-coded behavior. */
  Object.keys(GRID_META).forEach(function (name) {
    if (!Array.isArray(GRID_META[name].cross_field_rules)) {
      GRID_META[name].cross_field_rules = [];
    }
  });

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
     * D7.3=A (docs/decision_registry.md packet D7, wave P2A 2026-08-27):
     * bảng ngành của phần ĐƯỢC CHỌN bắt buộc >= 1 ngành khi công bố thành
     * lập -> required:true + minRows:1. required chặn 0 dòng dữ liệu
     * (INDUSTRY_REQUIRED), minRows là rào cản thứ hai khi có dòng nhưng
     * chưa đủ (validateGridLoop); grid KHÔNG được chọn vẫn im hoàn toàn
     * nhờ activeWhen (không sinh lỗi giả). */
    'PLI_M72': {
      loops: {
        ds_nganh_dntn: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Doanh nghiệp tư nhân)',
          required: true, minRows: 1,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['DNTN'] } },
          semanticKey: 'ds_nganh_dntn', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_tnhh_1tv: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty TNHH một thành viên)',
          required: true, minRows: 1,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['TNHH_1TV'] } },
          semanticKey: 'ds_nganh_tnhh_1tv', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_tnhh_2tv: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty TNHH hai thành viên trở lên)',
          required: true, minRows: 1,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['TNHH_2TV'] } },
          semanticKey: 'ds_nganh_tnhh_2tv', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_ctcp: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty cổ phần)',
          required: true, minRows: 1,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['CTCP'] } },
          semanticKey: 'ds_nganh_ctcp', syncGroup: 'ds_nganh_pli_m72'
        }),
        ds_nganh_dhdn: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách ngành nghề kinh doanh (Công ty hợp danh)',
          required: true, minRows: 1,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['DHDN'] } },
          semanticKey: 'ds_nganh_dhdn', syncGroup: 'ds_nganh_pli_m72'
        }),
        /* [Owner P2=A 2026-09-03] 4 lưới thành viên/cổ đông nested-grid
         * rebuild từ P2 lane — activeWhen theo đúng variant, syncGroup
         * riêng từng loại vì cột và semantic khác nhau. */
        ds_thanh_vien_tnhh_2tv: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách thành viên (Công ty TNHH hai thành viên trở lên)',
          required: true, minRows: 2,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['TNHH_2TV'] } },
          semanticKey: 'ds_thanh_vien_tnhh_2tv',
          syncGroup: 'ds_thanh_vien_tnhh_2tv'
        }),
        ds_co_dong_sang_lap_ctcp: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách cổ đông sáng lập (Công ty cổ phần)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['CTCP'] } },
          semanticKey: 'ds_co_dong_sang_lap_ctcp',
          syncGroup: 'ds_co_dong_sang_lap_ctcp'
        }),
        ds_co_dong_nuoc_ngoai_ctcp: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách cổ đông là nhà đầu tư nước ngoài (Công ty cổ phần)',
          required: false, minRows: 0,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['CTCP'] } },
          semanticKey: 'ds_co_dong_nuoc_ngoai_ctcp',
          syncGroup: 'ds_co_dong_nuoc_ngoai_ctcp'
        }),
        ds_thanh_vien_hop_danh_dhdn: mkGrid(GRID_META.ds_nganh, {
          label: 'Danh sách thành viên hợp danh (Công ty hợp danh)',
          required: true, minRows: 2,
          activeWhen: { valueOf: { key: 'dn.loai_hinh', equals: ['DHDN'] } },
          semanticKey: 'ds_thanh_vien_hop_danh_dhdn',
          syncGroup: 'ds_thanh_vien_hop_danh_dhdn'
        })
      }
    },
    /* m09-rebuild (D3.2=A): PLI_M09 — bảng 14 cột Mẫu 9 Phụ lục I TT 68/121.
     * Loop riêng ds_thanh_vien_hop_danh (tránh EXPORT_LOOP_CONTRACT_CONFLICT
     * với ds_thanh_vien 10 cột của PLI_M02 — tiền lệ M06 ds_thanh_vien_tnhh).
     * minRows 2: công ty hợp danh phải có ÍT NHẤT 2 thành viên hợp danh
     * (Điều 20 Luật Doanh nghiệp; khớp manifest min_rows). */
    'PLI_M09': {
      loops: {
        ds_thanh_vien_hop_danh: mkGrid(GRID_META.ds_thanh_vien_hop_danh, {
          label: 'Danh sách thành viên công ty hợp danh',
          semanticKey: 'ds_thanh_vien_hop_danh'
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
        }),
        /* Wave R3B1 (2026-08-27): HAI bảng thành viên hộ gia đình của
         * PLII_M02 (census manifest section a4_tv_hgd_sau_thay_doi = blocks
         * B072 ghep 10 cột và c7_tv_hgd_cap_doi = blocks B137/B129). Tập cột
         * GIỐNG HẾT GRID_META.ds_tv_ho_gia_dinh (M01) nhưng NGỮ CẢNH khác ->
         * key riêng, KHÔNG auto-sync (manifest ghi chú "key riêng"; cùng
         * nguyên tắc PLAN A như D4.1=A), chu_ky outputOnly đúng D2.4=A.
         *
         * TRẠNG THÁI: metadata sẵn sàng nhưng entry spec rebuild CHƯA được
         * khai ở tools/form_specs/household/PLII_M02.json vì file đó bị test
         * contract lane khác ghim cứng tập occurrence_id (tools/
         * test_industry_household.py t_m02_spec_occurrence_identity yêu cầu
         * đếm entry == 1 cho MÔI entry và tập id == 4 id ngành; tools/census/
         * p1_c_verify_plii_m02.py cũng vậy) - ngoài ownership lane R3B1.
         * Bỏ khoá ngay khi Lead/L3 mở tập id (thêm 2 id + spec list 10 cột).
         * Loop chưa tồn tại trong blocks -> resolver trả meta này KHÔNG đổi
         * hành vi runtime hiện có. */
        tv_hgd_sau_thay_doi: mkGrid(GRID_META.ds_tv_ho_gia_dinh, {
          label: 'Danh sách các thành viên hộ gia đình đăng ký hộ kinh doanh sau khi thay đổi',
          semanticKey: 'tv_hgd_sau_thay_doi'
        }),
        tv_hgd_cap_doi: mkGrid(GRID_META.ds_tv_ho_gia_dinh, {
          label: 'Thông tin về các thành viên hộ gia đình đăng ký hộ kinh doanh (cấp đổi/đăng ký lại)',
          semanticKey: 'tv_hgd_cap_doi'
        })
      }
    },
    /* Wave P2A (2026-08-27): PLI_M13 - NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT SAU KHI
     * THAY ĐỔI (census manifest section ndd_pl_sau_thay_doi, kind
     * editable-grid, status missing_grid; spec rebuild
     * tools/form_specs/change/PLI_M13.json). Chân trang 2 của Mẫu 13: "Ghi
     * thông tin của TẤT CẢ người đại diện theo pháp luật trong trường hợp
     * sau khi thay đổi công ty có nhiều hơn 01 người đại diện theo pháp
     * luật" -> D2.6=A dựng GRID nhiều dòng thay cho 1 bộ field; D2.7=A
     * minRows 1 / maxRows null. 7 cột đúng manifest required_columns
     * (alias ten tag ngắn như bộ người M02/M12/M15).
     * KHÔNG discriminator: nguồn Mẫu 13 chỉ có MỘT row-type (không có nhóm
     * "người đại diện theo ủy quyền" như M02/M15) -> không tự chế loai_dong.
     * KHÔNG cột Chữ ký: nguồn không có ô ký trong mục này (ký ở phần cuối
     * mẫu) -> D2.4=A không áp dụng cho bảng này. */
    'PLI_M13': {
      loops: {
        ds_ndd_pl_sau_thay_doi: {
          label: 'Người đại diện theo pháp luật sau khi thay đổi',
          minRows: 1, maxRows: null, required: false,
          allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: true, requirePrimary: false,
          columns: [
            { tag: 'ho_ten', type: 'text', required: true },
            { tag: 'ngay_sinh', type: 'text' },
            { tag: 'gioi_tinh', type: 'text' },
            { tag: 'so_cccd', type: 'cccd' },
            { tag: 'chuc_danh', type: 'text' },
            { tag: 'dia_chi', type: 'text' },
            { tag: 'quoc_gia', type: 'text' }
          ],
          duplicateKeys: ['so_cccd'],
          outputOnlyTags: [],
          semanticKey: 'ds_ndd_pl_sau_thay_doi'
        }
      }
    },
    /* Wave P2A (2026-08-27): PLII_M07 (GCN ĐKHKD) mục 7 - D2.8=A KEY RIÊNG
     * ds_thanh_vien_hkd_gcn, KHÔNG subset contract ds_tv_ho_gia_dinh của
     * M01/M02 vì tập cột KHÁC thật (nguồn PL2_Mau_07 P035-P041 = blocks
     * B027-B033): STT | Tên thành viên | Quốc tịch | Nơi ở hiện tại | Nơi
     * thường trú | Số định danh cá nhân | Ghi chú - KHÔNG có ngày sinh/
     * giới tính/dân tộc/chữ ký. Chu thich của mẫu ("chỉ ghi trong trường hợp
     * các thành viên hộ gia đình đăng ký thành lập hộ kinh doanh") -> bảng
     * TUỲ CHỌN (minRows 0, required false), khác ds_nganh (minRows 1). */
    'PLII_M07': {
      loops: {
        ds_thanh_vien_hkd_gcn: {
          label: 'Danh sách thành viên hộ gia đình đăng ký thành lập hộ kinh doanh',
          minRows: 0, maxRows: null, required: false,
          allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: true, requirePrimary: false,
          columns: [
            { tag: 'ten_thanh_vien', type: 'text', required: true },
            { tag: 'quoc_tich', type: 'text' },
            { tag: 'noi_o_hien_tai', type: 'text' },
            { tag: 'noi_thuong_tru', type: 'text' },
            { tag: 'so_cccd', type: 'cccd' },
            { tag: 'ghi_chu', type: 'text' }
          ],
          duplicateKeys: ['so_cccd'],
          outputOnlyTags: [],
          semanticKey: 'ds_thanh_vien_hkd_gcn'
        }
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

  /* _row_id dùng được: chuỗi khác rỗng và không phải chữ 'NaN'/'undefined'
   * (draft hỏng/producer lạ có thể chứa id rác - Class 9: row id NaN).
   * Id chuỗi lạ khác (vd 'member-stable-1') vẫn GIỮ nguyên - id chỉ cần
   * ổn định trong phiên, không bắt buộc đúng pattern của makeRowId. */
  function isUsableRowId(id) {
    return typeof id === 'string' && id !== '' &&
      id !== 'NaN' && id !== 'undefined';
  }

  /* Đảm bảo mọi row trong store.loops có _row_id (mutate tại chỗ).
   * Đồng thời migration canonical: ds_nganh_kinh_doanh -> ds_nganh khi chưa
   * có ds_nganh (giữ nguyên dữ liệu); KHÔNG đụng nganh_bo_sung/nganh_xoa_bo/
   * nganh_truoc_thay_doi.
   * Class 9 (defect registry: ô Tên ngành 'undefined', Mã ngành '6') - chuẩn
   * hoá AN TOÀN ngay ở lớp dữ liệu, mọi chỗ hiển thị/binding/export chỉ cần
   * đọc store:
   *  - row KHÔNG phải object (null/scalar/mảng từ draft legacy hỏng) -> thay
   *    bằng dòng object rỗng {giữ số dòng và thứ tự; scalar không thể map an
   *    toàn vào tag nào nên bỏ dữ liệu thay vì chế ngữ nghĩa};
   *  - giá trị nullish (undefined/null) trong row -> chuỗi rỗng (JSON round
   *    trip khôi phục draft không bao giờ tái sinh 'undefined' khi binding);
   *  - _row_id thiếu/rác ('NaN', 'undefined', số, rỗng) -> gán id mới hợp lệ
   *    (id chỉ có ý nghĩa kỹ thuật trong phiên, không mất dữ liệu kê khai). */
  function normalizeStoreLoops(store) {
    if (!store || typeof store !== 'object') return store;
    var loops = store.loops = store.loops || {};
    /* Guard draft hỏng: loops là primitive (chuỗi/số) thì không gán/đổi được
     * gì (strict mode ném khi ghi index chuỗi) -> bỏ qua chuẩn hoá, không ném. */
    if (!loops || typeof loops !== 'object') return store;
    if (loops.ds_nganh_kinh_doanh && !loops.ds_nganh) {
      loops.ds_nganh = loops.ds_nganh_kinh_doanh;
      delete loops.ds_nganh_kinh_doanh;
    }
    Object.keys(loops).forEach(function (name) {
      var rows = loops[name];
      /* Guard draft hỏng: loop truthy nhưng KHÔNG phải mảng (object/chuỗi/số)
       * trước đây ném TypeError ở .forEach -> chuẩn hoá về [] để bỏ dữ liệu
       * hỏng an toàn thay vì làm rơi cả luồng load draft. */
      if (!Array.isArray(rows)) {
        loops[name] = [];
        return;
      }
      rows.forEach(function (r, ix) {
        if (!r || typeof r !== 'object' || Array.isArray(r)) {
          r = {};          // row scalar/null/mảng: bỏ rác, giữ dòng + thứ tự
          rows[ix] = r;    // rồi chạy tiếp chuẩn hoá như row thường (có id)
        }
        Object.keys(r).forEach(function (k) {
          if (k.charAt(0) === '_') return; // field nội bộ xử lý riêng dưới
          if (r[k] === undefined || r[k] === null) r[k] = '';
        });
        if (!isUsableRowId(r._row_id)) r._row_id = makeRowId();
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
  /* Điện thoại/fax: chỉ chữ số sau khi bỏ dấu ngăn cách (khoảng trắng, chấm,
   * gạch nối, ngoặc, dấu +); dài 8-15 số (số VN 9-10 số, có đầu số quốc tế).
   * Class 14: 'dt: (028) 3825abc' / 'khong co so' phải là lỗi. */
  var PHONE_STRIP_RE = /[\s.\-()+]/g;
  /* Website: có host dạng domain (ít nhất một dấu chấm, TLD chữ cái >= 2),
   * scheme http(s) tuỳ chọn, port tuỳ chọn, path/query/fragment không có
   * khoảng trắng. Class 14: 'khong phai url' / 'http://' phải là lỗi. */
  var WEBSITE_RE =
    /^(?:https?:\/\/)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+(?::\d{1,5})?(?:[\/?#]\S*)?$/i;

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
      case 'phone': {
        var digits = v.replace(PHONE_STRIP_RE, '');
        if (!/^\d{8,15}$/.test(digits))
          return err('PHONE', 'Số điện thoại/fax không hợp lệ (chỉ gồm chữ số, '
            + 'có thể ngăn cách bởi khoảng trắng/dấu chấm/gạch/ngoặc): ' + v);
        break;
      }
      case 'website':
        if (!WEBSITE_RE.test(v))
          return err('WEBSITE', 'Địa chỉ website không hợp lệ (ví dụ đúng: '
            + 'www.congty.vn): ' + v);
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

  /* Class 14: các type cột bảng lặp được kiểm chứng nội dung (validateGridLoop
   * dùng lại validateField cho từng ô CÓ dữ liệu). 'text' và các type hiển thị
   * (readonly/outputOnly/radio/checkbox) không thuộc danh sách này. */
  var VALIDATABLE_COL_TYPES = ['cccd', 'email', 'phone', 'website', 'mst'];

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

  /* O3 export guard: SECTION-contract kind mới đang ACTIVE với store? Thuần,
   * không DOM. activeWhen đọc từ entry hoặc spec; số dòng business-data của
   * nested-grid do module tương ứng đếm (blank UI row / dòng chỉ có
   * discriminator / ô outputOnly-stt không tính). Không khai activeWhen ->
   * luôn active (hành vi cũ). Dùng chung bởi validateSectionEntry và export
   * guard (GridCtl.exportLoops) để "dữ liệu cũ của section inactive" không
   * lọt payload export. */
  function isActiveSection(entry, rows, st) {
    if (!entry) return true;
    var spec = entry.spec || {};
    var aw = entry.activeWhen || spec.activeWhen || null;
    if (!aw) return true;
    var count = 0;
    if (entry.kind === 'nested-grid') {
      var NG = p2TableModule('NestedGrid');
      count = NG && typeof NG.businessRowsOf === 'function'
        ? NG.businessRowsOf(spec, rows || []).length : 0;
    }
    return evalActiveWhen(aw, count, st);
  }

  /* Declarative cross-field rules. Supported contract forms are intentionally
   * small: {rule:'sum', tag|tags, equals|value, severity?, code?, when?} and
   * expression strings such as "sum(ty_le) == 100". Unknown rules are ignored
   * so introducing metadata ahead of a validator upgrade cannot break export. */
  function validateCrossFieldRules(docId, name, rules, rows, filled, tags, push) {
    (rules || []).forEach(function (spec) {
      if (!spec) return;
      var text = typeof spec === 'string' ? spec : String(spec.rule || '');
      var m = text.match(/^\s*sum\(\s*([^)]+?)\s*\)\s*(==|=|<=|>=|<|>)\s*(-?\d+(?:[.,]\d+)?)\s*$/i);
      var tag = null, op = null, expected = null;
      if (m) {
        tag = m[1].trim();
        op = m[2] === '=' ? '==' : m[2];
        expected = Number(m[3].replace(',', '.'));
      } else if (typeof spec === 'object' && (spec.rule === 'sum' || spec.type === 'sum')) {
        tag = spec.tag || (spec.tags && spec.tags[0]);
        op = spec.operator || '==';
        expected = spec.equals != null ? spec.equals : spec.value;
        expected = expected == null ? null : Number(expected);
      }
      if (!tag || !op || expected == null || isNaN(expected) ||
          (tags || []).indexOf(tag) < 0) return;
      var hasValue = false;
      var sum = 0;
      filled.forEach(function (r) {
        var n = parseMoney((r || {})[tag]);
        if (n != null) { hasValue = true; sum += n; }
      });
      if (!hasValue) return;
      var ok = op === '==' ? Math.round(sum * 100) === Math.round(expected * 100) :
        op === '<=' ? sum <= expected : op === '>=' ? sum >= expected :
        op === '<' ? sum < expected : sum > expected;
      if (ok) return;
      var cfg = typeof spec === 'object' ? spec : {};
      var code = cfg.code || 'CROSS_FIELD_RULE';
      var severity = cfg.severity || 'blocking';
      push({
        key: name + '.cross_field.' + tag,
        docId: docId, code: code,
        message: (cfg.message || ('Tổng ' + tag + ' không thỏa điều kiện ' +
          op + ' ' + expected + ' (đang là ' + sum + ')')),
        severity: severity
      });
    });
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
      // Class 9: id thiếu/rác ('NaN'...) phải gán lại trước khi làm key lỗi
      // "loop:<name>:<row_id>:<tag>" - id rác làm lỗi trỏ sai ô trên UI.
      if (r && typeof r === 'object' && !isUsableRowId(r._row_id)) {
        r._row_id = makeRowId();
      }
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

    // Class 14: cột khai type kiểm chứng (cccd/email/phone/website/mst) phải
    // hợp lệ KHI CÓ dữ liệu - trước đây so_cccd các bảng người rơi về 'text'
    // nên text rác đi thẳng vào DOCX. Dùng lại validateField để message tiếng
    // Việt + code đồng bộ với field thường (CCCD/EMAIL/PHONE/WEBSITE/MST).
    (g.columns || []).forEach(function (col) {
      if (!col || VALIDATABLE_COL_TYPES.indexOf(col.type) < 0) return;
      if ((tags || []).indexOf(col.tag) < 0) return; // cột không có trong mẫu
      rows.forEach(function (r) {
        var raw = cellStr(r, col.tag);
        if (!raw) return;
        var errs = validateField({
          key: name + '.' + col.tag,
          label: col.label || col.tag,
          type: col.type,
          required: false
        }, raw, {});
        if (errs.length) {
          errAt(r, col.tag, errs[0].code,
            label + ' dòng ' + dispIdx(r) + ': ' + errs[0].message);
        }
      });
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

    validateCrossFieldRules(docId, name, g.cross_field_rules, rows, filled, tags, push);
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

  /* ==================== P2 R2 runtime wiring: section theo kind ===========
   * Nối 3 kind mới (fixed-matrix / nested-grid / output-table) vào runtime
   * mà KHÔNG viết lại component: module thuần đã merge (fixed-matrix.js,
   * nested-grid.js, output-table.js) chỉ được require/gọi.
   *
   * - FORM_TABLE_CONTRACTS: metadata SECTION THEO KIND cho fixture production
   *   tối thiểu (O1 PLI_M70, O2 PLI_M71, F2 PLI_M03, F3 PLI_M04, N1 PLI_M02)
   *   theo docs/p2_component_contracts.md (LOCKED v1) +
   *   docs/p2_fixture_candidates.md + app/data/table_specs/manifest.json
   *   (`kind`, `semantic_key`, `fixed_rows`, `required_columns`). KHÔNG chế
   *   field ngoài schema đã khóa; thiếu gì báo gap ở lane B3/Lead.
   * - Dispatcher VALIDATION: kind quyết định đường validate. editable-grid
   *   giữ NGUYÊN đường cũ (getGridMeta -> validateGridLoop); fixed-matrix/
   *   nested-grid/output-table đi qua module tương ứng; fallback legacy chỉ
   *   áp dụng cho loop CHƯA classify thành kind mới (KHÔNG nuốt kind mới).
   * - Draft: dữ liệu vẫn nằm trong store {values, checks, loops};
   *   fixed-matrix giữ giá trị phẳng values["<semantic_key>.<row>.<tag>"]
   *   (đúng contract mục 2.4), nested-grid giữ rows phẳng trong
   *   loops[<loop>] có `_row_id` + field discriminator; ô computed/outputOnly
   *   là PROJECTION (recompute lúc render/export) và KHÔNG BAO GIỜ được ghi
   *   ngược vào draft -> không có hai nguồn số liệu mâu thuẫn.
   * ---------------------------------------------------------------------- */

  /* Danh sách kind hợp lệ (docs/p2_component_contracts.md mục 0). */
  var P2_SECTION_KINDS =
    ['editable-grid', 'fixed-matrix', 'nested-grid', 'output-table'];

  /* Resolve platform module của một kind. Browser: index.html nạp 3 script
   * TRƯỚC form-domain.js nên globals đã có (window.P2Tables.* cho hai module
   * CommonJS-shim, window.OutputTable do UMD tự gắn). Node (test không GUI):
   * require trực tiếp trong cùng thư mục ui/. KHÔNG cache khi chưa thấy -
   * trả null để caller degrade an toàn (giữ hành vi cũ) thay vì crash. */
  var _p2ModuleCache = {};
  function p2TableModule(name) {
    if (_p2ModuleCache[name] !== undefined) return _p2ModuleCache[name];
    var fileMap = { FixedMatrix: './fixed-matrix.js', NestedGrid: './nested-grid.js',
      OutputTable: './output-table.js' };
    var seen = null;
    try {
      if (typeof self !== 'undefined') seen = self;
      else if (typeof globalThis !== 'undefined') seen = globalThis;
      else if (typeof window !== 'undefined') seen = window;
    } catch (e) { seen = null; }
    if (seen && seen.P2Tables && seen.P2Tables[name]) {
      _p2ModuleCache[name] = seen.P2Tables[name];
      return _p2ModuleCache[name];
    }
    if (seen && name === 'OutputTable' && seen.OutputTable) {
      _p2ModuleCache[name] = seen.OutputTable;
      return _p2ModuleCache[name];
    }
    if (typeof require === 'function' && fileMap[name]) {
      try {
        _p2ModuleCache[name] = require(fileMap[name]);
        return _p2ModuleCache[name];
      } catch (e) { /* nạp không được -> coi như chưa nối */ }
    }
    _p2ModuleCache[name] = null;
    return null;
  }

  /* Contract SECTION cho các fixture production P2 (docs/
   * p2_fixture_candidates.md). Mỗi entry:
   *   sectionId / semanticKey : khớp manifest.json của form đó
   *   kind                    : kind đã classify (nguồn chân lý của dispatcher)
   *   policy                  : CRUD row cho controller UI
   *   anchor                  : nơi renderer chèn component vào blocks L0/v3
   *                             hiện vẫn là paragraph rời (generator lane B2
   *                             chưa rebuild) - text đã chuẩn hoá bỏ dấu/thẻ
   *                             (so normText như render.normText)
   *   spec                    : shape của module đúng như contract v1
   * Các section CÙNG mẫu nhưng CHƯA đăng ký (vd lua_chon_khu_san_xuat,
   * co_phan_duoc_quyen_chao_ban của PLI_M04, ho_so_bao_gom của PLI_M70/M71)
   * VẪN render/validate bằng đường cũ - không bị nuốt bởi dispatcher. */
  var FORM_TABLE_CONTRACTS = {
    /* O1 - output-table, bảng chữ ký 2 ô độc lập (M70 #block signature). */
    'PLI_M70': {
      sections: [{
        sectionId: 'chu_ky_nguoi_nop_nguoi_nhan',
        semanticKey: 'chu_ky_tiep_nhan_ho_so',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        /* Sau regen W1 (d48eb7d): chuỗi ký nằm TRONG ô w:tbl 2x1 (block cuối),
         * không còn paragraph role 'signature' — match thuần text trên
         * blockPlainText của table; EOF tới hết mẫu. */
        anchor: { match: 'nguoi nop (ky va ghi ho ten)',
          endMatch: null, endRole: null },
        spec: {
          kind: 'output-table',
          section_id: 'chu_ky_nguoi_nop_nguoi_nhan',
          semantic_key: 'chu_ky_tiep_nhan_ho_so',
          form_id: 'PLI_M70',
          /* 5R2 (sync Lead sau merge lane B): bảng ký NGANG 1 hàng × 2 cột
           * (NGƯỜI NỘP | NGƯỜI NHẬN) — khớp template 1x2 + form_maps +
           * _find_output_grid_block horizontal + cellLabel flat-trải-cột. */
          grid: { rows: 1, cols: 2, labels: [
            'NGƯỜI NỘP\n(Ký và ghi họ tên)', 'NGƯỜI NHẬN\n(Ký và ghi họ tên)'
          ] },
          inputs: [],
          active_when: [],
          notes: 'Giữ grid khi xuất DOCX dù không nhập liệu (PLAN mục G).'
        }
      }, {
        /* [F1-OUT 2026-09-06] ho_so_bao_gom — O1 OUTPUT_ONLY, D6.3: 3 dòng
         * đánh số cố định in sẵn (không header/STT-header, đúng bản giấy);
         * CQĐKKD in mô tả tài liệu khi tiếp nhận nên không có mirror key. */
        sectionId: 'ho_so_bao_gom',
        semanticKey: 'ds_tai_lieu_ho_so_nop',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'ho so bao gom', endMatch: 'thoi gian tra ket qua' },
        spec: {
          kind: 'output-table',
          section_id: 'ho_so_bao_gom',
          semantic_key: 'ds_tai_lieu_ho_so_nop',
          form_id: 'PLI_M70',
          grid: { rows: 3, cols: 2,
            labels: [['1.', ''], ['2.', ''], ['3.', '']] },
          inputs: [],
          outputOnlyTags: [],
          active_when: []
        }
      }]
    },
    /* O2 - output-table biến thể 1 ô ký (chỉ cơ quan cấp tỉnh). */
    'PLI_M71': {
      sections: [{
        sectionId: 'chu_ky_co_quan_cap_tinh',
        semanticKey: 'chu_ky_cqb_m71',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        /* Sau regen W1: heading '(TÊN CƠ QUAN...)' là ô w:tbl 1x1; span kết
         * thúc TRƯỚC national-separator '_____' để dòng gạch giữ nguyên hiển
         * thị dưới lưới ký (không bị bọc dupe-anchor). */
        anchor: { match: 'ten co quan dang ky kinh doanh cap tinh',
          endMatch: '_____', endRole: 'national-separator' },
        spec: {
          kind: 'output-table',
          section_id: 'chu_ky_co_quan_cap_tinh',
          semantic_key: 'chu_ky_cqb_m71',
          form_id: 'PLI_M71',
          grid: { rows: 1, cols: 1,
            labels: [['(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)']] },
          inputs: [],
          active_when: []
        }
      }, {
        /* [F1-OUT 2026-09-06] ho_so_bao_gom_online — O1 OUTPUT_ONLY, D6.3:
         * bản điện tử của M70, 3 dòng đánh số cố định in sẵn. */
        sectionId: 'ho_so_bao_gom_online',
        semanticKey: 'ds_tai_lieu_ho_so_online',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'ho so bao gom', endMatch: 'thoi gian tra ket qua' },
        spec: {
          kind: 'output-table',
          section_id: 'ho_so_bao_gom_online',
          semantic_key: 'ds_tai_lieu_ho_so_online',
          form_id: 'PLI_M71',
          grid: { rows: 3, cols: 2,
            labels: [['1.', ''], ['2.', ''], ['3.', '']] },
          inputs: [],
          outputOnlyTags: [],
          active_when: []
        }
      }]
    },
    /* ==================== F1-OUT (2026-09-06): 11 section O1 OUTPUT_ONLY ====
     * Các lưới do CQĐKKD phát hành — KHÔNG có input nào (O1: render từ hồ sơ
     * /canonical store khi có, ô không có dữ liệu in RỖNG đúng pháp định).
     * Cơ chế render: grid.cells per-cell mirror binding — output-table.js vẽ
     * span.mirror-fld read-only (cùng class với render.js band mirror); blocks
     * mirror run tương ứng do converter sinh từ the {key} trong template
     * (tools/build_form_maps.py _build_output_table_grid + docx_to_blocks
     * _bind_output_grid_mirrors). outputOnlyTags = danh sách mirror key của
     * section (không phải cột nhập). Anchor heading-paragraph được render.js
     * GIỮ hiển thị (không bọc dupe-anchor) — phần nguồn phía sau bị thay bằng
     * component grid. */
    /* F1O-1 - M52 khung rà soát 4 nhóm: 4 hàng DN/CN/VPĐD/ĐĐKD; D4.2=A tách
     * key mã số (ma_so_van_ban giữ cho DN; ma_so_cn/ma_so_vpdd/ma_so_ddkd). */
    'PLI_M52': {
      sections: [{
        sectionId: 'khung_ra_soat_4_nhom',
        semanticKey: 'ra_soat_thong_tin_4_nhom',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'de nghi doanh nghiep ra soat, kiem tra doi chieu',
          endMatch: 'sau khi ra soat, de nghi doanh nghiep gui' },
        spec: {
          kind: 'output-table',
          section_id: 'khung_ra_soat_4_nhom',
          semantic_key: 'ra_soat_thong_tin_4_nhom',
          form_id: 'PLI_M52',
          grid: {
            rows: 5, cols: 8,
            labels: [
              ['Nhóm', 'Tên', 'Mã số', 'Địa chỉ', 'Điện thoại',
                'Người đại diện theo pháp luật /\nNgười đứng đầu',
                'Đơn vị chủ quản (đối với địa điểm kinh doanh)',
                'Tình trạng pháp lý /\nTình trạng hoạt động'],
              ['1. Doanh nghiệp', '', '', '', '', '', '', ''],
              ['2. Chi nhánh', '', '', '', '', '', '', ''],
              ['3. Văn phòng đại diện', '', '', '', '', '', '', ''],
              ['4. Địa điểm kinh doanh', '', '', '', '', '', '', '']
            ],
            cells: [
              [{ text: 'Nhóm' }, { text: 'Tên' }, { text: 'Mã số' },
                { text: 'Địa chỉ' }, { text: 'Điện thoại' },
                { text: 'Người đại diện theo pháp luật /\nNgười đứng đầu' },
                { text: 'Đơn vị chủ quản (đối với địa điểm kinh doanh)' },
                { text: 'Tình trạng pháp lý /\nTình trạng hoạt động' }],
              [{ text: '1. Doanh nghiệp' }, { mirror: 'dn.ten_tieng_viet' },
                { mirror: 'ma_so_van_ban' }, { mirror: 'dn.dia_chi_tru_so' },
                { mirror: 'dien_thoai_khac' }, { text: '' }, { text: '' },
                { mirror: 'tinh_trang_phap_ly' }],
              [{ text: '2. Chi nhánh' }, { mirror: 'cn.ten_tieng_viet' },
                { mirror: 'ma_so_cn' }, { mirror: 'dia_chi_khac' },
                { text: '' }, { mirror: 'nguoi_dung_dau.ten' }, { text: '' },
                { mirror: 'tinh_trang_hoat_dong' }],
              [{ text: '3. Văn phòng đại diện' }, { mirror: 'cn.ten_tieng_viet' },
                { mirror: 'ma_so_vpdd' }, { mirror: 'dia_chi_khac' },
                { text: '' }, { mirror: 'nguoi_dung_dau.ten' }, { text: '' },
                { mirror: 'tinh_trang_hoat_dong' }],
              [{ text: '4. Địa điểm kinh doanh' }, { mirror: 'cn.ten_tieng_viet' },
                { mirror: 'ma_so_ddkd' }, { mirror: 'dia_chi_khac' },
                { text: '' }, { mirror: 'nguoi_dung_dau.ten' }, { text: '' },
                { mirror: 'tinh_trang_hoat_dong' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['dn.ten_tieng_viet', 'ma_so_van_ban',
            'dn.dia_chi_tru_so', 'dien_thoai_khac', 'tinh_trang_phap_ly',
            'cn.ten_tieng_viet', 'ma_so_cn', 'ma_so_vpdd', 'ma_so_ddkd',
            'dia_chi_khac', 'nguoi_dung_dau.ten', 'tinh_trang_hoat_dong'],
          active_when: [],
          notes: 'O1 OUTPUT_ONLY; D4.2=A tách key ma_so theo nhóm; render ' +
            'từ canonical store, ô thiếu dữ liệu in trống (docs/' +
            'owner_decision_packet_v7.md, docs/decision_registry.md).'
        }
      }]
    },
    /* F1O-2 - M56 tiếp tục kinh doanh trước hạn cho "một hoặc một số" đơn vị:
     * 1 hàng mirror + 1 hàng trống pháp định (D6.3). */
    'PLI_M56': {
      sections: [{
        sectionId: 'cn_vppd_ddkd_tiep_tuc_truoc_han',
        semanticKey: 'don_vi_tiep_tuc_truoc_han',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'mot hoac mot so chi nhanh/van phong dai dien/dia diem',
          endMatch: 'neu doanh nghiep chi thong bao tiep tuc' },
        spec: {
          kind: 'output-table',
          section_id: 'cn_vppd_ddkd_tiep_tuc_truoc_han',
          semantic_key: 'don_vi_tiep_tuc_truoc_han',
          form_id: 'PLI_M56',
          grid: {
            rows: 3, cols: 4,
            labels: [
              ['Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)', 'Mã số',
                'Tên chi nhánh chủ quản (đối với địa điểm kinh doanh trực thuộc chi nhánh)', 'Mã số chi nhánh chủ quản'],
              ['', '', '', ''],
              ['', '', '', '']
            ],
            cells: [
              [{ text: 'Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)' },
                { text: 'Mã số' },
                { text: 'Tên chi nhánh chủ quản (đối với địa điểm kinh doanh trực thuộc chi nhánh)' },
                { text: 'Mã số chi nhánh chủ quản' }],
              [{ mirror: 'cn.ten_tieng_viet' }, { mirror: 'cn.ma_so' },
                { text: '' }, { text: '' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['cn.ten_tieng_viet', 'cn.ma_so'],
          active_when: []
        }
      }]
    },
    /* F1O-3 - M63 địa điểm trực thuộc bị thu hồi: header + 2 hàng trống
     * pháp định (không có loop key canonical trong hồ sơ). */
    'PLI_M63': {
      sections: [{
        sectionId: 'dia_diem_truc_thuoc_bi_thu_hoi',
        semanticKey: 'ddkd_truc_thuoc_bi_thu_hoi',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'co cac dia diem kinh doanh truc thuoc chi nhanh',
          endMatch: 'la chi nhanh/van phong dai dien/dia diem kinh doanh cua doanh nghiep sau' },
        spec: {
          kind: 'output-table',
          section_id: 'dia_diem_truc_thuoc_bi_thu_hoi',
          semantic_key: 'ddkd_truc_thuoc_bi_thu_hoi',
          form_id: 'PLI_M63',
          grid: {
            rows: 3, cols: 4,
            labels: [
              ['Tên địa điểm kinh doanh', 'Mã số/mã số thuế', 'Địa chỉ', 'Tình trạng pháp lý'],
              ['', '', '', ''],
              ['', '', '', '']
            ],
            cells: [
              [{ text: 'Tên địa điểm kinh doanh' }, { text: 'Mã số/mã số thuế' },
                { text: 'Địa chỉ' }, { text: 'Tình trạng pháp lý' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: [],
          active_when: []
        }
      }]
    },
    /* F1O-4a/4b - M66 hai danh sách chấm dứt (defect bo_ten_ma_x23: tách
     * section, mỗi đơn vị 1 bộ tên+mã trên 1 dòng). */
    'PLI_M66': {
      sections: [{
        sectionId: 'don_vi_dang_lam_thu_tuc_cham_dut',
        semanticKey: 'don_vi_dang_cham_dut',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'thong tin chi nhanh/van phong dai dien/dia diem kinh doanh dang lam thu tuc cham dut',
          endMatch: 'truong hop chi nhanh dang lam thu tuc cham dut hoat dong co dia diem' },
        spec: {
          kind: 'output-table',
          section_id: 'don_vi_dang_lam_thu_tuc_cham_dut',
          semantic_key: 'don_vi_dang_cham_dut',
          form_id: 'PLI_M66',
          grid: {
            rows: 3, cols: 5,
            labels: [
              ['Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)', 'Mã số/mã số thuế',
                'Số Giấy chứng nhận đăng ký hoạt động (trường hợp không có mã số/mã số thuế)', 'Ngày cấp', 'Nơi cấp'],
              ['', '', '', '', ''],
              ['', '', '', '', '']
            ],
            cells: [
              [{ text: 'Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)' },
                { text: 'Mã số/mã số thuế' },
                { text: 'Số Giấy chứng nhận đăng ký hoạt động (trường hợp không có mã số/mã số thuế)' },
                { text: 'Ngày cấp' }, { text: 'Nơi cấp' }],
              [{ mirror: 'cn.ten_tieng_viet' }, { mirror: 'cn.ma_so_2' },
                { text: '' }, { text: '' }, { text: '' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['cn.ten_tieng_viet', 'cn.ma_so_2'],
          active_when: []
        }
      }, {
        sectionId: 'ddkd_truc_thuoc_dang_cham_dut',
        semanticKey: 'ddkd_truc_thuoc_dang_cham_dut',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'co cac dia diem kinh doanh truc thuoc sau dang lam thu tuc cham dut',
          endMatch: 'dang tai thong bao nay tren cong thong tin quoc gia' },
        spec: {
          kind: 'output-table',
          section_id: 'ddkd_truc_thuoc_dang_cham_dut',
          semantic_key: 'ddkd_truc_thuoc_dang_cham_dut',
          form_id: 'PLI_M66',
          grid: {
            rows: 3, cols: 2,
            labels: [
              ['Tên địa điểm kinh doanh trực thuộc (ghi bằng chữ in hoa)', 'Mã số/mã số thuế'],
              ['', ''],
              ['', '']
            ],
            cells: [
              [{ text: 'Tên địa điểm kinh doanh trực thuộc (ghi bằng chữ in hoa)' },
                { text: 'Mã số/mã số thuế' }],
              [{ mirror: 'cn.ten_tieng_viet' }, { mirror: 'cn.ma_so_2' }],
              [{ text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['cn.ten_tieng_viet', 'cn.ma_so_2'],
          active_when: []
        }
      }]
    },
    /* F1O-5 - M67 (các) đơn vị chấm dứt sau đây: nhiều đơn vị/giấy. */
    'PLI_M67': {
      sections: [{
        sectionId: 'don_vi_cham_dut_sau_day',
        semanticKey: 'don_vi_cham_dut_m67',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'thong bao (cac) chi nhanh/van phong dai dien/dia diem kinh doanh sau day',
          endMatch: 'noi nhan' },
        spec: {
          kind: 'output-table',
          section_id: 'don_vi_cham_dut_sau_day',
          semantic_key: 'don_vi_cham_dut_m67',
          form_id: 'PLI_M67',
          grid: {
            rows: 3, cols: 5,
            labels: [
              ['Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)', 'Mã số đơn vị hoặc mã số thuế',
                'Địa chỉ', 'Điện thoại/Fax/Thư điện tử/Website (nếu có)',
                'Chi nhánh chủ quản (tên, địa chỉ, mã số - đối với địa điểm kinh doanh trực thuộc chi nhánh)'],
              ['', '', '', '', ''],
              ['', '', '', '', '']
            ],
            cells: [
              [{ text: 'Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằng chữ in hoa)' },
                { text: 'Mã số đơn vị hoặc mã số thuế' }, { text: 'Địa chỉ' },
                { text: 'Điện thoại/Fax/Thư điện tử/Website (nếu có)' },
                { text: 'Chi nhánh chủ quản (tên, địa chỉ, mã số - đối với địa điểm kinh doanh trực thuộc chi nhánh)' }],
              [{ mirror: 'cn.ten_tieng_viet' }, { mirror: 'cn.ma_so' },
                { mirror: 'cn.dia_chi' }, { text: '' }, { text: '' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['cn.ten_tieng_viet', 'cn.ma_so', 'cn.dia_chi'],
          active_when: []
        }
      }]
    },
    /* F1O-6 - M68 danh sách đơn vị chấm dứt khi DN giải thể. */
    'PLI_M68': {
      sections: [{
        sectionId: 'don_vi_cham_dut_khi_doanh_nghiep_giai_the',
        semanticKey: 'don_vi_cham_dut_giai_the',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'cac chi nhanh, van phong dai dien, dia diem kinh doanh sau cua doanh nghiep dang lam thu tuc cham dut',
          endMatch: 'truong hop giai the doanh nghiep theo quy dinh tai dieu 208' },
        spec: {
          kind: 'output-table',
          section_id: 'don_vi_cham_dut_khi_doanh_nghiep_giai_the',
          semantic_key: 'don_vi_cham_dut_giai_the',
          form_id: 'PLI_M68',
          grid: {
            rows: 3, cols: 2,
            labels: [
              ['Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh', 'Mã số hoặc mã số thuế'],
              ['', ''],
              ['', '']
            ],
            cells: [
              [{ text: 'Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh' },
                { text: 'Mã số hoặc mã số thuế' }],
              [{ mirror: 'cn.ten_tieng_viet' }, { mirror: 'cn.ma_so' }],
              [{ text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: ['cn.ten_tieng_viet', 'cn.ma_so'],
          active_when: []
        }
      }]
    },
    /* F1O-7/8 - M70 + M71 "Hồ sơ bao gồm:" 3 dòng đánh số cố định, không
     * header (in sẵn dòng trống pháp định như bản giấy — D6.3): đăng ký ở
     * entry PLI_M70 / PLI_M71 phía trên (section thứ 2 của từng form). */
    /* F1O-9/10 - M75 hai lưới khôi phục: 3 dòng định loại đơn vị + địa điểm
     * trực thuộc (header + hàng trống pháp định — D6.3). */
    'PLI_M75': {
      sections: [{
        sectionId: 'cn_vppd_ddkd_khoi_phuc',
        semanticKey: 'don_vi_khoi_phuc_cua_dn',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'co cac chi nhanh/van phong dai dien/dia diem kinh doanh',
          endMatch: 'doi voi chi nhanh/van phong dai dien/dia diem kinh doanh thi ghi' },
        spec: {
          kind: 'output-table',
          section_id: 'cn_vppd_ddkd_khoi_phuc',
          semantic_key: 'don_vi_khoi_phuc_cua_dn',
          form_id: 'PLI_M75',
          grid: {
            rows: 4, cols: 5,
            labels: [
              ['Loại đơn vị', 'Tên', 'Mã số/mã số thuế', 'Địa chỉ', 'Tình trạng pháp lý'],
              ['Chi nhánh', '', '', '', ''],
              ['Văn phòng đại diện', '', '', '', ''],
              ['Địa điểm kinh doanh', '', '', '', '']
            ],
            cells: [
              [{ text: 'Loại đơn vị' }, { text: 'Tên' }, { text: 'Mã số/mã số thuế' },
                { text: 'Địa chỉ' }, { text: 'Tình trạng pháp lý' }],
              [{ text: 'Chi nhánh' }, { text: '' }, { text: '' }, { text: '' }, { text: '' }],
              [{ text: 'Văn phòng đại diện' }, { text: '' }, { text: '' }, { text: '' }, { text: '' }],
              [{ text: 'Địa điểm kinh doanh' }, { text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: [],
          active_when: []
        }
      }, {
        sectionId: 'ddkd_truc_thuoc_khoi_phuc',
        semanticKey: 'ddkd_truc_thuoc_khoi_phuc',
        kind: 'output-table',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'co cac dia diem kinh doanh truc thuoc chi nhanh',
          endMatch: 'la chi nhanh/van phong dai dien/dia diem kinh doanh cua doanh nghiep sau' },
        spec: {
          kind: 'output-table',
          section_id: 'ddkd_truc_thuoc_khoi_phuc',
          semantic_key: 'ddkd_truc_thuoc_khoi_phuc',
          form_id: 'PLI_M75',
          grid: {
            rows: 3, cols: 4,
            labels: [
              ['Tên địa điểm kinh doanh', 'Mã số/mã số thuế', 'Địa chỉ', 'Tình trạng pháp lý'],
              ['', '', '', ''],
              ['', '', '', '']
            ],
            cells: [
              [{ text: 'Tên địa điểm kinh doanh' }, { text: 'Mã số/mã số thuế' },
                { text: 'Địa chỉ' }, { text: 'Tình trạng pháp lý' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }],
              [{ text: '' }, { text: '' }, { text: '' }, { text: '' }]
            ]
          },
          inputs: [],
          outputOnlyTags: [],
          active_when: []
        }
      }]
    },
    /* F2 - fixed-matrix nguồn vốn điều lệ: 5 dòng pháp lý + Tổng cộng
     * outputOnly; tag cột lấy ĐÚNG manifest required_columns. */
    'PLI_M03': {
      sections: [{
        sectionId: 'nguon_von_dieule',
        semanticKey: 'nguon_von_dieu_le',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'nguon von dieu le', matchRole: 'section-heading',
          endMatch: null, endRole: null }, // mục cuối của mẫu
        spec: {
          kind: 'fixed-matrix',
          section_id: 'nguon_von_dieule',
          semantic_key: 'nguon_von_dieu_le',
          form_id: 'PLI_M03',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'von_ngan_sach_nha_nuoc', label: 'Vốn ngân sách nhà nước' },
            { id: 'von_tu_nhan', label: 'Vốn tư nhân' },
            { id: 'von_nuoc_ngoai', label: 'Vốn nước ngoài' },
            { id: 'von_khac', label: 'Vốn khác' },
            { id: 'tong_cong', label: 'Tổng cộng', output_only: true }
          ],
          columns: [
            { tag: 'loai_nguon_von', inputType: 'readonly',
              header: 'Loại nguồn vốn' },
            { tag: 'so_tien_vnd_va_tuong_duong', inputType: 'money',
              header: 'Số tiền (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_cong', formula: 'sum(so_tien_vnd_va_tuong_duong)',
              target_tag: 'so_tien_vnd_va_tuong_duong' },
            { id: 'tong_cong', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ nguồn vốn điều lệ phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'so_tien_vnd_va_tuong_duong',
              valueKey: 'von_dieu_le', severity: 'blocking',
              code: 'CAPITAL_MISMATCH',
              message: 'Tổng cộng nguồn vốn điều lệ phải khớp Vốn điều lệ kê khai ở mục 5.' }
          ]
        }
      }]
    },
    /* F3 - fixed-matrix cơ cấu loại cổ phần + Tổng số (đối chiếu VĐL). */
    'PLI_M04': {
      sections: [{
        sectionId: 'co_cau_loai_co_phan',
        semanticKey: 'co_cau_loai_co_phan',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'thong tin ve co phan', matchRole: 'section-heading',
          endMatch: 'thong tin ve co phan duoc quyen chao ban', endRole: 'body' },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'co_cau_loai_co_phan',
          semantic_key: 'co_cau_loai_co_phan',
          form_id: 'PLI_M04',
          stt: { mode: 'generated' },
          fixed_rows: [
            { id: 'co_phan_pho_thong', label: 'Cổ phần phổ thông' },
            { id: 'cp_uu_dai_bieu_quyet', label: 'Cổ phần ưu đãi biểu quyết' },
            { id: 'cp_uu_dai_co_tuc', label: 'Cổ phần ưu đãi cổ tức' },
            { id: 'cp_uu_dai_hoan_lai', label: 'Cổ phần ưu đãi hoàn lại' },
            { id: 'cp_uu_dai_khac', label: 'Các cổ phần ưu đãi khác' },
            { id: 'tong_so', label: 'Tổng số', output_only: true }
          ],
          columns: [
            { tag: 'loai_co_phan', inputType: 'readonly', header: 'Loại cổ phần' },
            { tag: 'so_luong', inputType: 'money', header: 'Số lượng' },
            { tag: 'gia_tri_vnd', inputType: 'money', header: 'Giá trị (bằng số, VNĐ)' },
            { tag: 'ty_le_so_von_dieule', inputType: 'percent',
              header: 'Tỉ lệ so với vốn điều lệ (%)' }
          ],
          totals: [
            { id: 'tong_so', formula: 'sum(so_luong)', target_tag: 'so_luong' },
            { id: 'tong_so', formula: 'sum(gia_tri_vnd)', target_tag: 'gia_tri_vnd' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le_so_von_dieule', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ so với vốn điều lệ phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'gia_tri_vnd', valueKey: 'von_dieu_le',
              severity: 'blocking', code: 'CAPITAL_MISMATCH',
              message: 'Tổng số cổ phần (giá trị VNĐ) phải khớp Vốn điều lệ kê khai.' }
          ]
        }
      },
      /* Wave cap-von (merge fc07c69): bảng "Thông tin về cổ phần được quyền
       * chào bán" 2 cột (Loại cổ phần readonly + Số lượng) — 5 loại cổ phần +
       * Tổng số output_only sum(so_luong). Biểu mẫu KHÔNG yêu cầu đối chiếu
       * VĐL cho bảng này (không cross rule). Dòng 5 in 'Cổ phần ưu đãi khác'
       * (không có 'Các') — nguyên văn TT 121/2026 Mẫu 4 tr.5. */
      {
        sectionId: 'co_phan_duoc_quyen_chao_ban',
        semanticKey: 'co_phan_duoc_quyen_chao_ban',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'thong tin ve co phan duoc quyen chao ban',
          matchRole: 'body', endMatch: null, endRole: null },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'co_phan_duoc_quyen_chao_ban',
          semantic_key: 'co_phan_duoc_quyen_chao_ban',
          form_id: 'PLI_M04',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'co_phan_pho_thong', label: 'Cổ phần phổ thông' },
            { id: 'cp_uu_dai_bieu_quyet', label: 'Cổ phần ưu đãi biểu quyết' },
            { id: 'cp_uu_dai_co_tuc', label: 'Cổ phần ưu đãi cổ tức' },
            { id: 'cp_uu_dai_hoan_lai', label: 'Cổ phần ưu đãi hoàn lại' },
            { id: 'cp_uu_dai_khac', label: 'Cổ phần ưu đãi khác' },
            { id: 'tong_so', label: 'Tổng số', output_only: true }
          ],
          columns: [
            /* [Phase 3] tag định danh cột label (inputType vẫn readonly,
             * không tạo input) — thống nhất convention 3 section anh em
             * (co_cau 'loai_co_phan', M05 'loai_nguon_von', M01 tai_san
             * 'loai_tai_san_gop_von'); census required column tên đúng
             * 'loai_co_phan_chao_ban'. */
            { tag: 'loai_co_phan_chao_ban', inputType: 'readonly',
              header: 'Loại cổ phần được quyền chào bán' },
            { tag: 'so_luong', inputType: 'money', header: 'Số lượng' }
          ],
          totals: [
            { id: 'tong_so', formula: 'sum(so_luong)', target_tag: 'so_luong' }
          ],
          cross_field_rules: []
        }
      }]
    },
    /* Wave cap-von (merge fc07c69): PLI_M05 nguồn vốn điều lệ — bảng 3 cột
     * (Loại nguồn vốn readonly / Số tiền money / Tỷ lệ %) + 5 dòng (VNNSNN,
     * tư nhân, nước ngoài, khác, Tổng cộng output_only), GIỐNG HỆT M03 —
     * đối chiếu trực tiếp TT 121/2026 Mẫu 5 tr.4 (cũng là trang owner xem
     * screenshot). Rules như M03: percentSum warning + sumEqualsKey blocking
     * với valueKey von_dieu_le (mục 5). */
    'PLI_M05': {
      sections: [{
        sectionId: 'nguon_von_dieule',
        semanticKey: 'nguon_von_dieu_le',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'nguon von dieu le', matchRole: 'section-heading',
          endMatch: null, endRole: null },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'nguon_von_dieule',
          semantic_key: 'nguon_von_dieu_le',
          form_id: 'PLI_M05',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'von_ngan_sach_nha_nuoc', label: 'Vốn ngân sách nhà nước' },
            { id: 'von_tu_nhan', label: 'Vốn tư nhân' },
            { id: 'von_nuoc_ngoai', label: 'Vốn nước ngoài' },
            { id: 'von_khac', label: 'Vốn khác' },
            { id: 'tong_cong', label: 'Tổng cộng', output_only: true }
          ],
          columns: [
            { tag: null, inputType: 'readonly', header: 'Loại nguồn vốn' },
            { tag: 'so_tien_vnd_va_tuong_duong', inputType: 'money',
              header: 'Số tiền (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_cong', formula: 'sum(so_tien_vnd_va_tuong_duong)',
              target_tag: 'so_tien_vnd_va_tuong_duong' },
            { id: 'tong_cong', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ nguồn vốn điều lệ phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'so_tien_vnd_va_tuong_duong',
              valueKey: 'von_dieu_le', severity: 'blocking',
              code: 'CAPITAL_MISMATCH',
              message: 'Tổng cộng nguồn vốn điều lệ phải khớp Vốn điều lệ kê khai ở mục 5.' }
          ]
        }
      }]
    },
    /* P2C fixed-matrix (merge 1691728, Lead wire): tài sản góp vốn vào VỐN ĐẦU
     * TƯ của PLI_M01 - D1.2=B: "Các tài sản khác" là Ô MÔ TẢ TEXT (đính kèm
     * danh mục riêng), KHÔNG sub-grid; D1.1=A: Tổng số output_only computed,
     * đối chiếu von_dau_tu_so blocking (CAPITAL_MISMATCH). */
    'PLI_M01': {
      sections: [{
        sectionId: 'tai_san_gop_von_von_dau_tu',
        semanticKey: 'co_cau_tai_san_gop_von_dau_tu',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        /* [Fix ISS-3 re-shoot P2] heading 'Tài sản góp vốn:' của M01 là block
         * BODY (không phải section-heading) — matchRole sai làm contract
         * fail-close, mất totals computed (Tổng số thành ô nhập). */
        anchor: { match: 'tai san gop von', matchRole: 'body',
          endMatch: 'thong tin dang ky thue', endRole: 'section-heading' },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'tai_san_gop_von_von_dau_tu',
          semantic_key: 'co_cau_tai_san_gop_von_dau_tu',
          form_id: 'PLI_M01',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'dong_viet_nam', label: 'Đồng Việt Nam' },
            { id: 'ngoai_te_tu_do_chuyen_doi',
              label: 'Ngoại tệ tự do chuyển đổi (ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ)' },
            { id: 'vang', label: 'Vàng' },
            { id: 'quyen_su_dung_dat', label: 'Quyền sử dụng đất' },
            { id: 'quyen_so_huu_tri_tue', label: 'Quyền sở hữu trí tuệ' },
            { id: 'tai_san_khac',
              label: 'Các tài sản khác (ghi rõ loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản, có thể lập thành danh mục riêng kèm theo hồ sơ đăng ký doanh nghiệp)' },
            { id: 'tong_so', label: 'Tổng số', output_only: true }
          ],
          columns: [
            { tag: 'loai_tai_san_gop_von', inputType: 'readonly',
              header: 'Tài sản góp vốn' },
            { tag: 'chi_tiet_ngoai_te_tai_san_khac', inputType: 'text',
              header: 'Ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ / loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản' },
            { tag: 'gia_tri_vnd', inputType: 'money',
              header: 'Giá trị vốn của từng tài sản trong vốn đầu tư (bằng số, VNĐ)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_so', formula: 'sum(gia_tri_vnd)',
              target_tag: 'gia_tri_vnd' },
            { id: 'tong_so', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ tài sản góp vốn đầu tư phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'gia_tri_vnd',
              valueKey: 'von_dau_tu_so', severity: 'blocking',
              code: 'CAPITAL_MISMATCH',
              message: 'Tổng số tài sản góp vốn đầu tư phải khớp Vốn đầu tư kê khai.' }
          ]
        }
      }]
    },
    /* N1 - nested-grid PLI_M02: header nhiều hàng thật (rowspan/colspan VẬT LÝ)
     * + discriminator loai_dong (NĐDPL vs người ủy quyền).
     * Nguồn header: app/data/blocks/PLI_M02.json block 126 (header nối dính).
     * Khớp vật lý 14 cột: 'Vốn được ủy quyền' là nhóm GỘP 2 cột con
     * (VNĐ | Tỷ lệ (%)) - tag cột thứ hai lấy ĐÚNG `ty_le` từ
     * manifest.required_columns, KHÔNG tự chế. Gap đã ghi nhận (báo lane B3/
     * Lead): header nguồn còn 2 nhóm chưa đủ evidence để khai tag canonical -
     * "Tổng giá trị vốn được đại diện" và "Thời điểm đại diện phần vốn";
     * contract dưới KHÔNG khai chúng (absence, không mislabel), chờ owner/B2. */
    'PLI_M02': {
      sections: [{
        sectionId: 'nddpl_uy_quyen_chu_so_huu',
        semanticKey: 'ds_nddpl_uy_quyen_chu_so_huu',
        kind: 'nested-grid',
        policy: { allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: false },
        anchor: {
          match: 'thong tin ve nguoi dai dien theo phap luat/nguoi dai dien theo uy quyen cua chu so huu',
          matchRole: 'body',
          endMatch: 'von dieu le', endRole: 'section-heading'
        },
        spec: {
          kind: 'nested-grid',
          section_id: 'nddpl_uy_quyen_chu_so_huu',
          semantic_key: 'ds_nddpl_uy_quyen_chu_so_huu',
          loop: 'ds_nddpl_uy_quyen_chu_so_huu',
          form_id: 'PLI_M02',
          header_rows: [
            [
              { text: 'STT', rowspan: 2 },
              { text: 'Tên người đại diện theo pháp luật/người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ngày, tháng, năm sinh', rowspan: 2 },
              { text: 'Giới tính', rowspan: 2 },
              { text: 'Số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân', colspan: 3 },
              { text: 'Quốc tịch', rowspan: 2 },
              { text: 'Dân tộc', rowspan: 2 },
              { text: 'Địa chỉ liên lạc', rowspan: 2 },
              { text: 'Vốn được ủy quyền', colspan: 2 },
              { text: 'Chữ ký của người đại diện theo pháp luật/người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ghi chú (nếu có)', rowspan: 2 }
            ],
            [
              { text: 'Số' }, { text: 'Ngày cấp' }, { text: 'Cơ quan cấp' },
              { text: 'VNĐ' }, { text: 'Tỷ lệ (%)' }
            ]
          ],
          row_groups: [
            { group_id: 'ndd_uy_quyen',
              match: { tag: 'loai_dong', equals: 'ndd_uy_quyen' },
              required_columns: ['ten_nguoi_dai_dien', 'von_duoc_uy_quyen_vnd'] },
            { group_id: 'ndd_pl',
              match: { tag: 'loai_dong', equals: 'ndd_pl' },
              required_columns: ['ten_nguoi_dai_dien'] }
          ],
          discriminator: { tag: 'loai_dong', values: ['ndd_pl', 'ndd_uy_quyen'] },
          columns: ['stt', 'ten_nguoi_dai_dien', 'ngay_sinh', 'gioi_tinh',
            'giay_to_so', 'giay_to_ngay', 'giay_to_co_quan', 'quoc_tich',
            'dan_toc', 'dia_chi', 'von_duoc_uy_quyen_vnd', 'ty_le', 'chu_ky',
            'ghi_chu'
          ].map(function (tag, col_index) {
            return { tag: tag, col_index: col_index,
              type: tag === 'chu_ky' ? 'outputOnly' :
                (tag === 'stt' ? 'stt' :
                  ((tag === 'von_duoc_uy_quyen_vnd' || tag === 'ty_le')
                    ? 'money' : 'text')) };
          }),
          /* D2.7=A: min 1 dòng / max không giới hạn cho danh sách NĐDPL/ủy quyền. */
          min_rows: 1,
          max_rows: null,
          totals: [],
          cross_field_rules: []
        }
      }, {
        /* P2C fixed-matrix (merge 1691728, Lead wire): nguồn vốn điều lệ
         * 5 dòng pháp lý + Tổng cộng output_only (D1.1=A), cùng bộ key
         * canonical với F2 (PLI_M03) - sumEqualsKey đối chiếu VĐL blocking. */
        sectionId: 'nguon_von_dieule',
        semanticKey: 'nguon_von_dieu_le',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        /* [Fix ISS-1 re-shoot P2] endMatch=null chỉ hợp lệ cho section CUỐI
         * form — span tới EOF đã ẩn luôn section 8..12 của M02. */
        anchor: { match: 'nguon von dieu le', matchRole: 'section-heading',
          endMatch: 'tai san gop von', endRole: 'section-heading' },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'nguon_von_dieule',
          semantic_key: 'nguon_von_dieu_le',
          form_id: 'PLI_M02',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'von_ngan_sach_nha_nuoc', label: 'Vốn ngân sách nhà nước' },
            { id: 'von_tu_nhan', label: 'Vốn tư nhân' },
            { id: 'von_nuoc_ngoai', label: 'Vốn nước ngoài' },
            { id: 'von_khac', label: 'Vốn khác' },
            { id: 'tong_cong', label: 'Tổng cộng', output_only: true }
          ],
          columns: [
            { tag: 'loai_nguon_von', inputType: 'readonly',
              header: 'Loại nguồn vốn' },
            { tag: 'so_tien_vnd_va_tuong_duong', inputType: 'money',
              header: 'Số tiền (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_cong', formula: 'sum(so_tien_vnd_va_tuong_duong)',
              target_tag: 'so_tien_vnd_va_tuong_duong' },
            { id: 'tong_cong', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ nguồn vốn điều lệ phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'so_tien_vnd_va_tuong_duong',
              valueKey: 'von_dieu_le', severity: 'blocking',
              code: 'CAPITAL_MISMATCH',
              message: 'Tổng cộng nguồn vốn điều lệ phải khớp Vốn điều lệ kê khai ở mục 7.' }
          ]
        }
      }, {
        /* P2C fixed-matrix (merge 1691728, Lead wire): cơ cấu tài sản góp vốn
         * vào vốn điều lệ 6 dòng + Tổng số; "Các tài sản khác" là Ô MÔ TẢ TEXT
         * theo chính chữ mẫu (D1.2 chưa có quyết định sub-grid cho M02). */
        sectionId: 'tai_san_gop_von_von_dieu_le',
        semanticKey: 'co_cau_tai_san_gop_von_dieu_le',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'tai san gop von', matchRole: 'section-heading',
          endMatch: 'nguoi dai dien theo phap luat',
          endRole: 'section-heading' },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'tai_san_gop_von_von_dieu_le',
          semantic_key: 'co_cau_tai_san_gop_von_dieu_le',
          form_id: 'PLI_M02',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'dong_viet_nam', label: 'Đồng Việt Nam' },
            { id: 'ngoai_te_tu_do_chuyen_doi',
              label: 'Ngoại tệ tự do chuyển đổi (ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ)' },
            { id: 'vang', label: 'Vàng' },
            { id: 'quyen_su_dung_dat', label: 'Quyền sử dụng đất' },
            { id: 'quyen_so_huu_tri_tue', label: 'Quyền sở hữu trí tuệ' },
            { id: 'tai_san_khac',
              label: 'Các tài sản khác (ghi rõ loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản, có thể lập thành danh mục riêng kèm theo hồ sơ đăng ký doanh nghiệp)' },
            { id: 'tong_so', label: 'Tổng số', output_only: true }
          ],
          columns: [
            { tag: 'loai_tai_san_gop_von', inputType: 'readonly',
              header: 'Tài sản góp vốn' },
            { tag: 'chi_tiet_ngoai_te_tai_san_khac', inputType: 'text',
              header: 'Ghi rõ loại ngoại tệ, số tiền được góp bằng mỗi loại ngoại tệ / loại tài sản, số lượng và giá trị còn lại của mỗi loại tài sản' },
            { tag: 'gia_tri_vnd', inputType: 'money',
              header: 'Giá trị vốn của từng tài sản trong vốn điều lệ (bằng số, VNĐ)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_so', formula: 'sum(gia_tri_vnd)',
              target_tag: 'gia_tri_vnd' },
            { id: 'tong_so', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: [
            { type: 'percentSum', tag: 'ty_le', equals: 100,
              severity: 'warning', code: 'PERCENT_SUM',
              message: 'Tổng tỷ lệ tài sản góp vốn phải đúng 100% khi đã kê khai.' },
            { type: 'sumEqualsKey', tag: 'gia_tri_vnd',
              valueKey: 'von_dieu_le', severity: 'blocking',
              code: 'CAPITAL_MISMATCH',
              message: 'Tổng số tài sản góp vốn phải khớp Vốn điều lệ kê khai ở mục 7.' }
          ]
        }
      }]
    },
    /* N6 - nested-grid PLI_M12 (Wave R3B1, 2026-08-27): người đại diện theo
     * ủy quyền SAU KHI THAY ĐỔI - ngữ cảnh riêng của mẫu thay đổi, KHÔNG dùng
     * chung key với PLI_M02/M15 (cùng nguyên tắc độc lập draft như PLAN A).
     * Nguồn header: app/data/blocks/PLI_M12.json block B145 (header ghep, số
     * cột vật lý dẫn đầu bởi "Chủ sở hữu/Thành viên công ty TNHH/Cổ đông là
     * nhà đầu tư nước ngoài là tổ chức" theo census manifest section
     * ndd_uy_quyen_sau_thay_doi). D2.1=A chỉ chốt discriminator cho bộ
     * M02/M13/M15 nên mẫu này CHƯA có evidence 2 row-type -> KHÔNG khai
     * discriminator (absence, không mislabel). Chu thich 2 ("nếu cột số 5 là
     * Số ĐDCN thì bỏ cột 6, 7") là rule điều kiện chưa có trong contract v1.
     * Hai nhóm 'Tổng giá trị vốn được đại diện'/'Thời điểm đại diện phần vốn'
     * tiếp tục chờ owner/B3 như N1. Spec cùng hình dạng đã qua validator
     * tools/build_form_maps.py tại tools/form_specs/change/PLI_M12.json. */
    'PLI_M12': {
      sections: [{
        /* Wave cap-von (merge fc07c69): 'Nguồn vốn điều lệ sau khi thay đổi
         * vốn điều lệ' — bảng 3 cột × 5 dòng như M03/M05, heading body-level
         * (không phải section-heading). Chưa có cross rule: form_maps PLI_M12
         * chưa có key số vốn điều lệ SAU thay đổi để đối chiếu (gap đã ghi —
         * valueKey cần owner/Lead chốt khi mở capability). */
        sectionId: 'nguon_von_dieule_sau_thay_doi',
        semanticKey: 'nguon_von_dieu_le_sau_thay_doi',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'nguon von dieu le sau khi thay doi von dieu le',
          matchRole: 'body', endMatch: null, endRole: null },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'nguon_von_dieule_sau_thay_doi',
          semantic_key: 'nguon_von_dieu_le_sau_thay_doi',
          form_id: 'PLI_M12',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'von_ngan_sach_nha_nuoc', label: 'Vốn ngân sách nhà nước' },
            { id: 'von_tu_nhan', label: 'Vốn tư nhân' },
            { id: 'von_nuoc_ngoai', label: 'Vốn nước ngoài' },
            { id: 'von_khac', label: 'Vốn khác' },
            { id: 'tong_cong', label: 'Tổng cộng', output_only: true }
          ],
          columns: [
            { tag: null, inputType: 'readonly', header: 'Loại nguồn vốn' },
            { tag: 'so_tien_vnd_va_tuong_duong', inputType: 'money',
              header: 'Số tiền (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước ngoài, nếu có)' },
            { tag: 'ty_le', inputType: 'percent', header: 'Tỷ lệ (%)' }
          ],
          totals: [
            { id: 'tong_cong', formula: 'sum(so_tien_vnd_va_tuong_duong)',
              target_tag: 'so_tien_vnd_va_tuong_duong' },
            { id: 'tong_cong', formula: 'sum(ty_le)', target_tag: 'ty_le' }
          ],
          cross_field_rules: []
        }
      },
      {
        sectionId: 'ndd_uy_quyen_sau_thay_doi',
        semanticKey: 'ds_ndd_uy_quyen_sau_thay_doi',
        kind: 'nested-grid',
        policy: { allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: false },
        anchor: {
          match: 'thong tin ve nguoi dai dien theo uy quyen sau khi thay doi',
          matchRole: 'body',
          endMatch: '1 dung trong truong hop thay doi tu nguoi dai dien',
          endRole: 'body'
        },
        spec: {
          kind: 'nested-grid',
          section_id: 'ndd_uy_quyen_sau_thay_doi',
          semantic_key: 'ds_ndd_uy_quyen_sau_thay_doi',
          loop: 'ds_ndd_uy_quyen_sau_thay_doi',
          form_id: 'PLI_M12',
          header_rows: [
            [
              { text: 'STT', rowspan: 2 },
              { text: 'Chủ sở hữu/Thành viên công ty TNHH/Cổ đông là nhà đầu tư nước ngoài là tổ chức', rowspan: 2 },
              { text: 'Tên người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ngày, tháng, năm sinh', rowspan: 2 },
              { text: 'Giới tính', rowspan: 2 },
              { text: 'Số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân', colspan: 3 },
              { text: 'Quốc tịch', rowspan: 2 },
              { text: 'Dân tộc', rowspan: 2 },
              { text: 'Địa chỉ liên lạc', rowspan: 2 },
              { text: 'Vốn được ủy quyền', colspan: 2 },
              { text: 'Chữ ký của người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ghi chú (nếu có)', rowspan: 2 }
            ],
            [
              { text: 'Số' }, { text: 'Ngày cấp' }, { text: 'Cơ quan cấp' },
              { text: 'VNĐ' }, { text: 'Tỷ lệ (%)' }
            ]
          ],
          columns: ['stt', 'chu_so_huu_tvtnhh_cdnn_to_chuc', 'ten_ndd_uy_quyen',
            'ngay_sinh', 'gioi_tinh', 'giay_to_so', 'giay_to_ngay',
            'giay_to_co_quan', 'quoc_tich', 'dan_toc', 'dia_chi',
            'von_duoc_uy_quyen_vnd', 'ty_le', 'chu_ky', 'ghi_chu'
          ].map(function (tag, col_index) {
            return { tag: tag, col_index: col_index,
              type: tag === 'chu_ky' ? 'outputOnly' :
                (tag === 'stt' ? 'stt' :
                  ((tag === 'von_duoc_uy_quyen_vnd' || tag === 'ty_le')
                    ? 'money' : 'text')) };
          }),
          min_rows: 1,       // D2.7=A: tối thiểu 1 dòng có dữ liệu
          max_rows: null,    // D2.7=A: không giới hạn vô căn cứ
          totals: [],
          cross_field_rules: []
        }
      }]
    },
    /* N7 - nested-grid PLI_M15 (Wave R3B1): người đại diện/theo ủy quyền của
     * chủ sở hữu MỚI. Cùng row-contract N1 theo D2.1=A (một policy chung cho
     * M02/M13/M15); nguồn: app/data/blocks/PLI_M15.json B48-B49 (paragraph
     * header ghep còn đựng chuỗi cam kết của mẫu ở run cuối -> rebuild ở
     * tools/form_specs/change/PLI_M15.json dùng trim/keep_from để GIỮ nguyên
     * chuỗi đó). min_rows 1 / max_rows null đúng D2.7=A. */
    'PLI_M15': {
      sections: [{
        sectionId: 'ndd_pl_uy_quyen_chu_so_huu_moi',
        semanticKey: 'ds_nddpl_uy_quyen_chu_so_huu_moi',
        kind: 'nested-grid',
        policy: { allowAdd: true, allowDelete: true, allowReorder: true,
          confirmDeleteNonEmpty: false },
        anchor: {
          match: 'nguoi dai dien theo phap luat/nguoi dai dien theo uy quyen cua chu so huu',
          matchRole: 'body',
          endMatch: 'doanh nghiep cam ket hoan toan chiu trach nhiem',
          endRole: 'body'
        },
        spec: {
          kind: 'nested-grid',
          section_id: 'ndd_pl_uy_quyen_chu_so_huu_moi',
          semantic_key: 'ds_nddpl_uy_quyen_chu_so_huu_moi',
          loop: 'ds_nddpl_uy_quyen_chu_so_huu_moi',
          form_id: 'PLI_M15',
          header_rows: [
            [
              { text: 'STT', rowspan: 2 },
              { text: 'Tên người đại diện theo pháp luật/người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ngày, tháng, năm sinh', rowspan: 2 },
              { text: 'Giới tính', rowspan: 2 },
              { text: 'Số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân', colspan: 3 },
              { text: 'Quốc tịch', rowspan: 2 },
              { text: 'Dân tộc', rowspan: 2 },
              { text: 'Địa chỉ liên lạc', rowspan: 2 },
              { text: 'Vốn được ủy quyền', colspan: 2 },
              { text: 'Chữ ký của người đại diện theo pháp luật/người đại diện theo ủy quyền', rowspan: 2 },
              { text: 'Ghi chú (nếu có)', rowspan: 2 }
            ],
            [
              { text: 'Số' }, { text: 'Ngày cấp' }, { text: 'Cơ quan cấp' },
              { text: 'VNĐ' }, { text: 'Tỷ lệ (%)' }
            ]
          ],
          row_groups: [
            { group_id: 'ndd_pl',
              match: { tag: 'loai_dong', equals: 'ndd_pl' },
              required_columns: ['ten_nguoi_dai_dien'] },
            { group_id: 'ndd_uy_quyen',
              match: { tag: 'loai_dong', equals: 'ndd_uy_quyen' },
              required_columns: ['ten_nguoi_dai_dien', 'ty_le'] }
          ],
          discriminator: { tag: 'loai_dong', values: ['ndd_pl', 'ndd_uy_quyen'] },
          columns: ['stt', 'ten_nguoi_dai_dien', 'ngay_sinh', 'gioi_tinh',
            'giay_to_so', 'giay_to_ngay', 'giay_to_co_quan', 'quoc_tich',
            'dan_toc', 'dia_chi', 'von_duoc_uy_quyen_vnd', 'ty_le', 'chu_ky',
            'ghi_chu'
          ].map(function (tag, col_index) {
            return { tag: tag, col_index: col_index,
              type: tag === 'chu_ky' ? 'outputOnly' :
                (tag === 'stt' ? 'stt' :
                  ((tag === 'von_duoc_uy_quyen_vnd' || tag === 'ty_le')
                    ? 'money' : 'text')) };
          }),
          min_rows: 1,       // D2.7=A: tối thiểu 1 dòng có dữ liệu
          max_rows: null,    // D2.7=A: không giới hạn vô căn cứ
          totals: [],
          cross_field_rules: []
        }
      }]
    },
    /* Wave cap-von (merge fc07c69) — D5.2: bảng "đăng ký cũ / đăng ký mới"
     * 3 chỉ tiêu của Phụ lục II Mẫu 2 (5.1 địa chỉ nhận thông báo thuế,
     * 5.2 tổng số lao động, chỉ tiêu khác). Text thuần, không totals/rules.
     * Anchor là câu dẫn body ngay trước bảng (heading là form-subtitle
     * 'ĐĂNG KÝ THAY ĐỔI NỘI DUNG ĐĂNG KÝ THUẾ'). */
    'PLII_M02': {
      sections: [{
        sectionId: 'a7_thue_chi_tieu_cu_moi',
        semanticKey: 'thue_chi_tieu_cu_moi',
        kind: 'fixed-matrix',
        policy: { allowAdd: false, allowDelete: false, allowReorder: false },
        anchor: { match: 'dang ky bo sung, thay doi cac chi tieu dang ky thue',
          matchRole: 'body', endMatch: null, endRole: null },
        spec: {
          kind: 'fixed-matrix',
          section_id: 'a7_thue_chi_tieu_cu_moi',
          semantic_key: 'thue_chi_tieu_cu_moi',
          form_id: 'PLII_M02',
          stt: { mode: 'none' },
          fixed_rows: [
            { id: 'chi_tieu_5_1_dia_chi_nhan_thong_bao_thue',
              label: '- Chỉ tiêu 5.1: Địa chỉ nhận thông báo thuế' },
            { id: 'chi_tieu_5_2_tong_so_lao_dong',
              label: '- Chỉ tiêu 5.2: Tổng số lao động' },
            { id: 'chi_tieu_khac', label: '-…..' }
          ],
          columns: [
            { tag: null, inputType: 'readonly', header: 'Chỉ tiêu' },
            { tag: 'thong_tin_dang_ky_cu', inputType: 'text',
              header: 'Thông tin đăng ký cũ' },
            { tag: 'thong_tin_dang_ky_moi', inputType: 'text',
              header: 'Thông tin đăng ký mới' }
          ],
          totals: [],
          cross_field_rules: []
        }
      }]
    }
  };

  function sectionsOfForm(docId) {
    var fm = docId ? FORM_TABLE_CONTRACTS[docId] : null;
    return (fm && fm.sections) || [];
  }

  /* Tất cả entry của một mẫu (renderer/controller nhận qua opts.sectionContracts).
   * Trả bản sao SHALLOW của array để caller mutate parts không đụng registry. */
  function sectionContractsOf(docId) {
    return sectionsOfForm(docId).slice();
  }

  /* Entry theo semantic_key HOẶC section_id (dùng cho test/gate). */
  function getSectionContract(docId, key) {
    var want = String(key == null ? '' : key);
    return sectionsOfForm(docId).filter(function (e) {
      return e.semanticKey === want || e.sectionId === want ||
        (e.spec && e.spec.semantic_key === want);
    })[0] || null;
  }

  /* Entry của LOOP name (chỉ kind mang dòng dữ liệu). Dùng trong validator
   * + controller row-op để kind mới KHÔNG rơi xuống đường editable/legacy. */
  function sectionContractForLoop(docId, name) {
    var hit = null;
    sectionsOfForm(docId).some(function (e) {
      var sk = e.spec && e.spec.semantic_key;
      if ((e.kind === 'nested-grid') &&
          (sk === name || (e.spec.loop || '') === name)) { hit = e; return true; }
      return false;
    });
    return hit;
  }

  // ------------------------------------------------- validate theo kind

  /* Row của fixed-matrix là dòng tổng/outputOnly? Nhất quán với predicate
   * của fixed-matrix.js (isOutputRow) + mọi id khai trong spec.totals. */
  function isFixedTotalRow(spec, row) {
    if (!row) return false;
    if (row.output_only === true || row.outputOnly === true) return true;
    return (Array.isArray(spec.totals) ? spec.totals : []).some(function (t) {
      return String(t.id) === String(row.id);
    });
  }

  /* Section còn có ÍT NHẤT MỘT ô nhập có dữ liệu? (fixed-matrix: giá trị phẳng
   * trong values; nested-grid: bất kỳ row nào có dữ liệu khác _row_id.) */
  function sectionHasData(entry, st) {
    var spec = entry.spec || {};
    var vals = st.values || {};
    if (entry.kind === 'fixed-matrix') {
      return (spec.fixed_rows || []).some(function (row) {
        if (isFixedTotalRow(spec, row)) return false;
        return (spec.columns || []).some(function (col) {
          if (!col) return false;
          var v = vals[spec.semantic_key + '.' + row.id + '.' + col.tag];
          return v != null && String(v).trim() !== '';
        });
      });
    }
    if (entry.kind === 'nested-grid') {
      var rows = (st.loops || {})[spec.semantic_key] || [];
      return rows.some(function (r) {
        return Object.keys(r || {}).some(function (k) {
          if (k.charAt(0) === '_') return false;
          return r[k] != null && String(r[k]).trim() !== '';
        });
      });
    }
    return false; // output-table không có rule dữ liệu
  }

  /* Cộng dồn 1 tag của section qua accessor đúng kind. Chỉ đếm ô NHẬP (bỏ
   * dòng tổng/outputOnly) để projection không được cộng hai lần. */
  function sectionSumTag(entry, st, tag) {
    var spec = entry.spec || {};
    var out = { hasValue: false, sum: 0 };
    if (entry.kind === 'fixed-matrix') {
      var vals = st.values || {};
      (spec.fixed_rows || []).forEach(function (row) {
        if (isFixedTotalRow(spec, row)) return;
        var raw = vals[spec.semantic_key + '.' + row.id + '.' + tag];
        if (raw == null || String(raw).trim() === '') return;
        var n = parseMoney(raw);
        if (n == null) return;
        out.hasValue = true;
        out.sum += n;
      });
    } else if (entry.kind === 'nested-grid') {
      ((st.loops || {})[spec.semantic_key] || []).forEach(function (row) {
        var raw = row ? row[tag] : null;
        if (raw == null || String(raw).trim() === '') return;
        var n = parseMoney(raw);
        if (n == null) return;
        out.hasValue = true;
        out.sum += n;
      });
    }
    return out;
  }

  /* Cross-field rules khai trong entry.spec.cross_field_rules. Shape hỗ trợ
   * nhỏ, cố ý giống slot của editable-grid (validateCrossFieldRules):
   *  - chuỗi "sum(<tag>) <= <số>" ;
   *  - {type:'percentSum', tag, equals?, severity?, code?, message?}
   *    (severity mặc định warning, code PERCENT_SUM);
   *  - {type:'sumEqualsKey', tag, valueKey, operator?, severity?, code?,
   *    message?} - đối chiếu tổng cột với một giá trị hồ sơ (vd vốn điều lệ).
   * Rule lạ bị BỎ QUA (fail-open ở mức "không tự sinh lỗi pháp lý") đúng như
   * nguyên tắc slot additive; severity đi thẳng vào error[] theo contract. */
  function evalSectionCrossFieldRules(docId, entry, st, push) {
    var spec = entry.spec || {};
    (Array.isArray(spec.cross_field_rules) ? spec.cross_field_rules : [])
      .forEach(function (ruleRaw) {
        if (!ruleRaw) return;
        var cfg = typeof ruleRaw === 'string' ? { rule: ruleRaw } : ruleRaw;
        var text = typeof ruleRaw === 'string' ? ruleRaw : String(cfg.rule || '');
        var m = text.match(
          /^\s*sum\(\s*([^)]+?)\s*\)\s*(==|=|<=|>=|<|>)\s*(-?\d+(?:[.,]\d+)?)\s*$/i);

        var sugarPercent = (cfg.type === 'percentSum');
        var compareKey = (cfg.type === 'sumEqualsKey');
        // Shape có cấu trúc không khai operator -> mặc định '==' (vd
        // percentSum: tổng == 100; sumEqualsKey: tổng cộng == vốn điều lệ).
        var op = cfg.operator || (m ? m[2] :
          ((sugarPercent || compareKey) ? '==' : null));
        var tag = cfg.tag || (m ? m[1].trim() : null);
        var expected = cfg.equals != null ? Number(cfg.equals) :
          (cfg.value != null ? Number(cfg.value) : null);
        // percentSum không khai mốc -> mặc định đúng 100% (mệnh đề phổ biến
        // nhất của bảng tỷ lệ; ghi rõ để rule thiếu dữ liệu vẫn có nghĩa).
        if (sugarPercent && expected == null) expected = 100;
        var vsKey = cfg.valueKey || null;
        if (!tag || !op) return;
        if (String(op) === '=') op = '==';

        if (!compareKey && (expected == null || isNaN(expected))) return;

        var sum = sectionSumTag(entry, st, tag);
        var actual = sum.sum;
        if (compareKey) {
          var other = parseMoney((st.values || {})[vsKey]);
          if (other == null) return;          // chưa kê khai giá trị đối chiếu
          actual = Math.round(sum.sum * 100) / 100;
          op = op || '==';
          expected = other;
        } else if (!sugarPercent && m == null) {
          return;                              // shape không hỗ trợ -> bỏ qua
        }
        if (!sum.hasValue) return;             // "khi co ke khai"
        var ok = op === '==' ?
          Math.round(actual * 100) === Math.round(expected * 100) :
          op === '<=' ? actual <= expected :
          op === '>=' ? actual >= expected :
          op === '<' ? actual < expected : actual > expected;
        if (ok) return;
        push({
          key: spec.semantic_key + '.cross_field.' + tag,
          docId: docId,
          code: cfg.code || (sugarPercent ? 'PERCENT_SUM' : 'CROSS_FIELD_RULE'),
          message: cfg.message || ('Tổng ' + tag + ' không thỏa điều kiện ' +
            op + ' ' + expected + ' (đang là ' + actual + ')'),
          severity: cfg.severity || (sugarPercent ? 'warning' : 'blocking')
        });
      });
  }

  /* Validate MỘT section theo kind bằng chính module của nó. Trả error[]
   * shape {key, docId, code, message, severity} (docs/htkk-ui-contract.md). */
  function validateSectionEntry(docId, entry, st) {
    var errs = [];
    var spec = entry.spec || {};
    if (entry.kind === 'fixed-matrix') {
      var FM = p2TableModule('FixedMatrix');
      if (FM && typeof FM.validate === 'function') {
        FM.validate(spec, { values: st.values || {} }).forEach(function (e) {
          errs.push({
            key: e.key, docId: docId, code: e.code,
            message: e.message, severity: e.severity || 'blocking'
          });
        });
      }
    } else if (entry.kind === 'nested-grid') {
      var NG = p2TableModule('NestedGrid');
      if (NG && typeof NG.validate === 'function') {
        var ngRows = (st.loops || {})[spec.semantic_key] || [];
        /* O3 (owner 2026-09-06): activeWhen khai ở entry hoặc spec quyết định
         * section có ACTIVE không. Dùng lại evalActiveWhen (MỘT nguồn chân lý
         * của store) với số dòng business-data do module đếm; section inactive
         * -> validate không sinh MIN_ROWS/MAX_ROWS. Không khai activeWhen ->
         * luôn active (hành vi cũ). */
        var ngAw = entry.activeWhen || spec.activeWhen || null;
        var ngCtx = null;
        if (ngAw && typeof NG.businessRowsOf === 'function') {
          ngCtx = { isActive: evalActiveWhen(
            ngAw, NG.businessRowsOf(spec, ngRows).length, st) };
        }
        NG.validate(spec, ngRows, ngCtx)
          .forEach(function (e) {
            errs.push({
              key: e.key, docId: docId, code: e.code,
              message: e.message, severity: e.severity || 'blocking'
            });
          });
      }
    } else if (entry.kind === 'editable-grid') {
      // Không thể xảy ra trong registry hiện tại; giữ nhánh này để dispatcher
      // Không nuốt kind editable-grid của section-level (đường cũ lo phần đó).
      var g = getGridMeta({ docId: docId, loop: spec.semantic_key });
      if (g) validateGridLoop(docId, spec.semantic_key, g, [], st, {}, function (e) {
        errs.push(e);
      });
    }
    // output-table: không có rule dữ liệu -> không sinh lỗi nào.
    evalSectionCrossFieldRules(docId, entry, st, function (e) { errs.push(e); });
    return errs;
  }

  /* Validate TẤT CẢ section đã đăng ký của một mẫu (dispatcher theo kind). */
  function validateFormSections(docId, st) {
    var errors = [];
    var seen = {};
    sectionsOfForm(docId).forEach(function (entry) {
      validateSectionEntry(docId, entry, st).forEach(function (e) {
        var id = [e.docId, e.key, e.code].join('|');
        if (seen[id]) return;
        seen[id] = true;
        errors.push(e);
      });
    });
    return errors;
  }

  /* Projection TỔNG TÍNH LẠI (recompute) cho các section tổng của một mẫu.
   * Đây là NGUỒN SỐ LIỆU duy nhất cho ô tổng outputOnly ở UI/export: giá trị
   * dùng công thức khai trong spec.totals, đọc THẲNG dữ liệu người dùng nhập,
   * KHÔNG đọc lại con số đã lưu -> không bao giờ có hai nguồn mâu thuẫn.
   * Trả map key "<semantic_key>.<row>.<tag>" ->
   * {value: number|null, inputType: 'money'|'percent'|null} để caller format
   * đúng kiểu (tiền dấu chấm ngăn nghìn, percent giữ số). */
  function recomputeSections(docId, store) {
    var out = {};
    var st = store || {};
    var FM = p2TableModule('FixedMatrix');
    sectionsOfForm(docId).forEach(function (entry) {
      if (entry.kind !== 'fixed-matrix') return;
      if (!FM || typeof FM.formulaValue !== 'function') return;
      var spec = entry.spec || {};
      (Array.isArray(spec.totals) ? spec.totals : []).forEach(function (t) {
        var ev = FM.formulaValue(t.formula, spec, { values: st.values || {} });
        var tag = t.target_tag || t.targetTag || 'value';
        var col = (Array.isArray(spec.columns) ? spec.columns : [])
          .filter(function (c) { return c && c.tag === tag; })[0];
        out[spec.semantic_key + '.' + t.id + '.' + tag] = {
          value: ev.supported ? ev.value : null,
          inputType: (col && (col.inputType || col.type)) || null
        };
      });
    });
    return out;
  }

  /* Validate một mẫu biểu. store = {values, checks, loops}. Trả error[].
   * Loop có grid meta (resolve theo docId: form-scoped trước, rồi toàn cục)
   * -> validate editable-grid với lỗi key theo _row_id:
   * "loop:<name>:<row_id>[:<tag>]"; loop khác giữ hành vi legacy.
   * R2 dispatch: loop ĐÃ classify là kind mới (nested-grid...) chạy qua
   * module của nó và KHÔNG rơi xuống đường editable/legacy; section không
   * khai loop (fixed-matrix giá trị phẳng, output-table) vẫn được validate. */
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
      // R2 dispatcher theo section.kind: loop đã classify thành kind mới
      // (nested-grid/fixed-matrix/output-table) phải đi đúng đường của nó -
      // fallback editable/legacy CHỈ dành cho schema chưa classify.
      var sec = sectionContractForLoop(docId, name);
      if (sec && sec.kind !== 'editable-grid') {
        validateSectionEntry(docId, sec, st).forEach(push);
        return;
      }
      var g = getGridMeta({ docId: docId, loop: name });
      if (g) validateGridLoop(docId, name, g, info.loops[name], st, ctx, push);
      else validateLegacyLoop(docId, name, info.loops[name], st, ctx, push);
    });

    // R2 dispatch: section không khai loop trong blocks (fixed-matrix lưu giá
    // trị phẳng values["<sk>.<row>.<tag>"], output-table không có input nào)
    // vẫn được validate qua module của nó; grid inactive chưa có dữ liệu thì
    // im hoàn toàn (không sinh lỗi giả).
    validateFormSections(docId, st).forEach(function (e) {
      var id = [e.docId, e.key, e.code].join('|');
      if (!seenErr[id]) { seenErr[id] = true; errors.push(e); }
    });

    // Selector form-scoped (P1.2 Option D): M72 bắt buộc chọn đúng một
    // loại hình - chưa chọn/giá trị lạ là blocking chặn export.
    validateSelector(docId, getFormSelector(docId), st).forEach(push);

    // F-V5-3 (PLAN v7 F0.4): nhóm loại-trừ chk ở lớp runtime — tối đa MỘT
    // tick mỗi nhóm. Registry đầy đủ cho fixture nằm ở
    // tools/phase5_fixtures.py (EXCLUSIVE_GROUPS); runtime chỉ chặn các cặp
    // mà tick đồng thời vi phạm pháp lý rõ ràng trên mọi mẫu.
    validateExclusiveChecks(docId, info.keys, st).forEach(push);

    return errors;
  }

  /* Nhóm loại-trừ chk: tick đồng thời >=2 option trong cùng nhóm là lỗi
     blocking (mô hình tổ chức công ty: HĐTV/HĐQT HOẶC Chủ tịch công ty). */
  var EXCLUSIVE_CHK_GROUPS = [
    {
      gid: 'mo_hinh_to_chuc',
      pattern: /^chk_auto_(hoi_dong_thanh_vien_giam_doc_hoac_tong_g|chu_tich_cong_ty_giam_doc_hoac_tong_giam)$/,
      message: 'Mô hình tổ chức công ty chỉ được chọn một: Hội đồng thành viên/'
               + 'Hội đồng quản trị HOẶC Chủ tịch công ty',
    },
  ];

  function validateExclusiveChecks(docId, keys, store) {
    var errors = [];
    var checks = (store && store.checks) || {};
    EXCLUSIVE_CHK_GROUPS.forEach(function (g) {
      var ticked = keys.filter(function (k) {
        return g.pattern.test(k) && checks[k];
      });
      if (ticked.length > 1) {
        errors.push({
          key: 'chk-group:' + g.gid,
          docId: docId,
          code: 'CHK_EXCLUSIVE_CONFLICT',
          message: g.message + ' (đang chọn ' + ticked.length + ' ô)',
          severity: 'blocking',
        });
      }
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
    /* Start with shallow copies of every legacy object.  Migration is
     * additive: fields introduced by newer/unknown producers must survive
     * even when this module does not understand them yet. */
    var up = Object.assign({}, draft, {
      v: 2,
      caseId: draft.caseId != null ? draft.caseId : null,
      checkedForms: Array.isArray(draft.checkedForms) ? draft.checkedForms.slice() : [],
      activeDocId: null,
      autoSum: !!draft.autoSum,
      viewState: {},
      savedAt: null
    });
    up.store = Object.assign({}, draft.store);
    up.store.values = Object.assign({}, draft.store.values);
    up.store.checks = Object.assign({}, draft.store.checks);
    up.store.loops = draft.store.loops || {};
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
  root.isActiveSection = isActiveSection;
  root.makeRowId = makeRowId;
  root.normalizeStoreLoops = normalizeStoreLoops;
  root.collectKeys = collectKeys;
  root.validateField = validateField;
  root.validateDocument = validateDocument;
  root.validateDossier = validateDossier;
  root.isValidMaNganh = isValidMaNganh;
  root.migrateDraft = migrateDraft;

  /* P2 R2 runtime wiring: dispatcher + section theo kind (3 module output-
   * table/fixed-matrix/nested-grid chỉ được require/gọi, không sửa). */
  root.P2_SECTION_KINDS = P2_SECTION_KINDS;
  root.FORM_TABLE_CONTRACTS = FORM_TABLE_CONTRACTS;
  root.p2TableModule = p2TableModule;
  root.sectionContractsOf = sectionContractsOf;
  root.getSectionContract = getSectionContract;
  root.sectionContractForLoop = sectionContractForLoop;
  root.sectionHasData = sectionHasData;
  root.validateSectionEntry = validateSectionEntry;
  root.validateFormSections = validateFormSections;
  root.recomputeSections = recomputeSections;

})(typeof module !== 'undefined' && module.exports ? module.exports : (window.FormDomain = window.FormDomain || {}));
