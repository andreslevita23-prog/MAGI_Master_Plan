# Baltasar v2 Rich Policy Layer

## Scope

- Model: `baltasar_v2_rich_model.joblib`.
- No retraining was performed.
- Policies only block trades by converting predictions to `DO_NOTHING`.
- Month/quarter blocking is diagnostic only.

## Variant Results

| variant | threshold | split | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_policy | 0.40 | validation | 20564 | 0.346324 | 0.239739 | 0.014781 | 303.960000 | 1.025651 | 566.890000 | 0.232300 | 0.250294 |
| no_policy | 0.40 | test | 35242 | 0.469950 | 0.297855 | 0.057629 | 2030.950000 | 1.096255 | 513.930000 | 0.319789 | 0.286051 |
| rich_policy_light | 0.40 | validation | 17733 | 0.298646 | 0.244178 | 0.037347 | 662.270000 | 1.065807 | 506.820000 | 0.241703 | 0.247634 |
| rich_policy_light | 0.40 | test | 27832 | 0.371138 | 0.295990 | 0.062575 | 1741.580000 | 1.105337 | 301.690000 | 0.311124 | 0.287389 |
| rich_policy_medium | 0.40 | validation | 11425 | 0.192411 | 0.239387 | 0.055587 | 635.080000 | 1.101081 | 348.180000 | 0.244259 | 0.232465 |
| rich_policy_medium | 0.40 | test | 19967 | 0.266259 | 0.295488 | 0.093171 | 1860.350000 | 1.162071 | 266.140000 | 0.310004 | 0.286591 |
| rich_policy_strict | 0.40 | validation | 5411 | 0.091128 | 0.214193 | 0.010283 | 55.640000 | 1.018491 | 241.800000 | 0.208358 | 0.223859 |
| rich_policy_strict | 0.40 | test | 11124 | 0.148338 | 0.294319 | 0.124210 | 1381.710000 | 1.223173 | 219.070000 | 0.310487 | 0.282935 |
| no_policy | 0.50 | validation | 3660 | 0.061639 | 0.285792 | 0.105413 | 385.810000 | 1.187423 | 193.230000 | 0.264109 | 0.321121 |
| no_policy | 0.50 | test | 6765 | 0.090211 | 0.320769 | 0.082132 | 555.620000 | 1.136375 | 292.510000 | 0.368388 | 0.306390 |
| rich_policy_light | 0.50 | validation | 3052 | 0.051400 | 0.289974 | 0.135524 | 413.620000 | 1.247187 | 159.950000 | 0.269311 | 0.324824 |
| rich_policy_light | 0.50 | test | 4562 | 0.060834 | 0.334064 | 0.127260 | 580.560000 | 1.217275 | 244.240000 | 0.349103 | 0.328537 |
| rich_policy_medium | 0.50 | validation | 1912 | 0.032200 | 0.308577 | 0.230429 | 440.580000 | 1.454835 | 75.210000 | 0.291107 | 0.337500 |
| rich_policy_medium | 0.50 | test | 2995 | 0.039938 | 0.337563 | 0.163092 | 488.460000 | 1.289190 | 134.090000 | 0.385256 | 0.318942 |
| rich_policy_strict | 0.50 | validation | 682 | 0.011486 | 0.262463 | 0.101261 | 69.060000 | 1.183651 | 57.300000 | 0.256696 | 0.273504 |
| rich_policy_strict | 0.50 | test | 1340 | 0.017869 | 0.358209 | 0.252873 | 338.850000 | 1.475853 | 59.380000 | 0.488038 | 0.299349 |

## Yearly Stability

| variant | threshold | period | trades | avg_r | total_r | PF | max_DD | low_sample |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_policy | 0.40 | 2024 | 20564 | 0.014781 | 303.960000 | 1.025651 | 566.890000 | False |
| no_policy | 0.40 | 2025 | 28153 | 0.064966 | 1829.000000 | 1.108597 | 473.620000 | False |
| no_policy | 0.40 | 2026 | 7089 | 0.028488 | 201.950000 | 1.047433 | 513.930000 | False |
| rich_policy_light | 0.40 | 2024 | 17733 | 0.037347 | 662.270000 | 1.065807 | 506.820000 | False |
| rich_policy_light | 0.40 | 2025 | 21778 | 0.064251 | 1399.260000 | 1.107747 | 301.690000 | False |
| rich_policy_light | 0.40 | 2026 | 6054 | 0.056544 | 342.320000 | 1.096514 | 236.120000 | False |
| rich_policy_medium | 0.40 | 2024 | 11425 | 0.055587 | 635.080000 | 1.101081 | 348.180000 | False |
| rich_policy_medium | 0.40 | 2025 | 15701 | 0.098233 | 1542.350000 | 1.170274 | 266.140000 | False |
| rich_policy_medium | 0.40 | 2026 | 4266 | 0.074543 | 318.000000 | 1.131373 | 145.870000 | False |
| rich_policy_strict | 0.40 | 2024 | 5411 | 0.010283 | 55.640000 | 1.018491 | 241.800000 | False |
| rich_policy_strict | 0.40 | 2025 | 8862 | 0.146421 | 1297.580000 | 1.266387 | 179.450000 | False |
| rich_policy_strict | 0.40 | 2026 | 2262 | 0.037193 | 84.130000 | 1.063727 | 167.660000 | False |
| no_policy | 0.50 | 2024 | 3660 | 0.105413 | 385.810000 | 1.187423 | 193.230000 | False |
| no_policy | 0.50 | 2025 | 5032 | 0.104271 | 524.690000 | 1.175655 | 292.510000 | False |
| no_policy | 0.50 | 2026 | 1733 | 0.017848 | 30.930000 | 1.028450 | 275.300000 | False |
| rich_policy_light | 0.50 | 2024 | 3052 | 0.135524 | 413.620000 | 1.247187 | 159.950000 | False |
| rich_policy_light | 0.50 | 2025 | 3357 | 0.118284 | 397.080000 | 1.200743 | 244.240000 | False |
| rich_policy_light | 0.50 | 2026 | 1205 | 0.152266 | 183.480000 | 1.264399 | 72.000000 | False |
| rich_policy_medium | 0.50 | 2024 | 1912 | 0.230429 | 440.580000 | 1.454835 | 75.210000 | False |
| rich_policy_medium | 0.50 | 2025 | 2116 | 0.155534 | 329.110000 | 1.274082 | 134.090000 | False |
| rich_policy_medium | 0.50 | 2026 | 879 | 0.181286 | 159.350000 | 1.326343 | 80.000000 | False |
| rich_policy_strict | 0.50 | 2024 | 682 | 0.101261 | 69.060000 | 1.183651 | 57.300000 | False |
| rich_policy_strict | 0.50 | 2025 | 926 | 0.295972 | 274.070000 | 1.572135 | 59.380000 | False |
| rich_policy_strict | 0.50 | 2026 | 414 | 0.156473 | 64.780000 | 1.277954 | 47.890000 | False |

## Quarterly Stability at Threshold 0.40

| variant | threshold | period | trades | avg_r | total_r | PF | max_DD | low_sample |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rich_policy_light | 0.40 | 2024Q1 | 4359 | 0.028986 | 126.350000 | 1.049882 | 378.280000 | False |
| rich_policy_light | 0.40 | 2024Q2 | 4231 | -0.014339 | -60.670000 | 0.974870 | 417.780000 | False |
| rich_policy_light | 0.40 | 2024Q3 | 3127 | 0.035241 | 110.200000 | 1.065921 | 416.280000 | False |
| rich_policy_light | 0.40 | 2024Q4 | 6016 | 0.080849 | 486.390000 | 1.141191 | 353.760000 | False |
| rich_policy_light | 0.40 | 2025Q1 | 5408 | 0.035595 | 192.500000 | 1.059722 | 270.510000 | False |
| rich_policy_light | 0.40 | 2025Q2 | 6064 | 0.049573 | 300.610000 | 1.078099 | 296.470000 | False |
| rich_policy_light | 0.40 | 2025Q3 | 5805 | 0.047006 | 272.870000 | 1.077424 | 301.690000 | False |
| rich_policy_light | 0.40 | 2025Q4 | 4501 | 0.140698 | 633.280000 | 1.264985 | 196.240000 | False |
| rich_policy_light | 0.40 | 2026Q1 | 5445 | 0.080299 | 437.230000 | 1.138154 | 213.700000 | False |
| rich_policy_light | 0.40 | 2026Q2 | 609 | -0.155846 | -94.910000 | 0.751577 | 143.730000 | False |
| rich_policy_medium | 0.40 | 2024Q1 | 2755 | 0.038399 | 105.790000 | 1.066518 | 295.840000 | False |
| rich_policy_medium | 0.40 | 2024Q2 | 2613 | 0.047382 | 123.810000 | 1.087932 | 270.640000 | False |
| rich_policy_medium | 0.40 | 2024Q3 | 1907 | 0.023608 | 45.020000 | 1.046021 | 290.640000 | False |
| rich_policy_medium | 0.40 | 2024Q4 | 4150 | 0.086858 | 360.460000 | 1.156300 | 283.610000 | False |
| rich_policy_medium | 0.40 | 2025Q1 | 4028 | 0.036316 | 146.280000 | 1.061881 | 197.690000 | False |
| rich_policy_medium | 0.40 | 2025Q2 | 4563 | 0.057480 | 262.280000 | 1.091450 | 266.140000 | False |
| rich_policy_medium | 0.40 | 2025Q3 | 4105 | 0.115469 | 474.000000 | 1.200980 | 255.740000 | False |
| rich_policy_medium | 0.40 | 2025Q4 | 3005 | 0.219564 | 659.790000 | 1.449543 | 101.570000 | False |
| rich_policy_medium | 0.40 | 2026Q1 | 3807 | 0.090428 | 344.260000 | 1.159589 | 145.870000 | False |
| rich_policy_medium | 0.40 | 2026Q2 | 459 | -0.057211 | -26.260000 | 0.900311 | 93.660000 | False |
| rich_policy_strict | 0.40 | 2024Q1 | 1197 | -0.113225 | -135.530000 | 0.818483 | 221.890000 | False |
| rich_policy_strict | 0.40 | 2024Q2 | 1163 | 0.120439 | 140.070000 | 1.245845 | 126.110000 | False |
| rich_policy_strict | 0.40 | 2024Q3 | 836 | -0.029510 | -24.670000 | 0.941941 | 183.260000 | False |
| rich_policy_strict | 0.40 | 2024Q4 | 2215 | 0.034208 | 75.770000 | 1.059765 | 211.870000 | False |
| rich_policy_strict | 0.40 | 2025Q1 | 2355 | 0.123083 | 289.860000 | 1.226499 | 179.450000 | False |
| rich_policy_strict | 0.40 | 2025Q2 | 2702 | 0.110252 | 297.900000 | 1.180303 | 136.660000 | False |
| rich_policy_strict | 0.40 | 2025Q3 | 2310 | 0.194905 | 450.230000 | 1.365405 | 118.520000 | False |
| rich_policy_strict | 0.40 | 2025Q4 | 1495 | 0.173639 | 259.590000 | 1.367202 | 68.670000 | False |
| rich_policy_strict | 0.40 | 2026Q1 | 1968 | 0.053928 | 106.130000 | 1.092566 | 167.660000 | False |
| rich_policy_strict | 0.40 | 2026Q2 | 294 | -0.074830 | -22.000000 | 0.873301 | 83.600000 | False |

## Comparisons

| model | split | threshold | trades | coverage | trade_precision | avg_r | total_r | profit_factor | max_drawdown_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rich_full_timing | validation | 0.40 | 20564 | 0.346324 | 0.239739 | 0.014781 | 303.960000 | 1.025651 | 566.890000 |
| rich_full_timing | validation | 0.50 | 3660 | 0.061639 | 0.285792 | 0.105413 | 385.810000 | 1.187423 | 193.230000 |
| rich_full_timing | test | 0.40 | 35242 | 0.469950 | 0.297855 | 0.057629 | 2030.950000 | 1.096255 | 513.930000 |
| rich_full_timing | test | 0.50 | 6765 | 0.090211 | 0.320769 | 0.082132 | 555.620000 | 1.136375 | 292.510000 |
| rich_no_timing | validation | 0.40 | 13300 | 0.223989 | 0.219098 | 0.001479 | 19.670000 | 1.002672 | 471.000000 |
| rich_no_timing | validation | 0.50 | 1554 | 0.026171 | 0.238095 | 0.002220 | 3.450000 | 1.003881 | 111.790000 |
| rich_no_timing | test | 0.40 | 27870 | 0.371645 | 0.265339 | 0.006342 | 176.710000 | 1.010628 | 726.370000 |
| rich_no_timing | test | 0.50 | 3358 | 0.044779 | 0.300476 | 0.065870 | 221.190000 | 1.112127 | 222.500000 |
| rich_coarse_timing | validation | 0.40 | 20043 | 0.337549 | 0.237190 | 0.003990 | 79.980000 | 1.006912 | 608.790000 |
| rich_coarse_timing | validation | 0.50 | 3116 | 0.052477 | 0.261553 | 0.025026 | 77.980000 | 1.043029 | 203.070000 |
| rich_coarse_timing | test | 0.40 | 37028 | 0.493766 | 0.276791 | 0.012952 | 479.580000 | 1.021343 | 679.750000 |
| rich_coarse_timing | test | 0.50 | 7486 | 0.099825 | 0.292680 | 0.034224 | 256.200000 | 1.056056 | 327.420000 |
| baltasar_v1_signal | validation | signal | 26701 | 0.449678 | 0.186173 | 0.006375 | 170.080000 | 1.012434 | 878.240000 |
| baltasar_v1_signal | test | signal | 48457 | 0.646171 | 0.263264 | 0.083469 | 4037.150000 | 1.152036 | 766.960000 |

## 2026Q2 Diagnostic

| variant | threshold | split | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_policy | 0.40 | 2026Q2 | 1160 | 0.505667 | 0.159483 | -0.318733 | -369.730000 | 0.548477 | 430.540000 | 0.666667 | 0.152838 |
| rich_policy_light | 0.40 | 2026Q2 | 609 | 0.265475 | 0.205255 | -0.155846 | -94.910000 | 0.751577 | 143.730000 | 0.000000 | 0.206954 |
| rich_policy_medium | 0.40 | 2026Q2 | 459 | 0.200087 | 0.226580 | -0.057211 | -26.260000 | 0.900311 | 93.660000 | 0.000000 | 0.227571 |
| rich_policy_strict | 0.40 | 2026Q2 | 294 | 0.128160 | 0.210884 | -0.074830 | -22.000000 | 0.873301 | 83.600000 | 0.000000 | 0.212329 |
| no_policy | 0.50 | 2026Q2 | 448 | 0.195292 | 0.129464 | -0.512299 | -229.510000 | 0.361248 | 268.860000 |  | 0.129464 |
| rich_policy_light | 0.50 | 2026Q2 | 128 | 0.055798 | 0.218750 | -0.177500 | -22.720000 | 0.726265 | 59.290000 |  | 0.218750 |
| rich_policy_medium | 0.50 | 2026Q2 | 113 | 0.049259 | 0.203540 | -0.201062 | -22.720000 | 0.688767 | 53.890000 |  | 0.203540 |
| rich_policy_strict | 0.50 | 2026Q2 | 63 | 0.027463 | 0.015873 | -0.701905 | -44.220000 | 0.118245 | 47.890000 |  | 0.015873 |

## Interpretation

On test at threshold 0.40, no_policy has avg R `0.057629` and PF `1.096255`. Light policy changes this to avg R `0.062575` and PF `1.105337`; medium to avg R `0.093171` and PF `1.162071`; strict to avg R `0.124210` and PF `1.223173`. Prefer the policy that improves drawdown and PF without collapsing coverage or failing validation.

## Technical Decisions

- No retraining is performed; policies only post-process existing rich_full_timing predictions.
- Blocked predictions are converted to DO_NOTHING.
- Month/quarter blocking is diagnostic only and is not part of any real policy.
- Diagnostic R columns are used only for evaluation.
- late_week is derived from textual weekday when available.
