@echo off
title BioNexus - Equipment Simulator
color 0E

echo ============================================================
echo   BIONEXUS EQUIPMENT SIMULATOR
echo ============================================================
echo.
echo   Make sure RUN.bat is already running (backend must be up).
echo.
echo   1. Full Demo (all 5 instruments, auto)
echo   2. Interactive Menu (choose instrument)
echo   3. Spectrophotometer only
echo   4. PCR Machine only
echo   5. Plate Reader only
echo   6. pH Meter only
echo   7. HPLC only
echo   0. Exit
echo.

set /p choice="  Your choice [0-7]: "

if "%choice%"=="1" (
    echo.
    echo   Running full demo...
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --auto"
) else if "%choice%"=="2" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py"
) else if "%choice%"=="3" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --equipment spectrophotometer"
) else if "%choice%"=="4" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --equipment pcr"
) else if "%choice%"=="5" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --equipment plate_reader"
) else if "%choice%"=="6" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --equipment ph_meter"
) else if "%choice%"=="7" (
    wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --equipment hplc"
) else if "%choice%"=="0" (
    echo   Bye!
    goto :end
) else (
    echo   Invalid choice.
)

echo.
echo   Done! Check http://localhost:3000 for results.
:end
echo   Press any key to close...
pause >nul
