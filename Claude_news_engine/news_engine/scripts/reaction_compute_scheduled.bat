@echo off
REM Runs compute_release_reactions.py for the Stats > Market reaction tab.
REM   reaction_compute_scheduled.bat            -> --incremental (judges new USD releases)
REM   reaction_compute_scheduled.bat baselines  -> --incremental --refresh-baselines (monthly)
REM Registered by scripts/register_reaction_tasks.ps1. Both DB paths are passed explicitly.
REM Releases younger than 10 minutes, or whose +5 min bar is not published yet, are left for the next run.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set MODE=--incremental
if /i "%1"=="baselines" set MODE=--incremental --refresh-baselines
echo [%DATE% %TIME%] reaction compute %MODE% starting >> scripts\reaction_compute_scheduled.log
python scripts\compute_release_reactions.py %MODE% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db >> scripts\reaction_compute_scheduled.log 2>&1
echo [%DATE% %TIME%] reaction compute finished (exit %ERRORLEVEL%) >> scripts\reaction_compute_scheduled.log
