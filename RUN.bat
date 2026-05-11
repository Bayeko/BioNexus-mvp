@echo off
title BioNexus - Backend + Frontend
color 0A

echo ============================================================
echo   BIONEXUS MVP - Starting Backend + Frontend
echo ============================================================
echo.

:: --- Backend (Django on port 8000) ---
echo [1/4] Setting up Python virtual environment...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && ([ -d venv ] || (python3 -m venv --without-pip venv && source venv/bin/activate && curl -sS https://bootstrap.pypa.io/get-pip.py | python3)) && source venv/bin/activate && pip install -q -r requirements.txt && pip install -q django-filter 2>/dev/null"

echo [2/4] Running migrations + creating demo user...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python manage.py migrate --run-syncdb 2>&1 | tail -1 && python create_demo_user.py"

echo [3/4] Starting Django backend on port 8000...
start "BioNexus Backend" wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"

:: --- Frontend (React/Vite on port 3000) ---
echo [4/4] Starting React frontend on port 3000...
start "BioNexus Frontend" wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/frontend && npm install --silent 2>/dev/null && npm start"

echo.
echo ============================================================
echo   BIONEXUS IS STARTING
echo ============================================================
echo.
echo   Backend:  http://localhost:8000/api/
echo   Frontend: http://localhost:3000
echo   Login:    demo_user / DemoPassword123!
echo.
echo   Waiting 5 seconds then opening browser...
echo ============================================================

timeout /t 5 /nobreak >nul
start http://localhost:3000

echo.
echo   Both servers are running in separate windows.
echo   Use STOP.bat to shut everything down.
echo   Press any key to close this window...
pause >nul
