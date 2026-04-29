# MAGI Monthly Analysis

## Objetivo

Este documento resume la estabilidad mensual de los votos direccionales de Baltasar y la interacción `Gaspar GOOD + Baltasar`. El foco principal es H48; H12, H96 y H288 se mantienen como comparación secundaria en los archivos de análisis generados.

## Dataset

- Run: `data/output/ceo_training/20260429T002335Z_magi_v01_phase2/`
- Registros analizados: 18,600
- Símbolo: EURUSD
- Meses observados: 2025-12 a 2026-04
- Horizonte principal: 48 barras M5

## Breakdown Mensual H48

| Mes | BUY | BUY hit | BUY net | SELL | SELL hit | SELL net | BUY+GOOD | BUY+GOOD hit | BUY+GOOD net | SELL+GOOD | SELL+GOOD hit | SELL+GOOD net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-12 | 228 | 64.91% | 9.27 | 376 | 64.36% | 7.00 | 12 | 50.00% | 1.83 | 372 | 64.52% | 7.03 |
| 2026-01 | 1,015 | 66.80% | 17.01 | 1,026 | 74.37% | 15.74 | 23 | 100.00% | 55.31 | 585 | 74.36% | 12.06 |
| 2026-02 | 692 | 67.20% | 7.60 | 1,072 | 49.81% | 4.89 | 5 | 100.00% | 26.36 | 220 | 64.55% | 8.89 |
| 2026-03 | 2,015 | 56.82% | 7.69 | 2,029 | 64.12% | 9.63 | 0 | n/a | n/a | 315 | 74.60% | 7.94 |
| 2026-04 | 623 | 52.01% | 6.58 | 1,149 | 32.03% | -5.11 | 88 | 75.00% | 22.05 | 957 | 32.60% | -4.69 |

## Homogeneidad

| Serie | Media mensual | Desv. estándar | Mejor mes | Peor mes | Meses positivos | Meses negativos | Concentración mejor mes |
|---|---:|---:|---|---|---:|---:|---:|
| BUY | 9.63 | 4.24 | 2026-01 | 2026-04 | 5 | 0 | 39.02% |
| SELL | 6.43 | 7.63 | 2026-01 | 2026-04 | 4 | 1 | 51.85% |
| BUY+GOOD | 26.39 | 22.05 | 2026-01 | 2025-12 | 4 | 0 | 57.64% |
| SELL+GOOD | 6.25 | 6.40 | 2026-01 | 2026-04 | 4 | 1 | 73.15% |

## Hallazgos

### BUY

BUY fue positivo en todos los meses observados. El mejor mes fue enero 2026 y el peor fue abril 2026, pero abril siguió siendo positivo. Esto sugiere una señal más homogénea que SELL.

### SELL

SELL fue heterogéneo. Enero y marzo fueron fuertes, pero abril cayó a un hit rate de 32.03% y net pips negativos. Esto indica dependencia de régimen y riesgo de degradación temporal.

### BUY + GOOD

`BUY + GOOD` fue muy fuerte en H48, pero con muestra limitada. Enero y abril tuvieron resultados destacados; marzo no tuvo casos. La señal no debe promoverse a regla sin validación fuera de muestra.

### SELL + GOOD

`SELL + GOOD` tuvo volumen alto, pero abril concentró un deterioro fuerte. La concentración del mejor mes fue alta, y el peor mes fue negativo. No hay evidencia suficiente para tratar `GOOD` como filtro robusto de SELL.

## Conclusión

El resultado fue parcialmente heterogéneo por mes:

- BUY mostró estabilidad razonable.
- SELL fue sensible al régimen mensual.
- Gaspar GOOD mejora BUY en ciertos contextos, pero no estabiliza SELL.
- Abril 2026 es el principal mes de alerta por degradación de SELL.
- Enero 2026 concentra gran parte del resultado positivo y debe tratarse con cuidado para evitar sobreajuste.

La siguiente fase debe validar estas relaciones fuera de muestra antes de entrenar CEO-MAGI.
