param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Detailed
)

$ErrorActionPreference = "Stop"

$commonScript = Join-Path $PSScriptRoot "common_local_app.ps1"
. $commonScript

$root = Get-RepoRoot
$pidPath = Join-Path (Get-RuntimeDir -Root $root) "local_app.pid"
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
    if ($Detailed) {
        try {
            $token = Get-LocalSessionToken -BaseUrl $url -TimeoutSec 2
            $headers = New-SessionHeaders -Token $token
            $detail = Invoke-WebRequest -Uri "$url/status/detail" -Headers $headers -UseBasicParsing -TimeoutSec 2
            Write-Host $detail.Content
        } catch {
            Write-Host "detail_error=$($_.Exception.Message)"
        }
    }
    exit 0
}

Remove-Item $pidPath -ErrorAction SilentlyContinue
Write-Host "status=stopped pid=none url=$url checked_at=$checkedAt stale_pid=$pidValue cleaned=true"
