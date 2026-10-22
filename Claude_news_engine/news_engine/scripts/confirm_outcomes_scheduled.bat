@echo off
REM Runs confirm_backtest_outcomes.py --auto --list on a schedule (see
REM scripts/register_outcome_confirm_task.ps1 for the Windows Scheduled
REM Task that calls this). --list means no interactive prompts -- clear
REM Dukascopy moves get auto-confirmed; anything ambiguous is left
REM exactly where it was, for the next manual `python
REM scripts\confirm_backtest_outcomes.py` (no --list) run to resolve.
REM
REM Not meant to be double-clicked routinely -- registered as a recurring
REM Scheduled Task instead. Runs through ops.run_job: output goes to the log with SAST
REM timestamps (1 MB, one backup) and the exit code is recorded for the health check.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
python -m ops.run_job --job outcome_confirm --log scripts\confirm_outcomes_scheduled.log -- scripts\confirm_backtest_outcomes.py --auto --list
exit /b %ERRORLEVEL%
