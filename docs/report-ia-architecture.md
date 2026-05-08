# Contrato de Arquitectura de Informacion â€” Reporte UI

Fecha: 2026-05-01

Version base: `0.5.4`

## Objetivo

Definir como se organiza la informacion del reporte para pasar de una vista lineal unica a un dashboard modular con lectura progresiva.

Este documento fija el contrato de diseno previo al embellecimiento visual.

## Principio rector

Primero: que paso.  
Segundo: por que paso.  
Tercero: que hacer.  
Ultimo: auditoria tecnica completa.

No se elimina informacion. Se reordena por prioridad de lectura.

## Navegacion principal propuesta

1. Dashboard
2. Cartera
3. Decision
4. Prediccion
5. Tecnico
6. Bonos y Macro
7. Operaciones
8. Riesgo e Integridad

## Vistas y pregunta de negocio

### 1) Dashboard Ejecutivo (P1)

Pregunta: "Como esta mi cartera hoy y que debo mirar primero?"

Incluye:
- hero / estado de corrida
- integridad resumida (semaforo)
- KPI cards principales
- panorama
- cambios relevantes
- alertas de cartera
- decision resumida
- sizing resumido

### 2) Cartera (P1)

Pregunta: "Que tengo, cuanto pesa y como esta compuesta mi cartera?"

Incluye:
- resumen por tipo
- distribucion por tipo/accion
- cartera maestra
- pendientes de consolidacion
- exposicion por activo/tipo

### 3) Decision y Rebalanceo (P1)

Pregunta: "Que hago con mi cartera?"

Incluye:
- decision final completa
- filtros por ticker/accion/tipo
- convicciones alcistas
- riesgos a recortar
- monitoreo destacado
- evolucion de racha
- sizing completo + drift

### 4) Senales y Prediccion (P1/P2)

Pregunta: "Que espera el sistema y con que confianza?"

Incluye:
- KPIs suba/baja/neutral
- confianza media
- coincidencia clasificador B
- top senales de suba/baja
- acierto historico (global/familia/banda/horizonte)
- detalle completo de prediccion

### 5) Tecnico (P2)

Pregunta: "Que dicen los indicadores tecnicos?"

Incluye:
- overlay tecnico
- mas fuertes / mas debiles
- 52w / SMA200
- RSI / momentum / volumen / drawdown
- tabla tecnica completa

### 6) Bonos y Macro (P2)

Pregunta: "Como impacta el contexto local/macro en la renta fija?"

Incluye:
- KPIs macro locales (CER/REM/tasas/FX/riesgo pais/reservas/UST)
- contexto macro narrativo
- subfamilias
- taxonomia local
- monitoreo completo de bonos

### 7) Operaciones e Historial (P2)

Pregunta: "Que movimientos hubo y como impactaron?"

Incluye:
- operaciones recientes
- trading/eventos/terminadas
- compras/ventas/dividendos/amortizaciones
- resumen por simbolo
- cambios vs snapshot
- tabla completa de operaciones

### 8) Riesgo e Integridad (P2/P3)

Pregunta: "Que tan confiable es el analisis y cuales son sus riesgos?"

Incluye:
- riesgo historico (retorno/vol/drawdown/benchmark/validacion)
- diagnostico completo de riesgo
- integridad y chequeos
- coberturas de datos (Finviz/tecnico/ratings)

## Niveles de lectura

### Nivel 1 â€” Lectura rapida

Siempre visible:
- total cartera, liquidez, ganancia
- estado de regimen
- alertas clave
- decision resumida
- sizing resumido
- integridad general

### Nivel 2 â€” Analisis modular

Visible por vista:
- composicion de cartera
- decision y rebalanceo
- prediccion
- tecnico
- bonos/macro
- operaciones
- riesgo

### Nivel 3 â€” Auditoria tecnica

Colapsable o secundario:
- tablas completas
- taxonomias completas
- diagnosticos extensos
- metodologia/cobertura detallada
- chequeos de integridad completos

## Mapeo bloque actual -> modulo destino

| Bloque actual | Modulo destino | Prioridad |
| --- | --- | --- |
| Header / Hero | Dashboard Ejecutivo | P1 |
| Quick-nav sticky | Layout global | P1 |
| Cards KPI | Dashboard Ejecutivo | P1 |
| Panorama | Dashboard Ejecutivo | P1 |
| Cambios | Dashboard / Prediccion | P1 |
| Operaciones recientes | Operaciones e Historial | P2 |
| Prediccion | Senales y Prediccion | P1 |
| Regimen de mercado | Dashboard + Riesgo (resumen) | P1 |
| Resumen por tipo | Cartera | P1 |
| Riesgo historico | Riesgo e Integridad | P2 |
| Sizing | Decision y Rebalanceo | P1 |
| Overlay tecnico | Tecnico | P2 |
| Bonos Locales | Bonos y Macro | P2 |
| Decision final | Decision y Rebalanceo | P1 |
| Cartera maestra | Cartera | P1 |
| Integridad | Riesgo e Integridad | P2 |

## Mapeo bloque -> componente visual sugerido

| Bloque | Componente sugerido |
| --- | --- |
| KPI financieros | KPI cards |
| Integridad resumida | status strip / badge |
| Estado de regimen | card + chips |
| Cambios relevantes | timeline corto / lista priorizada |
| Alertas de cartera | alert cards |
| Decision resumida | cards por accion |
| Sizing resumido | mini tabla + barra de asignacion |
| Distribucion de cartera | donut o barras horizontales |
| Tabla de decision | data table con filtros |
| Drift | barras comparativas |
| Prediccion suba/baja/neutral | barra apilada |
| Confianza media | gauge |
| Acierto historico | barras/linea |
| Tecnico por ticker | sparkline + chips |
| Bonos/macro | macro cards + tablas |
| Riesgo historico | KPI cards + panel comparativo |
| Integridad detallada | tabla tecnica |

## Backlog de implementacion visual

### P1 â€” Estructura de producto

1. Definir shell de navegacion por modulos (tabs o sidebar).
2. Implementar Dashboard Ejecutivo como nueva portada.
3. Separar Cartera, Decision, Prediccion en modulos primarios.
4. Mantener tablas largas en detalle colapsable por defecto.

### P2 â€” Modulos analiticos

1. Separar Tecnico y Bonos/Macro en vistas propias.
2. Separar Operaciones e Historial en vista propia.
3. Separar Riesgo e Integridad en vista tecnica dedicada.
4. Homogeneizar componentes reutilizables (cards, tables, chips, headers).

### P3 â€” Refinamiento visual

1. Visualizaciones ligeras (sparklines, barras compactas, gauges).
2. Jerarquia tipografica y color por estado semantico.
3. Ajuste responsive por modulo.
4. Revision final de accesibilidad visual.

## Criterios de aceptacion (fase IA)

- Cada vista responde una pregunta de negocio explicita.
- Ninguna tabla larga bloquea la lectura rapida inicial.
- El usuario puede navegar de resumen -> analisis -> auditoria sin perder contexto.
- La informacion actual del reporte sigue disponible (sin perdida funcional).


