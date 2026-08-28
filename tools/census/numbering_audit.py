# -*- coding: utf-8 -*-
"""Census đánh số mục liên tục trên 87 blocks (lệnh owner 2026-08-28).

Owner báo lỗi: PLI_M09 (tab "Danh sách thành viên công ty hợp danh") nhảy
mục 6 -> mục 8, mất mục 7. Census này quét TOÀN BỘ app/data/blocks/*.json
để bắt TRỌN lớp lỗi "đánh số mục" thay vì sửa từng mẫu tay.

Ba lớp kiểm tra:
  A. JUMP  — trong cùng một chuỗi đánh số, mục n nhảy sang n+k (k>1).
  B. CHAIN — chuỗi companion: form chính kết thúc ở mục X, form "Danh sách
     thành viên/cổ đông" đi kèm phải bắt đầu ở X+1 (tiền lệ nguồn: biểu mẫu
     Phụ lục I TT 68 đánh số LIÊN TỤC qua các mẫu trong cùng một bộ hồ sơ).
  C. GLUE  — chữ số chú thích chân trang dính vào chữ trong heading/body
     ("xã hội7:") — lớp lỗi extractor đã ghi ở Wave D audit (V3).

False positive đã loại: đánh số con "5.1" (regex ^\\d+\\.\\d+), đánh số
Roman (I./II.), restart chuỗi theo variant (PLI_M72 ×5 loại hình — chạy lại
1..N là đúng thiết kế Option D), khối "1. Họ, chữ đệm và tên" trong lưới
người (đánh số trường, không phải mục).

Mặc định chạy inventory (exit 0, ghi báo cáo JSON) — KHÔNG phải gate.
Chế độ --gate (dành cho release_runner SAU khi các nhóm rebuild theo TT 68
merge xong, khi kỳ vọng全部 xanh) fail nếu còn JUMP/CHAIN ngoài EXCEPTIONS.

Chạy: python3 -X utf8 -m tools.census.numbering_audit [--gate]
"""

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCKS = os.path.join(ROOT, "app", "data", "blocks")
OUT_DIR = os.path.join(ROOT, "generated_ho_so", "_visual_layout", "census")

TOPNUM = re.compile(r"^(\d{1,2})\s*[\.\)]\s*\S")
SUBNUM = re.compile(r"^\d{1,2}\s*\.\s*\d{1,2}")
GLUE = re.compile(r"[^\d\s:]\d{1,2}\s*:")

# Chuỗi companion: form chính -> form danh sách đi kèm (đánh số liên tục
# qua hai mẫu theo biểu mẫu Phụ lục I TT 68). Sửa/đ_expand theo census.
CONTINUATION_CHAINS = {
    "PLI_M03": "PLI_M06",   # DS thành viên TNHH 2TV+
    "PLI_M04": "PLI_M08",   # DS cổ đông CTCP (sáng lập + NĐT NN)
    "PLI_M05": "PLI_M09",   # DS thành viên công ty hợp danh
}

# Ngoại lệ có chủ đích (mỗi dòng một lý do — KHÔNG nới vô căn cứ):
# - PLI_M09: mất mục 1..7 + vùng nhiễm lặp "1. Thông tin thành viên/cổ đông"
#   (D3.1/D3.2=A) — chờ lane m09-rebuild dựng lại theo Phụ lục I Mẫu 9 TT 68.
EXCEPTIONS = {
    "PLI_M09",
}


def runtext(blk):
    parts = []
    for r in blk.get("runs", []):
        if isinstance(r, dict) and "text" in r:
            parts.append(str(r["text"]))
    return "".join(parts)


def extract_sequences(blocks):
    """Trả về list các chuỗi đánh số top-level liên tiếp (restart = chuỗi mới)."""
    seq = []
    for blk in blocks:
        if blk.get("t") != "p" or blk.get("role") != "section-heading":
            continue
        txt = runtext(blk).strip()
        if SUBNUM.match(txt):
            continue
        m = TOPNUM.match(txt)
        if not m:
            continue
        n = int(m.group(1))
        if seq and n <= seq[-1][0]:
            seq = []  # restart (variant / sub-document mới)
        seq.append((n, txt))
    return seq


def audit_form(fid, blocks):
    issues = []
    seq = extract_sequences(blocks)
    nums = [n for n, _ in seq]
    for (a, ta), (b, tb) in zip(seq, seq[1:]):
        if b > a + 1:
            issues.append({
                "class": "JUMP", "detail": "%d -> %d" % (a, b),
                "where": "%s | %s" % (ta[:48], tb[:48]),
            })
    glue = []
    for blk in blocks:
        if blk.get("t") != "p":
            continue
        txt = runtext(blk).strip()
        if GLUE.search(txt):
            glue.append(txt[:60])
    return nums, issues, glue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 nếu còn JUMP/CHAIN ngoài EXCEPTIONS")
    args = ap.parse_args()

    report = {}
    for path in sorted(glob.glob(os.path.join(BLOCKS, "*.json"))):
        fid = os.path.basename(path)[:-5]
        blocks = json.loads(open(path, encoding="utf-8").read())["blocks"]
        nums, issues, glue = audit_form(fid, blocks)
        entry = {}
        if issues:
            entry["issues"] = issues
        if glue:
            entry["glue_footnote"] = glue
        if entry:
            report[fid] = entry

    # B. chuỗi companion
    chains = {}
    for main_id, comp_id in sorted(CONTINUATION_CHAINS.items()):
        try:
            main_last = max(extract_sequences(
                json.loads(open(os.path.join(BLOCKS, main_id + ".json"),
                                encoding="utf-8").read())["blocks"]),
                default=(0, ""), key=lambda t: t[0])[0]
            comp_first = min(extract_sequences(
                json.loads(open(os.path.join(BLOCKS, comp_id + ".json"),
                                encoding="utf-8").read())["blocks"]),
                default=(0, ""), key=lambda t: t[0])[0]
        except FileNotFoundError:
            chains["%s->%s" % (main_id, comp_id)] = "MISSING-FORM"
            continue
        ok = comp_first == main_last + 1
        chains["%s->%s" % (main_id, comp_id)] = {
            "main_last": main_last, "comp_first": comp_first, "ok": ok}

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "numbering_report.json")
    full = {"generated_by": "tools/census/numbering_audit.py",
            "forms_scanned": len(glob.glob(os.path.join(BLOCKS, "*.json"))),
            "continuation_chains": chains, "forms": report}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=1)

    n_issue = sum(1 for v in report.values() if "issues" in v)
    n_glue = sum(1 for v in report.values() if "glue_footnote" in v)
    print("numbering_audit: %s forms scanned, %s forms có JUMP, %s forms có GLUE"
          % (full["forms_scanned"], n_issue, n_glue))
    for key, ch in chains.items():
        if isinstance(ch, dict):
            print("  chain %-16s main_last=%s comp_first=%s %s"
                  % (key, ch["main_last"], ch["comp_first"],
                     "OK" if ch["ok"] else "GAP"))
    for fid, v in sorted(report.items()):
        for it in v.get("issues", []):
            print("  JUMP %-10s %s %s" % (fid, it["detail"], it["where"]))
    print("report ->", os.path.relpath(out_path, ROOT))

    if args.gate:
        # EXCEPTIONS áp cho JUMP theo form (form đang chờ rebuild theo TT 68);
        # chain GAP của cặp có form thuộc EXCEPTIONS cũng tạm dung nạp tới khi
        # lane rebuild merge — khi đó EXCEPTIONS phải rỗng.
        jump_block = any(
            it["class"] == "JUMP" for fid, v in report.items()
            if fid not in EXCEPTIONS for it in v.get("issues", []))
        chain_block = any(
            isinstance(c, dict) and not c["ok"]
            for key, c in chains.items()
            if not any(fid in key for fid in EXCEPTIONS))
        return 1 if (jump_block or chain_block) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
