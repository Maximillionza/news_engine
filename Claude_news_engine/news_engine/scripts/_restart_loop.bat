@echo off
REM Internal helper for run_engine.bat — restarts %1 (a python script path,
REM relative to the repo root) whenever it exits, for any reason (crash,
REM unhandled exception outside the process's own try/except, taskkill).
REM Not meant to be run directly.
setlocal

:loop
echo [restart-loop] %DATE% %TIME% — starting: python %1
python %1
set EXITCODE=%ERRORLEVEL%
REM Exit code 3 = ops.single_instance found another copy already running
REM (B4 O8). Restarting would just loop every 5s, so stop here.
if "%EXITCODE%"=="3" (
    echo [restart-loop] %DATE% %TIME% — %1 is already running in another window; not restarting. This window can be closed.
    exit /b 3
)
echo [restart-loop] %DATE% %TIME% — %1 exited (code %EXITCODE%^). Restarting in 5s... (close this window or Ctrl-C to stop)
REM ping-based delay, not `timeout /t` — timeout.exe refuses to run
REM ("Input redirection is not supported") when stdin isn't a real
REM console, which can happen depending on how this .bat gets launched.
REM 6 pings at the default 1s spacing = ~5s.
ping -n 6 127.0.0.1 >nul
goto loop
