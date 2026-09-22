@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Stop Gadget Store Server

echo ======================================================
echo    STOPPING GADGET STORE SERVER (PORT 8086)
echo ======================================================
echo.

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8086" ^| findstr "LISTENING"') do (
    set PID=%%a
    if not "!PID!"=="" (
        echo Terminating process PID !PID! on port 8086...
        taskkill /F /PID !PID! >nul 2>&1
        set FOUND=1
    )
)

if "!FOUND!"=="1" (
    echo [SUCCESS] Server on port 8086 stopped.
) else (
    echo [INFO] No active server process found listening on port 8086.
)

echo.
pause
