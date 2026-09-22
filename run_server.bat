@echo off
setlocal
cd /d "%~dp0"
title Gadget Store Server (Port 8086)

echo ======================================================
echo    STARTING GADGET STORE SYSTEM (PRODUCTION NATIVE)
echo ======================================================
echo.

:: 1. Activate Python virtualenv
if exist ".\venv\Scripts\activate.bat" (
    call .\venv\Scripts\activate.bat
) else (
    echo [WARNING] venv not found! Using global python...
)

:: 2. Apply any pending database migrations
echo [1/3] Verifying database schema...
python manage.py migrate --settings=config.settings.local --noinput

:: 3. Collect static files
echo [2/3] Checking static assets...
python manage.py collectstatic --noinput --settings=config.settings.local

:: 4. Start Waitress multi-threaded production WSGI server
echo [3/3] Starting server on http://127.0.0.1:8086 ...
echo Access the application in your browser at:
echo    http://127.0.0.1:8086
echo.

waitress-serve --listen=127.0.0.1:8086 --threads=8 config.wsgi:application
