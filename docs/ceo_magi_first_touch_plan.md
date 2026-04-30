# CEO-MAGI First-Touch Intrabar Plan

## Por que first-touch es critico

La simulacion proxy de CEO v2 conservative_core mostro una brecha grande entre escenarios:

- Conservative: asume SL primero cuando TP y SL pudieron tocarse.
- Optimistic: asume TP primero en esos mismos casos.

Esa diferencia impide afirmar rentabilidad real. El primer-touch intrabar resuelve gran parte del problema porque evalua las velas futuras en orden temporal y registra si se toco primero TP, SL o ninguno.

## Que resuelve M5 intrabar

La primera version implementada usa el dataset limpio de Bot A M5:

- `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`

El script creado:

- `scripts/ceo_magi/build_intrabar_first_touch.py`

Inputs:

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/r_simulation/simulated_trades.csv`
- `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`

Outputs:

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/first_touch_trades.csv`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/first_touch_metrics.json`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/first_touch_summary.md`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/metrics_by_rr.csv`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/metrics_by_year.csv`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/metrics_by_month.csv`

## Decisiones tecnicas de la v0.1

- Timeframe: M5.
- Horizonte: 48 velas futuras M5.
- Entry price: `anchor_close` en el timestamp de decision CEO.
- Las velas evaluadas empiezan despues de la vela de entrada.
- Reglas de touch:
  - BUY TP: `high >= entry_price + TP_pips`
  - BUY SL: `low <= entry_price - SL_pips`
  - SELL TP: `low <= entry_price - TP_pips`
  - SELL SL: `high >= entry_price + SL_pips`
- Si TP y SL se tocan en la misma vela M5: `SAME_BAR_AMBIGUOUS`.
- Si no se toca TP/SL dentro del horizonte: `CLOSE_BY_TIMEOUT`.
- En timeout, el R se calcula con movimiento direccional al cierre H48 menos spread.
- Para metricas headline, `SAME_BAR_AMBIGUOUS` se trata como SL conservador; tambien se guarda R resuelto separado.

## Resultados principales

| RR | Trades con intrabar | Coverage | TP first | SL first | Timeout | Same-bar ambiguous | Avg R | Total R | PF | Max DD R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1:1 | 25,559 | 99.94% | 12,389 | 11,235 | 1,828 | 107 | 0.040966 | 1,047.05 | 1.089992 | 339.24 |
| 1:1.5 | 25,559 | 99.94% | 9,246 | 12,851 | 3,390 | 72 | 0.064391 | 1,645.78 | 1.123731 | 371.61 |
| 1:2 | 25,559 | 99.94% | 7,086 | 13,722 | 4,727 | 24 | 0.088719 | 2,267.56 | 1.160032 | 353.56 |

## Comparacion contra proxy anterior

| RR | First-touch Avg R | First-touch Total R | Proxy conservative Avg R | Proxy conservative Total R | Proxy optimistic Avg R | Proxy optimistic Total R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1:1 | 0.040966 | 1,047.05 | -0.233736 | -5,977.57 | 0.325425 | 8,322.43 |
| 1:1.5 | 0.064391 | 1,645.78 | -0.124401 | -3,181.42 | 0.378161 | 9,671.08 |
| 1:2 | 0.088719 | 2,267.56 | -0.040733 | -1,041.70 | 0.396234 | 10,133.30 |

La v0.1 reduce la incertidumbre principal: ya no necesitamos asumir siempre SL o TP cuando ambos fueron posibles dentro de H48. El resultado M5 queda entre los escenarios conservative y optimistic, como era esperable.

## Riesgos tecnicos

- M5 aun deja eventos same-bar ambiguos.
- No hay slippage ni comision.
- No hay bid/ask historico separado.
- No se valida todavia no solapamiento de operaciones.
- El uso de `anchor_close` debe confirmarse contra la ejecucion real esperada del sistema.
- La rentabilidad no debe declararse definitiva hasta repetir el backtest con M1 o tick, costos completos y reglas operativas reales.

## Datos que faltan para version institucional

Bot A o un extractor nuevo deberia exportar:

- Timeframe recomendado: M5 ahora, M1 ideal.
- Columnas minimas:
  - `symbol`
  - `timeframe`
  - `bar_open_timestamp`
  - `bar_close_timestamp`
  - `open`
  - `high`
  - `low`
  - `close`
  - `spread_pips`
  - `bid_open/bid_high/bid_low/bid_close` si existe
  - `ask_open/ask_high/ask_low/ask_close` si existe
  - `source_run_id`
- Formato recomendado:
  - `parquet` particionado por `symbol/timeframe/year/month`
  - alternativa: JSONL gzip por dia
- Ruta sugerida:
  - `data/intrabar/bot_a_m1/EURUSD/year=YYYY/month=MM/*.parquet`

## Empate con trades CEO

Para evitar leakage:

- Empatar entrada por `symbol + timestamp`.
- Usar solo barras con timestamp posterior al cierre de la vela de decision.
- No usar informacion posterior a la salida para decidir entrada.
- Validar que el primer bar futuro sea estrictamente posterior al entry timestamp.
- Registrar cantidad de barras disponibles por trade.

## Siguiente recomendacion

Usar esta v0.1 para redisenar labels RR 1:2 y, en paralelo, preparar export M1 desde Bot A. El siguiente bloque recomendado es construir `tradeable_direction_rr2_first_touch` y compararlo contra el target tradeable actual antes de reentrenar Baltasar v2.
