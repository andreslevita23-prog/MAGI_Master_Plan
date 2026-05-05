# Estado actual de MAGI demo local

Fecha: 2026-05-05  
Repositorio: `servidor-prosperity`  
Contexto: demo local MT5 con Bot A, backend MAGI, Bot B, Bot C y dashboard.

## A. Resumen ejecutivo

MAGI ya esta vivo en demo local con flujo completo funcional en modo observacion:

```text
Bot A -> POST /analisis -> backend MAGI -> decision -> GET /analisis/:symbol -> Bot B
```

Tambien existe Bot C como caja negra operativa pasiva y un journal cognitivo en backend para reconstruir decisiones. El dashboard carga datos reales desde endpoints API y no depende de mocks para snapshots ni ejecucion.

### Que ya funciona

| Area | Estado | Evidencia |
| --- | --- | --- |
| Conexion MT5 local | Funcional | EAs apuntan a `http://127.0.0.1:3000`. |
| Transporte JSON MQL5 | Corregido | `MagiTransport.mqh` elimina terminador nulo antes de `WebRequest`. |
| Bot A snapshot v2 | Funcional | Backend acepta `magi.snapshot.v2` y guarda snapshot normalizado. |
| Fallback M15 | Funcional con warning | M15 ya no invalida todo el snapshot por fallo parcial de alineacion. |
| Backend MAGI | Funcional | Genera decision, persistencia y payload compatible con Bot B. |
| Bot B v3.0 | Seguro para demo | Lee decisiones, dedupe, bloquea duplicados y soporta acciones de proteccion. |
| Bot C | Implementado como observador | Pendiente validar eventos reales de MT5 en archivo local. |
| Dashboard | Operativo | `/api/overview`, `/api/snapshots` y `/api/execution` devuelven data real. |
| Journal cognitivo | Activo | `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`. |

### Que falta

- Riesgo real: `risk_percent_per_trade` sigue llegando en `0.0`.
- Drawdown real: `daily_drawdown_percent` sigue llegando en `0.0`.
- Noticias/contexto externo: `news` o `news_context` llega vacio.
- Confirmacion de Bot C con eventos reales de apertura/cierre/modificacion.
- Correccion de encoding raro en logs con tildes (`a.Â m.`, textos acentuados).
- Validacion de lotaje real antes de permitir `open` automatico.
- Corrida limpia de 4 a 6 horas despues del fix definitivo de M15.

### Dictamen actual

MAGI esta vivo en demo local, con flujo completo funcional en modo observacion. No esta listo aun para abrir operaciones automaticamente hasta cerrar riesgo, lotaje y auditoria operativa.

## B. Arquitectura funcional actual

### Bot A

Bot A corre en MT5 y envia snapshots tecnicos a:

```text
POST http://127.0.0.1:3000/analisis
```

Contrato principal actual:

```text
magi.snapshot.v2
```

El snapshot incluye simbolo, precio actual, timestamp, vela ancla, OHLC, estructura de mercado, indicadores, contexto multi-timeframe, cuenta, posicion, contexto Gaspar, validacion y notas operativas.

Correcciones relevantes:

- URL local por defecto.
- Includes relativos compatibles con `MQL5\Experts`.
- Transporte UTF-8 sin byte nulo final.
- Fallback M15 no critico.
- Marcador de version en `OnInit` para confirmar EA real cargado.

### Backend / CEO-MAGI

El backend Express recibe snapshots, detecta contrato legacy o `magi.snapshot.v2`, normaliza, persiste artefactos, evalua decision MVP y genera salida para Bot B.

Responsabilidades actuales:

- Adapter `magi.snapshot.v2`.
- Compatibilidad legacy.
- Persistencia de snapshots.
- Decision conservadora MVP.
- Journal cognitivo por decision.
- Payload compatible con Bot B.
- Endpoints para dashboard y salud.

### Bot B

Bot B consulta:

```text
GET http://127.0.0.1:3000/analisis/<SYMBOL>
```

Estado actual:

- Recibe `action`, `decision_id`, `snapshot_id`, `decision_time` y `details`.
- Reconoce `hold`, `do_nothing`, `open`, `close`, `close_for_safety`, `protect`, `move_to_breakeven` y `modify`.
- Evita duplicados por posicion existente y por decision persistida.
- Usa comment compacto `MAGI|<short_decision_id>`.
- Prioriza hold seguro ante payload incompleto o accion desconocida.

### Bot C

Bot C esta disenado como caja negra operativa pasiva. No abre, no cierra y no modifica operaciones. Debe registrar realidad MT5:

- Apertura.
- Cierre.
- Modificacion SL/TP.
- Ticket.
- Simbolo.
- Magic number.
- Comment.
- Decision ID extraido de comment.
- Precio ejecutado.
- SL/TP reales.
- Profit final.
- Anomalias.

Estado actual: implementado, pendiente validar evidencia real en `MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl` durante una sesion con eventos MT5.

### Dashboard

El dashboard consume endpoints reales:

- `GET /api/overview`
- `GET /api/snapshots?limit=12`
- `GET /api/execution`
- `GET /api/cases`
- `GET /api/logs`

No se detecto uso de datos mock para las secciones principales de snapshots y ejecucion.

### Auditoria y journals

Backend guarda decision cognitiva en:

```text
data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl
```

Cada registro incluye:

- `decision_id`
- `snapshot_id`
- `symbol`
- `decision_time`
- `final_action`
- `reason`
- `melchor_vote`
- `ceo_decision`
- `execution_payload`
- rutas de artefactos persistidos

## C. Flujo probado

### Bot A envia snapshot v2

Evidencia de backend en `data/logs/2026-05-05/system.jsonl`:

```json
{"event":"snapshot_received","snapshot_id":"EURUSD_M5_2026-05-06T01:05:00_live","symbol":"EURUSD","contract":"magi.snapshot.v2","is_valid":true,"issues":[]}
```

### Backend responde y genera decision

Evidencia:

```json
{"event":"mvp_decision_ready","snapshot_id":"EURUSD_M5_2026-05-06T01:05:00_live","decision_id":"magi_565f1d805022b953","symbol":"EURUSD","final_action":"hold"}
```

La prueba automatizada `npm run test:e2e-demo` confirma que `POST /analisis` acepta v2 valido y que el payload de Bot B contiene `decision_id`, `snapshot_id`, `decision_time` y comment `MAGI|short_id`.

### Bot B recibe decision nueva

Evidencia en `data/execution/EURUSD.json`:

```json
{
  "symbol": "EURUSD",
  "snapshot_id": "EURUSD_M5_2026-05-06T01:05:00_live",
  "response": {
    "action": "hold",
    "decision_id": "magi_565f1d805022b953",
    "snapshot_id": "EURUSD_M5_2026-05-06T01:05:00_live",
    "details": {
      "symbol": "EURUSD",
      "comment": "MAGI|magi_565f1d8"
    }
  }
}
```

### Dashboard lee snapshots reales

La prueba local de esta version en puerto aislado confirmo HTTP 200 en:

- `/health`
- `/api/overview`
- `/api/snapshots`
- `/api/execution`

`npm run test:e2e-demo` tambien valida que `/api/snapshots` incluye el snapshot v2 y que `/api/execution` incluye la decision v2.

### Fallback M15 funciona

Evidencia de snapshot real aceptado:

```json
{
  "mtf_alignment_status": "warning",
  "mtf_data_source_status": "PARTIAL_FALLBACK",
  "validation": { "is_valid": true, "issues": [] }
}
```

Detalle de feature M15:

```json
{
  "timeframe": "M15",
  "data_source_status": "FALLBACK_LATEST_CLOSED",
  "alignment_status": "fallback",
  "alignment_warning": "fallback aplicado; fallo MTF original: iTime no resolvio rango temporal con Bars=100011"
}
```

El fix definitivo tambien cubre el caso mas severo: si M15 no puede usar fallback, queda como `FALLBACK_FAILED`, `alignment_status="warning"` y no llama `MagiValidationAddIssue` por el fallo parcial.

## D. Correcciones implementadas

| Correccion | Estado |
| --- | --- |
| Adapter `magi.snapshot.v2` | Implementado. |
| Compatibilidad legacy | Conservada. |
| Dedupe y seguridad Bot B | Implementado en Bot B v3.0. |
| Acciones Bot B de proteccion | Implementadas: close, close_for_safety, protect, move_to_breakeven, modify. |
| Bot C caja negra | Implementado como observador pasivo. |
| Journal cognitivo | Implementado en JSONL diario. |
| Byte nulo MQL5 | Corregido en `MagiTransport.mqh`. |
| URL local MT5 | Defaults apuntan a `http://127.0.0.1:3000/analisis`. |
| Fallback M15 | Corregido para no invalidar snapshot completo. |
| Includes MT5 | Corregidos a rutas relativas bajo `core/`. |
| Endpoints dashboard reales | Implementados y verificados. |
| Dashboard con datos reales | Conectado a API real. |
| Scripts demo | `start:demo`, `verify:demo-ready`, `test:e2e-demo`, `test:snapshot-v2`. |

## E. Evidencia operativa

### Validaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `npm run check` | OK. |
| `npm run test:snapshot-v2` | OK: legacy, v2 valido, v2 invalido y `GET /analisis/:symbol`. |
| `npm run test:e2e-demo` | OK: flujo v2, legacy, journal, dashboard API y Bot B payload. |
| `npm run verify:demo-ready` | OK: backend levanta, `/health`, carpetas, logs de arranque y e2e. |
| `git diff --check` global | Fallo por whitespace en archivos fuera del scope MAGI demo: `../docs/ceo_magi_v3_full_report.md`. |
| `git diff --check` del scope MAGI demo | OK. Solo warnings esperados LF/CRLF. |

Salida relevante de `test:e2e-demo`:

```json
{
  "ok": true,
  "checks": [
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

Salida relevante de `verify:demo-ready`:

```json
{
  "ok": true,
  "health": {
    "status": "ok",
    "services": {
      "snapshots": true,
      "execution": true,
      "audit": true
    }
  }
}
```

### Nota sobre HTTP 200 de Bot A

El backend no persiste literalmente el codigo HTTP visto por MT5 en los JSONL. La evidencia persistida equivalente es `snapshot_received` con `is_valid=true` y `mvp_decision_ready` inmediatamente posterior. La prueba automatizada confirma HTTP exitoso para `POST /analisis` con payload v2.

## F. Limitaciones actuales

| Limitacion | Impacto | Prioridad |
| --- | --- | --- |
| `risk_percent_per_trade=0.0` | No hay riesgo real por trade. No habilitar `open` automatico con dinero real. | Alta |
| `daily_drawdown_percent=0.0` | Melchor no puede bloquear por drawdown diario real. | Alta |
| `news` / `news_context` vacio | Falta filtro/eventos macro. | Media |
| Encoding raro en logs | Dificulta auditoria humana con tildes y hora local. | Media |
| Bot C sin eventos reales confirmados | Caja negra implementada pero no comprobada con operaciones MT5 reales. | Alta |
| Decisiones mayormente `hold` | Sistema conservador; falta calibrar criterios de entrada y modulos completos Baltasar/Gaspar. | Media |
| Lotaje real pendiente | No probar ejecucion automatica hasta validar calculo y limites. | Alta |
| Datos runtime generados | No deben subirse snapshots/logs de corrida salvo muestras anonimizadas y justificadas. | Media |

## G. Estado de estabilidad

| Componente | Estado |
| --- | --- |
| Conexion | Estable en local con `127.0.0.1:3000`. |
| Transporte | Corregido; byte nulo removido antes de `WebRequest`. |
| Bot A | Estable con fallback M15; snapshots parciales siguen validos si H1/H4/D1 y campos criticos estan OK. |
| Backend | Estable para v2 y legacy en pruebas automatizadas. |
| Bot B | Lectura estable, ejecucion protegida, dedupe activo. |
| Bot C | Activo/implementado, pendiente validar eventos reales. |
| Dashboard | Operativo con datos reales. |
| Decision MAGI | Conservadora; `hold` como resultado dominante. |

Clasificacion operativa: estable con warnings.

## H. Siguiente plan

1. Hacer corrida limpia de 4 a 6 horas con backend actualizado y EAs recompilados.
2. Confirmar en MT5 el marcador de Bot A:

```text
[MAGI][DEBUG] Bot_A VERSION=M15_NON_CRITICAL_FIX_ACTIVE
```

3. Revisar dashboard y logs cada hora:

- `/api/overview`
- `/api/snapshots`
- `/api/execution`
- `data/logs/YYYY-MM-DD/system.jsonl`
- `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`

4. Validar Bot C con eventos reales, aunque sean controlados en demo.
5. Corregir encoding de logs.
6. Implementar riesgo real:

- `risk_percent_per_trade`
- `daily_drawdown_percent`
- limites por sesion/dia

7. Validar lotaje y limites de apertura.
8. Solo despues probar ejecucion controlada con lote minimo y simbolo unico.

## I. Dictamen final

MAGI esta vivo en demo local, con flujo completo funcional en modo observacion. No esta listo aun para abrir operaciones automaticamente hasta cerrar riesgo, lotaje y auditoria operativa.

Estado recomendado para la proxima etapa:

```text
DEMO LOCAL EN OBSERVACION CONTROLADA
```

No habilitar ejecucion real/open automatica hasta cerrar:

- riesgo real,
- drawdown diario real,
- lotaje,
- validacion Bot C con eventos reales,
- una corrida limpia de 4 a 6 horas sin errores criticos.
