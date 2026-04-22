# Datasets

Este repositorio documenta el dataset inicial generado por `Bot_A_sub1` para el entrenamiento inicial de Baltasar.

## Dataset inicial

- Nombre del paquete local: `dataset_botA_sub1_4months_v1.zip`
- Ubicacion local: `C:\Users\Asus\Desktop\MAGI_Master_Plan\dataset\dataset_botA_sub1_4months_v1.zip`
- Fuente del paquete: corrida limpia `run_2025-12-15_00-00-00`
- Cobertura temporal observada: `2025-12-12` a `2026-04-14`
- Instrumento: `EURUSD`
- Timeframe ancla: `M5`
- Timeframe primario: `H1`
- Formatos incluidos: `CSV` y `JSONL`

## Uso previsto

Este dataset sirve como base para el entrenamiento inicial de Baltasar en tareas de lectura de contexto tecnico y features de mercado.

## Limitaciones conocidas

- No incluye posiciones abiertas activas en la muestra inicial.
- Se empaqueta fuera del repo principal por tamano y para evitar versionar datos brutos.
- El repo conserva codigo, contratos y documentacion; el paquete `.zip` queda solo en almacenamiento local.

## Contenido esperado

Dentro del paquete, la estructura sigue este patron:

```text
run_2025-12-15_00-00-00/
  EURUSD/
    anchor_M5__primary_H1/
      YYYY/
        MM/
          DD/
            *.csv
            *.jsonl
```

## Siguiente etapa

Con este dataset, la siguiente etapa recomendada es preparar el pipeline de carga, validacion y entrenamiento inicial de Baltasar sin modificar la semantica del contrato generado por `Bot_A_sub1`.
