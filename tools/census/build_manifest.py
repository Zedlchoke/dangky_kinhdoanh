# -*- coding: utf-8 -*-
"""Lead tool: hop nhat 3 census fragment thanh app/data/table_specs/manifest.json
va kiem tra gate T0 (87/87, status hop le, detector signature STT).

Read-only tren production blocks/templates; chi ghi manifest.json (--write).
"""
import argparse
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCKS_DIR = os.path.join(ROOT, "app", "data", "blocks")
TEMPLATES_DIR = os.path.join(ROOT, "app", "templates")
FRAG_DIR = os.path.join(ROOT, "app", "data", "table_specs", "fragments")
MANIFEST_PATH = os.path.join(ROOT, "app", "data", "table_specs", "manifest.json")

FRAGMENTS = [
    ("t0_a", "PLI_M01-M12", "149eb63"),
    ("t0_b", "PLI_M13-M80", "ff09541"),
    ("t0_c", "PLII_M01-M28", "cd144a8"),
]

REVIEWS = {
    "t0_b": {"commit": "f91129b", "verdict": "MERGE-READY", "agree": 47, "disagree": 0},
    "t0_c": {"commit": "9fcee27", "verdict": "NEEDS-FIXES(1)", "agree": 27, "disagree": 1},
}

VALID_STATUS = ("NO_TABLE", "TABLE_COMPLETE", "BLOCKED_LEGAL_REVIEW")

STT_RE = re.compile(r"^\s*STT\b")
GLUED_STT_RE = re.compile(r"^STT[A-ZÀ-Ỹ]")
LIST_HINT_RE = re.compile(r"\b(Danh sách|Liệt kê|Các)\b.{0,60}(sau|dưới đây)", re.I)

DEFECTS = [
    {
        "form_id": "PLII_M01",
        "id": "plii_m01_stt_thieu_tag_ho_gia_dinh",
        "detail": "Template w:tbl[1] (thành viên hộ gia đình) thiếu tag {_stt} ở ô r5c0 -> DOCX render cột STT trống, vi phạm DONE #8.",
        "evidence": "app/data/table_specs/fragments/review_t0_c.md",
        "queue": "P1",
    },
    {
        "form_id": "PLI_M23",
        "id": "pli_m23_heading_numbering",
        "detail": "Fragment ghi heading '6.' nhưng template thật là '7.' (sai số đánh số, không đổi bản chất).",
        "evidence": "app/data/table_specs/fragments/review_t0_b.md",
        "queue": "P1-spec-cleanup",
    },
    {
        "form_id": "PLI_M66",
        "id": "pli_m66_bo_ten_ma_x23",
        "detail": "Note '1 bộ tên+mã' thực tế lặp ×2/×3 trong mẫu; cần tách section khi rollout.",
        "evidence": "app/data/table_specs/fragments/review_t0_b.md",
        "queue": "P3-branches-products-admin",
    },
]

SIGNATURE_CLASSIFICATIONS = {
    "PLII_M06": [{"block": 14, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "Cau van huong dan ke khai khi mat ket noi CSDL; review_t0_c xac minh 0 w:tbl."}],
    "PLII_M11": [{"block": 18, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "'bao cao ve cac noi dung sau' la chu thich muc; khong co luoi theo sau."}],
    "PLII_M21": [{"block": 24, "verdict": "FALSE_POSITIVE_PROSE",
                  "reason": "Cau van ve nop ho so moi/gop noi dung thay doi; khong co luoi theo sau."}],
    "PLI_M18": [{"block": 35, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M32": [{"block": 14, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M33": [{"block": 19, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "Chan trang truong hop khong co CCCD/mat ket noi CSDL; 0 w:tbl."}],
    "PLI_M50": [{"block": 15, "verdict": "FALSE_POSITIVE_PROSE",
                 "reason": "'Yeu cầu doanh nghiệp báo cáo về các nội dung sau' la dau muc van ban; vung tuong ung da duoc ghi section noi_dung_yeu_cau_bao_cao (output-table/no_table)."}],
}

NO_TABLE_SECTION_KINDS = ("unknown", "output-table")

CAVEATS = [
    "~34 anchor trong t0_b viết tắt '...docx#pN' không resolve được bằng máy (đã review xác minh tay); chuẩn hóa khi sinh spec.",
    "PLI_M72: chỉ occurrence 1 có loop ds_nganh (Wave 2B); 4 vùng còn lại missing_grid -> P1 occurrence identity.",
    "Form BLOCKED_LEGAL_REVIEW không tính TABLE_COMPLETE; cần quyết định người dùng trước khi rollout tương ứng.",
]


def load_fragments():
    forms = []
    for tag, rng, commit in FRAGMENTS:
        path = os.path.join(FRAG_DIR, "%s.json" % tag)
        data = json.load(open(path, encoding="utf-8"))
        for f in data["forms"]:
            f["_source_fragment"] = tag
            f["_source_commit"] = commit
            f["_range"] = rng
            forms.append(f)
    return forms


def normalize_section(sec):
    out = dict(sec)
    sk = out.pop("semantic_key_suggestion", None)
    if sk is not None:
        out["semantic_key"] = sk
    return out


def para_text(block):
    parts = []
    for run in block.get("runs", []):
        if isinstance(run, dict) and isinstance(run.get("text"), str):
            parts.append(run["text"])
    return "".join(parts)


def recount_blocks(form_id):
    path = os.path.join(BLOCKS_DIR, "%s.json" % form_id)
    data = json.load(open(path, encoding="utf-8"))
    counts = {"p": 0, "chk": 0, "table": 0, "loop": 0}
    sig_p = 0
    hints = 0
    hits = []
    for bi, b in enumerate(data["blocks"]):
        t = b.get("t")
        if t in counts:
            counts[t] += 1
        if t == "p":
            txt = para_text(b)
            stt_hit = bool(STT_RE.search(txt) or GLUED_STT_RE.match(txt.strip()))
            hint_hit = bool(LIST_HINT_RE.search(txt))
            if stt_hit:
                sig_p += 1
            if hint_hit:
                hints += 1
            if stt_hit or hint_hit:
                hits.append({"block": bi, "stt": stt_hit, "list_hint": hint_hit,
                             "excerpt": txt.strip()[:120]})
    return counts, sig_p, hints, hits


def deep_template_tables(form_id):
    from docx import Document

    path = os.path.join(TEMPLATES_DIR, "%s.docx" % form_id)
    doc = Document(path)
    n = len(doc.tables)
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for part in (doc.part.header_parts if hasattr(doc.part, "header_parts") else []):
        pass
    for rel in doc.part.rels.values():
        if rel.reltype.endswith("/header") or rel.reltype.endswith("/footer"):
            root = rel.target_part._element if hasattr(rel.target_part, "_element") else None
            if root is not None:
                n += len(root.findall(".//%stbl" % W))
    body_root = doc.element.body
    raw_tbl = len(body_root.findall(".//%stbl" % W))
    return max(n, raw_tbl)


def build(forms):
    forms_sorted = sorted(forms, key=lambda f: f["form_id"])
    out_forms = []
    for f in forms_sorted:
        fid = f["form_id"]
        counts, sig_p, hints, hits = recount_blocks(fid)
        frag_counts = f.get("summary_counts", {})
        entry = {
            "form_id": fid,
            "form_status": f["form_status"],
            "source_fragment": f["_source_fragment"],
            "source_commit": f["_source_commit"],
            "sections": [normalize_section(s) for s in f.get("sections", [])],
            "legal_questions": f.get("legal_questions", []),
            "defects": [d for d in DEFECTS if d["form_id"] == fid],
            "summary_counts_fragment": frag_counts,
            "summary_counts_recount": counts,
            "detector": {"p_signatures": sig_p, "list_hints": hints,
                         "hits": hits,
                         "classifications": SIGNATURE_CLASSIFICATIONS.get(fid, [])},
        }
        out_forms.append(entry)
    return {
        "version": "table-manifest-v1",
        "generated_by": "lead/tools/census/build_manifest.py",
        "sources": [
            {"fragment": tag, "range": rng, "commit": commit} for tag, rng, commit in FRAGMENTS
        ],
        "reviews": REVIEWS,
        "caveats": CAVEATS,
        "totals": {},
        "forms": out_forms,
    }

def validate(manifest, deep):
    errors = []
    block_files = sorted(
        os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(BLOCKS_DIR, "*.json"))
    )
    mids = sorted(f["form_id"] for f in manifest["forms"])
    if len(mids) != 87:
        errors.append("manifest co %d form, can 87" % len(mids))
    if mids != block_files:
        errors.append("manifest ids khac danh sach blocks: %s" % (
            set(mids) ^ set(block_files)))
    tot_status = {}
    tot_sections = {}
    tot_sig = 0
    stale = []
    for f in manifest["forms"]:
        fid = f["form_id"]
        st = f["form_status"]
        if st not in VALID_STATUS:
            errors.append("%s: form_status '%s' khong hop le" % (fid, st))
        tot_status[st] = tot_status.get(st, 0) + 1
        rc = f["summary_counts_recount"]
        fc = f.get("summary_counts_fragment", {})
        for k in ("p", "chk", "table", "loop"):
            if fc and fc.get(k, -1) != rc[k]:
                errors.append("%s: summary_counts.%s fragment=%s recount=%s" % (fid, k, fc.get(k), rc[k]))
        det = f["detector"]
        hits = det.get("hits", [])
        cls_by_block = {c["block"]: c for c in det.get("classifications", [])}
        uncovered = [h for h in hits if h["block"] not in cls_by_block]
        for blk, c in sorted(cls_by_block.items()):
            if not any(h["block"] == blk for h in hits):
                stale.append("%s#b%03d" % (fid, blk))
            if st == "NO_TABLE" and not c["verdict"].startswith("FALSE_POSITIVE"):
                errors.append("%s: NO_TABLE nhung classification %s khong phai false positive" % (fid, c["verdict"]))
        if st == "NO_TABLE":
            if uncovered:
                tot_sig += len(uncovered)
                errors.append("%s: NO_TABLE co %d signature chua classify: blocks %s" % (
                    fid, len(uncovered), [h["block"] for h in uncovered]))
            bad_secs = [
                s for s in f["sections"]
                if not (s.get("kind") in NO_TABLE_SECTION_KINDS and s.get("status") == "no_table")
            ]
            if bad_secs:
                errors.append("%s: NO_TABLE nhung co section khong phai nhan thuc tin: %s" % (
                    fid, [(s.get("section_id"), s.get("kind"), s.get("status")) for s in bad_secs]))
        else:
            if not f["sections"]:
                errors.append("%s: %s phai co it nhat 1 section entry" % (fid, st))
        for kind in ("editable-grid", "fixed-matrix", "nested-grid", "output-table"):
            tot_sections[kind] = tot_sections.get(kind, 0) + sum(
                1 for s in f["sections"] if s.get("kind") == kind
            )
        if deep:
            ntbl = deep_template_tables(fid)
            f["detector"]["template_w_tbl"] = ntbl
            if st == "NO_TABLE" and ntbl != 0:
                errors.append("%s: NO_TABLE nhung template co %d w:tbl" % (fid, ntbl))
    if stale:
        print("WARNING: classification stale (khong con hit): %s" % ", ".join(stale))
    manifest["totals"] = {
        "forms": len(manifest["forms"]),
        "by_form_status": tot_status,
        "sections_by_kind": tot_sections,
        "unclassified_signatures": tot_sig,
    }
    return errors


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="dem w:tpl trong templates (cham hon)")
    ap.add_argument("--write", action="store_true", help="ghi manifest.json")
    args = ap.parse_args()

    forms = load_fragments()
    manifest = build(forms)
    errors = validate(manifest, args.deep)

    print("Manifest forms:", len(manifest["forms"]))
    print("Totals:", json.dumps(manifest["totals"], ensure_ascii=False, indent=1))
    blocked = [f["form_id"] for f in manifest["forms"] if f["form_status"] == "BLOCKED_LEGAL_REVIEW"]
    print("BLOCKED_LEGAL_REVIEW (%d): %s" % (len(blocked), ", ".join(blocked)))
    if errors:
        print("GATE FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("GATE PASS: 87/87, moi signature da classify, counts khop.")
    if args.write:
        os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1)
        print("Wrote", os.path.relpath(MANIFEST_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
