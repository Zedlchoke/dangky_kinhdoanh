# MASTER PLAN v6 — VISUAL TOÀN MẪU & TÍNH TỈ MỈ (Phase 6V)

> **Hiệu lực:** thay thế toàn bộ MASTER PLAN v5 (2026-09-04). Lịch sử v5 nằm
> trong `docs/execution_ledger.md` và git; mọi con số v5 chỉ còn giá trị tham
> chiếu. Đây là kế hoạch duy nhất có hiệu lực.
>
> **Mandate owner (2026-09-04):** "sửa visual toàn bộ các mẫu và tăng tính tỉ
> mỉ của app" — care tuyệt đối với những chi tiết nhỏ nhất, trên cả ba tầng:
> core (nguồn/generator), visual (trang in), và kết quả xuất (DOCX/PDF/ZIP).
>
> **Đầu vào:** audit 3 lớp ngày 2026-09-04 trên HEAD `294604c` (bằng chứng:
> `/tmp/audit_l2_report.json` khi audit; bản tóm tắt trong mục 1; corpus
> `generated_ho_so/_visual_layout/phase5r_gate/final/`).

---

## 0. Nguyên tắc bất biến (mọi agent, mọi phase, không ngoại lệ)

1. **Sửa gốc rễ, đúng lớp.** Template chỉ được sinh lại qua generator
   (`tools/build_form_maps.py` regen); CẤM sửa tay `app/templates/*.docx`.
   Generated artifact chỉ được thay qua pipeline; `audit_blocks_check` +
   exact-set gate (`tools/audit_expected_diff_files.txt`) phải xanh sau mỗi
   merge.
2. **Detector trước, fix sau.** Mỗi lớp lỗi phải có detector định lượng bắt
   được lỗi (baseline ĐỎ) TRƯỚC khi fix; fix xong detector phải xanh. Không
   có lỗi nào được đóng bằng "mắt thường nhìn ổn".
3. **Evidence tự tái lập được.** Mọi kết luận phải tái tạo từ HEAD sạch bằng
   lệnh ghi trong evidence (manifest + lệnh + số liệu). Evidence không khớp
   đĩa (như sự kiện PNG M72 1567/1644) bị coi là evidence THẤT BẠI.
4. **Regen ×2 zero-diff** sau mỗi thay đổi generator/template; drift-guard
   ID1/ID7 (`test_generator_deep_idempotency`) là trọng tài.
5. **Auditor độc lập thật sự.** Auditor không được là agent đã sửa phần tương
   ứng; không được edit code; chỉ được ghi report vào `docs/audits/`. Có quyền
   REJECT merge với evidence.
6. **File ownership không chồng lấn giữa các lane.** Lane không đụng file
   ngoài ownership (kể cả test file pin trạng thái — báo Lead, không tự sửa;
   tiền lệ 5R-laneM09).
7. **Không chạy song song trên cùng profile LibreOffice.** Mọi lane làm việc
   trong worktree riêng (`dangky_kinhdoanh-worktrees/6v-<lane>`); mọi lời gọi
   soffice qua profile cách ly (sau V0 là mặc định trong code).
8. **Luật pháp lý là chuẩn nội dung.** Trước khi sửa nội dung mẫu: đối chiếu
   TT 68/2025/TT-BTC, TT 121/2026/TT-BTC (hiệu lực 21-08-2026), NĐ 168/2025,
   NĐ 296/2026. Không tự suy diễn khi xung đột — lên `decision_registry`.
9. **Sổ sách đồng bộ:** mỗi merge cập nhật `docs/defect_registry.md`,
   `docs/decision_registry.md` (nếu có quyết định), `docs/execution_ledger.md`
   (checkpoint phase). Không ghi "đã xong" khi chưa có số liệu.
10. **Con số trung thực:** summary phải tách bạch `hard-fail` và `candidate`;
    không bao giờ phát biểu "0 lỗi" khi ý là "0 hard-fail" (bài học G-E2).

---

## 1. Baseline khởi đầu — audit 2026-09-04 @ `294604c`

### 1.1 Đã đóng (không làm lại, chỉ giữ regression guard)

| Hạng mục | Bằng chứng |
|---|---|
| Trang trắng 0/1567 (kể cả 25 record M72 mọi biến thể) | text-scan toàn corpus |
| M70 chữ ký ngang 1×2 không viền, cantSplit, ~5cm vùng viết | vision + B2 PASS |
| Orphan signature page 0 (subset B5) | `test_phase5r_signatures` 6/6 PASS |
| sectPr bug F1 (Lane D) đã sửa | `test_phase5r_metadata` PASS |
| Gate 57 PASS / 0 FAIL / 0 NOT RUN trên máy sạch | `/tmp/runner_clean2.json` |
| Word mở trực tiếp 91/91 | `word_open_inventory.json` (5R) |

### 1.2 Còn tái hiện — mục tiêu tiêu diệt của plan này

| Mã | Lớp lỗi | Quy mô (đo được) | Gốc rễ đã định danh |
|---|---|---|---|
| **B1** | Ngày/tháng/label dính nhau (`ngày04tháng…`, `:CÔNG TY`, `…vnWebsite:`) | 303 hit / 55 form, mọi fixture | Template skeleton không space quanh placeholder (VD PLII_M08: `{dia_diem_ky}, ngày{ngay_ky_vb}tháng{thang_ky_vb}năm{nam_ky_vb}`) |
| **B2** | Slot tên DN/hộ KD không nhận tên (gạch/chấm/trống) | ~37/72 form có slot tên | 3 gốc rễ: (a) template không có placeholder (PLII_M08); (b) có `{key}` nhưng form_maps thiếu tag (PLII_M02); (c) slot literal `……` trong khi slot cạnh có key (PLII_M13). 48/87 form đã bind đúng |
| **B3** | Tick checkbox = chữ "X" trần trước nhãn, không ô vuông | mọi form có chk | Render ghi giá trị "X" vào text; template không có ô vuông |
| **B4** | Giá trị trông như mã kỹ thuật (`NOI_O_HIEN_TAI_123`, `_HIEN`/`_TAI_1` bị wrap xé dòng) | 938 hit / 73 form | Fixture fallback sinh `LABEL_HOA_N` (phase5_fixtures.py:196-198) + token dài rơi cột ~1cm bị Word wrap giữa token |
| **B5** | Bảng 9–15 cột không đọc được (min col 566 twips ≈ 1.0cm; vision M12: cột hẹp nhất 1–2mm, M09: 2–3mm) | 60 bảng / 10 form (PLII_M01/02, PLI_M02/06/07/09/10/12/15/72) | Policy `min_col 567` rebaseline theo census thực tế (81b5931) → sàn cho phép cái con người không đọc được |

### 1.3 Lỗi hạ tầng gate (phải sửa TRƯỚC mọi lane visual)

| Mã | Vấn đề | Hệ quả |
|---|---|---|
| **I1** | soffice dùng profile mặc định dùng chung; 2 tiến trình chồng nhau → exit=1; run bị kill giữa chừng để lại `.lock`/zombie → mọi lời gọi sau đều chết | Gate đỏ giả 56/1 (2026-09-04); mất giờ chẩn đoán; nguy cơ tái diễn bất cứ khi nào 2 agent/run song song |
| **I2** | PNG M72: 25 record ghi chung 1 thư mục `final/<fixture>/PLI_M72/` → ghi đè lẫn nhau | manifest claim 1644 trang, đĩa 1567; 4/5 biến thể trỏ ảnh NHẦM; M72 không audit lại được từ corpus |
| **I3** | Summary chỉ đếm hard-fail; D9/D10/D11 hits nằm `gate_candidates` → in "D9=0" dù det_table_grid bắt được NARROW_COL trên chính corpus final | Ngôn ngữ "D1..D12=0" gây hiểu sai "không còn finding" |
| **I4** | `MIN_COL_TWIPS=567` nhưng census có bảng 566 → candidate vĩnh viễn không ai chặn | B5 sống sót qua gate |

---

## 2. Hướng đi

Mô hình tổng: **"Hạ tầng tin cậy → Detector phủ sâu → Fix theo lớp → Quyết
định owner cho cái khó → Quét tỉ mỉ toàn mẫu → Audit độc lập 3 tầng →
Checkpoint đứng vững."**

```
V0 Hạ tầng gate      ──gate V0──▶  V1 Detector mở rộng (baseline ĐỎ)
      │                                    │
      │                       ┌────────────┼─────────────┬──────────────┐
      ▼                       ▼            ▼             ▼              ▼
   (song song)          C4 Fixture    C1 Glue 55f   C2 Name-slot   C3 Chk glyph
   worktree/lane        (realism)     (regen skel)  (37 form)      (sau Q-V1)
                              └────────────┴─────────────┴──────────────┘
                                    merge TUẦN TỰ về main (Lead), mỗi merge:
                                    regen×2 → census → runner → visual gate
                                           │
                                           ▼
                              V3 Bảng rộng (sau Q-V2 owner)
                                           ▼
                              V4 Meticulousness sweep toàn 91 mẫu
                                           ▼
                              V5 Audit độc lập 3 tầng + checkpoint final
```

Nguyên lý An Toàn: V0 là điều kiện cần của mọi phase sau (không có evidence
đúng thì mọi "xanh" sau đó là giả). V1 phải ĐỎ đúng bằng số liệu mục 1.2 —
đó là định nghĩa "đã bắt được hết lỗi đã biết". V2 mỗi lane có detector riêng
làm trọng tài. V3 không tự quyết (Q-V2). V4 là vòng "tỉ mỉ" quét từng chi
tiền nhỏ chưa có tên trong B1–B5. V5 chỉ kết luận khi 3 auditor độc lập
(core/visual/export) cùng ký.

---

## 3. Tổ chức agent

### 3.1 Agent thực thi (subagent, có worktree riêng)

| Agent | Role | Ownership (được sửa) | CẤM đụng |
|---|---|---|---|
| `agent/6v-infra` | Hạ tầng gate & evidence: profile soffice cách ly, PNG per-variant, summary hai lớp, preflight runner, test concurrency | `app_web/main.py` (chỉ đường export/soffice), `tools/phase5_visual_gate.py` (analyze/render/summary), `tools/release_runner.py`, test mới | templates, form_maps, detectors ngữ nghĩa |
| `agent/6v-detectors` | Detector mở rộng D13–D16 + nâng D9; baseline đỏ pin bằng số liệu audit; negative tests | `tools/phase5_visual_gate.py` (detector + verdict), `tools/phase5r_table_policies.json`, `tools/test_phase6v_detectors.py` | mọi file fix lỗi (detector phải độc lập với fix) |
| `agent/6v-glue` | Diệt B1: chuẩn hóa space quanh placeholder trong skeleton 55 form qua regen; mở rộng xử lý `{dien_thoai_khac}Thư điện tử` | `tools/build_form_maps.py` (skeleton normalize + regen), allowlist diff, rebaseline census/policies | `app_web/**`, docx_render |
| `agent/6v-nameslot` | Diệt B2: phân loại chính xác 37 form thành 3 gốc rễ; engine extension chèn placeholder khi template thiếu; tag field form_maps; regen | `tools/build_form_maps.py`, `tools/form_specs/**`, `app/data/form_maps.json` (qua generator), engine spec extension | `app_web/**`, detector files |
| `agent/6v-chk` | Diệt B3: glyph ô vuông + X theo chuẩn owner chốt (Q-V1); cả UI shape và DOCX | `app_web/ui/**` (render chk), `tools/docx_render.py` (chỗ ghi X), tests | templates trực tiếp, fixture |
| `agent/6v-fixture` | Diệt B4 phía fixture: ValueFactory fallback → giá trị tiếng Việt thực + chỉ số nhúng (`Nơi ở hiện tại số 123`), giữ tính phân biệt cho D12; selftest cập nhật | `tools/phase5_fixtures.py` | templates, form_maps |
| `agent/6v-tables` | Diệt B5 theo phương án Q-V2 (landscape trang bảng / giảm font + sàn 900twips / split); width_policy + section orient khi cần | `tools/build_form_maps.py`, `tools/form_specs/**`, policies | quyết định pháp lý (chỉ implement) |
| `agent/6v-micro` | V4 meticulousness: census chi tiết nhỏ toàn 91 mẫu theo checklist 5.2; fix theo nhóm qua regen | theo nhóm được giao từng đợt (Lead cấp) | tự quyết phạm vi |

Quy tắc spawn: mỗi agent nhận prompt tự chứa (mã lỗi + số liệu + file +
gate); PHẢI chạy trong worktree riêng; KHÔNG merge tự vào main — Lead merge.

### 3.2 Agent audit độc lập (read-only, không được sửa code; report vào `docs/audits/`)

| Auditor | Phạm vi audit | Câu hỏi trọng tài | Đầu ra |
|---|---|---|---|
| `auditor/6v-core` | Sau MỖI merge lane: diff review đúng lớp hay vá symptoms; có nới test/allowlist che lỗi; regen ×2 zero-diff thật; drift-guard; ownership vi phạm | "Fix này có đứng vững khi regen lại từ nguồn không?" | verdict PASS / PASS-WITH-NOTES / FAIL + findings vào `defect_registry` |
| `auditor/6v-visual` | Corpus PNG/PDF sau mỗi phase: quét census (không sampling) theo checklist 5.2 + đối chiếu detector counts với mắt (vision tooling); ký `reviewer_verdict` per record | "Trang in này có đạt chuẩn một người Ketoan/Phòng ĐKKD đọc không?" | bảng verdict 91 form × fixture; mọi trang trắng/glue/token/tick sai phải có trang+file |
| `auditor/6v-export` | Kết quả xuất end-to-end: DOCX+PDF+ZIP integrity, manifest == đĩa 100% (kể cả M72), word-open loop 91/91, export 2 lần identical (determinism), concurrency 2 runner song song | "Từ nút Export đến file người dùng cầm — có gì sai không?" | inventory + hash + verdict per artifact |
| `auditor/6v-release` | MỘT lần cuối (V5): tái lập toàn bộ từ worktree sạch theo đúng lệnh trong evidence; đối chiếu mọi con số checkpoint | "Checkpoint này có đứng vững trên máy khác không?" | báo cáo final ký tên phase |

Auditor KHÔNG dùng chung context với executor (spawn fresh); auditor từ chối
kết luận khi thiếu evidence (ghi NOT-RUN) — không được đoán.

### 3.3 Vai trò con người

- **Owner:** quyết Q-V1..Q-V6 (mục 6); duyệt checkpoint V5; duyệt mở Windows
  packaging (ngoài scope plan này).
- **Lead (main session):** spawn/merge, giữ ownership không chồng, adjudicate
  xung đột lane-vs-auditor, cập nhật sổ sách, dừng khi auditor FAIL.

---

## 4. Phases

### V0 — Hạ tầng gate tin cậy (`agent/6v-infra`, tuần tự, ~1 buổi)

1. `app_web/main.py`: mọi lời gọi soffice thêm
   `-env:UserInstallation=file:///tmp/lo_prof_<case_id>` (một profile cách ly
   mỗi export run; dọn sau run). Exit=1 → retry đúng 1 lần với profile mới;
   message lỗi phân biệt `LO_PROFILE_BUSY` / `LO_CRASH` thay vì `soffice
   exit=1` mơ hồ.
2. `tools/phase5_visual_gate.py`: PNG dir theo record thật
   (`final/<fixture>/<variant>/<FORM>/page-NN.png`); assert cuối mỗi run:
   số file PNG == Σ manifest pages (phá ngay sự kiện 1567/1644).
3. Summary hai lớp: `summary.json` thêm `hard_fails` VÀ `candidates` đếm theo
   detector + list candidate IDs; chữ in ra gate tách rõ hai con số.
4. `tools/release_runner.py`: preflight cảnh báo nếu thấy tiến trình soffice
   của run khác đang sống (giảm chẩn đoán 56/1 về 0 phút).
5. Suite mới `test_export_concurrency` (đăng ký runner): 2 export chạy song
   song (2 process, 2 profile) phải 2 PASS, 0 exit=1.

**Gate V0:** (a) 2 runner song song → 2 PASS; (b) PNG disk == manifest 100%
sau re-render corpus 1 lượt; (c) runner 57/0/0 máy sạch; (d) summary in cả
hard-fail lẫn candidate. Auditor `6v-core` ký V0.

### V1 — Detector mở rộng + baseline ĐỎ (`agent/6v-detectors`)

Detector mới (đề đăng ký hard-fail; số liệu chốt theo audit 2026-09-04):

- **D13 glue**: `(ngày|tháng|năm)\d` | `\d(ngày|tháng|năm)` | `\):[A-ZÀ-Ỹ]` |
  `(Fax|Website|Thư điện tử|Điện thoại):` dính giá trị kế. Kỳ vọng baseline
  ≈ 55 form / 303 hit.
- **D14 name-slot**: mọi form có slot tên dưới tiêu đề phải (i) chứa giá trị
  non-empty ở valid-full, HOẶC (ii) nằm trong registry
  `handwriting_only_slots` (khai báo chủ đích, có lý do pháp lý). Kỳ vọng
  baseline ≈ 37 form.
- **D15 chk glyph**: tick phải là X ĐẶT TRONG ô vuông (shape/bảng/ký tự ☒ theo
  Q-V1); bắt "X trần trước nhãn" và "X rơi dòng riêng". Baseline: mọi form
  có chk.
- **D16 token-fragment**: PDF text có dòng chỉ chứa mảnh token (`_HIEN`,
  `_TAI_1`) hoặc giá trị khớp `^[A-Z][A-Z0-9_]*_[0-9]+$` do fallback sinh.
  Baseline ≈ 73 form (sẽ về 0 sau C4).
- **D9 nâng cấp**: bảng ≥10 cột: min col < 900 twips → hard; bảng <10 cột giữ
  sàn 567; xử lý lệch 566/567 (I4) bằng cách chốt sàn làm tròn xuống 566 cho
  legacy. Baseline ≈ 60 bảng / 10 form.

Việc: implement + `tools/test_phase6v_detectors.py` (positive + negative
mutations từng detector) + pin baseline ĐỎ bằng số liệu audit trong test
(detector chạy trên corpus sẵn có phải ra đúng số — chứng minh không chọn
số đẹp).

**Gate V1:** baseline ĐỎ khớp số liệu mục 1.2 (chênh lệch phải được giải
thích từng form); negative tests xanh; runner xanh (detector chỉ báo, chưa
chặn release tới V2 xong).

### V2 — Fix theo lớp gốc rễ (4 lane song song, merge TUẦN TỰ)

Thứ tự merge do Lead giữ: **C4 → C1 → C2 → C3** (fixture trước để giá trị
corpus thực tế trước khi chốt lại kỳ vọng detector; mỗi merge re-run V1
detector để rebaseline số).

- **C4 `agent/6v-fixture`:** nhánh default `ValueFactory.value()` sinh giá trị
  tiếng Việt thực + chỉ số nhúng theo họ key (địa chỉ → "Số N nhà 123, đường
  Kinh Dương Vương, phường 4, quận 8"); fallback `LABEL_HOA_N` bị XOÁ. Giữ
  tính phân biệt D12 bằng chỉ số duy nhất. Selftest fixtures cập nhật. D16
  phải về 0 sau C4.
- **C1 `agent/6v-glue`:** normalize skeleton trong pipeline regen: chèn space
  quanh mọi placeholder khi ngay trước/sau là ký tự word
  (`{key}` giữa "ngày"/"tháng"/"năm"/nhãn); xử lý cặp placeholder dính
  `{a}{b}` → separator chuẩn. Regen 55 form + drift-guard ×2 + allowlist diff
  + rebaseline census/policies/fixture. D13 → 0. Không sửa giá trị user có
  space có ý nghĩa (chỉ đụng skeleton template).
- **C2 `agent/6v-nameslot`:** pass phân loại chính xác 37 form (script từ
  audit làm nền, bắt buộc manual-confirm từng form) → 3 nhóm: (a) thiếu
  placeholder → engine extension "chèn placeholder vào slot" (mở rộng spec v1,
  tiền lệ đã ghi trong note PLI_M09) + regen; (b) form_maps thiếu tag → tag
  field đúng key sẵn có; (c) slot handwriting theo bản giấy → đưa vào
  `handwriting_only_slots` kèm ảnh nguồn. D14 → 0. Test mỗi form trong nhóm
  (a)/(b) có case dữ liệu thật in ra tên.
- **C3 `agent/6v-chk`:** theo Q-V1 (khởi động SAU owner chốt). Implement ô
  vuông + X: DOCX (bảng 1×1 không viền hoặc ☒ tùy chuẩn chốt — phải ra 1 glyph
  thống nhất toàn corpus) + UI control shape tương ứng + "X rơi dòng riêng"
  được phòng bằng keep-together. D15 → 0.

**Gate mỗi lane:** detector tương ứng ĐỎ→XANH trên corpus re-export; regen ×2
zero-diff; `auditor/6v-core` ký diff; `auditor/6v-visual` ký sample 10 form
(xử + nguyên vẹn). **Gate V2 tổng:** runner xanh; D13/D14/D16 = 0; D15 = 0
(nếu Q-V1 đã chốt); corpus mới evidence đầy đủ.

### V3 — Bảng rộng 10–15 cột (`agent/6v-tables`, sau Q-V2)

Phương án do owner chọn trong mục 6. Việc chung bất kể phương án: census 60
bảng rộng có `width_policy` đúng; header repeat + cantSplit đã có — giữ;
đo lại bằng D9 mới (≥900twips cho ≥10 cột) và bằng mắt auditor trên TOÀN BỘ
bảng rộng (không sample). Nếu owner chọn landscape-trang-bảng: mở section
orient trong generator chỉ cho trang chứa bảng, đối chiếu lại Word 16.16 mở
không lỗi + PDF page-size đúng.

**Gate V3:** D9 hard = 0 trên corpus; `auditor/6v-visual` verdict
"readable" từng bảng trong 60 bảng; số cột không đổi so với pháp định.

### V4 — Meticulousness sweep toàn 91 mẫu (`agent/6v-micro` + auditor/6v-visual)

Đây là vòng "chú ý những thứ nhỏ nhất" — quét census, không sampling:

1. **Census chi tiết nhỏ** (script mới `tools/census/6v_micro_census.py`):
   mọi khác biệt typography trong 91 template: kiểu dòng điền (…… vs ---- vs
   ____), độ dài gạch, dấu "…"/"..." lẫn lộn, space trước/sau ":" trong nhãn,
   khoảng trắng đôi, dấu ngoặc thiếu đóng/mở, superscript footnote đúng vị
   trí, cỡ chữ floor (≥8pt), viền bảng uniform, cell padding, header band
   trái/phải đúng căn.
2. **Chuẩn hóa một kiểu duy nhất** cho từng nhóm (chọn theo bản giấy gốc làm
   chuẩn; khác biệt có chủ đích phải nằm trong registry với lý do).
3. **Per-page reviewer_verdict 100%:** hoàn tất backlog 5R (647 candidate +
   toàn bộ trang) bằng auditor/6v-visual — mỗi trang có verdict và người ký.
4. **UI meticulousness** (phụ, 1 đợt nhỏ): label/input alignment, focus ring,
   aria-label nút thêm/xóa/duplicate, thông báo lỗi đồng/about, giữ nguyên
   trạng thái khi đổi form/variant (kế thừa checklist 5R Wave C).

**Gate V4:** micro-census 0 khác biệt không đăng ký; 100% trang có
reviewer_verdict; UI checklist PASS; runner xanh.

### V5 — Audit độc lập 3 tầng + checkpoint final

1. Re-export corpus full từ HEAD sạch (evidence mới, path
   `generated_ho_so/_visual_layout/phase6v/final/`).
2. `auditor/6v-export`: manifest == đĩa; determinism (export 2 lần hash
   giống); ZIP đúng nội dung; word-open loop 91/91 re-verify; concurrency
   test lặp lại.
3. `auditor/6v-visual`: verdict 91×5(+variants) theo checklist 5.2 trên
   corpus mới.
4. `auditor/6v-core`: diff toàn phase (V0→V5) — không có vá generated, không
   nới test, không allowlist vô lý.
5. `auditor/6v-release`: tái lập từ worktree sạch mọi con số checkpoint.
6. Lead viết checkpoint mới vào header PLAN này + `execution_ledger`; chỉ ký
   khi cả 4 auditor ≥ PASS-WITH-NOTES và mọi NOTE có owner-ack.

**Gate V5 (Definition of Done toàn cục):**

| # | Gate | Điều kiện PASS |
|---|---|---|
| G-A | Hạ tầng | 2 runner song song 2 PASS; PNG == manifest 100%; summary hai lớp trung thực |
| G-B | Detector | D1..D16 hard-fail = 0; candidates = 0 chưa adjudicate (mọi candidate có verdict) |
| G-C | Lỗi B1–B5 | D13/D14/D16 = 0; D15 = 0 (sau Q-V1); D9 hard = 0; bảng rộng verdict "readable" 60/60 |
| G-D | Evidence | corpus 6V tái lập được từ lệnh trong manifest; word-open 91/91; determinism PASS |
| G-E | Con người | 100% trang có reviewer_verdict; auditor core/visual/export/release ≥ PASS-WITH-NOTES |
| G-F | Sổ sách | defect/decision/ledger cập nhật; PLAN checkpoint mới; không debt ẩn |

---

## 5. Tiêu chí "tỉ mỉ" định lượng (checklist judge mọi trang)

### 5.1 Trang in (DOCX/PDF)

1. Không một cặp từ nào dính nhau ngoài chủ đích typography; label–value luôn
   có separator chuẩn.
2. Mọi slot điền: hoặc chứa dữ liệu, hoặc là "handwriting-only" đã đăng ký.
3. Tick = X trong ô vuông, cùng dòng với nhãn, đúng một option trong nhóm
   loại trừ.
4. Không token/mã kỹ thuật/mảnh token trong text; không placeholder `{...}`;
   không "X" rơi dòng.
5. Bảng: cột ≥ 900twips nếu ≥10 cột (hoặc phương án Q-V2); không chữ vỡ giữa
   token; header lặp khi sang trang; hàng không xé giữa dòng.
6. Dòng điền một kiểu toàn corpus; chấm dẫn (dot leader) đều.
7. Chữ ký: title + instruction + vùng viết ≥ 40pt cùng trang; orientation
   theo registry.
8. Trang trắng = 0; trang thưa phải có allowlist lý do.
9. Quốc hiệu/Số/Ngày (header band) đúng căn trái–phải, không viền lộ.
10. Footnote/superscript đúng vị trí, không orphan, không dính chữ.

### 5.2 UI (kế thừa + bổ sung)

- Không undefined/null/NaN/rác; control đúng semantics lẫn hình thức nguồn;
- validation mở đúng tab, focus đúng field, message dễ hiểu;
- 3 viewport + zoom 200% + keyboard-only không vỡ;
- không mất dữ liệu khi đổi form/variant/draft reload.

---

## 6. Quyết định owner (BLOCKED cho tới khi chốt — không agent được tự chọn)

| Mã | Câu hỏi | Đề xuất kèm bằng chứng | Cần trước phase |
|---|---|---|---|
| **Q-V1** | ✅ **ĐÃ CHỐT 2026-09-04**: ô vuông VẼ bằng viền + X bên trong (không phụ thuộc font glyph; Word 16.16 + LO giống nhau); không tick = ô trống; tick cùng dòng nhãn | Bảng 1×1 không viền + X: tương thích Word 16.16 tốt nhất, không phụ thuộc font glyph | V2-C3 — mở khoá |
| **Q-V2** | ✅ **ĐÃ CHỐT 2026-09-04**: landscape CHỈ trang chứa bảng ≥10 cột + sàn 900twips; số cột không đổi; policy portrait-section 5R bị supersede | (a) đọc được nhất; owner chấp nhận hồ sơ A4 không đồng nhất hướng để ưu tiên đọc được | V3 — mở khoá (sau C2 merge do chung file) |
| **Q-V3** | (hiện thực hóa theo V2-C2 đang chạy: thêm placeholder cho slot thiếu — C1 đã chuẩn space, C2 chèn key; xác nhận chính thức khi C2 merge) | Thêm placeholder ở (a)/(b) vì mục đích là form điền bằng máy; khác biệt bố cục không đổi cấu trúc pháp định | V2-C2 |
| **Q-V4** | (đã hiện thực hóa bởi C4 merged `a59c36e`: giá trị thực + chỉ số nhúng, D12 giữ nguyên 0 vi phạm) | Có — D16 vẫn bắt trùng giá trị nhờ chỉ số | V2-C4 — xong |
| **Q-V5** | 897 glue candidate WLAY-011 (553 cũ + 303 D13 mới + 41 liên hệ): adjudicate theo đợt auditor hay chốt 1 lượt? | 1 lượt trong V4 bởi auditor/6v-visual | V4 |
| **Q-V6** | Mở Windows/.exe packaging sau V5? | Chỉ khi G-A..G-F xanh | sau V5 |
| **Kế thừa** | Q-P4-1 min_rows nested-grid; WLAY-005 3 matrix M12 BLOCKED_OWNER; các câu hỏi M09 (mục 7, chân trang Mẫu 9) | giữ nguyên trạng thái OPEN trong registries | khi liên quan |

---

## 7. Trạng thái kế thừa từ v5 (chỉ giữ gì cần thiết cho 6V)

- **Gate release chuẩn:** runner `tools/release_runner.py` 57 suite — mọi
  suite mới của 6V PHẢI đăng ký vào đây (không chạy lẻ ngoài runner khi báo
  cáo release).
- **Corpus & baseline 5R:** `generated_ho_so/_visual_layout/phase5r_gate/`
  (final + baseline RED c9d095e) giữ nguyên làm lịch sử; corpus chuẩn của 6V
  là `phase6v/`.
- **WLAY:** 001–004, 006–010, 012 CLOSED; 005 PARTIAL (3 matrix M12 chờ
  owner); 011 OPEN-census (gộp vào Q-V5).
- **Bộ test trọng tài sẵn có:** `test_generator_deep_idempotency` (drift ID1/
  ID7), `audit_blocks_check`, exact-set `audit_expected_diff_files.txt`,
  `test_phase5r_*`, word-open loop (`phase5_word_open_loop.py`),
  coverage 111/111 drift=0.
- **Nguồn pháp lý:** TT 68/2025/TT-BTC; TT 121/2026/TT-BTC (HL 21-08-2026);
  NĐ 168/2025/NĐ-CP; NĐ 296/2026/NĐ-CP (HL 23-07-2026). Mẫu bị thay bởi
  TT 121: M01–M05, M10, M12, M27, M30 PL I; bỏ M11.
- **Excel/Windows:** Excel pilot M72 đã duyệt; rollout + Windows packaging
  nằm NGOÀI plan 6V, mở sau Q-V6.
- **Sự kiện môi trường 2026-09-04:** gate đỏ giả 56/1 do va chạm profile
  LibreOffice (worktree song song + lock/zombie); đã xử lý môi trường, HEAD
  `294604c` runner 57/0/0. Bản backup profile hỏng:
  `~/Library/Application Support/LibreOffice/4/user.wedged_20260904` (xoá
  khi V0 ổn định 1 tuần).

---

## 8. Sổ theo dõi & quy ước commit

- Commit message: `6V-<phase>(<lane>): <việc> — <bằng chứng ngắn>` (tiếng
  Việt không dấu, theo quán thế repo); mọi commit merge lane phải nhắc verdict
  auditor.
- `docs/defect_registry.md`: thêm dòng cho B1–B5, I1–I4 (status theo evidence
  audit 2026-09-04) ngay khi bắt đầu V0; cập nhật mỗi gate.
- `docs/audits/6v/`: mỗi auditor một thư mục phase (`v0-core.md`,
  `v2-visual-c1.md`, ...); format: verdict + findings + lệnh tái lập.
- Checkpoint cuối ghi vào header file này, thay thế dòng hiệu lực.
