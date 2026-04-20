# Connectors

## Objetivo

Esta capa define contratos y mocks para las futuras integraciones de MAGI sin activar trading real ni acoplar todavia servicios externos.

## Ubicacion

```text
src/server/services/connectors/
  adapters/
  registry.js
  shared.js
```

## Connectors disponibles

- `bot-a`: entrada de contexto y datos de mercado
- `bot-b`: salida de decisiones operativas
- `bot-c`: confirmacion complementaria
- `melchor`: seguridad y riesgo
- `baltasar`: analisis tecnico y datos
- `gaspar`: exploracion y oportunidad
- `ceo-magi`: arbitraje y decision final

## Contrato comun

Cada connector declara:

- `id`, `name`, `family`, `role`, `description`
- `inputContract`
- `outputContract`
- `connection`
- `mock`

## Endpoints

- `GET /api/connectors`
- `GET /api/connectors/:id`

## Siguiente integracion real sugerida

1. Conectar `Bot A` a un webhook o puente MT5.
2. Conectar `Melchor` a una politica real de riesgo.
3. Conectar `CEO-MAGI` a una orquestacion que combine salidas de Melchor, Baltasar y Gaspar.
