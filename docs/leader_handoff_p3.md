# Leader handoff — triển khai P3 (bản prompt cho agent Lead mới)

> File này là bản lưu của prompt bàn giao. Prompt hoạt động nằm cuối file.
> Cập nhật khi phạm vi thay đổi.

## Điều Leader mới PHẢI tự xác minh trước khi làm (không tin ai, kiểm bằng lệnh)

1. `git log --oneline -3` — HEAD phải ≥ commit "docs(plan): v3" và cây làm
   việc sạch. Nếu `PLAN.md` còn chỉnh tay của owner chưa commit → commit NGAY
   việc đó là hành động đầu tiên (`docs(plan): chỉnh theo owner`).
2. `python3 -X utf8 -m tools.release_runner` — phải 38 PASS / 0 FAIL / 0 NOT
   RUN. Nếu không → dừng, phân loại trước (tiền lệ P0).
3. `git worktree list` — `p3-e2e` phải còn tại `b61def0`; 15 lane cũ đã merge.

## Phạm vi được duyệt (P3 — PLAN.md mục 5)

- P3.0 dọn 15 worktree lane đã merge (owner đã duyệt trong PLAN; `p3-e2e`
  KHÔNG dọn).
- P3.1 merge `agent/p3-e2e` → main; đăng ký 4 suite mới vào release_runner +
  allowlist.
- P3.2 sửa 9 finding theo 4 cụm (draft-crash, export-path, DOCX-NUL, a11y) —
  chi tiết file:line trong PLAN.md mục 5-P3.2; mỗi cụm 1 commit + test phủ;
  mục tiêu `test_p3_a11y` 8 FAIL → 0.
- P3.3 đo a11y trên app shell thật (app.js tablist) — mở rộng suite hoặc
  manual evidence.
- P3.4 platform Windows: KHÔNG có môi trường → giữ NOT RUN, ghi hướng dẫn.

KHÔNG nằm trong phạm vi: P4 implement Excel (Review Gate chỉ sau P3 PASS),
P5/P6/P7, mọi blocker pháp lý đang blocked (M09, PLII_M02 member, M72 N2–N5,
D5.2, N-tail, D6.x, M03/M04/M05), push/tag/release (chỉ theo lệnh owner).

## Prompt hoạt động (copy từ đây xuống cho agent Lead mới)

```text
Bạn là Lead Engineer mới tiếp quản repo dangky_kinhdoanh tại
/Users/hoangminhlong/orca/dangky_kinhdoanh. Nhiệm vụ: triển khai PHASE P3
đúng PLAN.md v3. Không dùng lịch sử hội thoại cũ làm nguồn sự thật.

Đọc theo thứ tự: 1) PLAN.md (v3 — toàn bộ); 2) docs/execution_ledger.md;
3) docs/decision_registry.md; 4) docs/p2_component_contracts.md +
docs/p2_dependency_graph.md; 5) source/tests/manifests tại HEAD.

XÁC MINH ĐẦU TIÊN (không tin ai): git log/status/worktree list; release
runner phải 38/0/0; nếu PLAN.md còn chỉnh của owner chưa commit → commit
đó trước. Nếu runner đỏ → dừng, phân loại (tiền lệ P0 trong ledger).

PHẠM VI ĐƯỢC DUYỆT = P3 (PLAN mục 5): P3.0 dọn worktree cũ đã merge;
P3.1 merge agent/p3-e2e @ b61def0 (4 suite test_p3_e2e/draft/security/
a11y) + đăng ký release_runner + allowlist; P3.2 sửa 9 finding theo 4 cụm
PLAN liệt kê (draft Array.isArray guard form-domain.js:754 + app.js:97;
export sanitize case_id + mkdir try/except; safe_escape loại control char
XML; a11y outline/aria-colcount/aria-rowcount/aria-label nút + checkbox;
log redact); P3.3 a11y app shell; P3.4 giữ NOT RUN cho Windows.
KHÔNG đụng: P4 Excel, P5-P7, blocker pháp lý đang blocked, push/tag/release.

VẬN HÀNH theo PLAN mục 6 (SOP): worktree ../dangky_kinhdoanh-worktrees/
<lane> -b agent/<lane>; tối đa 3 lane, không chồng file; lane brief 5 mục
(BASE/ownership/forbidden/gate/report); Lead tự merge --no-ff tuần tự,
regen global (pipeline ×2 zero-diff, member-level cho docx), census nếu
counts đổi, allowlist exact-set cân, full runner, ledger, checkpoint.

BẮT BUỘC: visual re-shoot form bị ảnh hưởng sau mọi regen (recipe PLAN
6.2); sửa test theo bằng chứng không nới; cùng loop name khác contract =
tên loop riêng (tiền lệ ledger), không nới conflict guard; generated đổi
phải có dòng chủ đích trong tools/audit_expected_diff_files.txt.

Checkpoint báo: HEAD/commits, exact diff, PASS/FAIL/NOT RUN, generator
idempotency, visual evidence, blocker, git status. Mỗi cụm fix xong =
commit sạch. Dừng và hỏi owner nếu: finding đòi sửa ngoài phạm vi P3,
suite baseline đỏ không giải thích được, hoặc bất kỳ quyết định pháp lý.
```
