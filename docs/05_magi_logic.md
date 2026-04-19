# 05. MAGI Logic

## Contrato comun de voto de los magos

Cada mago devuelve:

- `decision`: `approve` | `reject` | `neutral`
- `confidence`: `0.0` a `1.0`
- `risk_flag`: `low` | `medium` | `high`
- `context_tag`: `trend` | `range` | `breakout` | `reversal` | `volatile` | `unclear`
- `reason`: texto breve opcional

## Significado comun

- `confidence` expresa solidez del analisis del mago.
- `risk_flag` expresa peligro contextual desde la perspectiva del mago.
- `neutral` expresa ausencia de evidencia suficiente para aprobar o rechazar.

## Jerarquia del sistema

- `Melchor` domina el riesgo.
- `Baltasar` domina la validacion tecnica.
- `Gaspar` complementa oportunidad.
- `CEO-MAGI` decide incluso ante senales mixtas.

## Reglas base del MVP

- Si `Melchor = reject` y `risk_flag = high` -> `no_trade` o accion conservadora equivalente.
- Si `Baltasar = reject` con alta `confidence` -> no abrir entrada.
- Si `Baltasar = approve` y `Melchor != reject` -> el CEO puede evaluar entrada.
- `Gaspar` puede reforzar y descubrir oportunidad, pero no sobrepasar a `Melchor`.

## Principio de arbitraje

El CEO no opera por democracia ciega. Resuelve segun jerarquia funcional, claridad del contexto y consistencia del caso.
