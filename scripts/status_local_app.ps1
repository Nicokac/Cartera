param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pidPath = Join-Path $root "data\runtime\local_app.pid"
$url = "http://$BindHost`:$Port"
$checkedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $pidPath)) {
    Write-Host "status=stopped pid=none url=$url checked_at=$checkedAt"
    exit 0
}

$pidValue = Get-Content $pidPath -ErrorAction SilentlyContinue
if (-not $pidValue) {
    Write-Host "status=stopped pid=none url=$url checked_at=$checkedAt"
    exit 0
}

$proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "status=running pid=$pidValue url=$url checked_at=$checkedAt"
    exit 0
}

Remove-Item $pidPath -ErrorAction SilentlyContinue
Write-Host "status=stopped pid=none url=$url checked_at=$checkedAt stale_pid=$pidValue cleaned=true"
