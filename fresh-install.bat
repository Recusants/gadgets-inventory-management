@echo off
TITLE Gadget Store System - Fresh Install (Wipe ^& Reinstall)
setlocal enabledelayedexpansion

echo ============================================================
echo       GADGET STORE SYSTEM - FRESH INSTALL TOOL
echo ============================================================
echo.
echo   This will permanently DELETE all local data including:
echo     - All sales, products, inventory and transactions
echo     - The PostgreSQL database and its volume
echo     - All running Gadget Store containers and images
echo.
echo   Use this ONLY when:
echo     - Setting up this machine for the first time
echo     - Recovering from a corrupt database
echo     - Performing a completely clean re-initialization
echo.
echo   The system will be reinstalled fresh from Docker Hub.
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Check Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM 2. Hard confirmation — must type YES in full
echo ------------------------------------------------------------
echo  WARNING: ALL LOCAL DATA WILL BE PERMANENTLY DELETED.
echo  This cannot be undone.
echo ------------------------------------------------------------
echo.
set "CONFIRM="
set /p "CONFIRM=Type YES (in capitals) to continue, or press Enter to cancel: "
if "!CONFIRM!" neq "YES" (
    echo.
    echo [INFO] Fresh install cancelled. Your data is safe.
    pause
    exit /b 0
)

echo.
echo [1/5] Stopping containers and removing compose volumes...
docker compose -f docker-compose.prod.yml down -v --remove-orphans 2>nul
echo [OK] Containers and compose volumes stopped and removed.
echo.

echo [2/5] Cleaning up any remaining database volumes...
for /f "tokens=*" %%v in ('docker volume ls -q 2^>nul') do (
    echo %%v | findstr /i "postgres" >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        docker volume rm -f %%v >nul 2>&1
        echo [OK] Removed volume: %%v
    )
)
echo.

echo [3/5] Removing old Gadget Store images...
for /f "tokens=*" %%i in ('docker images -q --filter "reference=*gadget-store*" 2^>nul') do (
    docker rmi -f %%i >nul 2>&1
)
echo [OK] Old images cleared.
echo.

echo [4/5] Verifying .env file...
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [OK] Created .env from template. Please edit it before the app starts.
    ) else (
        echo [ERROR] No .env or .env.example found!
        pause
        exit /b 1
    )
) else (
    echo [OK] .env exists.
)
echo.

echo [5/5] Pulling fresh image and starting clean installation...
echo.

REM Read registry from .env, always target latest for fresh install
set "DOCKER_REGISTRY=tinashemp"
set "TAG=latest"
set "HTTP_PORT=8086"

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="DOCKER_REGISTRY" set "DOCKER_REGISTRY=%%B"
    if /i "%%A"=="HTTP_PORT" set "HTTP_PORT=%%B"
)
set "DOCKER_REGISTRY=!DOCKER_REGISTRY: =!"
set "DOCKER_REGISTRY=!DOCKER_REGISTRY:"=!"
set "HTTP_PORT=!HTTP_PORT: =!"
set "HTTP_PORT=!HTTP_PORT:"=!"
if "!DOCKER_REGISTRY!"=="" set "DOCKER_REGISTRY=tinashemp"
if "!HTTP_PORT!"=="" set "HTTP_PORT=8086"

REM Ensure .env has TAG=latest so docker compose runs latest
powershell -NoProfile -Command "if (Select-String -Path '.env' -Pattern '^TAG\s*=') { (Get-Content '.env') -replace '^TAG\s*=.*$', 'TAG=latest' | Set-Content '.env' } else { Add-Content '.env' 'TAG=latest' }"

set "IMAGE=!DOCKER_REGISTRY!/gadget-store-app:latest"
echo Pulling !IMAGE!...
docker pull !IMAGE!
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not pull image. Check your internet connection.
    pause
    exit /b 1
)

docker compose -f docker-compose.prod.yml up -d
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start containers.
    echo.
    echo --- Diagnostic Logs for Database (gadget-store-postgres) ---
    docker logs gadget-store-postgres --tail 25 2>nul
    echo.
    echo --- Diagnostic Logs for Application (gadget-store-app) ---
    docker logs gadget-store-app --tail 25 2>nul
    echo.
    pause
    exit /b 1
)

REM Wait for app to boot and run migrations
echo.
echo Waiting for first-boot setup ^(migrations + static files^)...
timeout /t 20 /nobreak >nul

REM Get LAN IP
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback|Docker' -and $_.IPAddress -notmatch '^169\.254\.' } | Select-Object -First 1).IPAddress"') do set "SERVER_IP=%%a"
if "!SERVER_IP!"=="" set "SERVER_IP=127.0.0.1"

echo.
echo ============================================================
echo         FRESH INSTALL COMPLETE!
echo ============================================================
echo.
echo   Database    : PostgreSQL 16 (fresh, empty)
echo   Image       : !IMAGE!
echo   Local URL   : http://localhost:!HTTP_PORT!
echo   LAN URL     : http://!SERVER_IP!:!HTTP_PORT!
echo.
echo   Open http://localhost:!HTTP_PORT! to access the login page.
echo   To create an administrator superuser, run:
echo     docker exec -it gadget-store-app python manage.py createsuperuser --settings=config.settings.docker_prod
echo.
echo   To view startup logs:  docker logs -f gadget-store-app
echo ============================================================
echo.
pause
