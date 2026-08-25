"""Smoke test KHÔNG GUI cho asset giao diện app_web.

Chạy:  python -m tools.smoke_web_assets

Kiểm tra:
1. Các file UI bắt buộc tồn tại và decode được bằng UTF-8.
2. index.html nạp script đúng thứ tự: form-domain.js -> render.js -> app.js,
   và có các hook DOM chính theo docs/htkk-ui-contract.md.
3. Cú pháp JS hợp lệ (gọi node --check nếu máy có node).
4. Mock pilot đủ blocks_PLI_M02.json / blocks_PLI_M06.json / vsic_mini.json.

Không đụng production code; không mở cửa sổ pywebview.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "app_web" / "ui"
MOCK = UI / "mock"

REQUIRED_FILES = [
    UI / "index.html",
    UI / "style.css",
    UI / "render.js",
    UI / "app.js",
    UI / "form-domain.js",
    MOCK / "blocks_PLI_M02.json",
    MOCK / "blocks_PLI_M06.json",
    MOCK / "vsic_mini.json",
]

SCRIPT_ORDER = ["form-domain.js", "render.js", "app.js"]

DOM_HOOKS = [
    'id="pages"',
    'id="tabs"',
    'id="save-status"',
    'id="doc-title"',
    'id="err-list"',
    'id="btn-check"',
    'chk-check-all',
    'id="vsic-pop"',
    'id="toasts"',
    "form-domain.js",
    "render.js",
    "app.js",
]

passed, failed = 0, 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}" + (f"  [{extra}]" if extra else ""))


def main() -> int:
    for p in REQUIRED_FILES:
        ok = p.is_file()
        check(f"ton tai: {p.relative_to(ROOT)}", ok)
        if ok and p.suffix in {".js", ".html", ".css", ".json"}:
            try:
                p.read_text(encoding="utf-8")
                check(f"UTF-8 hop le: {p.name}", True)
            except UnicodeDecodeError as exc:
                check(f"UTF-8 hop le: {p.name}", False, repr(exc))

    html = (UI / "index.html").read_text(encoding="utf-8")
    pos = [html.find(f'"{s}"') for s in SCRIPT_ORDER]
    check("index.html nap du 3 script", all(x >= 0 for x in pos))
    if all(x >= 0 for x in pos):
        check("thu tu script form-domain -> render -> app", pos == sorted(pos),
              str(pos))
    for hook in DOM_HOOKS:
        check(f"DOM hook: {hook}", hook in html)

    for name in ("blocks_PLI_M02.json", "blocks_PLI_M06.json"):
        try:
            data = json.loads((MOCK / name).read_text(encoding="utf-8"))
            check(f"mock {name} JSON hop le, co id+blocks",
                  isinstance(data.get("id"), str) and isinstance(data.get("blocks"), list))
        except Exception as exc:  # noqa: BLE001
            check(f"mock {name} JSON hop le", False, repr(exc))

    node = shutil.which("node")
    if node:
        for js in ("render.js", "app.js", "form-domain.js"):
            r = subprocess.run([node, "--check", str(UI / js)],
                               capture_output=True, text=True)
            check(f"node --check {js}", r.returncode == 0, r.stderr.strip()[:200])
    else:
        print("SKIP  node --check (khong co node trong PATH)")

    print("-" * 60)
    print(f"Ket qua: {passed} PASS / {failed} FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
