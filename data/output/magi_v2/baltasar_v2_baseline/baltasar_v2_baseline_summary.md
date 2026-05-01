# Baltasar v2 Baseline

## Scope

- Target: `tradeable_direction_rr2_first_touch`.
- Model: `RandomForestClassifier`.
- This is an experimental baseline; Baltasar v1 is not replaced.

## Splits

| split | rows | start | end | DO_NOTHING | ENTER_BUY | ENTER_SELL |
| --- | --- | --- | --- | --- | --- | --- |
| train | 237132 | 2020-01-15T00:00:00+00:00 | 2023-12-29T23:55:00+00:00 | 139635 | 48210 | 49287 |
| validation | 59378 | 2024-01-02T00:00:00+00:00 | 2024-12-31T23:55:00+00:00 | 42450 | 8148 | 8780 |
| test | 74991 | 2025-01-02T00:00:30+00:00 | 2026-04-14T22:55:00+00:00 | 43774 | 15606 | 15611 |

## Threshold Metrics

### Validation

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.60 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.80 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

### Test

| threshold | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD | BUY_precision | SELL_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.60 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.70 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |
| 0.80 | 0 | 0.000000 |  |  |  |  | 0.000000 |  |  |

## Baltasar v1 Signal Comparison

| split | trades | coverage | trade_precision | avg_r | total_r | PF | max_DD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | 26701 | 0.449678 | 0.186173 | 0.006375 | 170.080000 | 1.012434 | 878.240000 |
| test | 48457 | 0.646171 | 0.263264 | 0.083469 | 4037.150000 | 1.152036 | 766.960000 |

## Top Feature Importance

| feature | importance |
| --- | --- |
| numeric__hour | 0.103579 |
| categorical__melchor_signal_BLOCK | 0.076626 |
| categorical__melchor_risk_flags_LOW | 0.066614 |
| categorical__mage_agreement_BLOCKED_BY_MELCHOR | 0.065893 |
| categorical__melchor_risk_flags_HIGH | 0.065241 |
| categorical__melchor_signal_APPROVE | 0.058455 |
| categorical__baltasar_signal_NEUTRAL | 0.052051 |
| categorical__mage_agreement_ACTIONABLE_CONSENSUS | 0.042907 |
| categorical__session_asia | 0.036616 |
| categorical__session_overlap | 0.034182 |
| categorical__weekday_friday | 0.032025 |
| categorical__baltasar_gaspar_alignment_BALTASAR_NEUTRAL | 0.032010 |
| numeric__daily_range_position | 0.026643 |
| numeric__atr | 0.023221 |
| categorical__session_new_york | 0.019879 |
| numeric__baltasar_confidence | 0.019874 |
| numeric__spread_pips | 0.018525 |
| categorical__session_london | 0.017540 |
| categorical__baltasar_signal_BUY | 0.015891 |
| categorical__session_inactive | 0.014096 |

## Leakage Check

- Passed: `True`
- Forbidden features in model: `[]`

## Technical Notes

- buy_R and sell_R are used only for evaluation, never as model features.
- Threshold decisions execute only if ENTER_BUY or ENTER_SELL probability exceeds the threshold; otherwise DO_NOTHING.
- Baltasar v1 comparison maps baltasar_signal BUY/SELL to ENTER_BUY/ENTER_SELL and all other values to DO_NOTHING.
- n_jobs=1 avoids Windows sandbox/joblib worker permission issues.
