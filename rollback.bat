@echo off
TITLE Gadget Store System - Version Rollback
setlocal enabledelayedexpansion

echo ============================================================
echo         GADGET STORE SYSTEM - VERSION ROLLBACK TOOL
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Verify Docker Engine
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM 2. Read Current Tag and Settings from .env
set "DOCKER_REGISTRY=tinashemp"
set "CURR_TAG=latest"
set "HTTP_PORT=8086"

if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "KEY=%%A"
        set "VAL=%%B"
        if /i "!KEY!"=="DOCKER_REGISTRY" set "DOCKER_REGISTRY=!VAL!"
        if /i "!KEY!"=="TAG" set "CURR_TAG=!VAL!"
        if /i "!KEY!"=="HTTP_PORT" set "HTTP_PORT=!VAL!"
    )
)

set "DOCKER_REGISTRY=!DOCKER_REGISTRY: =!"
set "CURR_TAG=!CURR_TAG: =!"
set "HTTP_PORT=!HTTP_PORT: =!"
if "!CURR_TAG!"=="" set "CURR_TAG=latest"
if "!DOCKER_REGISTRY!"=="" set "DOCKER_REGISTRY=tinashemp"
if "!HTTP_PORT!"=="" set "HTTP_PORT=8086"

echo Currently running tag : !CURR_TAG!
echo Target Docker Registry: !DOCKER_REGISTRY!/gadget-store-app
echo.
echo ------------------------------------------------------------
echo Please enter the version tag you want to rollback to.
echo Examples: v2.4.16, 2.4.16, v2.4.15
echo (Or type 'latest' to return to latest version)
echo ------------------------------------------------------------
echo.

set "TARGET_TAG="
set /p "TARGET_TAG=Rollback Tag: "

if "!TARGET_TAG!"=="" (
    echo [INFO] No version entered. Rollback cancelled.
    pause
    exit /b 0
)

REM Clean tag string
set "TARGET_TAG=!TARGET_TAG: =!"
set "IMAGE=!DOCKER_REGISTRY!/gadget-store-app:!TARGET_TAG!"

echo.
echo [1/4] Pulling specified version: !IMAGE!...
docker pull !IMAGE!
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Image !IMAGE! could not be found on Docker Hub.
    echo Please verify the version number exists in your Docker Hub repository.
    pause
    exit /b 1
)

echo [2/4] Updating TAG in .env file to !TARGET_TAG!...
powershell -NoProfile -Command "(Get-Content '.env') -replace '^TAG\s*=.*$', 'TAG=!TARGET_TAG!' | Set-Content '.env'"

echo [3/4] Recreating containers with tag !TARGET_TAG!...
docker compose -f docker-compose.prod.yml up -d
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start containers.
    pause
    exit /b 1
)

echo [4/4] Verifying database schema compatibility...
timeout /t 3 /nobreak >nul
docker exec gadget-store-app python manage.py migrate --noinput --settings=config.settings.docker_prod >nul 2>&1
docker exec gadget-store-app python manage.py collectstatic --noinput --settings=config.settings.docker_prod >nul 2>&1

REM Get LAN IP Address
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback|Docker' -and $_.IPAddress -notmatch '^169\.254\.' } | Select-Object -First 1).IPAddress"') do set "SERVER_IP=%%a"
if "!SERVER_IP!"=="" set "SERVER_IP=127.0.0.1"

echo.
echo ============================================================
echo            ROLLBACK COMPLETED SUCCESSFULLY!
echo ============================================================
echo.
echo   Current Active Tag: !TARGET_TAG!
echo   Server Local URL  : http://localhost:!HTTP_PORT!
echo   Store LAN URL     : http://!SERVER_IP!:!HTTP_PORT!
echo.
echo When you are ready to return to the latest version in the future:
echo Simply double-click update.bat, or run rollback.bat and enter 'latest'.
echo ============================================================
echo.
pause
