# Product scope registry — release dangky_kinhdoanh

> R0.2 master plan. Bảng nguồn sự thật cho **mọi surface phải ship**.
> Cập nhật khi thêm component/domain; audit R7 đối chiếu bảng này với
> evidence thực tế. Trạng thái: `SHIP` / `PENDING` (chưa làm) /
> `DECISION` (chờ owner).

## 1. Ứng dụng & nền tảng

| Surface | Nội dung | Trạng thái |
|---|---|---|
| UI desktop chính | `app_web/ui/*` chạy qua `app_web/main.py` + pywebview (WebView2) | SHIP |
| Legacy Tk | `app_tk/*` — chỉ giữ compatibility engine dùng chung | DECISION: owner chọn `legacy-supported` hoặc `deprecated`; hiện không mở rộng |
| Windows package | `.exe`/installer build tái lập, offline, máy sạch không Python | PENDING (R6) |
| Excel | KHÔNG trong scope (`PLAN_excel.md` không tồn tại tại checkpoint) | loại trừ, trừ khi owner cấp contract riêng |

## 2. Dữ liệu nghiệp vụ

| Surface | Số lượng / shape | Nguồn chân lý | Trạng thái |
|---|---|---|---|
| Use case thủ tục | 27 case trong `app/data/use_cases.json` (`bat_buoc` + optional + `forms_oneOf`) | use_cases.json | SHIP |
| Biểu mẫu | 87 form blocks (`app/data/blocks/*.json`) | blocks sinh từ generator | SHIP |
| Table sections | 111 section trong `table_specs/manifest.json`: editable-grid 43 · fixed-matrix 47 · nested-grid 7 · output-table 6 · prose-block 3 · scalar-fields 4 · source-contamination 1 | manifest `table-manifest-v1` | SHIP (manifest) — implement 3 kind còn PENDING (R2/R3) |
| Layout roles | layout manifest v1: 87/87; 46 form source-indicator; 83 newline-collapse; 47 digit-glue | layout manifest | PENDING rollout (R1) |
| VSIC | `app/data/nganh_vsic.json` local lookup | JSON local | SHIP |
| Draft | autosave JSON per case (`profiles/*.json_*_draft`) | store `{values, checks, loops}` | SHIP |

## 3. API bridge Python ↔ JS (`window.pywebview.api`)

| Method nhóm | Chức năng | Trạng thái |
|---|---|---|
| load/save draft, use-case meta | round-trip hồ sơ | SHIP |
| export DOCX / ZIP nhiều mẫu | qua `tools/docx_render.py`, gate blocking + conflict guard | SHIP |
| attachment file thực | upload nội dung binary | DECISION (packet D6: metadata-only hay file thật) |

## 4. Xuất DOCX

| Surface | Contract | Trạng thái |
|---|---|---|
| Template tagged + loop/cond | `{#loop}{/loop}`, `{?flag}{/flag}` fail-loud (`CondTagError`) | SHIP |
| M72 one-variant Option D | selector `dn.loai_hinh` → chỉ variant được chọn ra DOCX | SHIP |
| Totals recompute lúc export | fixed-matrix | PENDING (R2) |
| Visual fidelity DOCX→PDF/PNG | cần LibreOffice/Word | NOT RUN (R5) |

## 5. Chất lượng & packaging

| Surface | Gate | Trạng thái |
|---|---|---|
| Release test runner | `python3 -X utf8 -m tools.release_runner` — 29 suite | SHIP (29 PASS tại R0) |
| Dependency contract | `requirements-dev.txt` (python-docx==1.2.0, lxml==6.1.1 pin; pywebview khóa ở R6) | SHIP |
| Accessibility keyboard/a11y | WCAG cơ bản + grid ARIA | PENDING (R4) |
| Idempotency generator | chạy 2 lần cùng hash | gate mỗi lần regenerate |

## 6. Quyết định owner đang mở

Xem `docs/decision_registry.md` (D1–D7). Không surface nào ở trạng thái
lưng chừng ngoài danh sách này tới release.
