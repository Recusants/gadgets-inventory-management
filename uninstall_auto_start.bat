@echo off
setlocal
title Uninstall Auto-Start - Gadget Store System

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\GadgetStoreServer.lnk

echo Removing auto-start shortcut...
if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [SUCCESS] Auto-start on boot has been removed.
) else (
    echo [INFO] Shortcut was not present in Startup folder.
)

pause
