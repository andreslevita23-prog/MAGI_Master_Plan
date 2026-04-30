# Baltasar v2 Rich Features Model

## Objetivo

Entrenar un baseline experimental de Baltasar v2 usando el dataset enriquecido con features tecnicas reales M5+MTF y target RR 1:2 first-touch.

Este experimento no reemplaza Baltasar v1 y no modifica magos existentes.

## Inputs

- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.json`

## Script

- `scripts/magi_v2/train_baltasar_v2_rich_features.py`

## Outputs

- `data/output/magi_v2/baltasar_v2_rich_features_model/train.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features_model/validation.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features_model/test.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_model.joblib`
- `data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_metrics.json`
- `data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_summary.md`
- `data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_feature_importance.csv`

## Modelo

- `HistGradientBoostingClassifier`
- Features: `71`
- Target: `tradeable_direction_rr2_first_touch`
- Categorical encoding: `OrdinalEncoder`
- Sample weights: `class_weight=balanced`

RandomForest no se entreno en esta corrida. Se priorizo HGB por costo/beneficio y porque los baselines RF anteriores fueron mas lentos y mas debiles.

## Leakage check

El modelo usa exclusivamente `feature_columns` desde:

- `baltasar_v2_rich_features_summary.json`

No usa como features:

- `buy_R`
- `sell_R`
- `buy_first_touch`
- `sell_first_touch`
- `same_bar_ambiguous_flag`
- target
- outcomes futuros
- columnas diagnosticas

Resultado:

- `leakage_check.passed = true`
- `forbidden_features_in_model = []`

## Splits

| Split | Filas | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | ---: | ---: | ---: | ---: |
| Train | 237,132 | 139,635 | 48,210 | 49,287 |
| Validation | 59,378 | 42,450 | 8,148 | 8,780 |
| Test | 74,991 | 43,774 | 15,606 | 15,611 |

## Validation thresholds

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 32,149 | 0.541429 | 0.216274 | 0.004945 | 158.97 | 1.008863 | 901.74 |
| 0.40 | 20,564 | 0.346324 | 0.239739 | 0.014781 | 303.96 | 1.025651 | 566.89 |
| 0.50 | 3,660 | 0.061639 | 0.285792 | 0.105413 | 385.81 | 1.187423 | 193.23 |
| 0.60 | 237 | 0.003991 | 0.417722 | 0.440844 | 104.48 | 1.957215 | 31.00 |
| 0.70 | 3 | 0.000051 | 1.000000 | 2.000000 | 6.00 | n/a | 0.00 |

## Test thresholds

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 50,456 | 0.672827 | 0.270572 | 0.037834 | 1,908.35 | 1.064760 | 616.60 |
| 0.40 | 35,242 | 0.469950 | 0.297855 | 0.057629 | 2,030.95 | 1.096255 | 513.93 |
| 0.50 | 6,765 | 0.090211 | 0.320769 | 0.082132 | 555.62 | 1.136375 | 292.51 |
| 0.60 | 433 | 0.005774 | 0.316397 | 0.063857 | 27.65 | 1.109064 | 54.02 |
| 0.70 | 12 | 0.000160 | 1.000000 | 2.000000 | 24.00 | n/a | 0.00 |

## Comparacion contra Baltasar v1

La comparacion contra Baltasar v1 se carga desde el experimento `baltasar_v2_pure_directional`, porque el dataset rich final no conserva `baltasar_signal` para evitar leakage accidental.

| Split | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation | 26,701 | 0.449678 | 0.186173 | 0.006375 | 170.08 | 1.012434 | 878.24 |
| Test | 48,457 | 0.646171 | 0.263264 | 0.083469 | 4,037.15 | 1.152036 | 766.96 |

## Comparacion contra pure_directional

| Split | Threshold | Trades | Avg R | PF | Total R |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 0.40 | 22,089 | -0.032021 | 0.944210 | -707.21 |
| Validation | 0.50 | 1,189 | 0.159428 | 1.296540 | 189.56 |
| Test | 0.40 | 32,179 | 0.022056 | 1.036459 | 709.48 |
| Test | 0.50 | 3,609 | 0.056017 | 1.093229 | 202.11 |

Rich features mejora claramente a pure_directional en test:

- Threshold 0.40: avg R sube de `0.022056` a `0.057629`.
- Threshold 0.50: avg R sube de `0.056017` a `0.082132`.
- Trade precision tambien sube en 0.40 y 0.50.

## Feature importance

Top por permutation F1 macro:

1. `hour`
2. `weekday`
3. `session`
4. `volatility_12`
5. `d1_market_structure`
6. `h1_ema_20`
7. `htf_h4_structure`
8. `ema_20_50_distance`
9. `ema_20`
10. `returns_3`
11. `returns_6`
12. `close_to_ema20`
13. `m15_recent_range`
14. `h4_market_structure`
15. `h4_ema_20`

La senal sigue dominada por timing, pero ahora aparecen features tecnicas reales M5/MTF con contribucion positiva.

## Diagnostico

Baltasar v2 rich mejora al modelo `pure_directional`, pero todavia no supera globalmente a Baltasar v1.

Lectura honesta:

- En validation, rich threshold 0.50 supera a Baltasar v1 en avg R, PF, trade precision y drawdown, con menor coverage.
- En test, rich threshold 0.50 casi iguala el avg R de Baltasar v1 (`0.082132` vs `0.083469`), pero queda por debajo en PF y total R.
- Rich threshold 0.40 ofrece menor drawdown que Baltasar v1, pero tambien menor avg R/PF/total R.
- Threshold 0.70 tiene muestra demasiado pequena para tomarse como politica real.

## Conclusion

Baltasar v2 rich no esta listo para reemplazar Baltasar v1, pero es el primer modelo v2 que se acerca seriamente usando features tecnicas reales y mejora con claridad a `pure_directional`.

## Siguiente recomendacion

1. Hacer walk-forward por ano/quarter/month para rich thresholds 0.40 y 0.50.
2. Agregar comparacion operativa con drawdown mensual y meses malos.
3. Probar calibracion de probabilidades antes de fijar threshold.
4. Entrenar una variante HGB sin `hour/session` para medir cuanto edge viene realmente de tecnica vs timing.
5. Si se mantiene estable, usar rich threshold 0.50 como candidato para Baltasar v2 experimental, no productivo.
