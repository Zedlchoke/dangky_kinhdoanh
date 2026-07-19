#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FULL_DOCX = ROOT / "00_nguon_goc" / "Bieu_mau_PL_I_II_full.docx"
CATALOG = ROOT / "99_muc_luc" / "muc_luc_bieu_mau.csv"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)


def paragraph_text(p: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(t.text or "" for t in p.findall(".//w:t", NS))).strip()


def read_docx_body(path: Path) -> tuple[ET.Element, list[ET.Element], bytes]:
    with zipfile.ZipFile(path) as z:
        document_xml = z.read("word/document.xml")
    root = ET.fromstring(document_xml)
    body = root.find("w:body", NS)
    if body is None:
        raise ValueError(f"missing body: {path}")
    return root, list(body), document_xml


def detect_starts(paragraphs: list[ET.Element]) -> dict[tuple[str, int], int]:
    starts: dict[tuple[str, int], int] = {}
    for idx, p in enumerate(paragraphs):
        text = paragraph_text(p)
        m = re.search(r"Mẫu số\s+(\d+)\s*$", text)
        if not m:
            continue
        num = int(m.group(1))
        if idx < 166:
            continue
        if idx < 5590:
            pl = "PL1"
        elif idx >= 5648:
            pl = "PL2"
        else:
            continue
        starts.setdefault((pl, num), idx)
    return starts


def appendix_end(pl: str, paragraphs: list[ET.Element]) -> int:
    if pl == "PL1":
        for idx, p in enumerate(paragraphs):
            if idx > 5550 and paragraph_text(p) == "Mẫu số 1":
                return idx
    return len(paragraphs)


def catalog_paths() -> dict[tuple[str, int], list[Path]]:
    paths: dict[tuple[str, int], list[Path]] = {}
    for path in sorted(ROOT.glob("**/PL*_Mau_*.docx")):
        if "generated_ho_so" in path.parts or "my_test" in path.parts or "00_nguon_goc" in path.parts:
            continue
        m = re.search(r"(PL[12])_Mau_(\d+)", path.name)
        if not m:
            continue
        key = (m.group(1), int(m.group(2)))
        paths.setdefault(key, []).append(path)
    return paths


def catalog_titles() -> dict[tuple[str, int], str]:
    out: dict[tuple[str, int], str] = {}
    with CATALOG.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pl = "PL2" if "II" in row["phu_luc"] else "PL1"
            out[(pl, int(row["mau_so"]))] = row["ten_mau"]
    return out


def count_nonempty(path: Path) -> int:
    root, body, _ = read_docx_body(path)
    return sum(1 for p in root.findall(".//w:p", NS) if paragraph_text(p))


def rebuild_one(full_root: ET.Element, full_body_children: list[ET.Element], template_path: Path, start: int, end: int) -> None:
    out_root = deepcopy(full_root)
    out_body = out_root.find("w:body", NS)
    if out_body is None:
        raise ValueError("missing output body")
    sect_pr = None
    for child in list(out_body):
        if child.tag == f"{{{W_NS}}}sectPr":
            sect_pr = deepcopy(child)
        out_body.remove(child)
    for child in full_body_children[start:end]:
        if child.tag != f"{{{W_NS}}}sectPr":
            out_body.append(deepcopy(child))
    if sect_pr is not None:
        out_body.append(sect_pr)
    rendered = ET.tostring(out_root, encoding="utf-8", xml_declaration=True)
    backup = template_path.with_suffix(template_path.suffix + ".bak_before_full_rebuild")
    if not backup.exists():
        shutil.copy2(template_path, backup)
    tmp = template_path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(FULL_DOCX) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = rendered if item.filename == "word/document.xml" else zin.read(item.filename)
            zout.writestr(item, data)
    tmp.replace(template_path)


def backup_path(template_path: Path) -> Path:
    return template_path.with_suffix(template_path.suffix + ".bak_before_full_rebuild")


def main() -> None:
    full_root, body_children, _ = read_docx_body(FULL_DOCX)
    paragraph_indices = [idx for idx, child in enumerate(body_children) if child.tag == f"{{{W_NS}}}p"]
    body_index_by_para_index = {para_idx: body_idx for body_idx, para_idx in enumerate(paragraph_indices)}
    paragraphs = [body_children[idx] for idx in paragraph_indices]
    starts = detect_starts(paragraphs)
    paths = catalog_paths()
    titles = catalog_titles()
    report = []
    by_pl: dict[str, list[tuple[int, int]]] = {"PL1": [], "PL2": []}
    for (pl, num), para_start in starts.items():
        by_pl[pl].append((num, para_start))
    for pl in by_pl:
        by_pl[pl].sort()
    next_start: dict[tuple[str, int], int] = {}
    for pl, items in by_pl.items():
        pl_end = appendix_end(pl, paragraphs)
        for idx, (num, para_start) in enumerate(items):
            next_start[(pl, num)] = items[idx + 1][1] if idx + 1 < len(items) else pl_end

    for key, path_list in sorted(paths.items()):
        for path in path_list:
            if key not in starts or key not in next_start:
                report.append({"id": f"{key[0]}_{key[1]}", "path": str(path.relative_to(ROOT)), "status": "missing_start"})
                continue
            old_count = count_nonempty(path)
            para_start = starts[key]
            para_end = next_start[key]
            body_start = body_index_by_para_index[para_start]
            body_end = body_index_by_para_index.get(para_end, len(body_children))
            source_count = sum(1 for p in paragraphs[para_start:para_end] if paragraph_text(p))
            backup = backup_path(path)
            if source_count == 0 and backup.exists():
                shutil.copy2(backup, path)
                status = "restored_backup_zero_source"
                new_count = count_nonempty(path)
            elif source_count > 0 and (source_count > old_count + 5 or old_count <= 5 or old_count > source_count * 3):
                rebuild_one(full_root, body_children, path, body_start, body_end)
                status = "rebuilt"
                new_count = count_nonempty(path)
            else:
                status = "kept"
                new_count = old_count
            report.append(
                {
                    "id": f"{key[0]}_{key[1]}",
                    "title": titles.get(key, ""),
                    "path": str(path.relative_to(ROOT)),
                    "old_nonempty": old_count,
                    "source_nonempty": source_count,
                    "new_nonempty": new_count,
                    "status": status,
                }
            )
    out = ROOT / "generated_ho_so" / "TEMPLATE_REBUILD_REPORT.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rebuilt": sum(1 for x in report if x["status"] == "rebuilt"), "report": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
