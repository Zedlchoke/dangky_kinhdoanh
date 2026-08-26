# Contract L1 — extractor/schema blocks-v3 (Wave P1-LAYOUT)

Owner: lane L1 (`agent/layout-l1`, base `a0453d0`). File sở hữu:
`tools/docx_to_blocks.py`, `tools/layout_roles.py`,
`tools/layout_role_overrides.json`, `tools/test_layout_l1_extractor.py`,
`tools/census/check_layout_l1.py`, tài liệu này.

## 1. Schema version

- Blocks hiện hành (pre-L1) KHÔNG có trường version → quy ước chốt: thêm
  **top-level `"v": 3`** vào output mới của converter. Output cũ thiếu `v`
  được mọi reader coi là v2 (hợp lệ).
- **Việc Lead cần làm sau regen:** mở allowlist trong
  `tools/audit_blocks_check.py` MỤC 5 — hiện tại `ALLOWED_TOP_KEYS`,
  `ALLOWED_BLOCK_KEYS["p"]`, `ALLOWED_RUN_KEYS_TEXT` chưa chứa các trường mới
  (`v`, `role`, `format`, `footnotes`, run `vertAlign`, run
  `role:"footnote-ref"`). Trước regen, audit đọc blocks cũ nên vẫn xanh; ngay
  sau regen sẽ FAIL schema cho đến khi cập nhật allowlist (đúng ý đồ: audit
  phải biết contract mới).

## 2. Trường mới — tên / kiểu / khi emit

### Block "p"

| Trường | Kiểu | Khi emit |
|---|---|---|
| `role` | string ∈ ROLES | **Luôn emit** trên mọi block `p` mới (kể cả `"body"`). Block cũ thiếu = body mặc định. |
| `format` | object | Chỉ khi có thuộc tính khác default (xem bảng dưới). Rỗng ⇒ không có key. |
| `footnotes` | object `{id_string: text}` | Chỉ khi block chứa `footnote-ref` VÀ tìm thấy text trong `word/footnotes.xml`. Id không có text vẫn giữ ở run (fail-soft), không vào map. |

### `format` (đơn vị pt, EMU ÷ 12700, làm tròn 1 số thập phân)

| Key | Nguồn OOXML | Emit khi |
|---|---|---|
| `leftIndentPt`, `rightIndentPt`, `firstLineIndentPt` (có thể âm — hanging) | `w:ind` | giá trị ≠ 0/None |
| `spaceBeforePt`, `spaceAfterPt` | `w:spacing @before/@after` | ≠ 0/None |
| `lineSpacing` (float, vd 1.15) | `w:spacing @lineRule="auto"` | multiple ≠ 1.0, round 2 số lẻ |
| `lineSpacingPt` | `@lineRule="exact"/"atLeast"` (Length) | giá trị ≠ 0 |
| `keepWithNext` | `w:keepNext` | chỉ khi true |

### Run (trong `runs[]` của p/table/loop cell)

| Run dict | Khi emit |
|---|---|
| `{"text": "...", "vertAlign": "superscript"|"subscript"}` | run có `w:rPr/w:vertAlign`; chỉ emit key khi có |
| `{"role": "footnote-ref", "footnoteId": N}` | run chứa `<w:footnoteReference w:id="N"/>` (zero-width, giữ đúng vị trí giữa các text run) |

### Hard break / tab — BẢO TOÀN, không collapse

python-docx 1.2.0 `CT_R.text` đã map: `w:t`→text, `w:br`+`w:cr`→`\n`,
`w:tab`+`w:ptab`→`\t`, `w:noBreakHyphen`→`-`. Converter dựng lại chuỗi ký tự
theo ĐÚNG mapping này (`_char_stream`) nên `\n`/`\t` đi nguyên vẹn vào
`run.text`. Renderer (L2) escape xong mới chuyển `\n` thành `<br>`.

## 3. Semantic role

Module thuần `tools/layout_roles.py`: `classify_role(text_folded, format,
runs) -> role`. Không IO, không import python-docx. 14 role theo PLAN:
source-indicator, form-number, national-header, national-motto,
national-separator, date-line, form-title, form-subtitle, salutation, body,
section-heading, note, footnote, signature.

Thứ tự rule (match đầu thắng) — xem source để biết regex chính xác:
source-indicator (marker `PL1 - Mau so N:`, tên file `.docx/.pdf/...`, nhãn
import/scrape) → national-header (dòng đầu "Cộng hòa…") → national-motto →
national-separator (chỉ dấu kẻ) → form-number (`^Mẫu số \d+`, ≤80 ký tự) →
salutation → date-line (`ngày…tháng…năm` hoặc ≥2 input key ngày/tháng/năm-ky)
→ signature (`(Ký và ghi họ tên)`/`(Đã ký)` hoặc nhãn người ký IN HOA) → note
→ form-title (IN + từ khóa tiêu đề) → footnote (`^\d{1,2} `không có `.`/`)`)
→ section-heading (`1.`/`a.`/`I.` …) → form-subtitle (IN còn lại) → body.

Fold dấu giống `p1_c_verify_plii_m02.py`: NFD bỏ Mn, đ→d, dồn whitespace.
LƯU Ý: rule caps/nhiều dòng cần raw text — classifier tự dựng từ `runs`;
khi gọi trực tiếp không có runs thì truyền text GỐC (giữ hoa/\n) qua runs
`[{"text": ...}]`.

### source-indicator vs form-number

- Marker kỹ thuật `PL1 - Mau so 1: …`, `PL2 - Mau so …`, tên file, nhãn
  import/scrape ⇒ `source-indicator` (UI sẽ uiHidden ở tầng render — L2).
- Dòng pháp lý `Mẫu số 1`… `Mẫu số 72` ⇒ `form-number`, hiển thị bình thường.
- Một mẫu CÓ THỂ chứa cả hai (vd PLI_M01 block#0 marker + block#1 legal):
  rule source-indicator chạy TRƯỚC và regex form-number chủ động loại chuỗi
  bắt đầu bằng marker. Evidence: 46/87 form có marker (khớp census L0),
  90 dòng `Mẫu số N` hợp lệ.

### Override tường minh

`tools/layout_role_overrides.json` — đang là `{}` (rỗng). KHÔNG tự điền;
owner quyết định rồi mới bổ sung. Shape:

```json
{
  "by_index": {"PLI_M01": {"7": "note"}},
  "by_folded_prefix": [{"prefix": "ghi chu dang ky", "role": "note",
                        "forms": ["PLI_M01"]}]}
```

`by_index` dùng index paragraph cấp thân (thứ tự `w:p` trong body, đếm cả
paragraph bị bỏ/block rỗng — ổn định theo template). `by_folded_prefix` khớp
prefix trên bản fold; bỏ `forms` = áp mọi form. Role lạ trong override bị bỏ
qua (fail-soft).

## 4. Footnote reference

- Run `<w:footnoteReference w:id="N"/>` ⇒ run dict footnote-ref (id giữ
  nguyên kể cả khi không tìm thấy text — fail-soft, không crash).
- Text chú thích đọc từ part `word/footnotes.xml` qua
  `doc.part.package.iter_parts()` (python-docx không có API); id ≤ 0
  (separator) bỏ; text = nối `w:t`, strip biên.
- Hiện trạng 87 template: KHÔNG có footnoteReference thật; các "Tôi là1" là
  run superscript thường (đã xử lý bằng vertAlign). Hạ tầng footnote phục vụ
  template tương lai và detector.

## 5. Idempotency & random

- `import random` (dòng ~37) CHỈ dùng trong `self_check()` với seed cố định
  `Random(20260824)` / `Random(42)` để chọn mẫu kiểm định — KHÔNG nằm trên
  đường sinh output; test bảo vệ điều này bằng assert nguồn.
- Chứng minh: convert 87/87 form hai lần liên tiếp → `json.dumps` byte-giống
  nhau 100% (không timestamp, không set-iteration, lxml deterministic).

## 6. Detector `tools/census/check_layout_l1.py`

```bash
python3 -X utf8 tools/census/check_layout_l1.py --pre-regen   # NGAY BÂY GIỜ (blocks cũ): report chi tiết, exit 1 = expected-fail-pre-regen
python3 -X utf8 tools/census/check_layout_l1.py               # SAU KHI Lead regen 87 blocks: PASS exit 0
python3 -X utf8 tools/census/check_layout_l1.py --blocks-dir <dir>   # quét thư mục khác (vd bản regen thử)
```

Kiểm tra: (a) mọi block `p` có `role` ∈ ROLES; (b) 0 dòng khớp pattern
source-indicator còn role body/không-role; (c) newline bảo tồn; (d) digit-glue
baseline-text về 0 (mỗi trường hợp là vertAlign sup/sub hoặc role
footnote/form-number/source-indicator; mã trích dẫn pháp lý kiểu
"76/2025/QH15" được loại — chữ IN sau `/` là mã văn bản).

Kết quả đã đo trên worktree này (mô phỏng regen in-memory ra temp dir):

| Check | Pre-regen (blocks cũ a0453d0) | Post-regen (mô phỏng) |
|---|---|---|
| (a) thiếu role | 3830 (legacy) | **0** |
| (b) SI leak | 0 (46 đúng role qua rules) | **0** (46 stored role) |
| (c) block chứa `\n` | 309 | **316** ≥ ngưỡng 293 |
| (d) glue baseline | 103 | **0** |

### Ngưỡng newline — evidence-based

- L0 rollup `total_newline_blocks=336` đếm theo fragment gồm cả block chỉ có
  TAB (`Chức danh: \t`) và paragraph nguồn bị converter bỏ (marker `{?cond}`
  của PLI_M72) — khác phương pháp với detector.
- Detector đo CHẶT `\n` trong block `p` của app/data/blocks: baseline pre-regen
  **309**/82 form. Sau regen đo được 316 (+7 — blocks trên disk stale hơn
  converter HEAD; extractor mới bảo toàn thêm 7 block có `\n`).
- Ngưỡng post-regen: `int(309 × 0.95) = 293` — dư địa cho Lead merge/tách
  block khi review rollout mà vẫn bắt được mất mát thật sự.

## 7. Backward compatibility

- Mọi trường mới OPTIONAL; block cũ (thiếu role/format/vertAlign/`v`) hợp lệ
  với mọi reader hiện hành — chứng minh bởi regression suite đọc blocks cũ:
  `tools.audit_blocks_check`, `app_web/test_dom.js`, `test_loop_prod.js`,
  `test_grid.js` đều PASS tại HEAD worktree này.
- Node tests đọc blocks qua concat text/loop-contract — không phụ thuộc cách
  tách run; việc tách run theo metadata (b/i/u/vertAlign) KHÔNG đổi chuỗi text
  (audit mục 1 đối chiếu text template ↔ blocks toàn 87 mẫu: khớp 100%).

## 8. Giới hạn còn lại (cho Lead)

1. `audit_blocks_check.py` MỤC 5 cần mở allowlist (mục 1) trước/trong lúc
   regen; tương tự nếu có validator riêng ở app_tk/app_web sau này.
2. Renderer L2 chưa đọc `role/format/vertAlign/footnotes` — UI vẫn collapse
   `\n` cho đến khi L2 merge.
3. Rule role là heuristic có test; sai sót chỗ đặc biệt xử lý bằng override
   JSON (không sửa rule hot). Số lượng role hiện tại trên 87 mẫu: xem phân bố
   do detector in ở mục (a).
4. `footnotes` map chỉ gắn khi template thật sự có footnotes.xml + ref — chưa
   có mẫu thật nào để e2e ngoài fixture test.
5. Detector chưa quét wrapper/title do app sinh (thuộc phạm vi render/app,
   gate LAYOUT_DONE yêu cầu audit cả tầng đó ở L2/L3).
