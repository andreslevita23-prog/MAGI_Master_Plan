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

Los contratos no cambian cuando se introduzca ML. Solo cambia la forma interna de producir `decision`, `confidence` y `risk_flag` dentro de cada mago.
