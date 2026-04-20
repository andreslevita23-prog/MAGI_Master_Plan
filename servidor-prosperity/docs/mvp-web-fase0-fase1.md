# MVP web - Fase 0 y Fase 1

## Objetivo inmediato

Preparar la base tecnica para el MVP del centro de mando sin afectar el flujo actual:

- mantener `POST /analisis`
- mantener `GET /analisis/:symbol`
- no modificar bots MQL5
- agregar persistencia y contratos internos para la nueva capa MAGI

## Alcance de este paso

Este documento acompana solo la base minima:

- nuevas carpetas de datos
- contratos internos
- soporte de persistencia

Todavia no incluye:

- adaptador de normalizacion
- endpoints nuevos
- cambios del dashboard
- logica de casos o decisiones MAGI

## Carpetas nuevas previstas

- `data/snapshots/legacy/`
- `data/snapshots/normalized/`
- `data/execution/`
- `data/system/`

## Contratos base

### `snapshot_legacy_mt5`

Representa el payload actual enviado por `Bot A`.

### `snapshot_v1`

Representa el snapshot canonico interno que usara MAGI.

### `bot_b_legacy_response`

Representa la salida compatible que seguira consumiendo `Bot B`.

## Criterio de exito de este paso

- el servidor puede inicializar las nuevas carpetas
- no se altera el comportamiento actual del backend
- los contratos quedan disponibles para los siguientes pasos
