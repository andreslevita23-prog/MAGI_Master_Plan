# Gaspar v2.1b Regime Dataset

## Scope

This version reduces context granularity by excluding `d1_market_structure` and adds explicit SELL risk labels.

- Source trades: `100,876`
- Recommended min sample: `25`

## Grouping

`split`, `hour_bucket`, `daily_range_bucket`, `atr_bucket`, `h4_market_structure`, `predicted_direction`

## Configuration Comparison

### MIN_SAMPLE_SIZE = 25

- Contexts: `1,202`
- Has sufficient train BLOCK: `False`
- Q2 train context match rate: `100.00%`

Context label distribution by split:

| Split | ALLOW | BLOCK | NEUTRAL |
| --- | ---: | ---: | ---: |
| test | 121 | 98 | 161 |
| train | 425 | 3 | 64 |
| validation | 70 | 74 | 186 |

SELL risk distribution by split:

| Split | NOT_SELL | SELL_RISK_HIGH | SELL_RISK_LOW | SELL_RISK_NEUTRAL |
| --- | ---: | ---: | ---: | ---: |
| test | 183 | 57 | 69 | 71 |
| train | 245 | 2 | 208 | 37 |
| validation | 176 | 31 | 26 | 97 |

### MIN_SAMPLE_SIZE = 40

- Contexts: `1,202`
- Has sufficient train BLOCK: `False`
- Q2 train context match rate: `100.00%`

Context label distribution by split:

| Split | ALLOW | BLOCK | NEUTRAL |
| --- | ---: | ---: | ---: |
| test | 89 | 66 | 225 |
| train | 379 | 3 | 110 |
| validation | 44 | 46 | 240 |

SELL risk distribution by split:

| Split | NOT_SELL | SELL_RISK_HIGH | SELL_RISK_LOW | SELL_RISK_NEUTRAL |
| --- | ---: | ---: | ---: | ---: |
| test | 183 | 42 | 54 | 101 |
| train | 245 | 2 | 193 | 52 |
| validation | 176 | 19 | 16 | 119 |

### MIN_SAMPLE_SIZE = 50

- Contexts: `1,202`
- Has sufficient train BLOCK: `False`
- Q2 train context match rate: `100.00%`

Context label distribution by split:

| Split | ALLOW | BLOCK | NEUTRAL |
| --- | ---: | ---: | ---: |
| test | 80 | 54 | 246 |
| train | 351 | 2 | 139 |
| validation | 28 | 34 | 268 |

SELL risk distribution by split:

| Split | NOT_SELL | SELL_RISK_HIGH | SELL_RISK_LOW | SELL_RISK_NEUTRAL |
| --- | ---: | ---: | ---: | ---: |
| test | 183 | 36 | 49 | 112 |
| train | 245 | 2 | 180 | 65 |
| validation | 176 | 14 | 8 | 132 |

## Recommended Configuration

`MIN_SAMPLE_SIZE = 25`

- Train BLOCK contexts: `3`
- Train SELL_RISK_HIGH contexts: `2`
- Trainable: `False`
- Reason: min_sample=25 gives the best balance between coarse context coverage and enough BLOCK/SELL_RISK_HIGH examples in train among the tested settings.

## Bad SELL Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | predicted_direction | sample_size | avg_r | PF | DD | context_block_rr2 | sell_risk_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | london_open | mid_high | atr_low | range | SELL | 44 | -1.0000 | 0.0000 | 44.00 | BLOCK | SELL_RISK_HIGH |
| test | asia_core | mid_high | atr_mid_low | breakout | SELL | 33 | -1.0000 | 0.0000 | 33.00 | BLOCK | SELL_RISK_HIGH |
| validation | london_open | mid_low | atr_mid_high | breakout | SELL | 27 | -1.0000 | 0.0000 | 27.00 | BLOCK | SELL_RISK_HIGH |
| test | overlap | mid | atr_mid_low | trend | SELL | 25 | -1.0000 | 0.0000 | 25.00 | BLOCK | SELL_RISK_HIGH |
| validation | london_open | mid | atr_low | range | SELL | 26 | -0.9588 | 0.0028 | 25.00 | BLOCK | SELL_RISK_HIGH |
| validation | london_mid | mid_high | atr_mid_low | breakout | SELL | 34 | -0.9541 | 0.0170 | 33.00 | BLOCK | SELL_RISK_HIGH |
| test | new_york_mid | mid | atr_low | trend | SELL | 69 | -0.9439 | 0.0012 | 65.13 | BLOCK | SELL_RISK_HIGH |
| test | overlap | mid_low | atr_low | range | SELL | 26 | -0.8738 | 0.0000 | 22.72 | BLOCK | SELL_RISK_HIGH |

## BLOCK Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | predicted_direction | sample_size | avg_r | PF | DD | context_block_rr2 | sell_risk_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | london_open | mid_high | atr_low | range | SELL | 44 | -1.0000 | 0.0000 | 44.00 | BLOCK | SELL_RISK_HIGH |
| test | london_open | mid | atr_mid_low | trend | BUY | 36 | -1.0000 | 0.0000 | 36.00 | BLOCK | NOT_SELL |
| test | asia_core | mid_high | atr_mid_low | breakout | SELL | 33 | -1.0000 | 0.0000 | 33.00 | BLOCK | SELL_RISK_HIGH |
| validation | london_open | mid_low | atr_mid_high | breakout | SELL | 27 | -1.0000 | 0.0000 | 27.00 | BLOCK | SELL_RISK_HIGH |
| test | overlap | mid | atr_mid_low | trend | SELL | 25 | -1.0000 | 0.0000 | 25.00 | BLOCK | SELL_RISK_HIGH |
| validation | london_mid | mid_high | atr_low | breakout | BUY | 48 | -0.9979 | 0.0000 | 47.90 | BLOCK | NOT_SELL |
| test | london_mid | mid_low | atr_mid_low | range | BUY | 30 | -0.9830 | 0.0000 | 29.49 | BLOCK | NOT_SELL |
| validation | london_open | mid | atr_low | range | SELL | 26 | -0.9588 | 0.0028 | 25.00 | BLOCK | SELL_RISK_HIGH |

## ALLOW Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | predicted_direction | sample_size | avg_r | PF | DD | context_block_rr2 | sell_risk_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | asia_core | mid_low | atr_low | range | SELL | 64 | 2.0000 | inf | 0.00 | ALLOW | SELL_RISK_LOW |
| train | asia_core | mid_low | atr_mid_low | trend | BUY | 39 | 2.0000 | inf | 0.00 | ALLOW | NOT_SELL |
| train | asia_core | mid | atr_mid_low | trend | SELL | 27 | 2.0000 | inf | 0.00 | ALLOW | SELL_RISK_LOW |
| train | asia_core | mid_low | atr_low | breakout | SELL | 32 | 1.9878 | inf | 0.00 | ALLOW | SELL_RISK_LOW |
| train | inactive | mid_high | atr_mid_low | range | BUY | 28 | 1.9832 | inf | 0.00 | ALLOW | NOT_SELL |
| train | asia_core | low | atr_mid_low | range | BUY | 38 | 1.9795 | inf | 0.00 | ALLOW | NOT_SELL |
| train | asia_core | mid | atr_mid_low | breakout | SELL | 29 | 1.9772 | inf | 0.00 | ALLOW | SELL_RISK_LOW |
| train | asia_core | mid_high | atr_low | range | BUY | 114 | 1.9543 | 2026.3636 | 0.11 | ALLOW | NOT_SELL |

## 2026Q2 Worst Context Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | predicted_direction | sample_size | avg_r | PF | DD | context_block_rr2 | sell_risk_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | london_mid | mid_high | atr_mid_high | breakout | SELL | 36 | -1.0000 | 0.0000 | 36.00 | BLOCK | SELL_RISK_HIGH |
| test | inactive | mid | atr_mid_high | breakout | SELL | 12 | -1.0000 | 0.0000 | 12.00 | NEUTRAL | SELL_RISK_NEUTRAL |
| test | london_open | mid | atr_mid_high | range | SELL | 12 | -1.0000 | 0.0000 | 12.00 | NEUTRAL | SELL_RISK_NEUTRAL |
| test | london_open | mid | atr_mid_high | trend | SELL | 2 | -1.0000 | 0.0000 | 2.00 | NEUTRAL | SELL_RISK_NEUTRAL |
| test | london_mid | mid | atr_mid_low | breakout | BUY | 1 | -1.0000 | 0.0000 | 1.00 | NEUTRAL | NOT_SELL |
| test | london_open | mid_high | atr_mid_high | breakout | SELL | 12 | -0.9383 | 0.0000 | 11.26 | NEUTRAL | SELL_RISK_NEUTRAL |
| test | overlap | mid_high | atr_mid_high | breakout | SELL | 30 | -0.9000 | 0.0690 | 28.00 | BLOCK | SELL_RISK_HIGH |
| test | london_open | mid | atr_mid_high | breakout | SELL | 15 | -0.8053 | 0.0000 | 12.08 | NEUTRAL | SELL_RISK_NEUTRAL |

## Technical Warnings

- Rows are aggregated contexts, not individual trades.
- d1_market_structure is intentionally excluded to reduce granularity.
- Labels are computed independently within split, so this is suitable for dataset diagnostics; a production model should use causal rolling context labels.
- Aggregate R/PF/DD columns are diagnostics and label construction fields, not future model features unless rebuilt causally.
- No model is trained in this script.
