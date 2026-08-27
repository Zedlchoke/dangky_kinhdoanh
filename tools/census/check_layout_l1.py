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

Rule cấu trúc V3 bổ sung (audit Wave D round 1 — lớp lỗi mà pass 87/87 cũ
KHÔNG nhìn thấy; mỗi rule đều bắt được bằng chứng thật ở blocks HEAD
1c59fc13 nên "đỏ = lỗi dữ liệu thật", không phải đỏ-trên-không-gì):
  (e) run-glue cột bảng: một run text bắt đầu bằng "STT"/"Stt" rồi tiếp nối
      LIỀN bằng chữ-in-đầu-cột (tiêu đề các ô bảng bị scrape dính chung một
      w:t, vd PLI_M72 #109/#111 "STTTên cổ đôngQuốc tịch…"). Whitelist: run
      mang vertAlign bỏ qua (chú thích số mũ); chỉ xét ĐẦU run để không nhầm
      câu văn có "STT" theo sau là dấu chấm/ngoặc/khoảng trắng.
  (f) run text chứa chuỗi >= 5 chữ số liên tục (cột đếm bị dính, vd
      PLI_M02 #126 r11 "12345678910111213"). Whitelist ghi rõ lý do:
        * role source-indicator/form-number được bỏ qua (tên file/mã biểu
          mẫu chứa chuỗi số dài là hợp lệ — cùng chính sách với rule (d));
        * run mang vertAlign (chú thích) bỏ qua.
      KHÔNG exempt "run thuần số đứng một mình": cả 8 trường hợp thật đều là
      run thuần số, heuristic đó sẽ tắt luôn khả năng phát hiện.
  (g) heading đánh số nhưng không đúng vai trò cấu trúc:
      (g1) cả block bắt đầu "N. <chữ>" (^\\d{1,2}\\.\\s\\S) mà role không thuộc
           nhóm heading (section-heading/form-title/form-subtitle);
           whitelist: dòng kẻ chấm trống chữ ("1. .....", bản in để điền tay)
           không phải heading có nội dung.
           Round 2 L1FIX: 12 vị trí heading dài (>120 ký tự, cùng chuỗi mục
           với các nhãn NGẮN hơn đã là section-heading trong cùng form) được
           xử lý bằng tools/layout_role_overrides.json (by_folded_prefix +
           forms) nên tự hết đỏ sau regen; detector vẫn đọc role đã lưu nên
           trước regen chỉ báo đỏ đúng bằng dữ liệu thật.
      (g2) heading đánh số DÍNH ĐUÔI block trước, không phải block riêng —
           chính là bug V2 của PLI_M72 blk110/112. Predicate sao chép 1:1 từ
           docx_to_blocks._is_glued_heading_cut (kèm MAX_HEADING_TAIL_CHARS,
           HEADING_ROLES); converter đã tách dạng glue này nên khi Lead
           regen thì g2 tự về 0, không đỏ mãi vô lý.
           tools/test_layout_l1_extractor giữ bài test đối sánh hai bản
           predicate để chống drift.

Chạy:
    python3 -X utf8 tools/census/check_layout_l1.py               # sau regen: PASS=exit 0
    python3 -X utf8 tools/census/check_layout_l1.py --pre-regen   # report trên blocks CŨ, exit 1 kèm thống kê
    python3 -X utf8 tools/census/check_layout_l1.py --blocks-dir /tmp/x   # quét thư mục khác

Trạng thái hiện tại (blocks CHƯA regen lần nữa): chạy mặc định FAIL ở
(d)/(e)/(f)/(g) — đúng thiết kế; các lỗi dữ liệu thật đang mở cho lane khác
sửa và NGƯỠNG KHÔNG được nới chỉ để đạt PASS.
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

# ---------------------------------------------------------------------------
# Rule V3 (e)(f)(g) — lỗi cấu trúc run-glue / heading bị gộp (audit Wave D)
# ---------------------------------------------------------------------------

# (e) "STT" + chữ-in-đầu-cột dính liền trong MỘT run (bắt đầu run). (?i) để
#     bắt cả biến thể lowercase do scrape; look-ahead yêu cầu ký tự kế là CHỮ
#     (unicode), vì "STT" hợp lệ luôn đứng trước khoảng trắng/dấu chấm/ngoặc.
STT_GLUE_RUN_RE = re.compile(r"(?i)^stt(?=[^\W\d_])")

# (f) chuỗi chữ số dài >= 5 liên tục trong một run.
LONG_DIGIT_RUN_RE = re.compile(r"\d{5,}")

# role nhóm heading (đối sánh docx_to_blocks.HEADING_ROLES)
HEADING_ROLES_FOR_NUMBERING = frozenset(
    {"section-heading", "form-title", "form-subtitle"}
)
# role metadata được miễn rule (f) — lý do ở docstring
METADATA_ROLES_SKIP = frozenset({"source-indicator", "form-number"})

# (g1) block bắt đầu bằng heading đánh số "N. <chữ>"
NUMBERED_HEAD_BLOCK_START_RE = re.compile(r"^\d{1,2}\.\s\S")
# (g2) ứng viên ranh giới "N. <chữ>" ở bất kỳ đâu trong text ghép của block;
#      đồng bộ NUMBERED_HEADING_FIND_RE của tools/docx_to_blocks.py
NUMBERED_HEAD_OFFSET_RE = re.compile(r"\d{1,2}\.[ \t](?=\S)")
# guard độ dài đuôi — PHẢI bằng docx_to_blocks.MAX_HEADING_TAIL_CHARS
GLUED_HEADING_MAX_TAIL_CHARS = 300

# tag -> khoá thống kê trong stats của scan() (dùng chung report ở main())
STRUCT_RULE_KEYS = {"e": "struct_e", "f": "struct_f",
                    "g1": "struct_g1", "g2": "struct_g2"}


def is_stt_glue_run(text: str) -> bool:
    """(e) run mở đầu bằng STT/Stt + chữ-in-đầu-cột dính liền."""
    if not text or not text.strip():
        return False
    return bool(STT_GLUE_RUN_RE.match(text))


def long_digit_run(text: str):
    """(f) trả về match digit-run dai (LONG_DIGIT_RUN_RE) đầu tiên hoặc None."""
    if not text:
        return None
    return LONG_DIGIT_RUN_RE.search(text)


def _heading_tail_ok(tail: str) -> bool:
    """Đuôi sau ranh giới có đóng vai heading đánh số (tier-11 layout_roles)?

    Bản sao của docx_to_blocks._is_heading_tail — dòng kẻ chấm trống chữ
    ("1. ......") không phải heading có nội dung."""
    body = (tail or "").strip()
    if not body or not any(ch.isalpha() for ch in body):
        return False
    return classify_role(fold(body), None, [{"text": body}]) \
        in HEADING_ROLES_FOR_NUMBERING


def _is_glued_heading_cut(full: str, pos: int) -> bool:
    """(g2) `pos` có phải ranh giới heading đánh số GHÉP vào text trước đó?

    BẢN SAO 1:1 của docx_to_blocks._is_glued_heading_cut (Wave L1FIX): đổi
    bên converter thì phải đổi bên này và chạy lại test đối sánh trong
    tools/test_layout_l1_extractor.TestDetectorStructuralRules.test_predicate_detector_khop_converter_chong_drift."""
    prev = full[pos - 1]
    if prev == ".":
        # "5." + "1. …" / "…mục 10." là đánh số nhiều cấp con
        return False
    if prev.isdigit():
        # "1"+"0. Thông tin…" (= mục 10.) hoặc "123456789"+"2. Thông tin…"
        # (cột đếm scrape): ranh giới thật không suy ra được từ text.
        return False
    if prev.isspace():
        # đã ngắt dòng/hard break rõ ràng — ranh giới hiển thị còn nguyên
        return False
    tail = full[pos:]
    if not tail.strip():
        return False
    if len(tail) > GLUED_HEADING_MAX_TAIL_CHARS:
        return False
    return _heading_tail_ok(tail)


def glued_heading_offsets(full: str) -> list[int]:
    """Các offset heading đánh số dính đuôi text trước nó trong cùng block."""
    cuts: list[int] = []
    for m in NUMBERED_HEAD_OFFSET_RE.finditer(full):
        pos = m.start()
        if pos == 0 or not full[:pos].strip():
            continue
        if _is_glued_heading_cut(full, pos):
            cuts.append(pos)
    return cuts


def numbered_head_misrole(raw_text: str, eff_role) -> bool:
    """(g1) block bắt đầu "N. <chữ>" nhưng role không thuộc nhóm heading.

    Whitelist có lý do: dòng kẻ chấm trống chữ ("1. ..................",
    PLII_M17/PLI_M80) là chỗ trống để điền tay của biểu mẫu giấy, KHÔNG chứa
    nội dung heading nào cả nên không bắt buộc role heading."""
    body = (raw_text or "").strip()
    if not any(ch.isalpha() for ch in body):
        return False
    if eff_role in HEADING_ROLES_FOR_NUMBERING:
        return False
    return bool(NUMBERED_HEAD_BLOCK_START_RE.match(body))

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


def structural_findings(block, eff_role) -> list[tuple[str, str]]:
    """Các lỗi cấu trúc V3 (e)/(f)/(g) của một block "p".

    Trả về list (rule, sample). Rule là một trong "e", "f", "g1", "g2"."""
    out: list[tuple[str, str]] = []
    runs = [r for r in block.get("runs", []) if isinstance(r, dict)]
    full = "".join(
        r.get("text", "") for r in runs if isinstance(r.get("text"), str)
    )
    # (g1) heading đánh số mở đầu block nhưng role sai
    if numbered_head_misrole(full, eff_role):
        out.append(("g1", full.strip()[:70]))
    # quét từng run cho (e)/(f); chú thích số mũ không phải cột bảng/đếm
    for ri, r in enumerate(runs):
        txt = r.get("text")
        if not isinstance(txt, str) or r.get("vertAlign"):
            continue
        if is_stt_glue_run(txt):
            out.append(("e", "%r" % txt[:70]))
        dm = long_digit_run(txt)
        if dm and eff_role not in METADATA_ROLES_SKIP:
            start = max(0, dm.start() - 12)
            ctx = ("…" if start else "") + txt[start:dm.end() + 12] + \
                  ("…" if dm.end() + 12 < len(txt) else "")
            out.append(("f", "%r (run %d)" % (ctx, ri)))
    # (g2) heading đánh số dính đuôi — predicate đồng bộ converter
    for pos in glued_heading_offsets(full):
        tail = full[pos:]
        out.append(("g2", "%r" % (("…%s" % full[max(0, pos - 24):pos][-24:])
                                  + tail[:56])))
    return out


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
        # V3: rule -> [(fid, idx, sample)]
        "struct_e": [],
        "struct_f": [],
        "struct_g1": [],
        "struct_g2": [],
        "_rule_count": Counter(),   # rule -> số run/block vi phạm
        "_rule_form": {},           # rule -> set(form)
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

            for rule, sample in structural_findings(b, eff_role):
                lst = stats[STRUCT_RULE_KEYS[rule]]
                if len(lst) < 40:
                    lst.append((fid, idx, sample))
                stats["_rule_count"][rule] += 1
                stats["_rule_form"].setdefault(rule, set()).add(fid)
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

    # (e)(f)(g) — rule cấu trúc V3
    struct_key = STRUCT_RULE_KEYS
    STRUCT_RULES = (
        ("e", "STT + chữ-in-đầu-cột dính liền trong 1 run"),
        ("f", "chuỗi >=5 chữ số liên tục trong 1 run"),
        ("g1", 'block bắt đầu "N. <chữ>" nhưng role ngoài nhóm heading'),
        ("g2", "heading đánh số dính đuôi block trước (không phải block riêng)"),
    )
    for tag, label in STRUCT_RULES:
        hits = stats["_rule_count"].get(tag, 0)
        forms = sorted(stats["_rule_form"].get(tag) or ())
        print("(%s) %s:" % (tag, label))
        print("    số vi phạm                  : %d (trên %d form)"
              % (hits, len(forms)))
        samples = stats[struct_key[tag]]
        for fid, idx, sample in samples[:12]:
            print("      [%s #%s] %s" % (fid, idx, sample))
        more = hits - len(samples)
        if more > 0:
            print("      … và %d vị trí nữa" % more)
        if hits:
            problems.append(
                "(%s) %s — %d vị trí/%d form: %s"
                % (tag, label, hits, len(forms), ", ".join(forms[:8])
                   + ("…" if len(forms) > 8 else "")))

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
