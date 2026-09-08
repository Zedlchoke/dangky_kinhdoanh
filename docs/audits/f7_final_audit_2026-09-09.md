# F7 — FINAL INDEPENDENT AUDIT (READ-ONLY) — 2026-09-09

- **Auditor:** độc lập (F7), fresh worktree, không đụng file production.
- **BASE:** `44f21bc` · **HEAD:** `be69ca9` (`main` @ audit time) · **Range:** `44f21bc..HEAD` = **129 commits**, 283 files, +48 064 / −6 522.
- **Worktree audit:** `/Users/hoangminhlong/orca/dangky_kinhdoanh-worktrees/f7-auditor` (branch `auditor/f7-final`, từ HEAD).
- **PUSH STATUS:** `main` local **ahead origin/main 297 commits** (origin/main = `6ae63c2`) — wave **CHƯA push**, khớp chỉ thị owner "Không push (chờ lệnh owner)". Nhánh auditor không có upstream, auditor không push.
- **Phương pháp:** mọi gate chạy lại độc lập trong worktree f7-auditor (checkout byte-identical HEAD); production chỉ đọc.

---

## 1. VERDICT TỔNG

## **PASS-WITH-NOTES**

0 BLOCKER · 0 MAJOR · 6 NOTE (F7-N1..N6, tất cả là vệ sinh tài liệu/rủi ro đã ghi nhận, không ảnh hưởng đúng đắn production). Toàn bộ 13 gate yêu cầu + `release_runner` 65/65 chạy lại bởi auditor: **PASS hết, exit 0**.

---

## 2. DIFF REVIEW (ownership / assertion / test / push)

**Phạm vi:** F0L (current-law migration TT121/2026 + NĐ296/2026) → F1/F2/F4 → F3/F3H/F3T → F5 → dfix → allowlist.

1. **Ownership generated — VERIFIED.** Auditor chạy lại pipeline generator đủ 4 bước trong worktree:
   `build_form_maps` → `docx_to_blocks` → `tag_m72_sections` → `docx_to_blocks`, lặp ×2.
   Kết quả: `app/templates/**` + `app/data/blocks/**` + `app/data/form_maps.{json,js}` **zero-diff so HEAD**. Lưu ý kỹ thuật: chạy thiếu bước 3 (tagger M72) sẽ thấy `PLI_M72.{json,docx}` lệch (mất `cond` loại-hình) — đây là pipeline 4-bước có chủ đích (commit `6256c76`); bước 3 ghi lại 16 marker, verify PASS. File `PLI_M72.docx` sau regen khác HEAD chỉ ở **zip container metadata** — so sha256 từng member zip: `word/document.xml` identical (`a066a272…`), **0 member khác content** (đúng bài học đã ghi trong `test_generator_deep_idempotency.py`: python-docx save() chỉ đổi timestamp). Kết luận: mọi artifact generated tại HEAD tái sinh được từ nguồn + spec đã commit.
2. **Không file test nào bị xóa** (`--diff-filter=D` rỗng; không rename).
3. **Không hạ assertion.** Test diff: **+635 dòng assert / −42 dòng assert**; 9 file có removed assert, 8/9 file added ≥ removed; file duy nhất net −2 (`test_m0304_tails`) được kiểm chứng theo từng cụm: các assert bị bỏ là hợp đồng cấu trúc **luật cũ** (câu hỏi CSHHL '□ Có/□ Không', M04 '1.6' chưa sửa) thay bằng assert cấu trúc **luật mới** (TT121/2026: câu hỏi cũ PHẢI MẮT, dòng khai Mẫu số 10 PHẢI CÓ) — premise→evidence có comment, không phải weaken.
4. **dfix không fake pass / không bỏ check:** `d70fe14..HEAD` chỉ đụng `tools/row_placement.py`, `tools/header_semantics.py`, `tools/test_phase6v_detectors.py` (+111 dòng mutation), allowlist, docs. D18 thêm 2 guard false-positive lớp PDF (footnote guard + STT anchor), mutation giữ true-positive ĐỎ; D19 đổi hợp đồng lớp PDF sang so **band-vs-thân IN-DOCUMENT** (khớp D17 đã PASS 450/450) — lớp DOCX structural authoritative giữ nguyên. Corpus render không đổi → evidence corpus tại HEAD còn giá trị.
5. **Secrets/PII:** 0 hit `api_key|apikey|secret|password|passwd|private key|aws|ghp_|sk-proj-` trên toàn diff. 467 match "token" đều là ngữ nghĩa typography (token chữ khi render). Số serial dài trong diff (079085001234, 0312345678, 0901234567…) là fixture giả lập rành rành (chuỗi 1234/12345678).
6. **Allowlist H7 có kỷ luật:** `docs/phase6v_d5_sparse_allowlist.json` = **77 entry** (62 class (i) + 15 class (ii)), count khớp; mỗi lần thêm đều là commit riêng `chore(allowlist)` kèm evidence lane.

---

## 3. GATES ĐỘC LẬP — chạy lại bởi auditor (worktree f7-auditor)

| # | Gate | Exit | Kết quả | Kỳ vọng | Verdict |
|---|---|---|---|---|---|
| 1 | `python3 -X utf8 -m tools.release_runner --json /tmp/f7_runner.json` | **0** | **VERDICT: PASS — 65 PASS / 0 FAIL / 0 NOT RUN (critical 0)** | PASS | ✅ |
| 2 | `tools.census.build_manifest --deep` | **0** | GATE PASS **87/87** signature classify, counts khớp; sections_total **111**; unclassified 0 | PASS | ✅ |
| 3 | `tools.census.table_coverage_audit --no-write` | **0** | **GATE PASS — no drift**; sections 111 = 85 IV + 7 NO_TABLE + 1 REMOVED_BY_SOURCE_CLEANUP + 1 REMOVED_BY_CURRENT_LAW + 17 OUTPUT_ONLY; forms 87 | 111/111 drift 0 | ✅ |
| 4 | `node app_web/test_audit_wave_h_negative.js` | **0** | **57 PASS / 0 FAIL** (H7.4: diff ≡ manifest, 479 file) | allowlist sạch | ✅ |
| 5 | `tools.test_current_law_catalog` | **0** | **5/5 OK** | 5/5 | ✅ |
| 6 | `tools.test_current_law_migration` | **0** | **14/14 OK** | 14/14 | ✅ |
| 7 | `tools.test_phase6v_detectors` | **0** | **22 PASS / 0 FAIL / 0 SKIP** (mutation V3a-c + V4a-f + 2 case dfix) | 20+/20 | ✅ |
| 8 | `tools.test_row_contract_export` | **0** | **14 PASS / 0 FAIL** (pin matrix (4,0)/(4,1)/(4,4)/(4,6)/(5,2)/(0,3)) | 14/14 | ✅ |
| 9 | `tools.test_row_placement_anchors` | **0** | **2 PASS / 0 FAIL** (8 form production + PLI_M72 5 variant) | 2/2 | ✅ |
| 10 | `node app_web/test_f3t_parity.js` | **0** | **156 PASS / 0 FAIL** (13 anchor × 6 scenario) | 156/156 | ✅ |
| 11 | `node app_web/test_nv1_nv2_band_input.js` | **0** | **14 PASS / 0 FAIL** | 14/14 | ✅ |
| 12 | `tools.test_questionnaire` | **0** | **21 PASS / 0 FAIL** | 21/21 | ✅ |
| 13 | `tools.test_excel_roundtrip` | **0** | **9 PASS / 0 FAIL** | 9/9 | ✅ |

Sau runner + regen, `git status --porcelain` worktree = **rỗng** (gates không làm bẩn tree).

---

## 4. COVERAGE (111/111, drift 0)

- `table_coverage_audit --no-write` (exit 0): **111/111 sections classified, drift 0**; manifest statuses khớp (already_complete 82, no_table 7, partial_columns 4, removed_by_source_cleanup 1, output_only 17).
- `build_manifest --deep`: 87/87 form signature classified, unclassified 0; BLOCKED_LEGAL_REVIEW 33 form là nhãn quy trình hợp lệ, không chặn gate census.

---

## 5. CORPUS EVIDENCE — `docs/audits/f3v2_final_corpus_2026-09-08.{json,md}`

Render `phase8g_v2` từ HEAD sạch `d70fe14` (74 files merge không conflict); các commit sau corpus (`97cdea1..be69ca9`) chỉ đụng detector/test/allowlist/docs — evidence **có giá trị tại HEAD**.

| Hạng mục | Bằng chứng | Verdict |
|---|---|---|
| **HARD** | run1 d70fe14: 33 (D18 ×10 footnote-as-STT + D19 ×23 feed merged last-write-wins PLI_M79) → **dfix sửa đúng root cause đã adjudicate, re-run FULL gate phase8g_v2: HARD-FAIL 0 / 450 record, exit 0** | ✅ **HARD 0** |
| **Candidate** | còn **5** — D9 ×5 PLI_M10 NARROW_COL_WIDE adjudicate **(ii) pixel-OK total 14400** (min col 614); D5 ×2 đã allowlist `[f3v2-final]` → **candidate 0 unresolved** | ✅ |
| **Determinism** | PASS — 450/450 key `fixture\|tag\|form`, **sha256(word/document.xml) equal 450/450**, png list mismatch 0; rerun chạy trọn 5/5 fixture; detector VÀ allowlist đều deterministic | ✅ |
| Signature census | 450 = 450 clusters, coverage 100%, min gap **72.9pt** (sàn 72), median 100.5, below-72 = 0 | ✅ |
| ZIP / Word / PNG==đĩa | 450/450 testzip OK; Word 16.16.27 open-direct **90/90**; PNG 1737 = disk (cả 2 run) | ✅ |
| Preflight | release_runner 65/65 PASS, env_errors=[] | ✅ |
| Fix verified trên render | N-only: D5 BLANK 0; band label removal: BAND_LABEL_PRESENT 0; choice 1/nhóm: D15 0 FAIL/90 record; M05 token năm; M72 ctcp fragment hết; D17/D13/D14/D16 = 0 | ✅ |

---

## 6. REGISTRIES

| Tài liệu | Trạng thái | Ghi chú |
|---|---|---|
| `PLAN.md` | ✅ nhất quán | Checkpoint F3H+F3T ✅ (max(K,N) + D18 + D19 + render-fix + fixture; parity 156/0; corpus mới phase8g); ghi rõ Windows S1–S8 **NOT RUN (O6)**, "Không push (chờ lệnh owner)" |
| `docs/execution_ledger.md` | ⚠️ **STALE** (F7-N1) | Ghi đến Wave F1/F2/F4; **thiếu wave F3/F3H/F3T/F5/dfix/F7** — lịch sử chỉ nằm ở commit messages + evidence docs |
| `docs/defect_registry.md` | ⚠️ **F3T-1 stale** (F7-N2) | Heading vẫn `[OPEN 2026-09-08]` dù F3T đã đóng đủ 4 điều kiện tự đề ra (inventory census + mutation production-like 14/14 + parity 156/156 + corpus HARD 0) và PLAN ✅. Không có mục đóng. Defect 011 (label/value glue census) OPEN là hợp lệ — không mâu thuẫn HARD 0 |

---

## 7. VERDICT TỪNG GATE G0–G10

*(ánh xạ G0–G10 theo phạm vi audit F7; định nghĩa ghi rõ để report tự chứa)*

| Gate | Nội dung | Verdict |
|---|---|---|
| **G0** | Worktree/diff review: ownership generated, không xóa test, không hạ assertion, không push | **PASS** |
| **G1** | `release_runner` toàn suite (65 suite) | **PASS** (exit 0) |
| **G2** | Census manifest deep 87/87 | **PASS** (exit 0) |
| **G3** | Coverage 111/111 drift 0 | **PASS** (exit 0) |
| **G4** | H7 negative/allowlist (diff ≡ manifest) | **PASS** (57/0) |
| **G5** | Current-law catalog + migration (L-2026) | **PASS** (5/5, 14/14) |
| **G6** | Detectors + mutation (D1–D19) | **PASS** (22/0) |
| **G7** | Row contract + placement anchors + parity UI↔DOCX↔PDF | **PASS** (14/0, 2/0, 156/0) |
| **G8** | UI band input + questionnaire + Excel roundtrip | **PASS** (14/0, 21/0, 9/0) |
| **G9** | Corpus evidence: HARD 0, candidate 0 unresolved, determinism, ZIP/Word/census/PNG | **PASS** |
| **G10** | Secret/privacy + registry hygiene + push state | **PASS-WITH-NOTES** (secrets sạch, chưa push đúng lệnh; ledger/defect registry stale → F7-N1/N2) |

---

## 8. FINDINGS (notes — không chặn)

- **F7-N1 (MINOR, docs):** `docs/execution_ledger.md` thiếu wave F3 (phase8f/phase8g), F3H, F3T, F5, dfix, F7. Bằng chứng thực thi nằm rải trong commit messages + `docs/audits/*`; ledger cần 1 mục gộp để packet release tự chứa.
- **F7-N2 (MINOR, docs):** `docs/defect_registry.md` Class F3T-1 vẫn `[OPEN]` không mục đóng — mâu thuẫn với PLAN checkpoint ✅ và bằng chứng gates. Cần 1 dòng CLOSED kèm evidence (mutation 14/14, parity 156/156, corpus D5 BLANK=0 / D18 DOCX 0 hit).
- **F7-N3 (TRIVIAL, tool):** `tools/census/table_coverage_audit.py` dòng 1774 in `"wrote …"` **vô điều kiện** kể cả khi `--no-write` đã bỏ qua ghi (đã xác minh git status sạch sau chạy) — log gây hiểu nhầm, không sai chức năng.
- **F7-N4 (đã ghi nhận, chấp nhận có document):** dfix D18-lớp-PDF: chuỗi số không tìm thấy anchor 'STT' giờ bị bỏ qua ở mức NOTE (không HARD) — chấp nhận được vì lớp DOCX structural authoritative 0 hit toàn corpus; hằng heuristic mới (`PDF_STT_ANCHOR_DX=20pt`, footnote predicate) chưa đo phân bố rộng ngoài corpus hiện có. Đã ghi trong `risks_for_lead` của evidence.
- **F7-N5 (đã ghi nhận):** `phase5_visual_gate.py` default `--forms all` chưa lọc `current_law_status` (PLI_M11) — corpus chạy với `--forms 86 id` truyền tay. Cần lọc tại nguồn để tránh human error lần sau.
- **F7-N6 (outstanding đúng trạng thái):** D9 ×5 PLI_M10 hết vĩnh viễn cần nới policy D9 cho form có width-override per-form (chờ Lead quyết); Windows S1–S8 (O6) và human review (O5) vẫn NOT RUN — không được tính vào verdict kỹ thuật này.

## 9. RISKS / KHUYẾN NGHỊ

1. Cập nhật ledger + defect registry (F7-N1/N2) trước khi phát hành — 30 phút, không đụng production code.
2. Sửa print `--no-write` (F7-N3) và lọc `current_law_status` trong gate default (F7-N5).
3. Giữ nguyên trạng thái chưa-push; push chỉ theo lệnh owner (đang ahead 297).
4. Khi chạy corpus lần tới: dùng pipeline regen đủ 4 bước (có `tag_m72_sections`) — thiếu bước này sẽ chẩn đoán nhầm PLI_M72 lệch generator.

## 10. TÓM TẮT THỰC THI AUDITOR

- Tạo worktree `../dangky_kinhdoanh-worktrees/f7-auditor` (branch `auditor/f7-final` từ HEAD `be69ca9`); production chỉ đọc, `git status` production sạch trước/sau.
- 13/13 gate yêu cầu + regen ×2 + runner 65/65 chạy lại độc lập, đủ exit code ghi ở mục 3; artifact audit `/tmp/f7_runner.json`, `/tmp/f7_runner_stdout.txt`.
- Commit duy nhất trên worktree: báo cáo này. **Không push.**
