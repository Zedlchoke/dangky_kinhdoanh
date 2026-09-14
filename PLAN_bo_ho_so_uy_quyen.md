# Kế hoạch bộ hồ sơ ủy quyền cho dịch vụ đăng ký kinh doanh

## 0. Mục tiêu và cách hiểu thống nhất

Bạn là đơn vị dịch vụ đăng ký kinh doanh. Hồ sơ doanh nghiệp/hộ kinh doanh là dữ liệu đang khai. Ở cột bên phải người dùng chọn **người trực tiếp làm thủ tục được ủy quyền** (ví dụ profile Minh Long); phần mềm lấy thông tin Minh Long từ profile, áp dụng đúng tư cách/loại người và thủ tục, rồi sinh bộ văn bản ủy quyền để doanh nghiệp ký.

**Phạm vi giai đoạn đầu chỉ là ủy quyền thực hiện thủ tục đăng ký doanh nghiệp/hộ kinh doanh cho đơn vị dịch vụ.** Không triển khai các loại ủy quyền quản trị vốn/cổ đông trong cùng luồng.

Các loại “người đại diện theo ủy quyền của chủ sở hữu/thành viên” và “thành viên hộ gia đình ủy quyền cho chủ hộ” đã có thể xuất hiện trong tờ khai ĐKKD, nhưng là dữ liệu pháp lý của chính doanh nghiệp/hộ kinh doanh, **không phải bộ hồ sơ dịch vụ này**; nếu cần sẽ lập module riêng sau.

Không tự suy đoán yêu cầu công chứng, chứng thực, ký số hoặc giấy tờ kèm theo. Các quy tắc phải nằm trong catalog pháp lý có ngày hiệu lực và được người phụ trách pháp lý duyệt trước khi phát hành.

## 1. Kết quả người dùng cần nhận

- Chọn **người làm thủ tục được ủy quyền** từ danh sách profile đã lưu (Minh Long, Lan, Hùng…); thông tin cá nhân không phải nhập lại.
- Có thể thêm/sửa/khóa nhiều profile; mỗi hồ sơ chỉ chọn profile đang hoạt động.
- Thông tin doanh nghiệp/người có thẩm quyền ủy quyền lấy từ case hiện tại.
- Chọn thủ tục/case và phạm vi ủy quyền.
- Chọn một set có sẵn hoặc tạo set mới từ người hiện tại.
- Xem checklist trước khi sinh: văn bản nào bắt buộc, ai ký, bản chính/bản sao, công chứng/chứng thực, số bản, tệp đính kèm còn thiếu.
- Sinh từng văn bản Word/PDF và một gói ZIP toàn bộ set; tên tệp có mã hồ sơ, vai trò, người ký, phiên bản mẫu.
- Lưu set theo từng người, xem lịch sử các lần dùng, nhân bản thành set mới, khóa bản đã phát hành và thu hồi khi cần.
- Khi mở một hồ sơ đăng ký khác, tìm profile người làm thủ tục đã lưu và dùng lại dữ liệu; người dùng vẫn phải xác nhận snapshot trước khi xuất.

**Ví dụ:** hồ sơ hôm nay đang khai cho Công ty ABC. Ở panel phải chọn profile **Minh Long**. Phần mềm lấy CCCD, địa chỉ, điện thoại và tư cách của Minh Long, ghép với thông tin người đại diện Công ty ABC trong case, chọn template ủy quyền phù hợp, rồi sinh văn bản để Công ty ABC ký. Ngày mai chọn profile Lan thì hồ sơ mới dùng Lan; hồ sơ đã sinh cho Minh Long không bị thay đổi.

## 2. Mô hình dữ liệu đề xuất

### 2.1. Profile người làm thủ tục (`authorized_agent_profile`)

Các trường tối thiểu: `agent_id` ổn định (UUID), họ tên, ngày sinh, giới tính, quốc tịch, CCCD/hộ chiếu, ngày cấp/nơi cấp, địa chỉ liên hệ, điện thoại, email, chức danh/đơn vị dịch vụ, chữ ký mẫu (nếu có), giấy tờ đính kèm, tư cách (`service_staff|postal_staff|other_allowed`), trạng thái `active|locked|expired` và ghi chú. Profile là dữ liệu dùng lại; không ghi cứng “Minh Long” vào template.

Thông tin doanh nghiệp/người ủy quyền vẫn lấy từ store của hồ sơ đăng ký hiện tại. Nếu cần lưu khách hàng dùng lại cho nhiều case, đó là danh bạ doanh nghiệp riêng của module hồ sơ, không phải profile người làm thủ tục.

Không dùng số thứ tự làm khóa. Dữ liệu PII chỉ lưu ở thư mục dữ liệu người dùng, không ghi vào git, log, telemetry hay tên thư mục tạm.

### 2.2. Cấu hình đơn vị dịch vụ (`service_provider_settings`)

Lưu tên công ty dịch vụ, mã số doanh nghiệp, địa chỉ, thông tin nhận kết quả và danh sách `authorized_agent_profile`. Cho phép nhiều nhân viên nhưng mỗi bộ hồ sơ phải ghi rõ **một profile người được ủy quyền cụ thể**; không tự thay đổi người đã chốt trong hồ sơ cũ.

### 2.3. Mẫu set (`authorization_set_template`)

Một template xác định: `set_type=service_filing`, tên hiển thị, thủ tục/loại hồ sơ áp dụng, loại profile được phép làm thủ tục, bên ủy quyền lấy từ case, bên được ủy quyền lấy từ profile, danh sách văn bản và tệp cần khách cung cấp, trường dữ liệu cần hỏi, điều kiện one-of/min-max, yêu cầu ký và quy tắc pháp lý (`legal_rule_id`, `effective_from`, `effective_to`).

Template là dữ liệu phiên bản hóa, không sửa ngược các hồ sơ đã phát hành.

### 2.4. Hồ sơ ủy quyền đã tạo (`authorization_case`)

Gồm `authorization_id`, `case_id` đăng ký kinh doanh, `agent_id` (profile Minh Long), `service_provider_settings_id`, `set_template_id/version`, phạm vi công việc, cơ quan tiếp nhận, ngày lập, thời hạn, số văn bản, trạng thái `draft|ready|signed|submitted|revoked|expired`, người tạo/cập nhật, thời điểm và ghi chú.

Khi người dùng bấm “Sinh hồ sơ”, lưu **snapshot** của doanh nghiệp/người ký trong case, profile người được ủy quyền, template, quy tắc pháp lý và dữ liệu form. Thay đổi profile sau đó không làm thay đổi tài liệu đã phát hành.

### 2.5. Văn bản và tệp (`authorization_document`, `authorization_attachment`)

Mỗi tài liệu có `document_id`, loại (`authorization_letter`, `resolution`, `appointment`, `id_copy`, `cover_checklist`, …), mẫu Word/version, người ký, số bản, trạng thái, đường dẫn nội bộ, SHA-256, thời điểm sinh. Tệp đính kèm lưu hash, MIME, kích thước và đường dẫn; không nhúng dữ liệu nhị phân vào Excel.

### 2.6. Lưu trữ

Giữ draft hồ sơ hiện tại tương thích JSON v2. Bổ sung kho bền vững SQLite tại thư mục dữ liệu người dùng (Windows `%APPDATA%\\DangKyKinhDoanh`, macOS `~/Library/Application Support/DangKyKinhDoanh`), có migration/version, transaction và backup. `localStorage` chỉ là autosave tạm, không phải kho hồ sơ ủy quyền.

## 3. Luồng giao diện

### 3.1. Trong wizard hồ sơ đăng ký

Thêm panel bên phải **Người làm thủ tục được ủy quyền**:

1. Hiển thị danh sách profile đang hoạt động: Minh Long, Lan, Hùng…
2. Chọn một profile hoặc bấm **Thêm profile**; sửa/khóa profile ngay tại panel.
3. Hiển thị các set hợp lệ theo thủ tục và tư cách profile; nêu rõ lý do set bị loại.
4. Hiển thị thông tin doanh nghiệp ủy quyền lấy từ case, phần dữ liệu profile và phạm vi/thời hạn.
5. Hiển thị checklist tài liệu doanh nghiệp phải ký/cung cấp; cảnh báo profile thiếu CCCD, hết hạn giấy tờ hoặc không đúng tư cách.
6. Nút **Xem trước**, **Sinh toàn bộ**, **Mở thư mục**. Trước khi sinh phải có màn hình xác nhận snapshot doanh nghiệp + profile + template.

### 3.2. Kho “Profile người làm thủ tục và hồ sơ ủy quyền”

Có tìm kiếm profile theo tên/mã định danh/số điện thoại, xem các hồ sơ đã làm bởi profile đó, lọc theo thủ tục và trạng thái, mở tài liệu, tải ZIP, nhân bản hồ sơ cũ thành case mới, đánh dấu hết hạn/thu hồi. Bản đã `signed/submitted` chỉ được nhân bản, không sửa trực tiếp. Có nút sao lưu/khôi phục kho và hiển thị dung lượng.

### 3.3. Trải nghiệm và an toàn

- Cảnh báo rõ “văn bản này cần ký bởi ai”, không tự ký thay người dùng.
- Không ghi số CCCD/email đầy đủ trong toast, log hoặc tên file nếu không cần; cho phép tên file dạng mã.
- Mọi thao tác thay thế, thu hồi, xóa phải có confirm và audit event; xóa mềm trước, chỉ purge khi người dùng xác nhận.
- Có empty state, duplicate detection, undo khi xóa nhầm, và kiểm tra accessibility giống các form hiện có.

## 4. Bộ văn bản và renderer

### 4.1. Catalog ban đầu (cần pháp lý duyệt)

- Văn bản ủy quyền thực hiện thủ tục đăng ký doanh nghiệp/hộ kinh doanh cho đơn vị dịch vụ.
- Biến thể bên được ủy quyền là công ty dịch vụ, nhân viên cụ thể hoặc đơn vị bưu chính (chỉ bật nếu nghiệp vụ/pháp lý cho phép).
- Bản sao giấy tờ của doanh nghiệp/người ký và giấy tờ của profile Minh Long, nếu set của thủ tục yêu cầu.
- Phiếu kiểm kê tài liệu, trang ký, danh sách tệp đính kèm và biên bản bàn giao (nếu quy trình dịch vụ cần).

Mỗi mục phải có mã mẫu, nguồn pháp lý, trường bắt buộc, người ký và điều kiện áp dụng. Không dùng một mẫu duy nhất cho mọi loại khách hàng hoặc mọi bên nhận ủy quyền.

### 4.2. Quy tắc sinh

- Sinh DOCX từ template hiện có/ template mới, dùng cùng engine render và xử lý xuống dòng email dài.
- Tùy chọn xuất PDF qua LibreOffice; lỗi chuyển đổi không được làm mất DOCX.
- ZIP gồm các văn bản theo thứ tự checklist, `MANIFEST.json` (ID, template/version, hash, người ký, thời điểm) và `README.txt` hướng dẫn ký/nộp.
- Đầu ra lặp lại phải deterministic với cùng snapshot; kiểm tra idempotency và hash.

## 5. Excel: trao đổi set và hồ sơ ủy quyền

Workbook case-level hiện tại được mở rộng, không phá schema cũ. Thêm các sheet:

| Sheet | Nội dung | Khóa chính |
|---|---|---|
| `AUTH_AGENTS` | Các profile người làm thủ tục được ủy quyền | `agent_id` |
| `AUTH_SETS` | Set/template và quan hệ ủy quyền của case | `authorization_id` |
| `AUTH_DOCUMENTS` | Checklist, trạng thái ký, số bản, hash | `document_id` |
| `AUTH_ATTACHMENTS` | Metadata tệp, không chứa binary | `attachment_id` |
| `AUTH_AUDIT` | Lịch sử tạo/sửa/thu hồi/sinh tài liệu | `event_id` |

Quy tắc Excel:

- `META` ghi `schema_version`, `app_version`, `case_id`, `agent_id`, `manifest_hash`, ngày xuất, phiên bản catalog pháp lý.
- Ô nhập liệu có cột `value`, `display`, `type`, `required`, `allowed_values`, `error`; không dựa vào màu để biểu diễn dữ liệu.
- Import là hai pha: đọc/validate thành candidate rồi người dùng xác nhận thay thế; lỗi một sheet không được làm mất draft hiện tại.
- Giữ ID ổn định để round-trip không nhân đôi người/set; phát hiện xung đột và cho phép “dùng bản trong file / giữ bản hiện tại / tạo bản sao”.
- Tệp đính kèm được đối chiếu bằng SHA-256 và đường dẫn tương đối; báo thiếu tệp, không âm thầm bỏ qua.
- Test export/import rỗng, đầy đủ, nhiều người ủy quyền, duplicate, expired, thu hồi, Unicode, email dài và workbook cũ không có các sheet `AUTH_*`.

## 6. API và thay đổi mã nguồn

Bridge Python dự kiến thêm:

- `list_authorized_agent_profiles(filter_json)`
- `save_authorized_agent_profile(payload_json)` / `lock_authorized_agent_profile(id)`
- `list_authorization_sets(case_id)` / `create_authorization_case(payload_json)`
- `preview_authorization_case(id)` / `generate_authorization_case(id, options_json)`
- `open_authorization_document(id)` / `export_authorization_zip(id)`
- `export_authorization_excel(case_id)` / `import_authorization_excel(case_id)`
- `backup_authorization_store()` / `restore_authorization_store()`

Tất cả API trả mã lỗi có cấu trúc, không trả exception/PII thô. UI chỉ merge candidate sau confirm, giống hợp đồng import Excel case-level hiện tại.

## 7. Lộ trình triển khai cho agent

### A0 — Chốt nghiệp vụ và pháp lý

- Lập ma trận các biến thể ủy quyền dịch vụ (khách cá nhân/tổ chức/hộ kinh doanh × bên nhận là công ty/nhân viên) × 28 case hiện có.
- Xác định tài liệu bắt buộc/tùy chọn, người ký, số bản, công chứng/chứng thực, thời hạn.
- Đưa nguồn và ngày hiệu lực vào catalog; có người duyệt pháp lý ký acceptance.

### A1 — Schema, SQLite và migration

- Viết schema/migration, repository transaction, backup/restore, masking log.
- Viết seed catalog và dữ liệu random phục vụ test; không dùng PII thật.

### A2 — Danh bạ và kho set

- CRUD profile người làm thủ tục, tìm kiếm, version/snapshot, trạng thái và audit.
- Test duplicate, archive, concurrent save, restart app và quyền thư mục.

### A3 — Wizard chọn set

- Renderer checklist theo template; validation điều kiện; preview snapshot; luồng confirm.
- Chỉ liên kết dữ liệu khách hàng/người ký vào form hiện có; không thay đổi các loop “đại diện theo ủy quyền” nội bộ của PLI/PLII.

### A4 — Word/PDF/ZIP

- Tạo các template thật sau khi A0 duyệt; renderer deterministic, xử lý email/địa chỉ dài, ký và phụ lục.
- Visual QA từng trang bằng LibreOffice; kiểm tra manifest/hash.

### A5 — Excel và tương thích

- Mở rộng exporter/importer case-level theo mục 5; candidate/confirm và conflict resolver.
- Round-trip property tests, negative tests, workbook cũ và đường dẫn attachment.

### A6 — QA, đóng gói và phát hành

- E2E cho từng loại profile (nhân viên/cá nhân được phép/bưu chính nếu bật), 28 case đại diện, chọn lại profile cũ, offline/restart.
- Kiểm tra PII, backup/restore, accessibility, Windows `.exe`, macOS `.app`; cập nhật README và release checklist.

## 7A. Phân công agent song song — bắt buộc cho agent điều phối

Agent chính phải đóng vai trò **coordinator**, chia việc cho số subagent tối đa mà môi trường cho phép. Không để một agent làm tuần tự toàn bộ. Các subagent chỉ sửa nhánh/file được giao; coordinator chịu trách nhiệm hợp nhất, giải quyết mâu thuẫn và không cho phép code trước khi A0 đạt legal gate.

### Wave R — đọc luật và kiểm kê mẫu (chạy song song)

| Agent | Nhiệm vụ | Đầu ra bắt buộc |
|---|---|---|
| R1 — Legal primary sources | Đọc Nghị định 168/2025/NĐ-CP, Luật Doanh nghiệp và văn bản sửa đổi/liên quan hiện hành. Tập trung ủy quyền nộp hồ sơ, ký/nộp trực tiếp, trực tuyến, bưu chính, xác thực điện tử, công chứng/chứng thực. | `docs/authorization/legal_research.md`: URL chính thức, điều/khoản, trích yếu ngắn, ngày hiệu lực, điểm còn chưa chắc chắn. |
| R2 — Form/legal catalog | Đọc Văn bản hợp nhất biểu mẫu hiện hành và phụ lục/hướng dẫn hồ sơ. Xác định văn bản ủy quyền nào là thành phần hồ sơ, ai ký, bản chính/bản sao, số bản và điều kiện theo DN/HKD. | `docs/authorization/form_legal_matrix.md`: ma trận `case × loại khách × loại agent × tài liệu × người ký × công chứng`. |
| R3 — Repo inventory | Kiểm kê `app/data/use_cases.json`, `case_questionnaires`, `blocks`, `form_maps`, `app/templates`; phân biệt ủy quyền dịch vụ với “đại diện theo ủy quyền” nội bộ và ủy quyền hộ gia đình. | `docs/authorization/repo_inventory.md`: đường dẫn/bằng chứng, danh sách thiếu, không tự kết luận pháp lý. |
| R4 — Independent legal reviewer (nếu còn slot) | Đọc lại kết quả R1/R2 độc lập, tìm điểm mâu thuẫn hoặc diễn giải quá mức; kiểm tra nguồn cấp tỉnh/cơ quan tiếp nhận nếu có. | `docs/authorization/legal_review_notes.md` và danh sách câu hỏi cần chủ app/pháp lý duyệt. |

R1–R4 không được viết template Word hay thay đổi code. Coordinator chỉ chuyển sang Wave I sau khi có `LEGAL_GATE=approved` hoặc ghi rõ hạng mục bị block.

### Wave I — thiết kế và triển khai (chạy song song sau khi Wave R được duyệt)

| Agent | Nhiệm vụ | Đầu ra/code sở hữu |
|---|---|---|
| I1 — Data/store | Schema SQLite, migration, repository, backup/restore, snapshot và masking PII. | Module store + `docs/authorization/schema_contract.md` + migration tests. |
| I2 — Profile UI | Panel phải chọn profile Minh Long, thêm/sửa/khóa profile, validation CCCD/giấy tờ, autosave và accessibility. | `app_web/ui/*` theo file ownership đã thống nhất + UI tests. |
| I3 — Legal rules/templates | Tạo catalog template theo matrix đã duyệt, trường dữ liệu, điều kiện áp dụng và DOCX placeholder. | `app/data/authorization/*`, `app/templates/authorization/*`, render fixtures; không tự thêm điều luật ngoài R1/R2. |
| I4 — Generator | Ghép case + profile, sinh DOCX/PDF/ZIP/MANIFEST, deterministic hash, xử lý lỗi từng đầu ra. | Bridge/renderer + golden fixtures + visual report. |
| I5 — Excel | Sheet `AUTH_AGENTS`, `AUTH_SETS`, `AUTH_DOCUMENTS`, `AUTH_ATTACHMENTS`, `AUTH_AUDIT`; export/import candidate/confirm/conflict. | Excel tools + round-trip/negative tests; giữ tương thích workbook cũ. |
| I6 — QA/security (nếu còn slot) | E2E 28 case, Unicode/email dài, restart/offline, PII scan, backup restore, visual Word/PDF. | `docs/authorization/test_matrix.md`, test runner và defect list. |

Coordinator phải chia sẻ các contract của I1 trước cho I2–I5; I3 chỉ khóa template sau legal matrix; I4/I5 dùng cùng `authorization_id`, `agent_id` và snapshot version. Nếu môi trường chỉ cho ít slot, ưu tiên R1/R2/R3 ở Wave R rồi I1/I2/I3/I4/I5 theo dependency; vẫn giữ các nhiệm vụ độc lập dưới dạng handoff.

### Quy tắc điều phối, review và bàn giao

1. Mỗi agent nhận prompt có: mục tiêu, file được phép sửa, file cấm sửa, test phải chạy, format báo cáo và tiêu chí hoàn thành.
2. Không hai agent cùng sửa một file. Thay đổi schema/template phải qua coordinator review; thay đổi legal rule phải trỏ tới `legal_research.md`.
3. Agent gửi báo cáo theo mẫu: `DONE/BLOCKED`, files changed, commands/tests, evidence, open questions. Coordinator không chấp nhận báo cáo “đã xong” không có bằng chứng.
4. Sau mỗi wave, coordinator chạy `git diff --check`, test hợp đồng, kiểm tra PII và ghi decision vào `docs/authorization/decision_log.md`.
5. Khi agent bị block bởi thiếu quy định hoặc mẫu, giữ hạng mục ở `BLOCKED`, không tự đoán; chuyển câu hỏi cho chủ app/pháp lý.
6. Chỉ merge khi legal gate, schema gate, render gate và Excel round-trip gate đều đạt. Sau đó mới build `.exe`/`.app`.

### Prompt điều phối dùng cho agent chính

> Bạn là coordinator của module hồ sơ ủy quyền cho dịch vụ đăng ký kinh doanh. Hãy tạo tối đa subagent khả dụng và giao Wave R (R1–R4) chạy song song để đọc nguồn pháp lý chính thức, kiểm kê biểu mẫu và repo. Thu thập báo cáo vào các file được chỉ định, đối chiếu mâu thuẫn và xin duyệt legal gate trước khi code. Khi gate đạt, tạo Wave I (I1–I6) chạy song song theo ownership/dependency; không để hai agent sửa cùng file. Bắt buộc có schema contract, catalog template, UI profile bên phải, DOCX/PDF/ZIP, Excel round-trip, test negative/visual và báo cáo bàn giao. Không tự suy đoán luật; mọi quy tắc phải có nguồn, ngày hiệu lực và người duyệt.

## 8. Tiêu chí nghiệm thu (Definition of Done)

- Mỗi loại profile được phép có template và checklist đã được duyệt; không thể chọn set sai profile/case.
- Chọn người đã lưu tạo đúng toàn bộ tài liệu, đúng người ký và đúng điều kiện; snapshot mở lại vẫn giống hash.
- Một người có thể dùng trong nhiều case nhưng mỗi lần phát hành có `authorization_id` và lịch sử riêng.
- DOCX mở được, PDF/ZIP/manifest đầy đủ; lỗi một đầu ra được báo rõ và không làm mất đầu ra khác.
- Excel export → import giữ nguyên party/set/document/status/ID; import lỗi không thay draft đang mở.
- Xóa/thu hồi có audit và khôi phục được từ backup; không có PII trong repository/log.
- Test tự động và visual QA đạt; agent bàn giao báo cáo test, ảnh render, schema version và hướng dẫn nâng cấp.

## 9. Quyết định cần chủ app xác nhận trước khi A1

1. Kho dùng SQLite nội bộ (khuyến nghị) hay chỉ JSON; nếu nhiều máy dùng chung có cần thư mục đồng bộ không?
2. Có cho phép tổ chức dịch vụ/bưu chính làm bên được ủy quyền không, hay chỉ cá nhân?
3. Có cần ký số/đóng dấu điện tử không, hay phần mềm chỉ sinh tài liệu để ký tay?
4. Có lưu bản scan CCCD/giấy tờ trong kho không; nếu có, chính sách mật khẩu/mã hóa và thời hạn lưu là gì?
5. Khi một người đổi CCCD/địa chỉ, các set nháp cũ cập nhật tự động hay giữ snapshot và cảnh báo?

## 10. Nguồn pháp lý cần cập nhật khi triển khai

- Nghị định 168/2025/NĐ-CP về đăng ký doanh nghiệp: <https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2025-nd-cp-ve-dang-ky-doanh-nghiep-119250702175708554.htm>
- Văn bản hợp nhất 28/2026/VBHN-TT-BTC và danh mục 80 biểu mẫu: <https://xaydungchinhsach.chinhphu.vn/dang-ky-doanh-nghiep-chi-tiet-80-bieu-mau-119260910102204737.htm>

Hai liên kết trên chỉ là điểm bắt đầu kiểm tra. Trước khi phát hành phải đối chiếu bản gốc, văn bản sửa đổi sau ngày cập nhật và quy định của cơ quan tiếp nhận tại địa phương.
