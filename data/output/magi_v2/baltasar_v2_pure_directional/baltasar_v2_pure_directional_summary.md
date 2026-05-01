# Baltasar v2 Pure Directional

## Scope

- Target: `tradeable_direction_rr2_first_touch`.
- Selected model: `HistGradientBoostingClassifier`.
- Features: session, hour, weekday, spread_pips, atr, daily_range_position, regime.
- No mage votes, Baltasar v1 signal, first-touch outputs, R values, or future outcomes are used as features.

## Splits

| split | rows | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | --- | --- | --- | --- |
| train | 237132 | 139635 | 48210 | 49287 |
| validation | 59378 | 42450 | 8148 | 8780 |
| test | 74991 | 43774 | 15606 | 15611 |

## Validation Threshold Metrics

### RandomForestClassifier

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 40896 | 0.688740 | 0.192659 | -0.002937 | -120.070000 | 0.994422 | 1274.300000 | 0.167578 | 0.208029 |
| 0.40 | 4793 | 0.080720 | 0.201335 | -0.196109 | -939.950000 | 0.707361 | 1042.820000 | 0.171329 | 0.207878 |
| 0.50 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.60 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

### HistGradientBoostingClassifier

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 42192 | 0.710566 | 0.186576 | 0.001906 | 80.360000 | 1.003689 | 1656.980000 | 0.171383 | 0.200931 |
| 0.40 | 22089 | 0.372006 | 0.212730 | -0.032021 | -707.210000 | 0.944210 | 1842.910000 | 0.202120 | 0.221356 |
| 0.50 | 1189 | 0.020024 | 0.291842 | 0.159428 | 189.560000 | 1.296540 | 128.360000 | 0.211470 | 0.362916 |
| 0.60 | 60 | 0.001010 | 0.600000 | 0.805833 | 48.350000 | 3.044397 | 23.650000 |  | 0.600000 |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

## Test Threshold Metrics

### RandomForestClassifier

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 52017 | 0.693643 | 0.246439 | -0.014674 | -762.600000 | 0.975199 | 2142.650000 | 0.221498 | 0.261566 |
| 0.40 | 6754 | 0.090064 | 0.308114 | 0.005592 | 37.760000 | 1.008745 | 357.310000 | 0.373670 | 0.299900 |
| 0.50 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.60 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

### HistGradientBoostingClassifier

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 53776 | 0.717099 | 0.248568 | 0.003530 | 189.720000 | 1.006042 | 1007.860000 | 0.227672 | 0.267883 |
| 0.40 | 32179 | 0.429105 | 0.282234 | 0.022056 | 709.480000 | 1.036459 | 609.580000 | 0.269336 | 0.290796 |
| 0.50 | 3609 | 0.048126 | 0.304794 | 0.056017 | 202.110000 | 1.093229 | 205.310000 | 0.233645 | 0.330688 |
| 0.60 | 169 | 0.002254 | 0.189349 | -0.424497 | -71.740000 | 0.472500 | 83.740000 |  | 0.189349 |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

## Comparisons

### Baltasar v1 signal

| split | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 158721 | 0.669336 | 0.238456 | 0.005240 | 830.850000 | 1.009172 | 1868.010000 |
| validation | 26701 | 0.449678 | 0.186173 | 0.006375 | 170.080000 | 1.012434 | 878.240000 |
| test | 48457 | 0.646171 | 0.263264 | 0.083469 | 4037.150000 | 1.152036 | 766.960000 |

### Previous Baltasar v2 baseline

| split | trades_taken | coverage | trade_precision | avg_r | total_r | profit_factor | max_drawdown_r |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | 32611 | 0.549210 | 0.209653 | -0.023658 | -771.480000 | 0.957802 | 1557.860000 |
| test | 43905 | 0.585470 | 0.262271 | 0.003646 | 159.980000 | 1.006110 | 1278.180000 |

## Feature Importance

| feature | importance | method |
| --- | --- | --- |
| hour | 0.093402 | permutation_f1_macro |
| weekday | 0.016436 | permutation_f1_macro |
| spread_pips | 0.002984 | permutation_f1_macro |
| session | 0.001473 | permutation_f1_macro |
| regime | -0.000811 | permutation_f1_macro |
| daily_range_position | -0.005561 | permutation_f1_macro |
| atr | -0.009638 | permutation_f1_macro |

## Leakage Check

- Passed: `True`
- Forbidden features in model: `[]`

## Technical Notes

- Only session/hour/weekday/spread_pips/atr/daily_range_position/regime are used as features.
- No mage votes, Baltasar v1 signal, first-touch diagnostics, R values, labels, or future outcomes are used as features.
- buy_R and sell_R are used only for evaluation.
- HistGradientBoostingClassifier receives balanced sample weights.
- The saved model is selected by validation threshold avg_r, then PF, then trade precision.
