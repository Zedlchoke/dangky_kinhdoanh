# MASTER PLAN v5 — sửa lỗi và rà soát toàn bộ ứng dụng

> **CHECKPOINT PHASE 5R — 2026-09-04 @ `f51f218` (sau fix Lane D):** Phase
> 5R0–5R4 đã chạy xong trên main: gate visual **455/455 records** (91 form ×
> 5 fixture semantic) — **detector D1..D12 = 0, 0 trang trắng, 0 export
> error**; Word 16.16.27 mở trực tiếp **91/91 PASS**; runner **57 PASS /
> 0 FAIL** (3 suite 5R đã vào runner); coverage drift=0. Bằng chứng:
> `generated_ho_so/_visual_layout/phase5r_gate/final/` (manifest + summary +
> 1644 trang PNG + word_open_inventory). Baseline RED (244/455 FAIL) giữ tại
> `.../baseline_c9d095e/`. Auditor độc lập (Lane D): **PASS-WITH-NOTES** —
> 0 gian lận gate; 3 finding (F1 bug sectPr, F2 regen drift, F3 reviewer
> sign-off) đã xử lý/ghi nhận tại `f51f218`.
>
> **Trạng thái WLAY:** 001/002/003/004/006/007/008/009/010/012 CLOSED;
> 005 PARTIAL (3 matrix M12 BLOCKED_OWNER chờ owner); 011 OPEN-census (553
> glue candidate cần adjudicate). Reviewer sign-off 647 candidate + toàn bộ
> 1644 trang bởi NGƯỜI còn OPEN (gate ghi reviewer_verdict per record).
> Windows/.exe: NOT RUN. KHÔNG mở Phase 6/Excel rollout/Windows packaging
> cho tới owner duyệt báo cáo Phase 5R.

> **CẬP NHẬT KHẨN PHASE 5R — 2026-09-03:** audit corpus Word mới nhất đã xem
> **91 DOCX / 264 trang** và kết luận **VISUAL LAYOUT = FAIL**. Word mở trực
> tiếp 91/91 chỉ là openability PASS. Đã xác nhận source-indicator lộ ở 44 form,
> chữ ký sai cột/tách trang/thiếu vùng viết, field code lộ, trang trắng hoặc
> boundary thừa, fixed matrix phẳng/thiếu và bảng rộng khó đọc.
>
> Báo cáo bằng chứng: `docs/word_layout_audit_2026-09-03.md`.
> Kế hoạch sửa có hiệu lực: `docs/plan_phase5r_word_layout.md`.
> Mọi kết luận layout/Word trong các checkpoint cũ chỉ là lịch sử và bị
> supersede bởi Phase 5R. Không mở Phase 6 cho tới khi Definition of Done Phase
> 5R đạt trên commit sạch và auditor độc lập xác minh.

> **Checkpoint:** 2026-09-03 (buổi 2), `main@28df5cb` sau Phase 3+4:
> coverage **111/111 drift=0** — `IMPLEMENTED_VERIFIED` 64→**76**, MISSING
> 7→**0**, PARTIAL 4→**0**, BLOCKED_OWNER 22, NO_TABLE 7, OUTPUT_ONLY 6;
> runner **51 PASS / 0 FAIL / 0 NOT RUN** (thêm 2 suite row-contract);
> manifest census **tái lập được từ generator** (HEADING_OVERRIDES gỡ 3
> hand-fix Phase 2); row/blank-row contract implement + corpus + inventory
> machine-readable (`docs/row_contract_inventory.json`). Word/WebView2/
> Windows visual: **NOT RUN** (Phase 5+ OPEN). Sau checkpoint này, corpus WIP
> 91 DOCX đã được mở/render: open-direct **PASS 91/91**, nhưng audit bố cục
> **FAIL**; xem cập nhật Phase 5R phía trên.
> Chi tiết ledger `docs/execution_ledger.md`; owner decisions
> `docs/decision_registry.md` (thêm Q-P4-1 min_rows nested-grid).
>
> Đây là kế hoạch duy nhất có hiệu lực. Source/tests/manifests tại HEAD là trọng
> tài kỹ thuật; nội dung pháp lý phải đối chiếu văn bản đang có hiệu lực. Các kế
> hoạch/checkpoint cũ chỉ là lịch sử trong `docs/execution_ledger.md`.

## 0. Checkpoint Phase 3+4 (2026-09-03, buổi 2) — kết quả thật

**Phase 3 — 2 MISSING + 4 PARTIAL xử lý đúng bản chất (đều không phải bảng
thiếu thật, không thêm field mới, không sửa generated bằng tay):**

| Section | Root cause | Fix |
|---|---|---|
| PLI_M01/bhxh_phuong_thuc_dong | Census stale: notes than thiếu `chk_bc_03_thang` nhưng ba64f29 đã đủ 3/3 token | Override already_complete; audit scalar_credited verify region keys (tiền lệ PLI_M17) |
| PLI_M11/ds_to_chuc_xd_cshhl | Spec chỉ tồn tại inline trong build_form_maps | File spec `formation/PLI_M11.json` verbatim (regen zero-diff chứng minh bằng full run) |
| PLI_M01+M02 tai_san_gop_von, PLI_M04 co_cau/chao_ban | `stt` là số thứ tự in sẵn của fixed-matrix | Detector credit `stt` khi fixed-matrix có fixed_rows evidence (+ selftest 38→51, positive+negative) |
| PLI_M04/co_cau_loai_co_phan | `menh_gia_co_phan` là dòng scalar riêng (TT 121), không phải cột | Detector credit exact-match scalar vùng anchor |
| PLI_M04/co_phan_duoc_quyen_chao_ban | Cột label readonly thiếu tag định danh (lệch convention anh em) | Wire tag `loai_co_phan_chao_ban` trong runtime contract (inputType giữ readonly) |

Phát hiện quan trọng phụ: manifest.json từng bị sửa tay 3 heading ở Phase 2 →
regen mất fix. Đưa về `HEADING_OVERRIDES` trong build_manifest.py — manifest
tái lập được lại từ generator+fragments (delta chỉ còn override mới).

**Phase 4 — row/blank-row contract:**

- Gap thật đã vá: hàng MỌI ô tróng trong store đi thẳng vào DOCX → filter ở
  `GridCtl.exportLoops` (JS) + guard `_expand_loops` (Python last-mile),
  `{_stt}` đánh lại trên dữ liệu; draft round-trip giữ nguyên row (blank sống
  trong draft, chỉ lọc ở export); dòng chỉ có discriminator không bị mất.
- Fixed legal row ≠ blank row: fixed-matrix in đủ dòng pháp định khi rỗng
  (FM1), blankRows in sẵn của bản giấy không bị lọc — corpus pin cả hai.
- Inventory: `tools/census/row_contract_inventory.py` → JSON/MD (11 global
  grids, 18 form-scoped, 14 section contracts, 42 dynamic_tables, 21
  section_specs, 42 blankRows blocks; policies/gaps/test-coverage; gate count).
- BLOCKED_OWNER Q-P4-1: `min_rows` 3 nested-grid khai mà không tầng nào
  enforce — chờ owner chốt semantics (không tự chọn).

**Trạng thái lịch sử tại checkpoint Phase 4:** Word/WebView2/Windows/.exe khi
đó chưa chạy thật. Trạng thái Word/layout mới nhất nằm trong Phase 5R phía trên;
WebView2/Windows/.exe vẫn **NOT RUN**.

## 1. Mục tiêu

Không chỉ sửa các lỗi đã thấy. Wave này phải:

1. đưa release gate về xanh thật;
2. tái lập danh sách chính xác bảng nào đã có, thiếu, chưa đủ cột hoặc bị block;
3. quét 87/87 biểu mẫu và mọi use case trên UI, draft, validation, Excel,
   DOCX/ZIP và accessibility;
4. sửa lỗi theo gốc rễ, có test chống hồi quy, không vá generated artifact;
5. audit độc lập sau sửa;
6. chỉ mở Windows packaging khi mọi gate chất lượng đã xanh.

## 2. Kết quả audit hiện tại

### 2.1 Phần đã làm được

- Base code `main` đồng bộ `origin/main@6ae63c2`; worktree hiện có các cập nhật
  tài liệu audit chưa commit, không được coi là release-clean cho tới khi Lead
  review và commit/phân loại.
- P0/P1/P2/P3 nền kỹ thuật đã merge: bốn table kinds, draft migration,
  validation, DOCX export, M72 one-variant, accessibility fixes.
- Excel X1–X6 pilot PLI_M72 đã implement, round-trip/negative test PASS và owner
  đã duyệt hình phiếu mẫu.
- Header hai band đã áp dụng cho 22 mẫu.
- M09 đã rebuild/decontaminate; capital M03/M04/M05/M12 và tax PLII_M02 đã có
  spec/generated output mới.
- Manifest structural census vẫn nhận đủ 87 form, 111 section, không còn
  signature unclassified.
- Accessibility chạy ngoài sandbox: **36 PASS / 0 FAIL** cho PLI_M01, PLI_M02
  và app shell.

### 2.2 Gate hiện không xanh

Release runner trong sandbox: **43 PASS / 3 FAIL / 0 NOT RUN**.

- `test_p3_a11y`: FAIL do sandbox không được bind `127.0.0.1`; chạy ngoài
  sandbox đạt 36/36. Đây là hạn chế môi trường, không phải production defect,
  nhưng runner cần cơ chế phân loại `NOT RUN`/preflight đúng thay vì báo FAIL mơ hồ.
- `p1_c_verify_plii_m02`: FAIL do verifier chỉ gán 3/4 bảng ngành vào region sau
  khi thêm header-band và bảng thuế.
- `test_industry_household`: cùng lỗi phân loại table/region.

Kiểm tra trực tiếp template `PLII_M02.docx` cho thấy production hiện có **6
bảng**: 1 header-band, 3 bảng ngành Mục A, 1 bảng thuế, 1 bảng ngành C.3;
`form_maps` cũng khai đủ 4 dynamic table ngành. Hai FAIL sau nhiều khả năng là
verifier stale, nhưng phải sửa bằng semantic mapping và negative test, không
được nới thành “đếm gần đúng”.

Audit lại ngày 2026-08-30 xác nhận các con số trên chưa đổi. Đồng thời:

- `docx_render --test-all`: **87 PASS / 0 FAIL**, chỉ chứng minh sinh package,
  không phải visual PASS;
- `p1_b_verify_m72`: **9/0** và conditional export **6/0**;
- UI visual 87/87 và Word/PDF visual 87/87: **NOT RUN** do thiếu backend/tooling.

### 2.3 Lỗi layout/census đã xác nhận

`check_layout_l1` hiện FAIL:

- newline blocks còn 263, thấp hơn threshold 293; cần phân biệt regression thật
  với giảm hợp lệ do paragraph đã được chuyển thành bảng;
- 4 vùng `STT...` bị glue tại PLII_M02 và PLI_M72;
- 2 digit-run `12345678910` tại PLII_M02.

`numbering_audit --gate` hiện FAIL:

- 23/87 form còn footnote-glue;
- chain PLI_M03→PLI_M06 thiếu mục 7;
- chain PLI_M04→PLI_M08 thiếu mục 8–9;
- PLI_M05→PLI_M09 đã liên tục 6→7.

### 2.4 Danh sách bảng hiện chưa đáng tin

Manifest file vẫn báo 33 form `BLOCKED_LEGAL_REVIEW`, 33 section `missing_grid`,
5 `partial_columns`, 1 `partial`, 1 `contaminated`. Tuy nhiên source/spec/form
maps hiện đã triển khai một số section vẫn bị ghi `missing_grid`, ví dụ capital
M03/M04/M05, tax PLII_M02 và M09.

Nguyên nhân: fragment census và `LEAD_STATUS_OVERRIDES` chưa hòa giải ổn định;
một số override dùng section ID cũ/không trùng manifest. Vì vậy:

> Không được tuyên bố “còn 33 bảng thiếu”, cũng không được tuyên bố “đã đủ bảng”,
> cho tới khi tạo lại ma trận coverage 111/111 section từ source hiện tại.

### 2.5 Lỗi/gap người dùng cần điều tra

1. Bảng ngành từng xuất hiện `Tên ngành = undefined`, `Mã ngành = 6`; chưa có
   test tái hiện trạng thái draft/autosave thật.
2. Cột “Ngành nghề kinh doanh chính” đang dùng radio tròn. Semantics chọn một là
   đúng, nhưng hình thức phải đối chiếu mẫu gốc; nếu mẫu dùng ô vuông thì giữ
   radio semantics nhưng render control vuông và DOCX xuất `X`.
3. Chữ ký một số mẫu không đủ khoảng trống để ký.
4. Checkbox DOCX có thể để dấu `X` rơi sang dòng riêng.
5. PLII_M03–M06 có dấu hiệu bảng thuế bị làm phẳng thành số mồ côi.
6. Evidence screenshot M09 hiện có được chụp trước rebuild, không dùng làm bằng
   chứng cho HEAD mới.
7. Visual/browser audit mới trong phiên lập plan: **NOT RUN** vì không có browser
   backend. PDF re-render mới: **NOT RUN** vì môi trường thiếu Poppler. Evidence
   cũ chỉ dùng để lập giả thuyết, không được dùng để đóng gate hiện tại.

## 3. Nguồn pháp lý bắt buộc

Mỗi form/spec phải có `source_evidence` trỏ đúng phiên bản hiệu lực:

- Thông tư 68/2025/TT-BTC về biểu mẫu;
- Thông tư 121/2026/TT-BTC sửa Thông tư 68, hiệu lực 21-08-2026;
- Nghị định 168/2025/NĐ-CP về đăng ký doanh nghiệp;
- Nghị định 296/2026/NĐ-CP sửa Nghị định 168, hiệu lực 23-07-2026.

Trước khi sửa nội dung mẫu, Lead phải lập `form → văn bản → phụ lục/mẫu → phiên
bản → hiệu lực → source hash/page`. Không dùng bản scan cũ nếu mẫu đã bị thay;
không tự suy diễn khi hai văn bản xung đột.

## 4. Thứ tự thực hiện

### Wave A — Khôi phục baseline xanh

Lead làm trên main; chưa spawn coding lane.

1. Sửa hai verifier PLII_M02 theo semantic content:
   - nhận diện header-band bằng `band:header`/nội dung;
   - nhận diện bảng thuế bằng header “Chỉ tiêu”;
   - map đúng bốn industry table theo occurrence/heading/form_maps;
   - fail khi thiếu, thừa, đảo region hoặc table_index lệch.
2. Không thay production template nếu dump 6 bảng và `form_maps` vẫn khớp.
3. Thêm negative mutations cho header-band/tax table chen giữa các industry
   region để verifier không hồi quy.
4. Cho release runner preflight việc bind localhost:
   - có quyền → chạy a11y và PASS/FAIL bình thường;
   - không có quyền → critical `NOT RUN` có lý do, không ghi product FAIL giả;
   - release chính thức vẫn bắt buộc chạy a11y ở môi trường cho phép.
5. Chạy full runner ngoài sandbox/CI phù hợp đến **46 PASS / 0 FAIL / 0 NOT RUN**.

**Gate A:** repo sạch, verifier chính xác, runner xanh thật.

### Wave B — Tái lập bảng sự thật 111 section

Tạo một lane census/test riêng; không sửa UI/generator trong lane này.

1. Sinh `docs/table_coverage_current.md` hoặc JSON máy đọc được, một dòng cho
   từng section:
   `form_id · section_id · kind · source version · spec · template table ·
   form_maps · blocks · runtime contract · draft key · validation · DOCX · visual ·
   final status`.
2. Status cuối chỉ gồm:
   - `IMPLEMENTED_VERIFIED`;
   - `PARTIAL_COLUMNS`;
   - `MISSING_IMPLEMENTATION`;
   - `BLOCKED_OWNER`;
   - `NO_TABLE`;
   - `OUTPUT_ONLY`;
   - `REMOVED_BY_CURRENT_LAW`.
3. Reconcile fragment status, overrides, form specs, form maps và runtime
   contracts. Override không khớp section ID phải làm gate FAIL.
4. Gate hai chiều:
   - spec/form_maps/runtime có nhưng manifest vẫn `missing_grid` → FAIL;
   - manifest `implemented` nhưng thiếu template/blocks/runtime/export → FAIL.
5. Refresh totals từ effective statuses; không giữ `33 blocked` chỉ vì snapshot
   cũ.
6. Tách header-band khỏi data-table census; tách layout table khỏi business table.

**Gate B:** coverage 111/111 không có dòng mơ hồ; lúc đó mới có con số chính xác
“còn thiếu bao nhiêu bảng”.

### Wave C — Điều tra toàn ứng dụng, read-only

Sau Gate B, tạo một auditor mới không sửa code. Quét **không sampling**:

#### C1. Phạm vi

- 87 biểu mẫu;
- toàn bộ use case hiện có trong `use_cases.json`;
- 5 variant M72;
- scalar, date, checkbox, dropdown, selector và bốn table kinds;
- trạng thái rỗng, hợp lệ, lỗi, draft cũ, dữ liệu lớn;
- flow chọn thủ tục → nhập → validate → save/reload/import → Excel → DOCX/ZIP.

#### C2. UI/UX checklist từng form

- tiêu đề, quốc hiệu, form number, section numbering;
- field không tràn/chồng/cắt, label đúng ô, focus thấy rõ;
- không có `undefined`, `null`, `NaN`, giá trị rác hoặc placeholder lọt vào input;
- button thêm/xóa/nhân bản/lên/xuống hoạt động và có aria-label;
- radio/checkbox đúng semantics lẫn hình thức nguồn;
- validation message dễ hiểu, mở đúng tab và focus đúng field;
- 1280, 768, 375 px; zoom 100/150/200%; keyboard-only;
- không mất dữ liệu khi đổi form/variant.

#### C3. Table checklist

- đúng số bảng/section theo coverage matrix;
- đúng header rows, rowspan/colspan và số cột vật lý;
- nhập đúng **1 dòng** thì UI/draft/DOCX chỉ có đúng dữ liệu 1 dòng; blank rows in
  không biến thành dữ liệu;
- thêm/xóa/reorder/duplicate không đổi nhầm bảng cùng semantic key;
- totals/formula/cross-field đúng; output-only không sửa được;
- export không nuốt conflict và không trộn dữ liệu các occurrence/variant.

#### C4. DOCX/Word checklist

- render 87/87 bằng Word/LibreOffice, chia batch nhỏ;
- 0 marker `{...}`, 0 số mồ côi, 0 `X` riêng dòng, 0 trang trắng bất thường;
- chữ ký có khoảng trống thực tế;
- header band đúng trái/phải, không viền lộ;
- bảng đủ viền/cột/page-break; superscript/footnote đúng;
- M72 chỉ đúng một variant.

#### C5. Đầu ra

`inventory.json` + report gồm `PASS | FAIL | NOT RUN`, screenshot/PDF page và
reproduction steps cho từng lỗi. Evidence phải tạo từ HEAD hiện tại; ảnh cũ chỉ
được reuse nếu input hash, renderer và generated form không đổi.

**Gate C:** 87/87 form và mọi use case có verdict; không còn “chưa nhìn”.

### Wave D — Sửa lỗi theo lớp gốc rễ

Chỉ mở lane sau khi C phân nhóm lỗi. Tối đa ba lane song song, file ownership
không chồng.

#### D1 — Industry input/UI

- Tái hiện `undefined`/`6` từ draft/autosave/legacy migration trước khi sửa.
- Normalize missing cell về chuỗi rỗng, không stringify `undefined`.
- Kiểm binding `ma_nganh`/`ten_nganh`, VSIC async selection và row IDs.
- Quyết định hình vuông/tròn theo source; giữ exclusivity và accessibility.
- Thêm suite `test_industry_input_negative` phủ mọi loop ngành, reload và export.

#### D2 — Extractor/footnote/numbering

- Tách superscript footnote khỏi chữ nhưng không xóa số nội dung thật.
- Đưa 23 form GLUE về 0 bằng sandbox regen + negative fixtures.
- Phân loại newline giảm 309→263: cập nhật metric theo paragraph còn tồn tại nếu
  conversion-to-table hợp lệ; nếu mất newline thật thì sửa extractor.
- Xử lý bốn STT-glue/digit-run bằng table implementation hoặc explicit
  `BLOCKED_OWNER`; không dùng allowlist che lỗi.
- Reconcile chain M03→M06 và M04→M08 theo mẫu hiện hành.

#### D3 — DOCX/layout

- Signature có tối thiểu khoảng trống theo source và không đẩy footnote sai trang.
- Checkbox label + `X` cùng dòng; test cả checked/unchecked.
- Số mồ côi PLII_M03–M06: rebuild bảng thuế theo source hoặc giữ blocker owner;
  không remap bằng CSS để che cấu trúc thiếu.
- Header 22 mẫu kiểm cả UI và Word output.

#### D4 — Missing/partial tables

Rollout theo coverage matrix và quyết định pháp lý, ưu tiên:

1. bảng ảnh hưởng trực tiếp thao tác use case đang ship;
2. partial columns/data-loss;
3. M72 N2–N5;
4. admin/branch/attachment tables;
5. output-only/admin fixed rows.

Mỗi section phải đi xuyên spec → generated template → form_maps → blocks → runtime
→ draft → validation → DOCX → visual. Không ghi `IMPLEMENTED_VERIFIED` nếu chỉ có
module/test độc lập.

#### D5 — Documentation truth

Cập nhật đồng thời:

- `docs/decision_registry.md` — đóng quyết định đã implement; ghi nguồn mới;
- `docs/product_scope_registry.md` — 28 use case hiện tại, Excel không còn “out
  of scope”, P3/a11y không còn PENDING;
- `docs/defect_registry.md` — status theo evidence mới;
- `docs/execution_ledger.md` — checkpoint hiện hành;
- manifest/coverage totals.

**Gate D mỗi lane:** test đỏ trước → fix → targeted xanh → Lead merge → regen ×2
zero-diff → census → visual re-shoot → full runner → commit sạch.

### Wave E — Auditor độc lập sau sửa

Auditor mới, read-only, không phải agent đã sửa:

1. kiểm từng defect class và lỗi mới từ Wave C;
2. review diff để phát hiện nới test, sửa generated bằng tay hoặc override che lỗi;
3. chạy độc lập release, manifest coverage, numbering, L1, marker/glyph scan;
4. spot-check UI và Word output từ evidence mới;
5. verdict từng mục `PASS/PARTIAL/FAIL/NOT RUN`.

Không vào Wave F nếu còn FAIL thuộc scope đã mở.

### Wave F — P5R final whole-app gate

| Gate | PASS khi |
|---|---|
| G1 Legal/source | 87/87 map đúng TT 68+121 và NĐ 168+296 hiện hành; source evidence resolve được |
| G2 Coverage | 111/111 section có final status; 0 manifest/spec/runtime drift |
| G3 Numbering/footnote | 0 JUMP/CHAIN/GLUE ngoài exception owner phê duyệt |
| G4 UI hygiene | 0 undefined/null/NaN/rác; 0 overlap/cut; controls đúng semantics |
| G5 Tables | mọi implemented table qua one-row, round-trip, formula, conflict và DOCX tests |
| G6 DOCX/ZIP | 87/87 mở bằng Word; 0 marker/số mồ côi/X lệch/trang trắng; M72 đúng variant |
| G7 Excel | pilot PLI_M72 round-trip/negative/visual PASS; phạm vi rollout khác được ghi rõ |
| G8 A11y/viewport | keyboard, focus, ARIA, contrast, 3 viewport và zoom 200% PASS |
| G9 Resilience/security | draft xấu, Unicode, path hostile, offline/error handling PASS |
| G10 Release hygiene | runner 0 FAIL/critical NOT RUN, generator idempotent, allowlist cân, tree sạch |

### Wave G — Windows package

Chỉ mở khi F đạt 10/10:

- build `.exe`/installer tái lập;
- smoke trên Windows sạch không Python;
- WebView2/dialog/save/import/Excel/DOCX/ZIP/offline;
- ghi artifact path, hash, size, OS/WebView2 version và verdict.

### Wave H — Final audit và bàn giao

Auditor read-only mới đối chiếu toàn bộ `CORE_APP_DONE`. Nếu Excel được định nghĩa
là toàn bộ use case thay vì pilot PLI_M72, phải có wave rollout questionnaire
riêng trước khi ghi `FULL_PRODUCT_DONE`.

## 5. Quyết định owner cần chốt

1. Có mở rebuild bảng thuế PLII_M03–M06 để xử lý số mồ côi không?
2. PLI_M10 dùng mẫu mới theo TT 121 dù thay contract “Quyền chi phối” cũ?
3. PLI_M11 đã bị bãi bỏ: gỡ khỏi app/pipeline hay giữ ở trạng thái legacy?
4. Có mở phần đuôi còn thiếu của M03/M04/M05 theo mẫu hiện hành không?
5. “Ngành nghề chính” trên UI cần hình ô vuông như giấy hay chấp nhận radio tròn?
6. Excel là pilot PLI_M72 hay phải rollout cho mọi thủ tục trước `FULL_PRODUCT_DONE`?
7. `app_tk` là legacy-supported hay deprecated?
8. [Phase 4] `min_rows=1` của 3 nested-grid ủy quyền (PLI_M02/M12/M15): enforce
   vô điều kiện (sẽ chặn hồ sơ KHÔNG ủy quyền) / chỉ khi section có dữ liệu /
   xóa khai báo? Chi tiết `docs/decision_registry.md` Q-P4-1; đang giữ
   BLOCKED_OWNER, chưa enforce.

## 6. SOP dùng worker/sub-agent

### 6.1 Trình tự spawn bắt buộc

| Thời điểm | Agent được tạo | Điều kiện |
|---|---|---|
| Wave A | Không tạo sub-agent | Lead đưa baseline về 46/46 trước |
| Wave B | `coverage-agent` | main sạch, Gate A PASS |
| Wave C | `whole-app-auditor` read-only | coverage 111/111 đã commit |
| Wave D batch 1 | tối đa 3 lane: `fix-industry`, `fix-extractor`, `fix-docx-layout` | inventory Wave C đã phân loại root cause và ownership không chồng |
| Wave D batch 2 | các lane `fix-missing-<domain>` | batch 1 đã merge sạch; owner đã mở đúng legal scope |
| Wave E | `post-fix-auditor` read-only mới | mọi coding lane đã merge, main sạch |
| Wave H | `final-release-auditor` read-only mới | P5R 10/10 và Windows evidence có đủ |

Không tạo ba coding agent ngay từ đầu. Coverage và investigation phải hoàn tất
trước để tránh hai agent sửa cùng một lỗi hoặc dựa vào con số 33 bảng đã stale.

### 6.2 Chuẩn bị worktree

Lead chạy từ root repo:

```bash
ROOT_REPO=$(git rev-parse --show-toplevel)
BASE_COMMIT=$(git rev-parse HEAD)
WORKTREE_ROOT="${ROOT_REPO%/*}/dangky_kinhdoanh-worktrees"

git status --short
git worktree list
git branch --no-merged main
mkdir -p "$WORKTREE_ROOT"
```

Nếu `git status --short` có output chưa phân loại, **DỪNG**. Không dùng
`reset`, `clean`, `checkout --` hoặc `restore` để ép sạch.

Tạo coding lane:

```bash
git worktree add "$WORKTREE_ROOT/coverage" \
  -b agent/coverage "$BASE_COMMIT"

git worktree add "$WORKTREE_ROOT/fix-industry" \
  -b agent/fix-industry "$BASE_COMMIT"

git worktree add "$WORKTREE_ROOT/fix-extractor" \
  -b agent/fix-extractor "$BASE_COMMIT"

git worktree add "$WORKTREE_ROOT/fix-docx-layout" \
  -b agent/fix-docx-layout "$BASE_COMMIT"
```

Chỉ chạy ba lệnh `fix-*` sau Wave C. Nếu branch/worktree cùng tên đã tồn tại,
Lead audit branch đó trước; không tái sử dụng mù hoặc xóa để tạo lại.

Auditor read-only nên dùng detached worktree để HEAD không đổi trong lúc chấm:

```bash
git worktree add --detach "$WORKTREE_ROOT/audit-whole-app" "$BASE_COMMIT"
git worktree add --detach "$WORKTREE_ROOT/audit-post-fix" "$BASE_COMMIT"
```

Mỗi auditor chỉ dùng một detached worktree phù hợp phase, không tạo cả hai cùng
lúc. Auditor chỉ được ghi evidence vào `generated_ho_so/_visual_layout/<wave>/`
hoặc `/tmp`; report tracked phải trả bản nháp cho Lead review.

### 6.3 Brief bắt buộc trước khi giao agent

Mỗi brief phải có đủ:

1. `BASE_COMMIT` và absolute worktree path;
2. một mục tiêu hữu hạn;
3. exact file ownership;
4. forbidden files/actions;
5. test/evidence gate;
6. format báo cáo cuối.

Format trả về:

```text
LANE:
BASE:
HEAD:
WORKTREE:
DIFF_ALLOWLIST:
COMMITS:
TESTS_PASS:
TESTS_FAIL:
TESTS_NOT_RUN:
EVIDENCE:
FINDINGS:
BLOCKERS:
GIT_STATUS:
```

### 6.4 Brief `coverage-agent` — Wave B

```text
Mục tiêu: tạo coverage matrix 111/111 section theo PLAN Wave B.

Ownership:
- tools/census/table_coverage_audit.py (mới)
- tests trực tiếp cho audit trên
- docs/table_coverage_current.md hoặc JSON generated tương ứng

Forbidden:
- app_web/ui/**, app_web/main.py
- tools/build_form_maps.py, tools/docx_to_blocks.py, tools/docx_render.py
- app/templates/**, app/data/blocks/**, form_maps*, manifest hiện hành
- không regenerate, không sửa production, không chạy full release runner

Gate:
- 111/111 section có một final status hợp lệ
- audit hai chiều manifest ↔ spec/form_maps/blocks/runtime/export
- override không resolve section_id làm test FAIL
- không tự đổi missing thành implemented nếu chưa có evidence xuyên pipeline
```

Lead review output, sửa generator census nếu cần, rồi mới regenerate/commit
manifest và coverage totals trên main.

### 6.5 Brief `whole-app-auditor` — Wave C

```text
Bạn là auditor read-only. Không sửa code/test/spec/generated và không commit.
BASE là commit coverage 111/111 đã được Lead cung cấp.

Quét 87/87 form, mọi use case và 5 variant M72 theo PLAN Wave C. Với mỗi form:
- seed dữ liệu đại diện cho mọi field/table kind;
- kiểm UI ở 1280/768/375 và zoom 100/150/200;
- kiểm add/delete/reorder/one-row/draft/validation;
- xuất DOCX/ZIP, render Word/PDF khi tooling có;
- ghi PASS/FAIL/NOT RUN, reproduction steps và evidence path.

Chỉ ghi:
- generated_ho_so/_visual_layout/whole_app_audit/**
- /tmp/whole_app_audit_*

Đầu ra:
- inventory.json đủ 87 form
- use_case_matrix.json
- bảng lỗi nhóm theo root-cause class
- top lỗi data-loss/blocking trước, cosmetic sau
```

Nếu browser/Word/WebView2 không có, ghi `NOT RUN`; không thay bằng suy luận từ
DOM hoặc ảnh cũ.

### 6.6 Coding lanes Wave D batch 1

#### `fix-industry`

Ownership độc quyền:

- `app_web/ui/app.js`
- `app_web/ui/form-domain.js`
- `app_web/test_industry_input_negative.js` và test trực tiếp liên quan

Forbidden:

- `render.js`, `style.css`, `tools/**`, templates/blocks/form_maps/manifest;
- không sửa test để chấp nhận literal `undefined`, `null`, `NaN` hoặc mã rác;
- không regenerate, merge, push hoặc chạy release runner.

Gate: test đỏ tái hiện trước; sau fix phủ legacy draft, autosave, add row, VSIC,
reload, primary selection và export payload cho mọi loop ngành.

#### `fix-extractor`

Ownership độc quyền:

- `tools/docx_to_blocks.py`
- extractor fixtures/tests mới;
- `tools/layout_roles.py` hoặc role override chỉ khi brief Lead cho phép rõ.

Forbidden:

- runtime UI, `docx_render.py`, build_form_maps, generated artifacts;
- không chạy global regen; chỉ sandbox output tạm.

Gate: footnote GLUE 23→0 trong sandbox, không xóa digit nội dung thật; newline
metric được giải thích bằng test; STT/digit-run có classification rõ.

#### `fix-docx-layout`

Ownership độc quyền:

- `tools/docx_render.py`
- `app_web/ui/render.js`
- `app_web/ui/style.css`
- signature/checkbox/layout tests mới

Forbidden:

- `app.js`, `form-domain.js`, extractor/generator, generated artifacts;
- không chữa bảng thiếu bằng CSS.

Gate: signature spacing, checkbox X inline, header band và page-break có red→green
tests; DOCX checked/unchecked đều được kiểm.

Nếu investigation chứng minh một fix cần file của lane khác, agent dừng và báo
`BLOCKER_OWNERSHIP`; Lead đổi ownership ở batch kế tiếp, không cho sửa chéo.

### 6.7 Coding lanes Wave D batch 2 — missing tables

Chỉ tạo sau coverage matrix và owner decisions. Chia theo domain thay vì loại
file, ví dụ:

- `fix-missing-people`;
- `fix-missing-capital-tax`;
- `fix-missing-admin-output`.

Mỗi lane chỉ sở hữu form-spec files và test sandbox của domain. Các file dùng
chung `build_form_maps.py`, runtime registry và generated artifacts vẫn do Lead
sở hữu. Nếu hai domain cần sửa cùng source file dùng chung, chạy tuần tự.

### 6.8 Merge SOP — chỉ Lead

Với từng lane:

1. đọc báo cáo lane và `git diff BASE..HEAD`;
2. xác minh không có file ngoài allowlist;
3. chạy targeted tests tại lane;
4. merge `--no-ff` tuần tự vào main;
5. chạy targeted tests ngay sau merge;
6. nếu source/spec/extractor đổi: Lead regenerate pipeline đầy đủ;
7. chạy generator lần hai, yêu cầu zero diff hoặc member-level classification;
8. refresh coverage/census/allowlist;
9. visual re-shoot form ảnh hưởng;
10. chạy full release runner, `compileall`, `git diff --check`;
11. commit ledger/report và yêu cầu `git status` sạch trước lane tiếp theo.

Không merge hai lane cùng lúc và không để agent tự merge vào main.

### 6.9 Dọn worktree an toàn

Chỉ Lead dọn sau khi xác nhận lane sạch và commit đã merge:

```bash
git -C "$WORKTREE_ROOT/fix-industry" status --short
git merge-base --is-ancestor agent/fix-industry main
git worktree remove "$WORKTREE_ROOT/fix-industry"
git branch -d agent/fix-industry
git worktree prune
```

Lặp lại với từng lane sau khi thay đúng tên. Nếu `status --short` có output hoặc
`merge-base --is-ancestor` trả non-zero, **không remove**; báo Lead phân loại.

### 6.10 Quy tắc bất biến

- Lead giữ main, là người duy nhất merge, regenerate global artifacts, cân
  allowlist và cập nhật ledger.
- Main bẩn chưa phân loại thì không spawn.
- Tối đa ba coding lane song song; không hai lane cùng sở hữu `app.js`,
  `render.js`, `form-domain.js`, `docx_to_blocks.py`, `build_form_maps.py`,
  `docx_render.py`.
- Worker không regenerate global, không chạy release runner, không push/merge.
- Không sửa tay `app/templates`, `app/data/blocks`, `form_maps` hoặc manifest.
- Targeted tests khi sửa; full runner tại checkpoint; visual pilot trước batch.
- Mỗi phase kết thúc bằng commit sạch và báo cáo delta, không kể lại toàn lịch sử.

## 7. Evidence contract

Mỗi checkpoint báo:

- base/HEAD/commits/worktree;
- exact diff allowlist;
- commands, exit codes, PASS/FAIL/NOT RUN;
- generator run 1 và run 2 zero-diff/member-level classification;
- coverage delta 111 section;
- screenshot/Word/PDF evidence path và tool version;
- blocker/owner decision;
- `git status` cuối.

Không được gọi visual, WebView2, Word/PDF hoặc Windows smoke là PASS nếu chưa chạy
thật trên HEAD hiện tại.

## 8. Điểm bắt đầu cho agent implement

Agent tiếp theo bắt đầu tại **Wave A**, không chạy lại lịch sử P0–P3. Sau Gate A,
thực hiện Wave B trước khi sửa bảng hàng loạt. Không được dùng con số 33
`missing_grid` hiện tại để chia lane cho tới khi coverage matrix 111/111 hoàn tất.
