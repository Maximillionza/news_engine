' alerting/scripts/reality_check_hidden.vbs
'
' Hidden-window launcher for alerting/reality_check.py, run weekly by the
' NewsEngine_ShockRealityCheck scheduled task (see
' register_reality_check_task.ps1). Same fix as poll_once_hidden.vbs --
' powershell.exe -WindowStyle Hidden still flashes a console window
' briefly before hiding it; this task runs far less often (weekly) so it
' was never the main disruption, but it had the identical latent bug and
' is fixed the same way while the pattern is being applied anyway.
Set objShell = CreateObject("WScript.Shell")
' 2026-09-26: repointed to the dedicated news-engine worktree, same
' reasoning as poll_once_hidden.vbs's own 2026-09-26 comment.
projectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine"
pythonPath = "C:\Python314\python.exe"
logPath = projectRoot & "\alerting\reality_check.log"
cmd = "cmd /c cd /d """ & projectRoot & """ && """ & pythonPath & """ -m alerting.reality_check >> """ & logPath & """ 2>&1"
objShell.Run cmd, 0, True
