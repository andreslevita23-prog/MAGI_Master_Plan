# CEO-MAGI Temporal Splits And Baselines

## Objetivo

`scripts/ceo_magi/run_ceo_baselines.py` toma `ceo_final_dataset.parquet`, crea splits temporales reproducibles y evalua baselines operativos sin ML contra `ceo_label_h48`.

No entrena modelos, no modifica el dataset final y no cambia la logica de Melchor, Baltasar ni Gaspar.

## Input

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_final_dataset.parquet`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/baselines/`

Archivos:

- `train.parquet`
- `validation.parquet`
- `test.parquet`
- `baseline_metrics.json`
- `baseline_summary.md`

## Split Temporal

- Train: `2020-01-15` a `2023-12-31`
- Validation: `2024-01-01` a `2024-12-31`
- Test: `2025-01-01` a `2026-04-14`

Los rangos se implementan como fechas calendario inclusivas usando `[start, end + 1 day)`.

## Baselines

- `always_do_nothing`: siempre predice `DO_NOTHING`.
- `baltasar_only`: opera `ENTER_BUY` o `ENTER_SELL` cuando `baltasar_signal` es direccional.
- `gaspar_only`: opera solo si `gaspar_signal` trae direccion explicita. En el dataset actual `gaspar_signal` es calidad (`GOOD/FAIR/POOR`), por lo que este baseline toma cero trades.
- `baltasar_gaspar_aligned`: opera la direccion de Baltasar solo si `baltasar_gaspar_alignment == DIRECTION_MATCH`.
- `high_confidence_alignment`: igual que el baseline alineado, pero exige `baltasar_confidence >= 0.60` y `gaspar_confidence >= 0.60`.

## Normalizacion De Senales

El script normaliza de forma robusta:

- BUY: `BUY`, `buy`, `ENTER_BUY`, `LONG`, `OPEN_LONG`.
- SELL: `SELL`, `sell`, `ENTER_SELL`, `SHORT`, `OPEN_SHORT`.
- Sin direccion: `HOLD`, `NEUTRAL`, `none`, `null`, `NO_TRADE`, `DO_NOTHING`, `SKIP_WARN`.

## Metricas

Por split y baseline se calcula:

- total rows
- trades taken
- coverage
- label precision sobre trades ejecutados
- precision BUY
- precision SELL
- matriz de confusion simplificada
- distribucion de predicciones
- distribucion de trades por sesion
- distribucion de trades por ano
- comparacion contra `ceo_label_h48`

## Advertencias

- Estos baselines comparan acciones contra la etiqueta H48 inicial, no contra PnL real con costos, SL/TP o drawdown.
- `future_outcome_h*` no se usa para generar predicciones.
- `always_do_nothing` puede tener alto match rate global por imbalance, pero no toma trades y por tanto no es una politica operativa util.
- `gaspar_only` queda como baseline diagnostico hasta que Gaspar exponga direccion propia o se agregue `gaspar_proposed_direction` al dataset final.

## Proximos Pasos

1. Revisar si conviene agregar `gaspar_proposed_direction` al dataset final.
2. Agregar metricas de EV, drawdown y costos.
3. Implementar un baseline de reglas actual tipo CEO v0.1 si se desea comparar contra produccion rule-based.
4. Usar validation para seleccionar umbrales antes de entrenar ML.
