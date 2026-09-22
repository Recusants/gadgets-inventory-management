@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Create Superuser - Gadget Store System

echo ======================================================
echo       GADGET STORE SYSTEM - CREATE SUPERUSER
echo ======================================================
echo.

:: Check for running Docker container first
docker ps -q -f name=gadget_store_prod_web >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('docker ps -q -f name=gadget_store_prod_web') do set DOCKER_CID=%%i
    if defined DOCKER_CID (
        echo [INFO] Detected running Docker container: gadget_store_prod_web
        echo [INFO] Launching interactive createsuperuser inside Docker...
        echo.
        docker exec -it gadget_store_prod_web python manage.py createsuperuser
        goto :FINISH
    )
)

docker ps -q -f name=twentyone_void_prod_web >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('docker ps -q -f name=twentyone_void_prod_web') do set DOCKER_CID=%%i
    if defined DOCKER_CID (
        echo [INFO] Detected running Docker container: twentyone_void_prod_web
        echo [INFO] Launching interactive createsuperuser inside Docker...
        echo.
        docker exec -it twentyone_void_prod_web python manage.py createsuperuser
        goto :FINISH
    )
)

:: Otherwise check native Python venv
if exist ".\venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment (.\venv\Scripts\python.exe)...
    echo.
    .\venv\Scripts\python.exe manage.py createsuperuser
    goto :FINISH
)

:: Fallback to system python
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Using system Python...
    echo.
    python manage.py createsuperuser
    goto :FINISH
)

echo [ERROR] Neither Docker container nor Python environment was found!
echo Please ensure your server is running or Python is installed.
echo.
pause
exit /b 1

:FINISH
echo.
echo ======================================================
echo Superuser operation completed.
echo You can now log in at http://127.0.0.1:8086/accounts/login/
echo ======================================================
echo.
pause
