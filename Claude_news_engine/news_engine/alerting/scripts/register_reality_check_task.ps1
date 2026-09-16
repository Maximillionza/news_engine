# alerting/scripts/register_reality_check_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/reality_check.py
# once a week. Run this once from an elevated PowerShell prompt.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
# NOTE: the real python.exe path now lives inside reality_check_hidden.vbs
# itself (WScript.Shell.Run has no shell variables of its own) -- if
# python's location ever changes, update it there too, not just here.

# 2026-09-16 fix: same powershell.exe -WindowStyle Hidden flash bug found
# and fixed in register_poll_task.ps1 (that task's 2-minute cadence made
# it the disruptive one; this weekly task had the identical latent bug,
# fixed here the same way while the pattern is being applied anyway) --
# routed through reality_check_hidden.vbs, same reliably-invisible
# WScript.Shell.Run(...,0,True) mechanism already proven for
# NewsEngine_OutcomeConfirm. The original nested-quoting fix this
# replaced (cmd.exe /c's double-quote parsing bug, 2026-09-16) is
# preserved inside the .vbs's own cmd invocation, not lost.
$VbsPath = Join-Path $PSScriptRoot "reality_check_hidden.vbs"
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$VbsPath`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

# -Force added 2026-09-16, same reason as register_poll_task.ps1.
Register-ScheduledTask -TaskName "NewsEngine_ShockRealityCheck" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly reality check comparing shock-alert severity to realized price moves (news_engine/alerting)." -Force

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockRealityCheck'"
