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

## Checklist sugerido

- Definir contrato para `POST /analisis`
- Normalizar IDs de operacion
- Unificar timestamps en UTC
- Agregar endpoint de metricas
- Definir estrategia de despliegue y proxy para `prosperity.lat`
