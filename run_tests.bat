@echo off
TITLE Gadget Store System - Automated Test Suite Runner
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================================
echo      GADGET STORE SYSTEM - AUTOMATED TEST SUITE RUNNER
echo ============================================================
echo.

REM 1. Verify Python installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please ensure Python 3.10+ is installed.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%p in ('python --version 2^>^&1') do set "PY_VER=%%p"
echo [ENV] Python      : %PY_VER%
echo [ENV] Settings    : config.settings.local (SQLite In-Memory/Dev)
echo [ENV] Project Dir : %CD%
echo.

echo ------------------------------------------------------------
echo  SELECT TEST SUITE TO EXECUTE:
echo ------------------------------------------------------------
echo   [0] FULL Test Suite (All tests across all apps - default)
echo.
echo   [1] Accounts (Auth, Roles, Permissions, Staff Management)
echo.
echo   [2] Inventory (Products, Categories, IMEI/Serials, Stock Limits)
echo.
echo   [3] Sales & POS (Cart, Checkouts, Receipts, Cashier Sessions)
echo.
echo   [4] Reports (Daily Sales, Profit Margins, Stock Valuation)
echo.
echo   [5] Expenses (Expenditure Lifecycle, Categories, Audit Trail)
echo.
echo   [6] Dashboard (Overview Analytics, Low Stock Alerts)
echo.
echo   [7] Core (Company Settings, Localization, Notifications)
echo ------------------------------------------------------------
echo.

set "CHOICE=0"
set /p "CHOICE=Enter selection [0-7, Press Enter for default]: "
if "!CHOICE!"=="" set "CHOICE=0"

set "TARGET_APP="
if "!CHOICE!"=="0" (
    set "TARGET_NAME=FULL SYSTEM TEST SUITE"
    set "TARGET_APP="
) else if "!CHOICE!"=="1" (
    set "TARGET_NAME=Accounts Module"
    set "TARGET_APP=accounts"
) else if "!CHOICE!"=="2" (
    set "TARGET_NAME=Inventory Module"
    set "TARGET_APP=inventory"
) else if "!CHOICE!"=="3" (
    set "TARGET_NAME=Sales Module"
    set "TARGET_APP=sales"
) else if "!CHOICE!"=="4" (
    set "TARGET_NAME=Reports Module"
    set "TARGET_APP=reports"
) else if "!CHOICE!"=="5" (
    set "TARGET_NAME=Expenses Module"
    set "TARGET_APP=expenses"
) else if "!CHOICE!"=="6" (
    set "TARGET_NAME=Dashboard Module"
    set "TARGET_APP=dashboard"
) else if "!CHOICE!"=="7" (
    set "TARGET_NAME=Core Module"
    set "TARGET_APP=core"
) else (
    echo [WARN] Invalid choice "!CHOICE!"; defaulting to FULL TEST SUITE.
    set "TARGET_NAME=FULL SYSTEM TEST SUITE"
    set "TARGET_APP="
)

echo.
echo ============================================================
echo   EXECUTING: !TARGET_NAME!
echo ============================================================
echo.

set "DJANGO_SETTINGS_MODULE=config.settings.local"
set "DJANGO_SECRET_KEY=test-key-ci"

if "!TARGET_APP!"=="" (
    python manage.py test --verbosity=2
) else (
    python manage.py test !TARGET_APP! --verbosity=2
)

set "TEST_EXIT_CODE=%ERRORLEVEL%"

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo ============================================================
    echo           [SUCCESS] ALL AUTOMATED TESTS PASSED!
    echo ============================================================
    echo  Code quality verified. Ready for deployment and push.
    echo ============================================================
) else (
    echo ============================================================
    echo           [FAILURE] TEST SUITE REPORTED ERRORS!
    echo ============================================================
    echo  Exit Code: %TEST_EXIT_CODE%
    echo  Please review the traceback above and resolve any failures.
    echo ============================================================
)

echo.
pause
exit /b %TEST_EXIT_CODE%
