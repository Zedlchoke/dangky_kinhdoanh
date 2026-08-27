# P2 — QA wiring gate notes (Lane B3)

Ngày: 2026-08-27 · Base: `ab3c1f1` · Branch: `agent/b3-qa` · Owner file:
`app_web/test_wiring_gate.js` (test mới hoàn toàn, không đụng production).

## 1. Gate là gì

Gate ĐỘC LẬP bắt integration của runtime P2 với 3 component mới
(`fixed-matrix`, `nested-grid`, `output-table`). Self-contained, không đọc
artifact generated, không cần browser:

```bash
node app_web/test_wiring_gate.js     # từ root repo, clone bất kỳ
```

Fixture inline viết theo SHAPE CONTRACT đã khóa (`docs/p2_component_contracts.md`
mục 2.2 / 3.2 / 4.2 + `docs/p2_fixture_candidates.md` F2/N1/O1) — cố tình
KHÔNG dùng artifact generated để gate không "đúng chỉ vì generator hiện tại
đúng". Mọi mệnh đề bọc try/catch: harness hỏng cũng ra 1 mệnh đề đỏ có thông
báo chứ không chết suite. FAIL message luôn đủ `EXPECT / ACTUAL / HÌNH NHƯ CẦN`.

Nhóm mệnh đề (37 tổng):

| Nhóm | Kiểm gì | Trạng thái 2026-08-27 |
|---|---|---|
| [S] self-check | fixture hợp lệ qua chính module thuần (phải xanh; nếu đỏ → lỗi ở TEST) | 5 PASS / 0 FAIL |
| [A] plumbing tĩnh | index.html nạp script cả 3 module + script sống sót trong sandbox vm không CommonJS | 4 PASS / 5 FAIL |
| [B] dispatcher render | render runtime sinh marker DOM đặc trưng từng kind (transport probe: block.t mới / block.kind trên carrier / opts.sectionSpecs) | 0 PASS / 15 FAIL |
| [C] draft round-trip | `_row_id` ổn định qua migrateDraft×2 / GridCtl.ensureIds; dữ liệu phẳng kind mới sống qua upgrade v1→v2 | 3 PASS / 0 FAIL |
| [D] validation channel | lỗi kind mới mount đúng FormDomain (`validateDocument`), shape `{key,docId,code,message,severity}`, key navigable tới DOM | 1 PASS / 5 FAIL |

**Tổng: 12 PASS / 25 FAIL** (exit code 1). Đỏ CÓ KIỂM SOÁT: toàn bộ mệnh đề đỏ
thuộc A/B/D — đúng phần runtime chưa wire; nhóm S và C xanh chứng minh harness +
nền draft `_row_id` vốn đã idempotent.

## 2. Bản đồ điều kiện để gate XANH

1. **A1 ×3**: thêm `<script src="fixed-matrix.js">|nested-grid.js|output-table.js`
   vào `app_web/ui/index.html` trước `render.js`/`app.js`.
2. **A2 ×2**: `fixed-matrix.js` và `nested-grid.js` đang là CommonJS thuần
   (`module.exports = {...}`, **không UMD guard**) — nạp bằng `<script>` sẽ ném
   `ReferenceError: module is not defined`. Chọn một: UMD guard (mẫu
   `output-table.js`/`render.js`) HOẶC shim loader inline đứng TRƯỚC thẻ script
   HOẶC `<script type="module">`.
3. **B dispatcher ×3 + marker ×12**: `renderBlock` (`app_web/ui/render.js`)
   hôm nay chỉ biết `p/chk/table/loop`; kind lạ rơi vào `default: return ''` →
   markup bị nuốt ÂM THẦM. Cần dispatch theo `section.kind` sinh marker:
   - fixed-matrix: flat key `data-key="<semantic_key>.<row_id>.<tag>"`, giá trị
     phản chiếu, dòng pháp lý trống vẫn render, KHÔNG nút row-op, ô tổng là
     projection (không input).
   - nested-grid: `<thead>` ≥ 2 hàng, colspan/rowspan giữ nguyên, mỗi hàng dữ
     liệu mang `_row_id` ổn định, đủ số cột vật lý (không làm phẳng).
   - output-table: lưới chỉ đọc vẫn hiện trong DOM (`role="grid"` /
     `data-output-only="true"`) dù 0 input.
   - Chấp nhận BẤT KỲ transport nào trong ba cách đưa spec vào renderer
     (block.t riêng, `kind` trên carrier block, `opts.sectionSpecs`) — gate tự
     tìm transport đạt đủ marker của kind đó.
4. **D validation ×5**: wire validate() của module vào `FD.validateDocument` /
   `validateGridLoop` analog (channel FormDomain, không validator hard-code trong
   app.js); key lỗi phải trỏ được về ô DOM (`navigateToError`).
5. **C ×3 đã xanh**: giữ nguyên hành vi migrateDraft/ensureIds idempotent.

Chỉ cần lớp trên; gate đọc runtime trực tiếp nên sẽ chuyển xanh khách quan sau
merge Lane B1, không phải sửa file gate.

## 3. Bằng chứng gate khách quan (reference-wiring simulation)

Trong sandbox ngoài repo (`/tmp/b3sim`, bản copy, không commit): cài đúng
thay đổi mục 2 (script tag + UMD cho 2 module + dispatcher nhỏ theo kind trong
`renderBlock` + mount validate() vào `validateDocument`) → gate chạy lại:
**37 PASS / 0 FAIL, exit 0**. Nghĩa là mọi mệnh đề đỏ hôm nay đều khả đạt, giá
cả chặn nằm đúng ở chỗ chưa wire chứ không phải ở gate quá gắt.

## 4. Phát hiện cần lead/lane quyết (KHÔNG ai vá trong nhánh này)

1. `app_web/ui/fixed-matrix.js`, `nested-grid.js`: bare CommonJS → không nạp được
   như `<script>` thuần (evidence: mệnh đề A2 ném `ReferenceError` trong sandbox
   vm). Quyền sở hữu sửa thuộc lane/module owner; đây là prereq của mọi kế hoạch
   "chỉ thêm script tag".
2. `renderBlock` default nuốt markup âm thầm: cần marker/log tương ứng cơ chế
   `siSkipped` của L2 để kind chưa classify không mất data lặng lẽ.
3. Contract doc mục 2.2 khai totals chỉ có `"target": "outputOnly"` nhưng module
   yêu cầu thêm `target_tag` để projection đổ đúng ô (mã hiện hành
   `fixed-matrix.recompute` fallback `'value'`). Đề xuất bổ sung 1 dòng vào
   contract v1 (Lead quyết).
4. Hai chuỗi `_row_id` lệch format: `form-domain.makeRowId()` =
   `r<seq>_<rand>` vs `nested-grid.rowId()` fallback = `r<index+1>`. Không gây
   lỗi hôm nay (module ưu tiên `_row_id` sẵn có) nhưng đáng thống nhất.
5. output-table: runtime chưa có kênh audit presence nào (gate chưa thể kiểm
   "grid luôn tồn tại khi xuất DOCX") — thuộc Lane B2/export gate, ghi NOT RUN.

## 5. Không đụng gì tồn tại

`node app_web/test_dom.js` 58 PASS · `node app_web/test_grid.js` 111 PASS ·
`node app_web/test_m72_activation.js` 48 PASS · `git diff --check` sạch ·
`git status` chỉ có file test mới.

NOT RUN (ngoài phạm vi gate UI-runtime này): DOCX/render pipeline (Lane B2),
browser thật/Wave D visual, generator deep-idempotency.
