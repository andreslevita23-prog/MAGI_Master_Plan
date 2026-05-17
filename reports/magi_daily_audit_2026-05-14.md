# Auditoria diaria MAGI live-demo

Fecha auditada: jueves `2026-05-14` America/Bogota.

Fuentes revisadas:

- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\snapshots\normalized`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\audit\decisions\2026-05-14\magi_decisions.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\logs\2026-05-14`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\execution\EURUSD.json`
- `<MAGI_BOT_C_AUDIT_DIR>\2026-05-14\bot_c_events.jsonl`

No se modifico codigo. No se hizo commit.

## 1. Resumen ejecutivo

| Campo | Valor |
| --- | --- |
| Inicio dia local | `2026-05-14T05:00:00Z` |
| Fin dia local teorico | `2026-05-15T04:59:59Z` |
| Primer snapshot | `2026-05-14T05:00:00Z` |
| Ultimo snapshot disponible | `2026-05-14T21:25:00Z` |
| Duracion efectiva | 16.42h |

| Metrica | Valor |
| --- | ---: |
| Snapshots recibidos | 198 |
| Snapshots validos | 198 |
| Decisiones generadas | 199 |
| HOLD | 196 |
| OPEN | 2 |
| MODIFY | 1 |
| CLOSE / close_for_safety | 0 |
| Operaciones organicas | 2 |
| Operaciones sinteticas | 0 |
| Profit organico cerrado | +1.78 |
| Profit sintetico | 0.00 |
| Operacion abierta al corte | 1 |
| Errores graves backend/Bot B | 0 |
| Anomalias Bot C | 1 |

Respuesta directa:

| Pregunta | Respuesta |
| --- | --- |
| MAGI estuvo estable? | Si. Proceso datos, abrio trades y ejecuto un modify sin errores graves. |
| Hubo comportamiento extrano? | No. Los OPEN fueron SELL coherentes con setup bajista. |
| Hubo desalineaciones? | No graves. Bot C sigue sin poder conservar decision_id en cierre TP. |

Dictamen: **estable y operativo, con gestion activa puntual a breakeven**.

## 2. Operaciones del dia

### A. Organicas reales

| Ticket | Decision | Snapshot | Simbolo | Tipo | Apertura | Cierre | Duracion | Entrada | SL | TP | Profit | Resultado | Sesion | Melchor | Risk |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| `8632100564` | `magi_557b0b388628fa66` | `EURUSD_M5_2026-05-14T15:00:00_live` | EURUSD | SELL | `2026-05-14T12:00:29Z` | `2026-05-14T14:57:55Z` | 177.4m | 1.17013 | 1.17075 | 1.16835 | +1.78 | TP | overlap | ALLOW | LOW |
| `8636685436` | `magi_3a1e48188fce279e` | `EURUSD_M5_2026-05-14T18:00:00_live` | EURUSD | SELL | `2026-05-14T15:00:29Z` | abierta | n/a | 1.16775 | 1.16882 -> 1.16775 | 1.16594 | n/a | abierta/protegida | new_york | ALLOW | MEDIUM |

### B. Sinteticas/controladas

No hubo operaciones sinteticas/controladas el jueves 14.

## 3. Analisis de operaciones

### Trade 1: SELL ganador por TP

| Campo | Valor |
| --- | --- |
| Ticket | `8632100564` |
| Reason | `Caso MVP detectado: confluencia bajista H1/H4 con RSI y EMAs alineadas.` |
| Spread | 0.2 |
| MFE aprox. | +17.8 pips |
| MAE aprox. | -4.5 pips |
| Distancia al TP al cierre | 0.0 pips |
| Continuacion despues del TP | Si, el minimo posterior llego a 1.16646 |

Condiciones de entrada:

| TF | Estructura | Direction | RSI | EMA20 | EMA50 | EMA bajista OK |
| --- | --- | --- | ---: | ---: | ---: | --- |
| H1 | downtrend | bearish | 37.10 | 1.17115125 | 1.17218618 | true |
| H4 | downtrend | bearish | 40.44 | 1.17300045 | 1.17338997 | true |

Lectura: entrada coherente con reglas bajistas. No hay evidencia de mala entrada; el trade alcanzo TP y continuo a favor despues.

### Trade 2: SELL abierto y protegido a BE

| Campo | Valor |
| --- | --- |
| Ticket | `8636685436` |
| Reason | `Caso MVP detectado: confluencia bajista H1/H4 con RSI y EMAs alineadas.` |
| Spread | 0.2 |
| MFE aprox. hasta corte | +11.0 pips |
| MAE aprox. hasta corte | -3.6 pips |
| Estado | abierto |
| Gestion aplicada | `modify` a breakeven |
| SL original | 1.16882 |
| SL luego de gestion | 1.16775 |
| TP conservado | 1.16594 |

Condiciones de entrada:

| TF | Estructura | Direction | RSI | EMA20 | EMA50 | EMA bajista OK |
| --- | --- | --- | ---: | ---: | ---: | --- |
| H1 | downtrend | bearish | 26.04 | 1.17053662 | 1.17180533 | true |
| H4 | downtrend | bearish | 36.13 | 1.17268708 | 1.17324566 | true |

Lectura: entrada coherente con reglas bajistas. El avance a favor justifico gestion de riesgo. No hay cierre al corte, por tanto no se evalua win/loss final.

## 4. Gestion de posicion

| Accion | Evidencia |
| --- | --- |
| move_to_breakeven | Ejecutado como `modify` operativo a BE |
| protect | No como action directa |
| trailing | No aparece |
| modify | Si, `magi_be_d192c10bf8` |
| close_for_safety | No aparece |

Decision de gestion:

| Campo | Valor |
| --- | --- |
| Decision id | `magi_be_d192c10bf8` |
| Action | `modify` |
| Reason | `protect_capital_breakeven` |
| Source | `MAGI risk management / operator-approved` |
| SL anterior | 1.16882 |
| SL nuevo | 1.16775 |
| TP | 1.16594 |
| Confirmacion Bot C | `position_update` a `2026-05-14T21:22:00Z` |

Bot C confirma SL `1.16775000` y TP `1.16594000` despues del ajuste.

## 5. Auditoria Bot B

| Verificacion | Resultado |
| --- | ---: |
| Payloads Bot B | 199 |
| Duplicados detectados | 0 |
| Rechazos | 0 |
| Errores HTTP | 0 |
| Operaciones simultaneas | 0 |
| Coherencia execution/backend | Correcta |

Bot B ejecuto dos OPEN y un MODIFY. No hay evidencia de duplicacion.

## 6. Auditoria Bot C

| Evento | Total |
| --- | ---: |
| open | 2 |
| close | 1 |
| floating_snapshot | 564 |
| position_update | 3 |
| `orden_sin_decision_id` | 1 |

Contexto de anomalia: el cierre por TP del ticket `8632100564` quedo con comment `[tp 1.16835]`, sin decision_id. Es el problema conocido de MT5/Bot C: el deal de cierre no conserva el comment MAGI original.

## 7. Comportamiento del motor MVP

Causas principales de HOLD:

| Causa observada | Conteo |
| --- | ---: |
| Posicion abierta | 112 |
| H1 no uptrend | 172 |
| H4 no uptrend | 196 |
| RSI H1 < 55 | 196 |
| RSI H4 < 55 | 196 |
| EMA H1 no alineada alcista | 196 |
| EMA H4 no alineada alcista | 196 |

Nota: estos contadores de HOLD estan orientados a condiciones alcistas; el dia fue bajista. Los OPEN surgieron por el bloque bearish, no por setup bullish.

Sesiones con actividad:

| Sesion | Snapshots | OPEN |
| --- | ---: | ---: |
| london | 48 | 0 |
| overlap | 48 | 1 |
| new_york | 72 | 1 |
| inactive | 24 | 0 |
| asia | 6 | 0 |

London no fue dominante en ejecucion. La actividad real aparecio en overlap y New York.

## 8. Estadisticas del dia

| Metrica | Valor |
| --- | ---: |
| Snapshots/hora efectiva | 12.06 |
| Decisiones/hora efectiva | 12.12 |
| HOLD % | 98.49% |
| OPEN % | 1.01% |
| MODIFY % | 0.50% |
| Win rate organico cerrado | 100% |
| Profit organico cerrado | +1.78 |
| Profit sintetico | 0.00 |
| Duracion promedio trades cerrados | 177.4 min |
| Tiempo promedio entre opens | 180 min |

## 9. Veredicto

| Pregunta | Respuesta |
| --- | --- |
| MAGI sigue estable? | Si. |
| Las operaciones fueron coherentes? | Si, ambas SELL cumplian estructura/RSI/EMA bajista. |
| Confianza aumenta o disminuye? | Aumenta en ejecucion y gestion de riesgo. |
| Cuello de botella | Gestion sigue siendo tema clave, aunque hoy ya hubo BE puntual. |
| Hay senales para estudiar break-even? | Si. El segundo trade tuvo MFE de +11 pips y se protegió correctamente. |

## 10. Recomendaciones

### No tocar todavia

- No cambiar reglas de entrada por un dia bueno.
- No concluir rentabilidad por dos SELL.
- No mezclar la proteccion manual aprobada con una regla automatica ya formalizada.

### Planear

| Prioridad | Tema | Motivo |
| --- | --- | --- |
| Alta | Formalizar regla de breakeven | Hoy funciono via `modify` operator-approved. |
| Alta | Bot C `ticket -> decision_id` | Sigue `orden_sin_decision_id` en cierres. |
| Media | MFE/MAE por trade | Necesario para decidir BE automatico. |
| Media | Gestion activa | Convertir proteccion puntual en politica verificable. |
| Alta | Riesgo real/drawdown real | Sigue pendiente para fase seria. |

Conclusion: jueves 14 fue el dia mas fuerte operativamente: dos SELL coherentes, un TP confirmado y una posicion protegida a breakeven sin cerrar ni modificar TP.
