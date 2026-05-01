# Baltasar v2 Rich Feature Dataset

## Summary

- Rows: `371501`
- Columns: `87`
- Feature columns: `71`
- Match pct: `99.8872%`
- Temporal range: `2020-01-15T00:00:00+00:00` to `2026-04-14T22:55:00+00:00`

## Target Distribution

| label | rows |
| --- | --- |
| DO_NOTHING | 225859 |
| ENTER_SELL | 73678 |
| ENTER_BUY | 71964 |

## Match Method Distribution

| method | rows |
| --- | --- |
| symbol_anchor_bar_timestamp | 371082 |
| missing_raw_features | 419 |

## Feature Columns

session, hour, weekday, spread_pips, atr, daily_range_position, regime, anchor_open, anchor_high, anchor_low, anchor_close, candle_body_pct, upper_wick_pct, lower_wick_pct, returns_1, returns_3, returns_6, volatility_12, recent_range, ema_20, ema_50, ema_200, ema_20_50_distance, ema_50_200_distance, close_to_ema20, close_to_ema50, close_to_ema200, ema_20_slope, ema_50_slope, rsi_14, momentum, market_structure, structure_direction, support_distance_pips, resistance_distance_pips, mtf_alignment_status, htf_directional_alignment, htf_h4_structure, htf_d1_structure, m15_ema_20, m15_ema_50, m15_ema_200, m15_rsi_14, m15_market_structure, m15_structure_direction, m15_recent_range, m15_candle_pattern, h1_ema_20, h1_ema_50, h1_ema_200, h1_rsi_14, h1_market_structure, h1_structure_direction, h1_recent_range, h1_candle_pattern, h4_ema_20, h4_ema_50, h4_ema_200, h4_rsi_14, h4_market_structure, h4_structure_direction, h4_recent_range, h4_candle_pattern, d1_ema_20, d1_ema_50, d1_ema_200, d1_rsi_14, d1_market_structure, d1_structure_direction, d1_recent_range, d1_candle_pattern

## Diagnostic Columns

buy_R, sell_R, buy_first_touch, sell_first_touch, same_bar_ambiguous_flag

## Top Null Counts

| column | nulls |
| --- | --- |
| candle_body_pct | 487 |
| lower_wick_pct | 487 |
| upper_wick_pct | 487 |
| buy_R | 455 |
| sell_R | 455 |
| returns_6 | 425 |
| returns_3 | 422 |
| volatility_12 | 422 |
| returns_1 | 420 |
| ema_50_slope | 420 |
| ema_20_slope | 420 |
| ema_50 | 419 |
| ema_20 | 419 |
| close_to_ema20 | 419 |
| ema_50_200_distance | 419 |
| anchor_close | 419 |
| ema_20_50_distance | 419 |
| snapshot_id_raw | 419 |
| snapshot_id | 419 |
| anchor_high | 419 |

## Technical Decisions

- Labels are left-joined to Bot A clean features by symbol + anchor_bar_timestamp.
- If anchor_bar_timestamp is missing in labels, timestamp floor_to_m5 is used as fallback.
- M5 candle/EMA/return/volatility derived features use current and past rows only.
- buy_R/sell_R/first_touch diagnostics are retained for evaluation but excluded from feature_columns.
- future outcomes and label columns are not included in feature_columns.
