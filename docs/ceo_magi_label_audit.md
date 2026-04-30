# CEO-MAGI Label Audit

## Objetivo

`scripts/ceo_magi/audit_ceo_labels.py` audita el target actual `ceo_label_h48`, mide su dependencia respecto a `baltasar_signal` y revisa si los outcomes crudos permiten construir labels mas operativos.

Este script no modifica `ceo_final_dataset`, no entrena modelos y no reemplaza el label actual.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_final_dataset.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_training_records.jsonl`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/label_audit/`

Archivos:

- `label_audit_metrics.json`
- `label_audit_summary.md`
- `label_distribution_by_year.csv`
- `label_distribution_by_session.csv`
- `label_vs_baltasar_crosstab.csv`
- `label_vs_gaspar_crosstab.csv`
- `label_vs_regime_crosstab.csv`

## Auditorias Incluidas

El script calcula:

- crosstab absoluta entre `ceo_label_h48` y `baltasar_signal`
- crosstab porcentual global
- mutual information y normalized mutual information
- accuracy de una regla simple basada solo en `baltasar_signal`
- relacion con `gaspar_signal`, `session`, `regime`
- resumen numerico de `atr`, `daily_range_position` y `spread` por label
- campos reales disponibles dentro de `future_outcomes`

## Labels Alternativos Evaluados En Auditoria

Los siguientes labels se calculan solo en memoria y se reportan en `label_audit_metrics.json`:

- `ceo_label_h48_strict`
- `ceo_label_h48_ev`
- `ceo_label_h48_directional_filtered`
- `ceo_label_h48_tradeable`

No se escriben de vuelta al dataset final.

## Interpretacion

Si `ENTER_BUY` solo aparece cuando Baltasar es `BUY`, y `ENTER_SELL` solo cuando Baltasar es `SELL`, el target esta estructuralmente acoplado a Baltasar. Eso no significa que el label sea inutil, pero si significa que un modelo puede aprender la regla de direccion sin aprender abstencion contextual.

Para CEO-MAGI, el siguiente target debe penalizar entradas malas y premiar abstenciones buenas usando:

- retorno neto ajustado por spread/costo
- MFE y MAE
- filtros de riesgo/contexto
- tradeability real

## Datos Que Faltan Para Labels Institucionales

Aunque el JSONL actual tiene `future_return_pips`, MFE, MAE y movimiento arriba/abajo, faltan datos de ejecucion real:

- SL/TP por candidato
- hit TP / hit SL
- orden intrabar si toca TP y SL
- exit reason
- R multiple
- PnL neto con spread, comision y slippage
- drawdown durante la vida del trade
- impacto de position sizing

Estos campos deberian venir de una simulacion de trade candidato por snapshot, no de direccion futura cruda.
