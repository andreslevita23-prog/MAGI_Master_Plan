# Connectors

## Objetivo

Esta capa define contratos y mocks para las futuras integraciones de MAGI sin activar trading real ni acoplar todavia servicios externos.

## Ubicacion

```text
src/server/services/connectors/
  adapters/
  registry.js
  shared.js
```

## Connectors disponibles

- `bot-a`: entrada de contexto y datos de mercado
- `bot-b`: salida de decisiones operativas
- `bot-c`: confirmacion complementaria
- `melchor`: seguridad y riesgo
- `baltasar`: analisis tecnico y datos
- `gaspar`: exploracion y oportunidad
- `ceo-magi`: arbitraje y decision final

## Contrato comun

Cada connector declara:

- `id`, `name`, `family`, `role`, `description`
- `inputContract`
- `outputContract`
- `connection`
- `mock`

## Endpoints

- `GET /api/connectors`
- `GET /api/connectors/:id`
- `POST /analisis`: acepta `snapshot_legacy_mt5` y `magi.snapshot.v2`
- `GET /analisis/:symbol`: mantiene respuesta compatible con Bot B

## Bot A: legacy vs magi.snapshot.v2

El contrato legacy usa nombres historicos de MT5:

- `pair`
- `price`
- `context`
- `allowed_actions`
- `id_operacion`

El contrato `magi.snapshot.v2` usa el snapshot tecnico actual:

- `symbol`
- `current_price`
- `timestamp`
- `anchor_bar_timestamp`
- `bar_timestamp`
- `anchor_timeframe`
- `primary_timeframe`
- `anchor_open`, `anchor_high`, `anchor_low`, `anchor_close`
- `market_structure`, `structure_direction`
- `support_levels`, `resistance_levels`
- `ema_20`, `ema_50`, `ema_200`, `rsi_14`, `momentum`, `recent_range`
- `spread_pips`, `active_session`
- `mtf_alignment_status`, `mtf_alignment_warnings`, `mtf_data_source_status`
- `allowed_actions`
- `account`
- `position`
- `gaspar_context`
- `features`
- `validation`
- `news`
- `operational_notes`

Campos criticos de v2: `symbol`, `current_price` y `timestamp`. El backend rechaza v2 si alguno falta o no es usable.

Campos pendientes de calidad operativa:

- `daily_drawdown_percent` real
- `risk_percent_per_trade` real
- `news_context`
- detalle individual para multiples posiciones abiertas

## Siguiente integracion real sugerida

1. Conectar `Bot A` a un webhook o puente MT5.
2. Conectar `Melchor` a una politica real de riesgo.
3. Conectar `CEO-MAGI` a una orquestacion que combine salidas de Melchor, Baltasar y Gaspar.
