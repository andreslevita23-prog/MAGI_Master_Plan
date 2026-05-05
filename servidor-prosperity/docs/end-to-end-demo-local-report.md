# Reporte: prueba end-to-end local MAGI demo sin MT5

## Dictamen final

**LISTO PARA COMPILAR EN METAEDITOR**

La prueba local end-to-end sin MT5 valida el flujo completo desde un payload Bot A `magi.snapshot.v2` hasta el payload compatible con Bot B y el journal cognitivo del backend. Tambien valida que el contrato legacy sigue funcionando.

## Script creado

- `scripts/test-end-to-end-demo.mjs`

Tambien se agrego el comando:

```bash
npm run test:e2e-demo
```

## Flujo validado

1. Enviar payload Bot A `magi.snapshot.v2` a `POST /analisis`.
2. Backend acepta y normaliza snapshot.
3. Backend genera decision MAGI con `decision_id`, `snapshot_id` y `decision_time`.
4. Backend guarda journal cognitivo en:
   - `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`
5. `GET /analisis/:symbol` devuelve payload compatible con Bot B.
6. Payload Bot B incluye:
   - `action`
   - `details.symbol`
   - `decision_id`
   - `snapshot_id`
   - `decision_time`
   - `details.comment` con formato `MAGI|short_id`
7. `/api/snapshots`, `/api/overview` y `/api/execution` siguen respondiendo.
8. Payload legacy valido sigue funcionando.
9. Payload v2 invalido se rechaza con `400`.

## Comandos ejecutados

```bash
npm run check
npm run test:e2e-demo
```

Resultado:

```json
{
  "ok": true,
  "checks": [
    "Servidor local respondio /health",
    "POST /analisis acepto magi.snapshot.v2 valido",
    "Payload Bot B de v2 contiene decision_id/snapshot_id/decision_time/comment MAGI",
    "Journal cognitivo escribio la decision v2",
    "GET /analisis/:symbol devuelve payload compatible con Bot B",
    "/api/snapshots funciona e incluye snapshot v2",
    "/api/overview funciona",
    "/api/execution funciona e incluye decision v2",
    "POST /analisis rechaza magi.snapshot.v2 invalido",
    "POST /analisis mantiene compatibilidad legacy valida"
  ]
}
```

Ejemplo real de la corrida:

```json
{
  "v2": {
    "symbol": "E2EV2",
    "action": "hold",
    "decision_id": "magi_10877a5431d333c0",
    "snapshot_id": "E2EV2_M5_2026-05-05T12:00:00_live",
    "comment": "MAGI|magi_10877a5"
  },
  "legacy": {
    "symbol": "E2ELEG",
    "action": "hold",
    "decision_id": "magi_1717f708e92aa8f9",
    "snapshot_id": "E2ELEG_e2e_legacy_decision",
    "comment": "MAGI|magi_1717f70"
  }
}
```

## Validaciones obligatorias

| Validacion | Estado |
|---|---|
| v2 valido aceptado | OK |
| v2 invalido rechazado | OK |
| legacy valido aceptado | OK |
| Bot B payload contiene `action` | OK |
| Bot B payload contiene `details.symbol` | OK |
| Bot B payload contiene `decision_id` | OK |
| Bot B payload contiene `snapshot_id` | OK |
| Bot B payload contiene `decision_time` | OK |
| Bot B payload contiene comment `MAGI|short_id` | OK |
| Journal cognitivo se escribe | OK |
| `/api/snapshots` funciona | OK |
| `/api/overview` funciona | OK |
| `/api/execution` funciona | OK |
| Compatibilidad legacy no se rompe | OK |

## Notas tecnicas

- El script usa simbolos temporales `E2EV2` y `E2ELEG`.
- El script limpia artefactos de `data/analysis`, `data/execution`, `data/snapshots` y votos Melchor asociados a esos simbolos.
- El script valida el journal cognitivo durante la corrida y luego restaura el archivo `magi_decisions.jsonl` si existia antes, para no dejar basura de prueba.
- Los logs operativos normales del backend pueden escribirse durante la prueba.

## Cambios aplicados por la prueba

No fue necesario modificar backend para corregir errores. La prueba paso con la implementacion actual.

## Riesgos pendientes

- No se probo compilacion MQL5 ni ejecucion real en MetaTrader.
- La decision de prueba para simbolos temporales termina en `hold`, porque el motor MVP actual solo opera EURUSD.
- La validacion de ejecucion real queda para Bot B/Bot C en cuenta demo.

## Siguiente paso

Compilar en MetaEditor:

- `integrations/mt5/botB_v3.0.mq5`
- `integrations/mt5/Bot_C.mq5`

Luego ejecutar checklist demo con MT5:

- Bot B consulta `GET /analisis/:symbol`.
- Bot B ejecuta con comment `MAGI|short_id`.
- Bot C registra el evento en `MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl`.
- Cruzar `short_id` contra `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`.
