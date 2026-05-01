# 2026Q2 Regime Failure Analysis

## Period Performance

| Period | Trades | Avg R | Total R | PF | Max DD | Gaspar block rate | P(det) mean | Q2-like proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026Q2 | 459 | -0.0572 | -26.26 | 0.9003 | 93.66 | 0.0000 | 0.0988 | 0.4553 |
| 2025Q4 | 3,005 | 0.2196 | 659.79 | 1.4495 | 101.57 | 0.0662 | 0.1868 | 0.2659 |
| 2026Q1 | 3,807 | 0.0904 | 344.26 | 1.1596 | 145.87 | 0.0646 | 0.1839 | 0.2367 |

## Gaspar Probability in 2026Q2

| Metric | Value |
| --- | ---: |
| mean | 0.098761 |
| median | 0.068086 |
| p90 | 0.232914 |
| max | 0.385088 |
| share_ge_050 | 0.0 |
| share_ge_040 | 0.0 |
| share_ge_030 | 0.019608 |

## Candidate Rule Impact

| Rule | Q2 blocked | Q2 Avg R filtered | Q2 PF filtered | Test blocked | Test Avg R filtered | Test PF filtered | Test DD filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q2_like_proxy | 209 | 0.1050 | 1.2224 | 5,711 | 0.2091 | 1.3921 | 154.59 |
| sell_mid_high_h4_breakout_or_range | 412 | 0.1023 | 1.1850 | 6,612 | 0.1092 | 1.1922 | 210.58 |
| sell_low_gaspar_prob_030 | 9 | -0.0481 | 0.9164 | 2,809 | 0.1295 | 1.2309 | 212.04 |
| rolling_sell_pf_below_1 | 278 | 0.3671 | 1.9201 | 9,289 | 0.2105 | 1.3935 | 162.00 |
| rolling_pf_below_1_and_drawdown_high | 209 | 0.1050 | 1.2224 | 7,457 | 0.2650 | 1.5153 | 83.06 |

## Worst 2026Q2 Contexts

| Direction | Session | Range | H4 | D1 | Trades | Avg R | PF | DD | Gaspar block rate |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| SELL | new_york | mid | breakout | breakout | 12 | -1.0000 | 0.0000 | 12.00 | 0.0000 |
| SELL | overlap | mid_high | breakout | trend | 6 | -1.0000 | 0.0000 | 6.00 | 0.0000 |
| SELL | london | mid | breakout | breakout | 3 | -1.0000 | 0.0000 | 3.00 | 0.0000 |
| SELL | london | mid | trend | breakout | 2 | -1.0000 | 0.0000 | 2.00 | 0.0000 |
| BUY | london | mid | breakout | trend | 1 | -1.0000 | 0.0000 | 1.00 | 0.0000 |
| SELL | london | mid_high | breakout | trend | 48 | -0.9846 | 0.0000 | 47.26 | 0.0000 |
| SELL | overlap | mid_high | breakout | breakout | 24 | -0.8750 | 0.0870 | 22.00 | 0.0000 |
| SELL | new_york | mid | range | breakout | 8 | -0.8050 | 0.0092 | 6.50 | 0.0000 |
| SELL | asia | mid | breakout | breakout | 12 | -0.7567 | 0.0000 | 9.08 | 0.0000 |
| SELL | london | mid_high | range | breakout | 31 | -0.5161 | 0.3846 | 26.00 | 0.0000 |
| SELL | london | mid | range | breakout | 92 | -0.5154 | 0.2627 | 50.42 | 0.0000 |
| SELL | overlap | mid | breakout | trend | 24 | -0.3625 | 0.3464 | 12.71 | 0.0000 |

## Interpretation

2026Q2 is a small but negative slice: avg R `-0.0572` and PF `0.9003`, versus 2026Q1 avg R `0.0904` and PF `1.1596`. Gaspar did not block it because P(DETERIORATING) stayed low: mean `0.0988`, max `0.3851`, and share >= 0.50 `0.0000`. The strongest simple candidates are diagnostic only and should be tested in a dedicated detector or Melchor v2 risk layer.
