@echo off
title Goethe Booking Bot — Local Mode
:: Run from repo root regardless of where the .bat is launched from.
cd /d "%~dp0.."
echo ============================================
echo   Goethe Booking Bot — Local Runner
echo   Starts Flask backend on your laptop
echo   Dashboard: https://goethe-frontend-v3.vercel.app
echo   Backend:   http://localhost:5000
echo ============================================
echo.

:: Check Python
python --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

:: Install deps if missing
pip install -r requirements.txt --quiet 2>NUL

:: Copy .env.example to .env if .env missing
if not exist .env (
    echo Creating .env from .env.example — edit with your Railway env values
    copy .env.example .env >NUL
)

echo Starting bot on http://localhost:5000
echo Open the dashboard and set Backend URL to http://localhost:5000
echo.
echo Press Ctrl+C to stop the bot
echo ============================================
echo.

python webapp.py

if %errorlevel% neq 0 (
    echo.
    echo Bot exited with error code %errorlevel%
    pause
)
