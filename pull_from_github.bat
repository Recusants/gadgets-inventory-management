@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Pull Latest Update - 21 Void Technologies

echo ======================================================
echo    ONE-CLICK GITHUB PULL - GADGET STORE SYSTEM
echo ======================================================
echo.

:: 1. Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 goto :git_missing

:: 2. Check if this is a Git repository
if not exist ".git" goto :not_git_repo

:: 3. Detect current branch (default to main)
set BRANCH=main
for /f "tokens=*" %%B in ('git branch --show-current 2^>nul') do (
    set BRANCH=%%B
)
if "!BRANCH!"=="" set BRANCH=main

:: Safety backup of local database before pull
if exist "db.sqlite3" (
    if not exist "backups" mkdir "backups"
    copy /y "db.sqlite3" "backups\db_backup_pull.sqlite3" >nul 2>&1
    echo  [OK] Safety snapshot of database saved to backups\db_backup_pull.sqlite3
)

echo [1/4] Updating code from origin/!BRANCH! (Remote takes precedence, local data preserved)...
git fetch origin !BRANCH!
if errorlevel 1 goto :pull_error
git reset --hard origin/!BRANCH!
if errorlevel 1 goto :pull_error

echo.
echo [2/4] Checking Python environment and dependencies...
set PYTHON_CMD=python
if exist ".\venv\Scripts\python.exe" (
    set PYTHON_CMD=.\venv\Scripts\python.exe
    call .\venv\Scripts\activate.bat
    echo Using virtualenv: .\venv
) else (
    echo Using global Python interpreter...
)

if exist "requirements.txt" (
    echo Verifying required Python packages...
    pip install -r requirements.txt --quiet
)

echo.
echo [3/4] Applying database schema migrations...
!PYTHON_CMD! manage.py migrate --settings=config.settings.local --noinput
if errorlevel 1 (
    echo [WARNING] Migration command returned an error. Check database status.
)

echo.
echo [4/4] Updating static assets (CSS, JS, Splash screen)...
!PYTHON_CMD! manage.py collectstatic --settings=config.settings.local --noinput

echo.
echo ======================================================
echo [SUCCESS] System updated to latest version!
echo ======================================================
git log -1 --format="  Latest Commit: %%h (%%cr)%%n  Subject:       %%s%%n  Author:        %%an"
echo ======================================================
echo.

:: 5. Offer to start the server immediately
set /p START_CHOICE="Do you want to start the server right now? (Y/N) [default: Y]: "
if /i "!START_CHOICE!"=="" set START_CHOICE=Y
if /i "!START_CHOICE!"=="Y" (
    echo.
    echo Starting server via run_server.bat...
    if exist "run_server.bat" (
        call run_server.bat
    ) else (
        !PYTHON_CMD! manage.py runserver 127.0.0.1:8086 --settings=config.settings.local
    )
)

goto :done

:git_missing
echo.
echo ======================================================
echo [ERROR] Git is not installed or not found in system PATH!
echo Please download and install Git from: https://git-scm.com
echo ======================================================
echo.
pause
exit /b 1

:not_git_repo
echo.
echo ======================================================
echo [ERROR] This directory is not a Git repository (.git missing)!
echo ======================================================
echo.
pause
exit /b 1

:pull_error
echo.
echo ======================================================
echo [ERROR] 'git pull' failed!
echo ======================================================
echo Possible reasons:
echo  1. No internet connection to GitHub.
echo  2. Local file changes conflict with incoming updates.
echo     (Run 'git status' or 'git stash' to resolve conflicts).
echo  3. Remote origin is not configured properly.
echo ======================================================
echo.
pause
exit /b 1

:done
pause
exit /b 0
