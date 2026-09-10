# -*- coding: utf-8 -*-
"""test_f7_notes.py — pin hai note của F7 final audit (2026-09-09) N3/N5.

Mệnh đề kiểm chứng:
  [F7-N3] `tools.census.table_coverage_audit` KHÔNG được in "wrote …" khi
          chạy `--no-write` (đã bỏ qua ghi) — log phải trung thực
          ("no-write: KHÔNG ghi … (chỉ verdict)"); nhánh ghi thường vẫn in
          "wrote <path>" và file phải tồn tại sau khi chạy (ghi vào path tạm,
          không đụng docs/ thật).
  [F7-N5] `phase5_visual_gate` inventory mặc định (`--forms all`) phải đi qua
          `resolve_form_inventory` -> `active_form_ids`: form mang marker
          current_law_status inactive (PLI_M11 REMOVED_BY_CURRENT_LAW) bị
          loại KHỎI corpus mặc định; render-unit = 90/fixture
          (85 form main + PLI_M72 × 5 variant) trên catalog hiện hành.

Chạy: python3 -X utf8 -m tools.test_f7_notes  (từ root repo)
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.census import table_coverage_audit as tca   # noqa: E402
from tools.phase5_visual_gate import (                  # noqa: E402
    M72_VARIANTS, MAPS_PATH, resolve_form_inventory,
)


def _maps_real() -> dict:
    return json.loads(MAPS_PATH.read_text(encoding="utf-8"))


class F7N3NoWriteLogTruthful(unittest.TestCase):
    """[F7-N3] log 'wrote' phải phản ánh đúng việc có ghi file hay không."""

    def test_no_write_does_not_claim_wrote(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = tca.main(["--no-write"])
        self.assertEqual(rc, 0, "gate phải PASS (no drift) tại HEAD")
        out = buf.getvalue()
        self.assertIn("no-write: KHÔNG ghi", out, out)
        self.assertIn("(chỉ verdict)", out, out)
        self.assertNotIn("wrote %s" % tca.OUT_JSON, out, out)
        self.assertNotIn("wrote %s" % tca.OUT_MD, out, out)

    def test_write_mode_still_reports_wrote(self):
        # Ghi vào path tạm (patch module globals) — không đụng docs/ thật
        # (docs/ được stamp head, ghi đè sẽ làm bẩn tree).
        tmp = Path(tempfile.mkdtemp(prefix="f7n3_"))
        old_json, old_md = tca.OUT_JSON, tca.OUT_MD
        tmp_json, tmp_md = tmp / "cov.json", tmp / "cov.md"
        tca.OUT_JSON, tca.OUT_MD = tmp_json, tmp_md
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = tca.main([])
            out = buf.getvalue()
        finally:
            tca.OUT_JSON, tca.OUT_MD = old_json, old_md
        self.assertEqual(rc, 0)
        self.assertIn("wrote %s" % tmp_json, out, out)
        self.assertIn("wrote %s" % tmp_md, out, out)
        self.assertTrue(tmp_json.exists() and tmp_md.exists())


class F7N5GateDefaultFiltersCurrentLaw(unittest.TestCase):
    """[F7-N5] default `--forms all` phải lọc theo active catalog."""

    def test_default_all_excludes_removed_by_current_law(self):
        form_ids, skipped = resolve_form_inventory(_maps_real(), "all")
        self.assertEqual(
            skipped, [("PLI_M11", "removed_by_current_law")],
            "đúng PLI_M11 bị loại theo current-law")
        self.assertNotIn("PLI_M11", form_ids)
        self.assertEqual(len(form_ids), len(_maps_real()) - 1)

    def test_default_all_yields_90_render_units_per_fixture(self):
        # Kỳ vọng DERIVED từ catalog hiện hành (86 active, M11 removed):
        # batch 'main' = mọi form active TRỪ PLI_M72; PLI_M72 × 5 variant.
        form_ids, _ = resolve_form_inventory(_maps_real(), "all")
        non72 = [f for f in form_ids if f != "PLI_M72"]
        m72_units = len(M72_VARIANTS) if "PLI_M72" in form_ids else 0
        render_units = len(non72) + m72_units
        self.assertEqual(len(M72_VARIANTS), 5)
        self.assertEqual(render_units, 90,
                         "86 active - M72 + 5 variant = 90 render-unit")

    def test_explicit_form_list_is_respected_verbatim(self):
        # escape hatch: truyền tay id thì dùng nguyên danh sách (re-shoot
        # cục bộ vẫn được phép render form bất kỳ, kể cả form đã removed).
        form_ids, skipped = resolve_form_inventory(
            _maps_real(), "PLI_M11, PLI_M70")
        self.assertEqual(form_ids, ["PLI_M11", "PLI_M70"])
        self.assertEqual(skipped, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
