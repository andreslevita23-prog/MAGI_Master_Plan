# 14. Data Contracts

## Snapshot de Bot A

Ver `templates/bot_a_sample.json`.

Campos clave:

- identificacion del snapshot
- estado estructural del mercado
- niveles relevantes
- indicadores minimos
- precio y rango reciente
- estado de posicion abierta

## Votos de magos

Ver `templates/magi_votes_sample.json`.

Reglas:

- mismo contrato para los tres magos
- mismo catalogo de `context_tag`
- `reason` opcional, pero recomendable
- posibilidad de uno o multiples disparadores para el mismo snapshot

## Decision del CEO

Ver `templates/ceo_decision_sample.json`.

Reglas:

- contrato unificado por `case_type`
- `reason` obligatoria
- campos operativos nulos cuando no aplican

## Compatibilidad futura con ML

Los contratos no cambian cuando se introduzca ML. Solo cambia la forma interna de producir la salida propia de cada modulo, por ejemplo `decision`, `confidence`, `risk_flag`, `voto` o `score_oportunidad` segun aplique.

## Contrato de Gaspar

Gaspar usa un contrato separado para calidad de oportunidad. No predice direccion; recibe `proposed_direction` como propuesta externa o proxy estructural.

Ejemplo base: `gaspar_training_v1/contracts/gaspar_input_example.json`.

```json
{
  "module": "GASPAR",
  "role": "opportunity_quality",
  "symbol": "EURUSD",
  "timestamp": "...",
  "proposed_direction": "BUY|SELL|NEUTRAL",
  "higher_timeframe_confluence": {
    "h4_structure": "bullish|bearish|range",
    "d1_structure": "bullish|bearish|range",
    "directional_alignment": "aligned|contradictory|neutral"
  },
  "price_structure_position": {
    "distance_to_d1_support": 0.0,
    "distance_to_d1_resistance": 0.0,
    "position_in_d1_range": 0.0,
    "near_key_level": true
  },
  "timing_quality": {
    "active_session": "asia|london|new_york|overlap|inactive",
    "daily_atr_consumed_pct": 0.0,
    "available_range_to_next_level": 0.0,
    "h4_candle_pattern": "rejection|engulfing|inside|none"
  },
  "day_context": {
    "day_of_week": "monday|tuesday|wednesday|thursday|friday",
    "d1_volatility_vs_20d_avg": 0.0,
    "current_d1_range_vs_atr": 0.0
  },
  "target": {
    "voto": "GOOD|FAIR|POOR",
    "score_oportunidad": 0.0
  }
}
```

Salida esperada:

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

Durante entrenamiento, si no existe una direccion real externa, `proposed_direction` se genera como proxy heuristico usando solo estructura H4/D1: D1 bullish y H4 no bearish => `BUY`, D1 bearish y H4 no bullish => `SELL`, D1 range o conflicto fuerte H4/D1 => `NEUTRAL`.

Pendiente: cuando Gaspar pase de entrenamiento a operacion, Bot A principal debera incluir un bloque separado `gaspar_context` con los datos estructurales y temporales necesarios para Gaspar. Ese bloque no debe incluir confianza, probabilidades, features ni indicadores de Baltasar.
