#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cap_von_specs.py — Lane CAP-VON (nguồn vốn điều lệ + thuế hộ kinh doanh).

Mệnh đề kiểm chứng cho đợt spec 2026-08-28 (docs/leader_handoff_excel_next.md
Việc 4.1 nguồn vốn PLI_M03/M04/M05/M12 + Việc 4.2 thuế PLII_M02 D5.2):

  [SPEC]    5 file spec của lane qua loader/validator v1 (tools/build_form_maps)
            với ĐÚNG tập section đã khai (không rộng hơn phạm vi lane).
  [EVD]     census manifest (app/data/table_specs/manifest.json) có evidence cho
            từng section: kind/semantic_key/status + heading/anchor; row id +
            column tag lấy ĐÚNG manifest.
  [NGUỒN]   legal_status.ref PHẢI trỏ văn bản hiện hành TT 121/2026/TT-BTC
            (Phụ lục thay Mẫu 3/4/5/12 của Phụ lục I TT 68/2025, hiệu lực
            21/8/2026) kèm số mẫu + mục; riêng PLII_M02 phải ghi rõ TT 121
            KHÔNG đụng Phụ lục II. Với mẫu nào spec không trỏ được bản hiện
            hành -> FAIL (không được lặng lẽ dựng theo bản cũ).
  [SHAPE]   sandbox rebuild (OUT_TPL/OUT_DATA ghi vào tmp, KHÔNG đụng
            app/templates / app/data): w:tbl đúng số hàng/cột, glue biến mất
            trong vùng [anchor, drop_until), chuỗi pháp lý dính kèm GIỮ
            (mệnh giá cổ phần M04 là input đã map).
  [TOKEN]   blocks sinh ra có ĐỦ the "<sem>.<row>.<tag>" cho mọi dòng input;
            dòng tổng CÓ the nhưng KHÔNG đăng ký form_maps.fields (outputOnly).
  [D1.1]    tổng = sum(...) đúng target_row/target_tag, phủ mọi cột số;
            idempotent 2 lần chạy.
  [D5.2]    PLII_M02: 3 cột chỉ tiêu/cũ/mới + đúng 2 chỉ tiêu thuế của mẫu II.2
            (5.1 địa chỉ nhận thông báo thuế, 5.2 tổng số lao động) + dòng
            tiếp diễn '-….'; section phần C (c5) KHÔNG được dựng vì 7 ô đã
            map sẵn -> phải còn nguyên trong blocks.
  [DROP]    drop_until='(?!)' phải là regex không khớp gì (mục cuối của nguồn).

Chạy: python3 -X utf8 -m tools.test_cap_von_specs   (từ root repo/worktree)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.build_form_maps as bfm          # noqa: E402
import tools.docx_to_blocks as dxtb          # noqa: E402
from tools.docx_render import (ExportTotalsError,      # noqa: E402
                               recompute_totals)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "app" / "data" / "table_specs" / "manifest.json"
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"

RESULTS: list[tuple[bool, str]] = []

# ---------------------------------------------------------------------------
# Nguồn chân lý của lane: (form, section_id) -> kỳ vọng cấu trúc
# ---------------------------------------------------------------------------
FORMS = {
    ("PLI_M03", "nguon_von_dieule"): {
        "group": "formation", "mau": 3, "pl": "I",
        "semantic_key": "nguon_von_dieu_le",
        "anchor_fold": "6. nguon von dieu le",
        # [Owner P1=A 2026-09-03] nguồn canonical giờ là bản ĐẦY ĐỦ (tách từ
        # _Bieu_mau_PL_I_II_full) — vùng bảng mục 6 kết thúc tại mục 7
        "drop_until": "^7\\. thanh vien cong ty",
        "columns": [None, "so_tien_vnd_va_tuong_duong", "ty_le"],
        "rows": ["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai",
                 "von_khac", "tong_cong"],
        "total_row": "tong_cong",
        "totals": {"so_tien_vnd_va_tuong_duong", "ty_le"},
        "table_shape": (6, 3),
        "kept": [],                              # không giữ paragraph nào trong vùng
        "law_ref": ["121/2026", "Mẫu số 03", "6. Nguồn vốn điều lệ"],
    },
    ("PLI_M04", "nguon_von_dieule"): {
        "group": "formation", "mau": 4, "pl": "I",
        "semantic_key": "nguon_von_dieu_le",
        "anchor_fold": "6. nguon von dieu le",
        "drop_until": "^7\\. thong tin ve co phan",
        "columns": [None, "so_tien_vnd_va_tuong_duong", "ty_le"],
        "rows": ["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai",
                 "von_khac", "tong_cong"],
        "total_row": "tong_cong",
        "totals": {"so_tien_vnd_va_tuong_duong", "ty_le"},
        "table_shape": (6, 3),
        "kept": [],
        "law_ref": ["121/2026", "Mẫu số 04", "6. Nguồn vốn điều lệ"],
    },
    ("PLI_M04", "co_cau_loai_co_phan"): {
        "group": "formation", "mau": 4, "pl": "I",
        "semantic_key": "co_cau_loai_co_phan",
        "anchor_fold": "7. thong tin ve co phan",
        "drop_until": "^thong tin ve co phan duoc quyen chao ban",
        "columns": [None, "so_luong", "gia_tri_vnd", "ty_le_so_von_dieule"],
        "rows": ["co_phan_pho_thong", "cp_uu_dai_bieu_quyet", "cp_uu_dai_co_tuc",
                 "cp_uu_dai_hoan_lai", "cp_uu_dai_khac", "tong_so"],
        "total_row": "tong_so",
        "totals": {"so_luong", "gia_tri_vnd", "ty_le_so_von_dieule"},
        "table_shape": (7, 4),
        # 'Mệnh giá cổ phần (VNĐ)' là input đã map của mục — GIỮ, không drop
        "kept": ["menh gia co phan"],
        "law_ref": ["121/2026", "Mẫu số 04", "7. Thông tin về cổ phần"],
    },
    ("PLI_M04", "co_phan_duoc_quyen_chao_ban"): {
        "group": "formation", "mau": 4, "pl": "I",
        "semantic_key": "co_phan_duoc_quyen_chao_ban",
        "anchor_fold": "thong tin ve co phan duoc quyen chao ban",
        # [Owner P1=A 2026-09-03] nguồn đầy đủ — vùng kết thúc tại mục 8
        "drop_until": "^8\\. co dong sang lap",
        "columns": [None, "so_luong"],
        "rows": ["co_phan_pho_thong", "cp_uu_dai_bieu_quyet", "cp_uu_dai_co_tuc",
                 "cp_uu_dai_hoan_lai", "cp_uu_dai_khac", "tong_so"],
        "total_row": "tong_so",
        "totals": {"so_luong"},
        "table_shape": (7, 2),
        "kept": [],
        "law_ref": ["121/2026", "Mẫu số 04",
                    "Thông tin về cổ phần được quyền chào bán"],
    },
    ("PLI_M05", "nguon_von_dieule"): {
        "group": "formation", "mau": 5, "pl": "I",
        "semantic_key": "nguon_von_dieu_le",
        "anchor_fold": "6. nguon von dieu le",
        "drop_until": "(?!)",
        "columns": [None, "so_tien_vnd_va_tuong_duong", "ty_le"],
        "rows": ["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai",
                 "von_khac", "tong_cong"],
        "total_row": "tong_cong",
        "totals": {"so_tien_vnd_va_tuong_duong", "ty_le"},
        "table_shape": (6, 3),
        "kept": [],
        "law_ref": ["121/2026", "Mẫu số 05", "6. Nguồn vốn điều lệ"],
    },
    ("PLI_M12", "nguon_von_dieule_sau_thay_doi"): {
        "group": "change", "mau": 12, "pl": "I",
        "semantic_key": "nguon_von_dieu_le_sau_thay_doi",
        "anchor_fold": "nguon von dieu le sau khi thay doi von dieu le",
        "drop_until": "^tai san gop von sau khi thay doi von dieu le",
        "columns": [None, "so_tien_vnd_va_tuong_duong", "ty_le"],
        "rows": ["von_ngan_sach_nha_nuoc", "von_tu_nhan", "von_nuoc_ngoai",
                 "von_khac", "tong_cong"],
        "total_row": "tong_cong",
        "totals": {"so_tien_vnd_va_tuong_duong", "ty_le"},
        "table_shape": (6, 3),
        "kept": [],
        "law_ref": ["121/2026", "Mẫu số 12",
                    "Nguồn vốn điều lệ sau khi thay đổi vốn điều lệ"],
    },
    ("PLII_M02", "a7_thue_chi_tieu_cu_moi"): {
        "group": "household", "mau": 2, "pl": "II",
        "semantic_key": "thue_chi_tieu_cu_moi",
        "anchor_fold": "dang ky bo sung, thay doi cac chi tieu dang ky thue nhu sau",
        "drop_until": "^b\\. dang ky cap nhat, bo sung, hieu dinh thong tin dang ky ho kinh doanh",
        "columns": [None, "thong_tin_dang_ky_cu", "thong_tin_dang_ky_moi"],
        "rows": ["chi_tieu_5_1_dia_chi_nhan_thong_bao_thue",
                 "chi_tieu_5_2_tong_so_lao_dong", "chi_tieu_khac"],
        "total_row": None,
        "totals": set(),
        "table_shape": (4, 3),
        "kept": [],
        "law_ref": ["TT 68/2025", "Mẫu số 2", "Phụ lục II"],
    },
}
SPEC_PATHS = {
    fid: ROOT / "tools" / "form_specs" / want["group"] / ("%s.json" % fid)
    for (fid, _sid), want in FORMS.items()
}


def check(name: str):
    def deco(fn):
        def run(*args, **kw):
            try:
                fn(*args, **kw)
                RESULTS.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                RESULTS.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                RESULTS.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    """Chung quy tắc với build_form_maps.fold (thường, bỏ dấu, đ->d)."""
    s = re.sub(r"\s+", " ", text or "").strip()
    nfkd = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace(
        "đ", "d")


def raw_spec(fid: str) -> dict:
    return json.loads(SPEC_PATHS[fid].read_text(encoding="utf-8-sig"))


def entries_of(fid: str) -> dict:
    return bfm.load_form_spec(fid)


def entry_for(fid: str, sid: str):
    ext = entries_of(fid)
    for e in ext["entries"]:
        if ext["specs_by_id"][e["spec"]].get("section_id") == sid:
            return e, ext["specs_by_id"][e["spec"]]
    raise AssertionError("%s: không có entry section_id=%r" % (fid, sid))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def template_hash(docx_path: Path) -> str:
    """sha256(word/document.xml dạng canonical) — BỎ zip metadata.

    python-docx ghi entry zip kèm date_time hiện tại nên hash byte thô của
    .docx đổi ngay cả khi nội dung giống hệt nhau; idempotency ở đây là
    SEMANTIC, cùng định nghĩa với test_p2c_capital_specs.template_hash.
    """
    with zipfile.ZipFile(docx_path) as zf:
        raw = zf.read("word/document.xml")
    return hashlib.sha256(
        ET.canonicalize(xml_data=raw.decode("utf-8")).encode("utf-8")
    ).hexdigest()


def nest(flat_values: dict) -> dict:
    """Key phẳng '<sem>.<row>.<tag>' -> cây dict như app_web/main.py đựng."""
    out: dict = {}
    for key, value in flat_values.items():
        cur = out
        parts = key.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return out


def manifest_sections() -> dict:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {f["form_id"]: {s["section_id"]: s for s in f["sections"]}
            for f in data["forms"]}


def block_folds(fid: str) -> list[str]:
    data = json.loads((BLOCKS_DIR / ("%s.json" % fid)).read_text(
        encoding="utf-8"))
    out = []
    for b in data["blocks"]:
        if b.get("t") == "table":
            out.append("[TBL]")
            continue
        out.append(fold("".join(str(r.get("text", ""))
                                for r in (b.get("runs") or []))))
    return out


def body_paragraphs(doc):
    for el in doc.element.body.iterchildren():
        if el.tag.endswith("}p"):
            yield Paragraph(el, doc)
        elif el.tag.endswith("}tbl"):
            yield Table(el, doc)


# ---------------------------------------------------------------------------
# [SPEC] validator + phạm vi
# ---------------------------------------------------------------------------
@check("[SPEC] 5 file spec qua validator v1, dung kind/section_id/semantic_key")
def t_spec_validate():
    for (fid, sid), want in FORMS.items():
        raw = raw_spec(fid)
        assert raw["form_id"] == fid, "%s: form_id lệch file" % fid
        ext = entries_of(fid)
        e, spec = entry_for(fid, sid)
        assert spec["kind"] == "fixed-matrix", \
            "%s/%s: kind %r" % (fid, sid, spec["kind"])
        assert spec["semantic_key"] == want["semantic_key"], \
            "%s/%s: semantic_key %r != %r" % (fid, sid, spec["semantic_key"],
                                              want["semantic_key"])
        assert e.get("no_default_drops") is True, \
            "%s/%s: cần no_default_drops=true" % (fid, sid)
        assert e.get("drop_until") == want["drop_until"], \
            "%s/%s: drop_until %r != %r" % (fid, sid, e.get("drop_until"),
                                            want["drop_until"])
        ls = e.get("legal_status") or {}
        assert ls.get("blocked") is False, "%s/%s: đang blocked" % (fid, sid)
        assert ls.get("ref") and ls.get("question"), \
            "%s/%s: thiếu ref/question (gap phải ghi nhận)" % (fid, sid)
        # cột 0 là cột nhãn readonly, các cột còn lại đúng tag
        got_cols = [c["tag"] for c in spec["columns"]]
        assert got_cols == want["columns"], \
            "%s/%s: columns %r != %r" % (fid, sid, got_cols, want["columns"])
        assert spec["columns"][0]["input_type"] == "readonly", \
            "%s/%s: cột 0 phải readonly" % (fid, sid)
        # đúng 1 dòng tổng output_only, đứng CUỐI
        total_rows = [r for r in spec["fixed_rows"] if r["output_only"]]
        if want["total_row"]:
            assert len(total_rows) == 1 and \
                spec["fixed_rows"][-1]["id"] == want["total_row"], \
                "%s/%s: đúng 1 dòng tổng cuối" % (fid, sid)
        else:
            assert not total_rows, "%s/%s: không có dòng tổng" % (fid, sid)
        assert [r["id"] for r in spec["fixed_rows"]] == want["rows"], \
            "%s/%s: fixed_rows %r != %r" % (fid, sid,
                                            [r["id"] for r in spec["fixed_rows"]],
                                            want["rows"])
        # D1.1=A: totals sum() phủ đúng các cột số
        totals = {t["target_tag"]: t for t in spec["totals"]}
        assert set(totals) == want["totals"], \
            "%s/%s: totals %r != %r" % (fid, sid, sorted(totals),
                                        sorted(want["totals"]))
        for t in spec["totals"]:
            assert t["target_row"] == want["total_row"], \
                "%s/%s: totals target_row %r" % (fid, sid, t["target_row"])
            assert re.fullmatch(r"sum\([a-z0-9_]+\)", t["formula"]), \
                "%s/%s: formula %r (chỉ sum() cho section này)" % (
                    fid, sid, t["formula"])
            assert not t["target_tag"].startswith("thong_tin_dang_ky"), \
                "%s/%s: cột text không có tổng" % (fid, sid)


@check("[SPEC] pham vi lane: dung tap section moi mau (khong roi rong)")
def t_scope_exact():
    want = {
        "PLI_M03": {"ds_nganh", "nguon_von_dieule"},
        "PLI_M04": {"ds_nganh", "nguon_von_dieule", "co_cau_loai_co_phan",
                    "co_phan_duoc_quyen_chao_ban"},
        "PLI_M05": {"ds_nganh", "nguon_von_dieule"},
        # PLI_M12: 3 lưới ngành (2A/2B) + nested-grid người (R3B1) + nguồn vốn
        "PLI_M12": {"nganh_bo_sung", "nganh_xoa_bo", "nganh_sua_doi_chi_tiet",
                    "ndd_uy_quyen_sau_thay_doi",
                    "nguon_von_dieule_sau_thay_doi"},
        "PLII_M02": {"ds_nganh_bo_sung", "ds_nganh_xoa_bo",
                     "ds_nganh_sua_chi_tiet", "ds_nganh",
                     "a7_thue_chi_tieu_cu_moi"},
    }
    for fid, want_ids in want.items():
        raw = raw_spec(fid)
        got = {e["spec"]["id"] for e in raw["tables"]}
        assert got == want_ids, "%s: tập entry %r != %r" % (fid, sorted(got),
                                                            sorted(want_ids))
    # R3B1: PLI_M12 vẫn giữ nguyên lưới người đại diện theo ủy quyền
    ext = entries_of("PLI_M12")
    nested = [ext["specs_by_id"][e["spec"]] for e in ext["entries"]
              if ext["specs_by_id"][e["spec"]]["kind"] == "nested-grid"]
    assert len(nested) == 1 and nested[0]["loop"] == "ds_ndd_uy_quyen_sau_thay_doi", \
        "PLI_M12: mất/đổi entry nested-grid của lane R3B1"


# ---------------------------------------------------------------------------
# [EVD] census manifest
# ---------------------------------------------------------------------------
@check("[EVD] census manifest co evidence cho 7 section moi khai")
def t_evidence_manifest():
    forms = manifest_sections()
    for (fid, sid), want in FORMS.items():
        sec = forms[fid].get(sid)
        assert sec is not None, "%s: thiếu section %r trong manifest" % (fid, sid)
        assert sec["kind"] == "fixed-matrix", "%s/%s kind=%r" % (fid, sid,
                                                                 sec["kind"])
        assert sec["semantic_key"] == want["semantic_key"], \
            "%s/%s semantic_key=%r != %r" % (fid, sid, sec["semantic_key"],
                                             want["semantic_key"])
        ev = sec.get("source_evidence") or {}
        assert (ev.get("heading") or ev.get("anchor")), \
            "%s/%s thiếu evidence nguồn" % (fid, sid)
        # cột/row khai trong spec phải bọc được bằng required_columns của census
        req = set(sec.get("required_columns") or [])
        tags = {c for c in want["columns"] if c}
        for col_tag in tags:
            assert any(col_tag in r or r in col_tag or
                       col_tag.endswith(r) or r.endswith(col_tag)
                       for r in req), \
                "%s/%s: tag %r không khớp required_columns %r" % (
                    fid, sid, col_tag, sorted(req))


# ---------------------------------------------------------------------------
# [NGUỒN] văn bản hiện hành
# ---------------------------------------------------------------------------
@check("[NGUON] legal_status.ref tro TT 121/2026 (hien hanh) dung so mau/muc")
def t_law_source_current():
    for (fid, sid), want in FORMS.items():
        ls = (entry_for(fid, sid))[0].get("legal_status") or {}
        ref = "%s %s" % (ls.get("ref") or "", ls.get("question") or "")
        for token in want["law_ref"]:
            assert fold(token) in fold(ref), \
                "%s/%s: legal_status thiếu nguồn %r" % (fid, sid, token)
        if want["pl"] == "I":
            assert "121/2026" in (ls.get("ref") or ""), \
                "%s/%s: phải trỏ văn bản hiện hành TT 121/2026/TT-BTC" % (fid, sid)
        else:
            # Phụ lục II không bị TT 121 đụng tới -> phải ghi rõ điều đó
            assert "khong dung phu luc ii" in fold(ref), \
                "%s/%s: phải ghi rõ TT 121 không đụng Phụ lục II" % (fid, sid)


@check("[NGUON] drop_until='(?!)' la regex khong bao gio khop (muc cuoi nguon)")
def t_never_match_sentinel():
    for (fid, sid), want in FORMS.items():
        e, spec = entry_for(fid, sid)
        if e.get("drop_until") != "(?!":
            pass
        du = e.get("drop_until")
        if du != "(?!)":
            continue
        assert re.search(du, "") is None and re.search(du, "x") is None, \
            "%s/%s: sentinel phải không khớp gì" % (fid, sid)
        # ... và section đó phải là mục CUỐI của nguồn (không còn heading sau)
        src = bfm.find_source(fid)
        doc = docx.Document(str(src))
        folds = [fold(p.text) for p in doc.paragraphs]
        start = next(i for i, t in enumerate(folds)
                     if re.search(e["anchor"], t))
        assert not any(re.search(e["anchor"], t) for t in folds[start + 1:]), \
            "%s/%s: anchor lặp lại sau sentinel" % (fid, sid)


# ---------------------------------------------------------------------------
# [ANCHOR]/[DROP]
# ---------------------------------------------------------------------------
@check("[ANCHOR] anchor dung DUY NHAT 1 paragraph trong blocks hien tai + nguon")
def t_anchor_unique():
    for (fid, sid), want in FORMS.items():
        e, spec = entry_for(fid, sid)
        folds_b = block_folds(fid)
        hits_b = [i for i, t in enumerate(folds_b)
                  if re.search(e["anchor"], t)]
        assert len(hits_b) == 1, \
            "%s/%s: anchor khớp blocks %r (cần đúng 1)" % (fid, sid, hits_b)
        assert folds_b[hits_b[0]].startswith(want["anchor_fold"]), \
            "%s/%s: anchor trúng %r thay vì %r" % (
                fid, sid, folds_b[hits_b[0]][:60], want["anchor_fold"])
        src = bfm.find_source(fid)
        doc = docx.Document(str(src))
        folds_t = [fold(p.text) for p in doc.paragraphs]
        hits_t = [i for i, t in enumerate(folds_t)
                  if re.search(e["anchor"], t)]
        assert len(hits_t) == 1, \
            "%s/%s: anchor khớp nguồn %d lần" % (fid, sid, len(hits_t))


@check("[DROP] drop chi trong [anchor, drop_until) va khong nuot muc ke")
def t_drop_scoped_and_boundary():
    for (fid, sid), want in FORMS.items():
        e, spec = entry_for(fid, sid)
        src = bfm.find_source(fid)
        doc = docx.Document(str(src))
        raws = [p.text for p in doc.paragraphs]
        folds = [fold(t) for t in raws]
        start = next(i for i, t in enumerate(folds)
                     if re.search(e["anchor"], t)) + 1
        hits = [i for i in range(start, len(folds))
                if re.search(e["drop_until"], folds[i])]
        end = hits[0] if hits else len(folds)
        # mốc kế không bị drop pattern chạm tới
        if hits:
            assert not any(re.match(p, folds[end]) for p in e["drop"]), \
                "%s/%s: drop nuốt heading mục kế %r" % (fid, sid, raws[end][:60])
        # mọi paragraph CÓ TEXT trong vùng phải là glue của chính mục này
        kept = [fold(k) for k in want["kept"]]
        missed = [raws[i] for i in range(start, end)
                  if folds[i] and not any(re.match(p, folds[i])
                                          for p in e["drop"])
                  and not any(folds[i].startswith(k) for k in kept)]
        assert not missed, "%s/%s: drop bỏ sót glue %r" % (fid, sid, missed[:3])
        # ô trống là khoảng trình bày của mẫu — không được nuốt
        assert any(not folds[i] for i in range(start, end)), \
            "%s/%s: vùng không có ô trống như evidence" % (fid, sid)


@check("[DROP] chuoi phap ly din kem (menh gia co phan M04) duoc GIU nguyen")
def t_kept_inputs_preserved():
    ext = entries_of("PLI_M04")
    e, spec = entry_for("PLI_M04", "co_cau_loai_co_phan")
    fm_fields = json.loads((ROOT / "app" / "data" / "form_maps.json")
                           .read_text(encoding="utf-8"))["PLI_M04"]["fields"]
    keys = {f["key"] for f in fm_fields}
    assert "menh_gia_co_phan" in keys, \
        "M04: {menh_gia_co_phan} phải còn đăng ký trong form_maps"
    assert not any(re.match(p, "menh gia co phan (vnd):") for p in e["drop"]), \
        "M04: drop pattern không được nuốt dòng mệnh giá cổ phần"


# ---------------------------------------------------------------------------
# [SANDBOX] rebuild thật + kiểm định converter
# ---------------------------------------------------------------------------
def new_sandbox() -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="cap_von_sandbox_"))
    tpl_dir = tmp / "templates"
    data_dir = tmp / "data"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return tpl_dir, data_dir


def run_generation(fid: str, want: dict, tpl_dir: Path) -> dict:
    bfm._form_spec_cache.clear()
    src = bfm.find_source(fid)
    meta, _unmatched = bfm.process_form(
        src, {"Phu luc %s|%d" % (want["pl"], want["mau"]): "DEMO %s" % fid},
        None)
    assert (tpl_dir / ("%s.docx" % fid)).exists(), \
        "%s: generator chưa ghi template" % fid
    return meta


def fixed_matrix_tokens(blocks: dict, sem: str) -> list[str]:
    toks: list[str] = []
    for b in blocks["blocks"]:
        if b.get("t") != "table":
            continue
        for row in b.get("rows") or []:
            for cell in row.get("cells") or []:
                for r in cell.get("runs") or []:
                    key = ((r.get("input") or {}).get("key"))
                    if key:
                        toks.append(str(key))
    return [t for t in toks if t.startswith(sem + ".")]


@check("[SANDBOX] rebuild 5 mau: dung shape w:tbl + glue bien mat + token du")
def t_sandbox_rebuild():
    guards = {p.name: sha256_file(p)
              for p in sorted((ROOT / "app" / "templates").glob("*.docx"))}
    tpl_dir, _data = new_sandbox()
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, _data
    bfm._form_spec_cache.clear()
    try:
        seen = {}
        for (fid, sid), want in FORMS.items():
            if (fid, sid) in seen:
                continue
            meta = run_generation(fid, want, tpl_dir)
            seen[fid] = meta
            doc = docx.Document(str(tpl_dir / ("%s.docx" % fid)))
            shapes = [(len(t.rows), len(t.columns)) for t in doc.tables]
            assert want["table_shape"] in shapes, \
                "%s: không thấy w:tbl %s, có %r" % (fid, want["table_shape"],
                                                    shapes)
            sp = [s for s in (meta.get("section_specs") or [])
                  if s.get("section_id") == sid]
            assert len(sp) == 1, "%s: form_maps thiếu section_spec %r" % (fid, sid)
            assert sp[0]["kind"] == "fixed-matrix" and \
                sp[0]["semantic_key"] == want["semantic_key"]
            assert [r["id"] for r in sp[0]["fixed_rows"]] == want["rows"]
        # idempotent: chạy lần 2 cho cùng template (hash SEMANTIC của
        # word/document.xml — python-docx ghi zip timestamp mỗi lần lưu)
        for fid, meta in seen.items():
            want = next(w for (f, _s), w in FORMS.items() if f == fid)
            tpl = tpl_dir / ("%s.docx" % fid)
            h1 = template_hash(tpl)
            run_generation(fid, want, tpl_dir)
            assert template_hash(tpl) == h1, \
                "%s: rebuild 2 lần lệch nhau" % fid
        # template gốc trong repo KHÔNG bị chạm
        for name, before in guards.items():
            assert sha256_file(ROOT / "app" / "templates" / name) == before, \
                "%s bị ghi ngoài sandbox!" % name
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()
        shutil.rmtree(tpl_dir.parent, ignore_errors=True)


@check("[SANDBOX] convert + kiem dinh: du the tung o, dong tong khong lam field")
def t_sandbox_convert_tokens():
    tpl_dir, _data = new_sandbox()
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, _data
    bfm._form_spec_cache.clear()
    try:
        for fid in dict.fromkeys(f for f, _s in FORMS):
            want = next(w for (f, _s), w in FORMS.items() if f == fid)
            meta = run_generation(fid, want, tpl_dir)
            tpl = tpl_dir / ("%s.docx" % fid)
            blocks = dxtb.convert_document(docx.Document(str(tpl)), fid,
                                           "DEMO %s" % fid, overrides={},
                                           footnotes={},
                                           section_specs=meta["section_specs"])
            fields = {f["key"] for f in meta["fields"]}
            for (f, sid), w in FORMS.items():
                if f != fid:
                    continue
                toks = fixed_matrix_tokens(blocks, w["semantic_key"])
                editable = [r for r in w["rows"] if r != w["total_row"]]
                for r in editable:
                    for tag in (c for c in w["columns"] if c):
                        key = "%s.%s.%s" % (w["semantic_key"], r, tag)
                        assert key in toks, "%s/%s: thiếu the %s" % (fid, sid, key)
                        assert key in fields, \
                            "%s/%s: %s chưa đăng ký form_maps.fields" % (fid, sid, key)
                if w["total_row"]:
                    total_keys = ["%s.%s.%s" % (w["semantic_key"],
                                                w["total_row"], tag)
                                  for tag in (c for c in w["columns"] if c)]
                    assert all(k in toks for k in total_keys), \
                        "%s/%s: ô tổng phải vẫn có the" % (fid, sid)
                    assert not [k for k in fields
                                if k.startswith("%s.%s." % (w["semantic_key"],
                                                            w["total_row"]))], \
                        "%s/%s: dòng tổng bị đăng ký field (vi phạm outputOnly)" % (
                            fid, sid)
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()
        shutil.rmtree(tpl_dir.parent, ignore_errors=True)


@check("[SANDBOX] glue bien mat trong template moi (chi xet vung section)")
def t_sandbox_glue_gone():
    GLUE = {
        "nguon_von_dieule": ["loai nguon von", "von ngan sach nha nuoc",
                             "von tu nhan", "von nuoc ngoai", "von khac",
                             "tong cong", "ty le (%)"],
        "co_cau_loai_co_phan": ["loai co phan", "so luong", "gia tri (bang so",
                                "ti le so voi von dieu le", "co phan pho thong",
                                "cp_uu_dai", "co phan uu dai"],
        "co_phan_duoc_quyen_chao_ban": ["loai co phan duoc quyen chao ban",
                                        "co phan uu dai", "tong so"],
        "nguon_von_dieule_sau_thay_doi": ["loai nguon von",
                                          "von ngan sach nha nuoc", "tong cong"],
        "a7_thue_chi_tieu_cu_moi": ["thong tin dang ky cu",
                                    "thong tin dang ky moi",
                                    "chi tieu 5.1: dia chi nhan thong bao thue"],
    }
    tpl_dir, _data = new_sandbox()
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, _data
    bfm._form_spec_cache.clear()
    try:
        for fid in dict.fromkeys(f for f, _s in FORMS):
            want = next(w for (f, _s), w in FORMS.items() if f == fid)
            meta = run_generation(fid, want, tpl_dir)
            doc = docx.Document(str(tpl_dir / ("%s.docx" % fid)))
            texts = [p.text for p in body_paragraphs(doc) if isinstance(p, Paragraph)]
            folds = [fold(t) for t in texts]
            for (f, sid) in FORMS:
                if f != fid:
                    continue
                e, _spec = entry_for(fid, sid)
                start = next(i for i, t in enumerate(folds)
                             if re.search(e["anchor"], t)) + 1
                hits = [i for i in range(start, len(folds))
                        if re.search(e["drop_until"], folds[i])]
                end = hits[0] if hits else len(folds)
                region = folds[start:end]
                for glue in GLUE[sid]:
                    if glue == "tong so" and \
                            sid == "co_phan_duoc_quyen_chao_ban":
                        pass
                    left = [t for t in region if t.startswith(glue)]
                    assert not left, "%s/%s: glue còn sót %r (mẫu %r)" % (
                        fid, glue, left[:2], sid)
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()
        shutil.rmtree(tpl_dir.parent, ignore_errors=True)


@check("[D1.1] recompute_totals: tong tinh lai tu o du lieu, conflict blocking")
def t_export_recompute():
    tpl_dir, _data = new_sandbox()
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, _data
    bfm._form_spec_cache.clear()
    try:
        want = FORMS[("PLI_M03", "nguon_von_dieule")]
        meta = run_generation("PLI_M03", want, tpl_dir)
        specs = [s for s in meta["section_specs"]
                 if s["section_id"] == "nguon_von_dieule"]
        assert len(specs) == 1
        sem = want["semantic_key"]
        flat = {
            "%s.von_ngan_sach_nha_nuoc.so_tien_vnd_va_tuong_duong" % sem: "2000000000",
            "%s.von_ngan_sach_nha_nuoc.ty_le" % sem: "20",
            "%s.von_tu_nhan.so_tien_vnd_va_tuong_duong" % sem: "8000000000",
            "%s.von_tu_nhan.ty_le" % sem: "80",
            # stored SAI chủ đích: engine phải tính lại, không tin draft
            "%s.tong_cong.so_tien_vnd_va_tuong_duong" % sem: "1",
            "%s.tong_cong.ty_le" % sem: "7",
        }
        report = {r["target"]: r for r in
                  recompute_totals(nest(flat), specs, strict=False)}
        money = report["%s.tong_cong.so_tien_vnd_va_tuong_duong" % sem]
        pct = report["%s.tong_cong.ty_le" % sem]
        assert money["computed"] == "10000000000", \
            "M03: tổng nguồn vốn %r != 10000000000" % money["computed"]
        assert pct["computed"] == "100", \
            "M03: tổng tỷ lệ %r != 100" % pct["computed"]
        assert money["had_input"] is True
        # strict=True + stored != computed -> EXPORT_TOTALS_RECOMPUTE_CONFLICT
        try:
            recompute_totals(nest(flat), specs, strict=True)
        except ExportTotalsError as exc:
            codes = {p.get("code") for p in exc.problems}
            assert codes == {"EXPORT_TOTALS_RECOMPUTE_CONFLICT"}, codes
        else:  # pragma: no cover
            raise AssertionError("M03: stored sai mà không raise conflict")
        # cột text (PLII_M02 cũ/mới) không được tính tổng
        w2 = FORMS[("PLII_M02", "a7_thue_chi_tieu_cu_moi")]
        assert w2["totals"] == set()
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()
        shutil.rmtree(tpl_dir.parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# [D5.2] PLII_M02
# ---------------------------------------------------------------------------
@check("[D5.2] PLII_M02: bang cu/moi dung 3 chi tieu II.2 + phan C khong bi dong")
def t_plii_m02_tax():
    e, spec = entry_for("PLII_M02", "a7_thue_chi_tieu_cu_moi")
    labels = [r["label"] for r in spec["fixed_rows"]]
    # từng dòng phải trúng một dòng thật của mẫu II.2
    assert fold(labels[0]) == fold("- Chỉ tiêu 5.1: Địa chỉ nhận thông báo thuế")
    assert fold(labels[1]).startswith("- chi tieu 5.2") and \
        "tong so lao dong" in fold(labels[1])
    assert re.fullmatch(r"-[.…]+", labels[2]), \
        "dòng tiếp diễn phải giữ nguyên văn '-….' của mẫu, thấy %r" % labels[2]
    assert spec["totals"] == [], "bảng cũ/mới không có cột số -> không totals"
    # các chỉ tiêu 5.1/5.2 phải là CHỈ TIÊU thật của mục 5 phần C cùng mẫu
    src = bfm.find_source("PLII_M02")
    doc = docx.Document(str(src))
    folds = [fold(p.text) for p in doc.paragraphs]
    head = folds.index("5. thong tin dang ky thue:")
    window = folds[head:head + 14]
    assert any(t == "5.1" for t in window) and \
        any(t.startswith("dia chi nhan thong bao thue") for t in window), \
        "mẫu II.2 mất chỉ tiêu 5.1"
    assert any(t == "5.2" for t in window) and \
        any(t.startswith("tong so lao dong") for t in window), \
        "mẫu II.2 mất chỉ tiêu 5.2"
    assert not any("giam doc" in t for t in window), \
        "mẫu II.2 (hộ kinh doanh) không được có chỉ tiêu Giám đốc/TGĐ"
    # phần C mục 5 KHÔNG được rebuild: 7 ô đã map sẵn (nguy cơ 2 nguồn sự thật)
    blocks = json.loads((BLOCKS_DIR / "PLII_M02.json").read_text(
        encoding="utf-8"))["blocks"]
    tax_inputs = {"dia_chi_chi_tiet", "xa_phuong", "tinh_thanh",
                  "dien_thoai_lien_he", "fax", "email_tru_so", "so_lao_dong"}
    found = set()
    for b in blocks:
        for r in (b.get("runs") or []):
            k = (r.get("input") or {}).get("key")
            if k in tax_inputs:
                found.add(k)
    assert found == tax_inputs, \
        "7 ô thuế phần C mục 5 phải còn nguyên (thiếu %r)" % (tax_inputs - found)
    ext = entries_of("PLII_M02")
    assert not [e for e in ext["entries"]
                if ext["specs_by_id"][e["spec"]].get("section_id")
                in ("c5_thue_chi_tieu_cap_doi",)], \
        "PLII_M02: không được rebuild phần C mục 5 khi 7 ô đã map sẵn (W1 gap)"


@check("[D5.2] PLII_M02: 4 loop nganh + pin occurrence giu nguyen")
def t_plii_m02_industry_untouched():
    raw = raw_spec("PLII_M02")
    ids = []
    for e in raw["tables"]:
        for o in (e.get("occurrences") or []):
            ids.append(o["occurrence_id"])
    assert sorted(ids) == sorted(["nganh_bo_sung", "nganh_xoa_bo",
                                  "nganh_sua_doi_chi_tiet",
                                  "nganh_hien_tai"]), \
        "4 occurrence ngành của PLII_M02 bị đổi: %r" % ids


# ---------------------------------------------------------------------------
# [GUARD] không đụng artifact production
# ---------------------------------------------------------------------------
@check("[GUARD] suite khong ghi app/templates / app/data")
def t_guard_production_untouched():
    tpl = ROOT / "app" / "templates" / "PLI_M03.docx"
    before = sha256_file(tpl)
    fm = ROOT / "app" / "data" / "form_maps.json"
    before_fm = sha256_file(fm)
    tpl_dir, _data = new_sandbox()
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, _data
    bfm._form_spec_cache.clear()
    try:
        run_generation("PLI_M03", FORMS[("PLI_M03", "nguon_von_dieule")],
                       tpl_dir)
        assert sha256_file(tpl) == before, "template bị ghi ngoài sandbox!"
        assert sha256_file(fm) == before_fm, "form_maps bị ghi ngoài sandbox!"
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm._form_spec_cache.clear()
        shutil.rmtree(tpl_dir.parent, ignore_errors=True)


def main() -> int:
    for fn in (t_spec_validate, t_scope_exact, t_evidence_manifest,
               t_law_source_current, t_never_match_sentinel, t_anchor_unique,
               t_drop_scoped_and_boundary, t_kept_inputs_preserved,
               t_sandbox_rebuild, t_sandbox_convert_tokens,
               t_sandbox_glue_gone, t_export_recompute, t_plii_m02_tax,
               t_plii_m02_industry_untouched, t_guard_production_untouched):
        fn()
    ok = sum(1 for p, _ in RESULTS if p)
    fail = sum(1 for p, _ in RESULTS if not p)
    print("-" * 72)
    print("test_cap_von_specs: %d PASS / %d FAIL" % (ok, fail))
    for passed, name in RESULTS:
        if not passed:
            print("  -> %s" % name)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
