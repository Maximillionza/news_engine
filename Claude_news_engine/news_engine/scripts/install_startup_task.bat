@echo off
REM OPTIONAL — only needed if you want the news engine to start itself at
REM login/reboot, without you having to double-click run_engine.bat by
REM hand. Registers a Windows Task Scheduler task ("NewsEngineStartup")
REM that runs run_engine.bat when you log in. Uses schtasks.exe, built
REM into Windows — nothing downloaded, nothing installed.
REM
REM run_engine.bat itself only needs to fire ONCE per boot — it launches
REM the two _restart_loop.bat windows, which then loop forever on their
REM own (see run_engine.bat / _restart_loop.bat). This task is just the
REM "run that once at login" trigger.
REM
REM This is a STANDING change to this machine (it persists across
REM reboots until removed) — run it yourself when you actually want that,
REM don't assume it's already active. Safe and idempotent: rerunning this
REM overwrites the same task (/F), doesn't duplicate it.
REM
REM To remove: scripts\uninstall_startup_task.bat  (or Task Scheduler GUI
REM   -> Task Scheduler Library -> NewsEngineStartup -> Delete)
setlocal
set REPO_ROOT=%~dp0..
set SCRIPT_PATH=%REPO_ROOT%\scripts\run_engine.bat

schtasks /create /tn "NewsEngineStartup" /tr "\"%SCRIPT_PATH%\"" /sc onlogon /rl limited /f

if %ERRORLEVEL%==0 (
    echo Installed. "NewsEngineStartup" will run run_engine.bat at your next login.
    echo To start it right now without logging out/in: schtasks /run /tn "NewsEngineStartup"
    echo To remove it later: scripts\uninstall_startup_task.bat
) else (
    echo FAILED to register the task — see the error above.
)
