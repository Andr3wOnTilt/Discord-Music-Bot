@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Discord Bot Dashboard — Build System

cls
echo.
echo  =====================================================================
echo    Discord Bot Dashboard  —  Build System
echo    Author: Andr3wOnTilt
echo  =====================================================================
echo.

cd /d "%~dp0"
set "ROOT=%CD%"
set "BUILD_DIR=%ROOT%\build"
set "DIST_DIR=%ROOT%\build\dist"
set "ARGS_FILE=%BUILD_DIR%\_build_args.json"

echo  [1/5]  Checking Python...
echo  ---------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo         ERROR: Python not found.
    echo         Install Python from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo         %%i
echo.

echo  [2/5]  Installing dependencies...
echo  ---------------------------------------------------------------------
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo         WARNING: Could not upgrade pip. Continuing anyway.
)
python -m pip install "discord.py[voice]" yt-dlp psutil PyNaCl pyinstaller --quiet
if errorlevel 1 (
    echo         ERROR: Failed to install dependencies.
    echo         Try running manually: pip install discord.py[voice] yt-dlp psutil PyNaCl pyinstaller
    echo.
    pause & exit /b 1
)
echo         discord.py[voice]  OK
echo         yt-dlp             OK
echo         psutil             OK
echo         PyNaCl             OK
echo         pyinstaller        OK
echo.

echo  [3/5]  Preparing output folder...
echo  ---------------------------------------------------------------------
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if not exist "%DIST_DIR%"  mkdir "%DIST_DIR%"
if exist "%DIST_DIR%\DiscordBotDashboard.exe" (
    echo         Removing previous build...
    del /f /q "%DIST_DIR%\DiscordBotDashboard.exe" >nul 2>&1
)
echo         Output: %DIST_DIR%
echo.

echo  [4/5]  Collecting files and locating FFmpeg...
echo  ---------------------------------------------------------------------
python "%ROOT%\_build_prepare.py" "%ROOT%" "%BUILD_DIR%" "%DIST_DIR%"
if errorlevel 1 (
    echo.
    echo         ERROR: Build preparation failed.
    pause & exit /b 1
)
echo.

echo  [5/5]  Compiling... (this may take 3-6 minutes, do not close)
echo  ---------------------------------------------------------------------
python "%ROOT%\_build_run.py" "%ARGS_FILE%"
if errorlevel 1 (
    echo.
    echo  =====================================================================
    echo    BUILD FAILED
    echo    Review the output above for error details.
    echo  =====================================================================
    del /f /q "%ARGS_FILE%" >nul 2>&1
    echo.
    pause & exit /b 1
)

del /f /q "%ARGS_FILE%" >nul 2>&1

if not exist "%DIST_DIR%\DiscordBotDashboard.exe" (
    echo.
    echo         ERROR: Executable not found after build.
    pause & exit /b 1
)

for %%i in ("%DIST_DIR%\DiscordBotDashboard.exe") do (
    set /a "SIZE_MB=%%~zi / 1048576"
)

echo.
echo  =====================================================================
echo    BUILD SUCCESSFUL
echo.
echo    File : build\dist\DiscordBotDashboard.exe
echo    Size : ~!SIZE_MB! MB
echo.
echo    Ready to distribute on any Windows PC.
echo    No Python or dependencies required on target machine.
echo.
echo    (c) Andr3wOnTilt  --  All rights reserved.
echo  =====================================================================
echo.

choice /c YN /m "  Open output folder"
if not errorlevel 2 explorer "%DIST_DIR%"

echo.
pause
