# Baltasar v2 Baseline

## Objetivo

Entrenar un primer baseline experimental para Baltasar v2 usando el target operativo:

- `tradeable_direction_rr2_first_touch`

Clases:

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

Este modelo no reemplaza Baltasar v1. Es una prueba inicial para medir si las features actuales permiten aprender direccion operable con RR 1:2 y first-touch M5.

## Input

- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet`

## Script

- `scripts/magi_v2/train_baltasar_v2_baseline.py`

## Outputs

- `data/output/magi_v2/baltasar_v2_baseline/train.parquet`
- `data/output/magi_v2/baltasar_v2_baseline/validation.parquet`
- `data/output/magi_v2/baltasar_v2_baseline/test.parquet`
- `data/output/magi_v2/baltasar_v2_baseline/baltasar_v2_baseline_model.joblib`
- `data/output/magi_v2/baltasar_v2_baseline/baltasar_v2_baseline_metrics.json`
- `data/output/magi_v2/baltasar_v2_baseline/baltasar_v2_baseline_summary.md`
- `data/output/magi_v2/baltasar_v2_baseline/baltasar_v2_feature_importance.csv`

## Modelo

- Tipo: `RandomForestClassifier`
- `n_estimators`: 180
- `max_depth`: 12
- `min_samples_leaf`: 90
- `class_weight`: `balanced_subsample`
- `n_jobs`: 1

Se usa pipeline completo con imputacion, OneHotEncoder para categoricas y RandomForest.

## Features usadas

Permitidas:

- `session`
- `hour`
- `weekday`
- `spread_pips`
- `atr`
- `daily_range_position`
- `regime`
- `melchor_signal`
- `melchor_confidence`
- `melchor_risk_flags`
- `baltasar_signal`
- `baltasar_confidence`
- `gaspar_signal`
- `gaspar_confidence`
- `mage_agreement`
- `baltasar_gaspar_alignment`

Prohibidas y excluidas:

- `buy_outcome`
- `sell_outcome`
- `buy_R`
- `sell_R`
- `buy_first_touch`
- `sell_first_touch`
- `buy_bars_to_exit`
- `sell_bars_to_exit`
- `tradeable_direction_rr2_first_touch`
- `same_bar_ambiguous_flag`
- cualquier outcome futuro

`buy_R` y `sell_R` se usan solo para evaluacion operativa.

## Splits temporales

| Split | Filas | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | ---: | ---: | ---: | ---: |
| Train 2020-2023 | 237,132 | 139,635 | 48,210 | 49,287 |
| Validation 2024 | 59,378 | 42,450 | 8,148 | 8,780 |
| Test 2025-2026 | 74,991 | 43,774 | 15,606 | 15,611 |

## Metricas argmax

| Split | Accuracy | Macro F1 | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation | 0.509818 | 0.402251 | 32,611 | 0.549210 | 0.209653 | -0.023658 | -771.48 | 0.957802 | 1,557.86 |
| Test | 0.450721 | 0.394794 | 43,905 | 0.585470 | 0.262271 | 0.003646 | 159.98 | 1.006110 | 1,278.18 |

## Threshold analysis

Con thresholds 0.50, 0.60, 0.70 y 0.80 no se ejecutan trades en validation ni test.

Interpretacion: el modelo asigna probabilidades poco concentradas a `ENTER_BUY` y `ENTER_SELL`. Aunque por argmax a veces elige operar, la probabilidad de la clase operable no supera 0.50. Para una politica conservadora, este baseline no produce senales ejecutables.

## Comparacion contra Baltasar v1 signal

Se comparo contra la regla:

- `baltasar_signal=BUY` -> `ENTER_BUY`
- `baltasar_signal=SELL` -> `ENTER_SELL`
- otro valor -> `DO_NOTHING`

| Split | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation | 26,701 | 0.449678 | 0.186173 | 0.006375 | 170.08 | 1.012434 | 878.24 |
| Test | 48,457 | 0.646171 | 0.263264 | 0.083469 | 4,037.15 | 1.152036 | 766.96 |

En test, Baltasar v1 supera claramente al baseline ML en EV proxy, PF y drawdown. En validation tambien es mas estable operativamente.

## Feature importance principal

Top features:

1. `numeric__hour`
2. `categorical__melchor_signal_BLOCK`
3. `categorical__melchor_risk_flags_LOW`
4. `categorical__mage_agreement_BLOCKED_BY_MELCHOR`
5. `categorical__melchor_risk_flags_HIGH`
6. `categorical__melchor_signal_APPROVE`
7. `categorical__baltasar_signal_NEUTRAL`
8. `categorical__mage_agreement_ACTIONABLE_CONSENSUS`
9. `categorical__session_asia`
10. `categorical__session_overlap`

El modelo parece estar aprendiendo filtros de contexto/riesgo mas que direccion operable robusta.

## Diagnostico

Baltasar v2 baseline no aprendio aun una politica util superior a Baltasar v1.

Senales:

- Threshold 0.50+ colapsa a `DO_NOTHING`.
- Argmax opera demasiado sin suficiente confianza.
- Validation tiene EV proxy negativo.
- Test queda casi plano y por debajo de Baltasar v1.
- La importancia de features muestra dependencia fuerte de filtros de Melchor/contexto, no de una lectura direccional fuerte.

## Limitaciones

- Es un baseline sin tuning.
- RandomForest puede estar mal calibrado para usar thresholds de probabilidad.
- El target RR2 first-touch es mas exigente que el target anterior.
- M5 no resuelve same-bar internamente.
- No se usan features tecnicas mas ricas de Bot A/MTF crudas, solo el dataset tabular CEO.

## Recomendacion

No usar este baseline como Baltasar v2.

Siguiente paso recomendado:

1. Entrenar un baseline adicional sin `melchor_signal`, `mage_agreement` y `gaspar_signal` para obligar a Baltasar a aprender direccion, no filtros de otros magos.
2. Probar `HistGradientBoostingClassifier` con calibracion de probabilidades.
3. Evaluar thresholds mas bajos solo como diagnostico, no como politica final.
4. Construir features direccionales propias de Baltasar desde Bot A MTF si estan disponibles.
5. Mantener Baltasar v1 como referencia hasta que v2 supere EV/PF/drawdown en validation y test.
