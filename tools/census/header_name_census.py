# Lane C - READ-ONLY census of header-name occurrences across 87 form templates.
# Sinh docs/audits/header_name_census_<date>.json (raw data) + in summary.
# [sanitize path 2026-09-05 — Lead] script read-only, khong dong production.
import zipfile, re, json, sys, unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def fold(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s.lower()).strip()

TOKEN_RE = re.compile(r"\{[^{}]*\}")
FILL_RE = re.compile(r"[.\-_…·•]{3,}")

# name-label literals (folded). ("ho va ten" is band-only per task.)
PATTERNS = [
    "ten doanh nghiep",
    "ten ho kinh doanh",
    "ten chi nhanh",
    "ten van phong dai dien",
    "ten dia diem kinh doanh",
    "doanh nghiep cu",
    "doanh nghiep moi",
    "ho kinh doanh moi",
    "ten cong ty moi",
    "ten cong ty cu",
    "ten ca nhan",
    "ho va ten",
]

TITLE_RE = re.compile(
    r"^(giay de nghi|giấy đề nghị|don |đơn |thong bao|thông báo|bao cao|báo cáo|"
    r"cong bo|công bố|giay tiep nhan|giấy tiếp nhận|giay chung nhan|giấy chứng nhận|"
    r"danh sach|danh sách|quyet dinh|quyết định|phu luc|phụ lục|cong van|công văn|"
    r"trang thong tin|trang thông tin|giay uy quyen|giấy ủy quyền|thu uy quyen|"
    r"van ban de nghi|văn bản đề nghị|giấy đề nghị)\b", re.I)
CAPTION_RE = re.compile(r"^(pl\s*\d|mau so|mẫu số)", re.I)
QUOCHIEU_RE = re.compile(r"cong hoa xa hoi")

# ---- docx parsing helpers -------------------------------------------------

def para_lines(p):
    """Split a w:p into logical lines at w:br / w:cr; collect text of w:t."""
    lines, cur = [], []
    def walk(el):
        for ch in el:
            if ch.tag in (W + "br", W + "cr"):
                lines.append("".join(cur)); cur.clear()
            elif ch.tag == W + "t":
                cur.append(ch.text or "")
            elif ch.tag == W + "tab":
                cur.append("\t")
            else:
                walk(ch)
    walk(p)
    lines.append("".join(cur))
    return lines

def load_body(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return ET.fromstring(xml).find(W + "body"), xml

def norm(t):
    return t.replace("\u00a0", " ").strip()

# ---- scan one template ----------------------------------------------------

def scan_template(fid, tpl_path):
    body, raw_xml = load_body(tpl_path)
    elems = list(body)
    # text of every top-level element (for title / quoc-hieu detection)
    elem_lines = []  # list of (kind, lines)
    for el in elems:
        if el.tag == W + "p":
            elem_lines.append(("p", [l for l in para_lines(el) if norm(l)]))
        elif el.tag == W + "tbl":
            elem_lines.append(("tbl", []))
        else:
            elem_lines.append((el.tag.split("}")[1], []))

    # title end of band
    title_idx = None
    for i, (kind, lines) in enumerate(elem_lines):
        if kind != "p":
            continue
        for l in lines:
            if CAPTION_RE.match(norm(l)):
                continue
            if TITLE_RE.match(norm(l)):
                title_idx = i
                break
        if title_idx is not None:
            break
    band_end = title_idx if title_idx is not None else 25
    if band_end > 25:
        band_end = 25

    quoc_idx = None
    for i, (kind, lines) in enumerate(elem_lines):
        if kind == "p" and any(QUOCHIEU_RE.search(fold(l)) for l in lines):
            quoc_idx = i
            break
        if kind == "tbl":
            row_texts = table_texts(elems[i])
            if any(QUOCHIEU_RE.search(fold(t)) for t in row_texts):
                quoc_idx = i
                break

    occurrences = []
    no_band = True  # no name label anywhere in band region

    def add_occ(para_id, line_idx, text, para_text, in_table, band_pos, extra):
        f = fold(text)
        for pat in PATTERNS:
            if pat in f:
                if pat == "ho va ten" and band_pos == "after-band":
                    continue  # band-only literal
                occurrences.append(dict(
                    para_idx=para_id, line_idx=line_idx, text=text,
                    para_text=para_text,
                    fill_line=bool(FILL_RE.search(text)),
                    para_has_fill=bool(FILL_RE.search(para_text)),
                    has_token_line=bool(TOKEN_RE.search(text)),
                    has_token_para=bool(TOKEN_RE.search(para_text)),
                    in_table=in_table, band_region=band_pos,
                    matched_pattern=pat, **extra))
                break

    for i, el in enumerate(elems):
        if el.tag == W + "p":
            ls = [l for l in para_lines(el) if norm(l)]
            para_join = "\n".join(ls)
            if not ls:
                continue
            band_pos = ("before-band" if i < band_end else "after-band")
            for j, ln in enumerate(ls):
                add_occ(i, j, ln, para_join, False, band_pos, dict(table_cell=None))
        elif el.tag == W + "tbl":
            # in-band table?
            tbl_band = i < band_end
            tbl = el
            rows = tbl.findall(W + "tr")
            # which rows contain quoc hieu
            row_has_quoc = []
            for tr in rows:
                t = " ".join(cell_texts(tr))
                row_has_quoc.append(bool(QUOCHIEU_RE.search(fold(t))))
            for ri, tr in enumerate(rows):
                for ci, tc in enumerate(tr.findall(W + "tc")):
                    cell_paras = tc.findall(W + "p")
                    for pi, p in enumerate(cell_paras):
                        ls = [l for l in para_lines(p) if norm(l)]
                        if not ls:
                            continue
                        para_join = "\n".join(ls)
                        if tbl_band:
                            band_pos = "band-table"
                        else:
                            band_pos = "after-band"
                        for j, ln in enumerate(ls):
                            add_occ(i, j, ln, para_join, True,
                                    band_pos,
                                    dict(table_cell=f"tbl@{i}.row{ri}.cell{ci}.para{pi}",
                                         same_row_as_quoc=row_has_quoc[ri]))
        else:
            continue

    # token map across whole doc: key -> list of context lines (outside band only)
    token_ctx = {}
    for m in TOKEN_RE.finditer(raw_xml):
        pass  # raw_xml contains braces only in w:t text; refined below
    body_tokens = {}
    for i, el in enumerate(elems):
        if el.tag == W + "p":
            for ln in para_lines(el):
                for m in TOKEN_RE.finditer(ln):
                    key = m.group(0).strip("{}").strip()
                    body_tokens.setdefault(key, []).append(
                        (i, norm(ln)[:160], i < band_end))
        elif el.tag == W + "tbl":
            for p in el.iter(W + "p"):
                for ln in para_lines(p):
                    for m in TOKEN_RE.finditer(ln):
                        key = m.group(0).strip("{}").strip()
                        body_tokens.setdefault(key, []).append(
                            (i, norm(ln)[:160], i < band_end))

    return dict(
        occurrences=occurrences,
        band_end_idx=band_end,
        title_idx=title_idx,
        quoc_hieu_idx=quoc_idx,
        tokens_in_doc={k: v for k, v in body_tokens.items()},
    )

def cell_texts(tr):
    out = []
    for tc in tr.findall(W + "tc"):
        for p in tc.findall(W + "p"):
            out.extend(para_lines(p))
    return out

def table_texts(tbl):
    out = []
    for tr in tbl.findall(W + "tr"):
        out.append(" ".join(cell_texts(tr)))
    return out

# ---- main -----------------------------------------------------------------

def main():
    maps = json.load(open(ROOT / "app/data/form_maps.json", encoding="utf-8"))
    out = {}
    for fid in maps:
        tpl = ROOT / "app/templates" / f"{fid}.docx"
        info = scan_template(fid, tpl)
        occ = info["occurrences"]
        band_occ = [o for o in occ if o["band_region"] != "after-band"]
        out[fid] = dict(
            occurrences=occ,
            band_end_idx=info["band_end_idx"],
            title_idx=info["title_idx"],
            quoc_hieu_idx=info["quoc_hieu_idx"],
            no_band=len(band_occ) == 0,
            tokens_in_doc=info["tokens_in_doc"],
        )
    with open("/tmp/census_work/raw_census.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # quick stats
    n_forms_with_band_occ = sum(1 for v in out.values()
                                if any(o["band_region"] != "after-band"
                                       for o in v["occurrences"]))
    n_band_occ = sum(1 for v in out.values()
                     for o in v["occurrences"] if o["band_region"] != "after-band")
    n_after = sum(1 for v in out.values()
                  for o in v["occurrences"] if o["band_region"] == "after-band")
    print("forms:", len(out))
    print("forms with band-region name occurrence:", n_forms_with_band_occ)
    print("band-region occurrences:", n_band_occ, "| outside-band:", n_after)
    for fid, v in sorted(out.items()):
        b = [o for o in v["occurrences"] if o["band_region"] != "after-band"]
        if b:
            print(f"--- {fid}")
            for o in b:
                print(f"    para={o['para_idx']} line={o['line_idx']} cell={o.get('table_cell')}"
                      f" band={o['band_region']} fill={o['fill_line']}/{o['para_has_fill']}"
                      f" tok={o['has_token_line']}/{o['has_token_para']} :: {o['text'][:90]!r}")

if __name__ == "__main__":
    main()
