#Requires -Version 5.1
<#
.SYNOPSIS
    Windows smoke S1-S7 (+S6b Excel, +S8 tuy y) cho "Tro ly ho so DKKD" theo
    docs/platform_smoke_checklist.md — F6/O6 handoff.

.DESCRIPTION
    Chay TUAN TU S1->S7 (S6b phieu Excel case-level sau S6; S8 chi khi co
    .exe, tham -UseExe):
      S1 khoi chay app_web/main.py qua pywebview (python -X utf8)
      S2 UI render              (thao tac UI - MANUAL)
      S3 nhap du lieu tung kind (thao tac UI - MANUAL)
      S4 dialog mo ho so .json  (thao tac UI - MANUAL)
      S5 dialog luu ho so       (thao tac UI - MANUAL)
      S6 xuat DOCX/ZIP (blocked + sach) + kiem tra generated_ho_so
      S7 offline: tat mang, lap lai S2-S6
    Moi buoc ghi log vao <RepoRoot>\evidence\Windows_S<N>.log (append, co
    header thoi diem chay -> chay lai an toan / idempotent).

    QUAN TRONG: script KHONG TU DANH PASS cho buoc nao can nhin man hinh.
    No chi in "[MANUAL] kiem tra ... roi ghi PASS/FAIL vao evidence" va ghi
    nhan ket qua ban go vao. Chi buoc MAY DO duoc tu ghi (process con song,
    exit code, file xuat hien) - va cung KHONG the thay viec nguoi chay
    nhin man hinh.

    KHONG TAI XUONG GI: script chi KIEM TRA deps da cai (python, pywebview,
    WebView2 Runtime, soffice). Neu thieu -> huong dan cai roi DUNG (giu
    offline S7: sau khi deps cai, chay script khong can mang).

.PARAMETER Python
    Duong dan/ten python (mac dinh "python"). Vi du: -Python "py -3.11"
.PARAMETER RepoRoot
    Root repo (mac dinh: 2 cap tren thu muc chua script nay).
.PARAMETER EvidenceDir
    Thu muc evidence (mac dinh: <RepoRoot>\evidence).
.PARAMETER UseExe
    S8: chay buoc S8 bang dist\DangKyKinhDoanh.exe (hoac -ExePath chi dinh).
.PARAMETER ExePath
    Duong dan .exe cho S8 (mac dinh <RepoRoot>\dist\DangKyKinhDoanh.exe).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\windows_handoff\run_smoke_s1_s8.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\windows_handoff\run_smoke_s1_s8.ps1 -UseExe
#>
param(
    [string] $Python = "python",
    [string] $RepoRoot = "",
    [string] $EvidenceDir = "",
    [switch] $UseExe,
    [string] $ExePath = ""
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------- paths
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    # tools/windows_handoff/ -> root repo 2 cap tren
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
if ([string]::IsNullOrWhiteSpace($EvidenceDir)) {
    $EvidenceDir = Join-Path $RepoRoot "evidence"
}
if (-not (Test-Path -LiteralPath $EvidenceDir)) {
    New-Item -ItemType Directory -Path $EvidenceDir | Out-Null
}
$ImgDir = Join-Path $EvidenceDir "img"
if (-not (Test-Path -LiteralPath $ImgDir)) {
    New-Item -ItemType Directory -Path $ImgDir | Out-Null
}
$MainPy = Join-Path $RepoRoot "app_web\main.py"
if (-not (Test-Path -LiteralPath $MainPy)) {
    Write-Host "KHONG tim thay $MainPy - chay sai RepoRoot?" -ForegroundColor Red
    exit 2
}

$RunStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$RunTag = Get-Date -Format "yyyyMMdd_HHmmss"
$Global:AppProc = $null
$Global:AppOutLog = ""
$Global:AppErrLog = ""
$Script:StartedAt = Get-Date
$failedHard = $false

# ---------------------------------------------------------------- helpers
function Write-StepLog {
    param([string] $Step, [string[]] $Lines)
    $path = Join-Path $EvidenceDir ("Windows_{0}.log" -f $Step)
    $header = @("=== $Step | run $RunStamp | user=$env:USERNAME | host=$env:COMPUTERNAME ===")
    Add-Content -LiteralPath $path -Value ($header + $Lines) -Encoding UTF8
    Write-Host ("  [log] " + $path) -ForegroundColor DarkGray
}

function Stop-Session {
    param([string] $Reason)
    Write-StepLog "0_PREFLIGHT" @("SESSION STOPPED: $Reason")
    Write-Host "DUNG session theo quy tac checklist (FAIL o buoc nao dung o do): $Reason" -ForegroundColor Red
    exit 1
}

function Confirm-ContinueOnFail {
    param([string] $Step)
    Write-Host "  S$Step = FAIL. Checklist: 'dung o do'. Tiep tuc cac buoc sau?" -ForegroundColor Red
    $ans = (Read-Host "  Tiep tuc? [y/N]").Trim().ToUpper()
    if ($ans -ne "Y") { Stop-Session "S$Step FAIL - nguoi chay chon dung." }
}

function Get-ManualVerdict {
    param([string] $Step, [string] $Title, [string[]] $Checklist)
    Write-Host ""
    Write-Host "[MANUAL] kiem tra (S$Step): $Title" -ForegroundColor Yellow
    foreach ($item in $Checklist) {
        Write-Host ("    - " + $item) -ForegroundColor Yellow
    }
    Write-Host "  Chup man hinh luu vao: $ImgDir (ten goi y: Windows_S${Step}_*.png)" -ForegroundColor Yellow
    Write-Host "  ROI ghi PASS/FAIL vao evidence (nhap P=PASS / F=FAIL / S=skip-not-tested):" -ForegroundColor Yellow
    $verdict = ""
    while ($verdict -notin @("P", "F", "S")) {
        $verdict = (Read-Host "  S$Step verdict [P/F/S]").Trim().ToUpper()
    }
    $word = @{ "P" = "PASS"; "F" = "FAIL"; "S" = "NOT RUN (skip)" }[$verdict]
    Write-StepLog $Step @("VERDICT (nguoi chay nhin man hinh): $word")
    return $verdict
}

function Wait-AppAlive {
    param([int] $Seconds = 20)
    for ($i = 0; $i -lt $Seconds; $i++) {
        Start-Sleep -Seconds 1
        if ($Global:AppProc.HasExited) { return $false }
    }
    return -not $Global:AppProc.HasExited
}

function Stop-AppAndLogExit {
    param([string] $Step)
    if ($null -eq $Global:AppProc) { return }
    if (-not $Global:AppProc.HasExited) {
        Write-Host ""
        Write-Host "[MANUAL] Dong cua so ung dung (cai X) de script tiep tuc..." -ForegroundColor Yellow
        # Cho toi da 120s roi moi ep kill (khong bao gio treo mai)
        if (-not $Global:AppProc.WaitForExit(120000)) {
            Write-Host "  App khong tu dong sau 120s - ep ket thuc." -ForegroundColor Red
            $Global:AppProc.Kill()
        }
    }
    $Global:AppProc.WaitForExit()
    $code = $Global:AppProc.ExitCode
    $lines = @("App da dong. ExitCode = $code (ky vong 0).")
    # Gom toan bo console stdout/stderr cua phien vao log buoc roi xoa file tam
    foreach ($f in @($Global:AppOutLog, $Global:AppErrLog)) {
        if ($f -and (Test-Path -LiteralPath $f)) {
            $content = Get-Content -LiteralPath $f -ErrorAction SilentlyContinue
            if ($content) { $lines += "--- console ---"; $lines += $content }
            Remove-Item -LiteralPath $f -ErrorAction SilentlyContinue
        }
    }
    Write-StepLog $Step $lines
    $Global:AppProc = $null
}

function Start-App {
    param([string] $Step, [string] $TargetPath, [switch] $IsExe)
    $Global:AppOutLog = Join-Path $EvidenceDir ("Windows_{0}_console_out.tmp.log" -f $Step)
    $Global:AppErrLog = Join-Path $EvidenceDir ("Windows_{0}_console_err.tmp.log" -f $Step)
    Remove-Item -LiteralPath $Global:AppOutLog, $Global:AppErrLog -ErrorAction SilentlyContinue

    if ($IsExe) {
        Write-Host "[S$Step] launch .exe: $TargetPath" -ForegroundColor Cyan
        $Global:AppProc = Start-Process -FilePath $TargetPath `
            -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $Global:AppOutLog `
            -RedirectStandardError $Global:AppErrLog `
            -PassThru
    }
    else {
        Write-Host "[S$Step] launch: $Python -X utf8 app_web\main.py" -ForegroundColor Cyan
        # -X utf8 bat UTF-8 mode (quy uoc repo); quote path co space/dauViet
        $argStr = '-X utf8 "{0}"' -f $MainPy
        $Global:AppProc = Start-Process -FilePath $Python `
            -ArgumentList $argStr `
            -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $Global:AppOutLog `
            -RedirectStandardError $Global:AppErrLog `
            -PassThru
    }

    $alive = Wait-AppAlive -Seconds 20
    if (-not $alive) {
        $code = $Global:AppProc.ExitCode
        Write-Host "  FAIL: app thoat som (ExitCode=$code) trong 20s dau." -ForegroundColor Red
        $lines = @("FAIL: app thoat som trong 20s dau. ExitCode=$code")
        foreach ($f in @($Global:AppOutLog, $Global:AppErrLog)) {
            if (Test-Path -LiteralPath $f) {
                $content = Get-Content -LiteralPath $f -ErrorAction SilentlyContinue
                if ($content) { $lines += "--- console ---"; $lines += $content }
            }
        }
        Write-StepLog $Step $lines
        $Global:AppProc = $null
        return $false
    }

    # Evidence MAY DO 20s dau: console co traceback khong (ghi vao log buoc;
    # toan bo phien se duoc gom lai khi dong app trong Stop-AppAndLogExit).
    $early = @()
    foreach ($f in @($Global:AppOutLog, $Global:AppErrLog)) {
        if (Test-Path -LiteralPath $f) {
            $content = Get-Content -LiteralPath $f -ErrorAction SilentlyContinue
            if ($content) { $early += $content }
        }
    }
    if ($early.Count -gt 0) {
        Write-StepLog $Step (@("App song sau 20s. Console 20s dau:") + $early)
    } else {
        Write-StepLog $Step @("App song sau 20s. Console sach (khong output).")
    }
    Write-Host "  App dang chay (PID $($Global:AppProc.Id))." -ForegroundColor Green
    return $true
}

# ============================================================== PRE-FLIGHT
Write-Host ""
Write-Host "==== Windows smoke S1-S8 handoff | run $RunStamp ====" -ForegroundColor Cyan
Write-Host "RepoRoot    : $RepoRoot"
Write-Host "EvidenceDir : $EvidenceDir"
Write-Host "Python      : $Python"
Write-Host ""

$preflight = @()

# Python ton tai + version
try {
    $pyVer = & $Python -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    $preflight += "python version: $pyVer"
    Write-Host "python      : OK ($pyVer)" -ForegroundColor Green
} catch {
    Write-Host "python      : KHONG CHAY DUOC. Cai Python 3.11+ (docs/windows_handoff.md buoc 2) roi chay lai." -ForegroundColor Red
    exit 2
}

# pywebview import duoc (KHONG pip install tu script - giu offline S7)
$wv = & $Python -c "import webview; print(getattr(webview, '__version__', 'webview-ok'))" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "pywebview   : THIEU. Chay: $Python -m pip install -r requirements-dev.txt (docs/windows_handoff.md buoc 3) roi chay lai." -ForegroundColor Red
    exit 2
}
$preflight += "pywebview: $wv"
Write-Host "pywebview   : OK ($wv)" -ForegroundColor Green

# WebView2 Runtime (Evergreen) - registry check, chi LOG khong chan.
$wv2Keys = @(
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
)
$wv2ver = ""
foreach ($k in $wv2Keys) {
    $p = Get-ItemProperty -LiteralPath $k -ErrorAction SilentlyContinue
    if ($p -and $p.pv) { $wv2ver = $p.pv; break }
}
if ($wv2ver) {
    $preflight += "WebView2 Runtime: $wv2ver"
    Write-Host "WebView2    : OK ($wv2ver)" -ForegroundColor Green
} else {
    $preflight += "WebView2 Runtime: KHONG THAY trong registry - can xac nhan thu cong (Control Panel > Programs)"
    Write-Host "WebView2    : khong thay trong registry - kiem tra thu cong 'Microsoft Edge WebView2 Runtime' trong Programs." -ForegroundColor Yellow
}

# LibreOffice (S6 PDF + normalize Word-compat) - chi LOG khong chan.
$soffice = Get-Command soffice -ErrorAction SilentlyContinue
if ($soffice) {
    $preflight += "soffice: " + $soffice.Source
    Write-Host "LibreOffice : OK ($($soffice.Source))" -ForegroundColor Green
} else {
    $preflight += "soffice: khong thay trong PATH - S6 chi xuat duoc .docx, KHONG co normalize/PDF (ghi vao evidence)"
    Write-Host "LibreOffice : khong thay 'soffice' trong PATH - S6 se khong co PDF/normalize." -ForegroundColor Yellow
}

# User admin hay khong - chi LOG khong chan (PLAN F6.4: phai co kich ban
# user KHONG admin; neu may nay la admin, ghi ro vao evidence va lap lai
# toan bo launch + build + exe tren user thuong).
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    $preflight += "user: ADMIN - PLAN F6.4 yeu cau kich ban user KHONG admin: lap lai quy tren user thuong"
    Write-Host "User        : ADMIN - nho lap lai tren user KHONG admin (PLAN F6.4)." -ForegroundColor Yellow
} else {
    $preflight += "user: khong phai admin (dung kich ban PLAN F6.4)"
    Write-Host "User        : khong phai admin - dung kich ban yeu cau." -ForegroundColor Green
}

Write-StepLog "0_PREFLIGHT" $preflight

# ==================================================================== S1
if (-not (Start-App -Step "1" -TargetPath "")) { exit 1 }
$v1 = Get-ManualVerdict "1" "Cua so desktop da mo?" @(
    "Cua so 'Tro ly ho so DKKD' hien ra (khong trang trang, khong traceback trong console)",
    "Ghi lai version Windows + version WebView2 Runtime vao evidence" )
if ($v1 -eq "F") { Confirm-ContinueOnFail "1" }

# ==================================================================== S2
$v2 = Get-ManualVerdict "2" "UI render danh sach thu tuc" @(
    "Danh sach 28 thu tuc hien duoc, khong trang trang / layout vo",
    "Mo DevTools (neu duoc) khong co JS error nghiem trong" )
if ($v2 -eq "F") { Confirm-ContinueOnFail "2" }

# ==================================================================== S3
$v3 = Get-ManualVerdict "3" "Chon thu tuc + nhap tung kind du lieu" @(
    "text, money, percent, checkbox, radio",
    "vsic (tim nganh), editable-grid (them/xoa dong)",
    "fixed-matrix, nested-grid, output-table",
    "Chup screenshot tung kind -> evidence\img\Windows_S3_*.png" )
if ($v3 -eq "F") { Confirm-ContinueOnFail "3" }

# ==================================================================== S4
$v4 = Get-ManualVerdict "4" "Dialog MO ho so .json (tkinter)" @(
    "Nut 'Mo ho so .json' -> dialog tkinter mo duoc",
    "Chon file .json hop le -> du lieu nap dung vao app" )
if ($v4 -eq "F") { Confirm-ContinueOnFail "4" }

# ==================================================================== S5
$v5 = Get-ManualVerdict "5" "Dialog LUU ho so (draft)" @(
    "Luu draft .json thanh cong",
    "Mo lai bang S4 -> dung du lieu vua luu" )
if ($v5 -eq "F") { Confirm-ContinueOnFail "5" }

# ==================================================================== S6
$v6 = Get-ManualVerdict "6" "Xuat DOCX/ZIP (blocked truoc, sach sau)" @(
    "1) Ho so CO blocking error -> export PHAI bi chan, khong sinh file",
    "2) Ho so sach -> export OK, file nam trong generated_ho_so\, ZIP mo duoc",
    "3) Mo file .docx bang Word that (khong phai preview) - ghi version Word",
    "Neu co LibreOffice: thu ca 3 dinh dang docx/pdf/both" )

# Evidence MAY DO cho S6: thu muc moi trong generated_ho_so ke tu luc bat dau
$genDir = Join-Path $RepoRoot "generated_ho_so"
$s6auto = @()
if (Test-Path -LiteralPath $genDir) {
    $newDirs = Get-ChildItem -LiteralPath $genDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.CreationTime -ge $Script:StartedAt }
    foreach ($d in $newDirs) {
        $files = Get-ChildItem -LiteralPath $d.FullName -Recurse -File -ErrorAction SilentlyContinue
        $s6auto += ("{0} : {1} file ({2} bytes)" -f $d.Name, $files.Count,
                    (($files | Measure-Object Length -Sum).Sum))
    }
}
if ($s6auto.Count -gt 0) {
    Write-StepLog "6" (@("Evidence MAY DO - thu muc export moi ke tu luc chay script:") + $s6auto)
} else {
    Write-StepLog "6" @("Evidence MAY DO: KHONG thay thu muc moi trong generated_ho_so ke tu luc chay script (neu da export, kiem tra lai dia chi repo).")
}
if ($v6 -eq "F") { Confirm-ContinueOnFail "6" }

# ==================================================================== S6b
# Excel case-level (PLAN F6.4 + wave X5): UI co nut "Xuat phieu Excel cho
# khach" / "Nap phieu Excel" (app_web/ui/index.html btn-export-excel /
# btn-import-excel). Thu tuc co questionnaire: PLI_M12, PLI_M27, PLI_M72,
# PLII_M01..M04 (app/data/questionnaire/, 7 file).
$v6b = Get-ManualVerdict "6b" "Phieu Excel cho khach (xuat -> dien -> nap lai)" @(
    "Chon thu tuc CO questionnaire (vd PLI_M72) -> nut 'Xuat phieu Excel cho khach' -> dialog tkinter -> file .xlsx",
    "Mo file bang Excel Desktop THAT (ghi version) hoac LibreOffice Calc; khoa o vang nhap duoc, o xam lock",
    "Dien du cau bat buoc, luu, quay lai app -> 'Nap phieu Excel' -> du lieu tai tao dung (select/chk/ngay/tien)",
    "Xoa 1 cau bat buoc -> nap lai -> app bao THIEU cu the cau nao (fail-loud MISSING_REQUIRED), draft cu giu nguyen",
    "File khac case/sua sheet __map -> nap lai PHAI bi tu choi (checksum/contract)" )
if ($v6b -eq "F") { Confirm-ContinueOnFail "6b" }
# Evidence MAY DO cho S6b: file .xlsx nguoi chay vua luu (ho vi tri khac)
$xlsxHint = @("Nguoi chay tu ghi vao evidence: duong dan file .xlsx da xuat/nap, app+version da mo (Excel Desktop / LibreOffice Calc)")
Write-StepLog "6b" $xlsxHint

Stop-AppAndLogExit -Step "6"

# ==================================================================== S7
Write-Host ""
Write-Host "S7 OFFLINE: rut day mang / tat wifi / disable adapter truoc khi tiep tuc." -ForegroundColor Yellow
$v7net = (Read-Host "  Da NGAT mang chua? [Y/N]").Trim().ToUpper()
Write-StepLog "7" @("Nguoi chay xac nhan da ngat mang: $v7net")
if ($v7net -eq "Y") {
    if (Start-App -Step "7" -TargetPath "") {
        $v7 = Get-ManualVerdict "7" "Offline: lap lai nhanh S2-S6" @(
            "UI van render (S2), nhap du lieu van OK (S3)",
            "Mo/luu draft van OK (S4-S5)",
            "Export DOCX/ZIP van OK (S6)",
            "Xuat phiếu Excel van OK (S6b - app khong goi mang nao)",
            "App KHONG can mang nao (hoat dong nhu khi online)" )
        if ($v7 -eq "F") { Confirm-ContinueOnFail "7" }
        Stop-AppAndLogExit -Step "7"
    } else {
        $failedHard = $true
    }
    Write-Host ""
    Read-Host "  Bat lai mang roi nhan Enter"
} else {
    Write-StepLog "7" @("VERDICT: NOT RUN (nguoi chay khong ngat mang).")
}

# ==================================================================== S8
if ($UseExe) {
    if ([string]::IsNullOrWhiteSpace($ExePath)) {
        $ExePath = Join-Path $RepoRoot "dist\DangKyKinhDoanh.exe"
    }
    if (Test-Path -LiteralPath $ExePath) {
        $exeHash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
        Write-StepLog "8" @("Exe: $ExePath", "SHA-256: $exeHash")
        if (Start-App -Step "8" -TargetPath $ExePath -IsExe) {
            $v8 = Get-ManualVerdict "8" "Clean-machine .exe: lap lai S2-S6" @(
                "Exe mo duoc ma KHONG can Python trong may",
                "Lap lai nhanh S2-S6 nhu tren (gom S6b phieu Excel)",
                "Neu dat .exe trong duong dan co dau tieng Viet/space: lap lai S1-S6b tai cho (PLAN F6.4)",
                "Export trong .exe: MO thu muc export VA CHEP file ra ngoai ngay (thu muc extract tam bi xoa khi dong app; launcher co rescue-copy sang Documents\DangKyKinhDoanh\generated_ho_so - kiem tra cho nay neu quen)" )
            if ($v8 -eq "F") { Confirm-ContinueOnFail "8" }
            Stop-AppAndLogExit -Step "8"
        }
    } else {
        Write-Host "S8: KHONG thay $ExePath - build .exe truoc (docs/windows_handoff.md buoc 4)." -ForegroundColor Yellow
        Write-StepLog "8" @("NOT RUN: khong thay .exe tai $ExePath")
    }
} else {
    Write-StepLog "8" @("NOT RUN: chay lai voi -UseExe sau khi build .exe.")
}

# =================================================================== wrap
Write-Host ""
Write-Host "==== Hoan tat smoke session $RunTag ====" -ForegroundColor Cyan
Write-Host "Verdict do nguoi chay nhap tay nam trong evidence\Windows_S*.log."
Write-Host "BUOC TIEP THEO (docs/windows_handoff.md buoc 5):"
Write-Host "  1. Kiem tra lai tung log S1-S8 trong evidence\."
Write-Host "  2. Dien bang evidence trong tools\windows_handoff\README.md."
Write-Host "  3. Append ket qua vao docs\execution_ledger.md (PASS/FAIL/NOT RUN + nguoi chay + ngay)."
Write-Host "  4. FAIL o buoc nao -> dung o do, ghi nguyen nhan, KHONG danh PASS uoc luong."
if ($failedHard) {
    Write-Host "Co buoc app thoat som (FAIL may do) - xem log." -ForegroundColor Red
    exit 1
}
exit 0
