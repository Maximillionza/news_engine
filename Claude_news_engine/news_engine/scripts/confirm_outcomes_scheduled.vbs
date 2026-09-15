' scripts/confirm_outcomes_scheduled.vbs
'
' Hidden-window launcher for confirm_outcomes_scheduled.bat. The batch
' file itself already redirects all its output to
' scripts\confirm_outcomes_scheduled.log -- there is nothing on screen
' worth showing -- but Task Scheduler still opens a visible cmd.exe
' console every time it fires the task directly, popping up over
' whatever the user is doing every 15 minutes. WScript.Shell.Run's
' window-style argument of 0 (hidden) is the standard fix: the batch
' file still runs exactly the same, just with no window at all.
'
' Registered as this task's actual Action (see
' register_outcome_confirm_task.ps1) instead of cmd.exe /c ...bat
' directly. The third argument (True) makes this wait for the batch
' file to finish before exiting, so Task Scheduler's own run history
' still reflects the real duration and exit code.
Set objShell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, Len(WScript.ScriptFullName) - Len(WScript.ScriptName))
objShell.Run """" & scriptDir & "confirm_outcomes_scheduled.bat""", 0, True
