@echo off
TITLE Gadget Store System - SQLite Dev (Zero-Setup)
setlocal enabledelayedexpansion

echo ============================================================
echo   GADGET STORE SYSTEM - SQLITE DEV (ZERO-SETUP)
echo ============================================================
echo.
echo Mode: Host Virtualenv + SQLite (db.sqlite3)
echo Settings: config.settings.local (or settings_dev.py)
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

set "DJANGO_SETTINGS_MODULE=config.settings.local"

echo [1/2] Applying SQLite database migrations...
python manage.py migrate --settings=config.settings.local
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Migration failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting development server at http://127.0.0.1:8000/ ...
python manage.py runserver 127.0.0.1:8000 --settings=config.settings.local
