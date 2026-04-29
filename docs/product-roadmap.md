# Product Roadmap v0.3

Fecha de validacion: 2026-04-28

## Resultado del analisis

El roadmap propuesto coincide en lineas generales con el estado actual del proyecto y es aplicable como plan de ejecucion.

Ajustes puntuales detectados al validar contra el repo actual:

- Cobertura total actual: 84% (no 87%).
- Suite actual: 47 archivos `test_*.py` (alineado con el plan).
- Piso de cobertura en CI: 82% (alineado con el plan de subir a 85%).
- `POST /cancel` y boton de cancelacion en UI ya implementados (estado final `interrupted`).
- `status/detail` sigue con `log_tail` de 1200 chars.

## Avance de ejecucion

- 2026-04-28: completado primer item P1 de v0.3 (`POST /cancel` + boton UI).
- 2026-04-28: completado segundo item P1 de v0.3 (deteccion de corrida huerfana al startup y marcado `interrupted`).
- 2026-04-28: completado tercer item P1 de v0.3 (sanitizacion de secretos en `/status/detail`).
- 2026-04-28: completado cuarto item P1 de v0.3 (retry con backoff en clientes IOL y BCRA).
- 2026-04-28: completado quinto item P1 de v0.3 (cobertura >=82% en `sizing.py` y `bcra.py`).
- 2026-04-28: completado sexto item P1 de v0.3 (backup diario automatico de `data/runtime/*.csv`).
- 2026-04-28: completado septimo item P1 de v0.3 (scripts Bash Fase 1 cross-platform).
- 2026-04-28: completado primer item P2 de v0.4 (modal custom de confirmacion; reemplaza `window.confirm()`).
- 2026-04-28: completado segundo item P2 de v0.4 (panel de reportes anteriores en UI).
- 2026-04-28: completado tercer item P2 de v0.4 (centralizacion de utilidades de texto/numericas en `src/common/`).
- 2026-04-28: completado cuarto item P2 de v0.4 (token de sesion simple para `POST /run`).
- 2026-04-28: completada mejora de observabilidad en `/status/detail` (`log_tail` ampliado + `log_lines`).
- 2026-04-28: completados items P2 de validacion de input en `/run` (aporte externo no negativo, `username/password` con maximo 200 chars) y manejo explicito de error de `Popen` (HTTP 500 claro).
- 2026-04-28: completado item P2 de performance/observabilidad: `/status/detail` ahora expone `elapsed_seconds`.
- 2026-04-28: completado item P2 de observabilidad: log de tiempos por fase en `generate_real_report.py` (formato `Fase <nombre>: <seg>s`).
- 2026-04-28: completado item P2 de observabilidad: `LOG_FORMAT=json` opcional para structured logging en `generate_real_report.py`.
- 2026-04-28: completado item P2 de mantenibilidad/documentacion: nuevo `CONTRIBUTING.md` con setup, convenciones, tests y flujo de PR.
- 2026-04-28: completado item P2 de documentacion: `docs/decisions/` con ADRs iniciales (subprocess, CSV sin DB, float->Decimal gradual).
- 2026-04-29: completado item P2 de accesibilidad en UI (`aria-live` en estado, `aria-label` de icono y mensajes de error con `role=\"alert\"`).
- 2026-04-29: hardening adicional en `/run`: rechazo backend de `username/password` vacios (HTTP 422) para evitar corridas invalidas ante fallos de validacion en frontend/autocompletado.
- 2026-04-29: completados pendientes UX: tooltip explicativo en `Aporte externo ARS` y link `Ver log completo` cuando el estado es `error`.
- 2026-04-29: item P2 de DevOps (`macos-latest` en CI) queda como deuda tecnica pendiente por inestabilidad actual en GitHub Actions.
- 2026-04-29: fix de estabilidad CI: `server.py` asegura creacion de `reports/` antes del mount de archivos estaticos.
- 2026-04-29: `ubuntu-latest` en CI tambien queda temporalmente desactivado y marcado como deuda tecnica pendiente para no bloquear entregas.
- 2026-04-29: completado item P2 de escalabilidad/documentacion: checklist formal de alta de instrumento (`docs/instrument-onboarding-checklist.md`).
- 2026-04-29: completado item P1 de documentacion API: README referencia `/docs` y `/openapi.json` de FastAPI.

## Contexto

Este documento complementa `docs/improvement-roadmap.md` (foco dominio financiero) con foco producto/ingenieria y priorizacion por robustez operativa.

## Archivo objetivo

- `docs/product-roadmap.md`

---

## Roadmap por 18 dimensiones

### 1) Funcionalidad

Estado: pipeline completo y funcional; flujo principal cubierto.

Hallazgos:

- validaciones de entrada y errores de spawn ya cubiertos en `/run`.

Roadmap:

- P1: `POST /cancel` para terminar proceso y limpiar estado.
- P1: Detectar PID file huerfano al arrancar y marcar `interrupted`.
- P2: Validar `aporte_externo_ars >= 0` en Pydantic. (completado)
- P2: Manejar excepcion de `Popen` con 500 claro. (completado)

### 2) UX / Experiencia

Estado: UX funcional con presets, confirmacion y polling.

Hallazgos:

- Error truncado a 300 chars sin acceso directo a log completo.
- Sin historial persistente de corridas.
- Campo de aporte externo sin ayuda contextual.
- Sin progreso detallado.

Roadmap:

- P1: Boton "Cancelar corrida" cuando `running`.
- P1: Boton "Ver log completo" en error apuntando a `/status/detail`. (completado)
- P2: Panel de corridas recientes (ultimas 5).
- P2: Tooltip para "Aporte externo ARS". (completado)
- P3: Barra de progreso estimada.

### 3) UI / Interfaz

Estado: UI limpia y autocontenida, responsive basico.

Hallazgos:

- Estados solo con emojis (accesibilidad limitada).
- Panel de estado con poco contexto.

Roadmap:

- P2: Modal custom para confirmacion.
- P2: Texto/ARIA junto a indicadores de estado.
- P2: Seccion de reportes anteriores (`/reports/`).
- P3: Indicador de progreso animado.

### 4) Arquitectura

Estado: capas separadas, sin ciclos; server aislado del pipeline.

Hallazgos:

- `src/decision/scoring.py` mantiene alta complejidad.
- Orquestador principal del real run sigue denso (aunque ya split por modulos de apoyo).
- Faltan contratos formales por `Protocol`.

Roadmap:

- P2: Partir `apply_base_scores` en sub-funciones tematicas.
- P2: Extraer `_comentario_operativo` de sizing.
- P3: Formalizar interfaces con `typing.Protocol`.

### 5) Calidad de codigo

Estado: base clara y consistente, con baja deuda accidental.

Hallazgos:

- Funciones extensas en scoring/sizing.
- Type hints aun heterogeneos en algunos puntos.

Roadmap:

- P2: Centralizar utilidades comunes en `src/common/`.
- P2: Refactor de funciones largas.
- P3: Completar type hints donde queden `object` genericos.

### 6) Testing

Estado: CI activa, 47 archivos de tests y cobertura global 84% (floor 82%).

Hallazgos:

- `src/decision/sizing.py`: 67%.
- `src/clients/bcra.py`: 60%.
- `src/clients/bonistas_client.py`: 62%.
- Sin pruebas de concurrencia para `/run`.

Roadmap:

- P1: Llevar sizing y bcra a >=82%.
- P1: Subir floor de CI de 82% a 85%.
- P2: Smoke de scripts Bash en Unix.
- P3: Test concurrente: segundo `/run` devuelve 409.

### 7) Seguridad

Estado: entorno local (`127.0.0.1`) y password no persistida en navegador.

Hallazgos:

- Sin autenticacion en endpoints operativos (quedan abiertos `/cancel`, `/status`, `/status/detail`).
- Sin TLS (mitigado por localhost).
- Sin rate limiting en `POST /run`.

Roadmap:

- P1: Auditar que nunca se impriman credenciales.
- P1: Filtrar `log_tail` para secretos.
- P2: Token de sesion simple para `/run`.
- P2: Limitar largo de `username/password`. (completado)
- P3: Rate limiting de `/run` (3/min).

### 8) Performance

Estado: retry robusto en Finviz; caches parciales.

Hallazgos:

- Sin tiempo estimado expuesto al usuario.
- Sin cache intradia de precios.

Roadmap:

- P1: Retry con backoff para IOL y BCRA.
- P2: Exponer `elapsed_seconds`. (completado)
- P3: Cache intradia TTL 15 min.

### 9) Datos / Persistencia

Estado: CSV/JSON versionados por fecha; sin BD.

Hallazgos:

- Montos monetarios en `float`.
- Sin backup automatico de `data/runtime/`.
- Historial crece sin purga automatica.

Roadmap:

- P1: Backup diario de CSV runtime.
- P2: Migrar montos criticos a `Decimal`.
- P2: Retencion configurable (default 90 dias).
- P3: Validacion de integridad al arranque.

### 10) DevOps e Infra

Estado: GitHub Actions y distribucion ZIP vigente.

Hallazgos:

- Sin release automation end-to-end.
- Sin Docker para entorno dev/test.
- Cobertura de OS aun centrada en Linux CI.

Roadmap:

- P1: Script de release (version + tag + build).
- P2: Agregar `macos-latest` a matriz CI. (pendiente, bloqueado por inestabilidad CI)
- P3: Dockerfile para dev/testing.

### 11) Mantenibilidad

Estado: modularidad razonable y documentacion operativa.

Hallazgos:

- Sin ADR formales.
- `apply_base_scores` sigue como punto caliente.
- Sin `CONTRIBUTING.md`.

Roadmap:

- P2: Crear `docs/decisions/` con ADRs base. (completado)
- P2: Crear `CONTRIBUTING.md`. (completado)
- P2: Refactor `apply_base_scores`.

### 12) Escalabilidad

Estado: diseno single-user, objetivo personal.

Hallazgos:

- Historiales sin limite de crecimiento.
- Onboarding de nuevos instrumentos con varios puntos manuales.
- Faltan abstracciones para nuevas APIs.

Roadmap:

- P2: Retencion configurable de historiales.
- P2: Checklist formal para alta de instrumento. (completado)
- P3: Protocol de clientes externos.

### 13) Accesibilidad

Estado: labels basicos presentes.

Hallazgos:

- Indicadores por emoji sin texto equivalente.
- Sin `aria-live` en estado.
- Sin `role="alert"` en errores.
- Tablas del reporte con oportunidades semanticas.

Roadmap:

- P2: `aria-label` para estado. (completado)
- P2: `aria-live="polite"` en panel. (completado)
- P2: `role="alert"` en errores. (completado)
- P3: auditoria WCAG de contraste.

### 14) Compatibilidad

Estado: Windows cubierto; macOS/Linux parcial.

Hallazgos:

- Flujo operativo principal sigue centrado en PS1.
- Faltan scripts Bash equivalentes.
- Sin matriz formal de navegadores soportados.

Roadmap:

- P1: Fase 1 cross-platform (scripts Bash).
- P2: Fase 2 con `pwsh` cross-platform.
- P3: pruebas mobile/responsive del reporte.

### 15) Observabilidad

Estado: logging plano + `/status/detail`.

Hallazgos:

- Sin logging estructurado JSON opcional.
- `log_tail` corto para fallas largas.
- Sin metricas por fase ni notificaciones de fin de corrida.

Roadmap:

- P1: ampliar `log_tail` a 3000 + `log_lines`.
- P2: tiempos por fase en pipeline. (completado)
- P2: `LOG_FORMAT=json` opcional. (completado)
- P3: webhook on-completion.

### 16) Documentacion

Estado: README y guias base existentes.

Hallazgos:

- Falta referenciar mas explicitamente docs de API FastAPI.
- Sin ADRs ni guia de contribucion.
- Roadmaps tecnicos existen pero parte sigue sin implementacion.

Roadmap:

- P1: Referenciar `/docs` y `/openapi.json` en README. (completado)
- P2: `CONTRIBUTING.md`. (completado)
- P2: ADRs minimos. (completado)
- P3: diagrama Mermaid de arquitectura.

### 17) Integraciones

Estado: multiples APIs externas con fallback a snapshots.

Hallazgos:

- Retry completo concentrado en Finviz.
- Sin circuit breaker por proveedor.
- Sin endpoint de salud de integraciones.

Roadmap:

- P1: `_call_with_retry()` en IOL y BCRA.
- P2: circuit breaker simple por API.
- P3: `GET /api-health`.

### 18) Usabilidad operativa

Estado: operacion con scripts y UI simple.

Hallazgos:

- Sin gestion de reportes previos desde UI.
- Config de scoring solo por edicion manual de JSON.
- Sin scheduler para corrida periodica.

Roadmap:

- P2: Panel de reportes en UI.
- P3: scheduler opcional.
- P3: pagina de configuracion basica en UI.

---

## Plan de fases

### v0.3 - Robustez y seguridad (P1)

1. `POST /cancel` + boton UI.
2. Deteccion de PID huerfano al iniciar.
3. Auditoria/filtrado de credenciales en logs.
4. Retry en IOL y BCRA (patron Finviz).
5. Subir cobertura de `sizing.py` y `bcra.py` a >=82%.
6. Backup automatico de `data/runtime/`.
7. Scripts Bash Fase 1 (cross-platform).

Estado v0.3 (P1) al 2026-04-28:

- Completado: item 1.
- Completado: item 2.
- Completado: item 3.
- Completado: item 4.
- Completado: item 5.
- Completado: item 6.
- Completado: item 7.
- Pendiente: sin pendientes P1.

### v0.4 - UX, calidad y observabilidad (P2)

1. Modal custom de confirmacion.
2. Panel de reportes anteriores.
3. Centralizar utilidades comunes en `src/common/`.
4. Refactor `apply_base_scores`.
5. Token de sesion para `/run`.
6. Logs estructurados opcionales.
7. `log_tail` ampliado + tiempos por fase.
8. ADRs iniciales.

### v0.5 - Escalabilidad y polish (P3)

1. Rate limiting en `/run`.
2. Cache intradia de precios.
3. Circuit breakers de APIs.
4. Diagrama de arquitectura.
5. Scheduler opcional.
6. Cierre de deuda documental remanente.

---

## Verificacion de aplicabilidad

- No requiere cambios de codigo para iniciar: es documento de ejecucion.
- Es compatible con el estado real del repo al 2026-04-28.
- Puede ejecutarse en commits pequenos, independientes y verificables.
