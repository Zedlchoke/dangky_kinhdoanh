# P2 — Contract dự kiến cho 4 table component

Trạng thái: **LOCKED v1 — Lead review 2026-08-27**. Tài liệu này khóa contract
*du kiến* cho `editable-grid`, `fixed-matrix`, `nested-grid`, `output-table`
theo taxonomy PLAN.md, hiện trạng UI (`app_web/ui/form-domain.js`, `render.js`,
`app.js`) và census `app/data/table_specs/manifest.json` (`table-manifest-v1`).
baseline implement P2. Các quyết định pháp lý D1–D7 vẫn độc lập và không được
suy diễn từ contract kỹ thuật này.

> **REBASE 2026-08-26 theo HEAD `bdc2d03`** — mục 1 (`editable-grid`) đã được
> cập nhật theo code thực tế sau merge P1-UI/P1.1/P2.0: metadata **form-scoped**
> (`FORM_GRID_META` + resolver `getGridMeta`), **activeWhen** (selector
> `checkedKey`/`valueOf` là nguồn chính, `minFilledRows` chỉ INTERIM),
> `mkGrid` **deep clone** toàn bộ metadata, **export conflict guard**
> (`exportLoopsStrict` fail-loud) và **focus sau row-op** ĐÃ CÓ trong code.
>
> **REBASE 2026-08-27 theo HEAD `972e765`** — các mục 2–4 không còn "chưa có
> code": module `fixed-matrix.js`/`nested-grid.js`/`output-table.js` cùng
> fixture/test production đã merge (`5e3381b`, `bc8cbb4`, `0e25d93`) và PASS
> độc lập qua release runner; phần CHƯA CÓ THẬT là wiring runtime/draft/export
> và generator deep integration — see bảng gap mục 5. Schema contract v1 giữ
> nguyên.
> Số liệu kiểm chứng tại HEAD: 31 dynamic tables = 31
> loop blocks; 9/9 loop mới (5 PLI_M72 + 4 PLII_M02) có meta form-scoped;
> suite Node gồm 11 file (thêm `test_m72_activation.js` 45 PASS,
> `test_p20_hardening.js` 56 PASS).

Phân bố hiện có (manifest, 111 section): editable-grid 43 · fixed-matrix 47 ·
nested-grid 7 · output-table 6 · (ngoài phạm vi P2: prose-block 3,
scalar-fields 4, source-contamination 1).

---

## 0. Nguyên tắc chung cho cả 4 loại

1. Spec JSON (theo nhóm domain dưới `tools/form_specs/` hoặc
   `app/data/table_specs/`) là nguồn chân lý; generated artifacts
   (form_maps/templates/blocks) chỉ do Lead regenerate, không sửa tay.
2. Mỗi section có `section_id`, `semantic_key`, `source_evidence`
   (template + heading + anchor) — kế thừa đúng shape entry manifest.
3. Dữ liệu store giữ `{values, checks, loops}`; mọi dòng lặp mang `_row_id`
   ổn định, bị loại khỏi payload export.
4. Canonical key backward-compatible: đổi loop name phải có version +
   migration + test (PLAN, "Kiến trúc generator và schema mới" mục 6).
5. Validation trả `error[]` đúng contract `docs/htkk-ui-contract.md`
   (`{key, docId, code, message, severity}`), severity `blocking` chặn export,
   `warning` chỉ hiển thị.

---

## 1. `editable-grid` — danh sách số dòng thay đổi

### 1.1 Mục đích / khi nào dùng

Người dùng được thêm/xóa/sắp xếp dòng: ngành nghề, thành viên/cổ đông/chủ sở
hữu hưởng lợi, thành viên hộ gia đình, người đại diện ủy quyền, chi nhánh/
địa điểm liệt kê, tài liệu kèm theo. 43 section trong manifest.

### 1.2 Hiện trạng đã có (không viết lại)

| Thành phần | Vị trí | Nội dung |
|---|---|---|
| `GridCtl` | `app.js:75` | Thuần, không DOM: `addRow/deleteRows/clearRows/moveRow/duplicateRow/setExclusiveRadio/exportLoops/exportLoopsStrict/vsicResolve`; thao tác theo `_row_id`, duplicate bỏ `duplicateKeys` |
| `GRID_META` | `form-domain.js:129` | `{label, minRows, maxRows, required, allowAdd/allowDelete/allowReorder, confirmDeleteNonEmpty, requirePrimary, columns[{tag,type,required,col}], duplicateKeys, outputOnlyTags, autoName}` — giờ là **fallback toàn cục** của resolver, không còn map duy nhất |
| `FORM_GRID_META` | `form-domain.js:341` | Metadata **form-scoped theo mẫu**: `PLI_M72` (5 loop ngành loại hình) + `PLII_M02` (4 vùng ngành độc lập) — mỗi entry có `semanticKey` khớp `dynamic_tables.semantic_key` trong `app/data/form_maps.json`; resolver `getGridMeta({docId, loop, semanticKey})` (`form-domain.js:488`) theo thứ tự docId+semanticKey → docId+loop → `GRID_META` global → null; string-call `getGridMeta('<loop>')` giữ backward compat; `registerFormGridMeta(formId, fm)` (`form-domain.js:476`) nạp meta lúc runtime |
| ActiveWhen | `evalActiveWhen/activationModeOf/isActiveGrid` `form-domain.js:677/705/714` | Selector `checkedKey`/`valueOf{key,equals}` là nguồn chính; `minFilledRows` chỉ INTERIM chờ owner (PLI_M72); inactive → 0 lỗi validation |
| Deep clone | `deepCloneVal/mkGrid` `form-domain.js:297/315` | Meta trả về clone SÂU `columns/autoName/duplicateKeys/outputOnlyTags/activeWhen` — mutate một chỗ không lan sang `GRID_META` gốc hay loop/mẫu khác (negative test trong `test_p20_hardening`) |
| Stable row id | `makeRowId/normalizeStoreLoops` `form-domain.js:506/515` | `'r<seq>_<rand>'`, gán idempotent khi nạp draft |
| Validation | `validateGridLoop` `form-domain.js:726` | Lỗi key `"loop:<name>:<row_id>[:<tag]"`; code `INDUSTRY_REQUIRED/MIN_ROWS/MAX_ROWS/ROW_INCOMPLETE/VSIC_INVALID/DUPLICATE_*/PRIMARY_INDUSTRY_REQUIRED/MONEY/PERCENT_SUM` |
| Renderer | `render.js` render loop | `.loop-table[data-loop]`, `tr[data-row-id]`, cụm `.loop-btns[data-act=add|dup|del|clear|up|down]`, blankRows, `.btable-wrap` cuộn ngang |
| Export | `exportLoops/exportLoopsStrict` `app.js:217/379` | Bỏ field nội bộ `_*`, map `la_nganh_chinh` → `'X'/''`; conflict guard + lọc grid inactive-theo-selector (xem 1.4) |
| Focus sau row-op | `focusTagOfGrid/nextSelAfterDelete/focusGridRow` `app.js:1101/1122/1147` | Add/duplicate focus ô mã ngành (hoặc editable đầu theo meta); delete giữ selection bám `_row_id`; không bao giờ ném exception |

### 1.3 Trạng thái sau rebase (HEAD `bdc2d03`)

**ĐÃ CÓ trong code** (không còn là gap):

- **Metadata form-scoped**: `getGridMeta({docId, loop, semanticKey})` resolve
  theo thứ tự docId+semanticKey → docId+loop → `GRID_META[loop]` global →
  null; string-call `getGridMeta('<loop>')` giữ nguyên hành vi cũ; runtime có
  `registerFormGridMeta`. Cùng tên loop ở hai mẫu khác nhau không còn đè key:
  PLI_M72 (5 loop) và PLII_M02 (4 loop, trong đó vùng C.3 dùng canonical
  `ds_nganh` với `semanticKey: 'nganh_hien_tai'`) đều tự khai cột riêng.
- **ActiveWhen**: selector (`checkedKey` / `valueOf{key,equals}`) là NGUỒN
  CHÍNH quyết định grid active; khi KHÔNG khai selector, `minFilledRows` chỉ
  là cơ chế **INTERIM chờ owner chốt loại hình PLI_M72** (trạng thái BLOCKED,
  khuyến nghị Option B — xem `docs/m72_activation_proposal.md`). Helper audit:
  `activationModeOf(meta)` → `null | 'selector' | 'interim-filled-data'`,
  `isActiveGrid(meta, rows, store)` thuần dùng chung cho validator + export
  guard. Grid inactive → 0 lỗi validation.
- **Deep clone metadata**: `mkGrid` clone SÂU toàn bộ field qua
  `deepCloneVal` — mutation isolation có negative test.

**VẪN LÀ GAP**:

- Cross-field rules liên dòng/liên bảng (tổng vốn, % được đại diện) chưa có
  slot khai báo; đang hard-code qua `moneyTags/percentTags`.
- Keyboard di chuyển giữa ô/dòng và a11y lưới (arrow key, `aria-rowcount`)
  mới dừng ở mức focus sau row-op theo meta/`_row_id`.

### 1.4 Activation & export guard (P1.1 + P2.0 hardening)

Shape `activeWhen` khai báo trong meta (đánh giá thuần trên store, không
hard-code form ID):

```jsonc
{
  "activeWhen": {
    "checkedKey": "chk_lh_tnhh_2tv",              // selector checkbox (store.checks)
    // hoặc valueOf: { "key": "dn.loai_hinh", "equals": ["CTCP","DHDN"] }  // selector giá trị (store.values)
    "minFilledRows": 1                            // CHỈ khi không có selector -> INTERIM
  }
}
```

- `checkedKey` + `valueOf` cùng khai → AND (cả hai thoả); so giá trị sau trim,
  phân biệt hoa/thường; có selector thì `minFilledRows` bị BỎ QUA.
- **Export guard** trong `exportLoops` (`app.js:217`): grid inactive-theo-
  **selector** → bỏ toàn bộ rows khỏi payload DOCX; grid INTERIM vốn không có
  dòng dữ liệu → payload giữ nguyên hành vi cũ 100%.
- **Conflict guard** chống "first-doc-wins âm thầm": `collectLoopSides`
  (`app.js:299`) resolve meta ĐÚNG resolver cũ cho từng docId rồi gom các side
  {docId, semanticKey, metaRef} khác nhau về REFERENCE. Short-circuit: mọi mẫu
  trỏ cùng một object (điển hình là cùng fallback global) → tương đương tuyệt
  đối, không flag. Có ≥2 reference khác nhau mới so signature export contract
  `{requirePrimary, autoNameCodeTag/autoNameNameTag, colTags (sort),
  activationModeOf}`; signature BẰNG coi là tương đương (vd clone `mkGrid`
  của `PLII_M02.ds_nganh` vs bản global); LỆCH → conflict có cấu trúc:

```jsonc
{
  "code": "EXPORT_LOOP_CONTRACT_CONFLICT",
  "loop": "nganh_bo_sung",
  "winner": {"docId": "PLI_M12", "semanticKey": null, "signature": {/*…*/}},
  "sides": [{"docId": "PLI_M12", "semanticKey": null, "signature": {/*…*/}},
            {"docId": "PLII_M02", "semanticKey": "nganh_bo_sung", "signature": {/*…*/}}],
  "reasons": ["tap tag cot: [ma_nganh|ten_nganh] != [ma_nganh|ten_nganh_bo_sung]"]
}
```

  Combo thật PLI_M12 (global) + PLII_M02 (scoped) bị chặn loud; clone-vs-global
  cùng signature xuất bình thường. `exportLoops` ghi report vào
  `GridCtl.lastExportConflicts`, payload giữ first-wins (tương thích caller
  cũ); đường export THẬT đi qua **`exportLoopsStrict` (`app.js:379`) — chỗ
  duy nhất** ném lỗi `EXPORT_LOOP_CONTRACT_CONFLICT`; `buildExportData`/
  `doExport` đã wire qua đúng một chỗ này.
- **Focus sau row-op** (`focusTagOfGrid/nextSelAfterDelete/focusGridRow`
  `app.js:1101/1122/1147`): add/duplicate focus ô mã ngành nếu grid có cột
  `ma_nganh`, ngược lại ô editable đầu tiên theo meta columns; delete giữ
  selection bám `_row_id` (dòng kề theo index, clamp cuối); thao tác row-op
  luôn thành công kể cả khi focus thất bại.

### 1.5 Shape JSON đề xuất xuất từ spec

```jsonc
{
  "kind": "editable-grid",
  "section_id": "ndd_pl_sau_thay_doi",
  "loop": "ds_ndd_pl_sau_thay_doi",      // loop docxtemplater {#loop}{/loop}
  "semantic_key": "ds_ndd_pl_sau_thay_doi",
  "stt": {"mode": "generated"},           // {_stt} tự sinh 1-based, không lưu
  "min_rows": 1, "max_rows": null,
  "required": false,
  "policy": {"allow_add": true, "allow_delete": true, "allow_reorder": true},
  "columns": [
    {"tag": "ho_ten", "inputType": "text", "required": true},
    {"tag": "so_cccd", "inputType": "cccd"},
    {"tag": "chu_ky", "inputType": "outputOnly"}
  ],
  "duplicate_keys": ["so_cccd"],
  "totals": [],                            // thường rỗng; xem fixed-matrix
  "cross_field_rules": [],
  "active_when": []                        // shape spec-side CHƯA khóa; cơ chế runtime đã có:
}                                          // activeWhen{checkedKey|valueOf|minFilledRows} xem 1.4
```

`inputType` hợp nhất type hiện có của `GRID_META` (`text|money|percent|
checkbox|radio|readonly|vsic|outputOnly`). `min_rows/max_rows` đếm dòng CÓ
dữ liệu, vi phạm không khóa thao tác, chỉ validator chặn trước export (giữ
đúng chính sách hiện tại).

### 1.6 Renderer/controller/generator/validation

- Renderer sinh bảng từ blocks loop + meta form-scoped (đã đọc qua
  `getGridMeta({docId, loop, semanticKey})`); ẩn nút theo `policy`; giữ hành
  vi confirm-xóa-dòng-có-dữ-liệu.
- Controller đã mở rộng GridCtl bằng wrapper đọc meta form-scoped + focus sau
  row-op; KHÔNG đổi semantics hàm thuần đã test. Phần còn lại của P2 chỉ thêm
  slot cross-field, không đụng semantics cũ.
- Generator: anchor/boundary quanh heading section (như spec PLII_M02:
  `anchor` + `drop_until` + `occurrences[nth]`), gắn `{_stt}` khi `stt.mode =
  generated`, bảo toàn tag `la_nganh_chinh` dạng ô đánh dấu X.
- Validation: tái sử dụng `validateGridLoop` (đã hiểu activeWhen); rule mới
  (cross-field) đăng ký qua slot `cross_field_rules` thay vì hard-code.

### 1.7 Draft migration & export gate

- Draft v2 giữ nguyên; migration chỉ thêm: gán `_row_id` thiếu (idempotent),
  đổi tên loop legacy → canonical khi có mapping (tiền lệ
  `ds_nganh_kinh_doanh → ds_nganh`).
- Export gate hai lớp: (1) conflict guard — đường export thật đi qua
  `exportLoopsStrict`, ném lỗi `EXPORT_LOOP_CONTRACT_CONFLICT` khi các mẫu
  resolve cùng loop sang contract khác nhau (xem 1.4); (2) validation gate —
  chặn khi còn lỗi `blocking` của bất kỳ bảng nào trong hồ sơ. Payload bỏ
  `_row_id` và lọc grid inactive-theo-selector.

---

## 2. `fixed-matrix` — bảng dòng pháp lý cố định

### 2.1 Mục đích / khi nào dùng

Tên dòng do biểu mẫu quy định, người dùng chỉ điền giá trị: nguồn vốn điều lệ
(5 dòng + Tổng cộng), tài sản góp vốn (6 dòng + Tổng số), cơ cấu loại cổ phần
và cổ phần chào bán, bảng chỉ tiêu đăng ký thuế đánh số cố định, nhóm lựa chọn
(khu công nghiệp, BHXH phương thức đóng, mô hình tổ chức). 47 section — nhóm
lớn nhất, ưu tiên P3 `capital-assets`.

### 2.2 Shape JSON đề xuất

```jsonc
{
  "kind": "fixed-matrix",
  "section_id": "nguon_von_dieule",
  "semantic_key": "nguon_von_dieu_le",
  "fixed_rows": [
    {"id": "von_nsnn",        "label": "Vốn nhà nước đầu tư",     "cells": [...]},
    {"id": "von_tu_nhan",     "label": "Vốn tư nhân"},
    {"id": "von_nuoc_ngoai",  "label": "Vốn nước ngoài"},
    {"id": "von_khac",        "label": "Loại nguồn vốn khác",
     "detail_required_when_filled": true},
    {"id": "tong_cong",       "label": "Tổng cộng", "output_only": true}
  ],
  "columns": [
    {"tag": "loai_nguon_von",          "inputType": "readonly"},
    {"tag": "so_tien_vnd_va_tuong_duong","inputType": "money"},
    {"tag": "ty_le",                   "inputType": "percent", "computed": true}
  ],
  "stt": {"mode": "none"},                 // bảng nguồn vốn không có STT
  "colspan": [/* ô gộp ngang nếu mẫu có */],
  "totals": [
    {"id": "tong_cong", "formula": "sum(so_tien_vnd_va_tuong_duong)",
     "target": "outputOnly"}
  ],
  "cross_field_rules": [
    {"rule": "tong_cong == von_dieu_le", "severity": "blocking"},
    {"rule": "sum(ty_le) == 100 khi co ke khai", "severity": "warning"}
  ],
  "active_when": []
}
```

Điểm khác editable-grid: `fixed_rows` thay `min/max_rows`; KHÔNG cho xóa dòng;
dòng tổng là `outputOnly` computed, không lưu hai nguồn số liệu mâu thuẫn.

### 2.3 Renderer/controller/generator/validation

- Renderer vẽ đủ các dòng pháp lý kể cả khi trống (blank row theo mẫu);
  ô tổng readonly, cập nhật khi input thay đổi; không có nút add/delete.
- Controller chỉ ghi giá trị vào `checks/values` theo `(semantic_key, row.id,
  column.tag)`; khóa dòng `output_only`.
- Generator: dựng `w:tbl` thay chuỗi paragraph rời (hiện trạng missing_grid ở
  PLI_M01–M05, M12), anchor/boundary để không xóa paragraph bảng kế tiếp;
  idempotent hai lần chạy giống nhau.
- Validation: `MONEY` cho từng ô tiền, `PERCENT_SUM`, rule đối chiếu vốn
  điều lệ blocking (PLAN inventory B), giá trị không âm, ngoại tệ phải có loại
  tiền, "tài sản khác/vốn khác" phải có mô tả khi > 0.

### 2.4 Draft migration & export gate

- Draft: dữ liệu lưu dạng phẳng `values["<semantic_key>.<row>.<tag>"]` —
  migration không cần đổi shape; chỉ thêm binding cho ô từng thiếu token
  (vd `chk_bc_03_thang` PLI_M01).
- Export gate: tổng computed PHẢI được tính lại lúc export (không tin giá trị
  lưu); lỗi đối chiếu vốn blocking chặn DOCX.

---

## 3. `nested-grid` — bảng nhiều tầng/cột nhóm

### 3.1 Mục đích / khi nào dùng

Bảng thành viên/cổ đông phức tạp: cá nhân/tổ chức khác nhau, nhóm cột
"Loại tài sản, số lượng, giá trị tài sản góp vốn", người đại diện ủy quyền với
"Thời điểm đại diện phần vốn". 7 section (PLI_M02, PLI_M12, PLI_M15, 4 bảng
PLI_M72) — tất cả đang `missing_grid`.

### 3.2 Shape JSON đề xuất

```jsonc
{
  "kind": "nested-grid",
  "section_id": "nddpl_uy_quyen_chu_so_huu",
  "loop": "ds_nddpl_uy_quyen_chu_so_huu",
  "semantic_key": "ds_nddpl_uy_quyen_chu_so_huu",
  "header_rows": [                        // bảo toàn header nhiều hàng
    [{"text": "STT", "rowspan": 2}, {"text": "Tên người đại diện", "rowspan": 2},
     {"text": "Phần vốn góp", "colspan": 3}],
    [{"text": "VNĐ"}, {"text": "Ngoại tệ"}, {"text": "Tỷ lệ %"}]
  ],
  "row_groups": [                         // nhóm dòng cá nhân/tổ chức
    {"group_id": "ca_nhan", "match": "gtinh!=null", "extra_columns": [...]},
    {"group_id": "to_chuc", "match": "ten_to_chuc!=null", "extra_columns": [...]}
  ],
  "columns": [ /* phẳng sau khi khai triển, mỗi cột có col_index vật lý */ ],
  "discriminator": {"tag": "loai_dong", "values": ["ndd_pl", "ndd_uy_quyen"]},
  "min_rows": 0, "max_rows": null,
  "totals": [ /* vd tong_gia_tri_duoc_dai_dien */ ],
  "cross_field_rules": []
}
```

Ràng buộc bắt buộc (PLAN taxonomy 3): renderer/generator bảo toàn header nhiều
hàng, `colspan`, `rowspan`; KHÔNG làm phẳng khiến mất cột.

### 3.3 Renderer/controller/generator/validation

- Renderer dựng `<thead>` nhiều hàng từ `header_rows`; mỗi dòng dữ liệu vẫn
  mang `_row_id`; ô gộp chỉ ở header, vùng nhập luôn 1 ô/cột.
- Controller: thêm/xóa dòng theo policy như editable-grid; chọn `row_group`
  quyết định tập cột bắt buộc (`ROW_INCOMPLETE` theo nhóm).
- Generator: rebuild bảng từ header nối dính ("STTTên người đại diện…") —
  phải tách cột theo regex fold như `detect/cols` hiện có nhưng cho phép
  khai báo `header_rows` thủ công khi nguồn mất cấu trúc; anchor occurrence
  (nth) cho PLI_M72.
- Validation: duplicate key theo `discriminator` (một CCCD/MST không xuất hiện
  ở cả hai vai trò), tổng % được đại diện ≤ 100, tổng giá trị đối chiếu vốn.

### 3.4 Draft migration & export gate

- Draft: rows phẳng trong `loops[<loop>]`, cột nhóm là field thường; migration
  chỉ thêm `_row_id`/đổi tên loop có version.
- Export gate: kiểm tra đủ số cột vật lý khi render DOCX (không lệch cột —
  Acceptance Gate #8), rowspan/colspan giữ nguyên khi xuất.

---

## 4. `output-table` — bảng do cơ quan/engine tạo

### 4.1 Mục đích / khi nào dùng

Bảng do CQĐKKD phát hành hoặc chỉ để in: quyết định thu hồi (PLI_M63), thông
báo CQB (PLI_M66/M68/M75), khối chữ ký (PLI_M70/M71). 6 section, tất cả status
`output_only`.

### 4.2 Shape JSON đề xuất

```jsonc
{
  "kind": "output-table",
  "section_id": "chu_ky_nguoi_nop_nguoi_nhan",
  "semantic_key": "chu_ky_tiep_nhan_ho_so",
  "grid": {"rows": 2, "cols": 1, "labels": ["NGƯỜI NỘP", "NGƯỜI NHẬN"]},
  "inputs": [],                            // không ô nhập nào
  "active_when": [],
  "notes": "Giữ grid khi xuất DOCX dù không nhập liệu (PLAN mục G)"
}
```

### 4.3 Hành vi

- Renderer: vẽ khung/lưới chỉ đọc, không sinh input; vẫn giữ grid trong DOCX
  (không được bỏ grid chỉ vì UI không nhập).
- Generator: giữ nguyên cấu trúc bảng nguồn, đánh dấu `output_only` để audit
  không đòi input; biến thể Điều 2–4 (PLI_M63) render có điều kiện theo
  trường hợp — cần `active_when` sau khi legal chốt chủ thể nhập.
- Validation/export: không có rule dữ liệu; export gate chỉ kiểm tra presence
  của grid và không có tag sót trong DOCX.

---

## 5. Bảng gap tổng hợp theo component

| Component | Đã có | Gap P2 |
|---|---|---|
| editable-grid | GridCtl, GRID_META + FORM_GRID_META (`getGridMeta` form-scoped), activeWhen selector/INTERIM, mkGrid deep clone, conflict guard `exportLoopsStrict`, focus sau row-op, `_row_id`, validateGridLoop, renderer loop, exportLoops | slot `cross_field_rules`, keyboard/a11y lưới; owner chốt selector M72 để bỏ INTERIM |
| fixed-matrix | module `app_web/ui/fixed-matrix.js` + fixture/test PLI_M03/M04 đã merge (`5e3381b`) — **chưa nối runtime/generator** (0 reference trong UI, soi ngày 2026-08-27) | wire dispatcher/runtime, computed totals recompute lúc export, generator rebuild anchor/boundary |
| nested-grid | module `app_web/ui/nested-grid.js` + fixture/test N1 đã merge (`bc8cbb4`) — **chưa nối runtime/generator** | wire dispatcher/runtime, generator header_rows/rowspan/colspan/discriminator, occurrence M72 |
| output-table | module `app_web/ui/output-table.js` + fixture/test O1/O2 đã merge (`0e25d93`) — **chưa nối runtime/generator** | wire dispatcher/renderer presence gate, audit `output_only`, render có điều kiện |

> Cập nhật trạng thái 2026-08-27 (HEAD `972e765`): ba module trên là code
> standalone PASS độc lập qua release runner; chấp nhận Gate R2 khi đã wire vào
> runtime/draft/validation/DOCX và generator deep-idempotent. Contract v1
> trường tên/severity KHÔNG đổi.

> Lưu ý review: các shape trên là đề xuất ban đầu từ census; Lead cân nhắc
> thống nhất tên trường (`fixed_rows` vs `fixedRows`, snake_case hiện tại của
> spec) trước khi khóa contract.
