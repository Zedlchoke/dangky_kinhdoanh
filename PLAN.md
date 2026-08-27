# MASTER PLAN — hoàn thiện `dangky_kinhdoanh`

> **Checkpoint lập kế hoạch:** 2026-08-27, `main@0fd2785`.
>
> Đây là kế hoạch **duy nhất đang có hiệu lực** cho agent mới. Các checkpoint và
> prompt cũ đã được thay thế. Agent phải xác minh lại Git/test khi bắt đầu vì HEAD
> có thể đã thay đổi sau checkpoint này.

## 1. Mục tiêu và định nghĩa hoàn tất

Hoàn thiện ứng dụng desktop khai hồ sơ đăng ký kinh doanh trực tiếp trên biểu
mẫu, gồm UI web/pywebview, draft JSON, validation, các loại bảng, đồng bộ dữ
liệu, xuất DOCX/ZIP, độ trung thành hình thức, accessibility và bản phát hành
Windows.

Chỉ được báo `APP_DONE` khi đồng thời:

1. Layout 87/87 biểu mẫu đạt gate cấu trúc **và** visual; không lấy test DOM thay
   cho ảnh render thật.
2. `editable-grid`, `output-table`, `fixed-matrix`, `nested-grid` đã nối vào
   runtime UI, draft, validation và DOCX; fixture production của từng loại PASS.
3. Generator source/spec → template → `form_maps` → blocks chạy hai lần không
   tạo diff và không mất marker/format/rowspan/colspan/totals.
4. Mọi section trong manifest có implementation hoặc quyết định cuối của owner;
   không còn `BLOCKED_LEGAL_REVIEW` bị che giấu hoặc tự suy đoán.
5. Tất cả use case công bố chọn đúng forms, draft round-trip không mất dữ liệu,
   validation điều hướng đúng và export không rò placeholder/tag.
6. Keyboard-only, accessibility, viewport release và resilience đạt gate.
7. UI và DOCX/PDF có visual evidence; nested-grid được kiểm trực quan.
8. Windows `.exe` được build tái lập và smoke trên máy sạch không có Python.
9. Release runner không có FAIL hay critical NOT RUN; repo sạch, tài liệu build,
   version và checklist đầy đủ.
10. Auditor độc lập read-only xác nhận PASS. Push/tag/release chỉ khi owner yêu
    cầu rõ ràng.

Không dùng phần trăm hoàn thành hoặc tổng số test lớn để thay thế các gate trên.

## 2. Phạm vi và nguồn sự thật

### Trong scope

- UI chính: `app_web/ui/index.html`, `app_web/ui/app.js`,
  `app_web/ui/render.js`, `app_web/ui/form-domain.js`, `app_web/ui/style.css`.
- Desktop bridge: `app_web/main.py` + pywebview/WebView2.
- Schema/runtime data: `app/data/blocks/*.json`, `app/data/use_cases.json`,
  `app/data/form_maps.json` và bản JS tương ứng.
- Pipeline DOCX: source/spec, templates, converter/generator, export DOCX/ZIP.
- 87 biểu mẫu thuộc table/layout manifest và mọi use case đang công bố.
- Test, visual evidence, Windows packaging và release audit.

### Ngoài scope nếu chưa có quyết định mới

- `PLAN_excel.md` không tồn tại tại checkpoint. Excel không thuộc release này;
  muốn thêm phải có contract/roadmap riêng.
- `app_tk` chỉ compatibility với engine dùng chung. Owner vẫn phải chọn
  `legacy-supported` hoặc `deprecated`; không tự mở rộng Tk UI.
- Không thay đổi nội dung pháp lý chỉ để làm test xanh.

### Tài liệu phải đọc trước khi sửa code

1. `PLAN.md` — tài liệu này.
2. `docs/execution_ledger.md` — evidence/commit đã chạy.
3. `docs/decision_registry.md` — quyết định owner và phần còn thiếu.
4. `docs/product_scope_registry.md`.
5. `docs/p2_component_contracts.md`, `docs/p2_dependency_graph.md`,
   `docs/p2_fixture_candidates.md`.
6. `docs/legal_review_backlog.md` khi đụng nội dung pháp lý.

Nếu tài liệu cũ mâu thuẫn trạng thái ở mục 3 dưới đây, kiểm tra source/test/commit
và cập nhật tài liệu; không lùi production về checkpoint cũ.

## 3. Hiện trạng đã xác minh tại `0fd2785`

### Git và release baseline

- Branch: `main`; local hơn `origin/main` 4 commit tại thời điểm kiểm tra; chưa
  push.
- Release runner: **34 PASS / 0 FAIL / 0 NOT RUN**.
- Các worktree/branch cũ còn tồn tại; chúng chứa commit đã merge hoặc checkpoint
  cũ. Không tiếp tục code mù trên chúng. Lead phải audit rồi reuse hoặc dọn sau
  khi chắc chắn không có commit chưa merge.
- Không chạy generator với `--help` nếu script không khai báo CLI help; trước mọi
  generator run phải kiểm tra parser/source và có worktree sạch.

### Những phần đã xong — không làm lại từ đầu

| Hạng mục | Trạng thái/evidence |
|---|---|
| P0 table manifest | 87/87 form, 111 section, signature đã classify |
| L0 layout manifest | 87/87 form |
| P1 industry | M72 đủ 5 occurrence; PLII_M02 có 4 semantic loop riêng |
| P1.2 M72 | selector `dn.loai_hinh`; UI/DOCX chỉ đúng một variant; verifier và conditional export PASS |
| R0 baseline | verifier PLII_M02 cũ đã triage; release runner/dependency/scope registries có sẵn |
| R1.1 extractor | blocks-v3 đã merge/regenerate 87/87; 0 role thiếu, 0 marker leak, idempotency PASS |
| R1.2 renderer | L2 structural/DOM PASS; merge `1aaa6c5`; release machinery `5e1e08f` |
| Editable grid | module/runtime nền đã merge `b169c4b` |
| Output table | module + production fixture/test đã merge `0e25d93` |
| Fixed matrix | module + production fixture/test đã merge `5e3381b` |
| Nested grid | module + production fixture/test đã merge `bc8cbb4` |
| Draft migration | additive, idempotent, giữ unknown fields; merge `48fd3e2` |

### Việc còn thật sự mở

1. **R1 visual:** structural PASS nhưng screenshot/visual browser vẫn `NOT RUN`.
   Chưa được gọi P1-LAYOUT hoàn tất.
2. **R2 runtime wiring:** `output-table.js`, `fixed-matrix.js`,
   `nested-grid.js` hiện là module/test độc lập; chưa có reference production rõ
   trong `index.html`, `app.js`, `render.js`, `form-domain.js` hoặc bridge.
3. **R2 generator/export:** chưa chứng minh đủ anchor, boundary, occurrence,
   rowspan/colspan, totals, conditional presence và deep idempotency cho ba kind
   mới.
4. **P2 docs:** header đã khóa v1 nhưng một số đoạn thân còn ghi DRAFT/NOT
   IMPLEMENTED; phải rebase theo source hiện tại, không sửa contract ngầm.
5. **R3 rollout nghiệp vụ:** chỉ mở phần đã có quyết định; giữ block phần thiếu
   nguồn/canonical list.
6. **R4–R7:** E2E, accessibility/resilience, visual toàn diện, Windows package,
   clean-machine smoke và final audit chưa hoàn tất.

## 4. Quyết định owner đã có và blocker còn lại

Owner đã chọn bundle sau; agent phải triển khai đúng lựa chọn, không hỏi lại nếu
evidence hiện tại không mâu thuẫn:

- D1: D1.1=A; D1.2=B cho M01; D1.3=B; D1.4=A; D1.5=B; D1.6=A.
- D2: D2.1–D2.6=A; D2.7 min=1/max=null; D2.8=A; D2.9=A.
- D3: D3.1=A; D3.2=A; D3.3=A.
- D4: D4.1=A; D4.2=A.
- D5: D5.1=A; D5.3=A; D5.4=A.
- D6: D6.2=A; D6.3=B; D6.5=A; D6.6 tên tài liệu required, trường khác optional.
- D7: D7.1=A; D7.2=A nếu có nguồn đối chiếu; D7.3=A; D7.4=A.

Các packet chưa được đóng hoàn toàn:

- **D1/D3:** cần nguồn gốc M03/M04/M05 và policy D1.2 cho các form ngoài M01.
- **D5.2:** chưa có canonical list chỉ tiêu thuế PLII_M02; section giữ
  `BLOCKED_LEGAL_REVIEW`.
- **D6.1:** phải lập bảng evidence theo từng form trước khi chọn grid/scalar.
- **D6.4/M78:** đã chốt integer >=0 và mô tả “Sản phẩm khác” required khi SL>0,
  nhưng chưa có max/placeholder chính thức; không tự đặt giới hạn.
- **Product:** owner chưa chốt `app_tk` legacy hay deprecated.

D2, D4, D7 và phần kỹ thuật D6 đã đủ quyết định có thể triển khai. Một blocker
không được làm dừng toàn bộ app: isolate đúng section/form và tiếp tục lane độc
lập có evidence.

## 5. Mô hình điều phối bắt buộc cho Lead Agent

Lead phải dùng sub-agent/worktree để giảm thời gian, nhưng chỉ song song hóa việc
không chồng file hoặc dependency. Tối đa số lane phù hợp với concurrency thực tế;
không spawn agent chỉ để đọc cùng một việc.

### Quy tắc chung

- Lead giữ `main` làm integration worktree và là người duy nhất merge, regenerate
  global artifacts, cập nhật ledger và chạy release gate sau merge.
- Mỗi lane: branch + worktree riêng ngoài repo, allowlist file rõ, commit nhỏ,
  báo hash + test + PASS/FAIL/NOT RUN.
- Không cho hai lane đồng thời sở hữu `app.js`, `render.js`, `form-domain.js`,
  `style.css`, `docx_to_blocks.py`, `build_form_maps.py` hoặc `docx_render.py`.
- Không chỉnh tay generated artifacts. Sub-agent sửa source/spec/test; Lead
  regenerate một lần sau khi merge và chạy lần hai để chứng minh zero diff.
- Không reset/revert/clean/pull mù; không ghi đè thay đổi chưa rõ chủ sở hữu; không
  push/tag/release nếu owner chưa yêu cầu.
- Mỗi agent phải tự đọc file instruction/contract liên quan, inspect source trước
  khi sửa và giữ `git diff --check` xanh.
- Agent audit/visual là read-only với production code; phát hiện lỗi thì trả
  evidence cho lane sở hữu, không tự vá ngoài allowlist.

## 6. Lộ trình thực thi từ checkpoint hiện tại

### Wave A — Rebaseline và khóa integration surface

Lead tự thực hiện, không giao agent:

1. Xác minh `git status`, `HEAD`, divergence, `git worktree list`, commit chưa
   merge và thay đổi chưa rõ chủ sở hữu. Dừng nếu worktree bẩn không phân loại.
2. Chạy `python -m tools.release_runner --json-out <tmp-file>` hoặc CLI đúng theo
   source hiện tại. Baseline phải không thấp hơn 34 suite trừ khi runner được thay
   đổi có giải thích.
3. Inspect production imports/references của ba module mới, bridge export và
   generator. Ghi call graph ngắn vào execution ledger.
4. Rebase nội dung ba tài liệu P2 về trạng thái thật; không đổi contract v1 nếu
   chưa có evidence buộc đổi.
5. Tạo branch/worktree mới cho các lane dưới; không dùng branch đã merge nếu chưa
   audit sạch.

**Gate A:** worktree integration sạch; baseline tái lập; ownership map và thứ tự
merge được ghi rõ.

### Wave B — ba lane chạy song song

#### Lane B1 — runtime wiring

Mục tiêu: nối `output-table`, `fixed-matrix`, `nested-grid` vào UI/controller và
draft/validation mà không phá editable-grid/M72.

Ownership dự kiến:

- `app_web/ui/index.html`
- `app_web/ui/app.js`
- `app_web/ui/render.js`
- `app_web/ui/form-domain.js` chỉ khi integration bắt buộc
- test integration runtime mới

Yêu cầu:

- Dùng module hiện có, không viết lại component.
- Có dispatcher theo `section.kind`; fallback cũ chỉ cho schema legacy đã
  classify, không nuốt kind mới.
- Stable IDs/keys, keyboard navigation, focus, add/remove, computed/output-only,
  validation và draft round-trip đúng contract.
- Production fixtures tối thiểu: O1/O2, F2/F3 và N1 theo tài liệu candidates.
- Test isolation M72 và editable-grid vẫn PASS.

#### Lane B2 — generator + DOCX/export

Mục tiêu: hỗ trợ ba kind mới xuyên pipeline và chứng minh output cấu trúc.

Ownership dự kiến:

- `tools/build_form_maps.py`
- `tools/docx_to_blocks.py`
- `tools/docx_render.py`/engine export liên quan
- schema/spec contract và test generator/DOCX mới
- không commit bulk generated artifacts

Yêu cầu:

- Anchor/boundary/occurrence tường minh; không match heading mơ hồ.
- Giữ multi-row header, rowspan/colspan, physical column count, totals,
  output-only/conditional presence và nested discriminator/group.
- Negative mutation phải bắt thiếu/thừa/đảo marker, contamination và sai
  boundary.
- Có deep idempotency test; generator lần hai không thay semantic/hash đã định.
- M72 tiếp tục export đúng một variant.

#### Lane B3 — QA/contract/audit tooling

Mục tiêu: độc lập tạo gate bắt integration sai, không sửa production runtime hay
generator.

Ownership dự kiến:

- test/fixture QA mới
- `tools/release_runner.py`
- allowlist audit liên quan
- tài liệu P2/execution ledger đề xuất; Lead quyết định merge docs cuối

Yêu cầu:

- Test production fixture theo cả UI và DOCX shape.
- Test draft migration từ schema cũ, unknown-field preservation, round-trip và
  idempotency.
- Gate không cho module “PASS độc lập” bị hiểu nhầm là runtime hoàn tất.
- Ghi đúng PASS/FAIL/NOT RUN; không sửa production để chiều test.

### Wave C — Lead integration và regenerate

Thứ tự mặc định: **B3 test contract → B2 generator → B1 runtime**, nhưng Lead
được đổi thứ tự nếu dependency thực tế yêu cầu và phải ghi lý do. Không merge
một lane có contract khác với source đã khóa.

1. Review từng commit theo allowlist; cherry-pick/merge tuần tự.
2. Chạy test lane ngay sau mỗi merge.
3. Sau khi source/spec hoàn tất, Lead mới regenerate toàn bộ artifacts.
4. Review exact diff manifest; chạy generator lần hai; lần hai phải zero diff.
5. Chạy release runner, compileall, census/audit/DOCX negative tests và M72
   conditional export.
6. Render/inspect DOCX production của từng kind, chứng minh cả presence và absence
   đúng điều kiện.

**Gate R2:** bốn kind hoạt động thật trong runtime + draft + validation + DOCX;
generator deep-idempotent; release regression xanh. Chỉ khi đó mới ghi R2 PASS.

### Wave D — visual P1-LAYOUT, chạy độc lập với phần không chồng R2

Ngay khi có browser/render tooling, Lead tạo agent `visual-auditor` read-only:

1. Pilot biểu mẫu đại diện có newline, superscript/footnote, source indicator,
   fixed/nested/output/editable grid và M72 variant.
2. Chụp 1280x800, 768px, 375px; zoom 100%, 150%, 200%; kiểm keyboard focus,
   overflow, footer/panel che nội dung và marker leak.
3. Với DOCX, render PDF/PNG bằng LibreOffice/Word hoặc renderer đã được owner
   chấp thuận; lưu command, tool version và ảnh evidence.
4. Nếu tooling không có, ghi `NOT RUN`; tuyệt đối không suy ra visual PASS từ DOM.
5. Sau pilot PASS mới chia batch 87 form; auditor xác nhận độc lập.

**Gate R1:** detector/DOM + screenshot evidence 87/87 + auditor PASS.

### Wave E — R3 domain rollout

Chỉ mở sau R2 PASS; các lane domain có thể song song nếu file ownership không
chồng. Mỗi lane bắt đầu bằng evidence table `form → section → source → decision →
kind → keys → validation → export`.

1. **People/ownership:** D2 + phần D7 đủ evidence; PLII_M02/M07,
   PLI_M06–M10/M13/M15/M72. Không tự mở tax section D5.2.
2. **Branches/admin/output:** D4 + phần D6 đã quyết định. Lập evidence D6.1 trước;
   M78 triển khai rule đã chốt nhưng không tự đặt max/placeholder.
3. **Capital/assets:** chỉ phần D1/D3 có source. M03/M04/M05 hoặc policy ngoài
   M01 thiếu nguồn tiếp tục block đúng section.
4. **Tax:** triển khai D5.1/D5.3/D5.4; PLII_M02 D5.2 giữ block tới khi owner cung
   cấp canonical list.

Lead merge từng domain tuần tự, regenerate một lần mỗi batch, chạy release runner
và cập nhật manifest/blocker counts. Không dùng bulk heuristic để “xóa blocker”.

**Gate R3:** mọi section có implementation hoặc blocker owner minh bạch; không có
data loss, contamination hay rule pháp lý tự đoán.

### Wave F — R4 E2E, accessibility, security và resilience

- Test mọi use case: required/optional/oneOf forms, shared key, switch form,
  save/reload/import draft, validation, DOCX/ZIP export.
- Test keyboard-only, focus order/restore, `aria-*`, 200% zoom, contrast và screen
  reader smoke phù hợp tooling.
- Test malformed/legacy draft, unknown field, large nested grids, Unicode, đường
  dẫn dài, file permission lỗi, export retry và offline mode.
- Kiểm tra escaping/injection ở UI/DOCX/filename; không log dữ liệu nhạy cảm.
- WebView2/pywebview smoke phải chạy thật mới ghi PASS.

### Wave G — R5 visual QA toàn diện

- UI screenshot matrix cho representative flows và mọi layout/table class.
- DOCX/PDF render 87/87 hoặc sample policy đã được owner phê duyệt; ưu tiên toàn
  bộ nested/fixed/output và variant conditional.
- So với source/reference theo typography, spacing, page breaks, table geometry,
  superscript/footnote và absence/presence.
- Lỗi visual quay về lane sở hữu; sửa xong phải rerender evidence.

### Wave H — R6 Windows release

- Khóa Python/Node/build dependencies, WebView2 runtime policy, icon/version và
  reproducible build command.
- Build `.exe`/bundle trên Windows; không gọi artifact macOS/Linux là Windows
  smoke.
- Máy Windows sạch không Python: mở app, chọn hồ sơ, nhập bảng mỗi kind, save,
  reload, import legacy draft, validate, export DOCX/ZIP, chạy offline.
- Ghi hash, kích thước, exact path, OS/WebView2 version và PASS/FAIL/NOT RUN.

### Wave I — R7 audit và bàn giao

Tạo auditor mới read-only, không dùng agent đã implement lane chính. Auditor đối
chiếu `APP_DONE`, manifests, decision registry, release report, ảnh evidence,
package hash và repo cleanliness. Mọi FAIL quay về wave sở hữu. Chỉ sau auditor
PASS mới cập nhật `APP_DONE`; vẫn không push/tag/release nếu owner chưa yêu cầu.

## 7. Test/evidence contract

Mỗi báo cáo wave phải có:

- branch/worktree, commit hash, base hash;
- exact diff allowlist và file ngoài allowlist (nếu có);
- command + exit code + số PASS/FAIL/NOT RUN;
- generated diff lần một và zero diff lần hai;
- ảnh/visual evidence path nếu đã chạy;
- blocker, rủi ro và quyết định owner cần thêm;
- trạng thái rõ `PASS`, `FAIL` hoặc `NOT RUN`.

Bộ gate tối thiểu gồm release runner hiện hành, test component/integration mới,
Python tests industry/DOCX/audit, `compileall`, manifest gate, generator deep
idempotency và M72 conditional export. Agent phải đọc `tools/release_runner.py`
để dùng đúng CLI thay vì đoán lệnh.

Không được ghi PASS cho visual QA, WebView2 hoặc `.exe` smoke nếu chưa chạy thật.

## 8. Prompt khởi động cho Lead Agent mới

Sao chép nguyên khối dưới đây cho agent mới:

```text
Bạn là Lead Engineer chịu trách nhiệm hoàn thiện repo dangky_kinhdoanh đến
APP_DONE.

Nguồn điều phối duy nhất là PLAN.md hiện tại. Trước khi làm, đọc trọn PLAN.md,
docs/execution_ledger.md, docs/decision_registry.md,
docs/product_scope_registry.md, docs/p2_component_contracts.md,
docs/p2_dependency_graph.md và docs/p2_fixture_candidates.md. Sau đó inspect
source/test; không tin trạng thái cũ nếu không khớp code.

Bắt đầu bằng Wave A: audit git status/HEAD/divergence/worktrees, phân loại mọi
dirty file, chạy release baseline và xác minh production wiring của
output-table/fixed-matrix/nested-grid. Không reset/revert/clean thay đổi chưa rõ
chủ sở hữu; không push.

Sau khi baseline sạch, hãy chủ động tạo các sub-agent/worktree độc lập để tối ưu
thời gian theo PLAN:
- B1 runtime wiring;
- B2 generator + DOCX/export;
- B3 QA/contract/audit tooling.

Trước khi spawn, giao cho mỗi agent base commit, branch/worktree, mục tiêu, exact
file ownership, forbidden files, test gate và format báo cáo. Không để hai agent
sửa cùng file. Lead giữ main, review/merge tuần tự và là người duy nhất regenerate
global artifacts. Khi có browser/render tooling, tạo thêm visual-auditor read-only
cho Wave D; công việc visual có thể chạy song song nếu không chồng file.

Không viết lại bốn component đã merge. Mục tiêu gần nhất là đưa ba module mới vào
runtime + generator/export, chứng minh production fixture, migration và deep
idempotency. Giữ M72 chỉ xuất đúng một variant. Không tự đoán nội dung pháp lý;
isolate đúng blocker D1/D3, D5.2, D6.1, D6.4 và tiếp tục phần đã có quyết định.

Sau mỗi merge: chạy test lane, release runner và git diff --check. Sau thay đổi
source/spec: regenerate một lần, review exact allowlist, chạy lần hai phải zero
diff. Ghi PASS/FAIL/NOT RUN trung thực; visual, WebView2 và Windows .exe không
được PASS nếu chưa chạy.

Tiếp tục lần lượt Wave C→I tới khi APP_DONE hoặc gặp blocker cần authority/source
từ owner. Nếu blocker chỉ ảnh hưởng một section, không dừng các lane độc lập.
Cuối mỗi wave cập nhật execution ledger và báo commit, diff, tests, visual
evidence, rủi ro, blockers và bước tiếp theo. Không tự push/tag/release.
```

## 9. Điểm bắt đầu ngay bây giờ

Agent mới không quay lại P0/P1 hay viết thêm một “master plan” khác. Việc đầu tiên
sau rebaseline là mở Wave B, với mục tiêu gần nhất:

> **R2 production integration:** nối ba module bảng đã merge vào runtime và
> DOCX/generator, bổ sung gate integration + deep idempotency, giữ release runner
> xanh; đồng thời chạy visual auditor R1 nếu tooling khả dụng.
