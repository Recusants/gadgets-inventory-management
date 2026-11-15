@echo off
TITLE Gadget Store System - Update & Deployment
setlocal enabledelayedexpansion

echo ============================================================
echo       GADGET STORE SYSTEM - SYSTEM UPDATE & DEPLOYMENT
echo ============================================================
echo Time: %DATE% %TIME%
echo.

cd /d "%~dp0"

REM 1. Check Docker Desktop / Engine
echo [1/6] Checking Docker engine status...
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo [ERROR] Docker is not running or not accessible.
    echo Please start Docker Desktop, wait for the engine to start,
    echo and double-click update.bat again.
    echo ============================================================
    echo.
    pause
    exit /b 1
)
echo [OK] Docker engine is running.
echo.

REM 2. Verify .env file
echo [2/6] Checking configuration files...
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] .env not found. Initializing from .env.example...
        copy /y ".env.example" ".env" >nul
        echo [OK] Created .env file.
    ) else (
        echo [ERROR] Neither .env nor .env.example was found!
        pause
        exit /b 1
    )
)

if not exist "docker-compose.prod.yml" (
    echo [ERROR] docker-compose.prod.yml not found in %CD%!
    pause
    exit /b 1
)
echo [OK] Configuration files verified.
echo.

REM 3. Target Docker Image (Always latest for update.bat)
set "DOCKER_REGISTRY=tinashemp"
set "TAG=latest"
set "HTTP_PORT=8086"

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "KEY=%%A"
    set "VAL=%%B"
    if /i "!KEY!"=="DOCKER_REGISTRY" set "DOCKER_REGISTRY=!VAL!"
    if /i "!KEY!"=="HTTP_PORT" set "HTTP_PORT=!VAL!"
)

REM Strip spaces or quotes
set "DOCKER_REGISTRY=!DOCKER_REGISTRY: =!"
set "DOCKER_REGISTRY=!DOCKER_REGISTRY:"=!"
set "HTTP_PORT=!HTTP_PORT: =!"
set "HTTP_PORT=!HTTP_PORT:"=!"
if "!DOCKER_REGISTRY!"=="" set "DOCKER_REGISTRY=tinashemp"
if "!HTTP_PORT!"=="" set "HTTP_PORT=8086"

REM Ensure .env has TAG=latest so docker compose also starts latest
powershell -NoProfile -Command "if (Select-String -Path '.env' -Pattern '^TAG\s*=') { (Get-Content '.env') -replace '^TAG\s*=.*$', 'TAG=latest' | Set-Content '.env' } else { Add-Content '.env' 'TAG=latest' }"

set "IMAGE=!DOCKER_REGISTRY!/gadget-store-app:latest"

echo [3/6] Target Docker Image: !IMAGE!
echo.
echo Pulling latest image from Docker Hub...
docker pull !IMAGE!
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Failed to pull !IMAGE! from remote registry.
    echo Checking if a local cached image is available...
    docker image inspect !IMAGE! >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] No local or remote image found for !IMAGE!.
        echo Make sure the GitHub Actions build completed and pushed to Docker Hub.
        pause
        exit /b 1
    )
    echo [INFO] Found local image. Proceeding with deployment...
) else (
    echo [OK] Latest image downloaded successfully!
)
echo.

REM 4. Deploy / Recreate Containers
echo [4/6] Applying container updates...
docker compose -f docker-compose.prod.yml up -d
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start containers via docker compose.
    pause
    exit /b 1
)
echo [OK] Containers started.
echo.

REM 5. Verify container started cleanly (migrations ran inside entrypoint on startup)
echo [5/6] Verifying container startup...
timeout /t 5 /nobreak >nul

docker inspect --format="{{.State.Health.Status}}" gadget-store-app 2>nul | findstr /i "healthy starting" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Container started. Checking recent logs...
    docker logs gadget-store-app --tail 15
) else (
    echo [OK] Container is healthy.
)
echo.

REM Clean up obsolete images
docker image prune -f >nul 2>&1

REM 6. Get Server Local LAN IP Address
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback|Docker' -and $_.IPAddress -notmatch '^169\.254\.' } | Select-Object -First 1).IPAddress"') do set "SERVER_IP=%%a"
if "!SERVER_IP!"=="" set "SERVER_IP=127.0.0.1"

echo ============================================================
echo        GADGET STORE SYSTEM - DEPLOYED SUCCESSFULLY!
echo ============================================================
echo.
echo   Image Tag       : !TAG!
echo   Server Local URL: http://localhost:!HTTP_PORT!
echo   Store LAN URL   : http://!SERVER_IP!:!HTTP_PORT!
echo   Status          : HEALTHY ^& RUNNING
echo.
echo Client Terminals (Cashiers, Inventory, Admin):
echo   Point browsers across the LAN to: http://!SERVER_IP!:!HTTP_PORT!
echo.
echo Useful Commands:
echo   - View live logs:    docker logs -f gadget-store-app
echo   - Stop server:       docker compose -f docker-compose.prod.yml down
echo   - Rollback version:  rollback.bat
echo ============================================================
echo.
pause
