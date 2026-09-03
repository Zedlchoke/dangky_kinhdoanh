#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase5_word_open_loop.py — mở từng DOCX corpus bằng Microsoft Word thật
(16.16.27) qua AppleScript, chụp màn hình từng file, ghi verdict per file.

Verdict per file:
  PASS_OPEN_DIRECT — document mở (Word trả tên document), không sheet/dialog.
  FAIL_CORRUPT_DIALOG — Word báo corrupt (dialog "problem with its contents").
  FAIL_RECOVERY_REQUIRED — Word mở nhưng có sheet/dialog phục hồi.
  FAIL_TIMEOUT — AppleEvent timeout / không mở được.
Chạy:  python3 -X utf8 tools/phase5_word_open_loop.py
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "generated_ho_so" / "_visual_layout" / "phase5_word_open" / "shots"
INVENTORY = (ROOT / "generated_ho_so" / "_visual_layout" /
             "phase5_word_open" / "inventory.json")

OPEN_SCRIPT = '''on run argv
    set fpath to item 1 of argv
    set outPng to item 2 of argv
    -- [Phase 5] Word sandboxed: AppleEvent `open` gây dialog "Grant File
    -- Access" từng file; `open -a` (LaunchServices) cấp quyền ngầm nên
    -- luôn mở được. AppleScript chỉ dùng để đọc trạng thái + đóng.
    do shell script "open -a Microsoft\\\\ Word " & quoted form of fpath
    delay 5
    set docName to ""
    tell application "Microsoft Word"
        try
            set docName to name of active document
        end try
    end tell
    set sheetCount to -1
    set dlgCount to -1
    try
        tell application "System Events"
            tell process "Microsoft Word"
                set sheetCount to count of sheets of window 1
                set dlgCount to count of windows whose role is "AXDialog"
            end tell
        end tell
    end try
    do shell script "screencapture -x " & quoted form of outPng
    delay 1
    tell application "Microsoft Word"
        try
            close every document saving no
        end try
    end tell
    return (docName) & "||" & (sheetCount as string) & "||" & (dlgCount as string)
end run
'''

DISMISS_SCRIPT = '''on run
    tell application "System Events"
        tell process "Microsoft Word"
            try
                key code 53
                try
                    click button "OK" of sheet 1 of window 1
                end try
            end try
        end tell
    end tell
end run
'''


def main() -> int:
    import argparse
    global OPEN_SCRIPT, DISMISS_SCRIPT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "generated_ho_so"),
                    help="thư mục gốc chứa các dir DOCX corpus con")
    ap.add_argument("--pattern", default="phase5_word_open_*",
                    help="glob tên thư mục corpus con trong --root")
    ap.add_argument("--inventory", default=str(INVENTORY),
                    help="đường dẫn inventory.json ghi kết quả")
    args = ap.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)
    open_sc = "/tmp/dkdn_word_open.applescript"
    Path(open_sc).write_text(OPEN_SCRIPT, encoding="utf-8")
    dis_sc = "/tmp/dkdn_word_dismiss.applescript"
    Path(dis_sc).write_text(DISMISS_SCRIPT, encoding="utf-8")

    dirs = sorted(glob.glob(str(Path(args.root) / args.pattern)))
    inv_path = Path(args.inventory)
    jobs = []  # (form_id, variant, path)
    for d in dirs:
        for f in sorted(glob.glob(d + "/*.docx")):
            jobs.append({"form_id": Path(f).stem, "variant": "",
                         "path": f, "dir": d})
    # variant từ tên dir: phase5_word_open_<variant>_<ts> (riêng M72)
    for j in jobs:
        base = Path(j["dir"]).name.replace("phase5_word_open_", "")
        parts = base.rsplit("_", 1)
        j["variant"] = parts[0] if (j["form_id"] == "PLI_M72" and
                                    len(parts) == 2 and
                                    not parts[0].isdigit()) else ""
    print("jobs:", len(jobs))
    word_version = "16.16.27"
    records = []
    t0 = time.time()
    for i, j in enumerate(jobs):
        shot = SHOTS / ("%s%s.png" % (j["form_id"],
                                      ("_" + j["variant"]) if j["variant"] else ""))
        try:
            proc = subprocess.run(
                ["osascript", open_sc, j["path"], str(shot)],
                capture_output=True, text=True, timeout=90)
            out = (proc.stdout or "").strip()
            parts = out.split("||")
            doc_name = parts[0] if parts else ""
            try:
                sheets = int(parts[1]) if len(parts) > 1 else -1
            except ValueError:
                sheets = -1
            try:
                dlgs = int(parts[2]) if len(parts) > 2 else -1
            except ValueError:
                dlgs = -1
            if proc.returncode != 0 and "timed out" in (proc.stderr or ""):
                verdict = "FAIL_TIMEOUT"
            elif "corrupt" in (proc.stderr or ""):
                verdict = "FAIL_CORRUPT_DIALOG"
            elif not doc_name:
                verdict = "FAIL_TIMEOUT"
            elif sheets > 0 or dlgs > 0:
                verdict = "FAIL_RECOVERY_REQUIRED"
            else:
                verdict = "PASS_OPEN_DIRECT"
        except subprocess.TimeoutExpired:
            verdict = "FAIL_TIMEOUT"
            doc_name, sheets, dlgs = "", -1, -1
            subprocess.run(["osascript", dis_sc], capture_output=True,
                           timeout=30)
            subprocess.run(["osascript", "-e",
                            'tell application "Microsoft Word" to '
                            'close every document saving no'],
                           capture_output=True, timeout=30)
        records.append({
            "form_id": j["form_id"], "variant": j["variant"],
            "export_path": j["path"], "word_version": word_version,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "document_name": doc_name, "sheets": sheets, "dialogs": dlgs,
            "direct_open_verdict": verdict,
            "screenshot": str(shot),
        })
        print("%3d/%d %-10s %-8s %s" % (i + 1, len(jobs), j["form_id"],
                                        j["variant"] or "-", verdict))
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        inv_path.write_text(json.dumps({
            "word_version": word_version,
            "generated": datetime.now().isoformat(timespec="seconds"),
            "elapsed_s": round(time.time() - t0, 1),
            "records": records}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    ok = sum(1 for r in records if r["direct_open_verdict"] == "PASS_OPEN_DIRECT")
    print("DONE: %d/%d PASS_OPEN_DIRECT" % (ok, len(records)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
