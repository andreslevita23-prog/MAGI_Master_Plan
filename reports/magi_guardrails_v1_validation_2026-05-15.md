# Validacion MAGI Guardrails v1

Fecha de corte: 2026-05-15

No se modifica codigo operativo. Simulacion offline sobre artefactos historicos.

## Meses usados

- Meses de estres usados: 2020-03, 2022-04.

- Mes excluido: 2026-04 por dataset incompleto.

- Meses aleatorios no consecutivos con seed=42: 2020-09, 2021-08, 2022-08, 2024-06, 2024-10.

## Limitaciones de datos

- BE automatico `MFE >= 0.8R`: no se pudo simular objetivamente porque los artefactos no guardan MFE/MAE intratrade por operacion. Queda marcado como `not_simulated_no_mfe`.

- BE contextual: no simulado por la misma razon y por falta de contexto completo.

- News/macro guardrail: no hay calendario de noticias operable en estos artefactos. Queda como `placeholder_no_calendar`.

- Los guardrails simulados objetivamente son cluster toxico, friday guardrail y memoria operativa derivada.

## Stress months sin 2026-04

| group | scenario | operations | blocked | tp | sl | win_rate | profit_factor | net_r | avg_r | max_drawdown_r | saved_sl | sacrificed_tp | net_delta_vs_baseline_r | months_improved | months_worsened | lot_0_6_net_usd | lot_0_6_violated_daily | lot_0_6_violated_total | lot_1_0_net_usd | lot_1_0_violated_daily | lot_1_0_violated_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stress_ex_2026_04 | baseline | 275 | 0 | 182 | 93 | 0.661818 | 2.465929 | 177.692791 | 0.646156 | 7.516361 | 0 | 0 | 0.0 | 0 | 0 | 10661.57 | False | False | 17769.28 | False | False |
| stress_ex_2026_04 | guardrails_v1_friday_sl1 | 191 | 84 | 136 | 55 | 0.712042 | 3.08314 | 149.619564 | 0.783349 | 7.268688 | 38 | 46 | -28.073227 | 0 | 2 | 8977.17 | False | False | 14961.96 | False | False |
| stress_ex_2026_04 | guardrails_v1_friday_sl2 | 191 | 84 | 136 | 55 | 0.712042 | 3.08314 | 149.619564 | 0.783349 | 7.268688 | 38 | 46 | -28.073227 | 0 | 2 | 8977.17 | False | False | 14961.96 | False | False |
| stress_ex_2026_04 | cluster_only_2sl | 219 | 56 | 152 | 67 | 0.694064 | 2.83032 | 160.317505 | 0.732043 | 7.268688 | 26 | 30 | -17.375286 | 0 | 2 | 9619.05 | False | False | 16031.75 | False | False |
| stress_ex_2026_04 | cluster_only_3sl | 245 | 30 | 163 | 82 | 0.665306 | 2.500693 | 160.394452 | 0.654671 | 6.9748 | 11 | 19 | -17.298339 | 1 | 1 | 9623.67 | False | False | 16039.45 | False | False |
| stress_ex_2026_04 | friday_only_sl1 | 234 | 41 | 159 | 75 | 0.679487 | 2.665555 | 162.713576 | 0.695357 | 7.481972 | 18 | 23 | -14.979215 | 0 | 2 | 9762.81 | False | False | 16271.36 | False | False |
| stress_ex_2026_04 | friday_only_sl2 | 234 | 41 | 159 | 75 | 0.679487 | 2.665555 | 162.713576 | 0.695357 | 7.481972 | 18 | 23 | -14.979215 | 0 | 2 | 9762.81 | False | False | 16271.36 | False | False |


## Cinco meses aleatorios no consecutivos

| group | scenario | operations | blocked | tp | sl | win_rate | profit_factor | net_r | avg_r | max_drawdown_r | saved_sl | sacrificed_tp | net_delta_vs_baseline_r | months_improved | months_worsened | lot_0_6_net_usd | lot_0_6_violated_daily | lot_0_6_violated_total | lot_1_0_net_usd | lot_1_0_violated_daily | lot_1_0_violated_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_5_nonconsecutive | baseline | 248 | 0 | 180 | 68 | 0.725806 | 3.833393 | 206.563456 | 0.832917 | 4.949009 | 0 | 0 | 0.0 | 0 | 0 | 12393.81 | False | False | 20656.35 | False | False |
| random_5_nonconsecutive | guardrails_v1_friday_sl1 | 225 | 23 | 164 | 61 | 0.728889 | 3.826586 | 186.161031 | 0.827382 | 4.182031 | 7 | 16 | -20.402425 | 1 | 3 | 11169.66 | False | False | 18616.1 | False | False |
| random_5_nonconsecutive | guardrails_v1_friday_sl2 | 225 | 23 | 164 | 61 | 0.728889 | 3.826586 | 186.161031 | 0.827382 | 4.182031 | 7 | 16 | -20.402425 | 1 | 3 | 11169.66 | False | False | 18616.1 | False | False |
| random_5_nonconsecutive | cluster_only_2sl | 240 | 8 | 175 | 65 | 0.729167 | 3.91997 | 201.696276 | 0.840401 | 4.182031 | 3 | 5 | -4.86718 | 0 | 2 | 12101.78 | False | False | 20169.63 | False | False |
| random_5_nonconsecutive | cluster_only_3sl | 245 | 3 | 178 | 67 | 0.726531 | 3.848212 | 204.210381 | 0.833512 | 5.529876 | 1 | 2 | -2.353075 | 0 | 1 | 12252.62 | False | False | 20421.04 | False | False |
| random_5_nonconsecutive | friday_only_sl1 | 233 | 15 | 169 | 64 | 0.725322 | 3.741146 | 191.028211 | 0.819864 | 4.949009 | 4 | 11 | -15.535245 | 1 | 3 | 11461.69 | False | False | 19102.82 | False | False |
| random_5_nonconsecutive | friday_only_sl2 | 233 | 15 | 169 | 64 | 0.725322 | 3.741146 | 191.028211 | 0.819864 | 4.949009 | 4 | 11 | -15.535245 | 1 | 3 | 11461.69 | False | False | 19102.82 | False | False |


## Conjunto combinado

| group | scenario | operations | blocked | tp | sl | win_rate | profit_factor | net_r | avg_r | max_drawdown_r | saved_sl | sacrificed_tp | net_delta_vs_baseline_r | months_improved | months_worsened | lot_0_6_net_usd | lot_0_6_violated_daily | lot_0_6_violated_total | lot_1_0_net_usd | lot_1_0_violated_daily | lot_1_0_violated_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined | baseline | 523 | 0 | 362 | 161 | 0.692161 | 2.979494 | 384.256247 | 0.734716 | 7.516361 | 0 | 0 | 0.0 | 0 | 0 | 23055.37 | False | False | 38425.62 | False | False |
| combined | guardrails_v1_friday_sl1 | 416 | 107 | 300 | 116 | 0.721154 | 3.438763 | 335.780595 | 0.807165 | 7.268688 | 45 | 62 | -48.475652 | 1 | 5 | 20146.84 | False | False | 33578.06 | False | False |
| combined | guardrails_v1_friday_sl2 | 416 | 107 | 300 | 116 | 0.721154 | 3.438763 | 335.780595 | 0.807165 | 7.268688 | 45 | 62 | -48.475652 | 1 | 5 | 20146.84 | False | False | 33578.06 | False | False |
| combined | cluster_only_2sl | 459 | 64 | 327 | 132 | 0.712418 | 3.310756 | 362.013781 | 0.788701 | 7.268688 | 29 | 35 | -22.242466 | 0 | 4 | 21720.83 | False | False | 36201.38 | False | False |
| combined | cluster_only_3sl | 490 | 33 | 341 | 149 | 0.695918 | 3.041712 | 364.604833 | 0.744091 | 6.9748 | 12 | 21 | -19.651414 | 1 | 2 | 21876.29 | False | False | 36460.48 | False | False |
| combined | friday_only_sl1 | 467 | 56 | 328 | 139 | 0.702355 | 3.113374 | 353.741787 | 0.757477 | 7.481972 | 22 | 34 | -30.51446 | 1 | 5 | 21224.51 | False | False | 35374.18 | False | False |
| combined | friday_only_sl2 | 467 | 56 | 328 | 139 | 0.702355 | 3.113374 | 353.741787 | 0.757477 | 7.481972 | 22 | 34 | -30.51446 | 1 | 5 | 21224.51 | False | False | 35374.18 | False | False |


## Lectura ejecutiva

- Baseline combinado: 523 operaciones, 362 TP, 161 SL, PF 2.979494, neto 384.256247R, max DD 7.516361R.

- Guardrails v1 completo: bloquea 107 operaciones, evita 45 SL, sacrifica 62 TP y queda -48.475652R por debajo del baseline.

- Mejor variante combinada por neto: `cluster_only_3sl` con delta -19.651414R.

- Variante menos agresiva utilizable: `cluster_only_3sl`; baja el max DD de 7.516361R a 6.9748R, pero aun sacrifica 21 TP para evitar 12 SL y pierde -19.651414R.

- Conclusion numerica: los guardrails duros mejoran win rate/PF y algo de drawdown, pero sobre-restringen el sistema y destruyen demasiado neto historico para activarlos completos antes del 5 de junio.

- La evidencia no permite aprobar BE automatico todavia; primero hay que guardar MFE/MAE real por trade desde Bot C/backend.

- La evidencia tampoco permite activar news guardrail automatico; debe quedar como placeholder trazable hasta tener calendario/noticias operable.

- Implementacion recomendada: parcial y reversible. Memoria operativa + explicabilidad + modo sombra; bloqueo duro solo como opcion conservadora tras 3 SL consecutivos en mismo simbolo/direccion/contexto.



## Respuestas directas

1. **Mejoran MAGI o lo sobre-restringen:** la version completa lo sobre-restringe. El neto combinado baja -48.475652R.

2. **Mejoran drawdown sin destruir profit:** mejoran poco el drawdown, pero destruyen profit suficiente como para no aprobar hard-enforcement completo.

3. **SL evitados:** full v1 evita 45 SL en combinado; `cluster_only_3sl` evita 12.

4. **TP sacrificados:** full v1 sacrifica 62 TP; `cluster_only_3sl` sacrifica 21.

5. **Variante mas sana:** `cluster_only_3sl` es la menos danina entre las variantes duras, pero todavia reduce neto. Debe iniciar en modo sombra o con flag.

6. **Parametro de mas valor:** memoria operativa/auditoria. Como regla operativa, SAFE_MODE tras 3 SL consecutivos tiene mejor relacion riesgo/profit que 2SL o Friday completo.

7. **Parametro que no debe implementarse todavia:** BE automatico y news guardrail por falta de MFE/MAE y calendario. Friday guardrail completo tampoco debe ir duro todavia.

8. **Antes del 5 de junio:** conviene implementar parcialmente, no la version completa.

9. **Donde implementarlo:** Melchor decide riesgo/bloqueo; CEO-MAGI/backend persiste memoria y razones; Bot B solo ejecuta; dashboard audita.

10. **Impacto sobre viernes 15:** probablemente habria bloqueado reentradas/dano de viernes en live, pero la simulacion historica muestra que usar esa reaccion como regla global recorta demasiados TP.



## Evaluacion tipo fondeo

- Cuenta asumida: 100,000 USD; lotajes evaluados: 0.6 y 1.0.

- En los meses seleccionados, ninguna variante viola perdida diaria del 4% ni perdida total del 8% segun el PnL historico disponible.

- Baseline y variantes superan objetivos de fase 1/fase 2 en esta muestra no continua, pero esto no equivale a pasar una evaluacion real por calendario continuo.

- Con lotaje 1.0, baseline combinado queda en 38,425.62 USD; full v1 queda en 33,578.06 USD; `cluster_only_3sl` queda en 36,460.48 USD.

- Margen prudencial: el dataset usado no muestra violaciones, pero la conclusion debe tratarse como validacion historica parcial, no certificacion de fondeo.

## Donde viviria cada parametro

- Melchor: cluster toxico, friday risk, daily/session SL count, spread deteriorated cuando exista.

- CEO-MAGI/backend: persistencia de memoria operativa, safe_mode_active, blocked_until y auditoria.

- Bot B: no debe decidir estos parametros; solo respetar `hold`/`open`/`modify` del payload.

- Dashboard/auditoria: mostrar variables de memoria, razones de bloqueo y parametros no simulables.

## Veredicto

**IMPLEMENTAR PARCIALMENTE.** No implementar MAGI Guardrails v1 completo como bloqueo duro antes del 5 de junio. La version inicial recomendada es: memoria operativa en Melchor/CEO, razones de bloqueo en dashboard, simulacion en modo sombra para Friday/cluster, y un unico bloqueo opcional/reversible tras 3 SL consecutivos en el mismo simbolo/direccion/contexto. BE y news quedan bloqueados hasta tener MFE/MAE y calendario real.

## Archivos generados

- `reports\magi_guardrails_v1_stress_months.csv`

- `reports\magi_guardrails_v1_random_months.csv`

- `reports\magi_guardrails_v1_combined_summary.csv`

- `reports\magi_guardrails_v1_blocked_trades.csv`

- `reports\magi_guardrails_v1_equity_curves.csv`

- `reports\magi_guardrails_v1_validation_2026-05-15.md`
