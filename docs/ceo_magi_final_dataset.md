# CEO-MAGI Final Dataset

## Objetivo

`scripts/ceo_magi/build_ceo_final_dataset.py` convierte el JSONL crudo de entrenamiento CEO-MAGI en un dataset tabular listo para la siguiente fase de entrenamiento.

No entrena modelos, no modifica la logica de Melchor, Baltasar ni Gaspar, y no cambia contratos existentes. Solo lee registros CEO ya generados, aplana campos observables y crea una primera etiqueta operacional.

## Input

Input por defecto:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_training_records.jsonl`

Cada linea contiene:

- features disponibles en tiempo de decision
- voto normalizado de Melchor
- voto normalizado de Baltasar
- voto normalizado de Gaspar
- outcomes futuros H12/H48/H96/H288
- leakage guard del generador original

## Outputs

Outputs por defecto:

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_final_dataset.csv`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_final_dataset.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_final_dataset_summary.json`

## Columnas Generadas

El dataset final incluye:

- `timestamp`
- `symbol`
- `session`
- `hour`
- `weekday`
- `spread`
- `atr`
- `daily_range_position`
- `regime`
- `melchor_signal`
- `melchor_confidence`
- `melchor_risk_flags`
- `baltasar_signal`
- `baltasar_confidence`
- `gaspar_signal`
- `gaspar_confidence`
- `mage_agreement`
- `baltasar_gaspar_alignment`
- `future_outcome_h12`
- `future_outcome_h48`
- `future_outcome_h96`
- `future_outcome_h288`
- `ceo_label_h48`

## Regla Inicial De Label

La etiqueta principal es `ceo_label_h48`.

Regla inicial:

- `ENTER_BUY` si `baltasar_signal == BUY`, H48 `real_direction == BUY` y `future_return_pips >= 3.0`.
- `ENTER_SELL` si `baltasar_signal == SELL`, H48 `real_direction == SELL` y `future_return_pips <= -3.0`.
- `DO_NOTHING` en cualquier otro caso.

Esta regla es deliberadamente conservadora y todavia no representa una politica final. Su objetivo es crear una primera tarea supervisada coherente con la idea de que CEO-MAGI aprende cuando confiar en una senal direccional existente.

## Decisiones Tecnicas

- `atr` usa `features_at_decision_time.gaspar_context.timing_quality.daily_atr_consumed_pct`.
- Si ese campo falta, `atr` cae a `day_context.current_d1_range_vs_atr`.
- `daily_range_position` usa `gaspar_context.price_structure_position.position_in_d1_range`.
- `regime` combina sesion, estructura H4, estructura D1, alineacion direccional, bucket de ATR y bucket de posicion en rango D1.
- `future_outcome_h*` guarda `future_outcomes[horizon].real_direction`.
- En el JSONL CEO inspeccionado, `features_at_decision_time.features` viene vacio; por eso el primer dataset final se apoya en votos normalizados y `gaspar_context`.

## Advertencias

- `ceo_label_h48` usa outcomes futuros y por tanto nunca debe entrar como feature.
- Las columnas `future_outcome_h*` son diagnosticas/labels auxiliares y tampoco deben entrar como features del modelo.
- El label actual no incorpora aun costos completos, slippage, comision, drawdown ni reglas de ejecucion virtual.
- El dataset sigue siendo de un solo simbolo (`EURUSD`) y timeframe base `M5`.
- Esta version no aplica encoding, scaling ni split temporal. Eso debe hacerse en la fase de entrenamiento, ajustando transformadores solo con train.

## Proximos Pasos

1. Validar distribucion de labels y nulos.
2. Implementar split temporal train/validation/test.
3. Implementar baselines sin ML: `DO_NOTHING_ALWAYS`, `RULE_BASED_CURRENT`, `BALTASAR_ONLY`, `BALTASAR_GASPAR_GOOD`.
4. Definir EV neto con costos operativos.
5. Agregar evaluacion de coverage, precision en trades, EV, drawdown y F1 macro.
6. Entrenar un baseline tabular solo despues de tener metricas y baselines reproducibles.
