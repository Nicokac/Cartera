param(
    [switch]$InstallTestDeps,
    [switch]$SkipBootstrap
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvDir = Join-Path $root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

function Resolve-PythonLauncher {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, @("-3.12"))
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source, @())
    }

    throw "No se encontro Python. Instala Python 3.12 y reintenta."
}

if (-not (Test-Path $venvPython)) {
    $launcher = Resolve-PythonLauncher
    $pythonExe = $launcher[0]
    $pythonArgs = @($launcher[1]) + @("-m", "venv", $venvDir)
    Write-Host "[setup] creando entorno virtual en .venv ..."
    & $pythonExe @pythonArgs
}

if (-not (Test-Path $venvPython)) {
    throw "No se pudo crear el entorno virtual en .venv."
}

Write-Host "[setup] actualizando pip ..."
& $venvPython -m pip install --upgrade pip

Write-Host "[setup] instalando dependencias base ..."
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")

if ($InstallTestDeps) {
    Write-Host "[setup] instalando dependencias extra de test ..."
    & $venvPython -m pip install "httpx>=0.27,<1"
}

if (-not $SkipBootstrap) {
    Write-Host "[setup] ejecutando bootstrap de configuracion ..."
    & $venvPython (Join-Path $root "scripts\bootstrap_example_config.py")
}

$envPath = Join-Path $root ".env"
$envExamplePath = Join-Path $root ".env.example"
if (-not (Test-Path $envPath) -and (Test-Path $envExamplePath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Host "[setup] se creo .env desde .env.example (completa tus claves)."
}

Write-Host ""
Write-Host "Setup finalizado."
Write-Host "Siguientes pasos:"
Write-Host "  1) Editar .env con tus credenciales/API keys (si aplica)."
Write-Host "  2) Iniciar app local: .\scripts\start_local_app.ps1"
Write-Host "  3) Smoke rapido: .\scripts\smoke_local_app.ps1"
