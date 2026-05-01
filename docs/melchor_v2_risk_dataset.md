# Melchor v2 Risk Dataset

## Scope

Each row is a Baltasar+Gaspar candidate trade. Melchor v2 evaluates accumulated operational risk before allowing it.

## Dataset Size

- Rows: `100,876`
- Feature columns available: `23`
- Missing requested features: `['spread_pips', 'volatility_12', 'close_to_ema200', 'ema_20_50_distance', 'ema_50_200_distance']`
- Ready for training: `True`

## Label Distribution

### risk_block_rr2

| Split | APPROVE | BLOCK | CAUTION |
| --- | ---: | ---: | ---: |
| test | 7,836 | 11,547 | 584 |
| train | 61,086 | 7,396 | 1,002 |
| validation | 3,420 | 7,803 | 202 |

### risk_block_rr2_strict

| Split | APPROVE | BLOCK | CAUTION |
| --- | ---: | ---: | ---: |
| test | 8,023 | 10,754 | 1,190 |
| train | 61,401 | 6,212 | 1,871 |
| validation | 3,418 | 7,586 | 421 |

### risk_block_rr2_soft

| Split | APPROVE | BLOCK | CAUTION |
| --- | ---: | ---: | ---: |
| test | 7,836 | 11,547 | 584 |
| train | 61,086 | 7,396 | 1,002 |
| validation | 3,420 | 7,803 | 202 |

## 2026Q2 Capture

- Rows: `459`
- Main label: `{'BLOCK': 263, 'APPROVE': 155, 'CAUTION': 41}`
- Strict: `{'BLOCK': 245, 'APPROVE': 146, 'CAUTION': 68}`
- Soft: `{'BLOCK': 263, 'APPROVE': 155, 'CAUTION': 41}`

## Leakage Check

- Forbidden feature intersection: `[]`
- `realized_R`, future R/PF/DD, labels, dates and 2026Q2 flags are diagnostics/labels only, not features.

## Nulls

| Column | Nulls |
| --- | ---: |
| `rolling_sell_pf_20` | 13 |
| `rolling_sell_pf_50` | 13 |
| `rolling_sell_pf_100` | 13 |
| `rolling_sell_avg_R_20` | 13 |
| `rolling_sell_avg_R_50` | 13 |
| `rolling_sell_avg_R_100` | 13 |
| `rolling_pf_20` | 1 |
| `rolling_pf_50` | 1 |
| `rolling_pf_100` | 1 |
| `rolling_avg_R_20` | 1 |
| `rolling_avg_R_50` | 1 |
| `rolling_avg_R_100` | 1 |
| `rolling_drawdown_50` | 1 |
| `rolling_drawdown_100` | 1 |
| `rolling_win_rate_20` | 1 |
| `rolling_win_rate_50` | 1 |
| `rolling_win_rate_100` | 1 |
| `rolling_unfavorable_rate_50` | 1 |
| `rolling_unfavorable_rate_100` | 1 |

## Causal Controls

- Feature columns are past rolling state or current pre-trade context only.
- Future R/PF/DD columns are target-construction diagnostics and must not be model features.
- No date, month, quarter or 2026Q2 flag is a feature.
- Labels use future windows by design because they are supervised targets.

## Next Step

Train Melchor v2 as a three-class risk layer (`APPROVE`, `CAUTION`, `BLOCK`) if the training distribution has enough `BLOCK` examples and operational filtering improves validation/test.
