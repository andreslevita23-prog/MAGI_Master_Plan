# Reporte: ajuste seguro de Bot B para demo MAGI

## Dictamen final

**LISTO PARA PRUEBA LOCAL**

Bot B fue ajustado para operar de forma conservadora con el contrato actual de `GET /analisis/:symbol`. La ejecucion real debe validarse en MetaTrader antes de conectar una cuenta demo, porque desde este entorno no se puede compilar ni ejecutar el EA.

## Archivos modificados

- `integrations/mt5/botB_v3.0.mq5`

No se modifico el backend ni Bot A. La variante ajustada es `botB_v3.0.mq5`; `botB_v2.2.mq5` queda sin cambios.

## Acciones soportadas

| Accion recibida | Comportamiento |
|---|---|
| `hold` | No ejecuta nada. |
| `do_nothing` | Se normaliza a `hold`. |
| `open` | Abre `buy` o `sell` si el payload esta completo y no hay posicion existente. |
| `close` | Cierra posicion gestionable existente. |
| `close_for_safety` | Se normaliza a `close`. |
| `modify` | Modifica SL/TP con valores del payload; conserva SL/TP actual si uno falta. |
| `protect` | Se trata como modificacion defensiva de SL/TP. |
| `move_sl` | Se normaliza a `modify`. |
| `move_to_breakeven` | Mueve SL al precio de entrada de la posicion abierta y conserva TP actual si no viene uno nuevo. |
| accion desconocida | Hold seguro; no ejecuta. |

## Reglas de seguridad agregadas

- `MagicNumber` configurable y aplicado con `trade.SetExpertMagicNumber`.
- `OnePositionPerSymbol=true` por defecto: bloquea cualquier `open` si ya existe una posicion para el simbolo.
- Log explicito para duplicados: `open bloqueado: ya existe posicion`.
- Validacion de HTTP: solo procesa respuestas con status `200`.
- Validacion de JSON minimo: la respuesta debe parecer objeto JSON, tener `action` y `details.symbol`.
- Validacion de simbolo: `details.symbol` debe coincidir con el simbolo consultado.
- Validacion de frescura: acciones distintas de `hold` requieren `timestamp` o `decision_time` usable y no mayor a `MaxDecisionAgeSeconds` (default `120`).
- Dedupe por decision:
  - prioridad: `decision_id`
  - luego: `snapshot_id`
  - luego: `id_operacion`
  - fallback: `symbol|action|decision_time`
- Dedupe persistente por simbolo/magic en archivo local MT5:
  - `MAGI_BotB_last_{SYMBOL}_{MagicNumber}.txt`
- `open` exige:
  - `order_type` igual a `buy` o `sell`
  - `stop_loss`, `take_profit` y `lot_size` numericos y positivos
  - si `allowed_actions` existe, debe contener `open`
  - si aparecen flags de invalidez (`risk_valid:false`, `data_valid:false`, `is_valid:false`, `risk_status:"invalid"`), bloquea apertura
- `close` no exige SL/TP.
- `modify`/`protect` requieren posicion gestionable y al menos algun SL/TP valido o ya existente.
- `move_to_breakeven` requiere posicion gestionable y precio de entrada valido.

## Compatibilidad con backend actual

El backend actual sigue devolviendo:

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

Bot B mantiene compatibilidad con `open` y `hold`. Si el backend agrega `decision_id`, `snapshot_id`, `decision_time`, `allowed_actions` o flags de riesgo/validacion, Bot B los usara; si no vienen, conserva el comportamiento seguro con `id_operacion` y `timestamp`.

## Checklist de prueba demo

Antes de operar:

- Compilar `integrations/mt5/botB_v3.0.mq5` en MetaEditor.
- Configurar WebRequest para permitir `https://prosperity.lat`.
- Probar primero en Strategy Tester o cuenta demo.
- Confirmar inputs:
  - `ServerURL=https://prosperity.lat/analisis`
  - `MagicNumber=30001` o el magic acordado
  - `MaxDecisionAgeSeconds=120`
  - `OnePositionPerSymbol=true`

Casos funcionales:

- `hold`: no debe abrir, cerrar ni modificar.
- `open` valido: debe abrir una sola operacion con lotaje, SL, TP y comentario recibidos.
- `open` duplicado con posicion existente: debe imprimir `open bloqueado: ya existe posicion` y no abrir.
- decision repetida con mismo `id_operacion`: debe ignorarse despues de ejecutarse una vez.
- reiniciar MT5 y repetir la misma decision: debe ignorarse por archivo dedupe.
- `close_for_safety`: debe cerrar la posicion existente.
- `move_to_breakeven`: debe modificar SL al precio de entrada.
- `protect`/`modify`: debe modificar SL/TP segun payload.
- respuesta vieja: debe ignorarse por `MaxDecisionAgeSeconds`.
- respuesta HTTP no 200: debe ignorarse.
- JSON invalido o sin `action`: debe ignorarse.
- `allowed_actions` presente sin `open`: debe bloquear apertura.

## Riesgos pendientes

- El parser JSON sigue siendo manual. Se reforzo para el contrato actual, pero no equivale a un parser JSON completo.
- El backend actual no siempre envia `decision_id` o `snapshot_id`; el dedupe usa `id_operacion` y `timestamp` como fallback.
- `allowed_actions`, `risk_valid` y flags similares no forman parte obligatoria del contrato Bot B actual; Bot B solo los aplica si aparecen.
- No se validan `SYMBOL_TRADE_STOPS_LEVEL`, `SYMBOL_TRADE_FREEZE_LEVEL`, filling mode ni desviacion maxima.
- En cuentas hedge con multiples posiciones por simbolo, `PositionSelect(symbol)` puede no cubrir todos los casos. Para demo se prioriza `OnePositionPerSymbol=true`.
- No se pudo compilar el EA desde este entorno; la validacion final debe hacerse en MetaEditor.

## Resultado

El Bot B ajustado queda **LISTO PARA PRUEBA LOCAL** con prioridad de seguridad sobre ejecucion.
