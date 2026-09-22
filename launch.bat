@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM 21 VOID TECHNOLOGIES — Quick Launch Controller (Windows)
REM Modes: local (default), docker_dev, docker_prod
REM Usage: launch.bat [mode]
REM ============================================================================

set MODE=%~1
if "%MODE%"=="" set MODE=local

echo ============================================================================
echo   21 VOID TECHNOLOGIES — Record Keeping System
echo   Mode: %MODE%
echo ============================================================================

if /i "%MODE%"=="local" (
    echo [1/4] Checking Python environment...
    if not exist "venv\Scripts\python.exe" (
        echo Virtual environment not found. Creating venv...
        python -m venv venv
    )
    
    echo [2/4] Activating environment and checking dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    
    echo [3/4] Applying SQLite database migrations...
    python manage.py migrate --settings=config.settings.local
    
    echo [4/4] Starting 21 Void Technologies server...
    echo Opening application in default browser...
    start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000/"
    
    python manage.py runserver 127.0.0.1:8000 --settings=config.settings.local
    goto :eof
)

if /i "%MODE%"=="docker_dev" (
    echo Starting Docker Development Stack (Live Reload, PostgreSQL 16)...
    docker compose -f docker-compose.dev.yml up --build
    goto :eof
)

if /i "%MODE%"=="docker_prod" (
    echo Starting Docker Production Stack (Gunicorn + Nginx + PostgreSQL 16)...
    docker compose -f docker-compose.prod.yml up -d --build
    echo Opening production application...
    start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost/"
    echo Stack is running in background. Use 'docker compose -f docker-compose.prod.yml logs -f' to view logs.
    goto :eof
)

echo [ERROR] Unknown mode: "%MODE%"
echo Valid modes are: local, docker_dev, docker_prod
exit /b 1
