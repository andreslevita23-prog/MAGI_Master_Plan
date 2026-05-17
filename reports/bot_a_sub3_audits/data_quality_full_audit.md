# Bot A sub3 Full Historical Data Quality Audit

## Resumen Ejecutivo

- Decision: **apto con advertencias**
- Dataset auditado: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3`
- Runs detectados: `2`
- Archivos JSONL: `1709`
- Archivos CSV: `1709`
- Tamaño total: `3024.95 MB`
- Snapshots únicos consolidados: `371513`
- Rango anchor: `2020-01-15T00:00:00Z` a `2026-04-14T23:55:00Z`
- Símbolos: `{'EURUSD': 371513}`
- Timeframes: `{'M5': 371513}`

## Problemas Encontrados

| Severidad | Código | Conteo | Impacto |
|---|---|---:|---|
| high | duplicate_snapshot_ids | 18612 | Duplicates must be removed before simulation. |
| medium | spread_extreme_gt_5_pips | 1467 | Extreme spreads may require filtering by session/news. |
| medium | forbidden_future_columns_present | 371513 | Forbidden feature names are present and must be stripped before modeling. |
| medium | temporal_gaps_EURUSD | 85 | Intraday M5 gaps can bias forward horizons. |

## Calidad

- Snapshots validos por flag fuente: `371513`
- Invalidos o sin flag valido: `0`
- Duplicados snapshot_id removidos de la vista unica: `18612`
- Duplicados symbol+anchor removidos de la vista unica: `0`
- OHLC invalido: `0`
- Spreads negativos: `0`
- Spreads extremos > 5 pips: `1467`
- Features completas: `100.0%`
- Gaspar context disponible: `100.0%`

## Chequeos Criticos MAGI

- Trigger no closed_bar: `0`
- Anchor distinto de M5: `0`
- MTF age failures: `{}`
- MTF close timestamp leakage: `{}`
- Gaspar MTF failures: `{}`
- Columnas futuras/prohibidas detectadas: `371513`
- Top columnas prohibidas: `{'position.floating_pnl': 371513}`
- Columnas futuras/prohibidas con valor no nulo: `0`
- Top columnas prohibidas no nulas: `{}`

## Distribucion De Mercado

- Conteo por año: `{'2020': 57775, '2021': 59739, '2022': 59868, '2023': 59751, '2024': 59377, '2025': 58681, '2026': 16322}`
- Conteo por sesión: `{'asia': 108438, 'inactive': 30600, 'london': 77499, 'new_york': 92969, 'overlap': 62007}`
- Spread pips: `{'count': 371513, 'mean': 0.415663, 'min': 0.1, 'p25': 0.1, 'median': 0.2, 'p75': 0.5, 'p95': 1.2, 'p99': 3.6, 'max': 31.9}`
- Rango M5 pips: `{'count': 371513, 'mean': 3.99464, 'min': 0.0, 'p25': 2.0, 'median': 3.2, 'p75': 5.0, 'p95': 9.6, 'p99': 16.2, 'max': 130.5}`

## Gaps Temporales

`{'EURUSD': {'ordered_unique_anchors': 371513, 'duplicate_anchor_count_after_id_dedupe': 0, 'gap_counts': {'major_gt_3_days': 185, 'market_closure_or_multiday': 149, 'intraday_30_to_240_min': 12, 'minor_5_to_30_min': 73}, 'max_gap_minutes': 5940.0, 'gap_examples': [{'from': '2020-01-17T23:55:00Z', 'to': '2020-01-21T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-01-25T00:00:00Z', 'to': '2020-01-28T00:00:00Z', 'minutes': 4320.0, 'bucket': 'market_closure_or_multiday'}, {'from': '2020-01-31T23:55:00Z', 'to': '2020-02-04T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-02-07T23:55:00Z', 'to': '2020-02-11T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-02-14T23:55:00Z', 'to': '2020-02-18T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-02-21T23:55:00Z', 'to': '2020-02-25T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-02-28T23:55:00Z', 'to': '2020-03-03T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-03-07T00:00:00Z', 'to': '2020-03-10T00:00:00Z', 'minutes': 4320.0, 'bucket': 'market_closure_or_multiday'}, {'from': '2020-03-13T22:55:00Z', 'to': '2020-03-17T00:00:00Z', 'minutes': 4385.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-03-20T22:55:00Z', 'to': '2020-03-24T00:00:00Z', 'minutes': 4385.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-03-27T22:55:00Z', 'to': '2020-03-31T00:00:00Z', 'minutes': 4385.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-04-03T23:55:00Z', 'to': '2020-04-07T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-04-10T23:55:00Z', 'to': '2020-04-14T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-04-17T23:55:00Z', 'to': '2020-04-21T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-04-24T23:55:00Z', 'to': '2020-04-28T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-05-01T23:55:00Z', 'to': '2020-05-05T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-05-08T23:55:00Z', 'to': '2020-05-12T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-05-15T23:55:00Z', 'to': '2020-05-19T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-05-22T23:55:00Z', 'to': '2020-05-26T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}, {'from': '2020-05-29T23:55:00Z', 'to': '2020-06-02T00:00:00Z', 'minutes': 4325.0, 'bucket': 'major_gt_3_days'}]}}`

## Propuesta De Limpieza

- Usar JSONL como fuente primaria y CSV solo como respaldo/inventario para evitar duplicados.
- Consolidar por snapshot_id y por (symbol, anchor_bar_timestamp), conservando el primer registro válido.
- Ordenar siempre por symbol + anchor_bar_timestamp antes de cualquier simulación.
- Filtrar snapshots con validation.is_valid=false o con OHLC inválido.
- Mantener timestamps normalizados a UTC y documentar campos fuente sin sufijo Z como UTC asumido.
- Crear un calendario de mercado para distinguir cierres normales de gaps intradía reales.
- Revisar snapshots con spread_pips > 5 y decidir si se filtran o se etiquetan como régimen de baja calidad.
- Aplicar leakage guard antes de entregar features a cualquier modelo.
