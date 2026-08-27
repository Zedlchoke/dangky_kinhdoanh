# MASTER PLAN — hoàn thiện `dangky_kinhdoanh`

> **Checkpoint:** 2026-08-27, `main@7300ab4`.
>
> Đây là kế hoạch điều phối duy nhất cho thread mới. Không chạy lại prompt tại
> `0fd2785`, không làm lại P0/P1/R2 nếu không có regression thật. Trước khi làm,
> agent phải xác minh lại HEAD và trạng thái test vì checkpoint hiện tại đang có
> một batch R3B1 chưa commit.

## 1. Đích sản phẩm

Ứng dụng desktop cho phép chọn thủ tục đăng ký kinh doanh, nhập dữ liệu trực tiếp
trên biểu mẫu, dùng chung dữ liệu giữa các mẫu, khai các loại bảng, kiểm tra lỗi,
lưu/nhập draft và xuất DOCX/ZIP đúng cấu trúc pháp lý.

Sản phẩm được chia thành hai mốc:

### `CORE_APP_DONE`

Chỉ được công bố khi:

1. Mọi section trong 87 biểu mẫu có implementation hoặc blocker pháp lý được
   owner xác nhận; không tự đoán để xóa blocker.
2. Bốn loại bảng `editable-grid`, `fixed-matrix`, `nested-grid`, `output-table`
   hoạt động xuyên UI, draft, validation và DOCX.
3. Generator source/spec → template → `form_maps` → blocks chạy hai lần không tạo
   diff và không mất marker/format/rowspan/colspan/totals.
4. Mọi use case công bố qua E2E: chọn form, nhập, chuyển tab, lưu/mở/import,
   validation, DOCX/ZIP export và lỗi được điều hướng đúng.
5. Layout 87/87 qua detector, screenshot và auditor độc lập; không lấy DOM test
   thay cho visual evidence.
6. Keyboard-only, accessibility, viewport, resilience và security đạt gate.
7. Windows `.exe` build tái lập và smoke trên máy sạch không có Python.
8. Release runner không còn FAIL hoặc critical NOT RUN; repo sạch và final
   auditor read-only xác nhận PASS.

### `FULL_PRODUCT_DONE`

`CORE_APP_DONE` cộng thêm luồng Excel trong `PLAN_excel.md`, nhưng chỉ sau Review
Gate Excel và quyết định mở scope rõ ràng của owner. Khi chưa mở gate, Excel là
DRAFT và không chặn release core app.

## 2. Nguồn sự thật và phạm vi

Đọc theo thứ tự:

1. `PLAN.md` — trạng thái và thứ tự thực thi hiện hành.
2. `docs/execution_ledger.md` — commit/evidence lịch sử.
3. `docs/decision_registry.md` — lựa chọn owner và blocker còn thiếu.
4. `docs/product_scope_registry.md`.
5. `docs/p2_component_contracts.md`, `docs/p2_dependency_graph.md`,
   `docs/p2_fixture_candidates.md`.
6. `PLAN_excel.md` — chỉ đọc khi tới Review Gate Excel.
7. Source, tests và manifests tại HEAD — trọng tài cuối nếu docs cũ bị stale.

Trong scope core:

- `app_web/ui/*`, `app_web/main.py`, pywebview/WebView2.
- Draft, validation, shared keys, VSIC và bốn table kinds.
- `app/data/blocks`, use cases, `form_maps`, templates và DOCX/ZIP export.
- 87 biểu mẫu, visual QA, accessibility, Windows packaging và release audit.

Ngoài scope nếu chưa có quyết định mới:

- Không mở rộng `app_tk`; owner phải chọn `legacy-supported` hoặc `deprecated`.
- Không tự triển khai Excel trước Review Gate.
- Không tự sửa nội dung pháp lý thiếu nguồn.
- Không push/tag/release nếu owner chưa yêu cầu.

## 3. Đã hoàn thành — không làm lại

| Hạng mục | Trạng thái/evidence |
|---|---|
| P0 manifests | 87/87 form, 111 section, không còn signature unclassified |
| P1/P1.2 | industry grids và M72 selector/conditional export đã PASS; M72 chỉ xuất một variant |
| R0 | release runner, dependency contract, scope/decision registry đã có |
| Layout L1/L2 nền | blocks-v3, semantic roles/format, renderer/CSS structural đã merge |
| R2 runtime | bốn kind đã có dispatcher/runtime, draft, validation và fixtures |
| R2 generator/export | generator/export hỗ trợ kinds mới, recompute fail-loud và deep idempotency |
| R2 closure | output specs M70/M71 và formula `product()` parity JS/Python đã merge |
| R2 release checkpoint | từng đạt 38 PASS / 0 FAIL / 0 NOT RUN |
| Visual batch lần 1 | 123 PNG phủ 87 form; auditor độc lập đã chạy |
| Excel planning | `PLAN_excel.md` đã tồn tại dưới dạng DRAFT, review sau P4 |

Các commit chính đã có trong lịch sử; agent mới không cần kể lại hoặc tái tạo
chúng. Chỉ điều tra khi test hiện hành chứng minh regression.

## 4. Trạng thái thật tại checkpoint mới

### Git

- HEAD: `7300ab4`.
- Local hơn `origin/main` 50 commit tại thời điểm checkpoint; chưa push.
- Có nhiều worktree cũ; đa số lane đã merge. Không code tiếp trên branch cũ nếu
  chưa audit commit chưa merge.
- Main đang bẩn: 24 file tracked thuộc batch R3B1/regenerate và một `.DS_Store`.
  Đây chưa phải checkpoint có thể bàn giao sạch.

### Layout audit

Audit lần 1 đã PASS các gate allowlist, detector, release runner, DOM, screenshot
coverage, viewport và marker leak, nhưng **FAIL blocking** ở nội dung dòng chuẩn:

- Một số bảng people/ownership bị dẹt thành text glue.
- M72 có heading đánh số bị classifier gán `body`.
- Detector L1 trước đó chưa bắt đủ glue/digit-run/numbered-heading.

Hai vòng L1FIX đã merge tới `7300ab4`; cần regenerate/re-shoot và auditor tái
kiểm. Vì chưa có re-audit cuối, `LAYOUT_DONE = CHƯA`.

### R3B1 đang làm dở

Đã merge contracts/specs cho people/ownership và đăng ký N6/N7:

- `PLI_M02`: người đại diện/ủy quyền của chủ sở hữu.
- `PLI_M12`: người đại diện/ủy quyền sau thay đổi.
- `PLI_M15`: người đại diện/ủy quyền mới.
- Metadata hai nhóm thành viên hộ gia đình của `PLII_M02` đã có nhưng spec vẫn
  blocked theo evidence/legal contract.

Batch regenerate hiện tại đã làm thay đổi templates/blocks/form maps và tests,
nhưng chưa commit.

Targeted checks hiện tại:

- `test_r3b1_people_contracts.js`: 59 PASS / 0 FAIL.
- `test_runtime_tables.js`: 134 PASS / 0 FAIL.
- `test_r3b1_people_specs.py`: 10 PASS / **1 FAIL** tại trim-anchor `PLI_M02`.

Release runner hiện tại: **32 PASS / 6 FAIL / 0 NOT RUN**.

Sáu FAIL cần phân loại/sửa trước khi mở scope mới:

1. `test_acceptance`: kỳ vọng PLI_M02 chỉ có một loop đã stale.
2. `test_m72_activation`: dirty-worktree guard đang thấy batch chưa commit.
3. `test_audit_wave_h_negative`: exact diff allowlist chưa sync batch R3B1.
4. `test_nested_grid`: test còn tìm paragraph header cũ sau rebuild thành bảng.
5. `test_industry_change`: kỳ vọng PLI_M12 ba loop, hiện có bốn.
6. `build_manifest_deep`: summary counts của PLI_M02/M12/M15 chưa cập nhật.

Không mặc định coi tất cả là test stale: trim-anchor PLI_M02 phải kiểm tra production
shape trước, và mọi thay đổi expectation phải dựa vào contract/evidence.

## 5. Quyết định owner và blocker pháp lý

Các lựa chọn đã ghi nhận:

- D1: D1.1=A; D1.2=B cho M01; D1.3=B; D1.4=A; D1.5=B; D1.6=A.
- D2: D2.1–D2.6=A; D2.7 min=1/max=null; D2.8=A; D2.9=A.
- D3: D3.1=A; D3.2=A; D3.3=A.
- D4: D4.1=A; D4.2=A.
- D5: D5.1=A; D5.3=A; D5.4=A.
- D6: D6.2=A; D6.3=B; D6.5=A; D6.6 tên tài liệu required, trường khác optional.
- D7: D7.1=A; D7.2=A nếu có nguồn; D7.3=A; D7.4=A.

Blocker còn mở:

- D1/D3: thiếu nguồn gốc M03/M04/M05 và policy D1.2 ngoài M01.
- D5.2: thiếu canonical list chỉ tiêu thuế PLII_M02.
- D6.1: cần evidence per-form trước khi chọn grid/scalar.
- D6.4/M78: chưa có max/placeholder chính thức.
- N1/N6/N7: hai nhóm cột cuối về giá trị/thời điểm đại diện chưa đủ evidence để
  khóa canonical tag; phải khai thiếu, không mislabel.
- PLI_M15: cross-field rule giấy tờ theo chú thích nguồn chưa có contract v1.
- Product: `app_tk` chưa được owner phân loại cuối.

Blocker cục bộ không được làm dừng lane độc lập; giữ đúng section ở trạng thái
blocked và tiếp tục phần đã có quyết định.

## 6. Cách điều phối để tiết kiệm token

### Luật bắt buộc

- Lead giữ main và context tổng; sub-agent chỉ nhận một task hữu hạn cùng exact
  file ownership, forbidden files, gate và output format.
- Không spawn agent trong khi main đang bẩn chưa phân loại.
- Tối đa ba coding lane song song, chỉ khi không chồng file/dependency.
- Không giao nhiều agent cùng đọc/audit một tập file.
- Targeted tests trong lúc sửa; release runner đầy đủ chỉ tại checkpoint merge,
  trước regenerate và sau regenerate. Không chạy full visual 87 form sau mỗi sửa
  nhỏ; pilot form ảnh hưởng trước.
- Lead là người duy nhất merge, regenerate global artifacts, cập nhật manifest và
  ledger.
- Không dùng index block tuyệt đối nếu có semantic key/section ID/content anchor
  ổn định.
- Không chỉnh generated artifact bằng tay. Generator lần hai phải zero diff.
- Mỗi wave kết thúc bằng commit sạch. Không kéo work dở qua wave kế tiếp.
- Báo ngắn theo delta từ checkpoint; không kể lại toàn bộ lịch sử.
- PASS/FAIL/NOT RUN trung thực. Visual, WebView2 và `.exe` chỉ PASS khi chạy thật.

## 7. Kế hoạch thực thi từ bây giờ

### P0 — Recovery checkpoint R3B1 hiện tại

Lead mới tự làm; **không spawn agent** cho tới khi phân loại xong worktree.

1. Audit 24 modified files và `.DS_Store`; xác nhận toàn bộ thuộc batch R3B1,
   L1FIX regenerate hoặc thay đổi ngoài scope.
2. Không reset/revert. Lưu backup/quarantine nếu cần trước bất kỳ thao tác có thể
   ghi đè generated artifacts.
3. Điều tra trim-anchor PLI_M02 trên source template và template generated:
   - nếu production anchor/trim sai, sửa spec/generator;
   - nếu test đọc sai stage của pipeline, sửa test để kiểm đúng stage;
   - không nới thành “tìm thấy bất kỳ đâu”.
4. Đồng bộ năm test/manifest expectation còn stale theo semantic contract mới.
5. Chạy targeted tests R3B1, runtime, M72, industry, nested-grid và manifest.
6. Chạy generator lần hai; yêu cầu zero diff ngoài evidence file chủ đích.
7. Chạy release runner đầy đủ tới 0 FAIL.
8. Review exact allowlist, commit batch R3B1/regenerate/test sync thành các commit
   nhỏ hợp lý; cập nhật execution ledger.
9. Đảm bảo `git status` sạch và không còn sub-agent có commit chưa merge.

**Gate P0:** 0 FAIL, generator idempotent, worktree sạch, commit hash + evidence.
Nếu chưa đạt, không mở P1.

### P1 — Re-audit Layout và đóng R3B1

Sau P0, tạo một `visual-auditor` read-only, khác agent implement:

1. Pilot lại các form lỗi: PLI_M02, PLII_M02, PLI_M09, PLI_M12, PLI_M15, PLI_M72
   và các form bị role override round 2.
2. Kiểm bảng thật thay text glue, heading đúng role, không digit-run, không marker
   leak, M72 chỉ một variant.
3. Chụp 1280×800, 768, 375 và zoom 100/150/200 cho pilot.
4. Pilot PASS mới chạy batch evidence 87 form; reuse ảnh cũ chỉ khi hash input và
   renderer không đổi, nếu không phải chụp lại form bị ảnh hưởng.
5. Auditor ghi PASS/FAIL/NOT RUN từng gate. FAIL quay về lane sở hữu, không tự sửa.

**Gate P1:** `LAYOUT_DONE` chỉ khi detector + visual batch + auditor PASS.

### P2 — R3 domain rollout còn lại

Chỉ mở khi P0 sạch; P1 visual có thể chạy song song nếu read-only. Lead lập bảng
`form → section → source → decision → kind → keys → validation → export` trước
mỗi lane.

#### P2A — People/ownership phần còn lại

- Hoàn tất phần D2/D7 đủ evidence: PLII_M02/M07, PLI_M06–M10/M13/M15/M72.
- Không tự mở các section PLI_M09 còn source contamination hoặc M72 N2–N5 thiếu
  source/canonical tags.
- Thêm conditional/cross-field validation chỉ khi contract đã khóa.

#### P2B — Branches/admin/output

- Triển khai D4 và phần D6 đã quyết định.
- Lập evidence D6.1 theo từng form trước khi chọn grid/scalar.
- M78 dùng integer >=0 và required mô tả khi số lượng >0; không tự đặt max hoặc
  placeholder.

#### P2C — Capital/assets

- Triển khai phần D1/D3 có nguồn.
- M03/M04/M05 và policy ngoài M01 thiếu nguồn giữ block đúng section.
- Dùng formula `product()` đã có; không tự chế column projection/case policy nếu
  contract chưa khóa.

#### P2D — Tax

- Triển khai D5.1/D5.3/D5.4.
- PLII_M02 D5.2 tiếp tục `BLOCKED_LEGAL_REVIEW` tới khi owner cung cấp canonical
  list.

Các lane domain có thể dùng sub-agent song song khi file spec/forms không chồng;
Lead merge tuần tự, regenerate theo batch, targeted test rồi release runner.

**Gate P2:** mọi section có implementation hoặc blocker owner minh bạch; manifests
khớp recount; không mất dữ liệu/contamination/rule tự đoán.

### P3 — Hồ sơ end-to-end, accessibility, security và resilience

1. Test mọi use case: required/optional/oneOf forms và selector.
2. Nhập shared keys, bốn kinds, VSIC; chuyển tab không mất dữ liệu.
3. Save/reload/import legacy draft; giữ unknown fields, row IDs và thứ tự.
4. Validation điều hướng đúng form/field; lỗi blocking chặn export.
5. DOCX/ZIP không còn placeholder/tag và chỉ chứa section active.
6. Keyboard-only, focus order/restore, ARIA, contrast và zoom 200%.
7. Malformed/large draft, Unicode, đường dẫn dài, permission error, retry và
   offline behavior.
8. Escaping/injection/filename và log dữ liệu nhạy cảm.
9. Pywebview/WebView2 smoke thật; không có môi trường thì ghi NOT RUN.

**Gate P3:** core flow automated PASS và manual platform evidence đầy đủ.

### P4 — Review Gate Excel

Sau P2 + P3, Lead chỉ audit feasibility theo `PLAN_excel.md`, không implement ngay:

1. Đối chiếu questionnaire mapping với canonical keys/form maps ổn định.
2. Liệt kê thủ tục ưu tiên và câu hỏi đời thường cần owner duyệt.
3. Kiểm tra dependency/openpyxl, protection, dropdown và round-trip contract.
4. Báo effort/risk và xin owner lệnh rõ: `Bắt đầu Excel` hoặc `Để sau`.

Nếu owner chọn `Để sau`, Excel không chặn `CORE_APP_DONE`. Nếu owner chọn bắt đầu,
thực hiện chi tiết trong `PLAN_excel.md`: questionnaire layer → xuất XLSX theo
thủ tục → import fail-loud → remaining-fields report → round-trip/visual QA.

### P5 — Visual QA toàn diện

- UI screenshot matrix cho representative flows và mọi layout/table class.
- DOCX/PDF render bằng Word/LibreOffice hoặc renderer owner chấp thuận.
- Kiểm 87/87 hoặc sample policy được owner duyệt; mọi nested/fixed/output và M72
  conditional phải có visual evidence.
- So typography, spacing, page breaks, table geometry, superscript/footnote,
  presence/absence và marker leak.

### P6 — Windows build và clean-machine smoke

1. Khóa dependency, WebView2 policy, icon/version và reproducible build command.
2. Build `.exe`/bundle trên Windows.
3. Máy sạch không Python: mở app, chọn hồ sơ, nhập từng kind, save/reload/import,
   validate, export DOCX/ZIP và chạy offline.
4. Ghi exact artifact path, hash, size, OS/WebView2 version và verdict.

Không gọi macOS/Linux build hoặc compileall là Windows smoke.

### P7 — Final audit và bàn giao

Tạo auditor read-only mới, không dùng agent đã implement lane chính. Auditor đối
chiếu định nghĩa `CORE_APP_DONE`, manifests, decisions, release report, visual
evidence, package hash, docs và repo cleanliness. FAIL quay lại phase sở hữu.

Chỉ sau auditor PASS mới ghi `CORE_APP_DONE`. Nếu Excel đã được owner mở scope,
audit thêm `PLAN_excel.md` trước khi ghi `FULL_PRODUCT_DONE`.

## 8. Evidence contract cho mọi checkpoint

Mỗi báo cáo phải có:

- HEAD/base, branch/worktree và commit hash;
- exact diff allowlist, generated files và file ngoài allowlist;
- command, exit code, PASS/FAIL/NOT RUN;
- generator lần một + bằng chứng lần hai zero diff;
- visual evidence path/tool/version nếu đã chạy;
- blocker/rủi ro/quyết định owner;
- `git status` cuối.

Bộ gate tối thiểu: release runner hiện hành, relevant component/domain tests,
industry/DOCX/audit tests, `compileall`, manifests, generator deep idempotency,
M72 conditional export và `git diff --check`.

## 9. Prompt implement cho thread mới

```text
Bạn là Lead Engineer mới tiếp quản repo dangky_kinhdoanh. Mục tiêu là hoàn thiện
CORE_APP_DONE theo PLAN.md hiện tại, sau đó xử lý Review Gate Excel đúng policy.

Không dùng lịch sử hội thoại cũ làm nguồn sự thật. Đọc theo thứ tự:
1. PLAN.md;
2. docs/execution_ledger.md;
3. docs/decision_registry.md;
4. docs/product_scope_registry.md;
5. docs/p2_component_contracts.md, docs/p2_dependency_graph.md,
   docs/p2_fixture_candidates.md;
6. source/tests/manifests tại HEAD.
Chỉ đọc PLAN_excel.md khi tới P4 hoặc khi cần xác minh boundary Excel.

Checkpoint dự kiến là main@7300ab4 nhưng phải tự xác minh HEAD. Main đang có batch
R3B1 chưa commit: khoảng 24 modified files + .DS_Store; release gần nhất 32 PASS /
6 FAIL / 0 NOT RUN; targeted people contracts 59/59 PASS, runtime tables 134/134
PASS, people specs 10 PASS / 1 FAIL tại trim-anchor PLI_M02.

Nhiệm vụ đầu tiên là P0 Recovery trong PLAN. KHÔNG spawn agent, KHÔNG mở scope
mới và KHÔNG reset/revert/clean trước khi phân loại toàn bộ dirty files. Kiểm tra
trim-anchor PLI_M02 trên đúng stage source/template/generated; sửa production hoặc
test theo evidence, không nới test. Đồng bộ các expectation stale của acceptance,
M72 dirty guard, audit allowlist, nested-grid, industry-change và manifest recount.
Đưa release runner về 0 FAIL, chạy generator lần hai zero diff, review allowlist,
commit sạch và cập nhật execution ledger. Dừng mở phase mới nếu P0 chưa PASS.

Sau P0, tiếp tục tuần tự P1→P7 trong PLAN. Hãy tạo sub-agent/worktree để tối ưu
thời gian chỉ cho task độc lập:
- visual-auditor read-only cho P1;
- tối đa ba domain lane không chồng file trong P2;
- auditor read-only ở P7.
Trước khi spawn, giao base commit, exact file ownership, forbidden files, gate và
format báo cáo. Lead giữ main, review/merge tuần tự và là người duy nhất regenerate
global artifacts. Không tiếp tục branch/worktree cũ nếu chưa audit commit chưa merge.

Không làm lại P0/P1/R2 lịch sử khi không có regression. Không tự đoán nội dung
pháp lý; isolate blocker D1/D3, D5.2, D6.1, D6.4, N1/N6/N7 và tiếp tục phần độc lập.
Không implement Excel trước P4 và lệnh owner rõ ràng. Không push/tag/release.

Để tiết kiệm token:
- báo cáo theo delta từ checkpoint, không kể lại toàn bộ lịch sử;
- targeted tests trong lúc sửa, full runner tại checkpoint;
- pilot visual form bị ảnh hưởng trước, batch 87 form tại gate;
- không để hai agent đọc/sửa cùng scope;
- mỗi phase phải kết thúc bằng commit sạch trước khi mở phase sau.

Cuối mỗi checkpoint báo ngắn nhưng kiểm chứng được: HEAD/commits, exact diff,
tests PASS/FAIL/NOT RUN, generator idempotency, visual evidence, blockers và git
status. Chỉ ghi CORE_APP_DONE/FULL_PRODUCT_DONE khi mọi điều kiện trong PLAN đạt.
```
