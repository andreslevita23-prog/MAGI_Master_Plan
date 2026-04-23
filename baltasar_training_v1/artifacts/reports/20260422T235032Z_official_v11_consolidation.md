# Baltasar v1.1 Official Consolidation Report

## Official Status

- Version: `Baltasar v1.1`
- Reference run: `20260422T235032Z`
- Official target: `h18_t05`
- Official feature variant: `compact`
- Official baseline model: `baseline_tree`
- Official challenger: `random_forest`

## Why v1.1 Was Promoted

- The target redesign improved balance and signal relative to the old `h12_t08` default.
- The compact feature variant reduced the working feature set while preserving informative relative-price structure.
- The official baseline was not chosen by best point F1 alone. Stability and explainability carried more weight.

## Official Benchmark

             role       version                     scenario_name target_name feature_variant    model_name  feature_count  accuracy  f1_macro  walk_forward_f1_mean  walk_forward_f1_std                                                              trade_off
official_baseline Baltasar v1.1 candidate_target_compact_features     h18_t05         compact baseline_tree             16  0.393342  0.306621              0.312846             0.024333     Chosen for higher temporal stability and clearer interpretability.
       challenger Baltasar v1.1 candidate_target_compact_features     h18_t05         compact random_forest             16  0.389848  0.388620              0.325108             0.061122 Kept as challenger due to stronger point metrics but weaker stability.

## Metrics by Class

Official baseline:

  label  precision   recall       f1  support
   SELL   0.302326 0.010788 0.020833     1205
NEUTRAL   0.567506 0.425021 0.486036     2334
    BUY   0.295610 0.685004 0.412994     1327

Official challenger:

  label  precision   recall       f1  support
   SELL   0.281220 0.482158 0.355243     1205
NEUTRAL   0.611604 0.325193 0.424615     2334
    BUY   0.357280 0.419744 0.386001     1327

## Trade-off Chosen

Baseline chosen: baseline_tree with holdout F1 0.3066, walk-forward mean 0.3128 and std 0.0243. Challenger random_forest reaches higher point F1 0.3886 and higher walk-forward mean 0.3251, but with materially higher dispersion (0.0611), so it remains a challenger rather than the official baseline.

## Compact Features Selected

- numeric__candle_range_ratio, numeric__normalized_recent_range, numeric__ema_gap_50_200, numeric__ema_gap_20_50, numeric__price_vs_ema20, numeric__rsi_14, numeric__ema_gap_20_200, categorical__structure_direction_bullish

## Why Not the Highest F1 Point Model

- `random_forest` on compact features performed better on point metrics.
- It showed noticeably worse temporal stability.
- For Baltasar v1.1, the laboratory prioritizes a baseline that is easier to explain, easier to track and less sensitive across market tramos.

## Pending for Future Phases

1. Re-run full training flows using v1.1 defaults as the normal path.
2. Decide whether challenger promotion should require a minimum stability threshold.
3. Evaluate calibration, cost-sensitive learning and label redesign refinements in later phases.
4. Prepare executive-facing storytelling and visuals without altering the technical baseline.
