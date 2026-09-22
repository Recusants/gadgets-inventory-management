@echo off
setlocal
cd /d "%~dp0"
title Update & Run Gadget Store System
echo ======================================================
echo    ONE-CLICK LOCAL SERVER DEPLOY / UPDATE
echo ======================================================
echo.

echo [1/3] Pulling latest image from Docker Hub...
docker compose -f docker-compose.deploy.yml pull

echo.
echo [2/3] Starting containers in background...
docker compose -f docker-compose.deploy.yml up -d

echo.
echo [3/3] Checking migrations...
docker compose -f docker-compose.deploy.yml exec web python manage.py migrate --settings=config.settings.docker_prod

echo.
echo ======================================================
echo [SUCCESS] Server is live! Access it at: http://127.0.0.1:8086 (or http://server-ip:8086)
echo ======================================================
echo.
pause
