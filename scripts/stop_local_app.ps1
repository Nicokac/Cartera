param()

$ErrorActionPreference = "Stop"

$commonScript = Join-Path $PSScriptRoot "common_local_app.ps1"
. $commonScript

$root = Get-RepoRoot
$pidPath = Join-Path (Get-RuntimeDir -Root $root) "local_app.pid"

if (-not (Test-Path $pidPath)) {
    Write-Host "No hay PID file. La app local no parece estar corriendo."
    exit 0
}

$pidValue = Get-Content $pidPath -ErrorAction SilentlyContinue
if (-not $pidValue) {
    Remove-Item $pidPath -ErrorAction SilentlyContinue
    Write-Host "PID file vacio, limpiado."
    exit 0
}

$proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Id $pidValue -Force
    Write-Host "App local detenida (PID=$pidValue)."
} else {
    Write-Host "No existe proceso activo con PID=$pidValue."
}

Remove-Item $pidPath -ErrorAction SilentlyContinue
