' Start the background jobs (the history download and the paper loop) without a console window.
' Run by the Windows task "PredictionMarketTrader Jobs" when the user logs on, so that a restart of the PC does
' not leave them stopped. Safe to run at any time: research\start_jobs.ps1 starts only what is not running.
' It waits two minutes first, so the network is up before the first request.
' The project folder is wherever this script lives (its parent folder).
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
sh.CurrentDirectory = root
WScript.Sleep 120000
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & root & "\research\start_jobs.ps1"" -PaperLoop", 0, False
