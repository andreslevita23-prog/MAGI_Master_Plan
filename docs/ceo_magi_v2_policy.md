# CEO-MAGI v2 Policy Audit

## Objetivo

`scripts/ceo_magi/evaluate_ceo_v2_policy.py` valida una primera politica operativa conservadora de CEO-MAGI v2 sobre validation y test.

No entrena modelos, no modifica datasets y no cambia la logica de los magos. Usa probabilidades del modelo v2 ya entrenado.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/validation.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/test.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_model.joblib`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/policy/`

Archivos:

- `ceo_v2_policy_metrics.json`
- `ceo_v2_policy_summary.md`
- `policy_trades_validation.csv`
- `policy_trades_test.csv`

## Politicas Evaluadas

### threshold_070_pure

- threshold `0.70`
- sin filtros contextuales adicionales

### conservative_core

- threshold `0.70`
- session en `london`, `new_york`, `overlap`
- `daily_range_position` entre `0.15` y `0.65`
- Melchor `APPROVE`
- Gaspar diferente de `POOR`
- Baltasar `BUY` o `SELL`

### conservative_extended

- threshold `0.70`
- session en `london`, `new_york`, `overlap`
- `daily_range_position` entre `0.15` y `0.85`
- Melchor `APPROVE`
- Gaspar diferente de `POOR`
- Baltasar `BUY` o `SELL`

## Metricas

Por validation y test:

- rows evaluated
- trades taken
- coverage
- trade precision
- BUY precision
- SELL precision
- prediction distribution
- target distribution entre trades seleccionados
- performance por session
- performance por daily range bucket
- performance por month
- estabilidad validation vs test

## Interpretacion

La politica debe mejorar o al menos mantener la precision de threshold `0.70` puro con una cobertura todavia util. Si la precision sube pero la cobertura cae demasiado, la politica puede servir como modo demo conservador pero no como politica final.

Si validation y test divergen mucho, la politica probablemente esta sobreajustada a segmentos del test y debe pasar por walk-forward antes de usarse.
