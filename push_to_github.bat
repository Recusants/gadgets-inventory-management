@echo off
setlocal enabledelayedexpansion
title Push to GitHub - 21 Void Technologies

echo ======================================================
echo    ONE-CLICK GITHUB PUSH - GADGET STORE SYSTEM
echo ======================================================
echo.

:: Check if git is initialized
if not exist ".git" (
    echo [INFO] Initializing new Git repository...
    git init -b main
    if errorlevel 1 (
        echo [ERROR] Git init failed.
        pause
        exit /b 1
    )
)

:: Check if remote origin exists
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [SETUP REQUIRED] No GitHub remote repository configured yet.
    echo Please create a new repository on https://github.com/new
    set /p REPO_URL="Enter your GitHub Repository URL (e.g. https://github.com/username/gadget-store.git): "
    if "!REPO_URL!"=="" (
        echo [ERROR] No URL provided. Aborting.
        pause
        exit /b 1
    )
    git remote add origin !REPO_URL!
    echo [SUCCESS] Remote origin set to !REPO_URL!
    echo.
)

:: Prompt for commit message (Optional, defaults to timestamp)
set COMMIT_MSG=
set /p COMMIT_MSG="Enter commit message (Press ENTER to use auto-timestamp): "
if "!COMMIT_MSG!"=="" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
    set TIMESTAMP=!dt:~0,4!-!dt:~4,2!-!dt:~6,2! !dt:~8,2!:!dt:~10,2!
    set COMMIT_MSG=Update: !TIMESTAMP!
)

echo.
echo [1/3] Staging changes...
git add .

echo [2/3] Committing changes: "!COMMIT_MSG!"...
git commit -m "!COMMIT_MSG!"
if errorlevel 1 (
    echo [NOTICE] Nothing new to commit or commit failed.
)

echo [3/3] Pushing to GitHub...
:: Check current branch name
for /f "tokens=*" %%a in ('git branch --show-current') do set BRANCH=%%a
if "!BRANCH!"=="" set BRANCH=main

git push -u origin !BRANCH!
if errorlevel 1 (
    echo.
    echo ======================================================
    echo [ERROR] Push to GitHub failed!
    echo Possible causes:
    echo  1. You need to authenticate with GitHub (GitHub Personal Access Token or GitHub Desktop).
    echo  2. Remote branch has newer commits. Run: git pull origin !BRANCH! --rebase
    echo ======================================================
) else (
    echo.
    echo ======================================================
    echo [SUCCESS] Successfully pushed all code to GitHub on branch '!BRANCH!'!
    echo ======================================================
)

echo.
pause
