# Implementacion MAGI Guardrails v1 prudente

Fecha: 2026-05-15

## 1. Resumen ejecutivo

Se implemento una version prudente de MAGI Guardrails v1 enfocada en gobernanza operativa, trazabilidad y demo realista. No se modificaron las reglas de entrada ni el core del edge: H1/H4, RSI, EMAs, Baltasar, direccion base y RR principal quedan intactos.

El unico bloqueo duro nuevo es SAFE_MODE por 3 SL consecutivos en el mismo simbolo/direccion/contexto. Friday Guardrail y Cluster 2SL quedan en modo sombra. BE automatico y news guardrail no se activan por falta de MFE/MAE y calendario objetivo.

## 2. Archivos modificados

| Archivo | Cambio |
| --- | --- |
| `servidor-prosperity/src/server/services/governance/operational-governance.service.js` | Nuevo servicio de memoria operativa, SAFE_MODE 3SL, shadow guardrails, lotaje demo y estado persistente. |
| `servidor-prosperity/src/server/services/orchestrator/mvp-decision-engine.js` | Envuelve cada decision con gobernanza operativa sin tocar la logica de entrada. |
| `servidor-prosperity/src/server/index.js` | Aplica lotaje demo, persiste estado operativo, expone `/api/governance` y agrega logs de gobernanza. |
| `servidor-prosperity/src/server/services/adapters/mt5/bot-b-response-mapper.js` | Incluye `risk_state`, `cluster_state`, `shadow_guardrails`, `current_lot_size`, placeholders BE/news en payload Bot B. |
| `servidor-prosperity/src/server/services/audit/decision-audit.service.js` | Guarda estado de riesgo, cluster, shadow guardrails, lotaje y demo_mode_until en journal cognitivo. |
| `servidor-prosperity/src/server/services/execution/execution-store.service.js` | Persiste estado operativo junto al payload de ejecucion. |
| `servidor-prosperity/src/server/services/execution/execution-query.service.js` | Expone campos de gobernanza en `/api/execution`. |
| `servidor-prosperity/src/server/services/system/system-status.service.js` | Expone estado de gobernanza en `/api/overview`. |
| `servidor-prosperity/src/client/scripts/dashboard.js` | Muestra SAFE_MODE, lotaje demo, cluster y shadow guardrails. |
| `servidor-prosperity/scripts/start-demo.mjs` | Arranca demo con `DEMO_MODE=true`, `MAGI_DEMO_LOT_SIZE=1.0`, `MAGI_DEMO_MODE_UNTIL=2026-06-05`. |
| `servidor-prosperity/.env.example` | Documenta variables demo y lotaje. |
| `servidor-prosperity/package.json` | Agrega `npm run test:guardrails-v1`. |
| `servidor-prosperity/scripts/test-guardrails-v1.mjs` | Prueba de lotaje demo, trazabilidad y hold seguro por SAFE_MODE. |
| `servidor-prosperity/scripts/test-melchor-risk-engine.mjs` | Ajuste de expectativa: Bot B usa comment compacto `MAGI|...` y reason conserva explicacion. |

## 3. Lotaje demo 1.0

El lotaje se cambia en backend, no en Bot B.

Punto de aplicacion:

| Lugar | Valor |
| --- | --- |
| `servidor-prosperity/scripts/start-demo.mjs` | `MAGI_DEMO_LOT_SIZE=1.0` por defecto al ejecutar `npm run start:demo`. |
| `servidor-prosperity/src/server/services/governance/operational-governance.service.js` | `applyDemoLotSizing()` convierte `decision.lot_size` a `1.0` solo si `DEMO_MODE=true` y `final_action=open`. |
| Payload Bot B | `details.lot_size: 1.0` cuando hay `open` en demo. |

Motivo: adaptacion psicologica, visualizacion realista de PnL, entrenamiento operativo y preparacion hasta el 5 de junio. No es una ampliacion de agresividad productiva.

Fuera de `DEMO_MODE=true`, el core MVP conserva su lotaje base.

## 4. Guardrails activos

### SAFE_MODE por 3 SL consecutivos

Activo como bloqueo real.

Condicion:

- mismo simbolo,
- misma direccion,
- mismo dia operativo Colombia,
- misma sesion o sesion inmediatamente posterior,
- gap compatible con cluster,
- 3 SL consecutivos dentro del cluster.

Efecto:

```json
{
  "action": "hold",
  "reason": "safe_mode_cluster_3_consecutive_sl",
  "risk_state": {
    "safe_mode_active": true,
    "cluster_consecutive_sl": 3,
    "blocked_direction": "SELL",
    "blocked_until": "..."
  }
}
```

Importante: solo bloquea la direccion afectada. No apaga MAGI completo.

## 5. Guardrails en shadow mode

No bloquean operaciones. Solo registran trazabilidad.

### Friday Guardrail shadow

Registra:

```json
{
  "friday_guardrail_would_block": true,
  "friday_reason": "friday_after_12co_sl_recent_or_deteriorated_context"
}
```

Condiciones observadas: viernes despues de 12:00 Colombia, SL reciente, spread deteriorado o cluster deteriorado.

### Cluster 2SL shadow

Registra:

```json
{
  "cluster_2sl_would_block": true,
  "cluster_2sl_reason": "two_consecutive_sl_same_direction_context"
}
```

No bloquea despues de 2 SL todavia.

## 6. No implementado todavia

| Guardrail | Estado | Motivo |
| --- | --- | --- |
| BE automatico | No activo | Falta dataset MFE/MAE por trade. |
| BE contextual | No activo | Falta MFE/MAE y contexto intratrade suficiente. |
| Friday hard block | No activo | La simulacion mostro sobre-restriccion y sacrificio de TP. |
| Bloqueo despues de 1 SL | No activo | No validado; demasiado agresivo. |
| Bloqueo despues de 2 SL | Shadow only | Aun reduce demasiado neto historico como regla dura. |
| News guardrail automatico | No activo | No hay calendario/noticias operable. |

Placeholders incluidos:

```json
"be_auto_status": "not_enabled_no_mfe_mae_dataset"
```

```json
"news_guardrail_status": "not_enabled_no_calendar"
```

## 7. Memoria operativa persistida

Campos disponibles en decision, audit journal, execution payload/API y estado operativo:

- `daily_sl_count`
- `daily_tp_count`
- `session_sl_count`
- `cluster_consecutive_sl`
- `cluster_sequence`
- `same_direction_recent_sl`
- `safe_mode_active`
- `safe_mode_reason`
- `blocked_until`
- `friday_risk`
- `recent_reentry_damage`
- `last_trade_result`
- `last_trade_direction`
- `last_trade_close_time`
- `shadow_guardrails`
- `current_lot_size`
- `demo_mode_until: 2026-06-05`

Estado persistente:

`servidor-prosperity/data/system/magi_operational_state.json`

API:

- `GET /api/governance`
- `GET /api/overview`
- `GET /api/execution`

## 8. Fuente de Bot C para memoria

La memoria usa eventos de Bot C cuando el backend puede leerlos. Para la demo real en MT5, configurar:

```env
MAGI_BOT_C_AUDIT_DIR=<MAGI_BOT_C_AUDIT_DIR>
```

Si esa variable no esta configurada, el backend busca por defecto en `servidor-prosperity/data/audit/bot_c`, y la memoria quedara incompleta.

## 9. Activacion y desactivacion de SAFE_MODE

Activacion:

1. Bot C registra cierres.
2. Backend reconstruye cierres por ticket/decision_id.
3. Si detecta 3 SL consecutivos en el mismo simbolo/direccion/contexto, `safe_mode_active=true`.
4. Si el siguiente candidato es `open` en esa misma direccion, CEO-MAGI lo degrada a `hold`.

Desactivacion:

- automatica al llegar `blocked_until`,
- calculada como siguiente sesion relevante o siguiente dia operativo,
- no requiere intervencion manual,
- no borra historial ni resetea auditoria.

## 10. Como validar el lunes

1. Confirmar `.env` o entorno:

```env
DEMO_MODE=true
MAGI_DEMO_LOT_SIZE=1.0
MAGI_DEMO_MODE_UNTIL=2026-06-05
MAGI_BOT_C_AUDIT_DIR=<ruta real MT5 MAGI/audit>
```

2. Iniciar backend:

```bash
npm run start:demo
```

3. Verificar consola:

- `MAGI demo lot size: 1`
- `MAGI demo mode until: 2026-06-05`
- logs `[MAGI][governance]`

4. Verificar endpoints:

- `http://127.0.0.1:3000/health`
- `http://127.0.0.1:3000/api/governance`
- `http://127.0.0.1:3000/api/execution`
- `http://127.0.0.1:3000/dashboard`

5. Cuando aparezca `open`, confirmar en `data/execution/EURUSD.json`:

- `details.lot_size = 1`
- `current_lot_size = 1`
- `risk_state`
- `cluster_state`
- `shadow_guardrails`

6. Confirmar que Bot B no abre si recibe:

```json
{
  "action": "hold",
  "reason": "safe_mode_cluster_3_consecutive_sl"
}
```

## 11. Revision diaria hasta el 5 de junio

Revisar cada dia:

- cantidad de operaciones reales,
- secuencia `cluster_sequence`,
- `cluster_consecutive_sl`,
- `shadow_guardrails.friday_guardrail_would_block`,
- `shadow_guardrails.cluster_2sl_would_block`,
- si SAFE_MODE se activo,
- si Bot B respeto `hold`,
- si Bot C conserva suficiente trazabilidad por ticket,
- PnL con lotaje 1.0,
- distancia real a limites diarios/totales.

## 12. Validaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `npm run check` | OK |
| `npm run test:guardrails-v1` | OK |
| `npm run test:melchor` | OK |
| `npm run test:snapshot-v2` | OK |
| `npm run test:e2e-demo` | OK en rerun; un intento previo fallo transitoriamente en `/api/snapshots?limit=5`. |
| `npm run verify:demo-ready` | OK |

## 13. Riesgos pendientes

- La memoria depende de que `MAGI_BOT_C_AUDIT_DIR` apunte a la ruta real de MT5 o de que los eventos Bot C se sincronicen al workspace.
- Cierres de MT5 pueden seguir llegando sin `decision_id`; el backend intenta reconstruir por ticket/contexto, pero la trazabilidad perfecta aun requiere mejorar Bot C.
- BE automatico sigue pendiente hasta tener MFE/MAE intratrade.
- Friday Guardrail sigue en modo sombra; no debe interpretarse como proteccion real.
- Operar demo con 1.0 lote aumenta impacto psicologico y visualizacion de PnL, pero no convierte al sistema en apto para dinero real.

## 14. Dictamen

MAGI Guardrails v1 queda implementado de forma prudente para demo: memoria operativa, trazabilidad, lotaje demo 1.0, SAFE_MODE 3SL reversible y shadow mode para reglas no aprobadas.

Dictamen: **LISTO PARA VALIDAR EN DEMO EL LUNES**, manteniendo observacion diaria hasta el 5 de junio.
