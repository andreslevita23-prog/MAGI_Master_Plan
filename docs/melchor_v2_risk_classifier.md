# Melchor v2 Risk Classifier

## Scope

- Target: `risk_block_rr2`.
- Diagnostic target: `risk_block_rr2_strict`.
- Melchor v2 evaluates accumulated risk before a candidate trade; it does not predict direction.

## Model

- Model: `HistGradientBoostingClassifier`
- Train rows: `69,484`
- Validation rows: `11,425`
- Test rows: `19,967`
- Feature columns: `23`

## Classification Metrics

| Split | Accuracy | Macro F1 | P(BLOCK) | R(BLOCK) | P(APPROVE) | R(APPROVE) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 0.3309 | 0.2082 | 0.6579 | 0.1094 | 0.2933 | 0.8558 |
| test | 0.3964 | 0.2232 | 0.5408 | 0.0672 | 0.3888 | 0.9107 |

## Operational Filter

| Split | Mode | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | block_only | 1,298 | 10,127 | 0.0556 | 0.0425 | 1.1011 | 1.0770 | 348.18 | 335.22 |
| validation | block_plus_caution | 1,446 | 9,979 | 0.0556 | 0.0510 | 1.1011 | 1.0929 | 348.18 | 335.22 |
| test | block_only | 1,435 | 18,532 | 0.0932 | 0.1018 | 1.1621 | 1.1784 | 266.14 | 244.14 |
| test | block_plus_caution | 1,611 | 18,356 | 0.0932 | 0.1066 | 1.1621 | 1.1874 | 266.14 | 244.14 |

## 2026Q2 Impact

| Mode | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| block_only | 1 | 458 | -0.0572 | -0.0617 | 0.9003 | 0.8927 | 93.66 | 93.66 |
| block_plus_caution | 2 | 457 | -0.0572 | -0.0662 | 0.9003 | 0.8851 | 93.66 | 93.66 |

## Top Feature Importance

| Feature | Importance mean | Importance std |
| --- | ---: | ---: |
| `rolling_avg_R_100` | 0.006977 | 0.000956 |
| `rolling_avg_R_50` | 0.005583 | 0.003030 |
| `rolling_sell_avg_R_50` | 0.005343 | 0.001491 |
| `rolling_drawdown_50` | 0.004443 | 0.003473 |
| `rolling_unfavorable_rate_50` | 0.002780 | 0.000533 |
| `rolling_drawdown_100` | 0.002248 | 0.001224 |
| `rolling_win_rate_50` | 0.001733 | 0.001640 |
| `predicted_direction` | 0.001439 | 0.001043 |
| `rolling_pf_100` | 0.001011 | 0.000560 |
| `recent_sell_loss_streak` | 0.000999 | 0.001916 |
| `recent_loss_streak` | 0.000397 | 0.001084 |
| `daily_range_position` | -0.000104 | 0.003990 |
| `rolling_win_rate_100` | -0.000171 | 0.000692 |
| `rolling_sell_avg_R_20` | -0.000638 | 0.000903 |
| `rolling_pf_50` | -0.002269 | 0.000868 |
| `rolling_avg_R_20` | -0.002760 | 0.002442 |
| `rolling_sell_pf_50` | -0.002889 | 0.001497 |
| `rolling_sell_pf_20` | -0.002926 | 0.000878 |
| `rolling_pf_20` | -0.002994 | 0.002552 |
| `rolling_sell_avg_R_100` | -0.003886 | 0.001664 |

## Interpretation

On test, macro F1 is `0.2232`, BLOCK precision is `0.5408` and BLOCK recall is `0.0672`. Best operational mode by avg R/PF is `block_plus_caution`, moving from avg R `0.0932` / PF `1.1621` / DD `266.14` to avg R `0.1066` / PF `1.1874` / DD `244.14`.
