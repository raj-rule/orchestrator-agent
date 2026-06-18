@echo off
title CriticAI Startup Orchestrator
echo ===================================================
echo   CriticAI - Bootstrapping and Launching Services
echo ===================================================

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH. Please install Python 3.10+.
    pause
    exit /b
)

:: Recreate venv if needed
if not exist venv\Scripts\python.exe (
    echo Virtual environment not found. Re-creating...
    python -m venv venv
)

:: Install requirements
echo Installing backend dependencies...
call venv\Scripts\pip.exe install -r requirements.txt

:: Install frontend dependencies
echo Checking frontend dependencies...
cd swarm-ui
if not exist node_modules (
    echo node_modules not found. Installing package dependencies...
    call npm install
)
cd ..

:: Start servers concurrently
echo Starting FastAPI Backend and React Frontend...
start "CriticAI Backend" cmd /c "venv\Scripts\python.exe server.py"
start "CriticAI Frontend" cmd /c "cd swarm-ui && npm run dev"

echo ===================================================
echo   Servers started! 
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:5173
echo ===================================================
pause
