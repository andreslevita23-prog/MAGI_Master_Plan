# Integration Plan

## Objetivo

Conectar la base operativa actual con una evolucion gradual hacia MAGI modular, manteniendo compatibilidad con los bots MQL5 existentes y evitando rehacer la arquitectura.

## Estado completado

### Fase cerrada: MVP basico de consola operativa

Ya estan implementados:

- adaptador legacy de `Bot A`
- adaptador `magi.snapshot.v2` de `Bot A` actual
- snapshot normalizado interno
- validacion de entrada
- motor de decision MVP
- mapper de salida compatible con `Bot B`
- persistencia de ejecucion por simbolo
- endpoints reales de inspeccion
- consola web operativa con datos reales

## Integraciones siguientes previstas

- `Melchor`: evaluacion de riesgo
- `Baltasar`: evaluacion tecnica
- `Gaspar`: evaluacion de oportunidad
- `CEO-MAGI`: arbitraje final

## Regla de transicion

La transicion debe hacerse sin tocar:

- `integrations/mt5/BotA_v3.1.mq5`
- `integrations/mt5/botB_v3.0.mq5`
- contrato externo legacy de `POST /analisis`
- contrato externo de `GET /analisis/:symbol`

## Contratos aceptados por POST /analisis

`POST /analisis` acepta dos contratos de entrada:

- `snapshot_legacy_mt5`: contrato historico de Bot A con campos como `pair`, `price`, `context`, `allowed_actions` e `id_operacion`.
- `magi.snapshot.v2`: contrato tecnico actual de Bot A, alineado con el dataset generator `Bot_A_sub3`, con `symbol`, `current_price`, OHLC de barra ancla, indicadores, `features`, `gaspar_context`, `account`, `position` y `validation`.

El backend detecta `magi.snapshot.v2` por `schema_version` y lo normaliza mediante `snapshot-v2-adapter.js`. Si no detecta v2, conserva el flujo legacy sin eliminar funciones existentes.

Campos criticos para `magi.snapshot.v2`:

- `symbol`
- `current_price`
- `timestamp`

Si falta alguno, el endpoint rechaza la entrada con error `400`. Los campos no criticos faltantes se registran como issues de adaptacion para que aparezcan en logs, persistencia y consultas de snapshots.

Limitaciones pendientes conocidas:

- `daily_drawdown_percent` real no se calcula en Bot A; si llega en `0.0`, se conserva y se marca warning.
- `risk_percent_per_trade` real no se calcula en Bot A; si llega en `0.0`, se conserva y se marca warning.
- `news_context` aun llega como `news: []`.
- Multiples posiciones abiertas no tienen detalle individual completo de SL/TP por posicion.

## Proximo objetivo tecnico

Pasar de una `decision MVP unica` a un `flujo MAGI modular`, donde:

1. el snapshot normalizado alimenta a tres evaluadores separados
2. cada evaluador persiste su voto
3. `CEO-MAGI` toma la decision final
4. la respuesta final sigue saliendo en formato legacy compatible con `Bot B`

## Criterio de bajo riesgo

- agregar capas nuevas sin eliminar la actual hasta validar
- conservar persistencia por archivos en la primera iteracion modular
- exponer primero lectura por API antes de ampliar la UI
- hacer rollout por pasos: evaluadores -> votos -> CEO -> dashboard

## Documento de referencia para la siguiente fase

Ver [magi-modular-transition.md](./magi-modular-transition.md).
