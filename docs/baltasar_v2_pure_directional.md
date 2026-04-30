# Baltasar v2 Pure Directional

## Objetivo

Entrenar una variante direccional pura de Baltasar v2 usando solo variables de mercado/timing, sin votos de otros magos ni señales agregadas.

Target:

- `tradeable_direction_rr2_first_touch`

Clases:

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

## Input

- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet`

## Script

- `scripts/magi_v2/train_baltasar_v2_pure_directional.py`

## Outputs

- `data/output/magi_v2/baltasar_v2_pure_directional/train.parquet`
- `data/output/magi_v2/baltasar_v2_pure_directional/validation.parquet`
- `data/output/magi_v2/baltasar_v2_pure_directional/test.parquet`
- `data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_model.joblib`
- `data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_metrics.json`
- `data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_summary.md`
- `data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_feature_importance.csv`

## Features usadas

Permitidas:

- `session`
- `hour`
- `weekday`
- `spread_pips`
- `atr`
- `daily_range_position`
- `regime`

Excluidas:

- senales de Melchor
- senales de Gaspar
- `baltasar_signal` y `baltasar_confidence`
- `mage_agreement`
- outcomes first-touch
- `buy_R` / `sell_R`
- target
- cualquier columna futura

## Modelos probados

1. `RandomForestClassifier`
   - Entrenado sobre train completo.
   - `class_weight=balanced_subsample`.

2. `HistGradientBoostingClassifier`
   - Entrenado como baseline ligero sobre muestra estratificada de 12,000 filas.
   - Usa sample weights balanceados.
   - Se redujo a una prueba ligera porque HGB full single-thread no era razonable en este entorno.

Modelo seleccionado por validation:

- `HistGradientBoostingClassifier`

Regla de seleccion:

- mayor avg R en validation por threshold
- luego PF
- luego trade precision

## Splits

| Split | Filas | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | ---: | ---: | ---: | ---: |
| Train | 237,132 | 139,635 | 48,210 | 49,287 |
| Validation | 59,378 | 42,450 | 8,148 | 8,780 |
| Test | 74,991 | 43,774 | 15,606 | 15,611 |

## Validation thresholds

### RandomForestClassifier

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 40,896 | 0.688740 | 0.192659 | -0.002937 | -120.07 | 0.994422 | 1,274.30 |
| 0.40 | 4,793 | 0.080720 | 0.201335 | -0.196109 | -939.95 | 0.707361 | 1,042.82 |
| 0.50 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |
| 0.60 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |
| 0.70 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |

### HistGradientBoostingClassifier

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 42,192 | 0.710566 | 0.186576 | 0.001906 | 80.36 | 1.003689 | 1,656.98 |
| 0.40 | 22,089 | 0.372006 | 0.212730 | -0.032021 | -707.21 | 0.944210 | 1,842.91 |
| 0.50 | 1,189 | 0.020024 | 0.291842 | 0.159428 | 189.56 | 1.296540 | 128.36 |
| 0.60 | 60 | 0.001010 | 0.600000 | 0.805833 | 48.35 | 3.044397 | 23.65 |
| 0.70 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |

## Test thresholds

### RandomForestClassifier

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 52,017 | 0.693643 | 0.246439 | -0.014674 | -762.60 | 0.975199 | 2,142.65 |
| 0.40 | 6,754 | 0.090064 | 0.308114 | 0.005592 | 37.76 | 1.008745 | 357.31 |
| 0.50 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |
| 0.60 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |
| 0.70 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |

### HistGradientBoostingClassifier

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 53,776 | 0.717099 | 0.248568 | 0.003530 | 189.72 | 1.006042 | 1,007.86 |
| 0.40 | 32,179 | 0.429105 | 0.282234 | 0.022056 | 709.48 | 1.036459 | 609.58 |
| 0.50 | 3,609 | 0.048126 | 0.304794 | 0.056017 | 202.11 | 1.093229 | 205.31 |
| 0.60 | 169 | 0.002254 | 0.189349 | -0.424497 | -71.74 | 0.472500 | 83.74 |
| 0.70 | 0 | 0.000000 | n/a | n/a | n/a | n/a | 0 |

## Comparacion contra Baltasar v1

| Split | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation | 26,701 | 0.449678 | 0.186173 | 0.006375 | 170.08 | 1.012434 | 878.24 |
| Test | 48,457 | 0.646171 | 0.263264 | 0.083469 | 4,037.15 | 1.152036 | 766.96 |

## Comparacion contra Baltasar v2 baseline anterior

| Split | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation argmax | 32,611 | 0.549210 | 0.209653 | -0.023658 | -771.48 | 0.957802 | 1,557.86 |
| Test argmax | 43,905 | 0.585470 | 0.262271 | 0.003646 | 159.98 | 1.006110 | 1,278.18 |

## Feature importance

Importancia por permutation F1 macro del modelo seleccionado:

| Feature | Importance |
| --- | ---: |
| hour | 0.093402 |
| weekday | 0.016436 |
| spread_pips | 0.002984 |
| session | 0.001473 |
| regime | -0.000811 |
| daily_range_position | -0.005561 |
| atr | -0.009638 |

El modelo depende principalmente de `hour`. Esto sugiere que con las features actuales aprende timing parcial, pero no una lectura direccional tecnica profunda.

## Diagnostico

La variante pura mejora frente al baseline anterior en algunos thresholds, especialmente HGB:

- Validation HGB threshold 0.50: avg R positivo y PF 1.296540.
- Validation HGB threshold 0.60: PF alto, pero solo 60 trades.
- Test HGB threshold 0.40 y 0.50: avg R positivo y PF > 1.

Pero no supera a Baltasar v1 de forma estable:

- En test, Baltasar v1 mantiene mejor avg R (`0.083469`) y PF (`1.152036`) que HGB threshold 0.50 (`0.056017`, PF `1.093229`).
- HGB threshold 0.60 se rompe en test.
- RF no muestra edge suficiente.

## Conclusion

Baltasar v2 pure_directional aprende algo de timing/direccion debil, pero no alcanza todavia a Baltasar v1 en metricas operativas fuera de muestra.

El resultado apunta a que hacen falta features tecnicas mas ricas desde Bot A, no solo `session/hour/weekday/spread/ATR/daily_range_position/regime`.

## Siguiente recomendacion

Construir un dataset direccional Baltasar v2 con features tecnicas MTF propias:

- estructura H1/H4/D1
- momentum
- distancias a soporte/resistencia
- pendiente de EMAs
- RSI y cambios de RSI
- rango reciente y breakout/reversion flags
- alineacion MTF cruda

Luego repetir entrenamiento con el mismo target RR2 first-touch y comparar contra Baltasar v1 en validation/test y walk-forward.
