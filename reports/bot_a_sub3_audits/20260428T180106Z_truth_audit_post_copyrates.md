# Bot_A_sub3 Truth Audit Post CopyRates

- Score: `80`
- Root cause: `PARTIAL_HISTORY_GAPS`
- Run: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00`
- Files CSV/JSONL: `86` / `86`
- Rows CSV/JSONL/features: `24346` / `24346` / `97384`

## Structural
- JSON errors: `0`
- CSV errors: `0`
- Bad features_json: `0`
- Duplicate snapshot_id: `0`
- New fields: `{'selected_array_index': 97384, 'copied_array_size': 97384, 'rates_array_as_series': 97384}`
- Missing new fields: `0`

## MTF
- Snapshot mtf_data_source_status: `{'OK': 18603, 'ALIGNMENT_ERROR': 4364, 'INSUFFICIENT_HISTORY': 1379}`
- Feature data_source_status: `{'OK': {'count': 88987, 'pct': 91.38}, 'ALIGNMENT_ERROR': {'count': 6904, 'pct': 7.09}, 'INSUFFICIENT_HISTORY': {'count': 1493, 'pct': 1.53}}`
- Feature alignment_status: `{'ok': {'count': 88987, 'pct': 91.38}, 'error': {'count': 8397, 'pct': 8.62}}`
- TF alignment_status: `{'M15': {'ok': 24003, 'error': 343}, 'H1': {'ok': 22936, 'error': 1410}, 'H4': {'ok': 23424, 'error': 922}, 'D1': {'ok': 18624, 'error': 5722}}`
- Critical patterns: `{'selected_bar_inconsistent_old_or_rates0': 0, 'selected_mismatch_new_after_ordering': 0, 'no_closed_bar_within_limit': 6904}`
- Age stats: `{'M15': {'count': 24346, 'min': -1.0, 'max': 10.0, 'mean': 4.984227388482708, 'over_limit': 44, 'over_limit_pct': 0.18}, 'H1': {'count': 24346, 'min': -1.0, 'max': 55.0, 'mean': 27.24016265505627, 'over_limit': 216, 'over_limit_pct': 0.89}, 'H4': {'count': 24346, 'min': -1.0, 'max': 235.0, 'mean': 112.80448533640023, 'over_limit': 922, 'over_limit_pct': 3.79}, 'D1': {'count': 24346, 'min': -1.0, 'max': 1435.0, 'mean': 547.9215476875052, 'over_limit': 5722, 'over_limit_pct': 23.5}}`

## Readiness
- python_simulator: `APTO SOLO INGESTA/DEBUG`
- baltasar_training: `NO APTO`
- gaspar_training: `NO APTO`
- ceo_magi: `NO APTO`
- melchor: `NO APTO`

## Top Reasons
- `88987` (91.38%):
- `5722` (5.88%): no hay vela cerrada dentro de 0..1440.00 minutos previos al anchor
- `922` (0.95%): no hay vela cerrada dentro de 0..240.00 minutos previos al anchor
- `216` (0.22%): no hay vela cerrada dentro de 0..60.00 minutos previos al anchor
- `44` (0.05%): no hay vela cerrada dentro de 0..15.00 minutos previos al anchor
- `15` (0.02%): CopyRates por rango solo produjo 1 velas <= selected_bar_time=2025-12-26T00:00:00; requeridas=6
- `15` (0.02%): CopyRates por rango solo produjo 1 velas <= selected_bar_time=2026-01-02T00:00:00; requeridas=6
- `15` (0.02%): CopyRates por rango solo produjo 1 velas <= selected_bar_time=2026-01-05T00:00:00; requeridas=6
- `15` (0.02%): CopyRates por rango solo produjo 1 velas <= selected_bar_time=2026-01-12T00:00:00; requeridas=6
- `15` (0.02%): CopyRates por rango solo produjo 1 velas <= selected_bar_time=2026-01-19T00:00:00; requeridas=6
