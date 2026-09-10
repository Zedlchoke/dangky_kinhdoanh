# -*- coding: utf-8 -*-
"""Regression: nhãn email/website không được tách khỏi giá trị khi Word wrap."""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

from tools.docx_render import (
    _keep_contact_label_with_value,
    check_output,
    write_rendered,
)

ROOT = Path(__file__).resolve().parent.parent


def test_unit_split_runs() -> None:
    xml = (
        '<w:document><w:body><w:p><w:r><w:t>Điện thoại: 0900000025 '
        '</w:t></w:r><w:r><w:t>Thư điện tử</w:t></w:r>'
        '<w:r><w:t> (nếu có)</w:t></w:r><w:r>'
        '<w:t xml:space="preserve">: contact-rat-dai@example.com</w:t>'
        '</w:r><w:r><w:t> Website</w:t></w:r><w:r><w:t> (nếu có)</w:t></w:r>'
        '<w:r><w:t xml:space="preserve">: https://cong-ty-co-ten-mien-rat-dai.example.vn</w:t>'
        '</w:r></w:p></w:body></w:document>'
    )
    got = _keep_contact_label_with_value(xml)
    assert ":\u00a0contact-rat-dai@example.com" in got, got
    assert ":\u00a0https://cong-ty-co-ten-mien-rat-dai.example.vn" in got, got
    assert "Điện thoại: 0900000025" in got, got


def test_integration_plii_m02() -> None:
    form_id = "PLII_M02"
    fmap = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))[form_id]
    long_email = "bo-phan-ho-tro-khach-hang-va-ho-so-dang-ky-kinh-doanh@example.com"
    long_website = "https://cong-ty-co-ten-mien-rat-dai-cho-ho-kinh-doanh.example.vn"
    data = {
        "dien_thoai_khac": "0900000025",
        "dien_thoai_lien_he": "0900000025",
        "email_tru_so": long_email,
        "website": long_website,
    }
    tmp = Path(tempfile.mkdtemp(prefix="email_wrap_"))
    out = tmp / "PLII_M02.docx"
    write_rendered(ROOT / "app" / fmap["template"], data, out,
                   tables_meta=fmap.get("section_specs") or None)
    ok, message = check_output(out)
    assert ok, message
    with zipfile.ZipFile(out) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
    assert long_email in document_xml
    assert document_xml.count(":\u00a0" + long_email) >= 1, (
        "email vẫn có thể bị tách khỏi nhãn: %r" % long_email)
    assert document_xml.count(":\u00a0" + long_website) >= 1, (
        "website vẫn có thể bị tách khỏi nhãn: %r" % long_website)


def main() -> int:
    tests = (test_unit_split_runs, test_integration_plii_m02)
    failed = []
    for test in tests:
        try:
            test()
            print("PASS", test.__name__)
        except Exception as exc:  # noqa: BLE001
            failed.append((test.__name__, exc))
            print("FAIL", test.__name__, repr(exc))
    print("test_email_label_wrap: %d PASS / %d FAIL" %
          (len(tests) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
