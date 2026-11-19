# Start the background jobs that are not already running (Windows version of start_jobs.sh).
# Safe to run at any time, as often as you like. From PowerShell, anywhere:
#     E:\Coding\PredictionMarketTrader\research\start_jobs.ps1              history download only
#     E:\Coding\PredictionMarketTrader\research\start_jobs.ps1 -PaperLoop   ... and the paper loop
#     E:\Coding\PredictionMarketTrader\research\start_jobs.ps1 -Stop        stop both
# Everything they write goes under data\ in this folder (not committed).
param(
    [switch]$PaperLoop,             # also start scripts\paper_loop.py (asks Claude: needs the claude command)
    [double]$Every = 8,             # hours between paper cycles
    [string]$Config = "",           # config for the paper loop (default config.yaml)
    [switch]$Stop
)

$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"
$data = Join-Path $root "data"
New-Item -ItemType Directory -Force $data | Out-Null
if (-not (Test-Path $py)) { throw "no virtual environment: run setup.ps1 first" }

function Find-PmtJob([string]$script) {
    # the venv's python.exe starts the real interpreter as a child: both carry the script's full path
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$script*" }
}

function Start-PmtJob([string]$script, [string]$scriptArgs, [string]$log) {
    $cmd = "`"`"$py`" -u `"$script`" $scriptArgs >> `"$log`" 2>&1`""
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $root -WindowStyle Hidden
}

$claude = Join-Path $root ".tools\claude\node_modules\@anthropic-ai\claude-code\bin\claude.exe"

function Test-SignedIn {
    # asked without a Claude session's own variables, so the answer is about this Windows user's stored sign-in
    $saved = @{}
    Get-ChildItem Env: | Where-Object { $_.Name -match '^(CLAUDECODE|CLAUDE_CODE_|CLAUDE_AGENT_SDK_|ANTHROPIC_BASE_URL)' } |
        ForEach-Object { $saved[$_.Name] = $_.Value; Remove-Item "Env:\$($_.Name)" -ErrorAction SilentlyContinue }
    try { return ((& $claude auth status 2>$null | Out-String) -match '"loggedIn":\s*true') }
    finally { foreach ($k in $saved.Keys) { Set-Item "Env:\$k" $saved[$k] } }
}

$download = Join-Path $root "research\kalshi_download.py"
$loop = Join-Path $root "scripts\paper_loop.py"
$downloadLog = Join-Path $data "kalshi_download.log"

if ($Stop) {
    foreach ($s in @($download, $loop)) {
        Find-PmtJob $s | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
    Write-Host "stopped: history download and paper loop (both resume where they left off)"
    return
}

if (Find-PmtJob $download) { Write-Host "running: history download" }
else {
    Start-PmtJob $download "--interval 0.4 --first-pass 2500" $downloadLog
    Write-Host "started: history download"
}

if ($PaperLoop) {
    if (Find-PmtJob $loop) { Write-Host "running: paper loop" }
    elseif (-not ((Test-Path $claude) -or (Get-Command claude -ErrorAction SilentlyContinue))) {
        Write-Host "NOT started: paper loop (the claude command is not installed; see README)"
    }
    elseif ((Test-Path $claude) -and -not (Test-SignedIn)) {
        Write-Host "NOT started: paper loop (claude is not signed in). Run this once, then start again:"
        Write-Host "    & `"$claude`" auth login"
    }
    else {
        $a = "--every $Every"
        if ($Config) { $a += " --config `"$Config`"" }
        Start-PmtJob $loop $a (Join-Path $data "run_cycle.log")
        Write-Host "started: paper loop (a cycle every $Every h)"
    }
}

Start-Sleep -Seconds 3
if (Test-Path $downloadLog) { Get-Content $downloadLog -Tail 1 }
