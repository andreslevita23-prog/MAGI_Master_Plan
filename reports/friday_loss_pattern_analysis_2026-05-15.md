# Patron de perdidas de viernes en MAGI

Fecha de corte: 2026-05-15

Zona horaria para reglas viernes: America/Bogota (UTC-5).

## Resumen ejecutivo

Conclusion categorizada: **2. Patron parcial: viernes tarde/New York es peor, pero no todo el viernes**. El viernes 15 si fue malo y concentrado en reentradas durante overlap/New York, pero la evidencia historica no confirma que todo viernes sea estructuralmente perdedor. Los viernes tarde muestran riesgo operativo en live y algunos filtros mejoran drawdown, aunque en backtests amplios los filtros viernes pueden recortar bastante rentabilidad.

## 1. Demo/live por dia de la semana

| weekday | trades | tp | sl | be | win_rate | profit_factor | net | avg_r_or_pnl | max_drawdown | worst_loss_streak | best_win_streak | fast_reentries_3h_same_direction | avg_spread_pips |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lunes | 1 | 0 | 1 | 0 | 0.0 | 0.0 | -500.0 | -500.0 | 500.0 | 1 | 0 | 0 | 0.2 |
| martes | 0 | 0 | 0 | 0 |  |  | 0 |  | 0.0 | 0 | 0 | 0 |  |
| miercoles | 1 | 0 | 1 | 0 | 0.0 | 0.0 | -500.0 | -500.0 | 500.0 | 1 | 0 | 0 | 0.2 |
| jueves | 4 | 3 | 1 | 0 | 0.75 | 6.0 | 2500.0 | 625.0 | 500.0 | 1 | 2 | 0 | 0.2 |
| viernes | 11 | 2 | 7 | 1 | 0.2222 | 0.5714 | -1500.0 | -136.363636 | 2500.0 | 3 | 1 | 6 | 0.3364 |


## 2. Viernes live por sesion/franja

| friday_segment | trades | tp | sl | be | win_rate | profit_factor | net | max_drawdown | worst_loss_streak | fast_reentries_3h_same_direction | avg_spread_pips |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| london | 1 | 0 | 0 | 1 |  |  | 0.0 | 0.0 | 0 | 0 | 0.2 |
| overlap | 5 | 2 | 3 | 0 | 0.4 | 1.3333 | 500.0 | 1500.0 | 3 | 3 | 0.28 |
| new_york | 5 | 0 | 4 | 0 | 0.0 | 0.0 | -2000.0 | 2000.0 | 2 | 3 | 0.42 |
| friday_late_after_10co | 1 | 0 | 1 | 0 | 0.0 | 0.0 | -500.0 | 500.0 | 1 | 0 | 1.0 |
| friday_late_after_12co | 0 | 0 | 0 | 0 |  |  | 0 | 0.0 | 0 | 0 |  |


## 3. Escenarios de regla viernes en live

| scenario | trades | tp | sl | be | net | profit_factor | max_drawdown | trades_removed | tp_removed | sl_removed | removed_net | net_delta_vs_baseline | dd_delta_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Friday Rule A - no opens after 12:00 Colombia | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Friday Rule B - no opens after 10:00 Colombia | 16 | 5 | 9 | 1 | 500.0 | 1.1111 | 1500.0 | 1 | 0 | 1 | -500.0 | 500.0 | 0.0 |
| Friday Rule C - max 1 trade per session | 11 | 4 | 6 | 1 | 1000.0 | 1.3333 | 1000.0 | 6 | 1 | 4 | -1000.0 | 1000.0 | -500.0 |
| Friday Rule D - after 1 SL safe until Monday | 10 | 4 | 5 | 1 | 1500.0 | 1.6 | 1000.0 | 7 | 1 | 5 | -1500.0 | 1500.0 | -500.0 |
| Friday Rule E - after 2 SL safe until Monday | 12 | 4 | 7 | 1 | 500.0 | 1.1429 | 1500.0 | 5 | 1 | 3 | -500.0 | 500.0 | 0.0 |
| Friday Rule F - late only manage, no new opens | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |


## 4. Viernes en backtests/simulaciones

| dataset | trades | tp | sl | win_rate | profit_factor | net | avg_r_or_pnl | max_drawdown | worst_loss_streak | fast_reentries_3h_same_direction | avg_spread_pips |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | 79 | 53 | 26 | 0.6709 | 2.5857 | 53.826905 | 0.681353 | 7.516361 | 5 | 25 |  |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | 912 | 677 | 235 | 0.7423 | 3.8711 | 802.029719 | 0.879419 | 7.516361 | 5 | 160 |  |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | 17 | 13 | 4 | 0.7647 | 4.8267 | 14.689472 | 0.864087 | 1.439166 | 1 | 0 |  |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | 1607 | 966 | 640 | 0.6015 | 2.9008 | 1169.57 | 0.727797 | 8.0 | 7 | 480 | 0.3009 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | 1377 | 555 | 822 | 0.4031 | 1.2612 | 204.25 | 0.14833 | 147.44 | 97 | 0 |  |


## 5. Filtros viernes sobre backtests/simulaciones

| dataset | scenario | trades | tp | sl | net | profit_factor | max_drawdown | trades_removed | tp_removed | sl_removed | net_delta_vs_baseline | dd_delta_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Baseline | 278 | 183 | 95 | 176.727492 | 2.4272 | 7.516361 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule A - no opens after 12:00 Colombia | 244 | 163 | 81 | 161.513684 | 2.5307 | 7.481972 | 34 | 20 | 14 | -15.213808 | -0.034389 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule B - no opens after 10:00 Colombia | 244 | 163 | 81 | 161.513684 | 2.5307 | 7.481972 | 34 | 20 | 14 | -15.213808 | -0.034389 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule C - max 1 trade per session | 221 | 145 | 76 | 137.807135 | 2.3907 | 7.481972 | 57 | 38 | 19 | -38.920357 | -0.034389 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule D - after 1 SL safe until Monday | 226 | 152 | 74 | 152.417653 | 2.5813 | 7.481972 | 52 | 31 | 21 | -24.309839 | -0.034389 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule E - after 2 SL safe until Monday | 238 | 160 | 78 | 160.387778 | 2.5775 | 7.481972 | 40 | 23 | 17 | -16.339714 | -0.034389 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Friday Rule F - late only manage, no new opens | 244 | 163 | 81 | 161.513684 | 2.5307 | 7.481972 | 34 | 20 | 14 | -15.213808 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Baseline | 3346 | 2440 | 906 | 2804.002544 | 3.593 | 7.516361 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule A - no opens after 12:00 Colombia | 2964 | 2147 | 817 | 2449.36199 | 3.5091 | 7.481972 | 382 | 293 | 89 | -354.640554 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule B - no opens after 10:00 Colombia | 2964 | 2147 | 817 | 2449.36199 | 3.5091 | 7.481972 | 382 | 293 | 89 | -354.640554 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule C - max 1 trade per session | 2895 | 2105 | 790 | 2398.365835 | 3.5556 | 7.481972 | 451 | 335 | 116 | -405.636709 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule D - after 1 SL safe until Monday | 2945 | 2149 | 796 | 2462.67725 | 3.6022 | 7.481972 | 401 | 291 | 110 | -341.325294 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule E - after 2 SL safe until Monday | 3166 | 2316 | 850 | 2673.988629 | 3.6392 | 7.481972 | 180 | 124 | 56 | -130.013915 | -0.034389 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Friday Rule F - late only manage, no new opens | 2964 | 2147 | 817 | 2449.36199 | 3.5091 | 7.481972 | 382 | 293 | 89 | -354.640554 | -0.034389 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Baseline | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule A - no opens after 12:00 Colombia | 70 | 54 | 16 | 62.70341 | 4.2781 | 5.056002 | 9 | 6 | 3 | -6.324325 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule B - no opens after 10:00 Colombia | 70 | 54 | 16 | 62.70341 | 4.2781 | 5.056002 | 9 | 6 | 3 | -6.324325 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule C - max 1 trade per session | 75 | 57 | 18 | 65.590472 | 4.0969 | 5.056002 | 4 | 3 | 1 | -3.437263 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule D - after 1 SL safe until Monday | 75 | 57 | 18 | 64.366736 | 4.0391 | 5.056002 | 4 | 3 | 1 | -4.660999 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule E - after 2 SL safe until Monday | 79 | 60 | 19 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Friday Rule F - late only manage, no new opens | 70 | 54 | 16 | 62.70341 | 4.2781 | 5.056002 | 9 | 6 | 3 | -6.324325 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Baseline | 6539 | 3922 | 2615 | 4669.93 | 2.8517 | 9.0 | 0 | 0 | 0 | 0.0 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule A - no opens after 12:00 Colombia | 5866 | 3526 | 2338 | 4207.14 | 2.8662 | 9.0 | 673 | 396 | 277 | -462.79 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule B - no opens after 10:00 Colombia | 5866 | 3526 | 2338 | 4207.14 | 2.8662 | 9.0 | 673 | 396 | 277 | -462.79 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule C - max 1 trade per session | 5621 | 3384 | 2235 | 4018.24 | 2.8698 | 10.03 | 918 | 538 | 380 | -651.69 | 1.03 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule D - after 1 SL safe until Monday | 5498 | 3307 | 2189 | 3912.36 | 2.8593 | 9.0 | 1041 | 615 | 426 | -757.57 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule E - after 2 SL safe until Monday | 5867 | 3543 | 2322 | 4232.71 | 2.8953 | 9.0 | 672 | 379 | 293 | -437.22 | 0.0 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Friday Rule F - late only manage, no new opens | 5866 | 3526 | 2338 | 4207.14 | 2.8662 | 9.0 | 673 | 396 | 277 | -462.79 | 0.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Baseline | 4907 | 2117 | 2787 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0.0 | 0.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule A - no opens after 12:00 Colombia | 4523 | 1931 | 2589 | 778.44 | 1.3158 | 119.09 | 384 | 186 | 198 | -150.6 | -15.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule B - no opens after 10:00 Colombia | 4523 | 1931 | 2589 | 778.44 | 1.3158 | 119.09 | 384 | 186 | 198 | -150.6 | -15.0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule C - max 1 trade per session | 3652 | 1613 | 2036 | 744.06 | 1.3831 | 83.88 | 1255 | 504 | 751 | -184.98 | -50.21 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule D - after 1 SL safe until Monday | 3864 | 1839 | 2022 | 1170.03 | 1.6078 | 77.88 | 1043 | 278 | 765 | 240.99 | -56.21 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule E - after 2 SL safe until Monday | 3937 | 1862 | 2072 | 1165.64 | 1.5917 | 80.88 | 970 | 255 | 715 | 236.6 | -53.21 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Friday Rule F - late only manage, no new opens | 4523 | 1931 | 2589 | 778.44 | 1.3158 | 119.09 | 384 | 186 | 198 | -150.6 | -15.0 |


## 6. Respuestas directas

- **El viernes 15 fue coherente con un riesgo operativo real**, pero no basta para afirmar que todos los viernes son malos.

- **MAGI no pierde historicamente mas todos los viernes de forma clara** en todos los datasets. Hay datasets donde viernes sigue siendo rentable.

- **Viernes tarde/New York si es la zona que mas merece guardrail**, especialmente despues de SL o con spread deteriorado.

- **El patron aparece muy fuerte en demo/live reciente** y parcialmente en simulaciones via drawdown/filtros, pero no como ley universal.

- **La muestra live es insuficiente para apagar todo viernes**, pero suficiente para disenar una regla preventiva de viernes tarde y perdida agrupada.

- **Friday Rule F equivale a Rule A en los datos actuales**, porque se modela como no abrir despues de 12:00 Colombia y no habia eventos de gestion separados en los CSV historicos.


## 7. Recomendacion

Antes del 5 de junio conviene implementar una regla viernes prudente, pero no un bloqueo total de viernes. La mejor direccion es: viernes despues de 12:00 Colombia no abrir nuevas operaciones si ya hubo SL en el dia, y activar SAFE_MODE tras 2 SL de viernes. Tambien conviene limitar viernes tarde a gestion de posiciones abiertas.

- **Melchor:** debe evaluar `friday_risk`, `friday_late`, `friday_loss_count`, `spread_deteriorated`.

- **CEO-MAGI/backend:** debe persistir estado diario y convertir el bloqueo en HOLD/SAFE_MODE trazable.

- **Bot B:** no debe decidir la regla; solo respetar payload y proteger contra duplicados.

- **Dashboard/auditoria:** mostrar `friday_guardrail_active`, motivo y hora de desbloqueo.


## 8. Archivos generados

- `reports\friday_by_weekday_summary.csv`

- `reports\friday_session_breakdown.csv`

- `reports\friday_filter_scenarios.csv`

- `reports\friday_loss_pattern_analysis_2026-05-15.md`
