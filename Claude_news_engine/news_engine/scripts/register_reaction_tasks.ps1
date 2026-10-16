# scripts/register_reaction_tasks.ps1
#
# (Re)registers two per-user Windows Scheduled Tasks for the Market reaction tab:
#   NewsEngine_ReactionIncremental - hourly at :20, judges new USD releases (--incremental)
#   NewsEngine_ReactionBaselines   - 1st of each month 03:15, --incremental --refresh-baselines
# Both run reaction_compute_scheduled.bat through the hidden-window VBS launcher and log to
# scripts\reaction_compute_scheduled.log. No admin rights needed. Re-run after moving the repo.

$ErrorActionPreference = "Stop"
$vbsPath = Join-Path $PSScriptRoot "reaction_compute_scheduled.vbs"
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Hourly: first run at the next :20, repeating every hour.
$first = (Get-Date).Date.AddHours((Get-Date).Hour).AddMinutes(20)
if ($first -le (Get-Date)) { $first = $first.AddHours(1) }
$hourly = New-ScheduledTaskTrigger -Once -At $first -RepetitionInterval (New-TimeSpan -Hours 1)
$actionInc = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$vbsPath`""
Register-ScheduledTask -TaskName "NewsEngine_ReactionIncremental" -Action $actionInc -Trigger $hourly `
    -Settings $settings -Principal $principal -Force `
    -Description "Hourly: compute_release_reactions.py --incremental (Stats > Market reaction)." | Out-Null

# Monthly: Register-ScheduledTask has no monthly trigger in Windows PowerShell 5.1, so use schtasks.
$tr = "wscript.exe //B `"$vbsPath`" baselines"
schtasks.exe /Create /F /TN "NewsEngine_ReactionBaselines" /SC MONTHLY /D 1 /ST 03:15 /TR $tr | Out-Null
if ($LASTEXITCODE -ne 0) { throw "schtasks failed to register NewsEngine_ReactionBaselines" }

Write-Host "Registered NewsEngine_ReactionIncremental (hourly at :20) and NewsEngine_ReactionBaselines (monthly, 1st 03:15)"
