param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$commonScript = Join-Path $PSScriptRoot "common_local_app.ps1"
. $commonScript

$startScript = Join-Path $PSScriptRoot "start_local_app.ps1"
$statusScript = Join-Path $PSScriptRoot "status_local_app.ps1"
$stopScript = Join-Path $PSScriptRoot "stop_local_app.ps1"
$baseUrl = "http://$BindHost`:$Port"
$statusUrl = "$baseUrl/status"
$detailUrl = "$baseUrl/status/detail"

function Wait-ForStatusEndpoint {
    param(
        [string]$Url,
        [hashtable]$Headers = @{},
        [int]$MaxSeconds = 15
    )
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 2
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

    Write-Host "[smoke] waiting for /session endpoint..."
    $sessionToken = Get-LocalSessionToken -BaseUrl $baseUrl -TimeoutSec 2
    $sessionHeaders = New-SessionHeaders -Token $sessionToken

    Write-Host "[smoke] waiting for /status endpoint..."
    $payload = Wait-ForStatusEndpoint -Url $statusUrl -Headers $sessionHeaders -MaxSeconds 20
    Write-Host "[smoke] /status payload: $payload"

    if (-not ($payload -match '"status"\s*:\s*"(idle|running|done|error|interrupted)"')) {
        throw "Payload /status no tiene estructura esperada."
    }

    Write-Host "[smoke] waiting for /status/detail endpoint..."
    $detailPayload = Wait-ForStatusEndpoint -Url $detailUrl -Headers $sessionHeaders -MaxSeconds 20
    Write-Host "[smoke] /status/detail payload: $detailPayload"
    if (-not ($detailPayload -match '"log_path"\s*:')) {
        throw "Payload /status/detail no tiene estructura esperada."
    }

    Write-Host "[smoke] local app health OK"
    exit 0
} finally {
    Write-Host "[smoke] stopping local app..."
    & $stopScript
}
