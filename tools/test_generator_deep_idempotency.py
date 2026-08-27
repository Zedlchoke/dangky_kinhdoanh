# -*- coding: utf-8 -*-
"""Deep idempotency + negative mutation cho pipeline generator 3 kind mới.

Lane B2 (base ab3c1f1). Chạy HOÀN TOÀN trong sandbox (tmp dir): nguồn docx,
form_specs, templates, form_maps đều trỏ vào tmp qua monkeypatch
build_form_maps.ROOT/OUT_TPL/OUT_DATA/FORM_SPECS_DIR — KHÔNG chạy generator
vào production paths, KHÔNG đụng app/templates hay app/data/blocks.

Hai nhóm mệnh đề:

[ID] DEEP IDEMPOTENCY
    Định nghĩa semantic-hash của lane này:
      - template: sha256 trên cây canonical của word/document.xml (mọi phần tử
        với tên tag đã bỏ namespace + attrs sorted + text, KHÔNG dùng zip
        timestamps — bài học 2026-08-27: python-docx save() chỉ đổi timestamp,
        git-status binary không tin được);
      - blocks: sha256 trên json.dumps(convert_document(...), sort_keys=True)
    Generator chạy LẦN 1 rồi LẦN 2 từ cùng một nguồn => hash PHẢI giống hệt.
    Thêm dạng thật (nguồn + spec production của PLI_M01) để chứng minh hành vi
    kind "list" KHÔNG TRÔI (so semantic-hash lần 2 và so blocks JSON khớp
    artifact đang commit).

[NEG] NEGATIVE MUTATION — mỗi biến thể template/spec SAI PHẢI bị bắt:
    n1 thiếu marker {#loop}            -> converter không tìm thấy block loop
    n2 thừa hàng khuôn lặp 2 lần       -> không đúng 1 block loop
    n3 đảo vị trí the dữ liệu          -> GridSpecMismatch (sai col_index vật lý)
    n4 mất rowspan header (làm phẳng)  -> GridSpecMismatch (header lệch tiling)
    n5 thiếu marker đóng {/cond}       -> ValueError (marker lệch cặp)
    n6 region occurrence nhiễu         -> SKIP có kiểm soát, KHÔNG chèn bảng
    n7 boundary sai (dropUntil sai ranh) -> không xoá paragraph bảng kế tiếp

File thuần Python, style @check giống tools/test_m72_conditional_export.py.
Exit code 0 = PASS / 1 = FAIL.

Chạy:  python -X utf8 tools/test_generator_deep_idempotency.py
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document                     # noqa: E402
from docx.oxml.ns import qn                   # noqa: E402

from tools import build_form_maps as bfm      # noqa: E402
from tools import docx_to_blocks as dxtb      # noqa: E402
from tools import table_occurrences           # noqa: E402

_results: list[tuple[bool, str]] = []
_tmp_root: Path | None = None


def check(name: str):
    def deco(fn):
        def run(*args):
            try:
                fn(*args)
                _results.append((True, name))
                print("PASS %s" % name)
            except AssertionError as exc:
                _results.append((False, "%s: %s" % (name, exc)))
                print("FAIL %s: %s" % (name, exc))
            except Exception as exc:  # noqa: BLE001
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


# ---------------------------------------------------------------------------
# Sandbox helpers
# ---------------------------------------------------------------------------

SOURCE_DIR_NAME = "05_cong_bo_cung_cap_thong_tin"


def new_sandbox() -> dict:
    global _tmp_root
    _tmp_root = Path(tempfile.mkdtemp(prefix="b2_gen_"))
    paths = {
        "root": _tmp_root / "repo",
        "specs": _tmp_root / "form_specs",
        "templates": _tmp_root / "templates",
        "data": _tmp_root / "data",
    }
    for p in list(paths.values()) + [paths["root"] / SOURCE_DIR_NAME]:
        p.mkdir(parents=True, exist_ok=True)
    return paths


def apply_sandbox(paths: dict) -> dict:
    saved = {
        "ROOT": bfm.ROOT, "OUT_TPL": bfm.OUT_TPL, "OUT_DATA": bfm.OUT_DATA,
        "FORM_SPECS_DIR": bfm.FORM_SPECS_DIR,
    }
    bfm.ROOT = paths["root"]
    bfm.OUT_TPL = paths["templates"]
    bfm.OUT_DATA = paths["data"]
    bfm.FORM_SPECS_DIR = paths["specs"]
    bfm._form_spec_cache.clear()
    return saved


def restore(saved: dict) -> None:
    bfm.ROOT = saved["ROOT"]
    bfm.OUT_TPL = saved["OUT_TPL"]
    bfm.OUT_DATA = saved["OUT_DATA"]
    bfm.FORM_SPECS_DIR = saved["FORM_SPECS_DIR"]
    bfm._form_spec_cache.clear()


def write_source(paths: dict, mau_so: int, paragraphs: list[str],
                 trailing_table: bool = False) -> Path:
    """Sinh file nguồn demo (`PL1_Mau_<n>_demo_b2_lane.docx`) trong sandbox."""
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph("" if text is None else text)
    if trailing_table:
        tbl = doc.add_table(rows=2, cols=2)
        cells = (("BẢNG KẾ", "không xóa"), ("cột A", "cột B"))
        for ri in range(2):
            for ci in range(2):
                tbl.rows[ri].cells[ci].text = cells[ri][ci]
    path = paths["root"] / SOURCE_DIR_NAME / (
        "PL1_Mau_%02d_demo_b2_lane.docx" % mau_so)
    doc.save(str(path))
    return path


def write_spec(paths: dict, form_id: str, spec: dict) -> Path:
    """Spec phải nằm trong một thư mục NHÓM (loader glob '*/*.json')."""
    group = paths["specs"] / "change"
    group.mkdir(parents=True, exist_ok=True)
    out = group / ("%s.json" % form_id)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return out


def run_generation(form_id: str, mau_so: int, paths: dict) -> tuple[dict, Path]:
    bfm._form_spec_cache.clear()  # mỗi mệnh đề ghi lại spec mới cho cùng id
    source = bfm.find_source(form_id)
    titles = {"Phu luc I|%d" % mau_so: "DEMO %s" % form_id}
    meta, unmatched = bfm.process_form(source, titles, None)
    bfm.write_maps({form_id: meta})
    tpl = bfm.OUT_TPL / ("%s.docx" % form_id)
    assert tpl.exists(), "generator chưa ghi template: %s" % tpl
    return meta, tpl


def convert_blocks(tpl: Path, form_id: str, meta: dict) -> dict:
    doc = Document(str(tpl))
    return dxtb.convert_document(
        doc, form_id, meta.get("ten_mau", ""), overrides={}, footnotes={},
        section_specs=meta.get("section_specs"))


# ---------------------------------------------------------------------------
# Semantic hash (định nghĩa idempotency của lane này)
# ---------------------------------------------------------------------------

def canon_element(el) -> dict:
    tag = el.tag.split("}")[-1]
    return {
        "tag": tag,
        "attrs": sorted((k.split("}")[-1], v) for k, v in el.attrib.items()),
        "text": el.text or "",
        "children": [canon_element(child) for child in el],
    }


def template_hash(docx_path: Path) -> str:
    """sha256(content word/document.xml dạng cây canonical) — BỎ zip metadata."""
    with zipfile.ZipFile(docx_path) as zf:
        raw = zf.read("word/document.xml")
    blob = json.dumps(canon_element(ET.fromstring(raw)),
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def blocks_hash(data: dict) -> str:
    blob = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def body_texts(docx_path: Path) -> list[str]:
    """Text mọi paragraph con trực tiếp của body theo thứ tự (để soi boundary)."""
    doc = Document(str(docx_path))
    from docx.text.paragraph import Paragraph
    return [Paragraph(el, doc).text for el in doc.element.body.iterchildren()
            if el.tag == qn("w:p")]


def table_signature(docx_path: Path) -> list[list[list[str]]]:
    """[[[cell,...],...],...] cho mọi bảng — duyệt w:tc trực tiếp."""
    doc = Document(str(docx_path))
    sig = []
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:tbl"):
            continue
        rows = []
        for tr in child.tr_lst:
            row = []
            for tc in tr.iterchildren():
                if tc.tag != qn("w:tc"):
                    continue
                txt = "".join(
                    (node.text or "")
                    for node in tc.iter() if node.tag == qn("w:t"))
                row.append(txt.strip())
            rows.append(row)
        sig.append(rows)
    return sig


def physical_widths(docx_path: Path) -> list[int]:
    """Số gridCol của từng bảng trong template."""
    doc = Document(str(docx_path))
    widths = []
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:tbl"):
            continue
        grid = child.find(qn("w:tblGrid"))
        widths.append(len([el for el in grid.iterchildren()
                           if el.tag == qn("w:gridCol")]))
    return widths


# ---------------------------------------------------------------------------
# Spec fixtures (sandbox only — nội dung demo, không phải nội dung pháp lý)
# ---------------------------------------------------------------------------

NESTED_HEADERS = [
    [{"text": "STT", "rowspan": 2}, {"text": "Tên thành viên", "rowspan": 2},
     {"text": "Phần vốn góp", "colspan": 2}, {"text": "Chữ ký", "rowspan": 2}],
    [{"text": "VNĐ"}, {"text": "Ngoại tệ"}],
]

NESTED_COLUMNS = [
    {"header": "Tên thành viên", "tag": "ho_ten", "col_index": 1,
     "required": True},
    {"header": "VNĐ", "tag": "von_vnd", "col_index": 2, "input_type": "money"},
    {"header": "Ngoại tệ", "tag": "von_ntte", "col_index": 3,
     "input_type": "money"},
    {"header": "Chữ ký", "tag": "chu_ky", "col_index": 4,
     "input_type": "outputOnly"},
]


def nested_occ_spec(n_occ: int = 4, loop_prefix: str = "ds_tv"):
    """Spec nested-grid x4 occurrence cùng heading — kiểu PLI_M72 (nth).
    Prefix key theo biến thể (D2.9-A namespacing)."""
    occurrences = [{
        "occurrence_id": "%s_%02d" % (loop_prefix, i),
        "loop": "%s_%02d" % (loop_prefix, i),
        "match_heading": "5. Ngành, nghề kinh doanh",
        "nth": i,
        "sync_group": "ds_tv_demo",
        "end_markers": ["^6\\. von"],
    } for i in range(1, n_occ + 1)]
    return {
        "form_id": "PLI_M91",
        "group": "change",
        "note": "SANDBOX DEMO (test): 4 bảng lặp cùng heading, nth định vị.",
        "tables": [{
            "kind": "nested-grid",
            "pos": "after",
            "anchor": "^5\\. nganh, nghe kinh doanh",
            "no_default_drops": True,
            "drop": ["^stt ten thanh vien$", "^ma nganh\\d*$"],
            "spec": {
                "id": "ds_tv_nested_demo",
                "kind": "nested-grid",
                "semantic_key": "ds_tv_nested_demo",
                "section_id": "thanh_vien_demo",
                "stt": {"mode": "generated", "col_index": 0},
                "header_rows": NESTED_HEADERS,
                "columns": NESTED_COLUMNS,
            },
            "occurrences": occurrences,
        }],
    }


FIXED_MATRIX_SPEC = {
    "form_id": "PLI_M92",
    "group": "formation",
    "note": "SANDBOX DEMO (test): fixed-matrix dòng pháp lý + ô tổng computed.",
    "tables": [{
        "kind": "fixed-matrix",
        "pos": "after",
        "anchor": "^6\\. nguon von dieu le",
        "no_default_drops": True,
        "drop_until": "^7\\. bao hiem xa hoi",
        "drop": ["^loai nguon von$", "^so tien \\(bang so",
                 "^ty le \\(%\\)$"],
        "spec": {
            "id": "nguon_von_dieule_demo",
            "kind": "fixed-matrix",
            "semantic_key": "nguon_von_dieu_le_demo",
            "columns": [
                {"header": "Loại nguồn vốn", "tag": None,
                 "input_type": "readonly"},
                {"header": "Số tiền (bằng số; VNĐ)", "tag": "so_tien_vnd",
                 "input_type": "money"},
                {"header": "Tỷ lệ (%)", "tag": "ty_le", "input_type": "percent",
                 "computed": True},
            ],
            "fixed_rows": [
                {"id": "von_nsnn", "label": "Vốn ngân sách nhà nước"},
                {"id": "von_tu_nhan", "label": "Vốn tư nhân"},
                {"id": "von_nuoc_ngoai", "label": "Vốn nước ngoài"},
                {"id": "von_khac", "label": "Vốn khác"},
                {"id": "tong_cong", "label": "Tổng cộng",
                 "output_only": True},
            ],
            "totals": [
                {"formula": "sum(so_tien_vnd)", "target_row": "tong_cong",
                 "target_tag": "so_tien_vnd"},
                {"formula": "sum(ty_le)", "target_row": "tong_cong",
                 "target_tag": "ty_le"},
            ],
        },
    }],
}

OUTPUT_TABLE_SPEC = {
    "form_id": "PLI_M93",
    "group": "change",
    "note": "SANDBOX DEMO (test): output-table giữ lưới dù không nhập gì.",
    "tables": [{
        "kind": "output-table",
        "pos": "after",
        "anchor": "^4\\. chu ky nguoi nop",
        "no_default_drops": True,
        "drop_until": "^mau so 93 ket thuc",
        "drop": ["^nguoi nop \\(ky va ghi ho ten\\)",
                 "^nguoi nhan \\(ky va ghi ho ten\\)"],
        "spec": {
            "id": "chu_ky_demo",
            "kind": "output-table",
            "semantic_key": "chu_ky_tiep_nhan_ho_so_demo",
            "grid": {"rows": 2, "cols": 1,
                     "labels": ["NGƯỜI NỘP (Ký và ghi họ tên)",
                                "NGƯỜI NHẬN (Ký và ghi họ tên)"]},
        },
    }],
}

OUTPUT_COND_SPEC = {
    "form_id": "PLI_M94",
    "group": "change",
    "note": "SANDBOX DEMO (test): output-table presence có điều kiện {?cond}.",
    "tables": [dict(OUTPUT_TABLE_SPEC["tables"][0],
                    cond_flag="co_chi_tiet_cn")],
}


NESTED_SOURCE_PARAS = ["CONG BO NOI DUNG DANG KY THANH LAP DOANH NGHIEP DEMO",
                       "Mẫu số 91"]
for _i in range(1, 5):
    NESTED_SOURCE_PARAS += [
        "(TÊN DOANH NGHIỆP LOẠI %d)" % _i,
        "5. Ngành, nghề kinh doanh",
        "STT Tên thành viên Phần vốn góp VNĐ Ngoại tệ Chữ ký12345678910",
        "6. Vốn đầu tư của chủ sở hữu:",
    ]

FIXED_MATRIX_SOURCE_PARAS = [
    "GIAY DE NGHI DANG KY DOANH NGHIEP DEMO MAU 92",
    "Mẫu số 92",
    "6. Nguồn vốn điều lệ:",
    "Loại nguồn vốn",
    "Số tiền (bằng số; VNĐ)",
    "Tỷ lệ (%)",
    "Vốn ngân sách nhà nước",
]
for _i in range(4):
    FIXED_MATRIX_SOURCE_PARAS += [None, None]
FIXED_MATRIX_SOURCE_PARAS += [
    "Vốn tư nhân", None, None,
    "Vốn nước ngoài", None, None,
    "Vốn khác", None, None,
    "Tổng cộng", None, None,
    "7. Bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp:",
    "Ghi chú kỹ thuật vùng kế bên phải sống sót nguyên vẹn.",
]

OUTPUT_TABLE_SOURCE_PARAS = [
    "GIAY XAC NHAN NHAN HO SO DEMO MAU 93",
    "Mẫu số 93",
    "4. Chữ ký người nộp hồ sơ và người nhận hồ sơ:",
    "NGƯỜI NỘP (Ký và ghi họ tên)",
    "NGƯỜI NHẬN (Ký và ghi họ tên)",
    "Mẫu số 93 kết thúc ở đây để đảm bảo content phía sau còn nguyên.",
]


# ---------------------------------------------------------------------------
# [ID] deep idempotency
# ---------------------------------------------------------------------------

@check("[ID1] nested-grid x4 occurrence: hash lan 1 == lan 2 (template+blocks)")
def id_nested_occurrence(sandbox: dict):
    write_spec(sandbox, "PLI_M91", nested_occ_spec())
    write_source(sandbox, 91, NESTED_SOURCE_PARAS)
    meta1, tpl1 = run_generation("PLI_M91", 91, sandbox)
    h_tpl_1 = template_hash(tpl1)
    h_blk_1 = blocks_hash(convert_blocks(tpl1, "PLI_M91", meta1))
    tables_1 = table_signature(tpl1)

    meta2, tpl2 = run_generation("PLI_M91", 91, sandbox)
    h_tpl_2 = template_hash(tpl2)
    h_blk_2 = blocks_hash(convert_blocks(tpl2, "PLI_M91", meta2))
    assert h_tpl_1 == h_tpl_2, \
        "template hash khác nhau giữa 2 lần chạy: %s vs %s" % (h_tpl_1[:12],
                                                               h_tpl_2[:12])
    assert h_blk_1 == h_blk_2, "blocks hash khác nhau giữa 2 lần chạy"
    assert len(tables_1) == 4, "kỳ vọng đúng 4 bảng (mỗi occurrence 1 bảng), " \
                               "thấy %d" % len(tables_1)
    loops = sorted(re.findall(r"\{#(ds_tv_\d+)\}",
                              "\n".join(c for rows in tables_1 for row in rows
                                        for c in row)))
    assert loops == ["ds_tv_01", "ds_tv_02", "ds_tv_03", "ds_tv_04"], \
        "prefix key theo biến thể bị lệch: %s" % loops
    for width in physical_widths(tpl1):
        assert width == 5, \
            "làm phẳng mất cột: gridCol=%d kỳ vọng 5 (STT + 4 cột dữ liệu)" % width


@check("[ID2] fixed-matrix: hash lan 1 == lan 2; dong tong/co nhap dung vi tri")
def id_fixed_matrix(sandbox: dict):
    write_spec(sandbox, "PLI_M92", FIXED_MATRIX_SPEC)
    write_source(sandbox, 92, FIXED_MATRIX_SOURCE_PARAS, trailing_table=True)
    meta1, tpl1 = run_generation("PLI_M92", 92, sandbox)
    h1, blk1 = template_hash(tpl1), convert_blocks(tpl1, "PLI_M92", meta1)

    meta2, tpl2 = run_generation("PLI_M92", 92, sandbox)
    h2 = template_hash(tpl2)
    assert h1 == h2, "template hash lệch giữa hai lần chạy"
    assert blocks_hash(blk1) == blocks_hash(
        convert_blocks(tpl2, "PLI_M92", meta2)), "blocks hash lệch"

    specs = meta1.get("section_specs") or []
    assert len(specs) == 1 and specs[0]["kind"] == "fixed-matrix"
    sem = specs[0]["semantic_key"]
    keys = [f["key"] for f in meta1["fields"]]
    assert ("nguon_von_dieu_le_demo.tong_cong.so_tien_vnd" not in keys), \
        "ô tổng KHÔNG được đăng ký làm field người dùng: %s" % keys
    editable = [k for k in keys if k.startswith(sem + ".")]
    assert editable and all(not k.startswith("%s.tong_cong." % sem)
                            for k in editable), \
        "fields phải loại trừ dòng tổng: %s" % editable
    # JOIN table_index <-> block thứ tự của các block dạng bảng
    blk2 = convert_blocks(tpl2, "PLI_M92", meta2)
    tbl_blocks = [b for b in blk2["blocks"] if b.get("t") in ("table", "loop")]
    idx = specs[0]["table_index"]
    assert idx < len(tbl_blocks), \
        "table_index %d vượt số block bảng %d" % (idx, len(tbl_blocks))
    got_head = "".join(r.get("text", "")
                       for r in tbl_blocks[idx]["rows"][0]["cells"][0]["runs"])
    assert "Loại nguồn vốn".lower() in got_head.lower(), \
        "block tại table_index không phải fixed-matrix: %r" % got_head


@check("[ID3] output-table: hash giua 2 lan giong; grid GIU du block 'table'")
def id_output_table(sandbox: dict):
    write_spec(sandbox, "PLI_M93", OUTPUT_TABLE_SPEC)
    write_source(sandbox, 93, OUTPUT_TABLE_SOURCE_PARAS)
    meta1, tpl1 = run_generation("PLI_M93", 93, sandbox)
    h1, blk1 = template_hash(tpl1), convert_blocks(tpl1, "PLI_M93", meta1)
    meta2, tpl2 = run_generation("PLI_M93", 93, sandbox)
    assert h1 == template_hash(tpl2), "template hash lệch giữa hai lần chạy"
    assert blocks_hash(blk1) == blocks_hash(
        convert_blocks(tpl2, "PLI_M93", meta2)), "blocks hash lệch"
    out_tables = [b for b in blk1["blocks"] if b.get("t") == "table"]
    assert len(out_tables) == 1, "kỳ vọng đúng 1 block output-table"
    text_rows = []
    n_inputs = 0
    for row in out_tables[0]["rows"]:
        for cell in row["cells"]:
            text_rows.append(
                "".join(r.get("text", "") for r in cell.get("runs", [])))
            n_inputs += sum(1 for r in cell.get("runs", []) if "input" in r)
    assert n_inputs == 0, "output-table KHÔNG được sinh input"
    assert any("NGƯỜI NỘP" in t for t in text_rows), \
        "mất label hàng 1: %s" % text_rows
    assert any("NGƯỜI NHẬN" in t for t in text_rows), \
        "mất label hàng 2: %s" % text_rows


@check("[ID4] cond_flag: cặp marker cân đối vĩnh viễn sau khi rebuild")
def id_cond_wrapping(sandbox: dict):
    write_spec(sandbox, "PLI_M94", OUTPUT_COND_SPEC)
    write_source(sandbox, 94, OUTPUT_TABLE_SOURCE_PARAS)
    meta, tpl = run_generation("PLI_M94", 94, sandbox)
    texts = body_texts(tpl)
    markers = [t for t in texts if re.fullmatch(r"\{[/?][A-Za-z0-9_]+\}", t)]
    assert markers == ["{?co_chi_tiet_cn}", "{/co_chi_tiet_cn}"], \
        "marker điều kiện phải là 1 cặp đúng thứ tự, thấy %s" % markers
    convert_blocks(tpl, "PLI_M94", meta)  # blocks phải ra không lỗi


@check("[ID5] kind list PRODUCTION (PLI_M01): hanh vi khong troi vs artifact commit")
def id_legacy_form_no_drift(sandbox: dict):
    # copy NGUỒN THẬT và spec thật của PLI_M01 vào sandbox để chạy đúng
    # pipeline như production (spec "list" phải đọc được qua loader)
    src_dir = ROOT / "06_ho_kinh_doanh_va_chuyen_doi" / "02_chuyen_doi_hkd_sang_dn"
    sources = sorted(src_dir.glob("DN_PL1_Mau_01_*.docx"))
    assert sources, "không tìm thấy nguồn PLI_M01 trong repo"
    shutil.copy2(sources[0], sandbox["root"] / SOURCE_DIR_NAME / sources[0].name)
    real_spec_dir = ROOT / "tools" / "form_specs"
    for group_dir in sorted(p for p in real_spec_dir.iterdir() if p.is_dir()):
        dst = sandbox["specs"] / group_dir.name
        dst.mkdir(parents=True, exist_ok=True)
        for jf in sorted(group_dir.glob("*.json")):
            shutil.copy2(jf, dst / jf.name)
    meta1, tpl1 = run_generation("PLI_M01", 1, sandbox)
    meta2, tpl2 = run_generation("PLI_M01", 1, sandbox)
    assert template_hash(tpl1) == template_hash(tpl2), \
        "hash template PLI_M01 lệch giữa hai lần chạy"
    committed_tpl = ROOT / "app" / "templates" / "PLI_M01.docx"
    assert template_hash(committed_tpl) == template_hash(tpl1), \
        "template sinh ra khác artifact đang commit (drift hành vi list)"
    prod_blocks = json.loads(
        (ROOT / "app" / "data" / "blocks" / "PLI_M01.json").read_text(
            encoding="utf-8"))
    fresh = convert_blocks(tpl1, "PLI_M01", meta1)
    del fresh["ten_mau"], prod_blocks["ten_mau"]
    assert blocks_hash(fresh) == blocks_hash(prod_blocks), \
        "blocks PLI_M01 sinh lại khác artifact đang commit"


@check("[ID7] mau dung khai bao inline REBUILD_TABLES (PLI_M10): khong troi")
def id_inline_rebuild_no_drift(sandbox):
    src_dir = ROOT / "06_ho_kinh_doanh_va_chuyen_doi" / "02_chuyen_doi_hkd_sang_dn"
    sources = sorted(src_dir.glob("DN_PL1_Mau_10_*.docx"))
    assert sources, "không tìm thấy nguồn PLI_M10 trong repo"
    shutil.copy2(sources[0], sandbox["root"] / SOURCE_DIR_NAME / sources[0].name)
    meta1, tpl1 = run_generation("PLI_M10", 10, sandbox)
    meta2, tpl2 = run_generation("PLI_M10", 10, sandbox)
    assert template_hash(tpl1) == template_hash(tpl2), \
        "hash template PLI_M10 lệch giữa hai lần chạy"
    committed_tpl = ROOT / "app" / "templates" / "PLI_M10.docx"
    assert template_hash(committed_tpl) == template_hash(tpl1), \
        "mẫu dùng REBUILD_TABLES inline bị đổi hành vi sau khi thêm 3 kind"


@check("[ID6] boundary an toan: khong xoa paragraph bang ke tiep")
def id_boundary_next_section(sandbox: dict):
    write_spec(sandbox, "PLI_M92", FIXED_MATRIX_SPEC)
    write_source(sandbox, 92, FIXED_MATRIX_SOURCE_PARAS, trailing_table=True)
    meta, tpl = run_generation("PLI_M92", 92, sandbox)
    texts = body_texts(tpl)

    folded = [table_occurrences.fold_text(t) for t in texts]
    assert any(t.startswith("7. bao hiem xa hoi") for t in folded), \
        "heading mục 7 (bảng kế) bị xóa: %s" % texts
    sig = table_signature(tpl)
    static = [rows for rows in sig
              if any("BẢNG KẾ" in c for row in rows for c in row)]
    assert static, "w:tbl tĩnh phía sau bị mất sau rebuild"
    assert any("Ghi chú kỹ thuật vùng kế bên" in t for t in texts), \
        "paragraph sau heading mục 7 bị mất"


# ---------------------------------------------------------------------------
# [NEG] negative mutations
# ---------------------------------------------------------------------------

def mutant_template(tpl: Path, dest: Path, mutator) -> Path:
    """Lưu bản mutant vào tmp KHÔNG đụng template gốc."""
    doc = Document(str(tpl))
    mutator(doc)
    doc.save(str(dest))
    return dest


@check("[NEG1] thieu marker {#loop}: bat CAU TRUC lech (GridSpecMismatch)")
def neg_missing_loop_marker(sandbox: dict):
    def strip_open_marker(doc):
        for child in doc.element.body.iter(qn("w:t")):
            if child.text and "{#ds_tv_01}" in child.text:
                child.text = child.text.replace("{#ds_tv_01}", "")
                return
        raise AssertionError("fixture không còn marker loop để mutation")

    meta, tpl = run_generation("PLI_M91", 91, sandbox)
    bad = mutant_template(tpl, tpl.parent / "mutant_missing_loop.docx",
                          strip_open_marker)
    raised = None
    try:
        convert_blocks(bad, "PLI_M91", meta)
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, dxtb.GridSpecMismatch), \
        "mutation thiếu marker phải bị bắt bằng GridSpecMismatch, nhận %r" \
        % (raised,)


@check("[NEG2] THUA hang khuon (loop lap 2 lan trong cung bang): bat loud")
def neg_duplicate_loop_marker(sandbox: dict):
    def duplicate_template_row(doc):
        for child in doc.element.body.iterchildren():
            if child.tag != qn("w:tbl"):
                continue
            if "{#ds_tv_01}" not in "".join(
                    t.text or "" for t in child.iter(qn("w:t"))):
                continue
            tr_list = child.tr_lst
            clone = tr_list[-1]
            import copy as copy_mod
            dup = copy_mod.deepcopy(clone)
            clone.addnext(dup)
            return
        raise AssertionError("không thấy bảng cần mutation")

    meta, tpl = run_generation("PLI_M91", 91, sandbox)
    bad = mutant_template(tpl, tpl.parent / "mutant_dup_loop.docx",
                          duplicate_template_row)
    raised = None
    try:
        convert_blocks(bad, "PLI_M91", meta)
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, dxtb.GridSpecMismatch), \
        "bảng chứa 2 hàng khuôn cùng tên phải bị bắt loud, nhận %r" % (raised,)
    assert "đúng 1 hàng khuôn" in str(raised), \
        "thông báo phải nói rõ nguyên nhân lặp hàng khuôn: %s" % raised


@check("[NEG3] the du lieu SAI VI TRI vat ly: GridSpecMismatch")
def neg_misplaced_total_tag(sandbox: dict):
    meta, tpl = run_generation("PLI_M92", 92, sandbox)

    def swap_tags(doc):
        swapped = {
            "{nguon_von_dieu_le_demo.von_tu_nhan.so_tien_vnd}":
                "{nguon_von_dieu_le_demo.von_nuoc_ngoai.so_tien_vnd}",
        }
        done = False
        for child in doc.element.body.iter(qn("w:t")):
            if child.text and child.text.strip() in swapped:
                child.text = swapped[child.text.strip()]
                done = True
        assert done, "không tìm thấy the để mutation"

    bad = mutant_template(tpl, tpl.parent / "mutant_swap_tag.docx", swap_tags)
    raised = None
    try:
        convert_blocks(bad, "PLI_M92", meta)
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, dxtb.GridSpecMismatch), \
        "the ở sai cột vật lý phải bị bắt, nhận %r" % (raised,)
    assert "von_nuoc_ngoai" in str(raised) or "có the" in str(raised), \
        "thông báo phải nêu chi tiết ô lỗi: %s" % raised


@check("[NEG4] mat rowspan header (lam phang): GridSpecMismatch")
def neg_flattened_header(sandbox: dict):
    meta, tpl = run_generation("PLI_M91", 91, sandbox)

    def unmerge_header(doc):
        touched = 0
        for child in doc.element.body.iterchildren():
            if child.tag != qn("w:tbl"):
                continue
            for ri in (0, 1):  # cả ô gốc lẫn ô nối dọc (vMerge continue)
                tr = child.tr_lst[ri]
                for tc in tr.iterchildren():
                    if tc.tag != qn("w:tc"):
                        continue
                    tc_pr = tc.find(qn("w:tcPr"))
                    if tc_pr is None:
                        continue
                    vm = tc_pr.find(qn("w:vMerge"))
                    if vm is not None:
                        tc_pr.remove(vm)
                        touched += 1
            assert touched >= 5, \
                "fixture mất sẵn rowspan để mutation (chỉ bóc %d)" % touched
            return
        raise AssertionError("không thấy bảng nested để mutation")

    bad = mutant_template(tpl, tpl.parent / "mutant_flat_header.docx",
                          unmerge_header)
    raised = None
    try:
        convert_blocks(bad, "PLI_M91", meta)
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert isinstance(raised, dxtb.GridSpecMismatch), \
        "làm phẳng header phải bị bắt (rowspan/tiling lệch), nhận %r" % (raised,)


@check("[NEG5] thieu marker dong {/cond}: convert + render deu FAIL LOUD")
def neg_unbalanced_cond(sandbox: dict):
    from tools.docx_render import CondTagError, render
    meta, tpl = run_generation("PLI_M94", 94, sandbox)

    def drop_close(doc):
        removed = False
        for para_el in list(doc.element.body.iter(qn("w:p"))):
            texts = [t for t in para_el.iter(qn("w:t"))]
            if len(texts) == 1 and texts[0].text == "{/co_chi_tiet_cn}":
                para_el.getparent().remove(para_el)
                removed = True
        assert removed, "không thấy marker đóng để mutation"

    bad = mutant_template(tpl, tpl.parent / "mutant_no_close.docx", drop_close)
    err_conv = err_render = None
    try:
        convert_blocks(bad, "PLI_M94", meta)
    except Exception as exc:  # noqa: BLE001
        err_conv = exc
    try:
        render(str(bad), {"co_chi_tiet_cn": "X"})
    except Exception as exc:  # noqa: BLE001
        err_render = exc
    assert err_conv is not None or err_render is not None, \
        "thiếu marker đóng phải fail loud ở converter hoặc engine"
    if err_render is not None:
        assert isinstance(err_render, CondTagError), \
            "engine phải raise CondTagError, nhận %r" % (err_render,)


@check("[NEG6] region occ nhieu/nhiem: SKIP co kiem soat, KHONG chen bang lung")
def neg_contaminated_region(sandbox: dict):
    spec = nested_occ_spec(n_occ=4)
    # yêu cầu 5 occurrence trong khi nguồn chỉ có 4 heading -> nth=5 SKIP
    extra = dict(spec["tables"][0]["occurrences"][0])
    extra.update({"occurrence_id": "ds_tv_05", "loop": "ds_tv_05", "nth": 5})
    spec["tables"][0]["occurrences"].append(extra)
    paras = list(NESTED_SOURCE_PARAS)
    # chèn dấu hiệu nhiễm MỘT dòng SAU heading của lần xuất hiện thứ 2 -> nằm
    # trong vùng occ thứ hai nên bảng đó phải bị SKIP có kiểm soát.
    heading_idx = [i for i, t in enumerate(paras)
                   if t.startswith("5. Ngành, nghề kinh doanh")]
    assert len(heading_idx) >= 2, "fixture cần >=2 heading để chèn nhiễu"
    paras.insert(heading_idx[1] + 1, "Mẫu số 88 (nhiễm mẫu khác)")
    write_spec(sandbox, "PLI_M91", spec)
    write_source(sandbox, 91, paras)
    meta, tpl = run_generation("PLI_M91", 91, sandbox)
    sig = table_signature(tpl)
    assert len(sig) <= 3, \
        "SKIP phải chặn vùng nhiễm — còn %d bảng (kỳ vọng <=3)" % len(sig)
    joined = "\n".join(c for rows in sig for row in rows for c in row)
    assert "{#ds_tv_05}" not in joined, "occurrence SKIP vẫn được chèn bảng"
    assert "{#ds_tv_01}" in joined, "mất bảng ở vùng sạch thứ nhất"


@check("[NEG7] boundary drop_until KHÔNG nuốt paragraph bảng kế")
def neg_drop_scope_respects_until(sandbox: dict):
    write_spec(sandbox, "PLI_M92", FIXED_MATRIX_SPEC)
    write_source(sandbox, 92, FIXED_MATRIX_SOURCE_PARAS, trailing_table=True)
    meta, tpl = run_generation("PLI_M92", 92, sandbox)
    texts = body_texts(tpl)
    tail = "\n".join(texts[-3:])
    assert "7. Bảo hiểm xã hội" in tail, \
        "vùng drop ăn vượt drop_until tới heading mục 7: %r" % texts[-3:]
    assert "Ghi chú kỹ thuật vùng kế bên" in "\n".join(texts), \
        "paragraph sau heading mục 7 bị mất"


# ---------------------------------------------------------------------------
# [SCH] contract file tools/form_specs/schema/table_kinds.schema.json
# ---------------------------------------------------------------------------

SCHEMA_PATH = ROOT / "tools" / "form_specs" / "schema" / "table_kinds.schema.json"


@check("[SCH1] schema v1: moi example khai bao deu di qua duoc validator")
def sch_examples_valid(sandbox):
    assert SCHEMA_PATH.exists(), "thiếu contract table_kinds.schema.json"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    examples = schema.get("examples") or {}
    for kind in ("fixed-matrix", "nested-grid", "output-table"):
        entry = examples.get(kind)
        assert isinstance(entry, dict), "schema thiếu example cho %s" % kind
        spec = bfm._json_spec(entry["spec"], "PLI_SCHEMA_DEMO")
        assert spec["kind"] == kind
        del spec
    # legal_status hợp lệ phải được chấp nhận ở tầng entry
    raw_entry = dict(examples["output-table"])
    bfm._validate_legal_status(raw_entry, "PLI_SCHEMA_DEMO", "chu_ky_demo")
    del sandbox


@check("[SCH2] schema drift: truong le/sai kieu phai bi VALIDATOR chan")
def sch_schema_drift_rejected(sandbox):
    cases = [
        # header_rows sai kiểu (camelCase lạ) -> bị từ chối
        ({"id": "x", "kind": "nested-grid", "semantic_key": "k_x",
          "headerRows": [[{"text": "STT"}]],
          "columns": [{"header": "A", "tag": "a", "col_index": 0}]},
         "nested-grid với headerRows camelCase"),
        # col_index trùng nhau -> bị từ chối
        ({"id": "y", "kind": "nested-grid", "semantic_key": "k_y",
          "stt": {"mode": "none"},
          "header_rows": [[{"text": "A"}, {"text": "B"}]],
          "columns": [{"header": "A", "tag": "a", "col_index": 0},
                      {"header": "B", "tag": "b", "col_index": 0}]},
         "nested-grid col_index trùng"),
        # totals khác rỗng ở nested -> bị từ chối (v1)
        ({"id": "z", "kind": "nested-grid", "semantic_key": "k_z",
          "stt": {"mode": "none"},
          "header_rows": [[{"text": "A"}]],
          "columns": [{"header": "A", "tag": "a", "col_index": 0}],
          "totals": [{"formula": "sum(a)", "target": "r1"}]},
         "nested-grid có totals"),
        # fixed-matrix: target_row không output_only -> bị từ chối
        ({"id": "w", "kind": "fixed-matrix", "semantic_key": "k_w",
          "columns": [{"header": "T", "tag": "tien", "input_type": "money"}],
          "fixed_rows": [{"id": "r1", "label": "Dòng 1"}],
          "totals": [{"formula": "sum(tien)", "target_row": "r1",
                      "target_tag": "tien"}]},
         "fixed-matrix dòng tổng thiếu output_only"),
        # output-table có cột input -> bị từ chối
        ({"id": "v", "kind": "output-table", "semantic_key": "k_v",
          "grid": {"rows": 1, "cols": 1, "labels": ["Ký"]},
          "columns": [{"header": "X", "tag": "ten"}]},
         "output-table khai columns"),
    ]
    for raw, what in cases:
        raised = None
        try:
            bfm._json_spec(raw, "PLI_SCHEMA_DEMO")
        except ValueError as exc:
            raised = exc
        assert isinstance(raised, ValueError), \
            "%s phải bị validator chặn, nhưng vẫn được chấp nhận" % what


@check("[SCH3] kind khong hop le + occurrence sai nth: chan som o loader")
def sch_kind_and_nth_guard(sandbox):
    write_spec(sandbox, "PLI_M95", {
        "form_id": "PLI_M95",
        "tables": [{"kind": "editable-grid", "anchor": "^a",
                    "spec": {"id": "s", "semantic_key": "s"}}],
    })
    write_source(sandbox, 95, ["demo"])
    raised = None
    try:
        run_generation("PLI_M95", 95, sandbox)
    except ValueError as exc:
        raised = exc
    assert raised is not None and "kind khong hop le" in str(raised), \
        "kind lạ phải bị loader chặn trước khi sửa document, nhận %r" % (raised,)

    # nested-grid dùng occurrences nhưng bỏ sót nth=2 -> chặn
    spec = nested_occ_spec(n_occ=4)
    occs = spec["tables"][0]["occurrences"]
    del occs[2]  # còn nth 1,2,4 -> thiếu lần xuất hiện thứ 3
    write_spec(sandbox, "PLI_M91", spec)
    write_source(sandbox, 91, NESTED_SOURCE_PARAS)
    raised = None
    try:
        run_generation("PLI_M91", 91, sandbox)
    except ValueError as exc:
        raised = exc
    assert raised is not None and "nth phai lien tu" in str(raised), \
        "nth không liên tục phải bị chặn sớm, nhận %r" % (raised,)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    sandbox = new_sandbox()
    saved = apply_sandbox(sandbox)
    tests = [
        lambda: id_nested_occurrence(sandbox),
        lambda: id_fixed_matrix(sandbox),
        lambda: id_output_table(sandbox),
        lambda: id_cond_wrapping(sandbox),
        lambda: id_legacy_form_no_drift(sandbox),
        lambda: id_inline_rebuild_no_drift(sandbox),
        lambda: id_boundary_next_section(sandbox),
        lambda: neg_missing_loop_marker(sandbox),
        lambda: neg_duplicate_loop_marker(sandbox),
        lambda: neg_misplaced_total_tag(sandbox),
        lambda: neg_flattened_header(sandbox),
        lambda: neg_unbalanced_cond(sandbox),
        lambda: neg_contaminated_region(sandbox),
        lambda: neg_drop_scope_respects_until(sandbox),
        lambda: sch_examples_valid(sandbox),
        lambda: sch_schema_drift_rejected(sandbox),
        lambda: sch_kind_and_nth_guard(sandbox),
    ]
    try:
        for t in tests:
            t()
    finally:
        restore(saved)
        if _tmp_root is not None:
            shutil.rmtree(_tmp_root, ignore_errors=True)
    passed = sum(1 for ok, _ in _results if ok)
    failed = len(_results) - passed
    print("-" * 60)
    print("test_generator_deep_idempotency: %d PASS / %d FAIL"
          % (passed, failed))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
