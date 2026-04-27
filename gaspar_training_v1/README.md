# Gaspar Training Lab v1

Gaspar evalua calidad de oportunidad de entrada. No predice direccion; responde si una direccion propuesta tiene suficiente calidad estructural y temporal para ejecutarse.

## Proposito

Gaspar produce un voto operativo:

- `GOOD`: entrada de buena calidad.
- `FAIR`: entrada posible, pero con friccion o contexto incompleto.
- `POOR`: entrada de baja calidad o mal momento.

El modelo trabaja solo con estructura de precio y contexto temporal: estructura H4/D1, posicion dentro del rango D1, cercania a niveles, sesion, rango disponible y contexto diario.

## Diferencia con Baltasar

Baltasar puede proponer direccion en operacion, pero Gaspar no recibe confianza, probabilidades, features ni indicadores de Baltasar. Gaspar solo recibe `proposed_direction` (`BUY`, `SELL`, `NEUTRAL`) y evalua si esa propuesta tiene buen momento de ejecucion.

Durante entrenamiento, si no existe una direccion real externa, `proposed_direction` se genera como proxy heuristico usando solo estructura H4/D1:

- D1 bullish y H4 no bearish: `BUY`
- D1 bearish y H4 no bullish: `SELL`
- D1 range o conflicto fuerte H4/D1: `NEUTRAL`

## Diferencia con Melchor

Melchor gobierna riesgo y seguridad. Puede vetar operaciones aunque Gaspar vote `GOOD`. Gaspar solo califica oportunidad; no calcula riesgo maximo, tamano de posicion ni permisos finales.

## Flujo de entrenamiento

1. `Bot_A_sub2.mq5` exporta snapshots estructurales y temporales en CSV/JSONL.
2. `run_training.py` carga los archivos desde una carpeta.
3. El pipeline limpia datos, construye features y crea un target provisional versionado.
4. Se entrena un baseline simple y se valida con split temporal y walk-forward.
5. Se guardan metricas, figuras, modelo y reporte.
6. `run_diagnostics.py` audita distribucion de clases, columnas y datos faltantes.

## Datos esperados

El contrato base vive en `contracts/gaspar_input_example.json`. Los campos principales son:

- `module`, `role`, `symbol`, `timestamp`
- `proposed_direction`
- `higher_timeframe_confluence`
- `price_structure_position`
- `timing_quality`
- `day_context`
- `target` opcional

Si el dataset no trae target, el pipeline crea `score_oportunidad` y `voto` con la heuristica inicial documentada.

## Ejecutar

```bash
cd gaspar_training_v1
pip install -r requirements.txt
python run_training.py --data-path data --target-version v2
python run_diagnostics.py --data-path data --target-version v2
```

Tambien puedes apuntar a la carpeta exportada por MT5:

```bash
python run_training.py --data-path "C:\Users\Public\AppData\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub2" --target-version v2
```

## Outputs

- `artifacts/models/gaspar_baseline.joblib`
- `artifacts/metrics/gaspar_metrics.json`
- `artifacts/metrics/gaspar_walk_forward.csv`
- `artifacts/figures/gaspar_confusion_matrix.png`
- `artifacts/figures/gaspar_class_distribution.png`
- `reports/gaspar_training_report.md`
- `reports/gaspar_diagnostics_report.md`

## Targets provisionales

Los targets usan cuatro pilares:

- `higher_timeframe_confluence`: 0.40
- `price_structure_position`: 0.30
- `timing_quality`: 0.20
- `day_context`: 0.10

Versiones actuales:

- `v1`: heuristica inicial historica.
- `v2`: baseline oficial actual para Gaspar. En la auditoria de 24 meses obtuvo F1 macro 0.8912, accuracy 0.8809 y walk-forward medio 0.8665.
- `v3`: experimento intermedio conservado para trazabilidad.
- `v4`: challenger experimental; discretiza el contexto de rango diario con `daily_range_state` (`EARLY`, `MID`, `LATE`) y excluye `current_d1_range_vs_atr_capped` del entrenamiento v4. En 24 meses obtuvo F1 macro 0.8903, accuracy 0.8949 y walk-forward medio 0.8816.

La decision actual es mantener `v2` como baseline oficial y conservar `v4` como challenger hasta validar impacto economico con resultados reales registrados por Bot C.

## Operacion futura

Cuando Gaspar pase de entrenamiento a operacion, Bot A principal debera incluir un bloque separado `gaspar_context` con los datos estructurales y temporales necesarios para Gaspar, incluyendo `proposed_direction` si viene de un modulo externo. Ese bloque no debe mezclar confianza, probabilidades, features ni indicadores de Baltasar.
