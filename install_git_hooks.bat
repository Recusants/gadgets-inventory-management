@echo off
TITLE Install Git Hooks - Gadget Store System
cd /d "%~dp0"

echo ============================================================
echo   INSTALLING GIT PRE-PUSH TEST HOOK
echo ============================================================
echo.

where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    pause
    exit /b 1
)

git config core.hooksPath .githooks
if %ERRORLEVEL% equ 0 (
    echo [OK] Configured Git hooks directory: .githooks
    echo [OK] Pre-push hook active: tests will run automatically before every git push.
) else (
    echo [WARN] Could not set core.hooksPath; copying directly to .git\hooks...
    if not exist ".git\hooks" mkdir ".git\hooks"
    copy /Y ".githooks\pre-push" ".git\hooks\pre-push" >nul
    echo [OK] Copied hook to .git\hooks\pre-push
)

echo.
echo ============================================================
echo   Git hooks installed successfully!
echo ============================================================
pause
