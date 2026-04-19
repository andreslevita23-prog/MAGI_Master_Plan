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
