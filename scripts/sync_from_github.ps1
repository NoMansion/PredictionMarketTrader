# Bring in what the cloud session has committed since the last sync. The cloud session works on the stock
# trader's repository (branch claude/friendly-clarke-tf5rm4, folder PolymarketTrader); this project is its own
# repository, so the new commits are MERGED into it with git: nothing here is overwritten, and local changes
# that touch the same lines come back as ordinary merge conflicts to resolve.
#
#     Set-ExecutionPolicy -Scope Process Bypass; .\scripts\sync_from_github.ps1
#
# What it does: clones the branch into a temporary folder inside this one (so it stays on this drive), rewrites
# that copy so the PolymarketTrader folder is its root (the same commits get the same ids every time, so earlier
# syncs line up), fetches the result as the local branch "cloud", merges it, removes the temporary folder.
# data\, .venv\, .tools\ and .env are not in git and are not touched. Needs git on the PATH and a clean tree.
param(
    [string]$Repo = "https://github.com/NoMansion/StockTrader.git",
    [string]$Branch = "claude/friendly-clarke-tf5rm4"
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot
Set-Location $here
if (git status --porcelain) { throw "uncommitted changes here: commit them first, then sync" }
$tmp = Join-Path $here "_import_tmp"
if (Test-Path $tmp) { throw "$tmp already exists: look at it, delete it, run again" }
$ErrorActionPreference = "Continue"                 # git writes progress to stderr; exit codes are checked instead
try {
    git clone --quiet --no-tags --single-branch --branch $Branch $Repo $tmp 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    $env:FILTER_BRANCH_SQUELCH_WARNING = "1"
    git -C $tmp filter-branch --prune-empty --subdirectory-filter PolymarketTrader HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "the branch has no PolymarketTrader folder (or the rewrite failed)" }
    git fetch --quiet --no-tags $tmp "+${Branch}:refs/heads/cloud" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git fetch from the temporary copy failed" }
}
finally {
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
}
$new = git rev-list --count "HEAD..cloud"
if ($new -eq "0") { Write-Host "Already up to date with $Branch." -ForegroundColor Green; return }
git merge --no-ff --no-edit cloud
if ($LASTEXITCODE -ne 0) {
    Write-Host "$new new commits; the merge stopped on conflicts. Resolve them, then: git commit" -ForegroundColor Yellow
    return
}
Write-Host "Merged $new new commits from $Branch." -ForegroundColor Green
Write-Host "Run .\setup.ps1 again if requirements changed, then: .venv\Scripts\python -m pytest -q"
