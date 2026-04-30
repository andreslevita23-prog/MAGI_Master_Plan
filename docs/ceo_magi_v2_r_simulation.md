# CEO-MAGI v2 R Simulation Proxy

## Objetivo

`scripts/ceo_magi/simulate_ceo_v2_r_trades.py` evalua la politica `conservative_core` con una simulacion proxy de SL/TP/R usando los campos disponibles en `future_outcomes` H48.

No entrena modelos, no modifica datasets y no cambia la logica de los magos.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_training_records.jsonl`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_dataset.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_model.joblib`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/r_simulation/`

Archivos:

- `r_simulation_metrics.json`
- `r_simulation_summary.md`
- `simulated_trades.csv`
- `metrics_by_year.csv`
- `metrics_by_quarter.csv`
- `metrics_by_month.csv`
- `metrics_by_rr.csv`

## Politica Evaluada

`conservative_core`:

- threshold `0.70`
- session en `london`, `new_york`, `overlap`
- `daily_range_position` entre `0.15` y `0.65`
- Melchor `APPROVE`
- Gaspar diferente de `POOR`
- Baltasar `BUY` o `SELL`

## Perfiles RR

- `rr_1_1`: SL 10 pips, TP 10 pips
- `rr_1_1_5`: SL 10 pips, TP 15 pips
- `rr_1_2`: SL 10 pips, TP 20 pips

## Reglas Proxy

Para una operacion direccional:

- TP si `max_favorable_excursion >= TP + spread`
- SL si `abs(max_adverse_excursion) >= SL`
- si toca ambos dentro del horizonte H48, se marca `ambiguous`
- escenario `conservative`: si es ambiguo, SL primero
- escenario `optimistic`: si es ambiguo, TP primero
- si no toca TP ni SL, se cierra por `future_return_pips` direccional ajustado por spread y convertido a R

## Advertencias

Esto es una simulacion proxy, no rentabilidad real.

Faltan para backtest institucional:

- orden intrabar real de TP/SL
- precio de ejecucion
- comision
- slippage
- sizing
- timestamps exactos de entrada/salida
- reglas de no solapamiento de trades
- calendario de noticias/eventos si aplica

## Uso

Esta simulacion sirve para detectar si la politica tiene EV proxy positivo bajo supuestos razonables y para comparar sensibilidad entre perfiles RR. Si el escenario conservador es muy negativo y el optimista muy positivo, la estrategia depende demasiado de la incertidumbre intrabar y necesita datos de menor timeframe o simulador de ejecucion mas fiel.
