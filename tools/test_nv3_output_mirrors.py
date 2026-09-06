# -*- coding: utf-8 -*-
"""test_nv3_output_mirrors.py — [N-v3] regression bind occurrence output
"Tên doanh nghiệp" render-time (quyết định owner N-v3 2026-09-06):

  PLI_M48 p17 (thông báo sửa đổi/bổ sung — câu "về việc: … của (Tên doanh
  nghiệp) …"), PLI_M49 p9 NHÁNH doanh nghiệp hiện hữu (dòng
  "……….(Tên doanh nghiệp)………….." dưới "(Đối với các trường hợp còn lại)";
  nhánh thành lập mới dùng dữ liệu cá nhân — KHÔNG bind), PLI_M70 p14 (giấy
  tiếp nhận — câu "… về việc … của (Tên doanh nghiệp) …").

  Cơ chế: registry tools/header_name_binding.json section "output_mirrors"
  -> generator bind the {dn.ten_tieng_viet} vào template (_bind_output_mirrors,
  idempotent + fail-loud); converter biến run input cùng key thành run mirror
  (_output_mirrors_to_mirror — READ-ONLY, không input/tab-stop/draft key thứ
  hai); render thiếu canonical -> RỖNG đúng pháp định.

Kiểm định (mỗi form, trên bản regen SANDBOX — không đụng app/templates):
  (a) template có ĐÚNG 1 token, tại ĐÚNG occurrence (M49: nhánh DN; nhánh
      cá nhân và occurrence p14 "Tên Doanh nghiệp" KHÔNG có token);
  (b) blocks có ĐÚNG 1 run mirror {key} tại đúng block ngữ cảnh;
  (c) KHÔNG run input nào cùng key (read-only, không tạo input thứ hai);
  (d) sandbox render/export: draft dn.ten_tieng_viet='ABC' -> 'ABC' tại
      occurrence; draft thiếu -> trống, không sót token kỹ thuật.
  + idempotent (bind lần 2 = 0, template byte giữ nguyên) và fail-loud
    (expect sai -> ValueError).
  + [POST-REGEN] khi app/templates/app/data ĐÃ được Lead regen: lặp lại
    (a)-(c) trên artifact thật; chưa regen -> in SKIP (không fail).

Chạy:  python3 -X utf8 -m tools.test_nv3_output_mirrors
Exit 0 = PASS; exit 1 = FAIL.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import build_form_maps as bfm                 # noqa: E402
from tools import docx_render as dr                      # noqa: E402
from tools import docx_to_blocks as d2b                  # noqa: E402
from tools.layout_roles import fold                      # noqa: E402
from docx import Document                                # noqa: E402

KEY = "dn.ten_tieng_viet"
TOKEN = "{%s}" % KEY
REGISTRY = json.loads(
    (ROOT / "tools" / "header_name_binding.json").read_text(encoding="utf-8"))
FORMS = ["PLI_M48", "PLI_M49", "PLI_M70"]

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
                import traceback
                traceback.print_exc()
                _results.append((False, "%s: exception %r" % (name, exc)))
                print("FAIL %s: exception %r" % (name, exc))
        return run
    return deco


# ---------------------------------------------------------------------------
# sandbox regen: source -> template (tmp) -> blocks JSON — không đụng app/
# ---------------------------------------------------------------------------

_SANDBOX: dict[str, dict] = {}


def sandbox(fid: str) -> dict:
    """Regen 1 form vào tmp: {'tpl': Path, 'blocks': dict, 'meta': dict}."""
    if fid in _SANDBOX:
        return _SANDBOX[fid]
    titles = bfm.load_csv_titles()
    tmp = Path(tempfile.mkdtemp(prefix="nv3out-%s-" % fid))
    meta, unmatched = bfm.process_form(
        bfm.find_source(fid), titles, None, out_tpl=tmp)
    doc = Document(str(tmp / ("%s.docx" % fid)))
    data = d2b.convert_document(
        doc, fid, meta["ten_mau"],
        overrides=d2b.load_role_overrides(),
        footnotes=d2b.load_footnotes(doc),
        section_specs=meta.get("section_specs"),
    )
    _SANDBOX[fid] = {"tpl": tmp / ("%s.docx" % fid), "doc": doc,
                     "blocks": data, "meta": meta}
    return _SANDBOX[fid]


def template_token_lines(doc) -> list[str]:
    out = []
    for t in doc.element.body.iter(
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if TOKEN in (t.text or ""):
            out.append(t.text or "")
    return out


def walk_runs(blocks_json: dict):
    """Yield (block_idx, where, runs) cho p + table (bỏ (0,0) band)."""
    for bi, blk in enumerate(blocks_json["blocks"]):
        t = blk.get("t")
        if t == "p":
            yield bi, "p", blk.get("runs") or []
        elif t == "table":
            band = blk.get("band") == "header"
            for ri, row in enumerate(blk.get("rows") or []):
                for ci, cell in enumerate(row.get("cells") or []):
                    if band and ri == 0 and ci == 0:
                        continue
                    yield bi, "t r%d c%d" % (ri, ci), cell.get("runs") or []


def block_text(blk: dict) -> str:
    if blk.get("t") == "p":
        return "".join(r.get("text", "") for r in blk.get("runs") or [])
    return ""


# ---------------------------------------------------------------------------
# (a) template: đúng 1 token, đúng occurrence
# ---------------------------------------------------------------------------

def _assert_template(fid: str, doc) -> None:
    lines = template_token_lines(doc)
    assert len(lines) == 1, (
        "%s: template phải có ĐÚNG 1 token %s, thấy %d: %r"
        % (fid, TOKEN, len(lines), lines[:3]))

    if fid == "PLI_M48":
        paras = [p.text for p in doc.paragraphs if TOKEN in p.text]
        assert len(paras) == 1, "M48: token phải nằm ở 1 paragraph duy nhất"
        pf = fold(paras[0])
        assert "ve viec" in pf and "cua" in pf, (
            "M48: occurrence sai — phải là câu 'về việc: … của …', thấy %r"
            % paras[0])
        # occurrence người nhận '(Tên doanh nghiệp)' (dòng dưới 'Kính gửi:')
        # KHÔNG được bind — owner chỉ adjudicate occurrence p17
        recipient = [p.text for p in doc.paragraphs
                     if fold(p.text).startswith("(ten doanh nghiep)")]
        assert recipient, "M48: mất dòng người nhận '(Tên doanh nghiệp)'"
        assert TOKEN not in recipient[0], (
            "M48: occurrence người nhận 'Kính gửi: (Tên doanh nghiệp)' "
            "không được bind")
    elif fid == "PLI_M70":
        paras = [p.text for p in doc.paragraphs if TOKEN in p.text]
        assert len(paras) == 1, "M70: token phải nằm ở 1 paragraph duy nhất"
        pf = fold(paras[0])
        assert "ve viec" in pf, (
            "M70: occurrence sai — phải là câu '… về việc … của …', thấy %r"
            % paras[0])
    elif fid == "PLI_M49":
        paras = [p.text for p in doc.paragraphs if TOKEN in p.text]
        assert len(paras) == 1, "M49: token phải nằm ở 1 paragraph duy nhất"
        pf = fold(paras[0])
        # nhánh DN hiện hữu: '(Đối với các trường hợp còn lại)' đứng TRƯỚC
        # token trong CÙNG paragraph; nhánh thành lập mới (Ông/Bà, giấy tờ
        # cá nhân) đứng trước marker đó và KHÔNG có token riêng
        i_marker = pf.find("doi voi cac truong hop con lai")
        assert i_marker >= 0, (
            "M49: token không nằm trong paragraph khối Kính gửi 2 nhánh")
        assert "ong/ba" in pf[:i_marker], (
            "M49: nhánh thành lập mới (Ông/Bà) phải đứng trước nhánh DN")
        # dòng nhánh DN giờ CHỈ còn token (dòng kẻ + nhãn đã thay) — kiểm
        # trên text NGUYÊN vì fold() gộp whitespace (mất ranh giới w:br)
        raw = paras[0]
        i_tok = raw.find(TOKEN)
        line_start = raw.rfind("\n", 0, i_tok) + 1
        line_end = raw.find("\n", i_tok)
        line = raw[line_start:line_end if line_end >= 0 else len(raw)]
        assert re.fullmatch(
            r"[…\.]*" + re.escape(TOKEN) + r"[…\.]*", line), (
            "M49: dòng nhánh DN phải được thay bằng token, thấy %r" % line)
        # occurrence 'Tên Doanh nghiệp' (p14, câu 'Sau khi xem xét…') giữ nguyên
        p14 = [p.text for p in doc.paragraphs
               if "sau khi xem xet" in fold(p.text)]
        assert p14 and "(Tên Doanh nghiệp)" in p14[0] and TOKEN not in p14[0], (
            "M49: occurrence '(Tên Doanh nghiệp)' p14 không được đụng")


@check("(a) template sandbox: đúng 1 token tại đúng occurrence (M48/M49/M70)")
def a_template_tokens():
    for fid in FORMS:
        _assert_template(fid, sandbox(fid)["doc"])


# ---------------------------------------------------------------------------
# (b)+(c) blocks: 1 run mirror đúng chỗ, 0 run input cùng key
# ---------------------------------------------------------------------------

def _assert_blocks(fid: str, blocks: dict) -> tuple[int, int]:
    n_mirror = n_input = 0
    mirror_ctx = []
    for bi, where, runs in walk_runs(blocks):
        for r in runs:
            if r.get("input", {}).get("key") == KEY:
                n_input += 1
            if "mirror" in r:
                assert r["mirror"] == {"key": KEY}, (
                    "%s: run mirror sai shape: %r" % (fid, r))
                n_mirror += 1
                mirror_ctx.append(bi)
    assert n_input == 0, (
        "%s: PHẢI không có run input %s (read-only — không input thứ hai), "
        "thấy %d" % (fid, KEY, n_input))
    assert n_mirror == 1, (
        "%s: phải có ĐÚNG 1 run mirror, thấy %d tại block %r"
        % (fid, n_mirror, mirror_ctx))
    blk = blocks["blocks"][mirror_ctx[0]]
    assert blk.get("t") == "p", "%s: mirror phải nằm ở block p" % fid
    bf = fold(block_text(blk))
    if fid in ("PLI_M48", "PLI_M70"):
        assert "ve viec" in bf and "cua" in bf, (
            "%s: mirror block sai ngữ cảnh (phải chứa 'về việc … của …'): %r"
            % (fid, bf))
    else:  # M49: block khối Kính gửi 2 nhánh — marker nhánh DN đứng trước
        i_marker = bf.find("doi voi cac truong hop con lai")
        assert i_marker >= 0, (
            "M49: mirror block phải là khối Kính gửi chứa marker nhánh DN")
        assert "ong/ba" in bf[:i_marker], "M49: nhánh cá nhân phải trước nhánh DN"
    return n_mirror, n_input


@check("(b) blocks sandbox: đúng 1 run mirror {key} tại đúng block ngữ cảnh")
def b_blocks_mirror():
    for fid in FORMS:
        nm, _ = _assert_blocks(fid, sandbox(fid)["blocks"])
        assert nm == 1


@check("(c) blocks sandbox: KHÔNG run input cùng key (read-only mirror)")
def c_blocks_no_input():
    for fid in FORMS:
        _, ni = _assert_blocks(fid, sandbox(fid)["blocks"])
        assert ni == 0


# ---------------------------------------------------------------------------
# (d) sandbox render/export DOCX: 'ABC' đổ đúng chỗ; thiếu -> trống
# ---------------------------------------------------------------------------

def _render_xml(tpl: Path, data: dict) -> str:
    xml = dr.render(tpl, data)
    return zipfile.ZipFile(io.BytesIO(xml)).read(
        "word/document.xml").decode("utf-8")


import io  # noqa: E402


@check("(d) sandbox export: draft 'ABC' -> 'ABC' tại occurrence; thiếu -> trống")
def d_render_export():
    for fid in FORMS:
        tpl = sandbox(fid)["tpl"]
        xml_filled = _render_xml(tpl, {"dn": {"ten_tieng_viet": "ABC"}})
        assert "ABC" in xml_filled, "%s: render thiếu giá trị 'ABC'" % fid
        assert TOKEN not in xml_filled, "%s: sót token kỹ thuật khi có draft" % fid
        # vị trí: M48/M70 'của ABC', M49 dòng riêng
        if fid in ("PLI_M48", "PLI_M70"):
            assert re.search(r"của\s*<[^>]+>\s*ABC|của ABC", xml_filled) or \
                "của ABC" in re.sub(r"<[^>]+>", "", xml_filled), (
                "%s: 'ABC' không nằm tại occurrence 'của …'" % fid)
        else:
            plain = re.sub(r"<[^>]+>", "\n", xml_filled)
            assert re.search(r"\n\s*ABC\s*\n", plain), (
                "M49: 'ABC' phải là dòng riêng của nhánh DN")
        xml_blank = _render_xml(tpl, {})
        assert "ABC" not in xml_blank, "%s: draft trống mà vẫn thấy 'ABC'" % fid
        assert TOKEN not in xml_blank, "%s: sót token kỹ thuật khi draft trống" % fid
        plain_blank = re.sub(r"<[^>]+>", "", xml_blank)
        assert "undefined" not in plain_blank and "null" not in plain_blank, (
            "%s: in token kỹ thuật undefined/null khi draft trống" % fid)


# ---------------------------------------------------------------------------
# idempotent + fail-loud của generator
# ---------------------------------------------------------------------------

@check("(e) bind idempotent: lần 2 trả 0, template không đổi")
def e_idempotent():
    for fid in FORMS:
        sb = sandbox(fid)
        n2 = bfm._bind_output_mirrors(sb["doc"], fid)
        assert n2 == 0, "%s: bind lần 2 phải trả 0, thấy %d" % (fid, n2)
        before = template_token_lines(sb["doc"])
        assert len(before) == 1


@check("(f) fail-loud: expect sai -> ValueError")
def f_fail_loud():
    fid = "PLI_M48"
    sb = sandbox(fid)
    saved = bfm._HEADER_NAME_BINDING
    try:
        reg = json.loads(json.dumps(saved))  # deep copy
        reg["output_mirrors"][fid]["expect"] = 2
        bfm._HEADER_NAME_BINDING = reg
        try:
            bfm._bind_output_mirrors(sb["doc"], fid)
        except ValueError as exc:
            assert "1/2" in str(exc), "thông báo fail-loud thiếu 1/2: %r" % exc
        else:
            raise AssertionError("expect=2 phải raise ValueError")
    finally:
        bfm._HEADER_NAME_BINDING = saved


# ---------------------------------------------------------------------------
# [POST-REGEN] artifact thật: app/templates + app/data/blocks
# ---------------------------------------------------------------------------

@check("(g) [POST-REGEN] artifact thật (skip nếu Lead chưa regen)")
def g_committed_artifacts():
    done = []
    for fid in FORMS:
        tpl = ROOT / "app" / "templates" / ("%s.docx" % fid)
        if not tpl.exists():
            continue
        doc = Document(str(tpl))
        if not template_token_lines(doc):
            print("   SKIP %s: app/templates chưa regen (Lead regen sau merge)"
                  % fid)
            continue
        _assert_template(fid, doc)
        blocks = json.loads(
            (ROOT / "app" / "data" / "blocks" / ("%s.json" % fid))
            .read_text(encoding="utf-8"))
        _assert_blocks(fid, blocks)
        done.append(fid)
    if done:
        print("   artifact thật đã kiểm: %s" % ", ".join(done))


def main() -> int:
    a_template_tokens()
    b_blocks_mirror()
    c_blocks_no_input()
    d_render_export()
    e_idempotent()
    f_fail_loud()
    g_committed_artifacts()
    print("-" * 60)
    passed = sum(1 for ok, _ in _results if ok)
    failed = sum(1 for ok, _ in _results if not ok)
    print("Tổng kết: %d PASS / %d FAIL / %d test" % (
        passed, failed, len(_results)))
    for ok, name in _results:
        if not ok:
            print(" -", name)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
