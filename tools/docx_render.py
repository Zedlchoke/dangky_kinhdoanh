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


def render(template_path: str | os.PathLike, data: dict) -> bytes:
    """Render template thành nội dung file .docx mới (bytes).

    Không đụng vào file template nguồn — mọi thứ diễn ra trong bộ nhớ.
    """
    src_path = os.fspath(template_path)
    buf = io.BytesIO()
    with zipfile.ZipFile(src_path, "r") as src:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                raw = src.read(info.filename)
                name = info.filename.replace("\\", "/")
                if _RENDER_PART_RE.match(name):
                    xml = raw.decode("utf-8")
                    xml = _apply_conditions(xml, data)
                    xml = _expand_loops(xml, data)
                    xml = _subst_vars(xml, data)
                    raw = xml.encode("utf-8")
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = info.external_attr
                dst.writestr(zi, raw)
    return buf.getvalue()


def write_rendered(template_path: str | os.PathLike, data: dict, out_path: str | os.PathLike) -> None:
    """Tiện ích: render rồi ghi ra file."""
    content = render(template_path, data)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(content)


# ---------------------------------------------------------------------------
# Tự kiểm tra CLI: python -m tools.docx_render --test-all
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent.parent / "app"
FORM_MAPS_PATH = APP_DIR / "data" / "form_maps.json"
TEMPLATES_DIR = APP_DIR
OUT_TEST_DIR = Path(__file__).resolve().parent.parent / "generated_ho_so" / "_render_test"


def dummy_data_from_map(fmap: dict) -> dict:
    """Sinh dữ liệu dummy từ form_maps: text->'TEST', chk->'X', loop->2 dòng."""
    data: dict = {}
    for f in fmap.get("fields", []):
        data[f["key"]] = "X" if f.get("type") == "chk" else "TEST"
    for t in fmap.get("dynamic_tables", []):
        data[t["loop"]] = [{c["tag"]: "TEST" for c in t["columns"]} for _ in range(2)]
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
