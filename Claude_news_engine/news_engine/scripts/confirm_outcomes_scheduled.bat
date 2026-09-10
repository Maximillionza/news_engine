@echo off
REM Runs confirm_backtest_outcomes.py --auto --list on a schedule (see
REM scripts/register_outcome_confirm_task.ps1 for the Windows Scheduled
REM Task that calls this). --list means no interactive prompts -- clear
REM Dukascopy moves get auto-confirmed and, for any CPI/PPI occurrence
REM with a Tier 1 prediction already logged, the tier1_comparisons row
REM gets built automatically too (see confirm_backtest_outcomes.py's
REM _try_record_tier1_comparison hook); anything ambiguous is left
REM exactly where it was, for the next manual `python
REM scripts\confirm_backtest_outcomes.py` (no --list) run to resolve.
REM
REM Not meant to be double-clicked routinely -- registered as a recurring
REM Scheduled Task instead. Logs each run's output for later review.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo [%DATE% %TIME%] confirm_outcomes_scheduled run starting >> scripts\confirm_outcomes_scheduled.log
python scripts\confirm_backtest_outcomes.py --auto --list >> scripts\confirm_outcomes_scheduled.log 2>&1
echo [%DATE% %TIME%] confirm_outcomes_scheduled run finished >> scripts\confirm_outcomes_scheduled.log
