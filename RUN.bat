@echo off
REM ============================================================================
REM BioNexus MVP - Launcher for Windows
REM Auto-pulls latest code, then starts Backend + Frontend
REM ============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   BioNexus MVP - Starting...                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if we're in the right directory
if not exist "bionexus-platform" (
    echo ❌ ERROR: Run this from D:\Projects\BioNexus-mvp\
    pause
    exit /b 1
)

REM ── AUTO GIT PULL ──────────────────────────────────────────────────────────
echo 🔄 Pulling latest code from GitHub...
git pull origin claude/review-mvp-code-AnsTT
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Git pull failed - continuing with local code
) else (
    echo ✅ Code is up to date!
)
echo.

REM ── INSTALL NEW PACKAGES IF ANY ────────────────────────────────────────────
echo 📦 Checking backend packages...
call bionexus-platform\backend\venv\Scripts\activate.bat 2>nul
pip install -r bionexus-platform\backend\requirements.txt -q
echo ✅ Backend packages ready
echo.

echo 📦 Checking frontend packages...
cd bionexus-platform\frontend
call npm install --silent 2>nul
cd ..\..
echo ✅ Frontend packages ready
echo.

REM ── START BACKEND ──────────────────────────────────────────────────────────
echo 🔧 Starting Backend Django on http://localhost:8000 ...
start "BioNexus Backend" cmd /k "cd bionexus-platform\backend && .\venv\Scripts\activate && python manage.py runserver"
timeout /t 3 /nobreak >nul

REM ── START FRONTEND ─────────────────────────────────────────────────────────
echo 🎨 Starting Frontend React on http://localhost:5173 ...
start "BioNexus Frontend" cmd /k "cd bionexus-platform\frontend && npm start"

REM ── OPEN BROWSER ───────────────────────────────────────────────────────────
echo.
echo 🌐 Opening browser in 8 seconds...
timeout /t 8 /nobreak >nul
start http://localhost:5173

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                  ✅ BioNexus MVP is Running!                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:5173
echo.
echo   Login:     demo_user / DemoPassword123!
echo.
echo   🔄 Code auto-updates every time you run RUN.bat
echo   ⚠️  Keep both terminals open!
echo.
