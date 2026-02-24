@echo off
REM ============================================================================
REM BioNexus MVP - Launcher for Windows
REM Starts both Backend (Django) and Frontend (React) simultaneously
REM ============================================================================

REM Check if we're in the right directory
if not exist "bionexus-platform" (
    echo.
    echo ❌ ERROR: BioNexus folder not found!
    echo Please run this script from the BioNexus-mvp root directory
    echo.
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   BioNexus MVP - Starting...                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Colors and messages
echo 📦 Preparing backend and frontend...
echo.

REM Start Backend (Terminal 1)
echo 🔧 Starting Backend Django (Terminal 1)...
start "BioNexus Backend" cmd /k "cd bionexus-platform\backend && python -m venv venv >nul 2>&1 || echo venv exists... && .\venv\Scripts\activate && python manage.py runserver"

REM Wait a bit for backend to start
timeout /t 3 /nobreak

REM Start Frontend (Terminal 2)
echo 🎨 Starting Frontend React (Terminal 2)...
start "BioNexus Frontend" cmd /k "cd bionexus-platform\frontend && npm install >nul 2>&1 || echo npm packages installed... && npm start"

REM Open browser
echo.
echo 🌐 Opening browser...
timeout /t 5 /nobreak
start http://localhost:3000

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║              ✅ BioNexus MVP is Starting!                      ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 📊 What's happening:
echo   • Terminal 1 (Backend):   Django running on http://localhost:8000
echo   • Terminal 2 (Frontend):  React running on http://localhost:3000
echo   • Browser:                Automatically opened http://localhost:3000
echo.
echo 👤 Login with:
echo   Username: demo_user
echo   Password: DemoPassword123!
echo.
echo ⚠️  IMPORTANT NOTES:
echo   • Keep both terminals open (don't close them)
echo   • Changes to code will auto-reload in browser
echo   • Backend changes might require restart
echo   • If something breaks, check the terminal output
echo.
echo 🛑 To stop everything:
echo   1. Close Terminal 1 (Backend)
echo   2. Close Terminal 2 (Frontend)
echo   3. Or press Ctrl+C in each terminal
echo.
