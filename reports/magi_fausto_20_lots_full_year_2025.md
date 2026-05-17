# MAGI Fausto 20 lotes - ano completo 2025

Experimento exploratorio no productivo. Una sola cuenta, sin resets ni payouts.

- Periodo solicitado: 2025-01-01 a 2025-12-31.

- Meses disponibles en 2025 dentro del dataset: 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12.

- Cuenta inicial: 100,000 USD. Lote: 20.0.

- Limites medidos: perdida diaria 4,000 USD; perdida total balance <= 92,000 USD.

## Resumen

| scenario | initial_balance | final_balance | total_gain_usd | return_pct | max_balance | min_balance | worst_day | worst_day_usd | best_day | best_day_usd | max_drawdown_usd | max_drawdown_pct | max_drawdown_date | worst_loss_streak | best_win_streak | operations | tp | sl | win_rate | profit_factor | violated_daily | daily_violation_date | violated_total | total_violation_date | comment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 100000.0 | 342022.95 | 242022.95 | 242.02 | 348836.42 | 100000.0 | 2025-07-16 | -6115.13 | 2025-04-04 | 23078.13 | 13687.17 | 13.69 | 2025-07-16 | 5 | 25 | 180 | 126 | 54 | 0.7 | 2.9797 | True | 2025-01-16 | False |  | suicida para fondeo: viola limite diario |
| cluster_only_3sl | 100000.0 | 337302.77 | 237302.77 | 237.3 | 344116.25 | 100000.0 | 2025-07-16 | -7671.66 | 2025-04-04 | 23078.13 | 8270.47 | 8.27 | 2025-07-16 | 3 | 25 | 173 | 122 | 51 | 0.7052 | 3.0801 | True | 2025-01-16 | False |  | suicida para fondeo: viola limite diario |

## Tabla mensual

| scenario | month | operations | tp | sl | monthly_pnl_usd | month_close_balance | worst_day | worst_day_usd | best_day | best_day_usd | max_drawdown_month_usd | max_drawdown_month_date | violated_daily_dd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2025-01 | 17 | 12 | 5 | 22244.89 | 122244.89 | 2025-01-16 | -4108.73 | 2025-01-31 | 6810.82 | 7953.53 | 2025-01-16 | True |
| baseline | 2025-02 | 17 | 8 | 9 | 5648.53 | 127893.43 | 2025-02-12 | -3161.25 | 2025-02-14 | 3440.69 | 7370.37 | 2025-02-25 | False |
| baseline | 2025-03 | 14 | 8 | 6 | 9310.03 | 137203.45 | 2025-03-25 | -2748.76 | 2025-03-21 | 8152.4 | 6861.99 | 2025-03-20 | False |
| baseline | 2025-04 | 22 | 22 | 0 | 70105.65 | 207309.11 | 2025-04-30 | 925.7 | 2025-04-04 | 23078.13 | 0 |  | False |
| baseline | 2025-05 | 8 | 6 | 2 | 13431.98 | 220741.09 | 2025-05-14 | -2502.13 | 2025-05-16 | 6688.17 | 2502.13 | 2025-05-14 | False |
| baseline | 2025-06 | 4 | 3 | 1 | 7272.49 | 228013.59 | 2025-06-10 | 3329.11 | 2025-06-11 | 3943.38 | 2640.91 | 2025-06-11 | False |
| baseline | 2025-07 | 32 | 18 | 14 | 17860.35 | 245873.94 | 2025-07-16 | -6115.13 | 2025-07-17 | 9741.32 | 13687.17 | 2025-07-16 | True |
| baseline | 2025-08 | 13 | 12 | 1 | 32263.06 | 278137.0 | 2025-08-21 | 274.5 | 2025-08-07 | 16588.66 | 2766.68 | 2025-08-01 | False |
| baseline | 2025-09 | 12 | 10 | 2 | 22265.46 | 300402.46 | 2025-09-10 | -2380.66 | 2025-09-24 | 9396.09 | 4939.36 | 2025-09-11 | False |
| baseline | 2025-10 | 22 | 17 | 5 | 37465.31 | 337867.77 | 2025-11-01 | -1544.6 | 2025-10-02 | 6708.38 | 4860.6 | 2025-10-23 | False |
| baseline | 2025-11 | 14 | 8 | 6 | 7501.49 | 345369.26 | 2025-11-28 | -2545.63 | 2025-11-06 | 3895.71 | 2707.87 | 2025-11-07 | False |
| baseline | 2025-12 | 5 | 2 | 3 | -3346.31 | 342022.95 | 2025-12-10 | -2654.27 | 2025-12-09 | 1894.61 | 6813.47 | 2025-12-18 | False |
| cluster_only_3sl | 2025-01 | 17 | 12 | 5 | 22244.89 | 122244.89 | 2025-01-16 | -4108.73 | 2025-01-31 | 6810.82 | 7953.53 | 2025-01-16 | True |
| cluster_only_3sl | 2025-02 | 17 | 8 | 9 | 5648.53 | 127893.43 | 2025-02-12 | -3161.25 | 2025-02-14 | 3440.69 | 7370.37 | 2025-02-25 | False |
| cluster_only_3sl | 2025-03 | 14 | 8 | 6 | 9310.03 | 137203.45 | 2025-03-25 | -2748.76 | 2025-03-21 | 8152.4 | 6861.99 | 2025-03-20 | False |
| cluster_only_3sl | 2025-04 | 22 | 22 | 0 | 70105.65 | 207309.11 | 2025-04-30 | 925.7 | 2025-04-04 | 23078.13 | 0 |  | False |
| cluster_only_3sl | 2025-05 | 8 | 6 | 2 | 13431.98 | 220741.09 | 2025-05-14 | -2502.13 | 2025-05-16 | 6688.17 | 2502.13 | 2025-05-14 | False |
| cluster_only_3sl | 2025-06 | 4 | 3 | 1 | 7272.49 | 228013.59 | 2025-06-10 | 3329.11 | 2025-06-11 | 3943.38 | 2640.91 | 2025-06-11 | False |
| cluster_only_3sl | 2025-07 | 25 | 14 | 11 | 13140.18 | 241153.76 | 2025-07-16 | -7671.66 | 2025-07-17 | 9741.32 | 8270.47 | 2025-07-16 | True |
| cluster_only_3sl | 2025-08 | 13 | 12 | 1 | 32263.06 | 273416.82 | 2025-08-21 | 274.5 | 2025-08-07 | 16588.66 | 2766.68 | 2025-08-01 | False |
| cluster_only_3sl | 2025-09 | 12 | 10 | 2 | 22265.46 | 295682.28 | 2025-09-10 | -2380.66 | 2025-09-24 | 9396.09 | 4939.36 | 2025-09-11 | False |
| cluster_only_3sl | 2025-10 | 22 | 17 | 5 | 37465.31 | 333147.6 | 2025-11-01 | -1544.6 | 2025-10-02 | 6708.38 | 4860.6 | 2025-10-23 | False |
| cluster_only_3sl | 2025-11 | 14 | 8 | 6 | 7501.49 | 340649.08 | 2025-11-28 | -2545.63 | 2025-11-06 | 3895.71 | 2707.87 | 2025-11-07 | False |
| cluster_only_3sl | 2025-12 | 5 | 2 | 3 | -3346.31 | 337302.77 | 2025-12-10 | -2654.27 | 2025-12-09 | 1894.61 | 6813.47 | 2025-12-18 | False |

## Interpretacion

- baseline: termina en 342022.95 USD (+242.02%), pero viola perdida diaria el 2025-01-16. Peor dia -6115.13 USD, max DD 13687.17 USD.

- cluster_only_3sl: termina en 337302.77 USD (+237.3%), pero viola perdida diaria el 2025-01-16. Peor dia -7671.66 USD, max DD 8270.47 USD.


## Dictamen

Con 20 lotes, dejar correr 2025 completo genera una ganancia enorme en el historico, pero no seria apto para fondeo por la regla diaria: la cuenta viola el limite de perdida diaria. Estadisticamente es fascinante; operativamente es suicida para una evaluacion con reglas estrictas.

Grafica: `reports/fausto_20_lots_equity_2025.png`
