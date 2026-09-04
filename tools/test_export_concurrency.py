# -*- coding: utf-8 -*-
"""test_export_concurrency.py — [6V-V0/I1] chống hồi quy concurrency export.

Sự kiện 2026-09-04: release runner đỏ giả 56 PASS / 1 FAIL trên chính HEAD
294604c vốn xanh 57/0 — hai tiến trình soffice dùng CHUNG profile mặc định
LibreOffice chồng nhau → thằng sau exit=1. Sau V0 mọi lời gọi soffice đã qua
profile cách ly /tmp riêng (app_web.main._run_soffice). Suite này pin hành vi
đó bằng 2 export THẬT chạy song song:

  - spawn 2 process python, mỗi process export PLI_M01 + PLII_M08 × fixture
    valid-full qua ĐÚNG đường production (Bridge.export format both);
  - mỗi process phải: 0 error, PDF tồn tại > 0 bytes;
  - 2 process dùng pid khác nhau → 2 bộ profile /tmp khác nhau (spy rmtree
    ghi lại từng profile đã dọn; hai bộ không được có path trùng);
  - profile phải được dọn sạch (không còn /tmp/lo_prof_* của run này);
  - tổng runtime < 90s.

Chạy:  python3 -X utf8 -m tools.test_export_concurrency
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMS = ("PLI_M01", "PLII_M08")
FIXTURE = "valid-full"
CASE_ID = "conc_export"          # CHUNG cho 2 worker — giống 2 runner song song
RUNTIME_BUDGET_S = 90.0
TIMEOUT_S = 240                  # timeout cứng mỗi worker (chat hơn budget)

# Worker chạy trong process riêng: export thật qua Bridge + spy rmtree để
# ghi lại MỌI profile LibreOffice đã dọn (chứng minh profile riêng + dọn sạch).
_WORKER = r"""
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import app_web.main as m
from tools.phase5_fixtures import build_fixture, ValueFactory
from tools.phase5_visual_gate import BLOCKS_DIR

cleaned_profiles = []
_real_rmtree = m.shutil.rmtree
def _spy_rmtree(p, *a, **k):
    if "lo_prof_" in str(p):
        cleaned_profiles.append(str(p))
    return _real_rmtree(p, *a, **k)
m.shutil.rmtree = _spy_rmtree

maps = json.loads((Path(sys.argv[1]) / "app" / "data" / "form_maps.json")
                  .read_text(encoding="utf-8"))
data = {}
for fid in (%(forms)s):
    blk = {}
    bp = BLOCKS_DIR / ("%%s.json" %% fid)
    if bp.exists():
        blk = json.loads(bp.read_text(encoding="utf-8"))
    data.update(build_fixture(fid, maps[fid], "%(fixture)s", blk, ValueFactory()))

t0 = time.time()
r = m.Bridge().export({"case_id": "%(case)s", "format": "both",
                       "forms": [{"id": f} for f in (%(forms)s)],
                       "data": data})
elapsed = time.time() - t0
pdfs = []
for name in r.get("files") or []:
    p = Path(r["dir"]) / (name.rsplit(".", 1)[0] + ".pdf")
    pdfs.append({"pdf": p.name,
                 "size": p.stat().st_size if p.exists() else -1})
print("WORKER-RESULT " + json.dumps({
    "ok": bool(r.get("ok")), "errors": r.get("errors") or [],
    "pid": os.getpid(), "pdfs": pdfs,
    "profiles_cleaned": cleaned_profiles, "seconds": round(elapsed, 1),
}))
"""


def main() -> int:
    t0 = time.time()
    results = {}
    # spawn 2 worker song song bằng Popen rồi chờ cả hai
    code = _WORKER % {"forms": ", ".join('"%s"' % f for f in FORMS),
                      "fixture": FIXTURE, "case": CASE_ID}
    procs = {}
    for side in ("A", "B"):
        procs[side] = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-c", code, str(ROOT)],
            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace")
    for side, proc in procs.items():
        out, err = proc.communicate(timeout=TIMEOUT_S)
        line = next((ln for ln in reversed(out.splitlines())
                     if ln.startswith("WORKER-RESULT ")), "")
        if proc.returncode != 0 or not line:
            print("FAIL worker %s exit=%s tail=%s"
                  % (side, proc.returncode, (out + err).strip()[-400:]))
            return 1
        results[side] = json.loads(line[len("WORKER-RESULT "):])
    elapsed = time.time() - t0

    for side in ("A", "B"):
        r = results[side]
        if not r["ok"] or r["errors"]:
            print("FAIL worker %s errors=%s" % (side, r["errors"]))
            return 1
        if len(r["pdfs"]) != len(FORMS) or any(p["size"] <= 0 for p in r["pdfs"]):
            print("FAIL worker %s pdfs=%s" % (side, r["pdfs"]))
            return 1
        if not r["profiles_cleaned"]:
            print("FAIL worker %s không thấy profile nào được dọn "
                  "(spy rmtree không bắt được /tmp/lo_prof_*)" % side)
            return 1
        print("PASS worker %s: pid=%s, %d pdf >0 bytes, %d profile đã dọn, %.1fs"
              % (side, r["pid"], len(r["pdfs"]), len(r["profiles_cleaned"]),
                 r["seconds"]))

    # 2 process → 2 pid → 2 bộ profile RIÊNG (không có path trùng)
    pa, pb = set(results["A"]["profiles_cleaned"]), set(results["B"]["profiles_cleaned"])
    if results["A"]["pid"] == results["B"]["pid"]:
        print("FAIL 2 worker trùng pid=%s — không phải 2 process" % results["A"]["pid"])
        return 1
    if pa & pb:
        print("FAIL 2 worker dùng CHUNG profile: %s" % sorted(pa & pb))
        return 1
    print("PASS 2 bộ profile riêng biệt: |A|=%d |B|=%d trùng=%d"
          % (len(pa), len(pb), len(pa & pb)))

    leftover = sorted(glob.glob("/tmp/lo_prof_%s_*" % CASE_ID))
    if leftover:
        print("FAIL profile sót chưa dọn: %s" % leftover)
        return 1
    print("PASS /tmp không còn profile của run này (đã dọn hết)")

    # dọn thư mục export của worker (evidence tạm, không để lại rác repo)
    import shutil
    for p in glob.glob(str(ROOT / "generated_ho_so" / ("%s*" % CASE_ID))):
        if p.endswith(".zip"):
            Path(p).unlink(missing_ok=True)
        else:
            shutil.rmtree(p, ignore_errors=True)

    if elapsed >= RUNTIME_BUDGET_S:
        print("FAIL runtime %.1fs vượt budget %.0fs" % (elapsed, RUNTIME_BUDGET_S))
        return 1
    print("PASS tổng runtime song song %.1fs < %.0fs" % (elapsed, RUNTIME_BUDGET_S))
    print("Tổng kết: 8 PASS / 0 FAIL — concurrency export an toàn (V0-I1 đóng)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
