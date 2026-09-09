#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_wave2_docx_pins.py — regression pins lỗi lớp A (lane wave2-docx).

Pin trên ARTIFACT đã commit (app/data/blocks + app/data/form_maps — sinh bởi
pipeline 4 bước: build_form_maps -> tag_m72_sections -> docx_to_blocks x2),
không chạy lại generator: test đọc nhanh, fail khi artifact trôi khỏi hợp
đồng đã adjudicate. 4 nhóm:

  C1  "Ngày cấp: … Nơi cấp: …" bind nhầm — mọi block "p" của các form chịu
      ảnh hưởng chứa cả 2 nhãn phải có ĐỦ 2 input, key *ngay_cap đứng
      TRƯỚC *noi_cap. Root cause: slot '…' 1 ký tự sau "Ngày cấp:" vô hình
      với DOT_RUN ([.…]{2,}) trong tools/build_form_maps.py ->
      _assign_para_slots; fix 2026-09-09 (nhánh composite label).
      Form chịu ảnh hưởng: PLI_M42, PLI_M43, PLI_M63, PLI_M68, PLI_M69,
      PLI_M72 (x5 render-unit) — cùng 1 pattern nguồn
      '…): …… Ngày cấp: … Nơi cấp: ……'.
  C2  PLI_M67 block "(tên doanh nghiệp) …" bind dn.ten_tieng_viet (đối chiếu
      form anh em PLI_M66); {co_quan_dkkd} không còn đè lên ô tên (nguồn
      M67 không có nhãn ĐKKD fill nào khác — không có dòng "Kính gửi").
  C3  PLI_M12 in dòng "Mẫu số 12" đậm căn phải TRƯỚC band (TT 121/2026
      phụ lục I tr.50 — ảnh /tmp/legal_p0_pages/M12_p50.png; premise cũ
      "giấy đề nghị không có dòng Mẫu số" adjudicate SAI 2026-09-09).
  C4  nhãn "Mẫu số N" của 23 form band (HEADER_BAND_FORMS) in đậm căn phải
      (TT 121/2026 p50/p67/p70 + TT 68 p78/83/111/130/224/239; 7 mẫu nguồn
      đã đúng: M13/14/15/18/19/21/26; 15 mẫu chuẩn hoá: còn lại; M12 chèn).

Chạy:  python3 -X utf8 -m tools.test_wave2_docx_pins   (từ root worktree)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"

# Các form có pattern nguồn '…): …… Ngày cấp: … Nơi cấp: ……' — C1
C1_FORMS = ["PLI_M42", "PLI_M43", "PLI_M63", "PLI_M68", "PLI_M69", "PLI_M72"]

_results = []


def check(name):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def load_blocks(fid):
    return json.loads((BLOCKS_DIR / ("%s.json" % fid)).read_text(
        encoding="utf-8"))["blocks"]


def para_text(block):
    return "".join(r.get("text", "") for r in block.get("runs", []))


def para_inputs(block):
    return [(i, r["input"]["key"])
            for i, r in enumerate(block.get("runs", [])) if "input" in r]


def run_char_start(block, run_idx):
    """Vị trí ký tự BẮT ĐẦU của run `run_idx` trong text gộp của block."""
    return sum(len(r.get("text", ""))
               for r in block.get("runs", [])[:run_idx])


# ---------------------------------------------------------------------------
# C1
# ---------------------------------------------------------------------------

@check("[C1] block p co ca 2 nhãn Ngày cấp/Nơi cấp -> ĐỦ cặp *ngay_cap TRƯỚC *noi_cap")
def t_c1_pair_inputs():
    problems = []
    for fid in C1_FORMS:
        for bi, blk in enumerate(load_blocks(fid)):
            if blk.get("t") != "p":
                continue
            txt = para_text(blk)
            if "Ngày cấp" not in txt or "Nơi cấp" not in txt:
                continue
            # Paragraph còn chứa slot đứng TRƯỚC (số định danh/số hộ chiếu)
            # nên hợp đồng đúng: ĐÚNG 1 cặp *ngay_cap -> *noi_cap, cặp này
            # đứng sau mọi input khác ("Nơi cấp:" là ô cuối dòng).
            pair = [(i, k) for i, k in para_inputs(blk)
                    if k.endswith("ngay_cap") or k.endswith("noi_cap")]
            if len(pair) != 2:
                problems.append("%s blk%d: %d key ngay/noi (mong 2): %r"
                                % (fid, bi, len(pair), para_inputs(blk)))
                continue
            (i1, k1), (i2, k2) = pair
            if not (k1.endswith("ngay_cap") and k2.endswith("noi_cap")
                    and i1 < i2):
                problems.append("%s blk%d: sai cặp/thứ tự %r -> %r"
                                % (fid, bi, k1, k2))
                continue
            if k1.replace("ngay_cap", "") != k2.replace("noi_cap", ""):
                problems.append("%s blk%d: prefix lệch %r vs %r"
                                % (fid, bi, k1, k2))
                continue
            others = [(i, k) for i, k in para_inputs(blk)
                      if not (k.endswith("ngay_cap") or k.endswith("noi_cap"))]
            if any(i > i1 for i, _ in others):
                problems.append("%s blk%d: còn input khác sau cặp ngày/nơi: %r"
                                % (fid, bi, others))
    assert not problems, "%d block lệch:\n  " % len(problems) \
        + "\n  ".join(problems)


@check("[C1] toàn corpus: không block p nào gắn *ngay_cap SAU chữ 'Nơi cấp'")
def t_c1_global_no_ngay_after_noi():
    # Bất biến hướng: nếu một input *ngay_cap đứng sau run text chứa
    # "Nơi cấp" thì đúng là lỗi C1 tái phát (ô ngày rơi vào chỗ nơi cấp).
    bad = []
    for jf in sorted(BLOCKS_DIR.glob("*.json")):
        for bi, blk in enumerate(json.loads(
                jf.read_text(encoding="utf-8")).get("blocks", [])):
            if blk.get("t") != "p":
                continue
            seen_noi = False
            for r in blk.get("runs", []):
                if "text" in r and "Nơi cấp" in r.get("text", ""):
                    seen_noi = True
                if "input" in r and r["input"]["key"].endswith("ngay_cap") \
                        and seen_noi:
                    bad.append("%s blk%d: {%s} sau 'Nơi cấp'"
                               % (jf.stem, bi, r["input"]["key"]))
    assert not bad, bad


# ---------------------------------------------------------------------------
# C2
# ---------------------------------------------------------------------------

@check("[C2] PLI_M67 slot sau '(tên doanh nghiệp)' = {dn.ten_tieng_viet}")
def t_c2_m67_name_slot():
    blocks = load_blocks("PLI_M67")
    hits = []
    for bi, blk in enumerate(blocks):
        if blk.get("t") != "p":
            continue
        txt = para_text(blk)
        if "(tên doanh nghiệp)" not in txt:
            continue
        hits.append((bi, blk))
        inputs = para_inputs(blk)
        assert inputs, "PLI_M67 blk%d: ô tên doanh nghiệp không có input" % bi
        # input NGAY SAU vị trí "(tên doanh nghiệp)" trong dòng ký tự gộp
        # (nhãn có thể tách qua nhiều run in nghiêng — so trên text gộp)
        pos = txt.index("(tên doanh nghiệp)") + len("(tên doanh nghiệp)")
        after = [(i, k) for i, k in inputs
                 if run_char_start(blk, i) >= pos]
        assert after and after[0][1] == "dn.ten_tieng_viet", (
            "PLI_M67 blk%d: input sau '(tên doanh nghiệp)' = %r (mong "
            "dn.ten_tieng_viet)" % (bi, after[:1]))
        assert all(k != "co_quan_dkkd" for _, k in inputs), (
            "PLI_M67 blk%d: {co_quan_dkkd} vẫn đè câu thông báo" % bi)
    assert hits, "PLI_M67: không tìm thấy block '(tên doanh nghiệp)'"


@check("[C2] form_maps PLI_M67 có dn.ten_tieng_viet, không còn co_quan_dkkd")
def t_c2_m67_fields():
    fields = json.loads(FORM_MAPS.read_text(encoding="utf-8"))["PLI_M67"]["fields"]
    keys = [f["key"] for f in fields]
    assert "dn.ten_tieng_viet" in keys, \
        "PLI_M67 thiếu field dn.ten_tieng_viet: %s" % keys
    assert "co_quan_dkkd" not in keys, \
        "PLI_M67 còn field co_quan_dkkd (nhãn ĐKKD fill không tồn tại ở mẫu này)"


# ---------------------------------------------------------------------------
# C3 + C4
# ---------------------------------------------------------------------------

BAND_FORMS = [
    "PLI_M12", "PLI_M13", "PLI_M14", "PLI_M15", "PLI_M17", "PLI_M18",
    "PLI_M19", "PLI_M21", "PLI_M23", "PLI_M25", "PLI_M26", "PLI_M27",
    "PLI_M28", "PLI_M29", "PLI_M30", "PLI_M31", "PLI_M32", "PLI_M33",
    "PLII_M02", "PLII_M03", "PLII_M04", "PLII_M05", "PLII_M06",
]


def _form_number_block(fid):
    """Block role='form-number' đầu tiên (dòng 'Mẫu số N') hoặc None."""
    for bi, blk in enumerate(load_blocks(fid)[:8]):
        if blk.get("role") == "form-number" and blk.get("t") == "p":
            return bi, blk
    return None, None


@check("[C3] PLI_M12 có dòng 'Mẫu số 12' đậm căn phải TRƯỚC band header")
def t_c3_m12_mauso_before_band():
    blocks = load_blocks("PLI_M12")
    band_idx = next((i for i, b in enumerate(blocks)
                     if b.get("t") == "table" and b.get("band") == "header"),
                    None)
    assert band_idx is not None, "PLI_M12: không thấy block band header"
    assert band_idx >= 1, "PLI_M12: band đứng đầu, thiếu dòng 'Mẫu số 12'"
    pre = blocks[band_idx - 1]
    assert pre.get("t") == "p" and pre.get("role") == "form-number", \
        "PLI_M12: block ngay trước band không phải 'Mẫu số N': %r" % pre
    assert para_text(pre).strip() == "Mẫu số 12", \
        "PLI_M12: dòng trước band = %r" % para_text(pre)
    assert pre.get("align") == "right", \
        "PLI_M12: 'Mẫu số 12' chưa căn phải: %r" % pre.get("align")
    runs = [r for r in pre.get("runs", []) if r.get("text", "").strip()]
    assert runs and all(r.get("b") for r in runs), \
        "PLI_M12: 'Mẫu số 12' chưa in đậm: %r" % runs


@check("[C4] 23 form band: nhãn 'Mẫu số N' đều căn phải + in đậm")
def t_c4_mauso_right_bold():
    problems = []
    for fid in BAND_FORMS:
        bi, blk = _form_number_block(fid)
        if blk is None:
            problems.append("%s: thiếu block role=form-number" % fid)
            continue
        txt = para_text(blk).strip()
        if not re.match(r"^Mẫu\s*số\s*\d{1,4}$", txt):
            problems.append("%s: form-number = %r" % (fid, txt))
        if blk.get("align") != "right":
            problems.append("%s: align=%r (mong right)" % (fid, blk.get("align")))
        runs = [r for r in blk.get("runs", []) if r.get("text", "").strip()]
        if not runs or not all(r.get("b") for r in runs):
            problems.append("%s: runs chưa đậm: %r" % (fid, runs))
    assert not problems, "%d form lệch:\n  " % len(problems) \
        + "\n  ".join(problems)


def main() -> int:
    for _name, fn in sorted(globals().items()):
        if _name.startswith("t_") and callable(fn):
            fn()
    fails = [m for ok, m in _results if not ok]
    print("-" * 72)
    print("WAVE2-DOCX PINS: %d PASS / %d FAIL" % (
        sum(1 for ok, _ in _results if ok), len(fails)))
    for m in fails:
        print(" - FAIL %s" % m)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
