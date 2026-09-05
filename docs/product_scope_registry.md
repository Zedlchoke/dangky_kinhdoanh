# Product scope registry — release dangky_kinhdoanh

> R0.2 master plan, reconciled 2026-09-06 theo PLAN v7 + owner-delegated
> decisions. Bảng nguồn sự thật cho **mọi surface phải ship**.
> Cập nhật khi thêm component/domain; audit R7 đối chiếu bảng này với
> evidence thực tế. Trạng thái: `SHIP` / `PENDING` (chưa làm) /
> `DECISION` (chờ owner).

## 1. Ứng dụng & nền tảng

| Surface | Nội dung | Trạng thái |
|---|---|---|
| UI desktop chính | `app_web/ui/*` chạy qua `app_web/main.py` + pywebview (WebView2) | SHIP |
| Legacy Tk | `app_tk/*` — chỉ giữ compatibility engine dùng chung | DECIDED `deprecated` sau khi pywebview Windows smoke PASS; không mở rộng feature |
| Windows package | `.exe`/installer build tái lập, offline, máy sạch không Python | PENDING (R6) |
| Excel | P6=C: M72 + hộ kinh doanh + thay đổi ngành + thuế; export/import/round-trip/visual | SHIP; M72 pilot DONE, 3 cụm còn PENDING F4 |

## 2. Dữ liệu nghiệp vụ

| Surface | Số lượng / shape | Nguồn chân lý | Trạng thái |
|---|---|---|---|
| Use case thủ tục | 28 case trong `app/data/use_cases.json` (`bat_buoc` + optional + `forms_oneOf`) | use_cases.json | SHIP; re-audit after L-2026 migration |
| Biểu mẫu | 87 form blocks trước current-law migration | blocks sinh từ generator | PENDING L-2026: thay 9 mẫu TT121, bỏ active PLI_M11 |
| Table sections | 111 section; current coverage 76 IV · 22 owner-adjudicated/chờ implement · 7 no-table · 6 output-only | manifest `table-manifest-v1` | PENDING F1 + L-2026 migration |
| Layout roles | phase7v corpus 455 record, hard 0/candidate unresolved 0 | layout manifest + phase7v manifest | TECHNICAL PASS; current-law regen + human review còn PENDING |
| VSIC | `app/data/nganh_vsic.json` local lookup | JSON local | SHIP |
| Draft | autosave JSON per case (`profiles/*.json_*_draft`) | store `{values, checks, loops}` | SHIP |

## 3. API bridge Python ↔ JS (`window.pywebview.api`)

| Method nhóm | Chức năng | Trạng thái |
|---|---|---|
| load/save draft, use-case meta | round-trip hồ sơ | SHIP |
| export DOCX / ZIP nhiều mẫu | qua `tools/docx_render.py`, gate blocking + conflict guard | SHIP |
| attachment file thực | metadata tài liệu kèm theo; không upload binary trong scope core | DECIDED metadata-only |

## 4. Xuất DOCX

| Surface | Contract | Trạng thái |
|---|---|---|
| Template tagged + loop/cond | `{#loop}{/loop}`, `{?flag}{/flag}` fail-loud (`CondTagError`) | SHIP |
| M72 one-variant Option D | selector `dn.loai_hinh` → chỉ variant được chọn ra DOCX | SHIP |
| Totals recompute lúc export | fixed-matrix | SHIP cho implemented set; M12 current-law còn PENDING |
| Visual fidelity DOCX→PDF/PNG | phase7v 455 record/1653 PNG; Word open 91/91 | TECHNICAL PASS; HUMAN NOT_REVIEWED |

## 5. Chất lượng & packaging

| Surface | Gate | Trạng thái |
|---|---|---|
| Release test runner | `python3 -X utf8 -m tools.release_runner` — 63 suite | SHIP (63 PASS tại `a3c6c1b`); rerun after L-2026 |
| Dependency contract | `requirements-dev.txt` (python-docx==1.2.0, lxml==6.1.1 pin; pywebview khóa ở R6) | SHIP |
| Accessibility keyboard/a11y | unit suites xanh; full-browser sweep | PENDING F2 |
| Idempotency generator | chạy 2 lần cùng hash | gate mỗi lần regenerate |

## 6. Quyết định và evidence còn mở

Quyết định owner đã chốt tại `docs/owner_decision_packet_v7.md`. Còn mở là
implementation/evidence: L-2026 migration, 22 section theo mapping O1, Excel
3 cụm, full-browser sweep, AI/human corpus review và Windows S1–S8.
