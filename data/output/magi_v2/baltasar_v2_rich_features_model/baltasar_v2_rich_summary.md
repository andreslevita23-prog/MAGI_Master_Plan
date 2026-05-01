# Baltasar v2 Rich Features Model

## Scope

- Model: `HistGradientBoostingClassifier`
- Target: `tradeable_direction_rr2_first_touch`
- Feature count: `71`
- Experiment isolated; Baltasar v1 is not replaced.

## Splits

| split | rows | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | --- | --- | --- | --- |
| train | 237132 | 139635 | 48210 | 49287 |
| validation | 59378 | 42450 | 8148 | 8780 |
| test | 74991 | 43774 | 15606 | 15611 |

## Validation Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 32149 | 0.541429 | 0.216274 | 0.004945 | 158.970000 | 1.008863 | 901.740000 | 0.212262 | 0.221686 |
| 0.40 | 20564 | 0.346324 | 0.239739 | 0.014781 | 303.960000 | 1.025651 | 566.890000 | 0.232300 | 0.250294 |
| 0.50 | 3660 | 0.061639 | 0.285792 | 0.105413 | 385.810000 | 1.187423 | 193.230000 | 0.264109 | 0.321121 |
| 0.60 | 237 | 0.003991 | 0.417722 | 0.440844 | 104.480000 | 1.957215 | 31.000000 | 0.313869 | 0.560000 |
| 0.70 | 3 | 0.000051 | 1.000000 | 2.000000 | 6.000000 |  | 0.000000 | 1.000000 |  |

## Test Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 50456 | 0.672827 | 0.270572 | 0.037834 | 1908.350000 | 1.064760 | 616.600000 | 0.277792 | 0.266041 |
| 0.40 | 35242 | 0.469950 | 0.297855 | 0.057629 | 2030.950000 | 1.096255 | 513.930000 | 0.319789 | 0.286051 |
| 0.50 | 6765 | 0.090211 | 0.320769 | 0.082132 | 555.620000 | 1.136375 | 292.510000 | 0.368388 | 0.306390 |
| 0.60 | 433 | 0.005774 | 0.316397 | 0.063857 | 27.650000 | 1.109064 | 54.020000 | 0.206349 | 0.335135 |
| 0.70 | 12 | 0.000160 | 1.000000 | 2.000000 | 24.000000 |  | 0.000000 |  | 1.000000 |

## Comparisons

### Baltasar v1 signal

| split | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | 26701 | 0.449678 | 0.186173 | 0.006375 | 170.080000 | 1.012434 | 878.240000 |
| test | 48457 | 0.646171 | 0.263264 | 0.083469 | 4037.150000 | 1.152036 | 766.960000 |

### Baltasar v2 pure directional

| split | threshold | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.40 | 22089 | 0.372006 | -0.032021 | 0.944210 | -707.210000 |
| validation | 0.50 | 1189 | 0.020024 | 0.159428 | 1.296540 | 189.560000 |
| test | 0.40 | 32179 | 0.429105 | 0.022056 | 1.036459 | 709.480000 |
| test | 0.50 | 3609 | 0.048126 | 0.056017 | 1.093229 | 202.110000 |

## Top Feature Importance

| feature | importance | method |
| --- | --- | --- |
| hour | 0.036725 | permutation_f1_macro |
| weekday | 0.018388 | permutation_f1_macro |
| session | 0.015627 | permutation_f1_macro |
| volatility_12 | 0.004262 | permutation_f1_macro |
| d1_market_structure | 0.001401 | permutation_f1_macro |
| h1_ema_20 | 0.001152 | permutation_f1_macro |
| htf_h4_structure | 0.000986 | permutation_f1_macro |
| ema_20_50_distance | 0.000910 | permutation_f1_macro |
| ema_20 | 0.000874 | permutation_f1_macro |
| returns_3 | 0.000680 | permutation_f1_macro |
| returns_6 | 0.000617 | permutation_f1_macro |
| close_to_ema20 | 0.000469 | permutation_f1_macro |
| m15_recent_range | 0.000300 | permutation_f1_macro |
| h4_market_structure | 0.000287 | permutation_f1_macro |
| h4_ema_20 | 0.000244 | permutation_f1_macro |
| returns_1 | 0.000236 | permutation_f1_macro |
| close_to_ema50 | 0.000133 | permutation_f1_macro |
| anchor_high | 0.000109 | permutation_f1_macro |
| h4_ema_200 | 0.000043 | permutation_f1_macro |
| momentum | 0.000001 | permutation_f1_macro |
| candle_body_pct | 0.000000 | permutation_f1_macro |
| upper_wick_pct | 0.000000 | permutation_f1_macro |
| lower_wick_pct | 0.000000 | permutation_f1_macro |
| ema_20_slope | 0.000000 | permutation_f1_macro |
| ema_50_slope | 0.000000 | permutation_f1_macro |

## Leakage Check

- Passed: `True`
- Forbidden features in model: `[]`

## Technical Decisions

- Feature list is loaded exclusively from baltasar_v2_rich_features_summary.json.
- Diagnostic columns are used only for operational R metrics.
- Categorical features use OrdinalEncoder for HGB runtime practicality.
- RandomForest was not trained in this run because HGB was prioritized and previous RF baselines were slower/weaker.
- No mage logic or Baltasar v1 artifact is modified.
