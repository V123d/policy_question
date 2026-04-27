@echo off
title Policy QA Agent - Restart

echo ========================================
echo   Policy QA Agent - Restart All Services
echo ========================================
echo.

call "%~dp0stop.bat"

echo.
echo Waiting 3 seconds before restarting...
timeout /t 3 /nobreak >nul

call "%~dp0start.bat"
