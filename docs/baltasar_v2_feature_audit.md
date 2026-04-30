# Baltasar v2 Feature Audit

## Objetivo

Auditar `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl` para identificar features tecnicas reales disponibles para entrenar Baltasar v2 con mas senal que la variante `pure_directional`.

No se entrenaron modelos y no se modificaron datasets ni magos.

## Script

- `scripts/magi_v2/audit_baltasar_v2_features.py`

## Outputs

- `data/output/magi_v2/baltasar_v2_feature_audit/baltasar_v2_feature_audit_summary.md`
- `data/output/magi_v2/baltasar_v2_feature_audit/baltasar_v2_feature_audit.json`
- `data/output/magi_v2/baltasar_v2_feature_audit/available_columns.csv`
- `data/output/magi_v2/baltasar_v2_feature_audit/candidate_features.csv`
- `data/output/magi_v2/baltasar_v2_feature_audit/missing_recommended_features.csv`

## Resultado ejecutivo

El dataset limpio de Bot A contiene `371,513` snapshots M5 entre `2020-01-15T00:00:00Z` y `2026-04-14T23:55:00Z`.

La auditoria detecto `176` rutas/columnas reales, incluyendo rutas anidadas. Esto confirma que si hay base suficiente para construir un dataset `rich_features` para Baltasar v2.

La razon por la que `pure_directional` quedo corto es que uso solo:

- session
- hour
- weekday
- spread_pips
- atr
- daily_range_position
- regime

Pero Bot A ya trae mas senal tecnica:

- OHLC M5
- EMA 20/50/200 M5
- RSI M5
- momentum M5
- market structure M5
- structure direction M5
- recent range M5
- support/resistance levels
- EMA/RSI/structure/recent_range por M15/H1/H4/D1
- MTF alignment
- higher timeframe confluence

## Columnas top-level relevantes

Campos tecnicos directos:

- `anchor_open`
- `anchor_high`
- `anchor_low`
- `anchor_close`
- `current_price`
- `ema_20`
- `ema_50`
- `ema_200`
- `rsi_14`
- `momentum`
- `market_structure`
- `structure_direction`
- `recent_range`
- `support_levels`
- `resistance_levels`
- `spread_pips`
- `mtf_alignment_status`
- `mtf_alignment_warnings`
- `mtf_data_source_status`
- `active_session`
- `anchor_bar_timestamp`

## Features MTF disponibles

Dentro de `features` existen registros por timeframe:

- `M15`
- `H1`
- `H4`
- `D1`

Cada timeframe incluye:

- `ema_20`
- `ema_50`
- `ema_200`
- `rsi_14`
- `market_structure`
- `structure_direction`
- `recent_range`
- `candle_pattern`
- `age_minutes`
- `bar_timestamp`
- `bar_close_timestamp`
- `data_source_status`
- `alignment_status`

Esto permite construir una version `rich_features` sin pedir todavia un nuevo export de Bot A.

## Features listas para usar

| Grupo | Estado | Fuente |
| --- | --- | --- |
| OHLC M5 | listo | `anchor_open/high/low/close` |
| EMA M5 | listo | `ema_20`, `ema_50`, `ema_200` |
| RSI M5 | listo | `rsi_14` |
| Momentum M5 | listo | `momentum` |
| Estructura M5 | listo | `market_structure`, `structure_direction` |
| Recent range M5 | listo | `recent_range` |
| Spread | listo | `spread_pips` |
| Soporte/resistencia | listo | `support_levels`, `resistance_levels` |
| EMA MTF | listo | `features.M15/H1/H4/D1.ema_*` |
| RSI MTF | listo | `features.M15/H1/H4/D1.rsi_14` |
| Estructura MTF | listo | `features.M15/H1/H4/D1.market_structure`, `structure_direction` |
| Recent range MTF | listo | `features.M15/H1/H4/D1.recent_range` |
| Alineacion MTF | listo | `mtf_alignment_status`, `gaspar_context.higher_timeframe_confluence.directional_alignment` |

## Features derivables directamente

Se pueden derivar sin modificar Bot A:

- `candle_body_pct`
- `upper_wick_pct`
- `lower_wick_pct`
- `ema_distance`
- `ema_slope`
- retornos M5 lagged
- `atr_m5`
- distancia a high/low reciente
- distancia a soporte/resistencia en pips
- momentum H1 proxy desde EMA/RSI/structure H1

Estas derivaciones deben hacerse con ventanas pasadas solamente para evitar leakage.

## Features que faltan o conviene exportar desde Bot A

| Feature | Estado | Motivo |
| --- | --- | --- |
| `atr_h1` | requiere export | No hay ATR H1 directo ni OHLC H1 completo; `features.H1.recent_range` existe pero no es ATR. |
| fractals/swing markers | requiere export | No hay marcadores explicitos de fractales, swing high/low o pivots. |
| bid/ask OHLC | requiere export | No existe bid/ask historico separado para ejecucion institucional. |
| M1 intrabar | requiere export | M5 no resuelve same-bar dentro de una vela. |

## Comparacion contra features recomendadas

De la lista recomendada para Baltasar v2:

- Listas: `trend_h1`, `trend_h4`, `trend_d1`, `ema_fast_m5`, `ema_slow_m5`, `rsi_m5`, `rsi_h1`, `momentum_m5`, `support_distance_pips`, `resistance_distance_pips`, `structure_h1`, `structure_h4`, `mtf_trend_alignment`.
- Derivables: `ema_distance`, `ema_slope`, `atr_m5`, `momentum_h1`, `candle_body_pct`, `upper_wick_pct`, `lower_wick_pct`, `distance_to_recent_high`, `distance_to_recent_low`.
- Faltantes reales de Bot A: `atr_h1` directo y fractals/swing markers.

## Se puede entrenar Baltasar v2 rich_features?

Si. La recomendacion es construir primero un dataset tabular tecnico desde `cleaned_dataset.jsonl` y unirlo con:

- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet`

Llave recomendada:

- `symbol`
- `anchor_bar_timestamp`

Fallback:

- `timestamp` con `floor_to_m5`, tal como se hizo en el dataset RR2 first-touch.

## Recomendacion exacta del siguiente paso

Crear:

- `scripts/magi_v2/build_baltasar_v2_rich_feature_dataset.py`

Output sugerido:

- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.json`
- `data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.md`

Ese script debe:

1. Expandir features MTF por timeframe.
2. Derivar body/wicks, EMA distances, EMA slopes, returns, ATR M5, support/resistance distances y rolling high/low distances.
3. Unir con el target `tradeable_direction_rr2_first_touch`.
4. Marcar columnas prohibidas para entrenamiento.
5. Generar split temporal compatible con los experimentos anteriores.

Despues de eso, entrenar `Baltasar v2 rich_features` y compararlo contra:

- Baltasar v1
- Baltasar v2 pure_directional
- Baltasar v2 baseline con votos de magos
