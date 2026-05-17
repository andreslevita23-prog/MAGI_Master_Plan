# Analisis de clusters de reentrada MAGI

Fecha de corte: 2026-05-15

Definicion: mismo simbolo, misma direccion, gap cierre->apertura <= 180 minutos, mismo dia operativo Colombia y misma sesion o sesion inmediata posterior.

## Resumen ejecutivo

La hipotesis queda **parcialmente confirmada con un matiz importante**: en live/demo, el dano visible no vino de clusters que empiecen estrictamente con SL, sino de clusters que, una vez dentro, acumulan 2-3 SL consecutivos en la misma direccion/contexto. Los historicos muestran que las rachas iniciadas con TP suelen aportar edge y que incluso muchas rachas iniciadas con SL se recuperan. Por eso un cooldown ciego destruiria profit; la regla mas sana antes del 5 de junio es detectar 2 SL consecutivos o deterioro dentro del cluster, no bloquear toda reentrada.

## A. Clusters live/demo

| cluster_id | start_time | end_time | direction | session_start | trades | sequence | first_result | net | max_drawdown | max_consecutive_sl | started_tp_and_kept_winning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| live_demo_organic_normalized_usd::cluster_0001 | 2026-05-07T06:20:21+00:00 | 2026-05-07T16:08:29+00:00 | BUY | london | 2 | TP-SL | TP | 500.0 | 500.0 | 1 | False |
| live_demo_organic_normalized_usd::cluster_0002 | 2026-05-08T09:00:21+00:00 | 2026-05-08T18:27:22+00:00 | BUY | overlap | 4 | TP-SL-SL-SAFETY_PARTIAL | TP | 0.0 | 1000.0 | 2 | False |
| live_demo_organic_normalized_usd::cluster_0003 | 2026-05-14T12:00:29+00:00 | 2026-05-15T00:02:05+00:00 | SELL | overlap | 2 | TP-TP | TP | 2000.0 | 0.0 | 0 | True |
| live_demo_organic_normalized_usd::cluster_0004 | 2026-05-15T05:00:30+00:00 | 2026-05-15T17:10:44+00:00 | SELL | london | 7 | BE-SL-SL-SL-TP-SL-SL | BE | -1500.0 | 1500.0 | 3 | False |


## B. Resumen por dataset

| dataset | clusters | sl_start_clusters | sl_start_positive | sl_start_negative | sl_start_avg_net | sl_start_recovery_rate | first_sl_then_sl | first_sl_then_tp | tp_start_clusters | tp_start_kept_winning | tp_start_positive | tp_start_negative | tp_start_avg_net | clusters_2sl_consecutive | clusters_3sl_consecutive | clusters_gt3sl_consecutive | avg_damage_2sl_clusters | max_damage_cluster |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| live_demo_organic_normalized_usd | 4 | 0 | 0 | 0 |  |  | 0 | 0 | 3 | 1 | 2 | 0 | 833.333333 | 2 | 1 | 0 | -750.0 | -1500.0 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | 47 | 22 | 16 | 6 | 0.742722 | 0.7273 | 6 | 16 | 25 | 17 | 24 | 1 | 4.842526 | 14 | 5 | 2 | 1.067356 | -3.997379 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | 763 | 280 | 214 | 66 | 0.798899 | 0.7643 | 51 | 229 | 483 | 348 | 468 | 15 | 3.409274 | 104 | 24 | 7 | 0.159207 | -5.144565 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | 0 | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 |  | 0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | 1470 | 762 | 539 | 163 | 1.219291 | 0.7073 | 240 | 522 | 708 | 404 | 667 | 25 | 3.493545 | 442 | 125 | 32 | 1.169525 | -6.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | 0 | 0 | 0 | 0 |  |  | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 | 0 | 0 |  | 0 |


Lectura clave del resumen: en live/demo hay 0 clusters que empiezan con SL bajo la definicion estricta. El cluster danino principal fue `BE-SL-SL-SL-TP-SL-SL`. En historicos, los clusters que empiezan con TP son claramente mas saludables que los que empiezan con SL, pero los clusters SL-start tambien se recuperan con frecuencia alta.



## C. Simulaciones de reglas en live/demo

| scenario | trades | tp | sl | be | net | profit_factor | max_drawdown | trades_removed | tp_removed | sl_removed | removed_net | net_delta_vs_baseline | dd_delta_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Rule 1 - block after first SL in cluster | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Rule 2 - after 2 consecutive SL safe 180m | 12 | 4 | 7 | 1 | 500.0 | 1.1429 | 1500.0 | 5 | 1 | 3 | -500.0 | 500.0 | 0.0 |
| Rule 3 - after 3 consecutive SL safe next session/day | 14 | 4 | 8 | 1 | 0.0 | 1.0 | 1500.0 | 3 | 1 | 2 | 0.0 | 0.0 | 0.0 |
| Rule 4 - first TP max 1 reentry | 15 | 5 | 9 | 1 | 500.0 | 1.1111 | 1500.0 | 2 | 0 | 1 | -500.0 | 500.0 | 0.0 |
| Rule 5 - first SL one reentry, block if fails | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Rule 6 - TP clusters continue, SL clusters restrictive | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |


## D. Simulaciones de reglas en backtests/simulaciones

| dataset | scenario | trades | tp | sl | net | profit_factor | max_drawdown | trades_removed | tp_removed | sl_removed | removed_net | net_delta_vs_baseline | dd_delta_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Baseline | 278 | 183 | 95 | 176.727492 | 2.4272 | 7.516361 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Rule 1 - block after first SL in cluster | 198 | 133 | 65 | 131.652459 | 2.5523 | 5.629531 | 80 | 50 | 30 | 45.075033 | -45.075033 | -1.88683 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Rule 2 - after 2 consecutive SL safe 180m | 222 | 150 | 72 | 150.681782 | 2.6058 | 8.841719 | 56 | 33 | 23 | 26.04571 | -26.04571 | 1.325358 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Rule 6 - TP clusters continue, SL clusters restrictive | 220 | 149 | 71 | 150.76559 | 2.6283 | 6.208085 | 58 | 34 | 24 | 25.961902 | -25.961902 | -1.308276 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Baseline | 3346 | 2440 | 906 | 2804.002544 | 3.593 | 7.516361 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Rule 1 - block after first SL in cluster | 2723 | 1978 | 745 | 2232.87108 | 3.5116 | 7.449667 | 623 | 462 | 161 | 571.131464 | -571.131464 | -0.066694 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Rule 2 - after 2 consecutive SL safe 180m | 3128 | 2297 | 831 | 2662.242586 | 3.6995 | 8.841719 | 218 | 143 | 75 | 141.759958 | -141.759958 | 1.325358 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Rule 6 - TP clusters continue, SL clusters restrictive | 3003 | 2207 | 796 | 2550.152407 | 3.6886 | 6.843587 | 343 | 233 | 110 | 253.850137 | -253.850137 | -0.672774 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Baseline | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Rule 1 - block after first SL in cluster | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Rule 2 - after 2 consecutive SL safe 180m | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Rule 6 - TP clusters continue, SL clusters restrictive | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Baseline | 6539 | 3922 | 2615 | 4669.93 | 2.8517 | 9.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Rule 1 - block after first SL in cluster | 4527 | 2661 | 1864 | 3007.31 | 2.6799 | 8.45 | 2012 | 1261 | 751 | 1662.62 | -1662.62 | -0.55 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Rule 2 - after 2 consecutive SL safe 180m | 5546 | 3320 | 2224 | 3900.92 | 2.828 | 9.0 | 993 | 602 | 391 | 769.01 | -769.01 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Rule 6 - TP clusters continue, SL clusters restrictive | 5289 | 3183 | 2104 | 3762.5 | 2.865 | 8.01 | 1250 | 739 | 511 | 907.43 | -907.43 | -0.99 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Baseline | 4907 | 2117 | 2787 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Rule 1 - block after first SL in cluster | 4907 | 2117 | 2787 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Rule 2 - after 2 consecutive SL safe 180m | 4907 | 2117 | 2787 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Rule 6 - TP clusters continue, SL clusters restrictive | 4907 | 2117 | 2787 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |


## E. Respuestas directas

- **El verdadero problema no es reentrar siempre:** el problema es reentrar sin freno despues de perdida dentro del mismo contexto.

- **Las reentradas despues de ganancia parecen saludables en historicos amplios:** muchas rachas iniciadas con TP terminan positivas y sostienen una parte importante del profit.

- **En live/demo el cluster critico fue `BE-SL-SL-SL-TP-SL-SL`:** llego a 3 SL consecutivos y termino -1500 USD normalizados.

- **Clusters con 3 o mas SL consecutivos:** live/demo 1 cluster con 3 SL; stress 5 clusters con 3+ SL y 2 con mas de 3; CEO v3 decisions 24 con 3+ y 7 con mas de 3; scenario C 125 con 3+ y 32 con mas de 3.

- **SAFE_MODE tras 2 SL consecutivos es mas defendible que bloquear despues de 1 SL:** en live mejora +500 USD, pero en historicos reduce neto; debe ser contextual, no global.

- **Rule 6 es una direccion conceptual, no una regla lista tal cual:** permitir continuidad si el cluster inicia con TP; ser restrictivo si el cluster empieza o deriva en SL consecutivos.


## F. Recomendacion antes del 5 de junio

Implementar una regla de cluster en capa de riesgo, no en ejecucion:

- **Melchor:** detectar `cluster_started_with_sl`, `cluster_consecutive_sl`, `same_direction_reentry_cluster` y recomendar BLOCK/HOLD.

- **CEO-MAGI/backend:** mantener estado del cluster por simbolo/direccion/sesion y aplicar SAFE_MODE trazable.

- **Bot B:** no debe decidir clusters; solo ejecutar o no segun payload y mantener guardrails.

- **Dashboard/auditoria:** mostrar cluster activo, secuencia, bloqueo y regla aplicada.


## G. Archivos generados

- `reports\reentry_cluster_summary.csv`

- `reports\reentry_cluster_trades.csv`

- `reports\reentry_cluster_rule_scenarios.csv`

- `reports\reentry_cluster_sequence_analysis_2026-05-15.md`
