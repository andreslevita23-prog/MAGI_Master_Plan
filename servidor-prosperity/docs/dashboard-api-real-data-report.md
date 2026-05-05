# Reporte breve: rutas API dashboard MAGI

Fecha: 2026-05-05

## Diagnostico

El codigo actual del backend en `src/server/index.js` si implementa las rutas:

- `GET /api/overview`
- `GET /api/snapshots`
- `GET /api/execution`

La instancia viva probada en `http://127.0.0.1:3000` respondia `Cannot GET` para esas rutas, pero su `GET /health` devolvia un contrato viejo sin `services`. Eso indica que el proceso activo en el puerto 3000 no corresponde a la version actual del repo.

## Rutas confirmadas

| Ruta | Fuente de datos real | Devuelve |
| --- | --- | --- |
| `GET /api/overview` | `data/snapshots/normalized`, `data/execution` | Estado general, ultimo snapshot, estado Bot A y ultima decision/ejecucion persistida. |
| `GET /api/snapshots` | `data/snapshots/normalized` y `data/snapshots/legacy` | Lista reciente de snapshots, ultimo snapshot y total devuelto. |
| `GET /api/execution` | `data/execution/*.json` | Estados de ejecucion por simbolo, payload preparado para Bot B, ultimo estado y total devuelto. |

## Dashboard

`src/client/scripts/dashboard.js` ya consume datos reales con:

- `fetch("/api/overview")`
- `fetch("/api/snapshots?limit=12")`
- `fetch("/api/execution")`

No se detecto uso de datos mock para esas secciones.

## Como verificar en navegador

1. Detener cualquier proceso viejo que este usando el puerto 3000.
2. Iniciar desde la carpeta `servidor-prosperity`:

```bash
npm run start:demo
```

3. Abrir:

- `http://127.0.0.1:3000/health`
- `http://127.0.0.1:3000/api/overview`
- `http://127.0.0.1:3000/api/snapshots`
- `http://127.0.0.1:3000/api/execution`
- `http://127.0.0.1:3000/dashboard`

## Dictamen

DASHBOARD LISTO PARA DATOS REALES.
