# Baltasar v1.2 Consolidation

## Official Status

- Version: `Baltasar v1.2`
- Official target: `h12_t03`
- Official feature variant: `compact`
- Official baseline model: `random_forest`
- Explanatory reference model: `baseline_tree`
- Extended dataset run: `run_2024-04-15_00-00-00`

## Benchmark Oficial v1.2

                 role       version target_name feature_variant    model_name  feature_count  accuracy  f1_macro  walk_forward_f1_mean  walk_forward_f1_std                                                                           trade_off
    official_baseline Baltasar v1.2     h12_t03         compact random_forest             16  0.419618  0.401418              0.386500             0.011886      Promoted because the 24-month run improved both signal and temporal stability.
explanatory_reference Baltasar v1.2     h12_t03         compact baseline_tree             16  0.425374  0.390639              0.379223             0.014438 Retained as the explanatory reference because it is simpler to interpret and audit.

## Comparacion v1.1 vs v1.2

      version    model_name  accuracy  f1_macro  walk_forward_f1_mean  walk_forward_f1_std
Baltasar v1.1 baseline_tree  0.393342  0.306621              0.312846             0.024333
Baltasar v1.1 random_forest  0.389848  0.388620              0.325108             0.061122
Baltasar v1.2 baseline_tree  0.425374  0.390639              0.379223             0.014438
Baltasar v1.2 random_forest  0.419618  0.401418              0.386500             0.011886

## Por que cambia la baseline

- En v1.1 el `random_forest` era challenger porque tenia mejor F1 puntual pero peor estabilidad temporal.
- En v1.2, sobre 24 meses, `random_forest` mejora a la vez `f1_macro`, `walk_forward_f1_mean` y `walk_forward_f1_std`.
- Eso elimina la principal objecion tecnica que impedia promoverlo.
- `baseline_tree` se mantiene como referencia explicable porque sigue siendo mas facil de auditar y comunicar.

## Analisis de estabilidad

- Baseline oficial v1.2 (`random_forest`): holdout F1 `0.4014`, walk-forward mean `0.3865`, walk-forward std `0.0119`.
- Referencia explicable (`baseline_tree`): holdout F1 `0.3906`, walk-forward mean `0.3792`, walk-forward std `0.0144`.
- Frente a v1.1, ambos modelos mejoran estabilidad, pero `random_forest` deja de ser un modelo de alto F1 con alta dispersion y pasa a ser el mejor equilibrio general.

## Metricas por clase

Baseline oficial:

  label  precision   recall       f1  support
   SELL   0.330784 0.292627 0.310538     8721
NEUTRAL   0.517593 0.554194 0.535269    12077
    BUY   0.355440 0.361504 0.358446     8910

Referencia explicable:

  label  precision   recall       f1  support
   SELL   0.321008 0.200092 0.246521     8721
NEUTRAL   0.496873 0.624907 0.553583    12077
    BUY   0.368270 0.375421 0.371811     8910

## Riesgos actuales

- El target sigue siendo derivado, no una etiqueta final de negocio.
- El dataset extendido vive fuera del repo, en la ruta de `Common Files` de MT5, asi que la reproducibilidad depende de esa ubicacion local.
- Existen 110 gaps superiores a 8 horas; son razonables para mercado, pero conviene seguir monitoreando segmentacion temporal.
- No hubo tuning ni calibracion; esta consolidacion formaliza la base actual, no el techo de rendimiento.
- Las columnas de posicion (`entry_price`, `sl`, `tp`, `floating_pnl`, `position_type`) siguen con missing alto y deben seguir tratandose como evidencia secundaria.

## Decision documentada

- Se promueve `random_forest` como baseline oficial de Baltasar v1.2.
- Se conserva `baseline_tree` como modelo explicativo de referencia.
- No se cambian hiperparametros ni se introducen modelos nuevos en esta consolidacion.
