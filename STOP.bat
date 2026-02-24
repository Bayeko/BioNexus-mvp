@echo off
REM ============================================================================
REM BioNexus MVP - Stop all services
REM ============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                 Stopping BioNexus Services...                  ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Kill Python processes (Django)
echo 🔴 Stopping Django Backend...
taskkill /F /IM python.exe /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Django stopped
) else (
    echo ℹ️  Django was not running
)

REM Kill Node processes (React)
echo 🔴 Stopping React Frontend...
taskkill /F /IM node.exe /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ React stopped
) else (
    echo ℹ️  React was not running
)

REM Kill cmd windows
taskkill /F /FI "WINDOWTITLE eq BioNexus*" /T >nul 2>&1

echo.
echo ✅ All services stopped!
echo.
timeout /t 2 /nobreak
