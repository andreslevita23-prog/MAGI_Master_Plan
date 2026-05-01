# Gaspar v2.1 Regime Redesign Plan

## 1. Diagnóstico: por qué falló Gaspar v2 trade-level

Gaspar v2 fue entrenado como clasificador trade-by-trade con target `context_quality_rr2`:

- `FAVORABLE`: trade individual con R positivo.
- `UNFAVORABLE`: trade individual con R negativo.
- `NEUTRAL`: R cerca de cero o ambiguo.

El resultado no fue suficientemente operativo:

| Split | Accuracy | Macro F1 | Precision UNFAVORABLE | Recall UNFAVORABLE |
| --- | ---: | ---: | ---: | ---: |
| Validation | 0.4625 | 0.3475 | 0.6152 | 0.3632 |
| Test | 0.4415 | 0.3232 | 0.5883 | 0.3576 |

Como filtro sobre Baltasar v2 `rich_policy_medium 0.40`, Gaspar v2 no mejoró test:

| Bloqueo | Avg R original | Avg R filtrado | PF original | PF filtrado | Max DD original | Max DD filtrado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P(UNFAVORABLE) >= 0.50 | 0.0932 | 0.0879 | 1.1621 | 1.1537 | 266.14 | 251.91 |
| P(UNFAVORABLE) >= 0.60 | 0.0932 | 0.0897 | 1.1621 | 1.1562 | 266.14 | 263.14 |
| P(UNFAVORABLE) >= 0.70 | 0.0932 | 0.0930 | 1.1621 | 1.1617 | 266.14 | 266.14 |

En `2026Q2`, que era el régimen que más queríamos detectar, el filtro tampoco ayudó. Con `P(UNFAVORABLE) >= 0.50`, empeoró de `Avg R -0.0572 / PF 0.9003` a `Avg R -0.0879 / PF 0.8481`.

Conclusión: Gaspar v2 trade-level no debe pasar a integración CEO.

## 2. Por qué `FAVORABLE/UNFAVORABLE` individual es ruidoso

El resultado de un trade individual mezcla demasiadas cosas:

- Dirección de Baltasar.
- Timing exacto de entrada.
- Ruido local M5.
- Secuencia intrabar TP/SL.
- Proximidad a soporte/resistencia.
- Volatilidad inmediata.
- Régimen macro del día o semana.
- Azar operativo inevitable dentro de una muestra de trades.

Esto hace que un label por trade convierta a Gaspar en un segundo clasificador de resultado, no en un especialista de contexto. Gaspar no debería aprender si un trade aislado gana o pierde. Debe aprender si el entorno donde Baltasar está operando es estructuralmente favorable, neutro o peligroso.

El target individual también castiga contextos buenos con pérdidas normales y premia contextos malos donde un trade puntual ganó. Para un mago de régimen, esa señal es demasiado granular.

## 3. Nuevo objetivo de Gaspar v2.1

Gaspar v2.1 debe ser rediseñado como detector de régimen/contexto.

Objetivos:

- Detectar contextos donde Baltasar v2 tiende a tener EV positivo.
- Detectar contextos donde Baltasar v2 tiende a perder, aunque algunos trades aislados ganen.
- Detectar SELL malo como subproblema específico.
- Detectar deterioros tipo `2026Q2` antes de que el CEO aumente exposición.
- Producir señales útiles para CEO-MAGI:
  - `REINFORCE`
  - `CAUTION`
  - `BLOCK`

Gaspar v2.1 no debe predecir dirección. La dirección sigue siendo responsabilidad de Baltasar.

## 4. Propuesta de labels

### A. `context_block_rr2`

Label binario o ternario orientado a bloqueo:

- `BLOCK`: el segmento/región tiene PF bajo, Avg R negativo, DD alto o concentración de pérdidas.
- `ALLOW`: el segmento/región tiene PF positivo y estabilidad razonable.
- `CAUTION`: muestra baja, resultados mixtos o deterioro moderado.

Uso principal: política operacional simple para CEO.

Regla inicial sugerida:

- `BLOCK` si en el segmento agregado:
  - `avg_R < 0`, o
  - `PF < 1.00`, o
  - `max_DD` relativo al total R es excesivo, o
  - SELL en ese contexto es negativo y domina la pérdida.
- `ALLOW` si:
  - `avg_R > 0.05`,
  - `PF > 1.10`,
  - muestra suficiente,
  - comportamiento estable en validation/test.
- `CAUTION` para el resto.

### B. `regime_quality_bucket`

Label ordinal de calidad de régimen:

- `STRONG_POSITIVE`
- `POSITIVE`
- `MIXED`
- `NEGATIVE`
- `DANGEROUS`

Uso principal: dar granularidad al CEO y permitir thresholds de exposición.

Regla inicial sugerida:

- `STRONG_POSITIVE`: PF >= 1.20 y Avg R >= 0.10.
- `POSITIVE`: PF >= 1.05 y Avg R > 0.
- `MIXED`: PF entre 0.95 y 1.05 o Avg R cerca de cero.
- `NEGATIVE`: PF < 0.95 o Avg R < 0.
- `DANGEROUS`: PF < 0.85, Avg R negativo y DD elevado.

### C. `sell_risk_context`

Label especializado para el problema SELL:

- `SELL_BLOCK`
- `SELL_CAUTION`
- `SELL_OK`

Uso principal: permitir que Gaspar bloquee o degrade solo SELL en contextos donde BUY aún puede funcionar.

Regla inicial sugerida:

- `SELL_BLOCK` si SELL agregado tiene Avg R < 0 o PF < 1.00 con muestra suficiente.
- `SELL_CAUTION` si SELL tiene PF entre 1.00 y 1.10, DD alto o baja muestra.
- `SELL_OK` si SELL tiene PF >= 1.10 y Avg R positivo estable.

## 5. Cómo agregar labels de régimen

Gaspar v2.1 debe construir labels agregados antes de volver a asignarlos a cada fila. La fila individual recibe el label del contexto al que pertenece.

Agregaciones recomendadas:

### Buckets temporales suaves

- `hour_bucket`, no hora exacta:
  - `asia_core`
  - `london_open`
  - `london_mid`
  - `overlap`
  - `new_york_mid`
  - `late_us`
  - `inactive`

### Buckets de rango y volatilidad

- `daily_range_bucket`:
  - `low`
  - `mid_low`
  - `mid`
  - `mid_high`
  - `extreme_high`

- `atr_bucket`:
  - por cuantiles rolling o cuantiles train-only.

### Estructura y multi-timeframe

Agrupar por:

- `market_structure`
- `structure_direction`
- `h4_market_structure`
- `h4_structure_direction`
- `d1_market_structure`
- `d1_structure_direction`
- `mtf_alignment_status`
- `htf_directional_alignment`

### Dirección predicha

Incluir `prediction` como dimensión de agregación diagnóstica, no como feature cruda si el modelo final debe ser puramente contextual.

Para `sell_risk_context`, sí se debe calcular métrica separada para `ENTER_SELL`.

### Ventanas móviles

Agregar métricas rolling por ventanas temporales:

- 1 mes.
- 1 trimestre.
- 3 meses móviles.
- 6 meses móviles.

Ejemplos de features/labels agregados:

- `rolling_pf_3m_context`
- `rolling_avg_r_3m_context`
- `rolling_dd_3m_context`
- `rolling_sell_pf_3m_context`
- `context_sample_size_3m`

Importante: las ventanas rolling deben ser causales. Para una fila en tiempo `t`, solo se puede usar información anterior a `t`. No usar datos futuros del mismo mes/trimestre para generar features.

## 6. Métricas de evaluación

Gaspar v2.1 no debe evaluarse principalmente por accuracy.

Métricas principales:

- Mejora de PF al bloquear.
- Reducción de max DD.
- Avg R filtrado vs original.
- Total R retenido.
- Trades bloqueados buenos vs malos.
- Porcentaje de pérdidas bloqueadas.
- Porcentaje de ganancias sacrificadas.
- Estabilidad validation/test.
- Estabilidad por año/trimestre/mes.
- Impacto separado en BUY y SELL.
- Impacto específico en `2026Q2`.

Métrica clave de bloqueo:

| Métrica | Pregunta |
| --- | --- |
| Bad trades blocked | ¿Bloquea pérdidas reales? |
| Good trades blocked | ¿Sacrifica demasiados ganadores? |
| PF filtered | ¿Mejora el profit factor? |
| DD filtered | ¿Reduce drawdown? |
| Coverage retained | ¿Deja suficientes trades? |
| Validation/test stability | ¿Funciona fuera de muestra? |

## 7. Scripts existentes reutilizables

Reutilizar:

- `scripts/magi_v2/build_gaspar_v2_dataset_full.py`
  - Fuente completa 2020-2026.
  - Scoring de Baltasar rich model.
  - Aplicación de `rich_policy_medium 0.40`.
  - Unión con RR2 first-touch labels.

- `scripts/magi_v2/train_gaspar_v2_context_classifier_full.py`
  - Preprocessing.
  - Split temporal.
  - Evaluación de filtro.
  - Métricas de PF/DD/Avg R.

- `scripts/magi_v2/simulate_baltasar_v2_policy_medium_r.py`
  - Cálculo de R, PF, DD y métricas por dirección.

- `scripts/magi_v2/evaluate_baltasar_v2_rich_policy.py`
  - Definición original de `rich_policy_medium`.
  - Bad hours y reglas de bloqueo.

- `data/output/magi_v2/gaspar_v2_dataset_full/gaspar_v2_dataset_full.parquet`
  - Base reconstruida completa para generar labels agregados.

## 8. Próximo script recomendado

Crear:

`scripts/magi_v2/build_gaspar_v2_1_regime_dataset.py`

Output recomendado:

`data/output/magi_v2/gaspar_v2_1_regime_dataset/`

Archivos:

- `gaspar_v2_1_regime_dataset.parquet`
- `gaspar_v2_1_regime_dataset.csv`
- `train.parquet`
- `validation.parquet`
- `test.parquet`
- `gaspar_v2_1_regime_dataset_summary.json`
- `gaspar_v2_1_regime_dataset_summary.md`

Columnas objetivo:

- `context_block_rr2`
- `regime_quality_bucket`
- `sell_risk_context`

El primer target a probar debe ser:

`context_block_rr2`

Razón:

- Está alineado con el rol de Gaspar como `BLOCK / CAUTION / ALLOW`.
- Es más fácil de evaluar operacionalmente.
- Se conecta directamente con CEO-MAGI.
- Permite medir si bloquear mejora PF/DD sin exigir que Gaspar prediga cada trade individual.

## 9. Recomendación

Sí, se recomienda abandonar Gaspar v2 trade-level como candidato de integración.

No se recomienda abandonar las features ni la idea de Gaspar. El problema está en el target, no necesariamente en los datos.

La siguiente fase debe construir Gaspar v2.1 como detector de régimen usando labels agregados y evaluación por bloqueo operacional.

Ruta recomendada del próximo dataset:

`data/output/magi_v2/gaspar_v2_1_regime_dataset/gaspar_v2_1_regime_dataset.parquet`

