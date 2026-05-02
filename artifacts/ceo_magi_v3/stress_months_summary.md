# CEO-MAGI v3 Stress Months Audit

## Scope

- Months: `2020-03`, `2022-04`, `2026-04`.
- Universe: only CEO-MAGI v3 approved `ENTER` operations for primary metrics.
- Baseline comparison: all candidate decisions in the same month using `hypothetical_adjusted_R` before CEO filtering.
- No models, rules, Bot B, or MT5 were modified.

## Global Reference

- Global CEO ENTER PF: `3.5930`
- Global CEO ENTER Avg R: `0.8380`
- Global CEO ENTER Max DD: `7.52R`
- Global CEO ENTER win rate: `72.92%`

## Stress Month Summary

| Month | Stress | Ops | Wins | Losses | WR | Gross +pips | Gross -pips | Net pips | Avg R | PF | Max DD | Avg dur | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `2020-03` | pandemia pico | 181 | 116 | 65 | 64.09% | 2292.7 | -650.0 | 1104.6 | 0.6103 | 2.3093 | 7.52 | 27m | `degrades_but_survives` |
| `2022-04` | inflacion alta | 94 | 66 | 28 | 70.21% | 1253.6 | -279.1 | 672.3 | 0.7153 | 2.8245 | 7.48 | 1h 20m | `survives` |
| `2026-04` | periodo problematico reciente | 3 | 1 | 2 | 33.33% | 20.0 | -20.0 | -9.7 | -0.3218 | 0.6311 | 1.30 | 2h 15m | `stress_failure` |

## Baseline Comparison

| Month | CEO Total R | Baseline Total R | Delta R | CEO PF | Baseline PF | CEO DD | Baseline DD | Better than baseline? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2020-03` | 110.46 | 77.58 | 32.88 | 2.3093 | 1.3221 | 7.52 | 11.13 | `yes` |
| `2022-04` | 67.23 | 61.87 | 5.37 | 2.8245 | 1.8198 | 7.48 | 6.32 | `mixed/no` |
| `2026-04` | -0.97 | -1.01 | 0.05 | 0.6311 | 0.8607 | 1.30 | 3.08 | `yes` |

## Direction Breakdown

### 2020-03 - pandemia pico

| Direction | Ops | WR | Avg R | PF | Total R | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BUY` | 64 | 62.50% | 0.5588 | 2.1531 | 35.76 | 7.66 |
| `SELL` | 117 | 64.96% | 0.6384 | 2.4001 | 74.69 | 6.49 |

### 2022-04 - inflacion alta

| Direction | Ops | WR | Avg R | PF | Total R | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BUY` | 37 | 67.57% | 0.6570 | 2.5567 | 24.31 | 3.92 |
| `SELL` | 57 | 71.93% | 0.7531 | 3.0215 | 42.92 | 4.88 |

### 2026-04 - periodo problematico reciente

| Direction | Ops | WR | Avg R | PF | Total R | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BUY` | 0 | 0.00% | 0.0000 | 0.0000 | 0.00 | 0.00 |
| `SELL` | 3 | 33.33% | -0.3218 | 0.6311 | -0.97 | 1.30 |

## Gate Diagnostics

| Month | Candidates | ENTER | DO_NOTHING | Melchor blocks | Score blocks | Blocked hypothetical R | Gaspar high det. | Avg Gaspar ENTER | Avg Gaspar blocked |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2020-03` | 376 | 181 | 195 | 85 | 110 | -32.88 | 0 | 0.2104 | 0.2874 |
| `2022-04` | 145 | 94 | 51 | 13 | 38 | -5.37 | 0 | 0.2157 | 0.2628 |
| `2026-04` | 11 | 3 | 8 | 3 | 5 | -0.05 | 0 | 0.1703 | 0.1093 |

## Interpretation

- `2020-03`: survives; does not lose money; DD `7.52R`. Compared with baseline: PF improves, DD improves. Max loss streak `5`.
- `2022-04`: survives; does not lose money; DD `7.48R`. Compared with baseline: PF improves, DD does not improve. Max loss streak `4`.
- `2026-04`: does not survive cleanly; loses money; DD `1.30R`. Compared with baseline: PF does not improve, DD improves. Max loss streak `1`.

## Module Readout

Scoring is the most active gate in these stress months (`153` score blocks), while Melchor blocks `101` trades. The blocked trades had combined hypothetical R `-38.29`, so the gates were not merely cosmetic. Gaspar did not trigger the high-deterioration downgrade (`0` cases >= 0.70), but it still contributes inside the score penalty.

## Limitations

- `exit_price` is not available in the CEO-MAGI v3 artifacts, so exit price geometry is not audited here.
- Pips are pip-equivalent values using the validated fixed `SL=10` pips convention.
- 2026-04 has very few approved entries, so its metrics are directionally useful but statistically weak.

## Generated Files

- `artifacts\ceo_magi_v3\stress_months_audit.csv`
- `artifacts\ceo_magi_v3\stress_months_trade_detail.csv`
- `artifacts\ceo_magi_v3\stress_months_summary.md`
