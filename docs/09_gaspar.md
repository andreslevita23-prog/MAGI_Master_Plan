# 09. Gaspar

## Mision

Gaspar evalua calidad de oportunidad de entrada. No predice direccion; responde si el momento especifico tiene suficiente calidad para entrar.

Salida principal:

```json
{
  "module": "GASPAR",
  "role": "opportunity_quality",
  "voto": "GOOD|FAIR|POOR",
  "score_oportunidad": 0.0,
  "pillars": {
    "higher_timeframe_confluence": 0.0,
    "price_structure_position": 0.0,
    "timing_quality": 0.0,
    "day_context": 0.0
  },
  "reason": "..."
}
```

## Diferencia con Baltasar

Baltasar puede predecir direccion con datos tecnicos direccionales. Gaspar no recibe confianza, probabilidades, features ni indicadores de Baltasar. Gaspar solo recibe `proposed_direction` (`BUY`, `SELL`, `NEUTRAL`) y decide si esa propuesta tiene calidad estructural y temporal suficiente para ejecutarse.

Durante entrenamiento, si no existe una direccion real externa, `proposed_direction` se genera como proxy heuristico usando solo estructura H4/D1:

- D1 bullish y H4 no bearish: `BUY`
- D1 bearish y H4 no bullish: `SELL`
- D1 range o conflicto fuerte H4/D1: `NEUTRAL`

Regla critica: Gaspar no usa EMAs, RSI ni momentum. Esas senales pertenecen a Baltasar.

## Diferencia con Melchor

Melchor controla riesgo, seguridad y veto operativo. Gaspar no calcula exposicion, tamano de posicion ni permisos finales. Un voto `GOOD` de Gaspar puede ser rechazado por Melchor.

## Pilares de Gaspar

- `higher_timeframe_confluence`: estructura H4/D1 y alineacion con `proposed_direction`.
- `price_structure_position`: distancia a soporte/resistencia D1, posicion en rango y cercania a niveles.
- `timing_quality`: sesion activa, ATR diario consumido, rango disponible y patron H4.
- `day_context`: dia de semana, volatilidad D1 contra promedio de 20 dias y rango D1 actual contra ATR.

## Entrenamiento v1

El laboratorio base vive en `gaspar_training_v1/`.

Flujo:

1. `Bot_A_sub2.mq5` genera CSV/JSONL con estructura de precio y contexto temporal.
2. `run_training.py` carga snapshots, limpia datos y construye features.
3. Se crea un target provisional con heuristica de cuatro pilares si el dataset no trae target.
4. Se entrena un baseline simple.
5. Se reportan F1 macro, matriz de confusion, distribucion de clases y validacion temporal/walk-forward.

## Target provisional

Pesos iniciales:

- `higher_timeframe_confluence`: 0.40
- `price_structure_position`: 0.30
- `timing_quality`: 0.20
- `day_context`: 0.10

Umbrales:

- `GOOD`: score >= 0.65
- `FAIR`: 0.40 <= score < 0.65
- `POOR`: score < 0.40

Este target es una heuristica inicial. Debe refinarse con resultados reales registrados por Bot C.

## Pendiente operativo

Cuando Gaspar pase de entrenamiento a operacion, Bot A principal debera incluir un bloque separado `gaspar_context` con los datos estructurales y temporales necesarios para Gaspar, incluyendo `proposed_direction` si viene de un modulo externo. Ese bloque no debe mezclar confianza, probabilidades, features ni indicadores de Baltasar.
