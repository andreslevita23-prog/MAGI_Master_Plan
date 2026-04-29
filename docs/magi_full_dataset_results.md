# MAGI Full Dataset Results

## Qué Se Hizo

Se preparó un dataset limpio de Bot A sub3 y se generó un dataset CEO-MAGI sobre seis años de datos.

- Fuente limpia: `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`.
- Periodo: 2020-01-15 a 2026-04-14.
- Símbolo: EURUSD.
- Timeframe: M5.
- Snapshots procesados: 371,513.
- Registros CEO generados: 371,501.
- Magos reales: Melchor, Baltasar y Gaspar.
- Horizontes: 12, 48, 96 y 288 barras M5.

No se entrenó CEO-MAGI. No se optimizaron reglas. No se modificaron modelos.

## Calidad Del Dataset

El dataset limpio eliminó campos prohibidos y mantuvo flags de calidad.

- Duplicados finales: 0.
- Claves futuras/prohibidas restantes: 0.
- `is_high_spread`: 1,467 registros.
- `has_gap_forward`: 419 registros.
- Rango temporal ordenado: sí.

## Distribución De Votos

| Mago | Clase | Conteo |
|---|---|---:|
| Melchor | APPROVE | 232,316 |
| Melchor | BLOCK | 139,185 |
| Baltasar | BUY | 106,395 |
| Baltasar | SELL | 127,484 |
| Baltasar | NEUTRAL | 137,622 |
| Gaspar | GOOD | 72,784 |
| Gaspar | FAIR | 278,606 |
| Gaspar | POOR | 20,111 |

## Resultados Globales H48

| Señal | Casos | Hit rate | Net pips | Mediana |
|---|---:|---:|---:|---:|
| Baltasar BUY | 106,391 | 45.13% | 1.08 | 0.90 |
| Baltasar SELL | 127,455 | 44.15% | 0.79 | -0.60 |
| BUY + GOOD | 2,066 | 47.73% | 3.04 | 2.00 |
| SELL + GOOD | 68,608 | 44.51% | 0.31 | -0.70 |

## Comparación 4 Meses Vs 6 Años

El análisis de cuatro meses mostraba señales mucho más fuertes:

- BUY H48 cerca de 60%.
- BUY + GOOD cerca de 78%.
- SELL + GOOD relativamente aceptable.

En seis años:

- BUY cae a 45.13%.
- BUY + GOOD cae a 47.73%.
- SELL queda débil.
- Gaspar GOOD no domina globalmente.

Conclusión: el periodo corto capturó un régimen favorable, no una regla estable global.

## Baltasar

Baltasar conserva señal débil, pero no suficiente como motor aislado.

- BUY sigue siendo mejor que SELL en algunos regímenes.
- SELL es más sensible a spread, hora y mes.
- La señal direccional global es pequeña.

## Gaspar

Gaspar GOOD no es robusto globalmente:

| Calidad | Casos H48 | Hit rate direccional | Avg return |
|---|---:|---:|---:|
| GOOD | 72,755 | 44.60% | -0.19 |
| FAIR | 278,602 | 44.55% | 0.15 |
| POOR | 20,108 | 45.24% | 0.19 |

La calibración de Gaspar debe revisarse.

## Régimen

Mejores segmentos H48 con muestra suficiente:

| Segmento | Valor | Señal | Hit | Net pips |
|---|---|---|---:|---:|
| month | 2026-01 | Baltasar BUY | 66.80% | 17.01 |
| month | 2026-01 | Baltasar SELL | 74.37% | 15.74 |
| month | 2026-01 | SELL + GOOD | 74.36% | 12.06 |
| month | 2022-11 | Baltasar BUY | 55.67% | 11.07 |
| month | 2026-03 | Baltasar SELL | 64.12% | 9.63 |

Peores segmentos H48:

| Segmento | Valor | Señal | Hit | Net pips |
|---|---|---|---:|---:|
| m5_range_bucket | 10-20 | Gaspar POOR | 34.12% | -11.17 |
| month | 2022-04 | Gaspar POOR | 28.02% | -9.83 |
| month | 2020-03 | SELL + GOOD | 39.73% | -8.68 |
| month | 2025-03 | SELL + GOOD | 37.80% | -7.12 |
| month | 2022-04 | Baltasar BUY | 34.24% | -6.79 |

## Hallazgo Central

Los votos solos no son suficientes.

La señal aparece cuando se combina:

- voto
- confianza
- sesión
- hora UTC
- spread
- rango M5
- estructura H4/D1
- ATR diario consumido
- posición en rango D1

CEO-MAGI debe ser un modelo de decisión contextual, no un simple votador mayoritario.

## Implicación

No conviene entrenar CEO-MAGI como modelo final todavía. El siguiente paso debe ser un baseline interpretable con split temporal y walk-forward, usando régimen como feature obligatoria.
