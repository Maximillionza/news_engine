@echo off
REM Runs compute_release_reactions.py for the Stats > Market reaction tab.
REM   reaction_compute_scheduled.bat            -> --incremental (judges new USD releases)
REM   reaction_compute_scheduled.bat baselines  -> --incremental --refresh-baselines (monthly)
REM Registered by scripts/register_reaction_tasks.ps1. Both DB paths are passed explicitly.
REM Releases younger than 10 minutes, or whose +5 min bar is not published yet, are left for the next run.
REM Runs through ops.run_job (SAST-timestamped, size-capped log; exit code recorded for the health check).
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set MODE=--incremental
set JOB=reaction_incremental
if /i "%1"=="baselines" set MODE=--incremental --refresh-baselines
if /i "%1"=="baselines" set JOB=reaction_baselines
python -m ops.run_job --job %JOB% --log scripts\reaction_compute_scheduled.log -- scripts\compute_release_reactions.py %MODE% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db
exit /b %ERRORLEVEL%
