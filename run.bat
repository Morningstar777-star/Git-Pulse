@echo off
setlocal enabledelayedexpansion

title GitPulse Explorer — Launcher
cd /d "%~dp0"

echo ===============================================================================
echo   GITPULSE EXPLORER -- LOCAL GITHUB TREND INTELLIGENCE DASHBOARD
echo ===============================================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 was not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check for Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js was not found in your system PATH.
    echo Please install Node.js version 18 or higher from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

:: 3. Setup / Verify Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment in .venv ...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create Python virtual environment.
        pause
        exit /b 1
    )
)

:: 4. Verify Backend Dependencies
if not exist ".venv\Lib\site-packages\fastapi" (
    echo [2/4] Installing backend Python dependencies ...
    ".venv\Scripts\pip.exe" install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
) else (
    echo [2/4] Backend dependencies verified.
)

:: 5. Verify / Build Frontend Distribution
if not exist "frontend\dist\index.html" (
    echo [3/4] Building production frontend assets ...
    cd frontend
    if not exist "node_modules" (
        echo       Installing frontend npm packages ...
        call npm install
    )
    echo       Compiling Vite production bundle ...
    call npm run build
    cd /d "%~dp0"
    if not exist "frontend\dist\index.html" (
        echo [ERROR] Frontend build failed.
        pause
        exit /b 1
    )
) else (
    echo [3/4] Frontend distribution verified.
)

:: 6. Check if GitPulse is already running on port 8000
netstat -ano | findstr /R /C:":8000 " >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] GitPulse Explorer is already active on port 8000!
    echo Opening application in your default browser...
    start http://localhost:8000
    ping 127.0.0.1 -n 3 >nul
    exit /b 0
)

:: 7. Start GitPulse Server & Open Browser
echo [4/4] Starting GitPulse Explorer on http://localhost:8000 ...
echo.
echo ===============================================================================
echo   Status: ONLINE
echo   Local Dashboard: http://localhost:8000
echo   API Documentation: http://localhost:8000/docs
echo   Press CTRL+C in this window to stop the server anytime.
echo ===============================================================================
echo.

:: Open browser after a brief delay
start "" cmd /c "ping 127.0.0.1 -n 3 >nul && start http://localhost:8000"

:: Launch FastAPI backend (serving both API and prebuilt static frontend)
".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] GitPulse Server exited with an error.
    pause
)
