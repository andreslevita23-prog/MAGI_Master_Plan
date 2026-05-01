# Melchor v2 Rule Stability

## Scope

- No model is trained.
- This validates coverage, frequency and temporal stability for candidate Melchor v2 rules.
- Compared rules: `q2_like_proxy` and `combined_risk_rule`, each in `BLOCK` and `BLOCK+CAUTION` modes.

## Overall Coverage

| Split | Rule | Mode | Retained | Coverage | Avg R | Total R | PF | DD | BUY retained | SELL retained |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | `combined_risk_rule` | BLOCK | 8,666 | 43.40% | 0.5386 | 4667.55 | 2.2919 | 41.16 | 3,675 | 4,991 |
| test | `combined_risk_rule` | BLOCK+CAUTION | 6,025 | 30.17% | 0.5628 | 3391.08 | 2.3725 | 35.12 | 2,405 | 3,620 |
| test | `q2_like_proxy` | BLOCK | 11,265 | 56.42% | 0.3207 | 3612.48 | 1.6444 | 68.85 | 4,290 | 6,975 |
| test | `q2_like_proxy` | BLOCK+CAUTION | 8,820 | 44.17% | 0.3727 | 3287.59 | 1.7765 | 52.27 | 3,374 | 5,446 |
| validation | `combined_risk_rule` | BLOCK | 4,922 | 43.08% | 0.5186 | 2552.47 | 2.4320 | 33.37 | 3,266 | 1,656 |
| validation | `combined_risk_rule` | BLOCK+CAUTION | 3,624 | 31.72% | 0.5555 | 2013.00 | 2.5885 | 30.48 | 2,468 | 1,156 |
| validation | `q2_like_proxy` | BLOCK | 6,218 | 54.42% | 0.2924 | 1818.31 | 1.6479 | 60.80 | 3,784 | 2,434 |
| validation | `q2_like_proxy` | BLOCK+CAUTION | 4,757 | 41.64% | 0.3707 | 1763.32 | 1.8762 | 58.52 | 3,065 | 1,692 |

## Temporal Stability

| Candidate | Months no trades | Months <50 | Median monthly trades | Negative months | Quarters no trades | Quarters <100 | Median quarterly trades | Negative quarters |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `q2_like_proxy__block_plus_caution` | 0 | 0 | 455.0 | 0 | 0 | 0 | 1522.5 | 0 |
| `combined_risk_rule__block_plus_caution` | 0 | 0 | 311.5 | 1 | 0 | 0 | 1036.5 | 0 |
| `q2_like_proxy__block` | 0 | 0 | 640.5 | 1 | 0 | 0 | 1984.0 | 0 |
| `combined_risk_rule__block` | 0 | 0 | 478.5 | 0 | 0 | 0 | 1577.0 | 0 |

## 2026Q2

| Candidate | Retained | Coverage | Avg R | PF | DD | Avg R delta | PF delta | DD delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `q2_like_proxy__block_plus_caution` | 156 | 33.99% | 0.2563 | 1.5644 | 34.00 | 0.3135 | 0.6641 | 59.66 |
| `combined_risk_rule__block_plus_caution` | 119 | 25.93% | 0.6016 | 2.9975 | 13.71 | 0.6588 | 2.0972 | 79.95 |
| `q2_like_proxy__block` | 180 | 39.22% | 0.3771 | 1.9531 | 34.00 | 0.4343 | 1.0528 | 59.66 |
| `combined_risk_rule__block` | 161 | 35.08% | 0.5014 | 2.4620 | 23.02 | 0.5586 | 1.5617 | 70.64 |

## Recommendation

Recommended initial candidate: `combined_risk_rule__block`. The aggressive benchmark is `combined_risk_rule__block_plus_caution`, but coverage must be treated as a first-class risk control. `combined_risk_rule` in `BLOCK+CAUTION` is marked aggressive: `True`.
