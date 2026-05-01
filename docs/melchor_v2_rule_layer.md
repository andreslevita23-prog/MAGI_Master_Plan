# Melchor v2 Rule-Aware Risk Layer

## Scope

- No model is trained.
- Rules use accumulated operational risk available before each trade.
- Objective: compare explicit risk blocking against the Melchor v2 ML baseline.

## Thresholds

| Threshold | Value |
| --- | ---: |
| `rolling_drawdown_50_high` | 13.0000 |
| `rolling_drawdown_100_high` | 18.0000 |
| `rolling_unfavorable_rate_50_high` | 0.4600 |
| `rolling_unfavorable_rate_100_high` | 0.4300 |
| `recent_loss_streak_high` | 6.0000 |
| `recent_sell_loss_streak_high` | 7.0000 |

## Validation/Test Summary

| Split | Rule | Mode | Blocked | Avg R | PF | DD | Avg R delta | PF delta | DD delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | `combined_risk_rule` | BLOCK+CAUTION | 13,942 | 0.5628 | 2.3725 | 35.12 | 0.4697 | 1.2104 | 231.02 |
| test | `combined_risk_rule` | BLOCK | 11,301 | 0.5386 | 2.2919 | 41.16 | 0.4454 | 1.1299 | 224.98 |
| test | `q2_like_proxy` | BLOCK+CAUTION | 11,147 | 0.3727 | 1.7765 | 52.27 | 0.2796 | 0.6144 | 213.87 |
| test | `rolling_pf_below_1_and_drawdown_high` | BLOCK+CAUTION | 10,806 | 0.3306 | 1.6668 | 55.94 | 0.2374 | 0.5048 | 210.20 |
| test | `rolling_pf_below_1_and_drawdown_high` | BLOCK | 8,716 | 0.3220 | 1.6476 | 68.85 | 0.2288 | 0.4855 | 197.29 |
| test | `q2_like_proxy` | BLOCK | 8,702 | 0.3207 | 1.6444 | 68.85 | 0.2275 | 0.4824 | 197.29 |
| test | `rolling_sell_pf_below_1` | BLOCK+CAUTION | 7,023 | 0.2153 | 1.4029 | 204.86 | 0.1221 | 0.2409 | 61.28 |
| test | `rolling_sell_pf_below_1` | BLOCK | 5,759 | 0.2088 | 1.3893 | 199.59 | 0.1156 | 0.2273 | 66.55 |
| test | `rolling_sell_pf_below_1` | CAUTION | 1,264 | 0.0899 | 1.1560 | 243.79 | -0.0033 | -0.0061 | 22.35 |
| test | `q2_like_proxy` | CAUTION | 2,445 | 0.0876 | 1.1519 | 266.74 | -0.0055 | -0.0101 | -0.60 |
| test | `rolling_pf_below_1_and_drawdown_high` | CAUTION | 2,090 | 0.0708 | 1.1214 | 299.05 | -0.0224 | -0.0407 | -32.91 |
| test | `combined_risk_rule` | CAUTION | 2,641 | 0.0337 | 1.0565 | 445.69 | -0.0595 | -0.1056 | -179.55 |
| validation | `combined_risk_rule` | BLOCK+CAUTION | 7,801 | 0.5555 | 2.5885 | 30.48 | 0.4999 | 1.4874 | 317.70 |
| validation | `combined_risk_rule` | BLOCK | 6,503 | 0.5186 | 2.4320 | 33.37 | 0.4630 | 1.3309 | 314.81 |
| validation | `q2_like_proxy` | BLOCK+CAUTION | 6,668 | 0.3707 | 1.8762 | 58.52 | 0.3151 | 0.7751 | 289.66 |
| validation | `rolling_pf_below_1_and_drawdown_high` | BLOCK+CAUTION | 6,524 | 0.3365 | 1.7699 | 58.52 | 0.2809 | 0.6688 | 289.66 |

## 2026Q2 Impact

| Split | Rule | Mode | Blocked | Avg R | PF | DD | Avg R delta | PF delta | DD delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026Q2 | `combined_risk_rule` | BLOCK+CAUTION | 340 | 0.6016 | 2.9975 | 13.71 | 0.6588 | 2.0972 | 79.95 |
| 2026Q2 | `combined_risk_rule` | BLOCK | 298 | 0.5014 | 2.4620 | 23.02 | 0.5586 | 1.5617 | 70.64 |
| 2026Q2 | `rolling_pf_below_1_and_drawdown_high` | BLOCK | 279 | 0.3771 | 1.9531 | 34.00 | 0.4343 | 1.0528 | 59.66 |
| 2026Q2 | `q2_like_proxy` | BLOCK | 279 | 0.3771 | 1.9531 | 34.00 | 0.4343 | 1.0528 | 59.66 |
| 2026Q2 | `rolling_sell_pf_below_1` | BLOCK | 277 | 0.3656 | 1.9214 | 34.00 | 0.4228 | 1.0210 | 59.66 |
| 2026Q2 | `rolling_pf_below_1_and_drawdown_high` | BLOCK+CAUTION | 303 | 0.2563 | 1.5644 | 34.00 | 0.3135 | 0.6641 | 59.66 |
| 2026Q2 | `q2_like_proxy` | BLOCK+CAUTION | 303 | 0.2563 | 1.5644 | 34.00 | 0.3135 | 0.6641 | 59.66 |
| 2026Q2 | `rolling_sell_pf_below_1` | BLOCK+CAUTION | 301 | 0.2473 | 1.5438 | 34.00 | 0.3045 | 0.6435 | 59.66 |
| 2026Q2 | `combined_risk_rule` | CAUTION | 42 | -0.0849 | 0.8549 | 80.41 | -0.0277 | -0.0454 | 13.25 |
| 2026Q2 | `rolling_sell_pf_below_1` | CAUTION | 24 | -0.1235 | 0.7957 | 97.13 | -0.0663 | -0.1046 | -3.47 |
| 2026Q2 | `rolling_pf_below_1_and_drawdown_high` | CAUTION | 24 | -0.1245 | 0.7941 | 97.56 | -0.0673 | -0.1062 | -3.90 |
| 2026Q2 | `q2_like_proxy` | CAUTION | 24 | -0.1245 | 0.7941 | 97.56 | -0.0673 | -0.1062 | -3.90 |

## Best Results

| Split | Rule | Mode | Blocked | Avg R | PF | DD | Avg R delta | PF delta | DD delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | `combined_risk_rule` | BLOCK+CAUTION | 7,801 | 0.5555 | 2.5885 | 30.48 | 0.4999 | 1.4874 | 317.70 |
| test | `combined_risk_rule` | BLOCK+CAUTION | 13,942 | 0.5628 | 2.3725 | 35.12 | 0.4697 | 1.2104 | 231.02 |
| q2_2026 | `combined_risk_rule` | BLOCK+CAUTION | 340 | 0.6016 | 2.9975 | 13.71 | 0.6588 | 2.0972 | 79.95 |

## Comparison Against ML Baseline

| Split | ML mode | Blocked | Avg R | PF | DD |
| --- | --- | ---: | ---: | ---: | ---: |
| validation | block_only | 1,298 | 0.0425 | 1.0770 | 335.22 |
| validation | block_plus_caution | 1,446 | 0.0510 | 1.0929 | 335.22 |
| test | block_only | 1,435 | 0.1018 | 1.1784 | 244.14 |
| test | block_plus_caution | 1,611 | 0.1066 | 1.1874 | 244.14 |

## Interpretation

Best test rule is `combined_risk_rule` in `BLOCK+CAUTION` mode. It changes test avg R by `0.4697`, PF by `1.2104` and DD by `231.02`. For 2026Q2, best rule is `combined_risk_rule` in `BLOCK+CAUTION` mode, changing avg R by `0.6588` and PF by `2.0972`. Treat this as a risk-control comparison, not proof of production profitability.
