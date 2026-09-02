# PLAN — Wave D2 hoàn tất lỗi + Audit chuyên trách + P5R (bản vận hành chi tiết)

> **Lưu ý 2026-08-29:** tài liệu này giữ lại brief/worktree recipe lịch sử.
> Trạng thái, thứ tự gate và phạm vi hiện hành đã được thay bằng `PLAN.md` v4
> tại `main@6ae63c2`. Không chạy D2-A/C từ checkpoint `34b95a9` nguyên xi.
> Việc đầu tiên hiện tại là PLAN v4 Wave A (gỡ hai verifier PLII_M02) rồi Wave B
> (coverage matrix 111/111); chỉ sau đó mới tái sử dụng brief worker phù hợp từ
> tài liệu này.

> **Bản kế hoạch duy nhất cho phần còn lại**, do lệnh owner 2026-08-28:
> "viết PLAN hoàn chỉnh phần lỗi còn lại và phase tìm lỗi nữa… PLAN phải chi
> tiết, chỉn chu, có hướng dẫn tạo worktree và cho worker làm. Sau đó có
> audit lỗi xem có làm chuẩn không (**phải có worker chuyên audit**) rồi chạy
> P5R + kiểm tra các lỗi đã sửa."
>
> Trạng thái mở wave: HEAD `34b95a9` · runner 41/5 (3-4 clause pin cuối, đúng
> nguyên nhân) · sổ lỗi `docs/defect_registry.md` (9 Class) · 3 lane
> hdr2col/cap-von/m09-rebuild đã MERGE.
> PLAN.md mục P5R (10 gate G1–G10) là đích; tài liệu này là **kế hoạch đội
> hình + trình tự** để tới được đích.

---

## 0. Nguyên tắc bất biến (áp dụng mọi phase — trích PLAN mục 6/7)

1. **Lead giữ main** — là người duy nhất regen global artifact (build_form_maps
   → tag_m72_sections → docx_to_blocks → census), merge `--no-ff` tuần tự,
   cân allowlist.
2. **Tối đa 3 lane worktree song song**, không chồng file; `form-domain.js`,
   `app.js`, `docx_to_blocks.py`, `docx_render.py` mỗi thời điểm chỉ một
   chủ thể sở hữu.
3. **Worker KHÔNG**: regen global, merge, push, chạy release_runner, sửa file
   ngoài ownership, nới test. Worker CÓ: sandbox regen (redirect
   `bfm.OUT_TPL/OUT_DATA`), commit nhỏ trên branch riêng, báo cáo đúng format.
4. **Cấm sửa tay generated** (`app/templates/**`, `app/data/blocks/**`,
   `form_maps`, manifest) — mọi thay đổi qua spec/capability → Lead regen.
5. **Allowlist exact-set cân TẠI COMMIT** (H7 đọc diff đã commit; tree bẩn =
   đỏ ảo — tiền lệ nhiều lần trong session).
6. **Visual re-shoot BẮT BUỘC sau mọi regen** (UI snapshot + DOCX→Word→PDF).
7. **KHÔNG nới test** — sync pin chỉ theo bằng chứng sản phẩm mới + ghi lý do
   trong commit message. Suite KHÔNG BAO GIỜ pipe qua `| tail` khi quyết định
   commit (pipe nuốt exit code — sai lầm đã lặp 2 lần trong session).
8. Bài học verify pháp lý: TT 121/2026/TT-BTC (hiệu lực 21/8/2026) thay
   Mẫu PL I **1,2,3,4,5,10,12,27,30** + **bãi bỏ Mẫu 11** — mọi đối chiếu nội
   dung dùng bản hiện hành; PDF gốc đã tải ở `/tmp/tt121.pdf` (70 trang,
   scan — đọc bằng render trang ra PNG).

---

## 1. Danh mục lỗi còn lại (INPUT của wave — nguồn: defect_registry)

| # | Class | Phạm vi | Gốc rễ đã biết | Sửa ở phase |
|---|---|---|---|---|
| 1 | **Pin đỏ cuối** — p1_c (thiếu attribute bảng nganh_bo_sung sau exempt content-based), industry_household (region clause thiếu skip content-based), H7 (cân allowlist) | 3-4 clause | patch dở của Lead @ 34b95a9 | **D2-A** |
| 2 | **Class 9** — bảng ngành: ô Tên ngành `undefined`, Mã ngành tự có `6`, ○ thay □ (PLI_M03, ảnh owner 14:13) | mọi mẫu có ds_nganh (5 mẫu formation + PLII) | draft đĩa sạch → lỗi tầng binding/phiên (app.js/form-domain/render) | **D2-C lane W3** |
| 3 | **Class 3** — GLUE chữ số chú thích dính chữ ("xã hội7:") | 23/87 mẫu (census `numbering_audit`) | extractor L1 chưa tách superscript footnote | **D2-C lane W1** |
| 4 | **Class 7** — chữ ký không có chỗ trống để ký | các mẫu có role `signature` | không rule khoảng trống dọc | **D2-C lane W2** |
| 5 | **Class 8** — dấu X rơi riêng dòng ("Khấu trừ"/"X"; "Có X"/"Không X" tách hàng) | các mẫu checkbox chọn-1 | nhãn và {chk_*} khác paragraph trong template | **D2-C lane W2** |
| 6 | **Class 6** — số mồ côi PDF (bảng thuế dẹt PLII_M03–M06) | nhóm tạm ngừng/chấm dứt HKD | bảng thuế chưa rebuild — **ngoài phạm vi đã duyệt, CHỜ OWNER** | D2-C lane W4 *(chỉ mở khi owner gật)* |
| 7 | **Lỗi CHƯA BIẾT** — sẽ lộ ra ở phase điều tra (owner: "đa số biểu mẫu đều vậy") | toàn bộ 87 | — | **D2-B → D2-C** |
| 8 | Mẫu PLI_M10 theo TT 121 (18 cột, bỏ "Quyền chi phối" — D2.5=A lỗi thời) · PLI_M11 bị bãi bỏ · đuôi mục 7-11 M03/M04/M05 | 3+ mẫu | TT 121 thay biểu mẫu | **CHỜ OWNER** (packet riêng) |

---

## 2. Phase D2-A — Gỡ nốt pin đỏ (Lead, trên main, KHÔNG lane)

Mục tiêu: runner **46/0/0** trở lại để mọi phase sau có sàn sạch.

| # | Việc | Chi tiết chỉn chu |
|---|---|---|
| 1 | `tools/census/p1_c_verify_plii_m02.py` | Clause đếm bảng→vùng đang miss `nganh_bo_sung`: sau patch exempt content-based, bảng đầu vùng A bị loại nhầm hoặc span sai. Debug bằng dump `seq` + `spans` cho PLII_M02; đảm bảo 4 bảng ngành attribute đủ, riêng band (tên hộ) + bảng thuế (`Chỉ tiêu`) được exempt THEO NỘI DUNG ô đầu. |
| 2 | `tools/test_industry_household.py` | Region clause `t_m02_working_template_regions` đang thiếu khối skip (patch cũ bị remove, patch mới assert không khớp — file ở trạng thái nửa vải): thay vòng đếm bằng duyệt `body_tables(doc)` + skip ô đầu `ten ho kinh doanh/ten doanh nghiep/chi tieu` (đồng bộ p1_c). |
| 3 | `tools/audit_expected_diff_files.txt` | Cân exact-set: +mọi file thay đổi chưa có entry (kiểm bằng `git diff --name-only HEAD..working` sau các commit pin-sync). |
| 4 | Gate | `python3 -X utf8 -m tools.release_runner` → **46/0/0 VERDICT PASS**, chạy KHÔNG pipe; `git status` sạch; commit chuẩn "sync-pin: …(lý do)". |

---

## 3. Phase D2-B — WORKER ĐIỀU TRA (1 agent, read-only, KHÔNG cần worktree)

> Cơ sở: lệnh owner "phải 1 worker điều tra rồi sau đó 1 worker sửa". Worker
> này là **auditor read-only** theo SOP 6.2 — chỉ được ghi vào
> `generated_ho_so/_visual_layout/d2_invest/` (gitignored) + `/tmp`.

**Brief 5 mục (copy cho agent):**

1. **BASE/điểm xuất phát:** HEAD main sau D2-A (ghi số commit lúc spawn).
   KHÔNG đụng production, KHÔNG commit gì cả.
2. **File ownership (ghi được):** chỉ `generated_ho_so/_visual_layout/d2_invest/**`
   + script tạm `/tmp/d2_invest_*.py|sh`.
3. **Forbidden:** mọi file tracked; KHÔNG chạy release_runner; KHÔNG regen;
   KHÔNG commit.
4. **Nhiệm vụ (checklist cố định per-mẫu, 87/87 — KHÔNG sampling):**
   - B1. Render DOCX mẫu có data mồi (`tools.docx_render.write_rendered` +
     `dummy_data_from_map`) → PDF bằng **Microsoft Word** qua osascript,
     **chia lô ≤10 file/phiên Word** (bài học: lô 22 bị đứt 6/16) → PNG trang
     1 + các trang có bảng (Quartz render, như `/tmp/tt121_pages` đã làm).
   - B2. Soi từng PDF/blocks theo checklist: (a) số mồ côi đứng riêng dòng;
     (b) GLUE chữ-số (`[a-z]\d{1,2}:`); (c) dấu X lệch dòng; (d) vùng ký có
     ≥2 dòng trống chưa; (e) 22 mẫu band: tên trái/quốc hiệu phải, không
     viền; (f) bảng mất viền/sai số cột vs manifest; (g) marker `{..}` sót;
     (h) dãy mục nhảy (chạy sẵn `tools.census.numbering_audit`); (i) so
     nguyên văn 3 câu đầu + các heading vs bản scan TT 121 (`/tmp/tt121_pages`)
     cho 9 mẫu bị thay.
   - B3. Ghi `inventory.json`: `{form_id: {checks: {a..i: PASS|FAIL}, evidence:
     [png], note}}` + biên bản tổng hợp theo CLASS (mỗi FAIL gán vào Class cũ
     hoặc đề xuất Class mới).
5. **Báo cáo:** INV_FORMS=87 · INVENTORY path · số FAIL per class · top-5 lỗi
   nặng nhất · FINDINGS (điều bất ngờ) · NOTES. KHÔNG tự chấm "đã sửa".

**Đầu ra của phase:** inventory.json + bảng lỗi mới → Lead review → cập nhật
`docs/defect_registry.md` (commit docs) → cấp việc cho D2-C.

---

## 4. Phase D2-C — WORKER SỬA (tối đa 3 lane worktree song song)

### 4.0 Lệnh tạo worktree (chạy từ ROOT main, copy-paste)

```bash
BASE=$(git rev-parse HEAD)   # = HEAD sau D2-A
mkdir -p ../dangky_kinhdoanh-worktrees
git worktree add ../dangky_kinhdoanh-worktrees/fix-industry -b agent/fix-industry $BASE
git worktree add ../dangky_kinhdoanh-worktrees/fix-render-docx -b agent/fix-render-docx $BASE
git worktree add ../dangky_kinhdoanh-worktrees/fix-extractor -b agent/fix-extractor $BASE
git worktree list
```
(Worker cd vào worktree của mình; KHÔNG đụng repo chính; KHÔNG push/merge.)

### 4.1 Lane W3 — `fix-industry` (Class 9 — ƯU TIÊN CAO NHẤT, lỗi thao tác khách)

| Mục | Nội dung |
|---|---|
| **File ownership** | `app_web/ui/app.js` HOẶC `app_web/ui/form-domain.js`/`render.js` (chỉ định sau khi điều tra đúng chỗ — nếu lỗi nằm ở 2 file thì lane này giữ cả cụm `app.js`+`form-domain.js`, lane W2 chỉ còn `docx_render`+`render.js`+`style.css`), + test mới `app_web/test_industry_input_negative.js` |
| **Forbidden** | `tools/**` (generator), `app/templates/**`, `app/data/**`, `docx_render.py`, `release_runner.py`, allowlist |
| **Việc** | (1) Tái hiện `undefined`/`6` bằng test DOM (đỏ trước); (2) sửa binding/store ghép chuỗi; (3) test xanh; (4) rà các ô khác có cùng pattern (`String(x)+undefined`) |
| **Test gate** | suite mới xanh + `test_dom` 58/0 + `test_grid` 111/0 + `test_form_flow` 38/0 + `test_p3_e2e` 38/0 giữ nguyên |
| **Báo cáo** | LANE/BASE/HEAD/DIFF/TESTS/FINDINGS/NOTES |

### 4.2 Lane W2 — `fix-render-docx` (Class 7 + 8)

| Mục | Nội dung |
|---|---|
| **File ownership** | `tools/docx_render.py`, `app_web/ui/render.js`, `app_web/ui/style.css`, test mới `tools/test_signature_space.py` (hoặc JS tương đương) |
| **Forbidden** | `docx_to_blocks.py`, `build_form_maps.py`, templates/blocks, `app.js`/`form-domain.js` (của W3), release_runner, allowlist |
| **Việc** | (1) Class 7: block role `signature` render/EXPORT có ≥2 dòng trống trước chữ ký (theo bản gốc Word — đối chiếu nguồn 06_/01_mau_ho_kinh_doanh); (2) Class 8: nhãn + ô {chk_*} về CÙNG dòng khi xuất ("Có X  Không X"; "Khấu trừ X") — sửa ở lớp render/ghi DOCX hoặc đề xuất spec gộp paragraph (nếu phải đụng template = ghi FINDINGS cho Lead, KHÔNG tự sửa); (3) test đỏ-trước-xanh-sau cho từng Class |
| **Test gate** | suite mới xanh + `test_acceptance_docx` + `test_m72_conditional_export` + `docx_render --test-all` 87/87 |
| **Báo cáo** | như trên |

### 4.3 Lane W1 — `fix-extractor` (Class 3 GLUE — regen lớn nhất, chạy CUỐI)

| Mục | Nội dung |
|---|---|
| **File ownership** | `tools/docx_to_blocks.py`, test mới `tools/test_footnote_glue.py`; ( Lead sẽ tự sửa `tools/layout_roles.py`/overrides nếu cần — báo FINDINGS) |
| **Forbidden** | mọi thứ khác; templates/blocks (Lead regen); `render.js`/`docx_render.py` (của W2) |
| **Việc** | Rule V3: run/paragraph superscript-only hoặc digit-only **không phải nội dung** → tách thành footnote/gắn `vertAlign`, không dính vào chữ ("xã hội7:" → "xã hội" + chú thích 7); giữ nguyên mọi trường hợp chân số là NỘI DUNG thật (vd "Mã số dự án 6") — tự viết negative test phân biệt; sandbox-only verify (23 mẫu census GLUE về 0) |
| **Test gate** | suite mới xanh + `test_layout_l1_extractor` 55 + `numbering_audit` GLUE=0 (sandbox) + `test_generator_deep_idempotency` 17/0 |
| **Báo cáo** | như trên + liệt kê 23 mẫu sẽ đổi blocks (Lead chuẩn bị regen/allowlist) |

### 4.4 Phân vai đối với Class 6 (chờ owner)
Owner gật → mở lane W4 `fix-tax-plii` (form_specs PLII_M03/M04/M05/M06 mục
thuế theo Phụ lục II TT 68 — PL II KHÔNG bị TT 121 đụng) thay thế 1 lane
đang rảnh; KHÔNG mở trước khi có lệnh.

---

## 5. Phase D2-D — LEAD merge + regen + verify (tuần tự, SOP 6.3)

Trình tự khuyến nghị (W1 regen toàn cục nên để CUỐI):

```
W3 (fix-industry) → W2 (fix-render-docx) → W1 (fix-extractor)
```

Sau MỖI merge, Lead thực hiện **đủ 8 bước** (không bỏ bước):
1. `git merge --no-ff agent/<lane>` (message ghi evidence lane)
2. Targeted battery của lane + các suite chạm file đó
3. Regen nếu lane đổi spec/extractor: pipeline đầy đủ **×2 zero-diff**,
   so member-level docx (tiền lệ P0: restore template noise)
4. Census recount (`build_manifest --deep --write`) + `numbering_audit` +
   census glyph □/☐ = 0
5. Allowlist exact-set cân TẠI COMMIT (+entry có chú thích)
6. Visual re-shoot các mẫu ảnh hưởng (UI Playwright + DOCX→Word→PDF,
   lô ≤10/phiên Word) → `generated_ho_so/_visual_layout/<phase>/`
7. Full `tools.release_runner` **không pipe** → 0 FAIL
8. Commit + cập nhật ledger

---

## 6. Phase D2-E — WORKER AUDIT CHUYÊN TRÁCH (bắt buộc theo lệnh owner)

> Worker MỚI, read-only, **KHÔNG được là agent đã sửa** (tách biệt người sửa
> — người chấm). Không cần worktree (chỉ đọc main + ghi evidence gitignored).

**Brief 5 mục:**

1. **BASE:** HEAD sau D2-D (ghi commit). Đọc đầu vào: `docs/defect_registry.md`,
   `docs/plan_wave_D2_P5R.md`, `docs/execution_ledger.md` wave mới, git log
   `BASE_D2A..HEAD`.
2. **Ghi được:** `generated_ho_so/_visual_layout/d2_audit/**` +
   `docs/audit_d2_report.md` (bản nháp — Lead review rồi commit).
3. **Forbidden:** sửa code/test/spec/generated; chạy release_runner; merge.
4. **Nhiệm vụ chấm 3 tầng:**
   - **Tầng A — lỗi có thật sự được sửa?** Với MỖI Class 1–9 (và lỗi mới từ
     D2-B): mở evidence (PDF/PNG/blocks/census) tự kiểm, KHÔNG tin lời khai
     trong commit. Verdict per-Class: `PASS / PARTIAL / FAIL` + link evidence.
   - **Tầng B — có làm CHUẨN không (quy trình)?** Diff-review từng commit:
     fix có qua spec (không sửa tay generated)? pin sync có lý do + bằng
     chứng (không nới mù)? allowlist cân tại commit? visual re-shoot có đủ?
     worktree/lane có vi phạm ownership?
   - **Tầng C — chạy lại công cụ độc lập:** `numbering_audit` (0 JUMP, GLUE
     xu hướng giảm về 0), census glyph = 0, `build_manifest --deep` GATE,
     spot-check ngẫu nhiên 10/87 PDF (mở bằng mắt, so bản gốc).
5. **Báo cáo:** bảng verdict per-Class + per-gate; danh sách tồn đọng; câu
   CHỜ OWNER còn lại; kết luận "ĐỦ ĐIỀU KIỆN VÀO P5R / CHƯA (lý do)".

**Gate vào P5R:** audit Tầng A không còn FAIL nào thuộc phạm vi đã duyệt;
Tầng B không phát hiện vi phạm quy trình chưa được phân loại.

---

## 7. Phase D2-F — CHẠY P5R (10 gate, PLAN.md mục P5R) + kiểm tra hồi quy

Thực hiện đúng `PLAN.md` P5R, có bổ sung ma trận hồi quy lỗi:

| Bước | Việc | Chủ trì |
|---|---|---|
| F1 | Gate máy chạy được: G2 (`numbering_audit --gate`, EXCEPTIONS phải RỖNG), G3 (glyph=0), G4 (GLUE=0 + marker=0), G10 (runner 0 FAIL + allowlist + `git diff --check`) | Lead |
| F2 | Gate nội dung: G1 (87/87 vs bản hiện hành TT 121 — dùng inventory D2-B), G5 (header 22 mẫu), G6 (4 kind + round-trip), G7 (export DOCX/ZIP 87/87 qua Word), G8 (luồng Excel end-to-end) | Lead chuẩn bị → **audit worker D2-E chấm** |
| F3 | Gate a11y/viewport G9 (không hồi quy so với P3: 36/0 + 3 viewport) | Lead |
| F4 | **Ma trận hồi quy 9 Class** — mỗi Class 1 dòng bằng chứng xanh (census/PDF/audit) — bất kỳ FAIL → quay lại phase sở hữu, KHÔNG band-aid | Audit worker |
| F5 | Tổng kết: 10/10 gate + 9/9 Class hồi quy XANH → ghi sẵn điều kiện mở **P6 đóng gói** | Lead + Owner |

---

## 8. Bảng phân công tóm tắt

| Phase | Ai | Worktree | Gate ra |
|---|---|---|---|
| D2-A gỡ pin đỏ | **Lead** (main) | — | runner 46/0/0 |
| D2-B điều tra 87 mẫu | Worker điều tra (read-only) | không cần | inventory.json + registry cập nhật |
| D2-C sửa | W3 industry · W2 render/docx · W1 extractor (+W4 nếu owner mở) | 3 worktree | suite riêng xanh + regression giữ |
| D2-D merge/regen | **Lead** | main | 8 bước/merge, runner 0 FAIL |
| D2-E audit chuyên trách | **Worker audit MỚI** (read-only) | không cần | audit_d2_report verdict |
| D2-F P5R + hồi quy | Lead chuẩn bị + audit chấm | main | 10/10 gate + 9/9 Class |

---

## 9. Câu hỏi CHỜ OWNER (không tự mở)

1. **Mở phạm vi PLII_M03–M06** (tạm ngừng/chấm dứt HKD): rebuild bảng thuế —
   sửa Class 6 từ gốc? (Y/N)
2. **PLI_M10** rebuild theo Mẫu 10 TT 121 (18 cột, bỏ "Quyền chi phối" — làm
   mất quyết định D2.5=A cũ)? (Y/N)
3. **PLI_M11** đã bị bãi bỏ — gỡ khỏi pipeline/app hay giữ chờ hướng dẫn? (Y/N)
4. **Đuôi mục 7–11 của M03/M04/M05** (thành viên/thuế/BHXH/CSHHL bị cắt):
   cho mở capability chèn section theo TT 121 (giống cách đã làm mục 7 M09)? (Y/N)

---

## 10. Tiêu chuẩn "XONG" của cả wave

- Runner **46+/0 FAIL** · census GATE 87/87 · numbering GLUE/JUMP/CHAIN = 0
  (EXCEPTIONS rỗng) · glyph □/☐ dẹt = 0
- `docs/audit_d2_report.md`: mọi Class verdict PASS (PARTIAL phải có lý do +
  owner chấp nhận)
- P5R 10/10 gate XANH + ma trận hồi quy 9/9
- Tree sạch, docs (ledger/registry/PLAN) đồng bộ — lúc đó mới mở **P6 đóng gói**
