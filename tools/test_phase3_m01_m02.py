#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_phase3_m01_m02.py — Domain evidence tests cho phase3 lane B (p1+p2).

Chứng minh bằng evidence tầng domain (ĐỌC-ONLY, KHÔNG sửa data, KHÔNG dùng
status override) 2 nhóm audit Lane A đã chốt:

  1. PLI_M01 / bhxh_phuong_thuc_dong — census manifest stale (status
     'partial', notes than thiếu chk_bc_03_thang) nhưng blocks thực tế đã
     đủ 3 token chk_bc_hang_thang / chk_bc_03_thang / chk_bc_06_thang
     trong vùng anchor '7. Thông tin về việc đóng bảo hiểm xã hội6:'
     (fix commit ba64f29). Tiền lệ PLI_M17/phuong_thuc_dong_bhxh: nhóm chk
     cùng kiến trúc đã được credit IMPLEMENTED_VERIFIED qua đường chung.

  2. tai_san_gop_von_von_dau_tu (PLI_M01) + tai_san_gop_von_von_dieu_le
     (PLI_M02) — fixed-matrix mà STT là số thứ tự IN SẴN của dòng pháp
     định (KHÔNG phải input): spec khai fixed_rows 7 dòng (6 tài sản +
     tong_so output_only=true) + drop list chứa ^stt$ và ^\\d$; blocks
     không có input key 'stt'/'.stt' trong vùng anchor; runtime contract
     app_web/ui/form-domain.js khai `stt: { mode: 'none' }` + fixed_rows
     6 phần tử label (không đếm tong) cho cả 2 section.

Vùng anchor tính GIỐNG build_layout_index (tools/census/table_coverage_audit.py):
từ block khớp needle heading census của section tới block khớp anchor census
kế tiếp theo thứ tự vị trí (section cuối -> hết blocks phẳng).

Chạy:  python3 -X utf8 tools/test_phase3_m01_m02.py
Exit 0 = toàn PASS; exit 1 = có FAIL (báo blocker, KHÔNG tự sửa source).
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.census.table_coverage_audit import (  # noqa: E402
    anchor_pos_in,
    block_all_text,
    flatten_blocks,
    region_keys_scan,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(REPO, "app", "data", "table_specs", "manifest.json")
BLOCKS_DIR = os.path.join(REPO, "app", "data", "blocks")
FORM_DOMAIN_JS = os.path.join(REPO, "app_web", "ui", "form-domain.js")
SPEC_M01 = os.path.join(REPO, "tools", "form_specs", "formation",
                        "PLI_M01.json")
SPEC_M02 = os.path.join(REPO, "tools", "form_specs", "core", "PLI_M02.json")

BHXH_HEADING = "7. Thông tin về việc đóng bảo hiểm xã hội6:"
BHXH_TOKENS = ("chk_bc_hang_thang", "chk_bc_03_thang", "chk_bc_06_thang")

# (form_id, section_id, spec file path)
TAI_SAN_SECTIONS = (
    ("PLI_M01", "tai_san_gop_von_von_dau_tu", SPEC_M01),
    ("PLI_M02", "tai_san_gop_von_von_dieu_le", SPEC_M02),
)

RESULTS = []


def check(name, cond, detail=""):
    """Ghi + in 1 check PASS/FAIL kèm evidence ngắn (cả khi PASS)."""
    ok = bool(cond)
    RESULTS.append((name, ok, detail))
    print(("PASS  " if ok else "FAIL  ") + name +
          (("  | " + detail) if detail else ""))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_regions(fid):
    """Vùng anchor theo VỊ TRÍ của mọi section manifest của 1 form —
    cùng thuật toán build_layout_index: anchor_pos_in trên blocks phẳng,
    region = [anchor section, anchor census kế tiếp theo thứ tự vị trí),
    section cuối cùng -> hết blocks."""
    manifest = load_json(MANIFEST_PATH)
    form = next(f for f in manifest["forms"] if f["form_id"] == fid)
    doc = load_json(os.path.join(BLOCKS_DIR, "%s.json" % fid))
    flat = flatten_blocks(doc)
    flat_texts = [block_all_text(b) for b in flat]
    fpos = {}
    for s in form["sections"]:
        heading = (s.get("source_evidence") or {}).get("heading")
        if not heading:
            continue
        p = anchor_pos_in(flat_texts, heading)
        if p is not None:
            fpos[s["section_id"]] = p
    order = sorted(fpos.items(), key=lambda kv: (kv[1], kv[0]))
    regions = {}
    for i, (sid, start) in enumerate(order):
        end = order[i + 1][1] if i + 1 < len(order) else len(flat)
        if end <= start:
            end = start + 1
        regions[sid] = (start, min(end, len(flat)))
    return flat, regions


def contract_segments(raw):
    """Cắt đoạn contract từng section từ text form-domain.js: từ
    `sectionId: '<sid>'` tới sectionId kế tiếp (hoặc cuối file) sau
    `var FORM_TABLE_CONTRACTS`."""
    m_ftc = re.search(r"\bvar\s+FORM_TABLE_CONTRACTS\s*=", raw)
    if not m_ftc:
        return {}
    marks = [m for m in re.finditer(r"sectionId\s*:\s*'([^']+)'", raw)
             if m.start() > m_ftc.start()]
    segs = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        segs[m.group(1)] = raw[m.start():end]
    return segs


def fixed_rows_segment(seg):
    """Sub-đoạn mảng `fixed_rows: [ ... ]` (cân bằng ngoặc vuông)."""
    i0 = seg.index("fixed_rows:")
    j0 = seg.index("[", i0)
    depth = 0
    for j in range(j0, len(seg)):
        if seg[j] == "[":
            depth += 1
        elif seg[j] == "]":
            depth -= 1
            if depth == 0:
                return seg[j0:j + 1]
    return seg[j0:]


# ============================================================ 1. BHXH tokens
def test_m01_bhxh_tokens(flat_m01, regions_m01):
    reg = regions_m01.get("bhxh_phuong_thuc_dong")
    if reg is None:
        check("[M01-BHXH-tokens] anchor heading census tìm thấy trong blocks "
              "phẳng", False, "không tính được vị trí anchor %r"
              % BHXH_HEADING)
        check("[M01-BHXH-tokens] vùng anchor chứa đủ 3/3 chk token",
              False, "không có vùng anchor")
        return
    check("[M01-BHXH-tokens] anchor '%s' -> vùng blocks [%d:%d) trên %d "
          "block phẳng (anchor census cuối của PLI_M01 -> hết blocks)"
          % (BHXH_HEADING, reg[0], reg[1], len(flat_m01)), True,
          "vùng tính như build_layout_index")
    ins, chks = region_keys_scan(flat_m01, reg[0], reg[1])
    uniq = sorted(set(chks))
    found = sorted(set(BHXH_TOKENS) & set(uniq))
    missing = sorted(set(BHXH_TOKENS) - set(uniq))
    check("[M01-BHXH-tokens] vùng anchor chứa CẢ 3 chk token "
          "chk_bc_hang_thang/chk_bc_03_thang/chk_bc_06_thang",
          len(found) == 3,
          "tìm thấy %d/3 chk key trong vùng: %s%s"
          % (len(found), ",".join(uniq) or "—",
             ("; THIẾU: " + ",".join(missing)) if missing else ""))
    del ins  # input keys không thuộc assertion nhóm này


# ================================================= 2. census stale documented
def test_m01_bhxh_census_stale(manifest):
    m01 = next(f for f in manifest["forms"] if f["form_id"] == "PLI_M01")
    sec = next((s for s in m01["sections"]
                if s["section_id"] == "bhxh_phuong_thuc_dong"), None)
    if sec is None:
        check("[M01-BHXH-census-stale-documented] manifest có section "
              "bhxh_phuong_thuc_dong", False, "thiếu section")
        return
    check("[M01-BHXH-census-stale-documented] manifest status == "
          "'already_complete' (Lead ĐÃ land LEAD_STATUS_OVERRIDES Phase 3 — "
          "census 'partial' stale vì ba64f29 đã đủ 3/3 token)",
          sec.get("status") == "already_complete",
          "status=%r" % sec.get("status"))
    ove = json.dumps(sec.get("lead_status_override") or {}, ensure_ascii=False)
    check("[M01-BHXH-census-stale-documented] override evidence nêu căn cứ "
          "ba64f29 + tiền lệ PLI_M17",
          "ba64f29" in ove and "PLI_M17" in ove, "evidence: %s" % ove[:140])
    notes = sec.get("notes") or ""
    check("[M01-BHXH-census-stale-documented] notes census có chứa token "
          "'chk_bc_03_thang'",
          "chk_bc_03_thang" in notes,
          "notes: %s" % notes[:140])


# ========================================================= 3. spec fixed-rows
def test_tai_san_fixed_rows_specs():
    for fid, sid, spec_path in TAI_SAN_SECTIONS:
        tag = "%s/%s" % (fid, sid)
        doc = load_json(spec_path)
        entry = next((t for t in doc.get("tables") or []
                      if (t.get("spec") or {}).get("id") == sid), None)
        if entry is None:
            check("[%s] spec table entry tồn tại" % tag, False,
                  "không thấy tables[] entry với spec.id=%s trong %s"
                  % (sid, os.path.relpath(spec_path, REPO)))
            continue
        sp = entry["spec"]
        check("[%s] spec kind == 'fixed-matrix'" % tag,
              sp.get("kind") == "fixed-matrix", "kind=%r" % sp.get("kind"))
        rows = sp.get("fixed_rows") or []
        check("[%s] spec fixed_rows có đúng 7 phần tử (6 tài sản + tổng)"
              % tag, len(rows) == 7,
              "n=%d ids=%s" % (len(rows),
                               ",".join(r.get("id") or "?" for r in rows)))
        last = rows[-1] if rows else {}
        check("[%s] spec fixed_rows phần tử cuối id=='tong_so' và "
              "output_only==true" % tag,
              last.get("id") == "tong_so"
              and last.get("output_only") is True,
              "last=%s" % json.dumps(last, ensure_ascii=False))
        totals = sp.get("totals") or []
        formulas = {t.get("formula") for t in totals}
        check("[%s] spec totals có formula sum cho gia_tri_vnd và ty_le"
              % tag,
              "sum(gia_tri_vnd)" in formulas and "sum(ty_le)" in formulas,
              "formulas=%s" % sorted(x for x in formulas if x))
        cols = sp.get("columns") or []
        c0 = cols[0] if cols else {}
        check("[%s] spec cột 0 header 'Tài sản góp vốn' tag null + "
              "input_type readonly" % tag,
              c0.get("header") == "Tài sản góp vốn"
              and c0.get("tag") is None
              and c0.get("input_type") == "readonly",
              "col0=%s" % json.dumps(c0, ensure_ascii=False))
        drops = set(entry.get("drop") or [])
        check("[%s] spec drop list chứa '^stt$' và '^\\d$'" % tag,
              "^stt$" in drops and "^\\d$" in drops,
              "drop có %d pattern; ^stt$ %s, ^\\d$ %s"
              % (len(drops), "CÓ" if "^stt$" in drops else "THIẾU",
                 "CÓ" if "^\\d$" in drops else "THIẾU"))


# ======================================================= 4. STT not an input
def test_tai_san_stt_not_input(flat_by_form, regions_by_form):
    for fid, sid, _spec in TAI_SAN_SECTIONS:
        tag = "%s/%s" % (fid, sid)
        flat = flat_by_form[fid]
        reg = regions_by_form[fid].get(sid)
        if reg is None:
            check("[%s] vùng anchor tính được trong blocks" % tag, False,
                  "không thấy anchor của section trong blocks phẳng")
            continue
        ins, _chks = region_keys_scan(flat, reg[0], reg[1])
        uniq = sorted(set(ins))
        bad = [k for k in uniq if k == "stt" or k.endswith(".stt")]
        check("[%s] không có input key nào == 'stt' hoặc kết thúc '.stt' "
              "trong vùng anchor (STT là số thứ tự in sẵn, không phải field "
              "người dùng nhập)" % tag,
              not bad,
              "đã quét đệ quy %d input key vùng blocks [%d:%d)%s"
              % (len(uniq), reg[0], reg[1],
                 ("; key vi phạm: " + ",".join(bad)) if bad else ""))


# ================================================== 5+6. runtime contracts
def test_runtime_contracts():
    with open(FORM_DOMAIN_JS, "r", encoding="utf-8") as f:
        raw = f.read()
    segs = contract_segments(raw)
    if not segs:
        check("[runtime-stt-mode] FORM_TABLE_CONTRACTS đọc được từ "
              "form-domain.js", False, "không tìm thấy var FORM_TABLE_"
              "CONTRACTS")
        return
    for _fid, sid, _spec in TAI_SAN_SECTIONS:
        tag = "runtime/%s" % sid
        seg = segs.get(sid)
        if seg is None:
            check("[%s] contract segment tồn tại trong FORM_TABLE_CONTRACTS"
                  % tag, False, "không thấy sectionId: '%s'" % sid)
            continue
        # 5. stt: { mode: ... }
        m_mode = re.search(r"stt:\s*\{\s*mode:\s*'(generated|none)'\s*\}",
                           seg)
        check("[%s] contract khai stt: { mode: 'generated'|'none' }" % tag,
              m_mode is not None,
              "mode=%s" % (m_mode.group(1) if m_mode else "—"))
        # 6. fixed_rows: 6 phần tử label (không đếm tong)
        has_fixed = "fixed_rows:" in seg
        n_label_non_tong = 0
        ids = []
        if has_fixed:
            rows_txt = fixed_rows_segment(seg)
            entries = re.findall(
                r"\{\s*id:\s*'([A-Za-z0-9_]+)'\s*,\s*label:\s*'", rows_txt)
            ids = re.findall(r"\{\s*id:\s*'([A-Za-z0-9_]+)'", rows_txt)
            n_label_non_tong = sum(1 for i in entries if i != "tong_so")
        check("[%s] contract fixed_rows tồn tại và có 6 phần tử label "
              "(không đếm tong) — bằng chứng fixed_rows tầng runtime" % tag,
              has_fixed and n_label_non_tong == 6,
              "n_label(không tong)=%d; ids=%s"
              % (n_label_non_tong, ",".join(ids) or "—"))


def main():
    print("== phase3 lane B — domain evidence PLI_M01 / PLI_M02 ==")

    manifest = load_json(MANIFEST_PATH)
    flat_m01, regions_m01 = build_regions("PLI_M01")
    flat_m02, regions_m02 = build_regions("PLI_M02")
    flat_by_form = {"PLI_M01": flat_m01, "PLI_M02": flat_m02}
    regions_by_form = {"PLI_M01": regions_m01, "PLI_M02": regions_m02}

    test_m01_bhxh_tokens(flat_m01, regions_m01)
    test_m01_bhxh_census_stale(manifest)
    test_tai_san_fixed_rows_specs()
    test_tai_san_stt_not_input(flat_by_form, regions_by_form)
    test_runtime_contracts()

    fails = [r for r in RESULTS if not r[1]]
    print("\nTOTAL: %d | PASS: %d | FAIL: %d"
          % (len(RESULTS), len(RESULTS) - len(fails), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
