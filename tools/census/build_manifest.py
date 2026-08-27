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

# Form da chu dong tien hoa SAU census qua wave P1 (regenerate lam thay doi
# p/loop counts). Khong phai drift ro rang; moi dong la mot quyet dinh integrate.
EVOLVED_FORMS = {
    "PLI_M72": "P1: 1 loop -> 5 occurrence ds_nganh_*",
    "PLII_M02": "P1: them 3 loop Muc A (bo_sung/xoa_bo/sua_doi)",
    # W1 regen 2026-08-27 (commit d48eb7d): chu ky tro thanh w:tbl that
    "PLI_M70": "W1: 2 paragraph chu ky -> w:tbl output-table 2x1 (spec publication)",
    "PLI_M71": "W1: heading chu ky -> w:tbl output-table 1x1, giu national-separator",
    # R3B1 regen 2026-08-27 (merge 2202937/29b1efa): glue header nguoi/uy quyen
    # tro thanh loop nested-grid that, theo specs D2.1/D2.4/D2.7 da chot
    "PLI_M02":
        "R3B1: +loop nested-grid ds_nddpl_uy_quyen_chu_so_huu; P2C: +2 "
        "fixed-matrix nguon_von/tai_san (section_specs)",
    "PLI_M12":
        "R3B1: them loop nested-grid ds_ndd_uy_quyen_sau_thay_doi (3->4 loop)",
    "PLI_M15":
        "R3B1: glue header B49 -> loop nested-grid "
        "ds_nddpl_uy_quyen_chu_so_huu_moi (0->1 loop)",
    # Wave P2 regen 2026-08-27 (abe6084/1691728 + Lead regen batch)
    "PLII_M07":
        "P2A D2.8=A: +loop ds_thanh_vien_hkd_gcn (1->2 loop, 7 p -> w:tbl)",
    "PLI_M01":
        "P2C D1.1=A/D1.2=B: tai_san_gop_von_von_dau_tu -> w:tbl fixed-matrix",
    "PLI_M13":
        "P2A D2.6/D2.7=A: glue header -> loop grid ndd_pl_sau_thay_doi (0->1)",
}

TABLE_KINDS = ("editable-grid", "fixed-matrix", "nested-grid", "output-table")
NON_TABLE_KINDS = ("prose-block", "scalar-fields", "source-contamination")
SECTION_KINDS = TABLE_KINDS + NON_TABLE_KINDS
SECTION_STATUSES = (
    "missing_grid", "partial_columns", "partial", "already_complete",
    "output_only", "no_table", "contaminated",
)
NO_TABLE_SECTION_KINDS = ("prose-block", "scalar-fields")

RECLASSIFICATIONS = {
    ("PLII_M17", "ho_so_bao_gom"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Blocks b016-b019 la 3 dong cham tay '1....2....3....' khong input; co quan cap xa viet tay, trung thanh mau."},
    ("PLII_M18", "ho_so_bao_gom"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Giong PLII_M17 (ban nop online): dong cham tay khong input, khong luoi."},
    ("PLI_M09", "vung_nhiem_mau_6789_10"): {
        "kind": "source-contamination", "status": "contaminated",
        "reason": "Template chua nguyen van Mau 6/7/8/9(lan 2)/10 sau chan trang Mau 9 that (#p103-p222); can quyet dinh nguon/pham vi phap ly truoc khi lam bat cu grid nao."},
    ("PLI_M27", "don_vi_tam_ngung_tiep_tuc"): {
        "kind": "editable-grid", "status": "missing_grid",
        "reason": "6 khoi don vi (tam ngung/tiep tuc x CN/VPDD/DDKD) moi khoi 1 bo cn.*; ban chat danh sach don vi -> editable-grid du kien, cho quyet dinh 1-nhieu."},
    ("PLI_M28", "don_vi_cham_dut_hoat_dong"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "Cau truc danh so 1..4 la thong tin MOT don vi/giay; blocks map du cn.dia_chi/cn.ma_so; khong dong lap, khong STT."},
    ("PLI_M50", "noi_dung_yeu_cau_bao_cao"): {
        "kind": "prose-block", "status": "no_table",
        "reason": "Blocks b016-b018 la dong cham '......' khong input cho co quan dien noi dung; khong phai output-table."},
    ("PLI_M54", "xac_nhan_tam_ngung_toan_bo_don_vi"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "Mot cau xac nhan ap dung TOAN BO don vi, da map tu_ngay/den_ngay; census bac bo du doan danh sach cua PLAN muc E."},
    ("PLI_M55", "don_vi_tam_ngung_xac_nhan"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "'sau:' so it, mot giay = mot don vi; blocks map tu_ngay/den_ngay; khong dong lap."},
    ("PLI_M57", "don_vi_tiep_tuc_xac_nhan"): {
        "kind": "scalar-fields", "status": "no_table",
        "reason": "So it, mot giay = mot don vi; blocks map truong ngay thang; khong dong lap."},
    ("PLI_M67", "don_vi_cham_dut_sau_day"): {
        "kind": "editable-grid", "status": "missing_grid",
        "reason": "'(Cac) chi nhanh/VPDD/DDKD sau day' -> ban chat editable-grid du kien; blocks hien chi 1 bo ten/mso/dia_chi; cho quyet dinh 1-nhieu."},
}

STT_RE = re.compile(r"^\s*STT\b")
GLUED_STT_RE = re.compile(r"^STT[A-ZÀ-Ỹ]")
LIST_HINT_RE = re.compile(r"\b(Danh sách|Liệt kê|Các)\b.{0,60}(sau|dưới đây)", re.I)

DEFECTS = [
    # (đã gỡ plii_m01_stt_thieu_tag_ho_gia_dinh: stt_tag=true cho
    #  ds_tv_ho_gia_dinh đã integrate + test_plii_m01_member_stt PASS 5/5)
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

LEAD_STATUS_OVERRIDES = {
    # --- Wave P2 (2026-08-27): merge abe6084 (P2A) / 1691728 (P2C) /
    # a61cdfb (P2D) + Lead regen batch 8 mẫu. Evidence = suite thật đã chạy
    # trên main sau merge; loop_audit census giữ nguyên như hồ sơ lịch sử. ---
    ("PLI_M06", "ds_thanh_vien_tnhh"): {
        "status": "already_complete",
        "evidence": "P2A D2.2=A: cột 10 thoi_han_gop_von đã tag sau regen "
                    "(template 11 tag); test_p2a_people_specs [EVD]/[DELTA] 14 PASS.",
    },
    ("PLI_M07", "ds_co_dong_sang_lap"): {
        "status": "already_complete",
        "evidence": "P2A D2.3=A: +dan_toc cột 6 sau regen (10 tag); cùng kiến "
                    "trúc phẳng với PLI_M08; suite P2A 14 PASS.",
    },
    ("PLI_M08", "ds_co_dong_nn"): {
        "status": "already_complete",
        "evidence": "P2A D2.3=A: ghim spec khớp template (7 tag, thiếu 0); "
                    "suite P2A 14 PASS.",
    },
    ("PLI_M10", "ds_cshhl_doanh_nghiep"): {
        "status": "already_complete",
        "evidence": "P2A D2.5=A: cột quyen_chi_phoi trước Ghi chú (11 tag); "
                    "NĐ 168/2025 đ.b.k1 Đ17; suite P2A 14 PASS.",
    },
    ("PLI_M13", "ndd_pl_sau_thay_doi"): {
        "status": "already_complete",
        "evidence": "P2A D2.6/D2.7=A: loop grid 7 cột + minRows1; nguồn 1 "
                    "row-type nên KHÔNG discriminator (không mislabel); 14 PASS.",
    },
    ("PLII_M07", "m7_danh_sach_thanh_vien_hgd"): {
        "status": "already_complete",
        "evidence": "P2A D2.8=A: key riêng ds_thanh_vien_hkd_gcn đúng 7 cột "
                    "nguồn; test_industry_household 13 PASS (loop ngành không "
                    "xâm lấn).",
    },
    ("PLI_M17", "thue_chi_tieu_6_1_8"): {
        "status": "already_complete",
        "evidence": "P2D audit: chk_* đã gắn tag đủ 17 ô tại base cdf8803; "
                    "manifest census T0 stale; test_p2d_tax_specs 10 PASS.",
    },
    ("PLI_M17", "lua_chon_khu_cn_cxc_kt_kccn"): {
        "status": "already_complete",
        "evidence": "P2D D5.1=A: nhóm checkbox đã tag đủ tại base; census stale.",
    },
    ("PLI_M17", "phuong_thuc_dong_bhxh"): {
        "status": "already_complete",
        "evidence": "P2D D5.1=A: nhóm BHXH đã tag đủ tại base; census stale; "
                    "entry trùng sẽ tạo 2 nguồn sự thật nên không khai thêm.",
    },
    ("PLI_M19", "thue_thay_doi_A"): {
        "status": "already_complete",
        "evidence": "P2D: 9 ô chọn-1 đã tag đủ tại base; test_p2d 10 PASS.",
    },
    ("PLI_M23", "thue_chi_tieu_6_1_6"): {
        "status": "already_complete",
        "evidence": "P2D: 10 ô đã tag đủ tại base; numbering nguồn là mục 7 "
                    "(defect đã ghi); section_id giữ nguyên để JOIN spec/tests.",
    },
    ("PLI_M25", "thue_chi_tieu_6_1_6_ctck"): {
        "status": "already_complete",
        "evidence": "P2D: 10 ô đã tag đủ tại base (CTCK); census stale.",
    },
    ("PLI_M01", "tai_san_gop_von_von_dau_tu"): {
        "status": "already_complete",
        "evidence": "P2C D1.1=A/D1.2=B: fixed-matrix 7 dòng + Tổng số computed, "
                    "'tài sản khác' là ô mô tả text; regen template + "
                    "section_specs; suite P2C 16 PASS, runtime contract wired.",
    },
    ("PLI_M02", "nguon_von_dieule"): {
        "status": "already_complete",
        "evidence": "P2C D1.1=A: 5 dòng + Tổng cộng output_only, cùng key "
                    "canonical F2(M03); regen + section_specs; 16 PASS.",
    },
    ("PLI_M02", "tai_san_gop_von_von_dieu_le"): {
        "status": "already_complete",
        "evidence": "P2C: 6 dòng + Tổng số; 'tài sản khác' ô mô tả theo chữ "
                    "mẫu; regen + section_specs; 16 PASS.",
    },
    # --- R3B1 rebuild (b9bc572): 3 nested-grid thành bảng thật; 2 nhóm cột
    # cuối vẫn KHAI THIẾU chờ owner -> partial_columns (như tiền lệ M09). ---
    ("PLI_M02", "nddpl_uy_quyen_chu_so_huu"): {
        "status": "partial_columns",
        "evidence": "N1 rebuild 14 cột w:tbl thật (visual pilot PASS); thiếu 2 "
                    "nhóm header chưa có evidence tag canonical (gap đã ghi).",
    },
    ("PLI_M12", "ndd_uy_quyen_sau_thay_doi"): {
        "status": "partial_columns",
        "evidence": "N6 rebuild 15 cột; cùng gap 2 nhóm cuối như N1.",
    },
    ("PLI_M15", "ndd_pl_uy_quyen_chu_so_huu_moi"): {
        "status": "partial_columns",
        "evidence": "N7 rebuild 14 cột; cùng gap 2 nhóm cuối như N1.",
    },
    ("PLI_M72", "nganh_nghe_5_loai_hinh"): {
        "status": "already_complete",
        "evidence": "P1 integrate: generator occurrence identity + spec 5 occurrence "
                    "(ds_nganh_dntn/tnhh_1tv/tnhh_2tv/ctcp/dhdn) rebuild du 5 bang; "
                    "tools/test_industry_change.py 6 PASS (spec+blocks+render tung loai hinh, khong tron du lieu).",
    },
    ("PLII_M02", "a6_1_nganh_bo_sung"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_bo_sung (4 cot) qua occurrence contract; "
                    "tools/test_industry_household.py 13 PASS incl. render isolation.",
    },
    ("PLII_M02", "a6_2_nganh_bo"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_xoa_bo; suite household 13 PASS.",
    },
    ("PLII_M02", "a6_3_nganh_sua_chinh"): {
        "status": "already_complete",
        "evidence": "P1 integrate: loop rieng nganh_sua_doi_chi_tiet (3 cot, khong co nganh chinh theo template); "
                    "suite household 13 PASS.",
    },
}

CAVEATS = [
    "~34 anchor trong t0_b viết tắt '...docx#pN' không resolve được bằng máy (đã review xác minh tay); chuẩn hóa khi sinh spec.",
    "PLI_M72: P1 đã integrate đủ 5 lưới ngành theo occurrence contract (anchor nguồn thật p13/42/85/134/168); 4 lưới nested-grid thành viên/cổ đông vẫn BLOCKED chờ legal + people-ownership.",
    "PLII_M02: vùng C.3 giữ tên loop canonical ds_nganh (dùng chung PLI_M02/M07) kèm metadata occurrence_id=nganh_hien_tai.",
    "GRID_META phía app hiện là map phẳng theo tên loop: các loop mới PLI_M72 (5) và PLII_M02 (3 loop Mục A) tạm chạy legacy path, chưa có VSIC/primary validation riêng — queue P1-UI/P2 form-scoped meta.",
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


def normalize_section(fid, sec):
    out = dict(sec)
    sk = out.pop("semantic_key_suggestion", None)
    if sk is not None:
        out["semantic_key"] = sk
    rc = RECLASSIFICATIONS.get((fid, out.get("section_id")))
    if rc is not None:
        out["kind"] = rc["kind"]
        if "status" in rc:
            out["status"] = rc["status"]
        out["lead_reclassification"] = {"reason": rc["reason"]}
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
            "sections": [normalize_section(fid, s) for s in f.get("sections", [])],
            "legal_questions": f.get("legal_questions", []),
            "defects": [d for d in DEFECTS if d["form_id"] == fid],
            "summary_counts_fragment": frag_counts,
            "summary_counts_recount": counts,
            "detector": {"p_signatures": sig_p, "list_hints": hints,
                         "hits": hits,
                         "classifications": SIGNATURE_CLASSIFICATIONS.get(fid, [])},
        }
        for s in entry["sections"]:
            ov = LEAD_STATUS_OVERRIDES.get((fid, s.get("section_id")))
            if ov is not None:
                s["status"] = ov["status"]
                s["lead_status_override"] = {"evidence": ov["evidence"]}
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
                if fid in EVOLVED_FORMS:
                    print("INFO %s: %s fragment=%s recount=%s (%s)" % (
                        fid, k, fc.get(k), rc[k], EVOLVED_FORMS[fid]))
                else:
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
        for s in f["sections"]:
            kind = s.get("kind")
            stat = s.get("status")
            sid = s.get("section_id")
            if kind not in SECTION_KINDS:
                errors.append("%s/%s: section kind '%s' KHONG HOP LE (unknown/planned bi cam)" % (fid, sid, kind))
            if stat not in SECTION_STATUSES:
                errors.append("%s/%s: section status '%s' khong hop le (planned/TODO bi cam)" % (fid, sid, stat))
            if kind == "source-contamination" and st != "BLOCKED_LEGAL_REVIEW":
                errors.append("%s/%s: source-contamination chi cho phep tren form BLOCKED_LEGAL_REVIEW" % (fid, sid))
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
                errors.append("%s: NO_TABLE nhung co section khong phai prose/scalar thuan thong tin: %s" % (
                    fid, [(s.get("section_id"), s.get("kind"), s.get("status")) for s in bad_secs]))
        elif not f["sections"]:
            errors.append("%s: %s phai co it nhat 1 section entry" % (fid, st))
        for kind in SECTION_KINDS:
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
    total_secs = sum(len(f["sections"]) for f in manifest["forms"])
    kind_sum = sum(tot_sections.values())
    if total_secs != kind_sum:
        errors.append("tong so section (%d) khac tong sections_by_kind (%d)" % (total_secs, kind_sum))
    manifest["totals"] = {
        "forms": len(manifest["forms"]),
        "by_form_status": tot_status,
        "sections_total": total_secs,
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
