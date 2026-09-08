# -*- coding: utf-8 -*-
"""header_semantics.py — [F3H 2026-09-08] HEADER-SUBJECT-SEMANTICS detector
(tách khỏi D17 — D17 giữ nguyên hợp đồng sync cũ; lớp này thêm ngữ nghĩa
ROLE theo census docs/audits/header_semantic_census.json — 87 form, 5 role,
registry tools/header_name_binding.json section "roles").

Mã lỗi (đều vào HARD_FAIL_KEYS qua detector key "D19_header_semantics"):

  BAND_REQUIRED_MISSING      : form role required_band_mirror/required_band_input
                               nhưng template/blocks/PDF KHÔNG có band chủ thể.
  BAND_FORBIDDEN_PRESENT     : form role output_mirror/no_subject_band nhưng
                               template/blocks CÓ band chủ thể (fixture bắt
                               buộc PLI_M72: cấm tự thêm band). Band "TÊN TỔ
                               CHỨC" (M79/M80) KHÔNG phải band chủ thể —
                               is_header_band_table không tính nó.
  BAND_LABEL_REMOVED         : band có nhưng nhãn pháp định "TÊN DOANH
                               NGHIỆP/TÊN HỘ KINH DOANH" đã bị xoá/sửa.
  BAND_VALUE_OR_SLOT_MISSING : band thiếu run giá trị/slot (structural) hoặc
                               PDF valid-full không có dòng giá trị dưới nhãn
                               (fill-line input cũng phải còn nhìn thấy).
  BAND_WRONG_KEY             : band bind/render SAI key — giá trị band không
                               khớp canonical key của census.
  DUPLICATE_EDITABLE         : >=2 run input cùng canonical key CÙNG tầm nhìn
                               (band_input + thân, hoặc 2 thân) — vi phạm
                               "tên nhập đúng 1 lần". Fire khi >=2 input cùng
                               key cùng tầm nhìn VÀ (a) role=required_band_
                               input hoặc (b) một input nằm ở ô (0,0) band.
                               Body-body cùng key trên form đa mục (PLII_M02
                               A/C, PLI_M12, PLI_M75) là MỘT draft key store
                               đồng bộ — adjudicated GREEN; run dưới cond
                               khác nhau (M72: 5 biến thể) không đếm trùng.
  STALE_MIRROR               : mode mirror — giá trị band đúng canonical nhưng
                               thân KHÔNG còn giá trị đó (band đổi, thân chưa
                               đổi / mirror bị cắt).
  LEGAL_SUBTITLE_MUTATED     : nhãn phụ pháp định bị sửa — M72: 5 subtitle
                               biến thể "(TÊN DOANH NGHIỆP TƯ NHÂN)…"; M73/
                               M74: tiêu đề section "1. Tên doanh nghiệp".

Hai lớp:
  det_structural(form_id, blocks)            — DOCX/blocks, chạy mọi fixture.
  det_pdf(pages, form_id, data, full_text)   — PDF valid-full (cần giá trị
                                               canonical để đối chiếu).
  det_record(...)                            — hợp hai lớp cho gate loop.

Chạy độc lập: python3 -X utf8 tools/header_semantics.py  (sweep 87 form).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = ROOT / "tools" / "header_name_binding.json"

# role được phép có band chủ thể
BAND_REQUIRED_ROLES = ("required_band_mirror", "required_band_input")
# role CẤM có band chủ thể
BAND_FORBIDDEN_ROLES = ("output_mirror", "no_subject_band")

# nhãn phụ pháp định M72 (anchor của tag_m72_sections) + M73/M74
_DEFAULT_LEGAL_SUBTITLES = {
    "PLI_M72": ["(TÊN DOANH NGHIỆP TƯ NHÂN)",
                "(TÊN CÔNG TY TNHH MỘT THÀNH VIÊN)",
                "(TÊN CÔNG TY TNHH HAI THÀNH VIÊN)",
                "(TÊN CÔNG TY CỔ PHẦN)",
                "(TÊN CÔNG TY HỢP DANH)"],
    "PLI_M73": ["1. Tên doanh nghiệp"],
    "PLI_M74": ["1. Tên doanh nghiệp"],
}


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", (text or "").lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return out.replace("đ", "d")


def _squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", fold(text)).strip()


_registry: dict | None = None


def load_registry(path: Path = _REGISTRY_PATH) -> dict:
    global _registry
    if _registry is None:
        try:
            _registry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _registry = {}
    return _registry


def _role_of(form_id: str, registry: dict | None) -> str | None:
    reg = registry or load_registry()
    entry = (reg.get("roles") or {}).get(form_id) or {}
    return entry.get("role")


def _canonical_key(form_id: str, registry: dict | None) -> str | None:
    reg = registry or load_registry()
    entry = (reg.get("roles") or {}).get(form_id) or {}
    if entry.get("canonical_key"):
        return entry["canonical_key"]
    bind = (reg.get("forms") or {}).get(form_id) or {}
    return bind.get("key")


def _band_label(form_id: str, registry: dict | None) -> str | None:
    reg = registry or load_registry()
    bind = (reg.get("forms") or {}).get(form_id) or {}
    return bind.get("label")


# ---------------------------------------------------------------------------
# Blocks helpers
# ---------------------------------------------------------------------------

def _iter_blocks(blocks) -> list[dict]:
    if blocks is None:
        return []
    if isinstance(blocks, dict):
        return blocks.get("blocks") or []
    return list(blocks)


def _run_keys(runs: list[dict]) -> list[tuple[str, str]]:
    """[(kind, key)] với kind ∈ {'input','mirror'}."""
    out = []
    for r in runs or []:
        if isinstance(r.get("input"), dict) and r["input"].get("key"):
            out.append(("input", r["input"]["key"]))
        elif isinstance(r.get("mirror"), dict) and r["mirror"].get("key"):
            out.append(("mirror", r["mirror"]["key"]))
    return out


def _iter_runs(blocks_list: list[dict]):
    """Yield (runs, cond_signature, where) cho mọi p/table-cell."""
    for bi, blk in enumerate(blocks_list):
        t = blk.get("t")
        if t == "p":
            cond = tuple(sorted(blk.get("cond") or []))
            yield blk.get("runs") or [], cond, "p%d" % bi
        elif t == "table":
            for ri, row in enumerate(blk.get("rows") or []):
                for ci, cell in enumerate(row.get("cells") or []):
                    yield cell.get("runs") or [], (), \
                        "tbl%d.r%d.c%d" % (bi, ri, ci)


def _cell_text(cell: dict) -> str:
    parts = []
    for r in cell.get("runs") or []:
        if isinstance(r.get("text"), str):
            parts.append(r["text"])
    return "".join(parts)


# ---------------------------------------------------------------------------
# det_structural — DOCX/blocks layer (chạy mọi fixture)
# ---------------------------------------------------------------------------

def det_structural(form_id: str, blocks, registry: dict | None = None
                   ) -> list[dict]:
    reg = registry or load_registry()
    role = _role_of(form_id, reg)
    if role is None:
        return []
    blocks_list = _iter_blocks(blocks)
    if not blocks_list:
        return []
    hits: list[dict] = []

    band_tbls = [b for b in blocks_list
                 if b.get("t") == "table" and b.get("band") == "header"]

    # ---- BAND_REQUIRED_MISSING / BAND_FORBIDDEN_PRESENT ----
    if role in BAND_REQUIRED_ROLES and not band_tbls:
        hits.append({"code": "BAND_REQUIRED_MISSING", "role": role})
    if role in BAND_FORBIDDEN_ROLES and band_tbls:
        hits.append({"code": "BAND_FORBIDDEN_PRESENT", "role": role,
                     "n_band_tables": len(band_tbls)})

    canonical = _canonical_key(form_id, reg)
    label = _band_label(form_id, reg)

    # ---- band nội dung: nhãn + key ----
    if band_tbls and role in BAND_REQUIRED_ROLES:
        cell = band_tbls[0]["rows"][0]["cells"][0]
        text = _cell_text(cell)
        label_f = _squeeze(label or "")
        if label_f and label_f not in _squeeze(text):
            hits.append({"code": "BAND_LABEL_REMOVED", "label": label,
                         "cell_text": text[:60]})
        keys = _run_keys(cell.get("runs") or [])
        wrong = sorted({k for _kind, k in keys if k != canonical})
        if canonical and wrong:
            hits.append({"code": "BAND_WRONG_KEY", "expect": canonical,
                         "got": wrong})
        elif canonical and not any(k == canonical for _k, k in keys):
            # slot trống thật (không có run nào) — nếu slot bị CHIẾM bởi key
            # khác thì WRONG_KEY ở trên đã chẩn đoán đúng một lỗi, không bắn
            # thêm VALUE_OR_SLOT_MISSING cho cùng một cell.
            hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING",
                         "key": canonical,
                         "note": "band cell thiếu run giá trị/slot"})

    # ---- DUPLICATE_EDITABLE: "tên nhập đúng 1 lần" theo role ----
    # Fire khi >=2 input cùng canonical key CÙNG tầm nhìn (cond giống nhau)
    # VÀ (a) form role=required_band_input — band là ô nhập DUY NHẤT, thêm
    # ô nào nữa là trùng; hoặc (b) một trong các input nằm ở ô (0,0) band —
    # band mirror thành input thứ hai (mutation cấm của WAVE v7).
    # ADJUDICATED GREEN (không fire): 2+ input body cùng key ở các SECTION
    # pháp lý khác nhau của form đa mục (PLII_M02 mục A/C, PLI_M12 mục
    # "chấm dứt tồn tại"/"thay đổi tên", PLI_M75 thân + khối DN chủ quản) —
    # một draft key, store đồng bộ một giá trị, người dùng KHÔNG nhập 2 lần;
    # M72 5 biến thể loại hình dưới cond khác nhau → tầm nhìn khác nhau.
    if canonical:
        seen: dict[tuple, list] = {}
        band_locations = set()
        if band_tbls:
            for ri, cell in enumerate(
                    band_tbls[0]["rows"][0].get("cells") or []):
                band_locations.add("tbl%d.r0.c%d" % (
                    blocks_list.index(band_tbls[0]), ri))
        for runs, cond, where in _iter_runs(blocks_list):
            for kind, key in _run_keys(runs):
                if kind == "input" and key == canonical:
                    seen.setdefault(cond, []).append(where)
        for cond, ws in seen.items():
            if len(ws) < 2:
                continue
            if role == "required_band_input" or \
                    any(w in band_locations for w in ws):
                hits.append({"code": "DUPLICATE_EDITABLE", "key": canonical,
                             "cond": list(cond), "locations": ws[:8]})
                break

    # ---- LEGAL_SUBTITLE_MUTATED ----
    reg_entry = (reg.get("roles") or {}).get(form_id) or {}
    subs = reg_entry.get("legal_subtitles") \
        or _DEFAULT_LEGAL_SUBTITLES.get(form_id)
    if subs:
        hay = _squeeze("".join(
            "".join(r.get("text", "") for r in (runs or []))
            for runs, _c, _w in _iter_runs(blocks_list)))
        for sub in subs:
            if _squeeze(sub) not in hay:
                hits.append({"code": "LEGAL_SUBTITLE_MUTATED",
                             "subtitle": sub})
    return hits


# ---------------------------------------------------------------------------
# det_pdf — PDF layer (chỉ valid-full: cần giá trị canonical để đối chiếu)
# ---------------------------------------------------------------------------

_DASH_LINE = re.compile(r"^[-_.\u2013\u2014\u2026 ]{3,}$")
_MOTTO_FOLDS = ("cong hoa xa hoi chu nghia viet nam",
                "doc lap - tu do - hanh phuc")


def _page_lines_of(page) -> list[dict]:
    lines: dict[tuple, list] = {}
    for w in page.get("words") or []:
        lines.setdefault((w[5], w[6]), []).append(w)
    out = []
    for _bk, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        out.append({
            "text": " ".join(w[4] for w in ws),
            "fold": _squeeze(" ".join(w[4] for w in ws)),
            "x0": min(w[0] for w in ws), "x1": max(w[2] for w in ws),
            "y0": min(w[1] for w in ws), "y1": max(w[3] for w in ws),
        })
    return out


def _clean_band_piece(f: str) -> str:
    for m in _MOTTO_FOLDS:
        f = f.replace(m, " ")
    f = _DASH_LINE.sub(" ", f)
    return re.sub(r"\s+", " ", f).strip(" .,-")


def det_pdf(pages: list, form_id: str, data: dict | None,
            full_text: str | None = None,
            registry: dict | None = None) -> list[dict]:
    reg = registry or load_registry()
    role = _role_of(form_id, reg)
    if role not in BAND_REQUIRED_ROLES or not pages:
        return []
    canonical = _canonical_key(form_id, reg)
    if not canonical:
        return []
    label_f = _squeeze(_band_label(form_id, reg) or "")
    hits: list[dict] = []
    lines = _page_lines_of(pages[0])

    # ---- BAND_REQUIRED_MISSING (PDF): mất luôn nhãn ở trang 1 ----
    label = None
    for ln in lines:
        f = re.sub(r"[0-9]{1,2}$", "", ln["fold"])
        if f == label_f or (label_f and label_f in f
                            and len(f) <= len(label_f) + 2):
            label = ln
            break
    if label is None:
        return [{"code": "BAND_REQUIRED_MISSING", "layer": "pdf",
                 "label": label_f}]

    # ---- dòng giá trị / fill-line dưới nhãn ----
    below = [ln for ln in lines
             if ln["y0"] > label["y1"] - 2
             and not (ln["x1"] < label["x0"] - 30
                      or ln["x0"] > label["x0"] + 420)]
    below.sort(key=lambda ln: ln["y0"])
    value = (data or {}).get(canonical)
    hay = re.sub(r"\s+", " ", fold(
        full_text if full_text is not None
        else "\n".join(p.get("text", "") for p in pages)))
    hay = re.sub(r"\s+", " ", hay)
    fold_v = re.sub(r"\s+", " ", fold(value or ""))

    if not below:
        hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING", "layer": "pdf",
                     "key": canonical})
        return hits
    # mảnh band: tới 3 dòng dưới nhãn, bỏ motto + dòng kẻ
    pieces = []
    for ln in below[:3]:
        p = _clean_band_piece(ln["fold"])
        if p and any(c.isalpha() for c in p):
            pieces.append(p)
    if not pieces:
        hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING", "layer": "pdf",
                     "key": canonical,
                     "band_line": below[0]["text"][:60]})
        return hits

    band_ok = bool(fold_v) and any(
        fold_v in p or p in fold_v for p in pieces)
    band_input = role == "required_band_input"
    if band_ok:
        n = hay.count(fold_v) if fold_v else 0
        if band_input:
            # band là ô nhập duy nhất: giá trị phải xuất hiện ĐÚNG 1 lần
            if n >= 2:
                hits.append({"code": "DUPLICATE_EDITABLE", "layer": "pdf",
                             "key": canonical, "count": n})
            elif n == 0:
                hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING",
                             "layer": "pdf", "key": canonical})
        else:
            # mirror: band + thân phải CÙNG có giá trị (count >= 2)
            if n < 2:
                hits.append({"code": "STALE_MIRROR", "layer": "pdf",
                             "key": canonical, "count": n,
                             "value": (value or "")[:60]})
    else:
        # band hiển thị giá trị KHÁC canonical
        hits.append({"code": "BAND_WRONG_KEY", "layer": "pdf",
                     "expect": canonical,
                     "band_value": below[0]["text"][:60]})
    return hits


def det_record(form_id: str, blocks, pages=None, data=None,
               full_text: str | None = None, pdf_checks: bool = False,
               registry: dict | None = None) -> list[dict]:
    """Hợp hai lớp cho gate loop. pdf_checks=True chỉ khi fixture valid-full
    (giá trị canonical có mặt để đối chiếu — như D17)."""
    hits = det_structural(form_id, blocks, registry)
    if pdf_checks:
        hits += det_pdf(pages or [], form_id, data, full_text, registry)
    return hits


# ---------------------------------------------------------------------------
# CLI sweep: chạy det_structural trên toàn bộ blocks hiện có
# ---------------------------------------------------------------------------

def main() -> int:
    maps_path = ROOT / "app" / "data" / "form_maps.json"
    blocks_dir = ROOT / "app" / "data" / "blocks"
    maps = json.loads(maps_path.read_text(encoding="utf-8"))
    bad = 0
    missing_roles = []
    for fid in sorted(maps):
        p = blocks_dir / ("%s.json" % fid)
        blocks = json.loads(p.read_text(encoding="utf-8")) if p.exists() \
            else None
        hits = det_structural(fid, blocks)
        if _role_of(fid, None) is None:
            missing_roles.append(fid)
        for h in hits:
            bad += 1
            print("HIT %-9s %s" % (fid, json.dumps(h, ensure_ascii=False)))
    if missing_roles:
        print("THIẾU ROLE:", missing_roles)
    print("-" * 60)
    print("sweep %d form: %d hit, %d form thiếu role" % (
        len(maps), bad, len(missing_roles)))
    return 1 if (bad or missing_roles) else 0


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
