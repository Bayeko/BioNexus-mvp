@echo off
setlocal enabledelayedexpansion

REM ── Force run from the right directory ─────────────────────────────────────
cd /d "%~dp0"

title BioNexus MVP Launcher
cls

echo.
echo  ============================================================
echo   BioNexus MVP - Lancement automatique
echo  ============================================================
echo.

REM ── STEP 1: Git pull ───────────────────────────────────────────────────────
echo [1/5] Recuperation du dernier code...
git pull origin claude/review-mvp-code-AnsTT >nul 2>&1
echo       OK - Code a jour
echo.

REM ── STEP 2: Setup venv ─────────────────────────────────────────────────────
echo [2/5] Preparation du backend Python...
if not exist "bionexus-platform\backend\venv\Scripts\activate.bat" (
    echo       Creation de l'environnement Python...
    python -m venv bionexus-platform\backend\venv
)
call bionexus-platform\backend\venv\Scripts\activate.bat
pip install -r bionexus-platform\backend\requirements.txt -q --no-warn-script-location
echo       OK - Backend pret
echo.

REM ── STEP 3: Apply migrations ───────────────────────────────────────────────
echo [3/5] Verification de la base de donnees...
cd bionexus-platform\backend
python manage.py migrate --run-syncdb >nul 2>&1
python create_demo_user.py
cd ..\..
echo       OK - Base de donnees prete
echo.

REM ── STEP 4: NPM install ────────────────────────────────────────────────────
echo [4/5] Preparation du frontend React...
cd bionexus-platform\frontend
call npm install --silent >nul 2>&1
cd ..\..
echo       OK - Frontend pret
echo.

REM ── STEP 5: Start servers ──────────────────────────────────────────────────
echo [5/5] Demarrage des serveurs...

REM Kill old processes on ports 8000 and 5173
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" 2^>nul') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

REM Start Django backend
start "BioNexus - Backend Django" cmd /k "cd /d %~dp0bionexus-platform\backend && call venv\Scripts\activate && python manage.py runserver && pause"

REM Wait for Django to be ready
timeout /t 4 /nobreak >nul

REM Start React frontend
start "BioNexus - Frontend React" cmd /k "cd /d %~dp0bionexus-platform\frontend && npm start && pause"

REM Wait for Vite to compile
echo.
echo  Demarrage en cours, patientez...
timeout /t 10 /nobreak >nul

REM Open browser
start "" "http://localhost:5173"

echo.
echo  ============================================================
echo   OK - BioNexus est lance!
echo  ============================================================
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo.
echo   Login    : demo_user
echo   Password : DemoPassword123!
echo.
echo   GARDEZ LES 2 TERMINAUX OUVERTS!
echo.
echo  ============================================================
echo.
pause
