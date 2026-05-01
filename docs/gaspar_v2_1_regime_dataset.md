# Gaspar v2.1 Regime Dataset

## Scope

Each row is an aggregated context, not an individual trade.

The dataset groups Baltasar v2 `rich_policy_medium 0.40` trades by context buckets and assigns a regime/blocking label from aggregate RR 1:2 first-touch performance.

## Inputs

- Selected full trades source: `data\output\magi_v2\gaspar_v2_dataset_full\gaspar_v2_dataset_full.parquet`
- Rich features base: `data\output\magi_v2\baltasar_v2_rich_features\baltasar_v2_rich_features.parquet`
- RR2 labels base: `data\output\magi_v2\rr2_first_touch_labels\rr2_first_touch_labels.parquet`
- Optional policy reference: `data\output\magi_v2\baltasar_v2_rich_features_model\policy_medium_r_simulation\simulated_trades_040.csv`

## Context Definition

`split`, `hour_bucket`, `daily_range_bucket`, `atr_bucket`, `h4_market_structure`, `d1_market_structure`, `predicted_direction`

## Label Rule

- `NEUTRAL`: sample size < `50` or mixed/ambiguous context.
- `BLOCK`: avg R < 0 or PF < 1.
- `ALLOW`: avg R > 0 and PF >= 1.

## Dataset Size

- Contexts: `2,527`
- Source trades covered: `100,876`

## Label Distribution

| Label | Contexts |
| --- | ---: |
| NEUTRAL | 1,905 |
| ALLOW | 535 |
| BLOCK | 87 |

## Label Distribution by Split

### test

| Label | Contexts |
| --- | ---: |
| NEUTRAL | 620 |
| ALLOW | 66 |
| BLOCK | 52 |

### train

| Label | Contexts |
| --- | ---: |
| NEUTRAL | 766 |
| ALLOW | 449 |
| BLOCK | 4 |

### validation

| Label | Contexts |
| --- | ---: |
| NEUTRAL | 519 |
| BLOCK | 31 |
| ALLOW | 20 |

## BLOCK Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | d1_market_structure | predicted_direction | sample_size | avg_r | PF | DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | london_open | mid_high | atr_mid_low | breakout | breakout | SELL | 79 | -1.0000 | 0.0000 | 79.00 |
| test | asia_core | mid_high | atr_mid_high | breakout | range | SELL | 63 | -0.9524 | 0.0323 | 60.00 |
| test | overlap | mid_high | atr_low | breakout | range | BUY | 55 | -0.8909 | 0.0755 | 49.00 |
| test | overlap | mid_high | atr_mid_high | breakout | range | SELL | 89 | -0.8872 | 0.0711 | 78.96 |
| test | overlap | mid | atr_low | trend | range | SELL | 54 | -0.8630 | 0.0412 | 46.60 |
| validation | overlap | mid_high | atr_mid_high | breakout | breakout | BUY | 69 | -0.8261 | 0.1231 | 57.00 |
| test | london_mid | mid_high | atr_mid_low | trend | breakout | SELL | 107 | -0.8193 | 0.1204 | 97.67 |
| test | london_open | mid_high | atr_mid_low | breakout | trend | BUY | 51 | -0.7647 | 0.1702 | 45.00 |

## ALLOW Examples

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | d1_market_structure | predicted_direction | sample_size | avg_r | PF | DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | london_open | mid_low | atr_mid_low | range | breakout | SELL | 89 | 1.9537 | 174.8800 | 1.00 |
| train | asia_core | mid_high | atr_low | range | range | BUY | 97 | 1.9463 | 1717.2727 | 0.11 |
| train | london_open | low | atr_low | trend | trend | SELL | 63 | 1.9460 | inf | 0.00 |
| train | asia_core | mid | atr_low | trend | range | SELL | 55 | 1.9455 | 108.0000 | 1.00 |
| train | asia_core | mid | atr_low | range | breakout | BUY | 173 | 1.8838 | 82.4750 | 2.00 |
| train | asia_core | low | atr_mid_low | breakout | trend | SELL | 51 | 1.8806 | 260.2162 | 0.37 |
| train | london_open | mid_high | atr_low | breakout | trend | SELL | 50 | 1.8800 | 48.0000 | 1.00 |
| train | london_open | mid_high | atr_low | trend | trend | SELL | 64 | 1.8664 | inf | 0.00 |

## 2026Q2 BLOCK Examples

_No examples._

## 2026Q2 Worst Context Examples

These are diagnostic examples even when the formal label is `NEUTRAL` because the 2026Q2 sample is small after granular grouping.

| split | hour_bucket | daily_range_bucket | atr_bucket | h4_market_structure | d1_market_structure | predicted_direction | sample_size | avg_r | PF | DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | london_mid | mid_high | atr_mid_high | breakout | trend | SELL | 36 | -1.0000 | 0.0000 | 36.00 |
| test | inactive | mid | atr_mid_high | breakout | breakout | SELL | 12 | -1.0000 | 0.0000 | 12.00 |
| test | london_open | mid | atr_mid_high | range | breakout | SELL | 12 | -1.0000 | 0.0000 | 12.00 |
| test | london_open | mid | atr_mid_low | range | breakout | SELL | 10 | -1.0000 | 0.0000 | 10.00 |
| test | overlap | mid_high | atr_mid_high | breakout | trend | SELL | 6 | -1.0000 | 0.0000 | 6.00 |
| test | london_open | mid | atr_mid_high | trend | breakout | SELL | 2 | -1.0000 | 0.0000 | 2.00 |
| test | london_mid | mid | atr_mid_low | breakout | trend | BUY | 1 | -1.0000 | 0.0000 | 1.00 |
| test | london_open | mid_high | atr_mid_high | breakout | trend | SELL | 12 | -0.9383 | 0.0000 | 11.26 |

## Technical Warnings

- Rows are aggregated contexts, not individual trades.
- Labels are computed independently within train, validation and test splits to avoid mixing future outcome periods.
- Aggregated outcome metrics are stored for diagnostics and label construction; they should not be used as predictive features without a causal redesign.
- ATR buckets use train-period quartiles, then apply those thresholds to validation/test.
- No gaspar_training_v1 data is used.

## CEO Usage

Gaspar v2.1 should later map context outputs to `ALLOW`, `CAUTION`, or `BLOCK` signals for CEO-MAGI. It should not vote direction.

## Limitations

- This first version uses split-local aggregate labels, not causal rolling labels.
- Aggregate outcome metrics are diagnostics; do not feed them as model features unless they are rebuilt causally from past-only data.
- Context granularity may create low-sample contexts, intentionally labelled `NEUTRAL`.
