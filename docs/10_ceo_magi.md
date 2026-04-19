# 10. CEO-MAGI

## Rol

`CEO-MAGI` es la capa de arbitraje y decision final. Consume el contexto de `Bot A` y los tres votos obligatorios del caso.

## Contrato de salida unificado

- `case_type`: `entry_case` | `management_case`
- `action`
  - `entry_case`: `no_trade` | `open_trade`
  - `management_case`: `maintain` | `move_sl` | `break_even` | `close`
- `direction`: `buy` | `sell` | `null`
- `entry_price`: numero | `null`
- `sl`: numero | `null`
- `tp`: numero | `null`
- `reason`: string breve obligatoria

## Reglas por tipo de caso

### Entry case

- Si `action = no_trade`, todos los campos operativos son `null`.
- Si `action = open_trade`, `direction`, `entry_price`, `sl` y `tp` son obligatorios.

### Management case

- `direction` no cambia.
- `entry_price` no cambia.
- `sl` y `tp` solo se alteran si la accion lo requiere.
- `reason` siempre existe.

## Logica de decision del MVP

- Prioriza riesgo de `Melchor`.
- Exige validacion tecnica suficiente de `Baltasar` para nuevas entradas.
- Usa `Gaspar` como refuerzo y deteccion de oportunidad.
- Puede abstenerse aunque haya senales mixtas.

## Reglas para `SL` y `TP`

### Stop loss

- Basado en estructura de mercado.
- En compras, por debajo de soporte relevante.
- En ventas, por encima de resistencia relevante.
- Puede ajustarse con volatilidad basica usando `recent_range`.

### Take profit

- Basado en ratio riesgo/beneficio determinista.
- Minimo objetivo `1:1.5`, preferiblemente `1:2`.
- Alineado con estructura si hay niveles claros.
