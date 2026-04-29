# MAGI Signal Analysis

## Objetivo

Este documento resume el comportamiento observado de Baltasar y Gaspar en el dataset CEO-MAGI generado desde Bot A sub3. El análisis es descriptivo: no entrena CEO-MAGI, no optimiza reglas y no evalúa una estrategia de trading.

## Dataset Analizado

- Run: `data/output/ceo_training/20260429T002335Z_magi_v01_phase2/`
- Registros analizados: 18,600
- Símbolo: EURUSD
- Horizonte principal: 48 barras M5
- Horizontes secundarios: 12, 96 y 288 barras M5

## Baltasar

Baltasar generó:

- BUY: 4,577 votos
- SELL: 5,681 votos
- NEUTRAL: 8,342 votos

En H48:

| Voto | Casos | Hit rate | Avg net directional pips | Avg pips favorables | Avg pips adversos |
|---|---:|---:|---:|---:|---:|
| BUY | 4,573 | 60.35% | 9.67 | 24.37 | 11.98 |
| SELL | 5,652 | 56.76% | 6.67 | 22.00 | 13.04 |
| NEUTRAL | 8,339 | n/a | n/a | 18.27 | 4.88 |

Lectura:

- Baltasar contiene señal direccional.
- BUY fue más limpio que SELL en H48.
- SELL también superó azar direccional, pero con mayor variabilidad y sensibilidad mensual.
- NEUTRAL no debe evaluarse con hit rate direccional; funciona como abstención o zona de baja convicción.

## Gaspar

Gaspar generó en H48:

| Calidad | Casos |
|---|---:|
| GOOD | 2,753 |
| FAIR | 14,903 |
| POOR | 908 |

Lectura:

- Gaspar `GOOD` no fue uniformemente superior en todos los contextos.
- Gaspar parece actuar mejor como filtro contextual condicionado por la dirección de Baltasar.
- El comportamiento agregado `GOOD > FAIR > POOR` no aparece de forma estable en esta muestra.

## Interacción Baltasar + Gaspar

En H48:

| Grupo | Casos | Hit rate | Avg net directional pips | Mediana | P25 | P75 |
|---|---:|---:|---:|---:|---:|---:|
| BUY + GOOD | 128 | 78.12% | 26.30 | 20.65 | 4.70 | 53.18 |
| SELL + GOOD | 2,449 | 55.70% | 3.94 | 5.50 | -7.70 | 17.20 |
| NEUTRAL + GOOD | 176 | n/a | n/a | n/a | n/a | n/a |

Lectura:

- `BUY + GOOD` fue la combinación más fuerte, pero tiene muestra pequeña.
- `SELL + GOOD` no mejoró claramente la señal SELL.
- Gaspar parece discriminar mejor calidad contextual en BUY que en SELL.

## BUY Vs SELL

Resumen por horizonte:

| Horizonte | BUY hit | BUY net | SELL hit | SELL net |
|---:|---:|---:|---:|---:|
| 12 | 51.13% | 4.20 | 48.42% | 3.15 |
| 48 | 60.35% | 9.67 | 56.76% | 6.67 |
| 96 | 57.80% | 11.63 | 57.72% | 7.20 |
| 288 | 50.71% | 8.72 | 55.62% | 6.32 |

Observaciones:

- H48 fue el punto más claro para BUY.
- H96 mantuvo señal estable para ambos lados.
- H288 pierde claridad en BUY y mantiene SELL moderado.
- H12 es más ruidoso.

## Régimen De Mercado

El análisis mensual sugiere heterogeneidad:

- Enero 2026 fue fuerte para BUY y SELL.
- Abril 2026 deterioró SELL de forma marcada.
- BUY se mantuvo positivo en todos los meses observados.
- SELL depende más del régimen mensual y debe validarse fuera de muestra antes de usarse como señal fuerte.

## Observaciones Clave

- Baltasar BUY es la señal individual más consistente en esta muestra.
- Baltasar SELL tiene valor, pero mayor riesgo de régimen.
- Gaspar GOOD potencia BUY cuando coincide, pero no mejora SELL de forma robusta.
- La combinación `BUY + GOOD` merece validación fuera de muestra por su alto hit rate y net pips, aunque el tamaño muestral es limitado.
- No se debe entrenar CEO-MAGI todavía sin validar estabilidad temporal y fuera de muestra.
