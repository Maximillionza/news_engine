' scripts/reaction_compute_scheduled.vbs
'
' Hidden-window launcher for reaction_compute_scheduled.bat (same reason as
' confirm_outcomes_scheduled.vbs). Passes its first argument ('baselines' or nothing) through.
Set objShell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, Len(WScript.ScriptFullName) - Len(WScript.ScriptName))
arg = ""
If WScript.Arguments.Count > 0 Then arg = " " & WScript.Arguments(0)
objShell.Run """" & scriptDir & "reaction_compute_scheduled.bat""" & arg, 0, True
