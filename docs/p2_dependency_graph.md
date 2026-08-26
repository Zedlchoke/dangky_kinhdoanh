# P2 — Dependency graph và thứ tự triển khai an toàn

Trạng thái: **DRAFT cho Lead review**. Mô tả quan hệ renderer/controller/
generator/validation/domain-rollout cho 4 table component, dựa trên PLAN.md
(kiến trúc generator, Wave T1/P2/P3), manifest `table-manifest-v1` và hiện
trạng `app_web/ui/*`.

---

## 1. Đồ thị phụ thuộc

```mermaid
graph TD
    CT[p2_component_contracts.md<br/>schema chốt cho 4 kind]

    subgraph UI[Renderer + Controller - app_web/ui]
      FM_R[fixed-matrix renderer/controller]
      NG_R[nested-grid renderer/controller]
      OT_R[output-table renderer]
      EG_GAP[editable-grid gap:<br/>form-scoped meta, activeWhen,<br/>cross-field slot]
      GridCtl[GridCtl + GRID_META<br/>DA CO - stable baseline]
    end

    VAL[Formula/totals/cross-field validation<br/>form-domain.js]
    DRAFT[Draft migration v2 -> v3?]
    GATE[Export gate: totals recompute,<br/>blocking error check]

    GEN[Generator: anchor/boundary,<br/>rowspan/colspan, totals/STT tags,<br/>idempotency]

    FIX_EG[Fixture editable-grid]
    FIX_FM[Fixture fixed-matrix]
    FIX_NG[Fixture nested-grid]
    FIX_OT[Fixture output-table]
    TEST[Contract test tung component]

    P3[P3 domain rollout:<br/>capital-assets -> people-ownership<br/>-> tax-grids -> branches-admin]

    CT --> EG_GAP
    CT --> FM_R
    CT --> NG_R
    CT --> OT_R
    GridCtl --> EG_GAP
    EG_GAP --> VAL
    FM_R --> VAL
    NG_R --> VAL
    OT_R --> DRAFT
    VAL --> DRAFT
    VAL --> GATE
    CT --> GEN
    GEN --> FIX_EG & FIX_FM & FIX_NG & FIX_OT
    EG_GAP --> TEST
    FM_R --> TEST
    NG_R --> TEST
    OT_R --> TEST
    TEST --> P3
```

Quan hệ chặn chính:

| Upstream | Downstream | Lý do |
|---|---|---|
| Contract schema | mọi renderer/controller | không code UI trước khi tên trường được khóa |
| GRID_META form-scoped | PLI_M72 / PLII_M02 loop mới | map phẳng hiện tại đè key giữa các mẫu |
| Renderer fixed-matrix | formula/totals | ô tổng cần ô readonly để gắn computed |
| Validation cross-field | draft migration + export gate | migration phải giữ giá trị computed nhất quán |
| Generator rowspan/colspan | fixture nested-grid/fixed-matrix | fixture sinh từ generator, không sửa tay |
| Fixture + contract test | P3 rollout | Acceptance Gate #3 đòi spec + blocks + test trước rollout |

---

## 2. Thứ tự triển khai P2 đề xuất (tuần tự theo dependency)

Bước nào cũng có thể pause mà không hỏng production: các bước 1–4 chỉ thêm
module mới; bước 5 mới đụng generator (điểm regenerate tập trung của Lead).

1. **Contract** — Lead review + khóa `p2_component_contracts.md` (tên trường,
   severity rule, policy mặc định). Không viết code.
2. **Renderer/controller dùng chung** — theo thứ tự rủi ro tăng dần:
   a. editable-grid gap (form-scoped meta + activeWhen) — mở rộng, không đổi
      GridCtl thuần đã test;
   b. fixed-matrix renderer/controller (dòng cố định + ô tổng readonly);
   c. output-table renderer (đơn giản nhất, không input);
   d. nested-grid renderer/header nhiều hàng — cuối vì phức tạp rowspan.
3. **Formula/totals/cross-field validation** — slot khai báo trong meta,
   validator đọc meta thay vì hard-code; tái sử dụng parseMoney/PERCENT_SUM.
4. **Draft migration + export gate** — bump version draft nếu thêm shape mới;
   gate chặn blocking và recompute tổng lúc export.
5. **Generator: boundary an toàn, rowspan/colspan, totals/STT, idempotency**
   — chỉ Lead chạy regenerate global (`build_form_maps`, templates, blocks)
   sau khi review allowlist diff.
6. **Fixture + contract test cho từng component** — mỗi kind một cặp
   fixture/test theo `p2_fixture_candidates.md`; test đỏ phải sửa ở spec/generator,
   không sửa generated artifact.

Song song hóa an toàn: bước 2a–2d là file/module riêng (một agent sở hữu một
renderer); agent spec/test chỉ bắt đầu sau khi contract đã khóa hoặc làm trên
file tách biệt không chạm generated artifacts (nguyên tắc PLAN P1).

---

## 3. Điểm regenerate tập trung (Lead duy nhất)

Sau mỗi lần đổi spec/generator, CHỈ Lead chạy:

```powershell
python -X utf8 -m tools.build_form_maps --one <FORM_ID>   # thử riêng một mẫu
python -X utf8 tools/docx_to_blocks.py                    # sinh lại blocks
python -X utf8 tools/audit_blocks_check.py                # audit
# full regression + review allowlist diff trước khi commit generated artifacts
```

Agent lane khác KHÔNG regenerate global; vi phạm sẽ gây diff ngoài allowlist
và phá idempotency (Acceptance Gate #8/#9).

---

## 4. Rủi ro tại từng điểm mới

| Điểm mới | Rủi ro | Giảm thiểu |
|---|---|---|
| Form-scoped GRID_META | draft cũ lưu theo loop name phẳng bị đọc sai meta | fallback map cũ + test round-trip draft v2 |
| fixed-matrix computed totals | hai nguồn số liệu mâu thuẫn (nhập tay vs tính) | ô tổng outputOnly, recompute lúc export, blocking khi lệch vốn |
| nested-grid header rebuild | làm phẳng mất cột / lệch rowspan khi xuất DOCX | test so sánh cấu trúc w:tbl nguồn vs xuất (Gate #8); visual QA bắt buộc với mọi nested |
| Generator occurrence (PLI_M72) | nhân bản bảng khi chạy lại, xóa nhầm bảng kế | boundary `end_markers`, idempotency test chạy 2 lần giống byte |
| Draft migration | mất dữ liệu người dùng khi đổi shape | migration additive-only, giữ `_row_id`, có test dữ liệu cũ |
| Export gate siết thêm | hồ sơ cũ hợp lệ bỗng bị chặn | liệt kê rule mới vào release note; severity warning trước khi nâng blocking |

---

## 5. Điều kiện chuyển P3

P3 (capital-assets → people-ownership → tax-grids → branches-admin) chỉ mở
khi: contract đã khóa, cả 4 component có ít nhất một fixture pass contract
test, full regression xanh và Lead đã regenerate sạch allowlist. Trạng thái
BLOCKED_LEGAL_REVIEW của từng form vẫn chặn rollout tương ứng dù P2 hoàn tất
(xem `legal_review_backlog.md`).
