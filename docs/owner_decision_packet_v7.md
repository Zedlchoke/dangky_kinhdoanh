# Owner decision packet — Wave v7 (2026-09-05)

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
