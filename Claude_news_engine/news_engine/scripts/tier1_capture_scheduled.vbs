' scripts/tier1_capture_scheduled.vbs
'
' Hidden-window launcher for tier1_capture_scheduled.bat (same reason as
' reaction_compute_scheduled.vbs). Passes its first argument ('weekly' or nothing) through.
Set objShell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, Len(WScript.ScriptFullName) - Len(WScript.ScriptName))
arg = ""
If WScript.Arguments.Count > 0 Then arg = " " & WScript.Arguments(0)
objShell.Run """" & scriptDir & "tier1_capture_scheduled.bat""" & arg, 0, True
