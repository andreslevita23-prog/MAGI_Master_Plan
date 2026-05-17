# Analisis diario de equity MAGI

Fecha de corte: 2026-05-15

No se modifica codigo operativo. Analisis offline de simulacion historica por dia.

## Alcance

- Meses: 2020-03, 2022-04, 2020-09, 2021-08, 2022-08, 2024-06, 2024-10.

- Escenarios: baseline, cluster_only_3sl, guardrails_completos.

- Cuenta inicial: 100,000 USD. Reglas: perdida diaria maxima 4%, perdida total maxima 8%.

- PnL convertido desde `net_pips` historico con valor pip estandar: 10 USD por pip por lote.

## Lectura ejecutiva

- Con lotaje 0.6, las curvas son mas comodas: los peores dias y drawdowns quedan lejos de los limites de fondeo en esta muestra.

- Con lotaje 1.0, la muestra tampoco quema cuenta, pero algunos meses ya se sienten mas serruchados y emocionalmente mas exigentes.

- El valor `7.52R` del agregado equivale aproximadamente al tramo de drawdown relativo del sistema, pero en dinero real depende de pips/lote: en esta simulacion diaria el dolor visible se evalua mejor con USD y margen restante.

- Los guardrails completos suavizan algunos drawdowns, pero tambien cortan ganancia; `cluster_only_3sl` es menos invasivo.

## Resumen lotaje 0.6

| month | scenario | lot | net_usd | max_drawdown_usd | max_drawdown_pct | max_drawdown_duration_days | worst_day_usd | best_day_usd | min_daily_limit_margin_usd | min_total_limit_margin_usd | danger_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-03 | baseline | 0.6 | 6627.49 | 0.0 | 0.0 | 0 | 98.24 | 1136.52 | 4098.24 | 8098.24 | 0 |
| 2020-03 | cluster_only_3sl | 0.6 | 5559.95 | 176.65 | 0.001766 | 2 | -176.65 | 1136.52 | 3823.35 | 8098.24 | 0 |
| 2020-03 | guardrails_completos | 0.6 | 5525.52 | 53.83 | 0.000538 | 1 | -53.83 | 1136.52 | 3946.17 | 8098.24 | 0 |
| 2022-04 | baseline | 0.6 | 4034.08 | 0.0 | 0.0 | 0 | 11.76 | 614.84 | 4011.76 | 8105.33 | 0 |
| 2022-04 | cluster_only_3sl | 0.6 | 4063.72 | 0.0 | 0.0 | 0 | 11.76 | 614.84 | 4011.76 | 8105.33 | 0 |
| 2022-04 | guardrails_completos | 0.6 | 3451.65 | 5.28 | 5.3e-05 | 1 | -5.28 | 509.92 | 3994.72 | 8105.33 | 0 |
| 2020-09 | baseline | 0.6 | 4575.03 | 78.23 | 0.000782 | 2 | -78.23 | 622.38 | 3921.77 | 7978.32 | 0 |
| 2020-09 | cluster_only_3sl | 0.6 | 4575.03 | 78.23 | 0.000782 | 2 | -78.23 | 622.38 | 3921.77 | 7978.32 | 0 |
| 2020-09 | guardrails_completos | 0.6 | 3984.9 | 78.23 | 0.000782 | 2 | -78.23 | 622.38 | 3921.77 | 7978.32 | 0 |
| 2021-08 | baseline | 0.6 | 1711.78 | 80.59 | 0.000806 | 1 | -80.59 | 371.66 | 3919.41 | 7919.41 | 0 |
| 2021-08 | cluster_only_3sl | 0.6 | 1711.78 | 80.59 | 0.000806 | 1 | -80.59 | 371.66 | 3919.41 | 7919.41 | 0 |
| 2021-08 | guardrails_completos | 0.6 | 1384.72 | 80.59 | 0.000806 | 2 | -80.59 | 371.66 | 3919.41 | 7919.41 | 0 |
| 2022-08 | baseline | 0.6 | 4789.27 | 0.0 | 0.0 | 0 | 9.93 | 720.55 | 4009.93 | 8467.52 | 0 |
| 2022-08 | cluster_only_3sl | 0.6 | 4648.08 | 96.4 | 0.000964 | 2 | -96.4 | 720.55 | 3903.6 | 8467.52 | 0 |
| 2022-08 | guardrails_completos | 0.6 | 4404.53 | 94.4 | 0.000944 | 2 | -74.51 | 720.55 | 3925.49 | 8364.81 | 0 |
| 2024-06 | baseline | 0.6 | 483.95 | 159.77 | 0.001598 | 3 | -159.77 | 208.85 | 3840.23 | 7947.03 | 0 |
| 2024-06 | cluster_only_3sl | 0.6 | 483.95 | 159.77 | 0.001598 | 3 | -159.77 | 208.85 | 3840.23 | 7947.03 | 0 |
| 2024-06 | guardrails_completos | 0.6 | 483.95 | 159.77 | 0.001598 | 3 | -159.77 | 208.85 | 3840.23 | 7947.03 | 0 |
| 2024-10 | baseline | 0.6 | 833.78 | 89.01 | 0.00089 | 3 | -89.01 | 224.03 | 3910.99 | 7999.48 | 0 |
| 2024-10 | cluster_only_3sl | 0.6 | 833.78 | 89.01 | 0.00089 | 3 | -89.01 | 224.03 | 3910.99 | 7999.48 | 0 |
| 2024-10 | guardrails_completos | 0.6 | 911.56 | 19.9 | 0.000199 | 2 | -19.9 | 224.03 | 3980.1 | 7999.48 | 0 |


## Resumen lotaje 1.0

| month | scenario | lot | net_usd | max_drawdown_usd | max_drawdown_pct | max_drawdown_duration_days | worst_day_usd | best_day_usd | min_daily_limit_margin_usd | min_total_limit_margin_usd | danger_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-03 | baseline | 1.0 | 11045.81 | 0.0 | 0.0 | 0 | 163.74 | 1894.2 | 4163.74 | 8163.74 | 0 |
| 2020-03 | cluster_only_3sl | 1.0 | 9266.58 | 294.41 | 0.002944 | 2 | -294.41 | 1894.2 | 3705.59 | 8163.74 | 0 |
| 2020-03 | guardrails_completos | 1.0 | 9209.2 | 89.71 | 0.000897 | 1 | -89.71 | 1894.2 | 3910.29 | 8163.74 | 0 |
| 2022-04 | baseline | 1.0 | 6723.47 | 0.0 | 0.0 | 0 | 19.59 | 1024.73 | 4019.59 | 8175.56 | 0 |
| 2022-04 | cluster_only_3sl | 1.0 | 6772.86 | 0.0 | 0.0 | 0 | 19.59 | 1024.73 | 4019.59 | 8175.56 | 0 |
| 2022-04 | guardrails_completos | 1.0 | 5752.75 | 8.8 | 8.8e-05 | 1 | -8.8 | 849.86 | 3991.2 | 8175.56 | 0 |
| 2020-09 | baseline | 1.0 | 7625.05 | 130.38 | 0.001304 | 2 | -130.38 | 1037.29 | 3869.62 | 7963.86 | 0 |
| 2020-09 | cluster_only_3sl | 1.0 | 7625.05 | 130.38 | 0.001304 | 2 | -130.38 | 1037.29 | 3869.62 | 7963.86 | 0 |
| 2020-09 | guardrails_completos | 1.0 | 6641.51 | 130.38 | 0.001304 | 2 | -130.38 | 1037.29 | 3869.62 | 7963.86 | 0 |
| 2021-08 | baseline | 1.0 | 2852.96 | 134.32 | 0.001343 | 1 | -134.32 | 619.44 | 3865.68 | 7865.68 | 0 |
| 2021-08 | cluster_only_3sl | 1.0 | 2852.96 | 134.32 | 0.001343 | 1 | -134.32 | 619.44 | 3865.68 | 7865.68 | 0 |
| 2021-08 | guardrails_completos | 1.0 | 2307.86 | 134.32 | 0.001343 | 2 | -134.32 | 619.44 | 3865.68 | 7865.68 | 0 |
| 2022-08 | baseline | 1.0 | 7982.11 | 0.0 | 0.0 | 0 | 16.56 | 1200.91 | 4016.56 | 8779.2 | 0 |
| 2022-08 | cluster_only_3sl | 1.0 | 7746.8 | 160.66 | 0.001607 | 2 | -160.66 | 1200.91 | 3839.34 | 8779.2 | 0 |
| 2022-08 | guardrails_completos | 1.0 | 7340.88 | 157.33 | 0.001573 | 2 | -124.18 | 1200.91 | 3875.82 | 8608.01 | 0 |
| 2024-06 | baseline | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2024-06 | cluster_only_3sl | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2024-06 | guardrails_completos | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2024-10 | baseline | 1.0 | 1389.64 | 148.35 | 0.001484 | 3 | -148.35 | 373.39 | 3851.65 | 7999.14 | 0 |
| 2024-10 | cluster_only_3sl | 1.0 | 1389.64 | 148.35 | 0.001484 | 3 | -148.35 | 373.39 | 3851.65 | 7999.14 | 0 |
| 2024-10 | guardrails_completos | 1.0 | 1519.27 | 33.17 | 0.000332 | 2 | -33.17 | 373.39 | 3966.83 | 7999.14 | 0 |


## Peores tramos por drawdown con lotaje 1.0

| month | scenario | lot | net_usd | max_drawdown_usd | max_drawdown_pct | max_drawdown_duration_days | worst_day_usd | best_day_usd | min_daily_limit_margin_usd | min_total_limit_margin_usd | danger_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-03 | cluster_only_3sl | 1.0 | 9266.58 | 294.41 | 0.002944 | 2 | -294.41 | 1894.2 | 3705.59 | 8163.74 | 0 |
| 2024-06 | baseline | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2024-06 | cluster_only_3sl | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2024-06 | guardrails_completos | 1.0 | 806.59 | 266.28 | 0.002663 | 3 | -266.28 | 348.08 | 3733.72 | 7911.71 | 0 |
| 2022-08 | cluster_only_3sl | 1.0 | 7746.8 | 160.66 | 0.001607 | 2 | -160.66 | 1200.91 | 3839.34 | 8779.2 | 0 |
| 2022-08 | guardrails_completos | 1.0 | 7340.88 | 157.33 | 0.001573 | 2 | -124.18 | 1200.91 | 3875.82 | 8608.01 | 0 |
| 2024-10 | baseline | 1.0 | 1389.64 | 148.35 | 0.001484 | 3 | -148.35 | 373.39 | 3851.65 | 7999.14 | 0 |
| 2024-10 | cluster_only_3sl | 1.0 | 1389.64 | 148.35 | 0.001484 | 3 | -148.35 | 373.39 | 3851.65 | 7999.14 | 0 |


## Interpretacion operativa

- `0.6` parece el lotaje mas sano hoy: deja mas distancia psicologica y tecnica frente a limites diarios/totales.

- `1.0` no aparece como quemador en estos meses, pero es menos comodo: aumenta la velocidad del drawdown y exige mas tolerancia a dias negativos.

- Los meses que mas asustan son los que combinan varias perdidas cercanas o recuperaciones lentas, no necesariamente los de peor neto mensual.

- La curva de MAGI no es lineal; hay recuperaciones, pero la experiencia operativa real incluye serruchos. Eso refuerza operar demo/fondeo conservador antes de escalar.

## Recomendacion final

El lotaje `0.6` es la opcion prudente para una funded conservadora inicial. `1.0` debe tratarse como agresivo hasta validar mas meses continuos y la gestion activa de BE/drawdown. MAGI sigue prometedor, pero aun no debe evaluarse solo por net R agregado: la curva diaria y la distancia a limites son la metrica operativa principal.

## Archivos generados

- `reports\magi_daily_breakdown_0_6.csv`

- `reports\magi_daily_breakdown_1_0.csv`

- `reports\magi_equity_curves.csv`

- `reports\magi_drawdown_analysis.csv`

- `reports/charts/equity_curve_2020_03.png`

- `reports/charts/equity_curve_2022_04.png`

- `reports/charts/equity_curve_2020_09.png`

- `reports/charts/equity_curve_2021_08.png`

- `reports/charts/equity_curve_2022_08.png`

- `reports/charts/equity_curve_2024_06.png`

- `reports/charts/equity_curve_2024_10.png`
