# Informe ejecutivo MAGI: CEO v2 y reentrenamiento de magos

Fecha: 2026-04-29  
Alcance: estado actual de CEO-MAGI v2, simulacion operativa proxy y plan tecnico para reentrenar Melchor, Baltasar y Gaspar.

## 1. Resumen ejecutivo

MAGI ya cuenta con una base experimental completa para CEO-MAGI: dataset tabular, splits temporales, baselines sin ML, CEO v1, auditoria de labels, CEO v2 con target tradeable, analisis por segmentos, auditoria de politica, walk-forward y simulacion proxy R/SL/TP.

El hallazgo central es claro: CEO v2 aprendio abstencion contextual. La politica `conservative_core` redujo cobertura y mejoro la precision del set test frente a Baltasar y CEO v1 cuando se mide contra el target tradeable. Sin embargo, la simulacion proxy en R no valida rentabilidad operativa bajo el escenario conservador. Por tanto, CEO v2 no esta listo para demo operativa.

La siguiente fase no debe empezar por mas ML. Debe empezar por mejorar la simulacion con first-touch intrabar, construir labels RR 1:2 mas institucionales y despues reentrenar magos v2.

## 2. Que se construyo

- Dataset CEO final: 371,501 registros entre 2020-01-15T00:00:00Z y 2026-04-14T22:55:00Z.
- Pipeline tabular final con senales, contexto, regimen, votos, confianza y outcomes H12/H48/H96/H288.
- Baselines operativos sin ML: `always_do_nothing`, `baltasar_only`, `gaspar_only`, `baltasar_gaspar_aligned`, `high_confidence_alignment`.
- CEO v1 con RandomForest: replico `baltasar_only`, lo que confirmo dependencia del target original.
- Auditoria de labels: midio acoplamiento con Baltasar y disponibilidad real de campos MFE/MAE/return.
- CEO v2 tradeable: target conservador `ceo_label_h48_tradeable`.
- Segment analysis, policy audit, walk-forward y simulacion proxy con RR 1:1, 1:1.5 y 1:2.

## 3. Hallazgos principales

- CEO v1 no aprendio una funcion CEO real: copio la regla de Baltasar porque `ceo_label_h48` estaba acoplado a `baltasar_signal`.
- La dependencia label vs Baltasar fue alta: mutual information 0.3547; accuracy de una regla simple basada solo en Baltasar 65.12%.
- El target tradeable hizo que CEO v2 filtrara operaciones y aprendiera abstencion contextual.
- `conservative_core` mejoro precision en test a cambio de menor cobertura.
- La zona `daily_range_position > 0.85` debe bloquearse: aparecio como segmento de precision muy pobre.
- RR 1:2 fue el perfil proxy mas prometedor, pero aun negativo en escenario conservador.
- La diferencia entre escenarios conservative y optimistic demuestra que falta first-touch intrabar.

## 4. Resultados clave

### Distribucion del target tradeable

![Distribucion target tradeable](reports/magi_ceo_v2_and_mages_retraining_assets/tradeable_label_distribution.png)

| Clase | Filas | Peso |
| --- | --- | --- |
| DO_NOTHING | 350,111 | 94.24% |
| ENTER_BUY | 10,041 | 2.70% |
| ENTER_SELL | 11,349 | 3.05% |

### CEO v2 por threshold

![Precision por threshold](reports/magi_ceo_v2_and_mages_retraining_assets/threshold_precision_coverage.png)

| Split | Threshold | Trades | Coverage | Trade precision | BUY precision | SELL precision |
| --- | --- | --- | --- | --- | --- | --- |
| validation | 0.60 | 11,428 | 19.25% | 24.29% | 23.92% | 24.63% |
| validation | 0.70 | 5,075 | 8.55% | 25.71% | 25.93% | 25.48% |
| test | 0.60 | 21,113 | 28.15% | 23.86% | 22.88% | 24.77% |
| test | 0.70 | 8,662 | 11.55% | 26.51% | 27.86% | 25.29% |

### Policy audit

| Split | Politica | Trades | Coverage | Trade precision | BUY precision | SELL precision |
| --- | --- | --- | --- | --- | --- | --- |
| validation | threshold_070_pure | 5,075 | 8.55% | 25.71% | 25.93% | 25.48% |
| validation | conservative_core | 3,355 | 5.65% | 25.54% | 24.35% | 27.50% |
| test | threshold_070_pure | 8,662 | 11.55% | 26.51% | 27.86% | 25.29% |
| test | conservative_core | 4,830 | 6.44% | 28.59% | 28.97% | 28.00% |

### Walk-forward anual

![Walk-forward anual](reports/magi_ceo_v2_and_mages_retraining_assets/walk_forward_yearly_precision.png)

| Ano | Trades | Coverage | Trade precision |
| --- | --- | --- | --- |
| 2020 | 4,361 | 7.55% | 26.03% |
| 2021 | 3,190 | 5.34% | 32.04% |
| 2022 | 6,229 | 10.40% | 24.98% |
| 2023 | 3,609 | 6.04% | 26.10% |
| 2024 | 3,355 | 5.65% | 25.54% |
| 2025 | 3,649 | 6.22% | 24.88% |
| 2026 | 1,181 | 7.24% | 40.05% |

### Simulacion proxy R/SL/TP

![Avg R por RR](reports/magi_ceo_v2_and_mages_retraining_assets/rr_avg_r_comparison.png)

![Drawdown por RR](reports/magi_ceo_v2_and_mages_retraining_assets/rr_drawdown_comparison.png)

| RR | Escenario | Trades | Win rate | Avg R | Total R | PF | Max DD R | Ambiguous |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1:1 | conservative | 25,574 | 38.37% | -0.2337 | -5,977.57 | 0.6049 | 6,102.31 | 7,150 |
| 1:1 | optimistic | 25,574 | 66.33% | 0.3254 | 8,322.43 | 2.0430 | 118.32 | 7,150 |
| 1:1.5 | conservative | 25,574 | 37.19% | -0.1244 | -3,181.42 | 0.7909 | 3,512.79 | 5,141 |
| 1:1.5 | optimistic | 25,574 | 57.29% | 0.3782 | 9,671.08 | 1.9602 | 230.55 | 5,141 |
| 1:2 | conservative | 25,574 | 36.62% | -0.0407 | -1,041.70 | 0.9317 | 1,720.60 | 3,725 |
| 1:2 | optimistic | 25,574 | 51.18% | 0.3962 | 10,133.30 | 1.8783 | 293.83 | 3,725 |

### Meses mas relevantes en RR 1:2 conservative

| Mes | Trades | Total R | Avg R | Max DD R |
| --- | --- | --- | --- | --- |
| 2022-10 | 900 | -223.17 | -0.2480 | 317.17 |
| 2020-09 | 798 | -198.37 | -0.2486 | 243.90 |
| 2023-10 | 707 | -171.54 | -0.2426 | 241.39 |
| 2022-06 | 745 | -169.18 | -0.2271 | 216.18 |
| 2025-09 | 625 | -165.99 | -0.2656 | 169.27 |
| 2023-06 | 404 | 180.89 | 0.4477 | 44.94 |
| 2026-02 | 308 | 153.61 | 0.4987 | 18.72 |
| 2021-10 | 282 | 147.56 | 0.5233 | 66.00 |
| 2020-11 | 230 | 118.86 | 0.5168 | 54.92 |
| 2021-11 | 414 | 112.99 | 0.2729 | 70.00 |

## 5. Diagnostico tecnico

CEO v2 no debe pasar a demo operativa todavia. El sistema muestra capacidad para filtrar senales, pero no demuestra edge operativo validado. La precision de label mejoro; la rentabilidad proxy conservadora no.

La brecha entre conservative y optimistic no es un detalle menor: significa que muchas operaciones pudieron tocar TP y SL dentro del horizonte H48, pero no sabemos cual ocurrio primero. Sin orden intrabar, el resultado real no se puede afirmar.

La prioridad tecnica es mejorar la verdad de simulacion. Luego se deben construir labels de entrenamiento que optimicen EV, R, drawdown y ambiguedad, no accuracy direccional.

## 6. Plan de accion

1. Enriquecer simulador con first-touch intrabar M1/M5 si existen datos.
2. Construir labels RR 1:2 con costo, spread, MFE, MAE y orden de toque.
3. Reentrenar Baltasar v2 para direccion operable.
4. Reentrenar Gaspar v2 para calidad de contexto.
5. Reentrenar Melchor v2 para riesgo operativo.
6. Entrenar CEO v3 solo con magos v2.
7. Ejecutar backtest institucional con no solapamiento, costos, slippage, sizing y equity curve.

## 7. Baltasar v2

Objetivo: mejorar senal direccional operable, no solo direccion futura. El target sugerido es `tradeable_direction_rr2` o `expected_R_proxy`. Debe usar MFE/MAE, `future_return_pips`, spread y first-touch cuando este disponible.

Metricas de aceptacion: precision de trades, avg R proxy, profit factor, drawdown y estabilidad temporal. Baltasar v2 debe dejar de optimizar labels de direccion simple.

## 8. Gaspar v2

Objetivo: clasificar contexto operable/no operable. Gaspar no debe votar direccion; debe votar calidad de contexto.

Targets sugeridos: `context_quality_rr2` y `ambiguity_risk`. Features clave: session, bucket ATR, posicion en rango diario, estructura H4/D1, alineacion, volatilidad y regimen.

## 9. Melchor v2

Objetivo: riesgo operativo. Salida esperada: `APPROVE`, `CAUTION`, `BLOCK`.

Target sugerido: `risk_block_rr2`. Debe aprender bloqueos por spread, MAE, drawdown, ambiguedad TP/SL, rangos extremos y condiciones donde operar destruye EV.

## 10. CEO v3

CEO v3 debe entrenarse despues de magos v2. Input: votos nuevos, probabilidades y contexto. Output: `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.

El objetivo de CEO v3 no sera accuracy. Sera EV positivo, cobertura razonable, drawdown controlado y estabilidad fuera de muestra.

## 11. Riesgos y controles

- Sobreajuste por segmentos: controlar con walk-forward y ventanas futuras.
- Leakage: prohibir outcomes futuros como features.
- Meses malos: medir dispersion mensual y bloquear contextos si corresponde.
- Dependencia de proxy: no declarar rentabilidad hasta tener first-touch intrabar.
- Labels mal disenados: validar que no repliquen a Baltasar ni a una regla trivial.
- Falsas mejoras: comparar siempre contra `baltasar_only`, CEO v1 y `always_do_nothing`.

## 12. Proxima decision tecnica

La recomendacion es mejorar first-touch intrabar antes de reentrenar formalmente a los magos. Si se decide avanzar en paralelo, el primer mago debe ser Baltasar v2 con target RR 1:2, porque la direccion operable es la base para que Gaspar y Melchor aprendan contexto y riesgo con mejor verdad de mercado.

Scripts reutilizables: `build_ceo_v2_tradeable_dataset.py`, `train_ceo_v2_tradeable_model.py`, `evaluate_ceo_v2_policy.py`, `walk_forward_ceo_v2_policy.py`, `simulate_ceo_v2_r_trades.py`.

Archivos nuevos recomendados: `build_rr2_first_touch_labels.py`, `train_baltasar_v2_rr2.py`, `train_gaspar_v2_context.py`, `train_melchor_v2_risk.py`, `train_ceo_v3.py`, `backtest_magi_v3_institutional.py`.

## Conclusion

MAGI tiene una base tecnica solida para continuar, pero el resultado honesto es que CEO v2 todavia no demuestra rentabilidad operativa. La senal existe y la abstencion contextual mejoro, pero falta transformar la simulacion proxy en una verdad operativa mas confiable. El siguiente paso correcto es first-touch intrabar y labels RR 1:2 antes de CEO v3.
