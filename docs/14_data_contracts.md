# 14. Data Contracts

## Snapshot de Bot A

Ver `templates/bot_a_sample.json`.

Campos clave:

- identificacion del snapshot
- estado estructural del mercado
- niveles relevantes
- indicadores minimos
- precio y rango reciente
- estado de posicion abierta

## Votos de magos

Ver `templates/magi_votes_sample.json`.

Reglas:

- mismo contrato para los tres magos
- mismo catalogo de `context_tag`
- `reason` opcional, pero recomendable
- posibilidad de uno o multiples disparadores para el mismo snapshot

## Decision del CEO

Ver `templates/ceo_decision_sample.json`.

Reglas:

- contrato unificado por `case_type`
- `reason` obligatoria
- campos operativos nulos cuando no aplican

## Compatibilidad futura con ML

Los contratos no cambian cuando se introduzca ML. Solo cambia la forma interna de producir la salida propia de cada modulo, por ejemplo `decision`, `confidence`, `risk_flag`, `voto` o `score_oportunidad` segun aplique.

## Contrato de Gaspar

Gaspar usa un contrato separado para calidad de oportunidad. No predice direccion; recibe `proposed_direction` como propuesta externa o proxy estructural.

Ejemplo base: `gaspar_training_v1/contracts/gaspar_input_example.json`.

Contrato operativo para Bot A principal: `docs/18_gaspar_operational_contract.md`.

```json
{
  "module": "GASPAR",
  "role": "opportunity_quality",
  "symbol": "EURUSD",
  "timestamp": "...",
  "proposed_direction": "BUY|SELL|NEUTRAL",
  "higher_timeframe_confluence": {
    "h4_structure": "bullish|bearish|range",
    "d1_structure": "bullish|bearish|range",
    "directional_alignment": "aligned|contradictory|neutral"
  },
  "price_structure_position": {
    "distance_to_d1_support": 0.0,
    "distance_to_d1_resistance": 0.0,
    "position_in_d1_range": 0.0,
    "near_key_level": true
  },
  "timing_quality": {
    "active_session": "asia|london|new_york|overlap|inactive",
    "daily_atr_consumed_pct": 0.0,
    "available_range_to_next_level": 0.0,
    "h4_candle_pattern": "rejection|engulfing|inside|none"
  },
  "day_context": {
    "day_of_week": "monday|tuesday|wednesday|thursday|friday",
    "d1_volatility_vs_20d_avg": 0.0,
    "current_d1_range_vs_atr": 0.0
  },
  "target": {
    "voto": "GOOD|FAIR|POOR",
    "score_oportunidad": 0.0
  }
}
```

Salida esperada:

```json
{
  "module": "GASPAR",
  "role": "opportunity_quality",
  "voto": "GOOD|FAIR|POOR",
  "score_oportunidad": 0.0,
  "pillars": {
    "higher_timeframe_confluence": 0.0,
    "price_structure_position": 0.0,
    "timing_quality": 0.0,
    "day_context": 0.0
  },
  "reason": "..."
}
```

Durante entrenamiento, si no existe una direccion real externa, `proposed_direction` se genera como proxy heuristico usando solo estructura H4/D1: D1 bullish y H4 no bearish => `BUY`, D1 bearish y H4 no bullish => `SELL`, D1 range o conflicto fuerte H4/D1 => `NEUTRAL`.

Para `target_v4`, el pipeline deriva una feature discreta `daily_range_state` desde `current_d1_range_vs_atr`: `EARLY` si es menor a 0.60, `MID` entre 0.60 y 1.20, y `LATE` si es mayor a 1.20. Esta feature es derivada del contrato; no requiere que Bot A_sub2 la exporte.

Pendiente: cuando Gaspar pase de entrenamiento a operacion, Bot A principal debera incluir un bloque separado `gaspar_context` con los datos estructurales y temporales necesarios para Gaspar. Ese bloque no debe incluir confianza, probabilidades, features ni indicadores de Baltasar.

## Dataset operativo Bot_A_sub3

`Bot_A_sub3` recolecta el contrato operativo completo de `Bot A` desde Strategy Tester. La etapa cerrada usa una version simple y estable: dataset de `Bot_A_sub1` + `gaspar_context` del contrato operativo compartido.

Reglas:

- No define un contrato distinto al de `Bot A`.
- Usa `MagiBuildSnapshot(...)` como fuente unica del snapshot.
- Guarda JSONL completo con la misma serializacion que enviaria `Bot A` real.
- Guarda CSV plano para analisis tabular, entrenamiento y simulador Python.
- Genera un `run_id` unico por corrida y lo usa como carpeta de aislamiento.
- Usa `FILE_COMMON` y escribe bajo `Common Files`.
- No ejecuta trading, no decide y no modifica ordenes.
- Si una feature MTF no esta disponible, el snapshot debe marcarlo en `validation`, `alignment_status`, `alignment_warning` o `mtf_data_source_status`; no debe ocultarlo.
- Para datasets limpios de entrenamiento base puede correrse con `InpSkipInvalidSnapshots=true`.
- Para robustez y diagnostico debe correrse despues con `InpSkipInvalidSnapshots=false`.

Ruta esperada:

```text
Common Files/
  MAGI/
    datasets/
      bot_a_sub3/
        run_YYYY-MM-DD_HH-MM-SS_<tick>/
          <SYMBOL>/
            anchor_<TF>__primary_<TF>/
              YYYY/
                MM/
                  DD/
                    *.jsonl
                    *.csv
```

Auditoria de cierre:

```text
build=bot_a_sub3_simple_sub1_sub2_2026-04-28_v1
decision=APTO
score=100/100
jsonl_rows=18,612
csv_rows=18,612
duplicate_snapshot_id=0
mtf_ok=74,448/74,448
gaspar_context_present=18,612/18,612
```

Campos agregados para compatibilidad MAGI:

- `spread_pips`
- `active_session`
- `allowed_actions`
- `account.balance`
- `account.equity`
- `account.daily_drawdown_percent`
- `account.risk_percent_per_trade`
- `news`
- `operational_notes`
- `gaspar_context`

Campos planos en CSV para Gaspar:

- `gaspar_is_available`
- `gaspar_proposed_direction`
- `gaspar_proposed_direction_source`
- `gaspar_h4_structure`
- `gaspar_d1_structure`
- `gaspar_directional_alignment`
- `gaspar_h4_bar_timestamp`
- `gaspar_d1_bar_timestamp`
- `gaspar_h4_age_minutes`
- `gaspar_d1_age_minutes`
- `gaspar_distance_to_d1_support`
- `gaspar_distance_to_d1_resistance`
- `gaspar_position_in_d1_range`
- `gaspar_near_key_level`
- `gaspar_active_session`
- `gaspar_daily_atr_consumed_pct`
- `gaspar_available_range_to_next_level`
- `gaspar_h4_candle_pattern`
- `gaspar_day_of_week`
- `gaspar_d1_volatility_vs_20d_avg`
- `gaspar_current_d1_range_vs_atr`
- `gaspar_data_quality_flags`

Validacion minima para simulador Python y entrenamiento futuro:

- Cada linea JSONL debe parsear como JSON.
- Cada fila CSV debe tener `snapshot_id`, `symbol`, `anchor_bar_timestamp`, `current_price`, `mtf_data_source_status`, `validation_is_valid` y los campos `gaspar_*`.
- `snapshot_id` no debe duplicarse dentro de una corrida.
- Los archivos de distintas corridas deben vivir bajo carpetas `run_*` diferentes.
- `gaspar_context` no debe contener `ema`, `rsi`, `momentum`, confianza, probabilidades ni decision final.
- `features_json` del CSV debe parsear directamente como JSON.
- Las features M15/H1/H4/D1 deben tener `age_minutes` dentro de una vela cerrada del timeframe correspondiente.
- Cada feature MTF debe incluir `bars_available`, `oldest_bar_time`, `newest_bar_time` y `data_source_status` para distinguir falta de historico MT5 de error de seleccion temporal.

## Pendientes de contratos y labels

- Definir labels supervisados para Baltasar, Gaspar y CEO-MAGI.
- Incorporar outcomes reales desde Bot C cuando existan.
- Separar claramente labels futuros de features disponibles al momento del snapshot para evitar leakage.
- Documentar el mapeo entre snapshots de Bot A, decisiones CEO y cierres de operaciones.
