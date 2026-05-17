# Hipotesis de reentradas post-SL en MAGI

Fecha de corte: 2026-05-15

Modelo live normalizado: TP = +1000 USD, SL = -500 USD, BE = 0 USD.

## Resumen ejecutivo

La hipotesis es **verdadera para la demo/live reciente, pero solo parcialmente confirmada por los backtests**. En vivo, el dano mas visible del viernes 15 si vino de secuencias de reentrada rapida en la misma direccion despues de SL. Se detectaron 6 reentradas organicas en la misma direccion dentro de 3 horas de un SL previo; 4 terminaron en SL, 1 terminaron en TP y 1 fue safety/parcial. Bajo el modelo normalizado, ese grupo tuvo neto -1000 USD. Sin embargo, en artefactos historicos amplios, muchas reentradas rapidas fueron ganadoras; por eso un cooldown global despues de cada SL puede mejorar estabilidad pero tambien destruir parte del edge.

## Respuesta directa

- **La hipotesis es verdadera en live/demo:** el cluster mas danino observado tiene forma SL -> reentrada rapida -> SL.

- **No queda demostrada como verdad universal historica:** en varios backtests las reentradas rapidas post-SL fueron netamente positivas.

- **Conclusion operativa:** no conviene bloquear toda reentrada despues de 1 SL de forma ciega; si conviene disenar una capa de riesgo que detecte clusters: misma direccion, misma sesion/contexto, SL recientes, spread deteriorado, viernes/tarde o 2-3 perdidas agrupadas.

## 1. Evidencia live/demo

Operaciones organicas cerradas analizadas: 17. Reentradas rapidas misma direccion post-SL: 6. SL dentro de esas reentradas: 4. TP dentro de esas reentradas: 1. Safety/parcial dentro de esas reentradas: 1. Neto normalizado de esas reentradas: -1000.0 USD.

| ticket | direction | entry_time | exit_time | session | result | pnl_normalized | minutes_after_previous_sl | same_direction_as_previous_sl | within_3h_after_previous_sl | fast_same_direction_reentry |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8515425225 | BUY | 2026-05-06T15:00:20+00:00 | 2026-05-06T16:51:44+00:00 | new_york | SL | -500 |  | False | False | False |
| 8523501566 | BUY | 2026-05-07T06:20:21+00:00 | 2026-05-07T07:15:20+00:00 | london | TP | 1000 | 808.62 | True | False | False |
| 8525528485 | BUY | 2026-05-07T08:00:21+00:00 | 2026-05-07T16:08:29+00:00 | london | SL | -500 |  | False | False | False |
| 8547574064 | BUY | 2026-05-08T09:00:21+00:00 | 2026-05-08T13:32:01+00:00 | overlap | TP | 1000 | 1011.87 | True | False | False |
| 8553314033 | BUY | 2026-05-08T13:35:21+00:00 | 2026-05-08T14:00:57+00:00 | new_york | SL | -500 |  | False | False | False |
| 8554125215 | BUY | 2026-05-08T14:05:21+00:00 | 2026-05-08T14:10:39+00:00 | new_york | SL | -500 | 4.4 | True | True | True |
| 8554497278 | BUY | 2026-05-08T14:15:21+00:00 | 2026-05-08T18:27:22+00:00 | new_york | SAFETY_PARTIAL | 0.0 | 4.7 | True | True | True |
| 8569477584 | BUY | 2026-05-11T09:00:08+00:00 | 2026-05-11T11:56:27+00:00 | overlap | SL | -500 |  | False | False | False |
| 8632100564 | SELL | 2026-05-14T12:00:29+00:00 | 2026-05-14T14:57:55+00:00 | overlap | TP | 1000 | 4324.03 | False | False | False |
| 8636685436 | SELL | 2026-05-14T15:00:29+00:00 | 2026-05-15T00:02:05+00:00 | new_york | TP | 1000 |  | False | False | False |
| 8645768127 | SELL | 2026-05-15T05:00:30+00:00 | 2026-05-15T07:11:36+00:00 | london | BE | 0 |  | False | False | False |
| 8650330965 | SELL | 2026-05-15T09:00:30+00:00 | 2026-05-15T10:23:59+00:00 | overlap | SL | -500 |  | False | False | False |
| 8652091231 | SELL | 2026-05-15T10:25:30+00:00 | 2026-05-15T10:45:14+00:00 | overlap | SL | -500 | 1.52 | True | True | True |
| 8652574043 | SELL | 2026-05-15T10:50:30+00:00 | 2026-05-15T10:52:15+00:00 | overlap | SL | -500 | 5.27 | True | True | True |
| 8652728652 | SELL | 2026-05-15T10:55:30+00:00 | 2026-05-15T11:44:58+00:00 | overlap | TP | 1000 | 3.25 | True | True | True |
| 8655084624 | SELL | 2026-05-15T13:00:30+00:00 | 2026-05-15T14:17:26+00:00 | new_york | SL | -500 |  | False | False | False |
| 8659678120 | SELL | 2026-05-15T16:00:30+00:00 | 2026-05-15T17:10:44+00:00 | new_york | SL | -500 | 103.07 | True | True | True |


### Cooldowns sobre demo/live

| scenario | trades | wins | losses | be | net | profit_factor | max_drawdown | trades_removed | winning_trades_removed | losing_trades_removed | net_delta_vs_baseline | fast_same_direction_reentries | fast_reentry_losses | fast_reentry_wins | fast_reentry_net |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 17 | 5 | 10 | 1 | 0.0 | 1.0 | 1500.0 | 0 | 0 | 0 | 0.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown A - 60m same direction after 1 SL | 12 | 4 | 7 | 1 | 500 | 1.1429 | 1500.0 | 5 | 1 | 3 | 500.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown B - 90m same direction after 1 SL | 12 | 4 | 7 | 1 | 500 | 1.1429 | 1500.0 | 5 | 1 | 3 | 500.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown C - 180m same direction after 1 SL | 11 | 4 | 6 | 1 | 1000 | 1.3333 | 1000.0 | 6 | 1 | 4 | 1000.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown D - after 2 SL same direction/session block 3h | 13 | 4 | 8 | 1 | 0 | 1.0 | 2000.0 | 4 | 1 | 2 | 0.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown E - after 3 SL day safe until next day | 14 | 4 | 8 | 1 | 0.0 | 1.0 | 1500.0 | 3 | 1 | 2 | 0.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown F - same direction until session change | 11 | 4 | 6 | 1 | 1000 | 1.3333 | 1000.0 | 6 | 1 | 4 | 1000.0 | 6 | 4 | 1 | -1000.0 |
| Cooldown G - same direction until next day | 10 | 4 | 5 | 1 | 1500 | 1.6 | 1000.0 | 7 | 1 | 5 | 1500.0 | 6 | 4 | 1 | -1000.0 |


Mejor escenario live por neto: **Cooldown G - same direction until next day**, neto 1500 vs baseline, delta 1500.0.



Lectura live: los cooldowns de 60/90 minutos habrian mejorado el resultado en +500 USD normalizados; 180 minutos o bloqueo hasta cambio de sesion habrian mejorado +1000 USD; bloqueo hasta siguiente dia habria mejorado +1500 USD, pero este ultimo es demasiado agresivo para adoptarlo sin mas muestra.

## 2. Evidencia historica del simulador/backtests

Se analizaron artefactos historicos existentes con operaciones o decisiones ejecutables. Las metricas historicas usan R/realized_R cuando existe, no USD normalizado.

| dataset | scenario | trades | wins | losses | win_rate | net | profit_factor | max_drawdown | trades_removed | winning_trades_removed | losing_trades_removed | net_delta_vs_baseline | dd_delta_vs_baseline | fast_same_direction_reentries | fast_reentry_losses | fast_reentry_wins | fast_reentry_net |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Baseline | 278 | 183 | 95 | 0.6583 | 176.727492 | 2.4272 | 7.516361 | 0 | 0 | 0 | 0.0 | 0.0 | 79 | 25 | 54 | 56.076095 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Cooldown A - 60m same direction after 1 SL | 185 | 128 | 57 | 0.6919 | 135.345905 | 2.8166 | 7.929985 | 93 | 55 | 38 | -41.381587 | 0.413624 | 79 | 25 | 54 | 56.076095 |
| artifacts/ceo_magi_v3/stress_months_trade_detail.csv | Cooldown C - 180m same direction after 1 SL | 157 | 112 | 45 | 0.7134 | 124.179188 | 3.1129 | 5.176693 | 121 | 71 | 50 | -52.548304 | -2.339668 | 79 | 25 | 54 | 56.076095 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Baseline | 79 | 60 | 19 | 0.7595 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Cooldown A - 60m same direction after 1 SL | 79 | 60 | 19 | 0.7595 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |
| artifacts/ceo_magi_v3/random_3_months_trade_audit.csv | Cooldown C - 180m same direction after 1 SL | 79 | 60 | 19 | 0.7595 | 69.027735 | 4.2065 | 5.056002 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Baseline | 3346 | 2440 | 906 | 0.7292 | 2804.002544 | 3.593 | 7.516361 | 0 | 0 | 0 | 0.0 | 0.0 | 628 | 149 | 479 | 600.988945 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Cooldown A - 60m same direction after 1 SL | 2697 | 1974 | 723 | 0.7319 | 2267.287992 | 3.6538 | 8.829939 | 649 | 466 | 183 | -536.714552 | 1.313578 | 628 | 149 | 479 | 600.988945 |
| artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv | Cooldown C - 180m same direction after 1 SL | 2464 | 1816 | 648 | 0.737 | 2098.007818 | 3.7413 | 8.275674 | 882 | 624 | 258 | -705.994726 | 0.759313 | 628 | 149 | 479 | 600.988945 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Baseline | 6539 | 3922 | 2615 | 0.6 | 4669.93 | 2.8517 | 9.0 | 0 | 0 | 0 | 0.0 | 0.0 | 2000 | 669 | 1194 | 1797.3 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Cooldown A - 60m same direction after 1 SL | 4605 | 2735 | 1868 | 0.5942 | 3141.73 | 2.7525 | 9.62 | 1934 | 1187 | 747 | -1528.2 | 0.62 | 2000 | 669 | 1194 | 1797.3 |
| artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv | Cooldown C - 180m same direction after 1 SL | 3939 | 2349 | 1588 | 0.5966 | 2683.23 | 2.7662 | 9.0 | 2600 | 1573 | 1027 | -1986.7 | 0.0 | 2000 | 669 | 1194 | 1797.3 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Baseline | 4907 | 2117 | 2787 | 0.4317 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Cooldown A - 60m same direction after 1 SL | 4907 | 2117 | 2787 | 0.4317 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |
| data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv | Cooldown C - 180m same direction after 1 SL | 4907 | 2117 | 2787 | 0.4317 | 929.04 | 1.3496 | 134.09 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 0 | 0 |


### Lectura historica clave

- `stress_months_trade_detail.csv`: hubo 79 reentradas rapidas, 54 ganadoras y 25 perdedoras; neto positivo +56.08R. Cooldown C mejora PF y drawdown, pero reduce neto total.

- `ceo_magi_v3_decisions.csv`: hubo 628 reentradas rapidas, 479 ganadoras y 149 perdedoras; neto positivo +600.99R. Un cooldown global reduce mucho el beneficio total.

- `scenario_c_realistic_trades.csv`: hubo 2000 reentradas rapidas, 1194 ganadoras y 669 perdedoras; neto positivo +1797.3R. La variante SAFE_MODE mejora drawdown/PF, pero tambien recorta neto.

- `random_3_months_trade_audit.csv` y `simulated_trades_050.csv`: no mostraron reentradas rapidas detectables con este criterio/formato, asi que no aportan evidencia a favor del patron.


La tabla completa por escenario esta en `reports/reentry_cooldown_simulation_summary.csv`.

## 3. Conclusiones

- La hipotesis live no es absoluta: no todas las perdidas vienen de reentradas, pero el cluster mas danino si tiene esa forma.

- En live, las reentradas rapidas misma direccion explican 4 SL directos, equivalentes a -2000 USD brutos normalizados. Como tambien hubo 1 TP de +1000 USD, el dano neto del grupo fue -1000 USD.

- El cooldown live mas rentable fue bloqueo misma direccion hasta siguiente dia (+1500 USD), pero es demasiado restrictivo para convertirlo directamente en regla productiva.

- El cooldown live mas razonable parece 180 minutos o hasta cambio de sesion, porque habria evitado 4 SL y perdido 1 TP, mejorando +1000 USD y reduciendo max drawdown de 1500 a 1000 USD.

- La evidencia historica evita una conclusion simplista: las reentradas rapidas no son inherentemente malas. En los backtests grandes, muchas reentradas post-SL aportaron beneficio neto.

- Por tanto, la mejora recomendada no es `despues de cualquier SL no operar mas`, sino un guardrail contextual: misma direccion + misma sesion/contexto + SL reciente + deterioro operativo, o SAFE_MODE tras 2-3 SL agrupados.

- Conviene planear esto antes del 5 de junio, pero como capa de riesgo en Melchor/CEO-MAGI/backend, no en Bot B. Bot B debe seguir siendo ejecutor/guardrail, no cerebro de cooldown.

## 4. Donde implementarlo si se aprueba

- **Melchor:** lugar natural para bloquear por riesgo contextual: `recent_sl_same_direction`, `session_loss_cluster`, `daily_loss_count`, `friday_risk`.

- **CEO-MAGI/backend:** debe conservar estado entre decisiones y decidir si respeta el bloqueo, degrada a HOLD o activa SAFE_MODE.

- **Bot B:** solo deberia mantener guardrails de ejecucion: no duplicar, no operar decision vieja, respetar payload. No debe decidir cooldown estrategico.

- **Dashboard/auditoria:** mostrar `cooldown_active`, `cooldown_reason`, `blocked_until`, `previous_sl_ticket`.

## 5. Archivos generados

- `reports\reentry_cooldown_live_trades.csv`

- `reports\reentry_cooldown_simulation_summary.csv`

- `reports\reentry_cooldown_equity_comparison.csv`

- `reports\reentry_cooldown_hypothesis_2026-05-15.md`
