#!/usr/bin/env bash
# =============================================================================
# run_smoke_mac.sh — smoke S1–S8 (bản macOS) cho DangKyKinhDoanh.app (wave P1).
#
# Tương tự tools/windows_handoff/run_smoke_s1_s8.ps1:
#   - Ghi log vào $DKKD_EVIDENCE_DIR/macOS_<buoc>.log (mặc định evidence NGOÀI
#     git: ~/Documents/DangKyKinhDoanh/evidence_macos).
#   - Bước cần NHÌN MÀN HÌNH in "[MANUAL]" và chờ người chạy nhập P/F/S —
#     script KHÔNG TỰ PASS bước visual, KHÔNG tự đánh PASS theo ước lượng.
#   - Bước MÁY ĐỌC được tự PASS/FAIL (process sống, file sinh ra, exit code).
#
# Thêm so với Windows (đặc thù macOS + bundle đã build):
#   S-eng    engine probe BÊN TRONG bundle frozen: render DOCX từ fixture,
#            PDF qua soffice, Excel export→điền→import round-trip.
#   S-path   copy .app sang đường dẫn có dấu tiếng Việt + space rồi probe lại.
#   S-restart chạy app lần 2 + probe lần 2 (assets bền qua restart — Gate P1).
#   S-privacy bundle KHÔNG chứa profiles/, generated_ho_so/, docs/, 99_muc_luc/.
#   S8       clean-machine (Máy khác KHÔNG có Python) — mặc định NOT RUN.
#
# KHÔNG tải xuống gì; chỉ kiểm deps đã cài (python3, pywebview, soffice).
#
# Dùng:  bash tools/macos_handoff/run_smoke_mac.sh            # sau khi build
#        DKKD_APP=/path/to/DangKyKinhDoanh.app bash ... run_smoke_mac.sh
# =============================================================================
set -uo pipefail

SPEC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SPEC_DIR/../.." && pwd)"
APP="${DKKD_APP:-$REPO/dist/DangKyKinhDoanh.app}"
BIN="$APP/Contents/MacOS/DangKyKinhDoanh"
EVIDENCE="${DKKD_EVIDENCE_DIR:-$HOME/Documents/DangKyKinhDoanh/evidence_macos}"
PYTHON="${DKKD_PYTHON:-python3}"
RESCUE_DIR="$HOME/Documents/DangKyKinhDoanh/generated_ho_so"

mkdir -p "$EVIDENCE"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
AUTO_FAIL=0

c_step() { printf '\033[1;36m[smoke]\033[0m %s\n' "$*"; }
c_ok()   { printf '\033[1;32m[PASS ]\033[0m %s\n' "$*"; }
c_bad()  { printf '\033[1;31m[FAIL ]\033[0m %s\n' "$*"; }
c_man()  { printf '\033[1;33m[MANUAL]\033[0m %s\n' "$*"; }

log_step() { # log_step <tag> <dòng...>
    local tag="$1"; shift
    { echo "=== macOS $tag | run $STAMP | user=$(id -un) | host=$(hostname -s) ==="; printf '%s\n' "$@"; } \
        >> "$EVIDENCE/macOS_${tag}.log"
    c_step "log -> $EVIDENCE/macOS_${tag}.log"
}

auto_result() { # auto_result <tag> <tên-kiểm> <0|1> <chi tiết>
    local tag="$1" name="$2" ok="$3" detail="$4"
    if [ "$ok" = "0" ]; then
        c_ok "$name $detail"
        log_step "$tag" "AUTO PASS: $name $detail"
    else
        c_bad "$name $detail"
        log_step "$tag" "AUTO FAIL: $name $detail"
        AUTO_FAIL=$((AUTO_FAIL + 1))
    fi
}

ask_verdict() { # ask_verdict <tag> <tiêu đề> <mục...>  -> in P/F/S
    local tag="$1" title="$2"; shift 2
    echo ""
    c_man "kiểm tra (S$tag): $title"
    local item
    for item in "$@"; do printf '    - %s\n' "$item"; done
    printf '    Chụp màn hình lưu: %s (gợi ý tên: macOS_S%s_*.png)\n' "$EVIDENCE" "$tag"
    local v=""
    while [ "$v" != "P" ] && [ "$v" != "F" ] && [ "$v" != "S" ]; do
        read -r -p "  S$tag verdict [P=PASS / F=FAIL / S=skip NOT RUN]: " v || v="S"
        v="$(printf '%s' "$v" | tr '[:lower:]' '[:upper:]')"
    done
    case "$v" in
        P) log_step "$tag" "VERDICT (người chạy nhìn màn hình): PASS" ;;
        F) log_step "$tag" "VERDICT (người chạy nhìn màn hình): FAIL" ;;
        S) log_step "$tag" "VERDICT: NOT RUN (skip)" ;;
    esac
}

launch_gui() { # launch_gui <tag> [args...]  -> đặt GUI_PID; echo 0 nếu sống, 1 nếu chết
    local tag="$1"; shift
    local out="$EVIDENCE/macOS_${tag}_console_out.log" err="$EVIDENCE/macOS_${tag}_console_err.log"
    rm -f "$out" "$err"
    c_step "launch: $BIN $*"
    "$BIN" "$@" > "$out" 2> "$err" &
    GUI_PID=$!
    local i alive=1
    for i in $(seq 1 12); do
        sleep 1
        if ! kill -0 "$GUI_PID" 2>/dev/null; then alive=1; break; fi
        alive=0
    done
    if [ "$alive" = "0" ]; then
        c_ok "app SỐNG sau 12s (PID $GUI_PID)"
        log_step "$tag" "App sống sau 12s. PID=$GUI_PID. Console 20s đầu:" \
            "$(head -30 "$out" 2>/dev/null)" "$(head -30 "$err" 2>/dev/null)"
    else
        local code="?"
        wait "$GUI_PID" 2>/dev/null; code=$?
        c_bad "app THOÁT SỚM (exit=$code) trong 12s đầu"
        log_step "$tag" "FAIL: app thoát sớm trong 12s. ExitCode=$code" \
            "--- console out ---" "$(cat "$out" 2>/dev/null)" \
            "--- console err ---" "$(cat "$err" 2>/dev/null)"
    fi
    return "$alive"
}

close_gui() { # close_gui <tag> — chờ người dùng đóng cửa sổ, tối đa 150s rồi kill
    local tag="$1"
    GUI_EXIT=""
    echo ""
    c_man "ĐÓNG cửa sổ ứng dụng (nút X) để script tiếp tục..."
    local i
    for i in $(seq 1 150); do
        kill -0 "$GUI_PID" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$GUI_PID" 2>/dev/null; then
        c_bad "app không tự đóng sau 150s — gửi SIGTERM."
        kill "$GUI_PID" 2>/dev/null
        sleep 3
        kill -9 "$GUI_PID" 2>/dev/null
        log_step "$tag" "App bị kill cưỡng bức sau 150s (không đóng tay)."
    fi
    wait "$GUI_PID" 2>/dev/null
    GUI_EXIT=$?
    log_step "$tag" "App đã đóng. ExitCode=$GUI_EXIT (kỳ vọng 0)." \
        "--- console out (toàn bộ) ---" "$(cat "$EVIDENCE/macOS_${tag}_console_out.log" 2>/dev/null)" \
        "--- console err (toàn bộ) ---" "$(cat "$EVIDENCE/macOS_${tag}_console_err.log" 2>/dev/null)"
}

# ================================================================= S0 preflight
echo "==== macOS smoke S1–S8 + structural | run $STAMP ===="
echo "Repo     : $REPO"
echo "App      : $APP"
echo "Evidence : $EVIDENCE"
echo ""

PF=()
PF+=("commit: $(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo '?')")
PF+=("macOS: $(sw_vers -productVersion 2>/dev/null) ($(uname -m))")
PF+=("python3: $("$PYTHON" --version 2>&1)")
if "$PYTHON" -c 'import webview' 2>/dev/null; then
    PF+=("pywebview: $("$PYTHON" -c 'import importlib.metadata as m; print(m.version("pywebview"))' 2>/dev/null)")
else
    PF+=("pywebview: THIẾU (GUI launch sẽ fail — đọc docs/macos_handoff.md)")
fi
if command -v soffice >/dev/null 2>&1 || [ -x "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]; then
    PF+=("soffice: $(command -v soffice || echo '/Applications/LibreOffice.app/Contents/MacOS/soffice')")
else
    PF+=("soffice: KHÔNG CÓ — PDF + normalize Word-compat sẽ NOT RUN")
fi
if codesign -dv "$APP" >/dev/null 2>&1; then
    PF+=("codesign: $(codesign -dv "$APP" 2>&1 | grep -m1 'Signature=' || echo 'có')")
    codesign --verify --deep --strict "$APP" >/dev/null 2>&1 \
        && PF+=("codesign verify: OK (ad-hoc/unsigned cục bộ)") \
        || PF+=("codesign verify: FAIL")
else
    PF+=("codesign: KHÔNG CÓ signature")
fi
spctl -a -vv "$APP" >"$EVIDENCE/macOS_spctl.txt" 2>&1 \
    && PF+=("spctl assess: chấp nhận") \
    || PF+=("spctl assess: REJECTED (dự kiến với app chưa ký — Gatekeeper ghi evidence, xem macOS_spctl.txt)")
log_step "0_PREFLIGHT" "${PF[@]}"

if [ ! -x "$BIN" ]; then
    c_bad "Không thấy executable: $BIN — build trước (tools/macos_handoff/build_app.sh)."
    exit 2
fi

# ==================================================================== S1
launch_gui "S1"
S1_ALIVE=$?
if [ "$S1_ALIVE" = "0" ]; then
    auto_result "S1" "launch .app — process còn sống sau 12s" 0 "(PID $GUI_PID)"
    ask_verdict "1" "Cửa sổ desktop đã mở đúng?" \
        "Cửa sổ 'Trợ lý hồ sơ ĐKKD' hiện ra (không trắng trang, không traceback console)" \
        "Ghi version macOS + đã mở bằng .app chưa ký (right-click > Open nếu Gatekeeper chặn lần đầu)"
else
    auto_result "S1" "launch .app — process còn sống sau 12s" 1 ""
fi

# ==================================================================== S2–S5
if [ "$S1_ALIVE" = "0" ]; then
    ask_verdict "2" "UI render danh sách thủ tục" \
        "Danh sách 28 thủ tục hiển thị, không trắng trang / layout vỡ" \
        "Khác biệt so Windows: WKWebView — mở lại DevTools không được như WebView2, kiểm bằng thao tác UI"
    ask_verdict "3" "Chọn thủ tục + nhập từng kind dữ liệu" \
        "text, money, percent, checkbox, radio" \
        "vsic (tìm ngành), editable-grid (thêm/xoá dòng)" \
        "fixed-matrix, nested-grid, output-table" \
        "Chụp screenshot từng kind -> $EVIDENCE"
    ask_verdict "4" "Dialog MỞ hồ sơ .json (tkinter)" \
        "Nút 'Mở hồ sơ .json' -> dialog tkinter mở được trên macOS" \
        "Chọn file .json hợp lệ -> dữ liệu nạp đúng vào app"
    ask_verdict "5" "Dialog LƯU hồ sơ (draft)" \
        "Lưu draft .json thành công" \
        "Mở lại bằng S4 -> đúng dữ liệu vừa lưu"
fi

# ==================================================================== S6
if [ "$S1_ALIVE" = "0" ]; then
    S6_START="$(date +%s)"
    ask_verdict "6" "Xuất DOCX/ZIP (blocked trước, sạch sau)" \
        "1) Hồ sơ CÓ blocking error -> export PHẢI bị chặn, không sinh file" \
        "2) Hồ sơ sạch -> export OK, ZIP mở được" \
        "3) Mở .docx bằng Word for Mac/LibreOffice thật (ghi app + version)" \
        "Có LibreOffice: thử cả 3 định dạng docx/pdf/both"
    # Auto evidence: thư mục export MỚI (bundle + rescue dir)
    s6_lines=()
    for root_dir in "$APP/Contents/Frameworks/generated_ho_so" "$RESCUE_DIR"; do
        if [ -d "$root_dir" ]; then
            while IFS= read -r d; do
                n=$(find "$d" -type f | wc -l | tr -d ' ')
                s6_lines+=("$d : $n file")
            done < <(find "$root_dir" -maxdepth 1 -type d -newmt "$(date -r "$S6_START" '+%Y%m%d%H%M%S')" 2>/dev/null)
        fi
    done
    if [ "${#s6_lines[@]}" -gt 0 ]; then
        log_step "6" "AUTO evidence — thư mục export mới kể từ lúc chạy script:" "${s6_lines[@]}"
    else
        log_step "6" "AUTO evidence: CHƯA thấy thư mục export mới (rescue-copy chạy KHI ĐÓNG app — đóng app rồi xem lại ~/Documents/DangKyKinhDoanh/generated_ho_so)."
    fi
    close_gui "S6"
    [ "$GUI_EXIT" = "0" ] \
        && auto_result "S6" "app đóng sạch sau export, exit code" 0 "(exit=$GUI_EXIT)" \
        || auto_result "S6" "app đóng sạch sau export, exit code" 1 "(exit=$GUI_EXIT — kỳ vọng 0)"
fi

# ==================================================================== S7 offline
echo ""
read -r -p "S7 OFFLINE: Đã NGẮT mạng (tắt wifi/rút cáp) chưa? [y/N]: " off </dev/tty || off="N"
log_step "7" "Người chạy xác nhận đã ngắt mạng: ${off:-N}"
if [ "${off:-N}" = "Y" ]; then
    if launch_gui "S7"; then
        ask_verdict "7" "Offline: lặp lại nhanh S2–S6" \
            "UI vẫn render (S2), nhập dữ liệu vẫn OK (S3)" \
            "Mở/lưu draft vẫn OK (S4–S5)" \
            "Export DOCX/ZIP vẫn OK (S6)" \
            "App KHÔNG cần mạng (WKWebView không tải gì từ internet)"
        close_gui "S7"
    fi
    read -r -p "Bật lại mạng rồi nhấn Enter..." _ </dev/tty || true
else
    log_step "7" "VERDICT: NOT RUN (người chạy không ngắt mạng)."
fi

# =============================================== S-eng engine probe (AUTO)
cat > "$EVIDENCE/dkkd_engine_probe.py" <<'PYEOF'
"""Engine probe — chạy BÊN TRONG bundle frozen qua launch_app_web.py.

Import tools.* từ PYZ của bundle, render DOCX từ fixture dùng template +
form_maps BUNDLE, PDF qua soffice, Excel export->điền->import round-trip.
Exit 0 = toàn PASS; exit 1 = có FAIL (in rõ từng check).
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

OUT = Path(os.environ["DKKD_PROBE_OUT"])
OUT.mkdir(parents=True, exist_ok=True)
fails = []


def check(name, cond, extra=""):
    print("[probe] %-34s %s %s" % (name, "PASS" if cond else "FAIL", extra))
    if not cond:
        fails.append(name)


base = Path(getattr(sys, "_MEIPASS", "") or Path(sys.executable).resolve().parent)
print("[probe] bundle base (_MEIPASS): %s" % base)

# 1. Data bundle đủ
blocks = list((base / "app/data/blocks").glob("*.json"))
templates = list((base / "app/templates").glob("*.docx"))
fmaps = json.loads((base / "app/data/form_maps.json").read_text(encoding="utf-8"))
qs = list((base / "app/data/questionnaire").glob("*.json"))
check("app/data bundled (blocks+vsic)", len(blocks) == 87
      and (base / "app/data/nganh_vsic.json").is_file(),
      "blocks=%d" % len(blocks))
check("app/templates bundled (87 .docx)", len(templates) == 87,
      "n=%d" % len(templates))
check("form_maps.json 87 form", len(fmaps) == 87)
check("questionnaire bundled", len(qs) >= 1, "n=%d" % len(qs))

# 2. Engine import từ PYZ frozen
from tools.docx_render import write_rendered          # noqa: E402
from tools.excel_export import (                      # noqa: E402
    MAP_COLUMNS, MAP_SHEET, write_questionnaire)
from tools.excel_import import import_questionnaire   # noqa: E402
import tools.layout_roles                             # noqa: E402,F401
import tools.questionnaire.schema                     # noqa: E402,F401
check("engine imports từ PYZ bundle", True)

# 3. DOCX render từ fixture
fmap = fmaps["PLI_M72"]
template = base / "app" / fmap["template"]
docx_out = OUT / "probe_PLI_M72.docx"
data = {
    "dn": {"ten_tieng_viet": "CÔNG TY TNHH THỬ NGHIỆM BUNDLE",
           "ma_so_dn": "031000000000"},
    "dia_chi_chi_tiet": "Số 1 Đường Thử Nghiệm",
    "xa_phuong": "Phường Bến Nghé",
    "tinh_thanh": "TP. Hồ Chí Minh",
    "von_dieu_le_chu": "100.000.000",
}
write_rendered(template, data, docx_out,
               tables_meta=(fmap.get("section_specs") or None))
ok_docx = docx_out.is_file() and docx_out.stat().st_size > 1000
check("DOCX render (bundled engine)", ok_docx and zipfile.is_zipfile(docx_out),
      "%d bytes" % (docx_out.stat().st_size if ok_docx else 0))

# 4. PDF qua soffice
soffice = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
if Path(soffice).exists():
    prof = OUT / ("_lo_prof_%d" % os.getpid())
    try:
        r = subprocess.run(
            [soffice, "--headless", "--norestore",
             "-env:UserInstallation=file://%s" % prof,
             "--convert-to", "pdf", "--outdir", str(OUT), str(docx_out)],
            capture_output=True, text=True, timeout=180)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    pdf = OUT / "probe_PLI_M72.pdf"
    check("PDF qua soffice", r.returncode == 0 and pdf.is_file()
          and pdf.stat().st_size > 0,
          "rc=%d size=%d" % (r.returncode,
                             pdf.stat().st_size if pdf.is_file() else 0))
else:
    print("[probe] soffice KHÔNG có — PDF NOT RUN (ghi evidence)")

# 5. Excel round-trip: export -> điền ĐỦ form theo __map -> import.
#    Import là fail-loud (MISSING_REQUIRED với câu bắt buộc còn trống — đã
#    kiểm chứng thật trên bundle), nên probe phải điền toàn bộ câu như
#    tools/test_excel_roundtrip.py làm với fixture.
import openpyxl  # noqa: E402

q = json.loads((base / "app/data/questionnaire/PLI_M72.json")
               .read_text(encoding="utf-8"))
xlsx = OUT / "probe_phieu.xlsx"
write_questionnaire(q, str(xlsx), meta={"case_id": "probe",
                                        "today": "01/01/2026"})
check("Excel export (write_questionnaire)", xlsx.is_file()
      and xlsx.stat().st_size > 0)

ANSWER = "Công ty TNHH Thử Nghiệm Bundle"
FIXTURE = {
    "q_loai_hinh": "Doanh nghiệp tư nhân",   # select: label -> value DNTN
    "q_ten_tieng_viet": ANSWER,
    "q_dia_chi_tru_so": "123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh",
    "q_ho_ten": "nguyễn văn a",
    "q_gioi_tinh": "Nam",
    "q_so_cccd": "79085001234",              # chuỗi Text — giữ số 0 đầu
    "q_ngay_sinh": "05/12/1985",
    "q_cccd_ngay_cap": "02/03/2015",
    "q_von": "5.000.000",
    "q_nganh_ten": "Bán lẻ hàng điện tử",
    "q_nganh_ma": "4774",
    "q_nganh_chinh": "X",
    "q_dien_thoai": "0900000000",
    "q_email": "probe@example.com",
}
BY_TYPE = {"text": "Giá trị thử nghiệm bundle", "tel": "0900000000",
           "email": "probe@example.com", "money": "1.000.000",
           "integer": "10", "date": "05/12/1985", "mark": "X"}
wb = openpyxl.load_workbook(xlsx)
mp, ws = wb[MAP_SHEET], wb["Phieu"]
col = {h: i + 1 for i, h in enumerate(MAP_COLUMNS)}
seen_groups = set()
filled = 0
for r in range(4, mp.max_row + 1):
    qid = str(mp.cell(r, col["question_id"]).value or "")
    typ = str(mp.cell(r, col["type"]).value or "")
    group = str(mp.cell(r, col["row_group"]).value or "")
    when = str(mp.cell(r, col["when"]).value or "")
    cell = mp.cell(r, col["cell"]).value
    if when not in ("", "{}") and '"DNTN"' not in when:
        continue  # chỉ điền nhánh DNTN (import chỉ lấy nhánh khớp)
    val = FIXTURE.get(qid)
    if val is None:
        if group:
            if group in seen_groups:
                continue  # bảng lặp: chỉ điền hàng đầu của mỗi group
            seen_groups.add(group)
        val = BY_TYPE.get(typ)
    if val is None:
        continue  # select/mark lạ không có fixture -> bỏ, required sẽ fail-loud
    ws[cell] = val
    filled += 1
filled_path = OUT / "probe_phieu_filled.xlsx"
wb.save(filled_path)
check("Excel điền đủ form theo __map", filled >= 10, "filled=%d" % filled)

res = import_questionnaire(str(filled_path), q)
val = (res.get("data") or {}).get("dn.ten_tieng_viet") \
    if isinstance(res, dict) else None
check("Excel import round-trip trả đúng giá trị",
      isinstance(res, dict) and res.get("ok") is True and val == ANSWER,
      "value=%r" % (val,))

check("tools/phase5r_expectations.json trong bundle",
      (base / "tools/phase5r_expectations.json").is_file())

if fails:
    print("[probe] SUMMARY: %d FAIL -> %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("[probe] SUMMARY: ALL PASS")
sys.exit(0)
PYEOF

c_step "S-eng: engine probe BÊN TRONG bundle frozen"
PROBE_OUT="$EVIDENCE/engine_probe_out"
rm -rf "$PROBE_OUT"
DKKD_ENGINE_PROBE="$EVIDENCE/dkkd_engine_probe.py" DKKD_PROBE_OUT="$PROBE_OUT" \
    "$BIN" > "$EVIDENCE/macOS_S-eng_console.log" 2>&1
ENG_RC=$?
sed 's/^/    /' "$EVIDENCE/macOS_S-eng_console.log"
auto_result "S-eng" "engine probe trong bundle (exit=$ENG_RC)" "$ENG_RC" \
    "(output: $PROBE_OUT)"

# =============================================== S-path đường dẫn Unicode + space
UNI_DIR="$EVIDENCE/thư mục thử nghiệm ĐKKD có dấu và khoảng trắng"
rm -rf "$UNI_DIR"
mkdir -p "$UNI_DIR"
c_step "S-path: copy .app sang đường dẫn dấu + space: $UNI_DIR"
if ditto "$APP" "$UNI_DIR/DangKyKinhDoanh.app" 2>/dev/null; then
    rm -rf "$PROBE_OUT"
    DKKD_ENGINE_PROBE="$EVIDENCE/dkkd_engine_probe.py" DKKD_PROBE_OUT="$PROBE_OUT" \
        "$UNI_DIR/DangKyKinhDoanh.app/Contents/MacOS/DangKyKinhDoanh" \
        > "$EVIDENCE/macOS_S-path_console.log" 2>&1
    PATH_RC=$?
    tail -3 "$EVIDENCE/macOS_S-path_console.log" | sed 's/^/    /'
    auto_result "S-path" "engine probe từ đường dẫn Unicode+space (exit=$PATH_RC)" "$PATH_RC" ""

    # S-path GUI: launch nhanh từ đường dẫn lạ, sống 12s rồi kill.
    GUI_BIN="$UNI_DIR/DangKyKinhDoanh.app/Contents/MacOS/DangKyKinhDoanh"
    "$GUI_BIN" > "$EVIDENCE/macOS_S-path_gui_out.log" 2>&1 &
    GUI_PID=$!
    sleep 12
    if kill -0 "$GUI_PID" 2>/dev/null; then
        auto_result "S-path" "GUI launch từ đường dẫn Unicode+space — sống 12s" 0 ""
        kill "$GUI_PID" 2>/dev/null; sleep 2
        kill -9 "$GUI_PID" 2>/dev/null
        log_step "S-path" "GUI (đường dẫn lạ) đã kill sau kiểm tra."
    else
        wait "$GUI_PID" 2>/dev/null
        auto_result "S-path" "GUI launch từ đường dẫn Unicode+space — sống 12s" 1 "(exit=$?)"
    fi
    # dọn copy thử nghiệm (giữ evidence console log)
    rm -rf "$UNI_DIR"
else
    auto_result "S-path" "copy .app sang đường dẫn Unicode+space" 1 "(ditto thất bại)"
fi

# =============================================== S-restart (assets bền qua restart)
c_step "S-restart: launch GUI lần 2 (assets bền qua restart)"
if launch_gui "S-restart"; then
    auto_result "S-restart" "GUI lần 2 sống sau 12s" 0 "(PID $GUI_PID)"
    ask_verdict "S-restart" "Lần 2: UI vẫn render đủ như lần 1?" \
        "Danh sách thủ tục hiển thị, mở 1 thủ tục và xem 1 form bình thường"
    kill "$GUI_PID" 2>/dev/null; sleep 3
    kill -9 "$GUI_PID" 2>/dev/null
    log_step "S-restart" "GUI lần 2 đã kill sau kiểm tra."
else
    auto_result "S-restart" "GUI lần 2 sống sau 12s" 1 ""
fi

# =============================================== S-privacy bundle (AUTO)
c_step "S-privacy: bundle không chứa profiles/PII/evidence"
PRIV_BAD=""
for p in profiles generated_ho_so 99_muc_luc docs app_tk evidence; do
    [ -e "$APP/Contents/Frameworks/$p" ] && PRIV_BAD="$PRIV_BAD $p"
done
# draft/xlsx lạ trong bundle (profile thật thường là .json draft / .xlsx)
STRAY=$(find "$APP" -name "*_draft*.json" -o -name "*.xlsx" 2>/dev/null | head -5)
[ -z "$STRAY" ] || PRIV_BAD="$PRIV_BAD stray-draft/xlsx"
if [ -z "$PRIV_BAD" ]; then
    auto_result "S-privacy" "bundle sạch (không profiles/generated_ho_so/docs/legacy/evidence/draft)" 0 ""
else
    auto_result "S-privacy" "bundle sạch" 1 "(thấy:$PRIV_BAD)"
fi

# =============================================== S-viewer: module trong PYZ (AUTO)
c_step "S-viewer: kiểm tools.* trong PYZ bằng pyi-archive_viewer"
VIEWER_OUT="$EVIDENCE/macOS_pyz_inventory.txt"
if "$PYTHON" -m PyInstaller.utils.cliutils.archive_viewer -r -l "$BIN" > "$VIEWER_OUT" 2>&1 \
    || { command -v pyi-archive_viewer >/dev/null 2>&1 && pyi-archive_viewer -r -l "$BIN" > "$VIEWER_OUT" 2>&1; }; then
    MISS=""
    # viewer in tên module dạng dotted ('tools.docx_render')
    for m in "tools.docx_render" "tools.excel_export" "tools.excel_import" "tools.questionnaire.schema" "tools.layout_roles" "webview.platforms.cocoa" "tkinter.filedialog"; do
        grep -q "'$m'" "$VIEWER_OUT" || MISS="$MISS $m"
    done
    [ -z "$MISS" ] \
        && auto_result "S-viewer" "module engine + backend trong PYZ" 0 "" \
        || auto_result "S-viewer" "module engine + backend trong PYZ" 1 "(thiếu:$MISS)"
else
    log_step "S-viewer" "NOT RUN: không chạy được pyi-archive_viewer (S-eng đã chứng minh import thật)."
fi

# ==================================================================== S8
echo ""
read -r -p "S8 clean-machine (Máy KHÁC không có Python, mở đúng .app)? Đã chuẩn bị? [y/N]: " s8 </dev/tty || s8="N"
if [ "${s8:-N}" = "Y" ]; then
    log_step "8" "Chạy tay trên máy sạch: copy dist/DangKyKinhDoanh.app sang máy không có Python, mở bằng right-click > Open (Gatekeeper), lặp S2–S6."
    ask_verdict "8" "Clean-machine: .app mở được KHÔNG cần Python?" \
        "Copy .app sang máy sạch (không Python, không LibreOffice nếu muốn thửghiem offline tuyệt đối)" \
        "Right-click > Open lần đầu (Gatekeeper với app chưa ký)" \
        "Lặp nhanh S2–S6; ghi spctl/Gatekeeper verdict + SHA-256 vào evidence"
else
    log_step "8" "VERDICT: NOT RUN (chưa có máy sạch — cần máy Mac khác không cài Python)."
fi

# =================================================================== tổng kết
echo ""
echo "==== Hoàn tất smoke session $STAMP ===="
echo "Log: $EVIDENCE/macOS_S*.log — verdict MANUAL do NGƯỜI CHẠY nhập nằm trong log."
echo "BUỘC TIẾP: điền bảng evidence trong tools/macos_handoff/README.md + append docs/execution_ledger.md."
echo "FAIL ở bước nào -> dừng ở đó, ghi nguyên nhân, KHÔNG PASS ước lượng."
if [ "$AUTO_FAIL" -gt 0 ]; then
    c_bad "$AUTO_FAIL kiểm AUTO FAIL — xem log tương ứng."
    exit 1
fi
c_ok "Toàn bộ kiểm AUTO PASS (các bước MANUAL chờ verdict người chạy)."
exit 0
