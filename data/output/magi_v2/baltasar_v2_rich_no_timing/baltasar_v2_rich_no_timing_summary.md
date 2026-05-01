# Baltasar v2 Rich No Timing

## Scope

- Model: `HistGradientBoostingClassifier`
- Target: `tradeable_direction_rr2_first_touch`
- Feature count: `67`
- Removed features: `['session', 'hour', 'weekday', 'regime']`

## Splits

| split | rows | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | --- | --- | --- | --- |
| train | 237132 | 139635 | 48210 | 49287 |
| validation | 59378 | 42450 | 8148 | 8780 |
| test | 74991 | 43774 | 15606 | 15611 |

## Validation Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 34151 | 0.575146 | 0.185588 | -0.004375 | -149.420000 | 0.991535 | 1290.460000 |
| 0.40 | 13300 | 0.223989 | 0.219098 | 0.001479 | 19.670000 | 1.002672 | 471.000000 |
| 0.50 | 1554 | 0.026171 | 0.238095 | 0.002220 | 3.450000 | 1.003881 | 111.790000 |
| 0.60 | 155 | 0.002610 | 0.361290 | 0.270645 | 41.950000 | 1.508115 | 38.500000 |
| 0.70 | 10 | 0.000168 | 0.500000 | 1.509000 | 15.090000 |  | 0.000000 |

## Test Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 60583 | 0.807870 | 0.232045 | 0.008713 | 527.520000 | 1.015471 | 1216.540000 |
| 0.40 | 27870 | 0.371645 | 0.265339 | 0.006342 | 176.710000 | 1.010628 | 726.370000 |
| 0.50 | 3358 | 0.044779 | 0.300476 | 0.065870 | 221.190000 | 1.112127 | 222.500000 |
| 0.60 | 225 | 0.003000 | 0.337778 | 0.042400 | 9.540000 | 1.065612 | 68.460000 |
| 0.70 | 1 | 0.000013 | 0.000000 | -1.000000 | -1.000000 | 0.000000 | 1.000000 |

## Comparison: Rich With Timing

| split | threshold | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.40 | 20564 | 0.346324 | 0.014781 | 1.025651 | 303.960000 |
| validation | 0.50 | 3660 | 0.061639 | 0.105413 | 1.187423 | 385.810000 |
| test | 0.40 | 35242 | 0.469950 | 0.057629 | 1.096255 | 2030.950000 |
| test | 0.50 | 6765 | 0.090211 | 0.082132 | 1.136375 | 555.620000 |

## Comparison: Baltasar v1

| split | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- |
| validation | 26701 | 0.449678 | 0.006375 | 1.012434 | 170.080000 |
| test | 48457 | 0.646171 | 0.083469 | 1.152036 | 4037.150000 |

## Comparison: Pure Directional

| split | threshold | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.40 | 22089 | 0.372006 | -0.032021 | 0.944210 | -707.210000 |
| validation | 0.50 | 1189 | 0.020024 | 0.159428 | 1.296540 | 189.560000 |
| test | 0.40 | 32179 | 0.429105 | 0.022056 | 1.036459 | 709.480000 |
| test | 0.50 | 3609 | 0.048126 | 0.056017 | 1.093229 | 202.110000 |

## Top Feature Importance

| feature | importance | method |
| --- | --- | --- |
| volatility_12 | 0.027409 | permutation_f1_macro |
| m15_recent_range | 0.022588 | permutation_f1_macro |
| h4_rsi_14 | 0.005547 | permutation_f1_macro |
| ema_50_200_distance | 0.005161 | permutation_f1_macro |
| m15_ema_20 | 0.005120 | permutation_f1_macro |
| d1_recent_range | 0.004771 | permutation_f1_macro |
| support_distance_pips | 0.004249 | permutation_f1_macro |
| recent_range | 0.002949 | permutation_f1_macro |
| h4_ema_200 | 0.002335 | permutation_f1_macro |
| returns_1 | 0.002115 | permutation_f1_macro |
| spread_pips | 0.001732 | permutation_f1_macro |
| candle_body_pct | 0.001483 | permutation_f1_macro |
| d1_ema_200 | 0.001382 | permutation_f1_macro |
| resistance_distance_pips | 0.001211 | permutation_f1_macro |
| m15_ema_50 | 0.000965 | permutation_f1_macro |
| h4_ema_50 | 0.000897 | permutation_f1_macro |
| h1_ema_50 | 0.000855 | permutation_f1_macro |
| close_to_ema50 | 0.000593 | permutation_f1_macro |
| h4_structure_direction | 0.000556 | permutation_f1_macro |
| ema_50 | 0.000434 | permutation_f1_macro |
| htf_d1_structure | 0.000387 | permutation_f1_macro |
| close_to_ema200 | 0.000368 | permutation_f1_macro |
| returns_3 | 0.000359 | permutation_f1_macro |
| h4_ema_20 | 0.000297 | permutation_f1_macro |
| h1_candle_pattern | 0.000187 | permutation_f1_macro |

## Leakage Check

- Passed: `True`
- Forbidden features in model: `[]`

## Technical Decisions

- Features are loaded from rich feature summary and direct timing variables are removed.
- regime is removed because it encodes session/timing as a prefix.
- Diagnostic columns are used only for operational R metrics.
- No mage logic or Baltasar v1 artifact is modified.
- RandomForest was skipped to keep this isolated timing-ablation experiment lightweight.
