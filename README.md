# Prosperity / MAGI

Base tecnica recuperada para la plataforma central de Prosperity y la futura visualizacion operativa de MAGI. El proyecto combina un backend ligero en Express con un dashboard tecnico para monitorear estado general, modulos MAGI, decisiones, logs y configuracion.

## Estado actual

- La aplicacion corre localmente con `npm start`.
- El dashboard minimo ya incluye `Overview`, `Modules`, `Decisions / Signals`, `Logs` y `Settings`.
- El backend mantiene el endpoint historico `POST /analisis` y persiste decisiones en `data/analysis`.
- Si falta `OPENAI_API_KEY`, el servidor puede operar en modo mock para no bloquear desarrollo local.

## Stack detectado

- Node.js 22+
- Express 5
- OpenAI SDK
- Frontend estatico en HTML, CSS y JavaScript modular
- Persistencia local basada en archivos JSON y JSONL

## Como correrlo localmente

1. Instala dependencias:

```bash
npm install
```

2. Crea tu archivo de entorno:

```bash
copy .env.example .env
```

3. Inicia la aplicacion:

```bash
npm start
```

4. Abre:

- `http://localhost:3000/`
- `http://localhost:3000/dashboard`

## Scripts disponibles

- `npm start`: inicia el servidor
- `npm run dev`: inicia en modo watch
- `npm run check`: validacion sintactica del servidor
- `npm run smoke`: prueba rapida de health y dashboard
- `npm run test:input`: envia una entrada de prueba al endpoint de analisis

## Variables de entorno

Estas variables estan documentadas en `.env.example`:

- `PORT`: puerto local del servidor
- `OPENAI_API_KEY`: clave para analisis real con OpenAI
- `MAGI_OPENAI_MODEL`: modelo a usar para decisiones
- `MAGI_SITE_URL`: URL objetivo de despliegue
- `MAGI_ENABLE_MOCKS`: permite respuestas mock cuando falte IA o falle el parseo

## Estructura de carpetas

```text
src/
  client/
    assets/
    scripts/
    styles/
  server/
    config/
    services/
docs/
config/
data/
  analysis/
  errors/
  logs/
  responses/
  training/
integrations/
  mt5/
scripts/
```

## Endpoints principales

- `GET /health`
- `GET /api/status`
- `GET /api/dashboard`
- `GET /api/signals`
- `GET /api/modules`
- `GET /api/logs`
- `GET /api/settings`
- `GET /analisis/:symbol`
- `POST /analisis`

## Preparacion para despliegue futuro

- `MAGI_SITE_URL` ya permite declarar el dominio destino `https://prosperity.lat`.
- La estructura separa claramente codigo, datos, integraciones y configuracion.
- El dashboard usa datos persistidos y mocks controlados, lo que facilita conectar backend real sin rehacer la UI.

## Documentacion adicional

- [Arquitectura](./docs/architecture.md)
- [Roadmap](./docs/roadmap.md)
- [Plan de integracion](./docs/integration-plan.md)
- [Referencias legacy](./docs/legacy)

## Pendiente recomendado

- Rotar la `OPENAI_API_KEY` existente si estuvo expuesta fuera del entorno local.
- Conectar fuentes reales de Bot A, Bot B, Bot C y telemetria de MAGI.
- Agregar pruebas automatizadas para endpoints y adaptadores de logs.
- Inicializar o reconectar el repositorio Git con su remoto oficial antes del push final.
