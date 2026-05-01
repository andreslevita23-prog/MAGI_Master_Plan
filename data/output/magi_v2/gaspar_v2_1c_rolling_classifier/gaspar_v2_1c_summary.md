# Gaspar v2.1c Rolling Classifier

## Scope

- Target: `regime_deteriorating_rr2`.
- Secondary diagnostic target: `sell_risk_next_window`.
- Gaspar detects regime deterioration; it does not predict direction.

## Model

- Model: `HistGradientBoostingClassifier`
- Train rows: `69,484`
- Validation rows: `11,425`
- Test rows: `19,967`
- Feature columns: `50`

## Classification Metrics

| Split | Accuracy | Macro F1 | P(DETERIORATING) | R(DETERIORATING) | P(STABLE) | R(STABLE) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 0.5399 | 0.2644 | 0.6173 | 0.0559 | 0.5364 | 0.9693 |
| test | 0.5424 | 0.2678 | 0.4148 | 0.0644 | 0.5519 | 0.9271 |

## Filter Simulation

| Split | Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 0.50 | 486 | 10,939 | 0.0556 | 0.0728 | 1.1011 | 1.1337 | 348.18 | 332.30 |
| validation | 0.60 | 147 | 11,278 | 0.0556 | 0.0613 | 1.1011 | 1.1118 | 348.18 | 343.18 |
| validation | 0.70 | 19 | 11,406 | 0.0556 | 0.0569 | 1.1011 | 1.1035 | 348.18 | 347.18 |
| test | 0.50 | 1,379 | 18,588 | 0.0932 | 0.1152 | 1.1621 | 1.2033 | 266.14 | 240.14 |
| test | 0.60 | 663 | 19,304 | 0.0932 | 0.1034 | 1.1621 | 1.1811 | 266.14 | 247.14 |
| test | 0.70 | 226 | 19,741 | 0.0932 | 0.0953 | 1.1621 | 1.1660 | 266.14 | 257.14 |

## 2026Q2 Impact

| Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.50 | 0 | 459 | -0.0572 | -0.0572 | 0.9003 | 0.9003 | 93.66 | 93.66 |
| 0.60 | 0 | 459 | -0.0572 | -0.0572 | 0.9003 | 0.9003 | 93.66 | 93.66 |
| 0.70 | 0 | 459 | -0.0572 | -0.0572 | 0.9003 | 0.9003 | 93.66 | 93.66 |

## Top Feature Importance

| Feature | Importance mean | Importance std |
| --- | ---: | ---: |
| `rolling_unfavorable_rate_100` | 0.022542 | 0.001023 |
| `rolling_drawdown_100` | 0.021021 | 0.002668 |
| `rolling_drawdown_50` | 0.020430 | 0.002115 |
| `rolling_buy_avg_R_50` | 0.016612 | 0.002015 |
| `rolling_avg_R_100` | 0.016179 | 0.001391 |
| `recent_loss_streak` | 0.011876 | 0.001762 |
| `atr` | 0.011243 | 0.003808 |
| `rolling_pf_50` | 0.010592 | 0.002142 |
| `rolling_buy_win_rate_50` | 0.008480 | 0.002369 |
| `rolling_buy_avg_R_100` | 0.007744 | 0.001354 |
| `rolling_avg_R_50` | 0.006964 | 0.000545 |
| `rolling_unfavorable_rate_50` | 0.005992 | 0.000613 |
| `rolling_buy_avg_R_20` | 0.004281 | 0.000942 |
| `rolling_sell_pf_100` | 0.003846 | 0.001068 |
| `recent_sell_loss_streak` | 0.003553 | 0.001624 |
| `rolling_buy_win_rate_100` | 0.003164 | 0.000993 |
| `rolling_buy_pf_50` | 0.002555 | 0.000582 |
| `rolling_sell_pf_50` | 0.001945 | 0.001141 |
| `rolling_sell_win_rate_100` | 0.001847 | 0.001018 |
| `rolling_sell_avg_R_20` | 0.001693 | 0.000577 |

## Interpretation

On test, macro F1 is `0.2678` and DETERIORATING recall is `0.0644`. Best threshold by filtered avg R/PF is `0.50`, which improves Baltasar from avg R `0.0932` / PF `1.1621` to avg R `0.1152` / PF `1.2033`.
