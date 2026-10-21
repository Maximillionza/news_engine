@echo off
REM Runs capture_nowcast_from_cleveland.py: writes the formula Tier 1 row on the dashboard (B3).
REM   tier1_capture_scheduled.bat          -> --window-hours 48  (daily catch-up)
REM   tier1_capture_scheduled.bat weekly   -> --window-hours 192 (Monday: covers the whole week ahead)
REM Registered by scripts/register_tier1_tasks.ps1. Both DB paths are passed explicitly.
REM Runs through ops.run_job (SAST-timestamped, size-capped log; exit code recorded for the health check).
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set WINDOW=48
set JOB=tier1_capture_daily
if /i "%1"=="weekly" set WINDOW=192
if /i "%1"=="weekly" set JOB=tier1_capture_weekly
python -m ops.run_job --job %JOB% --log scripts\tier1_capture_scheduled.log -- scripts\capture_nowcast_from_cleveland.py --window-hours %WINDOW% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db
exit /b %ERRORLEVEL%
