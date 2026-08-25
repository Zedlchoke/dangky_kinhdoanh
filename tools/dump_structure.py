# -*- coding: utf-8 -*-
"""Dump cau truc block cua file docx de phan tich: paragraphs + tables (chi so hang/cot + van ban).

Cach dung:
    python tools/dump_structure.py <file.docx> [gioi_han_block]
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_blocks(doc):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", Table(child, doc))


def tc_iter(tr):
    """Duyệt con TRỰC TIẾP w:tc của w:tr thay vì row.cells + dedup id():
    proxy lxml/python-docx tạo mới mỗi lần truy cập nên id() không ổn định,
    dedup theo id() có thể bỏ nhầm ô. Ô merge ngang được cộng dồn chỉ số cột;
    ô vMerge-continue (text rỗng, phần tử riêng) được bỏ qua như bản cũ."""
    for child in tr.iterchildren():
        if child.tag == qn("w:tc"):
            yield child


def cell_text(tc, doc):
    return "\n".join(
        Paragraph(p_el, doc).text
        for p_el in tc.iterchildren()
        if p_el.tag == qn("w:p")
    )


def main():
    path = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    doc = Document(str(path))
    n = 0
    for kind, obj in iter_blocks(doc):
        if kind == "p":
            txt = obj.text.strip()
            if txt:
                print(f"P[{n}] {txt}")
        else:
            print(f"T[{n}] rows={len(obj.rows)} cols={len(obj.columns)}")
            for ri, tr in enumerate(obj._tbl.tr_lst):
                cells = []
                ci = 0
                for tc in tc_iter(tr):
                    tc_pr = tc.find(qn("w:tcPr"))
                    span = 1
                    vm_continue = False
                    if tc_pr is not None:
                        gs = tc_pr.find(qn("w:gridSpan"))
                        if gs is not None:
                            span = int(gs.get(qn("w:val")))
                        vm = tc_pr.find(qn("w:vMerge"))
                        if vm is not None and (vm.get(qn("w:val")) or "continue") == "continue":
                            vm_continue = True
                    if not vm_continue:
                        ct = cell_text(tc, obj.part.document).strip().replace("\n", " | ")
                        cells.append(f"({ri},{ci}){ct}")
                    ci += span
                if cells:
                    print("   " + " || ".join(cells))
        n += 1
        if n >= limit:
            break


if __name__ == "__main__":
    main()
