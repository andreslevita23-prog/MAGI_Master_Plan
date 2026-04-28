# 18. Gaspar Operational Contract

## Objetivo

Este contrato define el bloque exacto que `Bot A` principal debe enviar a Gaspar en operacion real bajo el nombre `gaspar_context`.

Gaspar evalua calidad de oportunidad. No predice direccion. Solo evalua si una hipotesis minima de direccion tiene suficiente calidad estructural y temporal para ejecutarse.

## Decision sobre `proposed_direction`

`Bot A` principal no debe calcular `proposed_direction` como opinion propia si Baltasar o CEO-MAGI ya entregan la hipotesis de direccion.

Regla operativa:

- Fuente primaria: Baltasar o CEO-MAGI.
- Valor permitido: `BUY`, `SELL`, `NEUTRAL`.
- Bot A solo debe transportar ese valor dentro de `gaspar_context`.
- Fallback permitido solo para shadow mode o backtesting sin Baltasar: proxy estructural H4/D1 usado por Bot_A_sub2.
- Si se usa fallback, debe quedar registrado fuera de Gaspar como metadata operativa, no como feature del modelo.

Proxy fallback permitido:

- D1 bullish y H4 no bearish => `BUY`.
- D1 bearish y H4 no bullish => `SELL`.
- D1 range o conflicto fuerte H4/D1 => `NEUTRAL`.

## JSON operativo completo

```json
{
  "gaspar_context": {
    "schema_version": "1.0",
    "module": "GASPAR",
    "role": "opportunity_quality",
    "symbol": "EURUSD",
    "timestamp": "2026-04-27T12:00:00Z",
    "anchor_timeframe": "M5",
    "structure_timeframes": {
      "h4": "H4",
      "d1": "D1"
    },
    "proposed_direction": "BUY",
    "higher_timeframe_confluence": {
      "h4_structure": "bullish",
      "d1_structure": "bullish",
      "directional_alignment": "aligned"
    },
    "price_structure_position": {
      "distance_to_d1_support": 0.0012,
      "distance_to_d1_resistance": 0.0048,
      "position_in_d1_range": 0.25,
      "near_key_level": true
    },
    "timing_quality": {
      "active_session": "london",
      "daily_atr_consumed_pct": 0.42,
      "available_range_to_next_level": 0.0036,
      "h4_candle_pattern": "rejection"
    },
    "day_context": {
      "day_of_week": "tuesday",
      "d1_volatility_vs_20d_avg": 1.05,
      "current_d1_range_vs_atr": 0.58
    }
  }
}
```

## Campos requeridos

| Campo | Tipo | Valores validos | Rango / regla | Uso |
| --- | --- | --- | --- | --- |
| `gaspar_context.schema_version` | string | `1.0` | requerido | Control de contrato. |
| `gaspar_context.module` | string | `GASPAR` | requerido | Identificacion del modulo. |
| `gaspar_context.role` | string | `opportunity_quality` | requerido | Identificacion de rol. |
| `gaspar_context.symbol` | string | simbolo MT5 | no vacio | Identifica instrumento. |
| `gaspar_context.timestamp` | string ISO-8601 | UTC recomendado | no futuro; parseable | Orden temporal y trazabilidad. |
| `gaspar_context.proposed_direction` | enum string | `BUY`, `SELL`, `NEUTRAL` | requerido | Hipotesis minima de direccion. No es prediccion de Gaspar. |
| `higher_timeframe_confluence.h4_structure` | enum string | `bullish`, `bearish`, `range` | requerido | Estructura H4. |
| `higher_timeframe_confluence.d1_structure` | enum string | `bullish`, `bearish`, `range` | requerido | Estructura D1. |
| `higher_timeframe_confluence.directional_alignment` | enum string | `aligned`, `contradictory`, `neutral` | requerido | Alineacion entre estructura y `proposed_direction`. |
| `price_structure_position.distance_to_d1_support` | number | float >= 0 | precio o puntos normalizados por simbolo | Distancia al soporte D1 relevante. |
| `price_structure_position.distance_to_d1_resistance` | number | float >= 0 | precio o puntos normalizados por simbolo | Distancia a resistencia D1 relevante. |
| `price_structure_position.position_in_d1_range` | number | float | 0..1 | 0 cerca de soporte, 1 cerca de resistencia. |
| `price_structure_position.near_key_level` | boolean | `true`, `false` | requerido | Cercania a nivel clave. |
| `timing_quality.active_session` | enum string | `asia`, `london`, `new_york`, `overlap`, `inactive` | requerido | Contexto de sesion. |
| `timing_quality.daily_atr_consumed_pct` | number | float | 0..1 | Porcentaje del ATR diario ya consumido. |
| `timing_quality.available_range_to_next_level` | number | float >= 0 | precio o puntos normalizados por simbolo | Espacio hasta el proximo nivel relevante en la direccion propuesta. |
| `timing_quality.h4_candle_pattern` | enum string | `rejection`, `engulfing`, `inside`, `none` | requerido | Patron H4 estructural. |
| `day_context.day_of_week` | enum string | `monday`, `tuesday`, `wednesday`, `thursday`, `friday` | requerido | Contexto de calendario operativo. |
| `day_context.d1_volatility_vs_20d_avg` | number | float > 0 | recomendado 0..5; hard reject si <= 0 | Volatilidad D1 contra promedio 20 dias. |
| `day_context.current_d1_range_vs_atr` | number | float >= 0 | recomendado 0..5; hard reject si < 0 | Rango D1 actual contra ATR. |

## Campos opcionales

| Campo | Tipo | Valores validos | Uso |
| --- | --- | --- | --- |
| `gaspar_context.anchor_timeframe` | string | `M1`, `M5`, `M15`, etc. | Trazabilidad del snapshot de entrada. |
| `gaspar_context.structure_timeframes.h4` | string | `H4` | Explicita timeframe estructural usado. |
| `gaspar_context.structure_timeframes.d1` | string | `D1` | Explicita timeframe estructural usado. |
| `gaspar_context.context_id` | string | UUID o id interno | Correlacion con Bot C, logs y CEO-MAGI. |
| `gaspar_context.source_timestamp` | string ISO-8601 | timestamp de captura raw | Auditoria si difiere de `timestamp`. |
| `gaspar_context.data_quality_flags` | array[string] | flags no modelados | Solo diagnostico; no debe entrar al modelo como feature. |

Campos opcionales recomendados para version futura:

- `context_id`
- `source_timestamp`
- `data_quality_flags`
- `symbol_point`
- `digits`

Estos campos ayudan a trazabilidad y normalizacion, pero no son indispensables para que Gaspar ejecute inferencia.

## Mapeo desde Bot_A_sub2 hacia Bot A principal

| Bot_A_sub2 / dataset | `gaspar_context` en Bot A principal | Estado |
| --- | --- | --- |
| `module` | `gaspar_context.module` | Requerido. |
| `role` | `gaspar_context.role` | Requerido. |
| `symbol` | `gaspar_context.symbol` | Requerido. |
| `timestamp` | `gaspar_context.timestamp` | Requerido. |
| `anchor` o timeframe de captura | `gaspar_context.anchor_timeframe` | Opcional recomendado. |
| `proposed_direction` | `gaspar_context.proposed_direction` | Requerido; fuente primaria Baltasar/CEO. |
| `h4_structure` | `higher_timeframe_confluence.h4_structure` | Requerido. |
| `d1_structure` | `higher_timeframe_confluence.d1_structure` | Requerido. |
| `directional_alignment` | `higher_timeframe_confluence.directional_alignment` | Requerido. |
| `distance_to_d1_support` | `price_structure_position.distance_to_d1_support` | Requerido. |
| `distance_to_d1_resistance` | `price_structure_position.distance_to_d1_resistance` | Requerido. |
| `position_in_d1_range` | `price_structure_position.position_in_d1_range` | Requerido. |
| `near_key_level` | `price_structure_position.near_key_level` | Requerido. |
| `active_session` | `timing_quality.active_session` | Requerido. |
| `daily_atr_consumed_pct` | `timing_quality.daily_atr_consumed_pct` | Requerido. |
| `available_range_to_next_level` | `timing_quality.available_range_to_next_level` | Requerido. |
| `h4_candle_pattern` | `timing_quality.h4_candle_pattern` | Requerido. |
| `day_of_week` | `day_context.day_of_week` | Requerido. |
| `d1_volatility_vs_20d_avg` | `day_context.d1_volatility_vs_20d_avg` | Requerido. |
| `current_d1_range_vs_atr` | `day_context.current_d1_range_vs_atr` | Requerido. |
| `daily_range_state` | derivado por pipeline/modelo v4 | No exportar como requerido. |
| `target.voto`, `target.score_oportunidad` | no enviar en operacion | Solo entrenamiento. |

## Campos que no deben incluirse en `gaspar_context`

Gaspar no debe recibir:

- `ema_20`, `ema_50`, `ema_200` ni cualquier EMA.
- `rsi_14` ni cualquier RSI.
- `momentum`.
- `iMA`, `iRSI` o nombres de indicadores MQL.
- `baltasar_confidence`.
- `baltasar_probability`.
- `baltasar_score`.
- probabilidades por clase de Baltasar.
- features internas de Baltasar.
- senales direccionales tecnicas calculadas para Baltasar.
- decision final de CEO-MAGI.
- datos de riesgo de Melchor como tamano de posicion, margen, exposicion o veto.
- `target.voto` o `target.score_oportunidad` en modo operacion.

Es valido que el snapshot global de Bot A tenga indicadores para otros modulos. La restriccion aplica al bloque `gaspar_context`.

## Validaciones previas en Bot A

Bot A debe validar antes de enviar a Gaspar:

1. `gaspar_context` existe y es un objeto separado del snapshot global.
2. No contiene campos prohibidos por nombre.
3. `proposed_direction` pertenece a `BUY`, `SELL`, `NEUTRAL`.
4. `h4_structure` y `d1_structure` pertenecen a `bullish`, `bearish`, `range`.
5. `directional_alignment` pertenece a `aligned`, `contradictory`, `neutral`.
6. `position_in_d1_range` esta en 0..1.
7. `daily_atr_consumed_pct` esta en 0..1.
8. `available_range_to_next_level` es >= 0.
9. `distance_to_d1_support` y `distance_to_d1_resistance` son >= 0.
10. `d1_volatility_vs_20d_avg` es > 0.
11. `current_d1_range_vs_atr` es >= 0.
12. `timestamp` es parseable y consistente con el ciclo operativo.
13. Si `proposed_direction` es `BUY`, `available_range_to_next_level` debe referirse al proximo nivel superior relevante.
14. Si `proposed_direction` es `SELL`, `available_range_to_next_level` debe referirse al proximo nivel inferior relevante.
15. Si `proposed_direction` es `NEUTRAL`, `available_range_to_next_level` puede calcularse como el menor espacio hacia soporte/resistencia o enviarse como 0 si no aplica.

## Indispensable vs futuro

Indispensable para inferencia actual:

- `symbol`
- `timestamp`
- `proposed_direction`
- `h4_structure`
- `d1_structure`
- `directional_alignment`
- `distance_to_d1_support`
- `distance_to_d1_resistance`
- `position_in_d1_range`
- `near_key_level`
- `active_session`
- `daily_atr_consumed_pct`
- `available_range_to_next_level`
- `h4_candle_pattern`
- `day_of_week`
- `d1_volatility_vs_20d_avg`
- `current_d1_range_vs_atr`

Puede quedar para version futura:

- `context_id`
- `source_timestamp`
- `data_quality_flags`
- `symbol_point`
- `digits`
- explicacion textual de niveles
- metadata de sesion extendida
- calidad de spread o liquidez, siempre que no mezcle indicadores de Baltasar.

## Regla final

`gaspar_context` debe ser autosuficiente para Gaspar y aislado de Baltasar. Puede contener una hipotesis minima de direccion, pero no puede contener la evidencia direccional, confianza, probabilidades ni indicadores usados para producir esa hipotesis.
