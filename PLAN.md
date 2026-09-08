# MASTER PLAN v7 — HOÀN THIỆN TOÀN BỘ SẢN PHẨM SAU PHASE 6V

> **⚠️ REOPEN F3H — HEADER-SUBJECT-SEMANTICS, 2026-09-08
> (`main@b2ec33c`, tree sạch):** owner phát hiện gate D17 hiện tại mới chứng
> minh binding/sync, chưa chứng minh mọi occurrence “TÊN DOANH NGHIỆP/TÊN HỘ
> KINH DOANH” được dùng đúng **vai trò pháp lý và UX**. Phải đóng F3H trước
> khi tiếp tục ký F5 trên corpus. Hai fixture phân biệt bắt buộc:
> `PLI_M31` nguồn có band `TÊN DOANH NGHIỆP` + dòng điền, nên phải **giữ nhãn
> pháp định và điền tên ngay dưới**; `PLI_M72` nguồn không có band này, chỉ có
> mục `1. Tên doanh nghiệp`, nên **không được tự thêm band**. Không xóa nhãn
> M31 chỉ vì tên lặp ở thân, và không thêm nhãn M72 để làm giao diện đồng đều.
> Chi tiết thực thi/gate: mục **F3H**.
>
> **✅ CHECKPOINT WAVE F0L–F4 — 2026-09-07 (Lead session, base `44f21bc`):**
> current-law migration L-2026 ĐÓNG ở mức kỹ thuật + **111/111 section đều có
> verdict, BLOCKED_OWNER = 0**:
> (1) **F0L** — 4 văn bản ký số (TT 121/2026, NĐ 296/2026, TT 68/2025,
> NĐ 168/2025) tải + SHA-256 (`docs/legal_sources_2026/`); 9 mẫu
> M1–M5/M10/M12/M27/M30 migrate qua source→spec→generator theo ảnh trang
> (delta inventory 10 form + ND296 22 điều); **PLI_M11 REMOVED_BY_CURRENT_LAW**
> (stamp + catalog + gate `test_current_law_catalog`); M09 decontaminate
> (129 đoạn nhiễm) verdict REMOVED_BY_SOURCE_CLEANUP; N-v4 M07 rebuild từ
> bản in TT68 p49-50; N-v1/N-v2 band-is-input M33/PLII_M06 (census 23/23
> bind, 0 blocked_owner); N-v3 mirrors M48/M49/M70. Lead proofread ảnh
> bắt 2 lỗi transcribe (M10 'họ hàng'→'hợp đồng'; M27/M30 mất tiêu đề khối ký).
> (2) **F1** — 10/10 user-input (M02 radio exclusive, M12×3 matrix O2
> computed-strict, M27×2 grid 2026, M78/79/80, PLII_M02-c5) + 11/11
> output-only (M52/M56/M63/M66×2/M67/M68/M70/M71/M75×2, mirror cell) +
> M09 removed — coverage `85 IV · 17 OUTPUT_ONLY · 7 NO_TABLE · 1+1 REMOVED`,
> drift 0.
> (3) **F2** — full sweep: 38/38 suite; 87 form render sạch; 2186 key
> 0 thiếu control; Chromium viewport×3 / zoom 200% / keyboard-only / ARIA /
> focus ring PASS; error-focus-first-field + btable-wrap đã fix; WebView2
> vẫn là gate Windows riêng. Evidence `docs/audits/ui_sweep_f2_2026-09-06.*`.
> (4) **F4** — Excel P6=C đủ 4 cụm: M72 pilot + hộ kinh doanh (4
> questionnaire) + thay đổi ngành (37 câu) + thuế (12 câu, phần thuế thật
> ở M12; N/A có reason); round-trip/negative/mã dài PASS.
> (5) **Fixture fix sau dryrun review** — slot ngày thành phần điền NGÀY
> (hết double-date); EXCLUSIVE_GROUPS +chu_the_hkd. Runner: **VERDICT PASS**.
> **F3 corpus kỹ thuật đã chạy** tại `9f15d58`: `phase8f_final` 450 record /
> 1752 PNG, HARD 0, candidate chưa adjudicate 0, ZIP 450/450, Word 90/90,
> determinism 450/450 và runner VERDICT PASS. Tuy nhiên human review phát hiện
> hợp đồng vai trò band tên chưa được diễn đạt/khóa đủ chặt, nên mở **F3H** và
> coi corpus/hash này là stale đối với F5. Trình tự mới: F3H → corpus mới → F5
> AI/human review → F7 auditor.
> Windows S1–S8 vẫn **NOT RUN** (O6 — handoff kit sẵn ở
> `tools/windows_handoff/`). Không push (chờ lệnh owner).

> **✅ CHECKPOINT WAVE v7 — 2026-09-05 (sau commit `9f756f6`):** hai defect
> ưu tiên của mandate đã đóng ở mức kỹ thuật + gate hard:
> (1) **HEADER-NAME-SYNC** — 20/22 slot band bind mirror read-only qua
> registry `tools/header_name_binding.json`; gate hard `D17_header_name`;
> PLI_M32 E2E 8/0; 2 slot BLOCKED_OWNER (PLI_M33, PLII_M06 — packet
> `docs/owner_decision_packet_v7.md` N-v1/N-v2). *(Cả hai đã đóng bằng
> N-v1/N-v2 band-is-input ở wave F0L–F4.)*
> (2) **SIGNATURE-USABILITY-SPACE** — sàn ký tay 72pt toàn corpus; D6 đồng
> bộ census (coverage 420/420, expected-but-zero = 0); min gap 72.9pt /
> median 119.6pt / <72pt = 0; "Đã ký" được đo nhưng không áp sàn; mutation
> V2a/V2b đủ theo mandate. *(Corpus phase7v chỉ còn là baseline kỹ thuật —
> corpus final là phase8f.)*
> Corpus mới `generated_ho_so/_visual_layout/phase7v/final/` (455 record):
> HARD 0 · candidate chưa adjudicate 0 · export error 0 · PNG 1653==đĩa ·
> ZIP 455/455 · Word 16.16.27 open-direct 91/91. Runner sau wave: xem
> `docs/execution_ledger.md` wave v7. Human review corpus mới vẫn
> **NOT_REVIEWED** (O5); Windows vẫn NOT RUN (O6).

> **Kế hoạch duy nhất có hiệu lực từ 2026-09-05.** Lịch sử P0→P5R→6V nằm
> trong `docs/execution_ledger.md`, `docs/defect_registry.md` và git. Không
> triển khai lại phase đã đóng nếu regression guard vẫn xanh.
>
> **Mục tiêu vận hành:** một Lead session chạy liên tục đến kết luận cuối,
> dùng tối đa 3 subagent/worktree song song, không tự dừng giữa các wave để xin
> checkpoint. “Một session” không biến việc của con người hoặc phần cứng không
> tồn tại thành PASS: thiếu quyết định pháp lý, human sign-off hoặc máy Windows
> thì kết quả cuối bắt buộc là `BLOCKED`/`NOT RUN`, kèm đúng gói tiếp tục.

> **OWNER DECISIONS 2026-09-06:** owner đã ủy quyền Lead tự duyệt toàn bộ
> packet v7. N-v1..N-v4 và O1..O8 đã chốt tại
> `docs/owner_decision_packet_v7.md`; không hỏi lại. O5/O6 vẫn là evidence
> outstanding, không phải decision outstanding. Đồng thời mở gate pháp lý
> **L-2026**: Thông tư 121/2026/TT-BTC đã thay Mẫu I.1–I.5, I.10, I.12,
> I.27, I.30 và bãi bỏ I.11 từ 21/08/2026; Nghị định 296/2026/NĐ-CP đã sửa
> Nghị định 168/2025/NĐ-CP. Mọi corpus hiện có trước migration này chỉ là
> baseline kỹ thuật, không được dùng để tuyên bố current-law release.

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
- Current-law migration mới mở ngày 2026-09-06: thay/rebuild `PLI_M01`–
  `PLI_M05`, `PLI_M10`, `PLI_M12`, `PLI_M27`, `PLI_M30` theo Thông tư
  121/2026/TT-BTC; đưa `PLI_M11` khỏi active catalog với verdict
  `REMOVED_BY_CURRENT_LAW`. Đây là prerequisite trước corpus/release cuối.
- Windows/WebView2/.exe smoke S1–S8: **NOT RUN — chưa có evidence Windows**.
- Defect owner báo sau 6V — **HEADER-NAME-SYNC**: ít nhất `PLI_M32` có
  `dn.ten_tieng_viet` ở thân mẫu nhưng ô header đầu trang vẫn là literal
  `TÊN DOANH NGHIỆP\n-------`; nhập tên phía dưới không cập nhật header UI/
  DOCX. Đây là lỗi binding thật, không phải cosmetic và chưa được 6V detector
  bắt. Owner đã chốt yêu cầu: nhập tên một lần, header phải đồng bộ.
- Audit vùng ký Phase 6V từng mở defect **SIGNATURE-USABILITY-SPACE** (chi tiết:
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
    khá chật;
  - **đã đóng kỹ thuật ở phase7v:** detector 420/420, min 72.9pt, gap <72pt
    bằng 0, split/orientation/missing bằng 0. Human review corpus mới vẫn
    `NOT_REVIEWED`.
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
| L-2026 | Baseline pháp lý sau NĐ 296/2026 + TT 121/2026 | **DECIDED:** migrate 9 mẫu bị thay, bỏ active M11 trước release |
| O1 | Adjudicate 22 section | **DECIDED:** 10 user-input, 11 output-only, 1 removed-by-source-cleanup; mapping exact trong packet v7 |
| O2 | WLAY-005/M12 | **DECIDED:** implement từ Mẫu 12 TT 121/2026, computed totals/mismatch blocking |
| O3 | Q-P4-1 `min_rows` | **DECIDED:** enforce min 1 chỉ khi section active; blank row không tính; max null |
| O4 | Mã định danh dài M09/M72 | **DECIDED:** preserve string/leading zero; wrap/landscape, không truncate |
| O5 | Review corpus cuối | **PROCESS DECIDED:** AI review 100% được phép; human evidence vẫn outstanding |
| O6 | Windows sạch | **AUTHORIZED:** chạy khi có máy; hiện vẫn NOT RUN |
| O7 | Excel ba cụm còn lại | **DECIDED:** triển khai đủ P6=C, auditor độc lập duyệt artifact |
| O8 | Vùng ký | **DECIDED + IMPLEMENTED:** manual floor 72pt; “Đã ký” miễn; detector 100% |

22 section phải được xuất tự động từ `docs/table_coverage_current.json`, không
chép tay rồi bỏ sót. Áp exact mapping đã duyệt trong packet v7; trạng thái chỉ
đổi khỏi `BLOCKED_OWNER` sau khi implementation/evidence tương ứng hoàn tất.

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

### F0L — Current-law migration 2026 (mở sau owner-delegated review)

Thực hiện trước F1/F2/F4 và trước khi sinh corpus mới:

1. tải/lưu hash bản ký số chính thức của TT 121/2026 và NĐ 296/2026; lập
   inventory khác biệt source 2025→2026 cho `PLI_M01`–`PLI_M05`, `PLI_M10`,
   `PLI_M12`, `PLI_M27`, `PLI_M30`;
2. migrate spec, canonical fields, use-case, UI/validation, template và
   questionnaire theo từng khác biệt có evidence; không OCR rồi tin mù—review
   ảnh trang nguồn và mutation test các field/bảng mới hoặc bị bỏ;
3. đưa `PLI_M11` khỏi active catalog với `REMOVED_BY_CURRENT_LAW`; giữ alias/
   migration đọc draft cũ nhưng không cho tạo hồ sơ mới bằng mẫu bị bãi bỏ;
4. đối chiếu ảnh hưởng NĐ 296/2026, đặc biệt xác thực điện tử và chủ sở hữu
   hưởng lợi, với M01–M05/M10 và validation hiện hành;
5. Lead regen generated artifacts ×2 zero-diff, cập nhật census denominator,
   coverage/manifest/use-case inventory và exact allowlist;
6. test current-law negative phải đỏ nếu active catalog còn M11, nếu hash
   source sai, hoặc một trong 9 mẫu vẫn mang fingerprint cấu trúc 2025.

**Gate F0L:** 9 mẫu thay thế khớp source chính thức; M11 inactive; mọi delta có
mapping/migration/test; runner + coverage + deep idempotency xanh. Corpus
`phase7v` không được tái sử dụng làm final evidence sau gate này.

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
   `fillable-header-slot` hay `legal-title/subtitle`. Với slot fillable, **giữ
   nhãn pháp định**, chỉ thay dòng điền/placeholder bên dưới bằng giá trị
   canonical cùng key ở thân mẫu; không thêm field/key thứ hai. Nếu payload
   rỗng nhưng workflow vẫn cho phép xuất bản nháp thì phải giữ một vùng điền
   nhìn thấy được, không được để trơ mỗi nhãn. Với title/subtitle (ví dụ tiêu
   đề loại hình M72), giữ nguyên. Fix qua spec/generator rồi Lead regen—cấm sửa
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

### F3H — Dứt điểm vai trò tên chủ thể ở đầu biểu mẫu

F3H là defect wave bắt buộc phát sinh từ human review. Không coi corpus
`phase8f_final` là đủ điều kiện human sign-off cho đến khi gate dưới đây xanh.
Mục tiêu không phải làm mọi mẫu giống nhau; mục tiêu là mỗi mẫu giống **đúng
nguồn hiện hành** và người dùng luôn biết nhập tên ở đâu.

#### F3H.1 — Một registry occurrence-level làm nguồn chân lý

Mở rộng `tools/header_name_binding.json` (hoặc sinh registry kế nhiệm có migration
rõ) để **mọi occurrence** liên quan tên chủ thể trong active catalog có record:

- `form_id`, variant/branch nếu có, source path + hash + vị trí evidence;
- `role` đúng một trong:
  - `required_band_mirror`: nguồn có band; nhãn pháp định luôn giữ; tên lấy từ
    một input canonical ở thân và band chỉ mirror read-only;
  - `required_band_input`: nguồn có band nhưng thân không có field tương đương;
    band là input duy nhất (`PLI_M33`, `PLII_M06` hiện thuộc nhóm này);
  - `no_subject_band`: nguồn không có band tên; cấm generator/UI tự thêm
    (`PLI_M72` và các form tương ứng);
  - `legal_title_or_subtitle`: chữ “tên doanh nghiệp/hộ” là tiêu đề, nhãn mục,
    tên loại hình hoặc câu pháp định; giữ nguyên, không biến thành input;
  - `output_mirror`: nội dung do cơ quan phát hành, bind read-only từ hồ sơ;
- `subject_kind`, canonical key, `label_required`, `blank_policy`, số input và
  số mirror kỳ vọng.

Không được phân loại chỉ bằng regex. Lane census phải đối chiếu ảnh/trang của
nguồn pháp lý hiện hành; các form đã migrate theo TT 121/2026 dùng source 2026.
Mỗi occurrence chưa đủ evidence là FAIL/NEEDS-ADJUDICATION, không tự chọn mode.

#### F3H.2 — Hợp đồng UX và export

1. Người dùng nhập tên chủ thể đúng **một lần**:
   - `required_band_mirror`: input ở thân, band cập nhật trực tiếp khi gõ, xóa,
     đổi A→B, đổi form/variant và reload draft; band không có tab-stop/input;
   - `required_band_input`: input nằm ngay trong band, có label/accessible name,
     draft/validation/export dùng cùng canonical key; không sinh input ẩn ở thân.
2. DOCX/PDF với tên đã nhập phải giữ nhãn pháp định và đặt tên vào đúng dòng
   điền; cấm output kiểu chỉ còn `TÊN DOANH NGHIỆP`/`TÊN HỘ KINH DOANH` mà
   không có giá trị hoặc vùng điền nhìn thấy.
3. Với bản nháp rỗng được phép xuất, band phải có fill-line/vùng điền đủ rõ;
   với hồ sơ final có field bắt buộc, validation phải chặn trước export.
4. `no_subject_band` không được nhận band mới. Tên ở mục thân như M72 vẫn phải
   bind đủ; việc thiếu band không phải lỗi nếu nguồn pháp lý không có band.
5. Không xóa nhãn nguồn chỉ vì tên xuất hiện lần nữa trong thân: band là chủ thể
   phát hành văn bản, còn dòng thân là nội dung kê khai. Nếu muốn một bản “rút
   gọn”, phải là output mode khác và không được thay thế bản pháp lý canonical.

#### F3H.3 — Fixture/gate bắt buộc

- Fixture tối thiểu: blank/draft, filled, A→B, Unicode dài, reload draft; M72
  chạy đủ 5 variant. Inventory form/render-unit lấy động từ active catalog,
  không hard-code denominator lịch sử.
- Fixture neo:
  - `PLI_M31`: đúng một band; literal nhãn vẫn có; giá trị canonical nằm ngay
    dưới nhãn; cùng tên ở dòng thân; 0 editable control thứ hai;
  - `PLI_M33` và `PLII_M06`: đúng một `band_input`; nhập được bằng chuột/bàn
    phím; blank/fill/reload/export nhất quán;
  - `PLI_M72`: 0 subject band ở cả 5 variant; mục `1. Tên doanh nghiệp/công ty`
    vẫn có đủ giá trị đúng variant; đổi variant không rò tên/label stale;
  - `PLI_M32`: mirror từ input thân, giữ nhãn, A→B và reload ra B.
- Thêm detector hard mới (không nhồi thêm ngoại lệ mơ hồ vào D17), tối thiểu
  bắt: `BAND_REQUIRED_MISSING`, `BAND_FORBIDDEN_PRESENT`,
  `BAND_LABEL_REMOVED`, `BAND_VALUE_OR_SLOT_MISSING`, `BAND_WRONG_KEY`,
  `DUPLICATE_EDITABLE`, `STALE_MIRROR`, `LEGAL_SUBTITLE_MUTATED`.
- Mutation test phải cố ý: xóa nhãn M31, bỏ value M31, thêm band M72, biến
  subtitle M72 thành input, dùng `dn_goc` thay `dn`, tạo hai band input và giữ
  giá trị A sau khi đổi B; từng mutation phải làm gate đỏ.
- Kiểm ba lớp độc lập: DOM/UI E2E; OOXML/DOCX structure; PDF→PNG visual. Với
  PDF, detector phải kiểm quan hệ gần nhau giữa label và value/fill-line, không
  chỉ đếm chuỗi toàn trang.

#### F3H.4 — Ownership, merge và evidence

- Lane A read-only: census occurrence-level + source-evidence matrix.
- Lane B: UI/store/draft/validation + test DOM/E2E; không sửa generator.
- Lane C: generator/export detector + mutation tests; không hand-edit generated
  artifacts.
- Lead: adjudicate matrix, merge A→B→C, regenerate template/blocks/form maps
  hai lần (lần hai zero-diff), review exact allowlist, chạy full runner và sinh
  lại corpus. Worktree/report chỉ dọn sau khi evidence đã commit.
- Bất kỳ record F5 đã review trên hash cũ đều stale. Chỉ record/hash corpus sau
  F3H mới được ký; không copy `reviewer_verdict` từ corpus cũ.

**Gate F3H:** 100% occurrence active có evidence+role; 0 role unknown; UI có
đúng một editable source cho mỗi canonical subject; tất cả required band có
label + value/slot đúng policy; tất cả forbidden band bằng 0; fixture M31/M32/
M33/PLII_M06/M72 xanh; detector hard/candidate chưa adjudicate = 0; regen lần
hai zero-diff; runner 0 FAIL; Word-open/DOCX/PDF/PNG corpus mới PASS. Visual QA
chỉ PASS sau khi đã render và xem corpus mới; nếu chưa xem thì ghi NOT RUN.

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
| G3 UI | full inventory động, 3 viewport, zoom, keyboard, draft/E2E; F3H đúng một editable source và đúng role band/no-band PASS |
| G4 Tables | 111/111 drift 0; không active section thiếu control/cột |
| G5 Documents | final corpus hard 0/candidate 0; F3H 100% occurrence đúng source-role, required band có label+value/slot, forbidden band=0; signature census/detector 100% + gap UX PASS; Word inventory động, ZIP/determinism PASS |
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
