# PHASE10-CONTACT — CORPUS W1 TỪ HEAD `d7ec076` + SWEEP NHÃN EMAIL/WEBSITE (2026-09-10)

> Phạm vi: wave W1 của `PLAN_hoan_thien_pfat_hanh.md` — render lại corpus từ
> HEAD sau khi render layer thêm `_keep_contact_label_with_value` (commit
> `d7ec076`, defect EML-001/WEB-001 của owner) + quét toàn bộ template có nhãn
> `Thư điện tử`/`Website`. Corpus v2 `phase9_bandfix_v2` coi là STALE cho
> HEAD này vì render layer đã đổi.
> Lane thực thi: agent W1 (read production, worktree riêng khi render);
> Lead review + commit. Không push trong phiên (chờ lệnh owner theo PLAN.md —
> lệnh push từng wave do owner phát trực tiếp).

## 1. Census + sweep nhãn contact (EML-001/WEB-001)

- **Census:** **67/86 form active có nhãn, 173 occurrence**
  (`Thư điện tử|Website` × biến thể `(nếu có)`/không ngoặc) trong
  `word/document.xml` — headers/footers 0 hit. Mọi occurrence đều có `{key}`
  giá trị theo sau: `email_tru_so` 60, `website` 61, `email_khac` 49,
  `ndd.email` 3. Suite pin con số DERIVED này — đổi template phải cập nhật pin
  có chủ đích.
- **Sweep: PASS 67/67 form** (+ PLI_M72 đủ 5 variant theo pipeline corpus).
  Hai lớp kiểm chứng độc lập, đi qua đúng đường production `Bridge.export`
  (LO normalize + PDF):
  1. DOCX trên đĩa: **0/173 occurrence thiếu NBSP** (`:\u00a0`) sau dấu `:`
     của nhãn — NBSP sống sót qua LO normalize;
  2. PDF hình học (text-layer): **173/173 hàng nhãn có giá trị bắt đầu cùng
     hàng** — nhãn không bị bỏ lại cuối dòng trước.
- **Suite:** `tools/test_contact_label_corpus.py` — 6/6 OK, exit 0.
- Evidence: `generated_ho_so/_visual_layout/phase10_contact/_sweep/`
  (72 render unit, gitignored).

## 2. Corpus v3 — `generated_ho_so/_visual_layout/phase10_contact/`

| Hạng mục | Kết quả |
|---|---|
| Record | **450** (86 form active − PLI_M11 removed; PLI_M72 ×5 variant = 90 render-unit × 5 fixture) |
| HARD-FAIL | **0**; export error 0 |
| Candidate | **7 — adjudicate đủ**: D9 `NARROW_COL_WIDE` PLI_M10 ×5 (lớp (ii) pixel-OK đã adjudicate từ phase8g; min col nay 625 ≥ 614/624 trước đây); D5 SPARSE PLI_M45 p2 ×2 (valid-full, choice-variants — 108 chars, chỉ cụm ký) → allowlist +2 entry lớp (i), prune 1 entry stale (empty-paper/main/PLI_M45 p2 — M45 empty-paper nay 1 trang sau fix A-8). Sau adjudicate: candidate unresolved = 0 |
| PNG == đĩa | 1717/1717 ok |
| ZIP | testzip 37/37 OK |
| Determinism | render ×2: sha256 `word/document.xml` khớp **450/450**; PNG list 1717/1717 (run 2 tại `phase10_contact_rerun/`; snapshots `_qa_contact/_determinism_det_run{1,2}.json`, `_corpus_v3_evidence.json`) |
| Pagination delta vs v2 | so từng PDF 450/450 — **đúng 1 record đổi** (empty-paper/main/PLI_M45 2→1 trang = fix A-8); 449 record còn lại nguyên page-count |
| Contact sheet | 450/450 tại `_qa_contact/<fixture>/<tag>__<form>.png` |
| Human review | **NOT_REVIEWED** (O5) — AI/contact-sheet chỉ sàng lọc; chờ reviewer người thật ký verdict |

Lệnh tái lập: `python3 -X utf8 tools/phase5_visual_gate.py --outdir
generated_ho_so/_visual_layout/phase10_contact` (inventory động: log run thật
`active=86 skipped=1 m72_variants=5 render_units_per_fixture=90`).

## 3. Fix kèm theo wave này

- **A-8 P1.1(a) — PLI_M45/M53 cụm ký mồ côi trang 2** (P1 còn mở từ phase9):
  render pass mới `_trim_trailing_sig_before` — registry-gated
  (`tools/phase5r_expectations.json` `signature.trailing_before_trim`, chỉ
  PLI_M45/M53), whitespace-only: zero `w:before` cụm ký cuối body + xoá para
  rỗng kề trước khối nội dung cuối. Chạy SAU `_ensure_signature_space` để
  không bị pass (a) chèn ngược; idempotent. Kết quả: M45 empty-paper về
  **1 trang**; M45 valid-minimal/valid-full/choice p2 còn cụm ký (108 chars →
  allowlist (i)); **M53 vẫn 2 trang** (thiếu ~1–3pt, cận biên đúng audit dự
  đoán) → phần dư thuộc phương án (c) P1.2 A4 geometry, **chờ owner**.
  Test: `tools/test_a8_trailing_sig_trim.py` 11/11 OK (unit byte-identical/
  idempotent/điều kiện chặt + render thật + control PLI_M47 + pin exact-set
  registry). `test_docx_layout_signatures` T1 được exemption có chủ đích
  (sp==0 chỉ sinh từ trim; hợp đồng riêng nằm ở suite A-8).
- **F7-N3:** `tools/census/table_coverage_audit.py` `--no-write` in
  `no-write: KHÔNG ghi …` thay vì `wrote …` vô điều kiện (log trung thực).
- **F7-N5:** tách `resolve_form_inventory()` trong `tools/phase5_visual_gate.py`
  (hành vi lọc current-law đã có từ `85a8b5b` — sau thời điểm F7 audit chạy;
  lane chỉ tách hàm testable + pin). Suite `tools/test_f7_notes.py` 5/5 OK.

## 4. Còn mở

- Human visual sign-off corpus v3 (O5) — NOT_REVIEWED, không tự ghi PASS.
- M53 + A4 geometry (P1.2) — quyết định owner.
- Word open-direct cho corpus v3: evidence cũ 90/90 là của v2; v3 chờ chạy
  Word loop lần tới khi máy có Word (16.16.27 có sẵn trên máy dev — chạy lại
  `word_open` inventory trước khi F5).

## 5. Ghi nhận ngoài lane

- `test_docx_layout_signatures` T0 fail `PLI_M07/body sp=0 blanks=0` là
  **pre-existing tại HEAD `d7ec076`** (suite ngoài runner; tái hiện trên
  worktree sạch) — không phải hệ quả của A-8; theo dõi ở defect registry.
