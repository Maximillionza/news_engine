@echo off
REM Starts the whole news engine: the dashboard (webapp/app.py) AND the
REM article-based accumulator (scripts/run_accumulator.py) — two genuinely
REM separate processes by design (see run_accumulator.py's docstring), but
REM in practice both need to be running for the dashboard to show anything
REM current. Confirmed live 2026-08-19: the accumulator was simply not
REM running for most of a session while the dashboard kept serving stale
REM data with nothing visibly wrong — this script (and the
REM accumulator_staleness_seconds field it makes easier to trust) exists
REM so that stops happening.
REM
REM Each process runs in its own window under _restart_loop.bat, so a
REM crash (or the Unicode console crash fixed 2026-08-19 — belt-and-
REM suspenders even though that's fixed at the source now) restarts it
REM automatically instead of silently going down.
REM
REM Usage: double-click this file, or run it from a terminal:
REM     scripts\run_engine.bat
REM To stop: close both spawned windows (or Ctrl-C in each).
cd /d "%~dp0.."

start "News Engine - Dashboard (port 5001)" cmd /k "scripts\_restart_loop.bat webapp\app.py"
start "News Engine - Article Accumulator" cmd /k "scripts\_restart_loop.bat scripts\run_accumulator.py"

echo Started both processes in their own windows.
echo Dashboard:   http://127.0.0.1:5001/
echo Accumulator: see its own window for live scoring output.
