@echo off
REM ============================================================================
REM BioNexus MVP - First Time Setup for Windows
REM Creates venv, installs packages, and initializes database
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║            BioNexus MVP - Initial Setup (Windows)              ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check Python
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found! Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo ✓ Python found
echo.

REM Check Node.js
echo 🔍 Checking Node.js installation...
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js not found! Please install from https://nodejs.org/
    echo Download the LTS version
    pause
    exit /b 1
)
echo ✓ Node.js found
echo.

REM Backend Setup
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                      BACKEND SETUP                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

cd bionexus-platform\backend

REM Create venv
echo 📦 Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ℹ️  Virtual environment already exists
)
echo.

REM Activate venv and install packages
echo 📥 Installing Python packages...
call .\venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo ✓ Packages installed
echo.

REM Apply migrations
echo 🗄️  Applying database migrations...
python manage.py migrate --run-syncdb
echo ✓ Migrations applied
echo.

REM Create test user
echo 👤 Creating test user (demo_user)...
python manage.py shell << EOF
from core.models import Tenant, User
from django.db import IntegrityError

try:
    # Check if tenant exists
    tenant = Tenant.objects.filter(slug='demo-lab').first()
    if not tenant:
        tenant = Tenant.objects.create(name="Demo Lab", slug="demo-lab")
        print("✓ Tenant created")
    else:
        print("ℹ️  Tenant already exists")

    # Check if user exists
    user = User.objects.filter(username='demo_user').first()
    if not user:
        user = User.objects.create_user(
            username='demo_user',
            email='demo@lab.local',
            password='DemoPassword123!',
            tenant=tenant
        )
        print("✓ User created")
    else:
        print("ℹ️  User already exists")

except Exception as e:
    print(f"⚠️  Error: {e}")
EOF
echo.

REM Frontend Setup
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                      FRONTEND SETUP                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

cd ..\..\bionexus-platform\frontend

echo 📥 Installing Node.js packages (this may take a minute)...
call npm install
echo ✓ Packages installed
echo.

REM Success
cd ..\..

echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   ✅ SETUP COMPLETE!                           ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🎉 You're ready to go!
echo.
echo 📝 Next steps:
echo   1. Run: RUN.bat (to start the application)
echo   2. Open: http://localhost:3000
echo   3. Login with:
echo      • Username: demo_user
echo      • Password: DemoPassword123!
echo.
echo 📚 Documentation:
echo   • DOCUMENTATION.md  - Complete guide
echo   • QUICK_START.md    - Quick reference
echo   • WINDOWS_SETUP.md  - Windows-specific help
echo.
pause
