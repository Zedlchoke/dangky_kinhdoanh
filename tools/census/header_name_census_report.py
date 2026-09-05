# Cập nhật note cho report: sinh /tmp/header_name_census_report.md từ JSON
import json, datetime

d = json.load(open("/tmp/header_name_census.json", encoding="utf-8"))
forms = d["forms"]
from collections import Counter
cls_cnt = Counter()
for v in forms.values():
    for o in v["occurrences"]:
        cls_cnt[o["classification"]] += 1

slot_rows = []
for fid, v in forms.items():
    for o in v["occurrences"]:
        if o["classification"] == "fillable-header-slot":
            keys = "; ".join(f"`{p['key']}`" for p in o["proposed_keys"]) or "—"
            flag = " ⚠ needs-owner" if "needs-owner" in o.get("note", "") else ""
            slot_rows.append((fid, o["text"], o["table_cell"] or f"para {o['para_idx']}",
                              keys, flag))

no_band = [fid for fid, v in forms.items() if v["no_band"]]

L = []
A = L.append
A("# HEADER-NAME CENSUS — 87 form đăng ký kinh doanh (Lane C, READ-ONLY)")
A("")
A(f"- Generated: {d['generated']}  |  base HEAD: `{d['base_head']}`  |  repo: repo root (tools/census/header_name_census.py)")
A("- Phạm vi: `word/document.xml` của 87 template `app/templates/<fid>.docx` (KHÔNG đụng `word/header*.xml` — các template không có header part riêng, band nằm trong body).")
A("- Định nghĩa band: các body element từ đầu tới tiêu đề biểu mẫu (regex ^GIẤY ĐỀ NGHỊ/^ĐƠN/^THÔNG BÁO/^BÁO CÁO/^CÔNG BỐ/^GIẤY TIẾP NHẬN/^GIẤY CHỨNG NHẬN/^GIẤY XÁC NHẬN/^DANH SÁCH/^QUYẾT ĐỊNH... , fold dấu) hoặc 25 element đầu — lấy min. Bảng band 2 cột (tên trái + quốc hiệu phải) tính là band. Dòng logic tách theo `<w:br/>`.")
A("- Literal lookup: fold hoa/thường + dấu theo 12 pattern nhiệm vụ (\"Họ và tên\" chỉ tính trong band).")
A("")
A("## 1. Tóm tắt theo classification (216 occurrence / 87 form)")
A("")
A("| Classification | Số occurrence | Số form | Ý nghĩa |")
A("|---|---|---|---|")
A(f"| **fillable-header-slot** | {cls_cnt['fillable-header-slot']} | {len(slot_rows)} | band tên chủ thể + fill-line, CHƯA bind token → cần mirror canonical key |")
A(f"| already-bound (band) | {cls_cnt['already-bound']} | 0 | KHÔNG form nào có band tên đã bind token |")
A(f"| output-admin-only | {cls_cnt['output-admin-only']} | — | tên chủ thể là nội dung output của cơ quan (giấy chứng nhận/xác nhận/quyết định/thông báo/công bố/giấy tiếp nhận), đã hoặc chưa bind |")
A(f"| legal-title/subtitle | {cls_cnt['legal-title/subtitle']} | — | nhãn câu hỏi thân (đa số đã bind), tiêu đề mục, subtitle loại hình — ngoài band |")
A(f"| not-applicable | {cls_cnt['not-applicable']} | — | prose/chú thích nhắc cụm tên; tiêu đề cột bảng danh sách (M10 \"Họ và tên\") |")
A("")
A(f"- **{len(slot_rows)} form có fillable-header-slot** (cần mirror): 17 form DN (PLI_M13–M33) + 5 form hộ (PLII_M02–M06).")
A(f"- **{len(no_band)} form không có band tên chủ thể nào** (band chỉ có quốc hiệu/Số/ngày hoặc là form danh sách/output): `{'` `'.join(sorted(no_band))}`.")
A("- RED FLAG `template-lost-signature` (nguồn CÓ cụm ký mà template MẤT): **KHÔNG có form nào** trong cả 87 form khảo sát nguồn 9 mẫu no-signature.")
A("")
A("## 2. Bảng 22 form fillable-header-slot → proposed key")
A("")
A("Band của cả 22 form cùng một kiểu: bảng đầu trang 2 ô, ô trái label + dòng gạch `-------` (2 run 1 paragraph tách `<w:br/>`), ô phải quốc hiệu; label nằm **cùng hàng** với quốc hiệu (`quoc_hieu_pos = same-band`); không ô nào có token.")
A("")
A("| Form | Band label | Vị trí | Proposed key | Ghi chú |")
A("|---|---|---|---|---|")
for fid, text, loc, keys, flag in slot_rows:
    A(f"| {fid} | {text} | `{loc}` | {keys} |{flag} |")
A("")
A("### Ghi chú riêng")
A("- **PLI_M32**: owner đã chỉ định mirror `chu_hkd.ho_ten` (thân: \"Tôi là (ghi họ tên bằng chữ in hoa): {chu_hkd.ho_ten}\" — para 7). Literal \"TÊN DOANH NGHIỆP\" cũng khớp `dn.ten_tieng_viet` (para 16) — liệt kê làm alternative, cần owner chốt.")
A("- **PLI_M33** ⚠ needs-owner: form kiểu M32 nhưng **không có input tên DN nào ở thân** (fields chỉ có `chu_hkd.ho_ten`). Options: (a) mirror `chu_hkd.ho_ten`; (b) thêm input tên DN mới nếu muốn band đúng literal.")
A("- **PLII_M06** ⚠ needs-owner: band \"TÊN HỘ KINH DOANH\" nhưng thân không có input tên hộ; thân chỉ có `chu_hkd.ho_ten` + nhãn không bind \"Là chủ hộ kinh doanh (Tên hộ kinh doanh) .....\" (para 22). Options: (a) mirror `chu_hkd.ho_ten`; (b) bổ sung key tên hộ.")
A("- PLII_M02–M05: key đề xuất `hkd_ten_tieng_viet_2` = key đang bind ở nhãn \"Tên hộ kinh doanh (ghi bằng chữ in hoa)\" ngay đầu thân. Riêng PLII_M02, các field tên SAU thay đổi đã bind qua token-đoạn-cách-dòng (`{hkd_ten_tieng_viet}`, `{hkd_ten_tieng_nuoc}`, `{hkd_ten_viet_tat}` ở para 18/20/22) — khác key, không thuộc phạm vi band.")
A("- 17 form DN: `dn.ten_tieng_viet` đều là key bind ở nhãn \"Tên doanh nghiệp (ghi bằng chữ in hoa)\" 2–5 element sau band (PLI_M25 nhãn dài \"Tên doanh nghiệp/Tên chi nhánh ...\"). Đã verify token tồn tại trong document.xml của từng form.")
A("")
A("## 3. Nhóm output-admin-only (88) — form do cơ quan phát hành")
A("")
A("Gồm 44 form output (Giấy chứng nhận/Giấy xác nhận/Quyết định/Thông báo của CQĐKKD/Công bố 72–74/Giấy tiếp nhận M70–M71, PLII_M17–M18): tên chủ thể trong thân là nội dung được in ra. 85/88 occurrence đã bind token (`dn.ten_tieng_viet`, `hkd_ten_tieng_viet_2`, `yeu_cau_dn`...).")
A("")
A("**3 ô output chưa bind — needs-owner (cân nhắc bind khi render, không thuộc sync band):**")
A("")
A("| Form | Para | Dòng |")
A("|---|---|---|")
for fid, v in forms.items():
    for o in v["occurrences"]:
        if o["classification"] == "output-admin-only" and "CHƯA bind" in o.get("note", ""):
            A(f"| {fid} | {o['para_idx']} | `{o['text'][:90]}` |")
A("")
A("- Đặc biệt **PLI_M70 vs PLI_M71**: M70 (bản nộp trực tiếp) có bảng ký 2 ô `NGƯỜI NỘP (Ký và ghi họ tên) | NGƯỜI NHẬN (Ký và ghi họ tên)` — section_spec `chu_ky_nguoi_nop_nguoi_nhan`; M71 (qua mạng điện tử) chỉ có bảng 1 ô `(TÊN CƠ QUAN ĐĂNG KÝ KINH DOANH CẤP TỈNH)` — section_spec `chu_ky_co_quan_cap_tinh`. Bảng ký cơ quan thuộc **M71**, không phải M70; đúng theo `tools/form_specs/publication/PLI_M71.json`.")
A("")
A("## 4. 9 FORM KHÔNG CÓ CỤM KÝ — verdict")
A("")
A("| Form | Nguồn gốc (find_source) | Nguồn có chỉ thị ký | Template có chỉ thị ký | Verdict |")
A("|---|---|---|---|---|")
VERDICT_SHORT = {
    "PLII_M18": "absence-correct",
    "PLI_M05": "absence-correct",
    "PLI_M07": "absence-correct (nguồn-stub)",
    "PLI_M10": "absence-correct",
    "PLI_M71": "absence-correct",
    "PLI_M72": "absence-correct",
    "PLI_M73": "absence-correct",
    "PLI_M74": "absence-correct",
    "PLI_M76": "absence-correct",
}
for fid, ns in d["no_signature_forms"].items():
    A(f"| {fid} | `{ns['source_file']}` | {ns['source_has_signature_directive']} | {ns['template_has_signature']} | **{VERDICT_SHORT[fid]}** |")
A("")
A("*(\"có chỉ thị ký\" = chỉ đếm cụm chỉ thị ký thật: \"Ký và ghi rõ họ tên\", \"Ký, ghi họ tên và đóng dấu\", \"Ký tên\", \"Đã ký\", \"Người khai\", \"Người nộp\", \"Ngày...ký\". Các phrase \"Người đại diện\"/\"Chủ hộ\" chỉ khớp NHÃN TRƯỜNG DỮ LIỆU/tiêu đề mục ở M05/M10/M72 — không phải khối ký; chi tiết ở từng form bên dưới. JSON giữ cả hai cờ: `source_has_signature` = khớp thô theo danh sách phrase nhiệm vụ, `source_has_signature_directive` = chỉ thị ký thật.)*")
A("")
A("**RED FLAG `template-lost-signature`: không có.** Chi tiết từng form + bằng chứng:")
A("")
for fid, ns in d["no_signature_forms"].items():
    A(f"### {fid} — {VERDICT_SHORT[fid]}")
    A("")
    A(f"- Nguồn: `{ns['source_file']}`")
    A(f"- Nguồn khớp phrase danh sách nhiệm vụ: {ns['source_has_signature']} | Chỉ thị ký THẬT ở nguồn: {ns['source_has_signature_directive']} | Template có chỉ thị ký: {ns['template_has_signature']}")
    A(f"- Tính chất: {ns['notes']}")
    A(f"- 3 dòng cuối nguồn (bằng chứng):")
    A("")
    for l in ns["evidence_tail"]:
        A(f"  > {l[:200]}")
    A("")
A("### Ghi chú bổ sung cụm ký")
A("- **PLI_M70/M71**: `chu_ky_co_quan_cap_tinh` nằm trong `app/data/form_maps.json` → `section_specs` của **PLI_M71** (không phải M70); M70 dùng `chu_ky_nguoi_nop_nguoi_nhan`. Cả hai là output-table render lúc runtime, không phải cụm ký bị mất trong docx.")
A("- **PLI_M72**: kiểm đủ 5 biến thể (DNTN, TNHH 1TV, TNHH 2TV+; CTCP, hợp danh — 5 khối \"Nơi đăng ký\" ở cả nguồn lẫn template): không biến thể nào có chỉ thị ký. Nguồn ↔ template khớp.")
A("- **PLI_M07**: nguồn gốc là **stub 2 dòng** (caption + \"Mẫu số 7\"); template tự dựng bảng + cột `Chữ ký {chu_ky}` — chiều ngược (template CÓ thêm phần ký so với nguồn, không phải mất). Cảnh báo cho Lead regen: nguồn M07 không đủ để tái sinh template.")
A("- **PLI_M10**: cụm \"Người đại diện theo pháp luật ... ký trực tiếp\" là chú thích mồ côi (footnote 15) tồn tại ở CẢ nguồn và template — không phải khối ký.")
A("- **PLI_M05**: các hit \"người đại diện\"/\"chủ hộ\" là nhãn trường dữ liệu, có y hệt ở template.")
A("")
A("## 5. Danh sách 65 form không có band tên (`no_band = true`)")
A("")
A(f"`{'` `'.join(sorted(no_band))}`")
A("")
A("---")
A("Sinh tự động bởi Lane C (read-only); dữ liệu thô: `/tmp/header_name_census.json`; script: `/tmp/census_work/`.")

open("/tmp/header_name_census_report.md", "w", encoding="utf-8").write("\n".join(L))
print("WROTE /tmp/header_name_census_report.md", len(L), "lines")
