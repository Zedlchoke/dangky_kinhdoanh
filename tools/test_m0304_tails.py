#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_m0304_tails.py — Lane fix-tails-m0304 (Owner P1=A, PLAN v4).

Kiểm chứng đuôi mẫu thành lập sau khi nguồn canonical đổi sang bản tách ĐẦY
ĐỦ (SOURCE_OVERRIDES trong tools/build_form_maps.py — không thuộc ownership
lane): M03 mục 8–11 (NĐDPL 8, thuế 9.1–9.9, BHXH 10, CSHHL 11) và M04 mục
10–13 (NĐDPL 10, thuế 11.1–11.9, BHXH 12, CSHHL 13). Generator tự map 124/144
fields dạng input phẳng; lane này KHÔNG đụng generator — kiểm kê + khoá cấu
trúc bằng test:

  [SRC]     nguồn canonical chứa TRỌN đuôi theo đúng cấu trúc: heading mục
            8/9/10/11 (M03) và 10/11/12/13 (M04), chỉ tiêu 9.1–9.9 / 11.1–11.9,
            3 dòng □ BHXH, câu BOT 'Có □/Không □', câu CSHHL '□ Có/□ Không'.
            Lỗi số '1.6' (thay vì 11.6) là TỰ NHIÊN của nguồn — giữ nguyên
            (không tự chế nội dung).
  [SPEC]    2 file spec của lane qua loader v1: inserts rỗng (superseded),
            anchor khớp ĐÚNG 1 paragraph nguồn, drop_until nằm SAU anchor, mọi
            drop pattern khớp >=1 paragraph trong vùng scoped và heading biên
            sống sót qua rebuild -> drop không nuốt đuôi.
  [INV]     form_maps đúng 124/144 fields; TRỌN key đuôi (slot + chk) đăng ký
            trong form_maps, có {tag} trong template và (với chk) là chk block
            trong blocks. Regen sandbox với spec hiện hành tái tạo ĐÚNG bộ
            key + label của repo (spec <-> artifact khớp, không ghi app/**).
  [TAX]     mục thuế: đủ chuỗi chỉ tiêu theo nguồn (gd./kt., ngày BĐHĐ, hạch
            toán 3 ô, năm tài chính, lao động, BOT cặp Có/Không, GTGT 4 ô)
            theo đúng THỨ TỰ, nhãn chk khớp nguyên văn nguồn.
  [BHXH]    đúng 3 glyph □ -> 3 key riêng biệt chk_bc_hang_thang /
            bc_03_thang / bc_06_thang, nhãn khớp nguyên văn nguồn, đúng thứ
            tự, mỗi key xuất hiện đúng 1 lần trong template.
  [CSHL]    câu hỏi 'Doanh nghiệp có chủ sở hữu hưởng lợi không?' có cặp
            'Có □ Không □' RIÊNG trên nguồn và trong template là 2 ô thật
            đứng ngay sau câu hỏi. HẠN CHẾ ĐÃ BIẾT (generator-level, ngoài
            ownership lane): key chk_co/chk_khong dùng chung với cặp BOT
            9.8/11.8 vì process_checkboxes chỉ repair trùng key TRONG CÙNG
            paragraph (Pha B) — hai câu nằm ở 2 paragraph khác nhau nên cùng
            key. Sửa đúng chỗ cần Lead đụng generator (tách pair theo vùng);
            khi đó assert đếm == 2 của suite này sẽ báo đổi để cập nhật
            KNOWN_DUP_CHK.
  [DUP]     không có key chk TRÙNG MỚI: tập key {tag} xuất hiện >1 lần trong
            template phải BẰNG CHÍNH XÁC allowlist 6 key đã biết (4 chk_gt_*
            của 2 khối chuyển đổi mục 1 — tiền lệ TRƯỚC lane, chk_co/
            chk_khong cặp BOT+CSHL như trên), mỗi key đúng 2 lần. Key
            chk_auto_* phải duy nhất toàn form.
  [RENDER]  render toàn bộ template qua docx_render.write_rendered với payload
            đủ key (chk='X') -> KHÔNG token nào sót ({a}, {#loop}, {?flag},
            {_stt}) trên document/header/footer; file render mở được bằng
            python-docx và giá trị đuôi xuất hiện đúng chỗ.
  [GUARD]   suite không ghi đè app/templates/** hay app/data/**.

Chạy: python3 -X utf8 -m tools.test_m0304_tails   (từ root repo/worktree)
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import contextlib
import zipfile
from pathlib import Path

import docx
from docx.text.paragraph import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.build_form_maps as bfm          # noqa: E402
from tools.docx_render import LEFTOVER_RE, write_rendered  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
FORM_MAPS = ROOT / "app" / "data" / "form_maps.json"
SPEC_DIR = ROOT / "tools" / "form_specs" / "formation"

FORMS = ("PLI_M03", "PLI_M04")
FIELD_COUNT = {"PLI_M03": 124, "PLI_M04": 144}

# Heading đuôi theo NGUỒN (đã fold, không dấu). M03 mục 8-11; M04 mục 10-13.
TAIL_HEADINGS = {
    "PLI_M03": {
        "ndd": "8. nguoi dai dien theo phap luat",
        "thue": "9. thong tin dang ky thue",
        "bhxh": "10. thong tin ve viec dong bao hiem xa hoi",
        "cshl": "11. thong tin ve chu so huu huong loi",
        "chi_tieu": ["9.%d" % i for i in range(1, 10)],
        "sai_so_so": None,  # nguồn M03 đánh số 9.x đủ
    },
    "PLI_M04": {
        "ndd": "10. nguoi dai dien theo phap luat",
        "thue": "11. thong tin dang ky thue",
        "bhxh": "12. thong tin ve viec dong bao hiem xa hoi",
        "cshl": "13. thong tin ve chu so huu huong loi",
        # nguồn in '1.6' thay vì '11.6' — lỗi số của nguồn, giữ nguyên văn
        "chi_tieu": ["11.%d" % i for i in (1, 2, 3, 4, 5, 7, 8, 9)],
        "sai_so_so": ("1.6", "11.6"),
    },
}

# Key slot (input phẳng) thuộc đuôi — giống nhau ở 2 mẫu.
TAIL_SLOT_KEYS = (
    ["ndd.ho_ten", "ndd.ngay_sinh", "ndd.thang_sinh", "ndd.nam_sinh",
     "ndd.gioi_tinh", "ndd.so_cccd", "ndd.chuc_vu", "dien_thoai_lien_he"]
    + ["gd.%s" % f for f in ("ho_ten", "ngay_sinh", "thang_sinh", "nam_sinh",
                             "gioi_tinh", "so_cccd", "dien_thoai")]
    + ["kt.%s" % f for f in ("ho_ten", "ngay_sinh", "thang_sinh", "nam_sinh",
                             "gioi_tinh", "so_cccd", "dien_thoai")]
    + ["ngay_bd", "thang_bd", "nam_bd", "ap_dung_tu", "so_lao_dong"]
)
# Key chk thuộc đuôi: hạch toán (9.5/11.5) + BOT (9.8/11.8) + GTGT
# (9.9/11.9) + BHXH (10/12).
TAIL_CHK_KEYS = (
    ["chk_ht_doc_lap", "chk_ht_hop_nhat", "chk_ht_phu_thuoc",
     "chk_co", "chk_khong"]
    + ["chk_gtgt_khoan_tru", "chk_gtgt_truc_tiep_tren_gtgt",
       "chk_gtgt_truc_tiep_doanh_so", "chk_gtgt_khong_phai_nop"]
    + ["chk_bc_hang_thang", "chk_bc_03_thang", "chk_bc_06_thang"]
)

# Dãy nhãn chk vùng thuế theo THỨ TỰ xuất hiện trong blocks.
TAX_CHK_ORDER = [
    "chk_ht_doc_lap", "chk_ht_hop_nhat", "chk_ht_phu_thuoc",
    "chk_co", "chk_khong",
    "chk_gtgt_khoan_tru", "chk_gtgt_truc_tiep_tren_gtgt",
    "chk_gtgt_truc_tiep_doanh_so", "chk_gtgt_khong_phai_nop",
]
TAX_CHK_LABELS = {
    "chk_ht_doc_lap": "Hạch toán độc lập",
    "chk_ht_hop_nhat": "Có báo cáo tài chính hợp nhất",
    "chk_ht_phu_thuoc": "Hạch toán phụ thuộc",
    "chk_co": "Có", "chk_khong": "Không",
    "chk_gtgt_khoan_tru": "Khấu trừ",
    "chk_gtgt_truc_tiep_tren_gtgt": "Trực tiếp trên GTGT",
    "chk_gtgt_truc_tiep_doanh_so": "Trực tiếp trên doanh số",
    "chk_gtgt_khong_phai_nop": "Không phải nộp thuế GTGT",
}
# Nhãn 3 phương thức BHXH theo nguồn (dòng bắt đầu □).
BHXH_LABELS = ["hang thang", "03 thang mot lan", "06 thang mot lan"]
BHXH_KEYS = ["chk_bc_hang_thang", "chk_bc_03_thang", "chk_bc_06_thang"]
BHXH_LABELS_RAW = ["Hàng tháng", "03 tháng một lần", "06 tháng một lần"]

CSHL_QUESTION = "doanh nghiep co chu so huu huong loi khong"

# Allowlist key chk trùng (xuất hiện đúng 2 lần trong template) — đã biết và
# được thừa nhận: 4 chk_gt_* (2 khối "Loại giấy tờ pháp lý" ở mục 1, tiền lệ
# TRƯỚC lane) + chk_co/chk_khong (câu BOT và câu CSHHL — hạn chế
# cross-paragraph của process_checkboxes, xem docstring [CSHL]).
KNOWN_DUP_CHK = {
    "chk_gt_cmnd": 2, "chk_gt_cccd": 2, "chk_gt_ho_chieu": 2,
    "chk_gt_loai_khac": 2, "chk_co": 2, "chk_khong": 2,
}

BOX_RE = re.compile(r"[□☐]")


# ---------------------------------------------------------------------------
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


def _fingerprint() -> dict:
    dig = {}
    for sub in ("templates", "data"):
        d = ROOT / "app" / sub
        for p in sorted(d.rglob("*")):
            if p.is_file():
                dig[str(p.relative_to(ROOT))] = hashlib.sha256(
                    p.read_bytes()).hexdigest()
    return dig


REPO_FP_BEFORE = _fingerprint()


def fold(text: str) -> str:
    return bfm.fold(re.sub(r"\s+", " ", text)).strip()


def src_paras(form_id: str) -> list[str]:
    doc = docx.Document(str(bfm.find_source(form_id)))
    return [p.text for p in doc.paragraphs]


def folds(form_id: str) -> list[str]:
    return [fold(t) for t in src_paras(form_id)]


def blocks_json(form_id: str) -> dict:
    return json.loads((BLOCKS_DIR / ("%s.json" % form_id)).read_text(
        encoding="utf-8"))


def chk_blocks(form_id: str) -> list[dict]:
    return [b for b in blocks_json(form_id)["blocks"] if b.get("t") == "chk"]


def para_texts(form_id: str) -> list[str]:
    """Text các block paragraph (t='p') trong blocks JSON."""
    out = []
    for b in blocks_json(form_id)["blocks"]:
        if b.get("t") != "p":
            continue
        out.append("".join(r.get("text", "") for r in b.get("runs", [])))
    return out


def form_maps_entry(form_id: str) -> dict:
    return json.loads(FORM_MAPS.read_text(encoding="utf-8"))[form_id]


def form_maps_keys(form_id: str) -> set[str]:
    return {f["key"] for f in form_maps_entry(form_id)["fields"]}


def tpl_path(form_id: str) -> Path:
    return ROOT / "app" / "templates" / ("%s.docx" % form_id)


def tpl_paras(form_id: str) -> list[str]:
    doc = docx.Document(str(tpl_path(form_id)))
    return [Paragraph(el, doc).text for el in doc.element.body.iterchildren()
            if el.tag.endswith("}p")]


def tpl_tag_counts(form_id: str) -> dict[str, int]:
    """Đếm occurrence của mọi {tag} trong word/document.xml của template."""
    with zipfile.ZipFile(tpl_path(form_id)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    counts: dict[str, int] = {}
    for m in re.finditer(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}", xml):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def spec_raw(form_id: str) -> str:
    return (SPEC_DIR / ("%s.json" % form_id)).read_text(encoding="utf-8-sig")


def load_spec_quiet(form_id: str):
    bfm._form_spec_cache.pop(form_id, None)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return bfm.load_form_spec(form_id)
        finally:
            pass


def sandbox_build(form_id: str) -> tuple[dict, Path]:
    """process_form THẬT với spec hiện hành trong sandbox tmp (không ghi
    app/**). Trả về (meta, đường dẫn template sandbox)."""
    tmp = Path(tempfile.mkdtemp(prefix="tails_sandbox_"))
    (tmp / "t").mkdir(parents=True, exist_ok=True)
    (tmp / "d").mkdir(parents=True, exist_ok=True)
    grp = tmp / "formation"
    grp.mkdir(parents=True, exist_ok=True)
    (grp / ("%s.json" % form_id)).write_text(spec_raw(form_id),
                                             encoding="utf-8")
    saved = (bfm.OUT_TPL, bfm.OUT_DATA, bfm.FORM_SPECS_DIR)
    bfm.OUT_TPL, bfm.OUT_DATA, bfm.FORM_SPECS_DIR = tmp / "t", tmp / "d", tmp
    bfm._form_spec_cache.clear()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            meta, _unmatched = bfm.process_form(
                bfm.find_source(form_id), {}, None)
        tpl = tmp / "t" / ("%s.docx" % form_id)
        assert tpl.exists(), "generator chưa ghi template vào sandbox"
        return meta, tpl
    finally:
        (bfm.OUT_TPL, bfm.OUT_DATA, bfm.FORM_SPECS_DIR) = saved
        bfm._form_spec_cache.clear()
        shutil.rmtree(tmp, ignore_errors=True)


def block_index_of(form_id: str, folded_prefix: str, texts: list[str]) -> int:
    """Chỉ số block paragraph đầu tiên có text folded startswith prefix."""
    for i, t in enumerate(texts):
        if fold(t).startswith(folded_prefix):
            return i
    raise AssertionError("%s: không tìm thấy block %r" % (form_id,
                                                          folded_prefix))


# ---------------------------------------------------------------------------
@check("[SRC] nguon canonical du duoi: heading muc + chi tieu 9.x/11.x + glyph")
def t_source_tail():
    for fid in FORMS:
        tf = folds(fid)
        h = TAIL_HEADINGS[fid]
        order = [h["ndd"], h["thue"], h["bhxh"], h["cshl"]]
        idx = []
        for mark in order:
            hits = [i for i, t in enumerate(tf) if t.startswith(mark)]
            assert hits, "%s: nguồn thiếu heading %r" % (fid, mark)
            assert len(hits) == 1, \
                "%s: heading %r xuất hiện %d lần" % (fid, mark, len(hits))
            idx.append(hits[0])
        assert idx == sorted(idx), "%s: thứ tự mục đuôi lệch: %s" % (fid, idx)
        # chỉ tiêu 9.1..9.9 / 11.1..11.9 (trừ chỉ tiêu lỗi số) trong vùng thuế
        for ct in h["chi_tieu"]:
            assert any(t == ct for t in tf[idx[1]:idx[2]]), \
                "%s: thiếu chỉ tiêu %r trong vùng mục thuế" % (fid, ct)
        # lỗi số của nguồn (M04: '1.6' thay vì '11.6') — giữ nguyên văn
        if h["sai_so_so"]:
            sai, dung = h["sai_so_so"]
            assert any(t == sai for t in tf[idx[1]:idx[2]]), \
                "%s: nguồn đã sửa %r -> %r? cập nhật TAIL_HEADINGS" % (
                    fid, sai, dung)
            assert not any(t == dung for t in tf[idx[1]:idx[2]]), \
                "%s: nguồn xuất hiện %r — evidence lỗi số hết hiệu lực" % (
                    fid, dung)
        # 3 dòng □ BHXH (glyph đứng TRƯỚC nhãn) trong vùng mục BHXH
        bh = [t for t in tf[idx[2]:idx[3]] if BOX_RE.search(t)]
        for lbl in BHXH_LABELS:
            assert any(t.startswith("□") and lbl in t for t in bh), \
                "%s: dòng □ %r không có trong vùng BHXH nguồn" % (fid, lbl)
        # câu BOT: 'Có □' và 'Không □' (glyph đứng SAU nhãn) trong mục thuế
        thue_zone = tf[idx[1]:idx[2]]
        assert any(t == "co □" for t in thue_zone), \
            "%s: không có dòng 'Có □' (BOT) trong mục thuế" % fid
        assert any(t == "khong □" for t in thue_zone), \
            "%s: không có dòng 'Không □' (BOT) trong mục thuế" % fid
        # câu CSHHL: '□ Có' và '□ Không' ngay sau câu hỏi
        cq = next(i for i, t in enumerate(tf) if t.startswith(CSHL_QUESTION))
        tail_after = tf[cq:cq + 3]
        assert any(t == "□ co" for t in tail_after), \
            "%s: sau câu hỏi CSHHL không có '□ Có' (thấy %r)" % (
                fid, tail_after)
        assert any(t == "□ khong" for t in tail_after), \
            "%s: sau câu hỏi CSHHL không có '□ Không'" % fid
        # nguồn flatten: không còn w:tbl nào (bảng do spec tái dựng)
        assert len(docx.Document(str(bfm.find_source(fid))).tables) == 0, \
            "%s: nguồn đã có w:tbl — cấu trúc nguồn đổi, rà lại lane" % fid


@check("[SPEC] spec lane qua loader; inserts rong; anchor/drop_until/drop an toan")
def t_spec_safety():
    for fid in FORMS:
        raw = json.loads(spec_raw(fid))
        assert raw.get("inserts") == [], \
            "%s: inserts phải rỗng (superseded bởi nguồn đầy đủ)" % fid
        ext = load_spec_quiet(fid)
        assert ext and ext["entries"], "%s: loader nạp 0 entry" % fid
        tf = folds(fid)
        rebuilt = tpl_paras(fid)
        rebuilt_folds = [fold(t) for t in rebuilt]
        for ent in ext["entries"]:
            hits = [i for i, t in enumerate(tf) if re.search(ent["anchor"], t)]
            assert len(hits) == 1, \
                "%s/%s: anchor %r khớp %d paragraph nguồn" % (
                    fid, ent["spec"], ent["anchor"], len(hits))
            ai = hits[0]
            if not ent.get("drop_until"):
                continue
            ei = next((i for i, t in enumerate(tf)
                       if i > ai and re.search(ent["drop_until"], t)), None)
            assert ei is not None, \
                "%s/%s: drop_until %r không thấy sau anchor" % (
                    fid, ent["spec"], ent["drop_until"])
            zone = tf[ai:ei]
            for pat in ent.get("drop") or []:
                assert any(re.match(pat, t) for t in zone), \
                    "%s/%s: drop %r không khớp paragraph nào trong vùng" % (
                        fid, ent["spec"], pat)
            # heading biên (đầu mục kế) phải sống sót qua rebuild
            prefix = zone and tf[ei][:25]
            assert prefix is not None or not zone, fid
            if prefix:
                assert any(t.startswith(prefix) for t in rebuilt_folds), \
                    "%s/%s: heading biên %r bị nuốt khi rebuild" % (
                        fid, ent["spec"], tf[ei][:50])


@check("[INV] 124/144 fields; tron key duoi trong form_maps + template + blocks")
def t_inventory():
    for fid in FORMS:
        entry = form_maps_entry(fid)
        assert len(entry["fields"]) == FIELD_COUNT[fid], \
            "%s: form_maps có %d fields, kỳ vọng %d (đã đổi? cập nhật suite)" % (
                fid, len(entry["fields"]), FIELD_COUNT[fid])
        fm_keys = form_maps_keys(fid)
        counts = tpl_tag_counts(fid)
        blk_keys = [b["key"] for b in chk_blocks(fid)]
        missing_fm = [k for k in TAIL_SLOT_KEYS + TAIL_CHK_KEYS
                      if k not in fm_keys]
        assert not missing_fm, "%s: form_maps thiếu key đuôi %s" % (
            fid, missing_fm)
        missing_tpl = [k for k in TAIL_SLOT_KEYS + TAIL_CHK_KEYS
                       if counts.get(k, 0) < 1]
        assert not missing_tpl, "%s: template thiếu {tag} đuôi %s" % (
            fid, missing_tpl)
        missing_blk = [k for k in TAIL_CHK_KEYS if k not in blk_keys]
        assert not missing_blk, "%s: blocks thiếu chk block đuôi %s" % (
            fid, missing_blk)
        print("     %s: %d key đuôi (slot %d + chk %d) đủ trên 3 lớp"
              % (fid, len(TAIL_SLOT_KEYS) + len(TAIL_CHK_KEYS),
                 len(TAIL_SLOT_KEYS), len(TAIL_CHK_KEYS)))


@check("[INV-REGEN] sandbox regen theo spec hien hanh tai tao dung bo key/label")
def t_regen_identity():
    for fid in FORMS:
        meta, _tpl = sandbox_build(fid)
        repo = form_maps_entry(fid)
        assert [f["key"] for f in meta["fields"]] == \
            [f["key"] for f in repo["fields"]], \
            "%s: sandbox regen lệch THỨ TỰ key so với form_maps repo" % fid
        assert [f.get("label", "") for f in meta["fields"]] == \
            [f.get("label", "") for f in repo["fields"]], \
            "%s: sandbox regen lệch label so với form_maps repo" % fid
        assert (meta.get("section_specs") or []) == \
            (repo.get("section_specs") or []), \
            "%s: sandbox lệch section_specs so với repo" % fid


@check("[TAX] cau truc muc thue theo nguon: chi tieu + thu tu chk + nhan nguyen van")
def t_tax_structure():
    for fid in FORMS:
        texts = para_texts(fid)
        h = TAIL_HEADINGS[fid]
        i_thue = block_index_of(fid, h["thue"], texts)
        i_bhxh = block_index_of(fid, h["bhxh"], texts)
        # chuỗi chỉ tiêu theo đúng thứ tự nguồn: heading số, gd/kt, ngày BĐHĐ,
        # hạch toán, năm tài chính, lao động, BOT, GTGT
        cur = i_thue
        for mark, key in (
                (h["chi_tieu"][0], None),
                ("ho, chu dem va ten giam doc", "gd.ho_ten"),
                ("ngay bat dau hoat dong", "ngay_bd"),
                ("hinh thuc hach toan", None),
                ("hoat dong theo du an bot", None),
                ("phuong phap tinh thue gtgt", None),
        ):
            hit = -1
            for j in range(cur, i_bhxh):
                if mark in fold(texts[j]):
                    hit = j
                    break
            assert hit >= 0, (
                "%s: trong vùng mục thuế không thấy %r (đang cần cho key %r)"
                % (fid, mark, key))
            cur = hit + 1
        # chk vùng thuế: đủ key, đúng thứ tự tương đối như nguồn
        keys_seq = [b["key"] for b in chk_blocks(fid)]
        pos = []
        for k in TAX_CHK_ORDER:
            assert k in keys_seq, "%s: thiếu chk %s" % (fid, k)
            pos.append(keys_seq.index(k))
        assert pos == sorted(pos), \
            "%s: thứ tự chk vùng thuế lệch nguồn: %s" % (fid, TAX_CHK_ORDER)
        # nhãn chk khớp nguyên văn nguồn
        by_key = {b["key"]: b.get("label", "") for b in chk_blocks(fid)}
        for k, lbl in TAX_CHK_LABELS.items():
            assert by_key.get(k) == lbl, \
                "%s: nhãn %s = %r, kỳ vọng %r" % (fid, k, by_key.get(k), lbl)
        # gd/kt đủ 7 trường mỗi người (5 slot + ngày/tháng/ngày sinh nhóm 3)
        for pre in ("gd", "kt"):
            for suf in ("ho_ten", "ngay_sinh", "thang_sinh", "nam_sinh",
                        "gioi_tinh", "so_cccd", "dien_thoai"):
                assert "%s.%s" % (pre, suf) in form_maps_keys(fid), \
                    "%s: thiếu trường %s.%s" % (fid, pre, suf)


@check("[BHXH] dung 3 glyph □ -> 3 key rieng, dung nhan dung thu tu")
def t_bhxh():
    for fid in FORMS:
        bs = [b for b in chk_blocks(fid)
              if b.get("key", "").startswith("chk_bc_")]
        assert [b["key"] for b in bs] == BHXH_KEYS, \
            "%s: chk BHXH %s != %s" % (fid, [b["key"] for b in bs], BHXH_KEYS)
        assert [b.get("label") for b in bs] == BHXH_LABELS_RAW, \
            "%s: nhãn BHXH lệch nguyên văn nguồn" % fid
        # blocks: đúng 3 block □ trong vùng mục BHXH (không thừa glyph)
        texts = para_texts(fid)
        h = TAIL_HEADINGS[fid]
        i0 = block_index_of(fid, h["bhxh"], texts)
        i1 = block_index_of(fid, h["cshl"], texts)
        # đếm trên TOÀN blocks (p + chk) của vùng
        zone = [b for b in blocks_json(fid)["blocks"]]
        def _btext(b):
            if b.get("t") == "chk":
                return "%s %s" % ("□", b.get("label", ""))
            if b.get("t") == "p":
                return "".join(r.get("text", "") for r in b.get("runs", []))
            return ""
        p_idx = -1
        glyph = []
        for bi, b in enumerate(zone):
            t = _btext(b)
            ft = fold(t)
            if b.get("t") == "p" and ft.startswith(h["bhxh"]):
                p_idx = len(glyph)
                continue
            if b.get("t") == "p" and ft.startswith(h["cshl"]):
                break
            if p_idx >= 0 and BOX_RE.search(t):
                glyph.append(ft)
        assert len(glyph) == 3, \
            "%s: vùng BHXH blocks có %d block chứa □ (kỳ vọng 3): %r" % (
                fid, len(glyph), glyph)
        for lbl in BHXH_LABELS:
            assert any(lbl in g for g in glyph), \
                "%s: glyph BHXH thiếu nhãn %r" % (fid, lbl)
        # template: mỗi key xuất hiện đúng 1 lần (không trùng với mẫu khác)
        counts = tpl_tag_counts(fid)
        for k in BHXH_KEYS:
            assert counts.get(k) == 1, \
                "%s: {%s} xuất hiện %d lần (kỳ vọng 1)" % (
                    fid, k, counts.get(k))


@check("[CSHL] cau hoi co pair 'Có/Khong' rieng tren nguon; cap o ngay sau cau hoi")
def t_cshl():
    for fid in FORMS:
        blocks = blocks_json(fid)["blocks"]
        cb = chk_blocks(fid)
        texts = para_texts(fid)
        i_cshl = block_index_of(fid, TAIL_HEADINGS[fid]["cshl"], texts)
        i_q = block_index_of(fid, CSHL_QUESTION, texts)
        assert i_cshl < i_q, "%s: câu hỏi CSHHL đứng trước heading mục" % fid
        # đúng 2 lần chk_co (BOT + CSHHL) — lần 2 phải đứng NGAY sau câu hỏi
        i_co = [j for j, b in enumerate(cb) if b["key"] == "chk_co"]
        assert len(i_co) == 2, \
            "%s: chk_co xuất hiện %d lần (BOT + CSHHL) — lệch allowlist" % (
                fid, len(i_co))
        bot_idx, cshl_idx = i_co
        assert bot_idx < cshl_idx, \
            "%s: thứ tự 2 lần chk_co không phải BOT -> CSHHL" % fid
        # vị trí block câu hỏi -> số chk block trước nó
        q_block_pos = None
        for bi, b in enumerate(blocks):
            if b.get("t") == "p" and fold("".join(
                    r.get("text", "") for r in b.get("runs", []))
                    ).startswith(CSHL_QUESTION):
                q_block_pos = bi
                break
        assert q_block_pos is not None, "%s: mất block câu hỏi CSHHL" % fid
        n_chk_before_q = sum(1 for b in blocks[:q_block_pos]
                             if b.get("t") == "chk")
        assert cshl_idx == n_chk_before_q, \
            "%s: pair CSHHL không nằm NGAY sau câu hỏi (chk trước câu hỏi=%d, " \
            "vị trí chk_co thứ 2=%d)" % (fid, n_chk_before_q, cshl_idx)
        assert cb[cshl_idx].get("label") == "Có", \
            "%s: ô 1 pair CSHHL sai nhãn %r" % (
                fid, cb[cshl_idx].get("label"))
        assert cb[cshl_idx + 1].get("key") == "chk_khong" and \
            cb[cshl_idx + 1].get("label") == "Không", \
            "%s: pair CSHHL thiếu bên Không hoặc sai nhãn" % fid
        # template: {chk_co}/{chk_khong} đúng 2 lần (BOT + CSHHL); nếu generator
        # đã tách pair theo vùng thì con số đổi -> cập nhật KNOWN_DUP_CHK
        counts = tpl_tag_counts(fid)
        assert counts.get("chk_co") == 2 and counts.get("chk_khong") == 2, \
            "%s: {chk_co}/{chk_khong} đếm %r/%r — generator đã tách pair? " \
            "cập nhật KNOWN_DUP_CHK" % (fid, counts.get("chk_co"),
                                        counts.get("chk_khong"))


@check("[DUP] khong key chk trung MOI; dung allowlist 6 key, moi key x2")
def t_no_new_dup():
    for fid in FORMS:
        counts = tpl_tag_counts(fid)
        dups = {k: n for k, n in counts.items()
                if k.startswith("chk_") and n > 1}
        assert dups == KNOWN_DUP_CHK, \
            "%s: tập chk trùng %r != allowlist %r (có trùng MỚI hoặc đã sửa " \
            "generator -> cập nhật suite + spec note)" % (fid, dups,
                                                          KNOWN_DUP_CHK)
        # chk_auto_* phải duy nhất toàn form (sản phẩm Pha B repair)
        fm_keys = [f["key"] for f in form_maps_entry(fid)["fields"]]
        auto = [k for k in fm_keys if k.startswith("chk_auto_")]
        assert len(auto) == len(set(auto)), \
            "%s: key chk_auto_* trùng: %s" % (fid, auto)


@check("[RENDER] write_rendered payload du key -> token het; du lieu duoi dung cho")
def t_render_tokens():
    money_parts = ("von", "ty_le", "so_luong", "gia_tri", "menh_gia", "so_tien")
    for fid in FORMS:
        data: dict = {}
        for f in form_maps_entry(fid)["fields"]:
            key = f["key"]
            node = data
            parts = key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            if key.startswith("chk_"):
                node[parts[-1]] = "X"
            elif any(p in parts[-1] for p in money_parts):
                node[parts[-1]] = "7"
            else:
                node[parts[-1]] = "ND_%s" % parts[-1]
        # loop ds_nganh: nhân 1 hàng mẫu với đủ tag của loop
        data["ds_nganh"] = [{"ten_nganh": "Sản phẩm test đuôi",
                             "ma_nganh": "0111001",
                             "la_nganh_chinh": "X"}]
        out = Path(tempfile.mkdtemp(prefix="tails_render_")) / (
            "%s_rendered.docx" % fid)
        try:
            write_rendered(tpl_path(fid), data, out)
            with zipfile.ZipFile(out) as z:
                parts = [n for n in z.namelist()
                         if re.match(
                             r"word/(document\.xml|header\d*\.xml|"
                             r"footer\d*\.xml)$", n)]
                leftover = []
                for n in parts:
                    xml = z.read(n).decode("utf-8")
                    for m in LEFTOVER_RE.finditer(xml):
                        leftover.append((n, m.group(0)))
            assert not leftover, "%s: render còn token sót: %s" % (
                fid, leftover[:8])
            # đọc lại bằng python-docx: giá trị đuôi xuất hiện đúng chỗ
            doc = docx.Document(str(out))
            lines = [p.text for p in doc.paragraphs]
            for t in doc.tables:
                for row in t.rows:
                    for c in row.cells:
                        lines.extend(c.text.splitlines())
            full = "\n".join(lines)
            assert "ND_ho_ten" in full and "ND_chuc_vu" in full, \
                "%s: giá trị slot đuôi (ndd/gd/kt) không thấy trong bản render" \
                % fid
            for k, lbl in zip(BHXH_KEYS, BHXH_LABELS_RAW):
                assert any("X" in ln and lbl in ln for ln in lines), \
                    "%s: ô %s (%s) không nhận giá trị X trong bản render" % (
                        fid, k, lbl)
        finally:
            shutil.rmtree(out.parent, ignore_errors=True)


@check("[GUARD] app/templates va app/data khong bi ghi trong suot suite")
def t_guard_repo_untouched():
    after = _fingerprint()
    assert len(after) > 100, "bảng fingerprint quá nhỏ (%d)" % len(after)
    changed = [k for k in after if REPO_FP_BEFORE.get(k) != after[k]]
    added = [k for k in after if k not in REPO_FP_BEFORE]
    removed = [k for k in REPO_FP_BEFORE if k not in after]
    assert not (changed or added or removed), \
        "suite đã ghi ngoài sandbox: changed=%s added=%s removed=%s" % (
            changed[:3], added[:3], removed[:3])


_results: list[tuple[bool, str]] = []


def main() -> int:
    for fn in (t_source_tail, t_spec_safety, t_inventory, t_regen_identity,
               t_tax_structure, t_bhxh, t_cshl, t_no_new_dup,
               t_render_tokens, t_guard_repo_untouched):
        fn()
    ok = sum(1 for p, _ in _results if p)
    fail = sum(1 for p, _ in _results if not p)
    print("-" * 72)
    print("test_m0304_tails: %d PASS / %d FAIL" % (ok, fail))
    for passed, name in _results:
        if not passed:
            print("  -> %s" % name)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
