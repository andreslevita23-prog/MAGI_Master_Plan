# 12. Bot C

## Rol

Registrar cada caso MAGI con suficiente detalle para reconstruccion, auditoria y dataset futuro.

## Objeto de registro por caso

- `case_id`
- `case_type`
- `timestamp_inicio`
- `snapshot_bot_a`
- `melchor_output`
- `baltasar_output`
- `gaspar_output`
- `trigger_source`
- `ceo_output`
- datos de ejecucion
- outcome posterior

## Outcome esperado por tipo

### Entry case ejecutado

- `result`: `win` | `loss` | `break_even`
- `r_multiple`
- `max_favorable_excursion`
- `max_adverse_excursion`
- `duration`
- `close_reason`

### Entry case no ejecutado

- `hypothetical_outcome` opcional
- `post_market_direction`

### Management case

- `action_effect`
- `post_action_impact`
- `final_position_state`

## Encadenamiento

Una operacion debe poder reconstruirse como:

`entry_case -> execution -> management_case(s) -> close -> final outcome`

## Uso futuro para ML

`Bot C` es la fuente primaria para datasets etiquetables, comparacion de decisiones, validacion offline y entrenamiento futuro de los magos.
