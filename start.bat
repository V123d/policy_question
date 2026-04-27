@echo off
title Policy QA Agent - Startup

echo ========================================
echo   Policy QA Agent - One-Click Startup
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python virtual environment...
if not exist "backend\venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found at backend\venv
    echo Please run: cd backend ^&^& python -m venv venv
    pause
    exit /b 1
)

echo [2/3] Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo [3/3] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo INFO: node_modules not found. Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

echo.
echo ========================================
echo   Starting Backend (port 8000)...
echo ========================================
start "Policy QA Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   Starting Frontend (port 3000)...
echo ========================================
start "Policy QA Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo.
echo   Services are starting in separate windows:
echo.
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:3000
echo   - API Docs: http://localhost:8000/docs
echo.
echo   Press any key to close this window...
echo ========================================
pause >nul
