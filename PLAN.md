# MASTER PLAN v7 — HOÀN THIỆN TOÀN BỘ SẢN PHẨM SAU PHASE 6V

> **✅ CHECKPOINT WAVE v7 — 2026-09-05 (sau commit `9f756f6`):** hai defect
> ưu tiên của mandate đã đóng ở mức kỹ thuật + gate hard:
> (1) **HEADER-NAME-SYNC** — 20/22 slot band bind mirror read-only qua
> registry `tools/header_name_binding.json`; gate hard `D17_header_name`;
> PLI_M32 E2E 8/0; 2 slot BLOCKED_OWNER (PLI_M33, PLII_M06 — packet
> `docs/owner_decision_packet_v7.md` N-v1/N-v2).
> (2) **SIGNATURE-USABILITY-SPACE** — sàn ký tay 72pt toàn corpus; D6 đồng
> bộ census (coverage 420/420, expected-but-zero = 0); min gap 72.9pt /
> median 119.6pt / <72pt = 0; "Đã ký" được đo nhưng không áp sàn; mutation
> V2a/V2b đủ theo mandate.
> Corpus mới `generated_ho_so/_visual_layout/phase7v/final/` (455 record):
> HARD 0 · candidate chưa adjudicate 0 · export error 0 · PNG 1653==đĩa ·
> ZIP 455/455 · Word 16.16.27 open-direct 91/91. Runner sau wave: xem
> `docs/execution_ledger.md` wave v7. Human review corpus mới vẫn
> **NOT_REVIEWED** (O5); Windows vẫn NOT RUN (O6); 22 BLOCKED_OWNER chờ O1.

> **Kế hoạch duy nhất có hiệu lực từ 2026-09-05.** Lịch sử P0→P5R→6V nằm
> trong `docs/execution_ledger.md`, `docs/defect_registry.md` và git. Không
> triển khai lại phase đã đóng nếu regression guard vẫn xanh.
>
> **Mục tiêu vận hành:** một Lead session chạy liên tục đến kết luận cuối,
> dùng tối đa 3 subagent/worktree song song, không tự dừng giữa các wave để xin
> checkpoint. “Một session” không biến việc của con người hoặc phần cứng không
> tồn tại thành PASS: thiếu quyết định pháp lý, human sign-off hoặc máy Windows
> thì kết quả cuối bắt buộc là `BLOCKED`/`NOT RUN`, kèm đúng gói tiếp tục.

---

## 0. Current truth — baseline phải xác minh trước khi sửa

### 0.1 Baseline đã đối chiếu tại lúc viết plan

- Base kỹ thuật: `main@000e8e2`; ban đầu tree sạch, chỉ có main worktree,
  `main` ahead `origin/main` 157 commit; **không push** khi chưa có lệnh owner.
- Phase 6V đóng ở phạm vi kỹ thuật xuất tài liệu:
  - corpus `generated_ho_so/_visual_layout/phase6v/final/`: 455 record
    (91 render unit × 5 fixture), `HARD 0`, `CANDIDATES 0`, export error 0,
    manifest khai 1631 PNG và đĩa có đúng 1631 PNG;
  - `reviewer_verdict`: **455/455 `NOT_REVIEWED`** — chưa có human sign-off;
  - Word 16.16.27 open-direct 91/91; ZIP và determinism nội dung PASS theo
    `docs/audits/6v/v5-export-audit.md`;
  - 4 audit report ở `docs/audits/6v/` đều từ PASS-WITH-NOTES trở lên, không
    BLOCKER. Bản `v2-core-audit.md` là bản Lead phục hồi rút gọn vì report gốc
    chưa commit trước khi worktree bị dọn; phải giữ note này trong audit cuối.
- Coverage live tại `000e8e2`: 111/111 section, drift 0:
  `IMPLEMENTED_VERIFIED 76 · BLOCKED_OWNER 22 · NO_TABLE 7 · OUTPUT_ONLY 6 ·
  MISSING 0 · PARTIAL 0`.
- Release runner live tại `000e8e2`: **57 PASS / 1 FAIL / 0 NOT RUN —
  VERDICT FAIL**. Suite đỏ `test_audit_wave_h_negative` H7.4 phát hiện exact
  diff allowlist thiếu đúng 4 audit artifact đã commit sau gate trước:
  `v2-core-audit.md`, `v5-export-audit.md`,
  `v5-export-audit-inventory.json`, `v5-release-audit.md`. Đây là lệch sổ/
  allowlist thật của checkpoint, không phải lỗi DOCX runtime; phải bổ sung từng
  entry có lý do và chạy lại, không tắt H7 hoặc nới sang wildcard.
- Bốn suite kế thừa chạy riêng tại `000e8e2`:
  - `tools.test_plii_m01_member_stt`: 5 PASS / 0 FAIL;
  - `tools.test_p2a_people_specs`: 13 PASS / 1 FAIL (pin PLII_M02 cũ);
  - `tools.test_r3b1_people_specs`: 8 PASS / 4 FAIL (evidence/anchor/pin
    PLII_M02 và M72 cũ);
  - `tools.test_header_layout`: 10 PASS / 1 FAIL (`PLI_M28` field-set pin cũ).
  Không được xóa/nới assertion để làm xanh; phải chứng minh pin lỗi thời hoặc
  sửa regression thật.
- Excel mới đóng pilot `PLI_M72` (X1–X6, owner đã duyệt hình). Quyết định P6=C
  yêu cầu rollout tiếp theo theo cụm: hộ kinh doanh → thay đổi ngành → thuế.
- Windows/WebView2/.exe smoke S1–S8: **NOT RUN — chưa có evidence Windows**.
- Defect owner báo sau 6V — **HEADER-NAME-SYNC**: ít nhất `PLI_M32` có
  `dn.ten_tieng_viet` ở thân mẫu nhưng ô header đầu trang vẫn là literal
  `TÊN DOANH NGHIỆP\n-------`; nhập tên phía dưới không cập nhật header UI/
  DOCX. Đây là lỗi binding thật, không phải cosmetic và chưa được 6V detector
  bắt. Owner đã chốt yêu cầu: nhập tên một lần, header phải đồng bộ.
- Audit lại vùng ký tại đúng corpus Phase 6V ngày 2026-09-05 —
  **SIGNATURE-USABILITY-SPACE đang OPEN** (chi tiết:
  `docs/audits/signature_space_census_2026-09-05.md`):
  - structural census phủ 87/87 template: 78 form có 84 cụm ký; 9 form không
    có cụm ký trong template (`PLII_M18`, `PLI_M05`, `PLI_M07`, `PLI_M10`,
    `PLI_M71`, `PLI_M72`, `PLI_M73`, `PLI_M74`, `PLI_M76`);
  - suite `python3 -X utf8 -m tools.test_phase5r_signatures` chạy thật
    **6 PASS / 0 FAIL**;
  - quét 455/455 PDF bằng ngữ pháp census mở rộng tìm 420 cụm ký, 0 cụm dưới
    sàn kỹ thuật hiện tại 40pt, 0 record có template-signature nhưng mất toàn
    bộ cụm ở output;
  - tuy nhiên 195/420 cụm ở 185/455 record, trải trên 40 form, dưới 72pt;
    trong đó 185 cụm là chỗ còn phải ký tay (10 cụm còn lại ghi “Đã ký”).
    Mức thấp nhất 43.4pt, chỉ khoảng 1.53cm, qua gate cũ nhưng nhìn thực tế
    còn chật cho chữ ký/họ tên/con dấu;
  - detector production D6 chỉ nhận 215/420 cụm do grammar hẹp và không đo
    đến mép trang khi không có dòng tiếp theo. Vì vậy kết quả Phase 6V
    `D6 hard 0` chỉ chứng minh ngưỡng 40pt trên phần detector nhận ra, **không
    chứng minh UX vùng ký đã hoàn tất**;
  - visual spot-check các trang rủi ro `PLII_M02`, `PLI_M15`, `PLI_M46`,
    `PLI_M66`, `PLII_M09` xác nhận khối không bị tách nhưng nhiều vùng 43–57pt
    khá chật. Human review toàn bộ 1631 PNG vẫn `NOT_REVIEWED`.
- `docs/product_scope_registry.md`, một phần `docs/legal_review_backlog.md` và
  nhãn OPEN lịch sử trong registries đang stale so với code/ledger hiện tại.

### 0.2 Lệnh preflight bắt buộc của Lead

```bash
cd /Users/hoangminhlong/orca/dangky_kinhdoanh
git status --short --branch
git rev-parse --short HEAD
git worktree list --porcelain
git diff --name-only
python3 -X utf8 -m tools.release_runner --json /tmp/final_v7_baseline.json
python3 -X utf8 -m tools.census.build_manifest --deep
python3 -X utf8 -m tools.test_phase6v_detectors
```

Sau đó chạy riêng 4 suite mục 0.1 và ghi đúng exit code. Nếu tree đã dirty,
Lead phân loại từng file là owner-change / generated drift / WIP cũ trước khi
tạo lane; không stash, reset hoặc ghi đè thay đổi không rõ chủ.

---

## 1. Định nghĩa “xong” — không dùng phần trăm cảm tính

### 1.1 `CORE_APP_DONE`

Chỉ được tuyên bố khi đồng thời:

1. 28/28 use case, 87/87 form và 5/5 variant M72 chạy UI → draft → validation
   → DOCX/PDF đúng dữ liệu; không section active bị thiếu input/control/bảng.
2. 111 section không còn `MISSING`, `PARTIAL`, `BLOCKED_OWNER` chưa adjudicate
   trong **scope core**; mỗi section phải là `IMPLEMENTED_VERIFIED`, `NO_TABLE`,
   `OUTPUT_ONLY` hoặc `REMOVED_BY_CURRENT_LAW` với source/owner verdict.
3. Runner chính và mọi suite kế thừa/strict đều 0 FAIL, 0 critical NOT RUN.
4. UI Chromium full sweep PASS; WebView2 thật vẫn là gate platform riêng.
5. Corpus cuối sau mọi fix: detector hard 0, candidate chưa adjudicate 0,
   manifest == đĩa; Word open-direct 91/91; DOCX/PDF/ZIP/determinism PASS.
6. Human reviewer ký mọi trang corpus cuối; máy không được tự ghi
   `reviewer_verdict=PASS` thay con người.

### 1.2 `FULL_PRODUCT_DONE`

Bao gồm `CORE_APP_DONE` và Excel P6=C hoàn chỉnh: M72 + hộ kinh doanh + thay
đổi ngành + thuế đều có questionnaire owner-approved, xuất/nạp/round-trip,
negative validation, UI và visual workbook PASS. `app_tk` có verdict cuối
`deprecated` hoặc `legacy-supported`, không còn `DECISION` mơ hồ.

### 1.3 `RELEASE_DONE`

Bao gồm `FULL_PRODUCT_DONE` và build Windows tái lập, WebView2/tkinter dialog,
offline, clean-machine `.exe` S1–S8 PASS; artifact có SHA-256 + dependency/
build manifest; auditor độc lập cuối PASS hoặc PASS-WITH-NOTES nhưng **0 note
chưa adjudicate**. Nếu thiếu máy Windows hoặc human reviewer, chỉ được báo
`TECHNICALLY_READY / RELEASE_NOT_DONE`.

---

## 2. Owner-input gate — điều kiện để thật sự kết thúc trong một session

Lead lập một packet duy nhất từ source evidence và xin owner trả lời trước khi
lane production phụ thuộc bắt đầu. Không hỏi lại các quyết định đã chốt.

| ID | Việc cần owner chốt/chuẩn bị | Default fail-closed |
|---|---|---|
| O1 | Adjudicate 22 section `BLOCKED_OWNER`: user-input, output-only, no-table, removed-by-law hay implement | giữ nguyên BLOCKED; không bịa field/bảng |
| O2 | WLAY-005/M12: hai matrix `tai_san_gop_von_*` và matrix `co_cau_loai_co_phan_sau_thay_doi`, kể cả chính tả nguồn “ưu đã biểu quyết” | không materialize 3 matrix |
| O3 | Q-P4-1: ba nested-grid có `min_rows=1` phải enforce khi active, enforce sau khi có dữ liệu, hay bỏ khai báo | giữ declaration nhưng không enforce; status BLOCKED |
| O4 | Mã định danh dài ở M09/M72: contract dữ liệu hợp pháp và policy layout/font/orientation | không đổi độ dài/format dữ liệu để làm đẹp |
| O5 | Người ký G-E và cách duyệt toàn corpus cuối | giữ 100% NOT_REVIEWED |
| O6 | Máy/VM Windows 10/11 sạch, có quyền build/smoke; cho phép mở Q-V6 | Windows/.exe giữ NOT RUN |
| O7 | Duyệt bộ câu hỏi Excel cho ba cụm còn lại | không phát hành questionnaire cho khách |
| O8 | Chốt chuẩn UX vùng ký: đề nghị tối thiểu 72pt (2.54cm) cho “ký/ghi họ tên”, và ngưỡng riêng cao hơn nếu phải đóng dấu; xác nhận 9 form không có chữ ký là đúng nguồn | giữ 40pt chỉ là legacy technical floor; không tuyên bố signature UX DONE |

22 section phải được xuất tự động từ `docs/table_coverage_current.json`, không
chép tay rồi bỏ sót. Các form cơ quan nhà nước phát hành phải được owner xác
định rõ là surface nhập của doanh nghiệp hay output/admin-only.

---

## 3. Mô hình agent/worktree cho một session

### 3.1 Giới hạn và vai trò

- Tối đa 4 agent hoạt động: **Lead trên main + 3 subagent**.
- Mỗi subagent một worktree/branch, không tự merge, không push, không dọn
  worktree trước khi Lead đã lưu report/commit cần giữ.
- Lead là chủ duy nhất của:
  `PLAN.md`, registries/ledger, `app/templates/**`, `app/data/blocks/**`,
  `app/data/form_maps.json`, manifests/census generated, allowlist và merge.
- Auditor được spawn fresh sau khi executor dừng; read-only với production.
  Report phải commit trước khi worktree bị remove.

### 3.2 Worktree chuẩn

```bash
BASE=$(git rev-parse HEAD)
git worktree add ../dangky_kinhdoanh-worktrees/final-contracts \
  -b agent/final-contracts "$BASE"
git worktree add ../dangky_kinhdoanh-worktrees/final-ui-excel \
  -b agent/final-ui-excel "$BASE"
git worktree add ../dangky_kinhdoanh-worktrees/final-docx \
  -b agent/final-docx "$BASE"
```

Lead ghi base SHA, file ownership và lệnh gate vào prompt từng lane. Nếu hai
lane cần cùng file, chạy tuần tự hoặc lane sau rebase từ main sau merge; cấm
“cùng sửa rồi giải conflict bằng chọn một bên”.

### 3.3 Merge order

1. contract/test truth;
2. UI runtime;
3. DOCX/generator source;
4. Lead regenerate generated artifacts đúng một lần, rồi regen lần hai phải
   zero-diff;
5. Excel rollout;
6. Windows packaging;
7. independent final audit.

Sau mỗi merge: diff allowlist → suite lane → deep idempotency → coverage →
runner. FAIL thì sửa gốc rễ trước merge kế; không tích lũy đỏ.

---

## 4. Chuỗi thực thi không tự dừng

### F0 — Reconcile truth và đóng nợ audit

Lead thực hiện trước khi thay production:

1. Đồng bộ `product_scope_registry`, `legal_review_backlog`, `decision_registry`,
   `defect_registry`, coverage docs và ledger với `000e8e2`/HEAD hiện hành.
   Nhãn lịch sử không được mang sang current truth.
2. Cân exact diff allowlist cho đúng 4 audit artifact mà H7.4 bắt được; mỗi
   entry ghi provenance. Chạy H7 đỏ→xanh trước mọi production merge.
3. Pin `pymupdf` đúng version đã dùng bởi gate vào dependency contract; thêm
   dependency cho browser/build chỉ sau khi probe môi trường thật.
4. Sửa hai note LOW đúng lớp:
   - F-V5-2: D15 PDF heuristic hiểu `X` nằm trong bordered cell; mutation test
     vẫn bắt X trần/rơi dòng thật;
   - F-V5-3: đăng ký cặp checkbox mô hình tổ chức PLI_M15 thành nhóm loại trừ;
     fixture và runtime validation đều không cho tick đồng thời.
5. Chạy và xử lý bốn suite kế thừa. Mỗi assertion đỏ phải có bảng:
   `premise cũ → hiện trạng → evidence → sửa test hay sửa production`.
   Mục tiêu: p2a 14/0, r3b1 tất cả xanh, PLII_M01 5/0, header 11/0.
6. Thêm toàn bộ bốn suite vào runner chính hoặc một gate `legacy-strict` mà
   release runner gọi bắt buộc; không để suite đỏ nằm ngoài release gate.

**Gate F0:** docs không mâu thuẫn; 4 suite 0 FAIL; runner 0 FAIL; tree sạch.

### F1 — Adjudicate và hoàn thiện 22 section

Lane contracts tạo matrix machine-readable cho đúng 22 section current:

- `form_id`, `section_id`, kind hiện tại;
- văn bản/source file + vị trí evidence;
- chủ thể nhập dữ liệu;
- verdict owner O1;
- schema/columns/row semantics/activeWhen;
- migration impact;
- test, UI, draft, validation và export evidence cần có.

Với section owner chọn implement:

1. spec là nguồn chân lý; không sửa tay template/form_maps/blocks;
2. implement đủ bốn kind đang dùng: editable-grid, fixed-matrix, nested-grid,
   output-table; không hạ nested thành text phẳng chỉ để nhanh;
3. computed total/cross-field/required/activeWhen/min/max rows phải nhất quán
   UI–draft–export;
4. blank user row bị lọc khi export, blankRows pháp định của mẫu vẫn giữ;
5. test negative cho thiếu cột, sai discriminator, inactive leakage, tổng sai,
   draft cũ và row boundary;
6. Lead regen ×2, cập nhật manifest/coverage từ generator.

M12 và Q-P4-1 chỉ triển khai theo O2/O3. PLI_M09 source-contamination phải
được xử lý theo source chính thức; không dùng đoạn mẫu khác nằm nhầm file.

**Gate F1:** 111/111 drift 0; `BLOCKED_OWNER=0` trong scope đã chốt; không
MISSING/PARTIAL; mọi loại trừ có owner/source verdict, không phải allowlist mù.

### F2 — Full UI sweep 5.2 và runtime E2E

Lane UI mở rộng Playwright harness thành inventory toàn bộ, không sampling:

1. render 28 use case, 87 form và 5 variant M72; kiểm mọi key active có control;
2. kiểm riêng slot tên doanh nghiệp/hộ, bảng ngành có cả tên + mã + ngành chính,
   mọi column của 4 table kind, nút add/delete/duplicate và output-only;
3. 3 viewport (desktop/tablet/narrow), zoom 200%, keyboard-only, focus ring,
   ARIA name/role/state, error focus đúng tab/field;
4. đổi form/variant, autosave, save/open JSON, reload draft cũ không mất dữ liệu;
5. activeWhen: section inactive không block validation và không lọt export;
6. fixture `empty/minimal/full/long/choice` và payload người dùng thực, không
   dùng token giả để làm evidence visual;
7. console error, `undefined/null/NaN`, overlap, overflow ngang và control không
   click được đều là FAIL.
8. **HEADER-NAME-SYNC:** với mọi form có slot tên chủ thể ở header, chỉ có một
   editable source-of-truth trong store; phần header là mirror read-only,
   không tạo input/tab-stop/validation thứ hai. Khi sửa, xóa, đổi draft hoặc
   đổi form/variant, mirror cập nhật ngay và không giữ giá trị stale. `PLI_M32`
   là fixture bắt buộc: nhập `dn.ten_tieng_viet` ở thân mẫu phải hiện cùng giá
   trị tại header. Dùng key đúng ngữ cảnh (`dn.*`, `dn_goc.*`, hộ kinh doanh,
   chi nhánh…) thay vì ép mọi mẫu về `dn.ten_tieng_viet`.

Chromium PASS không thay WebView2 PASS. Evidence lưu manifest screenshot +
viewport + form/use-case/variant + hash, không chỉ log tổng.

**Gate F2:** inventory phủ 100%, 0 missing control/column, 0 JS error, a11y
suite PASS; draft/E2E/export assertions xanh; census header-name 100% có
verdict và mọi slot fillable sync đúng từ một editable source.

### F3 — DOCX/PDF meticulousness cuối

Lane DOCX xử lý các debt còn lại dựa trên source, detector trước fix:

1. mã dài M09/M72 theo O4; không giảm dữ liệu fixture trái luật;
2. registry fill-line per-family: đối chiếu từng family với bản gốc, đăng ký
   khác biệt có chủ đích; không ép 75 form thành một style;
3. WLAY-005 M12 theo O2;
4. mọi bảng rộng: không vỡ token/tên/mã, header repeat, hàng cantSplit, đúng
   orientation/width và đủ cột;
5. title/name slot, source-indicator, checkbox, footnote, pagination, signature
   block/vùng viết, empty/trailing page tiếp tục là hard regression;
6. chạy detector/mutation trước-sau và thêm case payload người dùng thật đã
   từng phát hiện lỗi nhưng fixture cũ bỏ sót.
7. **HEADER-NAME-SYNC ở generator/export:** census toàn bộ header band có
   literal `TÊN DOANH NGHIỆP`/`TÊN HỘ KINH DOANH` và phân loại từng occurrence:
   `fillable-header-slot` hay `legal-title/subtitle`. Với slot fillable, thay
   placeholder label bằng giá trị canonical cùng key ở thân mẫu, giữ separator
   pháp định; không thêm field/key thứ hai. Với title/subtitle (ví dụ tiêu đề
   loại hình M72), giữ nguyên. Fix qua spec/generator rồi Lead regen—cấm sửa
   tay DOCX/blocks/form_maps. Test bắt buộc:
   - `PLI_M32` blank → header không có dữ liệu giả; filled → tên xuất đúng ở
     header và thân, không còn literal placeholder tại slot;
   - payload đổi tên A→B và draft reload đều xuất B ở cả hai vị trí;
   - tên Unicode/dài không vỡ band hoặc tràn sang ô quốc hiệu;
   - negative mutation thiếu binding, dùng sai key (`dn_goc`/`dn`), duplicate
     editable hoặc thay nhầm subtitle M72 phải làm gate đỏ.
8. **SIGNATURE-USABILITY-SPACE:** đồng bộ detector D6 với grammar census để
   mọi 420 cụm hiện có đều được đo; `expected signature but zero detected` là
   hard fail. Khi không có dòng kế tiếp, đo đến printable bottom boundary/page
   edge thay vì bỏ qua. Tách rõ “Đã ký” (không cần vùng viết) với
   “Ký/ghi họ tên/đóng dấu”. Sau O8, áp ngưỡng owner chốt cho từng loại, sửa
   qua generator/spec và kiểm cả khoảng trống lẫn keep-together/orientation;
   không chỉ chèn paragraph rỗng mù gây trang trắng. 9 form không có cụm ký
   phải có source/owner verdict, không tự coi absence là hợp lệ. Mutation test
   bắt buộc: grammar có/không ngoặc, “từng thành viên”, “đóng dấu”, cuối trang,
   cụm đôi ngang/dọc, gap dưới ngưỡng và mất hoàn toàn instruction.

Lead regen generated artifacts, review exact diff, regen lần hai zero-diff.

**Gate F3:** full corpus mới hard 0; candidate chưa adjudicate 0; manifest ==
đĩa; header-name sync PASS toàn census và `PLI_M32` E2E; signature detector
coverage == signature census/output truth, 0 missing cluster, 0 manual-sign
gap dưới ngưỡng O8 và 9 no-signature form có verdict; không pin số trang 1631
vì pagination có thể thay hợp lệ—chỉ pin identity và equality theo manifest.

### F4 — Excel P6=C hoàn chỉnh

Giữ nguyên pilot M72 và rollout ba cụm còn lại:

1. hộ kinh doanh;
2. thay đổi ngành;
3. thuế.

Mỗi cụm phải có questionnaire versioned do owner duyệt, câu hỏi đời thường,
mapping về canonical key, table rows, dropdown, protection, schema metadata,
documents-needed; export `.xlsx`, import, draft merge, validation và danh sách
thiếu. Test bắt buộc:

- deterministic content và protection/data-validation;
- round-trip scalar/check/radio/date/money/percent + cả 4 table kind;
- branch/variant activeWhen;
- file cũ/sai version/sửa map/thêm cột/xóa sheet/công thức độc hại/đường dẫn lạ;
- LibreOffice/Excel round-trip không mất Unicode hoặc mapping;
- UI chọn đúng procedure, cancel dialog và lỗi file hiển thị dễ hiểu.

**Gate F4:** tất cả procedure thuộc 4 cụm P6=C có questionnaire; owner duyệt
visual workbook đại diện từng cụm; Excel suites nằm trong runner; M72 không
regression.

### F5 — Human visual sign-off G-E

Chỉ thực hiện sau F0–F4 để không ký corpus stale:

1. Lead sinh corpus final mới từ HEAD sạch.
2. Công cụ review hiển thị từng record/page, form/fixture/variant và checklist;
   hỗ trợ resume, nhưng không tự điền PASS.
3. Owner/reviewer duyệt 100% trang; mỗi FAIL tạo defect có page/crop/class.
4. Fix bất kỳ FAIL nào → corpus/hash thay đổi → chỉ record bị ảnh hưởng và
   dependency pages phải review lại; auditor xác nhận freshness.
5. Manifest cuối không còn `NOT_REVIEWED`; có reviewer, timestamp, verdict,
   artifact hash. Chữ ký người không được giả bằng agent.

**Gate F5:** 100% final pages human PASS hoặc accepted-with-owner-note; 0 visual
FAIL; audit visual độc lập xác nhận manifest/sign-off khớp artifact.

### F6 — Windows/.exe + WebView2 release

Chỉ chạy khi O6 có máy/VM Windows sạch:

1. khóa Python, pywebview, WebView2, PyInstaller và mọi dependency theo version
   probe thật; tạo build config/script tái lập, không build thủ công một lần;
2. bundle đủ UI/assets/templates/data/VSIC/questionnaire, không chứa profiles,
   generated hồ sơ cá nhân, test evidence hoặc secret;
3. build hai lần từ checkout sạch; inventory nội dung và hash artifact;
4. chạy `docs/platform_smoke_checklist.md` S1–S8, mở rộng Excel export/import;
5. clean-machine không Python: launch, 28 use case representative matrix,
   draft dialog, DOCX/PDF/ZIP, Word open, Excel, offline;
6. WebView2 DevTools/console 0 lỗi nghiêm trọng; đường dẫn có dấu, space và user
   không có quyền admin phải được test;
7. quyết định P7 có hiệu lực: sau pywebview PASS, đánh dấu `app_tk` deprecated
   và loại khỏi package, hoặc test đầy đủ nếu owner đổi sang legacy-supported.

**Gate F6:** S1–S8 PASS bằng evidence Windows thật; clean-machine `.exe` PASS;
build reproducible theo manifest. macOS/compileall không thay thế gate này.

### F7 — Final independent audit và release truth

Sau khi executor dừng, spawn auditor fresh ở detached clean worktree. Auditor:

1. review toàn diff từ `000e8e2` đến candidate HEAD: ownership, generated-only,
   không hạ test/threshold/allowlist, không mất report khi dọn worktree;
2. chạy runner + `legacy-strict`, compileall, manifest deep, coverage 111/111,
   regen ×2, DOCX/PDF/ZIP/determinism, Word 91/91;
3. đối chiếu UI inventory, Excel rollout, human review hashes và Windows build/
   S1–S8;
4. audit secret/privacy: profiles và hồ sơ sinh thử không vào artifact/git;
5. ghi `PASS / FAIL / NOT RUN` từng gate; report phải commit trước cleanup.

Lead chỉ ghi `CORE_APP_DONE`, `FULL_PRODUCT_DONE`, `RELEASE_DONE` đúng mức đạt
được; cập nhật PLAN header/ledger/registries/product scope; `git status` sạch;
remove worktree đã merge. **Không push/tag/release** nếu owner chưa ra lệnh.

---

## 5. Gate matrix cuối

| Gate | PASS khi |
|---|---|
| G0 Truth | HEAD/base/dirty/ownership rõ; docs current không mâu thuẫn |
| G1 Contracts | 22 BLOCKED đã adjudicate; M12/min_rows có owner decision |
| G2 Tests | runner + legacy-strict + compileall 0 FAIL, 0 critical NOT RUN |
| G3 UI | full inventory 28/87/M72, 3 viewport, zoom, keyboard, draft/E2E và header-name mirror PASS |
| G4 Tables | 111/111 drift 0; không active section thiếu control/cột |
| G5 Documents | final corpus hard 0/candidate 0, header-name sync census PASS, signature census/detector 100% + gap UX PASS, Word 91/91, ZIP/determinism PASS |
| G6 Human | reviewer verdict 100% trên đúng hash corpus cuối |
| G7 Excel | P6=C đủ 4 cụm, round-trip/negative/UI/visual PASS |
| G8 Windows | reproducible `.exe`, WebView2/offline/clean-machine S1–S8 PASS |
| G9 Audit | auditor fresh ≥ PASS-WITH-NOTES, 0 blocker/note chưa adjudicate |
| G10 Hygiene | clean tree, worktree dọn đúng SOP, no secret, no unauthorized push |

`RELEASE_DONE` yêu cầu G0–G10 PASS. Không cộng điểm, không lấy gate này bù gate
khác, không dùng “gần xong” thay verdict.

---

## 6. Báo cáo cuối bắt buộc

```text
BASE / HEAD / BRANCH / AHEAD-REMOTE
COMMITS + MERGE ORDER
DIFF ALLOWLIST + GENERATED REGEN×2
OWNER DECISIONS APPLIED / STILL OPEN
COVERAGE 111 STATUS COUNTS + DRIFT
UI INVENTORY (use case/form/variant/viewport)
DOCX/PDF/ZIP/WORD/HUMAN REVIEW COUNTS
EXCEL CLUSTERS + ROUND-TRIP/VISUAL
WINDOWS BUILD HASH + S1–S8
TESTS PASS / FAIL / NOT RUN (từng suite, gồm legacy-strict)
AUDITOR VERDICT + FINDINGS
CORE_APP_DONE / FULL_PRODUCT_DONE / RELEASE_DONE
RISKS / BLOCKERS / EXACT RESUME COMMAND
GIT STATUS / WORKTREE STATUS / PUSH STATUS
```

Nếu bị chặn bởi O1–O7, Lead vẫn hoàn tất mọi lane độc lập còn chạy được, giữ
tree sạch, tạo một resume packet tự chứa và dừng đúng tại blocker. Không tự
chọn nội dung pháp lý, không giả human sign-off, không ghi Windows PASS nếu
chưa chạy trên Windows.
