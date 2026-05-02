# Auditoria de Meses de Estres - CEO-MAGI v3

## Confirmacion de Formato

- Usa el mismo formato operativo que `random_3_months_trade_audit`.
- Usa la misma convencion de pips: `net_pips = realized_R * 10`.
- Usa los mismos calculos de duracion: `exit_timestamp - timestamp`.
- Usa solo operaciones `ENTER` aprobadas por CEO-MAGI v3.
- No modifica modelos, reglas, Bot B ni MT5.

## Meses Analizados

- `2020-03`: pandemia pico.
- `2022-04`: inflacion alta.
- `2026-04`: periodo problematico reciente; datos parciales disponibles.

## Resumen Mensual Completo

| Mes | Contexto | Ops | Ganadoras | Perdedoras | BE | Win rate | Pips ganados brutos | Pips perdidos brutos | Pips netos | Duracion prom. | Min. | Max. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| `2020-03` | pandemia pico | 181 | 116 | 65 | 0 | 64.09% | 2292.7 | -650.0 | 1104.6 | 27m | 5m | 4h 00m |
| `2022-04` | inflacion alta | 94 | 66 | 28 | 0 | 70.21% | 1253.6 | -279.1 | 672.3 | 1h 20m | 5m | 4h 00m |
| `2026-04` | periodo problematico reciente; datos parciales disponibles | 3 | 1 | 2 | 0 | 33.33% | 20.0 | -20.0 | -9.7 | 2h 15m | 1h 15m | 3h 15m |

## Detalle de Trades

### 2020-03

| Timestamp entrada | Simbolo | Direccion | Entry price | Resultado | Net pips | Duracion | Score | Aggression mode | Reason codes |
| --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- |
| `2020-03-03 14:35:00+0000` | `EURUSD` | `BUY` | 1.11105 | `WIN` | 16.4 | 5m | 0.3353 | `normal` | `[score_normal]` |
| `2020-03-04 14:25:00+0000` | `EURUSD` | `SELL` | 1.11358 | `WIN` | 16.9 | 35m | 0.2615 | `cautious` | `[score_cautious]` |
| `2020-03-04 18:30:00+0000` | `EURUSD` | `BUY` | 1.11288 | `WIN` | 2.7 | 4h 00m | 0.2403 | `cautious` | `[score_cautious]` |
| `2020-03-05 10:00:00+0000` | `EURUSD` | `BUY` | 1.11230 | `WIN` | 17.0 | 1h 20m | 0.5899 | `premium` | `[score_premium]` |
| `2020-03-10 07:10:00+0000` | `EURUSD` | `SELL` | 1.13574 | `WIN` | 16.5 | 25m | 0.5399 | `premium` | `[score_premium]` |
| `2020-03-10 07:35:00+0000` | `EURUSD` | `SELL` | 1.13464 | `LOSS` | -13.4 | 10m | 0.2779 | `cautious` | `[score_cautious]` |
| `2020-03-10 07:45:00+0000` | `EURUSD` | `SELL` | 1.13594 | `WIN` | 15.4 | 15m | 0.5908 | `premium` | `[score_premium]` |
| `2020-03-10 08:00:00+0000` | `EURUSD` | `SELL` | 1.13410 | `LOSS` | -14.4 | 5m | 0.2344 | `cautious` | `[score_cautious]` |
| `2020-03-10 08:05:00+0000` | `EURUSD` | `SELL` | 1.13539 | `LOSS` | -13.8 | 5m | 0.2389 | `cautious` | `[score_cautious]` |
| `2020-03-10 08:10:00+0000` | `EURUSD` | `SELL` | 1.13686 | `WIN` | 17.3 | 25m | 0.4463 | `premium` | `[score_premium]` |
| `2020-03-10 08:35:00+0000` | `EURUSD` | `SELL` | 1.13508 | `LOSS` | -14.3 | 50m | 0.3297 | `normal` | `[score_normal]` |
| `2020-03-10 09:25:00+0000` | `EURUSD` | `BUY` | 1.13576 | `LOSS` | -13.0 | 15m | 0.2441 | `cautious` | `[score_cautious]` |
| `2020-03-10 09:40:00+0000` | `EURUSD` | `BUY` | 1.13514 | `WIN` | 16.8 | 10m | 0.4996 | `premium` | `[score_premium]` |
| `2020-03-10 09:50:00+0000` | `EURUSD` | `SELL` | 1.13686 | `LOSS` | -13.0 | 5m | 0.2578 | `cautious` | `[score_cautious]` |
| `2020-03-10 09:55:00+0000` | `EURUSD` | `SELL` | 1.13764 | `LOSS` | -13.2 | 10m | 0.2456 | `cautious` | `[score_cautious]` |
| `2020-03-10 10:05:00+0000` | `EURUSD` | `SELL` | 1.13885 | `LOSS` | -13.6 | 10m | 0.2485 | `cautious` | `[score_cautious]` |
| `2020-03-10 10:20:00+0000` | `EURUSD` | `SELL` | 1.13849 | `WIN` | 16.9 | 35m | 0.4689 | `premium` | `[score_premium]` |
| `2020-03-10 10:55:00+0000` | `EURUSD` | `SELL` | 1.13662 | `WIN` | 15.5 | 50m | 0.6304 | `premium` | `[score_premium]` |
| `2020-03-10 11:45:00+0000` | `EURUSD` | `SELL` | 1.13460 | `LOSS` | -13.5 | 15m | 0.2225 | `cautious` | `[score_cautious]` |
| `2020-03-10 12:40:00+0000` | `EURUSD` | `BUY` | 1.13407 | `WIN` | 15.7 | 45m | 0.2231 | `cautious` | `[score_cautious]` |
| `2020-03-10 14:00:00+0000` | `EURUSD` | `BUY` | 1.13594 | `WIN` | 16.6 | 10m | 0.2403 | `cautious` | `[score_cautious]` |
| `2020-03-10 14:35:00+0000` | `EURUSD` | `SELL` | 1.13883 | `WIN` | 15.5 | 1h 00m | 0.3246 | `normal` | `[score_normal]` |
| `2020-03-10 17:30:00+0000` | `EURUSD` | `SELL` | 1.13836 | `WIN` | 16.5 | 25m | 0.2852 | `cautious` | `[score_cautious]` |
| `2020-03-10 18:20:00+0000` | `EURUSD` | `SELL` | 1.13352 | `WIN` | 16.0 | 25m | 0.2043 | `cautious` | `[score_cautious]` |
| `2020-03-10 18:45:00+0000` | `EURUSD` | `SELL` | 1.13204 | `WIN` | 16.8 | 10m | 0.2830 | `cautious` | `[score_cautious]` |
| `2020-03-10 19:05:00+0000` | `EURUSD` | `BUY` | 1.13095 | `WIN` | 17.2 | 1h 05m | 0.3100 | `normal` | `[score_normal]` |
| `2020-03-10 21:00:00+0000` | `EURUSD` | `SELL` | 1.12950 | `WIN` | 17.3 | 25m | 0.4297 | `premium` | `[score_premium]` |
| `2020-03-10 21:30:00+0000` | `EURUSD` | `SELL` | 1.12968 | `LOSS` | -13.5 | 45m | 0.2424 | `cautious` | `[score_cautious]` |
| `2020-03-11 08:20:00+0000` | `EURUSD` | `SELL` | 1.13566 | `WIN` | 15.5 | 1h 00m | 0.6777 | `premium` | `[score_premium]` |
| `2020-03-11 09:20:00+0000` | `EURUSD` | `SELL` | 1.13461 | `WIN` | 17.3 | 45m | 0.6459 | `premium` | `[score_premium]` |
| `2020-03-11 10:05:00+0000` | `EURUSD` | `SELL` | 1.13285 | `WIN` | 15.5 | 1h 40m | 0.6044 | `premium` | `[score_premium]` |
| `2020-03-11 11:45:00+0000` | `EURUSD` | `SELL` | 1.13068 | `LOSS` | -13.1 | 30m | 0.2286 | `cautious` | `[score_cautious]` |
| `2020-03-11 12:15:00+0000` | `EURUSD` | `BUY` | 1.13175 | `WIN` | 16.9 | 1h 15m | 0.4742 | `premium` | `[score_premium]` |
| `2020-03-11 14:00:00+0000` | `EURUSD` | `BUY` | 1.13288 | `WIN` | 16.3 | 30m | 0.5481 | `premium` | `[score_premium]` |
| `2020-03-11 14:30:00+0000` | `EURUSD` | `SELL` | 1.13476 | `WIN` | 18.0 | 1h 40m | 0.5705 | `premium` | `[score_premium]` |
| `2020-03-11 17:00:00+0000` | `EURUSD` | `SELL` | 1.13071 | `WIN` | 16.4 | 15m | 0.5274 | `premium` | `[score_premium]` |
| `2020-03-11 17:15:00+0000` | `EURUSD` | `SELL` | 1.12831 | `WIN` | 18.2 | 25m | 0.5112 | `premium` | `[score_premium]` |
| `2020-03-11 17:40:00+0000` | `EURUSD` | `SELL` | 1.12641 | `LOSS` | -13.2 | 20m | 0.3273 | `normal` | `[score_normal]` |
| `2020-03-11 18:00:00+0000` | `EURUSD` | `SELL` | 1.12800 | `WIN` | 4.9 | 4h 00m | 0.4710 | `premium` | `[score_premium]` |
| `2020-03-12 09:45:00+0000` | `EURUSD` | `SELL` | 1.13183 | `WIN` | 17.3 | 25m | 0.4234 | `premium` | `[score_premium]` |
| `2020-03-12 10:10:00+0000` | `EURUSD` | `SELL` | 1.13018 | `LOSS` | -13.7 | 10m | 0.3117 | `normal` | `[score_normal]` |
| `2020-03-12 10:20:00+0000` | `EURUSD` | `SELL` | 1.12969 | `WIN` | 17.6 | 5m | 0.5647 | `premium` | `[score_premium]` |
| `2020-03-12 10:25:00+0000` | `EURUSD` | `SELL` | 1.12673 | `LOSS` | -13.2 | 45m | 0.3286 | `normal` | `[score_normal]` |
| `2020-03-12 11:10:00+0000` | `EURUSD` | `SELL` | 1.12720 | `WIN` | 16.7 | 40m | 0.5630 | `premium` | `[score_premium]` |
| `2020-03-12 11:50:00+0000` | `EURUSD` | `SELL` | 1.12489 | `WIN` | 17.4 | 25m | 0.5553 | `premium` | `[score_premium]` |
| `2020-03-12 12:15:00+0000` | `EURUSD` | `SELL` | 1.12286 | `LOSS` | -12.4 | 25m | 0.2697 | `cautious` | `[score_cautious]` |
| `2020-03-12 12:40:00+0000` | `EURUSD` | `SELL` | 1.12422 | `WIN` | 17.6 | 45m | 0.5525 | `premium` | `[score_premium]` |
| `2020-03-12 14:00:00+0000` | `EURUSD` | `SELL` | 1.12371 | `LOSS` | -12.8 | 5m | 0.3220 | `normal` | `[score_normal]` |
| `2020-03-12 14:05:00+0000` | `EURUSD` | `SELL` | 1.12466 | `LOSS` | -12.5 | 5m | 0.2201 | `cautious` | `[score_cautious]` |
| `2020-03-12 14:10:00+0000` | `EURUSD` | `SELL` | 1.12461 | `WIN` | 17.4 | 10m | 0.4165 | `premium` | `[score_premium]` |
| `2020-03-12 14:20:00+0000` | `EURUSD` | `SELL` | 1.12257 | `LOSS` | -12.9 | 10m | 0.2514 | `cautious` | `[score_cautious]` |
| `2020-03-12 14:30:00+0000` | `EURUSD` | `BUY` | 1.12138 | `LOSS` | -12.9 | 20m | 0.2457 | `cautious` | `[score_cautious]` |
| `2020-03-12 14:50:00+0000` | `EURUSD` | `SELL` | 1.12703 | `LOSS` | -12.6 | 5m | 0.2941 | `cautious` | `[score_cautious]` |
| `2020-03-12 14:55:00+0000` | `EURUSD` | `SELL` | 1.12502 | `WIN` | 17.5 | 5m | 0.3340 | `normal` | `[score_normal]` |
| `2020-03-12 17:00:00+0000` | `EURUSD` | `SELL` | 1.11448 | `WIN` | 16.5 | 10m | 0.3906 | `normal` | `[score_normal]` |
| `2020-03-12 17:35:00+0000` | `EURUSD` | `SELL` | 1.11248 | `WIN` | 17.7 | 5m | 0.2997 | `cautious` | `[score_cautious]` |
| `2020-03-12 17:40:00+0000` | `EURUSD` | `SELL` | 1.11097 | `WIN` | 16.3 | 5m | 0.3250 | `normal` | `[score_normal]` |
| `2020-03-12 17:50:00+0000` | `EURUSD` | `SELL` | 1.11024 | `WIN` | 17.1 | 10m | 0.2373 | `cautious` | `[score_cautious]` |
| `2020-03-12 18:15:00+0000` | `EURUSD` | `BUY` | 1.10666 | `WIN` | 16.8 | 20m | 0.3208 | `normal` | `[score_normal]` |
| `2020-03-13 07:35:00+0000` | `EURUSD` | `SELL` | 1.11989 | `LOSS` | -12.7 | 40m | 0.2685 | `cautious` | `[score_cautious]` |
| `2020-03-13 08:15:00+0000` | `EURUSD` | `SELL` | 1.12062 | `WIN` | 16.3 | 1h 10m | 0.5006 | `premium` | `[score_premium]` |
| `2020-03-13 09:25:00+0000` | `EURUSD` | `SELL` | 1.11731 | `LOSS` | -12.6 | 10m | 0.2623 | `cautious` | `[score_cautious]` |
| `2020-03-13 09:35:00+0000` | `EURUSD` | `SELL` | 1.11883 | `WIN` | 16.7 | 15m | 0.3802 | `normal` | `[score_normal]` |
| `2020-03-13 09:50:00+0000` | `EURUSD` | `SELL` | 1.11698 | `LOSS` | -12.5 | 10m | 0.2490 | `cautious` | `[score_cautious]` |
| `2020-03-13 10:15:00+0000` | `EURUSD` | `SELL` | 1.11940 | `LOSS` | -13.0 | 30m | 0.2356 | `cautious` | `[score_cautious]` |
| `2020-03-13 10:45:00+0000` | `EURUSD` | `SELL` | 1.12046 | `WIN` | 17.6 | 40m | 0.4314 | `premium` | `[score_premium]` |
| `2020-03-13 11:25:00+0000` | `EURUSD` | `SELL` | 1.11853 | `WIN` | 17.3 | 30m | 0.4274 | `premium` | `[score_premium]` |
| `2020-03-13 11:55:00+0000` | `EURUSD` | `SELL` | 1.11683 | `WIN` | 17.1 | 1h 20m | 0.4384 | `premium` | `[score_premium]` |
| `2020-03-13 14:10:00+0000` | `EURUSD` | `SELL` | 1.11633 | `WIN` | 17.9 | 25m | 0.3013 | `normal` | `[score_normal]` |
| `2020-03-13 14:35:00+0000` | `EURUSD` | `SELL` | 1.11465 | `WIN` | 17.5 | 20m | 0.3016 | `normal` | `[score_normal]` |
| `2020-03-13 18:25:00+0000` | `EURUSD` | `SELL` | 1.10800 | `WIN` | 17.0 | 15m | 0.2087 | `cautious` | `[score_cautious]` |
| `2020-03-17 08:30:00+0000` | `EURUSD` | `SELL` | 1.11718 | `WIN` | 18.0 | 35m | 0.4082 | `premium` | `[score_premium]` |
| `2020-03-17 09:05:00+0000` | `EURUSD` | `SELL` | 1.11501 | `WIN` | 17.6 | 40m | 0.5027 | `premium` | `[score_premium]` |
| `2020-03-17 11:40:00+0000` | `EURUSD` | `SELL` | 1.11126 | `WIN` | 17.1 | 20m | 0.4465 | `premium` | `[score_premium]` |
| `2020-03-17 12:00:00+0000` | `EURUSD` | `SELL` | 1.10938 | `WIN` | 18.0 | 25m | 0.4190 | `premium` | `[score_premium]` |
| `2020-03-17 12:25:00+0000` | `EURUSD` | `SELL` | 1.10653 | `WIN` | 16.5 | 25m | 0.4527 | `premium` | `[score_premium]` |
| `2020-03-17 12:50:00+0000` | `EURUSD` | `SELL` | 1.10414 | `WIN` | 16.8 | 20m | 0.4627 | `premium` | `[score_premium]` |
| `2020-03-17 14:00:00+0000` | `EURUSD` | `SELL` | 1.10127 | `WIN` | 17.0 | 30m | 0.5030 | `premium` | `[score_premium]` |
| `2020-03-17 14:30:00+0000` | `EURUSD` | `BUY` | 1.09865 | `LOSS` | -12.6 | 5m | 0.3067 | `normal` | `[score_normal]` |
| `2020-03-17 14:40:00+0000` | `EURUSD` | `BUY` | 1.09771 | `WIN` | 16.3 | 55m | 0.4232 | `premium` | `[score_premium]` |
| `2020-03-17 17:00:00+0000` | `EURUSD` | `SELL` | 1.09704 | `LOSS` | -12.3 | 15m | 0.3605 | `normal` | `[score_normal]` |
| `2020-03-17 17:50:00+0000` | `EURUSD` | `SELL` | 1.09874 | `WIN` | 17.2 | 10m | 0.3662 | `normal` | `[score_normal]` |
| `2020-03-17 18:00:00+0000` | `EURUSD` | `BUY` | 1.09709 | `WIN` | 16.9 | 30m | 0.6461 | `premium` | `[score_premium]` |
| `2020-03-17 18:30:00+0000` | `EURUSD` | `BUY` | 1.09854 | `LOSS` | -13.2 | 5m | 0.3014 | `normal` | `[score_normal]` |
| `2020-03-17 18:35:00+0000` | `EURUSD` | `BUY` | 1.09745 | `LOSS` | -12.4 | 25m | 0.2981 | `cautious` | `[score_cautious]` |
| `2020-03-17 19:00:00+0000` | `EURUSD` | `BUY` | 1.09661 | `WIN` | 17.9 | 55m | 0.5057 | `premium` | `[score_premium]` |
| `2020-03-17 19:55:00+0000` | `EURUSD` | `BUY` | 1.09860 | `WIN` | 17.6 | 30m | 0.4812 | `premium` | `[score_premium]` |
| `2020-03-17 21:00:00+0000` | `EURUSD` | `BUY` | 1.09996 | `LOSS` | -13.2 | 10m | 0.2603 | `cautious` | `[score_cautious]` |
| `2020-03-17 21:25:00+0000` | `EURUSD` | `BUY` | 1.09843 | `WIN` | 16.4 | 15m | 0.4440 | `premium` | `[score_premium]` |
| `2020-03-17 21:40:00+0000` | `EURUSD` | `BUY` | 1.10055 | `LOSS` | -12.3 | 1h 10m | 0.2807 | `cautious` | `[score_cautious]` |
| `2020-03-18 07:45:00+0000` | `EURUSD` | `SELL` | 1.10414 | `WIN` | 17.8 | 25m | 0.3149 | `normal` | `[score_normal]` |
| `2020-03-18 08:55:00+0000` | `EURUSD` | `SELL` | 1.10075 | `LOSS` | -12.1 | 20m | 0.2106 | `cautious` | `[score_cautious]` |
| `2020-03-18 09:45:00+0000` | `EURUSD` | `SELL` | 1.09971 | `WIN` | 16.3 | 15m | 0.2916 | `cautious` | `[score_cautious]` |
| `2020-03-18 10:15:00+0000` | `EURUSD` | `SELL` | 1.09846 | `WIN` | 17.9 | 40m | 0.2460 | `cautious` | `[score_cautious]` |
| `2020-03-18 11:25:00+0000` | `EURUSD` | `SELL` | 1.09877 | `LOSS` | -12.6 | 10m | 0.2110 | `cautious` | `[score_cautious]` |
| `2020-03-18 14:00:00+0000` | `EURUSD` | `SELL` | 1.09770 | `WIN` | 17.1 | 25m | 0.3545 | `normal` | `[score_normal]` |
| `2020-03-18 14:40:00+0000` | `EURUSD` | `SELL` | 1.09675 | `WIN` | 16.7 | 20m | 0.3135 | `normal` | `[score_normal]` |
| `2020-03-18 17:35:00+0000` | `EURUSD` | `SELL` | 1.08720 | `WIN` | 17.8 | 10m | 0.3280 | `normal` | `[score_normal]` |
| `2020-03-18 17:55:00+0000` | `EURUSD` | `SELL` | 1.08546 | `WIN` | 16.6 | 5m | 0.2162 | `cautious` | `[score_cautious]` |
| `2020-03-18 18:25:00+0000` | `EURUSD` | `SELL` | 1.08425 | `WIN` | 16.9 | 30m | 0.3476 | `normal` | `[score_normal]` |
| `2020-03-18 18:55:00+0000` | `EURUSD` | `BUY` | 1.08176 | `LOSS` | -12.4 | 5m | 0.3469 | `normal` | `[score_normal]` |
| `2020-03-18 19:00:00+0000` | `EURUSD` | `BUY` | 1.08091 | `WIN` | 17.9 | 30m | 0.4599 | `premium` | `[score_premium]` |
| `2020-03-18 19:30:00+0000` | `EURUSD` | `SELL` | 1.08333 | `LOSS` | -13.2 | 20m | 0.2072 | `cautious` | `[score_cautious]` |
| `2020-03-18 21:55:00+0000` | `EURUSD` | `BUY` | 1.08953 | `WIN` | 17.3 | 1h 05m | 0.4013 | `premium` | `[score_premium]` |
| `2020-03-19 08:20:00+0000` | `EURUSD` | `SELL` | 1.09338 | `LOSS` | -12.9 | 20m | 0.3244 | `normal` | `[score_normal]` |
| `2020-03-19 08:40:00+0000` | `EURUSD` | `SELL` | 1.09328 | `LOSS` | -12.9 | 10m | 0.2315 | `cautious` | `[score_cautious]` |
| `2020-03-19 08:50:00+0000` | `EURUSD` | `SELL` | 1.09361 | `WIN` | 17.3 | 30m | 0.4725 | `premium` | `[score_premium]` |
| `2020-03-19 09:20:00+0000` | `EURUSD` | `SELL` | 1.09109 | `WIN` | 17.5 | 10m | 0.6225 | `premium` | `[score_premium]` |
| `2020-03-19 09:30:00+0000` | `EURUSD` | `SELL` | 1.08915 | `WIN` | 16.8 | 10m | 0.7385 | `premium` | `[score_premium]` |
| `2020-03-19 09:40:00+0000` | `EURUSD` | `SELL` | 1.08596 | `LOSS` | -13.2 | 5m | 0.4283 | `premium` | `[score_premium]` |
| `2020-03-19 09:45:00+0000` | `EURUSD` | `SELL` | 1.08634 | `LOSS` | -13.8 | 5m | 0.3298 | `normal` | `[score_normal]` |
| `2020-03-19 09:55:00+0000` | `EURUSD` | `SELL` | 1.08561 | `WIN` | 16.4 | 15m | 0.5710 | `premium` | `[score_premium]` |
| `2020-03-19 10:10:00+0000` | `EURUSD` | `BUY` | 1.08253 | `LOSS` | -12.9 | 5m | 0.4770 | `premium` | `[score_premium]` |
| `2020-03-19 10:15:00+0000` | `EURUSD` | `BUY` | 1.08147 | `WIN` | 16.8 | 5m | 0.6577 | `premium` | `[score_premium]` |
| `2020-03-19 10:20:00+0000` | `EURUSD` | `SELL` | 1.08527 | `LOSS` | -11.8 | 5m | 0.4150 | `premium` | `[score_premium]` |
| `2020-03-19 10:25:00+0000` | `EURUSD` | `SELL` | 1.08731 | `LOSS` | -12.3 | 5m | 0.3804 | `normal` | `[score_normal]` |
| `2020-03-19 10:30:00+0000` | `EURUSD` | `SELL` | 1.08737 | `LOSS` | -13.3 | 10m | 0.3687 | `normal` | `[score_normal]` |
| `2020-03-19 10:40:00+0000` | `EURUSD` | `SELL` | 1.08706 | `LOSS` | -12.5 | 5m | 0.3741 | `normal` | `[score_normal]` |
| `2020-03-19 10:45:00+0000` | `EURUSD` | `SELL` | 1.08864 | `WIN` | 16.3 | 10m | 0.5906 | `premium` | `[score_premium]` |
| `2020-03-19 10:55:00+0000` | `EURUSD` | `SELL` | 1.08605 | `WIN` | 17.7 | 5m | 0.6884 | `premium` | `[score_premium]` |
| `2020-03-19 11:00:00+0000` | `EURUSD` | `BUY` | 1.08375 | `WIN` | 16.2 | 15m | 0.5925 | `premium` | `[score_premium]` |
| `2020-03-19 11:25:00+0000` | `EURUSD` | `SELL` | 1.08501 | `LOSS` | -13.2 | 10m | 0.3388 | `normal` | `[score_normal]` |
| `2020-03-19 11:35:00+0000` | `EURUSD` | `SELL` | 1.08661 | `WIN` | 17.2 | 5m | 0.4920 | `premium` | `[score_premium]` |
| `2020-03-19 11:40:00+0000` | `EURUSD` | `SELL` | 1.08435 | `WIN` | 17.0 | 20m | 0.5463 | `premium` | `[score_premium]` |
| `2020-03-19 12:00:00+0000` | `EURUSD` | `SELL` | 1.08237 | `WIN` | 17.6 | 25m | 0.5340 | `premium` | `[score_premium]` |
| `2020-03-19 12:25:00+0000` | `EURUSD` | `SELL` | 1.08054 | `WIN` | 17.8 | 35m | 0.4171 | `premium` | `[score_premium]` |
| `2020-03-19 18:45:00+0000` | `EURUSD` | `BUY` | 1.06884 | `LOSS` | -13.3 | 10m | 0.2716 | `cautious` | `[score_cautious]` |
| `2020-03-19 18:55:00+0000` | `EURUSD` | `BUY` | 1.06780 | `LOSS` | -12.3 | 5m | 0.2346 | `cautious` | `[score_cautious]` |
| `2020-03-19 19:00:00+0000` | `EURUSD` | `BUY` | 1.06628 | `WIN` | 17.9 | 15m | 0.5029 | `premium` | `[score_premium]` |
| `2020-03-19 19:15:00+0000` | `EURUSD` | `BUY` | 1.06821 | `WIN` | 16.8 | 20m | 0.5420 | `premium` | `[score_premium]` |
| `2020-03-19 19:35:00+0000` | `EURUSD` | `BUY` | 1.07013 | `LOSS` | -12.5 | 5m | 0.3156 | `normal` | `[score_normal]` |
| `2020-03-19 19:40:00+0000` | `EURUSD` | `BUY` | 1.06977 | `LOSS` | -11.9 | 10m | 0.3061 | `normal` | `[score_normal]` |
| `2020-03-19 21:00:00+0000` | `EURUSD` | `BUY` | 1.06673 | `WIN` | 17.2 | 15m | 0.5097 | `premium` | `[score_premium]` |
| `2020-03-19 21:15:00+0000` | `EURUSD` | `BUY` | 1.06881 | `LOSS` | -12.9 | 5m | 0.2214 | `cautious` | `[score_cautious]` |
| `2020-03-20 08:20:00+0000` | `EURUSD` | `BUY` | 1.07525 | `WIN` | 15.9 | 25m | 0.3020 | `normal` | `[score_normal]` |
| `2020-03-20 08:45:00+0000` | `EURUSD` | `SELL` | 1.07743 | `WIN` | 16.3 | 20m | 0.3369 | `normal` | `[score_normal]` |
| `2020-03-20 09:05:00+0000` | `EURUSD` | `SELL` | 1.07506 | `LOSS` | -12.6 | 25m | 0.2842 | `cautious` | `[score_cautious]` |
| `2020-03-20 11:30:00+0000` | `EURUSD` | `SELL` | 1.07617 | `WIN` | 17.5 | 15m | 0.3493 | `normal` | `[score_normal]` |
| `2020-03-20 11:45:00+0000` | `EURUSD` | `SELL` | 1.07319 | `WIN` | 16.5 | 25m | 0.4829 | `premium` | `[score_premium]` |
| `2020-03-20 12:10:00+0000` | `EURUSD` | `SELL` | 1.07214 | `LOSS` | -13.6 | 10m | 0.3077 | `normal` | `[score_normal]` |
| `2020-03-20 12:35:00+0000` | `EURUSD` | `SELL` | 1.07481 | `WIN` | 16.5 | 10m | 0.3747 | `normal` | `[score_normal]` |
| `2020-03-20 12:45:00+0000` | `EURUSD` | `SELL` | 1.07288 | `LOSS` | -12.6 | 15m | 0.2244 | `cautious` | `[score_cautious]` |
| `2020-03-20 14:00:00+0000` | `EURUSD` | `SELL` | 1.07106 | `LOSS` | -13.8 | 10m | 0.3089 | `normal` | `[score_normal]` |
| `2020-03-20 14:50:00+0000` | `EURUSD` | `SELL` | 1.07433 | `WIN` | 16.5 | 10m | 0.3891 | `normal` | `[score_normal]` |
| `2020-03-20 17:00:00+0000` | `EURUSD` | `SELL` | 1.07199 | `LOSS` | -12.5 | 5m | 0.3141 | `normal` | `[score_normal]` |
| `2020-03-20 17:05:00+0000` | `EURUSD` | `SELL` | 1.07427 | `WIN` | 17.9 | 25m | 0.3219 | `normal` | `[score_normal]` |
| `2020-03-20 17:30:00+0000` | `EURUSD` | `SELL` | 1.07250 | `LOSS` | -12.4 | 5m | 0.3110 | `normal` | `[score_normal]` |
| `2020-03-20 17:35:00+0000` | `EURUSD` | `SELL` | 1.07364 | `WIN` | 16.9 | 20m | 0.4304 | `premium` | `[score_premium]` |
| `2020-03-20 17:55:00+0000` | `EURUSD` | `BUY` | 1.06944 | `LOSS` | -13.9 | 5m | 0.5198 | `premium` | `[score_premium]` |
| `2020-03-20 18:00:00+0000` | `EURUSD` | `BUY` | 1.06814 | `WIN` | 16.6 | 5m | 0.6655 | `premium` | `[score_premium]` |
| `2020-03-20 18:05:00+0000` | `EURUSD` | `BUY` | 1.07033 | `LOSS` | -13.5 | 5m | 0.5025 | `premium` | `[score_premium]` |
| `2020-03-20 18:10:00+0000` | `EURUSD` | `BUY` | 1.06919 | `LOSS` | -13.0 | 25m | 0.4285 | `premium` | `[score_premium]` |
| `2020-03-20 18:35:00+0000` | `EURUSD` | `BUY` | 1.06811 | `LOSS` | -13.7 | 10m | 0.4416 | `premium` | `[score_premium]` |
| `2020-03-20 18:45:00+0000` | `EURUSD` | `BUY` | 1.06717 | `LOSS` | -12.3 | 5m | 0.3655 | `normal` | `[score_normal]` |
| `2020-03-20 18:50:00+0000` | `EURUSD` | `BUY` | 1.06706 | `LOSS` | -13.5 | 5m | 0.3572 | `normal` | `[score_normal]` |
| `2020-03-20 18:55:00+0000` | `EURUSD` | `BUY` | 1.06607 | `WIN` | 16.5 | 20m | 0.5642 | `premium` | `[score_premium]` |
| `2020-03-20 19:15:00+0000` | `EURUSD` | `BUY` | 1.06802 | `LOSS` | -12.7 | 40m | 0.3200 | `normal` | `[score_normal]` |
| `2020-03-20 21:20:00+0000` | `EURUSD` | `BUY` | 1.06512 | `LOSS` | -12.8 | 10m | 0.3127 | `normal` | `[score_normal]` |
| `2020-03-20 21:30:00+0000` | `EURUSD` | `BUY` | 1.06403 | `WIN` | 17.6 | 20m | 0.5587 | `premium` | `[score_premium]` |
| `2020-03-20 21:50:00+0000` | `EURUSD` | `BUY` | 1.06646 | `WIN` | 17.7 | 25m | 0.6435 | `premium` | `[score_premium]` |
| `2020-03-25 19:05:00+0000` | `EURUSD` | `BUY` | 1.08424 | `WIN` | 17.8 | 20m | 0.2211 | `cautious` | `[score_cautious]` |
| `2020-03-26 14:45:00+0000` | `EURUSD` | `BUY` | 1.09490 | `WIN` | 18.1 | 15m | 0.2489 | `cautious` | `[score_cautious]` |
| `2020-03-26 17:00:00+0000` | `EURUSD` | `BUY` | 1.09914 | `WIN` | 18.0 | 30m | 0.3696 | `normal` | `[score_normal]` |
| `2020-03-26 17:40:00+0000` | `EURUSD` | `BUY` | 1.09971 | `WIN` | 16.5 | 20m | 0.3091 | `normal` | `[score_normal]` |
| `2020-03-26 18:00:00+0000` | `EURUSD` | `BUY` | 1.10245 | `LOSS` | -13.7 | 5m | 0.2126 | `cautious` | `[score_cautious]` |
| `2020-03-26 18:05:00+0000` | `EURUSD` | `BUY` | 1.10126 | `WIN` | 17.0 | 50m | 0.3242 | `normal` | `[score_normal]` |
| `2020-03-26 18:55:00+0000` | `EURUSD` | `BUY` | 1.10349 | `LOSS` | -13.0 | 20m | 0.2711 | `cautious` | `[score_cautious]` |
| `2020-03-26 19:15:00+0000` | `EURUSD` | `BUY` | 1.10255 | `WIN` | 16.4 | 1h 50m | 0.3875 | `normal` | `[score_normal]` |
| `2020-03-26 21:15:00+0000` | `EURUSD` | `BUY` | 1.10288 | `WIN` | 18.0 | 45m | 0.2295 | `cautious` | `[score_cautious]` |
| `2020-03-27 08:35:00+0000` | `EURUSD` | `SELL` | 1.10458 | `WIN` | 17.8 | 55m | 0.4012 | `premium` | `[score_premium]` |
| `2020-03-27 10:10:00+0000` | `EURUSD` | `SELL` | 1.10397 | `WIN` | 17.7 | 20m | 0.2260 | `cautious` | `[score_cautious]` |
| `2020-03-27 10:30:00+0000` | `EURUSD` | `SELL` | 1.10205 | `WIN` | 16.3 | 1h 00m | 0.2868 | `cautious` | `[score_cautious]` |
| `2020-03-27 11:55:00+0000` | `EURUSD` | `SELL` | 1.10157 | `WIN` | 17.1 | 25m | 0.3204 | `normal` | `[score_normal]` |
| `2020-03-27 14:40:00+0000` | `EURUSD` | `SELL` | 1.09842 | `WIN` | 16.5 | 45m | 0.2251 | `cautious` | `[score_cautious]` |
| `2020-03-27 17:00:00+0000` | `EURUSD` | `BUY` | 1.10058 | `WIN` | 18.2 | 20m | 0.2345 | `cautious` | `[score_cautious]` |
| `2020-03-27 17:20:00+0000` | `EURUSD` | `BUY` | 1.10277 | `WIN` | 17.1 | 30m | 0.3465 | `normal` | `[score_normal]` |
| `2020-03-27 18:00:00+0000` | `EURUSD` | `BUY` | 1.10588 | `WIN` | 17.1 | 20m | 0.2177 | `cautious` | `[score_cautious]` |
| `2020-03-27 18:50:00+0000` | `EURUSD` | `BUY` | 1.10679 | `WIN` | 16.9 | 1h 05m | 0.3472 | `normal` | `[score_normal]` |
| `2020-03-27 19:55:00+0000` | `EURUSD` | `BUY` | 1.10943 | `WIN` | 17.5 | 1h 05m | 0.4136 | `premium` | `[score_premium]` |
| `2020-03-27 21:00:00+0000` | `EURUSD` | `BUY` | 1.11182 | `WIN` | 17.3 | 1h 15m | 0.4453 | `premium` | `[score_premium]` |
| `2020-03-31 09:30:00+0000` | `EURUSD` | `SELL` | 1.10070 | `WIN` | 16.6 | 2h 25m | 0.3128 | `normal` | `[score_normal]` |

### 2022-04

| Timestamp entrada | Simbolo | Direccion | Entry price | Resultado | Net pips | Duracion | Score | Aggression mode | Reason codes |
| --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- |
| `2022-04-01 07:05:00+0000` | `EURUSD` | `SELL` | 1.10669 | `WIN` | 17.6 | 3h 25m | 0.2265 | `cautious` | `[score_cautious]` |
| `2022-04-05 07:10:00+0000` | `EURUSD` | `BUY` | 1.09701 | `WIN` | 6.8 | 4h 00m | 0.2884 | `cautious` | `[score_cautious]` |
| `2022-04-05 11:10:00+0000` | `EURUSD` | `SELL` | 1.09808 | `WIN` | 17.3 | 2h 30m | 0.4189 | `premium` | `[score_premium]` |
| `2022-04-05 14:00:00+0000` | `EURUSD` | `SELL` | 1.09698 | `WIN` | 17.2 | 3h 20m | 0.2857 | `cautious` | `[score_cautious]` |
| `2022-04-05 17:20:00+0000` | `EURUSD` | `SELL` | 1.09465 | `WIN` | 16.3 | 1h 00m | 0.5552 | `premium` | `[score_premium]` |
| `2022-04-05 18:20:00+0000` | `EURUSD` | `SELL` | 1.09269 | `WIN` | 17.3 | 3h 15m | 0.5465 | `premium` | `[score_premium]` |
| `2022-04-06 12:00:00+0000` | `EURUSD` | `SELL` | 1.09231 | `WIN` | 17.6 | 1h 30m | 0.2572 | `cautious` | `[score_cautious]` |
| `2022-04-08 08:00:00+0000` | `EURUSD` | `BUY` | 1.08549 | `WIN` | 16.6 | 3h 05m | 0.2137 | `cautious` | `[score_cautious]` |
| `2022-04-08 14:30:00+0000` | `EURUSD` | `SELL` | 1.08641 | `WIN` | 16.9 | 1h 50m | 0.2388 | `cautious` | `[score_cautious]` |
| `2022-04-08 17:00:00+0000` | `EURUSD` | `BUY` | 1.08399 | `WIN` | 16.7 | 50m | 0.4522 | `premium` | `[score_premium]` |
| `2022-04-12 11:10:00+0000` | `EURUSD` | `SELL` | 1.08671 | `WIN` | 2.0 | 4h 00m | 0.3337 | `normal` | `[score_normal]` |
| `2022-04-13 10:10:00+0000` | `EURUSD` | `BUY` | 1.08162 | `WIN` | 16.5 | 35m | 0.4339 | `premium` | `[score_premium]` |
| `2022-04-13 10:45:00+0000` | `EURUSD` | `SELL` | 1.08349 | `LOSS` | -13.1 | 3h 50m | 0.2278 | `cautious` | `[score_cautious]` |
| `2022-04-13 14:35:00+0000` | `EURUSD` | `SELL` | 1.08436 | `WIN` | 17.9 | 50m | 0.2419 | `cautious` | `[score_cautious]` |
| `2022-04-14 12:25:00+0000` | `EURUSD` | `SELL` | 1.09119 | `WIN` | 16.5 | 2h 25m | 0.3364 | `normal` | `[score_normal]` |
| `2022-04-14 17:00:00+0000` | `EURUSD` | `BUY` | 1.07703 | `WIN` | 17.6 | 25m | 0.2731 | `cautious` | `[score_cautious]` |
| `2022-04-14 18:00:00+0000` | `EURUSD` | `BUY` | 1.07780 | `WIN` | 16.0 | 10m | 0.3412 | `normal` | `[score_normal]` |
| `2022-04-14 18:45:00+0000` | `EURUSD` | `BUY` | 1.07896 | `WIN` | 16.8 | 25m | 0.3497 | `normal` | `[score_normal]` |
| `2022-04-15 11:55:00+0000` | `EURUSD` | `SELL` | 1.08207 | `WIN` | 3.2 | 4h 00m | 0.3933 | `normal` | `[score_normal]` |
| `2022-04-15 21:00:00+0000` | `EURUSD` | `SELL` | 1.08103 | `WIN` | 17.2 | 3h 00m | 0.4294 | `premium` | `[score_premium]` |
| `2022-04-19 07:00:00+0000` | `EURUSD` | `BUY` | 1.07724 | `WIN` | 16.8 | 3h 35m | 0.6083 | `premium` | `[score_premium]` |
| `2022-04-19 10:35:00+0000` | `EURUSD` | `BUY` | 1.07909 | `WIN` | 17.5 | 1h 00m | 0.5189 | `premium` | `[score_premium]` |
| `2022-04-19 11:35:00+0000` | `EURUSD` | `SELL` | 1.08083 | `WIN` | 16.4 | 2h 15m | 0.4831 | `premium` | `[score_premium]` |
| `2022-04-19 14:00:00+0000` | `EURUSD` | `BUY` | 1.07940 | `LOSS` | -11.7 | 4h 00m | 0.2250 | `cautious` | `[score_cautious]` |
| `2022-04-20 07:00:00+0000` | `EURUSD` | `BUY` | 1.08184 | `LOSS` | -13.0 | 2h 30m | 0.2509 | `cautious` | `[score_cautious]` |
| `2022-04-20 11:40:00+0000` | `EURUSD` | `BUY` | 1.08285 | `WIN` | 16.5 | 1h 00m | 0.3707 | `normal` | `[score_normal]` |
| `2022-04-20 12:40:00+0000` | `EURUSD` | `SELL` | 1.08566 | `WIN` | 17.5 | 2h 15m | 0.3740 | `normal` | `[score_normal]` |
| `2022-04-20 17:15:00+0000` | `EURUSD` | `SELL` | 1.08592 | `WIN` | 0.2 | 4h 00m | 0.2913 | `cautious` | `[score_cautious]` |
| `2022-04-21 07:00:00+0000` | `EURUSD` | `BUY` | 1.08308 | `WIN` | 16.7 | 1h 50m | 0.3209 | `normal` | `[score_normal]` |
| `2022-04-21 08:50:00+0000` | `EURUSD` | `BUY` | 1.08507 | `WIN` | 17.7 | 45m | 0.4703 | `premium` | `[score_premium]` |
| `2022-04-21 09:35:00+0000` | `EURUSD` | `BUY` | 1.08796 | `WIN` | 15.7 | 20m | 0.5086 | `premium` | `[score_premium]` |
| `2022-04-21 09:55:00+0000` | `EURUSD` | `BUY` | 1.08992 | `LOSS` | -13.4 | 15m | 0.3080 | `normal` | `[score_normal]` |
| `2022-04-21 10:10:00+0000` | `EURUSD` | `BUY` | 1.08967 | `WIN` | 16.7 | 30m | 0.5953 | `premium` | `[score_premium]` |
| `2022-04-21 10:40:00+0000` | `EURUSD` | `BUY` | 1.09156 | `WIN` | 16.4 | 15m | 0.6358 | `premium` | `[score_premium]` |
| `2022-04-21 10:55:00+0000` | `EURUSD` | `BUY` | 1.09268 | `LOSS` | -12.5 | 15m | 0.3824 | `normal` | `[score_normal]` |
| `2022-04-21 11:10:00+0000` | `EURUSD` | `BUY` | 1.09187 | `LOSS` | -12.9 | 1h 40m | 0.3008 | `normal` | `[score_normal]` |
| `2022-04-21 12:50:00+0000` | `EURUSD` | `SELL` | 1.09094 | `LOSS` | -13.9 | 35m | 0.2657 | `cautious` | `[score_cautious]` |
| `2022-04-21 14:00:00+0000` | `EURUSD` | `SELL` | 1.09004 | `WIN` | 17.0 | 25m | 0.2726 | `cautious` | `[score_cautious]` |
| `2022-04-21 17:05:00+0000` | `EURUSD` | `SELL` | 1.08669 | `WIN` | 17.6 | 50m | 0.3180 | `normal` | `[score_normal]` |
| `2022-04-22 08:15:00+0000` | `EURUSD` | `SELL` | 1.08478 | `WIN` | 17.2 | 1h 40m | 0.3071 | `normal` | `[score_normal]` |
| `2022-04-22 09:55:00+0000` | `EURUSD` | `SELL` | 1.08264 | `WIN` | 16.8 | 20m | 0.4671 | `premium` | `[score_premium]` |
| `2022-04-22 10:15:00+0000` | `EURUSD` | `BUY` | 1.08045 | `LOSS` | -13.7 | 1h 15m | 0.3012 | `normal` | `[score_normal]` |
| `2022-04-22 11:30:00+0000` | `EURUSD` | `BUY` | 1.07932 | `WIN` | 16.1 | 2h 30m | 0.5593 | `premium` | `[score_premium]` |
| `2022-04-22 14:00:00+0000` | `EURUSD` | `BUY` | 1.08156 | `WIN` | 16.1 | 2h 10m | 0.5187 | `premium` | `[score_premium]` |
| `2022-04-22 17:00:00+0000` | `EURUSD` | `BUY` | 1.08062 | `LOSS` | -13.6 | 35m | 0.3164 | `normal` | `[score_normal]` |
| `2022-04-22 17:55:00+0000` | `EURUSD` | `BUY` | 1.07774 | `WIN` | 9.6 | 4h 00m | 0.2286 | `cautious` | `[score_cautious]` |
| `2022-04-22 21:55:00+0000` | `EURUSD` | `SELL` | 1.07917 | `WIN` | 16.7 | 2h 05m | 0.2395 | `cautious` | `[score_cautious]` |
| `2022-04-26 09:20:00+0000` | `EURUSD` | `SELL` | 1.07167 | `WIN` | 17.0 | 1h 00m | 0.5728 | `premium` | `[score_premium]` |
| `2022-04-26 10:20:00+0000` | `EURUSD` | `SELL` | 1.06941 | `WIN` | 17.1 | 45m | 0.5831 | `premium` | `[score_premium]` |
| `2022-04-26 11:05:00+0000` | `EURUSD` | `SELL` | 1.06760 | `LOSS` | -12.6 | 20m | 0.2980 | `cautious` | `[score_cautious]` |
| `2022-04-26 11:25:00+0000` | `EURUSD` | `SELL` | 1.06888 | `WIN` | 12.7 | 4h 00m | 0.4878 | `premium` | `[score_premium]` |
| `2022-04-26 17:00:00+0000` | `EURUSD` | `SELL` | 1.06744 | `WIN` | 16.8 | 45m | 0.3888 | `normal` | `[score_normal]` |
| `2022-04-26 17:45:00+0000` | `EURUSD` | `BUY` | 1.06446 | `WIN` | 17.0 | 1h 35m | 0.3720 | `normal` | `[score_normal]` |
| `2022-04-26 19:20:00+0000` | `EURUSD` | `SELL` | 1.06644 | `WIN` | 17.0 | 1h 45m | 0.5346 | `premium` | `[score_premium]` |
| `2022-04-27 09:15:00+0000` | `EURUSD` | `SELL` | 1.06283 | `WIN` | 17.1 | 1h 05m | 0.4001 | `premium` | `[score_premium]` |
| `2022-04-27 10:20:00+0000` | `EURUSD` | `SELL` | 1.06082 | `WIN` | 16.4 | 10m | 0.6214 | `premium` | `[score_premium]` |
| `2022-04-27 10:50:00+0000` | `EURUSD` | `SELL` | 1.06160 | `WIN` | 16.4 | 1h 00m | 0.3811 | `normal` | `[score_normal]` |
| `2022-04-27 11:50:00+0000` | `EURUSD` | `SELL` | 1.05971 | `LOSS` | -13.3 | 10m | 0.3399 | `normal` | `[score_normal]` |
| `2022-04-27 12:00:00+0000` | `EURUSD` | `SELL` | 1.05886 | `LOSS` | -13.0 | 10m | 0.4811 | `premium` | `[score_premium]` |
| `2022-04-27 12:10:00+0000` | `EURUSD` | `SELL` | 1.05963 | `LOSS` | -13.6 | 15m | 0.4633 | `premium` | `[score_premium]` |
| `2022-04-27 12:25:00+0000` | `EURUSD` | `SELL` | 1.06130 | `WIN` | 16.2 | 2h 05m | 0.6369 | `premium` | `[score_premium]` |
| `2022-04-27 14:30:00+0000` | `EURUSD` | `SELL` | 1.05937 | `WIN` | 16.1 | 1h 00m | 0.7678 | `premium` | `[score_premium]` |
| `2022-04-27 17:00:00+0000` | `EURUSD` | `SELL` | 1.05484 | `WIN` | 15.7 | 35m | 0.7005 | `premium` | `[score_premium]` |
| `2022-04-27 17:35:00+0000` | `EURUSD` | `BUY` | 1.05353 | `LOSS` | -12.9 | 20m | 0.4747 | `premium` | `[score_premium]` |
| `2022-04-27 17:55:00+0000` | `EURUSD` | `SELL` | 1.05265 | `LOSS` | -13.1 | 25m | 0.3139 | `normal` | `[score_normal]` |
| `2022-04-27 18:20:00+0000` | `EURUSD` | `SELL` | 1.05376 | `LOSS` | -14.1 | 15m | 0.2744 | `cautious` | `[score_cautious]` |
| `2022-04-27 18:35:00+0000` | `EURUSD` | `SELL` | 1.05522 | `LOSS` | -12.7 | 55m | 0.2997 | `cautious` | `[score_cautious]` |
| `2022-04-28 07:45:00+0000` | `EURUSD` | `SELL` | 1.05242 | `WIN` | 17.2 | 20m | 0.5219 | `premium` | `[score_premium]` |
| `2022-04-28 08:40:00+0000` | `EURUSD` | `BUY` | 1.05007 | `LOSS` | -13.1 | 5m | 0.3676 | `normal` | `[score_normal]` |
| `2022-04-28 08:45:00+0000` | `EURUSD` | `SELL` | 1.04916 | `LOSS` | -13.1 | 5m | 0.4487 | `premium` | `[score_premium]` |
| `2022-04-28 08:50:00+0000` | `EURUSD` | `SELL` | 1.05176 | `LOSS` | -12.9 | 1h 00m | 0.4192 | `premium` | `[score_premium]` |
| `2022-04-28 11:40:00+0000` | `EURUSD` | `SELL` | 1.05324 | `WIN` | 16.2 | 1h 45m | 0.2077 | `cautious` | `[score_cautious]` |
| `2022-04-28 14:10:00+0000` | `EURUSD` | `SELL` | 1.05040 | `WIN` | 16.6 | 1h 10m | 0.3923 | `normal` | `[score_normal]` |
| `2022-04-28 17:00:00+0000` | `EURUSD` | `SELL` | 1.05084 | `LOSS` | -14.0 | 10m | 0.3130 | `normal` | `[score_normal]` |
| `2022-04-28 17:10:00+0000` | `EURUSD` | `SELL` | 1.05125 | `WIN` | 16.4 | 25m | 0.4386 | `premium` | `[score_premium]` |
| `2022-04-28 17:35:00+0000` | `EURUSD` | `BUY` | 1.04913 | `WIN` | 16.2 | 25m | 0.7231 | `premium` | `[score_premium]` |
| `2022-04-28 18:00:00+0000` | `EURUSD` | `SELL` | 1.05148 | `LOSS` | -13.9 | 10m | 0.2907 | `cautious` | `[score_cautious]` |
| `2022-04-28 18:10:00+0000` | `EURUSD` | `SELL` | 1.05238 | `WIN` | 16.0 | 45m | 0.4551 | `premium` | `[score_premium]` |
| `2022-04-28 18:55:00+0000` | `EURUSD` | `SELL` | 1.05034 | `LOSS` | -12.9 | 55m | 0.4953 | `premium` | `[score_premium]` |
| `2022-04-29 08:15:00+0000` | `EURUSD` | `BUY` | 1.05266 | `WIN` | 16.3 | 1h 10m | 0.5807 | `premium` | `[score_premium]` |
| `2022-04-29 09:25:00+0000` | `EURUSD` | `BUY` | 1.05463 | `LOSS` | -13.1 | 45m | 0.4262 | `premium` | `[score_premium]` |
| `2022-04-29 10:10:00+0000` | `EURUSD` | `BUY` | 1.05406 | `WIN` | 15.7 | 25m | 0.7289 | `premium` | `[score_premium]` |
| `2022-04-29 10:35:00+0000` | `EURUSD` | `BUY` | 1.05617 | `WIN` | 17.5 | 1h 10m | 0.7052 | `premium` | `[score_premium]` |
| `2022-04-29 11:45:00+0000` | `EURUSD` | `SELL` | 1.05883 | `WIN` | 16.7 | 15m | 0.5794 | `premium` | `[score_premium]` |
| `2022-04-29 12:00:00+0000` | `EURUSD` | `SELL` | 1.05689 | `LOSS` | -13.0 | 50m | 0.5035 | `premium` | `[score_premium]` |
| `2022-04-29 12:50:00+0000` | `EURUSD` | `SELL` | 1.05788 | `WIN` | 16.3 | 1h 25m | 0.5790 | `premium` | `[score_premium]` |
| `2022-04-29 14:15:00+0000` | `EURUSD` | `SELL` | 1.05588 | `LOSS` | -13.1 | 15m | 0.3538 | `normal` | `[score_normal]` |
| `2022-04-29 14:30:00+0000` | `EURUSD` | `SELL` | 1.05741 | `WIN` | 16.8 | 10m | 0.5692 | `premium` | `[score_premium]` |
| `2022-04-29 14:40:00+0000` | `EURUSD` | `SELL` | 1.05563 | `WIN` | 17.4 | 40m | 0.6328 | `premium` | `[score_premium]` |
| `2022-04-29 17:00:00+0000` | `EURUSD` | `BUY` | 1.05337 | `LOSS` | -13.7 | 30m | 0.4533 | `premium` | `[score_premium]` |
| `2022-04-29 17:30:00+0000` | `EURUSD` | `BUY` | 1.05245 | `WIN` | 16.1 | 25m | 0.5791 | `premium` | `[score_premium]` |
| `2022-04-29 17:55:00+0000` | `EURUSD` | `BUY` | 1.05440 | `LOSS` | -12.4 | 35m | 0.3991 | `normal` | `[score_normal]` |
| `2022-04-29 18:30:00+0000` | `EURUSD` | `BUY` | 1.05348 | `WIN` | 17.5 | 1h 35m | 0.5128 | `premium` | `[score_premium]` |
| `2022-04-29 21:00:00+0000` | `EURUSD` | `SELL` | 1.05728 | `WIN` | 17.4 | 1h 35m | 0.6650 | `premium` | `[score_premium]` |

### 2026-04

| Timestamp entrada | Simbolo | Direccion | Entry price | Resultado | Net pips | Duracion | Score | Aggression mode | Reason codes |
| --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- |
| `2026-04-02 08:50:00+0000` | `EURUSD` | `SELL` | 1.15261 | `LOSS` | -13.2 | 1h 15m | 0.3561 | `normal` | `[score_normal]` |
| `2026-04-02 10:05:00+0000` | `EURUSD` | `SELL` | 1.15334 | `WIN` | 16.5 | 3h 15m | 0.4934 | `premium` | `[score_premium]` |
| `2026-04-03 21:00:00+0000` | `EURUSD` | `SELL` | 1.15201 | `LOSS` | -13.0 | 2h 15m | 0.3257 | `normal` | `[score_normal]` |

## Limitaciones

- `exit_price` no se incluye porque no existe en `ceo_magi_v3_decisions.csv` ni fue requerido en este formato rehecho.
- Los pips son equivalentes derivados de R con SL fijo de `10` pips; no son pips reportados por broker.
- `2026-04` tiene datos parciales: en el universo disponible solo hay operaciones hasta mediados de abril y solo 3 entradas aprobadas por CEO-MAGI v3.
- La duracion depende de `exit_timestamp`; si un trade fue timeout, la duracion refleja el cierre usado por la validacion offline.

## Archivos Generados

- `artifacts\ceo_magi_v3\stress_months_trade_audit_full.csv`
- `artifacts\ceo_magi_v3\stress_months_monthly_summary_full.csv`
- `artifacts\ceo_magi_v3\stress_months_trade_audit_full.md`
