# MAGI Session Summary - 2026-05-01

## 1. Resumen ejecutivo

MAGI avanz? desde experimentos aislados hacia una arquitectura experimental con roles m?s claros para los tres magos v2. Baltasar v2 act?a como motor direccional experimental, Gaspar v2.1c como filtro din?mico de deterioro y Melchor v2 como capa de riesgo acumulado basada en reglas.

El hallazgo principal de la sesi?n es que Baltasar v2, Gaspar v2.1c y Melchor v2 ya tienen responsabilidades diferenciadas. El sistema todav?a no est? listo para live/demo real, pero ya muestra edge proxy validado bajo RR 1:2 first-touch y mecanismos experimentales de control de riesgo.

No se debe declarar rentabilidad final. Falta integraci?n completa, validaci?n walk-forward del sistema conjunto y backtest institucional con costos reales, slippage, bid/ask, comisiones y reglas de no solapamiento operativo.

## 2. Qu? se hizo hoy

1. Se ejecut? la simulaci?n R final de Baltasar v2 `rich_policy_medium` para thresholds 0.40 y 0.50.
2. Se reconstruy? el dataset full 2020-2026 para Gaspar v2 desde la base correcta.
3. Se entren? Gaspar v2 context classifier y se comprob? que el enfoque trade-by-trade era d?bil.
4. Se redise?? Gaspar v2.1 como detector de r?gimen/deterioro.
5. Se construy? Gaspar v2.1c rolling/causal con features que usan solo pasado.
6. Se entren? Gaspar v2.1c como filtro de deterioro din?mico.
7. Se integr? Baltasar v2 + Gaspar v2.1c y se compar? contra Baltasar solo.
8. Se analiz? el fallo 2026Q2 y se identific? que era m?s riesgo acumulado que contexto t?cnico puro.
9. Se construy? Melchor v2 risk dataset como capa de riesgo acumulado.
10. Se entren? Melchor v2 ML baseline y se descart? como candidato estable.
11. Se evalu? Melchor v2 rule-aware sin ML.
12. Se valid? cobertura m?nima y estabilidad temporal de Melchor rule-layer.

## 3. Resultados clave

### Baltasar v2 rich_policy_medium

| Threshold | Avg R | Profit Factor | Max DD | Lectura |
| --- | ---: | ---: | ---: | --- |
| 0.40 | +0.0795 | 1.1405 | 348.18 | M?s cobertura, edge moderado |
| 0.50 | +0.1893 | 1.3496 | 134.09 | M?s defensivo, menos trades |

Baltasar v2 confirma se?al direccional proxy bajo RR 1:2 first-touch, pero no resuelve por s? solo deterioros como 2026Q2.

### Gaspar v2.1c

Gaspar v2.1c como clasificador ML puro fue d?bil, pero como filtro operativo aport? valor.

| M?trica test | Baltasar v2 solo | Baltasar + Gaspar |
| --- | ---: | ---: |
| Avg R | 0.0932 | 0.1152 |
| Profit Factor | 1.1621 | 1.2033 |
| Max DD | 266.14 | 240.14 |

Gaspar mejora especialmente SELL, pero no detecta 2026Q2. Eso confirma que Gaspar debe ser filtro de deterioro din?mico, no guardi?n final de riesgo acumulado.

### Melchor v2

El baseline ML de Melchor v2 fue descartado: bajo macro F1, bajo recall de BLOCK y sin captura ?til de 2026Q2.

La capa rule-aware fue claramente superior.

| Candidato | Coverage test | Avg R | PF | DD | Lectura |
| --- | ---: | ---: | ---: | ---: | --- |
| combined_risk_rule BLOCK | 43.4% | 0.5386 | 2.2919 | 41.16 | Candidato principal |
| q2_like_proxy BLOCK+CAUTION | 44.2% | 0.3727 | 1.7765 | 52.27 | Alternativa conservadora |
| combined_risk_rule BLOCK+CAUTION | 30.2% | 0.5628 | 2.3725 | 35.12 | Muy agresiva |

## 4. Diagn?stico honesto

Baltasar propone operaciones. Gaspar filtra deterioro din?mico. Melchor protege con reglas de riesgo acumulado. Esta separaci?n de roles es el avance t?cnico m?s importante de la sesi?n.

2026Q2 demostr? que el fallo no era principalmente direccional ni de contexto t?cnico. El patr?n fue deterioro operativo acumulado: rolling PF bajo, drawdown alto, SELL PF bajo, loss streak elevado y unfavorable rate alto. Por eso Melchor debe ser risk-layer, no predictor ML puro.

MAGI todav?a no est? listo para producci?n ni demo operativa real. Lo validado hasta ahora es proxy experimental con first-touch RR 1:2, no rentabilidad institucional.

## 5. Estado actual por m?dulo

| M?dulo | Estado | Rol actual | Decisi?n |
| --- | --- | --- | --- |
| Baltasar v2 | Candidato experimental | Direcci?n operable RR 1:2 | Mantener |
| Gaspar v2.1c | Filtro experimental | Deterioro din?mico | Integrar como filtro |
| Melchor v2 | Rule-layer experimental | Riesgo acumulado | Usar reglas, no ML puro |
| CEO v3 | Pendiente | Orquestaci?n final | Construir despu?s de integraci?n completa |
| Backtest institucional | Pendiente | Validaci?n realista | Requerido antes de demo/live |

## 6. Riesgos pendientes

- Falta integraci?n completa Baltasar + Gaspar + Melchor.
- Falta validaci?n walk-forward del sistema conjunto.
- Falta incorporar costos reales, slippage, comisiones, bid/ask y no solapamiento operativo.
- Falta decidir c?mo CEO v3 consumir? votos, probabilidades, bloqueos y cautelas.
- Existe riesgo de sobreoptimismo por proxy RR 1:2 y reglas derivadas de an?lisis hist?rico.
- La cobertura de Melchor debe tratarse como restricci?n de producto, no solo como m?trica t?cnica.

## 7. Plan para pr?xima sesi?n

### Prioridad 1

Integrar sistema completo:

- Baltasar v2 rich_policy_medium threshold 0.40.
- Gaspar v2.1c bloqueando deterioro din?mico.
- Melchor v2 `combined_risk_rule BLOCK` como candidato principal.
- Melchor v2 `q2_like_proxy BLOCK+CAUTION` como alternativa.

### Prioridad 2

Comparar cuatro configuraciones:

| Configuraci?n | Objetivo |
| --- | --- |
| Baltasar solo | Baseline direccional |
| Baltasar + Gaspar | Filtro din?mico |
| Baltasar + Gaspar + Melchor combined_risk_rule BLOCK | Candidato principal |
| Baltasar + Gaspar + Melchor q2_like_proxy BLOCK+CAUTION | Alternativa conservadora |

### Prioridad 3

Validaci?n temporal del sistema conjunto:

- A?o.
- Trimestre.
- Mes.
- BUY/SELL.
- Drawdown.
- Cobertura mensual y trimestral.
- 2026Q2.

### Prioridad 4

Si la integraci?n completa mejora de forma estable, preparar dataset para CEO v3 con entradas de Baltasar, Gaspar y Melchor.

## 8. Conclusi?n

MAGI no est? listo para producci?n, pero ya tiene una arquitectura experimental funcional donde cada mago empieza a cumplir su rol. Baltasar genera se?al direccional, Gaspar reduce deterioro din?mico y Melchor controla riesgo acumulado con reglas m?s efectivas que ML puro. La siguiente decisi?n cr?tica es validar si la integraci?n completa mantiene edge, cobertura y estabilidad temporal antes de dise?ar CEO v3.
