# Prosperity / MAGI

Backend y consola operativa inicial para Prosperity / MAGI. Esta base ya permite recibir entradas legacy desde `Bot A`, normalizarlas internamente, producir una decision MVP en backend, dejar una respuesta compatible para `Bot B` y visualizar el flujo real en la web.

## Estado actual

- La aplicacion corre localmente con `npm start`.
- `POST /analisis` sigue siendo compatible con `Bot A` sin cambios en MQL5.
- `GET /analisis/:symbol` sigue siendo compatible con `Bot B` sin cambios en MQL5.
- El backend ya persiste:
  - snapshot legacy
  - snapshot normalizado
  - estado de ejecucion por simbolo
  - eventos y errores recientes
- El dashboard MVP ya muestra datos reales en cuatro modulos:
  - `Estado del sistema`
  - `Instantaneas de Bot A`
  - `Casos y decision MAGI`
  - `Despacho y errores`

## Stack actual

- Node.js 22+
- Express 5
- Frontend estatico en HTML, CSS y JavaScript modular
- Persistencia local basada en archivos JSON y JSONL

## Como correrlo localmente

1. Instala dependencias:

```bash
npm install
```

2. Inicia la aplicacion:

```bash
npm start
```

3. Abre:

- `http://localhost:3000/`
- `http://localhost:3000/dashboard`

## Scripts disponibles

- `npm start`: inicia el servidor
- `npm run dev`: inicia en modo watch
- `npm run check`: validacion sintactica del servidor
- `npm run smoke`: prueba rapida de health y dashboard
- `node scripts/test-input-legacy.js`: envia una entrada legacy de prueba a `POST /analisis`

## Persistencia actual

```text
data/
  analysis/             # respuesta legacy disponible para Bot B
  errors/               # errores historicos
  execution/            # estado de ejecucion por simbolo
  logs/                 # eventos y logs diarios
  snapshots/
    legacy/             # payload original recibido desde Bot A
    normalized/         # snapshot interno del backend
  training/             # reservado para fases futuras
```

## Endpoints principales

### Compatibilidad legacy

- `POST /analisis`
- `GET /analisis/:symbol`

### Consola MVP

- `GET /api/overview`
- `GET /api/snapshots`
- `GET /api/snapshots/:id`
- `GET /api/cases`
- `GET /api/cases/:id`
- `GET /api/execution`
- `GET /api/logs`

### Complementarios existentes

- `GET /health`
- `GET /api/status`
- `GET /api/dashboard`
- `GET /api/modules`
- `GET /api/settings`
- `GET /api/connectors`
- `GET /api/connectors/:id`

## Flujo operativo actual

1. `Bot A` envia un JSON legacy a `POST /analisis`.
2. El backend guarda el payload original y genera un snapshot normalizado.
3. El motor MVP decide si hay `sin_caso` o `caso_mvp`.
4. El backend genera una respuesta legacy compatible para `Bot B`.
5. La salida se guarda en `data/analysis/<SYMBOL>.json` y `data/execution/<SYMBOL>.json`.
6. La consola web consume endpoints reales para mostrar el estado actual.

## Documentacion adicional

- [Arquitectura](./docs/architecture.md)
- [Plan de integracion](./docs/integration-plan.md)
- [Transicion a MAGI modular](./docs/magi-modular-transition.md)
- [Contratos de connectors](./docs/connectors.md)
- [Estado del MVP web](./docs/mvp-web-fase0-fase1.md)
- [Referencias legacy](./docs/legacy)
