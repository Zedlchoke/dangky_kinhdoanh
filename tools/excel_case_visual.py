# -*- coding: utf-8 -*-
"""Bằng chứng TRỰC QUAN bố cục workbook Excel CASE-LEVEL (PLAN §5-E3 — visual).

Với MỖI case READY (hoặc `--cases id1,id2`):
  1. `write_case_workbook` -> workbook gốc (meta ngày chạy).
  2. soffice headless --convert-to pdf (profile cách ly `lo_prof_visual_*`)
     -> 1 PDF chứa các sheet HIỂN thị (sheet ẩn veryHidden/hidden không in).
  3. pymupdf render từng trang PNG ~150dpi + contact sheet ghép (PIL).
  4. Kiểm TỰ ĐỘNG những gì text-layer PDF cho phép:
       - cắt cột / chữ bị clip: chuỗi nội dung ô (nhãn câu, guide, meta…)
         phải tìm thấy NGUYÊN VĂN (bỏ khoảng trắng để bao quả wrapped text)
         trong text-layer của ít nhất một trang;
       - tràn trang: ánh xạ trang PDF -> sheet qua dòng tiêu đề hàng 1;
       - tiếng Việt lỗi font: chuỗi tìm thấy phải đúng dấu (so exact), text
         layer không chứa U+FFFD; tofu (ô vuông) KHÔNG tự chẩn đoán được ->
         chuyển mục MANUAL cho người xem mắt;
       - số hàng bảng: cấu trúc map (layout=table) phải đủ `REPEAT_ROWS`
         hàng dữ liệu cho từng cột bảng.
  5. Sinh `docs/audits/excel_case_visual_<date>.md` — bảng PASS/WARN từng
     mục + ghi rõ cái nào CẦN NGƯỜI NHÌN MẮT (zoom 100%/125% trên Excel
     thật) = MANUAL NOT RUN.

Case PENDING (chưa có câu hỏi — lane content sở hữu) bị BỎ QUA, ghi NOT RUN.
Chạy lại được sau khi lane kia bật đủ 28 case:
  python3 -X utf8 -m tools.excel_case_visual
  python3 -X utf8 -m tools.excel_case_visual --cases id1,id2

Exit 0 khi mọi case chạy được và không có mục FAIL (WARN không fail);
exit 1 khi có FAIL (mất PDF, mất chuỗi ở mức nghiêm trọng, sai số hàng bảng).
Bằng chứng lưu `generated_ho_so/_visual_layout/excel_case_<date>/`
(ngoài git theo gitignore của `generated_ho_so/`).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402
from PIL import Image  # noqa: E402

from tools.excel_case_export import (  # noqa: E402
    DOCS_SHEET, GUIDE_SHEET, COMMON_SHEET, MAP_COLUMNS, MAP_SHEET,
    workbook_stem, write_case_workbook,
)
from tools.excel_export import REPEAT_ROWS  # noqa: E402
from tools.questionnaire.schema import DATE_NOTE, EXAMPLE_PREFIX, SELECT_NOTE  # noqa: E402

SOFFICE = "/opt/homebrew/bin/soffice"
DPI = 150
ZOOM = DPI / 72.0
THUMB_WIDTH = 380          # contact sheet
THUMB_COLS_MAX = 4

AUDIT_DATE = "2026-09-10"
OUT_BASE = ROOT / "generated_ho_so" / "_visual_layout" / "excel_case_20260910"
AUDIT_MD = ROOT / "docs" / "audits" / ("excel_case_visual_%s.md" % AUDIT_DATE)

META = {
    "today": datetime.now().strftime("%d/%m/%Y"),
    "exported_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _manifest(case_id: str) -> dict:
    """ĐỌC manifest TỪ ĐĨA lúc chạy (lane content có thể vừa bật case)."""
    return json.loads(
        (ROOT / "app" / "data" / "case_questionnaires" / ("%s.json" % case_id))
        .read_text(encoding="utf-8"))


def _case_is_ready(manifest: dict) -> bool:
    # [E5 2026-09-10] đồng bộ ngữ nghĩa "đã duyệt" với exporter/importer:
    # approved HOẶC owner_delegated (APPROVED_EQUIV) đều đếm là READY.
    try:
        from tools.excel_case_export import is_review_approved
    except Exception:  # noqa: BLE001 — fallback cũ nếu helper chưa tồn tại
        return any(f.get("content_review") == "approved" and f.get("questions")
                   for f in manifest.get("forms", []))
    return any(is_review_approved(f.get("content_review")) and f.get("questions")
               for f in manifest.get("forms", []))


def _squash(text: str) -> str:
    """Bỏ MỌI khoảng trắng — bao được text bị wrap nhiều dòng trong PDF."""
    return "".join(text.split())


def _fold(text: str) -> str:
    """Chuẩn hoá mạnh để so text-layer PDF: NFD bỏ dấu combining, đ->d,
    chỉ giữ [a-z0-9]. LibreOffice xuất PDF với font thay thế (Caladea) làm
    MỘT SỐ glyph tiếng Việt (ộ, ớ, ơ…) bị DỊCH VỊ TRÍ — base letter ở chỗ
    khác thứ tự gốc, nên so THẲNG fail ảo; fold chỉ giữ bộ ký tự lõi.
    """
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _bag(text: str) -> Counter:
    return Counter(_fold(text))


def _expected_strings(manifest: dict, wb) -> list[str]:
    """Chuỗi đáng lẽ HIỆN trên các sheet nhìn thấy — dùng đối chiếu PDF."""
    out: set[str] = set()

    def add(s):
        if s and _squash(s):
            out.add(_squash(str(s)))

    add(manifest["case_title"])
    hash8 = str(manifest["manifest_hash"])[:8]
    add("Hồ sơ: %s (%s) — Mã phiếu: %s — Ngày lập: %s" % (
        manifest["case_title"], manifest["case_id"], hash8, META["today"]))
    from tools.excel_case_export import GUIDE_LINES  # noqa: C0415
    for line in GUIDE_LINES:
        add("• " + line)
        add(line)
    add("Các mẫu trong phiếu này:")
    add("Thông tin dùng chung cho cả hồ sơ")
    for form in manifest.get("forms", []):
        if form.get("content_review") != "approved":
            add(form.get("form_id"))     # tên form pending liệt kê ở Hướng_dẫn
            continue
        add(form.get("title") or form.get("ten_mau"))
        for q in form.get("questions", []):
            add(q.get("group"))
            add(q.get("text"))
            if q.get("example"):
                add(EXAMPLE_PREFIX + str(q["example"]))
            elif q.get("type") == "select":
                add(SELECT_NOTE)
            if q.get("type") == "date":
                add(DATE_NOTE)
            # CHÚ Ý: option labels KHÔNG đưa vào — chúng chỉ nằm trong sheet
            # ẩn __lists/dropdown, không bao giờ render trên sheet nhìn thấy.
    add("DANH MỤC GIẤY TỜ CHỜ DUYỆT")
    add("Danh mục giấy tờ (THAM KHẢO — CHƯA DUYỆT):")
    for item in manifest.get("giay_to_kem") or []:
        add("[chưa duyệt] %s" % item)
    return sorted(out)


def _reconstruct_page_text(page) -> str:
    """Tái lập thứ tự đọc của text-layer MỘT trang.

    LibreOffice xuất glyph tiếng Việt tổ hợp (ả, ồ, ơ, ộ…) trong các text-run
    RIÊNG lệch baseline ~0.5-1pt, nên `get_text("text")` thường cho thứ tự sai
    (chữ màu mè cuối dòng). Gom ký tự theo CỤM y (dung sai 3pt) rồi sort theo
    x trong từng cụm -> tái lập đúng thứ tự đọc.
    """
    raw = page.get_text("rawdict")
    chars: list[tuple[float, float, str]] = []
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for ch in span.get("chars", []):
                    chars.append((ch["bbox"][1], ch["bbox"][0], ch["c"]))
    chars.sort(key=lambda t: (t[0], t[1]))
    lines_out: list[str] = []
    cur: list[tuple[float, str]] = []
    cur_y: float | None = None
    for y, x, c in chars:
        if cur_y is None or abs(y - cur_y) <= 3.0:
            cur.append((x, c))
            if cur_y is None:
                cur_y = y
        else:
            cur.sort(key=lambda t: t[0])
            lines_out.append("".join(c for _, c in cur))
            cur = [(x, c)]
            cur_y = y
    if cur:
        cur.sort(key=lambda t: t[0])
        lines_out.append("".join(c for _, c in cur))
    return "\n".join(lines_out)


def _pdf_page_geometry(pdf_path) -> tuple[list[int], list[float], list[float]]:
    """Số "word" + max_x + bề ngang của từng trang PDF (phục vụ dò dải mỏng)."""
    doc = pymupdf.open(str(pdf_path))
    try:
        words: list[int] = []
        max_xs: list[float] = []
        widths: list[float] = []
        for page in doc:
            w = page.get_text("words")
            words.append(len(w))
            max_xs.append(max((t[2] for t in w), default=0.0))
            widths.append(float(page.rect.width))
        return words, max_xs, widths
    finally:
        doc.close()


def _pdf_pages(pdf_path: Path) -> list[str]:
    """Text-layer từng trang (thứ tự) — đã tái lập thứ tự đọc + squash."""
    doc = pymupdf.open(str(pdf_path))
    try:
        return [_squash(_reconstruct_page_text(page)) for page in doc]
    finally:
        doc.close()


def _pdf_fonts(pdf_path: Path) -> list[str]:
    doc = pymupdf.open(str(pdf_path))
    try:
        names: set[str] = set()
        for page in doc:
            for f in page.get_fonts():
                names.add(str(f[3]))
        return sorted(names)
    finally:
        doc.close()


def _sheet_title_candidates(manifest: dict) -> dict[str, list[str]]:
    """Chuỗi nhận diện sheet trong text PDF (hàng 1/tiêu đề từng sheet)."""
    out: dict[str, list[str]] = {
        GUIDE_SHEET: [_squash(manifest["case_title"]),
                      _squash("Các mẫu trong phiếu này:")],
        COMMON_SHEET: [_squash("Thông tin dùng chung cho cả hồ sơ")],
        # [E4 2026-09-10] tiêu đề docs sheet đổi sau khi bỏ "CHỜ DUYỆT"
        DOCS_SHEET: [_squash("GIẤY TỜ CẦN CHUẨN BỊ NỘP KÈM")],
    }
    idx = 0
    from tools.excel_case_export import is_review_approved  # noqa: C0415
    for form in manifest.get("forms", []):
        if not is_review_approved(form.get("content_review")):
            continue
        idx += 1
        from tools.excel_case_export import sheet_display_name  # noqa: C0415
        title = str(form.get("title") or form.get("ten_mau") or "")
        out[sheet_display_name(idx, form)] = [_squash(title)] if title else []
    return out


def _map_pages_to_sheets(page_texts: list[str],
                         title_map: dict[str, list[str]],
                         sheet_order: list[str]) -> dict[str, int | None]:
    """Trang ĐẦU TIÊN của từng sheet (tham khảo — LibreOffice glyph dịch vị
    làm so THẲNG không đáng tin): ưu tiên khớp fold liên tiếp, fallback là
    trang có độ phủ bag ký tự của tiêu đề cao nhất; enforcing thứ tự sheet.

    Trả {sheet: index trang đầu | None}.
    """
    page_folds = [_fold(p) for p in page_texts]
    page_bags = [_bag(p) for p in page_texts]
    starts: dict[str, int | None] = {}
    cursor = 0
    for sheet in sheet_order:
        chosen: int | None = None
        # 1) fold liên tiếp từ vị trí cursor
        for t in title_map.get(sheet, []):
            ft = _fold(t)
            if not ft:
                continue
            for i in range(cursor, len(page_folds)):
                if ft in page_folds[i]:
                    chosen = i
                    break
            if chosen is not None:
                break
        # 2) coverage bag cao nhất từ cursor (>= 0.5), ưu tiên trang sớm
        if chosen is None:
            best = 0.0
            for t in title_map.get(sheet, []):
                tb = _bag(t)
                need = sum(tb.values())
                if not need:
                    continue
                for i in range(cursor, len(page_bags)):
                    covered = sum(min(c, page_bags[i].get(ch, 0))
                                  for ch, c in tb.items()) / need
                    if covered > best + 1e-9:
                        best = covered
                        chosen = i
            if best < 0.5:
                chosen = None
        if chosen is None:
            starts[sheet] = None
            continue
        starts[sheet] = chosen
        cursor = chosen + 1
    return starts


def _table_row_counts(wb) -> dict[str, int]:
    """Số hàng dữ liệu bảng (layout=table) theo cột map — so REPEAT_ROWS.

    Mỗi ô của bảng N hàng có N dòng map (một ô một dòng) -> đếm dòng map
    theo question_id rồi so với REPEAT_ROWS.
    """
    mp = wb[MAP_SHEET]
    col = {mp.cell(3, i + 1).value: i + 1 for i in range(len(MAP_COLUMNS))}
    exact: dict[str, int] = {}
    for r in range(4, mp.max_row + 1):
        if (mp.cell(r, col["layout"]).value or "") != "table":
            continue
        qid = mp.cell(r, col["question_id"]).value
        exact[qid] = exact.get(qid, 0) + 1
    return exact


def _contact_sheet(pngs: list[Path], out_path: Path) -> None:
    thumbs = []
    for p in pngs:
        img = Image.open(p)
        ratio = THUMB_WIDTH / img.width
        img = img.resize((THUMB_WIDTH, max(1, int(img.height * ratio))))
        thumbs.append(img)
    rows = (len(thumbs) + THUMB_COLS_MAX - 1) // THUMB_COLS_MAX
    row_heights = []
    for r in range(rows):
        row = thumbs[r * THUMB_COLS_MAX:(r + 1) * THUMB_COLS_MAX]
        row_heights.append(max(t.height for t in row))
    gap = 12
    w = THUMB_COLS_MAX * THUMB_WIDTH + (THUMB_COLS_MAX + 1) * gap
    h = sum(row_heights) + (rows + 1) * gap
    sheet = Image.new("RGB", (w, h), "white")
    y = gap
    for r in range(rows):
        x = gap
        for t in thumbs[r * THUMB_COLS_MAX:(r + 1) * THUMB_COLS_MAX]:
            sheet.paste(t, (x, y))
            x += THUMB_WIDTH + gap
        y += row_heights[r] + gap
    sheet.save(out_path)


# ---------------------------------------------------------------------------
# chạy 1 case
# ---------------------------------------------------------------------------

def run_case(case_id: str) -> dict:
    """Trả báo cáo dict cho 1 case; bằng chứng rơi vào OUT_BASE/<caseId>/."""
    manifest = _manifest(case_id)
    report: dict = {
        "case_id": case_id, "status": "RUN", "sheets": 0, "pages": 0,
        "clip_missing": [], "clip_scrambled": [], "diacritic_loss": [],
        "n_exact": 0, "n_expected_strings": 0, "diacritic_loss_ratio": 0.0,
        "fonts": [], "pages_per_sheet": {},
        "table_rows_ok": True, "table_rows_detail": {},
        "verdicts": {}, "notes": [],
    }
    case_dir = OUT_BASE / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    wb_path = write_case_workbook(
        manifest, case_dir / ("%s.xlsx" % workbook_stem(manifest)), meta=META)
    import openpyxl  # noqa: C0415
    wb = openpyxl.load_workbook(wb_path)
    visible = [s for s in wb.sheetnames
               if wb[s].sheet_state in ("visible", "hidden")]
    report["sheets"] = len(wb.sheetnames)
    report["hidden_sheets"] = [s for s in wb.sheetnames if s not in visible]

    # bảng lặp đủ REPEAT_ROWS hàng (structural — từ `__map`)
    rows_by_q = _table_row_counts(wb)
    bad = {q: n for q, n in rows_by_q.items() if n != REPEAT_ROWS}
    report["table_rows_detail"] = {
        "n_table_cols": len(rows_by_q), "rows_each": REPEAT_ROWS}
    report["table_rows_ok"] = not bad
    if bad:
        report["notes"].append("bảng lệch REPEAT_ROWS: %s" % bad)

    # Calc -> PDF (profile cách ly)
    profile = "file:///tmp/lo_prof_visual_%d_%s" % (os.getpid(),
                                                    case_id[:16])
    tmp_out = case_dir
    proc = subprocess.run(
        [SOFFICE, "--headless", "--norestore", "--convert-to", "pdf",
         "--outdir", str(tmp_out), "-env:UserInstallation=%s" % profile,
         str(wb_path)],
        capture_output=True, text=True, timeout=600)
    pdf_path = tmp_out / (wb_path.stem + ".pdf")
    if proc.returncode != 0 or not pdf_path.exists():
        report["status"] = "FAIL"
        report["notes"].append("soffice pdf rc=%s file=%s" % (
            proc.returncode, pdf_path.exists()))
        report["verdicts"] = {"export_pdf": "FAIL"}
        return report

    # render PNG từng trang + contact sheet
    doc = pymupdf.open(str(pdf_path))
    pngs: list[Path] = []
    try:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM))
            png = case_dir / ("page-%02d.png" % i)
            pix.save(str(png))
            pngs.append(png)
    finally:
        doc.close()
    if pngs:
        _contact_sheet(pngs, case_dir / "contact-sheet.png")
    report["pages"] = len(pngs)
    report["pdf"] = str(pdf_path.relative_to(ROOT))
    report["evidence_dir"] = str(case_dir.relative_to(ROOT))

    page_texts = _pdf_pages(pdf_path)
    report["fonts"] = _pdf_fonts(pdf_path)
    doc_sq = "\n".join(page_texts)
    doc_fold = _fold(doc_sq)
    doc_bag = _bag(doc_sq)
    report["verdicts"]["export_pdf"] = "PASS"

    # ---- cắt cột / clip: 4 tầng khớp giữa nội dung ô và text-layer PDF
    #  tier1 exact       : nguyên văn (NFC, bỏ wrap)          -> sạch
    #  tier2 fold        : đúng chữ, SAI KHÔNG DẤU            -> mất dấu font
    #  tier3 bag         : đủ bộ ký tự nhưng không liên tiếp  -> wrap/xen kẽ
    #                      cột hoặc glyph dịch vị — chữ CÓ in
    #  tier4 char_missing: thiếu hẳn ký tự -> nghi cắt cột/clip/font rớt
    expected = [s for s in _expected_strings(manifest, wb)]
    report["n_expected_strings"] = len(expected)
    diacritic_loss: list[str] = []
    bag_only: list[str] = []
    char_missing: list[str] = []
    n_exact = 0
    for s in expected:
        if s in doc_sq:
            n_exact += 1
            continue
        if _fold(s) in doc_fold:
            diacritic_loss.append(s)
            continue
        gap = _bag(s) - doc_bag
        if gap:
            char_missing.append("%s (thiếu: %s)" % (
                s[:80], "".join(sorted(gap.elements()))[:40]))
        else:
            bag_only.append(s)
    report["n_exact"] = n_exact
    report["diacritic_loss"] = diacritic_loss
    report["clip_scrambled"] = bag_only          # tier3 — layout interleave
    report["clip_missing"] = char_missing        # tier4 — clip thật
    frac_missing = (len(char_missing) / len(expected)) if expected else 0.0
    if frac_missing == 0:
        report["verdicts"]["column_clip"] = "PASS"
    elif frac_missing <= 0.2:
        report["verdicts"]["column_clip"] = "WARN"
    else:
        report["verdicts"]["column_clip"] = "FAIL"

    # ---- tràn trang: trang đầu của từng sheet + dò "dải mỏng" (tràn NGANG)
    # [fitToWidth 2026-09-10 — owner chốt] exporter đã ghi fitToWidth=1 +
    # pageSetUpPr.fitToPage cho mọi sheet công khai, nên LibreOffice co MỌI
    # cột vào một trang ngang (đo được: case hộ KD 11→5 trang, max_x <=94%).
    # Số trang > số sheet giờ là chia trang DỌC hợp lệ (fitToHeight=0),
    # KHÔNG còn là overflow. Dấu hiệu tràn ngang còn lại là trang "dải mỏng":
    # rất ít chữ VÀ dùng dưới 45% bề ngang — triệu chứng cột phải rơi riêng.
    sheet_order = [s for s in wb.sheetnames
                   if s not in report["hidden_sheets"]]
    first_pages = _map_pages_to_sheets(page_texts,
                                       _sheet_title_candidates(manifest),
                                       sheet_order)
    report["pages_per_sheet"] = {k: v for k, v in first_pages.items()}
    unresolved = [s for s, p in first_pages.items() if p is None]
    page_words, page_max_x, page_w = _pdf_page_geometry(pdf_path)
    # Trang words==0: LibreOffice không trích được text-layer (artifact font
    # đã ghi ở vietnamese_font) — ghi note, KHÔNG coi là dải mỏng.
    empty_pages = [i + 1 for i, n in enumerate(page_words) if n == 0]
    thin_strips = [i + 1 for i in range(len(page_texts))
                   if 0 < page_words[i] < 30
                   and (page_max_x[i] / page_w[i] if page_w[i] else 0) < 0.45]
    report["page_geometry"] = {
        "words_per_page": page_words,
        "width_usage": [round(x / w, 2) if w else 0
                        for x, w in zip(page_max_x, page_w)]}
    # [fitToWidth 2026-09-10] `unresolved` chỉ là THAM KHẢO: dò trang đầu sheet
    # qua text-layer không đáng tin khi LibreOffice mất nét Việt (xem
    # vietnamese_font + docstring _map_pages_to_sheets) — không phải evidence
    # overflow. Verdict chỉ WARN khi có dải mỏng thật (nghi tràn ngang).
    if unresolved:
        report["notes"].append(
            "tham khảo — không dò được trang đầu của sheet qua text-layer "
            "(mất nét Việt của LibreOffice): %s" % unresolved)
    if empty_pages:
        report["notes"].append(
            "trang không trích được text-layer (artifact LibreOffice): p%s"
            % empty_pages)
    if thin_strips:
        report["verdicts"]["page_overflow"] = "WARN"
        report["notes"].append(
            "trang 'dải mỏng' p%s — nghi tràn cột ngang (rất ít chữ, "
            "dùng <45%% bề ngang)" % thin_strips)
    else:
        report["verdicts"]["page_overflow"] = "PASS"

    # ---- tiếng Việt lỗi font: U+FFFD + tỉ lệ chuỗi MẤT DẤU trong text-layer
    has_replacement = "\ufffd" in doc_sq
    frac_diac = (len(diacritic_loss) / len(expected)) if expected else 0.0
    report["diacritic_loss_ratio"] = round(frac_diac, 3)
    if has_replacement or frac_diac > 0.5:
        report["verdicts"]["vietnamese_font"] = "FAIL"
        report["notes"].append(
            "text-layer mất dấu ở %.0f%% chuỗi%s — font lỗi"
            % (frac_diac * 100,
               " hoặc có U+FFFD" if has_replacement else ""))
    elif diacritic_loss or frac_diac:
        report["verdicts"]["vietnamese_font"] = "WARN"
        report["notes"].append(
            "%d/%d chuỗi đủ chữ nhưng thiếu dấu trong text-layer (font thay thế "
            "LibreOffice) — cần xem mắt trên Excel thật" % (
                len(diacritic_loss), len(expected)))
    else:
        report["verdicts"]["vietnamese_font"] = "PASS"
    report["verdicts"]["table_rows"] = \
        "PASS" if report["table_rows_ok"] else "FAIL"
    report["verdicts"]["manual_eyes"] = "MANUAL NOT RUN"
    return report


# ---------------------------------------------------------------------------
# audit markdown
# ---------------------------------------------------------------------------

def _write_audit(reports: list[dict], not_run: list[tuple[str, str]]) -> None:
    lines: list[str] = []
    a = lines.append
    a("# Audit bố cục trực quan — Excel case-level (%s)" % AUDIT_DATE)
    a("")
    a("- HEAD: `%s` — tool: `tools/excel_case_visual.py`" %
      _git_head())
    a("- LibreOffice: `%s` — render: pymupdf %s (PNG ~%ddpi)"
      % (_soffice_version(), _pymupdf_version(), DPI))
    a("- Meta xuất: `%s`" % json.dumps(META, ensure_ascii=False))
    a("- Bằng chứng: `%s/<caseId>/` "
      "(`page-NN.png`, `contact-sheet.png`, `*.pdf`, `*.xlsx`)" % OUT_BASE.relative_to(ROOT))
    a("- Phạm vi: case READY đọc từ đĩa lúc chạy. Case PENDING (chưa có câu "
      "hỏi) = NOT RUN, chờ lane content bật.")
    a("")
    a("## Bảng tổng hợp")
    a("")
    a("| case | sheet | trang PDF | cắt cột / clip | tràn trang | font tiếng Việt | số hàng bảng |")
    a("|---|---|---|---|---|---|---|")
    for r in reports:
        if r["status"] != "RUN":
            a("| %s | — | — | — | — | — | %s |" % (r["case_id"],
                                                   r["status"]))
            continue
        v = r["verdicts"]
        clip = v.get("column_clip", "?")
        clip_detail = ""
        if clip != "PASS":
            clip_detail = " (%d/%d chuỗi thiếu ký tự)" % (
                len(r["clip_missing"]), r.get("n_expected_strings", 0))
        overflow = v.get("page_overflow", "?")
        if overflow == "WARN" and r.get("pages_per_sheet"):
            overflow += " (spill %d trang; trang đầu: %s)" % (
                r["pages"] - (r["sheets"] - len(r.get("hidden_sheets", []))),
                json.dumps(r["pages_per_sheet"], ensure_ascii=False))
        a("| %s | %d | %d | %s%s | %s | %s | %s |" % (
            r["case_id"], r["sheets"], r["pages"], clip, clip_detail,
            overflow, v.get("vietnamese_font", "?"),
            v.get("table_rows", "?")))
    a("")
    a("Chi tiết `pages_per_sheet` (trang đầu chứa TOÀN VĂN tiêu đề sheet — "
      "dò qua text-layer, tham khảo). LƯU Ý: với sheet rộng hơn khổ giấy, "
      "tiêu đề hàng 1 có thể bị CẮT tại mép phải trang thật (vd "
      "`tam_ngung_tiep_tuc_kinh_doanh_hkd`: tiêu đề guide dừng ở \"…hộ kinh "
      "doa\") — khi đó 'trang đầu' lệch về trang sau; việc cắt tiêu đề này "
      "tự nó là phát hiện layout, thuộc WARN tràn trang:")
    a("")
    for r in reports:
        if r["status"] != "RUN":
            continue
        a("- **%s**: %s" % (
            r["case_id"],
            json.dumps(r.get("pages_per_sheet", {}), ensure_ascii=False)))
    a("")
    a("Font PDF dùng (tham khảo — tự động không adjudicate được hình dục chữ):")
    a("")
    for r in reports:
        if r["status"] != "RUN":
            continue
        a("- **%s**: `%s`" % (r["case_id"], ", ".join(r["fonts"])))
    a("")
    a("## Độ trung thực text-layer (đối chiếu chuỗi nội dung ô với PDF)")
    a("")
    a("Text-layer được TÁI LẬP từ toạ độ ký tự (LibreOffice xuất glyph dấu "
      "tiếng Việt trong các text-run riêng lệch baseline). 4 tầng khớp: "
      "nguyên văn / đủ chữ mất dấu / đủ bộ ký tự xen kẽ (wrap, glyph dịch vị) "
      "/ thiếu ký tự. Lớp PDF dùng font thay thế Calibri (Caladea/Libertine) "
      "nên HÌNH DẠNG dấu vẫn cần xem mắt — mã ký tự thì đối chiếu được.")
    a("")
    for r in reports:
        if r["status"] != "RUN":
            continue
        a("- **%s**: %d/%d nguyên văn, %d mất dấu (fold-only), %d xen kẽ "
          "(bag-only), %d thiếu ký tự."
          % (r["case_id"], r.get("n_exact", 0),
             r.get("n_expected_strings", 0), len(r.get("diacritic_loss", [])),
             len(r.get("clip_scrambled", [])), len(r.get("clip_missing", []))))
    a("")
    a("## Chuỗi THIẾU KÝ TỰ trong text-layer PDF (ứng viên cắt cột/clip thật)")
    a("")
    any_missing = False
    for r in reports:
        if r["status"] != "RUN" or not r["clip_missing"]:
            continue
        any_missing = True
        a("**%s** (%d):" % (r["case_id"], len(r["clip_missing"])))
        a("")
        for s in r["clip_missing"][:20]:
            a("- `%s`" % s[:130])
        if len(r["clip_missing"]) > 20:
            a("- … (%d chuỗi nữa)" % (len(r["clip_missing"]) - 20))
        a("")
    if not any_missing:
        a("(không có — mọi chuỗi nội dung ô đều đủ ký tự trong PDF)")
    a("")
    a("## Chuỗi ĐỦ CHỮ NHƯNG MẤT DẤU trong text-layer (mã ký tự lệch — artefact font)")
    a("")
    any_diac = False
    for r in reports:
        if r["status"] != "RUN" or not r.get("diacritic_loss"):
            continue
        any_diac = True
        a("**%s** (%d):" % (r["case_id"], len(r["diacritic_loss"])))
        a("")
        for s in r["diacritic_loss"][:10]:
            a("- `%s`" % s[:120])
        a("")
    if not any_diac:
        a("(không có)")
    a("")
    a("## CẦN NGƯỜI NHÌN MẮT — MANUAL NOT RUN")
    a("")
    a("Text-layer PDF không adjudicate được các mục dưới đây. Cần mở "
      "`page-NN.png` (đã kèm) và TỐT NHẤT là mở file `.xlsx` trong Excel thật, "
      "zoom 100%/125%:")
    a("")
    a("1. **Tofu/glyph sai** cho ký tự đặc biệt (▾, •, ơ ư + dấu) — đã thấy "
      "LibreOffice vẽ lệch một số glyph dấu khi render PDF (xem mục 'Độ trung "
      "thực text-layer'); text-layer không adjudicate được hình dạng chữ — "
      "phải nhìn ảnh PNG và Excel thật (zoom 100%/125%).")
    a("2. **Màu nền ô** VÀNG (`FFF2CC`) / XÁM (`D9D9D9`) và palette nhóm câu.")
    a("3. **Mũi tên dropdown** trên ô select (Calc in PDF không vẽ mũi tên — "
      "xác nhận trên Excel thật có ▾ khi bấm ô).")
    a("4. **Chỗ ngắt trang in** của sheet dài (mục tràn trang WARN phía trên "
      "chỉ báo số trang, không đánh giá chỗ cắt có làm mất ô vàng không).")
    a("5. **Watermark đỏ** `Giấy_tờ_cần_gửi` hiển thị đúng mức đáng sợ (đỏ "
      "`C00000`, không lấn chữ thường).")
    a("6. **Độ rộng cột thực tế trên Excel** (Calc render gần đúng; Excel có "
      "thể xuống hàng khác với PDF).")
    a("")
    a("## Khuyến nghị cho Lead (từ quan sát tự động — lane visual KHÔNG sửa "
      "exporter/importer)")
    a("")
    a("1. **In ấn tràn cột**: nhiều case có số trang PDF > số sheet — sheet "
      "rộng hơn khổ A4 dọc, cột phải (ghi chú ví dụ, cột E/F) tràn sang trang "
      "riêng. Đề xuất exporter thêm `ws.page_setup.fitToWidth = 1` (hoặc "
      "orientation landscape cho sheet có bảng row_group) để khách in không "
      "mất cột. Cần Lead duyệt trước khi đưa vào `tools/excel_case_export.py`.")
    a("2. **veryHidden -> hidden**: LibreOffice hạ `__map`/`__lists` về "
      "`hidden` khi mở/lưu lại (đã adjudicate ở lane Calc round-trip, "
      "`tools/test_excel_calc_roundtrip.py`) — checksum + presence vẫn khớp "
      "nên tamper-check KHÔNG yếu đi; đề xuất audit/check nào yêu cầu "
      "veryHidden trên file khách nạp lại hãy hạ thành CẢNH BÁO.")
    a("")
    a("## NOT RUN")
    a("")
    for cid, reason in not_run:
        a("- %s — %s" % (cid, reason))
    a("")
    AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=str(ROOT), capture_output=True, text=True,
                              timeout=10).stdout.strip() or "?"
    except Exception:  # noqa: BLE001
        return "?"


def _soffice_version() -> str:
    try:
        out = subprocess.run([SOFFICE, "--version"], capture_output=True,
                             text=True, timeout=60).stdout.strip()
        return out.splitlines()[0] if out else "?"
    except Exception:  # noqa: BLE001
        return "?"


def _pymupdf_version() -> str:
    import pymupdf as _m  # noqa: C0415
    return getattr(_m, "__version__", "?")


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="",
                        help="danh sách caseId cách nhau bằng dấu phẩy")
    args = parser.parse_args()

    if not Path(SOFFICE).exists() and not shutil.which(SOFFICE):
        print("FAIL: không tìm thấy soffice tại %s" % SOFFICE)
        return 1

    qdir = ROOT / "app" / "data" / "case_questionnaires"
    all_ids = []
    for p in sorted(qdir.glob("*.json")):
        if p.name == "_index.json":
            continue
        try:
            all_ids.append(json.loads(p.read_text(encoding="utf-8"))
                           .get("case_id") or p.stem)
        except ValueError:
            continue
    wanted = ([c.strip() for c in args.cases.split(",") if c.strip()]
              or all_ids)

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []
    not_run: list[tuple[str, str]] = []
    for cid in wanted:
        if cid not in all_ids:
            not_run.append((cid, "không có manifest trong app/data/case_questionnaires"))
            continue
        try:
            manifest = _manifest(cid)
        except ValueError:
            not_run.append((cid, "manifest đang được ghi/lỗi JSON lúc chạy — "
                                 "chạy lại sau khi lane content xong"))
            reports.append({"case_id": cid, "status": "NOT RUN (manifest latch)"})
            print("NOT RUN %s (manifest đang ghi)" % cid)
            continue
        if not _case_is_ready(manifest):
            not_run.append((cid, "PENDING — chưa có câu hỏi (lane content sở hữu)"))
            reports.append({"case_id": cid, "status": "NOT RUN"})
            print("NOT RUN %s (PENDING)" % cid)
            continue
        rep = run_case(cid)
        reports.append(rep)
        print("%-40s sheets=%d pages=%d clip_missing=%d verdicts=%s" % (
            cid, rep["sheets"], rep["pages"], len(rep["clip_missing"]),
            rep["verdicts"]))

    _write_audit(reports, not_run)
    print("-" * 72)
    print("audit: %s" % AUDIT_MD)
    print("evidence: %s" % OUT_BASE)
    fails = [r["case_id"] for r in reports
             if "FAIL" in (r.get("verdicts") or {}).values()
             or r.get("status") == "FAIL"]
    if fails:
        print("VISUAL: FAIL — %s" % ", ".join(fails))
        return 1
    print("VISUAL: PASS (các mục WARN + MANUAL xem %s)" % AUDIT_MD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
