# alerting/scripts/register_reality_check_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/reality_check.py
# once a week. Run this once from an elevated PowerShell prompt.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$PythonPath`" -m alerting.reality_check >> `"$ProjectRoot\alerting\reality_check.log`" 2>&1" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockRealityCheck" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly reality check comparing shock-alert severity to realized price moves (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockRealityCheck'"
