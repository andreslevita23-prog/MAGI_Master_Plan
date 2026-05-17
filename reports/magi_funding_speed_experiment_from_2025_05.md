# Experimento rapido de fondeo MAGI desde 2025-05

Exploratorio no productivo. No modifica codigo operativo.

- Meses disponibles desde 2025-05: 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03, 2026-04.

- Meses usados: 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03.

- 2026-04 excluido por dataset incompleto.

- Fase 1: 108,000 USD; Fase 2: reset a 100,000 USD y objetivo 105,000 USD desde el siguiente trade.

## Simulacion secuencial por escenario

| scenario | lot | burned | violated_daily | violated_total | passed_phase1 | phase1_date | phase1_days_cal | phase1_trading_days | phase1_balance | passed_phase2 | phase2_date | phase2_days_cal | phase2_trading_days | phase2_balance | worst_day_usd | best_day_usd | max_drawdown_usd | min_daily_margin_usd | min_total_margin_usd | max_balance | min_balance | final_balance | comment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3.0 | False | False | False | True | 2025-08-07 | 87 | 20 | 108283.7 | True | 2025-09-25 | 50 | 11 | 105159.22 | -917.27 | 2488.3 | 2053.08 | 3082.73 | 8000 | 108283.7 | 100000.0 | 105159.22 | punto medio viable |
| baseline | 5.0 | False | False | False | True | 2025-07-25 | 74 | 14 | 108689.89 | True | 2025-08-07 | 14 | 7 | 105116.27 | -1528.78 | 2466.76 | 3421.79 | 2122.78 | 6122.78 | 108689.89 | 98122.78 | 105116.27 | rapido pero agresivo |
| cluster_only_3sl | 3.0 | False | False | False | True | 2025-08-07 | 87 | 19 | 108075.2 | True | 2025-09-30 | 55 | 12 | 105180.78 | -1150.75 | 2488.3 | 1240.57 | 2849.25 | 8000 | 108075.2 | 100000.0 | 105180.78 | punto medio viable |
| cluster_only_3sl | 5.0 | False | False | False | True | 2025-07-25 | 74 | 14 | 108300.76 | True | 2025-08-07 | 14 | 6 | 105157.91 | -1917.91 | 2530.75 | 2067.62 | 2082.09 | 6122.78 | 108300.76 | 98122.78 | 105157.91 | rapido pero agresivo |

## 5 lotes dentro del mismo periodo que tarda 3 lotes

| scenario | period_end | trades_in_period | lot | burned | violated_daily | violated_total | reached105 | date105 | reached108 | date108 | worst_day_usd | best_day_usd | max_drawdown_usd | min_daily_margin_usd | min_total_margin_usd | max_balance | min_balance | final_balance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2025-09-25 | 68 | 5.0 | False | False | False | True | 2025-06-11 | True | 2025-07-25 | -1528.78 | 4147.17 | 3421.79 | 2471.22 | 8000.0 | 122404.87 | 100000.0 | 122404.87 |
| cluster_only_3sl | 2025-09-30 | 62 | 5.0 | False | False | False | True | 2025-06-11 | True | 2025-07-25 | -1917.91 | 4147.17 | 2067.62 | 2082.09 | 8000.0 | 122093.29 | 100000.0 | 122093.29 |

## Lectura corta

- baseline 3.0 lotes: punto medio viable. F1 2025-08-07; F2 2025-09-25; peor dia -917.27 USD; margen diario minimo 3082.73 USD.

- baseline 5.0 lotes: rapido pero agresivo. F1 2025-07-25; F2 2025-08-07; peor dia -1528.78 USD; margen diario minimo 2122.78 USD.

- cluster_only_3sl 3.0 lotes: punto medio viable. F1 2025-08-07; F2 2025-09-30; peor dia -1150.75 USD; margen diario minimo 2849.25 USD.

- cluster_only_3sl 5.0 lotes: rapido pero agresivo. F1 2025-07-25; F2 2025-08-07; peor dia -1917.91 USD; margen diario minimo 2082.09 USD.

- En el periodo exacto hasta 2025-09-25 usado por 3 lotes en baseline, 5 lotes no se quema, no viola diario, balance final 122404.87 USD, peor dia -1528.78 USD.

- En el periodo exacto hasta 2025-09-30 usado por 3 lotes en cluster_only_3sl, 5 lotes no se quema, no viola diario, balance final 122093.29 USD, peor dia -1917.91 USD.
