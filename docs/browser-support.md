# Compatibilidad de navegadores

Matriz oficial para la app local (`http://127.0.0.1:8000`) y reporte HTML (`/reports/real-report.html`).

## Soporte oficial (desktop)

- `Google Chrome` (estable, ultimas 2 versiones)
- `Microsoft Edge` (estable, ultimas 2 versiones)
- `Mozilla Firefox` (estable, ultimas 2 versiones)
- `Safari` macOS (ultimas 2 versiones mayores)

## Soporte oficial (mobile)

- `iOS Safari` (ultimas 2 versiones mayores)
- `Chrome Android` (ultimas 2 versiones estables)

## Estado por superficie

- App local (`static/index.html`): soportada en navegadores oficiales desktop y mobile.
- Reporte generado (`reports/*.html`): soportado en navegadores oficiales desktop; soporte mobile en modo lectura (sin interaccion compleja).

## Fuera de alcance

- Internet Explorer.
- Navegadores legacy sin soporte activo del proveedor.
- WebViews embebidas antiguas (sin actualizacion de motor).

## Criterio de validacion minima por release

1. Abrir app local y ejecutar flujo basico: login, correr, cancelar, ver estado.
2. Abrir un reporte generado y validar tablas/estilos principales.
3. Probar viewport mobile (320-430 px) en app local y reporte:
   - no hay solapamientos criticos
   - botones y enlaces siguen accesibles
