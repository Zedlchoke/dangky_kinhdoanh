#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""table_coverage_audit.py — coverage matrix 2 chiều cho 111 section business-table.

Wave B (coverage lane), PLAN v4. Đọc-only toàn bộ dữ liệu nguồn:

  * ``app/data/table_specs/manifest.json``      — census 87 form / 111 section
  * ``tools/census/build_manifest.py``          — LEAD_STATUS_OVERRIDES (key (form, section))
  * ``app/data/form_maps.json``                 — dynamic_tables / section_specs
  * ``app/data/blocks/<form_id>.json``          — blocks L0 (loop / table / chk / p)
  * ``tools/form_specs/{change,core,formation,household,publication}/<fid>.json``
  * ``app/templates/<form_id>.docx``            — đếm w:tbl bằng python-docx (structural)
  * ``app_web/ui/form-domain.js`` + ``app_web/ui/app.js`` — runtime contract
    (GRID_META / FORM_GRID_META / FORM_TABLE_CONTRACTS) + presence của
    section/loop key cho draft/validation. CHỈ ĐỌC bằng text scan.

Tool dựng 1 hàng / section với evidence từng stage, suy ``final_status``
bằng hàm thuần :func:`derive_final_status`, chạy gate 2 chiều (manifest vs
evidence), ghi ``docs/table_coverage_current.json`` + ``.md`` rồi:

  * exit 0  — không drift;
  * exit != 0 — có drift (in từng dòng). Drift là KẾT QUẢ ĐÚNG của audit,
    KHÔNG sửa manifest/blocks để qua gate.

Hai xử lý evidence cần lưu ý (đều chỉ dùng dữ liệu có sẵn, không suy diễn):

  * chk token trong notes là TIỀN TỐ ('chk_khu_' khớp 'chk_khu_cong_nghiep');
  * section semantic_key có thể khác tên loop implementation ('nganh_bo' vs
    'nganh_xoa_bo') — bridge CHỈ qua tên loop nêu tường minh trong
    ``LEAD_STATUS_OVERRIDES[..]['evidence']`` của chính section đó.

Chạy:
    python3 -X utf8 -m tools.census.table_coverage_audit
Selftest:
    python3 -X utf8 tools/test_table_coverage_audit.py
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, OrderedDict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANIFEST_PATH = os.path.join(REPO, "app", "data", "table_specs", "manifest.json")
FORM_MAPS_PATH = os.path.join(REPO, "app", "data", "form_maps.json")
BLOCKS_DIR = os.path.join(REPO, "app", "data", "blocks")
SPECS_DIRS = ("change", "core", "formation", "household", "publication")
SPECS_ROOT = os.path.join(REPO, "tools", "form_specs")
BUILD_MANIFEST_PY = os.path.join(REPO, "tools", "census", "build_manifest.py")
TEMPLATES_DIR = os.path.join(REPO, "app", "templates")
FORM_DOMAIN_JS = os.path.join(REPO, "app_web", "ui", "form-domain.js")
APP_JS = os.path.join(REPO, "app_web", "ui")
OUT_JSON = os.path.join(REPO, "docs", "table_coverage_current.json")
OUT_MD = os.path.join(REPO, "docs", "table_coverage_current.md")

EXPECTED_SECTIONS = 111

# ---------------------------------------------------------------- constants
STAGE_KEYS = ("spec", "template", "form_maps", "blocks", "runtime",
              "draft", "validation")

FINAL_IMPLEMENTED = "IMPLEMENTED_VERIFIED"
FINAL_PARTIAL = "PARTIAL_COLUMNS"
FINAL_MISSING = "MISSING_IMPLEMENTATION"
FINAL_BLOCKED = "BLOCKED_OWNER"
FINAL_NO_TABLE = "NO_TABLE"
FINAL_OUTPUT_ONLY = "OUTPUT_ONLY"
FINAL_REMOVED = "REMOVED_BY_CURRENT_LAW"
FINAL_STATUSES = (FINAL_IMPLEMENTED, FINAL_PARTIAL, FINAL_MISSING,
                  FINAL_BLOCKED, FINAL_NO_TABLE, FINAL_OUTPUT_ONLY,
                  FINAL_REMOVED)

# manifest status được gate coi là "đã implement"
MANIFEST_IMPLEMENTED_STATUSES = ("already_complete", "implemented")

_RE_BLOCKER = re.compile(
    r"(?i)blocker|blocked|ch[oờ]\s+(lead|owner|ph[oó]p\s+l[ýı])|pending\s+legal")
_RE_REMOVED_LAW = re.compile(
    r"(?i)(b[ãa]i\s*b[ỏo]|b[ỏo]\s*m[ụu]c|kh[oô]ng\s+c[òo]n\s+trong)\s+"
    r"(theo|b[ờı])\s*(ngh[ịı]\s*[đd][ịı]nh|th[ôo]ng\s*t[ưu]|v[ăa]n\s*b[ảa]n)"
    r"|(ngh[ịı]\s*[đd][ịı]nh|th[ôo]ng\s*t[ưu])\s*[sốs]?\.?\s*\d+(/[“\"]?\d+)?"
    r"\s*[^.]{0,60}(đ[ãa]\s*)?b[ỏo]\s*(m[ụu]c|bi[ểe]u\s*m[ẫu])")
_RE_CHK_TOKEN = re.compile(r"\bchk_[a-z0-9_]+\b")


# ============================================================ pure helpers

def norm_text(s: str) -> str:
    """Chuẩn hoá text so khớp: bỏ dấu, lower, non-alnum -> 1 space."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_js(src: str) -> str:
    """Bỏ /*..*/ comment, // comment và làm trơ string literal khỏi JS.

    Nội dung string được GIỮ (cần key quoted như ``'PLI_M72'``) nhưng các ký
    tự ``{}[];,`` bên trong string/comment được thay bằng space để không lệch
    bộ đếm depth khi scan object.
    """
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif c == "/" and nxt == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c in "\"'":
            j = i + 1
            buf = []
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c:
                    break
                buf.append(src[j] if src[j] not in "{}[],;" else " ")
                j += 1
            out.append('"' + "".join(buf) + '"')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def find_js_block(text: str, header_re: str) -> str | None:
    """Tìm ``var NAME = { ... };`` (balanced braces) trả body gồm cả 2 ngoặc."""
    m = re.search(header_re, text)
    if not m:
        return None
    start = text.find("{", m.end() - 1)
    if start < 0:
        return None
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    return None


_ENTRY_RE = re.compile(
    r"\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_$][\w$]*))\s*:")


def iter_js_entries(body: str):
    """Yield (key, value_text) các entry TẦNG ĐẦU TIÊN của object literal.

    ``body`` là text có ngoặc mở/đóng ngoài cùng (như trả về của
    :func:`find_js_block`). Giá trị là substring cân bằng ngoặc.
    """
    n = len(body)
    i = 1  # bỏ '{' mở
    while i < n - 1:
        m = _ENTRY_RE.match(body[i:])
        if not m:
            # không phải entry (dấu phẩy / whitespace) -> nhích 1 ký tự
            i += 1
            continue
        key = m.group(1) or m.group(2) or m.group(3)
        j = i + m.end()
        while j < n and body[j] in " \t\r\n":
            j += 1
        if j >= n:
            break
        ch = body[j]
        if ch in "{[":
            close_ch = "}" if ch == "{" else "]"
            depth = 0
            k = j
            while k < n:
                if body[k] == ch:
                    depth += 1
                elif body[k] == close_ch:
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            yield key, body[j:k + 1]
            i = k + 1
        else:
            # giá trị nguyên thuỷ (true/number/...) -> tới dấu ',' tầng 0
            k = j
            while k < n and body[k] not in ",}":
                k += 1
            yield key, body[j:k]
            i = k + 1


def extract_js_tags(value_text: str) -> list[str]:
    """Lấy các ``tag: 'xxx'`` trong 1 entry metadata runtime.

    strip_js chuẩn hoá mọi string delimiter sang nháy kép nên regex phải
    chấp nhận cả hai loại. Lookbehind ``(?<![\\w])`` tránh bắt nhầm
    ``target_tag:`` / ``semanticKey``...
    """
    return re.findall(r"(?<![\w])tag\s*:\s*['\"]([^'\"]+)['\"]", value_text)


def derive_final_status(kind, manifest_status, override_status, stages,
                        required_cols, evidenced_tags, legal_blocker,
                        override_blocked, removed_by_law):
    """Hàm THUẦN suy final_status từ evidence. KHÔNG đọc file.

    Tham số
    -------
    kind              : manifest section kind (vd 'editable-grid', 'output-table').
    manifest_status   : status cũ trong manifest census (có thể stale).
    override_status   : status trong LEAD_STATUS_OVERRIDES hoặc None.
    stages            : dict các stage bool: spec/template/form_maps/blocks/
                        runtime/draft/validation.
    required_cols     : list required_columns của manifest (có thể rỗng).
    evidenced_tags    : list tag vật lý có bằng chứng ở tầng dữ liệu/runtime,
                        HOẶC None khi KHÔNG tầng nào cho biết số cột đo được
                        (không đủ căn cứ kết luận thiếu cột).
    legal_blocker     : True khi notes manifest ghi blocker pháp lý tường minh.
    override_blocked  : True khi override ghi status blocked.
    removed_by_law    : True khi source_evidence/notes manifest ghi RÕ văn bản
                        hiện hành đã bỏ mục này (không suy diễn).

    Quy tắc (thứ tự ưu tiên) — bảo thủ, KHÔNG nâng missing -> implemented
    khi thiếu bất kỳ stage nào:

    1. ``OUTPUT_ONLY``  : kind output-table hoặc manifest output_only.
    2. ``REMOVED_BY_CURRENT_LAW`` : chỉ khi có bằng chứng tường minh.
    3. ``NO_TABLE``     : manifest no_table VÀ không tầng cấu trúc nào có
       bằng chứng bảng (spec/form_maps/blocks-loop/runtime; nhóm chk không
       phải bảng).
    4. Không bằng chứng implementation ở TẦNG NÀO (kể cả nhóm chk đã map
       trong blocks):
       ``BLOCKED_OWNER`` nếu legal_blocker/override_blocked, ngược lại
       ``MISSING_IMPLEMENTATION``. Có bằng chứng vật lý (chk) thì KHÔNG
       được coi là "không implementation" -> không BLOCKED.
    5. Có bằng chứng bảng:
       5a. ``PARTIAL_COLUMNS`` nếu evidenced_tags đủ tin cậy (khác None) và
           thiếu tag so với required_columns (hoặc groups chk thiếu token).
       5b. ``IMPLEMENTED_VERIFIED`` nếu ĐỦ 7 stage.
       5c. còn lại ``MISSING_IMPLEMENTATION`` (liệt kê stage thiếu).

    Xung đột evidence (vd manifest already_complete nhưng thiếu stage) được
    xử lý bảo thủ tại đây; drift 2 chiều do gate riêng báo.

    Trả về ``(final_status, missing_stages, detail)``.
    """
    missing = [k for k in STAGE_KEYS if not stages.get(k)]
    detail = []

    if kind == "output-table" or manifest_status == "output_only":
        return FINAL_OUTPUT_ONLY, [], ["render-only theo kind/manifest"]

    if removed_by_law:
        return FINAL_REMOVED, [], ["manifest ghi rõ văn bản hiện hành đã bỏ"]

    # bằng chứng bảng ở tầng cấu trúc (blocks chỉ-chk không tính là bảng)
    table_evidence = bool(
        stages.get("spec") or stages.get("form_maps") or stages.get("runtime")
        or stages.get("blocks_loop"))
    # bằng chứng implementation ở MỌI tầng (chk đã map trong blocks cũng tính:
    # có vật lý rồi thì không được kết luận "không implementation")
    impl_evidence = bool(table_evidence or stages.get("blocks_chk"))

    if manifest_status == "no_table" and not table_evidence:
        return FINAL_NO_TABLE, [], ["manifest no_table, không tầng nào thấy bảng"]

    if not impl_evidence:
        if override_blocked or legal_blocker:
            return FINAL_BLOCKED, [], ["không implementation + blocker tường minh"]
        return FINAL_MISSING, missing, ["không có bằng chứng bảng ở tầng nào"]

    # có bảng: kiểm tra cột
    if evidenced_tags is not None and required_cols:
        have = set(evidenced_tags)
        miss_cols = [c for c in required_cols if c not in have]
        if miss_cols:
            return (FINAL_PARTIAL, missing,
                    ["thiếu cột/token: %s" % ", ".join(miss_cols)])
        detail.append("đủ %d/%d cột có bằng chứng" % (len(required_cols),
                                                      len(required_cols)))

    if not missing:
        return FINAL_IMPLEMENTED, [], detail or ["đủ evidence xuyên pipeline"]
    return (FINAL_MISSING, missing,
            ["thiếu stage: " + ", ".join(missing)])


_RE_BRIDGE_TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")


def bridge_loop_names(override, inventory, base_names):
    """(THUẦN) Tên loop/section implementation nêu TƯỜNG MINH trong
    ``override['evidence']`` và CÓ THẬT trong ``inventory`` của cùng form.

    Nhiều section đặt semantic_key cấp section (vd 'nganh_bo') trong khi
    implementation dùng tên loop riêng (vd 'nganh_xoa_bo') — ánh xạ này do
    owner GHI RÕ trong evidence của override ("loop rieng nganh_xoa_bo"),
    không phải suy diễn của tool. Chỉ token nằm trong inventory (loop thật
    của form_maps/blocks/runtime cùng form) mới được nhận.

    Trả list tên bridge (đã loại trừ ``base_names`` = section_id +
    semantic_key khớp trực tiếp). Không override -> rỗng.
    """
    if not override:
        return []
    text = (override.get("evidence") or "").lower()
    tokens = set(_RE_BRIDGE_TOKEN.findall(text))
    return sorted((tokens & set(inventory)) - set(base_names))


def legal_blocker_flags(section_notes, form_legal_questions):
    """(THUẦN) Blocker pháp lý tường minh CHỈ từ dữ liệu manifest.

    * wording blocker trong ``notes`` của section (vd 'blocker', 'chờ
      owner/legal', 'pending legal');
    * HOẶC form của section có mảng ``legal_questions`` khác rỗng (manifest
      census đánh chính các form này BLOCKED_LEGAL_REVIEW).

    KHÔNG tự suy diễn nội dung pháp lý. Trả ``(blocked: bool, source: str|None,
    n_questions: int)``.
    """
    notes_hit = bool(_RE_BLOCKER.search(section_notes or ""))
    n_q = len(form_legal_questions or [])
    lq_hit = n_q > 0
    src = []
    if notes_hit:
        src.append("notes")
    if lq_hit:
        src.append("form.legal_questions(n=%d)" % n_q)
    return (notes_hit or lq_hit), (" + ".join(src) if src else None), n_q


def resolve_override_keys(overrides, manifest_index):
    """Gate override: mỗi key (form_id, section_id) phải resolve được section.

    Trả về list drift (rỗng khi mọi key hợp lệ). Hàm thuần nhận
    ``manifest_index`` = set of (form_id, section_id).
    """
    drift = []
    for (fid, sid) in sorted(overrides):
        if (fid, sid) not in manifest_index:
            drift.append({
                "gate": "override_resolve",
                "form_id": fid,
                "section_id": sid,
                "detail": "override key (%s, %s) KHÔNG resolve được section "
                          "trong manifest" % (fid, sid),
            })
    return drift


def check_section_count(n_sections):
    """Gate tổng số section phải đúng %d.""" % EXPECTED_SECTIONS
    drift = []
    if n_sections != EXPECTED_SECTIONS:
        drift.append({
            "gate": "section_count",
            "form_id": "*",
            "section_id": "*",
            "detail": "tổng section tổng hợp = %d != %d"
                      % (n_sections, EXPECTED_SECTIONS),
        })
    return drift


# ============================================================ loaders (I/O)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_overrides(py_path=BUILD_MANIFEST_PY):
    """Trích LEAD_STATUS_OVERRIDES khỏi build_manifest.py bằng literal_eval."""
    with open(py_path, "r", encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"LEAD_STATUS_OVERRIDES\s*=\s*\{", src)
    if not m:
        return {}
    start = src.index("{", m.start())
    depth = 0
    end = start
    for j in range(start, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    literal = " " * start + src[start:end]  # giữ offset, an toàn literal_eval
    data = ast.literal_eval(literal)
    return {tuple(k): v for k, v in data.items()}


def parse_runtime_index():
    """Scan form-domain.js: GRID_META / FORM_GRID_META / FORM_TABLE_CONTRACTS.

    Trả dict:
      grid_meta        : {loop: [tags]}
      form_grid_meta   : {form: {loop: [tags]}}
      form_contracts   : {form: [sectionId]}
      domain_text      : stripped lowercase text (presence check validation)
      app_text         : stripped lowercase text gộp app_web/ui/*.js TRỪ
                         form-domain.js (presence check draft)
    """
    with open(FORM_DOMAIN_JS, "r", encoding="utf-8") as f:
        domain = strip_js(f.read())

    grid_meta = {}
    body = find_js_block(domain, r"\bvar\s+GRID_META\s*=")
    if body:
        for key, val in iter_js_entries(body):
            grid_meta[key] = extract_js_tags(val)

    form_grid_meta = {}
    body = find_js_block(domain, r"\bvar\s+FORM_GRID_META\s*=")
    if body:
        for form, fval in iter_js_entries(body):
            loops = {}
            m = re.search(r"\bloops\s*:\s*\{", fval)
            if m:
                sub = find_block_from(fval, m.end() - 1)
                if sub:
                    for lk, lv in iter_js_entries(sub):
                        tags = extract_js_tags(lv)
                        if not tags:
                            # entry mkGrid(GRID_META.<base>, {...}) -> kế thừa
                            # tag của meta gốc khi không khai columns inline.
                            mb = re.search(
                                r"mkGrid\s*\(\s*GRID_META\.([A-Za-z0-9_]+)",
                                lv)
                            if mb and mb.group(1) in grid_meta:
                                tags = list(grid_meta[mb.group(1)])
                        # lọc entry phi-loop (label/minRows/semanticKey...)
                        if tags or "mkGrid" in lv or "tag:" in lv:
                            loops[lk] = tags
            # form entry cũng có thể khai loop trực tiếp (không qua wrapper)
            for k, v in iter_js_entries(fval):
                if k != "loops" and (v.lstrip().startswith("{")):
                    if ("mkGrid" in v or "tag:" in v or
                            extract_js_tags(v)):
                        loops.setdefault(k, extract_js_tags(v))
            form_grid_meta[form] = loops

    form_contracts = {}
    body = find_js_block(domain, r"\bvar\s+FORM_TABLE_CONTRACTS\s*=")
    if body:
        for form, fval in iter_js_entries(body):
            secs = {}
            # value text của 1 section = từ sectionId tới section kế tiếp
            # (gồm anchor + spec.columns -> đủ để bóc tag runtime)
            marks = list(re.finditer(
                r"sectionId\s*:\s*['\"]([^'\"]+)['\"]", fval))
            for i, m in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(fval)
                secs[m.group(1)] = fval[m.start():end]
            form_contracts[form] = secs

    app_parts = []
    if os.path.isdir(APP_JS):
        for name in sorted(os.listdir(APP_JS)):
            if not name.endswith(".js") or name == "form-domain.js":
                continue
            with open(os.path.join(APP_JS, name), "r", encoding="utf-8") as f:
                app_parts.append(strip_js(f.read()))

    return {
        "grid_meta": grid_meta,
        "form_grid_meta": form_grid_meta,
        "form_contracts": form_contracts,
        "domain_text": domain.lower(),
        "app_text": "\n".join(app_parts).lower(),
        # corpus app_web/ui nói chung (form-domain + mọi module UI) —
        # presence của section/loop key cho draft/validation theo đề
        "corpus_text": (domain + "\n" + "\n".join(app_parts)).lower(),
    }


def find_block_from(text: str, start: int) -> str | None:
    """Đọc 1 block cân bằng ngoặc bắt đầu tại ``start`` (ký tự '{')."""
    depth = 0
    n = len(text)
    for j in range(start, n):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    return None


def count_template_tables(form_id):
    """Đếm w:tbl bằng python-docx; trả (n_tables, error)."""
    path = os.path.join(TEMPLATES_DIR, "%s.docx" % form_id)
    if not os.path.exists(path):
        return None, "missing %s" % os.path.relpath(path, REPO)
    try:
        import docx  # python-docx
        d = docx.Document(path)
        return len(d.tables), None
    except Exception as exc:  # pragma: no cover - defensive
        return None, "python-docx error: %s" % exc


def blocks_text_all(blocks_doc):
    """Gộp toàn bộ text runs của blocks doc (để so anchor heading)."""
    parts = []

    def walk(x):
        if isinstance(x, dict):
            if x.get("t") == "p" or "runs" in x:
                for r in x.get("runs") or []:
                    t = r.get("text")
                    if t:
                        parts.append(t)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(blocks_doc)
    return norm_text(" ".join(parts))


def iter_block_items(blocks_doc):
    """Duyệt mọi block dict trong blocks doc (đệ quy qua region/children)."""
    stack = [blocks_doc]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("t") in ("loop", "table", "chk", "p"):
                yield cur
            for key in ("blocks", "children", "items", "region"):
                if isinstance(cur.get(key), list):
                    stack.extend(cur[key])
        elif isinstance(cur, list):
            stack.extend(cur)


def load_spec_docs(form_id):
    """Load mọi spec file của 1 form (theo nhóm) -> list (path, doc)."""
    out = []
    for grp in SPECS_DIRS:
        p = os.path.join(SPECS_ROOT, grp, "%s.json" % form_id)
        if os.path.exists(p):
            try:
                out.append((p, load_json(p)))
            except Exception as exc:  # pragma: no cover
                sys.stderr.write("WARN spec %s: %s\n" % (p, exc))
    return out


# ============================================================ matching

def _cols_stats(cols, start_index_key="col"):
    """(n_total, n_tagged, leading_untagged) từ list cột của 1 layer.

    ``leading_untagged`` = số cột đầu không tag (STT / cột label readonly)
    khi danh sách cột bắt đầu ở index > 0.
    """
    if not cols:
        return 0, 0, 0
    n_tagged = sum(1 for c in cols if c.get("tag"))
    idx = [c.get(start_index_key) for c in cols if isinstance(
        c.get(start_index_key), int)]
    leading = min(idx) if idx else 0
    leading = leading if leading > 0 else 0
    return len(cols), n_tagged, leading


def match_form_maps(fm_form, candidates):
    """Tìm dynamic_tables / section_specs của form khớp candidates.

    Trả (evidence_str | None, hits) với hits = list dict
    (kind, loop/id, tags, table_index, n_cols_total).
    """
    if not fm_form:
        return None, []
    hits = []
    for i, dt in enumerate(fm_form.get("dynamic_tables") or []):
        ids = {dt.get("id"), dt.get("loop")}
        if ids & candidates:
            tags = [c.get("tag") for c in (dt.get("columns") or [])
                    if c.get("tag")]
            n_total, _, leading = _cols_stats(dt.get("columns") or [])
            hits.append({"source": "dynamic_tables[%d]" % i,
                         "id": dt.get("id"), "loop": dt.get("loop"),
                         "tags": tags,
                         "table_index": dt.get("table_index"),
                         "n_cols_total": n_total + leading})
    for i, ss in enumerate(fm_form.get("section_specs") or []):
        ids = {ss.get("id"), ss.get("section_id"), ss.get("semantic_key")}
        if ids & candidates:
            tags = [c.get("tag") for c in (ss.get("columns") or [])
                    if c.get("tag")]
            n_total, _, leading = _cols_stats(ss.get("columns") or [])
            hits.append({"source": "section_specs[%d]" % i, "id": ss.get("id"),
                         "loop": ss.get("loop") or ss.get("id"),
                         "tags": tags,
                         "table_index": ss.get("table_index"),
                         "n_cols_total": n_total + leading})
    if not hits:
        return None, []
    ev = "; ".join(
        "form_maps.%s id=%s loop=%s cols=%d" %
        (h["source"], h["id"], h["loop"], len(h["tags"])) for h in hits)
    return "form_maps: " + ev, hits


def match_spec(spec_docs, candidates):
    """Tìm tables[] trong spec files khớp candidates."""
    hits = []
    for path, doc in spec_docs:
        for i, t in enumerate(doc.get("tables") or []):
            sp = t.get("spec") or {}
            occ_ids = {o.get("occurrence_id")
                       for o in (t.get("occurrences") or [])}
            ids = {sp.get("id"), sp.get("semantic_key"), sp.get("section_id"),
                   sp.get("loop")} | occ_ids
            if ids & candidates:
                if sp.get("cols"):
                    tags = [c[1] for c in sp["cols"] if len(c) > 1 and c[1]]
                    n_untagged = sum(1 for c in sp["cols"]
                                     if len(c) > 1 and not c[1])
                else:
                    tags = [c.get("tag") for c in (sp.get("columns") or [])
                            if c.get("tag")]
                    n_untagged = sum(1 for c in (sp.get("columns") or [])
                                     if not c.get("tag"))
                if not tags:
                    tags = list(sp.get("fields") or [])
                    n_untagged = 0
                hits.append({
                    "path": os.path.relpath(path, REPO),
                    "index": i,
                    "id": sp.get("id"),
                    "kind": sp.get("kind") or "editable-grid(legacy)",
                    "loop": sp.get("loop"),
                    "tags": tags,
                    "n_cols_total": len(tags) + n_untagged,
                })
    if not hits:
        return None, []
    ev = "; ".join(
        "%s#tables[%d] spec.id=%s kind=%s loop=%s cols=%d"
        % (h["path"], h["index"], h["id"], h["kind"], h["loop"],
           len(h["tags"])) for h in hits)
    return "spec: " + ev, hits


def block_norm_text(b):
    """Text đã norm của 1 block (chỉ tầng đỉnh, đủ so anchor heading)."""
    parts = []
    for r in b.get("runs") or []:
        if r.get("text"):
            parts.append(r["text"])
    return norm_text(" ".join(parts))


def match_blocks(blocks_doc, candidates, section, blocks_norm_text):
    """Evidence blocks: loop block / chk tokens / anchor heading.

    Trả dict {loop_ev, loop_hits, chk_ev, chk_ok, anchor_ev}.
    ``chk_ok``: True (đủ token) / False (thiếu) / None (notes không nêu token).
    """
    loop_hits = []
    chk_keys = set()
    n_tables = 0
    for b in iter_block_items(blocks_doc):
        t = b.get("t")
        if t == "loop":
            name = b.get("loop") or b.get("name")
            if name and name in candidates:
                cols = b.get("cols") or []
                n_total, _, leading = _cols_stats(cols)
                loop_hits.append({
                    "loop": name,
                    "cols": len(cols),
                    "tags": [c.get("tag") for c in cols if c.get("tag")],
                    "n_cols_total": n_total + leading,
                })
        elif t == "table":
            n_tables += 1
        elif t == "chk":
            if b.get("key"):
                chk_keys.add(b["key"])

    loop_ev = None
    if loop_hits:
        loop_ev = "blocks: " + "; ".join(
            "loop@%s cols=%d" % (h["loop"], h["cols"]) for h in loop_hits)

    # chk tokens nêu TƯỜNG MINH trong notes -> đối chiếu presence thật.
    # Token trong notes thường là TIỀN TỐ (vd 'chk_khu_' cho các key
    # 'chk_khu_cong_nghiep', ...) -> khớp cả prefix, không chỉ exact.
    notes_txt = " ".join(filter(None, [section.get("notes"),
                                       json.dumps(
                                           section.get("source_evidence") or {},
                                           ensure_ascii=False)]))
    mentioned = sorted(set(_RE_CHK_TOKEN.findall(notes_txt)))
    chk_ev = None
    chk_ok = None
    chk_missing = []
    if mentioned:
        found = []
        for tok in mentioned:
            hits_tok = sorted(k for k in chk_keys
                              if k == tok or k.startswith(tok))
            if hits_tok:
                found.append("%s->%d" % (tok, len(hits_tok)))
            else:
                chk_missing.append(tok)
        chk_ok = not chk_missing
        chk_ev = ("blocks: chk %d/%d token khớp key thật (%s)"
                  % (len(mentioned) - len(chk_missing), len(mentioned),
                     ",".join(found))) + (
            " THIẾU: " + ",".join(chk_missing) if chk_missing else "")

    anchor_ev = None
    anon_table_ev = None
    heading = (section.get("source_evidence") or {}).get("heading")
    if heading:
        base = norm_text(heading)
        anchor_ev = None
        for cut in (40, 32, 24, 16):
            needle = base[:cut]
            if len(needle) < 12:
                break
            if needle in blocks_norm_text:
                anchor_ev = ("blocks: anchor heading khớp (needle %d ký: "
                             "%r...)" % (len(needle), needle))
                break
        if anchor_ev is None:
            anchor_ev = ("blocks: KHÔNG tìm thấy anchor heading %r"
                         % base[:32])

        # Bảng fixed/output trong blocks L0 là block 'table' VÔ DANH (không
        # loop name, không tag) — "cấu trúc hiện có" theo census. Gắn về
        # section bằng VỊ TRÍ: block table/loop đầu tiên sau anchor heading.
        top = (blocks_doc or {}).get("blocks")
        if anchor_ev and "khớp" in anchor_ev and isinstance(top, list):
            needle24 = base[:24]
            if len(needle24) >= 12:
                for i, b in enumerate(top):
                    nt = block_norm_text(b)
                    if nt and needle24 in nt:
                        for j in range(i + 1, min(i + 9, len(top))):
                            if top[j].get("t") in ("table", "loop"):
                                anon_table_ev = (
                                    "blocks: block %s vô danh (L0 chưa tag) "
                                    "tại +%d block sau anchor heading"
                                    % (top[j].get("t"), j - i))
                                break
                        break

    return {"loop_ev": loop_ev, "loop_hits": loop_hits, "chk_ev": chk_ev,
            "chk_ok": chk_ok, "chk_missing": chk_missing,
            "anchor_ev": anchor_ev, "anon_table_ev": anon_table_ev,
            "n_chk": len(chk_keys),
            "n_table_blocks": n_tables}


def match_runtime(rt, form_id, candidates):
    """Evidence runtime trong form-domain.js (structured index)."""
    hits = []
    gm = rt["grid_meta"]
    fgm = rt["form_grid_meta"].get(form_id) or {}
    ftc = rt["form_contracts"].get(form_id) or {}
    for cand in sorted(candidates):
        if cand in gm:
            hits.append("GRID_META.%s cols=%d" % (cand, len(gm[cand])))
            hits.append(("__tags__", gm[cand]))
        if cand in fgm:
            tags = fgm[cand]
            hits.append("FORM_GRID_META.%s.%s cols=%d"
                        % (form_id, cand, len(tags)))
            hits.append(("__tags__", tags))
    for sid, sval in ftc.items():
        if sid in candidates:
            tags = extract_js_tags(sval)
            hits.append("FORM_TABLE_CONTRACTS.%s.%s tags=%d"
                        % (form_id, sid, len(tags)))
            hits.append(("__tags__", tags))
    evs = [h for h in hits if isinstance(h, str)]
    tags = []
    for h in hits:
        if isinstance(h, tuple):
            tags.extend(h[1])
    if not evs:
        return None, []
    return "runtime: " + "; ".join(evs), tags


# ============================================================ audit core

def audit_section(form, section, ctx):
    """Dựng 1 hàng coverage cho 1 section (đọc ctx đã cache)."""
    fid = form["form_id"]
    sid = section["section_id"]
    kind = section.get("kind")
    manifest_status = section.get("status")
    semantic = section.get("semantic_key")
    override = ctx["overrides"].get((fid, sid))
    embedded_ov = section.get("lead_status_override")

    candidates = {sid, semantic} - {None, ""}
    spec_docs = ctx["spec_docs"].get(fid) or []
    fm_form = (ctx["form_maps"] or {}).get(fid)

    # bridge: tên loop implementation do owner ghi trong override evidence
    bridged = bridge_loop_names(
        override, (ctx["runtime_inventory"] or {}).get(fid) or set(),
        candidates)
    candidates |= set(bridged)

    # --- spec
    spec_ev, spec_hits = match_spec(spec_docs, candidates)
    for h in spec_hits:
        if h.get("loop"):
            candidates.add(h["loop"])

    # --- form_maps (cần candidates đã có loop từ spec)
    maps_ev, maps_hits = match_form_maps(fm_form, candidates)
    for h in maps_hits:
        if h.get("loop"):
            candidates.add(h["loop"])

    # --- blocks
    blocks_doc = (ctx["blocks"] or {}).get(fid)
    blocks_norm = ctx["blocks_norm"].get(fid, "")
    bm = match_blocks(blocks_doc, candidates, section, blocks_norm)

    # --- runtime
    runtime_ev, runtime_tags = match_runtime(ctx["runtime"], fid, candidates)

    # --- draft / validation presence (text scan theo đề: presence của
    #     section/loop key trong app_web/ui nói chung — form-domain.js và
    #     các module UI; draft và validation dùng cùng corpus, ghi riêng 2
    #     cột vì là 2 stage nghiệm thu khác nhau)
    draft_hits = [c for c in sorted(candidates)
                  if c and re.search(r"\b%s\b" % re.escape(c),
                                     ctx["runtime"]["corpus_text"])]
    draft_ev = ("draft: key %s xuất hiện trong app_web/ui (corpus JS)"
                % ", ".join(draft_hits)) if draft_hits else None
    valid_hits = [c for c in sorted(candidates)
                  if c and re.search(r"\b%s\b" % re.escape(c),
                                     ctx["runtime"]["corpus_text"])]
    valid_ev = ("validation: key %s xuất hiện trong app_web/ui (corpus JS)"
                % ", ".join(valid_hits)) if valid_hits else None

    # --- template + docx_render structural
    n_tbl, tbl_err = ctx["template_tables"].get(
        fid, (None, "not scanned"))
    if n_tbl is not None:
        template_ev = "template: %s.docx w:tbl=%d" % (fid, n_tbl)
    else:
        template_ev = "template: — (%s)" % tbl_err
    template_ok = n_tbl is not None

    idx_ok = True
    idx_notes = []
    for h in maps_hits:
        ti = h.get("table_index")
        if isinstance(ti, int):
            if n_tbl is not None and ti < n_tbl:
                idx_notes.append("table_index=%d in range" % ti)
            else:
                idx_ok = False
                idx_notes.append("table_index=%d NGOÀI range (w:tbl=%s)"
                                 % (ti, n_tbl))
    docx_parts = ["structural-only: template %s w:tbl=%s" % (fid, n_tbl)]
    docx_parts += idx_notes
    anchor_ok = None
    if bm["anchor_ev"]:
        anchor_ok = "khớp" in bm["anchor_ev"]
        docx_parts.append("anchor ok" if anchor_ok else "anchor MISSING")
    docx_parts.append("KHÔNG phải visual; visual NOT RUN")
    docx_ev = "docx_render: " + "; ".join(docx_parts)
    # structural export chain: template tồn tại + table_index trong range +
    # (nếu section có heading anchor) anchor phải thấy trong blocks
    docx_structural_ok = bool(template_ok and idx_ok and anchor_ok is not False)

    # --- legal / removed flags (chỉ dùng marker tường minh trong manifest)
    notes_all = " ".join(filter(None, [
        section.get("notes") or "",
        json.dumps(section.get("source_evidence") or {}, ensure_ascii=False),
        json.dumps(form.get("legal_questions") or [], ensure_ascii=False),
    ]))
    legal_blocker, lb_source, n_lq = legal_blocker_flags(
        section.get("notes"), form.get("legal_questions"))
    removed_by_law = bool(_RE_REMOVED_LAW.search(notes_all))

    # --- evidenced tags + số cột vật lý cho PARTIAL_COLUMNS
    tag_lists = []
    for h in spec_hits:
        if h["tags"]:
            tag_lists.append(h["tags"])
    for h in maps_hits:
        if h["tags"]:
            tag_lists.append(h["tags"])
    for h in bm["loop_hits"]:
        if h["tags"]:
            tag_lists.append(h["tags"])
    if runtime_tags:
        tag_lists.append(runtime_tags)
    required_cols = list(section.get("required_columns") or [])

    # số cột vật lý: ưu tiên tầng gần template nhất (blocks loop ->
    # form_maps -> spec) vì tầng khai báo có thể "plan" cột chưa dựng.
    col_count = None
    for layer_hits in (bm["loop_hits"], maps_hits, spec_hits):
        if col_count is None and layer_hits:
            vals = [h.get("n_cols_total") or 0 for h in layer_hits]
            col_count = max(vals) if vals else None
            if col_count == 0:
                col_count = None

    evidenced_tags = None
    missing_cols = None
    name_variant_notes = []
    if tag_lists or col_count:
        flat = set()
        for lst in tag_lists:
            flat.update(lst)

        def tag_matches(col, tag):
            if tag == col or tag.endswith("_" + col) or col in tag:
                return True
            # chk_... key: bỏ prefix chk_ khi so
            return tag.startswith("chk_") and tag[4:] == col

        matched = {c for c in required_cols
                   if any(tag_matches(c, t) for t in flat)}
        if required_cols and col_count is not None and len(matched) < len(
                required_cols) and col_count >= len(required_cols):
            # đủ số cột vật lý nhưng tên lệch chuẩn giữa required_columns
            # (tên semantic) và tag từng tầng -> ghi nhận, không kết luận thiếu
            unmatched = [c for c in required_cols if c not in matched]
            name_variant_notes.append(
                "tên cột lệch chuẩn (required %s không khớp đen tag nào) "
                "nhưng số cột vật lý %d >= %d required"
                % (", ".join(unmatched), col_count, len(required_cols)))
            evidenced_tags = list(required_cols)
        else:
            evidenced_tags = sorted(matched)
            missing_cols = [c for c in required_cols if c not in matched]
    elif bm["chk_ok"] is True:
        evidenced_tags = list(required_cols)  # nhóm chk đủ token theo notes
        missing_cols = []
    elif bm["chk_ok"] is False:
        evidenced_tags = [c for c in required_cols
                          if c not in bm["chk_missing"]]
        missing_cols = list(bm["chk_missing"])

    # --- override label (an toàn khi thiếu evidence)
    if override:
        override_label = "%s (%s)" % (
            override.get("status", "?"),
            (override.get("evidence") or "")[:80])
    else:
        override_label = None

    stages = {
        "spec": bool(spec_ev),
        "template": template_ok,
        "form_maps": bool(maps_ev),
        "blocks": bool(bm["loop_ev"] or bm["chk_ev"] or bm["anon_table_ev"]),
        "blocks_loop": bool(bm["loop_ev"]),
        "blocks_chk": bm["chk_ok"] is True,
        "runtime": bool(runtime_ev),
        "draft": bool(draft_ev),
        "validation": bool(valid_ev),
    }
    final_status, missing_stages, detail = derive_final_status(
        kind=kind,
        manifest_status=manifest_status,
        override_status=(override or {}).get("status") if override else None,
        stages=stages,
        required_cols=required_cols,
        evidenced_tags=evidenced_tags,
        legal_blocker=legal_blocker,
        override_blocked=bool(override and override.get("status") == "blocked"),
        removed_by_law=removed_by_law,
    )

    conflicts = []
    if bridged:
        conflicts.append(
            "bridge: override evidence nêu tên implementation (%s) khác "
            "section_id/semantic_key — khớp qua evidence owner, không suy "
            "diễn" % ", ".join(bridged))
    if (manifest_status == "missing_grid" and final_status in
            (FINAL_IMPLEMENTED,)):
        conflicts.append("manifest missing_grid nhưng đủ evidence pipeline")
    if manifest_status in MANIFEST_IMPLEMENTED_STATUSES and (
            final_status in (FINAL_MISSING, FINAL_PARTIAL)):
        conflicts.append("manifest %s nhưng evidence bảo thủ cho %s (%s)"
                         % (manifest_status, final_status,
                            "; ".join(detail)))
    if embedded_ov and override and embedded_ov.get("status") and \
            embedded_ov.get("status") != override.get("status"):
        conflicts.append("embedded lead_status_override (%s) khác "
                         "build_manifest override (%s)"
                         % (embedded_ov.get("status"), override.get("status")))
    if embedded_ov and not embedded_ov.get("status") and override:
        conflicts.append("embedded lead_status_override chỉ có evidence "
                         "(không status) — tham chiếu build_manifest override "
                         "(%s)" % override.get("status"))
    if (embedded_ov and not override):
        conflicts.append("section có embedded lead_status_override nhưng "
                         "KHÔNG có key trong LEAD_STATUS_OVERRIDES")
    if missing_cols:
        conflicts.append("missing cols: %s" % ", ".join(missing_cols))
    if name_variant_notes:
        conflicts += name_variant_notes
    if kind == "source-contamination":
        conflicts.append("manifest đánh dấu source-contamination — cần sửa "
                         "nguồn trước khi implement (theo census, không "
                         "suy diễn thêm)")
    if bm["chk_ok"] is True and manifest_status in ("partial",
                                                    "partial_columns"):
        conflicts.append("chk token nêu trong notes thực tế CÓ MẶT trong "
                         "blocks — census partial có thể stale (cần "
                         "xác minh lại, tool không tự nâng)")

    def dash(x):
        return x if x else "—"

    row = OrderedDict([
        ("form_id", fid),
        ("section_id", sid),
        ("kind", kind),
        ("manifest_status", manifest_status),
        ("override", dash(override_label)),
        ("spec", dash(spec_ev)),
        ("template", dash(template_ev)),
        ("form_maps", dash(maps_ev)),
        ("blocks", "; ".join(filter(None, [bm["loop_ev"], bm["chk_ev"],
                                           bm["anon_table_ev"],
                                           bm["anchor_ev"]])) or "—"),
        ("runtime", dash(runtime_ev)),
        ("draft", dash(draft_ev)),
        ("validation", dash(valid_ev)),
        ("docx_render", docx_ev),
        ("visual", "NOT RUN (không có browser ở môi trường này)"),
        ("final_status", final_status),
        ("detail", "; ".join(detail)),
        ("missing_stages", missing_stages),
        ("missing_cols", missing_cols or []),
        ("bridged_names", bridged),
        ("conflicts", conflicts),
        ("flags", {
            "template_ok": template_ok,
            "docx_structural_ok": docx_structural_ok,
            "blocks_loop": stages["blocks_loop"],
            "blocks_chk_ok": bm["chk_ok"],
            "legal_blocker": legal_blocker,
            "legal_blocker_source": lb_source,
            "n_legal_questions_form": n_lq,
            "removed_by_law": removed_by_law,
        }),
    ])
    # bản full cho JSON (evidence không cắt gọn)
    row_full = dict(row)
    row_full["override_full"] = override
    row_full["semantic_key"] = semantic
    return row, row_full


def collect_drifts(rows, overrides, manifest_index, n_sections):
    """Gate 2 chiều manifest <-> evidence. Trả list drift dicts."""
    drifts = []
    drifts += resolve_override_keys(overrides, manifest_index)
    drifts += check_section_count(n_sections)
    for r in rows:
        fid, sid = r["form_id"], r["section_id"]
        # gate 1: implementation có ở tầng cấu trúc nhưng manifest missing_grid
        flags = r.get("flags") or {}
        structural = any([r["spec"] != "—", r["form_maps"] != "—",
                          flags.get("blocks_loop", False),
                          flags.get("blocks_chk_ok") is True,
                          r["runtime"] != "—"])
        if r["manifest_status"] == "missing_grid" and structural:
            drifts.append({
                "gate": "missing_grid_vs_evidence",
                "form_id": fid, "section_id": sid,
                "detail": "spec/form_maps/blocks-loop/runtime CÓ bằng chứng "
                          "nhưng manifest vẫn missing_grid",
            })
        # gate 2: manifest implemented nhưng thiếu evidence export/runtime
        if r["manifest_status"] in MANIFEST_IMPLEMENTED_STATUSES:
            missing = []
            if not flags.get("template_ok", False):
                missing.append("template")
            if r["blocks"] == "—":
                missing.append("blocks")
            if r["runtime"] == "—":
                missing.append("runtime")
            if not flags.get("docx_structural_ok", False):
                missing.append("docx_render(structural)")
            if missing:
                drifts.append({
                    "gate": "implemented_missing_evidence",
                    "form_id": fid, "section_id": sid,
                    "detail": "manifest %s nhưng thiếu evidence: %s"
                              % (r["manifest_status"], ", ".join(missing)),
                })
    return drifts


# ============================================================ outputs

def build_md(rows, totals, drifts, head_commit):
    lines = []
    ap = lines.append
    ap("# Table coverage hiện tại — 111 section / 87 form (Wave B)")
    ap("")
    ap("Sinh bởi `tools/census/table_coverage_audit.py` tại HEAD `%s`. "
       "Toàn bộ evidence là structural (đọc manifest/form_maps/blocks/specs/"
       "template w:tbl/JS contract). **Không có audit visual** — cột "
       "`visual` = NOT RUN (môi trường không có browser)." % head_commit)
    ap("")
    ap("## Totals theo `final_status`")
    ap("")
    ap("| final_status | số section |")
    ap("|---|---|")
    for st in FINAL_STATUSES:
        ap("| %s | %d |" % (st, totals.get(st, 0)))
    ap("| **Tổng** | **%d** |" % sum(totals.values()))
    ap("")
    ap("Định nghĩa: `IMPLEMENTED_VERIFIED` = đủ evidence spec + template + "
       "form_maps + blocks + runtime + draft + validation xuyên pipeline. "
       "`PARTIAL_COLUMNS` = có bảng/runtime nhưng cột vật lý thiếu so với "
       "`required_columns`. `MISSING_IMPLEMENTATION` = khai báo bảng nhưng "
       "thiếu ít nhất một stage (bảo thủ, không nâng khi thiếu evidence). "
       "`BLOCKED_OWNER` = KHÔNG có bằng chứng implementation + blocker tường "
       "minh trong manifest (notes ghi blocker hoặc form có `legal_questions` "
       "— đúng 33 form BLOCKED_LEGAL_REVIEW của census) hoặc override ghi "
       "blocked; tool KHÔNG tự suy diễn nội dung pháp lý. `NO_TABLE` = "
       "manifest no_table và không tầng nào có bằng chứng bảng. "
       "`OUTPUT_ONLY` = render-only. `REMOVED_BY_CURRENT_LAW` = CHỈ khi "
       "manifest ghi rõ văn bản hiện hành đã bỏ mục (không suy diễn).")
    ap("")
    ap("## Còn thiếu bao nhiêu bảng THẬT?")
    ap("")
    work = totals.get(FINAL_MISSING, 0) + totals.get(FINAL_PARTIAL, 0)
    ap("- Cần làm thật (thiếu implementation hoặc thiếu cột): **%d** section "
       "(`MISSING_IMPLEMENTATION` %d + `PARTIAL_COLUMNS` %d)."
       % (work, totals.get(FINAL_MISSING, 0), totals.get(FINAL_PARTIAL, 0)))
    ap("- Chờ owner/blocker pháp lý: %d. Không phải bảng (theo census): "
       "%d `NO_TABLE` + %d `OUTPUT_ONLY` + %d `REMOVED_BY_CURRENT_LAW`."
       % (totals.get(FINAL_BLOCKED, 0), totals.get(FINAL_NO_TABLE, 0),
          totals.get(FINAL_OUTPUT_ONLY, 0), totals.get(FINAL_REMOVED, 0)))
    ap("- Đã verify đủ pipeline: **%d** `IMPLEMENTED_VERIFIED`."
       % totals.get(FINAL_IMPLEMENTED, 0))
    ap("")

    ap("## Gate 2 chiều: %d drift" % len(drifts))
    ap("")
    if drifts:
        ap("Tool exit != 0. Mỗi dòng là drift manifest <-> evidence KHÔNG "
           "được tự sửa để qua gate:")
        ap("")
        for d in drifts:
            ap("- `[%s]` %s / %s — %s"
               % (d["gate"], d["form_id"], d["section_id"], d["detail"]))
    else:
        ap("Không có drift.")
    ap("")

    ap("## Danh sách section theo final_status")
    ap("")
    for st in FINAL_STATUSES:
        grp = [r for r in rows if r["final_status"] == st]
        if not grp:
            continue
        ap("### %s (%d)" % (st, len(grp)))
        ap("")
        for r in grp:
            note = (" — %s" % r["detail"]) if r["detail"] else ""
            ap("- `%s` / `%s` (%s, manifest: %s)%s"
               % (r["form_id"], r["section_id"], r["kind"],
                  r["manifest_status"], note))
        ap("")

    ap("## Ma trận đầy đủ (111 hàng)")
    ap("")
    ap("Evidence rút gọn; bản đầy đủ trong `docs/table_coverage_current.json`.")
    ap("")
    cols = ["form_id", "section_id", "kind", "manifest_status", "override",
            "spec", "template", "form_maps", "blocks", "runtime", "draft",
            "validation", "docx_render", "visual", "final_status"]
    ap("| " + " | ".join(cols) + " |")
    ap("|" + "---|" * len(cols))
    for r in rows:
        cells = []
        for c in cols:
            v = str(r[c])
            v = v.replace("|", "\\|").replace("\n", " ")
            if c in ("override", "spec", "template", "form_maps", "blocks",
                     "runtime", "draft", "validation", "docx_render"):
                # rút gọn prefix stage cho vừa bảng
                v = re.sub(r"^(spec|form_maps|runtime|docx_render|blocks|"
                           r"draft|validation|template): ", "", v)
                if len(v) > 90:
                    v = v[:87] + "..."
            cells.append(v if v else "—")
        ap("| " + " | ".join(cells) + " |")
    ap("")
    return "\n".join(lines)


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


# ============================================================ main

def main(argv=None):
    manifest = load_json(MANIFEST_PATH)
    form_maps = load_json(FORM_MAPS_PATH)
    overrides = parse_overrides()
    runtime = parse_runtime_index()

    forms = manifest["forms"]
    sections_all = [(f, s) for f in forms for s in f["sections"]]

    # cache blocks + spec docs + templates (1 lần chạy)
    blocks = {}
    blocks_norm = {}
    blocks_loop_names = {}
    for fid in sorted({f["form_id"] for f in forms}):
        p = os.path.join(BLOCKS_DIR, "%s.json" % fid)
        if os.path.exists(p):
            doc = load_json(p)
            blocks[fid] = doc
            blocks_norm[fid] = blocks_text_all(doc)
            names = set()
            for b in iter_block_items(doc):
                if b.get("t") == "loop":
                    nm = b.get("loop") or b.get("name")
                    if nm:
                        names.add(nm)
            blocks_loop_names[fid] = names
    spec_docs = {f["form_id"]: load_spec_docs(f["form_id"]) for f in forms}

    template_tables = {}
    for fid in sorted({f["form_id"] for f in forms}):
        template_tables[fid] = count_template_tables(fid)

    # inventory tên loop/section implementation theo form (cho bridge)
    fm_by_form = form_maps or {}
    runtime_inventory = {}
    for fid in sorted({f["form_id"] for f in forms}):
        inv = set(blocks_loop_names.get(fid) or set())
        inv |= set(runtime["grid_meta"].keys())
        inv |= set((runtime["form_grid_meta"].get(fid) or {}).keys())
        inv |= set(runtime["form_contracts"].get(fid) or [])
        for dt in (fm_by_form.get(fid) or {}).get("dynamic_tables") or []:
            for k in (dt.get("id"), dt.get("loop")):
                if k:
                    inv.add(k)
        for ss in (fm_by_form.get(fid) or {}).get("section_specs") or []:
            for k in (ss.get("id"), ss.get("section_id"),
                      ss.get("semantic_key")):
                if k:
                    inv.add(k)
        runtime_inventory[fid] = inv

    ctx = {
        "overrides": overrides,
        "form_maps": form_maps,
        "blocks": blocks,
        "blocks_norm": blocks_norm,
        "spec_docs": spec_docs,
        "runtime": runtime,
        "template_tables": template_tables,
        "runtime_inventory": runtime_inventory,
    }

    rows, rows_full = [], []
    for f, s in sections_all:
        row, row_full = audit_section(f, s, ctx)
        rows.append(row)
        rows_full.append(row_full)

    manifest_index = {(f["form_id"], s["section_id"]) for f, s in sections_all}
    drifts = collect_drifts(rows, overrides, manifest_index, len(rows))

    totals = Counter(r["final_status"] for r in rows)
    totals_by_manifest = Counter(r["manifest_status"] for r in rows)
    head = git_head()

    payload = OrderedDict([
        ("meta", {
            "tool": "tools/census/table_coverage_audit.py",
            "head": head,
            "expected_sections": EXPECTED_SECTIONS,
            "n_forms": len(forms),
            "n_sections": len(rows),
            "visual_audit": "NOT RUN (không có browser ở môi trường này)",
            "docx_render_note": "structural-only (w:tbl + anchors qua "
                                "form_maps/blocks), KHÔNG phải visual",
            "runtime_note": "presence của section/loop key trong "
                            "app_web/ui JS + structured GRID_META / "
                            "FORM_GRID_META / FORM_TABLE_CONTRACTS index; "
                            "draft & validation = presence key trong corpus "
                            "app_web/ui (form-domain.js + module UI); bridge "
                            "tên loop chỉ từ evidence của override",
            "legal_blocker_note": "BLOCKED_OWNER chỉ khi KHÔNG có bằng chứng "
                                  "bảng VÀ (notes ghi blocker HOẶC form có "
                                  "legal_questions) — không suy diễn pháp lý",
        }),
        ("totals_final_status", OrderedDict(
            (st, totals.get(st, 0)) for st in FINAL_STATUSES)),
        ("totals_manifest_status", dict(totals_by_manifest)),
        ("drifts", drifts),
        ("rows", rows_full),
    ])
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    # [Wave E] --no-write: runner chỉ cần verdict drift, không ghi đè file
    # docs (stamp head đổi mỗi commit -> làm bẩn tree sau mỗi lần runner).
    no_write = "--no-write" in (argv if argv is not None else sys.argv[1:])
    if not no_write:
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write(build_md(rows, totals, drifts, head))

    print("sections: %d | forms: %d | head: %s" % (len(rows), len(forms), head))
    print("totals:", dict(totals))
    print("manifest statuses:", dict(totals_by_manifest))
    if drifts:
        print("\nGATE FAIL — %d drift:" % len(drifts))
        for d in drifts:
            print("  [%s] %s / %s — %s"
                  % (d["gate"], d["form_id"], d["section_id"], d["detail"]))
        print("\nwrote %s\nwrote %s" % (OUT_JSON, OUT_MD))
        return 1
    print("\nGATE PASS — no drift")
    print("wrote %s\nwrote %s" % (OUT_JSON, OUT_MD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
