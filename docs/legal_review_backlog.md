# Legal review backlog — 33 form BLOCKED_LEGAL_REVIEW

Trạng thái: **Backlog chờ owner quyết định**. Trích trực tiếp từ
`app/data/table_specs/manifest.json` (`table-manifest-v1`) — câu hỏi pháp lý
giữ nguyên văn từ `legal_questions`, bằng chứng trích `source_evidence`,
`notes`, `defects`. Không suy diễn căn cứ mới.

Số liệu: 87 form census — TABLE_COMPLETE 4, BLOCKED_LEGAL_REVIEW **33**,
NO_TABLE 50. Cả 33 form BLOCKED đều có `legal_questions`.

Ưu tiên xử lý theo domain: capital-assets → people-ownership → tax →
branches/admin (nhóm theo kind/title vì entry manifest không có trường owner).

---

## Domain 1 — capital-assets (6 form)

### 1. PLI_M01 — BLOCKED_LEGAL_REVIEW

- Blocker: section `tai_san_gop_von_von_dau_tu` — "Tài sản góp vốn (trong vốn
  đầu tư)", fixed-matrix, missing_grid. Evidence:
  `app/templates/PLI_M01.docx#p91-p123`. Notes: chuỗi paragraph rời, không có
  w:tbl, blocks không có input nào cho vùng này.
- Câu hỏi pháp lý (nguyên văn):
  1. Ô "3 tháng một lần" (mục 7 BHXH) thiếu hoàn toàn checkbox token trong
     template/blocks — xác nhận dùng chung key `chk_bc_03_thang` như các mẫu khác?
  2. "Các tài sản khác" trong Tài sản góp vốn: mẫu cho phép "lập thành danh mục
     riêng kèm theo hồ sơ" — có cần sub-grid danh mục tài sản con không?
  3. Cặp ô Có/Không dùng chung key `chk_khong` (hiển thị ngoại tệ trên GCN;
     QSDĐ đảo/biên giới): tách key riêng để tránh liên động?
- Owner cần chốt + tác động:
  - (2A) Có sub-grid tài sản khác / (2B) chỉ ô mô tả text → A tăng scope P3
    capital-assets thêm component con; B giữ fixed-matrix thuần.
  - (1) dùng key chung / tách key; (3) giữ chung `chk_khong` / tách key riêng
    → ảnh hưởng binding + draft cũ.
- Task bị chặn: P3 capital-assets — rebuild `tai_san_gop_von_von_dau_tu`; fixture
  F4 liên quan; bổ sung binding BHXH (`partial`).

### 2. PLI_M02 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `nddpl_uy_quyen_chu_so_huu` (nested-grid, missing_grid,
  header nối 13 cột, `app/templates/PLI_M02.docx#p140-p144`),
  `nguon_von_dieule` + `tai_san_gop_von_von_dieu_le` (fixed-matrix,
  missing_grid), `mo_hinh_to_chuc_cong_ty` (fixed-matrix lựa chọn, missing_grid).
- Câu hỏi pháp lý (nguyên văn):
  1. Row contract danh sách NĐDPL/người đại diện theo ủy quyền: NĐDPL không kê
     khai vốn được ủy quyền (chân trang 6) còn người ủy quyền có tỷ lệ %
     (chân trang 7) — phân biệt kiểu dòng thế nào?
  2. Nguồn vốn điều lệ: tỷ lệ (%) và Tổng cộng có phải computed/outputOnly,
     tổng phải đối chiếu vốn điều lệ?
  3. Mô hình tổ chức công ty: dựng fixed-matrix radio chọn-1 hay giữ 2 chk độc lập?
- Owner cần chốt + tác động: (1) discriminator 2 row-type / tách 2 bảng →
  quyết định shape nested-grid N1 (fixture đầu); (2) nếu YES khớp contract P2
  proposed; (3) radio chọn-1 đơn giản hóa validation.
- Task bị chặn: nested-grid N1, fixed-matrix F4, rebuild nguồn vốn/tài sản M02.

### 3. PLI_M03 — BLOCKED_LEGAL_REVIEW

- Blocker: section `nguon_von_dieule` — "6. Nguồn vốn điều lệ", fixed-matrix,
  missing_grid (`app/templates/PLI_M03.docx#p108-p127`). Notes: template NGUỒN
  kết thúc ngay sau "Tổng cộng", không có mục thuế/BHXH/CSHHL như Mẫu 2.
- Câu hỏi pháp lý (nguyên văn): "Template/nguồn PLI_M03 kết thúc ngay sau mục 6
  Nguồn vốn điều lệ (không có thông tin đăng ký thuế/BHXH/CSHHL như Mẫu 2):
  đây là đầy đủ nội dung biểu mẫu hay file nguồn bị cắt khi tách từ file full?
  Cần đối chiếu bản gốc."
- Owner cần chốt + tác động: (A) đủ nội dung → dựng fixed-matrix ngay;
  (B) nguồn bị cắt → lấy bản gốc, mở lại census form này.
- Task bị chặn: P3 capital-assets — rebuild nguồn vốn M03; fixture F2.

### 4. PLI_M04 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `co_cau_loai_co_phan` + `co_phan_duoc_quyen_chao_ban`
  (fixed-matrix, missing_grid), `nguon_von_dieule`
  (`app/templates/PLI_M04.docx#p127-p184`). Template kết thúc sau mục 7.
- Câu hỏi pháp lý (nguyên văn):
  1. Giá trị loại cổ phần = số lượng × mệnh giá, Tổng số đối chiếu vốn điều lệ:
     xác nhận formula/computed policy trước khi dựng fixed-matrix?
  2. Template/nguồn PLI_M04 kết thúc tại mục 7 (cổ phần được quyền chào bán)
     mà không có mục thuế/BHXH/CSHHL như Mẫu 2: đủ nội dung pháp lý hay file
     nguồn bị cắt?
- Owner cần chốt + tác động: (1) formula computed → khớp contract P2; ngược lại
  phải cho nhập tay tổng (rủi ro lệch số); (2) như PLI_M03 (A/B).
- Task bị chặn: fixed-matrix F3, rebuild cơ cấu cổ phần + cổ phần chào bán M04.

### 5. PLI_M05 — BLOCKED_LEGAL_REVIEW

- Blocker: section `nguon_von_dieule` — "6. Nguồn vốn điều lệ", fixed-matrix,
  missing_grid (`app/templates/PLI_M05.docx#p85-p104`). Notes: template kết thúc
  ngay sau "Tổng cộng"; mẫu không có bảng thành viên hợp danh (theo Mẫu 9 gửi kèm).
- Câu hỏi pháp lý (nguyên văn): "Template/nguồn PLI_M05 kết thúc ngay sau mục 6
  Nguồn vốn điều lệ: đủ nội dung biểu mẫu hay file nguồn bị cắt khi tách? Thành
  viên hợp danh kê khai theo Mẫu 9 gửi kèm - xác nhận M05 không cần lưới thành
  viên inline?"
- Owner cần chốt + tác động: (A) M05 không cần lưới thành viên → scope gọn;
  (B) cần lưới inline → thêm section mới ngoài manifest hiện tại.
- Task bị chặn: rebuild nguồn vốn M05; xác nhận phạm vi form trước P3.

### 6. PLI_M12 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `nguon_von_dieule_sau_thay_doi`,
  `tai_san_gop_von_sau_thay_doi_vdl`, `tai_san_gop_von_sau_thay_doi_von_dau_tu`,
  `co_cau_loai_co_phan_sau_thay_doi` (đều fixed-matrix missing_grid),
  `ndd_uy_quyen_sau_thay_doi` (nested-grid missing_grid, header nối 14 cột).
- Câu hỏi pháp lý (nguyên văn):
  1. Người đại diện theo ủy quyền sau thay đổi: dựng nested-grid 14 cột đúng
     header nối hay editable-grid phẳng? Row contract theo loại chủ sở hữu
     (TNHH/CTCP tổ chức nước ngoài)?
  2. Hai ngữ cảnh tài sản góp vốn (sau thay đổi vốn điều lệ vs vốn đầu tư):
     xác nhận tách semantic key + draft riêng, không đồng bộ data?
  3. Nguồn vốn điều lệ sau thay đổi: Tổng cộng/Tỷ lệ computed và đối chiếu vốn
     điều lệ sau thay đổi?
- Owner cần chốt + tác động: (1) nested vs phẳng → chọn component; (2) nếu tách
  key (manifest đã khai 2 semantic_key riêng) thì draft phải tách store theo ngữ cảnh;
  (3) khớp formula policy của PLI_M04.
- Task bị chặn: 4 fixed-matrix + 1 nested-grid của M12; phụ thuộc policy chốt ở M02/M04.

## Domain 2 — people-ownership (10 form)

### 7. PLII_M02 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `a4_tv_hgd_sau_thay_doi`, `c7_tv_hgd_cap_doi`
  (editable-grid missing_grid), `a7_thue_chi_tieu_cu_moi`, `c5_thue_chi_tieu_cap_doi`
  (fixed-matrix missing_grid). Evidence: paragraph dính
  "STTHọ tên…Chữ ký12345678910" (blocks B072/B137).
- Câu hỏi pháp lý (nguyên văn):
  1. Ba bảng ngành Mục A (bổ sung/bỏ/sửa) xác nhận dùng row contract `ds_nganh`
     với semantic key riêng như PLAN mục A, và bảng "sửa ngành chính" chỉ 3 cột
     không thêm cột?
  2. Bảng chỉ tiêu thuế cũ/mới Mục A: mẫu chỉ in sẵn "- Chỉ tiêu 5.1: Địa chỉ
     nhận thông báo thuế" + "-…." — tập chỉ tiêu cố định bắt buộc gồm những gì
     (có 5.2 tổng số lao động hay chỉ tiêu khác)?
  3. Dữ liệu Mục C (cấp đổi): ngành/thành viên/thuế kê khai độc lập hay đồng bộ
     từ đăng ký hiện tại của hộ?
- Owner cần chốt + tác động: (1) nếu YES khớp spec P1-C hiện có; (2) thiếu tập
  chỉ tiêu thì không dựng được fixed-matrix cũ/mới; (3) đồng bộ tự động bị PLAN
  cấm giữa loop khác nghĩa — nếu owner đòi đồng bộ phải thiết kế copy-tường-minh.
- Task bị chặn: rebuild 2 bảng thành viên HGD + 2 bảng thuế; P1-UI form-scoped meta.

### 8. PLII_M07 — BLOCKED_LEGAL_REVIEW

- Blocker: section `m7_danh_sach_thanh_vien_hgd` — "7. Danh sách thành viên hộ
  gia đình đăng ký thành lập hộ kinh doanh", editable-grid, missing_grid.
  Tập cột KHÁC `ds_tv_ho_gia_dinh` của M01/M02 (thêm Ghi chú, không ngày sinh/
  giới tính/dân tộc/chữ ký).
- Câu hỏi pháp lý (nguyên văn): "Bảng thành viên tại GCN (Mẫu 7) khác contract
  ds_tv_ho_gia_dinh của M01 (7 cột, có Ghi chú) — dựng loop/semantic key riêng
  hay map subset từ contract chung?"
- Owner cần chốt + tác động: (A) key riêng `ds_thanh_vien_hkd_gcn` (khớp notes
  census) / (B) subset contract chung → A an toàn đồng bộ; B rút gọn nhưng dễ
  sai ngữ cảnh.
- Task bị chặn: rebuild grid GCN Mẫu 7; GRID_META form-scoped.

### 9. PLI_M06 — BLOCKED_LEGAL_REVIEW (thành viên TNHH)

- Blocker: section `ds_thanh_vien_tnhh` — editable-grid, partial_columns.
  Loop cũ THIẾU cột 10 "Thời hạn góp vốn"; so header mẫu gốc (14 cột glued
  trong nguồn M09) còn thiếu Ghi chú và nhóm cột loại tài sản/số lượng/giá trị.
- Câu hỏi pháp lý (nguyên văn):
  1. Thành viên TNHH: giữ editable-grid phẳng đủ cột (bổ sung Thời hạn góp vốn/
     Ghi chú/Loại tài sản...) hay dựng nested-grid đúng mẫu gốc (cá nhân/tổ chức/
     người đại diện theo ủy quyền với tổng giá trị vốn được đại diện)?
  2. Cột Chữ ký xác nhận là outputOnly (không phải text input)?
- Owner cần chốt + tác động: (1) phẳng → nâng cấp cột nhanh; nested → đúng mẫu
  nhưng đụng component nested-grid chưa có; (2) nếu YES khớp GRID_META hiện tại.
- Task bị chặn: audit/nâng cấp loop cũ M06 (P3 people-ownership).

### 10. PLI_M07 — BLOCKED_LEGAL_REVIEW

- Blocker: section `ds_co_dong_sang_lap` — editable-grid, partial_columns.
  Loop cũ THIẾU cột 6 "Dân tộc"; so header mẫu gốc (19 cột glued trong M09)
  thiếu Loại cổ phần, nhóm tài sản góp vốn, Vốn góp, Thời hạn góp vốn…
- Câu hỏi pháp lý (nguyên văn): "Cổ đông sáng lập: nâng cấp lên nested-grid đúng
  mẫu gốc (19 cột, cá nhân/tổ chức/NĐD ủy quyền) hay giữ bảng phẳng và chỉ bổ
  sung cột Dân tộc? Cần quyết định trước khi rollout."
- Owner cần chốt + tác động: (A) nested 19 cột / (B) phẳng + Dân tộc → quyết định
  khối lượng P3 people-ownership và thứ tự so với fixture N1/N2.
- Task bị chặn: upgrade loop M07.

### 11. PLI_M08 — BLOCKED_LEGAL_REVIEW

- Blocker: section `ds_co_dong_nn` — editable-grid, partial_columns. Khớp 8/8 cột
  template hiện tại nhưng so header mẫu gốc (18 cột cá nhân + biến thể tổ chức +
  mục NĐD ủy quyền, glued trong M09): mất Vốn góp/loại cổ phần/loại tài sản.
- Câu hỏi pháp lý (nguyên văn): "Cổ đông NĐT nước ngoài: giữ bản phẳng 8 cột hiện
  tại hay dựng nested-grid đúng mẫu gốc (cá nhân/tổ chức, vốn góp, loại cổ phần,
  loại tài sản góp vốn)?"
- Owner cần chốt + tác động: giống M07; chọn lệch nhau giữa M07/M08 sẽ làm hai
  bảng cổ đông khác architecture.
- Task bị chặn: upgrade loop M08.

### 12. PLI_M09 — BLOCKED_LEGAL_REVIEW (+ source-contamination)

- Blocker: section `ds_thanh_vien_hop_danh` (editable-grid, partial_columns,
  THIẾU cột Thời hạn góp vốn) + section `vung_nhiem_mau_6789_10`
  (source-contamination, `app/templates/PLI_M09.docx#p103-p222`: toàn văn Mẫu 6,
  7, 8, Mẫu 9 lần 2 và Mẫu 10 nằm sau chân trang Mẫu 9 thật).
- Câu hỏi pháp lý (nguyên văn):
  1. Xác định phạm vi pháp lý thật của Mẫu 9: vùng Mẫu 6/7/8/9(lần 2)/10 trong
     template+nguồn PLI_M09 là dư thừa do tách nguồn sai - được phép loại khỏi
     template khi rebuild?
  2. Nếu bản Mẫu 9 thứ hai (header 14 cột đầy đủ) mới là cấu trúc đúng: chọn nó
     thay TBL[0] phẳng hiện tại hay giữ phẳng?
- Owner cần chốt + tác động: (1A) được phép xóa vùng nhiễm → dọn template;
  (1B) phải giữ nguyên vẹn → chỉ đánh dấu output; (2) chọn bản 14 cột → rebuild
  lớn hơn nhưng đúng luật.
- Task bị chặn: decontamination M09 + rebuild thành viên hợp danh; các quyết định
  M06–M08 phụ thuộc cấu trúc thật của header glued nằm TRONG file M09 này.

### 13. PLI_M10 — BLOCKED_LEGAL_REVIEW

- Blocker: section `ds_cshhl_doanh_nghiep` — editable-grid, partial_columns.
  Loop đủ 10/10 cột dữ liệu template hiện tại; so header mẫu gốc 12 cột còn
  thiếu nhóm "Chủ sở hữu hưởng lợi được xác định…" (quyền chi phối).
- Câu hỏi pháp lý (nguyên văn): "Quyền chi phối của CSHHL (điểm b khoản 1 Điều 17
  NĐ 168/2025, chân trang 4 mẫu): là cột riêng trong bảng hay ghi vào cột Ghi chú?"
- Owner cần chốt + tác động: (A) cột riêng / (B) ghi chú → A thêm column tag +
  migration draft; B giữ schema.
- Task bị chặn: upgrade loop M10/M11 (hợp nhất biến thể cá nhân/tổ chức).

### 14. PLI_M13 — BLOCKED_LEGAL_REVIEW

- Blocker: section `ndd_pl_sau_thay_doi` — editable-grid, missing_grid.
  Evidence: chân trang 2 nguồn "Ghi thông tin của tất cả người đại diện theo
  pháp luật… nhiều hơn 01 người". Blocks chỉ có 1 bộ field ndd.*.
- Câu hỏi pháp lý (nguyên văn): "Chân trang mẫu cho phép nhiều NĐDPL trong 1 giấy
  đề nghị: cần dựng editable-grid danh sách NĐDPL hay giữ 1 bộ field và bắt nộp
  nhiều hồ sơ?"
- Owner cần chốt + tác động: (A) grid nhiều dòng / (B) 1 bộ field + nhiều hồ sơ
  → quyết định fixture E3-style cho nhóm NĐDPL; B đơn giản UI nhưng phiền người dùng.
- Task bị chặn: rebuild grid M13.

### 15. PLI_M15 — BLOCKED_LEGAL_REVIEW

- Blocker: section `ndd_pl_uy_quyen_chu_so_huu_moi` — nested-grid, missing_grid,
  header nối 1 paragraph (`...docx#p50`).
- Câu hỏi pháp lý (nguyên văn):
  1. Cột bắt buộc khác nhau giữa NĐDPL (không kê khai phần ủy quyền) và người đại
     diện theo ủy quyền (có tỷ lệ %): row contract phân biệt theo loại như thế nào?
  2. Số dòng tối thiểu/tối đa của danh sách trong 1 giấy đề nghị?
- Owner cần chốt + tác động: cùng chủ đề discriminator với PLI_M02 (nên chốt
  MỘT policy chung); min/max dòng → tham số min_rows/max_rows.
- Task bị chặn: rebuild nested M15 (backlog N-group).

### 16. PLI_M72 — BLOCKED_LEGAL_REVIEW

- Blocker: 4 section nested-grid `thanh_vien_tnhhh_hai_tv_tro_len`,
  `co_dong_sang_lap_cp`, `co_dong_nuoc_ngoai_cp`, `thanh_vien_hop_danh`
  (missing_grid; evidence p1796-p1823, p1751-p1755, p1876-p1889). 5 lưới ngành
  occurrence ĐÃ integrate P1.
- Câu hỏi pháp lý (nguyên văn):
  1. M72 gồm 5 phần theo loại hình DN: render chỉ phần được chọn (PLAN yêu cầu)
     thì 4 bảng ngành + 4 danh sách thành viên/cổ đông cần loop riêng cho từng
     phần hay engine render lặp 1 spec theo section active?
  2. Key trùng giữa các phần (`dn.ten_tieng_viet`, `ndd.*` xuất hiện nhiều lần)
     — cần namespacing theo loại hình trước khi thêm grid?
  3. Cột "Giá trị cổ phần" có quy đổi ngoại tệ — computed totals đối chiếu vốn
     điều lệ như PLAN mục B/C?
- Owner cần chốt + tác động: (1)+(2) namespacing/policy render là tiền điều kiện
  fixture N2; (3) khớp formula policy capital-assets.
- Task bị chặn: 4 nested-grid M72; P3 people-ownership; visual QA mọi nested grid.

## Domain 3 — tax (4 form)

### 17. PLI_M17 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `thue_chi_tieu_6_1_8` (fixed-matrix, partial_columns — thiếu
  4 hình thức hạch toán, BOT, GTGT), `lua_chon_khu_cn_cxc_kt_kccn`,
  `phuong_thuc_dong_bhxh` (missing_grid).
- Câu hỏi pháp lý (nguyên văn):
  1. Các nhóm checkbox chọn-1 (hạch toán, thuế GTGT, BHXH, khu) nên dựng
     fixed-matrix radio hay giữ chk độc lập? Điều kiện nghiệp vụ BHXH (ngành
     nông-lâm-ngư-diêm phải trả lương theo sản phẩm) có cần validation chéo?
  2. Chỉ tiêu 8 CTCK nước ngoài (mục 8) đã có chk_ctck + gp_ucsn_so — xác nhận
     đây là mục riêng ngoài bảng thuế?
- Owner cần chốt + tác động: (1) radio chọn-1 → pattern dùng chung cho
  M17/M19/M23/M25; validation chéo BHXH là cross-field rule mới; (2) phạm vi bảng thuế.
- Task bị chặn: bổ sung chỉ tiêu thuế M17; P3 tax-grids.

### 18. PLI_M19 — BLOCKED_LEGAL_REVIEW

- Blocker: section `thue_thay_doi_A` — fixed-matrix, partial_columns (7 chỉ tiêu;
  thiếu hình thức hạch toán + dự án BOT/BTO/BT/BOO/BLT/BTL/O&M).
- Câu hỏi pháp lý (nguyên văn): "Nhóm checkbox hạch toán/BOT thiếu hoàn toàn trong
  blocks — dựng fixed-matrix chung kiểu 'chỉ tiêu thuế' cho M17/M19/M23/M25?"
- Owner cần chốt + tác động: nếu YES → một spec pattern chung, giảm 4 lần làm
  riêng; nếu NO phải spec từng mẫu.
- Task bị chặn: rebuild chỉ tiêu thuế M19 (P3 tax-grids).

### 19. PLI_M23 — BLOCKED_LEGAL_REVIEW

- Blocker: section `thue_chi_tieu_6_1_6` — fixed-matrix, partial_columns (6 chỉ
  tiêu; thiếu hạch toán, BOT, GTGT). Defect `pli_m23_heading_numbering`: fragment
  ghi heading '6.' nhưng template thật là '7.' (sai đánh số, không đổi bản chất).
- Câu hỏi pháp lý (nguyên văn): "Như M19: thiếu nhóm checkbox hạch toán/BOT/GTGT
  — cần spec fixed-matrix dùng chung."
- Owner cần chốt + tác động: gộp vào quyết định M19; defect numbering sửa khi rebuild.
- Task bị chặn: rebuild chỉ tiêu thuế M23.

### 20. PLI_M25 — BLOCKED_LEGAL_REVIEW

- Blocker: section `thue_chi_tieu_6_1_6_ctck` — fixed-matrix, partial_columns
  (6 chỉ tiêu, cấu trúc giống M23; thiếu hạch toán, BOT, GTGT).
- Câu hỏi pháp lý (nguyên văn): "Như M19/M23."
- Owner cần chốt + tác động: theo quyết định chung nhóm CTCK/chỉ tiêu thuế.
- Task bị chặn: rebuild chỉ tiêu thuế M25.

## Domain 4 — branches/admin/products (13 form)

### 21. PLI_M27 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `danh_sach_ndd_pl_thong_bao` (editable-grid missing_grid,
  nguồn liệt kê "1. Họ tên… 2. Họ tên…") + `don_vi_tam_ngung_tiep_tuc`
  (editable-grid missing_grid, 6 khối CN/VPĐD/ĐĐKD × tạm ngừng/tiếp tục).
- Câu hỏi pháp lý (nguyên văn):
  1. Một thông báo M27 có được phép tạm ngừng/tiếp tục nhiều đơn vị cùng lúc
     không, hay mỗi đơn vị một thông báo riêng (giấy gốc trình bày dạng đơn khối)?
  2. Số lượng NĐDPL liệt kê ở mục 1.a tối đa bao nhiêu dòng?
- Owner cần chốt + tác động: (1) nhiều đơn vị/giấy → grid; một/giấy → scalar-fields
  (tiền lệ M28/M55); (2) maxRows.
- Task bị chặn: rebuild 2 grid M27 (P3 branches).

### 22. PLI_M52 — BLOCKED_LEGAL_REVIEW

- Blocker: section `khung_ra_soat_4_nhom` — "Rà soát 4 nhóm: doanh nghiệp /
  chi nhánh / VPĐD / địa điểm", fixed-matrix, partial_columns. Notes: key
  `ma_so_van_ban` tái sử dụng làm mã số của cả 3 nhóm (nhiễu ngữ nghĩa);
  nhóm DN thiếu field người đại diện.
- Câu hỏi pháp lý (nguyên văn):
  1. Key `ma_so_van_ban` dùng chung cho MSDN/mã số của 3 nhóm — cần tách key
     riêng từng nhóm trước khi dựng grid không?
  2. Mẫu do CQĐKKD phát hành để DN phản hồi: chủ thể nhập 4 nhóm này là doanh
     nghiệp đúng không?
- Owner cần chốt + tác động: (1) tách key → migration draft bắt buộc; (2) nếu DN
  là chủ thể nhập thì fixed-matrix partial phải bổ sung đủ field.
- Task bị chặn: rebuild khung rà soát M52.

### 23. PLI_M56 — BLOCKED_LEGAL_REVIEW

- Blocker: section `cn_vppd_ddkd_tiep_tuc_truoc_han` — editable-grid,
  missing_grid ("một hoặc một số" nhưng chỉ 1 bộ field; `ma_so_van_ban` mang
  ngữ nghĩa mã số đơn vị).
- Câu hỏi pháp lý (nguyên văn): "Trường hợp 'một hoặc một số đơn vị': cần grid
  nhiều dòng cho giấy xác nhận do CQĐKKD lập? Key ma_so_van_ban cần đổi tên đúng
  ngữ nghĩa?"
- Owner cần chốt + tác động: grid vs field đơn; rename key → draft migration.
- Task bị chặn: rebuild grid M56.

### 24. PLI_M63 — BLOCKED_LEGAL_REVIEW

- Blocker: section `dia_diem_truc_thuoc_bi_thu_hoi` (editable-grid missing_grid)
  + `noi_dung_quyet_dinh_thu_hoi` (output-table, quyết định do TRƯỞNG CQĐKKD ban
  hành, 2 biến thể Điều 2–4).
- Câu hỏi pháp lý (nguyên văn):
  1. M63 là quyết định hành chính do CQĐKKD ban hành — app ĐKKD cho doanh nghiệp
     kê khai thì section nào thuộc thẩm quyền nhập của DN, phần nào chỉ là output
     khi tích hợp hệ thống cơ quan?
  2. Biến thể Điều 2/3/4 theo 2 trường hợp thu hồi: render có điều kiện theo
     trường hợp nào?
- Owner cần chốt + tác động: (1) phân định input/output → activeWhen của
  output-table O3; (2) điều kiện render.
- Task bị chặn: rebuild grid ĐĐKD bị thu hồi; render quyết định có điều kiện.

### 25. PLI_M66 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `don_vi_dang_lam_thu_tuc_cham_dut`, `ddkd_truc_thuoc_dang_cham_dut`
  (editable-grid missing_grid) + `thong_bao_cqb` (output-table). Defect
  `pli_m66_bo_ten_ma_x23`: note '1 bộ tên+mã' thực tế lặp ×2/×3; cần tách section.
- Câu hỏi pháp lý (nguyên văn):
  1. M66 do CQĐKKD phát hành: ai là chủ thể kê khai trong app (DN xem/output hay
     cán bộ nhập)? Nếu output-only vẫn phải giữ grid khi xuất DOCX theo PLAN mục G.
  2. Số dòng tối đa của 2 danh sách đơn vị/địa điểm trực thuộc?
- Owner cần chốt + tác động: chủ thể nhập quyết định kind cuối cùng; maxRows tham số.
- Task bị chặn: tách section + rebuild 2 grid M66.

### 26. PLI_M67 — BLOCKED_LEGAL_REVIEW

- Blocker: section `don_vi_cham_dut_sau_day` — editable-grid, missing_grid.
  "(các)" gợi ý nhiều đơn vị nhưng blocks chỉ 1 bộ tên/mã/địa chỉ (lặp 2 lần).
- Câu hỏi pháp lý (nguyên văn): "'(các) chi nhánh... sau đây': một thông báo M67
  liệt kê được nhiều đơn vị không?"
- Owner cần chốt + tác động: 1-nhiều → grid; nếu một/giấy chuyển scalar-fields.
- Task bị chặn: rebuild grid M67.

### 27. PLI_M68 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `don_vi_cham_dut_khi_doanh_nghiep_giai_the` (editable-grid
  missing_grid) + `thong_bao_dang_giai_the` (output-table CQB).
- Câu hỏi pháp lý (nguyên văn): "Danh sách đơn vị chấm dứt khi giải thể: chủ thể
  nhập và giới hạn số dòng? Phần còn lại của biểu là output của cơ quan?"
- Owner cần chốt + tác động: như M66/M67 — chủ thể nhập + maxRows.
- Task bị chặn: rebuild grid M68; output-table O5.

### 28. PLI_M70 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `ho_so_bao_gom` (fixed-matrix missing_grid, 3 dòng đánh số cố
  định trên giấy, không header/STT-header) + `chu_ky_nguoi_nop_nguoi_nhan`
  (output-table). File nguồn trùng tại 05_cong_bo (bản 03 thắng).
- Câu hỏi pháp lý (nguyên văn):
  1. "Hồ sơ bao gồm:" cố định 3 dòng hay cho phép n tài liệu (một số hồ sơ có >3
     tài liệu đính kèm)?
  2. Ô NGƯỜI NỘP/NGƯỜI NHẬN xử lý outputOnly đúng theo PLAN mục C/G?
- Owner cần chốt + tác động: (1) cố định 3 → fixed-matrix; n tài liệu → editable-grid
  (min/max dòng); (2) nếu YES khớp fixture O1.
- Task bị chặn: rebuild danh sách hồ sơ M70; fixture O1.

### 29. PLI_M71 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `ho_so_bao_gom_online` (fixed-matrix missing_grid, bản điện tử)
  + `chu_ky_co_quan_cap_tinh` (output-table, chỉ chữ ký cơ quan).
- Câu hỏi pháp lý (nguyên văn): "Như M70: số dòng tài liệu cố định hay biến thiên?"
- Owner cần chốt + tác động: theo quyết định M70 (nên chốt chung một policy).
- Task bị chặn: rebuild M71; fixture O2.

### 30. PLI_M75 — BLOCKED_LEGAL_REVIEW

- Blocker: sections `cn_vppd_ddkd_khoi_phuc`, `ddkd_truc_thuoc_khoi_phuc`
  (editable-grid missing_grid; 3 dòng theo loại đơn vị CN/VPĐD/ĐĐKD) +
  `thong_bao_khoi_phuc_gcn` (output-table).
- Câu hỏi pháp lý (nguyên văn): "3 dòng đơn vị theo loại (CN/VPĐD/ĐĐKD):
  fixed-matrix 3 hàng hay editable-grid tự do? Chủ thể kê khai (CQB vs DN)?"
- Owner cần chốt + tác động: fixed-matrix 3 hàng khóa loại đơn vị; editable tự do
  linh hoạt hơn nhưng lệch trình bày giấy.
- Task bị chặn: rebuild 2 grid M75; output-table O6.

### 31. PLI_M78 — BLOCKED_LEGAL_REVIEW

- Blocker: section `san_pham_cung_cap_thong_tin` — "STT | Tên sản phẩm | Số lượng",
  fixed-matrix, missing_grid (PLAN mục F; 4 hàng quy định: 1 GCNĐKDN của…,
  2 lịch sử 3 năm, 3 thông tin DN mới nhất, 4 Sản phẩm khác). Blocks không có key
  nào cho sản phẩm/số lượng.
- Câu hỏi pháp lý (nguyên văn):
  1. Số lượng sản phẩm: integer >=0, giới hạn tối đa? Hàng 4 "Sản phẩm khác" bắt
     buộc nhập tên SP chi tiết khi SL > 0?
  2. Cột "Tên sản phẩm" các hàng 1-3 có placeholder tên DN điền vào ("của …") —
     canonical key cho tên DN trong từng hàng?
- Owner cần chốt + tác động: hybrid fixed + editable detail (PLAN F) hay thuần
  fixed; cross-field rule "SP khác bắt buộc mô tả khi SL>0".
- Task bị chặn: rebuild bảng sản phẩm M78 (P3 products).

### 32. PLI_M79 — BLOCKED_LEGAL_REVIEW

- Blocker: section `tai_lieu_kem_theo_de_nghi` — editable-grid, missing_grid
  (3 dòng đánh số + dấu "…" → số dòng biến thiên).
- Câu hỏi pháp lý (nguyên văn): "Số lượng tài liệu kèm theo: min/max? Cần upload
  file kèm mỗi dòng không (ngoài scope census)?"
- Owner cần chốt + tác động: min/max → tham số fixture E3; upload file là scope
  mới nếu owner yêu cầu (cần Lead duyệt scope).
- Task bị chặn: rebuild grid M79 (fixture E3).

### 33. PLI_M80 — BLOCKED_LEGAL_REVIEW

- Blocker: section `tai_lieu_kem_theo_thu_hoi` — editable-grid, missing_grid
  (giống M79).
- Câu hỏi pháp lý (nguyên văn): "Như M79: min/max dòng tài liệu kèm theo."
- Owner cần chốt + tác động: theo quyết định M79.
- Task bị chặn: rebuild grid M80.

---

## Thống kê cuối

| Mục | Giá trị |
|---|---|
| Tổng entry BLOCKED_LEGAL_REVIEW | 33 |
| capital-assets | 6 (PLI_M01, M02, M03, M04, M05, M12) |
| people-ownership | 10 (PLII_M02, PLII_M07, PLI_M06, M07, M08, M09, M10, M13, M15, M72) |
| tax | 4 (PLI_M17, M19, M23, M25) |
| branches/admin/products | 13 (PLI_M27, M52, M56, M63, M66, M67, M68, M70, M71, M75, M78, M79, M80) |
| Form CÓ legal_questions | 33/33 |
| Form KHÔNG legal_questions mà vẫn BLOCKED | **0 — danh sách rỗng**, không cần Lead bổ sung evidence |
| Form có defects kèm theo | 2 (PLI_M23 heading numbering; PLI_M66 lặp tên+mã ×2/×3) |
| Section blocker theo kind (ước tính từ entries trên) | editable-grid ~14 · fixed-matrix ~15 · nested-grid 7 · output-table 6 |

Lưu ý cho Lead: các quyết định có tính lan tỏa nên trả lời theo cụm —
(a) policy totals/computed (M02/M04/M12/M72), (b) row-type discriminator
NĐDPL/ủy quyền (M02/M13/M15), (c) fixed-matrix radio chọn-1 nhóm chỉ tiêu thuế
(M17/M19/M23/M25), (d) một-giấy-nhiều-đơn vị (M27/M56/M66/M67/M68/M75),
(e) phạm vi nguồn M03/M04/M05/M09.
