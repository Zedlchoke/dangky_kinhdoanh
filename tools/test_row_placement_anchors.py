# -*- coding: utf-8 -*-
"""test_row_placement_anchors.py — F3T regression anchors trên TEMPLATE
PRODUCTION (app/templates, không hard-code row count theo form).

Anchors tối thiểu theo owner directive 2026-09-08:
  - PLI_M72 đủ 5 biến thể (DNTN / TNHH_1TV / TNHH_2TV / CTCP / DHDN);
  - PLII_M01, PLII_M02, PLI_M02, PLI_M10, PLI_M12, PLI_M27, PLI_M79,
    PLI_M80.

Với MỖI loop có blankRows=K trong blocks của form anchor:
  1. dựng fixture N>0 (build_fixture valid-full cho dynamic_tables; loop
     nested-grid/chưa có dữ liệu được inject N=3 theo cột blocks);
  2. render production template qua tools.docx_render.render (đường export
     thật);
  3. assert hợp đồng F3T.2 trên bảng ĐÃ RENDER, registry tra từ blocks
     ([Pin sync — owner N-only 2026-09-08]: CHỈ N hàng dữ liệu, KHÔNG
     hàng trắng):
     - bảng loop tồn tại, header nguyên vẹn (signature khớp blocks);
     - tổng hàng = lead + header + N;
     - N hàng dữ liệu đứng NGAY SAU header (không blank chen trước dòng 1);
     - STT trên dòng dữ liệu = 1..N;
     - KHÔNG còn hàng trắng đuôi — bảng kết thúc ở dòng dữ liệu thứ N.
  4. kèm det_row_placement (D18) chạy trên cùng DOCX phải 0 hit.

M72: mỗi biến thể chỉ kích hoạt ĐÚNG flag của biến thể; mọi loop vùng biến
thể (ngành + lưới thành viên/cổ đông) đều được inject N=3 và assert như
trên. Bảng biến thể khác bị condition drop — isolation chi tiết đã pin ở
tools/test_m72_conditional_export (1/1/2/3/2 bảng + heading/footnote).

Chạy:  python3 -X utf8 -m tools.test_row_placement_anchors
Exit 0 = PASS / 1 = FAIL.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.docx_render import LEFTOVER_RE, render  # noqa: E402
from tools.phase5_fixtures import (  # noqa: E402
    ValueFactory, build_fixture,
)
from tools.row_placement import (  # noqa: E402
    _balanced_tbls, _row_cells, _top_level_rows, det_row_placement,
    fold_squeeze, load_loop_registry,
)

BLOCKS_DIR = ROOT / "app" / "data" / "blocks"
MAPS_PATH = ROOT / "app" / "data" / "form_maps.json"
OUT_DIR = Path("/tmp/f3t_row_placement_anchors")

ANCHORS = ["PLII_M01", "PLII_M02", "PLI_M02", "PLI_M10", "PLI_M12",
           "PLI_M27", "PLI_M79", "PLI_M80"]

# M72: biến thể -> (flag, [loop vùng biến thể]) — bảng biến thể khác bị
# condition drop; số bảng khớp pin EXPECTED_TABLES của
# tools/test_m72_conditional_export (1/1/2/3/2).
M72_CASES = [
    ("DNTN", "loai_hinh_dntn",
     ["ds_nganh_dntn"]),
    ("TNHH_1TV", "loai_hinh_tnhh_1tv",
     ["ds_nganh_tnhh_1tv"]),
    ("TNHH_2TV", "loai_hinh_tnhh_2tv",
     ["ds_nganh_tnhh_2tv", "ds_thanh_vien_tnhh_2tv"]),
    ("CTCP", "loai_hinh_ctcp",
     ["ds_nganh_ctcp", "ds_co_dong_sang_lap_ctcp",
      "ds_co_dong_nuoc_ngoai_ctcp"]),
    ("DHDN", "loai_hinh_dhdn",
     ["ds_nganh_dhdn", "ds_thanh_vien_hop_danh_dhdn"]),
]

N_INJECT = 3   # fixture N>0 chuẩn cho mọi loop anchor

_results: list[tuple[bool, str]] = []


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


def _load_blocks(fid: str) -> dict:
    return json.loads(
        (BLOCKS_DIR / ("%s.json" % fid)).read_text(encoding="utf-8"))


def _load_maps() -> dict:
    return json.loads(MAPS_PATH.read_text(encoding="utf-8"))


def _loop_cols(blocks_doc: dict, loop: str) -> list[str]:
    """Tag cột của loop theo blocks (để inject dữ liệu N>0)."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("t") == "loop" and \
                    (x.get("loop") or x.get("name")) == loop:
                tags = [c.get("tag") for c in (x.get("cols") or [])
                        if c.get("tag")]
                if tags:
                    found.append(tags)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(blocks_doc)
    return found[0] if found else []


def _render_docx(fid: str, payload: dict) -> Path:
    # maps[fid]["template"] dạng "templates/<FID>.docx" — tương đối từ app/
    tpl = ROOT / "app" / _load_maps()[fid]["template"]
    assert tpl.exists(), "mất template production: %s" % tpl
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / ("%s.docx" % fid)
    out.write_bytes(render(str(tpl), payload))
    return out


def _doc_tables(path: Path) -> list[list[list[str]]]:
    """[bảng][hàng][ô] text đã squeeze, duyệt bảng cân bằng tầng ngoài."""
    with zipfile.ZipFile(str(path)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    tables = []
    for s, e in _balanced_tbls(xml):
        rows = _top_level_rows(xml[s:e])
        tables.append([_row_cells(r) for r in rows])
    return tables


def _n_business(rows) -> int:
    """N theo last-mile guard: bỏ non-dict và dòng mọi ô trống (bỏ key _)."""
    n = 0
    if not isinstance(rows, list):
        return 0
    for item in rows:
        if not isinstance(item, dict):
            continue
        if any((str(v).strip() != "") if v is not None else False
               for k, v in item.items() if not k.startswith("_")):
            n += 1
    return n


def _assert_loop_placement(fid: str, tables, entry: dict, n: int) -> None:
    """Assert hợp đồng F3T.2 cho MỘT loop trên bảng đã render."""
    loop, k, h, sig = (entry["loop"], entry["k"], entry["header_rows"],
                       entry["sig"])
    tbl = next((t for t in tables
                if t and fold_squeeze("".join(t[0])) == sig), None)
    assert tbl is not None, \
        "%s/%s: không tìm thấy bảng loop (sig %r)" % (fid, loop, sig[:40])
    texts = [fold_squeeze("".join(cells)) for cells in tbl]
    non_blank = [i for i, t in enumerate(texts) if t]
    first_nb, last_nb = non_blank[0], non_blank[-1]
    # [Pin sync — owner N-only 2026-09-08] tổng hàng = lead + header + N
    # (không max(K,N), không hàng trắng)
    total_expect = first_nb + h + n
    assert len(tbl) == total_expect, \
        ("%s/%s: tổng hàng %d != lead %d + header %d + N=%d: %r"
         % (fid, loop, len(tbl), first_nb, h, n,
            ["".join(c)[:30] for c in tbl]))
    # data NGAY SAU header: nếu blank chen trước dòng 1 thì vị trí data đầu
    # sẽ là hàng trắng -> assert này bắn
    for j in range(n):
        cells = tbl[first_nb + h + j]
        assert not all(c == "" for c in cells), \
            ("%s/%s: blank chen giữa header và dòng %d (vùng data trống): %r"
             % (fid, loop, j + 1, cells))
    # STT 1..N trên data
    for j in range(n):
        stt = tbl[first_nb + h + j][0] if tbl[first_nb + h + j] else ""
        assert stt == str(j + 1), \
            "%s/%s: STT hàng %d = %r, kỳ vọng %d" % (
                fid, loop, first_nb + h + j, stt, j + 1)
    # [Pin sync — owner N-only 2026-09-08] KHÔNG hàng trắng đuôi — dòng
    # không-trắng cuối cùng phải là dòng dữ liệu thứ N (bảng kết thúc ngay
    # sau data; assert tổng hàng bên trên đã pin tổng = lead + header + N)
    assert last_nb == first_nb + h + n - 1, \
        ("%s/%s: còn hàng trắng sau dòng data cuối (last_nb=%d, kỳ vọng %d)"
         % (fid, loop, last_nb, first_nb + h + n - 1))


@check("[ANCHOR] 8 form production: N>0 -> placement N đúng + D18 0 hit")
def anchors_plain_forms():
    maps = _load_maps()
    for fid in ANCHORS:
        blocks_doc = _load_blocks(fid)
        registry = load_loop_registry(blocks_doc)
        assert registry, "%s: blocks không có loop blankRows nào" % fid
        payload = build_fixture(fid, maps[fid], "valid-full", blocks_doc,
                                ValueFactory())
        for entry in registry:
            loop = entry["loop"]
            rows = payload.get(loop)
            if not isinstance(rows, list) or not rows:
                # nested-grid/chưa có fixture -> inject N_INJECT dòng N>0
                tags = _loop_cols(blocks_doc, loop)
                assert tags, "%s/%s: không suy được cột từ blocks" % (
                    fid, loop)
                rows = [{t: "%s-%d" % (t, i + 1) for t in tags}
                        for i in range(N_INJECT)]
                payload[loop] = rows
        out = _render_docx(fid, payload)
        tables = _doc_tables(out)
        for entry in registry:
            n = _n_business(payload.get(entry["loop"]))
            assert n > 0, \
                "%s/%s: anchor phải có N>0, payload rỗng" % (
                    fid, entry["loop"])
            _assert_loop_placement(fid, tables, entry, n)
        xml = zipfile.ZipFile(str(out)).read(
            "word/document.xml").decode("utf-8")
        assert not LEFTOVER_RE.findall(xml), \
            "%s: còn marker sót" % fid
        hits = det_row_placement(out, registry)
        assert not hits, "%s: D18 bắn trên bản đã fix: %r" % (fid, hits)


@check("[ANCHOR] PLI_M72 đủ 5 biến thể: placement đúng cho mọi loop variant")
def anchors_m72_variants():
    fid = "PLI_M72"
    blocks_doc = _load_blocks(fid)
    registry = {e["loop"]: e for e in load_loop_registry(blocks_doc)}
    assert len(registry) == 9, \
        "M72 phải có 9 loop blankRows, thấy %d" % len(registry)
    for label, flag, loops in M72_CASES:
        payload = {"dn.ten_tieng_viet": "CONG TY TEST " + label}
        for _lbl, f, _loops in M72_CASES:
            payload[f] = "X" if f == flag else ""
        for loop in loops:
            tags = _loop_cols(blocks_doc, loop)
            assert tags, "M72/%s: không suy được cột" % loop
            payload[loop] = [{t: "%s-%d" % (t, i + 1) for t in tags}
                             for i in range(N_INJECT)]
        out = _render_docx(fid, payload)
        tables = _doc_tables(out)
        for loop in loops:
            entry = registry[loop]
            n = _n_business(payload[loop])
            _assert_loop_placement("%s[%s]" % (fid, label), tables, entry, n)
        xml = zipfile.ZipFile(str(out)).read(
            "word/document.xml").decode("utf-8")
        assert not LEFTOVER_RE.findall(xml), "M72[%s]: còn marker" % label
        hits = det_row_placement(out, list(registry.values()))
        # D18 đo toàn tài liệu; bảng biến thể khác đã drop nên phải 0 hit
        assert not hits, "M72[%s]: D18 bắn: %r" % (label, hits)


def main() -> int:
    anchors_plain_forms()
    anchors_m72_variants()
    fails = [r for r in _results if not r[0]]
    print("-" * 60)
    print("test_row_placement_anchors: %d PASS / %d FAIL"
          % (len(_results) - len(fails), len(fails)))
    for ok, name in _results:
        if not ok:
            print(" - FAIL:", name)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
