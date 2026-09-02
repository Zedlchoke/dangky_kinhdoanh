#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_docx_layout_signatures.py — Wave D batch 1, lane fix-docx-layout.

Đo STRUCTURAL (python zip/regex, không đo visual) trên DOCX render cho:

  [Class 7] khoảng trống vùng chữ ký (defect_registry.md mục Class 7):
    T0 [SRC-STD]   bản giấy nguồn tự thỏa chuẩn "dòng tiêu đề ký phải có
                   ít nhất MỘT dòng trống phía trên trong cùng container
                   (body/ô bảng), hoặc w:spacing w:before >= 120" — chuẩn
                   đo từ chính template nguồn (phân bố blanks_before của
                   84 title ký nguồn: {0-spacing:39, 1:9, 2:35, 9:1}; các
                   trường hợp 0 dòng trống ĐỀU có spacing before=120).
    T1 [RENDER-STD] output render phải thỏa chuẩn như T0 cho MỌI title ký.
                   (Đỏ trước fix: PLI_M70 mất dòng trống trên
                   "NGƯỜI NỘP/NGƯỜI NHẬN (Ký và ghi họ tên)".)
    T2 [FAITHFUL]  với từng title ký khớp theo thứ tự: blanks_before(render)
                   >= blanks_before(nguồn). Title ký có trong nguồn mà KHÔNG
                   có trong render là mất nội dung ở blocks/generator —
                   KHÔNG thể sửa ở render layer -> pin allowlist
                   MISSING_SIG_ALLOWLIST (strict: regen sửa xong phải xóa
                   entry, test sẽ đỏ để nhắc gỡ).
  [Class 8] dấu X checkbox tách label (defect_registry.md mục Class 8):
    T3 [BOX-ONLY]  đoạn render chỉ chứa "X" phải có gốc là dòng □ RIÊNG
                   trong bản giấy (thiết kế mẫu giấy — audit Wave trước:
                   128 đoạn "X" đứng một mình là chủ đích, KHÔNG được sửa);
                   tag {chk_*} đứng một mình mà nguồn để label+□ CÙNG dòng
                   -> vi phạm (X tách khỏi label của chính nó).
    T4 [SAME-LINE] paragraph template chứa tag chk CÙNG chữ -> render CHECKED
                   phải cho ra MỘT paragraph chứa đủ chữ + "X"; render
                   UNCHECKED phải giữ nguyên chữ (không mất đoạn). Đo cả hai
                   trạng thái X và trống (DOCX không hề chứa glyph □ — glyph
                   chỉ là thiết kế bản giấy).
    T5 [DETECTOR]  tự kiểm capability ĐỎ: detector của T3 phải bắt được ca
                   tổng hợp "nguồn cùng dòng / template tách dòng" và sạch
                   cho ca "nguồn đã để □ riêng dòng".
  [GUARD] T6 [PAGEBREAK] số marker ngắt trang explicit (<w:br w:type="page"/>
    + <w:pageBreakBefore/>) từng mẫu phải đúng bằng baseline pin (fix layout
    không được tạo/ngắt trang mới; python-docx không đếm được trang nên dùng
    heuristic marker XML — đúng gợi ý lane).

Output render test ghi vào generated_ho_so/_render_test/ (gitignored).
KHÔNG đọc/ghi app/templates, app/data ở chế độ ghi.

Chạy:  python3 -X utf8 -m tools.test_docx_layout_signatures
"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.docx_render import (  # noqa: E402
    APP_DIR,
    FORM_MAPS_PATH,
    _lookup,
    dummy_data_from_map,
    render,
)

# marker title vùng chữ ký: "(Ký..." hoặc "(Đã ký)" — dùng CÙNG regex cho
# nguồn và render để phép khớp T2 luôn công bằng hai phía.
SIG_MARK_RE = re.compile(r"\((?:Ký|Đã ký)")
GLYPH = "\u25a1"  # □ — ô vuông checkbox trên bản giấy nguồn

# Pin BLOCKED_OWNER (Class 7, mức MẤT NỘI DUNG — ngoài ownership render):
# title ký có trong nguồn giấy mà không có trong template/render. Mapping
# blocks PLI_M09 không chứa 4 đoạn ký cuối mỗi section
# ("……, ngày……tháng……năm……NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT/…(Ký và ghi họ tên)",
# body-level trong nguồn; app/data/blocks/PLI_M09.json không có text
# "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT" lẫn "(Ký" nào) — thuộc extractor/generator
# (forbidden), Lead regen sau merge. STRICT: nếu regen khôi phục (số missing
# giảm), test ĐỎ để bắt buộc cập nhật allowlist này.
MISSING_SIG_ALLOWLIST = {"PLI_M09": 4}

# Baseline marker ngắt trang explicit theo mẫu (đo tại BASE 65c7346, dữ liệu
# dummy checked): {fid: [w:br page, w:pageBreakBefore]}. Chỉ PLI_M12 có break.
PAGEBREAK_BASELINE = {"PLI_M12": [9, 0]}

# ngưỡng "một dòng trống" thay thế hợp lệ: spacing before >= 120 twips (6pt)
# — đúng cơ chế bản giấy dùng cho 39 title ký nằm sát nội dung trên.
MIN_SPACING_BEFORE = 120

# NHÁNH có cặp đóng đứng TRƯỚC ([ >] loại '/') để "<w:p/>" không bị nuốt
# chung với paragraph kế tiếp.
_PARA_RE = re.compile(r"<w:p[ >].*?</w:p>|<w:p[^>]*/>", re.S)
_CELL_RE = re.compile(r"<w:tc[ >].*?</w:tc>|<w:tc/>", re.S)
_TBL_RE = re.compile(r"<w:tbl[ >].*?</w:tbl>", re.S)
_SPACING_RE = re.compile(r'<w:spacing[^>]*w:before="(\d+)"')
_T_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")


def para_text(pxml: str) -> str:
    return "".join(_T_RE.findall(pxml))


def spacing_before(pxml: str) -> int:
    m = _SPACING_RE.search(pxml)
    return int(m.group(1)) if m else 0


def containers_of(xml: str) -> list:
    """Tách body thành các container theo đúng ngữ nghĩa OOXML: 1 container
    cho body (các paragraph con trực tiếp) + 1 container cho MỖI <w:tc>.
    Trả list [(tên, [pxml, ...])]. Đơn giản bằng đếm depth bảng khi quét."""
    bm = re.search(r"<w:body>(.*)</w:body>", xml, re.S)
    body = bm.group(1) if bm else xml
    out = [("body", [])]
    tbl_re = _TBL_RE
    consumed = [(m.start(), m.end()) for m in tbl_re.finditer(body)]
    def in_tbl(pos: int) -> bool:
        return any(s <= pos < e for s, e in consumed)
    # paragraph body-level (ngoài bảng) — theo thứ tự xuất hiện
    for m in _PARA_RE.finditer(body):
        if not in_tbl(m.start()):
            out[0][1].append(m.group(0))
    # từng ô bảng là một container riêng; bảng lồng: ô con đã nằm trong ô
    # cha nên chỉ lấy ô KHÔNG chứa ô khác (ô trong cùng nhất theo region)
    spans = [(m.start(), m.end()) for m in _CELL_RE.finditer(body)]
    inner = []
    for s, e in spans:
        if not any((s2 < s and e < e2) for s2, e2 in spans):
            inner.append((s, e))
    for i, (s, e) in enumerate(inner):
        cont = ("tc%d" % (i + 1), [])
        for m in _PARA_RE.finditer(body[s:e]):
            cont[1].append(m.group(0))
        out.append(cont)
    return out


def sig_rows(containers) -> list:
    """[(container, idx, text, spacing, blanks_before)] cho từng title ký."""
    rows = []
    for cname, paras in containers:
        for i, pxml in enumerate(paras):
            text = para_text(pxml)
            if not SIG_MARK_RE.search(text):
                continue
            blanks = 0
            j = i - 1
            while j >= 0 and para_text(paras[j]).strip() == "":
                blanks += 1
                j -= 1
            rows.append((cname, i, text, spacing_before(pxml), blanks))
    return rows


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()


def render_form(fid: str, fmap: dict, checked: bool) -> str:
    """Render 1 mẫu với dữ liệu dummy (checked) hoặc mọi chk rỗng."""
    data = dummy_data_from_map(fmap)
    if not checked:
        for f in fmap.get("fields", []):
            if f.get("type") == "chk":
                data[f["key"]] = ""
    return render(APP_DIR / fmap["template"], data)


def doc_xml(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return z.read("word/document.xml").decode("utf-8")


def paras_of(xml: str) -> list:
    return [para_text(m.group(0)) for m in _PARA_RE.finditer(xml)]


# ---------------------------------------------------------------- detectors

def chk_same_line_violations(src_paras: list, tpl_paras: list) -> list:
    """Class 8 detector: tag {chk_*} đứng MỘT MÌNH trong đoạn template,
    label (đoạn không trống liền trước) lại nằm CÙNG DÒNG với □ trong nguồn
    -> X sẽ tách khỏi label của chính nó (vi phạm). Trả list mô tả vi phạm.
    Ngược lại (nguồn đã để □ riêng dòng) là thiết kế mẫu giấy -> sạch."""
    viol = []
    for i, t in enumerate(tpl_paras):
        for tag in re.findall(r"\{chk_[A-Za-z0-9_]+\}", t):
            rest = norm(t.replace(tag, " "))
            if rest:
                continue  # tag có chữ cùng đoạn -> không phải kiểu tách dòng
            k = i - 1
            while k >= 0 and not tpl_paras[k].strip():
                k -= 1
            label = norm(tpl_paras[k]) if k >= 0 else ""
            if not label:
                continue
            for s in src_paras:
                if GLYPH in s and label[:20] in norm(s):
                    viol.append("%s: tag-only %s nhưng nguồn cùng dòng %r"
                                % (label[:30], tag, norm(s)[:60]))
                    break
    return viol


# ------------------------------------------------------------------- tests

def main() -> int:
    maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    passed = failed = 0
    fails: list[str] = []

    def check(name: str, cond: bool, extra: str = "") -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
            print("PASS  " + name)
        else:
            failed += 1
            fails.append(name + ("  [%s]" % extra if extra else ""))
            print("FAIL  " + name + ("  [%s]" % extra if extra else ""))

    out_dir = ROOT / "generated_ho_so" / "_render_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    # đo một lượt cho mọi mẫu: nguồn + render checked + render unchecked
    src_sig, ren_sig = {}, {}
    missing_sig: dict[str, int] = {}
    faith_fail: list[str] = []
    render_std_fail: list[str] = []
    src_std_fail: list[str] = []
    chk_t3_fail: list[str] = []
    chk_t4_fail: list[str] = []
    pagebreak_diff: list[str] = []

    for fid in sorted(maps):
        fmap = maps[fid]
        src_xml = doc_xml(zipfile_read_bytes(fmap["file"]))
        src_cont = containers_of(src_xml)
        src_rows = sig_rows(src_cont)
        src_sig[fid] = src_rows

        # T0: chính bản giấy nguồn phải thỏa chuẩn (blank trước HOẶC spacing)
        for cname, _i, _t, sp, blanks in src_rows:
            if blanks == 0 and sp < MIN_SPACING_BEFORE:
                src_std_fail.append("%s/%s sp=%d blanks=0" % (fid, cname, sp))

        checked = render_form(fid, fmap, True)
        (out_dir / ("%s.docx" % fid)).write_bytes(checked)
        ren_xml = doc_xml(checked)
        ren_rows = sig_rows(containers_of(ren_xml))
        ren_sig[fid] = ren_rows

        # T1: render phải thỏa chuẩn vùng trống trên title ký
        for cname, _i, t, sp, blanks in ren_rows:
            if blanks == 0 and sp < MIN_SPACING_BEFORE:
                render_std_fail.append("%s/%s sp=%d blanks=0 | %r"
                                       % (fid, cname, sp, norm(t)[:45]))

        # T2: khớp theo thứ tự, render không được đời hơn nguồn
        n = max(len(src_rows), len(ren_rows))
        for idx in range(n):
            s = src_rows[idx] if idx < len(src_rows) else None
            r = ren_rows[idx] if idx < len(ren_rows) else None
            if s and not r:
                missing_sig[fid] = missing_sig.get(fid, 0) + 1
                continue
            if r and not s:
                faith_fail.append("%s#%d render thừa title %r"
                                  % (fid, idx, norm(r[2])[:45]))
                continue
            if r[4] < s[4]:
                faith_fail.append("%s#%d blanks_before render=%d < nguồn=%d | %r"
                                  % (fid, idx, r[4], s[4], norm(r[2])[:45]))

        # T6: marker ngắt trang explicit phải đúng baseline
        br = len(re.findall(r'<w:br w:type="page"\s*/>', ren_xml))
        pbb = len(re.findall(r"<w:pageBreakBefore\s*/>", ren_xml))
        want = PAGEBREAK_BASELINE.get(fid, [0, 0])
        if [br, pbb] != want:
            pagebreak_diff.append("%s: [%d,%d] != baseline [%d,%d]"
                                  % (fid, br, pbb, want[0], want[1]))

        # Class 8: nguồn + template + render checked/unchecked
        tpl_xml = doc_xml((APP_DIR / fmap["template"]).read_bytes())
        src_paras = paras_of(src_xml)
        tpl_paras = paras_of(tpl_xml)
        # T3: tag-only phải có gốc □-riêng-dòng trong nguồn
        chk_t3_fail.extend(
            "%s: %s" % (fid, v)
            for v in chk_same_line_violations(src_paras, tpl_paras))
        # T4: đoạn template có tag chk CÙNG chữ -> checked giữ chữ+X cùng
        # đoạn; unchecked giữ chữ. Expected dựng bằng đúng dữ liệu dummy
        # mà engine sẽ thay (chk='X' / text='TEST', tra cứu lồng nhau).
        data_dummy = dummy_data_from_map(fmap)
        ren_checked = paras_of(ren_xml)
        ren_blank = paras_of(doc_xml(render_form(fid, fmap, False)))
        norm_checked = [norm(t) for t in ren_checked]
        norm_blank = [norm(t) for t in ren_blank]
        for t in tpl_paras:
            if "{chk_" not in t:
                continue
            if not norm(re.sub(r"\{[^}{}]+\}", "", t)):
                continue  # đoạn chỉ toàn tag — thuộc T3
            exp_x = norm(substitute_tags(t, data_dummy))
            exp_e = norm(substitute_tags(t, data_dummy, blanks=True))
            if exp_x not in norm_checked:
                chk_t4_fail.append("%s CHECKED thiếu đoạn %r"
                                   % (fid, exp_x[:55]))
            if exp_e not in norm_blank:
                chk_t4_fail.append("%s UNCHECKED mất đoạn %r"
                                   % (fid, exp_e[:55]))

    # ---- chốt kết quả từng mệnh đề
    check("T0 nguồn giấy thỏa chuẩn trống-trước-title-ký",
          not src_std_fail, "; ".join(src_std_fail[:4]))
    check("T1 render: title ký có >=1 dòng trống trên hoặc spacing>=120",
          not render_std_fail, "; ".join(render_std_fail[:4]))
    check("T2a render không thừa title ký so với nguồn",
          not [f for f in faith_fail if "thừa" in f],
          "; ".join(f for f in faith_fail if "thừa" in f)[:160])
    allowlisted = {k: v for k, v in missing_sig.items()
                   if MISSING_SIG_ALLOWLIST.get(k) == v}
    new_missing = {k: v for k, v in missing_sig.items()
                   if MISSING_SIG_ALLOWLIST.get(k) != v}
    check("T2b title ký mất so với nguồn đúng bằng allowlist BLOCKED_OWNER",
          not new_missing and set(allowlisted) <= set(MISSING_SIG_ALLOWLIST),
          "missing=%s allowlist=%s" % (missing_sig, MISSING_SIG_ALLOWLIST))
    check("T3 đoạn X-độc-lập đều có gốc □-riêng-dòng trong bản giấy",
          not chk_t3_fail, "; ".join(chk_t3_fail[:3]))
    check("T4 checked giữ chữ+X cùng đoạn, unchecked không mất đoạn",
          not chk_t4_fail, "; ".join(chk_t4_fail[:3]))
    check("T5 detector Class 8 bắt đúng ca tổng hợp (đỏ-capability)",
          detector_selftest(), "")
    check("T6 marker ngắt trang explicit đúng baseline (không tạo trang mới)",
          not pagebreak_diff, "; ".join(pagebreak_diff[:4]))

    print("-" * 60)
    print("Tổng kết: %d PASS / %d FAIL" % (passed, failed))
    if fails:
        print("Các lỗi:")
        for line in fails:
            print(" -", line)
    print("Thư mục render test:", out_dir)
    return 0 if failed == 0 else 1


def detector_selftest() -> bool:
    """T5: detector phải ĐỎ cho ca nguồn-cùng-dòng/template-tách-dòng và
    XANH cho ca nguồn để □ riêng dòng (thiết kế mẫu giấy)."""
    same_line_src = ["Bot/BTO không? Có \u25a1 Không \u25a1"]
    split_tpl = ["Có", "{chk_co}"]
    ok_red = len(chk_same_line_violations(same_line_src, split_tpl)) == 1
    box_only_src = ["Có hoạt động theo dự án không?", "Có", "\u25a1"]
    ok_green = not chk_same_line_violations(box_only_src, split_tpl)
    return ok_red and ok_green


def zipfile_read_bytes(rel_path: str) -> bytes:
    return (ROOT / rel_path).read_bytes()


_TAG_SUB_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")


def substitute_tags(text: str, data: dict, blanks: bool = False) -> str:
    """Thay {tag} bằng giá trị dummy của nó (chk -> 'X'/'', khác -> như data);
    mô phỏng đúng _subst_vars của engine ở mức text."""

    def repl(m: re.Match) -> str:
        val = _lookup(data, m.group(1))
        if val is None:
            return ""
        if blanks:
            return ""
        return str(val)

    return _TAG_SUB_RE.sub(repl, text)


if __name__ == "__main__":
    sys.exit(main())
