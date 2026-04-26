# 15. Risk Rules

## Reglas Melchor v1

La fuente ejecutable de reglas vive en `config/melchor_rules.json`.

Melchor no ejecuta veto final. Melchor evalua riesgo y recomienda mediante `vote`, `risk_block_recommendation`, `risk_level` y `recommended_action`.

- Solo operar en sesiones Londres, Nueva York o solapamiento.
- Riesgo maximo por operacion: `0.1%` del capital.
- Maximo `1` operacion abierta.
- No permitir RR menor a `1.5`.
- RR preferente: `2.0` o superior.
- Si hay `5` perdidas consecutivas: recomendar bloqueo de nuevas operaciones y notificar.
- Si drawdown diario `>= 0.7%`: emitir `NOTIFY`.
- Si drawdown diario `>= 1.0%`: recomendar cierre/proteccion y bloqueo de nuevas entradas.
- No operar en noticias de alto impacto de `USD`, `EUR` o `GBP`.
- Ventana de noticias: `30` minutos antes y `30` minutos despues.
- Si una operacion alcanza `50%` del TP: recomendar mover SL a breakeven.
- Despues de BE: recomendar trailing stop progresivo.
- No operar si spread `> 2.0` pips.
- SL minimo: `5` pips.
- SL maximo: `35` pips.
- Si faltan datos criticos: recomendar bloqueo.

## Reglas CEO-MAGI

- Bot A no decide: solo captura y envia snapshots.
- Melchor emite voto deterministico y auditable.
- CEO-MAGI debe leer `melchor_vote`.
- CEO-MAGI decide si bloquea, permite, protege o cierra.
- Si CEO-MAGI abre pese a `risk_block_recommendation: true`, debe registrar `override_melchor: true` y `override_reason`.
- Sin justificacion, CEO-MAGI puede respetar la recomendacion de bloqueo y no abrir.

## Reglas legacy que se conservan

- `POST /analisis` sigue recibiendo snapshots de Bot A.
- `GET /analisis/:symbol` sigue entregando la respuesta compatible para Bot B.
- El dashboard consume los mismos endpoints existentes.

## Pruebas manuales

Ejecutar desde `servidor-prosperity`:

```bash
npm run test:melchor
```

Casos cubiertos:

- `ALLOW` normal.
- `BLOCK` por RR menor a `1.5`.
- `BLOCK` por una operacion abierta.
- `NOTIFY` por drawdown diario `>= 0.7%`.
- Recomendacion de cierre/proteccion por drawdown diario `>= 1.0%`.
- `BLOCK` por noticia de alto impacto.
- `move_to_breakeven` cuando `profit_progress_to_tp >= 50%`.
