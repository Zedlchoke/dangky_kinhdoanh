# PHASE9-BANDFIX — AUDIT TABLE & KẾT QUẢ QA TOÀN BỘ MẪU (2026-09-09)

> Phạm vi: toàn bộ 87 form (86 active + PLI_M11 REMOVED) của catalog hiện hành,
> tiêu thụ qua 28 use case — không tồn tại nhóm "26 mẫu" riêng (kiểm kê
> 2026-09-09: `use_cases.json` có 28 case tham chiếu 27 form dưới dạng tổ hợp).
> Corpus QA: `generated_ho_so/_visual_layout/phase9_bandfix/` (v1, render tại
> HEAD 3f4af84 trước wave2/3) và `phase9_bandfix_v2/` (sau wave2+wave3).
> BASE `3f4af84` (F7 PASS-WITH-NOTES + bandfix a01f433/2ed4629) → các wave sửa
> của phiên này commit trên `main` sau đó. Không push (chờ lệnh owner).

## 1. Điểm xuất phát và bằng chứng v1

- Runner tại HEAD `3f4af84`: **65 PASS / 0 FAIL — VERDICT PASS** (trừ
  `test_docx_layout_ui` nằm ngoài runner: **4 FAIL stale pin** — đã sửa, xem A-14).
- Corpus v1 `phase9_bandfix`: 455 record (91 render-unit × 5 fixture),
  **HARD 0**, candidate 5 (D9 PLI_M10 pixel-OK — đã adjudicate trước đó),
  export error 0, PNG/PDF đầy đủ + 455 contact sheet tại `_qa_contact/`.
- Duyệt trực quan 6 agent trên v1: band 23 form (empty + full) **23/23 PASS**;
  empty-paper 68 sheet → 5 MAJOR phân trang; valid-full 68 sheet → adjudicate
  3 lớp A (lỗi thật), 3 lớp B (fixture/harness), 7 lớp C (chủ đích có ghi
  registry); choice-variants → 14 cụm tick N-tick/0-tick; legal P0+P1 đối
  chiếu 9 cặp ảnh nguồn (TT121 + TT68).

## 2. Bảng audit lỗi — mẫu, gốc rễ, cách sửa, trạng thái

Mức: BLOCKER / MAJOR / MINOR. Trạng thái tính đến commit cuối phiên.

| # | Mẫu/trang | Lỗi | Mức | Gốc rễ (file) | Cách sửa | Trạng thái |
|---|---|---|---|---|---|---|
| A-1 | PLI_M42/43/63/68/69 + PLI_M72 ×5 variant (trang có "Ngày cấp…Nơi cấp…") | 1 input `{ngay_cap}` trôi vào ô NƠI CẤP; "Ngày cấp" trống | MAJOR | `tools/build_form_maps.py::_assign_para_slots` — slot `…` 1 ký tự vô hình với DOT_RUN ≥2 | tách nhãn ghép `^ngay cap…noi cap$`: slot ẩn = `{..ngay_cap}`, nhóm cuối = `{..noi_cap}` (Lane C `33fb389`) | ✅ ĐÃ SỬA + pin `test_wave2_docx_pins` 6/6; verify render v2 |
| A-2 | PLI_M67 (câu "(tên doanh nghiệp)…") | slot sau "(tên doanh nghiệp)" bind `co_quan_dkkd` → in tên cơ quan thay tên DN | MAJOR | rule unanchored `co quan dang ky kinh doanh cap` trúng nhãn dài | rule neo đuôi `cua doanh nghiep: \(ten doanh nghiep\)$` → `dn.ten_tieng_viet`, đặt trước (Lane C `33fb389`) | ✅ ĐÃ SỬA + pin; verify render v2 |
| A-3 | PLI_M12 trang 1 | thiếu dòng "Mẫu số 12" (nguồn TT 121/2026 p50 in đậm góc phải trên) | MAJOR | generator migrate mất dòng; contract cũ TOP_BAND assert ngược lại | `_normalize_mauso_label` CHÈN "Mẫu số 12" đậm căn phải; contract `before == ["Mẫu số 12"]` (Lane C `33fb389`) | ✅ ĐÃ SỬA; verify render v2 |
| A-4 | 15 form band (M17/23/25/27/28/29/30/31/32/33, PLII_M02–06) | nhãn "Mẫu số N" căn TRÁI, nguồn pháp lý đặt PHẢI + đậm (9/9 cặp ảnh nguồn đã soi) | MINOR | generator giữ theo scrape lệch | `_normalize_mauso_label` chuẩn hoá PHẢI+đậm, idempotent (Lane C `33fb389`) | ✅ ĐÃ SỬA + pin `t_c4_mauso_right_bold` |
| A-5 | PLII_M17 empty-paper t2 | cặp ký NGƯỜI NỘP/NGƯỜI NHẬN bị cắt 2 trang, "NGƯỜI NHẬN" lơ lửng | MAJOR | `_ensure_signature_space` chèn spacer không-flag giữa cặp ký dọc | cặp atomic: keepNext cho instruction + spacer khi đoạn kế khớp `_SIG_TITLE_RE`; đếm `w:line exact` chống double-insert (Lane E `b19bb4c`) | ✅ ĐÃ SỬA (16 test); verify render v2 |
| A-6 | PLI_M70 empty-paper t2 (~95% trắng) | bảng ký ngang 1×2 cao ~74pt > chỗ trống → nguyên hàng sang t2 | MAJOR | `_SIG_TABLE_TEMPLATE` trHeight 1200 + spacer 800 (giá trị trước v7) | hạ 600/240 ở render pass + mirror generator (Lane E `8d10e25`) | ✅ ĐÃ SỬA; verify render v2 |
| A-7 | m72_dhdn empty-paper t2 (~95% trắng, 1 dòng mục 8) | run 9 paragraph rỗng sau bảng thành viên tràn trang | MAJOR | tàn dư đệm viết tay trong template, mâu thuẫn quyết định N-only | pass mới `_collapse_blank_para_runs` nén run ≥3 rỗng sau `</w:tbl>` về 1 (Lane E `02be545`) | ✅ ĐÃ SỬA — DNTN/DHDN về 1 trang (W3 15/0); entry D5 sẽ stale |
| A-8 | PLI_M45, PLI_M53 empty-paper t2 | cụm ký "TRƯỜNG ĐƠN VỊ" mồ côi t2 dù t1 còn vài % chỗ | MAJOR | đuôi cụm ~52pt > usable 25/7pt; para rỗng nằm SAU cụm nên E4 no-op | E4 trim (Lane E `cb2783a`) đúng spec nhưng no-op trên template hiện tại | ⚠️ CHƯA ĐÓNG — P1 adjudicate (đã allowlist class (i), cụm không bị TÁCH) — xem §4 |
| A-9 | Bảng ngành/CSHHL/thành viên trong corpus v1: M01/02/03/10/11, PLII_M01/02/07 | bảng chỉ có header, 0 dòng dữ liệu ở valid-full | MAJOR | `_nest` (app_web/main.py) đè LIST loop bằng dict khi key dotted trùng prefix qua merge batch 86 form | `_nest` giữ nguyên node list; merge dùng hàm chung `merge_fixture_data` (Lane B `85a8b5b`) | ✅ ĐÃ SỬA + 21 loop tái hiện được + test; verify render v2 |
| A-10 | PLII_M01 bảng thành viên cột ngày sinh; PLI_M02 p7 ngày sinh/ngày cấp | cột ngày chỉ có "24"/"23" (mất tháng/năm) | MAJOR | `_date_slot_is_component` dương tính giả: scalar trần cùng tên khác đối tượng | key trần trong grid tra theo namespace loop (`set_loop_ns`) (Lane B `85a8b5b`) | ✅ ĐÃ SỬA + test; verify render v2 |
| A-11 | M02/04/05 cột "bằng chữ" = số; cột % M04 = hàng trăm tỷ | fixture trả giá trị sai kiểu | MAJOR (realism) | `value()` nhánh `von` nuốt `_chu`/`ty_le` | check `_chu`/`bang_chu` + `ty_le`/`phan_tram` TRƯỚC nhánh von (Lane B `85a8b5b`) | ✅ ĐÃ SỬA + test — hệ quả có chủ đích: floors cột M10 đổi → regen M10 (commit wave3) |
| A-12 | choice-variants: 14 cụm N-tick/0-tick trên 12 form (m72 ngành chính ×3 dòng; đất đảo/GTNT Có[X]Không[X]; tình trạng thành lập 2 ô; M12 tách/sáp nhập; PLII_M02 đổi chủ hộ) | tick sai số lượng cụm loại-trừ | MAJOR (fixture) | fixture không đăng ký đủ EXCLUSIVE_GROUPS; `la_nganh_chinh` đánh mọi dòng | đăng ký cụm mới (2 file, nhất quán) + `la_nganh_chinh` chỉ dòng đầu; validator V1b bắt 0/2+ (Lane B `85a8b5b`) | ✅ ĐÃ SỬA + sweep 86 form sạch; verify render v2 |
| A-13 | Corpus gồm PLI_M11 (REMOVED_BY_CURRENT_LAW), không stamp | gate quét nhầm form đã bãi bỏ | MINOR (harness) | `phase5_visual_gate` dùng `sorted(maps)` | `active_form_ids()` như corpus exporter; render-unit 90/fixture (Lane B `85a8b5b`) | ✅ ĐÃ SỬA |
| A-14 | `test_docx_layout_ui.js` 4 FAIL (ngoài runner) | pin CSS cũ 42%/58%/bottom + pin band có nhãn — stale sau bandfix/e148d83 | MAJOR (test) | bandfix đổi CSS nhưng không sync suite | pin sync mirror-band + 36/64/top/13pt bold + check mirror đồng bộ giá trị (`25f1b97`) | ✅ ĐÃ SỬA 18/18 |
| A-15 | Test DOCX không pin geometry band mới (G1–G3) | revert 0.42/mất bold/mất vAlign vẫn xanh | MINOR (test gap) | bandfix a01f433 không kèm pin | pin ratio theo hằng số + TNR/13pt/bold theo băng + vAlign thứ tự tcPr (`25f1b97`) | ✅ ĐÃ THÊM 11/11 |
| C-1 | M70/71/75/63, PLII_M17/18 "Hồ sơ bao gồm" trống; M75/M63 bảng chi nhánh trống | bảng/khối trống ở valid-full | — | OUTPUT_ONLY (quyết định của cơ quan) — coverage adjudicate O1 | không sửa | ✅ CHÍNH ĐÁNG (lớp C) |
| C-2 | M73/M74 vùng công bố trống; M46 shell; M51 2 slot không binding | placeholder không điền | MINOR | khung in sẵn/chưa có input; M51 cần owner | không sửa; đưa registry + P2 | 📋 P2 |
| C-3 | Checkbox ô rỗng hẹp (border+NBSP ~1:2.5); valid-full không tick | glyph/thiết kế fixture | — | thiết kế 6V-V2 + fixture choice-variants chuyên tick | không sửa | ✅ CHÍNH ĐÁNG (lớp C) |
| C-4 | Số tiền không nhóm nghìn; "(lần N)"/"Nội dung kê khai số N" trong ô | fixture format policy | MINOR | locale-free có docstring; hậu tố anti-trùng D12 | không sửa; P2 realism | 📋 P2 |
| L-1 | M12/M27/M30 + 6 cặp TT68 | band cấu trúc khớp nguồn; DECIDED-DIFF: nhãn 'TÊN DOANH NGHIỆP' đã xoá (e148d83) lệch bản giấy | MINOR (pháp lý) | quyết định owner 2026-09-08 | giữ; owner xác nhận lại hệ quả | 📋 P1 owner-note |

## 3. Kiểm định hồi quy theo checklist lỗi lịch sử (mandate)

| Lỗi lịch sử | Gate chặn | Kết quả v1 |
|---|---|---|
| Mẫu 9 lẫn nội dung mẫu khác / không bảng thật | D1/D4 HARD + test V1a/V1f | 0 hit — sạch |
| Bảng quá hẹp, vỡ từng ký tự | D9 two-tier + floors longest-word | candidate 5 (M10, đã adjudicate pixel-OK); sau regen floors mới cần re-gate v2 |
| Ngày tháng nối sai/trùng | D13 skeleton glue | 0 hit |
| Checkbox không tick rõ/tách dòng | D15 + validator V1b mới | glyph trong ô, không rớt dòng; v1 còn 14 cụm tick sai số lượng → đã sửa A-12 |
| Thành phần lựa chọn văng trang | D5 + phân trang | A-5..A-8 đã xử lý 4/5 |
| Tiêu đề/bảng/ghi chú/chữ ký tách sai trang | D6/D7/D8 + D18 | A-5/A-6/A-7 sửa; D7/D8 còn blind-spot (P1) |
| Test dữ liệu/HTML không là bằng chứng Word | corpus PDF/PNG + Word open | v2 phải render lại toàn bộ + Word open trước khi kết luận |

## 4. Việc còn mở sau phiên (chốt ở PLAN tổng hợp)

- Verify render v2 + Word open + D5 allowlist prune + re-gate D9 M10.
- A-8 (M45/M53): adjudicate tiếp — 3 phương án ở PLAN §P1.1.
- Pin A4 page geometry: quyết định owner (đổi khổ LETTER→A4 toàn corpus).
- DECIDED-DIFF nhãn band + M09 các câu hỏi owner mở (đang PIN BLOCKED trong
  suite `r3b1` — không mất).
- Detector blind-spot D7 (split cấp-cặp) / D8 (spacer nội bộ ô).

## 5. Kết quả corpus v2 SAU wave2+wave3 (bằng chứng cuối phiên)

| Hạng mục | Kết quả |
|---|---|
| Corpus `phase9_bandfix_v2` | **450 record (90 render-unit × 5 fixture — M11 removed đã loại khỏi inventory)**; HARD **0**; candidate **5** (D9 PLI_M10 min-col 624 — pixel-OK đã adjudicate từ phase8g, nay cột thoáng hơn); export error 0 |
| Word open-direct 16.16.27 | **90/90 PASS_OPEN_DIRECT** (`word_open/inventory.json`) |
| Contact sheet | 450 sheet tại `_qa_contact/<fixture>/` (5 fixture × 90) |
| Verify từng fix bằng ảnh/text-layer | Mục 1-10 §5.1 dưới — **ĐẠT** (trừ A-8 đã ghi P1) |
| D5 allowlist | prune **26 entry stale** + thêm **4 entry (ii)** Lead duyệt ảnh; H7 exact-set 57/57 |
| Runner | **68 PASS / 0 FAIL — VERDICT PASS** (65 + 3 suite wave2/3 mới đăng ký) |

### 5.1 Verify từng fix trên corpus v2 (Lead, ảnh + text-layer)

1. PLI_M12: có "Mẫu số 12" đậm căn phải trên band — ĐẠT (ảnh).
2. Nhãn "Mẫu số" phải+đậm: M17 ĐẠT (ảnh đại diện); 23/23 pin structural `t_c4_mauso_right_bold` xanh.
3. Ngày cấp/Nơi cấp 2 giá trị: M42/M63/M68/m72_dntn (text: "Ngày cấp: 14/02/2025 Nơi cấp: Sở Kế hoạch…") — ĐẠT; 10 block pin `test_wave2_docx_pins` 6/6.
4. PLI_M67: "(tên doanh nghiệp) CÔNG TY TNHH MTV KỸ THUẬT - XÂY DỰNG TRƯỜNG THÀNH 23" — ĐẠT (text).
5. PLI_M70: 1 trang, cặp ký trang 1 (E1) — ĐẠT (ảnh + page count).
6. PLII_M17: 2 trang nhưng cặp NGƯỜI NỘP/NGƯỜI NHẬN nguyên khối cùng trang (E2) — ĐẠT (ảnh).
7. m72_dntn + m72_dhdn: 1 trang (E3; W3 pin 15/0) — ĐẠT.
8. Bảng dữ liệu valid-full: M10 có dòng + % hết số 12 chữ số (B3); PLII_M01 ngày sinh dd/mm/yyyy + VSIC giữ 0 đầu (B1+B2) — ĐẠT (text).
9. Tick choice-variants: m72_dntn ngành chính chỉ dòng 1 có X (B4a) — ĐẠT (text); **B6** merge de-dup 7 cụm "Có X Không X" (M01–M05/M12/M15) — ĐẠT (DOCX XML: 1 X-run) sau re-render fixture.
10. PLI_M45/M53: vẫn 2 trang (E4 no-op đã ghi) — P1 adjudicate tiếp.
