# Architecture

## Resumen

Prosperity / MAGI queda dividido actualmente en cinco dominios claros:

- `src/client`: consola web operativa en espanol
- `src/server`: servidor Express, rutas y servicios
- `src/server/services/connectors`: contratos y registro de futuras integraciones
- `src/server/services/adapters`, `orchestrator`, `execution`, `snapshots`: capa MVP ya operativa
- `data`: persistencia local de snapshots, ejecucion, logs, errores y respuestas legacy

## Flujo actual real

1. `Bot A` envia un payload legacy a `POST /analisis`.
2. El backend valida la entrada y la registra en `data/logs/<fecha>/botA.jsonl`.
3. El payload original se guarda en `data/snapshots/legacy/`.
4. El backend genera un snapshot normalizado y lo guarda en `data/snapshots/normalized/`.
5. El motor `mvp_decision_engine` clasifica `sin_caso` o `caso_mvp`.
6. La decision MVP se traduce a respuesta legacy para `Bot B`.
7. La salida final se guarda en:
   - `data/execution/<SYMBOL>.json`
   - `data/analysis/<SYMBOL>.json`
8. La consola consume endpoints reales para mostrar estado, snapshots, casos, despacho y errores.

## Decisiones de diseno activas

- Se mantuvo `POST /analisis` para no romper compatibilidad con `Bot A`.
- Se mantuvo `GET /analisis/:symbol` para no romper compatibilidad con `Bot B`.
- La nueva logica vive solo en backend mediante adaptadores y orquestacion.
- La persistencia sigue siendo local por archivos para facilitar auditoria y desarrollo.
- La consola MVP usa datos reales y ya no depende de placeholders para el flujo principal.

## Estructura actual relevante

```text
src/
  client/
    dashboard.html
    scripts/
    styles/
  server/
    config/
    domain/
      contracts/
    services/
      adapters/
      cases/
      connectors/
      execution/
      logs/
      orchestrator/
      snapshots/
      system/
      validation/
data/
  analysis/
  errors/
  execution/
  logs/
  snapshots/
    legacy/
    normalized/
  training/
```

## Límite actual del sistema

La arquitectura actual no es todavia MAGI modular completa. Hoy existe una unica capa de decision MVP. El siguiente paso natural es separar evaluaciones de `Melchor`, `Baltasar` y `Gaspar`, agregar una capa formal de `CEO-MAGI` y persistir votos mas decision final sin romper la compatibilidad ya lograda.
