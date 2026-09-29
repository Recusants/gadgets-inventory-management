@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title 21 Void Technologies - Dev Machine Setup Wizard

echo ============================================================================
echo      21 VOID TECHNOLOGIES — ONE-CLICK DEV MACHINE SETUP WIZARD
echo ============================================================================
echo.
echo This wizard will configure this computer for local development:
echo  - Verify Python 3 and Git installations
echo  - Auto-clone repository if running in standalone mode
echo  - Auto-create isolated virtual environment (.venv)
echo  - Install project dependencies from requirements.txt
echo  - Auto-configure development environment (.env)
echo  - Apply clean database schema migrations (Zero Seed Data)
echo  - Compile static assets and verify system health
echo.
echo ============================================================================
echo.

:: -----------------------------------------------------------------------------
:: STAGE 1: Prerequisite Verification (Python and Git)
:: -----------------------------------------------------------------------------
echo [1/7] Verifying prerequisites (Python and Git)...

:: Check Git
where git >nul 2>&1
if errorlevel 1 goto :git_missing
for /f "tokens=3 delims= " %%g in ('git --version 2^>^&1') do set GIT_VER=%%g
echo  [OK] Git found: !GIT_VER!

:: Check Python
where python >nul 2>&1
if errorlevel 1 goto :python_missing

:: Check Python version
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  [OK] Python found: !PY_VER!

:: -----------------------------------------------------------------------------
:: STAGE 2: Repository Verification / Auto-Sync (Remote Code Takes Precedence, Data Preserved)
:: -----------------------------------------------------------------------------
echo.
echo [2/7] Checking project repository...

set DEFAULT_REPO=https://github.com/Recusants/gadgets-inventory-management.git
set TARGET_DIR=gadget-store
set REPO_URL=!DEFAULT_REPO!
set BRANCH=main

:: Case A: Running directly inside project directory
if exist "manage.py" (
    echo  [OK] Project detected in current directory.
    goto :sync_existing_repo
)

:: Case B: Project already cloned in subfolder !TARGET_DIR! from a previous run
if exist "!TARGET_DIR!\manage.py" (
    echo  [OK] Project detected in .\!TARGET_DIR!.
    echo  [INFO] Entering project directory: .\!TARGET_DIR!...
    cd /d "!TARGET_DIR!"
    goto :sync_existing_repo
)

:: Case C: Standalone installer mode - fresh clone needed
echo.
echo  ------------------------------------------------------------------------
echo  [STANDALONE INSTALLER DETECTED]
echo  Project files not found in current folder.
echo  Cloning repository from GitHub:
echo    !DEFAULT_REPO!
echo  ------------------------------------------------------------------------
echo.
set REPO_INPUT=
set /p REPO_INPUT="Press ENTER to clone default repo, or enter custom Git URL: "
if defined REPO_INPUT (
    set "TRIMMED_INPUT=!REPO_INPUT: =!"
    if not "!TRIMMED_INPUT!"=="" set REPO_URL=!REPO_INPUT!
)

:: If target dir exists but without manage.py (interrupted or corrupted prior clone)
if exist "!TARGET_DIR!" (
    echo.
    echo  [WARNING] Directory .\!TARGET_DIR! exists but contains no project files.
    echo  [INFO] Cleaning incomplete directory before re-cloning...
    rmdir /s /q "!TARGET_DIR!" >nul 2>&1
)

echo.
echo  [INFO] Cloning repository into .\!TARGET_DIR!...
git clone "!REPO_URL!" "!TARGET_DIR!"
if errorlevel 1 goto :clone_error

if not exist "!TARGET_DIR!\manage.py" goto :clone_empty_error

echo  [OK] Repository cloned successfully!
echo  [INFO] Entering project directory: .\!TARGET_DIR!...
cd /d "!TARGET_DIR!"
goto :repo_ready

:sync_existing_repo
:: Safety backup of existing database before code synchronization
if exist "db.sqlite3" (
    if not exist "backups" mkdir "backups"
    copy /y "db.sqlite3" "backups\db_backup_sync.sqlite3" >nul 2>&1
    echo  [OK] Safety snapshot of database saved to backups\db_backup_sync.sqlite3
)

if not exist ".git" goto :repo_ready

:: Detect active branch
for /f "tokens=*" %%B in ('git branch --show-current 2^>nul') do set BRANCH=%%B
if "!BRANCH!"=="" set BRANCH=main

echo  [INFO] Synchronizing code with online repository - Remote code takes precedence...
echo  [INFO] Preserving your local database db.sqlite3, media folder, and .env...
git fetch origin !BRANCH!
if errorlevel 1 (
    echo  [WARNING] Could not reach GitHub to fetch updates. Continuing with existing local files.
    goto :repo_ready
)

git reset --hard origin/!BRANCH!
echo  [OK] Code successfully updated to match origin/!BRANCH! - Data preserved.

:repo_ready

:: -----------------------------------------------------------------------------
:: STAGE 3: Virtual Environment Auto-Provisioning
:: -----------------------------------------------------------------------------
echo.
echo [3/7] Configuring Python virtual environment...
if exist ".\venv\Scripts\python.exe" (
    echo  [OK] Virtual environment already exists at .\venv
) else (
    echo  [INFO] Creating new isolated virtual environment at .\venv...
    python -m venv venv
    if errorlevel 1 goto :venv_error
    echo  [OK] Virtual environment created successfully.
)

:: Activate the virtual environment
call .\venv\Scripts\activate.bat
if errorlevel 1 goto :activate_error
echo  [OK] Virtual environment activated.

:: -----------------------------------------------------------------------------
:: STAGE 4: Upgrade Pip & Install Dependencies
:: -----------------------------------------------------------------------------
echo.
echo [4/7] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip --quiet
if not exist "requirements.txt" goto :requirements_missing

echo  [INFO] Installing packages (this may take 1-2 minutes on first run)...
pip install -r requirements.txt --quiet
if errorlevel 1 goto :pip_error
echo  [OK] All Python packages installed successfully.

:: -----------------------------------------------------------------------------
:: STAGE 5: Environment Configuration (.env)
:: -----------------------------------------------------------------------------
echo.
echo [5/7] Checking local environment configuration (.env)...
if exist ".env" (
    echo  [OK] .env configuration file already exists. Preserving existing settings.
) else (
    echo  [INFO] Generating default development .env file...
    (
        echo # ==============================================================================
        echo # 21 Void Technologies - Local Development Environment Settings
        echo # ==============================================================================
        echo DJANGO_SETTINGS_MODULE=config.settings.local
        echo DJANGO_SECRET_KEY=dev-local-secret-key-21void-gadget-store-2026-secure
        echo DEBUG=True
        echo ALLOWED_HOSTS=*
        echo CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
    ) > .env
    echo  [OK] Clean .env file generated successfully.
)

:: -----------------------------------------------------------------------------
:: STAGE 6: Clean Database Schema Migrations (Zero Seed Data)
:: -----------------------------------------------------------------------------
echo.
echo [6/7] Applying database schema migrations (Clean Setup)...
python manage.py migrate --settings=config.settings.local --noinput
if errorlevel 1 goto :migration_error
echo  [OK] Database schema initialized cleanly with zero seed data.

:: -----------------------------------------------------------------------------
:: STAGE 7: Static Assets & System Health Check
:: -----------------------------------------------------------------------------
echo.
echo [7/7] Compiling static assets and running system check...

:: Synchronize version.json if helper exists
if exist "core\version.py" (
    python core\version.py >nul 2>&1
)

python manage.py collectstatic --settings=config.settings.local --noinput
if errorlevel 1 (
    echo  [WARNING] Static files collection reported a notice. Continuing...
) else (
    echo  [OK] Static assets collected.
)

:: Run Django System Check
python manage.py check --settings=config.settings.local
if errorlevel 1 goto :system_check_error
echo  [OK] System check passed with 0 issues.

:: -----------------------------------------------------------------------------
:: SUCCESS & OPTIONAL SERVER LAUNCH
:: -----------------------------------------------------------------------------
echo.
echo ============================================================================
echo [SUCCESS] DEV MACHINE SETUP COMPLETE!
echo ============================================================================
echo.
echo Project is fully configured and ready for development.
echo  - Location:            %CD%
echo  - Virtual Environment: .\venv (Active)
echo  - Database:            SQLite (db.sqlite3 - Clean Schema, No Seed Data)
echo  - Settings Module:     config.settings.local
echo.
echo Tips for this machine:
echo  - To start the server anytime:      run_server.bat  (or launch.bat)
echo  - To pull latest updates:           pull_from_github.bat
echo  - To create an admin account:       create_superuser.bat
echo ============================================================================
echo.

set /p LAUNCH_NOW="Do you want to start the development server now? (Y/N) [Default: Y]: "
if /i "!LAUNCH_NOW!"=="" set LAUNCH_NOW=Y
if /i "!LAUNCH_NOW!"=="Y" (
    echo.
    echo Opening application in default browser...
    start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000/"
    echo Starting server on http://127.0.0.1:8000 ...
    echo Press Ctrl+C in this window anytime to stop the server.
    echo.
    python manage.py runserver 127.0.0.1:8000 --settings=config.settings.local
) else (
    echo.
    echo You can start the server later by running: run_server.bat
    echo.
    pause
)

exit /b 0

:: -----------------------------------------------------------------------------
:: ERROR HANDLERS (Clear Guidance with Links)
:: -----------------------------------------------------------------------------
:git_missing
echo.
echo ============================================================================
echo [ERROR] Git is not installed or not found in system PATH!
echo ============================================================================
echo How to fix:
echo  1. Download Git for Windows from: https://git-scm.com/download/win
echo  2. Install with default settings.
echo  3. Restart your command prompt and run this wizard again.
echo ============================================================================
echo.
pause
exit /b 1

:python_missing
echo.
echo ============================================================================
echo [ERROR] Python is not installed or not found in system PATH!
echo ============================================================================
echo How to fix:
echo  1. Download Python 3.10+ from: https://www.python.org/downloads/
echo  2. IMPORTANT: During installation, check the box:
echo     [X] "Add Python to PATH"
echo  3. Restart your command prompt and run this wizard again.
echo ============================================================================
echo.
pause
exit /b 1

:clone_error
echo.
echo ============================================================================
echo [ERROR] 'git clone' failed!
echo ============================================================================
echo Please verify:
echo  1. Your internet connection is active.
echo  2. The repository URL is correct.
echo  3. If the repository is private, verify your Git / GitHub credentials.
echo ============================================================================
echo.
pause
exit /b 1

:clone_empty_error
echo.
echo ============================================================================
echo [ERROR] Cloned folder does not contain manage.py!
echo ============================================================================
echo.
pause
exit /b 1

:venv_error
echo.
echo ============================================================================
echo [ERROR] Failed to create virtual environment!
echo ============================================================================
echo Please verify that Python standard library venv module is available.
echo Try manually running: python -m venv venv
echo ============================================================================
echo.
pause
exit /b 1

:activate_error
echo.
echo ============================================================================
echo [ERROR] Failed to activate virtual environment at .\venv\Scripts\activate.bat
echo ============================================================================
echo.
pause
exit /b 1

:requirements_missing
echo.
echo ============================================================================
echo [ERROR] requirements.txt not found in current directory!
echo Please make sure you are in the project root folder.
echo ============================================================================
echo.
pause
exit /b 1

:pip_error
echo.
echo ============================================================================
echo [ERROR] Failed to install dependencies from requirements.txt!
echo Please check your internet connection or inspect the error details above.
echo ============================================================================
echo.
pause
exit /b 1

:migration_error
echo.
echo ============================================================================
echo [ERROR] Database migration failed!
echo Please check your database settings or inspect the error traceback above.
echo ============================================================================
echo.
pause
exit /b 1

:system_check_error
echo.
echo ============================================================================
echo [ERROR] Django system check identified issues!
echo ============================================================================
echo.
pause
exit /b 1
