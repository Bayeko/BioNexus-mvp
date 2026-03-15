@echo off
title BioNexus - Equipment Simulator
color 0E

echo ============================================================
echo   BIONEXUS EQUIPMENT SIMULATOR
echo ============================================================
echo.
echo   Make sure RUN.bat is already running (backend must be up).
echo.
echo   === LIVE DEMO (real-time, for client demos) ===
echo   L. LIVE DEMO - All instruments (fresh start + real-time)
echo   F. FAST LIVE DEMO - 2x speed (fresh start)
echo.
echo   === SINGLE INSTRUMENT (live, fresh start) ===
echo   S. Spectrophotometer
echo   P. PCR Machine
echo   R. Plate Reader
echo   H. pH Meter
echo   A. HPLC
echo.
echo   === OTHER ===
echo   1. Full Batch (all instruments, instant, no clean)
echo   C. Clean all demo data (reset to zero)
echo   0. Exit
echo.

set /p choice="  Your choice: "

if /i "%choice%"=="L" goto :live_all
if /i "%choice%"=="F" goto :live_fast
if /i "%choice%"=="S" goto :live_spectro
if /i "%choice%"=="P" goto :live_pcr
if /i "%choice%"=="R" goto :live_plate
if /i "%choice%"=="H" goto :live_ph
if /i "%choice%"=="A" goto :live_hplc
if "%choice%"=="1" goto :batch_all
if /i "%choice%"=="C" goto :clean
if "%choice%"=="0" goto :exit
echo   Invalid choice.
goto :done

:live_all
echo.
echo   Cleaning data + starting LIVE DEMO...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --no-prompt"
goto :done

:live_fast
echo.
echo   Cleaning data + starting FAST LIVE DEMO (2x speed)...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --speed 2 --no-prompt"
goto :done

:live_spectro
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --equipment spectrophotometer --no-prompt"
goto :done

:live_pcr
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --equipment pcr --no-prompt"
goto :done

:live_plate
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --equipment plate_reader --no-prompt"
goto :done

:live_ph
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --equipment ph_meter --no-prompt"
goto :done

:live_hplc
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean --live --equipment hplc --no-prompt"
goto :done

:batch_all
echo.
echo   Running full batch demo (no clean)...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --auto"
goto :done

:clean
echo.
echo   Cleaning all demo data...
wsl -d Ubuntu bash -c "cd /home/messa/BioNexus-mvp/bionexus-platform/backend && source venv/bin/activate && python simulate_equipment.py --clean"
goto :done

:exit
echo   Bye!
goto :done

:done
echo.
echo   Done! Check http://localhost:3000 for results.
echo   Press any key to close...
pause >nul
