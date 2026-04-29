# CEO-MAGI Training Methodology

## Alcance

Esta metodología describe cómo se debe entrenar el futuro CEO-MAGI usando el dataset generado a partir de Bot A sub3 y los votos reales de Melchor, Baltasar y Gaspar. No presupone una estrategia fija con SL/TP; el objetivo es aprender cuándo confiar en los magos bajo condiciones históricas observables.

## Dataset Base

- Fuente: Bot A sub3 limpio.
- Periodo: 2020-01-15 a 2026-04-14.
- Símbolo: EURUSD.
- Timeframe base: M5.
- Snapshots procesados: 371,513.
- Registros CEO generados: 371,501.
- Horizontes de outcome: 12, 48, 96 y 288 barras M5.
- Magos usados: Melchor real, Baltasar real y Gaspar real.

Cada registro CEO contiene:

- snapshot histórico en tiempo de decisión
- voto de Melchor
- voto de Baltasar
- voto de Gaspar
- outcomes futuros crudos
- leakage guard

## Hallazgo Central

Los votos aislados no son suficientes. En seis años, Baltasar y Gaspar muestran señal débil y heterogénea cuando se agregan globalmente. La señal aparece y desaparece según régimen:

- sesión
- hora UTC
- spread
- rango M5
- estructura H4/D1
- ATR diario consumido
- posición dentro del rango D1
- año/mes

Por tanto, el futuro CEO-MAGI debe aprender:

```text
votos + confianza + régimen + flags de riesgo -> decisión
```

No debe aprender únicamente:

```text
BUY/SELL/GOOD/FAIR/POOR -> entrar
```

## Objetivo Del CEO-MAGI

El CEO-MAGI debe decidir cuándo convertir la opinión de los magos en una acción operativa. Una salida inicial razonable:

- `ENTER_BUY`
- `ENTER_SELL`
- `HOLD`
- `AVOID`
- `LOW_CONFIDENCE`

La salida debe poder distinguir entre ausencia de señal, señal débil, señal bloqueada por riesgo y señal históricamente favorable bajo un régimen específico.

## Labels Sugeridos

### Label Principal

Outcome favorable H48:

- Para señales BUY: favorable si el movimiento posterior fue alcista y suficientemente positivo.
- Para señales SELL: favorable si el movimiento posterior fue bajista y suficientemente positivo en términos direccionales.
- Para NEUTRAL: usar como clase de abstención o como ejemplo de no entrada.

### Labels Secundarios

- H12: confirmación temprana y ruido de corto plazo.
- H96: persistencia del movimiento.
- H288: régimen amplio.
- MFE: potencial máximo favorable.
- MAE: riesgo adverso observado.

## Features Del CEO

### Votos

- Melchor vote.
- Baltasar direction.
- Gaspar quality.
- confidence por mago.
- reason/context tags cuando estén normalizados.

### Régimen

- active_session.
- hora UTC.
- día de semana.
- año/mes o features temporales equivalentes.
- spread.
- rango M5.
- H4 structure.
- D1 structure.
- directional_alignment.
- daily_atr_consumed_pct.
- position_in_d1_range.
- flags `is_high_spread` y `has_gap_forward`.

### Riesgo

- Melchor como filtro operativo.
- spread extremo.
- horarios no operables.
- drawdown/riesgo de cuenta cuando exista.

## Entrenamiento De Baltasar

### Objetivo

Predecir dirección:

- BUY
- SELL
- NEUTRAL

### Features

Features técnicas disponibles en tiempo de decisión:

- estructura de mercado
- dirección de estructura
- momentum
- RSI
- relación precio/EMAs
- gaps entre EMAs
- rango reciente
- ratios de vela

### Labels

Labels futuros construidos con retornos direccionales por horizonte, principalmente H48, y secundarios H12/H96/H288.

### Validación

Debe ser temporal, nunca aleatoria simple.

Métricas:

- F1 macro.
- precision/recall por clase.
- matriz de confusión.
- estabilidad por año y mes.
- desempeño por sesión y volatilidad.

## Entrenamiento De Gaspar

### Objetivo

Predecir calidad contextual:

- GOOD
- FAIR
- POOR

### Recalibración Necesaria

Gaspar GOOD no fue robusto globalmente en seis años. Debe recalibrarse porque:

- GOOD mejora algunos contextos BUY.
- GOOD no estabiliza SELL.
- FAIR y POOR no se ordenan consistentemente como calidad descendente.

### Enfoques Recomendados

- Entrenar separado por dirección BUY/SELL, o
- incluir `proposed_direction` como feature crítica, y
- evaluar lift por segmento de régimen.

Métricas:

- calibración por clase.
- lift vs baseline por dirección.
- performance por régimen.
- estabilidad temporal.

## Melchor

Melchor no debe entrenarse como predictor direccional. Su rol correcto:

- riesgo operativo
- horario
- spread
- noticias/eventos cuando existan
- condiciones prohibidas
- control de exposición

Para CEO-MAGI, Melchor debe entrar como:

- filtro duro cuando aplique
- feature de riesgo
- explicación operacional

No debe usarse para concluir que una dirección de mercado es rentable o no.

## Separación Temporal De Datos

Partición obligatoria inicial:

- Train: 2020-01 a 2023-12.
- Validation: 2024-01 a 2024-12.
- Test final: 2025-01 a 2026-04.

No usar split aleatorio simple, porque mezclaría regímenes y filtraría información temporal.

## Walk-Forward

Opción recomendada:

1. Entrenar 18 meses.
2. Validar 3 meses.
3. Test forward 3 meses.
4. Avanzar ventana.
5. Comparar estabilidad de métricas y selección de features.

Este esquema debe usarse antes de promover cualquier modelo a demo.

## Prevención De Leakage

Reglas obligatorias:

- `features_at_decision_time` solo puede contener información disponible al timestamp del snapshot.
- Labels se generan después del timestamp y nunca vuelven al payload de features.
- Prohibir columnas con nombres:
  - future
  - outcome
  - pnl
  - mfe
  - mae
  - target
  - forward_return
  - hit_tp
  - hit_sl
- No normalizar con estadísticas globales del dataset completo.
- Ajustar transformadores solo con train.
- MTF solo con velas cerradas.
- Auditar timestamps de H1/H4/D1 frente al snapshot base.

## Criterio De Éxito

CEO-MAGI estará listo para demo solo si:

- supera baseline HOLD/NEUTRAL en test final
- mantiene estabilidad por año/mes
- no depende de un único régimen
- muestra lift claro sobre Baltasar y Gaspar aislados
- tiene calibración razonable de confianza
- pasa auditoría de leakage
