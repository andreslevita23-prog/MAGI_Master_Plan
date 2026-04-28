# 20. Python Simulator Plan

## Objetivo

El simulador Python debe convertir los snapshots de `Bot_A_sub3` en un entorno reproducible para:

- evaluar entradas hipoteticas sin ejecutar trading real;
- generar labels futuros para Baltasar, Gaspar y CEO-MAGI;
- calcular outcomes como TP, SL, MFE, MAE y retorno;
- preparar datasets de entrenamiento sin introducir leakage.

El simulador no decide por MAGI. Solo reconstruye el timeline y evalua escenarios definidos por reglas o experimentos.

## Inputs esperados

Fuente primaria:

- JSONL completo de `Bot_A_sub3`.

Fuente secundaria:

- CSV plano de `Bot_A_sub3` para analisis tabular rapido.

Campos minimos:

- `snapshot_id`
- `symbol`
- `timestamp`
- `anchor_bar_timestamp`
- `bar_timestamp`
- `anchor_open`
- `anchor_high`
- `anchor_low`
- `anchor_close`
- `current_price`
- `spread_pips`
- `features`
- `gaspar_context`
- `validation`
- `mtf_data_source_status`
- `mtf_alignment_status`

El CSV debe tener `features_json` parseable con `json.loads`.

## Carga de snapshots

Proceso recomendado:

1. Recorrer todos los `.jsonl` bajo un `run_*`.
2. Parsear linea por linea.
3. Validar que `snapshot_id` no se repita.
4. Convertir timestamps a `datetime` timezone-aware o a UTC normalizado.
5. Ordenar por `symbol`, `anchor_bar_timestamp`, `snapshot_id`.
6. Guardar una tabla normalizada de snapshots.

Ejemplo inicial:

```python
from pathlib import Path
import json

def load_snapshots(run_path: str):
    records = []
    for path in sorted(Path(run_path).rglob("*.jsonl")):
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                record["_source_file"] = str(path)
                record["_line_number"] = line_number
                records.append(record)
    return records
```

## Reconstruccion del timeline

El timeline debe basarse en `anchor_bar_timestamp`, no en el orden fisico de archivos.

Reglas:

- ordenar por `symbol` y `anchor_bar_timestamp`;
- verificar monotonia creciente por simbolo;
- detectar huecos mayores al timeframe ancla;
- registrar gaps, pero no inventar barras;
- no usar datos posteriores al snapshot para construir features.

## Filtrado de snapshots validos

Para entrenamiento base:

- `validation.is_valid == true`;
- `mtf_data_source_status == "OK"`;
- todas las features requeridas tienen `alignment_status == "ok"`;
- `spread_pips >= 0`;
- OHLC valido;
- `gaspar_context.is_available == true` cuando se entrena Gaspar.

Para diagnostico:

- conservar snapshots invalidos;
- segmentar por `validation.issues`;
- medir frecuencia de `INSUFFICIENT_HISTORY`, `ALIGNMENT_ERROR` y gaps temporales.

## Labels futuros

Los labels se generan mirando barras posteriores al `anchor_bar_timestamp`. Nunca deben incorporarse como features de entrada.

Labels iniciales sugeridos:

- `future_return_h1`
- `future_return_h4`
- `hit_tp_before_sl`
- `bars_to_tp`
- `bars_to_sl`
- `max_favorable_excursion`
- `max_adverse_excursion`
- `outcome`: `TP`, `SL`, `TIMEOUT`, `NO_TRADE`

Horizontes sugeridos:

- 12 velas M5;
- 48 velas M5;
- 96 velas M5;
- hasta cierre de sesion.

## Simulacion de entradas y salidas

El simulador debe aceptar escenarios hipoteticos:

- direccion: `BUY`, `SELL`, `NEUTRAL`;
- precio de entrada: close del anchor, ask/bid simulado o precio configurable;
- spread/slippage;
- SL en pips, ATR, soporte/resistencia o estructura;
- TP fijo, ratio R, nivel tecnico o trailing;
- timeout por numero de barras.

Para cada snapshot candidato:

1. definir entrada hipotetica;
2. recorrer barras futuras;
3. calcular MFE y MAE;
4. detectar si TP o SL ocurre primero;
5. registrar outcome y tiempo hasta outcome.

## MFE, MAE, TP, SL y outcome

Definiciones:

- MFE: maximo movimiento favorable desde entrada antes del cierre del horizonte.
- MAE: maximo movimiento adverso desde entrada antes del cierre del horizonte.
- TP: primer toque del nivel de take-profit.
- SL: primer toque del stop-loss.
- outcome:
  - `TP` si TP ocurre antes de SL;
  - `SL` si SL ocurre antes de TP;
  - `AMBIGUOUS` si ambos niveles se tocan dentro de la misma vela y no hay granularidad suficiente;
  - `TIMEOUT` si no toca ninguno;
  - `NO_TRADE` si el escenario no habilita entrada.

Cuando TP y SL ocurren en la misma vela, no asumir un orden falso. Marcar `AMBIGUOUS` o usar datos de menor timeframe si existen.

## Datasets por modulo

Baltasar:

- features de direccion, momentum, EMA, RSI, estructura, rango reciente;
- labels de direccion futura, retorno y TP/SL por direccion hipotetica.

Gaspar:

- usar solo `gaspar_context`;
- excluir EMA, RSI, momentum, confidence y probability;
- labels de calidad de oportunidad: `GOOD`, `FAIR`, `POOR`, derivados de outcome, MFE/MAE, rango disponible y timing.

CEO-MAGI:

- combinar snapshot completo, voto hipotetico de magos y outcomes;
- labels de decision: entrar, no entrar, ajustar SL/TP, mantener o cerrar;
- separar con cuidado datos observables al momento de decision vs outcomes futuros.

## Estructura recomendada

```text
python_simulator/
  README.md
  pyproject.toml
  configs/
    default.yaml
    scenarios/
      h1_fixed_rr.yaml
      h4_structure.yaml
  src/
    magi_sim/
      __init__.py
      io.py
      schema.py
      timeline.py
      labels.py
      execution.py
      metrics.py
      datasets.py
      validation.py
  scripts/
    audit_run.py
    build_timeline.py
    simulate_scenarios.py
    build_training_sets.py
  tests/
    test_io.py
    test_timeline.py
    test_labels.py
    test_execution.py
  outputs/
    timelines/
    simulations/
    training_sets/
    reports/
```

## Scripts iniciales sugeridos

- `audit_run.py`: valida estructura, duplicados y campos criticos.
- `build_timeline.py`: convierte JSONL en parquet/csv ordenado.
- `simulate_scenarios.py`: ejecuta escenarios TP/SL/MFE/MAE.
- `build_training_sets.py`: genera datasets por modulo.
- `report_quality.py`: resume cobertura, gaps, balance y leakage checks.

## Criterios de validacion

- 0 JSONL corruptos.
- 0 duplicados de `snapshot_id`.
- timestamps monotonicamente ordenables por simbolo.
- OHLC valido.
- spreads no negativos.
- RSI dentro de 0..100.
- `features_json` parseable si se usa CSV.
- labels generados solo con datos posteriores.
- separacion clara entre features y targets.
- reporte de balance de clases por modulo.
- reporte de outliers y gaps temporales.

## Riesgos

- Data leakage por usar outcomes futuros como features.
- Ambiguedad intrabar cuando TP y SL se tocan en la misma vela.
- Sesgo por filtrar solo snapshots validos y excluir gaps de mercado.
- Desbalance fuerte de labels `TP`/`SL`/`TIMEOUT`.
- Diferencias entre precios bid/ask reales y simulados.
- Falta de outcomes reales de Bot C para validar decisiones finales.

## Pendientes

- Corrida `Bot_A_sub3` con `InpSkipInvalidSnapshots=false`.
- Dataset de snapshots parciales/invalidos.
- Definicion formal de labels de Baltasar.
- Definicion formal de labels de Gaspar.
- Definicion formal de labels CEO-MAGI.
- Integracion con Bot C para outcomes reales.
- Pruebas de simulador contra casos manuales conocidos.
