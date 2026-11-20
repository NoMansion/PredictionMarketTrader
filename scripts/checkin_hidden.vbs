' Runs scripts\checkin.ps1 without a window (for the Windows task "PredictionMarketTrader Check-in").
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & here & "\checkin.ps1""", 0, False
