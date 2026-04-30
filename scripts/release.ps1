<#
.SYNOPSIS
    Automatiza release local: bump de version, commit opcional, tag y build dist.

.DESCRIPTION
    - Actualiza `pyproject.toml` (`[project].version`)
    - Actualiza/crea `version.txt` en la raiz del repo
    - Crea tag git `vX.Y.Z`
    - Ejecuta `scripts/build_dist.ps1`

    Requiere working tree limpio salvo que se use `-AllowDirty`.

.EXAMPLE
    .\scripts\release.ps1 -Version 0.2.3
    .\scripts\release.ps1 -Version 0.2.3 -NoTag
    .\scripts\release.ps1 -Version 0.2.3 -NoBuild
    .\scripts\release.ps1 -Version 0.2.3 -DryRun
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [switch]$NoTag,
    [switch]$NoBuild,
    [switch]$AllowDirty,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version invalida. Usar formato SemVer estricto: X.Y.Z"
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pyprojectPath = Join-Path $root "pyproject.toml"
$versionFilePath = Join-Path $root "version.txt"
$buildScriptPath = Join-Path $root "scripts\build_dist.ps1"
$tagName = "v$Version"

if (-not (Test-Path $pyprojectPath)) {
    throw "No se encontro pyproject.toml en $pyprojectPath"
}
if (-not (Test-Path $buildScriptPath)) {
    throw "No se encontro build_dist.ps1 en $buildScriptPath"
}

Push-Location $root
try {
    $statusOutput = git status --porcelain
    $status = if ($null -eq $statusOutput) { "" } else { "$statusOutput".Trim() }
    if (-not $AllowDirty -and $status) {
        throw "Working tree no limpio. Commit/stash antes de release o usar -AllowDirty."
    }

    if (-not $NoTag) {
        $existingTagOutput = git tag -l $tagName
        $existingTag = if ($null -eq $existingTagOutput) { "" } else { "$existingTagOutput".Trim() }
        if ($existingTag) {
            throw "El tag $tagName ya existe."
        }
    }

    $pyprojectRaw = Get-Content $pyprojectPath -Raw
    if ($pyprojectRaw -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
        throw "No se encontro campo version en pyproject.toml"
    }
    $currentVersion = $Matches[1]
    $newPyprojectRaw = [regex]::Replace(
        $pyprojectRaw,
        '(?m)^version\s*=\s*"[^"]+"',
        "version = `"$Version`"",
        1
    )

    Write-Host ""
    Write-Host "[release] version actual : $currentVersion"
    Write-Host "[release] version nueva  : $Version"
    Write-Host "[release] tag           : $tagName"
    Write-Host "[release] build dist    : $(-not $NoBuild)"
    Write-Host "[release] dry run       : $DryRun"
    Write-Host ""

    if ($DryRun) {
        Write-Host "[release] DryRun activo: no se aplican cambios."
        return
    }

    Set-Content -Path $pyprojectPath -Value $newPyprojectRaw -Encoding utf8
    Set-Content -Path $versionFilePath -Value $Version -Encoding ascii
    Write-Host "[release] versiones actualizadas en pyproject.toml y version.txt"

    if (-not $NoTag) {
        git add pyproject.toml version.txt
        git commit -m "chore(release): bump version to $Version"
        git tag $tagName
        Write-Host "[release] commit y tag creados: $tagName"
    } else {
        Write-Host "[release] tag omitido por -NoTag"
    }

    if (-not $NoBuild) {
        & $buildScriptPath
    } else {
        Write-Host "[release] build omitido por -NoBuild"
    }

    Write-Host ""
    Write-Host "[release] listo: version $Version"
}
finally {
    Pop-Location
}
