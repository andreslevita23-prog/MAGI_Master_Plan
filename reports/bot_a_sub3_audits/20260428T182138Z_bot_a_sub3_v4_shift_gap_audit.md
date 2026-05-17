# Bot_A_sub3 v4 Shift Gap Audit

- Dataset: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00`
- Latest marker: `__runtime_marker__bot_a_sub3_operational_snapshot_2026-04-28_v4_shift_gap_buffer_fix.txt`
- Decision: `NO APTO`
- Score: `25`
- CSV files: `86`; JSONL files: `86`
- CSV rows: `48692`; JSONL rows: `48692`; unique snapshot_id: `24346`
- Duplicate snapshot_id: `24346` ids / `24346` duplicate rows
- JSONL parse errors: `0`; CSV parse errors: `0`; features_json parse errors: `0`

## V4 Last Occurrence Metrics
- Features: `97384`
- Data source status: `{'OK': 90480, 'ALIGNMENT_ERROR': 6904}`
- Data source pct: `{'OK': 92.9105, 'ALIGNMENT_ERROR': 7.0895}`
- Alignment status: `{'ok': 90480, 'error': 6904}`
- By timeframe data source: `{'D1': {'OK': 18624, 'ALIGNMENT_ERROR': 5722}, 'H1': {'OK': 24130, 'ALIGNMENT_ERROR': 216}, 'H4': {'OK': 23424, 'ALIGNMENT_ERROR': 922}, 'M15': {'OK': 24302, 'ALIGNMENT_ERROR': 44}}`
- By timeframe alignment: `{'D1': {'ok': 18624, 'error': 5722}, 'H1': {'ok': 24130, 'error': 216}, 'H4': {'ok': 23424, 'error': 922}, 'M15': {'ok': 24302, 'error': 44}}`
- Age stats: `{'M15': {'count': 24302, 'min': 0.0, 'p50': 5.0, 'p95': 10.0, 'max': 10.0, 'over_limit': 0}, 'H1': {'count': 24130, 'min': 0.0, 'p50': 30.0, 'p95': 55.0, 'max': 55.0, 'over_limit': 0}, 'H4': {'count': 23424, 'min': 0.0, 'p50': 115.0, 'p95': 225.0, 'max': 235.0, 'over_limit': 0}, 'D1': {'count': 18624, 'min': 0.0, 'p50': 715.0, 'p95': 1360.0, 'max': 1435.0, 'over_limit': 0}}`
- selected_bar_inconsistent: `0`
- selected_mismatch_new_after_ordering: `0`
- no_closed_bar_within_limit: `6904`
- INSUFFICIENT_HISTORY: `0`
- OK semantic mismatch: `0`

## Comparison
| Metric | Previous reference | V4 last occurrence | Delta |
|---|---:|---:|---:|
| MTF OK % | 91.38 | 92.9105 | +1.5305 |
| ALIGNMENT_ERROR % | 7.09 | 7.0895 | -0.0005 |
| INSUFFICIENT_HISTORY % | 1.53 | 0 | -1.5300 |
| selected_bar_inconsistent | 0 | 0 | +0 |
| no_closed_bar_within_limit | 6904 | 6904 | +0 |

## Top Warnings V4
- `5722`: no hay vela cerrada dentro de 0..1440.00 minutos previos al anchor
- `922`: no hay vela cerrada dentro de 0..240.00 minutos previos al anchor
- `216`: no hay vela cerrada dentro de 0..60.00 minutos previos al anchor
- `44`: no hay vela cerrada dentro de 0..15.00 minutos previos al anchor
