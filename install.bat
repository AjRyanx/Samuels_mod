@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo  DYNAMIC KIT ^& SPONSOR MOD FOR PES 2021 / SP FOOTBALL LIFE 2027
echo  Automated 1-Click Installer
echo ================================================================================
echo.

where powershell >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PowerShell is not found on your system!
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installer encountered an error (exit code %ERRORLEVEL%).
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
