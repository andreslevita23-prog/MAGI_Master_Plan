# MAGI v2 RR 1:2 First-Touch Labels

## Scope

- Target: `tradeable_direction_rr2_first_touch`.
- Classes: `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.
- Intrabar source: Bot A clean M5 candles.
- Rule: hypothetical BUY and SELL are evaluated with SL 10 pips / TP 20 pips over 48 future M5 bars.

## Summary

- Rows: `371501`
- Temporal coverage: `2020-01-15T00:00:00Z` to `2026-04-14T22:55:00Z`
- Same-bar ambiguous: `1101` (`0.2964%`)

## Label Distribution

| label | rows |
| --- | --- |
| DO_NOTHING | 225859 |
| ENTER_SELL | 73678 |
| ENTER_BUY | 71964 |

## Outcome Distribution

### BUY hypothetical

| outcome | rows |
| --- | --- |
| SL_FIRST | 182268 |
| CLOSE_BY_TIMEOUT | 116230 |
| TP_FIRST | 71964 |
| SAME_BAR_AMBIGUOUS | 584 |
| missing_entry_bar | 419 |
| INSUFFICIENT_FUTURE_BARS | 36 |

### SELL hypothetical

| outcome | rows |
| --- | --- |
| SL_FIRST | 180990 |
| CLOSE_BY_TIMEOUT | 115705 |
| TP_FIRST | 73678 |
| SAME_BAR_AMBIGUOUS | 673 |
| missing_entry_bar | 419 |
| INSUFFICIENT_FUTURE_BARS | 36 |

## Avg R by Label

| tradeable_direction_rr2_first_touch | buy_R | sell_R |
| --- | --- | --- |
| DO_NOTHING | -0.32654 | -0.356485 |
| ENTER_BUY | 2.0 | -1.0 |
| ENTER_SELL | -1.0 | 2.0 |

## Entry Match Method

| method | rows |
| --- | --- |
| exact_timestamp | 369012 |
| floor_to_m5 | 2070 |
| missing_entry_bar | 419 |

## Assumptions

- Uses real M5 first-touch from Bot A clean anchor candles, not aggregated future_return labels.
- Entry price is anchor_close at the snapshot timestamp.
- SL is fixed at 10 pips and TP is fixed at 20 pips.
- The next 48 M5 candles are evaluated in timestamp order.
- same_bar_ambiguous is labeled DO_NOTHING for the principal target.
- Timeout R subtracts spread_pips; TP/SL touch levels use raw fixed pip distances because bid/ask OHLC is not available.
- This dataset contains outcome diagnostics and labels; future model feature lists must exclude outcome columns.
