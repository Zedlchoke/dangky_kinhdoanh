[CmdletBinding()]
param()

# One-click Windows release build.
# Xóa và tạo lại output/work directory mỗi lần chạy để không tái sử dụng
# artifact cũ. Chỉ cho phép xóa đúng hai thư mục đã định danh dưới repo root.
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
$outDir = Join-Path $repoRoot "build_windows_exe"
$workDir = Join-Path $repoRoot "build_windows_work"
$specPath = Join-Path $scriptDir "dangky_kinhdoanh.spec"

function Remove-ExactDirectory([string] $expectedPath) {
    if (-not (Test-Path -LiteralPath $expectedPath)) { return }
    $resolved = (Resolve-Path -LiteralPath $expectedPath).Path
    if ($resolved -ne $expectedPath) {
        throw "Refuse to delete unexpected path: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

Remove-ExactDirectory $outDir
Remove-ExactDirectory $workDir
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { throw "Không tìm thấy python.exe trong PATH." }
if (-not (Test-Path -LiteralPath $specPath)) { throw "Không tìm thấy spec: $specPath" }

Write-Host "Building from $repoRoot"
& $python.Source -m PyInstaller --clean --noconfirm `
    --distpath $outDir --workpath $workDir $specPath
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$exePath = Join-Path $outDir "DangKyKinhDoanh.exe"
if (-not (Test-Path -LiteralPath $exePath)) { throw "Không tạo được $exePath" }

$commit = (& git -C $repoRoot rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = "unknown" }
$buildDate = Get-Date -Format "dd/MM/yyyy HH:mm:ss"
$readmePath = Join-Path $outDir "README.txt"
$hashPath = Join-Path $outDir "SHA256SUMS.txt"
@"
TRỢ LÝ HỒ SƠ ĐĂNG KÝ KINH DOANH — WINDOWS

Tệp chạy: DangKyKinhDoanh.exe
Commit: $commit
Build: $buildDate

Cách dùng: giải nén ZIP, giữ nguyên các tệp trong cùng thư mục rồi chạy
DangKyKinhDoanh.exe.

Yêu cầu máy khách: Windows 10/11 64-bit và Microsoft Edge WebView2 Runtime.
LibreOffice 26.8+ cần thiết nếu muốn xuất PDF/chuẩn hóa DOCX tự động.
Không cần cài Python.

Bản build chưa ký Authenticode nên SmartScreen có thể cảnh báo. Kiểm tra
SHA-256 trong SHA256SUMS.txt trước khi chạy.
"@ | Set-Content -LiteralPath $readmePath -Encoding UTF8

$hash = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  DangKyKinhDoanh.exe" | Set-Content -LiteralPath $hashPath -Encoding ASCII

$zipPath = Join-Path $outDir "DangKyKinhDoanh_windows_latest.zip"
Compress-Archive -LiteralPath @($exePath, $readmePath, $hashPath) `
    -DestinationPath $zipPath -Force
if (-not (Test-Path -LiteralPath $zipPath)) { throw "Không tạo được $zipPath" }

# Work directory chỉ là cache build, không cần gửi sang máy khách.
Remove-ExactDirectory $workDir

Write-Host ""
Write-Host "BUILD OK" -ForegroundColor Green
Write-Host "EXE : $exePath"
Write-Host "ZIP : $zipPath"
Write-Host "SHA : $hash"
Write-Host ""
Start-Process explorer.exe -ArgumentList $outDir
