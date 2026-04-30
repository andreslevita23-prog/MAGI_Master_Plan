# Baltasar v2 Rich Feature Dataset

## Objetivo

Construir un dataset tabular enriquecido para entrenar Baltasar v2 con features tecnicas reales de Bot A y target RR 1:2 first-touch M5.

No se entrenaron modelos, no se modificaron magos y no se cambiaron datasets originales.

## Script

- `scripts/magi_v2/build_baltasar_v2_rich_feature_dataset.py`

Validacion:

- `py_compile` OK.

## Inputs

- `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`
- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet`

## Outputs

- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.csv`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.json`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.md`

## Union

La union se hizo por:

- `symbol`
- `anchor_bar_timestamp`

Resultado:

- Filas totales: `371,501`
- Match exitoso: `371,082`
- Match pct: `99.8872%`
- Sin match: `419`

Distribucion de metodo:

| Metodo | Filas |
| --- | ---: |
| symbol_anchor_bar_timestamp | 371,082 |
| missing_raw_features | 419 |

El fallback `timestamp floor_to_m5` queda implementado para casos donde falte `anchor_bar_timestamp`, pero en esta corrida no fue necesario porque los labels ya conservaban `anchor_bar_timestamp`.

## Target

Target:

- `tradeable_direction_rr2_first_touch`

Distribucion:

| Clase | Filas |
| --- | ---: |
| DO_NOTHING | 225,859 |
| ENTER_SELL | 73,678 |
| ENTER_BUY | 71,964 |

## Columnas

- Columnas totales: `87`
- Feature columns explicitas: `71`
- Diagnostic columns: `5`

El dataset final conserva solo:

- columnas de identidad/trazabilidad
- target
- feature columns permitidas
- diagnostic columns permitidas

Se removieron del contrato de salida las senales de otros magos y outcomes no pedidos para reducir riesgo de leakage accidental.

## Feature columns

### Timing/contexto

- `session`
- `hour`
- `weekday`
- `spread_pips`
- `atr`
- `daily_range_position`
- `regime`

### OHLC y derivadas M5

- `anchor_open`
- `anchor_high`
- `anchor_low`
- `anchor_close`
- `candle_body_pct`
- `upper_wick_pct`
- `lower_wick_pct`
- `returns_1`
- `returns_3`
- `returns_6`
- `volatility_12`
- `recent_range`

### Indicadores M5

- `ema_20`
- `ema_50`
- `ema_200`
- `ema_20_50_distance`
- `ema_50_200_distance`
- `close_to_ema20`
- `close_to_ema50`
- `close_to_ema200`
- `ema_20_slope`
- `ema_50_slope`
- `rsi_14`
- `momentum`

### Estructura M5

- `market_structure`
- `structure_direction`
- `support_distance_pips`
- `resistance_distance_pips`

### MTF

Para `M15`, `H1`, `H4`, `D1`:

- `ema_20`
- `ema_50`
- `ema_200`
- `rsi_14`
- `market_structure`
- `structure_direction`
- `recent_range`
- `candle_pattern`

Ejemplos:

- `h1_ema_20`
- `h4_rsi_14`
- `d1_market_structure`
- `m15_candle_pattern`

### Alineacion

- `mtf_alignment_status`
- `htf_directional_alignment`
- `htf_h4_structure`
- `htf_d1_structure`

## Diagnostic columns

Estas columnas se conservan para evaluacion, pero no deben usarse como features:

- `buy_R`
- `sell_R`
- `buy_first_touch`
- `sell_first_touch`
- `same_bar_ambiguous_flag`

## Leakage guard

`feature_columns` no incluye:

- `buy_outcome`
- `sell_outcome`
- `buy_R`
- `sell_R`
- `buy_first_touch`
- `sell_first_touch`
- `buy_bars_to_exit`
- `sell_bars_to_exit`
- `same_bar_ambiguous_flag`
- target
- future outcomes
- senales de Melchor/Gaspar/Baltasar v1
- `mage_agreement`

El summary JSON registra:

- `forbidden_feature_check.passed = true`
- `forbidden_columns_in_features = []`

## Principales nulos

| Columna | Nulos | Motivo probable |
| --- | ---: | --- |
| `candle_body_pct` | 487 | 419 rows sin match + velas con rango cero |
| `upper_wick_pct` | 487 | 419 rows sin match + velas con rango cero |
| `lower_wick_pct` | 487 | 419 rows sin match + velas con rango cero |
| `buy_R` | 455 | 419 missing raw/features + 36 sin horizonte suficiente |
| `sell_R` | 455 | 419 missing raw/features + 36 sin horizonte suficiente |
| `returns_6` | 425 | primeras filas por simbolo + missing raw/features |
| `returns_3` | 422 | primeras filas por simbolo + missing raw/features |
| `volatility_12` | 422 | requiere min_periods rolling |
| `returns_1` | 420 | primera fila por simbolo + missing raw/features |
| `ema_20_slope` | 420 | primera fila por simbolo + missing raw/features |
| `ema_50_slope` | 420 | primera fila por simbolo + missing raw/features |

## Estado

El dataset esta listo para entrenar un `Baltasar v2 rich_features` experimental.

Recomendacion de entrenamiento:

1. Usar exclusivamente `feature_columns` desde el summary JSON.
2. Usar `diagnostic_columns` solo para metricas operativas.
3. Mantener split temporal 2020-2023 / 2024 / 2025-2026.
4. Comparar contra Baltasar v1, Baltasar v2 baseline y Baltasar v2 pure_directional.
5. Evaluar thresholds por avg R, PF, drawdown, trade precision y coverage; no solo accuracy.
