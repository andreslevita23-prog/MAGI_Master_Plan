# Auditoria MAGI 24h live/demo

Periodo auditado: primera corrida live/demo de aproximadamente 24 horas.

Fuentes principales:

- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\snapshots\normalized`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\audit\decisions\2026-05-05\magi_decisions.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\audit\decisions\2026-05-06\magi_decisions.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\logs\2026-05-05\system.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\logs\2026-05-06\system.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\logs\2026-05-06\botB.jsonl`
- `<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_events.jsonl`
- `<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_daily_summary.json`

No se modifico codigo. No se hizo commit.

## 1. Resumen general

MAGI se mantuvo recibiendo mercado real durante aproximadamente `24.42h`, desde `2026-05-05T21:35:06Z` hasta `2026-05-06T22:00:21Z`, con snapshots M5 de EURUSD.

Resumen consolidado:

| Metrica | Valor |
| --- | ---: |
| Duracion auditada por snapshots live | 24.42h |
| Snapshots normalizados totales en carpeta | 298 |
| Snapshots live EURUSD | 289 |
| Snapshots sinteticos/test | 8 |
| Decisiones auditadas EURUSD/EURUSD_TEST | 297 |
| Decisiones organicas EURUSD | 289 |
| Decisiones sinteticas/test | 8 |
| HOLD total | 290 |
| OPEN total | 4 |
| close_for_safety total | 3 |
| OPEN organicos | 1 |
| OPEN sinteticos | 3 |
| Cierres registrados por Bot C | 4 |
| Eventos Bot C | 122 |
| Anomalias Bot C | 4 |
| Profit demo por eventos Bot C | -0.83 |

Dictamen ejecutivo: **MAGI se comporto correctamente durante la ventana auditada**. Hubo una operacion organica real, coherente con la logica del motor MVP, ejecutada por Bot B y registrada por Bot C. No hay evidencia de fallo grave del backend ni de duplicacion de orden. Si hay pendientes operativos importantes antes de una fase demo seria prolongada.

## 2. Snapshots y decisiones

### Snapshots

| Campo | Valor |
| --- | --- |
| Primer snapshot live | `EURUSD_M5_2026-05-06T00:35:00_live` |
| Timestamp primer snapshot | `2026-05-05T21:35:06.000Z` |
| Ultimo snapshot live | `EURUSD_M5_2026-05-07T01:00:00_live` |
| Timestamp ultimo snapshot | `2026-05-06T22:00:21.000Z` |
| Frecuencia media | 11.83 snapshots/hora |
| Gap relevante | 30.35 min entre `00:30` y `01:00` |

Sesiones detectadas en snapshots live:

| Sesion | Snapshots |
| --- | ---: |
| asia | 85 |
| london | 60 |
| overlap | 48 |
| new_york | 72 |
| inactive | 24 |

### Decisiones

| Grupo | Total | HOLD | OPEN | close_for_safety |
| --- | ---: | ---: | ---: | ---: |
| Todas | 297 | 290 | 4 | 3 |
| Organicas EURUSD | 289 | 288 | 1 | 0 |
| Sinteticas/test | 8 | 2 | 3 | 3 |

Tiempos:

| Campo | Valor |
| --- | --- |
| Primera decision auditada | `EURUSD_M5_2026-05-06T00:35:00_live` |
| Hora primera decision | `2026-05-05T21:35:08.017Z` |
| Ultima decision auditada | `EURUSD_M5_2026-05-07T01:00:00_live` |
| Hora ultima decision | `2026-05-06T22:00:23.227Z` |
| Tiempo promedio entre decisiones | 4.95 min |
| Decisiones/hora | 12.16 |
| HOLD % total | 97.64% |
| OPEN % total | 1.35% |

### Errores de backend

En `2026-05-06/system.jsonl` no aparecen errores:

| Archivo | Eventos | Errores |
| --- | ---: | ---: |
| `data/logs/2026-05-06/system.jsonl` | 536 | 0 |
| `data/logs/2026-05-06/botB.jsonl` | 268 | 0 |

En `2026-05-05/system.jsonl` hay 5 `post_analisis_error`, pero corresponden a pruebas/control previas con payloads invalidos o JSON con byte extra, no a la corrida estable posterior:

- Falta de `symbol`.
- Falta de `current_price`.
- Error de parser JSON por caracter no whitespace despues del JSON.

## 3. Operaciones reales demo

Bot C registro 4 aperturas y 4 cierres:

| Tipo | Ticket | decision_id corto | Apertura UTC | Cierre UTC | Duracion | Lote | Entrada | SL | TP | Profit |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sintetica perfecta | 8503462726 | `magi_1db4a93` | 05:05:20 | 05:06:20 | 1.0 min | 0.01 | 1.17359 | 1.17200 | 1.17500 | -0.02 |
| Sintetica entrable | 8503549073 | `magi_ca81e4a` | 05:11:50 | 05:12:50 | 1.0 min | 0.01 | 1.17350 | 1.17220 | 1.17460 | 0.00 |
| Sintetica minima | 8503644149 | `magi_0560c94` | 05:18:20 | 05:19:50 | 1.5 min | 0.01 | 1.17318 | 1.17254 | 1.17494 | -0.02 |
| Organica real | 8515425225 | `magi_0a77b13` | 15:00:20 | 16:51:44 | 111.4 min | 0.01 | 1.17549 | 1.17470 | 1.17710 | -0.79 |

Separacion:

| Grupo | Aperturas | Cierres | Profit |
| --- | ---: | ---: | ---: |
| Sinteticas controladas | 3 | 3 | -0.04 |
| Organica real | 1 | 1 | -0.79 |
| Total por eventos Bot C | 4 | 4 | -0.83 |

Nota importante: el archivo `bot_c_daily_summary.json` actual muestra solo la operacion organica:

```json
{
  "operaciones_abiertas": 0,
  "operaciones_cerradas": 1,
  "profit_neto": -0.79,
  "posiciones_abiertas_al_cierre": 0,
  "anomalias": 1
}
```

Esto no coincide con el `bot_c_events.jsonl`, que conserva 4 aperturas y 4 cierres. La interpretacion mas probable es que el resumen diario fue reiniciado o recalculado parcialmente despues de un reinicio/ciclo del EA. Para auditoria historica, el JSONL de eventos es la fuente mas confiable.

## 4. Primera operacion organica real

La primera operacion organica fue abierta sin señal sintetica:

| Campo | Valor |
| --- | --- |
| Snapshot | `EURUSD_M5_2026-05-06T18:00:00_live` |
| Decision | `magi_0a77b132230ea375` |
| Hora decision | `2026-05-06T15:00:01.855Z` |
| Accion | `open` |
| Direccion | `buy` |
| Sesion | `new_york` |
| Precio snapshot | 1.17550 |
| Spread | 0.2 pips |
| Lote | 0.01 |
| SL decision | 1.17470 |
| TP decision | 1.17710 |
| Ticket MT5 | 8515425225 |
| Entrada real Bot C | 1.17549 |
| Cierre | SL |
| Precio cierre | 1.17470 |
| Profit | -0.79 |
| Duracion | 111.4 min |

### Condiciones tecnicas del snapshot organico

| Timeframe | Estructura | Direccion | RSI | EMA20 | EMA50 | EMA OK |
| --- | --- | --- | ---: | ---: | ---: | --- |
| H1 | uptrend | bullish | 61.00 | 1.17393522 | 1.17223918 | si |
| H4 | uptrend | bullish | 61.98 | 1.17164108 | 1.17149378 | si |

Validacion:

- `validation.is_valid = true`
- `position.has_open_position = false`
- `allowed_actions` incluia `open`
- `daily_drawdown_percent = 0`
- `risk_percent_per_trade = 0`
- `news = []`

Voto Melchor:

```json
{
  "vote": "ALLOW",
  "risk_block_recommendation": false,
  "risk_level": "LOW",
  "rules_triggered": [],
  "risk_reward_ratio": 2.0000000000002776,
  "preferred_rr": 2
}
```

Payload enviado a Bot B:

```json
{
  "action": "open",
  "id_operacion": "magi_0a77b132230ea375",
  "details": {
    "symbol": "EURUSD",
    "order_type": "buy",
    "entry_price": 1.1755,
    "stop_loss": 1.1747,
    "take_profit": 1.1771,
    "lot_size": 0.01,
    "comment": "MAGI|magi_0a77b13",
    "reason": "Caso MVP detectado: confluencia alcista H1/H4 con RSI y EMAs alineadas."
  },
  "decision_id": "magi_0a77b132230ea375",
  "snapshot_id": "EURUSD_M5_2026-05-06T18:00:00_live"
}
```

Comparacion con HOLD anteriores:

Los 5 HOLD inmediatamente anteriores (`17:35` a `17:55`) tuvieron la razon generica:

`No se crea caso: no hay confluencia minima suficiente para abrir entrada.`

En el snapshot `18:00`, por primera vez el motor encontro alineacion completa H1/H4 bajo sus reglas actuales. Despues de abrir, los HOLD siguientes cambiaron a:

`Se detecta posicion abierta. El MVP conserva gestion pasiva y no envia cambios todavia.`

Esto confirma que el sistema respeto una sola posicion por simbolo mientras la operacion estuvo abierta.

Comparacion con señales sinteticas:

| Caso | RSI H1/H4 | EMA H1 | EMA H4 | Resultado |
| --- | --- | --- | --- | --- |
| Sintetica perfecta | 64 / 64 | OK | OK | OPEN |
| Sintetica entrable | 58 / 55 | OK | OK | OPEN |
| Sintetica minima | 55 / 55 | OK | OK | OPEN |
| Organica real | 61 / 61.98 | OK | OK | OPEN |

La operacion organica fue coherente con las pruebas sinteticas: no fue una excepcion ni una desalineacion.

## 5. Auditoria Bot B

Evidencia backend:

- `data/logs/2026-05-06/botB.jsonl`
- `data/execution/EURUSD.json`

Resumen backend Bot B:

| Metrica | Valor |
| --- | ---: |
| Respuestas registradas en `botB.jsonl` | 268 |
| HOLD | 261 |
| OPEN | 4 |
| close_for_safety | 3 |
| Errores registrados | 0 |

Validaciones observadas:

- No hay evidencia backend de errores HTTP de Bot B en `2026-05-06`.
- No hay evidencia de duplicados ejecutados.
- Durante la operacion organica, las decisiones posteriores fueron HOLD por posicion abierta.
- El estado final en `data/execution/EURUSD.json` volvio a HOLD para `EURUSD_M5_2026-05-07T01:00:00_live`.

Limitacion: los logs internos completos del panel Experts/Journal de MT5 no estan en el repo. La evidencia de ejecucion real se basa en Bot C y en los archivos backend.

## 6. Auditoria Bot C

Bot C registro:

| Evento | Cantidad |
| --- | ---: |
| `open` | 4 |
| `close` | 4 |
| `floating_snapshot` | 113 |
| Eventos totales | 122 |
| Anomalias | 4 |

Anomalia detectada:

| Anomalia | Frecuencia |
| --- | ---: |
| `orden_sin_decision_id` | 4 |

Explicacion:

- Las aperturas conservan comment `MAGI|<short_id>` y Bot C extrae `decision_id`.
- Los cierres no conservan el mismo comment:
  - cierres sinteticos llegaron con `comment=""`.
  - cierre organico por SL llego con `comment="[sl 1.17470]"`.
- Por eso Bot C no puede extraer `decision_id` del deal de cierre y marca `orden_sin_decision_id`.

Gravedad real:

- No impide operar.
- No impide saber que el ticket se cerro.
- Si afecta trazabilidad completa decision -> ticket -> cierre.
- En auditoria seria, debe resolverse o compensarse correlacionando cierres por ticket/position id y no solo por comment.

Solucion probable:

1. Mantener un mapa local Bot C `ticket -> decision_id` desde el evento `open`.
2. Al ver `close` sin comment MAGI, buscar el `decision_id` por ticket.
3. Guardar en el evento de cierre el `decision_id` recuperado y marcar la fuente como `recovered_from_ticket_map`.
4. Recalcular `bot_c_daily_summary.json` desde `bot_c_events.jsonl`, no desde contadores volatiles.

## 7. Auditoria del motor MVP

Regla observada para BUY:

- `market_structure_H1 === "uptrend"`
- `market_structure_H4 === "uptrend"`
- `rsi14_H1 >= 55`
- `rsi14_H4 >= 55`
- `ema20_H1 > ema50_H1`
- `ema20_H4 > ema50_H4`

Conteo de causas sobre 288 HOLD organicos:

| Condicion faltante | Veces |
| --- | ---: |
| EMA H4 no cumple EMA20 > EMA50 | 185 |
| H1 no es uptrend | 157 |
| H4 no es uptrend | 97 |
| RSI H4 < 55 | 89 |
| EMA H1 no cumple EMA20 > EMA50 | 77 |
| RSI H1 < 55 | 29 |
| Posicion abierta | 22 |

Por sesion:

| Sesion | HOLD | EMA H4 no OK | H1 no uptrend | H4 no uptrend | RSI H4 < 55 | Posicion abierta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| asia | 85 | 77 | 48 | 49 | 77 | 0 |
| london | 60 | 60 | 36 | 0 | 12 | 0 |
| overlap | 48 | 48 | 12 | 0 | 0 | 0 |
| new_york | 71 | 0 | 37 | 24 | 0 | 22 |
| inactive | 24 | 0 | 24 | 24 | 0 | 0 |

Conclusion tecnica:

- EMA H4 siguio siendo el cuello de botella principal durante Asia/London/Overlap.
- En New York, cuando H4 ya estaba alineado, aparecio la primera operacion organica.
- El comportamiento coincide con la logica del codigo y con las pruebas sinteticas.

## 8. Estadisticas de 24h

| Metrica | Valor |
| --- | ---: |
| Snapshots/hora | 11.83 |
| Decisiones/hora | 12.16 |
| Tiempo promedio entre decisiones | 4.95 min |
| HOLD total | 97.64% |
| OPEN total | 1.35% |
| close_for_safety total | 1.01% |
| Operaciones demo ejecutadas | 4 |
| Operaciones organicas | 1 |
| Operaciones sinteticas | 3 |
| Profit demo por eventos Bot C | -0.83 |
| Profit organico | -0.79 |
| Duracion promedio total trades | 28.73 min |
| Duracion operacion organica | 111.4 min |
| Floating snapshots Bot C | 113 |

## 9. Veredicto

### MAGI se comporto correctamente?

Si. La operacion organica aparecio cuando las condiciones minimas se cumplieron. Antes de eso, el sistema sostuvo HOLD por falta de confluencia tecnica.

### Hubo fallos graves?

No hay evidencia de fallo grave en backend, Bot B o decision engine durante el 6 de mayo. Si hay pendientes de auditoria Bot C.

### Hubo señales de desalineacion?

No en la decision ni en la ejecucion. Si hay una desalineacion de trazabilidad en Bot C: el cierre no conserva `decision_id`.

### La operacion organica fue coherente?

Si. Fue BUY en New York con H1/H4 uptrend, RSI H1/H4 sobre 55 y EMAs alineadas. Melchor voto `ALLOW` con riesgo `LOW`.

### El sistema parece estable?

Si, con una salvedad: hubo un gap de 30.35 min entre snapshots al final de la ventana y el resumen diario de Bot C no coincide con el JSONL completo de eventos.

### Que tan cerca esta de una fase demo seria?

Esta cerca de una demo seria supervisada, no de dinero real. La base operativa funciona, pero faltan riesgo real, drawdown real, news context y trazabilidad completa de cierres.

## 10. Plan recomendado

### Cosas que NO deben tocarse todavia

- No cambiar reglas de entrada por una sola operacion organica perdedora.
- No relajar filtros por 24h de baja frecuencia.
- No subir lotaje.
- No pasar a dinero real.
- No confundir una perdida pequena demo con fallo de sistema.

### Correcciones necesarias

| Prioridad | Accion | Motivo |
| --- | --- | --- |
| Alta | Correlacionar cierres Bot C por ticket -> decision_id | Resolver `orden_sin_decision_id`. |
| Alta | Recalcular daily summary desde JSONL | Evitar resumen parcial tras reinicios. |
| Alta | Implementar/validar `risk_percent_per_trade` real | Live sigue enviando `0`. |
| Alta | Implementar/validar `daily_drawdown_percent` real | Bloqueo diario real no esta probado. |
| Media | Integrar `news_context` real | `news=[]` sigue dejando ciego el filtro de noticias. |
| Media | Revisar fallback M15 | Persistente, aunque no invalida snapshots. |
| Media | Monitorear gaps de snapshots | Hubo un gap de 30.35 min al final. |

### Prioridades operativas

1. Correr otra sesion London/New York completa sin señales sinteticas.
2. Confirmar si aparece otra operacion organica.
3. Validar si Bot B evita duplicados durante una posicion abierta.
4. Auditar si Bot C registra cierre por TP igual que por SL.
5. Revisar dashboard contra archivos JSONL, no solo summary.

### Riesgos

- Riesgo de auditoria incompleta si los cierres no se correlacionan por `decision_id`.
- Riesgo de operar sin drawdown real.
- Riesgo de operar en noticias por `news_context` vacio.
- Riesgo de tomar decisiones sobre muestra insuficiente.

## Conclusion final

MAGI completo su primera ventana de aproximadamente 24h con comportamiento tecnicamente coherente:

- recibio mercado real,
- sostuvo HOLD cuando faltaba confluencia,
- abrio una operacion organica cuando las reglas se cumplieron,
- Bot B ejecuto,
- Bot C audito,
- el dashboard/backend siguio operativo.

La operacion organica perdio por SL, pero eso no invalida el sistema. Lo relevante de esta auditoria no es rentabilidad sino reflejo, estabilidad y trazabilidad. El reflejo funciono. La estabilidad fue buena. La trazabilidad necesita mejorar en cierres y resumen diario.

Dictamen: **MAGI esta listo para una fase demo supervisada mas seria, todavia no para dinero real ni challenge de fondeo.**
