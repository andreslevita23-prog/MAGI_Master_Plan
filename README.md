# MAGI Master Plan

Plan maestro de arquitectura para MAGI, el nucleo de decision del sistema Prosperity.

## Proposito

Este repositorio documenta la arquitectura objetivo, el alcance del MVP, los contratos de datos y la evolucion prevista hacia una integracion progresiva de machine learning sin romper la trazabilidad ni el control de riesgo.

## Principios rectores

- Claridad antes que complejidad.
- Riesgo y disciplina por encima de frecuencia operativa.
- Un solo instrumento en el MVP: `EURUSD`.
- Maximo una operacion abierta a la vez.
- Maximo un caso MAGI activo a la vez.
- Contratos estables y compatibles con ML futuro.
- Auditoria completa de cada caso.

## Estructura documental

- `docs/01_vision.md`: vision del sistema y objetivos.
- `docs/02_architecture_overview.md`: arquitectura de alto nivel.
- `docs/03_system_flow.md`: flujo operativo end-to-end.
- `docs/04_modules.md`: responsabilidades de cada modulo.
- `docs/05_magi_logic.md`: reglas MAGI y jerarquia.
- `docs/06_bot_a.md`: especificacion del sensor periodico.
- `docs/07_melchor.md`: diseno del mago de riesgo.
- `docs/08_baltasar.md`: diseno del mago tecnico.
- `docs/09_gaspar.md`: diseno del mago de oportunidad.
- `docs/10_ceo_magi.md`: motor de arbitraje y decision final.
- `docs/11_bot_b.md`: ejecutor operativo.
- `docs/12_bot_c.md`: auditoria y dataset.
- `docs/13_cases.md`: semantica de `entry_case` y `management_case`.
- `docs/14_data_contracts.md`: contratos JSON entre modulos.
- `docs/15_risk_rules.md`: reglas duras de riesgo del MVP.
- `docs/16_mvp_scope.md`: alcance y limites del MVP.
- `docs/17_roadmap.md`: roadmap por fases.
- `docs/18_ml_future.md`: evolucion futura hacia ML.

## Diagramas y plantillas

- `diagrams/architecture.mmd`
- `diagrams/flow.mmd`
- `templates/bot_a_sample.json`
- `templates/magi_votes_sample.json`
- `templates/ceo_decision_sample.json`

## Estado esperado de la siguiente fase

Con esta base, la siguiente etapa puede traducir la arquitectura a implementacion modular sin redefinir contratos, semantica de casos ni gobierno de decision.

## Dataset inicial de Baltasar

La etapa de generacion del dataset inicial con `Bot_A_sub1` queda cerrada con una corrida limpia empaquetada fuera del repo principal.

- Documentacion del dataset: `datasets/README.md`
- Paquete local: `C:\Users\Asus\Desktop\MAGI_Master_Plan\dataset\dataset_botA_sub1_4months_v1.zip`
- Objetivo: entrenamiento inicial de Baltasar sobre `EURUSD`, con ancla `M5` y timeframe primario `H1`

El paquete no se versiona en GitHub por tamano. El repositorio conserva codigo, documentacion y referencias para reproducir o extender esta etapa.
