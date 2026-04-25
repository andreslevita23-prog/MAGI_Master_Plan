# Baltasar Training Lab

Resumen ejecutivo: este proyecto crea un laboratorio reproducible para entrenar y auditar a Baltasar sobre `triple_label_direction` (`BUY`, `SELL`, `NEUTRAL`). La base oficial actual es Baltasar v1.2: target `h12_t03`, features `compact`, `random_forest` como baseline oficial y `baseline_tree` como referencia explicable. El foco del laboratorio es interpretabilidad, trazabilidad y validacion temporal antes de cualquier tuning.

## Objetivo

Entrenar y comparar modelos de clasificacion multiclase para estimar direccion de mercado con tres etiquetas:

- `BUY`
- `SELL`
- `NEUTRAL`

## Baseline Oficial

Configuracion oficial consolidada de Baltasar v1.2:

- target: `h12_t03`
- feature variant: `compact`
- baseline oficial: `random_forest`
- modelo explicativo: `baseline_tree`

Motivo de eleccion:

- la corrida extendida de 24 meses mejoro senal y estabilidad temporal al mismo tiempo
- `random_forest` dejo de ser solo el mejor F1 puntual y paso a ser tambien el mejor compromiso de generalizacion
- `baseline_tree` se mantiene porque sigue siendo la referencia mas simple para explicar decisiones y revisar comportamiento por clase

## Executive Report

Informe ejecutivo final:

- Markdown: `artifacts/reports/baltasar_v11_executive_report.md`
- HTML: `artifacts/reports/baltasar_v11_executive_report.html`

Para regenerarlo:

```bash
cd baltasar_training_v1
python run_executive_report.py --config config/experiment.yaml
```

## Consolidacion v1.2

Entregables oficiales de Baltasar v1.2:

- Benchmark: `artifacts/metrics/official_v12_benchmark.csv`
- Reporte oficial: `artifacts/reports/baltasar_v12_consolidation.md`
- Reporte de entrenamiento extendido: `artifacts/reports/baltasar_v12_training_report.md`

Para regenerarlos:

```bash
cd baltasar_training_v1
python run_baltasar_v12.py --config config/experiment.yaml
python run_phase6_consolidation.py --config config/experiment.yaml
```

## Baltasar v1.2 Executive PDF Report

Reporte ejecutivo final de Baltasar v1.2:

- Markdown: `artifacts/reports/baltasar_v12_executive_report.md`
- HTML: `artifacts/reports/baltasar_v12_executive_report.html`
- PDF: `artifacts/reports/baltasar_v12_executive_report.pdf`

Para regenerarlo:

```bash
cd baltasar_training_v1
python run_baltasar_v12_pdf_report.py --config config/experiment.yaml
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
│   ├── data/
│   ├── diagnostics/
│   ├── evaluation/
│   ├── features/
│   ├── models/
│   ├── phase3/
│   ├── phase4/
│   ├── phase5/
│   ├── phase6/
│   └── visualization/
├── artifacts/
│   ├── models/
│   ├── metrics/
│   ├── figures/
│   └── reports/
├── app/
│   └── streamlit_app.py
├── run_experiment.py
├── run_diagnostics.py
├── run_phase3.py
├── run_phase4.py
├── run_baltasar_v12.py
└── run_phase6_consolidation.py
```

## Supuestos importantes

- El target sigue siendo derivado desde retorno futuro y no una etiqueta final de negocio.
- El split por defecto es temporal para evitar fuga de informacion.
- La configuracion central vive en `config/experiment.yaml`.
- El dataset extendido de `Bot_A_sub1` puede vivir fuera del repo, en la ruta estandar de `Common Files` de MT5.

## Instalacion

```bash
cd baltasar_training_v1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si ya tienes un interprete Python activo, puedes usarlo directamente:

```bash
pip install -r requirements.txt
```

## Ejecutar entrenamiento base

```bash
cd baltasar_training_v1
python run_experiment.py --config config/experiment.yaml
```

Salida esperada:

- dataset procesado en `data/processed/`
- metricas y reportes en `artifacts/metrics/`
- modelos serializados en `artifacts/models/`
- figuras en `artifacts/figures/`

## Ejecutar Baltasar v1.2

```bash
cd baltasar_training_v1
python run_baltasar_v12.py --config config/experiment.yaml
python run_phase6_consolidation.py --config config/experiment.yaml
```

Salida esperada:

- entrenamiento extendido y comparacion v1.1 vs v1.2 en `artifacts/metrics/`
- benchmark oficial v1.2 en `artifacts/metrics/official_v12_benchmark.csv`
- reporte oficial en `artifacts/reports/baltasar_v12_consolidation.md`
- figuras de walk-forward, target y confusion matrix en `artifacts/figures/`

## Abrir dashboard local

```bash
cd baltasar_training_v1
streamlit run app/streamlit_app.py
```

## Como conectar un dataset real

Hay tres caminos soportados:

1. Mantener el `.zip` inicial de snapshots.
2. Reemplazarlo por un CSV real.
3. Leer directamente un arbol de CSVs exportados por `Bot_A_sub1`.

Campos centrales en configuracion:

- `dataset.source.type`: `zip`, `csv` o `directory`
- `dataset.source.path`: ruta del archivo o carpeta
- `dataset.target_column`: nombre de la columna objetivo si ya existe
- `dataset.feature_drop_columns`: columnas a excluir del modelo
- `dataset.timestamp_column`: columna temporal usada para ordenar y partir

## Diseño para crecimiento futuro

- Registro de modelos desacoplado en `src/models/registry.py`.
- Separacion explicita entre carga, validacion, features, entrenamiento, evaluacion y visualizacion.
- Configuracion central en YAML.
- Soporte preparado para sumar CatBoost o LightGBM agregando un constructor al registro.

## Limitaciones conocidas

- El target actual es una aproximacion derivada.
- El dataset extendido no esta versionado dentro del repo.
- No se hace tuning exhaustivo; la intencion es tener una linea base explicable y estable.

## Proximos pasos sugeridos

- calibracion y criterios de promocion posteriores a v1.2
- refinamiento de target hacia eventos de negocio mas cercanos a trading real
- monitoreo de drift temporal y validacion por tramo
- eventual incorporacion de boosting externo solo despues de estabilizar la nueva base
