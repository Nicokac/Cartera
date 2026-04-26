# Guia Rapida de Tester (App Local)

## Objetivo

Levantar la app local, correr un reporte real y reportar feedback de forma consistente.

## Requisitos

- Windows + PowerShell
- Python 3.12 instalado
- credenciales IOL validas
- (opcional) `FRED_API_KEY` para enriquecer contexto macro

## Setup inicial

Desde la raiz del repo:

```powershell
.\scripts\setup_local_app.ps1
```

Opciones:

- incluir deps extra de test:

```powershell
.\scripts\setup_local_app.ps1 -InstallTestDeps
```

## Arranque y uso

1. Iniciar app:

```powershell
.\scripts\start_local_app.ps1
```

2. Abrir `http://127.0.0.1:8000`
3. Completar formulario:
   - `Usuario IOL`
   - `Password IOL`
   - fondeo (`usar liquidez IOL` y/o `aporte externo`)
4. Confirmar el resumen y ejecutar.
5. Esperar `status=done` y abrir el reporte.

Notas de seguridad:

- el password no se guarda en `localStorage`
- el server no expone password en `/status`
- las credenciales no viajan por argv al subprocess

## Comandos operativos

```powershell
.\scripts\status_local_app.ps1
.\scripts\status_local_app.ps1 -Detailed
.\scripts\stop_local_app.ps1
.\scripts\smoke_local_app.ps1
```

## Troubleshooting rapido

- no inicia la app:
  - revisar `data/runtime/local_app.err.log`
- puerto ocupado:
  - ejecutar `.\scripts\stop_local_app.ps1` y relanzar
- error de credenciales:
  - validar usuario/password IOL en el formulario
- estado inconsistente:
  - correr `.\scripts\smoke_local_app.ps1`

## Como reportar feedback

Incluir siempre:

1. version o commit probado
2. pasos exactos realizados
3. resultado esperado vs observado
4. captura del error (si hay)
5. extracto de `data/runtime/local_app.err.log` o `server_run.log` si aplica
