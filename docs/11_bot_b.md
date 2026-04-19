# 11. Bot B

## Rol

Ejecutar la instruccion final emitida por `CEO-MAGI` con precision y sin reinterpretacion analitica.

## Responsabilidades del MVP

- Abrir operacion si `action = open_trade`.
- Ajustar `SL` si `action = move_sl`.
- Mover a break-even si `action = break_even`.
- Cerrar posicion si `action = close`.
- No ejecutar nada si `action = no_trade` o `maintain`.

## Requisitos

- Respetar el contrato de salida del CEO.
- Confirmar resultado de ejecucion para `Bot C`.
- No improvisar parametros.
