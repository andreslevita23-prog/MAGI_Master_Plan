# Informe de corrida nocturna MAGI demo - 2026-05-05

## Resumen ejecutivo

Dictamen: **INESTABLE**

La evidencia disponible en archivos no confirma una corrida continua de 9 horas. Los logs auditables del backend para `2026-05-05` cubren aproximadamente **1h49m**, desde `2026-05-05T06:17:19Z` hasta `2026-05-05T08:06:16Z`.

Durante esa ventana el backend sí procesó snapshots y generó decisiones, pero la corrida no puede considerarse estable para demo MT5 porque se observaron rechazos `HTTP 400` en `POST /analisis`. La causa principal registrada es doble:

| Tipo de error | Evidencia | Impacto |
| --- | --- | --- |
| Payload `magi.snapshot.v2` inválido | `symbol=""` y `current_price=0` | El adapter v2 rechaza el snapshot con `400`. |
| JSON con byte nulo final | `express.json`: `Unexpected non-whitespace character after JSON...` | El request se rechaza antes de entrar al handler de `/analisis`. |

No hay evidencia de ejecución real de órdenes. Todas las decisiones registradas fueron `hold`. No se encontraron eventos de Bot C ni archivos `bot_c_events.jsonl` o `bot_c_daily_summary.json`.

## Alcance y fuentes revisadas

| Fuente | Estado |
| --- | --- |
| `data/logs/2026-05-05/botA.jsonl` | Revisado |
| `data/logs/2026-05-05/botB.jsonl` | Revisado |
| `data/logs/2026-05-05/system.jsonl` | Revisado |
| `data/audit/decisions/2026-05-05/magi_decisions.jsonl` | Revisado |
| `data/snapshots/` | Revisado |
| `data/execution/` | Revisado |
| `data/analysis/` | Revisado |
| `data/votes/` | Revisado |
| `MAGI/audit/` / Bot C | No se encontraron eventos de Bot C en el workspace |

## 1. Resumen de la corrida

| Métrica | Resultado |
| --- | --- |
| Hora inicial detectada | `2026-05-05T06:17:19.020Z` |
| Hora final detectada | `2026-05-05T08:06:16.632Z` |
| Duración aproximada auditable | `1h 48m 57s` |
| Símbolos vistos en logs | `EURUSD`, `V2TEST`, `LEGTEST`, `E2EV2`, `E2ELEG`, `VERIFYDEMO` |
| Snapshots aceptados (`snapshot_received`) | 15 |
| Rechazos inferidos por adapter v2 | 7 |
| Rechazos por parser JSON | 1 |
| Total de POST inferidos | 23 |

Nota: varios símbolos (`V2TEST`, `LEGTEST`, `E2EV2`, `E2ELEG`, `VERIFYDEMO`) corresponden a pruebas locales/scripts, no a una corrida limpia de MT5. El único símbolo de mercado real visible en esa fecha es `EURUSD`, pero aparece como payload legacy de prueba, no como snapshot real `magi.snapshot.v2` aceptado desde MT5.

## 2. Bot A

| Aspecto | Resultado |
| --- | --- |
| Entradas en `botA.jsonl` | 22 |
| Payloads legacy registrados | 7 |
| Payloads `magi.snapshot.v2` registrados | 15 |
| Payloads v2 inválidos detectados en log | 7 |
| Payloads rechazados antes de `botA.jsonl` | 1 confirmado por parser JSON |
| Último payload aceptado | `E2ELEG_e2e_legacy_decision` a `2026-05-05T08:05:57.452Z` |

Errores detectados:

| Hora UTC | Error | Evidencia |
| --- | --- | --- |
| `2026-05-05T08:05:57.362Z` | v2 inválido | `symbol=""`, `current_price=0`; faltan campos críticos `symbol` y `current_price` válido. |
| `2026-05-05T08:05:57.445Z` | v2 inválido | `symbol=""`, `current_price=0`; faltan campos críticos `symbol` y `current_price` válido. |
| `2026-05-05T08:06:16.632Z` | JSON inválido por byte nulo final | `Unexpected non-whitespace character after JSON at position 110`. |

Gaps:

| Periodo | Observación |
| --- | --- |
| `06:23:00Z` a `06:50:13Z` | Sin eventos en logs. |
| `06:50:13Z` a `07:08:06Z` | Sin eventos en logs. |
| `07:08:06Z` a `07:50:10Z` | Sin eventos en logs. |

No hay evidencia en archivos de una secuencia continua de snapshots cada vela durante 9 horas.

## 3. Backend / MAGI

| Métrica | Resultado |
| --- | --- |
| Eventos `snapshot_received` | 15 |
| Decisiones generadas en `system.jsonl` | 15 |
| Distribución de acciones | `hold`: 15 |
| `decision_id` presente | En decisiones nuevas posteriores al journal: sí |
| `snapshot_id` presente | Sí en decisiones nuevas |
| Journal cognitivo | Existe, pero solo conserva 2 registros en `magi_decisions.jsonl` |
| Votos Melchor | Presentes en los 2 registros auditados |
| Votos Baltasar/Gaspar | `null` en registros auditados |
| CEO decision | Presente como `ceo_decision.source = "mvp_engine"` |

Distribución por contrato aceptado:

| Contrato | Cantidad aceptada |
| --- | ---: |
| `snapshot_legacy_mt5` | 7 |
| `magi.snapshot.v2` | 8 |

Distribución de acciones:

| Fuente | hold | open | close/protect/modify |
| --- | ---: | ---: | ---: |
| `system.jsonl` | 15 | 0 | 0 |
| `botB.jsonl` | 15 | 0 | 0 |
| `magi_decisions.jsonl` | 2 | 0 | 0 |

Warnings importantes:

| Warning | Frecuencia observada |
| --- | ---: |
| `daily_drawdown_percent` llega `0.0` | 8 snapshots v2 aceptados |
| `risk_percent_per_trade` llega `0.0` | 8 snapshots v2 aceptados |
| `news_context` no disponible / `news` vacío | 8 snapshots v2 aceptados |

## 4. Bot B

Bot B no registra directamente sus logs de MT5 en este backend; lo que existe en `data/logs/2026-05-05/botB.jsonl` son los payloads que el backend preparó/persistió para Bot B.

| Aspecto | Resultado |
| --- | --- |
| Payloads backend para Bot B | 15 |
| Acciones recibidas | Todas `hold` |
| Payloads con `decision_id` y `snapshot_id` | 11 de 15 |
| Payloads sin `decision_id` | 4 primeros eventos, anteriores al journal cognitivo completo |
| Intento de ejecución real | No hay evidencia |
| Bloqueos por dedupe/timestamp/URL | No hay evidencia en archivos del backend |
| Errores de parsing de Bot B | No hay evidencia |

Los payloads más recientes contienen `comment` compacto tipo `MAGI|magi_...`, por lo que son compatibles con trazabilidad de Bot C si se ejecutaran.

## 5. Bot C

No se encontraron archivos de auditoría operativa de Bot C:

| Archivo esperado | Resultado |
| --- | --- |
| `MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl` | No encontrado |
| `MAGI/audit/YYYY-MM-DD/bot_c_daily_summary.json` | No encontrado |

Conclusión Bot C: no hay evidencia de aperturas, cierres, modificaciones SL/TP, profit flotante, tickets, anomalías operativas ni resumen diario. Esto puede significar que Bot C no estaba cargado, no tuvo eventos que registrar, o escribió fuera del workspace auditado.

## 6. Error nocturno

### Error A: adapter v2 rechaza payload inválido

| Campo | Valor |
| --- | --- |
| Hora | `2026-05-05T08:05:57.362Z` y `2026-05-05T08:05:57.445Z` |
| Archivo | `data/logs/2026-05-05/system.jsonl` |
| Evento | `post_analisis_error` |
| Causa | `symbol=""` y `current_price=0` |
| Validación | Faltan campos críticos `"symbol"` y `"current_price" valido` |
| Impacto | El snapshot se rechaza con `HTTP 400`; no genera decisión ni journal |
| ¿Detuvo sistema? | No. El backend siguió procesando otros requests |

Corrección recomendada: revisar por qué el generador de payload de prueba/cliente está enviando snapshots v2 con `symbol` vacío y `current_price=0`. El adapter actuó correctamente al rechazarlo.

### Error B: JSON rechazado por byte nulo final

| Campo | Valor |
| --- | --- |
| Hora | `2026-05-05T08:06:16.632Z` |
| Archivo | `data/logs/2026-05-05/system.jsonl` |
| Evento | `post_analisis_error` |
| Parser | `express.json` |
| Mensaje | `Unexpected non-whitespace character after JSON at position 110 (line 1 column 111)` |
| Content-Type | `application/json` |
| Impacto | El request se rechaza antes del handler `/analisis`; no llega a adapter ni journal |
| ¿Detuvo sistema? | No. Es error de request, no caída del backend |

Corrección recomendada: asegurar que MT5 compile y use el `core/MagiTransport.mqh` actualizado que recorta explícitamente el terminador nulo antes de `WebRequest`.

## 7. Calidad de la data recolectada

| Campo / área | Estado |
| --- | --- |
| Estructura v2 | Completa en v2 aceptados de prueba |
| `gaspar_context` | Disponible en 15 entradas v2 registradas en `botA.jsonl` |
| `features` | Presentes en 15 entradas v2 registradas |
| `position` | Presente en 15 entradas v2 registradas |
| `account` | Presente en 15 entradas v2 registradas |
| `risk_percent_per_trade` | Llega como `0` en todos los v2 aceptados |
| `daily_drawdown_percent` | Llega como `0` en todos los v2 aceptados |
| `news` / `news_context` | `news: []` en todos los v2 aceptados |
| Encoding | Se observa texto raro en `timestamp_local` (`a.Â m.`), no afecta contratos JSON ni decisiones |

Los snapshots v2 aceptados son estructuralmente buenos para la integración técnica, pero todavía tienen placeholders operativos en riesgo y noticias. Para ejecución real conviene mantener modo conservador hasta completar riesgo real.

## 8. Archivos persistidos

| Área | Evidencia |
| --- | --- |
| `data/execution/EURUSD.json` | Existe, última modificación `2026-05-05 01:22:26` hora local |
| `data/analysis/EURUSD.json` | Existe, última modificación `2026-05-05 01:22:17` hora local |
| `data/audit/decisions/2026-05-05/magi_decisions.jsonl` | Existe, 2 registros |
| `data/snapshots/` | Solo quedan snapshots antiguos de `2026-04-20`; los snapshots de pruebas recientes no permanecen en carpeta al momento de auditoría |
| `data/votes/` | Sin archivos presentes al momento de auditoría |

Nota: el journal apunta a rutas de snapshots/votos que ya no existen al momento de revisar. Esto puede deberse a scripts de prueba que limpian artefactos temporales.

## 9. Conclusión

Clasificación final: **INESTABLE**

Motivos:

- No hay evidencia de una corrida real continua de 9 horas.
- Hay `HTTP 400` confirmados.
- El error de byte nulo impide que algunos POST lleguen al handler.
- Hay snapshots v2 inválidos con campos críticos vacíos.
- No hay evidencia de Bot C ni trazabilidad operativa MT5.
- Todas las decisiones fueron `hold`; no se validó ejecución controlada real.

El backend no parece haberse caído; el problema es de calidad/transporte de requests y de evidencia incompleta de corrida.

## 10. Recomendaciones

### Críticas antes de otra noche

1. Copiar y recompilar en MT5 el `core/MagiTransport.mqh` actualizado:
   - Origen: `servidor-prosperity/integrations/mt5/core/MagiTransport.mqh`
   - Destino: `MQL5/Experts/core/MagiTransport.mqh`
   - Recompilar: `Bot_A.mq5`
2. Validar en Experts de MT5 que aparezcan los logs:
   - `[MAGI][DEBUG] Bot_A VERSION=V3_TRANSPORT_FIX_ACTIVE`
   - `[MAGI][DEBUG][TRANSPORT] StringLen=... ArraySize=... removed_null=...`
3. Ejecutar una prueba corta de 15-30 minutos con símbolo real `EURUSD` y confirmar que aparecen snapshots v2 aceptados en `system.jsonl`.
4. Confirmar que Bot C está cargado y que crea `MAGI/audit/YYYY-MM-DD/bot_c_events.jsonl`.

### Menores

1. Corregir encoding de `timestamp_local` para evitar texto como `a.Â m.`.
2. Separar logs de pruebas (`V2TEST`, `E2EV2`, etc.) de logs de demo real.
3. Evitar que scripts de prueba limpien artefactos necesarios para auditoría si se está auditando una corrida.
4. Registrar explícitamente `HTTP 200`/`HTTP 400` por request en logs del backend.

### Ejecución controlada

No recomiendo pasar todavía a ejecución real, aunque sea demo, hasta completar una noche limpia solo con observación.

Estado recomendado para la próxima corrida: **mantener solo observación**, con Bot A + backend + Bot B leyendo `hold` + Bot C activo, hasta obtener evidencia continua sin `HTTP 400`.
