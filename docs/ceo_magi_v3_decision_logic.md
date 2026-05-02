# CEO-MAGI v3 Decision Logic

Version: pre-production candidate  
Scope: final decision layer for entries only  
Status: formalized from validated MAGI v2 / online priority scoring results

## Objective

CEO-MAGI v3 converts the votes from Baltasar, Gaspar, Melchor, and the already calculated priority score into one executable decision for Bot B.

This layer does not train models, does not change the score formula, and does not change the rules of Baltasar, Gaspar, or Melchor. It only decides whether a trade is allowed and with what execution mode.

## Inputs

CEO-MAGI v3 receives one candidate signal at the decision timestamp.

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `timestamp` | string ISO-8601 | Decision time. |
| `symbol` | string | Trading symbol, e.g. `EURUSD`. |
| `baltasar_vote` | object | Directional opportunity vote. |
| `gaspar_vote` | object | Market context / deterioration vote. |
| `melchor_vote` | object | Risk-control vote. |
| `score` | number | Priority score already calculated by the validated formula. |
| `trade_plan` | object | Entry, SL, TP and sizing fields prepared upstream. |
| `active_trade` | boolean | Whether there is already one open trade. |

Expected vote fields:

```json
{
  "baltasar_vote": {
    "direction": "BUY",
    "confidence": 0.64,
    "signal": "ENTER_BUY"
  },
  "gaspar_vote": {
    "context": "NEUTRAL",
    "p_deteriorating": 0.32,
    "signal": "ALLOW"
  },
  "melchor_vote": {
    "signal": "APPROVE",
    "risk_flags": []
  }
}
```

Allowed normalized values:

| Module | Field | Allowed values |
| --- | --- | --- |
| Baltasar | `direction` | `BUY`, `SELL`, `NONE` |
| Baltasar | `signal` | `ENTER_BUY`, `ENTER_SELL`, `NO_SIGNAL` |
| Gaspar | `signal` | `ALLOW`, `CAUTION`, `BLOCK`, `UNKNOWN` |
| Melchor | `signal` | `APPROVE`, `CAUTION`, `BLOCK` |

## Decision Order

Rules are evaluated in this exact order:

1. If `active_trade = true`, return `DO_NOTHING`.
2. If Melchor returns `BLOCK`, return `DO_NOTHING`.
3. If Baltasar has no valid direction, return `DO_NOTHING`.
4. If `score < 0.20`, return `DO_NOTHING`.
5. Assign a base execution mode from the score.
6. Apply Gaspar deterioration adjustment.
7. Emit the final JSON decision for Bot B.

Melchor is a hard veto. Gaspar is not a hard veto in this version unless its upstream vote is already represented through Melchor or the score.

## Score Bands

| Score range | Base action | Base mode | Meaning |
| --- | --- | --- | --- |
| `< 0.20` | `DO_NOTHING` | `none` | Signal is below the validated operational threshold. |
| `0.20 <= score < 0.30` | `ENTER` | `cautious` | Trade allowed, but with defensive execution. |
| `0.30 <= score < 0.40` | `ENTER` | `normal` | Trade allowed with standard execution. |
| `score >= 0.40` | `ENTER` | `premium` | Highest-quality bucket; trade allowed with premium execution. |

The validated operating candidate is `min_score = 0.20`. Higher bands are quality tiers, not new model rules.

## Gaspar Integration

Gaspar reduces aggressiveness when deterioration risk is high.

Definition:

```text
gaspar_high_deterioration = gaspar_vote.p_deteriorating >= 0.70
```

Adjustment:

| Base mode | If Gaspar deterioration is high |
| --- | --- |
| `premium` | downgrade to `normal` |
| `normal` | downgrade to `cautious` |
| `cautious` | remain `cautious` |
| `none` | remain `none` |

Gaspar can also add a warning to `risk_notes`, but it does not override Melchor's hard veto rule.

## Execution Mode Meaning

Bot B receives the mode but must not reinterpret the trade.

| Mode | Intended execution behavior |
| --- | --- |
| `cautious` | Execute only the approved trade plan with conservative size or execution settings configured by risk policy. |
| `normal` | Execute the standard approved trade plan. |
| `premium` | Execute the approved trade plan with premium treatment allowed by risk policy. |

Sizing multipliers are intentionally not hard-coded here. They belong to the risk/execution configuration, not to the decision logic.

## Reference Logic

```python
def decide_ceo_magi_v3(signal: dict) -> dict:
    score = float(signal["score"])
    baltasar = signal["baltasar_vote"]
    gaspar = signal["gaspar_vote"]
    melchor = signal["melchor_vote"]

    if signal.get("active_trade", False):
        return do_nothing(signal, "active_trade_exists")

    if str(melchor.get("signal", "")).upper() == "BLOCK":
        return do_nothing(signal, "melchor_block")

    direction = str(baltasar.get("direction", "NONE")).upper()
    if direction not in {"BUY", "SELL"}:
        return do_nothing(signal, "no_valid_baltasar_direction")

    if score < 0.20:
        return do_nothing(signal, "score_below_0_20")

    if score < 0.30:
        mode = "cautious"
    elif score < 0.40:
        mode = "normal"
    else:
        mode = "premium"

    gaspar_p = float(gaspar.get("p_deteriorating", 0.0) or 0.0)
    gaspar_adjusted = False
    if gaspar_p >= 0.70:
        gaspar_adjusted = True
        if mode == "premium":
            mode = "normal"
        elif mode == "normal":
            mode = "cautious"

    return enter(signal, direction, mode, gaspar_adjusted)
```

## Output JSON for Bot B

When CEO decides not to trade:

```json
{
  "schema_version": "ceo_magi_v3.entry_decision.v1",
  "decision_id": "EURUSD-2026-04-10T14:35:00Z",
  "timestamp": "2026-04-10T14:35:00Z",
  "symbol": "EURUSD",
  "action": "DO_NOTHING",
  "execution_mode": "none",
  "direction": null,
  "entry_price": null,
  "stop_loss": null,
  "take_profit": null,
  "score": 0.1842,
  "reason_code": "score_below_0_20",
  "risk_notes": [
    "Score below validated operational threshold."
  ],
  "source": {
    "policy": "CEO-MAGI v3",
    "score_formula": "unchanged_online_priority_score",
    "min_operational_score": 0.2
  }
}
```

When CEO allows a trade:

```json
{
  "schema_version": "ceo_magi_v3.entry_decision.v1",
  "decision_id": "EURUSD-2026-04-10T14:35:00Z",
  "timestamp": "2026-04-10T14:35:00Z",
  "symbol": "EURUSD",
  "action": "ENTER",
  "execution_mode": "normal",
  "direction": "BUY",
  "entry_price": 1.08425,
  "stop_loss": 1.08325,
  "take_profit": 1.08625,
  "score": 0.4261,
  "reason_code": "score_premium_gaspar_downgraded",
  "risk_notes": [
    "Score is in premium band.",
    "Gaspar deterioration is high; execution mode downgraded from premium to normal."
  ],
  "votes": {
    "baltasar": {
      "signal": "ENTER_BUY",
      "direction": "BUY",
      "confidence": 0.71
    },
    "gaspar": {
      "signal": "CAUTION",
      "p_deteriorating": 0.74,
      "context": "UNFAVORABLE"
    },
    "melchor": {
      "signal": "APPROVE",
      "risk_flags": []
    }
  },
  "source": {
    "policy": "CEO-MAGI v3",
    "score_formula": "unchanged_online_priority_score",
    "min_operational_score": 0.2
  }
}
```

## Reason Codes

| Code | Meaning |
| --- | --- |
| `active_trade_exists` | CEO refuses a new entry because only one trade can be active. |
| `melchor_block` | Melchor vetoed the trade. |
| `no_valid_baltasar_direction` | No executable BUY/SELL direction exists. |
| `score_below_0_20` | Score is below the validated operational threshold. |
| `score_cautious` | Score is between `0.20` and `0.30`. |
| `score_normal` | Score is between `0.30` and `0.40`. |
| `score_premium` | Score is `>= 0.40`. |
| `score_normal_gaspar_downgraded` | Score was normal, but Gaspar high deterioration reduced mode to cautious. |
| `score_premium_gaspar_downgraded` | Score was premium, but Gaspar high deterioration reduced mode to normal. |

## Operational Notes

- CEO-MAGI v3 must process signals chronologically.
- If there is an open trade, new entry signals are ignored until that trade closes.
- The score must be calculated before this layer using only causal information available at the decision timestamp.
- This policy does not inspect `realized_R`, outcome, exit timestamp, target hit, stop hit, future bars, or any post-entry information.
- Bot B must execute only the JSON instruction emitted by CEO-MAGI v3.

## Final Policy

CEO-MAGI v3 is a deterministic execution gate:

1. Melchor protects the account with a hard veto.
2. The validated score threshold `0.20` decides whether the trade is operational.
3. Score bands define execution mode.
4. Gaspar reduces aggression when market deterioration is high.
5. Bot B receives one explicit action: `DO_NOTHING` or `ENTER`.

