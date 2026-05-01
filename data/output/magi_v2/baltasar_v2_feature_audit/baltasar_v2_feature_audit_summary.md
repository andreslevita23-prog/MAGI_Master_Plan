# Baltasar v2 Feature Audit

## Resultado ejecutivo

- Registros auditados: `371513`
- Rango temporal: `2020-01-15T00:00:00Z` a `2026-04-14T23:55:00Z`
- Rutas/columnas reales detectadas: `176`
- Candidate feature groups: `26`
- Features listas: `17`
- Features derivables: `7`
- Features que requieren export de Bot A: `2`

El dataset limpio de Bot A contiene bastante mas senal tecnica que el dataset tabular usado por Baltasar v2 pure_directional. En particular, hay EMA/RSI/estructura/rango reciente por M15/H1/H4/D1 dentro de `features`, ademas de OHLC M5, soporte/resistencia, momentum y spread.

## Top-level columns

account, active_session, allowed_actions, anchor_bar_timestamp, anchor_close, anchor_high, anchor_low, anchor_open, anchor_timeframe, bar_timestamp, current_price, ema_20, ema_200, ema_50, features, gaspar_context, has_gap_forward, is_high_spread, market_structure, momentum, mtf_alignment_status, mtf_alignment_warnings, mtf_data_source_status, news, operational_notes, position, primary_timeframe, recent_range, resistance_levels, rsi_14, schema_version, snapshot_id, source_mode, spread_pips, structure_direction, support_levels, symbol, timestamp, trigger_type, validation

## Candidate features listas

| feature_group | status | source | notes |
| --- | --- | --- | --- |
| ohlc_m5 | ready | anchor_open/high/low/close | Top-level M5 OHLC exists. |
| ema_fast_m5 | ready | ema_20 | Top-level EMA 20 exists. |
| ema_mid_m5 | ready | ema_50 | Top-level EMA 50 exists. |
| ema_slow_m5 | ready | ema_200 | Top-level EMA 200 exists. |
| rsi_m5 | ready | rsi_14 | Top-level RSI exists. |
| momentum_m5 | ready | momentum | Top-level categorical momentum exists. |
| market_structure_m5 | ready | market_structure + structure_direction | Top-level structure fields exist. |
| recent_range_m5 | ready | recent_range | Top-level recent range exists. |
| spread | ready | spread_pips | Spread exists. |
| support_resistance_distance_m5 | ready | support_levels/resistance_levels | Support/resistance levels exist as numeric lists. |
| mtf_ema_m15_h1_h4_d1 | ready | features.*.ema_20/50/200 | MTF EMA values exist for M15/H1/H4/D1. |
| mtf_rsi_m15_h1_h4_d1 | ready | features.*.rsi_14 | MTF RSI exists for M15/H1/H4/D1. |
| mtf_structure_m15_h1_h4_d1 | ready | features.*.market_structure/structure_direction | MTF structure exists. |
| mtf_recent_range_m15_h1_h4_d1 | ready | features.*.recent_range | MTF recent range exists. |
| mtf_alignment | ready | mtf_alignment_status + gaspar_context.higher_timeframe_confluence | Alignment/context fields exist. |
| session_time | ready | active_session + timestamps | Session and timestamp fields exist. |
| candle_body_wicks_m5 | derivable | anchor OHLC | Derive body and wick percentages from M5 OHLC. |
| ema_distance_m5 | derivable | close + EMA | Derive close-EMA and EMA spread distances. |
| ema_slope_m5 | derivable | EMA time series | Derive lagged EMA deltas after sorting by symbol/time. |
| returns_m5 | derivable | anchor_close time series | Derive lagged returns from sorted M5 closes. |
| atr_m5 | derivable | anchor OHLC time series | Derive true range/rolling ATR from M5 OHLC. |
| distance_to_recent_high_low | derivable | anchor OHLC rolling windows | Derive rolling high/low distances. |
| trend_h1_h4_d1 | ready | features.H1/H4/D1 structure_direction | Use exported MTF structure_direction and market_structure. |
| momentum_h1 | derivable | features.H1 EMA/RSI/structure | No H1 momentum label, but can derive proxy from H1 EMA/RSI/structure. |
| atr_h1 | needs_bot_a_export | H1 OHLC or ATR | H1 ATR is not exported directly; recent_range is present but not ATR. |
| fractals | needs_bot_a_export | swing/fractal markers | No explicit fractal/swing markers found. |

## Features recomendadas

| feature | status | available_source_or_gap | needs_bot_a_export |
| --- | --- | --- | --- |
| trend_h1 | ready | features.H1.structure_direction / features.H1.market_structure | False |
| trend_h4 | ready | features.H4.structure_direction / features.H4.market_structure | False |
| trend_d1 | ready | features.D1.structure_direction / features.D1.market_structure | False |
| ema_fast_m5 | ready | ema_20 | False |
| ema_slow_m5 | ready | ema_200 | False |
| ema_distance | derivable | anchor_close, ema_20, ema_50, ema_200 | False |
| ema_slope | derivable | lagged EMA time series | False |
| rsi_m5 | ready | rsi_14 | False |
| rsi_h1 | ready | features.H1.rsi_14 | False |
| atr_m5 | derivable | M5 OHLC rolling true range | False |
| atr_h1 | needs_bot_a_export | H1 ATR or H1 OHLC bars | True |
| momentum_m5 | ready | momentum | False |
| momentum_h1 | derivable | H1 EMA/RSI/structure proxy; direct label missing | False |
| candle_body_pct | derivable | M5 OHLC | False |
| upper_wick_pct | derivable | M5 OHLC | False |
| lower_wick_pct | derivable | M5 OHLC | False |
| distance_to_recent_high | derivable | rolling M5 highs | False |
| distance_to_recent_low | derivable | rolling M5 lows | False |
| support_distance_pips | ready | support_levels | False |
| resistance_distance_pips | ready | resistance_levels | False |
| structure_h1 | ready | features.H1.market_structure | False |
| structure_h4 | ready | features.H4.market_structure | False |
| mtf_trend_alignment | ready | mtf_alignment_status / gaspar_context.higher_timeframe_confluence.directional_alignment | False |

## Dataset de labels

- Disponible: `True`
- Filas: `371501`
- Target distribution: `{'DO_NOTHING': 225859, 'ENTER_SELL': 73678, 'ENTER_BUY': 71964}`

## Conclusion

Si podemos entrenar un Baltasar v2 rich_features con lo disponible. La siguiente version debe expandir `cleaned_dataset.jsonl` a una tabla de features tecnicas M5+MTF y unirla con `rr2_first_touch_labels.parquet` por `symbol + anchor_bar_timestamp/timestamp`.

La unica advertencia importante: H1 ATR directo, fractals/swing markers y momentum H1 explicito no estan exportados como campos directos; pueden derivarse parcialmente o pedirse a Bot A.
