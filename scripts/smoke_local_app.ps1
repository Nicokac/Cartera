param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$startScript = Join-Path $PSScriptRoot "start_local_app.ps1"
$statusScript = Join-Path $PSScriptRoot "status_local_app.ps1"
$stopScript = Join-Path $PSScriptRoot "stop_local_app.ps1"
$baseUrl = "http://$BindHost`:$Port"
$statusUrl = "$baseUrl/status"

function Wait-ForStatusEndpoint {
    param(
        [string]$Url,
        [int]$MaxSeconds = 15
    )
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                return $resp.Content
            }
        } catch {
            Start-Sleep -Milliseconds 400
        }
    }
    throw "Timeout esperando endpoint de estado: $Url"
}

Write-Host "[smoke] start local app..."
& $startScript -BindHost $BindHost -Port $Port -NoBrowser

try {
    Write-Host "[smoke] status script output:"
    & $statusScript

    Write-Host "[smoke] waiting for /status endpoint..."
    $payload = Wait-ForStatusEndpoint -Url $statusUrl -MaxSeconds 20
    Write-Host "[smoke] /status payload: $payload"

    if (-not ($payload -match '"status"\s*:\s*"(idle|running|done|error)"')) {
        throw "Payload /status no tiene estructura esperada."
    }

    Write-Host "[smoke] local app health OK"
    exit 0
} finally {
    Write-Host "[smoke] stopping local app..."
    & $stopScript
}
