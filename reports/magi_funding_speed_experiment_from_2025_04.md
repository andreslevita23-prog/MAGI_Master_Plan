# Experimento rapido de fondeo MAGI desde 2025-04

Experimento exploratorio no productivo. No modifica codigo operativo.

- Meses disponibles desde 2025-04: 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03, 2026-04.

- Meses usados: 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03.

- 2026-04 se excluye por estar incompleto en el artefacto historico.

- Fase 1: 108,000 USD. Fase 2: reset a 100,000 USD y objetivo 105,000 USD desde el siguiente trade disponible.

- Limites: perdida diaria 4,000 USD; perdida total balance <= 92,000 USD.

## Resultados

| scenario | lot | burned | violated_daily | violated_total | passed_phase1 | phase1_date | phase1_days_cal | phase1_trading_days | phase1_balance | passed_phase2 | phase2_date | phase2_days_cal | phase2_trading_days | phase2_balance | worst_day_usd | best_day_usd | max_drawdown_usd | min_daily_margin_usd | min_total_margin_usd | max_balance | min_balance | final_balance | comment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 1.0 | False | False | False | True | 2025-09-30 | 181 | 39 | 108159.95 | True | 2026-03-10 | 161 | 42 | 105045.06 | -305.76 | 1153.91 | 684.36 | 3694.24 | 8000 | 108159.95 | 100000.0 | 105045.06 | viable |
| baseline | 5.0 | False | False | False | True | 2025-04-09 | 7 | 3 | 108329.2 | True | 2025-04-23 | 15 | 3 | 105726.86 | 829.34 | 5769.53 | 0 | 4000 | 8000 | 108329.2 | 100000.0 | 105726.86 | sorprendentemente viable |
| cluster_only_3sl | 1.0 | False | False | False | True | 2025-10-01 | 182 | 39 | 108089.61 | True | 2026-03-13 | 163 | 42 | 105060.65 | -383.58 | 1153.91 | 413.52 | 3616.42 | 8000 | 108089.61 | 100000.0 | 105060.65 | viable |
| cluster_only_3sl | 5.0 | False | False | False | True | 2025-04-09 | 7 | 3 | 108329.2 | True | 2025-04-23 | 15 | 3 | 105726.86 | 829.34 | 5769.53 | 0 | 4000 | 8000 | 108329.2 | 100000.0 | 105726.86 | sorprendentemente viable |

## Lectura corta

- baseline lot 1.0: viable. Fase 1 pasa el 2025-09-30; Fase 2 pasa el 2026-03-10. Peor dia -305.76 USD, margen minimo diario 3694.24 USD, margen minimo total 8000 USD.

- baseline lot 5.0: sorprendentemente viable. Fase 1 pasa el 2025-04-09; Fase 2 pasa el 2025-04-23. Peor dia 829.34 USD, margen minimo diario 4000 USD, margen minimo total 8000 USD.

- cluster_only_3sl lot 1.0: viable. Fase 1 pasa el 2025-10-01; Fase 2 pasa el 2026-03-13. Peor dia -383.58 USD, margen minimo diario 3616.42 USD, margen minimo total 8000 USD.

- cluster_only_3sl lot 5.0: sorprendentemente viable. Fase 1 pasa el 2025-04-09; Fase 2 pasa el 2025-04-23. Peor dia 829.34 USD, margen minimo diario 4000 USD, margen minimo total 8000 USD.


## Nota sobre 5 lotes

El escenario de 5 lotes pasa mucho mas rapido en este tramo porque el inicio de abril 2025 fue favorable y no encuentra dias negativos antes de completar ambas fases. Eso lo hace llamativo, no prudente. Es sobreexposicion: un solo dia adverso de tamano comparable al mejor dia observado podria acercar o romper limites. No debe usarse como recomendacion real.
