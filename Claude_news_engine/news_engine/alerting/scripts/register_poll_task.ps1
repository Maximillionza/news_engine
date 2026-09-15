# alerting/scripts/register_poll_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/poll_once.py
# every 2 minutes indefinitely. Run this once from an elevated PowerShell
# prompt after Task 8 is committed. Adjust $PythonPath/$ProjectRoot if
# your environment differs.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$PythonPath`" -m alerting.poll_once >> `"$ProjectRoot\alerting\poll_once.log`" 2>&1" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration ([TimeSpan]::MaxValue)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockPoll" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Polls free RSS sources every 2 minutes for real-time news-shock alerting (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockPoll'"
