# Bot B Dry-Run Summary for CEO-MAGI v3

## Scope

- Input: `artifacts\ceo_magi_v3\ceo_magi_v3_decisions.jsonl`
- Mode: dry-run only
- Orders sent: `0`
- MT5 touched: `no`
- Bot B real modified: `no`

## Results

| Metric | Count |
| --- | ---: |
| Total decisions read | 6539 |
| ENTER valid | 3346 |
| DO_NOTHING valid | 3193 |
| Rejections | 0 |
| Payload warnings | 0 |

## ACK Status

| ACK status | Count |
| --- | ---: |
| `ACK_EXECUTABLE` | 3346 |
| `ACK_DO_NOTHING` | 3193 |

## Errors by Type

No schema errors found.

## Rejected Payload Examples

No rejected payloads.

## Operational Notes

- `ACK_EXECUTABLE` means the payload is structurally executable by Bot B, not that a broker order was sent.
- `ACK_DO_NOTHING` means Bot B can safely ignore the decision.
- `REJECT_INVALID_PAYLOAD` means Bot B should refuse the decision before any execution adapter sees it.
- The current CEO contract includes both `aggression_mode` and `execution_mode` for compatibility.

## Recommendation for Runtime Integration

Payloads are structurally ready for a runtime shadow mode. Next step: route JSONL decisions through a Bot B adapter stub that emits acknowledgements to Bot C without broker connectivity.

## Generated Files

- `artifacts\ceo_magi_v3\bot_b_dry_run_results.csv`
- `artifacts\ceo_magi_v3\bot_b_dry_run_summary.md`
- `artifacts\ceo_magi_v3\bot_b_dry_run_errors.jsonl`
