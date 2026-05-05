# Reporte final: MAGI demo listo para conexion MT5

## Estado final

**LISTO PARA CONECTAR MT5**

El backend quedo preparado para arrancar con un comando unico, validar carpetas/permisos, exponer health check operativo, mostrar logs claros de conexion MT5 y verificar automaticamente el flujo end-to-end local.

## Que se preparo

### Scripts

- `npm run start:demo`
  - valida puerto disponible
  - arranca servidor con `DEMO_MODE=true`
  - muestra URL base y endpoints clave
  - deja el backend esperando conexion desde MT5

- `npm run verify:demo-ready`
  - levanta backend en puerto temporal
  - valida `/health`
  - valida carpetas requeridas y escritura
  - valida logs de arranque
  - ejecuta `npm run test:e2e-demo`

### Health check

`GET /health` devuelve:

```json
{
  "status": "ok",
  "timestamp": "...",
  "services": {
    "snapshots": true,
    "execution": true,
    "audit": true
  }
}
```

### Carpetas verificadas

El backend crea/verifica:

- `data/`
- `data/audit/`
- `data/snapshots/`
- `data/execution/`

Tambien valida escritura con probes temporales.

### Logs de arranque

Al iniciar se imprime:

- puerto activo
- URL base
- ruta de datos
- endpoints `/analisis`, `/api/overview`, `/api/snapshots`
- ultimo snapshot recibido
- estado del journal
- `MAGI backend listo para conexion MT5`
- `Esperando conexion desde MT5...`

### Logs en caliente

Cuando llega `POST /analisis`:

- `symbol`
- `snapshot_id`
- `source_mode`
- `validation.is_valid`
- warnings del adapter
- warnings demo si riesgo real llega en placeholder

Cuando se genera decision:

- `decision_id`
- `action`
- `symbol`
- confirmacion del audit journal

## Archivos creados/modificados

### Creados

- `scripts/start-demo.mjs`
- `scripts/verify-demo-ready.mjs`
- `docs/run-magi-demo.md`
- `docs/demo-ready-report.md`

### Modificados

- `package.json`
- `src/server/index.js`
- `src/server/services/storage.js`

## Como ejecutar

Desde `servidor-prosperity`:

```bash
npm run verify:demo-ready
npm run start:demo
```

URL base:

```text
http://localhost:3000
```

Endpoints clave:

```text
POST /analisis
GET /health
GET /api/overview
GET /api/snapshots
GET /api/execution
GET /analisis/:symbol
```

## Que validar en MT5

1. Agregar `http://localhost:3000` a WebRequest permitido.
2. Configurar Bot A para enviar a `http://localhost:3000/analisis`.
3. Configurar Bot B con `ServerURL=http://localhost:3000/analisis`.
4. Cargar Bot C como observador.
5. Confirmar en consola backend:
   - `[BotA] ... valid=true`
   - `[MAGI] decision_id=... audit_journal=saved`
6. Confirmar archivos:
   - `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`
   - `data/snapshots/normalized/`
   - `data/execution/{SYMBOL}.json`
   - `MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl`

## Resultado de verificacion

La verificacion automatica esperada debe reportar:

```json
{
  "ok": true,
  "checks": [
    "Backend levanta sin errores",
    "/health responde OK",
    "Carpetas requeridas existen y son escribibles",
    "Logs de arranque contienen mensaje MT5",
    "Test end-to-end pasa"
  ]
}
```

## Riesgos pendientes

- Falta compilar Bot B/Bot C en MetaEditor.
- Bot A aun debe conectarse desde MT5 real.
- Risk fields reales (`daily_drawdown_percent`, `risk_percent_per_trade`) pueden llegar como placeholder; en demo se advierte sin bloquear.
- La ejecucion real depende de permisos WebRequest y configuracion de MT5.

## Conclusion

El backend quedo listo para que el usuario ejecute:

```bash
npm run start:demo
```

y conecte MT5 sin configuracion manual adicional del lado backend.

Estado final: **LISTO PARA CONECTAR MT5**.
