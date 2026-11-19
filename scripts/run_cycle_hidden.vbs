' Launch one paper-trading cycle without a console window (same pattern as the stock trader's daily job:
' a visible cmd window gets closed by accident and kills the run).
' Output is appended to data\run_cycle.log; python runs unbuffered (-u) so the log shows progress.
' The status file is rewritten after every run, including one that stopped or failed (single "&").
' The project folder is worked out from where this file lives (scripts\ inside it), so nothing here
' needs editing if the project moves.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
If Not fso.FolderExists("data") Then fso.CreateFolder("data")
sh.Run "cmd.exe /c ""echo ===== %DATE% %TIME% ===== >> data\run_cycle.log && .venv\Scripts\python.exe -u scripts\run_cycle.py >> data\run_cycle.log 2>&1 & .venv\Scripts\python.exe scripts\status.py --write > nul 2>&1""", 0, False
