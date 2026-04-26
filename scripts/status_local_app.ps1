param()

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidPath = Join-Path $root "data\runtime\local_app.pid"

if (-not (Test-Path $pidPath)) {
    Write-Host "status=stopped pid=none"
    exit 0
}

$pidValue = Get-Content $pidPath -ErrorAction SilentlyContinue
if (-not $pidValue) {
    Write-Host "status=stopped pid=none"
    exit 0
}

$proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "status=running pid=$pidValue"
    exit 0
}

Remove-Item $pidPath -ErrorAction SilentlyContinue
Write-Host "status=stopped pid=none (cleaned stale pid file: $pidValue)"
