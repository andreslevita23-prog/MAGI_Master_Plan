# Gaspar v2 context classifier

## Status

`BLOCKED`: no model was trained.

The provided dataset does not contain any rows in the required train window `2020-2023`.
Training on 2024 validation rows or 2025-2026 test rows would break the temporal contract and contaminate evaluation.

## Split audit

| Split | Rows |
| --- | ---: |
| Train 2020-2023 | 0 |
| Validation 2024 | 11,425 |
| Test 2025-2026 | 19,967 |

## Label distribution

| Label | Rows |
| --- | ---: |
| UNFAVORABLE | 18,306 |
| FAVORABLE | 12,358 |
| NEUTRAL | 728 |

## Leakage check

- Feature columns inferred: `68`.
- Forbidden feature intersection: `[]`.
- Diagnostic/result columns such as `realized_R`, `buy_R`, `sell_R`, `selected_at_050`, policy decisions, and target are excluded from features.

## Required next action

Generate Gaspar v2 train-period examples for `2020-2023` before training. The clean path is:

1. Apply the already-trained Baltasar v2 rich model to `baltasar_v2_rich_features.parquet` rows from 2020-2023.
2. Apply the existing `rich_policy_medium` selection rules at threshold `0.40`.
3. Label selected train trades with the same RR 1:2 first-touch R logic.
4. Rebuild `gaspar_v2_dataset.parquet` with train, validation, and test rows.
5. Train Gaspar v2 only after `train.parquet` is non-empty.

## Intended model once unblocked

- Primary model: `HistGradientBoostingClassifier`.
- Target: `context_quality_rr2`.
- Operational use: block when `P(UNFAVORABLE)` exceeds `0.50`, `0.60`, or `0.70`, then compare filtered R/PF/DD against Baltasar v2 medium `0.40`.
