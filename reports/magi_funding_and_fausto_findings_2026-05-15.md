# MAGI: hallazgos de fondeo y prototipo Fausto

Fecha de consolidacion: 2026-05-15

Este informe consolida experimentos exploratorios de simulacion. No modifica codigo operativo ni constituye recomendacion de riesgo.

## 1. Contexto

La exploracion nacio como una curiosidad tecnica: medir velocidad y fragilidad de MAGI bajo reglas tipo fondeo. Sin embargo, al cruzar stress tests, walk-forward, causal scoring, governance, auditorias anti-lookahead y las simulaciones recientes, aparecio una consistencia mas interesante de lo esperado.

Esto no es validacion definitiva. No garantiza rentabilidad futura, no autoriza lotajes extremos y no convierte a Fausto en estrategia productiva. Lo que si muestra es que el edge historico de MAGI no se deshace inmediatamente al escalar tamano; el problema aparece mas por restricciones intradia que por muerte lenta de equity.

## 2. Simulaciones de fondeo clasicas

| lote | inicio | fase1 | dias_f1 | fase2 | dias_f2 | peor_dia | max_dd | margen_diario | comentario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 2025-04-01 | 2025-09-30 | 181 | 2026-03-10 | 161 | -305.76 | 684.36 | 3694.24 | conservador, funded-compatible, lento |
| 3.0 | 2025-05-01 | 2025-08-07 | 87 | 2025-09-25 | 50 | -917.27 | 2053.08 | 3082.73 | punto medio viable |
| 5.0 | 2025-05-01 | 2025-07-25 | 74 | 2025-08-07 | 14 | -1528.78 | 3421.79 | 2122.78 | rapido pero agresivo |

### Lectura operativa

- **1 lote:** extremadamente conservador. Pasa ambas fases en el historico, pero tarda mucho. Es el perfil mas compatible con supervivencia y aprendizaje operativo.

- **3 lotes:** punto medio mas interesante. Acelera de forma clara sin acercarse dramaticamente al limite diario en el tramo probado. Es el primer candidato serio para una funded prudente, siempre que la demo confirme estabilidad.

- **5 lotes:** agresivo pero sorprendentemente viable en varios tramos. Pasa mas rapido, pero el margen psicologico y operativo se comprime. Depende mas del timing favorable.

## 3. Descubrimiento clave: daily DD

MAGI rara vez muere lentamente por perdida total. En las pruebas, el enemigo principal fue la perdida diaria: clusters violentos, sesiones toxicas y reentradas concentradas. El balance total podia seguir muy arriba, pero una sola jornada mala ya podia invalidar una evaluacion.

Esto refuerza la decision de implementar governance: SAFE_MODE, deteccion de cluster, shadow guardrails de viernes y auditoria de secuencias. El objetivo no es cambiar el edge, sino evitar que el edge se autodestruya por exposicion concentrada.

## 4. Proyecto Fausto: exploracion de edge bajo sobreexposicion

| lotes | payouts | burns | neto | supervivencia | ratio | peor_dia | dd | comentario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 5 | 1 | 44713.92 | 83.33 | 5.0 | -5236.28 | 5535.68 | edge sobrevive, pero con dientes; psicologicamente duro |
| 15 | 8 | 3 | 75904.79 | 72.73 | 2.67 | -5753.74 | 6202.85 | edge sobrevive, pero con dientes; psicologicamente duro |
| 20 | 9 | 3 | 86675.16 | 75.0 | 3.0 | -5399.8 | 7508.87 | edge sobrevive, pero con dientes; psicologicamente duro |

### Lectura Fausto

- **10 lotes:** el edge todavia respira. En baseline tuvo mas payouts que burns; en `cluster_only_3sl` incluso sobrevivio limpio en el tramo Fausto. Aun asi, psicologicamente es duro.

- **15 lotes:** muy rentable en tramos favorables, pero ya aparecen burns. Se vuelve dependiente del orden de trades.

- **20 lotes:** extremo. En cycling genera mucho neto en el tramo favorable, y en 2025 completo sin resets termina con +242% en baseline, pero viola daily DD. Para fondeo estricto es suicida, aunque estadisticamente sea fascinante.

## 5. Experimento 20 lotes, ano completo 2025

| escenario | final | ganancia | retorno | peor_dia | max_dd | violacion_diaria | comentario |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 342022.95 | 242022.95 | 242.02 | -6115.13 | 13687.17 | 2025-01-16 | suicida para fondeo: viola limite diario |

La curva 20 lotes demuestra la paradoja: el edge puede generar una curva final muy alta, pero las reglas de fondeo no perdonan el dolor intradia. La cuenta no muere por balance total; muere por dia malo.

## 6. Equity curves

### 1 lote baseline

![1 lote baseline](reports/charts/fausto/equity_baseline_1lot_2025_04_to_2026_03.png)

### 3 lotes baseline

![3 lotes baseline](reports/charts/fausto/equity_baseline_3lot_2025_05_to_2025_09.png)

### 5 lotes baseline

![5 lotes baseline](reports/charts/fausto/equity_baseline_5lot_2025_05_to_2025_09.png)

### Fausto 20 lotes 2025

![Fausto 20 lotes 2025](reports/fausto_20_lots_equity_2025.png)

Las curvas no muestran una death spiral tipica. Hay serruchos, retrocesos y clusters, pero tambien recuperaciones rapidas. Ese comportamiento es una de las senales mas interesantes: MAGI parece tener persistencia, pero necesita una capa de gobierno para que un dia toxico no invalide una cuenta.

## 7. Hallazgo estrategico

MAGI parece mas escalable, menos fragil y con edge mas persistente de lo esperado. Esa es la parte positiva. La parte peligrosa es que el riesgo escala de forma violenta: al subir lotaje, el problema deja de ser rentabilidad anual y pasa a ser supervivencia intradia.

En lenguaje operativo: MAGI puede producir, pero debe aprender a no suicidarse en dias toxicos.

## 8. Conclusiones prudentes

### MAGI serio

- Debe priorizar supervivencia, consistencia, governance y respeto estricto de daily DD.

- El rango 3-5 lotes merece estudio para funded, no adopcion automatica.

- El 3 lotes aparece como candidato prudente inicial si la demo live confirma estabilidad.

### Fausto

- Debe quedar como modulo experimental, no como core principal.

- Nunca debe usarse con capital vital ni como primera estrategia funded.

- Solo tendria sentido futuro si MAGI serio demuestra estabilidad, retiros y baja varianza en vivo.

## 9. Recomendaciones

### Antes del 5 de junio

- Seguir demo sin tocar reglas de entrada.

- Validar governance, SAFE_MODE, clusters y shadow Friday Guardrail.

- Medir daily DD real y MFE/MAE intradia.

- Revisar si 1 lote y 3 lotes mantienen comportamiento sano en live.

### Despues

- Evaluar funded prudente, probablemente iniciando en 1-3 lotes segun evidencia live.

- Considerar 5 lotes solo si la demo confirma margen diario suficiente.

- No usar Fausto como estrategia principal.

## 10. Veredicto

Los resultados son mas interesantes de lo esperado: MAGI no parece un sistema fragil que se rompe al escalar. Pero la escalabilidad del edge no equivale a seguridad operativa. La conclusion honesta es: MAGI merece seguir vivo, merece demo seria y merece governance fuerte. Fausto queda como laboratorio, no como volante principal.
