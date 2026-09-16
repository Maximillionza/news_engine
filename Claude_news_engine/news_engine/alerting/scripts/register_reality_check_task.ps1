# alerting/scripts/register_reality_check_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/reality_check.py
# once a week. Run this once from an elevated PowerShell prompt.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

# Same cmd.exe /c nested-quoting bug found live in register_poll_task.ps1
# on 2026-09-16 (Task Scheduler's real launch failed with LastTaskResult=1
# on every run despite the identical string working fine run manually) --
# fixed preemptively here before this task's first real Sunday run.
$RealityCheckScriptArgs = "-NoProfile -WindowStyle Hidden -Command `"& '$PythonPath' -m alerting.reality_check *>> '$ProjectRoot\alerting\reality_check.log'`""
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $RealityCheckScriptArgs -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockRealityCheck" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly reality check comparing shock-alert severity to realized price moves (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockRealityCheck'"
