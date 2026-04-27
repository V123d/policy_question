@echo off
title Policy QA Agent - Stop

echo ========================================
echo   Policy QA Agent - Stop All Services
echo ========================================
echo.

echo Stopping all running services...
echo.

echo [1/2] Stopping Backend (uvicorn)...
taskkill /FI "WINDOWTITLE eq Policy QA Backend*" /T /F >nul 2>&1
if errorlevel 1 (
    echo   - No backend process found.
) else (
    echo   - Backend stopped.
)

echo [2/2] Stopping Frontend (Next.js)...
taskkill /FI "WINDOWTITLE eq Policy QA Frontend*" /T /F >nul 2>&1
if errorlevel 1 (
    echo   - No frontend process found.
) else (
    echo   - Frontend stopped.
)

echo.
echo ========================================
echo   All services stopped.
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
