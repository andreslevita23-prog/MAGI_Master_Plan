# Auditoria tecnica de Bot B para integracion demo MAGI

## Dictamen final

**REQUIERE CAMBIOS IMPORTANTES**

Bot B puede consultar `GET /analisis/:symbol` y ejecutar una respuesta simple `open` con el contrato actual del backend. Sin embargo, no esta listo para demo segura porque no soporta varias acciones que el backend/MAGI ya puede emitir (`close_for_safety`, `protect`, `move_to_breakeven`), no evita aperturas duplicadas en la variante mas nueva, no valida antiguedad de la respuesta y usa parsing JSON manual fragil.

No se encontro un archivo llamado exactamente `Bot_B.mq5`. Se auditaron las variantes disponibles:

- `integrations/mt5/botB_v2.2.mq5`
- `integrations/mt5/botB_v3.0.mq5` (cabecera interna: `BotB_v3.1`)
- `src/server/services/adapters/mt5/bot-b-response-mapper.js`
- `src/server/index.js`
- `src/server/domain/contracts/execution-response.js`

## 1. Que hace Bot B actualmente

### Variante principal auditada: `botB_v3.0.mq5`

| Area | Comportamiento actual |
|---|---|
| Backend consultado | `ServerURL = "https://prosperity.lat/analisis"` |
| Endpoint usado | `GET {ServerURL}/{symbol}`, por ejemplo `/analisis/EURUSD` |
| Frecuencia | Timer cada `RefreshSeconds`, default `30` segundos |
| Simbolos | `SymbolsToTrade = "EURUSD,XAUUSD"` por default |
| Formato esperado | JSON con `action`, `id_operacion`, `details.symbol`, `details.order_type`, `details.entry_price`, `details.stop_loss`, `details.take_profit`, `details.lot_size`, `details.comment` |
| Acciones reconocidas | `hold`, `open`, `close`, `modify`; tambien convierte `move_sl` a `modify` |
| Lotaje | Lee `details.lot_size` y lo usa solo para `open` |
| SL/TP | Lee `details.stop_loss` y `details.take_profit`; exige ambos para cualquier accion no `hold` |
| Precio de entrada | Lee `details.entry_price`, pero para abrir usa ASK/ BID actual, no el entry recibido |
| Comment | Usa `details.comment` como comentario de orden |
| Magic number | No se configura magic number (`trade.SetExpertMagicNumber` no aparece) |
| Simbolo | Itera `SymbolsToTrade`, consulta por simbolo y valida `details.symbol` si viene informado |
| Errores HTTP | Solo valida `WebRequest == -1`; no valida codigos HTTP no-200 porque en MQL5 `WebRequest` devuelve status code positivo |
| Dedupe | Guarda `last_actions[i] = id_operacion` solo despues de ejecucion exitosa |

### Variante `botB_v2.2.mq5`

La v2.2 es mas simple. Consulta el mismo endpoint cada 30 segundos y soporta `hold`, `open`, `close`, `modify`. Tiene una proteccion mejor para una sola posicion por simbolo antes de `open`, pero ignora `details.lot_size` y usa siempre `0.01`. Aunque declara `last_actions`, no lo usa para deduplicar ejecuciones.

## 2. Que NO hace

| Limitacion | Evidencia tecnica | Riesgo |
|---|---|---|
| No soporta `close_for_safety` | Solo compara `action == "close"` | Si Melchor/CEO pide cierre de seguridad, Bot B no ejecuta nada. |
| No soporta `protect` | No hay rama para `protect` | Si MAGI pide proteccion, queda ignorada. |
| No soporta `move_to_breakeven` | Solo convierte `move_sl` a `modify` | Breakeven de Melchor no se traduce a modificacion. |
| No evita apertura si ya hay posicion en v3.0 | En `open` no llama `PositionSelect(symbol)` antes de comprar/vender | Puede duplicar operaciones por simbolo. |
| No valida respuesta vieja | No evalua `timestamp` ni TTL | Puede ejecutar una decision persistida antigua despues de reiniciar MT5. |
| Dedupe no persiste entre reinicios | `last_actions` vive solo en memoria | Tras reinicio, puede reejecutar una orden vieja si sigue publicada. |
| `hold` no actualiza `last_actions` | El dedupe no registra holds | No es grave para hold, pero no marca decision procesada. |
| Parsing JSON manual | `ExtractValue` / `ExtractNestedValue` buscan strings con `StringFind` | Fragil ante espacios, escapes, objetos anidados o cambios de orden/formato. |
| No valida HTTP 404/500 en v3.0 | `GetServerResponse` solo falla con `res == -1` | Puede intentar parsear errores JSON del backend como si fueran decisiones. |
| No respeta `allowed_actions` | El contrato Bot B no lo recibe ni Bot B lo valida | Depende totalmente del backend para seguridad. |
| No configura deviation/filling/magic | No hay configuracion explicita de ejecucion | Dificulta trazabilidad y control de ordenes propias. |

## 3. Compatibilidad backend actual vs Bot B

### Contrato que devuelve `GET /analisis/:symbol`

El endpoint lee `data/analysis/{SYMBOL}.json`; si no existe, devuelve:

```json
{
  "action": "hold",
  "id_operacion": "EURUSD_missing",
  "details": {
    "symbol": "EURUSD",
    "order_type": "",
    "entry_price": 0,
    "stop_loss": 0,
    "take_profit": 0,
    "lot_size": 0,
    "comment": "No existe analisis persistido para este simbolo."
  }
}
```

El mapper backend genera:

```json
{
  "action": "open|hold|...",
  "id_operacion": "snapshot_id o id_operacion",
  "details": {
    "symbol": "EURUSD",
    "order_type": "buy|sell|",
    "entry_price": 1.12,
    "stop_loss": 1.115,
    "take_profit": 1.13,
    "lot_size": 0.01,
    "comment": "..."
  },
  "timestamp": "..."
}
```

### Tabla de compatibilidad

| Campo backend | Bot B v3.0 espera | Compatible | Observacion |
|---|---|---:|---|
| `action` | top-level string | Si | Pero solo ejecuta `open`, `close`, `modify`; `hold` se ignora correctamente. |
| `id_operacion` | top-level string | Si | Se usa para dedupe en memoria. |
| `details.symbol` | string | Si | Si difiere del simbolo iterado, Bot B omite. |
| `details.order_type` | `buy`/`sell` para `open` | Si | Backend usa `decision.direction`, actualmente `buy`/`sell` para MVP open. |
| `details.entry_price` | numero/string convertible | Si | Bot B lo valida pero abre a precio de mercado ASK/BID. |
| `details.stop_loss` | numero/string convertible | Si | Obligatorio incluso para `close`, lo cual puede bloquear cierres si llega en 0. |
| `details.take_profit` | numero/string convertible | Si | Obligatorio incluso para `close`, lo cual puede bloquear cierres si llega en 0. |
| `details.lot_size` | numero/string convertible | Si | v3.0 lo usa; v2.2 lo ignora y usa 0.01 fijo. |
| `details.comment` | string | Si | Usado como comment de orden. |
| `timestamp` | No usado | Parcial | Bot B no valida frescura. |

## 4. Seguridad operativa

| Control | Estado |
|---|---|
| Evita duplicar operaciones | Parcial. v3.0 deduplica por `id_operacion` solo en memoria y solo tras ejecucion exitosa. v2.2 no deduplica aunque declara `last_actions`. |
| Respeta una sola posicion por simbolo | No en v3.0 para `open`. Si en v2.2. |
| Maneja errores HTTP | Parcial. v2.2 exige `res == 200`; v3.0 solo detecta `res == -1`. |
| Evita ordenes incompletas | Parcial. v3.0 valida entry/sl/tp/lot/order_type para open. Pero exige entry/sl/tp tambien para close/modify, y no valida distancias minimas, stops level ni freeze level. |
| Proteccion contra respuestas viejas | No. No valida `timestamp`, TTL ni estado persistido. |
| Respeta `allowed_actions` | No. Ese campo no forma parte de la respuesta Bot B actual. |
| Puede modificar SL/TP | Si para `modify` y alias `move_sl`. No para `move_to_breakeven`. |
| Puede cerrar posiciones | Si solo con action exacta `close`. No con `close_for_safety`. |
| Magic number | No. No hay filtro para distinguir posiciones de este EA. |

## 5. Hallazgos principales

1. **Acciones MAGI no mapeadas**: el backend puede emitir `close_for_safety`, `protect` y `move_to_breakeven`, pero Bot B v3.0 no las ejecuta.
2. **Riesgo de duplicar operaciones**: Bot B v3.0 no verifica `PositionSelect(symbol)` antes de abrir.
3. **Riesgo de reejecucion tras reinicio**: dedupe por `last_actions` no persiste y no hay TTL por `timestamp`.
4. **HTTP handling incompleto en v3.0**: una respuesta 404/500 puede llegar al parser como texto JSON no operativo.
5. **Contrato actual es compatible solo para caso feliz `open`/`hold`**: con una respuesta `open` bien formada, Bot B v3.0 puede abrir; con acciones de gestion de riesgo no esta alineado.

## 6. Cambios recomendados

| Prioridad | Cambio | Motivo |
|---|---|---|
| Alta | Mapear `close_for_safety` -> `close` | Cierre de emergencia debe ejecutarse. |
| Alta | Mapear `move_to_breakeven` y `protect` -> `modify` con SL/TP validos | Gestion de riesgo de Melchor/CEO no debe quedar ignorada. |
| Alta | Antes de `open`, bloquear si `PositionSelect(symbol)` es true | Evitar duplicacion por simbolo. |
| Alta | Validar HTTP `res == 200` en v3.0 | No parsear errores como decisiones. |
| Alta | Validar frescura con `timestamp` y TTL configurable | Evitar ejecutar respuestas antiguas. |
| Media | Persistir ultimo `id_operacion` por simbolo en GlobalVariables o archivo | Evitar reejecucion tras reinicio. |
| Media | Configurar magic number y filtrar posiciones por magic/simbolo | Trazabilidad y control de posiciones propias. |
| Media | Usar lotaje del backend en v2.2 o retirar v2.2 como candidato demo | Evitar diferencias entre variantes. |
| Media | No exigir entry/sl/tp para `close` | Cierre no deberia depender de precios de apertura. |
| Baja | Reemplazar parsing manual por parser JSON robusto o formato plano controlado | Reducir fragilidad del contrato. |

## 7. Plan minimo para dejar Bot B listo para demo

1. Tomar `botB_v3.0.mq5` como base unica de demo.
2. Agregar control `PositionSelect(symbol)` antes de cualquier `open`.
3. Agregar alias de acciones:
   - `close_for_safety` -> `close`
   - `move_to_breakeven` -> `modify`
   - `protect` -> `modify`
4. Validar `WebRequest` con status `200`.
5. Validar `timestamp` maximo, por ejemplo 60-120 segundos configurable.
6. Persistir `last_actions` por simbolo para sobrevivir reinicios.
7. Definir `MagicNumber` input y usar `trade.SetExpertMagicNumber`.
8. Probar con respuestas mock:
   - `hold`
   - `open buy`
   - `open sell`
   - `close_for_safety`
   - `move_to_breakeven`
   - respuesta vieja
   - respuesta incompleta

## 8. Conclusion

Bot B **no esta bloqueado**, porque el contrato principal de `GET /analisis/:symbol` coincide con lo que espera para `open` y `hold`. Pero para una demo MAGI segura necesita ajustes antes de habilitar ejecucion real. El estado correcto es:

**REQUIERE CAMBIOS IMPORTANTES**
