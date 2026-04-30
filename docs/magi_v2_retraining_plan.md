# MAGI v2 Retraining Plan

## Objetivo

Este documento define el plan tecnico para reentrenar Baltasar, Gaspar y Melchor v2 usando los hallazgos de CEO-MAGI v2:

- target `ceo_label_h48_tradeable`
- analisis por segmentos
- policy audit
- walk-forward policy
- simulacion proxy R/SL/TP/costos

No se entrena ningun modelo en esta fase.

## 1. Diagnostico Actual

CEO v1 fallo como modelo de arbitraje porque su target `ceo_label_h48` estaba demasiado acoplado a `baltasar_signal`. El RandomForest v1 replico `baltasar_only`, sin aprender abstencion contextual real.

CEO v2 corrigio parte del problema usando `ceo_label_h48_tradeable`. El modelo ya no colapso a `DO_NOTHING` y aprendio filtros contextuales utiles:

- Melchor `APPROVE`
- Gaspar no `POOR`
- sesiones operables
- rango D1 no extremo
- alineacion y calidad contextual
- umbral probabilistico

La politica `conservative_core` mejoro contra Baltasar/CEO v1 cuando se evalua contra el target tradeable:

- `baltasar_only` y CEO v1 sobre target tradeable quedaron cerca de 10-11% de precision de trades.
- CEO v2 con threshold `0.70` y filtros core quedo alrededor de 25-29% de precision de trades en validation/test.
- En walk-forward, la politica mantiene estabilidad razonable anual/trimestral, con precision global de trades cercana a 26.95%.

Pero la simulacion proxy R/SL/TP/costos no valida rentabilidad bajo escenario conservador:

- RR 1:1 conservative: `avg R -0.2337`, PF `0.6049`, max DD `6102.31R`.
- RR 1:1.5 conservative: `avg R -0.1244`, PF `0.7909`, max DD `3512.79R`.
- RR 1:2 conservative: `avg R -0.0407`, PF `0.9317`, max DD `1720.60R`.

RR 1:2 es el perfil mas prometedor porque reduce ambiguedad y acerca el EV proxy a cero, pero todavia no es positivo en el escenario conservador.

El problema principal es la ambiguedad TP/SL dentro de H48. La misma politica se ve muy positiva en escenario optimista y negativa en escenario conservador. Eso significa que el resultado depende demasiado del orden intrabar, dato que actualmente no esta disponible como `first_touch`.

Conclusion del diagnostico: CEO v2 aprendio abstencion contextual, pero MAGI todavia no tiene senales suficientemente operables para declarar ventaja en R. Antes de reentrenar fuerte, hay que mejorar la simulacion o construir labels RR 1:2 mucho mas fieles.

## 2. Reentrenamiento De Baltasar v2

### Objetivo

Baltasar v2 debe mejorar la senal direccional operable, no solo predecir direccion futura.

El objetivo no debe ser:

```text
BUY / SELL / NEUTRAL segun future_return_h48
```

El objetivo debe acercarse a:

```text
direccion que puede convertirse en operacion con EV proxy positivo bajo RR 1:2
```

### Target Sugerido

Primera opcion:

`tradeable_direction_rr2`

Clases:

- `BUY_TRADEABLE`
- `SELL_TRADEABLE`
- `NO_DIRECTION`

Regla base propuesta:

- BUY si una operacion BUY con SL 10 / TP 20 tiene resultado favorable en simulacion proxy RR 1:2.
- SELL si una operacion SELL con SL 10 / TP 20 tiene resultado favorable en simulacion proxy RR 1:2.
- NO_DIRECTION si no hay ventaja clara, hay ambiguedad excesiva, o el MAE/MFE no justifica operacion.

Segunda opcion:

`expected_R_proxy`

Target de regresion o ranking:

- valor continuo de R proxy por direccion
- permite optimizar ranking/score antes de discretizar decision

### Datos A Usar

Disponibles ahora:

- `future_return_pips`
- `max_favorable_excursion`
- `max_adverse_excursion`
- `reached_up_pips`
- `reached_down_pips`
- `spread`
- direccion propuesta
- features tecnicas historicas de Bot A / Baltasar

Necesario evitar:

- labels acoplados a direccion simple
- usar `real_direction` como unica verdad
- mezclar features futuras en entrenamiento

### Metricas

- precision en trades direccionales
- avg R proxy
- total R proxy
- profit factor
- max drawdown en R
- coverage
- precision BUY y SELL separadas
- estabilidad anual/trimestral/mensual

### Criterio De Exito

Baltasar v2 debe producir menos senales, pero mas operables. Si aumenta accuracy direccional pero no mejora R proxy, no sirve para CEO-MAGI.

## 3. Reentrenamiento De Gaspar v2

### Objetivo

Gaspar v2 debe clasificar contexto operable/no operable. No debe votar direccion.

Su tarea correcta:

```text
calidad del contexto para ejecutar una senal direccional externa
```

### Problema A Resolver

CEO v2 mostro que ciertos contextos son peligrosos:

- D1 range position alto (`> 0.85`)
- meses/regimenes de baja esperanza
- regimenes con alta ambiguedad TP/SL
- algunos tramos de `h4_range/d1_range` con d1pos alto

Gaspar v2 debe aprender a detectar estos contextos antes de que CEO tenga que compensar todo.

### Target Sugerido

Primera opcion:

`context_quality_rr2`

Clases:

- `GOOD`
- `FAIR`
- `POOR`

Definicion aproximada:

- GOOD: contexto con EV proxy positivo o precision tradeable alta bajo RR 1:2.
- FAIR: contexto incierto, suficiente para cautela.
- POOR: contexto con alta ambiguedad, bajo PF, alto drawdown o mala precision.

Segunda opcion:

`ambiguity_risk`

Clases:

- `LOW_AMBIGUITY`
- `MEDIUM_AMBIGUITY`
- `HIGH_AMBIGUITY`

Esto es clave porque la brecha conservative vs optimistic viene de operaciones donde TP y SL pudieron tocarse dentro de H48.

### Features

- session
- ATR bucket
- daily_range_position
- H4 structure
- D1 structure
- directional_alignment
- volatility
- spread
- available range to next level
- day_of_week
- current D1 range vs ATR
- distance to D1 support/resistance

### Salida

Gaspar v2 debe mantener salida de calidad/contexto:

- `GOOD`
- `FAIR`
- `POOR`

No debe votar BUY/SELL.

### Metricas

- lift de precision de trades al filtrar por GOOD/FAIR
- tasa de ambiguedad por clase
- avg R proxy por clase
- PF por clase
- drawdown por clase
- estabilidad temporal

## 4. Reentrenamiento De Melchor v2

### Objetivo

Melchor v2 debe seguir siendo riesgo operativo. No predice precio.

Debe aprender y/o formalizar bloqueos por:

- spread extremo
- MAE esperado alto
- drawdown esperado alto
- ambiguedad TP/SL
- rangos extremos
- sesiones bloqueadas
- condiciones de cuenta
- posible riesgo de noticias/eventos cuando exista

### Target Sugerido

`risk_block_rr2`

Clases:

- `APPROVE`
- `CAUTION`
- `BLOCK`

Regla base:

- BLOCK si el contexto historico muestra alto riesgo de SL, alta ambiguedad, drawdown extremo o spread no operable.
- CAUTION si el contexto es operable pero con incertidumbre elevada.
- APPROVE si no hay bloqueo operativo/riesgo.

### Features

- spread
- session
- daily_drawdown_percent
- risk_percent_per_trade
- open position state
- ATR consumed
- D1 range position
- MAE proxy por contexto
- ambiguity rate por contexto
- flags de datos

### Metricas

- reduccion de max drawdown
- reduccion de ambiguous trades
- reduccion de SL rate
- costo en coverage
- estabilidad de bloqueos por periodo

### Restriccion Conceptual

Melchor no debe concluir que BUY o SELL sera rentable. Su salida debe ser riesgo operativo:

- `APPROVE`
- `CAUTION`
- `BLOCK`

## 5. CEO v3

CEO v3 solo debe entrenarse despues de tener magos v2.

### Inputs

- votos nuevos de Baltasar v2
- score/probabilidad de Baltasar v2
- calidad de Gaspar v2
- score/probabilidad de Gaspar v2
- riesgo Melchor v2
- score/probabilidad de Melchor v2
- contexto de mercado
- politica RR objetivo

### Output

- `ENTER_BUY`
- `ENTER_SELL`
- `DO_NOTHING`

### Objetivo

CEO v3 debe optimizar EV/R esperado, no accuracy.

Metricas primarias:

- avg R
- total R
- profit factor
- max drawdown
- trade precision
- coverage
- estabilidad walk-forward

Metricas secundarias:

- macro F1
- precision/recall por clase
- calibration

## 6. Datos Faltantes Para Backtest Institucional

Para abandonar el proxy y validar de forma seria, faltan:

- orden intrabar M1/M5 dentro del horizonte
- `hit_tp`
- `hit_sl`
- `first_touch`
- SL/TP exacto por operacion candidata
- comisiones
- slippage
- precio real de entrada/salida
- no solapamiento de operaciones
- position sizing
- equity curve real
- max drawdown de cuenta
- calendario de noticias/eventos si aplica
- auditoria de ejecucion por timestamp

Sin estos campos, toda metrica de rentabilidad sigue siendo proxy.

## 7. Orden Recomendado De Implementacion

### A. Enriquecer Simulador Con First-Touch Intrabar

Prioridad maxima.

Si existen datos M5/M1, el simulador debe determinar:

- si TP toca primero
- si SL toca primero
- si ambos tocan en la misma vela y sigue ambiguo
- salida por timeout
- R neto con spread/costos

Esto ataca directamente el mayor problema actual: ambiguedad TP/SL.

### B. Construir Labels RR 1:2

Crear labels sobre RR 1:2 porque fue el perfil mas prometedor:

- menor drawdown proxy
- menor ambiguedad
- mejor acercamiento a EV cero en escenario conservador

Labels iniciales:

- `tradeable_direction_rr2`
- `context_quality_rr2`
- `risk_block_rr2`
- `expected_R_proxy`

### C. Reentrenar Baltasar v2

Primero entre los magos, porque Baltasar es la fuente de direccion y el sistema sigue dependiendo mucho de su senal.

### D. Reentrenar Gaspar v2

Despues, para mejorar la calidad contextual y reducir ambiguedad/regimenes malos.

### E. Reentrenar Melchor v2

Tercero, formalizando bloqueos de riesgo operacional que reduzcan drawdown y SL rate.

### F. Entrenar CEO v3

Entrenar CEO v3 solo con magos v2 y targets RR mas solidos.

### G. Backtest Final

Ejecutar backtest con:

- costos
- no solapamiento
- sizing
- equity curve
- drawdown real
- walk-forward

## 8. Riesgos

### Sobreajuste Por Segmentos

Los segmentos con alta precision pueden ser producto de test-mining. Deben validarse con walk-forward y no convertirse automaticamente en reglas duras.

### Meses Malos

La politica conservative_core tiene meses peligrosos, por ejemplo:

- 2023-11
- 2025-10
- 2023-02
- 2024-06

El reentrenamiento debe reducir exposicion en estos contextos sin usar el mes como truco de leakage.

### Dependencia De Proxy

La diferencia entre escenario conservative y optimistic en R simulation es demasiado grande. Cualquier label creado sin first-touch puede inducir decisiones equivocadas.

### Data Leakage

Peligros:

- usar outcomes agregados como feature
- normalizar con estadisticas globales
- crear regimes a partir de performance futura
- seleccionar filtros por test sin validar fuera de muestra

### Falsas Mejoras Por Target Mal Diseñado

CEO v1 ya mostro una falsa mejora: el modelo aprendio Baltasar, no CEO. Los targets v2/v3 deben medir tradeability y EV, no replicar reglas ya conocidas.

## Recomendacion Ejecutiva

No recomiendo reentrenar los magos todavia como paso inmediato. Recomiendo mejorar primero la simulacion con first-touch intrabar y R neto. Sin eso, el reentrenamiento puede optimizar un proxy equivocado.

Si se decide avanzar en paralelo, el primer mago a reentrenar debe ser Baltasar v2, porque la direccion sigue siendo la mayor dependencia del sistema.

El primer target a construir debe ser:

`tradeable_direction_rr2`

Como target auxiliar:

`expected_R_proxy`

## Archivos Y Scripts Reutilizables

Para construir la siguiente fase se pueden reutilizar:

- `scripts/ceo_magi/audit_ceo_labels.py`
- `scripts/ceo_magi/build_ceo_v2_tradeable_dataset.py`
- `scripts/ceo_magi/train_ceo_v2_tradeable_model.py`
- `scripts/ceo_magi/analyze_ceo_v2_segments.py`
- `scripts/ceo_magi/evaluate_ceo_v2_policy.py`
- `scripts/ceo_magi/walk_forward_ceo_v2_policy.py`
- `scripts/ceo_magi/simulate_ceo_v2_r_trades.py`
- `simulator/ceo_training_dataset.py`
- `simulator/execution.py`
- `simulator/metrics.py`
- `baltasar_training_v1/`
- `gaspar_training_v1/`
- `magi/adapters/*_real_adapter.py`

## Roadmap Siguiente Fase

1. Implementar first-touch intrabar en simulador.
2. Generar dataset de candidatos con R neto RR 1:2.
3. Auditar labels `tradeable_direction_rr2`, `context_quality_rr2`, `risk_block_rr2`.
4. Reentrenar Baltasar v2 con target direccional operable.
5. Reentrenar Gaspar v2 con target de calidad contextual/ambiguedad.
6. Reentrenar Melchor v2 con target de bloqueo operativo.
7. Entrenar CEO v3 con votos/probabilidades de magos v2.
8. Ejecutar backtest institucional con costos, no solapamiento y equity curve.
9. Validar walk-forward antes de cualquier demo.
