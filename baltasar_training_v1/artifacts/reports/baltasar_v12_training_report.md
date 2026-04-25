# Baltasar v1.2 Training Report

## Dataset Located

- Source run: `run_2024-04-15_00-00-00`
- Source path: `C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub1\run_2024-04-15_00-00-00`
- Source type: `directory`
- CSV files: `520`
- Rows before target drop: `148551`
- Columns: `35`
- Timestamp min: `2024-04-15 00:00:00+00:00`
- Timestamp max: `2026-04-14 23:50:00+00:00`
- Approx months: `23.95`

## Quick Validation

- Duplicate rows: `0`
- Duplicate snapshot ids: `0`
- Null timestamp rows: `0`
- Median gap minutes: `5.0000`
- P95 gap minutes: `5.0000`
- Gaps over 8h: `110`
- Largest gap hours: `49.0833`
- Missing required columns: `[]`
- Validation passed: `True`

## Baltasar v1.2 Metrics

      version target_name feature_variant    model_name                                                                                                    dataset_path  dataset_rows  feature_count  accuracy  precision_macro  recall_macro  f1_macro  walk_forward_f1_mean  walk_forward_f1_std
Baltasar v1.2     h12_t03         compact baseline_tree C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub1\run_2024-04-15_00-00-00        148539             16  0.425374         0.395384      0.400140  0.390639              0.379223             0.014438
Baltasar v1.2     h12_t03         compact random_forest C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub1\run_2024-04-15_00-00-00        148539             16  0.419618         0.401273      0.402775  0.401418              0.386500             0.011886

## Metrics by Class

### baseline_tree

  label  precision   recall       f1  support
   SELL   0.321008 0.200092 0.246521     8721
NEUTRAL   0.496873 0.624907 0.553583    12077
    BUY   0.368270 0.375421 0.371811     8910

### random_forest

  label  precision   recall       f1  support
   SELL   0.330784 0.292627 0.310538     8721
NEUTRAL   0.517593 0.554194 0.535269    12077
    BUY   0.355440 0.361504 0.358446     8910

## v1.1 vs v1.2

      version    model_name  accuracy  f1_macro  walk_forward_f1_mean  walk_forward_f1_std
Baltasar v1.1 baseline_tree  0.393342  0.306621              0.312846             0.024333
Baltasar v1.1 random_forest  0.389848  0.388620              0.325108             0.061122
Baltasar v1.2 baseline_tree  0.425374  0.390639              0.379223             0.014438
Baltasar v1.2 random_forest  0.419618  0.401418              0.386500             0.011886

## Conclusion

- Esta comparacion indica si Baltasar mejora al escalar a 24 meses sin tocar tuning ni arquitectura.
- El criterio principal sigue siendo consistencia temporal y comportamiento por clase, no solo el mejor punto de F1.
