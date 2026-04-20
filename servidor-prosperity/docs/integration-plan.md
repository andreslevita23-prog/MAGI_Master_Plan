# Integration Plan

## Objetivo

Conectar la base operativa actual con una evolucion gradual hacia MAGI modular, manteniendo compatibilidad con los bots MQL5 existentes y evitando rehacer la arquitectura.

## Estado completado

### Fase cerrada: MVP basico de consola operativa

Ya estan implementados:

- adaptador legacy de `Bot A`
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
- contrato externo de `POST /analisis`
- contrato externo de `GET /analisis/:symbol`

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
