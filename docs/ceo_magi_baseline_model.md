# CEO-MAGI Baseline Model v1

## Objetivo

`scripts/ceo_magi/train_ceo_baseline_model.py` entrena el primer baseline ML de CEO-MAGI para predecir:

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

El objetivo no es maximizar accuracy global. El objetivo principal es medir si un modelo tabular puede mejorar la precision cuando decide operar, manteniendo cobertura razonable y estabilidad entre validation y test.

## Inputs

- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/baselines/train.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/baselines/validation.parquet`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/baselines/test.parquet`

## Outputs

Directorio:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/models/`

Archivos:

- `ceo_baseline_model.joblib`
- `ceo_baseline_metrics.json`
- `ceo_baseline_summary.md`
- `ceo_feature_importance.csv`

## Modelo

Modelo inicial:

- `RandomForestClassifier`
- `n_estimators=120`
- `max_depth=12`
- `min_samples_leaf=100`
- `class_weight=balanced_subsample`
- `random_state=42`
- `n_jobs=1`

Se usa Random Forest por interpretabilidad, robustez tabular e importancia de features. No se hace optimizacion de hiperparametros en esta fase.

`n_jobs=1` se usa por portabilidad en el entorno local de Windows, donde los workers paralelos de joblib pueden quedar bloqueados por permisos del sandbox.

## Features Permitidas

Categoricas:

- `session`
- `weekday`
- `regime`
- `melchor_signal`
- `melchor_risk_flags`
- `baltasar_signal`
- `gaspar_signal`
- `mage_agreement`
- `baltasar_gaspar_alignment`

Numericas:

- `hour`
- `spread`
- `atr`
- `daily_range_position`
- `melchor_confidence`
- `baltasar_confidence`
- `gaspar_confidence`

## Features Prohibidas

Nunca se usan como features:

- `future_outcome_h12`
- `future_outcome_h48`
- `future_outcome_h96`
- `future_outcome_h288`
- `ceo_label_h48`

El script valida que ninguna columna prohibida entre en la lista de features antes de entrenar.

## Preprocessing

El pipeline guardado incluye:

- imputacion de categoricas con `UNKNOWN`
- `OneHotEncoder(handle_unknown="ignore")`
- imputacion numerica con mediana
- Random Forest

Los transformadores se ajustan con train mediante el pipeline de sklearn.

## Metricas

Por train, validation y test:

- accuracy
- macro F1
- precision por clase
- recall por clase
- matriz de confusion
- trades taken
- coverage
- trade precision
- BUY precision
- SELL precision
- distribucion de predicciones

Tambien se compara contra `baltasar_only` usando los artefactos de baselines sin ML.

## Advertencias

- `accuracy` puede ser enganosa porque `DO_NOTHING` es la clase mayoritaria.
- Un modelo que predice casi siempre `DO_NOTHING` puede parecer fuerte por accuracy y ser inutil operativamente.
- `trade_precision`, `coverage` y estabilidad entre validation/test son mas importantes que accuracy.
- Esta version no evalua EV, drawdown ni costos. Eso debe agregarse antes de considerar una promocion operativa.

## Proximos Pasos

1. Revisar si el modelo mejora `trade_precision` contra `baltasar_only`.
2. Revisar si la cobertura no colapsa.
3. Agregar EV/drawdown con costos.
4. Agregar umbrales por probabilidad en validation.
5. Evaluar walk-forward antes de cualquier demo.
