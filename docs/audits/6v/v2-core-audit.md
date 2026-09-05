# v2-core-audit — auditor/6v-core (bản PHỤC HỒI rút gọn bởi Lead)

> ⚠️ Bản gốc (177 dòng, worktree 6v-audit-core detached @c494ec8) bị mất
> trong đợt dọn worktree 2026-09-05 do Lead chưa commit trước khi remove —
> lỗi quy trình của Lead, ghi nhận trung thực. Nội dung dưới đây phục hồi
> từ execution_ledger (mục V2) + commit `6214ae3` đã xử findings, giữ nguyên
> verdict và số liệu đã được Lead verify độc lập tại thời điểm audit.

- Phạm vi: V0 hạ tầng + V1 detectors + C4/C1 (commit 9dce60e..c494ec8).
- 5 câu hỏi: Q1 LỚP ĐÚNG — PASS · Q2 TEST ĐỦ SỨC (cherry-pick-revert chứng
  minh test đỏ thật) — PASS · Q3 REGEN ĐỨNG VẶN — PASS · Q4 GATE TRUNG THỰC
  (record_verdicts không nới) — PASS · Q5 SỔ SÁCH — PASS-WITH-NOTES.
- 4 findings: F1 (MINOR) nhãn I4 còn "[OPEN]" dù đã đóng → Lead fix
  `6214ae3` · F2 (MINOR) 6v_v1_baseline.json stale D16 v1 sau grammar v2 →
  Lead rebaseline + trường grammar_version · F3 (NIT) transient
  FileNotFoundError run_export 2-fixtures-1-process (cùng vùng I5) → theo
  dõi, không tái hiện · F4 (NIT) PNG-assert chỉ chạy gate thủ công → ĐÓNG
  bởi auditor/6v-export (mục 4, 455/455 khớp).
- **OVERALL: PASS — 0 BLOCKER, 0 MAJOR.**
