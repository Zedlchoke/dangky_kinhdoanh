# Wave 1 — Contract inventory & báo cáo gap (Agent 1C `qa-contract`)

- Ngày: 2026-08-25 · Branch: `agent/qa-contract` · Worktree:
  `dangky_kinhdoanh-worktrees\qa-contract`
- Phạm vi: QA độc lập, KHÔNG sửa production (`app_web/ui/*.js`, `main.py`,
  `build_form_maps.py`, `docx_render.py`, `docx_to_blocks.py`, templates,
  `app/data/**` — chỉ đọc).
- Công cụ: `tools/test_contract_release.py` (mới, thuộc sở hữu 1C)

Chạy:

```powershell
python -X utf8 -m tools.test_contract_release
```

---

## 1. Kết quả chạy thật (baseline trước Integrate 1)

Tổng: **1 PASS / 2 FAIL** (exit code 1). Hai check đỏ là **chủ đích thiết kế**
(test phát hiện bug; phải xanh sau khi merge Agent 1A/1B):

| Check | Kết quả | Bằng chứng |
|---|---|---|
| (a) `CONTRACT_PLII_M01_STT_X` | **RED** (EXPECTED-RED-BEFORE-1A) | Render PLII_M01 với 3 dòng `ds_nganh`: tìm thấy bảng ngành và cột "Ngành, nghề kinh doanh chính", nhưng ô STT = `[('1',''),('2',''),('3','')]` — template chưa có `{_stt}` ở hàng khuôn; cột ngành chính cũng trống (chưa map `{la_nganh_chinh}`) |
| (b) `CONTRACT_FORMS_METADATA` | **RED** (EXPECTED-RED-BEFORE-1B) | 27 case / 36 form: **đủ** `bat_buoc` bool trên mọi form; nhưng case `chuyen_doi_hkd_sang_dn` (4 form I.1/I.2/I.3/I.4) **chưa có** metadata nhóm loại-trừ oneOf → UI hiện tick tất cả |
| (c) `INVENTORY_DS_NGANH` | **PASS** (thông tin) | Quét đủ 87 blocks, không lỗi cấu trúc; thiếu `ds_nganh` đúng 13/13 mẫu theo PLAN.md |

Kiểm chứng ngược (không commit): vá mô phỏng `{_stt}` + `{la_nganh_chinh}`
vào bản sao template → cùng bộ assertion **PASS** (STT `1/2/3`, đúng một `X`
ở dòng 1). Test đỏ vì contract chưa đáp ứng, không phải do test sai.

### Bug UI liên quan (chỉ đọc để lập luận)

`app_web/ui/app.js:477-483` — `renderFormList()` hardcode `"checked"` cho
mọi checkbox form; metadata `bat_buoc` bị bỏ qua khi map `case.forms -> docs`.
Agent 1B sẽ giữ metadata từng form và render bắt buộc = checked+disabled,
tùy chọn = unchecked.

---

## 2. Inventory bảng ngành nghề (87 mẫu)

Hiện có loop canonical `ds_nganh` (2 mẫu):

| Mẫu | Cột đã map | Ghi chú |
|---|---|---|
| `PLI_M02` | STT(tự sinh), ma_nganh, ten_nganh, chi_tiet, la_nganh_chinh | Pilot chuẩn, có `_row_id`, VSIC, requirePrimary |
| `PLII_M01` | ten_nganh, ma_nganh | Thiếu `{_stt}` và cột "Ngành, nghề kinh doanh chính" chưa map `{la_nganh_chinh}` — gap Agent 1A |

### 13 mẫu THIẾU `ds_nganh` — khớp 100% danh sách PLAN.md

| Nhóm | Số lượng | Mẫu | Trạng thái | Wave 2 owner |
|---|---|---|---|---|
| formation — đăng ký mới | 4 | `PLI_M01`, `PLI_M03`, `PLI_M04`, `PLI_M05` | THIẾU | 2A industry-formation |
| change — thay đổi/bổ sung/xóa bỏ | 7 | `PLI_M12`, `PLI_M17`, `PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`, `PLI_M72` | THIẾU | 2B industry-change |
| household — hộ kinh doanh | 2 | `PLII_M02`, `PLII_M07` | THIẾU | 2C industry-household |

Kết luận: danh sách quét được **trùng khớp chính xác** với PLAN.md mục
"Kế hoạch hoàn thiện sau audit độc lập" điểm 4; không phát hiện mẫu nào ngoài
13 bị mất `ds_nganh`, không có mâu thuẫn blocks ↔ form_maps.

### Các loop khác tên (liệt kê riêng — KHÔNG đề xuất gộp với `ds_nganh`)

| Loop | Mẫu | Ý nghĩa |
|---|---|---|
| `ds_thanh_vien` | PLI_M06, PLI_M09 | Danh sách thành viên TNHH 2TV+/hợp danh |
| `ds_cshhl` | PLI_M10, PLI_M11 | Chủ sở hữu hưởng lợi |
| `ds_co_dong_sang_lap` | PLI_M07 | Cổ đông sáng lập |
| `ds_co_dong_nn` | PLI_M08 | Cổ đông là nhà đầu tư nước ngoài |
| `ds_tv_ho_gia_dinh` | PLII_M01 | Thành viên hộ gia đình |

**Loop `nganh_*` khác nghĩa** (`nganh_bo_sung`, `nganh_xoa_bo`,
`nganh_truoc_thay_doi`): **chưa tồn tại** trong blocks/form_maps hiện tại —
chỉ PLAN.md dự liệu cho Wave 2B. Khi làm phải tạo mới theo semantic riêng,
mỗi loop có row contract + validation + test export độc lập; tuyệt đối không
map đè vào `ds_nganh` chỉ vì cùng chứa mã ngành.

---

## 3. Schema mong đợi từng nhóm (theo hiểu biết từ PLAN.md)

### 3a. Đăng ký mới — formation (2A: PLI_M01/M03/M04/M05)

- Loop canonical `ds_nganh` full-cột như PLI_M02: `{_stt}`, `ma_nganh`,
  `ten_nganh`, `chi_tiet`, `la_nganh_chinh`; header/cột khớp template pháp lý
  từng mẫu (M01 DNTN, M03 TNHH 2TV+, M04 CTCP, M05 hợp danh).
- Ngành chính bắt buộc đúng một dòng (`requirePrimary`) — cần xác nhận từng
  mẫu có cột "Ngành chính" trên biểu mẫu gốc trước khi bật.
- Fixture + structural DOCX test riêng cho mỗi mẫu.

### 3b. Thay đổi/bổ sung/xóa bỏ — change (2B: PLI_M12/M17/M19/M21/M23/M25/M72)

- Phân biệt rõ 4 semantic: ngành **hiện tại** (`ds_nganh`),
  `nganh_bo_sung`, `nganh_xoa_bo`, `nganh_truoc_thay_doi`.
- M12/M17/M19/M23/M25: giấy đề nghị/thông báo kèm phần ghi ngành; M21 (cấp đổi
  GCKD→GCDN): ngành ghi lại theo ngành kinh tế cấp 4.
- Nếu nghiệp vụ chưa đủ căn cứ cho một mẫu → ghi gap, để mẫu blocked, không
  tự suy diễn; không gộp loop khác nghĩa.

### 3c. Hộ kinh doanh — household (2C: PLII_M02/M07)

- Metadata loop theo đúng nghiệp vụ hộ KD; kiểm tra yêu cầu ngành chính của
  từng mẫu trước khi bật `requirePrimary` (PLII_M01 hiện có cột "Ngành, nghề
  kinh doanh chính" → sau 1A sẽ map `{la_nganh_chinh}`).
- Dùng VSIC lookup chung; shared data với canonical CHỈ khi semantics trùng.

---

## 4. Metadata chọn mẫu — bat_buoc / optional / oneOf (phát hiện check b)

Trạng thái `use_cases.json` (27 case / 36 form):

- ✅ Mọi form đều đã khai `bat_buoc: bool` (36/36).
- ❌ Không có metadata nhóm loại-trừ nào (oneOf) trên case hay form.
- Case bắt buộc phải có oneOf tối thiểu: `chuyen_doi_hkd_sang_dn`
  (I.1 / I.2 / I.3 / I.4 loại trừ nhau — chỉ được xuất đúng một giấy đề nghị;
  I.3 kèm M06, I.4 kèm M07).
- Case ứng viên thứ hai (cảnh báo, chưa fail): `thay_doi_chusohuu_chudn`
  (M15 TNHH 1TV ↔ M14 DNTN cũng loại trừ nhau).

Contract đề xuất cho 1B (test chấp nhận các cách khai tương đương):
case-level `one_of` / `form_groups` / `nhom_loai_tru` (danh sách nhóm tham
chiếu pl+mau) hoặc form-level `one_of_group` (tên nhóm gom lại); nhóm hợp lệ
phải phủ ≥2 form.

---

## 5. Gap nghiệp vụ cần Lead quyết (open questions)

1. `thay_doi_chusohuu_chudn` có đưa vào nhóm oneOf ngay Wave 1B hay để Wave 2?
   (nghiệp vụ M14/M15 hiển nhiên loại trừ).
2. `PLI_M21` (cấp đổi): dùng canonical `ds_nganh` hay schema riêng vì "ngành
   được ghi lại theo ngành kinh tế cấp 4"? Cần đối chiếu hướng dẫn điền TT 68.
3. `nganh_truoc_thay_doi` lấy dữ liệu từ đâu (draft cũ / nhập tay)? Nguồn dữ
   liệu chưa định nghĩa trong app.
4. Ngưỡng bật `requirePrimary` cho PLII_M02/M07: biểu mẫu gốc có cột ngành
   chính riêng hay chỉ ghi danh sách? Cần xem file Word gốc.
5. TT 121/2026/TT-BTC sửa biểu mẫu TT 68/2025 — chưa kiểm chứng có thay đổi
   cột bảng ngành không; ảnh hưởng trực tiếp spec Wave 2 nếu có.
6. Case pilot `pilot_ui_m02_m06` nên bị loại khỏi export thật bằng metadata
   gì (cờ `pilot=true`?) để không lẫn hồ sơ nghiệp vụ.

## 6. Mapping agent Wave 2 chịu trách nhiệm từng mẫu

| Agent | Branch dự kiến | Mẫu |
|---|---|---|
| 2A industry-formation | `agent/industry-formation` | PLI_M01, PLI_M03, PLI_M04, PLI_M05 |
| 2B industry-change | `agent/industry-change` | PLI_M12, PLI_M17, PLI_M19, PLI_M21, PLI_M23, PLI_M25, PLI_M72 |
| 2C industry-household | `agent/industry-household` | PLII_M02, PLII_M07 |

Wave 2 chỉ được tạo worktree từ commit `integration/wave-1` sau Integrate 1
(khi test 1A/1B/1C đã xanh).
