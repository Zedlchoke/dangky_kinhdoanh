# -*- coding: utf-8 -*-
"""test_corpus_ai_review.py — Lane C (F5/O5): unit test khung AI review.

Dựng corpus GIẢ dạng phase7v trong tmp (manifest.json + PNG nhỏ vẽ bằng PIL,
fallback pymupdf nếu thiếu PIL), rồi kiểm chứng tools/corpus_ai_review.py:

  [INIT]   --init tạo review_manifest.json: đủ record, mọi checklist item
           PENDING, KHÔNG verdict nào được sinh sẵn.
  [CHECK]  checklist đủ 7 hạng mục chuẩn (signature/header/wide-table/
           footnote/checkbox/name-date glue/blank-trailing), PNG thiếu được
           flag chứ không im lặng.
  [SET]    ghi verdict AI_REVIEWED_PASS/FAIL + reason + page cho ĐÚNG 1
           record, kèm sha256 từng PNG; reason rỗng bị từ chối.
  [GUARD]  verdict ngoài whitelist (HUMAN_REVIEWED, HUMAN_PASS, NOT_REVIEWED)
           và reason chứa token human-* đều BỊ TỪ CHỐI, không ghi đĩa.
  [STALE]  sửa PNG sau khi verdict → --verify báo stale; PNG nguyên → ok.
  [CLI]    chạy module qua command line thật (--init/--set/--summary).

Chạy: python3 -X utf8 -m tools.test_corpus_ai_review  (từ root repo)
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.corpus_ai_review as car  # noqa: E402


def _small_png(path: Path, width: int = 64, height: int = 40,
               color=(255, 255, 255)) -> None:
    """PNG nhỏ trong tmp: PIL trước, pymupdf fallback, cuối cùng là byte
    PNG tối thiểu tự dựng (đủ để hash, không cần giải mã)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        Image.new("RGB", (width, height), color).save(path, format="PNG")
        return
    except ImportError:
        pass
    try:
        import pymupdf  # noqa: F401
        doc = pymupdf.open()
        page = doc.new_page(width=width, height=height)
        pix = page.get_pixmap(dpi=36)
        pix.save(str(path))
        doc.close()
        return
    except ImportError:
        pass
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)


def make_fake_corpus(tmp: Path, forms=(("PLI_M09", "valid-full"),
                                       ("PLI_M01", "empty-paper"))) -> Path:
    corpus = tmp / "corpus"
    records = []
    for form, fixture in forms:
        png_dir = corpus / fixture / "main" / form
        pages = []
        for i in (1, 2):
            name = "page-%02d.png" % i
            _small_png(png_dir / name, color=(240 + i, 240, 250))
            pages.append(str((png_dir / name).resolve()))
        records.append({
            "form": form, "fixture": fixture, "tag": "main", "variant": "",
            "dir": str(png_dir.parent),
            "template": "templates/%s.docx" % form,
            "template_hash": "0" * 64,
            "page_count": len(pages),
            "pages": pages,
            "png_dir": str(png_dir),
            "detectors": {"D6_signature": {"fails": [], "candidates": []},
                          "D11_glue": [], "D11_glue_count": 0},
            "gate_verdict": "PASS_CANDIDATE_REVIEW",
            "reviewer_verdict": "NOT_REVIEWED",
        })
    (corpus / "manifest.json").write_text(
        json.dumps({"generated": "20990101_000000",
                    "fixtures": ["empty-paper", "valid-full"],
                    "forms": sorted({f for f, _ in forms}),
                    "records": records}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return corpus


class CorpusAiReview(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ai_review_test_"))
        self.corpus = make_fake_corpus(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------- [INIT]
    def test_init_creates_pending_skeleton(self):
        out = car.init_review_manifest(self.corpus)
        self.assertEqual(out["records_total"], 2)
        self.assertEqual(out["added"], 2)
        rv = json.loads((self.corpus / car.REVIEW_FILENAME)
                        .read_text(encoding="utf-8"))
        self.assertEqual(rv["_format"], car.REVIEW_FORMAT)
        self.assertEqual(len(rv["records"]), 2)
        for entry in rv["records"].values():
            self.assertEqual(entry["verdict"], car.PENDING)
            ids = [c["id"] for c in entry["checklist"]]
            self.assertEqual(ids, [i[0] for i in car.CHECKLIST_ITEMS])
            for item in entry["checklist"]:
                self.assertEqual(item["status"], car.PENDING)
                self.assertIsNone(item["page"])
        # init lần 2 phải idempotent (không nhân đôi record)
        out2 = car.init_review_manifest(self.corpus)
        self.assertEqual((out2["added"], out2["already"]), (0, 2))

    def test_checklist_flags_missing_png(self):
        # xoá 1 PNG -> checklist phải flag png_missing, không im lặng
        rec_key = "PLI_M01|empty-paper|main|"
        pages = json.loads((self.corpus / "manifest.json")
                           .read_text(encoding="utf-8"))["records"]
        target = next(r for r in pages if car.record_key(r) == rec_key)
        Path(target["pages"][0]).unlink()
        chk = car.build_checklist(target, self.corpus)
        self.assertEqual(len(chk["png_missing"]), 1, chk["png_missing"])

    def test_init_refreshes_metadata_keeps_verdicts(self):
        car.init_review_manifest(self.corpus)
        car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                        car.VERDICT_PASS, "OK theo anh", page=1)
        # làm hỏng metadata: xoá PNG để png_missing phải được tính lại khi init
        target = self.corpus / "valid-full" / "main" / "PLI_M09" / "page-01.png"
        digest_before = target.read_bytes()
        target.unlink()
        car.init_review_manifest(self.corpus)
        rv = json.loads((self.corpus / car.REVIEW_FILENAME)
                        .read_text(encoding="utf-8"))
        entry = rv["records"]["PLI_M09|valid-full|main|"]
        self.assertEqual(len(entry["png_missing"]), 1,
                         "init phải làm mới png_missing")
        self.assertEqual(entry["verdict"], car.VERDICT_PASS,
                         "init không được đụng verdict đã ghi")
        self.assertEqual(entry["png_sha256"]["page-01.png"],
                         __import__("hashlib").sha256(digest_before).hexdigest())
        target.write_bytes(digest_before)  # khôi phục cho các test khác

    # -------------------------------------------------------------- [SET]
    def test_set_verdict_records_hash_and_reason(self):
        car.init_review_manifest(self.corpus)
        out = car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                              car.VERDICT_FAIL,
                              "Bang 14 cot le cot 13, header chong dong",
                              page=2)
        self.assertEqual(out["pages_hashed"], 2)
        rv = json.loads((self.corpus / car.REVIEW_FILENAME)
                        .read_text(encoding="utf-8"))
        entry = rv["records"]["PLI_M09|valid-full|main|"]
        self.assertEqual(entry["verdict"], car.VERDICT_FAIL)
        self.assertEqual(entry["verdict_page"], 2)
        self.assertIn("le cot 13", entry["verdict_reason"])
        self.assertEqual(len(entry["png_sha256"]), 2)
        for name, digest in entry["png_sha256"].items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertTrue(name.startswith("page-"))
        # record kia vẫn PENDING — không PASS/FAIL lan
        self.assertEqual(rv["records"]["PLI_M01|empty-paper|main|"]["verdict"],
                         car.PENDING)

    def test_set_verdict_requires_reason(self):
        car.init_review_manifest(self.corpus)
        with self.assertRaises(ValueError):
            car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                            car.VERDICT_PASS, "   ")

    def test_set_verdict_unknown_record(self):
        with self.assertRaises(SystemExit):
            car.set_verdict(self.corpus, "NO_SUCH", "valid-full",
                            car.VERDICT_PASS, "x")

    # ------------------------------------------------------------ [GUARD]
    def test_guard_rejects_human_verdicts_and_tokens(self):
        car.init_review_manifest(self.corpus)
        before = (self.corpus / car.REVIEW_FILENAME).read_text(encoding="utf-8")
        for bad in ("HUMAN_REVIEWED", "HUMAN_PASS", "human-reviewed",
                    "NOT_REVIEWED", "human_pass"):
            with self.assertRaises(ValueError, msg=bad):
                car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                                bad, "reason")
        with self.assertRaises(ValueError):
            car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                            car.VERDICT_PASS, "duyet theo HUMAN_PASS cua lead")
        # đĩa không đổi sau toàn bộ các lần bị chặn
        after = (self.corpus / car.REVIEW_FILENAME).read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_guard_blocks_human_token_in_saved_file(self):
        rv = car.load_review_manifest(self.corpus)
        rv["records"]["evil|manual-patch|main|"] = {"verdict": "HUMAN_PASS"}
        with self.assertRaises(ValueError):
            car.save_review_manifest(self.corpus, rv)

    # ------------------------------------------------------------ [STALE]
    def test_verify_detects_stale_png(self):
        car.init_review_manifest(self.corpus)
        car.set_verdict(self.corpus, "PLI_M09", "valid-full",
                        car.VERDICT_PASS, "Trang doc giong mau", page=1)
        res = car.verify_review_manifest(self.corpus)
        self.assertEqual(res["stale"], [])
        self.assertEqual(res["verdicted"], 1)
        self.assertEqual(res["pending"], 1)
        # sửa PNG sau verdict -> stale
        target = self.corpus / "valid-full" / "main" / "PLI_M09" / "page-01.png"
        _small_png(target, color=(10, 20, 30))
        res2 = car.verify_review_manifest(self.corpus)
        self.assertEqual(len(res2["stale"]), 1)
        self.assertEqual(res2["stale"][0]["key"], "PLI_M09|valid-full|main|")
        self.assertEqual(res2["stale"][0]["changed"], ["page-01.png"])

    # -------------------------------------------------------------- [CLI]
    def test_cli_init_set_summary(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = car.main(["--corpus", str(self.corpus), "--init"])
        self.assertEqual(rc, 0)
        self.assertIn('"added": 2', buf.getvalue())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = car.main(["--corpus", str(self.corpus), "--set",
                           "--form", "PLI_M01", "--fixture", "empty-paper",
                           "--verdict", car.VERDICT_PASS,
                           "--reason", "Giay trang khong loi",
                           "--page", "1"])
        self.assertEqual(rc, 0)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = car.main(["--corpus", str(self.corpus), "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn('"AI_REVIEWED_PASS": 1', buf.getvalue())
        self.assertIn('"pending": 1', buf.getvalue())

    def test_cli_rejects_disallowed_verdict_choice(self):
        car.init_review_manifest(self.corpus)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                car.main(["--corpus", str(self.corpus), "--set",
                          "--form", "PLI_M09", "--fixture", "valid-full",
                          "--verdict", "HUMAN_PASS", "--reason", "x"])
        self.assertIn("invalid choice", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=1)
