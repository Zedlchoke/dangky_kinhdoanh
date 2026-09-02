# Whole-app audit handoff — 2026-08-30

> **Base kiểm tra:** `main@6ae63c2`
>
> **Mục đích:** bàn giao sự thật hiện hành cho agent tiếp theo sửa lỗi. Tài liệu
> này không tuyên bố visual QA hoàn tất. `PLAN.md` vẫn là kế hoạch điều phối có
> hiệu lực; file này là bằng chứng audit tại một checkpoint cụ thể.

## 1. Kết luận ngắn

Chưa thể nói toàn bộ ứng dụng đã hiển thị đúng hoặc mọi bảng đều dùng được.

- Structural census đã đọc đủ **87/87 form** và **111 section**.
- Bộ sinh DOCX tạo được **87/87 file** nhưng chưa render/soi bằng Word hoặc
  LibreOffice ở checkpoint này.
- Release runner hiện **43 PASS / 3 FAIL / 0 NOT RUN — VERDICT FAIL**.
- Layout L1 và numbering gate đều FAIL.
- UI visual audit 87 form × 28 use case × viewport/zoom là **NOT RUN** vì phiên
  audit không có browser backend.
- Word/PDF visual audit 87 form là **NOT RUN** vì không có LibreOffice/Poppler.
- Evidence hình cũ không được dùng để đóng gate vì có merge/generator change sau
  thời điểm chụp.

## 2. Những gì đã quét thật tại HEAD

| Phạm vi | Kết quả | Ý nghĩa đúng |
|---|---:|---|
| `tools.release_runner --verbose` | **43 PASS / 3 FAIL / 0 NOT RUN** | Release chưa xanh |
| `tools.census.build_manifest --deep` | **PASS, 87/87 form, 111 section** | Có đủ entry census; không chứng minh coverage status còn đúng |
| `tools.docx_render --test-all` | **87 PASS / 0 FAIL** | Sinh/mở package DOCX được; không phải visual PASS |
| `tools.census.p1_b_verify_m72` | **9 PASS / 0 FAIL** | M72 có đúng 5 occurrence và marker cấu trúc |
| `tools/test_m72_conditional_export.py` | **6 PASS / 0 FAIL** | M72 chỉ xuất đúng một variant; không chọn thì 0 bảng variant |
| `tools.smoke_web_assets` | **35 PASS / 0 FAIL** | Asset/DOM hook/syntax tồn tại; không chứng minh UI nhìn đúng |
| `tools/census.check_layout_l1` | **FAIL** | Còn lỗi cấu trúc layout |
| `tools.census.numbering_audit --gate` | **FAIL** | Còn footnote glue và chain gap |

## 3. Ba lỗi đang làm release runner đỏ

### AUD-001 — A11y không khởi động được trong môi trường audit

- Suite: `test_p3_a11y`.
- Lỗi: `listen EPERM: operation not permitted 127.0.0.1`.
- Phân loại: **ENVIRONMENT BLOCKED**, không được coi là product PASS hoặc product
  FAIL từ lần chạy này.
- Việc sửa: runner phải preflight quyền bind và báo `NOT RUN` có lý do; release
  chính thức vẫn phải chạy ở môi trường cho phép và đạt 0 FAIL/0 critical NOT RUN.

### AUD-002 — Verifier PLII_M02 nhận sai bảng ngành

- Suite: `p1_c_verify_plii_m02`.
- Template làm việc hiện có header-band, ba bảng ngành Mục A, bảng thuế và bảng
  ngành C.3. Verifier chỉ map được ba occurrence và bỏ `nganh_bo_sung`.
- Phân loại hiện tại: **verifier/region mapping stale**, chưa có bằng chứng cần
  sửa production template.
- Không được chữa bằng đếm gần đúng. Phải nhận diện semantic header/occurrence và
  thêm mutation test khi header-band/bảng thuế chen giữa các bảng ngành.

### AUD-003 — Household industry test dùng cùng mapping stale

- Suite: `test_industry_household` — 12 PASS / 1 FAIL.
- Cùng root cause AUD-002: template table set được map thiếu `nganh_bo_sung` so
  với bốn dynamic table trong `form_maps`.
- Sửa AUD-002 và AUD-003 trong cùng Wave A; không chia thành hai production fix.

## 4. Lỗi layout/nội dung đã xác nhận trên toàn bộ 87 form

### AUD-004 — Newline metric giảm bất thường

- `check_layout_l1`: 263 block paragraph chứa newline, thấp hơn threshold 293.
- Cần phân loại từng delta: paragraph chuyển thành table hợp lệ hay extractor làm
  mất ngắt dòng. Không hạ threshold trước khi có bảng giải thích.

### AUD-005 — Header bảng bị glue và digit-run

- PLII_M02 block `#69`, `#122`: `STT` dính tên cột; cùng hai block chứa chuỗi
  `12345678910`.
- PLI_M72 block `#109`, `#112`: `STT` dính tên cột cổ đông.
- Gate: sau fix, STT-glue = 0 và digit-run = 0; không allowlist che lỗi.

### AUD-006 — Footnote dính chữ trên 23 form

Danh sách chính xác từ `numbering_report.json`:

`PLII_M01`, `PLII_M02`, `PLI_M01`, `PLI_M02`, `PLI_M03`, `PLI_M04`,
`PLI_M05`, `PLI_M06`, `PLI_M08`, `PLI_M09`, `PLI_M12`, `PLI_M13`,
`PLI_M15`, `PLI_M17`, `PLI_M19`, `PLI_M21`, `PLI_M27`, `PLI_M32`,
`PLI_M66`, `PLI_M67`, `PLI_M68`, `PLI_M69`, `PLI_M72`.

Gate: extractor sandbox regen đưa GLUE về 0 mà không xóa chữ số nội dung thật;
sau đó Lead mới regen global và chạy visual lại.

### AUD-007 — Chuỗi đánh số companion bị đứt

- `PLI_M03 → PLI_M06`: 6 → 8, thiếu mục 7.
- `PLI_M04 → PLI_M08`: 7 → 10, thiếu mục 8–9.
- `PLI_M05 → PLI_M09`: 6 → 7, hiện PASS.

Không tự chèn nội dung pháp lý. Phải đối chiếu mẫu đang có hiệu lực và ghi
source evidence trước khi sửa.

## 5. Khoảng trống bảng/UI chưa được phép tuyên bố PASS

### AUD-008 — Coverage 111 section đang drift

Manifest vẫn tổng hợp 33 form `BLOCKED_LEGAL_REVIEW`, trong khi một số section
đã có spec/template/runtime mới như capital M03/M04/M05/M12, tax PLII_M02 và
M09. Vì vậy con số “33 bảng thiếu” hiện không đáng dùng để chia việc.

Agent coverage phải tạo ma trận 111/111 theo `PLAN.md` Wave B, kiểm hai chiều:

`source → spec → template → form_maps → blocks → runtime → draft → validation → DOCX → visual`.

Chỉ sau ma trận này mới kết luận chính xác bảng nào:

- đã implement và kiểm chứng;
- thiếu cột;
- thiếu implementation;
- output-only;
- bị chặn owner/pháp lý;
- không phải bảng hoặc đã bị văn bản hiện hành loại bỏ.

### AUD-009 — Lỗi bảng ngành `undefined`/mã `6` chưa tái hiện được

Đây là finding từ thao tác người dùng, nhưng static source không đủ đóng hoặc bác
bỏ. Agent UI phải tạo regression test từ draft/autosave/legacy migration và kiểm
`ma_nganh`, `ten_nganh`, row ID, VSIC selection, reload và export payload.

### AUD-010 — Hình thức chọn “Ngành nghề kinh doanh chính” chưa chốt

Radio giữ đúng semantics “chỉ một lựa chọn”, nhưng hình tròn/vuông phải đối
chiếu mẫu nguồn. Không đổi behavior hoặc CSS theo cảm tính.

### AUD-011 — Chữ ký, checkbox và bảng thuế cần visual evidence mới

- khoảng trống chữ ký trên UI và Word;
- dấu `X` checkbox có rơi sang dòng riêng;
- PLII_M03–M06 có số mồ côi do bảng thuế bị làm phẳng hay không;
- header hai band của 22 mẫu sau các merge mới;
- M09 sau rebuild.

Các mục này là **NOT RUN/OPEN**, không phải PASS từ test package DOCX 87/87.

## 6. Inventory visual phải chạy lại

Agent có browser/Word phải quét không sampling:

1. **87 form**, **28 use case**, **5 variant M72**.
2. UI tại 1280/768/375 px và zoom 100/150/200%.
3. Trạng thái rỗng, hợp lệ, lỗi, draft cũ và bảng có nhiều dòng.
4. Mọi table kind: add/delete/reorder/duplicate/one-row/round-trip/export.
5. DOCX/ZIP mở bằng Word hoặc LibreOffice, kiểm bảng, page-break, marker,
   footnote, chữ ký, checkbox và trang trắng.
6. Mỗi verdict phải là `PASS | FAIL | NOT RUN` kèm screenshot/page/repro.

Đầu ra bắt buộc:

- `generated_ho_so/_visual_layout/whole_app_audit/inventory.json` đủ 87 form;
- `use_case_matrix.json` đủ 28 use case;
- screenshot/PDF theo form + viewport/variant;
- report nhóm lỗi theo root cause, ưu tiên data-loss/blocking trước cosmetic.

## 7. Thứ tự cho agent mới

1. Bắt đầu **Wave A**: sửa AUD-002/AUD-003 và phân loại a11y preflight.
2. Chạy runner đến 0 FAIL/0 critical NOT RUN trên môi trường phù hợp.
3. Tạo **Wave B coverage 111/111**; chưa sửa bảng hàng loạt trước gate này.
4. Tạo auditor read-only cho **Wave C visual 87/87** trên commit coverage sạch.
5. Chỉ sau inventory Wave C mới chia coding lane theo root cause.
6. Tuân thủ worktree/file ownership/merge SOP trong `PLAN.md` mục 6.

## 8. Điểm dừng và cách báo cáo

Agent không được tuyên bố app hoàn tất khi mới đạt structural render. Báo cáo
checkpoint phải có:

```text
BASE / HEAD / WORKTREE
DIFF_ALLOWLIST / COMMITS
TESTS_PASS / TESTS_FAIL / TESTS_NOT_RUN
FORMS_AUDITED / USE_CASES_AUDITED / M72_VARIANTS_AUDITED
TABLE_COVERAGE_DELTA
EVIDENCE_PATHS
OPEN_DEFECTS / BLOCKED_OWNER
GIT_STATUS
```

Visual QA, WebView2, `.exe` smoke, Word/PDF và full Excel rollout không được ghi
PASS nếu chưa chạy thật trên HEAD được báo cáo.
