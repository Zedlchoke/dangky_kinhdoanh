# docs/audits/6v/v5-export-audit.md — auditor/6v-export (V5)

**Auditor:** auditor/6v-export (độc lập, read-only — spawn fresh, không dùng
context executor)
**Ngày audit:** 2026-09-05
**Đối tượng:** kết quả xuất end-to-end của PLAN.md mục 3.2, tại `main @ de86570`
**Worktree audit:** `../dangky_kinhdoanh-worktrees/6v-audit-export`
(branch `6v-audit-export`, checkout de86570, KHÔNG commit; file tracked
không bị sửa — `git status` worktree chỉ có file untracked của audit)
**Corpus chuẩn:** `generated_ho_so/_visual_layout/phase6v/v4b_corpuscheck`
(455 record = 91 form×variant × 5 fixture; 86 main + 5 variant M72; sinh
2026-09-05 14:06:13)
**Môi trường:** macOS darwin 24.4.0 arm64 · Microsoft Word 16.16.27 ·
LibreOffice 26.8.0.3 (`soffice`) · python-docx 1.2.0 · pymupdf 1.28.2
**Bằng chứng:** `generated_ho_so/_audit_v5/` (gitignored) trong worktree —
kết quả JSON, PDF xuất thử, crop PNG. Kịch bản audit:
`generated_ho_so/_audit_v5/audit23_determinism_zip.py`,
`audit23b_diff_detail.py`, `audit5_e2e_ui_data.py`,
`audit6_cross_fixture.py`.

---

## 1. WORD-OPEN — **PASS**

Chạy `tools/phase5_word_open_loop.py` bằng Microsoft Word thật 16.16.27 trên
corpus chuẩn, fixture `valid-full` (86 DOCX `main/` + 5 DOCX variant M72
`m72_dntn/`, `m72_tnhh_1tv/`, `m72_tnhh_2tv/`, `m72_ctcp/`, `m72_dhdn/`).

**Kết quả: 91/91 PASS_OPEN_DIRECT — 0 dialog phục hồi, 0 corrupt, 0 timeout**
(elapsed 794.9 s; `sheets=0, dialogs=0` mọi record). Inventory JSON đã ghi
vào report path: `docs/audits/6v/v5-export-audit-inventory.json`.

Ghi chú [INFO]: nhãn `variant` của tool derive từ tên dir corpus kiểu
`m72_tnhh_2tv` → ghi `'m72'`/`'m72_tnhh'` thay vì tên variant đầy đủ (logic
`rsplit` của tool đoán cho prefix `phase5_word_open_`). Chỉ ảnh hưởng nhãn
hiển thị trong inventory — đủ 5 file variant đều mở và PASS.

Tái lập:
```
python3 -X utf8 tools/phase5_word_open_loop.py \
  --root <repo>/generated_ho_so/_visual_layout/phase6v/v4b_corpuscheck/valid-full \
  --pattern '*' \
  --inventory <worktree>/generated_ho_so/_visual_layout/phase5_word_open/inventory_v4b_corpuscheck_validfull.json
```

## 2. DETERMINISM — **PASS**

8 form `PLI_M01, PLI_M09, PLI_M12, PLI_M15, PLII_M01, PLII_M02, PLII_M08,
PLI_M72 (variant CTCP)` — data `build_fixture` fixture `valid-full` (đúng
đường production), export **2 lần** qua `app_web.main.Bridge.export`
(format `both`): run A `audit_det_A_20260905_174043`, run B
`audit_det_B_20260905_174227`. Cả 2 run `ok=True, errors=0`.

| So sánh | Kết quả |
|---|---|
| DOCX `word/document.xml` (byte) | **giống hệt 8/8 form** |
| DOCX nguyên file | khác byte, nhưng **mọi entry trong zip giống hệt byte** — khác nhau chỉ ở metadata container zip (timestamp entry khi LO re-save) |
| PDF nguyên file | khác byte; mức lệch **CHỈ `/CreationDate`** (14 chữ số giây; `ModDate` vắng mặt ở cả 2 run) |
| PDF render (fingerprint pymupdf: số trang + text + pixel từng trang) | **giống hệt 8/8** (9, 8, 25, 6, 7, 13, 1, 6 trang) |

Mức lệch ghi rõ: nội dung xuất là **xác định 100%**; lệch duy nhất là dấu
thời gian sinh file do LibreOffice nhúng — thuộc lớp metadata được phép lệch
theo nhiệm vụ. Bằng chứng: `generated_ho_so/_audit_v5/audit23_result.json`,
`audit23b_diff_detail.json`.

Tái lập: `python3 -X utf8 generated_ho_so/_audit_v5/audit23_determinism_zip.py`
rồi `audit23b_diff_detail.py` (trong worktree).

## 3. ZIP INTEGRITY — **PASS**

ZIP của run A (`audit_det_A_20260905_174043.zip`): namelist **== payload yêu
cầu** — đúng 16 entry = 8 `.docx` + 8 `.pdf` của format `both`; **0 file lạ,
0 file thiếu**; `testzip()` = None (CRC sạch); size từng entry == size trên
đĩa. Bằng chứng: trường `zip` trong `audit23_result.json`.

Tái lập: như mục 2 (phần ZIP trong cùng script).

## 4. PNG == ĐĨA (đóng finding F4 của auditor-core) — **PASS**

Phép đếm **độc lập** (os.walk/rglob, không qua hàm assert của gate):

- `find page-*.png | wc -l` tương đương = **1631**.
- Σ manifest `records[].pages` của `v4b_corpuscheck` = **1631**.
- So tập: **trùng khớp 100%** — 0 file chỉ có trên đĩa, 0 file chỉ có trong
  manifest.
- So **per-record 455/455**: mỗi dir record trên đĩa chứa đúng danh sách
  `page-NN.png` manifest khai.
- `png_disk_assert` manifest tự khai `{claimed: 1631, disk: 1631, ok: true}` —
  khớp với phép đếm độc lập của auditor.

F4 (manifest ≠ đĩa) **đóng**: không còn sai lệch manifest↔đĩa, kể cả M72.

Tái lập:
```
find <repo>/generated_ho_so/_visual_layout/phase6v/v4b_corpuscheck -name 'page-*.png' | wc -l
# đối chiếu Σ len(r["pages"]) và per-record dir trong manifest.json
```

## 5. E2E TỪ UI-DATA — **PASS-WITH-NOTES**

Mô phỏng payload người dùng thật (data phẳng kiểu UI store: ten DN in hoa,
MST, địa chỉ, bảng thành viên 2 dòng, 1 checkbox tick) qua `Bridge.export`
(format `both`) cho 3 form — cả 3 `ok=True, errors=0`:

| Form | Tên DN | Vị trí đúng slot | Checkbox tick | Bảng |
|---|---|---|---|---|
| `PLI_M01` | HỘ KINH DOANH CỬA HÀNG TỔNG HỢP MINH PHÚ | trang 3, đúng nhãn «Tên doanh nghiệp viết bằng tiếng Việt (ghi bằng chữ in hoa):» | `chk_tt_thanh_lap_moi` = **X trong ô vuông có viền** (crop PNG; D15 XML 0 lỗi) | `ds_nganh` 1 dòng (mã 4711 có mặt) |
| `PLII_M02` | HỘ KINH DOANH THỜI TRANG MINH ANH | trang 1 (slot tên in hoa dưới tiêu đề) + trang 7 | `chk_ct_ho_gia_dinh` = **X trong ô vuông có viền** (crop PNG; D15 XML 0 lỗi) | `tv_hgd_sau_thay_doi` đủ 2 dòng (TRẦN THỊ BÍCH HỒNG, LÊ VĂN CƯỜNG) |
| `PLI_M72` (TNHH_2TV) | CÔNG TY TNHH MINH LONG PHÚ | trang 1 | flag variant `loai_hinh_tnhh_2tv` → đúng section TNHH 2TV render | `ds_thanh_vien_tnhh_2tv` đủ 2 dòng (PHẠM THỊ MAI 60%, ĐỖ VĂN HẢI 40%) |

Xác minh thị giác (auditor đọc crop PNG): ô tick hiện **☒**, các ô không
tick là **ô vuông trống** — đúng chuẩn Q-V1. Bằng chứng:
`_audit_v5/e2e/PLI_M01_p1_tick_real.png`, `PLII_M02_tick_crop.png`,
`audit5_result.json`.

**Note (finding F-V5-2, severity LOW):** D15 sub-check PDF
`X_OWN_LINE` bắn 1 hit ở PLI_M01 trang 4: X cột `la_nganh_chinh` của bảng
ngành nghề rơi một mình một dòng khi dòng bảng wrap (tên ngành dài của
payload E2E). Crop `PLI_M01_p4_X_own_line_crop.png` cho thấy X nằm **trong
ô bảng có viền** — hợp pháp về thị giác (XML-level D15 cũng 0 lỗi); corpus
không có hit vì fixture không sinh wrap này. Không phải lỗi người dùng nhìn
thấy; là giới hạn heuristic PDF-level của detector khi dòng wrap. Khuyến
nghị: cân nhắc miễn trừ X-in-bordered-cell ở lớp PDF của D15 hoặc xếp
candidate; không chặn V5.

Tái lập: `python3 -X utf8 generated_ho_so/_audit_v5/audit5_e2e_ui_data.py`.

## 6. CROSS-FIXTURE (PLI_M15 × 5) — **PASS-WITH-NOTES**

5 fixture qua `build_fixture` + `validate_fixture` (0 vi phạm V1–V4 cả 5) →
`Bridge.export` (format `both`): 5/5 `ok=True, errors=0`, **5 PDF khác nhau
hoàn toàn** (sha256 distinct):

| Fixture | Trang | Ngữ nghĩa xác minh |
|---|---|---|
| empty-paper | 4 | trống giá trị: ten không có trong PDF, 0 chữ X, 0 tick |
| valid-minimal | 5 | ten có mặt, không suffix dài |
| valid-full | 6 | ten có mặt, đầy đủ section |
| long-boundary | **28** | giá trị dài + suffix «kèm theo phần mô tả mở rộng số…» ép pagination (6→28 trang) |
| choice-variants | 6 | 3 chữ X trong PDF == 3 tick trong data; nhóm loại-trừ đã đăng ký `[chk_auto_khong, chk_co]` chọn **đúng 1** |

**Note (finding F-V5-3, severity LOW):** 2 checkbox «Mô hình tổ chức công
ty» của M15 — `chk_auto_hoi_dong_thanh_vien_giam_doc_hoac_tong_g…` và
`chk_auto_chu_tich_cong_ty_giam_doc_hoac_tong_giam…` — không nằm trong nhóm
loại-trừ nào (registry `EXCLUSIVE_GROUPS` / `chk_groups`), nên
choice-variants tick **cả hai** → PDF trang 3 hiện đồng thời «X Hội đồng
thành viên…» và «X Chủ tịch công ty…» — hai mô hình quản trị loại-trừ lẫn
nhau về pháp lý. Lỗi thuộc **lớp dữ liệu fixture** (registry nhóm), không
phải đường export — exporter render payload trung thực. Khuyến nghị: đăng ký
thành nhóm cho cặp này (hoặc chặn tick-đồng-thời cho các chk «auto mô
hình»); không chặn V5.

Tái lập: `python3 -X utf8 generated_ho_so/_audit_v5/audit6_cross_fixture.py`;
PDF bằng chứng tại `_audit_v5/crossfixture/PLI_M15_<fixture>.pdf`.

---

## Phạm vi & NOT-RUN

- Cả 6 mục được giao đều **ĐÃ CHẠY** — không có mục NOT-RUN.
- Ngoài phạm vi 6 mục: concurrency 2 runner song song (nêu trong bảng phạm vi
  PLAN 3.2 nhưng không thuộc 6 mục assigned của audit này) **không được
  tái lập** bởi audit này — suite `tools/test_export_concurrency` và con số
  runner 58/0/0 thuộc evidence của executor, auditor không xác nhận lại.

## OVERALL — **PASS-WITH-NOTES**

Từ nút Export đến file người dùng cầm: **không tìm thấy lỗi nào trên 6 phép
kiểm** — word-open 91/91 thật (Word 16.16.27), xuất xác định 100% về nội
dung (lệch duy nhất metadata dấu thời gian), ZIP đúng payload, manifest ==
đĩa tuyệt đối 455/455 record (F4 đóng), E2E từ dữ liệu UI ra PDF đúng slot/
đúng ô tick/đủ dòng bảng, 5 fixture tạo 5 hồ sơ phân biệt đúng ngữ nghĩa.
2 note LOW (F-V5-2 detector heuristic khi dòng bảng wrap; F-V5-3 registry
nhóm loại-trừ thiếu cặp «mô hình tổ chức» của M15) đều thuộc lớp
detector/fixture, không thuộc đường export — khuyến nghị đưa vào backlog
phase sau, không chặn checkpoint V5.

*auditor/6v-export — 2026-09-05*
