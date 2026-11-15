@echo off
title Clarity POS Windows Print Server
cd /d "%~dp0"
echo Starting Clarity POS Print Server (Dual Port: 9101 & 9300)...
if exist "%~dp0ClarityPrintServer.exe" (
    "%~dp0ClarityPrintServer.exe"
) else (
    python windows_print_server.py
)
pause
