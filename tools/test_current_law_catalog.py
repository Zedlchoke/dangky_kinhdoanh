# -*- coding: utf-8 -*-
"""F0L — gate catalog current-law (Lead).

Kiểm chứng trạng thái catalog sau L-2026 (owner decision 2026-09-06):

1. form_maps entry PLI_M11 phải mang marker ``current_law_status`` =
   ``REMOVED_BY_CURRENT_LAW`` (TT 121/2026/TT-BTC Điều 1 khoản 2, hiệu lực
   21/08/2026) — template/form_maps vẫn tồn tại chỉ để đọc draft cũ.
2. Không use case nào trong ``app/data/use_cases.json`` còn tham chiếu
   Mẫu Phụ lục I số 11 → không thể tạo hồ sơ mới bằng mẫu bị bãi bỏ
   (negative: nếu một case thêm ``{"pl": "I", "mau": 11}`` thì test đỏ).
3. Manifest census ghi rõ việc bãi bỏ theo văn bản hiện hành cho PLI_M11
   (nguồn verdict REMOVED_BY_CURRENT_LAW của coverage tool).
4. Hash 4 nguồn pháp lý khớp ``docs/legal_sources_2026/SOURCES.md``.
5. Ứng dụng không đăng ký PLI_M11 như form active: mọi ``forms``/``forms_oneOf``
   của 28 use case không chứa ``pl=I, mau=11`` (kiểm đệ quy toàn cây).
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
USE_CASES = ROOT / "app" / "data" / "use_cases.json"
MANIFEST = ROOT / "app" / "data" / "table_specs" / "manifest.json"
SOURCES_MD = ROOT / "docs" / "legal_sources_2026" / "SOURCES.md"
SOURCES_DIR = ROOT / "docs" / "legal_sources_2026"

TT121_SHA = "87f6989d209310b8c6fbec72a182c476bb83a462ce96d74c5218c26605342faf"

# trích từ tools/census/table_coverage_audit.py — ghi note "bãi bỏ theo
# văn bản" phải khớp ngữ pháp này để coverage kết luận REMOVED_BY_CURRENT_LAW
_RE_REMOVED_LAW = re.compile(
    r"(?i)(b[ãa]i\s*b[ỏo]|b[ỏo]\s*m[ụu]c|kh[oô]ng\s+c[òo]n\s+trong)\s+"
    r"(theo|b[ờı])\s*(ngh[ịı]\s*[đd][ịı]nh|th[ôo]ng\s*t[ưu]|v[ăa]n\s*b[ảa]n)")


def _walk_form_refs(node):
    """Sinh mọi dict form-ref {pl, mau} trong cấu trúc use case bất kỳdepth."""
    if isinstance(node, dict):
        if "pl" in node and "mau" in node:
            yield node
        else:
            for v in node.values():
                yield from _walk_form_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_form_refs(v)


class CurrentLawCatalog(unittest.TestCase):

    def test_01_m11_marker_trong_form_maps(self):
        fm = json.loads(FORM_MAPS.read_text(encoding="utf-8"))
        self.assertIn("PLI_M11", fm)
        st = fm["PLI_M11"].get("current_law_status")
        self.assertIsInstance(st, dict, "PLI_M11 thiếu current_law_status")
        self.assertEqual(st.get("status"), "REMOVED_BY_CURRENT_LAW")
        self.assertIn("121/2026", st.get("van_ban", ""))
        # các mẫu còn lại KHÔNG bị stamp removed
        for fid, meta in fm.items():
            if fid == "PLI_M11":
                continue
            cls = (meta.get("current_law_status") or {}).get("status")
            self.assertNotEqual(
                cls, "REMOVED_BY_CURRENT_LAW",
                "%s không thuộc danh sách bị bãi bỏ nhưng đang bị mark" % fid)

    def test_02_khong_use_case_nao_dung_mau_11(self):
        uc = json.loads(USE_CASES.read_text(encoding="utf-8"))
        offenders = [
            (case.get("id"), ref)
            for case in uc.get("cases", [])
            for ref in _walk_form_refs(case)
            if ref.get("pl") == "I" and int(ref.get("mau", -1)) == 11
        ]
        self.assertEqual(
            offenders, [],
            "Mẫu I số 11 đã bị TT 121/2026 bãi bỏ nhưng vẫn được tham chiếu: "
            "%s" % offenders)

    def test_03_use_case_hop_le_khong_mo_rong_mau_bi_bo(self):
        """Negative: chuỗi 'mau: 11' không được xuất hiện dưới dạng form-ref
        mới trong dữ liệu use case (chống reintroduce qua schema khác)."""
        raw = USE_CASES.read_text(encoding="utf-8")
        uc = json.loads(raw)
        dumps = json.dumps(uc, ensure_ascii=False)
        self.assertNotIn('"mau": 11,', dumps)
        self.assertNotIn('"mau":11,', dumps)

    def test_04_manifest_ghi_ro_bai_bo_theo_thong_tu(self):
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entry = next(f for f in m["forms"] if f["form_id"] == "PLI_M11")
        notes_all = json.dumps(entry, ensure_ascii=False)
        self.assertRegex(notes_all, _RE_REMOVED_LAW)
        self.assertIn("121/2026", notes_all)

    def test_05_hash_nguon_phap_ly_khop_sources_md(self):
        src = SOURCES_MD.read_text(encoding="utf-8")
        self.assertIn(TT121_SHA, src)
        pdf121 = SOURCES_DIR / "121-btc.signed.pdf"
        self.assertTrue(pdf121.exists(), "Thiếu file TT 121/2026 đã tải")
        digest = hashlib.sha256(pdf121.read_bytes()).hexdigest()
        self.assertEqual(
            digest, TT121_SHA,
            "SHA-256 TT 121/2026 lệch SOURCES.md — nguồn không còn nguyên")


if __name__ == "__main__":
    unittest.main()
