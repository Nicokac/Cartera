<#
.SYNOPSIS
    Genera el distribuible de Cartera de Activos para usuarios finales.
    Salida: dist/cartera-vX.Y.Z-win64.zip

.PARAMETER PyVersion
    Version de Python 3.12 embeddable a incluir. Default: 3.12.9.

.PARAMETER NoPack
    Genera los archivos pero no crea el ZIP (util para inspeccion).

.EXAMPLE
    .\scripts\build_dist.ps1
    .\scripts\build_dist.ps1 -PyVersion 3.12.10
    .\scripts\build_dist.ps1 -NoPack
#>
param(
    [string]$PyVersion = "3.12.9",
    [switch]$NoPack
)

$ErrorActionPreference = "Stop"

# --- Rutas base ---
$root    = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$distDir = Join-Path $root "dist"
$cache   = Join-Path $distDir "_cache"
$appName = "Cartera de Activos"
$buildRoot = Join-Path $distDir $appName
$buildApp  = Join-Path $buildRoot "app"

# --- Version ---
$pyprojectContent = Get-Content (Join-Path $root "pyproject.toml") -Raw
if ($pyprojectContent -match '(?m)^version\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
} else {
    throw "No se encontro version en pyproject.toml"
}

$outputZip = Join-Path $distDir "cartera-v$version-win64.zip"
Write-Host ""
Write-Host "[build] version   : $version"
Write-Host "[build] python    : $PyVersion"
Write-Host "[build] destino   : $outputZip"
Write-Host ""

# --- Preparar dirs ---
if (Test-Path $buildRoot) { Remove-Item -Recurse -Force $buildRoot }
foreach ($d in @($distDir, $cache, $buildRoot, $buildApp)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# ---------------------------------------------------------------
# 1. Python embeddable
# ---------------------------------------------------------------
$pyZipName  = "python-$PyVersion-embed-amd64.zip"
$pyZipCache = Join-Path $cache $pyZipName
if (-not (Test-Path $pyZipCache)) {
    $pyUrl = "https://www.python.org/ftp/python/$PyVersion/$pyZipName"
    Write-Host "[build] descargando Python $PyVersion embeddable..."
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyZipCache -UseBasicParsing
}

$pyDir = Join-Path $buildApp "python"
New-Item -ItemType Directory -Path $pyDir | Out-Null
Write-Host "[build] extrayendo Python embeddable..."
Expand-Archive -Path $pyZipCache -DestinationPath $pyDir -Force

# Configurar _pth: agregar packages/ y la raiz de app/ a sys.path
$shortVer = (($PyVersion -split '\.')[0..1]) -join ''   # "312" de "3.12.9"
$pthPath  = Join-Path $pyDir "python$shortVer._pth"
if (-not (Test-Path $pthPath)) {
    $pthPath = (Get-ChildItem $pyDir -Filter "*._pth" | Select-Object -First 1).FullName
}
Set-Content -Path $pthPath -Encoding ascii -Value @"
python$shortVer.zip
.
../packages
..
import site
"@
Write-Host "[build] _pth configurado ($pthPath)"

# ---------------------------------------------------------------
# 2. Bootstrappear pip en el Python embeddable
# ---------------------------------------------------------------
$getPipCache = Join-Path $cache "get-pip.py"
if (-not (Test-Path $getPipCache)) {
    Write-Host "[build] descargando get-pip.py..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPipCache -UseBasicParsing
}
$embPython = Join-Path $pyDir "python.exe"
Write-Host "[build] instalando pip en Python embeddable..."
& $embPython $getPipCache --no-warn-script-location --quiet

# ---------------------------------------------------------------
# 3. Instalar dependencias en packages/
# ---------------------------------------------------------------
$packagesDir = Join-Path $buildApp "packages"
New-Item -ItemType Directory -Path $packagesDir | Out-Null
$reqPath = Join-Path $root "requirements.txt"
Write-Host "[build] instalando dependencias (puede tardar varios minutos)..."
& $embPython -m pip install -r $reqPath --target $packagesDir --no-warn-script-location --quiet
Write-Host "[build] dependencias instaladas"

# ---------------------------------------------------------------
# 4. Copiar fuentes de la app
# ---------------------------------------------------------------
Write-Host "[build] copiando archivos de la app..."

foreach ($d in @("src", "scripts", "static")) {
    Copy-Item -Path (Join-Path $root $d) -Destination (Join-Path $buildApp $d) -Recurse -Force
}

# data/: solo mappings y examples  (runtime, strategy, snapshots y reports NO van en el zip
# para que sobrevivan las actualizaciones)
$dataDst = Join-Path $buildApp "data"
New-Item -ItemType Directory -Path $dataDst | Out-Null
foreach ($sub in @("mappings", "examples")) {
    $src = Join-Path $root "data\$sub"
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $dataDst $sub) -Recurse -Force
    }
}

foreach ($f in @("server.py", "requirements.txt")) {
    Copy-Item -Path (Join-Path $root $f) -Destination (Join-Path $buildApp $f) -Force
}


Set-Content -Path (Join-Path $buildApp "version.txt") -Value $version -Encoding ascii

$envExSrc = Join-Path $root ".env.example"
if (Test-Path $envExSrc) {
    Copy-Item -Path $envExSrc -Destination (Join-Path $buildApp ".env.example") -Force
}

# ---------------------------------------------------------------
# 5. LEEME.txt en la raiz del zip
# ---------------------------------------------------------------
$leemePath = Join-Path $buildRoot "LEEME.txt"
Set-Content -Path $leemePath -Encoding utf8 -Value @"
Cartera de Activos v$version
=======================================

COMO INICIAR
------------
Doble clic en "Iniciar Cartera.bat".
El browser se abre automaticamente con la app.

COMO DETENER
------------
Doble clic en "Detener Cartera.bat".

ACTUALIZACIONES
---------------
La app muestra la version actual en el pie de pagina.
Si hay una version nueva disponible, pedirsela a Nicolas Kachuk.

Para actualizar: descomprimir el nuevo ZIP en la misma carpeta
y elegir "Reemplazar todo". Los datos y reportes guardados
se conservan automaticamente.

CONFIGURACION OPCIONAL
----------------------
El archivo app\.env permite configurar claves opcionales
como FRED_API_KEY. Editarlo con el Bloc de notas si es necesario.
Las credenciales IOL se ingresan directamente en el formulario
de la app y no se guardan en ningun archivo.

SOPORTE
-------
Ante cualquier problema, avisar a Nicolas Kachuk con:
- Descripcion de lo que paso
- Captura de pantalla si es posible
"@

# AYUDA.txt en la raiz del zip (copiado desde docs/ayuda-usuario.txt)
$ayudaSrc = Join-Path $root "docs\ayuda-usuario.txt"
if (Test-Path $ayudaSrc) {
    Copy-Item -Path $ayudaSrc -Destination (Join-Path $buildRoot "AYUDA.txt") -Force
}

# ---------------------------------------------------------------
# 6. Bat files
# ---------------------------------------------------------------

# NOTA: se usa here-string de comilla simple (@'...'@) para que PS
# no interpole nada y los % y $ queden literales para batch/PS interno.

$iniciarBat = @'
@echo off
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0app"
set "PYTHON=%~dp0app\python\python.exe"
set "PIDFILE=%~dp0app\data\runtime\app.pid"

rem Crear directorios necesarios si no existen
if not exist "%~dp0app\data\runtime"   mkdir "%~dp0app\data\runtime"
if not exist "%~dp0app\data\strategy"  mkdir "%~dp0app\data\strategy"
if not exist "%~dp0app\data\snapshots" mkdir "%~dp0app\data\snapshots"
if not exist "%~dp0app\reports"        mkdir "%~dp0app\reports"

rem Crear .env desde .env.example si no existe aun
if not exist "%APP_DIR%\.env" (
    if exist "%APP_DIR%\.env.example" (
        copy "%APP_DIR%\.env.example" "%APP_DIR%\.env" >nul
    )
)

rem Cargar variables de .env (para FRED_API_KEY y similares)
if exist "%APP_DIR%\.env" (
    for /f "usebackq eol=# tokens=1* delims==" %%a in ("%APP_DIR%\.env") do (
        if not "%%a"=="" set "%%a=%%b"
    )
)

rem Bootstrap de configuracion de ejemplo en primera corrida
if not exist "%~dp0app\data\strategy\sizing_config.json" (
    "%PYTHON%" "%APP_DIR%\scripts\bootstrap_example_config.py" >nul 2>&1
)

rem Verificar si ya hay una instancia corriendo
if exist "%PIDFILE%" (
    <"%PIDFILE%" set /p RUNNING_PID=
    if not "!RUNNING_PID!"=="" (
        powershell -c "if (Get-Process -Id !RUNNING_PID! -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
        if not errorlevel 1 (
            echo.
            echo La app ya esta corriendo en http://127.0.0.1:8000
            start "" "http://127.0.0.1:8000"
            echo.
            pause
            exit /b 0
        )
    )
    del "%PIDFILE%" >nul 2>&1
)

echo.
echo Iniciando Cartera de Activos...
echo.

powershell -Command "$p = Start-Process -FilePath '%PYTHON%' -ArgumentList @('-m','uvicorn','server:app','--host','127.0.0.1','--port','8000') -WorkingDirectory '%APP_DIR%' -PassThru -WindowStyle Hidden; $p.Id | Out-File -FilePath '%PIDFILE%' -Encoding ascii -NoNewline"

timeout /t 3 /nobreak >nul

start "" "http://127.0.0.1:8000"

echo Listo. El browser deberia abrirse automaticamente.
echo Para cerrar la app, ejecuta "Detener Cartera.bat".
echo.
pause
'@

$detenerBat = @'
@echo off
set "PIDFILE=%~dp0app\data\runtime\app.pid"

if not exist "%PIDFILE%" (
    echo La app no estaba corriendo.
    echo.
    pause
    exit /b 0
)

<"%PIDFILE%" set /p PID=
if "%PID%"=="" (
    del "%PIDFILE%" >nul 2>&1
    echo La app no estaba corriendo.
) else (
    powershell -c "Stop-Process -Id %PID% -Force -ErrorAction SilentlyContinue"
    del "%PIDFILE%" >nul 2>&1
    echo App detenida correctamente.
)
echo.
pause
'@

Set-Content -Path (Join-Path $buildRoot "Iniciar Cartera.bat") -Value $iniciarBat -Encoding ascii
Set-Content -Path (Join-Path $buildRoot "Detener Cartera.bat") -Value $detenerBat -Encoding ascii

Write-Host "[build] bat files generados"

# ---------------------------------------------------------------
# 7. Empaquetar en ZIP
# ---------------------------------------------------------------
if (-not $NoPack) {
    if (Test-Path $outputZip) { Remove-Item $outputZip }
    Write-Host "[build] empaquetando..."
    Compress-Archive -Path $buildRoot -DestinationPath $outputZip
    $sizeMB = [math]::Round((Get-Item $outputZip).Length / 1MB, 1)
    Write-Host "[build] listo: $outputZip ($sizeMB MB)"
    # Limpiar carpeta de build intermedia; el zip es el unico artefacto
    Remove-Item -Recurse -Force $buildRoot
    Write-Host "[build] carpeta de build limpiada"
} else {
    Write-Host "[build] -NoPack: zip omitido. Archivos en: $buildRoot"
}

Write-Host ""
Write-Host "Build completado. Version: $version"
