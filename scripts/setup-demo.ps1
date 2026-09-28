param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$paths = [ordered]@{
    venv = 'D:\codex\venvs\quiz-assistant-demo'
    pipCache = 'D:\codex\cache\pip'
    temp = 'D:\codex\tmp\quiz-window-assistant-demo'
}

if ($DryRun) {
    [pscustomobject]$paths | ConvertTo-Json -Compress
    exit 0
}

New-Item -ItemType Directory -Force -Path $paths.pipCache, $paths.temp | Out-Null
$env:PIP_CACHE_DIR = $paths.pipCache
$env:TEMP = $paths.temp
$env:TMP = $paths.temp

$basePython = (Get-Command python -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath $paths.venv)) {
    & $basePython -m venv $paths.venv
}

$python = Join-Path $paths.venv 'Scripts\python.exe'
& $python -m pip install -e "$projectRoot[test]"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE"
}

Write-Host 'Setup complete. Double-click run-demo.cmd to start.'
