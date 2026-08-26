#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detector Wave L1 — kiểm tra contract extractor/schema trên app/data/blocks.

Kiểm tra (gắn với census L0 — app/data/layout_specs/layout_manifest.json,
baseline: 46 source-indicator block / 336 block chứa \\n / 142 digit-glue
candidate):
  (a) mọi block "p" phải có "role" thuộc tập ROLES (tools/layout_roles.py);
      block thiếu role = legacy pre-regen, chỉ được phép ở chế độ --pre-regen.
  (b) 0 dòng khớp pattern source-indicator (PL1 - Mau so N:, tên file .docx,
      nhãn import/scrape) còn ở role body/thiếu role. form-number pháp lý
      ("Mẫu số 1") KHÔNG bị tính là source-indicator.
  (c) newline bảo tồn: tổng block "p" chứa "\\n" trong text >= NGƯỠNG.
      Ngưỡng evidence-based: L0 đếm 336 block newline-collapse/83 form; việc
      gắn role/format không xóa ký tự "\\n" nào nên sau regen kỳ vọng giữ
      nguyên ≥ 95% (≥ 319). Chi tiết: docs/layout_l1_contract.md.
  (d) digit-glue về 0 dạng baseline-text: mỗi ứng viên L0 (chữ số dính chữ,
      vd "Tôi là1") sau regen phải là run superscript/subscript (vertAlign)
      hoặc block có role footnote/form-number/source-indicator. Đếm theo
      phương pháp của detector này trên text run (không qua OOXML).

Chạy:
    python3 -X utf8 tools/census/check_layout_l1.py               # sau regen: PASS=exit 0
    python3 -X utf8 tools/census/check_layout_l1.py --pre-regen   # report trên blocks CŨ, exit 1 kèm thống kê
    python3 -X utf8 tools/census/check_layout_l1.py --blocks-dir /tmp/x   # quét thư mục khác

Trạng thái hiện tại (HEAD a0453d0, blocks CHƯA regenerate): chạy mặc định sẽ
FAIL — đúng thiết kế; dùng --pre-regen để lấy thống kê chi tiết.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from collections import Counter

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import layout_roles  # noqa: E402
from layout_roles import fold, classify_role  # noqa: E402

DEFAULT_BLOCKS_DIR = os.path.join(ROOT, "app", "data", "blocks")
MANIFEST_PATH = os.path.join(
    ROOT, "app", "data", "layout_specs", "layout_manifest.json"
)

# L0 baseline (build_layout_manifest.py): tổng số block, không phải số form.
# LƯU Ý phương pháp: rollup L0 = 336 đếm theo census fragment gồm CẢ block
# chỉ có tab ('\t', vd "Chức danh: \t") và paragraph nguồn bị converter bỏ
# (marker {?cond} của M72). Detector này đo CHẶT ký tự "\n" trong block "p"
# của app/data/blocks — baseline đo trực tiếp pre-regen = 309 block/82 form
# (chênh 27 với L0 đã đối chiếu, xem docs/layout_l1_contract.md mục newline).
L0_SOURCE_INDICATOR_BLOCKS = 46
L0_NEWLINE_BLOCKS_ROLLUP = 336   # phương pháp L0 fragment (tham chiếu)
NEWLINE_BASELINE = 309           # "\n" thật trong p-blocks, đo pre-regen a0453d0
NEWLINE_KEEP_RATIO = 0.95
NEWLINE_THRESHOLD = int(NEWLINE_BASELINE * NEWLINE_KEEP_RATIO)  # 293

L0_DIGIT_GLUE_CANDIDATES = 142
# Pattern marker kỹ thuật (áp trên bản fold) — đồng bộ layout_roles.py
SOURCE_INDICATOR_RE = re.compile(r"^pl\d+\s*[-–]?\s*mau\s+so\b")
FILENAME_RE = re.compile(r"(^|\s)[a-z0-9_\-\. ]{0,64}\.(docx?|pdf|xlsm?|png|jpe?g)(\s|$|[.,;)])")
FORM_NUMBER_RE = re.compile(r"^mau so\s*\d{1,4}\b")

# chữ (>=2 ký tự) dính trực tiếp chữ số — ứng viên "Tôi là1" baseline-text
GLUE_RE = re.compile(
    r"([A-Za-zÀ-ỹăâđêôơưÁ-ỸĂÂĐÊÔƠƯ]{2,})([0-9]+)"
)
ROLES = layout_roles.ROLES


def load_blocks(blocks_dir):
    docs = []
    for name in sorted(os.listdir(blocks_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(blocks_dir, name)
        try:
            with io.open(path, "r", encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print("[X] %s: json hỏng %r" % (name, exc))
            continue
        docs.append((name[:-5], data))
    return docs


def para_text(block):
    return "".join(
        r.get("text", "") for r in block.get("runs", [])
        if isinstance(r, dict) and "text" in r
    )


def is_source_indicator_text(folded_text):
    """Marker kỹ thuật thật sự — loại trừ dòng pháp lý 'Mẫu số N'."""
    if FORM_NUMBER_RE.match(folded_text) and not SOURCE_INDICATOR_RE.match(folded_text):
        return False
    if SOURCE_INDICATOR_RE.match(folded_text):
        return True
    if FILENAME_RE.search(folded_text) and len(folded_text) <= 200:
        return True
    return False


def unresolved_glue_count(block, eff_role=None):
    """Số chữ số dính chữ còn Ở DẠNG BASELINE trong block.

    Run superscript/subscript chỉ gồm digits (hoặc digits ở đầu run vertAlign
    đứng ngay sau chữ) được coi là đã semantic -> không tính. Block có role
    footnote/form-number/source-indicator cũng được coi là đã phân loại xong.
    eff_role: role hiệu lực (stored hoặc suy luận) — dùng khi pre-regen block
    chưa có stored role.
    """
    if eff_role in ("footnote", "form-number", "source-indicator"):
        return 0
    runs = [r for r in block.get("runs", []) if isinstance(r, dict)]
    count = 0
    prev_letter_tail = False  # run trước kết bằng chữ?
    for r in runs:
        if "input" in r:
            prev_letter_tail = False
            continue
        txt = r.get("text", "")
        va = r.get("vertAlign")
        hits = []
        for m in GLUE_RE.finditer(txt):
            letters = m.group(1)
            # mã trích dẫn văn bản pháp lý "…số 76/2025/QH15 ngày…" — chữ IN
            # HOA đứng ngay sau '/' là mã (QH15, TT13…) không phải chú thích.
            before = txt[m.start() - 1] if m.start() > 0 else ""
            if before == "/" and letters.isupper():
                continue
            hits.append(m.group(0))
        # chữ số superscript ở ĐẦU run vertAlign, nối từ run trước: semantic
        if va and re.match(r"^[0-9]+(?![0-9])", txt) and prev_letter_tail:
            hits = [h for h in hits if not txt.startswith(h)]
        count += len(hits)
        prev_letter_tail = bool(txt) and re.search(r"[A-Za-zÀ-ỹà-ỹ]$", txt)
    return count


def scan(docs):
    stats = {
        "forms": len(docs),
        "p_blocks": 0,
        "missing_role": 0,
        "bad_role": 0,
        "roles": Counter(),
        "si_role_ok": 0,
        "si_leak": [],           # (fid, idx, text) marker chưa classify
        "newline_blocks": 0,
        "glue_baseline": [],     # (fid, idx, sample)
        "glue_total": 0,
    }
    for fid, data in docs:
        for idx, b in enumerate(data.get("blocks", [])):
            if b.get("t") != "p":
                continue
            stats["p_blocks"] += 1
            raw = para_text(b)
            folded = fold(raw)
            role = b.get("role")
            if role is None:
                stats["missing_role"] += 1
                eff_role = classify_role(folded, None, b.get("runs"))
            elif role not in ROLES:
                stats["bad_role"] += 1
                eff_role = role
                stats["roles"]["<lạ:%s>" % role] += 1
                continue
            else:
                eff_role = role
            stats["roles"][eff_role] += 1

            if eff_role == "source-indicator":
                stats["si_role_ok"] += 1
            elif is_source_indicator_text(folded):
                stats["si_leak"].append((fid, idx, raw[:70]))

            if "\n" in raw:
                stats["newline_blocks"] += 1

            n_glue = unresolved_glue_count(b, eff_role)
            if n_glue:
                stats["glue_total"] += n_glue
                if len(stats["glue_baseline"]) < 25:
                    m = GLUE_RE.search(raw)
                    stats["glue_baseline"].append((fid, idx, m.group(0) if m else "?"))
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-regen", action="store_true",
                    help="chế độ report trên blocks cũ (exit 1 kèm thống kê)")
    ap.add_argument("--blocks-dir", default=DEFAULT_BLOCKS_DIR)
    args = ap.parse_args()

    docs = load_blocks(args.blocks_dir)
    stats = scan(docs)

    print("=" * 72)
    print("CHECK LAYOUT L1 — blocks dir: %s" % os.path.relpath(args.blocks_dir, ROOT))
    print("forms=%s p_blocks=%s" % (stats["forms"], stats["p_blocks"]))
    print("-" * 72)

    problems = []

    # (a) role hợp lệ
    print("(a) role:")
    print("    thiếu role (legacy pre-regen) : %s" % stats["missing_role"])
    print("    role lạ                      : %s" % stats["bad_role"])
    print("    phân bố: %s" % dict(sorted(stats["roles"].items())))
    if stats["bad_role"]:
        problems.append("(a) %d block p có role ngoài tập ROLES" % stats["bad_role"])
    if not args.pre_regen and stats["missing_role"]:
        problems.append("(a) %d block p thiếu role (chưa regen?)" % stats["missing_role"])

    # (b) source-indicator leak
    print("(b) source-indicator:")
    print("    role đúng (source-indicator) : %s / L0 baseline %s"
          % (stats["si_role_ok"], L0_SOURCE_INDICATOR_BLOCKS))
    leak = stats["si_leak"]
    print("    LEAK marker còn ở body/không-role: %s" % len(leak))
    for fid, idx, txt in leak[:12]:
        print("      [%s #%s] %r" % (fid, idx, txt))
    if len(leak) > 12:
        print("      … và %d nữa" % (len(leak) - 12))
    if leak:
        problems.append("(b) %d dòng source-indicator chưa được đánh dấu role" % len(leak))

    # (c) newline bảo tồn
    print("(c) newline:")
    print("    block p chứa '\\\\n'          : %s (baseline đo pre-regen=%s, "
          "ngưỡng ≥%s = %.0f%%; L0 rollup=%s theo phương pháp fragment)"
          % (stats["newline_blocks"], NEWLINE_BASELINE, NEWLINE_THRESHOLD,
             NEWLINE_KEEP_RATIO * 100, L0_NEWLINE_BLOCKS_ROLLUP))
    if stats["newline_blocks"] < NEWLINE_THRESHOLD:
        problems.append(
            "(c) newline giảm bất thường: %s < ngưỡng %s"
            % (stats["newline_blocks"], NEWLINE_THRESHOLD))

    # (d) digit-glue baseline
    print("(d) digit-glue baseline-text:")
    print("    số trường hợp còn lại       : %s (L0 candidate=%s)"
          % (stats["glue_total"], L0_DIGIT_GLUE_CANDIDATES))
    for fid, idx, sample in stats["glue_baseline"][:12]:
        print("      [%s #%s] …%s…" % (fid, idx, sample))
    if len(stats["glue_baseline"]) > 12:
        print("      … và %d mẫu nữa" % (len(stats["glue_baseline"]) - 12))
    if stats["glue_total"] > 0:
        problems.append(
            "(d) %d chữ số dính chữ còn ở dạng baseline (phải là vertAlign "
            "superscript hoặc role footnote/form-number)" % stats["glue_total"])

    print("-" * 72)
    if problems:
        print("KẾT LUẬN: FAIL — %d nhóm vấn đề:" % len(problems))
        for pr in problems:
            print(" -", pr)
        if args.pre_regen:
            print("(--pre-regen: đây là trạng thái ĐÚNG KỲ VỌNG trước khi Lead "
                  "regenerate 87 blocks; thống kê phía trên là baseline đối chiếu.)")
        return 1
    print("KẾT LUẬN: PASS — contract L1 đạt trên %s forms." % stats["forms"])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
