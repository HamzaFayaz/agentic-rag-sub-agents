@echo off
REM Run this file — do NOT run start-dev.ps1 directly from CMD (it may open in Notepad).
cd /d "%~dp0"
echo.
echo Starting backend and frontend...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
if errorlevel 1 (
    echo.
    echo Startup failed. See messages above.
    pause
    exit /b 1
)
echo.
pause
