# CEO-MAGI v2 Walk-Forward Policy

## Objetivo

`scripts/ceo_magi/walk_forward_ceo_v2_policy.py` evalua la politica `conservative_core` de CEO-MAGI v2 a traves del tiempo.

No reentrena el modelo. Aplica el modelo v2 ya guardado y la politica fija sobre todo `ceo_v2_tradeable_dataset.parquet`.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_dataset.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_model.joblib`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/walk_forward_policy/`

Archivos:

- `walk_forward_metrics.json`
- `walk_forward_summary.md`
- `yearly_metrics.csv`
- `quarterly_metrics.csv`
- `monthly_metrics.csv`

## Politica Evaluada

`conservative_core`:

- threshold `0.70`
- session en `london`, `new_york`, `overlap`
- `daily_range_position` entre `0.15` y `0.65`
- Melchor `APPROVE`
- Gaspar diferente de `POOR`
- Baltasar `BUY` o `SELL`

## Ventanas

Se reporta:

- anual
- trimestral
- mensual

## Metricas

Por ventana:

- rows
- trades_taken
- coverage
- trade_precision
- BUY precision
- SELL precision
- prediction distribution
- selected target distribution

## Interpretacion

Esta validacion ayuda a detectar si una politica fija mantiene precision razonable a traves de anos, trimestres y meses. Si hay muchos meses con precision baja, cero trades o dependencia de pocos meses, la politica no debe promoverse todavia.

El siguiente paso recomendado, si la politica se ve estable, es simular R/SL/TP/costos. Si no se ve estable, conviene redisenar target, thresholds o filtros antes de agregar ejecucion.
