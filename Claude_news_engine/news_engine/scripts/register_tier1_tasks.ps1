# scripts/register_tier1_tasks.ps1
#
# (Re)registers two per-user Windows Scheduled Tasks for the Tier 1 capture (B3; B12 adds the Kalshi phase):
#   NewsEngine_Tier1Weekly - Mondays 07:00, tier1_capture_scheduled.bat weekly (--window-hours 192)
#   NewsEngine_Tier1Daily  - every day 07:00, tier1_capture_scheduled.bat (--window-hours 48)
# Both run through the hidden-window VBS launcher and log to scripts\tier1_capture_scheduled.log; the bat runs
# scripts\capture_tier1.py (Cleveland formula rows, then Kalshi market-implied rows).
# Times are machine-local (the PC runs SAST). -StartWhenAvailable makes a PC that was asleep at 07:00
# catch up on wake. WakeToRun is deliberately not set (that is the owner's machine setting).
# No admin rights needed. Applied at deploy by the controller; re-run after moving the repo.

$ErrorActionPreference = "Stop"
$vbsPath = Join-Path $PSScriptRoot "tier1_capture_scheduled.vbs"
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 07:00
$weeklyAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$vbsPath`" weekly"
Register-ScheduledTask -TaskName "NewsEngine_Tier1Weekly" -Action $weeklyAction -Trigger $weeklyTrigger `
    -Settings $settings -Principal $principal -Force `
    -Description "Mondays 07:00: capture_tier1.py --window-hours 192 (Tier 1 formula and market-implied rows)." | Out-Null

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At 07:00
$dailyAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$vbsPath`""
Register-ScheduledTask -TaskName "NewsEngine_Tier1Daily" -Action $dailyAction -Trigger $dailyTrigger `
    -Settings $settings -Principal $principal -Force `
    -Description "Daily 07:00: capture_tier1.py --window-hours 48 (Tier 1 formula and market-implied rows)." | Out-Null

Write-Host "Registered NewsEngine_Tier1Weekly (Mondays 07:00) and NewsEngine_Tier1Daily (daily 07:00)"
