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
