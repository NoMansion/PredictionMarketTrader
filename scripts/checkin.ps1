# One research check-in, run headless by the Claude Code CLI on Opus 5.5 (never Fable: the user, 2026-11-20).
# Started every 3 hours by the Windows task "PredictionMarketTrader Check-in" (through checkin_hidden.vbs), or by
# hand:   powershell -ExecutionPolicy Bypass -File E:\Coding\PredictionMarketTrader\scripts\checkin.ps1
#
# Writes data\checkin\<time>.json (the CLI's full answer, with the models that were really used and the cost) and
# one line per run to data\checkin.log; shows the answer's last line as a Windows notification.
param(
    [int]$TimeoutMinutes = 60,
    [string]$Model = "claude-opus-5-5",
    [string]$PromptFile = ""           # default scripts\checkin_prompt.md (another file only for testing the plumbing)
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$data = Join-Path $root "data"
$dir = Join-Path $data "checkin"
New-Item -ItemType Directory -Force $dir | Out-Null
$log = Join-Path $data "checkin.log"
$lock = Join-Path $data "checkin.lock"
$claude = Join-Path $root ".tools\claude\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
if (-not $PromptFile) { $PromptFile = Join-Path $PSScriptRoot "checkin_prompt.md" }
$prompt = Get-Content $PromptFile -Raw -Encoding UTF8
$stamp = Get-Date -Format "yyyyMMdd-HHmm"

function Write-Log([string]$msg) {
    Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date -Format "yyyy-MM-dd hh:mm tt"), $msg) -Encoding UTF8
}

function Show-Note([string]$text) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $t = $xml.GetElementsByTagName("text")
        $t.Item(0).AppendChild($xml.CreateTextNode("PredictionMarketTrader check-in")) | Out-Null
        $t.Item(1).AppendChild($xml.CreateTextNode($text)) | Out-Null
        $app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
    } catch { Write-Log "notification not shown: $($_.Exception.Message)" }
}

# one check-in at a time; a lock older than the timeout belongs to a run that died
if (Test-Path $lock) {
    $age = (Get-Date) - (Get-Item $lock).LastWriteTime
    if ($age.TotalMinutes -lt $TimeoutMinutes + 5) { Write-Log "skipped: another check-in is running"; return }
}
Set-Content -Path $lock -Value $PID
try {
    if (Test-Path (Join-Path $data "STOP")) { Write-Log "skipped: data\STOP exists (kill switch)"; return }
    if (-not (Test-Path $claude)) { Write-Log "FAILED: the claude program is missing ($claude)"; Show-Note "check-in failed: claude program missing"; return }
    # a run started from inside a Claude session must not inherit that session's identity
    Get-ChildItem Env: | Where-Object { $_.Name -match '^(CLAUDECODE|CLAUDE_CODE_|CLAUDE_AGENT_SDK_|ANTHROPIC_BASE_URL)' } |
        ForEach-Object { Remove-Item "Env:\$($_.Name)" -ErrorAction SilentlyContinue }
    $env:TEMP = Join-Path $data "tmp"; $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Force $env:TEMP | Out-Null
    $out = Join-Path $dir "$stamp.json"
    $err = Join-Path $dir "$stamp.err.txt"
    $pfile = Join-Path $dir "$stamp.prompt.txt"
    Set-Content -Path $pfile -Value $prompt -Encoding UTF8
    # no --fallback-model: if Opus is unavailable the run fails instead of answering on another model
    $cliArgs = @("-p", "--model", $Model, "--permission-mode", "auto", "--permission-prompts", "none",
              "--output-format", "json")
    $p = Start-Process -FilePath $claude -ArgumentList $cliArgs -WorkingDirectory $root -NoNewWindow -PassThru `
        -RedirectStandardInput $pfile -RedirectStandardOutput $out -RedirectStandardError $err
    if (-not $p.WaitForExit($TimeoutMinutes * 60 * 1000)) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Write-Log "FAILED: no answer within $TimeoutMinutes minutes (stopped)"
        Show-Note "check-in stopped after $TimeoutMinutes minutes without an answer"
        return
    }
    $raw = Get-Content $out -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    try { $j = $raw | ConvertFrom-Json } catch { $j = $null }
    if (-not $j) {
        $e = (Get-Content $err -Raw -ErrorAction SilentlyContinue)
        Write-Log "FAILED: exit $($p.ExitCode), no JSON answer: $(($e + $raw) -replace '\s+', ' ' | Select-Object -First 1)"
        Show-Note "check-in failed (exit $($p.ExitCode)): see data\checkin.log"
        return
    }
    $models = @()
    if ($j.modelUsage) { $models = @($j.modelUsage.PSObject.Properties.Name) }
    $bad = @($models | Where-Object { $_ -notmatch 'opus|haiku' })
    $text = [string]$j.result
    $last = (($text -split "`n") | Where-Object { $_.Trim() } | Select-Object -Last 1)
    if (-not $last) { $last = "(no answer text)" }
    $cost = if ($j.total_cost_usd) { "{0:n2}" -f [double]$j.total_cost_usd } else { "?" }
    $mins = if ($j.duration_ms) { "{0:n0}" -f ([double]$j.duration_ms / 60000) } else { "?" }
    $flag = if ($j.is_error) { "ERROR " } else { "" }
    if ($bad.Count) { $flag += "OTHER MODEL USED ($($bad -join ', ')) " }
    Write-Log ("{0}ok in {1} min, list price `${2}, models {3}: {4}" -f $flag, $mins, $cost, ($models -join ","), $last.Trim())
    Show-Note $last.Trim()
} finally {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
}
