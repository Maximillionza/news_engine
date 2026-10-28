@echo off
REM Runs capture_tier1.py (B12): phase 1 the Cleveland formula Tier 1 rows (B3), phase 2 the Kalshi
REM market-implied Tier 1 rows (T10); a Cleveland outage does not stop phase 2.
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
python -m ops.run_job --job %JOB% --log scripts\tier1_capture_scheduled.log -- scripts\capture_tier1.py --window-hours %WINDOW% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db
exit /b %ERRORLEVEL%
