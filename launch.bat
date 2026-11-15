@echo off
TITLE Gadget Store System - Dev Launch (Docker & PostgreSQL)
setlocal

set DOCKER_BUILDKIT=1
set COMPOSE_DOCKER_CLI_BUILD=1

echo ============================================================
echo   GADGET STORE SYSTEM - DEV ENVIRONMENT
echo ============================================================
echo.
echo URL: http://localhost:8001
echo Database: PostgreSQL on localhost:5433
echo Note: Code is volume-mounted; code edits reload live.
echo.
echo Run "launch.bat --build" only when requirements change.
echo Run "launch.bat env" to start host virtualenv with PostgreSQL.
echo Run "launch.bat sqlite" to start host virtualenv with SQLite.
echo.

if /i "%1"=="env" goto :run_env_dev
if /i "%1"=="--env" goto :run_env_dev
if /i "%1"=="sqlite" goto :run_sqlite_dev
if /i "%1"=="--sqlite" goto :run_sqlite_dev
if /i "%1"=="prod" goto :run_prod
if /i "%1"=="--prod" goto :run_prod

if "%1"=="--build" (
    echo [INFO] Rebuilding with BuildKit cache...
    docker compose -f docker-compose.dev.yml up --build
) else if "%1"=="-b" (
    echo [INFO] Rebuilding with BuildKit cache...
    docker compose -f docker-compose.dev.yml up --build
) else (
    echo [INFO] Starting containers (using cached image)...
    docker compose -f docker-compose.dev.yml up
)
goto :eof

:run_env_dev
call "%~dp0launch_env_dev.bat"
goto :eof

:run_sqlite_dev
call "%~dp0launch_sqlite_dev.bat"
goto :eof

:run_prod
echo [INFO] Starting Production Stack...
docker compose -f docker-compose.prod.yml up -d
echo [OK] Production running at http://localhost:8086
goto :eof
