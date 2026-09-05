# Owner decision packet — Wave v7 (2026-09-05)

> **OWNER-DELEGATED DECISION RECORDED 2026-09-06:** owner yêu cầu Lead tự
> duyệt. Các lựa chọn sản phẩm/kỹ thuật đã được chốt tại mục “Quyết định cuối”
> bên dưới. O5 human sign-off và O6 Windows smoke là bằng chứng thực thi, không
> thể biến thành PASS bằng quyết định trên giấy.

> Packet các quyết định owner CÒN THIẾU phát sinh từ wave v7
> (HEADER-NAME-SYNC + SIGNATURE-USABILITY-SPACE). Các quyết định đã chốt của
> wave (sàn 72pt, "Đã ký" miễn, một lần nhập, header mirror read-only) ĐÃ
> được áp dụng và không hỏi lại. Fail-closed: mọi mục dưới đây giữ nguyên
> trạng thái an toàn cho tới khi owner trả lời.

## N-v1 — PLI_M33: band "TÊN DOANH NGHIỆP" không có trường để mirror

- Hiện trạng: band đầu trang có slot fillable (`TÊN DOANH NGHIỆP` + dòng
  kẻ) nhưng thân mẫu CHỈ có `chu_hkd.ho_ten` (tên người nộp). Không có
  trường tên DN nào trong toàn mẫu (verify token + form_maps + blocks).
- Phương án:
  - (A) Thêm field `dn.ten_tieng_viet` vào thân M33 (spec + template regen)
    và bind band — tăng dữ liệu người dùng phải nhập;
  - (B) Coi band là **điền tay theo bản giấy** (handwriting-only, miễn
    detector như registry `phase6v_handwriting_slots.json`);
  - (C) Xóa slot band (đổi về nhãn thuần).
- Fail-closed hiện tại: giữ nguyên band literal + dòng kẻ; detector D17 bỏ
  qua (form không nằm registry bind).

## N-v2 — PLII_M06: band "TÊN HỘ KINH DOANH" không có input tên hộ

- Tương tự N-v1 nhưng mẫu hộ kinh doanh: thân không có key tên hộ nào.
- Phương án (A) thêm field / (B) handwriting-only / (C) bỏ slot.
- Fail-closed: giữ nguyên band literal.

## N-v3 — 3 ô output inline chưa bind (render-time)

- PLI_M70 p14, PLI_M48 p17, PLI_M49 p9: ô "TÊN …" trong khối output của cơ
  quan chưa có token. Đây là các form hướng output/admin — cần owner xác
  nhận render-time điền tên từ đâu (không bind mù).
- Fail-closed: giữ nguyên như bản giấy.

## N-v4 — PLI_M07: nguồn gốc là stub 2 dòng

- Nguồn gốc chỉ có caption + "Mẫu số 7"; template hiện tại TỰ DỰNG bảng +
  cột `Chữ ký {chu_ky}` (chiều ngược so với các trường hợp mất ký). Nguồn
  không đủ để tái sinh template. Owner xác nhận template hiện hành được
  chấp nhận là nguồn chân lý cho M07 (không tìm bản gốc khác).

## Các quyết định kế thừa còn mở (không đổi so với PLAN v7 mục 2)

O1 adjudicate 22 section BLOCKED_OWNER · O2 WLAY-005 M12 · O3 Q-P4-1
min_rows · O4 mã định danh dài M09/M72 · O5 người ký G-E (human sign-off
toàn corpus) · O6 máy Windows sạch · O7 Excel questionnaire 3 cụm còn lại.

## Trạng thái wave v7 (tham chiếu nhanh)

- HEADER-NAME-SYNC: 20/22 slot đã bind + gate hard D17; 2 slot chờ N-v1/N-v2.
- SIGNATURE-USABILITY-SPACE: sàn 72pt áp toàn corpus (owner đã chốt trong
  lệnh wave); corpus mới phase7v + Word-open + signgap evidence 72pt.
- Human review: toàn bộ corpus phase7v vẫn `NOT_REVIEWED` cho tới khi owner
  duyệt từng trang (O5).

---

## Quyết định cuối — owner ủy quyền Lead duyệt ngày 2026-09-06

### L-2026 — Baseline pháp lý hiện hành (ưu tiên cao nhất)

**DECIDED:** mọi workstream tiếp theo phải dùng Nghị định 168/2025/NĐ-CP đã
được sửa bởi Nghị định 296/2026/NĐ-CP và Thông tư 68/2025/TT-BTC đã được sửa
bởi Thông tư 121/2026/TT-BTC. Thông tư 121 có hiệu lực từ 21/08/2026 và:

- thay Mẫu Phụ lục I số 1, 2, 3, 4, 5, 10, 12, 27, 30;
- bãi bỏ Mẫu Phụ lục I số 11.

Do đó corpus `phase7v` và runner xanh chỉ là baseline kỹ thuật, chưa phải bằng
chứng current-law cho 9 mẫu bị thay. Lead phải import/đối chiếu đúng bản ký số
chính thức, migrate spec/template/UI/questionnaire tương ứng và đưa PLI_M11 ra
khỏi active procedure catalog (`REMOVED_BY_CURRENT_LAW`, giữ migration/alias
đọc draft cũ nếu cần). Cấm copy cấu trúc mẫu 2025 sang mẫu 2026 bằng suy đoán.

Nguồn chính thức:

- https://vanban.chinhphu.vn/?classid=1&docid=219269&pageid=27160
- https://vanban.chinhphu.vn/?classid=0&docid=218986&pageid=27160
- https://vanban.chinhphu.vn/?classid=1&docid=214411&pageid=27160
- https://vanban.chinhphu.vn/?classid=1&docid=214334&pageid=27160

### N-v1 — PLI_M33

**DECIDED A:** thêm canonical field `dn.ten_tieng_viet` vào surface nhập của
M33 và bind band thành mirror read-only. Đây là tên doanh nghiệp của thủ tục,
không được dùng `chu_hkd.ho_ten` (tên người đề nghị) thay thế. Một lần nhập,
draft/UI/DOCX/PDF cùng key.

### N-v2 — PLII_M06

**DECIDED A:** thêm field tên hộ theo canonical key đã dùng cho family PLII
(`hkd_ten_tieng_viet_2`, trừ khi migration inventory chứng minh key canonical
mới thay thế) và bind band mirror read-only. Không đồng nhất tên hộ với tên
người `chu_hkd.ho_ten`.

### N-v3 — PLI_M48/M49/M70

**DECIDED:** đây là output/admin forms. Bind các occurrence “Tên doanh nghiệp”
ở render-time từ `dn.ten_tieng_viet`; read-only, không thêm control hoặc draft
key. Với nhánh thành lập mới của M49, phần người nhận vẫn dùng dữ liệu cá nhân;
chỉ nhánh doanh nghiệp hiện hữu mới render tên DN. Missing canonical value phải
fail-loud hoặc để đúng blank pháp định theo contract, không in token kỹ thuật.

### N-v4 — PLI_M07

**DECIDED: không chấp nhận template tự dựng làm nguồn chân lý.** Mẫu 7 không
nằm trong danh sách bị thay/bãi bỏ bởi Thông tư 121/2026, nên phải rebuild và
đối chiếu với Mẫu số 7 Phụ lục I của Thông tư 68/2025 bản ký chính thức. Stub
hai dòng trong repo chỉ là artifact nguồn lỗi.

### O1 — Adjudicate 22 section

**DECIDED theo vai trò tài liệu:**

- **IMPLEMENTED AS USER INPUT (10):** `PLII_M02/c5_thue_chi_tieu_cap_doi`,
  `PLI_M02/mo_hinh_to_chuc_cong_ty`, ba matrix M12, hai grid M27,
  `PLI_M78/san_pham_cung_cap_thong_tin`, `PLI_M79/tai_lieu_kem_theo_de_nghi`,
  `PLI_M80/tai_lieu_kem_theo_thu_hoi`.
- **OUTPUT_ONLY (11):** M52 `khung_ra_soat_4_nhom`; M56 grid tiếp tục trước
  hạn; M63 grid địa điểm bị thu hồi; hai grid M66; grid M67; grid M68; M70/M71
  “hồ sơ bao gồm”; hai grid M75. Các form này do cơ quan đăng ký kinh doanh
  phát hành; dữ liệu được render từ hồ sơ/canonical store khi có, không tạo
  màn nhập trùng chỉ để điền output.
- **REMOVED_BY_SOURCE_CLEANUP (1):**
  `PLI_M09/vung_nhiem_mau_6789_10`; xóa vùng nhiễm khỏi M09 theo source chính
  thức, không hiển thị và không render. Coverage tool phải hỗ trợ verdict này
  hoặc loại row bằng migration có evidence; không ngụy trang thành output.

M12 và M27 thuộc nhóm biểu mẫu đã bị Thông tư 121/2026 thay thế: implement từ
mẫu 2026, không từ template 2025 hiện tại.

### O2 — WLAY-005/M12

**DECIDED IMPLEMENT:** materialize hai matrix tài sản góp vốn và matrix cơ cấu
loại cổ phần từ Mẫu 12 mới của Thông tư 121/2026. Tổng/tỷ lệ/giá trị suy ra là
computed output-only và mismatch là validation error; dữ liệu gốc vẫn editable.
Giữ nguyên chính tả của văn bản hiện hành, không kế thừa lỗi OCR hoặc typo từ
template cũ.

### O3 — `min_rows`

**DECIDED CONDITIONAL:** `min_rows=1` chỉ enforce khi section được kích hoạt bởi
selector/`activeWhen` xác định có người đại diện/ủy quyền. Inactive section có
0 dòng là hợp lệ và không block export. Active section phải có ít nhất một dòng
business-data hợp lệ; blank UI rows không được tính. `max_rows=null` nếu văn
bản không quy định giới hạn.

### O4 — mã định danh dài M09/M72

**DECIDED PRESERVE:** coi mã định danh là chuỗi, giữ đủ ký tự và số 0 đầu;
không truncate, không scientific notation, không chèn hyphen vào dữ liệu.
Layout dùng wrap-anywhere/fit column, landscape section khi cần và font floor
đọc được; overflow là hard fail.

### O5 — visual review

**DECIDED PROCESS, EVIDENCE STILL OUTSTANDING:** cho phép agent/auditor kiểm
100% PNG và ghi verdict riêng `AI_REVIEWED`, nhưng không được ghi
`HUMAN_REVIEWED` hay giả chữ ký người. `CORE_APP_TECHNICALLY_READY` có thể đạt
sau AI review; `CORE_APP_DONE/RELEASE_DONE` vẫn chờ người thật ký trên đúng
corpus hash.

### O6 — Windows

**DECIDED AUTHORIZED, NOT RUN:** được phép build/smoke ngay khi có Windows
10/11 sạch. Không có máy thì giữ S1–S8 `NOT RUN`; macOS/Wine không thay thế
WebView2 và clean-machine `.exe` evidence.

### O7 — Excel rollout

**DECIDED PROCEED:** triển khai đủ ba cụm còn lại theo P6=C: hộ kinh doanh →
thay đổi ngành → thuế. Questionnaire được pre-approved nếu mỗi câu hỏi là cách
diễn đạt đời thường trung thành với canonical field của đúng biểu mẫu hiện
hành, có mapping/source evidence, không thêm tư vấn pháp lý. Bắt buộc export,
import, round-trip, negative validation, UI và visual workbook; auditor độc lập
duyệt artifact cuối. Mẫu thuộc Thông tư 121/2026 phải migrate trước khi sinh
questionnaire.

### O8 — vùng ký

**DECIDED/ALREADY IMPLEMENTED:** giữ floor 72pt cho ký tay; “Đã ký” được miễn
write-space; các cụm đóng dấu không được thấp hơn 72pt và phải giữ khoảng lớn
hơn nếu mẫu hiện hành quy định. Tiếp tục pin detector coverage 100%.
