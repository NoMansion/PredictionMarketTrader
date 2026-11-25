# Move the research databases (the Kalshi history and its companions) off C: when C: runs short of space.
# The user, 2026-11-24: "if the C drive fills up please switch to using the D drive".
#
#     powershell -ExecutionPolicy Bypass -File C:\Coding\PredictionMarketTrader\scripts\move_history.ps1
#
# Stops ONLY the history download (never the paper loop), checkpoints and copies kalshi_hist.db, kalshi_hourly.db and
# kalshi_events.db (with their -wal / -shm files) to the target folder, checks each copy's size, writes the target into
# data\history_location.txt (research\data_paths.py: everything that opens these databases reads it), deletes the C:
# copies and starts the download again. Safe to run twice: once moved, it only removes C: copies left behind by a run
# that could not delete them (a file in use) and says where the databases are. Logs to data\move_history.log.
param(
    [string]$To = "D:\PredictionMarketTrader\data",
    [string]$DataDir = "",         # default data\ (tests only)
    [switch]$NoStop,               # do not touch processes (tests only)
    [switch]$NoRestart             # do not start the download afterwards (tests only)
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$data = if ($DataDir) { $DataDir } else { Join-Path $root "data" }
$pointer = Join-Path $data "history_location.txt"
$log = Join-Path $data "move_history.log"
$py = Join-Path $root ".venv\Scripts\python.exe"
$names = @("kalshi_hist.db", "kalshi_hourly.db", "kalshi_events.db")

function Write-Log([string]$msg) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd hh:mm tt"), $msg
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-DbFiles([string]$dir) {
    foreach ($n in $names) {
        foreach ($suffix in @("", "-wal", "-shm")) {
            $f = Join-Path $dir ($n + $suffix)
            if (Test-Path $f) { Get-Item $f }
        }
    }
}

function Find-Download {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*kalshi_download.py*" }
}

if (Test-Path $pointer) {
    $where = (Get-Content $pointer -Raw).Trim()
    # leftovers: only where the moved copy is there and at least as large
    foreach ($f in @(Get-DbFiles $data)) {
        $moved = Join-Path $where $f.Name
        if ((Test-Path $moved) -and (Get-Item $moved).Length -ge $f.Length) {
            try { Remove-Item $f.FullName -Force; Write-Log "removed a C: copy left behind: $($f.Name)" }
            catch { Write-Log "still in use, left for the next run: $($f.Name)" }
        }
    }
    Write-Host "already moved: the research databases are in $where"
    return
}

$files = @(Get-DbFiles $data)
if (-not $files.Count) { throw "nothing to move: no research databases in $data" }
$need = ($files | Measure-Object Length -Sum).Sum
$qualifier = Split-Path -Qualifier $To
$drive = Get-PSDrive ($qualifier.TrimEnd(':')) -ErrorAction SilentlyContinue
if (-not $drive) { throw "no drive $qualifier on this PC" }
if ($drive.Free -lt 2 * $need + 10GB) {
    throw ("{0} has {1:n1} GB free; moving {2:n1} GB needs twice that plus 10 GB" -f $qualifier, ($drive.Free / 1GB), ($need / 1GB))
}

$wasRunning = $false
if (-not $NoStop) {
    $running = @(Find-Download)
    $wasRunning = $running.Count -gt 0
    $running | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    for ($i = 0; $i -lt 30 -and @(Find-Download).Count; $i++) { Start-Sleep -Seconds 2 }
    if (@(Find-Download).Count) { throw "the history download would not stop" }
}

try {
    # fold each write-ahead log into its database, so the main files are complete on their own
    $dbs = @($names | ForEach-Object { Join-Path $data $_ } | Where-Object { Test-Path $_ })
    & $py -c "import sqlite3, sys`nfor p in sys.argv[1:]:`n    c = sqlite3.connect(p, timeout=120); c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchall(); c.close()" @dbs
    New-Item -ItemType Directory -Force $To | Out-Null
    $files = @(Get-DbFiles $data)
    foreach ($f in $files) {
        $dest = Join-Path $To $f.Name
        Copy-Item -Path $f.FullName -Destination $dest -Force
        if ((Get-Item $dest).Length -ne $f.Length) { throw "copy of $($f.Name) is not the same size" }
    }
    [IO.File]::WriteAllText($pointer, $To)           # no byte-order mark
    Write-Log ("moved {0} files, {1:n2} GB, to {2} (C: had {3:n1} GB free)" -f $files.Count, ($need / 1GB), $To,
               ((Get-PSDrive C).Free / 1GB))
    foreach ($f in $files) {
        try { Remove-Item $f.FullName -Force }
        catch { Write-Log "still in use, left for the next run: $($f.Name)" }
    }
} finally {
    if ($wasRunning -and -not $NoRestart) {
        & (Join-Path $root "research\start_jobs.ps1") | Out-Null
        Write-Log "history download started again (it reads data\history_location.txt)"
    }
}
