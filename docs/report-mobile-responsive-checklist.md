# Checklist Mobile/Responsive del Reporte

Fecha: 2026-04-30

Objetivo:

- validar que `reports/real-report.html` sea legible y utilizable en mobile sin romper lectura de tablas y secciones.

## Viewports a probar

1. `320x568` (mobile pequeno)
2. `375x667` (mobile estandar)
3. `390x844` (mobile moderno)
4. `768x1024` (tablet)

## Navegadores objetivo

- iOS Safari (ultimas 2 versiones)
- Chrome Android (ultimas 2 versiones)
- Chrome desktop (modo responsive device emulation)

## Checklist funcional

1. Carga inicial del HTML:
   - sin desbordes horizontales globales inesperados
   - tipografia legible sin zoom manual obligatorio
2. Navegacion por secciones:
   - los bloques principales se distinguen visualmente
   - no hay superposicion de titulos/textos
3. Tablas:
   - headers visibles y alineados con columnas
   - columnas criticas (`Ticker`, `Accion`, `Score`) legibles
   - scroll horizontal local aceptable cuando la tabla no entra en ancho
4. Bloques de prediccion/riesgo:
   - textos no truncados de forma critica
   - labels (`Robusta/Parcial/Corta/Sin historia`) visibles
5. Enlaces:
   - links de navegacion interna/externa clickeables en mobile
   - areas de toque razonables (sin solapes)

## Criterios de aceptacion

- AA visual basica: contenido principal legible sin zoom en viewport `375x667`.
- Sin bloqueos de lectura: toda tabla relevante puede leerse con scroll local si aplica.
- Sin regresiones estructurales: no hay secciones ocultas por solapes o overflow fuera de control.

## Registro de ejecucion (plantilla)

- Fecha:
- Commit:
- Dispositivo/Navegador:
- Resultado general: `OK` / `Observaciones`
- Observaciones:
