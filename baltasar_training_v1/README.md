# Baltasar Training v1

Resumen ejecutivo: este proyecto crea un laboratorio reproducible para el entrenamiento supervisado de Baltasar sobre `triple_label_direction` (`BUY`, `SELL`, `NEUTRAL`). La base oficial actual es Baltasar v1.1: target `h18_t05`, variante de features `compact`, `baseline_tree` como baseline oficial y `random_forest` compacto como challenger. El laboratorio incluye carga desde el paquete local actual de snapshots, validación de dataset, EDA visual, generación configurable del target, comparación de modelos de árboles, exportación automática de artefactos y un dashboard local en Streamlit para revisar corridas.

El laboratorio prioriza interpretabilidad, trazabilidad y claridad operacional. La primera versión evita redes neuronales, protege contra fuga de información usando split temporal por defecto y deja desacoplada la definición del target para que más adelante pueda sustituirse por una etiqueta real ya calculada.

## Objetivo

Entrenar y comparar modelos de clasificación multiclase para estimar dirección de mercado con tres etiquetas:

- `BUY`
- `SELL`
- `NEUTRAL`

## Alcance de esta versión

- Carga de snapshots desde un `.zip` o desde un CSV plano.
- Validación estructural y semántica básica del dataset.
- Etiquetado configurable basado en retorno futuro a horizonte fijo.
- Entrenamiento reproducible con `DecisionTreeClassifier`, `RandomForestClassifier` y `HistGradientBoostingClassifier`.
- Métricas exportadas automáticamente.
- Gráficos y tablas listos para revisión.
- Dashboard local para navegar resultados e historial.

## Baseline Oficial

Configuracion oficial consolidada de Baltasar v1.1:

- target: `h18_t05`
- feature variant: `compact`
- baseline oficial: `baseline_tree`
- challenger oficial: `random_forest`

Motivo de eleccion:

- no se eligio solo por el mejor `F1` puntual
- se priorizo mejor estabilidad temporal, trazabilidad y menor redundancia del set de features
- el challenger conserva mejor punto de comparacion, pero no fue promovido por su mayor dispersion en walk-forward

## Executive Report

Informe ejecutivo final:

- Markdown: `artifacts/reports/baltasar_v11_executive_report.md`
- HTML: `artifacts/reports/baltasar_v11_executive_report.html`

Para regenerarlo:

```bash
cd baltasar_training_v1
python run_executive_report.py --config config/experiment.yaml
```

## Estructura

```text
baltasar_training_v1/
├── README.md
├── requirements.txt
├── config/
│   └── experiment.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   └── reports/
├── notebooks/
│   ├── 01_data_validation.ipynb
│   ├── 02_eda.ipynb
│   └── 03_model_review.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── utils.py
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   └── visualization/
├── artifacts/
│   ├── models/
│   ├── metrics/
│   └── figures/
├── app/
│   └── streamlit_app.py
└── run_experiment.py
```

## Supuestos importantes

- El paquete actual de `Bot_A_sub1` no trae una columna de target final lista para entrenar `triple_label_direction`.
- En esta versión, el target se deriva a partir del retorno futuro de `current_price` a un horizonte configurable (`horizon_steps`).
- La clase se asigna con umbrales simétricos configurables:
  - retorno >= `buy_threshold`: `BUY`
  - retorno <= `sell_threshold`: `SELL`
  - en otro caso: `NEUTRAL`
- Si más adelante existe una columna objetivo real, basta con apuntar `dataset.target_column` en la configuración y desactivar el etiquetado derivado.

## Instalación

Desde la raíz de este proyecto:

```bash
cd baltasar_training_v1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si ya tienes un intérprete Python activo, puedes usarlo directamente:

```bash
pip install -r requirements.txt
```

## Ejecutar entrenamiento

```bash
cd baltasar_training_v1
python run_experiment.py --config config/experiment.yaml
```

Salida esperada:

- dataset procesado en `data/processed/`
- métricas y reportes en `artifacts/metrics/`
- modelos serializados en `artifacts/models/`
- figuras en `artifacts/figures/`

## Abrir dashboard local

```bash
cd baltasar_training_v1
streamlit run app/streamlit_app.py
```

## Ejecutar la fase de diagnostico

```bash
cd baltasar_training_v1
python run_diagnostics.py --config config/experiment.yaml
```

Salida esperada:

- tablas diagnosticas en `artifacts/metrics/`
- reporte tecnico en `artifacts/reports/`
- nuevas figuras de sensibilidad del target, confusion normalizada, correlacion y walk-forward en `artifacts/figures/`
- secciones adicionales dentro del dashboard para auditoria de target, metricas por clase y analisis temporal

## Ejecutar la fase 3

```bash
cd baltasar_training_v1
python run_phase3.py --config config/experiment.yaml
```

Salida esperada:

- grid sistematico de targets en `artifacts/metrics/`
- comparacion de escenarios y recomendacion Baltasar v1.1 en `artifacts/reports/`
- figuras de balance, estabilidad y comparacion experimental en `artifacts/figures/`
- nueva seccion de fase 3 dentro del dashboard

## Ejecutar la fase 4

```bash
cd baltasar_training_v1
python run_phase4.py --config config/experiment.yaml
```

Salida esperada:

- benchmark oficial v1.1 en `artifacts/metrics/`
- reporte de consolidacion en `artifacts/reports/`
- seccion oficial de baseline en el dashboard

## Cómo conectar un dataset real

Hay dos caminos soportados:

1. Mantener el `.zip` actual de snapshots y ajustar solo la configuración.
2. Reemplazarlo por un CSV real y editar `config/experiment.yaml`.

Campos centrales en configuración:

- `dataset.source.type`: `zip` o `csv`
- `dataset.source.path`: ruta del archivo
- `dataset.target_column`: nombre de la columna objetivo si ya existe
- `dataset.feature_drop_columns`: columnas a excluir del modelo
- `dataset.timestamp_column`: columna temporal usada para ordenar y partir

## Diseño para crecimiento futuro

- Registro de modelos desacoplado en `src/models/registry.py`.
- Separación explícita entre carga, validación, features, entrenamiento, evaluación y visualización.
- Configuración central en YAML.
- Soporte preparado para sumar CatBoost o LightGBM agregando un constructor de modelo al registro.

## Que queda pendiente

- recalibracion y criterios de promocion del challenger
- nuevas iteraciones de label design mas cercanas a eventos de trading real
- tuning y calibracion solo despues de consolidar la base v1.1
- preparacion de narrativa ejecutiva y material de presentacion

## Qué exporta cada corrida

- resumen de la corrida
- parámetros efectivos
- métricas por modelo
- métricas por clase
- matriz de confusión
- importancia de variables
- comparación visual de modelos
- historial acumulado de corridas

## Limitaciones conocidas

- El target actual es una aproximación derivada, no una etiqueta de negocio cerrada.
- La lectura del `.zip` está pensada para reproducibilidad y claridad, no para máxima velocidad.
- No se hace tuning exhaustivo; la intención es tener una línea base explicable.

## Próximos pasos sugeridos

- conectar el label de negocio definitivo si ya existe fuera de este paquete
- agregar validación walk-forward
- sumar calibración y análisis de probabilidad
- agregar modelos gradient boosting externos como CatBoost o LightGBM
