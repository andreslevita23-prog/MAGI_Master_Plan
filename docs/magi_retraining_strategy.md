# MAGI Retraining Strategy

## Objetivo

Definir cómo reentrenar Melchor, Baltasar, Gaspar y CEO-MAGI después del análisis histórico 2020-2026. El hallazgo central es que la señal no vive en los votos aislados: vive en la interacción entre votos y régimen.

## Principios

- Entrenar con particiones temporales.
- Medir estabilidad, no solo promedio global.
- Evaluar por dirección BUY/SELL.
- Evaluar por régimen.
- Separar señales direccionales de filtros operativos.
- Mantener leakage guard estricto.

## Baltasar

### Rol

Baltasar debe producir dirección:

- BUY
- SELL
- NEUTRAL

### Problema Observado

En cuatro meses, Baltasar BUY parecía fuerte. En seis años, la señal se degrada:

- BUY H48: hit rate 45.13%, net pips 1.08.
- SELL H48: hit rate 44.15%, net pips 0.79.

Esto indica que el modelo capta algo, pero no lo suficiente de forma global.

### Estrategia

- Reentrenar con labels H48 como principal.
- Mantener H12/H96/H288 como labels secundarios.
- Agregar features de régimen.
- Evaluar por año, sesión, hora y volatilidad.
- Penalizar modelos que funcionen solo en 2026.

### Métricas

- F1 macro.
- precision/recall por clase.
- matriz de confusión.
- estabilidad por periodo.
- hit rate direccional por régimen.
- net directional pips por régimen.

## Gaspar

### Rol

Gaspar debe medir calidad contextual:

- GOOD
- FAIR
- POOR

### Problema Observado

Gaspar GOOD no fue robusto globalmente:

- GOOD H48: hit rate direccional 44.60%, avg return -0.19.
- FAIR H48: 44.55%, avg return 0.15.
- POOR H48: 45.24%, avg return 0.19.

La jerarquía GOOD > FAIR > POOR no se sostiene de forma agregada.

### Estrategia

Recalibrar Gaspar con una de estas opciones:

1. Modelo separado por dirección:
   - Gaspar BUY quality.
   - Gaspar SELL quality.
2. Modelo único con `proposed_direction` como feature crítica.
3. Modelo de ranking/lift por régimen en vez de clasificación plana.

### Métricas

- lift de GOOD vs no GOOD.
- calibración por segmento.
- performance por dirección.
- estabilidad temporal.
- matriz de confusión de calidad.

## Melchor

### Rol

Melchor debe seguir siendo filtro operativo y de riesgo.

No debe reentrenarse como predictor de precio.

### Variables De Interés

- sesión
- spread
- riesgo de cuenta
- condiciones prohibidas
- drawdown
- estado operativo
- gaps o problemas de data

### Uso En CEO

Melchor puede alimentar al CEO como:

- bloqueo duro
- flag de riesgo
- feature de contexto
- explicación operacional

## CEO-MAGI

### Rol

CEO-MAGI debe aprender cuándo confiar en los magos.

Input:

- votos
- confidence
- features de régimen
- flags de riesgo
- calidad de data

Output:

- ENTER_BUY
- ENTER_SELL
- HOLD
- AVOID
- LOW_CONFIDENCE

### Label Principal

Outcome favorable H48.

### Labels Secundarios

- H12 para validación de corto plazo.
- H96 para persistencia.
- H288 para régimen.
- MFE/MAE para asimetría de oportunidad/riesgo.

## Segmentos Obligatorios

El entrenamiento y la reportería deben incluir:

- active_session
- año
- mes
- día de semana
- hora UTC
- rango M5
- spread
- h4_structure
- d1_structure
- directional_alignment
- daily_atr_consumed_pct
- position_in_d1_range

## Train/Validation/Test

Partición inicial:

- Train: 2020-01 a 2023-12.
- Validation: 2024-01 a 2024-12.
- Test final: 2025-01 a 2026-04.

Regla: todas las transformaciones deben ajustarse solo con train.

## Walk-Forward

Esquema:

- Train: 18 meses.
- Validation: 3 meses.
- Test forward: 3 meses.
- Avanzar ventana.

La decisión de pasar a demo debe depender de estabilidad walk-forward, no solo de un test final agregado.

## Riesgos

- Sobreajuste a 2026.
- Falsa señal por mes específico.
- Gaspar GOOD mal calibrado.
- SELL sensible a spread y horario.
- Features de régimen que actúan como proxy temporal.
- Cambios futuros en mercado no representados por el histórico.

## Próximo Paso

Entrenar un baseline CEO interpretable:

- modelo simple
- features limitadas
- validación temporal
- reporte por régimen

Solo después probar modelos más complejos.
