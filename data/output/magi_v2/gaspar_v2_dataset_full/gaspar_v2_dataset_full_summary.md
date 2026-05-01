# Gaspar v2 Full Dataset

## Status

Rebuilt from the complete 2020-2026 MAGI v2 base, not from `policy_trades.csv` and not from `gaspar_training_v1`.

## Sources

- Rich features: `data\output\magi_v2\baltasar_v2_rich_features\baltasar_v2_rich_features.parquet`
- RR2 first-touch labels: `data\output\magi_v2\rr2_first_touch_labels\rr2_first_touch_labels.parquet`
- Baltasar v2 rich model: `data\output\magi_v2\baltasar_v2_rich_features_model\baltasar_v2_rich_model.joblib`
- Explicitly not used as base: `gaspar_training_v1`, old `gaspar_v2_dataset.parquet`, `policy_trades.csv`.

## Policy Applied

- Baltasar rich model directional probability threshold >= 0.40
- block session == inactive
- block daily_range_position > 0.85
- block hours [13, 15, 16, 20, 22]

## Dataset Size

- Rows: `100,876`
- Columns: `94`
- Feature columns for Gaspar: `68`
- Temporal range: `2020-01-15T12:00:00+00:00` to `2026-04-09T14:05:00+00:00`
- Valid train 2020-2023: `True`

## Split Rows

| Split | Rows |
| --- | ---: |
| train | 69,484 |
| validation | 11,425 |
| test | 19,967 |

## Label Distribution by Split

### train

| Label | Rows |
| --- | ---: |
| FAVORABLE | 46,276 |
| UNFAVORABLE | 22,628 |
| NEUTRAL | 580 |

### validation

| Label | Rows |
| --- | ---: |
| UNFAVORABLE | 6,515 |
| FAVORABLE | 4,536 |
| NEUTRAL | 374 |

### test

| Label | Rows |
| --- | ---: |
| UNFAVORABLE | 11,791 |
| FAVORABLE | 7,822 |
| NEUTRAL | 354 |

## Leakage Check

- Forbidden feature intersection: `[]`
- Direct timing feature intersection: `[]`
- Gaspar v1 used: `False`

## Next Step

Train `Gaspar v2 context classifier` using the generated `train.parquet`, `validation.parquet`, and `test.parquet` splits.
