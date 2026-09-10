#!/usr/bin/env bash
# =============================================================================
# build_app.sh — build DangKyKinhDoanh.app TÁI LẬP được (wave P1, PLAN §7).
#
# Quy trình (PLAN §7.3 + tương đương F6.1/F6.3):
#   1. Ghi build manifest (python/pyinstaller/pywebview version, commit, macOS,
#      arch, trạng thái codesign) vào thư mục evidence NGOÀI git.
#   2. Build LẦN 1 từ checkout sạch bằng spec onedir/windowed.
#   3. Build LẦN 2 từ checkout sạch (xoá build/ + dist/ giữa 2 lần).
#   4. So inventory (đường dẫn tương đối + SHA-256 từng file) 2 lần build +
#      SHA-256 executable chính. Khác timestamp có giải thích là hợp lệ.
#   5. Kiểm negative: KHÔNG profiles/, generated_ho_so/, docs/, 99_muc_luc/
#      trong bundle (không PII/evidence máy cá nhân).
#
# Output: <repo>/dist/DangKyKinhDoanh.app  +  <repo>/dist/_build1_DangKyKinhDoanh.app
# Evidence: $DKKD_EVIDENCE_DIR (mặc định ~/Documents/DangKyKinhDoanh/evidence_macos
# — NGOÀI git; không bao giờ ghi evidence vào repo).
#
# Dùng:  bash tools/macos_handoff/build_app.sh
# =============================================================================
set -euo pipefail

SPEC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SPEC_DIR/../.." && pwd)"
SPEC="$SPEC_DIR/dangky_kinhdoanh_mac.spec"
PYTHON="${DKKD_PYTHON:-python3}"
EVIDENCE="${DKKD_EVIDENCE_DIR:-$HOME/Documents/DangKyKinhDoanh/evidence_macos}"
BUILD="$REPO/build"
DIST="$REPO/dist"
APP_NAME="DangKyKinhDoanh.app"

log()  { printf '\033[1;36m[build]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[WARN ]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[FAIL ]\033[0m %s\n' "$*"; exit 1; }

mkdir -p "$EVIDENCE"

# ---- .git/info/exclude (local-only, KHÔNG đụng .gitignore) ----------------
# build/ và dist/ chưa có trong .gitignore của repo; thêm local exclude để
# artifact không bao giờ rơi vào `git add`. Báo lại Lead để quyết định có
# đưa hẳn vào .gitignore (thay đổi tracked) hay không.
for d in "/build/" "/dist/"; do
    grep -qx "$d" "$REPO/.git/info/exclude" 2>/dev/null || printf '%s\n' "$d" >> "$REPO/.git/info/exclude"
done

# ---- Build manifest --------------------------------------------------------
MANIFEST="$EVIDENCE/macOS_build_manifest.txt"
COMMIT="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo 'khong-phai-git')"
PY_VER="$("$PYTHON" --version 2>&1)"
PYI_VER="$("$PYTHON" -m PyInstaller --version 2>&1)"
WEBVIEW_VER="$("$PYTHON" -c 'import importlib.metadata as m; print(m.version("pywebview"))' 2>/dev/null || echo 'KHONG CO')"
OPENPYXL_VER="$("$PYTHON" -c 'import importlib.metadata as m; print(m.version("openpyxl"))' 2>/dev/null || echo '?')"
DOCX_VER="$("$PYTHON" -c 'import importlib.metadata as m; print(m.version("python-docx"))' 2>/dev/null || echo '?')"
ARCH="$(uname -m)"
MACOS_VER="$(sw_vers -productVersion 2>/dev/null || echo '?')"
IDENTITIES="$(security find-identity -v -p codesigning 2>/dev/null | grep -c ')' || true)"

{
    echo "=== macOS build manifest — $(date '+%Y-%m-%d %H:%M:%S') ==="
    echo "repo            : $REPO"
    echo "commit          : $COMMIT"
    echo "git status      :"
    git -C "$REPO" status --porcelain | sed 's/^/    /'
    echo "python          : $PY_VER"
    echo "pyinstaller     : $PYI_VER"
    echo "pywebview       : $WEBVIEW_VER"
    echo "openpyxl        : $OPENPYXL_VER"
    echo "python-docx     : $DOCX_VER"
    echo "macOS           : $MACOS_VER ($ARCH)"
    echo "codesign identities hợp lệ: $IDENTITIES (0 = app chỉ ad-hoc sign, unsigned)"
    echo "spec            : $SPEC"
    echo "evidence        : $EVIDENCE"
} > "$MANIFEST"
log "Build manifest -> $MANIFEST"

# ---- Trạng thái checkout sạch (cảnh báo, không chặn) ----------------------
# "Checkout sạch" nghĩa là KHÔNG có file lạ ảnh hưởng nội dung bundle;
# chính các file handoff mới (chưa commit) được ghi nhận trong manifest.
DIRTY="$(git -C "$REPO" status --porcelain -- ':!build' ':!dist' | grep -v '^??' || true)"
if [ -n "$DIRTY" ]; then
    warn "Working tree có thay đổi tracked chưa commit — ghi nhận trong manifest:"
    printf '%s\n' "$DIRTY" | sed 's/^/    /'
fi

# ---- Build một lần ---------------------------------------------------------
build_once() {
    local tag="$1"
    log "=== BUILD $tag: xoá build/ dist/ cũ rồi build từ sạch ==="
    rm -rf "$BUILD" "$DIST"
    ( cd "$REPO" && "$PYTHON" -m PyInstaller --clean --noconfirm "$SPEC" \
        > "$EVIDENCE/macOS_build_${tag}_console.log" 2>&1 ) \
        || { tail -40 "$EVIDENCE/macOS_build_${tag}_console.log"; fail "PyInstaller build $tag thất bại — xem log."; }

    [ -d "$DIST/$APP_NAME" ] || { tail -40 "$EVIDENCE/macOS_build_${tag}_console.log"; fail "Không thấy dist/$APP_NAME sau build $tag."; }

    # Negative check: không PII/evidence trong bundle.
    local bad=""
    for p in profiles generated_ho_so 99_muc_luc docs app_tk evidence; do
        [ -e "$DIST/$APP_NAME/Contents/Frameworks/$p" ] && bad="$bad $p"
    done
    [ -z "$bad" ] || fail "Bundle chứa thư mục cấm:$bad — kiểm spec datas."

    # Inventory: SHA-256 từng file theo đường dẫn tương đối (ổn định 2 lần).
    local inv="$EVIDENCE/macOS_app_inventory_${tag}.txt"
    ( cd "$DIST/$APP_NAME" && find . -type f -print0 | LC_ALL=C sort -z \
        | xargs -0 shasum -a 256 ) > "$inv"
    shasum -a 256 "$DIST/$APP_NAME/Contents/MacOS/DangKyKinhDoanh" \
        > "$EVIDENCE/macOS_exec_sha256_${tag}.txt"
    du -sh "$DIST/$APP_NAME" | awk '{print "size: " $1}' >> "$inv"
    log "BUILD $tag OK — inventory: $inv"
}

build_once "1"
mv "$DIST/$APP_NAME" "$DIST/_build1_$APP_NAME"

build_once "2"

# ---- So sánh 2 lần build ---------------------------------------------------
DIFF_OUT="$EVIDENCE/macOS_app_inventory_diff.txt"
if diff -u "$EVIDENCE/macOS_app_inventory_1.txt" \
           "$EVIDENCE/macOS_app_inventory_2.txt" > "$DIFF_OUT" 2>&1; then
    log "Inventory 2 lần build GIỐNG NHAU 100% (cả SHA-256 từng file)."
    echo "IDENTICAL: inventory + SHA-256 mọi file giống hệt giữa build 1 và 2." \
        > "$DIFF_OUT"
else
    warn "Inventory 2 lần build KHÁC — xem $DIFF_OUT (khác timestamp/metadata"
    warn "cần được giải thích; khác NỘI DUNG module/data là FAIL tái lập)."
fi

# Trạng thái codesign của artifact cuối.
{
    echo "=== codesign artifact cuối (build 2) ==="
    codesign -dv "$DIST/$APP_NAME" 2>&1 || true
    codesign --verify --deep --strict "$DIST/$APP_NAME" 2>&1 || true
    spctl -a -vv "$DIST/$APP_NAME" 2>&1 || true
} > "$EVIDENCE/macOS_codesign_status.txt" 2>&1 || true

log "=== XONG ==="
log "Artifact : $DIST/$APP_NAME (+ $DIST/_build1_$APP_NAME để đối chiếu)"
log "SHA-256 exec: $(awk '{print $1}' "$EVIDENCE/macOS_exec_sha256_2.txt")"
log "Diff inventory: $DIFF_OUT"
log "Evidence (ngoài git): $EVIDENCE"
