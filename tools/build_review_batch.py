#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tạo lô nhỏ DOCX/XLSX để owner duyệt giao diện thủ công.

Chỉ dùng fixture giả ngữ nghĩa và ĐÚNG engine exporter production. Không ghi
đè output cũ, không cần LibreOffice và không thay thế visual QA PDF/PNG.

Chạy:
  python -X utf8 -m tools.build_review_batch
"""
from __future__ import annotations

import json
import sys
import zipfile
from datetime import date
from pathlib import Path

from tools.docx_render import write_rendered
from tools.excel_export import write_questionnaire
from tools.phase5_fixtures import build_fixture, validate_fixture

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "generated_ho_so" / "review_forms_20260910"

# Bốn mẫu đại diện cho các form phổ biến và những layout khó: hộ kinh doanh,
# thay đổi HKD, bảng ngành/thuế DN và khối ngày-ký/tạm ngừng.
SAMPLES = (
    ("01_PLII_M01_dang_ky_ho_kinh_doanh.docx", "PLII_M01", "valid-full"),
    ("02_PLII_M02_thay_doi_ho_kinh_doanh.docx", "PLII_M02", "choice-variants"),
    ("03_PLI_M12_thay_doi_nganh_nghe.docx", "PLI_M12", "valid-full"),
    ("04_PLI_M27_tam_ngung_doanh_nghiep.docx", "PLI_M27", "long-boundary"),
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if OUT_DIR.exists():
        print("Từ chối ghi đè lô review đã có: %s" % OUT_DIR)
        return 2
    OUT_DIR.mkdir(parents=True)

    maps = load_json(ROOT / "app" / "data" / "form_maps.json")
    manifest: list[dict] = []
    try:
        for filename, form_id, fixture in SAMPLES:
            fmap = maps[form_id]
            blocks = load_json(ROOT / "app" / "data" / "blocks" / (form_id + ".json"))
            data = build_fixture(form_id, fmap, fixture, blocks=blocks)
            errors = validate_fixture(fmap, blocks, data, fixture)
            if errors:
                raise ValueError("%s fixture lỗi: %s" % (form_id, "; ".join(errors)))

            output = OUT_DIR / filename
            write_rendered(ROOT / "app" / fmap["template"], data, output,
                           tables_meta=fmap.get("section_specs") or None)
            manifest.append({
                "file": filename,
                "form_id": form_id,
                "form_name": fmap.get("ten_mau", form_id),
                "fixture": fixture,
                "data_is_fake": True,
            })

        # Excel production hiện mới theo form; đưa M12 làm ví dụ khách điền.
        q = load_json(ROOT / "app" / "data" / "questionnaire" / "PLI_M12.json")
        excel_name = "05_Excel_khach_dien_PLI_M12.xlsx"
        write_questionnaire(q, OUT_DIR / excel_name, meta={
            "case_id": "review_thay_doi_nganh_nghe",
            "today": date.today().strftime("%d/%m/%Y"),
        })
        manifest.append({
            "file": excel_name,
            "form_id": "PLI_M12",
            "form_name": "Phiếu Excel khách điền — thay đổi ngành nghề",
            "fixture": "blank-client-workbook",
            "data_is_fake": True,
        })

        note = (
            "# Lô mẫu để duyệt\n\n"
            "- Các DOCX dùng dữ liệu giả, không được nộp hoặc gửi khách thật.\n"
            "- Mở từng DOCX trong Microsoft Word và ghi rõ: tên file, số trang, "
            "vị trí lỗi, ảnh chụp và nhận xét.\n"
            "- Kiểm: header, ngày/tháng/năm, dấu tick, bảng rộng, hàng lặp, "
            "chữ ký và khoảng trắng/tách trang.\n"
            "- Excel là file trống đúng luồng hiện tại: kiểm màu ô, dropdown, "
            "cột, hàng bảng và hướng dẫn.\n"
            "- Không có PDF/PNG QA trong lô này vì máy hiện chưa có LibreOffice "
            "(`soffice`).\n"
        )
        (OUT_DIR / "README.md").write_text(note, encoding="utf-8")
        (OUT_DIR / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        archive = OUT_DIR.parent / (OUT_DIR.name + ".zip")
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(OUT_DIR.iterdir()):
                zf.write(path, path.name)
    except Exception:
        # Không xoá output lỗi: giữ nguyên để điều tra, không gây mất evidence.
        raise

    print("Đã tạo %d artifact tại %s" % (len(manifest), OUT_DIR))
    print("ZIP: %s" % archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
