# Experimento Fausto MAGI 2025-05-01 a 2025-09-25

Exploratorio no productivo. Simula prop-firm cycling con reset tras payout o quema. No modifica codigo operativo.

## Reglas

- Cuenta inicial por ciclo: 100,000 USD.

- Payout al tocar balance >= 108,000 USD; se retira `balance - 100,000` y se reinicia cuenta.

- Quema si perdida diaria <= -4,000 USD o balance <= 92,000 USD; se reinicia cuenta.

- Cada reset se trata como cuenta nueva, por eso tambien reinicia el conteo diario.

## Tabla principal

| scenario | lot | payouts | burns | net_total | avg_cycle_days | survival_pct | payout_burn_ratio | worst_day_usd | worst_drawdown | max_balance | min_balance | avg_trades_before_payout | avg_trades_before_burn | expectancy_per_cycle | comment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 5.0 | 2 | 0 | 16881.67 | 51.5 | 100.0 | inf | -3272.09 | 3421.79 | 108689.89 | 98122.78 | 28 | 0 | 8440.84 | agresivo pero sorprendentemente limpio |
| baseline | 10.0 | 5 | 1 | 44713.92 | 22.17 | 83.33 | 5.0 | -5236.28 | 5535.68 | 109523.17 | 96245.56 | 11.4 | 11 | 7452.32 | edge sobrevive, pero con dientes; psicologicamente duro |
| baseline | 15.0 | 8 | 3 | 75904.79 | 12.27 | 72.73 | 2.67 | -5753.74 | 6202.85 | 110197.38 | 95839.12 | 7 | 3.33 | 6900.44 | edge sobrevive, pero con dientes; psicologicamente duro |
| baseline | 20.0 | 9 | 3 | 86675.16 | 7.67 | 75.0 | 3.0 | -5399.8 | 7508.87 | 110779.39 | 94600.2 | 5.44 | 5.33 | 7222.93 | edge sobrevive, pero con dientes; psicologicamente duro |
| cluster_only_3sl | 5.0 | 2 | 0 | 16526.93 | 54 | 100.0 | inf | -1917.91 | 2067.62 | 108300.76 | 98122.78 | 25 | 0 | 8263.46 | agresivo pero sorprendentemente limpio |
| cluster_only_3sl | 10.0 | 4 | 0 | 34669.62 | 29 | 100.0 | inf | -3835.83 | 4135.23 | 109417.38 | 96245.56 | 12.75 | 0 | 8667.41 | agresivo pero sorprendentemente limpio |
| cluster_only_3sl | 15.0 | 7 | 2 | 65693.76 | 14.67 | 77.78 | 3.5 | -5753.74 | 6202.85 | 110276.75 | 95821.54 | 7.14 | 4 | 7299.31 | edge sobrevive, pero con dientes; psicologicamente duro |
| cluster_only_3sl | 20.0 | 9 | 3 | 87192.87 | 7.83 | 75.0 | 3.0 | -5571.28 | 5671.56 | 110850.51 | 94428.72 | 5.33 | 3.33 | 7266.07 | edge sobrevive, pero con dientes; psicologicamente duro |

## Ciclos cerrados

| scenario | lot | cycle | kind | start | end | calendar_days | trades | final_balance | payout_amount | max_drawdown | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 5.0 | 1 | payout | 2025-05-13 | 2025-07-25 | 74 | 32 | 108689.89199999999 | 8689.891999999993 | 3421.793499999985 | target_8pct |
| baseline | 5.0 | 2 | payout | 2025-07-25 | 2025-08-22 | 29 | 24 | 108191.7785 | 8191.7785 | 1877.2174999999988 | target_8pct |
| baseline | 10.0 | 1 | payout | 2025-05-13 | 2025-06-10 | 29 | 9 | 108380.549 | 8380.548999999999 | 1251.0650000000023 | target_8pct |
| baseline | 10.0 | 2 | burn | 2025-06-11 | 2025-07-16 | 36 | 11 | 100095.82099999998 | 0.0 | 5535.682000000015 | daily_loss -5236.28 |
| baseline | 10.0 | 3 | payout | 2025-07-16 | 2025-07-25 | 10 | 12 | 108903.41399999999 | 8903.41399999999 | 1377.8029999999999 | target_8pct |
| baseline | 10.0 | 4 | payout | 2025-07-25 | 2025-08-07 | 14 | 18 | 108510.995 | 8510.994999999995 | 3754.435000000012 | target_8pct |
| baseline | 10.0 | 5 | payout | 2025-08-07 | 2025-08-27 | 21 | 7 | 109523.16500000001 | 9523.165000000008 | 0.0 | target_8pct |
| baseline | 10.0 | 6 | payout | 2025-09-03 | 2025-09-25 | 23 | 11 | 109395.79300000002 | 9395.79300000002 | 2469.6820000000007 | target_8pct |
| baseline | 15.0 | 1 | payout | 2025-05-13 | 2025-05-17 | 5 | 5 | 108019.5145 | 8019.514500000005 | 1876.5975000000035 | target_8pct |
| baseline | 15.0 | 2 | payout | 2025-05-20 | 2025-07-15 | 57 | 8 | 110019.65050000002 | 10019.650500000018 | 1980.6839999999938 | target_8pct |
| baseline | 15.0 | 3 | burn | 2025-07-15 | 2025-07-16 | 2 | 6 | 96776.062 | 0.0 | 6202.850999999995 | daily_loss -5753.74 |
| baseline | 15.0 | 4 | burn | 2025-07-16 | 2025-07-16 | 1 | 2 | 95937.4705 | 0.0 | 4062.529500000004 | daily_loss -4062.53 |
| baseline | 15.0 | 5 | payout | 2025-07-16 | 2025-07-17 | 2 | 6 | 110046.4 | 10046.399999999994 | 2066.704500000007 | target_8pct |
| baseline | 15.0 | 6 | payout | 2025-07-17 | 2025-07-30 | 14 | 12 | 109488.292 | 9488.292000000001 | 5631.6524999999965 | target_8pct |
| baseline | 15.0 | 7 | burn | 2025-07-30 | 2025-07-30 | 1 | 2 | 95839.12299999999 | 0.0 | 4160.877000000008 | daily_loss -4160.88 |
| baseline | 15.0 | 8 | payout | 2025-07-30 | 2025-08-01 | 3 | 8 | 110197.37949999998 | 10197.37949999998 | 2083.1790000000037 | target_8pct |
| baseline | 15.0 | 9 | payout | 2025-08-07 | 2025-08-07 | 1 | 4 | 109988.93800000001 | 9988.93800000001 | 0.0 | target_8pct |
| baseline | 15.0 | 10 | payout | 2025-08-07 | 2025-09-03 | 28 | 5 | 109231.735 | 9231.735 | 0.0 | target_8pct |
| baseline | 15.0 | 11 | payout | 2025-09-04 | 2025-09-24 | 21 | 8 | 108912.87849999999 | 8912.878499999992 | 3704.523000000001 | target_8pct |
| baseline | 20.0 | 1 | payout | 2025-05-13 | 2025-05-17 | 5 | 5 | 110692.686 | 10692.686000000002 | 2502.1300000000047 | target_8pct |
| baseline | 20.0 | 2 | payout | 2025-05-20 | 2025-06-11 | 23 | 7 | 110011.792 | 10011.792000000001 | 2640.9119999999966 | target_8pct |
| baseline | 20.0 | 3 | burn | 2025-07-15 | 2025-07-16 | 2 | 6 | 101648.062 | 0.0 | 5671.5639999999985 | daily_loss -5072.75 |
| baseline | 20.0 | 4 | burn | 2025-07-16 | 2025-07-16 | 1 | 2 | 94600.20000000001 | 0.0 | 5399.799999999988 | daily_loss -5399.80 |
| baseline | 20.0 | 5 | payout | 2025-07-16 | 2025-07-17 | 2 | 7 | 110779.39000000001 | 10779.390000000014 | 2755.6059999999998 | target_8pct |
| baseline | 20.0 | 6 | burn | 2025-07-17 | 2025-07-25 | 9 | 8 | 99518.56800000001 | 0.0 | 7508.869999999981 | daily_loss -4355.68 |
| baseline | 20.0 | 7 | payout | 2025-07-26 | 2025-07-29 | 4 | 3 | 109789.232 | 9789.232000000004 | 0.0 | target_8pct |
| baseline | 20.0 | 8 | payout | 2025-07-30 | 2025-08-01 | 3 | 10 | 108191.42199999996 | 8191.421999999962 | 5547.83600000001 | target_8pct |
| baseline | 20.0 | 9 | payout | 2025-08-01 | 2025-08-07 | 7 | 3 | 109993.30200000001 | 9993.30200000001 | 0.0 | target_8pct |
| baseline | 20.0 | 10 | payout | 2025-08-07 | 2025-08-07 | 1 | 3 | 109795.864 | 9795.864000000001 | 0.0 | target_8pct |
| baseline | 20.0 | 11 | payout | 2025-08-21 | 2025-09-03 | 14 | 4 | 109038.902 | 9038.902000000002 | 0.0 | target_8pct |
| baseline | 20.0 | 12 | payout | 2025-09-04 | 2025-09-24 | 21 | 7 | 108382.56999999998 | 8382.569999999978 | 4939.364000000001 | target_8pct |
| cluster_only_3sl | 5.0 | 1 | payout | 2025-05-13 | 2025-07-25 | 74 | 26 | 108300.76150000001 | 8300.761500000008 | 2067.616999999984 | target_8pct |
| cluster_only_3sl | 5.0 | 2 | payout | 2025-07-25 | 2025-08-27 | 34 | 24 | 108226.167 | 8226.167000000001 | 1877.2174999999988 | target_8pct |
| cluster_only_3sl | 10.0 | 1 | payout | 2025-05-13 | 2025-06-10 | 29 | 9 | 108380.549 | 8380.548999999999 | 1251.0650000000023 | target_8pct |
| cluster_only_3sl | 10.0 | 2 | payout | 2025-06-11 | 2025-07-25 | 45 | 17 | 108220.97399999997 | 8220.973999999973 | 4135.234000000011 | target_8pct |
| cluster_only_3sl | 10.0 | 3 | payout | 2025-07-25 | 2025-08-07 | 14 | 18 | 108650.71699999999 | 8650.71699999999 | 3754.435000000012 | target_8pct |
| cluster_only_3sl | 10.0 | 4 | payout | 2025-08-07 | 2025-09-03 | 28 | 7 | 109417.38300000002 | 9417.383000000016 | 0.0 | target_8pct |
| cluster_only_3sl | 15.0 | 1 | payout | 2025-05-13 | 2025-05-17 | 5 | 5 | 108019.5145 | 8019.514500000005 | 1876.5975000000035 | target_8pct |
| cluster_only_3sl | 15.0 | 2 | payout | 2025-05-20 | 2025-07-15 | 57 | 8 | 110019.65050000002 | 10019.650500000018 | 1980.6839999999938 | target_8pct |
| cluster_only_3sl | 15.0 | 3 | burn | 2025-07-15 | 2025-07-16 | 2 | 6 | 96776.062 | 0.0 | 6202.850999999995 | daily_loss -5753.74 |
| cluster_only_3sl | 15.0 | 4 | payout | 2025-07-17 | 2025-07-25 | 9 | 7 | 110087.0575 | 10087.057499999995 | 2056.2495000000054 | target_8pct |
| cluster_only_3sl | 15.0 | 5 | burn | 2025-07-25 | 2025-07-25 | 1 | 2 | 95821.537 | 0.0 | 4178.463000000003 | daily_loss -4178.46 |
| cluster_only_3sl | 15.0 | 6 | payout | 2025-07-25 | 2025-08-01 | 8 | 11 | 109375.43049999997 | 9375.430499999973 | 4160.877000000008 | target_8pct |
| cluster_only_3sl | 15.0 | 7 | payout | 2025-08-01 | 2025-08-07 | 7 | 6 | 110276.7475 | 10276.747499999998 | 2075.006999999998 | target_8pct |
| cluster_only_3sl | 15.0 | 8 | payout | 2025-08-07 | 2025-08-27 | 21 | 5 | 109204.786 | 9204.785999999993 | 0.0 | target_8pct |
| cluster_only_3sl | 15.0 | 9 | payout | 2025-09-03 | 2025-09-24 | 22 | 8 | 108710.5765 | 8710.576499999996 | 3704.523000000001 | target_8pct |
| cluster_only_3sl | 20.0 | 1 | payout | 2025-05-13 | 2025-05-17 | 5 | 5 | 110692.686 | 10692.686000000002 | 2502.1300000000047 | target_8pct |
| cluster_only_3sl | 20.0 | 2 | payout | 2025-05-20 | 2025-06-11 | 23 | 7 | 110011.792 | 10011.792000000001 | 2640.9119999999966 | target_8pct |
| cluster_only_3sl | 20.0 | 3 | burn | 2025-07-15 | 2025-07-16 | 2 | 6 | 101648.062 | 0.0 | 5671.5639999999985 | daily_loss -5072.75 |
| cluster_only_3sl | 20.0 | 4 | payout | 2025-07-16 | 2025-07-25 | 10 | 8 | 110850.50600000001 | 10850.506000000008 | 2741.6659999999974 | target_8pct |
| cluster_only_3sl | 20.0 | 5 | burn | 2025-07-25 | 2025-07-25 | 1 | 2 | 94428.71600000001 | 0.0 | 5571.283999999985 | daily_loss -5571.28 |
| cluster_only_3sl | 20.0 | 6 | payout | 2025-07-25 | 2025-07-30 | 6 | 4 | 108031.25 | 8031.25 | 1937.5859999999957 | target_8pct |
| cluster_only_3sl | 20.0 | 7 | burn | 2025-07-30 | 2025-07-30 | 1 | 2 | 94452.16399999999 | 0.0 | 5547.83600000001 | daily_loss -5547.84 |
| cluster_only_3sl | 20.0 | 8 | payout | 2025-07-30 | 2025-08-01 | 3 | 5 | 110017.15999999999 | 10017.159999999989 | 2777.572 | target_8pct |
| cluster_only_3sl | 20.0 | 9 | payout | 2025-08-01 | 2025-08-07 | 7 | 5 | 110372.144 | 10372.144 | 2766.6760000000068 | target_8pct |
| cluster_only_3sl | 20.0 | 10 | payout | 2025-08-07 | 2025-08-07 | 1 | 3 | 109795.864 | 9795.864000000001 | 0.0 | target_8pct |
| cluster_only_3sl | 20.0 | 11 | payout | 2025-08-21 | 2025-09-03 | 14 | 4 | 109038.902 | 9038.902000000002 | 0.0 | target_8pct |
| cluster_only_3sl | 20.0 | 12 | payout | 2025-09-04 | 2025-09-24 | 21 | 7 | 108382.56999999998 | 8382.569999999978 | 4939.364000000001 | target_8pct |

## Interpretacion humana

- baseline 5.0 lotes: agresivo pero sorprendentemente limpio. Payouts=2, burns=0, neto retirado=16881.67 USD, peor dia=-3272.09 USD.

- baseline 10.0 lotes: edge sobrevive, pero con dientes; psicologicamente duro. Payouts=5, burns=1, neto retirado=44713.92 USD, peor dia=-5236.28 USD.

- baseline 15.0 lotes: edge sobrevive, pero con dientes; psicologicamente duro. Payouts=8, burns=3, neto retirado=75904.79 USD, peor dia=-5753.74 USD.

- baseline 20.0 lotes: edge sobrevive, pero con dientes; psicologicamente duro. Payouts=9, burns=3, neto retirado=86675.16 USD, peor dia=-5399.8 USD.

- cluster_only_3sl 5.0 lotes: agresivo pero sorprendentemente limpio. Payouts=2, burns=0, neto retirado=16526.93 USD, peor dia=-1917.91 USD.

- cluster_only_3sl 10.0 lotes: agresivo pero sorprendentemente limpio. Payouts=4, burns=0, neto retirado=34669.62 USD, peor dia=-3835.83 USD.

- cluster_only_3sl 15.0 lotes: edge sobrevive, pero con dientes; psicologicamente duro. Payouts=7, burns=2, neto retirado=65693.76 USD, peor dia=-5753.74 USD.

- cluster_only_3sl 20.0 lotes: edge sobrevive, pero con dientes; psicologicamente duro. Payouts=9, burns=3, neto retirado=87192.87 USD, peor dia=-5571.28 USD.


## Lectura corta

- Fausto no explota en este tramo; el periodo fue favorable para el edge. Pero eso no prueba robustez: a 15-20 lotes el resultado depende demasiado del orden de trades y de no recibir una secuencia mala temprano.

- 10 lotes es el primer nivel que parece agresivo pero aun legible en este periodo. 15 y 20 entran en territorio de timing extremo: imprimen si el tramo acompana, pero serian psicologicamente dificiles y vulnerables a un cambio de regimen.

- 5 lotes sirve como referencia: agresivo, pero menos absurdo que 10/15/20. Nada de esto es recomendacion real de riesgo.
