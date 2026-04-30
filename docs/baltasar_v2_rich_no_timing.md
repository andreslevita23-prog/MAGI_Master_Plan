# Baltasar v2 Rich No Timing

## Objetivo

Entrenar una variante `Baltasar v2 rich_no_timing` usando las mismas features tecnicas del dataset rich, pero eliminando variables de timing directo para comprobar si el edge sobrevive sin horario/sesion.

Este experimento no reemplaza Baltasar v1 y no modifica magos existentes.

## Inputs

- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.json`

## Script

- `scripts/magi_v2/train_baltasar_v2_rich_no_timing.py`

## Outputs

- `data/output/magi_v2/baltasar_v2_rich_no_timing/train.parquet`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/validation.parquet`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/test.parquet`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_model.joblib`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_metrics.json`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_summary.md`
- `data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_feature_importance.csv`

## Features eliminadas

- `session`
- `hour`
- `weekday`
- `regime`

`regime` se elimino porque incluye la sesion como prefijo y por tanto codifica timing de forma indirecta.

## Features usadas

Features restantes: `67`.

Incluyen:

- spread
- ATR
- daily range position
- OHLC M5
- candle body/wicks
- returns
- volatility
- EMA/RSI/momentum
- market structure
- support/resistance distances
- MTF M15/H1/H4/D1
- MTF alignment / higher timeframe confluence

No se usaron diagnostics, target, first-touch outcomes ni future outcomes como features.

## Modelo

- `HistGradientBoostingClassifier`
- sample weights balanceados
- `OrdinalEncoder` para categoricas

RandomForest se omitio para mantener la ablacion enfocada y razonable en tiempo.

## Splits

| Split | Filas | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | ---: | ---: | ---: | ---: |
| Train | 237,132 | 139,635 | 48,210 | 49,287 |
| Validation | 59,378 | 42,450 | 8,148 | 8,780 |
| Test | 74,991 | 43,774 | 15,606 | 15,611 |

## Validation thresholds

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 34,151 | 0.575146 | 0.185588 | -0.004375 | -149.42 | 0.991535 | 1,290.46 |
| 0.40 | 13,300 | 0.223989 | 0.219098 | 0.001479 | 19.67 | 1.002672 | 471.00 |
| 0.50 | 1,554 | 0.026171 | 0.238095 | 0.002220 | 3.45 | 1.003881 | 111.79 |
| 0.60 | 155 | 0.002610 | 0.361290 | 0.270645 | 41.95 | 1.508115 | 38.50 |
| 0.70 | 10 | 0.000168 | 0.500000 | 1.509000 | 15.09 | n/a | 0.00 |

## Test thresholds

| Threshold | Trades | Coverage | Trade precision | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30 | 60,583 | 0.807870 | 0.232045 | 0.008713 | 527.52 | 1.015471 | 1,216.54 |
| 0.40 | 27,870 | 0.371645 | 0.265339 | 0.006342 | 176.71 | 1.010628 | 726.37 |
| 0.50 | 3,358 | 0.044779 | 0.300476 | 0.065870 | 221.19 | 1.112127 | 222.50 |
| 0.60 | 225 | 0.003000 | 0.337778 | 0.042400 | 9.54 | 1.065612 | 68.46 |
| 0.70 | 1 | 0.000013 | 0.000000 | -1.000000 | -1.00 | 0.000000 | 1.00 |

## Comparacion directa contra rich con timing

| Split | Threshold | No timing avg R | No timing PF | With timing avg R | With timing PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 0.40 | 0.001479 | 1.002672 | 0.014781 | 1.025651 |
| Validation | 0.50 | 0.002220 | 1.003881 | 0.105413 | 1.187423 |
| Test | 0.40 | 0.006342 | 1.010628 | 0.057629 | 1.096255 |
| Test | 0.50 | 0.065870 | 1.112127 | 0.082132 | 1.136375 |

Quitar timing reduce mucho el edge, especialmente en validation y en test threshold 0.40. En test threshold 0.50 sobrevive algo de edge tecnico, pero menor que rich con timing.

## Comparacion contra Baltasar v1

| Split | Trades | Coverage | Avg R | PF | Total R |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation | 26,701 | 0.449678 | 0.006375 | 1.012434 | 170.08 |
| Test | 48,457 | 0.646171 | 0.083469 | 1.152036 | 4,037.15 |

El modelo no timing no supera a Baltasar v1:

- Test 0.50 queda en avg R `0.065870` vs Baltasar v1 `0.083469`.
- PF test 0.50 queda en `1.112127` vs Baltasar v1 `1.152036`.
- Total R es mucho menor por cobertura reducida.

## Feature importance

Top features:

1. `volatility_12`
2. `m15_recent_range`
3. `h4_rsi_14`
4. `ema_50_200_distance`
5. `m15_ema_20`
6. `d1_recent_range`
7. `support_distance_pips`
8. `recent_range`
9. `h4_ema_200`
10. `returns_1`

Esta lista confirma que, sin timing, el modelo usa estructura tecnica real: volatilidad, rangos, RSI H4, EMAs MTF y distancias a niveles.

## Conclusion

El edge no desaparece completamente sin timing, pero cae de forma importante.

Lectura:

- Si hay senal tecnica real.
- La senal tecnica sola es mas debil que rich con timing.
- El rendimiento de Baltasar v2 rich depende bastante del horario/sesion.
- El modelo no timing no supera a Baltasar v1.

## Siguiente recomendacion

No descartar las features tecnicas. La mejor lectura es combinada:

1. Mantener timing en el candidato rich, pero controlar sobreajuste con walk-forward.
2. Entrenar y evaluar por segmentos horarios para ver donde timing aporta sin romper generalizacion.
3. Crear variante `rich_no_session_but_hour_allowed` o `rich_technical_plus_session_bucket` para medir dependencia fina.
4. Agregar M1/first-touch mas preciso y features de swing/fractals para reforzar edge tecnico.
5. No reemplazar Baltasar v1 hasta que rich supere avg R/PF/drawdown en test y walk-forward.
