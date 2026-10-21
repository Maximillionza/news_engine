@echo off
REM Runs capture_nowcast_from_cleveland.py: writes the formula Tier 1 row on the dashboard (B3).
REM   tier1_capture_scheduled.bat          -> --window-hours 48  (daily catch-up)
REM   tier1_capture_scheduled.bat weekly   -> --window-hours 192 (Monday: covers the whole week ahead)
REM Registered by scripts/register_tier1_tasks.ps1. Both DB paths are passed explicitly.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set WINDOW=48
if /i "%1"=="weekly" set WINDOW=192
echo [%DATE% %TIME%] tier1 capture --window-hours %WINDOW% starting >> scripts\tier1_capture_scheduled.log
python scripts\capture_nowcast_from_cleveland.py --window-hours %WINDOW% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db >> scripts\tier1_capture_scheduled.log 2>&1
echo [%DATE% %TIME%] tier1 capture finished (exit %ERRORLEVEL%) >> scripts\tier1_capture_scheduled.log
