@echo off
title BioNexus - First-Time Setup
color 0B

echo ============================================================
echo   BIONEXUS - First-Time Setup
echo ============================================================
echo.
echo   This installs everything needed in WSL Ubuntu.
echo   You only need to run this ONCE.
echo.

echo [1/4] Creating Python virtual environment...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && rm -rf venv && python3 -m venv --without-pip venv && source venv/bin/activate && curl -sS https://bootstrap.pypa.io/get-pip.py | python3 && echo '  [OK] venv + pip ready'"

echo [2/4] Installing Python dependencies...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && pip install -q -r requirements.txt && pip install -q django-filter && echo '  [OK] All packages installed'"

echo [3/4] Running database migrations...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python manage.py migrate --run-syncdb 2>&1 | tail -3 && echo '  [OK] Database ready'"

echo [4/4] Creating demo user...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python create_demo_user.py"

echo.
echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo   You can now use:
echo     RUN.bat       - Start backend + frontend
echo     SIMULATE.bat  - Run equipment simulator
echo     STOP.bat      - Stop everything
echo.
echo   Press any key to close...
pause >nul
