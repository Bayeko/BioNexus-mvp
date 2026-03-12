@echo off
title BioNexus - Stopping All Services
color 0C

echo ============================================================
echo   BIONEXUS - Stopping all services
echo ============================================================
echo.

echo Killing Django backend...
wsl -d Ubuntu bash -c "pkill -f 'manage.py runserver' 2>/dev/null"
taskkill /FI "WINDOWTITLE eq BioNexus Backend" /F >nul 2>&1

echo Killing React frontend...
wsl -d Ubuntu bash -c "pkill -f 'vite' 2>/dev/null; pkill -f 'npm' 2>/dev/null"
taskkill /FI "WINDOWTITLE eq BioNexus Frontend" /F >nul 2>&1

echo.
echo   All services stopped.
echo   Press any key to close...
pause >nul
