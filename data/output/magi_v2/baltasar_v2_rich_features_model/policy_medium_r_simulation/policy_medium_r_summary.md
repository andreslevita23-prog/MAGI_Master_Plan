# Baltasar v2 rich_policy_medium - final R simulation

## Scope

- Uses first-touch RR 1:2 labels.
- Evaluates only the existing `rich_policy_medium` policy.
- No retraining, no new rules, no mage logic changes.

## Threshold comparison

| Threshold | Trades | Coverage | Avg R | Total R | PF | Max DD | Win rate | Trade precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 040 | 31,392 | 23.36% | 0.0795 | 2495.43 | 1.1405 | 348.18 | 40.24% | 27.51% |
| 050 | 4,907 | 3.65% | 0.1893 | 929.04 | 1.3496 | 134.09 | 43.14% | 32.63% |

## BUY vs SELL

| Threshold | Direction | Trades | Avg R | PF | Max DD | Win rate | Precision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 040 | BUY | 14,293 | 0.1166 | 1.2122 | 237.59 | 42.06% | 27.92% |
| 040 | SELL | 17,099 | 0.0485 | 1.0837 | 737.10 | 38.71% | 27.17% |
| 050 | BUY | 2,033 | 0.2488 | 1.4863 | 84.87 | 46.09% | 33.01% |
| 050 | SELL | 2,874 | 0.1472 | 1.2616 | 186.15 | 41.06% | 32.36% |

## Baltasar v1 comparison

| Split | Trades | Coverage | Avg R | Total R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 26,701 | 44.97% | 0.0064 | 170.08 | 1.0124 | 878.24 |
| test | 48,457 | 64.62% | 0.0833 | 4037.15 | 1.1520 | 766.96 |

## 2026Q2 diagnostic

| Threshold | Trades | Coverage | Avg R | Total R | PF | Max DD | Win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 040 | 459 | 20.01% | -0.0572 | -26.26 | 0.9003 | 93.66 | 34.20% |
| 050 | 113 | 4.93% | -0.2011 | -22.72 | 0.6888 | 53.89 | 30.09% |

## Technical decision

- `0.40` is the principal threshold because it keeps a much larger sample and remains EV positive.
- `0.50` is a defensive threshold with higher avg R/PF and lower drawdown, but much lower coverage.
- SELL remains weaker than BUY and should be diagnosed before promoting Baltasar v2.
- 2026Q2 remains a regime warning and should be analyzed before starting production-style integration.
