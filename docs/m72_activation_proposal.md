# PROPOSAL: M72 Activation Contract (selector loại hình DN cho PLI_M72)

> **TRẠNG THÁI: PRODUCTION WIRING = BLOCKED** — chờ contract owner chốt
> phương án selector + dữ liệu pháp lý. CƠ CHẾ (mechanism) đã triển khai xong,
> test phủ, sẵn sàng nhận khai báo metadata khi owner quyết định.
>
> Agent: P1.1 A (M72 activation) · Worktree `p11/a-m72-activation` · base `0ee70d3`
> Files đụng tới: `app_web/ui/form-domain.js`, `app_web/ui/app.js`,
> `app_web/test_m72_activation.js` (mới). KHÔNG đụng `tools/**`, `app/data/**`,
> `use_cases.json`.

## 1. Evidence audit (đã xác minh lại trên worktree)

1. **PLI_M72 blocks không có bất kỳ tín hiệu chọn loại hình nào.**
   `app/data/blocks/PLI_M72.json`: 149 blocks = **144 paragraph + 5 loop**
   (`ds_nganh_dntn`, `ds_nganh_tnhh_1tv`, `ds_nganh_tnhh_2tv`, `ds_nganh_ctcp`,
   `ds_nganh_dhdn`, mỗi loop 3 cột `ten_nganh/ma_nganh/la_nganh_chinh`).
   **0 block kiểu `chk`**, 0 field key chứa "loai_hinh". Toàn bộ 35 key
   `chk_*` trong kho blocks thuộc các mẫu khác; key gần nhất về loại hình là
   `chk_tt_chuyen_doi_loai_hinh` (PLI_M02 — checkbox "thay đổi loại hình" của
   thủ tục thay đổi, KHÔNG phải selector của M72).
2. **Không case nào tham chiếu mẫu 72.** `use_cases.json` có 27 case; case
   `cong_bo_noi_dung_dkdn` trỏ `mau: 32` (PLI_M32). `dong_bo` không nhắc M72.
   `form_maps.json` có định nghĩa PLI_M72 (fields cũng không có selector).
   → PLI_M72 hiện **không reachable** qua luồng chọn case thông thường
   (`formIdOf` chỉ map các form nằm trong `case.forms`).
3. **Hiện trạng meta**: `FORM_GRID_META.PLI_M72` gồm 5 loop clone từ
   `GRID_META.ds_nganh` (`required:false/minRows:0`) +
   `activeWhen:{minFilledRows:1}`; `evalActiveWhen` đánh giá thuần trên store.
4. **exportLoops xuất TẤT CẢ loops có trong store**, resolve meta theo docId
   đầu tiên có loop trùng, không lọc theo trạng thái active (trước bản này).
5. **Draft cũ** (`profiles/*.json`, shape `case_id/forms/shared/private/chk/
   tables` của app_tk): chỉ có `chk_tt_chuyen_doi_loai_hinh` rỗng trong draft
   TNHH-2TV/CTCP — không phải signal chọn loại hình cho M72; không draft v2
   nào chứa M72. Không có `ui_layouts/PLI_M72.json`.

**Kết luận: HIỆN KHÔNG CÓ canonical field/case-context đủ tin cậy để xác định
loại hình DN cho M72.** Khớp kỳ vọng Lead. Vì vậy mọi mapping pháp lý
(check nào = loại hình nào) bị CẤM tự tạo; chỉ làm nền cơ chế data-driven.

## 2. Mechanism đã triển khai (data-driven, không hard-code form ID)

### 2.1 Shape meta mở rộng (app_web/ui/form-domain.js)

```js
activeWhen: {
  checkedKey: 'chk_xxx',                    // selector kiểu checkbox (store.checks)
  valueOf: { key: 'dn.loai_hinh', equals: ['CTCP','DHDN'] } // selector kiểu giá trị (store.values)
  // , minFilledRows: N  // CHỈ fallback khi KHÔNG khai selector
}
```

### 2.2 Thứ tự ưu tiên (evalActiveWhen)

1. `activeWhen` **có selector** (`checkedKey` hoặc `valueOf`) → selector là
   **NGUỒN CHÍNH duy nhất** quyết định active; `minFilledRows` bị BỎ QUA
   (không cộng dồn). `checkedKey` + `valueOf` cùng khai → AND (cả hai thoả).
   So giá trị `valueOf` sau trim, phân biệt hoa/thường.
2. `activeWhen` **không selector** → `minFilledRows` là cơ chế **INTERIM chờ
   owner** (hiện trạng PLI_M72): grid chỉ active khi có ≥ N dòng CÓ DỮ LIỆU;
   grid trống không sinh lỗi nào. **Đây KHÔNG phải nguồn xác định loại hình
   chính thức** — đã ghi chú INTERIM tại từng meta production.
3. Không `activeWhen` → luôn active (hành vi cũ 100%).

### 2.3 Audit mode (activationModeOf) + helper

- `FD.activationModeOf(meta)` → `null` | `'selector'` |
  `'interim-filled-data'` — suy TRỰC TIẾP từ activeWhen nên không thể khai lệch.
- `FD.isActiveGrid(meta, rows, store)` — đánh giá active thuần (dùng chung
  validator + export guard).
- `FD.registerFormGridMeta(formId, fm)` — đăng ký meta form-scoped lúc
  runtime (test fixture dùng cái này; owner sau này có thể nạp metadata mà
  không sửa code validator).
- Validation giữ nguyên logic: inactive → 0 lỗi (kể cả warning); active mà
  trống + `required` → `INDUSTRY_REQUIRED` blocking; thiếu ngành chính →
  `PRIMARY_INDUSTRY_REQUIRED`.

### 2.4 Export guard (GridCtl.exportLoops trong app_web/ui/app.js)

- Grid **inactive-theo-selector** → bỏ toàn bộ rows khỏi payload DOCX
  (section không áp dụng phải rỗng trong văn bản).
- Grid inactive vì **INTERIM** → vốn không có dòng có dữ liệu → KHÔNG filter,
  payload giữ nguyên 100% hành vi cũ (có regression test chứng minh, kể cả
  dòng trống chỉ có `_row_id` và việc requirePrimary điền `la_nganh_chinh:''`).
- Grid không có `activeWhen` → không bị đụng.
- Lưu ý hợp đồng: guard chỉ áp dụng khi meta resolve ra là selector-mode;
  thứ tự `docIds` truyền vào vẫn quyết định meta thắng (meta đầu tiên theo
  thứ tự mảng) — đã có test ghi nhận hợp đồng này.

## 3. Các option selector cho owner

### Option A — Entry case dùng PLI_M72 + forms_oneOf nhóm 5 section giả lập
Thêm entry case (vd `cong_bo_noi_dung_dkdn_loai_hinh`) với `forms: [mau 72]`;
tách 5 section thành 5 "form" ảo trong cùng oneOf group `{ids:[...], max:1}`
để UI ép chọn đúng một phần.
- Ưu: dùng lại cơ chế oneOf có sẵn; không đụng blocks.
- Nhược: form ảo ≠ mẫu thật (payload/văn bản vẫn là M72 gộp); cần thay đổi
  Bridge/export để gom 5 id về một file DOCX; draft cũ lệch shape.

### Option B — Canonical checks key chọn loại hình ngay trong chính mẫu M72
Sửa template/blocks M72 thêm ô tick loại hình (vd 5 key `chk_lh_*`), meta mỗi
loop khai `activeWhen:{checkedKey:'chk_lh_<loai>'}`.
- Ưu: đúng ngữ nghĩa mẫu (người điền tick trên chính tờ khai); mechanism hiện
  tại hỗ trợ trọn gói (validation/export/draft); khớp cách các mẫu khác đã
  dùng `chk_*`.
- Nhược: phải regen template + blocks + census (thuộc gate Lead); draft cũ
  không mất gì (key mới thêm vào).

### Option C — Derive từ case loại hình thành lập đang chọn
Khi hồ sơ đang ở case loại hình tương ứng (DNTN/TNHH1TV/TNHH2TV/CTCP/DHDN),
tự suy section M72 active theo `caseId`; khai bằng
`activeWhen:{valueOf:{key:'@case_type', equals:[...]}}` hoặc mapping ngoài.
- Ưu: người dùng không phải tick lại; nhất quán với hồ sơ gốc.
- Nhược: M72 là mẫu công bố độc lập, có thể nộp ngoài ngữ cảnh thành lập →
  derive từ case là GIẢ ĐỊNH pháp lý, bắt buộc owner xác nhận; cần thêm nguồn
  dữ liệu "@case_type" vào store (chưa tồn tại).

## 4. Dữ liệu ảnh hưởng khi owner chốt

| Kênh | Option A | Option B | Option C |
|---|---|---|---|
| `use_cases.json` | +entry case (+oneOf) | giữ nguyên (hoặc thêm ghi_chu) | thêm mapping case→loại hình |
| blocks/template M72 | không đổi | **regen** thêm chk | không đổi |
| Draft cũ | không phá | không phá | cần suy @case_type lúc restore |
| FORM_GRID_META | đổi activeWhen 5 loop thành selector | như trái | như trái |

## 5. Test cần có khi owner chốt (ngoài suite hiện tại)

1. Fixture thật thay fixture giả: thay `SEL_KEYS` giả trong
   `test_m72_activation.js` bằng key/case owner chốt (file được tách sẵn để
   chỉ cần sửa fixture, không sửa assertion cơ chế).
2. E2E export DOCX: section không chọn in ra 0 dòng bảng (Python gate Lead,
   mở rộng `test_industry_change.py`).
3. Draft cũ → mới: hồ sơ đã lưu trước khi có selector vẫn validate/export đúng
   (interim data-driven vẫn chạy khi chưa tick).
4. forms_oneOf/checkFormSelection nếu chọn Option A: nhóm 5 section không vi
   phạm `FORM_ONEOF_EMPTY` khi chỉ dùng M72 standalone.

## 6. Khuyến nghị

**Option B** (canonical checks key trong chính mẫu M72): khớp ngữ nghĩa mẫu,
tận dụng nguyên cơ chế đã test, ít rủi ro draft cũ nhất. Chi phí là một lần
regen template/blocks thuộc gate Lead. Option C chỉ cân nhắc nếu owner xác
nhận M72 luôn nộp kèm hồ sơ loại hình xác định.

## 7. Rủi ro cần Lead review

1. **Thứ tự docIds trong exportLoops**: meta đầu tiên thắng — khi wiring
   production phải đảm bảo docId của mẫu selector đứng trước meta interim
   khác trùng loop name (không xảy ra hiện nay vì tên loop M72 là duy nhất).
2. **INTERIM vẫn cho phép dữ liệu ở nhiều section cùng lúc** (minFilledRows
   kích hoạt từng grid độc lập) — chấp nhận được vì M72 chưa reachable qua
   case; nhưng nếu lộ ra UI thì người dùng có thể điền 2 phần, validator sẽ
   soi cả hai (an toàn pháp lý hơn im lặng, khác thiết kế selector max-1).
3. `p1_b_verify_m72.py` FAIL sẵn tại HEAD (template copy thiếu tiêu đề cột
   `stt/ten nganh/ma nganh` vùng ds_nganh_tnhh_1tv) — **trước khi agent đụng
   mã**, thuộc Wave 2B/gate Lead; `test_industry_change.py` (6 PASS) vẫn bảo
   đảm structural 5 occurrence.
4. Selector so chuỗi trim + case-sensitive: nếu key giá trị tương lai dùng
   nhiều cách viết (vd "TNHH 1 TV") thì owner phải chuẩn hoá danh sách equals.

## 8. Bằng chứng kiểm thử (commit cơ chế + test)

- Node: `test_dom 58 · test_domain 64 · test_grid 108 · test_loop_prod 112 ·
  test_acceptance 46 · test_form_flow 38 · test_household_shared 10 ·
  test_form_grid_meta 87 · test_audit_p1_negative 37` — đều PASS, không tụt
  so baseline.
- Mới: `node app_web/test_m72_activation.js` → **45 PASS / 0 FAIL** phủ 8 yêu
  cầu + negative mutation-isolation + unit ưu tiên selector/interim.
- Python (gate Lead, chạy tay xác nhận không đụng artifact):
  `python tools/test_industry_change.py` → 6 PASS / 0 FAIL.
