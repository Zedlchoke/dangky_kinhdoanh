#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_m09_rebuild.py — Lane m09-rebuild (PLI_M09, BASE eaa50f0).

Mệnh đề kiểm chứng cho rebuild Mẫu số 9 Phụ lục I TT 68/2025/TT-BTC
"Danh sách thành viên công ty hợp danh" theo quyết định D3.1=A (decontaminate)
và D3.2=A (chọn bản Mẫu 9 thứ hai — header 14 cột) của docs/decision_registry.md:

  [LOAD]   tools/form_specs/formation/PLI_M09.json qua validator v1 của
           tools/build_form_maps.load_form_spec (chạy TRƯỚC khi đụng document).
  [COLS]   14 cột khai báo đúng thứ tự biểu mẫu gốc; `cols` regex -> tag khớp
           1-1, không trùng tag, cột STT không gắn the.
  [SANDBOX] build thật trong sandbox (OUT_TPL/OUT_DATA ghi vào temp, KHÔNG đụng
           app/templates / app/data): bảng 14 cột vật lý, header khớp khai báo,
           hàng mẫu gắn {#loop}{_stt}...{/loop}, form_maps side (dynamic_tables +
           fields) đăng ký đủ tag dưới key "<loop>.<tag>".
  [DECON]  template sau build KHÔNG còn dấu hiệu nhiễm Mẫu 6/7/8/9(lần 2)/10,
           nội dung hợp pháp (mục 8-10, cam kết, khối ký, chân trang 1-9) được
           GIỮ; tàn dư vùng nhiễm đã bị xóa TẠI NGUỒN (laneC 2026-09-06),
           pin đúng 1 đường ký + 1 'STT' hợp pháp.
  [NUM]    ĐÁNH SỐ MỤC LIÊN TỤC: dãy mục "N." trong template tăng dần, không
           trùng, không nhảy trong phạm vi nó có; ghép với PLI_M05 (mục 1..6 của
           use case thanh_lap_hop_danh) phải phủ 1..10 và thiếu ĐÚNG mục 7 đã
           khai gap (mục 7 = "Thành viên công ty (kê khai theo Mẫu số 9 Phụ lục
           I ...): Gửi kèm." bị mất ở nguồn). Mọi lệch khác đều ĐỎ.
  [NEG]    tháo 1 cột trong spec (in-memory) -> build vẫn chạy (generator trung
           thực với spec) nhưng helper contract của test này phải TỪ CHỐI ->
           chứng minh suite có cắn.
  [GUARD]  artifact production (app/templates/PLI_M09.docx, app/data/form_maps,
           app/data/blocks) KHÔNG bị đụng bởi suite này (lane KHÔNG regen global).

Chạy: python3 -X utf8 -m tools.test_m09_rebuild   (từ root repo)
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import docx
from docx.text.paragraph import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.build_form_maps as bfm          # noqa: E402
import tools.docx_to_blocks as dxtb          # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "tools" / "form_specs" / "formation" / "PLI_M09.json"
SRC_M05 = ROOT / "app" / "templates" / "PLI_M05.docx"
GUARDED = [ROOT / "app" / "templates" / "PLI_M09.docx",
           ROOT / "app" / "data" / "form_maps.json",
           ROOT / "app" / "data" / "blocks" / "PLI_M09.json"]

# ---------------------------------------------------------------------------
# Hợp đồng 14 cột (nguồn: header glued của bản Mẫu 9 thứ hai trong tài liệu
# nguồn, đối chiếu bản mẫu .doc Mẫu số 9 Phụ lục I — ngày tra cứu 2026-08-28;
# Mẫu số 9 KHÔNG thuộc 09 biểu mẫu TT 121/2026/TT-BTC thay thế).
# Thứ tự cột = thứ tự vật lý của biểu mẫu gốc (chân số 1..14 của header gốc).
# ---------------------------------------------------------------------------
EXPECTED_HEADERS = [
    "STT",
    "Tên thành viên",
    "Ngày, tháng, năm sinh đối với thành viên là cá nhân",
    "Giới tính",
    "Loại giấy tờ, số, ngày cấp, cơ quan cấp Giấy tờ pháp lý của cá nhân",
    "Quốc tịch",
    "Dân tộc",
    "Địa chỉ liên lạc",
    "Phần vốn góp (bằng số; VNĐ và giá trị tương đương theo đơn vị tiền nước "
    "ngoài: bằng số, loại ngoại tệ, nếu có)",
    "Tỷ lệ (%)",
    "Loại tài sản, số lượng, giá trị tài sản góp vốn",
    "Thời hạn góp vốn",
    "Chữ ký của thành viên",
    "Ghi chú (nếu có)",
]
EXPECTED_TAGS = [   # None = cột STT do engine sinh ({_stt})
    None, "ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "quoc_tich",
    "dan_toc", "dia_chi", "von_dong_gop", "ty_le_von", "loai_tai_san_gop_von",
    "thoi_han_gop_von", "chu_ky", "ghi_chu",
]
LOOP = "ds_thanh_vien_hop_danh"
FIELDS = [t for t in EXPECTED_TAGS if t and t != "chu_ky"]   # chu_ky = outputOnly

# Mục đánh số "N." của Mẫu số 9 Phụ lục I (đoạn mà template PLI_M09 giữ) và của
# Mẫu số 5 (Giấy đề nghị đăng ký doanh nghiệp - Công ty hợp danh, mục 1..6 nằm
# trong template PLI_M05 — cùng use case thanh_lap_hop_danh trên app).
# [Lead sync 2026-08-28] dòng mục 7 ĐÃ được chèn vào template qua spec
# "inserts" (nguyên văn TT 121/2026 Mẫu 5 tr.4/PDF45 — giống hệt TT 68):
# M09 giờ đủ 7..10; khi ghép M05 (1..6) phủ trọn 1..10, KHÔNG còn gap.
M09_SECTIONS_PRESENT = [7, 8, 9, 10]
M05_SECTIONS_PRESENT = [1, 2, 3, 4, 5, 6]
FULL_RANGE = list(range(1, 11))          # mục 1..10 của Mẫu số 5 Phụ lục I
KNOWN_GAP = []                           # đã vá — không còn mục thiếu
SECTION7_VERBATIM = ("7. Thành viên công ty (kê khai theo Mẫu số 9 Phụ lục I "
                     "ban hành kèm Thông tư này): Gửi kèm.")

# Dấu hiệu nhiễm (Mẫu 6/7/8/9 lần 2/10) phải VẮNG MẶT trong template sau build.
# CONTAM_HEADINGS = heading mẫu đứng THÀNH 1 PARAGRAPH RIÊNG (chân trang hợp pháp
# của Mẫu số 5 có nhắc chữ "Mẫu số 10 Phụ lục I" nên không thể soi theo chuỗi con).
CONTAM_HEADINGS = ["Mẫu số 6", "Mẫu số 7", "Mẫu số 8", "Mẫu số 10"]
CONTAM_MARKERS = [
    "DANH SÁCH THÀNH VIÊN CÔNG TY TRÁCH NHIỆM HỮU HẠN",
    "DANH SÁCH CỔ ĐÔNG SÁNG LẬP",
    "DANH SÁCH CỔ ĐÔNG LÀ NHÀ ĐẦU TƯ NƯỚC NGOÀI",
    "DANH SÁCH CHỦ SỞ HỮU HƯỞNG LỢI",
    "Thành viên góp vốn là tổ chức",
    "Thông tin người đại diện theo pháp luật/ủy quyền của cổ đông",
    "I. Cổ đông sáng lập là cá nhân",
    "A. Thành viên hợp danh",
]
# Nội dung hợp pháp phải CÒN (Mẫu số 5 PL I — mục 7(khối GCN đầu tư)..10 + ký).
KEEP_MARKERS = [
    "Thông tin về Giấy chứng nhận đăng ký đầu tư",
    "Mã số dự án",
    "8. Thông tin đăng ký thuế:",
    "8.1", "8.9",
    "Thông tin về Giám đốc/Tổng giám đốc (nếu có):",
    "9. Thông tin về việc đóng bảo hiểm xã hội",
    "10. Thông tin về chủ sở hữu hưởng lợi của doanh nghiệp",
    "Các thành viên hợp danh cam kết:",
    "CÁC THÀNH VIÊN HỢP DANH",
    "9 - Các thành viên hợp danh của công ty ký trực tiếp vào phần này.",
]

_results: list[tuple[bool, str]] = []


def check(name: str):
    def deco(fn):
        def run():
            try:
                fn()
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:                        # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


def fold(text: str) -> str:
    """Chung quy tắc với build_form_maps.fold (thường, bỏ dấu, đ->d)."""
    s = re.sub(r"\s+", " ", text or "").strip()
    nfkd = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").replace(
        "đ", "d")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def body_texts(doc) -> list[str]:
    return [Paragraph(el, doc).text for el in doc.element.body.iterchildren()
            if el.tag.endswith("}p")]


def _plain(block: dict) -> str:
    """Text phẳng của 1 block (để soi nhiễm trong block JSON)."""
    if "text" in block and isinstance(block["text"], str):
        return block["text"]
    return "".join(str(r.get("text", "")) for r in block.get("runs") or [])


def folds_count_heading(blocks: dict, heading: str = "Mẫu số 9") -> int:
    """Số block có text trùng khớp heading (fold)."""
    target = fold(heading)
    return sum(1 for b in blocks["blocks"]
               if fold(_plain(b)).strip() == target)


def section_numbers(texts: list[str]) -> list[int]:
    """Số mục heading 'N.' (bỏ mục con '8.1', bỏ chân trang không có dấu chấm)."""
    out = []
    for t in texts:
        m = re.match(r"^\s*(\d+)\.(?!\d)", t or "")
        if m:
            out.append(int(m.group(1)))
    return out


def sample_row_tags(sample: list[str]) -> list:
    """Tag đọc từ hàng mẫu của bảng rebuild (ô 0 = STT engine -> None)."""
    tags = [None]
    for cell in sample[1:]:
        m = re.search(r"\{([a-z_]+)\}", cell)
        tags.append(m.group(1) if m else None)
    return tags


def assert_contract_14(headers: list[str], tags: list) -> None:
    """Hợp đồng 14 cột — dùng ở cả nhánh chính lẫn nhánh NEGATIVE."""
    assert len(headers) == 14, "số cột = %d, kỳ vọng 14 (D3.2=A)" % len(headers)
    assert len(tags) == 14, "số tag = %d, kỳ vọng 14" % len(tags)
    assert headers == EXPECTED_HEADERS, (
        "header lệch biểu mẫu gốc:\n  got  %r\n  want %r"
        % (headers, EXPECTED_HEADERS))
    assert tags == EXPECTED_TAGS, (
        "tag lệch hợp đồng:\n  got  %r\n  want %r" % (tags, EXPECTED_TAGS))
    assert tags[0] is None, "cột 0 phải là STT engine (tag null), nhận %r" % tags[0]
    named = [t for t in tags if t]
    assert len(named) == len(set(named)), "tag trùng nhau: %r" % named
    assert set(named) == {t for t in EXPECTED_TAGS if t}, "tập tag lệch"
    for new_col in ("loai_tai_san_gop_von", "thoi_han_gop_von", "ghi_chu"):
        assert new_col in named, "thiếu cột mới theo D3.2=A: %s" % new_col


# ---------------------------------------------------------------------------
# Sandbox build dùng chung (không đụng artifact production)
# ---------------------------------------------------------------------------
def build_sandbox(spec_override: dict | None = None):
    """Chạy process_form cho PLI_M09 với OUT_TPL/OUT_DATA sang temp.

    spec_override = raw spec JSON thay thế (dùng ở nhánh NEGATIVE).
    Trả về (doc, meta, tmp_dir) — global của build_form_maps luôn được trả như
    cũ; caller chỉ còn phải xoá tmp_dir.
    """
    tmp = Path(tempfile.mkdtemp(prefix="m09_rebuild_"))
    tpl_dir, data_dir = tmp / "templates", tmp / "data"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    saved_tpl, saved_data = bfm.OUT_TPL, bfm.OUT_DATA
    real_load = bfm.load_form_spec
    bfm.OUT_TPL, bfm.OUT_DATA = tpl_dir, data_dir
    bfm._form_spec_cache.clear()
    try:
        if spec_override is not None:
            ent = spec_override["tables"][0]
            sid = ent["spec"]["id"]
            entries = [{k: v for k, v in ent.items() if k != "spec"}]
            entries[0]["spec"] = sid
            ext = {"entries": entries,
                   "specs_by_id": {sid: bfm._json_spec(ent["spec"], "PLI_M09")}}
            bfm.load_form_spec = (lambda fid, _ext=ext, _real=real_load:
                                  _ext if fid == "PLI_M09" else _real(fid))
        src = bfm.find_source("PLI_M09")
        meta, unmatched = bfm.process_form(src, {"Phu luc I|9": "T-M09"}, None)
        meta["unmatched"] = unmatched
        tpl_path = tpl_dir / "PLI_M09.docx"
        if not tpl_path.exists():
            raise AssertionError("generator chưa ghi template sandbox")
        return docx.Document(str(tpl_path)), meta, tmp
    finally:
        bfm.OUT_TPL, bfm.OUT_DATA = saved_tpl, saved_data
        bfm.load_form_spec = real_load
        bfm._form_spec_cache.clear()


def sandbox_texts() -> list[str]:
    """Build sandbox và trả về danh sách text paragraph (dọn sandbox xong)."""
    doc, _meta, tmp = build_sandbox()
    try:
        return body_texts(doc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check("[LOAD] spec PLI_M09 qua validator v1 cua loader")
def t_load():
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    assert raw["form_id"] == "PLI_M09"
    assert raw["group"] == "formation", "nhóm phải là formation (PLI_M01..M11)"
    assert len(raw["tables"]) == 1, "chỉ 1 entry (bảng chính 14 cột)"
    ent = raw["tables"][0]
    assert ent["spec"]["kind"] == "list"
    assert ent["spec"]["loop"] == LOOP, "loop phải riêng để né export conflict guard"
    assert ent["spec"]["loop"] != "ds_thanh_vien", (
        "loop cũ ds_thanh_vien đã bị GRID_META khác dùng -> "
        "EXPORT_LOOP_CONTRACT_CONFLICT nếu giữ")
    assert ent["no_default_drops"] is True
    assert ent["drop_until"], "phải có drop_until để giới hạn vùng drop"
    assert len(ent["headers"]) == 14
    assert len(ent["drop"]) >= 60, "decontaminate phải có bộ pattern drop"
    ext = bfm.load_form_spec("PLI_M09")
    assert ext and len(ext["entries"]) == 1
    assert ext["specs_by_id"]["ds_thanh_vien_hop_danh"]["loop"] == LOOP
    # anchor khớp ĐÚNG 1 paragraph nguồn (khối GCN đầu tư — điểm chèn bảng)
    src = docx.Document(str(bfm.find_source("PLI_M09")))
    hits = [i for i, p in enumerate(src.paragraphs)
            if re.search(ent["anchor"], fold(p.text))]
    assert hits == [2], "anchor khớp %r (kỳ vọng [2] = khối GCN đầu tư)" % hits
    assert not ent.get("trim"), "không dùng trim (cắt đuôi glue không khả dụng)"


@check("[COLS] cols regex -> tag khop 1-1 tren 14 header khai bao")
def t_cols_mapping():
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    ent = raw["tables"][0]
    spec = bfm._json_spec(ent["spec"], "PLI_M09")
    mapped = bfm._col_tags_for_headers(ent["headers"], spec)
    got = [mapped[i] for i in range(len(ent["headers"]))]
    assert got == EXPECTED_TAGS, "mapping lệch: %r" % (got,)
    folded = {fold(re.sub(r"\s+", " ", h)).strip() for h in ent["headers"]}
    missing = set(spec["detect"]) - folded
    assert not missing, "detect thiếu trong header: %r" % sorted(missing)
    for token in ("thoi han gop von", "ghi chu (neu co)", "stt"):
        assert token in folded, "thiếu token detect %r (mất khả năng chặn sớm)" % token


@check("[SANDBOX] build that: bang 14 cot + form_maps side")
def t_sandbox_build():
    doc, meta, tmp = build_sandbox()
    try:
        assert meta["unmatched"] == [], "còn ô □ chưa gắn the: %r" % meta["unmatched"]
        assert len(doc.tables) == 1, "số bảng = %d, kỳ vọng 1" % len(doc.tables)
        tbl = doc.tables[0]
        headers = [c.text.strip() for c in tbl.rows[0].cells]
        sample = [c.text.strip() for c in tbl.rows[-1].cells]
        assert_contract_14(headers, sample_row_tags(sample))
        assert "{_stt}" in tbl.rows[-1].cells[0].text, (
            "cột STT phải gắn {_stt}, nhận %r" % tbl.rows[-1].cells[0].text)
        assert "{#%s}" % LOOP in tbl.rows[-1].cells[0].text, (
            "thẻ mở loop phải nằm ở ô đầu có the")
        assert "{/%s}" % LOOP in tbl.rows[-1].cells[-1].text, (
            "thẻ đóng loop phải nằm ở ô cuối có the")
        assert len(tbl.rows) == 1 + bfm.REBUILD_BLANK_ROWS, (
            "số hàng bảng = %d (1 header + %d hàng trắng)"
            % (len(tbl.rows), bfm.REBUILD_BLANK_ROWS))
        # form_maps side
        dyn = [d for d in meta["dynamic_tables"] if d["loop"] == LOOP]
        assert len(dyn) == 1, "form_maps thiếu dynamic_table %r" % LOOP
        got = [(c["col"], c["tag"]) for c in dyn[0]["columns"]]
        want = [(i, t) for i, t in enumerate(EXPECTED_TAGS) if t]
        assert got == want, "cols form_maps lệch: %r" % (got,)
        keys = {f["key"] for f in meta["fields"]}
        for tag in FIELDS:
            assert ("%s.%s" % (LOOP, tag)) in keys, "thiếu field %s.%s" % (LOOP, tag)
        assert ("%s.chu_ky" % LOOP) not in keys, (
            "chu_ky là outputOnly, không đăng ký field nhập")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check("[DECON] khong con vung nhiem Mau 6/7/8/9(lan 2)/10, noi dung hop phap giu nguyen")
def t_decontaminate():
    texts = sandbox_texts()
    folds = [fold(t) for t in texts]
    for heading in CONTAM_HEADINGS:
        hits = [t for t, f in zip(texts, folds) if f == fold(heading)]
        assert not hits, "còn heading nhiễm %r: %r" % (heading, hits[:2])
    # bản Mẫu 9 thứ hai đã bị xoá: chỉ còn ĐÚNG 1 dòng 'Mẫu số 9' của mẫu
    assert folds.count("mau so 9") == 1, (
        "số dòng 'Mẫu số 9' = %d, kỳ vọng 1 (bản copy thứ hai phải bị xoá)"
        % folds.count("mau so 9"))
    for marker in CONTAM_MARKERS:
        hits = [t for t in texts if fold(marker) in fold(t)]
        assert not hits, "còn dấu hiệu nhiễm %r: %r" % (marker, hits[:2])
    joined = "\n".join(fold(t) for t in texts)
    for marker in KEEP_MARKERS:
        assert fold(marker) in joined, "mất nội dung hợp pháp: %r" % marker
    # Tàn dư vùng nhiễm đã BIẾN MẤT khỏi nguồn (laneC REMOVED_BY_SOURCE_CLEANUP,
    # 2026-09-06: xóa p103-p222 + đuôi glue 'Mẫu số 6' của p102 tại file nguồn):
    # chỉ còn đường ký hợp pháp p090 (25 '_') của khối "CÁC THÀNH VIÊN HỢP DANH"
    # và 'STT' của bảng thuế mục 8. Pin đúng 1/1 để tàn dư không hồi sinh.
    underscores = [t for t in texts if re.fullmatch(r"_+", (t or "").strip() or "x")]
    stt_only = [t for t in texts if (t or "").strip() == "STT"]
    assert len(underscores) == 1, (
        "số đường '_' = %d, kỳ vọng 1 (đường ký hợp pháp p090; 4 tàn dư"
        " p112/p140/p166/p219 đã bị xóa khỏi nguồn — nếu >1 nghĩa là nhiễm "
        "tái xuất hoặc mất đường ký)" % len(underscores))
    assert len(stt_only) == 0, (
        "số paragraph 'STT' = %d, kỳ vọng 0 ('STT' của bảng thuế mục 8 nằm "
        "trong bảng sau build; tàn dư p189 đã bị xóa khỏi nguồn)"
        % len(stt_only))
    # bảng chèn đúng chỗ: ngay sau 'Mẫu số 9', rồi dòng mục 7 (Lead chèn qua
    # spec inserts — lệnh owner 2026-08-28), rồi khối GCN đầu tư. Khoảng giữa
    # 'Mẫu số 9' và mục 7 chỉ được chứa paragraph nhẹ (spacer/close-break của
    # landscape) — bảng 14 cột là w:tbl nên không xuất hiện trong danh sách p.
    folds = [fold(t) for t in texts]
    assert folds[0].startswith("pl1 - mau so 9"), "mất dòng tiêu đề nguồn"
    assert folds[1] == "mau so 9", "p001 phải là 'Mẫu số 9', nhận %r" % folds[1]
    hits7 = [i for i, f in enumerate(folds) if f.startswith("7. thanh vien cong ty")]
    assert len(hits7) == 1, "dòng mục 7 xuất hiện %d lần, kỳ vọng 1" % len(hits7)
    i7 = hits7[0]
    assert 1 < i7 < len(folds), "mục 7 phải đứng sau khối tiêu đề"
    between = [f for f in folds[2:i7] if f]
    assert not between, (
        "giữa 'Mẫu số 9' và mục 7 chỉ được có bảng + paragraph nhẹ, thấy: %r"
        % between[:3])
    assert folds[i7 + 1].startswith("- thong tin ve giay chung nhan dang ky dau tu"), (
        "p004 sau mục 7 phải là khối GCN đầu tư, nhận %r" % folds[4])


@check("[BLOCKS] template sandbox quay tron duoc ve blocks (converter app đọc)")
def t_blocks_roundtrip():
    doc, meta, tmp = build_sandbox()
    try:
        blocks = dxtb.convert_document(
            doc, "PLI_M09", "Danh sách thành viên công ty hợp danh",
            overrides={}, footnotes={}, section_specs=meta.get("section_specs"))
        loops = [b for b in blocks["blocks"] if b.get("t") == "loop"]
        assert len(loops) == 1, "số block loop = %d, kỳ vọng 1" % len(loops)
        assert loops[0]["loop"] == LOOP, "loop block = %r" % loops[0].get("loop")
        got = [(c["col"], c["tag"]) for c in loops[0]["cols"]]
        want = [(i, t) for i, t in enumerate(EXPECTED_TAGS) if t]
        assert got == want, "cols block lệch: %r" % (got,)
        plain = fold("".join(_plain(b) for b in blocks["blocks"]))
        for marker in CONTAM_MARKERS:
            assert fold(marker) not in plain, "blocks còn nhiễm: %r" % marker
        for heading in CONTAM_HEADINGS:
            same = [b for b in blocks["blocks"]
                    if fold(_plain(b)).strip() == fold(heading)]
            assert not same, "blocks còn heading nhiễm %r" % heading
        assert folds_count_heading(blocks) == 1, (
            "blocks phải còn đúng 1 dòng 'Mẫu số 9' của chính mẫu")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check("[NUM] danh so muc lien tuc: M09 = [7..10] (da chen muc 7), ghep M05 phu 1..10 DU")
def t_numbering():
    texts = sandbox_texts()
    nums = section_numbers(texts)
    assert len(set(nums)) == len(nums), "trùng số mục: %r" % nums
    assert nums == list(range(nums[0], nums[-1] + 1)), "nhảy mục trong M09: %r" % nums
    assert nums == M09_SECTIONS_PRESENT, (
        "dãy mục trong PLI_M09 = %r, kỳ vọng %r" % (nums, M09_SECTIONS_PRESENT))
    # ghép use case thanh_lap_hop_danh = PLI_M05 (mục 1..6) + PLI_M09
    m05_nums = section_numbers(body_texts(docx.Document(str(SRC_M05))))
    assert m05_nums == M05_SECTIONS_PRESENT, (
        "PLI_M05 đổi số mục so với base: %r" % m05_nums)
    merged = sorted(m05_nums + nums)
    assert len(set(merged)) == len(merged), "trùng số mục khi ghép: %r" % merged
    missing = [n for n in FULL_RANGE if n not in merged]
    assert missing == KNOWN_GAP, (
        "mục thiếu khi ghép M05+M09 = %r, kỳ vọng Đúng %r" % (missing, KNOWN_GAP))
    # mục 7 chèn bằng spec "inserts" với NGUYÊN VĂN đúng bản hiện hành
    # (TT 121/2026 Mẫu 5 tr.4/PDF45 — đối chiếu TT 68 giống hệt)
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    ins = raw.get("inserts") or []
    assert ins, "spec phải khai inserts để chèn mục 7 (không sửa tay template)"
    joined = "".join(r.get("text", "") for r in ins[0]["runs"])
    assert SECTION7_VERBATIM in joined, (
        "insert không chứa nguyên văn dòng mục 7: %r" % joined[:120])
    # template thật phải chứa dòng đã chèn (không chỉ spec)
    import zipfile as _zip
    tpl_xml = _zip.ZipFile(str(bfm.OUT_TPL / "PLI_M09.docx")).read(
        "word/document.xml").decode("utf-8")
    assert "7. Thành viên công ty" in tpl_xml, \
        "template PLI_M09 chưa có dòng mục 7 — regen chưa chạy inserts"


@check("[NEG] spec bi thao 1 cot -> build ra 13 cot va helper contract TU CHOI")
def t_negative_missing_column():
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    broken = copy.deepcopy(raw)
    ent = broken["tables"][0]
    idx = ent["headers"].index("Thời hạn góp vốn")       # cột 10 bị thiếu ở grid cũ
    del ent["headers"][idx]
    del ent["spec"]["cols"][idx]
    ent["spec"]["fields"] = [f for f in ent["spec"]["fields"]
                             if f != "thoi_han_gop_von"]
    ent["spec"]["detect"] = [d for d in ent["spec"]["detect"]
                             if d != "thoi han gop von"]
    ent["drop"] = list(ent["drop"]) + [r"^thoi han gop von$"]

    doc, meta, tmp = build_sandbox(spec_override=broken)
    try:
        assert len(doc.tables) == 1
        tbl = doc.tables[0]
        headers = [c.text.strip() for c in tbl.rows[0].cells]
        tags = sample_row_tags([c.text.strip() for c in tbl.rows[-1].cells])
        # generator TRUNG THỰC với spec: thật sự build 13 cột
        assert len(headers) == 13 and len(tbl.columns) == 13, (
            "generator không phản ánh spec bị tháo cột: %d cột" % len(tbl.columns))
        assert "thoi_han_gop_von" not in tags
        # ... và hợp đồng của test này phải TỪ CHỐI trạng thái đó -> suite ĐỎ
        try:
            assert_contract_14(headers, tags)
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "helper contract KHÔNG cắn: spec tháo 1 cột vẫn được chấp nhận")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@check("[GUARD] suite khong đụng artifact production (khong regen global)")
def t_guard_production():
    before = {str(p): sha256_file(p) for p in GUARDED if p.exists()}
    assert len(before) == len(GUARDED), "artifact production thiếu: %r" % GUARDED
    sandbox_texts()
    for p in GUARDED:
        assert sha256_file(p) == before[str(p)], "%s bị ghi ngoài sandbox!" % p
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    # [Lead sync 2026-08-28] + "inserts": capability chèn paragraph qua spec
    # (sửa mất mục 7) — loader tools/build_form_maps.py đã validate shape.
    extra = set(raw) - {"form_id", "group", "note", "gap_nghiepvu", "tables",
                        "section_cond", "inserts"}
    assert not extra, "root key không được phép: %r" % sorted(extra)


def main() -> int:
    t_load()
    t_cols_mapping()
    t_sandbox_build()
    t_decontaminate()
    t_blocks_roundtrip()
    t_numbering()
    t_negative_missing_column()
    t_guard_production()
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 72)
    print("test_m09_rebuild: %d PASS / %d FAIL" % (passed, failed))
    for ok, name in _results:
        if not ok:
            print("  -> %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
