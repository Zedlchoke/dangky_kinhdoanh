# -*- coding: utf-8 -*-
"""phase5_export_corpus.py — Phase 5: xuất corpus qua ĐÚNG đường export
của app (Bridge.export -> write_rendered -> LibreOffice normalize) bằng dữ
liệu đại diện (dummy_data_from_map). PLI_M72 xuất 5 lần, mỗi lần một variant
(dn.loai_hinh + flag) — inventory ghi rõ mẫu + variant.

[Lane C F3, 2026-09-06] chuẩn bị corpus định danh MỚI (phase8f):
  - inventory render-unit đọc ĐỘNG từ form_maps qua
    phase5_fixtures.active_form_ids — KHÔNG còn kẹp cứng 87 form; form mang
    marker current_law_status inactive (vd PLI_M11 sau khi owner chốt loại
    khỏi catalog — TT 121/2026 bãi bỏ Mẫu 11) tự bị loại khỏi corpus và
    được ghi log; marker CHƯA tồn tại => không skip form nào;
  - --outdir chỉ định corpus dir mới (mặc định phase8f/<ts>) — không đè
    corpus cũ phase7v/final;
  - KHÔNG pin số trang: tool không đụng pagination; identity hồ sơ nằm ở
    manifest do phase5_visual_gate ghi (records[] + pages[] + hash).

Chạy:  python3 -X utf8 -m tools.phase5_export_corpus [--outdir <dir>] \
           [--forms PLI_M09,PLI_M01]
Output: JSON ra stdout (inventory + batch + m72 + SUMMARY).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_web.main import Bridge                      # noqa: E402
from tools.docx_render import dummy_data_from_map    # noqa: E402
from tools.phase5_fixtures import active_form_ids    # noqa: E402

# Corpus dir mới mặc định — phase8f, KHÔNG đè phase7v/final (chỉ đọc).
DEFAULT_CORPUS_NAME = "phase8f"

M72_VARIANTS = [
    ("DNTN", "loai_hinh_dntn"),
    ("TNHH_1TV", "loai_hinh_tnhh_1tv"),
    ("TNHH_2TV", "loai_hinh_tnhh_2tv"),
    ("CTCP", "loai_hinh_ctcp"),
    ("DHDN", "loai_hinh_dhdn"),
]


def default_corpus_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ROOT / "generated_ho_so" / DEFAULT_CORPUS_NAME / ts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="",
                    help="corpus dir mới (mặc định generated_ho_so/%s/<ts>) "
                         "— không đè corpus cũ phase7v" % DEFAULT_CORPUS_NAME)
    ap.add_argument("--forms", default="all",
                    help="subset form để smoke, vd PLI_M09,PLI_M01")
    args = ap.parse_args()

    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    # inventory ĐỘNG từ form_maps + marker current_law_status (F3)
    form_ids, skipped = active_form_ids(maps, log=print)
    spec_manifest = json.loads((ROOT / "app" / "data" / "table_specs" /
                                "manifest.json").read_text(encoding="utf-8"))
    spec_ids = {f["form_id"] for f in spec_manifest["forms"]}
    unknown = sorted(set(form_ids) - spec_ids)
    assert not unknown, ("form_maps có form ngoài table_specs manifest: %r"
                         % unknown)
    if args.forms != "all":
        want = {f.strip() for f in args.forms.split(",") if f.strip()}
        form_ids = [f for f in form_ids if f in want]
        assert form_ids, "subset --forms không khớp inventory động"
    print(json.dumps({"inventory": {"active": len(form_ids),
                                    "skipped": skipped,
                                    "fixtures": 5,
                                    "render_units": len(form_ids) * 5}},
                     ensure_ascii=False))

    bridge = Bridge()

    # ---- 1) các mẫu thường (M72 riêng) ----
    payload = {"case_id": "phase5_word_open", "format": "docx",
               "forms": [{"id": fid} for fid in form_ids if fid != "PLI_M72"]}
    data = {}
    for fid in payload["forms"]:
        data.update(dummy_data_from_map(maps[fid["id"]]))
    payload["data"] = data
    r1 = bridge.export(payload)
    out_dir = r1.get("dir")
    print(json.dumps({"batch": {"ok": r1.get("ok"),
                                "files": len(r1.get("files") or []),
                                "errors": r1.get("errors") or [],
                                "dir": out_dir}}, ensure_ascii=False))

    # ---- 2) PLI_M72 x5 variant ----
    base72 = dummy_data_from_map(maps["PLI_M72"])
    m72 = []
    for value, flag in M72_VARIANTS:
        d = dict(base72)
        d["dn.loai_hinh"] = value
        d[flag] = "X"
        r = bridge.export({"case_id": "phase5_word_open_%s" % value.lower(),
                           "format": "docx",
                           "forms": [{"id": "PLI_M72"}], "data": d})
        m72.append({"variant": value, "flag": flag, "ok": r.get("ok"),
                    "files": r.get("files") or [],
                    "errors": r.get("errors") or [],
                    "dir": r.get("dir")})
        print(json.dumps({"m72": m72[-1]}, ensure_ascii=False))

    print(json.dumps({"SUMMARY": {"batch_ok": r1.get("ok"),
                                  "inventory_active": len(form_ids),
                                  "inventory_skipped": skipped,
                                  "corpus_dir": args.outdir or
                                  str(default_corpus_dir()),
                                  "m72_variants_ok":
                                      sum(1 for x in m72 if x["ok"])}},
                     ensure_ascii=False))
    return 0 if r1.get("ok") and all(x["ok"] for x in m72) else 1


if __name__ == "__main__":
    sys.exit(main())
