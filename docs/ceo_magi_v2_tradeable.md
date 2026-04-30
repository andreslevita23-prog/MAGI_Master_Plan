# CEO-MAGI v2 Tradeable

## Por Que v1 Fallo

CEO v1 uso `ceo_label_h48`, un target que estaba estructuralmente acoplado a `baltasar_signal`: `ENTER_BUY` solo existia cuando Baltasar era `BUY`, `ENTER_SELL` solo cuando Baltasar era `SELL`, y `NEUTRAL` nunca producia entrada.

El RandomForest v1 aprendio a replicar `baltasar_only`. Eso confirmo que el target no obligaba al CEO a aprender abstencion contextual.

## Que Cambia En v2

v2 usa un target experimental mas conservador:

`ceo_label_h48_tradeable`

El dataset v2 se genera en:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_v2_tradeable/`

No reemplaza `ceo_final_dataset.parquet`.

## Construccion Del Target Tradeable

La regla reutiliza la logica auditada en `scripts/ceo_magi/audit_ceo_labels.py`.

Una entrada solo se etiqueta como tradeable si cumple:

- Baltasar es direccional.
- Melchor es `APPROVE`.
- Gaspar no es `POOR`.
- Sesion operable: `london`, `new_york` u `overlap`.
- `spread <= 2`.
- `atr <= 1.2`.
- `daily_range_position` entre `0.15` y `0.85`.
- Sin `DIRECTION_MISMATCH` ni `DIRECTION_REJECTED_BY_GASPAR`.
- Movimiento H48 neto ajustado por spread al menos 7 pips.
- `max_favorable_excursion >= 8`.
- `abs(max_adverse_excursion) <= 10`.

Si no cumple, el label es `DO_NOTHING`.

## Scripts

- `scripts/ceo_magi/build_ceo_v2_tradeable_dataset.py`
- `scripts/ceo_magi/train_ceo_v2_tradeable_model.py`

## Features Permitidas

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

No se usan campos futuros, outcomes ni labels como features.

## Modelo

Baseline ML:

- `RandomForestClassifier`
- `class_weight=balanced_subsample`
- sin redes neuronales
- sin optimizacion de hiperparametros

La evaluacion incluye prediccion por argmax y politica por umbral de probabilidad: `0.50`, `0.60`, `0.70`, `0.80`.

## Metricas Principales

Se reporta:

- accuracy
- macro F1
- precision/recall por clase
- matriz de confusion
- trades taken
- coverage
- trade precision
- BUY precision
- SELL precision
- distribucion de predicciones
- comparacion contra CEO v1, `baltasar_only` y `always_do_nothing`

## Limitaciones

Este target todavia no es institucional. Usa MFE/MAE y movimiento H48 como aproximacion, pero no tiene:

- SL/TP explicitos por candidato
- orden intrabar de TP/SL
- comisiones y slippage
- R multiple
- drawdown de trade abierto
- position sizing

## Siguiente Paso Recomendado

Si v2 mejora precision con cobertura razonable, el siguiente paso es agregar simulacion de trade candidato por snapshot para construir un label basado en R multiple y drawdown real. Si v2 colapsa o solo aprende filtros duros, conviene pasar a un modelo de scoring/EV por regimen antes de otro clasificador multiclase.
