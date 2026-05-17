# Auditoria integral MAGI demo/live hasta 2026-05-15

Fecha de corte: 2026-05-15
Zona horaria operativa usada para el analisis diario: America/Bogota
Fuentes revisadas:

- `data/snapshots/normalized`
- `data/audit/decisions`
- `data/execution`
- `data/logs`
- `<MAGI_BOT_C_AUDIT_DIR>`

Este informe separa estrictamente rendimiento organico, pruebas sinteticas/controladas y acciones operativas aprobadas por operador. El resultado financiero normalizado usa la cuenta hipotetica solicitada de 100,000 USD:

- TP / ganadora: +1,000 USD
- SL / perdedora: -500 USD
- BE: 0 USD
- Safety parcial: se reporta aparte si no puede normalizarse limpiamente

## 1. Resumen ejecutivo

MAGI sigue vivo, operativo y trazable en demo. El flujo Bot A -> backend MAGI -> decision -> Bot B -> Bot C -> dashboard se mantuvo funcionando y genero operaciones reales organicas. La infraestructura mostro capacidad de recibir snapshots live, producir decisiones, entregar payload ejecutable a Bot B y registrar aperturas/cierres/modificaciones en Bot C.

El viernes 15 fue el dia mas debil de la demo: 7 operaciones organicas, 1 ganadora, 5 perdedoras y 1 BE. El resultado normalizado del viernes fue -1,500 USD (-1.5%). No se observa una ruptura del contrato tecnico ni un fallo grave de ejecucion; el problema principal fue operativo/estrategico: demasiadas reentradas SELL en una misma jornada de viernes, con varias entradas tardias en movimiento ya extendido, gestion mayormente pasiva, spreads menos favorables en dos entradas y ausencia de regla formal de apagado/reduccion por viernes o por racha de perdidas.

En la semana completa, MAGI quedo neutral bajo el modelo normalizado: 10 operaciones organicas, 3 ganadoras, 6 perdedoras y 1 BE, con neto normalizado de 0 USD. Desde el inicio de la demo/live, el resultado organico normalizado tambien queda en 0 USD si se excluye el cierre safety parcial no normalizado: 5 TP, 10 SL, 1 BE y 1 safety parcial.

Dictamen: MAGI esta estable en demo y sigue siendo prometedor, pero no esta listo para fondeo. Antes del 5 de junio deben cerrarse como minimo: gestion activa formal, break-even sistematico, limite diario/semanal de operaciones o perdidas, cierre viernes, riesgo/drawdown reales, noticias reales y trazabilidad Bot C `ticket -> decision_id`.

## 2. Reporte del viernes 15 de mayo

Ventana auditada local: 2026-05-15 00:00:00 a 2026-05-15 23:59:59 America/Bogota
Primer snapshot detectado: `EURUSD_M5_2026-05-15T08:00:00_live`
Ultimo snapshot detectado: `EURUSD_M5_2026-05-15T20:40:00_live`

| Metrica | Valor |
|---|---:|
| Snapshots live recibidos | 153 |
| Decisiones generadas | 154 |
| HOLD | 146 |
| OPEN | 7 |
| MODIFY | 1 |
| CLOSE | 0 |
| Operaciones organicas abiertas | 7 |
| Operaciones organicas cerradas | 7 |
| Ganadoras | 1 |
| Perdedoras | 5 |
| BE | 1 |
| Safety/viernes | 0 |
| Profit/loss demo observado | -1.82 |
| Resultado normalizado | -1,500 USD |
| Resultado normalizado % | -1.5% |

Distribucion por sesion en snapshots del viernes:

| Sesion | Snapshots |
|---|---:|
| London | 48 |
| Overlap | 48 |
| New York | 57 |

### Operaciones del viernes

| Ticket | Tipo | Apertura UTC | Cierre UTC | Entrada | SL inicial | TP | Cierre | Resultado | Profit demo | Resultado normalizado | Sesion |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| 8645768127 | SELL | 2026-05-15 05:00:30 | 2026-05-15 07:11:36 | 1.16469 | 1.16551 | 1.16311 | 1.16469 | BE | 0.00 | 0 | London |
| 8650330965 | SELL | 2026-05-15 09:00:30 | 2026-05-15 10:23:59 | 1.16330 | 1.16409 | 1.16169 | 1.16409 | SL | -0.79 | -500 | Overlap |
| 8652091231 | SELL | 2026-05-15 10:25:30 | 2026-05-15 10:45:14 | 1.16389 | 1.16464 | 1.16224 | 1.16464 | SL | -0.75 | -500 | Overlap |
| 8652574043 | SELL | 2026-05-15 10:50:30 | 2026-05-15 10:52:15 | 1.16450 | 1.16530 | 1.16290 | 1.16530 | SL | -0.80 | -500 | Overlap |
| 8652728652 | SELL | 2026-05-15 10:55:30 | 2026-05-15 11:44:58 | 1.16546 | 1.16640 | 1.16331 | 1.16331 | TP | +2.15 | +1,000 | Overlap |
| 8655084624 | SELL | 2026-05-15 13:00:30 | 2026-05-15 14:17:26 | 1.16254 | 1.16345 | 1.16105 | 1.16345 | SL | -0.91 | -500 | New York |
| 8659678120 | SELL | 2026-05-15 16:00:30 | 2026-05-15 17:10:44 | 1.16263 | 1.16335 | 1.16095 | 1.16335 | SL | -0.72 | -500 | New York |

### Lectura tecnica del viernes

Todas las entradas del viernes fueron SELL y estuvieron alineadas con la lectura macro del motor MVP: H1 y H4 bajistas, estructura bearish, EMA20 por debajo de EMA50 y RSI debil. Es decir, las entradas fueron coherentes con las reglas principales de direccion.

Lo que salio mal no parece ser una inversion aleatoria BUY/SELL ni una desalineacion Bot A/backend/Bot B. El problema fue la calidad operativa de la secuencia:

- Hubo demasiadas reentradas SELL en una sola jornada.
- Varias entradas aparecieron con RSI H1/H4 muy bajo, lo que sugiere entrada tardia en movimiento extendido.
- La operacion `8652574043` duro menos de 2 minutos y cerro en SL, con spread de 0.6 pips, lo que apunta a ruido/whipsaw y timing pobre.
- La operacion `8659678120` se abrio en New York tarde con spread de 1.0 pip, demasiado alto para el perfil conservador que se busca.
- No hubo una regla formal que frenara el sistema tras una racha de SL.
- No hubo regla formal de viernes/tarde para reducir o apagar riesgo.

### MFE/MAE aproximado del viernes

| Ticket | Resultado | MFE aprox. pips | MAE aprox. pips | Distancia faltante a TP aprox. |
|---|---|---:|---:|---:|
| 8645768127 | BE | 14.5 | 1.1 | 15.8 |
| 8650330965 | SL | 14.9 | 8.0 | 24.0 |
| 8652091231 | SL | 2.4 | 7.5 | 24.0 |
| 8652574043 | SL | 0.0 | 8.3 | 24.0 |
| 8652728652 | TP | 21.5 | 0.0 | 0.0 |
| 8655084624 | SL | 5.9 | 9.1 | 24.0 |
| 8659678120 | SL | 2.7 | 7.3 | 24.0 |

La primera operacion del viernes avanzo lo suficiente para justificar BE, y de hecho fue protegida. Dos operaciones posteriores tambien tuvieron MFE relevante antes de fallar, lo que refuerza que el cuello de botella no es solo entrada; tambien hay gestion y timing.

### Modificacion BE del viernes

Se registro una modificacion de SL a BE en la operacion `8645768127`.

| Campo | Valor |
|---|---|
| Action | `modify` |
| Reason | `protect_capital_breakeven_after_strong_favorable_move` |
| Source | `MAGI risk management / operator-approved` |
| SL nuevo | 1.16469 |
| TP conservado | 1.16311 |
| Registro Bot C | `position_update` detectado |
| Resultado final | BE |

### Debia apagarse MAGI por ser viernes?

MAGI no necesariamente debia estar apagado desde el inicio del viernes, porque la sesion London/overlap puede tener liquidez real. Pero con la evidencia del dia, si debia existir una proteccion formal para viernes:

- No abrir nuevas operaciones tarde en New York.
- Reducir riesgo o bloquear tras una racha de perdidas.
- Evitar nuevas entradas con spread degradado.
- Forzar cierre/reduccion antes del riesgo de fin de semana.

La ausencia de esa regla fue un problema operativo real del viernes.

## 3. Reporte semanal actual

Semana operativa auditada: lunes 2026-05-11 a viernes 2026-05-15.

| Metrica semanal | Valor |
|---|---:|
| Operaciones organicas | 10 |
| Ganadas | 3 |
| Perdidas | 6 |
| BE | 1 |
| Safety parcial | 0 |
| Win rate sobre TP/SL | 33.3% |
| Win rate sobre cerradas totales | 30.0% |
| Profit factor normalizado aprox. | 1.0 |
| Profit/loss demo observado | +0.98 |
| Resultado neto normalizado | 0 USD |
| Resultado neto normalizado % | 0.0% |
| Maximo balance semanal | 101,500 USD |
| Minimo balance semanal | 99,500 USD |
| Maximo drawdown semanal | 1,500 USD |
| Maximo drawdown semanal % | 1.5% |
| Mejor dia | 2026-05-14 |
| Dia mas debil | 2026-05-15 |

### Resultado por dia

| Dia | Operaciones organicas | TP | SL | BE | Profit demo | Resultado normalizado |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-11 | 1 | 0 | 1 | 0 | -0.78 | -500 |
| 2026-05-12 | 0 | 0 | 0 | 0 | 0.00 | 0 |
| 2026-05-13 | 0 | 0 | 0 | 0 | 0.00 | 0 |
| 2026-05-14 | 2 | 2 | 0 | 0 | +3.58 | +2,000 |
| 2026-05-15 | 7 | 1 | 5 | 1 | -1.82 | -1,500 |
| **Total** | **10** | **3** | **6** | **1** | **+0.98** | **0** |

### Sesiones de la semana

| Sesion | Operaciones | TP | SL | BE | Resultado normalizado |
|---|---:|---:|---:|---:|---:|
| London | 1 | 0 | 0 | 1 | 0 |
| Overlap | 6 | 2 | 4 | 0 | 0 |
| New York | 3 | 1 | 2 | 0 | 0 |

La semana termino plana bajo el modelo objetivo. El jueves mostro el mejor comportamiento: dos operaciones ganadoras, ejecucion limpia y una de ellas protegida. El viernes devolvio la ganancia semanal por sobreoperacion y secuencia de perdidas.

## 4. Reporte desde inicio de demo/live

Desde el primer dia operativo real de MAGI hasta el corte actual se detectaron 20 operaciones en total:

- 17 operaciones organicas reales.
- 3 operaciones sinteticas/controladas de infraestructura.
- 0 cierres manuales discrecionales detectados como intervencion directa desde MT5.
- 1 cierre safety parcial organico/controlado por viernes, ejecutado por flujo MAGI/Bot B.

### Resumen organico completo

| Metrica | Valor |
|---|---:|
| Operaciones organicas reales | 17 |
| TP / ganadoras | 5 |
| SL / perdedoras | 10 |
| BE | 1 |
| Safety parcial no normalizado | 1 |
| Win rate sobre TP/SL | 33.3% |
| Win rate sobre todas las cerradas | 29.4% |
| Profit/loss demo observado organico | +1.33 |
| Profit neto normalizado | 0 USD |
| Balance hipotetico actual | 100,000 USD |
| Maximo balance alcanzado | 101,500 USD |
| Minimo balance alcanzado | 99,500 USD |
| Maximo drawdown absoluto | 1,500 USD |
| Maximo drawdown porcentual | 1.5% |
| Peor racha de perdidas | 3 |
| Mejor racha de ganancias | 2 |

### Operaciones sinteticas/controladas

Las operaciones sinteticas fueron pruebas de infraestructura y reflejos Bot B/Bot C. No deben mezclarse con performance organica.

| Ticket | Tipo | Resultado | Profit demo | Incluir en performance organica |
|---|---|---|---:|---|
| 8503462726 | Sintetica/controlada | Cierre controlado/parcial | -0.02 | No |
| 8503549073 | Sintetica/controlada | BE/controlada | 0.00 | No |
| 8503644149 | Sintetica/controlada | Cierre controlado/parcial | -0.02 | No |

### Clasificacion completa de operaciones

| Fecha local aprox. | Tipo | Motivo | Ticket | BUY/SELL | Resultado | Profit demo | Incluir en performance organica |
|---|---|---|---|---|---|---:|---|
| 2026-05-06 | Sintetica | Prueba perfecta/infraestructura | 8503462726 | BUY/SELL test | Parcial/controlado | -0.02 | No |
| 2026-05-06 | Sintetica | Prueba entrable/infraestructura | 8503549073 | BUY/SELL test | BE/controlado | 0.00 | No |
| 2026-05-06 | Sintetica | Umbral minimo/infraestructura | 8503644149 | BUY/SELL test | Parcial/controlado | -0.02 | No |
| 2026-05-06 | Organica | Setup real | 8515425225 | SELL | SL | -0.79 | Si |
| 2026-05-07 | Organica | Setup real | 8523501566 | SELL | TP | +1.68 | Si |
| 2026-05-07 | Organica | Setup real | 8525528485 | SELL | SL | -0.82 | Si |
| 2026-05-08 | Organica | Setup real | 8547574064 | SELL | TP | +1.57 | Si |
| 2026-05-08 | Organica | Setup real | 8553314033 | SELL | SL | -1.02 | Si |
| 2026-05-08 | Organica | Setup real | 8554125215 | SELL | SL | -0.73 | Si |
| 2026-05-08 | Organica/safety | Cierre preventivo viernes | 8554497278 | SELL | Safety parcial | +0.46 | Reportar aparte |
| 2026-05-11 | Organica | Setup real | 8569477584 | SELL | SL | -0.78 | Si |
| 2026-05-14 | Organica | Setup real | 8632100564 | SELL | TP | +1.78 | Si |
| 2026-05-14 | Organica | Setup real + BE | 8636685436 | SELL | TP | +1.80 | Si |
| 2026-05-15 | Organica | Setup real + BE | 8645768127 | SELL | BE | 0.00 | Si |
| 2026-05-15 | Organica | Setup real | 8650330965 | SELL | SL | -0.79 | Si |
| 2026-05-15 | Organica | Setup real | 8652091231 | SELL | SL | -0.75 | Si |
| 2026-05-15 | Organica | Setup real | 8652574043 | SELL | SL | -0.80 | Si |
| 2026-05-15 | Organica | Setup real | 8652728652 | SELL | TP | +2.15 | Si |
| 2026-05-15 | Organica | Setup real | 8655084624 | SELL | SL | -0.91 | Si |
| 2026-05-15 | Organica | Setup real | 8659678120 | SELL | SL | -0.72 | Si |

### Equity curve normalizada organica

La operacion safety parcial se deja fuera del balance normalizado porque no corresponde a TP/SL/BE completo bajo el supuesto financiero solicitado.

| # | Cierre UTC | Ticket | Resultado | P/L normalizado | Balance | Drawdown desde pico |
|---:|---|---|---|---:|---:|---:|
| 0 | Inicio | - | - | 0 | 100,000 | 0 |
| 1 | 2026-05-06 16:51 | 8515425225 | SL | -500 | 99,500 | 500 |
| 2 | 2026-05-07 07:15 | 8523501566 | TP | +1,000 | 100,500 | 0 |
| 3 | 2026-05-07 16:08 | 8525528485 | SL | -500 | 100,000 | 500 |
| 4 | 2026-05-08 13:32 | 8547574064 | TP | +1,000 | 101,000 | 0 |
| 5 | 2026-05-08 14:00 | 8553314033 | SL | -500 | 100,500 | 500 |
| 6 | 2026-05-08 14:10 | 8554125215 | SL | -500 | 100,000 | 1,000 |
| 7 | 2026-05-08 18:27 | 8554497278 | Safety parcial | N/A | 100,000 | 1,000 |
| 8 | 2026-05-11 11:56 | 8569477584 | SL | -500 | 99,500 | 1,500 |
| 9 | 2026-05-14 14:57 | 8632100564 | TP | +1,000 | 100,500 | 500 |
| 10 | 2026-05-15 00:02 | 8636685436 | TP | +1,000 | 101,500 | 0 |
| 11 | 2026-05-15 07:11 | 8645768127 | BE | 0 | 101,500 | 0 |
| 12 | 2026-05-15 10:23 | 8650330965 | SL | -500 | 101,000 | 500 |
| 13 | 2026-05-15 10:45 | 8652091231 | SL | -500 | 100,500 | 1,000 |
| 14 | 2026-05-15 10:52 | 8652574043 | SL | -500 | 100,000 | 1,500 |
| 15 | 2026-05-15 11:44 | 8652728652 | TP | +1,000 | 101,000 | 500 |
| 16 | 2026-05-15 14:17 | 8655084624 | SL | -500 | 100,500 | 1,000 |
| 17 | 2026-05-15 17:10 | 8659678120 | SL | -500 | 100,000 | 1,500 |

## 5. Evaluacion tipo cuenta de fondeo

Supuestos:

- Cuenta: 100,000 USD
- Perdida diaria maxima: 5% = 5,000 USD
- Perdida total maxima: 10% = 10,000 USD
- Objetivo fase 1: 8% = 108,000 USD
- Objetivo fase 2: 5% = 105,000 USD

| Pregunta | Respuesta |
|---|---|
| MAGI habria perdido la cuenta? | No |
| Habria violado perdida diaria? | No |
| Habria violado perdida total? | No |
| Habria alcanzado fase 1? | No |
| Habria alcanzado fase 2? | No |
| Seguiria en proceso? | Si |
| Peor drawdown observado | 1,500 USD / 1.5% |
| Margen restante frente al limite diario | 3,500 USD sobre el peor dia normalizado |
| Margen restante frente al limite total | 8,500 USD frente al max drawdown, 9,500 USD frente al minimo bajo balance inicial |
| Maximo balance alcanzado | 101,500 USD |
| Balance actual normalizado | 100,000 USD |

MAGI no habria quemado una cuenta de evaluacion bajo estas reglas genericas, pero tampoco esta cerca de pasar una fase. El resultado actual indica supervivencia operativa, no aptitud de fondeo. La muestra es pequena y el viernes mostro una debilidad clara de control de frecuencia/riesgo operativo.

## 6. Diagnostico tecnico

### Que funciono bien

- Bot A siguio entregando snapshots live validos.
- Backend genero decisiones con `decision_id` y `snapshot_id`.
- Bot B ejecuto operaciones, respeto una posicion por simbolo y no se observaron duplicados.
- Bot C registro aperturas, cierres y modificaciones.
- El dashboard/backend continuaron reflejando datos reales.
- Las entradas OPEN fueron coherentes con la logica direccional H1/H4.
- Las modificaciones a BE pudieron ejecutarse mediante flujo MAGI/Bot B, no como cierre manual.

### Que fallo o preocupa

- El viernes produjo 7 OPEN organicos y 5 SL, una frecuencia demasiado alta para demo conservadora.
- No hay regla formal de apagado/reduccion por viernes, fin de semana o racha de perdidas.
- La gestion sigue siendo mayormente pasiva; BE fue operador-aprobado, no una politica automatica completa.
- Algunas entradas se dieron con RSI muy extendido, posible persecucion de movimiento.
- Dos entradas del viernes tuvieron spreads menos favorables: 0.6 y 1.0 pips.
- Bot C sigue mostrando la anomalia conocida de cierres sin `decision_id` cuando MT5 no conserva el comment en deals de cierre.
- `risk_percent_per_trade` y `daily_drawdown_percent` reales siguen siendo una prioridad pendiente para fondeo.
- `news_context` no permite todavia evaluar bloqueo por noticias de alto impacto.

### Problema principal actual

El problema principal no parece ser la direccion base H1/H4. Las entradas SELL del viernes estaban alineadas con el motor MVP. El cuello de botella parece estar en una combinacion de:

- Gestion activa insuficiente.
- Falta de regla de break-even formal.
- Falta de limite de reentradas/perdidas por dia.
- Falta de filtro operativo de viernes/tarde.
- Posible SL placement/timing en movimientos extendidos.
- Tamano de muestra todavia pequeno.

## 7. Recomendaciones

### No tocar todavia

- Reglas principales de entrada H1/H4.
- Umbrales base de direccion.
- Filtro EMA20/EMA50.
- Estructura de decision CEO/Melchor.
- Contratos Bot A -> backend -> Bot B.

La evidencia aun no justifica relajar o endurecer entradas. El viernes fue malo, pero tambien fue una muestra de gestion/frecuencia, no necesariamente una invalidacion de la logica direccional.

### Prioridad alta

| Prioridad | Recomendacion | Motivo |
|---|---|---|
| Alta | Formalizar break-even automatico | Ya se vio que BE protege capital y evita convertir trades favorables en perdedores. |
| Alta | Implementar limite de perdidas/reentradas por dia | El viernes mostro sobreoperacion despues de SL consecutivos. |
| Alta | Regla formal de viernes/fin de semana | Evitar operaciones tarde en New York y cierres riesgosos antes del weekend. |
| Alta | Corregir trazabilidad Bot C `ticket -> decision_id` | Necesario para auditoria seria y fondeo. |
| Alta | Usar drawdown real y risk percent real | Los placeholders no son aceptables para evaluar riesgo profesional. |
| Alta | Integrar news_context operativo | Sin noticias reales, no se puede auditar si un SL fue por evento externo. |

### Prioridad media

| Prioridad | Recomendacion | Motivo |
|---|---|---|
| Media | Dashboard de explicabilidad por decision | Ver causa principal de HOLD/OPEN sin abrir JSONL. |
| Media | MFE/MAE por trade en reporte automatico | Necesario para disenar BE/trailing sin adivinar. |
| Media | Analisis por sesion | London/overlap/New York tienen comportamiento distinto. |
| Media | Filtro de spread mas visible | Spread de 1.0 pip en Friday NY no encaja con demo conservadora. |
| Media | Detector de entradas extendidas | RSI extremadamente bajo puede ser setup valido o entrada tarde; requiere estudio. |

## 8. Lectura critica por categoria

| Categoria | Estado | Comentario |
|---|---|---|
| Entrada | Coherente, pero con timing discutible | La direccion fue correcta segun H1/H4, pero algunos SELL parecieron tardios. |
| Gestion | Debil | BE existe por accion aprobada, pero falta politica automatica completa. |
| SL placement | A estudiar | Varias operaciones tuvieron MFE antes de SL; puede requerir BE o SL mas contextual. |
| BE | Prometedor, no formalizado | Protegio una operacion el viernes y otra el jueves. |
| Sesion | Necesita control | Friday New York y cierre semanal requieren restricciones. |
| Noticias | Pendiente | Sin `news_context` real no se puede descartar impacto externo. |
| Ejecucion | Estable | Bot B no mostro duplicados graves y ejecuto payloads. |
| Trazabilidad | Buena con una anomalia conocida | Bot C registra, pero los cierres pueden perder `decision_id`. |
| Tamano de muestra | Insuficiente | 17 organicas no bastan para conclusiones estadisticas fuertes. |

## 9. Que debe pasar antes del 5 de junio

Antes de considerar una fase seria de fondeo o evaluacion, deberia ocurrir lo siguiente:

1. Correr mas dias live-demo sin tocar reglas de entrada.
2. Formalizar BE automatico con criterios objetivos.
3. Agregar limite diario de perdidas y maximo de reentradas por simbolo/sesion.
4. Implementar cierre/reduccion de viernes y riesgo de fin de semana.
5. Corregir trazabilidad Bot C para cierres sin `decision_id`.
6. Activar riesgo real: `risk_percent_per_trade` y `daily_drawdown_percent`.
7. Integrar noticias o al menos bloqueo manual/trazable de eventos de alto impacto.
8. Construir reporte automatico de MFE/MAE por operacion.
9. Validar que el comportamiento organico no depende de pruebas sinteticas.
10. Acumular muestra suficiente para estimar varianza real.

## 10. Veredicto final

MAGI sigue vivo, estable y prometedor en demo. Ya no es solo una arquitectura teorica: recibio mercado real, genero decisiones, abrio operaciones organicas, tuvo ganadoras, perdedoras, BE, modificaciones de proteccion y auditoria operativa.

Pero el viernes 15 fue una advertencia importante. El sistema no fallo por caerse ni por romper contratos; fallo en control operativo: demasiadas entradas en una misma direccion durante una jornada de viernes, con poca gestion activa y sin freno por secuencia de perdidas. Esa perdida normalizada de -1.5% no destruye una cuenta, pero revela una brecha que debe corregirse antes de cualquier fondeo.

Estado actual: demo operativa estable con riesgo controlado por supervision, no apta aun para fondeo.
Debe continuar en demo.
Sigue siendo prometedor.
No esta listo para dinero real ni challenge.
Antes del 5 de junio, la prioridad no es tocar entradas: es profesionalizar gestion, limites, viernes, noticias, riesgo real y trazabilidad.
