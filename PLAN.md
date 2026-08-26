# Kế hoạch: giao diện khai trực tiếp kiểu HTKK

## Mục tiêu

Chuyển giao diện web desktop hiện có thành trải nghiệm **khai trực tiếp trên mẫu** lấy cảm hứng từ HTKK: mỗi mẫu biểu là một tab, người dùng điền vào các ô ngay trong mẫu, dữ liệu chung tự đồng bộ giữa các mẫu, có kiểm tra lỗi và xuất DOCX như hiện nay.

Không sao chép nguyên xi thương hiệu hay tài sản giao diện HTKK. Mục tiêu là cách thao tác và độ rõ ràng: khung desktop, bảng kê có ô nhập liệu, tab mẫu, thanh lệnh và phản hồi kiểm tra.

## Hiện trạng đã xác nhận

- UI web là hướng triển khai chính: `app_web/ui/index.html`, `app_web/ui/app.js`, `app_web/ui/render.js`, `app_web/ui/style.css`; đóng gói desktop bằng `app_web/main.py` + pywebview.
- Dữ liệu mẫu đã ở dạng schema: `app/data/blocks/*.json`. Danh mục thủ tục nằm ở `app/data/use_cases.json`; map xuất DOCX ở `app/data/form_maps.json`.
- Kho dữ liệu trung tâm `state.store` hiện đã đồng bộ được các ô có cùng `data-key`, hỗ trợ bảng lặp, VSIC, tự cộng vốn, tự lưu JSON và xuất DOCX.
- Điểm cần thay đổi: trung tâm đang hiển thị liên tiếp tất cả trang A4; tab dưới chỉ cuộn đến trang. Chưa có metadata kiểu/điều kiện bắt buộc cho field, validation tập trung, điều hướng lỗi, hay hỗ trợ bàn phím/accessibility đầy đủ.

## Quyết định kiến trúc

1. Giữ nguyên Python bridge và engine DOCX. Đây là thay đổi trải nghiệm nhập liệu, không đổi template, `form_maps.json` hay contract export.
2. Dùng HTML/CSS tương tác để giả lập tờ khai (không dựng PDF/canvas). Nó giữ được ô nhập, bàn phím, accessibility và tái sử dụng trực tiếp schema blocks hiện có.
3. `data-key` là canonical key duy nhất để đồng bộ. Hai ô có cùng key phải cùng giá trị; key khác nhau không tự gộp chỉ vì nhãn giống nhau. Nếu phát hiện cần gộp, bổ sung alias tường minh vào metadata sau khi rà soát nghiệp vụ.
4. Thêm dần `fieldMeta` theo key, tách khỏi dữ liệu pháp lý của mẫu: `type`, `label`, `required`, `pattern`, `inputMode`, `help`, `readonly/computed`, `options`, validation/rule. Không đổi key cũ.
5. Chỉ render **một mẫu đang active** trong viewport. State bổ sung `activeDocId`, `dirty`, `validation`, `selectedLoopRow`, `viewState`; khi đổi tab phải giữ dữ liệu, scroll và focus.
6. Pilot trước trên `PLI_M02` và `PLI_M06` (có field chung và bảng lặp), sau khi đạt tiêu chí mới mở rộng mặc định cho toàn bộ block schema.

## Trải nghiệm đích (MVP)

- Màn hình desktop (>= 1024px): header gọn có tên thủ tục/trạng thái lưu; navigator trái có nhóm, thủ tục, checklist mẫu và trạng thái; viewport trung tâm nền xám chứa tờ khai active; panel phải co/mở cho hướng dẫn và lỗi.
- Mỗi ô nhập có viền tối 1px, giá trị xanh, focus rõ. Ô tự tính/khóa nền xanh nhạt và có chỉ dấu chỉ đọc. Văn bản và lưới mẫu giữ hình học hiện hữu.
- Thanh đáy: tab cho từng mẫu, badge lỗi/chưa lưu và lệnh `Thêm dòng`, `Nhập lại`, `Kiểm tra`, `Lưu`, `In/PDF` (nếu thực hiện), `Xuất DOCX`, `Nhập JSON`, `Đóng`. Các lệnh chưa có backend phải ẩn hoặc disabled kèm lý do, không làm nút giả.
- `Kiểm tra` kiểm tra form hiện tại/toàn bộ hồ sơ, nhóm lỗi theo mẫu ở panel phải. Bấm lỗi sẽ mở đúng tab, cuộn và focus ô lỗi.
- VSIC hỗ trợ click lẫn Up/Down/Enter/Escape. Bảng lặp thêm dòng, chọn/xóa dòng; xóa dòng có dữ liệu cần xác nhận.
- `Ctrl+S` lưu, `Ctrl+PageUp/PageDown` đổi mẫu, `Esc` đóng popup. Điều hướng Tab theo thứ tự ô trên mẫu.
- Tablet/mobile là chế độ hỗ trợ: panel thành drawer, bảng giữ chiều ngang và cuộn ngang; không reflow phá vỡ bảng pháp lý. Khuyến nghị màn hình >= 1024px khi mẫu dày.

## Kế hoạch thực hiện và giao song song

### Giai đoạn 0 — chốt contract (Agent lead, tuần tự; 0.5–1 ngày)

Deliverable: `docs/htkk-ui-contract.md` (hoặc tài liệu thiết kế tương đương), mock HTML/CSS của `PLI_M02`, và danh sách key pilot.

- Chốt model `fieldMeta`, cấu trúc lỗi `{key, docId, code, message, severity}`, `activeDocId`, API validate và action IDs.
- Rà `PLI_M02`, `PLI_M06`: key dùng chung, key riêng, field bắt buộc/định dạng, bảng lặp và quy tắc tổng vốn.
- Chốt chính sách MVP: lỗi blocking không cho xuất DOCX; thao tác đổi case/nhập lại khi dirty phải hỏi xác nhận.
- Gate: Agent A/B/C/D chỉ bắt đầu sửa code sau khi contract được duyệt. Không sửa bulk các file block trong pilot.

### Giai đoạn 1 — bốn nhánh chạy song song (2–4 ngày)

| Agent | Phạm vi sở hữu | File chính | Điều kiện hoàn tất |
| --- | --- | --- | --- |
| A — domain/validation | `fieldMeta`, validator thuần, parse/format tiền, rule required/pattern/cross-field; unit test | mới `app_web/ui/form-domain.js`, metadata pilot, `test_domain.js` | Không DOM; test chạy độc lập; không đổi export contract |
| B — renderer/UI | Shell desktop, semantics ARIA, renderer nhận metadata, CSS HTKK-like, tabpanel | `index.html`, `style.css`, `render.js` | Render được PLI_M02/M06, label/id ổn định, 200% zoom và focus rõ |
| C — controller/state | Một tab active, mirror canonical key, dirty/autosave, focus/scroll restore, VSIC keyboard, loop selection | `app.js` | Tab không mất data; đổi mẫu, save/reload và sync shared key đều đúng |
| D — QA/integration safety | Test plan, mock pilot, DOM tests và smoke pywebview/export; đo lỗi/hồi quy | `test_dom.js`, mới test, `tools/*` nếu cần | Test tái lập được và không ghi đè data/template hiện hữu |

Nguyên tắc để tránh xung đột: A chỉ sở hữu domain/metadata; B không sửa logic store; C không viết CSS/renderer trừ integration tối thiểu; D không sửa production code trừ test fixture. Các agent commit/PR riêng, lead rebase/integrate theo thứ tự **A -> B -> C -> D**.

### Giai đoạn 2 — tích hợp pilot (Agent lead; 1–2 ngày)

- Ghép contract/domain, renderer và controller.
- Kiểm thử end-to-end PLI_M02 + PLI_M06: điền key chung ở M02, chuyển M06, giá trị phải xuất hiện; điền bảng thành viên, tổng vốn phải cập nhật theo policy; save/reload giữ active tab và loop.
- So sánh export DOCX pilot trước/sau: không còn placeholder, thông tin canonical đi đúng template.
- Gate release pilot: tất cả tiêu chí nghiệm thu bên dưới pass tại 1280x800 và không có critical accessibility issue.

### Giai đoạn 3 — rollout và hardening (Agent B/C/D song song; 2–4 ngày)

- Áp dụng renderer/tab behavior cho tất cả schema blocks mà không cần sửa từng mẫu.
- Bổ sung `fieldMeta` theo ưu tiên các case hay dùng; field thiếu metadata vẫn render input text tương thích ngược và chỉ có validation cơ bản.
- Dọn hiệu năng: không rerender toàn màn hình trên mỗi gõ phím, debounce save/validation, giữ focus khi thay đổi bảng.
- Regression toàn bộ use case chọn được và export selected forms.

## Tiêu chí nghiệm thu

1. Chọn thủ tục tạo một tab cho mỗi mẫu được chọn; tab active duy nhất hiển thị, đổi tab không mất input/scroll/focus.
2. Sửa một key chung ở Mẫu A, Mẫu B hiển thị đúng cùng giá trị ngay khi mở; save/reload giữ case, selected forms, active tab, data và loop rows.
3. Required/format/rule lỗi có viền, icon/text và `aria-describedby`; `Kiểm tra` nhóm lỗi theo form và điều hướng chính xác đến ô.
4. Tiền định dạng `1.000.000` khi blur, số thật dùng đúng cho auto-sum/export. Các ô calculated/locked có trạng thái rõ ràng.
5. VSIC hoạt động bằng chuột lẫn bàn phím và chọn đồng thời mã/tên cho đúng dòng.
6. Bảng lặp thêm/xóa đúng dòng, không âm số dòng, hỏi xác nhận khi xóa dữ liệu; tổng vốn cập nhật theo policy.
7. `node app_web/test_dom.js` xanh; test domain/DOM mới xanh; smoke load-fill-mirror-save-reload-export xanh. Export lỗi validation bị chặn với thông báo rõ ràng.
8. 1280x800 không che viewport bởi footer; 768px và 375px vẫn dùng được navigation/action, bảng cuộn ngang; keyboard-only thực hiện được core flow. Không có lỗi axe mức critical.

## Rủi ro và kiểm soát

- Schema block chuyển từ DOCX không có tọa độ/ý nghĩa field đầy đủ: metadata bổ sung dần, pilot trước.
- Key nhãn giống nhau nhưng ý nghĩa khác: không auto-map theo nhãn; cần alias có review nghiệp vụ.
- Rerender HTML có thể làm mất caret/focus: controller phải patch active view hoặc lưu/khôi phục focus rõ ràng.
- Worktree hiện đang có nhiều thay đổi chưa commit: agent chỉ sửa file thuộc phạm vi của mình, không reset/revert file khác, tích hợp qua branch/commit nhỏ.

## Lệnh kiểm thử tối thiểu

```powershell
node app_web/test_dom.js
python -m tools.e2e_case_test
python app_web/main.py --mock
```

---

## Kế hoạch hoàn thiện sau audit độc lập (cập nhật 2026-08-25)

### Trạng thái hiện tại và định nghĩa “hoàn thành”

Phần pilot `PLI_M02` và nền `editable-grid` đã đạt phần lớn mục tiêu kỹ thuật:
9 loop production hiện có render đúng grid, thao tác dòng dùng controller chung,
VSIC tự điền tên ngành, draft migration và DOCX `PLI_M02` đã có test. Tuy nhiên,
toàn dự án **chưa hoàn thành** cho tới khi đóng đủ các gap sau:

1. DOCX `PLII_M01` phải xuất STT và dấu `X` ở cột ngành chính. Test hiện tại
   đang chấp nhận hai ô này rỗng, trái với contract export.
2. Mẫu bắt buộc/tùy chọn phải dùng metadata `bat_buoc`; không được tick tất cả.
   Các nhóm loại hình loại trừ nhau phải hỗ trợ `oneOf`.
3. Chặn race khi đổi thủ tục/restore draft; autosave thành công phải đồng bộ
   `dirty=false` và trạng thái hiển thị.
4. Rollout `ds_nganh` còn thiếu cho 13 mẫu:
   `PLI_M01`, `PLI_M03`, `PLI_M04`, `PLI_M05`, `PLI_M12`, `PLI_M17`,
   `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`, `PLI_M72`, `PLII_M02`,
   `PLII_M07`.
5. Có manual smoke WebView2 và visual QA DOCX/PDF ở độ phân giải release.
6. Worktree tích hợp sạch, không để dependency cache, output test hoặc file sinh
   tạm lọt vào commit; mọi generated artifact phải tái tạo được từ generator.

Release chỉ được gọi là DONE khi tất cả gate ở cuối chương này PASS. Không được
đổi test để hợp thức hóa output thiếu dữ liệu.

### Nguyên tắc chia việc cho subagent

- Một **Lead/Integrator Agent** giữ worktree chính, lập baseline, giao việc,
  review và merge. Lead không sửa cùng file khi subagent đang sở hữu file đó.
- Mỗi subagent làm trong một Git worktree và một branch riêng; không cho nhiều
  agent dùng chung thư mục làm việc.
- Chia theo quyền sở hữu file. Nếu hai nhiệm vụ cùng sửa `app_web/ui/app.js` hoặc
  `tools/build_form_maps.py`, gộp vào một agent hoặc chạy theo wave tuần tự.
- Subagent phải đọc `PLAN.md`, `git status --short`, test liên quan và source
  production trước khi sửa. Không reset/revert thay đổi của người khác.
- Mỗi branch có commit nhỏ, message rõ, kèm báo cáo test. Không merge branch có
  file untracked không giải thích được.
- File generated dùng chung như `app/data/form_maps.json`, `form_maps.js` và
  nhiều `blocks/*.json` chỉ được regenerate **một lần trong worktree tích hợp**
  sau khi merge source/spec. Subagent chỉ commit generated file thuộc đúng mẫu
  mình sở hữu khi Lead xác nhận không gây diff ngoài phạm vi.
- Không chạy song song các agent có quan hệ phụ thuộc. Chỉ các task ghi file
  tách biệt mới được parallel.

### Chuẩn bị baseline trước khi tạo worktree

Worktree hiện tại có nhiều file modified/untracked. Không tạo worktree từ `HEAD`
cũ vì subagent sẽ không nhìn thấy implementation mới. Lead phải review danh sách,
loại cache/output khỏi phạm vi, rồi tạo một baseline commit có thể quay lại.

PowerShell tham khảo, chạy tại repo chính:

```powershell
git status --short
git diff --check
git add -A
git status --short
git commit -m "chore: checkpoint editable grid and PLI_M02 pilot"
```

Chỉ `git add -A` sau khi Lead xác nhận các file xóa/untracked đều có chủ đích.
Không commit `.webview_deps/`, `__pycache__/`, hồ sơ sinh thử hoặc output test;
bổ sung `.gitignore` trước nếu cần. Baseline phải chạy lại được các test hiện có.

Tạo thư mục worktree nằm cạnh repo, không nằm bên trong repo:

```powershell
$Repo = (Resolve-Path '.').Path
$WtRoot = Join-Path (Split-Path $Repo -Parent) 'dangky_kinhdoanh-worktrees'
New-Item -ItemType Directory -Force -Path $WtRoot | Out-Null

git worktree add -b agent/docx-plii-m01 "$WtRoot\docx-plii-m01" HEAD
git worktree add -b agent/form-flow-state "$WtRoot\form-flow-state" HEAD
git worktree add -b agent/qa-contract "$WtRoot\qa-contract" HEAD
```

Sau Wave 1 được merge và có baseline mới, tạo worktree rollout từ commit mới,
không tạo trước từ baseline cũ:

```powershell
git worktree add -b agent/industry-formation "$WtRoot\industry-formation" HEAD
git worktree add -b agent/industry-change "$WtRoot\industry-change" HEAD
git worktree add -b agent/industry-household "$WtRoot\industry-household" HEAD
```

Mỗi coding agent phải được khởi chạy với `cwd` trỏ đúng worktree của mình. Khi
branch đã merge, kiểm tra worktree sạch trước khi gỡ:

```powershell
git -C "$WtRoot\docx-plii-m01" status --short
git worktree remove "$WtRoot\docx-plii-m01"
git branch -d agent/docx-plii-m01
git worktree prune
```

Không remove worktree còn thay đổi chưa commit hoặc chưa bàn giao.

### Sơ đồ wave và phụ thuộc

```text
Baseline sạch
   |
   +-- Wave 1A: PLII_M01 DOCX ----------+
   +-- Wave 1B: chọn mẫu + state --------+--> Integrate 1 + full regression
   +-- Wave 1C: QA contract/read-only ---+
                                             |
                                             v
                              Generator/spec contract ổn định
                                             |
   +-- Wave 2A: nhóm thành lập ----------+
   +-- Wave 2B: nhóm thay đổi ------------+--> Regenerate tập trung + Integrate 2
   +-- Wave 2C: nhóm hộ kinh doanh -------+
                                             |
                                             v
                           Wave 3: E2E, visual QA, package/release
```

### Wave 1 — đóng lỗi nền và test xanh giả

#### Agent 1A — `docx-plii-m01`

Phạm vi sở hữu:

- `tools/build_form_maps.py` phần spec `PLII_M01`.
- `app/templates/PLII_M01.docx` và generated artifacts chỉ của `PLII_M01`.
- `tools/test_acceptance_docx.py` và test DOCX liên quan.

Nhiệm vụ:

1. Thêm `stt_tag=True` cho bảng ngành `PLII_M01` và map
   `la_nganh_chinh` vào cột ngành chính.
2. Bảo đảm template hàng loop có `{_stt}`, `{ten_nganh}`, `{ma_nganh}`,
   `{la_nganh_chinh}` và marker mở/đóng đúng.
3. Sửa acceptance test: ba dòng phải có STT `1/2/3`, đúng một dấu `X`, đúng
   mã/tên từng ô; không được assert hai cột này rỗng.
4. Regenerate theo pipeline, xác nhận không còn loop tag trong XML và không làm
   thay đổi mẫu khác ngoài dự kiến.

Gate branch:

- `python -X utf8 -m tools.test_acceptance_docx`
- `python -X utf8 -m tools.audit_blocks_check`
- `python -X utf8 -m tools.audit_engine_test`

#### Agent 1B — `form-flow-state`

Phạm vi sở hữu:

- `app_web/ui/app.js`, DTO/API trả use-case metadata nếu cần.
- Test riêng cho chọn mẫu, race và autosave.

Nhiệm vụ:

1. Giữ metadata từng form khi map `case.forms -> docs` thay vì chỉ giữ ID.
2. Render form bắt buộc ở trạng thái checked + disabled; form tùy chọn mặc định
   unchecked, trừ khi draft đã chọn.
3. Khai metadata và UI cho nhóm `oneOf`; tối thiểu case
   `chuyen_doi_hkd_sang_dn` chỉ cho chọn đúng một loại hình. Không suy đoán nhóm
   từ tên mẫu trong renderer; nhóm phải nằm trong dữ liệu use-case/schema.
4. Validation trước export: thiếu mẫu bắt buộc hoặc nhóm `oneOf` chưa/chọn quá
   một phải blocking.
5. Thêm request sequence/token cho `onCaseChange()`: kết quả async cũ không được
   ghi vào state nếu user đã chuyển case.
6. Autosave local thành công đặt `dirty=false`; autosave lỗi giữ dirty và báo lỗi.
7. Draft restore giữ đúng lựa chọn bắt buộc/tùy chọn/oneOf và active form hợp lệ.

Gate branch:

- Test case có form bắt buộc + optional.
- Test case bốn form `oneOf` không thể xuất cả bốn.
- Test Promise case cũ resolve sau case mới không ghi đè `state.docs`.
- Test autosave thành công/thất bại và cảnh báo đổi case.
- Toàn bộ `test_dom.js`, `test_domain.js`, `test_grid.js` vẫn PASS.

#### Agent 1C — `qa-contract` (không sửa production trùng Agent 1A/1B)

Phạm vi sở hữu ban đầu: test/audit/docs độc lập. Agent này không sửa
`app.js`, `render.js`, `form-domain.js`, `build_form_maps.py` hoặc template.

Nhiệm vụ:

1. Viết/siết contract test phát hiện STT/ngành chính rỗng trong DOCX.
2. Thêm test xác nhận mọi `bat_buoc=false` không bị tick mặc định và các case
   loại trừ nhau có metadata rõ.
3. Lập inventory 13 mẫu thiếu `ds_nganh`, phân loại schema mong đợi:
   đăng ký mới, thay đổi/bổ sung/xóa bỏ, hộ kinh doanh. Không tự động đồng bộ
   các loop khác nghĩa với canonical `ds_nganh`.
4. Báo cáo gap; chỉ commit test không xung đột. Test mới có thể đỏ trước khi
   merge Agent 1A/1B nhưng phải xanh sau Integrate 1.

### Integrate 1 — Lead Agent

1. Fetch/review từng branch; kiểm tra `git diff --check` và phạm vi file.
2. Merge/cherry-pick Agent 1A và 1B, giải quyết generated artifacts tại Lead.
3. Merge test của 1C; không nới assertion để lấy màu xanh.
4. Regenerate `form_maps`, templates/blocks theo pipeline một lần.
5. Chạy full regression và tạo commit baseline `integration/wave-1`.
6. Chỉ sau đó mới tạo worktree Wave 2 từ commit này.

### Wave 2 — rollout bảng ngành nghề còn thiếu

Trước khi chạy song song, Lead nên tách cấu hình bảng theo mẫu ra file spec riêng
(ví dụ `tools/form_specs/industry/*.json` hoặc module nhỏ theo nhóm) để ba agent
không cùng sửa một dictionary lớn trong `build_form_maps.py`. Generator trung tâm
đọc các spec và Lead là nơi duy nhất regenerate toàn bộ output dùng chung.

#### Agent 2A — `industry-formation`

- Mẫu: `PLI_M01`, `PLI_M03`, `PLI_M04`, `PLI_M05`.
- Tạo spec bảng theo đúng template pháp lý của từng mẫu.
- Dùng canonical `ds_nganh` khi dữ liệu có cùng ý nghĩa đăng ký ngành hiện tại.
- Mỗi mẫu có fixture + structural DOCX test riêng.

#### Agent 2B — `industry-change`

- Mẫu: `PLI_M12`, `PLI_M17`, `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`,
  `PLI_M72`.
- Trước khi map, phân biệt rõ danh sách hiện tại với `nganh_bo_sung`,
  `nganh_xoa_bo`, `nganh_truoc_thay_doi`; không gộp chỉ vì cùng có mã ngành.
- Nếu nghiệp vụ chưa đủ căn cứ, ghi gap và để mẫu đó blocked thay vì tự suy diễn.
- Mỗi semantic loop có row contract, validation và test export độc lập.

#### Agent 2C — `industry-household`

- Mẫu: `PLII_M02`, `PLII_M07`.
- Kiểm tra yêu cầu ngành chính của từng mẫu trước khi bật `requirePrimary`.
- Dùng VSIC lookup chung nhưng metadata loop theo đúng nghiệp vụ hộ kinh doanh.
- Thêm test draft, shared data (chỉ khi canonical semantics trùng) và DOCX.

Quy tắc Wave 2:

- Subagent commit source spec, fixture và test của nhóm mình.
- Không commit global regenerated `form_maps.json/js` nếu thay đổi mẫu ngoài nhóm.
- Lead merge cả ba spec, regenerate một lần, review diff theo danh sách allowlist.
- Mỗi mẫu phải có test production block + DOCX structure; không chỉ test mock.

### Wave 3 — hardening, visual QA và release desktop

#### Agent 3A — E2E WebView2

- Chạy app thật, không dùng `?mock=1`.
- Test 1280×800 và 1366×768: tab, scroll, focus lỗi, popup VSIC, bảng rộng,
  thêm/xóa/reorder/duplicate, draft/reload và export.
- Chụp ảnh các màn hình trọng yếu, ghi pass/fail theo case và mẫu.

#### Agent 3B — DOCX/PDF visual QA

- Dùng LibreOffice/Word render DOCX đại diện thành PDF/PNG.
- Kiểm tra header, border, row height, wrap tiếng Việt, dấu `X`, page break,
  clipping và 1/3/100 dòng.
- Ít nhất: `PLI_M02`, `PLI_M03`, `PLI_M06`, `PLII_M01`, một mẫu thay đổi và
  một mẫu hộ kinh doanh.

#### Agent 3C — packaging/release hygiene

- Xác minh chạy bằng `.exe` local, không cần server Internet; WebView2 runtime
  và asset local được đóng gói đúng.
- Test đường dẫn có dấu/khoảng trắng, máy không có Python và hồ sơ export lớn.
- Không đóng gói `.webview_deps` hoặc output test theo cách làm repo phình; dùng
  dependency/build pipeline rõ ràng.
- Tạo release checklist, version và hướng dẫn backup/restore draft.

### Bộ lệnh regression bắt buộc tại worktree tích hợp

```powershell
node app_web/test_dom.js
node app_web/test_domain.js
node app_web/test_grid.js
node app_web/test_loop_prod.js
node app_web/test_acceptance.js
python -X utf8 -m tools.smoke_web_assets
python -X utf8 -m tools.audit_blocks_check
python -X utf8 -m tools.audit_content_check
python -X utf8 -m tools.audit_engine_test
python -X utf8 -m tools.test_pli_m02_industry
python -X utf8 -m tools.test_acceptance_docx
python -X utf8 -m compileall -q app_web tools
```

Thêm test mới vào suite/gate tương ứng. Một test bị skip vì thiếu browser,
LibreOffice, Tcl/Tk hoặc WebView2 không được báo là PASS; phải ghi `NOT RUN`, lý
do và owner chạy bù trên môi trường release.

### Release gates cuối cùng

1. Không còn test xanh giả: `PLII_M01` có STT và đúng một dấu `X` trong DOCX.
2. 9 loop cũ và mọi loop mới có header/body cùng grid, mapping đúng cột.
3. 13 mẫu rollout có production block, template loop và DOCX test tương ứng;
   mẫu bị blocked nghiệp vụ phải được nêu rõ, không tính DONE.
4. Mẫu bắt buộc không thể bỏ; optional không tự tick; `oneOf` chọn đúng một.
5. Đổi case nhanh, restore draft và autosave vượt qua race/reload tests.
6. VSIC, duplicate, ngành chính, stable row id và validation navigation PASS.
7. Full regression không lỗi; repo/worktree tích hợp sạch sau commit.
8. Manual WebView2 và visual DOCX QA có bằng chứng, không còn clipping/vỡ bảng.
9. Bản `.exe` chạy local trên máy test sạch và xuất hồ sơ mở được bằng Word.

## Prompt tổng để Lead Agent implement kế hoạch bằng subagent/worktree

```text
Bạn là Lead/Integrator Coding Agent của repo Windows:
C:\Users\Tuyen PC\orca\dangky_kinhdoanh

MỤC TIÊU
Hoàn thiện toàn bộ phần “Kế hoạch hoàn thiện sau audit độc lập” trong PLAN.md.
Không chỉ làm test xanh; output UI/DOCX production phải đúng nghiệp vụ và đúng
release gates. Hãy dùng subagent chạy song song trong Git worktree riêng để rút
ngắn tiến độ, nhưng không cho hai agent sửa cùng file trong cùng wave.

BẮT BUỘC TRƯỚC KHI CODE
1. Đọc toàn bộ PLAN.md và AGENTS.md nếu có.
2. Kiểm tra git status/diff. Repo hiện có thể đang dirty: không reset/revert/xóa
   thay đổi của người dùng. Review và tạo baseline commit sạch trước khi tạo
   worktree; không tạo worktree từ HEAD cũ làm mất implementation hiện tại.
3. Không commit .webview_deps, __pycache__, generated_ho_so test hoặc cache.
4. Chạy bộ regression hiện tại để ghi baseline pass/fail.
5. Lập plan có owner, branch, worktree, file ownership, dependency và gate.

TỔ CHỨC AGENT
- Lead giữ worktree tích hợp, chỉ review/merge/regenerate/test khi subagent chạy.
- Wave 1 chạy song song tối đa 3 subagent:
  A. docx-plii-m01: sửa STT + la_nganh_chinh và test DOCX PLII_M01.
  B. form-flow-state: bat_buoc/optional/oneOf, async case token, autosave dirty.
  C. qa-contract: test độc lập + inventory 13 mẫu, không sửa production trùng A/B.
- Merge Wave 1, regenerate tập trung và full regression.
- Sau Wave 1, tách industry specs theo file/nhóm nếu cần, rồi chạy Wave 2:
  D. industry-formation: PLI_M01/M03/M04/M05.
  E. industry-change: PLI_M12/M17/M19/M21/M23/M25/M72; không gộp loop khác nghĩa.
  F. industry-household: PLII_M02/PLII_M07.
- Lead merge spec, regenerate global artifacts đúng một lần và chạy full test.
- Wave 3 giao E2E WebView2, visual DOCX/PDF và packaging cho các agent tách biệt
  nếu môi trường có đủ runtime.

QUY TẮC THỰC THI
- Mỗi agent có branch agent/<task> và worktree riêng nằm ngoài repo chính.
- Gửi cho từng agent: mục tiêu, file được sở hữu, file cấm sửa, test gate và format
  báo cáo. Agent phải commit trước khi bàn giao hash cho Lead.
- Không chạy parallel task cùng sửa app_web/ui/app.js, tools/build_form_maps.py,
  form_maps.json/js hoặc cùng template. Nếu ownership chồng nhau, chạy tuần tự.
- Generated artifacts toàn cục do Lead tạo sau merge source/spec.
- Không sửa test để chấp nhận dữ liệu thiếu. Đặc biệt PLII_M01 phải assert STT
  1/2/3 và dấu X đúng cột.
- Không suy diễn nghiệp vụ giữa ds_nganh và nganh_bo_sung/nganh_xoa_bo/
  nganh_truoc_thay_doi. Nếu thiếu căn cứ, đánh dấu blocked kèm bằng chứng.
- Dùng UTF-8; giữ canonical keys và migration tương thích draft cũ.
- Sau mỗi merge: git diff --check, test liên quan, rồi full regression theo PLAN.

YÊU CẦU CHẤT LƯỢNG
- Test production blocks/templates, không chỉ mock hoặc helper mô phỏng.
- Có test failure trước fix cho các bug audit nếu khả thi.
- DOCX test phải kiểm tra từng cell, số dòng, STT, dấu X và leftover tokens.
- Browser/LibreOffice test không chạy được phải ghi NOT RUN, không gọi PASS.
- Đảm bảo add/delete/clear/reorder/duplicate áp dụng generic cho mọi editable-grid.
- Mẫu bắt buộc/optional/oneOf phải đúng cả UI, draft, validation và export.
- Race case load và autosave phải có deterministic test.

BÁO CÁO SAU MỖI WAVE
1. Agent/branch/worktree và commit hash.
2. File đã sửa, contract/migration thay đổi.
3. Test command + kết quả PASS/FAIL/NOT RUN.
4. Generated diff ngoài dự kiến, conflict và cách giải quyết.
5. Gap nghiệp vụ hoặc rủi ro còn lại.

ĐIỀU KIỆN DỪNG
Chỉ báo DONE khi toàn bộ release gates trong PLAN.md đạt. Nếu còn mẫu chưa rollout,
PLII_M01 thiếu STT/X, optional/oneOf sai, visual QA chưa chạy hoặc .exe chưa smoke
trên máy sạch, hãy báo PARTIAL/NOT RUN tương ứng và tiếp tục phần còn an toàn.
Không tự ý reset repo, xóa worktree chưa sạch, hay che lỗi bằng cách nới test.
```

## Prompt triển khai cho agent lead

```text
Bạn là lead engineer của repo C:\\Users\\Tuyen PC\\orca\\dangky_kinhdoanh. Hãy triển khai MVP giao diện “khai trực tiếp kiểu HTKK” theo PLAN.md, bắt đầu bằng pilot PLI_M02 và PLI_M06.

Ràng buộc bắt buộc:
- Dùng app_web làm UI chính. Giữ nguyên app_web/main.py bridge, tools/docx_render.py, templates DOCX và contract export/draft hiện có.
- HTML/CSS chỉ lấy cảm hứng thao tác HTKK, không sao chép tài sản/thương hiệu HTKK.
- data-key là canonical contract đồng bộ; không rename hàng loạt form map/block key. Chỉ đồng bộ exact key, alias phải tường minh và có test.
- Hiển thị đúng một mẫu active; tab đáy chuyển mẫu, không chỉ scroll trang. Giữ data, active tab, scroll/focus khi đổi tab/re-render.
- Tạo domain module thuần cho field metadata, validation và định dạng tiền; controller không nhồi logic validation trực tiếp.
- Mở đầu bằng tài liệu contract (metadata, lỗi, actions) và unit test cho domain. Sau đó triển khai UI/controller pilot.
- Bổ sung accessibility: label/id ổn định, aria-required/invalid/describedby, tablist/tab/tabpanel, focus visible. Hỗ trợ Ctrl+S, Ctrl+PgUp/PgDn, VSIC Arrow/Enter/Escape.
- Kiểm tra lỗi blocking trước export; xóa dữ liệu/đổi case khi dirty phải xác nhận. Nút không có backend phải disabled/hide có lý do.
- Không chạm hay revert thay đổi không liên quan trong worktree.

Tiêu chí demo: chọn một case pilot, điền dn.ten_tieng_viet ở M02 rồi sang M06 vẫn thấy giá trị; bảng lặp/VSIC/tổng vốn chạy; Ctrl+S lưu, reload khôi phục, Kiểm tra đưa focus đến lỗi, export DOCX pass.

Trước khi giao, chạy node app_web/test_dom.js và python -m tools.e2e_case_test, thêm test phù hợp cho validation/tab/focus/VSIC. Báo cáo file đổi, test đã chạy, những field/rule chưa metadata hóa và rủi ro còn lại.
```

## Prompt ngắn cho các agent song song

### Agent A — domain

```text
Theo PLAN.md Giai đoạn 1, chỉ làm domain/validation cho app_web: form-domain.js, metadata pilot PLI_M02/PLI_M06 và unit test. API phải thuần, không DOM, không đổi app.js/render.js/export. Định nghĩa field meta, validate, format/parse tiền, error contract. Commit nhỏ và báo rõ public API cho agent C.
```

### Agent B — renderer/UI

```text
Theo PLAN.md Giai đoạn 1, chỉ làm renderer/UI và accessibility của app_web. Dựng shell/tabpanel HTKK-like, CSS responsive desktop-first, ID/label/ARIA ổn định và render metadata tương thích ngược. Không đổi state business logic/export. Dùng contract đã chốt; demo PLI_M02/M06 và báo DOM hooks cần agent C nối.
```

### Agent C — controller/state

```text
Theo PLAN.md Giai đoạn 1, chỉ làm app_web/ui/app.js: active document tabs, canonical mirroring, dirty/autosave, khôi phục focus/scroll, keyboard shortcuts, VSIC keyboard, selection/xóa loop an toàn, validate navigation và block export. Tích hợp qua public API/domain + DOM hooks đã chốt. Không sửa CSS/schema bất khả kháng; thêm test controller/DOM.
```

### Agent D — QA

```text
Theo PLAN.md Giai đoạn 1, làm QA không thay đổi production behavior: lập acceptance test checklist, fixtures/mock và test Node/Python cho pilot PLI_M02/M06. Phủ load -> fill shared key -> tab -> validate -> VSIC/loop -> save/reload -> export. Bảo đảm test hiện hữu xanh và báo reproduction steps cho mọi lỗi.
```

---

## Đánh giá độc lập sau MVP và kế hoạch tiếp theo (2026-08-25)

### Kết luận ngắn

Phần shell HTKK, tab active, store dùng chung, draft v2, validation cơ bản và export bridge đã đi đúng hướng. Chưa nên rollout rộng trước khi sửa lớp **schema bảng production**: test hiện tại chủ yếu dùng mock rút gọn, trong khi blocks thật có cấu trúc khác và đang làm bảng lệch cột hoặc mất hẳn vùng nhập ngành nghề.

### Kết quả kiểm tra

- PASS: `app_web/test_dom.js` — 58/58.
- PASS: `app_web/test_domain.js` — 64/64.
- PASS: `tools/smoke_web_assets.py` — 35/35.
- PASS: `tools/audit_engine_test.py` — 10/10; engine DOCX thay tag/loop và tạo file hợp lệ.
- PASS sau khi chạy UTF-8: `tools/audit_content_check.py` — 4 case mẫu.
- `tools/e2e_case_test.py` render headless được DOCX nhưng phần Tk không chạy trên môi trường kiểm tra do thiếu Tcl/Tk; đây là lỗi môi trường test, không phải kết luận UI pass.
- Không thực hiện được browser visual test vì môi trường kiểm tra không có browser backend. Cần chạy manual smoke trên máy dev trước khi release.
- Không thực hiện được DOCX -> PNG visual QA vì máy không có LibreOffice/`soffice`; kiểm tra cấu trúc bằng `python-docx` vẫn xác nhận PLI_M02 xuất ra **0 bảng**, PLI_M06 có 1 bảng, PLII_M01 có 2 bảng.

### Phát hiện ưu tiên cao

#### P0.1 — Mock đang che lỗi dữ liệu production

- Mock PLI_M02 có 29 blocks và có loop ngành nghề; production PLI_M02 có 273 blocks nhưng không có loop/table nào.
- Mock PLI_M06 dùng chỉ số cột 1-based (`2..7`), production converter tạo chỉ số 0-based (`1..11`). Renderer hiện giả định 1-based nên test mock xanh nhưng bảng thật sai.
- Hành động: mọi test renderer/schema phải chạy thêm trực tiếp trên `app/data/blocks/*.json`; mock chỉ dùng cho demo offline và phải được sinh tự động từ production, không duy trì thủ công như một schema khác.

#### P0.2 — Tất cả 8 bảng lặp production đang lệch số cột

So sánh số ô header với số ô body do renderer hiện sinh:

| Mẫu/loop | Header | Body hiện tại |
| --- | ---: | ---: |
| PLI_M06 `ds_thanh_vien` | 12 | 11 |
| PLI_M07 `ds_co_dong_sang_lap` | 11 | 10 |
| PLI_M08 `ds_co_dong_nn` | 8 | 7 |
| PLI_M09 `ds_thanh_vien` | 12 | 11 |
| PLI_M10 `ds_cshhl` | 11 | 10 |
| PLI_M11 `ds_cshhl` | 8 | 7 |
| PLII_M01 `ds_nganh` | 4 | 2 |
| PLII_M01 `ds_tv_ho_gia_dinh` | 10 | 9 |

Nguyên nhân: `docx_to_blocks.parse_table()` lưu `col` theo zero-based, còn `renderLoop()` đang xử lý như one-based. Ngoài ra renderer loop chưa bảo toàn đầy đủ `colspan`/`rowspan` của header.

Hành động:

1. Chốt `col` là zero-based trong schema contract.
2. Renderer lấy tổng số cột từ grid/header, không suy ra từ `max(tag column)`.
3. Giữ ô STT và các cột chưa map; không để field trượt sang cột kế bên.
4. Bổ sung kiểu cột loop `text | money | percent | checkbox | radio | readonly`.
5. Test từng bảng production: số cột header = body, tag nằm đúng tiêu đề, dữ liệu export về đúng cell.

#### P0.3 — Ngành nghề đang mất chức năng ở 14 mẫu

Các mẫu có tiêu đề `STT / Tên ngành / Mã ngành` dạng paragraph rời nhưng không có loop nhập liệu:

`PLI_M01`, `PLI_M02`, `PLI_M03`, `PLI_M04`, `PLI_M05`, `PLI_M12`, `PLI_M17`, `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`, `PLI_M72`, `PLII_M02`, `PLII_M07`.

Đặc biệt PLI_M02/03/04 hiện chỉ hiện chữ tiêu đề; người dùng không có nơi nhập nhiều ngành và dữ liệu ngành không đi vào export. Đây là lỗi chức năng/schema, không thể sửa chỉ bằng CSS `border`.

Hành động:

1. Mở rộng `REBUILD_TABLES`/form map để tạo `ds_nganh` cho PLI_M01–M05 trước.
2. Schema bảng ngành tối thiểu: `stt` tự sinh, `ten_nganh`, `ma_nganh`, `la_nganh_chinh` (radio/checkbox theo nghiệp vụ).
3. Dùng một canonical loop name thống nhất (`ds_nganh`) hoặc khai alias/migration rõ ràng; hiện `form-domain.js` có `ds_nganh_kinh_doanh` nhưng production PLII_M01 dùng `ds_nganh`.
4. VSIC chọn mã phải điền tên trong cùng dòng; kiểm tra trùng mã, mã hợp lệ và đúng một ngành chính nếu mẫu yêu cầu.
5. Sau pilot PLI_M02, rollout 9 mẫu còn lại theo nhóm nghiệp vụ và kiểm tra DOCX từng mẫu.

#### P0.4 — Vốn điều lệ cần “bảng UI”, không nên biến thành loop

Vốn điều lệ là một nhóm field đơn (`von_dieu_le`, `von_dieu_le_chu`, ngoại tệ hoặc cơ cấu vốn), không phải danh sách nhiều dòng như ngành nghề. Đề xuất tách hai lớp:

- **UI:** thêm block/layout `field-grid` để kẻ bảng HTKK gồm nhãn, ô nhập, đơn vị và ô computed; có thể nhóm số tiền, bằng chữ, ngoại tệ và cơ cấu vốn.
- **DOCX:** tiếp tục đổ vào các tag hiện có để không tự ý thay bố cục biểu mẫu pháp lý. Chỉ dựng lại bảng trong DOCX nếu có bản mẫu chính thức chứng minh nguồn Word hiện tại đã làm mất bảng.

Hiện có 16 field vốn dạng paragraph ở PLI_M02/03/04/05/12/72 và PLII_M01/02. Pilot `field-grid` nên bắt đầu tại PLI_M02, sau đó PLI_M03/04/05.

Không nên hard-code vị trí bằng CSS selector theo số thứ tự block. Tạo metadata UI riêng, ví dụ `app/data/ui_layouts/PLI_M02.json`, tham chiếu canonical keys; generator blocks có thể chạy lại mà không làm mất layout UI.

#### P0.5 — Chọn mẫu tùy chọn đang sai nghiệp vụ

`renderFormList()` hiện tick tất cả docs và không dùng `bat_buoc`. Có ít nhất 3 case có mẫu tùy chọn; case `chuyen_doi_hkd_sang_dn` chứa bốn mẫu loại hình loại trừ nhau nhưng UI hiện có thể chọn/xuất tất cả.

Hành động: Bridge trả metadata forms của case; bắt buộc tick + khóa, tùy chọn để trống, và hỗ trợ nhóm lựa chọn loại trừ `oneOf` cho loại hình doanh nghiệp.

### Phát hiện ưu tiên trung bình

- Thêm request token/case-load sequence để kết quả tải async của case cũ không ghi đè case mới; luồng restore draft hiện có nguy cơ race.
- Autosave đổi status thành “Đã lưu” nhưng chưa đặt `dirty=false`; trạng thái hiển thị và cảnh báo đổi case có thể mâu thuẫn.
- `section.page-a4` chưa có `role="tabpanel"`/`aria-labelledby`; checkbox lồng trong run chưa có accessible label đầy đủ.
- Sửa `audit_blocks_check.py`: phần so text đang gom nhãn block checkbox về cuối làm báo lệch thứ tự giả; phần dedup cell dùng `id()` trên lxml proxy có thể bỏ nhầm ô. Audit cần trở thành release gate đáng tin cậy.
- Cài Tcl/Tk đúng cho test legacy hoặc tách `e2e_case_test` thành web headless và Tk legacy để lỗi môi trường một UI không che kết quả UI còn lại.

### Thứ tự triển khai đề xuất

#### Sprint 1 — sửa nền bảng và test production (P0, 1–2 ngày)

- Sửa zero-based column contract + colspan/rowspan.
- Thêm regression test dùng blocks thật cho đủ 8 loop.
- Đồng bộ hoặc sinh lại mock từ production.
- Sửa audit để không còn false positive; gate: schema frontend + loop production PASS.

#### Sprint 2 — pilot ngành nghề + vốn PLI_M02 (P0, 2–3 ngày)

- Dựng `ds_nganh` thật trong template/form map/block PLI_M02.
- Thêm cột ngành chính và VSIC row behavior.
- Thêm `ui_layouts/PLI_M02.json` với `field-grid` cho vốn điều lệ.
- Test nhập -> draft -> tab -> validation -> DOCX; render DOCX thành PNG trên máy có LibreOffice và kiểm tra toàn bộ trang.

#### Sprint 3 — nghiệp vụ chọn mẫu và ổn định state (P0/P1, 1–2 ngày)

- Bắt buộc/tùy chọn/oneOf form selection.
- Chặn race case loading và draft restore.
- Đồng bộ dirty/autosave state, hoàn thiện tabpanel/a11y.

#### Sprint 4 — rollout có kiểm soát (3–5 ngày)

- Ngành nghề: PLI_M01/03/04/05 trước, sau đó PLI_M12/17/19/21/23/25/72 và PLII_M02/07.
- Field-grid vốn: PLI_M03/04/05, rồi các mẫu thay đổi/công bố liên quan.
- Mỗi mẫu chỉ được đánh dấu hoàn thành khi production fixture, UI table alignment, save/reload và DOCX visual QA đều PASS.

### Gate trước khi đóng gói `.exe`

1. Không còn test chính nào chỉ chạy mock mà thiếu production fixture tương ứng.
2. 8/8 loop hiện có và mọi loop ngành mới có header/body cùng grid và mapping đúng cột.
3. Case có mẫu tùy chọn không tự xuất nhầm mẫu.
4. Draft khác case khôi phục đúng qua thử nghiệm lặp nhiều lần.
5. DOCX đại diện PLI_M02, PLI_M06, PLII_M01 được render PNG và kiểm tra không vỡ bảng, clipping hoặc mất dữ liệu.
6. Manual smoke trên WebView2 desktop tại 1280x800 và 1366x768.

---

## Đặc tả luồng bảng ngành nghề: thêm/xóa dòng và tự điền tên (2026-08-25)

> Cập nhật phạm vi: thêm/xóa/sắp xếp dòng là năng lực của **component bảng lặp dùng chung**, không phải tính năng riêng của bảng ngành nghề. Phần ngành nghề bên dưới chỉ bổ sung hành vi VSIC và ngành chính trên nền component chung đó.

### Nền tảng bảng lặp dùng chung (`editable-grid`)

Mọi bảng có dữ liệu nhiều dòng phải dùng chung một cơ chế, gồm tối thiểu:

- `ds_nganh`: ngành nghề kinh doanh.
- `ds_thanh_vien`: thành viên công ty TNHH/hợp danh.
- `ds_co_dong_sang_lap`: cổ đông sáng lập.
- `ds_co_dong_nn`: cổ đông/nhà đầu tư nước ngoài.
- `ds_cshhl`: chủ sở hữu hưởng lợi cá nhân/tổ chức.
- `ds_tv_ho_gia_dinh`: thành viên hộ gia đình.
- Các bảng lặp mới phát hiện khi audit toàn bộ 87 mẫu.

Component không hard-code tên cột. Mỗi bảng nhận metadata:

```json
{
  "loop": "ds_thanh_vien",
  "rowKey": "_row_id",
  "minRows": 0,
  "maxRows": null,
  "allowAdd": true,
  "allowDelete": true,
  "allowReorder": true,
  "confirmDeleteNonEmpty": true,
  "columns": [
    {"tag": "ho_ten", "type": "text", "required": true},
    {"tag": "von_dong_gop", "type": "money"},
    {"tag": "ty_le_von", "type": "percent"}
  ]
}
```

Các thao tác chung:

- Thêm dòng đầu/cuối hoặc sau dòng đang chọn.
- Xóa dòng đang chọn; xác nhận nếu dòng có dữ liệu.
- Xóa nhiều dòng đã chọn; xác nhận một lần và nêu số dòng.
- Xóa tất cả dữ liệu bảng; xác nhận rõ phạm vi, sau đó vẫn giữ một dòng trống trên UI.
- Di chuyển dòng Lên/Xuống; có thể bổ sung kéo-thả sau MVP nhưng bàn phím/nút vẫn phải hoạt động.
- Nhân bản dòng khi dữ liệu gần giống nhau, nhưng xóa các field định danh/khóa do metadata quy định.
- STT tự đánh lại; không lưu STT như dữ liệu người dùng.
- Undo thao tác xóa gần nhất trong phiên là mục tiêu P1; tối thiểu MVP phải có confirm trước xóa.
- Lưu draft/khôi phục/xuất DOCX phải giữ đúng số dòng và thứ tự.
- Validation lỗi phải định vị bằng `loop + stable row id + tag`, không chỉ row index, để đổi thứ tự không làm lỗi trỏ sai dòng.

“Tự do” của người dùng vẫn phải nằm trong giới hạn hồ sơ hợp lệ:

- Người dùng được tự do thêm/xóa/sắp xếp dữ liệu, nhưng không được xóa header hoặc cấu trúc bảng pháp lý.
- `minRows/maxRows` và field bắt buộc do metadata của từng thủ tục quyết định.
- Nếu xóa dòng làm vi phạm số thành viên tối thiểu, app vẫn cho thao tác nhưng hiển thị lỗi blocking trước export; không âm thầm ngăn người dùng chỉnh sửa.
- Các cột chữ ký hoặc xác nhận chỉ dùng ở bản in có thể được đánh dấu `outputOnly`, không bắt người dùng nhập trên UI.
- Bảng readonly/computed vẫn dùng renderer chung nhưng tắt action theo metadata.

Kiến trúc đề xuất:

- `render.js`: chỉ render grid theo schema/metadata, không chứa rule riêng của ngành hay thành viên.
- `app.js` hoặc module controller riêng: xử lý selection, add/delete/reorder/duplicate và focus restoration dùng chung.
- `form-domain.js`: validate generic `minRows`, required column, money/percent, duplicate theo cấu hình; validator chuyên ngành như VSIC là rule plug-in.
- `docx_to_blocks.py`: sinh grid coordinates nhất quán zero-based.
- Mỗi bảng chỉ khai báo metadata và rule riêng, không copy/paste handler JavaScript.

### Mục tiêu trải nghiệm

Người dùng chỉ cần nhập **mã ngành**, phần mềm tự tra danh mục VSIC local và điền **tên ngành chính thức** vào cùng dòng. Bảng cho phép thêm/xóa/sắp xếp dòng nhưng không cho xóa cấu trúc bảng pháp lý khỏi biểu mẫu.

Ví dụ:

| STT | Mã ngành | Tên ngành theo VSIC | Chi tiết hoạt động | Ngành chính |
| ---: | --- | --- | --- | :---: |
| 1 | 0111 | Trồng lúa |  | ● |
| 2 | 0112 | Trồng ngô và cây lương thực có hạt khác |  | ○ |

### Data contract

Canonical loop dùng cho danh sách ngành chung của một hồ sơ:

```json
{
  "ds_nganh": [
    {
      "ma_nganh": "0111",
      "ten_nganh": "Trồng lúa",
      "chi_tiet": "",
      "la_nganh_chinh": true
    }
  ]
}
```

Quy tắc:

- `ma_nganh`: mã VSIC cấp 4, lưu dạng chuỗi để không mất số `0` đầu.
- `ten_nganh`: lấy từ `app/data/nganh_vsic.json`; mặc định readonly để mã và tên không lệch nhau.
- `chi_tiet`: tùy chọn, chỉ dùng khi mẫu có yêu cầu mô tả chi tiết.
- `la_nganh_chinh`: boolean; hiển thị radio nếu nghiệp vụ yêu cầu đúng một ngành chính.
- Không auto-sync các bảng có ý nghĩa khác nhau như `nganh_bo_sung`, `nganh_xoa_bo`, `nganh_truoc_thay_doi`. Chỉ các mẫu cùng tham chiếu canonical `ds_nganh` mới dùng chung dữ liệu.
- Draft migration phải chuyển dữ liệu cũ từ `ds_nganh_kinh_doanh` sang `ds_nganh` khi `ds_nganh` chưa tồn tại; không ghi đè dữ liệu mới.

### Luồng nhập mã -> tự điền tên

1. Khi ô mã rỗng: xóa tên tự điền và bỏ lỗi VSIC của dòng.
2. Khi đang gõ 1–3 chữ số: giữ focus, mở gợi ý mã phù hợp; chưa báo lỗi blocking.
3. Khi nhập đủ mã hợp lệ: tra danh mục VSIC local, điền ngay `ten_nganh`, đóng gợi ý và đánh dấu dòng hợp lệ.
4. Khi nhập mã không tồn tại: không tự tạo tên; giữ giá trị để người dùng sửa, đánh dấu đỏ và báo “Mã ngành không có trong danh mục VSIC”.
5. Khi người dùng chọn một kết quả từ popup bằng chuột hoặc Enter: điền đồng thời mã + tên.
6. Cho phép tìm ngược bằng tên ngành có dấu/không dấu; chọn kết quả cũng điền đồng thời mã + tên.
7. Khi đổi mã đã hợp lệ sang mã khác: tên cũ phải được thay ngay, không được giữ tên không khớp.
8. Không cần Internet; toàn bộ lookup chạy từ `app/data/nganh_vsic.json` trong app `.exe`.

### Thêm/xóa/sắp xếp dòng

- Dùng toàn bộ hành vi chung của `editable-grid` thay vì viết handler riêng cho `ds_nganh`.
- `Thêm dòng`: chèn một dòng trống sau dòng đang chọn; nếu chưa chọn thì thêm cuối bảng; riêng bảng ngành sau đó focus ô `ma_nganh`.
- `Xóa dòng`: dùng confirm chung; thông điệp ngành hiển thị thêm mã/tên sắp xóa.
- `Xóa tất cả`: dùng action chung; sau khi xóa vẫn giữ một dòng trống để bảng còn sử dụng được.
- `Lên/Xuống`: dùng action chung; STT tự đánh lại từ 1 và thứ tự mới phải được giữ khi lưu draft/export.
- Nếu xóa dòng đang là ngành chính, validation yêu cầu chọn ngành chính mới trước export.
- Không cho thêm hai dòng có cùng mã ngành; lỗi duplicate phải trỏ đến cả dòng trùng trước và dòng vừa nhập.

### Chọn ngành nghề kinh doanh chính

- Dùng radio trong cột `Ngành chính`, không dùng checkbox nếu mẫu yêu cầu duy nhất một ngành.
- Chọn một dòng sẽ đặt `la_nganh_chinh=true` cho dòng đó và `false` cho tất cả dòng còn lại trong cùng `ds_nganh`.
- Nếu bảng có ít nhất một ngành nhưng chưa chọn ngành chính, tạo lỗi blocking `PRIMARY_INDUSTRY_REQUIRED` ở những mẫu yêu cầu.
- Với mẫu không có cột/nghiệp vụ ngành chính, field vẫn có thể tồn tại trong store nhưng không render và không bắt buộc.

### Đồng bộ giữa các mẫu

- `state.store.loops.ds_nganh` là nguồn chân lý duy nhất trong hồ sơ.
- Khi thêm, sửa, xóa hoặc đổi thứ tự ở Mẫu A, Mẫu B cùng dùng `ds_nganh` phải thấy danh sách mới ngay khi mở tab.
- Không giữ bản sao per-form của cùng danh sách.
- Metadata từng form quyết định cột nào được hiển thị; ví dụ form A có `chi_tiet`, form B chỉ có `ma_nganh/ten_nganh`, nhưng cả hai đọc cùng row object.
- Export từng mẫu chỉ lấy các cột mà template của mẫu đó hỗ trợ.

### Validation và export

Blocking errors:

- Mã rỗng trong một dòng đã có dữ liệu khác.
- Mã không tồn tại trong VSIC.
- Trùng mã ngành.
- Tên lưu trong store không khớp tên chính thức của mã (tự sửa lại tên trước khi báo lỗi nếu có thể).
- Thiếu ngành chính ở mẫu bắt buộc.
- Không có dòng ngành nào ở thủ tục bắt buộc kê khai ngành.

Export:

- STT sinh tự động theo thứ tự hiện tại, không yêu cầu người dùng nhập.
- DOCX nhận `ds_nganh` sau khi validation pass.
- Mỗi dòng phải đi đúng cột `STT / Tên ngành / Mã ngành / Ngành chính` của template.
- Nếu template chưa có bảng loop, generator phải dựng bảng/tag hợp lệ trước; không mô phỏng bảng chỉ bằng CSS vì dữ liệu sẽ không vào DOCX.

### Acceptance tests bắt buộc

1. Nhập `0111` -> tên tự thành `Trồng lúa`.
2. Nhập mã bắt đầu bằng `0` -> draft/export vẫn giữ số `0` đầu.
3. Nhập tên `trong lua` -> gợi ý `0111`; Enter điền đủ mã + tên.
4. Nhập mã sai -> báo VSIC, không điền tên giả và chặn export.
5. Đổi `0111` sang mã hợp lệ khác -> tên cập nhật, không giữ `Trồng lúa`.
6. Thêm 3 dòng -> STT 1/2/3; xóa dòng 2 -> STT còn 1/2.
7. Xóa dòng có dữ liệu -> có confirm; cancel không mất dữ liệu.
8. Trùng mã -> lỗi `DUPLICATE_INDUSTRY` và chặn export.
9. Chọn ngành chính dòng 2 -> mọi dòng khác thành false.
10. Xóa ngành chính -> yêu cầu chọn lại trước export.
11. Nhập ở PLI_M02, mở mẫu khác dùng `ds_nganh` -> thấy đúng danh sách và thứ tự.
12. Save/reload draft -> giữ rows, thứ tự, chi tiết và ngành chính.
13. DOCX PLI_M02/PLII_M01 có đúng số dòng, đúng cột và không còn loop tag.
14. Test phải chạy trên production blocks, không chỉ mock thủ công.

## Prompt implement mới: bảng ngành nghề + field-grid vốn điều lệ

```text
Bạn là Lead Coding Agent của repo:
C:\Users\Tuyen PC\orca\dangky_kinhdoanh

Hãy đọc toàn bộ PLAN.md, đặc biệt các phần:
- “Đánh giá độc lập sau MVP và kế hoạch tiếp theo”
- “Đặc tả luồng bảng ngành nghề: thêm/xóa dòng và tự điền tên”

Nhiệm vụ lần này chỉ gồm:
1. Sửa nền renderer/schema bảng production.
2. Triển khai hoàn chỉnh bảng ngành nghề pilot cho PLI_M02.
3. Triển khai field-grid vốn điều lệ pilot cho PLI_M02.
4. Bảo đảm draft, validation và DOCX export hoạt động end-to-end.

Không rollout sang tất cả mẫu trong cùng một PR.

PHASE 1 — SỬA NỀN BẢNG

- Xác nhận tools/docx_to_blocks.py tạo col zero-based và ghi rõ contract.
- Sửa app_web/ui/render.js để renderLoop dùng zero-based.
- Tổng số cột body phải lấy từ grid/header, không lấy max tag column.
- Giữ STT, cột không map, colspan và rowspan; field không được trượt cột.
- Thêm regression test đọc trực tiếp 8 loop production trong app/data/blocks.
- Với từng loop, assert số cột header bằng body và tag nằm đúng cột tiêu đề.
- Không xem test mock là bằng chứng production pass.
- Sinh/cập nhật mock từ production hoặc tạo script kiểm tra mock không sai contract.

PHASE 1B — COMPONENT EDITABLE-GRID DÙNG CHUNG

- Không viết add/delete/reorder riêng cho ds_nganh.
- Tạo API/controller generic cho mọi `block.t === "loop"`:
  addRow(loop, afterRowId), deleteRows(loop, rowIds), clearRows(loop),
  moveRow(loop, rowId, direction), duplicateRow(loop, rowId).
- Mỗi row có `_row_id` ổn định trong draft/UI; loại `_row_id` khỏi payload DOCX export.
- Metadata mỗi bảng quy định minRows/maxRows, action được phép, column types,
  required fields, duplicate keys và outputOnly fields.
- Áp dụng ngay cho các bảng production hiện có: ds_thanh_vien,
  ds_co_dong_sang_lap, ds_co_dong_nn, ds_cshhl, ds_tv_ho_gia_dinh,
  sau đó ds_nganh.
- Xóa dòng có dữ liệu phải confirm; xóa nhiều dòng confirm một lần.
- Cho phép người dùng chỉnh tự do ngay cả khi tạm thời vi phạm minRows;
  validator báo blocking trước export thay vì khóa thao tác chỉnh sửa.
- STT luôn được tính từ thứ tự array, không lưu như field.
- Error navigation dùng stable row id để vẫn đúng sau reorder/delete.

PHASE 2 — CANONICAL DS_NGANH

- Dùng state.store.loops.ds_nganh làm nguồn chân lý.
- Row contract:
  { ma_nganh, ten_nganh, chi_tiet, la_nganh_chinh }
- Thêm migration ds_nganh_kinh_doanh -> ds_nganh khi cần, không mất dữ liệu.
- Không gộp các loop có ý nghĩa nganh_bo_sung/nganh_xoa_bo nếu chưa có mapping nghiệp vụ rõ.

PHASE 3 — PLI_M02 INDUSTRY TABLE

- Cập nhật tools/build_form_maps.py để dựng bảng ngành nghề thật cho PLI_M02.
- Bảng gồm: STT, Mã ngành, Tên ngành, Chi tiết hoạt động (nếu dùng), Ngành chính.
- Thêm tags/loop vào app/templates/PLI_M02.docx và regenerate form_maps/blocks bằng pipeline hiện có; không chỉnh JSON generated thủ công nếu generator có thể sinh.
- Bảo đảm DOCX renderer nhân dòng đúng và không còn {#ds_nganh}/{/ds_nganh}.

PHASE 4 — TRA CỨU VSIC

- Dữ liệu tra cứu lấy local từ app/data/nganh_vsic.json.
- Nhập đủ mã hợp lệ tự điền tên chính thức.
- Mã rỗng xóa tên; mã sai không giữ tên cũ.
- Gõ mã chưa đủ hiện suggestion nhưng chưa báo blocking.
- Cho tìm tên có dấu/không dấu; ArrowUp/ArrowDown/Enter/Escape hoạt động.
- ten_nganh readonly mặc định.
- Mã lưu dạng string, không làm mất số 0 đầu.
- Chặn mã trùng và hỗ trợ một radio ngành chính.

PHASE 5 — QUẢN LÝ DÒNG

- Tích hợp bảng ngành với editable-grid chung, không tạo controller riêng.
- Thêm dòng sau dòng chọn, riêng ngành focus ma_nganh.
- Xóa một/nhiều dòng có dữ liệu phải confirm và không mất dữ liệu khi cancel.
- Giữ ít nhất một dòng trống trên UI.
- Action Lên/Xuống/nhân bản dùng chung; đánh lại STT sau thay đổi.
- Xóa ngành chính phải phát sinh validation yêu cầu chọn lại.
- Không cho xóa header hoặc cấu trúc bảng pháp lý.

PHASE 6 — FIELD-GRID VỐN ĐIỀU LỆ

- Không biến vốn điều lệ thành loop.
- Tạo metadata UI riêng app/data/ui_layouts/PLI_M02.json hoặc cấu trúc tương đương ổn định.
- Render nhóm vốn dạng field-grid HTKK: bằng số, bằng chữ, ngoại tệ/đơn vị nếu mẫu có.
- Các ô dùng đúng canonical keys hiện tại và export vào tag DOCX hiện có.
- Không hard-code theo block index và không tự ý đổi layout DOCX pháp lý.

VALIDATION

- VSIC_INVALID, DUPLICATE_INDUSTRY, PRIMARY_INDUSTRY_REQUIRED,
  INDUSTRY_REQUIRED và ROW_INCOMPLETE là blocking.
- Click lỗi phải mở đúng tab, chọn đúng dòng, scroll và focus đúng cell.
- Export phải bị chặn khi còn blocking error.

TEST BẮT BUỘC

- Chạy test hiện có.
- Thêm đủ 14 acceptance tests trong PLAN.md cho bảng ngành.
- Test production PLI_M02, PLI_M06 và PLII_M01; không chỉ mock.
- Chạy cùng một bộ contract test add/delete/reorder/duplicate cho ít nhất
  ds_nganh, ds_thanh_vien, ds_co_dong_sang_lap và ds_tv_ho_gia_dinh.
- Kiểm tra minRows không khóa thao tác xóa nhưng chặn export đúng lúc.
- Kiểm tra stable row id giữ đúng focus/error sau reorder và delete.
- Kiểm tra nhập -> autosave -> reload -> validation -> export.
- Render DOCX PLI_M02 thành PNG trên môi trường có LibreOffice và kiểm tra mọi trang.

RÀNG BUỘC

- Không reset/revert thay đổi không liên quan trong worktree.
- Không rename hàng loạt canonical keys.
- Không sửa engine DOCX ngoài phần thật sự cần cho loop/table.
- Dùng UTF-8.
- Commit tách nhỏ: table contract/tests, ds_nganh/VSIC, PLI_M02 generator,
  field-grid vốn, integration/E2E.

BÁO CÁO CUỐI

- File đã sửa/tạo.
- Contract schema cuối cùng.
- Kết quả test production và mock.
- Ảnh/render QA DOCX nếu môi trường hỗ trợ.
- Các mẫu còn lại chưa rollout.
- Rủi ro/migration còn lại.
```

---

## Chương trình hoàn thiện toàn bộ bảng trong 87 biểu mẫu

> Phần này mở rộng và **thay thế phạm vi rollout bảng hẹp trước đây**. Mục tiêu
> không còn là chỉ hoàn thiện `ds_nganh`, mà là phát hiện, dựng lại, nhập liệu,
> kiểm tra và xuất DOCX đúng cho **mọi vùng có bản chất là bảng** trong toàn bộ
> 87 biểu mẫu. Không được báo DONE chỉ vì các bảng đã biết trước đã xanh.

### Định nghĩa DONE cho phạm vi bảng

Một biểu mẫu chỉ được đánh dấu `TABLE_COMPLETE` khi:

1. Tất cả bảng trong bản mẫu pháp lý đã được ghi vào inventory có bằng chứng
   nguồn, kể cả bảng bị converter làm mất lưới và chỉ còn paragraph nối tiếp.
2. Bảng nhiều dòng dùng `editable-grid`; bảng có dòng cố định dùng
   `fixed-matrix`; bảng chỉ hiển thị kết quả dùng `output-table`. Không biến tất
   cả thành loop một cách máy móc.
3. Mọi cột/ô nhập có canonical key hoặc lý do `outputOnly`; không còn cột pháp
   lý bị bỏ trống do chưa map.
4. UI giữ đúng hàng/cột, border, colspan/rowspan, STT, loại input, đơn vị và
   computed totals; thao tác bàn phím/focus/error hoạt động.
5. Draft, migration, đồng bộ liên mẫu và export giữ đúng số dòng, thứ tự và
   semantic data.
6. DOCX structural test kiểm tra từng cell, số hàng, tổng, dấu `X` và không còn
   token; visual QA xác nhận không vỡ bảng/ngắt trang/clipping.
7. Mỗi một trong 87 mẫu có trạng thái cuối cùng trong manifest:
   `NO_TABLE`, `TABLE_COMPLETE`, hoặc `BLOCKED_LEGAL_REVIEW`. Không có trạng
   thái trống/`TODO`; mẫu blocked không được tính là DONE.

### Bằng chứng baseline hiện tại

Quét `app/data/blocks/*.json` tại thời điểm lập kế hoạch:

- 87 file production blocks.
- 3.913 paragraph blocks, 226 checkbox blocks.
- Chỉ có 9 loop blocks thuộc 8 mẫu (`PLII_M01`, `PLI_M02`, `PLI_M06`–`M11`).
- Có ít nhất 45 vùng bắt đầu bằng paragraph `STT` nhưng chưa phải bảng schema.
- Điều này chứng minh các bảng mất lưới không giới hạn ở ngành nghề; test 9 loop
  hiện tại không phải bằng chứng toàn bộ biểu mẫu đã có bảng.

Số liệu 45 là detector ban đầu, không phải inventory cuối cùng. Một số bảng
không có `STT` (nguồn vốn, bảng lựa chọn cố định, danh sách đơn vị trực thuộc)
và một số header bị nối thành một paragraph. Phase T0 phải quét cả XML/DOCX,
paragraph và nguồn mẫu pháp lý để không bỏ sót.

### Taxonomy component bảng

#### 1. `editable-grid` — danh sách số dòng thay đổi

Dùng khi người dùng có thể thêm/xóa/sắp xếp dòng, ví dụ:

- Ngành nghề.
- Thành viên, cổ đông, chủ sở hữu hưởng lợi.
- Thành viên hộ gia đình.
- Người đại diện theo ủy quyền khi có nhiều người.
- Chi nhánh, văn phòng đại diện, địa điểm kinh doanh được liệt kê.
- Sản phẩm/tài liệu yêu cầu cung cấp.
- Chi tiết “tài sản khác” nếu có nhiều tài sản.

Phải dùng controller chung hiện có: add/delete/clear/reorder/duplicate, stable
`_row_id`, confirm xóa, validation theo row ID và loại `_row_id` khỏi export.

#### 2. `fixed-matrix` — bảng có tập dòng pháp lý cố định

Dùng khi tên dòng do biểu mẫu quy định và người dùng chỉ điền giá trị:

- Nguồn vốn điều lệ: vốn ngân sách nhà nước, vốn tư nhân, vốn nước ngoài,
  loại nguồn vốn khác và tổng cộng theo đúng mẫu.
- Tài sản góp vốn: Đồng Việt Nam, ngoại tệ, vàng, quyền sử dụng đất, quyền sở
  hữu trí tuệ, tài sản khác và tổng số.
- Cơ cấu loại cổ phần và cổ phần được quyền chào bán.
- Các bảng chỉ tiêu đăng ký thuế đánh số cố định.

Không cho người dùng xóa dòng pháp lý cố định. Có thể cho mở sub-grid chi tiết
ở dòng “Tài sản khác”. Tổng và tỷ lệ phải tính từ numeric canonical values.

#### 3. `nested-grid` — bảng nhiều tầng/cột nhóm

Dùng cho bảng thành viên/cổ đông phức tạp có cá nhân/tổ chức, phần vốn/cổ phần,
loại tài sản và người đại diện theo ủy quyền. Renderer/generator phải bảo toàn
header nhiều hàng, `colspan`, `rowspan`; không làm phẳng khiến mất cột.

#### 4. `output-table`

Dùng cho bảng do cơ quan/engine tạo hoặc ô chỉ đọc. Vẫn phải giữ grid khi xuất,
nhưng không tạo ô nhập nếu người dùng không phải chủ thể kê khai.

### Manifest bắt buộc

Tạo source-of-truth, khuyến nghị:

```text
app/data/table_specs/
├── manifest.json
├── industry/
├── capital_assets/
├── people_ownership/
├── tax/
├── branches_locations/
└── administrative/
```

Mỗi entry của `manifest.json` tối thiểu:

```json
{
  "form_id": "PLI_M02",
  "section_id": "tai_san_gop_von",
  "title": "Tài sản góp vốn",
  "source_evidence": {
    "template": "app/templates/PLI_M02.docx",
    "heading": "8. Tài sản góp vốn",
    "page_or_anchor": "paragraph:150"
  },
  "kind": "fixed-matrix",
  "semantic_key": "co_cau_tai_san_gop_von",
  "required_columns": ["loai_tai_san", "gia_tri_vnd", "ty_le"],
  "status": "planned",
  "owner": "capital-assets",
  "tests": []
}
```

Manifest phải được generator/audit đọc được; không chỉ là tài liệu mô tả. Audit
phải fail nếu form có signature bảng nhưng chưa có entry, entry `planned` còn
tồn tại lúc release, hoặc spec khai cột nhưng template/blocks/export thiếu cột.

## Inventory nghiệp vụ ban đầu cần hoàn thiện

Danh sách dưới đây là minimum bắt buộc từ dữ liệu hiện có. Phase T0 có quyền
bổ sung thêm, không được xóa mục nếu chưa có bằng chứng mẫu đó thật sự không cần
bảng.

### A. Ngành nghề kinh doanh

#### Đăng ký/ngành hiện tại

- Đã có: `PLI_M02`, `PLII_M01` (vẫn phải test đầy đủ STT/ngành chính).
- Cần dựng: `PLI_M01`, `PLI_M03`, `PLI_M04`, `PLI_M05`, `PLI_M17`,
  `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`, `PLI_M72`, `PLII_M07`.
- `PLI_M72` chứa nhiều phần theo loại hình doanh nghiệp; từng phần phải map đúng
  bảng ngành tương ứng nhưng chỉ render phần được chọn, không nhân bản dữ liệu
  thành nhiều nguồn chân lý.

#### Thay đổi ngành

- `PLI_M12`: ba bảng semantic riêng:
  `nganh_bo_sung`, `nganh_xoa_bo`, `nganh_sua_chi_tiet`.
- `PLII_M02`: tối thiểu các bảng ngành bổ sung, ngành bỏ, sửa ngành chính và
  bảng ngành trong phần đăng ký lại/thông tin hiện tại theo đúng section được
  người dùng chọn.
- Không đồng bộ tự động giữa các loop khác nghĩa. VSIC lookup được dùng chung,
  nhưng row contract/validation/export tách riêng.

### B. Nguồn vốn, tài sản góp vốn và cổ phần

#### Nguồn vốn

Cần `fixed-matrix` tại:

- `PLI_M02`, `PLI_M03`, `PLI_M04`, `PLI_M05` — nguồn vốn điều lệ.
- `PLI_M12` — nguồn vốn điều lệ sau thay đổi.

Tối thiểu map tên loại nguồn vốn, giá trị, tỷ lệ (nếu mẫu có), tổng cộng. Tổng
nguồn vốn phải đối chiếu vốn điều lệ; chênh lệch là blocking hoặc warning theo
contract nghiệp vụ được duyệt.

#### Tài sản góp vốn

Cần `fixed-matrix` tại:

- `PLI_M01` — tài sản trong vốn đầu tư.
- `PLI_M02` — tài sản trong vốn điều lệ.
- `PLI_M12` — hai ngữ cảnh riêng: sau thay đổi vốn điều lệ và sau thay đổi vốn
  đầu tư; không dùng chung data nếu hai section cùng xuất hiện.

Các dòng pháp lý: Đồng Việt Nam, ngoại tệ tự do chuyển đổi, vàng, quyền sử dụng
đất, quyền sở hữu trí tuệ, tài sản khác, tổng số. Các cột tối thiểu: giá trị VNĐ
và tỷ lệ; ngoại tệ/tài sản khác phải có chi tiết theo yêu cầu mẫu. Validation:

- Tổng giá trị tài sản = vốn đầu tư/vốn điều lệ liên quan.
- Tổng tỷ lệ = 100% khi có kê khai.
- Giá trị không âm; ngoại tệ có loại tiền; tài sản khác có mô tả.
- Tổng là computed/outputOnly, không lưu hai nguồn số liệu mâu thuẫn.

#### Cơ cấu cổ phần

- `PLI_M04`: bảng loại cổ phần và bảng cổ phần được quyền chào bán.
- `PLI_M12`: bảng loại cổ phần sau thay đổi.
- `PLI_M72`: phần công ty cổ phần gồm mệnh giá, tổng số và các danh sách cổ
  đông; phải kiểm tra có bảng loại cổ phần/cơ cấu cần dựng thêm từ mẫu gốc.

Các bảng fixed rows giữ các loại cổ phần theo mẫu. Tính giá trị = số lượng ×
mệnh giá nếu applicable, tổng số lượng/giá trị/tỷ lệ và đối chiếu vốn điều lệ.

### C. Thành viên, cổ đông, vốn góp và chủ sở hữu hưởng lợi

#### Các bảng hiện có nhưng phải audit lại đủ cột

- `PLI_M06`: thành viên TNHH.
- `PLI_M07`: cổ đông sáng lập.
- `PLI_M08`: cổ đông là nhà đầu tư nước ngoài.
- `PLI_M09`: thành viên hợp danh.
- `PLI_M10`, `PLI_M11`: chủ sở hữu hưởng lợi.
- `PLII_M01`: thành viên hộ gia đình.

Không được coi là hoàn chỉnh chỉ vì loop tồn tại. Phải so với header mẫu gốc để
bổ sung các cột đang bị đơn giản hóa, đặc biệt:

- Thời hạn góp vốn.
- Loại cổ phần, số lượng, giá trị và tỷ lệ.
- Loại tài sản, số lượng, giá trị tài sản góp vốn.
- Dữ liệu cá nhân/tổ chức khác nhau.
- Người đại diện theo pháp luật/ủy quyền và tỷ lệ phần vốn được đại diện.
- Chữ ký là `outputOnly`, không phải text input thông thường.

`PLI_M09` hiện có dấu hiệu chứa nhiều phần danh sách nối tiếp từ quá trình tách
nguồn; phải audit boundary/source trước khi sửa, tránh map nhầm bảng M06/M07/M08
vào mẫu M09.

#### Các bảng còn thiếu rõ ràng

- `PLII_M02`: danh sách thành viên hộ gia đình sau thay đổi và bảng thành viên
  trong phần thông tin đăng ký lại nếu mẫu yêu cầu.
- `PLII_M07`: danh sách thành viên hộ gia đình.
- `PLI_M72`: danh sách thành viên TNHH, cổ đông sáng lập, cổ đông nước ngoài và
  thành viên hợp danh trong các section loại hình khác nhau.
- `PLI_M12`: người đại diện theo ủy quyền sau thay đổi nếu section cho phép nhiều
  người; audit xem cần editable/nested grid thay vì field đơn.

### D. Bảng thông tin đăng ký thuế

Các section `STT | Các chỉ tiêu thông tin đăng ký thuế` hiện đang là paragraph
rời ở tối thiểu:

- `PLI_M01`, `PLI_M02`, `PLI_M06`, `PLI_M08`, `PLI_M09`, `PLI_M12`,
  `PLI_M17`, `PLI_M19`, `PLI_M23`, `PLI_M25`, `PLII_M02`.

Đây chủ yếu là `fixed-matrix`/section-grid, không phải danh sách người dùng tự
thêm dòng. Giữ mã chỉ tiêu (6.1, 6.2…), nhãn, ô nhập nhiều cột cũ/mới nếu mẫu
có, checkbox và nhóm địa chỉ. Canonical key dùng chung giữa mẫu chỉ khi ý nghĩa
giống hoàn toàn; không map chỉ dựa vào số thứ tự chỉ tiêu.

### E. Chi nhánh, văn phòng đại diện và địa điểm kinh doanh

Audit và dựng `editable-grid` cho các section có từ “liệt kê/các ... sau”:

- `PLI_M54`: các chi nhánh/văn phòng đại diện/địa điểm cùng tạm ngừng hoặc tiếp
  tục kinh doanh nếu section cho phép nhiều đơn vị.
- `PLI_M63`: địa điểm kinh doanh trực thuộc chi nhánh.
- `PLI_M66`: danh sách đơn vị và địa điểm trực thuộc đang làm thủ tục chấm dứt.
- `PLI_M68`: các chi nhánh/văn phòng đại diện/địa điểm đang chấm dứt.
- `PLI_M75`: các đơn vị/địa điểm trực thuộc cần khôi phục.

Row contract tối thiểu tùy mẫu: loại đơn vị, tên, mã số/mã số thuế, địa chỉ,
tình trạng pháp lý, ngày hiệu lực và ghi chú. Không ép các section khác nghiệp
vụ dùng chung loop nếu việc đồng bộ có thể làm sai hồ sơ.

### F. Sản phẩm/dịch vụ cung cấp thông tin

- `PLI_M78`: bảng `STT | Tên sản phẩm | Số lượng sản phẩm`, gồm các dòng sản
  phẩm quy định và “Sản phẩm khác”. Audit mẫu gốc để quyết định fixed rows hay
  hybrid fixed + editable details; số lượng phải là integer không âm.

### G. Các bảng hành chính/output-only và bảng không có STT

Phase T0 phải quét thêm:

- Header bị nối dạng `STTTên...` trong một paragraph.
- Các đoạn “Danh sách…”, “Liệt kê…”, “Các … sau” không có STT riêng.
- Bảng quyết định/thông báo do cơ quan đăng ký kinh doanh tạo.
- Bảng có đường kẻ nhưng chỉ chứa output hoặc chữ ký.

Nếu không cần nhập, khai `output-table`; không được bỏ grid khỏi DOCX chỉ vì UI
không nhập liệu.

## Kiến trúc generator và schema mới

1. Tách table specs khỏi dictionary tập trung trong `build_form_maps.py` để các
   nhóm có thể làm song song, ví dụ một JSON/module mỗi form hoặc mỗi domain.
2. Generator đọc manifest/spec, tìm anchor theo section + heading + context;
   không dùng mỗi regex `STT` vì một mẫu có nhiều bảng.
3. Mỗi spec khai:
   - `kind`, `loop/semanticKey`, `headers`, `columns`, `headerRows`.
   - `fixedRows` hoặc `minRows/maxRows`.
   - `stt`, `colspan/rowspan`, `inputType`, `required`, `outputOnly`.
   - totals/formulas, duplicate keys, cross-field rules.
   - source anchor và stop boundary để không xóa paragraph của bảng kế tiếp.
4. Pipeline duy nhất:
   source/spec → template tagged → `form_maps` → blocks → mock fixture → tests.
   Không chỉnh generated JSON thủ công.
5. Generator phải idempotent: chạy hai lần không nhân đôi bảng, không đổi file
   ngoài allowlist và tạo cùng output byte/semantic-equivalent.
6. Giữ backward-compatible canonical keys/draft migration; thay đổi loop name
   phải có version + migration + test.

## Kế hoạch thực hiện bằng worktree/subagent

### Wave T0 — census toàn bộ 87 mẫu (song song, chỉ đọc production)

- Agent T0-A: `PLI_M01–PLI_M12` — ngành, vốn, tài sản, cổ phần, danh sách.
- Agent T0-B: `PLI_M13–PLI_M80` — chi nhánh/địa điểm, hành chính, sản phẩm và
  các bảng bị nối header.
- Agent T0-C: `PLII_M01–PLII_M28` — hộ kinh doanh, thành viên, ngành, thuế.

Mỗi agent ghi một fragment manifest riêng để tránh conflict. Với mỗi form:

- Đối chiếu blocks, tagged template, XML table/header và nguồn pháp lý.
- Chụp/ghi bằng chứng heading + cột + loại bảng.
- Đánh dấu `already_complete`, `missing_grid`, `partial_columns`, `output_only`
  hoặc `no_table`.
- Không sửa generator/template trong Wave T0.

Lead merge fragments, audit đủ 87/87 mẫu và khóa `table-manifest-v1` trước khi
coding rollout. Mọi mục mới phát hiện trở thành scope bắt buộc.

### Wave T1 — nền component và generator (tuần tự theo dependency)

- Agent T1-A: schema manifest/spec + audit detector + idempotency tests.
- Agent T1-B: renderer `fixed-matrix`, `nested-grid`, `output-table`, formula và
  accessibility; không hard-code form ID.
- Agent T1-C: generator modular, anchor/boundary an toàn, tag totals/STT và
  production block contract.
- Agent T1-D: domain validation/totals/migration; chạy sau khi contract T1-A ổn.

Integrate T1 rồi chạy full regression; chỉ sau đó mới tạo worktree rollout.

### Wave T2 — rollout theo domain (song song qua spec file tách biệt)

- Agent T2-A `industry-all`: toàn bộ bảng ngành hiện tại/bổ sung/xóa/sửa.
- Agent T2-B `capital-assets`: nguồn vốn, tài sản góp vốn, loại cổ phần, cổ
  phần chào bán và đối chiếu totals.
- Agent T2-C `people-ownership`: thành viên, cổ đông, chủ sở hữu hưởng lợi,
  người đại diện, thành viên hộ gia đình; audit/nâng cấp cả loop cũ.
- Agent T2-D `tax-grids`: toàn bộ bảng chỉ tiêu đăng ký thuế.
- Agent T2-E `branches-products-admin`: đơn vị trực thuộc, sản phẩm và bảng
  hành chính/output-only.

Subagent chỉ commit spec/source/test thuộc domain mình. Lead merge spec và là
người duy nhất regenerate global `form_maps.json/js`, templates và blocks.

### Wave T3 — integration theo batch

Không merge một lần 87 mẫu. Chia batch:

1. Thành lập doanh nghiệp: `PLI_M01–M11`.
2. Thay đổi doanh nghiệp: `PLI_M12–M26`.
3. Đơn vị trực thuộc, trạng thái và hành chính: các mẫu `PLI` còn lại.
4. Hộ kinh doanh: `PLII_M01–M28`.

Mỗi batch phải pass structural DOCX và visual sample trước batch kế tiếp. Nếu
generated diff ngoài allowlist, dừng và sửa generator trước khi tiếp tục.

### Wave T4 — E2E và visual release QA

- Test UI thật cho mỗi loại component: editable, fixed, nested, output.
- Test 0/1/min/max/100 rows, Unicode, text dài, tiền lớn, tỷ lệ thập phân.
- Test draft/save/reload/reorder/export và đồng bộ liên mẫu.
- Render DOCX → PDF/PNG bằng LibreOffice/Word; kiểm tra toàn bộ bảng ở ít nhất
  một file mỗi domain và mọi mẫu có nested grid.
- Máy release phải smoke `.exe` local, không có Python, đường dẫn có dấu/khoảng
  trắng và WebView2 runtime theo chiến lược đóng gói.

## Acceptance gates cho chương trình toàn bộ bảng

1. Manifest có 87/87 form, không entry `planned/unknown`.
2. Detector paragraph `STT`, `STTTên`, “Danh sách”, “Liệt kê”, “Các … sau”
   không còn phát hiện vùng bảng chưa được classify.
3. Mọi entry `TABLE_COMPLETE` có spec, production blocks và ít nhất một test.
4. Không còn bảng pháp lý chỉ là chuỗi paragraph header/value rời nếu bảng đó
   cần nhập hoặc cần giữ lưới khi xuất.
5. Các bảng ngành, nguồn vốn, tài sản, cổ phần, thành viên/cổ đông, thuế,
   chi nhánh/địa điểm và sản phẩm đều đạt contract ở trên.
6. Loop cũ PLI_M06–M11 được audit đủ cột, không chỉ giữ trạng thái hiện tại.
7. Totals tài sản/nguồn vốn/cổ phần đối chiếu đúng vốn liên quan; tỷ lệ đúng
   policy và lỗi blocking trước export.
8. DOCX không còn tag, không lệch cột/STT/dấu X, không mất rowspan/colspan.
9. Full regression hiện có và test mới đều PASS; NOT RUN không tính PASS.
10. Visual QA và `.exe` smoke có bằng chứng. Chỉ khi đó mới báo TABLES DONE.

## Prompt implement toàn bộ phần cần kẻ bảng

```text
Bạn là Lead/Integrator Agent của repo:
C:\Users\Tuyen PC\orca\dangky_kinhdoanh

Hãy đọc toàn bộ PLAN.md, ưu tiên chương:
“Chương trình hoàn thiện toàn bộ bảng trong 87 biểu mẫu”.

MỤC TIÊU
Dứt điểm mọi phần có bản chất là bảng trong toàn bộ 87 biểu mẫu: phát hiện đủ,
phân loại đúng, dựng UI có lưới, nhập liệu, validation, draft, đồng bộ và xuất
DOCX đúng. Không giới hạn ở ngành nghề hoặc 9 loop đang có. Chỉ báo DONE khi
10 Acceptance Gates của chương này đều đạt.

NGUYÊN TẮC AN TOÀN
1. Kiểm tra git status/diff và tạo baseline sạch; không reset/revert thay đổi
   của người dùng. Không commit cache/output test.
2. Mỗi subagent dùng branch + Git worktree riêng ngoài repo chính.
3. Không cho hai agent sửa cùng file. Trước rollout phải tách specs theo
   form/domain; Lead là người duy nhất regenerate global artifacts.
4. Không chỉnh generated JSON thủ công. Pipeline phải idempotent.
5. Không gọi test mock là bằng chứng production; không nới test để hợp thức hóa
   ô/cột rỗng.
6. Không tự gộp loop khác nghĩa. Thiếu căn cứ pháp lý thì ghi
   BLOCKED_LEGAL_REVIEW kèm bằng chứng, không suy diễn.

WAVE T0 — CENSUS TRƯỚC KHI CODE
Spawn tối đa 3 subagent song song:
- T0-A audit PLI_M01–M12.
- T0-B audit PLI_M13–M80.
- T0-C audit PLII_M01–M28.

Mỗi agent chỉ đọc production và ghi manifest fragment riêng. Phải xem blocks,
DOCX/XML, form_maps và mẫu nguồn; nhận diện cả STT rời, header nối “STTTên…”,
“Danh sách”, “Liệt kê”, “Các … sau” và bảng không có STT. Mỗi form bắt buộc có
NO_TABLE/TABLE_COMPLETE/BLOCKED_LEGAL_REVIEW và evidence. Lead merge đủ 87/87,
chạy detector và commit table-manifest-v1. Không bắt đầu rollout khi census chưa
đủ.

WAVE T1 — PLATFORM
Thực hiện theo dependency trong PLAN:
- schema/audit manifest;
- renderer fixed-matrix/nested-grid/output-table;
- modular generator + anchor/boundary + idempotency;
- validation/totals/migration.
Integrate và full regression trước Wave T2.

WAVE T2 — DOMAIN ROLLOUT
Spawn các agent có spec folder riêng:
- industry-all;
- capital-assets;
- people-ownership;
- tax-grids;
- branches-products-admin.

Phạm vi tối thiểu chính là inventory A–G trong PLAN. Đặc biệt phải làm:
- PLI_M01/M02/M12 tài sản góp vốn;
- PLI_M02/M03/M04/M05/M12 nguồn vốn;
- PLI_M04/M12 cơ cấu cổ phần;
- các bảng ngành hiện tại và thay đổi;
- audit/nâng cấp đủ cột PLI_M06–M11;
- bảng thuế ở mọi mẫu được liệt kê;
- PLII_M02/M07 và PLI_M72 các danh sách thành viên/cổ đông;
- các đơn vị trực thuộc PLI_M54/M63/M66/M68/M75;
- sản phẩm PLI_M78.

Lead merge source/spec, regenerate tập trung và review allowlist. Chia integration
theo bốn batch trong PLAN; không merge 87 mẫu một lần.

YÊU CẦU TEST MỖI BẢNG
- Contract header/body/colspan/rowspan và đúng loại component.
- Add/delete/reorder/duplicate cho editable; fixed rows không được xóa.
- Input type, required/outputOnly, stable row ID và error navigation.
- Formula/totals và cross-check vốn/tỷ lệ.
- Draft round-trip và migration.
- DOCX từng cell, STT, dấu X, totals, số hàng, leftover tokens.
- Visual PDF/PNG cho bảng phức tạp; không chạy được phải báo NOT RUN.

BÁO CÁO MỖI WAVE
- Agent, worktree, branch, commit hash, ownership.
- Inventory/spec/file thay đổi.
- Test command và PASS/FAIL/NOT RUN.
- Generated diff ngoài allowlist.
- Mẫu BLOCKED_LEGAL_REVIEW và bằng chứng cần người dùng quyết định.
- Tỷ lệ TABLE_COMPLETE trên 87 mẫu và số table sections hoàn tất/tổng số.

Không báo DONE theo phần trăm ước lượng. Chỉ báo TABLES DONE khi manifest 87/87,
không còn signature bảng chưa classify, mọi table entry có production test,
full regression + visual QA + .exe smoke đạt đủ Acceptance Gates trong PLAN.
```

---

## Checkpoint sau kiểm tra độc lập — 2026-08-26

Phần này là trạng thái mới nhất và **thay thế các nhận định tiến độ cũ** nếu có
mâu thuẫn. Các contract, inventory A–G và Acceptance Gates ở trên vẫn giữ nguyên.

### Baseline đã xác nhận

- Nhánh chính tại commit `47ddaf3` (`integrate2: regenerate form_maps 13 mau
  rollout + audit ky vong 24 loop`); worktree chính sạch tại thời điểm audit.
- Wave 1 đã hoàn tất: sửa DOCX `PLII_M01` (STT + dấu X ngành chính), metadata
  `bat_buoc`/`forms_oneOf`, export gate, request token chống race khi đổi case,
  autosave đồng bộ `dirty=false` và phục hồi lựa chọn từ draft.
- Wave 2 đã thêm bảng ngành cho 13 mẫu: `PLI_M01`, `PLI_M03`, `PLI_M04`,
  `PLI_M05`, `PLI_M12`, `PLI_M17`, `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`,
  `PLI_M72`, `PLII_M02`, `PLII_M07`.
- Production hiện có khoảng 3.853 paragraph blocks, 226 checkbox blocks và 24
  loop trên 21 mẫu. Form specs đã được tách theo domain trong `tools/form_specs/`.
- Các suite DOM, domain, grid, loop production, acceptance, form flow, household,
  contract release, industry formation/change/household, smoke web assets,
  block/content/engine audit và compile/import đều PASS trong lần audit. Kết quả
  xanh này chưa thay thế visual QA hoặc clean-machine `.exe` smoke.

### Mức hoàn thành thực tế

| Hạng mục | Trạng thái | Nhận định |
| --- | --- | --- |
| Luồng chọn mẫu, state, autosave, draft | DONE | Có regression test |
| Nền editable-grid/loop | STABLE BASELINE | Chưa bao phủ fixed/nested/output |
| Bảng ngành nghề | PARTIAL | Đã rollout rộng nhưng còn điểm mù M72 và PLII_M02 |
| Census 87 mẫu | PARTIAL | Có fragment 75/87 ở worktree, chưa có manifest hợp nhất |
| Vốn, tài sản, cổ phần | NOT ROLLED OUT | Là ưu tiên domain kế tiếp |
| Thành viên/cổ đông/người đại diện | PARTIAL | Loop cũ cần audit đủ cột; còn bảng thiếu |
| Bảng thuế/fixed matrix | NOT ROLLED OUT | Cần component chung trước |
| Nested/output table | NOT IMPLEMENTED | Chưa có renderer/schema đầy đủ |
| Visual DOCX và `.exe` | NOT RUN/NOT READY | Chưa đủ bằng chứng release |

Ước lượng để quản trị tiến độ, không dùng làm gate: lõi MVP khoảng 70%; riêng mục
tiêu “dứt điểm toàn bộ bảng” khoảng 30–35%. Chỉ Acceptance Gates mới quyết định
`TABLES DONE`.

### Hai điểm mù phải sửa trước rollout domain mới

1. **`PLI_M72`:** mẫu có năm section loại hình với năm lưới ngành riêng. Generator
   hiện chỉ dựng occurrence đầu tiên; bốn lưới còn lại có nguy cơ vẫn là paragraph.
   Spec đã ghi `gap_nghiepvu`, nhưng test hiện chỉ đòi một loop nên xanh giả về độ
   đầy đủ. Phải hỗ trợ anchor occurrence/section identity và test đủ cả năm section.
2. **`PLII_M02`:** không được gộp toàn bộ nghiệp vụ vào một `ds_nganh`. Phải audit
   và tạo semantic loop riêng cho ngành bổ sung, xóa bỏ, sửa đổi và danh sách hiện
   tại/đăng ký lại theo đúng section thực tế. Mỗi section có test độc lập.

Detector còn khoảng 30 signature paragraph `STT` chưa thành table block. Đây là
queue để phân loại, không mặc định cả 30 đều là lỗi. Mỗi signature phải kết thúc
ở một trong các trạng thái: có table spec, xác nhận `NO_TABLE`, `OUTPUT_ONLY`, hoặc
`BLOCKED_LEGAL_REVIEW` kèm evidence.

### Trạng thái census/worktree

- `T0-B` đã kiểm kê 47 mẫu: 20 `BLOCKED_LEGAL_REVIEW`, 2 `TABLE_COMPLETE`,
  25 `NO_TABLE`; fragment chưa merge vào `main`.
- `T0-C` đã kiểm kê 28 mẫu: 2 `BLOCKED`, 1 `TABLE_COMPLETE`, 25 `NO_TABLE`;
  fragment chưa merge vào `main`.
- `T0-A` chưa có census commit được xác nhận. Vì vậy mới có dữ liệu sơ bộ 75/87,
  chưa có `app/data/table_specs/manifest.json` chuẩn và chưa đạt gate T0.
- Không merge mù hai fragment: Lead phải review schema/evidence, chuẩn hóa status,
  hoàn tất T0-A rồi mới sinh manifest 87/87.

### Rủi ro tích hợp và desktop release

- `main` local đang đi trước `origin/main` 36 commit và đi sau 2 commit tại thời
  điểm audit. Hai commit remote có dấu hiệu là upload mã cũ/cache; không chạy
  `git pull` mù. Tạo nhánh backup, inspect diff rồi cherry-pick/merge có chọn lọc.
- `.webview_deps` đã bỏ khỏi Git nhưng `app_web/main.py` còn đường dẫn vendored.
  Import local thành công có thể do môi trường đã cài `pywebview`; chưa chứng minh
  chạy được trên máy sạch.
- Chưa có build spec/pipeline `.exe` được xác nhận. Release gate bắt buộc build
  tái lập được, khai báo dependency và smoke trên Windows không có Python.

## Kế hoạch tiếp theo từ checkpoint 2026-08-26

### P0 — Khóa baseline và hoàn tất T0 (blocking)

1. Tạo backup branch/tag tại `47ddaf3`; inspect hai commit remote, không pull mù.
2. Review fragment T0-B/T0-C read-only; chuẩn hóa schema và status.
3. Chạy lại T0-A cho `PLI_M01–PLI_M12` trong worktree riêng.
4. Lead hợp nhất thành `app/data/table_specs/manifest.json`, chứng minh đủ 87/87.
5. Chạy detector; mọi signature phải được classify. Commit `table-manifest-v1`.

Có thể chạy song song ba lane không ghi trùng file: agent T0-A census, agent review
T0-B và agent review T0-C. Lead là người duy nhất tạo manifest hợp nhất.

### P1 — Dứt điểm domain ngành nghề (blocking trước domain mới)

1. Mở rộng generator để định danh nhiều occurrence bằng section/anchor/boundary.
2. Dựng đủ năm lưới ngành của `PLI_M72`; test số section, semantic key và DOCX.
3. Tách đầy đủ các loop ngành của `PLII_M02`; thêm test từng nghiệp vụ.
4. Thêm negative audit: không còn signature ngành chưa classify.
5. Regenerate tập trung, review allowlist, chạy full regression.

P1 generator và spec có quan hệ phụ thuộc; không cho hai agent cùng sửa generator.
Một agent sở hữu generator/contract, các agent spec/test chỉ bắt đầu sau khi contract
được tích hợp hoặc làm trên file tách biệt không chạm generated artifacts.

### P2 — Hoàn thiện nền table component

1. Chốt schema cho `fixed-matrix`, `nested-grid`, `output-table` và editable-grid.
2. Triển khai renderer/controller dùng chung: add/delete/insert/reorder khi policy
   cho phép; fixed row không được xóa; stable row ID, keyboard và accessibility.
3. Thêm formula/totals, cross-field validation, draft migration và export gate.
4. Nâng generator với boundary an toàn, rowspan/colspan, totals/STT và idempotency.
5. Có contract test + production fixture cho từng loại component trước rollout.

### P3 — Rollout domain theo thứ tự ưu tiên

Sau P2, chạy song song qua spec folder/file ownership tách biệt:

1. `capital-assets`: tài sản góp vốn, nguồn vốn, vốn điều lệ, cơ cấu cổ phần.
2. `people-ownership`: thành viên, cổ đông, chủ sở hữu hưởng lợi, người đại diện;
   audit/nâng cấp toàn bộ loop cũ `PLI_M06–M11`.
3. `tax-grids`: mọi bảng chỉ tiêu đăng ký thuế/fixed matrix trong manifest.
4. `branches-products-admin`: đơn vị trực thuộc, sản phẩm, bảng hành chính/output.

Lead merge spec theo từng batch T3 và là người duy nhất regenerate global artifacts.
Không merge toàn bộ 87 mẫu trong một lần.

### P4 — Release gate

1. Full structural regression cho 87/87 mẫu và mọi table entry.
2. Visual QA DOCX → PDF/PNG theo domain và cho mọi nested grid.
3. Test dữ liệu biên: 0/1/max/100 dòng, Unicode, text dài, tiền/tỷ lệ lớn.
4. Chốt dependency/build spec, build `.exe` tái lập và smoke máy Windows sạch.
5. Chỉ báo `TABLES DONE` khi đủ 10 Acceptance Gates; `NOT RUN` không tính PASS.

## Prompt bàn giao cho agent có context mới (dùng từ checkpoint 2026-08-26)

```text
Bạn là Lead/Integrator Agent tiếp quản repo:
C:\Users\Tuyen PC\orca\dangky_kinhdoanh

MỤC TIÊU CUỐI
Hoàn thiện dứt điểm mọi phần có bản chất là bảng trong toàn bộ 87 biểu mẫu đăng ký
kinh doanh: UI nhập trực tiếp kiểu HTKK, thêm/xóa/sắp xếp dòng theo policy, tự đồng
bộ dữ liệu chung, validation/totals, draft và xuất DOCX đúng lưới pháp lý. Sau đó
đóng gói app desktop `.exe` chạy local. Không giới hạn scope ở bảng ngành nghề.

ĐỌC TRƯỚC KHI LÀM
1. Đọc toàn bộ PLAN.md, ưu tiên:
   - “Chương trình hoàn thiện toàn bộ bảng trong 87 biểu mẫu”;
   - “Checkpoint sau kiểm tra độc lập — 2026-08-26”;
   - “Kế hoạch tiếp theo từ checkpoint 2026-08-26”;
   - 10 Acceptance Gates.
2. Kiểm tra `git status --short`, `git log --oneline --decorate -20`, worktree và
   branch hiện hữu. Không giả định trạng thái vẫn giống checkpoint.
3. Baseline audit là commit `47ddaf3`, nhưng hãy xác minh HEAD hiện tại trước khi
   tạo branch/worktree.

CONTEXT ĐÃ BIẾT
- Wave 1 đã xong: PLII_M01 STT/X, bat_buoc/forms_oneOf, export gate, chống race,
  autosave dirty=false và draft restore.
- Wave 2 đã rollout ngành cho 13 mẫu; production có 24 loop trên 21 mẫu.
- Test hiện có đều PASS tại checkpoint, nhưng đó chưa phải bằng chứng toàn bộ bảng.
- PLI_M72 còn điểm mù: cần đủ 5 lưới ngành theo 5 section loại hình; test cũ chỉ
  yêu cầu 1 loop.
- PLII_M02 cần các semantic loop ngành riêng (bổ sung/xóa/sửa/hiện tại), không được
  coi một ds_nganh là hoàn tất.
- T0-B có census 47 mẫu và T0-C có 28 mẫu ở worktree/branch riêng, chưa merge.
  T0-A chưa được xác nhận; main chưa có manifest 87/87.
- Còn khoảng 30 signature STT cần classify. Fixed-matrix, nested-grid và
  output-table chưa hoàn thiện. Vốn/tài sản/cổ phần/thuế còn phần lớn chưa rollout.
- Local main từng ahead origin 36 và behind 2; không `git pull` mù.
- `.exe`/clean-machine packaging chưa được chứng minh.

NGUYÊN TẮC LÀM VIỆC
- Bảo toàn mọi thay đổi của người dùng; không reset/revert/overwrite ngoài scope.
- Dùng subagent song song chỉ cho task độc lập. Mỗi agent có branch + Git worktree
  riêng ngoài repo và ownership file không chồng lấn.
- Lead không sửa file agent đang sở hữu. Không cho nhiều agent cùng sửa generator,
  `app.js`, renderer hoặc generated global artifacts.
- Agent chỉ commit source/spec/test thuộc scope. Lead là người duy nhất regenerate
  `form_maps.json/js`, templates và blocks toàn cục sau khi merge specs.
- Không sửa generated JSON thủ công; generator phải idempotent và diff nằm trong
  allowlist. Không nới test để hợp thức hóa thiếu bảng/cột.
- Không tự suy diễn pháp lý. Ghi `BLOCKED_LEGAL_REVIEW` kèm heading, cột, source và
  câu hỏi cụ thể khi thiếu căn cứ.
- Mỗi wave báo command test và PASS/FAIL/NOT RUN. NOT RUN không được gọi là PASS.

THỨ TỰ THỰC HIỆN BẮT BUỘC

P0 — BASELINE + CENSUS
1. Xác minh HEAD/worktree/remote divergence; tạo backup branch/tag an toàn.
2. Inspect hai commit remote, không pull/merge mù.
3. Spawn tối đa 3 agent độc lập: hoàn tất T0-A; review T0-B; review T0-C.
4. Mỗi agent chỉ ghi fragment/evidence riêng. Lead chuẩn hóa và hợp nhất manifest.
5. Gate: `app/data/table_specs/manifest.json` đủ 87/87, mọi signature được classify,
   rồi commit `table-manifest-v1`. Chưa đạt thì không rollout domain mới.

P1 — CLOSE INDUSTRY BLIND SPOTS
1. Nâng generator hỗ trợ occurrence/section identity và boundary an toàn.
2. Hoàn thiện đủ 5 lưới ngành PLI_M72.
3. Tách đủ semantic loops ngành PLII_M02.
4. Thêm structural/DOCX test từng section và detector negative.
5. Regenerate tập trung, review allowlist, full regression.

P2 — TABLE PLATFORM
Triển khai contract/schema/renderer/controller/generator/test cho editable-grid,
fixed-matrix, nested-grid và output-table; gồm policy thêm/xóa/reorder, fixed rows,
stable ID, formulas/totals, validation, draft migration, accessibility và export.

P3 — DOMAIN ROLLOUT
Sau khi P2 xanh, giao các worktree tách biệt cho:
- capital-assets;
- people-ownership;
- tax-grids;
- branches-products-admin.
Tích hợp theo bốn batch trong PLAN, không merge 87 mẫu cùng lúc.

P4 — RELEASE
Full structural regression 87/87, visual DOCX/PDF/PNG, dữ liệu biên, build `.exe`
tái lập và smoke trên Windows sạch không có Python.

BÁO CÁO SAU MỖI WAVE
- Agent/worktree/branch/commit/ownership.
- Manifest entries và table sections hoàn tất/tổng số.
- File/spec/generated diff trong và ngoài allowlist.
- Tất cả lệnh test cùng PASS/FAIL/NOT RUN.
- BLOCKED_LEGAL_REVIEW cùng evidence và quyết định cần người dùng.
- Rủi ro còn lại và gate tiếp theo.

Không báo DONE theo phần trăm. Chỉ báo TABLES DONE khi đủ manifest 87/87, không còn
signature chưa classify, mọi table entry có production test, full regression và
visual QA đều PASS, đồng thời `.exe` smoke đạt đủ 10 Acceptance Gates trong PLAN.md.

Hãy bắt đầu bằng audit read-only và trình bày baseline thực tế. Sau đó tạo worktree
và điều phối P0; không nhảy thẳng vào sửa bảng vốn/tài sản trước khi gate T0 đạt.
```

---

## Wave P1-LAYOUT — chuẩn hóa hình thức và độ trung thành biểu mẫu

### Lý do bổ sung

Visual audit trên giao diện web phát hiện các lỗi không được các structural test
hiện tại bắt:

1. Toàn bộ biểu mẫu trên UI đang có hiện tượng hiển thị marker/descriptor kỹ thuật
   ở đầu tờ khai (ví dụ `PL1 - Mau so 1: ...`, `PL2 - Mau so ...`), dù đây không
   phải nội dung người dùng cần nhập. Pattern tĩnh hiện thấy trực tiếp trong nhiều
   block; các mẫu còn lại vẫn phải audit cả block, wrapper/title do app sinh và
   source, không được thu hẹp scope theo số pattern grep được.
2. Quốc hiệu, tiêu ngữ và đường kẻ nằm trong một run có `\n`, nhưng HTML làm phẳng
   whitespace nên ba dòng bị dồn thành một dòng và nhìn như canh lề sai.
3. Số chú thích chân trang bị làm phẳng vào chữ, ví dụ `Tôi là1` thay vì footnote
   superscript/tooltip hoặc nhãn sạch `Tôi là`.
4. Block schema mới giữ chủ yếu `align=left|center|right`, chưa giữ đủ first-line
   indent, left/right indent, tab stop, spacing before/after, line spacing,
   keep-with-next và run superscript/subscript từ DOCX.
5. Các tiêu đề, dòng ngày tháng, `Kính gửi`, ghi chú và footnote chưa có semantic
   role; CSS phải đoán từ text hoặc áp cùng một style cho mọi paragraph.

Không sửa riêng `PLI_M01` bằng CSS selector theo form ID. Mục tiêu là pipeline
trích xuất và render trung thành cho toàn bộ 87 mẫu, với override tường minh chỉ
khi source thật sự đặc biệt.

### Vị trí trong roadmap

P1-LAYOUT chạy sau khi P1-UI contract ổn định và phải PASS trước khi rollout P3
hàng loạt. Có thể chuẩn bị census/layout contract song song với P1-UI nếu ownership
file tách biệt, nhưng không cho hai agent cùng sửa `render.js`, `style.css` hoặc
`docx_to_blocks.py`.

Visual fidelity của UI và visual fidelity của DOCX là hai gate riêng:

- **UI preview:** dễ đọc, đúng dòng/căn lề, không lộ marker kỹ thuật, footnote rõ.
- **DOCX output:** không được làm mất nội dung pháp lý, footnote, numbering, bảng,
  placeholder hoặc style cần thiết của file xuất.

### Contract semantic role

Mỗi paragraph có thể có `role` tường minh, tối thiểu:

```text
source-indicator
form-number
national-header
national-motto
national-separator
date-line
form-title
form-subtitle
salutation
body
section-heading
note
footnote
signature
```

`role` phải được sinh từ source/generator bằng rule có test và có thể override qua
metadata riêng. Renderer không tự regex lại toàn bộ văn bản ở mỗi lần render.

#### Source indicator

- Các dòng kiểu `PL1 - Mau so 1: ...`, `PL2 - Mau so ...`, tên file, nhãn
  import/scrape hoặc descriptor
  kỹ thuật phải được đánh dấu `role=source-indicator`, `uiHidden=true`.
- Không nhầm với dòng pháp lý `Mẫu số 1`, `Mẫu số 72`… Dòng form-number hợp lệ vẫn
  hiển thị và phải giữ đúng căn lề từ mẫu nguồn.
- Không xóa marker khỏi source hoặc generated data một cách im lặng. Giữ evidence
  và detector report để audit; UI có thể ẩn theo role.
- DOCX output phải có test riêng xác nhận marker có/không thuộc mẫu pháp lý trước
  khi quyết định loại khỏi bản xuất.

#### Quốc hiệu, tiêu ngữ và tiêu đề

- Bảo toàn hard line break trong run/paragraph. `\n` trong text phải render thành
  line break an toàn, không bị browser collapse thành space.
- Không dùng `white-space: pre` toàn trang gây tràn ngang. Có thể chuyển newline
  đã escape thành `<br>` hoặc dùng `pre-line` tại đúng run/block contract.
- Quốc hiệu, tiêu ngữ, đường kẻ và tiêu đề nhiều dòng phải giữ từng dòng riêng,
  căn giữa/căn phải theo source, không nối chữ.
- Dòng `Mẫu số ...`, ngày tháng, `Kính gửi`, chữ ký và tiêu đề có style/spacing
  riêng, không áp một margin chung cho mọi `.bp`.

#### Footnote và chuỗi `Tôi là1`

- Không dùng regex xóa mọi chữ số đứng sau chữ; có thể phá số điều, mã mẫu, ngày
  và dữ liệu hợp pháp.
- Converter phải nhận biết run superscript, `w:vertAlign`, footnote reference hoặc
  cấu trúc OOXML tương đương.
- UI mặc định hiển thị `Tôi là¹` bằng `<sup>` có tooltip/link tới chú thích nếu
  footnote tồn tại. Nếu product owner chọn nhãn nhập sạch, UI có thể ẩn marker
  nhưng phần help/footnote vẫn phải truy cập được.
- DOCX output giữ footnote đúng source pháp lý. Không xóa footnote khỏi template
  chỉ để ảnh UI đẹp hơn.
- Acceptance detector: không còn chuỗi baseline `Tôi là1`, `Tôi là2`... trong DOM;
  chữ số phải là run footnote semantic hoặc không hiển thị theo policy đã chốt.

### Mở rộng block schema tối thiểu

Không bắt buộc mọi thuộc tính đều có trên mọi block; chỉ emit khi source có giá trị
khác mặc định. Contract dự kiến:

```json
{
  "t": "p",
  "role": "national-header",
  "align": "center",
  "format": {
    "leftIndentPt": 0,
    "rightIndentPt": 0,
    "firstLineIndentPt": 0,
    "spaceBeforePt": 0,
    "spaceAfterPt": 0,
    "lineSpacing": 1.15,
    "keepWithNext": true
  },
  "runs": [
    {"text": "...", "b": true},
    {"text": "1", "vertAlign": "superscript", "role": "footnote-ref"}
  ]
}
```

Nếu dùng đơn vị khác phải thống nhất và ghi trong contract. Không đưa raw OOXML
hoặc style object không ổn định thẳng vào UI schema.

Các tab stop không thể biểu diễn ổn định trong responsive HTML phải được chuyển
thành layout semantic phù hợp, ví dụ `date-line` dùng inline layout/flex/grid có
wrap an toàn. Không chèn hàng loạt `&nbsp;` để giả tab.

### Wave L0 — census hình thức 87 mẫu (read-only, song song)

Chia ba agent theo form range như census bảng:

- L0-A: `PLI_M01–PLI_M12`.
- L0-B: `PLI_M13–PLI_M80`.
- L0-C: `PLII_M01–PLII_M28`.

Mỗi agent ghi fragment riêng, không sửa production. Với mỗi mẫu kiểm tra:

- Source indicator/filename marker ở mọi nguồn có thể hiển thị: paragraph block,
  document wrapper/title, tab caption và metadata do app ghép thêm.
- Form number và vị trí/căn lề.
- Quốc hiệu, tiêu ngữ, separator.
- Hard line break bị collapse.
- Tiêu đề chính/phụ và `Kính gửi`.
- Date line, tab/indent, signature.
- Footnote/superscript/subscript và chuỗi digit dính chữ.
- Paragraph có indent/spacing đặc biệt.
- UI screenshot trang đầu ở viewport chuẩn.
- DOCX source/tagged/output có khác nhau về layout hay không.

Lead merge thành `app/data/layout_specs/manifest.json` hoặc artifact tương đương,
đủ 87/87. Mọi issue có `form_id`, block index/source paragraph, category, evidence,
expected role/style và status.

### Wave L1 — extractor/schema contract

Một agent sở hữu duy nhất `tools/docx_to_blocks.py` và test extractor:

1. Trích xuất newline/hard break đúng nghĩa.
2. Trích xuất superscript/subscript/footnote reference.
3. Trích xuất paragraph indents/spacing/line spacing/keep-with-next cần thiết.
4. Gán semantic role qua rule/module tách biệt và override manifest.
5. Phân biệt `source-indicator` với `form-number` hợp lệ.
6. Backward compatible với block cũ thiếu `role/format/vertAlign`.
7. Generator idempotent; chạy hai lần cho semantic-equivalent output.

Không regenerate 87 mẫu trong worktree subagent. Lead tích hợp extractor/contract
trước, sau đó regenerate tập trung và review allowlist.

### Wave L2 — renderer/CSS

Một agent khác chỉ bắt đầu sửa renderer sau khi L1 contract được khóa, sở hữu:

- `app_web/ui/render.js`.
- `app_web/ui/style.css`.
- DOM/layout tests liên quan.

Yêu cầu:

- Escape text trước rồi mới chuyển hard break hợp lệ thành `<br>`.
- Render `superscript/subscript` bằng semantic HTML.
- Ẩn `source-indicator` theo role, không theo substring ngẫu nhiên.
- Áp paragraph format qua class/CSS custom property có allowlist; không đưa chuỗi
  style tùy ý từ JSON vào HTML.
- Có style riêng cho form-number, national header/motto/separator, date line,
  title, salutation, note, footnote và signature.
- Giữ responsive behavior; ở 1280×800 không tràn ngang ngoài bảng được phép scroll.
- 100%, 125%, 150% và 200% zoom vẫn đọc được, input không đè chữ.
- Không làm thay đổi canonical keys, store, validation hoặc export payload.

### Wave L3 — rollout và visual QA

Lead regenerate theo batch, không một lần mù 87 mẫu:

1. Pilot: `PLI_M01`, `PLI_M02`, `PLII_M01`, `PLI_M72`.
2. Formation: `PLI_M01–M11`.
3. Change: `PLI_M12–M26`.
4. Các mẫu PLI còn lại.
5. Household: `PLII_M01–M28`.

Mỗi batch phải có:

- Generated diff allowlist.
- Detector technical marker/footnote/newline.
- DOM snapshot/contract tests.
- Screenshot trang đầu của mọi mẫu trong batch tại viewport chuẩn.
- Screenshot các trang/section đặc biệt đối với mẫu dài.
- So sánh side-by-side source DOCX, UI và output DOCX/PDF cho mẫu đại diện.
- Báo rõ PASS/FAIL/NOT RUN; không dùng cảm nhận “trông ổn”.

### Test bắt buộc

1. Cả 87/87 biểu mẫu không render marker kỹ thuật `PL1/PL2 - Mau so ...`, tên file
   hoặc descriptor import ở bên trong tờ khai UI; `PLI_M01` là regression sample,
   không phải toàn bộ scope.
2. Các dòng `Mẫu số ...` hợp lệ vẫn còn và có alignment theo source/approved override.
3. Quốc hiệu, tiêu ngữ và separator là ba visual line riêng.
4. Tiêu đề hai dòng không bị nối thành một dòng.
5. `Tôi là1` không xuất hiện dưới dạng baseline text; footnote là `<sup>` hoặc được
   ẩn theo policy kèm help có thể truy cập.
6. Detector chạy đủ 87 block files và không còn marker chưa classify.
7. Không xóa nhầm số điều, số mẫu, mã ngành, ngày tháng hoặc số định danh.
8. Input canonical và checkbox vẫn render/focus/validate như trước.
9. Grid/table tests, draft và export regression vẫn PASS.
10. DOCX output không mất footnote, placeholder, table tag hoặc paragraph pháp lý.
11. Visual QA có evidence; `NOT RUN` không tính PASS.

### Acceptance Gate P1-LAYOUT

Chỉ báo `LAYOUT_DONE` khi:

1. Layout manifest đủ 87/87.
2. 87/87 mẫu không còn source indicator chưa classify hoặc còn hiển thị trong vùng
   tờ khai UI; detector phải kiểm cả blocks và wrapper/title do app sinh.
3. Hard breaks và semantic footnotes render đúng.
4. Các header/title/date/salutation/signature giữ alignment/spacing đã duyệt.
5. Không còn known defect dạng `Tôi là1` baseline.
6. Pilot và mọi batch rollout đều có screenshot evidence.
7. Structural table, domain, draft, export và DOCX tests không hồi quy.
8. Independent visual auditor không tham gia implementation xác nhận PASS.

## Prompt implement Wave P1-LAYOUT cho agent có context mới

```text
Bạn là Lead/Integrator Agent tiếp quản repo:
C:\Users\Tuyen PC\orca\dangky_kinhdoanh

MỤC TIÊU
Thực hiện Wave P1-LAYOUT trong PLAN.md: sửa tận gốc độ trung thành hình thức của
87 biểu mẫu trên UI và bảo toàn DOCX. Owner xác nhận marker kỹ thuật đầu mẫu là
lỗi trên toàn bộ biểu mẫu, không chỉ PLI_M01. Các lỗi đã thấy còn gồm
quốc hiệu/tiêu ngữ bị dồn dòng, alignment/indent/spacing sai và footnote bị dính
vào nhãn như “Tôi là1”. Không hard-code riêng PLI_M01 và không xóa chữ số bằng
regex mù.

TRƯỚC KHI SỬA
1. Đọc toàn bộ PLAN.md, ưu tiên “Wave P1-LAYOUT — chuẩn hóa hình thức và độ trung
   thành biểu mẫu”, cùng Acceptance Gates hiện hành.
2. Đọc PLAN_excel.md nhưng KHÔNG triển khai Excel; EXCEL_START_GATE vẫn NOT_READY.
3. Chạy git status/log/worktree/diff. Bảo toàn mọi file modified/untracked của
   owner. Đặc biệt không đụng profile draft và không xóa PLAN_excel.md.
4. Xác minh HEAD thực tế; baseline từng được xác nhận là 6eaf4ee nhưng có thể đã
   thay đổi. Không reset/revert và không pull origin mù.
5. Chạy baseline Node/Python/audit tests và ghi PASS/FAIL/NOT RUN.

ROOT CAUSE ĐÃ BIẾT
- Nhiều block có paragraph đầu dạng “PL1/PL2 - Mau so ...”; owner xác nhận toàn bộ
  UI biểu mẫu đều bị marker kỹ thuật. Phải audit cả 87 blocks và document
  wrapper/title do app sinh, không coi số grep tĩnh là tổng scope.
- Quốc hiệu/tiêu ngữ/separator nằm trong một run có newline; renderRuns hiện không
  bảo toàn hard break nên browser collapse thành space.
- PLI_M01/M02/M03/M04/M32/M33 có text dạng “Tôi là1”; phải đọc OOXML/source để
  xác định footnote reference, không tự xóa số.
- Block schema hiện chủ yếu có align, thiếu paragraph format và run vertAlign.

ĐIỀU PHỐI WORKTREE
Không cho hai agent sửa cùng file. Dùng tối đa 3 subagent song song ở L0:
- L0-A census PLI_M01–M12;
- L0-B census PLI_M13–M80;
- L0-C census PLII_M01–M28.
Mỗi agent chỉ ghi layout manifest fragment/evidence riêng, không sửa production.

Lead merge census đủ 87/87 và khóa layout contract. Sau đó chạy tuần tự:
- L1 extractor/schema agent sở hữu tools/docx_to_blocks.py + extractor tests;
- tích hợp L1;
- L2 renderer agent sở hữu render.js/style.css + DOM/layout tests;
- tích hợp L2;
- L3 Lead regenerate theo batch và visual QA.

Không chạy L1 và L2 song song trước khi contract role/format/vertAlign được khóa.
Lead là người duy nhất regenerate blocks/templates/form_maps toàn cục.

CONTRACT BẮT BUỘC
- Semantic paragraph roles: source-indicator, form-number, national-header,
  national-motto, national-separator, date-line, form-title, form-subtitle,
  salutation, body, section-heading, note, footnote, signature.
- Paragraph format cần thiết: indent, spacing, line spacing, keep-with-next.
- Run metadata: superscript/subscript/footnote-ref và hard break.
- Backward compatible khi block cũ không có metadata mới.
- UI ẩn source-indicator theo role nhưng vẫn giữ evidence; không ẩn “Mẫu số ...”.
- Text phải escape an toàn trước khi chuyển newline thành <br>.
- Không dùng &nbsp; hàng loạt hoặc inline style tùy ý từ JSON.

PILOT BẮT BUỘC
PLI_M01, PLI_M02, PLII_M01, PLI_M72.

ACCEPTANCE BẮT BUỘC
Pilot chứng minh cơ chế trên bốn mẫu, nhưng detector marker phải chạy toàn bộ 87
mẫu ngay trong wave này; không được chờ rollout mới phát hiện marker còn sót.

1. Cả 87/87 mẫu không còn dòng kỹ thuật “PL1/PL2 - Mau so ...”, filename hoặc
   descriptor import trong vùng tờ khai UI; detector có danh sách form-level.
2. Các dòng “Mẫu số ...” hợp lệ vẫn còn và đúng vị trí.
3. Quốc hiệu, tiêu ngữ, separator là ba dòng riêng.
4. Tiêu đề nhiều dòng giữ line break.
5. Không còn baseline “Tôi là1”; số 1 là footnote semantic/superscript hoặc ẩn
   theo policy có help, trong khi DOCX vẫn giữ footnote pháp lý.
6. Input, checkbox, GRID_META, draft và export không hồi quy.
7. Screenshot 1280x800 ở 100% và 200% zoom có evidence.

ROLLOUT
Sau pilot PASS, regenerate/integrate theo batch formation, change, PLI còn lại,
household. Mỗi batch có detector, allowlist, test và screenshot trang đầu mọi mẫu.
Không báo LAYOUT_DONE nếu chỉ sửa bốn mẫu pilot.

INDEPENDENT AUDIT
Sau rollout, tạo auditor agent hoàn toàn mới, không dùng agent vừa code. Auditor
bắt đầu read-only, tự chạy detector/test, so source/UI/output, kiểm screenshot và
không sửa production. Nếu FAIL, trả reproduction cho coding agent sửa rồi audit
lại. NOT RUN không tính PASS.

BÁO CÁO
- Agent/worktree/branch/commit/ownership.
- Layout manifest coverage 87/87.
- Marker/newline/footnote/format findings trước và sau.
- Generated diff trong/ngoài allowlist.
- Test command PASS/FAIL/NOT RUN.
- Screenshot/visual evidence.
- Independent audit verdict.

Chỉ báo LAYOUT_DONE khi đủ 8 Acceptance Gates P1-LAYOUT trong PLAN.md. Không triển
khai PLAN_excel.md và không gọi toàn dự án TABLES DONE ở wave này.
```
