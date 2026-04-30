# CEO-MAGI v2 Segment Analysis

## Objetivo

`scripts/ceo_magi/analyze_ceo_v2_segments.py` analiza en que contextos funciona mejor el modelo CEO-MAGI v2 tradeable usando solo el set de test.

No entrena modelos, no modifica datasets y no cambia la logica de los magos.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/test.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/ceo_v2_tradeable_model.joblib`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/segments/`

Archivos:

- `ceo_v2_segments_summary.md`
- `ceo_v2_segments_metrics.json`
- `segment_by_session.csv`
- `segment_by_hour.csv`
- `segment_by_weekday.csv`
- `segment_by_regime.csv`
- `segment_by_gaspar_signal.csv`
- `segment_by_melchor_signal.csv`
- `segment_by_baltasar_signal.csv`
- `segment_by_daily_range_bucket.csv`
- `segment_by_atr_bucket.csv`

## Thresholds

Se analizan dos politicas:

- threshold `0.60`
- threshold `0.70`

La regla es:

- ejecutar `ENTER_BUY` si su probabilidad es la mayor entre BUY/SELL y supera el threshold
- ejecutar `ENTER_SELL` si su probabilidad es la mayor entre BUY/SELL y supera el threshold
- si ninguna supera el threshold, `DO_NOTHING`

## Segmentos

Se reporta por:

- session
- hour
- weekday
- regime
- gaspar_signal
- melchor_signal
- baltasar_signal
- daily_range_bucket
- atr_bucket

Para cada segmento:

- rows
- trades_taken
- coverage
- trade_precision
- BUY precision
- SELL precision
- predicciones por clase
- low_sample

`low_sample=true` si `trades_taken < 100`.

## Uso

Este analisis sirve para detectar:

- contextos donde v2 tiene mejor precision
- horarios/sesiones que conviene bloquear
- segmentos con muestra demasiado baja
- candidatos para una primera politica operativa con filtros duros

No debe usarse solo para elegir el mejor segmento por precision, porque eso puede sobreajustar al test. La decision debe preferir segmentos con muestra suficiente, precision estable y sentido operativo.
