# Signature space census — 2026-09-05

## Phạm vi và kết luận

- Baseline: `main@000e8e2`.
- Corpus: `generated_ho_so/_visual_layout/phase6v/final/`, 455 PDF
  (91 render unit x 5 fixture), 1631 PNG theo manifest.
- Structural census: 87/87 template; 78 form có chữ ký, tổng 84 cụm; 9 form
  không có cụm ký trong template.
- Output census mở rộng: 455/455 PDF, 420 cụm; không record nào có chữ ký ở
  template nhưng mất toàn bộ chữ ký ở output.
- Legacy threshold 40pt: 420/420 đạt; minimum 43.4pt.
- UX reference 72pt: 195/420 không đạt, thuộc 185 record và 40 form. Trong đó
  185 cụm còn phải ký tay; 10 cụm mang instruction “Đã ký”.
- Production D6 hiện chỉ nhận 215/420 cụm. Do đó `D6 hard 0` chưa chứng minh
  toàn bộ signature corpus đã được đo.
- Visual spot-check 5 family rủi ro xác nhận không split, nhưng các vùng
  43–57pt nhìn chật cho ký tên/ghi họ tên/đóng dấu.

Verdict: **PASS theo floor kỹ thuật cũ 40pt; FAIL/OPEN theo yêu cầu UX “đủ
lớn để ký” cho đến khi owner chốt ngưỡng và corpus mới đạt ngưỡng đó.** Human
review toàn bộ 1631 PNG vẫn `NOT_REVIEWED`.

## 40 form có ít nhất một cụm dưới 72pt

`PLII_M01`, `PLII_M02`, `PLII_M03`, `PLII_M04`, `PLII_M05`, `PLII_M06`,
`PLII_M09`, `PLI_M01`, `PLI_M02`, `PLI_M03`, `PLI_M04`, `PLI_M06`, `PLI_M08`,
`PLI_M09`, `PLI_M11`, `PLI_M13`, `PLI_M14`, `PLI_M15`, `PLI_M17`, `PLI_M18`,
`PLI_M19`, `PLI_M21`, `PLI_M23`, `PLI_M25`, `PLI_M26`, `PLI_M27`, `PLI_M28`,
`PLI_M29`, `PLI_M30`, `PLI_M31`, `PLI_M32`, `PLI_M33`, `PLI_M46`, `PLI_M66`,
`PLI_M67`, `PLI_M68`, `PLI_M69`, `PLI_M78`, `PLI_M79`, `PLI_M80`.

## 9 form không có cụm ký trong template

`PLII_M18`, `PLI_M05`, `PLI_M07`, `PLI_M10`, `PLI_M71`, `PLI_M72`, `PLI_M73`,
`PLI_M74`, `PLI_M76`.

Đây mới là mô tả cấu trúc, không phải kết luận pháp lý. Mỗi form cần source/
owner verdict rằng absence là đúng trước khi đóng gate.

## Evidence và hạn chế detector

Suite đã chạy:

```bash
python3 -X utf8 -m tools.test_phase5r_signatures
# 6 PASS / 0 FAIL
```

Quét output dùng grammar rộng trong `tools.test_phase5r_signatures.py` để nhận
cả instruction có/không ngoặc, `từng thành viên`, `đóng dấu`; khoảng trống là
từ đáy instruction đến dòng text gần nhất chồng cột, hoặc đến page edge nếu
không có dòng dưới. Production `det_signatures()` hiện có hai blind spot:

1. grammar `_SIG_INSTR_FOLD` hẹp nên chỉ nhận 215/420 cụm;
2. nếu không có dòng text phía dưới thì D8 không ghi phép đo nào.

Các spot-check dùng PNG corpus hiện hữu:

- `valid-full/main/PLII_M02/page-12.png`;
- `valid-full/main/PLI_M15/page-06.png`;
- `valid-full/main/PLI_M46/page-01.png`;
- `valid-full/main/PLI_M66/page-02.png`;
- `valid-full/main/PLII_M09/page-01.png`.

## Acceptance cần bổ sung

1. Owner chốt ngưỡng: đề nghị 72pt (2.54cm) cho ký/ghi họ tên và policy riêng
   cho trường hợp đóng dấu; không áp ngưỡng viết tay cho instruction “Đã ký”.
2. Detector coverage phải bằng output census; expected signature nhưng zero
   detected là hard fail.
3. Đo cả cluster cuối trang, keep-together, orientation và split.
4. Fix qua generator/spec; không hand-edit generated DOCX và không chèn dòng
   rỗng mù gây blank page.
5. Regenerate corpus sau fix, rerun Word-open/ZIP/determinism, rồi human review
   trên đúng hash corpus cuối.
