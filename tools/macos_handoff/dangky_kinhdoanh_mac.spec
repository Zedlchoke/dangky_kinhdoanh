# -*- mode: python ; coding: utf-8 -*-
"""dangky_kinhdoanh_mac.spec — PyInstaller spec cho "Trợ lý hồ sơ ĐKKD" macOS.

Build TÁI LẬP được (PLAN §7 wave P1), chạy từ root repo trên macOS (arm64
hoặc Intel — bundle chỉ chạy được trên kiến trúc build):

    python3 -m PyInstaller --clean --noconfirm tools/macos_handoff/dangky_kinhdoanh_mac.spec

Kết quả: dist/DangKyKinhDoanh.app — **windowed + onedir** (PLAN §7.3: ưu tiên
onedir để debug/export bền vững; chỉ cân nhắc onefile sau khi vị trí
generated_ho_so đã cố định ở thư mục người dùng).

Layout bundle (SAO CHÉP NGUYÊN cấu trúc repo; app_web/main.py chạy lại qua
launch_app_web.py với đúng __file__ — xem header file đó):
    app_web/main.py          (DATA — runpy cần bản .py thật, không phải .pyc)
    app_web/ui/**            (index.html, style.css, app.js, form-domain…, mock/)
    app/data/**              (blocks 87, form_maps.json, use_cases.json,
                              nganh_vsic.json [VSIC đầy đủ, không mock mini],
                              questionnaire/ 7, table_specs/, ui_layouts/,
                              layout_specs/, form_maps.js, use_cases.js)
    app/templates/**         (87 .docx gốc — form_maps.json trỏ
                              templates/<id>.docx TÍNH TỪ app/, docx_render đọc)
    tools/phase5r_expectations.json  (docx_render đọc lúc render: ngưỡng vùng
                              ký per-form; vắng mặt -> rơi về {} — vẫn bundle
                              để hành vi GIỐNG HỆT chạy từ source)

CỐ Ý KHÔNG bundle (PLAN §7.4 + F6.2):
    profiles/                (hồ sơ cá nhân — PII)
    generated_ho_so/         (hồ sơ sinh thử / evidence máy cá nhân)
    docs/, evidence/, 99_muc_luc/ (legacy), app_tk/ (legacy UI)
    tools/test_*.py, app_web/test_*.js (test suite)

pywebview lấy từ pip (repo KHÔNG có .webview_deps trên máy này); backend
macOS là WKWebView qua PyObjC (webview.platforms.cocoa — bắt buộc liệt kê
hiddenimport vì pywebview chọn backend bằng importlib ĐỘNG, modulegraph
không quét được).

pywebview/PyInstaller CHƯA pin trong requirements-dev.txt ("không pin mù") —
ghi version thật vào build manifest khi build (build_app.sh tự ghi).
"""
import os

from PyInstaller.utils.hooks import collect_data_files

# SPECPATH = thư mục chứa spec (tools/macos_handoff); root repo 2 cấp trên.
SPEC_DIR = SPECPATH
TOOLS_DIR = os.path.dirname(SPEC_DIR)
REPO = os.path.dirname(TOOLS_DIR)


def _repo(*parts):
    return os.path.join(REPO, *parts)


datas = [
    # main.py là DATA (runpy chạy bản .py trong bundle) — KHÔNG phải entry.
    (_repo("app_web", "main.py"), "app_web"),
    (_repo("app_web", "ui"), "app_web/ui"),
    (_repo("app", "data"), "app/data"),
    (_repo("app", "templates"), "app/templates"),
    # docx_render đọc tools/phase5r_expectations.json lúc render
    # (parent.parent/tools/… tính từ __file__ của nó = _MEIPASS/tools/…).
    (_repo("tools", "phase5r_expectations.json"), "tools"),
]
# pywebview cài từ pip: bundle kèm data (js/css của pywebview).
datas += collect_data_files("webview")

hiddenimports = [
    # Dialog mở/lưu draft + phiếu Excel trong app_web/main.py dùng tkinter.
    "tkinter",
    "tkinter.filedialog",
    # pywebview + backend macOS (WKWebView qua PyObjC). main.py đi vào bundle
    # dạng DATA nên modulegraph không quét được; pywebview import backend
    # bằng importlib động -> PHẢI liệt kê tường minh.
    "webview",
    "webview.platforms.cocoa",
    # Import trễ bên trong app_web/main.py (runtime `from tools.x import …`):
    # tools/ là namespace package (KHÔNG có __init__.py) — điểm rủi ro cao
    # nhất của bundle; liệt kê tường minh cả code lẫn module con.
    "tools",
    "tools.docx_render",
    "tools.excel_export",
    "tools.excel_import",
    "tools.questionnaire",
    "tools.questionnaire.schema",
    "tools.layout_roles",
    # docx_render lazy `import docx` (python-docx) trong hàm merge-XML.
    "docx",
]

# Wave E2 (Excel case-level, lane KHÁC sở hữu) đang thêm lazy import
# `tools.excel_case_export` / `tools.excel_case_import` trong app_web/main.py
# + manifests `app/data/case_questionnaires/` (đi theo bundle tự động nhờ
# datas CẢ THƯ MỤC app/data). Thêm hiddenimport khi module đã tồn tại
# (PyInstaller ERROR nếu hiddenimport thiếu) — sau khi lane E merge, dòng
# điều kiện này tự kích hoạt; không cần sửa spec.
for _mod in ("excel_case_export", "excel_case_import"):
    if os.path.isfile(_repo("tools", _mod + ".py")):
        hiddenimports.append("tools." + _mod)

a = Analysis(
    [_repo("tools", "macos_handoff", "launch_app_web.py")],
    pathex=[REPO],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Không cho modulegraph kéo nhầm đống test/evidence qua package tools.
        "tools.test_acceptance_docx",
        "profiles",
        "app_tk",
        "tkinter.test",
        "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binaries/datas do COLLECT đem đi
    name="DangKyKinhDoanh",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed .app — KHÔNG mở Terminal khi double-click
    icon=None,
    entitlements_file=_repo("tools", "macos_handoff", "entitlements.plist"),
    codesign_identity=None,  # KHÔNG codesign thật — máy không có cert
    # (PyInstaller vẫn ad-hoc sign bắt buộc trên Apple Silicon; xem README).
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DangKyKinhDoanh",
)

app = BUNDLE(
    coll,
    name="DangKyKinhDoanh.app",
    bundle_identifier="vn.dkkd.trolyhoso",
)
