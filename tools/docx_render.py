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

# Phân loại role paragraph (WLAY-001): module thuần, chỉ cần ROOT trên sys.path.
# Chạy `python -m tools.docx_render` từ ROOT thì có sẵn; chạy trực tiếp như
# script thì tự thêm ROOT.
try:
    from tools.layout_roles import classify_role, fold
except ImportError:  # noqa: F401 — python tools/docx_render.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.layout_roles import classify_role, fold

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


# XML 1.0 (spec 2.2, production "Char") chỉ cho phép 3 ký tự điều khiển C0:
# tab 0x09, LF 0x0A, CR 0x0D. Phần còn lại của khối C0 (NUL, BEL, US, …), DEL
# 0x7F và khối C1 0x80-0x9F KHÔNG phải Char: đưa thẳng vào giá trị làm
# word/document.xml không well-formed -> Word từ chối mở file DOCX
# (finding F-P3-SEC-NUL). Giá trị người dùng được loại các ký tự này trước
# khi escape; tab/LF/CR được GIỮ NGUYÊN vì hợp lệ và Word cần chúng để ngắt
# dòng/đoạn. Pattern viết bằng raw string (escape \x do re tự đọc) để file
# nguồn không chứa byte điều khiển thô.
_XML_BAD_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]")


def safe_escape(val) -> str:
    """Escape giá trị dữ liệu cho XML; đồng thời vô hiệu hóa ngoặc nhọn để
    giá trị người dùng không bị đọc nhầm thành tag ở lượt thay sau.

    Ký tự điều khiển bất hợp pháp trong XML 1.0 bị loại khỏi giá trị trước
    khi escape; tab 0x09 / LF 0x0A / CR 0x0D được giữ lại vì spec 2.2 cho
    phép. Giá trị rỗng sau khi loại vẫn trả chuỗi rỗng hợp lệ."""
    return escape(
        _XML_BAD_CTRL_RE.sub("", str(val))
    ).replace("{", "&#123;").replace("}", "&#125;")


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
            printed = 0  # PHASE 4: {_stt} đếm trên dòng dữ liệu, sau khi lọc
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                # PHASE 4 row/blank-row contract (last-mile guard): dòng loop
                # mà MỌI giá trị dữ liệu trống (bỏ key nội bộ _) không trở
                # thành business data — không in hàng DOCX. Đường export JS
                # (GridCtl.exportLoops) đã lọc trước; guard này chặn payload
                # gọi render trực tiếp. Dòng chỉ có discriminator/structural
                # key (giá trị khác rỗng) vẫn được in — không mất cấu trúc.
                if not any(
                    (str(v).strip() != "") if v is not None else False
                    for k, v in item.items()
                    if not k.startswith("_")
                ):
                    continue
                printed += 1
                r = row.replace("{#%s}" % name, "").replace("{/%s}" % name, "")
                # Biến engine {_stt}: số thứ tự 1-based của dòng dữ liệu
                # (thay trước khi quét tag thường để dữ liệu không ghi đè)
                r = r.replace("{_stt}", str(printed))
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
    form_id = Path(src_path).stem
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
                    if name == "word/document.xml":
                        # Phase 5R1 (WLAY-001): loại marker source-indicator
                        # sau khi conditions/loops/subst đã chốt văn bản.
                        xml = _drop_source_indicators(xml)
                        # Phase 5R1 (WLAY-006): vô hiệu hoá field code literal
                        # sót trong template chưa regen.
                        xml = _strip_flat_field_code(xml)
                        # Phase 5R1 (WLAY-007a): bỏ paragraph rỗng cuối body
                        # (gốc rễ trang trắng M72 TNHH_2TV).
                        xml = _drop_trailing_empty_para(xml)
                        # Phase 5R2 (WLAY-002): guard render cho template chưa
                        # regen — cặp ký dọc kề nhau -> bảng 1x2 không viền.
                        xml = _horizontal_signature_tables(xml, form_id)
                        # Phase 5R2 (WLAY-003): keepNext/keepLines/cantSplit
                        # cho cụm ký — chống tách title/instr qua trang.
                        xml = _keep_signature_blocks(xml)
                        # Phase 5R2 (WLAY-004): chèn dòng trống cho
                        # vùng ký (trên title) và BẢO ĐẢM VÙNG VIẾT dưới mỗi
                        # instruction — sau khi conditions/loops đã chốt
                        # cấu trúc.
                        xml = _ensure_signature_space(xml, form_id)
                        # Phase 5R Lane C (WLAY-008/C2): pin chất lượng
                        # bảng — tblHeader hàng header thật, cantSplit mọi
                        # hàng, tblW = tổng grid (pct giữ nguyên). Đặt CUỐI
                        # để pin cả bảng 1x2 chữ ký sinh phía trên.
                        xml = _pin_table_quality(xml)
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
                    # detail KHÔNG nhúng stored/computed (P3.2/F-P3-SEC-LOG):
                    # message này đi thẳng vào errors[] trả về UI, còn giá trị
                    # người dùng thì không. Hàng + tag đủ để định vị ô lệch;
                    # giá trị thật vẫn nằm trong problems[i] để debug nội bộ.
                    "detail": "%s: tổng lưu khác tổng tính lại "
                              "(đã lọc giá trị khỏi thông báo)"
                              % (total.get("target_tag"),),
                    "stored": stored, "computed": computed})
            # luôn lấy kết quả tính lại — draft không được quyết định tổng
            _set_nested(data, target, computed)
    if problems and strict:
        raise ExportTotalsError(problems)
    return report


# ---------------------------------------------------------------------------
# Phase 5R1 (WLAY-001): role=source-indicator lộ trong DOCX
#
# UI (app_web/ui/render.js) đã BỎ role=source-indicator khỏi DOM nhưng đường
# export DOCX render template nguyên trạng nên marker kỹ thuật do bước tách
# nguồn sinh ra ("PL1 - Mau so 9: Giấy đề nghị ...") vẫn in ở trang 1 của
# đúng 44 form (docs/word_layout_audit_2026-09-03.md mục 4, đã xác minh 44/44
# template chứa marker ở body-level). Marker là metadata của pipeline, KHÔNG
# phải nội dung pháp lý của biểu mẫu -> xử lý NGAY TRƯỚC KHI XUẤT: với mọi
# paragraph CON TRỰC TIẾP của <w:body> trong word/document.xml mà
# classify_role() xếp role 'source-indicator' thì LOẠI paragraph đó.
#
# Ràng buộc:
# - Chỉ word/document.xml, chỉ con trực tiếp của w:body — KHÔNG đụng
#   header/footer, KHÔNG đụng paragraph trong w:tbl (đã quét BASE: 0 marker
#   nằm trong bảng).
# - Dòng pháp lý "Mẫu số N" (role 'form-number') phải GIỮ NGUYÊN — rule
#   source-indicator của layout_roles đứng trước và chỉ khớp dạng
#   "PL<d> - Mau so ..." nên không nhầm với form-number (test pin cả hai).
# - Form không có marker -> XML trả về NGUYÊN BẢN (byte-identical với
#   pipeline trước khi thêm bước này).
# ---------------------------------------------------------------------------

def _drop_source_indicators(xml: str) -> str:
    """Loại paragraph con trực tiếp của w:body có role 'source-indicator'.
    Trả XML mới; không có marker thì trả nguyên xml (byte-identical).
    Chỉ chạy cho word/document.xml (header/footer không có marker)."""
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    spans = _split_body_children(body)
    out: list[str] = []
    pos = 0
    dropped = 0
    for s, e in spans:
        seg = body[s:e]
        if not seg.startswith("<w:p"):
            continue
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", seg))
        if text.strip() and classify_role(fold(text)) == "source-indicator":
            out.append(body[pos:s])
            pos = e
            dropped += 1
    if not dropped:
        return xml
    out.append(body[pos:])
    return xml[:bm.start(2)] + "".join(out) + xml[bm.end(2):]


# ---------------------------------------------------------------------------
# Phase 5R1 (WLAY-007a): trang trắng do paragraph rỗng cuối body
#
# Gốc rễ (M72 variant TNHH_2TV, tái hiện từ corpus audit): đuôi body sau
# render là [...nội dung][footnote có điều kiện][paragraph RỖNG][sectPr].
# Paragraph rỗng cuối (kế thừa từ bản nguồn, spacing before=120) là con
# trực tiếp cuối ngay trước sectPr — khi nội dung trước nó lấp vừa đầy
# trang cuối, nó tự mình tràn sang trang kế và in ra trang TRẮNG 0 ký tự.
# Điều trị CÓ ĐIỀU KIỆN ngay lúc export (chung cho mọi form, không hard-code
# theo fixture, không chèn page break): chỉ xoá KHI paragraph đó
#   (a) là con trực tiếp CUỐI của body đứng ngay trước sectPr cuối, và
#   (b) rỗng hoàn toàn — không w:t có chữ, không drawing/pict (không giữ
#       nội dung nào, không đụng paragraph cuối BẢNG vì w:tbl là span riêng).
# Mất một dòng trống cuối tài liệu không mất nội dung pháp lý; khoảng trống
# vùng ký đã được _ensure_signature_space bảo đảm độc lập.
# ---------------------------------------------------------------------------

_TRAILING_EMPTY_HAS_CONTENT_RE = re.compile(
    r"<w:drawing[ >]|<w:pict[ >]|<w:object[ >]")


def _drop_trailing_empty_para(xml: str) -> str:
    """Xoá paragraph rỗng cuối body (ngay trước sectPr cuối) — gốc rễ trang
    trắng M72. Không có paragraph rỗng cuối thì trả nguyên xml."""
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    spans = _split_body_children(body)
    if len(spans) < 2:
        return xml
    last_s, last_e = spans[-1]
    if not body[last_s:last_e].startswith("<w:sectPr"):
        return xml
    prev_s, prev_e = spans[-2]
    seg = body[prev_s:prev_e]
    if not seg.startswith("<w:p"):
        return xml  # w:tbl/sectPr — không đụng
    texts = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", seg))
    if texts.strip() or _TRAILING_EMPTY_HAS_CONTENT_RE.search(seg):
        return xml  # có nội dung -> giữ nguyên
    new_body = body[:prev_s] + body[prev_e:]
    return xml[:bm.start(2)] + new_body + xml[bm.end(2):]


# ---------------------------------------------------------------------------
# Phase 5R1 (WLAY-006, guard cuối tại export): field code Word bị làm phẳng
#
# Generator (build_form_maps.drop_flat_field_code_paras) đã loại paragraph
# field code stale lúc SINH template, nhưng template hiện hành chỉ được làm
# mới bởi Lead regen. Guard này vô hiệu hoá text field code literal CÒN SÓT
# trong w:t NGAY LÚC RENDER để đường export không bao giờ in chữ rác
# ' PAGE \\* MERGEFORMAT 2' (đồng bộ ngữ pháp với detector D2 của gate và
# với FLAT_FIELD_CODE_RE của generator — 3 nơi phải giữ cùng một grammar).
# Token 'MERGEFORMAT' không phải nội dung pháp lý; chỉ xoá text của w:t,
# không đổi cấu trúc paragraph.
# ---------------------------------------------------------------------------

_FLAT_FIELD_CODE_RE = re.compile(
    r"\b(?:PAGE|NUMPAGES|TOC|HYPERLINK|SEQ|STYLEREF|IF)\s*\\\*|\bMERGEFORMAT\b")
_WT_RE = re.compile(r"(<w:t[^>]*>)([^<]*)(</w:t>)")


def _strip_flat_field_code(xml: str) -> str:
    """Vô hiệu hoá literal field code trong w:t (giữ tag, xoá text)."""
    def _repl(m: re.Match) -> str:
        return (m.group(1) + m.group(3)) if (
            m.group(2) and _FLAT_FIELD_CODE_RE.search(m.group(2))
        ) else m.group(0)
    return _WT_RE.sub(_repl, xml)


# ---------------------------------------------------------------------------
# Class 7 (defect_registry.md) + Phase 5R2 (WLAY-003/004): khối ký
#
# Bản giấy nguồn LUÔN tách dòng tiêu đề vùng ký khỏi nội dung phía trên bằng
# ít nhất một dòng trống, hoặc bằng w:spacing w:before=120 ngay trên đoạn
# title (đo tại BASE: 84 title ký nguồn — 39 case sát nội dung đều có
# spacing 120, 44 case còn lại có 1-2 đoạn trống, 1 outlier 9). Generator
# (blocks -> template) có chỗ làm RƠI dòng trống đó (vd PLI_M70: cặp
# "NGƯỜI NỘP/NGƯỜI NHẬN (Ký và ghi họ tên)" bị bó vào ô bảng, không còn
# dòng trống lẫn spacing -> in ra không có chỗ ký). Blocks là generated
# NÊN KHÔNG sửa generated blocks: xử lý NGAY TRƯỚC KHI XUẤT — với mọi
# paragraph document.xml chứa marker title ký "(Ký…"/"(Đã ký…)", nếu
# KHÔNG có đoạn trống liền trước trong cùng container (body/ô bảng) và
# KHÔNG có spacing before >= 120 thì chèn một paragraph rỗng ngay trước.
# Chỉ THÊM khoảng trống, không đổi chữ/số đoạn có nội dung.
#
# Phase 5R2 bổ sung hai nội dung:
#
# WLAY-003 (_keep_signature_blocks): khối ký bị tách qua trang — instruction
# rơi đầu trang trong khi title nằm trang trước (SIG_SPLIT: PLI_M09 trang 5,
# PLII_M25). Ở mức XML có chủ đích (không hard-code page break):
#   - paragraph chứa instruction "(Ký…"/"(Đã ký…" -> w:keepLines (cụm
#     title+instr trong MỘT paragraph qua w:br không bị xẻ dòng);
#   - paragraph title ký NGAY TRƯỚC instruction trong cùng container ->
#     w:keepNext + w:keepLines (title dính theo instr);
#   - bảng chứa khối ký (sau WLAY-002 regen: bảng 1x2) -> w:tr/w:cantSplit
#     cho mọi hàng (hàng ký không bị xẻ giữa trang).
# Chỉ THÊM thuộc tính khi chưa có (idempotent — render 2 lần cùng bytes).
#
# WLAY-004 (_ensure_signature_space mở rộng): MỖI cụm ký — không chỉ cụm
# cuối — phải có vùng viết dọc dưới instruction. Nếu NGAY SAU paragraph
# instruction (sau một chuỗi paragraph rỗng nếu có) là nội dung chữ kế tiếp
# trong cùng container mà khoảng dọc ước tính < ngưỡng contract
# (min_write_gap_pt của form trong tools/phase5r_expectations.json; mặc định
# 480 twips ~ 2 dòng trống) thì chèn MỘT paragraph đệm exact-height ngay sau
# instruction (chỉ THÊM khoảng, không đổi chữ, không đụng paragraph khác).
# Trong bảng: đệm nằm trong ô (row height/spacing trong ô).
# ---------------------------------------------------------------------------

_SIG_TITLE_RE = re.compile(r"\((?:Ký|Đã ký)")
_SIG_MIN_SPACE_TWIPS = 120
_SIG_WRITE_DEFAULT_TWIPS = 480      # 2 dòng trống ~ vùng viết tối thiểu
_SIG_WRITE_SAFETY_TWIPS = 60        # dự phòng sai số metric dòng khi in
_SIG_SPACING_RE = re.compile(r'<w:spacing[^>]*w:before="(\d+)"')
# token quét tuần tự: biên container (ô bảng/bảng) hoặc một paragraph.
# NHÁNH có cặp đóng phải đứng TRƯỚC ([ >] loại luôn '/'), nếu không
# "<w:p/>" sẽ bị nhánh đầu nuốt chung với paragraph kế tiếp.
_SIG_TOKEN_RE = re.compile(
    r"<w:tc[ >]|</w:tc>|<w:tbl[ >]|</w:tbl>"
    r"|<w:p[ >].*?</w:p>|<w:p[^>]*/>", re.S)
_SIG_T_RE = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")

_EXPECT_PATH = Path(__file__).resolve().parent.parent / "tools" / \
    "phase5r_expectations.json"
_EXPECT_CACHE: dict | None = None


def _signature_expectations() -> dict:
    """Registry kỳ vọng khối ký (đọc 1 lần; vắng mặt/hỏng -> {})."""
    global _EXPECT_CACHE
    if _EXPECT_CACHE is None:
        try:
            _EXPECT_CACHE = json.loads(
                _EXPECT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _EXPECT_CACHE = {}
    return _EXPECT_CACHE


def _sig_write_min_twips(form_id: str | None) -> int:
    """Ngưỡng vùng viết dưới instruction (twips): min_write_gap_pt × 20 của
    contract nếu form có khai; ngược lại mặc định 2 dòng trống (480)."""
    sig = ((_signature_expectations().get(form_id or "") or {})
           .get("signature") or {})
    gap_pt = sig.get("min_write_gap_pt")
    try:
        return max(0, int(round(float(gap_pt) * 20)))
    except (TypeError, ValueError):
        return _SIG_WRITE_DEFAULT_TWIPS


def _sig_para_text(p_xml: str) -> str:
    return "".join(_SIG_T_RE.findall(p_xml))


def _ppr_add_flag(p_xml: str, flag: str) -> str:
    """Thêm flag (<w:keepNext/>|<w:keepLines/>) vào pPr của paragraph theo
    đúng thứ tự schema (ngay sau w:pStyle nếu có). Idempotent: đã có -> giữ
    nguyên bytes."""
    if flag in p_xml:
        return p_xml
    m = re.match(r"<w:p(?:\s[^>]*)?>", p_xml)
    if not m:
        return p_xml  # <w:p/> tự đóng — không có pPr để thêm
    head, rest = m.group(0), p_xml[m.end():]
    if rest.startswith("<w:pPr>"):
        at = len("<w:pPr>")
        sm = re.match(r"(<w:pStyle[^>]*/>)", rest[at:])
        if sm:
            at += sm.end()
        return head + rest[:at] + flag + rest[at:]
    return head + "<w:pPr>" + flag + "</w:pPr>" + rest


def _sig_title_only(text: str) -> bool:
    """Paragraph NHÁN người ký (chỉ title, không paren instruction): chữ IN
    ngắn. Dùng cho cặp title-para + instr-para chạy kề."""
    t = text.strip()
    if not t or _SIG_TITLE_RE.search(t) or len(t) > 80:
        return False
    alpha = [c for c in t if c.isalpha()]
    return len(alpha) >= 4 and sum(c.isupper() for c in alpha) / len(alpha) >= 0.6


def _keep_signature_blocks(xml: str) -> str:
    """WLAY-003: keepLines/keepNext cho cụm ký + cantSplit cho hàng bảng ký.
    Trả XML mới; cụm đã mang thuộc tính -> bytes giữ nguyên (idempotent).

    Pass 1 — paragraph: token-walk theo container; paragraph chứa instruction
    "(Ký…"/"(Đã ký…" nhận keepLines; nếu NGAY TRƯỚC nó (cùng container) là
    paragraph nhãn IN HOA thì nhãn đó nhận keepNext+keepLines.
    Pass 2 — bảng: bảng có <=4 hàng và MỌI hàng đều chứa ô instruction ký ->
    cantSplit cho từng hàng chưa có (hàng ký không bị xẻ giữa trang)."""
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)

    # --- pass 1: paragraph-level keep ---
    # Title para NGAY TRƯỚC instr para được GIỮ LẠI (buffer) đến khi biết
    # token kế tiếp: là instr -> flush với keepNext+keepLines; khác -> flush
    # nguyên trạng. Idempotent: đã có flag thì bytes giữ nguyên.
    out: list[str] = []
    pos = 0
    pending: tuple[int, int, str] | None = None  # (start, end, tok) title treo

    def _flush(with_keep: bool) -> None:
        nonlocal pending, pos
        if pending is not None:
            s, e, tok = pending
            out.append(body[pos:s])
            if with_keep:
                # thứ tự schema: keepNext TRƯỚC keepLines — chèn keepLines
                # trước rồi keepNext cùng vị trí (sau pStyle) giữ đúng thứ tự
                tok = _ppr_add_flag(
                    _ppr_add_flag(tok, "<w:keepLines/>"), "<w:keepNext/>")
            out.append(tok)
            pos = e
            pending = None

    for m in _SIG_TOKEN_RE.finditer(body):
        tok = m.group(0)
        if tok.startswith("<w:tc") or tok in ("</w:tc>", "</w:tbl>") \
                or tok.startswith("<w:tbl"):
            _flush(False)
            out.append(body[pos:m.end()])
            pos = m.end()
            continue
        text = _sig_para_text(tok)
        if _SIG_TITLE_RE.search(text):
            _flush(True)   # title treo liền trước instr -> keepNext+keepLines
            out.append(body[pos:m.start()])
            out.append(_ppr_add_flag(tok, "<w:keepLines/>"))
            pos = m.end()
            continue
        if text.strip() and _sig_title_only(text):
            # nhãn IN HOA — giữ lại chờ token kế tiếp (title của cụm?)
            out.append(body[pos:m.start()])
            pos = m.start()
            pending = (m.start(), m.end(), tok)
            continue
        _flush(False)
        out.append(body[pos:m.end()])
        pos = m.end()
    _flush(False)
    out.append(body[pos:])
    body = "".join(out)   # không đổi khi không có cụm ký (ghép lại nguyên vẹn)

    # --- pass 2: table row cantSplit (thay từ cuối lên đầu để giữ offset) ---
    segs = list(_iter_balanced_tbls(body))
    for start, end in reversed(segs):
        seg = body[start:end]
        rows = ROW_RE.findall(seg)
        if not rows or len(rows) > _SIG_TABLE_MAX_ROWS:
            continue
        if not all(
                any(_SIG_TITLE_RE.search(_sig_para_text(p))
                    for p in re.findall(r"<w:p[ >].*?</w:p>|<w:p[^>]*/>",
                                        row, re.S))
                for row in rows):
            continue
        new_seg = _add_rows_cantsplit(seg, rows)
        if new_seg != seg:
            body = body[:start] + new_seg + body[end:]
    return xml[:bm.start(2)] + body + xml[bm.end(2):]


# Bảng ký cần khoá hàng: giới hạn số hàng (bảng 1x2 sau WLAY-002 là 1 hàng)
_SIG_TABLE_MAX_ROWS = 4


def _iter_balanced_tbls(body: str):
    """Trả (start, end) của MỖI bảng cân bằng (chịu được bảng lồng nhau)."""
    pos = 0
    while True:
        m = re.search(r"<w:tbl[ >]", body[pos:])
        if not m:
            return
        start = pos + m.start()
        depth = 1
        scan = pos + m.end()
        while depth:
            mm = re.search(r"<w:tbl[ >]|</w:tbl>", body[scan:])
            if not mm:
                raise ValueError("w:tbl khong dong trong body")
            depth += -1 if mm.group(0).startswith("</") else 1
            scan += mm.end()
        yield start, scan
        pos = scan


def _add_rows_cantsplit(seg: str, rows: list[str]) -> str:
    """Chèn <w:trPr><w:cantSplit/></w:trPr> vào từng hàng chưa có (trPr là
    con đầu của w:tr theo schema)."""
    out = seg
    for row in rows:
        if "<w:cantSplit/>" in row:
            continue
        m = re.match(r"<w:tr((?:\s[^>]*)?)>", row)
        if not m:
            continue
        old_open = m.group(0)
        rest = row[len(old_open):]
        if rest.startswith("<w:trPr>"):
            new_row = old_open + "<w:trPr><w:cantSplit/>" + \
                rest[len("<w:trPr>"):]
        else:
            new_row = old_open + "<w:trPr><w:cantSplit/></w:trPr>" + rest
        out = out.replace(row, new_row, 1)
    return out


def _ensure_signature_space(xml: str, form_id: str | None = None) -> str:
    """Class 7 + WLAY-004: (a) mỗi title vùng ký có >=1 dòng trống phía trên
    trong cùng container (hoặc spacing before đủ) — hành vi cũ giữ nguyên;
    (b) MỖI instruction ký có vùng viết dọc đạt ngưỡng contract trước nội
    dung chữ kế tiếp trong cùng container (chèn paragraph đệm exact-height
    ngay sau instruction — chỉ thêm khoảng, không đổi chữ)."""
    min_write = _sig_write_min_twips(form_id)
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    paras = list(_SIG_TOKEN_RE.finditer(body))
    # CẶP token với phần tử kế tiếp trong cùng container để tính vùng viết
    inserts: list[tuple[int, int, str]] = []   # (start, end, spacer_xml)
    for idx, m in enumerate(paras):
        tok = m.group(0)
        if not tok.startswith("<w:p"):
            continue
        text = _sig_para_text(tok)
        if not _SIG_TITLE_RE.search(text):
            continue
        # (a) dòng trống phía trên title — hành vi Class 7 cũ
        prev_empty = False
        for j in range(idx - 1, -1, -1):
            ptok = paras[j].group(0)
            if ptok.startswith("<w:tc") or ptok in ("</w:tc>", "</w:tbl>") \
                    or ptok.startswith("<w:tbl"):
                break
            if ptok.startswith("<w:p"):
                prev_empty = _sig_para_text(ptok).strip() == ""
                # chỉ para liền kề mới quyết định (đúng hành vi cũ)
                break
        sp = _SIG_SPACING_RE.search(tok)
        has_space = bool(sp and int(sp.group(1)) >= _SIG_MIN_SPACE_TWIPS)
        if not prev_empty and not has_space:
            # (a) chèn dòng trống ngay TRƯỚC title — giữ hành vi Class 7
            inserts.append((m.start(), m.start(), "<w:p/>"))
        # (b) vùng viết dưới instruction — Phase 5R2
        # dò trong cùng container: chuỗi paragraph rỗng rồi tới paragraph có
        # chữ (F) hoặc biên container/kết thúc.
        existing = 0
        f_text = ""
        for j in range(idx + 1, len(paras)):
            ntok = paras[j].group(0)
            if ntok.startswith("<w:tc") or ntok in ("</w:tc>", "</w:tbl>") \
                    or ntok.startswith("<w:tbl"):
                break
            if not ntok.startswith("<w:p"):
                continue
            ntext = _sig_para_text(ntok)
            if ntext.strip():
                sp2 = _SIG_SPACING_RE.search(ntok)
                existing += int(sp2.group(1)) if sp2 else 0
                f_text = ntext
                break
            sp2 = _SIG_SPACING_RE.search(ntok)
            existing += 240 + (int(sp2.group(1)) if sp2 else 0)
        if f_text and existing < min_write:
            deficit = min_write + _SIG_WRITE_SAFETY_TWIPS - existing
            spacer = ("<w:p><w:pPr>"
                      '<w:spacing w:before="0" w:after="0" w:line="%d" '
                      'w:lineRule="exact"/></w:pPr></w:p>' % deficit)
            inserts.append((m.end(), m.end(), spacer))
    if not inserts:
        return xml
    out: list[str] = []
    pos = 0
    for s, e, seg in inserts:
        if s < pos:
            continue  # đè nhau (không xảy ra: mỗi paragraph một insert)
        out.append(body[pos:s])
        out.append(seg)
        pos = e
    out.append(body[pos:])
    return xml[:bm.start(2)] + "".join(out) + xml[bm.end(2):]


# ---------------------------------------------------------------------------
# Phase 5R2 (WLAY-002 render guard): cụm 2 chữ ký NGANG cho form đã pin
#
# Generator (build_form_maps.build_horizontal_signature_tables) đã sinh bảng
# không viền 1x2 lúc REGEN — nhưng template production chỉ được làm mới bởi
# Lead regen. Trong thời gian template chưa regen, guard này hợp nhất cặp
# paragraph ký dọc chạy kề thành bảng 1x2 NGAY LÚC RENDER (chỉ form có
# registry pin horizontal — hiện là PLI_M70). Khi Lead regen xong, template
# đã mang sẵn bảng nên guard rút về no-op (không còn cặp paragraph dọc).
# ---------------------------------------------------------------------------

def _horizontal_signature_tables(xml: str, form_id: str | None) -> str:
    """Registry pin horizontal + 2 title -> khối ký dọc được thay bằng bảng
    không viền 1 hàng × 2 ô NGAY LÚC RENDER (guard cho template chưa regen;
    Lead regen xong thì template đã mang bảng 1x2 và guard rút về no-op).
    Hai dạng nguồn được hỗ trợ (đồng bộ generator):
      (a) cặp paragraph ký dọc kề nhau ở body-level;
      (b) bảng 2 hàng × 1 cột — mỗi ô chứa đúng 1 cụm ký khớp titles[i]
          (template production PLI_M70 hiện hành là dạng này).
    Ô mới: paragraph cụm ký gốc (khôi phục jc=center + spacing before=120
    theo bản nguồn nếu thiếu) + spacer exact 240 twips làm vùng viết."""
    sig = ((_signature_expectations().get(form_id or "") or {})
           .get("signature") or {})
    if sig.get("orientation") != "horizontal" or sig.get("signers") != 2:
        return xml
    titles_folded = [re.sub(r"\s+", " ", fold(t)).strip()
                     for t in (sig.get("titles") or [])]
    if len(titles_folded) != 2:
        return xml

    def _logical_lines(p_xml: str) -> list[str]:
        logical: list[str] = [""]
        for m2 in re.finditer(r"<w:t[^>]*>([^<]*)</w:t>|<w:br/?>", p_xml):
            if m2.group(0).startswith("<w:br"):
                logical.append("")
            else:
                logical[-1] += m2.group(1)
        return [ln for ln in logical if ln.strip()]

    def _para_matches(p_xml: str, title_folded: str) -> bool:
        lines = _logical_lines(p_xml)
        if not any(re.search(r"\((?:ky|da ky)", fold(ln)) for ln in lines):
            return False
        return any(
            re.sub(r"\s+", " ", fold(ln)).strip() == title_folded
            for ln in lines)

    def _cell_sig_para(tc_xml: str, title_folded: str) -> str | None:
        for p_xml in re.findall(r"<w:p[ >].*?</w:p>|<w:p[^>]*/>", tc_xml,
                                re.S):
            if _para_matches(p_xml, title_folded):
                return p_xml
        return None

    def _cell_wrap(cell_w: int, p_xml: str) -> str:
        if "<w:jc" not in p_xml:
            p_xml = p_xml.replace(
                "<w:p>",
                '<w:p><w:pPr><w:jc w:val="center"/>'
                '<w:spacing w:before="120"/></w:pPr>', 1)
        return (
            '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'
            "<w:tcBorders>"
            '<w:top w:val="nil"/><w:left w:val="nil"/>'
            '<w:bottom w:val="nil"/><w:right w:val="nil"/>'
            "</w:tcBorders></w:tcPr>"
            "%s"
            "<w:p><w:pPr>"
            '<w:spacing w:before="0" w:after="0" w:line="240" '
            'w:lineRule="exact"/></w:pPr></w:p></w:tc>' % (cell_w, p_xml))

    def _table(total_w: int, cell_w: int, cells_xml: list[str]) -> str:
        grid = "".join('<w:gridCol w:w="%d"/>' % cell_w for _ in range(2))
        return (
            "<w:tbl><w:tblPr>"
            '<w:tblW w:w="%d" w:type="dxa"/>'
            "<w:tblBorders>"
            '<w:top w:val="nil"/><w:left w:val="nil"/>'
            '<w:bottom w:val="nil"/><w:right w:val="nil"/>'
            '<w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
            "</w:tblBorders>"
            '<w:tblLayout w:type="fixed"/>'
            "</w:tblPr>"
            "<w:tblGrid>%s</w:tblGrid>"
            "<w:tr><w:trPr><w:cantSplit/>"
            '<w:trHeight w:val="1200" w:hRule="atLeast"/></w:trPr>'
            "%s</w:tr></w:tbl>" % (total_w, grid, "".join(cells_xml)))

    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    spans = _split_body_children(body)
    total_w = 8640   # 12240 pgSz - 1800*2 pgMar (khổ chuẩn corpus)
    cell_w = total_w // 2

    # (a) cặp paragraph dọc kề nhau
    for i in range(len(spans) - 1):
        s1, e1 = spans[i]
        s2, e2 = spans[i + 1]
        p1, p2 = body[s1:e1], body[s2:e2]
        if not (p1.startswith("<w:p") and p2.startswith("<w:p")):
            continue
        if not (_para_matches(p1, titles_folded[0])
                and _para_matches(p2, titles_folded[1])):
            continue
        tbl = _table(total_w, cell_w, [_cell_wrap(cell_w, p1),
                                       _cell_wrap(cell_w, p2)])
        new_body = body[:s1] + tbl + body[e1:s2] + body[e2:]
        return xml[:bm.start(2)] + new_body + xml[bm.end(2):]

    # (b) bảng 2 hàng × 1 cột chứa 2 cụm ký
    for s, e in spans:
        seg = body[s:e]
        if not seg.startswith("<w:tbl"):
            continue
        rows = ROW_RE.findall(seg)
        if len(rows) != 2:
            continue
        cell_paras: list[str] = []
        ok = True
        for ri, row in enumerate(rows):
            tcs = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
            if len(tcs) != 1:
                ok = False
                break
            p_xml = _cell_sig_para(tcs[0], titles_folded[ri])
            if p_xml is None:
                ok = False
                break
            cell_paras.append(p_xml)
        if not ok:
            continue
        tbl = _table(total_w, cell_w, [_cell_wrap(cell_w, p)
                                       for p in cell_paras])
        new_body = body[:s] + tbl + body[e:]
        return xml[:bm.start(2)] + new_body + xml[bm.end(2):]
    return xml


# ---------------------------------------------------------------------------
# Phase 5R Lane C (WLAY-008/C2): pin chất lượng bảng lúc render
#
# Với MỌI bảng trong body (không chỉ bảng rộng), render must guarantee:
#   (a) tblHeader  — hàng tiêu đề thật lặp lại khi bảng tràn trang. "Header
#       thật" = hàng 0 có chữ và KHÔNG phải band quốc hiệu (heuristic
#       is_header_band_table của docx_to_blocks: ô đầu "TÊN DOANH NGHIỆP"/
#       "TÊN HỘ KINH DOANH" + cả bảng chứa khối quốc hiệu). Hàng tier-2 của
#       header nhiều tầng (có ô vMerge-continuation) cũng được mark để Word
#       repeat CẢ KHỐI header (w:tblHeader chỉ có tác dụng với các hàng đầu
#       liên tiếp).
#   (b) cantSplit  — mọi hàng (kể cả bảng lồng) không bị xẻ qua trang. Hàng
#       cao hơn 1 trang Word tự xử (cantSplit vẫn an toàn theo spec OOXML).
#   (c) tblW       — bảng khai width dxa ĐÚNG tổng gridCol; thiếu/sai/type
#       auto -> set; type="pct" giữ nguyên.
#
# Idempotent: mọi lần chèn đều kiểm tra tồn tại trước; bảng đã đủ pin -> xml
# trả về NGUYÊN byte. Không đụng nội dung pháp lý/số hàng/cột.
# ---------------------------------------------------------------------------

_TRPR_ORDER = ("w:cnfStyle", "w:divId", "w:gridBefore", "w:gridAfter",
               "w:wBefore", "w:wAfter", "w:cantSplit", "w:trHeight",
               "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden")
_TRPR_INDEX = {name: i for i, name in enumerate(_TRPR_ORDER)}
_TR_TOKEN_RE = re.compile(r"<w:tr[ >]|</w:tr>|<w:tbl[ >]|</w:tbl>")
# band quốc hiệu (replicate docx_to_blocks.is_header_band_table ở lớp xml)
_BAND_FIRST_CELL = ("TÊN DOANH NGHIỆP", "TÊN HỘ KINH DOANH")
_BAND_MOTTO = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
_VMERGE_CONTINUE_RE = re.compile(
    r'<w:vMerge(?:\s+w:val="(?:continue|true)")?\s*/>')


def _row_visible_text(seg: str) -> str:
    texts = re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", seg)
    return "".join(texts).strip()


def _trpr_add_props(row_seg: str, props: list[str]) -> str:
    """Chèn các property (vd '<w:cantSplit/>') vào trPr của hàng, đặt đúng
    vị trí theo thứ tự schema CT_TrPr. Đã có property thì bỏ qua."""
    need = [p for p in props if p not in row_seg]
    if not need:
        return row_seg
    m = re.match(r"<w:tr((?:\s[^>]*)?)>", row_seg)
    if not m:
        return row_seg
    open_tag = m.group(0)
    rest = row_seg[m.end():]

    def _order(p: str) -> int:
        return _TRPR_INDEX.get(
            "w:" + re.match(r"<w:(\w+)", p).group(1), 99)

    need.sort(key=_order)
    if rest.startswith("<w:trPr>"):
        inner_end = rest.index("</w:trPr>")
        inner = rest[len("<w:trPr>"):inner_end]
        tail = rest[inner_end:]
        for p in need:
            tag = "w:" + re.match(r"<w:(\w+)", p).group(1)
            idx = _TRPR_INDEX.get(tag, 99)
            placed = False
            for ex in re.finditer(r"<w:(\w+)[ />]", inner):
                ex_tag = "w:" + ex.group(1)
                if _TRPR_INDEX.get(ex_tag, 99) > idx:
                    inner = inner[:ex.start()] + p + inner[ex.start():]
                    placed = True
                    break
            if not placed:
                inner = inner + p
        return open_tag + "<w:trPr>" + inner + tail
    return open_tag + "<w:trPr>" + "".join(need) + "</w:trPr>" + rest


def _pin_tblw(seg: str) -> str:
    """tblW type='dxa' w:w = tổng gridCol (missing/auto/sai -> set; pct giữ)."""
    grid_m = re.search(r"<w:tblGrid>(.*?)</w:tblGrid>", seg, re.S)
    if not grid_m:
        return seg
    cols = [int(w) for w in re.findall(
        r'<w:gridCol[^>]*w:w="(\d+)"', grid_m.group(1))]
    if not cols:
        return seg
    total = sum(cols)
    tw = re.search(r"<w:tblW\b[^>]*?/>", seg)
    if tw:
        old = tw.group(0)
        if 'w:type="pct"' in old:
            return seg
        mw = re.search(r'w:w="(\d+)"', old)
        if mw and int(mw.group(1)) == total and 'w:type="dxa"' in old:
            return seg  # đã đúng -> nguyên byte
        new = '<w:tblW w:w="%d" w:type="dxa"/>' % total
        return seg[:tw.start()] + new + seg[tw.end():]
    # thiếu -> chèn vào tblPr trước phần tử đầu thuộc nhóm sau tblW
    new = '<w:tblW w:w="%d" w:type="dxa"/>' % total
    tblpr = re.search(r"<w:tblPr/>|<w:tblPr>.*?</w:tblPr>", seg, re.S)
    if not tblpr:
        return seg
    old = tblpr.group(0)
    if old == "<w:tblPr/>":
        return seg[:tblpr.start()] + "<w:tblPr>" + new + "</w:tblPr>" + \
            seg[tblpr.end():]
    insert_at = None
    for ex in re.finditer(r"<w:(\w+)[ />]", old):
        if ex.group(1) in ("tblJc", "tblBorders", "tblLayout", "tblCellMar",
                           "tblLook", "tblCaption", "tblDescription"):
            insert_at = ex.start()
            break
    if insert_at is None:
        insert_at = len(old) - len("</w:tblPr>")
    new_pr = old[:insert_at] + new + old[insert_at:]
    return seg[:tblpr.start()] + new_pr + seg[tblpr.end():]


def _header_row_count(seg: str, rows: list[str]) -> int:
    """Số hàng đầu được mark tblHeader: 0 nếu không phải header thật; nếu
    header thật thì + các hàng tier tiếp theo đang vMerge-continuation."""
    if len(rows) < 2:
        return 0
    if not _row_visible_text(rows[0]):
        return 0
    first = _row_visible_text(rows[0])
    if any(k in first for k in _BAND_FIRST_CELL) and _BAND_MOTTO in seg:
        return 0  # band layout quốc hiệu — không phải header cột
    n = 1
    for row in rows[1:3]:
        if _VMERGE_CONTINUE_RE.search(row):
            n += 1
        else:
            break
    return n


def _pin_one_table(seg: str, top_level: bool) -> str:
    """Pin một bảng (đệ quy cho bảng lồng): tblW + cantSplit/tblHeader."""
    # 1. tblW (mọi tầng bảng đều đáng pin)
    seg = _pin_tblw(seg)
    # 2. đếm hàng header trước khi biến đổi chuỗi
    n_hdr = _header_row_count(seg, _direct_tbl_rows(seg)) if top_level else 0
    # 3. xử lý ngược thứ tự để offset không trôi; bảng lồng được đệ quy trước
    spans = _direct_tbl_rows_spans(seg)
    for s, e in reversed(spans):
        row = seg[s:e]
        # bảng lồng bên trong ô -> pin đệ quy (chỉ cantSplit + tblW)
        for ns, ne in _iter_tbls_in(row):
            inner = row[ns:ne]
            pinned_inner = _pin_one_table(inner, top_level=False)
            if pinned_inner != inner:
                row = row[:ns] + pinned_inner + row[ne:]
        props = ["<w:cantSplit/>"]
        if n_hdr and _row_index_of(spans, (s, e)) < n_hdr:
            props.append("<w:tblHeader/>")
        new_row = _trpr_add_props(row, props)
        if new_row != row:
            seg = seg[:s] + new_row + seg[e:]
    return seg


def _row_index_of(spans: list, span: tuple) -> int:
    for i, sp in enumerate(spans):
        if tuple(sp) == span:
            return i
    return -1


def _iter_tbls_in(seg: str):
    """(start, end) bảng lồng NGAY TRONG seg (depth 1 tương đối)."""
    pos = 0
    depth = 0
    while True:
        m = re.search(r"<w:tbl[ >]|</w:tbl>", seg[pos:])
        if not m:
            return
        tok = m.group(0)
        if tok.startswith("<w:tbl"):
            if depth == 0:
                start = pos + m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                yield start, pos + m.end()
        pos += m.end()


def _direct_tbl_rows(seg: str) -> list[str]:
    return [seg[s:e] for s, e in _direct_tbl_rows_spans(seg)]


def _direct_tbl_rows_spans(seg: str) -> list[tuple[int, int]]:
    """(start, end) các hàng TRỰC TIẾP của bảng (seg gồm cả tag mở bảng)."""
    spans = []
    pos = 0
    tbl_depth = 0
    while True:
        m = _TR_TOKEN_RE.search(seg, pos)
        if not m:
            break
        tok = m.group(0)
        if tok.startswith("<w:tbl"):
            tbl_depth += 1
            pos = m.end()
            continue
        if tok == "</w:tbl>":
            tbl_depth -= 1
            pos = m.end()
            continue
        if tok.startswith("<w:tr"):
            if tbl_depth == 1:
                d = 1
                scan = m.end()
                while d:
                    mm = re.search(r"<w:tr[ >]|</w:tr>", seg[scan:])
                    d += -1 if mm.group(0) == "</w:tr>" else 1
                    scan += mm.end()
                spans.append((m.start(), scan))
                pos = scan
                continue
            pos = m.end()
            continue
        pos = m.end()
    return spans


def _pin_table_quality(xml: str) -> str:
    """WLAY-008/C2: pin tblHeader/cantSplit/tblW cho mọi bảng trong body.
    Idempotent; không đụng bảng đã đúng (byte-identical)."""
    bm = _BODY_RE.search(xml)
    if not bm:
        return xml
    body = bm.group(2)
    out: list[str] = []
    pos = 0
    for s, e in _iter_balanced_tbls(body):
        if s < pos:
            continue  # bảng lồng đã nằm trong span cha đã xử lý
        seg = body[s:e]
        out.append(body[pos:s])
        out.append(_pin_one_table(seg, top_level=True))
        pos = e
    out.append(body[pos:])
    return xml[:bm.start(2)] + "".join(out) + xml[bm.end(2):]


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
