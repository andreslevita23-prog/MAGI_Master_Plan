# CEO-MAGI Training Plan

## Objetivo

CEO-MAGI no debe predecir el mercado de forma directa. Su tarea debe ser aprender cuando convertir las senales de Melchor, Baltasar y Gaspar en una decision operativa y cuando abstenerse.

Salida objetivo inicial:

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

El criterio principal no es accuracy. El criterio principal es seleccionar pocos contextos con mejor expectativa, riesgo controlado y cobertura razonable.

## Auditoria Del Repositorio

### Estructura principal encontrada

- `magi/`: contratos y logica actual de los magos.
- `magi/adapters/`: adaptadores reales de Melchor, Baltasar y Gaspar.
- `simulator/`: carga, validacion, timeline, ejecucion virtual, metricas, generacion de dataset CEO y analisis agregados.
- `config/simulator_v01.yaml`: configuracion actual del simulador y modo de generacion CEO.
- `data/clean/bot_a_sub3_full/`: dataset limpio de Bot A sub3.
- `data/output/ceo_training/`: datasets y analisis generados para CEO-MAGI.
- `data/output/simulations/`: corridas del simulador MAGI.
- `baltasar_training_v1/`: pipeline historico de entrenamiento/validacion de Baltasar.
- `gaspar_training_v1/`: pipeline historico de entrenamiento/validacion de Gaspar.
- `docs/`: documentacion de arquitectura, contratos, simulador, datasets y metodologia.
- `tests/`: pruebas unitarias del simulador, validacion, adapters y dataset CEO.

### Scripts MAGI relevantes

- `run_simulation.py`: entrada principal. Si `ceo_training_mode=true`, genera dataset CEO; si no, corre simulacion con CEO rule-based y ejecucion virtual.
- `simulator/ceo_training_dataset.py`: construye `ceo_training_records.jsonl` con votos, features en tiempo de decision, outcomes futuros y leakage guard.
- `simulator/ceo_vote_analysis.py`: analiza combinaciones Melchor/Baltasar/Gaspar.
- `simulator/ceo_individual_vote_analysis.py`: analiza votos individuales y cruces Baltasar x Gaspar.
- `simulator/ceo_monthly_vote_analysis.py`: analiza estabilidad mensual H48.
- `simulator/ceo_regime_analysis.py`: segmenta resultados por regimen/contexto.
- `simulator/execution.py`: ejecucion virtual para trades con SL/TP/timeout.
- `simulator/metrics.py`: metricas basicas de simulacion.
- `scripts/generate_magi_full_phase_report.py` y `scripts/generate_magi_executive_report.py`: reportes existentes.

## Dataset CEO-MAGI Encontrado

Dataset mas reciente:

`data/output/ceo_training/20260429T141153Z_magi_v01_phase2/`

Archivos principales:

- `ceo_training_records.jsonl`
- `ceo_training_summary.json`
- `ceo_training_summary.md`
- `ceo_individual_vote_analysis.json`
- `ceo_individual_vote_analysis.md`
- `ceo_monthly_vote_analysis.json`
- `ceo_monthly_vote_analysis.md`
- `ceo_regime_analysis.json`
- `ceo_regime_analysis.md`
- `ceo_regime_segments.csv`
- `baltasar_vote_outcomes.csv`
- `gaspar_quality_outcomes.csv`
- `baltasar_gaspar_cross_outcomes.csv`
- `baltasar_monthly_outcomes.csv`
- `gaspar_good_monthly_outcomes.csv`

Resumen del dataset mas reciente:

- Fuente limpia: `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`
- Registros fuente limpios: 371,513
- Registros CEO generados: 371,501
- Registros omitidos por falta de futuro: 12
- Simbolo: `EURUSD`
- Timeframe base: `M5`
- Periodo: `2020-01-15T00:00:00Z` a `2026-04-14T23:55:00Z`
- Horizontes: H12, H48, H96, H288 barras M5
- Umbral flat: 3.0 pips
- Melchor/Baltasar/Gaspar en modo `real`
- Snapshots invalidos: 0
- Parse errors: 0

Conteo de votos:

- Melchor `APPROVE`: 232,316
- Melchor `BLOCK`: 139,185
- Baltasar `BUY`: 106,395
- Baltasar `SELL`: 127,484
- Baltasar `NEUTRAL`: 137,622
- Gaspar `GOOD`: 72,784
- Gaspar `FAIR`: 278,606
- Gaspar `POOR`: 20,111

## Campos Disponibles

Cada registro CEO contiene:

- `schema_version`
- `snapshot_id`
- `symbol`
- `timestamp`
- `anchor_bar_timestamp`
- `features_at_decision_time`
- `melchor_vote`
- `baltasar_vote`
- `gaspar_vote`
- `future_outcomes`
- `leakage_guard`

### Votos y confianza

Los votos usan contrato `MageVote`:

- `agent`
- `agent_version`
- `vote`
- `direction`
- `quality`
- `confidence`
- `risk_flag`
- `context_tag`
- `features_used`
- `reason`

Interpretacion actual:

- Melchor: `vote` = `APPROVE` o `BLOCK`.
- Baltasar: `direction` = `BUY`, `SELL` o `NEUTRAL`.
- Gaspar: `quality` = `GOOD`, `FAIR` o `POOR`.

### Features disponibles en tiempo de decision

En `features_at_decision_time` hay:

- OHLC M5: `open`, `high`, `low`, `close`, `current_price`.
- Operativa: `spread_pips`, `active_session`, `account`.
- Features tecnicas del snapshot: `features`.
- Contexto Gaspar: `gaspar_context`.
- Contexto H4/D1: `higher_timeframe_confluence`.
- Timing: `daily_atr_consumed_pct`, `available_range_to_next_level`, `h4_candle_pattern`.
- Dia: `day_of_week`, `d1_volatility_vs_20d_avg`, `current_d1_range_vs_atr`.
- Estructura: `h4_structure`, `d1_structure`, `directional_alignment`.
- Posicion en rango: `distance_to_d1_support`, `distance_to_d1_resistance`, `near_key_level`, `position_in_d1_range`.
- Metadatos: `source_file`, `source_line`.

El dataset limpio de Bot A sub3 tambien tiene columnas utiles antes de entrar a CEO:

- `is_high_spread`
- `has_gap_forward`
- `market_structure`
- `momentum`
- `mtf_alignment_status`
- `mtf_data_source_status`
- `recent_range`
- `rsi_14`
- `structure_direction`
- features M15/H1/H4/D1 en lista.

Advertencia: algunas de estas features del dataset limpio no quedan completamente aplanadas en `features_at_decision_time`, porque el generador actual conserva `snapshot.features` segun la normalizacion de `simulator.loaders`. El primer paso tecnico debe confirmar y aplanar explicitamente el conjunto final de features.

### Outcomes disponibles

`future_outcomes` incluye H12, H48, H96 y H288:

- `future_return`
- `future_return_pips`
- `future_timestamp`
- `horizon_bars`
- `max_favorable_excursion`
- `max_adverse_excursion`
- `proposed_direction`
- `reached_down_pips`
- `reached_up_pips`
- `real_direction`

H48 ya aparece como horizonte principal en los analisis existentes. Es una buena primera etiqueta operativa, manteniendo H12/H96/H288 como validaciones secundarias.

## Estado De Documentacion

Documentacion relevante existente:

- `docs/10_ceo_magi.md`: rol y contrato conceptual de CEO-MAGI.
- `docs/14_data_contracts.md`: contratos de datos.
- `docs/20_python_simulator_plan.md`: plan del simulador Python.
- `docs/simulator_plan.md`: plan amplio del simulador.
- `docs/simulator_real_mages_integration.md`: integracion con magos reales.
- `docs/ceo_dataset_generation.md`: generacion del dataset CEO.
- `docs/ceo_magi_training_methodology.md`: metodologia inicial de entrenamiento.
- `docs/magi_signal_analysis.md`: analisis de senales.
- `docs/magi_monthly_analysis.md`: analisis mensual.
- `docs/magi_full_dataset_results.md`: resultados del dataset completo.
- `docs/magi_retraining_strategy.md`: estrategia futura de reentrenamiento.

Estado: la documentacion cubre bien generacion, auditoria y lectura metodologica. Falta convertirla en un pipeline reproducible de entrenamiento/evaluacion de CEO con artefactos versionados, split temporal fijo, metricas de trading con abstencion y reporte ejecutivo automatico.

## Hallazgos Tecnicos

Los votos aislados no son suficientes como politica operativa. En H48:

- Baltasar BUY tiene hit rate aproximado de 45.13% y avg net direccional de 1.0789 pips.
- Baltasar SELL tiene hit rate aproximado de 44.15% y avg net direccional positivo de 0.6176 pips al medirlo direccionalmente.
- BUY+GOOD mejora a 47.73% y 3.0409 pips promedio, pero con solo 2,066 casos.
- SELL+GOOD queda cerca de 44.51% y 0.3073 pips promedio, con 68,608 casos.

La senal aparece por regimen, no globalmente. El analisis de regimen encuentra segmentos H48 muy positivos y muy negativos por mes, hora, rango M5, estructura H4/D1, ATR consumido y posicion en rango D1. Esto confirma que CEO-MAGI debe ser un selector de contexto, no un predictor direccional puro.

## Que Falta Para Entrenar En Serio

Falta implementar, sin cambiar contratos ni logica de magos:

1. Dataset final aplanado para CEO.
2. Definicion formal de label `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.
3. Split temporal reproducible.
4. Baselines comparables.
5. Modelo baseline entrenable y persistible.
6. Evaluacion con abstencion y costos.
7. Validacion walk-forward.
8. Reporte ejecutivo automatico.
9. Auditoria de leakage post-flattening.
10. Registro de artefactos: config, features, labels, modelo, metricas y reporte.

## Arquitectura Propuesta

### A. Construccion Del Dataset Final CEO

Crear un nuevo modulo, por ejemplo:

- `simulator/ceo_dataset_final.py`
- `scripts/build_ceo_final_dataset.py`

Entrada:

- `data/output/ceo_training/<run_id>/ceo_training_records.jsonl`

Salida propuesta:

- `data/output/ceo_training/<run_id>/final/ceo_features.parquet`
- `data/output/ceo_training/<run_id>/final/ceo_labels.parquet`
- `data/output/ceo_training/<run_id>/final/feature_manifest.json`
- `data/output/ceo_training/<run_id>/final/label_manifest.json`
- `data/output/ceo_training/<run_id>/final/dataset_audit.md`

Transformaciones:

- Aplanar votos: Melchor, Baltasar, Gaspar, confidence, risk flags, context tags.
- Aplanar regimen: sesion, hora UTC, dia, mes, spread bucket, rango M5, estructura H4/D1, alignment, ATR consumido, posicion rango D1.
- Aplanar mercado observable: OHLC, spread, cuenta, flags de calidad disponibles.
- Codificar categoricas con transformador ajustado solo en train.
- Mantener `timestamp`, `snapshot_id`, `symbol` como columnas de auditoria, no como features directas salvo features temporales controladas.
- Excluir `future_outcomes`, retornos, MFE/MAE, labels y cualquier campo prohibido del bloque de features.

Label inicial recomendado:

- Si Baltasar `BUY` y outcome H48 direccional supera umbral neto/riesgo: candidato `ENTER_BUY`.
- Si Baltasar `SELL` y outcome H48 direccional supera umbral neto/riesgo: candidato `ENTER_SELL`.
- Todo lo demas: `DO_NOTHING`.

Condicion conservadora para label positivo:

- Melchor no debe estar `BLOCK`.
- Baltasar debe ser direccional.
- H48 debe tener net directional pips positivo despues de costo estimado.
- MAE no debe exceder un limite razonable frente a MFE o frente al SL virtual.
- H12 no debe mostrar deterioro extremo temprano.

Esto debe parametrizarse. No conviene hardcodear un unico umbral antes de medir sensibilidad.

### B. Train/Validation/Test Split

No usar split aleatorio simple.

Split inicial fijo recomendado:

- Train: `2020-01-15` a `2023-12-31`
- Validation: `2024-01-01` a `2024-12-31`
- Test final: `2025-01-01` a `2026-04-14`

Reglas:

- Ajustar imputacion, encoding, escalado y seleccion de features solo con train.
- Usar validation para umbrales de decision y calibracion.
- Usar test una sola vez para reporte final.
- Reportar resultados por ano, mes, sesion, direccion y cobertura.

### C. Baseline Model

Baselines obligatorios:

- `DO_NOTHING_ALWAYS`: cobertura 0%, sirve como baseline de riesgo.
- `RULE_BASED_CURRENT`: replica CEO actual: Melchor approve/warn, Baltasar direccional, Gaspar GOOD/FAIR, no POOR.
- `BALTASAR_ONLY`: operar toda senal BUY/SELL sin Gaspar.
- `BALTASAR_GASPAR_GOOD`: operar solo BUY/SELL con Gaspar GOOD.
- `SEGMENT_LOOKUP_BASELINE`: tabla conservadora de segmentos train con minimo de casos y EV positivo, validada fuera de muestra.

Modelo baseline recomendado:

- `HistGradientBoostingClassifier` o `RandomForestClassifier` como primer modelo tabular.
- Alternativa conservadora: `LogisticRegression` multinomial con regularizacion y features bien codificadas.
- Entrenar probabilidad de 3 clases: `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.
- Aplicar umbral operacional: entrar solo si probabilidad y EV estimado superan umbrales definidos en validation.

No promover un modelo por accuracy. Un modelo que diga `DO_NOTHING` casi siempre puede tener buen accuracy si las clases positivas son raras.

### D. Metricas

Metricas principales:

- Precision en trades: precision solo sobre `ENTER_BUY` y `ENTER_SELL`.
- EV por trade: promedio de pips direccionales o R esperado neto de costos.
- Drawdown: max drawdown sobre curva de trades seleccionados.
- Coverage: porcentaje de snapshots donde CEO opera.
- F1 macro: metrica secundaria para evitar ignorar clases minoritarias.

Metricas adicionales:

- Precision por clase: BUY y SELL separados.
- Recall de oportunidades, solo como diagnostico.
- Profit factor o win/loss pips.
- Avg MAE y p95 MAE de trades seleccionados.
- Estabilidad mensual: meses positivos vs negativos.
- Concentracion: cuanto depende el resultado de pocos meses.
- Calibration: reliability por bins de probabilidad.
- Lift vs baselines: EV, precision y drawdown.

Evaluacion operativa:

- Una prediccion `DO_NOTHING` no debe contarse igual que un acierto direccional.
- Accuracy global debe quedar como metrica informativa menor.
- El reporte debe separar "clasificacion" de "politica operativa".

### E. Validacion Walk-Forward Futura

Implementar despues del split inicial fijo.

Esquema recomendado:

- Train rolling o expanding de 18 a 36 meses.
- Validation de 3 meses.
- Test forward de 3 meses.
- Avance de ventana de 3 meses.
- Repetir hasta 2026-04.

Por ventana reportar:

- coverage
- precision trades
- EV/trade
- max drawdown
- F1 macro
- meses positivos/negativos
- mejores/peores regimenes
- drift de features y distribucion de votos

Criterio de promocion:

- EV positivo en test forward agregado.
- Drawdown aceptable.
- No depender de un unico ano, mes o regimen.
- Coverage suficiente para que la muestra sea estadisticamente util.
- Lift claro contra `RULE_BASED_CURRENT`.

### F. Reporte Ejecutivo

Crear reporte automatico por corrida:

- `reports/ceo_magi_training/<timestamp>_executive_report.md`
- opcional PDF despues de estabilizar el Markdown.

Contenido:

- Dataset usado y periodo.
- Definicion de label y costos.
- Split temporal.
- Baselines.
- Modelo entrenado.
- Tabla de metricas train/validation/test.
- Curva de equity o pips acumulados en test.
- Drawdown.
- Coverage.
- Precision BUY/SELL.
- F1 macro.
- Analisis por regimen.
- Analisis por mes.
- Top errores: entradas malas y abstenciones perdidas.
- Decision ejecutiva: no promover / seguir investigando / candidato a demo.

## Implementacion Recomendada Por Fases

### Fase 1: Dataset final y auditoria

Crear el flattening final, manifiestos y auditoria de leakage. No entrenar todavia.

Entregables:

- Dataset tabular.
- Manifiesto de features.
- Manifiesto de labels.
- Conteos por clase y periodo.
- Pruebas unitarias de leakage.

### Fase 2: Baselines

Implementar baselines sin ML para establecer el piso real.

Entregables:

- Comparacion de `RULE_BASED_CURRENT`, `BALTASAR_ONLY`, `BALTASAR_GASPAR_GOOD`, `SEGMENT_LOOKUP_BASELINE`.
- Metricas operativas en train/validation/test.

### Fase 3: Modelo baseline

Entrenar un primer modelo tabular con umbrales calibrados en validation.

Entregables:

- Modelo persistido.
- Pipeline de preprocesamiento persistido.
- Metricas y reporte ejecutivo.

### Fase 4: Walk-forward

Validar estabilidad temporal real antes de cualquier demo.

Entregables:

- Reporte por ventanas.
- Resumen agregado.
- Decision de promocion o rechazo.

## Archivos Encontrados

Archivos clave de codigo:

- `run_simulation.py`
- `config/simulator_v01.yaml`
- `magi/contracts.py`
- `magi/ceo_magi.py`
- `magi/adapters/melchor_real_adapter.py`
- `magi/adapters/baltasar_real_adapter.py`
- `magi/adapters/gaspar_real_adapter.py`
- `simulator/ceo_training_dataset.py`
- `simulator/ceo_vote_analysis.py`
- `simulator/ceo_individual_vote_analysis.py`
- `simulator/ceo_monthly_vote_analysis.py`
- `simulator/ceo_regime_analysis.py`
- `simulator/execution.py`
- `simulator/metrics.py`
- `simulator/loaders.py`
- `simulator/validation.py`

Datos clave:

- `data/clean/bot_a_sub3_full/cleaned_dataset.jsonl`
- `data/clean/bot_a_sub3_full/cleaned_dataset_summary.json`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_training_records.jsonl`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_training_summary.json`
- `data/output/ceo_training/20260429T141153Z_magi_v01_phase2/ceo_regime_analysis.md`

Docs clave:

- `docs/ceo_dataset_generation.md`
- `docs/ceo_magi_training_methodology.md`
- `docs/magi_signal_analysis.md`
- `docs/magi_monthly_analysis.md`
- `docs/magi_full_dataset_results.md`
- `docs/magi_retraining_strategy.md`

## Datos Listos

- Dataset limpio Bot A sub3 de 371,513 snapshots.
- Dataset CEO de 371,501 registros.
- Votos reales de Melchor, Baltasar y Gaspar por snapshot.
- Confidence, risk flags, context tags y features usadas por mago.
- Features observables de decision y contexto Gaspar H4/D1.
- Outcomes H12/H48/H96/H288.
- Leakage guard basico por nombres prohibidos.
- Analisis descriptivos por voto, mes y regimen.

## Datos Faltantes

- Dataset final aplanado y estable para ML.
- Label operacional final de 3 clases.
- Costos operativos explicitos: spread/comision/slippage.
- Definicion formal de EV en pips o R.
- Curva de equity para politica CEO entrenada.
- Drawdown de politicas candidatas.
- Manifest de features con tipos y origen.
- Auditoria de transformadores para evitar leakage.
- Resultados por split temporal fijo.
- Walk-forward reproducible.
- Reporte ejecutivo de entrenamiento.

## Recomendacion Principal

Implementar primero `build_ceo_final_dataset`: aplanar features, construir labels conservadores y generar auditoria. Sin ese paso, entrenar seria prematuro porque el modelo podria optimizar una definicion inestable de oportunidad o mezclar campos que no deben entrar como features.

Despues, correr baselines sin ML. Solo si los baselines muestran una politica evaluable y las metricas estan bien instrumentadas, pasar al primer modelo baseline.

## Pruebas Recomendadas

- Prueba de schema: todo registro CEO requerido tiene votos, features, outcomes y leakage guard.
- Prueba de flattening: columnas esperadas, tipos estables y sin columnas prohibidas.
- Prueba de leakage: ninguna feature contiene `future`, `outcome`, `pnl`, `mfe`, `mae`, `target`, `label`, `forward_return`, `hit_tp`, `hit_sl`.
- Prueba de split temporal: train, validation y test no se solapan y mantienen orden cronologico.
- Prueba de labels: BUY/SELL/DO_NOTHING se derivan solo de outcomes y reglas parametrizadas, nunca de features futuras.
- Prueba de baselines: replicas deterministas de reglas actuales producen conteos esperados.
- Prueba de metricas: precision trades, EV, drawdown, coverage y F1 macro con fixtures pequenos.
- Prueba de reproducibilidad: misma config produce mismos manifests y conteos.
- Prueba de reporte: el Markdown ejecutivo se genera aun si algun modelo tiene coverage cero.
