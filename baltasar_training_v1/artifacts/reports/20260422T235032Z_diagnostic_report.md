# Baltasar Diagnostic Report

## Executive Summary

- Run diagnosticada: `20260422T235032Z`
- Mejor modelo actual: `baseline_tree`
- Accuracy: 0.2227
- F1 macro: 0.2216
- Filas etiquetadas: 24333
- Clases observadas: {'NEUTRAL': 18416, 'SELL': 2967, 'BUY': 2950}

## Main Hypotheses

1. El target actual concentra 75.7% en `NEUTRAL` con una razon max/min de 6.24. Esto sugiere una tarea ruidosa y parcialmente desbalanceada donde las clases direccionales tienen menos soporte y mayor ambiguedad.
2. La matriz de confusion muestra que el modelo no aprende bien la frontera entre direccion y no-direccion: `NEUTRAL` tiene recall 0.1223, mientras `BUY` y `SELL` quedan en 0.2211 y 0.8308. La mayor parte del error ocurre confundiendo las clases direccionales con `NEUTRAL`.
3. Las features mas utiles parecen concentrarse en pocas senales de contexto (`recent_range, ema_50, anchor_open`), mientras varias variables aportan poco o nada (`position_type, open_positions_count, sl, tp, validation_is_valid`).
4. El spread temporal de `f1_macro` entre folds fue de 0.1097. Si este rango es amplio, el problema no es solo de capacidad del modelo sino de estabilidad del regimen de mercado.

## Target Audit

Se evaluaron 4 configuraciones de target derivado modificando horizonte y thresholds.

           name  horizon_steps  buy_threshold  sell_threshold  rows  neutral_share  buy_share  sell_share  imbalance_ratio  accuracy  f1_macro
tighter_h12_t05             12         0.0005         -0.0005 24333       0.577282   0.210455    0.212263         2.743019  0.354017  0.342600
 longer_h24_t08             24         0.0008         -0.0008 24321       0.620369   0.188315    0.191316         3.294323  0.316752  0.280688
current_h12_t08             12         0.0008         -0.0008 24333       0.756832   0.121235    0.121933         6.242712  0.222724  0.221556
 shorter_h6_t06              6         0.0006         -0.0006 24339       0.780722   0.109413    0.109865         7.135561  0.219187  0.198976

Lectura:
- Si thresholds mas laxos reducen el desbalance pero no mejoran `f1_macro`, el problema probablemente es ruido del label y no solo soporte por clase.
- Si horizontes mas largos cambian mucho la distribucion, la definicion actual del target puede no estar alineada con la escala informativa de las features.

## Class Diagnosis

Metricas por clase para el mejor modelo:

  label  precision   recall       f1  support
   SELL   0.136124 0.830795 0.233921      591
NEUTRAL   0.825758 0.122266 0.212995     3566
    BUY   0.214481 0.221127 0.217753      710

Interpretacion:
- El modelo actual esta dominado por errores entre `BUY/SELL` y `NEUTRAL`.
- Una accuracy baja junto con precision macro mayor que f1 macro suele indicar que el clasificador acierta algunos nichos pero no generaliza de forma balanceada.

## Feature Diagnosis

Top features por importancia:
- recent_range, ema_50, anchor_open, structure_direction, ema_20

Top features por score univariado:
- recent_range, ema_200, anchor_low, current_price, anchor_close

Pares numericos altamente correlacionados:
- anchor_close ~ current_price (1.00); anchor_high ~ anchor_close (1.00); anchor_low ~ anchor_close (1.00); anchor_open ~ anchor_low (1.00); anchor_high ~ current_price (1.00)

## Temporal Validation

Resumen walk-forward:

 fold             model_name  train_rows  test_rows                test_start                  test_end  accuracy  precision_macro  recall_macro  f1_macro                        error
    1          baseline_tree       12166       3041 2026-02-13 08:40:00+00:00 2026-03-02 03:25:00+00:00  0.314370         0.355829      0.347383  0.224379                          NaN
    1          random_forest       12166       3041 2026-02-13 08:40:00+00:00 2026-03-02 03:25:00+00:00  0.465636         0.354323      0.369851  0.305224                          NaN
    1 hist_gradient_boosting       12166       3041 2026-02-13 08:40:00+00:00 2026-03-02 03:25:00+00:00       NaN              NaN           NaN       NaN [WinError 5] Acceso denegado
    2          baseline_tree       15207       3041 2026-03-02 03:30:00+00:00 2026-03-16 17:45:00+00:00  0.276554         0.329469      0.341449  0.195565                          NaN
    2          random_forest       15207       3041 2026-03-02 03:30:00+00:00 2026-03-16 17:45:00+00:00  0.337389         0.268061      0.342155  0.249903                          NaN
    2 hist_gradient_boosting       15207       3041 2026-03-02 03:30:00+00:00 2026-03-16 17:45:00+00:00       NaN              NaN           NaN       NaN [WinError 5] Acceso denegado
    3          baseline_tree       18248       3041 2026-03-16 17:50:00+00:00 2026-03-31 09:10:00+00:00  0.266031         0.403945      0.375697  0.267387                          NaN
    3          random_forest       18248       3041 2026-03-16 17:50:00+00:00 2026-03-31 09:10:00+00:00  0.212101         0.320962      0.418059  0.216832                          NaN
    3 hist_gradient_boosting       18248       3041 2026-03-16 17:50:00+00:00 2026-03-31 09:10:00+00:00       NaN              NaN           NaN       NaN [WinError 5] Acceso denegado
    4          baseline_tree       21289       3041 2026-03-31 09:15:00+00:00 2026-04-14 22:35:00+00:00  0.224926         0.368614      0.388088  0.212482                          NaN
    4          random_forest       21289       3041 2026-03-31 09:15:00+00:00 2026-04-14 22:35:00+00:00  0.213745         0.352210      0.367573  0.207741                          NaN
    4 hist_gradient_boosting       21289       3041 2026-03-31 09:15:00+00:00 2026-04-14 22:35:00+00:00       NaN              NaN           NaN       NaN [WinError 5] Acceso denegado

Lectura:
- Variaciones marcadas entre folds apoyan la hipotesis de inestabilidad temporal.
- Si un modelo mantiene una media similar pero con alta dispersion, hace falta robustecer el label y la evaluacion antes de pensar en tuning.

## Prioritized Recommendations

1. Revisar la definicion del target antes de tocar hiperparametros, especialmente thresholds y horizonte.
2. Reducir o transformar features redundantes, en especial familias de EMAs y niveles poco informativos si se confirma su baja utilidad.
3. Mantener la validacion temporal como criterio principal; no confiar en una sola particion holdout.
4. Agregar analisis de regimen temporal y persistencia de senales antes de introducir modelos mas complejos.
5. Solo despues de estabilizar target y evaluacion, considerar ajustes de clase o costo.

## Next Suggested Steps

- Probar etiquetas derivadas con reglas de evento mas cercanas a la semantica de trading real.
- Incorporar features de cambio o slope en lugar de snapshots crudos cuando la interpretabilidad lo permita.
- Evaluar por mes o por tramo de mercado para detectar donde Baltasar aprende algo util y donde no.
