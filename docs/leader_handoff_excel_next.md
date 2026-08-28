# Leader handoff — Excel X6 + rollout bảng + sửa layout header (prompt cho agent Lead mới)

> Bản lưu của prompt bàn giao (2026-08-28, sau khi Excel X1–X5 đóng).
> Prompt hoạt động nằm cuối file. Agent mới KHÔNG dùng lịch sử hội thoại cũ
> làm nguồn sự thật — chỉ dùng file này + PLAN.md + docs/execution_ledger.md
>
> - docs/decision_registry.md + source/tests/manifests tại HEAD.

## Tình trạng bàn giao (đã xác minh tại HEAD `9f136be`)

- P3 ĐÓNG (đã push origin/main = `78a0b0f`), P4 Review Gate ĐÓNG (owner trả
E1–E6 + ra lệnh "Bắt đầu Excel").
- Excel: X1 questionnaire (`114e7fa`), X2 xuất (`fae9a6a`), X3 nạp
(`550d611`), X5 UI+bridge (`a5b0b73`), X4 tích hợp+round-trip (`3d5457d`,
`9f136be`). Release runner **46 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS**.
- Còn 3 commit local chưa push (b72a155, 2e386fd, 114e7fa→9f136be là 6+6
commit) — push CHỈ khi owner ra lệnh.

## XÁC MINH ĐẦU TIÊN (không tin ai)

1. `git log --oneline -5` ≥ `9f136be`, `git status` sạch, `git worktree list`
 chỉ main (+ agent/p2-wire giữ nguyên — prototype đã park).
2. `python3 -X utf8 -m tools.release_runner` phải **46/0/0 VERDICT PASS**.
 Đỏ → dừng phân loại theo tiền lệ P0/H7 (exact-set chỉ cân TẠI COMMIT —
 sửa manifest xong phải commit rồi mới chạy lại suite).
3. Đọc PLAN.md mục 4 (luồng Excel), docs/execution_ledger.md 2 wave cuối,
 docs/decision_registry.md.

## PHẠM VI ĐƯỢC DUYỆT (lệnh owner 2026-08-28)

### Việc 1 — X6 visual Excel (còn lại của luồng Excel)

- Sinh phiếu thật: `python3 -X utf8 -m tools.excel_export` (hoặc qua bridge)
cho PLI_M72 → lưu evidence `generated_ho_so/_visual_layout/excel/`.
- Reload-kiểm cấu trúc (openpyxl): protection, dropdown, ô vàng unlocked,
sheet ẩn `___map` — suite đã phủ; việc còn lại là **owner mở bằng Excel
thật và duyệt hình** (máy dev không có Excel/LibreOffice — ghi NOT RUN có
lý do, đừng tự nói PASS giúp owner).

### Việc 2 — use case thiếu: "Thay đổi nội dung đăng ký hộ kinh doanh"

- `app/data/use_cases.json` thiếu thủ tục trỏ tới **PLII_M02** (Phụ lục II
Mẫu 2 — "Giấy đề nghị đăng ký thay đổi nội dung đăng ký hộ kinh doanh",
do chủ hộ ký). Owner không thấy option này trong dropdown "Thủ tục".
- Thêm use case (nhóm gợi ý "Thay đổi nội dung đăng ký hộ kinh doanh",
forms: PL II Mẫu 2, bat_buoc=true) — data-only.
- CHÚ Ý sync pin: các suite đếm use case (test_acceptance "PLAN.md 14 mục
  - EXTRA", test_form_flow…) có thể đỏ — sửa pin THEO BẰNG CHỨNG, không nới.

### Việc 3 — layout header: TÊN DN, HKD trái + quốc hiệu phải (yêu cầu owner kèm ảnh)

- Hiện app xếp dọc: "TÊN DOANH NGHIỆP", "TÊN HỘ KINH DOANH) (giữa) rồi "CỘNG HÒA XÃ HỘI CHỦ  
NGHĨA VIỆT NAM / Độc lập - Tự do - Hạnh phúc" (giữa). ĐÚNG PHẢI LÀ (bản  
Word gốc, vd Phụ lục II Mẫu 2 / Phụ lục I Mẫu 13):
  - cùng một band: "TÊN DOANH NGHIỆP ____________" TRÁI, khối quốc hiệu
  PHẢI (2 dòng, dòng 2 gạch chân "Độc lập - Tự do - Hạnh phúc");
  - dòng kế: "Số: …" TRÁI và "…, ngày … tháng … năm …" PHẢI.
- Sửa ở LỚP TEMPLATE/BLOCKS của các mẫu bị ảnh hưởng (soi header từng mẫu
có ô TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH: PLI_M01–M15, PLII_M01–M02, M72
— census bằng grep "TÊN DOANH NGHIỆP"/"TÊN HỘ KINH DOANH" trong
app/data/blocks) — KHÔNG sửa tay generated: mọi thay đổi đi qua spec →
Lead regen → visual re-shoot BẮT BUỘC từng mẫu ảnh hưởng + runner.
- Nếu layout nằm ở docx template (w:p alignment/tables) thì regen phải giữ
marker/field; snapshot + DOCX export đều phải ra đúng band 2 cột.

### Việc 4 — bổ sung TOÀN BỘ loại bảng còn blocked (nguồn pháp lý mới)

- Owner CHÍNH THỨC cho phép: tự tra cứu trên mạng **Nghị định 168/2025/NĐ-CP**  
**(ngày 30/6/2025) + Thông tư 68/2025/TT-BTC** (biểu mẫu phụ lục I/II chính  
là các mẫu trong app) hoặc **hỏi owner bất cứ thông tin pháp lý nào**.
- Các nhóm việc (theo census 33 missing_grid + 5 partial_columns + 1
partial + 1 contaminated):
  1. Nguồn vốn điều lệ PLI_M03/M04/M05 + PLI_M12 (blocker cũ D1.3/D1.5/
   D3.3 chờ bản gốc — GIỜ dựng theo phụ lục TT 68; phần nguồn hiện có bị
   cắt (thuế/BHXH sau mục 6/7) lấy đúng biểu mẫu TT 68 làm chuẩn, GHI RÕ
   trong spec nguồn tham chiếu điều/dòng nào).
  2. Thuế PLII_M02 (D5.2) — lấy danh mục chỉ tiêu từ TT 68 (đúng mẫu II.2).
  3. M09 rebuild (D3.1/D3.2 đã chọn A: decontaminate + bản 14 cột).
  4. M72 N2–N5 + N-tail (D2.9/D7.4=A đã có).
  5. Các fixed-matrix thuế PLI_M17/M19/M23/M25 đầy đủ chỉ tiêu (D5.1=A).
- Quy trình MỖI nhóm: đọc biểu mẫu TT 68 → viết spec (tools/form_specs) →
lane dựng → Lead regen (build_form_maps → tag_m72_sections →
docx_to_blocks, ×2 zero-diff, member-level docx) → census manifest →
allowlist exact-set cân → visual re-shoot → runner. Mỗi nhóm 1 commit.
- GHI vào decision_registry phần "Owner response": 2026-08-28 owner cho
phép dựng theo TT 68/NĐ 168 (thay việc chờ bản gốc) — trích dẫn nguồn
điều khoản vào `source_evidence` của spec.

## QUY TẮC BẤT BIẾN (đọc PLAN.md mục 6/7)

- Lead giữ main; lane worktree tối đa 3, không chồng file; Lead merge
--no-ff tuần tự + targeted battery sau từng merge.
- Mọi generated đổi phải có dòng chủ đích trong
tools/audit_expected_diff_files.txt; exact-set cân TẠI COMMIT (suite H7
đọc diff đã commit — chạy suite khi tree bẩn sẽ đỏ ảo, tiền lễ nhiều lần
trong session trước).
- KHÔNG nới test; sửa pin theo bằng chứng sản phẩm mới phải ghi lý do trong
commit. KHÔNG đụng blocker chưa được phép (giờ chỉ còn những gì TT 68
không trả lời được — hỏi owner).
- Visual re-shoot sau mọi regen (recipe PLAN 6.2) — bắt regression mà 46
suite xanh không thấy.
- Push/tag/release CHỈ theo lệnh owner. Suite mới PHẢI đăng ký
tools/release_runner.py.

## Prompt hoạt động (copy từ đây xuống cho agent Lead mới)

```text
Bạn là Lead Engineer mới tiếp quản repo dangky_kinhdoanh tại
/Users/hoangminhlong/orca/dangky_kinhdoanh. Đọc: 1) PLAN.md (v3); 2)
docs/execution_ledger.md (2 wave cuối: P3, P4, Excel X1–X5); 3)
docs/decision_registry.md; 4) docs/leader_handoff_excel_next.md (file này);
5) source/tests/manifests tại HEAD.

XÁC MINH ĐẦU TIÊN: git log/status/worktree; release runner phải 46/0/0
VERDICT PASS tại HEAD >= 9f136be. Đỏ -> dừng, phân loại (tiền lệ P0).

NHIỆM VỤ theo thứ tự owner ưu tiên:
(1) Thêm use case "Thay đổi nội dung đăng ký hộ kinh doanh" (PLII_M02,
    Phụ lục II Mẫu 2, do chủ hộ ký) vào app/data/use_cases.json — data-only;
    sync pin suite đếm use case theo bằng chứng, không nới.
(2) Sửa layout header các mẫu có ô TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH:
    tên DN TRÁI + quốc hiệu PHẢI cùng band, dòng Số trái / ngày-tháng-năm
    phải (đúng bản Word gốc Phụ lục II Mẫu 2 và Phụ lục I Mẫu 13). Sửa qua
    spec + regen Lead, KHÔNG sửa tay generated; visual re-shoot từng mẫu
    bị ảnh hưởng (UI + export DOCX qua Word) bắt buộc.
(3) Bổ sung toàn bộ loại bảng đang blocked theo nguồn Nghị định
    168/2025/NĐ-CP + Thông tư 68/2025/TT-BTC (owner cho phép tự tra cứu
    mạng và yêu cầu hỏi owner bất cứ thông tin pháp lý nào cần): nguồn vốn
    M03/M04/M05/M12; thuế PLII_M02 (D5.2); M09 rebuild 14 cột; M72 N2–N5 +
    N-tail; thuế M17/M19/M23/M25. Mỗi nhóm: spec trích dẫn điều/dòng nguồn
    -> lane -> Lead regen pipeline ×2 zero-diff -> census -> allowlist ->
    visual re-shoot -> runner. Ghi owner-response 2026-08-28 vào
    docs/decision_registry.md.
(4) X6: sinh phiếu Excel mẫu thật cho PLI_M72, evidence vào
    generated_ho_so/_visual_layout/excel/, nhờ owner mở bằng Excel duyệt
    hình (không có Excel trên máy dev — trung thực NOT RUN).

BẮT BUỘC: SOP worktree/lane PLAN mục 6 (tối đa 3 lane, brief 5 mục); Lead
merge --no-ff tuần tự; regen ×2 zero-diff; allowlist exact-set cân TẠI
COMMIT (H7 đọc diff đã commit — tree bẩn thì suite đỏ ảo); visual re-shoot
sau mọi regen; không nới test; runner 46 suite 0 FAIL tại checkpoint;
checkpoint báo HEAD/commits/diff/PASS-FAIL-NOT RUN/visual/blocker/git
status. Dừng hỏi owner nếu: quyết định pháp lý ngoài TT 68/NĐ 168, suite
đỏ không giải thích được, hoặc việc đòi sửa ngoài phạm vi trên.
KHÔNG: push/tag/release khi chưa có lệnh; đụng P5/P6/P7.
```

