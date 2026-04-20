# Transicion a MAGI modular

## Objetivo

Evolucionar el backend desde una `decision MVP unica` a un `flujo MAGI modular` compuesto por:

- `Melchor`
- `Baltasar`
- `Gaspar`
- `CEO-MAGI`

sin romper la compatibilidad ya lograda con `Bot A`, `Bot B`, `POST /analisis` y `GET /analisis/:symbol`.

## Principio de compatibilidad

La entrada y la salida externas permanecen congeladas:

- `Bot A` sigue enviando el mismo payload legacy a `POST /analisis`
- `Bot B` sigue leyendo el mismo contrato legacy desde `GET /analisis/:symbol`

Todo el cambio ocurre dentro del backend.

## Arquitectura propuesta

### 1. Entrada estable

- `POST /analisis` sigue siendo el punto de entrada
- se mantiene:
  - parseo
  - validacion
  - snapshot legacy
  - snapshot normalizado

### 2. Capa de evaluacion MAGI

Se reemplaza el motor unico por tres evaluadores independientes:

- `melchor.service.js`
- `baltasar.service.js`
- `gaspar.service.js`

Cada uno recibe el mismo snapshot normalizado y devuelve un voto o evaluacion separada.

### 3. Capa de arbitraje

`ceo-magi.service.js` consume:

- snapshot normalizado
- voto de Melchor
- voto de Baltasar
- voto de Gaspar

y produce:

- decision final canonica
- razon final consolidada
- salida lista para traducirse a formato legacy

### 4. Capa de compatibilidad con Bot B

El mapper actual se conserva, pero deja de leer una decision MVP unica y pasa a leer la decision final de `CEO-MAGI`.

## Como introducir Melchor, Baltasar y Gaspar sin romper compatibilidad

### Paso 1

Agregar servicios nuevos sin quitar el motor MVP existente.

### Paso 2

Hacer que el flujo actual genere tambien evaluaciones separadas, pero mantener el mapper final apuntando todavia a la decision MVP si hace falta rollback rapido.

### Paso 3

Cuando los tres votos y el CEO esten validados, cambiar la fuente del mapper final hacia la decision de `CEO-MAGI`.

### Paso 4

Mantener un modo de fallback al motor MVP durante la transicion inicial.

## Como separar sus votos o evaluaciones

Cada modulo debe producir un contrato estable, por ejemplo:

```json
{
  "snapshot_id": "EURUSD_...",
  "module": "melchor",
  "decision": "approve",
  "confidence": 0.74,
  "risk_flag": "low",
  "context_tag": "trend",
  "reason": "Riesgo contextual controlado.",
  "timestamp": "..."
}
```

Campos base recomendados:

- `snapshot_id`
- `module`
- `decision`
- `confidence`
- `risk_flag`
- `context_tag`
- `reason`
- `timestamp`

## Como construir la capa de CEO-MAGI

`CEO-MAGI` debe ser una capa separada de arbitraje, no un simple promedio.

Entrada:

- snapshot normalizado
- voto de `Melchor`
- voto de `Baltasar`
- voto de `Gaspar`

Salida recomendada:

```json
{
  "snapshot_id": "EURUSD_...",
  "case_state": "caso_magi",
  "case_type": "entry_case",
  "final_action": "open",
  "direction": "buy",
  "entry_price": 1.12,
  "stop_loss": 1.115,
  "take_profit": 1.13,
  "lot_size": 0.01,
  "reason": "Baltasar valida estructura, Melchor no bloquea y Gaspar refuerza oportunidad.",
  "source": "ceo_magi"
}
```

Regla de bajo riesgo:

- `Melchor` puede bloquear
- `Baltasar` valida estructura
- `Gaspar` refuerza o cuestiona oportunidad
- `CEO-MAGI` decide la salida final

## Como persistir votos y decision final

Persistencia inicial sugerida:

```text
data/
  votes/
    melchor/
    baltasar/
    gaspar/
  decisions/
    ceo/
  execution/
```

Por cada snapshot:

- un archivo de voto por modulo
- una decision final de CEO
- una respuesta legacy final para Bot B

## Endpoints nuevos o ampliados

### Nuevos

- `GET /api/votes`
- `GET /api/votes/:snapshotId`
- `GET /api/decisions`
- `GET /api/decisions/:snapshotId`

### Ampliados

- `GET /api/cases`
  - incluir resumen de votos
  - incluir fuente final de decision
- `GET /api/cases/:id`
  - incluir votos completos
  - incluir decision CEO
- `GET /api/execution`
  - incluir referencia a decision final

### Sin cambios

- `POST /analisis`
- `GET /analisis/:symbol`

## Dashboard a ampliar

La consola actual ya tiene:

- estado
- instantaneas
- casos
- despacho
- errores

La ampliacion natural seria:

### Casos y decision MAGI

- mostrar si la decision vino del motor MVP o de `CEO-MAGI`
- mostrar resumen de votos por modulo

### Nuevo bloque de votos

- `Melchor`
- `Baltasar`
- `Gaspar`
- decision
- confidence
- risk_flag
- razon

### Despacho

- seguir mostrando la salida final para `Bot B`
- agregar referencia al `snapshot_id` y a la decision de CEO

## Transicion paso a paso y con bajo riesgo

### Fase A

- crear contratos de voto
- crear servicios `melchor`, `baltasar`, `gaspar`
- persistir votos
- no cambiar aun la salida final

### Fase B

- crear `ceo-magi.service.js`
- persistir decision final de CEO
- exponer endpoints de votos y decisiones
- seguir dejando el mapper final en modo conmutable

### Fase C

- cambiar el mapper final para que la respuesta de `Bot B` venga desde `CEO-MAGI`
- mantener fallback al motor MVP durante validacion

### Fase D

- ampliar dashboard para mostrar votos y decision final modular
- validar consistencia entre votos, CEO y respuesta legacy final

## Riesgos principales

- desalineacion entre votos y respuesta final
- duplicidad temporal entre motor MVP y flujo modular
- incremento de persistencia y endpoints sin orden claro
- mezclar demasiado pronto logica de evaluacion y arbitraje

## Mitigacion

- contratos pequenos y estables
- persistencia separada por modulo
- rollout por capas
- fallback temporal al motor MVP
- mantener congelada la interfaz legacy con los bots
