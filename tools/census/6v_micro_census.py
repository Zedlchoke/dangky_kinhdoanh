# -*- coding: utf-8 -*-
r"""Micro-census "tỉ mỉ" trên 87 template DOCX (lane 6V-V4, PLAN.md mục 5.1).

READ-ONLY với mọi file tracked: script chỉ ĐỌC app/templates/*.docx, output
duy nhất là tools/census/6v_micro_census.json (--out). KHÔNG sửa template,
KHÔNG phải gate — bằng chứng quyết định phạm vi fix đợt sau.

Bảy nhóm check, mỗi nhóm một counter + danh sách form lệch + ví dụ:
  a. fill_line_style   — kiểu dòng điền trộn lẫn (…… vs ---- vs ____ vs
                         …... / dot ascii vs unicode); chuẩn hóa 1 kiểu là
                         chủ đích, form trộn >= 2 style bị liệt kê.
  b. colon_paren       — space trước ":" của nhãn; space đôi; ngoặc
                         ( ) thiếu đóng/mở trong cùng đoạn.
  c. font_floor        — text có w:sz < 16 half-point (< 8pt) — sàn cỡ chữ
                         PLAN 5.1; run 1pt rỗng cũng được đếm riêng.
  d. superscript_glue  — chữ số chú thích dính chữ / superscript sai vị trí.
                         Tái dùng ĐÚNG logic đã audit:
                         tools/census/check_layout_l1.unresolved_glue_count
                         (numbering_audit GLUE cũng dùng nó), đối chiếu thêm
                         regex phẳng GLUE [^\d\s:]\\d{1,2}\\s*: như
                         numbering_audit.audit_form đã làm.
  e. orphan_heading    — heading lạc đơn dòng ngoài bảng: đoạn thân mà văn
                         bản gập dấu = "stt" (tiền lệ M09 audit từng thấy).
  f. header_band       — band quốc hiệu: bảng 2 ô trái–phải (band table,
                         hình dạng mà docx_to_blocks.is_header_band_table nhận
                         để render hdr2col) vs đoạn 3 dòng center có w:br vs
                         đoạn DÍNH không br (2 cột dính 1 dòng = lệch) vs
                         không có band; kèm căn lề dòng "Số:…" / "Ngày…" .
  g. table_border_pad  — viền bảng uniform: tblBorders thiếu cạnh (partial),
                         style lệch giữa các bảng cùng form, override
                         tcBorders ở mức ô; cell padding (tblCellMar) lệch
                         giữa các bảng cùng form.

Chạy:  python3 -X utf8 tools/census/6v_micro_census.py
Kết quả: stdout bảng tóm tắt + tools/census/6v_micro_census.json
Định dạng JSON: mỗi nhóm {"count": <số form lệch>, "forms": [...],
"examples": [{"form", "detail"}...]}; kèm "per_form" chi tiết từng mẫu.
"""

import argparse
import glob
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(ROOT, "app", "templates")
OUT_DEFAULT = os.path.join(ROOT, "tools", "census", "6v_micro_census.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from check_layout_l1 import unresolved_glue_count, GLUE_RE  # noqa: E402
from layout_roles import SOURCE_INDICATOR_RE  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_EXAMPLES = 6

FILL_TOKEN_RE = re.compile(r"(\u2026+|\.{3,}|-{3,}|_{3,}|[\u2026.]{3,})")
SPACE_COLON_RE = re.compile(r"\S[ \t\u00a0]+:")      # "nhãn :" — space trước :
DOUBLE_SPACE_RE = re.compile(r"\S {2,}(?=\S)")        # space đôi giữa chữ
# marker danh sách "a)" "b)" đầu từ — không phải ngoặc lệch
LIST_MARKER_RE = re.compile(r"(^|[\s(>])[a-zà-ỹđ]\)", re.UNICODE)
FOLD_STT = ("stt", "stt.", "stt:", "số tt", "số tt.")
HEADER_KEYS = ("CƠ QUAN", "CỘNG HÒA")
MOTTO = "Độc lập - Tự do - Hạnh phúc"


def fold(text):
    """Gập dấu tiếng Việt + lowercase — dùng cho so khớp không phân biệt dấu."""
    import unicodedata
    nfd = unicodedata.normalize("NFD", text or "")
    no_mark = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", no_mark.replace("đ", "d")).strip().lower()


def para_text(p, with_br=False):
    """Text nối toàn bộ w:t của đoạn; with_br thì chèn '\\n' tại w:br, '\\t' tại tab."""
    parts = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif with_br and node.tag == W + "br":
            parts.append("\n")
        elif with_br and node.tag == W + "tab":
            parts.append("\t")
    return "".join(parts)


def para_jc(p):
    jc = p.find(W + "pPr/" + W + "jc")
    return jc.get(W + "val") if jc is not None else None


def load_body(path):
    with zipfile.ZipFile(path) as z:
        return ET.fromstring(z.read("word/document.xml")).find(W + "body")


def classify_fill(tok):
    chars = set(tok)
    if chars == {"-"}:
        return "DASH"
    if chars == {"_"}:
        return "UNDERSCORE"
    if chars == {"…"}:
        return "DOT_UNICODE"
    if chars == {"."}:
        return "DOT_ASCII"
    return "MIXED"  # …... trộn unicode + ascii


def para_runs_blocks(p):
    """Chuyển đoạn w:p sang shape block {runs:[{text, vertAlign}]} để tái dùng
    unresolved_glue_count (cùng shape blocks JSON mà numbering_audit dùng)."""
    runs = []
    for r in p.findall(W + "r"):
        va = r.find(W + "rPr/" + W + "vertAlign")
        txt = "".join(t.text or "" for t in r.iter(W + "t"))
        if not txt:
            continue
        runs.append({"text": txt,
                     "vertAlign": va.get(W + "val") if va is not None else None})
    return {"t": "p", "role": None, "runs": runs}


# --------------------------------------------------------------------- nhóm

def census_fill_line(fid, body, out):
    """a. kiểu dòng điền trộn lẫn."""
    styles = Counter()
    samples = []
    for p in body.iter(W + "p"):
        txt = para_text(p)
        for m in FILL_TOKEN_RE.finditer(txt):
            st = classify_fill(m.group(0))
            styles[st] += 1
            if (st, txt.strip()[:70]) not in samples:
                samples.append((st, txt.strip()[:70]))
    out["fill_styles"] = sorted(styles)
    out["fill_style_counts"] = dict(styles)
    if len(styles) > 1:
        out["fill_line_style"] = {
            "styles": sorted(styles),
            "counts": dict(styles),
            "samples": [{"style": s, "context": c} for s, c in samples[:4]],
        }


def census_colon_paren(fid, body, out):
    """b. space trước ':', space đôi, ngoặc lệch."""
    hits = {"space_colon": [], "double_space": [], "paren": []}
    for p in body.iter(W + "p"):
        txt = para_text(p).strip()
        if not txt:
            continue
        # marker danh sách "a)" là chú dòng hợp lệ, không phải ngoặc lệch
        balance_txt = LIST_MARKER_RE.sub(r"\1", txt)
        for m in SPACE_COLON_RE.finditer(txt):
            ctx = txt[max(0, m.start() - 30):m.end() + 12]
            hits["space_colon"].append(ctx.strip())
            break
        m = DOUBLE_SPACE_RE.search(txt)
        if m:
            hits["double_space"].append(txt[max(0, m.start() - 25):m.end() + 20].strip())
        if balance_txt.count("(") != balance_txt.count(")"):
            hits["paren"].append(txt[:80])
    entry = {}
    if hits["space_colon"]:
        entry["space_before_colon"] = {"n_paragraphs": len(hits["space_colon"]),
                                       "samples": hits["space_colon"][:3]}
    if hits["double_space"]:
        entry["double_space"] = {"n_paragraphs": len(hits["double_space"]),
                                 "samples": hits["double_space"][:3]}
    if hits["paren"]:
        entry["paren_unbalanced"] = {"n_paragraphs": len(hits["paren"]),
                                     "samples": hits["paren"][:3]}
    if entry:
        out["colon_paren"] = entry


def census_font_floor(fid, body, out):
    """c. w:sz < 16 half-point (< 8pt) — cả run thật lẫn paragraph-mark."""
    low, empty_low, mark_low = [], 0, 0
    for r in body.iter(W + "r"):
        sz = r.find(W + "rPr/" + W + "sz")
        if sz is None:
            continue
        try:
            half = int(sz.get(W + "val"))
        except (TypeError, ValueError):
            continue
        if half < 16:
            txt = "".join(t.text or "" for t in r.iter(W + "t"))
            if txt.strip():
                low.append({"pt": half / 2.0, "text": txt.strip()[:60]})
            else:
                empty_low += 1
    # w:sz của dấu ¶ cuối đoạn (w:pPr/w:rPr/w:sz): không nằm trong w:r nào
    for p in body.iter(W + "p"):
        sz = p.find(W + "pPr/" + W + "rPr/" + W + "sz")
        if sz is None:
            continue
        try:
            if int(sz.get(W + "val")) < 16:
                mark_low += 1
        except (TypeError, ValueError):
            continue
    if low or empty_low or mark_low:
        entry = {"runs_below_8pt": len(low), "empty_runs_below_8pt": empty_low,
                 "paragraph_marks_below_8pt": mark_low}
        if low:
            entry["samples"] = low[:3]
        out["font_floor"] = entry


def census_superscript_glue(fid, body, out):
    """d. superscript/footnote vị trí — logic tái dùng từ check_layout_l1."""
    glue_unresolved, glue_flat_hits, sup_runs = [], [], 0
    for p in body.iter(W + "p"):
        raw = para_text(p).strip()
        # dòng marker kỹ thuật "PL1 - Mau so 1: ..." — cùng loại trừ với
        # numbering_audit (role=source-indicator ở blocks): "PL2" trúng GLUE_RE
        # là false positive, không phải chú thích dính chữ.
        if raw and SOURCE_INDICATOR_RE.match(fold(raw)):
            continue
        for r in p.findall(W + "r"):
            va = r.find(W + "rPr/" + W + "vertAlign")
            if va is not None and va.get(W + "val") == "superscript":
                sup_runs += 1
                txt = "".join(t.text or "" for t in r.iter(W + "t"))
                # superscript chứa CHỮ/gạch dưới (vd "____") = vị trí đáng ngờ;
                # chữ số + dấu câu ("5:", "4, 5") là marker chú thích hợp lệ.
                if re.search(r"[A-Za-zÀ-ỹ_]", txt):
                    glue_flat_hits.append("SUP:" + txt.strip()[:40])
        blk = para_runs_blocks(p)
        if raw and GLUE_RE.search(raw) and unresolved_glue_count(blk) > 0:
            glue_unresolved.append(raw[:60])
    entry = {}
    if glue_unresolved:
        entry["glue_unresolved"] = {"n_paragraphs": len(glue_unresolved),
                                    "samples": glue_unresolved[:3]}
    if glue_flat_hits:
        entry["superscript_non_digit"] = {"n_runs": len(glue_flat_hits),
                                          "samples": glue_flat_hits[:3]}
    # superscript_runs_total chỉ là NGỮ CẢNH (chú thích số hợp lệ vẫn có) —
    # không đủ để coi form là lệch, chỉ kèm khi đã có hit.
    if entry and sup_runs:
        entry["superscript_runs_total"] = sup_runs
    if entry:
        out["superscript_glue"] = entry


def census_orphan_heading(fid, body, out):
    """e. heading lạc đơn dòng "STT" ngoài bảng (body-level)."""
    hits = []
    for p in body.findall(W + "p"):  # chỉ đoạn THÂN, không đụng ô bảng
        txt = para_text(p).strip()
        if not txt or len(txt) > 12:
            continue
        if fold(txt) in FOLD_STT:
            hits.append(txt)
    if hits:
        out["orphan_heading"] = {"n_paragraphs": len(hits), "samples": hits[:3]}


def census_header_band(fid, body, out):
    """f. band quốc hiệu trái–phải + căn dòng Số:/Ngày."""
    mechanism = None
    band_jc = None
    glued = False
    for p in body.findall(W + "p"):
        txt_br = para_text(p, with_br=True)
        if "CỘNG HÒA" in txt_br:
            band_jc = para_jc(p)
            lines = txt_br.split("\n")
            qua_line = next((l for l in lines if "CỘNG HÒA" in l), "")
            motto_line = next((l for l in lines if "Độc lập" in l), "")
            if motto_line and motto_line != qua_line:
                mechanism = "para_br_3lines" if band_jc in (None, "center") \
                    else "para_br_align:" + str(band_jc)
            else:
                mechanism = "para_glued_no_br"
                glued = True
            break
    for tbl in body.findall(W + "tbl"):
        all_txt = "".join(t.text or "" for t in tbl.iter(W + "t"))
        if "CỘNG HÒA" in all_txt and "Độc lập" in all_txt:
            row0 = tbl.find(W + "tr")
            n_cells = len(row0.findall(W + "tc")) if row0 is not None else 0
            mechanism = "table_2col" if n_cells >= 2 else "table_%dcell" % n_cells
            break
    out["band_mechanism"] = mechanism or "none"

    so_line_jc = None
    for i, p in enumerate(body.findall(W + "p")):
        txt = para_text(p).strip()
        f = fold(txt)
        if f.startswith("so:") or f.startswith("so :"):
            so_line_jc = para_jc(p) or "inherit"
            break
        if i > 14:
            break
    if so_line_jc is not None:
        out["so_line_jc"] = so_line_jc
    if glued or (mechanism or "none") == "none":
        out["header_band"] = {"issue": "glued_no_br" if glued else "no_band"}
    elif so_line_jc not in (None, "right", "end"):
        out["header_band"] = {"issue": "so_line_not_right", "jc": so_line_jc}


def table_signature(tbl):
    """(edges/val của tblBorders, cellMar signature, cell overrides) của 1 bảng."""
    tpr = tbl.find(W + "tblPr")
    borders, cellmar, overrides = {}, None, 0
    if tpr is not None:
        tb = tpr.find(W + "tblBorders")
        if tb is not None:
            for edge in tb:
                name = edge.tag.split("}")[1]
                borders[name] = edge.get(W + "val")
        cm = tpr.find(W + "tblCellMar")
        if cm is not None:
            cellmar = tuple(sorted(
                (e.tag.split("}")[1], e.get(W + "w") or "0") for e in cm))
    # override viền ở mức ô: tcBorders khai cạnh mà tblBorders không có,
    # hoặc giá trị khác bảng — điểm bất uniform thật sự.
    for tcb in tbl.findall(".//" + W + "tcPr/" + W + "tcBorders"):
        for edge in tcb:
            name = edge.tag.split("}")[1]
            val = edge.get(W + "val")
            if val in (None, "nil", "none"):
                continue
            if borders.get(name) != val:
                overrides += 1
    return borders, cellmar, overrides


def census_table_border_pad(fid, body, out):
    """g. viền bảng uniform + cell padding."""
    tbls = body.findall(W + "tbl")
    if not tbls:
        return
    sigs, borderless, partial, total_overrides, cellmar_set = set(), 0, 0, 0, set()
    for tbl in tbls:
        borders, cellmar, overrides = table_signature(tbl)
        total_overrides += overrides
        if cellmar:
            cellmar_set.add(cellmar)
        if not borders:
            borderless += 1
            continue
        edges = set(borders)
        # bảng viền đủ khung chuẩn = 4 cạnh ngoài + 2 cạnh trong
        if not {"top", "left", "bottom", "right", "insideH", "insideV"} <= edges:
            partial += 1
        sigs.add(tuple(sorted(borders.items())))
    entry = {"tables": len(tbls), "borderless": borderless,
             "partial_borders": partial, "cell_border_overrides": total_overrides}
    if len(sigs) > 1:
        entry["border_sig_variants"] = len(sigs)
    if len(cellmar_set) > 1:
        entry["cellmar_variants"] = len(cellmar_set)
    issues = partial + total_overrides + (len(sigs) - 1 if len(sigs) > 1 else 0) \
        + (len(cellmar_set) - 1 if len(cellmar_set) > 1 else 0)
    if issues:
        out["table_border_pad"] = entry


# ------------------------------------------------------------------- driver

GROUP_KEYS = ["a_fill_line_style", "b_colon_paren", "c_font_floor",
              "d_superscript_glue", "e_orphan_heading", "f_header_band",
              "g_table_border_pad"]
GROUP_TITLES = {
    "a_fill_line_style": "a. kiểu dòng điền trộn lẫn",
    "b_colon_paren": "b. space ':' / space đôi / ngoặc lệch",
    "c_font_floor": "c. cỡ chữ < 8pt (w:sz < 16)",
    "d_superscript_glue": "d. superscript/footnote dính chữ",
    "e_orphan_heading": "e. heading 'STT' lạc đơn dòng",
    "f_header_band": "f. band quốc hiệu trái–phải",
    "g_table_border_pad": "g. viền bảng uniform / cell padding",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "*.docx")))
    per_form = {}
    for path in paths:
        fid = os.path.basename(path)[:-5]
        body = load_body(path)
        entry = {}
        census_fill_line(fid, body, entry)
        census_colon_paren(fid, body, entry)
        census_font_floor(fid, body, entry)
        census_superscript_glue(fid, body, entry)
        census_orphan_heading(fid, body, entry)
        census_header_band(fid, body, entry)
        census_table_border_pad(fid, body, entry)
        per_form[fid] = entry

    groups = {}
    for gk in GROUP_KEYS:
        # "lệch" theo nhóm: a = trộn >= 2 style; f = glued/no_band/so_line;
        # còn lại = có entry tương ứng.
        forms, examples = [], []
        for fid, entry in per_form.items():
            if gk == "a_fill_line_style":
                hit = entry.get("fill_line_style")
                detail = ("trộn %d style: %s" % (len(hit["styles"]), ",".join(hit["styles"]))
                          if hit else None)
            elif gk == "f_header_band":
                issue = (entry.get("header_band") or {}).get("issue")
                detail = ("band=%s %s" % (entry.get("band_mechanism"), issue)
                          if issue else None)
            else:
                short = gk.split("_", 1)[1]
                hit = entry.get(short)
                detail = json.dumps(hit, ensure_ascii=False)[:160] if hit else None
            if detail:
                forms.append(fid)
                if len(examples) < MAX_EXAMPLES:
                    examples.append({"form": fid, "detail": detail})
        groups[gk] = {"count": len(forms), "forms": forms, "examples": examples}

    # band mechanism distribution (ngữ cảnh nhóm f, mọi form)
    mech = Counter(e.get("band_mechanism") for e in per_form.values())

    report = {
        "generated_by": "tools/census/6v_micro_census.py",
        "base_commit": "7e39a78",
        "scope": "app/templates/*.docx (87 template; 91 file corpus = 87 + "
                 "4 biến thể render M72)",
        "checklist": "PLAN.md mục 5.1 (tiêu chí tỉ mỉ trang in)",
        "read_only": True,
        "scanned": len(paths),
        "band_mechanism_distribution": dict(mech),
        "groups": groups,
        "per_form": per_form,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    # ------- bảng tóm tắt stdout
    print("micro-census 87 template — %s" % ("scan OK" if len(paths) == 87
                                             else "CẢNH BÁO: %s file" % len(paths)))
    print("band mechanism:", dict(mech))
    print()
    print("%-22s %-38s %6s  ví dụ" % ("nhóm", "tiêu chí", "form lệch"))
    print("-" * 100)
    for gk in GROUP_KEYS:
        g = groups[gk]
        print("%-22s %-38s %6d  %s" % (gk, GROUP_TITLES[gk][3:], g["count"],
                                       ", ".join(g["forms"][:3])))
    print()
    print("report ->", os.path.relpath(args.out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
