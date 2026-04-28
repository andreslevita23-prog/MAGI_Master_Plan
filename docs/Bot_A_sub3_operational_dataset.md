# Bot_A_sub3 Operational Dataset

## Estado de la etapa

`Bot_A_sub3` queda cerrado como recolector simple y estable para Strategy Tester.

Build validado:

```text
bot_a_sub3_simple_sub1_sub2_2026-04-28_v1
```

Resultado de auditoria del primer dataset limpio:

```text
Decision: APTO
Score: 100/100
Run: run_2025-12-15_00-00-00_659700906
Registros JSONL: 18,612
Registros CSV: 18,612
Duplicados snapshot_id: 0
MTF OK: 74,448/74,448 features
gaspar_context presente: 18,612/18,612
```

Reportes locales:

- `reports/bot_a_sub3_audits/20260428T190039Z_bot_a_sub3_audit.md`
- `reports/bot_a_sub3_audits/20260428T190153Z_bot_a_sub3_simple_audit.md`

## Objetivo

`Bot_A_sub3` combina de forma directa:

- la logica de dataset estable de `Bot_A_sub1`;
- el contexto estructural/temporal de `Bot_A_sub2` para Gaspar;
- el snapshot operativo compartido de Bot A.

No decide, no envia ordenes y no modifica logica de trading. Solo observa y persiste.

## Archivos

- EA: `servidor-prosperity/integrations/mt5/Bot_A_sub3.mq5`
- Snapshot compartido: `servidor-prosperity/integrations/mt5/core/MagiFeatureEngine.mqh`
- Serializacion compartida: `servidor-prosperity/integrations/mt5/core/MagiSerializer.mqh`
- Writer de dataset: `servidor-prosperity/integrations/mt5/core/MagiDatasetWriter.mqh`
- Contexto Gaspar: `servidor-prosperity/integrations/mt5/core/MagiGasparContext.mqh`

## Diseno vigente

`Bot_A_sub3` usa el flujo de `Bot_A_sub1`:

1. selecciona simbolos;
2. espera una nueva vela cerrada del timeframe ancla;
3. llama a `MagiBuildSnapshot(...)`;
4. persiste JSONL completo;
5. persiste CSV plano;
6. guarda todo bajo una carpeta unica `run_*` en `FILE_COMMON`.

La integracion de Gaspar no se implementa como contrato aparte dentro de `sub3`. El bloque `gaspar_context` lo agrega el snapshot compartido, usando el mismo core que puede usar Bot A real.

## Run ID y aislamiento

La version simple genera un `run_id` con fecha/hora y `GetTickCount()`:

```text
run_YYYY-MM-DD_HH-MM-SS_<tick>
```

Esto evita mezclar corridas cuando Strategy Tester repite `TimeLocal()` o arranca varias pruebas con la misma fecha simulada.

Ruta esperada:

```text
<Terminal Common Data Path>/Files/MAGI/datasets/bot_a_sub3/<run_id>/
```

Estructura:

```text
run_YYYY-MM-DD_HH-MM-SS_<tick>/
  EURUSD/
    anchor_M5__primary_H1/
      YYYY/
        MM/
          DD/
            magi_bot_a_sub3_simple__symbol_EURUSD__anchor_M5__primary_H1__date_YYYY-MM-DD.csv
            magi_bot_a_sub3_simple__symbol_EURUSD__anchor_M5__primary_H1__date_YYYY-MM-DD.jsonl
```

## Campos principales

El JSONL contiene el snapshot operativo completo:

- identificacion: `schema_version`, `snapshot_id`, `symbol`, `timestamp`;
- timeframe: `anchor_timeframe`, `primary_timeframe`, `anchor_bar_timestamp`, `bar_timestamp`;
- OHLC ancla: `anchor_open`, `anchor_high`, `anchor_low`, `anchor_close`;
- estructura y niveles: `market_structure`, `structure_direction`, `support_levels`, `resistance_levels`;
- indicadores: `ema_20`, `ema_50`, `ema_200`, `rsi_14`, `momentum`;
- precio/volatilidad: `current_price`, `recent_range`, `spread_pips`;
- operacion observada: `position`, `account`, `allowed_actions`;
- calidad de datos: `validation`, `mtf_alignment_status`, `mtf_data_source_status`;
- features MTF: `features`;
- contexto Gaspar: `gaspar_context`.

El CSV contiene una vista plana para analisis y entrenamiento, incluido `features_json` como JSON autonomo parseable.

## gaspar_context

`gaspar_context` incluye:

- `is_available`
- `schema_version`
- `module`
- `role`
- `symbol`
- `timestamp`
- `anchor_timeframe`
- `structure_timeframes`
- `h4_bar_timestamp`
- `d1_bar_timestamp`
- `h4_age_minutes`
- `d1_age_minutes`
- `context_id`
- `proposed_direction`
- `proposed_direction_source`
- `higher_timeframe_confluence`
- `price_structure_position`
- `timing_quality`
- `day_context`
- `data_quality_flags`

Reglas:

- no contiene EMA;
- no contiene RSI;
- no contiene momentum;
- no contiene confianza;
- no contiene probabilidades;
- no contiene decision final del CEO.

En Strategy Tester, `proposed_direction_source` puede usar un fallback estructural H4/D1 para shadow mode. Eso no convierte a Bot A en decisor; queda marcado como fuente proxy.

## Alineacion MTF

El snapshot compartido alinea M15, H1, H4 y D1 contra `anchor_bar_timestamp`, que representa el cierre de la vela ancla cerrada.

Cada item de `features` incluye:

- `bar_timestamp`
- `bar_close_timestamp`
- `age_minutes`
- `anchor_ibar_shift`
- `selected_shift`
- `selected_array_index`
- `copied_array_size`
- `rates_array_as_series`
- `bars_available`
- `oldest_bar_time`
- `newest_bar_time`
- `data_source_status`
- `alignment_status`
- `alignment_warning`

Estados:

- `OK`: la feature esta alineada.
- `INSUFFICIENT_HISTORY`: MT5 no entrego historico suficiente.
- `ALIGNMENT_ERROR`: existe historico, pero no se encontro una vela cerrada valida dentro de la regla temporal.

`Bot_A_sub3` no oculta errores MTF. Si una feature no esta disponible, queda marcada en el snapshot. En la corrida auditada con `skip_invalid_snapshots=true`, todos los snapshots persistidos quedaron validos.

## Como correr

1. Copiar o sincronizar `Bot_A_sub3.mq5` y la carpeta `core/` dentro de `MQL5/Experts`.
2. Abrir MetaEditor y compilar `Bot_A_sub3.mq5`.
3. En Strategy Tester seleccionar:
   - Symbol: `EURUSD`
   - `InpAnchorTimeframe = M5`
   - `InpPrimaryTimeframe = H1`
   - `InpWriteCsv = true`
   - `InpWriteJsonl = true`
   - `InpSkipInvalidSnapshots = true` para dataset limpio de entrenamiento base.
   - `InpSkipInvalidSnapshots = false` para una corrida futura con snapshots parciales/invalidos.
4. Ejecutar la prueba.
5. Verificar el marker:

```text
__runtime_marker__bot_a_sub3_simple_sub1_sub2_2026-04-28_v1.txt
```

## Como validar

Ejecutar:

```powershell
& "C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\audit_bot_a_sub3_dataset.py --data-path "C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\<run_id>" --output-dir reports\bot_a_sub3_audits
```

Criterios minimos:

- JSONL parseable linea por linea.
- CSV parseable.
- `features_json` parseable con `json.loads`.
- `snapshot_id` unico dentro de la corrida.
- OHLC consistente.
- `spread_pips >= 0`.
- `rsi_14` dentro de 0..100.
- `gaspar_context` presente.
- M15/H1/H4/D1 con `age_minutes` dentro del limite esperado cuando `data_source_status=OK`.
- errores MTF marcados como `validation`/`alignment_warning`, no ocultos.

## Pendientes

- Ejecutar una corrida futura con `InpSkipInvalidSnapshots=false`.
- Generar dataset con snapshots parciales/invalidos para robustez.
- Entrenamiento formal de Baltasar.
- Entrenamiento formal de Gaspar.
- Diseno de labels para entrenamiento supervisado.
- Integracion con CEO-MAGI.
- Integracion futura con Bot C y outcomes reales.

## Regla de compatibilidad

`Bot_A_sub3` no tiene contrato propio. Si un campo existe en su JSONL, existe en el contrato compartido que usa `Bot_A` real.
