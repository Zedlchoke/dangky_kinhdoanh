#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""row_placement.py — F3T detector ROW_PLACEMENT (D18_row_placement).

Defect được bắt (F3T.1, tái hiện tại HEAD): `_expand_loops` cũ chỉ thay hàng
marker và KHÔNG consume K hàng trắng preallocated đứng trước marker → DOCX
in K+N hàng theo pattern K-blank-then-data (4 trắng đứng TRƯỚC, dữ liệu nối
SAU). UI render.js thì đã đúng `max(rows.length, blankRows)`.

Hợp đồng kiểm (F3T.2) trên BẢNG LẶP CÓ K TRẮNG (blankRows của blocks):
  1. dữ liệu bắt đầu NGAY SAU header — không khối trắng chen giữa header và
     dòng dữ liệu 1 (kể cả hàng trắng nằm giữa hai dòng dữ liệu);
  2. tổng số hàng = header + max(K, N);
  3. STT liên tục 1..N trên dòng dữ liệu; hàng trắng phải có STT TRỐNG
     (không được "đánh STT cho hàng trắng");
  4. fixed-matrix/output-table KHÔNG bị áp (chỉ bảng khớp signature header
     của một loop trong registry blocks mới bị đếm hàng theo max(K,N); hai
     rule (1)/(3)-blank-STT vẫn chạy generic vì template HEAD quét 0/87 mẫu
     phi-loop có pattern này — verified census 47 loop / 26 form).

Hai lớp:
  - STRUCTURAL DOCX (authoritative, fail-loud): đọc word/document.xml, duyệt
    bảng cân bằng (bảng lồng được tách tầng — production 0 bảng lồng, đã
    quét 87 mẫu), mỗi bảng 3 rule BLANK_BEFORE_DATA / STT_ON_BLANK /
    STT_BREAK + rule ROW_COUNT_MISMATCH theo registry loop.
  - PDF (bổ trợ, chạy khi truyền `pages` có word coordinates — gate chỉ bật
    cho fixture valid-full nơi N>=1): chuỗi dòng STT 1,2,... (>=2 dòng, số
    tăng dần, token trái nhất thuần số ở lề trái) mà băng dọc KHÔNG CHỮ ngay
    phía trên dòng STT=1 cao quá ngưỡng → PDF_BLANK_GAP. N=0 (không có dòng
    STT) không bao giờ bị bắn — đó là case K trắng hợp pháp.

Codes:
  BLANK_BEFORE_DATA  — hàng trắng (kể cả hàng chỉ có STT) có hàng dữ liệu
                       phía dưới trong cùng bảng = blank chen trước/ giữa data.
  STT_ON_BLANK       — hàng trắng đuôi (sau dòng dữ liệu cuối) vẫn mang STT.
  STT_BREAK          — STT dòng dữ liệu không liên tục 1..N (đảo/thiếu/lặp).
  ROW_COUNT_MISMATCH — tổng hàng != header + max(K, N) theo mọi loop ứng viên
                       cùng signature header.
  PDF_BLANK_GAP      — (PDF) khoảng trắng dọc bất thường ngay trên dòng STT=1.

Registry loop xây từ blocks (`app/data/blocks/<fid>.json`, block t=loop có
blankRows) qua `load_loop_registry` — KHÔNG hard-code theo form.

Chạy độc lập (smoke tự dựng):  python3 -X utf8 -m tools.row_placement
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROW_RE = re.compile(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", re.S)
_INT_RE = re.compile(r"^\d{1,4}$")
_DRAWING_RE = re.compile(r"<w:drawing[ >]|<w:pict[ >]|<w:object[ >]")

# PDF: gap dọc (pt) trên dòng STT=1 vượt ngưỡng -> khối trắng chen trước data.
# Một hàng bảng ~14-18pt pitch; K=3 blank ~ 45-55pt. Ngưỡng 40pt bắt K>=3;
# K=4/5 của corpus (80-100pt) dư dả. DOCX structural mới là lớp authoritative
# bắt đủ mọi K — lớp PDF chỉ là belt-and-braces chống render lạ sau conversion.
PDF_GAP_MIN_PT = 40.0
# STT column nằm ở lề trái bảng (x0 < 110pt trên khổ A4 ~ 595pt).
PDF_STT_X0_MAX = 110.0


def fold_squeeze(text: str) -> str:
    """Chuẩn hoá text so khớp signature: bỏ TOÀN khoảng trắng."""
    return re.sub(r"\s+", "", text or "")


def load_loop_registry(blocks_doc) -> list[dict]:
    """Duyệt blocks doc (dict đã parse của app/data/blocks/<fid>.json): mọi
    block t=loop có blankRows -> entry {loop, k, header_rows, sig}.

    sig = text hàng header ĐẦU (rows[headerRows[0]], mặc định rows[0]) nối
    runs rồi fold_squeeze — khớp text hàng đầu tiên của bảng đã render."""
    out: list[dict] = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("t") == "loop" and x.get("blankRows"):
                rows = x.get("rows") or []
                hr = x.get("headerRows") or ([0] if rows else [])
                sig = ""
                if rows and hr:
                    ri = hr[0] if 0 <= hr[0] < len(rows) else 0
                    r0 = rows[ri]
                    sig = fold_squeeze("".join(
                        "".join((run or {}).get("text", "")
                                for run in (c.get("runs") or []))
                        for c in (r0.get("cells") or [])))
                out.append({
                    "loop": x.get("loop") or x.get("name"),
                    "k": int(x.get("blankRows") or 0),
                    "header_rows": max(1, len(hr)) if rows else 1,
                    "sig": sig,
                })
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(blocks_doc)
    return out


# ---------------------------------------------------------------------------
# DOCX structural
# ---------------------------------------------------------------------------

def _balanced_tbls(s: str):
    """(start, end) từng bảng cân bằng (bảng lồng nằm trong span bảng cha —
    chỉ tầng ngoài được yield, như det_table_grid)."""
    pos = 0
    while True:
        m = re.search(r"<w:tbl[ >]", s[pos:])
        if not m:
            return
        start = pos + m.start()
        depth = 1
        scan = pos + m.end()
        while depth:
            mm = re.search(r"<w:tbl[ >]|</w:tbl>", s[scan:])
            if not mm:
                return  # hỏng cấu trúc — bỏ phần còn lại
            depth += -1 if mm.group(0).startswith("</") else 1
            scan += mm.end()
        yield start, scan
        pos = scan


def _top_level_rows(seg: str) -> list[str]:
    """Các hàng tầng ngoài của span bảng (hàng chứa bảng lồng bị gộp —
    production đã quét 0/87 mẫu có bảng lồng trong hàng)."""
    rows: list[str] = []
    depth = 0
    for rm in ROW_RE.finditer(seg):
        r = rm.group(0)
        if depth == 0:
            rows.append(r)
        depth += (len(re.findall(r"<w:tbl[ >]", r))
                  - len(re.findall(r"</w:tbl>", r)))
    return rows


def _row_text(row: str) -> str:
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", row))


def _row_cells(row: str) -> list[str]:
    """Text đã squeeze của từng ô (w:tc) — ô merge dọc lặp lại text là chấp
    nhận được vì các rule chỉ cần 'trống/không trống' và ô STT đầu tiên."""
    cells = []
    for cm in re.finditer(r"<w:tc[ >].*?</w:tc>", row, re.S):
        cells.append(fold_squeeze(_row_text(cm.group(0))))
    return cells


def _row_is_blank(cells: list[str]) -> bool:
    """Hàng trắng theo hợp đồng F3T: MỌI ô trống, hoặc chỉ ô STT (đầu) mang
    một số thuần — hàng trắng bị 'đánh STT' vẫn là hàng trắng (và bị bắt
    riêng bằng STT_ON_BLANK khi nằm đuôi)."""
    non_empty = [c for c in cells if c]
    if not non_empty:
        return True
    return len(non_empty) == 1 and bool(_INT_RE.match(non_empty[0]))


def _stt_cell_empty(cells: list[str]) -> bool:
    """Ô STT (ô đầu) của hàng trắng phải trống."""
    return not (cells and _INT_RE.match(cells[0]))


def det_row_placement(docx_path, registry: list[dict] | None,
                      pages: list[dict] | None = None) -> list[dict]:
    """D18_row_placement: structural DOCX (+ PDF nếu có pages).

    registry: kết quả load_loop_registry(blocks_doc) của form; None/rỗng ->
    chỉ chạy 2 rule generic (BLANK_BEFORE_DATA, STT_ON_BLANK).
    Trả list issue dict {"table"/"page", "code", ...} — rỗng = PASS."""
    issues: list[dict] = []
    with zipfile.ZipFile(str(docx_path)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    sig_map: dict[str, list[dict]] = {}
    for e in registry or []:
        if e.get("sig"):
            sig_map.setdefault(e["sig"], []).append(e)

    for ti, (ts, te) in enumerate(_balanced_tbls(xml)):
        rows = _top_level_rows(xml[ts:te])
        if not rows:
            continue
        cells_per_row = [_row_cells(r) for r in rows]
        texts = [fold_squeeze("".join(cs)) for cs in cells_per_row]
        blank = [_row_is_blank(cs) for cs in cells_per_row]
        non_blank_idx = [i for i in range(len(rows)) if not blank[i]]
        if not non_blank_idx:
            continue  # bảng toàn trắng (không header) — không phải loop data
        first_nb, last_nb = non_blank_idx[0], non_blank_idx[-1]

        # (1) BLANK_BEFORE_DATA: hàng trắng có hàng dữ liệu phía dưới —
        # dữ liệu phải liền kề từ header, trắng chỉ được nằm đuôi.
        gaps = [i for i in range(first_nb, last_nb) if blank[i]]
        if gaps:
            issues.append({"table": ti, "code": "BLANK_BEFORE_DATA",
                           "blank_rows": [i + 1 for i in gaps],
                           "first_data_row": last_nb + 1})

        # (2) STT_ON_BLANK: hàng trắng đuôi (sau dòng dữ liệu cuối) không
        # được mang STT — "STT của hàng trắng để trống" (F3T.2.1).
        bad_stt = [i + 1 for i in range(last_nb + 1, len(rows))
                   if blank[i] and not _stt_cell_empty(cells_per_row[i])]
        if bad_stt:
            issues.append({"table": ti, "code": "STT_ON_BLANK",
                           "rows": bad_stt})

        # (3) STT_BREAK + (4) ROW_COUNT_MISMATCH: chỉ bảng khớp signature
        # header của một loop trong registry (loop-scoped, fixed-matrix/
        # output-table không bị áp). Thân bảng = sau đủ header_rows của
        # loop; hàng trắng lead trước header không bị đếm.
        sig = texts[first_nb]
        cands = sig_map.get(sig, [])
        if not cands:
            continue
        body_start = first_nb + min(c["header_rows"] for c in cands)
        data_idx = [i for i in range(body_start, len(rows)) if not blank[i]]
        stts = []
        for i in data_idx:
            cs = cells_per_row[i]
            if cs and _INT_RE.match(cs[0]):
                stts.append(int(cs[0]))
        if stts and stts != list(range(1, len(stts) + 1)):
            issues.append({"table": ti, "code": "STT_BREAK",
                           "stt": stts[:20]})
        matched = any(
            len(rows) == first_nb + c["header_rows"] + max(
                c["k"],
                len([i for i in range(first_nb + c["header_rows"],
                                      len(rows)) if not blank[i]]))
            for c in cands)
        if not matched:
            issues.append({
                "table": ti, "code": "ROW_COUNT_MISMATCH",
                "rows_total": len(rows),
                "expected_any": sorted({
                    first_nb + c["header_rows"] + max(
                        c["k"],
                        len([i for i in range(first_nb + c["header_rows"],
                                              len(rows)) if not blank[i]]))
                    for c in cands}),
                "n_data": len(data_idx),
                "loops": [c["loop"] for c in cands]})

    if pages:
        issues.extend(det_row_placement_pdf(pages))
    return issues


# ---------------------------------------------------------------------------
# PDF bổ trợ (cần word coordinates — gate.tranges valid-full)
# ---------------------------------------------------------------------------

def det_row_placement_pdf(pages: list[dict]) -> list[dict]:
    """Băng dọc KHÔNG CHỮ bất thường ngay trên dòng STT=1 của một chuỗi STT
    tăng dần (>=2 dòng) -> khối trắng chen giữa header và dòng dữ liệu đầu
    (pattern K-blank-then-data sống sót qua conversion). N=0 không có dòng
    STT nên không bao giờ bị bắn — K trắng hợp pháp."""
    hits: list[dict] = []
    for p in pages:
        words = p.get("words") or []
        if len(words) < 2:
            continue
        lines: dict[int, list[tuple]] = {}
        for w in words:
            key = int(round((w[1] + w[3]) / 2.0 / 3.0))  # bucket ~3pt
            lines.setdefault(key, []).append(w)
        ordered = sorted(lines.items(), key=lambda kv: kv[0])
        # chuẩn hoá: mỗi line = dict(words, y0, y1, x0_first)
        norm = []
        for _key, ws in ordered:
            ws = sorted(ws, key=lambda w: w[0])
            norm.append({"words": ws,
                         "y0": min(w[1] for w in ws),
                         "y1": max(w[3] for w in ws),
                         "x0": ws[0][0],
                         "first": ws[0][4]})
        i = 0
        while i < len(norm) - 1:
            ln = norm[i]
            if not _INT_RE.match(ln["first"]) or ln["first"] != "1" \
                    or ln["x0"] > PDF_STT_X0_MAX:
                i += 1
                continue
            # chuỗi STT tăng dần 1,2,... trên các line kề nhau
            run = [ln]
            expect = 2
            for j in range(i + 1, len(norm)):
                pj = norm[j]
                if _INT_RE.match(pj["first"]) and pj["first"] == str(expect) \
                        and pj["x0"] <= PDF_STT_X0_MAX \
                        and pj["y0"] - run[-1]["y1"] < 3.0 * max(
                            run[-1]["y1"] - run[-1]["y0"], 6.0):
                    run.append(pj)
                    expect += 1
                elif pj["y0"] > ln["y1"] + 3.0 * max(
                        ln["y1"] - ln["y0"], 6.0):
                    break
            if len(run) < 2:
                i += 1
                continue
            # line có chữ gần nhất PHÍA TRÊN run
            prev = None
            for j in range(i - 1, -1, -1):
                if norm[j]["words"]:
                    prev = norm[j]
                    break
            if prev is not None:
                lh = max(ln["y1"] - ln["y0"], 6.0)
                gap = ln["y0"] - prev["y1"]
                if gap > max(PDF_GAP_MIN_PT, 2.5 * lh):
                    hits.append({"page": p["pno"] + 1,
                                 "code": "PDF_BLANK_GAP",
                                 "gap_pt": round(gap, 1),
                                 "stt_run": len(run)})
                break  # một trang chỉ cần bắt lần đầu
            i += len(run)
    return hits


# ---------------------------------------------------------------------------
# Smoke tự dựng (không đụng production): python3 -X utf8 -m tools.row_placement
# ---------------------------------------------------------------------------

def _min_docx(path: Path, tables_xml: str) -> Path:
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>%s'
           "<w:sectPr/></w:body></w:document>" % tables_xml)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)
    return path


def _tbl(rows_cells: list[list[str]]) -> str:
    body = "".join(
        "<w:tr>%s</w:tr>" % "".join(
            "<w:tc><w:p><w:r><w:t>%s</w:t></w:r></w:p></w:tc>" % c
            for c in cells)
        for cells in rows_cells)
    return ("<w:tbl><w:tblPr/><w:tblGrid>"
            + "".join('<w:gridCol w:w="2000"/>' for _ in rows_cells[0])
            + "</w:tblGrid>" + body + "</w:tbl>")


REG = [{"loop": "ds_x", "k": 4, "header_rows": 1,
        "sig": fold_squeeze("STT Tên ngành Mã ngành")}]


def _smoke() -> int:
    tmp = Path("/tmp/f3t_row_placement_smoke")
    fails: list[str] = []

    def expect(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name,
              "" if cond else detail)
        if not cond:
            fails.append(name)

    # đúng (K=4, N=2): header + 2 data + 2 trắng
    good = _min_docx(tmp / "good.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["1", "Trồng lúa", "0111"],
        ["2", "Chăn nuôi", "0141"],
        ["", "", ""],
        ["", "", ""],
    ]))
    expect("good (4,2) pass", det_row_placement(good, REG) == [],
           det_row_placement(good, REG))
    # defect K+N: header + 4 trắng + 1 data
    bad = _min_docx(tmp / "bad.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["", "", ""], ["", "", ""], ["", "", ""], ["", "", ""],
        ["1", "Trồng lúa", "0111"],
    ]))
    hits = det_row_placement(bad, REG)
    codes = {h["code"] for h in hits}
    expect("K+N defect RED", {"BLANK_BEFORE_DATA", "ROW_COUNT_MISMATCH"}
           <= codes, hits)
    # mutation: blank giữa hai dòng dữ liệu
    mid = _min_docx(tmp / "mid.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["1", "Trồng lúa", "0111"],
        ["", "", ""],
        ["2", "Chăn nuôi", "0141"],
        ["", "", ""],
    ]))
    hits = det_row_placement(mid, REG)
    expect("blank giữa data RED", "BLANK_BEFORE_DATA" in
           {h["code"] for h in hits}, hits)
    # mutation: STT cho hàng trắng (đuôi)
    sttblank = _min_docx(tmp / "sttblank.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["1", "Trồng lúa", "0111"],
        ["2", "", ""],
        ["3", "", ""],
    ]))
    hits = det_row_placement(sttblank, REG)
    expect("STT trên hàng trắng RED",
           "STT_ON_BLANK" in {h["code"] for h in hits}, hits)
    # mutation: STT đảo thứ tự
    swap = _min_docx(tmp / "swap.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["2", "Chăn nuôi", "0141"],
        ["1", "Trồng lúa", "0111"],
        ["", "", ""], ["", "", ""],
    ]))
    hits = det_row_placement(swap, REG)
    expect("STT đảo thứ tự RED", "STT_BREAK" in {h["code"] for h in hits},
           hits)
    # N=0: header + 4 trắng -> PASS
    empty = _min_docx(tmp / "empty.docx", _tbl([
        ["STT", "Tên ngành", "Mã ngành"],
        ["", "", ""], ["", "", ""], ["", "", ""], ["", "", ""],
    ]))
    expect("N=0 giữ K trắng pass", det_row_placement(empty, REG) == [],
           det_row_placement(empty, REG))
    # fixed-matrix không có trong registry: blank-generic vẫn bắt, count không
    fixed = _min_docx(tmp / "fixed.docx", _tbl([
        ["Loại vốn", "Số tiền"],
        ["", ""],
        ["NSNN", "100"],
    ]))
    hits = det_row_placement(fixed, REG)
    expect("bảng lạ: blank chen vẫn RED generic",
           "BLANK_BEFORE_DATA" in {h["code"] for h in hits}, hits)

    # PDF: gap lớn trên STT=1 -> RED; gap thường -> PASS
    def _pdf_pages(path, rows_y):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        for y, txt in rows_y:
            page.insert_text((50, y), txt)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(path))
        doc.close()
        d2 = fitz.open(str(path))
        return [{"pno": p.number, "text": p.get_text("text"),
                 "words": p.get_text("words")} for p in d2]

    bad_pdf = _pdf_pages(tmp / "bad.pdf", [
        (700, "STT Ten nganh Ma nganh"),
        (790, "1 0111 Trong lua"),
        (808, "2 0141 Chan nuoi"),
    ])
    hits = det_row_placement_pdf(bad_pdf)
    expect("PDF gap 90pt RED", len(hits) == 1 and
           hits[0]["code"] == "PDF_BLANK_GAP", hits)
    good_pdf = _pdf_pages(tmp / "good.pdf", [
        (700, "STT Ten nganh Ma nganh"),
        (718, "1 0111 Trong lua"),
        (736, "2 0141 Chan nuoi"),
    ])
    expect("PDF gap thường pass", det_row_placement_pdf(good_pdf) == [],
           det_row_placement_pdf(good_pdf))

    print("-" * 60)
    print("row_placement smoke: %s" % ("FAIL %d" % len(fails) if fails
                                       else "ALL PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(_smoke())
