# Defect registry — Wave D2 Defect Hunt (lệnh owner 2026-08-28)

> Owner lệnh: các lớp lỗi hiển thị/nội dung phải được **identify tận gốc rồi
> loại bỏ** trước khi bàn giao — không vá tay từng mẫu. Sổ này track từng lớp
> lỗi: bằng chứng → gốc rễ → cách sửa → trạng thái. Một lớp lỗi = một fix hệ
> thống + test/census chống hồi quy, KHÔNG sửa từng file generated.

## Audit reconciliation — 2026-08-30 @ `6ae63c2`

> Bảng này là trạng thái hiện hành, ưu tiên hơn các nhãn `IN FIX/OPEN` lịch sử
> bên dưới. Chi tiết kế hoạch xử lý nằm trong `PLAN.md` v4.

| Class/gap | Trạng thái hiện tại | Evidence mới |
|---|---|---|
| 1 Checkbox dẹt | FIXED, cần giữ regression | runner suites liên quan PASS; blocks glyph census cần đưa thành gate cuối |
| 2 Đứt đánh số | **FIXED (Wave D batch 2, `fe0c680`)** | dòng pointer mục 7 (M03) + mục 8–9 (M04) khôi phục qua spec `inserts pos:"end"` — nguyên văn para 847/1161/1162 bản gốc full; numbering gate exit 0 (3/3 chain OK, 0 JUMP, 0 GLUE). Phần đuôi mục 8–13 (thuế/BHXH/CSHHL) là D1.3/D1.5/D3.3 OPEN — owner packet có bằng chứng delta 116→226 dòng |
| 3 Footnote GLUE | **RESOLVED census-level (Wave D batch 1)** | 50/50 hit là superscript đã tách đúng từ BASE; `numbering_audit` giờ vertAlign-aware → **0 unresolved**; test pin `tools/test_extractor_footnote_glue.py` |
| 4 Header hai band | **PASS + lock test (Wave D batch 1)** | UI band đúng trái/phải (`test_docx_layout_ui.js` 16/0); DOCX pinned `test_header_layout` 11/11 |
| 5 | Gộp vào Class 9 | — |
| 6 Số mồ côi/bảng thuế PLII_M03–M06 | OPEN, chờ owner mở scope | Word/PDF evidence cũ; chưa có rebuild table chính thức |
| 7 Khoảng trống chữ ký | **FIXED render-layer (Wave D batch 1)** | PLI_M70 2/87 vị trí thiếu dòng trống — `_ensure_signature_space` chèn lúc render; test T0–T2 đỏ→xanh; PLI_M09 thiếu 4 khối ký = BLOCKED_OWNER (mất ở tách nguồn, chờ regen) |
| 8 Dấu X rơi dòng | **CLOSED — không phải defect (Wave D batch 1)** | đo 44 chk × 87 mẫu: 0/44 trường hợp X tách khỏi label khi nguồn để cùng dòng; dòng "X"/"□" một mình là thiết kế bản giấy (khớp audit 128 đoạn); test khóa T3–T5 |
| 9 `undefined`/`6` trong bảng ngành | **FIXED (Wave D batch 1, `74ce895`)** | root cause: applyVsicPick đọc sai key (`ma_nganh` vs `ma`) + ghi ô theo INDEX + normalize bỏ sót; fix normalize/_row_id-binding/export guard; 36 test mới |
| 10 Verifier PLII_M02 table-region | **FIXED (Wave A, `cdb39f9`)** | classifier theo semantic header (band/thuế "Chỉ tiêu"/industry); đối chiếu theo THỨ TỰ vùng (bắt thiếu/thừa/đảo); selftest negative mutation trong verifier; `test_industry_household` 13/0, `p1_c` VERIFY PASS |
| 11 Manifest/coverage drift | **MEASURED (Wave B, merge `9aa755e`)** | ma trận 111/111 tại `docs/table_coverage_current.{json,md}`; gate 2 chiều exit 1 với **42 drift**: 12 `missing_grid_vs_evidence` (census stale — capital M03/M04/M05/M12, thuế+member PLII_M02) + 30 `implemented_missing_evidence` (already_complete nhưng thiếu runtime contract — chủ yếu nhóm chk; cần adjudicate cơ chế chk-token trước khi refresh manifest). Backlog thật: **26 section cần làm** (20 MISSING + 6 PARTIAL); 41 BLOCKED_OWNER; override 22/22 resolve OK |
| 12 L1 structural regression | **PARTIAL (Wave D batch 1)** | newline 309→263 toàn bộ hợp lệ (0 mất dữ liệu) — baseline census cập nhật 263; còn 4 STT-glue + 2 digit-run = BLOCKED_OWNER template (PLII_M02 #69/#122, PLI_M72 #109/#112) → batch 2 |
| 13 Visual evidence freshness | **UI: RUN @ Wave C (87/87 PASS)**; Word PDF: NOT RUN | UI Playwright 87/87 (0 marker/undefined/overlap, keyboard 3070 tab-stop, 3 viewport + zoom 200%); DOCX structural 87/87. Word AppleScript bị TCC chặn (-1712/-609); computer-use cũng bị chặn (accessibility/screen recording denied) → cần owner cấp quyền hoặc chấp nhận NOT RUN |
| 14 Validation gap khối liên hệ (Wave C F1) | **FIXED (Wave D batch 1, `74ce895`)** | 4 key vào FIELD_META dùng chung + type phone/website + so_cccd type `cccd` 7 grid meta + validateGridLoop per-type; 110 test mới phủ đủ 20 form |
| 15 PLI_M12 chk kép "Có □/Không □" (Wave D phát hiện phụ) | **FIXED (Wave E fix, `2593e3e`)** | generator 2 PHA: legacy toàn form giữ byte + convention chỉ cho đoạn key-trùng với exclusion TẦM FORM; regen 7 form drift (M01/M02/M03/M04/M05/M12/M15); re-audit độc lập: 0 đoạn dup trong 87 blocks, 4 câu hỏi M12 4 cặp key riêng, DOCX 1 key = 1 X; header_layout [FIELDS] 11/0. Ghi nhận OBS: PLII_M06 `co_quan_dkkd`×2 = cùng biến nhắc 2 lần trong 1 câu — by-design |
| 16 Template bị Word 16.16 từ chối "corrupt/unreadable" (Wave P1 phát hiện 2026-09-03) | **OPEN — BLOCKER G6, root cause chưa bám được** | Word 16.16 (16.16.27, Office 2019 Mac) từ chối mở `app/templates/PLII_M02.docx`, `PLI_M12.docx`, `PLI_M03.docx` (dialog "corrupt"/"unreadable content", có recovery; Word từng crash). `PLI_M01.docx` + render M01 + file python-docx minimal mở OK. Nguồn gốc `PL1_Mau_12_tach_tu_file_full.docx` CŨNG bị từ chối → lỗi thừa kế từ serialization của nguồn convert cũ, generator trung thành giữ nguyên. LO/lxml/textutil/XSD-validate (ECMA 376 transitional, 5th ed) đều PASS; violation profile M02 ≡ M01 → khía nghiêm ngặt của Word chưa xác định. Tất cả gate structural hiện có MÙ với lớp lỗi này. Cần: recovery-diff (Yes → save repaired → diff) hoặc schema deep-diff trong phiên chuyên trách |

Audit handoff đầy đủ, gồm exact 23 form GLUE và ranh giới structural/visual:
`docs/whole_app_audit_2026-08-30.md`.

Release runner audit: 43 PASS / 3 FAIL trong sandbox; a11y fail do bind localhost
EPERM nhưng chạy ngoài sandbox đạt 36/36, nên còn hai FAIL verifier/region cần sửa
thật. Không gọi release xanh cho tới khi full runner chạy ở môi trường phù hợp đạt
0 FAIL/0 critical NOT RUN.

> **Cập nhật Wave A 2026-09-02 (`cdb39f9`):** runner có preflight `bind_localhost`
> → a11y NOT RUN có lý do khi môi trường cấm bind (không còn FAIL giả); release
> chính thức vẫn bắt buộc a11y ở môi trường hỗ trợ. Trên máy dev cho phép bind:
> **46 PASS / 0 FAIL / 0 NOT RUN — VERDICT PASS**. Class 10 FIXED như bảng trên.
> Class 3/11/12/13 vẫn OPEN đúng trạng thái.

## Class 1 — Checkbox dẹt thành text (BHXH "3 tháng một lần")

- **Bằng chứng:** owner báo thiếu checkbox "3 tháng" cho phương thức đóng
  BHXH. Nguồn Word PLI_M01 mục 7 có "Phương thức đóng BHXH (chọn 1 trong 3
  phương thức)" + "□ 3 tháng một lần"; blocks PLI_M01 b132 là `p body` text
  "□ 3 tháng một lần" (không tick được) giữa 2 block `chk` chuẩn.
- **Gốc rễ:** `build_form_maps.process_checkboxes` chỉ gắn the `{chk_*}` khi
  nhãn khớp whitelist `CHK_RULES`; "3 thang mot lan" (không số 0 đầu) không
  khớp rule "03 thang mot lan" → glyph ở lại nguyên văn.
- **Fix hệ thống:** rule `0?3/0?6 thang mot lan` + fallback `_auto_chk_key`
  (mọi ô □/☐ không khớp rule đều được gắn the `chk_auto_<slug>`, dedupe).
  Không phụ thuộc whitelist nữa — lớp lỗi xóa sổ.
- **Trạng thái: FIXED** @ `ba64f29` — regen 4 mẫu (M01/M02/M15/PLII_M02),
  6 glyph → 6 chk, sandbox 0 glyph, visual re-shoot 4/4
  (`generated_ho_so/_visual_layout/chkfix/`), runner 46/0/0.

## Class 2 — Đứt đánh số mục / mất mục giữa các mẫu companion

- **Bằng chứng:** owner báo M09 (tab Danh sách thành viên công ty hợp danh)
  nhảy mục 6 → mục 8, mất mục 7. Census `tools/census/numbering_audit.py`:
  CHAIN GAP M03→M06 (6→8), M04→M08 (7→10), M05→M09 (6→8); M09 còn thiếu cả
  mục 1..7 và nhiễm lặp "I./1." (vùng p103-p222, D3.1).
- **Gốc rễ:** nguồn docx các mẫu chính bị CẮT (M03 hết mục 6, M04 hết 7,
  M05 hết 6 — D1.3/D1.5 cũ) trong khi companion (DS thành viên/cổ đông)
  tiếp tục đánh số từ mục 8/10 theo biểu mẫu gốc.
- **Fix:** rebuild theo Phụ lục I TT 68 (lệnh owner 2026-08-28) — lane
  `cap-von` (M03/M04/M05/M12 + thuế PLII_M02) và lane `m09-rebuild` (M09 14
  cột + đánh số liên tục). Sau merge: đăng ký `numbering_audit --gate` vào
  release_runner (EXCEPTIONS rỗng).
- **Trạng thái: IN FIX** (3 lane đang chạy).

## Class 3 — GLUE chữ số chú thích chân trang trong heading/body

- **Bằng chứng:** census GLUE 23/87 mẫu: "9. Thông tin về việc đóng bảo hiểm
  xã hội7:", "11. Thông tin về chủ sở hữu hưởng lợi của doanh nghiệp14:"…
  (số chú thích superscript bị flatten dính vào chữ).
- **Gốc rễ:** extractor L1 (docx_to_blocks) chưa có rule tách superscript
  footnote khỏi run text — gap V3 đã ghi ở Wave D audit lần 1.
- **Fix dự kiến:** rule V3 ở `docx_to_blocks.py` (Lead sở hữu) — khôi phục
  ký hiệu chú thích (D7.2=A) hoặc tách run superscript; regen toàn cục +
  visual re-shoot + runner. Chạy SAU batch-1 merge để regen gộp một đợt.
- **Trạng thái: OPEN** (Lead, xếp hàng sau batch-1).

## Class 4 — Layout header: TÊN DN/HKD + quốc hiệu xếp dọc

- **Bằng chứng:** nguồn docx PLII_M02 P2–P5 xếp dọc, "Số:" căn GIỮA (sai);
  bản Word gốc (PLII Mẫu 2 / PLI Mẫu 13): band 1 tên TRÁI + quốc hiệu PHẢI,
  band 2 "Số:" TRÁI + ngày-tháng-năm PHẢI.
- **Fix:** lane `hdr2col` — tái cấu trúc header thành bảng không viền 2 cột
  ở lớp build_form_maps (cấm sửa tay generated); Lead regen + visual re-shoot
  từng mẫu ảnh hưởng (UI + DOCX qua Word).
- **Trạng thái: IN FIX** (lane đang chạy).

## Class 5 — "Vấn đề nhập trong bảng ngành nghề" (ĐÃ TÁI HIỆN — chuyển Class 9)

- Probe 2026-08-28 trên snapshot sạch không tái hiện; screenshot owner
  14:13 sau đó tái hiện được với dấu hiệu cụ thể → nhập vào Class 9.

## Class 6 — Số mồ côi trong PDF xuất (bảng thuế bị dẹt ở mẫu NGOÀI 5 nhóm)

- **Bằng chứng:** owner duyệt `generated_ho_so/_visual_layout/hdr2col/pdf/PLII_M06.pdf`
  (Word render bản export thật) và báo "có các số lẩn lơ mất thẩm mỹ" — các số
  "4/5/6/1/2" đứng riêng một dòng quanh mục 6 Thông tin đăng ký thuế.
- **Gốc rễ:** census blocks PLII_M06 KHÔNG có paragraph số standalone — các số
  đó là STT/số mục của BẢNG CHỈ TIÊU THUẾ bị dẹt thành text ở nguồn (mẫu
  tạm ngừng HKD — KHÔNG thuộc 5 nhóm được duyệt rebuild, các lớp fixed-matrix
  thuế của nhóm này còn BLOCKED).
- **Hướng xử lý:** cần owner mở phạm vi rebuild bảng thuế cho nhóm PLII_M03–M06
  (tạm ngừng/chấm dứt HKD) theo TT 68/121, hoặc chấp nhận REMAP các số tàn dư
  vào layout dạng danh sách như bản gốc. KHÔNG tự mở phạm vi.
- **Trạng thái: CẦN OWNER CHỐT PHẠM VI.**

## Class 7 — Chữ ký không có chỗ trống để ký

- **Bằng chứng:** owner: "ký họ tên phải chừa chỗ ra cho đúng để người ta ký".
  Blocks PLII_M06 b25 `signature` = "CHỦ HỘ KINH DOANH\n(Ký và ghi họ tên)1"
  — không có khoảng trống dọc nào trên chữ ký; bản Word gốc có 2–4 dòng trắng.
- **Gốc rễ:** extractor giữ nguyên đoạn nguồn không có dòng trống; renderer
  không cộng thêm chỗ ký. (Glue số "1" sau "(Ký và ghi họ tên)" = Class 3.)
- **Hướng xử lý:** rule layout cho block role `signature` (spaceBefore hoặc
  N dòng trắng) ở extractor/renderer — thuộc đợt V3/GLUE + P5R gate G5/G7.
- **Trạng thái: OPEN** (xếp hàng đợt extractor V3, Lead sở hữu).

## Class 8 — Dấu X checkbox rơi riêng dòng trong PDF xuất

- **Bằng chứng:** PLII_M06.pdf: "Khấu trừ" / "X" tách 2 dòng; "Có X" và
  "Không X" mỗi cái một dòng (bản gốc in "Có □  Không □" cùng hàng).
- **Gốc rễ:** template đặt nhãn và ô {chk_*} ở paragraph kế nhau; export
  docxtemplater đổ giá trị "X" xuống dòng riêng. Cần gộp nhãn+tag cùng
  paragraph ở template/extractor, hoặc renderer chk ghép inline.
- **Trạng thái: OPEN** (Lead, đợt layout DOCX cùng Class 7).

## Class 9 — Bảng ngành nghề: ô Tên ngành hiện "undefined", Mã ngành tự có số "6"

- **Bằng chứng:** screenshot owner 2026-08-28 14:13 — app, thủ tục "Thành lập
  Công ty TNHH hai thành viên trở lên" (PLI_M03), mục 4 bảng ngành: ô Tên
  ngành dòng 1 hiện chữ **`undefined`** (viền đỏ, kèm lỗi bắt buộc "bắt buộc
  kê khai ít nhất một dòng"), ô **Mã ngành tự điền sẵn `6`** (text bôi đen);
  cột "Ngành, nghề kinh doanh chính" hiển thị ○ (hình tròn) thay □ như bản gốc.
- **Đây chính là tái hiện được Class 5** ("vấn đề nhập trong bảng ngành nghề")
  — đóng Class 5, tách thành Class 9 có bằng chứng cụ thể.
- **Giả thuyết gốc rễ (chưa xác nhận):** draft/autosave đã lưu chuỗi
  `"undefined"` (lỗi JS ghép chuỗi khi ghi draft) và giá trị rác `"6"` vào
  store của `ds_nganh.ten_nganh`/`ma_nganh`, hoặc binding ô input đọc nhầm
  key. Cần reproduce + dump draft json để chỉ đúng dòng code.
- **Trạng thái: OPEN — ƯU TIÊN CAO** (ảnh hưởng trực tiếp thao tác nhập của
  khách; lỗi dữ liệu 'undefined' có thể lan vào DOCX export).

## Phương pháp chống hồi quy cho Wave D2

- `tools/census/numbering_audit.py` (JUMP/CHAIN/GLUE) — inventory hiện tại,
  lên **gate** trong release_runner khi Class 2/3 đóng (EXCEPTIONS rỗng).
- Census glyph □/☐ = 0 trong mọi block — đã xanh từ `ba64f29`, sẽ ghép vào
  audit suite khi đăng ký gate numbering.
