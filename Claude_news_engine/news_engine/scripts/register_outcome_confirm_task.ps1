# scripts/register_outcome_confirm_task.ps1
#
# (Re)registers the "NewsEngine_OutcomeConfirm" Windows Scheduled Task —
# runs confirm_outcomes_scheduled.bat every 15 minutes, indefinitely,
# starting from whenever this script is run.
#
# 2026-09-15 fix: the task used to call cmd.exe /c ...bat directly, which
# pops a visible console window on screen every 15 minutes even though
# the batch file already redirects all its own output to
# confirm_outcomes_scheduled.log — nothing in that window was ever worth
# looking at, it just interrupted whatever was on screen. Action is now
# wscript.exe //B confirm_outcomes_scheduled.vbs — a tiny hidden-window
# launcher (see that file) that runs the exact same batch file with zero
# window. Re-run this script any time the task needs re-registering
# (e.g. after moving this repo to a different path).
#
# Run this from an elevated or normal PowerShell prompt as the user who
# should own the task (Masoodt) — no admin rights required for a
# per-user task at Limited run level.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$vbsPath = Join-Path $PSScriptRoot "confirm_outcomes_scheduled.vbs"

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B `"$vbsPath`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
$settings = New-ScheduledTaskSettingsSet
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "NewsEngine_OutcomeConfirm" `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Runs scripts/confirm_backtest_outcomes.py --auto --list every 15 minutes via a hidden-window launcher (confirm_outcomes_scheduled.vbs) so it never pops a console window on screen." `
    -Force

Write-Host "Registered NewsEngine_OutcomeConfirm -> wscript.exe //B $vbsPath (every 15 min, hidden window)"
