param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDir = Join-Path $root "data\runtime"
$errLog = Join-Path $runtimeDir "local_app.err.log"
$outLog = Join-Path $runtimeDir "local_app.out.log"

function Show-Menu {
    Write-Host ""
    Write-Host "=== Cartera Local App ==="
    Write-Host "1) Start"
    Write-Host "2) Status"
    Write-Host "3) Stop"
    Write-Host "4) Open Browser"
    Write-Host "5) Tail Error Log"
    Write-Host "6) Tail Output Log"
    Write-Host "7) Exit"
}

while ($true) {
    Show-Menu
    $choice = Read-Host "Selecciona una opcion"
    switch ($choice) {
        "1" {
            & (Join-Path $PSScriptRoot "start_local_app.ps1") -BindHost $BindHost -Port $Port
        }
        "2" {
            & (Join-Path $PSScriptRoot "status_local_app.ps1")
        }
        "3" {
            & (Join-Path $PSScriptRoot "stop_local_app.ps1")
        }
        "4" {
            Start-Process "http://$BindHost`:$Port" | Out-Null
            Write-Host "Browser abierto en http://$BindHost`:$Port"
        }
        "5" {
            if (Test-Path $errLog) {
                Get-Content $errLog -Wait
            } else {
                Write-Host "No existe $errLog"
            }
        }
        "6" {
            if (Test-Path $outLog) {
                Get-Content $outLog -Wait
            } else {
                Write-Host "No existe $outLog"
            }
        }
        "7" {
            break
        }
        default {
            Write-Host "Opcion invalida."
        }
    }
}
