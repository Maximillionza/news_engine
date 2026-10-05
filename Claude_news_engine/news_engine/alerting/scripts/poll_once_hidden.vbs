' alerting/scripts/poll_once_hidden.vbs
'
' Hidden-window launcher for alerting/poll_once.py, run every 2 minutes
' by the NewsEngine_ShockPoll scheduled task (see register_poll_task.ps1).
'
' The task used to call powershell.exe -WindowStyle Hidden directly.
' -WindowStyle Hidden is a well-known unreliable flag on Windows: it
' still creates and briefly shows a console window before applying the
' hidden style, so every 2-minute run flashed a window on screen and
' stole focus for an instant -- at a 2-minute cadence, disruptive enough
' during active work to look "intermittent" (2026-09-16, user-reported:
' a popup appearing/disappearing that also caused erratic mouse
' movement). WScript.Shell.Run's window-style argument of 0 (hidden) is
' the same reliably-invisible mechanism already proven for
' NewsEngine_OutcomeConfirm (see scripts/confirm_outcomes_scheduled.vbs)
' -- routed through cmd.exe here (not straight to python.exe) only
' because cmd's own >> redirection is what actually writes the log file;
' WScript.Shell.Run itself has no shell redirection of its own.
Set objShell = CreateObject("WScript.Shell")
' 2026-09-26: repointed to the dedicated news-engine worktree so this
' scheduled task no longer runs against whatever branch happens to be
' checked out in the shared main repo directory (root cause of a real
' incident where a fix landed on the wrong branch entirely).
projectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine"
pythonPath = "C:\Python314\python.exe"
logPath = projectRoot & "\alerting\poll_once.log"
cmd = "cmd /c cd /d """ & projectRoot & """ && """ & pythonPath & """ -m alerting.poll_once >> """ & logPath & """ 2>&1"
objShell.Run cmd, 0, True
