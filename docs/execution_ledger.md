# Execution ledger — master plan R0→R7 (checkpoint d882793)

> Sổ cái điều phối. Lead cập nhật sau mỗi wave; mỗi dòng là một task có
> owner + branch + ownership + gate + commit + evidence. Không báo hoàn tất
> theo phần trăm — chỉ theo gate PASS/FAIL/NOT RUN.

Quy ước worktree lane: `../dangky_kinhdoanh-worktrees/<lane>` ngoài repo chính.
Ownership độc quyền theo wave: `app.js`, `form-domain.js`, `render.js`,
`style.css`, `docx_to_blocks.py`, `build_form_maps.py`, `docx_render.py`.

## R0 — Baseline, scope registry, decision queue

| Task | Owner | Branch/Worktree | File ownership | Dependency | Gate | Commit | Test evidence | Blocker |
|---|---|---|---|---|---|---|---|---|
| Đọc PLAN.md + 5 docs, audit git (HEAD d882793, ahead 8/behind 0, 1 worktree) | Lead | main | — | — | baseline tái lập | — | git status sạch trừ PLAN.md | — |
| Commit master plan PLAN.md | Lead | main | docs only | — | diff đúng 437 insertions | `208de0e` | git diff --stat | — |
| Backup tag baseline | Lead | main | — | — | tag tại d882793 | tag `baseline/p1.2-d882793` | git tag -l | — |
| Triage `p1_c_verify_plii_m02.py` FAIL (4 mâu thuẫn match_heading) | Lead | main | tools/census/p1_c_verify_plii_m02.py | — | production không đổi; verifier so hành vi + negative selftest | `1caabd5` | verifier PASS exit 0 | — |
| Release test runner chính thức (29 suite, PASS/FAIL/NOT RUN, exit thật) | Lead | main | tools/release_runner.py | node, python-docx | verdict tổng đúng ngữ nghĩa NOT-RUN-critical=FAIL | `e6b9226` | runner VERDICT PASS 29/29 | — |
| Dependency contract dev/test | Lead | main | requirements-dev.txt | pip | pin python-docx==1.2.0, lxml==6.1.1; pywebview ghi rõ chờ R6 | `e6b9226` | runner preflight deps | pywebview chưa cài máy dev |
| Sync allowlist H7 (3 file R0) theo quy ước lane B P1.2 | Lead | main | app_web/test_audit_wave_h_negative.js | commit runner trước | H7.4 đúng tập EXPECTED | `c287562` | suite 56 PASS | — |
| Product scope registry | Lead | main | docs/product_scope_registry.md | manifest census | mọi surface có trạng thái | (commit docs) | — | app_tk DECISION owner |
| Decision registry D1–D7 từ 33 blockers | Lead | main | docs/decision_registry.md | legal_review_backlog | mỗi packet đủ evidence/options/khuyến nghị/impact | (commit docs) | — | **D1–D7 OPEN chờ owner** |

**Gate R0:** ✅ baseline tái lập (29/29 PASS, 0 NOT RUN) · ✅ hết FAIL mơ hồ
(p1_c triaged: verifier kỳ vọng sai format, production giữ nguyên) ·
✅ release runner hoạt động · ✅ scope registry + decision registry tồn tại ·
✅ worktree sạch sau commit · ⏳ owner chưa trả lời D1–D7 (không chặn R1/R2).

## R1 — P1-LAYOUT (L1 → L2 → L3)

| Task | Owner | Branch/Worktree | File ownership | Dependency | Gate | Commit | Test evidence | Blocker |
|---|---|---|---|---|---|---|---|---|
| R1.1 L1 extractor/schema (newline run, sup/sub/footnote, indent/spacing/keep-with-next, role, source-indicator vs form-number, detector 87/87, idempotent) | Lane L1 | agent/layout-l1 @ ../dangky_kinhdoanh-worktrees/layout-l1 | tools/docx_to_blocks.py + extractor tests | R0 | contract khóa, fixture extractor, semantic-idempotent | — | — | — |
| R1.2 L2 renderer/CSS (escape→br, sup/sub semantic, ẩn source-indicator theo role, allowlist CSS, responsive 375/768/1280×800, zoom 100–200%) | Lane L2 → Lead | agent/layout-l2 @ ../dangky_kinhdoanh-worktrees/layout-l1 → main | render.js, style.css, test_layout_l2_render.js, dev/snapshot.html | R1.1 merge | structural/DOM PASS; visual gate NOT RUN | `c301599`, merge `1aaa6c5` | `node app_web/test_layout_l2_render.js`: 77 PASS / 0 FAIL; L1 detector 87/87 PASS; release runner 30 PASS / 0 FAIL / 0 NOT RUN sau machinery sync; `git diff --check` PASS; visual browser backend unavailable = NOT RUN | visual evidence viewport/zoom chưa có |
| R1.2 release machinery sync | Lead | main | tools/release_runner.py, tools/audit_expected_diff_files.txt | L2 merge | suite L2 nằm trong runner; H7 exact-set không hồi quy | `5e1e08f` | `test_m72_activation`: 48 PASS / 0 FAIL; `test_audit_wave_h_negative`: 56 PASS / 0 FAIL; release runner 30/30 PASS | — |
| R1.3 L3 rollout batch (pilot → M01–M11 → M12–M26 → PLI còn lại → PLII_M01–M28) | Lead | main regenerate | generated artifacts | R1.2 merge + visual tooling | detector 87/87, screenshot từng batch | — | detector structural PASS; screenshot pilot/batches NOT RUN vì browser backend unavailable | visual gate chặn rollout/gate R1 |
| Independent visual auditor LAYOUT | Auditor mới | read-only | — | R1.3 | 8 Acceptance Gates P1-LAYOUT | — | NOT RUN — chưa có visual evidence để audit | chờ R1.3 visual evidence |

## R2 — P2 table platform

| Task | Owner | Branch/Worktree | File ownership | Dependency | Gate | Commit | Test evidence | Blocker |
|---|---|---|---|---|---|---|---|---|
| R2.1 khóa contract 4 kinds | Lead | main | docs/p2_component_contracts.md, docs/p2_dependency_graph.md, docs/p2_fixture_candidates.md | R1.2 merge | hết DRAFT | — | LOCKED v1 sau review Lead ngày 2026-08-27; D1–D7 vẫn OPEN và độc lập | — |
| R2.2 editable-grid remainder (cross_field_rules slot, keyboard/a11y lưới) | Lane EG → Lead | agent/p2-eg @ ../dangky_kinhdoanh-worktrees/p2-eg → main | form-domain.js, app.js, test_grid.js | R2.1 | fixture E1/E2 PASS | `213add3`, merge `b169c4b` | `node app_web/test_grid.js`: 111 PASS / 0 FAIL; `test_domain.js`: 64 PASS / 0 FAIL; `test_dom.js`: 58 PASS / 0 FAIL; release runner: 30 PASS / 0 FAIL / 0 NOT RUN; `git diff --check` PASS | fixed/nested/output components and generator gate remain |
| R2.2 output-table | Lane output → Lead | agent/p2-output @ ../dangky_kinhdoanh-worktrees/p2-output → main | output-table.js, test_output_table.js | R2.1 | production fixture O1/O2 PASS; no input/draft mutation; conditional render | `784f66d`, merge `0e25d93` | `node app_web/test_output_table.js` PASS; production PLI_M70/PLI_M71; release runner 31 PASS / 0 FAIL / 0 NOT RUN; `git diff --check` PASS | cần wire module vào renderer/controller và DOCX presence gate |
| R2.2 fixed-matrix | Lane fixed → Lead | agent/p2-fixed @ ../dangky_kinhdoanh-worktrees/p2-fixed → main | fixed-matrix.js, test_fixed_matrix.js | R2.1 | production fixture F2/F3 PASS; fixed rows, totals recompute, validation hooks | `c0693dd`, merge `5e3381b` | `node app_web/test_fixed_matrix.js` PASS; production PLI_M03/PLI_M04; release runner 32 PASS / 0 FAIL / 0 NOT RUN; `git diff --check` PASS | cần wire module vào renderer/controller và DOCX generator |
| R2.2 nested-grid | Lane nested → Lead | agent/p2-nested @ ../dangky_kinhdoanh-worktrees/p2-nested → main | nested-grid.js, test_nested_grid.js | R2.1 | production fixture N1 PASS; multi-row headers, physical columns, discriminator/groups | `2ff4890`, merge `bc8cbb4` | `node app_web/test_nested_grid.js` PASS; production PLI_M02 N1; H7 56 PASS; release runner 33 PASS / 0 FAIL / 0 NOT RUN; `git diff --check` PASS | cần wire module vào renderer/controller và DOCX generator |
| R2.3 draft migration | Lane migration → Lead | agent/p2-migration @ ../dangky_kinhdoanh-worktrees/p2-migration → main | form-domain.js, test_p2_migration.js | R2.1 | additive/idempotent/unknown-field preservation | `4e76340`, merge `48fd3e2` | `node app_web/test_p2_migration.js` PASS; `test_domain.js` 64 PASS; `test_grid.js` 111 PASS; release runner 34 PASS / 0 FAIL / 0 NOT RUN; `git diff --check` PASS | export/generator integration còn thiếu |
| R2.2 output-table → fixed-matrix → nested-grid | các lane tách module | tuần tự theo dependency graph | renderer/module riêng | R2.1 | fixture O1/O2, F1, N1 skeleton | — | — | F2/F3/F4 cần D1; N-full cần D2/D7 |
| Generator anchor/boundary/occurrence/totals/idempotency | Lead-only regenerate | main | build_form_maps.py, docx_to_blocks.py | contracts | chạy 2 lần cùng hash | — | — | — |

## Wave A rebaseline @ main 0fd2785→972e765 (2026-08-27)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Audit dirty state (89 artifact files) | Lead | Kiểm chứng byte-level: `word/document.xml` identical HEAD vs WT cho PLI_M01/M02/M30/PLII_M10; PLI_M72 chỉ thiếu 16 marker `{?loai_hinh_*}` → 146 field `cond` strip trong blocks; nguyên nhân = regen toàn cục đứt giữa chừng (zip timestamps + mất bước `tag_m72_sections.py`) | ✅ phân loại xong |
| Quarantine backup dirty artifacts | Lead | `/tmp/dangky_dirty_backup_0fd2785/templates` (87 file) + `/data/PLI_M72.json`; owner phê duyệt restore | ✅ |
| Restore artifacts về HEAD + baseline tái lập | Lead | Working tree sạch trừ PLAN.md; release runner **34 PASS / 0 FAIL / 0 NOT RUN** (`rr_clean_baseline.json`); `git diff --check` xanh | ✅ PASS |
| Commit master plan mới | Lead | `972e765` (chỉ PLAN.md, 1 file) | ✅ |
| Inspect production wiring của output-table/fixed-matrix/nested-grid | Lead | grep runtime: **0 reference** trong `index.html`/`app.js`/`render.js`/`form-domain.js`/`main.py` — 3 module standalone chưa nối. Call graph hiện hành: `index.html → form-domain.js/render.js/app.js → store(Render.newStore)+GridCtl(FormDomain.getGridMeta)` ; draft=`main.py save_draft/load_draft` ; export=`main.py export(payload)` ; generator=`build_form_maps.py (nguồn 6 folder → form_maps + templates) → tag_m72_sections.py (M72 markers) → docx_to_blocks.py (templates → blocks/*.json)` ; export DOCX=`docx_render.py` | ✅ ghi rõ — B1 sẽ lắp dispatcher theo kind, B2 khai bridge/generator |

**Gate A:** ✅ integration worktree sạch · ✅ baseline tái lập 34/34 ·
✅ ownership map: B1=index.html/app.js/render.js(+style.css/form-domain.js nếu bắt buộc);
B2=build_form_maps.py/docx_to_blocks.py/docx_render.py+spec/test mới;
B3=QA test/fixture mới (không đụng production); Lead giữ regenerate + merge.

## Wave D — visual P1-LAYOUT: pilot mở màn @ ab3c1f1 (2026-08-27)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Kiểm tra tooling browser/render | Lead | Python Playwright OK (`chromium-1228` tại `~/Library/Caches/ms-playwright`); DOCX renderer candidate: **Microsoft Word** (`/Applications/Microsoft Word.app`) — LibreOffice chưa có; harness `app_web/dev/snapshot.html` sẵn từ merge L2 | ✅ tooling đủ cho UI pilot |
| Pilot screenshots qua Playwright (Lead preview trước batch audit) | Lead | Script `~/.claude/jobs/8bd7e9b6/tmp/visual_pilot.py`; evidence `generated_ho_so/_visual_layout/pilot/` (9 PNG gitignored): PLI_M01/M02/PLII_M01/M70 @1280×800; PLI_M72 dntn+tnhh_2tv (biến thể switch đúng subtitle/Vốn điều lệ/mục 7, footnote superscript ²); PLI_M01 @768w, @375w; PLI_M72 zoom200% | ✅ 9/9 chụp thành công, 0 marker-leak, 0 snap-err (script tự scan DOM) |
| Lead mắt thường từng shot then chốt | Lead | M01 input viền/bảng vốn góp giữ hình học; M72 chỉ một variant hiển thị + selector radio đúng Option D; M70 date-line flex + hai khối ký output presence | ✅ structural pilot PASS |
| Batch 87 form + auditor độc lập read-only | Auditor mới | NOT RUN — chờ merge Wave B (B1 đổi dispatcher) rồi mới audit có ý nghĩa | ⏳ chờ B1 |

> Ghi chú kế hoạch batch sau merge: 3 viewport (1280×800/768/375) + zoom 100/150/200%
> × 87 form, lưu theo pattern `_visual_layout/<batch>/`, auditor agent KHÁC lead
> implement, đối chiếu DOCX qua Word→PDF→PNG khi mở Wave G.

## Wave B/C — R2 platform integration @ main ab3c1f1→(mới) (2026-08-27)

| Task | Owner | Commit/evidence | Trạng thái |
|---|---|---|---|
| B3 independent wiring gate | Lane B3 → Lead | `96cc12e`+`07808d0` merge `6486b5e`; gate 37 mệnh đề (S/A/B/C/D) | ✅ merged |
| B1 runtime wiring | Lane B1 → Lead | `94b98fb`,`a9ee544`,`65b9c23` merge `3428584`; suite riêng 124 PASS, toàn bộ regression giữ nguyên | ✅ merged |
| Gate sync theo kiến trúc production | Lead | `8567684`: sandbox window===globalThis, transport `opts.sectionContracts`, bất biến cấu trúc header, docId thật | ✅ **37 PASS / 0 FAIL** |
| B2 generator/export | Lane B2 → Lead | `62bbfa2` merge `676bf58`; deep idempotency 17 PASS, export kinds 13 PASS, M72 conditional 6 PASS | ✅ merged |
| Bridge totals recompute | Lead | `29ee9b6`: `write_rendered(...tables_meta=section_specs)` | ✅ |
| Machinery sync | Lead | manifest + runner đăng ký 4 suite mới → release runner **38 PASS / 0 FAIL / 0 NOT RUN**, H7 56 PASS, `git diff --check` xanh | ✅ VERDICT PASS |
| Visual evidence kind mới | Lead | snapshot harness nạp module + contracts; browser thật: M03 FM 3×5 + 8 input, M04 FM 4×6, M02 nested-grid ×2 (14 cột vật lý), M70 OT 2×1 outOnly=1; ảnh trong `generated_ho_so/_visual_layout/pilot/`; marker-leak scan 9/9 clean | ✅ pilot |

**Gate kỹ thuật R2 platform:** bốn kind wired runtime/draft/validation ✓ · generator
deep-idempotent ✓ · export recompute fail-loud ✓ · fixtures production PASS ✓ ·
runner xanh ✓.

**Chưa gọi R2 PASS tổng thể** — các mục còn mở (trung thực):
1. Regen batch thực tế sinh `w:tbl` mới trong templates/blocks: bị chặn pháp lý
   cho F2/F3 (D1.3/D1.5/D3.3 chờ bản gốc) — build skip qua `legal_status.blocked`;
   O1/O2 (DECIDED) sẵn sàng làm batch đầu nhưng cần per-form spec filescommitted.
2. Kênh validation N1 vocabulary canonical (`ten_nguoi_dai_dien` vs `ho_ten`,
   `ds_nddpl_uy_quyen_chu_so_huu` vs `nddpl_uy_quyen_chu_so_huu`) — chờ owner chốt
   trước khi khóa spec (ledger gap từ B1 #5.3).
3. Slot formula tích `so_luong × menh_gia` (F3/D1.4=A đã DECIDED): fixed-matrix
   hiện chỉ hỗ trợ `sum()` — cần schema v2 slot (đề xuất `product()`) trước khi
   rebuild PLI_M04/M12.
4. Free-text rule shape `sumEqualsKey` dùng trong runtime cần ghi nhận thành
   contract khi update docs v2 (docs v1 không bị sửa).
5. Duplicate source aliasing M70/M71 (03↔05 folder cùng tên file byte-identical):
   find_source first-hit có thể lật path lưu trong form_maps — đề nghị chuẩn hóa
   mapping canonical nguồn ở hygiene wave sau.

## Wave W1/W2 — R2-closure @ main 0cddd7f→(sau merge) (2026-08-27)

| Task | Owner | Commit/evidence | Trạng thái |
|---|---|---|---|
| W1 publication specs O1/O2 | Lane W1 → Lead | `f155078`,`bd9c25e`,`3c44b64` merge `d48eb7d`; test riêng 8/8; baselines giữ nguyên | ✅ merged |
| Lead regen targeted O1/O2 | Lead | `11f3f3b`: templates M70/M71 có w:tbl thật (2x1/1x1), blocks + form_maps `section_specs` sinh đúng; dispatcher anchors adapt (M71 span trước national-separator); fixture assertions đọc cell thay paragraph role cũ | ✅ regen theo batch, allowlist review |
| W1 gap trung thực | Lead ghi nhận | PLI_M01 2 section already_complete **chưa đăng ký được** — schema v1 chỉ có entry rebuild; chỉ ghi `gap_nghiepvu`, không chế mechanism | ⏳ backlog schema "already-mapped mode" |
| W2 product() parity | Lane W2 → Lead | `19bbd3e`,`a07ddaf` merge `0b0a2bd`; 24 JS + 19 PY assertions mới; parity cơ học py→JS | ✅ merged |
| Semantics product() Lead duyệt | Lead | (1) dòng bỏ trống hoàn toàn bị skip như sum; (2) đã kê khai thiếu thừa số → tổng TRỐNG không in 0; (3) cột-level projection backlog R3; (4) case-sensitivity backlog; (5) version giữ v1 + note additive | ✅ ghi minh bạch |
| Census evolution | Lead | `604a830` EVOLVED_FORMS + manifest recount 87/87 GATE PASS | ✅ |
| Battery sau closure | Lead | **38 PASS / 0 FAIL / 0 NOT RUN**, H7 56/0, H7.2 tổng quát hóa manifest-driven | ✅ VERDICT PASS |

**R2 kỹ thuật platform: ĐÓNG.** Còn mở (không chặn các wave sau, isolate đúng): N1
vocabulary owner decision; bản gốc M03/M04/M05; already-mapped registration mode;
column-level projection formula; case-sensitivity sum.

## Wave D audit lần 1 — độc lập @ HEAD 5118b7e (2026-08-27)

| Gate | Verdict | Evidence auditor (đã spot-check lệnh) |
|---|---|---|
| G1 allowlist + idempotency | ✅ PASS | 144 file diff = manifest exact (141 + 3 self-ref); diff --check 0 |
| G2 L1 detector | ✅ PASS (nhưng coverage hẹp — V3) | 87/87, exit 0; SI 46/46, leak 0 |
| G3 release runner | ✅ PASS | 38/0/0 VERDICT PASS |
| G4 DOM/layout | ✅ PASS | wiring 37/0; L2 render 77/0 |
| G5 screenshot phủ | ✅ PASS | 123 PNG / 87 form; 3 form dài nhất kiểm đáy không cắt |
| G6 viewport matrix | ✅ PASS (note N1: 375/768 xuất 804px do min-width 210mm — hành vi cuộn ngang đúng thiết kế) | |
| G7 marker/SI/form-number | ✅ PASS | 21 ảnh soi mắt; 0 `{..}`; "Mẫu số XX" đủ |
| **G8 nội dung dòng chuẩn** | ❌ **FAIL — BLOCKING** | V1: 6 form (PLI_M02 blk126, PLII_M02 blk72/129, PLI_M09 blk87/88/132/163, PLI_M12 blk145, PLI_M15 blk49, PLI_M72 blk109/111) bảng bị dẹt thành text glue + digit runs `12345678910`, không lưới dù GRID_META sẵn; V2: M72 blk110/112 tail-glue heading "8."/"9." role=body |
| V3 detector gap | 🟡 minor | L1 cần 3 rule: `STT<Capital>` run-glue, `\d{5,}` trong run text, numbered-heading role sai |
| Kết luận | **LAYOUT_DONE = CHƯA** | Sửa V1/V2 (+V3 rule) → re-shoot → tái audit |

> Ghi chú không chặn: N2 harness bar hiện flags JSON (chrome harness, không vào
> DOCX); N3 selector M72 nằm trong sheet ở harness (không có @media print).
> V1/V2 là nợ census đã ghi "Giới hạn ghi nhận tại HEAD" trong dependency graph,
> giờ bị auditor chặn tại gate thật. Wave E R3B mở để sửa đúng phần DECIDED.

## Wave P0 — Recovery checkpoint R3B1 @ main 7300ab4 (2026-08-27, Lead mới)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Phân loại 25 file modified + .DS_Store | Lead | Toàn bộ thuộc batch R3B1 regen + L1FIX round 2 (role flip body→section-heading 6 block) + sync test của lead trước; `.DS_Store` là rác macOS (đã ignore); `git branch --no-merged main` RỖNG — không còn sub-agent commit chưa merge | ✅ |
| Trim-anchor PLI_M02 theo đúng stage | Lead | Trim chạy lúc REBUILD trên NGUỒN (`bfm.find_source`, build_form_maps.py:1416-1443): hits=[144]/[230]/[50] khớp đúng 1 paragraph/form. Template generated + blocks không còn glue (đã thành w:tbl). Sync test đọc stage NGUỒN `tools/test_r3b1_people_specs.py::t_trim_matches_glue` — giữ nguyên độ cứng (exact 1 hit + keep_from) | ✅ 11/11 PASS |
| Sync expectation stale post-regen | Lead | `test_acceptance`/`test_pli_m02_industry`: chọn loop ds_nganh THEO TÊN thay vì đếm tổng (46/0); `test_industry_change`: exact-set + EXTRA_LOOPS {M02:1, M12:1} (6/0); `test_nested_grid`: header tra từ loop block 14 cột sau rebuild, giữ negative digit-run (PASS); H7 allowlist +10 entry có chủ đích | ✅ |
| Manifest recount M02/M12/M15 | Lead | Theo tiền lệ EVOLVED_FORMS (604a830): 3 entry lý do R3B1 (loop 1→2 / 3→4 / 0→1); `build_manifest --deep --write` GATE PASS 87/87, chỉ lệch key loop, p/chk/table nguyên vẹn | ✅ |
| Generator lần hai zero diff | Lead | Full pipeline (build_form_maps → tag_m72_sections → docx_to_blocks) ×2: JSON/blocks strict ZERO-DIFF RUN2 vs RUN1. Templates 87: 84 file member-level IDENTICAL toàn bộ (chỉ zip mtime/recompress — packaging noise của full regen) → RESTORE về HEAD để batch đúng scope evidence; 3 file content-change đúng bằng PLI_M02/M12/M15 (R3B1 chủ đích). Caveat: docx zip mtime làm byte-idempotency tuyệt đối bất khả thi — backlog generator hygiene | ✅ (classification minh bạch) |
| Dirty-worktree guard M72 | Lead | `test_m72_activation` check #8 đúng thiết kế: đỏ khi tree bẩn, tự xanh sau commit — KHÔNG sửa gate | ✅ (post-commit) |

**Gate P0:** release runner đầy đủ sau commit — 38 PASS / 0 FAIL / 0 NOT RUN
(xem Báo cáo checkpoint P0). LAYOUT_DONE vẫn CHƯA (P1 re-audit là phase kế tiếp).

## Wave P2 — R3 domain rollout (lane P2A/P2C/P2D) @ cdf8803→78d1879 (2026-08-27/28)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Merge lane P2D (a61cdfb) | Lead | D5.1: audit chứng minh chk_* đã wired đủ tại base (M17 17 ô/M19 9/M23 10/M25 10) — manifest census STALE; không khai entry trùng (tránh 2 nguồn sự thật). D5.3: slot cross_field_rules chưa có trong contract v1 (thử nghiệm cả 2 vị trí đều bị loader chặn) → khai slot inert + gap. M23 numbering nguồn là mục 7 (defect đã ghi). Suite mới 10/0 | ✅ |
| Merge lane P2C (1691728) | Lead | 3 fixed-matrix: M01 tai_san (D1.2=B mô tả text), M02 nguon_von + tai_san_von_dieu_le (D1.1=A totals output_only). Suite sandbox 16/0 + JS 60/0. Gap minh bạch: STT in sẵn, % computed, cross-field wire | ✅ |
| Merge lane P2A (abe6084) | Lead | PLII_M07 D2.8=A key riêng; M06 +thoi_han_gop_von (D2.2=A); M07 +dan_toc; M08 ghim spec (D2.3=A); M10 +quyen_chi_phoi (D2.5=A); M13 grid 7 cột, 1 row-type → KHÔNG discriminator; D7.3=A required/minRows 5 loop M72. Suite 14 PY + 80 JS | ✅ |
| Lead regen batch 8 mẫu (b9bccdf) | Lead | --one ×8 (PLII_M07, M06, M07, M08, M10, M13, M01, M02) + docx_to_blocks; deep idempotency 17/0; template member-level byte-identical quy tắc như P0 | ✅ |
| Lead wire runtime (516b22a) | Lead | FORM_TABLE_CONTRACTS +3 section P2C (sumEqualsKey CAPITAL_MISMATCH blocking + percentSum warning, key canonical chung F2); tripwire [GATE]/[GAP] P2C lật thành assert thật; m72 N9 required=true/minRows=1 | ✅ |
| Rename M06 loop (a578e43, 78d1879) | Lead | Export conflict guard flag ĐÚNG ds_thanh_vien 2 contract (11 vs 10 cột) — fail-loud đúng LOCKED v1. Theo tiền lệ nganh_sua_doi_chi_tiet: M06 loop riêng ds_thanh_vien_tnhh (trùng semantic_key manifest); GRID_META entry global mới 11 cột; ds_thanh_vien 10 cột giữ cho M09; draft M06 rỗng thực tế → không migration (chính sách D2.9). Sync 6 suite pin cũ | ✅ |
| Census refresh (6e972e7) | Lead | 18 LEAD_STATUS_OVERRIDES có evidence suite thật: 15 already_complete + N1/N6/N7 partial_columns (2 nhóm cuối khai thiếu); EVOLVED_FORMS +PLII_M07/PLI_M01/PLI_M13. GATE PASS 87/87 sau --write | ✅ |
| Fix L1 invariant + W1 guard | Lead | test_layout_l1_extractor 55/55 (invariant 12 override viết lại MẠNH HƠN post-regen); test_w1 8/8 (guard PLI_M01 thu hẹp theo section đã-map) | ✅ |
| Release runner checkpoint | Lead | **38 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS** @ 78d1879; git status sạch; allowlist exact-set 180=180 | ✅ |

**Blocker còn mở (owner, không chặn lane khác):** M09 (D3), PLII_M02 member grids
(ghim occurrence), M72 N2–N5, D5.2 canonical thuế PLII_M02, N-tail groups
(Tổng giá trị/Thời điểm), D6.1 evidence M56, D6.3 min/max, D6.4 max/placeholder,
M03/M04/M05 bản gốc.

### Visual re-shoot P2 @ fc8b5e0→b839fa6 (2026-08-28)

| Vòng | Kết quả | Evidence |
|---|---|---|
| Re-shoot 9 chủ thể (8 form regen + M72@dntn) | **FAIL** — bắt 2 regression do wire 516b22a: ISS-1 (M02 §7/§8 endMatch:null → span EOF nuốt section 8–12) + ISS-3 (M01 matchRole sai, contract fail-close mất totals computed) | report.json `gates` + 9 PNG `p2reshoot/` |
| Fix 1 (5f73f10) | endMatch thật cho M02 §7/§8; M01 anchor role body + endMatch; REG gate renderBlocks thật (bắt marker/khoảng trống) | test_p2c 64/0; runner 38/0/0 |
| Re-verify 1 | ISS-1/3 hết; còn ISS-5 (builder fixed-matrix ăn heading section — M03 gap có sẵn từ R2) | report.json `reverify` |
| Fix 2 (b839fa6) | render.js: block anchor fixed-matrix giữ hiển thị (theo kind); REG +assert heading đúng 1 lần ×3 form | test_p2c 66/0; runner 38/0/0 |
| Re-verify 2 | **RESHOOT_PASS 5/5** — heading đúng vị trí/đúng 1 lần, 0 marker, không tràn; ISS-2 được fix 2 xử lý; ghi chú nhỏ còn mở: M01 header là td (semantics bảng, để P5) | report.json `reverify2` + `final_verdict` |

**Ghi chú quy trình:** re-shoot bắt regression do chính Lead wire — đúng lý do
PLAN bắt visual evidence sau mọi regen; Production fix + REG gate đi cặp.

## Wave PLAN-v3 — rewrite kế hoạch @ f3d614c (2026-08-28, lệnh owner)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Push toàn bộ lên GitHub | Lead | origin/main = f3d614c (85 commit), 29 heads (22 agent/*), 2 tag baseline | ✅ |
| Rewrite PLAN.md v3 | Lead | Xóa P0/P1/P2 đã đóng (tham chiếu ledger); chi tiết còn lại: P3 (merge p3-e2e + 9 finding theo 4 cụm fix + app-shell a11y + platform NOT RUN), P4 Review Gate Excel, P5/P6/P7; tích hợp PLAN_excel nguyên văn thành mục 4 (workflow 7 bước + X1–X6 + rủi ro + E1–E6); quy tắc "phase mới chỉ mở theo lệnh owner" vào mục 6 | ✅ |
| PLAN_excel.md → bản lưu | Lead | Đánh dấu superseded bởi PLAN.md mục 4, giữ nguyên văn để tra cứu | ✅ |

## Wave P3 — E2E/A11y/Security/Resilience @ main ccff34a→eeb0ba1 (2026-08-28, lệnh owner)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Phân loại baseline đỏ 37/1 | Lead | H7.4 exact-set lệch `docs/leader_handoff_p3.md` (commit ea112ed của Lead trước chưa cân manifest — docs-only, không phải regression production). Fix +1 dòng chủ đích `ccff34a`; tái lập **38 PASS / 0 FAIL / 0 NOT RUN** | ✅ |
| P3.0 dọn worktree đã merge | Lead | 17 lane cũ merged=YES sạch → remove + xóa 17 branch; **lệch mô tả bắt được**: `p2-wire` có 4 file CHƯA commit (prototype component-dispatch bị Wave B1 thay thế) → park thành commit `200780a` trên `agent/p2-wire` (KHÔNG merge), không xóa mất việc | ✅ |
| P3.1 merge p3-e2e @ b61def0 | Lead | `76c89b8` --no-ff: đúng 4 file test mới (2360 dòng, 220 PASS tại lane); đăng ký 4 suite vào release_runner + allowlist +4 (`b490874`); runner **42/0/0**. a11y exit-0 là quy ước lane (8 FAIL = KNOWN-FINDING, không phá gate) | ✅ |
| P3.2 cụm draft-crash | Lane p3-fix-draft | `451a4ae` merge `a4749e2`: guard Array.isArray `normalizeStoreLoops` + `GridCtl.rows/ensureIds` (2 lớp — loops primitive strict-mode ném khi ghi index); draft hỏng → chuẩn hóa [] an toàn. test_p3_draft **80/0/0 KNOWN-FINDING** (74/0/6 trước); domain 64/0, grid 111/0, hardening 56/0 | ✅ đóng F-P3-1/2 |
| P3.2 cụm export-path + log-redact | Lane p3-fix-export | `7cf8144`+`3e7ab7f` merge `704a9e3`: `_sanitize_name` (case_id limit 255-1-16 ts; fid chỉ phần tên file, key tra maps giữ nguyên) + mkdir try/except `EXPORT_DIR_CREATE_FAILED` + `_safe_error` bỏ repr; docx_render detail ExportTotalsError lọc stored/computed (giữ ở problems[i]). 7/7 case hostile không throw/không thoát generated_ho_so. Lead sync 2 pin cũ GHIM giá trị thô → `not in` (`65cd829`, CHẶT hơn không nới); export kinds 13/0, totals product 19/0 | ✅ đóng F-P3-SEC-PATH/FID/LOG |
| P3.2 cụm DOCX-NUL | Lane p3-fix-docx | `328fcac` merge `d1f4727`: `safe_escape` strip `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]` (XML 1.0 Char spec 2.2), GIỮ \t\n\r; giá trị sạch byte-for-byte (docx_render --test-all 87/87). test_p3_security **90/0/0** | ✅ đóng F-P3-SEC-NUL |
| P3.2 cụm a11y + P3.3 app shell | Lane p3-fix-a11y | `53f3133` merge `eeb0ba1`: bỏ `outline:none` 2 chỗ che `:focus-visible`; renderLoop/nested/fixed-matrix `role=grid`+col/rowcount; 6 nút row-op + .chk-box aria-label (chk-box qua enhancement DOM — test_dom/layout_l2 pin đúng chuỗi HTML, pattern "renderer remains unchanged"); test_p3_a11y **36/0** (24/8 trước) + gate G7 app shell thật (tablist/roving/arrow/trap, `?mock=1`, index.html KHÔNG cần sửa) | ✅ 8 FAIL → 0; 9/9 finding đóng |
| P3.4 platform Windows | Lead | `865cb16`: `docs/platform_smoke_checklist.md` S1–S8 + quy tắc verdict; **NOT RUN — CHƯA TỪNG CHẠY** (không có máy Windows) | ✅ NOT RUN có lý do |
| Gate P3 | Lead | Runner **42 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS** @ eeb0ba1; compileall PASS; `git diff --check` 0; **không regen** (0 thay đổi generated; test_generator_deep_idempotency 17/0); visual re-shoot 5/5 (M01/M02/M03/M70/M72@dntn — 0 marker, aria đủ, không tràn, 0 page error; Lead soi mắt M01+M72) `generated_ho_so/_visual_layout/p3_reshoot/`; dọn xong 5 worktree fix-lane đã merge; git status sạch | ✅ **P3 PASS** |

**Gate P3 (PLAN mục 5):** runner ~42 suite 0 FAIL ✓ · 4 suite P3 xanh ✓ · 9 finding
đóng ✓ · blocking-error chặn export có test (test_p3_e2e DOCX export gate 38/0) ✓ ·
evidence platform NOT RUN có lý do ✓. **Blocker pháp lý giữ nguyên trạng thái blocked**
(M09, PLII_M02 member, M72 N2–N5, D5.2, N-tail, D6.x, M03/M04/M05 — không đụng).
Còn mở không chặn: lone surrogate/U+FFFE-U+FFFF không strip trong safe_escape
(fail-loud ở render, gap đã ghi); index.html không phát hiện thiếu sót a11y.

## Wave P4 — Review Gate Excel @ main 78a0b0f→b72a155 (2026-08-28, lệnh owner)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| P4.1 đối chiếu data-key | Lead | `docs/p4_excel_review_gate.md` §1: 381 scalar key (243 prefixed/138 flat) + 20 loop đo từ form_maps @ 78a0b0f; phân loại Ổn định (dn.*, 5 loop ngành M72 `ds_nganh_pli_m72`, vốn, người, 6 lưới người DECIDED) / Đang trôi (`ma_so_van_ban` D4.2 chưa tách; `ds_thanh_vien` M09 sẽ đổi 14 cột D3.2; flat-vs-prefix → bắt buộc map per-procedure; ngày sinh tách 3 key) / Bị chặn (D5.2, N2–N5, N-tail — 40 section census chưa đủ) | ✅ |
| P4.2 thủ tục ưu tiên + cụm câu hỏi | Lead | §2: khuyến nghị cụm đầu **"Thành lập doanh nghiệp" qua PLI_M72** (1 thủ tục phủ 5 variant `loai_hinh`, key thuộc vùng ổn định; phù sau: PLII_M01 hộ KD, M02/M12 đổi ngành; thuế để sau) + draft 23 câu v1 nhóm đời thường map `question_id → data_key`, chờ owner duyệt (E6) | ✅ draft chờ duyệt |
| P4.3 dependency | Lead | §3: openpyxl 3.1.5 có sẵn máy dev **chưa pin**; probe thật sandbox: protection sheet ✓, dropdown DataValidation Unicode ✓, round-trip ✓; file dialog theo pattern tkinter `main.py:139–166`; máy sạch OK (thuần Python) | ✅ khả thi |
| P4.4 effort/risk + E1–E6 | Lead | §4: X1–X6 ~9–13 phiên, mỗi wave commit sạch; §5: E1–E6 kèm khuyến nghị; **lệnh chờ owner: `Bắt đầu Excel` hoặc `Để sau`** | ⏳ chờ owner |
| Gate P4 (docs-only) | Lead | commit `b72a155` (+allowlist 1 entry có chú thích); H7 56/0 tại HEAD; full runner tái xác minh tại HEAD docs-only | ✅ |

## Wave Excel X1–X5 @ main 114e7fa→9f136be (2026-08-28, lệnh owner "Bắt đầu Excel" + duyệt E1–E6)

| Wave | Owner | Commit | Evidence | Trạng thái |
|---|---|---|---|---|
| X1 questionnaire | Lead | `114e7fa` | schema v1 + builder fail-loud + cụm 24 câu owner duyệt (E6); artifact `app/data/questionnaire/PLI_M72.json` generated ×2 zero-diff; test_questionnaire 10/0; runner 43/0/0 | ✅ |
| X2 xuất .xlsx | Lane x2-export | `cc1c221`→merge `fae9a6a` | write_questionnaire protection/dropdown/quy ước vàng–xám + sheet map; pin openpyxl==3.1.5; test_excel_export 25/0 | ✅ |
| X3 nạp .xlsx | Lane x3-import | `3191fa8`→merge `550d611` | import_questionnaire(path, q) fail-loud 8 mã lỗi riêng; selftest 6/0 + probe 32 assertion | ✅ |
| X5 UI + bridge | Lane x5-ui | `df2e666`→merge `a5b0b73` | 2 nút + Bridge.export/import_questionnaire (sanitize doc_id, _safe_error); dom 58/0, e2e 38/0, a11y 36/0 | ✅ |
| X4 tích hợp + round-trip/negative | Lead | `3d5457d`+`9f136be` | Căn 3 lệch lane (map contract key/when+metadata key=value; bảng N hàng = N dòng map; bridge đảo (path, q)) + hằng render về lớp X1; test_excel_roundtrip 4/0 (giữ 100% giá trị, đổi nhánh when, deterministic theo nội dung ô), test_excel_negative 9/0 (data=None khi fail); runner **46/0/0 VERDICT PASS** @ 9f136be | ✅ |
| X6 visual | Lead | — | phiếu mẫu thật + owner duyệt hình (máy dev không có Excel/LibreOffice — mở bằng Excel là việc owner) | ⏳ |
| Phát sinh từ owner | — | — | (1) thiếu use case "Thay đổi nội dung đăng ký hộ kinh doanh" (PLII_M02) trong use_cases.json; (2) header mẫu phải xếp TÊN DN trái + quốc hiệu phải như bản Word gốc (Mẫu 2/13); (3) mở bảng blocked bằng nguồn NĐ 168/2025 + TT 68 (owner khuyến khích tự tra cứu + hỏi owner khi cần) | ⏳ handoff |

## Wave Lead-tiếp-quản @ main 178ba3a→355e133 (2026-08-28, lệnh owner: use case + header + rollout TT 68 + X6)

| Task | Owner | Commit/evidence | Trạng thái |
|---|---|---|---|
| XÁC MINH đầu tiên | Lead | HEAD ≥ 9f136be; worktree chỉ main; commit edit tồn đọng handoff (`178ba3a`); runner 46/0/0 | ✅ |
| Use case "Thay đổi nội dung đăng ký hộ kinh doanh" (PLII_M02) | Lead | `85fa95b`: +1 case (27→28) theo Điều 100/101 NĐ 168 (đọc nguyên văn); pin P3-UC1 sync theo bằng chứng; allowlist +1 `85fa95b`→`eaa50f0` (2 suite đỏ ảo H7 khi chưa cân — đúng tiền lệ) | ✅ |
| Fix lớp lỗi checkbox dẹt thành text | Lead | `ba64f29`: gốc rễ = process_checkboxes chỉ gắn the khi khớp whitelist CHK_RULES ("3 thang..." ≠ "03 thang..."). Rule `0?3/0?6` + fallback `_auto_chk_key` (mọi □/☐ đều được gắn the). Regen 4 mẫu, 6 glyph → 6 chk; sandbox pass 0 glyph; visual re-shoot 4/4 (0 marker, 0 page error, M01 render đúng "3 tháng một lần") `generated_ho_so/_visual_layout/chkfix/` | ✅ |
| Census đánh số mục + chuỗi companion | Lead | `ba64f29`+`355e133`: `tools/census/numbering_audit.py` (JUMP/CHAIN/GLUE). Phân loại: CHAIN GAP M03→M06 (6→8), M04→M08 (7→10), M05→M09 (6→8) — đúng phạm vi lane rebuild; GLUE chữ chú thích 23 mẫu — lớp extractor V3, chờ đợt riêng; 0 JUMP ngoài vùng nhiễm M09 | ✅ census / ⏳ fix qua lanes |
| X6 phiếu Excel mẫu PLI_M72 | Lead | `generated_ho_so/_visual_layout/excel/PLI_M72_phieu_mau.xlsx` + preview HTML; reload-kiểm openpyxl PASS (protection ON, sheet ẩn ___map, 41 ô điền vàng/65 hàng). **Owner mở bằng Excel thật và duyệt hình: PASS (2026-08-28, trả lời "ok")** — NOT RUN kết thúc, X6 ĐÓNG | ✅ |
| Lanes song song (SOP mục 6, tối đa 3) | 3 lane agent | BASE `eaa50f0`: `agent/hdr2col` (Việc 2 header 2 band) · `agent/cap-von` (Việc 3a nguồn vốn M03/M04/M05/M12 + 3b thuế PLII_M02) · `agent/m09-rebuild` (Việc 3c M09 14 cột + fix mất mục 7). Lead tự wire form-domain.js khi merge (PLAN 6.4). Batch 2: M72 N2–N5 + thuế M17/M19/M23/M25 | ⏳ đang chạy |
| Owner response 2026-08-28 (lần 2) | Lead | docs/decision_registry.md: nguồn TT 68/NĐ 168 + 5 nhóm mở + defect hunt + lưu ý TT 121/2026/TT-BTC sửa TT 68 (thay 09 biểu mẫu — lane phải kiểm tra) | ✅ |

**Gate giữa wave (355e133):** runner **46/0/0 VERDICT PASS**; `git status` sạch;
deep idempotency 17/0; manifest GATE PASS 87/87; visual re-shoot chkfix 4/4.

## R3–R7 (khung — chi tiết hóa khi mở wave)

| Wave | Điều kiện mở | Ghi chú |
|---|---|---|
| R3A capital | D1 + D3 DECIDED, P2 fixture pass | PLI_M01–M05, M12 |
| R3B people | D2 + D7 DECIDED | PLII_M02/M07, PLI_M06–M10, M13, M15, M72 |
| R3C tax | D5 DECIDED | PLI_M17/M19/M23/M25, thuế PLII_M02 |
| R3D branches/admin | D6 (+D4 cho M52) | 13 form còn lại |
| R4 E2E/a11y | R1–R3 gates PASS | automated + manual WebView2 |
| R5 visual QA | R4 PASS | cần LibreOffice/Word hoặc renderer được owner chấp thuận |
| R6 Windows package | R5 PASS | cần môi trường Windows sạch của owner để smoke |
| R7 independent audit | R6 PASS | auditor mới read-only; APP_DONE 10 điều kiện |

## Wave A — PLAN v4 baseline xanh @ main 6ae63c2→cdb39f9 (2026-09-02, Lead)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Phân loại 4 tài liệu dirty + commit riêng | Lead | `eb9e723` (PLAN v4, defect reconciliation, D2/P5R ghi lịch sử, audit handoff) — nhất quán với source đã kiểm: 2 FAIL verifier thật, a11y phụ thuộc môi trường | ✅ |
| Tái hiện baseline | Lead | runner **44 PASS / 2 FAIL / 0 NOT RUN** trên máy dev (a11y bind OK ở đây): `p1_c_verify_plii_m02` + `test_industry_household` — đúng AUD-002/003 | ✅ |
| Root cause AUD-002/003 | Lead | classifier bảng theo VỊ TRÍ (skip mù bảng đầu `first_tbl_seen`, mốc thuế `tax_start`) ăn nhầm bảng ngành thật sau khi template có 6 bảng: p1_c mất `nganh_bo_sung`, household mất `nganh_hien_tai`. Production template/form_maps ĐÚNG — không sửa template (PLAN A.2) | ✅ |
| Fix semantic classifier + mutation test | Lead | `cdb39f9`: `classify_table` (band/thuế "Chỉ tiêu"/industry theo nội dung header) dùng chung 1 nguồn cho cả 2 gate; đối chiếu theo THỨ TỪ vùng (bắt thiếu/thừa/đảo — sorted cũ không bắt được đảo); selftest negative mutation (band/thuế chen giữa, thiếu, đảo, ngoài vùng) chạy mỗi lần verifier | ✅ |
| Preflight a11y trong runner | Lead | `build_cmd` preflight `bind_localhost`: sandbox cấm bind → critical NOT RUN có lý do (không FAIL giả); release chính thức vẫn bắt buộc a11y ở môi trường hỗ trợ. Đã test cả 2 nhánh | ✅ |
| Cân allowlist H7 | Lead | +`docs/whole_app_audit_2026-08-30.md` (commit eb9e723 đưa vào range diff baseline..HEAD); H7 56/0 | ✅ |
| Full runner checkpoint | Lead | **46 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS** @ `cdb39f9`; `git diff --check` 0; git status sạch | ✅ **GATE A PASS** |

**Còn OPEN sau Gate A (không thuộc Wave A):** Class 3 footnote GLUE 23 form,
Class 11 coverage drift, Class 12 L1 (newline 263 + STT/digit-run), Class 13
visual NOT RUN — xử lý ở Wave B/C/D theo PLAN v4.

## Wave B — coverage matrix 111/111 @ main 1082d75→9aa755e (2026-09-02, coverage-agent)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Worktree `agent/coverage` @ 1082d75 | Lead | worktree sạch, SOP 6.2 | ✅ |
| Tool census 2 chiều + selftest + matrix | coverage-agent | `62fb4d6`: đúng 4 file ownership (`table_coverage_audit.py` 1369 dòng, selftest 447 dòng 44/44 PASS, `docs/table_coverage_current.{json,md}` 111 hàng); không đụng production | ✅ |
| Trạng thái 111 section | coverage-agent | IMPLEMENTED_VERIFIED 31 · PARTIAL_COLUMNS 6 · MISSING_IMPLEMENTATION 20 · BLOCKED_OWNER 41 · NO_TABLE 7 · OUTPUT_ONLY 6 · REMOVED_BY_CURRENT_LAW 0 | ✅ Gate B: 111/111 có status có bằng chứng |
| Gate hai chiều | Lead xác minh | tool exit 1 thật (42 drift — lần đầu đo exit qua pipe `tail` là sai, đã đo lại trực tiếp): 12 census-stale + 30 thiếu runtime contract; override 22/22 resolve; count 111 PASS | ✅ gate hoạt động, drift là deliverable |
| Merge + cân allowlist | Lead | merge `--no-ff` → `9aa755e`; allowlist +4 entry; runner **46/0/0 VERDICT PASS** sau merge; tool re-run trên main cùng kết quả (chỉ lệch stamp head) | ✅ |
| Dọn worktree | Lead | status sạch → `worktree remove` + `branch -d` | ✅ |
| Chưa làm (có chủ đích) | Lead | KHÔNG refresh production manifest ngay: nhóm 30 `implemented_missing_evidence` cần adjudicate cơ chế chk-token (runtime thật của section chk là chk-token + renderer + CHK_RULES, không phải GRID_META) trước khi lật status — tránh lật ngược 30 dòng already_complete theo heuristic | ⏳ Wave D / owner packet |

**Con số công bố sau Gate B:** cần làm thật **26 section** (20 MISSING + 6 PARTIAL);
chờ owner/pháp lý 41; không phải bảng 13. Chi tiết từng dòng trong
`docs/table_coverage_current.md`.

## Wave C — whole-app audit read-only @ 9e9ba0d (detached, 2026-09-02, whole-app-auditor)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Auditor read-only, detached worktree | Lead | worktree @ 9e9ba0d, git status sạch, 0 commit; evidence ghi vào `generated_ho_so/_visual_layout/whole_app_audit/` (gitignored) | ✅ |
| UI quét 87/87 | auditor | Playwright + snapshot.html: DOM hygiene @1280 (0 `undefined/null/NaN`, 0 marker leak, 0 overlap/cut, 0 console error) + 768/375 + zoom 150/200% + keyboard (3070 tab stop, 0 mất outline) + aria; 4 data states (rỗng/hợp lệ/invalid/legacy/large) qua engine validate/migrate thật | ✅ 87/87 |
| DOCX/Word | auditor | sinh DOCX 87/87 + structural scan document.xml (0 marker, số bảng == coverage matrix); **Word PDF visual NOT RUN** — TCC Automation chặn AppleEvent (-1712/-609), blocker môi trường, xử lý ở Wave F bằng GUI-drive | ✅ structural / ⏳ visual |
| Use case 28/28 + M72 5/5 + ZIP 5 đại diện + Excel | auditor | 28/28 mở form + luồng chính; M72 5 variant không trộn (structural); ZIP đủ 4 table kind; Excel PLI_M72 round-trip PASS | ✅ |
| Finding mới F1 | auditor | **20 form validation gap** khối liên hệ + CCCD M07 (Class 14 mới trong defect registry) — rác in được vào DOCX | ❌ chuyển Wave D fix-industry |
| Verdict Gate C | Lead | 87/87 form + 28/28 use case đều có verdict (thành phần Word visual = NOT RUN trung thực) | ✅ **GATE C PASS (có NOT RUN có lý do)** |

**Chuyển sang Wave D:** 3 lane batch 1 theo PLAN 6.6 + F1 vào fix-industry (cùng
file ownership form-domain.js). Word PDF visual: Wave F dùng computer-use GUI
thay AppleScript TCC.

## Wave D batch 1 — 3 lane @ main 65c7346→cc2349e (2026-09-02, Lead merge)

| Lane | HEAD | Deliverable | Kết quả |
|---|---|---|---|
| fix-extractor | `2c6c5a8` | KHÔNG đổi extractor — chứng minh extractor compliant tại BASE: GLUE 50/50 hit là superscript tách đúng; newline 309→263 toàn bộ hợp lệ (511/511 w:br giữ trọn); STT/digit-run + chain-gap BLOCKED_OWNER có evidence nguồn (bản gốc full CÓ mục 7/8–9, mất ở bước tách); test pin 12/12 | ✅ merged |
| Lead census | sau merge | `numbering_audit` GLUE vertAlign-aware → **0 unresolved** (50 block phân loại đúng); `check_layout_l1` baseline 263 kèm comment bằng chứng | ✅ |
| fix-industry | `74ce895` | Class 9: applyVsicPick sai key + binding INDEX → _row_id + normalize nullish + export guard (36 test). Class 14: 4 key contact FIELD_META + phone/website + cccd (110 test, đủ 20 form). 3 pin cũ sửa có căn cứ | ✅ merged |
| fix-docx-layout | `299f986` | Class 7 PLI_M70 render-layer `_ensure_signature_space` (T0–T2 đỏ→xanh); Class 8 CLOSED không phải defect (44 chk đo, 0/44 lệch); Class 4 band PASS + lock test 16/0; page-break baseline pin | ✅ merged |
| Checkpoint | Lead | runner **46 PASS / 0 FAIL / 0 NOT RUN** @ `cc2349e`; allowlist +5 (4 test mới + test_domain.js pin); worktrees dọn sạch; không cần regen (extractor/generator unchanged; docx_render là render layer) | ✅ **BATCH 1 ĐÓNG** |

**Sang batch 2 (template/source + generator, Lead ownership regen):**
1. Chain-gap mục 7 (PLI_M03) + mục 8–9 (PLI_M04) — đã có nguyên văn nguồn.
2. PLI_M09 thiếu 4 khối chữ ký (nguồn 5, template 1) — cùng class mất ở tách nguồn.
3. STT-glue/digit-run PLII_M02 #69/#122 + PLI_M72 #109/#112 — rebuild w:tbl.
4. PLI_M12 chk kép `chk_khong` (Class 15 mới).
Sau batch 2: regen ×2 zero-diff, census/L1/numbering gate kỳ vọng xanh hết (ngoài
owner exception), runner full.

## Wave D batch 2 — source/template @ main 56c11bf→fe0c680 (2026-09-03, Lead trực tiếp)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Điều tra nguồn chain-gap | Lead | delta đo được: `DN_PL1_Mau_03/04` (116/149 dòng) vs bản gốc full (226/260 dòng) — mất TOÀN BỘ đuôi mục 8–11/10–13 (NĐDPL, thuế, BHXH, CSHHL, cam kết, ký, footnote). Nguyên văn mục 7/8–9: para 847/1161/1162 `_Bieu_mau_PL_I_II_full.docx` | ✅ |
| Quyết định phạm vi | Lead | KHÔNG swap nguồn đầy đủ — phần đuôi thuộc D1.3/D1.5/D3.3 OPEN (owner). Khôi phục CHỈ dòng pointer trong chuỗi hiện hành qua cơ chế spec `inserts` (mở rộng `pos:"end"`, pipeline-native, không sửa tay template) | ✅ trung thực phạm vi |
| Regen M03/M04 + chain gate | Lead | `numbering_audit --gate` **exit 0**: 3/3 chain OK (7→8, 9→10, 6→7), 0 JUMP, 0 GLUE unresolved; pin `CHAIN_FORMS` cập nhật main_last 7/9 | ✅ Class 2 CLOSED |
| Class 15 chk kép M12 | Lead | root cause: heuristic ưu tiên seg_after cho mọi glyph → "Có □ Không □" cả hai về `chk_khong`. Fix surgical: chỉ can thiệp khi legacy sinh key TRÙNG trong cùng paragraph (quy ước before/after + dedup); deep idempotency **17/0** — mọi form khác byte-giữ-nguyên; block18 = `chk_co`/`chk_khong` | ✅ Class 15 FIXED |
| M09 4 khối ký | Lead | đối chiếu nguồn: 4 đoạn @para 111/139/165/218 đều trong vùng nhiễm p102→hết (D3.1=A owner đã duyệt decontaminate); khối ký thật @89 có trong blocks → **by-design, không phải defect**; allowlist pin ghi vĩnh viễn lý do | ✅ CLOSED |
| STT-glue/digit-run 4+2 vị trí | Lead | PLII_M02 #69/#122 = header 2 lưới thành viên (blocker owner "ghim occurrence" — template KHÔNG có bảng thành viên, 4 loop blocks chỉ là ngành); PLI_M72 #109/#112 = N2–N5 (blocker D2.9). Coverage a4/c7 "PARTIAL_COLUMNS" là over-bridge của tool → adjudication ghi vào registry | ⏳ owner packet |
| Checkpoint | Lead | runner **46 PASS / 0 FAIL / 0 NOT RUN** @ `fe0c680`; tree sạch; form_maps.js/json sync | ✅ **BATCH 2 ĐÓNG** |

## Wave E — post-fix-auditor độc lập @ fe0c680→2593e3e→db46a6b (2026-09-03)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Auditor mới read-only, detached | Lead | worktree @ fe0c680; E1 gate chạy độc lập khớp Lead: runner 46/0/0, numbering exit 0, L1 đúng (e)4+(f)2, idempotency 17/0, coverage 42 drift totals nguyên, p1_c PASS, 0 marker/glyph leak 87 blocks + 87 DOCX XML | ✅ |
| Diff review chống gian lận gate | auditor | 6 pin sửa ĐỀU có căn cứ (P3-D23, FIELD_META cap, N8c, CHAIN_FORMS, MISSING_SIGAllowlist M09 by-design, allowlist entries khớp diff); KHÔNG có assertion luôn-true / hạ threshold / sửa generated tay | ✅ |
| **Finding F1 (BLOCKER)** | auditor | mục 7/8–9 mới khôi phục bị `.dupe-anchor` ẩn trên UI (section không endMatch nuốt span tới EOF) — DOCX đúng, UI không thấy | ❌ → fix |
| **Finding F2 (HIGH)** | auditor | Class 15 chỉ fix 1/11 đoạn: dedup per-paragraph còn sót chk_khong×2 (#50/#115) + collision chéo chk_co #18↔#188; form_maps drift generator ở 6 form → test_header_layout [FIELDS] đỏ ngoài runner | ❌ → fix |
| Fix F1 | Lead | `render.js sectionSpanOfParts`: không có boundary tường minh → span dừng ở BẢNG CUỐI section; re-audit delta: mục 7/8–9 visible đúng vị trí, 3 form fixed-matrix khác 0 dupLeak | ✅ `2593e3e` |
| Fix F2 | Lead | `process_checkboxes` 2 PHA (legacy toàn form giữ byte + convention chỉ cho đoạn key-trùng, exclusion TẦM FORM) + regen 7 form drift; re-audit delta: 0 đoạn dup trong 87 blocks, 4 câu hỏi Có/Không M12 4 cặp key riêng, DOCX 1 key = 1 X, header_layout [FIELDS] 11/0 | ✅ `2593e3e` |
| Runner mở rộng | Lead | +3 census suite: numbering (critical, PASS), L1 + coverage (diagnostic noncritical — FAIL hiển thị không chặn); coverage chạy `--no-write` khỏi bẩn tree; verdict đếm đúng cờ critical | ✅ `db46a6b` |
| Verdict Wave E | Lead | RE-AUDIT DELTA **PASS** (auditor xác minh độc lập cả F1/F2 + gates); các còn lại đều owner-blocked có packet | ✅ **WAVE E ĐÓNG** |

## Wave F — P5R assessment @ db46a6b (trung thực, chưa tuyên bố DONE)

| Gate | Verdict | Ghi chú |
|---|---|---|
| G1 Legal/source | **PASS** | specs có legal_status/source_evidence; đuôi M03/M04 chờ P1 packet (không chặn phần đã implement) |
| G2 Coverage | **PARTIAL** | 111/111 status có bằng chứng; manifest refresh chờ adjudicate chk (packet P1/P2/P4) — 42 drift đã đo và phân loại |
| G3 Numbering | **PASS** | numbering gate exit 0 (0 JUMP/CHAIN/GLUE unresolved); L1 STT/digit-run = diagnostic FAIL owner-blocked (P2) |
| G4 UI hygiene | **PASS** | Wave C 87/87 + re-shoot 8 form sau fix: 0 undefined/NaN/marker/overlap/console |
| G5 Tables | **PASS (implemented set)** | 31 IV + 6 PC qua one-row/round-trip/formula/conflict/DOCX; backlog 26 section chờ owner scope |
| G6 DOCX/ZIP | **PARTIAL** | structural 87/87 + 0 marker + M72 đúng variant; **Word visual NOT RUN (TCC)** → chờ P8a |
| G7 Excel | **PASS (pilot)** | M72 round-trip/negative/visual owner-approved; rollout chờ P6 |
| G8 A11y/viewport | **PASS** | keyboard/3 viewport/zoom 200% Wave C 87/87 |
| G9 Resilience/security | **PASS** | P3 suites + Class 9/14 fixes; draft xấu/Unicode/path hostile PASS |
| G10 Release hygiene | **PASS** | runner **47 PASS / 2 FAIL diagnostic / 0 critical NOT RUN — VERDICT PASS**; idempotency 17/0; allowlist cân; tree sạch |

**Kết luận P5R: 7 PASS / 3 PARTIAL — CHƯA tuyên bố CORE_APP_DONE.** Blocker duy
nhất ngoài scope code: P8a (quyền Word visual) + các owner packet
`docs/owner_decision_packet_2026-09-03.md`. Wave G (Windows): NOT RUN — không có
máy Windows. Wave H: chờ P5R đủ điều kiện.

## Wave P-owner — nhận owner decisions + phát hiện Class 16 (2026-09-03, ongoing)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| Owner decisions P1–P8 | Owner | P1=A, P2=A, P3=A, P4 có điều kiện, P5=B, P6=C, P7, P8a cấp quyền, P8b chờ máy; KHÔNG push | ✅ ghi decision_registry |
| Đồng bộ checkpoint | Lead | PLAN.md header 6ae63c2→cafb72d; decision registry § Owner decisions | ✅ |
| Pre-work P1 | Lead | nguồn đầy đủ M03/M04 (tách từ bản gốc) + `SOURCE_OVERRIDES` + drop_until chốt mục kế + xóa inserts superseded + numbering chain so mục POINTER (`Gửi kèm`); regen M03/M04 = 124/144 fields; runner 46/0/0 @ `5907066` | ✅ |
| Spawn 3 lane P1/P2/P3 | Lead | `fix-tails-m0304` (specs đuôi M03/M04), `fix-member-grids` (2 lưới M02 + N2–N5 M72), `fix-tax-m0306` (bảng thuế PLII_M03–06); ownership không chồng; đang chạy nền | ⏳ |
| P8a probe | Lead | `osascript` đọc Word OK (16.16.27) — TCC Automation mở | ✅ |
| **Class 16 phát hiện (BLOCKER G6)** | Lead | Word 16.16 từ chối template M02/M12/M03 ("corrupt"/"unreadable", có recovery, Word từng crash); M01 mở OK; bisect: bỏ band+tax VẪN corrupt; nguồn gốc M12 CŨNG corrupt → lỗi thừa kế từ serialization nguồn convert cũ; LO/lxml/textutil/XSD ECMA-376 đều PASS → gate structural mù. Word-open pilot "10/10" TRÚNG THỰC HÓA lại (user phải bấm OK/Yes hộ) | ❌ OPEN |
| Hướng xử lý Class 16 | Lead | phiên chuyên trách: recovery-diff (Yes → save repaired → diff XML) HOẶC chuẩn hóa nguồn qua LO round-trip rồi regen; sau đó mới chạy Word-open 87/87 tự động (kèm auto-dismiss dialog qua Accessibility) | ⏳ |

## Wave P-owner lanes — P1/P2/P3 merge + pin sync @ main 5907066→de158c4 (2026-09-03)

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| **P1 fix-tails-m0304** (`3aa4989`) | lane | M03 mục 8–11 / M04 mục 10–13 auto-map chuẩn (124/144 fields); thuế/BHXH/CSHL/NĐDPL xác nhận theo nguồn; `test_m0304_tails` 10/0; chk_co/chk_khong trùng BOT↔CSHL → Lead sửa generator | ✅ merged |
| **P2 fix-member-grids** (`dfb6c14`) | lane | 2 lưới thành viên M02 + 4 lưới M72 N2–N5 — nested-grid; **digit-run + STT-glue = 0**; `test_member_grids_rebuild` 18/0; trim Superscript preservation | ✅ merged |
| **P3 fix-tax-m0306** (`a282f76`) | lane | **PLII_M03–06 KHÔNG có bảng thuế trong nguồn** — Class 6 premise false; 4 spec PIN BLOCKED; `test_tax_m0306_rebuild` 7/0 | ✅ merged |
| Pin sync 9 suite | Lead assistant | `de158c4`: 7 files +376/−87; p1_c REGIONS 4→6; p1_b spec 5 entry + 9 w:tbl; m72_export table counts; industry_change EXTRA_LOOPS +4; household M02_OCCURRENCES 4→6; H7 +4 entries | ✅ |
| **Checkpoint** | Lead | L1 **exit 0** (Class 12 GIẢI QUYẾT) · numbering **exit 0** · idempotency **17/0** · runner **48 PASS / 1 FAIL diagnostic / VERDICT PASS** @ `de158c4` | ✅ **GATES XANH** |
| Coverage totals | Lead | IV 33 · BLOCKED 37 · NO_TABLE 7 · MISSING 24 · PARTIAL 4 · OUTPUT_ONLY 6 = **111** | ✅ |
| Word corrupt (Class 16) | Lead | **Mitigated at export layer**: LO normalize trong Bridge.export → user nhận Word-compatible .docx + .pdf; template gốc vẫn corrupt nếu mở trực tiếp | ⏳ mitigated |
| PDF export | Lead | `payload.format = docx|pdf|both` (mặc định both); LO headless convert; ZIP chứa đúng định dạng; soffice không có → fallback .docx | ✅ `aeb9fad`+ |

## Phase 5R — Word/DOCX Layout Remediation @ main 403ca1a→93d69f0 (2026-09-03/04, Lead + 3 lane)

Baseline dirty Phase 5 WIP được Lead xác minh (targeted tests xanh) và commit
`b7e4ef4`; gate visual dựng tại `c9d095e` + `18d7101`; baseline RED 455 records
/ 244 FAIL đo tại `generated_ho_so/_visual_layout/phase5r_gate/baseline_c9d095e/`.

| Task | Owner | Evidence | Trạng thái |
|---|---|---|---|
| 5R0 gate visual | Lead | `phase5_fixtures.py` (5 fixture semantic, validator V1–V4 chặn dummy tick tràn, selftest 436/436); `phase5_visual_gate.py` (export Bridge→LO→PDF→PNG từng trang + 12 detector D1–D12 + manifest hash/verdict); `test_phase5_visual_detectors.py` 12/12 hai chiều (docx/pdf tổng hợp, injected defect phải bị bắt); registry `phase5r_expectations.json` | ✅ |
| Lane A metadata/boundary | `agent/p5r-metadata` (5 commits, merge `c7ff269`) | WLAY-001 `_drop_source_indicators` (44/44 marker body-level, 0 trong bảng, byte-identical khi không marker); WLAY-006 generator `drop_flat_field_code_paras` + guard `_strip_flat_field_code`; WLAY-007a trailing empty (→5R4 mở rộng drop run); WLAY-007b `drop_foreign_annex_tail` cắt banner PHỤ LỤC khác phụ lục; `test_phase5r_metadata` 15/15 đỏ→xanh | ✅ merged |
| Lead regen sau A | Lead | content-aware save (`save_template_content_aware` — chống churn zip); regen idempotent run4==run5 zero-diff document.xml 87/87; manifest EVOLVED_FORMS +M28/+M80; allowlist H7 sync | ✅ |
| Lane B signature | `agent/p5r-signature` (merge `4de74b4`) | Census 87 form → registry 78 entry có evidence (2 BLOCKED_OWNER M14/PLII_M17); M70 spec 1x2 + render guard `_horizontal_signature_tables`; `_keep_signature_blocks` keepNext/keepLines/cantSplit; `_ensure_signature_space` vùng viết theo contract (M15 6.4pt→≥40pt); orphan policy (9 trang BLANK baseline biến mất); `test_phase5r_signatures` 6/6 | ✅ merged |
| Lane C tables | `agent/p5r-tables` (merge bfd680c + lead commit) | Census 12 bảng ≥10 cột; landscape LOẠI bằng evidence (0/87 nguồn landscape); width_policy='content' 12/12 (Lead hoàn tất M10 path legacy + regen); render pin tblHeader/cantSplit/tblW idempotent; M12: 5 matrix materialized OK, 3 BLOCKED_OWNER (`phase5r_table_policies.json`); `test_phase5r_tables` 10/10 | ✅ merged |
| 5R4 typography/orphan | Lead | Trailing-empty drop TOÀN BỘ run (M05 14 para rỗng → trang trắng); footnote keepLines (M80 xẻ câu); D6 vocabulary generic caps-line (M14 false positive); fix gate stale-move (run kill để evidence cũ bị analyze nhầm) | ✅ |
| **GATE FINAL** | Lead | `generated_ho_so/_visual_layout/phase5r_gate/final/` — **455/455 records (91 form × 5 fixture) 0 gate-fail, exit 0**; 1644 trang render PNG; D1..D12 = 0; 0 export error; Word 16.16.27 open-direct **91/91 PASS** (`word_open_inventory.json`); runner VERDICT PASS; coverage drift=0; L1/numbering/idempotency xanh | ✅ |
| Lane D audit độc lập | `agent/p5r-audit` (read-only detached @ d1bc538) | **OVERALL: PASS-WITH-NOTES** — Không phát hiện gian lận gate (diff review 24 commits: 0 assertion hạ/always-true, threshold không bị nới, 0 nhánh hard-code theo form, allowlist không có miễn trừ ngầm); hash-verified 6 records + 1607/1607 PNG tồn tại; visual 3 PNG bằng mắt PASS (M70 ngang, M15 vùng viết, M80 sạch). 3 finding: **F1** bug sectPr (61c8068 cắt mất sectPr trên path sparse — fix giữ span cuối + đăng ký 3 suite 5R vào runner 54→57); **F2** regen drift (11 template width_policy chưa regen + form_maps first/last-wins + docx_to_blocks matcher M70 1x2 — fix: first-wins + SOURCE_OVERRIDES skip alias + matcher/verifier horizontal + cellLabel trải cột + FORM_TABLE_CONTRACTS sync + regen đầy đủ rebaseline census/policies/fixture); **F3** trung thực: reviewer_verdict NOT_REVIEWED 455 + 647 candidates pending (đúng hợp đồng WLAY-012 — sign-off người dùng còn OPEN) | ✅ fixed @ f51f218 |
| **GATE FINAL (re-run trên HEAD f51f218 sau fix Lane D)** | Lead | **455/455 records, 0 gate-fail, exit 0; 1644 trang PNG; Word 16.16.27 91/91 PASS_OPEN_DIRECT; runner 57 PASS / 0 FAIL**; tree sạch | ✅ |

**Còn OPEN/BLOCKED sau 5R (trung thực):** WLAY-011 glue = census 553 candidate
(chủ yếu artifact trích xuất PDF của ô bảng kề nhau — chưa adjudicate từng
nhóm); WLAY-005 = 3 matrix M12 BLOCKED_OWNER chờ owner; 2 entry orientation
BLOCKED_OWNER (M14, PLII_M17); min_write_gap 40pt mới pin cho M15 (các form
khác đo 27.3pt là census); Windows/.exe = NOT RUN. Reviewer verdict trong
manifest mặc định NOT_REVIEWED — auditor độc lập (Lane D) review thay.

## Phase 6V — Visual toàn mẫu & tính tỉ mỉ @ main 9dce60e→310f868 (2026-09-04, PLAN v6)

Baseline: audit 3 lớp 2026-09-04 trên HEAD 294604c (B1–B5 visual + I1–I4 hạ
tầng; số liệu trong PLAN v6 mục 1). Sự kiện gate đỏ giả 56/1 = va chạm profile
LibreOffice mặc định (worktree song song + .lock/zombie sót) — đã chẩn đoán
kín bằng profile cách ly exit=0, backup profile hỏng
`~/Library/.../LibreOffice/4/user.wedged_20260904`.

| Task | Owner | Branch/Worktree | Kết quả & evidence | Trạng thái |
|---|---|---|---|---|
| V0.1 profile soffice cách ly + retry + LO_CRASH/LO_PROFILE_BUSY | `agent/6v-infra` | 6v-infra `003c3dd` | helper `_run_soffice` per-call `/tmp/lo_prof_<case>_<pid>`; 4 unit mock + E2E export OK | ✅ merged |
| V0.2 PNG per-record + assert đĩa==manifest | `agent/6v-infra` | `4b10169` | `<fixture>/<tag>/<FORM>/page-NN.png`; M72 5 biến thể tách 8/3/2/2/4 trang; assert exit 2 khi lệch (test thiếu/thưa 3/3) | ✅ merged |
| V0.3 summary hai lớp hard-fail/candidates | `agent/6v-infra` | `62ec9e7` | stdout `HARD-FAIL: X` / `CANDIDATES: Y`; summary.json hard_fail_counts + candidate_counts + candidate_ids | ✅ merged |
| V0.4 preflight runner quét soffice sống | `agent/6v-infra` | `109c1d2` | WARNING `!` dòng đầu + JSON `soffice_preflight_warnings`; không đổi verdict | ✅ merged |
| V0.5 suite test_export_concurrency + fix out_dir collision cùng giây | `agent/6v-infra` | `fbb775e` | **Gốc rễ thứ 3 của sự kiện 56/1** (agent tự phát hiện): `Bridge.export` mkdir exist_ok=True cho 2 run cùng case_id cùng giây ghi chung out_dir → norm_dir bị xóa dưới chân soffice; fix exist_ok=False + vành đai `_p<pid>`; suite 8 PASS ~20s, 2 bộ profile riêng | ✅ merged |
| V0-Lead sandbox pid suffix + allowlist | Lead | `5cceeac` | `test_phase5r_signatures` sandbox cố định `/tmp/p5r_laneB_*` khiến 2 runner song song đỏ giả (rmtree lẫn nhau) — pid suffix; allowlist +`tools/test_export_concurrency.py` (H7.4 57/0) | ✅ merged |
| **GATE V0** | Lead | merge `310f868` | (a) 2 runner song song `--only test_phase5r_signatures` **2 PASS** (exit 0 cả hai); (b) corpuscheck `phase6v/v0_corpuscheck`: 455 records / 0 export error / **PNG claim=disk=1644** (tái lập con số sự kiện 1567/1644); (c)(d) runner full trên main + summary hai lớp — kết quả ghi tại checkpoint dòng này | ✅ |

### V1 — Detector mở rộng + baseline ĐỎ @ main 1bc4c40 (2026-09-04, Lead review PASS)

| Task | Owner | Kết quả & evidence | Trạng thái |
|---|---|---|---|
| D13 skeleton glue / D14 name-slot / D15 chk glyph / D16 token value / D9 hai tầng | `agent/6v-detectors` (6 commits, merge `1bc4c40`) | Baseline ĐỎ trên corpus v0_corpuscheck 455 record: **D13 323 rec/1104 hit/77 form** (55 form date-glue khớp audit; +22 form contact/paren cùng gốc rễ B1); **D14 14 form RED** + registry handwriting rỗng; **D15 17/17 form chk RED (191 hit)**; **D16 355 rec/8846 hit/82 form**; **D9 NARROW_COL_WIDE 60 bảng/10 form khớp 100% audit B5, sàn legacy 566 đóng I4**. Suite pin 7/7 + negative mutations; verdict candidates-only (V1g). `tools/census/6v_v1_baseline.json` = bảng per-form đối chiếu audit | ✅ merged |
| Lead amendment | Lead `f435ee6` | detector_keys legacy +D13–D16 (Esc2); allowlist 4 file (H7.4 57/0); hồi quy test_phase5r_tables 10/0 | ✅ |

**Quyết định Lead khi merge V1:**
1. **D14 grammar giữ nguyên** (chat, pin): scope V2-C2 = **14 form** (PLII_M08/10/11/12/13/19/21/22/23/25/27/28, PLI_M43, PLI_M71). 5 form "slot nhận token kỹ thuật" (PLI_M05, PLII_M01/07, PLI_M73/74) do **C4** giải quyết (fixture realism → slot hiển thị tên thật; D16 về 0 xác nhận). Con số "~37" của audit 2026-09-04 là heuristic scan thô — bị supersede bởi D14 grammar chặt.
2. **test_phase6v_detectors CHƯA đăng ký release_runner**: suite phụ thuộc corpus `generated_ho_so` (gitignored, local-only) — đăng ký sẽ làm runner máy-dependent hoặc skip lặng. Lead chạy thủ công tại mỗi merge; xem lại chiến lược corpus ở V5.
3. Esc1 (`_count` keys rơi candidates): xử lý khi nâng hard ở V2. Esc4 (FP tiềm ẩn D15): theo dõi qua adjudicate V4.

**Gate V1:** ✅ baseline đỏ khớp audit (mọi lệch có giải thích per-form trong JSON) · ✅ negative mutations 7/7 · ✅ corpus không đụng · ✅ runner không đổi · ✅ ownership sạch. Full runner main sau merge: xem checkpoint docs kế tiếp.

### V2 (phần 1/2) — C4 fixture + C1 glue merged @ main a59c36e→d746390 (2026-09-04, Lead review PASS)

| Task | Owner | Kết quả (Lead kiểm chứng độc lập) | Trạng thái |
|---|---|---|---|
| C4 fixture realism | `agent/6v-fixture` (merge `a59c36e`) | ValueFactory default → giá trị TV thật (272 cặp key\|label), D12 giữ; selftest 437/0; subset 11 form: D16 3742→16 (16/16 là FP dòng `_____`); D14 5 form slot-nhan-token XANH | ✅ merged |
| C1 normalize skeleton glue | `agent/6v-glue` (merge `07cf007`) | rule chèn space quanh {tag} (census 3 ví dụ bản giấy, docstring); regen 81/87 template, regen×2 zero-diff (Lead chạy lại 17/17); 0 non-glue text diff (Lead đối chứng PLII_M08: 4 run, thuần space); D13 subset 10 form tệ nhất = 0 | ✅ merged |
| D16 grammar v2 (Lead) | Lead `d746390` | bỏ FP dòng toàn gạch dưới (đường điền bản giấy) — pin 355/8846 → 342/8751 + mutation mới; suite 7/7 | ✅ |
| Kiểm chứng kết hợp | Lead | subset 5 form × 2 fixture export trên main (C4+C1 cùng lúc): **D13 = 0, D16 = 0** | ✅ |

**Phân định 4 suite tranh chấp C1** (Lead chạy trên main@66ba61d): p2a 13/1
FAIL, r3b1 FAIL (PLI_M12 anchor 137≠144 + 2 BLOCKED), w1 FAIL (PLI_M70 grid),
member_grids PASS — **giống hệt branch C1 = pre-existing từ 5R**, không do C1.
Các suite này NGOÀI release_runner (lane-level, known-open) — chuyển thành
backlog adjudicate ở V4, không chặn V2.

**Trạng thái B:** B1 CLOSED-pending-corpus (D13=0 subset; corpus full chốt ở
V2-final) · B4 PARTIAL→CLOSED-pending-corpus (value 0 + grammar v2; wrap không
còn nguồn) · B2 chờ C2 (14 form, đã mở khoá sau C1) · B3 chờ Q-V1 · B5 chờ
Q-V2 (V3). C2 được phát prompt tiếp theo.

### V2 (phần 2/2) + audit đêm — C2 + C3 merged, V2 ĐÓNG @ main 12b9615→6214ae3 (2026-09-04/05)

| Task | Owner | Kết quả (Lead kiểm chứng độc lập) | Trạng thái |
|---|---|---|---|
| Corpus scoreboard full 455 record @9fb707c | `agent/6v-corpus` | gate exit 0, 0 export error, PNG 1663/1663 khớp; **D13 323/1104/77→0, D16 342/8751/82→0, D11 201→0** (C4+C1 toàn corpus); D14 14→13 (PLI_M71 tự xanh do C1 sửa paren-glue); D15/D9 giữ đúng chờ C3/V3; v0-rerun khớp pin (apples-to-apples) | ✅ |
| Auditor độc lập V0→C4/C1 | `auditor/6v-core` (report `docs/audits/6v/v2-core-audit.md`) | **OVERALL PASS** — Q1–Q4 PASS, Q5 PASS-WITH-NOTES; 0 BLOCKER/MAJOR; 4 finding (F1 nhãn I4, F2 JSON stale, F3 transient run_export NIT, F4 PNG-assert ngoài runner NIT); đã cherry-pick-revert test chứng minh test đỏ thật | ✅ F1/F2 xử `6214ae3`; F3/F4 theo dõi |
| C2 name-slot 14 form | `agent/6v-nameslot` (merge `12b9615`) | engine name_slots data-driven + 14 spec + regen; Lead rerun evidence: 14/14 D14=0, slot render tên thật; idempotency 17/17 | ✅ merged |
| C3 chk glyph (Q-V1) | `agent/6v-chk` (merge `27d7b90`) | run w:bdr 4 cạnh + X (không font-glyph), UI vuông hóa; Lead rerun: suite 7/7 pin giữ, D15 subset = 0 hit (cả 2 lớp), test_dom 58/0 | ✅ merged |
| Auditor findings F1–F4 | Lead `6214ae3` | F1 nhãn I4 ĐÃ ĐÓNG; F2 rebaseline JSON + grammar_version; F3 (transient FileNotFoundError run_export 2-fixtures-1-process, không tái hiện, cùng vùng I5) + F4 (tái chạy PNG-assert đĩa==manifest ở V5 trước khi CLOSE I2) — theo dõi | ✅ |

**Trạng thái B sau V2 (định lượng):** B1 CLOSED (full corpus 0) · B2 CLOSED
(14/14 form, subset = full scope) · B3 CLOSED-pending-corpus (subset 0; xác
nhận toàn corpus ở gate V3-final) · B4 CLOSED (full corpus 0) · B5 → V3.
Còn lại cho V4: D6 candidate 157, D5 68, WLAY-011 adjudicate, D15/D9 chốt
sau V3. Runner chính thức sau merge: xem dòng checkpoint kế tiếp.

**Runner chính thức sau V2-final (main @ HEAD): 58 PASS / 0 FAIL / 0 NOT RUN**
(57/1 tạm thời do lane C2 bỏ sót allowlist 14 file — runner H7.4 bắt đúng,
Lead bổ sung `ea6e7f0`+1; tái chạy 58/0.)

### V3 — Bảng rộng landscape @ main 1c111db (2026-09-05, Lead review PASS)

| Task | Owner | Kết quả (Lead kiểm chứng độc lập) | Trạng thái |
|---|---|---|---|
| Landscape section bảng ≥10 cột (Q-V2) | `agent/6v-tables` (merge `1c111db`) | 12 bảng/10 form, sàn 900tw, tổng 14400; form_maps/blocks 0 byte đổi; 190/190 trang ngang đo 792×612; word-open 10/10 PASS_OPEN_DIRECT; chống trang mồ côi ranh giới section (commit 97bed57) | ✅ merged |
| Gate V3-final full corpus | agent + Lead rerun | 455r, exit 0, HARD 0, 0 export error, PNG 1619/1619; **D9 60→0 (B5 CLOSED)**; D13/D14/D16 giữ 0; D5 68→60; D6 157→155 (+1 PLI_M02 WRITE_SPACE 27.4pt do reflow — vào hàng adjudicate V4) | ✅ |
| D15 residue 16 hit | agent điều tra + Lead verify | **X_OWN_LINE, residue lane C3/B3**: {chk} nằm paragraph riêng (layout template gốc) — M03/M05 Lead đã rerun xác nhận; 6 form landscape có chk-paragraph byte-identical main → KHÔNG phải hồi quy V3. Chuyển mini-lane 6v-chkline | ⏳ mini-lane |

**Runner sau merge: 58 PASS / 0 FAIL / 0 NOT RUN.** B5 CLOSED. B3 còn đúng
lớp X_OWN_LINE 16 form choice-variants (BARE_X = 0 toàn corpus — cơ chế ô
vuông của C3 hiệu lực toàn corpus).

### V2 B3-residue — mini-lane 6v-chkline @ main ea60397 (2026-09-05, Lead review PASS)

| Task | Owner | Kết quả | Trạng thái |
|---|---|---|---|
| Gộp 140 chk-own-paragraph vào dòng nhãn (16 form) | `agent/6v-chkline` (merge `ea60397`) | 140/140, box-first (đúng layout gốc "☐ nhãn"); agent tự bắt lỗi wrap ở vòng 1 và tự sửa chiều; Lead rerun D15 = **0/17 form** + probe "X Thành lập mới" same-line; suite 7/7, idempotency 17/17, H7.4 57/0 (lane chạy H7.4 TRƯỚC khi báo — đã học bài C2) | ✅ merged |
| **B3 CLOSED** | — | D15: 191 → 16 → **0** (subset; full corpus xác nhận ở gate V4-final) | ✅ |
| Phát hiện ngoài lane "M72 regen drift" | agent báo; Lead kiểm chứng | **FALSE ALARM** — agent chạy thiếu bước `tag_m72_sections` trong pipeline; Lead chạy đủ 3 bước: committed tái lập **340/340 text-run + 5/5 markers**. Ghi nhận quy tắc: regen M72 LUÔN đủ build → tag_m72_sections → docx_to_blocks | ✅ đóng |

**Runner sau merge: 58 PASS / 0 FAIL / 0 NOT RUN.** B1–B5 toàn bộ CLOSED
(B3 chờ xác nhận full corpus tại V4-final). V4 mở: chỗ ký 40pt (155 cụm),
micro-census 91 form, FIELD_META hint UI, adjudicate D6-155/D5-60/WLAY-011.

### V4 (phần 1) — signgap + micro merged @ main 0ca9fdf→HEAD (2026-09-05, Lead review PASS)

| Task | Owner | Kết quả (Lead kiểm chứng độc lập) | Trạng thái |
|---|---|---|---|
| Sàn vùng viết 40pt toàn corpus + D6 write-gap → HARD | `agent/6v-signgap` (merge `0ca9fdf`) | registry 78 entry; M70 bake 800twips; evidence 12 form × 2 fixture **0 form-fixture dưới chuẩn** (Lead rerun); H7.4 57/0 (kể cả dọn 1 entry manifest trùng); exception ownership test_phase5_visual_detectors = pin sync D6 hard — Lead duyệt | ✅ merged |
| Micro-census 7 nhóm + FIELD_META hint UI | `agent/6v-micro` (merge `ceb14be`) | census read-only: a=75 trộn kiểu điền / f=53 band lệch / d=31 sup / e=14 STT lạc đơn / c=9 font<8pt / g=8 viền-pad / b=4 ngoặc (bằng chứng cho đợt fix kế tiếp); UI +28 key meta + placeholder hint; node dom 64/0, domain 65/0, form_flow 38/0 | ✅ merged |
| Conflict allowlist 2 lane | Lead | union 2 block; lane micro bỏ sót `app_web/test_dom.js` (+6 assertion) → runner H7.4 bắt đúng, Lead bổ sung | ✅ |
| Runner sau merge | Lead | **58 PASS / 0 FAIL / 0 NOT RUN** | ✅ |
| Gate V4-final full corpus | Lead (đang chạy) | kỳ vọng: exit 0, D6 write-gap hard = 0, D15 = 0 (xác nhận B3 toàn corpus), D13/D14/D16 giữ 0, PNG==disk | ⏳ |

**Hàng đợi V4 còn lại (từ micro-census):** fix theo nhóm a/f/d/e/c/g/b (cần lane
tiếp theo sau khi auditor/6v-visual adjudicate mức "lỗi thật vs chủ đích bản
giấy" — nhóm f=53 phần lớn "so-line không cần phép" theo ghi chú census).

### Gate V4-final — full corpus @ HEAD 374ea29 (2026-09-05, Lead chạy trực tiếp)

**exit 0 · 455 record · 0 export error · PNG 1612/1612 khớp đĩa ·
HARD-FAIL 0 · CANDIDATES 71 (chỉ D5_blank_sparse 72 hit).**

| Detector | V0 baseline | V4-final |
|---|---|---|
| D13 skeleton glue | 323 rec | **0** |
| D14 name-slot | 14 rec | **0** |
| D15 chk glyph | 191 hit | **0** (B3 xác nhận toàn corpus) |
| D16 token values | 8751 hit | **0** |
| D9 table grid (WIDE) | 60 bảng | **0** |
| D6 signature (write-gap nay HARD) | 155 cand @27.3pt | **0 hard + 0 cand** (≥40pt toàn corpus) |
| D5 blank/sparse | 78 | **72 — lớp duy nhất còn, chờ auditor adjudicate** |

(Số trang 1619→1612: reflow sau spacer 40pt — assert đĩa==manifest vẫn ok.)

### V4b + Gate V4-final-2 — ĐẠT G-B TUYỆT ĐỐI @ main d66b26a (2026-09-05)

| Task | Owner | Kết quả | Trạng thái |
|---|---|---|---|
| 10 việc fix theo adjudication (D5 6 hit, vỡ token, STT, ngoặc, separator, M12-dot, fixture, census regex, D5 allowlist, Mẫu số registry) | `agent/6v-v4fix` (merge `177cd2f`) | xem commit message từng việc 1–10; lane tự khai manifest (H7.4 57/0) | ✅ merged |
| Lead rebaseline sau longest-word | Lead `9dad012`+`d66b26a` | WIDE_TABLE_FIXTURE + policies min_col 954/918/909/928 (cố ý); 3 fragment p−1 (M06/M08/M78 gộp đoạn); manifest rebuild; allowlist +2 fragment + dedupe → tables 10/0, manifest_deep exit 0 | ✅ |
| **Gate V4-final-2 (v4b_corpuscheck)** | Lead | **exit 0 · 455 record · 0 export error · HARD-FAIL 0 · CANDIDATES 0** · PNG 1631/1631 — **G-B đạt: 0 hard + 0 candidate chưa adjudicate**; 3 form từng vỡ token = 0 mảnh vỡ (Lead đo lại) | ✅ |
| Runner | Lead | **58 PASS / 0 FAIL / 0 NOT RUN** (sau 3 vòng bắt pin-stale/allowlist — gate làm đúng vai trò) | ✅ |

**V4 ĐÓNG.** Tất cả detector D1–D16 = 0 hard + 0 candidate trên toàn corpus.
Sang V5: auditor/6v-export + auditor/6v-release, sau đó checkpoint đóng 6V.

### V5 — audit độc lập 3 tầng + final corpus (2026-09-05)

| Auditor | Verdict | Điểm chính (Lead đã đọc toàn văn) |
|---|---|---|
| `auditor/6v-core` (V2) | **PASS** (0 BLOCKER/MAJOR) | báo cáo gốc mất trong dọn worktree (lỗi Lead) — phục hồi rút gọn `docs/audits/6v/v2-core-audit.md`; F1/F2 fix `6214ae3`; F3 theo dõi; **F4 đóng bởi export auditor** |
| `auditor/6v-visual` (V4) | **PASS-WITH-NOTES** | `v4-visual-audit.md` (commit `960d0b2`) |
| `auditor/6v-export` (V5) | **PASS-WITH-NOTES** | **word-open 91/91 THẬT trên corpus 6V (Word 16.16.27)**; determinism PASS (chỉ lệch timestamp metadata); ZIP PASS; PNG==đĩa 455/455 (đóng F4); E2E từ UI-data PASS (tên đúng slot, ☒ đúng, bảng đủ dòng); 2 note LOW (F-V5-2 heuristic D15 khi dòng bảng wrap — không phải lỗi nhìn thấy; F-V5-3 registry nhóm loại-trừ M15) |
| `auditor/6v-release` (V5) | **PASS-WITH-NOTES** | tái lập từ worktree sạch: 58/0/0 + 7/7 + exit 0, **0 con số lệch** so ledger; repro song song 2 PASS. Gate: G-A PASS · G-B PASS · G-C PASS-WITH-NOTES · G-D PARTIAL (word-open 6V đã có từ export auditor + determinism PASS + final corpus đang chạy — đóng sau) · **G-E CHƯA ĐẠT (reviewer_verdict 455/455 NOT_REVIEWED — cần NGƯỜI duyệt, bàn cho owner)** · G-F PASS-WITH-NOTES |

**Hiệu chỉnh trung thực theo F1 (release auditor):** phát biểu "V4 ĐÓNG"
(ledger/commit de86570) cần đọc là **"V4 ĐÓNG ở scope detector/G-B"** —
Gate V4 PLAN còn 3 điều kiện ngoài detector: reviewer_verdict 100% (=G-E,
bàn owner), micro-census nhóm a=75 registry per-family (chờ owner đối chiếu
bản gốc — Q-V8 tinh thần đã chốt giữ nguyên), UI checklist 5.2 đầy đủ
(mới có FIELD_META hint, chưa sweep). Không thay đổi kết luận kỹ thuật.

**Backlog còn lại sau 6V (không chặn):** F-V5-2/3 (LOW) · vỡ token mã
13-chữ-số cột hẹp M09/M72-tnhh (G-C note b — chờ owner) · UI sweep 5.2 ·
WLAY-005 M12 3 matrix · Q-P4-1 min_rows · suite known-open 5R (p2a/r3b1/w1,
header_layout PLI_M28) · Q-V6 Windows packaging.

### V5-final — final corpus + ĐÓNG PHASE 6V (2026-09-05)

**Corpus chuẩn bàn giao:** `phase6v/final/` — 455 record, exit 0, HARD 0,
CANDIDATES 0, PNG 1631/1631 (F6 đóng → G-D PASS: final corpus + word-open
91/91 thật [export auditor, cùng nội dung HEAD] + determinism PASS + hash
trong manifest). **G-E human sign-off còn mở — bàn owner** (455/455
NOT_REVIEWED, đúng thiết kế cần người duyệt). Checkpoint đóng ghi header
PLAN.md. Tổng commit 6V: V0 310f868 → V1 1bc4c40 → V2 a59c36e/07cf007/
12b9615/27d790 → B3r ea60397 → V3 1c111db → V4 0ca9fdf/ceb14be → V4b
177cd2f/9dad012/d66b26a → V5 8ccce9b → final.
