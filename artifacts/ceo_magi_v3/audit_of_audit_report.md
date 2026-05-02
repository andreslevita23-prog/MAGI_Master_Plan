# Audit of 3-Month CEO-MAGI v3 Audit

## Executive Answer

- Numbers correct: `yes`
- Critical mismatches found: `0`
- Warnings found: `0`
- Inflation detected: `no`
- Bias verdict: `selected months are not extreme, but still only a small sample`
- Reliability: `arithmetically reliable for describing these 3 months only`

## Selected Months

- `2020-12`, `2022-01`, `2025-10`
- Non-continuous: `yes`

## Consistency Validation

No consistency, formula, duplicate, missing-trade, pips, or duration errors were found.

## Recalculated Monthly Metrics

| Month | Ops | Wins | Losses | Win rate | Gross win pips | Gross loss pips | Net pips | Avg duration min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2020-12` | 20 | 13 | 7 | 65.00% | 253.0 | -65.6 | 129.7 | 110.8 |
| `2022-01` | 37 | 30 | 7 | 81.08% | 553.3 | -60.0 | 373.3 | 130.3 |
| `2025-10` | 22 | 17 | 5 | 77.27% | 282.0 | -35.7 | 187.3 | 135.9 |

## Summary Comparison

| Month | Ops diff | Win rate diff | Net pips diff | Avg duration diff |
| --- | ---: | ---: | ---: | ---: |
| `2020-12` | 0.0000 | 0.000000 | 0.000000 | 0.000000 |
| `2022-01` | 0.0000 | 0.000000 | 0.000000 | 0.000000 |
| `2025-10` | 0.0000 | 0.000000 | 0.000000 | 0.000000 |

## Bias Validation

| Group | Ops | Win rate | Net pips | Avg duration min |
| --- | ---: | ---: | ---: | ---: |
| Selected 3 months | 79 | 75.95% | 690.3 | 126.9 |
| Rest of dataset | 3267 | 72.85% | 27349.7 | 92.6 |
| Full dataset | 3346 | 72.92% | 28040.0 | 93.4 |

| Selected mean percentile vs all monthly distribution | Percentile |
| --- | ---: |
| `net_pips_month` | 42.11% |
| `win_rate` | 56.58% |
| `trades_executed` | 38.16% |
| `avg_duration_minutes` | 63.16% |

## Interpretation

The monthly arithmetic is internally consistent: counts, win rate, pips, and duration recompute back to the published summary. The selected months have a higher aggregate win rate than the rest of the dataset (75.95% vs 72.85%). The selected average monthly net pips sits around the 42% percentile of all CEO-MAGI v3 ENTER months.

## Potential Errors

- `exit_price` is unavailable in the source files, so this audit cannot validate exit price geometry.
- Pips are pip-equivalent values derived from R with fixed `SL=10 pips`; they are not broker-reported pip PnL.
- The selected months are random and non-continuous, but they are not a statistically complete walk-forward sample.

## Generated Files

- `artifacts\ceo_magi_v3\audit_of_audit_report.md`
- `artifacts\ceo_magi_v3\audit_of_audit_differences.csv`
