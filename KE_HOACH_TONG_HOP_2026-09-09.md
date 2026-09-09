# KE_HOACH_TONG_HOP — PLAN TRIỂN KHAI SAU PHASE9-BANDFIX (2026-09-09)

> Kế hoạch tổng hợp cuối của phiên Lead 2026-09-09 (base `3f4af84`, F7
> PASS-WITH-NOTES + bandfix). Ghi đè phần "việc tiếp theo" của các plan cũ;
> nguyên tắc tiên quyết vẫn theo `PLAN.md` v7 (gate G0–G10, không push khi
> chưa có lệnh owner, không tự ghi human sign-off / Windows PASS).

## 0. Trạng thái kết thúc phiên

- **Đã đóng** (P0): 12 lỗi corpus lớp A + 3 lỗi fixture/harness lớp B + 4 chủ
  đề test (chi tiết: `docs/audits/phase9_bandfix_audit_2026-09-09.md` §2).
- **Đang chạy/verify**: corpus v2 `phase9_bandfix_v2` render lại toàn bộ từ
  main sau wave2+wave3; gate detector; Word open; D5 allowlist prune;
  re-review trực quan các form đã sửa.
- **Không đụng**: corpus evidence gitignored trong worktree
  `../dangky_kinhdoanh-worktrees/f3-corpus-v2` (phase8g_v2) — KHÔ được xóa
  worktree này; docs audit phase8f/phase7v là lịch sử.

## 1. P0 — must (những gì còn lại của P0, thực hiện NGAY sau phiên)

| # | Việc | Điều kiện hoàn thành |
|---|---|---|
| P0-1 | Verify corpus v2: detector HARD 0, candidate adjudicate (D9 M10 min col đổi 614→~656 sau floors mới — kỳ vọng hết candidate hoặc adjudicate lại "(ii)"), export error 0 | summary.json + manifest == đĩa |
| P0-2 | Word open-direct toàn bộ render-unit (loop `phase5_word_open`) trên corpus v2 | 90/90 PASS_OPEN_DIRECT |
| P0-3 | Re-review trực quan các form vừa sửa: M12 (có "Mẫu số 12"), 23 band (nhãn phải+đậm), M42/43/63/68/69 + 5×M72 (Ngày cấp/Nơi cấp đúng 2 ô), M67 (tên DN), M70 (cặp ký về t1), PLII_M17 (cặp nguyên khối), m72_dntn/dhdn (1 trang), M01/02/03/10/PLII_M01/02/07 (bảng có dữ liệu), choice-variants (mỗi cụm đúng 1 tick) | mỗi form PASS có ảnh; FAIL → defect mới, fix theo wave nhỏ |
| P0-4 | Prune `docs/phase6v_d5_sparse_allowlist.json`: gỡ entry stale thực sự mất hit (dự kiến: m72_dhdn p2 ×2, PLI_M70 p2 ×2; PLII_M17 giữ vì trang 2 vẫn tồn tại — cặp đã nguyên khối). KHÔNG gỡ trước khi gate xác nhận | H7 allowlist xanh sau prune |
| P0-5 | Runner 65/65 + compileall + manifest deep + coverage 111/111 drift 0 trên main cuối | VERDICT PASS |

## 2. P1 — should (1–2 kỳ tới)

1. **A-8 M45/M53 — cụm ký mồ côi trang 2.** Ba phương án, khuyến nghị (a):
   (a) generator: regen template dời paragraph rỗng từ sau cụm ký lên trước
   (thu hồi ~18pt, M45 chắc ăn; M53 cận biên 3pt — verify ảnh); (b) chấp nhận
   làm "trang cuối tự nhiên" class (i) đã allowlist (cụm không bị TÁCH, đúng
   thông lệ in); (c) nếu làm cả (a) mà M53 vẫn tràn → gộp về P1.2.
2. **Pin khổ giấy A4 toàn corpus** (Lane D mục 5 — NGUY HIỂM, cần owner
   duyệt): đổi `w:pgSz` LETTER→A4 ở render; fix gốc cho mọi minor phân trang
   ("dòng lửng", list Nơi nhận tách) vì A4 cao hơn ~50pt; ĐÁNH ĐỔI: toàn bộ
   corpus re-paginate, D5 allowlist làm lại, pixel baseline render lại, W3
   pin đếm trang lại. Chỉ làm một lần, lane riêng, sau khi corpus v2 ký.
3. **Detector blind-spot** (defect mới từ Lane D): D7 thêm split cấp-CẶP ký
   (2 cụm ký dọc khác trang) và cụm-orphan (cụm cuối nhảy trang khi trang
   trước còn ≥ ngưỡng chỗ trống); D8 đo thêm spacer exact NỘI BỘ ô bảng ký
   (hiện 800tw cũ < sàn 72pt của chính registry mà không ai thấy).
4. **DECIDED-DIFF pháp lý — nhãn "TÊN DOANH NGHIỆP/HỘ KINH DOANH" đã xoá khỏi
   band (e148d83):** bản in app lệch bản giấy ở cả 23 form band; P0 đối chiếu
   ảnh nguồn đã ghi nhận. Owner xác nhận lại (chấp nhận để header gọn, hay
   trả nhãn về dạng "band_input" kiểu M33/PLII_M06). Trước khi owner trả:
   giữ nguyên hiện trạng, không tự đổi.
5. **Pin parity DOCX↔CSS band** (test agent G5): đọc `HEADER_BAND_LEFT_RATIO`
   từ build_form_maps + `.hdr-band` từ style.css, assert 36/36, 13pt/13pt,
   bold, top — chặn vĩnh viễn kiểu trôi đã xảy ra ở 2ed4629.
6. **M02/03/04/05 nhãn "Ngày cấp…Nơi cấp…" 0-input** (Lane C ghi nhận 8
   paragraph slot `…` đơn không tách được): mở rộng rule nếu muốn bind —
   hiện các ô này để trống in tay, không sai so bản giấy, chỉ thiếu auto-fill.
7. **Defect registry cập nhật:** đóng Class 4 (band dọc) sau khi v2 ký; ghi
   D7/D8 blind-spot; ghi A-8 trạng thái; đồng bộ `decision_registry` (D1–D7
   packets còn OPEN — phần lớn đã supersede bởi O1–O8, cần one-pass dọn như
   F0 đã làm cho các registry khác).

## 3. P2 — could (cosmetic/realism/khi owner mở)

1. M51: bind "Địa chỉ trụ sở chính" + "Mã số DN" vào b8 (owner chốt rồi sửa
   blocks qua generator rule).
2. Registry entry cho shell-form: M46 (chứng nhận in tay, 1 field), M73/M74
   (khung công bố — vùng in do cơ quan điền) → `table_coverage_current`.
3. Fixture realism (chỉ khi owner yêu cầu, đụng corpus toàn phần): tỷ lệ cuối
   = 100 − tổng các dòng trước; `ghi_chu` thay câu "Nội dung kê khai số N";
   cân nhắc nhóm nghìn cho tiền (đụng format policy locale-free — cần owner +
   đổi đồng bộ DOCX/UI).
4. Thẩm mỹ ô checkbox rỗng (border+NBSP hẹp): nếu owner muốn ô vuông cân —
   đổi `_CHK_NBSP` thành 2 NBSP/ký tự rộng, chạy lại D15 + mutation.
5. Font render: C4 ghi nhận sans-fallback nghi vấn ở thumbnail — verify font
   nhúng trong PDF v2; nếu lệch, pin font nhúng LibreOffice profile.
6. UI/form sau này — quy trình bắt buộc khi đổi band/nhãn/geometry:
   sửa `build_form_maps.py` (generator) → regen 4 bước ×2 zero-diff → sync
   pin `test_header_layout` + `test_docx_layout_ui` + parity test P1.5 →
   render mẫu ảnh hưởng → duyệt ảnh trang 1. CẤM sửa tay
   `app/templates/**`, `app/data/blocks/**`, `form_maps.json`.
7. **Windows/release (F6) và human sign-off (F5)** vẫn là gate chưa chạy:
   O5 (human review corpus) — AI review 100% được phép nhưng chữ ký người
   không được giả; O6 (Windows S1–S8) — cần máy Windows thật.

## 4. Excel import/export — khi owner mở lại (KHÔNG triển khai trước lệnh)

Kiến trúc đã P6=C đủ 4 cụm (M72 pilot, hộ kinh doanh, thay đổi ngành, thuế);
openpyxl pin 3.1.5; questionnaire tách khỏi form_maps; manifest
`blocked_tt121_migration` chặn cụm trỏ form chưa migrate; round-trip/negative
trong runner. Khi mở, làm ĐÚNG thứ tự (từ audit Excel 2026-09-09):

1. Map M72 vào use case "thành lập DN" hoặc làm questionnaire M01–M05 (hiện
   chọn thủ tục thành lập rồi bấm "Xuất phiếu" sẽ nhận NO_QUESTIONNAIRE);
2. Round-trip đầy đủ từng cụm còn lại (hiện chỉ M72 có RT; 6 artifact còn
   lại mới có validate + negative);
3. UI E2E tự động cho nút xuất/nạp phiếu (chọn → xuất → nạp → draft, cancel);
4. Chốt `ho_so_bao_gom` rồi thêm bảng "Giấy tờ bạn cần chuẩn bị" vào phiếu;
5. Owner duyệt visual workbook bằng Excel thật từng cụm (máy dev không có
   Excel — còn NOT RUN);
6. Quy ước bất biến: questionnaire regen ĐI CÙNG regen template (đã có gate
   Q1a/Q5a/Q6a); đổi nội dung câu hỏi bump `version` per-question.

## 5. Thứ tự merge & vận hành (giữ nguyên kỷ luật PLAN v7)

1. contract/test truth → 2. UI runtime → 3. DOCX/generator source →
4. Lead regen generated ×2 (lần 2 zero-diff) → 5. runner + coverage →
6. corpus render + detector + visual → 7. Excel rollout → 8. Windows →
9. independent audit.
Worktree: mỗi lane một worktree/branch, không tự merge; Lead merge theo thứ
tự trên; allowlist thêm từng entry có lý do, không wildcard; KHÔNG push khi
chưa có lệnh owner; worktree dọn sau khi evidence đã commit — NGOẠI TRỪ
`f3-corpus-v2` (chứa corpus evidence gitignored).

## 6. Rủi ro pháp lý đang mở (tổng hợp)

| Rủi ro | Trạng thái | Hành động |
|---|---|---|
| Band thiếu nhãn pháp định 'TÊN DN/HKD' vs bản giấy (23 form) | DECIDED-DIFF e148d83, đã đối chiếu ảnh nguồn P0/P1 | Owner xác nhận lại (P1.4) |
| M09: mất mục 7 "Thành viên công ty…Gửi kèm", 2 bảng chưa rebuild, câu hỏi chân trang/khối ký | PIN BLOCKED trong `r3b1` (suite đỏ nếu đụng) | Owner chốt từng mục (đang mở từ F0L) |
| M45/M53 trang ký mồ côi | đã allowlist class (i), cụm nguyên khối | P1.1 adjudicate |
| D5 class (i) 62 entry "trang cuối tự nhiên" | adjudicate hiện hành | prune stale sau v2, giữ phần còn lại |
| Chân trang/khối ký M09, DECIDED-DIFF, A4 geometry | chưa có quyết định | không tự đổi nội dung pháp lý |
