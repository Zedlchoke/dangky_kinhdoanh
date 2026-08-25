# Contract UI "khai trực tiếp kiểu HTKK" — Pilot PLI_M02 + PLI_M06

Trạng thái: **ĐÃ CHỐT** (Giai đoạn 0). Mọi agent A/B/C/D phải tuân theo tài liệu này.
Nguyên tắc chung: `data-key` là canonical key duy nhất. Chỉ đồng bộ exact key.
Không rename key, không auto-gộp key chỉ vì nhãn giống nhau. Alias phải tường minh
trong metadata và có test.

---

## 1. fieldMeta contract (Agent A sở hữu)

Module: `app_web/ui/form-domain.js` (UMD như render.js: node require hoặc
`window.FormDomain`).

```js
FormDomain.getFieldMeta(key) -> meta | null

meta = {
  key:      string,            // canonical data-key
  label:    string,            // accessible name / nhãn lỗi
  type:     'text' | 'money' | 'email' | 'cccd' | 'mst'
          | 'number' | 'vsic', // 'text' mặc định nếu không khai báo
  required: boolean,           // thiếu giá trị => blocking error REQUIRED
  inputMode?: 'numeric'|'email'|'decimal',
  maxLength?: number,
  help?: string,               // hint hiển thị ở panel phải
  computed?: boolean           // ô tự tính (von_dieu_le khi autoSum) - readonly động
}
```

- Metadata khai báo **theo key** trong `FormDomain.FIELD_META` (map phẳng).
  Key không có metadata vẫn render input text tương thích ngược, chỉ có validation cơ bản.
- Loop tag metadata: `FormDomain.LOOP_META = { <loopName>: { label, minRowsFilled,
  moneyTags:[], percentTags:[] } }`. Ví dụ pilot:
  `ds_thanh_vien: { minRowsFilled: 1, moneyTags: ['von_dong_gop'], percentTags: ['ty_le_von'] }`.
- Rule tổng vốn giữ nguyên logic render.js (`TOTAL_RULES`): domain không nhân bản.

## 2. Validation error contract

```js
error = {
  key:      string,        // canonical data-key (hoặc '<loopName>.<tag>' cho rule bảng)
  docId:    string|null,   // PLI_M02 / PLI_M06 / null cho lỗi toàn hồ sơ
  code:     string,        // REQUIRED|EMAIL|CCCD|MST|NUMERIC|MONEY|VSIC|MIN_ROWS|PERCENT_SUM
  message:  string,        // tiếng Việt, người dùng đọc trực tiếp
  severity: 'blocking' | 'warning'
}
```

API thuần (không DOM):

```js
parseMoney(str) -> number|null       // '1.000.000'/'1000000'/'' -> số; rác -> null
formatMoney(n)  -> '1.000.000'       // luôn dấu '.' ngăn cách nghìn
validateField(meta, value, ctx) -> error[]          // ctx: {docId}
validateDocument(docId, blocks, store, ctx) -> error[]
validateDossier(docs, store, ctx) -> error[]        // docs=[{id,blocks}]
collectKeys(blocks) -> { keys:[], loops:{name:[tags]} }
```

- `ctx`: `{ vsicList }` (danh sách VSIC để check mã ngành; optional).
- Một lỗi duy nhất cho mỗi `(docId,key,code)` dù key xuất hiện nhiều lần trong mẫu;
  điều hướng focus vào instance đầu tiên.
- Chính sách tiền: ô nhập hiển thị `1.000.000`; dữ liệu store/export dùng đúng chuỗi
  đã format (render.js parse lại bằng `parseNum`, bỏ dấu '.'); tổng cộng trên số thật.

## 3. state bổ sung (Agent C sở hữu app.js)

```js
state.activeDocId : string|null   // id của MẪU DUY NHẤT đang hiển thị
state.dirty       : boolean       // có thay đổi chưa lưu
state.saveState   : 'unsaved'|'saving'|'saved'|'error'
                  // hiển thị: Chưa lưu / Đang lưu / Đã lưu / Lỗi lưu
state.errors      : error[]       // kết quả Kiểm tra gần nhất
state.selectedLoopRow : { [loopName]: rowIndex }   // chọn dòng bảng lặp
state.viewState   : { [docId]: { scrollTop, focusKey } } // phục hồi khi đổi tab
```

- Chỉ render **một** section `.page-a4[data-doc-id]` tương ứng activeDocId vào
  `#pages`. Đổi tab = re-render trung tâm từ store (store là nguồn chân lý nên dữ
  liệu chung tự "đồng bộ" giữa các mẫu), sau đó khôi phục scrollTop/focus của mẫu mới.
- Không rerender toàn trang khi gõ phím: chỉ mirror các input cùng data-key.

## 4. Draft version & migration

```json
// v2 (mới)
{ "v": 2, "caseId", "checkedForms":[], "activeDocId",
  "autoSum": bool,
  "viewState": { "<docId>": {"scrollTop":0,"focusKey":null} },
  "store": {"values":{},"checks":{},"loops":{}},
  "savedAt": "ISO-8601" }
```

- Migration v1→v2: `migrateDraft(d)`: nếu `v>=2` trả nguyên vẹn; nếu draft v1
  (có `store`) thì bổ sung `v=2, activeDocId=null, viewState={}, savedAt=null`.
  Draft không có `store` bị bỏ qua. Hàm nằm trong form-domain.js, có test.
- localStorage key giữ nguyên: `hoso_draft_autosave`.

## 5. DOM hooks giữa renderer (B) và controller (C)

| Hook | Renderer cấp | Controller dùng |
| --- | --- | --- |
| Panel active | `<div id="pages">` chứa đúng 1 `section.page-a4[data-doc-id="<id>"]` | setActiveDoc(id) → renderActiveDoc() |
| Tab | `#tabs [role="tab"][data-doc-id]`, active có `aria-selected="true"` + class `active` | click/keyboard chuyển tab thật |
| Input text | `input.fld[data-key][data-field-id][aria-label]` (+`.calc`,`.loop-fld`) | setKeyValue + mirrorKey |
| Checkbox | `input.chk-box[data-key][data-field-id]` | checks sync |
| Ô lỗi | class `invalid`, `aria-invalid="true"`, `aria-describedby="msg_<field-id>"` | controller tạo/tìm `<span id="msg_<field-id>" class="fld-msg">` ngay sau input |
| Required | `aria-required="true"` (từ fieldMeta.required) | — |
| Bảng lặp | `tbody tr[data-row-index]` trong `.loop-table[data-loop]`; nút `.btn-row-add`/`.btn-row-del` kèm `data-loop`; dòng chọn có class `row-sel` + `aria-selected` | chọn/thêm/xóa dòng |
| VSIC pop | `#vsic-pop .vsic-item.sel` | ArrowUp/Down/Enter/Escape |
| Save status | `#save-status` trong header | setSaveState() cập nhật text+class |
| Error panel | `#err-panel #err-list` | nhóm lỗi theo docId; item `button.err-item[data-doc-id][data-key]` |

- Stable field id: `f_<key sanitize>` (ký tự ngoài `[A-Za-z0-9_.:-]` thành `_`),
  trùng lặp trong cùng mẫu đếm thêm `_2`,`_3`… Ổn định giữa các lần render vì thứ
  tự block không đổi.
- Accessible name: `aria-label` = fieldMeta.label nếu có, fallback là text run
  tĩnh liền trước trong cùng đoạn/ô (renderer tự trích, tối đa ~90 ký tự).

## 6. Action IDs

| ID / selector | Hành vi |
| --- | --- |
| `#btn-check` | Kiểm tra mẫu hiện tại; `#chk-check-all` tick = toàn hồ sơ |
| `#btn-save` (Ctrl+S) | Lưu nhanh localStorage, saveState machine |
| `#btn-export`, `#btn-export2` | Xuất DOCX; CHẶN nếu còn lỗi blocking |
| `#btn-save-draft` / `#btn-open-draft` | Lưu/mở file .json qua Bridge |
| `#btn-reset` | Nhập lại (confirm khi dirty) |
| `#chk-autosum` | Tự cộng tổng vốn (giữ nguyên nghĩa cũ) |
| `.btn-row-add[data-loop]` / `.btn-row-del[data-loop]` | Thêm/xóa dòng bảng lặp; xóa dòng có dữ liệu phải confirm |
| `#sel-nhom` / `#sel-case` / `.form-tick` | Nhóm / thủ tục / chọn mẫu; đổi case khi dirty phải confirm |
| Ctrl+PageUp / Ctrl+PageDown | Tab trước / sau |
| Escape | Đóng VSIC popup |

## 7. Chính sách chặn export

1. `doExport()` chạy `validateDossier` trước.
2. Còn ≥1 lỗi `severity:'blocking'` → KHÔNG gọi Bridge.export; mở panel lỗi,
   toast rõ ràng "Không thể xuất: N lỗi cần sửa".
3. Chỉ lỗi `warning` → cho xuất, hiển thị cảnh báo.
4. Mock mode vẫn chặn export như cũ (thông báo cần Bridge).

## 8. Phạm vi pilot & giới hạn đã biết

- Pilot: `PLI_M02`, `PLI_M06`. Case pilot mới **cộng thêm** vào use_cases.json:
  `id="pilot_ui_m02_m06"` (không sửa case cũ nào).
- Block thật PLI_M06 (convert DOCX) **không có** ô `dn.ten_tieng_viet`; do đó demo
  "điền tên ở M02 → sang M06 thấy giá trị" đầy đủ ở chế độ mock (?mock=1, mock M06
  có ô này). Trên dữ liệu thật, các key thật sự chung (địa chỉ, ngày cấp, ndd.*,
  von_dieu_le…) vẫn đồng bộ đúng. Không tự ý chèn thêm ô vào block thật.
- Field chưa metadata hóa: mọi key ngoài danh sách FIELD_META pilot → validation cơ
  bản (none), render text bình thường. Rollout sau bổ sung dần.
