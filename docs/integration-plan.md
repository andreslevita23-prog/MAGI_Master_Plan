# Integration Plan

## Objetivo

Dejar una ruta clara para conectar la base recuperada con el ecosistema MAGI sin rehacer la arquitectura.

## Integraciones previstas

- `Bot A`: entrada de contexto y datos de mercado
- `Bot B`: decisiones operativas y salida de ejecucion
- `Bot C`: soporte adicional para analisis o confirmaciones
- `Melchor`: seguridad y riesgo
- `Baltasar`: analisis tecnico y consolidacion de datos
- `Gaspar`: exploracion de oportunidades
- `CEO-MAGI`: arbitraje de decision final

## Puntos de extension

- Crear adaptadores en `src/server/services` por integracion.
- Estabilizar un contrato JSON por evento para señales y logs.
- Reemplazar mocks del dashboard por endpoints dedicados de cada modulo.
- Publicar configuraciones sensibles solo via variables de entorno.

## Connectors implementados en esta fase

- `Bot A`: contrato para entrada de contexto de mercado
- `Bot B`: contrato para despacho de decisiones
- `Bot C`: contrato para confirmacion complementaria
- `Melchor`: contrato de evaluacion de riesgo
- `Baltasar`: contrato de analisis tecnico
- `Gaspar`: contrato de exploracion de oportunidades
- `CEO-MAGI`: contrato de orquestacion final

Todos estan en `src/server/services/connectors/adapters/` y hoy operan en modo mock-ready.

## Como conectarlos despues

1. Definir la variable de entorno del connector correspondiente.
2. Sustituir el `mock.sample` por una llamada real o un adaptador de transporte.
3. Mantener el mismo `inputContract` y `outputContract` para no romper dashboard ni orquestacion.
4. Exponer salud o telemetria propia por connector cuando ya exista backend real.

## Checklist sugerido

- Definir contrato para `POST /analisis`
- Normalizar IDs de operacion
- Unificar timestamps en UTC
- Agregar endpoint de metricas
- Definir estrategia de despliegue y proxy para `prosperity.lat`
