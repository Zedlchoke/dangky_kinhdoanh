# [integ(F0L) 2026-09-06] Census band tên chủ thể SAU migrate current-law
# (L-2026: TT 121/2026/TT-BTC thay 9 mẫu). Read-only đối với app/: chỉ ghi
# 2 file docs/audits/header_name_census_f0l_<date>.{json,md} (không đè
# header_name_census_2026-09-05.*).
#
# Premise cũ (census 2026-09-05): 22 fillable-header-slot; PLI_M12 là
# needs-owner vì "nguồn mất ô tên + TT 121 đã thay mẫu".
# Hiện trạng: M12 đã migrate theo TT 121/2026 (ảnh p50) — template CÓ band
# 'TÊN DOANH NGHIỆP' ở trang đầu -> 23 fillable-header-slot; adjudication
# theo tools/header_name_binding.json (21 bind + 2 blocked_owner).
# Evidence: chạy tools.census.header_name_census (raw scan) tại worktree
# final-integration — PLI_M12 para=0 band=before-band 'TÊN DOANH NGHIỆP'.
#
# Chạy:  python3 -X utf8 -m tools.census.header_name_census_f0l
from __future__ import annotations

import datetime
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from tools.census.header_name_census import (  # noqa: E402
    fold,
    scan_template,
)

ROOT = Path(__file__).resolve().parent.parent.parent
BINDING_PATH = ROOT / "tools" / "header_name_binding.json"
DOCS = ROOT / "docs" / "audits"

BAND_LABELS = ("ten doanh nghiep", "ten ho kinh doanh")

# Các mẫu migrate F0L cần đối chiếu "không phát sinh band mới" (task F0L-3c)
MIGRATED_SAMPLES = ["PLII_M01", "PLI_M02", "PLI_M03", "PLI_M04", "PLI_M05",
                    "PLI_M27", "PLI_M30"]


def base_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def classify(fid: str, occ: dict, binding: dict) -> dict:
    """Phân loại MỘT occurrence trong vùng band theo ngữ nghĩa F0L.

    fillable-header-slot  = nhãn 'TÊN DOANH NGHIỆP|TÊN HỘ KINH DOANH' ở ô
                            (0,0) của band-table HOẶC paragraph band có
                            dòng kẻ điền tên.
    legal-title/subtitle  = nhãn thân/tiêu đề nằm TRƯỚC tiêu đề biểu mẫu
                            (band_end suy từ title) — không phải ô band.
    """
    f = fold(occ["text"])
    is_slot = (f.startswith(BAND_LABELS)
               and (occ["band_region"] == "band-table"
                    or occ["fill_line"] or occ["para_has_fill"]))
    entry = {
        "para_idx": occ["para_idx"],
        "line_idx": occ["line_idx"],
        "table_cell": occ.get("table_cell"),
        "band_region": occ["band_region"],
        "text": occ["text"],
        "classification": "legal-title/subtitle",
    }
    if is_slot:
        entry["classification"] = "fillable-header-slot"
        b = binding.get("forms", {}).get(fid)
        if b:
            entry["adjudication"] = "bound"
            entry["binding_key"] = b["key"]
            entry["binding_label"] = b["label"]
        elif fid in binding.get("blocked_owner", {}):
            entry["adjudication"] = "blocked_owner"
            entry["binding_note"] = binding["blocked_owner"][fid]["reason"]
        else:
            entry["adjudication"] = "unadjudicated"
    return entry


def main() -> None:
    maps = json.loads((ROOT / "app/data/form_maps.json").read_text(
        encoding="utf-8"))
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    generated = datetime.date.today().isoformat()

    out = {
        "generated": generated,
        "base_head": base_head(),
        "base_head_note": (
            "[integ(F0L) 2026-09-06] census band tên chủ thể sau migrate "
            "current-law L-2026 (TT 121/2026/TT-BTC). Phiên bản mới — KHÔNG "
            "đè docs/audits/header_name_census_2026-09-05.* (vẫn là base "
            "cho phần phân loại toàn corpus + no-signature verdicts)."),
        "method": (
            "raw scan bằng tools/census/header_name_census.py "
            "(scan_template trên 87 template app/templates/*.docx) + "
            "phân loại vùng band theo header_name_binding.json"),
        "forms": {},
    }

    slot_rows = []
    migrated_new_band = []
    for fid in maps:
        info = scan_template(fid, ROOT / "app/templates" / f"{fid}.docx")
        band_occ = [o for o in info["occurrences"]
                    if o["band_region"] != "after-band"]
        classified = [classify(fid, o, binding) for o in band_occ]
        out["forms"][fid] = {
            "band_occurrences": classified,
            "band_end_idx": info["band_end_idx"],
            "title_idx": info["title_idx"],
            "quoc_hieu_idx": info["quoc_hieu_idx"],
            "no_band": len(band_occ) == 0,
        }
        for c in classified:
            if c["classification"] == "fillable-header-slot":
                slot_rows.append((fid, c))
                if fid in MIGRATED_SAMPLES and fid not in (
                        "PLI_M27", "PLI_M30"):
                    migrated_new_band.append(fid)

    # ---- summary ---------------------------------------------------------
    cls_cnt = Counter(c["classification"] for v in out["forms"].values()
                      for c in v["band_occurrences"])
    bound = [r for r in slot_rows if r[1].get("adjudication") == "bound"]
    blocked = [r for r in slot_rows if r[1].get("adjudication") == "blocked_owner"]
    unadj = [r for r in slot_rows if r[1].get("adjudication") == "unadjudicated"]
    out["summary"] = {
        "band_region_occurrences": sum(cls_cnt.values()),
        "classification_counts": dict(cls_cnt),
        "fillable_header_slot": len(slot_rows),
        "bound": len(bound),
        "blocked_owner": len(blocked),
        "unadjudicated": len(unadj),
        "m12_delta": (
            "PLI_M12: needs-owner (2026-09-05) -> BOUND dn.ten_tieng_viet "
            "(current-law TT 121/2026, ảnh p50; L-2026)"),
        "migrated_samples_no_new_band": sorted(
            set(MIGRATED_SAMPLES) - set(migrated_new_band)),
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    json_path = DOCS / f"header_name_census_f0l_{generated}.json"
    md_path = DOCS / f"header_name_census_f0l_{generated}.md"
    json_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- markdown --------------------------------------------------------
    L: list[str] = []
    A = L.append
    A("# HEADER-NAME CENSUS — F0L (post-migration current-law, READ-ONLY)")
    A("")
    A(f"- Generated: {generated}  |  base HEAD: `{out['base_head']}`")
    A("- Phạm vi: vùng band (từ đầu tài liệu tới tiêu đề biểu mẫu) của 87 "
      "template `app/templates/<fid>.docx`. Phân loại toàn corpus + "
      "no-signature verdicts: xem `header_name_census_2026-09-05.*` "
      "(vẫn còn hiệu lực).")
    A("- Mục đích: rebaseline census sau migrate L-2026 (TT 121/2026/TT-BTC) "
      "— đối chiếu.allowlist HEADER_BAND_FORMS (23 mẫu) + "
      "tools/header_name_binding.json.")
    A("")
    A("## 1. Tóm tắt vùng band")
    A("")
    A("| Chỉ số | Giá trị |")
    A("|---|---|")
    A(f"| Band-region occurrences | {sum(cls_cnt.values())} |")
    A(f"| fillable-header-slot | **{len(slot_rows)}** (2026-09-05: 22; "
      "+PLI_M12) |")
    A(f"| — đã bind (header_name_binding.json) | {len(bound)} |")
    A(f"| — blocked_owner | {len(blocked)} (`{'`, `'.join(f for f, _ in blocked) or '—'}`) |")
    A(f"| — unadjudicated | {len(unadj)} (phải = 0) |")
    A(f"| legal-title/subtitle trong vùng band | {cls_cnt.get('legal-title/subtitle', 0)} |")
    A("")
    A("## 2. Delta so với census 2026-09-05")
    A("")
    A("| Mẫu | Trước | Sau | Evidence |")
    A("|---|---|---|---|")
    A("| PLI_M12 | needs-owner (premise cũ: nguồn mất ô tên + TT 121 đã "
      "thay mẫu) | **fillable-header-slot, BOUND `dn.ten_tieng_viet`** | "
      "template M12 2026 (ảnh p50) có band 'TÊN DOANH NGHIỆP' ở trang đầu; "
      "nguồn migrate có khối 4 paragraph header chuẩn; thân có "
      "`{dn.ten_tieng_viet}` (form_maps fields[6]) |")
    A("| Các mẫu migrate còn lại (PLII_M01, PLI_M02–M05, PLI_M27, PLI_M30) "
      "| — | **không phát sinh band mới** | census raw: không occurrence "
      "loại fillable-header-slot mới ngoài M12; PLI_M27/M30 giữ band đã "
      "allowlist từ 2026-09-05 |")
    A("")
    A("## 3. Bảng 23 fillable-header-slot")
    A("")
    A("| Form | Label | Vị trí | Adjudication | Key |")
    A("|---|---|---|---|---|")
    for fid, c in sorted(slot_rows):
        loc = c["table_cell"] or f"para {c['para_idx']}"
        adj = c.get("adjudication", "?")
        key = c.get("binding_key", "—") if adj == "bound" else (
            "blocked: " + (c.get("binding_note", "")[:60] + "…"
                           if c.get("binding_note") else "—")
            if adj == "blocked_owner" else "⚠ CHƯA adjudicate")
        A(f"| {fid} | {c['text'][:40]} | `{loc}` | {adj} | {key} |")
    A("")
    A("## 4. Dữ liệu thô từng form")
    A("")
    A("Xem `" + json_path.name + "` — `forms[<fid>]`: band_occurrences "
      "(đã phân loại), band_end_idx, title_idx, quoc_hieu_idx, no_band.")
    A("")
    A("---")
    A("Sinh tự động bởi `tools/census/header_name_census_f0l.py` "
      "[integ(F0L)]; raw scan: `tools/census/header_name_census.py`.")
    md_path.write_text("\n".join(L), encoding="utf-8")
    print("WROTE", json_path)
    print("WROTE", md_path)
    print("summary:", json.dumps(out["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
