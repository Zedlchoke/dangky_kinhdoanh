# v5-release-audit — auditor/6v-release (độc lập)

- **Ngày:** 2026-09-05
- **Base:** `de86570` (main, "docs(6V-V4final2): GATE DAT G-B TUYET DOI …"). Xác minh: `main` = `de865707975401cf71aedfa4e81e3021472789ec`, working tree repo chính sạch.
- **Worktree audit:** `../dangky_kinhdoanh-worktrees/6v-audit-release` (nhánh `6v-audit-release`, tạo bằng `git worktree add … -b 6v-audit-release de86570`). Read-only với main; sản phẩm duy nhất là file này (không commit, không đụng file tracked nào).
- **Môi trường tôi:** macOS arm64 (darwin 24.4.0) · Python 3.13.14 · node v24.5.0 · python-docx 1.2.0 · lxml 6.1.1 · pymupdf 1.28.2 · openpyxl 3.1.5 · soffice (/opt/homebrew/bin). Khớp pins trong `requirements-dev.txt` **trừ pymupdf — xem F4**.
- **Câu hỏi trọng tài (PLAN 3.2):** "Checkpoint này có đứng vững trên máy khác không?"

---

## 1. Tái lập từ worktree sạch — 3 lệnh bằng chứng + tái lập bổ sung

| # | Lệnh (chạy nguyên văn, cwd = worktree) | Kỳ vọng (ledger) | Kết quả tôi đo | Verdict |
|---|---|---|---|---|
| 1a | `python3 -X utf8 -m tools.release_runner --json /tmp/rel_runner.json` | 58 PASS / 0 FAIL / 0 NOT RUN | **58 PASS / 0 FAIL / 0 NOT RUN** (critical NOT RUN 0), `VERDICT: PASS`, exit 0. JSON ghi `summary: {pass:58, fail:0, not_run:0, verdict:PASS}`; 58 suite đăng ký đúng như tôi đếm trong `SUITES`. Chậm nhất: `test_phase5r_signatures` 160.3s, `test_p3_security` 78.5s | **KHỚP** |
| 1b | `python3 -X utf8 -m tools.test_phase6v_detectors` | 7/7 | **7 PASS / 0 FAIL / 0 SKIP**, exit 0 (V1a pin + V1b–V1g mutations) | **KHỚP** |
| 1c | `python3 -X utf8 -m tools.census.build_manifest --deep` | exit 0 | **exit 0**, `GATE PASS: 87/87, moi signature da classify, counts khop`. Không `--write` → không ghi gì (đúng docstring "read-only trừ --write") | **KHỚP** |
| 1d | 2× `release_runner --only test_phase5r_signatures` **song song** | 2 PASS (Gate V0a / Class I6) | cả hai **exit 0**, `VERDICT: PASS` | **KHỚP** |
| 1e | `node app_web/{test_dom,test_domain,test_form_flow,test_grid}.js` | ledger V4: dom 64/0, domain 65/0, form_flow 38/0; lịch sử grid 111/0 | 64/0, 65/0, 38/0, 111/0 | **KHỚP 4/4** |

`git status --short` worktree sau TOÀN BỘ phép chạy: **0 file dirty** (runner + manifest `--deep` không bẩn tree; guard #8 của `test_m72_activation` PASS cũng xác nhận điều này trong-run).

**Cách tiếp cận corpus cho 1b (trung thực phương pháp):** corpus `generated_ho_so/_visual_layout/phase6v/v0_corpuscheck` là gitignored, local-only, KHÔNG có trong worktree sạch. Tôi **không symlink, không copy** — đọc code `tools/test_phase6v_detectors.py:50-52,149-152,168`: test tự có fallback `MAIN_CHECKOUT` (repo chính). Nghĩa là: **detector code + `form_maps.json` lấy từ worktree (đúng state `de86570`)**, corpus đóng băng (455 record, render post-V0) lấy từ repo chính. Tôi xác minh độc lập corpus đó: 455 record, manifest claim 1644 trang == 1644 PNG trên đĩa. Đây là phép "apples-to-apples" đúng thiết kế (pin baseline ĐỎ V1 trên corpus v0 không đổi).

**V1a pin khớp nguyên trên corpus v0 (chạy live tại 1b):** D13 323 rec/1104 hit/77 form · D14 14/14/14 (65 form có slot) · D15 17 rec/191 hit (BARE_X_PARAGRAPH 130 + X_OWN_LINE 61) · D16 342/8751/82 (TOKEN_VALUE 2865 + TOKEN_FRAGMENT 5886) · D9 50/60/10 (toàn NARROW_COL_WIDE) — đúng bảng PIN trong test.

## 2. Đối chiếu sổ sách — từng dòng CLOSED mục 6V

### 2a. `docs/defect_registry.md` (Class 6V)

| Dòng | Claim (tóm tắt) | Tôi đo lại | Verdict |
|---|---|---|---|
| I1 ĐÃ ĐÓNG 6V-V0 | `_run_soffice` profile cách ly + retry; Gate V0(a) 2 runner song song 2 PASS; suite `test_export_concurrency` | tái lập 1d exit 0×2; suite `test_export_concurrency` PASS 35.3s trong runner | **KHỚP** |
| I2 ĐÃ ĐÓNG 6V-V0 | PNG per-variant + assert; "Corpuscheck V0: claim=disk=1644" | v0_corpuscheck: manifest 1644 == đĩa 1644 (tự đếm `rglob('*.png')`); v4b `png_disk_assert {claimed:1631, disk:1631, ok:true}` | **KHỚP** |
| I3 ĐÃ ĐÓNG 6V-V0 | corpuscheck V0 "CANDIDATES: 360 (D9=50, D6=159, D11=201, D5=78)" | summary.json v0: `candidate_total_records` 360; D9 50, D6 159, D11_glue 201, D5 78 | **KHỚP** (ghi chú F7 về `candidate_hits` 689) |
| I4 ĐÃ ĐÓNG 6V-V1 | sàn legacy làm tròn xuống 566; NARROW_COL legacy = 0 | mutation V1f case 566-8-cột PASS; V1a pin D9 chỉ có NARROW_COL_WIDE | **KHỚP** |
| I5 ĐÃ ĐÓNG 6V-V0 | suite `test_export_concurrency` chống hồi quy | PASS trong runner | **KHỚP** |
| I6 ĐÃ ĐÓNG 6V-V0 | pid suffix sandbox; Gate V0(a) song song | tái lập 1d | **KHỚP** |
| B1 (D13) | 323/1104/77 → 0 | pin khớp (mục 1b); v4b summary D13=0 | **KHỚP** |
| B2 (D14) | 14 form → 0 | pin khớp; v4b D14=0 | **KHỚP** |
| B3 (D15) | 191 hit (130+61) → 0 | pin khớp cả 2 code; v4b D15=0 | **KHỚP** |
| B4 (D16) | 355/8846 → grammar v2 342/8751 → 0 | pin 342/8751 khớp; v4b D16=0 | **KHỚP** |
| B5 (D9) | 60 bảng/10 form → 0 | pin khớp; v4b D9=0 | **KHỚP** |
| 6V-V4a (adjudicate) | D5 72 hit = 59(i)+7(ii)+6(iii); micro: a=1 thật, b=3+1FP census, c=0, d=31, e=14, f=53 chờ Q-V8, g=0 | v4_corpuscheck: 71 rec/72 hit D5 ✓; tally trùng nguyên văn `docs/audits/6v/v4-visual-audit.md` (59/7/6; 12/15 spot PASS) | **KHỚP** |
| 6V-V4b việc 1 | D5 6 hit (iii) fix → HARD 0 | v4b summary `hard_fail_hits` 0, `candidate_hits` 0, 0 export error | **KHỚP** |
| 6V-V4b việc 2 | width redistribution longest-word; 3 spot pages hết vỡ; **cột mã 13 chữ số CÒN vỡ — chờ owner** | claim "còn vỡ" được registry TỰ GHI (trung thực) — tôi không tái render để đo lại (NOT-RUN, xem mục 5) | **KHỚP (mức claim)** |
| 6V-V4b việc 3–7 | STT 14 form=0, ngoặc 3 form=0, separator 31=0, M12 dot, fixture ngày đủ + handwriting-only, selftest 437 | micro-census worktree: e=0, b=0, d=0, a=75, c=9, f=53, g=8 ✓; `phase5_fixtures_selftest` PASS trong runner | **KHỚP** |
| 6V-V4b việc 8 | census rebaseline b4→0, d31→0, e14→0 | `tools/census/6v_micro_census.json` @worktree: b=0, d=0, e=0 | **KHỚP** |
| 6V-V4b việc 9 | D5 allowlist nạp mặc định, candidate "chưa adjudicate" = 0 | `docs/phase6v_d5_sparse_allowlist.json`: count 59 (50 i + 9 ii), cơ chế `_d5_sparse_allowed`; v4b candidate 0 | **KHỚP** (ghi chú F8) |
| 6V-V4b việc 10 | "Mẫu số N" nguồn↔template 4/4, đăng ký per-form | bảng 4 form trong `decision_registry.md` có file nguồn + jc + vị trí | **KHỚP (mức đăng ký; không tái đối chiếu nguồn docx)** |

### 2b. `docs/execution_ledger.md` (Phase 6V, các checkpoint định lượng)

| Claim ledger | Tôi đo lại | Verdict |
|---|---|---|
| Runner 58/0/0 (dòng "Runner chính thức sau V2-final", V3, V2-B3, V4, V4b) | 58/0/0 VERDICT PASS (mục 1a) | **KHỚP** |
| V2-final: "D13→0, D16→0, D11 201→0; D14 14→13" | v2_corpuscheck summary: cand D9 50, D6 157, D5 68, **D14 13**, D15 17; D13/D16/D11 không còn trong candidate_counts | **KHỚP** |
| V3: "190/190 trang ngang đo 792×612" | `_lane_evidence/6v-tables/.../page_rect_report.json`: 190 rects, tất cả 792×612 | **KHỚP** |
| V3: "word-open 10/10 PASS_OPEN_DIRECT" | **KHÔNG tìm thấy file evidence** trong `phase6v/_lane_evidence/6v-tables/` (chỉ summary/manifest/page_rect) và trong cây phase6v (chỉ có inventory của lane 6v-chk) | **LỆCH — evidence không định vị được (F3)** |
| Gate V4-final @374ea29: 455r, 0 export err, PNG 1612/1612, HARD 0, CANDIDATES 71 (D5 72 hit) | v4_corpuscheck: 455 rec, đĩa 1612==1612, hard 0, `candidate_total_records` 71 / `candidate_hits` 72 toàn D5, 0 export err | **KHỚP** |
| Gate V4-final-2 (v4b_corpuscheck): exit 0, 455r, 0 export err, HARD 0, CANDIDATES 0, PNG 1631/1631 — "G-B đạt" | v4b_corpuscheck: tất cả 14 key detector = 0, hard 0, cand 0, 0 err, 1631==1631 | **KHỚP** |
| "auditor/6v-core (report `docs/audits/6v/v2-core-audit.md`)" | file **KHÔNG tồn tại** trong repo @de86570 (`docs/audits/6v/` chỉ có `v4-visual-audit.md`) | **LỆCH (F5)** |
| "test_phase6v_detectors KHÔNG đăng ký runner (corpus gitignored)" | 58 suite không có suite này; test tự SKIP khi thiếu corpus (không SKIP trên máy tôi) | **KHỚP (thiết kế)** |
| policies min_col 954/918/909/928 (dòng 9dad012) | 4 giá trị đều có trong `tools/phase5r_table_policies.json` | **KHỚP** |
| Word corrupt Class 16 "mitigated at export layer" (5R/P-owner) | ngoài phạm vi đo trực tiếp của tôi (cần Word GUI) | NOT-RUN |

**Kết luận mục 2:** mọi số liệu định lượng CLOSED của 6V mà tôi tái lập được đều **KHỚP** — 0 lệch số. 2 lệch thuộc loại **evidence/kho lưu trữ** (F3, F5), không phải sai số.

## 3. Gate V5 (Definition of Done) — chấm bằng bằng chứng thực tế

| Gate | Verdict | Bằng chứng |
|---|---|---|
| **G-A** Hạ tầng | **PASS** | (1) 2 runner song song 2 PASS — tôi tái lập (1d); (2) PNG == manifest 100% — tôi tự đếm trên cả 3 corpus: v0 1644/1644, v4 1612/1612, v4b 1631/1631; (3) summary hai lớp trung thực — summary.json có `hard_fail_counts` + `candidate_counts` + `candidate_ids`; v0 hiển thị CANDIDATES 360 dù HARD 0 (không che) |
| **G-B** Detector | **PASS** | v4b summary: 14/14 detector = 0, `hard_fail_hits` 0, `candidate_hits` 0, 0 export error trên 455 record. Candidate cuối cùng (D5 72) đã adjudicate 59+7 qua allowlist + 6 fix (việc 1). Ghi chú: "D1..D16" là cách nói gộp — tập detector thực tế D1–D6, D9–D16 (không có D7/D8) |
| **G-C** Lỗi B1–B5 | **PASS-WITH-NOTES** | D13/D14/D16 = 0 ✓; D15 = 0 sau Q-V1 ✓; D9 hard = 0 ✓ (tất cả đo trên corpus v4b + pin V1a). Notes: (a) điều kiện "bảng rộng verdict 'readable' 60/60" **chưa có artifact per-bảng được ký**; (b) chính registry V4b tự ghi còn 1 lớp vỡ token cột mã 13 chữ số (M09 14 cột, M72 tnhh 8 cột portrait) chờ owner — nghĩa là "readable" chưa tuyệt đối trên mọi cột |
| **G-D** Evidence | **PARTIAL — CHƯA ĐẠT** | Đạt: corpus có hash (`docx_hash`/`pdf_hash`/`template_hash`), `png_disk_assert` ok, tôi xác minh manifest==đĩa 3/3 corpus; generator determinism (idempotency 17/0 trong runner). Chưa đạt: **word-open 91/91** — bằng chứng duy nhất là của 5R (`phase5r_gate/final/word_open_inventory.json`, 91 record, template PRE-6V); corpus 6V ghi `word_open_verdict: NOT RUN` 455/455; **determinism export 2 lần hash giống** — NOT-RUN (thuộc auditor/6v-export); PLAN V5.1 yêu cầu corpus re-export từ HEAD sạch vào `phase6v/final/` — thư mục chưa tồn tại (F6) |
| **G-E** Con người | **CHƯA ĐẠT** | Điều kiện "100% trang có reviewer_verdict": corpus cuối v4b ghi `reviewer_verdict: NOT_REVIEWED` **455/455** (v4-visual-audit đã NOT-RUN phần này một cách trung thực). Điều kiện "auditor core/visual/export/release ≥ PASS-WITH-NOTES": visual ✓ PASS-WITH-NOTES; release = report này; **core v2 không có trong repo (F5); export chưa chạy** |
| **G-F** Sổ sách | **PASS-WITH-NOTES** | defect/decision/ledger cập nhật đến V4b, mọi số tôi đối chiếu khớp (mục 2); debt đều ghi minh bạch. Note: checkpoint mới **chưa ghi vào header PLAN.md** (mục 8 PLAN) — đúng trình tự V5.6 (chờ auditor ký), là việc còn lại chứ không phải sai lệch |

Lưu ý đặt tên: đề bài nhắc "GATE 10/10 (G-A..G-F)" — PLAN v6 định nghĩa **6 gate** G-A..G-F; bảng G1–G10 là của Wave F/P5R (phase trước). Tôi chấm đủ 6 gate.

## 4. TODO-nước-đục — chỗ docs nói mạnh hơn cái tôi đo được

- **F1 (quan trọng nhất) — "V4 ĐÓNG" (ledger dòng cuối V4b + commit message de86570) rộng hơn Gate V4 của PLAN.** PLAN định nghĩa Gate V4 = 4 điều kiện: micro-census 0 khác biệt không đăng ký; **100% trang có reviewer_verdict**; **UI checklist PASS**; runner xanh. Tại `de86570`: (a) reviewer_verdict NOT_REVIEWED 455/455; (b) micro-census nhóm a=75 form fill-line "registry per-family **chờ owner đối chiếu bản gốc**" — tức khác biệt chưa đăng ký hết; (c) UI meticulousness mới có "+28 key FIELD_META hint" — chưa có sweep 5.2 đầy đủ trong evidence; chỉ điều kiện runner xanh (+ detector 0/0) là thỏa. Câu "Tất cả detector D1–D16 = 0 hard + 0 candidate" thì **đúng**. Đề xuất phát ngôn: "V4 ĐÓNG (scope detector/G-B) — Gate V4 PLAN còn 3 điều kiện", tránh để người đọc sau suy ra G-E đã xong.
- **F2 — reviewer_verdict 100% chưa ai ký trên corpus cuối (455 NOT_REVIEWED).** Cùng gốc F1; là việc của auditor/6v-visual vòng V5 trên corpus mới (đúng danh sách việc PLAN V5.3). Nói rõ ở checkpoint để owner không duyệt nhầm.
- **F3 — word-open là bằng chứng cũ.** Corpus 6V ghi `word_open_verdict: NOT RUN` toàn bộ 455; bằng chứng 91/91 duy nhất là 5R trên template **pre-6V** (template đã thay rất nhiều: landscape, chk viền w:bdr, name-slot, width floors); claim V3 "word-open 10/10 PASS_OPEN_DIRECT" **không tìm thấy file evidence** trong `_lane_evidence/6v-tables/` (có thể nằm ở worktree lane đã dọn hoặc /tmp). Đây là vi phạm tinh thần quy tắc PLAN 0.3 ("evidence không khớp đĩa = evidence THẤT BẠI") ở mức ghi nhận — số không bị nghi, nhưng không tái lập được từ cây evidence hiện có.
- **F4 — `requirements-dev.txt` tự mô tả "reproducible" nhưng thiếu pymupdf.** 6 tool import pymupdf, trong đó ≥3 suite runner: `test_phase5_visual_detectors` (critical), `test_phase5r_signatures`, `test_phase5r_metadata`, cộng `test_phase6v_detectors` và gate visual. Máy khác cài đúng file này sẽ **đỏ runner (FAIL loud, không silent)** — an toàn, nhưng không tái lập được "58/0/0" chỉ với dependency contract. Pin `pymupdf==1.28.2` (version đã chạy xanh trên máy này).
- **F5 — `docs/audits/6v/v2-core-audit.md` được ledger tham chiếu nhưng không có trong repo @de86570** (`docs/audits/6v/` chỉ có `v4-visual-audit.md`). Commit report auditor core; khi có thêm export/release thì G-E mới có đủ chữ ký.
- **F6 — PLAN V5.1 quy định re-export corpus từ HEAD sạch vào `phase6v/final/`** — thư mục chưa tồn tại; corpus cuối `v4b_corpuscheck` render trên repo chính (không chứng minh được retroactively rằng tree当时 sạch). Việc này thuộc vòng V5 (Lead + auditor/6v-export), không phải sai sót đã ghi sai.
- **F7 (minor, lịch sử) — summary v0: `candidate_hits` 689 ≠ tổng per-detector 488** (50+159+201+78); 689 = 488 + 201, tức D11 bị đếm hai lần qua 2 key `D11_glue` và `D11_glue_count`. Đã supersede (v4b candidates=0) nhưng nếu tái sử dụng summary thì sửa cách cộng.
- **F8 (minor, dễ đọc nhầm) — allowlist D5 `count: 59` (50 i + 9 ii, đo trên corpus v4b)** khác tally của v4-visual-audit "59(i)+7(ii)" (đo trên corpus v4). File đã giải thích trong `source_adjudication`, nhưng hai bộ số dùng cùng nhãn (i)/(ii) trên hai corpus khác nhau — nên thêm 1 dòng cảnh báo ở đầu file.
- **F9 (minor, ngôn ngữ) — "D1–D16"**: tập detector thực tế là D1–D6, D9–D16 (summary không có D7/D8). Không sai số liệu, chỉ là nhãn gộp.

## 5. NOT-RUN kèm lý do (không đoán)

| Mục | Lý do |
|---|---|
| Windows smoke S1–S8 / .exe packaging | Không có máy Windows — trùng NOT RUN đã ghi trong ledger (`platform_smoke_checklist.md` "CHƯA TỪNG CHẠY") |
| Word-open re-verify trên template hiện hành (6V) | Cần tự động hóa Word GUI (P8a đã cấp quyền nhưng việc này thuộc auditor/6v-export vòng V5); tôi chỉ đọc lại inventory có sẵn và nhận thấy nó stale (F3) |
| Determinism export 2 lần hash giống / ZIP integrity end-to-end | Thuộc auditor/6v-export (PLAN V5.2); yêu cầu chạy export thật, ngoài 3 lệnh nhiệm vụ của auditor release |
| Tái render để đo lại "cột mã 13 chữ số còn vỡ" (V4b việc 2) | Yêu cầu export + LO; tôi chấp nhận claim ở mức registry tự ghi là còn mở (trung thực) — không tái xác minh bằng ảnh |
| Đối chiếu từng số `v2_corpuscheck`/`v3_corpuscheck` | Corpus trung gian đã supersede; tôi chỉ spot-check các con số được ledger trích (D14 13, D6 157, D5 68) — khớp |
| Đối chiếu bản giấy gốc TT 68/121 | Bản gốc không có trong repo; chỉ đối chiếu được qua registries nội bộ (giống giới hạn mà v4-visual-audit đã khai) |

## 6. OVERALL + khuyến nghị Q-V6

**OVERALL: PASS-WITH-NOTES** cho câu hỏi trọng tài của auditor này — *checkpoint `de86570` tái lập được từ worktree sạch*: cả 3 lệnh bằng chứng chạy đúng số liệu ledger (58/0/0 · 7/7 · exit 0/87/87), repro song song 2 PASS, 4 suite node khớp số assertion nội bộ, mọi con số định lượng CLOSED của 6V tôi đối chiếu đều khớp (0 lệch số), corpus evidence tự nhất quán (manifest==đĩa 3/3). Gate: **G-A PASS · G-B PASS · G-C PASS-WITH-NOTES · G-D PARTIAL · G-E CHƯA ĐẠT · G-F PASS-WITH-NOTES.**

**Q-V6 (mở Windows/.exe packaging):** theo chữ PLAN ("Chỉ khi G-A..G-F xanh") → **CHƯA MỞ — CHẶN CÓ ĐIỀU KIỆN**. Checkpoint không hề thiếu tin cậy về mặt tôi kiểm tra (G-A/B/C xanh, tái lập được 100%), nhưng G-D (word-open re-verify trên template 6V + determinism export) và G-E (reviewer_verdict 100% + đủ chữ ký 4 auditor) chưa xanh. 5 việc mở khóa — đều không đụng production code:

1. Lead + auditor/6v-export chạy vòng V5: re-export corpus từ HEAD sạch vào `phase6v/final/` (PLAN V5.1), determinism export 2 lần, ZIP integrity, **word-open 91/91 re-verify trên template hiện hành** (F3/F6).
2. auditor/6v-visual ký `reviewer_verdict` 100% trên corpus V5 (F2).
3. Commit `docs/audits/6v/v2-core-audit.md` vào repo (F5).
4. Pin `pymupdf` trong `requirements-dev.txt` (F4).
5. Lead ghi checkpoint V5 vào header PLAN.md + ledger sau khi 4 auditor ký (G-F note).

Sau 5 việc trên, G-A..G-F đủ điều kiện xanh và Q-V6 không còn chặn nội bộ (máy/VM Windows của owner — P8b — vẫn là điều kiện độc lập thuộc về owner).

## 7. Lệnh tái lập (nguyên văn, cwd = worktree `6v-audit-release` @ de86570)

```bash
git -C /Users/hoangminhlong/orca/dangky_kinhdoanh worktree add \
  /Users/hoangminhlong/orca/dangky_kinhdoanh-worktrees/6v-audit-release \
  -b 6v-audit-release de86570
cd /Users/hoangminhlong/orca/dangky_kinhdoanh-worktrees/6v-audit-release

python3 -X utf8 -m tools.release_runner --json /tmp/rel_runner.json        # 58/0/0 VERDICT PASS
python3 -X utf8 -m tools.test_phase6v_detectors                            # 7 PASS / 0 FAIL / 0 SKIP
python3 -X utf8 -m tools.census.build_manifest --deep                      # exit 0, GATE PASS 87/87

# G-A repro: 2 runner song song
python3 -X utf8 -m tools.release_runner --only test_phase5r_signatures \
  --json /tmp/rel_par_A.json & \
python3 -X utf8 -m tools.release_runner --only test_phase5r_signatures \
  --json /tmp/rel_par_B.json & wait                                        # 2× exit 0

# Corpus đĩa == manifest (đọc-only tại repo chính)
python3 - <<'EOF'
import json
from pathlib import Path
for d in ('v0_corpuscheck','v4_corpuscheck','v4b_corpuscheck'):
    b = Path('/Users/hoangminhlong/orca/dangky_kinhdoanh/generated_ho_so/_visual_layout/phase6v')/d
    m = json.load(open(b/'manifest.json', encoding='utf-8'))['records']
    claimed = sum(len(r['pages']) if isinstance(r.get('pages'), list) else int(r.get('pages') or 0) for r in m)
    print(d, len(m), 'rec | claimed', claimed, '| disk', len(list(b.rglob('*.png'))))
EOF

# Số assertion nội bộ
node app_web/test_dom.js; node app_web/test_domain.js        # 64/0, 65/0
node app_web/test_form_flow.js; node app_web/test_grid.js    # 38/0, 111/0
```

*(Auditor: auditor/6v-release — spawn fresh, không dùng context chung với executor, không commit. Bằng chứng chạy: `/tmp/rel_runner.json`, `/tmp/rel_par_A.json`, `/tmp/rel_par_B.json`, `/tmp/rel_manifest_deep.log`.)*
