# -*- coding: utf-8 -*-
"""Release test runner chinh thuc cua du an (R0.4 — master plan checkpoint d882793).

Liệt kê TOÀN BỘ suite Node/Python bắt buộc trong "Bộ regression release tối
thiểu" (PLAN.md). Mỗi suite chạy đúng một lần, ghi exit code thật và phân loại:

  PASS     — exit code 0.
  FAIL     — exit code != 0.
  NOT RUN  — bỏ qua vì thiếu dependency, kèm lý do. KHÔNG bao giờ tính là PASS.

Verdict tổng:
  PASS     — mọi suite critical đều PASS (không có critical NOT RUN).
  FAIL     — còn ≥1 FAIL hoặc ≥1 critical NOT RUN ("release-critical NOT RUN
             = FAIL" theo R7).

Suite nào thêm về sau (component/domain mới) PHẢI đăng ký vào SUITES ở đây,
không chạy lẻ ngoài runner khi báo cáo release.

Cách dùng:
  python3 -X utf8 -m tools.release_runner            # chạy toàn bộ
  python3 -X utf8 -m tools.release_runner --list     # chỉ liệt kê
  python3 -X utf8 -m tools.release_runner --json out.json
  python3 -X utf8 -m tools.release_runner --only test_dom
  python3 -X utf8 -m tools.release_runner --verbose  # in tail output suite FAIL

Exit code runner: 0 = verdict PASS; 1 = verdict FAIL; 2 = lỗi cấu hình/môi trường.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_S = int(os.environ.get("RELEASE_RUNNER_TIMEOUT", "600"))

# ---------------------------------------------------------------------------
# Danh sách suite chuẩn (khớp PLAN.md "Bộ regression release tối thiểu").
# type: node | module | compileall
# requires: dependency keys phải có sẵn thì mới chạy; thiếu -> NOT RUN.
# critical: False chỉ dùng cho suite tiện ích không chặn release.
# ---------------------------------------------------------------------------
SUITES: list[dict] = [
    # --- Node (app_web) ---
    {"name": "test_dom",                  "type": "node", "target": "app_web/test_dom.js"},
    {"name": "test_domain",               "type": "node", "target": "app_web/test_domain.js"},
    {"name": "test_grid",                 "type": "node", "target": "app_web/test_grid.js"},
    {"name": "test_loop_prod",            "type": "node", "target": "app_web/test_loop_prod.js"},
    {"name": "test_acceptance",           "type": "node", "target": "app_web/test_acceptance.js"},
    {"name": "test_form_flow",            "type": "node", "target": "app_web/test_form_flow.js"},
    {"name": "test_household_shared",     "type": "node", "target": "app_web/test_household_shared.js"},
    {"name": "test_form_grid_meta",       "type": "node", "target": "app_web/test_form_grid_meta.js"},
    {"name": "test_audit_p1_negative",    "type": "node", "target": "app_web/test_audit_p1_negative.js"},
    {"name": "test_m72_activation",       "type": "node", "target": "app_web/test_m72_activation.js"},
    {"name": "test_p12_m72_selector",     "type": "node", "target": "app_web/test_p12_m72_selector.js"},
    {"name": "test_p20_hardening",        "type": "node", "target": "app_web/test_p20_hardening.js"},
    {"name": "test_audit_wave_h_negative", "type": "node", "target": "app_web/test_audit_wave_h_negative.js"},
    {"name": "test_layout_l2_render",     "type": "node", "target": "app_web/test_layout_l2_render.js"},
    {"name": "test_output_table",         "type": "node", "target": "app_web/test_output_table.js"},
    {"name": "test_fixed_matrix",         "type": "node", "target": "app_web/test_fixed_matrix.js"},
    {"name": "test_nested_grid",          "type": "node", "target": "app_web/test_nested_grid.js"},
    {"name": "test_p2_migration",         "type": "node", "target": "app_web/test_p2_migration.js"},
    # --- Phase 4 (2026-09-03): row/blank-row contract corpus ---
    {"name": "test_row_contract_corpus",  "type": "node", "target": "app_web/test_row_contract_corpus.js"},
    # --- Wave B (2026-08-27): B1 runtime wiring + B3 wiring gate ---
    {"name": "test_runtime_tables",       "type": "node", "target": "app_web/test_runtime_tables.js"},
    {"name": "test_wiring_gate",          "type": "node", "target": "app_web/test_wiring_gate.js"},
    # --- P3 (2026-08-28): E2E / draft resilience / security / a11y ---
    {"name": "test_p3_e2e",               "type": "node", "target": "app_web/test_p3_e2e.js"},
    {"name": "test_p3_draft",             "type": "node", "target": "app_web/test_p3_draft.js"},
    {"name": "test_p3_security",          "type": "node", "target": "app_web/test_p3_security.js"},
    {"name": "test_p3_a11y",              "type": "node", "target": "app_web/test_p3_a11y.js", "preflight": "bind_localhost"},
    # --- Excel X1 (2026-08-28): lớp questionnaire (PLAN.md mục 4) ---
    {"name": "test_questionnaire",        "type": "module", "target": "tools.test_questionnaire"},
    # --- Excel X2 (2026-08-28): xuất phiếu xlsx ---
    {"name": "test_excel_export",         "type": "module", "target": "tools.test_excel_export"},
    # --- Excel X4 (2026-08-28): round-trip + negative ---
    {"name": "test_excel_roundtrip",      "type": "module", "target": "tools.test_excel_roundtrip"},
    {"name": "test_excel_negative",       "type": "module", "target": "tools.test_excel_negative"},
    # --- Python ---
    {"name": "p1_b_verify_m72",           "type": "module", "target": "tools.census.p1_b_verify_m72",
     "requires": ["python-docx"]},
    {"name": "p1_c_verify_plii_m02",      "type": "module", "target": "tools.census.p1_c_verify_plii_m02",
     "requires": ["python-docx"]},
    {"name": "test_m72_conditional_export", "type": "module", "target": "tools.test_m72_conditional_export",
     "requires": ["python-docx"]},
    {"name": "test_industry_formation",   "type": "module", "target": "tools.test_industry_formation",
     "requires": ["python-docx"]},
    {"name": "test_industry_change",      "type": "module", "target": "tools.test_industry_change",
     "requires": ["python-docx"]},
    # --- Wave B (2026-08-27): B2 generator/export ---
    {"name": "test_generator_deep_idempotency", "type": "module",
     "target": "tools.test_generator_deep_idempotency", "requires": ["python-docx"]},
    {"name": "test_export_grid_kinds",    "type": "module", "target": "tools.test_export_grid_kinds",
     "requires": ["python-docx"]},
    # --- Phase 4 (2026-09-03): row/blank-row contract ở lớp engine DOCX ---
    {"name": "test_row_contract_export",  "type": "module", "target": "tools.test_row_contract_export",
     "requires": ["python-docx"]},
    # --- Phase 5 (2026-09-03): fix bug owner (VSIC Bridge-first, loop-fld
    #     underline, chu_hkd.ho_ten M01, LO normalize outdir tạm) ---
    {"name": "test_phase5_ui_fixes",      "type": "module", "target": "tools.test_phase5_ui_fixes",
     "requires": ["python-docx"]},
    # --- Phase 5R0 (2026-09-03): gate visual — fixture semantic + detector
    #     hai chiều (bắt injected defect, qua nội dung hợp lệ). Suite synthetic
    #     này phải xanh tuyệt đối: nó là điều kiện tin gate corpus RED/GREEN.
    {"name": "test_phase5_visual_detectors", "type": "module",
     "target": "tools.test_phase5_visual_detectors", "requires": ["python-docx"]},
    {"name": "phase5_fixtures_selftest",  "type": "module", "target": "tools.phase5_fixtures"},
    {"name": "test_industry_household",   "type": "module", "target": "tools.test_industry_household",
     "requires": ["python-docx"]},
    {"name": "test_contract_release",     "type": "module", "target": "tools.test_contract_release",
     "requires": ["python-docx"]},
    {"name": "test_acceptance_docx",      "type": "module", "target": "tools.test_acceptance_docx",
     "requires": ["python-docx"]},
    {"name": "test_audit_p1_docx_negative", "type": "module", "target": "tools.test_audit_p1_docx_negative",
     "requires": ["python-docx"]},
    {"name": "audit_blocks_check",        "type": "module", "target": "tools.audit_blocks_check",
     "requires": ["python-docx"]},
    {"name": "audit_content_check",       "type": "module", "target": "tools.audit_content_check",
     "requires": ["python-docx"]},
    {"name": "audit_engine_test",         "type": "module", "target": "tools.audit_engine_test",
     "requires": ["python-docx"]},
    {"name": "smoke_web_assets",          "type": "module", "target": "tools.smoke_web_assets"},
    {"name": "build_manifest_deep",       "type": "module", "target": "tools.census.build_manifest",
     "args": ["--deep"]},
    {"name": "build_layout_manifest",     "type": "module", "target": "tools.census.build_layout_manifest"},
    # [Wave E 2026-09-03] Census gates vào runner theo finding auditor:
    # numbering (exit 0 sau batch 2) là release-critical; L1 (còn 4 STT-glue +
    # 2 digit-run BLOCKED_OWNER member grids — packet P2) và coverage (42 drift
    # đo được — packet P1/P2) là DIAGNOSTIC critical=False: hiển thị FAIL thật
    # trong runner mà không chặn checkpoint cho tới owner chốt.
    {"name": "numbering_audit_gate",      "type": "module", "target": "tools.census.numbering_audit",
     "args": ["--gate"]},
    {"name": "check_layout_l1",           "type": "module", "target": "tools.census.check_layout_l1",
     "critical": False},
    {"name": "table_coverage_audit",      "type": "module", "target": "tools.census.table_coverage_audit",
     "args": ["--no-write"], "critical": False},
    {"name": "compileall",                "type": "compileall", "target": "app_web app_tk tools",
     "args": ["app_web", "app_tk", "tools"]},
]


def check_deps() -> tuple[dict[str, str | None], list[str]]:
    """Trả về {dep_key: version hoặc None nếu thiếu} và danh sách lỗi môi trường."""
    have: dict[str, str | None] = {}
    errors: list[str] = []

    node = shutil.which("node")
    if node is None:
        errors.append("node không có trong PATH — 13 suite Node sẽ NOT RUN")
        have["node"] = None
    else:
        v = subprocess.run([node, "--version"], capture_output=True, text=True)
        have["node"] = node
        have["node_version"] = v.stdout.strip() or "unknown"

    try:
        import docx  # noqa: F401
        import importlib.metadata as md
        have["python-docx"] = md.version("python-docx")
    except Exception:
        have["python-docx"] = None
        errors.append("python-docx chưa cài — các suite DOCX sẽ NOT RUN "
                      "(cài: pip install -r requirements-dev.txt)")
    return have, errors


def _preflight_bind_localhost() -> str | None:
    """Trả về lý do NOT RUN nếu tiến trình không được bind 127.0.0.1.

    Suite a11y cần HTTP server localhost; sandbox/CI có thể cấm bind (EPERM).
    Khi bị cấm: critical NOT RUN có lý do — KHÔNG ghi product FAIL giả
    (PLAN v4 Wave A bước 4). Release chính thức vẫn bắt buộc chạy a11y ở môi
    trường hỗ trợ, nên critical NOT RUN vẫn làm verdict FAIL.
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
    except OSError as exc:
        return ("preflight bind 127.0.0.1 bị chặn (%s) — môi trường không cho "
                "chạy a11y; chạy lại runner ngoài sandbox/môi trường cho phép"
                % exc)
    finally:
        s.close()
    return None


PREFLIGHTS = {
    "bind_localhost": _preflight_bind_localhost,
}


def build_cmd(suite: dict, deps: dict) -> tuple[list[str] | None, str | None]:
    """Trả về (argv, reason_not_run)."""
    missing = [r for r in suite.get("requires", []) if deps.get(r) is None]
    if missing:
        return None, "thiếu dependency: %s" % ", ".join(missing)
    pf_name = suite.get("preflight")
    if pf_name:
        pf = PREFLIGHTS.get(pf_name)
        if pf is None:
            return None, "preflight không rõ: %r" % pf_name
        reason = pf()
        if reason:
            return None, reason
    if suite["type"] == "node":
        return [deps["node"] or "node", suite["target"]], None
    if suite["type"] == "module":
        argv = [sys.executable, "-X", "utf8", "-m", suite["target"]]
        argv += suite.get("args", [])
        return argv, None
    if suite["type"] == "compileall":
        return [sys.executable, "-X", "utf8", "-m", "compileall", "-q"] + suite["args"], None
    return None, "type không hỗ trợ: %r" % suite["type"]


def run_suite(suite: dict, deps: dict) -> dict:
    start = time.time()
    result = {
        "name": suite["name"],
        "type": suite["type"],
        "target": suite["target"],
        "critical": suite.get("critical", True),
        "status": "NOT RUN",
        "exit_code": None,
        "seconds": None,
        "reason": None,
        "tail": "",
    }
    argv, reason = build_cmd(suite, deps)
    if argv is None:
        result["reason"] = reason
        return result
    try:
        proc = subprocess.run(
            argv, cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT_S,
        )
        result["exit_code"] = proc.returncode
        result["status"] = "PASS" if proc.returncode == 0 else "FAIL"
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            result["tail"] = "\n".join(out.strip().splitlines()[-25:])
        result["seconds"] = round(time.time() - start, 2)
    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["reason"] = "timeout sau %ss" % TIMEOUT_S
    except FileNotFoundError as exc:
        result["reason"] = "không chạy được %s: %s" % (argv[0], exc)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Release test runner chính thức")
    ap.add_argument("--list", action="store_true", help="chỉ liệt kê suite")
    ap.add_argument("--only", metavar="SUBSTR", help="chạy suite có tên chứa SUBSTR")
    ap.add_argument("--json", metavar="PATH", help="ghi báo cáo JSON ra PATH")
    ap.add_argument("--verbose", action="store_true", help="in tail output suite FAIL")
    args = ap.parse_args()

    deps, env_errors = check_deps()

    if args.list:
        for s in SUITES:
            req = ",".join(s.get("requires", [])) or "-"
            print("%-28s %-10s requires=%s" % (s["name"], s["type"], req))
        return 0

    suites = [s for s in SUITES if not args.only or args.only in s["name"]]
    if not suites:
        print("Không có suite khớp --only=%r" % args.only)
        return 2

    print("=" * 78)
    print("RELEASE TEST RUNNER — root %s" % ROOT)
    print("deps: node=%s python-docx=%s" % (
        deps.get("node_version") or deps.get("node") or "MISSING",
        deps.get("python-docx") or "MISSING"))
    for e in env_errors:
        print("ENV-WARN: %s" % e)
    print("=" * 78)

    results = [run_suite(s, deps) for s in suites]

    width = max(len(r["name"]) for r in results) + 2
    for r in results:
        line = "%-*s %-7s" % (width, r["name"], r["status"])
        if r["seconds"] is not None:
            line += " %6.1fs" % r["seconds"]
        if r["exit_code"] is not None:
            line += "  exit=%d" % r["exit_code"]
        if r["reason"]:
            line += "  (%s)" % r["reason"]
        print(line)
        if args.verbose and r["status"] == "FAIL" and r["tail"]:
            print("-" * 78)
            print(r["tail"])
            print("-" * 78)

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_nr = sum(1 for r in results if r["status"] == "NOT RUN")
    n_nr_crit = sum(1 for r in results if r["status"] == "NOT RUN" and r["critical"])
    crit_fail = any(r["status"] == "FAIL" and r["critical"] for r in results)

    print("=" * 78)
    print("Tổng: %d PASS / %d FAIL / %d NOT RUN (trong đó critical NOT RUN: %d)"
          % (n_pass, n_fail, n_nr, n_nr_crit))
    verdict = "PASS" if (not crit_fail and n_nr_crit == 0 and suites) else "FAIL"
    print("VERDICT: %s%s" % (
        verdict,
        "" if verdict == "PASS" else
        "  (critical FAIL hoặc critical NOT RUN đều làm verdict=FAIL; "
        "FAIL noncritical = diagnostic, không chặn)"))
    print("=" * 78)

    if args.json:
        report = {
            "root": str(ROOT),
            "deps": {k: v for k, v in deps.items()},
            "env_errors": env_errors,
            "results": results,
            "summary": {
                "pass": n_pass, "fail": n_fail, "not_run": n_nr,
                "not_run_critical": n_nr_crit, "verdict": verdict,
            },
        }
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("JSON report: %s" % args.json)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
