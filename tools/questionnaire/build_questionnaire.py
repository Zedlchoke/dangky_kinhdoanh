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


def build_one(path: Path, form_maps: dict, write: bool) -> tuple[str, str]:
    source = json.loads(path.read_text(encoding="utf-8"))
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
    built = []
    for p in paths:
        try:
            doc_id, _ = build_one(p, form_maps, write=not args.check)
        except QuestionnaireError as exc:
            print("FAIL  %s: %s" % (p.stem, exc), file=sys.stderr)
            return 1
        built.append(doc_id)
    action = "KIỂM" if args.check else "SINH"
    print("%s OK %d questionnaire: %s" % (action, len(built), ", ".join(built)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
