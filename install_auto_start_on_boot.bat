@echo off
setlocal
cd /d "%~dp0"
title Install Auto-Start on Boot - Gadget Store System

echo ====================================================================
echo    INSTALL AUTO-START ON BOOT (ZERO DOCKER DESKTOP REQUIRED)
echo ====================================================================
echo.

set SCRIPT_DIR=%~dp0
set VBS_TARGET=%SCRIPT_DIR%start_background_silent.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\GadgetStoreServer.lnk

echo [1/2] Creating Windows Startup shortcut...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_TARGET%\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'Gadget Store Server Silent Background Launcher'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Startup shortcut created at:
    echo           "%SHORTCUT_PATH%"
    echo.
    echo The server will now automatically start silently in the background
    echo on port 8086 whenever this computer turns on!
) else (
    echo [ERROR] Failed to create shortcut.
    pause
    exit /b 1
)

echo.
echo [2/2] Launching server in the background right now...
wscript.exe "%VBS_TARGET%"

echo.
echo ====================================================================
echo [ALL SET!] Server is now running silently in background!
echo Access the system at:
echo    http://127.0.0.1:8086
echo ====================================================================
echo.
pause
