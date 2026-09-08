# Header semantic census (F3H) — 2026-09-08

> Chỉ thị: docs/f3h_f3t_directive_2026-09-08.md (mục 2 — F3H lane) — census occurrence-level mọi “TÊN DOANH NGHIỆP/TÊN HỘ KINH DOANH” từ ảnh nguồn pháp lý.

Nguồn: (1) bảng 5-role từ ảnh scan TT 121/2026 (9 mẫu, /tmp/tt121_pages) + TT 68/2025 (78 mẫu, /tmp/tt68_pages); (2) structural scan template docx; (3) tools/header_name_binding.json.

## 5 role

- `required_band_mirror` — band + thân có trường tên cùng key: **21 form**
- `required_band_input` — band là ô nhập tên chủ thể duy nhất: **2 form**
- `no_subject_band` — không có band chủ thể: **19 form**
- `legal_title_or_subtitle` — "TÊN..." chỉ là tiêu đề phụ, không fillable: **0 form**
- `output_mirror` — không band; tên chủ thể là nội dung output CQ cấp/công bố: **45 form**

Tổng: **87 form**, **360 occurrence** (image + structural), **23 form có band chủ thể** (registry band-bound: 23 — khớp).

## Cặp phân biệt bắt buộc (fixture)

- **PLI_M31** (p134, role `required_band_mirror`): FIXTURE 1/2 (phân biệt với PLI_M72): source CÓ band + gạch chân điền NGAY DƯỚI NHÃN (dòng 'Số:' là số hồ sơ, tách biệt) — converter PHẢI giữ nhãn + fill-line dưới nhãn.
- **PLI_M72** (p199-p206, role `output_mirror`): FIXTURE 2/2 (phân biệt với PLI_M31): source KHÔNG CÓ band — '(TÊN...)' là tiêu đề phụ biến thể + '1. Tên doanh nghiệp' là section output; converter CẤM TỰ THÊM band. Detector BAND_FORBIDDEN_PRESENT.

Fixture phụ: PLI_M32 (mirror A→B), PLI_M33 + PLII_M06 (band_input), PLI_M79/PLI_M80 (band “TÊN TỔ CHỨC” là band NGƯỜI ĐỀ NGHỊ — cấm nhận nhầm là band chủ thể).

## Sửa soạn theo ảnh 2026-09-08

- PLI_M47: no_subject_band → output_mirror — ảnh p159 có khối 'Kính gửi: (Tên doanh nghiệp)/Địa chỉ/Mã số' (bản nháp 09-07 ghi sai 'KHÔNG có trường tên chủ thể')
- PLI_M50: no_subject_band → output_mirror — ảnh p162 có khối 'Kính gửi: (Tên doanh nghiệp)'
- PLI_M63: no_subject_band → output_mirror — ảnh p182 có trường 'Tên doanh nghiệp (ghi bằng chữ in hoa):' (mục 'Là chi nhánh/VPĐD/điểm KD của doanh nghiệp sau:')
- Chốt fixture bắt buộc: PLI_M31 (ảnh p134) CÓ band 'TÊN DOANH NGHIỆP' + fill dưới nhãn; PLI_M72 (ảnh p199) KHÔNG band, '(TÊN...)' là subtitle — khớp bảng census

## Bảng census theo form

| Form | Nguồn (trang ảnh) | Band | Role | subject | key | occurrence chính |
|---|---|---|---|---|---|---|
| PLII_M01 | 68/2025/TT-BTC p221-p231 | — | `no_subject_band` | hkd | hkd_ten_tieng_viet | [input/self] Tên hộ kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa); [input/self] Tên hộ kinh doanh viết bằng tiếng nước ngoài (nếu có):; [input/self] Tên hộ kinh doanh viết tắt (nếu có): |
| PLII_M02 | 68/2025/TT-BTC p224-p235 | TÊN HỘ KINH DOANH | `required_band_mirror` | hkd | hkd_ten_tieng_viet_2 | [input/self] TÊN HỘ KINH DOANH; [mirror/self] Tên hộ kinh doanh (ghi bằng chữ in hoa):; [input/self] ĐĂNG KÝ THAY ĐỔI TÊN HỘ KINH DOANH (tên VN/NN/viết tắt sau t |
| PLII_M03 | 68/2025/TT-BTC p236 | TÊN HỘ KINH DOANH | `required_band_mirror` | hkd | hkd_ten_tieng_viet_2 | [input/self] TÊN HỘ KINH DOANH; [mirror/self] Tên hộ kinh doanh (ghi bằng chữ in hoa): |
| PLII_M04 | 68/2025/TT-BTC p237 | TÊN HỘ KINH DOANH | `required_band_mirror` | hkd | hkd_ten_tieng_viet_2 | [input/self] TÊN HỘ KINH DOANH; [mirror/self] Tên hộ kinh doanh (ghi bằng chữ in hoa): |
| PLII_M05 | 68/2025/TT-BTC p238 | TÊN HỘ KINH DOANH | `required_band_mirror` | hkd | hkd_ten_tieng_viet_2 | [input/self] TÊN HỘ KINH DOANH; [mirror/self] Tên hộ kinh doanh (ghi bằng chữ in hoa): |
| PLII_M06 | 68/2025/TT-BTC p239-p240 | TÊN HỘ KINH DOANH | `required_band_input` | hkd | hkd_ten_tieng_viet_2 | [input/self] TÊN HỘ KINH DOANH |
| PLII_M07 | 68/2025/TT-BTC p241 | — | `output_mirror` | hkd | hkd_ten_tieng_viet | [output/self] 1. Tên hộ kinh doanh / Tên hộ kinh doanh viết bằng tiếng Việ |
| PLII_M08 | 68/2025/TT-BTC p242 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M09 | 68/2025/TT-BTC p243 | — | `no_subject_band` | hkd | — | — |
| PLII_M10 | 68/2025/TT-BTC p244 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M11 | 68/2025/TT-BTC p245 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M12 | 68/2025/TT-BTC p246 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M13 | 68/2025/TT-BTC p247 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Tên hộ kinh doanh: |
| PLII_M14 | 68/2025/TT-BTC p248-p249 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Điều 1. Thu hồi ...: Tên hộ kinh doanh (ghi bằng chữ in hoa) |
| PLII_M15 | 68/2025/TT-BTC p250 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Điều 1. Thu hồi ...: Tên hộ kinh doanh (ghi bằng chữ in hoa) |
| PLII_M16 | 68/2025/TT-BTC p251 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Điều 1. Hủy bỏ QĐ thu hồi ...: Tên hộ kinh doanh (ghi bằng c |
| PLII_M17 | 68/2025/TT-BTC p252 | — | `no_subject_band` | none | — | — |
| PLII_M18 | 68/2025/TT-BTC p253 | — | `no_subject_band` | none | — | — |
| PLII_M19 | 68/2025/TT-BTC p254 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Yêu cầu (tên hộ kinh doanh): ... tạm ngừng kinh doanh ngành, |
| PLII_M20 | 68/2025/TT-BTC p255 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Tên hộ kinh doanh (ghi bằng chữ in hoa): |
| PLII_M21 | 68/2025/TT-BTC p256-p257 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M22 | 68/2025/TT-BTC p258 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M23 | 68/2025/TT-BTC p259 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M24 | 68/2025/TT-BTC p260 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Tên hộ kinh doanh (ghi bằng chữ in hoa): |
| PLII_M25 | 68/2025/TT-BTC p261 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh) |
| PLII_M26 | 68/2025/TT-BTC p262 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Tên hộ kinh doanh:; [narrative_gap/self] của ... (Tên hộ kinh doanh) – Mã số hộ kinh doanh (nếu có) |
| PLII_M27 | 68/2025/TT-BTC p263 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [output/self] Tên hộ kinh doanh: |
| PLII_M28 | 68/2025/TT-BTC p264-p265 | — | `output_mirror` | hkd | hkd_ten_tieng_viet_2 | [narrative_gap/self] Kính gửi: (Tên hộ kinh doanh); [output/self] - Tên hộ kinh doanh: |
| PLI_M01 | 121/2026/TT-BTC p5-p10 | — | `no_subject_band` | dn | dn.ten_tieng_viet | [input/self] Tên doanh nghiệp viết bằng tiếng Việt (ghi bằng chữ in hoa):; [input/self] Tên doanh nghiệp viết bằng tiếng nước ngoài (nếu có):; [input/self] Tên doanh nghiệp viết tắt (nếu có): |
| PLI_M02 | 121/2026/TT-BTC p11-p22 | — | `no_subject_band` | dn | dn.ten_tieng_viet | [input/self] Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):; [input/self] Tên công ty viết bằng tiếng nước ngoài (nếu có):; [input/self] Tên công ty viết tắt (nếu có): |
| PLI_M03 | 121/2026/TT-BTC p23-p31 | — | `no_subject_band` | dn | dn.ten_tieng_viet | [input/self] Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):; [input/other_subject] Tên doanh nghiệp (ghi bằng chữ in hoa): (bị chia/tách/hợp nh |
| PLI_M04 | 121/2026/TT-BTC p32-p41 | — | `no_subject_band` | dn | dn.ten_tieng_viet | [input/self] Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):; [input/other_subject] Tên doanh nghiệp (ghi bằng chữ in hoa): (bị chia/tách/hợp nh |
| PLI_M05 | 121/2026/TT-BTC p42-p48 | — | `no_subject_band` | dn | dn.ten_tieng_viet | [input/self] Tên công ty viết bằng tiếng Việt (ghi bằng chữ in hoa):; [input/self] Tên công ty viết bằng tiếng nước ngoài (nếu có):; [input/self] Tên công ty viết tắt (nếu có): |
| PLI_M06 | 68/2025/TT-BTC p47-p48 | — | `no_subject_band` | none | — | — |
| PLI_M07 | 68/2025/TT-BTC p49-p50 | — | `no_subject_band` | none | — | — |
| PLI_M08 | 68/2025/TT-BTC p51-p52 | — | `no_subject_band` | none | — | — |
| PLI_M09 | 68/2025/TT-BTC p53-p54 | — | `no_subject_band` | none | — | — |
| PLI_M10 | 121/2026/TT-BTC p49 | — | `no_subject_band` | none | — | [input/requester] 'Họ và tên' là cột cá nhân trong danh sách CSHHL (không phải |
| PLI_M11 | 68/2025/TT-BTC p56 | — | `no_subject_band` | none | — | — |
| PLI_M12 | 121/2026/TT-BTC p50-p66 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [mirror/other_subject] Tên doanh nghiệp (ghi bằng chữ in hoa): (DN bị sáp nhập/chia |
| PLI_M13 | 68/2025/TT-BTC p74-p75 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M14 | 68/2025/TT-BTC p76-p77 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/self] Đăng ký thay đổi tên doanh nghiệp tư nhân (đánh dấu X) + tên |
| PLI_M15 | 68/2025/TT-BTC p78-p80 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M17 | 68/2025/TT-BTC p83-p87 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh viết bằ |
| PLI_M18 | 68/2025/TT-BTC p88-p89 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M19 | 68/2025/TT-BTC p90-p99 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ |
| PLI_M21 | 68/2025/TT-BTC p102 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M23 | 68/2025/TT-BTC p111-p122 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh viết bằ |
| PLI_M25 | 68/2025/TT-BTC p123-p125 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M26 | 68/2025/TT-BTC p126 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M27 | 121/2026/TT-BTC p67-p69 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/branch_key] Tên chi nhánh/địa điểm kinh doanh (ghi bằng chữ in hoa): |
| PLI_M28 | 68/2025/TT-BTC p130-p131 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M29 | 68/2025/TT-BTC p132 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M30 | 121/2026/TT-BTC p70 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M31 | 68/2025/TT-BTC p134 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M32 | 68/2025/TT-BTC p135 | TÊN DOANH NGHIỆP | `required_band_mirror` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [mirror/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/requester] Tôi là1 (ghi họ tên bằng chữ in hoa): |
| PLI_M33 | 68/2025/TT-BTC p136-p137 | TÊN DOANH NGHIỆP | `required_band_input` | dn | dn.ten_tieng_viet | [input/self] TÊN DOANH NGHIỆP; [narrative_gap/self] của ............ (Tên Doanh nghiệp) – Mã số doanh nghiệp ... |
| PLI_M42 | 68/2025/TT-BTC p150 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] 1. Tên chi nhánh/văn phòng đại diện (ghi bằng chữ in hoa): |
| PLI_M43 | 68/2025/TT-BTC p151 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp/chi nhánh (ghi bằng chữ in hoa):; [output/branch_key] 1. Tên địa điểm kinh doanh (ghi bằng chữ in hoa): |
| PLI_M45 | 68/2025/TT-BTC p157-p158 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ |
| PLI_M46 | 68/2025/TT-BTC p158 | — | `no_subject_band` | none | — | — |
| PLI_M47 | 68/2025/TT-BTC p159 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] Kính gửi: (Tên doanh nghiệp); [output/other_subject] Tên Cơ quan thuế quản lý trực tiếp: |
| PLI_M48 | 68/2025/TT-BTC p160 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] về việc: .......... của (Tên doanh nghiệp) .......... |
| PLI_M49 | 68/2025/TT-BTC p161 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] (Đối với các trường hợp còn lại) ....... (Tên doanh nghiệp) ; [narrative_gap/self] về việc đăng ký/thông báo ... của (Tên doanh nghiệp) – Mã số |
| PLI_M50 | 68/2025/TT-BTC p162 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] Kính gửi: (Tên doanh nghiệp) |
| PLI_M51 | 68/2025/TT-BTC p163 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] Kính gửi: (Tên doanh nghiệp) |
| PLI_M52 | 68/2025/TT-BTC p164-p165 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] 1. Đối với doanh nghiệp: - Tên doanh nghiệp: |
| PLI_M53 | 68/2025/TT-BTC p166 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] Kính gửi: (Tên doanh nghiệp); [narrative_gap/self] Yêu cầu (tên doanh nghiệp): ... tạm ngừng kinh doanh ngành,  |
| PLI_M54 | 68/2025/TT-BTC p167 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M55 | 68/2025/TT-BTC p168 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ |
| PLI_M56 | 68/2025/TT-BTC p169-p170 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ; [output/branch_key] Tên chi nhánh chủ quản: |
| PLI_M57 | 68/2025/TT-BTC p171-p172 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh/địa điểm kinh doanh (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh chủ quản: |
| PLI_M63 | 68/2025/TT-BTC p181-p183 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ; [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa): |
| PLI_M66 | 68/2025/TT-BTC p191-p192 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp:; [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh: |
| PLI_M67 | 68/2025/TT-BTC p193 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] (tên doanh nghiệp) ...., mã số doanh nghiệp: ... (inline ngh |
| PLI_M68 | 68/2025/TT-BTC p194-p195 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp: |
| PLI_M69 | 68/2025/TT-BTC p196 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp: |
| PLI_M70 | 68/2025/TT-BTC p197 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] 01 bộ hồ sơ ... về việc: .......... của (Tên doanh nghiệp) . |
| PLI_M71 | 68/2025/TT-BTC p198 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] 01 bộ hồ sơ ... về việc: .......... của (Tên doanh nghiệp) . |
| PLI_M72 | 68/2025/TT-BTC p199-p206 | — | `output_mirror` | dn | dn.ten_tieng_viet | [subtitle/self] (TÊN DOANH NGHIỆP TƯ NHÂN) / (TÊN CÔNG TY TNHH MỘT THÀNH VIÊ; [output/self] 1. Tên doanh nghiệp / Tên doanh nghiệp viết bằng tiếng Việt: |
| PLI_M73 | 68/2025/TT-BTC p207 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] 1. Tên doanh nghiệp (tên tiếng Việt khi tiến hành đổi tên) + |
| PLI_M74 | 68/2025/TT-BTC p208 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] 1. Tên doanh nghiệp / Tên doanh nghiệp viết bằng tiếng Việt: |
| PLI_M75 | 68/2025/TT-BTC p209-p210 | — | `output_mirror` | dn | dn.ten_tieng_viet | [output/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [output/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ |
| PLI_M76 | 68/2025/TT-BTC p211 | — | `output_mirror` | dn | dn.ten_tieng_viet | [narrative_gap/self] Kính gửi: (Tên doanh nghiệp) |
| PLI_M78 | 68/2025/TT-BTC p213-p214 | — | `no_subject_band` | none | — | [input/requester] Tôi là (ghi họ tên bằng chữ in hoa): |
| PLI_M79 | 68/2025/TT-BTC p215-p216 | TÊN TỔ CHỨC | `no_subject_band` | dn | dn.ten_tieng_viet | [band_other/requester] TÊN TỔ CHỨC1 (tổ chức ĐỀ NGHỊ — KHÔNG phải band chủ thể); [input/self] Tên doanh nghiệp (ghi bằng chữ in hoa):; [input/branch_key] Tên chi nhánh/văn phòng đại diện/địa điểm kinh doanh (ghi bằ |
| PLI_M80 | 68/2025/TT-BTC p217-p218 | TÊN TỔ CHỨC | `no_subject_band` | dn | — | [band_other/requester] TÊN TỔ CHỨC1 (tổ chức ĐỀ NGHỊ — KHÔNG phải band chủ thể); [input/self] Tên doanh nghiệp/chi nhánh/văn phòng đại diện/địa điểm kinh  |

## Cross-check structural ↔ ảnh

- match: 86 form
- structural_band_only (xem structural_occurrences): 1 form

Ghi chú: các form GIẤY XÁC NHẬN/THÔNG BÁO do CQ cấp (M45, M54-M57, PLII_M20) có structural census cũ đánh dấu 'before-band' do band_end fallback — ảnh xác nhận KHÔNG có band; đã phân loại lại theo ảnh (output_mirror).

## Điểm unclear

- PLI_M03/M04: trang chứa mục '2. Tên công ty' ở thân không đọc trực tiếp toàn bộ (pattern M01/M02 + structural) — không ảnh hưởng role (đã xác minh KHÔNG band từ ảnh trang đầu)
- PLI_M42/M43: dòng 'Tên doanh nghiệp (ghi bằng chữ in hoa):' nằm dưới vùng crop đầu trang — xác minh bằng structural + tile bìa GCN (chứng từ CQ cấp)

## Đề xuất cho registry + detector lane

- Bổ sung output_mirrors: PLI_M47, PLI_M50, PLI_M51, PLI_M53, PLI_M71, PLI_M76, PLII_M26 (static '(Tên doanh nghiệp)/(Tên hộ kinh doanh)' chưa bind token)
- PLI_M80: bind dn.ten_tieng_viet vào fill-line 'Tên doanh nghiệp/chi nhánh/VPĐD/điểm KD (ghi bằng chữ in hoa):' (p218)
- output_mirrors đã có PLI_M48/PLI_M49/PLI_M70 — khớp ảnh
- Đề xuất cho detector lane: BAND_REQUIRED_MISSING cho 21 form required_band_mirror + 2 form required_band_input; BAND_FORBIDDEN_PRESENT cho 45 form output_mirror + 19 form no_subject_band (kể cả form có band 'TÊN TỔ CHỨC' — M79/M80: band khác chủ thể, KHÔNG được tính là band TÊN DN/HKD)
