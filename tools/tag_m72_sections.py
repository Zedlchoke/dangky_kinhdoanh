# -*- coding: utf-8 -*-
"""Gắn marker vùng điều kiện loại hình DN vào app/templates/PLI_M72.docx.

Contract P1.2 "Option D" (docs/m72_activation_proposal.md, phần bổ sung):
mỗi biến thể loại hình của Mẫu 72 được bọc bởi cặp paragraph marker
`{?loai_hinh_<variant>}` ... `{/loai_hinh_<variant>}` ở con trực tiếp của
body. Engine (tools/docx_render.py) chỉ xuất nội dung biến thể có flag
truthy trong payload export; converter (tools/docx_to_blocks.py) gắn
`cond` vào blocks để UI chỉ render biến thể đang chọn. Marker là thẻ kỹ
thuật vô hình trong output, KHÔNG phải checkbox pháp lý chèn vào mẫu.

Ranh giới bọc (đã xác minh trên template):
  - DNTN     : từ "(TÊN DOANH NGHIỆP TƯ NHÂN)" đến trước marker TNHH_1TV;
  - TNHH_1TV : từ marker tương ứng đến trước marker TNHH_2TV + dòng ghi
               chú chân trang số 1;
  - TNHH_2TV : ... đến trước marker CTCP + ghi chú số 2;
  - CTCP     : ... đến trước marker HỢP DANH + ghi chú số 3;
  - DHDN     : ... đến trước dòng gạch dưới kết thúc chung.
  Ghi chú chân trang 1/2/3 được bọc theo đúng biến thể chứa số mũ tương
  ứng ("của công ty" + superscript 1/2/3 - bằng chứng cấu trúc tài liệu,
  không suy đoán nghiệp vụ). Dòng gạch dưới và các đoạn trắng cuối tài
  liệu là nội dung dùng chung - KHÔNG bọc (chờ owner xác nhận nếu cần).

Idempotent: template đã đúng marker -> không đổi gì, exit 0 (--check để
chỉ kiểm tra). Có marker nhưng SAI vị trí -> exit 1, không tự sửa mù
(buộc regen template bằng build_form_maps rồi chạy lại tagger này).

Chạy:  python -X utf8 tools/tag_m72_sections.py            # gắn marker
       python -X utf8 tools/tag_m72_sections.py --check    # chỉ kiểm tra
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "app" / "templates" / "PLI_M72.docx"

# (flag, anchor bắt đầu section, anchor đóng riêng | None = trước anchor kế)
SECTIONS = [
    ("loai_hinh_dntn", "(ten doanh nghiep tu nhan)", None),
    ("loai_hinh_tnhh_1tv", "(ten cong ty tnhh mot thanh vien)", None),
    ("loai_hinh_tnhh_2tv", "(ten cong ty tnhh hai thanh vien)", None),
    ("loai_hinh_ctcp", "(ten cong ty co phan)", None),
    ("loai_hinh_dhdn", "(ten cong ty hop danh)", "^_{5,}$"),
]

# Ghi chú chân trang thuộc biến thể chứa superscript tương ứng
# ("của công ty" + 1/2/3). Bằng chứng: dòng 2/3 còn số prefix trong text;
# dòng của số 1 đã MẤT số ở nguồn (chỉ còn dấu cách đầu dòng) - xác định
# theo vị trí (dòng ghi chú ĐẦU TIÊN sau khối kết thúc chung).
FOOTNOTE_WRAPS = [
    ("loai_hinh_tnhh_1tv", r"^ghi ten cua tat ca nguoi dai dien"),
    ("loai_hinh_tnhh_2tv", r"^2\s*ghi ten cua tat ca nguoi dai dien"),
    ("loai_hinh_ctcp", r"^3\s*ghi ten cua tat ca nguoi dai dien"),
]


def fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", out.replace("đ", "d")).strip()


def body_paras(doc):
    els = [el for el in doc.element.body.iterchildren()
           if el.tag == qn("w:p")]
    texts = [fold("".join(r.text for r in Paragraph(el, doc).runs))
             for el in els]
    return els, texts


def unique_hit(texts, pred_desc, pred):
    hits = [i for i, t in enumerate(texts) if pred(t)]
    if len(hits) != 1:
        raise SystemExit("LOI anchor %r: khop %d lan (can dung 1)"
                         % (pred_desc, len(hits)))
    return hits[0]


def expected_sequence():
    seq = []
    flags = [f for f, _s, _e in SECTIONS]
    starts = []
    for flag, start_pat, _e in SECTIONS:
        starts.append(start_pat)
    bounds = []
    for k, (flag, start_pat, end_pat) in enumerate(SECTIONS):
        if end_pat is not None:
            bounds.append((flag, "S%d" % k, "E%d" % k))
        else:
            bounds.append((flag, "S%d" % k, "S%d" % (k + 1)))
    # dựng chuỗi kỳ vọng theo thứ tự vị trí: S0 < S1 < ... < E_last,
    # với E_k (k<last) == S_{k+1}: tại đó [close(k), open(k+1)].
    seq.append("{?%s}" % flags[0])
    for k in range(len(flags) - 1):
        seq.append("{/%s}" % flags[k])
        seq.append("{?%s}" % flags[k + 1])
    seq.append("{/%s}" % flags[-1])
    for flag, _pat in FOOTNOTE_WRAPS:
        seq += ["{?%s}" % flag, "{/%s}" % flag]
    return seq


def existing_markers(doc):
    _els, texts = body_paras(doc)
    out = []
    for t in texts:
        m = re.fullmatch(r"\{(\?|/)([A-Za-z0-9_]+)\}", t)
        if m:
            out.append("{%s%s}" % (m.group(1), m.group(2)))
    return out


def plan_insertions(doc):
    """Trả về {index_paragraph_anchor: [marker_elements]} chèn TRƯỚC anchor."""
    _els, texts = body_paras(doc)
    starts = {}
    for k, (flag, start_pat, _e) in enumerate(SECTIONS):
        starts[k] = unique_hit(texts, start_pat,
                               lambda t, p=start_pat: t.startswith(fold(p)))
    inserts: dict[int, list] = {}

    def add(idx, mk):
        inserts.setdefault(idx, []).append(mk)

    def marker(flag, close):
        p = OxmlElement("w:p")
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = ("{/%s}" if close else "{?%s}") % flag
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        p.append(r)
        return p

    last = len(SECTIONS) - 1
    for k, (flag, start_pat, end_pat) in enumerate(SECTIONS):
        add(starts[k], marker(flag, False))
        if end_pat is not None:
            rx = re.compile(end_pat)
            e = unique_hit(
                texts, end_pat,
                lambda t, r=rx: bool(r.match(t)) and t != "")
            if e <= starts[k]:
                raise SystemExit("LOI: end %r dung TRUOC start %r"
                                 % (end_pat, start_pat))
            add(e, marker(flag, True))
        else:
            add(starts[k + 1], marker(flag, True))  # nhóm sau open(k+1)
    for flag, pat in FOOTNOTE_WRAPS:
        rx = re.compile(pat)
        i = unique_hit(texts, pat, lambda t, r=rx: bool(r.match(t)))
        add(i, marker(flag, False))
        add(i + 1, marker(flag, True))
    return inserts


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    doc = Document(str(TEMPLATE_PATH))
    markers = existing_markers(doc)
    expect = expected_sequence()
    if markers == expect:
        print("PLI_M72: %d marker điều kiện đã đúng - không đổi gì."
              % len(markers))
        return 0
    if check_only:
        print("FAIL: marker hiện có (%d): %s" % (len(markers), markers))
        print("Kỳ vọng (%d): %s" % (len(expect), expect))
        return 1
    if markers:
        print("Template ĐÃ có marker nhưng sai sequence: %s" % markers)
        print("Không tự sửa mù. Regen template (build_form_maps --one "
              "PLI_M72) rồi chạy lại tagger.")
        return 1
    paras, _texts = body_paras(doc)
    inserts = plan_insertions(doc)
    # chèn theo nhóm từ CUỐI tài liệu lên để index không trôi; trong cùng
    # nhóm giữ THỨ TỰ khai báo (vd [{/prev}, {?next}]) vì addprevious luôn
    # chèn ngay trước anchor -> phần tử sau cùng của nhóm nằm gần anchor nhất
    for i in sorted(inserts, reverse=True):
        for mk in inserts[i]:
            paras[i].addprevious(mk)
    doc.save(str(TEMPLATE_PATH))
    ok = existing_markers(Document(str(TEMPLATE_PATH))) == expect
    print("Đã gắn %d marker. Verify sau ghi: %s"
          % (sum(len(v) for v in inserts.values()), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
