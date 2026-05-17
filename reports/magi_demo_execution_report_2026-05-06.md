# Informe ejecutivo MAGI demo - 2026-05-06

## 1. Resumen ejecutivo

Hoy MAGI pasó de estar simplemente conectado a quedar validado como flujo operativo demo de punta a punta:

`Bot A -> backend MAGI -> decision -> Bot B -> MT5 demo -> Bot C -> dashboard/auditoria`.

El sistema recibió snapshots reales de Bot A, los normalizó, generó decisiones, expuso payloads compatibles con Bot B, ejecutó operaciones sintéticas controladas en MT5 demo y registró eventos reales con Bot C.

Dictamen actual: **MAGI está vivo, estable y operativo en demo local controlada**. No está listo para dinero real. Sí está listo para seguir observación live y pruebas demo supervisadas.

Estado al cierre de esta revisión:

| Area | Estado |
| --- | --- |
| Conexión Bot A -> backend | Operativa |
| Normalización snapshot v2 | Operativa |
| Decisión MAGI | Operativa, conservadora en live |
| Bot B | Ejecuta payloads demo correctamente |
| Bot C | Registra aperturas/cierres, con anomalía conocida en cierres |
| Dashboard/API | Operativo con datos reales |
| Riesgo real | Pendiente |
| News context | Pendiente |

## 2. Línea de tiempo del día

| Momento / bloque | Evidencia | Resultado |
| --- | --- | --- |
| Corrida live prolongada | `servidor-prosperity/data/snapshots/normalized/` | Bot A generó snapshots live EURUSD durante varias horas. |
| Auditoría de snapshots | 98 snapshots live normalizados detectados hasta `EURUSD_M5_2026-05-06T08:40:00_live` | Snapshots válidos, con warnings operativos de riesgo/news. |
| Revisión de HOLD orgánicos | `servidor-prosperity/data/audit/decisions/2026-05-06/magi_decisions.jsonl` | Decisiones orgánicas mayormente HOLD por falta de confluencia mínima. |
| Prueba sintética perfecta | `EURUSD_M5_2026-05-06T08-00-00_buy_synthetic_live_execution_test_1778043908983` | MAGI generó OPEN y Bot B ejecutó. |
| Prueba sintética entrable | `EURUSD_M5_2026-05-06T08-10-00_buy_synthetic_acceptable_setup_1778044293805` | MAGI generó OPEN y Bot B ejecutó. |
| Prueba sintética umbral mínimo | `EURUSD_M5_2026-05-06T08-15-00_buy_synthetic_minimum_threshold_1778044697494` | MAGI generó OPEN con RSI 55/55 y EMAs apenas cruzadas. |
| Validación Bot B | `servidor-prosperity/data/execution/EURUSD.json` | Bot B leyó decisiones, ejecutó opens y cierres controlados. |
| Validación Bot C | `MQL5/Files/MAGI/audit/2026-05-06/bot_c_events.jsonl` | Bot C registró apertura, floating snapshot y cierre. |
| Validación dashboard/API | `/health`, `/api/overview`, `/api/snapshots`, `/api/execution`, `/api/logs` | Endpoints activos con datos reales. |

## 3. Evidencia técnica

### Snapshots live revisados

Rutas:

- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\snapshots\normalized`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\audit\decisions\2026-05-06\magi_decisions.jsonl`

Resumen detectado:

| Métrica | Valor |
| --- | ---: |
| Snapshots live EURUSD normalizados | 98 |
| Primer snapshot live detectado | `EURUSD_M5_2026-05-06T00:35:00_live` |
| Último snapshot live detectado | `EURUSD_M5_2026-05-06T08:40:00_live` |
| Sesión Asia | 77 |
| Sesión London | 21 |
| Decisiones auditadas del día | 77 |
| Decisiones sintéticas | 6 |

Ejemplos live relevantes:

| Snapshot | Sesión | Resultado | Causa principal |
| --- | --- | --- | --- |
| `EURUSD_M5_2026-05-06T06:55:00_live` | asia | HOLD | H1 bearish/downtrend, H4 RSI bajo 55 y EMAs no alineadas. |
| `EURUSD_M5_2026-05-06T08:20:00_live` | london | HOLD | H4 EMA20 < EMA50. |
| `EURUSD_M5_2026-05-06T08:25:00_live` | london | HOLD | H4 EMA20 < EMA50. |

### Snapshots sintéticos generados

| Tipo | Snapshot | Resultado |
| --- | --- | --- |
| Perfecta | `EURUSD_M5_2026-05-06T08-00-00_buy_synthetic_live_execution_test_1778043908983` | OPEN |
| Entrable | `EURUSD_M5_2026-05-06T08-10-00_buy_synthetic_acceptable_setup_1778044293805` | OPEN |
| Mínima | `EURUSD_M5_2026-05-06T08-15-00_buy_synthetic_minimum_threshold_1778044697494` | OPEN |

### Decision IDs relevantes

| Caso | decision_id | Acción | Comentario |
| --- | --- | --- | --- |
| Perfecta BUY | `magi_1db4a934b9082c6e` | `open` | `MAGI\|magi_1db4a93` |
| Cierre perfecta | `magi_69bdfcd1834c4029` | `close_for_safety` | Cierre controlado. |
| Entrable BUY | `magi_ca81e4aad5fbdaf2` | `open` | `MAGI\|magi_ca81e4a` |
| Cierre entrable | `magi_562d6e287c9c853e` | `close_for_safety` | Cierre controlado. |
| Mínima BUY | `magi_0560c94d91672310` | `open` | `MAGI\|magi_0560c94` |
| Cierre mínima | `magi_8b1b270e8c00fd52` | `close_for_safety` | Cierre controlado. |

### Tickets MT5 de prueba

Archivo Bot C:

`<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_events.jsonl`

| Caso | Ticket | Deal apertura | Precio apertura | SL | TP | Cierre | Profit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Perfecta | `8503462726` | `8096540860` | `1.17359000` | `1.17200000` | `1.17500000` | `8096552786` | `-0.02000000` |
| Entrable | `8503549073` | `8096641576` | `1.17350000` | `1.17220000` | `1.17460000` | `8096653680` | `0.00000000` |
| Mínima | `8503644149` | `8096747433` | `1.17318000` | `1.17254000` | `1.17494000` | `8096761253` | `-0.02000000` |

Resumen Bot C:

`<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_daily_summary.json`

```json
{
  "operaciones_abiertas": 3,
  "operaciones_cerradas": 3,
  "ganadoras": 0,
  "perdedoras": 2,
  "breakeven": 1,
  "profit_neto": -0.04,
  "posiciones_abiertas_al_cierre": 0,
  "anomalias": 3
}
```

### Endpoints dashboard confirmados

| Endpoint | Estado |
| --- | --- |
| `/health` | `status: ok`, servicios snapshots/execution/audit en `true` |
| `/api/overview` | Operativo, datos reales; uptime detectado sobre 29k segundos |
| `/api/snapshots` | Operativo, lista snapshots reales y sintéticos |
| `/api/execution` | Operativo, lee estado real de `data/execution` |
| `/api/logs` | Operativo, muestra eventos `snapshot_received` y `mvp_decision_ready` |

## 4. Qué quedó validado

### Bot A

- Envía snapshots `magi.snapshot.v2` al backend local.
- Genera snapshots válidos.
- Mantiene `symbol`, precio, sesión, MTF, features, account, position y validation.
- Sigue emitiendo warnings operativos por campos pendientes: riesgo real, drawdown real y news.

### Backend MAGI

- Acepta payload v2 y conserva persistencia.
- Escribe snapshots normalizados y legacy.
- Genera estado de ejecución para Bot B.
- Mantiene journal cognitivo en `data/audit/decisions/YYYY-MM-DD/magi_decisions.jsonl`.

### CEO-MAGI / motor MVP

- Hace HOLD cuando no hay confluencia mínima.
- Abre con setup perfecto, entrable y mínimo.
- La regla observada para BUY es binaria:
  - H1 `uptrend`
  - H4 `uptrend`
  - RSI H1/H4 >= 55
  - EMA20 H1/H4 > EMA50 H1/H4

### Melchor

- No bloqueó las entradas sintéticas.
- Votó `ALLOW` en los tres OPEN.
- Marcó `risk_level=MEDIUM` por `rr_below_preferred`, con RR calculado cerca de `1.9999999999997`.
- Forzó `close_for_safety` cuando el snapshot sintético de cierre puso `daily_drawdown_percent=1`.

### Bot B

- Leyó payloads desde `/analisis/EURUSD`.
- Ejecutó órdenes demo con lote `0.01`.
- Respetó comment compacto `MAGI|<short_id>`.
- Cerró las operaciones con `close_for_safety`.

### Bot C

- Registró aperturas, floating snapshots y cierres.
- Detectó ticket, deal, symbol, magic number, precio, volumen, SL/TP y profit.
- Detectó anomalía en cierres: `orden_sin_decision_id`.

### Dashboard

- Ya consume datos reales desde endpoints backend.
- Muestra snapshots, execution, overview y logs reales.

### Auditoría cognitiva

- Cada decisión queda con `decision_id`, `snapshot_id`, voto de Melchor, decisión CEO/MVP y `execution_payload`.
- La trazabilidad cognitiva existe; la trazabilidad operativa de cierres necesita mejora.

## 5. Hallazgos clave

1. MAGI no operó orgánicamente porque no había confluencia técnica completa.
2. La condición faltante principal en live London fue `EMA20 H4 > EMA50 H4`.
3. MAGI sí abre con señal perfecta.
4. MAGI sí abre con señal buena/entrable.
5. MAGI sí abre con señal mínima aceptable.
6. Melchor permitió las operaciones y marcó riesgo medio por RR apenas bajo 2 debido a precisión decimal.
7. Bot B ejecutó correctamente en cuenta demo.
8. Bot C registra apertura y cierre, pero los cierres quedan con `orden_sin_decision_id` porque MT5 no conserva comment en el deal de cierre.
9. La frecuencia offline en 6 meses no continuos fue de `357` operaciones, promedio `59.5` al mes, con alta variabilidad por régimen.

Frecuencia offline validada desde `artifacts/ceo_magi_v3`:

| Bloque | Meses | Operaciones |
| --- | ---: | ---: |
| 3 meses aleatorios | 2020-12, 2022-01, 2025-10 | 79 |
| 3 meses estrés | 2020-03, 2022-04, 2026-04 | 278 |
| Total 6 meses no continuos | 6 meses | 357 |

## 6. Qué NO debe concluirse

- No debe concluirse que MAGI está listo para dinero real.
- No debe concluirse que hay que ajustar reglas por 7 horas sin trades.
- No debe concluirse que MAGI es demasiado estricto o demasiado permisivo con esta muestra.
- No debe confundirse prueba sintética con rendimiento real.
- No debe confundirse ejecución demo con validación de rentabilidad.
- No debe asumirse que la frecuencia offline se replicará linealmente en una sesión live corta.

## 7. Riesgos y pendientes

| Prioridad | Pendiente | Riesgo |
| --- | --- | --- |
| Alta | Correlación de cierres Bot C con `decision_id` | Los cierres quedan auditados, pero no plenamente vinculados a la decisión MAGI. |
| Alta | `risk_percent_per_trade` real llega `0` en live | Melchor opera con placeholder, no con riesgo real completo. |
| Alta | `daily_drawdown_percent` real llega `0` en live | El bloqueo diario real todavía no está validado con cuenta. |
| Media | `news_context` sigue vacío | MAGI no bloquea por noticias reales. |
| Media | M15 fallback persistente | No invalida snapshots, pero sigue indicando problema de alineación/histórico M15. |
| Media | Validar operación orgánica no sintética | Falta ver una entrada real generada por mercado, no forzada. |
| Media | Precisión RR | `rr_below_preferred` aparece por `1.9999999999997`, conviene normalizar tolerancia. |
| Baja | Tabla frecuencia esperada vs live | Ayudará a calibrar expectativas por sesión/régimen. |

## 8. Proyección realista

### Corto plazo

MAGI debe seguir en demo controlada, idealmente durante London y New York. El objetivo inmediato no es rentabilidad, sino observar si aparece una operación orgánica y si toda la cadena la audita correctamente.

### 1 a 2 semanas

Prioridad en estabilizar auditoría, riesgo real, drawdown real, news context y trazabilidad de cierres. Si se consiguen varias sesiones live sin errores y al menos una operación orgánica auditada de punta a punta, el sistema gana madurez operativa.

### 1 mes

Se debería buscar una demo con métricas suficientes: número de snapshots, decisiones, operaciones orgánicas, rechazos, errores, drawdown, consistencia de Bot C y discrepancias entre decisión y ejecución.

### 2 a 3 meses

Solo tendría sentido evaluar un challenge de fondeo pequeño si hay evidencia live suficiente: estabilidad, baja varianza, control de pérdidas, riesgo real funcionando, cierres trazables y disciplina de no intervenir reglas por ansiedad.

### 6 meses

Solo considerar una renuncia o dependencia financiera si hay consistencia real, retiros demostrados, baja varianza, reservas personales y operación estable en condiciones cambiantes. Hoy no estamos ahí. Hoy lo correcto es decir: MAGI está vivo y prometedor, pero todavía está en validación.

## 9. Plan de trabajo para mañana

Prioridad:

1. No tocar reglas de entrada.
2. Dejar correr MAGI en sesión London/New York.
3. Observar si aparece una operación orgánica.
4. Corregir o diseñar solución para Bot C y `orden_sin_decision_id`.
5. Revisar `risk_percent_per_trade` y `daily_drawdown_percent` reales.
6. Revisar `news_context`.
7. Revisar M15 fallback.
8. Preparar tabla de frecuencia esperada vs frecuencia live.
9. Documentar todo en un informe final si la sesión de mañana genera operación orgánica.

## 10. Entregables generados hoy

Este informe:

`C:\Users\Asus\Desktop\MAGI_Master_Plan\reports\magi_demo_execution_report_2026-05-06.md`

Archivos de evidencia principales:

- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\snapshots\normalized`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\audit\decisions\2026-05-06\magi_decisions.jsonl`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\servidor-prosperity\data\execution\EURUSD.json`
- `<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_events.jsonl`
- `<MAGI_BOT_C_AUDIT_DIR>\2026-05-06\bot_c_daily_summary.json`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\artifacts\ceo_magi_v3\random_3_months_monthly_summary.csv`
- `C:\Users\Asus\Desktop\MAGI_Master_Plan\artifacts\ceo_magi_v3\stress_months_monthly_summary_full.csv`

## Dictamen final

**MAGI está vivo, estable y operativo en demo local supervisada.**

La cadena completa funciona. Lo pendiente no es conectividad básica, sino madurez operativa: riesgo real, news, auditoría de cierres, validación orgánica y métricas live suficientes.
