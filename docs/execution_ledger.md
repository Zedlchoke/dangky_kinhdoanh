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
| X6 phiếu Excel mẫu PLI_M72 | Lead | `generated_ho_so/_visual_layout/excel/PLI_M72_phieu_mau.xlsx` + preview HTML; reload-kiểm openpyxl PASS (protection ON, sheet ẩn ___map, 65 hàng). **NOT RUN: mở bằng Excel thật — máy dev không có Excel, chờ owner duyệt hình** | ⏳ chờ owner |
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
