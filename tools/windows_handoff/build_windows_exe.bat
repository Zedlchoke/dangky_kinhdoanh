@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows_exe.ps1"
set "BUILD_RC=%ERRORLEVEL%"
echo.
if not "%BUILD_RC%"=="0" echo BUILD FAILED (exit %BUILD_RC%)
pause
exit /b %BUILD_RC%
