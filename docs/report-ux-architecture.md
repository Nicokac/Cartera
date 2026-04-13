# Arquitectura UX/UI del Reporte

## Objetivo

Definir una arquitectura nueva para el reporte HTML que mejore:

- prioridad visual
- velocidad de lectura
- foco ejecutivo
- trazabilidad de cambios entre corridas
- escalabilidad de la interfaz a medida que el motor sume mas senales

Este documento describe la estructura objetivo. La fase inicial ya fue implementada y validada en corrida real al `2026-04-11 15:13`.

## Estado actual

La nueva arquitectura ya quedo aplicada en una primera version completa:

- portada ejecutiva con `Panorama`, KPIs priorizados y `Sizing activo`
- bloque de `Cambios materiales` con limpieza de ruido neutral-neutral
- `Decision final` con vista priorizada antes de la tabla completa
- `Overlay tecnico` y `Bonos Locales` con capas de sintesis antes del detalle
- navegacion sticky y detalle colapsable para secciones pesadas

Baseline visual validada:

- mejor jerarquia de lectura
- menor dominancia de tablas largas
- menor ruido en cambios de accion
- tabla completa de decision relegada a segunda capa
- criterio de score consolidado en un bloque general, no repetido por fila

## Cierre de iteracion

La iteracion inicial de UX/UI puede considerarse cerrada con estos puntos:

- arquitectura de cuatro capas ya implementada
- validacion con corridas reales sucesivas
- cleanup de ruido en cambios de accion
- microcopy estabilizado
- tabla completa de decision compactada hasta un nivel aceptable

Lo que queda a futuro ya no es rediseño base. Es polish menor o una nueva fase si aparece evidencia real de friccion.

## Principios

- primero decision, despues detalle
- primero cambios, despues stock
- primero lectura ejecutiva, despues lectura analitica
- menos tablas dominantes
- mas bloques de sintesis y comparacion
- mantener portabilidad del HTML estatico
- no romper el contrato actual del pipeline

## Problema actual

Hoy el reporte funciona, pero la UX tiene estos limites:

- demasiada densidad tabular
- poca separacion entre lo importante y lo accesorio
- la portada muestra KPIs, pero no cuenta bien que cambio
- la decision final compite visualmente con tablas secundarias
- el overlay tecnico y bonos consumen mucho espacio cognitivo
- la pagina escala peor a medida que crecen columnas y senales

## Estructura objetivo

La pagina deberia reorganizarse en cuatro capas:

1. lectura ejecutiva
2. decision operativa
3. diagnostico analitico
4. detalle completo

## Capa 1: Lectura Ejecutiva

Debe responder en menos de 15 segundos:

- que cambio hoy
- que exige accion
- cual es el sizing sugerido
- que riesgos o faltantes de cobertura existen

### Bloques propuestos

#### 1. Hero de corrida

Mantener:

- tipo de corrida
- fecha y hora
- lede corto

Mejorar:

- convertirlo en cabecera realmente ejecutiva
- incluir una bajada sintetica con el estado de la cartera

Ejemplo de contenido:

- regimen activo
- numero de refuerzos y reducciones
- cobertura Finviz y tecnica

#### 2. KPI strip principal

Reducir la cantidad de tarjetas visibles en la primera fila.

Prioridad:

- total consolidado
- liquidez
- MEP
- refuerzos
- reducciones
- sizing activo

Mover KPIs secundarios a una segunda capa o bloque desplegable.

#### 3. Resumen de cambios

Nuevo bloque obligatorio.

Debe mostrar:

- senales nuevas
- refuerzos persistentes
- reducciones persistentes
- activos que cambiaron de accion
- cambios de sizing respecto de la corrida anterior

Este bloque es la pieza mas importante que hoy falta.

#### 4. Top acciones del dia

Nuevo bloque de highlight.

Subbloques:

- prioridades de compra o refuerzo
- prioridades de reduccion
- observaciones tacticas

Formato sugerido:

- cards o lista corta de 3 a 6 items
- no tabla

## Capa 2: Decision Operativa

Debe responder:

- que hago con cada activo importante
- por que
- con que conviccion relativa

### Bloques propuestos

#### 1. Decision priorizada

Reemplazar la tabla plana como primera vista por una lista priorizada.

Orden sugerido:

- senales nuevas
- refuerzos
- reducciones
- neutrales relevantes

Cada item deberia mostrar:

- ticker
- accion
- score
- racha
- drivers
- motivo resumido

La tabla completa puede quedar debajo como vista expandida.

#### 2. Tabla completa de decision

Mantenerla, pero como segunda capa.

Mejoras sugeridas:

- filtros mas utiles
- orden visual por accion
- resaltado de filas que cambiaron desde la corrida previa
- opcion de ver solo cambios

#### 3. Sizing operativo

Elevarlo visualmente.

Hoy el sizing existe, pero no domina la lectura.
Deberia verse como una salida principal del motor.

Mostrar:

- fuente de fondeo
- monto
- top asignaciones
- buckets de prudencia

## Capa 3: Diagnostico Analitico

Debe explicar el por que del motor, no competir con la decision.

### Bloques propuestos

#### 1. Regimen de mercado

Mantenerlo arriba del detalle tecnico, pero con mejor jerarquia visual.

Debe verse como contexto de decision, no como metadata perdida.

#### 2. Overlay tecnico

Separar dos vistas:

- resumen tecnico
- tabla completa

Resumen tecnico:

- activos mas fuertes
- activos mas debiles
- nombres cerca de maximos anuales
- nombres por debajo de SMA200

Tabla completa:

- queda para analisis detallado

#### 3. Bonos locales

Mantener, pero colapsado o en una seccion secundaria.

Priorizar arriba:

- contexto macro
- resumen por subfamilia

Dejar abajo:

- monitoreo completo

#### 4. Integridad y cobertura

Moverlo a una posicion menos dominante que hoy.

Es importante, pero no deberia aparecer antes que la lectura ejecutiva.

## Capa 4: Detalle Completo

Reservada para auditoria y revision profunda.

### Bloques

- cartera maestra completa
- tabla tecnica completa
- tabla de bonos completa
- chequeos de integridad

Esta capa sigue siendo necesaria, pero no debe mandar la experiencia.

## Navegacion objetivo

La navegacion deberia reflejar prioridad real:

1. Panorama
2. Cambios
3. Decision
4. Sizing
5. Regimen
6. Tecnico
7. Bonos
8. Cartera
9. Integridad

Si seguimos con nav horizontal:

- deberia ser sticky
- deberia resaltar la seccion activa

Si damos un salto mayor:

- conviene pasar a sidebar en desktop

## Componentes UI propuestos

### Mantener

- cards KPI
- badges de accion
- chips de drivers
- tablas con scroll horizontal

### Agregar

- callouts de cambio
- cards de prioridad
- bloques resumidos por categoria
- secciones colapsables
- resaltado visual de cambios vs corrida previa
- indicadores de cobertura con severidad

### Reducir

- tablas como primer formato de lectura
- exceso de KPI equivalentes en la portada
- densidad de metadata secundaria en hero y bloques altos

## Estrategia de implementacion

No conviene hacer un rediseño total en un solo paso.

## Fase 1

Objetivo:

- reordenar la jerarquia sin romper contenido

Trabajo:

- nueva portada ejecutiva
- bloque de cambios
- sizing mas visible
- mover integridad al final

## Fase 2

Objetivo:

- mejorar lectura de decision

Trabajo:

- lista priorizada de decisiones
- tabla completa como segunda capa
- filtros mejores
- resaltado de cambios

## Fase 3

Objetivo:

- mejorar lectura analitica

Trabajo:

- resumen tecnico antes de la tabla
- bonos con resumen arriba y detalle abajo
- cobertura e integridad mas claras

## Fase 4

Objetivo:

- refinar interaccion y look & feel

Trabajo:

- nav sticky o sidebar
- colapsables
- mejor ritmo visual
- estados vacios y mensajes de error mas expresivos

## Restricciones tecnicas

- seguir generando un HTML estatico
- no introducir dependencia frontend pesada
- mantener compatibilidad con `generate_smoke_report.py`
- mantener compatibilidad con `generate_real_report.py`
- no alterar el contrato de datos solo por razones visuales

## Criterio de exito

El rediseño se considera bueno si:

- un usuario entiende en menos tiempo que cambio
- el sizing se identifica sin buscarlo
- la decision final domina la lectura
- el detalle sigue estando disponible sin saturar la portada
- la version smoke y la real conservan la misma arquitectura visual
