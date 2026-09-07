# AI review dryrun — corpus phase7v/final (F5) — 2026-09-06

> Dryrun quy trình review mắt cho corpus `generated_ho_so/_visual_layout/
> phase7v/final` (455 record / 1653 PNG, baseline KỸ THUẬT trước migrate
> TT121). Mục đích: LUYỆN QUY TRÌNH cho corpus cuối phase8f, KHÔNG phải
> verdict final. AI PASS không đóng gate F5 — gate vẫn cần sign-off
> chấp nhận bằng người (PLAN F5).

## 1. Thiết lập mẫu có kiểm soát

- Mẫu: **20 record / 123 PNG** (~7.4% record, ~7.4% trang), chọn trải đều
  nhóm signature-heavy: PLII_M02 ×3, PLI_M15 ×3, PLI_M70 ×2, PLI_M09 ×2,
  PLI_M32 ×3, PLI_M10 ×2, PLI_M12 ×1, PLI_M72 ×4 (4 tag entidad: dntn,
  ctcp, dhdn, tnhh_2tv). Fixture phủ đủ 5 loại: valid-full ×9,
  valid-minimal ×2, choice-variants ×5, long-boundary ×2, empty-paper ×2.
- Mỗi record: đọc **toàn bộ** trang PNG bằng mắt, chấm đủ 7 hạng mục
  checklist protocol, ghi verdict qua CLI `--set` từng record.
- Verdict: **3 AI_REVIEWED_PASS / 17 AI_REVIEWED_FAIL**, 0 ghi ngoài
  whitelist, 0 cố tình chạm chuỗi `human-*` (tool hard-guard không kích
  hoạt vì không thử — đúng thiết kế).
- `--verify` sau khi ghi xong: `verdicted: 20, stale: [], pending: 435,
  corpus_records: 455` — **0 stale**.

## 2. Verdict từng record

| # | Key (form|fixture|tag) | Trang | Verdict | Finding chính |
|---|---|---|---|---|---|
| 1 | PLI_M70\|valid-full | 2 | **PASS** | 7/7; p2 2 khối ký đủ vùng |
| 2 | PLI_M70\|valid-minimal | 2 | **PASS** | p2 sparse hợp lệ (trang ký) |
| 3 | PLI_M15\|empty-paper | 5 | **PASS** | field trống đúng fixture; minor: template "Số Hộ chiếu(dới..." thiếu khoảng cách trước ngoặc (mọi fixture) |
| 4 | PLI_M32\|valid-full | 2 | FAIL | `name_date_glue` p1: "09/09/1978/10/1980" 2 mốc ngày dính nhau |
| 5 | PLI_M32\|choice-variants | 2 | FAIL | như trên (lặp theo fixture) |
| 6 | PLI_M32\|long-boundary | 2 | FAIL | như trên; wrap tên DN 7 dòng trong slot header KHÔNG tràn cột phải — OK |
| 7 | PLI_M10\|valid-full | 2 | FAIL | `blank_trailing` p2: block ghi chú rơi riêng p2 dù p1 trống >50%; bảng trống giống hệt empty-paper (fixture M10 không có dữ liệu) |
| 8 | PLI_M10\|empty-paper | 2 | FAIL | như trên |
| 9 | PLI_M72\|valid-full\|m72_dntn | 2 | FAIL | `name_date_glue` p2: "18/06/1987/07/1989" + "Ngày cấp: … Nơi cấp: 24/12/2026" (ngày rơi vào field nơi cấp) |
| 10 | PLI_M72\|valid-full\|m72_ctcp | 6 | FAIL | 4 findings: blank_trailing p2 (1 dòng mồ côi, khớp adjudication (ii) chờ polish keepNext); wide_table p4-p5: 5 dòng trống template + 3 dòng dữ liệu nối SAU trong cùng bảng mục 8; glue p6: fragment header bảng dính vào đầu mục 9; name_date_glue p6 |
| 11 | PLI_M72\|valid-full\|m72_dhdn | 3 | FAIL | wide_table p2: cùng pattern 5 trống + 3 dữ liệu; số "103500000000" gãy giữa chữ số trong cell; p3 sparse adjudicated (i) — không tính fail |
| 12 | PLI_M72\|choice-variants\|m72_tnhh_2tv | 4 | FAIL | wide_table p2-p3 (pattern trống+dữ liệu); số gãy giữa chữ số; name_date_glue p4 |
| 13 | PLII_M02\|valid-full | 13 | FAIL | double-date p2-p3; wide_table p4/p10 (4-5 trống + dữ liệu nối sau); checkbox p10 nhóm chủ thể không tick; footnote p13 số mũ ⁹ trùng 2 chú thích (xác nhận trong DOCX) |
| 14 | PLII_M02\|choice-variants | 13 | FAIL | `checkbox` p2 + p10: HAI nhóm loại-trừ đều tick cả 2 ô (vi phạm chọn ≤1); còn double-date, bảng trống+dữ liệu, dup ⁹ |
| 15 | PLII_M02\|valid-minimal | 11 | FAIL | double-date biến thể nặng hơn: "08/08/1977/09/" (mốc 2 bị cắt cụt); bảng trống+dữ liệu; dup ⁹ |
| 16 | PLI_M15\|valid-full | 7 | FAIL | double-date p1; bảng 13 cột xẻ: p3 chỉ 5 dòng trống, p4-p5 mới có dữ liệu; cột "Ngày cấp" chỉ còn "17"/"02"/"15"; checkbox "Mô hình tổ chức" không tick |
| 17 | PLI_M15\|choice-variants | 7 | FAIL | như trên; checkbox tick ĐÚNG 1/nhóm (khác PLII_M02) |
| 18 | PLI_M09\|valid-full | 8 | FAIL | `signature_block` p7-p8: tiêu đề khối ký ở p7 nhưng 3 đường ký rơi p8 SAU footnote 8-9; double-date 8.1/8.2; mọi nhóm checkbox không tick; bảng 14 cột 4 trống + dữ liệu nối sau |
| 19 | PLI_M09\|empty-paper | 6 | FAIL | cùng defect signature tách khối → lỗi form, không phụ thuộc fixture |
| 20 | PLI_M12\|valid-full | 24 | FAIL | `wide_table` p7-p8 + p12-p13: bảng "Tài sản góp vốn" VỠ GRID hoàn toàn (số cột 1-6 thành dòng lẻ, không viền; row 6 + "Tổng số" mồ côi sang trang kế); bảng ủy quyền p15-p16 mất giá trị "Ngày cấp" (chỉ còn "26"/"12"); double-date p18; checkbox không tick; nhiều trang gần trắng (p2, p13, p21) |

## 3. Phân lớp findings (theo tần suất)

1. **Value-merge ngày sinh "2 mốc dính nhau"** — 12/20 record: field
   "Ngày, tháng, năm sinh" chứa 2 ngày ghép ("09/09/1978/10/1980",
   biến thể cắt cụt "08/08/1977/09/"). Có sẵn trong DOCX (không phải lỗi
   render). Detector D11_glue KHÔNG bắt (glue label-value sạch, lỗi nằm ở
   giá trị). Nghi root cause: fixture person-generator ghép 2 giá trị.
2. **Bảng danh sách "dòng trống template rồi dữ liệu nối sau"** — 9/20:
   generator APPEND dòng dữ liệu SAU các dòng trống của template thay vì
   điền vào/sắp lên đầu. Kèm hậu quả: bảng xẻ trang với header lặp
   (nhìn như 2 bảng — m72_ctcp p4-p5), con số gãy giữa chữ số trong cell
   hẹp ("10350000000/0", "23/11/1/986").
3. **Mất giá trị do cột hẹp** — PLI_M15 p4-p5, PLI_M12 p15-p16: cột
   "Ngày cấp" chỉ hiển thị "17"/"02"/"15"/"26" — phần còn lại của ngày
   KHÔNG hiển thị (mất nội dung, không phải wrap).
4. **Checkbox nhóm loại-trừ sai** — PLII_M02 choice-variants tick CẢ HAI ô
   ở 2 nhóm khác nhau (p2, p10); ngược lại valid-full của PLII_M02/M15/M09/
   M12 lại KHÔNG tick ô nào dù scenario có dữ liệu tương ứng. Fixture
   choice-variants đang tick-all thay vì tick đúng 1 tổ chức hợp lệ.
5. **Signature block tách khối qua trang (M09)** — tiêu đề khối ký và các
   đường ký cách nhau bởi block footnote; lặp ở cả valid-full lẫn
   empty-paper → lỗi pagination của form.
6. **Bảng vỡ grid hoàn toàn (M12)** — p7-p8, p12-p13: bảng tài sản góp vốn
   mất viền ô, số cột thành dòng lẻ giữa trang, row mồ côi sang trang kế.
   Nặng nhất đợt review.
7. **Footnote/blank:** số mũ ⁹ trùng 2 chú thích (PLII_M02, template-level);
   trang gần trắng/nội dung mồ côi (M10 p2, M12 p2/p13/p21, m72_ctcp p2 —
   cái cuối đã adjudicated (ii) chờ polish keepNext).
8. **Header name sync** — 20/20 record ĐỨNG (slot header khớp key thân mẫu,
   không stale, long-boundary wrap 7 dòng không tràn). Không phát hiện
   defect class này trong mẫu.

## 4. Bài học quy trình cho corpus phase8f cuối

- **Mật độ/lực review thực tế:** 123 PNG ≈ một phiên review tập trung;
  mức ~5.5 PNG/record. Corpus đầy đủ 455 record / 1653 PNG ≈ 13× khối lượng
  này — cần chia lô theo form (không theo fixture) và review toàn bộ 5
  fixture của 1 form trong một lượt để tận dụng nhận biết mẫu hình (các
  defect lặp đúng theo fixture, chỉ lần đầu cần đối chiếu DOCX).
- **Thứ tự hiệu quả:** đọc fixture nhỏ trước (2 trang) để calibration,
  multi-page sau; với form >20 trang (M12=24, long-boundary 28-46 trang),
  soi trang bảng/ký trước theo detector hints rồi vẫn phải lật hết trang
  (defect mồ côi nằm ở trang "trống nhìn qua").
- **Checklist nào bắt được gì:** 6/7 mục bắt được defect thực:
  name_date_glue (double-date — bắt nhiều nhất), wide_table (vỡ grid,
  mất giá trị, dòng trống+dữ liệu), checkbox (tick-all/nhưng không tick),
  signature_block (tách khối M09), blank_trailing (mồ côi), footnote
  (dup ⁹). Riêng `header_name` không bắt được gì trong mẫu (điểm sáng —
  D17/HEADER-NAME-SYNC đang tốt). Hai class mà DETECTOR không bắt được
  (double-date value-merge, mất giá trị ngày cấp) chỉ thấy khi ĐỌC ẢNH —
  khẳng định vai trò review mắt là lớp lọc không thay thế được.
- **Đối chiếu DOCX khi nghi value-level:** 2 lần dùng unzip document.xml
  để phân biệt lỗi render vs lỗi nội dung gốc — nên đưa vào protocol làm
  bước chuẩn của FAIL (crop + trích DOCX làm evidence cho defect registry).
- **Chi phí --set:** 1 lệnh/record, cần --tag cho M72 (tag = entity type,
  variant cố định "m72") — dễ nhầm lúc đầu; ghi vào runbook.

## 5. CLI — gap ghi nhận (không sửa tool trong đợt này)

1. Không có lệnh liệt kê record đã verdict + reason (phải đọc thẳng
   review_manifest.json để tổng hợp findings) — một `--list` hoặc
   `--summary --verbose` sẽ giúp đợt corpus 455 record.
2. `--verify` quét lại toàn bộ record PENDING mỗi lần (chỉ cần đối chiếu
   entry có verdict) — với 1653 PNG vẫn nhanh, không blocker.
3. Key M72: `--tag` mang ý nghĩa entity type, `--variant` luôn "m72" —
   về mặt schema hơi lệch tên, nhưng tool nhất quán theo manifest nên
   không cần đổi.
4. Hard-guard `human-*` hoạt động đúng thiết kế (không thử phá — guard
   nằm ở cả lúc nhập lẫn lần ghi cuối).

## 6. Phạm vi & ranh giới

- KHÔNG sửa app/**, tools/**, allowlist (0 entry thêm); corpus PNG là
  evidence READ-ONLY — chỉ ghi review_manifest.json qua CLI.
- 0 verdict giả danh người; mọi verdict qua `--set` đúng 1 record/lệnh.
- Worktree: `../dangky_kinhdoanh-worktrees/final-f5-dryrun`, branch
  `agent/final-f5-dryrun`, không push/merge.
- review_manifest.json nằm trong corpus (gitignored) ở checkout chính —
  verdict sống cùng corpus, không commit vào git (đúng thiết kế evidence
  theo corpus).

## 7. Rủi ro cho đợt corpus cuối

1. Double-date person-generator là defect NGANG FORM (12/20 record, mọi
   fixture) — nếu không sửa ở generator, phase8f sẽ fail hàng loạt theo
   đúng class này; nên fix generator trước khi render corpus cuối.
2. Checkbox tick-all ở choice-variants làm fixture MẤT GIÁ TRỊ kiểm thử
   nhóm loại-trừ (phải là tick đúng 1) — cần sửa fixture spec trước phase8f.
3. Pattern bảng "trống + dữ liệu nối sau" xuất hiện ở mọi form danh sách —
   một fix ở generator sẽ giải tỏa 1/3 số FAIL ghi nhận được.
4. review_manifest đang 20/455 — phần còn lại 435 record vẫn PENDING;
   chỉ review đúng mẫu 20 này, phần kia là việc của đợt review toàn corpus
   (không review đại trà không kiểm soát theo ràng buộc nhiệm vụ).
