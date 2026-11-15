@echo off
TITLE Gadget Store System - Create Desktop Shortcuts
setlocal EnableDelayedExpansion

echo ============================================================
echo   GADGET STORE SYSTEM - DESKTOP SHORTCUT SETUP
echo ============================================================
echo.

set "INSTALL_DIR=%~dp0"
if "%INSTALL_DIR:~-1%"=="\" set "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

REM Detect port from .env
set "HTTP_PORT=8086"
if exist "%INSTALL_DIR%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%INSTALL_DIR%\.env") do (
        if /i "%%A"=="HTTP_PORT" set "HTTP_PORT=%%B"
    )
)
set "HTTP_PORT=!HTTP_PORT: =!"
set "HTTP_PORT=!HTTP_PORT:"=!"
if "!HTTP_PORT!"=="" set "HTTP_PORT=8086"

REM Detect local LAN IP
echo Detecting server network address...
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback|Docker' -and $_.IPAddress -notmatch '^^169\.254\.' } | Select-Object -First 1).IPAddress"') do set "SERVER_IP=%%a"
if "%SERVER_IP%"=="" set "SERVER_IP=127.0.0.1"

echo Server URL: http://%SERVER_IP%:!HTTP_PORT!
echo.

REM 1. Create Browser Shortcut (.url) on Desktop
echo [1/4] Creating Desktop Browser Shortcut: "Gadget Store System.url"...
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "URL_FILE=%DESKTOP_DIR%\Gadget Store System.url"

(
echo [InternetShortcut]
echo URL=http://%SERVER_IP%:!HTTP_PORT!
echo IconIndex=0
echo IconFile=%SystemRoot%\System32\shell32.dll
) > "%URL_FILE%"

if exist "%URL_FILE%" (
    echo [OK] Created desktop browser shortcut: "%URL_FILE%"
) else (
    echo [WARNING] Could not create shortcut directly on %DESKTOP_DIR%
)
echo.

REM 2. Create Desktop Launcher (.lnk)
echo [2/4] Creating Desktop Application Launcher: "Launch Gadget Store.lnk"...
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%DESKTOP_DIR%\Launch Gadget Store.lnk'); " ^
    "$s.TargetPath = '%INSTALL_DIR%\update.bat'; " ^
    "$s.WorkingDirectory = '%INSTALL_DIR%'; " ^
    "$s.Description = 'Launch / Update Gadget Store Server'; " ^
    "$s.Save()"

if exist "%DESKTOP_DIR%\Launch Gadget Store.lnk" (
    echo [OK] Created desktop launcher shortcut.
)
echo.

REM 3. Create Desktop Updater Shortcut (.lnk)
echo [3/4] Creating Desktop Update Shortcut: "Update Gadget Store.lnk"...
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%DESKTOP_DIR%\Update Gadget Store.lnk'); " ^
    "$s.TargetPath = '%INSTALL_DIR%\update.bat'; " ^
    "$s.WorkingDirectory = '%INSTALL_DIR%'; " ^
    "$s.Description = 'Update Gadget Store System to Latest Release'; " ^
    "$s.IconLocation = '%SystemRoot%\System32\shell32.dll,238'; " ^
    "$s.Save()"

if exist "%DESKTOP_DIR%\Update Gadget Store.lnk" (
    echo [OK] Created desktop update shortcut.
)
echo.

REM 4. Silent Background Docker Startup Prompt
echo [4/4] Setting up Silent Background Docker startup on logon...
echo (Runs Docker minimized in the system tray so the main window NEVER pops up on boot)
set /p "ENABLE_DOCKER_SILENT=Would you like Docker to start completely in the background on boot? (Y/N) [Y]: "
if "!ENABLE_DOCKER_SILENT!"=="" set "ENABLE_DOCKER_SILENT=Y"

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if /i "!ENABLE_DOCKER_SILENT!"=="Y" (
    powershell -NoProfile -Command ^
        "$ws = New-Object -ComObject WScript.Shell; " ^
        "$s = $ws.CreateShortcut('%STARTUP_FOLDER%\Silent Docker Startup.lnk'); " ^
        "$s.TargetPath = 'wscript.exe'; " ^
        "$s.Arguments = '\"%INSTALL_DIR%\run_silent_docker.vbs\"'; " ^
        "$s.WorkingDirectory = '%INSTALL_DIR%'; " ^
        "$s.Description = 'Silent Background Docker Startup on Boot'; " ^
        "$s.Save()"

    echo [OK] Silent Docker Startup added to Windows Startup folder.
    echo      Docker Desktop will now start minimized in tray on boot!
) else (
    echo [INFO] Skipped Silent Docker startup.
)
echo.

echo ============================================================
echo   Desktop shortcuts created successfully!
echo   Server URL: http://%SERVER_IP%:!HTTP_PORT!
echo ============================================================
pause
