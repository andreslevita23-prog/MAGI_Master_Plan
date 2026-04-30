# MAGI v2 RR 1:2 First-Touch Labels

## Objetivo

Construir el primer target operativo real para reentrenar Baltasar v2 usando first-touch M5, no direccion simple ni outcomes agregados.

El target principal es:

- `tradeable_direction_rr2_first_touch`

Clases:

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

## Inputs

- Intrabar M5 limpio: `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`
- First-touch CEO v2 de referencia: `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/first_touch/first_touch_trades.csv`
- Dataset CEO v2 con features/contexto: `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_dataset.parquet`

## Script

- `scripts/magi_v2/build_rr2_first_touch_labels.py`

## Outputs

- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet`
- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.csv`
- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels_summary.json`
- `data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels_summary.md`

## Regla de label

Para cada snapshot M5:

1. Se toma `anchor_close` como `entry_price`.
2. Se evalua un BUY hipotetico con SL 10 pips y TP 20 pips.
3. Se evalua un SELL hipotetico con SL 10 pips y TP 20 pips.
4. Se recorren las siguientes 48 velas M5 en orden temporal.
5. Si BUY toca TP primero y SELL no tiene mejor R, el label es `ENTER_BUY`.
6. Si SELL toca TP primero y BUY no tiene mejor R, el label es `ENTER_SELL`.
7. Si ambos ganan con el mismo R, ambos fallan, ambos son ambiguos, no hay 48 velas futuras o no hay ventaja clara, el label es `DO_NOTHING`.
8. Si TP y SL ocurren en la misma vela M5, se marca `same_bar_ambiguous_flag` y el label principal se fuerza a `DO_NOTHING`.

## Columnas principales

El dataset incluye trazabilidad y diagnostico:

- `source_index`
- `snapshot_id`
- `timestamp`
- `anchor_bar_timestamp`
- `entry_match_method`
- `symbol`
- `entry_price`
- `buy_outcome`
- `sell_outcome`
- `buy_R`
- `sell_R`
- `buy_first_touch`
- `sell_first_touch`
- `buy_bars_to_exit`
- `sell_bars_to_exit`
- `tradeable_direction_rr2_first_touch`
- `same_bar_ambiguous_flag`
- `spread_pips`

Tambien conserva las features permitidas para futuros modelos:

- session, hour, weekday
- atr, daily_range_position, regime
- melchor_signal, melchor_confidence, melchor_risk_flags
- baltasar_signal, baltasar_confidence
- gaspar_signal, gaspar_confidence
- mage_agreement, baltasar_gaspar_alignment

## Resultados de generacion

- Filas generadas: `371,501`
- Coverage temporal: `2020-01-15T00:00:00Z` a `2026-04-14T22:55:00Z`
- Same-bar ambiguous: `1,101` (`0.2964%`)

## Distribucion del label

| Label | Filas | Porcentaje |
| --- | ---: | ---: |
| DO_NOTHING | 225,859 | 60.80% |
| ENTER_BUY | 71,964 | 19.37% |
| ENTER_SELL | 73,678 | 19.83% |

## Outcomes hipoteticos

### BUY

| Outcome | Filas |
| --- | ---: |
| SL_FIRST | 182,268 |
| CLOSE_BY_TIMEOUT | 116,230 |
| TP_FIRST | 71,964 |
| SAME_BAR_AMBIGUOUS | 584 |
| missing_entry_bar | 419 |
| INSUFFICIENT_FUTURE_BARS | 36 |

### SELL

| Outcome | Filas |
| --- | ---: |
| SL_FIRST | 180,990 |
| CLOSE_BY_TIMEOUT | 115,705 |
| TP_FIRST | 73,678 |
| SAME_BAR_AMBIGUOUS | 673 |
| missing_entry_bar | 419 |
| INSUFFICIENT_FUTURE_BARS | 36 |

## Avg R por clase

| Label | buy_R | sell_R |
| --- | ---: | ---: |
| DO_NOTHING | -0.326540 | -0.356485 |
| ENTER_BUY | 2.000000 | -1.000000 |
| ENTER_SELL | -1.000000 | 2.000000 |

## Calidad de empate temporal

| Metodo | Filas |
| --- | ---: |
| exact_timestamp | 369,012 |
| floor_to_m5 | 2,070 |
| missing_entry_bar | 419 |

Decision tecnica: se usa `floor_to_m5` solo cuando el timestamp del dataset CEO trae segundos dentro de la misma vela, por ejemplo `03:10:30Z`. Se conserva `timestamp` original y se agrega `anchor_bar_timestamp` para trazabilidad.

## Assumptions

- Se usa first-touch real M5 desde Bot A.
- La entrada es `anchor_close`, porque los snapshots son de vela cerrada.
- SL y TP son fijos: 10 pips y 20 pips.
- El horizonte es de 48 velas M5 futuras.
- `same_bar_ambiguous` no se usa para direccionalidad; se etiqueta `DO_NOTHING`.
- El timeout resta `spread_pips`.
- TP/SL usan niveles fijos en pips sin bid/ask separado, porque el dataset no trae bid/ask OHLC historico.
- Las columnas outcome/diagnostico no deben usarse como features al entrenar Baltasar v2.

## Limitaciones

- M5 no resuelve el orden dentro de una misma vela.
- No hay M1/tick en el repo para reducir aun mas la ambiguedad.
- No hay slippage, comisiones ni bid/ask OHLC separado.
- No se modela no solapamiento de operaciones.
- Este target mejora la verdad operativa, pero sigue siendo proxy hasta tener ejecucion institucional.

## Recomendacion para Baltasar v2

Entrenar Baltasar v2 primero con este target, pero con un enfoque conservador:

- Modelo baseline interpretable antes de optimizar.
- Split temporal igual que CEO: train 2020-2023, validation 2024, test 2025-2026.
- Features permitidas: contexto y senales disponibles al snapshot.
- Features prohibidas: `buy_outcome`, `sell_outcome`, `buy_R`, `sell_R`, first-touch, labels y cualquier futuro.
- Metricas prioritarias: precision de `ENTER_BUY`/`ENTER_SELL`, coverage, EV proxy RR 1:2, profit factor, drawdown y estabilidad walk-forward.
