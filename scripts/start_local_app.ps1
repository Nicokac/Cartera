param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDir = Join-Path $root "data\runtime"
$pidPath = Join-Path $runtimeDir "local_app.pid"
$outLog = Join-Path $runtimeDir "local_app.out.log"
$errLog = Join-Path $runtimeDir "local_app.err.log"

if (-not (Test-Path $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if (Test-Path $pidPath) {
    $existingPid = Get-Content $pidPath -ErrorAction SilentlyContinue
    if ($existingPid) {
        $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Local app ya esta corriendo (PID=$existingPid) en http://$BindHost`:$Port"
            if (-not $NoBrowser) {
                Start-Process "http://$BindHost`:$Port" | Out-Null
            }
            exit 0
        }
    }
}

$python = Get-Command python -ErrorAction Stop
$args = @("-m", "uvicorn", "server:app", "--host", $BindHost, "--port", "$Port")

$proc = Start-Process `
    -FilePath $python.Source `
    -ArgumentList $args `
    -WorkingDirectory $root `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $pidPath -Value $proc.Id -Encoding ascii
Start-Sleep -Milliseconds 800

if ($proc.HasExited) {
    Write-Host "No se pudo iniciar la app local. Revisa:"
    Write-Host "  $errLog"
    exit 1
}

Write-Host "App local iniciada (PID=$($proc.Id)) en http://$BindHost`:$Port"
Write-Host "Para detenerla: .\scripts\stop_local_app.ps1"

if (-not $NoBrowser) {
    Start-Process "http://$BindHost`:$Port" | Out-Null
}
