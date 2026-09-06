# Defect registry — Wave D2 Defect Hunt (lệnh owner 2026-08-28)

> Owner lệnh: các lớp lỗi hiển thị/nội dung phải được **identify tận gốc rồi
> loại bỏ** trước khi bàn giao — không vá tay từng mẫu. Sổ này track từng lớp
> lỗi: bằng chứng → gốc rễ → cách sửa → trạng thái. Một lớp lỗi = một fix hệ
> thống + test/census chống hồi quy, KHÔNG sửa từng file generated.

## Phase 5R reconciliation — 2026-09-04 @ `93d69f0`

> Trạng thái hiện hành của WLAY-001..012 (audit `word_layout_audit_2026-09-03.md`).
> Gate bằng chứng: `generated_ho_so/_visual_layout/phase5r_gate/final/` —
> 455/455 records (91 form × 5 fixture) detector 0, Word open-direct 91/91,
> runner 54/0/0. Baseline RED cùng gate: `.../baseline_c9d095e/` (244/455 FAIL).

| WLAY | Trạng thái | Fix gốc rễ + bằng chứng |
|---|---|---|
| 001 source-indicator lộ 44 form | **CLOSED** | `_drop_source_indicators` (docx_render, body-level, reuse classify_role — UI/DOCX nhất quán); D1=0 trên 455 records; "Mẫu số N" pháp lý giữ nguyên (test pin) |
| 002 M70 ký 2x1 sập dọc | **CLOSED** | spec W1 rebuild 1x2 không viền (`build_horizontal_signature_tables`) + render guard; PNG gate chứng minh 2 signer cùng hàng; D6 orientation pass |
| 003 khối ký tách trang | **CLOSED** | `_keep_signature_blocks`: keepNext+keepLines cặp title/instr, cantSplit hàng bảng ký; SIG_SPLIT=0 (M09, PLII_M25, PLI_M14 đã hết) |
| 004 M15 thiếu vùng viết | **CLOSED** | `_ensure_signature_space` mở rộng: vùng viết dưới MỖI instruction theo `min_write_gap_pt` contract; M15 6.4pt → ≥40pt (đo pymupdf) |
| 005 M12 matrix phẳng | **PARTIAL / BLOCKED_OWNER** | 5 matrix materialized OK (nguon_von, nganh_bo_sung/xoa_bo/sua_doi, ndd_uy_quyen 8×15 — gap 2 nhóm cột B145 chờ tag); 3 BLOCKED_OWNER chờ owner duyệt cấu trúc: tai_san_gop_von ×2 (D1.2 chỉ chốt B cho M01), co_cau_loai_co_phan_sau_thay_doi (nguồn in sẵn lỗi chính tả "ưu đã biểu quyết") — `tools/phase5r_table_policies.json` |
| 006 field code lộ M28 | **CLOSED** | generator `drop_flat_field_code_paras` (loại số trang stale của nguồn, không dựng lại field sai vị trí) + guard `_strip_flat_field_code`; grammar đồng bộ 3 nơi (generator/render/detector); D2=0 |
| 007 trang trắng/boundary thừa | **CLOSED** | `drop_foreign_annex_tail` (M80 không kéo banner PHỤ LỤC II); `_drop_trailing_empty_para` drop TOÀN BỘ run paragraph rỗng cuối body (M72 TNHH_2TV, M05 14 para); D4=0, D5 BLANK=0 trên 455 records |
| 008 bảng rộng chữ vỡ | **CLOSED (policy)** | census 12 bảng ≥10 cột; landscape LOẠI bằng evidence (0/87 nguồn landscape); split-table chỉ candidate (nguồn in trọn 1 bảng); width_policy='content' 12/12 + render pin tblHeader/cantSplit/tblW; D9=0 |
| 009 orphan page | **CLOSED (policy)** | policy: trang chỉ chứa instruction ký không title = lỗi; 9 trang BLANK baseline biến mất sau keep-together; 32 combo SPARSE còn lại là census có giải thích (footnote/trang cuối pháp lý) |
| 010 fixture TEST + tick tràn | **CLOSED** | `phase5_fixtures.py`: 5 fixture semantic giá trị phân biệt theo họ key; validator V1–V4; regression: dummy cũ bị chặn V1 |
| 011 label/value glue | **OPEN (census)** | fixture semantic đã thay TEST; census 553 candidate toàn corpus — phần lớn là artifact nối ô bảng kề nhau của PDF text extraction; cần adjudicate từng nhóm trước khi sửa run-assembly (không chèn space mù) |
| 012 gate đánh đồng structural/visual | **CLOSED** | gate tách OPEN_DIRECT (word loop) / STRUCTURAL (detector XML) / VISUAL_LAYOUT (detector PDF + PNG từng trang + reviewer_verdict trong manifest); structural không tự nâng thành visual |

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
| 6 Số mồ côi/bảng thuế PLII_M03–M06 | **CLOSED — premise false (P3 lane, `a282f76`)** | P3 lane xác định: cả 4 mẫu PLII_M03–M06 **KHÔNG có bảng thuế trong nguồn** (0 w:tbl, 0 marker thuế, kiểm cả `_Bieu_mau_PL_I_II_full.docx` P5919–P6017). "Số mồ côi" trong evidence cũ gần như chắc chắn là đuôi mục thuế của mẫu PLI_M03/M04/M05 (đã xử lý ở P1=A). 4 spec PIN BLOCKED + suite 7/0 |
| 7 Khoảng trống chữ ký | **FIXED render-layer (Wave D batch 1)** | PLI_M70 2/87 vị trí thiếu dòng trống — `_ensure_signature_space` chèn lúc render; test T0–T2 đỏ→xanh; PLI_M09 thiếu 4 khối ký = BLOCKED_OWNER (mất ở tách nguồn, chờ regen) |
| 8 Dấu X rơi dòng | **CLOSED — không phải defect (Wave D batch 1)** | đo 44 chk × 87 mẫu: 0/44 trường hợp X tách khỏi label khi nguồn để cùng dòng; dòng "X"/"□" một mình là thiết kế bản giấy (khớp audit 128 đoạn); test khóa T3–T5 |
| 9 `undefined`/`6` trong bảng ngành | **FIXED (Wave D batch 1, `74ce895`)** | root cause: applyVsicPick đọc sai key (`ma_nganh` vs `ma`) + ghi ô theo INDEX + normalize bỏ sót; fix normalize/_row_id-binding/export guard; 36 test mới |
| 10 Verifier PLII_M02 table-region | **FIXED (Wave A, `cdb39f9`)** | classifier theo semantic header (band/thuế "Chỉ tiêu"/industry); đối chiếu theo THỨ TỰ vùng (bắt thiếu/thừa/đảo); selftest negative mutation trong verifier; `test_industry_household` 13/0, `p1_c` VERIFY PASS |
| 11 Manifest/coverage drift | **MEASURED (Wave B, merge `9aa755e`)** | ma trận 111/111 tại `docs/table_coverage_current.{json,md}`; gate 2 chiều exit 1 với **42 drift**: 12 `missing_grid_vs_evidence` (census stale — capital M03/M04/M05/M12, thuế+member PLII_M02) + 30 `implemented_missing_evidence` (already_complete nhưng thiếu runtime contract — chủ yếu nhóm chk; cần adjudicate cơ chế chk-token trước khi refresh manifest). Backlog thật: **26 section cần làm** (20 MISSING + 6 PARTIAL); 41 BLOCKED_OWNER; override 22/22 resolve OK |
| 12 L1 structural regression | **RESOLVED (P2 member grid rebuild, `dfb6c14`)** | STT-glue + digit-run = **0** trên template/blocks cả M02/M72; `check_layout_l1` **exit 0**; newline 265 ≥ ngưỡng 249 |
| 13 Visual evidence freshness | **UI: RUN @ Wave C (87/87 PASS)**; Word PDF: NOT RUN | UI Playwright 87/87 (0 marker/undefined/overlap, keyboard 3070 tab-stop, 3 viewport + zoom 200%); DOCX structural 87/87. Word AppleScript bị TCC chặn (-1712/-609); computer-use cũng bị chặn (accessibility/screen recording denied) → cần owner cấp quyền hoặc chấp nhận NOT RUN |
| 14 Validation gap khối liên hệ (Wave C F1) | **FIXED (Wave D batch 1, `74ce895`)** | 4 key vào FIELD_META dùng chung + type phone/website + so_cccd type `cccd` 7 grid meta + validateGridLoop per-type; 110 test mới phủ đủ 20 form |
| 15 PLI_M12 chk kép "Có □/Không □" (Wave D phát hiện phụ) | **FIXED (Wave E fix, `2593e3e`)** | generator 2 PHA: legacy toàn form giữ byte + convention chỉ cho đoạn key-trùng với exclusion TẦM FORM; regen 7 form drift (M01/M02/M03/M04/M05/M12/M15); re-audit độc lập: 0 đoạn dup trong 87 blocks, 4 câu hỏi M12 4 cặp key riêng, DOCX 1 key = 1 X; header_layout [FIELDS] 11/0. Ghi nhận OBS: PLII_M06 `co_quan_dkkd`×2 = cùng biến nhắc 2 lần trong 1 câu — by-design |
| 16 Template bị Word 16.16 từ chối "corrupt/unreadable" | **MITIGATED at export layer — CHƯA VERIFIED 87/87 Word** | LO normalize (re-save qua `soffice --convert-to docx`) chạy tự động trong Bridge.export → cả .docx và .pdf đều Word-compatible. Tokens/chk/bảng giữ nguyên qua LO round-trip. E2E test: M02 corrupt → normalize → 10.7KB docx + 177KB PDF. **Còn mở**: Word-open 87/87 corpus verification; recovery-diff để tìm root cause OOXML |

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

## Class I1 (6V) — Gate đỏ giả: LibreOffice profile mặc định dùng chung [ĐÃ ĐÓNG 6V-V0]

- **Bằng chứng:** 2026-09-04 runner 56/1 trên HEAD 294604c vốn 57/0; isolated
  profile `-env:UserInstallation` exit=0 mọi phép; `.lock` 03/09 + zombie
  `(soffice)` 97% CPU giữ profile mặc định; ps thấy soffice của worktree
  p5r-evidence chạy song song.
- **Gốc rễ:** `app_web/main.py` gọi soffice qua profile mặc định; 2 tiến trình
  chồng nhau → exit=1; kill giữa chừng để lock/zombie.
- **Fix:** `6v-infra 003c3dd` — helper `_run_soffice` profile
  `/tmp/lo_prof_<case>_<pid>` + retry 1 lần + LO_CRASH/LO_PROFILE_BUSY;
  suite `test_export_concurrency` chống hồi quy. Gate V0(a) 2 runner song
  song 2 PASS.
- **Di sản:** profile hỏng backup `~/Library/Application Support/LibreOffice/
  4/user.wedged_20260904` (xoá khi V0 ổn định 1 tuần — PLAN v6 mục 7).

## Class I2 (6V) — Evidence PNG M72 ghi đè lẫn nhau (1567/1644) [ĐÃ ĐÓNG 6V-V0]

- **Bằng chứng:** 25 record M72 cùng PNG dir `final/<fixture>/PLI_M72/`;
  manifest claim 1644, đĩa 1567; long-boundary dhdn claim 14 trang thực chất
  là 14 trang đầu của ctcp.
- **Fix:** `6v-infra 4b10169` — PNG `<fixture>/<tag>/<FORM>/` +
  `assert_png_disk_matches_manifest` exit 2. Corpuscheck V0: claim=disk=1644.

## Class I3 (6V) — Summary gate che candidates sau con số 0 [ĐÃ ĐÓNG 6V-V0]

- **Bằng chứng:** summary in `D9_table_grid: 0` dù det_table_grid bắt
  NARROW_COL trên corpus final (PLI_M02/M12 cột 566 < sàn 567).
- **Fix:** `6v-infra 62ec9e7` — summary hai lớp + candidate_ids; corpuscheck
  V0 hiển thị CANDIDATES: 360 (D9=50, D6=159, D11=201, D5=78) trung thực.

## Class I5 (6V) — out_dir export collision cùng giây [ĐÃ ĐÓNG 6V-V0]

- **Bằng chứng:** suite V5 tái hiện 2/2: 2 worker cùng case_id cùng giây nhận
  chung out_dir (`mkdir exist_ok=True`), `_lo_norm` bị worker kia xóa dưới
  chân soffice → exit=0 mà không có file. Gốc rễ thứ 3 của sự kiện 56/1 (agent
  6v-infra phát hiện khi viết suite concurrency).
- **Fix:** `6v-infra fbb775e` — `mkdir(exist_ok=False)` + vành đai `_p<pid>`,
  giữ hành vi tuần tự cũ trong cùng process.

## Class I6 (6V) — Sandbox cố định test_phase5r_signatures đỏ giả khi chạy song song [ĐÃ ĐÓNG 6V-V0]

- **Bằng chứng:** 2 runner `--only test_phase5r_signatures` song song: 1 PASS
  / 1 FAIL (FileNotFoundError/FileExistsError tại `/tmp/p5r_laneB_*` do 2
  process rmtree lẫn nhau) — không phải soffice.
- **Fix:** Lead `5cceeac` — suffix pid cho SANDBOX_TPL/TEST_OUT/sandbox_neg;
  sau fix 2 runner song song 2 PASS (Gate V0(a)).

## Class I4 (6V) — MIN_COL_TWIPS 567 lệch census 566, candidate vĩnh viễn [ĐÃ ĐÓNG 6V-V1 — auditor finding F1 sửa nhãn]

> Sàn legacy làm tròn xuống 566 đã merge tại `5b941f9` (D9 hai tầng);
> NARROW_COL legacy = 0 trên corpus (scoreboard v2). Phần "bảng ≥10 cột
> < 900twips" thuộc B5 — phase V3.

- **Bằng chứng:** det D9 dùng `< 567` nhưng corpus có bảng min col 566
  (rebaseline policies min_col 567 "census thực tế" 81b5931); hit rơi vào
  candidate không chặn.
- **Kế hoạch:** V1 nâng D9 (bảng ≥10 cột min < 900twips → hard sau V2); số
  liệu B5 (60 bảng/10 form) trong PLAN v6 mục 1.2.

## Class B1–B5 (6V) — 5 lớp lỗi visual còn tái hiện, baseline đo được @ V1 [OPEN — lane V2]

Số liệu baseline ĐỎ chính thức: `tools/census/6v_v1_baseline.json` (455 record
corpus v0_corpuscheck, detectors D13–D16 + D9 hai tầng; corpus template
identical audit-HEAD — git diff 294604c..313b0af app/templates rỗng).

- **B1 skeleton glue — D13: 323 rec / 1104 hit / 77 form.** Gốc rễ: template
  skeleton không space quanh placeholder (PLII_M08 `{dia_diem_ky}, ngày{ngay_ky_vb}tháng…`),
  kèm contact-glue `{dien_thoai_khac}Thư điện tử` (PLII_M13). Fix lane: V2-C1 (regen skeleton).
- **B2 name-slot trống — D14: 14 form RED** (PLII_M08/10/11/12/13/19/21/22/23/25/27/28,
  PLI_M43, PLI_M71; 65 form có slot). 3 gốc rễ (audit): thiếu placeholder /
  có `{key}` nhưng form_maps thiếu tag / slot literal `……`. Fix lane: V2-C2
  (scope 14 form; 5 form slot-nhan-token → B4/C4). Con số "~37" audit cũ =
  heuristic thô, supersede.
- **B3 tick X trần — D15: 17/17 form có chk RED, 191 hit** (130 BARE_X_PARAGRAPH +
  61 X_OWN_LINE). Fix lane: V2-C3, chờ owner Q-V1 (glyph chuẩn).
- **B4 token làm giá trị — D16: 355 rec / 8846 hit / 82 form** (2865 TOKEN_VALUE
  + 5981 TOKEN_FRAGMENT do Word wrap cột hẹp). Gốc rễ kép: fixture fallback
  LABEL_HOA_N + bảng hẹp xé token. Fix lane: V2-C4 (fixture realism); phần
  wrap phụ thuộc B5.
- **B5 bảng ≥10 cột hẹp — D9 NARROW_COL_WIDE: 60 bảng / 10 form** (PLII_M01/02,
  PLI_M02/06/07/09/10/12/15/72; mọi bảng min col 566 twips). Fix lane: V3
  sau owner Q-V2. Sàn legacy mới 566 (đóng I4 — bảng 566 không còn treo).

## Class 6V-V4a — kết quả adjudicate auditor/6v-visual (2026-09-05, docs/audits/6v/v4-visual-audit.md)

**D5 72 hit:** 59 hợp pháp + 7 chấp nhận → lập sparse allowlist; **6 lỗi thật
→ lane V4b**: orphan footnote note 4 hit (M12 p2, M80 p3×2, M02 p33 —
keep-with-previous) + M72 spillover 2 hit (tnhh_2tv/dhdn p3 — row tail tràn).

**Spot-check 15 trang: 12 PASS / 3 VIOLATION cùng lớp "vỡ token giữa từ trong
cột hẹp"** (PLII_M02 p4, PLI_M09 p16, M72 p2: "Nguyễ/n", "Singapo/re",
"060000/000023/9") → lane V4b: width redistribution theo longest-word cho cột
tên/quốc tịch/mã-GCTP (không đổi số cột, tổng 14400 giữ nguyên).

**Micro-census adjudicate:** a=1 form thật (M12 dòng ASCII-dot) + registry
per-family; b=3 form thật (M54/M55/M57 ngoặc ")" mồ côi) + 1 FP census
regex; c=0 (artifact paragraph-mark — đóng); d=31 form separator superscript
(cosmetic chuẩn hóa); e=14 form "STT" mồ côi (header bảng bị làm phẳng);
f=53 form band para_br **chờ owner Q-V8**; g=0 (đúng registry band).

**Finding ngoài phạm vi:** M76 thiếu khối ký — **ĐÃ ĐÓNG bằng nguồn gốc**
(05_cong_bo.../PL1_Mau_76... không có dòng ký — template đúng nguồn, là
thông báo chấp thuận điện tử). "Mẫu số N" vị trí M19 phải vs khác trái →
lane V4b đối chiếu nguồn gốc trong repo rồi đăng ký. Fixture: ngày chỉ số
ngày + cột "Chữ ký" nhận dữ liệu → lane V4b (policy handwriting-only cột).

## Class 6V-V4b — fix theo adjudication auditor/6v-visual (2026-09-05, lane agent/6v-v4fix)

Base: 960d0b2, worktree `dangky_kinhdoanh-worktrees/6v-v4fix` (nhánh 6v-v4fix).
Mỗi mục: việc → gốc rễ → fix → evidence. Số liệu trước/sau đo CÙNG môi
trường (tối 2026-09-05; corpus sáng 07:36 drift 46↔52 trang trên PLI_M12
long-boundary với template hash GIỐNG NHAU bee134e5 — main repo pass-free
cũng render 52 trang: drift môi trường LO/metrics, không phải do lane).

1. **D5 6 hit (iii)**: orphan footnote note 4 hit (M12 empty p2, M80
   empty/minimal p3, M02 long-boundary p33) + M72 spillover 2 hit
   (tnhh_2tv empty p3, dhdn minimal p3). Fix ở render
   (`tools/docx_render.py::_keep_footnote_notes`): bó CẶP sep→note đầu +
   note áp chót→note cuối (keepNext), đoạn ngắn kề trước keepNext, note
   cuối keepLines; separator đuôi-only của biến thể M72 không có chú thích
   (dhdn/dntn) bị bỏ. Đơn vị atomic cả cụm BỊ LOẠI vì tự sinh trang đứng
   riêng (M12 long-boundary 46→52 trang khi thử). Sau fix: 6/6 hit biến
   mất (p2 M12 = sep+note 173kt; p3 M80 = 2 note; p33→p35 M02 = notes
   12-13; M72 dhdn minimal 3→2 trang; tnhh_2tv p3 = bộ máy chú thích
   nguyên khối 219kt). HARD 0.
2. **Vỡ token cột hẹp (3 spot VIOLATION 5.1-5)**: width_policy content
   nâng cấp sàn longest-word trong generator (`_content_col_widths` 3 bước
   + `_table_word_floors` sample 48 giá trị ValueFactory/tag, metric đo từ
   corpus PDF: digit 135/lower 125/upper 175 tw + lề 216). 10 form bảng
   rộng regen; M72 4 bảng thành viên/cổ đông khai width_policy content
   (7-9 cột, CONTENT_POLICY_MIN_COLS=7). Sau fix: PLII_M02 p4 sạch hoàn
   toàn ('0600000000068' nguyên vẹn, 0 mảnh); PLI_M09 p16 + M72 p2: tên/
   quốc tịch/địa chỉ hết vỡ, **cột mã 13 chữ số CÒN vỡ** — giới hạn toán
   học: M09 14 cột × sàn 900 = 12600/14400 (dư 1800 < want 1101 của mã),
   M72 tnhh 8 cột portrait 8640 thiếu ~300 twips. **CHỜ OWNER**: landscape
   mở cho bảng 7-9 cột (vượt ngưỡng Q-V2) hoặc font 11pt cột mã hoặc
   fixture CCCD 12 số (đúng định dạng pháp lý hiện hành — hiện fixture
   13 số "0%d%011d").
3. **STT mồ côi 14 form (nhóm e)**: nguồn bị làm phẳng (0 w:tbl — bóc
   nguồn xác nhận), 'STT' trần body-level = header cột bảng không còn tồn
   tại → bỏ 18 đoạn trên 14 form (M12×4, M09×2, còn lại 1); caption + số
   mục giữ nguyên; bảng thật không đụng.
4. **Ngoặc ')' mồ côi M54/M55/M57 (nhóm b)**: nguồn vốn đã thiếu '('
   (0 mở/1 đóng) → bổ sung '(' theo chuẩn corpus; sau fix opens=closes=1.
5. **Separator superscript 31 form (nhóm d)**: bỏ vertAlign khỏi
   paragraph chỉ-gạch-dưới; sau fix 0/31.
6. **M12 ASCII-dot (nhóm a — 1 dòng thật)**: 'là:' + 118 chấm ASCII →
   '…'×34+'.' khớp chính form.
7. **Fixture**: 'ngay_sinh'/'ngay_cap' → ngày đủ dd/mm/yyyy (sinh 19xx,
   cấp 20xx); cột 'Chữ ký' (tag chu_ky, 9 bảng) = handwriting-only —
   fixture để trống, policy `is_handwriting_column` trong phase5_fixtures
   (D14/registry slot-tiêu đề giữ nguyên). Selftest 437 PASS.
8. **Census bug**: LIST_MARKER_RE bỏ tiền tố '(' (FP '(i)/(ii)' nhóm b) +
   base_commit lấy HEAD thật. Rebaseline: b 4→0, d 31→0, e 14→0; c=9
   (artifact đo — adjudicate 0), f=53 (Q-V8), g=8 (đúng registry band),
   a=75 (khác VAI TRÒ fill-line — FP lớp, chỉ 1 dòng thật là M12 đã fix;
   registry fill-line per-family chờ owner đối chiếu bản gốc).
9. **D5 sparse allowlist**: `docs/phase6v_d5_sparse_allowlist.json` nạp
   mặc định vào gate (`_d5_sparse_allowed` — khớp fixture/tag/form/page,
   khóa vắng = wildcard; BLANK giữ hành vi cũ). Mục tiêu: candidate D5
   "chưa adjudicate" = 0.
10. **"Mẫu số N" position**: nguồn↔template khớp 4/4 (M19 right; M30/
    PLII_M02/PLII_M03 trái) → đăng ký per-form trong decision_registry,
    không sửa; KHÔNG cần báo Lead (không có lệch).

## Wave v7 — HEADER-NAME-SYNC + SIGNATURE-USABILITY-SPACE (2026-09-05, main 77b992a→)

Base: PLAN v7 (owner ban hành), corpus tham chiếu phase6v/final @ 000e8e2.
Census đầu vào: `docs/audits/header_name_census_2026-09-05.{json,md}`
(216 occurrence / 87 form) + `docs/audits/signature_space_census_2026-09-05.md`.

### Class V7-H1 — HEADER-NAME-SYNC [ĐÃ ĐÓNG — hard gate D17]

- **Bằng chứng:** PLI_M32 band đầu trang (ô (0,0) bảng band) là literal
  `TÊN DOANH NGHIỆP` + dòng kẻ `-------` trong khi thân có input
  `{dn.ten_tieng_viet}` — nhập tên không cập nhật band ở UI lẫn DOCX.
- **Census:** 22 fillable-header-slot; 97 legal-title/subtitle; 88
  output-admin-only (85 đã bind); 9 not-applicable; 65 form không có band.
- **Fix gốc rễ (4 tầng, 1 registry):** `tools/header_name_binding.json`
  (nguồn chân lý) → generator `_bind_header_name_slot` (thay dòng kẻ bằng
  the {key}, fail-loud) → converter `_band_first_cell_to_mirror` (run
  `mirror`, KHÔNG input thứ hai) → render.js `span.mirror-fld` + app.js
  `mirrorKey` cập nhật ngay khi nhập/xóa. Gate `D17_header_name` HARD
  (valid-full): band còn dòng kẻ = HDR_NAME_UNBOUND; giá trị band khác thân
  = HDR_NAME_SYNC.
- **Scope:** 20 form bind (16 DN → `dn.ten_tieng_viet` gồm PLI_M32; 4 hộ
  PLII_M02–05 → `hkd_ten_tieng_viet_2`). Regen 20 template + 20 blocks ×2
  zero-diff (commit 55637db).
- **BLOCKED_OWNER:** PLI_M33 (band TÊN DOANH NGHIỆP, thân chỉ có
  `chu_hkd.ho_ten` — không có trường tên DN để mirror), PLII_M06 (band TÊN
  HỘ KINH DOANH, thân không có input tên hộ). +3 ô output inline chưa bind
  (M70 p14, M48 p17, M49 p9). Không tự bind — chờ owner.
- **Test:** `tools/test_v7_header_name.py` 8/0 (E2E blank/filled/A→B/
  Unicode/PDF-D17/mutation); V2c mutations; test_dom 69/0 (span mirror,
  không input thứ hai); header_layout 11/0.

### Class V7-S1 — SIGNATURE-USABILITY-SPACE [ĐÃ ĐÓNG — hard gate D8@72pt]

- **Bằng chứng:** census 2026-09-05: 195/420 cụm output dưới 72pt (185 phải
  ký tay), minimum 43.4pt — qua sàn cũ 40pt nhưng chật cho ký/họ tên/con
  dấu. D6 cũ chỉ nhận 215/420 cụm (grammar hẹp) và không đo cụm cuối trang.
- **Fix gốc rễ:** (1) registry `min_write_gap_pt` 40→72 toàn 78 entry;
  (2) detector D6 grammar ĐỒNG BỘ census (thêm "ký, ghi họ tên và đóng dấu",
  chỉ thị không ngoặc, "từng thành viên") + đo đến MÉP DƯỚI TRANG khi không
  có dòng dưới + tách "Đã ký" (không áp sàn viết tay) + SIG_MISSING hard;
  (3) render `_ensure_signature_space`: nhận cụm không ngoặc, skip "Đã ký",
  spacer exact-height ép sàn 72pt (chỉ thêm khoảng — nguồn có khoảng lớn
  hơn thì giữ nguyên).
- **Mutation bắt buộc (V2a/V2b):** gap 71 FAIL / 72 PASS / registry pin 80
  được tôn trọng / cuối trang được đo / "Đã ký" không bị ép / đóng dấu +
  từng thành viên nhận diện / SIG_MISSING / SIG_SPLIT / SIG_ORIENTATION.
- **Test:** test_phase6v_detectors 10/0; test_phase5r_signatures 6/0;
  docx_layout_signatures 8/0; signgap evidence chạy lại trên corpus mới.

### Verdict 9 form không có cụm ký (census nguồn 2026-09-05)

`PLII_M18`, `PLI_M05`, `PLI_M07`*, `PLI_M10`, `PLI_M71`, `PLI_M72`,
`PLI_M73`, `PLI_M74`, `PLI_M76` → **absence-correct** (nguồn gốc không có
chỉ thị ký, template khớp nguồn; chi tiết + bằng chứng 3 dòng cuối:
`docs/audits/header_name_census_2026-09-05.md` mục 4).
*PLI_M07: nguồn là stub 2 dòng, template tự dựng bảng + cột Chữ ký —
chiều ngược (template CÓ thêm so với nguồn); nguồn không đủ tái sinh.

## F0L migration defects — 2026-09-06 @ e268038

| Defect | Trạng thái | Fix gốc rễ + bằng chứng |
|---|---|---|
| M10 cột 16 transcribe sai 'Nhóm cá nhân có quan hệ gia đình/**họ hàng**7' | **CLOSED** | Ảnh p49 @350dpi đọc rõ '/hợp đồng7' (fn7: 'quan hệ gia đình... hoặc hợp đồng cùng nhau sở hữu'); sửa spec + inventory; regen template contains 'hợp đồng'; pin t_m10_2026_contract chặn hồi quy |
| M27/M30 mất khối chữ ký tiêu đề (para trống tại vị trí title) sau edit nguồn lane | **CLOSED** | B1 census_registry bắt titles=[]; khôi phục verbatim TT121 p69 (3 dòng + (Ký và ghi họ tên)6) / p70 (2 dòng + (Ký và ghi họ tên)2); census titles khớp registry; signers=1 |
| M27 glue superscript chú thích 4/5 (chữ số nằm run thường) | **CLOSED** | Tách run superscript tại source (para 20/34); test_extractor_footnote_glue 12/12 |
| p2a/r3b1 pin premise 2025 (M10 12 cột 'Quyền chi phối', M12 anchor index, M09 glue, STT-glue extinct) | **CLOSED** | Pin sync có bảng premise→hiện trạng→evidence trong comment test; không bỏ assertion nào |
