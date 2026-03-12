@echo off
title BioNexus Orchestrator - Stopping

echo ========================================
echo   BioNexus Orchestrator - Stopping...
echo ========================================
echo.

echo Stopping backend server...
wsl.exe -d Ubuntu -- bash -c "[ -f /tmp/bionexus-backend.pid ] && kill \"$(cat /tmp/bionexus-backend.pid)\" 2>/dev/null; rm -f /tmp/bionexus-backend.pid"

echo Stopping dashboard...
wsl.exe -d Ubuntu -- bash -c "[ -f /tmp/bionexus-dashboard.pid ] && kill \"$(cat /tmp/bionexus-dashboard.pid)\" 2>/dev/null; rm -f /tmp/bionexus-dashboard.pid"

echo Cleaning up remaining processes on ports 3737 and 5173...
wsl.exe -d Ubuntu -- bash -c "fuser -k 3737/tcp 2>/dev/null; fuser -k 5173/tcp 2>/dev/null"

echo.
echo   All processes stopped.
echo ========================================
pause
