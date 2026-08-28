# MASTER PLAN — hoàn thiện `dangky_kinhdoanh` (v3)

> **Checkpoint:** 2026-08-28, `main@f3d614c` — đã push `origin/main`
> (github.com/Zedlchoke/dangky_kinhdoanh, 29 heads, 2 tag baseline).
> Release runner hiện hành: **38 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS**.
>
> Đây là kế hoạch duy nhất có hiệu lực. Các phase **P0 (Recovery), P1
> (Layout), P2 (Domain rollout)** đã ĐÓNG — chi tiết trong
> `docs/execution_ledger.md`, không làm lại nếu không có regression thật.
> **Quy tắc đứng đầu (lệnh owner 2026-08-28):** mỗi phase dưới đây CHỈ mở khi
> owner ra lệnh rõ ràng;lane P3 (`agent/p3-e2e`) đã chạy xong nhưng CHƯA merge —
> merge cũng phải có lệnh.

## 1. Đích sản phẩm

Ứng dụng desktop cho phép chọn thủ tục đăng ký kinh doanh, nhập dữ liệu trực
tiếp trên biểu mẫu, dùng chung dữ liệu giữa các mẫu, khai các loại bảng, kiểm
tra lỗi, lưu/nhập draft và xuất DOCX/ZIP đúng cấu trúc pháp lý.

### `CORE_APP_DONE` — chỉ công bố khi TOÀN BỘ:

1. Mọi section trong 87 biểu mẫu có implementation hoặc blocker pháp lý do
 owner xác nhận (không tự đoán để xóa blocker).
2. Bốn loại bảng `editable-grid`, `fixed-matrix`, `nested-grid`,
 `output-table` hoạt động xuyên UI, draft, validation và DOCX.
3. Generator source/spec → template → `form_maps` → blocks chạy hai lần không
 tạo diff, không mất marker/format/rowspan/colspan/totals.
4. Mọi use case công bố qua E2E: chọn form, nhập, chuyển tab, lưu/mở/import,
 validation, DOCX/ZIP export, lỗi điều hướng đúng.
5. Layout 87/87 qua detector + screenshot + auditor độc lập (đã đạt P1 — duy
 trì qua mọi regen).
6. Keyboard-only, accessibility, viewport, resilience, security đạt gate.
7. Windows `.exe` build tái lập + smoke trên máy sạch không Python.
8. Release runner không còn FAIL/critical NOT RUN; repo sạch; final auditor
 read-only PASS.

### `FULL_PRODUCT_DONE` = `CORE_APP_DONE` + luồng Excel (phần 4 của PLAN này)

đã implement và audit. Excel KHÔNG chặn `CORE_APP_DONE`.

## 2. Nguồn sự thật (đọc theo thứ tự)

1. `PLAN.md` này → 2. `docs/execution_ledger.md` → 3.
`docs/decision_registry.md` (D1–D7 + các gap còn mở) → 4.
`docs/product_scope_registry.md` → 5. `docs/p2_component_contracts.md`,
`docs/p2_dependency_graph.md`, `docs/p2_fixture_candidates.md` → 6. Source,
tests, manifests tại HEAD (trọng tài cuối nếu docs stale).

## 3. Hiện trạng kỹ thuật tại checkpoint (cần biết khi làm)

- **Đã DECIDED + implement:** 3 nested-grid N1/N6/N7 (PLI_M02/M12/M15); 6
lưới người (PLII_M07, PLI_M06/M07/M08/M10/M13); 3 fixed-matrix capital
(M01 tài sản ĐT, M02 nguồn vốn + tài sản VĐL); D7.3 (M72 required/minRows 1);
census 18 lead_status_override — GATE PASS 87/87.
- **Đang đậu trên branch:** `agent/p3-e2e` @ `b61def0` — 4 suite mới
(`test_p3_e2e/draft/security/a11y.js`, 2.360 dòng, 220 PASS) + **9 finding**
production có bằng chứng (chưa sửa).
- **Blocker pháp lý chờ owner** (giữ đúng trạng thái blocked, không tự mở):
M09 (packet D3) · PLII_M02 2 lưới thành viên (ghim occurrence_id) · M72
N2–N5 · D5.2 (canonical thuế PLII_M02) · 2 nhóm cột cuối N1/N6/N7 ·
D6.1 (evidence per-form, M56 chưa đọc) · D6.3 min/max · D6.4 max/placeholder ·
M03/M04/M05 cần bản gốc.
- **Nợ kỹ thuật đã ghi:** docx zip-mtime làm byte-idempotency tuyệt đối bất
khả thi (generator hygiene) · slot `cross_field_rules` chưa có trong
generator contract v1 (chỉ runtime) · thiếu chế độ đăng ký section
"already-mapped" · validator chưa có type `chkExclusiveConditional` · M01
header bảng là `td` trong `tbody` (cosmetic, P5).
- **Worktrees:** 15 lane cũ ĐÃ merge (có thể dọn sau khi owner duyệt — P3.0);
`p3-e2e` giữ nguyên tới khi merge.

## 4. LUỒNG EXCEL — tích hợp từ `PLAN_excel.md` (nguyên văn đã hợp nhất)

> Trạng thái: **THIẾT KẾ CHI TIẾT ĐÃ DUYỆT đưa vào PLAN**; implement CHỈ khi
> owner ra lệnh "Bắt đầu Excel" sau Review Gate (mục 5.4). `PLAN_excel.md`
> giữ nguyên như bản lưu; phần này là bản hợp nhất có hiệu lực.

### 4.1 Quy trình đích (owner chốt 2026-08-27 — BẮT BUỘC đúng thứ tự)

```
(1) Owner xác định khách muốn làm dịch vụ nào
(2) Owner CHỌN thủ tục trong app
(3) App XUẤT file Excel riêng cho thủ tục đó — đẹp, dễ dùng, câu hỏi đời thường(nhưng vẫn giữ tính chuyên nghiệp)
(4) Khách nhận file, tự điền (app không cần chạy)
(5) Owner nạp file Excel vào app
(6) App tự điền toàn bộ thông tin vào biểu mẫu + liệt kê ô CÒN THIẾU
(7) Owner rà, bổ sung, xuất DOCX như quy trình hiện tại
```

Excel = **phiếu thu thập thông tin đối mặt khách**, KHÔNG phải bản sao biểu
mẫu pháp lý. Sau bước (6) Excel hết vai trò; draft trong app là nguồn chân lý
duy nhất.

### 4.2 Nguyên tắc "câu hỏi dễ hiểu" (yêu cầu cứng)

- Không dùng nhãn biểu mẫu khô cứng. Mapping ngầm `question_id → data-key`,
ví dụ: "Bạn muốn đặt tên công ty là gì? (tiếng Việt)" → `dn.ten_tieng_viet`;
"Công ty do ai đứng tên chịu trách nhiệm?" → `ndd.ho_ten`; "Vốn bạn đăng ký
góp là bao nhiêu (VNĐ)?" → `von_dieu_le`; "Công ty hoạt động trong lĩnh vực
nào? Ghi tên ngành" → `ds_nganh.ten_nganh` (app tra VSIC giúp).
- Một câu hỏi một ý; có ví dụ điền mẫu (chữ mờ) ngay dưới ô.
- Tùy chọn chọn-là-dropdown (loại hình DN, phương án thuế…), khách không gõ.
- Gom theo nhóm đời thường ("Về người đại diện", "Về vốn", "Về ngành nghề"),
KHÔNG theo mục 1/2/3 biểu mẫu.
- Cái app tự sinh được thì KHÔNG hỏi khách (tổng vốn, số thành viên suy từ
danh sách, ngày nộp hồ sơ…).

### 4.3 Hình thức file (yêu cầu cứng "đẹp, dễ dùng")

Sheet mở đầu: tiêu đề dịch vụ + hướng dẫn 5 dòng + quy ước màu (ô vàng = điền,
ô xám = app tự làm). **Khóa bảo vệ** mọi ô ngoài vùng điền (Excel protection).
Màu nhóm phần, viền rõ, cột rộng vừa, không cuộn ngang màn hình thường. Cuối
file: bảng "Giấy tờ bạn cần chuẩn bị" từ `ho_so_bao_gom` (khi DECIDED).

### 4.4 Kiến trúc + các wave triển khai (khi được mở)


| Wave                     | Nội dung                                                                                                                                                                                                                                       | File/ownership                                                              | Gate                                                                                  |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| X1 Lớp questionnaire     | Schema `{question_id, data_key, type, example, options[], group, version}`; KHUNG sinh tự động từ `form_maps`/registry; **nội dung câu hỏi là sản phẩm** — Lead soạn, owner duyệt từng cụm; tách biệt hoàn toàn, KHÔNG sửa form_maps/templates | `tools/questionnaire/` (schema + builder) + `app/data/questionnaire/*.json` | khung khớp 100% data-key có trong registry; question chưa có data-key = fail build    |
| X2 Xuất .xlsx            | openpyxl **pin version** trong `requirements-dev.txt`; đọc use case đang chọn → subset questionnaire → viết file: protection, styling, data validation dropdown, bảng giấy tờ kèm theo                                                         | `tools/excel_export.py` (mới)                                               | mở được Excel/LibreOffice/Google Sheets; protection bật; 0 ô data ngoài locked-region |
| X3 Nạp .xlsx             | Kiểm cấu trúc fail-loud (mã lỗi riêng: sai khung/sai version/ô lạ) → dịch question_id→data_key vào draft → validator chuẩn hiện có → panel lỗi = "danh sách còn thiếu"                                                                         | `tools/excel_import.py` (mới)                                               | file khách sửa khung → lỗi rõ; không bao giờ ghi đè draft khi fail                    |
| X4 Round-trip + negative | draft→xlsx→draft giữ 100% giá trị; file rỗng trường bắt buộc; bảng lặp nhiều dòng; dropdown gõ tự do; protection phá khung                                                                                                                     | `tools/test_excel_roundtrip.py`, `tools/test_excel_negative.py`             | 2 suite xanh + đăng ký release_runner                                                 |
| X5 UI                    | Nút "Xuất phiếu Excel cho khách" (màn hồ sơ) + "Nạp phiếu Excel" (cạnh "Mở hồ sơ .json")                                                                                                                                                       | `app_web/ui/app.js`, `index.html`, `main.py` bridge                         | E2E: chọn thủ tục → xuất → nạp → draft đúng                                           |
| X6 Visual + packaging    | Screenshot phiếu Excel; kiểm openpyxl trên máy sạch (R6)                                                                                                                                                                                       | evidence `generated_ho_so/_visual_layout/excel/`                            | owner duyệt hình ảnh file                                                             |


### 4.5 Rủi ro &amp; chặn (nguyên bảng PLAN_excel)


| Rủi ro                                | Chặn bằng                                                                       |
| ------------------------------------- | ------------------------------------------------------------------------------- |
| Khách phá khung/sheet                 | Protection + kiểm cấu trúc lúc nạp, fail-loud                                   |
| Khách gõ tự do ô dropdown             | Data Validation + validator blocking                                            |
| Câu hỏi thân thiện lệch nghĩa pháp lý | Owner duyệt từng cụm; câu hỏi gắn version                                       |
| Mẫu giấy đổi → câu hỏi sai            | Regen questionnaire cùng đợt regen template; diff review như generated artifact |
| Máy khách không có Excel              | .xlsx mở đa ứng dụng; app nạp bằng openpyxl, không cần Excel                    |
| Phá Windows packaging                 | openpyxl thuần Python, pin version, test máy sạch (P6)                          |


### 4.6 Câu hỏi owner trả khi MỞ (chưa trả)

- **E1** Xuất theo một thủ tục đã chọn — có cần kèm biến thể gì không?
- **E2** Chuẩn hóa dữ liệu khách: hoa/thường, ngày `01/02/2026`, số tiền có
dấu chấm nghìn — xử lý thế nào?
- **E3** Ngành nghề: khách ghi tên tự do → app tra VSIC đề xuất → owner chọn?
- **E4** Danh sách "còn thiếu": dùng panel lỗi hiện có hay thêm "checklist bổ
sung" theo nhóm câu?
- **E5** Có cần xuất ngược hồ sơ đã điền ra Excel để khách xác nhận không?
- **E6** Bộ câu hỏi cụm đầu: owner tự soạn hay Lead soạn nháp owner sửa?
(Khuyến nghị cụm đầu: **"Thành lập doanh nghiệp"**.)

## 5. Các phase còn lại — chi tiết thực thi

### P3 — E2E / A11y / Security / Resilience (SẴN SÀNG, chờ lệnh)

- **P3.0** (tùy chọn, cần owner duyệt) dọn 15 worktree lane đã merge.
- **P3.1** Merge `agent/p3-e2e` → main; đăng ký 4 suite vào
`tools/release_runner.py` + `tools/audit_expected_diff_files.txt`; runner
vẫn 0 FAIL.
- **P3.2** Sửa 9 finding theo cụm (mỗi cụm 1 commit + test phủ):
  - **Cụm draft-crash**: `Array.isArray` guard ở `normalizeStoreLoops`
  (form-domain.js:754) và `GridCtl.ensureIds/rows` (app.js:97) — draft hỏng
  bị bỏ qua an toàn thay vì crash; negative test trong `test_p3_draft.js`.
  - **Cụm export-path**: `Bridge.export` sanitize `case_id` (cấm `..`, NUL,
  ký tự điều khiển, &gt;255 byte) + `try/except` quanh `mkdir` trả mã lỗi;
  test bằng `case_id` hostile qua stub webview.
  - **Cụm DOCX-NUL**: `docx_render.safe_escape` loại ký tự điều khiển bất hợp
  pháp XML (giữ `\t\n\r`) + test ParseError biến mất.
  - **Cụm a11y**: bỏ `.fld:focus{outline:none}` (giữ `:focus-visible`);
  `aria-colcount`/`aria-rowcount` cho `renderLoop` + nested + đồng bộ
  `enhanceEditableGrids`; `aria-label` cho 6 nút row-op và `.chk-box`;
  log info truncate giá trị nhạy cảm. Mục tiêu: `test_p3_a11y` 8 FAIL → 0.
  Mỗi cụm: targeted suite trong lúc sửa; không đụng generated artifacts.
- **P3.3** Đo a11y trên **app shell thật** (app.js tablist) — mở rộng
`test_p3_a11y.js` hoặc ghi manual evidence; hiện finding a11y dựa trên
renderer + đối chiếu tĩnh app.js.
- **P3.4** Platform thật: pywebview/WebView2 smoke + dialog tkinter — CHỈ chạy
được khi owner cung cấp máy Windows; không có → giữ NOT RUN kèm hướng dẫn
chưa từng chạy.
- **Gate P3**: runner (giờ ~42 suite) 0 FAIL; 4 suite P3 xanh; 9 finding đóng
hoặc owner chấp nhận chờ; blocking error chặn export đã có test; evidence
platform đầy đủ hoặc NOT RUN có lý do.

### P4 — Review Gate Excel (sau P3; KHÔNG implement trước lệnh)

1. Lead đối chiếu questionnaire mapping với canonical keys/form_maps — báo
 danh sách data-key ổn định vs đang trôi.
2. Liệt kê thủ tục ưu tiên + các câu hỏi đời thường cần owner duyệt (đề xuất
 cụm "Thành lập doanh nghiệp").
3. Kiểm dependency: openpyxl pin, protection/dropdown/round-trip khả thi trên
 pywebview (file dialog).
4. Báo effort/risk và hỏi owner trả **E1–E6** (mục 4.6) + lệnh rõ:
 `Bắt đầu Excel` hoặc `Để sau`. Nếu `Để sau` → Excel không chặn
 CORE_APP_DONE; nếu `Bắt đầu` → chạy X1→X6 (mục 4.4) theo đúng wave, mỗi
 wave kết thúc commit sạch.

### P5 — Visual QA toàn diện

- UI screenshot matrix cho representative flows + MỌI layout/table class
(editable/fixed/nested/output + M72 conditional) — tái sử dụng ảnh P1/P2
chỉ khi hash input + renderer không đổi.
- DOCX → PDF/PNG bằng **Microsoft Word** (đã có trên máy) hoặc renderer owner
chấp thuận; so typography, spacing, page breaks, table geometry,
superscript/footnote, presence/absence, marker leak.
- 87/87 hoặc sample policy do owner duyệt; xử lý ghi chú còn mở (M01 header
`td` trong `tbody` — quyết định nâng `thead` hay chấp nhận).
- Auditor độc lập read-only chấm từng gate.

### P5R — Rà soát toàn diện app (Whole-App Detail Review) — NGAY TRƯỚC ĐÓNG GÓI

> **Bản vận hành chi tiết: `docs/plan_wave_D2_P5R.md`** — trình tự phase
> D2-A (gỡ pin đỏ) → D2-B (worker điều tra 87 mẫu, read-only) → D2-C (3 lane
> worker sửa: fix-industry / fix-render-docx / fix-extractor) → D2-D (Lead
> merge + regen 8 bước) → **D2-E worker AUDIT chuyên trách** (người mới, không
> trùng người sửa — chấm 3 tầng: lỗi đã sửa chưa / quy trình chuẩn không /
> công cụ độc lập) → D2-F chạy P5R 10 gate + ma trận hồi quy 9 Class lỗi.
> Danh mục lỗi còn lại: `docs/defect_registry.md` (Class 1–9 + câu hỏi chờ
> owner ở mục 9 của plan).

> Mở theo lệnh owner 2026-08-28: "rà lại toàn bộ app, sử dụng toàn bộ, xem
> xét toàn bộ biểu mẫu, attention to detail — xem lại toàn bộ rồi rút ra gate
> chỉ tiêu riêng biệt chi tiết, chỉn chu, tỉ mỉ nhất", đặt **ngay trước P6**.
> Đây là cổng chất lượng cuối: KHÔNG cho phép đóng gói khi còn một gate đỏ.

**Phạm vi rà (toàn bộ, không sampling):** 87/87 biểu mẫu · mọi use case
(use_cases.json) · mọi loại trường (input, ngày, checkbox, dropdown, 4 kind
bảng + nested + selector M72) · mọi luồng (chọn thủ tục → nhập → draft →
validate → Excel xuất/nạp → DOCX/ZIP) · mọi trạng thái (rỗng, đầy đủ, lỗi,
draft cũ/migration) · nội dung đối chiếu **nguồn pháp lý HIỆN HÀNH**
(TT 68/2025 như được sửa bởi TT 121/2026 — 9 mẫu PL I 1/2/3/4/5/10/12/27/30
đã thay, Mẫu 11 đã bãi bỏ; PL II nguyên bản TT 68).

**Gate chỉ tiêu riêng biệt (mỗi gate đo được, có evidence riêng):**


| #   | Gate                     | Chỉ tiêu PASS                                                                                                                                                                                                     |
| --- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | Nội dung ↔ nguồn pháp lý | 87/87 khớp bản biểu mẫu hiệu lực (TT 121 amends TT 68); 0 lệch chữ/cột/mục; mọi spec có `source_evidence` số hiệu văn bản + mẫu + dòng                                                                            |
| G2  | Đánh số mục              | `tools/census/numbering_audit --gate` xanh: 0 JUMP, chuỗi companion liên tục, EXCEPTIONS RỖNG                                                                                                                     |
| G3  | Checkbox                 | 0 glyph □/☐ dẹt trong blocks; 100% checkbox tick được, giá trị vào draft + DOCX                                                                                                                                   |
| G4  | Sạch marker/ghép chữ     | 0 marker `{..}` sót trong UI lẫn DOCX xuất; 0 GLUE chữ số chú thích dính chữ (census GLUE = 0)                                                                                                                    |
| G5  | Header band              | 22 mẫu TÊN DN/HKD: tên TRÁI + quốc hiệu PHẢI cùng band, "Số:" trái + ngày phải — đúng cả UI lẫn DOCX in qua Word                                                                                                  |
| G6  | Bảng 4 kind              | nhập/xóa/tổng/cross-field đúng từng section; draft round-trip giữ 100% giá trị; conflict-guard không lặng lẽ nuốt dữ liệu, kiểm tra các bảng nếu chỉ nhập 1 dòng thì có xuất ra 1 dòng không hay mặc định 4 dòng. |
| G7  | Export DOCX/ZIP          | 87/87 mở được bằng Microsoft Word, đúng 1 biến thể M72, không trang trắng/cookies; lỗi điều hướng export đúng mã                                                                                                  |
| G8  | Luồng Excel              | xuất phiếu → điền mẫu → nạp → danh sách "còn thiếu" đúng, file khách phá khung bị chặn fail-loud                                                                                                                  |
| G9  | A11y/keyboard/viewport   | không hồi quy so với P3 (tab/roving/aria/focus-visible; 3 viewport)                                                                                                                                               |
| G10 | Sạch máy dựng            | runner toàn XANH 0 NOT RUN critical; census manifest GATE 87/87; allowlist exact-set cân; `git status` sạch                                                                                                       |


**Cách làm:** Lead chạy census/probe tự động (số liệu G2–G4, G10) → auditor
độc lập read-only MỚI chấm G1/G5–G9 theo checklist từng mẫu (attention to
detail: kể cả dấu chấm lửng, dòng kẻ, chính tả nguồn) → mọi gate đỏ quay lại
phase sở hữu sửa → chỉ khi 10/10 XANH mới mở P6. Bất kỳ gate nào không đo được
bằng máy phải có evidence thủ tục + người chấm ghi rõ tên.

### P6 — Windows build + clean-machine smoke

1. Khóa dependency (requirements pin + openpyxl nếu Excel đã mở), WebView2
 policy, icon/version, build command tái lập được.
2. Build `.exe`/installer trên Windows (máy owner).
3. Máy sạch KHÔNG Python: mở app, chọn hồ sơ, nhập từng kind, save/reload/
 import, validate, export DOCX/ZIP, chạy offline.
4. Ghi exact artifact path, hash, size, OS + WebView2 version, verdict từng
 bước. macOS/Linux/compileall KHÔNG được tính là Windows smoke.

### P7 — Final audit + bàn giao

- Auditor read-only MỚI (không dùng agent đã implement): đối chiếu định nghĩa
`CORE_APP_DONE` (mục 1) với manifests, decisions, release report, visual
evidence, package hash, docs, repo cleanliness. FAIL → quay lại phase sở hữu.
- PASS → ghi `CORE_APP_DONE`. Nếu Excel đã được mở + hoàn thành → audit thêm
luồng Excel → `FULL_PRODUCT_DONE`.

## 6. SOP vận hành worktree &amp; sub-agent (bắt buộc)

### 6.1 Worktree lane (coding)

```bash
# Tạo (chạy từ ROOT repo, KHÔNG bao giờ code trực tiếp trong worktree của lane khác):
git worktree add ../dangky_kinhdoanh-worktrees/<lane> -b agent/<lane> <BASE_COMMIT>
cd ../dangky_kinhdoanh-worktrees/<lane>
```

- Đặt tên: `<lane>` = `p3-fix-draft`, `p3-fix-export`, `p3-fix-a11y`…;
branch `agent/<lane>`.
- Lane commit nhỏ, message rõ, kết thúc bằng `Co-Authored-By: Claude <noreply@anthropic.com>`; KHÔNG push, KHÔNG merge, KHÔNG đụng repo chính
sau khi tạo worktree.
- Mỗi lane nhận brief có đủ 5 mục: BASE commit · **file ownership exact**
(được tạo/sửa) · **forbidden files** · test gate (suite phải xanh, tính cả
baseline suites) · format báo cáo cuối (LANE/BASE/HEAD/DIFF/TESTS/FINDINGS/
NOTES).
- Lane KHÔNG regen global (sandbox temp ĐƯỢC — pattern `bfm.OUT_TPL/OUT_DATA`
như `tools/test_r3b1_people_specs.py`); KHÔNG chạy release_runner.

### 6.2 Sub-agent auditor (read-only)

- Audito KHÔNG sửa code — chỉ được ghi vào `generated_ho_so/_visual_layout/ <thư_mục_evidence>/` (gitignored) + script tạm `/tmp/`.
- Recipe đã kiểm chứng: `python3 -m http.server <port>` từ ROOT +
Playwright/Chromium headless + `app_web/dev/snapshot.html?doc=<FORM_ID> &sel=<dntn|tnhh_1tv|tnhh_2tv|ctcp|dhdn>&values=<json>`; full-page screenshot
  - DOM probe sau render; kill server khi xong.
- Nếu audito phiên trước mất transcript → spawn audito MỚI với brief hẹp
(đọc evidence có sẵn, không chụp lại nếu không cần).

### 6.3 Merge SOP (CHỈ Lead, tuần tự)

```
review diff lane → git merge --no-ff agent/<lane> (message ghi evidence)
→ targeted battery → Lead regen batch nếu lane đổi spec (chạy pipeline đầy đủ
build_form_maps → tag_m72_sections → docx_to_blocks, chạy ×2 zero-diff,
so member-level cho docx) → sửa pin/tripwire test thành trạng thái mới
(không nới) → census manifest nếu counts đổi → allowlist exact-set cân
(= =) → full release runner → ledger + checkpoint report.
```

- Conflict-guard/export/rename: theo tiền lệ đã ghi trong ledger (M06
`ds_thanh_vien_tnhh`, `nganh_sua_doi_chi_tiet`) — cùng loop name khác
contract là FAIL-loud đúng thiết kế, sửa bằng tên loop riêng chứ không nới
guard.

### 6.4 Khi nào được spawn

- KHÔNG spawn khi main bẩn chưa phân loại xong.
- Tối đa 3 lane song song, không chồng file; `form-domain.js` chỉ một lane
sở hữu tại một thời điểm.
- Việc độc lập đọc-đơn (audit visual, đếm evidence) → 1 agent riêng, brief hẹp.
- Lead tự làm: regen, census, allowlist, ledger, merge, mọi thay đổi
`app_web/ui/render.js`/`form-domain.js` khi &gt;1 lane cần.

## 7. Quy tắc điều phối (bất biến)

- Lead giữ main, là người DUY NHẤT regen global artifacts (build_form_maps →
tag_m72_sections → docx_to_blocks → census manifest) và merge lane.
- Targeted tests khi sửa; release runner đầy đủ tại checkpoint; visual pilot
form bị ảnh hưởng trước, batch tại gate. **Visual re-shoot sau mọi regen là
BẮT BUỘC** (bài học P2: bắt 2 regression mà 38 suite xanh không thấy).
- Mọi thay đổi generated phải nằm trong `tools/audit_expected_diff_files.txt`
có chủ đích; exact-set phải cân trước commit.
- Mỗi phase kết thúc commit sạch + cập nhật ledger; **phase mới chỉ mở theo
lệnh owner**. PASS/FAIL/NOT RUN trung thực — chỉ PASS khi chạy thật.

## 8. Evidence contract mỗi checkpoint

HEAD/base + commit list · exact diff allowlist · command/exit code/PASS-FAIL-
NOT RUN · generator lần hai zero diff (ngoại lệ đã classification) · visual
evidence path/tool · blocker/rủi ro/quyết định owner · `git status` cuối.
Bộ gate tối thiểu: release runner, suite lane liên quan, industry/DOCX/audit,
compileall, manifests, generator deep idempotency, M72 conditional export,
`git diff --check`.