@echo off
TITLE Gadget Store System - 1-Click Push (GitHub ^& Docker Hub)
setlocal enabledelayedexpansion

echo ============================================================
echo   GADGET STORE SYSTEM - ONE-CLICK GITHUB PUSH ^& DOCKER BUILD
echo ============================================================
echo.

cd /d "%~dp0"

REM 1. Verify Git installation
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

REM 2. Verify or Initialize Git Repository
if not exist ".git" (
    echo [INFO] Git repository is not yet initialized in this folder.
    choice /C YN /M "Would you like to initialize git now"
    if !ERRORLEVEL! neq 1 exit /b 0
    git init
    git branch -M main
    set /p "GIT_REMOTE=Enter GitHub remote URL [default: https://github.com/Recusants/gadgets-inventory-management.git]: "
    if "!GIT_REMOTE!"=="" set "GIT_REMOTE=https://github.com/Recusants/gadgets-inventory-management.git"
    git remote add origin !GIT_REMOTE!
    echo [OK] Initialized git repository with remote origin: !GIT_REMOTE!
    echo.
)

REM 3. Determine current branch
for /f "tokens=*" %%i in ('git branch --show-current 2^>nul') do set CURRENT_BRANCH=%%i
if "%CURRENT_BRANCH%"=="" set CURRENT_BRANCH=main
echo [INFO] Active Branch: %CURRENT_BRANCH%
echo.

REM 4. Version Management (version.txt)
set "CURR_VER=2.4.16"
if exist "version.txt" (
    set /p CURR_VER=<version.txt
    set "CURR_VER=!CURR_VER: =!"
)

REM Auto-calculate next patch version via PowerShell
for /f "tokens=*" %%v in ('powershell -NoProfile -Command "$v = '%CURR_VER%'.Trim().TrimStart('v'); $parts = $v.Split('.'); if ($parts.Length -eq 3) { [int]$p = $parts[2] + 1; $parts[0] + '.' + $parts[1] + '.' + $p } else { '2.4.17' }"') do set "NEXT_VER=%%v"

echo ------------------------------------------------------------
echo  VERSION RELEASE MANAGEMENT
echo ------------------------------------------------------------
echo  Current Version : %CURR_VER%
echo  Suggested Next  : %NEXT_VER%
echo.
set "USER_VER="
set /p "USER_VER=Enter release version [Press Enter for %NEXT_VER%]: "
if "!USER_VER!"=="" set "USER_VER=%NEXT_VER%"

REM Clean version string (remove leading v if entered)
for /f "tokens=*" %%v in ('powershell -NoProfile -Command "'!USER_VER!'.Trim().TrimStart('v')"') do set "CLEAN_VER=%%v"
set "TAG_NAME=v!CLEAN_VER!"

REM 5. Check for uncommitted changes or unpushed commits
git status --porcelain > "%TEMP%\git_status.txt"
set HAS_CHANGES=0
for %%A in ("%TEMP%\git_status.txt") do if %%~zA gtr 0 set HAS_CHANGES=1
del "%TEMP%\git_status.txt" 2>nul

set HAS_UNPUSHED=0
for /f "tokens=*" %%C in ('git log origin/%CURRENT_BRANCH%..%CURRENT_BRANCH% --oneline 2^>nul') do set HAS_UNPUSHED=1

REM 6. Commit Message & What's New Change Details
set "COMMIT_MSG=%*"
if not defined COMMIT_MSG (
    echo ------------------------------------------------------------
    echo  COMMIT AND RELEASE DETAILS
    echo ------------------------------------------------------------
    set /p "COMMIT_MSG=Enter release title / commit message [Press Enter for 'Release !TAG_NAME!']: "
    if not defined COMMIT_MSG (
        for /f "tokens=*" %%T in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "NOW_TIME=%%T"
        set "COMMIT_MSG=Release !TAG_NAME! - !NOW_TIME!"
    )
)

set "RELEASE_NOTES="
echo.
set /p "RELEASE_NOTES=Enter What's New change notes [Press Enter to auto-generate from changes]: "
echo.

REM 7. Synchronize version across version.txt, VERSION, version.json, and FEATURE_UPDATES.txt
echo ------------------------------------------------------------
echo  SYNCHRONIZING RELEASE TRACKS AND WHAT'S NEW CHANGELOG
echo ------------------------------------------------------------
if exist "sync_version.py" (
    python sync_version.py "!TAG_NAME!" --title "!COMMIT_MSG!" --notes "!RELEASE_NOTES!"
) else (
    echo !CLEAN_VER!> "version.txt"
    echo !TAG_NAME!> "VERSION"
)
echo [INFO] Tag to be published: !TAG_NAME! (Docker Hub: !TAG_NAME! and latest)
echo.

echo.
echo ============================================================
echo [1/5] RUNNING AUTOMATED TEST SUITE BEFORE PUSH
echo ============================================================
set "DJANGO_SETTINGS_MODULE=config.settings.local"
set "DJANGO_SECRET_KEY=test-key-ci"
python manage.py test
if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo [ERROR] AUTOMATED TESTS FAILED!
    echo Push aborted to prevent releasing broken code.
    echo Please fix failing tests before pushing.
    echo ============================================================
    echo.
    pause
    exit /b 1
)
echo [OK] All automated tests passed successfully!

where flake8 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Running Flake8 syntax and lint check...
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.venv,build,dist
    if !ERRORLEVEL! neq 0 (
        echo.
        echo ============================================================
        echo [ERROR] FLAKE8 LINT CHECKS FAILED!
        echo Push aborted to prevent breaking CI pipeline on GitHub.
        echo ============================================================
        echo.
        pause
        exit /b 1
    )
    echo [OK] Flake8 checks passed cleanly!
)
echo.

echo [2/5] Staging files...
git add -A

if %HAS_CHANGES% equ 1 (
    echo [3/5] Committing: "!COMMIT_MSG!"...
    git commit -m "!COMMIT_MSG!"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Commit failed.
        pause
        exit /b 1
    )
) else (
    echo [3/5] No uncommitted file changes; proceeding with release tag...
)

echo [4/5] Creating Git release tag: !TAG_NAME!...
git tag -fa !TAG_NAME! -m "Release !TAG_NAME!"

echo [5/5] Pushing code and tag to GitHub origin %CURRENT_BRANCH%...
git push origin %CURRENT_BRANCH% !TAG_NAME! --force

if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================================
    echo [ERROR] Git push failed. Please check network/permissions.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                    PUSH SUCCESSFUL!
echo ============================================================
echo.
echo GitHub Actions is now building and publishing two tags to Docker Hub:
echo   1. :latest       (Default tag for standard client updates)
echo   2. :!TAG_NAME!     (Pinned immutable version for rollbacks)
echo.

set "REPO_URL="
for /f "tokens=*" %%u in ('git remote get-url origin 2^>nul') do set "REPO_URL=%%u"
if defined REPO_URL (
    set "REPO_URL=!REPO_URL:.git=!"
    set "ACTIONS_URL=!REPO_URL!/actions"
) else (
    set "ACTIONS_URL=https://github.com/Recusants/gadgets-inventory-management/actions"
)

echo Monitor your build on GitHub:
echo   !ACTIONS_URL!
echo.

choice /C YN /T 6 /D N /M "Open GitHub Actions page in your web browser"
if !ERRORLEVEL! equ 1 start "" "!ACTIONS_URL!"

echo.
echo ============================================================
echo All done! GitHub Actions will compile and publish the image.
echo When ready, run update.bat on the client LAN server.
echo ============================================================
echo.
pause
