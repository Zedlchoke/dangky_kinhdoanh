# AI review protocol — corpus visual cuối (F5/O5)

> Quy trình agent review 100% PNG của corpus visual cuối, và cách ghi verdict
> bằng `tools/corpus_ai_review.py`. Tool này CHỈ là khung ghi nhận
> (bookkeeping) — nó KHÔNG tự chấm; agent ĐỌC ẢNH là người kết luận.
>
> Ranh giới verdict: agent chỉ được ghi **`AI_REVIEWED_PASS` /
> `AI_REVIEWED_FAIL`**. Mọi chuỗi giả danh người (`human-*`:
> HUMAN_PASS, HUMAN_REVIEWED, human-reviewed, …) bị tool **TỪ CHỐI tuyệt
> đối** ở mọi trường (verdict/reason/page) cả lúc nhập lẫn lần ghi đĩa cuối.
> Chữ ký người không được giả bằng agent (PLAN F5) — **AI PASS không đóng
> gate F5**; gate F5 vẫn cần human PASS hoặc accepted-with-owner-note.

## 1. Phạm vi

- Corpus: `generated_ho_so/_visual_layout/phase7v/final` (baseline phase7v;
  corpus "final" sau F0–F4 dùng cùng schema) — dạng phase7v:
  `manifest.json` với `records[]`, mỗi record có `pages[]` trỏ tới PNG.
  Baseline đã đo: **455 record / 1653 PNG**, `reviewer_verdict` khởi điểm
  `NOT_REVIEWED` trên toàn bộ.
- Đối tượng review là **ảnh render thật trên đĩa**: tool từ chối ghi verdict
  khi bất kỳ PNG của record thiếu (`PNG thiếu trên đĩa — chấm trên ảnh thật
  trước khi ghi verdict`).
- Có thể có corpus "current-law" mới sau F0L (TT 121/2026) — protocol này
  áp dụng nguyên xi cho corpus nào, không cần sửa.

## 2. CLI thật (`tools/corpus_ai_review.py`, chạy từ root repo)

| Lệnh | Tác dụng |
|---|---|
| `python3 -X utf8 -m tools.corpus_ai_review --corpus <corpus_dir> --init` | Tạo/làm mới khung `review_manifest.json` (`_format: ai_review_manifest_v1`): mọi record khởi điểm `AI_REVIEW_PENDING` kèm checklist 7 mục + page hints từ detector. **Re-run an toàn**: làm mới metadata (`page_count`, `png_missing`, detector hints) nhưng TUYỆT ĐỐI giữ nguyên verdict/reason/hash đã ghi. |
| `python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --set --form PLI_M09 --fixture valid-full --verdict AI_REVIEWED_FAIL --reason "Bang thanh vien le cot 13" --page 3` | Ghi verdict cho **ĐÚNG MỘT record** (`key = form\|fixture\|tag\|variant`, mặc định `tag=main`, `variant=""`). Lưu kèm: `verdict_reason`, `verdict_page`, `verdict_at`, `png_sha256` (mỗi PNG một hash), `template_hash_at_review`. |
| `python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --verify` | Đối chiếu hash đã ghi với PNG hiện tại trên đĩa → trả `{verdicted, stale[], pending, corpus_records}`. Stale = PNG đã đổi sau khi verdict. |
| `python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --summary` | Đếm `AI_REVIEWED_PASS` / `AI_REVIEWED_FAIL` / `pending`. |

Ràng buộc `--set` (tool tự kiểm, vi phạm là lỗi KHÔNG ghi):

1. `--verdict` chỉ nhận whitelist 2 giá trị `AI_*` — không có chế độ hàng
   loạt, không có verdict thứ ba.
2. `--reason` **bắt buộc** (chống PASS/FAIL mù); rỗng/whitespace bị từ chối.
3. Chuỗi `human-*` trong verdict/reason/page bị từ chối (`giá trị chứa token
   human-* bị TỪ CHỐI`).
4. Record phải tồn tại trong corpus manifest theo đúng key; thiếu PNG trên
   đĩa bị từ chối.

KHÔNG sửa `review_manifest.json` bằng tay: tool kiểm `_format` và quét
`human-*` mỗi lần load **và** lần cuối trước khi ghi đĩa — file sửa tay lệch
format làm toàn bộ review không đọc được nữa.

## 3. Checklist 7 hạng mục (đúng thứ tự tool xuất)

Agent chấm từng record trên TẤT CẢ các trang PNG của record. Mỗi mục trong
`review_manifest.json` có `criteria` + `detector_hints` (detector nào có hit
thì mục đó cần soi kỹ — nhưng **hints không phải kết luận**):

| # | Mục | Tiêu chí chấm |
|---|---|---|
| 1 | `signature_block` — Khối chữ ký (footer mỗi trang) | Đúng mẫu chữ ký của form, đủ **vùng viết ≥ 72pt** theo ngưỡng owner (O8/SIGNATURE-USABILITY-SPACE: registry 78 entry chuẩn hoá 40→72pt; evidence phase7v min gap 72.9pt), không thiếu đường ký/ngày tháng, không lệch trang khi pagination; "Đã ký" không cần vùng viết nhưng phải nhận diện đúng loại. |
| 2 | `header_name` — Header tên biểu mẫu | Header/trang đầu ghi đúng tên mẫu; slot tên DN/HKD không dính vào nhãn, không trống khi fixture có giá trị; **đúng một nguồn nhập** — slot header là mirror read-only của key thân mẫu (HEADER-NAME-SYNC, D17 HARD, fixture bắt buộc `PLI_M32`), không xuất hiện giá trị thứ hai/stale. |
| 3 | `wide_table` — Bảng rộng / grid | Bảng **≥ 10 cột** không vỡ cụm ký tự (D9), cột không tràn mép trang, header không chồng dòng. |
| 4 | `footnote` — Chân trang chú thích | Số mũ chú thích khớp dòng chú thích chân trang; chú thích không cắt giữa trang, không trôi sang mẫu khác. |
| 5 | `checkbox` — Checkbox | Ô □/☐ in đúng glyph dạng **ô vuông có viền** (F-V5-2: X tự do trong ô viền được nhận), tick X nằm đúng ô, nhóm loại-trừ chọn ≤ 1 (fixture choice-variants). |
| 6 | `name_date_glue` — Name/date glue | Nhãn và giá trị ngày/tháng/năm, họ tên không dính liền mất khoảng cách (D11/D13/D17), thứ tự field không đổi chỗ. |
| 7 | `blank_trailing` — Trang trắng / trailing | Không trang trắng thừa, không nội dung mồ côi sau trang cuối, tổng số trang hợp lý theo fixture (`page_count` là hint, không phải chuẩn — pagination có thể đổi hợp lệ). |

## 4. Quy trình chuẩn cho một đợt review

```
# 0) Tạo/làm mới khung (idempotent, giữ verdict cũ)
python3 -X utf8 -m tools.corpus_ai_review --corpus generated_ho_so/_visual_layout/<corpus> --init

# 1) Với MỖI record: mở toàn bộ PNG trong pages[] của record (theo thứ tự),
#    chấm đủ 7 mục ở trên (ưu tiên soi mục có detector_hints).

# 2) Ghi verdict record-level — đúng một record mỗi lệnh:
#    - đủ 7/7 đạt  -> AI_REVIEWED_PASS, reason ghi tóm tắt trang đã soi
#    - bất kỳ mục hỏng -> AI_REVIEWED_FAIL, reason BẮT BUỘC ghi mã mục + trang
#      + mô tả cụ thể (ví dụ: "signature_block p3: vùng ký 41pt < 72pt")
python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --set \
    --form PLI_M09 --fixture valid-full \
    --verdict AI_REVIEWED_FAIL \
    --reason "signature_block p3: vuong ky 41pt < 72pt; wide_table p2 OK" \
    --page 3

# 3) Cuối đợt: chống stale + chốt độ phủ
python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --verify
python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --summary
```

Trạng thái đợt HOÀN TẤT (mức agent): `--summary` cho `pending: 0` và
`--verify` cho `stale: []`.

## 5. Quy tắc stale (PNG đổi → verdict hết hiệu lực)

- Lúc ghi verdict, tool lưu `sha256` của từng PNG + `template_hash_at_review`.
- Bất kỳ thay đổi generator/template/fixture nào sinh lại PNG →
  `--verify` liệt kê record vào `stale` (kèm tên file đã đổi).
- Record stale **phải được review lại từ đầu** (đọc lại ảnh) rồi `--set`
  lại — không được kéo verdict cũ; tool không tự xoá verdict stale.
- Theo PLAN F5.4: sau một lần fix, CHỈ record bị ảnh hưởng và dependency
  pages phải review lại (không chấm lại toàn corpus), và auditor độc lập
  xác nhận freshness qua chính `--verify` + hash manifest.

## 6. FAIL → defect

Mỗi `AI_REVIEWED_FAIL` tạo **một defect** trong `docs/defect_registry.md`
(PLAN F5.3) với: form/fixture/tag/variant (= key), trang (`verdict_page`),
class (tên mục checklist hỏng), crop/screenshot minh hoạ, và reason y nguyên
như đã ghi. Verdict giữ `AI_REVIEWED_FAIL` cho tới khi fix → Lead regen →
`--verify` sạch ở record đó → agent review lại ảnh mới → PASS. Không "đặt
lại" FAIL thành PASS vì đã tạo defect.

## 7. Điều cấm (tóm tắt)

1. Cấm ghi verdict ngoài 2 giá trị `AI_*`; cấm mọi biến thể `human-*`
   (kể cả trong reason — ví dụ "human sẽ check sau" là chuỗi hợp lệ về mặt
   ngôn ngữ nhưng bị regex `human[-_ ]` chặn: **hãy tránh viết chữ human**
   trong reason).
2. Cấm set hàng loạt PASS (không có API như vậy — đừng viết script vòng lặp
   PASS-all; mỗi record phải được đọc ảnh).
3. Cấm verdict khi PNG thiếu (`png_missing`) hoặc khi chưa mở ảnh.
4. Cấm sửa tay `review_manifest.json` / `manifest.json`.
5. Cấm dùng AI PASS để tuyên bố gate F5 đạt — gate F5 là human sign-off
   (100% trang human PASS hoặc accepted-with-owner-note); agent review là
   lớp lọc trước, evidence của nó phục vụ việc human review nhanh hơn.
