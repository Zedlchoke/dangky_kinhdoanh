# v4-visual-audit — auditor/6v-visual (độc lập)

- **Ngày:** 2026-09-05
- **Base:** `be6bdbf` (main), worktree audit: `dangky_kinhdoanh-worktrees/6v-audit-visual` (nhánh `6v-audit-visual`)
- **Phạm vi nhiệm vụ (3 phần):** (1) adjudicate 72 hit D5_blank_sparse; (2) adjudicate micro-census 7 nhóm; (3) spot-check thị giác 15 trang ngẫu nhiên theo checklist PLAN mục 5.1.
- **Đầu vào:**
  - Corpus: `generated_ho_so/_visual_layout/phase6v/v4_corpuscheck/` — 455 record; PNG trên đĩa đếm được **1612 = 1612 manifest** (đếm lại bằng `find … -name "page-*.png" | wc -l`).
  - Census thô: `tools/census/6v_micro_census.json` (base_commit `7e39a78` — đã xác nhận là ancestor của `be6bdbf`; diff template giữa 2 commit chỉ `PLI_M70.docx`).
- **Phương pháp:** 3 agent con read-only (24+24+24 trang PNG) cho phần 1, có rubric tự chứa; auditor tự mở PNG trực tiếp cho các trang rủi ro cao nhất + toàn bộ 15 trang spot-check; kiểm chứng XML template (`app/templates/*.docx`) bằng script /tmp (không đụng repo); đo font-size thật trên PDF bằng pymupdf (cùng thư viện gate).
- **Auditor này KHÔNG phải agent đã sửa code; không sửa file tracked nào.** Report này là sản phẩm duy nhất, không commit.

---

## Phần 1 — Adjudicate 72 hit D5_blank_sparse (71 record)

Tất cả 72 trang đều đã được mở PNG (3 agent con) + đối chiếu PDF text. Auditor tự xác minh trực tiếp 3 trang rủi ro nhất (PLI_M42 p2 valid-full, PLI_M72 p3 m72_dhdn, PLI_M12 p2 empty-paper) — khớp verdict agent.

**Rubric:** (i) hợp pháp — trang cuối tự nhiên thưa/chữ ký cuối hồ sơ; (ii) chấp nhận được — legacy layout/giá trị dài wrap qua ranh giới trang; (iii) LỖI THẬT — trang gần trống vô lý, nội dung bị đẩy lệch.

**Tally: (i) = 59 · (ii) = 7 · (iii) = 6** (72 hit / 71 record — record `empty-paper/main/PLI_M12` có 2 hit).

### empty-paper (21 hit)

| Form | Trang | Loại | Lý do 1 câu |
|---|---|---|---|
| PLII_M10 | 2/2 | (i) | Đuôi khối Nơi nhận ("- Lưu:") + khối chữ ký TRƯỜNG PHÒNG + (Ký…) nguyên vẹn cùng trang |
| PLII_M17 | 2/2 | (ii) | Cặp NGƯỜI NỘP (tr1) / NGƯỜI NHẬN (tr2) wrap qua ranh giới trang, mỗi khối vẫn đủ dòng (Ký và ghi họ tên) |
| PLII_M19 | 2/2 | (i) | Khối chữ ký TRƯỜNG PHÒNG nguyên vẹn trang cuối; Nơi nhận đã đủ ở tr1 |
| PLII_M22 | 2/2 | (i) | Như PLII_M19 |
| PLII_M23 | 2/2 | (i) | Như PLII_M19 |
| PLI_M02 | 6/14 | (ii) | 4 dòng nhãn form (Tỉnh/TP, Quốc gia, ĐT/Fax, Email/Website) là đuôi mục địa chủ wrap từ tr5 — wrap tự nhiên, không mất phần tử |
| PLI_M12 | 2/22 | **(iii)** | ORPHAN NOTE: chú giải "Kê khai trong trường hợp có nhà đầu tư nước ngoài…" (footnote-style, marker ¹ + kẻ chân TRỐNG ở tr1) nằm một mình tr2, thân tiếp tục tr3 — trang gần trống vô lý giữa form |
| PLI_M12 | 22/22 | (i) | Dòng chỉ dẫn chữ ký cuối "Trường hợp Tòa án hoặc Trọng tài chỉ định…ký trực tiếp vào phần này" — khối chuẩn cuối hồ sơ |
| PLI_M13 | 3/3 | (i) | Dòng chỉ dẫn Tòa án/Trọng tài cuối; khối chữ ký + footnote 1–3 nguyên vẹn ở tr2 |
| PLI_M19 | 7/7 | (i) | Như PLI_M13 (chữ ký + footnote 1–5 nguyên vẹn tr6) |
| PLI_M45 | 2/2 | (i) | Khối chữ ký TRƯỜNG ĐƠN VỊ nguyên vẹn |
| PLI_M48 | 2/2 | (i) | Đuôi Nơi nhận + khối chữ ký cùng trang |
| PLI_M50 | 2/2 | (i) | Khối Nơi nhận đầy đủ + khối chữ ký cùng trang |
| PLI_M51 | 2/2 | (i) | 1 từ wrap "nghiệp." (đuôi câu tr1) + Nơi nhận + chữ ký cùng trang |
| PLI_M53 | 2/2 | (i) | Khối chữ ký TRƯỜNG ĐƠN VỊ nguyên vẹn |
| PLI_M55 | 2/2 | (i) | 2 ô form cuối (Mã số, Lý do tạm ngừng) + Nơi nhận + chữ ký cùng trang |
| PLI_M57 | 2/2 | (i) | Nơi nhận + khối chữ ký cùng trang |
| PLI_M70 | 2/2 | (i) | Cặp NGƯỜI NỘP/NGƯỜI NHẬN nguyên khối cùng trang |
| PLI_M80 | 3/3 | **(iii)** | ORPHAN FOOTNOTE: chú thích ³ rơi một mình tr3 trong khi marker (Ký và ghi họ tên)³ và footnote ¹,² đều ở tr2 |
| PLI_M72 (m72_dntn) | 2/2 | (i) | Ô điền cuối form Excel M72 ("8. Nơi đăng ký…___") — hợp lệ theo thiết kế M72 |
| PLI_M72 (m72_tnhh_2tv) | 3/3 | **(iii)** | ORPHAN FOOTNOTE: chú thích ² ("Ghi tên của tất cả người đại diện…") một mình tr3, tham chiếu mục 8 ở tr2 |

### valid-minimal (19 hit)

| Form | Trang | Loại | Lý do 1 câu |
|---|---|---|---|
| PLII_M07 | 3/3 | (i) | Khối chữ ký TRƯỜNG PHÒNG nguyên vẹn |
| PLII_M10 | 2/2 | (i) | Nơi nhận + chữ ký cùng trang |
| PLII_M17 | 2/2 | (i) | Cặp NGƯỜI NỘP/NGƯỜI NHẬN nguyên khối |
| PLII_M19 | 2/2 | (i) | "- Lưu:" + chữ ký cùng trang |
| PLII_M22 | 2/2 | (i) | Như trên |
| PLII_M23 | 2/2 | (i) | Như trên |
| PLI_M12 | 22/22 | (i) | Dòng chỉ dẫn chữ ký cuối chuẩn |
| PLI_M18 | 3/3 | (i) | Như trên |
| PLI_M42 | 2/2 | (i) | Khối chữ ký TRƯỜNG ĐƠN VỊ nguyên vẹn (giá trị ngắn hơn nên không có đuôi wrap như valid-full) |
| PLI_M43 | 2/2 | (i) | Như trên |
| PLI_M45 | 2/2 | (i) | Đuôi Nơi nhận + chữ ký cùng trang |
| PLI_M48 | 2/2 | (i) | Nơi nhận + chữ ký cùng trang |
| PLI_M50 | 2/2 | (i) | Như trên |
| PLI_M52 | 3/3 | (i) | Khối chữ ký nguyên vẹn |
| PLI_M53 | 2/2 | (i) | Đuôi Nơi nhận + chữ ký cùng trang |
| PLI_M70 | 2/2 | (i) | "Nơi nhận kết quả bản giấy" + cặp NỘP/NHẬN cùng trang |
| PLI_M75 | 3/3 | (i) | Khối chữ ký nguyên vẹn |
| PLI_M80 | 3/3 | **(iii)** | ORPHAN FOOTNOTE ³ một mình tr3 (marker + footnote ¹,² ở tr2) — y hệt empty-paper |
| PLI_M72 (m72_dhdn) | 3/3 | **(iii)** | Trang CHỈ có 1 nét gạch underscore trơ trọi (~1/4 bề ngang), không nhãn/không gì khác — ô điền mồ côi nghi spillover print-area M72 (auditor tự soi, xác nhận) |

### valid-full (11 hit)

| Form | Trang | Loại | Lý do 1 câu |
|---|---|---|---|
| PLII_M17 | 2/2 | (i) | Cặp NGƯỜI NỘP/NGƯỜI NHẬN nguyên khối |
| PLII_M20 | 2/2 | (i) | Chữ ký TRƯỜNG PHÒNG nguyên vẹn |
| PLII_M22 | 2/2 | (i) | Đuôi Nơi nhận (Sở KHĐT…; Lưu hồ sơ gốc 17) + chữ ký cùng trang |
| PLII_M23 | 2/2 | (i) | Như trên |
| PLII_M25 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLI_M12 | 24/24 | (i) | Dòng chỉ dẫn chữ ký cuối chuẩn |
| PLI_M31 | 2/2 | (i) | Như trên |
| PLI_M42 | 2/2 | (ii) | "Liêm, TP. Hà Nội" = đuôi địa chỉ "…quận Nam Từ Liêm" xé giữa cụm qua trang (auditor tự soi) — khối chữ ký vẫn nguyên; wart dữ-liệu-dài, không mất phần tử |
| PLI_M43 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLI_M52 | 3/3 | (i) | Đuôi Nơi nhận + chữ ký cùng trang |
| PLI_M76 | 2/2 | (ii) | 1 câu cuối "Đề nghị Ông/Bà liên hệ…" wrap sang từ đoạn dài tr1, câu nguyên vẹn |

### long-boundary (10 hit)

| Form | Trang | Loại | Lý do 1 câu |
|---|---|---|---|
| PLII_M08 | 2/2 | (i) | Chữ ký TRƯỜNG PHÒNG nguyên vẹn |
| PLII_M17 | 2/2 | (i) | Đuôi giá trị "Minh - Phòng ĐKKD" (wrap "Hồ Chí/Minh" — đúng chủ đích stress long-boundary) + cặp NỘP/NHẬN đầy đủ cùng trang |
| PLII_M20 | 2/2 | (i) | "- Lưu: Lưu hồ sơ gốc số 17" + chữ ký cùng trang |
| PLII_M25 | 2/2 | (i) | Như trên |
| PLII_M27 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLI_M02 | 33/33 | **(iii)** | Khối footnote bị xé 2 trang: 1–12 ở tr32, dòng 13 mồ côi một mình tr33 |
| PLI_M12 | 46/46 | (i) | Dòng chỉ dẫn chữ ký cuối chuẩn |
| PLI_M31 | 2/2 | (i) | Như trên |
| PLI_M47 | 2/2 | (i) | Chữ ký TRƯỜNG ĐƠN VỊ nguyên vẹn |
| PLI_M76 | 2/2 | (ii) | Đuôi câu "…giấy chứng/nhận" wrap qua trang, câu hoàn chỉnh |

### choice-variants (11 hit)

| Form | Trang | Loại | Lý do 1 câu |
|---|---|---|---|
| PLII_M17 | 2/2 | (i) | Cặp NỘP/NHẬN nguyên khối |
| PLII_M20 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLII_M22 | 2/2 | (i) | Đuôi Nơi nhận + chữ ký cùng trang |
| PLII_M23 | 2/2 | (i) | Như trên |
| PLII_M25 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLI_M12 | 24/24 | (i) | Dòng chỉ dẫn cuối chuẩn |
| PLI_M31 | 2/2 | (i) | Như trên |
| PLI_M42 | 2/2 | (ii) | Đuôi địa chỉ "Liêm, TP. Hà Nội" wrap (như valid-full) |
| PLI_M43 | 2/2 | (i) | Chữ ký nguyên vẹn |
| PLI_M52 | 3/3 | (i) | Đuôi Nơi nhận + chữ ký cùng trang |
| PLI_M76 | 2/2 | (ii) | 1 câu cuối wrap sang, nguyên vẹn |

### Kết luận phần 1

- **59 hit (i)** hợp pháp; **7 hit (ii)** chấp nhận được (đều là wrap giá trị/cặp chữ ký qua ranh giới trang, không mất phần tử pháp lý; chữ ký title + dòng hướng dẫn không bao giờ tách 2 trang trên cả 72 trang).
- **6 hit (iii) — lỗi thật, khuyến nghị đưa vào lane fix (đều cùng 2 gốc rễ):**
  1. *Orphan footnote-style note* (4 hit): `empty-paper/main/PLI_M12` p2, `empty-paper` + `valid-minimal` PLI_M80 p3, `long-boundary/main/PLI_M02` p33. Gốc rễ: chú thích nhúng dạng đoạn thân (template không có `footnotes.xml`) + page break → chú thích tách khỏi marker. Vi phạm checklist 5.1-10 ("không orphan"). Fix gợi ý: keep-with-previous / gộp cụm marker+chú thích.
  2. *Spillover print-area M72* (2 hit): `empty-paper/m72_tnhh_2tv/PLI_M72` p3 (chú thích ² một mình), `valid-minimal/m72_dhdn/PLI_M72` p3 (chỉ còn 1 nét gạch underscore). Gốc rễ: vùng in/row tail của render M72 tràn 1 dòng. Vi phạm 5.1-8 (trang gần trống vô lý).
- Khuyến nghị kế tiếp: 6 hit (iii) vào `defect_registry`; lập **D5 sparse allowlist** (5.1-8) từ bảng trên để các hit (i)/(ii) có lý do đăng ký, biến candidate D5 về 0 "chưa adjudicate" theo gate G-B.
- Không trang nào trong 72 trang có vi phạm khác: không token/placeholder, không bảng vỡ, không chữ ký title tách hướng dẫn. Header band không xuất hiện trên trang thưa nào — đã xác nhận band nằm nguyên ở trang 1 (đúng thiết kế, chỉ trang 1 có band).

---

## Phần 2 — Adjudicate micro-census 7 nhóm

> Nguyên tắc chấm: khác biệt **CÓ CHỦ ĐÍCH theo bản giấy** (đã đăng ký / role-consistent) = không cần sửa; còn lại = lỗi thật đưa lane fix. Không có bản giấy gốc trong repo nên chuẩn "bản giấy" chỉ đối chiếu được qua `docs/decision_registry.md` + nhất quán nội bộ; các mục cần đối chiếu bản gốc thật được ghi rõ "chờ owner".

### a. fill_line_style — 75 form "trộn kiểu điền"

- Soi XML ngữ cảnh (PLII_M01, PLII_M02, PLI_M12, PLI_M72): "trộn" thực chất là **khác vai trò**: gạch DASH = rule trang trí sau khối quốc hiệu; UNDERSCORE = đường kẻ separator footnote (hoặc ô điền M72); DOT (…/...) = dòng điền chữ ký/ngày. Trong cùng một vai trò, từng form nhất quán.
- Ngoại lệ thật tìm được: **PLI_M12 có 1 dòng ASCII-dot `là:..........` giữa các dòng unicode `……` cùng vai trò** — lẫn lộn "…"/"..." đúng định nghĩa checklist 5.2/6.
- Cross-form: family PLII điền bằng ASCII-dots, family PLI điền bằng unicode-ellipsis — khác kiểu **giữa các form** (5.1-6 "một kiểu toàn corpus" không thỏa theo nghĩa hẹp), khả năng cao theo bản gốc từng family nhưng **chưa có entry registry**.
- **Số form cần fix thật: 1** (PLI_M12 — 1 dòng, sửa nhỏ). Cả khối: khuyến nghị Lead lập registry "fill-line style per family" (kèm đối chiếu bản gốc) thay vì ép 1 kiểu toàn corpus.

### b. colon_paren — 4 form paren_unbalanced

- `PLI_M12`: **false-positive của công cụ** — `LIST_MARKER_RE = (^|[\s(>])[a-zà-ỹđ]\)` ăn luôn "(i)"/"(ii)" (numeral La Mã trong ngoặc), xóa ")" làm census tự tạo imbalance. Đo lại thủ công: opens=2/closes=2, cân bằng. → 0 fix; khuyến nghị sửa regex census (loại trường hợp "(\w)") + rebaseline.
- `PLI_M54` / `PLI_M55` / `PLI_M57`: **LỖI THẬT** — template có đoạn `Cơ quan đăng ký kinh doanh cấp tỉnh): {co_quan_dkkd}` (0 mở / 1 đóng, hàng xóm cũng không có "("), render ra "…cấp tỉnh): Phòng Đăng ký kinh doanh - Sở…" (đã xác nhận trên PDF valid-full cả M54 và M55). Dấu ")" mồ côi nhìn thấy được bởi người đọc.
- **Số form cần fix thật: 3** (M54, M55, M57 — cùng 1 gốc rễ, bổ sung "(" đầu dòng hoặc bỏ ")" theo bản gốc).

### c. font_floor — 9 form

- XML (9/9 form): `runs_below_8pt = 0`, chỉ 1–4 **paragraph-mark** <8pt (dấu ¶ ẩn) → phần lớn là artifact đo, đúng như census note.
- Kiểm chứng độc lập bằng PDF (đo span thật, toàn corpus 87 form): mọi text thường ≥ 8pt (body 12pt); các span 7.0pt duy nhất là **chữ số tham chiếu footnote dạng superscript** (LO/Word tự scale ~58% — chuẩn typography, không phải "chữ quá nhỏ") và **đường separator underscore bị style superscript** (thuộc nhóm d, xem dưới).
- **Số form cần fix thật: 0.** (Gap phương pháp của census: chỉ quét `w:sz` tường minh trong `document.xml`, không phủ size kế thừa — PDF cross-check này đã đóng khoảng trống đó.)

### d. superscript_glue — 31 form (superscript chứa underscore)

- 31 form đều có đúng 1 pattern chung: **đường kẻ separator footnote là 1 paragraph gạch underscore bị style `vertAlign=superscript`** → render ~7pt, ngắn (~39 ký tự), nhích cao hơn baseline (soi crop PLII_M01 p5; span PDF size=7.0).
- Nhìn đơn lẻ: chấp nhận được (vẫn đọc là separator); nhưng **không nhất quán corpus**: các form khác (PLI_M30, PLII_M03, PLI_M51…) có separator thường, full-width. PLI_M72 còn làm nó thành dòng "____" mồ côi 7pt giữa form (liên quan 2 hit (iii) phần 1).
- **Số form cần fix thật: 31 (cùng 1 gốc rễ, 1 chỗ sửa trong generator/template render)** — mức cosmetic, khuyến nghị chuẩn hóa về separator thường (hoặc đường kẻ really-thật) trong lane micro; không blocker.

### e. orphan_heading — 14 form ("STT" lạc đơn)

- XML: các đoạn "STT" là **đoạn THÂN ngoài bảng**, ngay sau heading mục thuế/tài sản và trước caption — tức header-row của bảng bản giấy bị "làm phẳng" thành các dòng paragraph center: `STT` / `Các chỉ tiêu thông tin đăng ký thuế` / `5.1` lơ lửng không có bảng.
- Soi PNG xác nhận: `valid-full/main/PLII_M02` p8, `empty-paper/main/PLI_M19` p4, `choice-variants/main/PLI_M12` p13 — người đọc Ketoan sẽ thấy "STT" không gắn với bảng nào; bản giấy gốc trình bày bằng bảng có viền.
- **Số form cần fix thật: 14** — hoặc khôi phục header đúng vai trò (bỏ dòng "STT" mồ côi / ghép vào caption), hoặc đăng ký lý do chuyển đổi bảng→danh sách. Hiện chưa có đăng ký nào.

### f. header_band — 53 form (para_br_3lines + so_line_not_right)

- XML: band = 1 paragraph 3 dòng (quốc hiệu / độc lập / `----`) căn giữa; dòng `Số: …` là paragraph riêng **jc=center** (không có tab-stop phải). PNG `valid-full/PLII_M08` p1: Số căn giữa, ngày-tháng-năm căn phải.
- Đối chiếu registry: `decision_registry` đã chốt chuẩn cho family kia (22 form `table_2col` — tên trái + quốc hiệu phải, "Số:" TRÁI / ngày PHẢI; soi `PLII_M02` p1 khớp chuẩn). Family para_br (53 form) **không có entry registry nào** cho kiểu band centered + Số centered.
- Nhận định: không phải lỗi render (nhất quán, sạch); "so_line_not_right" là flag máy (kiểm jc không cần phép — đúng như census note). Nhưng theo V4-2, "khác biệt có chủ đích phải nằm trong registry với lý do" — hiện chưa có.
- **Số form cần fix thật: 0 lỗi render; 53 form chờ quyết định owner** (đối chiếu bản gốc TT 68/121 từng mẫu: nếu bản gốc có quốc hiệu giữa + Số giữa thì đăng ký; không thì chuẩn hóa về 1 kiểu). Không tự adjudicate legal được.

### g. table_border_pad — 8 form (border_sig_variants=2)

- XML đo lại (đủ tblPr + tcPr): 2 signature = **bảng band đầu trang không viền** (tên DN/HKĐ trái + quốc hiệu phải — đúng chuẩn đã chốt trong `decision_registry`) và **các bảng dữ liệu viền đủ 4 cạnh + inside**. Không có bảng "viền lộn xộn".
- PNG `PLII_M02` p1/p4: band sạch, bảng dữ liệu lưới đều.
- **Số form cần fix thật: 0** — khác biệt có chủ đích, đã có registry chuẩn band.

---

## Phần 3 — Spot-check thị giác 15 trang ngẫu nhiên (checklist 5.1)

Sample: uniform random 15/1612 trang, seed `20260905` (tái lập được). Đối chiếu 10 điều mục 5.1.

| # | Trang (fixture/form/p) | Verdict | Ghi chú cụ thể |
|---|---|---|---|
| 1 | empty-paper/PLI_M03 p5 | **PASS** | note: trên form giấy trống, slot ngày sinh còn skeleton "//" (đọc ổn, có thể cân nhắc "…/…/…" theo bản giấy); ô vuông rỗng đúng thiết kế empty-paper |
| 2 | empty-paper/PLI_M19 p4 | **PASS** | note: pattern "STT" mồ côi (nhóm e) hiện diện; vị trí ô vuông trước/sau nhãn không nhất quán trong cùng nhóm ("□ Hạch toán độc lập" vs "Có báo cáo tài chính hợp nhất□") |
| 3 | empty-paper/PLI_M51 p2 | **PASS** | note: slot Nơi nhận trống render "- ;" (trông như lỗi dấu chấm phẩy lơ lửng trên bản in trống); wrap "nghiệp." đầu trang |
| 4 | valid-minimal/PLI_M30 p1 | **PASS** | band chuẩn registry, footnote bottom đúng chỗ, separator thường |
| 5 | valid-full/PLII_M02 p4 | **VIOLATION (5.1-5)** | bảng landscape 10 cột đọc được nhưng **vỡ token trong cột hẹp**: "ĐẶN/G", "HẰN/G", "Singapo/re", tên + chỉ số tách dòng ("MINH HẢI/66"); note: cột "Chữ ký" bị fixture điền tên (xem Finding ngoài phạm vi #3) |
| 6 | valid-full/PLI_M01 p5 | **PASS** | bảng tài sản 4 cột sạch; note dữ liệu (ngoài phạm vi): cột Tỷ lệ không cộng khớp "Tổng số" |
| 7 | valid-full/PLI_M04 p4 | **PASS** | note: ô vuông vẽ cao hơn rộng (chữ nhật đứng) ở vài dòng inline "Có□ Không □"; superscript ⁴ đúng chỗ |
| 8 | long-boundary/PLI_M03 p6 | **PASS** | giá trị dài wrap tự nhiên, không vỡ |
| 9 | long-boundary/PLI_M09 p16 | **VIOLATION (5.1-5)** | header lặp đúng khi sang trang ✓, hàng không xé ✓, nhưng cột hẹp vỡ token nặng: "ĐẶN/G MINH HẢI 236", "Nguyễ/n Văn", "phườn/g", mã GCTP "060000/000023/9" |
| 10 | long-boundary/PLI_M31 p2 | **PASS** | trang thưa = chỉ dẫn ký cuối hồ sơ (khớp phần 1) |
| 11 | long-boundary/PLI_M48 p2 | **PASS** | Nơi nhận đầy đủ + chữ ký cùng trang |
| 12 | choice-variants/PLII_M03 p1 | **PASS** | band chuẩn, footnote bottom sạch |
| 13 | choice-variants/PLI_M12 p13 | **PASS** | pattern header-bảng-làm-phẳng (nhóm e) hiện diện: "6" / caption / "Tổng số" centered lơ lửng giữa trang thưa |
| 14 | choice-variants/PLI_M19 p1 | **PASS** | note: dòng "Mẫu số 19" góc PHẢI (các form khác góc TRÁI — xem Finding ngoài phạm vi #2); dòng điền "……" nhất quán trong form |
| 15 | choice-variants/m72_tnhh_2tv/PLI_M72 p2 | **VIOLATION (5.1-5)** | bảng thành viên 8 cột đọc được nhưng vỡ token: "NGUYỄ/N", "Singapo/re", "0500000/000112", vốn "5700000/0000" |

**Tally: 12/15 PASS (trong đó 8 PASS kèm note), 3/15 VIOLATION cùng 1 lớp: chữ vỡ giữa token trong cột bảng hẹp (5.1-5).** Lớp này là trade-off đã biết của Q-V2 (sàn 900 twips cho ≥10 cột, số cột không đổi); checklist 5.1-5 vẫn ghi "không chữ vỡ giữa token" nên ghi nhận là violation, mức ưu tiên do Lead/owner xếp (khả năng xử lý: nới cột họ tên/quốc tịch/số-GCTP hoặc chặn break-word cho token dài).

---

## Finding ngoài phạm vi (không tự adjudicate)

1. **PLI_M76 không có khối chữ ký**: trong corpus valid-full/long-boundary/choice-variants, cả 2 trang render đều không có title chữ ký hay vùng ký nào (grep text + soi PNG p1/p2). Thông báo của cơ quan ĐKKD thường phải có người ký — **cần owner đối chiếu bản giấy** (thiếu = lỗi nội dung mẫu; có theo bản gốc nhưng bị mất khi build template = lỗi build).
2. **Vị trí dòng "Mẫu số N" không nhất quán giữa form**: PLI_M19 đặt góc phải, PLI_M30/PLII_M02/PLII_M03 đặt góc trái. Khả năng theo bản gốc từng mẫu — cần registry xác nhận, không sửa theo "1 kiểu toàn corpus" khi chưa đối chiếu.
3. **Cột "Chữ ký" trong bảng thành viên được fixture điền tên + chỉ số** (PLII_M02 p4, PLI_M09 p16, M72 p2): cột ký trên bản giấy là vùng viết tay. Câu hỏi policy: `handwriting_only_slots` có áp dụng cho cột bảng không? (D14 chỉ chạy slot tên dưới tiêu đề.)
4. **Độ thực của giá trị valid-full**: trường ngày đôi khi chỉ có số ngày ("Ngày, tháng, năm sinh: 12", "Ngày cấp 10") — mandate B4 là "giá trị tiếng Việt thực"; thuộc lane fixture (`agent/6v-fixture`), không đánh giá trong report này.
5. **Bug census (công cụ, không phải corpus)**: `LIST_MARKER_RE` ăn cả "(i)/(ii)" (nhóm b, PLI_M12) — sửa regex + rebaseline để census kỳ sau không báo lại false-positive.

## NOT-RUN (kèm lý do — không đoán)

- **Word-open loop 91/91, determinism, ZIP/integrity**: NOT-RUN — thuộc auditor/6v-export và gate V5, không nằm trong 3 phạm vi nhiệm vụ này.
- **Regen ×2 zero-diff / drift-guard**: NOT-RUN — thuộc auditor/6v-core.
- **UI checklist 5.2 (V4 mục 4)**: NOT-RUN — nhiệm vụ này chỉ phủ trang in (5.1); UI thuộc lane micro/ui khác.
- **Đối chiếu trực tiếp bản giấy gốc TT 68/2025, TT 121/2026**: NOT-RUN — bản gốc không có trong repo; phần 2 chỉ dùng registry nội bộ + nhất quán làm chuẩn; các mục "chờ owner" (nhóm a cross-form, nhóm f) phải đối chiếu bản gốc trước khi chốt.
- **Verdict reviewer per-record 100% (G-E)**: nhiệm vụ này adjudicate 72 candidate D5 + 15 trang spot-check, KHÔNG thay thế nghĩa vụ per-page verdict 100% của V4 — phần còn lại chưa có người ký.

---

## OVERALL: **PASS-WITH-NOTES**

- HARD-fail 0 của gate khớp quan sát độc lập; PNG đĩa == manifest 1612/1612; không phát hiện lỗi lớp nghiêm trọng (không token, không placeholder, không glue, không chữ ký vỡ).
- Nhưng gate V4 ("micro-census 0 khác biệt không đăng ký" + "trang thưa phải có allowlist") **chưa thỏa tuyệt đối**: còn 6 hit D5 (iii) chưa vào registry, 14 form "STT" mồ côi, 3 form ngoặc ")" mồ côi, 31 form separator superscript chưa chuẩn hóa/đăng ký, 53 form band centered chưa có entry registry, và 1 lớp violation 5.1-5 (vỡ token cột hẹp) trong spot-check.
- Mọi mục trên đều có form/trang cụ thể + gốc rễ ở các phần trên, đủ đưa vào lane fix hoặc registry mà không cần điều tra thêm.

## Lệnh tái lập

```bash
git worktree add ../dangky_kinhdoanh-worktrees/6v-audit-visual -b 6v-audit-visual be6bdbf
# PNG đĩa vs manifest
find generated_ho_so/_visual_layout/phase6v/v4_corpuscheck -name "page-*.png" | wc -l   # 1612
# D5 hits từ manifest
python3 - <<'EOF'
import json
m=json.load(open('generated_ho_so/_visual_layout/phase6v/v4_corpuscheck/manifest.json'))
print(sum(1 for r in m['records'] for g in (r.get('gate_candidates') or [])
          if g['detector']=='D5_blank_sparse'))  # 72
EOF
# Census thô
python3 tools/census/6v_micro_census.py   # base_commit 7e39a78 (ancestor của be6bdbf)
# Font-floor PDF (script dùng fitz/pymupdf như gate) — xem mục phần 2c trong report
```

*(Auditor: agent/6v-visual — phiên độc lập, spawn fresh, không dùng context chung với executor.)*
