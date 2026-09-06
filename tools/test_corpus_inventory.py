# -*- coding: utf-8 -*-
"""test_corpus_inventory.py — Lane C (F3): unit test inventory render-unit
động cho corpus cuối (phase8f).

Mệnh đề kiểm chứng:
  [MARKER]  current_law_status: entry KHÔNG có marker -> active (không skip);
            marker inactive (string hoặc dict {"status": ...}) -> skip;
            marker 'active'/rỗng -> active; trạng thái KHÔNG nhận diện ->
            fail-open (vẫn active) — chỉ owner chốt mới loại form.
  [INVEN]   active_form_ids đọc ĐỘNG từ form_maps thật: đủ 87 form hiện tại,
            KHÔNG kẹp cứng con số (87 là kết quả, không phải assertion);
            mô phỏng PLI_M11 inactive -> 86 active + PLI_M11 nằm trong skip.
  [FIXT]    render-unit = active × 5 fixture (empty-paper, valid-minimal,
            valid-full, long-boundary, choice-variants).
  [PIN]     tool export không pin số trang (grep source: không có 'page'
            pin/limit cứng) và không pin tổng số form cũ (assert 87 đã bị
            tháo — identity theo form_maps + manifest).

Chạy: python3 -X utf8 -m tools.test_corpus_inventory  (từ root repo)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.phase5_fixtures import (           # noqa: E402
    FIXTURES, active_form_ids, current_law_status,
)


def _maps_real() -> dict:
    return json_loads((ROOT / "app" / "data" / "form_maps.json"))


def json_loads(p: Path) -> dict:
    import json
    return json.loads(p.read_text(encoding="utf-8"))


class CurrentLawStatusMarker(unittest.TestCase):
    def test_absent_marker_is_active(self):
        # marker chưa tồn tại trong form_maps -> KHÔNG skip (không suy đoán)
        self.assertIsNone(current_law_status({"id": "PLI_M09"}))
        self.assertIsNone(current_law_status({}))

    def test_inactive_variants(self):
        for st in ("inactive", "removed", "repealed", "bo_loai",
                   "khoi_catalog"):
            self.assertEqual(current_law_status(
                {"current_law_status": st}), st)
            self.assertEqual(current_law_status(
                {"current_law_status": {"status": st}}), st)
        # chữ hoa / khoảng trắng vẫn nhận diện
        self.assertEqual(current_law_status(
            {"current_law_status": " Inactive "}), "inactive")

    def test_active_or_unknown_states(self):
        self.assertIsNone(current_law_status(
            {"current_law_status": "active"}))
        self.assertIsNone(current_law_status({"current_law_status": ""}))
        # trạng thái lạ -> KHÔNG inactive (fail-open)
        self.assertEqual(current_law_status(
            {"current_law_status": "pending_review"}), "pending_review")


class ActiveFormIdsInventory(unittest.TestCase):
    LOG = []

    def _log(self, line: str) -> None:
        self.LOG.append(line)

    def test_real_maps_all_active_and_count_not_hardcoded(self):
        maps = _maps_real()
        active, skipped = active_form_ids(maps)
        self.assertEqual(skipped, [], "form_maps hiện tại chưa có marker — "
                                      "không form nào được skip")
        self.assertEqual(active, sorted(maps))
        # kỳ vọng DERIVED từ form_maps (hôm nay = 87 form): khi owner chốt
        # marker cho PLI_M11 thì con số này tự theo maps, không phải pin test
        self.assertEqual(len(active), len(maps))
        self.assertNotIn("PLI_M11", [f for f, _s in skipped])

    def test_simulated_pli_m11_inactive_is_skipped_and_logged(self):
        maps = _maps_real()
        maps["PLI_M11"]["current_law_status"] = "inactive"
        self.LOG.clear()
        active, skipped = active_form_ids(maps, log=self._log)
        self.assertNotIn("PLI_M11", active)
        self.assertEqual(skipped, [("PLI_M11", "inactive")])
        self.assertEqual(len(active), 86)
        self.assertTrue(any("skip PLI_M11" in ln for ln in self.LOG),
                        "skip phải được ghi log: %r" % self.LOG)

    def test_unknown_marker_state_fails_open_with_log(self):
        maps = {"A": {}, "B": {"current_law_status": "weird_state"}}
        self.LOG.clear()
        active, skipped = active_form_ids(maps, log=self._log)
        self.assertEqual(active, ["A", "B"])  # fail-open: vẫn đưa vào corpus
        self.assertEqual(skipped, [])
        self.assertTrue(any("weird_state" in ln for ln in self.LOG))

    def test_render_units_times_five_fixtures(self):
        maps = _maps_real()
        maps["PLI_M11"]["current_law_status"] = "inactive"
        active, _skipped = active_form_ids(maps)
        render_units = len(active) * len(FIXTURES)
        self.assertEqual(len(FIXTURES), 5)
        self.assertEqual(render_units, 86 * 5)


class ExportToolPinAudit(unittest.TestCase):
    def test_export_tool_has_no_page_pins_and_no_87_pin(self):
        src = (ROOT / "tools" / "phase5_export_corpus.py").read_text(
            encoding="utf-8")
        self.assertNotIn("== 87", src, "không được pin tổng form cứng")
        # không pin số trang: tool không đụng pagination/page index
        for pat in (r"page[_-]?count\s*==", r"pages?\s*=\s*\d+",
                    r"\b1653\b", r"\b455\b"):
            self.assertIsNone(re.search(pat, src),
                              "tool export không được pin số trang/số "
                              "record cứng (pattern %r)" % pat)
        self.assertIn("phase8f", src, "corpus dir mới phải là phase8f, "
                                      "không đè phase7v")


if __name__ == "__main__":
    unittest.main(verbosity=1)
