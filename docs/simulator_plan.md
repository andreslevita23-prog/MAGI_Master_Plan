# Plan tecnico del simulador/backtester Python de MAGI

## 1. Objetivo del simulador

El simulador Python de MAGI debe reconstruir un recorrido historico reproducible usando datasets generados por Bot A, ejecutar decisiones hipoteticas de Melchor, Baltasar, Gaspar y CEO-MAGI, simular operaciones bajo reglas controladas y producir evidencia auditable para evaluar, comparar y reentrenar los magos.

Debe probar:

- si el flujo multiagente produce decisiones consistentes sobre datos historicos;
- como se comportan las reglas de aprobacion, bloqueo y desacuerdo entre magos;
- que resultados habrian tenido las operaciones bajo reglas de entrada, SL, TP, costos y horarios definidos;
- que variables disponibles al momento del snapshot explican mejor los outcomes;
- que combinaciones de votos, sesiones, simbolos y contextos aportan o destruyen valor;
- si los datos de Bot A son suficientes, limpios y estables para alimentar entrenamiento supervisado.

No debe intentar resolver todavia:

- ejecucion real contra broker o MetaTrader;
- optimizacion automatica agresiva de parametros;
- gestion avanzada de multiples posiciones simultaneas;
- portfolio allocation multi-simbolo;
- latencia, rechazos, requotes o microestructura real;
- entrenamiento final de modelos productivos;
- decisiones discrecionales o interpretaciones fuera del contrato de datos;
- prometer performance futura a partir de 4 meses de historico.

La primera responsabilidad del simulador es ser correcto, trazable y dificil de contaminar con leakage. La rentabilidad viene despues de la confiabilidad del laboratorio.

## 2. Alcance v0.1

La version v0.1 debe ser una base minima seria, no un prototipo desordenado. Debe permitir correr el dataset inicial de 4 meses y generar outputs auditables.

### Carga de datasets Bot A

- Leer archivos JSONL y/o CSV exportados por Bot A.
- Soportar estructura de carpetas por corrida `run_*`.
- Validar campos minimos: `snapshot_id`, `symbol`, `timestamp`, `anchor_bar_timestamp`, `current_price`, OHLC, `spread_pips`, `validation`, `features` y `gaspar_context`.
- Normalizar timestamps a UTC timezone-aware.
- Ordenar por `symbol`, `anchor_bar_timestamp` y `snapshot_id`.
- Detectar duplicados, gaps, timestamps fuera de orden, OHLC invalido, spreads negativos y snapshots invalidos.
- Emitir un reporte de calidad antes de simular.

### Recorrido historico por timestamp

- Iterar snapshots en orden temporal.
- Mantener estado del simulador: balance, equity, posicion abierta, historial de operaciones y ultimo snapshot procesado.
- No usar informacion futura para decidir en el timestamp actual.
- Permitir filtros por simbolo, sesion, rango de fechas y calidad de snapshot.

### Votos mock/rule-based de magos

Melchor v0.1:

- Rol: control de riesgo y autorizacion.
- Salida: `APPROVE`, `BLOCK` o `WARN`.
- Reglas iniciales: bloquear spread excesivo, drawdown diario excedido, snapshot invalido, sesion no permitida o riesgo operacional alto.

Baltasar v0.1:

- Rol: direccion tecnica.
- Salida: `BUY`, `SELL` o `NEUTRAL`.
- Reglas iniciales: EMA, momentum, RSI, estructura y alineacion MTF cuando existan.

Gaspar v0.1:

- Rol: calidad de oportunidad.
- Salida: `GOOD`, `FAIR` o `POOR`.
- Reglas iniciales: confluencia H4/D1, distancia a soporte/resistencia, rango disponible, sesion activa y consumo de ATR diario.

Los votos deben registrar `reason`, `confidence`, `features_used` y `rule_version`.

### Decision de CEO-MAGI

CEO-MAGI v0.1 debe consolidar votos con reglas simples:

- `NO_TRADE` si Melchor bloquea.
- `NO_TRADE` si Baltasar es `NEUTRAL`.
- `NO_TRADE` si Gaspar es `POOR`.
- `OPEN_LONG` si Melchor aprueba, Baltasar indica `BUY` y Gaspar es `GOOD` o `FAIR`.
- `OPEN_SHORT` si Melchor aprueba, Baltasar indica `SELL` y Gaspar es `GOOD` o `FAIR`.
- `SKIP_WARN` si la oportunidad existe pero Melchor emite `WARN` y la configuracion exige aprobacion estricta.

Cada decision debe incluir trazabilidad completa: snapshot, votos, regla activada, parametros de riesgo, precio teorico, SL, TP y razon.

### Simulacion basica de operaciones

- Una sola operacion abierta a la vez por corrida v0.1.
- Entrada al `current_price` ajustado por spread configurable o al close del anchor segun configuracion.
- Direccion `LONG` o `SHORT`.
- Tamano fijo o riesgo fijo por trade.
- Costos basicos: spread y slippage fijo opcional.
- Cierre por SL, TP, timeout, fin de dataset o cierre manual por regla simple.
- Si SL y TP se tocan en la misma vela, marcar `AMBIGUOUS` salvo que exista granularidad menor suficiente.

### SL/TP

v0.1 debe soportar:

- SL fijo en pips;
- TP por ratio R fijo;
- timeout por numero maximo de barras;
- parametrizacion por YAML.

No incluir todavia trailing stop, partial closes, break-even dinamico ni sizing adaptativo complejo.

### Metricas

Calcular metricas por corrida, simbolo, sesion, mes, direccion, mago y alineacion de votos:

- total trades;
- win rate;
- profit factor;
- expectancy;
- average R;
- max drawdown;
- Sharpe simplificado si aplica;
- trades por sesion;
- performance por combinaciones de votos.

### Outputs auditables

Cada corrida debe crear una carpeta unica en `data/output/<run_id>/` con:

- `config_resolved.yaml`;
- `data_quality_report.json`;
- `data_quality_report.md`;
- `snapshots_used.parquet` o `snapshots_used.csv`;
- `votes.jsonl`;
- `ceo_decisions.jsonl`;
- `trades.jsonl`;
- `closed_trades.csv`;
- `metrics.json`;
- `metrics.md`;
- `retraining_records.jsonl`;
- `run_manifest.json`.

## 3. Alcance v0.2 a v1.0

### v0.2: base de backtesting confiable

- Completar loader robusto JSONL/CSV.
- Agregar pruebas unitarias para parsing, orden temporal, validacion y simulacion SL/TP.
- Incluir costos configurables por simbolo.
- Agregar manejo explicito de eventos `AMBIGUOUS`.
- Exportar reportes markdown consistentes.

### v0.3: conexion de Melchor real

- Reemplazar mock de Melchor por adaptador real.
- Mantener interfaz estable `MagiAgent.evaluate(snapshot) -> MageVote`.
- Comparar Melchor real vs Melchor rule-based.
- Medir performance cuando Melchor aprueba, bloquea o advierte.
- Registrar version del modelo/reglas de Melchor.

### v0.4: conexion de Baltasar real

- Integrar Baltasar real como proveedor de direccion.
- Comparar direccion real vs proxy rule-based.
- Medir precision direccional, outcomes por confianza y deterioro por regimen de mercado.
- Generar dataset de error analysis para Baltasar.

### v0.5: conexion de Gaspar real

- Integrar Gaspar real como evaluador de calidad de oportunidad.
- Comparar `GOOD`, `FAIR`, `POOR` contra outcomes por R, MFE, MAE y timeout.
- Validar que Gaspar no reciba variables prohibidas de direccion tecnica si su contrato lo excluye.
- Generar dataset de reentrenamiento especifico de Gaspar.

### v0.6: reportería ejecutiva

- Crear reportes en `reports/` para CEO-MAGI y revision humana.
- Incluir resumen ejecutivo, tablas por periodo, drawdown, equity curve, matriz de combinaciones de votos y principales fallos.
- Exportar CSV/Parquet para analisis externo.
- Preparar comparativas entre corridas.

### v0.7: dataset para reentrenamiento

- Consolidar `retraining_records.jsonl`.
- Separar features disponibles al momento de decision, votos, decision CEO y labels futuros.
- Crear datasets por modulo: Melchor, Baltasar, Gaspar y CEO-MAGI.
- Versionar schemas y reglas de labeling.
- Agregar chequeos automaticos de leakage.

### v0.8: validacion con 6 años historicos

- Ejecutar el simulador sobre dataset amplio de 6 años.
- Medir estabilidad por año, trimestre, sesion, simbolo, volatilidad y regimen.
- Identificar degradacion fuera del periodo de desarrollo.
- Documentar diferencias entre 4 meses y 6 años.

### v0.9: comparacion entre estrategias

- Soportar multiples estrategias/configuraciones en la misma suite.
- Comparar rule-based vs magos reales vs combinaciones hibridas.
- Incluir ranking por metricas y restricciones de riesgo.
- Agregar pruebas de sensibilidad de SL, TP, spread, slippage y filtros horarios.

### v1.0: laboratorio estable de MAGI

- Backtester reproducible, probado y documentado.
- Contratos de datos versionados.
- Reporteria ejecutiva y tecnica.
- Datasets de reentrenamiento generados de forma automatica.
- Validacion amplia con 6 años.
- Comparacion formal entre estrategias.
- Criterios claros para pasar a pruebas demo con datos recientes y ejecucion controlada.

## 4. Arquitectura propuesta

Estructura recomendada en la raiz del repositorio:

```text
data/
  input/
    bot_a/
      run_YYYY-MM-DD_HH-MM-SS/
  output/
    simulations/
      run_YYYYMMDD_HHMMSS_<config>/
    training/
      melchor/
      baltasar/
      gaspar/
      ceo_magi/
magi/
  __init__.py
  contracts.py
  melchor.py
  baltasar.py
  gaspar.py
  ceo_magi.py
  adapters/
    __init__.py
    mock_agents.py
    real_agents.py
simulator/
  __init__.py
  config.py
  loaders.py
  validation.py
  timeline.py
  execution.py
  portfolio.py
  metrics.py
  reporting.py
  retraining.py
  schemas.py
  audit.py
config/
  simulator_v01.yaml
  costs.yaml
  symbols.yaml
  sessions.yaml
reports/
  simulator/
    README.md
run_simulation.py
tests/
  test_loaders.py
  test_validation.py
  test_timeline.py
  test_execution.py
  test_metrics.py
```

Responsabilidades:

- `data/input`: datasets historicos de Bot A, preferiblemente inmutables por corrida.
- `data/output`: resultados generados por el simulador, aislados por `run_id`.
- `magi/`: contratos e implementaciones de Melchor, Baltasar, Gaspar y CEO-MAGI.
- `magi/adapters/`: adaptadores mock, rule-based y reales sin cambiar la interfaz del simulador.
- `simulator/loaders.py`: lectura JSONL/CSV, parsing y normalizacion.
- `simulator/validation.py`: validaciones de calidad y contratos.
- `simulator/timeline.py`: orden temporal y generador de snapshots.
- `simulator/execution.py`: motor de entrada, SL, TP, timeout y cierre.
- `simulator/portfolio.py`: balance, equity, posicion abierta y restricciones.
- `simulator/metrics.py`: calculo de metricas.
- `simulator/reporting.py`: generacion de JSON, CSV y Markdown.
- `simulator/retraining.py`: construccion de registros para reentrenamiento.
- `simulator/schemas.py`: dataclasses o Pydantic models para contratos internos.
- `config/`: parametros declarativos de simulacion.
- `reports/`: reportes humanos y comparativas.
- `run_simulation.py`: entrypoint CLI.

## 5. Contratos de datos

Los contratos deben versionarse. Cada registro debe incluir `schema_version`.

### Snapshot de entrada

Campos minimos:

```json
{
  "schema_version": "bot_a_snapshot_v1",
  "snapshot_id": "string",
  "run_id": "string",
  "symbol": "EURUSD",
  "timestamp": "2026-01-01T12:00:00Z",
  "anchor_bar_timestamp": "2026-01-01T11:55:00Z",
  "timeframe": "M5",
  "open": 1.0,
  "high": 1.0,
  "low": 1.0,
  "close": 1.0,
  "current_price": 1.0,
  "spread_pips": 0.8,
  "active_session": "london",
  "features": {},
  "gaspar_context": {},
  "account": {
    "balance": 10000.0,
    "equity": 10000.0,
    "daily_drawdown_percent": 0.0,
    "risk_percent_per_trade": 1.0
  },
  "validation": {
    "is_valid": true,
    "issues": []
  }
}
```

### Voto de cada mago

Contrato unificado:

```json
{
  "schema_version": "mage_vote_v1",
  "snapshot_id": "string",
  "agent": "MELCHOR",
  "agent_version": "rule_based_v0.1",
  "vote": "APPROVE",
  "direction": null,
  "quality": null,
  "confidence": 0.72,
  "risk_flag": "LOW",
  "context_tag": "trend",
  "features_used": ["spread_pips", "active_session"],
  "reason": "string"
}
```

Especializacion esperada:

- Melchor: `vote` en `APPROVE|WARN|BLOCK`.
- Baltasar: `direction` en `BUY|SELL|NEUTRAL`.
- Gaspar: `quality` en `GOOD|FAIR|POOR`.

### Decision CEO-MAGI

```json
{
  "schema_version": "ceo_decision_v1",
  "snapshot_id": "string",
  "decision_id": "string",
  "ceo_version": "rule_based_v0.1",
  "action": "OPEN_LONG",
  "direction": "LONG",
  "entry_price": 1.0,
  "sl": 0.999,
  "tp": 1.002,
  "risk_r": 1.0,
  "position_size": 0.1,
  "decision_rule": "melchor_approve_baltasar_buy_gaspar_good_or_fair",
  "votes": {
    "melchor": "APPROVE",
    "baltasar": "BUY",
    "gaspar": "GOOD"
  },
  "reason": "string"
}
```

Acciones permitidas v0.1:

- `OPEN_LONG`;
- `OPEN_SHORT`;
- `NO_TRADE`;
- `SKIP_WARN`;
- `FORCED_CLOSE`.

### Operacion simulada

```json
{
  "schema_version": "simulated_trade_v1",
  "trade_id": "string",
  "decision_id": "string",
  "snapshot_id": "string",
  "symbol": "EURUSD",
  "direction": "LONG",
  "entry_timestamp": "2026-01-01T12:00:00Z",
  "entry_price": 1.0,
  "sl": 0.999,
  "tp": 1.002,
  "initial_risk_price": 0.001,
  "position_size": 0.1,
  "spread_pips": 0.8,
  "slippage_pips": 0.1,
  "status": "OPEN"
}
```

### Resultado de operacion

```json
{
  "schema_version": "trade_result_v1",
  "trade_id": "string",
  "exit_timestamp": "2026-01-01T13:20:00Z",
  "exit_price": 1.002,
  "exit_reason": "TP",
  "pnl": 100.0,
  "pnl_r": 2.0,
  "mfe_r": 2.1,
  "mae_r": -0.4,
  "bars_held": 16,
  "duration_minutes": 80,
  "ambiguous_intrabar": false
}
```

`exit_reason` permitido v0.1:

- `TP`;
- `SL`;
- `TIMEOUT`;
- `END_OF_DATA`;
- `AMBIGUOUS`;
- `FORCED_CLOSE`.

### Registro para reentrenamiento

```json
{
  "schema_version": "magi_retraining_record_v1",
  "record_id": "string",
  "snapshot_id": "string",
  "symbol": "EURUSD",
  "timestamp": "2026-01-01T12:00:00Z",
  "features_at_decision_time": {},
  "melchor_vote": {},
  "baltasar_vote": {},
  "gaspar_vote": {},
  "ceo_decision": {},
  "trade_result": {},
  "labels": {
    "did_trade": true,
    "outcome": "TP",
    "pnl_r": 2.0,
    "mfe_r": 2.1,
    "mae_r": -0.4,
    "good_opportunity": true
  },
  "leakage_guard": {
    "features_cutoff_timestamp": "2026-01-01T12:00:00Z",
    "labels_generated_after_timestamp": "2026-01-01T12:00:00Z"
  }
}
```

Regla critica: `features_at_decision_time` nunca puede incluir `trade_result`, labels futuros, maximos/minimos futuros ni campos derivados de barras posteriores.

## 6. Metricas principales

Metricas base:

- `total_trades`: numero de operaciones cerradas.
- `win_rate`: trades ganadores / total trades.
- `gross_profit`: suma de PnL positivo.
- `gross_loss`: valor absoluto de suma de PnL negativo.
- `profit_factor`: `gross_profit / gross_loss`.
- `expectancy`: promedio de `pnl_r` por trade.
- `average_r`: promedio aritmetico de R.
- `median_r`: mediana de R.
- `max_drawdown`: peor caida desde maximo de equity.
- `max_drawdown_r`: drawdown expresado en R.
- `sharpe_simplified`: media de retornos por trade / desviacion estandar de retornos por trade, solo si hay muestra suficiente.
- `avg_bars_held` y `avg_duration_minutes`.
- `ambiguous_rate`: trades ambiguos / total trades.

Metricas por segmentacion:

- trades por sesion: asia, london, new_york, overlap, inactive.
- trades por simbolo.
- trades por mes/trimestre/año.
- trades por direccion: long vs short.
- trades por alineacion entre magos:
  - Melchor aprueba + Baltasar direccional + Gaspar GOOD;
  - Melchor aprueba + Baltasar direccional + Gaspar FAIR;
  - Melchor advierte + oportunidad tecnica;
  - Melchor bloquea;
  - Baltasar NEUTRAL;
  - Gaspar POOR.
- performance cuando Melchor aprueba vs bloquea:
  - aprobados que se operaron;
  - bloqueados simulados en modo sombra para medir costo de oportunidad;
  - bloqueados que habrian perdido.
- performance cuando Baltasar y Gaspar coinciden:
  - Baltasar BUY/SELL y Gaspar GOOD/FAIR;
  - direccion clara con calidad alta.
- performance cuando hay desacuerdo:
  - Baltasar direccional y Gaspar POOR;
  - Baltasar NEUTRAL y Gaspar GOOD;
  - Melchor WARN/BLOCK con oportunidad aparente.

Metricas de data:

- snapshots totales;
- snapshots validos;
- snapshots descartados;
- duplicados;
- gaps temporales;
- cobertura por simbolo;
- cobertura por sesion;
- porcentaje con `gaspar_context` disponible;
- porcentaje con MTF alineado;
- distribucion de spread.

## 7. Metodologia de validacion

### Dataset de desarrollo: 4 meses

Uso:

- desarrollar loader, contratos, simulacion y reportes;
- depurar reglas iniciales;
- encontrar errores de datos;
- validar que las metricas se calculan correctamente.

Restriccion:

- no usar los 4 meses como evidencia suficiente de edge;
- no optimizar parametros hasta maximizar performance del periodo.

### Dataset de validacion amplia: 6 años

Uso:

- evaluar robustez temporal;
- medir ciclos de mercado distintos;
- comparar años buenos y malos;
- detectar estrategias que solo funcionaron en el dataset corto.

Salida requerida:

- reporte por año;
- reporte por trimestre;
- estabilidad por sesion y simbolo;
- comparacion 4 meses vs 6 años;
- escenarios de costos conservadores.

### Entrenamiento

- Separar datasets por modulo.
- Mantener corte temporal estricto.
- Usar features disponibles solo hasta el timestamp del snapshot.
- Versionar dataset, labels, filtros y configuracion.
- Guardar manifiesto con hashes o conteos por archivo.

### Validacion

- Validar fuera de muestra por tiempo, no con particion aleatoria simple.
- Separar periodos train/validation/test cronologicamente.
- Mantener un periodo final no tocado para evaluacion.
- Evaluar degradacion de performance por regimen.

### Walk-forward testing

Propuesta inicial:

- entrenar en ventana historica fija o expansiva;
- validar en el siguiente bloque temporal;
- avanzar la ventana;
- consolidar resultados por fold temporal;
- registrar parametros por fold.

Ejemplo:

- Train: 18 meses.
- Validation: 3 meses.
- Test forward: 3 meses.
- Step: 3 meses.

La configuracion exacta debe ajustarse al timeframe, numero de trades y disponibilidad del dataset de 6 años.

### Control de sobreajuste

- Limitar numero de parametros optimizables.
- Medir sensibilidad alrededor de parametros elegidos.
- Rechazar configuraciones que solo ganan en un periodo estrecho.
- Comparar contra baselines simples.
- Penalizar estrategias con pocos trades.
- Reportar intervalos de confianza o, minimo, dispersion por folds.
- Congelar reglas antes de correr el periodo final.

### Prevencion de data leakage

- Separar `features_at_decision_time` de `labels`.
- Prohibir cualquier campo calculado con barras posteriores dentro de features.
- Generar labels en un modulo separado y posterior al recorrido historico.
- Registrar `features_cutoff_timestamp`.
- Auditar columnas prohibidas por patrones: `future`, `result`, `outcome`, `mfe`, `mae`, `pnl`, `hit_tp`, `hit_sl`.
- Verificar que MTF use velas cerradas y no informacion parcial futura.
- No normalizar usando estadisticas globales del dataset completo para entrenamiento.

## 8. Criterios de exito

### El simulador funciona cuando

- carga el dataset de 4 meses sin errores criticos;
- genera reporte de calidad reproducible;
- recorre snapshots en orden temporal correcto;
- produce votos, decisiones, trades y metricas para una corrida completa;
- una misma configuracion sobre el mismo input genera los mismos outputs;
- los casos unitarios de SL, TP, timeout y ambiguedad pasan;
- cada trade puede rastrearse hasta snapshot, votos y decision CEO.

### Los magos son auditables cuando

- cada voto tiene `agent_version`, `confidence`, `reason` y `features_used`;
- cada decision de CEO-MAGI incluye votos y regla activada;
- se puede reconstruir por que se abrio, se omitio o se bloqueo una operacion;
- los cambios de version quedan reflejados en outputs;
- hay comparativas entre mock/rule-based y magos reales.

### La data sirve para reentrenamiento cuando

- los registros separan features, votos, decisiones y labels;
- los labels se generan solo con informacion posterior;
- existen checks de leakage;
- los contratos son estables y versionados;
- hay suficientes ejemplos por clase y segmento;
- se documentan descartes, gaps y datos invalidos;
- se pueden generar datasets por Melchor, Baltasar, Gaspar y CEO-MAGI.

### MAGI esta listo para pruebas demo cuando

- v0.1 corre correctamente sobre 4 meses;
- v0.8 corre sobre 6 años con reportes consistentes;
- los costos de spread/slippage estan modelados de forma conservadora;
- las reglas de riesgo de Melchor bloquean condiciones invalidas;
- existe reporte ejecutivo comprensible;
- se conocen las limitaciones del backtest;
- las metricas no dependen de un unico periodo o pocas operaciones;
- hay trazabilidad suficiente para explicar operaciones ganadoras y perdedoras.

## 9. Riesgos tecnicos

- Datos incompletos: snapshots sin features, sin `gaspar_context`, sin OHLC o con validacion fallida.
- Timestamps mal alineados: mezcla de timezone local, UTC, vela abierta y vela cerrada.
- Gaps temporales: huecos por mercado cerrado, errores de exportacion o falta de historico.
- Data leakage: labels, MFE, MAE, retornos futuros o barras posteriores usados como features.
- Overfitting: reglas ajustadas al dataset de 4 meses que fallan en 6 años.
- Seleccion sesgada: filtrar solo snapshots perfectos puede ocultar problemas reales de operacion.
- Ambiguedad intrabar: SL y TP tocados en la misma vela sin saber el orden real.
- Diferencia backtest vs ejecucion real: spread variable, slippage, latencia, rechazo, freeze levels y liquidez.
- Horarios de mercado: sesiones, rollover, viernes, lunes, feriados y cambios de horario de verano.
- Costos subestimados: comisiones, swap, spread nocturno y slippage en noticias.
- Multiples simbolos: correlacion y exposicion agregada no modeladas en v0.1.
- Datos MTF inconsistentes: H1/H4/D1 no cerrados o mal sincronizados con M5.
- Modelos con confianza mal calibrada: alta confianza no implica mayor expectancy.
- Deterioro por regimen: estrategias que funcionan en tendencia pero fallan en rango o volatilidad extrema.

## 10. Entregables concretos

Documentos:

- `docs/simulator_plan.md`: plan tecnico del simulador.
- `docs/simulator_contracts.md`: contratos versionados y ejemplos JSON.
- `docs/simulator_validation_methodology.md`: metodologia de validacion, walk-forward y leakage checks.
- `reports/simulator/README.md`: convenciones de reportes generados.

Codigo:

- `run_simulation.py`: entrypoint CLI.
- `config/simulator_v01.yaml`: configuracion base.
- `config/costs.yaml`: costos por simbolo.
- `magi/contracts.py`: modelos de votos y decisiones.
- `magi/melchor.py`: interfaz y mock/rule-based Melchor.
- `magi/baltasar.py`: interfaz y mock/rule-based Baltasar.
- `magi/gaspar.py`: interfaz y mock/rule-based Gaspar.
- `magi/ceo_magi.py`: reglas CEO-MAGI v0.1.
- `simulator/loaders.py`: loader Bot A.
- `simulator/validation.py`: validaciones de datos.
- `simulator/timeline.py`: recorrido historico.
- `simulator/execution.py`: motor de operaciones.
- `simulator/portfolio.py`: estado de cuenta y posicion.
- `simulator/metrics.py`: metricas.
- `simulator/reporting.py`: outputs JSON/CSV/Markdown.
- `simulator/retraining.py`: registros para reentrenamiento.
- `simulator/schemas.py`: schemas internos.

Pruebas:

- `tests/test_loaders.py`.
- `tests/test_validation.py`.
- `tests/test_timeline.py`.
- `tests/test_execution.py`.
- `tests/test_metrics.py`.
- fixtures pequeñas con snapshots sinteticos para TP, SL, timeout y ambiguedad.

Outputs esperados por corrida:

- `data/output/simulations/<run_id>/run_manifest.json`.
- `data/output/simulations/<run_id>/config_resolved.yaml`.
- `data/output/simulations/<run_id>/data_quality_report.json`.
- `data/output/simulations/<run_id>/data_quality_report.md`.
- `data/output/simulations/<run_id>/votes.jsonl`.
- `data/output/simulations/<run_id>/ceo_decisions.jsonl`.
- `data/output/simulations/<run_id>/trades.jsonl`.
- `data/output/simulations/<run_id>/closed_trades.csv`.
- `data/output/simulations/<run_id>/metrics.json`.
- `data/output/simulations/<run_id>/metrics.md`.
- `data/output/simulations/<run_id>/retraining_records.jsonl`.

## Orden de implementacion paso a paso

1. Crear contratos internos en `simulator/schemas.py` y `magi/contracts.py`.
2. Crear `config/simulator_v01.yaml` con dataset path, costos, SL, TP, timeout, sesiones y flags.
3. Implementar loader Bot A en `simulator/loaders.py`.
4. Implementar validaciones de dataset en `simulator/validation.py`.
5. Implementar timeline historico en `simulator/timeline.py`.
6. Implementar magos mock/rule-based v0.1 en `magi/`.
7. Implementar CEO-MAGI rule-based v0.1.
8. Implementar motor de ejecucion con una sola operacion abierta, SL, TP, timeout y ambiguedad.
9. Implementar metricas base y segmentadas.
10. Implementar reporting auditable.
11. Implementar generacion de `retraining_records.jsonl`.
12. Crear fixtures sinteticos y pruebas unitarias.
13. Correr dataset de 4 meses y corregir errores de datos/contratos.
14. Congelar v0.1 y generar reporte base.
15. Integrar Melchor real y comparar contra mock.
16. Integrar Baltasar real y comparar contra mock.
17. Integrar Gaspar real y comparar contra mock.
18. Ejecutar validacion amplia con 6 años.
19. Agregar comparador de estrategias.
20. Preparar reporte ejecutivo y criterio de paso a pruebas demo.
