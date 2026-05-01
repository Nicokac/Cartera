param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$commonScript = Join-Path $PSScriptRoot "common_local_app.ps1"
. $commonScript

$root = Get-RepoRoot
$runtimeDir = Get-RuntimeDir -Root $root
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
                Open-LocalUrl -Url "http://$BindHost`:$Port"
            }
            exit 0
        }
    }
}

$pythonExe = Resolve-VenvPython -Root $root
$uvicornArgs = @("-m", "uvicorn", "server:app", "--host", $BindHost, "--port", "$Port")

$startProcessParams = @{
    FilePath = $pythonExe
    ArgumentList = $uvicornArgs
    WorkingDirectory = $root
    RedirectStandardOutput = $outLog
    RedirectStandardError = $errLog
    PassThru = $true
}
if (Test-IsWindowsPlatform) {
    $startProcessParams["WindowStyle"] = "Hidden"
}

$proc = Start-Process @startProcessParams

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
    Open-LocalUrl -Url "http://$BindHost`:$Port"
}
