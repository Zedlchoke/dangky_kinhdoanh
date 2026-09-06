# -*- coding: utf-8 -*-
"""corpus_ai_review.py — khung ghi nhận AI review cho corpus visual phase7v+
(F5/O5, Lane C 2026-09-06).

Vấn đề: corpus 455 record / 1653 PNG (generated_ho_so/_visual_layout/phase7v/
final) có `reviewer_verdict: NOT_REVIEWED` trên toàn bộ — gate structural
(PASS_CANDIDATE_REVIEW) ≠ visual. Việc CHẤM visual do agent ĐỌC ẢNH thực hiện
riêng; tool này CHỈ là khung ghi nhận (bookkeeping), không tự chấm:

  - đọc manifest.json của corpus (dạng phase7v: records[] với pages[] PNG);
  - xuất CHECKLIST review cho từng record (signature block, header name,
    bảng rộng, footnote, checkbox, name/date glue, trang trắng/trailing) —
    status mặc định PENDING, kèm gợi ý trang từ metadata (page_count,
    detector flags) nhưng KHÔNG sinh verdict;
  - ghi verdict `AI_REVIEWED_PASS` / `AI_REVIEWED_FAIL` (+ reason + page)
    vào review manifest RIÊNG (<corpus>/review_manifest.json), mỗi lần ĐÚNG
    MỘT record, kèm sha256 của từng PNG để chống stale;
  - --verify đối chiếu hash đã ghi với PNG trên đĩa → chỉ ra record stale.

HARD-GUARD (F5): tool KHÔNG TUYỆT ĐỐI hỗ trợ verdict giả danh người:
chuỗi khớp ``human-*`` (HUMAN_PASS, HUMAN_REVIEWED, human-reviewed, …) trong
verdict/reason/page bị TỪ CHỐI bằng lỗi, không ghi. Verdict hợp lệ là
whitelist 2 giá trị AI_*; không có API set hàng loạt PASS.

Chạy (từ root repo):
  python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --init
  python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --set \
      --form PLI_M09 --fixture valid-full --verdict AI_REVIEWED_FAIL \
      --reason "Bang thanh vien le cot 13" --page 3
  python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --verify
  python3 -X utf8 -m tools.corpus_ai_review --corpus <dir> --summary
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERDICT_PASS = "AI_REVIEWED_PASS"
VERDICT_FAIL = "AI_REVIEWED_FAIL"
ALLOWED_VERDICTS = (VERDICT_PASS, VERDICT_FAIL)
PENDING = "AI_REVIEW_PENDING"
REVIEW_FORMAT = "ai_review_manifest_v1"
REVIEW_FILENAME = "review_manifest.json"

# human-*: mọi biến thể human_pass / human-pass / HUMAN_REVIEWED / reviewed
# by human ... đều bị chặn ở mọi trường văn bản do tool ghi.
HUMAN_TOKEN_RE = re.compile(r"human[-_ ]", re.IGNORECASE)

# Checklist 7 hạng mục chuẩn của 1 record visual (F5). Mỗi mục: id, nhãn,
# tiêu chí. Tool chỉ liệt kê — người/agent đọc ảnh mới kết luận.
CHECKLIST_ITEMS = (
    ("signature_block",
     "Khối chữ ký (footer mỗi trang)",
     "Đúng mẫu chữ ký của form, không thiếu đường ký/ngày tháng, không lệch "
     "trang khi pagination."),
    ("header_name",
     "Header tên biểu mẫu",
     "Header/trang đầu ghi đúng tên mẫu; slot tên DN/HKD (nếu có) không dính "
     "vào nhãn, không trống khi fixture có giá trị."),
    ("wide_table",
     "Bảng rộng / grid",
     "Bảng >= 10 cột không vỡ cụm ký tự (D9), cột không tràn mép trang, "
     "header không chồng dòng."),
    ("footnote",
     "Chân trang chú thích",
     "Số mũ chú thích khớp dòng chú thích chân trang; chú thích không cắt "
     "giữa trang, không trôi sang mẫu khác."),
    ("checkbox",
     "Checkbox",
     "Ô □/☐ in đúng glyph, tick X nằm đúng ô, nhóm loại-trừ chọn <= 1 "
     "(fixture choice-variants)."),
    ("name_date_glue",
     "Name/date glue",
     "Nhãn và giá trị ngày/tháng/năm, họ tên không dính liền mất khoảng cách "
     "(D11/D13/D17), thứ tự field không đổi chỗ."),
    ("blank_trailing",
     "Trang trắng / trailing",
     "Không trang trắng thừa, không nội dung mồ côi sau trang cuối, tổng số "
     "trang hợp lý theo fixture."),
)


# --------------------------------------------------------------------- utils
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(p).read_bytes())
    return h.hexdigest()


def record_key(rec: dict) -> str:
    return "|".join(str(rec.get(k, "") or "") for k in
                    ("form", "fixture", "tag", "variant"))


def _assert_no_human_token(*values: str) -> None:
    for v in values:
        if v and HUMAN_TOKEN_RE.search(str(v)):
            raise ValueError(
                "giá trị chứa token human-* bị TỪ CHỐI (khung này chỉ ghi "
                "verdict AI): %r" % v)


def resolve_png(corpus_dir: Path, page: str) -> Path | None:
    """Resolve đường dẫn PNG: manifest ghi repo-root-relative; corpus có thể
    nằm ở repo khác (worktree, bản sao, tmp) nên thử lần lượt absolute,
    corpus-dir rồi TỪNG bậc cha của corpus-dir (tìm đúng repo gốc)."""
    p = Path(page)
    if p.is_absolute():
        return p if p.exists() else None
    seen = set()
    for base in (Path(corpus_dir), ROOT, *Path(corpus_dir).parents):
        if base in seen:
            continue
        seen.add(base)
        cand = base / p
        if cand.exists():
            return cand
    return None


# ------------------------------------------------------------------ manifest
def load_manifest(corpus_dir: Path) -> dict:
    path = Path(corpus_dir) / "manifest.json"
    if not path.exists():
        raise SystemExit("không thấy manifest.json trong %s" % corpus_dir)
    m = json.loads(path.read_text(encoding="utf-8"))
    if "records" not in m:
        raise SystemExit("manifest không có 'records' (cần corpus dạng "
                         "phase7v): %s" % path)
    return m


def load_review_manifest(corpus_dir: Path) -> dict:
    path = Path(corpus_dir) / REVIEW_FILENAME
    if path.exists():
        rv = json.loads(path.read_text(encoding="utf-8"))
        if rv.get("_format") != REVIEW_FORMAT:
            raise SystemExit("review manifest sai format: %s" % path)
        _assert_no_human_token(json.dumps(rv, ensure_ascii=False))
        return rv
    return {"_format": REVIEW_FORMAT,
            "created": _now(),
            "records": {}}


def save_review_manifest(corpus_dir: Path, rv: dict) -> Path:
    blob = json.dumps(rv, ensure_ascii=False, indent=1)
    _assert_no_human_token(blob)  # chốt cửa cuối trước khi ghi đĩa
    path = Path(corpus_dir) / REVIEW_FILENAME
    path.write_text(blob + "\n", encoding="utf-8")
    return path


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------- checklist
def build_checklist(rec: dict, corpus_dir: Path) -> dict:
    """Checklist PENDING cho 1 record — không verdict, chỉ hạng mục + page hint."""
    pages = rec.get("pages") or []
    resolved = [resolve_png(corpus_dir, p) for p in pages]
    missing = [p for p, r in zip(pages, resolved) if r is None]
    # page hint theo metadata: detector có hits -> hạng mục liên quan cần soi
    det = rec.get("detectors") or {}
    hints = {}
    for det_key, item_ids in (("D6_signature", ("signature_block",)),
                              ("D17_header_name", ("header_name",)),
                              ("D9_table_grid", ("wide_table",)),
                              ("D11_glue", ("name_date_glue",)),
                              ("D13_skeleton_glue", ("name_date_glue",)),
                              ("D14_name_slot", ("header_name",)),
                              ("D15_chk_glyph", ("checkbox",))):
        if det.get(det_key):
            for iid in item_ids:
                hints.setdefault(iid, []).append(det_key)
    if rec.get("page_count", 0) >= 6 or pages:
        hints.setdefault("blank_trailing", []).append("page_count=%s"
                                                      % rec.get("page_count"))
    return {
        "key": record_key(rec),
        "form": rec.get("form"),
        "fixture": rec.get("fixture"),
        "tag": rec.get("tag"),
        "variant": rec.get("variant"),
        "page_count": rec.get("page_count", len(pages)),
        "png_missing": missing,
        "checklist": [
            {"id": iid, "label": label, "criteria": criteria,
             "status": PENDING, "page": None, "notes": "",
             "detector_hints": hints.get(iid, [])}
            for iid, label, criteria in CHECKLIST_ITEMS
        ],
        "verdict": PENDING,
        "verdict_reason": "",
        "verdict_page": None,
    }


def init_review_manifest(corpus_dir: Path) -> dict:
    """Tạo khung review manifest: mọi record PENDING, không verdict."""
    manifest = load_manifest(corpus_dir)
    rv = load_review_manifest(corpus_dir)
    known = set(rv["records"])
    added = 0
    for rec in manifest["records"]:
        k = record_key(rec)
        if k not in known:
            rv["records"][k] = build_checklist(rec, Path(corpus_dir))
            added += 1
        else:
            # làm mới metadata (png_missing, page_count, detector hints) nhưng
            # TUYỆT ĐỐI giữ nguyên verdict/reason/hash đã ghi
            fresh = build_checklist(rec, Path(corpus_dir))
            entry = rv["records"][k]
            for meta in ("page_count", "png_missing", "checklist"):
                entry[meta] = fresh[meta]
    rv["corpus_dir"] = str(corpus_dir)
    rv["corpus_generated"] = manifest.get("generated", "")
    rv["updated"] = _now()
    save_review_manifest(corpus_dir, rv)
    return {"records_total": len(manifest["records"]),
            "added": added,
            "already": len(manifest["records"]) - added,
            "path": str(Path(corpus_dir) / REVIEW_FILENAME)}


# ------------------------------------------------------------------- verdict
def set_verdict(corpus_dir: Path, form: str, fixture: str,
                verdict: str, reason: str,
                tag: str = "main", variant: str = "",
                page: int | None = None) -> dict:
    """Ghi verdict AI cho ĐÚNG MỘT record (không có chế độ hàng loạt)."""
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError(
            "verdict phải thuộc %s, nhận %r — khung này KHÔNG ghi verdict "
            "khác (human-* bị cấm tuyệt đối)" % (ALLOWED_VERDICTS, verdict))
    _assert_no_human_token(verdict, reason, str(page or ""))
    if not reason or not reason.strip():
        raise ValueError("verdict phải kèm reason (chống PASS/FAIL mù)")
    manifest = load_manifest(corpus_dir)
    by_key = {record_key(r): r for r in manifest["records"]}
    key = "|".join([form, fixture, tag, variant])
    if key not in by_key:
        raise SystemExit("không thấy record %r trong corpus manifest" % key)
    rec = by_key[key]
    resolved = [resolve_png(corpus_dir, p) for p in rec.get("pages") or []]
    if any(r is None for r in resolved):
        raise SystemExit("PNG thiếu trên đĩa cho %r — chấm trên ảnh thật "
                         "trước khi ghi verdict" % key)
    rv = load_review_manifest(corpus_dir)
    entry = rv["records"].get(key) or build_checklist(rec, Path(corpus_dir))
    entry.update({
        "verdict": verdict,
        "verdict_reason": reason.strip(),
        "verdict_page": page,
        "verdict_at": _now(),
        "png_sha256": {Path(p).name: sha256_file(r)
                       for p, r in zip(rec.get("pages") or [], resolved)},
        "template_hash_at_review": rec.get("template_hash", ""),
    })
    rv["records"][key] = entry
    rv["updated"] = _now()
    save_review_manifest(corpus_dir, rv)
    return {"key": key, "verdict": verdict,
            "pages_hashed": len(entry["png_sha256"])}


# -------------------------------------------------------------------- verify
def verify_review_manifest(corpus_dir: Path) -> dict:
    """Đối chiếu hash lúc-verdict với PNG hiện tại: stale = PNG đã đổi."""
    corpus_dir = Path(corpus_dir)
    rv = load_review_manifest(corpus_dir)
    manifest = load_manifest(corpus_dir)
    pages_by_key = {record_key(r): (r.get("pages") or [])
                    for r in manifest["records"]}
    stale, missing_review, ok = [], [], 0
    for key, entry in sorted(rv["records"].items()):
        if entry.get("verdict") not in ALLOWED_VERDICTS:
            missing_review.append(key)
            continue
        recorded = entry.get("png_sha256") or {}
        current = {}
        for name, page in zip(recorded, pages_by_key.get(key, [])):
            p = resolve_png(corpus_dir, page)
            if p is not None:
                current[Path(p).name] = sha256_file(p)
        diff = sorted(n for n in recorded
                      if current.get(n) != recorded[n])
        if diff:
            stale.append({"key": key, "changed": diff})
        else:
            ok += 1
    return {"verdicted": ok + len(stale), "stale": stale,
            "pending": len(missing_review),
            "corpus_records": len(manifest["records"])}


def summarize(corpus_dir: Path) -> dict:
    rv = load_review_manifest(corpus_dir)
    counts = {PENDING: 0, VERDICT_PASS: 0, VERDICT_FAIL: 0}
    for entry in rv["records"].values():
        counts[entry.get("verdict", PENDING)] = \
            counts.get(entry.get("verdict", PENDING), 0) + 1
    return {"records": len(rv["records"]),
            "AI_REVIEWED_PASS": counts.get(VERDICT_PASS, 0),
            "AI_REVIEWED_FAIL": counts.get(VERDICT_FAIL, 0),
            "pending": counts.get(PENDING, 0)}


# ----------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", action="store_true",
                   help="tạo/cập nhật khung review_manifest.json (PENDING)")
    g.add_argument("--set", action="store_true",
                   help="ghi verdict cho 1 record")
    g.add_argument("--verify", action="store_true",
                   help="đối chiếu hash chống stale")
    g.add_argument("--summary", action="store_true")
    ap.add_argument("--form")
    ap.add_argument("--fixture")
    ap.add_argument("--tag", default="main")
    ap.add_argument("--variant", default="")
    ap.add_argument("--verdict", choices=ALLOWED_VERDICTS)
    ap.add_argument("--reason")
    ap.add_argument("--page", type=int)
    args = ap.parse_args(argv)
    corpus = Path(args.corpus)
    if args.init:
        print(json.dumps(init_review_manifest(corpus), ensure_ascii=False))
        return 0
    if args.set:
        if not (args.form and args.fixture and args.verdict):
            ap.error("--set cần --form --fixture --verdict")
        print(json.dumps(set_verdict(corpus, args.form, args.fixture,
                                     args.verdict, args.reason or "",
                                     tag=args.tag, variant=args.variant,
                                     page=args.page), ensure_ascii=False))
        return 0
    if args.verify:
        print(json.dumps(verify_review_manifest(corpus), ensure_ascii=False))
        return 0
    print(json.dumps(summarize(corpus), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
