# -*- coding: utf-8 -*-
"""Builder questionnaire — wave X1 (PLAN.md mục 4).

Đọc nguồn câu hỏi được owner duyệt (`tools/questionnaire/clusters/*.json`)
đối chiếu registry `app/data/form_maps.json`, rồi sinh artifact
`app/data/questionnaire/<doc_id>.json` cho runtime X3 (nạp phiếu) và X2
(xuất phiếu).

Nguyên tắc:
- FAIL-LOUD: câu hỏi thiếu data_key / key không có trong form_maps / type lạ /
  question_id trùng → exit 1, KHÔNG ghi artifact (PLAN X1 gate: "khung khớp
  100% data-key có trong registry; question chưa có data-key = fail build").
- Artifact là generated: mọi thay đổi phải nằm trong
  `tools/audit_expected_diff_files.txt` có chủ đích và regen đi cùng đợt
  regen template (PLAN 4.5).
- KHÔNG sửa form_maps/templates (tách biệt hoàn toàn).

Cách dùng (từ ROOT):
  python3 -X utf8 -m tools.questionnaire.build_questionnaire            # build hết
  python3 -X utf8 -m tools.questionnaire.build_questionnaire --check    # chỉ kiểm
  python3 -X utf8 -m tools.questionnaire.build_questionnaire --one CLUSTER_ID
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.questionnaire.schema import (  # noqa: E402
    QuestionnaireError, load_form_maps, validate)

CLUSTER_DIR = ROOT / "tools" / "questionnaire" / "clusters"
OUT_DIR = ROOT / "app" / "data" / "questionnaire"

BLOCKED_PREFIX = "blocked_"
BLOCKED_VERSION = 1


def load_blocked(paths: list[Path], form_maps: dict) -> dict[str, dict]:
    """[O7] Đọc các manifest `blocked_*.json` — thủ tục bị CHẶN sinh câu hỏi.

    Form thuộc Thông tư 121/2026 thay thế (vd I_M12/I_M27...) phải migrate
    template/spec trước khi sinh questionnaire (owner packet v7 — O7/L-2026).
    Trả map doc_id -> entry blocked. Fail-loud: doc_id không có trong
    form_maps, sai khung manifest, hoặc thiếu reason.
    """
    out: dict[str, dict] = {}
    for p in paths:
        if not p.stem.startswith(BLOCKED_PREFIX):
            continue
        source = json.loads(p.read_text(encoding="utf-8"))
        if source.get("blocked_version") != BLOCKED_VERSION:
            raise QuestionnaireError(
                "BAD_VERSION", "%s: blocked_version=%r không hỗ trợ"
                % (p.stem, source.get("blocked_version")))
        entries = source.get("blocked")
        # [f4xl 2026-09-06] danh sách rỗng là HỢP LỆ: 9 mẫu TT121-thay đã
        # migrate xong (merge e268038) — manifest giữ lại làm sổ theo dõi
        # (ghi chú M11 REMOVED_BY_CURRENT_LAW), `blocked: []` = không còn
        # form nào bị chặn. Chỉ fail-loud khi thiếu/không phải list.
        if not isinstance(entries, list):
            raise QuestionnaireError(
                "NO_ENTRIES", "%s: thiếu danh sách 'blocked'" % p.stem)
        for e in entries:
            doc_id = e.get("doc_id") if isinstance(e, dict) else None
            if not doc_id:
                raise QuestionnaireError(
                    "MISSING_FIELD", "%s: entry thiếu doc_id" % p.stem)
            if doc_id not in form_maps:
                raise QuestionnaireError(
                    "DOC_NOT_FOUND", "%s: %r không có trong form_maps"
                    % (p.stem, doc_id))
            if not e.get("reason"):
                raise QuestionnaireError(
                    "MISSING_FIELD", "%s: %s thiếu reason" % (p.stem, doc_id))
            if doc_id in out:
                raise QuestionnaireError(
                    "DUP_ID", "%s: doc_id blocked trùng: %s" % (p.stem, doc_id))
            entry = dict(e)
            entry["manifest"] = p.stem
            out[doc_id] = entry
    return out


def build_one(path: Path, form_maps: dict, write: bool,
              blocked: dict[str, dict] | None = None) -> tuple[str, str]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if blocked and source.get("doc_id") in blocked:
        raise QuestionnaireError(
            "DOC_BLOCKED",
            "%s: form %s đang blocked-chờ-migration (%s) — KHÔNG sinh câu "
            "hỏi cho tới khi migrate xong" % (
                path.stem, source["doc_id"],
                blocked[source["doc_id"]].get("reason", "")))
    warnings = validate(source, form_maps)
    out = {
        "doc_id": source["doc_id"],
        "title": source["title"],
        "questionnaire_version": source["questionnaire_version"],
        "cluster": path.stem,
        "questions": source["questions"],
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=False)
    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / (source["doc_id"] + ".json")).write_text(
            payload + "\n", encoding="utf-8")
    for w in warnings:
        print("WARN  %s: %s" % (path.stem, w))
    return source["doc_id"], payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--one", help="chỉ build cluster này (tên file không .json)")
    ap.add_argument("--check", action="store_true",
                    help="chỉ kiểm tra, không ghi artifact")
    args = ap.parse_args(argv)

    paths = sorted(CLUSTER_DIR.glob("*.json"))
    if args.one:
        paths = [p for p in paths if p.stem == args.one]
        if not paths:
            print("KHÔNG có cluster %r" % args.one, file=sys.stderr)
            return 2
    if not paths:
        print("KHÔNG có cluster nào trong %s" % CLUSTER_DIR, file=sys.stderr)
        return 2

    form_maps = load_form_maps(ROOT)
    # [O7] manifest blocked_* được đọc trước; builder fail-loud nếu một cluster
    # câu hỏi trỏ tới form đang blocked.
    blocked = load_blocked(paths, form_maps)
    built = []
    for p in paths:
        if p.stem.startswith(BLOCKED_PREFIX):
            continue
        try:
            doc_id, _ = build_one(p, form_maps, write=not args.check,
                                  blocked=blocked)
        except QuestionnaireError as exc:
            print("FAIL  %s: %s" % (p.stem, exc), file=sys.stderr)
            return 1
        built.append(doc_id)
    for doc_id, e in sorted(blocked.items()):
        print("BLOCKED %s (%s): %s" % (doc_id, e.get("cluster", ""),
                                       e.get("reason", "")))
    action = "KIỂM" if args.check else "SINH"
    print("%s OK %d questionnaire: %s; blocked-chờ-migration: %d"
          % (action, len(built), ", ".join(built) or "(không)", len(blocked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
