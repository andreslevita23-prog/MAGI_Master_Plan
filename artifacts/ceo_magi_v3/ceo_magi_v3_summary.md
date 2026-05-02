# CEO-MAGI v3 Offline Decision Summary

## Scope

- Policy: `CEO-MAGI v3`
- Source strategy: `A_base_scenario_c`
- Realized R column for metrics: `adjusted_R`
- Min operational score: `0.20`
- Gaspar high deterioration threshold: `0.70`

## Decision Counts

| Action | Count |
| --- | ---: |
| `ENTER` | 3346 |
| `DO_NOTHING` | 3193 |

## Aggression Modes

| Mode | Count |
| --- | ---: |
| `none` | 3193 |
| `premium` | 1514 |
| `cautious` | 941 |
| `normal` | 891 |

## Metrics

| Segment | Decisions | ENTER | DO_NOTHING | Coverage | PF | Avg R | Max DD | Total R | Win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` | 6539 | 3346 | 3193 | 51.17% | 3.5930 | 0.8380 | 7.52 | 2804.00 | 72.92% |
| `train` | 5177 | 2947 | 2230 | 56.92% | 3.6734 | 0.8622 | 7.52 | 2540.80 | 73.46% |
| `validation` | 483 | 153 | 330 | 31.68% | 3.8176 | 0.7262 | 5.25 | 111.10 | 71.24% |
| `test` | 879 | 246 | 633 | 27.99% | 2.6609 | 0.6183 | 6.84 | 152.10 | 67.48% |
| `2026Q2` | 11 | 3 | 8 | 27.27% | 0.6311 | -0.3218 | 1.30 | -0.97 | 33.33% |

## BUY vs SELL - Test ENTER Decisions

| Segment | Decisions | ENTER | DO_NOTHING | Coverage | PF | Avg R | Max DD | Total R | Win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `BUY` | 100 | 100 | 0 | 100.00% | 2.4044 | 0.5623 | 5.33 | 56.23 | 65.00% |
| `SELL` | 146 | 146 | 0 | 100.00% | 2.8602 | 0.6566 | 6.84 | 95.86 | 69.18% |

## Top Reason Codes

| Reason code | Count |
| --- | ---: |
| `score_below_0_20` | 2407 |
| `score_premium` | 1514 |
| `score_cautious` | 941 |
| `score_normal` | 891 |
| `melchor_block` | 786 |

## Operational Warnings

- Offline mode uses already generated/validated signals; it does not prove live connectivity or broker execution.
- Bot A and Bot B were not modified. JSONL is an execution contract candidate only.
- Metrics use `adjusted_R` when CEO-MAGI v3 returns ENTER; skipped trades keep hypothetical R only for audit.
- Trade plans use the existing RR2 convention with 10-pip SL to derive SL/TP when entry price is available.
- No Gaspar downgrades were observed in this source because `p_deteriorating` never reached 0.70.
- 2026Q2 remains a weak regime and should stay under special monitoring.

## Conclusion

CEO-MAGI v3 offline keeps a positive realistic edge on the test split, but 2026Q2 remains fragile: PF `2.6609`, Avg R `0.6183`, Max DD `6.84` and Total R `152.10`.

## Generated Files

- `artifacts\ceo_magi_v3\ceo_magi_v3_decisions.csv`
- `artifacts\ceo_magi_v3\ceo_magi_v3_decisions.jsonl`
- `artifacts\ceo_magi_v3\ceo_magi_v3_summary.md`
- `artifacts\ceo_magi_v3\ceo_magi_v3_summary.json`
