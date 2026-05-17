# CopyRates Fix Verification

- Verdict: `FIX FALLIDO`
- Score: `35`
- Current run: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-14_00-00-00`
- Previous run: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub3\run_2025-12-15_00-00-00`

## Persistence
- CSV/JSONL files: `102` / `102`
- CSV/JSONL rows: `24346` / `24346`
- Newest file time: `2026-04-28T01:56:29.029828`

## Structural
- JSON errors: `0`
- CSV errors: `0`
- Bad features_json: `0`
- Duplicate snapshot_id: `0`
- New fix field counts: `{}`

## MTF
- Snapshot mtf_data_source_status: `{'ALIGNMENT_ERROR': 24346}`
- Feature alignment_status: `{'error': {'count': 97384, 'pct': 100.0}}`
- TF alignment_status: `{'M15': {'error': 24346}, 'H1': {'error': 24346}, 'H4': {'error': 24346}, 'D1': {'error': 24346}}`
- selected_bar_inconsistent: `{'count': 90480, 'pct_features': 92.91}`
- old rates0 message: `{'count': 90480, 'pct_features': 92.91}`

## Compare Previous
- Previous selected_bar_inconsistent: `{'count': 95852, 'pct_features': 92.96}`
- Previous feature alignment_status: `{'error': {'count': 103116, 'pct': 100.0}}`

## Top Reasons
- `5722` (5.88%): no hay vela cerrada dentro de 0..1440.00 minutos previos al anchor
- `922` (0.95%): no hay vela cerrada dentro de 0..240.00 minutos previos al anchor
- `288` (0.3%): vela seleccionada inconsistente: selected=2025-12-30T00:00:00 rates0=2025-12-22T00:00:00
- `288` (0.3%): vela seleccionada inconsistente: selected=2026-01-05T00:00:00 rates0=2025-12-26T00:00:00
- `288` (0.3%): vela seleccionada inconsistente: selected=2026-01-06T00:00:00 rates0=2025-12-29T00:00:00
- `288` (0.3%): vela seleccionada inconsistente: selected=2026-01-07T00:00:00 rates0=2025-12-30T00:00:00
- `288` (0.3%): vela seleccionada inconsistente: selected=2026-01-08T00:00:00 rates0=2025-12-31T00:00:00
- `288` (0.3%): vela seleccionada inconsistente: selected=2026-01-12T00:00:00 rates0=2026-01-05T00:00:00

## Correction
- El veredicto se clasifica como `FIX FALLIDO` porque el dataset no incluye los campos nuevos del fix (`selected_array_index`, `copied_array_size`, `rates_array_as_series`) y conserva mensajes antiguos `rates0`. Esto indica que la corrida no us? el core recompilado con la reconstrucci?n de buffer.
