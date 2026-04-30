# Baltasar v2 Rich Coarse Timing

## Scope

- Model: `HistGradientBoostingClassifier`
- Target: `tradeable_direction_rr2_first_touch`
- Feature count: `70`
- Removed features: `['hour', 'weekday', 'regime']`
- Created features: `['hour_bucket', 'weekday_bucket']`

## Splits

| split | rows | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | --- | --- | --- | --- |
| train | 237132 | 139635 | 48210 | 49287 |
| validation | 59378 | 42450 | 8148 | 8780 |
| test | 74991 | 43774 | 15606 | 15611 |

## Validation Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 33202 | 0.559163 | 0.216824 | 0.020126 | 668.230000 | 1.036841 | 630.600000 |
| 0.40 | 20043 | 0.337549 | 0.237190 | 0.003990 | 79.980000 | 1.006912 | 608.790000 |
| 0.50 | 3116 | 0.052477 | 0.261553 | 0.025026 | 77.980000 | 1.043029 | 203.070000 |
| 0.60 | 122 | 0.002055 | 0.434426 | 0.374344 | 45.670000 | 1.717292 | 20.570000 |
| 0.70 | 1 | 0.000017 | 1.000000 | 2.000000 | 2.000000 |  | 0.000000 |

## Test Thresholds

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 51820 | 0.691016 | 0.257449 | 0.009802 | 507.830000 | 1.016627 | 780.420000 |
| 0.40 | 37028 | 0.493766 | 0.276791 | 0.012952 | 479.580000 | 1.021343 | 679.750000 |
| 0.50 | 7486 | 0.099825 | 0.292680 | 0.034224 | 256.200000 | 1.056056 | 327.420000 |
| 0.60 | 395 | 0.005267 | 0.420253 | 0.339620 | 134.150000 | 1.649889 | 51.000000 |
| 0.70 | 3 | 0.000040 | 1.000000 | 2.000000 | 6.000000 |  | 0.000000 |

## Annual Stability at Threshold 0.50

| period | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 10503 | 0.181795 | 0.772732 | 1.389024 | 14588.920000 | 8.351322 | 26.000000 |
| 2021 | 11843 | 0.198246 | 0.804019 | 1.542262 | 18265.010000 | 12.979491 | 31.000000 |
| 2022 | 16054 | 0.268157 | 0.758316 | 1.350425 | 21679.720000 | 7.717166 | 44.000000 |
| 2023 | 8839 | 0.147931 | 0.817061 | 1.540700 | 13618.250000 | 12.216375 | 22.070000 |
| 2024 | 3116 | 0.052477 | 0.261553 | 0.025026 | 77.980000 | 1.043029 | 203.070000 |
| 2025 | 5977 | 0.101856 | 0.287770 | 0.028817 | 172.240000 | 1.047191 | 327.420000 |
| 2026 | 1509 | 0.092520 | 0.312127 | 0.055639 | 83.960000 | 1.091202 | 239.350000 |

## Quarterly Stability at Threshold 0.50

| period | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020Q1 | 2770 | 0.219180 | 0.722744 | 1.243292 | 3443.920000 | 6.197115 | 22.000000 |
| 2020Q2 | 2128 | 0.142094 | 0.796992 | 1.455174 | 3096.610000 | 9.572405 | 17.000000 |
| 2020Q3 | 2897 | 0.189793 | 0.792889 | 1.435951 | 4159.950000 | 9.203088 | 18.000000 |
| 2020Q4 | 2708 | 0.181794 | 0.783235 | 1.435908 | 3888.440000 | 9.573911 | 26.000000 |
| 2021Q1 | 4267 | 0.296773 | 0.780642 | 1.462353 | 6239.860000 | 10.369581 | 25.000000 |
| 2021Q2 | 2972 | 0.199584 | 0.820659 | 1.581393 | 4699.900000 | 14.378594 | 31.000000 |
| 2021Q3 | 2084 | 0.136530 | 0.829175 | 1.659726 | 3458.870000 | 22.172002 | 12.630000 |
| 2021Q4 | 2520 | 0.165724 | 0.803175 | 1.534278 | 3866.380000 | 12.237843 | 19.000000 |
| 2022Q1 | 2627 | 0.179158 | 0.777313 | 1.442569 | 3789.630000 | 9.833636 | 29.560000 |
| 2022Q2 | 3552 | 0.237148 | 0.778716 | 1.405251 | 4991.450000 | 8.581873 | 23.000000 |
| 2022Q3 | 4029 | 0.263989 | 0.783073 | 1.397865 | 5632.000000 | 8.317422 | 35.000000 |
| 2022Q4 | 5846 | 0.390645 | 0.720322 | 1.243011 | 7266.640000 | 6.302182 | 44.000000 |
| 2023Q1 | 2719 | 0.182068 | 0.809857 | 1.538488 | 4183.150000 | 12.403200 | 22.070000 |
| 2023Q2 | 1531 | 0.102538 | 0.902678 | 1.790346 | 2741.020000 | 33.534362 | 12.840000 |
| 2023Q3 | 2405 | 0.160794 | 0.767983 | 1.395917 | 3357.180000 | 8.611100 | 18.000000 |
| 2023Q4 | 2184 | 0.146292 | 0.820055 | 1.527885 | 3336.900000 | 11.364331 | 16.000000 |
| 2024Q1 | 470 | 0.032067 | 0.338298 | 0.259383 | 121.910000 | 1.508107 | 78.430000 |
| 2024Q2 | 894 | 0.059644 | 0.212528 | -0.112707 | -100.760000 | 0.820546 | 203.070000 |
| 2024Q3 | 593 | 0.040065 | 0.281619 | 0.120523 | 71.470000 | 1.230973 | 84.860000 |
| 2024Q4 | 1159 | 0.077624 | 0.257981 | -0.012632 | -14.640000 | 0.979128 | 132.260000 |
| 2025Q1 | 1591 | 0.113376 | 0.274670 | 0.004613 | 7.340000 | 1.007548 | 208.630000 |
| 2025Q2 | 1530 | 0.102157 | 0.345098 | 0.067667 | 103.530000 | 1.106369 | 154.200000 |
| 2025Q3 | 1710 | 0.113742 | 0.277193 | -0.043058 | -73.630000 | 0.932823 | 210.140000 |
| 2025Q4 | 1146 | 0.078295 | 0.245201 | 0.117801 | 135.000000 | 1.222039 | 106.970000 |
| 2026Q1 | 1017 | 0.072560 | 0.376598 | 0.230521 | 234.440000 | 1.416006 | 75.000000 |
| 2026Q2 | 492 | 0.214473 | 0.178862 | -0.305854 | -150.480000 | 0.578535 | 239.350000 |

## Comparison: Rich With Timing

| split | threshold | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.40 | 20564 | 0.346324 | 0.014781 | 1.025651 | 303.960000 |
| validation | 0.50 | 3660 | 0.061639 | 0.105413 | 1.187423 | 385.810000 |
| test | 0.40 | 35242 | 0.469950 | 0.057629 | 1.096255 | 2030.950000 |
| test | 0.50 | 6765 | 0.090211 | 0.082132 | 1.136375 | 555.620000 |

## Comparison: Rich No Timing

| split | threshold | trades | coverage | avg_r | PF | total_r |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.40 | 13300 | 0.223989 | 0.001479 | 1.002672 | 19.670000 |
| validation | 0.50 | 1554 | 0.026171 | 0.002220 | 1.003881 | 3.450000 |
| test | 0.40 | 27870 | 0.371645 | 0.006342 | 1.010628 | 176.710000 |
| test | 0.50 | 3358 | 0.044779 | 0.065870 | 1.112127 | 221.190000 |

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
| hour_bucket | 0.061401 | permutation_f1_macro |
| weekday_bucket | 0.010741 | permutation_f1_macro |
| spread_pips | 0.002037 | permutation_f1_macro |
| m15_recent_range | 0.001652 | permutation_f1_macro |
| structure_direction | 0.001631 | permutation_f1_macro |
| d1_ema_50 | 0.001439 | permutation_f1_macro |
| h4_market_structure | 0.000940 | permutation_f1_macro |
| volatility_12 | 0.000929 | permutation_f1_macro |
| h4_structure_direction | 0.000918 | permutation_f1_macro |
| ema_20 | 0.000563 | permutation_f1_macro |
| m15_structure_direction | 0.000523 | permutation_f1_macro |
| h1_candle_pattern | 0.000327 | permutation_f1_macro |
| ema_200 | 0.000325 | permutation_f1_macro |
| h4_candle_pattern | 0.000316 | permutation_f1_macro |
| market_structure | 0.000140 | permutation_f1_macro |
| resistance_distance_pips | 0.000092 | permutation_f1_macro |
| close_to_ema50 | 0.000014 | permutation_f1_macro |
| candle_body_pct | 0.000000 | permutation_f1_macro |
| upper_wick_pct | 0.000000 | permutation_f1_macro |
| lower_wick_pct | 0.000000 | permutation_f1_macro |
| ema_20_slope | 0.000000 | permutation_f1_macro |
| ema_50_slope | 0.000000 | permutation_f1_macro |
| mtf_alignment_status | 0.000000 | permutation_f1_macro |
| m15_market_structure | 0.000000 | permutation_f1_macro |
| m15_candle_pattern | 0.000000 | permutation_f1_macro |

## Leakage Check

- Passed: `True`
- Forbidden features in model: `[]`

## Technical Decisions

- Features are loaded from rich feature summary.
- hour and weekday are removed and replaced by coarse buckets.
- session is kept because it is a coarse operational window.
- regime is removed because it encodes session/timing as a prefix.
- Diagnostic columns are used only for operational R metrics.
- No mage logic or Baltasar v1 artifact is modified.
- RandomForest was skipped to keep this coarse timing experiment lightweight.
