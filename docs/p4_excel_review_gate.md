# P4 — Review Gate Excel (báo cáo chờ quyết định owner)

> Trạng thái: **CHỜ OWNER**. P4 là cổng review, KHÔNG implement — X1–X6 chỉ
> chạy sau lệnh rõ `Bắt đầu Excel`; nếu `Để sau` thì Excel không chặn
> `CORE_APP_DONE` (PLAN mục 4/5-P4). Số liệu dưới đây đo trực tiếp từ
> `app/data/form_maps.json` + `app/data/table_specs/manifest.json` +
> `app_web/ui/form-domain.js` tại HEAD `78a0b0f` (ngày 2026-08-28), probe
> openpyxl chạy thật trong sandbox.

## 1. P4.1 — Kết quả đối chiếu data-key với canonical keys/form_maps

Tổng cộng **381 scalar key** (243 có prefix kiểu `dn.*`, 138 flat) + **20 loop
canonical** + section_specs cho 4 kind bảng.

### 1a. Vùng ỔN ĐỊNH — map questionnaire được ngay

| Vùng | Key đại diện | Bằng chứng ổn định |
|---|---|---|
| Định danh DN | `dn.ten_tieng_viet`, `dn.ten_nuoc_ngoai`, `dn.ten_viet_tat`, `dn.ma_so_dn`, `dn.dia_chi_tru_so` | Nhóm `dn.*` dùng chéo nhiều mẫu (39–41+), không có tiền lệ rename |
| Ngành (mọi biến thể) | cột `ten_nganh` / `ma_nganh` / `la_nganh_chinh` trên 5 loop `ds_nganh_<variant>` của PLI_M72, sync_group `ds_nganh_pli_m72` | D2.9-A + D-M72-ACT (Option D) DECIDED; selector `dn.loai_hinh` đã wire runtime; D7.3-A ngành bắt buộc ≥1 |
| Vốn | `von_dau_tu_so` (dntn) · `von_dieu_le` (tnhh/ctcp/dhdn) · `menh_gia_co_phan`, `tong_so_co_phan` (ctcp) | Key scalar trong M72, không trùng ngữ nghĩa; nguồn vốn chi tiết DECIDED qua M02 (D1.1=A) |
| Người đứng đầu | `ho_ten_in_hoa` + `chu_hkd.*` (dntn) · `to_chuc.ten` (tnhh_1tv) · `ndd.*` (tnhh_2tv/ctcp/dhdn, có `chuc_vu`) | Key variant-scoped rõ ràng trong M72; không đụng vùng blocked |
| Lưới người DECIDED | `ds_thanh_vien_tnhh` (M06), `ds_co_dong_sang_lap` (M07), `ds_co_dong_nn` (M08), `ds_cshhl` (M10), `ds_tv_ho_gia_dinh` (PLII_M07) | Cột chuẩn `ho_ten/ngay_sinh/quoc_tich/dia_chi/ty_le…` đã khóa qua P2 (D2.x) |
| Khối ký dùng chung | `dia_diem_ky`, `ngay_ky_vb`, `thang_ky_vb`, `nam_ky_vb` (74–75 mẫu) | Ổn định tuyệt đối — nhưng **app tự sinh được nên KHÔNG hỏi khách** (PLAN 4.2) |

### 1b. Vùng ĐANG TRÔI — xử lý/tránh trước khi map

1. **`ma_so_van_ban` (PLI_M52)** — 1 key mang 3 ngữ nghĩa (MSDN/mã CN/mã VPĐD).
   D4.2-A đã chốt tách key + migration nhưng **CHƯA làm** → cấm map câu hỏi
   vào key này.
2. **`ds_thanh_vien` (PLI_M09)** — D3.2-A sẽ thay bằng bản 14 cột khi có bản
   gốc → cột thành viên hợp danh **sẽ đổi** → không map câu hỏi thành viên
   hợp danh tới khi rebuild xong.
3. **M03/M04/M05** — chờ bản gốc (D3.3/D1.3/D1.5); câu hỏi vốn của các mẫu này
   lấy theo M02 (nguồn vốn DECIDED), không map theo matrix hiện tại.
4. **138 key flat vs 243 prefixed** — cùng ngữ nghĩa nhưng shape khác giữa các
   mẫu (vd `fax` flat 57 mẫu, trong khi định danh DN là `dn.*`) → questionnaire
   **bắt buộc map per-procedure** `question_id → {docId, key}`, tái sử dụng
   pattern form-scoped resolver (tiền lệ `getGridMeta`), không map key toàn cục.
5. **Ngày sinh tách 3 key** (`ngay_sinh`/`thang_sinh`/`nam_sinh`) — 1 câu hỏi
   điền 3 key; E2 (chuẩn hóa ngày) phải chốt trước khi sinh mapping.
6. **58 label trùng → nhiều key** — đa số là namespacing per-loop hợp lệ
   (D2.9), không phải lỗi; nhưng nguyên tắc mapping theo `(docId, loop)` chứ
   không theo label hiển thị.

### 1c. Vùng BỊ CHẶN — không hỏi khách được (blocker pháp lý giữ nguyên)

Thuế PLII_M02 (D5.2) · member grids PLII_M02 (ghim occurrence) · M72 N2–N5
thành viên/cổ đông 4 bảng · N-tail groups (Tổng giá trị/Thời điểm) · 2 nhóm cột
cuối N1/N6/N7. Census: 33 `missing_grid` + 1 `partial` + 5 `partial_columns` +
1 `contaminated` — các vùng này không có câu hỏi Excel trong phiên đầu.

## 2. P4.2 — Thủ tục ưu tiên + cụm câu hỏi đầu (draft chờ duyệt — E6)

**Khuyến nghị cụm đầu: "Thành lập doanh nghiệp" qua PLI_M72** — 1 thủ tục phủ
cả 5 biến thể (`dntn/tnhh_1tv/tnhh_2tv/ctcp/dhdn`) nhờ selector `dn.loai_hinh`
(Option D đã DECIDED + đã wire runtime). Toàn bộ key liên quan thuộc vùng ổn
định (1a). Phủ tiếp theo (theo sau): hộ kinh doanh (PLII_M01, 45 fields),
thay đổi ngành (PLI_M02/M12). Thuế để sau (D5.2 blocked).

Draft bộ câu hỏi v1 (nhóm đời thường, mỗi câu 1 ý, có ví dụ điền mờ; câu
loại hình quyết định variant → các câu theo variant chỉ bật khi được chọn):

**Nhóm "Về doanh nghiệp bạn muốn thành lập"**
1. "Bạn muốn thành lập loại hình nào?" — dropdown: DN tư nhân / TNHH 1 TV /
   TNHH 2 TV trở lên / Công ty cổ phần / Công ty hợp danh → `dn.loai_hinh`
2. "Bạn muốn đặt tên công ty là gì? (tiếng Việt)" → `dn.ten_tieng_viet`
   (ví dụ: Công ty TNHH Minh Long)
3. "Có tên tiếng nước ngoài không? (bỏ trống nếu không có)" → `dn.ten_nuoc_ngoai`
4. "Cần tên viết tắt không?" → `dn.ten_viet_tat` (ví dụ: ML)
5. "Đã có mã số doanh nghiệp chưa? (bỏ trống nếu đăng ký mới)" → `dn.ma_so_dn`
6. "Trụ sở chính ở đâu? (số nhà, đường, phường/xã, quận/huyện, tỉnh/thành)" →
   `dn.dia_chi_tru_so`
7. "Số điện thoại liên hệ?" → `dien_thoai_khac` · 8. "Email?" → `email_khac`
   (website/fax: hỏi tuỳ chọn hoặc bỏ — khuyến nghị bỏ để gọn)

**Nhóm "Về ngành nghề kinh doanh"** (lặp được, ≥1 dòng — D7.3-A)
9. "Bạn kinh doanh ngành nào? Ghi tên ngành, ví dụ: Bán lẻ hàng điện tử" →
   `<loop-variant>.ten_nganh`; app tra VSIC gợi ý mã → `ma_nganh` (chờ E3)
10. "Đây có phải ngành nghề chính không?" → `la_nganh_chinh` (đúng 1 dòng)

**Nhóm "Về vốn"** (bật theo loại hình)
11. dntn: "Bạn dự kiến đầu tư bao nhiêu vốn (VNĐ)?" → `von_dau_tu_so`
12. tnhh/ctcp/dhdn: "Vốn điều lệ là bao nhiêu (VNĐ)?" → `von_dieu_le`
13. ctcp: "Mệnh giá một cổ phần (VNĐ)?" → `menh_gia_co_phan` (mặc định 10.000)
    · 14. "Tổng số cổ phần chào bán?" → `tong_so_co_phan`
    ⚠ Giới hạn ghi rõ: chi tiết vốn góp từng thành viên (N2–N5) đang blocked
    → phiên đầu KHÔNG hỏi, chỉ hỏi tổng.

**Nhóm "Về người đứng đầu / người đại diện"** (bật theo loại hình)
15. dntn: "Chủ doanh nghiệp họ và tên? (sẽ in hoa trên văn bản)" →
    `ho_ten_in_hoa` · 16. "Giới tính?" → `chu_hkd.gioi_tinh`
17. "Ngày, tháng, năm sinh? (dd/mm/yyyy)" → `ngay_sinh` + `thang_sinh` +
    `nam_sinh` (1 câu điền 3 key — chờ E2 chốt format)
18. "Quốc tịch?" → `chu_hkd.quoc_tich` · 19. "Số CCCD?" → `chu_hkd.so_cccd`
20. "CCCD ngày cấp / nơi cấp?" → `ngay_cap` + `noi_cap`
21. "Địa chỉ liên lạc (chỗ ở hiện tại)?" → `dia_chi_lien_lac`
22. tnhh_1tv: "Tên tổ chức chủ sở hữu (in hoa)?" → `to_chuc.ten`
23. tnhh_2tv/ctcp/dhdn: "Người đại diện theo pháp luật họ tên?" → `ndd.ho_ten`
    · "Chức danh?" → `ndd.chuc_vu` (Tổng giám đốc / Giám đốc / Trưởng ban…)
    (các câu 16–21 ứng với `ndd.*` khi không phải dntn)

**KHÔNG hỏi** (app tự sinh theo PLAN 4.2): ngày nộp (`dia_diem_ky`,
`ngay_ky_vb/thang_ky_vb/nam_ky_vb` = ngày tạo phiếu), nơi đăng ký
(`co_quan_dkkd` suy từ tỉnh/thành trụ sở — owner xác nhận luật ánh xạ).

## 3. P4.3 — Dependency check (bằng chứng chạy thật)

| Hạng mục | Kết quả |
|---|---|
| openpyxl | Máy dev có **3.1.5**, **chưa pin** trong `requirements-dev.txt` → khi mở X2 pin chính xác (thêm vào file, kèm ghi chú máy sạch P6) |
| Protection (khóa ô ngoài vùng điền) | ✅ probe: `ws.protection.sheet=True`, ô điền `locked=False` — giữ nguyên sau round-trip |
| Dropdown chọn-là-chọn | ✅ probe: `DataValidation(type="list", formula1="Công ty TNHH,Doanh nghiệp tư nhân,…")` — Unicode tiếng Việt OK |
| Round-trip | ✅ probe: ghi → đọc lại `B2` nguyên giá trị tiếng Việt |
| File dialog trên pywebview | ✅ khả thi — pattern `tkinter.filedialog` (`askopenfilename`/`asksaveasfilename`) đã dùng cho mở/lưu draft JSON (`app_web/main.py:139–166`); nạp/xuất phiếu Excel đi cùng pattern; smoke Windows đã có S4–S5 trong `docs/platform_smoke_checklist.md` (mở rộng cho Excel khi mở X5) |
| Máy sạch (P6) | openpyxl thuần Python → pin version + test máy sạch như kế hoạch; không dependency hệ thống |

## 4. P4.4 — Effort / rủi ro (khi được lệnh `Bắt đầu Excel`)

| Wave | Nội dung chính | Effort ước tính* | Gate |
|---|---|---|---|
| X1 | Schema questionnaire + builder sinh khung từ form_maps/registry + nội dung cụm đầu (mục 2) | 2–3 phiên + 1 vòng duyệt owner | khung khớp 100% data-key registry; question thiếu data-key = fail build |
| X2 | Xuất .xlsx (protection, styling, dropdown, sheet hướng dẫn) | 2–3 phiên | mở đa ứng dụng; protection bật; 0 ô data ngoài vùng locked |
| X3 | Nạp .xlsx fail-loud + dịch question→key + validator chuẩn | 2 phiên | sai khung báo lỗi rõ; không ghi đè draft khi fail |
| X4 | Round-trip + negative (2 suite đăng ký runner) | 1–2 phiên | 2 suite xanh trong release runner |
| X5 | UI 2 nút + bridge (Xuất phiếu / Nạp phiếu) | 1–2 phiên | E2E chọn→xuất→nạp→draft đúng |
| X6 | Visual + máy sạch + duyệt hình | 1 phiên | owner duyệt ảnh phiếu |

\* phiên = ca làm việc Lead (sub-agent lane khi tách được file); mỗi wave kết
thúc commit sạch.

**Rủi ro & giảm thiểu** (bảng PLAN 4.5 + bổ sung từ P4.1): câu hỏi lệch nghĩa
pháp lý → owner duyệt từng cụm + gắn version; key trôi → cụm đầu chỉ dùng vùng
ổn định 1a, mapping per-procedure; mẫu giấy đổi → regen questionnaire đi cùng
regen template, diff review như generated artifact; máy khách không Excel →
nạp bằng openpyxl; họ sơ cần chuẩn bị (`ho_so_bao_gom`) cho cụm đầu chưa DECIDED
→ soạn tĩnh theo luật + owner duyệt nội dung trước khi in vào phiếu (X2).

## 5. Câu hỏi owner trả khi MỞ (E1–E6 — kèm khuyến nghị Lead)

| # | Câu hỏi | Khuyến nghị Lead |
|---|---|---|
| E1 | Xuất theo 1 thủ tục — có kèm biến thể gì không? | 1 questionnaire/thủ tục; câu loại hình quyết định variant M72; câu riêng biến thể bật theo lựa chọn |
| E2 | Chuẩn hóa dữ liệu khách (hoa/thường, ngày `01/02/2026`, tiền có dấu chấm)? | trim; tên giữ nguyên người gõ, trường "in hoa" do app tự upper; ngày `dd/mm/yyyy` → tách `ngay/thang/nam_sinh`; tiền bỏ dấu chấm nghìn trước khi ghi key |
| E3 | Ngành: khách ghi tên tự do → app tra VSIC → ai chốt? | app gợi ý top-3 mã VSIC, owner chọn lúc nạp phiếu; khách không cần biết mã |
| E4 | "Danh sách còn thiếu" dùng panel lỗi hay checklist riêng? | dùng panel lỗi hiện có (validator chuẩn); ô vàng còn trống trong phiếu = còn thiếu, nhóm theo nhóm câu |
| E5 | Có cần xuất ngược hồ sơ đã điền ra Excel để khách xác nhận? | ĐỂ SAU — không nằm trong X1–X6 |
| E6 | Cụm đầu ai soạn? | Lead đã soạn nháp (mục 2) — owner duyệt/sửa; cụm sau lặp quy trình |

**Lệnh cần owner:** `Bắt đầu Excel` (chạy X1→X6 theo wave, mỗi wave commit
sạch) **hoặc** `Để sau` (Excel không chặn `CORE_APP_DONE`, ghi backlog).

## 6. Customer export mode (owner chốt 2026-09-15, wave P0)

Hai chế độ xuất workbook case-level qua `export_mode`:

| Mode | Đối tượng | AUTH_* | Nội dung |
|---|---|---|---|
| `full` (mặc định) | Nội bộ | Có | Toàn bộ câu như hiện tại |
| `customer` | Khách | Không | Một sheet ``Phiếu_khách`` (hàng 1 tiêu đề, câu hỏi từ hàng 2); đủ câu khách trừ ``audience=staff``; wizard select thay mark nội bộ; ``__map``/``__lists`` veryHidden |

Metadata câu hỏi tùy chọn: `audience` (`customer`|`staff`), `tier`
(`core`|`conditional`|`rare`|`wizard`), `wizard: true`, `wizard_sets` trên
option select. Pilot: `thanh_lap_tnhh_1tv`, `dang_ky_ho_kinh_doanh_lan_dau`.
Contract `__map`/checksum giữ nguyên — mọi ô vàng xuất ra vẫn có dòng map.
