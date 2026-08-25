# tools/form_specs/ — spec bảng tái dựng (rebuild) theo từng mẫu

Mỗi file `<nhóm>/<FORM_ID>.json` mô tả **trọn vẹn** cấu hình tái dựng bảng danh
sách bị mất lưới khi convert cho một mẫu. `tools/build_form_maps.py` ưu tiên
đọc file spec này; **không có file thì fallback** về khai báo inline
`REBUILD_TABLES` / `DYNAMIC_TABLES` như trước (byte-identical với các mẫu đã
chuyển: `core/PLI_M02.json`, `core/PLII_M01.json`).

Nhóm: `formation` (thành lập) · `change` (thay đổi/bổ sung) · `household`
(hộ kinh doanh) · `core` (spec chuẩn đã chuyển từ inline).

## Schema

```jsonc
{
  "form_id": "PLI_M02",          // phải khớp tên file
  "group": "core",               // thư mục chứa file (tham khảo, loader không dùng)
  "note": "...",                 // ghi chú kỹ thuật cho người đọc
  "gap_nghiepvu": null | "...",  // gap nghiệp vụ cần agent nhóm/Lead review;
                                 // build sẽ print dòng "[form_specs] <id> GAP NGHIEPVU: ..."
  "tables": [                    // một mẫu có thể có NHIỀU bảng (vd PLI_M12 có 3 lưới)
    {
      "spec": {                  // định nghĩa bảng động — cùng hình dạng phần tử DYNAMIC_TABLES
        "id": "ds_nganh_vsic",   // id spec, duy nhất trong file
        "detect": ["stt", "ma nganh", "ten nganh theo vsic"],
                                 // token FOLD (thường, bỏ dấu) phải khớp TRONG KHÔNG
                                 // thiếu so với tập header sau khi fold — nếu thiếu,
                                 // _build_list_table raise ValueError
        "stt_tag": true,         // true = cột STT gắn {_stt} (engine tự sinh số 1-based)
        "cols": [                // [regex_trên_header_folded, tag] — tag null = không gắn the;
                                 // regex khớp đầu tiên thắng, khai theo thứ tự cột
          ["^stt$", null],
          ["^ma nganh", "ma_nganh"]
        ],
        "loop": "ds_nganh",      // tên loop docxtemplater {#loop}...{/loop}
        "fields": ["ma_nganh"]   // tag đăng ký vào form_maps.fields dạng "<loop>.<tag>"
      },
      "pos": "after",            // after | before (mặc định after)
      "anchor": "^4\\. nganh, nghe kinh doanh",
                                 // regex trên text ĐÃ FOLD của paragraph — điểm chèn bảng
      "headers": ["STT", "Mã ngành"],   // tiêu đề cột của bảng MỚI (in đậm)
      "no_default_drops": true,  // tắt drop toàn-văn-bản mặc định (^stt.{40,}, ^\d{5,}$)
                                 // — bật cho mọi mẫu có lưới khác dùng ô STT rời
      "drop_until": "^5\\. chu so huu",
                                 // có drop_until => drop chỉ áp trong vùng
                                 // (sau anchor -> trước drop_until) thay vì toàn văn bản
      "drop": ["^stt$", "..."],  // regex xóa paragraph tàn dư lưới cũ
      "trim": ["^sttho ten"],    // cắt paragraph dính chữ: giữ phần từ keep_from
      "keep_from": "Tôi xin cam kết"
    }
  ]
}
```

Quy tắc regex trong file JSON: escape đúng kiểu JSON (`"\\d"`, `"\\."`,
`"\\b"` — đừng dùng `"\b"` vì đó là backspace). Loader đọc bằng `utf-8-sig`
nên chịu được BOM.

## Quy trình cho agent Wave 2 (2A/2B/2C)

1. Spec ds_nganh của 13 mẫu đã tạo sẵn theo template thật. Đọc `gap_nghiepvu`
   của từng file (build cũng in ra) và xử lý gap thuộc nhóm mình.
2. Chạy thử riêng một mẫu (ghi đè entry form_maps + template):
   `python -X utf8 -m tools.build_form_maps --one PLI_M12`
3. Sinh lại blocks + audit:
   `python -X utf8 tools/docx_to_blocks.py` rồi
   `python -X utf8 tools/audit_blocks_check.py`.
4. Sửa spec = sửa file JSON của mẫu đó rồi chạy lại bước 2-3. **Không** sửa
   dictionary Python; chỉ đụng file nhóm mình để tránh conflict merge.
5. Sau khi cả 3 nhóm merge đủ loop mới, cập nhật kỳ vọng tổng số block loop
   trong `tools/audit_blocks_check.py` (hiện cố định = 9).

Lưu ý: `--one <FORM_ID>` tìm nguồn qua `iter_docx_files()` — các mẫu thành lập
PLI_M01..M05 lấy nguồn từ `06_ho_kinh_doanh_va_chuyen_doi/02_chuyen_doi_hkd_sang_dn/DN_PL1_Mau_*.docx`
(thư mục `01_…` hiện không có trong repo).
