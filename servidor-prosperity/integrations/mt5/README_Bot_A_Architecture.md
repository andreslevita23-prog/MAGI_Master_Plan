# MAGI MT5 Bot_A Architecture

## Objetivo

Esta implementacion separa `Bot_A` (produccion) y `Bot_A_sub1` (Strategy Tester) sobre un nucleo compartido para que ambos generen el mismo snapshot y la misma semantica de features.

## Archivos

- `Bot_A.mq5`
  Resuelve: captura en vivo y envio HTTP del snapshot.
  Riesgo que evita: divergencia entre recoleccion y transporte.
  Prueba: compilar en MT5 y validar `WebRequest` con URL autorizada.

- `Bot_A_sub1.mq5`
  Resuelve: generacion de dataset historico en tester con politica de almacenamiento configurable.
  Riesgo que evita: rutas ambiguas o no reproducibles en exportacion.
  Prueba: compilar, correr en Strategy Tester y verificar archivos `.csv` y `.jsonl`.

- `Bot_A_sub3.mq5`
  Resuelve: recoleccion simple y estable de dataset operativo completo, combinando el flujo de dataset de `Bot_A_sub1` con `gaspar_context`.
  Riesgo que evita: entrenar o simular con un contrato distinto al que produce el sensor real.
  Prueba: compilar, correr en Strategy Tester y verificar carpeta unica por `run_id`, JSONL completo, CSV plano, `gaspar_context` y auditoria APTO.

- `core/MagiCommon.mqh`
  Resuelve: tipos, timestamps, validacion y helpers comunes.
  Riesgo que evita: nombres inconsistentes y logs dispersos.
  Prueba: compilacion transitiva desde ambos EAs.

- `core/MagiFeatureEngine.mqh`
  Resuelve: calculo compartido de features usando barras cerradas.
  Riesgo que evita: leakage por usar barra en formacion.
  Prueba: compilacion y validacion funcional en MT5/Tester.

- `core/MagiGasparContext.mqh`
  Resuelve: calculo del bloque separado `gaspar_context` requerido por Gaspar sin mezclar EMA, RSI, momentum ni features internas de Baltasar.
  Riesgo que evita: contaminar el contrato de Gaspar con senales direccionales de otro modulo.
  Prueba: inspeccionar JSONL y confirmar que `gaspar_context` contiene solo estructura H4/D1, posicion en rango, sesion y contexto diario.

- `core/MagiSerializer.mqh`
  Resuelve: mismo payload JSON/CSV para vivo y tester.
  Riesgo que evita: esquemas distintos entre inferencia y entrenamiento.
  Prueba: inspeccion de salidas y parsing en backend.

- `core/MagiTransport.mqh`
  Resuelve: encapsular `WebRequest`.
  Riesgo que evita: duplicar manejo HTTP y errores.
  Prueba: envio manual desde MT5.

- `core/MagiDatasetWriter.mqh`
  Resuelve: politica de almacenamiento, construccion de rutas, validacion previa a escritura y trazabilidad.
  Riesgo que evita: append silencioso en rutas desconocidas, fallos opacos y datos historicos inconsistentes.
  Prueba: validar creacion de carpetas, cabecera unica, append y logs en Tester.

## Flujo de datos

1. `OnTick` detecta una nueva barra cerrada en el timeframe ancla.
2. `MagiFeatureEngine` calcula features con `shift=1`.
3. `MagiCommon` agrega validaciones e incidencias.
4. `MagiSerializer` genera JSON y CSV derivados del mismo snapshot.
5. `Bot_A` envia el JSON; `Bot_A_sub1` persiste dataset.

## Contrato de salida

El snapshot preserva los campos canonicos del proyecto:

- `symbol`
- `timestamp`
- `market_structure`
- `structure_direction`
- `support_levels`
- `resistance_levels`
- `ema_20`
- `ema_50`
- `ema_200`
- `rsi_14`
- `momentum`
- `current_price`
- `recent_range`
- `position`

Y agrega bloques utiles para escalabilidad:

- `schema_version`
- `snapshot_id`
- `source_mode`
- `trigger_type`
- `anchor_timeframe`
- `primary_timeframe`
- `features`
- `validation`
- `spread_pips`
- `active_session`
- `allowed_actions`
- `account`
- `news`
- `operational_notes`
- `gaspar_context`

`Bot_A_sub3` usa `MagiBuildSnapshot` y `MagiSerializeSnapshotJson`, los mismos componentes que usa `Bot_A` real. Por regla de contrato, si un campo aparece en el dataset de `Bot_A_sub3`, tambien puede ser producido por `Bot_A` real. Los campos que aun no tienen fuente operativa definitiva quedan con valor `0`, arreglo vacio o nota `pending`, pero el contrato ya existe.

### Cierre de etapa Bot_A_sub3

La version cerrada para dataset operativo simple es:

```text
bot_a_sub3_simple_sub1_sub2_2026-04-28_v1
```

Auditoria:

```text
decision=APTO
score=100/100
run_id=run_2025-12-15_00-00-00_659700906
csv_rows=18,612
jsonl_rows=18,612
duplicate_snapshot_id=0
mtf_status=OK en 74,448/74,448 features
gaspar_context=presente en 18,612/18,612 snapshots
```

Esta version elimina la instrumentacion diagnostica pesada dentro del EA y conserva un flujo facil de entender: detectar barra cerrada, construir snapshot, persistir CSV/JSONL. Si se requiere diagnostico de snapshots parciales, correr con `InpSkipInvalidSnapshots=false`.

## Politica de almacenamiento para Bot_A_sub3

`Bot_A_sub3` fuerza `COMMON_FILES` y no usa fallback local para evitar mezclar corridas en rutas ambiguas del Strategy Tester.

Ruta relativa recomendada:

`MAGI\\datasets\\bot_a_sub3\\<run_id>\\<symbol>\\anchor_<TF>__primary_<TF>\\YYYY\\MM\\DD\\<prefix>__symbol_<SYMBOL>__anchor_<TF>__primary_<TF>__date_<YYYY-MM-DD>.<ext>`

Ejemplo:

- CSV:
  `...\\Common\\Files\\MAGI\\datasets\\bot_a_sub3\\run_2026-04-28_12-00-00_123456\\EURUSD\\anchor_M5__primary_H1\\2026\\04\\28\\magi_bot_a_sub3_simple__symbol_EURUSD__anchor_M5__primary_H1__date_2026-04-28.csv`

- JSONL:
  `...\\Common\\Files\\MAGI\\datasets\\bot_a_sub3\\run_2026-04-28_12-00-00_123456\\EURUSD\\anchor_M5__primary_H1\\2026\\04\\28\\magi_bot_a_sub3_simple__symbol_EURUSD__anchor_M5__primary_H1__date_2026-04-28.jsonl`

El JSONL conserva el snapshot completo. El CSV aplana los campos principales del snapshot y los campos de `gaspar_context` para analisis tabular, entrenamiento y simulador Python.

## Alineacion temporal MTF

Las features M15, H1, H4 y D1 se alinean contra `anchor_bar_timestamp`.

`anchor_bar_timestamp` se calcula como el cierre de la vela ancla cerrada (`MqlRates.time + PeriodSeconds(anchor_timeframe)`). MT5 entrega `MqlRates.time` como apertura; usarlo directamente desplazaria el snapshot M5 una vela parcial hacia atras para la auditoria MTF.

El motor registra el resultado de `iBarShift(symbol, timeframe, anchor_bar_timestamp, false)` para depuracion, pero la seleccion real es por ventana temporal con `CopyRates`: solo acepta la ultima vela cuyo `bar_time <= anchor_bar_timestamp` y cuyo cierre teorico `bar_time + PeriodSeconds(timeframe) <= anchor_bar_timestamp`. Despues vuelve a cargar una ventana historica por rango temporal y busca explicitamente `rates[i].time == selected_bar_time`; no asume que `rates[0]` venga alineado desde `CopyRates`. Si no existe una vela cerrada dentro del limite esperado, marca `alignment_status=error` en vez de usar una vela vieja.

El `age_minutes` reportado mide los minutos desde el cierre de la vela usada hasta el `anchor_bar_timestamp`.

Limites esperados por auditoria:

- M15: `age_minutes <= 15`
- H1: `age_minutes <= 60`
- H4: `age_minutes <= 240`
- D1: `age_minutes <= 1440`

El snapshot incluye `mtf_alignment_status`, `mtf_alignment_warnings` y `mtf_data_source_status`. Cada item de `features` incluye `bar_timestamp`, `age_minutes`, `bars_available`, `oldest_bar_time`, `newest_bar_time`, `data_source_status`, `alignment_status` y `alignment_warning`.

`mtf_data_source_status=INSUFFICIENT_HISTORY` indica que Strategy Tester no entrego historico MTF suficiente alrededor del `anchor_bar_timestamp`. `ALIGNMENT_ERROR` indica que el historico existe, pero la seleccion de vela cerrada fallo. En ambos casos Bot A observa y reporta el fallo; no sustituye la vela por contexto viejo.

`Bot_A_sub3` simple no agrega una arquitectura de diagnostico propia. Usa `InpSkipInvalidSnapshots`:

- `true`: genera un dataset limpio de snapshots validos para entrenamiento base.
- `false`: permite una corrida futura con snapshots parciales/invalidos para robustez y analisis de gaps.

Para auditar una corrida:

```powershell
& "C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\audit_bot_a_sub3_dataset.py --data-path "C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\<run_id>" --output-dir reports\bot_a_sub3_audits
```

## Politica de almacenamiento para Bot_A_sub1

### Recomendacion para Strategy Tester

La opcion recomendada es `COMMON_FILES` cuando quieres que los datasets queden fuera del sandbox variable de cada agente del tester y sean mas faciles de localizar entre ejecuciones. Usa `LOCAL_FILES` solo cuando quieras aislar resultados por agente o por entorno de prueba.

### Inputs que controlan la ruta

- `InpStorageMode`
  Valores: `MAGI_STORAGE_COMMON` o `MAGI_STORAGE_LOCAL`.

- `InpFallbackToLocalIfCommonFails`
  Solo aplica si `InpStorageMode = MAGI_STORAGE_COMMON`.
  Si es `true`, se intenta `LOCAL_FILES` cuando falla la apertura o preparacion en `COMMON_FILES`.
  Si es `false`, no hay fallback implicito.

- `InpStorageRootFolder`
  Carpeta raiz relativa dentro de `MQL5\\Files`.

- `InpStorageSubfolder`
  Subcarpetas adicionales relativas, por ejemplo `datasets\\bot_a_sub1`.

- `InpSplitPathBySymbol`
  Si es `true`, crea una carpeta por simbolo.

- `InpSplitPathByTimeframe`
  Si es `true`, crea una carpeta `anchor_<TF>__primary_<TF>`.

- `InpSplitPathByDate`
  Si es `true`, crea una jerarquia `YYYY\\MM\\DD`.

- `InpDatasetPrefix`
  Prefijo estable del nombre de archivo.

### Como se construye la ruta

La ruta relativa sigue esta convencion:

`<root_folder>\\<subfolder>\\[symbol]\\[anchor_<TF>__primary_<TF>]\\[YYYY\\MM\\DD]\\<prefix>__symbol_<SYMBOL>__anchor_<TF>__primary_<TF>__date_<YYYY-MM-DD>.<ext>`

Los segmentos entre corchetes solo aparecen si su input correspondiente esta activado.

### Ejemplos de rutas finales esperadas

Ejemplo recomendado con `COMMON_FILES`, `root=MAGI`, `subfolder=datasets\\bot_a_sub1`, `split_by_symbol=true`, `split_by_timeframe=true`, `split_by_date=true`, `symbol=EURUSD`, `anchor=M5`, `primary=H1`, fecha `2026-04-21`:

- CSV:
  `...\\Common\\Files\\MAGI\\datasets\\bot_a_sub1\\EURUSD\\anchor_M5__primary_H1\\2026\\04\\21\\magi_bot_a_sub1__symbol_EURUSD__anchor_M5__primary_H1__date_2026-04-21.csv`

- JSONL:
  `...\\Common\\Files\\MAGI\\datasets\\bot_a_sub1\\EURUSD\\anchor_M5__primary_H1\\2026\\04\\21\\magi_bot_a_sub1__symbol_EURUSD__anchor_M5__primary_H1__date_2026-04-21.jsonl`

Ejemplo con `LOCAL_FILES`, sin split por fecha:

- CSV:
  `...\\MQL5\\Files\\MAGI\\datasets\\bot_a_sub1\\EURUSD\\anchor_M5__primary_H1\\magi_bot_a_sub1__symbol_EURUSD__anchor_M5__primary_H1__date_2026-04-21.csv`

## Trazabilidad e instrumentacion

`Bot_A_sub1` y `MagiDatasetWriter` imprimen:

- politica de almacenamiento elegida,
- base path efectiva primaria,
- si hay o no fallback a local,
- ruta esperada inicial para CSV y JSONL,
- ruta final efectiva usada al crear o hacer append,
- errores exactos de apertura, creacion de carpeta, cabecera y escritura.

## Robustez aplicada a la persistencia

- La cabecera CSV se escribe solo si el archivo esta vacio.
- Se evita persistir dos veces la misma barra ancla dentro de la misma ejecucion.
- Antes de escribir, se valida `timestamp`, `symbol`, `anchor_timeframe`, `primary_timeframe` y `bar_timestamp`.
- Antes de escribir, se reconstruye la barra OHLC del timeframe primario para validar consistencia.
- Si falla `COMMON_FILES`, el fallback a `LOCAL_FILES` solo ocurre cuando `InpFallbackToLocalIfCommonFails=true`.

## Que revisar en tu instalacion de MT5

- Que `Bot_A_sub1` compile en MetaEditor.
- Que el tester tenga historial suficiente para el timeframe primario y para `EMA 200`.
- Que las carpetas bajo `MQL5\\Files` o `Common\\Files` sean escribibles.
- Que el log del Strategy Tester muestre la politica de almacenamiento y la ruta final efectiva.

## Validacion rapida de que Bot_A_sub1 escribio archivos

1. Ejecuta el EA en Strategy Tester con `InpWriteCsv=true` y/o `InpWriteJsonl=true`.
2. Revisa el log y busca `Ruta final CSV efectiva` o `Ruta final JSONL efectiva`.
3. Abre la carpeta indicada en ese log.
4. Confirma que:
   - existe el archivo,
   - el CSV tiene una sola cabecera,
   - las nuevas barras se agregan en append,
   - el JSONL tiene una linea por snapshot.

## Verificaciones pendientes fuera de este entorno

- Compilacion real en MetaEditor/MT5.
- Disponibilidad de suficiente historial para `EMA 200` y `RSI 14`.
- Ubicacion exacta de `LOCAL_FILES` y `COMMON_FILES` en tu instalacion concreta del tester.
- Validacion funcional de escritura, append y fallback dentro del Strategy Tester.
