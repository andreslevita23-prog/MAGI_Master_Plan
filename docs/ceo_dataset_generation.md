# CEO-MAGI Dataset Generation

## Objetivo

El dataset CEO-MAGI se genera para entrenar y validar un futuro modelo CEO-MAGI sin depender todavía de una estrategia fija de SL/TP. Cada registro combina:

- snapshot histórico de Bot A sub3
- voto normalizado de Melchor real
- voto normalizado de Baltasar real
- voto normalizado de Gaspar real
- outcomes futuros crudos del precio

El propósito es medir qué combinaciones de votos fueron seguidas por movimientos favorables, adversos o planos en horizontes definidos.

## Flujo De Generación

El flujo se ejecuta desde `run_simulation.py` con `ceo_training_mode=true`:

1. Carga snapshots Bot A sub3 desde JSONL.
2. Normaliza timestamps y contratos `Snapshot`.
3. Valida campos mínimos.
4. Ordena por `symbol` y `anchor_bar_timestamp`.
5. Ejecuta Baltasar real.
6. Ejecuta Gaspar real usando la dirección propuesta por Baltasar cuando aplica.
7. Ejecuta Melchor real como filtro operativo/riesgo.
8. Calcula outcomes futuros crudos por horizonte.
9. Escribe registros auditables en JSONL y resumen en JSON/Markdown.

Comando usado para el run documentado:

```powershell
& 'C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' run_simulation.py --config config/simulator_v01.yaml --input-path 'C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00_659700906'
```

## Dataset Usado

- Fuente: Bot A sub3
- Run: `run_2025-12-15_00-00-00_659700906`
- Formato procesado: JSONL
- Símbolo: EURUSD
- Snapshots cargados: 18,612
- Snapshots válidos: 18,612
- Registros CEO generados: 18,600
- Registros omitidos por falta de barras futuras: 12
- Periodo observado: 2025-12-13 a 2026-04-14

## Estructura De `ceo_training_records.jsonl`

Cada línea es un objeto JSON independiente con este contrato:

```json
{
  "schema_version": "ceo_training_record_v0.1",
  "snapshot_id": "string",
  "symbol": "EURUSD",
  "timestamp": "ISO-8601 UTC",
  "anchor_bar_timestamp": "ISO-8601 UTC",
  "features_at_decision_time": {},
  "melchor_vote": {},
  "baltasar_vote": {},
  "gaspar_vote": {},
  "future_outcomes": {},
  "leakage_guard": {}
}
```

### Votos Normalizados

Los tres magos se guardan usando el contrato `MageVote`:

- `agent`
- `agent_version`
- `vote`
- `direction`
- `quality`
- `confidence`
- `risk_flag`
- `context_tag`
- `features_used`
- `reason`

Baltasar aporta principalmente `direction` (`BUY`, `SELL`, `NEUTRAL`). Gaspar aporta principalmente `quality` (`GOOD`, `FAIR`, `POOR`). Melchor aporta `vote` (`APPROVE`, `BLOCK`) y debe interpretarse como filtro operativo/riesgo, no como predictor directo de rentabilidad.

## Horizontes Usados

Los outcomes se calcularon en barras M5:

- 12 barras
- 48 barras
- 96 barras
- 288 barras

Para cada horizonte se calcula:

- `future_return`
- `future_return_pips`
- `max_favorable_excursion`
- `max_adverse_excursion`
- `real_direction`
- `reached_up_pips`
- `reached_down_pips`

La lectura direccional depende del voto de Baltasar:

- Si Baltasar vota `BUY`, favorable es subida y adverso es bajada.
- Si Baltasar vota `SELL`, favorable es bajada y adverso es subida.
- Si Baltasar vota `NEUTRAL`, se guarda el outcome no direccional y no se calcula hit rate direccional.

## Leakage Guard

El generador elimina campos con nombres asociados a etiquetas futuras o resultados posteriores:

- `future`
- `outcome`
- `pnl`
- `mfe`
- `mae`
- `target`
- `label`
- `forward_return`
- `hit_tp`
- `hit_sl`

Cada registro incluye:

- `features_cutoff_timestamp`: timestamp del snapshot.
- `labels_generated_after_timestamp`: timestamp del snapshot.
- `removed_feature_paths`: rutas removidas por leakage guard.
- `features_clean`: indicador final de limpieza del payload.

## Outputs

El run principal quedó en:

`data/output/ceo_training/20260429T002335Z_magi_v01_phase2/`

Archivos principales:

- `ceo_training_records.jsonl`
- `ceo_training_summary.json`
- `ceo_training_summary.md`
- análisis agregados en JSON/Markdown/CSV

Los outputs bajo `data/output/ceo_training/*` no se versionan en Git porque contienen artefactos pesados y reproducibles.

## Limitaciones

- No se entrenó CEO-MAGI.
- No se optimizaron reglas ni modelos.
- No se evaluaron trades, SL/TP ni ejecución real.
- La muestra cubre aproximadamente cuatro meses y un símbolo.
- El análisis depende de calidad temporal y consistencia de Bot A sub3.
- La validación fuera de muestra todavía está pendiente.
