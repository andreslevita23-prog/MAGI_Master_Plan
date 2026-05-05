# Reporte tecnico: adapter backend para magi.snapshot.v2

## Dictamen final

**LISTO PARA PRUEBA LOCAL**

El backend acepta ahora snapshots `magi.snapshot.v2` de Bot A, los normaliza para el flujo interno y conserva compatibilidad con el contrato legacy y con `GET /analisis/:symbol`.

## Archivos creados

- `src/server/services/adapters/mt5/snapshot-v2-adapter.js`
- `scripts/test-snapshot-v2-adapter.mjs`
- `docs/bot-a-snapshot-v2-adapter-report.md`

## Archivos modificados

- `src/server/index.js`
- `src/server/services/adapters/mt5/bot-b-response-mapper.js`
- `src/server/services/snapshots/snapshot-store.service.js`
- `package.json`
- `docs/integration-plan.md`
- `docs/connectors.md`

## Que cambio

- `POST /analisis` detecta `schema_version` compatible con `magi.snapshot.v2`.
- Payloads legacy siguen usando `validateLegacySnapshot()` y `adaptBotALegacySnapshot()`.
- Payloads v2 usan `validateSnapshotV2Payload()` y `adaptBotASnapshotV2()`.
- El adapter v2 mapea datos de mercado, OHLC ancla, indicadores, MTF, cuenta, posicion, Gaspar, features, validacion, noticias y notas operativas al snapshot normalizado.
- Los campos criticos `symbol`, `current_price` y `timestamp` se validan con rechazo HTTP `400` si faltan o son invalidos.
- Los campos no criticos faltantes se registran como warnings en `normalized.validation.issues`.
- Si `daily_drawdown_percent` o `risk_percent_per_trade` llegan en `0.0`, se conservan sin inventar valores y se registra warning explicito.
- La persistencia de snapshots sanitiza el nombre de archivo para soportar `snapshot_id` v2 con timestamps ISO que contienen `:`.
- La respuesta hacia Bot B sigue saliendo con `action`, `id_operacion`, `details` y `timestamp`.

## Como probarlo

Desde `servidor-prosperity`:

```bash
npm run check
npm run test:snapshot-v2
```

La prueba `test:snapshot-v2` levanta el servidor en puerto `3105` y verifica:

- payload legacy aceptado
- payload `magi.snapshot.v2` valido aceptado
- payload v2 invalido rechazado con `400`
- `GET /analisis/:symbol` mantiene forma compatible con Bot B

## Riesgos pendientes

- `daily_drawdown_percent` real sigue pendiente en Bot A.
- `risk_percent_per_trade` real sigue pendiente en Bot A.
- `news_context` sigue llegando vacio si Bot A manda `news: []`.
- Multiples posiciones abiertas aun no tienen detalle individual completo por posicion.
- El motor MVP actual sigue siendo una capa transicional; el snapshot v2 ya queda normalizado para alimentar Melchor, Baltasar, Gaspar y CEO-MAGI, pero la orquestacion modular completa no fue cambiada en esta tarea.
