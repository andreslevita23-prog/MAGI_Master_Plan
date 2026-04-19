# 07. Melchor

## Mision

Proteger capital y bloquear escenarios peligrosos.

## Responsabilidades en el MVP

- Analizar riesgo contextual del snapshot.
- Endurecer su criterio cuando existe una posicion abierta.
- Bloquear cualquier intento de nueva entrada si ya hay una operacion viva.
- Emitir voto de riesgo bajo el contrato comun.

## Señales tipicas que pesan en Melchor

- Estructura dudosa o inestable.
- Volatilidad anormal frente al rango reciente.
- Distancia de `SL` irracional respecto a estructura.
- Relacion riesgo/beneficio deficiente.
- Exposicion viva ya existente.

## Rol futuro con ML

Melchor podra usar ML para mejorar deteccion de escenarios peligrosos y filtros de rechazo, pero sus reglas duras nunca dependeran exclusivamente de un modelo.
