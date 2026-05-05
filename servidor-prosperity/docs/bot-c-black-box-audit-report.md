# Rediseño Bot C: caja negra operativa MAGI

## Dictamen final

**LISTO PARA PRUEBA LOCAL**

Se implemento la primera version de Bot C como auditor operativo pasivo. Bot C no abre, no cierra y no modifica operaciones; solo observa eventos MT5 y escribe evidencia local. El backend ahora conserva un journal cognitivo de decisiones MAGI y el payload para Bot B incluye identificadores de auditoria.

## Arquitectura de auditoria propuesta

```text
Bot A -> POST /analisis -> backend
  backend guarda:
    snapshot legacy/normalized
    voto Melchor disponible
    decision CEO/MVP enriquecida
    payload enviado a Bot B
    journal data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl

Bot B -> GET /analisis/:symbol
  recibe:
    decision_id
    snapshot_id
    decision_time
    action
    details
  ejecuta en MT5 con comment compacto:
    MAGI|<short_decision_id>

Bot C -> MT5 observador
  registra:
    aperturas
    cierres
    modificaciones/updates
    snapshots flotantes
    ticket/deal/order
    magic_number
    comment
    decision_id compacto extraido del comment
    profit/SL/TP/precio
```

La union entre realidad cognitiva y realidad operativa se hace por:

- `decision_id`
- `snapshot_id`
- `symbol`
- `magic_number`
- `ticket`
- `deal`
- timestamps
- `comment` con formato `MAGI|<short_decision_id>`

## Auditoria del backend actual

### Lo que ya guardaba

| Evidencia | Ruta / archivo | Estado |
|---|---|---|
| Snapshots legacy | `data/snapshots/legacy/*.json` | Existe |
| Snapshots normalizados | `data/snapshots/normalized/*.json` | Existe |
| Execution state por simbolo | `data/execution/{SYMBOL}.json` | Existe |
| Payload actual para Bot B | `data/analysis/{SYMBOL}.json` | Existe |
| Logs Bot A/B/system | `data/logs/YYYY-MM-DD/*.jsonl` | Existe |
| Votos Melchor | `data/votes/melchor/*.json` | Existe si Melchor se evalua |
| Votos Baltasar/Gaspar | `data/votes/baltasar`, `data/votes/gaspar` | No existen en este backend actual |

### Campos cognitivos

| Campo requerido | Estado despues del ajuste |
|---|---|
| `snapshot_id` | Persistido en snapshot, execution, audit y payload Bot B |
| `decision_id` | Nuevo: generado por backend y persistido |
| votos individuales | `melchor_vote` disponible; `baltasar_vote`/`gaspar_vote` quedan `null` hasta integracion real |
| decision final CEO | Persistida como `ceo_decision`; actualmente representa la decision MVP/CEO transicional |
| razon de decision | Persistida en `reason` y `details.reason` |
| `override_melchor` | Persistido si existe en decision |
| payload exacto Bot B | Persistido en `execution_payload` dentro del journal audit |
| timestamp decision | Nuevo: `decision_time` |

## Contrato minimo de auditoria

Cada registro en `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl` usa:

```json
{
  "schema_version": "magi.audit.decision.v1",
  "status": "sent",
  "decision_id": "magi_...",
  "snapshot_id": "EURUSD_...",
  "symbol": "EURUSD",
  "decision_time": "2026-05-05T00:00:00.000Z",
  "final_action": "open",
  "order_type": "buy",
  "lot_size": 0.01,
  "sl": 1.115,
  "tp": 1.13,
  "reason": "Caso MVP detectado...",
  "melchor_vote": {},
  "baltasar_vote": null,
  "gaspar_vote": null,
  "ceo_decision": {},
  "override_melchor": false,
  "execution_payload": {},
  "files": {}
}
```

Estados previstos: `pending`, `sent`, `executed`, `rejected`, `closed`. En esta version backend registra `sent`; Bot C registra la realidad MT5 en su propio JSONL.

## Parte backend implementada

Archivos modificados/creados:

- `src/server/config/paths.js`
- `src/server/services/audit/decision-audit.service.js`
- `src/server/index.js`
- `src/server/services/adapters/mt5/bot-b-response-mapper.js`
- `src/server/domain/contracts/execution-response.js`

Cambios:

- Se agrega `data/audit/decisions`.
- Se genera `decision_id`, `decision_time` y `short_decision_id` antes de mapear a Bot B.
- Se persiste cada decision completa como JSONL diario:
  - `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`
- El payload de Bot B incluye:
  - `decision_id`
  - `snapshot_id`
  - `decision_time`
  - `id_operacion`
  - `details.reason`
- El comentario enviado a MT5 usa formato compacto:
  - `MAGI|<short_decision_id>`

## Parte Bot B implementada

Archivo modificado:

- `integrations/mt5/botB_v3.0.mq5`

Cambio relevante para auditoria:

- Si el backend envia `decision_id`, Bot B usa comment `MAGI|<short_decision_id>`.
- Si no hay `decision_id`, usa `snapshot_id`.
- Si tampoco hay IDs, mantiene fallback seguro.

## Parte Bot C implementada

Archivo creado:

- `integrations/mt5/Bot_C.mq5`

Bot C registra eventos MT5 en:

- `MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl`
- `MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json`

Eventos observados:

- `open`
- `close`
- `close_open`
- `deal`
- `order_update`
- `position_update`
- `floating_snapshot`

Campos por evento:

```json
{
  "schema_version": "magi.bot_c.event.v1",
  "event_type": "open",
  "timestamp": "2026-05-05T00:00:00Z",
  "symbol": "EURUSD",
  "magic_number": 30001,
  "ticket": 123456,
  "deal": 234567,
  "order": 345678,
  "comment": "MAGI|magi_ab12cd3",
  "decision_id": "magi_ab12cd3",
  "snapshot_id": "",
  "price": 1.12,
  "volume": 0.01,
  "sl": 1.115,
  "tp": 1.13,
  "profit": 0,
  "floating_profit": 0,
  "retcode": 10009,
  "anomaly": ""
}
```

Resumen diario:

```json
{
  "schema_version": "magi.bot_c.daily_summary.v1",
  "date": "2026-05-05",
  "operaciones_abiertas": 1,
  "operaciones_cerradas": 1,
  "ganadoras": 1,
  "perdedoras": 0,
  "breakeven": 0,
  "profit_neto": 12.5,
  "drawdown_aproximado": 0,
  "simbolos_operados": "EURUSD",
  "decisiones_ejecutadas": "magi_ab12cd3",
  "decisiones_sin_ejecutar_detectables": 0,
  "posiciones_abiertas_al_cierre": 0,
  "anomalias": 0
}
```

## Como se cruzan los datos

1. Buscar `decision_id` en `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`.
2. Tomar `short_decision_id`.
3. Buscar eventos Bot C cuyo `comment` o `decision_id` contenga ese short id.
4. Verificar:
   - `symbol`
   - `magic_number`
   - `ticket/deal`
   - hora de ejecucion vs `decision_time`
   - precio/SL/TP reales vs `execution_payload.details`
   - profit final del cierre

## Checklist de prueba local

Backend:

- Ejecutar `npm run check`.
- Enviar un snapshot Bot A legacy o v2.
- Confirmar que existe:
  - `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`
  - `data/execution/{SYMBOL}.json`
  - `data/analysis/{SYMBOL}.json`
- Confirmar que `GET /analisis/:symbol` devuelve `decision_id`, `snapshot_id` y `decision_time`.

Bot B:

- Compilar `botB_v3.0.mq5`.
- Confirmar que una orden abierta queda con comment `MAGI|...`.

Bot C:

- Compilar `Bot_C.mq5`.
- Adjuntarlo a un chart demo.
- Ejecutar una orden MAGI via Bot B.
- Confirmar archivos locales:
  - `MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl`
  - `MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json`
- Verificar que el evento contiene `ticket`, `deal`, `magic_number`, `comment`, `decision_id`, `price`, `sl`, `tp`.

Casos:

- open registrado
- modify/protect registrado como update
- move_to_breakeven registrado con SL real
- close registrado con profit final
- orden manual sin comment MAGI marcada como anomalia `orden_sin_decision_id`

## Riesgos pendientes

- Bot C extrae solo el ID compacto desde el comment; el cruce completo requiere comparar contra `short_decision_id` del backend.
- `snapshot_id` no cabe de forma confiable en comment MT5; queda en backend y no siempre en Bot C.
- Baltasar/Gaspar aun no tienen votos persistidos por este backend; quedan `null`.
- Bot C no puede detectar decisiones no ejecutadas que nunca llegaron a MT5; eso debe inferirse cruzando journal backend vs eventos MT5.
- No se pudo compilar MQL5 desde este entorno; MetaEditor debe validar `Bot_C.mq5` y `botB_v3.0.mq5`.
- El resumen diario de Bot C vive en memoria durante la sesion; si se reinicia el EA, conserva archivo de eventos pero el contador del resumen vuelve a calcular parcialmente desde nuevos eventos.

## Conclusion

La version 1 cumple el objetivo de trazabilidad:

- Backend guarda la realidad cognitiva.
- Bot B transporta identificadores al entorno MT5.
- Bot C guarda la realidad operativa sin intervenir en ejecucion.

Dictamen: **LISTO PARA PRUEBA LOCAL**.
