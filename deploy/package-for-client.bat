@echo off
TITLE Gadget Store System - Prepare Client Deployment Package
setlocal EnableDelayedExpansion

echo ============================================================
echo   GADGET STORE SYSTEM - GENERATE CLIENT DEPLOYMENT PACKAGE
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "OUTPUT_DIR=%~dp0client-package"
set "ZIP_FILE=%~dp0GadgetStore_LAN_Client_Deployment.zip"

echo [1/4] Preparing clean output directories...
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\logs"
mkdir "%OUTPUT_DIR%\media"
mkdir "%OUTPUT_DIR%\staticfiles"
mkdir "%OUTPUT_DIR%\backups"

echo [2/4] Copying deployment scripts and configuration...
copy /y "%PROJECT_ROOT%\docker-compose.prod.yml" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\update.bat" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\rollback.bat" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\fresh-install.bat" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\create_desktop_shortcuts.bat" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\run_silent_docker.vbs" "%OUTPUT_DIR%\" >nul
if exist "%PROJECT_ROOT%\ClarityPrintServer.exe" copy /y "%PROJECT_ROOT%\ClarityPrintServer.exe" "%OUTPUT_DIR%\" >nul
if exist "%PROJECT_ROOT%\start_print_server.bat" copy /y "%PROJECT_ROOT%\start_print_server.bat" "%OUTPUT_DIR%\" >nul
if exist "%PROJECT_ROOT%\run_silent_print_server.vbs" copy /y "%PROJECT_ROOT%\run_silent_print_server.vbs" "%OUTPUT_DIR%\" >nul
copy /y "%PROJECT_ROOT%\.env.example" "%OUTPUT_DIR%\.env" >nul

echo [3/4] Copying deployment instructions and generating launcher...
copy /y "%~dp0INSTRUCTIONS.txt" "%OUTPUT_DIR%\" >nul
if exist "%~dp0README.md" (
    copy /y "%~dp0README.md" "%OUTPUT_DIR%\" >nul
)

REM Create Open Gadget Store shortcut
(
echo @echo off
echo echo Opening Gadget Store System...
echo set "HTTP_PORT=8086"
echo if exist "%%~dp0.env" ^(
echo     for /f "usebackq tokens=1,* delims==" %%%%A in ^("%%~dp0.env"^) do ^(
echo         if /i "%%%%A"=="HTTP_PORT" set "HTTP_PORT=%%%%B"
echo     ^)
echo ^)
echo set "HTTP_PORT=%%HTTP_PORT: =%%"
echo set "HTTP_PORT=%%HTTP_PORT:"=%%"
echo if "%%HTTP_PORT%%"=="" set "HTTP_PORT=8086"
echo for /f "tokens=*" %%%%a in ^('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { `$_.InterfaceAlias -notmatch 'vEthernet|Loopback|Docker' -and `$_.IPAddress -notmatch '^^169\.254\.' } | Select-Object -First 1).IPAddress"'^) do set "SERVER_IP=%%%%a"
echo if "%%SERVER_IP%%"=="" set "SERVER_IP=127.0.0.1"
echo start http://%%SERVER_IP%%:%%HTTP_PORT%%
) > "%OUTPUT_DIR%\Open Gadget Store.bat"

echo [4/4] Creating zip archive...
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"
ping -n 2 127.0.0.1 >nul
powershell -NoProfile -Command "$ProgressPreference = 'SilentlyContinue'; Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '%ZIP_FILE%' -Force"

echo.
echo ============================================================
echo               PACKAGE CREATED SUCCESSFULLY!
echo ============================================================
echo.
echo Client Folder: %OUTPUT_DIR%
echo Zip Archive  : %ZIP_FILE%
echo.
echo What to do next:
echo 1. Copy "%ZIP_FILE%" to the client server (via USB drive or network).
echo 2. Extract to "C:\avail\GadgetStore\".
echo 3. Configure .env and double-click "update.bat".
echo ============================================================
echo.
if "%CI%"=="" if not "%~1"=="--no-pause" pause
