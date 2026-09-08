# F3-CORPUS-FINAL — Corpus cuối render từ HEAD sạch d70fe14 (phase8g_v2) — 2026-09-08

Agent: CORPUS-FINAL · Worktree `/Users/hoangminhlong/orca/dangky_kinhdoanh-worktrees/f3-corpus-v2` (branch `agent/f3-corpus-v2`).
Merge: `git merge main` → **fast-forward 20df7bc..d70fe14** (74 files: N-only sync, band label removal, render-fix, D18 bỏ ROW_COUNT_MISMATCH, D19 BAND_LABEL_PRESENT; không conflict).
**[dfix 2026-09-08] DETECTOR-FIX đóng HARD 0:** sửa 2 detector heuristic lớp PDF (D18 + D19) đúng root cause đã adjudicate — mutation 22/22, **re-run FULL gate phase8g_v2 → HARD-FAIL 0** (chi tiết mục DFIX cuối file; render corpus KHÔNG đổi — chỉ lớp detector).

## Corpus chính thức

**Đường dẫn tuyệt đối (gitignored, KHÔNG commit):**
`/Users/hoangminhlong/orca/dangky_kinhdoanh-worktrees/f3-corpus-v2/generated_ho_so/_visual_layout/phase8g_v2`

- Render: `python3 -X utf8 tools/phase5_visual_gate.py --outdir generated_ho_so/_visual_layout/phase8g_v2 --forms <86 active id>` (gate default chưa lọc `current_law_status` — truyền thủ công; inventory động **active 86**, skip đúng `[('PLI_M11', 'removed_by_current_law')]`)
- **450 record** = 5 fixture × 90 record/fixture (85 form tag `main` + PLI_M72 ×5 tag `m72_dntn/m72_tnhh_1tv/m72_tnhh_2tv/m72_ctcp/m72_dhdn`)
- **1737 PNG** (`png_disk_assert` claimed=1737 disk=1737 **ok=true**; −17 so phase8g do pagination dời sau N-only)
- `export_errors = 0`; smoke export `phase5_export_corpus` 85 batch OK + M72 ×5 variant OK

## Kết quả gates

| Gate | Kết quả |
|---|---|
| Preflight `release_runner` (`/tmp/f3v2_final_preflight.json`) | **VERDICT PASS 65/65**, env_errors=[] |
| Visual gate HARD (run d70fe14) | ~~33 FAIL~~ = D18_row_placement ×10 + D19_header_semantics ×23 — **ĐÃ ĐÓNG bởi dfix 2026-09-08**, xem mục DFIX |
| Visual gate HARD (re-run sau dfix) | **0 FAIL — HARD 0 / 450 record** (5 fixture × 90, exit 0; `summary.json` hard_fail_counts = {}) — chỉ còn 5 candidate D9 adjudicate (ii) |
| Visual gate candidate (re-run sau dfix) | **5 record** — D9 ×5 PLI_M10 `NARROW_COL_WIDE` mọi fixture, adjudicate (ii) pixel-OK total 14400 (không đổi so run trước; D5 ×2 đã allowlist `[f3v2-final]`) |
| Signature census v7 | **PASS** — census 450 = detector 450 (**coverage 100%**), expected-but-zero = 0, manual 440 cluster, min gap **72.9pt** (sàn 72), median 100.5pt, below-72 = **0** |
| ZIP validity | **450/450 testzip OK** (`zip_validity.json` trong corpus) |
| Word open (Microsoft Word 16.16.27) | **90/90 PASS_OPEN_DIRECT** (85 form + M72 ×5 variant), 899.4s — inventory `phase8g_v2/word_open/inventory.json` |
| PNG manifest == đĩa | ok cả 2 run (1737/1737 run 1; 1737/1737 rerun) |
| Determinism (vs `phase8g_v2_rerun`) | **PASS** — 450/450 key `fixture\|tag\|form`, danh sách trang khớp, **sha256(word/document.xml) khớp 450/450** (`phase8g_v2_rerun/determinism_check.json`, so trên đĩa; rerun chạy trọn 5/5 fixture) |

## Các fix của d70fe14 verified trên corpus render thật

- **N-only (47 loop):** D5 BLANK = **0** toàn corpus (không còn hàng trắng); D18 lớp DOCX structural = **0 hit** (0 BLANK_BEFORE_DATA / STT_BREAK; ROW_COUNT_MISMATCH đã bỏ theo owner) — hợp đồng "chỉ N data rows" GIỮ ĐÚNG.
- **Band label removal (23 form, e148d83):** D19 **BAND_LABEL_PRESENT = 0** toàn corpus — nhãn đã xoá sạch, band CHỈ còn tên.
- **Choice tick 1/nhóm (5 nhóm mới):** D15 = **0 FAIL** trên 90 record choice-variants; D12 fixture exclusivity = 0.
- **RFIX M10/M05/M72:** D9 M10 detail **total=14400**, 18 cột đủ (min col 614) 5/5 fixture; M05 = "ngày 04 tháng 05 **năm 2025**" (regex `năm 0d` không thấy); m72_ctcp 5/5 hết fragment "Ghi chú (nếu có)9." và CÓ heading "9. Người đại diện" (20 variant khác không có — đúng đặc thù CTCP).
- **D17 = 0 FAIL** toàn corpus (band↔body mirror đồng bộ, band_input exempt F3B OK); D14 = 0; D13 = 0; D16 = 0.

## HARD 33 — phân tích & adjudication (ĐÃ ĐÓNG bởi dfix 2026-09-08 — giữ làm bằng chứng root cause)

### D18_row_placement ×10 — `PDF_BLANK_GAP` — PLI_M07 (5 fixture) + PLI_M10 (5 fixture)

- Chỉ **lớp PDF bổ trợ** bắn (gap 75.5pt stt_run 2 với M07; 81.1pt stt_run 3 với M10); lớp DOCX authoritative **0 hit**.
- Root cause: heuristic PDF (không đổi ở d70fe14) nhận nhầm **chữ số superscript của khối chú thích pháp lý chân trang** ("1 …", "2 …", "3 …") làm chuỗi STT; gap là khoảng hở tự nhiên giữa "(Ký và ghi họ tên)" và khối chú thích.
- **Bằng chứng render đúng:** trang bị bắn **giống hệt từng byte text** giữa phase8g_v2 và phase8g (corpus trước đã adjudicate cùng lớp): `empty-paper/main/PLI_M07.pdf` p2, `empty-paper/main/PLI_M10.pdf` p2, `valid-full/main/PLI_M07.pdf` p2 — pymupdf `get_text()` equal=True.

### D19_header_semantics ×23 — `BAND_WRONG_KEY` — đúng 23/23 form band-required (100% population, chỉ valid-full)

- **Root cause xác định đúng lần này (khác chẩn đoán corpus trước): FEED MISMATCH dữ liệu, không phải layout.** Batch export gộp data mọi form **last-write-wins** trên key chung: `dn.ten_tieng_viet` do **PLI_M79** ghi cuối ("CÔNG TY TNHH MTV KỸ THUẬT - XÂY DỰNG TRƯỜNG THÀNH 23") → band **và** thân mirror đều render ĐÚNG giá trị merged (D17 PASS 450/450, count>=2). Nhưng D19 được nuôi `data=` fixture **per-form** (vd PLI_M12 "CÔNG TY TNHH SẢN XUẤT THƯƠNG MẠI HOÀNG GIA 7") → containment fail.
- **Bằng chứng render đúng (thử nghiệm mới):** export **PLI_M12 một mình** với fixture per-form → **D19 = 0 hit (PASS)**, giá trị per-form có mặt trong PDF. Structural layer 0 hit; BAND_LABEL_PRESENT = 0 (fix owner giữ vững).
- Kèm theo: chẩn đoán "fragment containment + motto cùng dòng" trong `docs/audits/f3v2_corpus_2026-09-08.json` **không đủ** — Lead nên đọc mục `root_cause_da_xac_dinh_dung` trong JSON của lane này.

**[dfix 2026-09-08 — ĐÃ ĐÓNG]** Hai việc nêu trên cho Lead đã được DETECTOR-FIX thực hiện đúng hướng adjudicate: (a) D18-lớp-PDF loại trừ khối chú thích chân trang khỏi STT-run; (b) D19-lớp-PDF đổi sang hợp đồng so band-vs-thân IN-DOCUMENT (không so fixture per-form) — xem chi tiết diff + mutation + re-run gate ở mục DFIX dưới đây.

## DFIX 2026-09-08 — DETECTOR-FIX: sửa 2 detector heuristic lớp PDF → HARD 0

Scope: CHỈ lớp detector (`tools/row_placement.py`, `tools/header_semantics.py`, mutation suite `tools/test_phase6v_detectors.py`). KHÔNG đụng `app/**`, `form_specs/**`; không fake pass, không bỏ check — hợp đồng structural (authoritative) giữ nguyên.

### Fix 1 — D18 `PDF_BLANK_GAP` ×10 (`tools/row_placement.py` `det_row_placement_pdf`)

- **Cũ (đỏ sai 10 record):** mọi chuỗi dòng số tăng dần bắt đầu "1" ở lề trái (≥2 dòng) đều bị coi là STT-run → đo gap dọc phía trên. Chuỗi superscript marker chú thích pháp lý chân trang ("1 Nếu cột số 5…", "2 Ghi giá trị…", "3 Loại tài sản…") thoả shape này → gap tự nhiên 75.5pt (M07, stt_run 2) / 81.1pt (M10, stt_run 3) giữa "(Ký và ghi họ tên)" và khối footnote bị đọc là "khoảng trống trên STT=1".
- **Mới (2 guard, generic — không hard-code form):**
  1. **FOOTNOTE GUARD** — dòng số 1-2 chữ số mà dòng kề dưới (kề nhau, Δy < 2×line-height) bắt đầu CÙNG lề x0 (±3pt) bằng từ KHÔNG thuần số = prose footnote wrap cùng margin → cả chuỗi là footnote, không phải bảng. Hàng STT thật không có shape này (dòng dưới là số STT kế hoặc cách quãng).
  2. **HEADER ANCHOR** — chuỗi chỉ được đo gap khi có dòng chữ "STT" PHÍA TRÊN cùng x-range (|Δx0| ≤ 20pt = "số nằm CÙNG bảng với header STT"); không có anchor = không xác định được → bỏ qua (NOTE-level, KHÔNG HARD).
- Bảo đảm không cụt chân true-positive: mutation giữ case bảng STT thật kẽ hở 70pt sau header → vẫn ĐỎ `PDF_BLANK_GAP`; DOCX structural (authoritative, 0 hit toàn corpus) không đổi.
- Kèm sync smoke trong module: expectation "K+N defect RED" còn đòi `ROW_COUNT_MISMATCH` (code owner đã BỎ tại d70fe14, fail từ trước tại HEAD 577670d — pre-existing) → sửa thành pin `BLANK_BEFORE_DATA` (defect vẫn RED).

### Fix 2 — D19 `BAND_WRONG_KEY` ×23 (`tools/header_semantics.py` `det_pdf`)

- **Cũ (đỏ sai 23 record):** `band_ok` yêu cầu giá trị canonical trong `data` (fixture **per-form**) phải xuất hiện trong mảnh band; batch export gộp 86 form/1 payload → `dn.ten_tieng_viet` last-write-wins (PLI_M79 ghi cuối) → band VÀ thân cùng render giá trị **merged** ≠ fixture per-form → containment fail → `BAND_WRONG_KEY` trên 100% form band-required. D17 (so thuần in-document) PASS 450/450 cùng corpus — mâu thuẫn trực tiếp.
- **Mới (hợp đồng IN-DOCUMENT, khớp D17):** giá trị band đọc từ CHÍNH tài liệu (mảnh band sau khi lọc motto/dòng kẻ), so với THÂN cùng PDF: mirror — BẤT KỲ mảnh band nào được thân lặp lại (count ≥ 2) là PASS; band_input — mỗi mảnh ĐÚNG 1 lần (≥2 → `DUPLICATE_EDITABLE`, 0 → `BAND_VALUE_OR_SLOT_MISSING`). Tham số `data` KHÔNG còn tham chiếu pass/fail — chỉ dùng CHẨN ĐOÁN code khi band/thân lệch (mảnh khớp canonical → `STALE_MIRROR`; không → `BAND_WRONG_KEY`).
- Không fake pass: mọi mutation ĐỎ cũ của V4e giữ nguyên code lỗi (STALE_MIRROR / BAND_WRONG_KEY / DUPLICATE_EDITABLE / SLOT_MISSING đều vẫn bị bắt thuần in-document, không cần data).

### Verification

| Check | Kết quả |
|---|---|
| Mutation suite `python3 -X utf8 -m tools.test_phase6v_detectors` | **22/22 PASS** (20 cũ + 2 case mới: `V3b2_d18_pdf_footnote_marker_guard`, `V4e2_d19_pdf_in_document_feed` — pin cả 2 shape footnote thật M07/M10 + worst case footnote DƯỚI bảng STT cùng x-range + feed merged batch) |
| Smoke `python3 -X utf8 -m tools.row_placement` | ALL PASS (7/7) |
| Sweep structural `python3 -X utf8 tools/header_semantics.py` | 87 form: 0 hit, 0 thiếu role |
| E2E fixture `python3 -X utf8 -m tools.test_f3h_fixtures` | 5/5 PASS (M31/M72/M32 mirror A→B) |
| Quét D18-PDF toàn corpus phase8g_v2 (450 doc × mọi trang, RGlob PDF) | **0 hit** (trước: 10) |
| D19 `det_record` pdf_checks=True trên 90 record valid-full | **0 hit** (trước: 23) |
| **Re-run FULL gate** `python3 -X utf8 tools/phase5_visual_gate.py --outdir generated_ho_so/_visual_layout/phase8g_v2 --forms <86 active id>` | **HARD-FAIL: 0** — 5 fixture × 90 record: 0 FAIL mỗi fixture (444.6/435.3/397.0/414.6/396.8s); exit 0; export_errors 0; **PNG 1737/1737 ok**; candidate còn **5** = D9 ×5 PLI_M10 (adjudicate (ii) pixel-OK, không đổi) |

Render corpus KHÔNG thay đổi (chỉ lớp detector): 450 record / 1737 PNG giữ nguyên; ZIP/Word/determinism đã PASS ở run d70fe14 trên cùng nội dung render nên không cần chạy lại.

## Adjudication 7 candidate (run 1) — zero unresolved

1. **D9 ×5 — PLI_M10 `NARROW_COL_WIDE` mọi fixture — (ii) pixel-OK:** total **14400** đúng, 18 cột đủ, min col 614 (override per-form 500), không mất cột 18, không glyph dính — cùng lớp adjudicate corpus phase8g/[f3]. Muốn hết vĩnh viễn cần nới policy D9 cho form override per-form (Lead quyết).
2. **D5 ×2 — allowlist +2 entry `[f3v2-final]`** (`docs/phase6v_d5_sparse_allowlist.json`, 75 → **77**; (i) 62, (ii) 15; KHÔNG nới HARD):
   - `empty-paper/m72_dhdn/PLI_M72` p2 (2/2): mục "8. Nơi đăng ký: (Cơ quan đăng ký kinh doanh cấp tỉnh)" — section pháp lý cuối M72, cùng lớp 2 entry m72_dhdn cũ (pagination dời sau N-only).
   - `long-boundary/main/PLII_M01` p3 (3/14): dòng mục "5.3. Tổng số lao động (dự kiến): 269" — long-boundary đẩy section sang trang kế, giá trị nguyên vẹn.

## Rủi ro / còn mở cho Lead

1. ~~Gate verdict = FAIL 33 HARD~~ **ĐÃ ĐÓNG — HARD 0 sau dfix 2026-09-08** (mutation 22/22, re-run gate exit 0).
2. ~~Chẩn đoán D19 cũ (fragment containment) không đủ~~ **ĐÃ XỬ LÝ** — detector chuyển hợp đồng in-document đúng nguyên nhân feed merged; giữ lại ghi chú lịch sử ở mục HARD 33 trên làm bằng chứng adjudicate.
3. D9 ×5 M10 còn candidate (allowlist chỉ D5) — adjudicated (ii); fix vĩnh viễn thuộc policy D9.
4. PNG tổng 1737 (−17) do pagination dời sau N-only — không mất nội dung (ZIP/Word/determinism PASS đủ).
5. Gate default `--forms all` vẫn chưa lọc `current_law_status` — lần này truyền `--forms` 86 id thủ công (rủi ro cũ giữ nguyên).
6. [dfix] D18-PDF guard "không có anchor STT → bỏ qua" nghĩa là lớp PDF bổ trợ chỉ fire khi trang có header 'STT' cùng x-range phía trên chuỗi số — chấp nhận được vì DOCX structural là lớp authoritative (0 hit toàn corpus); `PDF_STT_ANCHOR_DX=20pt` và predicate footnote (Δx0 ≤3pt, kề nhau <2×line-height, token sau marker không thuần số) là hằng heuristic mới, chưa đo phân bố rộng ngoài corpus hiện có.

## artefacts tham chiếu

- Run 1: `phase8g_v2/{manifest.json, summary.json, v7_signature_census.json, zip_validity.json, word_open/inventory.json}`
- Rerun: `phase8g_v2_rerun/{manifest.json, summary.json, determinism_check.json}`
- Preflight JSON: `/tmp/f3v2_final_preflight.json`; log gate: `/tmp/f3v2_final_gate.log`, `/tmp/f3v2_final_rerun.log`; log Word: `/tmp/f3v2_final_wordopen.log`
- Allowlist: `docs/phase6v_d5_sparse_allowlist.json` (77 entry, +2 `[f3v2-final]`)
- [dfix 2026-09-08] Re-run gate sau fix detector (cùng outdir, nội dung render không đổi): log `/tmp/dfix_gate_run.log`; `summary.json` hard_fail_counts={} candidate D9 ×5; manifest 450 record/PNG 1737 ok
