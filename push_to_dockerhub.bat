@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Push to Docker Hub - 21 Void Technologies

echo ======================================================
echo    ONE-CLICK DOCKER HUB PUSH - GADGET STORE SYSTEM
echo ======================================================
echo.

:: 1. Check if Docker Desktop is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running!
    echo Please launch Docker Desktop first and wait until it is ready.
    echo.
    pause
    exit /b 1
)

:: 2. Load or prompt for Docker Hub username
set IMAGE_NAME=gadget-store-app
set DOCKER_USER=

if exist ".dockerhub_user" (
    set /p DOCKER_USER=<.dockerhub_user
)

if "!DOCKER_USER!"=="" (
    set /p DOCKER_USER="Enter your Docker Hub Username: "
    if "!DOCKER_USER!"=="" (
        echo [ERROR] Username cannot be empty.
        pause
        exit /b 1
    )
    echo !DOCKER_USER!>.dockerhub_user
    echo [SAVED] Docker Hub username '!DOCKER_USER!' saved to .dockerhub_user
) else (
    echo [INFO] Using Docker Hub user: !DOCKER_USER! (from .dockerhub_user)
)

:: 3. Check if logged in, otherwise prompt login
echo.
echo [1/3] Verifying Docker Hub authentication...
docker login -u !DOCKER_USER!
if errorlevel 1 (
    echo [ERROR] Docker Hub login failed. Check your password or Personal Access Token.
    pause
    exit /b 1
)

echo.
echo [Auto-Versioning] Calculating latest Clarity Retail version...
if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe core\version.py
) else (
    python core\version.py
)

:: 4. Build Docker Production Image
echo.
echo [2/3] Building production Docker image: !DOCKER_USER!/!IMAGE_NAME!:latest ...
docker build -f Dockerfile.prod -t !DOCKER_USER!/!IMAGE_NAME!:latest .
if errorlevel 1 (
    echo.
    echo [ERROR] Docker build failed! Check output above.
    pause
    exit /b 1
)

:: 5. Push to Docker Hub
echo.
echo [3/3] Pushing image to Docker Hub repository...
docker push !DOCKER_USER!/!IMAGE_NAME!:latest
if errorlevel 1 (
    echo.
    echo [ERROR] Docker push failed! Check your internet connection and repository permissions.
    pause
    exit /b 1
)

echo.
echo ======================================================
echo [SUCCESS] Successfully pushed image to Docker Hub!
echo Image URI: !DOCKER_USER!/!IMAGE_NAME!:latest
echo ======================================================
echo.
pause
