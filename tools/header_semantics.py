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
  BAND_LABEL_PRESENT         : [Pin sync — owner band-label removal
                               2026-09-08] owner đã XOÁ nhãn "TÊN DOANH
                               NGHIỆP/TÊN HỘ KINH DOANH" khỏi ô band (commit
                               e148d83 — in ra CHỈ hiện tên) nên hiện trạng
                               CHUẨN là band KHÔNG có nhãn, chỉ còn the giá
                               trị; code (đổi nghĩa từ BAND_LABEL_REMOVED)
                               fire khi nhãn XUẤT HIỆN LẠI — artifact dựng
                               trước 2026-09-08 hoặc mutation trả nhãn về.
  BAND_VALUE_OR_SLOT_MISSING : band thiếu run giá trị/slot (structural) hoặc
                               PDF valid-full không có dòng giá trị ở vùng
                               band (fill-line input cũng phải còn nhìn
                               thấy).
  BAND_WRONG_KEY             : band bind/render SAI key — lớp PDF: giá trị
                               band KHÔNG được thân cùng tài liệu lặp lại và
                               cũng không khớp canonical ([dfix 2026-09-08]
                               so band-vs-thân IN-DOCUMENT, không so với
                               `data` fixture riêng — batch export gộp data
                               last-write-wins nên PDF thật render giá trị
                               merged; `data` chỉ còn vai trò chẩn đoán code
                               STALE_MIRROR vs BAND_WRONG_KEY).
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
  det_pdf(pages, form_id, data, full_text)   — PDF valid-full, so band-vs-thân
                                               IN-DOCUMENT (dfix 2026-09-08:
                                               data chỉ dùng chẩn đoán code).
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

    # ---- band nội dung: nhãn (đã bị xoá) + key ----
    if band_tbls and role in BAND_REQUIRED_ROLES:
        cell = band_tbls[0]["rows"][0]["cells"][0]
        text = _cell_text(cell)
        # [Pin sync — owner band-label removal 2026-09-08] commit e148d83:
        # hiện trạng CHUẨN là ô band CHỈ có the giá trị, KHÔNG có nhãn.
        # Nhãn xuất hiện lại = artifact cũ/mutation → BAND_LABEL_PRESENT.
        label_f = _squeeze(label or "")
        if label_f and label_f in _squeeze(text):
            hits.append({"code": "BAND_LABEL_PRESENT", "label": label,
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


def _band_slot_lines(lines: list) -> tuple[dict | None, list]:
    """[Pin sync — owner band-label removal 2026-09-08] neo vùng band bằng
    dòng quốc hiệu. Dòng giá trị band = các dòng TRONG CỘT TRÁI (x0 không
    vượt quá mốc quốc hiệu) nằm trong cửa sổ dọc quanh dòng quốc hiệu — bao
    cả dòng TRÊN nó vì tên dài wrap làm lệch baseline trái/phải. Trả về
    (dòng quốc hiệu, [dòng quốc hiệu] + slot theo y)."""
    motto = None
    for ln in lines:
        if _MOTTO_FOLDS[0] in ln["fold"]:
            motto = ln
            break
    if motto is None:
        return None, []
    lo, hi = motto["y0"] - 40.0, motto["y1"] + 40.0
    slot = [ln for ln in lines
            if ln is not motto
            and ln["x0"] <= motto["x0"] + 20
            and lo <= ln["y0"] <= hi]
    slot.sort(key=lambda ln: ln["y0"])
    return motto, [motto] + slot[:4]


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
    """[Pin sync — owner band-label removal 2026-09-08] commit e148d83 xoá
    nhãn khỏi ô band nên vùng band trên PDF KHÔNG còn dòng nhãn để neo.
    Neo mới: dòng quốc hiệu (motto) trang 1 — luôn có trong band chủ thể và
    không có ở bảng dữ liệu. Dòng giá trị band = phần còn lại của dòng
    motto (PDF hay gom baseline trái+phải thành một dòng) cộng tối đa 2
    dòng dưới nó trong cùng cột trái (tên dài wrap).

    [dfix 2026-09-08] Hợp đồng lớp PDF là IN-DOCUMENT: giá trị band (đọc từ
    chính tài liệu) phải được THÂN cùng tài liệu lặp lại — mirror count >= 2
    (band + thân), band_input count == 1 (band là ô nhập duy nhất). KHÔNG
    đối chiếu `data` fixture riêng: batch export gộp data mọi form vào MỘT
    payload, key chung last-write-wins (dn.ten_tieng_viet do PLI_M79 ghi
    cuối) → PDF thật render giá trị MERGED ở cả band lẫn thân (D17 PASS
    450/450 theo cùng hợp đồng), còn `data` per-form thì giá trị khác → so
    band-vs-fixture bắn nhầm BAND_WRONG_KEY trên 23/23 form band-required.
    `data` chỉ còn dùng để CHẨN ĐOÁN code khi band/thân lệch nhau (đúng
    canonical → STALE_MIRROR; khác → BAND_WRONG_KEY) — pass/fail thuần
    trong-document."""
    reg = registry or load_registry()
    role = _role_of(form_id, reg)
    if role not in BAND_REQUIRED_ROLES or not pages:
        return []
    canonical = _canonical_key(form_id, reg)
    if not canonical:
        return []
    hits: list[dict] = []
    lines = _page_lines_of(pages[0])

    # ---- BAND_REQUIRED_MISSING (PDF): mất luôn band (không còn quốc hiệu) ----
    motto, slot = _band_slot_lines(lines)
    if motto is None:
        return [{"code": "BAND_REQUIRED_MISSING", "layer": "pdf"}]

    value = (data or {}).get(canonical)
    hay = re.sub(r"\s+", " ", fold(
        full_text if full_text is not None
        else "\n".join(p.get("text", "") for p in pages)))
    hay = re.sub(r"\s+", " ", hay)
    fold_v = re.sub(r"\s+", " ", fold(value or ""))

    # mảnh band: dòng quốc hiệu + các dòng slot (bỏ motto + dòng kẻ)
    pieces = []
    for ln in slot:
        p = _clean_band_piece(ln["fold"])
        if p and any(c.isalpha() for c in p):
            pieces.append(p)
    if not pieces:
        hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING", "layer": "pdf",
                     "key": canonical,
                     "band_line": (slot[-1]["text"] if len(slot) > 1
                                   else motto["text"])[:60]})
        return hits

    band_input = role == "required_band_input"
    # [dfix 2026-09-08] so band-vs-thân trong document: đếm TỪNG mảnh band
    # trong toàn văn (tên dài wrap 2 dòng → mỗi mảnh vẫn khớp đoạn thân
    # tương ứng; mảnh lân cận ngoài giá trị — vd tên cơ quan — không ga lỗi).
    counts = [hay.count(p) for p in pieces]
    if band_input:
        # band là ô nhập duy nhất: MỖI mảnh giá trị phải xuất hiện ĐÚNG 1 lần
        if any(c >= 2 for c in counts):
            hits.append({"code": "DUPLICATE_EDITABLE", "layer": "pdf",
                         "key": canonical,
                         "count": max(counts)})
        elif any(c == 0 for c in counts):
            hits.append({"code": "BAND_VALUE_OR_SLOT_MISSING",
                         "layer": "pdf", "key": canonical})
    else:
        # mirror: band + thân phải CÙNG có giá trị — BẤT KỲ mảnh band nào
        # được thân lặp lại (count >= 2) là đủ; band chỉ gồm mảnh đơn-lần
        # (count 1: chỉ band có, thân không) hoặc mảnh lạ (count 0: band
        # hiện giá trị không tồn tại trong tài liệu) đều là lệch band-thân.
        if not any(c >= 2 for c in counts):
            # chẩn đoán: band đúng canonical (mảnh nào khớp giá trị canonical
            # của fixture) → mirror bị cắt (STALE_MIRROR); band hiện giá trị
            # khác hẳn → bind sai key (BAND_WRONG_KEY).
            matches_canonical = bool(fold_v) and any(
                fold_v in p or p in fold_v for p in pieces)
            hits.append({
                "code": "STALE_MIRROR" if matches_canonical
                else "BAND_WRONG_KEY",
                "layer": "pdf", "key": canonical,
                "count": max(counts) if counts else 0,
                "band_value": (slot[-1]["text"] if len(slot) > 1
                               else motto["text"])[:60],
                **({"value": value[:60]} if matches_canonical else {})})
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
