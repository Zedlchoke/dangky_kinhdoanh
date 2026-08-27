"""Engine render DOCX thuần Python (chỉ dùng zipfile + re + python-docx khi test).

Cách hoạt động:
- Đọc template .docx (zip), xử lý chuỗi XML của word/document.xml và (nếu có)
  các word/header*.xml, word/footer*.xml.
- Bảng lặp: tìm <w:tr> chứa {#ten_loop} và {/ten_loop} trong cùng một hàng,
  nhân bản hàng cho từng phần tử của data[ten_loop] (list[dict]), thay {tag}
  bằng giá trị tương ứng; nếu list rỗng thì xóa hẳn hàng khuôn.
  Biến {_stt} trong hàng khuôn được thay bằng số thứ tự 1-based của dòng.
- Biến: thay mọi {a.b.c} bằng tra cứu lồng nhau trong data; thiếu -> "".
- Mọi phần XML khác và các entry zip khác được giữ nguyên.

Chạy tự kiểm tra:  python -m tools.docx_render --test-all
"""

from __future__ import annotations

import copy
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# Tag biến: {key} hoặc {a.b.c} — chữ/số/gạch dưới/chấm
TAG_RE = re.compile(r"\{([A-Za-z0-9_][A-Za-z0-9_.]*)\}")
# Tag mở/đóng bảng lặp
LOOP_OPEN_RE = re.compile(r"\{#([A-Za-z0-9_]+)\}")
# Vùng điều kiện body-level (P1.2 M72 Option D): paragraph chỉ chứa
# {?ten_flag} mở vùng và {/ten_flag} đóng vùng. Khi data[ten_flag] truthy
# (chuỗi không rỗng, vd 'X') -> giữ nội dung, bỏ 2 paragraph marker; khi
# falsy -> bỏ TOÀN BỘ nội dung giữa cặp marker (kể cả bảng). Marker phải
# nằm ở con trực tiếp của <w:body>; lồng nhau được hỗ trợ qua stack.
COND_OPEN_RE = re.compile(r"^\{\?([A-Za-z0-9_]+)\}$")
COND_CLOSE_RE = re.compile(r"^\{/([A-Za-z0-9_]+)\}$")
_BODY_RE = re.compile(r"(<w:body>)(.*)(</w:body>)", re.S)
_ELEM_OPEN_RE = re.compile(r"<w:(p|tbl|sectPr)(?=[ >/])")
# Một hàng <w:tr> ... </w:tr> (tag nằm trọn trong một w:t nên regex là đủ)
ROW_RE = re.compile(r"<w:tr(?:\s[^>]*)?>.*?</w:tr>", re.S)

# Các part XML cần render
_RENDER_PART_RE = re.compile(r"^word/(document\.xml|header\d*\.xml|footer\d*\.xml)$")

# Chuỗi sót lại cần phát hiện khi kiểm tra: {từ} / {a.b} / {#loop} / {/loop}
# / {?flag} — (kể cả biến engine {_stt} — nếu sót là lỗi render)
LEFTOVER_RE = re.compile(r"\{[/#?]?[A-Za-z_][A-Za-z0-9_.#/?]*\}")


def _lookup(data: dict, key: str):
    """Tra cứu lồng nhau 'a.b.c' trong data; trả None nếu thiếu."""
    cur = data
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def safe_escape(val) -> str:
    """Escape giá trị dữ liệu cho XML; đồng thời vô hiệu hóa ngoặc nhọn để
    giá trị người dùng không bị đọc nhầm thành tag ở lượt thay sau."""
    return escape(str(val)).replace("{", "&#123;").replace("}", "&#125;")


def _subst_vars(xml: str, data: dict) -> str:
    """Thay mọi {key} bằng giá trị lồng nhau trong data; thiếu -> rỗng."""

    def repl(m: re.Match) -> str:
        val = _lookup(data, m.group(1))
        if val is None:
            return ""
        return safe_escape(val)

    return TAG_RE.sub(repl, xml)


def _expand_loops(xml: str, data: dict) -> str:
    """Nhân bản/xóa các hàng <w:tr> khuôn của bảng lặp."""
    out: list[str] = []
    pos = 0
    for m in ROW_RE.finditer(xml):
        row = m.group(0)
        name = next(
            (
                n
                for n in LOOP_OPEN_RE.findall(row)
                if "{/%s}" % n in row
            ),
            None,
        )
        if name is None:
            continue  # hàng thường, giữ nguyên
        out.append(xml[pos : m.start()])
        items = data.get(name)
        if isinstance(items, list):
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                r = row.replace("{#%s}" % name, "").replace("{/%s}" % name, "")
                # Biến engine {_stt}: số thứ tự 1-based của dòng dữ liệu
                # (thay trước khi quét tag thường để dữ liệu không ghi đè)
                r = r.replace("{_stt}", str(idx + 1))
                # Thay tag cột theo dữ liệu dòng; tag lồng nhau để lượt sau xử lý
                r = TAG_RE.sub(
                    lambda mm: (
                        safe_escape(item.get(mm.group(1), ""))
                        if "." not in mm.group(1)
                        else mm.group(0)
                    ),
                    r,
                )
                out.append(r)
        # items không phải list hoặc list rỗng -> xóa hẳn hàng khuôn
        pos = m.end()
    out.append(xml[pos:])
    return "".join(out)


def _truthy(val) -> bool:
    """Giá trị điều kiện vùng: chuỗi không rỗng (vd 'X') là truthy; None/rỗng
    (flag chưa được chọn) là falsy -> nội dung vùng bị loại khỏi output."""
    if val is None:
        return False
    return str(val).strip() != ""


def _para_marker(elem_xml: str):
    """Paragraph con trực tiếp của body có phải marker điều kiện không?
    Trả ('open'|'close', tên) hoặc None. Text = nối mọi <w:t> rồi strip."""
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", elem_xml)
    s = "".join(texts).strip()
    m = COND_OPEN_RE.match(s)
    if m:
        return ("open", m.group(1))
    m = COND_CLOSE_RE.match(s)
    if m:
        return ("close", m.group(1))
    return None


def _split_body_children(body: str):
    """Tách body XML thành list span (start, end) các CON TRỰC TIẾP của
    <w:body>. w:p không lồng nhau (đủ một cặp mở/đóng); w:tbl đếm depth;
    phần tử khác/whitespace giữa các span được giữ nguyên khi dựng lại."""
    spans = []
    pos = 0
    n = len(body)
    while pos < n:
        m = _ELEM_OPEN_RE.search(body, pos)
        if not m:
            break
        tag = m.group(1)
        start = m.start()
        if tag == "p":
            # <w:p> có thể tự đóng (<w:p .../>) với đoạn rỗng
            gt = body.index(">", m.end())
            if body[gt - 1] == "/":
                start, pos, end = start, gt + 1, gt + 1
            else:
                end = body.index("</w:p>", gt) + len("</w:p>")
                pos = end
        elif tag == "tbl":
            depth = 1
            scan = m.end()
            while depth:
                mm = re.search(r"<w:tbl[ >]|</w:tbl>", body[scan:])
                if not mm:
                    raise ValueError("w:tbl khong dong trong body template")
                tok = mm.group(0)
                depth += -1 if tok.startswith("</") else 1
                scan += mm.end()
            end = scan
            pos = end
        else:  # sectPr: có thể tự đóng hoặc có cặp đóng
            close = body.index(">", m.end())
            if body[close - 1] == "/":
                pos = close + 1
                end = close + 1
            else:
                end = body.index("</w:sectPr>", close) + len("</w:sectPr>")
                pos = end
        spans.append((start, end))
    return spans


class CondTagError(ValueError):
    """Marker điều kiện sai cú pháp/lồng nhau — fail loud, không render nửa vời."""


def _apply_conditions(xml: str, data: dict) -> str:
    """Xử lý vùng điều kiện {?flag}...{/flag} ở con trực tiếp của <w:body>.
    - Cặp marker khớp, flag truthy  -> bỏ 2 paragraph marker, giữ nội dung.
    - Cặp marker khớp, flag falsy   -> bỏ cả vùng (marker + toàn bộ nội dung).
    - Sai cú pháp (đóng không mở, mở không đóng, tên lệch, lồng chéo)
      -> raise CondTagError (template lỗi phải bị phát hiện ngay).
    Chỉ chạy cho word/document.xml (marker không nằm trong header/footer)."""
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    spans = _split_body_children(body)
    if not spans:
        return xml
    # Gắn trạng thái stack theo từng span; markers luôn bị loại.
    drop = [False] * len(spans)
    stack = []  # [(name, truthy)]
    events = []
    for si, (s, e) in enumerate(spans):
        seg = body[s:e]
        mk = _para_marker(seg) if seg.startswith("<w:p") else None
        if mk:
            events.append((si, mk))
    for si, (kind, name) in events:
        if kind == "open":
            stack.append((name, si, _truthy(data.get(name))))
        else:
            if not stack:
                raise CondTagError(
                    "{/%s} không có {?} mở tương ứng" % name)
            oname, osi, otruthy = stack.pop()
            if oname != name:
                raise CondTagError(
                    "{?%s} bị đóng bởi {/%s} sai cặp (lồng chéo)" % (oname, name))
            # Vùng [osi..si]: marker luôn loại; nội dung chỉ giữ khi truthy
            # và mọi cha đang mở cũng truthy.
            parents_truthy = all(t for _n, _osi, t in stack)
            keep = otruthy and parents_truthy
            for j in range(osi, si + 1):
                drop[j] = drop[j] or (not keep) or j in (osi, si)
    if stack:
        raise CondTagError(
            "{?%s} không được đóng trước hết body" % stack[-1][0])
    out = []
    pos = 0
    for (s, e), d in zip(spans, drop):
        out.append(body[pos:s])
        if not d:
            out.append(body[s:e])
        pos = e
    out.append(body[pos:])
    return xml[:bm.start(2)] + "".join(out) + xml[bm.end(2):]


def render(template_path: str | os.PathLike, data: dict,
           tables_meta: list | None = None,
           totals_strict: bool = True) -> bytes:
    """Render template thành nội dung file .docx mới (bytes).

    tables_meta (tuỳ chọn): metadata cấu trúc bảng do form_maps mang
    (`section_specs`, xem tools/form_specs/schema/table_kinds.schema.json).
    Có giá trị -> TỔNG của fixed-matrix được TÍNH LẠI từ các ô dữ liệu trước
    khi thay biến (không tin giá trị lưu trong draft, D1.1=A). Payload người
    gọi không bị mutate (bản sao sâu làm bên trong).
    totals_strict=False chỉ ghi nhận xung đột vào báo cáo trả về bởi
    recompute_totals() thay vì raise — dùng cho trường hợp audit/khám phá.

    Không đụng vào file template nguồn — mọi thứ diễn ra trong bộ nhớ.
    """
    payload = data
    if tables_meta:
        # render không được mutate payload của caller: tính tổng trên bản sao
        # sâu (payload draft luôn JSON-serializable; phòng khi không phải thì
        # dùng deepcopy tổng quát)
        if isinstance(data, dict):
            try:
                payload = json.loads(json.dumps(data))
            except (TypeError, ValueError):
                payload = copy.deepcopy(data)
        else:
            payload = copy.deepcopy(data)
        recompute_totals(payload, tables_meta, strict=totals_strict)

    src_path = os.fspath(template_path)
    buf = io.BytesIO()
    with zipfile.ZipFile(src_path, "r") as src:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                raw = src.read(info.filename)
                name = info.filename.replace("\\", "/")
                if _RENDER_PART_RE.match(name):
                    xml = raw.decode("utf-8")
                    xml = _apply_conditions(xml, payload)
                    xml = _expand_loops(xml, payload)
                    xml = _subst_vars(xml, payload)
                    raw = xml.encode("utf-8")
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = info.external_attr
                dst.writestr(zi, raw)
    return buf.getvalue()


def write_rendered(template_path: str | os.PathLike, data: dict,
                   out_path: str | os.PathLike, **kwargs) -> None:
    """Tiện ích: render rồi ghi ra file."""
    content = render(template_path, data, **kwargs)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(content)


# ---------------------------------------------------------------------------
# Totals recompute lúc export (D1.1=A — ô tổng outputOnly, không tin stored)
#
# Lane W2 — D1.4=A: "giá trị loại cổ phần = số lượng × mệnh giá" là projection,
# nên ngoài `sum(<tag>)` lớp này nhận thêm `product(<tag>[, <tag>...])`. Grammar
# được nới tương ứng ở tools/form_specs/schema/table_kinds.schema.json (mục
# fixed_matrix.totals); phía JS đối ứng là productFormula() trong
# app_web/ui/fixed-matrix.js.
#
# Ngữ nghĩa product() chốt cho CẢ HAI phía:
#   1. op viết thường đúng chữ (`sum`|`product`) — 'SUM(' vẫn bị coi là formula
#      lạ để hai engine không lệch nhau; `sum` giữ nguyên arity 1 tag như cũ;
#   2. quét các dòng input (loại dòng tổng/output_only), mỗi dòng nhân các ô số
#      theo đúng thứ tự tag khai báo, rồi CỘNG DỒN tích từng dòng vào ô tổng;
#   3. dòng KHÔNG kê khai gì (rỗng ở mọi thừa số) bị bỏ qua — như sum đã bỏ qua
#      ô rỗng, một loại cổ phần không dùng không được tính thành 0 đồng;
#   4. dòng ĐÃ kê khai mà THIẾU >= 1 thừa số -> không suy ra được con số pháp
#      lý nên ô tổng bị coi là KHÔNG XÁC ĐỊNH và in TRỐNG (''), tuyệt đối KHÔNG
#      thay bằng '0' (trống nghĩa là "chưa đủ dữ liệu nguồn");
#   5. không có dòng nào đủ thừa số (ví dụ draft trắng tinh) -> cũng TRỐNG;
#   6. parse/format vẫn dùng number_value()/format_total() hiện có; tích có thể
#      âm/thập phân, việc chặn số âm thuộc validator đầu vào (input_type=money);
#   7. mã lỗi KHÔNG đổi tên, KHÔNG thêm mới: FORMULA_UNSUPPORTED và
#      EXPORT_TOTALS_RECOMPUTE_CONFLICT như trước; mã chốt đường export thật
#      vẫn thuộc về exportLoopsStrict (app_web/ui/app.js), lớp này không chạm.
# ---------------------------------------------------------------------------

_TOTALS_FORMULA_RE = re.compile(
    r"^(sum|product)\(\s*"
    r"([A-Za-z0-9_]+(?:\s*,\s*[A-Za-z0-9_]+)*)\s*\)$")


def _parse_totals_formula(formula: str) -> tuple[str | None, list[str]]:
    """Đọc formula tổng -> (op, [tag...]); op=None nếu không thuộc grammar.

    `sum(<tag>)` : đúng 1 tag (hành vi cũ, không đổi);
    `product(a[, b...])`: >=1 tag, phân tách bởi dấu phẩy.
    """
    match = _TOTALS_FORMULA_RE.match(str(formula or ""))
    if not match:
        return None, []
    tags = [part.strip() for part in match.group(2).split(",")]
    if match.group(1) == "sum" and len(tags) != 1:
        return None, []      # sum nhiều tham số chưa từng hợp lệ ở v1
    return match.group(1), tags


class ExportTotalsError(ValueError):
    """Tính lại tổng lúc export gặp xung đột/formula không hỗ trợ.

    problems: list dict {"code", "semantic_key", "row", "detail",
    "stored", "computed"}. code =
      EXPORT_TOTALS_RECOMPUTE_CONFLICT — stored != computed;
      FORMULA_UNSUPPORTED              — mẫu formula chưa hỗ trợ.

    Chú ý: đây KHÔNG phải cơ chế chốt của đường export thật. Loop-contract
    vẫn do `exportLoopsStrict` (app_web/ui/app.js) giữ vai trò duy nhất với
    mã lỗi riêng của nó; lớp này chỉ bảo đảm DOCX không bao giờ in một con
    số tổng mà các ô dữ liệu nguồn không tính ra, và KHÔNG đặt tên đè lên
    mã chốt đó."""

    def __init__(self, problems: list):
        self.problems = problems
        detail = "; ".join(
            "%s [%s]%s%s" % (
                p["code"], p["semantic_key"],
                (" row=%s" % p["row"]) if p.get("row") else "",
                (" %s" % p["detail"]) if p.get("detail") else "")
            for p in problems)
        super().__init__("tổng lúc export lệch/sai spec (%d): %s"
                         % (len(problems), detail))


def number_value(value) -> float | None:
    """Đổi chuỗi số người dùng thành số: bỏ dấu cách, chấp nhận dấu phẩy thập
    phân và dấu chấm ngăn cách nghìn. Trả về None khi rỗng/không parse được —
    trùng hành vi numberValue() của app_web/ui/fixed-matrix.js."""
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().replace(" ", "").replace(" ", "")
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        result = float(text)
    except ValueError:
        return None
    return result


def format_total(value: float) -> str:
    """Định dạng tổng tính lại: số nguyên không nhóm hàng nghìn, số lẻ cắt
    zero-dư (locale-free để DOCX và UI không lệch nhau vì định dạng máy)."""
    if float(value).is_integer():
        return str(int(value))
    return ("%.4f" % value).rstrip("0").rstrip(".")


def _set_nested(data: dict, dotted_key: str, value) -> None:
    cur = data
    parts = dotted_key.split(".")
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def recompute_totals(data: dict, tables_meta: list,
                     *, strict: bool = True) -> list[dict]:
    """Tính lại mọi tổng khai báo trong tables_meta từ chính các ô dữ liệu.

    Formula nhận ở v1 + mở rộng lane W2 (D1.4=A): `sum(<tag>)` và
    `product(<tag>[, <tag>...])` — ngữ nghĩa ghi chú ngay trên
    _TOTALS_FORMULA_RE, đối ứng phía JS là app_web/ui/fixed-matrix.js.
    Trả về report list [{"semantic_key","row","formula","target","stored",
    "computed"}]; raise ExportTotalsError khi strict=True và có xung đột.
    Chỉ hỗ trợ kind "fixed-matrix"; kind khác (nested-grid/output-table) hiện
    không có hàng tổng nên được bỏ qua im lặng.
    """
    problems: list[dict] = []
    report: list[dict] = []
    for meta in tables_meta or []:
        if not isinstance(meta, dict):
            continue
        if meta.get("kind") != "fixed-matrix":
            continue
        sem = str(meta.get("semantic_key") or "")
        if not sem:
            continue
        rows = [r for r in meta.get("fixed_rows", []) if isinstance(r, dict)]
        total_row_ids = {str(t.get("id")) for t in rows if t.get("output_only")}
        column_tags = {c.get("tag") for c in meta.get("columns", []) if c.get("tag")}
        input_rows = [str(r["id"]) for r in rows
                      if not r.get("output_only")
                      and str(r["id"]) not in total_row_ids]
        for total in meta.get("totals", []) or []:
            op, formula_tags = _parse_totals_formula(
                str(total.get("formula") or ""))
            target = "%s.%s.%s" % (sem, total.get("target_row"),
                                   total.get("target_tag"))
            # tag lạ (không thuộc columns) vẫn là formula không hỗ trợ như v1
            if op is None or any(t not in column_tags for t in formula_tags):
                if strict:
                    raise ExportTotalsError([{
                        "code": "FORMULA_UNSUPPORTED", "semantic_key": sem,
                        "row": total.get("target_row"),
                        "detail": "formula %r" % total.get("formula")}])
                problems.append({
                    "code": "FORMULA_UNSUPPORTED", "semantic_key": sem,
                    "row": total.get("target_row"), "detail": "formula %r"
                    % (total.get("formula"),)})
                continue

            seen_any = False
            if op == "sum":
                # hành vi cũ: bỏ qua ô rỗng, tổng của "không kê khai" là 0
                acc = 0.0
                for rid in input_rows:
                    val = number_value(
                        _lookup(data, "%s.%s.%s" % (sem, rid, formula_tags[0])))
                    if val is None:
                        continue
                    seen_any = True
                    acc += val
                computed = format_total(acc)
            else:
                # product (D1.4=A): tích các cột thừa số theo từng dòng rồi cộng
                # dồn; dòng khai báo thiếu thừa số -> tổng TRỐNG, KHÔNG thay 0.
                acc = 0.0
                complete_rows = 0
                indeterminate = False
                for rid in input_rows:
                    missing = 0
                    row_product = 1.0
                    for tag in formula_tags:
                        val = number_value(
                            _lookup(data, "%s.%s.%s" % (sem, rid, tag)))
                        if val is None:
                            missing += 1
                            continue
                        row_product *= val
                    if missing == len(formula_tags):
                        continue          # dòng không kê khai gì: bỏ như sum
                    if missing:
                        # dòng có khai báo mà thiếu thừa số -> không suy ra được
                        indeterminate = True
                        break
                    complete_rows += 1
                    seen_any = True
                    acc += row_product
                computed = ("" if indeterminate or not complete_rows
                            else format_total(acc))

            stored_raw = _lookup(data, target)
            stored = "" if stored_raw is None else str(stored_raw).strip()
            record = {
                "semantic_key": sem, "row": total.get("target_row"),
                "formula": total.get("formula"), "target": target,
                "target_tag": total.get("target_tag"),
                "stored": stored, "computed": computed,
                "had_input": seen_any,
            }
            report.append(record)
            mismatch = False
            if computed == "":
                # tổng trống mà draft còn giữ số -> vẫn là xung đột phải nêu ra
                mismatch = bool(stored)
            else:
                stored_num = number_value(stored)
                mismatch = bool(stored) and stored_num is not None and \
                    abs(stored_num - round(acc, 4)) > 1e-9
            if mismatch:
                problems.append({
                    "code": "EXPORT_TOTALS_RECOMPUTE_CONFLICT",
                    "semantic_key": sem, "row": total.get("target_row"),
                    "detail": "%s: stored %r != computed %r"
                              % (total.get("target_tag"), stored, computed),
                    "stored": stored, "computed": computed})
            # luôn lấy kết quả tính lại — draft không được quyết định tổng
            _set_nested(data, target, computed)
    if problems and strict:
        raise ExportTotalsError(problems)
    return report


# ---------------------------------------------------------------------------
# Tự kiểm tra CLI: python -m tools.docx_render --test-all
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent.parent / "app"
FORM_MAPS_PATH = APP_DIR / "data" / "form_maps.json"
TEMPLATES_DIR = APP_DIR
OUT_TEST_DIR = Path(__file__).resolve().parent.parent / "generated_ho_so" / "_render_test"


def dummy_data_from_map(fmap: dict) -> dict:
    """Sinh dữ liệu dummy từ form_maps: text->'TEST', chk->'X', loop->2 dòng.

    section_specs (fixed-matrix/nested-grid/output-table) cũng được phủ:
    ô input nhận 'TEST', còn ô tổng/computed/outputOnly KHÔNG được gán giá trị
    giả — sau đó recompute_totals() điền số tổng từ chính các ô 'TEST'.
    """
    data: dict = {}
    for f in fmap.get("fields", []):
        data[f["key"]] = "X" if f.get("type") == "chk" else "TEST"
    for t in fmap.get("dynamic_tables", []):
        data[t["loop"]] = [{c["tag"]: "TEST" for c in t["columns"]} for _ in range(2)]
    for spec in fmap.get("section_specs", []) or []:
        kind = spec.get("kind")
        sem = spec.get("semantic_key")
        if kind == "fixed-matrix":
            editable = {r["id"] for r in spec.get("fixed_rows", [])
                        if not r.get("output_only")}
            for row_id in sorted(editable):
                for c in spec.get("columns", []):
                    if c.get("tag") and not c.get("computed"):
                        data["%s.%s.%s" % (sem, row_id, c["tag"])] = "TEST"
        elif kind == "nested-grid":
            # đã được phủ qua dynamic_tables phía trên (loop cùng tên)
            continue
        elif kind == "output-table":
            continue  # lưới chỉ để in: không có input nào
    specs = [s for s in (fmap.get("section_specs") or [])
             if s.get("kind") == "fixed-matrix"]
    if specs:
        recompute_totals(data, specs, strict=False)
    return data


def check_output(path: Path) -> tuple[bool, str]:
    """Kiểm tra bằng python-docx: file mở OK và không còn tag {..} sót."""
    try:
        import docx  # python-docx
    except ImportError:
        return False, "không import được python-docx"

    try:
        d = docx.Document(str(path))
        _ = len(d.paragraphs) + len(d.tables)  # ép đọc toàn bộ
    except Exception as exc:  # noqa: BLE001
        return False, "python-docx không mở được: %s" % exc

    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    leftovers = LEFTOVER_RE.findall(xml)
    if leftovers:
        uniq = ", ".join(sorted(set(leftovers))[:10])
        return False, "còn %d tag sót: %s" % (len(leftovers), uniq)
    return True, "OK"


def run_test_all() -> int:
    if not FORM_MAPS_PATH.exists():
        print("KHÔNG tìm thấy", FORM_MAPS_PATH)
        return 2
    maps = json.loads(FORM_MAPS_PATH.read_text(encoding="utf-8"))
    OUT_TEST_DIR.mkdir(parents=True, exist_ok=True)

    passed = failed = 0
    failures: list[str] = []
    for fid in sorted(maps):
        fmap = maps[fid]
        tpath = APP_DIR / fmap["template"]
        out = OUT_TEST_DIR / ("%s.docx" % fid)
        try:
            data = dummy_data_from_map(fmap)
            write_rendered(tpath, data, out)
            ok, msg = check_output(out)
        except Exception as exc:  # noqa: BLE001
            ok, msg = False, "lỗi render: %r" % (exc,)
        if ok:
            passed += 1
            print("PASS %s" % fid)
        else:
            failed += 1
            failures.append("%s: %s" % (fid, msg))
            print("FAIL %s: %s" % (fid, msg))

    print("-" * 60)
    print("Tổng kết: %d PASS / %d FAIL / %d mẫu" % (passed, failed, len(maps)))
    if failures:
        print("Các lỗi:")
        for line in failures:
            print(" -", line)
    print("Thư mục kết quả:", OUT_TEST_DIR)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if "--test-all" in sys.argv[1:]:
        sys.exit(run_test_all())
    print(__doc__)
    print("Dùng: python -m tools.docx_render --test-all")
    sys.exit(0)
