# alerting/scripts/register_poll_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/poll_once.py
# every 2 minutes indefinitely. Run this once from an elevated PowerShell
# prompt after Task 8 is committed. Adjust $PythonPath/$ProjectRoot if
# your environment differs.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

# cmd.exe /c with two separately-quoted paths (python.exe AND the log
# path) hit a real, reproducible Windows quoting bug on first live
# registration, 2026-09-16: Task Scheduler's actual process launch failed
# (LastTaskResult=1) on every run, before the log redirection even created
# a file -- yet the identical string worked fine run manually through an
# interactive shell, which re-quotes differently. powershell.exe's own
# call operator + *>> (redirect all streams, append) avoids the nested
# double-quote parsing entirely and is the reliable fix.
$PollScriptArgs = "-NoProfile -WindowStyle Hidden -Command `"& '$PythonPath' -m alerting.poll_once *>> '$ProjectRoot\alerting\poll_once.log'`""
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $PollScriptArgs -WorkingDirectory $ProjectRoot
# [TimeSpan]::MaxValue is rejected by Task Scheduler's XML schema (its
# Duration element has a much smaller valid range) -- found live on first
# real registration attempt, 2026-09-15. 10 years is comfortably
# "indefinite" for practical purposes and well within the valid range.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockPoll" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Polls free RSS sources every 2 minutes for real-time news-shock alerting (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockPoll'"
