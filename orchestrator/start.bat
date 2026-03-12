@echo off
title BioNexus Orchestrator

echo ========================================
echo   BioNexus Orchestrator - Starting...
echo ========================================
echo.

:: Start the backend server in a new window (port 3737)
echo [1/3] Starting backend server...
start "BioNexus Backend" cmd /k wsl.exe -d Ubuntu -- bash -lc "cd ~/BioNexus-mvp/orchestrator && npm run dev"

:: Start the dashboard dev server in a new window (port 5173)
echo [2/3] Starting dashboard...
start "BioNexus Dashboard" cmd /k wsl.exe -d Ubuntu -- bash -lc "cd ~/BioNexus-mvp/orchestrator/dashboard && npm run dev"

:: Wait for servers to boot
echo [3/3] Waiting for servers to start...
timeout /t 8 /nobreak > nul

:: Open dashboard in default browser
echo.
echo   Backend:   http://localhost:3737
echo   Dashboard: http://localhost:5173
echo.
start "" http://localhost:5173

echo ========================================
echo   BioNexus is running!
echo   Close the server windows to shut down.
echo ========================================
