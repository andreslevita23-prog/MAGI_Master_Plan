# Bot_A_sub3 Diagnostic Audit

- Verdict: `DIAGNOSTICO CORRECTO`
- Diagnostic score: `100`
- Run path: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00`
- CSV/JSONL files: `102` / `102`
- CSV/JSONL rows: `24346` / `24346`
- JSON errors: `0`
- CSV errors: `0`
- Bad features_json: `0`
- Duplicate snapshot_id: `0`

## Distributions
- Snapshot validation: `{'false': 24346}`
- Snapshot mtf_data_source_status: `{'ALIGNMENT_ERROR': 24346}`
- Feature data_source_status: `{'ALIGNMENT_ERROR': {'count': 97384, 'pct': 100.0}}`
- Feature alignment_status: `{'error': {'count': 97384, 'pct': 100.0}}`
- Root cause by snapshot: `{'B_ALIGNMENT_ERROR': {'count': 24346, 'pct': 100.0}}`

## Timeframe Detail
- Feature TF data_source_status: `{'M15': {'ALIGNMENT_ERROR': 24346}, 'H1': {'ALIGNMENT_ERROR': 24346}, 'H4': {'ALIGNMENT_ERROR': 24346}, 'D1': {'ALIGNMENT_ERROR': 24346}}`
- Feature TF alignment_status: `{'M15': {'error': 24346}, 'H1': {'error': 24346}, 'H4': {'error': 24346}, 'D1': {'error': 24346}}`
- Age stats: `{'M15': {'count': 24346, 'min': -1.0, 'max': 10.0, 'mean': 4.984227388482708, 'over_limit': 44}, 'H1': {'count': 24346, 'min': -1.0, 'max': 55.0, 'mean': 27.24016265505627, 'over_limit': 216}, 'H4': {'count': 24346, 'min': -1.0, 'max': 235.0, 'mean': 112.80448533640023, 'over_limit': 922}, 'D1': {'count': 24346, 'min': -1.0, 'max': 1435.0, 'mean': 547.9215476875052, 'over_limit': 5722}}`
- Bars stats: `{'M15': {'count': 24346, 'min': 48505, 'max': 56630, 'mean': 52571.25141707057}, 'H1': {'count': 24346, 'min': 12135, 'max': 14167, 'mean': 13151.958104000658}, 'H4': {'count': 24346, 'min': 3040, 'max': 3549, 'mean': 3294.4346915304363}, 'D1': {'count': 24346, 'min': 509, 'max': 593, 'mean': 550.9889509570361}}`

## Top Reasons
- `D1` `ALIGNMENT_ERROR` `error` count `5722`: no hay vela cerrada dentro de 0..1440.00 minutos previos al anchor
- `H4` `ALIGNMENT_ERROR` `error` count `922`: no hay vela cerrada dentro de 0..240.00 minutos previos al anchor
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2025-12-30T00:00:00 rates0=2025-12-22T00:00:00
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2026-01-05T00:00:00 rates0=2025-12-26T00:00:00
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2026-01-06T00:00:00 rates0=2025-12-29T00:00:00
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2026-01-07T00:00:00 rates0=2025-12-30T00:00:00
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2026-01-08T00:00:00 rates0=2025-12-31T00:00:00
- `D1` `ALIGNMENT_ERROR` `error` count `288`: vela seleccionada inconsistente: selected=2026-01-12T00:00:00 rates0=2026-01-05T00:00:00
