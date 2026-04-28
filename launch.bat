@echo off
chcp 65001 >nul
title Gemini Chat Backup Tool

:: Provjeri Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nije instaliran ili nije u PATH-u.
    echo Preuzmite Python sa https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Provjeri Playwright
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instaliram Playwright...
    pip install playwright
    playwright install chromium
)

:: Pokreni skriptu
cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo =========================================
    echo   Gemini Chat Backup Tool
    echo =========================================
    echo.
    echo Pokretanje interaktivnog moda...
    echo.
    echo TIP: Povucite .txt datoteku s linkovima na ovu .bat datoteku
    echo      za automatski backup (Drag ^& Drop mod).
    echo.
    timeout /t 2 >nul
    python gemini_backup.py
) else (
    echo.
    echo =========================================
    echo   Gemini Chat Backup Tool
    echo   Drag ^& Drop Mod
    echo =========================================
    echo.
    echo Datoteka: %~1
    echo.
    python gemini_backup.py "%~1"
)

echo.
echo =========================================
echo Pritisnite bilo koju tipku za izlaz...
pause >nul