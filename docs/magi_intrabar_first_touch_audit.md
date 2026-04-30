# MAGI Intrabar First-Touch Data Audit

## Objetivo

Auditar si el repositorio contiene datos intrabar M1/M5 suficientes para resolver el problema principal de la simulacion R/SL/TP de CEO v2: cuando TP y SL pudieron tocarse dentro del horizonte H48, determinar cual se toco primero.

## Resultado ejecutivo

Si existen datos intrabar suficientes para una primera version real de first-touch.

El repositorio contiene un dataset limpio de Bot A en M5:

- Ruta: `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`
- Summary: `data/clean/bot_a_sub3_full/cleaned_dataset_summary.json`
- Registros: `371,513`
- Simbolo: `EURUSD`
- Timeframe: `M5`
- Rango: `2020-01-15T00:00:00Z` a `2026-04-14T23:55:00Z`
- Duplicados despues de limpieza: `0`
- Parse errors: `0`
- Gaps forward marcados: `419` (`0.1128%`)
- High spread rows: `1,467` (`0.3949%`)

No se encontro un dataset M1 equivalente dentro del repo. M5 es suficiente para una primera validacion operativa, pero no elimina la ambiguedad cuando TP y SL caen dentro de la misma vela M5.

## Datasets intrabar encontrados

| Dataset | Ruta | Timeframe | Registros | Simbolo | Rango temporal | Estado |
| --- | --- | --- | ---: | --- | --- | --- |
| Bot A sub3 clean full | `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl` | M5 | 371,513 | EURUSD | 2020-01-15 a 2026-04-14 | Utilizable |

## Columnas disponibles

El JSONL limpio contiene las columnas necesarias para reconstruir first-touch M5:

- `snapshot_id`
- `symbol`
- `timestamp`
- `anchor_bar_timestamp`
- `anchor_timeframe`
- `anchor_open`
- `anchor_high`
- `anchor_low`
- `anchor_close`
- `current_price`
- `spread_pips`
- `active_session`
- `trigger_type`
- `validation`

Tambien contiene features y contexto de magos, pero no son necesarios para first-touch.

## Empate con operaciones CEO v2

Las operaciones seleccionadas por `conservative_core` estan en:

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/r_simulation/simulated_trades.csv`

Ese archivo contiene:

- `source_index`
- `timestamp`
- `symbol`
- `direction`
- `rr_profile`
- `sl_pips`
- `tp_pips`
- `spread`

El empate se puede hacer por:

- `symbol`
- `timestamp` de la operacion CEO
- `anchor_bar_timestamp` del dataset M5

## Se puede reconstruir first-touch?

Si, para una primera version M5:

- Entrada: cierre de la vela ancla `anchor_close`.
- Horizonte: 48 velas futuras M5.
- BUY:
  - TP si `high >= entry_price + TP_pips`
  - SL si `low <= entry_price - SL_pips`
- SELL:
  - TP si `low <= entry_price - TP_pips`
  - SL si `high >= entry_price + SL_pips`
- Si TP y SL se tocan en la misma vela M5: `SAME_BAR_AMBIGUOUS`.
- Si no se toca nada: `CLOSE_BY_TIMEOUT`.

## Limitaciones

- No hay M1 disponible en el repo; M1 seria ideal para reducir ambiguedad same-bar.
- M5 no puede ordenar eventos dentro de una misma vela.
- Se usa `anchor_close` como precio de entrada porque CEO opera sobre snapshots de vela cerrada.
- El dataset usa OHLC M5, no ticks ni bid/ask separado.
- Spread existe como `spread_pips`, pero no hay slippage ni comisiones.
- La validacion sigue siendo proxy hasta tener ejecucion real, first-touch M1 o tick, costos completos y reglas de no solapamiento.

## Conclusion

Los datos M5 disponibles permiten implementar first-touch real de primera version y reducir la brecha entre los escenarios conservative/optimistic de la simulacion proxy. Aun asi, las velas con TP y SL dentro del mismo M5 siguen siendo ambiguas y deben tratarse como riesgo residual hasta disponer de M1 o tick.
