# Informe Ejecutivo: Melchor v1

## 1. Resumen Ejecutivo

Melchor es el modulo de riesgo de MAGI. Su funcion dentro del sistema no es buscar oportunidades de mercado ni ejecutar operaciones, sino evaluar si una decision propuesta respeta las reglas de proteccion de capital. En terminos de gobierno, Melchor actua como voto especializado de riesgo: observa un snapshot normalizado, aplica reglas deterministicas y entrega una recomendacion auditable a CEO-MAGI.

El problema que resuelve es separar la generacion de senales de la evaluacion de riesgo. Antes, la logica de decision podia mezclarse con componentes sensores o flujos MVP. Con Melchor v1, Bot A permanece como sensor, CEO-MAGI conserva la autoridad final, y el riesgo queda representado por un modulo independiente, trazable y conservador.

En esta version se implemento un motor real de reglas, configuracion centralizada, persistencia de votos y pruebas automatizables. Melchor v1 evalua sesiones, riesgo por operacion, operaciones abiertas, RR, drawdown, noticias, spread, SL, datos criticos y breakeven.

El estado actual es funcional y listo para pruebas operativas controladas. La version es deterministica, no usa machine learning y ya esta integrada al flujo backend. Sus principales limitaciones dependen de la calidad y completitud de los datos recibidos desde Bot A y de la madurez futura del gobierno de decisiones de CEO-MAGI.

## 2. Arquitectura Del Modulo

Melchor vive en el backend Node.js de `servidor-prosperity`. Los archivos clave son:

- `config/melchor_rules.json`: reglas configurables de riesgo.
- `servidor-prosperity/services/melchor-risk-engine.js`: motor deterministico de evaluacion.
- `servidor-prosperity/src/server/services/voting/melchor-voting.service.js`: evaluacion y persistencia del voto.
- `servidor-prosperity/src/server/services/orchestrator/mvp-decision-engine.js`: integracion con CEO/MVP decision engine.
- `servidor-prosperity/src/server/services/connectors/adapters/melchor.js`: contrato del conector Melchor.
- `templates/melchor_decision_sample.json`: ejemplo de salida.
- `docs/07_melchor.md` y `docs/15_risk_rules.md`: documentacion funcional y normativa.

La integracion con Bot A es indirecta. Bot A sigue enviando snapshots a `POST /analisis`. El adapter legacy normaliza spread, sesion, drawdown, perdidas consecutivas, riesgo, noticias y progreso hacia TP. Bot A no decide y no contiene reglas de Melchor.

CEO-MAGI recibe la decision preliminar del motor MVP y consulta el voto de Melchor antes de entregar una decision final. Bot B no consume el voto crudo como orden; recibe la respuesta final mapeada desde la decision de CEO-MAGI mediante el contrato legacy de ejecucion.

El flujo completo es: Bot A envia snapshot, el backend valida y normaliza, el decision engine construye una decision candidata, Melchor evalua riesgo, el voto se persiste, CEO-MAGI decide la accion final y Bot B recibe esa decision por `GET /analisis/:symbol` o por `POST /analisis`.

## 3. Logica De Decision

Melchor v1 opera con reglas explicitas. No infiere patrones, no entrena modelos y no produce probabilidades aprendidas. Cada salida puede explicarse por reglas disparadas en `rules_triggered`.

Evalua sesiones Londres, Nueva York o solapamiento; riesgo por operacion sobre `0.1%`; operaciones abiertas; RR menor a `1.5`; RR bajo el preferente `2.0`; cinco perdidas consecutivas; drawdown diario de `0.7%` o `1.0%`; noticias de alto impacto USD, EUR o GBP en ventana de 30 minutos; spread mayor a `2.0` pips; SL fuera de `5` a `35` pips; y datos criticos faltantes.

Los outputs posibles son:

- `ALLOW`: no se detecta bloqueo de riesgo.
- `BLOCK`: recomienda no abrir.
- `PROTECT`: recomienda proteger una operacion abierta.
- `CLOSE`: recomienda cierre o proteccion por riesgo critico.
- `NOTIFY`: recomienda notificar sin bloquear por si mismo.

El campo `risk_block_recommendation` es la senal ejecutiva principal de bloqueo recomendado. Cuando es `true`, Melchor esta diciendo que, desde riesgo, la decision candidata no deberia avanzar. Sin embargo, esto no es una orden final ni un veto operativo absoluto.

## 4. Gobierno Y Control

El cambio de gobierno mas importante es que Melchor no tiene poder de veto absoluto. Melchor recomienda; CEO-MAGI gobierna.

CEO-MAGI usa `melchor_vote` como input de riesgo. Si Melchor recomienda bloqueo, CEO puede respetar esa recomendacion y convertir la accion final en `hold`, `protect`, `close_for_safety` o `move_to_breakeven`, segun el caso. Esto mantiene una politica conservadora por defecto.

Tambien existe un mecanismo de override. Si `risk_block_recommendation === true` y CEO-MAGI abre, la decision debe registrar:

```json
{
  "override_melchor": true,
  "override_reason": "justificacion operativa"
}
```

Esto evita decisiones silenciosas contra riesgo. La decision final permite auditar que Melchor recomendo bloqueo, que CEO-MAGI abrio y por que razon.

## 5. Persistencia Y Trazabilidad

Cada voto se guarda en `servidor-prosperity/data/votes/melchor/`. El nombre del archivo incluye timestamp, simbolo y `snapshot_id`, lo que facilita reconstruir la secuencia de evaluacion.

El voto incluye modulo, version, `vote`, `risk_block_recommendation`, confianza, nivel de riesgo, razon, reglas disparadas, accion recomendada, timestamp, simbolo y snapshot asociado. Esta estructura permite auditoria humana y procesamiento futuro.

En el futuro, Bot C podra consumir estos votos como evidencia operacional. Esto abre la puerta a analisis post-trade, deteccion de patrones de override, medicion de calidad de decisiones y entrenamiento futuro de modelos sin perder la base deterministica.

## 6. Testing Y Validacion

Se ejecutaron tres validaciones principales:

- `npm run check`: validacion sintactica del servidor.
- `npm run test:melchor`: pruebas de reglas y gobierno CEO/Melchor.
- `npm run smoke`: validacion basica de salud del backend, dashboard, modulos y conectores.

Los escenarios cubiertos incluyen ALLOW normal, BLOCK por RR menor a `1.5`, BLOCK por operacion abierta, NOTIFY por drawdown `>= 0.7%`, recomendacion de cierre/proteccion por drawdown `>= 1.0%`, bloqueo por noticia de alto impacto, move to breakeven al alcanzar 50% del TP, CEO respetando bloqueo, CEO ignorando bloqueo solo con justificacion y Bot B recibiendo la decision final de CEO.

El nivel de confianza actual es bueno para pruebas controladas de MVP. No equivale aun a validacion financiera completa, porque depende de datos externos y de mas escenarios reales.

## 7. Limitaciones Actuales

Melchor v1 no usa ML, no optimiza parametros automaticamente y no predice resultados de mercado. Tampoco valida noticias desde una fuente externa en tiempo real; evalua la informacion recibida en el snapshot. No calcula lotaje avanzado ni riesgo monetario completo si Bot A no provee los datos necesarios.

El riesgo principal es la calidad de datos. Si Bot A no envia sesion, spread, drawdown, noticias, SL/TP o progreso a TP con consistencia, Melchor puede recomendar bloqueo o evaluar con menor contexto.

Tambien falta una interfaz de auditoria para explorar votos historicos desde dashboard y una politica mas formal para aprobar overrides humanos o automaticos.

## 8. Siguientes Pasos Recomendados

Como mejoras inmediatas, se recomienda exponer un endpoint `GET /api/votes/melchor`, mostrar el ultimo voto en dashboard y agregar fixtures de snapshots reales para pruebas repetibles. Tambien conviene definir un contrato mas estricto para los campos de riesgo que Bot A debe enviar.

Para Melchor v2 se recomienda ampliar gestion monetaria, soportar calendarios de noticias con fuente externa, agregar severidad ponderada por regla y registrar metricas de acierto por recomendacion.

La integracion con Bot C deberia convertir los votos en memoria operativa: comparar recomendacion versus resultado, medir overrides, identificar reglas demasiado estrictas o demasiado permisivas y preparar datasets auditables. ML puede entrar mas adelante como apoyo analitico, pero no deberia reemplazar las reglas duras de control de riesgo.
