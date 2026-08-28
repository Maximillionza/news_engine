@echo off
REM Removes the "NewsEngineStartup" task registered by
REM scripts\install_startup_task.bat. Does not stop any already-running
REM engine windows — close those (or Ctrl-C) separately.
schtasks /delete /tn "NewsEngineStartup" /f
