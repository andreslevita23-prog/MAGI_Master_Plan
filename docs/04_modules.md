# 04. Modules

## Bot A

Sensor periodico. Recoge contexto de mercado y estado de posicion, normaliza el snapshot y lo distribuye. No filtra oportunidades ni propone trades.

## Melchor

Guardia de capital. Evalua peligro contextual, endurece riesgo ante posicion abierta y puede bloquear entradas peligrosas.

## Baltasar

Validador tecnico. Determina si el setup tiene calidad estructural suficiente para justificar una decision operativa.

## Gaspar

Explorador de oportunidad. Detecta escenarios utiles menos obvios sin romper el marco conservador del sistema.

## CEO-MAGI

Arbitro final. Consume votos y contexto, decide accion, define entrada, `SL` y `TP`, y justifica la decision.

## Bot B

Ejecutor determinista. Traduce la decision final a una accion operativa en el entorno broker/MT5.

## Bot C

Auditor y constructor de dataset. Guarda cada caso, encadena historia de la operacion y permite reconstruccion futura.

## Bot D

Modulo futuro de optimizacion y aprendizaje. Analizara historicos, comparara desempeno por modulo y asistira en la evolucion del sistema.
