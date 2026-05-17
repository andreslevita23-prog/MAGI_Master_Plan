# Desglose mes por mes - MAGI Guardrails v1

Fecha de corte: 2026-05-15

Fuente: simulacion offline sobre `artifacts/ceo_magi_v3/stress_months_trade_detail.csv` y `artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv`.

No se modifica codigo operativo.

## Criterios

- Meses stress: 2020-03 y 2022-04.

- Meses aleatorios no consecutivos: 2020-09, 2021-08, 2022-08, 2024-06, 2024-10.

- Abril 2026 excluido por dataset incompleto.

- `guardrails_completos` usa la variante `guardrails_v1_friday_sl1` del simulador.

- Distancias a limites calculadas con lotaje 1.0 por ser el caso mas exigente: perdida diaria maxima 4% y perdida total maxima 8% sobre cuenta de 100,000 USD.

- `cerca_de_quemar`: `SI` si viola limite; `Cerca` si queda a <= 1,000 USD del limite diario o <= 2,000 USD del limite total; `No` en caso contrario.

## Tabla individual por mes

| mes | fuente | escenario | operaciones | bloqueadas | TP | SL | BE | win_rate | PF | net_R | max_DD_R | peor_dia | mejor_dia | PnL_0_6 | PnL_1_0 | cerca_de_quemar | dist_limite_diario_1_0 | dist_limite_total_1_0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-03 | stress_months | baseline | 181 | 0 | 116 | 65 | 0 | 0.640884 | 2.30929 | 110.458108 | 7.516361 | 2020-03-03 (163.74 USD @1.0) | 2020-03-27 (1894.2 USD @1.0) | 6627.49 | 11045.81 | No | 4163.74 | 8000.0 |
| 2020-03 | stress_months | cluster_only_3sl | 158 | 23 | 100 | 58 | 0 | 0.632911 | 2.23032 | 92.66584 | 6.9748 | 2020-03-19 (-294.41 USD @1.0) | 2020-03-27 (1894.2 USD @1.0) | 5559.95 | 9266.58 | No | 3705.59 | 8000.0 |
| 2020-03 | stress_months | guardrails_completos | 114 | 67 | 81 | 33 | 0 | 0.710526 | 3.146941 | 92.092025 | 4.12481 | 2020-03-13 (-89.71 USD @1.0) | 2020-03-27 (1894.2 USD @1.0) | 5525.52 | 9209.2 | No | 3910.29 | 8000.0 |
| 2022-04 | stress_months | baseline | 94 | 0 | 66 | 28 | 0 | 0.702128 | 2.824536 | 67.234683 | 7.481972 | 2022-04-12 (19.59 USD @1.0) | 2022-04-29 (1024.73 USD @1.0) | 4034.08 | 6723.47 | No | 4019.59 | 8000.0 |
| 2022-04 | stress_months | cluster_only_3sl | 87 | 7 | 63 | 24 | 0 | 0.724138 | 3.145907 | 67.728612 | 6.185696 | 2022-04-12 (19.59 USD @1.0) | 2022-04-29 (1024.73 USD @1.0) | 4063.72 | 6772.86 | No | 4019.59 | 8000.0 |
| 2022-04 | stress_months | guardrails_completos | 77 | 17 | 55 | 22 | 0 | 0.714286 | 2.988539 | 57.527539 | 7.268688 | 2022-04-27 (-8.8 USD @1.0) | 2022-04-26 (849.86 USD @1.0) | 3451.65 | 5752.75 | No | 3991.2 | 8000.0 |
| 2020-09 | ceo_magi_v3_decisions | baseline | 73 | 0 | 58 | 15 | 0 | 0.794521 | 5.775572 | 76.250521 | 2.55222 | 2020-09-04 (-130.38 USD @1.0) | 2020-09-03 (1037.29 USD @1.0) | 4575.03 | 7625.05 | No | 3869.62 | 7828.4 |
| 2020-09 | ceo_magi_v3_decisions | cluster_only_3sl | 73 | 0 | 58 | 15 | 0 | 0.794521 | 5.775572 | 76.250521 | 2.55222 | 2020-09-04 (-130.38 USD @1.0) | 2020-09-03 (1037.29 USD @1.0) | 4575.03 | 7625.05 | No | 3869.62 | 7828.4 |
| 2020-09 | ceo_magi_v3_decisions | guardrails_completos | 66 | 7 | 52 | 14 | 0 | 0.787879 | 5.302412 | 66.415072 | 3.033384 | 2020-09-04 (-130.38 USD @1.0) | 2020-09-03 (1037.29 USD @1.0) | 3984.9 | 6641.51 | No | 3869.62 | 7828.4 |
| 2021-08 | ceo_magi_v3_decisions | baseline | 44 | 0 | 29 | 15 | 0 | 0.659091 | 2.759617 | 28.529623 | 2.074541 | 2021-08-03 (-134.32 USD @1.0) | 2021-08-06 (619.44 USD @1.0) | 1711.78 | 2852.96 | No | 3865.68 | 7865.68 |
| 2021-08 | ceo_magi_v3_decisions | cluster_only_3sl | 44 | 0 | 29 | 15 | 0 | 0.659091 | 2.759617 | 28.529623 | 2.074541 | 2021-08-03 (-134.32 USD @1.0) | 2021-08-06 (619.44 USD @1.0) | 1711.78 | 2852.96 | No | 3865.68 | 7865.68 |
| 2021-08 | ceo_magi_v3_decisions | guardrails_completos | 38 | 6 | 25 | 13 | 0 | 0.657895 | 2.556639 | 23.078619 | 1.370498 | 2021-08-03 (-134.32 USD @1.0) | 2021-08-06 (619.44 USD @1.0) | 1384.72 | 2307.86 | No | 3865.68 | 7865.68 |
| 2022-08 | ceo_magi_v3_decisions | baseline | 89 | 0 | 65 | 24 | 0 | 0.730337 | 3.738957 | 79.8211 | 4.949009 | 2022-08-23 (16.56 USD @1.0) | 2022-08-03 (1200.91 USD @1.0) | 4789.27 | 7982.11 | No | 4016.56 | 8000.0 |
| 2022-08 | ceo_magi_v3_decisions | cluster_only_3sl | 86 | 3 | 63 | 23 | 0 | 0.732558 | 3.772913 | 77.468025 | 5.529876 | 2022-08-23 (-160.66 USD @1.0) | 2022-08-03 (1200.91 USD @1.0) | 4648.08 | 7746.8 | No | 3839.34 | 8000.0 |
| 2022-08 | ceo_magi_v3_decisions | guardrails_completos | 80 | 9 | 59 | 21 | 0 | 0.7375 | 3.899878 | 73.408792 | 4.182031 | 2022-08-19 (-124.18 USD @1.0) | 2022-08-03 (1200.91 USD @1.0) | 4404.53 | 7340.88 | No | 3875.82 | 8000.0 |
| 2024-06 | ceo_magi_v3_decisions | baseline | 12 | 0 | 8 | 4 | 0 | 0.666667 | 3.798296 | 8.065859 | 2.662804 | 2024-06-13 (-266.28 USD @1.0) | 2024-06-28 (348.08 USD @1.0) | 483.95 | 806.59 | No | 3733.72 | 7911.71 |
| 2024-06 | ceo_magi_v3_decisions | cluster_only_3sl | 12 | 0 | 8 | 4 | 0 | 0.666667 | 3.798296 | 8.065859 | 2.662804 | 2024-06-13 (-266.28 USD @1.0) | 2024-06-28 (348.08 USD @1.0) | 483.95 | 806.59 | No | 3733.72 | 7911.71 |
| 2024-06 | ceo_magi_v3_decisions | guardrails_completos | 12 | 0 | 8 | 4 | 0 | 0.666667 | 3.798296 | 8.065859 | 2.662804 | 2024-06-13 (-266.28 USD @1.0) | 2024-06-28 (348.08 USD @1.0) | 483.95 | 806.59 | No | 3733.72 | 7911.71 |
| 2024-10 | ceo_magi_v3_decisions | baseline | 30 | 0 | 20 | 10 | 0 | 0.666667 | 2.597725 | 13.896353 | 4.047864 | 2024-10-25 (-148.35 USD @1.0) | 2024-10-31 (373.39 USD @1.0) | 833.78 | 1389.64 | No | 3851.65 | 7999.14 |
| 2024-10 | ceo_magi_v3_decisions | cluster_only_3sl | 30 | 0 | 20 | 10 | 0 | 0.666667 | 2.597725 | 13.896353 | 4.047864 | 2024-10-25 (-148.35 USD @1.0) | 2024-10-31 (373.39 USD @1.0) | 833.78 | 1389.64 | No | 3851.65 | 7999.14 |
| 2024-10 | ceo_magi_v3_decisions | guardrails_completos | 29 | 1 | 20 | 9 | 0 | 0.689655 | 3.052719 | 15.192689 | 2.751528 | 2024-10-04 (-33.17 USD @1.0) | 2024-10-31 (373.39 USD @1.0) | 911.56 | 1519.27 | No | 3966.83 | 7999.14 |


## Lectura rapida

- Ningun mes/escenario de esta muestra queda cerca de quemar bajo el criterio anterior con lotaje 1.0.

- La distancia al limite total aparece estable en 8,000 USD cuando el balance nunca cae por debajo del capital inicial durante el mes simulado; no debe interpretarse como certificacion de fondeo continua.

- En varios meses los guardrails completos reducen SL, pero tambien sacrifican TP y bajan net R. La lectura fina debe hacerse por mes, no solo por agregado.
