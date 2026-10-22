@echo off
title GitPulse Explorer — Development Mode
cd /d "%~dp0"

echo ===============================================================================
echo   GITPULSE EXPLORER -- CONCURRENT HOT-RELOAD DEVELOPMENT MODE
echo ===============================================================================
echo.

:: 1. Start FastAPI Backend in new window
echo Starting FastAPI Backend (Port 8000)...
start "GitPulse Backend" cmd /k "cd /d \"%~dp0\" && .venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"

:: 2. Wait 2 seconds for backend to start
timeout /t 2 /nobreak >nul

:: 3. Start Vite Dev Server in current window
echo Starting Vite Dev Server (Port 5173)...
start http://localhost:5173
cd frontend
call npm run dev
