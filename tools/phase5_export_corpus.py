# -*- coding: utf-8 -*-
"""phase5_export_corpus.py — Phase 5: xuất corpus 87/87 qua ĐÚNG đường export
của app (Bridge.export -> write_rendered -> LibreOffice normalize) bằng dữ
liệu đại diện (dummy_data_from_map). PLI_M72 xuất 5 lần, mỗi lần một variant
(dn.loai_hinh + flag) — inventory ghi rõ mẫu + variant.

Chạy:  python3 -X utf8 tools/phase5_export_corpus.py
Output: generated_ho_so/phase5_word_open/<ts>/ + docs ghi JSON ra stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_web.main import Bridge                      # noqa: E402
from tools.docx_render import dummy_data_from_map    # noqa: E402

M72_VARIANTS = [
    ("DNTN", "loai_hinh_dntn"),
    ("TNHH_1TV", "loai_hinh_tnhh_1tv"),
    ("TNHH_2TV", "loai_hinh_tnhh_2tv"),
    ("CTCP", "loai_hinh_ctcp"),
    ("DHDN", "loai_hinh_dhdn"),
]


def main() -> int:
    maps = json.loads((ROOT / "app" / "data" / "form_maps.json")
                      .read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "app" / "data" / "table_specs" /
                           "manifest.json").read_text(encoding="utf-8"))
    form_ids = sorted(f["form_id"] for f in manifest["forms"])
    assert len(form_ids) == 87, "manifest phải 87 form, thấy %d" % len(form_ids)

    bridge = Bridge()

    # ---- 1) 86 mẫu (M72 riêng) ----
    payload = {"case_id": "phase5_word_open", "format": "docx",
               "forms": [{"id": fid} for fid in form_ids if fid != "PLI_M72"]}
    data = {}
    for fid in payload["forms"]:
        data.update(dummy_data_from_map(maps[fid["id"]]))
    payload["data"] = data
    r1 = bridge.export(payload)
    out_dir = r1.get("dir")
    print(json.dumps({"batch86": {"ok": r1.get("ok"),
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

    print(json.dumps({"SUMMARY": {"forms_86_ok": r1.get("ok"),
                                  "m72_variants_ok":
                                      sum(1 for x in m72 if x["ok"])}},
                     ensure_ascii=False))
    return 0 if r1.get("ok") and all(x["ok"] for x in m72) else 1


if __name__ == "__main__":
    sys.exit(main())
