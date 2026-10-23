@echo off
title NEO AI Assistant Launcher
echo ========================================================
echo   NEO AI - Your Local AI PC Assistant
echo ========================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo Starting NEO AI Desktop Assistant...
python main.py --mode ui

if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Application closed with return code %errorlevel%.
    pause
)
