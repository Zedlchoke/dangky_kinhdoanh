# -*- coding: utf-8 -*-
"""Tach cac mau bieu tu file tong hop _Bieu_mau_PL_I_II_full.docx thanh file docx rieng.

Cach dung:
    python tools/split_full_docx.py <duong_dan_file_full> <thu_muc_dich> --mau 12 13 14
Mau tim kiem la lan xuat hien dau tien cua "Mẫu số N" (thuoc Phu luc I).
"""
import argparse
import re
import sys
import shutil
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

HEADER_RE = re.compile(r"^\s*Mẫu số (\d+)\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("full")
    ap.add_argument("dest")
    ap.add_argument("--mau", type=int, nargs="+", required=True)
    args = ap.parse_args()

    src = Path(args.full)
    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    doc = Document(str(src))
    body = list(doc.element.body.iterchildren())

    def block_text(ch):
        return "".join(n.text or "" for n in ch.iter(qn("w:t")))

    # Anchor "that" = paragraph đúng nguyên văn "Mẫu số N" nằm SAU mục lục
    # (mục lục kết thúc tại khối "CỘNG HÒA XÃ HỘI..." đầu tiên của thân mẫu số 1).
    toc_end = None
    for i, ch in enumerate(body):
        if ch.tag == qn("w:p") and block_text(ch).strip().upper().startswith("CỘNG HÒA"):
            toc_end = i
            break
    if toc_end is None:
        raise SystemExit("Khong tim thay moc bat dau than file")
    print(f"Muc luc ket thuc tai block {toc_end}")
    # Vung than Phu luc I ket thuc truoc marker PHỤ LỤC II
    plii_idx = len(body)
    for i, ch in enumerate(body):
        if i > toc_end and ch.tag == qn("w:p") and re.match(r"^\s*PHỤ LỤC\s*II\b", block_text(ch)):
            plii_idx = i
            break
    print(f"Than Phu luc I: [{toc_end}, {plii_idx})")
    anchors = {}
    for i, ch in enumerate(body):
        if i <= toc_end or i >= plii_idx or ch.tag != qn("w:p"):
            continue
        m = re.fullmatch(r"Mẫu số (\d+)", block_text(ch).strip())
        if m:
            n = int(m.group(1))
            if n not in anchors:
                anchors[n] = i
    print(f"Anchor truc tiep: {sorted(anchors)}")
    starts = {}
    sorted_a = sorted(anchors.items(), key=lambda kv: kv[1])
    for mau in args.mau:
        if mau in anchors:
            starts[mau] = anchors[mau]
            continue
        # Fallback: mau mat tieu de -> vung giua anchor truoc va sau (theo vi tri),
        # lay block dau tien co CỘNG HÒA lam diem bat dau.
        prev_idx = max((v for k, v in sorted_a if k < mau), default=None)
        next_idx = min((v for k, v in sorted_a if k > mau), default=plii_idx)
        if prev_idx is None:
            continue
        for i in range(prev_idx + 1, next_idx):
            if "CỘNG HÒA" in block_text(body[i]).upper():
                starts[mau] = i
                break
    print(f"Diem bat dau su dung: {dict(sorted(starts.items()))}")

    # Ranh gioi ket thuc = anchor ke tiep (TAT CA cac mau, khong chi mau yeu cau)
    all_bounds = sorted(set(list(anchors.values()) + [plii_idx]))

    bounds = sorted((v, k) for k, v in starts.items())
    results = []
    for mau in args.mau:
        if mau not in starts:
            results.append((mau, "KHONG TIM THAY"))
            continue
        s = starts[mau]
        # ket thuc = anchor/ranh gioi ke tiep hoac cuoi than Phu luc I
        e = plii_idx
        for v in all_bounds:
            if v > s:
                e = v
                break
        # bo sectPr cuoi body khoi vung giu (giu lai rieng)
        out_path = dest_dir / f"PL1_Mau_{mau:02d}_tach_tu_file_full.docx"
        shutil.copy(str(src), str(out_path))
        ndoc = Document(str(out_path))
        nbody = ndoc.element.body
        children = list(nbody.iterchildren())
        sect_prs = [c for c in children if c.tag == qn("w:sectPr")]
        for j, ch in enumerate(children):
            if s <= j < e and ch.tag != qn("w:sectPr"):
                continue
            if ch.tag == qn("w:sectPr"):
                continue  # xoa het sectPr giua cac phan, se them lai 1 cua o cuoi
            nbody.remove(ch)
        # dam bao con dung 1 sectPr o cuoi de Word mo dung trang
        if not [c for c in nbody.iterchildren() if c.tag == qn("w:sectPr")]:
            for sp in sect_prs[:1]:
                import copy
                nbody.append(copy.deepcopy(sp))
        # kiem tra noi dung
        txt = "\n".join(
            "".join(n.text or "" for n in p.iter(qn("w:t")))
            for p in nbody.iterchildren() if p.tag == qn("w:p"))
        ok = f"Mẫu số {mau}" in txt
        ndoc.save(str(out_path))
        results.append((mau, f"{out_path.name} ({e - s} block, header={'OK' if ok else 'SAI'})"))

    for mau, msg in results:
        print(f"Mau {mau}: {msg}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
