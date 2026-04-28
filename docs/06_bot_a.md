# 06. Bot A

## Rol

`Bot A` es un sensor periodico de `EURUSD`. Su responsabilidad es entregar un snapshot limpio y consistente cada 5 minutos.

## Salida minima del snapshot

### Identificacion

- `symbol`
- `timestamp`

### Estructura de mercado

- `market_structure`: `trend` | `range` | `breakout`
- `structure_direction`: `bullish` | `bearish` | `neutral`

### Niveles

- `support_levels`
- `resistance_levels`

### Indicadores

- `ema_20`
- `ema_50`
- `ema_200`
- `rsi_14`

### Momentum

- `momentum`: `bullish` | `bearish` | `weak`

### Precio y volatilidad

- `current_price`
- `recent_range`

### Estado de posicion

- `has_open_position`
- `position_type`
- `entry_price`
- `sl`
- `tp`
- `floating_pnl`

## Regla de oro

`Bot A` no emite opinion operativa. Solo publica contexto estructurado.

## Uso por el resto del sistema

- Los magos leen el mismo snapshot.
- El CEO usa ese contexto para parametrizar entrada, `SL` y `TP`.
- `Bot C` guarda el snapshot como insumo base del caso.

## Bloque operativo para Gaspar

Cuando Gaspar se integre a operacion real, `Bot A` principal debe incluir un bloque separado `gaspar_context`.

Reglas:

- `gaspar_context` debe seguir `docs/18_gaspar_operational_contract.md`.
- `gaspar_context` no debe incluir EMA, RSI, momentum, confianza, probabilidades ni features de Baltasar.
- `Bot A` no debe emitir opinion operativa ni calcular direccion si Baltasar o CEO-MAGI ya entregan `proposed_direction`.
- `Bot A` solo debe transportar `proposed_direction` (`BUY`, `SELL`, `NEUTRAL`) como hipotesis minima de direccion y agregar contexto estructural/temporal para que Gaspar evalúe calidad de oportunidad.
- Los indicadores generales del snapshot pueden existir para otros modulos, pero no deben copiarse dentro de `gaspar_context`.

## Adecuacion operativa vigente

La fuente compartida del contrato es `MagiBuildSnapshot(...)` en `servidor-prosperity/integrations/mt5/core/MagiFeatureEngine.mqh`.

`Bot A` real y `Bot_A_sub3` deben usar el mismo contrato:

- `Bot A` real construye el snapshot con `MagiBuildSnapshot(...)` y lo serializa con `MagiSerializeSnapshotJson(...)`.
- `Bot_A_sub3` construye el snapshot con la misma funcion y persiste el mismo JSON en JSONL.
- El CSV de `Bot_A_sub3` es solo una vista plana para analisis; no define un contrato distinto.

Campos agregados al snapshot compartido:

- `spread_pips`
- `active_session`
- `allowed_actions`
- `account.balance`
- `account.equity`
- `account.daily_drawdown_percent`
- `account.risk_percent_per_trade`
- `news`
- `operational_notes`
- `gaspar_context`
- `mtf_alignment_status`
- `mtf_alignment_warnings`
- `mtf_data_source_status`

Las features multi-timeframe se cargan como velas cerradas alineadas al `anchor_bar_timestamp`. En Bot A, `anchor_bar_timestamp` representa el cierre de la vela ancla cerrada. Cada item de `features` expone `bar_timestamp`, `age_minutes`, `selected_array_index`, `copied_array_size`, `rates_array_as_series`, `bars_available`, `oldest_bar_time`, `newest_bar_time`, `data_source_status`, `alignment_status` y `alignment_warning`.

`mtf_data_source_status` puede ser `OK`, `INSUFFICIENT_HISTORY` o `ALIGNMENT_ERROR`. Si MT5 Strategy Tester no entrega historico MTF suficiente, el snapshot debe fallar explicitamente con `INSUFFICIENT_HISTORY` y nunca arrastrar una vela vieja.

Campos pendientes o provisionales:

- `daily_drawdown_percent`: queda en `0.0` hasta tener calculo diario persistente.
- `risk_percent_per_trade`: queda en `0.0` hasta conectar politica de riesgo operativa.
- `news`: queda como arreglo vacio hasta conectar calendario/noticias.
- `gaspar_context.proposed_direction_source`: en Strategy Tester usa `fallback_h4_d1_shadow`; en produccion debe transportar la hipotesis primaria de Baltasar o CEO-MAGI cuando exista.

`Bot A` sigue sin decidir. La direccion proxy solo existe para shadow mode/backtesting y queda marcada como fuente fallback.

## Cierre de etapa Bot_A_sub3

La etapa vigente de `Bot_A_sub3` queda cerrada con una implementacion simple:

- conserva el flujo de dataset probado de `Bot_A_sub1`;
- usa `MagiBuildSnapshot(...)` como snapshot operativo compartido;
- integra `gaspar_context`, equivalente funcional al foco de `Bot_A_sub2`;
- guarda JSONL completo y CSV plano;
- genera `run_id` unico con fecha/hora y `GetTickCount()`;
- usa `FILE_COMMON`;
- no contiene logica de trading, senales ni ejecucion.

Auditoria validada:

- build: `bot_a_sub3_simple_sub1_sub2_2026-04-28_v1`;
- run: `run_2025-12-15_00-00-00_659700906`;
- score: `100/100`;
- decision: `APTO`;
- registros JSONL: `18,612`;
- registros CSV: `18,612`;
- duplicados `snapshot_id`: `0`;
- MTF OK: `74,448/74,448`;
- `gaspar_context` presente: `18,612/18,612`.

Pendiente: una corrida futura con `InpSkipInvalidSnapshots=false` para recolectar snapshots parciales/invalidos y medir robustez ante gaps de mercado o historial incompleto.
