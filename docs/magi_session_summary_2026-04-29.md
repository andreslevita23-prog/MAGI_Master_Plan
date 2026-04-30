# MAGI Session Summary - 2026-04-29

## Resumen ejecutivo

La sesión de hoy convirtió el trabajo de CEO-MAGI y Baltasar v2 en una ruta técnica mucho más clara. Se pasó de entrenar modelos aislados a validar si las señales tienen valor operativo bajo first-touch M5, RR 1:2, filtros de contexto y métricas de riesgo. El hallazgo principal es que Baltasar v2 con features técnicas reales sí muestra edge, pero solo cuando se controla la exposición a horarios, rango diario y segmentos débiles.

El mejor experimento ML bruto sigue siendo `Baltasar v2 rich_features` con timing completo. La variante `rich_no_timing` confirmó que existe edge técnico, aunque menor. La variante `rich_coarse_timing` redujo dependencia de hora exacta, pero perdió demasiado edge tras corregir el bucket semanal. La capa `rich_policy_medium` sobre `rich_full_timing` fue el resultado más sólido del día: mejora PF, avg R y drawdown frente al modelo sin policy, y compite bien contra Baltasar v1 en calidad operativa, aunque con menos cobertura.

La conclusión honesta es que MAGI avanzó de forma importante, pero Baltasar v2 todavía no debe reemplazar automáticamente a Baltasar v1. El candidato principal para la siguiente fase es `rich_policy_medium` threshold `0.40`, con `0.50` como modo defensivo de alta convicción. Antes de promoverlo, falta una simulación R final y un diagnóstico profundo de SELL y del régimen problemático de 2026Q2.

## Qué se hizo hoy

1. Se entrenó y evaluó `Baltasar v2 rich_features` usando features técnicas reales M5 + MTF y target RR 1:2 first-touch M5.
2. Se entrenó `rich_no_timing` para medir si el edge sobrevivía sin variables directas de horario.
3. Se auditó `rich_full_timing` con walk-forward y segmentos para detectar dependencia de timing y zonas peligrosas.
4. Se creó `rich_coarse_timing`, eliminando `hour`, `weekday` y `regime`, y creando `hour_bucket` y `weekday_bucket`.
5. Se detectó y corrigió un problema técnico: `weekday` venía como texto y el primer bucket lo convertía a `UNKNOWN`.
6. Se reentrenó `rich_coarse_timing` con `weekday_bucket` correcto.
7. Se ejecutó walk-forward y segment analysis de `rich_coarse_timing`.
8. Se concluyó que `rich_coarse_timing` reduce dependencia sospechosa, pero pierde demasiado edge.
9. Se creó una policy layer sobre `rich_full_timing` sin reentrenar.
10. Se evaluaron `rich_policy_light`, `rich_policy_medium` y `rich_policy_strict`.
11. Se validó profundamente `rich_policy_medium` en thresholds `0.40` y `0.50`.
12. Se documentaron resultados en docs individuales y artefactos de validación.

## Modelos evaluados

| Modelo / variante | Objetivo | Resultado resumido |
| --- | --- | --- |
| Baltasar v2 rich_features | Usar features técnicas reales + timing completo | Mejor experimento ML bruto; se acerca/supera parcialmente a Baltasar v1 en calidad, pero necesita policy |
| rich_no_timing | Medir edge técnico sin timing directo | El edge técnico existe, pero cae frente a rich_full_timing |
| rich_coarse_timing | Suavizar timing sin hora exacta | Tras corregir weekday_bucket, perdió demasiado edge |
| rich_policy_medium | Bloquear segmentos peligrosos sobre rich_full_timing | Mejor candidato experimental actual |

## Resultados clave

### Comparación principal en test

| Modelo / policy | Threshold | Trades | Coverage | Avg R | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baltasar v1 signal | signal | 48,457 | 64.62% | 0.0835 | 1.1520 | 766.96 |
| rich_full_timing sin policy | 0.40 | 35,242 | 46.99% | 0.0576 | 1.0963 | 513.93 |
| rich_full_timing sin policy | 0.50 | 6,765 | 9.02% | 0.0821 | 1.1364 | 292.51 |
| rich_no_timing | 0.50 | 3,358 | 4.48% | 0.0659 | 1.1121 | 222.50 |
| rich_coarse_timing | 0.50 | 7,486 | 9.98% | 0.0342 | 1.0561 | 327.42 |
| rich_policy_medium | 0.40 | 19,967 | 26.63% | 0.0932 | 1.1621 | 266.14 |
| rich_policy_medium | 0.50 | 2,995 | 3.99% | 0.1631 | 1.2892 | 134.09 |

### Validación de rich_policy_medium

| Threshold | Split | Trades | Coverage | Avg R | PF | Max DD |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0.40 | Validation | 11,425 | 19.24% | 0.0556 | 1.1011 | 348.18 |
| 0.40 | Test | 19,967 | 26.63% | 0.0932 | 1.1621 | 266.14 |
| 0.50 | Validation | 1,912 | 3.22% | 0.2304 | 1.4548 | 75.21 |
| 0.50 | Test | 2,995 | 3.99% | 0.1631 | 1.2892 | 134.09 |

## Estabilidad temporal de rich_policy_medium

| Threshold | Años positivos | Trimestres positivos | Meses positivos |
| --- | ---: | ---: | ---: |
| 0.40 | 3/3 | 9/10 | 18/28 |
| 0.50 | 3/3 | 9/10 | 16/21 |

El único trimestre negativo en ambos thresholds fue `2026Q2`. No se recomienda bloquear trimestres como regla real, pero sí estudiarlo como régimen problemático.

## Hallazgos clave

- El timing sí aporta. Quitar timing directo reduce el rendimiento.
- El edge técnico existe. `rich_no_timing` no colapsa, lo que confirma que no todo depende de horario.
- La hora exacta ayuda, pero puede sobreajustar. La versión coarse redujo dependencia, pero perdió demasiado rendimiento.
- SELL sigue siendo más débil y con peor drawdown que BUY.
- Horas peligrosas bloqueadas por policy medium: `13`, `15`, `16`, `20`, `22`.
- `session == inactive` y `daily_range_position > 0.85` deben evitarse.
- `2026Q2` es el régimen/periodo más problemático y requiere diagnóstico.

## Decisiones técnicas tomadas

1. No reemplazar Baltasar v1 todavía.
2. Mantener `rich_full_timing` como mejor base ML.
3. Descartar `rich_coarse_timing` como candidato principal después de la corrección de `weekday_bucket`.
4. Promover `rich_policy_medium` a candidato experimental principal.
5. Usar threshold `0.40` como candidato operativo por mayor muestra y cobertura.
6. Mantener threshold `0.50` como modo defensivo/alta convicción.
7. No bloquear meses/trimestres como política real; solo usarlos para diagnóstico.
8. Validar SELL por separado antes de avanzar hacia integración.

## Estado actual de MAGI

### Qué funciona

- Dataset RR 1:2 first-touch M5 construido y utilizable.
- Features técnicas M5 + MTF disponibles y tabularizadas.
- Baltasar v2 rich aprende señal útil.
- La policy layer mejora robustez y reduce drawdown.
- `rich_policy_medium 0.40` supera a Baltasar v1 en avg R/PF test con menor drawdown, aunque opera menos.

### Qué NO está listo

- Baltasar v2 no debe reemplazar a Baltasar v1 todavía.
- SELL necesita diagnóstico profundo.
- `2026Q2` no está entendido.
- Falta simulación R final específica de `rich_policy_medium`.
- Falta decidir cómo Gaspar v2 debe filtrar contexto usando estos hallazgos.

## Conclusión honesta

MAGI tiene una señal operativa real en Baltasar v2, pero el valor no está en predicción direccional cruda. El valor aparece cuando se combina modelo, target first-touch y policy de abstención. La mejor ruta no es más complejidad de ML todavía, sino validar con más profundidad la política actual, entender SELL, estudiar el régimen malo y luego decidir si Gaspar v2 debe aprender esos bloqueos de contexto de forma nativa.

## Plan siguiente sesión

### Objetivo del siguiente bloque

Confirmar si Baltasar v2 puede convertirse en motor principal o si debe quedar como señal secundaria/filtrada por Gaspar/CEO.

### Prioridad 1: simulación R final de rich_policy_medium

- Evaluar `rich_policy_medium` thresholds `0.40` y `0.50`.
- Usar first-touch/RR 1:2 como base.
- Reportar avg R, PF, max DD, total R, meses malos y estabilidad temporal.
- Comparar contra Baltasar v1 y rich_full_timing sin policy.

### Prioridad 2: diagnóstico profundo de SELL

- Separar BUY vs SELL por threshold.
- Analizar SELL por hora, sesión, rango diario, ATR, mes y trimestre.
- Determinar si SELL debe tener umbral mayor, bloqueo adicional o tratamiento separado.

### Prioridad 3: análisis del régimen problemático 2026Q2

- Revisar si el problema viene de volatilidad, rango diario, dirección, sesión o estructura MTF.
- No convertir 2026Q2 en regla de bloqueo.
- Usarlo para diseñar features/targets de Gaspar v2.

### Prioridad 4: decidir inicio de Gaspar v2

- Si la simulación R final confirma robustez, definir target `context_quality_rr2`.
- Gaspar v2 debe aprender contexto operable/no operable, no dirección.
- Usar hallazgos de policy medium como base de labels y validación.

## Archivos relevantes producidos o usados

- `scripts/magi_v2/train_baltasar_v2_rich_features.py`
- `scripts/magi_v2/train_baltasar_v2_rich_no_timing.py`
- `scripts/magi_v2/train_baltasar_v2_rich_coarse_timing.py`
- `scripts/magi_v2/analyze_baltasar_v2_rich_walkforward.py`
- `scripts/magi_v2/analyze_baltasar_v2_coarse_walkforward.py`
- `scripts/magi_v2/evaluate_baltasar_v2_rich_policy.py`
- `scripts/magi_v2/validate_baltasar_v2_policy_medium.py`
- `docs/baltasar_v2_rich_features_model.md`
- `docs/baltasar_v2_rich_no_timing.md`
- `docs/baltasar_v2_rich_coarse_timing.md`
- `docs/baltasar_v2_rich_walkforward.md`
- `docs/baltasar_v2_coarse_walkforward.md`
- `docs/baltasar_v2_rich_policy.md`
- `docs/baltasar_v2_policy_medium_validation.md`

