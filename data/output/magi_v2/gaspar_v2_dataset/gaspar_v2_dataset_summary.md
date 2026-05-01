# Gaspar v2 context dataset

## Purpose

Builds the first Gaspar v2 dataset to learn whether market context favors or hurts trades selected by `Baltasar v2 rich_policy_medium`.

Gaspar v2 is not a directional model. It should learn context quality and later help CEO-MAGI block, caution, or reinforce Baltasar trades.

## Inputs

- `simulated_trades_040.csv`: `data\output\magi_v2\baltasar_v2_rich_features_model\policy_medium_r_simulation\simulated_trades_040.csv`
- `simulated_trades_050.csv`: `data\output\magi_v2\baltasar_v2_rich_features_model\policy_medium_r_simulation\simulated_trades_050.csv`
- `baltasar_v2_rich_features.parquet`: `data\output\magi_v2\baltasar_v2_rich_features\baltasar_v2_rich_features.parquet`

## Output

- Rows: `31,392`
- Columns: `91`
- Feature columns: `68`
- Rich feature match rate: `100.00%`
- Selected at threshold 0.50: `4,907` (`15.63%`)

## Label

`context_quality_rr2`:

- `FAVORABLE`: selected trade ended with `R > +0.10`.
- `UNFAVORABLE`: selected trade ended with `R < -0.10`.
- `NEUTRAL`: absolute R near zero, missing R, or same-bar ambiguous.

## Label distribution

| Label | Rows | Share |
| --- | ---: | ---: |
| UNFAVORABLE | 18,306 | 58.31% |
| FAVORABLE | 12,358 | 39.37% |
| NEUTRAL | 728 | 2.32% |

## Distribution by split

| split | FAVORABLE | NEUTRAL | UNFAVORABLE | TOTAL |
| --- | ---: | ---: | ---: | ---: |
| test | 7,822 | 354 | 11,791 | 19,967 |
| validation | 4,536 | 374 | 6,515 | 11,425 |

## Distribution by predicted direction

| prediction | FAVORABLE | NEUTRAL | UNFAVORABLE | TOTAL |
| --- | ---: | ---: | ---: | ---: |
| ENTER_BUY | 5,892 | 340 | 8,061 | 14,293 |
| ENTER_SELL | 6,466 | 388 | 10,245 | 17,099 |

## 2026Q2 diagnostic

- Rows: `459`
- Avg R: `-0.0572`
- Label distribution: `{'UNFAVORABLE': 287, 'FAVORABLE': 148, 'NEUTRAL': 24}`

## Favorable context examples

| prediction | regime | market_structure | structure_direction | mtf_alignment_status | rows | avg_r |
| --- | --- | --- | --- | --- | ---: | ---: |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bullish | ok | 122 | 1.5179 |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_low | trend | bearish | ok | 101 | 1.6844 |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bearish | ok | 85 | 1.7764 |
| ENTER_SELL | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bullish | ok | 77 | 1.8857 |
| ENTER_SELL | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_low | trend | bullish | ok | 77 | 1.7612 |
| ENTER_SELL | overlap|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bullish | ok | 71 | 1.6332 |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | trend | bearish | ok | 66 | 1.8323 |
| ENTER_SELL | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bearish | ok | 64 | 1.8447 |

## Unfavorable context examples

| prediction | regime | market_structure | structure_direction | mtf_alignment_status | rows | avg_r |
| --- | --- | --- | --- | --- | ---: | ---: |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_low | trend | bearish | ok | 167 | -0.9958 |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | range | neutral | ok | 134 | -0.9861 |
| ENTER_SELL | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bullish | ok | 133 | -0.9638 |
| ENTER_SELL | overlap|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | range | neutral | ok | 127 | -0.9747 |
| ENTER_BUY | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_high | breakout | bullish | ok | 117 | -0.9877 |
| ENTER_SELL | london|h4_range|d1_bearish|align_aligned|atr_extended|d1pos_low | breakout | bullish | ok | 115 | -0.9168 |
| ENTER_BUY | london|h4_range|d1_bearish|align_aligned|atr_extended|d1pos_low | trend | bearish | ok | 106 | -0.9977 |
| ENTER_SELL | london|h4_range|d1_range|align_neutral|atr_extended|d1pos_mid_low | trend | bullish | ok | 103 | -0.9764 |

## Feature columns

`spread_pips`, `atr`, `daily_range_position`, `regime`, `anchor_open`, `anchor_high`, `anchor_low`, `anchor_close`, `candle_body_pct`, `upper_wick_pct`, `lower_wick_pct`, `returns_1`, `returns_3`, `returns_6`, `volatility_12`, `recent_range`, `ema_20`, `ema_50`, `ema_200`, `ema_20_50_distance`, `ema_50_200_distance`, `close_to_ema20`, `close_to_ema50`, `close_to_ema200`, `ema_20_slope`, `ema_50_slope`, `rsi_14`, `momentum`, `market_structure`, `structure_direction`, `support_distance_pips`, `resistance_distance_pips`, `mtf_alignment_status`, `htf_directional_alignment`, `htf_h4_structure`, `htf_d1_structure`, `m15_ema_20`, `m15_ema_50`, `m15_ema_200`, `m15_rsi_14`, `m15_market_structure`, `m15_structure_direction`, `m15_recent_range`, `m15_candle_pattern`, `h1_ema_20`, `h1_ema_50`, `h1_ema_200`, `h1_rsi_14`, `h1_market_structure`, `h1_structure_direction`, `h1_recent_range`, `h1_candle_pattern`, `h4_ema_20`, `h4_ema_50`, `h4_ema_200`, `h4_rsi_14`, `h4_market_structure`, `h4_structure_direction`, `h4_recent_range`, `h4_candle_pattern`, `d1_ema_20`, `d1_ema_50`, `d1_ema_200`, `d1_rsi_14`, `d1_market_structure`, `d1_structure_direction`, `d1_recent_range`, `d1_candle_pattern`

## Main feature nulls

| Column | Nulls |
| --- | ---: |
| `lower_wick_pct` | 1 |
| `candle_body_pct` | 1 |
| `upper_wick_pct` | 1 |
| `spread_pips` | 0 |
| `regime` | 0 |
| `daily_range_position` | 0 |
| `atr` | 0 |
| `anchor_open` | 0 |
| `anchor_close` | 0 |
| `anchor_low` | 0 |
| `anchor_high` | 0 |
| `returns_1` | 0 |
| `returns_3` | 0 |
| `returns_6` | 0 |
| `volatility_12` | 0 |

## Technical decisions

- The principal universe is threshold `0.40`; threshold `0.50` is stored only as diagnostic `selected_at_050` to avoid duplicate context rows.
- Exact `hour`, `weekday`, and `session` are kept only as diagnostics, not as Gaspar feature columns.
- Policy decisions such as threshold, variant, prediction confidence, and selected-at-threshold are not feature columns.
- Baltasar labels and first-touch/R diagnostics are not Gaspar features.
- `regime` is retained as a market-context feature, but should be reviewed before training if it encodes time/session directly.

## Next step

Train a first Gaspar v2 context classifier using only the listed feature columns, then evaluate whether it can identify high-loss SELL contexts and the 2026Q2 regime deterioration before CEO-MAGI uses it as a blocking/caution signal.
