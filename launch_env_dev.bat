@echo off
TITLE Gadget Store System - Host Env Dev (PostgreSQL)
setlocal enabledelayedexpansion

echo ============================================================
echo   GADGET STORE SYSTEM - ENV DEV (POSTGRESQL)
echo ============================================================
echo.
echo Mode: Host Virtualenv + PostgreSQL
echo Settings: config.settings.env_dev (or settings.py)
echo.

cd /d "%~dp0"

REM 1. Verify Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

REM 2. Activate venv if present
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
)

set "DJANGO_SETTINGS_MODULE=config.settings.env_dev"

echo [1/2] Applying database migrations to PostgreSQL...
python manage.py migrate --settings=config.settings.env_dev
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARN] Could not connect to PostgreSQL or migration failed.
    echo Ensure PostgreSQL is running on host (e.g. localhost:5433 or 5432).
    echo You can start the dev PostgreSQL container using:
    echo     docker compose -f docker-compose.dev.yml up db -d
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting development server at http://127.0.0.1:8000/ ...
python manage.py runserver 127.0.0.1:8000 --settings=config.settings.env_dev
