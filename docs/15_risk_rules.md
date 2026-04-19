# 15. Risk Rules

## Reglas duras del MVP

- Solo `EURUSD`.
- Maximo una operacion abierta.
- Maximo un caso activo.
- Con posicion abierta, quedan bloqueados nuevos `entry_case`.
- `Melchor` debe bloquear cualquier intento de nueva entrada si ya existe una operacion viva.

## Reglas de entrada

- No abrir si `Melchor = reject` y `risk_flag = high`.
- No abrir si `Baltasar = reject` con alta `confidence`.
- No abrir si el `SL` estructural deja una relacion riesgo/beneficio invalida.

## Reglas de gestion

- No sobregestionar.
- Solo activar `management_case` por cambio relevante.
- Priorizar proteccion de capital y beneficios antes que frecuencia de ajuste.

## Racional

Las reglas duras existen para mantener el MVP controlado, auditable y apto para generar datos consistentes.
