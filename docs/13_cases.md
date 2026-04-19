# 13. Cases

## entry_case

### Condiciones de activacion

- No existe posicion abierta.
- No existe otro caso activo.
- Uno o mas magos detectan oportunidad real de entrada.

### Resolucion

- El caso nace cuando un mago lo dispara.
- Los tres magos votan sobre el mismo snapshot.
- El CEO decide `no_trade` o `open_trade`.
- El caso se considera cerrado cuando el CEO decide.

## management_case

### Condiciones de activacion

- Existe una posicion abierta.
- No existe otro caso activo.
- Un mago detecta necesidad real de gestion.
- No se activa por reevaluacion pasiva.

### Acciones permitidas

- `maintain`
- `move_sl`
- `break_even`
- `close`

### Resolucion

- El caso se cierra cuando el CEO toma la decision.
- Un nuevo `management_case` solo puede nacer en un snapshot posterior con nueva razon valida.
