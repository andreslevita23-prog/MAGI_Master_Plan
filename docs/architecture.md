# Architecture

## Resumen

Prosperity / MAGI queda dividido en cuatro dominios claros:

- `src/client`: interfaz web y dashboard tecnico
- `src/server`: servidor Express, rutas y servicios
- `src/server/services/connectors`: contratos, mocks y registro de adapters
- `data`: almacenamiento local de analisis, logs, errores y respuestas
- `integrations`: conectores externos y artefactos MT5

## Flujo actual

1. Un bot o cliente envia una carga JSON a `POST /analisis`.
2. El servidor registra la entrada en `data/logs/<fecha>/botA.jsonl`.
3. Si hay `OPENAI_API_KEY`, solicita decision al modelo configurado.
4. Si no hay clave o el parseo falla y `MAGI_ENABLE_MOCKS=true`, responde con un fallback limpio.
5. La decision final se guarda en `data/analysis/<SYMBOL>.json` y en `botB.jsonl`.
6. El dashboard consume `GET /api/dashboard` para renderizar overview, modulos, decisiones, logs y settings.
7. Los contratos de integracion se exponen por `GET /api/connectors` para preparar conexiones reales sin acoplarlas todavia.

## Decisiones de diseno

- Se mantuvo Express por minimo impacto.
- Se evito introducir frameworks frontend pesados.
- Se conservo la persistencia local por archivos, util para recuperacion tecnica inmediata.
- Se agrego una capa de servicios para aislar paths, logging y agregacion del dashboard.
- Se agrego un registro de connectors para desacoplar futuras integraciones de bots y modulos MAGI.

## Evolucion sugerida

- Extraer adaptadores por bot en `src/server/services/adapters/`.
- Agregar autenticacion para dashboard y endpoints sensibles.
- Sustituir almacenamiento por base de datos cuando existan requerimientos de concurrencia.
