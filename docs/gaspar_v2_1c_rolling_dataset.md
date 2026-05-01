# Gaspar v2.1c Rolling Causal Dataset

## Scope

Each row is a selected Baltasar v2 trade with rolling system-state features computed only from previous trades.

Targets use future windows and are labels only, never features.

## Dataset Size

- Rows: `100,876`
- Windows: `[20, 50, 100]`
- Primary target window: `50` trades

## Split Rows

| Split | Rows |
| --- | ---: |
| test | 19,967 |
| train | 69,484 |
| validation | 11,425 |

## `regime_deteriorating_rr2` Distribution

| Split | DETERIORATING | NEUTRAL | STABLE |
| --- | ---: | ---: | ---: |
| test | 8,882 | 20 | 11,065 |
| train | 4,220 | 0 | 65,264 |
| validation | 5,371 | 0 | 6,054 |

## `sell_risk_next_window` Distribution

| Split | HIGH | LOW | NEUTRAL |
| --- | ---: | ---: | ---: |
| test | 9,310 | 10,637 | 20 |
| train | 5,044 | 64,440 | 0 |
| validation | 6,001 | 5,424 | 0 |

## Rolling Nulls

| Column | Nulls |
| --- | ---: |
| `rolling_sell_avg_R_20` | 13 |
| `rolling_sell_pf_20` | 13 |
| `rolling_sell_win_rate_20` | 13 |
| `rolling_sell_avg_R_50` | 13 |
| `rolling_sell_pf_50` | 13 |
| `rolling_sell_win_rate_50` | 13 |
| `rolling_sell_avg_R_100` | 13 |
| `rolling_sell_pf_100` | 13 |
| `rolling_sell_win_rate_100` | 13 |
| `rolling_avg_R_20` | 1 |
| `rolling_pf_20` | 1 |
| `rolling_win_rate_20` | 1 |
| `rolling_buy_avg_R_20` | 1 |
| `rolling_buy_pf_20` | 1 |
| `rolling_buy_win_rate_20` | 1 |
| `rolling_unfavorable_rate_20` | 1 |
| `rolling_avg_R_50` | 1 |
| `rolling_pf_50` | 1 |
| `rolling_win_rate_50` | 1 |
| `rolling_buy_avg_R_50` | 1 |
| `rolling_buy_pf_50` | 1 |
| `rolling_buy_win_rate_50` | 1 |
| `rolling_unfavorable_rate_50` | 1 |
| `rolling_avg_R_100` | 1 |
| `rolling_pf_100` | 1 |

## Deterioration Examples

| timestamp | split | prediction | realized_R | rolling_avg_R_50 | rolling_pf_50 | rolling_sell_avg_R_50 | rolling_sell_pf_50 | rolling_drawdown_50 | recent_loss_streak | recent_sell_loss_streak | regime_deteriorating_rr2 | sell_risk_next_window |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-01-15 12:00:00+00:00 | train | ENTER_BUY | 2.0 | nan | nan | nan | nan | nan | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:05:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:10:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:15:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:20:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:25:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:30:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:35:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:40:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:45:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |

## SELL High Risk Examples

| timestamp | split | prediction | realized_R | rolling_avg_R_50 | rolling_pf_50 | rolling_sell_avg_R_50 | rolling_sell_pf_50 | rolling_drawdown_50 | recent_loss_streak | recent_sell_loss_streak | regime_deteriorating_rr2 | sell_risk_next_window |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-01-15 12:00:00+00:00 | train | ENTER_BUY | 2.0 | nan | nan | nan | nan | nan | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:05:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:10:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:15:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:20:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:25:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:30:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:35:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:40:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |
| 2020-01-15 12:45:00+00:00 | train | ENTER_BUY | 2.0 | 2.0 | inf | nan | nan | 0.0 | 0 | 0 | DETERIORATING | HIGH |

## 2026Q2 Capture

- Rows: `459`
- Regime distribution: `{'DETERIORATING': 259, 'STABLE': 180, 'NEUTRAL': 20}`
- SELL distribution: `{'HIGH': 259, 'LOW': 180, 'NEUTRAL': 20}`
- 2026Q2-like proxy rate: `0.455338`

## Causal Controls

- All rolling feature columns use only previous trades and are shifted by construction.
- Future windows are used only to build target labels.
- No date, month or quarter is used as a predictive feature.
- The 2026Q2-like proxy uses only past rolling PF, sell PF, drawdown and unfavorable rate.
