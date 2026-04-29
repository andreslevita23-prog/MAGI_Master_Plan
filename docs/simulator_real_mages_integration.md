# Integracion de magos reales al simulador MAGI v0.1

## Objetivo

Este documento diagnostica como conectar Melchor, Baltasar y Gaspar reales al simulador Python de MAGI v0.1 antes de ejecutar una simulacion final con magos reales sobre Bot A sub3.

No propone cambiar la arquitectura grande del simulador. La recomendacion es introducir adaptadores reales detras de la interfaz actual `evaluate(snapshot) -> MageVote`, manteniendo el pipeline existente:

```text
config -> loader -> validation -> timeline -> mage adapters -> CEO-MAGI -> execution -> metrics -> outputs
```

## Estado actual del simulador

### Ubicacion de magos mock/rule-based

El simulador actual instancia directamente implementaciones rule-based en `run_simulation.py`:

- `magi/melchor.py` -> `MelchorRuleBased`
- `magi/baltasar.py` -> `BaltasarRuleBased`
- `magi/gaspar.py` -> `GasparRuleBased`
- `magi/ceo_magi.py` -> `CeoMagiRuleBased`

Punto de acoplamiento actual:

```python
melchor = MelchorRuleBased(config.melchor)
baltasar = BaltasarRuleBased(config.baltasar)
gaspar = GasparRuleBased(config.gaspar)
ceo = CeoMagiRuleBased(config.ceo_magi)
```

Cada mago expone:

```python
evaluate(snapshot: Snapshot) -> MageVote
```

CEO-MAGI espera tres votos ya normalizados:

```python
ceo.decide(snapshot, melchor_vote, baltasar_vote, gaspar_vote) -> CeoDecision
```

### Contrato interno `MageVote`

Archivo: `magi/contracts.py`

```json
{
  "schema_version": "mage_vote_v1",
  "snapshot_id": "string",
  "agent": "MELCHOR|BALTASAR|GASPAR",
  "agent_version": "string",
  "vote": "APPROVE|WARN|BLOCK|null",
  "direction": "BUY|SELL|NEUTRAL|null",
  "quality": "GOOD|FAIR|POOR|null",
  "confidence": 0.0,
  "risk_flag": "LOW|MEDIUM|HIGH|CRITICAL",
  "context_tag": "string",
  "features_used": [],
  "reason": "string"
}
```

Especializacion actual:

- Melchor rule-based usa `vote`: `APPROVE`, `WARN`, `BLOCK`.
- Baltasar rule-based usa `direction`: `BUY`, `SELL`, `NEUTRAL`.
- Gaspar rule-based usa `quality`: `GOOD`, `FAIR`, `POOR`.

### Contrato esperado por CEO-MAGI

Archivo: `magi/ceo_magi.py`

CEO-MAGI actual toma decisiones con estas reglas:

- `NO_TRADE` si `melchor.vote == BLOCK`.
- `NO_TRADE` si `baltasar.direction == NEUTRAL`.
- `NO_TRADE` si `gaspar.quality == POOR`.
- `SKIP_WARN` si `melchor.vote == WARN` y `strict_warn == true`.
- `OPEN_LONG` si Melchor aprueba o advierte, Baltasar dice `BUY` y Gaspar es `GOOD` o `FAIR`.
- `OPEN_SHORT` si Melchor aprueba o advierte, Baltasar dice `SELL` y Gaspar es `GOOD` o `FAIR`.

Implicacion: cualquier mago real debe ser adaptado al contrato `MageVote` antes de llegar a CEO-MAGI. No conviene hacer que CEO-MAGI consuma formatos nativos heterogeneos.

## Modulos reales encontrados

## Melchor real

### Ubicacion

Implementacion principal:

- `servidor-prosperity/services/melchor-risk-engine.js`

Conector:

- `servidor-prosperity/src/server/services/connectors/adapters/melchor.js`

Documentacion:

- `docs/07_melchor.md`
- `docs/15_risk_rules.md`
- `docs/reports/melchor_v1_executive_report.md`

Configuracion:

- `config/melchor_rules.json`

Pruebas existentes:

- `servidor-prosperity/scripts/test-melchor-risk-engine.mjs`

### Naturaleza del modulo

Melchor real v1 es deterministico, no ML. Evalua reglas de riesgo, sesiones, spread, drawdown, noticias, posiciones abiertas, RR y SL.

### Entrada nativa

El motor real espera:

```js
evaluateMelchorRisk(snapshot, {
  candidateTrade,
  accountContext,
  now
})
```

Campos relevantes del snapshot normalizado:

```json
{
  "snapshot_id": "string",
  "symbol": "EURUSD",
  "timestamp": "ISO",
  "market": {
    "price": 1.1,
    "session": "london|new_york|overlap|asia|inactive",
    "spread_pips": 1.0,
    "allowed_actions": ["open", "hold"]
  },
  "position": {
    "has_open_position": false,
    "open_positions_count": 0,
    "profit_progress_to_tp": 0.0
  },
  "validation": {
    "is_valid": true,
    "issues": []
  },
  "account": {
    "daily_drawdown_percent": 0.0,
    "consecutive_losses": 0,
    "risk_percent_per_trade": 0.1
  },
  "news": []
}
```

`candidateTrade` es obligatorio cuando se evalua una apertura:

```json
{
  "action": "open",
  "entry_price": 1.1,
  "stop_loss": 1.099,
  "take_profit": 1.102,
  "risk_percent": 0.1,
  "spread_pips": 1.0
}
```

### Salida nativa

```json
{
  "module": "MELCHOR",
  "version": "v1.0",
  "vote": "ALLOW|BLOCK|PROTECT|CLOSE|NOTIFY",
  "risk_block_recommendation": false,
  "confidence": 1.0,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "reason": "string",
  "rules_triggered": [],
  "recommended_action": {
    "action": "hold",
    "details": {}
  },
  "timestamp": "ISO",
  "symbol": "EURUSD",
  "snapshot_id": "string"
}
```

### Mapeo requerido a `MageVote`

| Melchor real | `MageVote.vote` | `risk_flag` | Nota |
| --- | --- | --- | --- |
| `ALLOW` | `APPROVE` | `risk_level` | Compatible con apertura. |
| `NOTIFY` | `WARN` | `MEDIUM` o `risk_level` | No bloquea por si solo. |
| `BLOCK` | `BLOCK` | `risk_level` | Bloqueo recomendado. |
| `CLOSE` | `BLOCK` o futura accion gestion | `CRITICAL` | En v0.3 puede bloquear nuevas entradas. |
| `PROTECT` | `WARN` o futura accion gestion | `MEDIUM` | Relevante cuando haya posicion abierta real. |

Riesgo: Melchor real no deberia evaluar primero sin `candidateTrade` cuando la pregunta es abrir. En el simulador actual Melchor vota antes de que CEO-MAGI construya una operacion candidata. Para conectar Melchor correctamente hay dos opciones:

1. `v0.3` conservadora: construir un `candidateTrade` provisional antes de consultar Melchor usando la misma config de ejecucion virtual: entrada `current_price`, SL fijo, TP por R.
2. `v0.3b` mas limpia: separar CEO-MAGI en dos pasos: Baltasar/Gaspar proponen setup, se construye candidate trade, Melchor evalua riesgo, CEO-MAGI decide.

La opcion 1 mantiene arquitectura actual con menor cambio.

## Baltasar real

### Ubicacion

Laboratorio:

- `baltasar_training_v1/`

Documentacion:

- `docs/08_baltasar.md`
- `baltasar_training_v1/README.md`
- `baltasar_training_v1/artifacts/reports/baltasar_v12_training_report.md`
- `baltasar_training_v1/artifacts/reports/baltasar_v12_consolidation.md`

Modelos serializados:

- `baltasar_training_v1/artifacts/models/*random_forest.joblib`
- `baltasar_training_v1/artifacts/models/*baseline_tree.joblib`
- modelos candidatos como `candidate_target_compact_features__random_forest.joblib`

Pipeline de features/modelo:

- `baltasar_training_v1/src/features/variants.py`
- `baltasar_training_v1/src/features/engineering.py`
- `baltasar_training_v1/src/models/training.py`
- `baltasar_training_v1/src/models/registry.py`

Configuracion:

- `baltasar_training_v1/config/experiment.yaml`

### Naturaleza del modulo

Baltasar v1.2 es un clasificador multiclase de direccion:

- `BUY`
- `SELL`
- `NEUTRAL`

Baseline oficial documentado:

- target: `h12_t03`
- feature variant: `compact`
- modelo oficial: `random_forest`
- referencia explicable: `baseline_tree`

### Entrada esperada por el pipeline

El entrenamiento oficial usa columnas de Bot A sub1:

```text
snapshot_id
symbol
anchor_bar_timestamp
current_price
anchor_open
anchor_high
anchor_low
anchor_close
market_structure
structure_direction
ema_20
ema_50
ema_200
rsi_14
momentum
recent_range
validation_is_valid
has_open_position
```

La variante `compact` deriva:

```text
candle_body_ratio
candle_range_ratio
upper_wick_ratio
lower_wick_ratio
price_vs_ema20
price_vs_ema50
price_vs_ema200
ema_gap_20_50
ema_gap_50_200
ema_gap_20_200
normalized_recent_range
```

Tambien conserva categorias:

```text
market_structure
structure_direction
momentum
has_open_position
```

### Salida esperada para el simulador

El modelo produce una clase: `BUY`, `SELL` o `NEUTRAL`. Para `MageVote`:

```json
{
  "agent": "BALTASAR",
  "direction": "BUY|SELL|NEUTRAL",
  "confidence": 0.0,
  "features_used": ["compact_feature_set"],
  "reason": "Baltasar v1.2 random_forest prediction"
}
```

Si el modelo soporta `predict_proba`, la confianza deberia ser `max(probabilities)`. Si no, usar `1.0` para arbol explicable o una confianza neutral documentada.

### Estado de inferencia

El laboratorio tiene entrenamiento y modelos `.joblib`, pero no se encontro un wrapper operativo de inferencia listo para el simulador. Falta crear un adaptador que:

1. convierta `Snapshot` a una fila compatible con el schema de entrenamiento;
2. aplique `build_compact_feature_set` o reproduzca exactamente esas transformaciones;
3. cargue el `.joblib` oficial;
4. ejecute `predict` y opcionalmente `predict_proba`;
5. devuelva `MageVote`.

## Gaspar real

### Ubicacion

Laboratorio:

- `gaspar_training_v1/`

Documentacion:

- `docs/09_gaspar.md`
- `docs/18_gaspar_operational_contract.md`
- `gaspar_training_v1/README.md`
- `gaspar_training_v1/reports/gaspar_training_report.md`
- `gaspar_training_v1/reports/gaspar_diagnostics_report.md`

Contrato ejemplo:

- `gaspar_training_v1/contracts/gaspar_input_example.json`

Modelo serializado:

- `gaspar_training_v1/artifacts/models/gaspar_baseline.joblib`
- variantes posibles: `gaspar_v2_baseline.joblib`, `gaspar_v4_baseline.joblib` si existen tras entrenamientos posteriores.

Pipeline:

- `gaspar_training_v1/src/gaspar/data.py`
- `gaspar_training_v1/src/gaspar/features.py`
- `gaspar_training_v1/src/gaspar/schemas.py`
- `gaspar_training_v1/src/gaspar/training.py`
- `gaspar_training_v1/src/gaspar/targeting.py`

### Naturaleza del modulo

Gaspar evalua calidad de oportunidad, no direccion. Su salida operativa es:

```json
{
  "module": "GASPAR",
  "role": "opportunity_quality",
  "voto": "GOOD|FAIR|POOR",
  "score_oportunidad": 0.0,
  "pillars": {},
  "reason": "string"
}
```

### Entrada esperada

Gaspar necesita el bloque aislado `gaspar_context`:

```json
{
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
  }
}
```

El pipeline real normaliza campos a columnas:

```text
proposed_direction
h4_structure
d1_structure
directional_alignment
distance_to_d1_support
distance_to_d1_resistance
position_in_d1_range
near_key_level
active_session
daily_atr_consumed_pct
available_range_to_next_level
h4_candle_pattern
day_of_week
d1_volatility_vs_20d_avg
current_d1_range_vs_atr_capped
daily_range_state
```

### Salida esperada para el simulador

Mapeo a `MageVote`:

```json
{
  "agent": "GASPAR",
  "quality": "GOOD|FAIR|POOR",
  "confidence": 0.0,
  "context_tag": "opportunity_quality",
  "features_used": ["gaspar_context"],
  "reason": "string"
}
```

Si el modelo real tiene `predict_proba`, usar la maxima probabilidad como `confidence`; si no, registrar `score_oportunidad` si se usa la heuristica de `schemas.build_gaspar_output`.

## Compatibilidad con Bot A sub3

### Dataset localizado

Ruta encontrada:

```text
C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00_659700906
```

Auditoria existente generada:

- `reports/bot_a_sub3_audits/20260428T215651Z_bot_a_sub3_audit.json`
- `reports/bot_a_sub3_audits/20260428T215651Z_bot_a_sub3_audit.md`

Resumen auditado:

- CSV: 86 archivos, 18,612 filas.
- JSONL: 86 archivos, 18,612 filas.
- Parse errors: 0.
- Duplicados: 0.
- OHLC invalido: 0.
- Spreads negativos: 0.
- RSI fuera de rango: 0.
- MTF OK: 74,448/74,448.
- Decision: `APTO`, score `100`.

### Campos reales observados en JSONL Bot A sub3

Nivel raiz:

```text
schema_version
snapshot_id
symbol
source_mode
trigger_type
timestamp
anchor_bar_timestamp
bar_timestamp
anchor_timeframe
primary_timeframe
anchor_open
anchor_high
anchor_low
anchor_close
market_structure
structure_direction
support_levels
resistance_levels
ema_20
ema_50
ema_200
rsi_14
momentum
current_price
recent_range
spread_pips
active_session
mtf_alignment_status
mtf_alignment_warnings
mtf_data_source_status
allowed_actions
account
news
position
gaspar_context
features
validation
```

CSV plano incluye columnas equivalentes y campos `gaspar_*`, mas `features_json`.

### Compatibilidad con Melchor real

Compatible parcialmente.

Bot A sub3 trae:

- `snapshot_id`
- `symbol`
- `timestamp`
- `current_price`
- `spread_pips`
- `active_session`
- `allowed_actions`
- `account.balance`
- `account.equity`
- `account.daily_drawdown_percent`
- `account.risk_percent_per_trade`
- `news`
- `position.has_open_position`
- `position.open_positions_count`
- `validation.is_valid`

Faltan o requieren transformacion:

- `market.price` debe mapearse desde `current_price`.
- `market.session` debe mapearse desde `active_session`.
- `market.spread_pips` debe mapearse desde `spread_pips`.
- `market.allowed_actions` debe mapearse desde `allowed_actions`.
- `candidateTrade` no existe en Bot A sub3; debe construirse en el simulador antes de Melchor real.
- `risk_percent_per_trade` en Bot A sub3 aparece como `0.0` o pendiente; Melchor real puede permitir/bloquear distinto segun config.
- `consecutive_losses` no aparece en account; debe default a 0 o derivarse del portfolio simulado.
- Noticias existen como lista, pero el dataset puede no traer calendario real completo.

### Compatibilidad con Baltasar real

Alta a nivel de datos, media a nivel de integracion.

Bot A sub3 trae los campos de Bot A sub1 que Baltasar v1.2 espera:

- OHLC anchor.
- `current_price`.
- `market_structure`.
- `structure_direction`.
- `ema_20`, `ema_50`, `ema_200`.
- `rsi_14`.
- `momentum`.
- `recent_range`.
- `validation.is_valid` o `validation_is_valid` en CSV.
- `has_open_position` en `position` o CSV plano.

Gaps:

- El simulador `Snapshot.features` espera dict, pero Bot A sub3 JSONL trae `features` como lista MTF. Esto no rompe a Baltasar si el adaptador usa campos raiz, pero el reporte actual del simulador marca `missing_features` por esa diferencia.
- El modelo oficial de Baltasar esta en laboratorio de entrenamiento y no tiene wrapper operativo versionado para inferencia dentro de `magi/`.
- Hay que fijar exactamente cual `.joblib` es el oficial para inferencia. La documentacion dice `Baltasar v1.2 random_forest`, pero existen multiples archivos de modelos.
- El adaptador debe reproducir la misma transformacion `compact` usada en entrenamiento, incluyendo columnas categoriales y orden/shape esperados por el pipeline serializado.

### Compatibilidad con Gaspar real

Alta a nivel de contrato de datos.

Bot A sub3 trae `gaspar_context` anidado con:

- `schema_version`
- `module`
- `role`
- `symbol`
- `timestamp`
- `proposed_direction`
- `proposed_direction_source`
- `higher_timeframe_confluence`
- `price_structure_position`
- `timing_quality`
- `day_context`
- `data_quality_flags`

Esto coincide con `docs/18_gaspar_operational_contract.md`.

Gaps:

- `proposed_direction` actual viene de `fallback_h4_d1_shadow`, no de Baltasar real. Para simulacion con magos reales, Gaspar deberia recibir la direccion propuesta por Baltasar, no el fallback de Bot A.
- Si se mantiene fallback para shadow mode, debe quedar registrado como fallback, no como decision primaria.
- El modelo `gaspar_baseline.joblib` requiere wrapper de inferencia que convierta `gaspar_context` a columnas del pipeline.
- Debe decidirse target operativo: `v2` oficial o `v4` challenger. La documentacion favorece `v2` como baseline oficial.

## Gaps detectados

### Gaps de arquitectura

1. `run_simulation.py` instancia clases concretas rule-based. Falta una fabrica/adaptador configurable por modo:
   - `rule_based`
   - `real`
   - `shadow`

2. No existe interfaz base explicita tipo:

```python
class MageAdapter:
    def evaluate(self, snapshot: Snapshot, context: SimulationContext) -> MageVote:
        ...
```

3. Melchor real necesita `candidateTrade`, pero la secuencia actual consulta Melchor antes de construir una propuesta de trade.

4. Gaspar real deberia consumir `proposed_direction` de Baltasar real. La secuencia actual evalua los tres magos de forma independiente sobre el mismo snapshot.

### Gaps de contratos

1. Melchor real usa `ALLOW/BLOCK/PROTECT/CLOSE/NOTIFY`; simulador usa `APPROVE/BLOCK/WARN`.
2. Gaspar real usa `voto`; simulador usa `quality`.
3. Baltasar real produce clase `BUY/SELL/NEUTRAL`; simulador ya es compatible en `direction`.
4. Bot A sub3 JSONL trae `features` como lista MTF, no como dict. El simulador deberia aceptar `features` list o mapearla por timeframe.
5. `validation_is_valid` en CSV y `validation.is_valid` en JSONL deben normalizarse igual.

### Gaps de inferencia

1. Melchor real esta en JavaScript/Node.js, mientras el simulador es Python. Hay que elegir:
   - portar reglas a Python;
   - invocar Node.js por subprocess;
   - exponerlo como servicio interno;
   - crear un script CLI estable de Melchor.

2. Baltasar tiene modelos `.joblib`, pero falta wrapper operativo de inferencia.
3. Gaspar tiene modelo `.joblib`, pero falta wrapper operativo de inferencia.
4. No hay manifiesto unico que declare "modelo oficial activo" para Baltasar/Gaspar.

### Gaps de datos

1. `candidateTrade` no existe antes de Melchor real.
2. `risk_percent_per_trade` puede venir en 0.0 o como pendiente operativo.
3. `consecutive_losses` no existe en Bot A sub3.
4. Noticias historicas pueden estar vacias o incompletas.
5. Gaspar necesita `proposed_direction` de Baltasar real para modo real completo.

## Transformaciones requeridas por snapshot

### Snapshot -> Melchor real

Crear `MelchorRealAdapter` que construya:

```json
{
  "snapshot_id": "...",
  "symbol": "...",
  "timestamp": "...",
  "market": {
    "price": "current_price",
    "session": "active_session",
    "spread_pips": "spread_pips",
    "allowed_actions": "allowed_actions"
  },
  "position": {
    "has_open_position": "position.has_open_position",
    "open_positions_count": "position.open_positions_count"
  },
  "validation": "validation",
  "account": "account",
  "news": "news"
}
```

Y un `candidateTrade` provisional:

```json
{
  "action": "open",
  "entry_price": "current_price",
  "stop_loss": "derived from execution.sl_pips",
  "take_profit": "derived from execution.tp_rr",
  "risk_percent": "account.risk_percent_per_trade or config default",
  "spread_pips": "spread_pips"
}
```

Para construir SL/TP se necesita direccion. Por eso Melchor real debe ir despues de Baltasar y antes de CEO final, o recibir dos candidatos sombra (`BUY` y `SELL`) si se conserva la secuencia actual.

### Snapshot -> Baltasar real

Crear `BaltasarRealAdapter` que construya una fila:

```text
snapshot_id
symbol
anchor_bar_timestamp
current_price
anchor_open
anchor_high
anchor_low
anchor_close
market_structure
structure_direction
ema_20
ema_50
ema_200
rsi_14
momentum
recent_range
validation_is_valid
has_open_position
```

Luego aplicar exactamente la transformacion compacta de `baltasar_training_v1/src/features/variants.py`.

Salida:

```text
direction = model.predict(row)[0]
confidence = max(model.predict_proba(row)[0]) si existe
```

### Snapshot + Baltasar direction -> Gaspar real

Crear `GasparRealAdapter` que:

1. lea `snapshot.gaspar_context`;
2. reemplace `proposed_direction` con `baltasar.direction` en modo real;
3. recalcule `directional_alignment` si cambia la direccion propuesta;
4. aplaste el contexto a columnas usando las mismas reglas de `gaspar_training_v1/src/gaspar/data.py`;
5. aplique `build_feature_frame(..., target_version='v2')`;
6. ejecute modelo real o heuristica oficial;
7. devuelva `MageVote.quality`.

## Riesgos de leakage

1. Baltasar no debe recibir `forward_return`, `future_price`, outcomes del simulador, `trades`, `pnl_r`, MFE, MAE ni labels.
2. Gaspar no debe recibir EMAs, RSI, momentum, probabilidades, confianza ni features internas de Baltasar.
3. `proposed_direction` puede venir de Baltasar, pero solo como clase final `BUY/SELL/NEUTRAL`; no deben pasarle probabilidades ni evidencia tecnica.
4. Melchor puede recibir candidate trade derivado del snapshot actual y config, pero no resultado futuro.
5. Si se normalizan features para modelos, la normalizacion debe venir del pipeline entrenado, no recalcularse con todo el dataset de backtest.
6. Cualquier target heuristico de entrenamiento debe quedar fuera del modo inferencia.

## Que ya es compatible

- Bot A sub3 contiene datos suficientes para Baltasar v1.2.
- Bot A sub3 contiene `gaspar_context` compatible con el contrato operativo.
- Melchor real puede evaluar riesgo con transformacion de snapshot y candidate trade.
- El contrato interno `MageVote` es suficientemente general para envolver los tres formatos reales.
- CEO-MAGI actual puede seguir funcionando si recibe `MageVote` normalizado.

## Que falta adaptar

- Fabrica de magos por configuracion.
- Adaptador real de Melchor.
- Adaptador real de Baltasar.
- Adaptador real de Gaspar.
- Normalizador de Bot A sub3 para aceptar `features` como lista MTF.
- Seleccion explicita de modelos oficiales `.joblib`.
- Secuencia de decision en dos pasos para que:
  1. Baltasar proponga direccion.
  2. Gaspar evalue calidad de esa direccion.
  3. Se construya candidate trade.
  4. Melchor evalua riesgo.
  5. CEO-MAGI decide.

## Mago que puede conectarse primero

Recomendacion: conectar Melchor real primero en `v0.3`.

Motivos:

- Es deterministico y auditable.
- Ya existe implementacion real completa.
- No depende de modelos `.joblib`.
- Sus gaps son de adaptacion de contrato, no de ML.
- Permite validar gobierno de riesgo antes de introducir predictores.

Segundo: Baltasar real en `v0.4`.

Motivos:

- Bot A sub3 trae casi todos los campos necesarios.
- Su salida encaja directo con `MageVote.direction`.
- El principal trabajo es wrapper de inferencia y seleccion de modelo oficial.

Tercero: Gaspar real en `v0.5`.

Motivos:

- Aunque Bot A sub3 trae `gaspar_context`, Gaspar real debe usar la direccion de Baltasar en modo real.
- Conviene conectarlo despues de que Baltasar real ya produzca `BUY/SELL/NEUTRAL`.

## Plan de integracion

### v0.3 - Conectar Melchor real

1. Crear `magi/adapters/` sin tocar la logica de negocio existente.
2. Crear interfaz comun:

```python
class MageAdapter:
    def evaluate(self, snapshot, context) -> MageVote:
        ...
```

3. Mover rule-based actual a adaptadores o mantener wrappers compatibles.
4. Crear `MelchorRealAdapter`.
5. Elegir transporte:
   - preferido corto plazo: subprocess Node.js con script CLI estable;
   - alternativa futura: portar reglas a Python;
   - alternativa operativa: servicio HTTP local.
6. Implementar mapper:
   - Bot A sub3 snapshot -> Melchor normalized snapshot.
   - decision candidate -> `candidateTrade`.
   - Melchor output -> `MageVote`.
7. Agregar modo `melchor.mode = real|rule_based|shadow`.
8. Ejecutar pruebas unitarias con fixtures controlados.
9. Comparar Melchor real vs rule-based en modo shadow, sin cambiar aun decisiones finales.

### v0.4 - Conectar Baltasar real

1. Definir modelo oficial activo:
   - `baltasar_training_v1/artifacts/models/<official_v12_random_forest>.joblib`.
2. Crear `BaltasarRealAdapter`.
3. Reusar o copiar de forma controlada las transformaciones compactas.
4. Crear funcion `snapshot_to_baltasar_row(snapshot)`.
5. Garantizar que columnas y tipos coinciden con entrenamiento.
6. Convertir salida a `MageVote.direction`.
7. Registrar `agent_version`, modelo, path y feature variant en outputs.
8. Correr pruebas de inferencia con 3 snapshots sinteticos.
9. Correr shadow comparison contra `BaltasarRuleBased`.

### v0.5 - Conectar Gaspar real

1. Definir baseline operativo: `target_version = v2`.
2. Crear `GasparRealAdapter`.
3. Crear `snapshot_to_gaspar_row(snapshot, proposed_direction)`.
4. Reemplazar `gaspar_context.proposed_direction` por salida de Baltasar real en modo real.
5. Recalcular `directional_alignment`.
6. Verificar campos prohibidos dentro de `gaspar_context`.
7. Ejecutar modelo `.joblib` o heuristica oficial de salida.
8. Convertir `voto` a `MageVote.quality`.
9. Correr shadow comparison contra `GasparRuleBased`.

### v0.6 - Simulacion real completa

1. Activar:

```text
melchor.mode = real
baltasar.mode = real
gaspar.mode = real
```

2. Correr primero sobre muestra pequeña de Bot A sub3.
3. Validar:
   - conteos de votos;
   - distribucion de clases;
   - decisiones CEO;
   - trades abiertos;
   - errores por snapshot;
   - latencia si se usa subprocess Node.js.
4. Correr sobre los 18,612 snapshots de Bot A sub3.
5. Comparar contra baseline rule-based con mismo motor de ejecucion.
6. Documentar resultados y no optimizar parametros en esta fase.

## Cambios minimos recomendados antes de integrar

1. Ajustar loader para aceptar `features` como lista MTF y no marcar `missing_features` si la lista existe y no esta vacia.
2. Agregar `magi/adapters/` con wrappers, no reemplazar clases actuales.
3. Agregar `mode` por mago en config.
4. Introducir un `SimulationContext` con:
   - portfolio state;
   - execution config;
   - proposed_direction;
   - candidate_trade;
   - previous votes.
5. Mantener `MageVote` como frontera estable hacia CEO-MAGI.

## Decision recomendada

No correr una simulacion "real" completa todavia.

Primero implementar v0.3 con Melchor real en modo shadow. Despues conectar Baltasar real y hacer que Gaspar consuma su direccion. Solo entonces tiene sentido correr una simulacion completa con los tres magos reales.
