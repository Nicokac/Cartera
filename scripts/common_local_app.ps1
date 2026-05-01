Set-StrictMode -Version Latest

$script:CommonLocalAppRoot = $PSScriptRoot

function Test-IsWindowsPlatform {
    return $env:OS -eq "Windows_NT"
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $script:CommonLocalAppRoot "..")).Path
}

function Get-RuntimeDir {
    param(
        [string]$Root
    )

    return (Join-Path (Join-Path $Root "data") "runtime")
}

function Resolve-VenvPython {
    param(
        [string]$Root
    )

    $venvDir = Join-Path $Root ".venv"
    if (Test-IsWindowsPlatform) {
        $candidate = Join-Path (Join-Path $venvDir "Scripts") "python.exe"
    } else {
        $candidate = Join-Path (Join-Path $venvDir "bin") "python"
    }

    if (Test-Path $candidate) {
        return $candidate
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw "No se encontro Python ni entorno virtual en .venv."
}

function Get-LocalSessionToken {
    param(
        [string]$BaseUrl,
        [int]$TimeoutSec = 2
    )

    $session = Invoke-RestMethod -Uri "$BaseUrl/session" -UseBasicParsing -TimeoutSec $TimeoutSec
    $token = [string]($session.token)
    if (-not $token) {
        throw "La app local no devolvio token de sesion."
    }
    return $token
}

function New-SessionHeaders {
    param(
        [string]$Token
    )

    return @{ "X-Session-Token" = $Token }
}

function Open-LocalUrl {
    param(
        [string]$Url
    )

    if (Test-IsWindowsPlatform) {
        Start-Process $Url | Out-Null
        return
    }

    $openCmd = Get-Command open -ErrorAction SilentlyContinue
    if ($openCmd) {
        & $openCmd.Source $Url | Out-Null
        return
    }

    $xdgOpenCmd = Get-Command xdg-open -ErrorAction SilentlyContinue
    if ($xdgOpenCmd) {
        & $xdgOpenCmd.Source $Url | Out-Null
        return
    }

    Write-Host "Abre manualmente: $Url"
}
