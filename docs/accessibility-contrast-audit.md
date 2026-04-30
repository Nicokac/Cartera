# Auditoria de contraste WCAG (UI local)

Fecha: 2026-04-30

Alcance:

- `static/index.html` (app local en `http://127.0.0.1:8000`)

## Ajustes aplicados

1. Texto secundario de timestamp de estado:
   - antes: `#888`
   - ahora: `#4b5563`

2. Texto de footer:
   - antes: `#aaa`
   - ahora: `#4b5563`

3. Botones deshabilitados:
   - `button:disabled` mantiene fondo `#93c5fd` y cambia texto a `#1f2937`
   - `#btn-cancel:disabled` mantiene fondo `#ef9a9a` y cambia texto a `#7f1d1d`

## Resultado esperado

- Mejora de legibilidad para textos secundarios y estados deshabilitados.
- Reduccion de riesgo de incumplimiento AA en elementos de bajo contraste.

## Verificacion manual recomendada

1. Abrir la app local y revisar visualmente:
   - timestamp de estado (`#status-time`)
   - footer
   - botones deshabilitados durante corrida
2. Validar combinaciones de color en una herramienta de contraste WCAG (AA normal text).
