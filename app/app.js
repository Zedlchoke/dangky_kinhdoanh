const forms = {
  pl1_1: ["PL1", 1, "Giấy đề nghị đăng ký doanh nghiệp - Doanh nghiệp tư nhân", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_01_giay_de_nghi_dang_ky_doanh_nghiep_doanh_nghiep_tu_nhan.docx"],
  pl1_2: ["PL1", 2, "Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn một thành viên", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_02_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_mot_thanh_vien.docx"],
  pl1_3: ["PL1", 3, "Giấy đề nghị đăng ký doanh nghiệp - Công ty trách nhiệm hữu hạn hai thành viên trở lên", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_03_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx"],
  pl1_4: ["PL1", 4, "Giấy đề nghị đăng ký doanh nghiệp - Công ty cổ phần", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_04_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_co_phan.docx"],
  pl1_5: ["PL1", 5, "Giấy đề nghị đăng ký doanh nghiệp - Công ty hợp danh", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_05_giay_de_nghi_dang_ky_doanh_nghiep_cong_ty_hop_danh.docx"],
  pl1_6: ["PL1", 6, "Danh sách thành viên công ty TNHH hai thành viên trở lên", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_06_danh_sach_thanh_vien_cong_ty_trach_nhiem_huu_han_hai_thanh_vien_tro_len.docx"],
  pl1_7: ["PL1", 7, "Danh sách cổ đông sáng lập công ty cổ phần", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_07_danh_sach_co_dong_sang_lap_cong_ty_co_phan.docx"],
  pl1_8: ["PL1", 8, "Danh sách cổ đông là nhà đầu tư nước ngoài", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_08_danh_sach_co_dong_la_nha_dau_tu_nuoc_ngoai.docx"],
  pl1_9: ["PL1", 9, "Danh sách thành viên công ty hợp danh", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_09_danh_sach_thanh_vien_cong_ty_hop_danh.docx"],
  pl1_10: ["PL1", 10, "Danh sách chủ sở hữu hưởng lợi của doanh nghiệp", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_10_danh_sach_chu_so_huu_huong_loi_cua_doanh_nghiep.docx"],
  pl1_11: ["PL1", 11, "Kê khai thông tin để xác định chủ sở hữu hưởng lợi của doanh nghiệp", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_11_ke_khai_thong_tin_de_xac_dinh_chu_so_huu_huong_loi_cua_doanh_nghiep.docx"],
  pl1_12: ["PL1", 12, "Giấy đề nghị/Thông báo thay đổi nội dung đăng ký doanh nghiệp", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_12_giay_de_nghi_dang_ky_thay_doi_noi_dung_giay_chung_nhan_dang_ky_doanh_nghiep_thong_bao_thay_doi_n.docx"],
  pl1_13: ["PL1", 13, "Giấy đề nghị đăng ký thay đổi người đại diện theo pháp luật", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_13_giay_de_nghi_dang_ky_thay_doi_nguoi_dai_dien_theo_phap_luat.docx"],
  pl1_14: ["PL1", 14, "Giấy đề nghị đăng ký thay đổi chủ doanh nghiệp tư nhân", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_14_giay_de_nghi_dang_ky_thay_doi_chu_doanh_nghiep_tu_nhan.docx"],
  pl1_15: ["PL1", 15, "Giấy đề nghị đăng ký thay đổi chủ sở hữu công ty TNHH một thành viên", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_15_giay_de_nghi_dang_ky_thay_doi_chu_so_huu_cong_ty_tnhh_mot_thanh_vien.docx"],
  pl1_16: ["PL1", 16, "Thông báo về việc cho thuê doanh nghiệp tư nhân", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_16_thong_bao_ve_viec_cho_thue_doanh_nghiep_tu_nhan.docx"],
  pl1_17: ["PL1", 17, "Đăng ký hoạt động chi nhánh/VPĐD hoặc lập địa điểm kinh doanh", "../03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_17_giay_de_nghi_dang_ky_hoat_dong_chi_nhanh_van_phong_dai_dien_thong_bao_lap_dia_diem_kinh_doanh.docx"],
  pl1_18: ["PL1", 18, "Thông báo lập chi nhánh/văn phòng đại diện ở nước ngoài", "../03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_18_thong_bao_ve_viec_lap_chi_nhanh_van_phong_dai_dien_o_nuoc_ngoai.docx"],
  pl1_19: ["PL1", 19, "Thay đổi nội dung hoạt động chi nhánh/VPĐD/địa điểm kinh doanh", "../03_chi_nhanh_van_phong_dai_dien_dia_diem/PL1_Mau_19_giay_de_nghi_dang_ky_thay_doi_noi_dung_dang_ky_hoat_dong_chi_nhanh_van_phong_dai_dien_dia_diem_k.docx"],
  pl1_26: ["PL1", 26, "Cấp lại giấy chứng nhận/giấy xác nhận", "../02_thay_doi_thong_tin_doanh_nghiep/PL1_Mau_26_giay_de_nghi_cap_lai_giay_chung_nhan_dang_ky_doanh_nghiep_giay_xac_nhan_thay_doi_noi_dung_dang_k.docx"],
  pl1_27: ["PL1", 27, "Tạm ngừng/tiếp tục kinh doanh trước thời hạn", "../04_tam_ngung_cham_dut_giai_the/PL1_Mau_27_thong_bao_ve_viec_tam_ngung_kinh_doanh_tiep_tuc_kinh_doanh_truoc_thoi_han_da_thong_bao_cua_doanh.docx"],
  pl1_28: ["PL1", 28, "Chấm dứt hoạt động chi nhánh/VPĐD/địa điểm kinh doanh", "../04_tam_ngung_cham_dut_giai_the/PL1_Mau_28_thong_bao_ve_viec_cham_dut_hoat_dong_chi_nhanh_van_phong_dai_dien_dia_diem_kinh_doanh.docx"],
  pl1_30: ["PL1", 30, "Thông báo về việc giải thể doanh nghiệp", "../04_tam_ngung_cham_dut_giai_the/PL1_Mau_30_thong_bao_ve_viec_giai_the_doanh_nghiep.docx"],
  pl1_31: ["PL1", 31, "Huỷ bỏ nghị quyết/quyết định giải thể doanh nghiệp", "../04_tam_ngung_cham_dut_giai_the/PL1_Mau_31_thong_bao_ve_viec_huy_bo_nghi_quyet_quyet_dinh_giai_the_doanh_nghiep.docx"],
  pl1_32: ["PL1", 32, "Giấy đề nghị công bố nội dung đăng ký doanh nghiệp", "../05_cong_bo_cung_cap_thong_tin/PL1_Mau_32_giay_de_nghi_cong_bo_noi_dung_dang_ky_doanh_nghiep.docx"],
  pl1_33: ["PL1", 33, "Giấy đề nghị dừng thực hiện thủ tục đăng ký doanh nghiệp", "../05_cong_bo_cung_cap_thong_tin/PL1_Mau_33_giay_de_nghi_dung_thuc_hien_thu_tuc_dang_ky_doanh_nghiep.docx"],
  pl1_34: ["PL1", 34, "Cam kết thực hiện mục tiêu xã hội, môi trường", "../01_dang_ky_thanh_lap_doanh_nghiep/PL1_Mau_34_cam_ket_thuc_hien_muc_tieu_xa_hoi_moi_truong.docx"],
  pl1_78: ["PL1", 78, "Giấy đề nghị cung cấp thông tin đăng ký doanh nghiệp", "../05_cong_bo_cung_cap_thong_tin/PL1_Mau_78_giay_de_nghi_cung_cap_thong_tin_dang_ky_doanh_nghiep.docx"],
  pl2_1: ["PL2", 1, "Giấy đề nghị đăng ký hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_01_giay_de_nghi_dang_ky_ho_kinh_doanh.docx"],
  pl2_2: ["PL2", 2, "Giấy đề nghị đăng ký thay đổi nội dung đăng ký hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_02_giay_de_nghi_dang_ky_thay_doi_noi_dung_dang_ky_ho_kinh_doanh.docx"],
  pl2_3: ["PL2", 3, "Tạm ngừng/tiếp tục kinh doanh hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_03_giay_de_nghi_dang_ky_tam_ngung_kinh_doanh_tiep_tuc_kinh_doanh_truoc_thoi_han_da_dang_ky_cua_ho_k.docx"],
  pl2_4: ["PL2", 4, "Thông báo chấm dứt hoạt động hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_04_thong_bao_ve_viec_cham_dut_hoat_dong_ho_kinh_doanh.docx"],
  pl2_5: ["PL2", 5, "Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_05_giay_de_nghi_cap_lai_giay_chung_nhan_dang_ky_ho_kinh_doanh.docx"],
  pl2_6: ["PL2", 6, "Dừng thực hiện thủ tục đăng ký hộ kinh doanh", "../06_ho_kinh_doanh_va_chuyen_doi/01_mau_ho_kinh_doanh/PL2_Mau_06_giay_de_nghi_dung_thuc_hien_thu_tuc_dang_ky_ho_kinh_doanh.docx"],
};

const procedures = [
  ["formation", "Thành lập doanh nghiệp"],
  ["change", "Thay đổi thông tin doanh nghiệp"],
  ["branch", "Chi nhánh / VPĐD / địa điểm kinh doanh"],
  ["pauseClose", "Tạm ngừng / chấm dứt / giải thể"],
  ["household", "Hộ kinh doanh"],
  ["convertHkd", "Chuyển hộ kinh doanh sang doanh nghiệp"],
  ["lookup", "Chỉ tra cứu biểu mẫu"],
];

const entityTypes = [
  ["private", "Doanh nghiệp tư nhân"],
  ["llc1", "Công ty TNHH một thành viên"],
  ["llc2", "Công ty TNHH hai thành viên trở lên"],
  ["jsc", "Công ty cổ phần"],
  ["partnership", "Công ty hợp danh"],
  ["branch", "Chi nhánh"],
  ["rep", "Văn phòng đại diện"],
  ["location", "Địa điểm kinh doanh"],
  ["hkd", "Hộ kinh doanh"],
];

const scenariosByProcedure = {
  formation: [
    ["normal", "Thành lập mới thông thường"],
    ["social", "Thành lập doanh nghiệp xã hội"],
    ["splitMerge", "Thành lập trên cơ sở chia/tách/hợp nhất"],
  ],
  change: [
    ["address", "Đổi địa chỉ trụ sở"],
    ["name", "Đổi tên doanh nghiệp"],
    ["businessLines", "Thay đổi ngành, nghề kinh doanh"],
    ["legalRep", "Đổi người đại diện theo pháp luật"],
    ["capital", "Đổi vốn điều lệ/phần vốn góp/cổ phần"],
    ["owner", "Đổi chủ DNTN/chủ sở hữu TNHH 1TV"],
    ["tax", "Thay đổi thông tin đăng ký thuế"],
    ["beneficial", "Cập nhật chủ sở hữu hưởng lợi"],
    ["reissue", "Cấp lại giấy chứng nhận/giấy xác nhận"],
  ],
  branch: [
    ["openBranch", "Lập chi nhánh/VPĐD/địa điểm"],
    ["changeBranch", "Thay đổi nội dung hoạt động"],
    ["foreignBranch", "Lập chi nhánh/VPĐD ở nước ngoài"],
    ["closeBranch", "Chấm dứt hoạt động"],
  ],
  pauseClose: [
    ["pause", "Tạm ngừng/tiếp tục trước thời hạn"],
    ["dissolve", "Giải thể doanh nghiệp"],
    ["cancelDissolve", "Huỷ bỏ quyết định giải thể"],
    ["stopProcedure", "Dừng thực hiện thủ tục"],
  ],
  household: [
    ["hkdRegister", "Đăng ký hộ kinh doanh"],
    ["hkdChange", "Thay đổi hộ kinh doanh"],
    ["hkdPause", "Tạm ngừng/tiếp tục hộ kinh doanh"],
    ["hkdClose", "Chấm dứt hộ kinh doanh"],
    ["hkdReissue", "Cấp lại giấy chứng nhận hộ kinh doanh"],
  ],
  convertHkd: [
    ["convert", "Đăng ký thành lập DN trên cơ sở chuyển đổi từ HKD"],
  ],
  lookup: [["lookup", "Tra cứu theo tên/mã mẫu"]],
};

const fieldLabels = {
  company_name: "Tên doanh nghiệp / hộ kinh doanh",
  company_code: "Mã số doanh nghiệp / mã số thuế",
  owner_name: "Họ tên chủ sở hữu/chủ hộ/người đại diện",
  owner_birth: "Ngày sinh",
  owner_gender: "Giới tính",
  owner_id: "Số định danh cá nhân",
  owner_phone: "Điện thoại",
  owner_email: "Email",
  street: "Số nhà, đường, tổ/xóm",
  ward: "Xã/Phường/Đặc khu",
  province: "Tỉnh/Thành phố",
  hq_street: "Số nhà, đường, tổ/xóm của trụ sở",
  hq_ward: "Xã/Phường/Đặc khu của trụ sở",
  hq_province: "Tỉnh/Thành phố của trụ sở",
  registry_office: "Cơ quan đăng ký kinh doanh",
  filing_place: "Nơi nộp hồ sơ / tỉnh thành",
  business_lines: "Ngành nghề kinh doanh",
  charter_capital: "Vốn điều lệ / vốn đầu tư",
  tax_method: "Phương pháp tính thuế GTGT",
  director_name: "Giám đốc/Tổng giám đốc",
  accountant_name: "Kế toán trưởng/phụ trách kế toán",
  change_content: "Nội dung thay đổi",
  new_address: "Địa chỉ mới",
  new_name: "Tên mới",
  new_legal_rep: "Người đại diện mới",
  branch_name: "Tên chi nhánh/VPĐD/địa điểm",
  branch_address: "Địa chỉ chi nhánh/VPĐD/địa điểm",
  pause_from: "Tạm ngừng từ ngày",
  pause_to: "Tạm ngừng đến ngày",
  dissolve_reason: "Lý do giải thể/chấm dứt",
  hkd_certificate: "Số Giấy chứng nhận đăng ký hộ kinh doanh",
  hkd_name: "Tên hộ kinh doanh được chuyển đổi",
  hkd_tax_code: "Mã số thuế hộ kinh doanh",
  hkd_address: "Địa chỉ trụ sở hộ kinh doanh",
};

const baseFields = ["company_name", "owner_name", "owner_id", "owner_phone", "street", "ward", "province"];
let people = JSON.parse(localStorage.getItem("people") || "[]");
let businessLines = JSON.parse(localStorage.getItem("businessLines") || "[]");

function mappedForms() {
  return window.FORM_MAPS?.forms || [];
}

function mappedById(id) {
  return mappedForms().find((form) => form.id === id);
}

const formationForms = {
  private: ["pl1_1"],
  llc1: ["pl1_2"],
  llc2: ["pl1_3", "pl1_6"],
  jsc: ["pl1_4", "pl1_7"],
  partnership: ["pl1_5", "pl1_9"],
};

const formationNames = {
  private: "doanh nghiệp tư nhân",
  llc1: "công ty TNHH một thành viên",
  llc2: "công ty TNHH hai thành viên trở lên",
  jsc: "công ty cổ phần",
  partnership: "công ty hợp danh",
};

function selected(id) {
  return document.getElementById(id).value;
}

function checked(id) {
  return document.getElementById(id).checked;
}

function optionize(select, items) {
  select.innerHTML = items.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
}

function formCard(key, reason = "") {
  if (!forms[key]) {
    const mapped = mappedById(key);
    return { key, pl: mapped?.pl || "", num: mapped?.num || "", title: mapped?.title || key, path: mapped ? `/${mapped.path}` : "#", reason };
  }
  const [pl, num, title, path] = forms[key];
  return { key, pl, num, title, path: path.replace(/^\.\.\//, "/"), reason };
}

function uniqueCards(cards) {
  return Array.from(new Map(cards.map((card) => [card.key, card])).values());
}

function commonFilingNotes() {
  const notes = [
    "Cơ quan xử lý chính với doanh nghiệp là Cơ quan đăng ký kinh doanh cấp tỉnh; hộ kinh doanh là cấp xã.",
    "Hồ sơ điện tử có giá trị pháp lý tương đương hồ sơ giấy; cần chuẩn bị bản điện tử đầy đủ, đúng thông tin kê khai trên Cổng thông tin quốc gia.",
  ];
  if (checked("onlineFiling")) notes.push("Nếu nộp online, người ký/nộp cần tài khoản định danh điện tử hoặc cơ chế ký/xác thực hợp lệ.");
  if (checked("authorizedFiler")) notes.push("Có ủy quyền: kèm văn bản ủy quyền và giấy tờ pháp lý của người được ủy quyền theo quy định về ủy quyền thực hiện thủ tục.");
  if (checked("conditionalBusiness")) notes.push("Ngành nghề có điều kiện: tách việc đăng ký doanh nghiệp với điều kiện kinh doanh sau đăng ký; cần kiểm tra giấy phép/chứng chỉ/vốn pháp định nếu có.");
  return notes;
}

function buildFormation({ convert = false } = {}) {
  const type = selected("entityType");
  const cards = (formationForms[type] || formationForms.llc1).map((key) => formCard(key, "Mẫu lõi theo loại hình dự kiến đăng ký."));
  const docs = ["Điều lệ công ty, trừ doanh nghiệp tư nhân.", "Bản sao giấy tờ pháp lý của cá nhân/tổ chức liên quan, trừ trường hợp được miễn do kê khai số định danh cá nhân theo quy định."];
  const notes = commonFilingNotes();
  const questions = ["Tên doanh nghiệp dự kiến đã tra cứu trùng/gây nhầm lẫn chưa?", "Địa chỉ trụ sở có quyền sử dụng hợp pháp và ghi theo địa giới hành chính hiện hành chưa?", "Ngành nghề kinh doanh chính và các ngành nghề phụ đã chốt mã ngành chưa?", "Vốn điều lệ/vốn đầu tư và tỷ lệ góp vốn của từng người đã chốt chưa?", "Ai là người đại diện theo pháp luật và thông tin số định danh cá nhân đã chính xác chưa?"];

  if (type === "private") docs.push("Bản sao giấy tờ pháp lý của chủ doanh nghiệp tư nhân nếu không kê khai số định danh cá nhân.");
  if (type === "llc2") docs.push("Danh sách thành viên và giấy tờ pháp lý của thành viên/người đại diện theo ủy quyền.");
  if (type === "jsc") docs.push("Danh sách cổ đông sáng lập; nếu có nhà đầu tư nước ngoài thì thêm danh sách cổ đông là nhà đầu tư nước ngoài.");
  if (type === "partnership") docs.push("Danh sách thành viên công ty hợp danh; giấy tờ pháp lý của thành viên.");
  if (checked("foreignInvestor")) {
    cards.push(formCard("pl1_8", "Dùng khi công ty cổ phần có cổ đông là nhà đầu tư nước ngoài."));
    docs.push("Giấy chứng nhận đăng ký đầu tư hoặc văn bản chấp thuận góp vốn/mua cổ phần/phần vốn góp nếu pháp luật đầu tư yêu cầu.");
    questions.push("Nhà đầu tư nước ngoài có thuộc diện phải đăng ký góp vốn/mua cổ phần/phần vốn góp trước không?");
  }
  if (checked("beneficialOwner")) {
    cards.push(formCard("pl1_10", "Kê khai danh sách chủ sở hữu hưởng lợi khi thuộc trường hợp phải kê khai."));
    if (type === "jsc" && checked("orgMember")) cards.push(formCard("pl1_11", "Dùng để xác định chủ sở hữu hưởng lợi qua cổ đông là tổ chức sở hữu từ 25% quyền biểu quyết trở lên."));
    questions.push("Ai là cá nhân cuối cùng sở hữu/kiểm soát doanh nghiệp theo tiêu chí chủ sở hữu hưởng lợi?");
  }
  if (checked("orgMember")) docs.push("Giấy tờ pháp lý của tổ chức, văn bản cử người đại diện theo ủy quyền và giấy tờ pháp lý của người đại diện theo ủy quyền.");
  if (selected("scenario") === "social") {
    cards.push(formCard("pl1_34", "Doanh nghiệp xã hội phải có cam kết mục tiêu xã hội, môi trường."));
    docs.push("Cam kết thực hiện mục tiêu xã hội, môi trường có chữ ký của chủ thể có thẩm quyền.");
  }
  if (selected("scenario") === "splitMerge") {
    docs.push("Nghị quyết/quyết định chia, tách, hợp nhất hoặc hợp đồng hợp nhất/sáp nhập tương ứng.");
    notes.push("Nhóm chia/tách/hợp nhất cần rà soát thêm điều khoản kế thừa quyền, nghĩa vụ, lao động, thuế và tài sản.");
  }
  if (convert) {
    docs.unshift("Bản sao Giấy chứng nhận đăng ký hộ kinh doanh.");
    notes.unshift("Đăng ký chuyển đổi từ hộ kinh doanh thực hiện tại cấp tỉnh nơi doanh nghiệp dự định đặt trụ sở.");
    notes.push("Sau khi doanh nghiệp chuyển đổi được cấp Giấy chứng nhận đăng ký doanh nghiệp, hộ kinh doanh không được tiếp tục hoạt động.");
    notes.push("Cơ quan đăng ký kinh doanh cấp xã chuyển tình trạng hộ kinh doanh sang đã chấm dứt sau khi nhận thông tin hoàn thành nghĩa vụ thuế.");
    questions.unshift("Hộ kinh doanh đã hoàn thành nghĩa vụ thuế đến thời điểm chuyển đổi chưa?");
    questions.unshift("Loại hình doanh nghiệp sau chuyển đổi là gì?");
  }

  return {
    title: `${convert ? "Chuyển hộ kinh doanh sang" : "Thành lập"} ${formationNames[type] || "doanh nghiệp"}`,
    risk: checked("foreignInvestor") || selected("scenario") === "splitMerge" ? "high" : checked("conditionalBusiness") ? "medium" : "low",
    forms: uniqueCards(cards),
    docs,
    notes,
    questions,
  };
}

function buildChange() {
  const scenario = selected("scenario");
  const cards = [];
  const docs = [];
  const notes = commonFilingNotes();
  const questions = ["Doanh nghiệp đang là loại hình nào?", "Nội dung thay đổi có làm sửa Điều lệ không?", "Người ký hồ sơ là ai và có đúng thẩm quyền không?"];

  if (scenario === "legalRep") {
    cards.push(formCard("pl1_13", "Mẫu chuyên biệt cho thay đổi người đại diện theo pháp luật."));
    docs.push("Nghị quyết/quyết định của chủ sở hữu/HĐTV/ĐHĐCĐ/HĐQT theo trường hợp cụ thể.");
    questions.push("Việc đổi người đại diện có làm thay đổi nội dung Điều lệ ngoài thông tin cá nhân và chữ ký không?");
  } else if (scenario === "owner") {
    cards.push(formCard(selected("entityType") === "private" ? "pl1_14" : "pl1_15", "Dùng cho thay đổi chủ DNTN hoặc chủ sở hữu công ty TNHH một thành viên."));
    docs.push("Hợp đồng/chứng từ chuyển nhượng, thừa kế, tặng cho hoặc tài liệu chứng minh thay đổi chủ sở hữu theo tình huống.");
  } else if (scenario === "reissue") {
    cards.push(formCard("pl1_26", "Cấp lại giấy chứng nhận/giấy xác nhận do mất, cháy, rách, nát hoặc bị tiêu hủy."));
  } else if (scenario === "beneficial") {
    cards.push(formCard("pl1_12", "Thông báo cập nhật nội dung đăng ký doanh nghiệp."));
    cards.push(formCard("pl1_10", "Danh sách chủ sở hữu hưởng lợi."));
    if (checked("orgMember")) cards.push(formCard("pl1_11", "Kê khai để xác định chủ sở hữu hưởng lợi qua tổ chức."));
  } else if (scenario === "businessLines") {
    cards.push(formCard("pl1_12", "Thông báo thay đổi ngành, nghề kinh doanh."));
    docs.push("Bảng ngành nghề bổ sung/bỏ/sửa chi tiết, mã ngành cấp 4 và ngành nghề chính sau thay đổi.");
    questions.push("Ngành nào bổ sung, ngành nào bỏ, ngành nào chỉ sửa chi tiết?");
    questions.push("Sau thay đổi, ngành nghề kinh doanh chính là ngành nào?");
  } else {
    cards.push(formCard("pl1_12", "Mẫu chung cho đăng ký/thông báo thay đổi, cập nhật, bổ sung, hiệu đính."));
    docs.push("Nghị quyết/quyết định của chủ sở hữu/HĐTV/ĐHĐCĐ/HĐQT theo loại hình và nội dung thay đổi.");
  }

  if (scenario === "address" && checked("taxMove")) {
    docs.push("Tài liệu/hoàn tất thủ tục với cơ quan thuế về chuyển địa điểm trước khi đăng ký thay đổi trụ sở.");
    notes.push("Đổi địa chỉ làm đổi cơ quan thuế quản lý: xử lý thủ tục thuế trước khi nộp hồ sơ thay đổi trụ sở.");
  }
  if (scenario === "capital") {
    docs.push("Biên bản họp HĐTV hoặc ĐHĐCĐ nếu loại hình yêu cầu; danh sách thành viên/cổ đông cập nhật nếu thay đổi tỷ lệ/phần vốn.");
    if (selected("entityType") === "llc2") cards.push(formCard("pl1_6", "Cập nhật danh sách thành viên khi thay đổi phần vốn góp."));
  }

  return { title: "Thay đổi thông tin doanh nghiệp", risk: checked("taxMove") || checked("foreignInvestor") ? "high" : "medium", forms: uniqueCards(cards), docs, notes, questions };
}

function buildBranch() {
  const s = selected("scenario");
  const map = { openBranch: "pl1_17", changeBranch: "pl1_19", foreignBranch: "pl1_18", closeBranch: "pl1_28" };
  const docs = ["Quyết định/nghị quyết của doanh nghiệp về việc lập, thay đổi hoặc chấm dứt đơn vị phụ thuộc.", "Thông tin người đứng đầu chi nhánh/VPĐD nếu có."];
  const notes = commonFilingNotes();
  const questions = ["Đơn vị là chi nhánh, văn phòng đại diện hay địa điểm kinh doanh?", "Địa chỉ đơn vị phụ thuộc thuộc tỉnh/thành nào?", "Ngành nghề/hoạt động của chi nhánh có khớp với ngành nghề doanh nghiệp không?"];
  if (s === "foreignBranch") questions.push("Quốc gia/vùng lãnh thổ đặt chi nhánh/VPĐD ở nước ngoài là đâu và có yêu cầu hợp pháp hóa tài liệu không?");
  return { title: "Hồ sơ chi nhánh, văn phòng đại diện, địa điểm kinh doanh", risk: s === "foreignBranch" ? "high" : "medium", forms: [formCard(map[s] || "pl1_17", "Mẫu chính cho nghiệp vụ đã chọn.")], docs, notes, questions };
}

function buildPauseClose() {
  const s = selected("scenario");
  const map = { pause: "pl1_27", dissolve: "pl1_30", cancelDissolve: "pl1_31", stopProcedure: "pl1_33" };
  const docs = [];
  const notes = commonFilingNotes();
  const questions = ["Ngày dự kiến bắt đầu hiệu lực của thủ tục là ngày nào?", "Doanh nghiệp còn nghĩa vụ thuế, lao động, hợp đồng hoặc khoản nợ nào chưa xử lý không?"];
  if (s === "dissolve") {
    docs.push("Nghị quyết/quyết định giải thể; phương án xử lý nợ; tài liệu hoàn tất nghĩa vụ thuế và các nghĩa vụ liên quan.");
    notes.push("Giải thể là nhóm rủi ro cao: cần đối chiếu nghĩa vụ thuế, bảo hiểm, lao động, hợp đồng và tài sản trước khi nộp.");
  }
  return { title: "Tạm ngừng, chấm dứt hoặc giải thể", risk: s === "dissolve" ? "high" : "medium", forms: [formCard(map[s] || "pl1_27", "Mẫu chính cho nghiệp vụ đã chọn.")], docs, notes, questions };
}

function buildHousehold() {
  const s = selected("scenario");
  const map = { hkdRegister: "pl2_1", hkdChange: "pl2_2", hkdPause: "pl2_3", hkdClose: "pl2_4", hkdReissue: "pl2_5" };
  const docs = ["Giấy tờ pháp lý của chủ hộ/thành viên hộ gia đình theo trường hợp.", "Thông tin địa chỉ, ngành nghề, vốn kinh doanh, số điện thoại liên hệ."];
  const notes = ["Hộ kinh doanh nộp hồ sơ tại Cơ quan đăng ký kinh doanh cấp xã.", "Khi thay đổi một số nội dung đăng ký hộ kinh doanh, thời hạn thường là 10 ngày kể từ ngày có thay đổi."];
  const questions = ["Chủ hộ là cá nhân hay các thành viên hộ gia đình?", "Có thay đổi địa chỉ dẫn đến đổi cơ quan thuế quản lý trực tiếp không?", "Số điện thoại liên hệ đã có trong hồ sơ đăng ký chưa?"];
  if (checked("taxMove")) notes.push("Đổi địa chỉ làm đổi cơ quan thuế quản lý: thực hiện thủ tục thuế trước khi đăng ký thay đổi với cấp xã.");
  return { title: "Hồ sơ hộ kinh doanh", risk: checked("taxMove") ? "medium" : "low", forms: [formCard(map[s] || "pl2_1", "Mẫu chính cho nghiệp vụ đã chọn.")], docs, notes, questions };
}

function buildResult() {
  const p = selected("procedure");
  if (p === "formation") return buildFormation();
  if (p === "change") return buildChange();
  if (p === "branch") return buildBranch();
  if (p === "pauseClose") return buildPauseClose();
  if (p === "household") return buildHousehold();
  if (p === "convertHkd") return buildFormation({ convert: true });
  const picked = selected("mappedFormPicker") || mappedForms()[0]?.id;
  return { title: "Tra cứu và điền trực tiếp biểu mẫu", risk: "low", forms: picked ? [formCard(picked, "Mẫu được chọn trực tiếp từ bản đồ 108 mẫu.")] : [], docs: ["Dùng field chi tiết bên dưới để điền vào mẫu Word."], notes: ["Chế độ này đi theo bản đồ field trích xuất từ Word; các trường không liên quan có thể bỏ trống."], questions: ["Mẫu này dùng cho tình huống nghiệp vụ nào và ai là người có thẩm quyền ký?"] };
}

function requiredFields() {
  const p = selected("procedure");
  const s = selected("scenario");
  const type = selected("entityType");
  let fields = [...baseFields];
  if (p === "formation" || p === "convertHkd") {
    fields.push("owner_birth", "owner_gender", "owner_email", "hq_street", "hq_ward", "hq_province", "registry_office", "filing_place", "charter_capital", "director_name", "accountant_name", "tax_method");
    if (p === "convertHkd") fields.push("hkd_name", "hkd_certificate", "hkd_tax_code", "hkd_address");
  }
  if (p === "change") {
    fields = ["company_name", "company_code", "owner_name", "owner_id", "registry_office", "filing_place", "change_content"];
    if (s === "businessLines") fields = ["company_name", "company_code", "owner_name", "owner_id", "registry_office", "filing_place"];
    if (s === "address") fields.push("new_address");
    if (s === "name") fields.push("new_name");
    if (s === "legalRep") fields.push("new_legal_rep", "owner_birth", "owner_gender", "owner_phone");
    if (s === "capital") fields.push("charter_capital");
  }
  if (p === "branch") fields = ["company_name", "company_code", "owner_name", "registry_office", "filing_place", "branch_name", "branch_address"];
  if (p === "pauseClose") {
    fields = ["company_name", "company_code", "owner_name"];
    if (s === "pause") fields.push("pause_from", "pause_to");
    if (s === "dissolve") fields.push("dissolve_reason");
  }
  if (p === "household") {
    fields = ["company_name", "owner_name", "owner_birth", "owner_gender", "owner_id", "owner_phone", "street", "ward", "province", "charter_capital"];
    if (s !== "hkdRegister") fields.push("company_code");
    if (s === "hkdChange") fields.push("change_content");
    if (s === "hkdPause") fields.push("pause_from", "pause_to");
    if (s === "hkdClose") fields.push("dissolve_reason");
  }
  if (type === "private" && !fields.includes("charter_capital")) fields.push("charter_capital");
  return [...new Set(fields)];
}

function renderFields() {
  const fields = requiredFields();
  const multiline = new Set(["change_content", "new_address", "branch_address", "dissolve_reason", "hkd_address"]);
  document.getElementById("dynamicFields").innerHTML = fields.map((key) => {
    const label = fieldLabels[key] || key;
    const saved = localStorage.getItem(`field:${key}`) || "";
    const input = multiline.has(key)
      ? `<textarea id="field_${key}" data-field="${key}">${saved}</textarea>`
      : `<input id="field_${key}" data-field="${key}" value="${saved}" />`;
    return `<label>${label} <span class="required-mark">*</span>${input}</label>`;
  }).join("");
  document.querySelectorAll("[data-field]").forEach((el) => {
    el.addEventListener("input", () => localStorage.setItem(`field:${el.dataset.field}`, el.value));
  });
  renderBusinessLines();
  renderDeepFields();
  renderPeople();
}

function needsBusinessLines() {
  const p = selected("procedure");
  const s = selected("scenario");
  return p === "formation" || p === "convertHkd" || p === "branch" || p === "household" || (p === "change" && s === "businessLines");
}

function businessLineMode() {
  return selected("procedure") === "change" && selected("scenario") === "businessLines" ? "change" : "register";
}

function emptyBusinessLine() {
  return { action: "Bổ sung", code: "", name: "", detail: "", isPrimary: false };
}

function saveBusinessLines() {
  localStorage.setItem("businessLines", JSON.stringify(businessLines));
}

function getBusinessLines() {
  if (!needsBusinessLines()) return [];
  return businessLines.filter((line) => ["code", "name", "detail"].some((key) => String(line[key] || "").trim()));
}

function businessLineSummary(rows = getBusinessLines()) {
  return rows.map((line, index) => {
    const action = businessLineMode() === "change" ? `${line.action || "Bổ sung"} - ` : "";
    const primary = line.isPrimary ? " | Ngành chính" : "";
    const detail = line.detail ? ` | Chi tiết: ${line.detail}` : "";
    return `${index + 1}. ${action}${line.code || ""} - ${line.name || ""}${primary}${detail}`;
  }).join("\n");
}

function renderBusinessLines() {
  const container = document.getElementById("dynamicFields");
  if (!needsBusinessLines()) return;
  if (!businessLines.length) businessLines = [emptyBusinessLine()];
  const mode = businessLineMode();
  container.insertAdjacentHTML("beforeend", `
    <div class="structured-editor business-lines-editor">
      <div class="repeat-head">
        <h3>${mode === "change" ? "Bảng thay đổi ngành, nghề kinh doanh" : "Bảng ngành, nghề kinh doanh"}</h3>
        <button id="addBusinessLine" type="button">Thêm ngành</button>
      </div>
      <div class="business-table ${mode === "change" ? "change-mode" : "register-mode"}">
        <div class="business-table-head">
          ${mode === "change" ? "<span>Loại</span>" : ""}
          <span>Mã ngành</span>
          <span>Tên ngành, nghề</span>
          <span>Chi tiết</span>
          <span>Chính</span>
          <span></span>
        </div>
        ${businessLines.map((line, index) => `
          <div class="business-table-row">
            ${mode === "change" ? `<select data-business-line="${index}" data-business-field="action">
              ${["Bổ sung", "Bỏ", "Sửa chi tiết"].map((x) => `<option ${line.action === x ? "selected" : ""}>${x}</option>`).join("")}
            </select>` : ""}
            <input data-business-line="${index}" data-business-field="code" value="${line.code || ""}" placeholder="6201" />
            <input data-business-line="${index}" data-business-field="name" value="${line.name || ""}" placeholder="Lập trình máy vi tính" />
            <input data-business-line="${index}" data-business-field="detail" value="${line.detail || ""}" placeholder="Chi tiết theo giấy phép/điều kiện nếu có" />
            <input type="checkbox" ${line.isPrimary ? "checked" : ""} data-business-line="${index}" data-business-field="isPrimary" />
            <button type="button" data-remove-business-line="${index}">Xóa</button>
          </div>
        `).join("")}
      </div>
    </div>
  `);
  document.getElementById("addBusinessLine").addEventListener("click", () => {
    businessLines.push(emptyBusinessLine());
    saveBusinessLines();
    render();
  });
  document.querySelectorAll("[data-remove-business-line]").forEach((button) => {
    button.addEventListener("click", () => {
      businessLines.splice(Number(button.dataset.removeBusinessLine), 1);
      saveBusinessLines();
      render();
    });
  });
  document.querySelectorAll("[data-business-line]").forEach((input) => {
    input.addEventListener("input", updateBusinessLine);
    input.addEventListener("change", updateBusinessLine);
  });
}

function updateBusinessLine(event) {
  const index = Number(event.target.dataset.businessLine);
  const field = event.target.dataset.businessField;
  businessLines[index][field] = event.target.type === "checkbox" ? event.target.checked : event.target.value;
  saveBusinessLines();
}

function renderDeepFields() {
  const container = document.getElementById("dynamicFields");
  const formIds = getFormIds();
  const mapped = formIds.map(mappedById).filter(Boolean);
  if (!mapped.length) return;
  const html = mapped.map((form) => {
    const fields = form.fields.filter(shouldShowDeepField).slice(0, 80);
    const checks = form.checkboxes.slice(0, 80);
    return `
      <div class="deep-field-section">
        <h3>${form.pl} - Mẫu ${String(form.num).padStart(2, "0")}: ${form.title}</h3>
        ${(form.structuredTables || []).map((table) => `<p class="structured-note">${table.title}</p>`).join("")}
        ${fields.map((field) => {
          const key = `deep:${form.id}:${field.id}`;
          const saved = localStorage.getItem(key) || "";
          const input = field.type === "textarea"
            ? `<textarea data-deep-field="${form.id}" data-deep-id="${field.id}" data-label="${field.label}" data-paragraph="${field.paragraphIndex}">${saved}</textarea>`
            : `<input data-deep-field="${form.id}" data-deep-id="${field.id}" data-label="${field.label}" data-paragraph="${field.paragraphIndex}" value="${saved}" />`;
          return `<label>${field.label}${input}</label>`;
        }).join("")}
        ${checks.length ? `<h3>Ô chọn trong mẫu</h3>` : ""}
        ${checks.map((box) => {
          const key = `deepbox:${form.id}:${box.id}`;
          const checked = localStorage.getItem(key) === "1" ? "checked" : "";
          return `<label class="check"><input type="checkbox" ${checked} data-deep-checkbox="${form.id}" data-box-id="${box.id}" data-label="${box.label}" data-paragraph="${box.paragraphIndex}" /><span>${box.label}</span></label>`;
        }).join("")}
      </div>`;
  }).join("");
  container.insertAdjacentHTML("beforeend", html);
  document.querySelectorAll("[data-deep-field]").forEach((el) => {
    el.addEventListener("input", () => localStorage.setItem(`deep:${el.dataset.deepField}:${el.dataset.deepId}`, el.value));
  });
  document.querySelectorAll("[data-deep-checkbox]").forEach((el) => {
    el.addEventListener("change", () => localStorage.setItem(`deepbox:${el.dataset.deepCheckbox}:${el.dataset.boxId}`, el.checked ? "1" : "0"));
  });
}

function shouldShowDeepField(field) {
  const low = (field.label || "").toLowerCase();
  if (field.commonKey === "business_lines") return false;
  if (low.includes("tình trạng thành lập")) return false;
  if (low === "stt" || low === "tên ngành" || low === "mã ngành") return false;
  if (low.includes("đánh dấu x vào ô thích hợp")) return false;
  return true;
}

function needsPeople() {
  const type = selected("entityType");
  const p = selected("procedure");
  const s = selected("scenario");
  return type === "llc2" || type === "jsc" || type === "partnership" || checked("beneficialOwner") || checked("foreignInvestor") || s === "capital" || s === "beneficial";
}

function emptyPerson(role = "Thành viên/cổ đông") {
  return { name: "", type: "Cá nhân", idNumber: "", address: "", capital: "", ratio: "", role };
}

function savePeople() {
  localStorage.setItem("people", JSON.stringify(people));
}

function renderPeople() {
  const section = document.getElementById("peopleSection");
  if (!needsPeople()) {
    section.innerHTML = "";
    return;
  }
  if (!people.length) people = [emptyPerson(selected("entityType") === "jsc" ? "Cổ đông sáng lập" : "Thành viên")];
  section.innerHTML = `
    <div class="repeat-head">
      <h3>Danh sách người/tổ chức liên quan</h3>
      <button id="addPerson" type="button">Thêm dòng</button>
    </div>
    ${people.map((person, index) => `
      <article class="person-card">
        <header>
          <span>Dòng ${index + 1}</span>
          <button type="button" data-remove-person="${index}">Xóa</button>
        </header>
        <div class="person-grid">
          <label>Họ tên/Tổ chức<input data-person="${index}" data-person-field="name" value="${person.name || ""}" /></label>
          <label>Loại<select data-person="${index}" data-person-field="type"><option ${person.type === "Cá nhân" ? "selected" : ""}>Cá nhân</option><option ${person.type === "Tổ chức" ? "selected" : ""}>Tổ chức</option></select></label>
          <label>Số giấy tờ/MST<input data-person="${index}" data-person-field="idNumber" value="${person.idNumber || ""}" /></label>
          <label>Vai trò<input data-person="${index}" data-person-field="role" value="${person.role || ""}" /></label>
          <label>Địa chỉ<input data-person="${index}" data-person-field="address" value="${person.address || ""}" /></label>
          <label>Vốn góp<input data-person="${index}" data-person-field="capital" value="${person.capital || ""}" /></label>
          <label>Tỷ lệ %<input data-person="${index}" data-person-field="ratio" value="${person.ratio || ""}" /></label>
        </div>
      </article>
    `).join("")}
  `;
  document.getElementById("addPerson").addEventListener("click", () => {
    people.push(emptyPerson());
    savePeople();
    renderPeople();
  });
  document.querySelectorAll("[data-remove-person]").forEach((button) => {
    button.addEventListener("click", () => {
      people.splice(Number(button.dataset.removePerson), 1);
      savePeople();
      renderPeople();
    });
  });
  document.querySelectorAll("[data-person]").forEach((input) => {
    input.addEventListener("input", updatePerson);
    input.addEventListener("change", updatePerson);
  });
}

function updatePerson(event) {
  const index = Number(event.target.dataset.person);
  const field = event.target.dataset.personField;
  people[index][field] = event.target.value;
  savePeople();
}

function render() {
  const result = buildResult();
  document.getElementById("summaryTitle").textContent = result.title;
  const risk = document.getElementById("riskBadge");
  risk.className = `risk ${result.risk}`;
  risk.textContent = result.risk === "high" ? "Cần rà soát kỹ" : result.risk === "medium" ? "Có điều kiện kèm theo" : "Thông thường";
  document.getElementById("formsList").innerHTML = result.forms.map((item) => `
    <article class="form-card">
      <header>
        <div>
          <strong>${item.pl} - Mẫu ${String(item.num).padStart(2, "0")}</strong>
          <p>${item.title}</p>
        </div>
        <a href="${item.path}">Mở Word</a>
      </header>
      ${item.reason ? `<p class="meta">${item.reason}</p>` : ""}
    </article>
  `).join("");
  document.getElementById("docsList").innerHTML = result.docs.map((x) => `<li>${x}</li>`).join("");
  document.getElementById("notesList").innerHTML = result.notes.map((x) => `<li>${x}</li>`).join("");
  document.getElementById("questionsList").innerHTML = result.questions.map((x) => `<li>${x}</li>`).join("");
  renderFields();
  renderCatalog();
}

function renderCatalog() {
  const q = document.getElementById("catalogSearch").value.toLowerCase().trim();
  const mappedItems = mappedForms().map((form) => ({
    key: form.id,
    pl: form.pl,
    num: form.num,
    title: form.title,
    path: `/${form.path}`,
  }));
  const fallbackItems = Object.entries(forms).map(([key, data]) => ({
    key,
    pl: data[0],
    num: data[1],
    title: data[2],
    path: data[3],
  }));
  const items = (mappedItems.length ? mappedItems : fallbackItems)
    .filter((item) => !q || `${item.key} ${item.pl} ${item.num} ${item.title}`.toLowerCase().includes(q));
  document.getElementById("catalogList").innerHTML = items.map((item) => `
    <article class="catalog-row">
      <header>
        <div><strong>${item.pl} - Mẫu ${String(item.num).padStart(2, "0")}</strong><p>${item.title}</p></div>
        <a href="${item.path}">Mở</a>
      </header>
    </article>
  `).join("");
}

function updateScenarioOptions() {
  optionize(document.getElementById("scenario"), scenariosByProcedure[selected("procedure")]);
  document.getElementById("mappedFormPickerWrap").classList.toggle("hidden", selected("procedure") !== "lookup");
  if (selected("procedure") === "lookup") {
    optionize(document.getElementById("mappedFormPicker"), mappedForms().map((form) => [form.id, `${form.pl} - Mẫu ${String(form.num).padStart(2, "0")} | ${form.title}`]));
  }
  render();
}

function checklistText() {
  const r = buildResult();
  return [
    r.title,
    "",
    "Mẫu cần dùng:",
    ...r.forms.map((f) => `- ${f.pl} Mẫu ${f.num}: ${f.title}`),
    "",
    "Giấy tờ ngoài biểu mẫu:",
    ...r.docs.map((x) => `- ${x}`),
    "",
    "Câu hỏi cần chốt:",
    ...r.questions.map((x) => `- ${x}`),
    "",
    "Lưu ý:",
    ...r.notes.map((x) => `- ${x}`),
  ].join("\n");
}

function getFormIds() {
  return buildResult().forms.map((f) => f.key);
}

function getData() {
  const data = {};
  document.querySelectorAll("[data-field]").forEach((el) => {
    data[el.dataset.field] = el.value.trim();
  });
  const lines = getBusinessLines();
  if (lines.length) data.business_lines = businessLineSummary(lines);
  if (selected("procedure") === "change" && selected("scenario") === "businessLines") {
    data.change_content = data.change_content || "Thay đổi ngành, nghề kinh doanh";
  }
  return data;
}

function getPeople() {
  return needsPeople() ? people.filter((p) => Object.values(p).some((value) => String(value || "").trim())) : [];
}

function getAutoFields() {
  const out = {};
  document.querySelectorAll("[data-deep-field]").forEach((el) => {
    const formId = el.dataset.deepField;
    out[formId] ||= {};
    out[formId][el.dataset.deepId] = {
      label: el.dataset.label,
      paragraphIndex: Number(el.dataset.paragraph),
      value: el.value.trim(),
    };
  });
  return out;
}

function getAutoCheckboxes() {
  const out = {};
  document.querySelectorAll("[data-deep-checkbox]").forEach((el) => {
    const formId = el.dataset.deepCheckbox;
    out[formId] ||= {};
    out[formId][el.dataset.boxId] = {
      label: el.dataset.label,
      paragraphIndex: Number(el.dataset.paragraph),
      checked: el.checked,
    };
  });
  return out;
}

function labelsForPayload() {
  const proc = procedures.find(([value]) => value === selected("procedure"))?.[1] || "";
  const entity = entityTypes.find(([value]) => value === selected("entityType"))?.[1] || "";
  const scenario = scenariosByProcedure[selected("procedure")].find(([value]) => value === selected("scenario"))?.[1] || "";
  return { proc, entity, scenario };
}

optionize(document.getElementById("procedure"), procedures);
optionize(document.getElementById("entityType"), entityTypes);
updateScenarioOptions();

document.getElementById("procedure").addEventListener("change", updateScenarioOptions);
document.querySelectorAll("select, input").forEach((el) => el.addEventListener("change", render));
document.getElementById("catalogSearch").addEventListener("input", renderCatalog);
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".tab-page").forEach((x) => x.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});
document.getElementById("printChecklist").addEventListener("click", () => window.print());
async function writeClipboard(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (error) {
    // Fall through to the legacy path, which works better in embedded WebKit.
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.focus();
  area.select();
  const ok = document.execCommand("copy");
  area.remove();
  return ok;
}

document.getElementById("copyChecklist").addEventListener("click", async () => {
  const ok = await writeClipboard(checklistText());
  document.getElementById("copyChecklist").textContent = "Đã sao chép";
  if (!ok) document.getElementById("copyChecklist").textContent = "Không sao chép được";
  setTimeout(() => (document.getElementById("copyChecklist").textContent = "Sao chép checklist"), 1600);
});

document.getElementById("generateDossier").addEventListener("click", async () => {
  const resultBox = document.getElementById("generateResult");
  const missing = requiredFields().filter((key) => !(document.querySelector(`[data-field="${key}"]`)?.value || "").trim());
  if (needsPeople() && !getPeople().length) missing.push("people");
  if (needsBusinessLines() && !getBusinessLines().some((line) => line.code && line.name)) missing.push("businessLines");
  if (missing.length) {
    resultBox.innerHTML = `Còn thiếu: ${missing.map((key) => {
      if (key === "people") return "danh sách người/tổ chức liên quan";
      if (key === "businessLines") return "bảng ngành, nghề kinh doanh";
      return fieldLabels[key];
    }).join(", ")}.`;
    return;
  }
  const labels = labelsForPayload();
  const payload = {
    procedure: selected("procedure"),
    scenario: selected("scenario"),
    entityType: selected("entityType"),
    procedureLabel: labels.proc,
    entityLabel: labels.entity,
    scenarioLabel: labels.scenario,
    flags: {
      foreignInvestor: checked("foreignInvestor"),
      beneficialOwner: checked("beneficialOwner"),
      orgMember: checked("orgMember"),
      taxMove: checked("taxMove"),
      conditionalBusiness: checked("conditionalBusiness"),
      authorizedFiler: checked("authorizedFiler"),
      onlineFiling: checked("onlineFiling"),
    },
    data: getData(),
    people: getPeople(),
    businessLines: getBusinessLines(),
    autoFields: getAutoFields(),
    autoCheckboxes: getAutoCheckboxes(),
    formIds: getFormIds(),
  };
  resultBox.textContent = "Đang sinh bộ hồ sơ...";
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await response.json();
    if (!response.ok) throw new Error(json.error || "Không sinh được hồ sơ");
    const folderUrl = `/${json.folder}/`;
    const zipUrl = `/api/download?path=${encodeURIComponent(json.zip)}`;
    const revealUrl = `/api/reveal?path=${encodeURIComponent(json.folder)}`;
    resultBox.innerHTML = `
      <strong>Đã sinh ${json.count} file Word.</strong>
      <div class="result-actions">
        <a class="button-link" href="${folderUrl}">Xem thư mục</a>
        <a class="button-link primary-link" href="${zipUrl}" download>Tải ZIP</a>
        <button id="revealFolder" type="button">Mở trong Finder</button>
      </div>
    `;
    document.getElementById("revealFolder").addEventListener("click", async () => {
      await fetch(revealUrl);
    });
  } catch (error) {
    resultBox.innerHTML = "Chưa kết nối server sinh hồ sơ. Hãy chạy <strong>python3 run_app.py</strong> rồi mở app tại địa chỉ local.";
  }
});

document.getElementById("serverNotice").textContent = location.protocol === "file:"
  ? "Muốn sinh Word tự động: chạy python3 run_app.py rồi mở link local."
  : "Đang dùng chế độ sinh hồ sơ tự động.";
