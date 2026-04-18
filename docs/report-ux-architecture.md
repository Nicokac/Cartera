# Arquitectura UX/UI del Reporte

## Objetivo

Documentar la arquitectura vigente del reporte HTML y la deuda de diseño que todavia queda abierta.

## Estado actual

La arquitectura base del reporte ya esta implementada y estable:

- portada ejecutiva con `Panorama`
- bloque visible de `Cambios`
- `Decision` priorizada antes de la tabla completa
- `Sizing` y `Regimen` en primera capa
- capas analiticas separadas para tecnico y bonos
- detalle completo relegado a bloques secundarios

## Capas vigentes

### 1. Lectura ejecutiva

Debe responder rapido:

- que cambio
- que pide accion
- si hay sizing activo
- si existe alguna alerta operacional

Bloques:

- hero de corrida
- KPIs principales
- `Panorama`
- `Cambios`
- highlights de decision

### 2. Decision operativa

Debe exponer:

- refuerzos activos
- reducciones activas
- monitoreo relevante
- tabla completa como segunda capa

### 3. Diagnostico analitico

Debe explicar el contexto:

- regimen de mercado
- overlay tecnico resumido
- bonos locales resumidos
- coberturas y notas del pipeline

### 4. Detalle completo

Reservado para auditoria y revision profunda:

- cartera completa
- tabla tecnica completa
- monitoreo completo de bonos
- chequeos de integridad

## Principios vigentes

- primero decision, despues detalle
- primero cambios, despues stock estable
- primero resumen ejecutivo, despues explicacion analitica
- mantener HTML estatico portable
- no cambiar contratos del pipeline solo por UX

## Deuda abierta

La mayor deuda ya no es de producto sino de estructura:

- `scripts/report_renderer.py` sigue siendo el orquestador mas grande del repo
- `render_report()` todavia concentra demasiado ensamblado
- parte del crecimiento del renderer se explica por sumar secciones nuevas sin seguir fragmentando helpers

## Objetivo de la proxima iteracion

La siguiente mejora razonable no es rediseñar la UX base. Es seguir partiendo el renderer por secciones:

1. header y KPIs
2. decision
3. operaciones
4. analitica
5. detalle y tablas

## Restricciones tecnicas

- seguir generando HTML estatico
- mantener compatibilidad entre smoke y real run
- no introducir dependencia frontend pesada
- no duplicar logica de negocio dentro de helpers visuales

## Criterio de exito

La arquitectura se considera sana si:

- el usuario entiende el estado de la corrida sin leer tablas largas
- los cambios materiales dominan la lectura
- el sizing no queda enterrado
- el detalle sigue disponible sin contaminar la portada
- el renderer principal baja de tamaño sin repartir logica de negocio de forma caotica
