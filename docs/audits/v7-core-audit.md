# AUDIT ĐỘC LẬP WAVE v7 — v7_core_audit

- Auditor: độc lập (không phải agent wave v7). READ-ONLY production; toàn bộ lệnh chạy TUẦN TỰ, mỗi suite chạy 1 lần, không có lần chạy lại nào cần thiết (0 đỏ).
- Range: `000e8e2..HEAD` (branch main, HEAD = `a7240e5`). Wave commits thực tế: 9 (7 như lệnh + `d12e9d0` gate-fix + `a7240e5` PLAN checkpoint).
- Working tree SAU toàn bộ gate runs: sạch (`git status` rỗng) — `build_manifest --deep` tái sinh deterministic, 0 drift.

## 1. Verdict từng mục

| # | Mục | Verdict | Bằng chứng (exit code thật) |
|---|---|---|---|
| 1a | Diff review — generated đi qua generator | **PASS** | 75 file đổi, 0 deleted/renamed. 20 blocks + 20 templates khớp ĐÚNG tập 20 form trong `tools/header_name_binding.json`; `form_maps.json` KHÔNG đổi. Blocks diff (vd `app/data/blocks/PLI_M13.json`) chỉ thêm run `mirror` — đúng converter `_band_first_cell_to_mirror`. `test_header_layout.t_fields_unchanged` tái lập đúng logic production (đối chiếu `build_form_maps.main()`: `setdefault` first-wins + skip SOURCE_OVERRIDES tại dòng ~4265 — khớp). |
| 1b | Không nớt/xóa assertion để làm xanh | **PASS-WITH-NOTES** | 40 pin đổi đều có replacement + comment premise→evidence (`[Pin sync — PLAN v7 F0.5]` p2a/r3b1; `[v7-F0]` header_layout; 40→72 trích quyết định owner). 2 điểm ghi NOTE-1, NOTE-4 dưới. |
| 1c | `audit_expected_diff_files.txt` provenance | **PASS** | +21 dòng, 3 khối comment provenance ([6V-FINAL 000e8e2], [v7-checkpoint 77b992a], [WAVE v7]); khối cuối +8 file khớp commit `d12e9d0` "H7 +8 file wave v7". |
| 1d | `audit_blocks_check.py` mirror có validate shape | **PASS** | Thêm `ALLOWED_RUN_KEYS_MIRROR` + validate: `mirror` phải `{'key': <str>}` không rỗng, cấm key lạ, cấm lẫn `text`/`input`; nhánh else chỉnh `text`/`mirror` (tools/audit_blocks_check.py:736-786). |
| 2 | 10 gate chạy lại tuần tự | **PASS 10/10** | Bảng chi tiết mục 2 dưới — tất cả xanh lần chạy đầu, không cần rerun. |
| 3 | Corpus manifest | **PASS** | `phase7v/final/manifest.json`: records 455; `reviewer_verdict` = NOT_REVIEWED ×455 (0 PASS giả); `png_disk_assert` ok=true 1653==1653 mismatches []; `export_errors` []; gate_fails 0 / gate_candidates 0 / D17 fails 0 trên 455 records. |
| 4 | Secret/privacy | **PASS-WITH-NOTES** | 0 secret/API key/private key trong diff (các hit "token" là token-placeholder `{key}` của mẫu); 0 file `profiles/*.json_*` mới; 1 hardcoded path — MINOR-1. |
| 5 | Registry nhất quán | **PASS** | `tools/header_name_binding.json`: 20 forms + 2 blocked_owner; PLI_M33/PLII_M06 KHÔNG trong forms; cả 20 entry đủ `key` + `reason`; 2 blocked_owner có reason pháp lý cụ thể. |

## 2. Gate chạy lại — kết quả thật

| Suite | Kết quả | Exit |
|---|---|---|
| `python3 -X utf8 -m tools.test_phase6v_detectors` | 10 PASS / 0 FAIL (gồm V2c D17 mutations) | 0 |
| `python3 -X utf8 -m tools.test_v7_header_name` | 8 PASS / 0 FAIL (E1–E8) | 0 |
| `python3 -X utf8 -m tools.test_phase5r_signatures` | 6 PASS / 0 FAIL | 0 |
| `python3 -X utf8 -m tools.test_header_layout` | 11 PASS / 0 FAIL | 0 |
| `python3 -X utf8 -m tools.audit_blocks_check` | sạch (chỉ note mức-2) | 0 |
| `node app_web/test_audit_wave_h_negative.js` | 57 PASS / 0 FAIL | 0 |
| `node app_web/test_dom.js` | 69 PASS / 0 FAIL | 0 |
| `python3 -X utf8 -m compileall -q app_web app_tk tools` | — | 0 |
| `python3 -X utf8 -m tools.census.build_manifest --deep` | GATE PASS 87/87, unclassified 0 | 0 |
| `python3 -X utf8 -m tools.census.table_coverage_audit --no-write` | GATE PASS — no drift | 0 |
| Runner report `/tmp/final_v7_final.json` | **63 PASS / 0 FAIL / 0 NOT RUN**, verdict PASS; env_errors [], soffice preflight []; tập suite khớp 1:1 `release_runner.SUITES` hiện tại (63) | — |
| `tools.census.v7_signature_census --corpus .../phase7v/final` | **VERDICT PASS**: census 420 = detector 420 (coverage_equal true); manual min 72.9pt / median 119.6pt / **<72pt = 0** | 0 |
| ZIP 455 docx (rglob corpus, `zipfile.testzip`) | 455/455 valid, 0 invalid | 0 |

## 3. Findings

**BLOCKER: không có. MAJOR: không có.**

- **MINOR-1** — `tools/census/header_name_census_report.py:27`: hardcode `/Users/hoangminhlong/orca/dangky_kinhdoanh` trong chuỗi metadata của report sinh ra. Chỉ là evidence script đọc/ghi /tmp, không ảnh hưởng runtime app; nhưng vi phạm đúng chữ rule hygiene "production tree không hardcode home path". Đề xuất: thay bằng `os.getcwd()`/tên repo.
- **MINOR-2** — `docs/phase6v_d5_sparse_allowlist.json`: metadata `by_class` stale — khai `{(i):50,(ii):9}` (tổng 59) trong khi thực tế `sparse_pages` có 64 entry với (i)=55,(ii)=9. `count: 64` đúng; grep toàn `tools/` không có consumer nào đọc `by_class` → chỉ sai metadata, không ảnh hưởng gate.
- **MINOR-3** — `docs/execution_ledger.md` mục Wave v7 dừng ở commit `481f5d6`: thiếu 4 dòng ledger cho `49fccbe`, `9f756f6` (commit evidence chính), `d12e9d0`, `a7240e5`. Bằng chứng của `9f756f6` đã được audit này xác minh độc lập trên đĩa (mục 4), nhưng sổ ledger cần bổ sung để truy vết.
- **NOTE-1** — `tools/test_phase5r_signatures.py:475` (B4): pin XML `len(spacers) >= 2` → `>= 1` là nới về hình thức. KHÔNG load-bearing cho màu xanh: render M15 hiện tại cho 4 dòng exact-height `[20,20,1380,1380]` (audit tái lập), M15 không có cụm "Đã ký" nên cả 2 cụm ký vẫn nhận spacer 1380 twips, và assertion PDF đo gap >= 72pt theo TỪNG instruction vẫn bọc cả 2 cụm.
- **NOTE-2** — Lệnh audit kỳ vọng runner "62 PASS"; thực tế **63** — `release_runner.SUITES` hiện định nghĩa 63 (F0.6 fold 4 legacy + `test_v7_header_name` + `test_export_concurrency`...), report khớp exact-set. Con số 62 trong lệnh đã stale, không phải defect.
- **NOTE-3** — Lệnh audit ghi "+2 commit gate-fix"; thực tế chỉ có 1 (`d12e9d0`) + PLAN checkpoint `a7240e5` = 9 commit tổng.
- **NOTE-4** — `docs/phase6v_d5_sparse_allowlist.json` +5 entry mới (59→64, lớp (i)) trong wave v7: spillover của spacer 72pt đẩy chú thích pháp lý (Tòa án/Trọng tài) sang trang sau vùng ký; mỗi entry có reason `[v7]` riêng. Corpus records xác nhận gate_fails=0/candidates=0 sau adjudicate — chấp nhận được, không phải che lỗi HARD.
- **NOTE-5** — `tools/census/table_coverage_audit.py` với `--no-write` vẫn in dòng "wrote docs/table_coverage_current.{json,md}" dù không ghi (kiểm `git status` sạch). Log gây hiểu lầm, đề xuất sửa log.
- **NOTE-6** — `word_open_verdict` trong manifest phase7v = NOT_RUN ×455 (trung thực, không giả PASS); bằng chứng Word-open thật nằm ngoài manifest: `/tmp/phase7v_word_open.log` "DONE: 91/91 PASS_OPEN_DIRECT" + 91 docx trên đĩa `generated_ho_so/_visual_layout/phase7v/word_open/phase5_word_open_*_20260905_221705/` (ZIP 91/91 valid — audit kiểm). Inventory JSON chi tiết nằm ở /tmp (ephemeral) — nên commit bản inventory để bằng chứng bền hơn.

## 4. Đối chiếu độc lập các claim của wave

- 72pt là quyết định owner: comment tại `tools/phase5r_expectations.json` (comment header), `tools/phase5_visual_gate.py` (SIG_WRITE_PT=72), `tools/test_phase5r_signatures.py:317` — nhất quán 3 nơi; 78/78 entry registry = 72, không entry nào < 72 (registry chỉ được pin CAO hơn sàn — detector dùng `max(72, pin)`).
- Corpus HARD 0 / candidate 0: đếm lại từ `manifest.json` 455 records (gate_fails/gate_candidates/D17 fails đều 0) — khớp claim `9f756f6`.
- Word 16.16.27 91/91: xác minh trên đĩa (NOTE-6).
- PNG 1653==đĩa: `png_disk_assert.ok = true`, mismatches rỗng.

## 5. Kết luận gate

- **G0–G2 (kỹ thuật: diff/hygiene diff + suite lõi + gate detector): ĐẠT** — mọi exit code 0, corpus HARD 0 / candidate 0, census 420=420 min 72.9pt.
- **G4–G5 (visual corpus + census/chống hồi quy): ĐẠT** ở mức kỹ thuật — D17 hard gate có mutation V2c; D6@72pt có mutation V2a/V2b; 2 defect H1/S1 đóng bằng fix gốc rễ 4 tầng 1 registry.
- **G3 (UI full sweep): CHƯA ĐẠT / CÒN MOỔ** — 2 BLOCKED_OWNER (PLI_M33, PLII_M06) + 3 ô output inline chưa bind chờ owner; sweep người dùng chưa thấy evidence trong wave.
- **G6 (human review corpus): NOT RUN** — reviewer_verdict NOT_REVIEWED ×455 (đúng thiết kế: không giả PASS; chờ reviewer ký).
- **G7 (Excel 3 cụm): KHÔNG ĐỔI BỞI WAVE v7** — 3 suite Excel trong runner PASS (test_excel_export/roundtrip/negative); không có evidence gate "3 cụm" mới trong wave, trạng thái kế thừa.
- **G8 (Windows): NOT RUN** — PLAN checkpoint `a7240e5` ghi rõ còn Windows; toàn bộ evidence wave v7 trên macOS.
- **G9 (audit này): PASS-WITH-NOTES** — 0 BLOCKER, 0 MAJOR, 3 MINOR, 6 NOTE.
- **G10 (hygiene): PASS-WITH-NOTES** — tree sạch sau mọi gate run, 0 secret, 0 profiles mới; còn MINOR-1 (hardcode path trong evidence script) + MINOR-2 (metadata stale) + MINOR-3 (ledger thiếu 4 dòng).

**Tuyên bố được: wave v7 ĐẠT gate kỹ thuật G0–G2, G4–G5.** Không tuyên bố G3/G6/G8 (đúng trạng thái còn mở như PLAN checkpoint đã khai); G7 kế thừa; G10 đạt kèm 3 MINOR không chặn.
