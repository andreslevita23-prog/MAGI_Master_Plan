# 17. Roadmap

## Fase 0 - Arquitectura

- Cerrar descubrimiento.
- Definir modulos, contratos y flujo.
- Establecer plan maestro del repositorio.

## Fase 1 - MVP funcional

- Implementar `Bot A`, magos, `CEO-MAGI`, `Bot B` y `Bot C`.
- Operar `EURUSD` con reglas deterministas.
- Registrar casos completos.

## Fase 2 - Robustez

- Fortalecer validaciones.
- Mejorar resiliencia operativa.
- Ajustar observabilidad y manejo de errores.

## Fase 3 - Auditoria avanzada

- Analitica de decisiones.
- Evaluacion de rechazos y oportunidades perdidas.
- Reportes por modulo y por tipo de caso.

## Fase 4 - Integracion ML

- Construir datasets desde `Bot C`.
- Entrenar progresivamente `Melchor`, `Baltasar` y `Gaspar`.
- Validar en shadow mode.
- Promover modelos sin romper contratos.

## Fase 4A - Gaspar Training v1

- Mantener `gaspar_training_v1/` como laboratorio modular separado de Baltasar.
- Usar `Bot_A_sub2.mq5` para generar dataset estructural/temporal de Gaspar.
- Mantener `target_v2` como baseline oficial actual tras auditoria y entrenamiento de 24 meses.
- Mantener `target_v4` como challenger experimental por su mejor estabilidad walk-forward, sin promoverlo todavia.
- Comparar resultados por F1 macro, matriz de confusion, distribucion de clases y walk-forward.
- Reemplazar o calibrar la heuristica con resultados reales registrados por Bot C.
- Antes de operar, agregar en Bot A principal un bloque `gaspar_context` con estructura, contexto temporal y `proposed_direction`, sin confianza, probabilidades, features ni indicadores de Baltasar.
