# Ejecutar MAGI demo backend

## Arranque

Desde `servidor-prosperity`:

```bash
npm run start:demo
```

El comando valida que el puerto este libre y arranca el backend con `DEMO_MODE=true`.

URL base por defecto:

```text
http://localhost:3000
```

Para usar otro puerto:

```bash
$env:PORT=3001
npm run start:demo
```

## URL para MT5

Bot A debe enviar snapshots a:

```text
http://localhost:3000/analisis
```

Bot B debe consultar:

```text
http://localhost:3000/analisis/EURUSD
http://localhost:3000/analisis/XAUUSD
```

En MT5, agregar la URL base a WebRequest:

```text
http://localhost:3000
```

Si usas dominio/tunel, configurar el valor equivalente.

## Endpoints para verificar

```text
GET http://localhost:3000/health
GET http://localhost:3000/api/overview
GET http://localhost:3000/api/snapshots
GET http://localhost:3000/api/execution
GET http://localhost:3000/analisis/EURUSD
```

`/health` debe devolver:

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

## Que ver en consola

Al iniciar:

```text
MAGI backend demo
Puerto activo: 3000
URL base: http://localhost:3000
Ruta de datos: ...
Journal audit activo: si (...)
MAGI backend listo para conexion MT5
Esperando conexion desde MT5...
```

Cuando llega Bot A:

```text
[BotA] contract=magi.snapshot.v2 symbol=EURUSD snapshot_id=... source_mode=live valid=true
```

Cuando se genera decision:

```text
[MAGI] decision_id=... action=... symbol=EURUSD audit_journal=saved
```

En `DEMO_MODE=true`, el backend advierte si llegan placeholders de riesgo como:

- `daily_drawdown_percent=0.0 placeholder`
- `risk_percent_per_trade=0.0 placeholder`

## Archivos de auditoria

Backend:

```text
data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl
data/snapshots/legacy/
data/snapshots/normalized/
data/execution/
data/analysis/
data/logs/
```

Bot C en MT5:

```text
MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl
MQL5/Files/MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json
```

## Verificacion automatica

```bash
npm run verify:demo-ready
```

Verifica:

- backend levanta
- `/health` responde OK
- carpetas existen y son escribibles
- logs de arranque aparecen
- test end-to-end local pasa

## Errores comunes

| Error | Causa probable | Accion |
|---|---|---|
| Puerto no disponible | Ya hay un servidor en 3000 | Cerrar proceso o usar `PORT=3001` |
| MT5 WebRequest falla | URL no autorizada en MT5 | Agregar `http://localhost:3000` en opciones de MT5 |
| `/health` sin audit true | Carpeta `data/audit` no escribible | Revisar permisos del proyecto |
| Bot B recibe hold | No hay decision operable o el MVP bloqueo | Revisar `data/execution/{SYMBOL}.json` y audit journal |
| No aparece journal | No llego `POST /analisis` valido | Revisar consola y `data/logs` |

## Secuencia recomendada

1. Ejecutar `npm run verify:demo-ready`.
2. Ejecutar `npm run start:demo`.
3. Abrir MT5 y habilitar WebRequest.
4. Compilar/cargar Bot A, Bot B y Bot C.
5. Enviar primer snapshot.
6. Confirmar consola y `data/audit/decisions`.
7. Confirmar Bot C local si Bot B ejecuta en demo.
