# UI sweep protocol — những gì đã phủ, những gì còn thiếu cho gate F2

> Đối chiếu harness hiện có (`app_web/test_full_sweep_inventory.js`, Lane B)
> với yêu cầu **Gate F2** của `PLAN.md` (mục "F2 — Full UI sweep 5.2 và
> runtime E2E"), và đề xuất phương án bổ sung bằng Playwright.
> **Tài liệu này chỉ ĐỀ XUẤT** — không cài framework mới, không sửa app_web/
> (quy tắc wave: framework Playwright chỉ lắp khi Lead mở F2).

## 1. Harness hiện có phủ gì (Lane B, chuỗi-HTML thuần, không jsdom)

Chạy: `node app_web/test_full_sweep_inventory.js`. Nguồn dữ liệu:
`app/data/use_cases.json` (28 use case — nguồn chân lý thủ tục, gồm
`forms_oneOf`) + `app/data/form_maps.json` (87 form id). Corpus sweep =
form id duy nhất từ inventory (**27 id** vì có case dùng chung mẫu) +
**60 id** ngoài inventory có trong form_maps = **87 form**; form có selector
(ví dụ `PLI_M72`) render thêm **từng option** của selector + store rỗng.

Từng form được assert trên chuỗi HTML render bằng đúng harness DOM production
(`ui/render.js` + `ui/form-domain.js`):

| Check | Nội dung |
|---|---|
| S1 | `app/data/blocks/<id>.json` + entry `form_maps` tồn tại cho mọi form |
| S2 | Render 2 lần liên tiếp **byte-identical** (determinism) |
| S3 | `console.error` = 0 toàn sweep (`console.warn` được đếm riêng) |
| S4 | Không `undefined` / `NaN` / `value="null"` lọt vào HTML (mọi biến thể) |
| S5 | Mỗi key input khai trong blocks có control `data-key="<key>"` trong ÍT NHẤT MỘT biến thể; key lạ đối chiếu form_maps/FIELD_META ghi chú INVENTORY-META |
| S6 | Section contracts: fixed-matrix đủ ô `<sk>.<row>.<tag>` (trừ output-only/readonly), nested-grid + output-table có component, **output-table KHÔNG có input** |
| S7 | **Inactive leakage**: `validateDocument` trên store rỗng không sinh blocking error nào trỏ vào loop/section đang INACTIVE (`activeWhen`, grid activation `selector`) |

Điểm mạnh: phủ TOÀN bộ form (không sampling), render thật bằng code
production, determinism + console + undefined/NaN + activeWhen là các assert
cứng, FAIL liệt kê form chờ Lead (không tự sửa blocks/specs).

## 2. Chưa phủ gì so với Gate F2

Gate F2 yêu cầu: "inventory phủ 100%, 0 missing control/column, 0 JS error,
**a11y suite PASS**; **draft/E2E/export assertions xanh**; census header-name
100% có verdict…". Mapping từng khoản PLAN F2:

| PLAN F2 | Trạng thái | Ghi chú |
|---|---|---|
| 1. Render 28 UC / 87 form / 5 variant M72; mọi key active có control | **ĐÃ PHỦ** (structural) | Phủ bằng chuỗi HTML; variant M72 đi qua selector logic của form-domain |
| 2. Slot tên DN/hộ; bảng ngành tên+mã+ngành chính; mọi column 4 table kind; nút add/delete/duplicate + output-only | **PHỦ MỘT PHẦN** | Column/cell presence + output-only đã assert (S5/S6); ngược lại: **nút bấm chỉ "tồn tại trong HTML"**, chưa assert khả năng click/gắn sự kiện; ngữ nghĩa "bảng ngành đủ tên+mã+ngành chính" và header-name mirror (`span.mirror-fld`) chưa có assert riêng |
| 3. 3 viewport, zoom 200%, keyboard-only, focus ring, ARIA name/role/state, error focus đúng field | **CHƯA PHỦ** | Harness chuỗi-HTML không có layout engine/DOM runtime — không đo được viewport, overflow, focus, ARIA |
| 4. Đổi form/variant, autosave, save/open JSON, reload draft cũ không mất dữ liệu | **CHƯA PHỦ** | Không có runtime app.js/store/bridge trong harness |
| 5. activeWhen: inactive không block validation **và không lọt export** | **PHỦ NỬA** | S7 phủ chiều validation-block; chiều **lọt export** (payload chứa key section inactive) chưa ai assert |
| 6. Fixture `empty/minimal/full/long/choice` + payload người dùng thật | **CHƯA PHỦ** | Harness chỉ render store rỗng + từng option selector |
| 7. Console error / undefined-null-NaN / overlap / overflow ngang / control không click được | **PHỦ NỬA** | Console + undefined/NaN có (S3/S4) nhưng là console của **render.js trong Node**, không phải console runtime WebView2/Chromium; overlap/overflow/clickability cần layout thật |
| 8. HEADER-NAME-SYNC (mirror cập nhật ngay, không stale khi sửa/đổi draft/form/variant) | **CHƯA PHỦ** | Hành vi runtime qua store — phải test trên DOM sống; `PLI_M32` là fixture bắt buộc |

Kết luận: harness Lane B là **nền structural** (khoản 1 và nửa khoản 7);
5 nhóm còn thiếu đều cần **DOM sống + layout thật + runtime bridge** — đúng
NOTE thiết kế trong header của chính harness: "nâng cấp lên
jsdom/playwright + axe-core khi Lead mở F2".

## 3. Đề xuất bổ sung bằng Playwright (CHỈ ĐỀ XUẤT)

### 3.1 Hai chế độ chạy (chọn khi Lead mở F2; có thể làm cả hai)

- **A — Chromium + bridge shim (dev-loop, chạy mọi OS):** serve
  `app_web/ui/index.html` (`--mock=1` đã có sẵn đường mock), chèn init script
  stub `window.pywebview.api` trả JSON thật từ `app/data/` (list_cases/
  get_blocks/form maps) và bắt payload export/draft vào biến kiểm chứng.
  Lợi: chạy được trong CI/CI-macOS; chi phí thấp.
- **B — bắn thẳng vào WebView2 thật (evidence F2/F6):** đặt
  `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222` khi
  launch `app_web/main.py`, rồi
  `chromium.connectOverCDP('http://127.0.0.1:9222')`. Đây là chế độ duy nhất
  tính evidence, vì **Chromium PASS không thay WebView2 PASS** (PLAN F2).
  Ghép tự nhiên với F6: cùng máy Windows, cùng buổi smoke.

### 3.2 Bộ test bổ sung, map 1-1 các khoản còn thiếu

1. **Viewport matrix** (khoản 3, 7): mỗi form × 3 viewport (1280×800,
   768×1024, 390×844) × variant selector; assert
   `scrollWidth <= clientWidth` (không overflow ngang), không overlap bằng
   `elementFromPoint` tại tâm control phải trùng control.
2. **Zoom 200%** (khoản 3): chạy lại matrix ở zoom 200% — headed dùng
   Ctrl+`=`; headless dùng CSS `zoom: 2` trên `documentElement` (ghi rõ
   trong evidence rằng headless là xấp xỉ, kết luận chốt bằng headed).
3. **Keyboard-only + focus ring** (khoản 3): Tab đi hết cây focusable —
   mọi control đạt được, không focus trap, không tabindex dương; checkbox/
   radio đổi bằng Space/mũi tên; assert `getComputedStyle(focus)` có outline
   khả kiến (focus ring).
4. **ARIA name/role/state** (khoản 3): axe-core quét từng form × variant
   (critical/serious = FAIL) + assert đích: mọi input có nhãn
   (`label[for]`/`aria-label`), radio group có tên, grid có header — tái sử
   dụng đúng danh sách key/section của `test_full_sweep_inventory.js`.
5. **Error focus đúng field** (khoản 3): submit hồ sơ thiếu dữ liệu →
   `document.activeElement` phải là control của field lỗi đầu tiên, message
   lỗi nối bằng `aria-describedby`.
6. **Draft + đổi form/variant** (khoản 4, 8): điền dữ liệu → autosave →
   save/open JSON → reload → so store key-đếm-key; đổi form rồi quay lại,
   đổi variant M72 → **`PLI_M32`**: nhập `dn.ten_tieng_viet` ở thân, header
   mirror hiện cùng giá trị NGAY, không giữ giá trị stale sau khi xóa/đổi
   draft (HEADER-NAME-SYNC). Key soi theo ngữ cảnh (`dn.*`, `dn_goc.*`,
   hộ, chi nhánh…), không ép về một key.
7. **activeWhen không lọt export** (khoản 5): điền store có section
   inactive → gọi export qua shim (chế độ A) hoặc đọc payload qua bridge
   (chế độ B) → assert key của section inactive KHÔNG có trong payload.
8. **Fixtures + payload thật** (khoản 6): chạy lại bộ trên × fixture
   `empty/minimal/full/long/choice` (tái dùng `tools/phase5_fixtures.py`)
   + ≥2 payload người dùng thật từng phát hiện lỗi; cấm token giả làm
   evidence visual.
9. **Runtime console** (khoản 7): gom console/pageerror của trình duyệt
   thật — zero error nghiêm trọng toàn sweep (bổ sung cho S3 vốn chỉ thấy
   render.js trong Node).

### 3.3 Evidence + gate

- Mỗi assertion FAIL lưu evidence dạng manifest: screenshot + viewport +
  form/use-case/variant + hash ảnh — không chỉ log tổng (PLAN F2).
- Gate F2 khép khi: Lane B inventory 100% xanh (đã có) + bộ Playwright
  trên xanh ở cả hai chế độ A/B + census header-name 100% verdict.
- Thứ tự lắp khi được duyệt: (1) emitter danh sách form/variant từ
  `test_full_sweep_inventory.js` thành JSON dùng chung (một nguồn sự thật),
  (2) shim bridge + viewport/overflow/ARIA, (3) draft/export/M32 E2E,
  (4) chế độ B trên máy Windows của F6. KHÔNG cài Playwright/axe-core trong
  wave hiện tại.
