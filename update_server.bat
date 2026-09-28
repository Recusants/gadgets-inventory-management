@echo off
setlocal
cd /d "%~dp0"
title Update and Run Gadget Store System

echo ======================================================
echo    ONE-CLICK LOCAL SERVER DEPLOY / UPDATE
echo ======================================================
echo.

:: 1. Verify Docker daemon is running
echo Checking Docker engine status...
docker info >nul 2>&1
if errorlevel 1 goto :docker_error

echo.
echo [1/3] Pulling latest image from Docker Hub...
docker compose -f docker-compose.deploy.yml pull
if errorlevel 1 goto :pull_error

echo.
echo [2/3] Starting containers in background...
docker compose -f docker-compose.deploy.yml up -d
if errorlevel 1 goto :up_error

echo.
echo [3/3] Checking migrations...
docker compose -f docker-compose.deploy.yml exec web python manage.py migrate --settings=config.settings.docker_prod

echo.
echo ======================================================
echo [SUCCESS] Server is live! Access it at:
echo    http://127.0.0.1:8086
echo    http://localhost:8086
echo ======================================================
echo.
pause
exit /b 0

:docker_error
echo.
echo ======================================================
echo [ERROR] Docker Desktop is not running or failed to start!
echo ======================================================
echo Docker Desktop must be open and running to deploy via Docker.
echo.
echo How to resolve:
echo  1. Open "Docker Desktop" from your Windows Start Menu.
echo  2. Wait until the whale icon in the taskbar turns solid green [Running].
echo  3. If Docker Desktop shows an error on start:
echo     - Open PowerShell as Administrator and run: wsl --update
echo     - Ensure Hardware Virtualization is enabled in your BIOS.
echo.
echo --- ALTERNATIVE NATIVE DEPLOYMENT [NO DOCKER NEEDED] ---
echo If this machine does not support Docker Desktop, run:
echo    run_server.bat
echo or to auto-start when Windows boots:
echo    install_auto_start_on_boot.bat
echo ======================================================
echo.
pause
exit /b 1

:pull_error
echo.
echo ======================================================
echo [ERROR] Failed to pull image from Docker Hub.
echo Please check your internet connection and try again.
echo ======================================================
echo.
pause
exit /b 1

:up_error
echo.
echo ======================================================
echo [ERROR] Failed to start Docker containers.
echo ======================================================
echo.
pause
exit /b 1
