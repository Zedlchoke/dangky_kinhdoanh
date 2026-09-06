# -*- mode: python ; coding: utf-8 -*-
"""dangky_kinhdoanh.spec — PyInstaller spec cho "Trợ lý hồ sơ ĐKKD" (F6/O6).

Build TÁI LẬP được (không build thủ công một lần — PLAN F6.1), chạy từ root
repo trên Windows 10/11 với Python 3.11+ 64-bit:

    pyinstaller --clean --noconfirm tools\\windows_handoff\\dangky_kinhdoanh.spec

Kết quả: dist\\DangKyKinhDoanh.exe (onefile, console=True để S1 đọc được
traceback console theo docs/platform_smoke_checklist.md).

Layout bundle (SAO CHÉP NGUYÊN cấu trúc repo, app_web/main.py chạy lại qua
launch_app_web.py với đúng __file__ — xem header file đó):
    app_web/main.py          (DATA — runpy cần bản .py thật, không phải .pyc)
    app_web/ui/**            (index.html, style.css, render/app/form-domain…, mock/)
    app/data/**              (blocks 87, form_maps, use_cases, nganh_vsic.json
                              [VSIC đầy đủ, không dùng mock/mini], questionnaire/,
                              layout_specs/, table_specs/, ui_layouts/)
    app/templates/**         (87 .docx gốc — form_maps.json trỏ
                              templates/<id>.docx TÍNH TỪ app/, export render
                              đọc trực tiếp)
    .webview_deps/**         (CHỈ khi repo có — pywebview vendored; nếu không
                              có thì pywebview lấy từ pip, xem hiddenimports)

CỐ Ý KHÔNG bundle (PLAN F6.2):
    profiles/                (hồ sơ cá nhân)
    generated_ho_so/         (hồ sơ sinh thử / evidence)
    docs/, evidence/, tools/test_*.py, app_web/test_*.js (test & evidence)
    app_tk/                  (legacy UI; P7: deprecated sau khi pywebview PASS)

LƯU Ý build manifest (PLAN F6.1): trước khi build GHI LẠI
`python --version`, `pip freeze`, `pyinstaller --version`, version
"Microsoft Edge WebView2 Runtime" vào evidence/Windows_build_manifest.txt.
Version pywebview/PyInstaller khóa tại lần probe thật đầu tiên (requirements-dev.txt
hiện chưa pin pywebview/PyInstaller — cập nhật pin SAU khi Windows runner
probe xong; không pin mù từ máy macOS).
"""
import os

# SPECPATH = thư mục chứa spec (tools/windows_handoff); root repo 2 cấp trên.
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
]
# pywebview vendored (nếu có) — bundle y nguyên để main.py tìm thấy ở đúng chỗ.
if os.path.isdir(_repo(".webview_deps")):
    datas.append((_repo(".webview_deps"), ".webview_deps"))

hiddenimports = [
    # Dialog mở/lưu draft + phiếu Excel trong app_web/main.py dùng tkinter.
    "tkinter",
    "tkinter.filedialog",
    # pywebview + backend Windows (Edge WebView2 / WinForms qua pythonnet).
    # Modulegraph không quét được chúng vì main.py đi vào bundle dạng DATA.
    "webview",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr_loader",
    "pythonnet",
    # Import trễ bên trong app_web/main.py (runtime `from tools.x import …`):
    "tools",
    "tools.docx_render",
    "tools.excel_export",
    "tools.excel_import",
]

a = Analysis(
    [_repo("tools", "windows_handoff", "launch_app_web.py")],
    pathex=[REPO],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Không cho_modulegraph kéo nhầm đống test/evidence qua package tools.
        "tools.test_acceptance_docx",
        "profiles",
        "app_tk",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# KHÔNG có COLLECT() => onefile.
# runtime_tmpdir=None: extract vào %TEMP%\_MEIxxxx mỗi lần chạy và bị XOÁ khi
# thoát => generated_ho_so ghi trong phiên sẽ mất nếu quên chép ra;
# launch_app_web.py có bước rescue-copy sang Documents\DangKyKinhDoanh\
# làm lưới an toàn. Người chạy phải mở thư mục export NGAY trong phiên (S6).
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DangKyKinhDoanh",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # tắt UPX: giảm nguy cơ antivirus xoá nhầm exe chưa ký
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # S1 yêu cầu đọc được traceback console nếu launch lỗi
    icon=None,
)
