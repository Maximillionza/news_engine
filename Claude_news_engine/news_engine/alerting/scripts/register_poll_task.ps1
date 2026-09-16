# alerting/scripts/register_poll_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/poll_once.py
# every 2 minutes indefinitely. Run this once from an elevated PowerShell
# prompt after Task 8 is committed. Adjust $PythonPath/$ProjectRoot if
# your environment differs.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
# NOTE: the real python.exe path now lives inside poll_once_hidden.vbs
# itself (WScript.Shell.Run has no shell variables of its own) -- if
# python's location ever changes, update it there too, not just here.

# 2026-09-16 fix: powershell.exe -WindowStyle Hidden is a well-known
# unreliable flag -- it still creates and briefly shows a console window
# before the hidden style applies, so every 2-minute run flashed a
# window on screen and stole focus for an instant (user-reported: a
# popup appearing/disappearing that also caused erratic mouse movement).
# Routed through poll_once_hidden.vbs instead -- WScript.Shell.Run's
# window-style argument of 0 is reliably invisible (same fix already
# proven for NewsEngine_OutcomeConfirm, see
# scripts/confirm_outcomes_scheduled.vbs). The original nested-quoting
# fix this replaced (cmd.exe /c's double-quote parsing bug, 2026-09-16)
# is preserved inside the .vbs's own cmd invocation, not lost.
$VbsPath = Join-Path $PSScriptRoot "poll_once_hidden.vbs"
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$VbsPath`"" -WorkingDirectory $ProjectRoot
# [TimeSpan]::MaxValue is rejected by Task Scheduler's XML schema (its
# Duration element has a much smaller valid range) -- found live on first
# real registration attempt, 2026-09-15. 10 years is comfortably
# "indefinite" for practical purposes and well within the valid range.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

# -Force added 2026-09-16 so this script can be re-run to apply the
# hidden-launcher fix above to an already-registered task, instead of
# needing a separate Unregister-ScheduledTask step first.
Register-ScheduledTask -TaskName "NewsEngine_ShockPoll" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Polls free RSS sources every 2 minutes for real-time news-shock alerting (news_engine/alerting)." -Force

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockPoll'"
