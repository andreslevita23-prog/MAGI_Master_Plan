# Gaspar v2 Context Classifier Full

## Scope

- Gaspar v2 classifies context quality: `FAVORABLE`, `UNFAVORABLE`, `NEUTRAL`.
- Gaspar does not predict direction.
- R, selected_at_050, policy decisions, direct time fields, labels and future/result columns are excluded from features.

## Model

- Model: `HistGradientBoostingClassifier`
- Train rows: `69,484`
- Validation rows: `11,425`
- Test rows: `19,967`
- Feature columns: `68`

## Classification Metrics

| Split | Accuracy | Macro F1 | P(UNFAVORABLE) | R(UNFAVORABLE) | P(FAVORABLE) | R(FAVORABLE) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 0.4625 | 0.3475 | 0.6152 | 0.3632 | 0.4146 | 0.6338 |
| test | 0.4415 | 0.3232 | 0.5883 | 0.3576 | 0.3916 | 0.5825 |

## Gaspar Filter Simulation

| Split | Block threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | Max DD original | Max DD filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 0.50 | 1,711 | 9,714 | 0.0556 | 0.0646 | 1.1011 | 1.1203 | 348.18 | 294.94 |
| validation | 0.60 | 340 | 11,085 | 0.0556 | 0.0508 | 1.1011 | 1.0925 | 348.18 | 330.51 |
| validation | 0.70 | 8 | 11,417 | 0.0556 | 0.0550 | 1.1011 | 1.1000 | 348.18 | 348.18 |
| test | 0.50 | 3,007 | 16,960 | 0.0932 | 0.0879 | 1.1621 | 1.1537 | 266.14 | 251.91 |
| test | 0.60 | 662 | 19,305 | 0.0932 | 0.0897 | 1.1621 | 1.1562 | 266.14 | 263.14 |
| test | 0.70 | 7 | 19,960 | 0.0932 | 0.0930 | 1.1621 | 1.1617 | 266.14 | 266.14 |

## 2026Q2 Impact

| Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | Max DD original | Max DD filtered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.50 | 56 | 403 | -0.0572 | -0.0879 | 0.9003 | 0.8481 | 93.66 | 95.66 |
| 0.60 | 3 | 456 | -0.0572 | -0.0541 | 0.9003 | 0.9056 | 93.66 | 93.66 |
| 0.70 | 0 | 459 | -0.0572 | -0.0572 | 0.9003 | 0.9003 | 93.66 | 93.66 |

## Top Feature Importance

| feature | importance_mean | importance_std |
| --- | ---: | ---: |
| `m15_recent_range` | 0.011709 | 0.004177 |
| `h4_ema_200` | 0.009535 | 0.002609 |
| `h4_recent_range` | 0.008551 | 0.004437 |
| `rsi_14` | 0.006500 | 0.002359 |
| `resistance_distance_pips` | 0.005150 | 0.002454 |
| `d1_rsi_14` | 0.003702 | 0.002054 |
| `close_to_ema200` | 0.003659 | 0.001845 |
| `upper_wick_pct` | 0.002962 | 0.001217 |
| `returns_3` | 0.002820 | 0.000607 |
| `close_to_ema20` | 0.002367 | 0.002134 |
| `returns_1` | 0.002330 | 0.001382 |
| `ema_50_200_distance` | 0.002056 | 0.004225 |
| `h4_market_structure` | 0.001907 | 0.000644 |
| `spread_pips` | 0.001705 | 0.001252 |
| `m15_market_structure` | 0.001580 | 0.001250 |
| `recent_range` | 0.001462 | 0.002620 |
| `ema_20_50_distance` | 0.001457 | 0.003395 |
| `structure_direction` | 0.001344 | 0.000186 |
| `returns_6` | 0.001191 | 0.003331 |
| `daily_range_position` | 0.000959 | 0.001482 |

## Interpretation

On test, Gaspar reaches macro F1 `0.3232` and UNFAVORABLE recall `0.3576`. The best test filter by avg R/PF is threshold `0.70`, which does not improve Baltasar v2 from avg R `0.0932` / PF `1.1621` to avg R `0.0930` / PF `1.1617`.
